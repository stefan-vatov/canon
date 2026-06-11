#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""Generate the per-harness guidance artifacts from canon-core.md.

canon-core.md is the single source of truth. This script writes:

  .pi/APPEND_SYSTEM.md   Pi project-local append-system prompt
  .codex/system.md       templates/codex-base.md + the Canon section
  dist/CLAUDE.md         Claude Code project memory file
  dist/AGENTS.md         Codex/agents.md-convention guidance file

Run after any edit to canon-core.md; never edit the generated files.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADER = "<!-- GENERATED from canon-core.md by tools/build.py - edit canon-core.md instead -->\n\n"


def main():
    core = (ROOT / "canon-core.md").read_text()
    codex_base = (ROOT / "templates" / "codex-base.md").read_text()

    outputs = {
        ROOT / ".pi" / "APPEND_SYSTEM.md": HEADER + core,
        ROOT / "dist" / "CLAUDE.md": HEADER + core,
        ROOT / "dist" / "AGENTS.md": HEADER + core,
        ROOT / ".codex" / "system.md":
            codex_base.rstrip("\n") + "\n\n# Project Canon\n\n" + HEADER + core,
    }
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        changed = not path.exists() or path.read_text() != content
        path.write_text(content)
        print(f"{'wrote  ' if changed else 'fresh  '}{path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
