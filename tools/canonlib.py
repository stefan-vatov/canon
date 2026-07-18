"""Shared, dependency-free Canon path and manifest helpers."""

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
REPO_CANON_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])canon/([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\.md)"
    r"(?![A-Za-z0-9_./-])"
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


def manifest_routes(text: str) -> set[str]:
    """Return exact safe Canon-relative routes declared by a manifest."""
    routes: set[str] = set()
    for match in MARKDOWN_LINK_RE.finditer(text):
        route = normalize_route(match.group("angle") or match.group("plain"))
        if route:
            routes.add(route)
    # Exact canon/...md path literals remain valid routing entries. A basename
    # or prose fragment cannot satisfy completeness.
    routes.update(match.group(1) for match in REPO_CANON_PATH_RE.finditer(text))
    return routes


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
        ok, detail = contained_regular_file(canon, route)
        if not ok:
            issues.append(f"{route}: {detail}")
    return issues
