"""List every Write/Edit call in one agent transcript with its result, and save refused report/table drafts.

Usage: py -3.12 -X utf8 -I recover_writes.py <agent-*.jsonl> <out dir>
Prints file paths, times and result status; error texts are cut to 600 characters.
"""
import json
import os
import sys


def text_of(cc):
    if isinstance(cc, list):
        return " ".join(x.get("text", "") for x in cc if isinstance(x, dict))
    return str(cc)


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    uses = {}
    results = {}
    with open(src, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            try:
                o = json.loads(line)
            except Exception:
                continue
            msg = o.get("message") or {}
            c = msg.get("content")
            if not isinstance(c, list):
                continue
            for b in c:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    uses[b.get("id")] = (b.get("name"), b.get("input"), n, o.get("timestamp"))
                elif b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = (b.get("is_error"), text_of(b.get("content")), n,
                                                     o.get("timestamp"))
    for tid, (name, inp, n, ts) in uses.items():
        if name not in ("Write", "Edit"):
            continue
        fp = (inp or {}).get("file_path")
        r = results.get(tid)
        st = "no result" if r is None else ("ERROR" if r[0] else "ok")
        print("%s line %d %s %s -> %s" % (ts, n, name, fp, st))
        if r is not None and (r[0] or "refus" in r[1].lower() or "denied" in r[1].lower()):
            print("    result:", " ".join(r[1].split())[:600])
        if name == "Write" and fp and os.path.basename(fp).lower() in ("report.md", "tables.md"):
            p = os.path.join(out, "recovered_L%d_%s" % (n, os.path.basename(fp)))
            with open(p, "w", encoding="utf-8", newline="\n") as g:
                g.write(inp.get("content", ""))
            print("    saved", p, len(inp.get("content", "")), "chars")
    print()
    for tid, (iserr, txt, n, ts) in results.items():
        if iserr:
            name = uses.get(tid, ("?",))[0]
            print("ERROR %s line %d %s: %s" % (ts, n, name, " ".join(txt.split())[:300]))


if __name__ == "__main__":
    main()
