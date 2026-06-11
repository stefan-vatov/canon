#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""canon doctor: mechanical health checks for a canon/ directory.

usage: canon-doctor.py [--root DIR] [--json]

Checks (error -> exit 1, warn -> reported only):

  structure        required core files exist                          error
  manifest         every permanent Canon file is referenced, and      error
                   every manifest link resolves to a real file
  line-caps        permanent files stay under 250 lines               error
  scratch-ignored  canon/scratch/ is git-ignored                      error
  changelog-smell  dates / "previously" / "added" phrasing in         warn
                   permanent files (current-state rule)
  staleness        domain files whose frontmatter `sources` changed   warn
                   since their `verified` commit, or domain files
                   missing frontmatter entirely

Designed for CI or pre-commit in any repo that carries a Canon.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REQUIRED = ["overview.md", "glossary.md", "standards.md", "manifest.md"]
MAX_LINES = 250
CHANGELOG_RE = re.compile(r"(?i)\bpreviously\b|\b20\d\d-\d\d-\d\d\b|\bwe (?:added|changed|removed)\b")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def git(root, *args):
    proc = subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip()


def permanent_files(canon):
    return sorted(p for p in canon.rglob("*.md")
                  if "scratch" not in p.relative_to(canon).parts)


def parse_frontmatter(text):
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    fm = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            fm[key.strip()] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        else:
            fm[key.strip()] = value
    return fm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    canon = root / "canon"
    findings = []

    def add(check, severity, detail):
        findings.append({"check": check, "severity": severity, "detail": detail})

    if not canon.is_dir():
        add("structure", "error", "no canon/ directory")
        return report(findings, args.json)

    for name in REQUIRED:
        if not (canon / name).is_file():
            add("structure", "error", f"missing canon/{name}")

    files = permanent_files(canon)
    manifest = canon / "manifest.md"
    if manifest.is_file():
        text = manifest.read_text()
        for p in files:
            rel = str(p.relative_to(canon))
            if p != manifest and rel not in text and p.name not in text:
                add("manifest", "error", f"{rel} not referenced in manifest.md")
        for link in re.findall(r"\]\(([^)#]+)\)", text):
            if not link.startswith(("http://", "https://")) \
                    and not (canon / link).exists():
                add("manifest", "error", f"manifest links to missing file: {link}")

    for p in files:
        body = p.read_text(errors="replace")
        rel = str(p.relative_to(canon))
        n = len(body.splitlines())
        if n > MAX_LINES:
            add("line-caps", "error", f"{rel} has {n} lines (max {MAX_LINES})")
        content = FRONTMATTER_RE.sub("", body)
        for hit in set(CHANGELOG_RE.findall(content)):
            add("changelog-smell", "warn", f"{rel} contains changelog-style text: {hit!r}")

    rc, _ = git(root, "rev-parse", "--git-dir")
    in_git = rc == 0
    if in_git:
        rc, _ = git(root, "check-ignore", "-q", str(canon / "scratch" / "x"))
        if rc != 0:
            add("scratch-ignored", "error", "canon/scratch/ is not git-ignored")

    # Staleness: domain files (anything outside the four core files) should
    # carry frontmatter; if sources changed since `verified`, flag.
    core_names = set(REQUIRED)
    for p in files:
        rel_parts = p.relative_to(canon).parts
        is_domain = len(rel_parts) > 1 and rel_parts[0] not in ("decisions", "plans")
        if not is_domain:
            continue
        rel = str(p.relative_to(canon))
        fm = parse_frontmatter(p.read_text(errors="replace"))
        if not fm or "sources" not in fm or "verified" not in fm:
            add("staleness", "warn", f"{rel} has no sources/verified frontmatter")
            continue
        if not in_git:
            continue
        verified = fm["verified"]
        rc, _ = git(root, "cat-file", "-e", f"{verified}^{{commit}}")
        if rc != 0:
            add("staleness", "warn", f"{rel}: verified commit {verified!r} not found")
            continue
        sources = fm["sources"] if isinstance(fm["sources"], list) else [fm["sources"]]
        rc, out = git(root, "log", "--oneline", f"{verified}..HEAD", "--", *sources)
        if rc == 0 and out:
            changed = out.splitlines()
            add("staleness", "warn",
                f"{rel} is stale: {len(changed)} commit(s) touched "
                f"{', '.join(sources)} since {verified}")

    return report(findings, args.json)


def report(findings, as_json):
    errors = [f for f in findings if f["severity"] == "error"]
    if as_json:
        print(json.dumps({"ok": not errors, "findings": findings}, indent=2))
    else:
        if not findings:
            print("canon doctor: all checks passed")
        for f in findings:
            print(f"[{f['severity']}] {f['check']}: {f['detail']}")
        if findings:
            print(f"canon doctor: {len(errors)} error(s), "
                  f"{len(findings) - len(errors)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
