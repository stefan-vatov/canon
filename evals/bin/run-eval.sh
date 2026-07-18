#!/usr/bin/env bash
# Run one immutable, attributable eval batch.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
EVALS="$ROOT/evals"

SCENARIO="" HARNESS="codex" RUNS=1 JUDGE=1
GUIDANCE="$ROOT/canon-core.md"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scenario) SCENARIO="$2"; shift 2;;
    --harness) HARNESS="$2"; shift 2;;
    --runs) RUNS="$2"; shift 2;;
    --guidance) GUIDANCE="$2"; shift 2;;
    --no-judge) JUDGE=0; shift;;
    *) echo "unknown arg: $1" >&2; exit 1;;
  esac
done

if ! [[ "$SCENARIO" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]]; then
  echo "--scenario must be one directory name" >&2; exit 1
fi
if ! [[ "$HARNESS" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]]; then
  echo "--harness must be one adapter name" >&2; exit 1
fi
if ! [[ "$RUNS" =~ ^[1-9][0-9]*$ ]]; then
  echo "--runs must be a positive integer" >&2; exit 1
fi
if [[ "$JUDGE" == 1 && -z "${JUDGE_CMD:-}" ]]; then
  echo "JUDGE_CMD is required when judging is enabled" >&2; exit 1
fi

SCEN_DIR="$EVALS/scenarios/$SCENARIO"
ADAPTER_SOURCE="$EVALS/adapters/$HARNESS.sh"
[[ -d "$SCEN_DIR" ]] || { echo "no such scenario: $SCENARIO" >&2; exit 1; }
[[ -x "$ADAPTER_SOURCE" ]] || { echo "no such adapter: $HARNESS" >&2; exit 1; }
[[ -f "$GUIDANCE" && ! -L "$GUIDANCE" ]] || { echo "guidance must be a regular file" >&2; exit 1; }
uv run --script "$EVALS/bin/provenance.py" validate-inputs \
  --root "$ROOT" --scenario-dir "$SCEN_DIR" --guidance "$GUIDANCE"
GUIDANCE="$(cd "$(dirname "$GUIDANCE")" && pwd -P)/$(basename "$GUIDANCE")"

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$EVALS/results/$STAMP-$SCENARIO-$HARNESS-$$"
PRIVATE_STATE="$(mktemp -d "${TMPDIR:-/tmp}/canon-eval-state.XXXXXX")"
FROZEN_SCENARIO="$PRIVATE_STATE/scenario"
FROZEN_EVALUATOR="$PRIVATE_STATE/evaluator"
FROZEN_GUIDANCE="$PRIVATE_STATE/guidance.md"
cp -R "$SCEN_DIR" "$FROZEN_SCENARIO"
cp "$GUIDANCE" "$FROZEN_GUIDANCE"
mkdir -p "$FROZEN_EVALUATOR/evals" "$FROZEN_EVALUATOR/tools"
cp -R "$EVALS/bin" "$EVALS/adapters" "$EVALS/judge" "$FROZEN_EVALUATOR/evals/"
cp "$EVALS/rubric.md" "$FROZEN_EVALUATOR/evals/rubric.md"
cp "$ROOT/tools/canonlib.py" "$FROZEN_EVALUATOR/tools/canonlib.py"
ADAPTER="$FROZEN_EVALUATOR/evals/adapters/$HARNESS.sh"
PROVENANCE="$FROZEN_EVALUATOR/evals/bin/provenance.py"
CHECKER="$FROZEN_EVALUATOR/evals/bin/check.py"
JUDGE_SCRIPT="$FROZEN_EVALUATOR/evals/bin/judge.sh"
SUMMARIZER="$FROZEN_EVALUATOR/evals/bin/summarize.py"
mkdir -p "$OUT"
cp "$FROZEN_GUIDANCE" "$OUT/guidance-used.md"

JUDGE_REQUEST=requested
[[ "$JUDGE" == 0 ]] && JUDGE_REQUEST=skipped
uv run --script "$PROVENANCE" batch \
  --out "$OUT" --root "$ROOT" --scenario-dir "$FROZEN_SCENARIO" \
  --scenario "$SCENARIO" --guidance "$OUT/guidance-used.md" \
  --guidance-source "$GUIDANCE" --harness "$HARNESS" \
  --adapter "$ADAPTER_SOURCE" --runs "$RUNS" --model "${EVAL_MODEL:-}" \
  --reasoning "${EVAL_REASONING:-}" --judge "$JUDGE_REQUEST" \
  --judge-command "${JUDGE_CMD:-}"
BATCH_ID="$(uv run python -c 'import json,sys; print(json.load(open(sys.argv[1]))["batch_id"])' "$OUT/manifest.json")"
echo "results: $OUT"

BATCH_FINALIZED=0
finalize() {
  local status=failed
  [[ "$BATCH_FINALIZED" == 1 ]] && status=completed
  if [[ -f "$OUT/manifest.json" && ! -f "$OUT/batch-receipt.json" ]]; then
    uv run --script "$PROVENANCE" batch-finish \
      --out "$OUT" --status "$status" >/dev/null 2>&1 || true
  fi
  rm -rf "$PRIVATE_STATE"
}
trap finalize EXIT

OVERALL_FAILED=0
for i in $(seq 1 "$RUNS"); do
  RUN="$OUT/run-$i"
  WORK="$RUN/workspace"
  STATE="$PRIVATE_STATE/state-run-$i"
  STATE_KEY="$(uv run python -c 'import secrets; print(secrets.token_hex(32))')"
  mkdir -p "$RUN" "$STATE"
  cp -R "$FROZEN_SCENARIO/fixture" "$WORK"

  export WORKDIR="$WORK" GUIDANCE_FILE="$FROZEN_GUIDANCE"
  AGENT_STATUS=completed
  JUDGE_STATUS=skipped
  RUN_FAILED=0
  CHECK_FILES=()

  if ! "$ADAPTER" install; then
    AGENT_STATUS=failed; RUN_FAILED=1
  fi
  git -C "$WORK" init -q --template=
  git -C "$WORK" -c user.email=eval@local -c user.name=eval add -A
  git -C "$WORK" -c user.email=eval@local -c user.name=eval \
    -c commit.gpgsign=false commit -qm baseline
  BASELINE="$(git -C "$WORK" rev-parse HEAD)"
  uv run --script "$PROVENANCE" run-start \
    --run "$RUN" --index "$i" --batch-id "$BATCH_ID" --baseline "$BASELINE"

  run_check() { # expected_json out_json
    local expected_json="$1" out_json="$2"
    if uv run --script "$CHECKER" \
      --workdir "$WORK" --expected "$expected_json" --out "$out_json" \
      --transcript-dir "$RUN" --baseline "$BASELINE" \
      --state-dir "$STATE" --state-key "$STATE_KEY"; then
      CHECK_FILES+=("$out_json")
    else
      RUN_FAILED=1
    fi
  }

  if [[ -d "$FROZEN_SCENARIO/tasks" ]]; then
    for STEP_DIR in "$FROZEN_SCENARIO"/tasks/*/; do
      STEP="$(basename "$STEP_DIR")"
      PRIVATE_TASK="$PRIVATE_STATE/task-$i-$STEP.md"
      cp "$STEP_DIR/task.md" "$PRIVATE_TASK"
      export TASK_FILE="$PRIVATE_TASK" TRANSCRIPT="$RUN/transcript-$STEP.txt"
      echo "[$SCENARIO/$HARNESS] run $i/$RUNS step $STEP: agent..."
      if ! "$ADAPTER" run; then
        AGENT_STATUS=failed; RUN_FAILED=1
      fi
      if [[ -f "$STEP_DIR/expected.json" ]]; then
        run_check "$STEP_DIR/expected.json" "$RUN/checks-$STEP.json"
      fi
    done
    : > "$RUN/transcript.txt"
    for transcript in "$RUN"/transcript-*.txt; do
      printf '\n===== session %s =====\n' "$(basename "$transcript")" >> "$RUN/transcript.txt"
      sed -n '1,$p' "$transcript" >> "$RUN/transcript.txt"
    done
    [[ -f "$FROZEN_SCENARIO/expected.json" ]] && \
      run_check "$FROZEN_SCENARIO/expected.json" "$RUN/checks.json"
  else
    PRIVATE_TASK="$PRIVATE_STATE/task-$i.md"
    cp "$FROZEN_SCENARIO/task.md" "$PRIVATE_TASK"
    export TASK_FILE="$PRIVATE_TASK" TRANSCRIPT="$RUN/transcript.txt"
    echo "[$SCENARIO/$HARNESS] run $i/$RUNS: agent..."
    if ! "$ADAPTER" run; then
      AGENT_STATUS=failed; RUN_FAILED=1
    fi
    run_check "$FROZEN_SCENARIO/expected.json" "$RUN/checks.json"
  fi

  JUDGE_FILE=""
  if [[ "$JUDGE" == 1 ]]; then
    echo "[$SCENARIO/$HARNESS] run $i/$RUNS: judge..."
    if "$JUDGE_SCRIPT" "$RUN" "$FROZEN_SCENARIO"; then
      JUDGE_STATUS=completed
      JUDGE_FILE="$RUN/judge.json"
    else
      JUDGE_STATUS=failed; RUN_FAILED=1
    fi
  fi

  STATE_FILES=()
  if compgen -G "$STATE/*.json" >/dev/null; then
    mkdir -p "$RUN/temporal-state"
    for state_file in "$STATE"/*.json; do
      cp "$state_file" "$RUN/temporal-state/$(basename "$state_file")"
      STATE_FILES+=("$RUN/temporal-state/$(basename "$state_file")")
    done
  fi

  RUN_STATUS=completed
  [[ "$RUN_FAILED" == 1 ]] && { RUN_STATUS=failed; OVERALL_FAILED=1; }
  FINISH_ARGS=(run-finish --run "$RUN" --status "$RUN_STATUS" \
    --agent-status "$AGENT_STATUS" --judge-status "$JUDGE_STATUS")
  for check_file in "${CHECK_FILES[@]}"; do FINISH_ARGS+=(--check "$check_file"); done
  [[ -n "$JUDGE_FILE" ]] && FINISH_ARGS+=(--judge-artifact "$JUDGE_FILE")
  for state_file in "${STATE_FILES[@]}"; do FINISH_ARGS+=(--state "$state_file"); done
  uv run --script "$PROVENANCE" "${FINISH_ARGS[@]}"
done

# Retain the frozen inputs only after all evaluated sessions have ended.
mkdir -p "$OUT/inputs"
cp -R "$FROZEN_SCENARIO" "$OUT/inputs/scenario"
cp -R "$FROZEN_EVALUATOR" "$OUT/inputs/evaluator"

if [[ "$OVERALL_FAILED" == 0 ]]; then
  BATCH_FINALIZED=1
fi
uv run --script "$PROVENANCE" batch-finish \
  --out "$OUT" --status "$([[ "$BATCH_FINALIZED" == 1 ]] && echo completed || echo failed)"
uv run --script "$SUMMARIZER" "$OUT"
[[ "$OVERALL_FAILED" == 0 ]]
