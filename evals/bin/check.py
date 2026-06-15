#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""Mechanical checks for a completed eval run.

Reads the scenario's expected.json and the post-run workspace, emits
checks.json with one pass/fail entry per check. Checks:

  required_files        files that must exist after the run
  manifest_complete     every permanent canon/*.md is referenced in manifest.md
  canon_line_limits     permanent canon files stay under max_canon_lines
  tests_pass            the fixture's test_cmd exits 0
  diff_scope            every changed file matches allowed_change_globs
  rules                 per-scenario content rules (must_regex / forbid_regex)
  holdout_pass          hidden tests the agent never saw, copied in from the
                        scenario dir at scoring time, run, then removed; they
                        encode requirements stated in earlier sessions
"""
import argparse
import fnmatch
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def git(workdir, *args):
    return subprocess.run(
        ["git", "-C", str(workdir), *args],
        capture_output=True, text=True, check=True,
    ).stdout


def changed_files(workdir):
    subprocess.run(["git", "-C", str(workdir), "add", "-A"],
                   capture_output=True, check=True)
    out = git(workdir, "diff", "--cached", "--name-only", "HEAD")
    return [line for line in out.splitlines() if line.strip()]


def permanent_canon_files(workdir):
    canon = workdir / "canon"
    if not canon.is_dir():
        return []
    return sorted(
        p for p in canon.rglob("*.md")
        if "scratch" not in p.relative_to(canon).parts
    )


def matching_files(workdir, glob):
    return sorted(
        p for p in workdir.rglob("*")
        if p.is_file()
        and ".git" not in p.relative_to(workdir).parts
        and fnmatch.fnmatch(str(p.relative_to(workdir)), glob)
    )


def canon_reads_from_transcripts(transcript_dir):
    """Ordered list of canon/* paths the agent opened, parsed from any
    stream-json transcripts in transcript_dir. Returns [] for plain-text
    (e.g. codex) transcripts, where per-tool file paths are not structured."""
    reads = []
    tdir = Path(transcript_dir)
    if not tdir.is_dir():
        return reads
    for tf in sorted(tdir.glob("transcript*.txt")):
        for raw in tf.read_text(errors="replace").splitlines():
            raw = raw.strip()
            if not raw.startswith("{") or '"tool_use"' not in raw:
                continue
            try:
                e = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if e.get("type") != "assistant":
                continue
            for b in e.get("message", {}).get("content", []):
                if b.get("type") == "tool_use" and b.get("name") == "Read":
                    fp = b.get("input", {}).get("file_path", "")
                    idx = fp.find("canon/")
                    if idx >= 0:
                        reads.append(fp[idx:])
    return reads


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--expected", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--transcript-dir", default=None,
                    help="dir holding transcript*.txt, for routing checks")
    args = ap.parse_args()

    work = Path(args.workdir).resolve()
    expected_path = Path(args.expected).resolve()
    expected = json.loads(expected_path.read_text())
    changed = changed_files(work)
    checks = []

    def add(check_id, ok, detail=""):
        checks.append({"id": check_id, "pass": bool(ok), "detail": detail})

    for rel in expected.get("required_files", []):
        add(f"required:{rel}", (work / rel).is_file(), "missing" if not (work / rel).is_file() else "")

    canon_files = permanent_canon_files(work)
    manifest = work / "canon" / "manifest.md"
    if manifest.is_file():
        text = manifest.read_text()
        missing = [
            str(p.relative_to(work / "canon"))
            for p in canon_files
            if p != manifest
            and str(p.relative_to(work / "canon")) not in text
            and p.name not in text
        ]
        add("manifest_complete", not missing,
            f"not referenced: {', '.join(missing)}" if missing else "")
    elif (work / "canon").is_dir():
        add("manifest_complete", False, "canon/ exists but manifest.md missing")

    max_lines = expected.get("max_canon_lines", 250)
    too_long = [
        f"{p.relative_to(work)} ({n})"
        for p in canon_files
        if (n := len(p.read_text().splitlines())) > max_lines
    ]
    if canon_files:
        add("canon_line_limits", not too_long, ", ".join(too_long))

    test_cmd = expected.get("test_cmd")
    if test_cmd:
        try:
            proc = subprocess.run(test_cmd, shell=True, cwd=work,
                                  capture_output=True, text=True, timeout=300)
            add("tests_pass", proc.returncode == 0,
                "" if proc.returncode == 0 else (proc.stderr or proc.stdout)[-500:])
        except subprocess.TimeoutExpired:
            add("tests_pass", False, "test_cmd timed out")

    globs = expected.get("allowed_change_globs")
    if globs:
        out_of_scope = [
            f for f in changed
            if not any(fnmatch.fnmatch(f, g) for g in globs)
        ]
        add("diff_scope", not out_of_scope, ", ".join(out_of_scope))

    for rule in expected.get("rules", []):
        files = matching_files(work, rule["glob"])
        contents = {p: p.read_text(errors="replace") for p in files}
        ok, detail = True, ""
        if rule.get("must_regex"):
            ok = any(re.search(rule["must_regex"], c) for c in contents.values())
            if not ok:
                detail = f"no file matching {rule['glob']} contains /{rule['must_regex']}/"
        if ok and rule.get("forbid_regex"):
            hits = [str(p.relative_to(work)) for p, c in contents.items()
                    if re.search(rule["forbid_regex"], c)]
            ok = not hits
            detail = f"/{rule['forbid_regex']}/ found in: {', '.join(hits)}" if hits else ""
        add(f"rule:{rule['id']}", ok, detail or rule.get("description", ""))

    # Routing precision: did the agent read the right Canon doc and avoid
    # bulk-loading sibling domains? Isolates retrieval/routing from
    # correctness (LongMemEval Oracle idea). Only scorable with a structured
    # (claude stream-json) transcript; skipped otherwise so codex runs don't
    # fail spuriously.
    routing = expected.get("routing")
    if routing and args.transcript_dir:
        reads = canon_reads_from_transcripts(args.transcript_dir)
        if not reads:
            add("routing_precision", True,
                "no structured transcript reads (non-claude harness); skipped")
        else:
            domain_glob = routing.get("domain_glob", "canon/*/overview.md")
            domain_reads = sorted({r for r in reads if fnmatch.fnmatch(r, domain_glob)})
            must = routing.get("must_read", [])
            missing = [m for m in must if not any(r.endswith(m) or m in r for r in reads)]
            max_domains = routing.get("max_domain_reads", 2)
            ok = not missing and len(domain_reads) <= max_domains
            detail = ""
            if missing:
                detail = f"never read required: {', '.join(missing)}"
            elif len(domain_reads) > max_domains:
                detail = (f"bulk-loaded {len(domain_reads)} domain docs "
                          f"(max {max_domains}): {', '.join(domain_reads)}")
            add("routing_precision", ok, detail)

    holdout = expected.get("holdout")
    if holdout:
        src = expected_path.parent / holdout["dir"]
        copied = []
        try:
            for f in sorted(p for p in src.rglob("*") if p.is_file()):
                dest = work / f.relative_to(src)
                if dest.exists():
                    add("holdout_pass", False,
                        f"workspace already has {dest.relative_to(work)}; "
                        "holdout would clobber agent files")
                    break
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                copied.append(dest)
            else:
                try:
                    proc = subprocess.run(holdout["test_cmd"], shell=True,
                                          cwd=work, capture_output=True,
                                          text=True, timeout=300)
                    add("holdout_pass", proc.returncode == 0,
                        "" if proc.returncode == 0
                        else (proc.stderr or proc.stdout)[-500:])
                except subprocess.TimeoutExpired:
                    add("holdout_pass", False, "holdout test_cmd timed out")
        finally:
            # The agent must never find holdout tests in a later session.
            for dest in copied:
                dest.unlink(missing_ok=True)

    passed = sum(1 for c in checks if c["pass"])
    result = {
        "passed": passed,
        "total": len(checks),
        "score": round(passed / len(checks), 3) if checks else None,
        "checks": checks,
    }
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    print(f"mechanical: {passed}/{len(checks)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
