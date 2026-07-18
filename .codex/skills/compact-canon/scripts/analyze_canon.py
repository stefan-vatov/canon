#!/usr/bin/env python3
"""Read-only inventory for Project Canon compaction."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


CORE_FILES = {"overview.md", "glossary.md", "standards.md", "manifest.md"}
SPECIAL_DIRS = {"decisions", "plans", "scratch"}
MAX_BYTES = 64 * 1024
MAX_LINES = 250
WORD_RE = re.compile(r"[a-z][a-z0-9_-]{2,}")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#?]+\.md)(?:#[^)]+)?\)")
CANON_PATH_RE = re.compile(r"(?<![A-Za-z0-9_./-])canon/([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\.md)")
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
STOP_WORDS = {
    "and", "are", "but", "canon", "file", "files", "for", "from", "has",
    "have", "into", "must", "not", "only", "project", "should", "that",
    "the", "their", "then", "this", "use", "when", "with",
}


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def strip_yaml_comment(value: str) -> str | None:
    quote: str | None = None
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


def parse_yaml_scalar(raw: str, *, allow_full_commit: bool = False) -> str | None:
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
        result: list[str] = []
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


def parse_inline_list(raw: str) -> list[str] | None:
    value = strip_yaml_comment(raw.strip())
    if value is None or not value.startswith("[") or not value.endswith("]"):
        return None
    inner = value[1:-1].strip()
    if not inner:
        return []
    items: list[str] = []
    start = 0
    quote: str | None = None
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


def parse_simple_frontmatter(raw: str) -> dict[str, object] | None:
    data: dict[str, object] = {}
    pending_key: str | None = None
    pending_items: list[str] = []
    pending_indent: int | None = None
    flow_key: str | None = None
    flow_parts: list[str] = []
    for line in raw.splitlines():
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
                data[flow_key] = parsed_list
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
            data[pending_key] = pending_items if pending_items else ""
            pending_key = None
            pending_items = []
            pending_indent = None
        if ":" not in line:
            return None
        key, value = line.split(":", 1)
        key = key.strip()
        if not FRONTMATTER_KEY_RE.fullmatch(key) or key in data:
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
                data[key] = parsed_list
        else:
            parsed = parse_yaml_scalar(value, allow_full_commit=key == "verified")
            if parsed is None:
                return None
            data[key] = parsed
    if flow_key is not None:
        return None
    if pending_key is not None:
        data[pending_key] = pending_items if pending_items else ""
    return data


def strip_frontmatter(text: str) -> tuple[str, dict[str, object]]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text, {}
    return text[match.end() :], parse_simple_frontmatter(match.group(1)) or {}


def permanent_markdown(canon: Path) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    unsafe: list[str] = []
    for path in sorted(canon.rglob("*.md")):
        rel = path.relative_to(canon)
        if rel.parts and rel.parts[0] == "scratch":
            continue
        if path.is_symlink() or not path.is_file():
            unsafe.append(rel.as_posix())
            continue
        files.append(path)
    return files, unsafe


def manifest_routes(canon: Path, text: str) -> set[str]:
    routes: set[str] = set(CANON_PATH_RE.findall(text))
    for target in LINK_RE.findall(text):
        if "://" in target or target.startswith("/"):
            continue
        candidate = target.removeprefix("./").removeprefix("canon/")
        if ".." in Path(candidate).parts:
            continue
        routes.add(candidate)
    return {route for route in routes if (canon / route).suffix == ".md"}


def paragraphs(body: str) -> set[str]:
    result: set[str] = set()
    for paragraph in re.split(r"\n\s*\n", body):
        normalized = re.sub(r"[`*_>#|\[\]()]", " ", paragraph.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if len(normalized) >= 90 and not normalized.startswith("sources:"):
            result.add(normalized)
    return result


def token_counts(body: str) -> Counter[str]:
    return Counter(word for word in WORD_RE.findall(body.lower()) if word not in STOP_WORDS)


def cosine(left: Counter[str], right: Counter[str]) -> float:
    common = left.keys() & right.keys()
    numerator = sum(left[word] * right[word] for word in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def freshness(root: Path, rel: str, metadata: dict[str, object]) -> str:
    sources = metadata.get("sources")
    verified = str(metadata.get("verified", ""))
    if not isinstance(sources, list) or not sources or not re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", verified):
        return "indeterminate"
    commit = run_git(root, "cat-file", "-e", f"{verified}^{{commit}}")
    if commit.returncode:
        return "indeterminate"
    ancestor = run_git(root, "merge-base", "--is-ancestor", verified, "HEAD")
    if ancestor.returncode:
        return "indeterminate"
    safe_sources: list[str] = []
    for source in sources:
        source_path = Path(str(source))
        if source_path.is_absolute() or ".." in source_path.parts:
            return "indeterminate"
        resolved = root / source_path
        if resolved.is_symlink() or not resolved.exists():
            return "indeterminate"
        safe_sources.append(source_path.as_posix())
    dirty = run_git(root, "status", "--porcelain", "--untracked-files=all", "--", *safe_sources)
    canon_dirty = run_git(root, "status", "--porcelain", "--", f"canon/{rel}")
    if dirty.stdout.strip():
        return "pending" if canon_dirty.stdout.strip() else "stale"
    changed = run_git(root, "diff", "--quiet", f"{verified}..HEAD", "--", *safe_sources)
    if changed.returncode == 0:
        return "fresh"
    if changed.returncode == 1:
        return "stale"
    return "indeterminate"


def analyze(root: Path) -> dict[str, object]:
    root = Path(run_git(root, "rev-parse", "--show-toplevel").stdout.strip() or root).resolve()
    canon = root / "canon"
    if canon.is_symlink() or not canon.is_dir():
        raise SystemExit(f"missing or unsafe Canon directory: {canon}")
    files, unsafe = permanent_markdown(canon)
    relative = {path.relative_to(canon).as_posix(): path for path in files}
    bodies: dict[str, str] = {}
    metadata: dict[str, dict[str, object]] = {}
    records: list[dict[str, object]] = []
    decision_hashes: dict[str, str] = {}
    paragraph_owners: defaultdict[str, list[str]] = defaultdict(list)
    vectors: dict[str, Counter[str]] = {}
    for rel, path in relative.items():
        text = path.read_text(errors="replace")
        if rel.startswith("decisions/"):
            decision_hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        body, frontmatter = strip_frontmatter(text)
        bodies[rel], metadata[rel] = body, frontmatter
        for paragraph in paragraphs(body):
            paragraph_owners[paragraph].append(rel)
        vectors[rel] = token_counts(body)
        top = rel.split("/", 1)[0]
        needs_freshness = rel not in CORE_FILES and top not in SPECIAL_DIRS
        lines = text.splitlines()
        compact_bytes = len(re.sub(r"\s+", " ", text).strip().encode())
        records.append({
            "path": rel,
            "lines": len(lines),
            "bytes": len(text.encode()),
            "compact_bytes": compact_bytes,
            "max_line_length": max((len(line) for line in lines), default=0),
            "canon_links": len(manifest_routes(canon, body) - {rel}),
            "words": len(WORD_RE.findall(body.lower())),
            "freshness": freshness(root, rel, frontmatter) if needs_freshness else "not-applicable",
        })
    manifest = bodies.get("manifest.md", "")
    routes = manifest_routes(canon, manifest)
    expected_routes = set(relative) - {"manifest.md"}
    repeated = [
        {"files": owners, "text": paragraph[:220]}
        for paragraph, owners in paragraph_owners.items()
        if len(owners) > 1
    ]
    overlap: list[dict[str, object]] = []
    names = sorted(vectors)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            score = cosine(vectors[left], vectors[right])
            if score >= 0.45:
                overlap.append({"left": left, "right": right, "score": round(score, 3)})
    overlap.sort(key=lambda item: (-float(item["score"]), str(item["left"]), str(item["right"])))
    freshness_counts = Counter(str(record["freshness"]) for record in records)
    cap_violations = [
        record
        for record in records
        if int(record["lines"]) > MAX_LINES or int(record["bytes"]) > MAX_BYTES
    ]
    return {
        "root": str(root),
        "canon": str(canon),
        "summary": {
            "files": len(records),
            "lines": sum(int(record["lines"]) for record in records),
            "bytes": sum(int(record["bytes"]) for record in records),
            "words": sum(int(record["words"]) for record in records),
            "routes": len(routes),
            "cap_violations": len(cap_violations),
            "freshness": dict(sorted(freshness_counts.items())),
        },
        "missing_routes": sorted(expected_routes - routes),
        "dead_routes": sorted(routes - set(relative)),
        "unsafe_paths": unsafe,
        "cap_violations": cap_violations,
        "decision_hashes": decision_hashes,
        "files_without_canon_links": sorted(
            str(record["path"])
            for record in records
            if "/" in str(record["path"])
            and not str(record["path"]).startswith(("decisions/", "plans/"))
            and int(record["canon_links"]) == 0
        ),
        "largest_files": sorted(records, key=lambda item: (-int(item["bytes"]), str(item["path"])))[:15],
        "repeated_paragraphs": repeated[:20],
        "overlap_candidates": overlap[:20],
        "files": records,
    }


def print_text(report: dict[str, object]) -> None:
    summary = report["summary"]
    assert isinstance(summary, dict)
    print(f"Canon: {report['canon']}")
    print(
        "Permanent: "
        f"{summary['files']} files, {summary['lines']} lines, "
        f"{summary['bytes']} bytes, {summary['words']} words"
    )
    print(f"Routes: {summary['routes']} | freshness: {summary['freshness']}")
    print(f"Size-cap violations: {summary['cap_violations']}")
    for key in ("missing_routes", "dead_routes", "unsafe_paths"):
        values = report[key]
        assert isinstance(values, list)
        print(f"{key.replace('_', ' ').title()}: {', '.join(map(str, values)) if values else 'none'}")
    print("Largest files:")
    for item in report["largest_files"]:
        print(
            f"  {item['bytes']:>7} B  {item['lines']:>4} lines  "
            f"max-line={item['max_line_length']:<5} compact={item['compact_bytes']:>7} B  "
            f"{item['path']}  [{item['freshness']}]"
        )
    print("Files without Canon links:", ", ".join(report["files_without_canon_links"]) or "none")
    print("Repeated paragraphs:", len(report["repeated_paragraphs"]))
    print("Overlap candidates:")
    for item in report["overlap_candidates"]:
        print(f"  {item['score']:.3f}  {item['left']} <> {item['right']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root or a path inside it")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    report = analyze(args.root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
