# Extract every tool call (and a clipped view of its result) from the round's transcripts.
# Usage: py -3.9 -I -B extract_calls.py <transcripts_dir> <out_dir> <label=file.jsonl>... -- <scrub1> <scrub2> ...
# The transcripts' folder path is passed as an argument and never written to disk; every string after "--"
# is replaced by "<redacted>" in everything written, and the transcripts' folder path by "<transcripts>".
import json
import os
import sys
from collections import Counter

args = sys.argv[1:]
tdir = args[0]
out_dir = args[1]
rest = args[2:]
if "--" in rest:
    k = rest.index("--")
    pairs, scrubs = rest[:k], rest[k + 1:]
else:
    pairs, scrubs = rest, []
scrubs = sorted({s for s in scrubs if s}, key=len, reverse=True)


def scrub(text):
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False)
    for variant in (tdir, tdir.replace("\\", "/"), tdir.replace("\\", "\\\\")):
        text = text.replace(variant, "<transcripts>")
    for s in scrubs:
        text = text.replace(s, "<redacted>")
        text = text.replace(s.lower(), "<redacted>")
        text = text.replace(s.upper(), "<redacted>")
    return text


def result_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict):
                if c.get("type") == "text":
                    parts.append(c.get("text", ""))
                else:
                    parts.append("[" + str(c.get("type")) + " block]")
            else:
                parts.append(str(c))
        return "\n".join(parts)
    return json.dumps(content, ensure_ascii=False)


os.makedirs(out_dir, exist_ok=True)
summary = {}
for pair in pairs:
    label, fname = pair.split("=", 1)
    path = os.path.join(tdir, fname)
    calls = []          # ordered tool_use records
    results = {}        # tool_use_id -> (text, is_error)
    prompt = None
    attach_types = Counter()
    attachments = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            t = obj.get("type")
            if t == "attachment":
                att = obj.get("attachment")
                at = att.get("type") if isinstance(att, dict) else type(att).__name__
                attach_types[at] += 1
                attachments.append((obj.get("timestamp"), at, json.dumps(att, ensure_ascii=False)[:600]))
                continue
            if t not in ("user", "assistant"):
                continue
            msg = obj.get("message") or {}
            content = msg.get("content")
            ts = obj.get("timestamp")
            if t == "user" and isinstance(content, str) and prompt is None:
                prompt = content
                continue
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict):
                    continue
                if t == "assistant" and item.get("type") == "tool_use":
                    calls.append({"id": item.get("id"), "name": item.get("name"),
                                  "input": item.get("input"), "ts": ts})
                elif t == "user" and item.get("type") == "tool_result":
                    results[item.get("tool_use_id")] = (result_text(item.get("content")),
                                                        bool(item.get("is_error")))
                elif t == "user" and item.get("type") == "text" and prompt is None:
                    prompt = item.get("text")
    names = Counter(c["name"] for c in calls)
    summary[label] = {"calls": len(calls), "by_tool": dict(names), "attachments": dict(attach_types),
                      "results_found": sum(1 for c in calls if c["id"] in results)}
    with open(os.path.join(out_dir, "prompt_" + label + ".txt"), "w", encoding="utf-8") as fo:
        fo.write(scrub(prompt or ""))
    # full calls (inputs in full, results in full) as JSON lines for scanning
    with open(os.path.join(out_dir, "calls_full_" + label + ".jsonl"), "w", encoding="utf-8") as fo:
        for i, c in enumerate(calls, 1):
            res, err = results.get(c["id"], ("<no result>", False))
            rec = {"n": i, "ts": c["ts"], "name": c["name"], "input": c["input"], "is_error": err,
                   "result": res}
            fo.write(scrub(json.dumps(rec, ensure_ascii=False)) + "\n")
    # readable list: inputs (Write content clipped), results clipped
    with open(os.path.join(out_dir, "calls_" + label + ".txt"), "w", encoding="utf-8") as fo:
        for i, c in enumerate(calls, 1):
            inp = dict(c["input"] or {})
            if c["name"] == "Write" and isinstance(inp.get("content"), str):
                inp["content"] = "<%d chars>" % len(inp["content"])
            if c["name"] == "Edit":
                for key in ("old_string", "new_string"):
                    if isinstance(inp.get(key), str) and len(inp[key]) > 300:
                        inp[key] = inp[key][:300] + "...<%d chars>" % len(inp[key])
            res, err = results.get(c["id"], ("<no result>", False))
            clip = res if len(res) <= 1500 else res[:1100] + "\n...<clipped %d chars>...\n" % (len(res) - 1500) + res[-400:]
            fo.write("#%d %s %s%s\n" % (i, c["ts"], c["name"], " ERROR" if err else ""))
            fo.write("  IN: " + scrub(json.dumps(inp, ensure_ascii=False)) + "\n")
            fo.write("  OUT(%d chars): " % len(res) + scrub(clip).replace("\n", "\n    ") + "\n\n")
    # attachment bodies are not written (they hold account identifiers); only their types are counted above
with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fo:
    json.dump(summary, fo, indent=1)
print(json.dumps(summary, indent=1))
