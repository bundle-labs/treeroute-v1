# n05: index of cells.json entries by table/panel/column (read-only); optional filter args: table [line ...]
import collections
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
CELLS = os.path.join(ROOT, r"paper\supp_build\s3_13\reconcile\cells.json")
d = json.loads(open(CELLS, "rb").read().decode("utf-8"))
E = d["entries"]
print("entries:", len(E))
if len(sys.argv) == 1:
    c = collections.Counter((e["table"], e["panel"], e["column"]) for e in E)
    for k, v in sorted(c.items()):
        print(k, v)
else:
    tab = sys.argv[1]
    lines = set(int(x) for x in sys.argv[2:])
    for e in E:
        if e["table"] == tab and (not lines or e["line"] in lines):
            print(json.dumps(e, ensure_ascii=False))
