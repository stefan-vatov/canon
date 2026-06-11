#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""Aggregate checks.json and judge.json across the runs of one result dir.

usage: summarize.py RESULTS_DIR [RESULTS_DIR ...]

Pass several result dirs to compare guidance variants side by side.
"""
import json
import sys
from pathlib import Path


def load(path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def summarize(result_dir):
    result_dir = Path(result_dir)
    runs = sorted(p for p in result_dir.glob("run-*") if p.is_dir())
    rows, failed_checks, judge_notes = [], {}, []

    for run in runs:
        # A run has one checks.json (single-session) or several
        # checks-<step>.json plus a final checks.json (multi-session chain).
        all_checks = []
        for path in sorted(run.glob("checks*.json")):
            data = load(path)
            if data:
                step = path.stem.replace("checks-", "") if "-" in path.stem else "final"
                all_checks.extend((step, c) for c in data["checks"])
        judge = load(run / "judge.json")
        n_pass = sum(1 for _, c in all_checks if c["pass"])
        mech = round(n_pass / len(all_checks), 3) if all_checks else None
        jscore = judge.get("judge_score") if judge else None
        rows.append((run.name, mech, jscore))
        for step, c in all_checks:
            if not c["pass"]:
                check_id = c["id"] if step == "final" else f"{step}:{c['id']}"
                failed_checks.setdefault(check_id, []).append(run.name)
        if judge:
            for c in judge.get("criteria", []):
                if c.get("score") == 0:
                    failed_checks.setdefault(f"judge:{c['id']}", []).append(run.name)
            if judge.get("notes"):
                judge_notes.append(f"{run.name}: {judge['notes']}")

    mechs = [m for _, m, _ in rows if m is not None]
    judges = [j for _, _, j in rows if j is not None]
    summary = {
        "result_dir": str(result_dir),
        "runs": len(rows),
        "mechanical_mean": round(sum(mechs) / len(mechs), 3) if mechs else None,
        "judge_mean": round(sum(judges) / len(judges), 3) if judges else None,
        "failed": {k: v for k, v in sorted(failed_checks.items())},
    }
    (result_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    print(f"\n=== {result_dir.name} ===")
    print(f"{'run':<10} {'mechanical':>11} {'judge':>7}")
    for name, mech, jscore in rows:
        print(f"{name:<10} {fmt(mech):>11} {fmt(jscore):>7}")
    print(f"{'mean':<10} {fmt(summary['mechanical_mean']):>11} {fmt(summary['judge_mean']):>7}")
    if failed_checks:
        print("failing checks (check -> runs):")
        for check_id, in_runs in sorted(failed_checks.items()):
            print(f"  {check_id}: {', '.join(in_runs)}")
    for note in judge_notes:
        print(f"note  {note}")
    return summary


def fmt(x):
    return "-" if x is None else f"{x:.2f}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: summarize.py RESULTS_DIR [RESULTS_DIR ...]")
    for d in sys.argv[1:]:
        summarize(d)
