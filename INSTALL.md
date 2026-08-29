# How to install and maintain Project Canon

This guide installs Project Canon in a target repository and covers the full
consumer lifecycle: first install, safe merges, the `compact-canon` maintenance
skill, bootstrap, verification, upgrade, rollback, and uninstall.

Project Canon is repository-scoped agent guidance. Install only the integration
for the agent you use, then start a new agent session from the target repository.

An installation has two parts: the generated instruction file every session
loads, and the `compact-canon` skill that audits and compacts an overgrown
`canon/` on demand. Install both — the skill lives only in this checkout, so a
target that skips it has no compaction path once the checkout is gone.

## Prerequisites

- A trusted, clean checkout of this Project Canon repository at a commit or
  tag you can record.
- A target Git repository.
- A POSIX-compatible shell and Python 3.10 or later.
- [`uv`](https://docs.astral.sh/uv/) for `canon-doctor.py` verification.
- A clean or understood target worktree. The commands below do not stage or
  commit changes.
- Exclusive access to the target integration paths while each command runs;
  do not install, upgrade, roll back, or uninstall concurrently.

Set these variables once in the shell where you will run the commands. Replace
both example paths:

```sh
CANON="$(git -C /absolute/path/to/project-canon rev-parse --show-toplevel)" || exit 1
TARGET="$(git -C /absolute/path/to/target-repository rev-parse --show-toplevel)" || exit 1

test -f "$CANON/dist/AGENTS.md" || exit 1
test -f "$CANON/tools/canon-doctor.py" || exit 1
test -f "$CANON/tools/build.py" || exit 1

test -z "$(git -C "$CANON" status --porcelain --untracked-files=all)" || {
  printf 'Canon checkout is dirty; refusing to rebuild or install\n' >&2
  exit 1
}
uv run --script "$CANON/tools/build.py" >/dev/null || exit 1
test -z "$(git -C "$CANON" status --porcelain --untracked-files=all)" || {
  printf 'Generated artifacts were stale at the selected revision\n' >&2
  exit 1
}
BUILD_OUTPUT="$(uv run --script "$CANON/tools/build.py")" || exit 1
printf '%s\n' "$BUILD_OUTPUT"
if printf '%s\n' "$BUILD_OUTPUT" | grep -q '^wrote'; then
  printf 'Generated artifacts did not stabilize after rebuild\n' >&2
  exit 1
fi
CANON_REF="$(git -C "$CANON" rev-parse HEAD)" || exit 1
git -C "$TARGET" status --short || exit 1
printf 'Installing Canon revision %s\n' "$CANON_REF"
```

Record `CANON_REF` in the target change or pull request. Safe whole-file
upgrades and removals use it to prove that a Canon-owned file was not modified
locally.

## Choose one integration

| Agent | Source artifact | Target path |
|---|---|---|
| Claude Code | `dist/CLAUDE.md` | `CLAUDE.md` |
| Codex, Pi, or another `AGENTS.md` reader | `dist/AGENTS.md` | `AGENTS.md` |

The always-loaded guidance ships exclusively as repository instruction files.
Pi 0.83 and later loads a project `AGENTS.md` natively, so Pi uses the
`AGENTS.md` integration with no Pi-specific file. For tools not listed here,
use `AGENTS.md` only when that tool's current documentation says it loads the
file.

Both generated artifacts end with the small, removable provenance line
`_Remembered with [Project Canon](https://agentcanon.dev)._`. Whole-file
installs and managed merges preserve it as part of the Canon-owned payload.

The `compact-canon` skill is installed separately, into whichever skill
directories your agents read — one integration file, but as many skill copies
as the target needs; see [Install the `compact-canon`
skill](#install-the-compact-canon-skill).

Every `dist/` artifact is generated. Never edit `dist/` in the Canon checkout.

## Install when the target path is absent

These commands deliberately refuse to overwrite anything. Run only the block
for your agent.

### Claude Code

```sh
(
  set -eu
  destination="$TARGET/CLAUDE.md"
  if test -e "$destination" || test -L "$destination"; then
    printf 'Refusing existing target: %s\n' "$destination" >&2
    exit 1
  fi
  cp "$CANON/dist/CLAUDE.md" "$destination"
  cmp -s "$CANON/dist/CLAUDE.md" "$destination"
)
```

### Codex, Pi, or another `AGENTS.md` reader

```sh
(
  set -eu
  destination="$TARGET/AGENTS.md"
  if test -e "$destination" || test -L "$destination"; then
    printf 'Refusing existing target: %s\n' "$destination" >&2
    exit 1
  fi
  cp "$CANON/dist/AGENTS.md" "$destination"
  cmp -s "$CANON/dist/AGENTS.md" "$destination"
)
```

An absent-target copy is **Canon-owned**: keep repository-specific rules in a
different file or convert the target to a managed merge before adding local
content. This ownership distinction makes later replacement and removal safe.

## Back up before changing an existing target

Run this before an install into an existing path, an upgrade, a rollback test,
or an uninstall. It creates a unique sibling directory outside the target Git
worktree and copies every relevant existing target into it.

```sh
BACKUP_DIR="$(
  set -eu
  backup="$(mktemp -d "${TARGET%/}.canon-backup.XXXXXX")"
  trap 'rm -rf "$backup"' EXIT
  trap 'exit 1' HUP INT TERM

  for path in \
    "$TARGET/AGENTS.md" \
    "$TARGET/CLAUDE.md"
  do
    test ! -L "$path" || {
      printf 'Refusing symlinked integration path: %s\n' "$path" >&2
      exit 1
    }
  done

  test ! -e "$TARGET/AGENTS.md" || \
    cp -p "$TARGET/AGENTS.md" "$backup/AGENTS.md"
  test ! -e "$TARGET/CLAUDE.md" || \
    cp -p "$TARGET/CLAUDE.md" "$backup/CLAUDE.md"

  trap - EXIT HUP INT TERM
  printf '%s\n' "$backup"
)" || {
  printf 'Canon backup failed; no target change is authorized\n' >&2
  exit 1
}

printf 'Canon backup: %s\n' "$BACKUP_DIR"
```

Keep the printed path until the change is verified. Do not place the backup in
the target repository or commit it.

## Merge into an existing instruction file

Use a delimited managed block for an existing `AGENTS.md` or `CLAUDE.md`.
Repository-specific text stays outside the block. Future upgrades replace only
the block.

Define this helper in the current shell:

```sh
canon_merge_block() {
  python3 - "$1" "$2" <<'PY'
from pathlib import Path
import os
import stat
import sys
import tempfile

target = Path(sys.argv[1])
source = Path(sys.argv[2])
begin = "<!-- BEGIN PROJECT CANON -->"
end = "<!-- END PROJECT CANON -->"

if target.is_symlink() or not target.is_file():
    raise SystemExit(f"refusing non-regular target: {target}")
if source.is_symlink() or not source.is_file():
    raise SystemExit(f"refusing non-regular source: {source}")

original = target.read_text(encoding="utf-8")
payload = source.read_text(encoding="utf-8").rstrip("\n")
begin_count = original.count(begin)
end_count = original.count(end)

if begin_count == 0 and end_count == 0:
    prefix = original.rstrip("\n")
    merged = (prefix + "\n\n" if prefix else "")
    merged += f"{begin}\n{payload}\n{end}\n"
elif begin_count == 1 and end_count == 1 and original.index(begin) < original.index(end):
    before, remainder = original.split(begin, 1)
    _, after = remainder.split(end, 1)
    merged = before + f"{begin}\n{payload}\n{end}" + after
else:
    raise SystemExit("refusing malformed or duplicate Project Canon markers")

descriptor, temporary_name = tempfile.mkstemp(
    prefix=f".{target.name}.canon-", dir=target.parent
)
try:
    with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
        temporary.write(merged)
    os.chmod(temporary_name, stat.S_IMODE(target.stat().st_mode))
    os.replace(temporary_name, target)
finally:
    if os.path.exists(temporary_name):
        os.unlink(temporary_name)
PY
}
```

After creating the backup, run the matching command:

```sh
# Existing AGENTS.md
canon_merge_block "$TARGET/AGENTS.md" "$CANON/dist/AGENTS.md"

# Existing CLAUDE.md
canon_merge_block "$TARGET/CLAUDE.md" "$CANON/dist/CLAUDE.md"
```

The helper refuses symlinks, missing files, duplicate markers, and unmatched
markers. Review the resulting diff before continuing:

```sh
git -C "$TARGET" diff -- AGENTS.md CLAUDE.md
```

## Verify the integration wiring

The copy commands for absent targets already compare every installed file with
its source. For a managed Markdown merge, verify exactly one marker pair in the
file you changed:

```sh
MERGED_FILE="$TARGET/AGENTS.md"  # choose the file you actually merged

test "$(grep -Fxc '<!-- BEGIN PROJECT CANON -->' "$MERGED_FILE")" -eq 1
test "$(grep -Fxc '<!-- END PROJECT CANON -->' "$MERGED_FILE")" -eq 1
grep -Fqx '_Remembered with [Project Canon](https://agentcanon.dev)._' \
  "$MERGED_FILE"
```

Inspect the surrounding repository-specific text as well; byte comparison
applies only to Canon-owned whole files.

## Install the `compact-canon` skill

The instruction file governs how sessions read and change Canon day to day. It
does not carry the maintenance procedure for a Canon that has already grown
inventories, repeated rules, legacy metadata, or routing gaps. That procedure
is the `compact-canon` skill, and it is loaded from the target repository's own
skill directory — not from this checkout, which the target will not have.

The skill is a portable `SKILL.md` directory with a Python analyzer beside it.
It lives at `.codex/skills/compact-canon/` in this repository because that is
where this repository's own agent reads it; nothing about the skill is
Codex-specific, and the source path carries no meaning for your target.

Unlike the instruction file, the skill is not one-per-repository. Install a
copy into **every** skill directory the agents working in the target actually
read — one if a single agent works there, several if several do. Duplicate
copies do not conflict: each harness loads only its own.

Consult your agent's current documentation for the directory it loads project
skills from. Two conventions in use at the time of writing:

| Agent | Skill directory in the target |
|---|---|
| Claude Code | `.claude/skills/` |
| Codex | `.codex/skills/` |

Treat that table as examples, not as the supported set. Any harness that loads
a project skill directory takes the same copy; a harness that loads none is
covered by the fallback at the end of this section.

List one destination per line, then run the copy. It refuses an existing path
and verifies every installed file against its source:

```sh
(
  set -eu
  source="$CANON/.codex/skills/compact-canon"
  test -d "$source" || exit 1
  test ! -L "$source" || exit 1

  # one entry per skill directory your agents read; edit this list
  set -- \
    "$TARGET/.claude/skills/compact-canon" \
    "$TARGET/.codex/skills/compact-canon"

  for destination do
    if test -e "$destination" || test -L "$destination"; then
      printf 'Refusing existing target: %s\n' "$destination" >&2
      exit 1
    fi
    parent="${destination%/*}"
    test ! -L "$parent" || exit 1
    mkdir -p "$parent" || exit 1
    cp -R "$source" "$destination" || exit 1
    find "$destination" -name '__pycache__' -type d -prune -exec rm -rf {} +
    diff -r -x '__pycache__' "$source" "$destination" >/dev/null || exit 1
    printf 'Installed skill: %s\n' "$destination"
  done
)
```

The loop stops at the first refusal, and destinations before it stay installed;
the printed lines say which. Resolve the refused path — an existing directory
is never overwritten — and rerun with only the remaining destinations.

Each copied directory is Canon-owned in the same sense as a whole-file
integration: keep repository-specific instructions out of it so upgrades and
removal stay safe.

Invoke it by name once installed. The trigger syntax belongs to the harness —
`$compact-canon` in Codex, "use the compact-canon skill" in Claude Code, and
whatever your agent documents elsewhere. Every form accepts a `dry run`
request, which reports candidates and changes nothing.

For an agent with no project skill directory, skip this section and paste the
skill's procedure, or a request naming it, into the session instead. The
migration and maintenance prompts below still work without the skill; they
lose the procedure, not the intent.

## Bootstrap Canon in the first session

Start a fresh agent session from `TARGET`. A session that was already running
may not reload the newly installed repository instructions.

If `canon/` is absent, send this prompt exactly:

```text
Set up Project Canon in this repository now. Preserve all existing repository
instructions. Create canon/manifest.md with status: reference and
canon/standards.md with status: normative. Create canon/architecture/,
canon/decisions/, and canon/scratch/, and add canon/scratch/ to the
repository-root .gitignore without removing existing entries. Do not invent
standards, decisions, architecture, rationale, or domain terms. Do not create
source-file inventories or sources/verified metadata. Do not change application
code. Report the files created and any unresolved knowledge gaps.
```

If `canon/` already exists, do not run the bootstrap prompt. Start a fresh
session and ask the agent to inspect Canon health before the first real task.

Large repositories should start with only the core structure. Add focused
architecture pages only when work first needs a durable law or product
invariant; do not bulk-document the codebase during installation.

## Migrate an existing repository Canon

Upgrading the agent guidance does not silently rewrite the target repository's
`canon/`. Existing decisions and human standards need reviewed migration.

Start from a clean target worktree. In a session that can load the installed
[`compact-canon`](.codex/skills/compact-canon/SKILL.md) skill, invoke it
explicitly — Codex users can write `$compact-canon` in place of the first
clause. If you skipped the skill install, give the same request without the
first sentence:

```sh
MIGRATION_BASE="$(git -C "$TARGET" rev-parse HEAD)" || exit 1
printf 'Legacy decision baseline: %s\n' "$MIGRATION_BASE"
```

```text
Use the compact-canon skill to rework this repository's Canon into the
invariant-first shape. Preserve human standards and every existing decision byte-for-byte.
Remove implementation inventories and legacy sources/verified metadata from
non-decision pages; legacy metadata inside an existing decision is immutable
history. Replace removed metadata only with truthful status, package or
architectural scope, executable validation, and relationship links. Make
manifest.md a compact concern-to-page router, keep scratch out of normal
context, and move operational guidance only when an existing development-doc
destination is in scope. Run the Canon doctor with the pre-migration commit as
`--baseline` in strict mode and report all abstentions.
```

Review every changed Canon paragraph against this test:

> Canon changed because the system must now guarantee that ...

If the explanation is only a file or symbol move, remove that paragraph from
Canon instead of translating the inventory into a new form. Run migration and
application refactors as separate changes when practical; this makes deleted
mirroring easy to distinguish from changed guarantees.

## Verify the installation

Verification is required before committing the target change.

Run the normal check first:

```sh
uv run --script "$CANON/tools/canon-doctor.py" --root "$TARGET"
```

Normal mode exits nonzero for errors. It prints warnings but exits zero when
there are no errors. Warnings identify likely implementation inventories and
changelog-style prose.

For a migrated Canon with legacy decision records, add
`--baseline "$MIGRATION_BASE"` to every normal and strict doctor invocation.
Keep that reviewed commit reachable; the doctor uses it only to grandfather
unchanged historical decision records — their legacy metadata, stale links,
and oversize bodies are all waived, since immutable bytes could never be
repaired — and still protects every decision present at the current `HEAD`.

Then run the release gate:

```sh
uv run --script "$CANON/tools/canon-doctor.py" --root "$TARGET" --strict
```

`--strict` exits nonzero for **any** finding, including warnings. A clean
installation prints:

```text
canon doctor: all checks passed
```

Finally review staged, unstaged, and untracked target changes, and confirm that
no backup is inside the worktree:

```sh
git -C "$TARGET" status --short --untracked-files=all
git -C "$TARGET" diff --check
git -C "$TARGET" diff --cached --check
git -C "$TARGET" diff --no-ext-diff
git -C "$TARGET" diff --cached --no-ext-diff
```

`git diff` does not print untracked file contents. Open every untracked path
listed by `git status` before staging it.

Doctor validates `canon/`; it does not prove that the agent launcher loaded
`AGENTS.md` or `CLAUDE.md`. The fresh-session bootstrap behavior is that
end-to-end check.

## Upgrade Canon

Update the Canon checkout to the clean revision you want to install, set
`CANON_REF` to the new `HEAD`, and keep the previously recorded revision as
`INSTALLED_REF`:

```sh
INSTALLED_REF=full-commit-id-recorded-at-install
git -C "$CANON" cat-file -e "${INSTALLED_REF}^{commit}" || exit 1
test -z "$(git -C "$CANON" status --porcelain --untracked-files=all)" || exit 1
uv run --script "$CANON/tools/build.py" >/dev/null || exit 1
test -z "$(git -C "$CANON" status --porcelain --untracked-files=all)" || {
  printf 'Generated artifacts are stale at the upgrade revision\n' >&2
  exit 1
}
BUILD_OUTPUT="$(uv run --script "$CANON/tools/build.py")" || exit 1
printf '%s\n' "$BUILD_OUTPUT"
printf '%s\n' "$BUILD_OUTPUT" | grep -q '^wrote' && exit 1
CANON_REF="$(git -C "$CANON" rev-parse HEAD)" || exit 1
printf 'Upgrading Canon from %s to %s\n' "$INSTALLED_REF" "$CANON_REF"
```

Create a fresh backup before upgrading.

### Upgrade a Canon-owned whole file

Define this guard. It reconstructs the artifact from the recorded installed
revision and refuses a locally modified, symlinked, or ambiguous target:

```sh
canon_assert_owned() {
  destination=$1
  artifact=$2
  installed_ref=$3
  previous="$(mktemp)"

  if test -L "$destination" || test ! -f "$destination"; then
    printf 'Refusing non-regular Canon-owned target: %s\n' "$destination" >&2
    rm -f "$previous"
    return 1
  fi
  if ! git -C "$CANON" show "${installed_ref}:${artifact}" > "$previous"; then
    printf 'Cannot read %s at %s\n' "$artifact" "$installed_ref" >&2
    rm -f "$previous"
    return 1
  fi
  if ! cmp -s "$destination" "$previous"; then
    printf 'Refusing locally modified or ambiguous target: %s\n' "$destination" >&2
    rm -f "$previous"
    return 1
  fi
  rm -f "$previous"
}

canon_replace_owned() {
  destination=$1
  artifact=$2
  installed_ref=$3
  source=$4

  canon_assert_owned "$destination" "$artifact" "$installed_ref" || return 1
  python3 - "$destination" "$source" <<'PY'
from pathlib import Path
import os
import stat
import sys
import tempfile

target = Path(sys.argv[1])
source = Path(sys.argv[2])
if target.is_symlink() or not target.is_file():
    raise SystemExit(f"refusing non-regular target: {target}")
if source.is_symlink() or not source.is_file():
    raise SystemExit(f"refusing non-regular source: {source}")
mode = stat.S_IMODE(target.stat().st_mode)
descriptor, temporary_name = tempfile.mkstemp(
    prefix=f".{target.name}.canon-", dir=target.parent
)
try:
    with os.fdopen(descriptor, "wb") as temporary:
        temporary.write(source.read_bytes())
        temporary.flush()
        os.fsync(temporary.fileno())
    os.chmod(temporary_name, mode)
    os.replace(temporary_name, target)
finally:
    if os.path.exists(temporary_name):
        os.unlink(temporary_name)
PY
  cmp -s "$source" "$destination"
}
```

Run the matching upgrade:

```sh
# Canon-owned AGENTS.md
canon_replace_owned \
  "$TARGET/AGENTS.md" dist/AGENTS.md "$INSTALLED_REF" \
  "$CANON/dist/AGENTS.md"

# Canon-owned CLAUDE.md
canon_replace_owned \
  "$TARGET/CLAUDE.md" dist/CLAUDE.md "$INSTALLED_REF" \
  "$CANON/dist/CLAUDE.md"
```

If an ownership guard refuses a Markdown file, do not overwrite it. Restore the
backup, identify the local rules, and use the managed-block procedure.

### Upgrade a managed block

Re-define `canon_merge_block` in the current shell, then run the same merge
command used during installation. When one valid marker pair exists, the
helper replaces only its contents and preserves all repository-specific text.

### Upgrade the installed skill

Upgrade the skill in the same change as the instruction file, so the target
never mixes revisions. Define this guard, which reconstructs the skill from the
recorded installed revision and refuses a locally modified copy:

```sh
canon_assert_owned_skill() {
  destination=$1
  installed_ref=$2
  previous="$(mktemp -d)" || return 1

  if test -L "$destination" || test ! -d "$destination"; then
    printf 'Refusing non-directory skill target: %s\n' "$destination" >&2
    rm -rf "$previous"
    return 1
  fi
  if ! git -C "$CANON" archive "$installed_ref" .codex/skills/compact-canon \
      | tar -x -C "$previous"; then
    printf 'Cannot read the skill at %s\n' "$installed_ref" >&2
    rm -rf "$previous"
    return 1
  fi
  if ! diff -r -x '__pycache__' \
      "$previous/.codex/skills/compact-canon" "$destination" >/dev/null; then
    printf 'Refusing locally modified skill target: %s\n' "$destination" >&2
    rm -rf "$previous"
    return 1
  fi
  rm -rf "$previous"
}
```

Then replace every installed copy with the new revision. List the same
destinations you installed:

```sh
(
  set -eu
  source="$CANON/.codex/skills/compact-canon"

  # one entry per installed copy; edit this list
  set -- \
    "$TARGET/.claude/skills/compact-canon" \
    "$TARGET/.codex/skills/compact-canon"

  for destination do
    canon_assert_owned_skill "$destination" "$INSTALLED_REF" || exit 1
    rm -rf "$destination" || exit 1
    cp -R "$source" "$destination" || exit 1
    find "$destination" -name '__pycache__' -type d -prune -exec rm -rf {} +
    diff -r -x '__pycache__' "$source" "$destination" >/dev/null || exit 1
    printf 'Upgraded skill: %s\n' "$destination"
  done
)
```

If the guard refuses, do not overwrite. Diff that copy against the recorded
revision, move any repository-specific text out of the skill directory, and
rerun. The loop stops at the first refusal; the printed lines show which
destinations were already upgraded.

If the skill was never installed, use the first-install command instead.

After either upgrade path, start a new agent session, run doctor in strict
mode, review the diff, and record the new `CANON_REF`.

## Roll back a failed integration change

Rollback restores only the integration paths captured by the backup command.
It does not revert later bootstrap changes in `canon/` or `.gitignore`. Restore
before making unrelated target changes; otherwise use the uninstall procedure
so later work is preserved.

Set `BACKUP_DIR` to the printed backup path, then restore the relevant file:

```sh
BACKUP_DIR=/absolute/path/printed-by-the-backup-command

canon_restore_file() {
  source=$1
  destination=$2
  parent=${destination%/*}

  if test -L "$source" || test ! -f "$source"; then
    printf 'Refusing missing, symlinked, or non-file backup: %s\n' "$source" >&2
    return 1
  fi
  if test -L "$destination" || test -L "$parent"; then
    printf 'Refusing symlinked restore path: %s\n' "$destination" >&2
    return 1
  fi
  if test -e "$parent" && test ! -d "$parent"; then
    printf 'Refusing non-directory restore parent: %s\n' "$parent" >&2
    return 1
  fi
  mkdir -p "$parent" || return 1
  cp -p "$source" "$destination"
}

# Choose only the integration you are restoring.
canon_restore_file "$BACKUP_DIR/AGENTS.md" "$TARGET/AGENTS.md"
canon_restore_file "$BACKUP_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"
```

If the integration path did not exist before installation, rollback is the
same as uninstalling that Canon-owned path.

After restoring, start a new session and rerun doctor.

## Uninstall Canon

Back up the current target first. Uninstall the agent integration, the
`compact-canon` skill, and the `canon/` knowledge directory as separate
decisions: removing agent guidance does not imply deleting project knowledge.

### Remove a managed block

Define this helper:

```sh
canon_remove_block() {
  python3 - "$1" <<'PY'
from pathlib import Path
import os
import stat
import sys
import tempfile

target = Path(sys.argv[1])
begin = "<!-- BEGIN PROJECT CANON -->"
end = "<!-- END PROJECT CANON -->"

if target.is_symlink() or not target.is_file():
    raise SystemExit(f"refusing non-regular target: {target}")
original = target.read_text(encoding="utf-8")
if original.count(begin) != 1 or original.count(end) != 1:
    raise SystemExit("refusing missing, malformed, or duplicate Project Canon markers")
if original.index(begin) > original.index(end):
    raise SystemExit("refusing reversed Project Canon markers")

before, remainder = original.split(begin, 1)
_, after = remainder.split(end, 1)
updated = before + after
if not after.strip():
    updated = before.rstrip("\n") + ("\n" if before.strip() else "")

descriptor, temporary_name = tempfile.mkstemp(
    prefix=f".{target.name}.canon-", dir=target.parent
)
try:
    with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
        temporary.write(updated)
    os.chmod(temporary_name, stat.S_IMODE(target.stat().st_mode))
    os.replace(temporary_name, target)
finally:
    if os.path.exists(temporary_name):
        os.unlink(temporary_name)
PY
}
```

Run it on the merged target:

```sh
canon_remove_block "$TARGET/AGENTS.md"
canon_remove_block "$TARGET/CLAUDE.md"
```

Choose only the command for the installed integration. Review the diff before
deleting the backup.

### Remove a Canon-owned whole file

Set `INSTALLED_REF` to the Canon revision currently installed and re-define
`canon_assert_owned`. Then verify before deleting:

The artifact paths below apply to installations made after this repository
adopted the `dist/` layout. For an older recorded revision — including a
retired integration that this repository no longer generates — inspect that
revision's tree and supply its historical artifact path; a missing path is a
safe refusal, not permission to delete.

```sh
# Choose only the installed integration.
canon_assert_owned "$TARGET/AGENTS.md" dist/AGENTS.md "$INSTALLED_REF" && \
  rm "$TARGET/AGENTS.md"

canon_assert_owned "$TARGET/CLAUDE.md" dist/CLAUDE.md "$INSTALLED_REF" && \
  rm "$TARGET/CLAUDE.md"
```

The guard refuses removal if the file differs from the recorded artifact. Do
not bypass that refusal: preserve local rules and remove only the Canon text
through a reviewed merge.

### Remove the installed skill

Set `INSTALLED_REF` to the Canon revision currently installed, re-define
`canon_assert_owned_skill`, and verify each copy before deleting it:

```sh
(
  set -eu

  # one entry per installed copy; edit this list
  set -- \
    "$TARGET/.claude/skills/compact-canon" \
    "$TARGET/.codex/skills/compact-canon"

  for destination do
    canon_assert_owned_skill "$destination" "$INSTALLED_REF" || exit 1
    rm -rf "$destination" || exit 1
    printf 'Removed skill: %s\n' "$destination"
  done
)
```

The guard refuses removal if a directory differs from the recorded revision,
and the loop stops there; the printed lines say which copies are already gone.
Remove a now-empty skills parent only if nothing else uses it.

### Decide separately whether to remove `canon/`

The `canon/` directory may contain valuable project-authored standards and
decisions. Remove it only with explicit project-owner approval and only after
backing it up. No automated deletion command is provided because that action
cannot be inferred from uninstalling an agent integration.

Finish by starting a new agent session and reviewing repository status. Doctor
should now report `no canon/ directory` if you intentionally removed project
knowledge; that is expected after a complete uninstall, not a passing health
check.

## Troubleshooting

### `Refusing existing target`

The absent-target command found a file or directory. Back it up and use the
matching merge procedure; do not delete it to make the copy command pass.

### `Refusing locally modified or ambiguous target`

The whole-file ownership proof failed. Confirm `INSTALLED_REF`. If the file
contains local rules, preserve them and use a reviewed managed block. Never
force replacement or removal.

### Doctor reports warnings but the command succeeds

That is normal-mode behavior. Run with `--strict`; warnings then fail the
command and must be resolved before release.

### Doctor rejects `sources` or `verified`

These fields belong to the retired repository-mirroring model. Remove the
source inventory and commit hash. Classify the page as `normative`,
`reference`, `draft`, or `deprecated`; replace implementation paths with
package or architectural `scope` values, and link only stable executable
checks under `validation`.

### Doctor reports an implementation inventory

Replace exhaustive files, symbols, exports, or repository instances with one
general ownership or behavior rule. Keep a few examples only when they are
explicitly non-exhaustive and materially improve comprehension.

## For Project Canon maintainers

`dist/CLAUDE.md` and `dist/AGENTS.md` are generated from `canon-core.md`.
After changing the core, run:

```sh
uv run --script tools/build.py
uv run --script tools/build.py
uv run python -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
```

Never edit `dist/` by hand. See [`evals/PLAYBOOK.md`](evals/PLAYBOOK.md) before
measuring or adopting a guidance change.
