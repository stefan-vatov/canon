#!/usr/bin/env bash
# Adapter: stub. Runs no agent and changes nothing in the workspace.
# Exists to test the eval/optimizer plumbing for free: scenarios that
# require agent action will fail their checks, which is the expected signal.
set -euo pipefail

case "${1:-run}" in
  install)
    cp "$GUIDANCE_FILE" "$WORKDIR/CLAUDE.md"
    ;;
  run)
    echo "stub adapter: no agent was run" > "$TRANSCRIPT"
    ;;
  *)
    echo "usage: stub.sh install|run" >&2; exit 1;;
esac
