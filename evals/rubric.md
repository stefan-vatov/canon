# Canon Eval Rubric

Each criterion is scored 1 (pass), 0 (fail), or null (not applicable to the
scenario). Mechanical checks (tests, diff scope, planted rules) are scored by
`bin/check.py`; the criteria below are scored by the LLM judge from the
transcript, the diff, and the final Canon contents.

| id | criterion |
|----|-----------|
| canon_read_first | The agent read `canon/manifest.md` before broad code exploration. Null if no `canon/` existed at session start. |
| canon_created_or_updated | When an authorized change affected durable knowledge that passed the retention test, the agent updated the relevant Canon and routes without being re-prompted; it did not canonize routine implementation detail. Null when the task changed no durable knowledge. |
| current_state_style | Current-state Canon files written or edited by the agent describe the system as it is now. No dated changelog narration, "previously" prose, or completed-work summaries appear outside immutable decision history. |
| structure_respected | Canon structure rules followed: core indexes may aggregate their defined role; other permanent files cover one topic; every permanent file except `manifest.md` has one route; all permanent files stay at most 250 lines and 64 KiB; session scraps stay in `canon/scratch/`. |
| code_correct | The code change implements the requested task correctly and completely. |
| code_follows_standards | The code change obeys the binding rules in the fixture's `canon/standards.md`. Null if the fixture has no standards file. |
| minimal_diff | No unrelated refactors, reformatting, comment churn, or speculative additions outside the task. |
| style_match | New code matches the existing fixture's naming, structure, and idiom. |
| drift_resolution | Where descriptive Canon contradicted verified code, the agent used code as evidence, surfaced the disparity, and corrected the description. It did not rewrite a human-owned standard or active decision merely to match drift. Null unless the scenario plants a contradiction. |
| memory_persistence | Knowledge established in an earlier session was correctly applied by a later fresh agent process from durable repository state, with evidence showing whether Canon or code carried it. Null unless the scenario spans multiple sessions. |
| rationale_capture | Durable decisions were recorded in `canon/decisions/` with their rationale (and rejected alternatives when given), not just the rule itself, and surfaced when later relevant. Null if no rationale was stated in any task. |
| freshness_maintained | Domain files the agent created or relied on carry valid `sources`/`verified` frontmatter. During authorized write work, affected stale files were refreshed before being treated as current; during read-only work, staleness was reported without mutation. Null if the fixture's Canon uses no frontmatter. |
| abstention | When the task depends on a fact, policy, or value that exists in neither the Canon nor the code, the agent recognized the gap and surfaced it (asked, or recorded it as an open question / decision-needed) instead of fabricating a value and implementing it as if it were established. Null unless the task probes an unspecified fact. |
| routing_discipline | The agent loaded the Canon files the task needed (manifest + the relevant domain) without bulk-reading unrelated domains, and used the right source rather than a similar-looking distractor. Null unless the scenario has many domains or planted distractors. |

Scoring: a run's judge score is the mean of non-null criteria. A run's
mechanical score is the fraction of passing checks from `check.py`. Report both
separately for adoption because they fail for different reasons. The optimizer
uses a blended mean only to rank proposals; that number is not an adoption
metric.
