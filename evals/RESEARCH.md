# Research: the next frontier for Canon evals

Deep-research pass (2026-06-14, 11 adversarially-verified claims; full run hit
a session limit before final synthesis). Sources are long-horizon agent-memory
benchmarks and long-context degradation studies. This file records the findings
that drive new scenarios so designs are traceable to evidence.

## Verified failure-mode taxonomy (convergent across benchmarks)

- **LongMemEval** (github.com/xiaowu0162/LongMemEval): five abilities —
  information extraction, multi-session reasoning, temporal reasoning,
  **knowledge updates**, **abstention** (declining when info isn't available).
  Ships context tiers (S ~115k tok/~40 sessions; M ~500 sessions) plus an
  **Oracle variant with only evidence sessions** that isolates retrieval/
  routing quality from long-context degradation.
- **LoCoMo** (snap-research.github.io/locomo): single-hop, multi-hop,
  temporal, commonsense, **adversarial (unknowable)** question types;
  ~300 turns / ~35 sessions per conversation.
- **MemBench** (aclanthology.org/2025.findings-acl.989): info extraction,
  cross-session reasoning, knowledge updating, temporal reasoning, reflective
  summarization. Builds difficulty by **injecting irrelevant "noise" content
  verified NOT to conflict, tuning the noise proportion**. Real memory
  mechanisms show a **sharp accuracy decline as token volume grows** (>100k).
- **MemoryAgentBench** (arxiv 2507.05257): four competencies — accurate
  retrieval, test-time learning, long-range understanding, **selective
  forgetting**; *no current method masters all four*. Reformats long-context
  data into multi-turn (session-like) form.
- Simple single-factoid needle-in-a-haystack is largely solved; difficulty
  comes from **distractors, multi-hop, and irrelevant-content volume**.

## Implications for Canon (what we were NOT yet testing)

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

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
