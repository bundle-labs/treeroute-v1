# Probe the line structure of one transcript file (path given as argument; nothing written to disk).
import json
import sys
from collections import Counter

path = sys.argv[1]
types = Counter()
first = {}
with open(path, encoding="utf-8") as fh:
    for i, line in enumerate(fh):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        t = obj.get("type")
        types[t] += 1
        if t not in first:
            first[t] = obj
print("line types:", dict(types))
for t, obj in first.items():
    print("== type", t, "keys:", sorted(obj.keys()))
    msg = obj.get("message")
    if isinstance(msg, dict):
        print("   message keys:", sorted(msg.keys()))
        c = msg.get("content")
        if isinstance(c, list):
            print("   content item types:", [x.get("type") for x in c if isinstance(x, dict)])
        else:
            print("   content type:", type(c).__name__, "len", len(c) if c else 0)
