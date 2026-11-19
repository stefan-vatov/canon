---
name: compact-canon
description: One-time migration that slims an overgrown or legacy Project Canon (`canon/`) to a handful of flat notes. Use when a repository's canon has decision records, `sources`/`verified` or `status` front matter, a manifest, per-feature specs or mandatory session-start reads, or when asked to slim, compact, prune, migrate or assess what a canon costs. A dry run changes nothing. Not for routine upkeep, which the installed Canon block already covers.
---

# Compact Canon

Take a canon that grew into a second codebase and leave what the current Canon
block allows: at most twelve flat notes holding what code, tests and git cannot
say. Most of what you find goes; git keeps all of it.

This skill was written from a real migration. One adopter ran the older rules
for 30 days: 640 commits, 384 canon files, 200k words, 271 decision records.
Canon was touched in 488 of 639 commits, about half of all canon file touches
were `verified:` bumps, agents read about 23k tokens before any code, and an
"immutable" approval record caused a finished piece of work to be reverted 18
minutes after it landed. After the migration its canon is four notes.

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
  comments, links and documentation that point into canon.

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
the canon files the instruction files tell an agent to read. Cited paths and
the owner's answers are the evidence of value; size, age and tidiness are not.

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
| Operator procedure, deploy, recovery, key handling | the runbook beside the tool |
| Single-module contract, limit, default, status code, field list | its code and tests; delete the prose |
| Why one piece of code is unusual | a short comment at that code |
| Cross-owner guarantee, accepted gap, measured dead end | a flat canon note, or a clause in one |
| Owner-approved plan for unbuilt work | a flat canon note, losing nothing decided |
| Decision record of any kind | its live rule to one of the homes above, then delete |
| Retired stack, completed migration, approval, checkpoint, session direction | delete |
| Manifest, index, overview, glossary, standards page | live lines to the instruction file; delete |

## Apply (in this order)

1. **Tag first.** Tag the starting commit (for example `canon-v1`) and cite it
   in every later commit body, so each deleted file is one
   `git show canon-v1:<path>` away.
2. **Instructions first.** Until they change, every later commit owes the old
   ceremony. Replace the canon protocol in `AGENTS.md` with the current Canon
   block; make `CLAUDE.md` import it (`@AGENTS.md`) rather than duplicate it;
   reduce any system-prompt copy to a pointer. Remove session-start reads,
   stamp duties, decision-record rules and cue-word triggers. Put the owner's
   unwritten working rules into the instruction file, each with its reason.
3. **Move runbooks beside their tools.** Operating, deploy and recovery
   procedures move verbatim next to the tooling they drive: strip front
   matter, fix links, change no meaning. Add only what the destination does
   not already say.
4. **Repoint citations.** Find every inbound reference with
   `git grep -n "canon/" -- ':!canon'`. Point it at the live home, or drop it
   where the citing sentence already states the rule. A dead pointer is worse
   than none. A dated data artifact may keep an old path only if it names the
   tag.
5. **Delete decision records after moving still-live rules.** For each record,
   ask whether a rule in it still governs work. If so, move that one rule to
   its home as one clause. Rejected alternatives and history stay in git. Do
   not build a register, a decision index or an archive directory. "Immutable"
   records go too.
6. **Delete specs that copy code.** Per-feature specifications, inventories,
   limits, defaults and file maps go; the code and tests are the record. If a
   spec states behavior no test covers, report it as a test gap instead of
   keeping the prose.
7. **Keep only** cross-owner guarantees, accepted gaps with their reason,
   measured lessons (what, the number, the commit) and owner-approved plans.
   Write any preserved plan in full before deleting its sources. Rewrite each
   survivor from the code and the tag, not from old summaries: no front
   matter, no stamps, current fact with its reason in a clause, naming the
   code or test that enforces it. Flatten `canon/`; git-ignore `canon/scratch/`.
8. **Review against the tag.** Check every row of the disposition table, every
   item the owner asked to keep, and every live rule from a deleted record
   against `canon-v1`, and confirm each landed in its new home. Run the
   repository's own checks. Re-run the analyzer for the before/after numbers.

Never guess a rule, limit or reason to fill a gap; report the gap.

## Verify and report

- `ls canon/` shows at most twelve flat notes, no `decisions/`, no manifest.
- No front matter, stamps or status fields remain.
- `git grep "canon/"` outside `canon/` finds only paths that exist.
- No instruction file asks for a canon read at session start.

Report files and words before and after, startup reads before and after, what
moved where, what the owner asked to keep and where it is, references
repointed, unresolved gaps, the tag and the command that recovers a deleted
file, and the commits. Then tell the owner the skill can be uninstalled.
