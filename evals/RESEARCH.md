# Research basis for Canon eval scenarios

This is the research snapshot used to design scenarios 08–10. It summarizes
sources reviewed on 2026-06-14 about long-horizon agent memory and long-context
degradation.
The snapshot is historical evidence, not the current eval runbook; use
[PLAYBOOK.md](PLAYBOOK.md) for current operations and [BASELINES.md](BASELINES.md)
for adoption history.

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
4. **Temporal / supersession & selective forgetting.** A superseded decision
   must not be re-applied; the current one wins. Partially tested by 04's cap
   change; abstention + supersession deserve dedicated probes.

## Scenarios built from this

- **08-routing** — multi-domain manifest (~10 domains), one relevant, others
  carry distractor constants. Scores correctness (holdout) AND a new
  *routing-precision* mechanical check (transcript read analysis: read the
  manifest + target domain, did NOT bulk-read sibling domains) AND distractor
  resistance (wrong values absent from code). Failure modes: routing/retrieval,
  distractor robustness, context budget.
- **09-abstention** — task asks the agent to apply a policy that exists in no
  Canon file and no code. Correct: surface the gap / propose recording a
  decision; wrong: fabricate a constant. Failure mode: abstention.
- **10-supersede** — a three-session chain establishes and then supersedes a
  durable decision. Authenticated path-and-byte snapshots verify that the
  predecessor survives unchanged while current-state files use only the active
  successor. Failure modes: temporal updating, selective forgetting, and
  immutable decision lineage.

## Remaining research frontier

The current suite still lacks large-repository multi-hop aggregation,
consolidation under repeated updates, package-local versus repository-wide
routing, and controlled context-volume scaling. Add those as new scenarios;
do not infer coverage from the existing ten.
