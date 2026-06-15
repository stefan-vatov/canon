# Judge instructions

You are grading a single run of an AI coding agent that was operating under
"Project Canon" guidance: the agent must treat the `canon/` directory as
authoritative project memory, consult it before broad code exploration, keep
it accurate after meaningful changes, and treat running code as outranking
Canon documents when they disagree.

Below you will find: the rubric, the task(s) the agent was given, the agent's
diff, the final Canon contents, mechanical check results, and a (possibly
truncated) transcript. Multi-session scenarios run each task as a FRESH agent
session in the same workspace: nothing carries over between sessions except
the repository contents, so any knowledge from an earlier task that shows up
correctly in a later one must have traveled through the Canon (or code).
Weigh memory_persistence heavily in those scenarios — it is the core claim
under test.

Score every rubric criterion as 1 (clearly satisfied), 0 (violated or
absent), or null (not applicable to this scenario). Be strict: when evidence
is missing or ambiguous, score 0, not 1.

When the correct response to the task is to abstain — the task depends on a
fact or policy that exists in neither the Canon nor the code, so the right
move is to surface the gap rather than implement — score `code_correct` as
null (not 0): producing no implementation is correct, and `abstention` is the
criterion that judges it. Do not penalize a correct refusal under
`code_correct` or `minimal_diff`. Use the transcript to verify
*ordering* claims (e.g. Canon read before code exploration), the diff to
verify code claims, and the Canon contents to verify documentation claims.
Do not let the mechanical check results substitute for your own reading;
they are context only.

Reply with ONLY a JSON object, no markdown fences, in this shape:

{
  "criteria": [
    {"id": "canon_read_first", "score": 1, "reason": "..."},
    {"id": "canon_created_or_updated", "score": 0, "reason": "..."},
    {"id": "current_state_style", "score": null, "reason": "..."},
    {"id": "structure_respected", "score": 1, "reason": "..."},
    {"id": "code_correct", "score": 1, "reason": "..."},
    {"id": "code_follows_standards", "score": 1, "reason": "..."},
    {"id": "minimal_diff", "score": 1, "reason": "..."},
    {"id": "style_match", "score": 1, "reason": "..."},
    {"id": "drift_resolution", "score": null, "reason": "..."},
    {"id": "memory_persistence", "score": null, "reason": "..."},
    {"id": "rationale_capture", "score": null, "reason": "..."},
    {"id": "freshness_maintained", "score": null, "reason": "..."},
    {"id": "abstention", "score": null, "reason": "..."},
    {"id": "routing_discipline", "score": null, "reason": "..."}
  ],
  "notes": "one short paragraph: the most important behavioral gap you saw"
}

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
