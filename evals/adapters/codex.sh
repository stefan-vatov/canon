#!/usr/bin/env bash
# Adapter: OpenAI Codex CLI. Env: WORKDIR, TASK_FILE, GUIDANCE_FILE, TRANSCRIPT.
# Subcommands: install (place guidance, pre-baseline), run (execute agent).
set -euo pipefail

case "${1:-run}" in
  install)
    cp "$GUIDANCE_FILE" "$WORKDIR/AGENTS.md"
    ;;
  run)
    cd "$WORKDIR"
    codex exec --sandbox workspace-write \
      ${EVAL_MODEL:+-m "$EVAL_MODEL"} \
      ${EVAL_REASONING:+-c "model_reasoning_effort=\"$EVAL_REASONING\""} \
      "$(cat "$TASK_FILE")" \
      > "$TRANSCRIPT" 2>&1 || true
    ;;
  *)
    echo "usage: codex.sh install|run" >&2; exit 1;;
esac
