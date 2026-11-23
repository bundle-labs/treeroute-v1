# n06: dump cells.json entries for given table:panel pairs (read-only), compactly, to a file in this folder.
# usage: n06_cells_dump.py OUTNAME table:panel [table:panel ...]   (panel may be '' -> write table: )
import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
CELLS = os.path.join(ROOT, r"paper\supp_build\s3_13\reconcile\cells.json")
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.loads(open(CELLS, "rb").read().decode("utf-8"))
E = d["entries"]
outname = sys.argv[1]
want = []
for a in sys.argv[2:]:
    t, p = a.split(":")
    want.append((t, p))
with open(os.path.join(HERE, outname), "w", encoding="utf-8", newline="\n") as f:
    for e in E:
        if (e["table"], e["panel"]) in want:
            f.write("L%d %s/%s row=%s col=%s part=%s printed=%r stored=%r sel=%s src=%s\n" % (
                e["line"], e["table"], e["panel"], e["row"], e["column"], e["part"], e["printed"],
                e["stored"], e["selector"], e["source"]))
print("done")
