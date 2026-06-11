#!/usr/bin/env bash
# Adapter: Pi. Env: WORKDIR, TASK_FILE, GUIDANCE_FILE, TRANSCRIPT.
# Subcommands: install (place guidance, pre-baseline), run (execute agent).
# NOTE: verify the headless invocation against your Pi version (`pi --help`);
# adjust the `run` branch if the flag differs.
set -euo pipefail

case "${1:-run}" in
  install)
    mkdir -p "$WORKDIR/.pi"
    cp "$GUIDANCE_FILE" "$WORKDIR/.pi/APPEND_SYSTEM.md"
    ;;
  run)
    cd "$WORKDIR"
    pi -p "$(cat "$TASK_FILE")" \
      ${EVAL_MODEL:+--model "$EVAL_MODEL"} \
      > "$TRANSCRIPT" 2>&1 || true
    ;;
  *)
    echo "usage: pi.sh install|run" >&2; exit 1;;
esac
