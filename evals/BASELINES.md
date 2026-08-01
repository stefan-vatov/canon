# Evaluation adoption ledger

This is the durable decision record for Canon evaluations. It answers which
guidance was adopted or rejected, on what evidence, and within which limits.
It is not a run database, a current repository inventory, or an input to the
build and test tooling.

Raw bundles belong in `evals/results/` or durable external storage. That
directory is Git-ignored, so a local artifact key in this ledger is useful only
on a machine where the named archive has been retained.

## Maintenance contract

- Add an entry only for an adoption decision, a release baseline, or a negative
  result worth preventing others from repeating.
- Keep each entry under roughly 60 lines plus at most one compact result table.
  Do not paste transcripts, exhaustive bundle IDs, per-run narration, or
  implementation inventories.
- State the question, decision, tested revision, comparison key, decisive
  result, evidence location, and limitations.
- Compare scores only when guidance, scenario, harness, worker model and
  reasoning, judge command and prompt, run count, source state, and attested
  evaluator inputs match. Otherwise record an absolute result or a new
  baseline, not a delta.
- Treat old entries as historical facts. Correct factual errors in place, but
  never rewrite old scores to match a newer harness or guidance revision.
- When this file approaches 250 lines, collapse superseded entries into the
  experiment index with a Git record pointer; Git history remains the detailed
  archive.
- Update the current baseline only after the required gates in `PLAYBOOK.md`
  pass. Routine code or file moves require no ledger edit.

## Current accepted baseline

### 2026-08-01 — minimal AGENTS.md-only guidance adopted

**Question.** After removing every system-prompt delivery path (Canon now
ships only as generated `CLAUDE.md`/`AGENTS.md`), can a much smaller guidance
core keep cross-model Canon behavior at the accepted level?

**Decision.** Adopt the 3,511-byte core (36% of the 9,789-byte predecessor).
Same-wave three-arm comparison (prior core, a 5,193-byte compact candidate,
and the adopted candidate) plus an absolute cross-model readiness check.

**Comparison key.** Seven isolated worker lanes ran the five discriminating
scenarios (`02-feature`, `05-impact` ×3 runs, `08-routing`, `09-abstention`,
three-session `10-supersede`). Matched three-arm lanes: `gpt-5.6-terra`/medium
(Codex), `zai/glm-5.1:medium` (Pi), `claude-sonnet-5` (Claude Code);
candidate-only lanes: `gpt-5.6-sol`/high, `deepseek/deepseek-v4-pro:medium`,
`minimax/MiniMax-M3:medium`, `claude-haiku-4-5`. 70 judged batches, then a
3-run tie-break wave on `10-supersede` (GLM and Sonnet) that selected a
sharpened supersession rule. Judge: `claude -p --model claude-opus-5`, pinned
for the whole wave. Not numerically comparable with the 2026-07-24
Gemini-judged entry.

**Decisive result.** `gpt-5.6-terra` scored 1.000/1.000 on all five scenarios
for all three arms; `gpt-5.6-sol` passed 5/5 on the adopted-lineage candidate.
Every sub-ceiling cell on Claude/Pi lanes failed identically under the prior
core in the same wave (`02-feature` `refund_contract_canonized`, 0.93/0.86 on
Sonnet across all three arms), so no measured regression is attributable to
minimization. Tie-break on `10-supersede` (3 runs/arm): adopted core mean
0.97/0.97 on GLM and 0.94/0.97 on Sonnet, versus 0.91/0.92 and 0.98/0.92 for
the prior core; floors 0.91/0.92 on both, matching the prior core's observed
floor. Long-session compaction runs (04-memory-chain fixture, two forced
compactions verified per session via `isCompactSummary` events) kept full
Canon discipline on Sonnet; Haiku missed decision records in long sessions
under the prior core and the candidate alike — a tier limit, recorded as a
negative baseline, not a guidance regression.

**Limitations.** Judge/worker family overlap on the Claude lanes; the Kimi
K2.5 lane was dropped (OpenRouter 402, credits exhausted — the same failure
discarded an earlier partial wave, rerun entirely under the pinned Claude
judge); the previously unusable Claude eval adapter was repaired in the same
change (`--allowedTools` for headless writes). Result bundles under
`evals/results/20260801-*`; each batch's `guidance-used.md` is the
adopted-bytes authority.

### 2026-07-24 — invariant-first guidance adopted (superseded)

**Question.** Is the invariant-first rework ready for release across capable
and weaker live model tiers?

**Decision.** Adopt. This is an absolute cross-model readiness decision, not a
matched numerical A/B improvement claim against the retired inventory-first
guidance.

**Tested revisions.** The round-two panel used
`af76a5dec1a1651ff08861de8c701733206009b5`. Supersession hardening used
`a49f5f1`, and exact-final confirmation used
`1bd88410250d61ef2c028a133b9d4d8a5f31a6a5`. Every retained summary recorded a
clean source state.

**Comparison key.** Six isolated workers ran the same five discriminating
scenarios. `05-impact` used three runs; `02-feature`, `08-routing`,
`09-abstention`, and the three-session `10-supersede` used one run each. The
judge was `openrouter/google/gemini-3.1-pro-preview:high` through Pi. The panel
labels `GPT 5.5 high` and `GPT Spark` mapped to `gpt-5.6-sol` at high reasoning
and `gpt-5.6-terra` at medium reasoning, respectively.

| exact worker | harness | required batches | mechanical mean / floor | judge mean / floor |
|---|---|---:|---:|---:|
| `gpt-5.6-sol`, high | Codex | 5/5 | 1.000 / 1.000 | 1.000 / 1.000 |
| `gpt-5.6-terra`, medium | Codex | 5/5 | 1.000 / 1.000 | 1.000 / 1.000 |
| `zai/glm-5.1:medium` | Pi | 4/5 | 0.992 / 0.944 | 0.915 / 0.818 |
| `minimax/MiniMax-M3:medium` | Pi | 3/5 | 0.968 / 0.867 | 0.852 / 0.500 |
| `deepseek/deepseek-v4-pro:medium` | Pi | 3/5 | 0.972 / 0.870 | 0.812 / 0.636 |
| `openrouter/moonshotai/kimi-k2.5:medium` | Pi | 2/5 | 0.918 / 0.750 | 0.808 / 0.667 |

**Decisive result.** Both capable Codex tiers passed every required gate and
judge criterion. Weaker-tier failures remain negative baselines: they omitted
durable contract details, fabricated missing policy, malformed decision
metadata, missed current-state updates, or broke historical routing. Missing
routing telemetry was `unsupported`, never counted as a pass.

Round one exposed evaluator false positives and guidance gaps, so its scores
are not compared with round two. The accepted corrections made public-binding,
integer-arithmetic, inventory, abstention, supersession, historical-routing,
and validation-path checks semantic and explicit. On the exact final
supersession revision, GPT Spark passed at 1.000/1.000. GLM fixed its validation
path but still removed a required historical route, scoring 0.893/0.917; this
was model non-compliance rather than another guidance ambiguity.

**Deterministic evidence.** Repeated builds were fresh; 55 repository tests and
ten fixture suites passed; nine seeded Canon fixtures passed strict doctor
validation; 24 scenario JSON contracts parsed; Python, shell, ShellCheck, and
whitespace validation passed. Two independent final reviewers approved after
their findings were corrected.

**Artifacts and limits.** The local artifact-set key is
`live-20260724-invariant-first`, retained on the release machine under
`evals/results/` as a 43 MB Git-ignored archive. It is absent from fresh
checkouts. Retained receipts attest selected evaluator inputs but do not
cryptographically bind every executable, transcript, credential, or workspace.
Transport-only failures were excluded and successful direct reruns were used.

## Prior adoption decisions

### 2026-07-18 — evaluator integrity hardening adopted

**Decision.** Adopt a reviewed synthesis; do not adopt any raw candidate.

**Evidence.** An adversarial supervisor moved from 0/8 on the external frozen
base to 8/8 on all six candidates, but independent hard-gate review found a
ship blocker in every candidate. The synthesis added terminal receipt
integrity, retained input hashes, strict judge schemas, contained paths,
temporal byte snapshots, sandboxed holdouts, and explicit unsupported routing
telemetry. Deterministic validation passed.

**Limits.** The frozen-base object
`161d77d316bc79bc5a3486fe308e260ef66ae993` is not retained in this repository.
All implementation workers and reviewers were GPT-backed despite the panel
labels, and no final live paid-model batch followed the synthesis. Treat this
as evaluator-integrity evidence, not behavioral model-score evidence. This
guidance was later superseded by the invariant-first release; its integrity
controls remain.

### 2026-07-17 — durable-decision boundary adopted

**Decision.** Adopt the GPT Spark-labelled candidate, actually GPT-5.6 Terra
at medium reasoning, after matched Terra/Sol evaluation.

**Evidence.** The candidate passed all six three-session chains at
1.000 mechanical and judge means, including within each pinned worker/judge
stratum. Follow-up controls showed routine modal requirements created spurious
decision records in 6/6 baseline runs and 0/6 adopted runs while still
refreshing current-state Canon in 6/6. A strengthened checker then detected a
previously hidden predecessor overwrite and confirmed three fresh chains.

**Limits.** Kimi, ZAI, and MiniMax cells were transport failures, not
model-quality measurements. This guidance was later superseded by the
invariant-first release.

## Earlier experiment index

The detailed pre-compaction narrative remains recoverable from Git at
`fe820d3:evals/BASELINES.md`. This index retains only decisions that affect
future evaluation work.

| date | outcome | durable conclusion | record |
|---|---|---|---|
| 2026-06-11 | baseline | Strong Codex tiers saturated the original fixture set; future work needed harder scenarios or weaker tiers. | `08eae37` |
| 2026-06-14 | adopted | Optimizer round two improved the matched weak-tier mean by 0.15 without strong-tier regression. | `00c70c7` |
| 2026-06-14 | adopted | Hoisting the Canon-read-first directive removed catastrophic misses across the tested scenarios. | `6d14eda` |
| 2026-06-14 | rejected | The lean 141-line candidate regressed feature behavior; instruction removal was not a demonstrated win. | `9f446d3` |
| 2026-06-15 | rejected | Durable abstention-gap wording did not improve behavior above noise; do not retry wording-only variants without a new mechanism. | `9f638c7` |
| 2026-06-15 | rejected | The integer-arithmetic cue traded a routing gain for a feature regression and was net neutral. | `57c12b9` |
| 2026-06-15 | rejected | Supersession-hygiene gains disappeared in same-batch confirmation; cross-batch deltas were variance. | `11524e9` |

## Entry template

New entries should stay short and use this shape:

```markdown
## YYYY-MM-DD — decision title

**Question.** The single decision this evaluation informs.

**Decision.** Adopt, reject, or baseline only.

**Tested revision and comparison key.** Source revision; scenarios and run
counts; exact worker, reasoning, harness, judge, and relevant evaluator pins.

**Decisive result.** Required passes, means and floors, or the qualitative
gate that decided the outcome.

**Artifacts and limits.** Durable URL or local artifact-set key, provenance
boundary, invalid cells, and what the evidence does not establish.
```
