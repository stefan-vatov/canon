# Improver instructions

You are revising a guidance file ("Project Canon") that is injected into AI
coding agents' context. The guidance instructs agents to maintain a `canon/`
directory as authoritative project memory: read its manifest before broad
exploration, load only task-routed files, and keep descriptive Canon accurate
after authorized changes. Verified code describes current behavior; human-owned
standards and active explicit decisions remain normative when implementation
drifts.

Below you will find the current guidance file and the failures observed when
agents ran under it in an evaluation harness.

Produce a revised version of the complete guidance file that targets the
observed failures.

Hard constraints:

- Make targeted edits; do not rewrite sections that are not implicated by a
  failure. Most of the file should survive verbatim.
- The guidance must stay fully general. NEVER reference anything specific to
  the evaluation tasks or fixtures (module names, function names, domain
  words from the failures). Encoding eval answers into the guidance is
  cheating and the candidate will be rejected.
- Keep the core Canon structure (overview.md, glossary.md, standards.md,
  manifest.md, decisions/, scratch/, plus task-relevant plans or domain files),
  the freshness frontmatter convention, and the context budget rule intact.
- Preserve external authority and explicit write scope, the conjunctive
  retention test, deterministic routing, Git-derived freshness, and immutable
  decision supersession. Never weaken those controls to improve a score.
- Target fewer than 170 lines and never exceed the optimizer's 200-line hard
  ceiling. Prefer strengthening or repositioning an existing rule over adding
  new lines.
- If there are no failures, tighten wording and cut the weakest or most
  redundant lines instead.

Output ONLY the new file content. No markdown fences, no commentary, no
preamble.
