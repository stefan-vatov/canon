#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""Generate the per-harness guidance artifacts from canon-core.md into dist/.

canon-core.md is the single source of truth. Everything a consumer copies is
generated under dist/, mirroring the path it should be copied TO in a target
repo:

  dist/CLAUDE.md              -> <repo>/CLAUDE.md            (Claude Code)
  dist/AGENTS.md              -> <repo>/AGENTS.md            (Codex / AGENTS.md)
  dist/.pi/APPEND_SYSTEM.md   -> <repo>/.pi/APPEND_SYSTEM.md (Pi)
  dist/.codex/system.md       -> <repo>/.codex/system.md     (Codex full prompt)
  dist/.codex/config.toml     -> <repo>/.codex/config.toml   (static, wires system.md)

Run after any edit to canon-core.md; never edit the generated files. Sources
are canon-core.md, templates/codex-base.md, and templates/codex-config.toml.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
HEADER = "<!-- GENERATED from canon-core.md by tools/build.py - edit canon-core.md instead -->\n\n"


def main():
    core = (ROOT / "canon-core.md").read_text()
    codex_base = (ROOT / "templates" / "codex-base.md").read_text()
    codex_system = codex_base.rstrip("\n") + "\n\n# Project Canon\n\n" + HEADER + core

    generated = {
        DIST / "CLAUDE.md": HEADER + core,
        DIST / "AGENTS.md": HEADER + core,
        DIST / ".pi" / "APPEND_SYSTEM.md": HEADER + core,
        DIST / ".codex" / "system.md": codex_system,
    }
    # static files copied verbatim into dist/
    copied = {
        DIST / ".codex" / "config.toml": ROOT / "templates" / "codex-config.toml",
    }

    for path, content in generated.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        changed = not path.exists() or path.read_text() != content
        path.write_text(content)
        print(f"{'wrote  ' if changed else 'fresh  '}{path.relative_to(ROOT)}")

    for path, src in copied.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        content = src.read_text()
        changed = not path.exists() or path.read_text() != content
        path.write_text(content)
        print(f"{'wrote  ' if changed else 'fresh  '}{path.relative_to(ROOT)} (copied)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
