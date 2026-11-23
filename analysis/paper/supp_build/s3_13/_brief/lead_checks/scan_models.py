"""List the models in this project's session records from a given UTC date on (model ids and dates only).

Usage: py -3.12 -X utf8 -I -B scan_models.py <project transcripts folder> <YYYY-MM-DD>
Reads every *.jsonl under the folder (main sessions and their subagents); for each assistant message with a model and a
timestamp on or after the date, counts the model and keeps its first and last UTC date. Prints nothing else.
"""
import json
import os
import sys
from collections import defaultdict


def main():
    folder, since = sys.argv[1], sys.argv[2]
    seen = defaultdict(lambda: [0, "9999", "0000", set()])
    files = 0
    for base, dirs, names in os.walk(folder):
        if os.sep + "memory" in base:
            continue
        for n in names:
            if not n.endswith(".jsonl"):
                continue
            files += 1
            kind = "subagent" if (os.sep + "subagents" + os.sep) in os.path.join(base, n) else "main"
            try:
                with open(os.path.join(base, n), encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if '"model"' not in line:
                            continue
                        try:
                            o = json.loads(line)
                        except ValueError:
                            continue
                        msg = o.get("message") if isinstance(o.get("message"), dict) else {}
                        m = msg.get("model")
                        ts = o.get("timestamp") or ""
                        if not m or not ts or ts[:10] < since or m == "<synthetic>":
                            continue
                        e = seen[m]
                        e[0] += 1
                        e[1] = min(e[1], ts[:10])
                        e[2] = max(e[2], ts[:10])
                        e[3].add(kind)
            except OSError:
                continue
    print("files read: %d; models from %s on:" % (files, since))
    for m, (n, a, b, kinds) in sorted(seen.items(), key=lambda kv: kv[1][1]):
        print("  %-34s %7d messages  %s to %s  (%s)" % (m, n, a, b, ", ".join(sorted(kinds))))


if __name__ == "__main__":
    main()
