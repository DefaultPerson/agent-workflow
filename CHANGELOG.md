# Changelog

## 2.4.0

`/clarify` learns to write in the project's vocabulary, surfaces hard-to-reverse decisions as ADR offers, and exposes an optional seam to publish to an issue tracker. Both Claude and Codex variants updated in lockstep.

### Added

- **`## Writing style for the enriched spec` section** in both `skills/clarify/SKILL.md` and `skills-codex/clarify/SKILL.md`. Five rules borrowed from mattpocock/skills `grill-with-docs`: sharpen fuzzy language, be opinionated about terminology, keep FR definitions tight (one sentence in MUST/SHOULD/MAY tense), stress-test edge cases with concrete scenarios (input → expected output), cross-reference with code. Each rule has a ❌/✅ pair next to it. Applied in step 2 (questioner) and steps 3-5 (decomposition / contracts / edge cases).
- **Phase 5 ADR candidate detection** — scans the in-memory enriched spec for decisions passing all three criteria (hard to reverse + surprising without context + real trade-off). Surfaces up to 3 highest-reverse-cost candidates via AskUserQuestion / numbered TUI prompt. User options: `Create ADR-NNNN`, `Already documented (specify)`, `Skip`. Creates `docs/adr/NNNN-slug.md` with sequential numbering when approved. Cap of 3 per run prevents fatigue.
- **Phase 1 ADR sweep** — reads existing `docs/adr/*.md` if present to extract slugs and titles. Phase 5 flags conflicts between the in-memory spec and established ADRs regardless of the 3-criteria filter.
- **Phase 10 downstream offer** — after the backup disposition choice, if `~/.claude/skills/to-prd/SKILL.md` (or `~/.codex/skills/to-prd/SKILL.md` for the Codex variant) exists, a second AskUserQuestion / TUI prompt asks whether to publish via `/to-prd`. Never auto-invokes; just prints `Type /to-prd next` for explicit user intent.
- **`skills/clarify/references/adr-format.md`** — minimal ADR template (1-3 sentences, optional Status/Considered Options/Consequences), the 3 criteria for offering, four-digit sequential numbering scheme, and qualifying examples. Attribution to mattpocock/skills `grill-with-docs/ADR-FORMAT.md` (MIT) on the first line.

### Changed

- **`## Connections to other skills`** in both variants rewritten to show upstream (`mattpocock:grill-with-docs` for project-wide vocabulary / ADRs — orthogonal), downstream (`/to-prd` to tracker, `mattpocock:tdd` / `codex exec` / manual for build), and the explicit boundary (clarify does NOT touch `CONTEXT.md`; ADR offers are scoped to the spec being clarified, not project-wide).
- **README flow diagram** — added `/to-prd → issue tracker` as a downstream branch from the enriched spec; clarify box now shows `+ADRs` to reflect Phase 5 output. Example section gained step 4 demonstrating the optional `/to-prd` invocation.
- **Self-check** in both SKILL.md files gained an ADR bullet: confirmation that the step 5 ADR candidate detection ran and that existing ADRs were respected or conflicts flagged.

### Why

Two recurring quality holes in /clarify output:

1. **Fuzzy terminology.** Enriched specs picked up the input's vague words ("user", "account", "system") and propagated them. The next reader had to guess which actor or entity was meant. The mattpocock `grill-with-docs` writing rules were already battle-tested for exactly this — pulling them into a single section gives /clarify the same discipline without re-inventing the wheel.
2. **Architectural decisions buried in tasks.** Hard-to-reverse choices (DB schema, public API contract, infra/auth/messaging, security boundary) ended up inline in task descriptions. The user couldn't easily find or audit them later. The ADR seam gives those decisions a permanent, project-scoped artifact with attribution to the spec that triggered the decision.

The `/to-prd` downstream offer removes the manual step of copying the enriched spec into Linear / GitHub Issues by hand — but stays opt-in to keep tracker writes under explicit user intent.

## 2.3.0

Codex CLI support — `agent-skills` now ships dual SKILL.md variants (Claude + Codex) with shared `roles/`, `scripts/`, `references/` via install-time symlinks. Same skills, two hosts, no dual maintenance for the shared core.

### Added

- **Codex CLI variants** — `skills-codex/{cleanup,clarify,extract}/SKILL.md` (3 new files). Behaviourally identical to Claude variants; differ only in invocation idiom:
  - User gates: numbered TUI prompts instead of `AskUserQuestion` clickable radio
  - cleanup gap-detection: `codex exec -` subprocesses (sequential or `xargs -P N` parallel) instead of in-process `Agent` tool
  - clarify Phase 7.6: **symmetric cross-model consensus** — Codex variant uses `claude -p` as the cross-model reviewer (since host is Codex, Claude is "the other model") and `codex exec -` as same-family-fresh-ctx self-assessor
- **`install-codex.sh`** — shell installer that creates `~/.codex/skills/<name>/` dirs with symlinks to Codex-variant SKILL.md plus shared subdirs from Claude variant tree. Idempotent (`ln -sfn`).
- **`skills/clarify/roles/codex-self-assessor.md`** — mirror of `claude-self-assessor.md` for the Codex variant's Phase 7.6. Same categorization logic (ACCEPT / REJECT_PETTY / NEEDS_USER), reframed for Codex as the assessor.
- **README "Install in Codex CLI" section** — LLM-pasteable 5-step Bash block (clone + install + verify + check deps + restart). Self-contained, idempotent, self-verifying.

### Changed

- **`skills/clarify/roles/codex-reviewer.md`** — minor rewrite of the intro to work for both invocation paths: `codex review --uncommitted "<prompt>"` (Claude variant) and `claude -p - < prompt` with `<spec_path>` substituted (Codex variant). Same file, both modes via "Read the spec at <spec_path> from disk OR work from the working-tree diff" wording.
- **`skills/clarify/SKILL.md`** — removed `WebSearch`, `WebFetch` from `allowed-tools` (dead code, never actually invoked in workflow).

### Why

Previously `agent-skills` only worked in Claude Code. v2.0.0 deleted `skills-codex/` arguing skills were "tool-agnostic at the Bash level" — true at frontmatter level, false for body text that literally mentioned `AskUserQuestion` / `Agent` as Claude-only verbs. v2.3.0 reintroduces Codex variants — but **without dual maintenance for shared core** (roles/scripts/references symlink from Claude variant tree). Only SKILL.md bodies diverge (~20-30% of total content), with direct unambiguous invocations in each host instead of conditional "if-host-X-do-Y" prose. Phase 7.6 cross-model consensus is symmetric — each host uses the other agent as the cross-model reviewer.

Codex's native `codex plugin install` is not yet shipped (`plugins` feature flag stable but disabled); v2.3 uses symlinks. When Codex adds plugin install, this section will be replaced with a one-liner via Codex marketplace.

## 2.2.0

`/clarify` no longer makes scope decisions on its own. Step 5 now has a hard user-facing gate.

### Added

- **Step 5 "Scope-cut audit" — hard gate before the enriched spec is written to disk.** Scans the in-memory spec for deferral signals: FRs marked `MAY` with phrases `(v2)` / `(future)` / `(deferred)` / `(later)` / `(stretch goal)` / `(MVP only)`, items in a `Non-goals` section that map back to anything in the input, and features / endpoints / edge cases mentioned in the input that got silently dropped from task coverage. For every signal found, surfaces a batched AskUserQuestion (multiSelect false, up to 4 items per call, batched if more) with per-item options `Keep deferred` / `Include in v1` / `Drop entirely`. Apply user decisions before writing. If the audit finds nothing — gate silently passes.

### Changed

- **`How to do it wrong vs right` got a fourth pair: "Implicit scope reduction"** — concrete failure mode (batch user creation + admin DELETE silently tagged `MAY (v2)`) paired with the audit-gate fix.
- **`Rules` section adds Authority entry: "scope decisions belong to the user".** The model never silently demotes an input-mentioned requirement to deferred. "Looks unconventional" / "v2 would be cleaner" / "user probably didn't mean it" are not valid reasons.
- **`references/contracts.md` got a hard-rule callout** stating that `MAY + (vN)` / `(deferred)` requires user confirmation via the step 5 audit — never silent.
- **Self-check bullet added:** "Was the step 5 Scope-cut audit run, with every detected deferral confirmed by the user via AskUserQuestion?" Senior-review check now blocks silent v2-tagging.
- **Prior commitment rule mentions the audit** as a step-5 contract, not just placeholder/consistency/ambiguity.

### Why

Recurring user pain: `/clarify` would mark requirements as `MAY (v2)` or move features into `Non-goals` without asking. From the model's POV it felt like "clean spec hygiene"; from the user's POV it was silent deletion of intent. Scope cuts are a user decision, not a documentation choice. The audit makes that explicit in the workflow rather than relying on prompt discipline alone.

## 2.1.0

`/clarify` Phase 7.6 now talks to the `codex` CLI directly. The `codex-plugin-cc` Claude Code plugin is no longer a dependency.

### Changed

- **Phase 7.6 invocation switched from `codex-plugin-cc` to `codex review --uncommitted`.** The codex CLI exposes a stable, public `review` subcommand that takes a custom prompt and a target. We pass `roles/codex-reviewer.md` as the full prompt and `--uncommitted` as the scope (which covers the just-written enriched spec, staged or unstaged). Output is parsed by extracting the last fenced JSON code block — schema is enforced by the prompt itself. The full `codex-plugin-cc` plugin (~5100 lines of plugin runtime, app-server broker, background-jobs infrastructure) is no longer needed.
- **`roles/codex-reviewer.md` rewritten as a standalone prompt.** Previously it was a "focus brief" passed as `USER_FOCUS` to the plugin's adversarial-review template — the plugin supplied the adversarial framing and JSON schema. Now the file owns everything: adversarial role, substance criteria, user-intent preservation rule, scope-NOT-to-review carve-out, output format (fenced JSON block with `summary` + `findings`).
- **Detection of the codex dependency switched from `ls` filesystem-probe to `command -v codex`.** Old detection looked for `~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs` — brittle to upstream layout changes. New detection only cares whether the `codex` binary is on `$PATH`, which is a stable contract.
- **README + Prerequisites simplified.** Installing `codex-plugin-cc` via `/plugin install codex@openai-codex` is no longer required. Only `npm install -g @openai/codex` + `codex login` for users who want Phase 7.6 cross-model consensus.

### Removed

- The v2.0.3 workaround section in the SKILL.md ("Skill tool reports `codex:adversarial-review` as unavailable") — no longer relevant because we never touch the `Skill` tool for codex now.

### Why

The v2.0.3 fix used `node "$COMPANION" adversarial-review …` to bypass the `Skill` tool's `disable-model-invocation` block on the slash command. That worked but kept us coupled to the `codex-plugin-cc` plugin layout, the cache-path glob, and the plugin's internal IPC runtime. By dropping that wrapper, the dependency chain collapses to one well-known public CLI command. Single-plugin install for the user; less code in our SKILL.md; nothing to break when codex-plugin-cc reorganizes its scripts.

## 2.0.3

### Fixed

- **`/clarify` Phase 7.6 invocation of Codex adversarial review.** Previous versions called `Skill(skill="codex:adversarial-review", ...)`, which the Skill tool silently refuses because the slash command has `disable-model-invocation: true` in its frontmatter — it's a user-only command. Symptom: clarify reported "codex-plugin-cc not installed" and fell back to single-model validation, even when the plugin was installed and `/codex:adversarial-review` worked perfectly when the user typed it manually. Fix: detect the plugin by filesystem probe (`ls ~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs`) and invoke the underlying node script directly via Bash (`node <path> adversarial-review --wait --scope working-tree "<focus_brief>"`). The script itself has no model-invocation restriction. SKILL.md weakness/failure-mode sections updated to explicitly call out this trap so future maintainers don't reintroduce it.

## 2.0.2

### Changed

- **`/clarify` step 10 — backup disposition.** After approval, the skill now asks via AskUserQuestion whether to delete `<spec>.bak`. Default = delete (rollback is still possible via `git checkout HEAD -- <spec>` against the `pre-clarify: <name>` snapshot from step 6). Escape hatch = keep, for diff-compare or extra safety. Prevents `.bak` files from silently accumulating in the workspace and polluting `git status`.

## 2.0.1

Hardening pass on the v2.0 trio. No breaking API; behaviour changes only inside `/extract` output layout and `/clarify` consensus-loop hygiene.

### Changed

- **`/extract` output is now one shared `extracted/` parent per directory.** Previously each note produced its own sibling `<note>.extracted/`, so processing N notes in a directory left N folders cluttering it. New layout: `<note-dir>/extracted/<note-basename>/<slug>/...` — N notes consolidate under one `extracted/` umbrella. `.gitignore` pattern simplified from `*.extracted/` to `extracted/`.
- **`/extract` URL triage step (new Phase 2).** Heuristic-classifies bare hosts, `docs.*` subdomains and path roots, GitHub repo roots, package-registry landings, and anchor-only URLs as `reference`. A single AskUserQuestion surfaces them with three options (skip all / extract all / pick which); default is skip. Stops noise URLs (API docs, citation links, tool homepages) from polluting the output. Final report enumerates four states: `extracted` / `error` / `skipped(reference)` / `skipped(user)`.
- **`/clarify` Phase 7.6 no longer writes `<spec>.critique.<N>.json` or `<spec>.critique.<N>.rejected.md`.** Codex findings and round-by-round breakdowns live in memory during the loop and are printed to stdout at round boundaries. On consensus failure or oscillation, the full round log is dumped to stdout before user escalation. The two `.bak` and `<spec>` files are the only on-disk artifacts now.
- **`/clarify` clarified that Phase 7.6 depends on `codex-plugin-cc` (the Claude Code skill), not the bare `codex` CLI.** The CLI is a transitive dependency of the plugin, not the entry point this skill uses. Fallback to `roles/spec-validator.md` triggers when the plugin is missing (not when the CLI is).
- **`/clarify` Connections section no longer recommends downstream skills.** Removed the `mattpocock:tdd / Claude Code goal feature / manual implementation / claude -p verify` bullet list; downstream choices belong to the user, not the skill. The "Does not call other skills automatically" sentence remains.

## 2.0.0

Breaking release — removes the orchestration skills, slims `/clarify`, adds `/extract`, fixes `/cleanup` multi-file handling.

### Removed

- **Skills:** `/execute`, `/verify`, `/autoresearch`, `/ralph-loop`, `/cancel-ralph`. For independent AC verification on a clarify-produced spec, use `claude -p` in a fresh context. `autoresearch` moved to a separate repository.
- **`skills-codex/`** and **`.codex-plugin/`** — the remaining skills (`cleanup`, `clarify`, `extract`) are tool-agnostic at the Bash level; no parallel manifest needed.
- **Hooks:** `ralph-stop.py` Stop hook gone with `ralph-loop`. Orphaned `.claude/ralph-loop.local.md` state files from prior versions are safe to delete:
  ```bash
  rm -f .claude/ralph-loop.local.md
  ```

### Changed

- **`/clarify` slimmed:** spec-generation core preserved (AC format, proof commands, contracts, edge cases, risks), but execute-orchestration parts removed — `[P]` parallel markers, Stages, the Execution Order section, dependency graphs, and worker prompt templates. Output is now suitable for human consumption or the Claude Code goal feature, NOT autonomous orchestration.
- **`/clarify` Phase 7.6 added:** cross-model consensus loop driving `codex:adversarial-review` from `openai/codex-plugin-cc` against the uncommitted spec edit, iterating up to 3 rounds (configurable via `--consensus-rounds N`, `0` disables) until both Codex and Claude agree. Falls back to single-model internal validation if the plugin isn't installed or the spec is outside a git repo.
- **`/cleanup` multi-file fix:** N input files → N independent pipelines end-to-end, not one merged file. Per-source backup, per-source gap detection (4a/4b/4c), per-source final verification. The `<50-line skip` for Phase 4b now only triggers in single-file mode. `--merge` flag preserves legacy single-output behavior.
- **Template overhaul:** every SKILL.md now follows a uniform shape — `Use when ...` description format, honest weakness section, ❌/✅ contrast pairs, "letter = spirit" canon, Cialdini-framed rules, senior-review self-check before output. Role prompts moved out of SKILL.md bodies into per-skill `roles/*.md`.

### Added

- **`/extract`** — new skill. Pulls content out of every URL in a notes file:
  - YouTube via `yt-dlp` (subtitles, manual or auto-generated, en+ru)
  - Public Telegram via embed-page scrape (no auth required)
  - Generic HTML via `pandoc` (falls back to crude curl strip if pandoc missing)
  - Interactive prompt for "other" URLs (custom command escape hatch)
  - **URL triage** — heuristic-classifies bare hosts, `docs.*`, GitHub repo roots, package-registry landings, and anchor-only URLs as `reference`; surfaces them in a single AskUserQuestion before extraction begins. Default = skip all references; escape hatches: extract all, or pick which. Stops noise URLs (API docs, citation links, tool homepages) from polluting `extracted/`.
  - Annotates each successful URL in the source note with a local pointer; preserves originals; gitignores the `extracted/` output (one shared parent per directory, per-note subfolder inside — multi-file runs in the same dir consolidate, not proliferate).
