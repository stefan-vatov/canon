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

Prior history: pre-adoption baseline 0.955 (01-bootstrap + 06-decisions,
1 run, 2026-06-10); optimizer round 1 kept +0.022 (repo-root .gitignore
instruction + decision-citation discipline), re-validated, adopted at
202feaf.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
