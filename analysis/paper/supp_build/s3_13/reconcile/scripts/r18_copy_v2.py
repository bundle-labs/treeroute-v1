# r18 (version 3, step 2a): byte copies of the version-2 agreed files, made before any other version-3 step writes in
# OUT\reconcile: OUT\reconcile\tables_agreed.md -> OUT\reconcile\tables_agreed_v2.md and OUT\reconcile\cells.json ->
# OUT\reconcile\cells_v2.json. OUT\reconcile\tables_agreed_v1.md is not touched. Stops (and writes nothing) if a copy
# exists already, or if a source is not the version-2 file: tables_agreed.md must have the SHA-256 that the change order
# and CHANGES_v3.md give for version 2 (a7710171...6570c9, in full in CHANGES_v3.md) and equal both builders' version-2
# copies OUT\A\tables_v2.md and OUT\B\tables_v2.md; cells.json must equal OUT\A\cells_v2.json and OUT\B\cells_v2.json.
# Paths are found from this file's place.
import sys, re, hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2]
R = OUT / "reconcile"


def sha(b):
    return hashlib.sha256(b).hexdigest()


pairs = [(R / "tables_agreed.md", R / "tables_agreed_v2.md", "tables_v2.md"), (R / "cells.json", R / "cells_v2.json", "cells_v2.json")]
for src, dst, _ in pairs:
    if dst.exists():
        raise SystemExit("stop: OUT\\reconcile\\%s exists already; nothing written" % dst.name)
ch = (OUT / "spec" / "CHANGES_v3.md").read_text(encoding="utf-8")
full = re.findall(r"\b(a7710171[0-9a-f]{50}6570c9)\b", ch)
order = (OUT / "_brief" / "fix_order_v3.md").read_text(encoding="utf-8")
if len(set(full)) != 1 or "a7710171...6570c9" not in order:
    raise SystemExit("stop: the version-2 SHA-256 is not as the order and CHANGES_v3.md give it")
want = full[0]
print("version-2 tables.md SHA-256 (CHANGES_v3.md, abbreviated in the order):", want)
data = {}
for src, dst, bname in pairs:
    b = src.read_bytes()
    data[src.name] = b
    print("OUT\\reconcile\\%s:" % src.name, len(b), "bytes, sha256", sha(b))
    if src.name == "tables_agreed.md" and sha(b) != want:
        raise SystemExit("stop: tables_agreed.md is not version 2")
    for X in ("A", "B"):
        v2 = (OUT / X / bname).read_bytes()
        print("   equal to OUT\\%s\\%s:" % (X, bname), v2 == b)
        if v2 != b:
            raise SystemExit("stop: a builder's version-2 copy differs from the agreed version-2 file; nothing written")
for src, dst, _ in pairs:
    b = data[src.name]
    with open(dst, "xb") as fh:
        fh.write(b)
    got = dst.read_bytes()
    print("OUT\\reconcile\\%s written:" % dst.name, len(got), "bytes, sha256", sha(got), "; byte-identical to %s:" % src.name, got == b)
    if got != b:
        raise SystemExit("stop: the copy differs")
v1 = (R / "tables_agreed_v1.md").read_bytes()
print("OUT\\reconcile\\tables_agreed_v1.md kept:", len(v1), "bytes, sha256", sha(v1))
