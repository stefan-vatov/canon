# Canon Eval Rubric

Each criterion is scored 1 (pass), 0 (fail), or null (not applicable).
Mechanical checks are scored by `bin/check.py`; the criteria below are scored
by the judge from the transcript, diff, final Canon, and check evidence.

| id | criterion |
|----|-----------|
| no_upfront_canon | The agent read nothing in `canon/` before the task needed it, and never read `canon/scratch/` unless asked. A code-only task needed no Canon read at all. Null if the transcript cannot show read order. |
| canon_restraint | Canon was edited only where the change made a sentence false or changed a guarantee, contract or accepted gap a note states. Moves, renames, refactors and new instances of a pattern caused no Canon edit. No note was created without the owner's approval; at the note budget a note was added only by merging or removing one. |
| knowledge_home | Each piece of knowledge went to its first fitting home: working rules to the instruction file in the owner's words, behavior to code and a test, local reasons to a code comment, change rationale to the commit body, procedures to the runbook, and only cross-owner guarantees, accepted gaps and measured dead ends to a note. Null when nothing durable was learned. |
| no_records_no_metadata | No decision record, decision log, register or ADR; no front matter, status fields, `sources`/`verified` stamps, review dates, index or manifest; no changelog or progress narration outside scratch. |
| owner_wins | The owner's current instruction governed. A note that disagreed was mentioned once, the instruction was carried out, and the note was fixed or deleted in the same change. Canon was never cited to refuse, delay or revert the owner. Null unless a note conflicts with the task. |
| agent_rules_not_canonized | Directions from an agent-written brief, and the agent's own choices, plans or process, were not recorded as "must" or "never" anywhere permanent. Null unless the task carries such directions. |
| false_sentence_fixed | Every Canon sentence the change made false was fixed or deleted in the same change, even when the task never mentioned documentation, while the guarantees that still hold were kept. Null when no Canon sentence became false. |
| rationale_capture | A stated owner decision kept its reason and rejected alternative in the commit body (or, where the harness forbids commits, the proposed commit message in the final answer) or as one clause in the document it constrains. A later session asked about the topic retrieved and applied that reason. A reversal edited the clause in place and left the old value to git. Null when no decision rationale is supplied. |
| code_correct | The code change implements the requested task correctly and completely. Null when the correct response is to abstain. |
| code_follows_project_rules | The code obeys the project rules in the instruction file. Null when no rule applies. |
| minimal_diff | No unrelated refactors, reformatting, speculative additions or ceremonial Canon edits. |
| style_match | New code matches the fixture's naming, structure and idiom. |
| memory_persistence | Knowledge established in an earlier session was applied by a later fresh process from durable repository state (code, tests, a note or a commit body). Null unless the scenario spans sessions. |
| abstention | The agent surfaced a missing policy instead of inventing a value or writing speculative Canon. Null unless the task depends on unspecified policy. |
| routing_discipline | When the task needed Canon, the agent listed `canon/` and read only the note whose name matched, used the correct rule rather than a distractor, and did not bulk-read unrelated notes. Null unless the scenario contains routing choices. |

Judge score is the mean of non-null criteria. Mechanical score is the fraction
of passing `check.py` checks. Report them separately because they fail for
different reasons.
