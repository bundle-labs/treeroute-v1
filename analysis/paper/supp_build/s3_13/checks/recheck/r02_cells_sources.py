# r02_cells_sources.py - every distinct source file of OUT/reconcile/cells.json, with the problem and piece names
# replaced by <p> and <m>, and the number of entries per source and per table (read-only; prints to the screen).
# Used to check the source list of the SHAP protocol's staged entry of 2026-11-17 (fix P-1).
import collections
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", ".."))
E = json.load(open(os.path.join(OUT, "reconcile", "cells.json"), encoding="utf-8"))["entries"]
c = collections.Counter()
t = collections.defaultdict(set)
for e in E:
    s = e["source"]
    s = re.sub(r"\\(pm25|ndvi|fire|defo|coral)\\", r"\\<p>\\", s)
    s = re.sub(r"tr_shap_(pm25|ndvi|fire|defo|coral)_", "tr_shap_<p>_", s)
    s = re.sub(r"\\lead_0\\(treeroute_B1|treeroute|rival_[a-z0-9_]+)\\", r"\\lead_0\\<m>\\", s)
    c[s] += 1
    t[s].add(e["table"])
for s, n in sorted(c.items(), key=lambda kv: -kv[1]):
    print("%6d  %s  (tables %s)" % (n, s, ", ".join(sorted(t[s]))))
print("entries:", len(E), "distinct sources:", len(c))
