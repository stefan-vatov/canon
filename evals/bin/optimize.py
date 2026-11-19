#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""Hill-climbing optimizer for the Canon guidance file.

Loop: evaluate the current best guidance, feed the observed failures to an
improver LLM that proposes a revised guidance file, evaluate the candidate,
keep it only if the combined score beats the best by at least --min-delta.

usage:
  optimize.py --scenarios 01-bootstrap,02-feature,03-drift \
              --harness codex --runs 3 --iterations 5 \
              [--guidance ../canon-core.md] [--no-judge] [--min-delta 0.02]

env:
  IMPROVER_CMD  required command reading the improver prompt on stdin and
                printing revised guidance on stdout
  EVAL_MODEL    pin the agent model (forwarded to adapters)
  JUDGE_CMD     judge invocation (forwarded to judge.sh)

Anti-cheating: candidates that mention fixture-specific terms are rejected;
an optimizer tuning against known evals would otherwise encode the answers.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

EVALS = Path(__file__).resolve().parent.parent
ROOT = EVALS.parent

# Terms that only exist in eval fixtures; their presence in a candidate means
# the improver encoded eval answers instead of general guidance.
LEAK_TERMS = [
    "wordstats", "top_words", "payments", "refund", "amount_cents",
    "fetch_with_retry", "MAX_RETRIES", "ConnectionError", "ledger",
    "promo", "campaign", "quantity_discount", "format_cents",
    "apply_promo", "validate_promo", "order_total", "discount",
    "create_note", "note_validation", "validate_note_text", "MAX_NOTE_LENGTH",
    "format_timestamp", "set_stock", "stock_level", "sku", "oversell",
    "apply_platform_fee", "platform fee", "250 bps", "billingcore",
    "within_refund_window", "refund window", "REFUND_WINDOW",
    "default_page_size", "clamp_page_size", "DEFAULT_PAGE_SIZE", "page size",
    "support-tickets", "support tickets", "export_rows", "include_archived",
    "archived", "sweeper", "is_expired", "timeout_minutes", "slugify",
    "textutil", "restock", "invoices", "old-importer", "pagination",
]


# The owner's invariants. A candidate must keep each clause verbatim
# (whitespace-normalized); the optimizer may tune everything else. Whole
# normative clauses are listed so that flipping "Must not" to "Must", or
# dropping one item from a list, is caught.
OWNER_INVARIANTS = [
    "read nothing in `canon/` at session start",
    "Nothing in Canon outranks what the owner says now: say once that a note "
    "disagrees, do what was asked, and fix or delete the note in the same change.",
    "Only the owner's words make a rule.",
    'Never record your own choices, plans or process as "must" or "never".',
    "Decisions get no records. No `decisions/` directory, decision log, register or ADR.",
    "**Must**, in the same change: fix or delete every Canon sentence your change "
    "makes false; update a note when a guarantee, contract or accepted gap it "
    "states changes.",
    "**Must not**: edit Canon because nearby code changed (moves, renames, "
    "refactors and repeats of a pattern oblige nothing); create a note without "
    "the owner's approval; add front matter, status fields, `sources`/`verified` "
    "stamps, review dates, an index or a manifest; copy what code holds (limits, "
    "defaults, status codes, field lists, file or test inventories); write "
    "changelogs, progress, approvals or handovers anywhere but scratch; cite "
    "Canon to refuse or delay the owner.",
    "Canon stays small by rule, not by tooling.",
    "At the limit, add a note only by removing or merging one. Never split a "
    "note to fit the budget.",
    "Nothing in Canon is immutable; git is the history",
]

# Wording that restores a rule the owner retired. It is searched in the
# candidate's whitespace-flattened text after the invariant clauses above are
# removed, so line wraps cannot hide it and the invariants' own "no ADR" or
# "never split" wording cannot trip it. This screens common wordings only; a
# maintainer still applies the veto to every candidate before adoption.
RETIRED_RULES = [
    (r"\bread (?:every|all|each) (?:canon |of the )?(?:notes?|pages?|files?)\b",
     "mandatory reads of every note"),
    (r"\b(?:cat|read|load|open)\b[^.]{0,30}`?canon/\*", "bulk Canon reads"),
    (r"\bload (?:all|every|the whole)(?: of)? `?canon", "bulk Canon reads"),
    (r"\b(?:first|before (?:any|you|starting|work))\b[^.]{0,60}\b(?:read|load|open)\b[^.]{0,40}canon/",
     "an up-front Canon read"),
    (r"canon/(?:manifest|index|overview|glossary|decisions)\.md", "a manifest, index or register"),
    (r"\bADRs?\b", "ADRs"),
    (r"\bdecision (?:records?|registers?|logs?|entr(?:y|ies))\b", "decision records"),
    (r"\brecord (?:each|every|the|a|your) decisions?\b", "decision records"),
    (r"\bsupersed", "supersession records"),
    (r"\blast[ -]verified\b|\bverified[ -]stamps?\b|\breview[ -]by\b", "freshness stamps"),
    (r"\b(?:split|break)\b[^.]{0,30}\binto\b", "splitting notes"),
    (r"canon-doctor|\bpre-commit\b[^.]{0,40}\bcanon\b|\bci\b[^.]{0,40}\b(?:canon|must fail|fails?)\b",
     "a Canon gate or checker"),
    (r"\b(?:run|wire|add)\b[^.]{0,30}\b(?:checker|linter|doctor|validator|gate)\b",
     "a Canon gate or checker"),
    (r"\brules? (?:that )?an? agents? (?:writes?|wrote|records?)\b[^.]{0,20}\bbind",
     "agent-authored rules binding agents"),
    (r"\bagent-(?:written|authored) (?:rules?|briefs?)\b[^.]{0,30}\b(?:bind|binding|apply)",
     "agent-authored rules binding agents"),
]
FRONT_MATTER = re.compile(r"(?m)^\s*(?:sources|verified|status|scope|validation)\s*:")


def normalized(text):
    return " ".join(text.split())


def run_eval(guidance, scenario, harness, runs, judge):
    cmd = [
        str(EVALS / "bin" / "run-eval.sh"),
        "--scenario", scenario, "--harness", harness,
        "--runs", str(runs), "--guidance", str(guidance),
    ]
    if not judge:
        cmd.append("--no-judge")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"run-eval.sh failed for {scenario}:\n{proc.stderr[-1000:]}")
    match = re.search(r"^results: (.+)$", proc.stdout, re.M)
    if not match:
        raise RuntimeError(f"run-eval.sh produced no results dir for {scenario}:\n{proc.stderr[-1000:]}")
    return Path(match.group(1).strip())


def combined_score(result_dir):
    summary = json.loads((result_dir / "summary.json").read_text())
    if not summary.get("complete"):
        raise RuntimeError(f"incomplete eval result: {result_dir}")
    if not summary.get("pass_all_required"):
        raise RuntimeError(f"eval failed a required integrity/correctness gate: {result_dir}")
    parts = [v for v in (summary.get("mechanical_mean"), summary.get("judge_mean"))
             if v is not None]
    return sum(parts) / len(parts) if parts else 0.0


def gather_failures(result_dirs):
    """Deduplicated failure descriptions across all scenarios' runs."""
    lines = []
    for result_dir in result_dirs:
        scenario = result_dir.name.split("-", 3)[-1]
        for run in sorted(result_dir.glob("run-*")):
            for check_file in sorted(run.glob("checks*.json")):
                checks = load_json(check_file)
                if not checks:
                    continue
                step = check_file.stem[len("checks-"):] if check_file.stem != "checks" else ""
                label = f"{scenario}/{step}" if step else scenario
                for c in checks["checks"]:
                    if c.get("outcome") != "unsupported" and not c["pass"]:
                        lines.append(f"[{label}] check '{c['id']}': {c['detail'] or 'failed'}")
            judge = load_json(run / "judge.json")
            if judge:
                for c in judge.get("criteria", []):
                    if c.get("score") == 0:
                        lines.append(f"[{scenario}] judge '{c['id']}': {c.get('reason', '')}")
                if judge.get("notes"):
                    lines.append(f"[{scenario}] judge note: {judge['notes']}")
    seen, out = set(), []
    for line in lines:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return out


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def evaluate(guidance, scenarios, harness, runs, judge):
    dirs = [run_eval(guidance, s, harness, runs, judge) for s in scenarios]
    scores = {d.name: combined_score(d) for d in dirs}
    mean = sum(scores.values()) / len(scores)
    return mean, dirs, scores


def propose(improver_cmd, guidance_text, failures, score):
    prompt = "\n".join([
        (EVALS / "judge" / "improver-prompt.md").read_text(),
        "## Sentences to keep verbatim",
        "\n".join(f"- {sentence}" for sentence in OWNER_INVARIANTS),
        "## Current guidance file", guidance_text,
        "## Current combined score", f"{score:.3f}",
        "## Observed failures",
        "\n".join(f"- {f}" for f in failures) or "(none — tighten and shorten instead)",
    ])
    proc = subprocess.run(improver_cmd, shell=True, input=prompt,
                          capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        detail = proc.stderr.strip()[-1000:] or "no error output"
        raise RuntimeError(
            f"improver command failed with exit code {proc.returncode}: {detail}"
        )
    text = proc.stdout.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[^\n]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    return text.strip() + "\n"


def candidate_problems(text):
    problems = []
    leaks = [t for t in LEAK_TERMS if re.search(rf"\b{re.escape(t)}\b", text)]
    if leaks:
        problems.append(f"leaked fixture terms: {', '.join(leaks)}")
    lines = len(text.splitlines())
    if lines < 30:
        problems.append(f"suspiciously short ({lines} lines)")
    if lines > 200:
        problems.append(f"too long ({lines} lines)")
    words = len(text.split())
    if words > 800:
        problems.append(f"too long ({words} words)")
    if "canon/" not in text:
        problems.append("does not mention canon/")
    flat = normalized(text)
    remainder = flat
    for sentence in sorted(OWNER_INVARIANTS, key=len, reverse=True):
        clause = normalized(sentence)
        if clause not in flat:
            problems.append(f"drops owner invariant: {sentence[:80]}")
        remainder = remainder.replace(clause, " ")
    for pattern, rule in RETIRED_RULES:
        if re.search(pattern, remainder, re.IGNORECASE):
            problems.append(f"restores retired rule: {rule}")
    if FRONT_MATTER.search(text):
        problems.append("restores retired rule: front matter or stamps")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", required=True,
                    help="comma-separated scenario names")
    ap.add_argument("--harness", default="codex")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--iterations", type=int, default=3)
    ap.add_argument("--guidance", default=str(ROOT / "canon-core.md"))
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--min-delta", type=float, default=0.02,
                    help="candidate must beat best by at least this much")
    ap.add_argument("--improver-cmd", default=None,
                    help="overrides the required IMPROVER_CMD env")
    args = ap.parse_args()

    import os
    improver_cmd = args.improver_cmd or os.environ.get("IMPROVER_CMD")
    if not improver_cmd:
        ap.error("set IMPROVER_CMD or pass --improver-cmd")
    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    judge = not args.no_judge

    opt_dir = EVALS / "results" / f"opt-{time.strftime('%Y%m%d-%H%M%S')}"
    opt_dir.mkdir(parents=True)
    history = []

    best_text = Path(args.guidance).read_text()
    (opt_dir / "iter-0-baseline.md").write_text(best_text)
    print(f"== baseline: evaluating {args.guidance} on {scenarios} "
          f"({args.runs} run(s) each, {args.harness}) ==")
    best_score, best_dirs, per = evaluate(opt_dir / "iter-0-baseline.md",
                                          scenarios, args.harness, args.runs, judge)
    print(f"== baseline combined score: {best_score:.3f} {per} ==")
    history.append({"iteration": 0, "kind": "baseline", "score": best_score,
                    "per_scenario": per, "kept": True})

    for i in range(1, args.iterations + 1):
        failures = gather_failures(best_dirs)
        print(f"\n== iteration {i}: proposing (against {len(failures)} failure signals) ==")
        try:
            candidate_text = propose(improver_cmd, best_text, failures, best_score)
        except RuntimeError as exc:
            print(f"== iteration {i}: PROPOSAL FAILED: {exc} ==")
            history.append({"iteration": i, "kind": "proposal_failed",
                            "error": str(exc), "kept": False})
            continue
        candidate_path = opt_dir / f"iter-{i}-candidate.md"
        candidate_path.write_text(candidate_text)

        problems = candidate_problems(candidate_text)
        if problems:
            print(f"== iteration {i}: REJECTED before eval: {'; '.join(problems)} ==")
            history.append({"iteration": i, "kind": "rejected",
                            "problems": problems, "kept": False})
            continue

        try:
            score, dirs, per = evaluate(candidate_path, scenarios,
                                        args.harness, args.runs, judge)
        except RuntimeError as exc:
            print(f"== iteration {i}: REJECTED after eval: {exc} ==")
            history.append({"iteration": i, "kind": "rejected",
                            "stage": "evaluation", "error": str(exc),
                            "kept": False})
            continue
        kept = score >= best_score + args.min_delta
        print(f"== iteration {i}: score {score:.3f} vs best {best_score:.3f} "
              f"-> {'KEPT' if kept else 'discarded'} ==")
        history.append({"iteration": i, "kind": "candidate", "score": score,
                        "per_scenario": per, "kept": kept})
        if kept:
            best_text, best_score, best_dirs = candidate_text, score, dirs

    (opt_dir / "best.md").write_text(best_text)
    (opt_dir / "history.json").write_text(json.dumps(history, indent=2) + "\n")
    print(f"\nbest combined score: {best_score:.3f}")
    print(f"best guidance: {opt_dir / 'best.md'}")
    print(f"history:       {opt_dir / 'history.json'}")
    if best_text != Path(args.guidance).read_text():
        print(f"\nReview the diff before adopting:\n"
              f"  diff {args.guidance} {opt_dir / 'best.md'}")
    else:
        print("\nNo candidate beat the baseline; shipped guidance unchanged.")


if __name__ == "__main__":
    main()
