<div align="center">

# Project Canon

**Repo-scoped guidance that keeps AI project memory authoritative, current, and bounded.**

![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)
![Artifact](https://img.shields.io/badge/artifact-agent_config-2f6f4e.svg)
![Claude](https://img.shields.io/badge/claude-CLAUDE.md-555.svg)
![Codex](https://img.shields.io/badge/codex-AGENTS.md-555.svg)
![Pi](https://img.shields.io/badge/pi-append_system-555.svg)

</div>

Project Canon gives coding agents a maintained `canon/` directory for durable
project knowledge. The agent reads `canon/manifest.md` before broad source
exploration, loads only task-routed files, and updates affected knowledge during
authorized implementation work.

Verified code is primary evidence of current behavior. Human-owned standards
and active explicit decisions remain normative when implementation drifts.
During an authorized write task, descriptive Canon must be corrected to match
verified behavior.

## Quick start

This path installs Canon for an agent that reads `AGENTS.md`. For existing
instruction files, Codex system-prompt installation, upgrades, rollback, or
uninstall, use [INSTALL.md](INSTALL.md).

### Prerequisites

- A Git repository that will receive Canon.
- A checkout of this repository.
- An agent that reads `AGENTS.md`, or one of the supported integration files.
- [`uv`](https://docs.astral.sh/uv/) when running the doctor, build, or eval tools.

### 1. Install the guidance

Replace both paths. The first two commands canonicalize each Git root, including
linked worktrees:

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
  FRESHNESS="$(uv run --script "$CANON/tools/build.py")"
  printf '%s\n' "$FRESHNESS"
  ! printf '%s\n' "$FRESHNESS" | grep -q '^wrote'
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

The block intentionally refuses to overwrite an existing `AGENTS.md`.
Follow the managed-merge procedure in [INSTALL.md](INSTALL.md) when the target
already contains agent instructions.

Do not run the install concurrently with another process that can modify
`AGENTS.md`. Keep the printed revision with the target change; upgrades and
uninstalls use it to prove ownership.

### 2. Bootstrap the repository Canon

Start a new agent session from `$TARGET` and give it this request:

```text
Set up Project Canon in this repository. Preserve all existing project
instructions. Create the four core Canon files, decisions/ and scratch/, add
canon/scratch/ to the repository-root .gitignore, and route every permanent
Canon Markdown file except manifest.md. Inspect only enough of the repository
to write accurate core orientation; do not invent standards, policies,
decisions, rationale, or domain claims. Report anything that still needs
human input.
```

This explicit request authorizes Canon setup. The guidance does not treat
ordinary feature work, reviews, or audits as permission to create Canon.

### 3. Verify the result

```sh
uv run --script "$CANON/tools/canon-doctor.py" \
  --root "$TARGET" --strict
```

Exit `0` means no errors or warnings. Without `--strict`, warnings are printed
but do not make the command fail. Resolve or consciously migrate every warning
before using strict mode as a CI gate.

## Choose an integration

For an absent target, every generated path mirrors its default destination.
Managed merges may give the Canon-owned prompt a distinct name.

| Agent or harness | Source | Destination | Use when |
|---|---|---|---|
| Codex or another `AGENTS.md` reader | `dist/AGENTS.md` | `AGENTS.md` | Recommended general integration |
| Codex full system prompt | `dist/.codex/` | `.codex/` | Experimental; only with a pinned, verified base prompt |
| Pi | `dist/.pi/APPEND_SYSTEM.md` | `.pi/APPEND_SYSTEM.md` | Pi loads a project append-system prompt |
| Claude Code | `dist/CLAUDE.md` | `CLAUDE.md` | The target uses a project `CLAUDE.md` |

All variants contain the same generated Canon section. The full Codex system
artifact also includes `templates/codex-base.md`; its config is copied from
`templates/codex-config.toml`. Never copy a whole directory over an existing
`.codex/` or `.pi/` directory. The full Codex system prompt replaces the model
instructions file with a vendored base prompt and is not release-agnostic.
Treat it as experimental; use `AGENTS.md` unless you have synchronized and
tested that template against the exact Codex CLI release you deploy.

Project `.codex/config.toml` settings load only after Codex trusts the
repository. If you choose the full system prompt, accept the trust prompt in a
fresh session and verify the configured prompt is loaded before relying on it.

## Use Canon during normal work

There is no Canon launcher. Start the agent from the repository root and make
the normal task request. The installed guidance directs it to:

1. read `canon/manifest.md` before broad exploration;
2. load only routes whose hooks match the task and likely touched paths;
3. read `canon/standards.md` before changing code;
4. make and test the smallest authorized change;
5. retain only durable knowledge that passes the retention test; and
6. check freshness, manifest coverage, and decision immutability before ending.

Reviews, explanations, plans, status checks, and audits remain read-only unless
the user explicitly authorizes repository changes.

## Canon structure

```text
canon/
    overview.md              # short project orientation
    glossary.md              # durable domain terms
    standards.md             # human-owned normative rules
    manifest.md              # exact routes and read conditions
    decisions/               # immutable explicit human decisions
    plans/                   # provisional plans, when needed
    scratch/                 # ignored notes and handovers
    [domain]/overview.md     # focused descriptive knowledge
```

Every permanent Canon Markdown file except `manifest.md` has one exact manifest
route. Descriptive domain files declare repository-relative `sources` and an
immutable pre-change `verified` commit. Permanent files stay at most 250 lines
and 64 KiB. Temporary analysis and completed-work notes belong in
`canon/scratch/`.

## Validate a repository

Run the doctor from the Canon checkout or with an absolute script path:

```sh
uv run --script tools/canon-doctor.py --root /absolute/path/to/target
uv run --script tools/canon-doctor.py --root /absolute/path/to/target --json
uv run --script tools/canon-doctor.py --root /absolute/path/to/target --strict
```

The doctor checks required structure, exact and contained manifest routes,
missing or unsafe routed files, line and byte caps, ignored scratch state,
changelog-style prose, and Git-derived freshness. Errors always return
nonzero. Warnings return nonzero only with `--strict`.

## Maintain this repository

`canon-core.md` is the source of the shared Canon section. Generated files
under `dist/` must not be edited directly.

After changing `canon-core.md` or a template:

```sh
uv run --script tools/build.py
uv run --script tools/build.py
uv run python -m unittest discover -s tests -v
git diff --check
```

The second build should report every artifact as `fresh`. Review the generated
diff in the same change as its source, then require the deterministic suite to
finish with `OK`.

To evaluate a guidance change with agents, follow [evals/README.md](evals/README.md).
To run an adoption round, use [evals/PLAYBOOK.md](evals/PLAYBOOK.md).

## Documentation map

- [INSTALL.md](INSTALL.md) — install, merge, verify, upgrade, rollback, and uninstall.
- [canon-core.md](canon-core.md) — exact agent operating instructions.
- [evals/README.md](evals/README.md) — eval reference, commands, artifacts, and troubleshooting.
- [evals/PLAYBOOK.md](evals/PLAYBOOK.md) — current improvement and adoption runbook.
- [evals/BASELINES.md](evals/BASELINES.md) — durable experiment and adoption history.
- [evals/RESEARCH.md](evals/RESEARCH.md) — research basis and untested frontiers.

## Repository scope

```text
canon-core.md                  # source of the shared Canon section
templates/                     # Codex base prompt and static config
dist/                          # generated agent artifacts
tools/build.py                 # artifact generator
tools/canon-doctor.py          # repository validator
evals/                         # guidance measurement harness
tests/                         # deterministic regression suite
```

Consumer use needs Git and the selected agent. The maintenance tools use `uv`
and Python standard-library code. Agent evaluations additionally require the
selected agent CLI, explicit model configuration, and an execution sandbox;
see the eval prerequisites before running them.

## Credit

Forked from [fjzeit's original concept](https://github.com/fjzeit/lode).

## License

MIT. See [LICENSE](LICENSE).
