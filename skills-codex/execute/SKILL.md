---
name: execute
description: >
  Execute an enriched spec: parse tasks, spawn parallel worktree agents,
  commit per task, auto-verify, fix loop. Autonomous after clarify approval.
  Triggers: "execute", "/execute", "выполни спеку", "implement spec",
  "запусти выполнение", "run spec"
allowed-tools: [shell, glob_file_search, rg, read_file, apply_patch, agent]
---

# Execute Skill

Execute an enriched spec autonomously: parse tasks, run them in parallel worktree agents where possible, verify acceptance criteria, fix failures.

## Usage

```
/execute <spec file>
```

## Algorithm

$ARGUMENTS

Arguments: `<spec file>`

### Phase 1: Read & Parse Spec

1. **Validate**: If no argument — ask for file path.
2. **Check for resume**: If previous execution state exists (spec has tasks with `**Status**: done`):
   - Read spec → find tasks with `**Status**: todo` → resume from first incomplete stage
   - Log: "Resuming execution from stage {name} ({N} tasks remaining)"
   - Skip to Phase 3 with existing branch
3. **Read** the spec file completely.
4. **Validate format**: Run `verify-spec.py` if available:
   - Search for script: glob_file_search `**/scripts/verify-spec.py`
   - If found: `python3 <resolved-path> <spec>`
   - If not found: log warning "verify-spec.py not found, skipping format validation" and continue
   - If FAIL → abort with message: "Spec validation failed. Run /clarify first."
5. **Parse** from spec:
   - **Overview** — project description, overall goal
   - **Constraints** — what to respect
   - **Non-goals** — what NOT to build
   - **TASK blocks** — regex `### TASK-{N}`: extract title, [P], Status, depends_on, Files, Leverage, AC+Proof, Edge Cases
   - **Execution Order** — stages with task groups and checkpoints
6. **Build dependency graph** from depends_on fields.
7. **Count**: "Found N tasks in M stages. K parallelizable."

### Phase 2: Setup

1. **Create branch** (skip if resuming): `git checkout -b execute/<spec-slug>`
   - `<spec-slug>` = filename without extension, lowercase, dashes
2. **Initial commit**: commit the spec file to branch for traceability
3. **Enable auto-resume** if spec has >1 stage OR >5 tasks:
   Use Codex built-in resume for continuous execution:
   ```bash
   codex resume --last "Read <spec-path>. Find first stage with **Status**: todo tasks. Execute it (3a→3b→3c). Update task statuses in spec. If all tasks verified — report ALL DONE."
   ```
   For small specs (1 stage, ≤5 tasks): skip auto-resume.

### Phase 3: Stage Loop (plan → execute → verify → next)

Process stages from Execution Order **one at a time**. Each stage goes through the full cycle.

```
FOR each stage in Execution Order:
  3a. Plan stage (batch-style research + decomposition, NO plan mode)
  3b. Execute stage (spawn [P] workers + serial tasks)
  3c. Verify stage (independent codex exec subprocess)
  3d. Fix loop (max 3, only this stage's failures)
  3e. IF PASS → mark stage done, proceed to next
      IF still FAIL after 3 → report, stop
```

This ensures later stages build on verified foundations.

#### 3.0 Re-read Spec (start of EVERY stage)

**Re-read the spec file from disk.** Do this at the beginning of every stage iteration — not from memory, from the file. This is how you survive context compaction.

1. Read spec file completely
2. Parse task statuses: find the first stage with `**Status**: todo` tasks
3. If all tasks verified/failed → jump to Phase 4 (Report)
4. Log: "Stage {name}: {N} tasks todo, {M} done, {K} verified"

This pattern ensures correctness after context compaction or resume.

#### 3a. Plan Stage (batch-style, NO /plan)

**Do NOT enter plan mode** — spec is already approved. This is execution-time planning.

1. **Research** codebase for this stage's tasks:
   - Launch subagent(s) via `/agent` in foreground to scan files referenced in Leverage and Files fields
   - Identify current patterns, conventions, existing implementations to build on
   - Check if previous stages changed anything that affects this stage

2. **Decompose** into independent work units:
   - Verify [P] tasks are truly independent (no shared file writes)
   - Split large tasks if needed, merge trivial ones
   - Confirm each unit is implementable in isolation (worktree)

2.5. **Context budget check**: If >5 [P] tasks in this stage, consider batching into groups of 5 to avoid resource exhaustion. Minimize worker prompt size — include only the relevant task's context, not the entire spec.

3. **Build worker prompt template** for this stage:
   - Include codebase conventions discovered in step 1
   - Include verification recipe (AC proof commands + any stage-specific checks)
   - Each worker prompt must be fully self-contained

4. **Log**: "Stage {name}: {N} units planned ({K} parallel, {M} serial). Starting execution."

#### 3b. Execute Stage

**Parallel tasks ([P] marker)**:

Spawn ALL [P] tasks in this stage as worktree agents:

```bash
# For each [P] task, spawn a subagent with worktree isolation:
codex --worktree=execute/task-{N} --full-auto exec "<worker prompt>"
```

Or via `/agent` command with worktree flag, running in background.

Note: workers only need [shell, glob_file_search, rg, read_file, apply_patch]. The worker prompt explicitly scopes their work to listed Files.

As agents complete:
- **DONE** → merge worktree branch:
  ```bash
  git merge <worktree-branch> --no-edit
  ```
  - If merge succeeds → update spec on disk: find `### TASK-{N}:` section, change `**Status**: todo` → `**Status**: done`. Read the spec file, find the exact line, replace (not from memory).
  - If merge conflicts:
    1. Check conflicting files against task's **Files** field
    2. If conflicts are ONLY in this task's files → resolve using worktree version (`git checkout --theirs <file> && git add <file>`), then `git commit --no-edit`
    3. If conflicts touch OTHER tasks' files → `git merge --abort`, edit spec: status → `blocked`, log: "Merge conflict with files outside task scope: {files}"
- **DONE_WITH_CONCERNS** → merge (same conflict handling as DONE), log concerns → edit spec: status → `done`
- **BLOCKED** → log blocker, edit spec: status → `blocked`
- **NEEDS_CONTEXT** → if answerable from spec, re-dispatch with context; else edit spec: status → `blocked`

**Serial tasks (no [P] marker)**:

Execute directly (no subagent — saves context):
1. Read Leverage files
2. Implement the task
3. Run Proof commands
4. Commit: `"execute: TASK-{N} — {title}"`
5. Edit spec: `**Status**: todo` → `done`

Update status table after each completion.

#### 3c. Verify Stage (independent subprocess)

Verify runs as a **separate Codex process** — zero shared context with execute/builder.

**Pre-check**: Verify `codex` CLI is available:
```bash
command -v codex >/dev/null 2>&1
```
If not available → fall back to in-process verification (run proof commands directly in current session). Log concern: "codex CLI not found — verification ran in-process (shared context, independence not guaranteed)".

1. Write verify prompt to temp file:
   ```bash
   cat > /tmp/verify-prompt.txt << 'VERIFY_EOF'
   You are an independent verifier. You have NO context from the builder.
   
   Read the spec at: {spec-path}
   Verify ONLY these tasks: {TASK-N, TASK-M, ...}
   
   For each acceptance criterion (AC-N.M):
   1. Find the Proof: command in the spec
   2. Run it exactly as written
   3. Compare output to expected outcome from Given/When/Then
   4. Rate: PASS | FAIL | UNKNOWN
   
   For each FAIL, include:
   - Expected vs actual output
   - Affected files (from task Files field)
   - Root cause (WHY it failed)
   - Suggested fix (concrete, actionable)
   
   If all PASS, do a quick sanity check:
   - git diff --stat to see modified files
   - Scan for debug code (console.log, print, TODO, FIXME)
   - Report concerns as DONE_WITH_CONCERNS (not FAIL)
   
   Output format:
   OVERALL: PASS | FAIL | PARTIAL
   Then per-criterion table and problems section if any FAIL.
   VERIFY_EOF
   ```

2. Run as independent process:
   ```bash
   codex exec "$(cat /tmp/verify-prompt.txt)" --full-auto > /tmp/verify-result.txt 2>&1
   ```

3. Parse result from `/tmp/verify-result.txt`:
   - Extract OVERALL status
   - Extract per-criterion PASS/FAIL/UNKNOWN
   - Extract problems section (if FAIL)

**Why subprocess**: `codex exec` creates a completely separate session. The verifier:
- Has ZERO builder context (no conversation history, no worker reports)
- Reads spec from disk (written by clarify, not execute)
- Runs proof commands independently
- Cannot be influenced by execute's framing

4. **Optional: cross-model review** (if Claude Code plugin installed):
   After AC verify passes, run Claude adversarial review for code quality.
   Cross-model review is SUPPLEMENTARY — it checks code quality/design, not AC compliance.
   AC verify (`codex exec`) remains the primary gate.

#### 3d. Fix Loop (per stage, max 3)

**IF all stage AC = PASS** → mark stage done, proceed to next stage.

**IF any FAIL**:
1. For each failed criterion (from verify's problems report):
   - What went wrong (expected vs actual)
   - Which files are affected
   - Minimal fix hint
2. Fix ONLY failed tasks — do not touch passing code
3. Commit: `"fix: TASK-{N} — {criterion description}"`
4. Re-verify (3c again)
5. Max 3 iterations per stage

**IF still FAIL after 3 iterations**:
- Edit spec: mark failed tasks `**Status**: failed`
- Log: "Stage {name} FAILED after 3 fix attempts. Failures: {list}"
- DO NOT proceed to next stage (failed stage blocks dependents)
- Ask user: "Stage failed. (A) retry manually, (B) skip stage, (C) abort"

#### Worker Prompt Template

Self-contained — worker has NO parent context:

```
You are implementing a single task from a specification.

## Overall Goal
{Overview section from spec}

## Constraints
{Constraints section — respect these}

## Non-goals
{Non-goals section — do NOT build these}

## Your Task
### TASK-{N}: {title}
**Files**: {files}
**Leverage**: {leverage — read these first for patterns to reuse}
**Acceptance Criteria**:
{all AC with Proof commands}
**Edge Cases**:
{edge cases}

## Instructions
1. Read Leverage files first — understand existing patterns
2. Implement the task, modifying ONLY files listed in Files
3. Run each Proof command — they must pass
4. Commit: "execute: TASK-{N} — {title}"
5. Self-review: completeness? YAGNI? existing patterns followed?

## Report
- Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- What was implemented
- Test results (each Proof command + exit code)
- **Verification commands**: list ALL commands the verifier should run —
  AC proof commands + any additional checks discovered during implementation
  (e.g., "also run `npm test` to check no regressions")
- Concerns (if DONE_WITH_CONCERNS — what worries you)
- Blocker details (if BLOCKED/NEEDS_CONTEXT — what's missing)
```

### Phase 4: Report

```
=== EXECUTE COMPLETE ===

Spec: <path>
Branch: execute/<slug>
Stages: M total, K passed, L failed

Per-stage results:
| Stage | Tasks | Status | Fix rounds | Concerns |
|-------|-------|--------|------------|----------|
| Setup | 2 | PASS | 0 | — |
| Foundation | 3 | PASS | 1 | — |
| Stories | 5 | PASS | 0 | TASK-6: file growing large |
| Polish | 2 | FAIL | 3 (max) | — |

Failed criteria (if any):
- AC-8.1: expected 200, got 500 after 3 fix attempts

Next: review changes on branch execute/<slug>, then merge to main
```

### Auto-resume

Activated in Phase 2 for specs with >1 stage or >5 tasks.
Uses `codex resume --last` for continuous execution across context limits.
State persistence: spec file `**Status**` fields are the source of truth — resume reads spec to find next `todo` stage.

---

## Status Table Format

```
| # | Task | Stage | Mode | Status | Verify |
|---|------|-------|------|--------|--------|
| 1 | Create User model | Setup | serial | done | PASS |
| 2 | Add auth middleware | Foundation | serial | done | PASS |
| 3 | Login endpoint | Stories | [P] | running | — |
| 4 | Register endpoint | Stories | [P] | running | — |
| 5 | Integration tests | Polish | serial | pending | — |

Current stage: Stories (2/2 agents running)
```

Re-render after each agent completion or task execution.

---

## Rules

- Act immediately — spec is already approved (hard gate was in clarify).
- Match the user's language in all output.
- Worker prompts must be FULLY self-contained — workers cannot access parent context.
- Each task = one commit. Clean history for review.
- Never modify files outside the task's Files field in parallel mode.
- **[P] tasks in the same stage MUST be independent.** They run in separate worktrees and cannot see each other's changes. If TASK-A's proof depends on TASK-B's output → they CANNOT be [P]. If a [P] task fails due to missing sibling code — this is a spec error. Report it.
- If a task is BLOCKED — log and continue, don't halt the entire pipeline.
- Fix loop max 3 iterations — prevents infinite loops on unfixable issues.
- Constraints and Non-goals go into every worker prompt — prevents over-building.
- **Worktree cleanup**: At the start of Phase 3, check for orphaned worktrees from previous runs: `git worktree prune`. Also run this on any unrecoverable error before exiting.
