#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""Distill an agent transcript into a compact, ordered action log for the judge.

Claude Code emits stream-json (one JSON event per line) that is enormously
verbose — a single session can be 150KB+, so raw byte-truncation feeds the
judge almost nothing but the init event. This extracts the signal the judge
actually needs: the ordered sequence of tool calls (with key inputs),
assistant text, and brief results, so evidence like "read canon/manifest.md
before grepping code" survives.

Plain-text transcripts (e.g. the codex adapter) are passed through, truncated
to a generous budget. Usage: distill-transcript.py FILE [max_chars]
"""
import json
import sys
from pathlib import Path

MAX = int(sys.argv[2]) if len(sys.argv) > 2 else 20000


def short(text, n):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n] + "…"


def tool_input_summary(name, inp):
    # Surface the field that reveals what the tool touched.
    for key in ("file_path", "path", "pattern", "command", "url", "query"):
        if key in inp:
            return short(inp[key], 100)
    return short(json.dumps(inp), 100)


def distill_stream_json(lines):
    out = []
    for raw in lines:
        raw = raw.strip()
        if not raw.startswith("{"):
            continue
        try:
            e = json.loads(raw)
        except json.JSONDecodeError:
            continue
        etype = e.get("type")
        if etype == "system" and e.get("subtype") == "init":
            out.append("[session start]")
        elif etype == "assistant":
            for b in e.get("message", {}).get("content", []):
                bt = b.get("type")
                if bt == "text" and b.get("text", "").strip():
                    out.append(f"[say] {short(b['text'], 240)}")
                elif bt == "thinking" and b.get("thinking", "").strip():
                    out.append(f"[think] {short(b['thinking'], 140)}")
                elif bt == "tool_use":
                    out.append(f"[tool] {b.get('name','?')} {tool_input_summary(b.get('name',''), b.get('input', {}))}")
        elif etype == "user":
            content = e.get("message", {}).get("content", [])
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        body = b.get("content", "")
                        if isinstance(body, list):
                            body = " ".join(x.get("text", "") for x in body if isinstance(x, dict))
                        out.append(f"[result] {short(body, 80)}")
        elif etype == "result":
            out.append("[session end]")
    return out


def main():
    path = Path(sys.argv[1])
    if not path.is_file():
        print("(transcript missing)")
        return 0
    text = path.read_text(errors="replace")
    stripped = text.lstrip()
    is_json_lines = stripped.startswith("{") and '"type"' in stripped[:2000]

    if is_json_lines:
        events = distill_stream_json(text.splitlines())
        rendered = "\n".join(events) if events else "(no events parsed)"
    else:
        rendered = text  # plain text (e.g. codex)

    if len(rendered) > MAX:
        # keep head and tail — first actions and final state both matter
        half = MAX // 2
        rendered = rendered[:half] + "\n…[middle elided]…\n" + rendered[-half:]
    print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
