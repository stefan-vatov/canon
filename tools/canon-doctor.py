#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""canon doctor: mechanical health checks for a canon/ directory.

usage: canon-doctor.py [--root DIR] [--json] [--strict]

Checks (error -> exit 1, warn -> reported only):

  structure        required core files exist                          error
  manifest         every permanent Canon file is referenced, and      error
                   every manifest link resolves to a real file
  line-caps        permanent files stay under 250 lines               error
  scratch-ignored  canon/scratch/ is git-ignored                      error
  changelog-smell  dates / "previously" / "added" phrasing in         warn
                   current-state files (immutable decisions exempt)
  staleness        dirty, missing, indeterminate, or committed source warn
                   changes newer than the latest domain-file refresh

Designed for CI or pre-commit in any repo that carries a Canon.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from canonlib import (
    contained_regular_file,
    manifest_route_issues,
    missing_manifest_routes,
)

REQUIRED = ["overview.md", "glossary.md", "standards.md", "manifest.md"]
MAX_LINES = 250
MAX_BYTES = 64 * 1024
CHANGELOG_RE = re.compile(r"(?i)\bpreviously\b|\b20\d\d-\d\d-\d\d\b|\bwe (?:added|changed|removed)\b")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
FRONTMATTER_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
PLAIN_STRING_RE = re.compile(r'''[A-Za-z0-9._/][^\s\[\]{},#&*!|>"`\\]*''')
IMPLICIT_NON_STRING_RE = re.compile(
    r"(?ix)(?:"
    r"null|~|true|false|yes|no|on|off|"
    r"[-+]?(?:0b[01_]+|0o[0-7_]+|0x[0-9a-f_]+|[0-9][0-9_]*"
    r"(?:\.[0-9_]*)?(?:e[-+]?[0-9]+)?|\.[0-9_]+(?:e[-+]?[0-9]+)?)|"
    r"[-+]?\.(?:inf|nan)|"
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[tT ]\S+)?"
    r")"
)
FULL_COMMIT_ID_RE = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")


def git(root, *args):
    try:
        proc = subprocess.run(["git", "-C", str(root), *args],
                              capture_output=True, text=True)
    except OSError as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def permanent_files(canon):
    return sorted(p for p in canon.rglob("*.md")
                  if "scratch" not in p.relative_to(canon).parts)


def strip_yaml_comment(value):
    quote = None
    escaped = False
    skip_next = False
    for index, char in enumerate(value):
        if skip_next:
            skip_next = False
            continue
        if escaped:
            escaped = False
            continue
        if quote == '"' and char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                if quote == "'" and index + 1 < len(value) and value[index + 1] == "'":
                    skip_next = True
                    continue
                quote = None
            continue
        prefix = value[:index].rstrip()
        if char in "'\"" and (not prefix or prefix.endswith(("[", ","))):
            quote = char
        elif char == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return None if quote or escaped else value.rstrip()


def parse_yaml_scalar(raw, *, allow_full_commit=False):
    value = strip_yaml_comment(raw.strip())
    if value is None or not value:
        return None
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None
        return parsed if isinstance(parsed, str) else None
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            return None
        inner = value[1:-1]
        index = 0
        result = []
        while index < len(inner):
            if inner[index] == "'":
                if index + 1 >= len(inner) or inner[index + 1] != "'":
                    return None
                result.append("'")
                index += 2
            else:
                result.append(inner[index])
                index += 1
        return "".join(result)
    if value.startswith(("[", "{", "&", "*", "!", "|", ">", "%", "@", "`")):
        return None
    if (
        value.endswith(("]", "}"))
        or re.search(r":(?:\s|$)", value)
        or (
            IMPLICIT_NON_STRING_RE.fullmatch(value)
            and not (allow_full_commit and FULL_COMMIT_ID_RE.fullmatch(value))
        )
        or not PLAIN_STRING_RE.fullmatch(value)
    ):
        return None
    return value


def parse_inline_list(raw):
    value = strip_yaml_comment(raw.strip())
    if value is None or not value.startswith("[") or not value.endswith("]"):
        return None
    inner = value[1:-1].strip()
    if not inner:
        return []
    items = []
    start = 0
    quote = None
    escaped = False
    index = 0
    while index < len(inner):
        char = inner[index]
        if escaped:
            escaped = False
        elif quote == '"' and char == "\\":
            escaped = True
        elif quote:
            if char == quote:
                if quote == "'" and index + 1 < len(inner) and inner[index + 1] == "'":
                    index += 1
                else:
                    quote = None
        elif char in "'\"" and not inner[start:index].strip():
            quote = char
        elif char == ",":
            parsed = parse_yaml_scalar(inner[start:index])
            if parsed is None:
                return None
            items.append(parsed)
            start = index + 1
        elif char in "[]{}":
            return None
        index += 1
    if quote or escaped:
        return None
    tail = inner[start:].strip()
    if not tail:
        return items or None
    parsed = parse_yaml_scalar(tail)
    if parsed is None:
        return None
    items.append(parsed)
    return items


def parse_frontmatter(text):
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    fm = {}
    pending_key = None
    pending_items = []
    pending_indent = None
    flow_key = None
    flow_parts = []
    for line in match.group(1).splitlines():
        indentation = line[: len(line) - len(line.lstrip(" \t"))]
        if line.strip() and "\t" in indentation:
            return None
        if flow_key is not None:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line.startswith(" "):
                return None
            fragment = strip_yaml_comment(line.strip())
            if fragment is None:
                return None
            if fragment == "]":
                parsed_list = parse_inline_list("[" + " ".join(flow_parts) + "]")
                if parsed_list is None:
                    return None
                fm[flow_key] = parsed_list
                flow_key = None
                flow_parts = []
            elif fragment:
                flow_parts.append(fragment)
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith(" "):
            fragment = strip_yaml_comment(line.strip())
            if pending_key is not None and not pending_items and fragment == "[":
                flow_key = pending_key
                pending_key = None
                pending_indent = None
                continue
            item = re.fullmatch(r"( +)-\s+(.+?)\s*", line)
            if pending_key is None or item is None:
                return None
            indent = len(item.group(1))
            if pending_indent is not None and indent != pending_indent:
                return None
            parsed = parse_yaml_scalar(item.group(2))
            if parsed is None:
                return None
            pending_indent = indent
            pending_items.append(parsed)
            continue
        if pending_key is not None:
            fm[pending_key] = pending_items if pending_items else ""
            pending_key = None
            pending_items = []
            pending_indent = None
        if ":" not in line:
            return None
        key, _, value = line.partition(":")
        key = key.strip()
        if not FRONTMATTER_KEY_RE.fullmatch(key) or key in fm:
            return None
        value = strip_yaml_comment(value.strip())
        if value is None:
            return None
        if not value:
            pending_key = key
        elif value.startswith("["):
            if strip_yaml_comment(value) == "[":
                flow_key = key
            else:
                parsed_list = parse_inline_list(value)
                if parsed_list is None:
                    return None
                fm[key] = parsed_list
        else:
            parsed = parse_yaml_scalar(value, allow_full_commit=key == "verified")
            if parsed is None:
                return None
            fm[key] = parsed
    if flow_key is not None:
        return None
    if pending_key is not None:
        fm[pending_key] = pending_items if pending_items else ""
    return fm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="return nonzero for warnings as well as errors")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    canon = root / "canon"
    findings = []

    def add(check, severity, detail):
        findings.append({"check": check, "severity": severity, "detail": detail})

    if not canon.is_dir():
        add("structure", "error", "no canon/ directory")
        return report(findings, args.json, args.strict)

    for name in REQUIRED:
        path = canon / name
        if not path.is_file():
            add("structure", "error", f"missing canon/{name}")
        elif path.is_symlink():
            add("structure", "error", f"canon/{name} must not be a symlink")

    files = permanent_files(canon)
    manifest = canon / "manifest.md"
    if manifest.is_file():
        text = manifest.read_text()
        for rel in missing_manifest_routes(files, canon, text):
            add("manifest", "error", f"{rel} not referenced in manifest.md")
        for issue in manifest_route_issues(canon, text):
            add("manifest", "error", f"unsafe or missing route: {issue}")

    for p in files:
        if p.is_symlink():
            add("structure", "error", f"{p.relative_to(canon)} must not be a symlink")
            continue
        body = p.read_text(errors="replace")
        rel = str(p.relative_to(canon))
        n = len(body.splitlines())
        if n > MAX_LINES:
            add("line-caps", "error", f"{rel} has {n} lines (max {MAX_LINES})")
        size = p.stat().st_size
        if size > MAX_BYTES:
            add("size-caps", "error", f"{rel} has {size} bytes (max {MAX_BYTES})")
        if p.relative_to(canon).parts[0] != "decisions":
            content = FRONTMATTER_RE.sub("", body)
            for hit in set(CHANGELOG_RE.findall(content)):
                add("changelog-smell", "warn", f"{rel} contains changelog-style text: {hit!r}")

    rc, _, _ = git(root, "rev-parse", "--git-dir")
    in_git = rc == 0
    if in_git:
        rc, _, err = git(root, "check-ignore", "-q", str(canon / "scratch" / "x"))
        if rc == 1:
            add("scratch-ignored", "error", "canon/scratch/ is not git-ignored")
        elif rc != 0:
            add("scratch-ignored", "error", f"could not verify scratch ignore: {err or 'git failed'}")

    rc, _, _ = git(root, "rev-parse", "--verify", "HEAD^{commit}") if in_git else (1, "", "")
    has_history = in_git and rc == 0
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
            add("staleness", "warn", f"{rel}: history indeterminate outside Git")
            continue
        verified = fm["verified"]
        sources = fm["sources"] if isinstance(fm["sources"], list) else [fm["sources"]]
        if not isinstance(verified, str) or not FULL_COMMIT_ID_RE.fullmatch(verified):
            add("staleness", "warn", f"{rel}: history indeterminate; verified must be a full immutable hexadecimal commit id")
            continue
        if not sources or not all(isinstance(source, str) and source.strip() for source in sources):
            add("staleness", "warn", f"{rel}: sources must contain repository-relative paths")
            continue
        domain_rel = str(p.relative_to(root))
        rc, _, err = git(root, "ls-files", "--error-unmatch", "--", domain_rel)
        if rc != 0:
            add("staleness", "warn", f"{rel}: domain file is not tracked; freshness is indeterminate ({err or 'git failed'})")
            continue
        if not has_history:
            add("staleness", "warn", f"{rel}: history indeterminate in unborn repository")
            continue
        rc, resolved, err = git(root, "rev-parse", "--verify", f"{verified}^{{commit}}")
        if rc != 0:
            add("staleness", "warn", f"{rel}: history indeterminate; verified commit {verified!r} not found ({err or 'git failed'})")
            continue
        if resolved.lower() != verified.lower():
            add("staleness", "warn", f"{rel}: history indeterminate; verified must identify the full commit id")
            continue
        rc, _, err = git(root, "merge-base", "--is-ancestor", verified, "HEAD")
        if rc == 1:
            add("staleness", "warn", f"{rel}: history indeterminate; {verified!r} is not an ancestor of HEAD")
            continue
        if rc != 0:
            add("staleness", "warn", f"{rel}: history indeterminate; ancestry check failed: {err or 'git failed'}")
            continue
        for source in sources:
            source = source.strip()
            safe, detail = contained_regular_file(root, source)
            if not safe:
                add("staleness", "warn", f"{rel}: invalid source {source!r}: {detail}")
                continue
            ignored_rc, _, ignored_err = git(root, "check-ignore", "-q", "--", source)
            if ignored_rc == 0:
                add("staleness", "warn", f"{rel}: ignored source cannot be verified: {source}")
                continue
            if ignored_rc != 1:
                add("staleness", "warn", f"{rel}: source ignore check failed: {ignored_err or 'git failed'}")
                continue
            rc, dirty, err = git(root, "status", "--porcelain=v1", "--untracked-files=all", "--", source)
            if rc != 0:
                add("staleness", "warn", f"{rel}: history indeterminate; source status failed: {err or 'git failed'}")
                continue
            if dirty:
                add("staleness", "warn", f"{rel} is stale: source has staged or unstaged changes: {source}")
                continue
            rc, source_history, err = git(
                root, "rev-list", "--full-history", "--topo-order",
                f"{verified}..HEAD", "--", source,
            )
            if rc != 0:
                add("staleness", "warn", f"{rel}: history indeterminate; source traversal failed: {err or 'git failed'}")
                continue
            source_commits = [commit for commit in source_history.splitlines() if commit]
            if not source_commits:
                continue
            rc, domain_history, err = git(
                root, "rev-list", "--full-history", "--topo-order",
                f"{verified}..HEAD", "--", domain_rel,
            )
            if rc != 0:
                add("staleness", "warn", f"{rel}: history indeterminate; Canon traversal failed: {err or 'git failed'}")
                continue
            domain_commits = [commit for commit in domain_history.splitlines() if commit]
            if not domain_commits:
                add("staleness", "warn", f"{rel} is stale: {source} changed after {verified} without a Canon refresh")
                continue
            uncovered = []
            for source_commit in source_commits:
                covered = False
                for domain_commit in domain_commits:
                    ancestor_rc, _, _ = git(
                        root, "merge-base", "--is-ancestor", source_commit, domain_commit
                    )
                    if ancestor_rc == 0:
                        covered = True
                        break
                if not covered:
                    uncovered.append(source_commit)
            if uncovered:
                add("staleness", "warn", f"{rel} is stale: {source} has {len(uncovered)} source change(s) after its latest Canon refresh")

    return report(findings, args.json, args.strict)


def report(findings, as_json, strict=False):
    errors = [f for f in findings if f["severity"] == "error"]
    failed = bool(errors or (strict and findings))
    if as_json:
        print(json.dumps({"ok": not failed, "strict": strict, "findings": findings}, indent=2))
    else:
        if not findings:
            print("canon doctor: all checks passed")
        for f in findings:
            print(f"[{f['severity']}] {f['check']}: {f['detail']}")
        if findings:
            print(f"canon doctor: {len(errors)} error(s), "
                  f"{len(findings) - len(errors)} warning(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
