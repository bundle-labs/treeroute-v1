# n18: .py bytes of OUT's archived folders in the records writer's listing and now (read-only, os.stat only).
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", ".."))
L = json.load(open(os.path.join(OUT, r"stage\_scripts\records\work\listing_out.json"), encoding="utf-8"))
TOPS = ("spec", "A", "B", "reconcile", "skeptic", "_brief")
then = sum(r[1] for r in L["files"] if r[0].replace("\\", "/").split("/")[0] in TOPS and r[0].endswith(".py"))
now = 0
for t in TOPS:
    for dp, dn, fn in os.walk(os.path.join(OUT, t)):
        for f in fn:
            if f.endswith(".py"):
                now += os.stat(os.path.join(dp, f)).st_size
print("OUT archived .py bytes: at listing %s, now %s" % (format(then, ","), format(now, ",")))
print("with SHAP's 2,056,719: at listing %s, now %s" % (format(then + 2056719, ","), format(now + 2056719, ",")))
