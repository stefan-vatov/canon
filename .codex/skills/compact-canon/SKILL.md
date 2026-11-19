---
name: compact-canon
description: One-time migration that slims an overgrown or legacy Project Canon (`canon/`) to a handful of flat notes. Use when a repository's canon has decision records, `sources`/`verified` or `status` front matter, a manifest, per-feature specs or mandatory session-start reads, or when asked to slim, compact, prune, migrate or assess what a canon costs. A dry run changes nothing. Not for routine upkeep, which the installed Canon block already covers.
---

# Compact Canon

Take a canon that grew into a second codebase and leave what the current Canon
block allows: at most twelve flat notes holding what code, tests and git cannot
say. Most of what you find goes; git keeps all of it.

This skill was written from a real migration. In one adopter's last 30 days
under the older rules, `canon/` was touched in 488 of 639 commits and about
half of all canon file touches were `verified:` bumps; at migration it held
384 files, about 200k words and 272 decision records. A typical fix was
estimated to read about 23k tokens of canon before any code, and an
"immutable" approval record caused a finished piece of work to be reverted 18
minutes after it landed. After the migration its canon is four notes. That
migration also first lost a dead-man alert, four open recovery gaps and the
baseline latency numbers, and missed citations by bare name; the steps below
are ordered so you do not.

Run this once per repository, then uninstall it. Afterwards the Canon block in
the instruction file keeps canon small. This skill installs no check, hook,
link checker or word budget, and recommends none.

## Mode

- `dry run`, `assess`, `audit` or `plan`: read-only. Produce the measurements,
  the disposition table and the ordered plan below. Edit nothing.
- An explicit request to migrate, slim, compact or prune: apply, in the order
  below, one reviewable commit per step. Apply needs a clean worktree.
- Follow the repository's own commit, branch and checkout rules. Never push;
  where pushing deploys, say so and leave it to the owner. Change no code
  behavior: outside `canon/` and the instruction files you touch only
  comments, links, runbooks and documentation that point into canon, except
  for removing old Canon machinery (step 3).

## Ask the owner first

1. Which canon content have you or your agents actually used? Name files.
2. Is anything to be kept without loss, such as a plan for unbuilt work?
3. Which working rules do you keep repeating to agents that are written down
   nowhere, or only in one agent's private memory?

The owner's answers outrank every heuristic below.

## Measure (read-only)

Run the bundled analyzer from this skill's directory:

```sh
python3 <this-skill-directory>/scripts/analyze_canon.py --root /path/to/repo [--days 30] [--json]
```

It reports files and words per directory, decision records, front matter and
stamp fields, the share of recent commits touching `canon/` and of canon file
touches that only bump a stamp, canon paths cited from outside `canon/`, and
the canon files the instruction files name next to "read" (a proxy for
startup reads, not a measurement). Cited paths and the owner's answers are the
evidence of value; size, age and tidiness are not.

## Decide (one row per file)

Write a disposition table outside the repository or in ignored
`canon/scratch/`: `path<TAB>action<TAB>target-or-reason`, with actions
`DELETE`, `KEEP`, `MOVE:<dest>`, `MERGE:<dest>` and `REWRITE:<dest>`. The
default is `DELETE`. A file earns another action only if a future task needs
it, getting it wrong is costly, and the code, tests and ordinary search
cannot answer it.

| Found in canon | Goes to |
| --- | --- |
| Owner working rule, often filed as a decision | the instruction file, in the owner's words |
| Operator procedure, deploy, recovery, key handling, an alert or other operating requirement | the runbook beside the tool |
| Open gap (accepted or not), measured number | a surviving note, the runbook, or a comment at the owning code |
| Single-module contract, limit, default, status code, field list | its code and tests; delete the prose |
| Why one piece of code is unusual | a short comment at that code |
| Cross-owner guarantee, accepted gap, measured dead end | a flat canon note, or a clause in one |
| Owner-approved plan for unbuilt work | a flat canon note, losing nothing decided |
| Decision record of any kind | its live rule to one of the homes above, then delete |
| Retired stack, completed migration, approval, checkpoint, session direction | delete |
| Manifest, index, overview, glossary, standards page | live lines to the instruction file; delete |

## Apply (in this order)

1. **Tag first.** Tag the starting commit (for example `canon-v1`). Cite the
   tag name and its full commit SHA in every later commit body, so each
   deleted file is one `git show canon-v1:<path>` away, and ask the owner to
   push the tag so the history survives clones.
2. **Instructions first.** Until they change, every later commit owes the old
   ceremony. Replace the canon protocol in `AGENTS.md` with the current Canon
   block; make `CLAUDE.md` import it (`@AGENTS.md`) rather than duplicate it;
   reduce any system-prompt copy to a pointer. Remove session-start reads,
   stamp duties, decision-record rules and cue-word triggers. Put the owner's
   unwritten working rules into the instruction file, each with its reason.
3. **Remove old Canon machinery.** Delete earlier compact-canon copies (or
   replace them with this one), a vendored `canon-doctor.py` or `canonlib.py`,
   a checkout of the Canon product inside `canon/`, and every hook, CI job or
   build step (`prebuild`, pre-commit) that runs them or checks stamps. Keep
   every check of the product itself.
4. **Write the survivors before deleting anything.** Write any plan the owner
   wants kept, in full, and rewrite each surviving note from the code and the
   tag, not from old summaries: no front matter, no stamps, current fact with
   its reason in a clause, naming the code or test that enforces it. Keep only
   cross-owner guarantees, gaps with their reason, measured lessons (what, the
   number, the commit) and owner-approved plans. If a survivor is over the
   core's budget (about a thousand words, twelve notes), ask the owner to set
   other numbers in the instruction file; never split or truncate it. Flatten
   `canon/`; git-ignore `canon/scratch/`.
5. **Move runbooks and live requirements beside their tools.** Operating,
   deploy and recovery procedures move verbatim next to the tooling they
   drive: strip front matter, fix every link inside the moved text, change no
   meaning. Add only what the destination does not already say.
6. **Repoint citations.** `git grep -n "canon/" -- ':!canon'` is not enough.
   Also grep every file you will delete by its basename stem and its slug
   (decision IDs are often cited bare), and the section titles of deleted
   documents as they are cited ("handoff §6.3"). Point each hit at the live
   home, or drop it where the citing sentence already states the rule. A dead
   pointer is worse than none. A dated data artifact may keep an old path only
   if it names the tag.
7. **Delete decision records after moving still-live rules.** For each record,
   ask whether a rule in it still governs work. If so, move that one rule to
   its home as one clause. Rejected alternatives and history stay in git. Do
   not build a register, a decision index or an archive directory. "Immutable"
   records go too.
8. **Delete specs that copy code, and nothing else with them.** Per-feature
   specifications, inventories, limits, defaults and file maps go; the code
   and tests are the record. Never delete the only statement of an operating
   requirement (an alert, a stop condition, a recovery step), an open gap,
   accepted or not, or a measurement that code and tests do not hold. Move it
   first, to a runbook, a comment at the owning code or a surviving note, and
   delete the file only when each such sentence has a home or the owner
   accepts losing it. If a spec states behavior no test covers, report it as a
   test gap.
9. **Review against the tag.** Read every deleted file at the tag, in a fresh
   session or with a second reviewer, looking for operating requirements, open
   gaps and measurements that found no home. Check every row of the
   disposition table, every item the owner asked to keep, every live rule from
   a deleted record, and every link inside moved files. Run the repository's
   own checks. Re-run the analyzer for the before/after numbers.

Never guess a rule, limit or reason to fill a gap; report the gap.

## Verify and report

- `ls canon/` shows flat notes within the budget (twelve of about a thousand
  words, or the owner's numbers in the instruction file), no `decisions/`, no
  manifest.
- No front matter, stamps or status fields remain.
- `git grep "canon/"` outside `canon/` finds only paths that exist, and no
  deleted file's stem, slug or cited section title is still referenced.
- Every link inside a moved file resolves.
- No instruction file asks for a canon read at session start, and no hook,
  CI job or build step runs old Canon tooling.

Report files and words before and after, startup reads before and after, what
moved where, what the owner asked to keep and where it is, references
repointed, unresolved gaps, the tag with its full SHA and the command that
recovers a deleted file, and the commits. Then tell the owner the skill can be uninstalled.
