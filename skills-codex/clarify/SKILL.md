---
name: clarify
description: >
  Use when you have a clean spec/notes file that needs to be made
  implementation-ready: decomposed into atomic tasks with verifiable
  acceptance criteria (Given/When/Then + shell proof commands),
  constraints, edge cases, and risk surface. Output is suitable for
  human implementation, mattpocock:tdd, or Claude Code goal feature.
  Tradeoff: slow and thorough — overkill for tasks under 1 hour. For
  freeform PRD use mattpocock:to-prd instead. Triggers: "clarify",
  "/clarify", "уточни спеку", "enrich spec", "обогати спеку",
  "decompose spec".
when_to_use: >
  The input is a cleaned-up markdown spec/notes file (probably after
  /cleanup) that captures the WHAT but not the HOW. You want to turn it
  into atomic tasks with shell-verifiable AC before handing to a builder
  (human, mattpocock:tdd, or goal feature). Do NOT use for raw chat
  exports (run /cleanup first), for already-decomposed specs, or for
  product-management-style PRDs (mattpocock:to-prd is better suited).
allowed-tools: [Bash, Glob, Grep, Read, Edit, Write]
---

# Clarify (Codex variant)

Turn a clean spec into an implementation-ready document with atomic tasks, verifiable acceptance criteria, contracts, edge cases, and risks.

This is the **Codex CLI variant**. Behaviourally identical to the Claude Code variant — only the user-interaction and cross-model-consensus invocations differ. **Phase 7.6 is symmetric**: this variant uses `claude -p` as the cross-model reviewer (because the host is Codex, so Claude is "the other model"), and `codex exec` as the same-family-fresh-ctx self-assessor. Shared resources (`roles/`, `scripts/`, `references/`) come from the Claude variant tree via install-time symlinks.

> **Letter = spirit.** If a rule blocks you from reaching the goal it was
> written for, the rule is wrong, not the goal. Don't look for a wording
> loophole — ask what the rule is protecting, and protect that.

## Usage

```
/clarify <spec.md> [--consensus-rounds N]
```

`--consensus-rounds` defaults to 3. Set it to 0 to skip the cross-model consensus loop (Phase 7.6) — only internal validation runs.

## Weaknesses and when NOT to use

- **Slow and thorough — overkill for hour-long tasks.** Decomposition + AC + edge cases + 3 consensus rounds (if claude CLI is available) take 10-15 minutes. For smaller tasks, write the AC by hand.
- **Does not work on raw chat exports or unstructured notes.** The input spec must already be sectioned with `## ` (after `/cleanup`). Otherwise — abort.
- **Not suited for product-style PRDs.** This skill forces test-first AC with proof commands; for product-management PRDs use `mattpocock:to-prd` (freeform success metrics).
- **Phase 7.6 consensus loop requires the `claude` CLI on `$PATH`** (npm `@anthropic-ai/claude-code`) since the Codex variant uses Claude as the cross-model reviewer. The skill detects it via `command -v claude` and invokes `claude -p` with the prompt from `roles/codex-reviewer.md` plus the spec content. Without `claude` on `$PATH` — fallback to internal validation (single-model `codex exec` of `roles/spec-validator.md`, weaker).
- **Not for autonomous orchestration.** The output has no `[P]` markers, Stages, or dependency graphs.
- **Non-interactive mode (`codex exec` invocation of `/clarify` itself).** The clarifying questions (step 2), Scope-cut audit (step 5), approval (step 9), and backup disposition (step 10) need user input via TUI. From `codex exec` without TTY, fail with an explicit error rather than auto-resolving. Must run from `codex` TUI.

## How to do it wrong vs right

### AC format

❌ **Wrong:** `AC-1.1: API returns correct response`
- "Correct" — who decides?
- No proof command
- Boolean (works / doesn't) — no UNKNOWN

✅ **Right:** `AC-1.1: GET /api/users returns 200, JSON with {id,name,email}, <200ms`
- Concrete numbers and fields
- Proof: `curl -w '%{time_total}' localhost:8080/api/users | jq '.[].id'`
- Tristate: PASS / FAIL / UNKNOWN (when the server isn't running)

### Task scope

❌ **Wrong:** `TASK-1: Implement authentication system`
- Touches many files
- Multiple purposes mixed
- Cannot be verified with a single command

✅ **Right:** `TASK-1: Create User model in src/models/user.py with email/password fields`
- 1 file, clear boundaries
- Atomic — one testable deliverable
- AC: `python -c "from src.models.user import User; User(email='a@b', password='x')"` runs without errors

### Cross-model consensus disagreement

❌ **Wrong:** Claude (the reviewer) returns NEEDS_IMPROVEMENT with an issue "requirement X looks unusual, suggest removing it". I apply it — I remove it.
- The user added the requirement on purpose.
- Removing it "helped me faster" but stomped the user's intent.

✅ **Right:** Issue type = NEEDS_USER (either Claude flagged it that way itself, or the Codex self-assessor reclassified). Prompt the user with both views via numbered TUI list. The user decides.

### Implicit scope reduction

❌ **Wrong:** Input spec mentions "batch user creation" and "admin role for DELETE". Mid-decomposition I think "those feel like v2 territory" — I mark them `MAY (deferred to v2)` and move on. Same for "rate limiting" which I drop into a `Non-goals` section without asking.
- The user wrote those into the input on purpose. Marking them v2 silently is the same as deleting a user-stated requirement.

✅ **Right:** Step 5 has a hard-gate "Scope-cut audit" with TUI numbered prompts. Anything that ends up tagged `MAY` + `(v2)/(future)/(deferred)/(later)/(stretch)/(MVP only)`, or goes into `Non-goals`, or drops an input-mentioned feature/edge-case — gets surfaced via TUI prompt **before** the enriched spec is written to disk. Per item: `Keep deferred` / `Include in v1` / `Drop entirely`. Nothing gets quietly downgraded.

## Writing style for the enriched spec

> Borrowed from `mattpocock:grill-with-docs` writing rules (MIT). Applies in step 2 (questioner) and steps 3-5 (decomposition / contracts / edge cases).

### Sharpen fuzzy language

When the input uses vague or overloaded terms ("user", "account", "system", "data"), propose a precise canonical term and ask which the user means via TUI prompt. Don't accept fuzzy phrasing — push for precision until the next reader can't misread it.

❌ **Fuzzy:** "Users can manage their subscriptions"
✅ **Sharp:** "Subscription owners (Customer accounts) can cancel/resume their own subscriptions; admin operators (Admin accounts) can cancel/resume on behalf of any Customer."

### Be opinionated about terminology

Pick ONE canonical term per concept and stick with it through the entire spec. If the input uses synonyms (user/account/principal), pick the most precise — usually the one mapping to a code type — and note the aliases in a brief "Terminology" preamble if ambiguity is worth flagging.

❌ **Wishy-washy:** Task uses "user" in line 3, "account" in line 7, "principal" in line 12 to mean the same thing.
✅ **Opinionated:** Pick "Customer" (maps to `src/models/customer.py`); the Terminology preamble lists "user / account / principal — all refer to the Customer entity unless explicitly qualified."

### Keep FR definitions tight

Each FR is ONE sentence in MUST/SHOULD/MAY tense. Describe what the system MUST/SHOULD/MAY do — not how. The HOW belongs in tasks; the WHAT in FR.

❌ **Long:** `FR-001: The auth middleware checks JWT validity, verifies signature against the public key, checks expiration, and returns 401 with body {error: 'invalid_token'} if any check fails.`
✅ **Tight:** `FR-001: The API MUST return 401 for tokens that are missing, expired, or have invalid signatures.`

### Stress-test edge cases with concrete scenarios

Each edge case has a concrete input + expected output. The next reader should be able to write a test from the edge case alone.

❌ **Abstract:** "Edge case: empty request body."
✅ **Concrete:** "Edge case: `POST /users` with body `{}` (no email field) → `400 { error: 'email_required' }`."

### Cross-reference with code

If the codebase has paths/types matching spec terms, read them. If code says X and spec says Y, surface the conflict in step 2 (questioner) via TUI prompt. The spec must agree with shipping code or explicitly call out the divergence as part of the change.

❌ **Stale:** Spec describes `POST /users` accepting `{email, name}`; code at `src/routes/users.py` already accepts `{email, name, phone}`. Skill writes spec as-is.
✅ **Reconciled:** Skill flags via TUI: "Spec describes a POST shape with {email, name}; code already accepts {email, name, phone}. Is the spec describing a regression, or did you forget phone?"

## Roles

Step 2 (questioner pattern) and the Phase 7.6 consensus loop (with fallback validator) — templates live in `roles/` (shared with Claude variant via install-time symlinks):

- `roles/questioner.md` — format contract for clarifying questions in step 2 (originally an `AskUserQuestion` format spec for the Claude variant — in Codex, render as numbered TUI prompts)
- `roles/codex-reviewer.md` — **full prompt** for the cross-model reviewer. **Same file used by both variants**, picks up the right mode by reading the spec_path or working-tree diff. In Codex variant: passed to `claude -p` as stdin prompt.
- `roles/codex-self-assessor.md` — Phase 7.6 self-assessor for Codex variant (mirror of `claude-self-assessor.md`). Categorizes Claude's findings as ACCEPT / REJECT_PETTY / NEEDS_USER. Run via `codex exec -` fresh subprocess.
- `roles/spec-validator.md` — fallback used inside Phase 7.6 when `claude` CLI is not available

Substitutions:

| Variable | Source |
|---|---|
| `{spec_path}` | the spec file after step 6 (write) |
| `{round}` | round counter in Phase 7.6 (1, 2, 3) |
| `{spec_path}.bak` | original spec (pre-enrichment) for coverage check |
| `{reviewer_prompt}` | full text content of `roles/codex-reviewer.md`, with `<spec_path>` substituted, passed as stdin to `claude -p` |

Invocations (Codex variant):

- **Cross-model reviewer = `claude -p`** (Claude is the "other model" since host is Codex):
  ```bash
  command -v claude >/dev/null 2>&1 || { echo "claude CLI not installed; using fallback validator"; FALLBACK=1; }
  PROMPT="$(sed "s|<spec_path>|$SPEC_PATH|g" roles/codex-reviewer.md)"
  OUTPUT="$(printf '%s' "$PROMPT" | claude -p -)"
  # Extract the last fenced JSON code block — same parser as Claude variant.
  FINDINGS="$(printf '%s' "$OUTPUT" | python3 -c '
import sys, re, json
text = sys.stdin.read()
matches = re.findall(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
print(matches[-1] if matches else json.dumps({"summary":"approve","findings":[]}))
')"
  ```
  Output schema (controlled by `roles/codex-reviewer.md`): `{summary: "needs-attention"|"approve", findings: [{file, line_start, line_end, confidence, recommendation}]}`.

- **Self-assessor = `codex exec -`** (same family as host, fresh ctx):
  ```bash
  printf '%s\n\nSpec file: %s\n\nClaude findings:\n%s' \
    "$(cat roles/codex-self-assessor.md)" "$SPEC_PATH" "$FINDINGS" \
    | codex exec -
  ```

- **Fallback validator (no `claude` CLI):**
  ```bash
  envsubst < roles/spec-validator.md | codex exec -
  ```

## What the skill does (step by step)

1. **Read and analyze the spec.** Validate (markdown, has `## ` headers, no cleanup markers `[MISSING]`/etc), classify type (product / technical / small), scan the codebase if present, flag `[NEEDS CLARIFICATION]` items. Also sweep `docs/adr/*.md` if it exists — extract slugs and titles into an in-memory list of "established decisions" for Phase 5 conflict detection. Skip silently if `docs/adr/` is absent.
2. **Ask the user what's unclear** (hard gate). Max 5 questions via numbered TUI prompts — format in `roles/questioner.md` (the file's `AskUserQuestion` semantic translates to numbered TUI list in Codex). If the spec is already clear — skip.
3. **Decompose into atomic tasks.** Format adapts to type — details in `references/task-format.md`. Main rule: each task touches 1-3 files, AC is Given/When/Then + a shell Proof command (NO `[P]` markers or Stages).
4. **Define contracts** (FR-NNN format, MUST/SHOULD/MAY). Skip if the spec is small or single-component. Details in `references/contracts.md`.
5. **Self-review checklist.** Placeholder scan, internal consistency, ambiguity check, **ADR candidate detection**, and a **hard-gate Scope-cut audit (user-facing)**.

   **ADR candidate detection** (runs before the Scope-cut audit). Scan the in-memory enriched spec (Implementation Decisions, Contracts, Tasks with architectural impact) for decisions that pass ALL THREE criteria from `references/adr-format.md`:

   1. **Hard to reverse** — DB schema change, public API contract, infra/auth/messaging choice, security boundary, major dependency lock-in.
   2. **Surprising without context** — a future reader looking at just the code will wonder "why this way?"
   3. **Real trade-off** — an explicit alternative was considered and rejected.

   Build a candidate list (max 5 — cut-off to prevent over-detection). For each candidate, score against the 3 criteria; pass only if all three are true. Surface the 3 highest-reverse-cost passes via numbered TUI prompts (one per candidate), with options:
   - **Create ADR-NNNN: `<short title>`** — write minimal ADR per `references/adr-format.md` (1-3 sentences) at `docs/adr/NNNN-slug.md`. NNNN = max existing + 1, four-digit padded. Create `docs/adr/` lazily if absent.
   - **Already documented (specify ADR-MMMM)** — the user names the existing ADR; if the in-memory spec contradicts it, surface as a conflict question (Keep spec / Revise spec to match ADR / Supersede ADR / Discuss).
   - **Skip** — ignore the candidate.

   Additionally, scan the in-memory spec against the Phase 1 ADR sweep list. If any contract/task contradicts an established ADR, surface it via TUI prompt regardless of the 3-criteria filter.

   After ADR decisions are applied, proceed to the **Scope-cut audit (user-facing)**. The audit scans the in-memory enriched spec for deferral signals:
   - FR-NNN entries marked `MAY` with phrases `(v2)`, `(future)`, `(deferred)`, `(later)`, `(stretch goal)`, `(MVP only)`, `(out of scope for now)`, `(not for now)`.
   - Items in a `Non-goals` section that map back to anything mentioned in the input.
   - Features / endpoints / edge cases present in the input that have no backing task or were silently dropped from a task's coverage.

   If any signal is found, surface a numbered TUI prompt per item (one at a time or batched) with `Keep deferred (current)` / `Include in v1` / `Drop entirely`. Apply user decisions to the in-memory spec. Loop back to step 3/4 if scope changes require re-decomposition. NEVER write to disk while scope cuts are unconfirmed. If the audit finds nothing — gate silently passes.
6. **Write the enriched spec.** Back up the original (`<spec>.bak`), write enriched into the original path. Template structures: see `references/task-format.md`.
7. **Mechanical validation.** `python3 scripts/verify-spec.py <spec>`. FAIL → fix and re-run.
8. **Cross-model consensus loop (Phase 7.6).** `claude -p` review + `codex exec` self-assess, iterate until CONSENSUS or max rounds. Details — next section. Can be skipped with `--consensus-rounds 0`.
9. **Approval gate.** Summary report + numbered TUI prompt (Approve / Modify / Questions). After approval, proceed to step 10.
10. **Backup disposition + downstream offer.** Spec is approved — `<spec>.bak` is no longer load-bearing and just clutters `git status`. First TUI prompt (backup):
    1. **Delete `<spec>.bak`** (default, recommended) — `rm <spec>.bak`. Clean workspace; rollback is still possible via `git checkout HEAD -- <spec>` (the `pre-clarify: <name>` snapshot from step 6 holds the original).
    2. **Keep `<spec>.bak`** — for further iteration or extra safety net.

    Then, **only if `/to-prd` is installed** (Glob check: `~/.codex/skills/to-prd/SKILL.md` exists), a second numbered TUI prompt (downstream):
    1. **Stay local** (default) — continue manually, with `mattpocock:tdd` on the file, or with `codex exec` driving the build.
    2. **Publish to issue tracker via `/to-prd`** — print the literal instruction `Type /to-prd next to wrap this spec as a PRD and publish.` Do NOT auto-invoke; the user types `/to-prd` themselves to keep tracker writes under explicit intent.

    If `/to-prd` is not installed, skip the downstream question — print `"Spec approved. /clear before continuing."` as before.

## Phase 7.6 — Cross-model consensus loop (Codex variant — symmetric to Claude)

After steps 6-7 (write enriched spec + verify-spec.py mechanical check), the convergence loop runs. Step 8 in the walkthrough is Phase 7.6.

The loop drives `claude -p` (cross-model reviewer) against the spec, then has Codex (in a fresh `codex exec -` invocation) categorize the findings. Two independent passes per round — Claude finds, Codex triages. The prompt sent to Claude lives in `roles/codex-reviewer.md` (same file Claude variant sends to `codex review` — it works for both via the "Read the spec at <spec_path>" wording).

```
MAX_ROUNDS = consensus_rounds_flag (default 3, 0 disables)
round = 0
reviewer_prompt = sed "s|<spec_path>|$SPEC_PATH|g" roles/codex-reviewer.md

# Detect the claude CLI on $PATH.
if bash: `command -v claude` returns empty:
  log WARNING "claude CLI not installed; falling back to single-model validation"
  result = bash: envsubst < roles/spec-validator.md | codex exec -
  → CONSENSUS or NEEDS_FIX (single round only)
  goto Step 9 (approval gate)

# The spec must be in the working tree (not yet committed). Step 6
# wrote <spec>; do NOT commit until consensus + approval.

rounds = []   # in-memory history: [{findings, assessment, applied, rejected, escalated}]

while round < MAX_ROUNDS:
  round += 1

  # 1. Cross-model review = Claude via `claude -p`. Public, stable CLI.
  claude_output = bash:
    printf '%s' "$reviewer_prompt" | claude -p -
  findings_json = extract last fenced ```json``` block from claude_output
                  (python3 one-liner with regex; on miss → {"summary":"approve","findings":[]})

  # 2. Self-assessment = Codex in fresh `codex exec -` subprocess (same family as host).
  assessment = bash:
    printf '%s\n\nSpec file: %s\n\nClaude findings:\n%s' \
      "$(cat roles/codex-self-assessor.md)" "$SPEC_PATH" "$findings_json" \
      | codex exec -

  # 3. Exit on consensus
  if findings_json.summary == "approve" and assessment.verdict == AGREE_PASS:
    → CONSENSUS, exit loop

  # 4. Process findings via assessment categorization
  applied, rejected, needs_user = [], [], []
  for each finding in findings_json.findings:
    cat = assessment.categorization[finding.id]
    if cat == ACCEPT:
      apply finding.recommendation to spec
      applied.append(finding)
    elif cat == REJECT_PETTY:
      rejected.append((finding, reason))
    elif cat == NEEDS_USER:
      needs_user.append(finding)

  print round summary: N applied, M rejected (with reasons), K queued for user
  rounds.append({findings_json, assessment, applied, rejected, needs_user})

  if needs_user not empty:
    TUI numbered prompt per issue with both views (Claude's recommendation + Codex's assessment)
    apply user decisions

  # 5. Oscillation detection
  if hash(findings_json.findings) == rounds[-3].findings_hash:
    → ESCALATE to user: "the models are stuck — your call"
    print full rounds[] summary to stdout
    break

if round == MAX_ROUNDS and not CONSENSUS:
  ESCALATE to user: "(A) approve as-is, (B) abort, (C) one more round"
  print full rounds[] summary to stdout
```

Failure modes:
- **`claude` CLI not on `$PATH`** → fallback to `roles/spec-validator.md` via `codex exec -` (single-model, weaker). Detection is via `command -v claude`. Install: `npm install -g @anthropic-ai/claude-code`.
- **Spec not in a git repository** → less critical for Codex variant (Claude reads the file directly), but still recommended for the `pre-clarify` snapshot path in step 6.
- **Claude's response has no JSON block** → python extractor returns empty `approve` result, log warning, treat round as no-op.
- **Models gang up on user intent** → `roles/codex-reviewer.md` forbids proposing removal of unusual requirements; `roles/codex-self-assessor.md` mirrors the rule when categorizing.
- **Petty disagreements** → prompt's "Scope NOT to review" section excludes style/formatting/word-choice. If any leak through → REJECT_PETTY category.
- **Oscillation** → hash comparison between rounds N and N-2, escalation.

Output schema reminder (defined by `roles/codex-reviewer.md` — same for both variants):
```json
{
  "summary": "needs-attention | approve",
  "findings": [
    {
      "file": "<spec.md path>",
      "line_start": <int>,
      "line_end": <int>,
      "confidence": <0..1>,
      "recommendation": "<concrete change>"
    }
  ]
}
```

## Outputs

- `<spec>` — overwritten with enriched version
- `<spec>.bak` — original before enrichment. Offered for deletion at step 10.

Git: `pre-clarify: <name>` (snapshot before) and `clarify: enrich <name>` (after step 6).

Phase 7.6 internals live in memory and are printed to stdout at round boundaries — no critique files written. If consensus fails or oscillates, the full round-by-round summary is dumped to stdout before user escalation.

## Connections to other skills

- **Input:** typically after `/cleanup` (sectioned markdown without `[MISSING]` markers). A manually written spec is also fine if it's structurally valid. Optionally preceded by `/extract` for URL content extraction.
- **Upstream (project-level, orthogonal):** `mattpocock:grill-with-docs` for project-wide domain modelling — it owns `CONTEXT.md` (glossary) and ADR creation in the general case. Run it once per project when vocabulary needs nailing down. `/clarify` reads existing `docs/adr/*.md` to respect prior decisions but does NOT touch `CONTEXT.md`. ADR offers in Phase 5 are scoped to decisions surfaced *by the spec being clarified*; project-wide ADRs are still grill-with-docs's job.
- **Output (on disk):** enriched spec replaces the original; `.bak` backup is kept until step 10 disposition; new ADRs (if user approved any in Phase 5) land in `docs/adr/`.
- **Output (optional, in tracker):** Step 10 offers a literal "type `/to-prd` next" instruction if `mattpocock:to-prd` is installed at `~/.codex/skills/to-prd/`. That skill wraps the enriched spec as a PRD and publishes to the configured issue tracker.
- **Downstream builders:** `mattpocock:tdd` (RED-GREEN-REFACTOR on the file or on a tracker issue), `codex exec` for autonomous, or manual implementation.
- **Cross-model dependency:** Phase 7.6 uses `claude -p` (npm `@anthropic-ai/claude-code`) as reviewer. Without it — graceful fallback to `roles/spec-validator.md` via `codex exec -`.

## Rules

### Commonality
The spec is a shared artifact. Downstream work (mattpocock:tdd, goal feature, manual builder) makes decisions from it. If you let a placeholder through, leave a vague AC, or fail to resolve a contradictory FR — the next step works from a holey map.

### Prior commitment
In step 5 (self-review) you committed to running placeholder scan + consistency + ambiguity check + **Scope-cut audit (user-facing gate)**. In step 7 — `verify-spec.py`. In step 8 — the consensus loop (or fallback). Skipping any step withdraws the basis for the final verdict.

### Authority (scope decisions belong to the user)
Marking a requirement `MAY (v2)`, moving a feature into `Non-goals`, or dropping an edge case from a task's coverage — these are scope decisions, not spec hygiene. The user wrote the input on purpose; deciding what's in v1 vs deferred is theirs, not yours. The Scope-cut audit in step 5 is a hard user-facing gate precisely so the model never makes this call alone.

### Social proof (cross-model rationale)
Phase 7.6 exists because single-model self-review is weaker. An independent second model (Claude, via `claude -p`) catches issues the first biases past. If you "skip" Phase 7.6 when claude is present, you remove the only real basis to trust the spec beyond "Codex approved its own output".

## Self-check before delivering the result

Would this spec pass review by a senior engineer who has to build the system from it? Concretely:

- Does every AC have a concrete proof command (not "it works", not "manual check")?
- No placeholders (`TBD`, `...`, `[NEEDS CLARIFICATION]`, `<insert here>`)?
- **Was the step 5 Scope-cut audit run, with every detected deferral confirmed by the user via TUI prompt?** No silent v2-tagging.
- **Was the step 5 ADR candidate detection run?** Any hard-to-reverse + surprising + real-trade-off decisions surfaced to the user (max 3); existing ADRs in `docs/adr/` respected or conflicts flagged.
- Is every task atomic — 1-3 files, single purpose, executable by an independent worker without questions to the author?
- Did Phase 7.6 pass (or was it explicitly skipped with reasoning)?
- Coverage: does every Overview item have at least one task? Does every task track back to Overview / FR?
- Was the user offered the choice to keep or delete `<spec>.bak` at step 10?

If "no" on any item — redo, don't ship.
