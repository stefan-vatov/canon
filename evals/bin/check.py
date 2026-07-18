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
  rules                 per-scenario file-count and content rules
                        (min_matching_files / must_regex / forbid_regex)
  holdout_pass          hidden tests the agent never saw, copied in from the
                        scenario dir at scoring time, run, then removed; they
                        encode requirements stated in earlier sessions
"""
import argparse
import fnmatch
import hashlib
import hmac
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from canonlib import (  # noqa: E402
    contained_regular_file,
    manifest_route_issues,
    missing_manifest_routes,
)


def git(workdir, *args):
    return subprocess.run(
        ["git", "-C", str(workdir), *args],
        capture_output=True, text=True, check=True,
    ).stdout


def changed_files(workdir, baseline):
    if baseline:
        git(workdir, "cat-file", "-e", f"{baseline}^{{commit}}")
    else:
        baseline = "HEAD"
    subprocess.run(["git", "-C", str(workdir), "add", "-A"],
                   capture_output=True, check=True)
    out = git(workdir, "diff", "--cached", "--name-only", baseline)
    return [line for line in out.splitlines() if line.strip()]


def permanent_canon_files(workdir):
    canon = workdir / "canon"
    if not canon.is_dir():
        return []
    return sorted(
        p for p in canon.rglob("*.md")
        if "scratch" not in p.relative_to(canon).parts
        and not p.is_symlink()
    )


def matching_files(workdir, glob):
    return sorted(
        p for p in workdir.rglob("*")
        if p.is_file()
        and not p.is_symlink()
        and ".git" not in p.relative_to(workdir).parts
        and fnmatch.fnmatch(str(p.relative_to(workdir)), glob)
    )


def _canon_transcript_path(raw):
    raw = str(raw).replace("\\", "/")
    marker = raw.rfind("/canon/")
    candidate = raw[marker + 1:] if marker >= 0 else raw
    if not candidate.startswith("canon/"):
        return None
    parts = Path(candidate).parts
    if ".." in parts or len(parts) < 2 or not candidate.endswith(".md"):
        return None
    return "/".join(parts)


def canon_reads_from_transcripts(transcript_dir):
    """Return successful structured Canon reads and telemetry support.

    A tool request is not evidence of a read. It counts only after a matching,
    non-error tool result appears in the structured transcript.
    """
    requested, successful = {}, []
    saw_structured_result = False
    tdir = Path(transcript_dir)
    if not tdir.is_dir():
        return successful, False
    for tf in sorted(tdir.glob("transcript*.txt")):
        for raw in tf.read_text(errors="replace").splitlines():
            raw = raw.strip()
            if not raw.startswith("{"):
                continue
            try:
                e = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if e.get("type") == "item.completed":
                item = e.get("item", {})
                if item.get("type") == "command_execution":
                    saw_structured_result = True
                    command = str(item.get("command", ""))
                    exit_code = item.get("exit_code")
                    first = command.strip().split(maxsplit=2)
                    reader = first[0] if first else ""
                    if reader == "rtk" and len(first) > 1:
                        reader = first[1]
                    if exit_code == 0 and reader in ("cat", "sed", "head", "tail"):
                        for match in re.finditer(
                            r"(?<![A-Za-z0-9_./-])(canon/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\.md)"
                            r"(?![A-Za-z0-9_./-])",
                            command,
                        ):
                            successful.append(match.group(1))
            for b in e.get("message", {}).get("content", []):
                if b.get("type") == "tool_use" and b.get("name") == "Read":
                    path = _canon_transcript_path(b.get("input", {}).get("file_path", ""))
                    if path and b.get("id"):
                        requested[b["id"]] = path
                elif b.get("type") == "tool_result":
                    saw_structured_result = True
                    path = requested.get(b.get("tool_use_id"))
                    if path and not b.get("is_error", False):
                        successful.append(path)
    return successful, saw_structured_result


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

    canon_files = permanent_canon_files(work)
    manifest = work / "canon" / "manifest.md"
    if manifest.is_file():
        text = manifest.read_text()
        missing = missing_manifest_routes(canon_files, work / "canon", text)
        add("manifest_complete", not missing,
            f"not referenced: {', '.join(missing)}" if missing else "", required=True)
        route_issues = manifest_route_issues(work / "canon", text)
        add("manifest_routes_safe", not route_issues, "; ".join(route_issues), required=True)
    elif (work / "canon").is_dir():
        add("manifest_complete", False, "canon/ exists but manifest.md missing", required=True)

    max_lines = expected.get("max_canon_lines", 250)
    too_long = [
        f"{p.relative_to(work)} ({n})"
        for p in canon_files
        if (n := len(p.read_text().splitlines())) > max_lines
    ]
    if canon_files:
        add("canon_line_limits", not too_long, ", ".join(too_long))
    max_bytes = expected.get("max_canon_bytes", 64 * 1024)
    too_large = [
        f"{path.relative_to(work)} ({path.stat().st_size})"
        for path in canon_files if path.stat().st_size > max_bytes
    ]
    if canon_files:
        add("canon_size_limits", not too_large, ", ".join(too_large))

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
            if not ok:
                detail = f"no file matching {rule['glob']} contains /{rule['must_regex']}/"
        if ok and rule.get("forbid_regex"):
            hits = [str(p.relative_to(work)) for p, c in contents.items()
                    if re.search(rule["forbid_regex"], c)]
            ok = not hits
            detail = f"/{rule['forbid_regex']}/ found in: {', '.join(hits)}" if hits else ""
        add(f"rule:{rule['id']}", ok, detail or rule.get("description", ""))

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
            for path in matching_files(work, glob)
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
        files = matching_files(work, spec["glob"])
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
        reads, supported = canon_reads_from_transcripts(args.transcript_dir)
        if not supported:
            add("routing_precision", False,
                "structured successful-read telemetry is unsupported",
                outcome="unsupported")
        else:
            domain_glob = routing.get("domain_glob", "canon/*/overview.md")
            domain_reads = sorted({r for r in reads if fnmatch.fnmatch(r, domain_glob)})
            must = routing.get("must_read", [])
            missing = [m for m in must if m not in reads]
            max_domains = routing.get("max_domain_reads", 2)
            ok = not missing and len(domain_reads) <= max_domains
            detail = ""
            if missing:
                detail = f"never read required: {', '.join(missing)}"
            elif len(domain_reads) > max_domains:
                detail = (f"bulk-loaded {len(domain_reads)} domain docs "
                          f"(max {max_domains}): {', '.join(domain_reads)}")
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
