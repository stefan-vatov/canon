#!/usr/bin/env python3
"""Read-only measurements of what a repository's Project Canon costs.

Reports what a one-time migration needs to decide on: files and words per
directory, decision records, front matter and stamps, how much recent commit
traffic touches canon/ and how much of it only bumps stamps, which canon
paths are cited from outside canon/, and how many words the instruction
files tell an agent to read before it starts. Nothing is written.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

WORD_RE = re.compile(r"\S+")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
STAMP_KEY_RE = re.compile(
    r"^\s*(?:sources|verified|last[_ -]?verified|status|scope|validation|"
    r"supersedes|superseded_by|related|review(?:ed)?(?:_by|_on)?)\s*:",
    re.IGNORECASE,
)
STAMP_LINE_RE = re.compile(
    r"^\s*(?:verified|last[_ -]?verified|reviewed(?:[_ ]on)?)\s*:", re.IGNORECASE
)
DECISION_NAME_RE = re.compile(r"(?:^|[-_/])(?:decisions?|adr)(?:[-_.]|$)", re.IGNORECASE)
CANON_PATH_RE = re.compile(r"canon/[A-Za-z0-9_./-]+")
INSTRUCTION_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".codex/system.md",
    ".github/copilot-instructions.md",
)
READ_CUE_RE = re.compile(r"\bread\b", re.IGNORECASE)


def git(root: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "-c", "color.ui=never", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else None


def words(path: Path) -> int:
    return len(WORD_RE.findall(path.read_text(errors="replace")))


def canon_markdown(canon: Path) -> list[Path]:
    if canon.is_symlink() or not canon.is_dir():
        return []
    return sorted(
        path
        for path in canon.rglob("*.md")
        if path.is_file()
        and not path.is_symlink()
        and path.relative_to(canon).parts[0] != "scratch"
    )


def is_decision_record(relative: Path) -> bool:
    return any(part.lower() in ("decisions", "adr", "adrs") for part in relative.parts[:-1]) or bool(
        DECISION_NAME_RE.search(relative.stem)
    )


def inventory(root: Path) -> dict[str, object]:
    canon = root / "canon"
    files = canon_markdown(canon)
    per_directory: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "words": 0})
    largest = []
    decisions = []
    front_matter = 0
    stamp_fields = Counter()
    for path in files:
        relative = path.relative_to(canon)
        directory = relative.parts[0] if len(relative.parts) > 1 else "."
        count = words(path)
        per_directory[directory]["files"] += 1
        per_directory[directory]["words"] += count
        largest.append((count, relative.as_posix()))
        if is_decision_record(relative):
            decisions.append(relative.as_posix())
        match = FRONTMATTER_RE.match(path.read_text(errors="replace"))
        if match:
            front_matter += 1
            for line in match.group(1).splitlines():
                if STAMP_KEY_RE.match(line):
                    stamp_fields[line.split(":", 1)[0].strip().lower()] += 1
    largest.sort(reverse=True)
    return {
        "files": len(files),
        "words": sum(item["words"] for item in per_directory.values()),
        "per_directory": dict(sorted(per_directory.items())),
        "largest": [{"path": path, "words": count} for count, path in largest[:10]],
        "decision_records": len(decisions),
        "front_matter_files": front_matter,
        "stamp_fields": dict(sorted(stamp_fields.items())),
    }


def churn(root: Path, days: int) -> dict[str, object] | None:
    since = f"--since={days} days ago"
    total = git(root, "rev-list", "--count", since, "HEAD")
    touching = git(root, "rev-list", "--count", since, "HEAD", "--", "canon/")
    log = git(
        root, "log", since, "--format=COMMIT %H", "--no-ext-diff", "--unified=0", "-p", "--",
        "canon/",
    )
    if total is None or touching is None or log is None:
        return None
    touches = 0
    stamp_only = 0
    current_lines: list[str] | None = None

    def close(lines: list[str] | None) -> None:
        nonlocal touches, stamp_only
        if lines is None:
            return
        touches += 1
        if lines and all(STAMP_LINE_RE.match(line[1:]) for line in lines):
            stamp_only += 1

    for line in log.splitlines():
        if line.startswith(("COMMIT ", "diff --git ")):
            close(current_lines)
            current_lines = [] if line.startswith("diff --git ") else None
        elif current_lines is not None and line[:1] in "+-" and not line.startswith(("+++", "---")):
            current_lines.append(line)
    close(current_lines)
    total_count = int(total.strip() or 0)
    touching_count = int(touching.strip() or 0)
    return {
        "days": days,
        "commits": total_count,
        "commits_touching_canon": touching_count,
        "canon_file_touches": touches,
        "stamp_only_touches": stamp_only,
    }


def inbound_references(root: Path) -> dict[str, object] | None:
    output = git(root, "grep", "-I", "-n", "-o", "-E", r"canon/[A-Za-z0-9_./-]+", "--", ".", ":!canon")
    if output is None:
        # git grep exits 1 when nothing matches; distinguish that from no repository.
        return None if git(root, "rev-parse", "--git-dir") is None else {"files": 0, "targets": {}}
    targets = Counter()
    citing_files = set()
    for line in output.splitlines():
        path, _, rest = line.partition(":")
        _, _, match = rest.partition(":")
        target = match.rstrip(".,;:)`'\"")
        if target in ("canon/", "canon/scratch/") or target.startswith("canon/scratch"):
            continue
        targets[target] += 1
        citing_files.add(path)
    return {
        "files": len(citing_files),
        "targets": dict(targets.most_common(25)),
    }


def startup_reads(root: Path) -> dict[str, object]:
    instruction_words = 0
    named = set()
    present = []
    for name in INSTRUCTION_FILES:
        path = root / name
        if not path.is_file() or path.is_symlink():
            continue
        present.append(name)
        text = path.read_text(errors="replace")
        instruction_words += len(WORD_RE.findall(text))
        for line in text.splitlines():
            if READ_CUE_RE.search(line):
                for match in CANON_PATH_RE.findall(line):
                    candidate = root / match.rstrip(".,;:)`'\"")
                    if candidate.is_file() and candidate.suffix == ".md":
                        named.add(candidate.relative_to(root).as_posix())
    named_words = sum(words(root / path) for path in named)
    return {
        "instruction_files": present,
        "instruction_words": instruction_words,
        "canon_files_named_with_read": sorted(named),
        "canon_words_named_with_read": named_words,
    }


def analyze(root: Path, days: int) -> dict[str, object]:
    return {
        "root": str(root),
        "canon": inventory(root),
        "churn": churn(root, days),
        "inbound_references": inbound_references(root),
        "startup": startup_reads(root),
    }


def print_text(report: dict[str, object]) -> None:
    canon = report["canon"]
    print(f"canon/: {canon['files']} files, {canon['words']} words")
    for directory, row in canon["per_directory"].items():
        print(f"  {directory}: {row['files']} files, {row['words']} words")
    print(f"decision records: {canon['decision_records']}")
    print(f"files with front matter: {canon['front_matter_files']}")
    for field, count in canon["stamp_fields"].items():
        print(f"  {field}: {count}")
    print("largest notes:")
    for row in canon["largest"]:
        print(f"  {row['words']:>7}  {row['path']}")
    history = report["churn"]
    if history is None:
        print("churn: not a git repository")
    else:
        print(
            f"last {history['days']} days: {history['commits_touching_canon']} of "
            f"{history['commits']} commits touched canon/; {history['stamp_only_touches']} of "
            f"{history['canon_file_touches']} canon file touches changed only stamps"
        )
    inbound = report["inbound_references"]
    if inbound is not None:
        print(f"files outside canon/ citing canon paths: {inbound['files']}")
        for target, count in inbound["targets"].items():
            print(f"  {count:>5}  {target}")
    startup = report["startup"]
    print(
        f"instruction files: {', '.join(startup['instruction_files']) or 'none'} "
        f"({startup['instruction_words']} words)"
    )
    print(
        f"canon files named next to 'read': {len(startup['canon_files_named_with_read'])} "
        f"({startup['canon_words_named_with_read']} words)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument("--days", type=int, default=30, help="churn window in days (default: 30)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = analyze(Path(args.root).resolve(), args.days)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
