#!/usr/bin/env bash
# Assemble judge input from a run directory and score it with an LLM.
# usage: judge.sh RUN_DIR SCENARIO_DIR
# env: JUDGE_CMD  command that reads a prompt on stdin and prints a reply
#                 (default: claude -p). Point it at any model/harness.
set -euo pipefail

RUN="$1"; SCEN="$2"
EVALS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$RUN/workspace"

git -C "$WORK" add -A >/dev/null 2>&1 || true

{
  cat "$EVALS/judge/judge-prompt.md"
  echo; echo "## Rubric"; cat "$EVALS/rubric.md"
  if [[ -d "$SCEN/tasks" ]]; then
    echo; echo "## Tasks (each ran as a FRESH agent session, oldest first)"
    for t in "$SCEN"/tasks/*/task.md; do
      echo "### $(basename "$(dirname "$t")")"; cat "$t"; echo
    done
  else
    echo; echo "## Task given to the agent"; cat "$SCEN/task.md"
  fi
  echo; echo "## Agent's diff against the baseline"
  echo '```diff'
  git -C "$WORK" diff --cached HEAD | head -c 30000
  echo '```'
  echo; echo "## Canon files after the run"
  if [[ -d "$WORK/canon" ]]; then
    find "$WORK/canon" -name '*.md' -not -path '*/scratch/*' | sort | while read -r f; do
      echo "### ${f#"$WORK"/}"
      head -c 4000 "$f"; echo
    done
  else
    echo "(no canon/ directory exists)"
  fi
  echo; echo "## Mechanical check results"
  for c in "$RUN"/checks*.json; do
    [[ -f "$c" ]] && { echo "### $(basename "$c")"; cat "$c"; }
  done
  echo; echo "## Transcript (distilled action log)"
  if compgen -G "$RUN/transcript-*.txt" > /dev/null; then
    # Multi-session: distill each session separately so the judge sees the
    # ordered actions of every session, not raw stream-json noise.
    for t in "$RUN"/transcript-*.txt; do
      printf '\n===== session %s =====\n' "$(basename "$t" .txt | sed 's/^transcript-//')"
      uv run --script "$EVALS/bin/distill-transcript.py" "$t" 15000
    done
  else
    uv run --script "$EVALS/bin/distill-transcript.py" "$RUN/transcript.txt" 40000
  fi
} > "$RUN/judge-input.md"

JUDGE_CMD="${JUDGE_CMD:-claude -p}"
$JUDGE_CMD < "$RUN/judge-input.md" > "$RUN/judge-raw.txt" 2>"$RUN/judge-err.txt" || true

uv run python - "$RUN" <<'PYEOF'
import json, re, sys
from pathlib import Path

run = Path(sys.argv[1])
raw = (run / "judge-raw.txt").read_text(errors="replace")
match = re.search(r"\{.*\}", raw, re.DOTALL)
if not match:
    print("judge: no JSON found in output", file=sys.stderr)
    sys.exit(1)
data = json.loads(match.group(0))
scores = [c["score"] for c in data.get("criteria", []) if c.get("score") is not None]
data["judge_score"] = round(sum(scores) / len(scores), 3) if scores else None
(run / "judge.json").write_text(json.dumps(data, indent=2) + "\n")
print(f"judge: {data['judge_score']}")
PYEOF
