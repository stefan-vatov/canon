# Canon Evals

A harness for measuring whether the Project Canon guidance actually changes
agent behavior, so edits to the guidance are driven by scores instead of
intuition.

**Resuming this work in a new session? Start with [PLAYBOOK.md](PLAYBOOK.md)** —
the operational runbook (current state, how to run a round, the adoption
discipline, gotchas, and the next frontier). `BASELINES.md` is the full
round-by-round history; `RESEARCH.md` is the evidence behind the harder
scenarios.

## How it works

Each scenario is a small fixture repo plus a task prompt plus expectations.
One eval run:

1. copies the fixture into a throwaway workspace
2. installs the guidance under test via a harness **adapter**
   (`CLAUDE.md` for Claude Code, `AGENTS.md` for Codex,
   `.pi/APPEND_SYSTEM.md` for Pi), then commits a git baseline
3. runs the agent headless on the task, capturing the transcript
4. scores **mechanical checks** (`bin/check.py`): required Canon files,
   manifest completeness, line limits, tests pass, diff scope, planted-rule
   compliance
5. scores **qualitative criteria** (`bin/judge.sh` + `rubric.md`): an LLM
   judge reads transcript + diff + Canon and scores ordering, current-state
   style, minimal diff, drift handling
6. `bin/summarize.py` aggregates runs into `summary.json`

## Quick start

```sh
# prerequisites: uv, git, and the agent CLI you want to test
evals/bin/run-eval.sh --scenario 02-feature --harness claude --runs 3
evals/bin/run-eval.sh --scenario 04-memory-chain --harness codex --runs 1
```

All Python (scoring scripts, fixture tests, holdout tests) runs through `uv`;
no system Python or venv setup is needed.

Results land in `evals/results/<timestamp>-<scenario>-<harness>/`, including
the exact guidance file that was tested (`guidance-used.md`), per-run
workspaces, transcripts, `checks.json`, `judge.json`, and a `summary.json`.

Pin models for comparability:

```sh
EVAL_MODEL=claude-sonnet-4-6 evals/bin/run-eval.sh --scenario 02-feature --harness claude --runs 3
JUDGE_CMD="claude -p --model claude-opus-4-8" evals/bin/run-eval.sh ...
```

## The improvement loop

1. **Baseline:** run all scenarios at `--runs 3`+ against the current
   guidance. Record the means.
2. **Tweak:** copy the guidance, edit one thing:
   `cp .pi/APPEND_SYSTEM.md /tmp/variant-b.md && $EDITOR /tmp/variant-b.md`
3. **Re-measure:** `evals/bin/run-eval.sh --scenario ... --guidance /tmp/variant-b.md --runs 3`
4. **Compare:** `uv run --script evals/bin/summarize.py results/<baseline-dir> results/<variant-dir>`
5. Keep the edit only if scores improve; then apply it to `canon-core.md`
   and run `uv run --script tools/build.py` to regenerate all shipped
   variants — they are generated, never edited directly.

The default guidance under test is `canon-core.md`, the single source all
shipped variants are built from.

## Automated optimization

`bin/optimize.py` runs the improvement loop unattended — hill-climbing on
the guidance file:

```sh
uv run --script evals/bin/optimize.py \
  --scenarios 01-bootstrap,02-feature,03-drift \
  --harness codex --runs 3 --iterations 5
```

Per iteration: evaluate the current best guidance, hand the failing checks
and judge reasons to an improver LLM (`IMPROVER_CMD`, default `claude -p`)
that proposes a revised guidance file, evaluate the candidate, keep it only
if it beats the best by `--min-delta` (default 0.02 — below that, treat the
difference as run-to-run noise). Everything lands in
`evals/results/opt-<timestamp>/`: every candidate, `history.json`, and
`best.md`.

Guard rails:

- Candidates that mention fixture-specific terms (`LEAK_TERMS` in
  `optimize.py`) are rejected before evaluation — an optimizer tuning
  against known evals will otherwise encode the answers into the guidance.
  Extend that list whenever you add a scenario.
- Candidates outside 30–200 lines are rejected (degenerate or bloated).
- The script never overwrites the shipped guidance; adopting `best.md` into
  `canon-core.md` (then regenerating with `tools/build.py`) is a deliberate
  human step. Read the diff first — a higher score from a change you can't
  explain is a red flag, not a win.
- Keep a hold-out scenario the optimizer never sees, and check the adopted
  guidance against it before shipping.

The `stub` adapter runs no agent and changes nothing — use it to test
harness/optimizer plumbing for free.

## How code changes are judged "in line"

Four layers, from cheapest to richest:

1. **Tests** — each fixture ships a unit suite; `test_cmd` must exit 0.
2. **Diff scope** — `allowed_change_globs` in `expected.json`; touching
   anything else fails `diff_scope`.
3. **Planted standards** — the fixture's `canon/standards.md` contains
   deliberately machine-checkable rules (integer cents only, type hints,
   test-with-change), enforced as `must_regex`/`forbid_regex` rules. This is
   the direct measurement of whether the Canon is *binding*: the rule exists
   only in the Canon, so compliance proves the agent read and obeyed it.
4. **LLM judge** — `code_correct`, `code_follows_standards`, `minimal_diff`,
   `style_match` in `rubric.md`, scored from the actual diff.

## Scenarios

| scenario | sessions | tests |
|----------|----------|-------|
| `01-bootstrap` | 1 | no `canon/` exists; agent must create the structure while doing a feature |
| `02-feature` | 1 | full Canon with planted standards; agent must obey them and canonize the new behavior |
| `03-drift` | 1 | Canon contradicts code; agent must trust code, change nothing, and correct the Canon |
| `04-memory-chain` | 10 | the core claim: cross-session memory (see below) |
| `05-staleness` | 1 | a domain file with stale `sources`/`verified` frontmatter and a planted wrong claim; the agent must refresh content and re-stamp `verified` while doing a feature |
| `06-decisions` | 2 | session 1 states a decision with rationale and a rejected alternative; session 2 challenges it — the decision record must exist, stay immutable, and ground the answer |
| `07-pressure` | 1 | an URGENT-hotfix framing tempts the agent to skip tests, canonization, and frontmatter; the binding rules must survive deadline pressure |
| `08-routing` | 1 | ~10 domains, one relevant; sibling domains carry distractor rates. Tests routing precision (read the right doc, don't bulk-load — scored from the transcript) and distractor resistance. Research-driven; see RESEARCH.md |
| `09-abstention` | 1 | the task needs a policy that exists in no Canon file and no code; the agent must surface the gap, not fabricate a value. Research-driven; see RESEARCH.md |
| `10-supersede` | 3 | a default is established, then superseded; the new value must win and the old record stay as immutable, marked-superseded history. Tests temporal/selective-forgetting; see RESEARCH.md |

## The memory chain (04)

Canon's whole thesis is that project knowledge survives across sessions so
the agent never starts from scratch. Single-session scenarios
can't test that, so `04-memory-chain` runs ten tasks as ten **fresh agent
sessions** in the same workspace. Nothing carries over between sessions
except the repository contents: any knowledge from session 1 that shows up
correctly in session 7 must have traveled through the Canon.

The chain plants knowledge conversationally and probes it later:

- session 1 states a business policy (percentage-only discounts, 40% cap,
  with rationale), and domain terminology ("promo", "campaign" = promos
  sharing one expiry date) — stated once, never repeated
- sessions 2–4 build features that must silently respect that policy
- session 5 changes the policy (cap becomes 50%) — the Canon must be
  *updated*, not appended to
- session 6 refactors; the updated cap must survive
- session 7 implements "campaigns" — the required expiry field exists only
  in session 1's terminology, so it can only come from the glossary
- session 8 plants a false drift report — agent must verify against code
  and change nothing
- session 9 requests a handover — must land in `canon/scratch/`, not
  permanent files
- session 10 audits the Canon; the final check verifies current-state prose
  after ten sessions of churn

**Holdout tests** make the probes objective: hidden unit tests the agent
never sees, copied into the workspace at scoring time, run, and removed
before the next session. Each assertion traces to knowledge stated in
exactly one earlier session — passing means the knowledge persisted; this
is the same hidden-test principle SWE-bench uses. Per-step checks live in
`tasks/NN-*/expected.json` + `tasks/NN-*/holdout/`; the cumulative final
suite is `holdout/holdout_final.py`.

Cost note: one run = 10 agent sessions. Start with `--runs 1` and scale up
only for comparisons you intend to act on.

## Adding a scenario

Create `evals/scenarios/<name>/` with `task.md` (the prompt), `fixture/`
(a small self-contained repo, tests runnable with stdlib only), and
`expected.json`:

```json
{
  "test_cmd": "uv run python -m unittest discover -s . -p 'test_*.py'",
  "required_files": ["canon/manifest.md"],
  "allowed_change_globs": ["src/*", "canon/*"],
  "rules": [
    {"id": "x", "glob": "src/*.py", "must_regex": "...", "forbid_regex": "...",
     "description": "..."}
  ]
}
```

Note: globs use `fnmatch`, where `*` also crosses `/` — `canon/*` matches
`canon/payments/overview.md`. fnmatch does NOT expand braces (`{a,b}`).

A `routing` block scores retrieval/routing separately from correctness
(LongMemEval Oracle idea), parsed from the run's stream-json transcript:

```json
"routing": {"domain_glob": "canon/*/overview.md",
            "must_read": ["canon/pricing/overview.md"], "max_domain_reads": 2}
```

It passes if the agent read every `must_read` doc and at most `max_domain_reads`
files matching `domain_glob` (i.e. didn't bulk-load). Skipped automatically for
plain-text transcripts (e.g. codex), where per-tool file paths aren't structured.

For a multi-session scenario, replace the root `task.md` with
`tasks/NN-step/task.md` directories; each step runs as a fresh agent session
and may carry its own `expected.json`. Diffs are always computed against the
*initial* baseline, so per-step `allowed_change_globs` accumulate — don't use
them to assert "this step changed nothing"; use a holdout test on behavior
instead. Two extra `expected.json` keys:
`"holdout": {"dir": "holdout", "test_cmd": "uv run python -m unittest <module>"}`
runs hidden tests from the expected file's directory (copied in, run,
removed); the root `expected.json` is checked after the final step.
Always verify a scenario is *winnable*: implement a correct solution by hand
and confirm every check and holdout passes against it.

## Caveats

- **Variance is real.** Never compare single runs; 3–5 per variant is the
  floor. Pin `EVAL_MODEL` and `JUDGE_CMD` while comparing.
- **Judge bias.** If the judge model is the same family as the agent, treat
  judge scores as relative signal, not absolute truth. Mechanical checks are
  the trustworthy core.
- **Overfitting.** Don't tune the guidance against one scenario; add
  scenarios as you discover new failure modes, and keep old ones as
  regression tests.
- **Pi adapter** (`adapters/pi.sh`) uses a best-guess headless invocation;
  verify against `pi --help` before relying on it.
- Claude Code headless still loads your user-level `~/.claude/CLAUDE.md`;
  this is constant noise across variants but means absolute scores include
  your personal config.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
