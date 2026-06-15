<div align="center">

# Project Canon

**Project Canon is repo-scoped agent guidance for keeping AI project memory authoritative, current, and enforceable.**

![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)
![Artifact](https://img.shields.io/badge/artifact-agent_config-2f6f4e.svg)
![Claude](https://img.shields.io/badge/claude-CLAUDE.md-555.svg)
![Codex](https://img.shields.io/badge/codex-AGENTS.md-555.svg)
![Pi](https://img.shields.io/badge/pi-append_system-555.svg)

</div>

Project Canon turns project memory into a maintained `canon/` directory that the
agent must read before broad code exploration and update after meaningful
changes.

## Why Canon

AI coding sessions drift when project memory reads like optional notes. Canon makes
the memory layer feel binding:

- `canon/` signals source-of-truth project knowledge.
- `manifest.md` is a routing index — every entry says when to read that file,
  so memory informs context instead of crowding it out.
- `standards.md` signals binding local rules, not casual practices.
- `glossary.md` signals precise domain language.
- `decisions/` keeps durable decisions with their rationale and rejected
  alternatives, immutable once written.
- Freshness frontmatter (`sources` + `verified`) on every domain file makes
  staleness detectable instead of discoverable-by-accident.
- `canonize` gives the agent one verb for committing durable knowledge.

The code still wins when docs and implementation disagree. Canon is authoritative
memory, not a substitute for reality.

## Quick Start

All guidance artifacts are generated from the single source of truth,
[`canon-core.md`](canon-core.md). Copy the one matching your agent into your
target repository. For step-by-step setup instructions an AI agent can follow
directly, see [INSTALL.md](INSTALL.md).

### Claude Code

```sh
cp path/to/canon/dist/CLAUDE.md CLAUDE.md
```

### Codex

```sh
cp path/to/canon/dist/AGENTS.md AGENTS.md
```

Alternatively, copy the full Codex system prompt (base prompt plus the Canon
section), which is wired via `config.toml`'s `model_instructions_file`:

```sh
cp -r path/to/canon/dist/.codex .codex
```

### Pi

```sh
mkdir -p .pi
cp path/to/canon/dist/.pi/APPEND_SYSTEM.md .pi/APPEND_SYSTEM.md
```

Every artifact under `dist/` mirrors the path you copy it to. Start a new
session from the target repository. If no `canon/` directory exists yet, ask
the agent to create the Canon structure and then begin work.

## Canon Structure

```text
canon/
    overview.md              # one-paragraph living project orientation
    glossary.md              # short term -> meaning lines
    standards.md             # binding project rules, patterns, and practices
    manifest.md              # routing index of every Canon file
    decisions/               # immutable decision records, one per decision
    plans/                   # provisional roadmaps and TODOs
    scratch/                 # git-ignored session scraps and handovers
    [domain]/overview.md     # focused orientation per domain, with
                             # sources/verified freshness frontmatter
```

Permanent Canon files describe the current system state. Completed-work notes,
handover drafts, and temporary analysis belong in `canon/scratch/`.

## Tooling

- `tools/build.py` — regenerates all guidance artifacts from `canon-core.md`.
  Run it after any core edit; never edit the generated files.
- `tools/canon-doctor.py` — mechanical health checks for any repo carrying a
  Canon: structure, manifest completeness and dead links, line caps,
  scratch git-ignored, changelog-style smell, and git-based staleness
  detection of domain files. Suitable for CI or pre-commit:

  ```sh
  uv run --script path/to/canon/tools/canon-doctor.py --root . [--json]
  ```

- `evals/` — a measurement harness for the guidance itself: scenario-based
  agent evals (including a ten-session memory chain with hidden holdout
  tests) and a hill-climbing optimizer. See [evals/README.md](evals/README.md),
  or [evals/PLAYBOOK.md](evals/PLAYBOOK.md) to run or resume the improvement
  loop.

Requires [uv](https://docs.astral.sh/uv/); everything else is stdlib.

## Repository Scope

```text
canon-core.md                  # the single source of truth for the guidance
templates/                     # build inputs (codex base prompt + config)
dist/                          # generated artifacts — copy these into a repo
    CLAUDE.md                  #   Claude Code variant
    AGENTS.md                  #   Codex / AGENTS.md variant
    .pi/APPEND_SYSTEM.md       #   Pi variant
    .codex/system.md           #   full Codex system prompt
    .codex/config.toml         #   wires system.md (static)
tools/                         # build + doctor utilities
evals/                         # guidance measurement harness
```

`dist/` is regenerated from `canon-core.md` by `tools/build.py` (and kept in
sync on `main` by a CI workflow); never edit it by hand. Agent-specific
launchers and shell wrappers are intentionally absent — Canon is plain repo
guidance plus maintenance utilities, not a command shim.

## Credit

Forked from [fjzeit's original concept](https://github.com/fjzeit/lode).

## License

MIT. See [LICENSE](LICENSE).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
