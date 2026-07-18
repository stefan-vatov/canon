---
name: compact-canon
description: Audit and safely compact an overgrown Project Canon (`canon/`) by inventorying all permanent knowledge, checking routed claims against repository evidence, merging overlap, removing reconstructible or completed-work prose, tightening manifest routes, and preserving human-owned standards and immutable decisions. Use when asked to clean, compact, prune, deduplicate, tighten, reorganize, or reduce a large Canon; when Canon has accumulated stale or overlapping files; or when a dry-run compaction assessment is needed.
---

# Compact Canon

Compact durable project memory without optimizing blindly for fewer files or
lines. Preserve information that changes future decisions; remove memory that
adds context cost without durable value.

## Choose the mode

- Treat `audit`, `assess`, `mock`, `plan`, or `dry run` as read-only.
- Treat an explicit request to `compact`, `clean`, `prune`, `deduplicate`, or
  `tighten` as authorization to edit `canon/` only.
- Do not edit source code, tests, project configuration, or decision records.
- Do not commit, push, or modify unrelated dirty files unless separately asked.

Apply mode requires a completely clean worktree, including untracked files. If
it is dirty, report the exact paths and stop after the audit; never stash,
reset, restore, stage, or delete existing work. Never delete an untracked Canon
file; classify it and report it.

## Establish the baseline

1. Read applicable repository instructions.
2. Record `git status --short`, the current commit, and the Canon paths already
   dirty before the run.
3. Read `canon/manifest.md` and `canon/standards.md`, then every permanent Canon
   Markdown file in bounded, manifest-order batches. Keep a claim ledger rather
   than loading the entire Canon into one context. This task permits a full
   Canon traversal; it does not permit a full source-tree traversal.
4. Run the bundled analyzer:

   ```sh
   python3 .codex/skills/compact-canon/scripts/analyze_canon.py --root /path/to/repo
   ```

   Use `--json` when another tool will consume the inventory. If the skill is
   installed outside the repository, invoke the script from the skill's own
   directory.

5. Run `tools/canon-doctor.py --root <repo> --json` when that tool exists.
   Treat its result as mechanical evidence, not as permission to rewrite
   policy.

Record before-metrics: HEAD, permanent files, lines, bytes, size-cap failures,
manifest coverage, fresh/stale/indeterminate files, repeated paragraphs,
overlap candidates, doctor findings, and hashes of every decision record.

## Classify every permanent file

Assign one disposition and a short evidence statement:

- **Keep** — unique durable knowledge that passes the retention test.
- **Merge** — durable content duplicated across files that can remain one
  focused topic within the size caps.
- **Rewrite** — useful knowledge obscured by verbosity, chronology, repeated
  examples, or implementation detail.
- **Delete** — content fully reconstructible from localized code or ordinary
  search, obsolete descriptive state, completed-work narration, or exact
  duplication with no unique contract or rationale.
- **Abstain** — normative, ambiguous, weakly sourced, or unsafe to change.

Retain a claim only when all are true:

1. A future session is likely to need it.
2. Getting it wrong would materially change a decision or implementation.
3. It is stable and has an identified source or human owner.
4. It is not reliably reconstructible from localized code, tests, types,
   configuration, or ordinary search.

For every proposed merge, rewrite, or deletion, inspect only the named sources
and the smallest necessary surrounding code. Do not trust stale Canon prose as
proof of its own value. Size, age, formatter padding, wide tables, long lines,
and lexical similarity are investigation signals, never deletion proof. Prefer
abstention when evidence is incomplete.

## Preserve these boundaries

- Never edit, delete, rename, combine, or reuse an existing decision record.
  Only explicit new human direction can supersede one, through a new record.
- Preserve `standards.md` verbatim by default. Automatically remove only a
  byte-identical duplicate owned elsewhere; any semantic rewrite requires
  explicit human confirmation.
- Preserve supplied rationale and rejected alternatives exactly in meaning;
  never manufacture missing rationale.
- Keep the four core files. Keep exact manifest routes for every permanent
  Markdown file except `manifest.md`.
- Keep descriptive files current-state oriented, single-topic, and within the
  repository's line and byte caps.
- Exclude `canon/scratch/` from permanent-memory metrics. Do not promote
  handovers or session notes into permanent memory merely to preserve them.
- Do not archive deleted bloat into another permanent file or into scratch.
- A smaller Canon is not automatically a better Canon. Set no deletion quota.

## Apply a compaction

In apply mode, create an operation ledger before editing. Then:

1. Rewrite useful files in place before considering moves or deletion.
2. Merge overlapping descriptive files only when the destination remains one
   topic and all unique contracts, caveats, and links survive.
3. Update the manifest and inbound relative links in the same patch as any
   move, merge, or deletion.
4. Remove changelog prose, completed-task summaries, duplicate examples,
   speculative notes, and routine implementation detail.
5. Refresh `sources` and `verified` metadata only after checking the named
   source evidence. Follow the repository's existing freshness convention.
6. Leave standards, decisions, and uncertain claims unchanged; list them under
   `Abstained` in the result. A proven no-op is a valid compaction result.

Use patch-based edits. Preserve pre-existing user changes and keep the diff
limited to the authorized Canon paths.

## Verify semantic preservation

1. Re-run the analyzer and Canon doctor.
2. Resolve broken routes and links, size-cap failures, malformed frontmatter,
   and newly stale metadata.
3. Run `git diff --check` and inspect the complete Canon diff.
4. Compare the operation ledger with the diff: every deletion must have a
   retained destination or explicit evidence that it failed the retention test.
5. Search the post-compaction Canon for every active decision name, normative
   keyword, public contract, operational constraint, and domain term identified
   in the baseline.
6. Confirm decision paths and hashes are identical, standards bytes are
   unchanged, and no non-Canon path changed.

Report before/after metrics, files merged or removed, durable information
preserved, abstentions, validator results, and the exact diff scope. In a
read-only run, report candidates and projected savings without changing files.
