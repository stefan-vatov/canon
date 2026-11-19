#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""Mechanical checks for a completed eval run.

Reads the scenario's expected.json and the post-run workspace, emits
checks.json with one pass/fail entry per check. Checks:

  required_files        files that must exist after the run
  tests_pass            the fixture's test_cmd exits 0
  diff_scope            every changed file matches allowed_change_globs
  rules                 per-scenario file-count and content rules
                        (min_matching_files / max_matching_files /
                        must_regex / forbid_regex, narrowed by exclude_globs;
                        search_commit_messages lets must_regex also match
                        commit messages written after the baseline)
  answer                the session's final answer matches a regex (a
                        recommendation, an abstention)
  routing_precision     which canon notes the agent read, from structured
                        transcript telemetry
  holdout_pass          hidden tests the agent never saw, copied in from the
                        scenario dir at scoring time, run, then removed; they
                        encode requirements stated in earlier sessions
"""
import argparse
import ast
import fnmatch
import hashlib
import hmac
import io
import json
import os
import platform
import posixpath
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import tokenize
from pathlib import Path
from urllib.parse import urlsplit

PYTHON_FLOAT_LITERAL_RE = re.compile(
    r"(?:"
    r"(?:\d[\d_]*\.[\d_]*|\.[\d_]+)(?:[eE][+-]?[\d_]+)?"
    r"|"
    r"\d[\d_]*[eE][+-]?[\d_]+"
    r")(?:[jJ])?\Z"
)


def git(workdir, *args):
    return subprocess.run(
        ["git", "-C", str(workdir), *args],
        capture_output=True, text=True, check=True,
    ).stdout


def contained_regular_file(root, relative):
    """Validate a path as a non-symlink regular file beneath root."""
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
            return False, "symlinked paths are not valid evidence"
    if not resolved.is_file():
        return False, "path is not a regular file"
    return True, ""


def changed_files(workdir, baseline):
    if baseline:
        git(workdir, "cat-file", "-e", f"{baseline}^{{commit}}")
    else:
        baseline = "HEAD"
    subprocess.run(["git", "-C", str(workdir), "add", "-A"],
                   capture_output=True, check=True)
    out = git(workdir, "diff", "--cached", "--name-only", baseline)
    return [line for line in out.splitlines() if line.strip()]


def final_answer(transcript):
    """Return the agent's final answer from one session transcript, or ""."""
    path = Path(transcript) if transcript else None
    if path is None or not path.is_file():
        return ""
    text = path.read_text(errors="replace")
    answer, saw_json = "", False
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw.startswith("{"):
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        saw_json = True
        if event.get("type") == "result" and isinstance(event.get("result"), str):
            answer = event["result"]
        elif event.get("type") == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                answer = item["text"]
        elif event.get("type") == "assistant":
            content = event.get("message", {}).get("content", [])
            texts = [b.get("text", "") for b in content
                     if isinstance(b, dict) and b.get("type") == "text"]
            if any(t.strip() for t in texts):
                answer = "\n".join(texts)
    return answer if saw_json else text[-4000:]


def commit_messages_since(workdir, baseline):
    """Commit messages the agent wrote after the baseline, or "" without one."""
    if not baseline:
        return ""
    result = subprocess.run(
        ["git", "-C", str(workdir), "log", "--format=%B", f"{baseline}..HEAD"],
        capture_output=True, text=True, check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def selected_files(workdir, glob, excluded=()):
    """Files matching glob, minus any matching one of the excluded globs."""
    return [
        path for path in matching_files(workdir, glob)
        if not any(fnmatch.fnmatch(str(path.relative_to(workdir)), g) for g in excluded)
    ]


def matching_files(workdir, glob):
    return sorted(
        p for p in workdir.rglob("*")
        if p.is_file()
        and not p.is_symlink()
        and ".git" not in p.relative_to(workdir).parts
        and fnmatch.fnmatch(str(p.relative_to(workdir)), glob)
    )


def python_float_signals(text):
    """Return lexical float use without treating comments or strings as code."""
    signals = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        for token in tokens:
            if token.type == tokenize.NAME and token.string == "float":
                signals.append(f"line {token.start[0]}: float")
            elif (
                token.type == tokenize.NUMBER
                and (
                    PYTHON_FLOAT_LITERAL_RE.fullmatch(token.string)
                    or token.string.lower().endswith("j")
                )
            ):
                signals.append(f"line {token.start[0]}: {token.string}")
    except (IndentationError, tokenize.TokenError) as exc:
        signals.append(f"unparseable Python: {exc}")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        signals.append(f"unparseable Python: {exc}")
    else:
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.BinOp, ast.AugAssign))
                and isinstance(node.op, ast.Div)
            ):
                signals.append(f"line {node.lineno}: true division")
    return signals


def has_python_public_binding(text, name):
    """Return whether a module binds ``name`` at top level."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                return True
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                bound_name = alias.asname or alias.name
                if bound_name == name:
                    return True
    return False


CANON_READERS = {
    "cat", "sed", "head", "tail", "rg", "grep", "egrep", "fgrep", "find",
    "awk", "less", "more", "nl", "bat", "view", "strings", "xxd", "od", "wc",
}
# Readers whose first positional argument is a pattern or program, not a file.
PATTERN_FIRST = {"rg", "grep", "egrep", "fgrep", "awk", "sed"}
SHELLS = {"bash", "sh", "zsh", "dash"}
SEGMENT_SPLIT = {"&&", "||", ";", "|", "&"}
PREFIX_WORDS = {"rtk", "sudo", "command", "env", "xargs", "time", "nice", "do", "then", "else"}


def canon_relative(raw, workdir, cwd="."):
    """Resolve a path argument against the workspace; return ``canon/...`` or None.

    ``cwd`` is the command's working directory relative to the workspace. An
    absolute path counts only if it lies inside the workspace's own canon/;
    a parent directory that happens to be called canon is not Canon.
    """
    raw = str(raw).strip().strip("'\"").replace("\\", "/")
    if not raw or raw.startswith("-") or "$" in raw:
        return None
    if raw.startswith("/") or raw.startswith("~"):
        if workdir is None or raw.startswith("~"):
            return None
        rel = os.path.relpath(raw, str(workdir))
    else:
        rel = os.path.normpath(os.path.join(cwd, raw))
    rel = rel.replace(os.sep, "/")
    if rel == ".." or rel.startswith("../"):
        return None
    if rel == "canon":
        return "canon/"
    if rel.startswith("canon/"):
        return rel
    return None


def is_canon_ancestor(raw, workdir, cwd="."):
    """Whether a path is the workspace root (or another ancestor of canon/)."""
    raw = str(raw).strip().strip("'\"") or "."
    if raw.startswith("/"):
        if workdir is None:
            return False
        rel = os.path.relpath(raw, str(workdir))
    else:
        rel = os.path.normpath(os.path.join(cwd, raw))
    return rel.replace(os.sep, "/") == "."


def expand_canon_target(target, workdir):
    """Expand a canon/ directory or glob into the notes it reads."""
    if target.endswith(".md") and not any(ch in target for ch in "*?["):
        return [target]
    pattern = target.rstrip("/")
    if not any(ch in pattern for ch in "*?["):
        pattern = pattern + "/*"
    notes = []
    if workdir is not None and (workdir / "canon").is_dir():
        for path in sorted((workdir / "canon").rglob("*.md")):
            rel = path.relative_to(workdir).as_posix()
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(rel, pattern + ".md"):
                notes.append(rel)
    return notes or [target]


def shell_segments(command):
    """Split a command into (argv, piped) pairs, unwrapping ``bash -lc '...'``.

    ``piped`` is true when the segment reads the previous segment's output.
    Subshell and group punctuation is dropped, so ``(cd canon && cat x.md)``
    still yields its commands in order.
    """
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()")
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    segments, current, piped, next_piped = [], [], False, False
    for token in tokens:
        if token in ("(", ")", "{", "}"):
            continue
        if token in SEGMENT_SPLIT or token in (";;", "|&"):
            if current:
                segments.append((current, piped))
            current, piped = [], token in ("|", "|&")
            next_piped = piped
        else:
            if not current:
                piped = next_piped
            current.append(token)
    if current:
        segments.append((current, piped))
    expanded = []
    for argv, piped in segments:
        name = Path(argv[0]).name if argv else ""
        if name in SHELLS and len(argv) >= 3 and argv[1].startswith("-") and "c" in argv[1]:
            expanded.extend(shell_segments(argv[2]))
        else:
            expanded.append((argv, piped))
    return expanded


def canon_targets_in_command(command, workdir=None):
    """Return canon/ paths, directories or globs a shell command reads."""
    targets, cwd, loop_items = [], ".", []
    for argv, piped in shell_segments(command):
        while argv and ("=" in argv[0] and not argv[0].startswith("-")):
            argv = argv[1:]  # leading VAR=value assignments
        while argv and Path(argv[0]).name in PREFIX_WORDS:
            argv = argv[1:]
        if not argv:
            continue
        reader = Path(argv[0]).name
        if reader == "cd":
            dest = argv[1] if len(argv) > 1 else "."
            if dest.startswith("/") and workdir is not None:
                dest = os.path.relpath(dest, str(workdir))
            cwd = os.path.normpath(os.path.join(cwd, dest)).replace(os.sep, "/")
            continue
        if reader == "for" and "in" in argv:
            for item in argv[argv.index("in") + 1:]:
                target = canon_relative(item, workdir, cwd)
                if target:
                    loop_items.append(target)
            continue
        if reader not in CANON_READERS:
            continue
        if loop_items and any("$" in arg for arg in argv[1:]):
            targets.extend(loop_items)
        positionals, explicit_pattern, recursive, executes = [], False, False, False
        for arg in argv[1:]:
            if arg in ("-e", "--regexp", "-f", "--file"):
                explicit_pattern = True
            if arg in ("-r", "-R", "--recursive") or (
                arg.startswith("-") and not arg.startswith("--") and ("r" in arg or "R" in arg)
                and reader in ("grep", "egrep", "fgrep")
            ):
                recursive = True
            if arg in ("-exec", "-execdir", "-ok", "-okdir"):
                executes = True
            if arg.startswith("-"):
                continue
            positionals.append(arg)
        if reader == "find":
            if not executes:
                continue  # a listing, like ls
            paths = positionals[:1] if positionals else ["."]
            recursive = True
        elif reader in PATTERN_FIRST and not explicit_pattern:
            paths = positionals[1:]
        else:
            paths = positionals
        if reader == "rg":
            recursive = True
            if not paths and not piped:
                paths = ["."]
        elif reader in ("grep", "egrep", "fgrep") and recursive and not paths and not piped:
            paths = ["."]
        if cwd == "canon" or cwd.startswith("canon/"):
            if not paths and not piped and reader not in PATTERN_FIRST:
                paths = ["."]
        for arg in paths:
            target = canon_relative(arg, workdir, cwd)
            if target:
                targets.append(target)
            elif recursive and is_canon_ancestor(arg, workdir, cwd) and (
                workdir is None or (workdir / "canon").is_dir()
            ):
                targets.append("canon/")
    return targets


def canon_reads_from_transcripts(transcript_dir, workdir=None):
    """Return ordered successful Canon reads and whether telemetry is supported.

    Telemetry is supported as soon as any structured tool event parses, so a
    session with zero Canon reads is a measured zero, not an unknown. A tool
    request counts as a read only after a matching, non-error result.
    """
    requested, successful = {}, []
    supported = False
    tdir = Path(transcript_dir)
    if not tdir.is_dir():
        return successful, False

    def record(targets):
        for target in targets:
            successful.extend(expand_canon_target(target, workdir))

    for tf in sorted(tdir.glob("transcript*.txt")):
        for raw in tf.read_text(errors="replace").splitlines():
            raw = raw.strip()
            if not raw.startswith("{"):
                continue
            try:
                e = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(e, dict):
                continue
            if e.get("type") == "item.completed":
                item = e.get("item", {})
                if item.get("type") == "command_execution":
                    supported = True
                    if item.get("exit_code") == 0:
                        record(canon_targets_in_command(str(item.get("command", "")), workdir))
            message = e.get("message", {})
            content = message.get("content", []) if isinstance(message, dict) else []
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    supported = True
                    name, inp = b.get("name"), b.get("input", {}) or {}
                    targets = []
                    if name == "Read":
                        target = canon_relative(inp.get("file_path", ""), workdir)
                        targets = [target] if target else []
                    elif name == "Grep":
                        path = inp.get("path") or "."
                        target = canon_relative(path, workdir)
                        if target is None and is_canon_ancestor(path, workdir) and (
                            workdir is not None and (workdir / "canon").is_dir()
                        ):
                            target = "canon/"
                        glob = inp.get("glob")
                        if glob and not fnmatch.fnmatch("note.md", Path(glob).name):
                            target = None  # a search restricted to non-Markdown files
                        if inp.get("type") and inp.get("type") not in ("md", "markdown"):
                            target = None
                        if target:
                            if glob and target == "canon/":
                                target = "canon/" + glob.lstrip("/")
                            targets = [target]
                    elif name == "Bash":
                        targets = canon_targets_in_command(str(inp.get("command", "")), workdir)
                    # Glob lists files like `ls`; listing canon/ is allowed.
                    if targets and b.get("id"):
                        requested[b["id"]] = targets
                elif b.get("type") == "tool_result":
                    targets = requested.pop(b.get("tool_use_id"), None)
                    if targets and not b.get("is_error", False):
                        record(targets)
    return successful, supported


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_signature(payload, key):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(key.encode(), encoded, hashlib.sha256).hexdigest()


STATE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\Z")


def state_artifact_path(state_dir, state_id):
    """Return a contained artifact path for a safe, single-component state ID."""
    if not isinstance(state_id, str) or not STATE_ID_RE.fullmatch(state_id):
        raise ValueError(
            "state ID must contain only ASCII letters, digits, underscores, and hyphens"
        )
    path = state_dir / f"{state_id}.json"
    try:
        path.relative_to(state_dir)
    except ValueError as exc:
        raise ValueError("state artifact resolves outside the state directory") from exc
    return path


def read_state_artifact(path):
    """Read an existing regular state file without following a symlink."""
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise OSError("state artifact is not a regular non-symlink file")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(fd)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
        ):
            raise OSError("state artifact changed while opening")
        with os.fdopen(fd, encoding="utf-8") as handle:
            fd = -1
            return handle.read()
    finally:
        if fd >= 0:
            os.close(fd)


def write_state_artifact(path, text):
    """Write a regular state file without following a pre-existing symlink."""
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise OSError("state artifact is not a regular non-symlink file")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("state artifact is not a regular file")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(text)
    finally:
        if fd >= 0:
            os.close(fd)


def safe_copy_workspace(source, destination):
    """Copy a workspace without following any agent-controlled symlink."""
    for path in source.rglob("*"):
        rel = path.relative_to(source)
        if ".git" in rel.parts or "__pycache__" in rel.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError(f"workspace symlink is not allowed in holdout execution: {rel}")
        target = destination / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def run_test(command, workdir, timeout=300):
    """Run agent-controlled code with a deny-network macOS sandbox by default.

    Other platforms must provide ``CANON_EVAL_SANDBOX_CMD`` (use ``{command}``
    and ``{workdir}`` placeholders) or explicitly opt in to unsafe host
    execution with ``CANON_EVAL_ALLOW_HOST_EXECUTION=1``.
    """
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    wrapper = os.environ.get("CANON_EVAL_SANDBOX_CMD")
    if wrapper:
        rendered = wrapper.format(command=command, workdir=str(workdir))
        return subprocess.run(rendered, shell=True, cwd=workdir, capture_output=True,
                              text=True, timeout=timeout, env=env)
    if platform.system() == "Darwin" and Path("/usr/bin/sandbox-exec").is_file():
        with tempfile.TemporaryDirectory(prefix="canon-eval-runtime-") as directory:
            sandbox_tmp = Path(directory)
            env.update(TMPDIR=str(sandbox_tmp), UV_CACHE_DIR=str(sandbox_tmp / "uv-cache"))
            home = str(Path.home())
            profile = "\n".join([
                "(version 1)",
                "(allow default)",
                "(deny network*)",
                f'(deny file-write* (subpath "{home}"))',
                f'(allow file-write* (subpath "{workdir}"))',
                f'(allow file-write* (subpath "{sandbox_tmp}"))',
            ])
            return subprocess.run(
                ["/usr/bin/sandbox-exec", "-p", profile, "/bin/sh", "-c", command],
                cwd=workdir, capture_output=True, text=True, timeout=timeout, env=env,
            )
    if os.environ.get("CANON_EVAL_ALLOW_HOST_EXECUTION") == "1":
        return subprocess.run(command, shell=True, cwd=workdir, capture_output=True,
                              text=True, timeout=timeout, env=env)
    raise RuntimeError(
        "no evaluator sandbox configured; set CANON_EVAL_SANDBOX_CMD or explicitly "
        "set CANON_EVAL_ALLOW_HOST_EXECUTION=1"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--expected", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--answer-transcript", default=None,
                    help="transcript of the session just checked, for answer rules")
    ap.add_argument("--transcript-dir", default=None,
                    help="dir holding transcript*.txt, for routing checks")
    ap.add_argument("--baseline", default=None,
                    help="immutable baseline commit captured before agent execution")
    ap.add_argument("--state-dir", default=None,
                    help="evaluator-only temporal snapshot directory")
    ap.add_argument("--state-key", default=None,
                    help="ephemeral HMAC key for temporal snapshots")
    args = ap.parse_args()

    work = Path(args.workdir).resolve()
    expected_path = Path(args.expected).resolve()
    expected = json.loads(expected_path.read_text())
    changed = changed_files(work, args.baseline)
    checks = []

    def add(check_id, ok, detail="", outcome=None, required=False):
        checks.append({
            "id": check_id,
            "pass": bool(ok),
            "outcome": outcome or ("pass" if ok else "fail"),
            "required": bool(required),
            "detail": detail,
        })

    for rel in expected.get("required_files", []):
        safe, detail = contained_regular_file(work, rel)
        add(f"required:{rel}", safe, detail if not safe else "", required=True)

    test_cmd = expected.get("test_cmd")
    if test_cmd:
        try:
            proc = run_test(test_cmd, work)
            add("tests_pass", proc.returncode == 0,
                "" if proc.returncode == 0 else (proc.stderr or proc.stdout)[-500:],
                required=True)
        except subprocess.TimeoutExpired:
            add("tests_pass", False, "test_cmd timed out", required=True)
        except RuntimeError as exc:
            add("tests_pass", False, str(exc), required=True)

    globs = expected.get("allowed_change_globs")
    if globs is not None:
        out_of_scope = [
            f for f in changed
            if not any(fnmatch.fnmatch(f, g) for g in globs)
        ]
        add(
            "diff_scope",
            not out_of_scope,
            ", ".join(out_of_scope),
            required=bool(expected.get("diff_scope_required", False)),
        )

    commit_messages = None
    answer_text = final_answer(args.answer_transcript)
    for rule in expected.get("rules", []):
        files = selected_files(work, rule["glob"], rule.get("exclude_globs", []))
        contents = {p: p.read_text(errors="replace") for p in files}
        ok, detail = True, ""
        if rule.get("min_matching_files") is not None:
            minimum = rule["min_matching_files"]
            ok = len(files) >= minimum
            if not ok:
                detail = (f"{len(files)} files match {rule['glob']}; "
                          f"need at least {minimum}")
        if ok and rule.get("max_matching_files") is not None:
            maximum = rule["max_matching_files"]
            ok = len(files) <= maximum
            if not ok:
                detail = (f"{len(files)} files match {rule['glob']}; "
                          f"allow at most {maximum}")
        if ok and rule.get("must_regex"):
            ok = any(re.search(rule["must_regex"], c) for c in contents.values())
            if not ok and rule.get("search_commit_messages"):
                if commit_messages is None:
                    # A harness whose sandbox forbids commits (Codex keeps .git
                    # read-only) gets credit for the message it proposes.
                    transcripts = sorted(Path(args.transcript_dir).glob("transcript-*.txt")) \
                        if args.transcript_dir else []
                    proposed = "\n".join(final_answer(t) for t in transcripts)
                    commit_messages = (commit_messages_since(work, args.baseline)
                                       + "\n" + proposed + "\n" + answer_text)
                ok = bool(re.search(rule["must_regex"], commit_messages))
            if not ok:
                where = (" or a commit message (made or proposed)"
                         if rule.get("search_commit_messages") else "")
                detail = (f"no file matching {rule['glob']}{where} "
                          f"contains /{rule['must_regex']}/")
        if ok and rule.get("forbid_regex"):
            hits = [str(p.relative_to(work)) for p, c in contents.items()
                    if re.search(rule["forbid_regex"], c)]
            ok = not hits
            detail = f"/{rule['forbid_regex']}/ found in: {', '.join(hits)}" if hits else ""
        if ok and rule.get("forbid_python_floats"):
            hits = {}
            for path, content in contents.items():
                signals = python_float_signals(content)
                if signals:
                    hits[str(path.relative_to(work))] = signals
            ok = not hits
            if hits:
                detail = "Python float use found: " + "; ".join(
                    f"{path} ({', '.join(signals)})"
                    for path, signals in hits.items()
                )
        if ok and rule.get("python_public_binding"):
            name = rule["python_public_binding"]
            ok = any(has_python_public_binding(content, name) for content in contents.values())
            if not ok:
                detail = f"no file matching {rule['glob']} binds public name {name!r}"
        add(
            f"rule:{rule['id']}",
            ok,
            detail or rule.get("description", ""),
            required=bool(rule.get("required", True)),
        )

    answer = expected.get("answer")
    if answer:
        ok = bool(answer_text.strip()) and bool(re.search(answer["must_regex"], answer_text))
        add(
            "answer",
            ok,
            "" if ok else (answer.get("description") or
                           f"final answer does not match /{answer['must_regex']}/"),
            required=bool(answer.get("required", True)),
        )

    state_dir = Path(args.state_dir).resolve() if args.state_dir else None
    state_key = args.state_key
    for spec in expected.get("preserve", []):
        state_id = spec.get("snapshot")
        check_id = f"preserve:{state_id}"
        try:
            if state_dir is None:
                # Validate expected-controlled IDs even when temporal state is unavailable.
                state_artifact_path(Path("."), state_id)
                snapshot_path = None
            else:
                snapshot_path = state_artifact_path(state_dir, state_id)
        except ValueError as exc:
            add(check_id, False, str(exc), required=True)
            continue
        if not state_dir or not state_key:
            add(check_id, False, "authenticated temporal state is unavailable", required=True)
            continue
        try:
            envelope = json.loads(read_state_artifact(snapshot_path))
            payload = envelope["payload"]
            valid_signature = hmac.compare_digest(
                envelope["hmac_sha256"], snapshot_signature(payload, state_key)
            )
        except (OSError, KeyError, TypeError, UnicodeError, json.JSONDecodeError):
            add(check_id, False, "snapshot is missing or corrupt", required=True)
            continue
        if not valid_signature:
            add(check_id, False, "snapshot authentication failed", required=True)
            continue
        glob = spec.get("glob", payload["glob"])
        current = {
            str(path.relative_to(work)): file_digest(path)
            for path in selected_files(work, glob, payload.get("exclude_globs", []))
        }
        original = payload["files"]
        missing = sorted(set(original) - set(current))
        modified = sorted(path for path in original if current.get(path) != original[path])
        added = sorted(set(current) - set(original)) if spec.get("exact_set", False) else []
        problems = []
        if missing:
            problems.append(f"missing: {', '.join(missing)}")
        if modified:
            problems.append(f"modified: {', '.join(modified)}")
        if added:
            problems.append(f"unexpected: {', '.join(added)}")
        add(check_id, not problems, "; ".join(problems), required=True)

    for spec in expected.get("capture", []):
        state_id = spec.get("id")
        check_id = f"capture:{state_id}"
        try:
            if state_dir is None:
                state_artifact_path(Path("."), state_id)
                snapshot_path = None
            else:
                snapshot_path = state_artifact_path(state_dir, state_id)
        except ValueError as exc:
            add(check_id, False, str(exc), required=True)
            continue
        if not state_dir or not state_key:
            add(check_id, False, "authenticated temporal state is unavailable", required=True)
            continue
        files = selected_files(work, spec["glob"], spec.get("exclude_globs", []))
        contents = {path: path.read_text(errors="replace") for path in files}
        problems = []
        exact = spec.get("exact_count")
        if exact is not None and len(files) != exact:
            problems.append(f"{len(files)} files match; require exactly {exact}")
        must_regex = spec.get("must_regex")
        if must_regex and not any(re.search(must_regex, text) for text in contents.values()):
            problems.append(f"no captured file contains /{must_regex}/")
        if not files:
            problems.append("no files matched")
        if problems:
            add(check_id, False, "; ".join(problems), required=True)
            continue
        payload = {
            "glob": spec["glob"],
            "exclude_globs": list(spec.get("exclude_globs", [])),
            "files": {str(path.relative_to(work)): file_digest(path) for path in files},
        }
        envelope = {
            "payload": payload,
            "hmac_sha256": snapshot_signature(payload, state_key),
        }
        try:
            state_dir.mkdir(parents=True, exist_ok=True)
            if state_dir.is_symlink() or not state_dir.is_dir():
                raise OSError("state directory is not a regular directory")
            write_state_artifact(
                snapshot_path, json.dumps(envelope, indent=2, sort_keys=True) + "\n"
            )
        except OSError as exc:
            add(check_id, False, f"state artifact is unsafe: {exc}", required=True)
            continue
        add(check_id, True, f"captured {len(files)} file(s)", required=True)

    # Routing precision: did the agent read the right Canon doc and avoid
    # bulk-loading sibling domains? Isolates retrieval/routing from
    # correctness (LongMemEval Oracle idea). Score only adapters for which
    # successful structured read telemetry is supported; otherwise record an
    # explicit unsupported outcome rather than a pass or failure.
    routing = expected.get("routing")
    if routing and args.transcript_dir:
        reads, supported = canon_reads_from_transcripts(args.transcript_dir, work)
        if not supported:
            # Routing is a required check: without telemetry it cannot pass.
            # A scenario may opt out with "require_telemetry": false.
            required = routing.get("require_telemetry", True)
            add("routing_precision", False,
                "structured tool telemetry is unsupported",
                outcome="fail" if required else "unsupported",
                required=bool(required))
        else:
            domain_glob = routing.get("domain_glob", "canon/*.md")
            domain_reads = sorted({r for r in reads if fnmatch.fnmatch(r, domain_glob)})
            must = routing.get("must_read", [])
            missing = [m for m in must if m not in reads]
            max_domains = routing.get("max_domain_reads", 2)
            ok = not missing and len(domain_reads) <= max_domains
            order = ", ".join(reads) if reads else "none"
            if missing:
                detail = f"never read required: {', '.join(missing)}; reads in order: {order}"
            elif len(domain_reads) > max_domains:
                detail = (f"read {len(domain_reads)} Canon notes "
                          f"(max {max_domains}); reads in order: {order}")
            else:
                detail = f"reads in order: {order}"
            add("routing_precision", ok, detail, required=True)

    holdout = expected.get("holdout")
    if holdout:
        src = expected_path.parent / holdout["dir"]
        try:
            with tempfile.TemporaryDirectory(prefix="canon-holdout-") as directory:
                isolated = Path(directory) / "workspace"
                isolated.mkdir()
                safe_copy_workspace(work, isolated)
                collision = None
                for source in sorted(path for path in src.rglob("*") if path.is_file()):
                    if source.is_symlink():
                        collision = f"holdout contains a symlink: {source.relative_to(src)}"
                        break
                    destination = isolated / source.relative_to(src)
                    if destination.exists() or destination.is_symlink():
                        collision = f"holdout would clobber {destination.relative_to(isolated)}"
                        break
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
                if collision:
                    add("holdout_pass", False, collision, required=True)
                else:
                    try:
                        proc = run_test(holdout["test_cmd"], isolated)
                        add("holdout_pass", proc.returncode == 0,
                            "" if proc.returncode == 0
                            else (proc.stderr or proc.stdout)[-500:], required=True)
                    except subprocess.TimeoutExpired:
                        add("holdout_pass", False, "holdout test_cmd timed out", required=True)
                    except RuntimeError as exc:
                        add("holdout_pass", False, str(exc), required=True)
        except ValueError as exc:
            add("holdout_pass", False, str(exc), required=True)

    measured = [check for check in checks if check["outcome"] in ("pass", "fail")]
    passed = sum(1 for check in measured if check["outcome"] == "pass")
    result = {
        "schema_version": 2,
        "passed": passed,
        "total": len(measured),
        "unsupported": sum(1 for check in checks if check["outcome"] == "unsupported"),
        "score": round(passed / len(measured), 3) if measured else None,
        "required_pass": all(
            check["outcome"] == "pass" for check in checks if check["required"]
        ),
        "checks": checks,
    }
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    print(f"mechanical: {passed}/{len(measured)} ({result['unsupported']} unsupported)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
