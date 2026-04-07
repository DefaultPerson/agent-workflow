---
name: cleanup
description: >
  Clean up and restructure messy notes/plans: semantic sort, AI rewrite,
  100% verified gap detection, optional split into spec + references.
  Triggers: "cleanup", "/cleanup", "почисти", "реорганизуй", "clean up",
  "plan-rewrite", "/plan-rewrite", "rewrite plan", "sort plan"
allowed-tools: [shell, glob_file_search, rg, read_file, apply_patch, agent]
---

# Cleanup Skill

Clean up, reorganize, and optionally split a plan file with **100% verified** gap detection.

## Usage

```
/cleanup <file path> [file2] [file3]
```

Multiple files: concatenated with `<!-- from: filename -->` markers, sorted together.

## Algorithm

$ARGUMENTS

Arguments: `<file path> [file2] [file3]`

### Phase 0: Input Handling

1. **Validate**: If no argument — output the question as text and wait for user response.
2. **Multi-file**: If multiple files provided:
   - Backup each: `cp <fileN> <fileN>.bak`
   - Concatenate into first file path with section markers:
     ```
     <!-- from: file1.md -->
     <contents of file1>
     
     <!-- from: file2.md -->
     <contents of file2>
     ```
   - Continue with the concatenated file as input.
3. **Single file**: proceed to Phase 1.

### Phase 1: Sort

1. **Backup** (if single file): `cp <file> <file>.bak`
3. **Semantic sort** (AI — you do this directly):
   - Parse sections by `## ` headers.
   - Orphan lines before first header → create a header for them.
   - **Semantic audit**: go through EVERY non-empty line in EVERY section. If a line's topic doesn't match its section — move it to the correct section. If no suitable section exists — create a new one.
   - Insert moved lines before the first `### ` subsection in the target section. Respect code block boundaries (``` ... ```).
   - Collapse consecutive blank lines (max 1).
   - Preserve frontmatter at the top.
   - Preserve every original line exactly as-is — no rewording, no reformatting. You MAY add new `## ` headers for organization, but NEVER delete or rename existing lines. Header cleanup happens in Phase 3.
4. **Write** sorted version to original file path.
   - **Unicode caution**: The apply_patch tool may normalize Unicode (losing non-breaking spaces U+00A0 etc.). If verify-sort.py shows missing lines — check `repr()` of lines for `\xa0` and similar characters, then use Python for byte-for-byte copying from the original.

### Phase 2: Verify Sort

Run the verification script:

```bash
python3 scripts/verify-sort.py <file>.bak <file>
```

- The script checks that ALL original lines are present in sorted (superset check). New lines (added headers) are OK.
- If FAIL (original lines missing) → restore from backup, ABORT, report error.
- If PASS → continue.

### Phase 3: Rewrite

Rewrite the sorted file into a clean, well-structured document. Create `<basename>.rewritten.<ext>`:

- Fix grammar, punctuation, style, typos.
- Remove exact duplicates (same meaning — keep the more detailed version).
- Restructure: add `## ` section summaries, create `### ` subsections where logical.
- Clean up chat artifacts: timestamps (☀️, Ivan KOLESNIKOV), informal fragments → integrate into structured items.
- Rephrase unclear/broken sentences for clarity.
- Convert unstructured notes into actionable items where possible.
- Consolidate related items within the same section.

**Chat log handling:**
- Extract and PRESERVE: specific numbers, prices, URLs, actionable insights, named entities.
- Summarize back-and-forth debate into key positions with attribution.
- If a chat section has >50 lines, create a "Key takeaways" subsection + keep raw data points as bullets.
- NEVER reduce a chat section to <20% of its original line count.

Constraints:
- MUST preserve ALL ideas, tasks, links, URLs, references — every distinct thought must survive.
- DO NOT merge DIFFERENT tasks that seem related but are distinct.
- DO NOT drop informal notes/questions — they may contain important context. Rephrase but keep.
- The gap detection pipeline will catch any losses, so focus on producing a CLEAN readable plan.
- AVOID using `<details>` / `<summary>` HTML blocks for critical content. Gap detection agents and scripts search raw text and may miss content inside HTML tags. If you use `<details>`, duplicate key facts outside the collapsible block (e.g., in a summary line above it).

### Phase 4: Gap Detection (three levels)

#### 4a: Deterministic check (script)

```bash
python3 scripts/verify-rewrite.py <sorted> <rewritten>
```

Extracts and compares URLs (only). Report missing URLs.

#### 4b: Semantic check (pre-filter + background agents)

> **Small file optimization**: If sorted file has <50 non-empty content lines → skip 4b entirely, rely on 4c fuzzy matching + agent verification. This saves significant time on small files.

> **GATE CHECK** (for files ≥50 lines): 4b and 4c are DIFFERENT checks. BOTH are mandatory, in order.
> - **4b** = per-section semantic comparison → MISSING / PARTIAL / REVERSED
> - **4c** = safety net script fuzzy-match → only TRUE_MISSING
> Do NOT skip 4b. Do NOT substitute 4b with 4c.

**Step 1 — Pre-filter via rg** (reduces agent load by ~60-80%):

1. For each `## ` section in the sorted file, collect all non-empty content lines.
2. For each line, extract 2-3 unique keywords (prefer proper nouns, numbers, technical terms).
   - **For lines with URLs**: extract domain/path as keyword (e.g., from `https://t.me/foo/123` → `foo/123`; from `https://github.com/user/repo` → `repo`).
   - **For lines containing ONLY a URL**: grep by domain+path fragment.
3. `rg` each keyword in the rewritten file.
4. If ANY grep finds the meaning of the line → mark COVERED, skip.
5. If NO grep finds the line → add to the UNFOUND list for that section.

Example:
- Sorted line: `Автоматизация отработки фандингов https://t.me/automaker_main/43`
- Keywords: `фандинг`, `automaker`
- rg `automaker` in rewritten → found at line 85 → COVERED, skip.

**Step 2 — Spawn agents for sections with unfound lines**:

Assign 1-2 sections (by headers) per agent (only sections with remaining unfound lines after Step 1). No limit on agent count.

- `subagent_type`: `Explore`
- `run_in_background`: true

**Agent prompt** (use this for each agent, replacing SECTIONS and FILE_PATHS):

```
You are a gap detector. Compare SORTED file vs REWRITTEN file for these sections: [SECTIONS].

Files:
- Sorted: [SORTED_PATH]
- Rewritten: [REWRITTEN_PATH]

CRITICAL: Use rg tool to search for key phrases from each sorted line. Do NOT rely on manual reading for large files. For each line, grep 3-5 unique words in the rewritten file.

IMPORTANT: The rewritten file may contain HTML blocks (<details>, <summary>, <table>).
Content inside these tags IS valid — search INSIDE them with rg. A line found inside
<details>...</details> counts as present.

For EACH non-empty line in your assigned sections of the SORTED file:
1. Search for a semantic equivalent in the REWRITTEN file (search the ENTIRE file, not just the same section)
2. If found with same meaning → SKIP
3. If found but details lost → PARTIAL (quote both lines + what was lost)
4. If meaning changed/reversed → REVERSED (quote both lines)
5. If NOT found anywhere → MISSING (quote the sorted line)

RULES:
- Grammar/formatting changes are NOT gaps. "setup nginx" → "Set up Nginx" is fine.
- PARTIAL only when a SPECIFIC IDEA, DETAIL, or CONTEXT is lost — not formatting.
- These are NOT gaps: bullet→checkbox, case changes, typo fixes, punctuation, link text changes.
- If the core idea and all details are preserved, it's a SKIP regardless of formatting.
- You MUST quote exact text from both files. If you cannot quote the rewritten equivalent — it IS missing.
- Output format per finding:
  SECTION: <header>
  TYPE: MISSING|PARTIAL|REVERSED
  SORTED_LINE: "<exact quote>"
  REWRITTEN_LINE: "<exact quote or NOT_FOUND>"
  LOST_DETAIL: "<what was lost>" (PARTIAL only)
```

**4b is complete when**: All section agents have returned results. Now proceed to 4c.

#### 4c: Coverage safety net (script + agent verification)

**Step 1**: Run the coverage script:
```bash
python3 scripts/verify-coverage.py <sorted> <rewritten> <gaps>
```

The script checks every sorted line against rewritten (fuzzy match) and gaps. Lines not found → written to `<basename>.uncovered.tmp`.

**Step 2**: If uncovered candidates exist, split into batches of 100 lines. Spawn one agent per batch in parallel. **No limit on agent count** — use as many as needed. NEVER skip this step.

- `subagent_type`: `Explore`
- Each agent reads its batch from `.uncovered.tmp`, plus the rewritten file
- For each candidate, the agent determines: is this truly missing from rewritten, or just rephrased/reformatted?

**Agent prompt**:
```
You are a coverage verifier. You have a list of lines that a fuzzy-matching script
could not find in the rewritten file. Many of these are FALSE POSITIVES — the content
IS in the rewritten file but was rephrased, reformatted, or had typos fixed.

IMPORTANT: The rewritten file may use <details><summary>...</summary>...</details> blocks.
Content inside these blocks IS present — search the raw file text, not rendered output.
Many false positives come from content moved into <details> blocks.

CHAT SUMMARIZATION RULE: The rewritten file intentionally summarizes raw chat logs
(timestamped messages like "☀️, [date]") into structured "Key takeaways" sections.
If a chat message's substantive facts (numbers, prices, names, conclusions) appear
in summarized form — it is COVERED, not MISSING. Specifically:
- Timestamps, emoji markers, informal greetings → always FALSE POSITIVE
- Conversational fragments ("Ну хз", "Ага", "Потом конечная") → FALSE POSITIVE
- Back-and-forth debate condensed to conclusion → COVERED
- Specific numbers/facts preserved in summary → COVERED
Only report TRUE_MISSING if the substantive IDEA has no equivalent anywhere in the file.

Files:
- Uncovered candidates: [UNCOVERED_TMP_PATH]
- Rewritten: [REWRITTEN_PATH]

For EACH line in the uncovered file:
1. Search the ENTIRE rewritten file for content with the same meaning
2. If found (even rephrased, reformatted, typo-fixed, summarized) → FALSE POSITIVE, skip it
3. If truly NOT found anywhere → TRUE MISSING, report it

Output ONLY the TRUE MISSING lines, one per line, with format:
TRUE_MISSING: "<exact line from uncovered file>"

If all lines are false positives, output: "ALL COVERED — no true gaps found."
```

**Step 3**: Only TRUE MISSING lines from the agent get added to the gaps file as `[UNCOVERED]`. Delete the `.uncovered.tmp` file.

### Phase 5: Gaps File

1. Wait for all background agents to complete.
2. Merge results from script (4a) + agents (4b).
3. Write initial `<basename>.gaps.md`.
4. Run coverage check (4c) — script finds candidates, agent verifies, only true gaps added.
5. Delete `.uncovered.tmp`.
6. Deduplicate.

**Gaps file format:**

```markdown
# Gaps: <filename>
<!-- Delete lines you don't need. Keep lines to apply to rewritten. -->
<!-- Summary: N MISSING, M PARTIAL, K REVERSED, L UNCOVERED -->

## <Section Name>

- [MISSING] `<exact sorted line>`
- [PARTIAL] `<sorted line>` → rewritten: `<rewritten line>` | Lost: <detail>
- [REVERSED] `<sorted line>` → rewritten: `<rewritten line>`
- [UNCOVERED] `<sorted line>`
```

### Phase 5.5: Auto-continue check

**IF gaps_count == 0** (no MISSING, PARTIAL, REVERSED, or UNCOVERED items):
→ Delete the empty gaps file.
→ Output: "No gaps found. Skipping to final verification."
→ Jump to **Phase 8** (Final Verification).

**ELSE** → continue to Phase 6.

### Phase 6: PAUSE

Output a report:

```
=== CLEANUP COMPLETE (Phases 1-5) ===

Files:
  Backup:    <path>.bak          (<N> lines)
  Sorted:    <path>              (<N> lines, verified)
  Rewritten: <path>.rewritten    (<N> lines)
  Gaps:      <path>.gaps.md      (<N> items: X missing, Y partial, Z reversed, W uncovered)

Next: edit .gaps.md, delete what you don't need. Write me when you're ready to continue. 
```

**STOP. Do not continue until the user indicates they are ready.**

### Phase 7: Apply

When the user indicates they are ready:

1. Read the edited gaps file.
2. For each remaining item:
   - `[MISSING]` / `[UNCOVERED]` → insert the original line into the appropriate section in rewritten.
   - `[PARTIAL]` → augment the rewritten line with the lost detail.
   - `[REVERSED]` → fix the meaning in rewritten.
3. Delete the gaps file.
4. Output: "Applied N items. Final: <path>.rewritten (<N> lines)"

### Phase 8: Final Verification

Verify the final rewritten file against the original backup:

```bash
# All URLs from original present in final?
python3 scripts/verify-rewrite.py <file>.bak <basename>.rewritten.<ext>

# Every original line covered in final?
python3 scripts/verify-coverage.py <file>.bak <basename>.rewritten.<ext> /dev/null
```

- If uncovered candidates found → **MANDATORY**: spawn NEW agents (batches of 100).
  Do NOT reuse Phase 4c results — Phase 4c compared **sorted → rewritten**,
  Phase 8 compares **backup (original) → rewritten**. Different source = different gaps.
  **Optimization**: Если Phase 4c не выявила TRUE_MISSING items, И sorted файл
  отличается от backup только добавленными `## ` headers (что проверено в Phase 2),
  то допустимо запустить 1 агент на ВЕСЬ список uncovered (вместо батчей по 100),
  с инструкцией "expect mostly false positives, report only truly unique content".
  Use this prompt:
  ```
  You are a final coverage verifier. Lines from the ORIGINAL BACKUP were not fuzzy-matched
  in the FINAL rewritten file. Many are FALSE POSITIVES (rephrased, reformatted, reorganized).

  IMPORTANT: The rewritten file may contain <details>, <summary> and other HTML elements.
  Content inside these tags IS present — search inside them.

  CHAT SUMMARIZATION RULE: The rewritten file intentionally summarizes raw chat logs
  (timestamped messages like "☀️, [date]") into structured "Key takeaways" sections.
  If a chat message's substantive facts (numbers, prices, names, conclusions) appear
  in summarized form — it is COVERED, not MISSING. Specifically:
  - Timestamps, emoji markers, informal greetings → always FALSE POSITIVE
  - Conversational fragments → FALSE POSITIVE
  - Back-and-forth debate condensed to conclusion → COVERED
  - Specific numbers/facts preserved in summary → COVERED
  Only report TRUE_MISSING if the substantive IDEA has no equivalent anywhere.

  Files:
  - Uncovered candidates: [UNCOVERED_TMP_PATH]
  - Final rewritten: [REWRITTEN_PATH]

  For EACH line:
  1. Search ENTIRE rewritten file for same meaning
  2. Found (even rephrased, inside <details>, summarized) → FALSE POSITIVE, skip
  3. Truly not found → TRUE MISSING

  Output: TRUE_MISSING: "<exact line>" or "ALL COVERED — no true gaps found."
  ```
- If TRUE MISSING found → report them, DO NOT replace original, DO NOT delete backup.
- If all clear:
  1. **Auto-replace**: `mv <file>.rewritten <file>` — original is replaced, `.bak` stays as backup.
  2. Delete the gaps file if it exists.
  3. Output: "✅ Final verification passed. Original replaced. Backup: <file>.bak"

### Phase 9: Report

Output a final report:

```
=== CLEANUP REPORT ===

Metrics:
  Original:  <N> lines
  Rewritten: <N> lines (<ratio>% compression)
  Gaps found: <N> (X applied, Y dismissed by user)
  URLs: <N> original, <M> preserved, <K> missing (user-approved)
  Original replaced: yes/no
  Backup: <path>.bak

Issues encountered:
- <any verification failures, skipped steps, agent errors, or anomalies>

Fixes (brief, only if issues found):
- <concrete action to resolve each issue>

Recommendations:
- <suggestions for the file or future rewrites>
```

---

## Phase B: Split (optional)

After Phase 9 Report, offer to split the cleaned file into structured spec + reference files.

### Phase 10: Split Analysis (plan mode)

1. Analyze the clean file for distinct topics/projects.
2. **IF** single topic OR file has <100 lines → skip split, suggest clarify:
   ```
   "File is focused on a single topic. Recommend: /compact then /clarify <file>"
   ```
3. **IF** multiple distinct topics found → **enter plan mode** (`/plan`):
   - Write a split plan to the plan file with:
     - List of output files with names and descriptions
     - For each file: which sections/line ranges go there
     - Cross-reference strategy (which specs link to which references)
     - Estimated line counts per file
   - Plan format:
     ```markdown
     # Split Plan: <filename>
     
     ## Output files
     
     ### spec-<topic-A>.md (~N lines)
     Sections: <list of ## headers going here>
     Content: <brief description>
     
     ### references-<topic-A>.md (~M lines)
     Sections: <list of ## headers going here>
     Content: links, research, external refs related to topic A
     
     ### spec-<topic-B>.md (~K lines)
     ...
     
     ## Cross-references
     - spec-<A>.md → references-<A>.md
     - spec-<B>.md → references-<B>.md
     ```
   - Exit plan mode — user reviews and approves.
   - If user rejects → ask what to change, revise plan, re-submit.
   - If user approves → proceed to Phase 11.

### Phase 11: Execute Split

1. Create output directory: `<basename>/` (sibling to input file).
2. Follow the approved plan — for each file:
   - `spec-<topic-slug>.md` — main content (tasks, goals, requirements, decisions).
   - `references-<topic-slug>.md` — links, research notes, external refs, raw data.
3. Add cross-references at top of each spec:
   ```markdown
   > References: [references-<topic>.md](references-<topic>.md)
   ```
4. Preserve every original line exactly as-is in one of the output files.

### Phase 12: Verify Split

```bash
python3 scripts/verify-split.py <original-clean-file> <output-dir>
```

The script concatenates all `.md` files in output dir and checks that every line from the original is present (fuzzy match). New lines (navigation headers, cross-references) are OK.

- If FAIL → report uncovered lines. Do NOT delete original.
- If PASS → continue.

### Phase 13: Handoff

```
=== SPLIT COMPLETE ===

Files:
  <list of created files with line counts>

Recommend: /clear then /clarify <spec-file.md>
```

Use `/clear` (not `/compact`) — clarify works best with a fresh context window, especially when split produced multiple specs that will each get their own clarify cycle.

---

## Scaling

The skill must handle files of any size. Scale resources proportionally:
- Phase 4b (semantic check): 1 agent per 1-2 sections. No limit on agent count. Skip for files <50 lines.
- Phase 4c (coverage): batch uncovered into groups of 100. 1 agent per batch. No limit.
- Phase 8 (final): same scaling as Phase 4c (or 1 agent if Phase 4c was clean — see optimization).
Never skip a verification step due to file size or token cost.

## Rules

- Act immediately — no confirmation needed (except Phase 6 pause and Phase 10 split question).
- Match the user's language in all output.
- If any phase fails — report the error, restore from backup if needed, and stop.
- **Git commits** (if git initialized):
  - **Before start**: `git add <input-files> && git commit -m "pre-cleanup: <filename>"` — snapshot before any changes
  - **After Phase 9**: `cleanup: rewrite <filename>`
  - **After Phase 12**: `cleanup: split <filename> into <N> files`

## Output Contract

The cleanup output is suitable as input for `/clarify`. The output file MUST:
- Be a valid markdown file
- Have `## ` section headers for all major topics
- Contain no unresolved markers (`[MISSING]`, `[PARTIAL]`, `[REVERSED]`, `[UNCOVERED]`)
- If split was performed: each `spec-*.md` file is an independent clarify input

## Scripts

All scripts are in `scripts/` (plugin root) or `~/.codex/skills/cleanup/scripts/` (legacy):

| Script | Purpose | Args |
|--------|---------|------|
| `verify-sort.py` | Superset check — all original lines preserved, new lines OK | `<backup> <sorted>` |
| `verify-rewrite.py` | URL presence check (with normalization) | `<source> <target>` |
| `verify-coverage.py` | Safety net — every line accounted for | `<sorted> <rewritten> <gaps>` |
| `verify-split.py` | Split verification — all lines present across output files | `<original> <output-dir>` |
