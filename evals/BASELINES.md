# Baseline Reference Scores

Reference numbers that candidate guidance must beat. Re-baseline whenever
the guidance, a scenario, the judge prompt, or the agent model changes.

## 2026-06-11 — canon-core.md @ 202feaf, codex / gpt-5.5 / high reasoning

3 runs per scenario, judge: claude (default). `04-memory-chain` held out as
the optimizer-blind control (not part of optimization baselines by design).

| scenario | mechanical | judge |
|----------|-----------:|------:|
| 01-bootstrap | 1.00 | 1.00 |
| 02-feature | 1.00 | 1.00 |
| 03-drift | 1.00 | 1.00 |
| 05-staleness | 1.00 | 1.00 |
| 06-decisions | 1.00 | 1.00 |

**Status: saturated at this model tier.** The suite no longer discriminates
for codex/gpt-5.5-high; further guidance improvement must come from harder
scenarios (outer loop), measurement on weaker model tiers where guidance
quality carries more of the load, or judge-note mining.

Soft signals from judge notes despite perfect scores (candidate outer-loop
material):

- Core files (overview/glossary/standards) carry no freshness frontmatter —
  the spec only mandates it for domain files, and both an optimizer
  candidate and a judge note independently flagged the ambiguity. Decide
  the convention either way, then add a scenario check for it.
- Occasional ordering wobble: Canon content drafted before the code change
  it describes is finalized.
- Minor scope creep at diff edges (annotating adjacent code).

## 2026-06-14 — round 3 adopted (hoisted first-action directive)

Two changes this round. (1) Fixed a measurement bug: the judge was fed
raw stream-json truncated by bytes, so multi-session runs were judged on
the init event alone — now distilled to a compact ordered action log
(see `bin/distill-transcript.py`). Corrected judging is marginally
stricter. (2) Hoisted an unmissable "FIRST ACTION, EVERY TASK: read the
Canon before find/grep/source" directive — plus lexical decision cues —
to the very top of canon-core.md, after diagnosing that the 06-decisions
failures all cascade from canon-read-first being skipped.

A/B, n=3, corrected judge (haiku agent / sonnet judge). The decisive
metric is the floor (worst run), since the failure mode is a catastrophic
canon-skip, not a low mean:

| | candidate worst→best | prior-core worst→best |
|--|--|--|
| 06-decisions | 0.91 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 (lucky batch) |
| 05-staleness | 0.90 / 0.90 / 1.00 | **0.44** / 0.90 / 1.00 |
| 07-pressure | 1.00 / 1.00 / 1.00 | 0.89 / 0.90 / 1.00 (mech 0.93) |

Candidate worst run across all 9 = 0.90; prior-core worst = 0.44.
Combined means 0.928 → 0.984. No scenario regressed; candidate had zero
mechanical failures across 9 runs. Codex no-regression: 06-decisions
1.00 / 1.00 on gpt-5.5-high.

Variance lesson: n=3 is too noisy to pin a single scenario's mean at this
tier (prior-core 06 swung from a ⅔-fail batch earlier to a clean 3/3
here). Decisions now weight the floor (catastrophic-miss rate) over the
mean, and the regression guard spans multiple scenarios so one lucky
batch can't mask a real effect.

## 2026-06-14 — optimizer round 2 adopted (Haiku-driven)

The codex tier was saturated, so discrimination moved to a small model
(claude / haiku via the claude harness), where the guidance — not the
model — carries compliance. Haiku exposed real failures (canon-read-first
skipped, placeholder `verified` left, decision records not written, tests
skipped under pressure). Optimizer round 2 (improver: claude) proposed a
candidate addressing all 20 failure signals; adopted after a two-gate
validation.

Validation, n=3, apples-to-apples (haiku agent, sonnet judge):

| scenario | prior core @0d0bcab | adopted core | combined Δ |
|----------|:-------------------:|:------------:|:----------:|
| 02-feature | 0.93 / 0.82 | 0.98 / 0.96 | +0.10 |
| 05-staleness | 0.86 / 0.56 | 1.00 / 1.00 | +0.29 |
| 06-decisions | 0.88 / 0.68 | 0.88 / 0.70 | +0.01 |
| 07-pressure | 0.83 / 0.67 | 0.98 / 0.96 | +0.22 |
| **combined mean** | **0.779** | **0.933** | **+0.15** |

No-regression gate (candidate, codex / gpt-5.5 / high, 1 run):
02-feature, 06-decisions, 07-pressure all 1.00 / 1.00 — the stronger
guidance costs the strong model nothing.

Edits adopted (all map to verified failures, none leak fixture answers):
canon-read-first repositioned to "before any file listing/search/read";
`verified` must be `git rev-parse --short HEAD`, never a placeholder;
editing a `sources` file obligates refreshing its Canon file; decision
record written the moment a decision is stated, with a manifest entry;
a pre-report verification checklist; "urgency exempts nothing".

Remaining laggard: 06-decisions (~0.79 on haiku) — decision-record
creation is the hardest behavior for the small model. Next target.

Note: optimizer iters 2-3 this round returned degenerate output (improver
hit a session limit); the length/leak guards rejected both, so no
session-limit text could be adopted as guidance.

## 2026-06-11 — discrimination probes

- **Weak-tier scan** (codex / gpt-5.5 / **low** reasoning, 1 run each,
  scenarios 01/02/03/05/06): all 1.00 / 1.00. The suite is saturated at
  both effort tiers — the guidance, not the model, is carrying compliance.
- **07-pressure** (urgent-hotfix framing, codex / gpt-5.5 / low, 2 runs):
  behaviorally clean in both runs — Canon read first, regression tests
  shipped despite the "ship fast" framing, frontmatter refreshed. One
  mechanical false negative (test-name regex too narrow) found and fixed;
  treat pre-fix 0.96 as 1.00 behaviorally.

Standing conclusion: improvement gradient at this fixture scale is
exhausted for the codex harness. Next discrimination axes: other harnesses
/ small models, larger multi-domain fixtures (context budget), longer
chains.

Prior history: pre-adoption baseline 0.955 (01-bootstrap + 06-decisions,
1 run, 2026-06-10); optimizer round 1 kept +0.022 (repo-root .gitignore
instruction + decision-citation discipline), re-validated, adopted at
202feaf.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
