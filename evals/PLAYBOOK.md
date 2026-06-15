# Canon Eval & Improvement Playbook

Start here to resume work in a new session. This is the operational runbook;
`README.md` has the mechanics, `BASELINES.md` the full history, `RESEARCH.md`
the evidence behind the harder scenarios.

## What this is

A measurement harness for the Project Canon guidance (`../canon-core.md`). It
runs an agent through scenario repos, scores whether it followed the Canon
discipline (mechanically + with an LLM judge), and lets you A/B guidance edits
so improvements are driven by scores, not vibes. `canon-core.md` is the single
source of truth; `../tools/build.py` regenerates the four shipped artifacts
(`.pi/APPEND_SYSTEM.md`, `.codex/system.md`, `dist/CLAUDE.md`, `dist/AGENTS.md`)
— never edit those by hand.

## Current state (2026-06-15)

- 10 scenarios (01–10). Single-session, multi-session chains, plus three
  research-driven ones: `08-routing` (routing/distractors), `09-abstention`
  (don't fabricate missing policy), `10-supersede` (temporal/forgetting).
- Guidance has had 2 edits adopted (rounds 2–3) and 4 rejected (4, 6, 7, 8).
  Weak-model (Haiku) floor was lifted 0.44 → ~0.90. **The guidance is at a
  robust local optimum for this suite** — more prompt edits are diminishing
  returns. Real gains now need harder scenarios.
- Baselines (current core): Codex gpt-5.5-high saturates 01–09 at 1.00;
  Haiku ranges 0.89–1.00; `10-supersede` is the only scenario that
  discriminates even on the strong tier (codex 0.97/0.91). See BASELINES.md.

## How to run one A/B round (the core loop)

1. **Baseline + candidate, same batch.** Copy the guidance, make ONE focused
   edit, run both against the same scenarios in the same session:
   ```sh
   cp canon-core.md /tmp/cand.md && $EDITOR /tmp/cand.md
   EVAL_MODEL=haiku JUDGE_CMD="claude -p --model claude-sonnet-4-6" \
     evals/bin/run-eval.sh --scenario 06-decisions --runs 3 --harness claude --guidance /tmp/cand.md
   EVAL_MODEL=haiku JUDGE_CMD="claude -p --model claude-sonnet-4-6" \
     evals/bin/run-eval.sh --scenario 06-decisions --runs 3 --harness claude   # current core
   ```
2. **Compare** with `uv run --script evals/bin/summarize.py <dir-a> <dir-b>`,
   or read each `summary.json`.
3. **Adopt only if BOTH gates pass** (see discipline below). To adopt: apply
   the edit to `canon-core.md`, run `uv run --script tools/build.py`, commit.
4. **Record the round in BASELINES.md** — win or loss. Negative results are
   valuable; they stop the same edit being re-tried.

Autonomous hill-climb (proposes + A/Bs edits for you):
```sh
uv run --script evals/bin/optimize.py --scenarios 06-decisions,08-routing \
  --harness claude --runs 3 --iterations 3
```
It writes candidates + `best.md` to `evals/results/opt-*/` but never touches
`canon-core.md` — adoption stays a human step.

## The discipline (hard-won — do not skip)

- **Two gates to adopt:** (a) clear improvement above noise on the
  discriminating tier (Haiku), AND (b) no regression on the strong tier
  (Codex). An edit that helps weak but hurts strong is rejected.
- **Same-batch comparison only.** Cross-batch deltas lie. Round 8's "win"
  (0.93→0.97) was pure variance — the same-batch n=6 showed it was flat. If
  you compare a candidate to a baseline from a different run, you will fool
  yourself. Always run current + candidate together.
- **n ≥ 3, judge by the floor.** Single runs are noise. The decision metric
  that's held up is the *floor* (worst run / catastrophic-miss rate), not the
  mean — failures here are bimodal (a run either complies or face-plants).
- **Pin models** (`EVAL_MODEL`, `JUDGE_CMD`) across a comparison; a score is
  always guidance × model × harness.
- **Discriminate before optimizing.** If every scenario already scores ~1.00,
  there's no gradient — drop to a weaker model/effort tier or add a harder
  scenario. Don't tune against a saturated suite.
- **Leak guard:** `optimize.py` rejects candidates containing fixture terms
  (`LEAK_TERMS`) — extend it when you add a scenario, or the optimizer can
  cheat by encoding answers.

## Gotchas / environment

- **Codex needs workspace credits** (`gpt-5.5` via ChatGPT account). When it's
  "out of credits" every run aborts with zero tool calls and scores ~0 — that
  is NOT a guidance signal. Refill before trusting any Codex number. This is a
  manual top-up, not a timed reset.
- Everything Python runs through **uv** (PEP-723 inline deps); no venv.
- `run-eval.sh` git-inits with an empty template and pid-suffixes result dirs
  — both fixes for parallel-run races. Safe to run waves concurrently now.
- Results dirs are git-ignored (`evals/results/*`); BASELINES.md is the
  durable record. Each result dir keeps `guidance-used.md` so you can tell
  which variant produced it (line count distinguishes versions).
- The judge transcript is distilled (`distill-transcript.py`) from stream-json
  — raw stream-json is too verbose and starves the judge.

## Next frontier (where the gradient actually is)

Prompt edits are tapped out on this suite. To improve further:
1. **Harder scenarios** (highest value). RESEARCH.md lists untested failure
   modes: multi-hop aggregation across domains, memory consolidation/
   compaction, larger multi-domain repos where the context budget truly bites.
   `10-supersede` proved the strong tier *can* be cracked — build more like it.
2. **Mechanical enforcement** as a real product surface: wire `canon-doctor.py`
   into CI / a pre-commit hook in a consuming repo.
3. **Re-run the round-8 idea** (supersession hygiene) only with the Codex gate
   available and a same-batch n≥6 — it was rejected on variance, not disproven.

## When you adopt an edit, the commit ritual

Conventional, lowercase, with the Co-Authored-By trailer. `feat(guidance):`
for an adopted edit (then rebuild artifacts in the same commit),
`test(evals):` for scenarios, `fix(evals):` for harness, `docs(evals):` for
BASELINES/records.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
