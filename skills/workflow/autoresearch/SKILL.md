---
name: autoresearch
description: >
  Autonomous keep-or-revert experiment loop. Iteratively optimizes any metric
  through single atomic changes, committing before verification and discarding
  failures. Two execution modes: ralph (same-session, quick iterations) and
  scheduled (cron trigger, fresh session per iteration — for multi-hour iterations).
  Triggers: "autoresearch", "/autoresearch", "auto research", "optimize metric",
  "автоисследование", "оптимизируй метрику"
allowed-tools: [Bash, Glob, Grep, Read, Edit, Write]
---

# Autoresearch

Autonomous keep-or-revert experiment loop. One atomic change per iteration — commit, verify, keep or discard.

## Usage

```
/autoresearch <goal in natural language>
/autoresearch --continue    # used by scheduled trigger, skips setup
```

$ARGUMENTS

Arguments: `<goal>` — what you want to optimize, in natural language.

---

## Phase 0: SETUP

**If `autoresearch-scratchpad.md` already exists in the project root OR `$ARGUMENTS` contains `--continue` — skip to Phase 1.**

### 0.1 Parse goal

Extract the optimization goal from `$ARGUMENTS`. If empty — ask what to optimize (AskUserQuestion).

### 0.2 Interactive setup

Ask all questions in ONE AskUserQuestion call:

1. **Scope** — which files/directories are you allowed to modify? (e.g. `src/api/`, `train.py`, `tests/`)
2. **Metric command** — what shell command measures the metric? Must output a number to stdout (e.g. `pytest -q 2>&1 | tail -1`, `wc -l src/*.py`, `ab -n 100 http://localhost:8080/ 2>&1 | grep 'Time per request'`)
3. **Guard command** (optional) — what command checks nothing is broken? (e.g. `pytest`, `npm test`, `cargo check`). Leave empty to skip
4. **Direction** — is higher better or lower better? (e.g. "higher" for accuracy, "lower" for latency)
5. **Max iterations** — how many iterations max? (default: 20)
6. **Execution mode**:
   - **`ralph`** (default) — same session, ralph-loop re-injects after each iteration. Best for quick iterations (<30 min each). Fails if session context fills before `max_iterations`.
   - **`scheduled`** — cron-triggered, fresh session per iteration. Best for long iterations (>1h each — ML training, long benchmarks, integration suites). Each iteration gets a full context window.
7. **Iteration estimate hours** (only if `mode = scheduled`) — how long does ONE iteration typically take? Used to compute cron schedule (trigger fires every `estimate + 30min buffer`).

### 0.3 Dry-run validation

Use session-specific temp files to avoid collisions with concurrent sessions:
```bash
AUTORESEARCH_TMP="/tmp/autoresearch-$(git rev-parse --short HEAD)-$$"
```

Run the metric command once. Verify a number can be extracted from output:

```bash
<metric_cmd> > ${AUTORESEARCH_TMP}-run.log 2>&1
grep -oE '[0-9]+\.?[0-9]*' ${AUTORESEARCH_TMP}-run.log | tail -1
```

If no number found — report error, ask user to fix the metric command. Do NOT proceed until a number is extractable.

### 0.4 Create experiment branch

```bash
git checkout -b autoresearch/<goal-slug>
```

Where `<goal-slug>` is the goal slugified (lowercase, spaces to dashes, special chars removed, max 40 chars).

### 0.5 Baseline

Run metric command, record the extracted number as baseline (iteration 0).

### 0.6 Create state files

**`autoresearch-scratchpad.md`** (config in frontmatter + empty working memory):

```markdown
---
goal: "<goal>"
scope: "<scope>"
metric_cmd: "<metric command>"
guard_cmd: "<guard command or empty>"
direction: "<higher_is_better or lower_is_better>"
best_metric: <baseline number>
best_commit: "<current HEAD hash>"
iteration: 0
max_iterations: <N>
mode: "<ralph or scheduled>"
iteration_estimate_hours: <number or empty if ralph>
trigger_id: "<set later for scheduled mode>"
---

## What worked

## What failed

## Next to try

## Blocked ideas
```

**`autoresearch-history.tsv`** (header + baseline row):

```
iteration	commit	metric	delta	status	description
0	<HEAD hash>	<baseline>	-	BASELINE	initial measurement
```

### 0.7 Activate execution mode

Branch on `mode` from Phase 0.2:

#### Mode A: ralph (default)

Create ralph-loop state file to enable automatic loop enforcement:

```bash
mkdir -p .claude
cat > .claude/ralph-loop.local.md << 'RALPH_EOF'
---
active: true
iteration: 1
session_id: ${CLAUDE_CODE_SESSION_ID}
max_iterations: <max_iterations from setup>
completion_promise: "AUTORESEARCH COMPLETE"
started_at: "<current UTC timestamp>"
---
Continue autoresearch. Read autoresearch-scratchpad.md for full context and current state.
RALPH_EOF
```

Proceed to Phase 1.

#### Mode B: scheduled

Compute cron schedule from `iteration_estimate_hours`:
- `1h` → every 90 minutes: `*/90 * * * *` (fallback: `30 */2 * * *`)
- `2h` → every 2.5h: `30 */2 * * *`  (approximation — cron doesn't do half-hours cleanly, round up)
- `3h` → every 3.5h: `0 */4 * * *`
- `Nh` → every `ceil(N + 0.5)` hours: `0 */X * * *` where `X = ceil(N + 0.5)`

Invoke the `schedule` skill to create a recurring trigger:

```
Use the schedule skill to create a new trigger:
- name: "autoresearch-<goal-slug>"
- cron: "<computed cron expression>"
- prompt: "/autoresearch --continue"
- working_directory: "<current project root>"
- description: "Autoresearch iteration for: <goal>"
```

After the trigger is created, record its ID in the scratchpad frontmatter (`trigger_id: <id>`) so later phases can delete it.

Print to user:
```
Scheduled mode activated.
- Trigger: autoresearch-<goal-slug>
- Schedule: <cron expression> (every <X>h)
- Estimated iterations until max: <N> × <estimate>h = <total>h
- Each iteration runs in a fresh session

To stop early: /schedule delete autoresearch-<goal-slug>
```

**Do NOT proceed to Phase 1 in scheduled mode during initial setup.** Exit cleanly — the trigger will wake up on schedule and invoke `/autoresearch --continue` to run the first iteration.

### 0.8 Proceed to Phase 1

Only in `mode: ralph`. Scheduled mode exits after 0.7.

---

## Phase 1: READ STATE

**Do this at the START of every iteration.** Re-read everything from disk — this is how you survive context compaction.

1. Read `autoresearch-scratchpad.md` — parse frontmatter for config, read body for working memory
2. Read last 20 lines of `autoresearch-history.tsv` — identify patterns (what worked, what failed, streaks)
3. Run `git log --oneline -15` — see recent experiment commits
4. Run `git diff` — working tree should be clean. If not, `git stash` to save changes, then investigate why tree was dirty

From the TSV, compute:
- **Consecutive discards**: count trailing DISCARD/CRASH/GUARD_FAIL rows
- **Diff hash**: `{ git diff; git diff --cached; git status --porcelain; } | md5sum | head -c 32` — for stall detection

---

## Phase 2: IDEATE

Choose what to try this iteration, based on state:

### Priority order:

1. **Fix crashes first** — if last status was CRASH, diagnose and fix the crash before trying new ideas
2. **Exploit** — if recent KEEPs exist, try variations of what worked (same approach, different parameters)
3. **Explore** — pick from "Next to try" in scratchpad
4. **Pivot** — if >5 consecutive discards: stop incremental changes. Re-read ALL state. Combine near-miss ideas. Try a fundamentally different approach
5. **Circuit breaker** — if diff hash is identical to previous iteration (>3 times): you are stuck in a loop making the same change. WARNING: break the pattern, try something completely different, or consider stopping

### Rules:

- **ONE atomic change per iteration.** If you catch yourself thinking "and also...", stop. That's two changes — save the second for next iteration.
- **Never modify the metric or guard commands.** That's gaming the eval, not improving the code.
- **Never modify files outside scope.** Scope is a hard boundary.

---

## Phase 3: MODIFY

Make your ONE atomic change to file(s) within scope.

---

## Phase 4: COMMIT

Commit BEFORE running verification. This enables clean rollback via `git revert` if the change fails.

```bash
git add <specific files you changed — never git add -A>
git commit -m "autoresearch: <concise description of what you changed and why>"
```

---

## Phase 5: VERIFY

Run the metric command with output redirected to /tmp (keeps raw output out of context window):

```bash
<metric_cmd> > ${AUTORESEARCH_TMP}-run.log 2>&1
echo "Exit code: $?"
```

Extract the metric number:
```bash
grep -oE '[0-9]+\.?[0-9]*' ${AUTORESEARCH_TMP}-run.log | tail -1
```

- If command exits non-zero → `status = CRASH`
- If no number extractable → `status = CRASH`
- Otherwise → proceed to Guard (if configured) or Decide

---

## Phase 5.5: GUARD (skip if no guard_cmd)

Run the guard command:

```bash
<guard_cmd> > ${AUTORESEARCH_TMP}-guard.log 2>&1
echo "Exit code: $?"
```

- If guard passes (exit 0) → proceed to Decide
- If guard fails → attempt rework (fix the issue while keeping the optimization). Max 2 rework attempts. Amend the existing commit after each rework (`git add <files> && git commit --amend --no-edit`), re-run guard
- If guard still fails after 2 reworks → `status = GUARD_FAIL`

---

## Phase 6: DECIDE

```
IF metric improved (respecting direction) AND (no guard OR guard passed):
    status = KEEP
    Update in scratchpad frontmatter:
      best_metric: <new metric>
      best_commit: <new commit hash>
ELSE:
    status = DISCARD | CRASH | GUARD_FAIL
    git revert --no-edit HEAD
```

"Improved" means:
- `direction: higher_is_better` → new metric > best_metric
- `direction: lower_is_better` → new metric < best_metric

---

## Phase 7: LOG + SCRATCHPAD

### 7.1 Append to history

Append one line to `autoresearch-history.tsv`:

```
<iteration>	<commit or REVERTED>	<metric>	<delta from best>	<status>	<description>
```

### 7.2 Update scratchpad

Increment `iteration:` in frontmatter.

Update body sections:
- **What worked**: add if KEEP
- **What failed**: add if DISCARD/CRASH/GUARD_FAIL (include why)
- **Next to try**: remove the idea you just tried, add new ideas based on results
- **Blocked ideas**: move confirmed dead-ends here

**You MUST actually modify the scratchpad body every iteration.** If the scratchpad file's content doesn't change, you're not learning from your experiments.

---

## Phase 8: EXIT CHECK

Read `iteration`, `max_iterations`, `mode`, `trigger_id` from scratchpad frontmatter.

```
IF iteration >= max_iterations:
    Print summary report:
      - Best metric achieved: X (started at Y, improvement: Z%)
      - Iterations: N total, K kept, M discarded
      - Best commit: <hash>

    IF mode == "scheduled":
      Invoke schedule skill to delete trigger <trigger_id>.
      Print: "Scheduled trigger deleted."

    Output: <promise>AUTORESEARCH COMPLETE</promise>

ELSE:
    Print: "Iteration <N>: <STATUS>. Metric: <value> (best: <best>, delta: <delta>)"

    IF mode == "ralph":
      Immediately continue to Phase 1 for next iteration.
      (If you try to stop, ralph-loop will catch the exit and re-inject the prompt.)

    IF mode == "scheduled":
      Exit cleanly. The cron trigger will wake up next cycle and invoke
      /autoresearch --continue for the next iteration. Do NOT loop in this session.
```

---

## Cleanup

When done (after `<promise>` or manual cancel):

- The experiment branch `autoresearch/<goal>` contains all successful changes
- `autoresearch-scratchpad.md` and `autoresearch-history.tsv` are on the branch as experiment record
- User can `git switch main && git merge autoresearch/<goal>` to apply results
- Or cherry-pick specific commits
- **Mode: ralph** — delete ralph-loop state: `rm .claude/ralph-loop.local.md` (if not auto-cleaned)
- **Mode: scheduled** — delete cron trigger via `schedule` skill using `trigger_id` from scratchpad (if not auto-cleaned in Phase 8)

---

## Rules

- Act immediately — no confirmation needed after setup
- Match the user's language in output
- ONE change per iteration. Always.
- Commit BEFORE verify. Always.
- Re-read state from disk at start of every iteration. Always.
- Never modify metric/guard commands
- Never modify files outside scope
- Output redirect to /tmp — never let raw command output flood context
- If any phase fails catastrophically — revert, log, continue to next iteration
