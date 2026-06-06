<div align="center">

# Project Canon

**Project Canon is repo-scoped agent guidance for keeping AI project memory authoritative, current, and enforceable.**

![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)
![Artifact](https://img.shields.io/badge/artifact-agent_config-2f6f4e.svg)
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
- `manifest.md` signals a complete inventory the agent must consult.
- `standards.md` signals binding local rules, not casual practices.
- `glossary.md` signals precise domain language.
- `canonize` gives the agent one verb for committing durable knowledge.

The code still wins when docs and implementation disagree. Canon is authoritative
memory, not a substitute for reality.

## Quick Start

### Codex

Copy the Codex guidance file into your target repository:

```text
cp path/to/canon/AGENTS.md AGENTS.md
```

Start a new Codex session from that repository. Codex loads `AGENTS.md` before
work and includes it in the model-visible instruction chain.

If no `canon/` directory exists yet, ask Codex to create the Canon structure and
then begin work.

### Pi

Copy the project-local Pi append-system prompt into your target repository:

```text
mkdir -p .pi
cp path/to/canon/.pi/APPEND_SYSTEM.md .pi/APPEND_SYSTEM.md
```

Start a new Pi session from that repository. Pi appends `.pi/APPEND_SYSTEM.md`
to its default system prompt when the project is trusted.

If no `canon/` directory exists yet, ask Pi to create the Canon structure and
then begin work.

## Canon Structure

```text
canon/
    overview.md              # one-paragraph living project orientation
    glossary.md              # short term -> meaning lines
    standards.md             # binding project rules, patterns, and practices
    manifest.md              # hierarchical index of every Canon file
    plans/                   # provisional roadmaps and TODOs
    scratch/                 # git-ignored session scraps and handovers
    [domain]/overview.md     # focused orientation for each domain
```

Permanent Canon files describe the current system state. Completed-work notes,
handover drafts, and temporary analysis belong in `canon/scratch/`.

## Repository Scope

This repository ships two repo-scoped guidance artifacts:

```text
AGENTS.md
.pi/APPEND_SYSTEM.md
```

Agent-specific launchers, shell wrappers, and duplicate prompt files are
intentionally absent. Canon is plain repo guidance, not a command shim.

## Credit

Forked from [fjzeit/lode](https://github.com/fjzeit/lode).

## License

MIT. See [LICENSE](LICENSE).
