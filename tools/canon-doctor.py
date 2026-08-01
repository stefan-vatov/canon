#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""Mechanical health checks for a compact, invariant-first canon/ directory.

usage: canon-doctor.py [--root DIR] [--json] [--strict] [--baseline REV]

Checks (error -> exit 1, warn -> reported only):

  structure               required core files exist                       error
  frontmatter             permanent pages use the compact metadata schema error
  manifest                every normative page is routed; routes resolve  error
  links                   local Markdown and metadata links resolve       error
  validation              declared repository evidence paths safely exist error
  line-caps / size-caps   permanent pages stay within size limits         error
  decision-immutability   committed decision records keep their bytes     error
  scratch-ignored         canon/scratch/ is ignored and never routed      error
  inventory-smell         prose appears to mirror implementation files    warn
  changelog-smell         current rules contain dated change narration    warn

The doctor deliberately does not compare source-file changes with Canon.
Behavior-preserving implementation changes have no Canon impact.
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
    manifest_routes,
    markdown_link_issues,
    missing_manifest_routes,
    resolve_canon_reference,
)

REQUIRED = ["manifest.md", "standards.md"]
MAX_LINES = 250
MAX_BYTES = 64 * 1024
STATUSES = {"normative", "reference", "draft", "deprecated"}
ALLOWED_FIELDS = {
    "status",
    "scope",
    "validation",
    "related",
    "supersedes",
    "replaced_by",
}
LIST_FIELDS = {"scope", "validation", "related", "supersedes"}
LEGACY_FIELDS = {"sources", "verified"}
SOURCE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cs", ".ex", ".exs", ".go", ".java", ".js",
    ".jsx", ".kt", ".php", ".py", ".rb", ".rs", ".swift", ".ts", ".tsx",
}
CHANGELOG_RE = re.compile(
    r"(?i)\bpreviously\b|\b20\d\d-\d\d-\d\d\b|\bwe (?:added|changed|removed)\b"
)
SOURCE_REFERENCE_RE = re.compile(
    r"`[^`\n]*\.(?:c|cc|cpp|cs|exs?|go|java|jsx?|kt|php|py|rb|rs|swift|tsx?)"
    r"(?::\d+)?`"
)
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
FRONTMATTER_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
PLAIN_STRING_RE = re.compile(r'''[A-Za-z0-9._/@:+-][^\s\[\]{},#&*!|>"`\\]*''')
IMPLICIT_NON_STRING_RE = re.compile(
    r"(?ix)(?:"
    r"null|~|true|false|yes|no|on|off|"
    r"[-+]?(?:0b[01_]+|0o[0-7_]+|0x[0-9a-f_]+|[0-9][0-9_]*"
    r"(?:\.[0-9_]*)?(?:e[-+]?[0-9]+)?|\.[0-9_]+(?:e[-+]?[0-9]+)?)|"
    r"[-+]?\.(?:inf|nan)|"
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[tT ]\S+)?"
    r")"
)


def git(root: Path, *args: str) -> tuple[int, str, str]:
    try:
        process = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return 127, "", str(exc)
    return process.returncode, process.stdout.strip(), process.stderr.strip()


def git_bytes(root: Path, *args: str) -> tuple[int, bytes, bytes]:
    try:
        process = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return 127, b"", str(exc).encode()
    return process.returncode, process.stdout, process.stderr


def baseline_decisions(
    root: Path,
    revision: str,
) -> tuple[dict[str, bytes], Path | None, str | None]:
    """Return immutable decision bytes at a Git baseline."""
    returncode, top_text, error = git(root, "rev-parse", "--show-toplevel")
    if returncode != 0:
        return {}, None, error or "not a Git worktree"
    git_root = Path(top_text).resolve()
    try:
        prefix = root.relative_to(git_root)
    except ValueError:
        return {}, git_root, "root resolves outside its Git worktree"

    returncode, commit_id, error = git(
        git_root,
        "rev-parse",
        "--verify",
        f"{revision}^{{commit}}",
    )
    if returncode != 0:
        if revision == "HEAD":
            return {}, git_root, None
        return {}, git_root, error or f"invalid baseline {revision!r}"
    revision = commit_id

    decision_root = prefix / "canon" / "decisions"
    returncode, listing, error = git(
        git_root,
        "ls-tree",
        "-r",
        "--name-only",
        "-z",
        revision,
        "--",
        decision_root.as_posix(),
    )
    if returncode != 0:
        return {}, git_root, error or "could not inspect baseline decisions"

    result: dict[str, bytes] = {}
    canon_prefix = prefix / "canon"
    for repository_path in filter(None, listing.split("\0")):
        path = Path(repository_path)
        if path.suffix != ".md":
            continue
        try:
            relative = path.relative_to(canon_prefix).as_posix()
        except ValueError:
            continue
        returncode, content, binary_error = git_bytes(
            git_root,
            "show",
            f"{revision}:{repository_path}",
        )
        if returncode != 0:
            return (
                {},
                git_root,
                binary_error.decode(errors="replace")
                or f"could not read {repository_path} at {revision}",
            )
        result[relative] = content
    return result, git_root, None


def permanent_files(canon: Path) -> tuple[list[Path], list[Path]]:
    """Return permanent Markdown files and unsafe symlinks without following them."""
    files: list[Path] = []
    unsafe: list[Path] = []
    pending = [canon]
    while pending:
        directory = pending.pop()
        for path in sorted(directory.iterdir()):
            relative = path.relative_to(canon)
            if relative.parts[0] == "scratch":
                if len(relative.parts) == 1 and path.is_symlink():
                    unsafe.append(path)
                continue
            if path.is_symlink():
                unsafe.append(path)
            elif path.is_dir():
                pending.append(path)
            elif path.is_file() and path.suffix == ".md":
                files.append(path)
    return sorted(files), sorted(unsafe)


def strip_yaml_comment(value: str) -> str | None:
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
                if (
                    quote == "'"
                    and index + 1 < len(value)
                    and value[index + 1] == "'"
                ):
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


def parse_yaml_scalar(raw: str) -> str | None:
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
    if value.startswith(("[", "{", "&", "*", "!", "|", ">", "%", "`")):
        return None
    if (
        value.endswith(("]", "}"))
        or re.search(r":(?:\s|$)", value)
        or IMPLICIT_NON_STRING_RE.fullmatch(value)
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
                if (
                    quote == "'"
                    and index + 1 < len(inner)
                    and inner[index + 1] == "'"
                ):
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


def parse_frontmatter(text: str) -> dict[str, object] | None:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    frontmatter: dict[str, object] = {}
    pending_key = None
    pending_items: list[str] = []
    pending_indent = None
    flow_key = None
    flow_parts: list[str] = []
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
                parsed = parse_inline_list("[" + " ".join(flow_parts) + "]")
                if parsed is None:
                    return None
                frontmatter[flow_key] = parsed
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
            frontmatter[pending_key] = pending_items if pending_items else ""
            pending_key = None
            pending_items = []
            pending_indent = None
        if ":" not in line:
            return None
        key, _, value = line.partition(":")
        key = key.strip()
        if not FRONTMATTER_KEY_RE.fullmatch(key) or key in frontmatter:
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
                parsed = parse_inline_list(value)
                if parsed is None:
                    return None
                frontmatter[key] = parsed
        else:
            parsed = parse_yaml_scalar(value)
            if parsed is None:
                return None
            frontmatter[key] = parsed
    if flow_key is not None:
        return None
    if pending_key is not None:
        frontmatter[pending_key] = pending_items if pending_items else ""
    return frontmatter


def validation_issue(root: Path, value: str) -> str | None:
    ok, detail = contained_regular_file(root, value)
    return None if ok else detail


def metadata_link_issue(canon: Path, page: Path, value: str) -> str | None:
    route = resolve_canon_reference(page.relative_to(canon), value)
    if route is None:
        return "not a safe relative Markdown path"
    if route == "scratch" or route.startswith("scratch/"):
        return "scratch must not be linked from permanent Canon"
    ok, detail = contained_regular_file(canon, route)
    return None if ok else detail


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return nonzero for warnings as well as errors",
    )
    parser.add_argument(
        "--baseline",
        help=(
            "trusted pre-migration Git commit whose legacy decision records "
            "may be grandfathered; defaults to HEAD for immutability only"
        ),
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    canon = root / "canon"
    findings: list[dict[str, str]] = []

    def add(check: str, severity: str, detail: str) -> None:
        findings.append({"check": check, "severity": severity, "detail": detail})

    if not canon.is_dir() or canon.is_symlink():
        add("structure", "error", "no safe canon/ directory")
        return report(findings, args.json, args.strict)

    for name in REQUIRED:
        path = canon / name
        if not path.is_file():
            add("structure", "error", f"missing canon/{name}")
        elif path.is_symlink():
            add("structure", "error", f"canon/{name} must not be a symlink")

    files, unsafe_paths = permanent_files(canon)
    for path in unsafe_paths:
        add(
            "structure",
            "error",
            f"{path.relative_to(canon).as_posix()} must not be a symlink",
        )
    head_records, git_root, head_error = baseline_decisions(root, "HEAD")
    if head_error:
        add("decision-immutability", "error", head_error)
    legacy_records: dict[str, bytes] = {}
    legacy_error = None
    if args.baseline is not None:
        legacy_records, legacy_git_root, legacy_error = baseline_decisions(
            root,
            args.baseline,
        )
        if git_root is None:
            git_root = legacy_git_root
        if legacy_error:
            add("decision-immutability", "error", legacy_error)

    reported_decisions: set[str] = set()

    def verify_decisions(records: dict[str, bytes], label: str) -> set[str]:
        unchanged = set()
        for rel, original in sorted(records.items()):
            path = canon / rel
            if path.is_symlink() or not path.is_file():
                if rel not in reported_decisions:
                    reported_decisions.add(rel)
                    add(
                        "decision-immutability",
                        "error",
                        f"{rel} existed at {label} but is missing or unsafe",
                    )
            elif path.read_bytes() != original:
                if rel not in reported_decisions:
                    reported_decisions.add(rel)
                    add(
                        "decision-immutability",
                        "error",
                        f"{rel} differs from its immutable bytes at {label}",
                    )
            else:
                unchanged.add(rel)
        return unchanged

    head_unchanged = verify_decisions(head_records, "HEAD")
    if (
        args.baseline is not None
        and not legacy_error
        and legacy_records == head_records
    ):
        legacy_unchanged = head_unchanged
    elif args.baseline is not None and not legacy_error:
        legacy_unchanged = verify_decisions(legacy_records, args.baseline)
    else:
        legacy_unchanged = set()

    metadata: dict[Path, dict[str, object] | None] = {}
    normative_files: list[Path] = []
    grandfathered_decisions: set[str] = set()
    for path in files:
        relative = path.relative_to(canon)
        rel = relative.as_posix()
        if path.is_symlink():
            add("structure", "error", f"{rel} must not be a symlink")
            continue
        body = path.read_text(errors="replace")
        is_decision = relative.parts[0] == "decisions"
        # A grandfathered decision's bytes are immutable, so schema, cap, and
        # link findings against it could never be repaired; skip them all.
        is_grandfathered_decision = is_decision and rel in legacy_unchanged
        if is_grandfathered_decision:
            grandfathered_decisions.add(rel)
        if not is_grandfathered_decision:
            line_count = len(body.splitlines())
            if line_count > MAX_LINES:
                add(
                    "line-caps",
                    "error",
                    f"{rel} has {line_count} lines (max {MAX_LINES})",
                )
            size = path.stat().st_size
            if size > MAX_BYTES:
                add("size-caps", "error", f"{rel} has {size} bytes (max {MAX_BYTES})")

        frontmatter = parse_frontmatter(body)
        metadata[path] = frontmatter
        if frontmatter is None:
            if is_decision:
                normative_files.append(path)
                if not is_grandfathered_decision:
                    add(
                        "frontmatter",
                        "error",
                        f"{rel} is a new decision and requires compact front matter",
                    )
            else:
                add("frontmatter", "error", f"{rel} has no valid front matter")
        elif is_grandfathered_decision:
            normative_files.append(path)
        else:
            keys = set(frontmatter)
            for key in sorted(keys & LEGACY_FIELDS):
                add(
                    "frontmatter",
                    "error",
                    f"{rel} uses retired implementation-inventory field {key!r}",
                )
            for key in sorted(keys - ALLOWED_FIELDS - LEGACY_FIELDS):
                add("frontmatter", "error", f"{rel} uses unknown field {key!r}")
            status = frontmatter.get("status")
            if not isinstance(status, str) or status not in STATUSES:
                add(
                    "frontmatter",
                    "error",
                    f"{rel} status must be one of {sorted(STATUSES)}",
                )
            elif status == "normative":
                normative_files.append(path)
            if rel == "manifest.md" and status != "reference":
                add("frontmatter", "error", "manifest.md must have status: reference")
            if rel == "standards.md" and status != "normative":
                add("frontmatter", "error", "standards.md must have status: normative")
            if is_decision and status not in (None, "normative"):
                add(
                    "frontmatter",
                    "error",
                    f"{rel} decision records must have status: normative",
                )

            for field in LIST_FIELDS:
                if field not in frontmatter:
                    continue
                value = frontmatter[field]
                if (
                    not isinstance(value, list)
                    or not value
                    or not all(isinstance(item, str) and item.strip() for item in value)
                    or len(set(value)) != len(value)
                ):
                    add(
                        "frontmatter",
                        "error",
                        f"{rel} field {field!r} must be a non-empty unique string list",
                    )
            replaced_by = frontmatter.get("replaced_by")
            if replaced_by is not None and not isinstance(replaced_by, str):
                add(
                    "frontmatter",
                    "error",
                    f"{rel} field 'replaced_by' must be one Markdown path",
                )
            if status == "deprecated" and not isinstance(replaced_by, str):
                add(
                    "frontmatter",
                    "error",
                    f"{rel} is deprecated but does not name replaced_by",
                )
            if replaced_by is not None and (status != "deprecated" or is_decision):
                add(
                    "frontmatter",
                    "error",
                    f"{rel} uses replaced_by outside a deprecated non-decision page",
                )
            if "supersedes" in frontmatter and not is_decision:
                add(
                    "frontmatter",
                    "error",
                    f"{rel} uses supersedes outside decisions/",
                )

            scopes = frontmatter.get("scope", [])
            if isinstance(scopes, list):
                source_scopes = [
                    value
                    for value in scopes
                    if Path(value.split("#", 1)[0]).suffix.lower() in SOURCE_SUFFIXES
                ]
                if source_scopes:
                    add(
                        "inventory-smell",
                        "warn",
                        f"{rel} scope names implementation files: {', '.join(source_scopes)}",
                    )
            validations = frontmatter.get("validation", [])
            if isinstance(validations, list):
                for value in validations:
                    issue = validation_issue(root, value)
                    if issue:
                        add(
                            "validation",
                            "error",
                            f"{rel} validation {value!r}: {issue}",
                        )
            for field in ("related", "supersedes"):
                values = frontmatter.get(field, [])
                if isinstance(values, list):
                    for value in values:
                        issue = metadata_link_issue(canon, path, value)
                        route = resolve_canon_reference(relative, value)
                        if (
                            not issue
                            and field == "supersedes"
                            and (
                                route is None
                                or not route.startswith("decisions/")
                                or route == rel
                            )
                        ):
                            issue = "must name a different predecessor in decisions/"
                        if issue:
                            add(
                                "links",
                                "error",
                                f"{rel} {field} link {value!r}: {issue}",
                            )
            if isinstance(replaced_by, str):
                issue = metadata_link_issue(canon, path, replaced_by)
                route = resolve_canon_reference(relative, replaced_by)
                if not issue and route == rel:
                    issue = "must name a different replacement page"
                if issue:
                    add(
                        "links",
                        "error",
                        f"{rel} replaced_by link {replaced_by!r}: {issue}",
                    )

        content = FRONTMATTER_RE.sub("", body)
        if not is_decision:
            for hit in sorted(set(CHANGELOG_RE.findall(content))):
                add(
                    "changelog-smell",
                    "warn",
                    f"{rel} contains changelog-style text: {hit!r}",
                )
            source_references = sorted(set(SOURCE_REFERENCE_RE.findall(content)))
            if len(source_references) >= 5:
                add(
                    "inventory-smell",
                    "warn",
                    f"{rel} appears to enumerate {len(source_references)} implementation files",
                )
        if not is_grandfathered_decision:
            for issue in markdown_link_issues(canon, path, body):
                add("links", "error", f"{rel}: {issue}")

    supersession_graph: dict[str, set[str]] = {}
    for path, frontmatter in metadata.items():
        rel = path.relative_to(canon).as_posix()
        if (
            rel in grandfathered_decisions
            or not rel.startswith("decisions/")
            or not isinstance(frontmatter, dict)
            or not isinstance(frontmatter.get("supersedes"), list)
        ):
            continue
        supersession_graph[rel] = {
            route
            for value in frontmatter["supersedes"]
            if isinstance(value, str)
            and (route := resolve_canon_reference(path.relative_to(canon), value))
            is not None
            and route.startswith("decisions/")
        }
    visiting: set[str] = set()
    visited: set[str] = set()
    cycle_nodes: set[str] = set()

    def visit_decision(node: str, trail: list[str]) -> None:
        if node in visiting:
            cycle_nodes.update(trail[trail.index(node) :])
            return
        if node in visited:
            return
        visiting.add(node)
        trail.append(node)
        for predecessor in sorted(supersession_graph.get(node, set())):
            if predecessor in supersession_graph:
                visit_decision(predecessor, trail)
        trail.pop()
        visiting.remove(node)
        visited.add(node)

    for decision in sorted(supersession_graph):
        visit_decision(decision, [])
    if cycle_nodes:
        add(
            "links",
            "error",
            "decision supersession cycle: " + ", ".join(sorted(cycle_nodes)),
        )

    manifest = canon / "manifest.md"
    if manifest.is_file() and not manifest.is_symlink():
        manifest_text = manifest.read_text(errors="replace")
        for rel in missing_manifest_routes(normative_files, canon, manifest_text):
            add("manifest", "error", f"normative page {rel} is not routed")
        for issue in manifest_route_issues(canon, manifest_text):
            add("manifest", "error", f"unsafe or missing route: {issue}")
        routed = manifest_routes(manifest_text)
        if any(route == "scratch" or route.startswith("scratch/") for route in routed):
            add("scratch-ignored", "error", "manifest.md must not route scratch")

    if git_root is None:
        add(
            "scratch-ignored",
            "error",
            "could not verify repository-root scratch ignore outside Git",
        )
    else:
        repository_ignore = root / ".gitignore"
        if repository_ignore.is_symlink() or not repository_ignore.is_file():
            add(
                "scratch-ignored",
                "error",
                "repository-root .gitignore must be a regular non-symlink file",
            )
        returncode, ignore_detail, error = git(
            root,
            "check-ignore",
            "-v",
            "--no-index",
            str(canon / "scratch" / "probe"),
        )
        if returncode == 1:
            add("scratch-ignored", "error", "canon/scratch/ is not git-ignored")
        elif returncode != 0:
            add(
                "scratch-ignored",
                "error",
                f"could not verify scratch ignore: {error or 'git failed'}",
            )
        else:
            source = ignore_detail.split("\t", 1)[0].rsplit(":", 2)[0]
            source_path = Path(source)
            if not source_path.is_absolute():
                source_path = git_root / source_path
            if source_path.resolve() != repository_ignore.resolve():
                add(
                    "scratch-ignored",
                    "error",
                    "canon/scratch/ must be ignored by the repository-root .gitignore",
                )
        for path in files:
            returncode, _, error = git(
                root,
                "check-ignore",
                "-q",
                "--no-index",
                str(path),
            )
            if returncode == 0:
                add(
                    "scratch-ignored",
                    "error",
                    f"permanent Canon file is ignored: "
                    f"{path.relative_to(canon).as_posix()}",
                )
            elif returncode not in (0, 1):
                add(
                    "scratch-ignored",
                    "error",
                    f"could not verify permanent Canon visibility: "
                    f"{error or 'git failed'}",
                )
        returncode, tracked, error = git(
            root,
            "ls-files",
            "--",
            "canon/scratch",
        )
        if returncode != 0:
            add(
                "scratch-ignored",
                "error",
                f"could not verify tracked scratch files: {error or 'git failed'}",
            )
        elif tracked:
            add(
                "scratch-ignored",
                "error",
                "canon/scratch/ contains tracked files",
            )

    return report(findings, args.json, args.strict)


def report(
    findings: list[dict[str, str]],
    as_json: bool,
    strict: bool = False,
) -> int:
    errors = [finding for finding in findings if finding["severity"] == "error"]
    failed = bool(errors or (strict and findings))
    if as_json:
        print(
            json.dumps(
                {"ok": not failed, "strict": strict, "findings": findings},
                indent=2,
            )
        )
    else:
        if not findings:
            print("canon doctor: all checks passed")
        for finding in findings:
            print(
                f"[{finding['severity']}] "
                f"{finding['check']}: {finding['detail']}"
            )
        if findings:
            print(
                f"canon doctor: {len(errors)} error(s), "
                f"{len(findings) - len(errors)} warning(s)"
            )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
