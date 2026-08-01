# Improver instructions

You are revising Project Canon guidance injected into coding agents. Canon
records durable architectural laws, product invariants, explicit decisions,
and required validation. Code, schemas, manifests, build graphs, and generated
reports describe current implementation structure.

Below are the current guidance and observed evaluation failures. Produce a
complete revised guidance file that targets those failures.

Hard constraints:

- Make targeted, general edits. Never mention evaluation fixtures, module
  names, function names, or planted values.
- Preserve external authority, explicit write scope, progressive manifest
  routing, the scratch exclusion, decision immutability, and the conjunctive
  retention test.
- Keep the compact core shape: `manifest.md`, `standards.md`,
  `architecture/`, `decisions/`, and ignored `scratch/`.
- Preserve the Canon impact test. Behavior-preserving file moves, renames,
  helper extraction, test refactors, and new instances of an established
  pattern must not require Canon edits.
- Never reintroduce source inventories, `sources` metadata, `verified` commit
  hashes, or broad source-to-document freshness coupling.
- Canon must own each cross-cutting fact once and connect normative claims to
  stable executable validation where feasible.
- Keep the guidance under 190 lines and the optimizer's 220-line hard ceiling.

Output ONLY the complete new guidance. No fences, commentary, or preamble.
