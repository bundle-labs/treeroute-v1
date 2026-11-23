"""Read-only scan: which model IDs wrote the assistant turns in the project's session transcripts.

Usage: py -3.12 -I scan_models.py <projects_dir> [<projects_dir> ...]
Prints, per transcript folder, each model ID with its message count and first/last timestamp,
split into main-session files and subagent files. Writes nothing.
"""
import json
import os
import sys
from collections import defaultdict


def scan(root):
    stats = defaultdict(lambda: [0, None, None, set()])  # key -> [count, first_ts, last_ts, files]
    n_files = 0
    n_bad = 0
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith(".jsonl"):
                continue
            path = os.path.join(dirpath, name)
            kind = "subagent" if "subagents" in path.split(os.sep) else "main"
            n_files += 1
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if '"type":"assistant"' not in line and '"type": "assistant"' not in line:
                        continue
                    try:
                        obj = json.loads(line)
                    except ValueError:
                        n_bad += 1
                        continue
                    if obj.get("type") != "assistant":
                        continue
                    msg = obj.get("message") or {}
                    model = msg.get("model")
                    if not model:
                        continue
                    ts = obj.get("timestamp")
                    key = (kind, model)
                    s = stats[key]
                    s[0] += 1
                    if ts:
                        if s[1] is None or ts < s[1]:
                            s[1] = ts
                        if s[2] is None or ts > s[2]:
                            s[2] = ts
                    s[3].add(os.path.relpath(path, root).split(os.sep)[0])
    return n_files, n_bad, stats


def main(argv):
    for root in argv:
        n_files, n_bad, stats = scan(root)
        print(f"== {root}")
        print(f"   files scanned: {n_files}; unparsable assistant lines: {n_bad}")
        for (kind, model), (count, first, last, tops) in sorted(stats.items(), key=lambda kv: (kv[0][0], kv[1][1] or "")):
            print(f"   {kind:8s} {model:40s} msgs={count:7d} first={first} last={last} top_entries={len(tops)}")


if __name__ == "__main__":
    main(sys.argv[1:])
