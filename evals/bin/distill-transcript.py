#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""Distill a transcript into a compact, ordered action log for the judge.

Claude stream-JSON and Codex exec JSON events are distilled into tool calls,
commands, assistant text, and brief results so ordering evidence (including
which Canon notes were read, and when) survives. Plain-text transcripts are
passed through. Other JSON event shapes produce ``(no events parsed)``.

Usage: distill-transcript.py FILE [max_chars] [--final]

With --final, print only the session's final answer (Claude's result event,
Codex's last agent message, or the tail of a plain-text transcript).
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
        elif etype == "thread.started":
            out.append("[session start]")
        elif etype == "turn.completed":
            out.append("[session end]")
        elif etype == "item.completed":
            item = e.get("item", {})
            itype = item.get("type")
            if itype == "agent_message" and str(item.get("text", "")).strip():
                out.append(f"[say] {short(item['text'], 240)}")
            elif itype == "reasoning" and str(item.get("text", "")).strip():
                out.append(f"[think] {short(item['text'], 140)}")
            elif itype == "command_execution":
                out.append(
                    f"[cmd] {short(item.get('command', ''), 160)} "
                    f"(exit {item.get('exit_code')})"
                )
            elif itype == "file_change":
                paths = [c.get("path", "?") for c in item.get("changes", []) if isinstance(c, dict)]
                out.append(f"[edit] {short(', '.join(paths), 160)}")
    return out


def final_answer(text):
    answer, saw_json = "", False
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw.startswith("{"):
            continue
        try:
            e = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(e, dict):
            continue
        saw_json = True
        if e.get("type") == "result" and isinstance(e.get("result"), str):
            answer = e["result"]
        elif e.get("type") == "item.completed":
            item = e.get("item", {})
            if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                answer = item["text"]
        elif e.get("type") == "assistant":
            texts = [b.get("text", "") for b in e.get("message", {}).get("content", [])
                     if isinstance(b, dict) and b.get("type") == "text"]
            if any(t.strip() for t in texts):
                answer = "\n".join(texts)
    return answer if saw_json else text[-MAX:]


def main():
    path = Path(sys.argv[1])
    if not path.is_file():
        print("(transcript missing)")
        return 0
    text = path.read_text(errors="replace")
    if "--final" in sys.argv[3:]:
        answer = final_answer(text).strip() or "(no final answer)"
        print(answer[-MAX:])
        return 0
    stripped = text.lstrip()
    is_json_lines = stripped.startswith("{") and '"type"' in stripped[:2000]

    if is_json_lines:
        events = distill_stream_json(text.splitlines())
        rendered = "\n".join(events) if events else "(no events parsed)"
    else:
        rendered = text  # plain-text adapters

    if len(rendered) > MAX:
        # keep head and tail — first actions and final state both matter
        half = MAX // 2
        rendered = rendered[:half] + "\n…[middle elided]…\n" + rendered[-half:]
    print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
