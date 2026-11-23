# r08: which printed two-decimal numbers would come out differently if someone re-rounded a three-decimal
# printout (such as V\reconcile\report.md A6) instead of formatting the stored double once; and the stored
# values closest to a rounding boundary. Information for the text writers only. Read-only.
import sys, collections
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F401,F403

sys.stdout.reconfigure(encoding="utf-8")
ents = load_json(OUT / "A" / "cells.json")["entries"]
trap = []
close = []
for e in ents:
    st = e["stored"]
    if len(st) != 1 or not finite(st[0]):
        continue
    v = st[0]
    p = e["printed"]
    if p.replace(MINUS, "-").lstrip("-")[:2] in ("0.", "1.") and len(p.replace(MINUS, "-").lstrip("-")) == 4 and "%" not in p:
        three = format(v, ".3f")
        if NUM2(float(three)) != p:
            trap.append((e["table"], e["panel"], e["row"], e["column"], e["part"], v, three, NUM2(float(three)), p))
        d = abs(abs(v) * 100 - (int(abs(v) * 100) + 0.5))
        close.append((d, e["table"], e["panel"], e["row"], e["column"], e["part"], v, p))
print("two-decimal cells:", len(close), "that a re-rounded three-decimal printout would change:", len(trap))
for t in trap:
    print("  ", t)
close.sort()
print("closest to a two-decimal rounding boundary (distance in hundredths):")
for c in close[:8]:
    print("  ", c)
