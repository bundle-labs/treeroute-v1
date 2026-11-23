# r03_results_selectors.py - the cells.json entries whose source is V/A/results.json, tallied by table and by the
# selector's pattern (problem names replaced by <p>, pair keys by <pair>), to check what the SHAP protocol's staged
# entry of 2026-11-17 says results.json gives (fix P-1). Read-only; prints to the screen.
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
for e in E:
    if not e["source"].endswith("results.json"):
        continue
    s = e["selector"]
    s = re.sub(r"\b(pm25|ndvi|fire|defo|coral)\b", "<p>", s)
    s = re.sub(r"pairs\.[^.]+\|[^.]+\.", "pairs.<pair>.", s)
    s = re.sub(r"players\.[^.]+\.", "players.<j>.", s)
    s = re.sub(r"\.(value|ci_low|ci_high|n_finite)$", ".<part>", s)
    s = re.sub(r"top(3|10)\[\d+\](\[\d+\])?", r"top\1[i]", s)
    c[(e["table"], s)] += 1
for (tab, s), n in sorted(c.items()):
    print("%-6s %5d  %s" % (tab, n, s[:160]))
