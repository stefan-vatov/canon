# Canon Eval Rubric

Each criterion is scored 1 (pass), 0 (fail), or null (not applicable).
Mechanical checks are scored by `bin/check.py`; the criteria below are scored
by the judge from the transcript, diff, final Canon, and check evidence.

| id | criterion |
|----|-----------|
| canon_read_first | The agent read `canon/manifest.md` before broad code exploration and did not read scratch. Null if no `canon/` existed at session start. |
| canon_impact_correct | The agent correctly classified the work as no impact, clarification, or change. It updated only the owning invariant when a durable guarantee changed and left Canon untouched for implementation-only work. |
| implementation_inventory_avoided | Canon edits describe durable laws, public semantics, rationale, and validation—not exhaustive files, symbols, exports, helpers, tests, or implementation sequences. Null when Canon was not edited. |
| metadata_and_routing | New or edited pages use valid status/scope/validation/relationship metadata; normative pages have concise manifest routes; scratch is neither routed nor cited. Null when Canon was not edited. |
| current_rule_style | Normative architecture pages state current guarantees without dated changelog narration, completed-work summaries, or temporary migration status. Decision history is exempt. Null when Canon was not edited. |
| code_correct | The code change implements the requested task correctly and completely. |
| code_follows_standards | The code change obeys applicable rules in `canon/standards.md`. Null when no standard applies. |
| minimal_diff | No unrelated refactors, reformatting, comments, speculative additions, or ceremonial Canon edits. |
| style_match | New code matches the fixture's naming, structure, and idiom. |
| normative_conflict_handled | When verified behavior and normative Canon conflict, the agent did not silently rewrite either side. It followed explicit human direction, repaired the defect, or surfaced the ambiguity. Null unless a conflict is planted. |
| memory_persistence | Knowledge established in an earlier session was correctly applied by a later fresh process from durable repository state. Null unless the scenario spans sessions. |
| rationale_capture | Explicit durable decisions preserve supplied rationale and rejected alternatives, and immutable predecessors survive supersession. Null when no decision rationale is supplied. |
| executable_validation | A changed normative guarantee links to the smallest stable executable check where feasible; missing automation is reported rather than replaced with prose inventory. Null when no Canon guarantee changed. |
| abstention | The agent surfaces a missing policy instead of inventing a value or writing speculative Canon. Null unless the task depends on unspecified policy. |
| routing_discipline | The agent loads the manifest and relevant page without bulk-reading unrelated pages or scratch, and uses the correct rule rather than a distractor. Null unless the scenario contains routing choices. |

Judge score is the mean of non-null criteria. Mechanical score is the fraction
of passing `check.py` checks. Report them separately because they fail for
different reasons.
