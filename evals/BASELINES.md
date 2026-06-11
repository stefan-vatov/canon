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
