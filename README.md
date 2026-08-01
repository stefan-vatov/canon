<div align="center">

# Project Canon

**Compact architectural laws and product invariants for coding agents.**

![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)
![Artifact](https://img.shields.io/badge/artifact-agent_config-2f6f4e.svg)
![Claude](https://img.shields.io/badge/claude-CLAUDE.md-555.svg)
![Codex](https://img.shields.io/badge/codex-AGENTS.md-555.svg)
![Pi](https://img.shields.io/badge/pi-append_system-555.svg)

</div>

Project Canon gives repository-scoped coding agents a small, durable record of
the rules that must survive implementation churn:

> Canon explains why the system is shaped this way and what must remain true.
> Code, schemas, package manifests, build graphs, and generated reports explain
> where the implementation currently lives.

Canon is not a manually synchronized mirror of the repository. File moves,
renames, helper extraction, test refactors, and new instances of an established
pattern should normally produce `Canon impact: none`.

## What Canon owns

Canon is authoritative for:

- package ownership and dependency direction;
- public contract and user-visible behavior;
- persistence, migration, retry, timeout, interruption, and lifecycle policy;
- security, privacy, and platform guarantees;
- required validation at risky boundaries;
- explicit architectural decisions and supplied rationale.

Canon does not maintain:

- source-file, export, class, helper, schema, or test inventories;
- current file locations, line numbers, barrel contents, or test shards;
- temporary migration status or completed-work summaries;
- facts already expressed by types, manifests, schemas, build graphs, or
  generated reports.

Documentation states the requirement. Tests and policy checks prove it. Code
supplies the implementation.

## Repository Canon shape

```text
canon/
    manifest.md          # compact concern-to-page router
    standards.md         # project-wide architectural laws
    architecture/        # focused subsystem and product invariants
    decisions/           # immutable explicit human decisions
    scratch/             # ignored, temporary, non-authoritative work
```

Only `manifest.md` and `standards.md` are required files. Canon grows when a
durable invariant needs an owner, not whenever the source tree grows.

Every new permanent page uses compact metadata:

```yaml
---
status: normative
scope:
  - "@example/persistence"
validation:
  - tests/architecture/test_dependency_policy.py
related:
  - ./runtime-services.md
---
```

`status` is `normative`, `reference`, `draft`, or `deprecated`. Normative pages
must be routed from the manifest. Legacy `sources` lists and `verified` commit
hashes are rejected: they created documentation churn without proving truth.
Validation entries name existing regular, non-symlink files with
repository-root-relative paths, never paths relative to the Canon page.
Successor decisions use `supersedes` as a non-empty list of local predecessor
decision paths, while current-state architecture pages state the active rule
or value explicitly. Predecessors remain manifest-routed as clearly labeled
historical decision context.

## Canon impact

Every implementation change gets one classification:

| Classification | Meaning | Canon action |
|---|---|---|
| No impact | Guarantees, ownership, contracts, and validation stay unchanged | Do not edit Canon |
| Clarification | The intended rule is unchanged but materially ambiguous | Clarify the owning rule |
| Change | A durable guarantee, boundary, behavior, risk policy, or required check changes | Update the smallest owning page |

Before editing Canon, finish: `Canon changed because the system must now
guarantee that ...`. If the reason is only that a file or symbol moved, leave
Canon alone.

When a guarantee changes, record its complete durable contract: supplied
boundaries, invalid cases, error behavior, numeric limits, exceptions, and
negations. When a required policy is absent, report the gap instead of
guessing, implementing, testing, or canonizing a value.

## Quick start

This installs the generated `AGENTS.md` integration into a repository that
does not already have one. For managed merges, upgrades, rollback, uninstall,
or full Codex system-prompt installation, use [INSTALL.md](INSTALL.md).

### Prerequisites

- A Git repository that will receive Canon.
- A clean checkout of this repository.
- An agent that reads one of the supported integration files.
- [`uv`](https://docs.astral.sh/uv/) for build and validation tools.

### 1. Install the guidance

Replace both paths:

```sh
CANON="$(git -C /absolute/path/to/canon rev-parse --show-toplevel)" || exit 1
TARGET="$(git -C /absolute/path/to/target-repository rev-parse --show-toplevel)" || exit 1
export CANON TARGET

(
  set -eu
  test -f "$CANON/dist/AGENTS.md"
  test -z "$(git -C "$CANON" status --porcelain --untracked-files=all)"
  uv run --script "$CANON/tools/build.py" >/dev/null
  test -z "$(git -C "$CANON" status --porcelain --untracked-files=all)" || {
    echo "generated Canon artifacts were stale" >&2
    exit 1
  }
  CANON_REF="$(git -C "$CANON" rev-parse HEAD)"
  if test -e "$TARGET/AGENTS.md" || test -L "$TARGET/AGENTS.md"; then
    echo "refusing existing target: $TARGET/AGENTS.md" >&2
    exit 1
  fi
  cp "$CANON/dist/AGENTS.md" "$TARGET/AGENTS.md"
  cmp -s "$CANON/dist/AGENTS.md" "$TARGET/AGENTS.md"
  printf 'Record installed Canon revision: %s\n' "$CANON_REF"
)
```

The block refuses to overwrite an existing instruction file. Follow the
managed-merge procedure in [INSTALL.md](INSTALL.md) when one already exists.

### 2. Bootstrap the repository Canon

Start a fresh agent session from the target repository:

```text
Set up Project Canon in this repository. Preserve all existing instructions.
Create canon/manifest.md with status: reference and canon/standards.md with
status: normative. Create canon/architecture/, canon/decisions/, and
canon/scratch/, and add canon/scratch/ to the repository-root .gitignore.
Do not invent standards, decisions, architecture, rationale, or domain terms.
Do not create source-file inventories or sources/verified metadata. Report
anything that still needs human input.
```

### 3. Verify it

```sh
uv run --script "$CANON/tools/canon-doctor.py" \
  --root "$TARGET" --strict
```

Exit `0` means the structure, metadata, normative routes, links, validation
references, scratch boundary, and size limits pass.

## Supported integrations

| Agent or harness | Source | Default destination |
|---|---|---|
| Codex or another `AGENTS.md` reader | `dist/AGENTS.md` | `AGENTS.md` |
| Claude Code | `dist/CLAUDE.md` | `CLAUDE.md` |
| Pi | `dist/.pi/APPEND_SYSTEM.md` | `.pi/APPEND_SYSTEM.md` |
| Codex full system prompt | `dist/.codex/` | `.codex/` |

All variants contain the same generated Canon contract. The full Codex prompt
also vendors `templates/codex-base.md` and is release-sensitive; prefer
`AGENTS.md` unless you test against the exact Codex CLI release.

## Normal agent workflow

The installed guidance directs an agent to:

1. read `canon/manifest.md` and only the relevant routed pages;
2. exclude `canon/scratch/` from normal context;
3. identify applicable invariants and validation;
4. implement and test the requested work;
5. classify Canon impact and edit Canon only for a clarification or change;
6. report `Canon impact: none` or the exact invariant updated.

The manifest is a router, not a catalog. Each route has exactly one local
Markdown link and an explicit, non-empty `read when ...` or `read for ...`
condition. A well-routed agent should usually load one or two Canon pages,
while loading any additional routed authority that jointly governs the task
instead of treating the usual count as a cap.

## Validate and compact

The doctor is dependency-free Python:

```sh
uv run --script tools/canon-doctor.py --root /absolute/path/to/target
uv run --script tools/canon-doctor.py --root /absolute/path/to/target --json
uv run --script tools/canon-doctor.py --root /absolute/path/to/target --strict
uv run --script tools/canon-doctor.py --root /absolute/path/to/target \
  --baseline <trusted-pre-migration-commit> --strict
```

Without `--baseline`, existing decisions are still checked against `HEAD` for
byte immutability, but historical records with invalid metadata, stale
links, or oversize bodies are not grandfathered.
Supply `--baseline` only with the reviewed commit recorded before migrating a
legacy Canon; keep that commit pinned in subsequent validation.

Use [`$compact-canon`](.codex/skills/compact-canon/SKILL.md) for an on-demand
audit or migration of an overgrown Canon. It identifies repeated rules,
implementation inventories, legacy metadata, routing gaps, and reconstructible
prose while preserving human standards and immutable decisions. Ask for a
`dry run` to receive candidates without changing files.

## Maintain this repository

`canon-core.md` is the source of every generated agent artifact under `dist/`.
After changing the core or a template:

```sh
uv run --script tools/build.py
uv run --script tools/build.py
PYTHONDONTWRITEBYTECODE=1 \
  uv run python -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
```

The second build must report every artifact as `fresh`.

## Documentation

- [INSTALL.md](INSTALL.md) — safe installation, merge, upgrade, rollback, and
  uninstall procedures.
- [canon-core.md](canon-core.md) — exact shared agent contract.
- [evals/README.md](evals/README.md) — evaluation harness and scenarios.
- [evals/PLAYBOOK.md](evals/PLAYBOOK.md) — improvement and adoption runbook.
- [evals/BASELINES.md](evals/BASELINES.md) — compact evaluation adoption ledger.

Project Canon is MIT licensed and originated as a fork of
[fjzeit's concept](https://github.com/fjzeit/lode).
