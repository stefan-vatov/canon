# Installing Project Canon

This file explains how to install Project Canon's guidance into a **target
repository** — the repo you actually want the AI agent to work in. It is
written to be followed by an AI agent or a human; the steps are the same.

Project Canon is repo-scoped agent guidance that makes an agent treat a
`canon/` directory as authoritative, current, and binding project memory.
See [README.md](README.md) for what it is and why; this file is just setup.

## TL;DR for an AI agent

If you were asked to "set up Canon" (or "install Canon") in a repository:

1. Identify the agent/harness that will run in the target repo.
2. Copy the matching file(s) from this repo's `dist/` directory into the
   target repo, at the **same path** shown below.
3. Make sure the target repo has a `canon/` directory; if it does not, create
   the Canon structure (see "After copying").
4. Do not modify anything under `dist/` — it is generated.

## Pick the file for your agent

Every artifact under `dist/` mirrors the path you copy it to. Run these from
the **target repo root**, with `CANON` pointing at a checkout of this repo:

```sh
CANON=/path/to/canon   # or a cloned copy of this repository

# Claude Code  → project memory file at repo root
cp "$CANON/dist/CLAUDE.md" ./CLAUDE.md

# Codex / any agent that reads AGENTS.md → repo root
cp "$CANON/dist/AGENTS.md" ./AGENTS.md

# Codex, full system prompt (alternative to AGENTS.md; wires system.md via config.toml)
cp -r "$CANON/dist/.codex" ./.codex

# Pi → project-local append-system prompt
mkdir -p ./.pi && cp "$CANON/dist/.pi/APPEND_SYSTEM.md" ./.pi/APPEND_SYSTEM.md
```

Copy only the one(s) for the agent you use. They all carry identical Canon
guidance, generated from a single source (`canon-core.md`).

| Agent | Copy from | To (in target repo) |
|-------|-----------|---------------------|
| Claude Code | `dist/CLAUDE.md` | `CLAUDE.md` |
| Codex (AGENTS.md) | `dist/AGENTS.md` | `AGENTS.md` |
| Codex (full system prompt) | `dist/.codex/` | `.codex/` |
| Pi | `dist/.pi/APPEND_SYSTEM.md` | `.pi/APPEND_SYSTEM.md` |

Note: Grok coding agents are not supported at this layer — they expose no
system-prompt hook, only the AGENTS.md merge layer. If you drive Grok and
want Canon, copy `dist/AGENTS.md` to `AGENTS.md` (best effort, not the
system-prompt integration Canon targets).

## After copying

Start a fresh agent session from the target repo. Then:

- **If `canon/` already exists:** the agent reads `canon/manifest.md`,
  `canon/glossary.md`, and `canon/overview.md` first, and maintains them as it
  works. Nothing else to do.
- **If `canon/` does not exist:** ask the agent to create the Canon structure
  before real work. The minimum is:

  ```text
  canon/
      overview.md     # one-paragraph living project orientation
      glossary.md     # domain term -> meaning lines
      standards.md    # binding project rules and practices
      manifest.md     # routing index of every Canon file ("read this when ...")
      decisions/      # immutable decision records, one per decision
      scratch/        # session scraps (git-ignored)
  ```

  Also add `canon/scratch/` to the target repo's top-level `.gitignore`.

On a large existing codebase, the agent should bootstrap incrementally: create
the core files now and enrich each domain as work touches it.

## Verifying (optional)

This repo ships a mechanical health check you can run against any repo that
carries a `canon/`:

```sh
uv run --script "$CANON/tools/canon-doctor.py" --root /path/to/target-repo
```

It reports structure problems, an incomplete manifest, oversized files,
un-ignored scratch, changelog-style prose, and stale domain files.

## For maintainers of this repo

`dist/` is **generated** from `canon-core.md` by `tools/build.py`; a CI
workflow regenerates and commits it on merge to `main`. To change the
guidance, edit `canon-core.md` and run `uv run --script tools/build.py` —
never edit files under `dist/` by hand. To measure a guidance change before
shipping it, see [evals/PLAYBOOK.md](evals/PLAYBOOK.md).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
