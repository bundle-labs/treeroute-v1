"""Read-only: print type, timestamp and a text excerpt of chosen lines of a session transcript (.jsonl).

Usage: py -3.12 -I show_lines.py <transcript.jsonl> <spec> [<spec> ...]
A spec is N (one line) or A-B:user (every genuine user text message in lines A..B).
"""
import json
import sys


def text_of(obj, limit=420):
    msg = obj.get("message") or {}
    content = msg.get("content")
    parts = []
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text":
                parts.append(b.get("text", ""))
            elif b.get("type") == "tool_use":
                inp = b.get("input") or {}
                parts.append(f"[tool_use {b.get('name')}: {str(inp.get('file_path') or inp.get('command') or '')[:160]}]")
                if b.get("name") == "Write":
                    parts.append(str(inp.get("content", ""))[:limit])
            elif b.get("type") == "tool_result":
                c = b.get("content")
                if isinstance(c, list):
                    c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                parts.append(f"[tool_result] {str(c)[:limit]}")
    s = " ".join(parts).replace("\n", " / ")
    return s[:limit]


def is_user_text(obj):
    if obj.get("type") != "user":
        return False
    content = (obj.get("message") or {}).get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return any(isinstance(b, dict) and b.get("type") == "text" for b in content)
    return False


def main(argv):
    path = argv[0]
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    for spec in argv[1:]:
        if ":user" in spec:
            a, b = spec.split(":")[0].split("-")
            print(f"== user text messages in lines {a}-{b}")
            for n in range(int(a), int(b) + 1):
                obj = json.loads(lines[n - 1])
                if is_user_text(obj):
                    print(f"  [{n}] {obj.get('timestamp')} USER: {text_of(obj, 300)}")
        else:
            n = int(spec)
            obj = json.loads(lines[n - 1])
            print(f"[{n}] {obj.get('type')} {obj.get('timestamp')}: {text_of(obj)}")


if __name__ == "__main__":
    main(sys.argv[1:])
