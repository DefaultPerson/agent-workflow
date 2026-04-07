# agent-workflow

Spec-driven development pipeline for AI coding agents. Turn messy notes into shipped code — autonomously.

Built on the [harness pattern](https://www.anthropic.com/engineering/harness-design-long-running-apps): state on disk, deterministic verification, graceful recovery from context limits.

## The Flow

```
 ┌────────┐ /cleanup ┌────────┐ /clarify ┌────────┐ /execute ┌────────┐ /verify
 │ notes  ├─────────>│  spec  ├─────────>│tasks+AC├─────────>│  code  ├────────> PASS/FAIL
 │ ideas  │          │ sorted │    ▲     │proof   │          │commits │
 │ chat   │          │verified│    │     │[P]marks│          │per task│
 └────────┘          └────────┘ approval └────────┘          └───┬────┘
                                  gate              worktree     │
                                                    agents    ◄──┘ fix loop
                                                              (max 3 rounds)
```

**cleanup** — sort, rewrite, 3-level gap detection, 100% verified content preservation. Optionally split into spec + references.

**clarify** — decompose into tasks with Given/When/Then acceptance criteria, concrete proof commands, [P]arallel markers, execution order. Approval gate: nothing runs without your OK.

**execute** — spawn parallel worktree agents per [P] task, serial for the rest. Each task = one commit. Auto-verify all AC via independent subprocess. Fix loop on failures (max 3 rounds).

**verify** — fresh context, zero builder narrative. Run every proof command, report per-criterion PASS/FAIL/UNKNOWN with evidence.

**autoresearch** — standalone autonomous optimization loop. One atomic change per iteration: commit → measure → keep or revert. Circuit breaker on stalls, pivot after 5+ failures.

**ralph-loop** — autonomous execution across context limits. Stop hook blocks exit until completion promise or max iterations. State on disk, zero context dependency. Used by execute and autoresearch automatically; also available standalone via `/ralph-loop`.

## Example

You have a 300-line brain dump — mixed notes, chat logs, URLs, half-baked ideas across 3 files:

```bash
/cleanup notes.md chat-export.md ideas.md
```

The agent sorts everything semantically, rewrites into clean structured markdown, runs 3-level gap detection (deterministic + AI + fuzzy matching) to guarantee **zero content loss**. Every URL, every number, every idea survives. Output: clean spec + backup.

```bash
/clarify spec.md
```

Asks clarifying questions one at a time, decomposes into atomic tasks with acceptance criteria:

```
### TASK-3: Create auth middleware [P]
**Files**: src/middleware/auth.ts
**AC**:
- AC-3.1: Unauthenticated request returns 401
  Proof: `curl -s -o /dev/null -w '%{http_code}' localhost:3000/api/protected` → 401
```

Approval gate — you review the enriched spec before anything runs.

```bash
/execute spec.md
```

Creates branch, spawns parallel worktree agents for [P] tasks, each commits independently. Auto-verifies all AC via isolated subprocess. Failures get 3 fix attempts. Result: clean commit history, per-stage status report.

```bash
/verify spec.md
```

Independent verification — fresh context, runs every proof command, reports evidence. The verifier has zero knowledge of how the code was built.

## Installation

### Claude Code

```bash
/plugin marketplace add DefaultPerson/agent-workflow
/plugin install agent-workflow
```

ralph-loop is included — long-running execution works out of the box.

### Codex CLI

```bash
git clone https://github.com/DefaultPerson/agent-workflow.git
cp -r agent-workflow/skills-codex/* ~/.codex/skills/
cp -r agent-workflow/hooks ~/.codex/hooks/agent-workflow
```

## Prerequisites

Git, `gh` CLI (authenticated), Python 3.10+.

## License

MIT
