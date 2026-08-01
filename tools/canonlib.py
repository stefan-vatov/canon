"""Shared, dependency-free Canon path, link, and manifest helpers."""

from __future__ import annotations

import posixpath
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


# Markdown inline links with a plain or angle-bracket destination and optional
# title. This intentionally does not pretend to be a full Markdown parser; a
# malformed or ambiguous route is rejected instead of guessed.
MANIFEST_LINK_RE = re.compile(
    r"\[[^\]\n]+\]\(\s*(?:<(?P<angle>[^>\n]{1,1024})>|(?P<plain>[^\s)]{1,1024}))"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)
# Page-body links are matched more permissively than manifest routes: empty
# labels, one level of nested brackets, and labels wrapping a single line
# are all real CommonMark links whose broken targets must still be reported.
# Labels never span a blank line, so a stray bracket in one paragraph cannot
# turn later prose into a link.
BODY_LINK_RE = re.compile(
    r"\[(?:[^\[\]\n]|\n(?![ \t]*\n)|\[[^\[\]\n]*\])*\]"
    r"\(\s*(?:<(?P<angle>[^>\n]{1,1024})>|(?P<plain>[^\s)]{1,1024}))"
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
            if text[cursor] == "\n":
                line_end = text.find("\n", cursor + 1)
                if line_end == -1:
                    line_end = len(text)
                if not text[cursor + 1 : line_end].strip():
                    # A blank line ends the paragraph; a code span cannot
                    # continue across it, so the opener is a literal backtick.
                    break
                cursor += 1
                continue
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
    legitimate merely by naming it. A route resolves exactly like a page link
    written in ``manifest.md`` at the Canon root.
    """
    return resolve_canon_reference(Path("manifest.md"), target)


def visible_markdown_text(text: str) -> str:
    """Return text without HTML comments, fenced blocks, and code spans.

    Fence state is tracked first so a literal ``<!--`` inside a fenced block
    cannot swallow the rest of the page, and comment state is tracked across
    lines so fence-like markers inside a comment stay inert.
    """
    visible_lines: list[str] = []
    in_fence = False
    fence_marker = ""
    in_comment = False
    for line in text.splitlines():
        if in_comment:
            end = line.find("-->")
            if end == -1:
                continue
            in_comment = False
            line = line[end + 3 :]
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
        segments: list[str] = []
        rest = line
        while True:
            start = rest.find("<!--")
            if start == -1:
                segments.append(rest)
                break
            segments.append(rest[:start])
            # Search from start + 2 so the empty forms <!--> and <!---> close
            # immediately instead of swallowing the rest of the page.
            end = rest.find("-->", start + 2)
            if end == -1:
                in_comment = True
                break
            rest = rest[end + 3 :]
        visible_lines.append("".join(segments))
    return _strip_inline_code("\n".join(visible_lines))


def manifest_route_records(text: str) -> list[tuple[str, str]]:
    """Return safe routes and their visible lines after Markdown exclusions."""
    records: list[tuple[str, str]] = []
    for line in visible_markdown_text(text).splitlines():
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
    """Return real Markdown link destinations in source order.

    Comments, fenced blocks, code spans, escapes, and image links are
    excluded with the same rules the manifest parser applies, so quoted
    counter-examples never register as live links.
    """
    visible = visible_markdown_text(text)
    return [
        match.group("angle") or match.group("plain")
        for match in BODY_LINK_RE.finditer(visible)
        if _is_real_link(visible, match.start())
    ]


def resolve_canon_reference(page: Path, target: str) -> str | None:
    """Resolve a local Markdown target to a safe Canon-relative route.

    This is the single route resolver: the manifest router delegates here via
    ``normalize_route`` so routing and link checking cannot disagree.
    """
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
        or route.startswith(("../", "/"))
        or not route.endswith(".md")
    ):
        return None
    return route


def contained_regular_file(root: Path, relative: str) -> tuple[bool, str]:
    """Validate a route/source as a non-symlink regular file beneath root.

    ``relative`` is not percent-decoded here: link targets are already
    decoded exactly once by the route resolvers, and metadata paths are used
    as written (minus any URL query or fragment suffix).
    """
    root = root.resolve()
    raw = relative.strip()
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
        route
        for path in files
        if (route := path.relative_to(canon).as_posix()) != "manifest.md"
        and route not in routes
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
