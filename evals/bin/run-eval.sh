#!/usr/bin/env bash
# Run one eval scenario N times against a harness and score the results.
#
# usage: evals/bin/run-eval.sh --scenario 02-feature [--harness claude|codex|pi]
#                              [--runs N] [--guidance FILE] [--no-judge]
#
# Scenario shapes:
#   single-session: scenarios/<name>/task.md + expected.json
#   multi-session:  scenarios/<name>/tasks/NN-<step>/task.md — each step runs
#                   as a FRESH agent session in the same workspace (this is
#                   how cross-session Canon memory is exercised); a step may
#                   carry its own expected.json, and the scenario root
#                   expected.json is checked after the final step.
#
# env: EVAL_MODEL  pin the agent model (passed to the adapter)
#      JUDGE_CMD   override the judge invocation (default: claude -p)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVALS="$ROOT/evals"

SCENARIO="" HARNESS="claude" RUNS=1 JUDGE=1
GUIDANCE="$ROOT/canon-core.md"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scenario) SCENARIO="$2"; shift 2;;
    --harness)  HARNESS="$2"; shift 2;;
    --runs)     RUNS="$2"; shift 2;;
    --guidance) GUIDANCE="$2"; shift 2;;
    --no-judge) JUDGE=0; shift;;
    *) echo "unknown arg: $1" >&2; exit 1;;
  esac
done

if [[ -z "$SCENARIO" ]]; then
  echo "usage: run-eval.sh --scenario NAME [--harness claude|codex|pi] [--runs N] [--guidance FILE] [--no-judge]" >&2
  echo "scenarios:" >&2; ls "$EVALS/scenarios" >&2
  exit 1
fi

SCEN_DIR="$EVALS/scenarios/$SCENARIO"
ADAPTER="$EVALS/adapters/$HARNESS.sh"
[[ -d "$SCEN_DIR" ]] || { echo "no such scenario: $SCENARIO" >&2; exit 1; }
[[ -x "$ADAPTER" ]] || { echo "no such adapter: $ADAPTER" >&2; exit 1; }
GUIDANCE="$(cd "$(dirname "$GUIDANCE")" && pwd)/$(basename "$GUIDANCE")"

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$EVALS/results/$STAMP-$SCENARIO-$HARNESS"
mkdir -p "$OUT"
cp "$GUIDANCE" "$OUT/guidance-used.md"
echo "results: $OUT"

run_check() { # workdir expected_json out_json
  uv run --script "$EVALS/bin/check.py" \
    --workdir "$1" --expected "$2" --out "$3" || echo "warn: check.py failed" >&2
}

for i in $(seq 1 "$RUNS"); do
  RUN="$OUT/run-$i"
  WORK="$RUN/workspace"
  mkdir -p "$RUN"
  cp -R "$SCEN_DIR/fixture" "$WORK"

  export WORKDIR="$WORK" GUIDANCE_FILE="$GUIDANCE"

  # Guidance is installed before the baseline commit so it never shows in the
  # agent's diff.
  "$ADAPTER" install
  git -C "$WORK" init -q
  git -C "$WORK" -c user.email=eval@local -c user.name=eval add -A
  git -C "$WORK" -c user.email=eval@local -c user.name=eval commit -qm baseline

  if [[ -d "$SCEN_DIR/tasks" ]]; then
    # Multi-session chain: one fresh agent session per task step.
    for STEP_DIR in "$SCEN_DIR"/tasks/*/; do
      STEP="$(basename "$STEP_DIR")"
      export TASK_FILE="$STEP_DIR/task.md" TRANSCRIPT="$RUN/transcript-$STEP.txt"
      echo "[$SCENARIO/$HARNESS] run $i/$RUNS step $STEP: agent..."
      "$ADAPTER" run || echo "warn: adapter exited nonzero at $STEP" >&2
      if [[ -f "$STEP_DIR/expected.json" ]]; then
        run_check "$WORK" "$STEP_DIR/expected.json" "$RUN/checks-$STEP.json"
      fi
    done
    # Stitch per-step transcripts so the judge sees the whole chain.
    for t in "$RUN"/transcript-*.txt; do
      printf '\n===== session %s =====\n' "$(basename "$t")"
      cat "$t"
    done > "$RUN/transcript.txt"
    [[ -f "$SCEN_DIR/expected.json" ]] && \
      run_check "$WORK" "$SCEN_DIR/expected.json" "$RUN/checks.json"
  else
    export TASK_FILE="$SCEN_DIR/task.md" TRANSCRIPT="$RUN/transcript.txt"
    echo "[$SCENARIO/$HARNESS] run $i/$RUNS: agent..."
    "$ADAPTER" run || echo "warn: adapter exited nonzero" >&2
    run_check "$WORK" "$SCEN_DIR/expected.json" "$RUN/checks.json"
  fi

  if [[ "$JUDGE" == 1 ]]; then
    echo "[$SCENARIO/$HARNESS] run $i/$RUNS: judge..."
    "$EVALS/bin/judge.sh" "$RUN" "$SCEN_DIR" || echo "warn: judge failed" >&2
  fi
done

uv run --script "$EVALS/bin/summarize.py" "$OUT"
