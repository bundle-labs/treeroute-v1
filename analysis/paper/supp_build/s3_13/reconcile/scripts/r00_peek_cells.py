# r00: print a few cells.json entries per (table, panel, source kind), to learn the selector shapes. Read-only.
import sys, json, re, collections
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2]
d = json.loads((OUT / "A" / "cells.json").read_text(encoding="utf-8"))
seen = collections.defaultdict(int)
for e in d["entries"]:
    src = re.sub(r"\\(pm25|ndvi|fire|defo|coral)\\", r"\\<p>\\", e["source"])
    src = re.sub(r"tr_shap_\w+_lead0", "tr_shap_<p>_lead0", src)
    sel = re.sub(r"\d+", "N", e["selector"])
    k = (e["table"], e["panel"], src.split("\\")[-1], e["column"] if e["table"] in ("S3.19", "S3.20", "S3.21", "S3.28", "S3.29", "S3.30", "9", "S3.22") else e["part"])
    seen[k] += 1
    if seen[k] <= 1:
        print(json.dumps(e, ensure_ascii=False))
print(len(seen), "kinds")
print(collections.Counter(e["source"].split("\\")[-1] for e in d["entries"]))
