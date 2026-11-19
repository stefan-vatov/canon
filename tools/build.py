#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""Generate the per-harness guidance artifacts from canon-core.md into dist/.

canon-core.md is the single source of truth. Everything a consumer copies is
generated under dist/, mirroring the path it should be copied TO in a target
repo:

  dist/CLAUDE.md  -> <repo>/CLAUDE.md  (Claude Code)
  dist/AGENTS.md  -> <repo>/AGENTS.md  (Codex, Pi, and other AGENTS.md readers)

Each artifact is one managed block between BEGIN/END PROJECT CANON markers,
so a fresh copy is already a managed file: the owner's own rules go above or
below the block in the same file, and upgrades replace only the block.

Canon ships only as repository instruction files; there is no system-prompt
delivery. Run after any edit to canon-core.md; never edit the generated files.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BEGIN = "<!-- BEGIN PROJECT CANON -->\n"
HEADER = "<!-- GENERATED from Project Canon's canon-core.md; edit project rules outside this block -->\n\n"
END = "<!-- END PROJECT CANON -->\n"


def main():
    core = (ROOT / "canon-core.md").read_text()
    if not core.endswith("\n"):
        core += "\n"
    block = BEGIN + HEADER + core + END

    generated = {
        DIST / "CLAUDE.md": block,
        DIST / "AGENTS.md": block,
    }

    for path, content in generated.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        changed = not path.exists() or path.read_text() != content
        path.write_text(content)
        print(f"{'wrote  ' if changed else 'fresh  '}{path.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
