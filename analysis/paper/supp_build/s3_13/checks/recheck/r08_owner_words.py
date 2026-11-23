# r08_owner_words.py - claims C11: visible uses of "owner" (HTML comments removed) per supplement file, staged copies in
# place of live ones, to check the fixer's reason for leaving "the owner" in Tables S3.18 b and S3.20 note c.
# Read-only; prints counts and a short context per hit.
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", ".."))
ROOT = os.path.normpath(os.path.join(OUT, "..", "..", ".."))
D = os.path.join(ROOT, "paper", "draft")
SD = os.path.join(OUT, "stage", "paper", "draft")
for n in sorted(os.listdir(D)):
    if not (n.startswith("S") and n.endswith(".md")):
        continue
    p = os.path.join(SD, n) if os.path.exists(os.path.join(SD, n)) else os.path.join(D, n)
    t = re.sub(r"<!--.*?-->", "", open(p, "rb").read().decode("utf-8"), flags=re.S)
    hits = list(re.finditer(r"\b[Oo]wner'?s?\b", t))
    if hits:
        print("%s (%s): %d" % (n, "staged" if p.startswith(SD) else "live", len(hits)))
        for m in hits[:3]:
            print("    ...%s..." % t[max(0, m.start() - 50):m.end() + 30].replace("\n", " "))
