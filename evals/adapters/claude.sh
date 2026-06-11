#!/usr/bin/env bash
# Adapter: Claude Code. Env: WORKDIR, TASK_FILE, GUIDANCE_FILE, TRANSCRIPT.
# Subcommands: install (place guidance, pre-baseline), run (execute agent).
set -euo pipefail

case "${1:-run}" in
  install)
    cp "$GUIDANCE_FILE" "$WORKDIR/CLAUDE.md"
    ;;
  run)
    cd "$WORKDIR"
    # stream-json keeps tool calls in the transcript so the judge can verify
    # Canon-read-before-exploration ordering. EVAL_MODEL pins the model.
    claude -p "$(cat "$TASK_FILE")" \
      ${EVAL_MODEL:+--model "$EVAL_MODEL"} \
      --permission-mode bypassPermissions \
      --verbose --output-format stream-json \
      > "$TRANSCRIPT" 2>&1 || true
    ;;
  *)
    echo "usage: claude.sh install|run" >&2; exit 1;;
esac
