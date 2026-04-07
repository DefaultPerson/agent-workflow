---
name: ralph-loop
description: >
  Start an autonomous loop that survives context limits. Blocks agent exit
  until completion promise is output or max iterations reached. State on disk.
  Triggers: "ralph-loop", "/ralph-loop", "start ralph", "loop"
allowed-tools: [Bash, Read, Edit, Write]
---

# Ralph Loop

Autonomous execution loop that survives context window limits. Each iteration starts by re-reading state from disk — no dependence on conversation history.

## Usage

```
/ralph-loop <prompt or file> [--max N] [--promise TEXT]
```

- `<prompt or file>` — task description (inline text or path to .md file)
- `--max N` — max iterations before forced stop (default: 10)
- `--promise TEXT` — completion phrase (default: "RALPH COMPLETE")

## Algorithm

### 1. Parse Arguments

From `$ARGUMENTS`:
- Extract `--max N` (default 10)
- Extract `--promise "TEXT"` (default "RALPH COMPLETE")
- Everything else = prompt (or file path)

If argument is a file path (exists on disk) → read its content as the prompt.
If no arguments → ask: "What task should ralph loop on?"

### 2. Create State File

```bash
mkdir -p .claude
cat > .claude/ralph-loop.local.md << 'RALPH_EOF'
---
active: true
iteration: 1
max_iterations: {MAX}
completion_promise: "{PROMISE}"
started_at: "{UTC timestamp}"
---

## Task

{PROMPT}

## Resume Instructions

You are in a ralph loop. On each iteration:
1. Re-read this file and any relevant state files FROM DISK (not from memory)
2. Check what work remains
3. Do the next chunk of work
4. If ALL work is genuinely complete, output: <promise>{PROMISE}</promise>
5. If work remains, just stop — the loop will restart you automatically

Do NOT output the promise tag unless the task is truly finished.
RALPH_EOF
```

### 3. Confirm & Start

Output:
```
Ralph loop activated.
- Max iterations: {MAX}
- Completion promise: "{PROMISE}"
- State file: .claude/ralph-loop.local.md

Starting task...
```

Then begin executing the prompt. Work until done or context runs out — the Stop hook will catch the exit and restart you.

### 4. Completion

When the task is genuinely complete:

```
<promise>{PROMISE}</promise>
```

The Stop hook sees this, cleans up the state file, and allows exit.

## How It Works

The `hooks/ralph-stop.py` Stop hook runs every time the agent tries to stop:
- Reads `.claude/ralph-loop.local.md`
- If active and no `<promise>` found → **blocks exit** (exit code 2), increments iteration
- Agent resumes, re-reads state file, continues work
- If promise found or max iterations → allows exit, deletes state file

## User Input

```text
$ARGUMENTS
```
