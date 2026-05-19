# agent-skills

Three focused skills for the pre-implementation half of an AI coding workflow: losslessly reorganize messy notes, pull content out of links, decompose specs into atomic tasks with verifiable acceptance criteria.

## The Flow

```
 ┌────────┐  cleanup  ┌──────────┐  clarify  ┌─────────┐  extract  ┌────────────┐    →   /to-prd → issue tracker
 │ notes  ├──────────>│  clean   ├──────────>│ atomic  ├──────────>│  tasks +   │    →   TDD (red/green/refactor)
 │  with  │           │ markdown │           │ tasks + │           │  offline   │    →   Claude Code goal feature
 │ links  │           │ document │           │ AC with │           │   link     │    →   manual implementation
 └────────┘           └──────────┘           │  proof  │           │  content   │    →   claude -p for AC verify
                                             │commands │           └────────────┘
                                             │+ADRs    │
                                             └─────────┘
                                                  ▲
                                                  │
                                      Codex+Claude consensus
                                        (Phase 7.6 in clarify)
```

The `/to-prd` seam (if installed separately) wraps the enriched spec as a PRD and publishes to the configured issue tracker — opt-in, never auto-invoked.

## Skills

- **`/cleanup`** — losslessly reorganize a messy notes/plan/chat dump into a clean sectioned markdown file. Three-level gap detection (deterministic URL check + per-section semantic agents + fuzzy coverage net) proves nothing was lost. Multi-file input → multi-file output (per-source pipelines, not merged).
- **`/extract`** — pull content out of every URL in a notes file (YouTube subtitles via yt-dlp, public Telegram via embed-page scrape, HTML via pandoc/curl). Replaces each URL with a local pointer, preserves originals, gitignores extracted content.
- **`/clarify`** — turn a clean spec into an implementation-ready document: atomic tasks with Given/When/Then acceptance criteria, shell-runnable proof commands, contracts (FR-NNN with MUST/SHOULD/MAY), edge cases, risks. Reads existing `docs/adr/*.md` and offers to write new ADRs for hard-to-reverse decisions surfaced during decomposition (cap 3 per run, all 3 criteria must hold). Cross-model consensus loop with Codex (optional) catches issues single-model self-review misses.

Each skill follows the same template — `description` states triggers and tradeoffs (not algorithm), honest weakness section up front, ❌/✅ contrast pairs, "letter = spirit" canon, Cialdini-framed rules, senior-review self-check before output.

## Example

```bash
# 1. Reorganize the chaos into a clean sectioned doc with proven coverage
#    (nothing dropped, every URL preserved).
/cleanup research-notes.md

# 2. Pull content out of every URL in the cleaned doc (YouTube transcripts,
#    Telegram posts, articles). Original URLs stay; pointers to local copies
#    appear next to each one.
/extract research-notes.md

# 3. Decompose into atomic tasks with verifiable AC. Phase 7.6 invokes
#    `codex review --uncommitted` (codex CLI, if installed) against the
#    uncommitted spec edit and iterates up to 3 rounds until consensus.
#    Phase 5 offers ADR creation for hard-to-reverse decisions.
/clarify research-notes.md

# 4. (Optional) If `/to-prd` is installed, publish the enriched spec to
#    your issue tracker (e.g. Linear, GitHub Issues) wrapped as a PRD.
/to-prd
```

## Installation

```bash
/plugin marketplace add DefaultPerson/agent-skills
/plugin install agent-skills@agent-skills
```

Optional (for `/clarify` Phase 7.6 cross-model consensus): install the [Codex CLI](https://github.com/openai/codex):

```bash
npm install -g @openai/codex
codex login   # one-time auth
```

`/clarify` drives `codex review --uncommitted` directly — no companion Claude Code plugin needed. Without the CLI (or when the spec isn't in a git repo, since `--uncommitted` operates on the working tree), `/clarify` falls back to single-model internal validation with a warning.

## Install in Codex CLI

Codex CLI's native `codex plugin install` is not yet operational (the `plugins` feature flag is `stable` but disabled by default). Until it ships, use the symlink installer below.

**For an LLM agent: copy the entire block below into your Codex session — the agent will install and verify.**

```bash
# 1. Clone (or update) the plugin repo locally.
PLUGIN_ROOT="${HOME}/.local/share/agent-skills"
git clone https://github.com/DefaultPerson/agent-skills.git "$PLUGIN_ROOT" 2>/dev/null \
  || git -C "$PLUGIN_ROOT" pull --ff-only

# 2. Run the Codex installer (creates per-skill dirs in ~/.codex/skills/
#    with symlinks to Codex-variant SKILL.md + shared roles/scripts/references).
bash "$PLUGIN_ROOT/install-codex.sh"

# 3. Verify each skill has SKILL.md plus shared subdirs.
for s in cleanup clarify extract; do
  echo "--- $s ---"; ls -la "$HOME/.codex/skills/$s/"
done

# 4. For /clarify Phase 7.6 cross-model consensus, ensure both CLIs are on PATH.
#    Codex variant uses `claude -p` as the cross-model reviewer (Claude is the
#    "other model" since host is Codex). The Claude variant uses `codex review`.
command -v codex  >/dev/null || echo "MISSING codex:  npm install -g @openai/codex"
command -v claude >/dev/null || echo "MISSING claude: npm install -g @anthropic-ai/claude-code"

# 5. Restart your codex session — skills load on startup.
echo "Done. Three skills installed: /cleanup, /clarify, /extract."
```

When Codex ships native `codex plugin install`, this section will be replaced with a one-liner. Track [openai/codex](https://github.com/openai/codex) for status.

## Prerequisites

- **Required:** Git, `bash`, `jq`, `python3`.
- **`/extract` deps** (probed at runtime, install prompt if missing): `yt-dlp` (YouTube subtitles), `pandoc` (HTML — optional, falls back to crude curl). Telegram works with just `curl`.
- **`/clarify` Phase 7.6 optional:**
  - In **Claude Code**: [Codex CLI](https://github.com/openai/codex) (`npm install -g @openai/codex`) — Claude variant uses `codex review --uncommitted` as the cross-model reviewer.
  - In **Codex CLI**: [Claude Code CLI](https://docs.claude.com/en/docs/claude-code) (`npm install -g @anthropic-ai/claude-code`) — Codex variant uses `claude -p` as the cross-model reviewer.
  - Spec must live in a git repo for working-tree review; otherwise the loop falls back to internal `spec-validator` (single-model, weaker).

Release history: see [CHANGELOG.md](CHANGELOG.md).

## License

MIT
