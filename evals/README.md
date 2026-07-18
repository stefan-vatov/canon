# How to run Canon evaluations

This guide shows you how to run, judge, verify, compare, optimize, and recover
Project Canon evaluation batches from the repository root.

Use [PLAYBOOK.md](PLAYBOOK.md) for the adoption discipline,
[BASELINES.md](BASELINES.md) for the result history, and
[RESEARCH.md](RESEARCH.md) for the evidence behind the harder scenarios.

## What a batch records

Each scenario is a small fixture repository, one or more task prompts, and an
`expected.json` contract. `evals/bin/run-eval.sh`:

1. freezes the scenario, guidance, adapter, evaluator scripts, prompt, and rubric;
2. copies the fixture into a disposable workspace;
3. installs the selected guidance, commits the Git baseline, and runs each task
   in a fresh agent process;
4. runs fixture checks in that run workspace and hidden holdouts in disposable
   copies;
5. optionally sends the assembled evidence to `JUDGE_CMD`;
6. writes hash-bound run receipts, a terminal batch receipt, and `summary.json`.

Results land in:

```text
evals/results/<timestamp>-<scenario>-<harness>-<pid>/
```

A completed bundle contains the tested `guidance-used.md`, `manifest.json`,
`batch-receipt.json`, frozen inputs under `inputs/`, per-run workspaces,
transcripts, checks, receipts, temporal snapshots, optional judge artifacts,
and `summary.json`. Results are Git-ignored; record durable conclusions in
`BASELINES.md`.

## Prerequisites

- Bash, Git, and [`uv`](https://docs.astral.sh/uv/).
- A writable checkout of this repository and temporary-directory access.
- For a live run, the selected adapter's CLI installed, authenticated, and able
  to run headlessly. The examples below use `codex`.
- For a judged run, an explicit `JUDGE_CMD` that follows the contract below.
- For optimization, an explicit `IMPROVER_CMD`; judged optimization also needs
  `JUDGE_CMD`.
- A sandbox for fixture and holdout test commands. On macOS, the checker uses
  `/usr/bin/sandbox-exec` with network denied. On other systems, configure
  `CANON_EVAL_SANDBOX_CMD` with `{command}` and `{workdir}` placeholders.

`CANON_EVAL_ALLOW_HOST_EXECUTION=1` bypasses that evaluator sandbox. Use it only
on a disposable machine for code you trust; agent-generated code then executes
directly on the host.

## Preflight the repository

Run these checks from the repository root:

```sh
test "$(git rev-parse --show-toplevel)" = "$PWD"
command -v bash
command -v git
command -v uv
test -x evals/bin/run-eval.sh
test -x evals/adapters/stub.sh
bash -n evals/bin/run-eval.sh evals/bin/judge.sh evals/adapters/*.sh
uv run python -m unittest discover -s tests -p 'test_*.py'
```

For the Codex adapter, also run:

```sh
command -v codex
test -x evals/adapters/codex.sh
codex --version
```

On a platform without the built-in macOS sandbox, make the missing sandbox an
explicit preflight failure:

```sh
if [[ "$(uname -s)" != Darwin || ! -x /usr/bin/sandbox-exec ]]; then
  if [[ -z "${CANON_EVAL_SANDBOX_CMD:-}" && "${CANON_EVAL_ALLOW_HOST_EXECUTION:-}" != 1 ]]; then
    echo 'Configure CANON_EVAL_SANDBOX_CMD before running evals.' >&2
    exit 1
  fi
fi
```

For comparisons, keep the repository state unchanged across both runs and use
the same scenario, adapter, run count, agent model, reasoning level, judge
command, and evaluator. A clean checkout makes the provenance easiest to audit.

## Run the free plumbing smoke test

The `stub` adapter installs the guidance, writes a transcript, and runs no
agent. It verifies runner, checker, receipt, provenance, and summarizer plumbing
without model cost:

```sh
env -u JUDGE_CMD \
  evals/bin/run-eval.sh \
  --scenario 02-feature \
  --harness stub \
  --runs 1 \
  --no-judge
```

The command prints an absolute `results:` path and a summary. The current
fixture produces a complete bundle while intentionally failing several
behavioral checks because no agent changed the workspace. That is expected:
the stub score is plumbing evidence, not evidence that the guidance works.

Inspect the newest smoke result without copying a path by hand:

```sh
SMOKE_DIR="$(find evals/results -mindepth 1 -maxdepth 1 \
  -type d -name '*-02-feature-stub-*' -print | sort | tail -n 1)"
test -n "$SMOKE_DIR"
uv run python -m json.tool "$SMOKE_DIR/summary.json"
```

## Run a live batch without a judge

Use `--no-judge` for a quick mechanical run. Unsetting an ambient `JUDGE_CMD`
keeps its hash out of no-judge comparison metadata:

```sh
env -u JUDGE_CMD \
  evals/bin/run-eval.sh \
  --scenario 02-feature \
  --harness codex \
  --runs 1 \
  --no-judge
```

One run is a functional check, not adoption evidence. For an actionable
comparison, pin the model and reasoning level and use at least three runs:

```sh
read -r -p 'Exact agent model ID: ' EVAL_MODEL
read -r -p 'Reasoning level: ' EVAL_REASONING
export EVAL_MODEL EVAL_REASONING

env -u JUDGE_CMD \
  evals/bin/run-eval.sh \
  --scenario 02-feature \
  --harness codex \
  --runs 3 \
  --no-judge
```

`EVAL_REASONING` is currently forwarded by the Codex adapter. Other adapters
may ignore it even though the requested value is retained in provenance.

## Configure a judge

There is deliberately no default judge. `JUDGE_CMD` is executed as:

```text
/bin/sh -c "$JUDGE_CMD" < judge-input.md > judge-raw.txt 2> judge-err.txt
```

The command contract is:

- **stdin:** UTF-8 Markdown containing the judge instructions, rubric, task or
  ordered tasks, staged diff, final permanent Canon files, mechanical check
  JSON, and a distilled transcript;
- **stdout:** one JSON object and nothing else—no Markdown fence or commentary;
- **stderr:** diagnostics only; they are retained in `judge-err.txt`;
- **exit:** zero on success; a nonzero exit fails the run and batch;
- **time/model:** handled by your command or wrapper, not by the harness.

The JSON object must have a non-empty `criteria` array. Use every criterion ID
listed in [rubric.md](rubric.md) exactly once. Each entry must contain a unique
string `id`, a `score` of `0`, `1`, or `null`, and a reason. Use `null` only
when the rubric says the criterion is not applicable. Include at least one
numeric score and a short top-level `notes` string. `judge.sh` calculates and
adds `judge_score` as the mean of the non-null scores.

Although the parser can extract JSON from surrounding text, extra prose or
multiple objects can make its greedy JSON match invalid. Emit only the object.
The current summarizer validates uniqueness and score types, but it does not
enforce the exact rubric ID set; a missing or invented ID silently changes the
denominator. Treat the complete rubric list as part of the wrapper contract.

Configure the exact command, including pinned model and options, then run a
judged batch:

```sh
read -r -p 'Exact judge command, including model and options: ' JUDGE_CMD
test -n "$JUDGE_CMD"
export JUDGE_CMD

EVAL_MODEL="$EVAL_MODEL" \
EVAL_REASONING="$EVAL_REASONING" \
JUDGE_CMD="$JUDGE_CMD" \
  evals/bin/run-eval.sh \
  --scenario 02-feature \
  --harness codex \
  --runs 3
```

The manifest records a hash of the `JUDGE_CMD` string, not the contents of a
wrapper executable or the model actually served behind it. Keep wrappers
immutable and record their digest and served model with the evaluation record.

## Verify and interpret a result

Every invocation prints its result directory. To select the newest ordinary
batch in a non-concurrent local workflow:

```sh
RESULT_DIR="$(find evals/results -mindepth 1 -maxdepth 1 \
  -type d -name '20*-*-*-*' -print | sort | tail -n 1)"
test -n "$RESULT_DIR"
uv run python -m json.tool "$RESULT_DIR/summary.json"
```

Interpret the summary fields separately:

| field | meaning |
|---|---|
| `complete` | The expected runs, frozen inputs, receipts, hashes, check schemas, and requested judge artifacts passed integrity validation. |
| `pass_all_required` | All checks marked `required` passed. This is a hard gate, but optional behavioral checks may still have failed. |
| `mechanical_mean` | Mean fraction of measured mechanical checks that passed. |
| `judge_mean` | Mean of non-null judged criteria, or `null` for `--no-judge`. |
| `failed` | Check or judge criterion IDs mapped to the runs that failed them. |
| `unsupported` | Telemetry that could not be measured. It is excluded, never counted as a pass. |
| `comparison_key` | The metadata that must match before two bundles can be compared. |

Process exit zero alone does not prove behavioral success. Require
`complete: true` and `pass_all_required: true`, then inspect
`mechanical_mean`, `judge_mean`, `failed`, and `unsupported`:

```sh
uv run python - "$RESULT_DIR/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1]))
assert summary["complete"] is True, summary
assert summary["pass_all_required"] is True, summary
print("mechanical_mean:", summary["mechanical_mean"])
print("judge_mean:", summary["judge_mean"])
print("failed:", summary["failed"])
print("unsupported:", summary["unsupported"])
PY
```

Re-running the retained summarizer verifies the bundle with the evaluator that
created it, rather than whatever code is currently checked out:

```sh
uv run --script \
  "$RESULT_DIR/inputs/evaluator/evals/bin/summarize.py" \
  "$RESULT_DIR"
```

## Compare a baseline and candidate

Run the baseline and candidate in the same wave from an unchanged checkout.
They are independent batches; the harness does not create a shared A/B batch
or prove that two runs were adjacent in time.

This mechanical-only example is runnable after the model pins above:

```sh
(
  set -euo pipefail
  : "${EVAL_MODEL:?Set EVAL_MODEL first}"
  : "${EVAL_REASONING:?Set EVAL_REASONING first}"

  cp canon-core.md /tmp/canon-candidate.md
  "${EDITOR:-vi}" /tmp/canon-candidate.md

  BASELINE_LOG="$(mktemp)"
  env -u JUDGE_CMD EVAL_MODEL="$EVAL_MODEL" EVAL_REASONING="$EVAL_REASONING" \
    evals/bin/run-eval.sh --scenario 02-feature --harness codex \
    --guidance canon-core.md --runs 3 --no-judge 2>&1 | tee "$BASELINE_LOG"
  BASELINE_DIR="$(sed -n 's/^results: //p' "$BASELINE_LOG" | tail -n 1)"

  CANDIDATE_LOG="$(mktemp)"
  env -u JUDGE_CMD EVAL_MODEL="$EVAL_MODEL" EVAL_REASONING="$EVAL_REASONING" \
    evals/bin/run-eval.sh --scenario 02-feature --harness codex \
    --guidance /tmp/canon-candidate.md --runs 3 --no-judge 2>&1 | tee "$CANDIDATE_LOG"
  CANDIDATE_DIR="$(sed -n 's/^results: //p' "$CANDIDATE_LOG" | tail -n 1)"

  test -n "$BASELINE_DIR"
  test -n "$CANDIDATE_DIR"
  uv run --script evals/bin/summarize.py "$BASELINE_DIR" "$CANDIDATE_DIR"
  rm -f "$BASELINE_LOG" "$CANDIDATE_LOG"
)
```

For a judged comparison, configure one immutable `JUDGE_CMD`, omit
`env -u JUDGE_CMD` and `--no-judge`, and pass the identical command string to
both runs.

`summarize.py` validates and prints both bundles, but it does not calculate a
delta or enforce the adoption rules in `PLAYBOOK.md`. Comparison is refused
unless both summaries have the same:

- scenario name and frozen scenario hash;
- harness and adapter;
- requested model and reasoning level;
- judge status and `JUDGE_CMD` string hash;
- source revision and dirty-state boolean;
- run count; and
- recorded evaluator hashes.

Guidance is intentionally excluded from the compatibility key. Compare only
one baseline/candidate scenario pair per invocation; bundles from different
scenarios are incompatible. If comparison is refused, each individually valid
summary may still have been written before the command exited nonzero.

## Run the optimizer

`evals/bin/optimize.py` performs heuristic hill climbing. It evaluates the
current best guidance, sends observed failures to `IMPROVER_CMD`, evaluates
the proposed candidate, and keeps it only when the blended mean improves by
`--min-delta` (default `0.02`). It is useful for proposing candidates, not for
making an adoption decision.

`IMPROVER_CMD` is executed with `shell=True` and receives an improver prompt
on stdin. It must print only the complete revised guidance Markdown on stdout;
one outer Markdown fence is tolerated and stripped. Keep it below the
600-second timeout and make it exit zero. Candidates are rejected if they:

- contain a fixture-specific term from `LEAK_TERMS`;
- have fewer than 30 or more than 200 lines; or
- do not mention `canon/`.

Configure the improver command:

```sh
read -r -p 'Exact improver command, including model and options: ' IMPROVER_CMD
test -n "$IMPROVER_CMD"
export IMPROVER_CMD
```

Run mechanical-only optimization:

```sh
: "${EVAL_MODEL:?Set EVAL_MODEL first}"
: "${EVAL_REASONING:?Set EVAL_REASONING first}"
: "${IMPROVER_CMD:?Set IMPROVER_CMD first}"

env -u JUDGE_CMD \
  EVAL_MODEL="$EVAL_MODEL" \
  EVAL_REASONING="$EVAL_REASONING" \
  IMPROVER_CMD="$IMPROVER_CMD" \
  uv run --script evals/bin/optimize.py \
  --scenarios 01-bootstrap,02-feature,03-drift \
  --harness codex \
  --runs 3 \
  --iterations 5 \
  --no-judge
```

Run judged optimization with the configured judge:

```sh
: "${JUDGE_CMD:?Set JUDGE_CMD first}"

EVAL_MODEL="$EVAL_MODEL" \
EVAL_REASONING="$EVAL_REASONING" \
IMPROVER_CMD="$IMPROVER_CMD" \
JUDGE_CMD="$JUDGE_CMD" \
  uv run --script evals/bin/optimize.py \
  --scenarios 01-bootstrap,02-feature,03-drift \
  --harness codex \
  --runs 3 \
  --iterations 5
```

The optimizer writes `iter-*-candidate.md`, `best.md`, and `history.json`
under `evals/results/opt-<timestamp>/`; it never changes `canon-core.md`.
`--improver-cmd` overrides the environment variable. The optimizer rejects
incomplete results and required-check failures, but it blends available means,
does not implement the playbook's floor/two-tier gates, and currently gathers
failure text only from `checks.json`, not multi-session `checks-*.json` files.
Optimizer artifacts do not record the improver command, model, provider,
version, or optimizer source revision. Record those separately; `best.md` and
`history.json` are proposal artifacts, not adoption provenance. Do not use a
stub optimization score as behavioral evidence.

## Adopt a candidate safely

`best.md` is an unauthenticated proposal. Do not copy it directly into
`canon-core.md`. Follow [PLAYBOOK.md](PLAYBOOK.md): evaluate the proposal in a
same-wave paired run, pass the capable-tier and holdout gates, then adopt the
accepted bundle's hash-validated `guidance-used.md`. Rebuild twice and record
the result in `BASELINES.md`.

## Recover a failed or interrupted batch

Batches cannot resume agent sessions. Every invocation creates a new result
directory, and the exit trap marks a started but unfinished batch `failed`
when it can. A hard kill may leave no terminal receipt or retained frozen
inputs. Either state is permanently invalid for comparison.

Keep the partial directory for diagnosis. If you did not save the printed
path, select the newest batch and inspect its evidence:

```sh
RESULT_DIR="$(find evals/results -mindepth 1 -maxdepth 1 \
  -type d -name '20*-*-*-*' -print | sort | tail -n 1)"
test -n "$RESULT_DIR"

test ! -f "$RESULT_DIR/batch-receipt.json" || \
  uv run python -m json.tool "$RESULT_DIR/batch-receipt.json"
test ! -f "$RESULT_DIR/summary.json" || \
  uv run python -m json.tool "$RESULT_DIR/summary.json"
find "$RESULT_DIR" -maxdepth 2 -type f \
  \( -name 'receipt.json' -o -name 'checks*.json' -o \
     -name 'transcript*.txt' -o -name 'judge-err.txt' \) -print
```

If every run receipt and the terminal batch receipt say `completed`, frozen
inputs exist, and only summary generation was interrupted, recreate the
summary with the retained evaluator:

```sh
uv run --script \
  "$RESULT_DIR/inputs/evaluator/evals/bin/summarize.py" \
  "$RESULT_DIR"
```

Otherwise, fix the external cause—agent authentication, credits, judge output,
sandbox configuration, or tool failure—and rerun the original
`evals/bin/run-eval.sh` command. Do not edit receipts, hashes, checks, judge
output, or `summary.json` to repair a bundle. The optimizer also has no resume
mode; `best.md` and `history.json` are guaranteed only after normal completion.

## Troubleshooting

### `JUDGE_CMD is required when judging is enabled`

Configure `JUDGE_CMD` as described above, or add `--no-judge` and unset the
ambient variable:

```sh
env -u JUDGE_CMD \
  evals/bin/run-eval.sh --scenario 02-feature --harness codex --runs 1 --no-judge
```

### `no evaluator sandbox configured`

Configure `CANON_EVAL_SANDBOX_CMD`. On a controlled disposable host only, you
can explicitly accept direct execution:

```sh
export CANON_EVAL_ALLOW_HOST_EXECUTION=1
```

### `incompatible result bundles; comparison refused`

Open each summary and compare its `comparison_key`. Rerun a same-wave pair
with identical scenario, toolchain, source state, run count, pins, and judge
command. Do not compare different scenarios in one summarizer invocation.

### `invalid eval result ...`

Read the reported missing, failed, corrupt, or digest-mismatched artifact.
Use the recovery procedure above; a failed receipt cannot be converted into a
completed receipt after the fact.

## Scenarios

| scenario | sessions | purpose |
|---|---:|---|
| `01-bootstrap` | 1 | Create a Canon while implementing a feature. |
| `02-feature` | 1 | Obey planted standards and canonize new behavior. |
| `03-drift` | 1 | Trust running code over contradictory Canon and repair the Canon. |
| `04-memory-chain` | 10 | Preserve and update knowledge across fresh sessions. |
| `05-staleness` | 1 | Refresh stale source-backed domain knowledge before using it. |
| `06-decisions` | 2 | Record rationale and use the decision when challenged later. |
| `07-pressure` | 1 | Preserve tests, Canon, and freshness discipline under urgency framing. |
| `08-routing` | 1 | Read the correct domain without bulk-loading distractors. |
| `09-abstention` | 1 | Surface a missing policy instead of fabricating it. |
| `10-supersede` | 3 | Apply a superseding decision while preserving authenticated prior history. |

One `04-memory-chain` run means ten fresh agent sessions in one workspace.
Only repository contents persist. Hidden tests run in disposable copies, so
they never become visible to later agent sessions. Start multi-session
scenarios at `--runs 1` and scale up only for a comparison you intend to use.

## Add a scenario

Create `evals/scenarios/<name>/` with a small `fixture/`, a `task.md`, and an
`expected.json`. For a multi-session scenario, replace `task.md` with ordered
`tasks/NN-step/task.md` directories; a step may have its own `expected.json`,
and the root contract runs after the final step.

A minimal contract looks like:

```json
{
  "test_cmd": "uv run python -m unittest discover -s . -p 'test_*.py'",
  "required_files": ["canon/manifest.md"],
  "max_canon_lines": 250,
  "max_canon_bytes": 65536,
  "allowed_change_globs": ["src/*", "canon/*"],
  "rules": [
    {
      "id": "implementation-shape",
      "glob": "src/*.py",
      "min_matching_files": 1,
      "max_matching_files": 4,
      "must_regex": "def ",
      "forbid_regex": "TODO",
      "description": "Implementation is present and complete."
    }
  ]
}
```

Globs use Python `fnmatch`: `*` can cross `/`, and brace expansion is not
supported. Mechanical required gates are required files, manifest integrity,
fixture tests, holdouts, authenticated `capture`/`preserve`, and scorable
routing checks. Line/byte caps, diff scope, and content rules affect the score
but are not currently hard `pass_all_required` gates.

Additional contract blocks:

- `holdout`: copy hidden tests into a disposable workspace and run them there;
- `routing`: require successful structured reads and cap sibling-domain reads;
- `capture`: authenticate the exact paths and bytes matched at one step;
- `preserve`: require a later step to retain the captured set and contents.

The routing parser recognizes successful Codex JSON command reads and Claude
structured `Read` results. If an adapter provides no supported successful-read
telemetry, routing is recorded as `unsupported`, not passed.

Always prove a scenario is winnable: implement a correct solution by hand and
confirm every intended mechanical check and holdout passes. Extend
`LEAK_TERMS` in `evals/bin/optimize.py` when a scenario introduces distinctive
fixture vocabulary.

## Current limitations

- Variance is real. Use three to five runs at minimum, pin models, and follow
  the floor/no-regression gates in `PLAYBOOK.md`.
- Mechanical checks are the trustworthy core; judge scores are relative signal
  and can inherit model-family bias.
- Codex emits structured JSON and its successful reads are mechanically
  scorable, but `distill-transcript.py` does not yet render the current Codex
  event shape. Codex qualitative judge input therefore contains
  `(no events parsed)` for transcript evidence; diff, Canon, and check evidence
  still reaches the judge. Do not rely on Codex judge scores for
  transcript-ordering criteria until the distiller is updated.
- Judge validation does not yet require the complete exact rubric ID set.
- Evaluator provenance hashes the core checker, judge, summarizer, provenance,
  prompt, rubric, and adapter, but not the executed `distill-transcript.py` or
  imported `tools/canonlib.py`. Preserve the full result bundle and source
  revision when stronger attestation matters.
- Comparison metadata does not attest the operating system, `uv`, Git, or agent
  CLI versions, the sandbox wrapper or host-execution opt-in, ambient agent
  configuration, authentication, or the backend model actually served. Hold
  these external controls constant and record them with consequential runs.
- The Pi headless invocation is a best effort; verify it against `pi --help`
  before treating its results as comparable.
- Do not optimize against one scenario or a saturated suite. Keep an
  optimizer-blind holdout and add harder scenarios when scores stop
  discriminating.
