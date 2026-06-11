# Canon Eval Rubric

Each criterion is scored 1 (pass), 0 (fail), or null (not applicable to the
scenario). Mechanical checks (tests, diff scope, planted rules) are scored by
`bin/check.py`; the criteria below are scored by the LLM judge from the
transcript, the diff, and the final Canon contents.

| id | criterion |
|----|-----------|
| canon_read_first | The agent consulted `canon/manifest.md`, `canon/overview.md`, or `canon/glossary.md` before broad code exploration. Null if no `canon/` existed at session start. |
| canon_created_or_updated | After a change to behavior, structure, or contracts, the agent created or updated the relevant Canon files without being re-prompted. |
| current_state_style | Canon files written or edited by the agent describe current system state. No changelog entries, dates, "previously", or completed-work summaries in permanent files. |
| structure_respected | Canon structure rules followed: one topic per file, manifest kept in sync with all Canon files, files under 250 lines, session scraps only in `canon/scratch/`. |
| code_correct | The code change implements the requested task correctly and completely. |
| code_follows_standards | The code change obeys the binding rules in the fixture's `canon/standards.md`. Null if the fixture has no standards file. |
| minimal_diff | No unrelated refactors, reformatting, comment churn, or speculative additions outside the task. |
| style_match | New code matches the existing fixture's naming, structure, and idiom. |
| drift_resolution | Where Canon contradicted code, the agent treated code as source of truth, surfaced the disparity to the user, and corrected the Canon. Null unless the scenario plants a contradiction. |
| memory_persistence | Knowledge stated conversationally in an earlier session (policies, limits, terminology) was correctly applied in later sessions without being restated — evidence that it traveled via the Canon, not luck. Null unless the scenario spans multiple sessions. |
| rationale_capture | Durable decisions were recorded in `canon/decisions/` with their rationale (and rejected alternatives when given), not just the rule itself, and surfaced when later relevant. Null if no rationale was stated in any task. |
| freshness_maintained | Domain files the agent created or relied on carry `sources`/`verified` frontmatter, and the agent refreshed stale files (content and `verified`) before trusting them. Null if the fixture's Canon uses no frontmatter. |

Scoring: a run's judge score is the mean of non-null criteria. A run's
mechanical score is the fraction of passing checks from `check.py`. Report
both; do not blend them into one number, they fail for different reasons.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
