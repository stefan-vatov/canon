# How to install and maintain Project Canon

This guide installs Project Canon in a target repository and covers the full
consumer lifecycle: first install, safe merges, bootstrap, verification,
upgrade, rollback, and uninstall.

Project Canon is repository-scoped agent guidance. Install only the integration
for the agent you use, then start a new agent session from the target repository.

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
FRESHNESS="$(uv run --script "$CANON/tools/build.py")" || exit 1
printf '%s\n' "$FRESHNESS"
if printf '%s\n' "$FRESHNESS" | grep -q '^wrote'; then
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
| Codex or another `AGENTS.md` reader | `dist/AGENTS.md` | `AGENTS.md` |
| Codex full system prompt (experimental) | `dist/.codex/system.md` and `dist/.codex/config.toml` | `.codex/` |
| Pi | `dist/.pi/APPEND_SYSTEM.md` | `.pi/APPEND_SYSTEM.md` |

For Codex, choose either `AGENTS.md` or the full system-prompt integration.
Installing both repeats the same Canon guidance. For tools not listed here,
use `AGENTS.md` only when that tool's current documentation says it loads the
file.

The full Codex system artifact replaces the model instructions file with a
vendored base prompt and is therefore coupled to a Codex release. It is an
experimental integration, not a release-agnostic default. Prefer `AGENTS.md`
unless you have synchronized and tested `templates/codex-base.md` against the
exact Codex CLI release you deploy. Project `.codex/config.toml` also loads only
after Codex trusts the repository.

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

### Codex with `AGENTS.md`

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

### Codex with the full system prompt

Use this only after accepting the version-coupling warning above and only when
the entire `.codex/` directory is absent:

```sh
(
  set -eu
  destination="$TARGET/.codex"
  if test -e "$destination" || test -L "$destination"; then
    printf 'Refusing existing target: %s\n' "$destination" >&2
    exit 1
  fi
  mkdir "$destination"
  trap 'rm -rf "$destination"' EXIT
  trap 'exit 1' HUP INT TERM
  cp "$CANON/dist/.codex/config.toml" "$destination/config.toml"
  cp "$CANON/dist/.codex/system.md" "$destination/system.md"
  cmp -s "$CANON/dist/.codex/config.toml" "$destination/config.toml"
  cmp -s "$CANON/dist/.codex/system.md" "$destination/system.md"
  trap - EXIT HUP INT TERM
)
```

### Pi

```sh
(
  set -eu
  destination="$TARGET/.pi/APPEND_SYSTEM.md"
  test ! -L "$TARGET/.pi" || {
    printf 'Refusing symlinked directory: %s\n' "$TARGET/.pi" >&2
    exit 1
  }
  mkdir -p "$TARGET/.pi"
  if test -e "$destination" || test -L "$destination"; then
    printf 'Refusing existing target: %s\n' "$destination" >&2
    exit 1
  fi
  cp "$CANON/dist/.pi/APPEND_SYSTEM.md" "$destination"
  cmp -s "$CANON/dist/.pi/APPEND_SYSTEM.md" "$destination"
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
    "$TARGET/.codex" \
    "$TARGET/.pi" \
    "$TARGET/AGENTS.md" \
    "$TARGET/CLAUDE.md" \
    "$TARGET/.pi/APPEND_SYSTEM.md"
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

  if test -e "$TARGET/.codex"; then
    cp -Rp "$TARGET/.codex" "$backup/.codex"
  fi

  if test -e "$TARGET/.pi/APPEND_SYSTEM.md"; then
    mkdir -p "$backup/.pi"
    cp -p "$TARGET/.pi/APPEND_SYSTEM.md" \
      "$backup/.pi/APPEND_SYSTEM.md"
  fi

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

Use a delimited managed block for an existing `AGENTS.md`, `CLAUDE.md`, Pi
append-system file, or custom Codex system prompt. Repository-specific text
stays outside the block. Future upgrades replace only the block.

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

# Existing Pi append-system file
canon_merge_block \
  "$TARGET/.pi/APPEND_SYSTEM.md" \
  "$CANON/dist/.pi/APPEND_SYSTEM.md"
```

The helper refuses symlinks, missing files, duplicate markers, and unmatched
markers. Review the resulting diff before continuing:

```sh
git -C "$TARGET" diff -- AGENTS.md CLAUDE.md .pi/APPEND_SYSTEM.md
```

## Merge into an existing `.codex/`

Never copy a directory over an existing `.codex/`. Back up the directory first,
then use the case that matches its configuration. The backup preflight refuses
a symlinked `.codex/`; do not bypass that containment check.

### Existing `.codex/` with no `config.toml`

Install a separate Canon-owned system prompt and create only the missing
configuration file. Existing `.codex/` contents remain untouched.

```sh
(
  set -eu
  codex="$TARGET/.codex"
  prompt="$codex/canon-system.md"
  config="$codex/config.toml"
  if test -L "$codex" || test ! -d "$codex"; then
    printf 'Refusing missing, symlinked, or non-directory path: %s\n' "$codex" >&2
    exit 1
  fi
  if test -e "$config" || test -L "$config"; then
    printf 'config.toml already exists; use the next section\n' >&2
    exit 1
  fi
  if test -e "$prompt" || test -L "$prompt"; then
    printf 'canon-system.md already exists; refusing overwrite\n' >&2
    exit 1
  fi
  trap 'rm -f "$prompt" "$config"' EXIT
  trap 'exit 1' HUP INT TERM
  cp "$CANON/dist/.codex/system.md" "$prompt"
  printf '%s\n' 'model_instructions_file = "canon-system.md"' > "$config"
  cmp -s "$CANON/dist/.codex/system.md" "$prompt"
  trap - EXIT HUP INT TERM
)
```

Record that this procedure created `config.toml`; uninstall uses that fact to
decide whether an empty configuration file may be removed.

### Existing `config.toml` without `model_instructions_file`

First confirm the key is absent. No output means this case applies:

```sh
grep -nE "^[[:space:]]*(model_instructions_file|'model_instructions_file'|\"model_instructions_file\")[[:space:]]*=" \
  "$TARGET/.codex/config.toml" || true
```

Define this helper. It inserts the Canon key before the first TOML table, so it
is a top-level setting, and refuses any existing key:

```sh
canon_add_codex_key() {
  python3 - "$1" <<'PY'
from pathlib import Path
import os
import re
import stat
import sys
import tempfile

target = Path(sys.argv[1])
needle = 'model_instructions_file = "canon-system.md"'
pattern = re.compile(
    r"(?m)^\s*(?:model_instructions_file|\"model_instructions_file\"|"
    r"'model_instructions_file')\s*="
)

if target.is_symlink() or not target.is_file():
    raise SystemExit(f"refusing non-regular config: {target}")
original = target.read_text(encoding="utf-8")
if pattern.search(original):
    raise SystemExit("model_instructions_file already exists; refusing duplicate key")

merged = needle + "\n\n" + original
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

Then install the separate prompt and add the key:

```sh
(
  set -eu
  codex="$TARGET/.codex"
  prompt="$codex/canon-system.md"
  if test -L "$codex" || test ! -d "$codex"; then
    printf 'Refusing missing, symlinked, or non-directory path: %s\n' "$codex" >&2
    exit 1
  fi
  if test -e "$prompt" || test -L "$prompt"; then
    printf 'canon-system.md already exists; refusing overwrite\n' >&2
    exit 1
  fi
  trap 'rm -f "$prompt"' EXIT
  trap 'exit 1' HUP INT TERM
  cp "$CANON/dist/.codex/system.md" "$prompt"
  canon_add_codex_key "$TARGET/.codex/config.toml"
  cmp -s "$CANON/dist/.codex/system.md" "$prompt"
  trap - EXIT HUP INT TERM
)
```

### Existing `config.toml` with `model_instructions_file`

Keep the existing key and merge Canon into the system prompt it already names.
Do not replace the configured prompt.

```sh
grep -nE "^[[:space:]]*(model_instructions_file|'model_instructions_file'|\"model_instructions_file\")[[:space:]]*=" \
  "$TARGET/.codex/config.toml"
```

Codex resolves a relative `model_instructions_file` from the `.codex/` folder
containing `config.toml`, so the shipped configuration uses `system.md`.
The resolver below accepts one unescaped, single-line quoted path and refuses
ambiguous TOML instead of copying configuration text into the shell. This
matches the common Codex form while failing safely for advanced TOML syntax:

```sh
canon_codex_system_path() {
  python3 - "$1" <<'PY'
from pathlib import Path
import re
import sys

config = Path(sys.argv[1])
if config.is_symlink() or not config.is_file():
    raise SystemExit(f"refusing missing, symlinked, or non-file config: {config}")
codex = config.parent
if codex.is_symlink() or not codex.is_dir():
    raise SystemExit(f"refusing symlinked or non-directory path: {codex}")
codex = codex.resolve(strict=True)

key = r"(?:model_instructions_file|\"model_instructions_file\"|'model_instructions_file')"
assignment = re.compile(
    rf"^\s*{key}\s*=\s*([\"'])([^\"'\\\n]+)\1\s*(?:#.*)?$"
)
matches = []
for line in config.read_text(encoding="utf-8").splitlines():
    if re.match(r"^\s*\[", line):
        break
    match = assignment.match(line)
    if match:
        matches.append(match.group(2))
if len(matches) != 1:
    raise SystemExit("refusing absent, duplicate, escaped, or non-simple top-level path")

raw = Path(matches[0])
candidate = raw if raw.is_absolute() else codex / raw
if candidate.is_symlink() or not candidate.is_file():
    raise SystemExit(f"refusing missing, symlinked, or non-file prompt: {candidate}")
resolved = candidate.resolve(strict=True)
try:
    resolved.relative_to(codex)
except ValueError:
    raise SystemExit(f"refusing prompt outside .codex/: {resolved}")
print(resolved)
PY
}

SYSTEM_PATH="$(canon_codex_system_path "$TARGET/.codex/config.toml")" || exit 1

canon_merge_block "$SYSTEM_PATH" "$CANON/dist/AGENTS.md"
```

If the configured prompt resolves outside `.codex/`, the containment check
refuses it. Use the `AGENTS.md` integration or perform a separately reviewed
manual merge; do not weaken the check in a copy-paste install.

These path and trust semantics come from the official
[Codex project-config documentation](https://developers.openai.com/codex/config-advanced#project-config-files-codexconfigtoml).

Review both files after any `.codex/` merge:

```sh
git -C "$TARGET" diff -- .codex/config.toml .codex
```

## Verify the integration wiring

The copy commands for absent targets already compare every installed file with
its source. For a managed Markdown merge, verify exactly one marker pair in the
file you changed:

```sh
MERGED_FILE="$TARGET/AGENTS.md"  # choose the file you actually merged

test "$(grep -Fxc '<!-- BEGIN PROJECT CANON -->' "$MERGED_FILE")" -eq 1
test "$(grep -Fxc '<!-- END PROJECT CANON -->' "$MERGED_FILE")" -eq 1
```

For a separate prompt added to an existing `.codex/`, verify its bytes and the
exact relative key:

```sh
cmp -s \
  "$CANON/dist/.codex/system.md" \
  "$TARGET/.codex/canon-system.md"
grep -Fxn 'model_instructions_file = "canon-system.md"' \
  "$TARGET/.codex/config.toml"
```

If Canon was merged into an existing configured prompt, run the marker check
with `MERGED_FILE="$SYSTEM_PATH"`. Inspect the surrounding repository-specific
text as well; byte comparison applies only to Canon-owned whole files.

For the full Codex integration, open a fresh session from the target root.
Trust the project only after reviewing it. Codex ignores project `.codex/`
configuration in untrusted repositories, so the absence of a startup warning
about ignored project configuration is part of the load check.

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

Start from a clean target worktree. In a session that can load this checkout's
bundled [`$compact-canon`](.codex/skills/compact-canon/SKILL.md) skill, invoke
it explicitly. Otherwise give the same migration request without the first
sentence:

```sh
MIGRATION_BASE="$(git -C "$TARGET" rev-parse HEAD)" || exit 1
printf 'Legacy decision baseline: %s\n' "$MIGRATION_BASE"
```

```text
Use $compact-canon to rework this repository's Canon into the invariant-first
shape. Preserve human standards and every existing decision byte-for-byte.
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
unchanged historical decision metadata and still protects every decision
present at the current `HEAD`.

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
`AGENTS.md`, `CLAUDE.md`, `.codex/`, or Pi configuration. The fresh-session
bootstrap behavior is that end-to-end check.

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
FRESHNESS="$(uv run --script "$CANON/tools/build.py")" || exit 1
printf '%s\n' "$FRESHNESS"
printf '%s\n' "$FRESHNESS" | grep -q '^wrote' && exit 1
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

# Canon-owned Pi file
canon_replace_owned \
  "$TARGET/.pi/APPEND_SYSTEM.md" \
  dist/.pi/APPEND_SYSTEM.md \
  "$INSTALLED_REF" \
  "$CANON/dist/.pi/APPEND_SYSTEM.md"
```

For a Canon-owned `.codex/` installed into an absent directory, verify both
owned files before replacing either:

```sh
canon_assert_owned \
  "$TARGET/.codex/config.toml" \
  dist/.codex/config.toml \
  "$INSTALLED_REF" && \
canon_assert_owned \
  "$TARGET/.codex/system.md" \
  dist/.codex/system.md \
  "$INSTALLED_REF" && \
canon_replace_owned \
  "$TARGET/.codex/config.toml" \
  dist/.codex/config.toml \
  "$INSTALLED_REF" \
  "$CANON/dist/.codex/config.toml" && \
canon_replace_owned \
  "$TARGET/.codex/system.md" \
  dist/.codex/system.md \
  "$INSTALLED_REF" \
  "$CANON/dist/.codex/system.md"
```

For `canon-system.md` installed alongside an existing `.codex/`, its bytes
come from `dist/.codex/system.md`:

```sh
canon_replace_owned \
  "$TARGET/.codex/canon-system.md" \
  dist/.codex/system.md \
  "$INSTALLED_REF" \
  "$CANON/dist/.codex/system.md"
```

If an ownership guard refuses a Markdown file, do not overwrite it. Restore the
backup, identify the local rules, and use the managed-block procedure. Never
put Markdown markers in `.codex/config.toml`; preserve its TOML and use the
matching existing-configuration procedure instead.

### Upgrade a managed block

Re-define `canon_merge_block` in the current shell, then run the same merge
command used during installation. When one valid marker pair exists, the
helper replaces only its contents and preserves all repository-specific text.

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
canon_restore_file \
  "$BACKUP_DIR/.pi/APPEND_SYSTEM.md" \
  "$TARGET/.pi/APPEND_SYSTEM.md"
```

To restore an existing `.codex/` exactly while preserving the failed current
state for inspection:

```sh
(
  set -eu
  backup="$BACKUP_DIR/.codex"
  destination="$TARGET/.codex"
  current="$(mktemp -d "${TARGET%/}.canon-rollback-current.XXXXXX")"

  if test -L "$backup" || test ! -d "$backup"; then
    printf 'Refusing missing, symlinked, or non-directory backup: %s\n' "$backup" >&2
    exit 1
  fi
  if test -L "$destination"; then
    printf 'Refusing symlinked current path: %s\n' "$destination" >&2
    exit 1
  fi
  if test -e "$destination" && test ! -d "$destination"; then
    printf 'Refusing non-directory current path: %s\n' "$destination" >&2
    exit 1
  fi

  if test -d "$destination"; then
    mv "$destination" "$current/.codex"
    printf 'Failed .codex state preserved at %s\n' "$current/.codex"
  else
    printf 'No current .codex state to preserve\n'
  fi
  cp -Rp "$backup" "$destination"
)
```

If the integration path did not exist before installation, rollback is the
same as uninstalling that Canon-owned path.

After restoring, start a new session and rerun doctor.

## Uninstall Canon

Back up the current target first. Uninstall the agent integration and the
`canon/` knowledge directory as separate decisions: removing agent guidance
does not imply deleting project knowledge.

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
canon_remove_block "$TARGET/.pi/APPEND_SYSTEM.md"

# Existing Codex system prompt only: first re-define
# canon_codex_system_path from the install section.
SYSTEM_PATH="$(canon_codex_system_path "$TARGET/.codex/config.toml")" || exit 1
canon_remove_block "$SYSTEM_PATH"
```

Choose only the command for the installed integration. Review the diff before
deleting the backup.

### Remove a Canon-owned whole file

Set `INSTALLED_REF` to the Canon revision currently installed and re-define
`canon_assert_owned`. Then verify before deleting:

The artifact paths below apply to installations made after this repository
adopted the `dist/` layout. For an older recorded revision, inspect that
revision's tree and supply its historical artifact path; a missing path is a
safe refusal, not permission to delete.

```sh
# Choose only the installed integration.
canon_assert_owned "$TARGET/AGENTS.md" dist/AGENTS.md "$INSTALLED_REF" && \
  rm "$TARGET/AGENTS.md"

canon_assert_owned "$TARGET/CLAUDE.md" dist/CLAUDE.md "$INSTALLED_REF" && \
  rm "$TARGET/CLAUDE.md"

canon_assert_owned \
  "$TARGET/.pi/APPEND_SYSTEM.md" \
  dist/.pi/APPEND_SYSTEM.md \
  "$INSTALLED_REF" && \
  rm "$TARGET/.pi/APPEND_SYSTEM.md"
rmdir "$TARGET/.pi" 2>/dev/null || true
```

The guard refuses removal if the file differs from the recorded artifact. Do
not bypass that refusal: preserve local rules and remove only the Canon text
through a reviewed merge.

For a Canon-owned `.codex/` installed into an absent directory, verify both
files before removing either:

```sh
canon_assert_owned \
  "$TARGET/.codex/config.toml" \
  dist/.codex/config.toml \
  "$INSTALLED_REF" && \
canon_assert_owned \
  "$TARGET/.codex/system.md" \
  dist/.codex/system.md \
  "$INSTALLED_REF" && \
rm "$TARGET/.codex/config.toml" "$TARGET/.codex/system.md"
rmdir "$TARGET/.codex" 2>/dev/null || \
  printf 'Kept non-empty .codex/ directory\n'
```

### Remove `canon-system.md` from an existing `.codex/`

First verify the owned prompt against `dist/.codex/system.md` at
`INSTALLED_REF`. Then remove the exact top-level key Canon added. The helper
preserves an empty `config.toml`; remove that file afterward only if your
installation record proves Canon created it:

```sh
canon_remove_codex_key() {
  python3 - "$1" <<'PY'
from pathlib import Path
import os
import stat
import sys
import tempfile

target = Path(sys.argv[1])
prefix = 'model_instructions_file = "canon-system.md"\n'

if target.is_symlink() or not target.is_file():
    raise SystemExit(f"refusing non-regular config: {target}")
original = target.read_text(encoding="utf-8")
if not original.startswith(prefix):
    raise SystemExit("refusing config not prefixed by Canon's exact key")

updated = original[len(prefix):]
if updated.startswith("\n"):
    updated = updated[1:]

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

# Set to 1 only when the recorded install created config.toml.
CANON_CREATED_CONFIG=0

(
  set -eu
  canon_assert_owned \
    "$TARGET/.codex/canon-system.md" \
    dist/.codex/system.md \
    "$INSTALLED_REF"
  canon_remove_codex_key "$TARGET/.codex/config.toml"
  rm "$TARGET/.codex/canon-system.md"
  if test "$CANON_CREATED_CONFIG" = 1 && \
      test ! -s "$TARGET/.codex/config.toml"; then
    rm "$TARGET/.codex/config.toml"
  fi
  rmdir "$TARGET/.codex" 2>/dev/null || true
)
```

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

### `model_instructions_file already exists`

Keep that key. Resolve its path and merge the managed Canon block into the
existing system prompt.

### `Refusing locally modified or ambiguous target`

The whole-file ownership proof failed. Confirm `INSTALLED_REF`. If the file
is Markdown and contains local rules, preserve them and use a reviewed managed
block. Never put Markdown markers in `.codex/config.toml`; preserve its TOML
and follow the existing-configuration procedure. Never force replacement or
removal.

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

`dist/` is generated from `canon-core.md`, `templates/codex-base.md`, and
`templates/codex-config.toml`. After changing a source, run:

```sh
uv run --script tools/build.py
uv run --script tools/build.py
uv run python -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
```

Never edit `dist/` by hand. See [`evals/PLAYBOOK.md`](evals/PLAYBOOK.md) before
measuring or adopting a guidance change.
