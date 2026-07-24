"""Shared, dependency-free Canon path, link, and manifest helpers."""

from __future__ import annotations

import posixpath
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


# Markdown inline links with a plain or angle-bracket destination and optional
# title. This intentionally does not pretend to be a full Markdown parser; a
# malformed or ambiguous route is rejected instead of guessed.
MARKDOWN_LINK_RE = re.compile(
    r"\]\(\s*(?:<(?P<angle>[^>]+)>|(?P<plain>[^\s)]+))"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)
MANIFEST_LINK_RE = re.compile(
    r"\[[^\]\n]+\]\(\s*(?:<(?P<angle>[^>]+)>|(?P<plain>[^\s)]+))"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)


def _is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    index -= 1
    while index >= 0 and text[index] == "\\":
        backslashes += 1
        index -= 1
    return backslashes % 2 == 1


def _strip_inline_code(text: str) -> str:
    """Blank CommonMark-style code spans while preserving line positions."""
    characters = list(text)
    index = 0
    while index < len(text):
        if text[index] != "`" or _is_escaped(text, index):
            index += 1
            continue
        opener_end = index
        while opener_end < len(text) and text[opener_end] == "`":
            opener_end += 1
        width = opener_end - index
        cursor = opener_end
        closing_end = None
        while cursor < len(text):
            if text[cursor] != "`":
                cursor += 1
                continue
            run_end = cursor
            while run_end < len(text) and text[run_end] == "`":
                run_end += 1
            if run_end - cursor == width:
                closing_end = run_end
                break
            cursor = run_end
        if closing_end is None:
            index = opener_end
            continue
        for position in range(index, closing_end):
            if characters[position] != "\n":
                characters[position] = " "
        index = closing_end
    return "".join(characters)


def _is_real_link(text: str, start: int) -> bool:
    if _is_escaped(text, start):
        return False
    return not (
        start > 0
        and text[start - 1] == "!"
        and not _is_escaped(text, start - 1)
    )


def normalize_route(target: str) -> str | None:
    """Return a safe Canon-relative Markdown route, or ``None``.

    Routes are lexical identifiers first. Filesystem containment and symlink
    checks happen separately so a manifest cannot make an escaping symlink
    legitimate merely by naming it.
    """
    target = unquote(target.strip().strip("<>"))
    if not target or "\\" in target or "\x00" in target:
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or target.startswith(("/", "~")):
        return None
    route = posixpath.normpath(parsed.path)
    if route.startswith("canon/"):
        route = route.removeprefix("canon/")
    route = route.removeprefix("./")
    if (
        not route
        or route in (".", "..")
        or route.startswith("../")
        or not route.endswith(".md")
    ):
        return None
    return route


def manifest_route_records(text: str) -> list[tuple[str, str]]:
    """Return safe routes and their visible lines after Markdown exclusions."""
    records: list[tuple[str, str]] = []
    without_comments = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    visible_lines: list[str] = []
    in_fence = False
    fence_marker = ""
    for line in without_comments.splitlines():
        stripped = line.lstrip()
        fence = re.match(r"(`{3,}|~{3,})", stripped)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker[0] == fence_marker[0] and len(marker) >= len(fence_marker):
                in_fence = False
                fence_marker = ""
            continue
        if in_fence:
            continue
        visible_lines.append(line)
    for line in _strip_inline_code("\n".join(visible_lines)).splitlines():
        matches = [
            match
            for match in MANIFEST_LINK_RE.finditer(line)
            if _is_real_link(line, match.start())
        ]
        if len(matches) != 1:
            continue
        match = matches[0]
        remainder = line[: match.start()] + line[match.end() :]
        if not re.search(r"(?i)\bread\s+(?:when|for)\s+[A-Za-z0-9]", remainder):
            continue
        route = normalize_route(match.group("angle") or match.group("plain"))
        if route:
            records.append((route, line))
    return records


def manifest_routes(text: str) -> set[str]:
    """Return safe, one-link routes with an explicit retrieval condition."""
    return {route for route, _line in manifest_route_records(text)}


def markdown_link_targets(text: str) -> list[str]:
    """Return Markdown link destinations in source order."""
    return [
        match.group("angle") or match.group("plain")
        for match in MARKDOWN_LINK_RE.finditer(text)
    ]


def resolve_canon_reference(page: Path, target: str) -> str | None:
    """Resolve a local Markdown target to a safe Canon-relative route."""
    raw = unquote(target.strip().strip("<>"))
    if not raw or "\\" in raw or "\x00" in raw:
        return None
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc or raw.startswith(("/", "~")):
        return None
    if not parsed.path or not parsed.path.endswith(".md"):
        return None
    if parsed.path.startswith("canon/"):
        candidate = parsed.path.removeprefix("canon/")
    else:
        candidate = posixpath.join(page.parent.as_posix(), parsed.path)
    route = posixpath.normpath(candidate).removeprefix("./")
    if (
        not route
        or route in (".", "..")
        or route.startswith("../")
        or not route.endswith(".md")
    ):
        return None
    return route


def contained_regular_file(root: Path, relative: str) -> tuple[bool, str]:
    """Validate a route/source as a non-symlink regular file beneath root."""
    root = root.resolve()
    raw = unquote(relative.strip())
    parsed = urlsplit(raw)
    route = posixpath.normpath(parsed.path)
    if (
        not raw
        or "\\" in raw
        or "\x00" in raw
        or parsed.scheme
        or parsed.netloc
        or raw.startswith(("/", "~"))
        or route in (".", "..")
        or route.startswith("../")
    ):
        return False, "path is not a safe repository-relative path"

    candidate = root / route
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, RuntimeError, ValueError):
        return False, "path is missing or resolves outside its root"

    current = root
    for part in Path(route).parts:
        current = current / part
        if current.is_symlink():
            return False, "symlinked paths are not valid permanent Canon/source evidence"
    if not resolved.is_file():
        return False, "path is not a regular file"
    return True, ""


def missing_manifest_routes(files: list[Path], canon: Path, text: str) -> list[str]:
    routes = manifest_routes(text)
    return sorted(
        path.relative_to(canon).as_posix()
        for path in files
        if path.name != "manifest.md"
        and path.relative_to(canon).as_posix() not in routes
    )


def manifest_route_issues(canon: Path, text: str) -> list[str]:
    """Return deterministic problems for every declared local route."""
    issues = []
    for route in sorted(manifest_routes(text)):
        if route == "scratch" or route.startswith("scratch/"):
            issues.append(f"{route}: scratch must not be routed")
            continue
        ok, detail = contained_regular_file(canon, route)
        if not ok:
            issues.append(f"{route}: {detail}")
    return issues


def markdown_link_issues(canon: Path, page: Path, text: str) -> list[str]:
    """Return broken or unsafe local Markdown links for one Canon page."""
    issues = []
    relative_page = page.relative_to(canon)
    for target in markdown_link_targets(text):
        parsed = urlsplit(unquote(target.strip().strip("<>")))
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        if not parsed.path.endswith(".md"):
            continue
        route = resolve_canon_reference(relative_page, target)
        if route is None:
            issues.append(f"{target}: path is not a safe Canon Markdown link")
            continue
        if route == "scratch" or route.startswith("scratch/"):
            issues.append(f"{target}: scratch must not be linked from permanent Canon")
            continue
        ok, detail = contained_regular_file(canon, route)
        if not ok:
            issues.append(f"{target}: {detail}")
    return issues
