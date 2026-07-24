# How to run and adopt Canon evaluations

This playbook shows you how to run an attributable Canon evaluation, compare a
guidance candidate with the current core, validate the resulting artifacts,
and adopt or recover safely. Run every command from the repository root.
`evals/README.md` documents the harness and scenarios; `BASELINES.md` is the
durable results ledger; `RESEARCH.md` records the evidence behind scenarios.

## Current state: 2026-07-24

The current worktree contains the invariant-first rework:

- schema-v2 batch and run receipts bind canonical checks, successful judge
  output, temporal state, retained guidance, scenarios, and selected evaluator
  inputs with SHA-256;
- Canon records architectural laws, product invariants, decisions, and
  validation links rather than source inventories;
- the doctor validates metadata, normative routes, links, scratch isolation,
  and safe repository-relative validation evidence paths without coupling
  source changes to docs;
- scenario 05 requires no Canon edit for a behavior-preserving extraction, and
  scenario 08 rejects function-level inventory prose;
- scenarios 04 and 10 use authenticated path-and-byte snapshots for temporal
  preservation checks;
- missing routing telemetry is `unsupported`, never an automatic pass;
- holdout tests run in disposable copies; fixture tests run in the per-run
  workspace under the configured test sandbox;
- deterministic regressions cover Canon validation and eval integrity;
- `canon-core.md` supplies the shared Canon section; `tools/build.py` combines
  it with two templates to write five files under `dist/`.

The July 18 integrity work remains in place, but its model scores predate the
new guidance, rubric, and scenario set. **No live paid-model batch has been run
after the invariant-first rework.** Treat all earlier scores in
`BASELINES.md` as historical and incomparable. The next paid run must establish
the behavioral baseline for this revision.

## Prerequisites and pins

You need Bash, Git, `uv`, the selected worker CLI, credentials/quota for the
worker and judge, and a test-execution sandbox. The commands below use the
Codex adapter. For an adoption-grade judged run, export all three pins before
starting:

- `EVAL_MODEL`: the exact worker model ID;
- `EVAL_REASONING`: the exact Codex reasoning tier;
- `JUDGE_CMD`: a stable shell command that pins the judge model and settings.

There is no default judge. `JUDGE_CMD` is executed through `/bin/sh -c`, reads
the assembled judge prompt on standard input, and must write only the JSON
object requested by `evals/judge/judge-prompt.md` to standard output. Pin the
model and effort inside that command. Keep credentials in the command's
environment, not in the command string.

Run this preflight after exporting your real values. The `${VAR:?}` guards are
intentional: they prevent an unpinned run from starting.

```bash
set -euo pipefail

test "$(git rev-parse --show-toplevel)" = "$PWD"
command -v git >/dev/null
command -v uv >/dev/null
command -v codex >/dev/null
test -x evals/adapters/codex.sh

: "${EVAL_MODEL:?export the exact worker model ID}"
: "${EVAL_REASONING:?export the exact Codex reasoning tier}"
: "${JUDGE_CMD:?export a judge command with an explicit model and settings}"
export EVAL_MODEL EVAL_REASONING JUDGE_CMD

if { test "$(uname -s)" != Darwin || \
     test ! -x /usr/bin/sandbox-exec; } && \
   test -z "${CANON_EVAL_SANDBOX_CMD:-}" && \
   test "${CANON_EVAL_ALLOW_HOST_EXECUTION:-0}" != 1; then
  echo "configure CANON_EVAL_SANDBOX_CMD before running fixture code" >&2
  exit 1
fi
```

On macOS, the checker uses `/usr/bin/sandbox-exec` when it is executable. On other
platforms, set `CANON_EVAL_SANDBOX_CMD` to a sandbox wrapper containing
`{command}` and `{workdir}` substitutions. `CANON_EVAL_ALLOW_HOST_EXECUTION=1`
is an explicit unsafe opt-in that runs agent-controlled fixture code on the
host. The built-in profile is not a confidentiality boundary; use a disposable
host or container for untrusted fixtures and never put secrets in them.

The manifest records the requested worker model/reasoning and a hash of the
judge command string. It does not resolve or authenticate the actual provider,
model, CLI version, executable contents, credentials, or ambient configuration.
It also does not attest the OS, `uv`/Git versions, sandbox wrapper or unsafe
host-execution mode. Record material runtime identities and environment details
in `BASELINES.md`, and run comparisons from a dedicated unchanged worktree and
toolchain.

## Run the deterministic integrity gate

Run this gate before spending model credits and after changing the evaluator,
doctor, scenarios, or guidance:

```bash
PYTHONDONTWRITEBYTECODE=1 \
  uv run python -m unittest discover -s tests -p 'test_*.py' -v

uv run python -m py_compile tools/*.py evals/bin/*.py tests/*.py
bash -n evals/bin/*.sh evals/adapters/*.sh

uv run python - <<'PY'
import json
from pathlib import Path

paths = sorted(Path("evals/scenarios").rglob("*.json"))
for path in paths:
    json.loads(path.read_text())
print(f"validated {len(paths)} scenario JSON files")
PY
```

The first command currently ends with `Ran 9 tests` and `OK`. It invokes no
model. The other commands validate Python syntax, shell syntax, and all
scenario JSON.

### Smoke-test the end-to-end plumbing without a model

After configuring the platform sandbox, run one stub batch:

```bash
set -euo pipefail

unset JUDGE_CMD
STUB_LOG="$(mktemp "${TMPDIR:-/tmp}/canon-stub.XXXXXX")"
evals/bin/run-eval.sh \
  --scenario 02-feature \
  --harness stub \
  --runs 1 \
  --no-judge | tee "$STUB_LOG"

STUB_DIR="$(sed -n 's/^results: //p' "$STUB_LOG")"
test -d "$STUB_DIR"

uv run --script \
  "$STUB_DIR/inputs/evaluator/evals/bin/summarize.py" \
  "$STUB_DIR"

uv run python - "$STUB_DIR" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads((Path(sys.argv[1]) / "summary.json").read_text())
assert summary.get("complete") is True, summary
assert summary.get("pass_all_required") is False, summary
print("stub provenance smoke passed; required behavior gate failed as expected")
PY
```

The stub changes no task code and is intentionally a poor agent. Its score is
not worker behavior evidence; this command checks orchestration, test sandbox,
receipts, retained inputs, and summary validation only.

## Run one judged A/B comparison wave

`run-eval.sh` accepts one guidance file, so Canon has no native two-variant
batch. An A/B round is two independently receipted bundles run back-to-back
from the same unchanged worktree and runtime. The compatibility check catches
many mismatches, but it cannot prove temporal pairing. For a marginal result,
run a second independent wave in reverse order.

The recipe below freezes both guidance files before either batch begins, edits
one candidate, and captures the exact result directories without guessing
timestamped names.

```bash
set -euo pipefail

: "${EVAL_MODEL:?export the exact worker model ID}"
: "${EVAL_REASONING:?export the exact Codex reasoning tier}"
: "${JUDGE_CMD:?export the pinned judge command}"
export EVAL_MODEL EVAL_REASONING JUDGE_CMD

SCENARIO=10-supersede
RUNS=3
HARNESS=codex
ROUND_DIR="$(mktemp -d "${TMPDIR:-/tmp}/canon-ab.XXXXXX")"
BASELINE_GUIDANCE="$ROUND_DIR/baseline.md"
CANDIDATE_GUIDANCE="$ROUND_DIR/candidate.md"

cp canon-core.md "$BASELINE_GUIDANCE"
cp "$BASELINE_GUIDANCE" "$CANDIDATE_GUIDANCE"
"${EDITOR:-vi}" "$CANDIDATE_GUIDANCE"
cmp -s "$BASELINE_GUIDANCE" "$CANDIDATE_GUIDANCE" && {
  echo "candidate is identical to baseline" >&2
  exit 1
}

git status --porcelain --untracked-files=all > "$ROUND_DIR/worktree.before"

evals/bin/run-eval.sh \
  --scenario "$SCENARIO" \
  --harness "$HARNESS" \
  --runs "$RUNS" \
  --guidance "$BASELINE_GUIDANCE" | tee "$ROUND_DIR/baseline.log"
BASELINE_DIR="$(sed -n 's/^results: //p' "$ROUND_DIR/baseline.log")"
test -d "$BASELINE_DIR"

evals/bin/run-eval.sh \
  --scenario "$SCENARIO" \
  --harness "$HARNESS" \
  --runs "$RUNS" \
  --guidance "$CANDIDATE_GUIDANCE" | tee "$ROUND_DIR/candidate.log"
CANDIDATE_DIR="$(sed -n 's/^results: //p' "$ROUND_DIR/candidate.log")"
test -d "$CANDIDATE_DIR"

git status --porcelain --untracked-files=all > "$ROUND_DIR/worktree.after"
cmp "$ROUND_DIR/worktree.before" "$ROUND_DIR/worktree.after"

printf 'baseline:  %s\ncandidate: %s\n' "$BASELINE_DIR" "$CANDIDATE_DIR"
```

Each result is created under
`evals/results/YYYYMMDD-HHMMSS-SCENARIO-HARNESS-PID/`. The runner prints the
absolute path near the start; that `results:` line is not completion evidence.
Wait for each process to finish and validate both bundles.

For a mechanical-only development smoke, omit the judge preflight, unset
`JUDGE_CMD`, and add `--no-judge` to both commands. Do not use an unjudged smoke
as the sole evidence for a qualitative guidance adoption.

## Validate artifacts and compare the pair

Use the baseline bundle's retained summarizer. This revalidates with the same
summarizer bytes used during the batch, rather than whatever happens to be in
the current worktree later.

```bash
set -euo pipefail

: "${BASELINE_DIR:?run the baseline bundle first}"
: "${CANDIDATE_DIR:?run the candidate bundle first}"

FROZEN_SUMMARIZER="$BASELINE_DIR/inputs/evaluator/evals/bin/summarize.py"
test -f "$FROZEN_SUMMARIZER"

uv run --script "$FROZEN_SUMMARIZER" \
  "$BASELINE_DIR" \
  "$CANDIDATE_DIR"

uv run python - "$BASELINE_DIR" "$CANDIDATE_DIR" <<'PY'
import json
import sys
from pathlib import Path

failed = []
for raw in sys.argv[1:]:
    result = Path(raw)
    summary = json.loads((result / "summary.json").read_text())
    if summary.get("complete") is not True:
        failed.append(f"{result}: artifact lineage is incomplete")
    if summary.get("pass_all_required") is not True:
        failed.append(f"{result}: a required check failed")
    print(
        f"{result.name}: mechanical_mean={summary.get('mechanical_mean')} "
        f"judge_mean={summary.get('judge_mean')}"
    )
if failed:
    raise SystemExit("\n".join(failed))
PY
```

The summarizer verifies retained guidance/scenario and selected evaluator
hashes, terminal batch/run receipts, expected run lineage, canonical artifact
paths and digests, check/judge schemas, and comparison compatibility. It
refuses incompatible scenario hashes, harness/adapter, requested worker pins,
judge status/command hash, Git revision/dirty state, run count, or selected
evaluator hashes.

It does **not** compute an A/B delta, floor, winner, or adoption decision. Read
the printed per-run tables; the lowest per-run value is the observed floor. Keep
mechanical and judge scores separate. `complete: true` means the declared
artifact lineage is internally valid; only `pass_all_required: true` means all
required correctness/integrity checks passed.

Known provenance boundary: transcripts, workspaces, raw judge I/O, and the
derived summary are not receipt-bound canonical artifacts. The selected
evaluator hash map includes the checker, Canon doctor, and shared Canon path
library, but still omits retained files such as `run-eval.sh` and
`distill-transcript.py`. This is why an unchanged same-wave toolchain and a
durable runtime record remain mandatory even after the validator passes.

## Decide whether to adopt

Adoption is a human gate; no script implements it. Require all of the
following:

1. Both bundles are compatible, `complete: true`, and
   `pass_all_required: true`.
2. The candidate improves a deliberately discriminating worker stratum with
   headroom. Start at `n >= 3`; confirm a marginal change in a fresh,
   reverse-order wave instead of treating noise as a win.
3. The per-run floor and catastrophic-miss rate improve or hold. A higher mean
   that introduces a severe miss is not an adoption.
4. A capable worker stratum and an optimizer-blind holdout show no regression,
   using their own matched pairs and the same pins within each pair.
5. Mechanical and judge metrics tell a coherent story, failed judge criteria
   have been read, and unsupported telemetry is not claimed as success.
6. The diff is general guidance, not encoded fixture answers, and every change
   is explainable from observed failures.

Record wins, losses, exact worker/judge identities, CLI versions, run counts,
bundle paths, per-run floors, means, and known limitations in `BASELINES.md`.
Result directories are git-ignored; the baseline ledger is the durable record.

### Apply an accepted candidate and rebuild

After the candidate passes every gate, review and adopt the exact retained
guidance that was evaluated:

```bash
set -euo pipefail

: "${CANDIDATE_DIR:?set the accepted candidate result directory}"
ACCEPTED="$CANDIDATE_DIR/guidance-used.md"
test -f "$ACCEPTED"

set +e
diff -u canon-core.md "$ACCEPTED"
DIFF_STATUS=$?
set -e
test "$DIFF_STATUS" -le 1

cp "$ACCEPTED" canon-core.md
uv run --script tools/build.py

REBUILD_CHECK="$(uv run --script tools/build.py)"
printf '%s\n' "$REBUILD_CHECK"
if printf '%s\n' "$REBUILD_CHECK" | grep -q '^wrote'; then
  echo "generated artifacts were not stable after rebuild" >&2
  exit 1
fi

PYTHONDONTWRITEBYTECODE=1 \
  uv run python -m unittest discover -s tests -p 'test_*.py' -v
git diff --check -- canon-core.md dist/
git status --short -- canon-core.md dist/ evals/BASELINES.md
```

The first build may print `wrote`; the second must print only `fresh`. Include
`canon-core.md`, all changed generated files under `dist/`, and the
`BASELINES.md` record in the same reviewed change. Never edit generated files
by hand.

## Use the optimizer for proposals only

`optimize.py` is exploration tooling, not adoption-grade paired A/B. It
evaluates a cached baseline and later candidates in separate batches, blends
mechanical and judge means, uses one configured stratum, and does not enforce
the floor, capable-tier, or holdout gates above. Its failure collector reads
`checks.json` but misses multi-session `checks-*.json` files.

A judged optimizer run requires three explicit commands/pins:

- `IMPROVER_CMD`: reads the improver prompt on standard input and writes the
  complete replacement guidance on standard output, without fences or prose;
- `EVAL_MODEL` and `EVAL_REASONING`: pin the Codex worker;
- `JUDGE_CMD`: pins the judge and emits the required JSON.

Run a proposal search only after exporting those exact values:

```bash
set -euo pipefail

: "${IMPROVER_CMD:?export the pinned improver command}"
: "${EVAL_MODEL:?export the exact worker model ID}"
: "${EVAL_REASONING:?export the exact Codex reasoning tier}"
: "${JUDGE_CMD:?export the pinned judge command}"
export IMPROVER_CMD EVAL_MODEL EVAL_REASONING JUDGE_CMD

uv run --script evals/bin/optimize.py \
  --scenarios 06-decisions,08-routing \
  --harness codex \
  --runs 3 \
  --iterations 3 \
  --min-delta 0.02
```

The improver has a 600-second timeout. The optimizer writes candidates,
`best.md`, and `history.json` under `evals/results/opt-TIMESTAMP/`; evaluated
batches are sibling timestamped result directories. It never changes
`canon-core.md`. The optimizer artifacts do not authenticate the exact
improver command or hash, model/provider/version, or optimizer source revision,
and a nonzero improver exit is not checked before stdout is considered. Record
those details yourself and treat `best.md` as an unauthenticated proposal.
Audit it, then re-run it through the manual paired adoption path before
shipping it.

## Recover from failures

### `summary.json` is missing after a completed batch

If `batch-receipt.json` is completed and retained inputs exist, regenerate the
derived summary with the frozen validator:

```bash
set -euo pipefail
: "${RESULT_DIR:?set the completed result directory}"

uv run --script \
  "$RESULT_DIR/inputs/evaluator/evals/bin/summarize.py" \
  "$RESULT_DIR"
```

The validator replaces `summary.json` and exits nonzero if the bundle is not
valid. It has positional result-directory arguments only; do not pass
`--help`, which is interpreted as a directory name.

### The batch is interrupted, failed, incomplete, or digest-mismatched

It is not resumable. Preserve the directory for diagnosis, then rerun the
entire original command into a new result directory with the same guidance,
scenario, harness, run count, judge setting, and pins. Do not copy successful
runs between batches, edit canonical artifacts, regenerate receipts, or reuse
archived temporal state. Each run's HMAC key is ephemeral, so temporal-state
files are evidence, not checkpoints.

Normal failures best-effort write a failed terminal receipt and clean private
state. A hard kill can leave `canon-eval-state.*`, `canon-eval-runtime-*`, or
`canon-holdout-*` directories below the system temporary directory. Confirm no
evaluation is active before inspecting or removing any orphan.

### `complete: true` but `pass_all_required: false`

The batch is valid behavioral evidence, not a corrupt batch. Keep it as a
negative result, inspect `summary.json`, canonical `checks*.json`, and judge
reasons, and reject or revise the candidate. Runner and summarizer exit zero do
not override this gate.

### `incompatible result bundles; comparison refused`

Do not force or hand-edit the comparison. Rerun both variants in one unchanged
wave with identical scenario, harness, run count, requested worker model and
reasoning, judge command, source revision/state, and evaluator. Compatibility
does not prove they were run close together, so keep the logs and runtime
record from the same wave.

### The judge or worker fails

- Judge: inspect `run-N/judge-err.txt` and `run-N/judge-raw.txt`; fix the pinned
  command or its JSON response, then rerun the full batch.
- Worker: inspect `run-N/transcript*.txt`; restore authentication, quota, model
  availability, and CLI configuration, then rerun. Infrastructure aborts are
  never guidance scores.
- Sandbox: configure `CANON_EVAL_SANDBOX_CMD` on non-macOS, or make a deliberate
  unsafe-host decision; then rerun the full batch.

### The optimizer is interrupted

There is no optimizer resume checkpoint. Candidate files and child batches may
remain useful for diagnosis, but `best.md` and `history.json` are authoritative
only after normal completion. Audit a candidate, restart with that file passed
to `--guidance` if appropriate, and treat the new optimizer directory as a new
exploration run.
