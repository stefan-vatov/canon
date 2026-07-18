#!/usr/bin/env bash
# Adapter: Claude Code. Env: WORKDIR, TASK_FILE, GUIDANCE_FILE, TRANSCRIPT.
# Subcommands: install (place guidance, pre-baseline), run (execute agent).
set -euo pipefail

install_guidance() {
  python3 - "$GUIDANCE_FILE" "$WORKDIR" "CLAUDE.md" <<'PY'
import os, secrets, shutil, stat, sys
source, workdir, target = sys.argv[1:]
flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
parts = [p for p in workdir.split(os.sep) if p not in ("", ".")]
if ".." in parts: raise SystemExit("guidance destination may not contain '..'")
directory = os.open(os.sep if os.path.isabs(workdir) else ".", flags); temporary = None
try:
    for part in parts:
        child = os.open(part, flags, dir_fd=directory); os.close(directory); directory = child
    try: target_stat = os.stat(target, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError: target_stat = None
    if target_stat is not None and not stat.S_ISREG(target_stat.st_mode):
        raise SystemExit("guidance destination must be a regular, non-symlink file")
    source_fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        source_stat = os.fstat(source_fd)
        if not stat.S_ISREG(source_stat.st_mode): raise SystemExit("guidance source must be a regular file")
        temporary = f".canon-guidance-{os.getpid()}-{secrets.token_hex(8)}"
        output_fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                            getattr(os, "O_NOFOLLOW", 0), stat.S_IMODE(source_stat.st_mode),
                            dir_fd=directory)
        with os.fdopen(source_fd, "rb", closefd=False) as src, os.fdopen(output_fd, "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.replace(temporary, target, src_dir_fd=directory, dst_dir_fd=directory); temporary = None
    finally: os.close(source_fd)
finally:
    if temporary is not None:
        try: os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError: pass
    os.close(directory)
PY
}

scrub_worker_env() {
  unset WORKDIR TASK_FILE GUIDANCE_FILE TRANSCRIPT JUDGE_CMD IMPROVER_CMD \
    ROOT EVALS SCENARIO SCEN_DIR HARNESS RUNS JUDGE GUIDANCE ADAPTER_SOURCE \
    STAMP OUT PRIVATE_STATE FROZEN_SCENARIO FROZEN_EVALUATOR FROZEN_GUIDANCE \
    ADAPTER PROVENANCE CHECKER JUDGE_SCRIPT SUMMARIZER BATCH_ID RUN WORK \
    STATE STATE_KEY PRIVATE_TASK STEP_DIR STEP BASELINE JUDGE_REQUEST \
    BATCH_FINALIZED OVERALL_FAILED AGENT_STATUS JUDGE_STATUS RUN_FAILED \
    CHECK_FILES JUDGE_FILE STATE_FILES RUN_STATUS FINISH_ARGS EVAL_MODEL EVAL_REASONING
}

case "${1:-run}" in
  install)
    install_guidance
    ;;
  run)
    cd "$WORKDIR"
    agent_prompt="$(cat "$TASK_FILE")"
    transcript_path="$TRANSCRIPT"
    adapter_model="${EVAL_MODEL:-}"
    export -n agent_prompt transcript_path adapter_model 2>/dev/null || true
    scrub_worker_env
    # stream-json keeps tool calls in the transcript so the judge can verify
    # Canon-read-before-exploration ordering. EVAL_MODEL pins the model.
    args=(-p "$agent_prompt")
    [[ -z "$adapter_model" ]] || args+=(--model "$adapter_model")
    claude "${args[@]}" --verbose --output-format stream-json \
      > "$transcript_path" 2>&1
    ;;
  *)
    echo "usage: claude.sh install|run" >&2; exit 1;;
esac
