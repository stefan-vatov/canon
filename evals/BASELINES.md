# Evaluation and adoption ledger

This file preserves historical experiments and adoption decisions. Results are
comparable only when every comparison key matches, including guidance,
scenario, harness/adapter, worker model and reasoning, judge command/prompt,
run count, source state, and attested evaluator inputs.

## 2026-07-24 — invariant-first release: LIVE BASELINE ESTABLISHED

Direct production feedback found the prior Canon slightly net harmful during
large behavior-preserving extractions. The useful dependency, ownership,
runtime, persistence, and product rules were coupled to manual source
inventories and Git-anchor freshness checks. Ordinary file moves therefore
caused documentation churn without changing architecture or behavior.

The release candidate replaces the product model across guidance, generated
artifacts, doctor, compaction skill, analyzer, public documentation, rubric,
and fixtures:

- required core reduced to `manifest.md` and `standards.md`, with focused
  normative pages under `architecture/`;
- `sources` and `verified` metadata retired in favor of status, package or
  architectural scope, durable validation evidence, and relationship links;
- explicit no-impact / clarification / change classification added, with
  behavior-preserving refactors required to leave Canon untouched;
- doctor source-to-document staleness coupling removed and replaced with
  metadata, normative-route, link, validation, scratch, and inventory checks;
- scenario 05 replaced by a behavior-preserving extraction that penalizes
  Canon edits, while scenario 08 now rejects function-level canonization.

### Live panel

Six isolated live workers evaluated the same five discriminating scenarios.
`05-impact` used three runs; `02-feature`, `08-routing`, `09-abstention`, and
the three-session `10-supersede` used one run each. The independent judge for
every scored batch was
`openrouter/google/gemini-3.1-pro-preview:high` through Pi. Final round-two
source was `af76a5dec1a1651ff08861de8c701733206009b5`; every retained summary
records `source_dirty: false`.

The evolutionary-workflow panel labels map to the actual pinned Codex
backends as follows: `GPT 5.5 high` used `gpt-5.6-sol` at high reasoning, and
`GPT Spark` used `gpt-5.6-terra` at medium reasoning. The table names the
actual workers; bundle lists retain the panel labels.

The table reports run-weighted means and the lowest batch mean as the observed
floor. A required pass count is stricter than either mean.

| rank | exact worker | harness | required batches | mechanical mean / floor | judge mean / floor |
|---:|---|---|---:|---:|---:|
| 1= | `gpt-5.6-sol`, high | Codex | 5/5 | 1.000 / 1.000 | 1.000 / 1.000 |
| 1= | `gpt-5.6-terra`, medium | Codex | 5/5 | 1.000 / 1.000 | 1.000 / 1.000 |
| 3 | `zai/glm-5.1:medium` | Pi | 4/5 | 0.992 / 0.944 | 0.915 / 0.818 |
| 4 | `minimax/MiniMax-M3:medium` | Pi | 3/5 | 0.968 / 0.867 | 0.852 / 0.500 |
| 5 | `deepseek/deepseek-v4-pro:medium` | Pi | 3/5 | 0.972 / 0.870 | 0.812 / 0.636 |
| 6 | `openrouter/moonshotai/kimi-k2.5:medium` | Pi | 2/5 | 0.918 / 0.750 | 0.808 / 0.667 |

Selected round-two bundle IDs, in `05/02/08/09/10` order:

- GLM: `20260724-162917-05-impact-pi-88339`,
  `20260724-164007-02-feature-pi-7460`,
  `20260724-164407-08-routing-pi-11473`,
  `20260724-164615-09-abstention-pi-12892`,
  `20260724-164719-10-supersede-pi-13355`;
- DeepSeek: `20260724-162922-05-impact-pi-88569`,
  `20260724-163246-02-feature-pi-94418`,
  `20260724-163400-08-routing-pi-96235`,
  `20260724-163505-09-abstention-pi-98555`,
  `20260724-163552-10-supersede-pi-146`;
- MiniMax: `20260724-165524-05-impact-pi-17496`,
  `20260724-170910-02-feature-pi-23860`,
  `20260724-171820-08-routing-pi-26882`,
  `20260724-172159-09-abstention-pi-28102`,
  `20260724-172313-10-supersede-pi-29106`;
- Kimi: `20260724-162942-05-impact-pi-89125`,
  `20260724-163448-02-feature-pi-97881`,
  `20260724-163616-08-routing-pi-548`,
  `20260724-163909-09-abstention-pi-5786`,
  `20260724-164059-10-supersede-pi-8345`;
- GPT 5.5 high: `20260724-163547-05-impact-codex-99575`,
  `20260724-164527-02-feature-codex-12227`,
  `20260724-164841-08-routing-codex-14040`,
  `20260724-165049-09-abstention-codex-15133`,
  `20260724-165142-10-supersede-codex-15622`;
- GPT Spark: `20260724-163007-05-impact-codex-89906`,
  `20260724-163451-02-feature-codex-98075`,
  `20260724-163620-08-routing-codex-722`,
  `20260724-163725-09-abstention-codex-2746`,
  `20260724-163822-10-supersede-codex-3876`.

Each abbreviated ID expands beneath the corresponding worker directory in
`evals/results/live-20260724-invariant-first/round2/`.

The capable Codex tiers passed every required gate and every judge criterion.
The weaker tiers are retained as negative baselines, not relabeled successes:
their misses were incomplete durable-contract updates, fabricated missing
policy, malformed decision metadata, omitted current-state updates, or broken
historical routing. Missing routing telemetry remained `unsupported` and did
not count as a pass.

Round-one results at `62257de4861e91f3f4dc1aeded992eb08ad02ffe`
identified three evaluator false positives and three general guidance gaps.
Those scores are not compared numerically because both the evaluator and judge
changed. The accepted corrections:

- distinguish validation filenames and comments from implementation
  inventories and executable float use;
- verify Python public bindings and integer-only arithmetic semantically;
- preserve complete supplied contracts and abstain when product policy is
  absent;
- require list-shaped supersession metadata, an explicit current-state rule,
  immutable predecessors, and labeled historical manifest routes;
- define validation metadata as repository-root-relative evidence paths.

The strengthened supersession scenario then ran on all six workers at
`a49f5f1`: GPT 5.5 high, GPT Spark, and MiniMax passed at 1.000/1.000;
GLM scored 0.929/0.923, DeepSeek 0.857/0.538, and Kimi 0.821/0.833.
The corresponding bundle IDs are
`20260724-173854-10-supersede-codex-40447`,
`20260724-173901-10-supersede-codex-40707`,
`20260724-173834-10-supersede-pi-40223`,
`20260724-173821-10-supersede-pi-40054`,
`20260724-173828-10-supersede-pi-40140`, and
`20260724-173840-10-supersede-pi-40328` under the archived `supersession/`
worker directories.
On exact final revision
`1bd88410250d61ef2c028a133b9d4d8a5f31a6a5`, GPT Spark again passed
1.000/1.000. GLM correctly used repository-root-relative validation evidence
but still removed an explicitly required historical route, scoring
0.893/0.917; that is recorded as model non-compliance rather than another
guidance ambiguity. Final-confirm bundle IDs are
`20260724-175257-10-supersede-codex-53467` for GPT Spark and
`20260724-175250-10-supersede-pi-53380` for GLM.

### Release decision and evidence boundary

The invariant-first implementation is approved for release. This is an
absolute cross-model readiness decision, not a matched A/B improvement claim:
no numerical comparison is made against the retired inventory-first guidance.
Use a capable tier for high-risk Canon migrations and decision supersession;
the weaker-model rows quantify why.

Deterministic release evidence on the final revision: generated artifacts are
fresh on a second build; 55 repository regressions pass; all ten active fixture
test suites pass; all nine seeded Canon fixtures pass the strict doctor at the
Git baseline; 24 scenario JSON contracts parse; Python and shell syntax,
ShellCheck, and whitespace validation pass. Two independent final reviewers
approved the guidance, evaluator, route parser, and generated artifacts after
their findings were corrected.

Raw artifacts are preserved in this release machine's working copy under
`evals/results/live-20260724-invariant-first/`. They are Git-ignored by design
and are not distributed with this commit; a fresh checkout has only this
ledger, not the 43 MB receipt archive.
Transport-only failures were excluded: Claude authentication was revoked, the
Kimi collaboration bridge had no quota, one GPT orchestration worker abandoned
yielded processes, and one MiniMax runner applied a premature cutoff. The
actual Kimi worker ran successfully through Pi/OpenRouter; GPT and MiniMax
batches were rerun under direct supervision. The project provenance boundary
still applies: retained receipts attest selected evaluator inputs but do not
cryptographically bind every runtime executable, transcript, or workspace.

## 2026-07-18 — integrity hardening pass: GPT synthesis ADOPTED

External frozen-base identifier: `161d77d316bc79bc5a3486fe308e260ef66ae993`.
That object is not retained in this repository, so the supervisor result is
narrative historical evidence rather than a reproducible current baseline. Six isolated
candidates used the evolutionary-workflow labels, but every implementation
worker and reviewer in this pass was GPT-based; no Claude or LiteLLM model was
invoked. The frozen adversarial supervisor was 0/8 on the base and 8/8 on all
six candidates, proving it was a useful floor but not a sufficient winner
test.

| label | actual backend | ephemeral commit | supervisor | independent hard-gate review |
|---|---|---|---:|---:|
| GLM | GPT-5.6 Sol ultra | `48fe38e` | 8/8 | 64/100, reject |
| Deepseek | GPT-5.6 Terra max | `118b470` | 8/8 | 52/100, reject |
| MiniMax | GPT-5.6 Sol ultra | `79fc952` | 8/8 | 62/100, reject |
| Kimi | GPT-5.6 Sol ultra | `51d9752` | 8/8 | 74/100, reject |
| GPT 5.5 high | GPT-5.6 Sol ultra | `056fdf6` | 8/8 | 72/100, seed |
| GPT Spark | GPT-5.6 Sol ultra | `7fd3c19` | 8/8 | 70/100, reject |

Every raw candidate had at least one ship blocker hidden by the common probe:
failed runs could be marked complete; malformed judges could disappear from a
mean; provenance could downgrade to legacy semantics; manifest/source symlinks
could escape roots; or temporal "immutability" was only a regex. The adopted
result is therefore a reviewed synthesis, not an unchanged candidate.
The candidate hashes name commits created in isolated temporary clones; they
are experiment identifiers and are not guaranteed reachable from this
repository's permanent Git refs.

Adopted changes:

- compact guidance with explicit authority/write scope, a four-part retention
  test, deterministic two-pass routing, atomic freshness semantics, and
  byte-immutable decision supersession.
- exact contained manifest/source paths, symbolic-anchor rejection, full-DAG
  source coverage, dirty/ignored/missing-source handling, byte caps, and a
  strict doctor mode;
- schema-v2 batch/run receipts with terminal status, SHA-256 artifact lineage,
  strict check schemas, bounded judge values, retained declared inputs, and
  immutable-baseline diffs;
- authenticated cross-session path/byte snapshots for scenarios 04 and 10,
  with temporal violations marked required;
- successful structured-read routing evidence, explicit unsupported telemetry,
  disposable holdout workspaces, network-denied macOS test execution, and
  explicit sandbox configuration elsewhere;
- non-destructive install documentation for existing agent configuration.

Deterministic validation: supervisor 8/8, repository regressions 9/9, portable
ambient-signing stub batch complete, Python/shell/JSON validation clean, and
all generated artifacts fresh. A live paid-model confirmatory batch was not run
after the final hardening, so no behavioral model-score claim is made for this
revision.

Known attestation limits: judge validation does not yet require the exact full
rubric criterion set, so its denominator is not mechanically fixed. Evaluator
lineage also omits `distill-transcript.py` and the imported `tools/canonlib.py`.
Treat judge output and toolchain identity as attributable but not yet fully
attested until those gaps are closed.

Read-only production audit: Ember Rhythm was never modified. It demonstrated
the need for migration-safe enforcement: one real manifest omission
(`architecture/workouts-strong-parity.md`), two oversized Canon files, legacy
freshness metadata, and existing project-specific agent instructions that must
not be overwritten.

## 2026-07-17 — evolution pass 1: durable-decision boundary ADOPTED

Six frozen-base candidates targeted the remaining `10-supersede` gradient.
Each valid candidate ran six three-session chains: runs 1–3 used GPT-5.6 Terra
at medium reasoning and runs 4–6 used GPT-5.6 Sol at high reasoning. Judges
used the same GPT mix; transcript-only criteria were null.

| candidate | mechanical mean | judge mean | result |
|-----------|----------------:|-----------:|--------|
| current @ dcd109d | 0.994 | 0.849 | baseline |
| GLM | 0.983 | 0.817 | rejected |
| Deepseek | — | — | invalid: isolation/scope failure |
| MiniMax | — | — | invalid: task transport failure |
| Kimi | — | — | invalid: isolation/scope failure |
| GPT 5.5 high (GPT-5.6 Sol runtime) | 1.000 | 0.983 | runner-up |
| GPT Spark (GPT-5.6 Terra runtime) | 1.000 | 1.000 | **adopted** |

The adopted candidate also won within each pinned worker/judge stratum:

| stratum (n=3) | baseline mean mech/judge (floor) | adopted mean mech/judge (floor) |
|---------------|----------------------------------:|---------------------------------:|
| GPT-5.6 Terra medium | 1.000 / 0.846 (0.750) | 1.000 / 1.000 (1.000) |
| GPT-5.6 Sol high | 0.989 / 0.852 (0.778) | 1.000 / 1.000 (1.000) |

Both GPT candidates were mechanically perfect. Terra won the qualitative gate:
all six runs preserved immutable decision history and recorded only supplied
rationale. The Sol variant had one immutable-history rewrite. (Three initial
judge deductions were corrected on review: one treated task-supplied rationale
as invented, and two wrongly required domain freshness metadata on decision
records.) The adopted 181-line guidance narrows decision records to explicit,
authoritative, durable human choices; excludes modal wording in routine tasks
and inferred design choices; records only supplied rationale/alternatives; and
requires superseding records plus current-state links that expose only the
active decision.

Post-review controls covered both sides of the new boundary. A focused
same-batch routine-requirement A/B (six baseline and six adopted-trigger runs,
using the same Terra/Sol split) asked agents to implement a modal `must`/`never`
page-size validator. All 12 implementations and test suites passed; baseline
created a spurious decision record in 6/6 runs, while adopted guidance created
one in 0/6 and still refreshed current-state Canon in 6/6.

An initial three-chain supersession smoke exposed a real floor failure: one
agent overwrote the predecessor record, but the old checker still reported
12/12. The final wording now forbids editing, deleting, renaming, or reusing an
existing record path. The generic checker gained `min_matching_files`, and
scenario 10 now requires distinct predecessor and successor files. It correctly
rescored the bad run at 12/13. On the exact final 181-line guidance, three fresh
chains each preserved two decision files, passed 13/13 mechanical checks, and
scored 1.000 with strict qualitative judges.

A read-only production audit of `ember-rhythm` supported the boundary: the
live install has no decision records despite durable project choices, while
routine modal requirements are common and ambiguous. The audit also found
separate future gradients—an older installed guidance bundle, unbounded Canon
context, incomplete manifest routing, and a same-commit freshness blind spot.
None were mixed into this single-variable pass. This pass made no writes to the
production repository; its pre-existing dirty checkout was left untouched.

Kimi/ZAI/MiniMax target-model cells were cut off as invalid after the LiteLLM
collaboration bridge repeatedly dropped or misrouted task payloads. Two partial
baseline chains showed Kimi at 5/6 and ZAI at 6/6 through supersession, but the
matrix was incomplete and is not adoption evidence. Treat those cells as
transport failures, not model-quality measurements.

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

## 2026-06-15 — round 8: supersession-hygiene edit (r8) — REJECTED (variance)

Targeted the one strong-tier gradient from round 7 (codex leaks "changed
from 50 to 100" into current-state docs on 10-supersede). r8 added a
supersession-hygiene rule to the decision-records section: "When a value or
rule is superseded, current-state files must state only the new value; the
prior value belongs in its decision record — never 'changed from X' …".

Initial cross-batch read looked like a win (10-supersede 0.93→0.97 on
haiku). The n=6 SAME-BATCH confirmation killed it:

| 10-supersede haiku | current | r8 |
|--------------------|:-------:|:--:|
| pooled n=6 | ~0.95 / 0.955 | ~0.94 / 0.90 |
| wave J same-batch n=3 | 0.97 / 0.97 | 0.91 / 0.83 |

The apparent gain was cross-batch variance — wave D's current baseline was
a low draw (0.93); head-to-head, r8 is neutral-to-slightly-worse. No Haiku
benefit. The codex no-regression gate was also unavailable (workspace out of
credits — manual refill, not a timed reset; all round-8 codex numbers were
non-executing aborts, not signal). With no demonstrated win on the testable
tier, r8 REJECTED; candidate file removed. Lesson reinforced: only same-batch
comparisons are trustworthy at this variance; cross-batch deltas mislead.

Standing tally: 2 guidance edits adopted (rounds 2, 3), 4 rejected (round 4
lean, round 6 abstention ×2, round 7 INT, round 8 r8). The guidance is at a
robust local optimum for the current suite; further real gains need harder
scenarios (10-supersede is the first strong-tier discriminator), not edits.

## 2026-06-15 — round 7: comprehensive baselines + INT edit REJECTED

Parallel eval burn. First full baselines on both tiers (current core).

Haiku (n=3, claude harness, sonnet judge), mech / judge:

| 01 | 02 | 03 | 05 | 06 | 07 | 08 | 09 |
|----|----|----|----|----|----|----|----|
|1.00/1.00|0.95/1.00|1.00/1.00|1.00/0.97|0.94/0.92|0.95/1.00|0.90/0.88|0.91/0.85|

Codex gpt-5.5-high (n=2): every scenario 1.00/1.00 — strong tier fully
saturated on 01-09.

04-memory-chain (the flagship 10-session chain), first weak-tier run
(haiku n=2): 0.89 / 0.85 — cross-session Canon memory holds reasonably but
imperfectly on a small model; healthy discrimination, not saturated.

10-supersede (new) discriminates on BOTH tiers — the first scenario the
strong model does not ace:
- haiku 0.93/0.94 — misses manifest entries for new decision records
- codex 0.97/0.91 — writes supersession changelog-style ("changed from 50
  to 100") in the current-state doc instead of pure current state

INT candidate (hoisted integer-arithmetic / literal-standards cue) — REJECTED.
A/B n=6 haiku (pooled), codex n=2:

| scenario | current | INT | 
|----------|:-------:|:---:|
| 08-routing | ~0.91/0.85 | ~0.94/0.91 (modest win, the no_floats target) |
| 02-feature | ~0.95/1.00 | ~0.93/0.95 (small, consistent regression) |
| 05-staleness | ~0.98 | ~0.97 (neutral) |
| codex 02/05/08 | 1.00 | 1.00 (no regression) |

Net Haiku ~wash (+0.005): the 08 gain is traded for a 02 loss — the
round-4 "more instructions can hurt elsewhere" effect again. No clear win
above noise; kept current core.

Harness robustness fixes found during the burn (both committed): git init
uses an empty template (hook-copy race) and result dirs are pid-suffixed
(same-second same-scenario collision). A collided A/B pair was discarded;
all reported numbers are from verified-distinct dirs.

## 2026-06-15 — round 5 (frontier scenarios) + round 6 (abstention edit REJECTED)

Round 5 added research-driven 08-routing and 09-abstention (see RESEARCH.md)
plus routing-precision scoring and the abstention/code_correct judge fix.
Both new scenarios discriminate:

| scenario | codex gpt-5.5 high | haiku |
|----------|:------------------:|:-----:|
| 08-routing | 1.00 / 1.00 | 0.94 / 1.00 (no_floats dips, routing OK) |
| 09-abstention | 0.91 / 1.00 | 0.91 / 0.78 |

Key finding: agents abstain *verbally* (don't fabricate — orders.py never
modified in any run) but do NOT durably record the gap; `gap_surfaced` fails
~1/3 of runs on BOTH tiers. 08's routing_precision check passed on both
models (routing isn't the weak point; integer-cents discipline is).

Round 6 tried to fix durable-gap-recording with a guidance rule, in two
placements:

| 09-abstention | current | mid-doc rule | hoisted rule |
|---------------|:-------:|:------------:|:------------:|
| haiku | 0.91 / 0.82 | 0.91 / 0.78 | 0.91 / 0.79 |
| codex | 0.91 / 1.00 | 0.95 / 1.00 | 0.91 / 1.00 |

Neither beats current above noise; `gap_surfaced` stays ~0.91 regardless.
Inspection: agents abstain correctly but don't write a scratch/decisions
note with or without the rule. REJECTED both edits; kept current core.
Conclusion: durable-recording of a non-event is resistant to prompting at
these tiers — likely a capability limit, not a wording gap. `gap_surfaced`
is partly aspirational (verbal abstention is already correct behavior).

Kept from round 6 (correctness/robustness, independent of the rejected edit):
judge no longer penalizes correct abstention under code_correct; run-eval.sh
git init uses an empty template to avoid a parallel hook-copy race.

## 2026-06-14 — round 4 REJECTED (lean / de-duplication hypothesis)

Research-driven (arXiv 2510.14842 "Boosting Instruction Following at Scale":
adding instructions degrades following via tension/conflict between them;
AGENTS.md best-practice guides: minimize, state triggers once, most-important
first). Hypothesis: a lean 141-line core (177 -> 141, canon-read-first stated
once at top instead of three times) holds or improves the weak-model floor at
lower token cost.

A/B, n=3, corrected judge (haiku agent / sonnet judge), combined means:

| scenario | lean (141 ln) | current (177 ln) |
|----------|:-------------:|:----------------:|
| 06-decisions | 0.985 | 1.000 |
| 05-staleness | 0.967 | 0.967 |
| 07-pressure | 1.000 | 0.988 |
| 02-feature | 0.952 | 0.988 |
| **mean** | **0.976** | **0.986** |

Both have healthy floors, zero catastrophic misses; current marginally ahead
(+0.01, within noise) but lean shows a small, consistent 02-feature dip on
BOTH tiers (codex 0.93/0.88 vs 1.00). Mechanism: compressing the freshness
section made the agent more likely to stamp `verified` with the pre-commit
HEAD. Verdict: keep the 177-line core; the redundancy is reinforcing, not
conflicting, and the suite is near its ceiling so trimming has no headroom to
help. Negative result kept so the lean cut is not re-attempted.

Takeaway: further real gains need harder/larger scenarios (multi-domain repos
where the context-budget rule bites, longer chains), not prompt-trimming.

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
