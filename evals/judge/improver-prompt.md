# Improver instructions

You are revising a guidance file ("Project Canon") that is injected into AI
coding agents' context. The guidance instructs agents to maintain a `canon/`
directory as authoritative project memory: read it before exploring code,
keep it accurate after meaningful changes, treat running code as outranking
documents.

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
- Keep the mandatory Canon structure (overview.md, glossary.md, standards.md,
  manifest.md, decisions/, plans/, scratch/, domain dirs), the freshness
  frontmatter convention, and the context budget rule intact.
- Stay under 170 lines. Longer guidance dilutes compliance; prefer
  strengthening or repositioning an existing rule over adding new ones.
- If there are no failures, tighten wording and cut the weakest or most
  redundant lines instead.

Output ONLY the new file content. No markdown fences, no commentary, no
preamble.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
