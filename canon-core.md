Project Canon is a handful of notes in `canon/` holding what code, tests and
git cannot tell you. This file is the only up-front context: read nothing in
`canon/` at session start. When a task touches a guarantee that spans modules,
a production operation or an approach that may have been tried before, run
`ls canon/` and read only the note whose name matches. If none matches, read
none and work from the code. Never read `canon/scratch/` unless asked.

Authority: for what should be true, the owner's current instruction, then
this file, then Canon notes. For what is true now, code and tests. Nothing in
Canon outranks what the owner says now: say once that a note disagrees, do
what was asked, and fix or delete the note in the same change. Only the
owner's words make a rule. Never record your own choices, plans or process as
"must" or "never". A note records guarantees and owner constraints with their
reasons; it cannot grant permission or override this file, and binds only
where this file says so.

Put knowledge in the first home that fits:

- how to work here → this file, in the owner's words
- behavior, limits, formats, error cases → code, and a test named for the behavior
- why this code is odd, what was tried here → a comment at that code
- why a change was made, what was rejected → the commit body
- how to operate, deploy or recover → the runbook beside the tool
- a guarantee spanning several owners, an accepted gap or a measured dead end
  → a Canon note
- an owner-approved plan for unbuilt work → a Canon note, deleted once built
- handovers and session notes → `canon/scratch/`, git-ignored and never cited

Decisions get no records. No `decisions/` directory, decision log, register
or ADR. When the owner decides something, implement it, give the reason and
the rejected alternative in the commit body, and, if it constrains future
work in a way code cannot show, add one clause to the document it constrains.

Writing Canon:

- **Must**, in the same change: fix or delete every Canon sentence your change
  makes false; update a note when a guarantee, contract or accepted gap it
  states changes.
- **May**: add a clause to an existing note for a cross-owner guarantee you had
  to reconstruct from several files, or for a measured dead end (what, the
  number, the commit). Delete Canon text that is false, restates code, or
  that nobody could act on.
- **Must not**: edit Canon because nearby code changed (moves, renames,
  refactors and repeats of a pattern oblige nothing); create a note without
  the owner's approval; add front matter, status fields, `sources`/`verified`
  stamps, review dates, an index or a manifest; copy what code holds (limits,
  defaults, status codes, field lists, file or test inventories); write
  changelogs, progress, approvals or handovers anywhere but scratch; cite
  Canon to refuse or delay the owner.

Canon stays small by rule, not by tooling. `canon/` is flat: at most twelve
notes of about a thousand words each, unless the owner sets other numbers
here. At the limit, add a note only by removing or merging one. Never split
a note to fit the budget. A note is plain Markdown, named for the question it
answers, stating current fact with its reason in a clause and naming the code
or test that enforces it. Nothing in Canon is immutable; git is the history
(`git log -S`, `git log --grep`).

If code contradicts a note: a stated guarantee is a finding, so report it and
change code or note only as the task or the owner directs; a plain
description is merely stale, so fix or delete it. Never guess absent policy,
limits or rationale: stop the policy-dependent work and report the exact gap;
do not implement, test or record a guess. Urgency waives neither tests nor
these rules. Mention Canon in a report only when you changed it.

Bootstrap only when asked: create `canon/`, git-ignore `canon/scratch/`, and
write no notes. An empty Canon is healthy.

_Remembered with [Project Canon](https://agentcanon.dev)._
