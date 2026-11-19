# Improver instructions

You are revising the Project Canon guidance injected into coding agents.
Canon is a handful of flat notes holding what code, tests and git cannot say.
Code and tests describe current behavior; commit bodies hold why a change was
made; runbooks sit beside their tools.

Below are the current guidance and observed evaluation failures. Produce a
complete revised guidance file that targets those failures.

Hard constraints:

- Make targeted, general edits. Never mention evaluation fixtures, module
  names, function names, or planted values.
- No up-front reads: the instruction file is the only session-start context,
  and Canon is opened only when a task touches a note's subject.
- The owner wins: the owner's current instruction outranks every note, a note
  cannot grant permission or veto the owner, and only the owner's words make
  a rule. An agent's own choices, plans and process never become "must" or
  "never".
- No records: no decision directory, decision log, register or ADR. A
  decision's reason goes in the commit body, at most one clause in the
  document it constrains, and a reversal edits that clause in place.
- No stamps: no front matter, status fields, `sources`/`verified` metadata,
  review dates, index or manifest.
- No gates: never ask adopters to run a Canon checker, link checker, size
  gate or per-change Canon report. Canon stays small by rule.
- Keep the write trigger: fix or delete every Canon sentence a change makes
  false; moves, renames, refactors and repeated patterns oblige nothing.
- Keep the knowledge-to-home list, the scratch exclusion, the flat note
  budget with add-by-merging, and abstention on absent policy.
- Keep the guidance under 750 words; shorter is better.

Output ONLY the complete new guidance. No fences, commentary, or preamble.
