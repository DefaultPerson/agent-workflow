---
name: clarify
description: >
  Enrich a spec with tasks, acceptance criteria, edge cases, and implementation order.
  Makes any spec implementation-ready for batch execution.
  Triggers: "clarify", "/clarify", "уточни спеку", "enrich spec",
  "обогати спеку", "decompose spec"
allowed-tools: [Bash, Glob, Grep, Read, Edit, Write, Agent, WebSearch, WebFetch]
---

# Clarify Skill

Enrich a spec into an implementation-ready document with tasks, acceptance criteria, edge cases, contracts, and execution order.

## Usage

```
/clarify <spec file>
```

## Algorithm

$ARGUMENTS

Arguments: `<spec file>`

### Phase 1: Read & Analyze

1. **Validate**: If no argument — ask for file path (AskUserQuestion).
2. **Read** the spec file completely.
2.5. **Input validation**: Check spec is a valid clarify input:
   - Must be a markdown file (`.md` extension)
   - Must have at least one `## ` section header
   - Must not contain unresolved cleanup markers (`[MISSING]`, `[PARTIAL]`, `[REVERSED]`, `[UNCOVERED]`)
   - If markers found → abort: "Spec contains unresolved cleanup gaps. Run /cleanup first or remove markers."
3. **Identify**: project type, tech stack, scope, existing structure.
4. **Scan codebase** (if project directory exists):
   - Existing code, tests, configs, dependencies.
   - Use Glob/Grep to understand the current state.
5. **Scope check**: If spec describes multiple independent subsystems — flag immediately.
   - Decompose into sub-specs BEFORE continuing.
   - Each sub-spec gets its own clarify cycle.
6. **Classify spec type** (auto-detect, do NOT ask user):
   - **product** — has end users, features, UI/UX. Signals: "user", "customer", "page", "form", "dashboard", "API endpoint for users".
   - **technical** — infra, migrations, refactoring, tooling, CLI. Signals: "migrate", "refactor", "setup", "deploy", "config", "CI/CD", "monitoring", "optimize".
   - **small** — <5 tasks expected OR spec is <30 lines OR describes a single focused change.
   This classification drives format choices in Phases 3-5. State the detected type in output.
7. **Mark unknowns**: flag anything unclear with `[NEEDS CLARIFICATION]`.

### Phase 2: Clarifying Questions

**Hard gate**: Do NOT proceed to decomposition until unclear points are resolved.

- Generate up to 5 questions about unclear points.
- Present **one question at a time**, prefer multiple choice with a recommended option:
  ```
  **Q1**: What auth method should the API use?
  
  **Recommended**: B — JWT tokens (stateless, standard for REST APIs)
  
  A. Session-based (server-side sessions)
  B. JWT tokens (stateless)
  C. API keys (simple, for internal services)
  ```
- Focus on:
  - Ambiguous requirements (could be interpreted two ways?)
  - Missing constraints (performance targets, scale, auth, persistence?)
  - Priority conflicts (which feature matters most?)
  - Items flagged `[NEEDS CLARIFICATION]` in Phase 1.
- **IF spec is already clear** (no `[NEEDS CLARIFICATION]` flags, no ambiguity) → skip to Phase 3.

### Phase 3: Decompose into Tasks

Decomposition adapts to **spec type** detected in Phase 1:

**Product spec** → group by user story (US-N), each story = independently testable deliverable.
**Technical spec** → group by concern area (AREA-N: "Database", "Auth", "Monitoring").
**Small spec** → flat numbered list, no grouping.

**Task format (product):**

```markdown
### TASK-{N}: {title} [P]

**Story**: US-{M} — {story title}
**Status**: todo
**Depends on**: TASK-X, TASK-Y (or "none")
**Files**: {exact paths to create/modify}
**Leverage**: {existing code to reuse — paths to models, utils, patterns, or "none"}
**Requirements**: {FR-001, FR-003 — which requirements this fulfills}

**Acceptance Criteria**:
- [ ] AC-{N}.1: {concrete, verifiable criterion}
  Given: {initial state}
  When: {action}
  Then: {expected outcome}
  Proof: `{exact command to verify}`
- [ ] AC-{N}.2: ...

**Edge Cases**:
- {boundary condition}: {expected behavior}
- {error scenario}: {expected handling}
```

**Task format (technical):**

```markdown
### TASK-{N}: {title} [P]

**Area**: AREA-{M} — {concern area}
**Status**: todo
**Depends on**: TASK-X (or "none")
**Files**: {exact paths}
**Leverage**: {existing code to reuse, or "none"}

**Acceptance Criteria**:
- [ ] AC-{N}.1: {criterion}
  Proof: `{command}`

**Edge Cases**:
- {relevant edge case only}
```

**Task format (small):**

```markdown
### TASK-{N}: {title}

**Files**: {paths}
**Leverage**: {existing code, or "none"}
**AC**: {criterion} — Proof: `{command}`
```

**Task granularity examples:**

BAD (too broad):
- "Implement authentication system" — affects many files, multiple purposes
- "Add user management" — vague scope, no file paths

GOOD (atomic):
- "Create User model in src/models/user.py with email/password fields"
- "Add password hashing utility in src/utils/auth.py using bcrypt"
- "Create LoginForm component in src/components/LoginForm.tsx"

**Rules for acceptance criteria** (all spec types):
- **Tristate status**: PASS | FAIL | UNKNOWN — never boolean.
- **Concrete, not vague**: NOT "it works" → "GET /api/users returns 200; JSON has {id,name,email}; <200ms"
- **Each AC independently verifiable** with a concrete proof command.
- **Proof commands** must be runnable: `curl`, `pytest`, `ls`, `grep`, etc.

**Rules for tasks** (all spec types):
- **Atomic scope**: 1-3 related files per task.
- **Single purpose**: one testable outcome per task.
- `[P]` marker if task can run in parallel with others.
- **Leverage field** required — forces the agent to look for reusable code.

**Edge cases** — generate only RELEVANT categories per task (pick 2-3, not all 5):
- **Input**: empty, null, oversized, unicode, special chars
- **Boundaries**: min/max values, single element, empty collection
- **Errors**: network failure, timeout, partial failure, invalid state
- **Concurrency**: race conditions, duplicate processing
- **Security**: auth bypass, injection, rate limiting

### Phase 4: Contracts

**Skip if**: small spec, OR single-component technical spec.

Define interfaces between components:
- **API endpoints**: method, path, request/response schema with types.
- **Type definitions**: interfaces, structs, enums.
- **Event contracts**: pub/sub topics, payload schemas.
- Label each: `FR-{NNN}` (functional requirement, spec-kit format).
- Use MUST/SHOULD/MAY for requirement levels:
  ```
  - FR-001: System MUST return 401 for unauthenticated requests
  - FR-002: System SHOULD cache responses for 5 minutes
  - FR-003: System MAY support batch operations in v2
  ```

### Phase 5: Execution Order

Adapts to spec type:

**Product spec:**
```
Phase 1 (Setup):      TASK-1 [serial] — scaffolding, deps
Phase 2 (Foundation): TASK-2, TASK-3 [serial, blocks all] — core abstractions
  Checkpoint: "Core types and interfaces defined"
Phase 3 (Stories):    TASK-4 [P], TASK-5 [P], TASK-6 [P] — feature work
  Checkpoint: "US-1, US-2, US-3 each independently functional"
Phase 4 (Polish):     TASK-7, TASK-8 [serial] — integration, edge cases
  Checkpoint: "All acceptance criteria passing"
```

**Technical spec:**
```
Phase 1 (Setup):        TASK-1 [serial] — prerequisites
Phase 2 (Core Work):    TASK-2 [P], TASK-3 [P] — main changes
  Checkpoint: "Core changes applied, tests passing"
Phase 3 (Verification): TASK-4 [serial] — integration testing, validation
```

**Small spec:**
```
1. TASK-1
2. TASK-2 (depends on TASK-1)
3. TASK-3 [P with TASK-2]
```

- Build dependency graph from task `depends_on` fields.
- `[P]` markers for parallelizable tasks.
- **Checkpoints** between phases: concrete verification statement.
- **Stages** (if project is large, product type):
  - Stage 1 (MVP): core user stories only.
  - Stage 2 (v1): full story set.
  - Stage 3 (v2): optimization, polish.

### Phase 6: Spec Self-Review + Validation

**Step 1 — Self-review checklist** (before writing):

1. **Placeholder scan**: any TBD, TODO, "...", `[NEEDS CLARIFICATION]`, incomplete sections?
2. **Internal consistency**: do tasks match overview? do AC match task descriptions? do contracts match API tasks?
3. **Scope check**: focused enough for a single execution cycle? or needs further decomposition?
4. **Ambiguity check**: could any AC be interpreted two ways? could any task description mean two different things?

Fix any issues found. Loop back to relevant phase if needed.

**Step 2 — Write spec** (Phase 7), then run mechanical validation:

```bash
python3 scripts/verify-spec.py <spec-file>
```

If FAIL → fix the reported issues and re-run.

**Step 3 — Validation subagent** (after verify-spec.py PASS):

Spawn an Explore agent:
```
You are a spec validator. Read the enriched spec at [PATH].
Check:
1. Template compliance — all required sections present (Overview, Constraints, Tasks, Execution Order)
2. Task quality — each task is atomic (1-3 files), has concrete AC with proof commands
3. Consistency — tasks match overview, AC match task descriptions
4. Coverage — all items from Overview have corresponding tasks
5. No placeholders — no TBD, TODO, "...", vague descriptions

Rate: PASS | NEEDS_IMPROVEMENT | MAJOR_ISSUES
If not PASS — list specific issues with section references.
```

- **PASS** → proceed to Phase 8 (Approval).
- **NEEDS_IMPROVEMENT** → auto-fix issues, re-run verify-spec.py, re-validate.
- **MAJOR_ISSUES** → show issues to user, ask for guidance.

### Phase 7: Write Enriched Spec

1. **Backup** original: `cp <spec> <spec>.bak`
2. **Write** enriched spec to the original file.
3. **Run verify-spec.py** and validation subagent (Phase 6 Steps 2-3).

**Structure (product spec):**

```markdown
# {Project Name}

## Overview
{original spec content, preserved and cleaned up}

## Constraints
- {technical constraints}
- {performance constraints}
- {scope constraints}

## Non-goals
- {what is explicitly NOT being built}
- {what is deferred to future stages}

## User Stories
### US-1: {title}
{description, acceptance scenarios}

## Tasks
{all tasks with AC, grouped by story}

## Contracts
{API/type definitions — if multi-component}

## Execution Order
{phase-based plan with [P] markers and checkpoints}

## Risks
**High:** {risk}: mitigation: {strategy}
**Medium:** {risk}: mitigation: {strategy}

## Stages
{MVP → v1 → v2 — if large project}

## References
{links to reference files}
```

**Structure (technical spec):**

```markdown
# {Project Name}

## Overview
{original spec content}

## Constraints
## Non-goals

## Tasks
{grouped by concern area}

## Execution Order
{Setup → Core Work → Verification}

## Risks
```

**Structure (small spec):**

```markdown
# {Title}

## Overview
## Constraints
## Tasks
{flat numbered list}
```

### Phase 8: Approval

**Hard gate** — no implementation without explicit approval.

Present summary:
```
=== CLARIFY COMPLETE ===

Spec: <path>
Stories: N user stories
Tasks: M tasks (K parallelizable)
Acceptance Criteria: P total (Q with proof commands)
Edge Cases: R documented
Contracts: S functional requirements
Stages: T (if applicable)

Backup: <path>.bak
```

Ask user (AskUserQuestion):
```
Spec enriched. Review and approve, or request changes?

Options:
A. Approve — proceed to execution
B. Modify — specify which sections to change
C. Questions — ask me anything about the spec
```

- **IF Modify** → iterate on specific sections, re-run Phase 6 self-review.
- **IF Approve** → output:
  ```
  Spec approved. Recommend: /clear then /execute <spec.md>
  ```

## Rules

- Act immediately — no confirmation needed except Phase 2 questions and Phase 8 approval.
- Match the user's language in all output.
- Preserve ALL original spec content — enrich, don't replace.
- If spec references existing code — read and verify before writing tasks.
- Each AC MUST have a concrete proof command. No exceptions.
- **Git commits** (if git initialized):
  - **Before start**: `git add <spec-file> && git commit -m "pre-clarify: <filename>"` — snapshot before enrichment
  - **After Phase 7**: `clarify: enrich <spec-filename>`
- If any phase reveals the spec needs fundamental rework — report to user, don't force-enrich a broken spec.
