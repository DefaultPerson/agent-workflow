---
name: verify
description: >
  Verify implementation against spec acceptance criteria.
  Fresh context, runs proof commands, reports per-criterion evidence.
  Triggers: "verify", "/verify", "проверь спеку", "verify spec",
  "проверь реализацию", "check implementation"
allowed-tools: [shell, glob_file_search, rg, read_file]
---

# Verify Skill

Independently verify that implementation matches spec acceptance criteria. Fresh context — no builder narrative, judge only what you see in the code.

## Usage

```
/verify <spec file>
```

## Algorithm

$ARGUMENTS

Arguments: `<spec file>`

### Phase 1: Read & Parse

1. **Validate**: If no argument — ask for file path.
2. **Read** spec file completely.
3. **Parse all TASK blocks**: extract AC-{N}.{M} + Proof commands.
4. **Count**: "Found N tasks with M acceptance criteria total."

### Phase 2: Verify Each Criterion

**Step 0 — Determine project directory** (once, before any commands):
1. If spec file is inside a git repo → `git -C "$(dirname <spec-file>)" rev-parse --show-toplevel` = project root
2. Else → `dirname <spec-file>` = project root
3. `cd` to project root before running any proof commands
4. Log: "Project directory: {path}"

For each TASK, for each AC:

1. **Run Proof command** exactly as written in the spec (from the project directory):
   ```bash
   {proof command from AC}
   ```
2. **Capture**: exit code, stdout (first 50 lines), stderr (first 10 lines).
3. **Evaluate**:
   - Check exit code (0 = success for most commands)
   - Check output matches expected outcome from Given/When/Then
   - If command not runnable (missing deps, server not started) → UNKNOWN
4. **Rate**: PASS | FAIL | UNKNOWN
5. **Record evidence**:
   ```
   AC-{N}.{M}: {criterion text}
   Status: PASS | FAIL | UNKNOWN
   Command: {proof command}
   Exit code: {N}
   Output: {summary — first meaningful line}
   ```

**Rules**:
- Run commands in the project directory (git root of spec file, or spec's parent dir if not in git — determined once in Phase 2 Step 0)
- Do NOT modify any code — read-only verification
- Do NOT trust prior claims — run every command fresh
- If a proof command requires a running server, check if it's running first. If not, note as UNKNOWN with reason
- UNKNOWN is valid — it means "can't determine", not "failed"

### Phase 3: Report

```
=== VERIFY REPORT ===

Spec: <path>
Overall: PASS | FAIL | PARTIAL
Criteria: N total, M PASS, K FAIL, L UNKNOWN

| Task | AC | Status | Evidence |
|------|----|--------|----------|
| TASK-1 | AC-1.1 | PASS | exit 0, "5 tests passed" |
| TASK-1 | AC-1.2 | FAIL | expected 200, got 404 |
| TASK-2 | AC-2.1 | PASS | file exists at src/models/user.py |
| TASK-2 | AC-2.2 | UNKNOWN | server not running, can't test endpoint |
```

**Overall rating**:
- **PASS**: all criteria are PASS, zero UNKNOWN
- **PASS_WITH_UNKNOWNS**: all verified criteria are PASS, but 1+ are UNKNOWN (< 30% of total). Report which criteria could not be verified and why
- **FAIL**: any criterion is FAIL
- **PARTIAL**: no FAIL, but >= 30% UNKNOWN — too many unverifiable criteria to trust the result

### Phase 4: Problems (MANDATORY if any FAIL — execute's fix loop depends on this)

For EACH FAIL criterion, generate a problem report. Be specific and actionable — the fixer agent uses this to make targeted corrections:

```
## Failed Criteria

### AC-{N}.{M}: {criterion text}

**Status**: FAIL
**Expected**: {from Given/When/Then — exact expected behavior}
**Actual**: {proof command stdout/stderr — what actually happened}
**Exit code**: {N}
**Affected files**: {from task Files field in spec}
**Root cause**: {1 sentence — WHY it failed, not just WHAT failed}
**Suggested fix**: {1-3 sentences — concrete, actionable steps. 
  e.g., "Register /api/users route in src/app.py line 45, add import from src/routes/users"}
```

**Rules for problems**:
- Do NOT say "check the code" — specify WHICH file, WHICH function, WHAT change
- Include the proof command output that demonstrates the failure
- Root cause must explain WHY, not just restate the failure
- Suggested fix must be actionable without reading the full codebase

---

### Phase 5: Quick Sanity Check (only if all AC PASS)

If all proof commands passed, do a lightweight code review:

1. Find the branch base and diff against it:
   ```bash
   BASE=$(git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null || git rev-list --max-parents=0 HEAD)
   git diff --stat "$BASE"..HEAD
   ```
2. For each modified file, scan for:
   - Debug code left behind: `console.log`, `print(`, `debugger`, `TODO`, `FIXME`, `XXX`
   - Hardcoded secrets: patterns like `password = "`, `api_key = "`, `secret =`
   - Commented-out code blocks (>3 lines)
3. If issues found → report as **DONE_WITH_CONCERNS** (not FAIL — AC all passed)
4. If clean → report PASS

This is a safety net, not a blocker. AC PASS = implementation correct. Sanity check = code hygiene.

---

## Independence Guarantee

Verify MUST operate with **zero builder context**:

- **Called by execute** (automatic): runs as `codex exec` subprocess — completely separate OS process, zero shared context with builder. Execute writes prompt to temp file, runs `codex exec`, parses stdout.
- **Called standalone** (manual, gold standard): user does `/clear` then `/verify spec.md` — fresh session, maximum independence.
- **Critical rule**: NEVER read conversation history, git commit messages, or worker reports as "proof" of implementation. Run the actual Proof commands from the spec and judge only current code state.

This prevents the verifier from being biased by the builder's claims. The proof-loop pattern (DenisSergeevitch/repo-task-proof-loop) emphasizes: "source of truth is current repository state and current command results, not prior chat claims."

---

## Rules

- **Read-only**: Do NOT modify any files. You are a verifier, not a fixer.
- **Run every proof command**: No skipping, no assumptions.
- **Fresh every time**: Don't cache results. Run commands anew.
- Match the user's language in all output.
- If a proof command is dangerous (rm, format, etc.) — report as UNKNOWN, do not run.
- Truncate long command outputs to first 50 lines — enough for evidence, saves context.
- UNKNOWN is not FAIL — distinguish clearly. UNKNOWN = "can't verify", FAIL = "verified wrong."
