# Research basis for Canon eval scenarios

This is the research snapshot used to design scenarios 08–10. It summarizes
sources reviewed on 2026-06-14 about long-horizon agent memory and long-context
degradation.
The snapshot is historical evidence, not the current eval runbook; use
[PLAYBOOK.md](PLAYBOOK.md) for current operations and [BASELINES.md](BASELINES.md)
for adoption decisions.

## Failure-mode taxonomy in the cited benchmarks

- **[LongMemEval](https://github.com/xiaowu0162/LongMemEval)**: five abilities —
  information extraction, multi-session reasoning, temporal reasoning,
  **knowledge updates**, **abstention** (declining when info isn't available).
  Ships context tiers (S ~115k tok/~40 sessions; M ~500 sessions) plus an
  **Oracle variant with only evidence sessions** that isolates retrieval/
  routing quality from long-context degradation.
- **[LoCoMo](https://github.com/snap-research/locomo)**: single-hop, multi-hop,
  temporal, commonsense, **adversarial (unknowable)** question types;
  ~300 turns / ~35 sessions per conversation.
- **[MemBench](https://aclanthology.org/2025.findings-acl.989/)**: information extraction,
  cross-session reasoning, knowledge updating, temporal reasoning, reflective
  summarization. Builds difficulty by **injecting irrelevant "noise" content
  verified NOT to conflict, tuning the noise proportion**. Real memory
  mechanisms show a **sharp accuracy decline as token volume grows** (>100k).
- **[MemoryAgentBench](https://arxiv.org/abs/2507.05257)**: four competencies — accurate
  retrieval, test-time learning, long-range understanding, **selective
  forgetting**; *no current method masters all four*. Reformats long-context
  data into multi-turn (session-like) form.
- Simple single-factoid needle-in-a-haystack is largely solved; difficulty
  comes from **distractors, multi-hop, and irrelevant-content volume**.

## Gaps in the pre-scenario-08 suite

1. **Routing vs bulk-load is untested.** The Oracle-variant idea: score
   *retrieval/routing quality separately from correctness*. A run can get the
   right answer by bulk-reading everything — that is a routing failure even
   though correctness passes. Our "context budget / never bulk-load the whole
   Canon" rule had zero coverage.
2. **Distractors.** MemBench-style: plant plausible-but-wrong values in
   sibling domain docs; only the correct domain (or code) holds the truth.
3. **Abstention.** Asking for a policy that was never decided must yield
   "not established — surface the gap", not a fabricated value. Untested.
4. **Temporal updating & selective forgetting.** A reversed value must not be
   re-applied; the current one wins. Partially tested by 04's cap change;
   abstention and reversal deserve dedicated probes.

## Scenarios built from this

- **08-routing** — ten flat notes, one relevant, others carry distractor
  constants. Scores correctness (holdout) AND a *routing-precision* mechanical
  check (transcript read analysis: read the matching note, did NOT bulk-read
  sibling notes) AND distractor resistance (wrong values absent from code).
  Failure modes: routing/retrieval, distractor robustness, context budget.
- **09-abstention** — task asks the agent to apply a policy that exists in no
  Canon file and no code. Correct: surface the gap and ask the owner; wrong:
  fabricate a constant. Failure mode: abstention.
- **10-reversal** — the owner reverses a value a note states and calls final.
  The note is edited in place: the old value disappears, the claim of
  permanence goes, the cross-owner fact that still holds stays, and history is
  left to git. An authenticated snapshot verifies a later session leaves the
  corrected note alone. Failure modes: temporal updating and selective
  forgetting.

Selective forgetting argues for editing the current statement in place. The
2026-08 suite instead rewarded keeping every superseded decision as an
immutable, routed record; in a production adopter that produced 272 records
the agents had to read past, and an immutable approval record overrode the
owner's later instruction. Git already keeps every prior statement
(`git log -S`), so Canon holds only what is true now.

## Remaining research frontier

The current suite still lacks large-repository multi-hop aggregation,
consolidation under repeated updates, package-local versus repository-wide
routing, controlled context-volume scaling, and the field costs no fixture is
big enough to show (commit churn, stamp-only touches, words read before code).
Add those as new scenarios or measure them on a real adopter; do not infer
coverage from the existing fifteen.
