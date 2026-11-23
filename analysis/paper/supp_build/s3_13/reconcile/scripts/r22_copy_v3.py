# r22 (version 4, step 2a): byte copies of the version-3 agreed files, made before any other version-4 step writes in
# OUT\reconcile: OUT\reconcile\tables_agreed.md -> OUT\reconcile\tables_agreed_v3.md and OUT\reconcile\cells.json ->
# OUT\reconcile\cells_v3.json. The version-1 and version-2 copies (tables_agreed_v1.md, tables_agreed_v2.md,
# cells_v2.json) are not touched. Stops (and writes nothing) if a copy exists already, or if a source is not the
# version-3 file: tables_agreed.md must have the SHA-256 that CHANGES_v4.md gives for version 3 in full (86f7eb2a...5919d7,
# abbreviated so in the change order) and equal both builders' version-3 copies OUT\A\tables_v3.md and
# OUT\B\tables_v3.md; cells.json must equal OUT\A\cells_v3.json and OUT\B\cells_v3.json. Paths are found from this
# file's place.
import sys, re, hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2]
R = OUT / "reconcile"


def sha(b):
    return hashlib.sha256(b).hexdigest()


pairs = [(R / "tables_agreed.md", R / "tables_agreed_v3.md", "tables_v3.md"), (R / "cells.json", R / "cells_v3.json", "cells_v3.json")]
for src, dst, _ in pairs:
    if dst.exists():
        raise SystemExit("stop: OUT\\reconcile\\%s exists already; nothing written" % dst.name)
ch = (OUT / "spec" / "CHANGES_v4.md").read_text(encoding="utf-8")
full = re.findall(r"\b(86f7eb2a[0-9a-f]{50}5919d7)\b", ch)
order = (OUT / "_brief" / "fix_order_v4.md").read_text(encoding="utf-8")
if len(set(full)) != 1 or "86f7eb2a...5919d7" not in order:
    raise SystemExit("stop: the version-3 SHA-256 is not as the order and CHANGES_v4.md give it")
want = full[0]
print("version-3 tables.md SHA-256 (CHANGES_v4.md, abbreviated in the order):", want)
data = {}
for src, dst, bname in pairs:
    b = src.read_bytes()
    data[src.name] = b
    print("OUT\\reconcile\\%s:" % src.name, len(b), "bytes, sha256", sha(b))
    if src.name == "tables_agreed.md" and sha(b) != want:
        raise SystemExit("stop: tables_agreed.md is not version 3")
    for X in ("A", "B"):
        v3 = (OUT / X / bname).read_bytes()
        print("   equal to OUT\\%s\\%s:" % (X, bname), v3 == b)
        if v3 != b:
            raise SystemExit("stop: a builder's version-3 copy differs from the agreed version-3 file; nothing written")
for src, dst, _ in pairs:
    b = data[src.name]
    with open(dst, "xb") as fh:
        fh.write(b)
    got = dst.read_bytes()
    print("OUT\\reconcile\\%s written:" % dst.name, len(got), "bytes, sha256", sha(got), "; byte-identical to %s:" % src.name, got == b)
    if got != b:
        raise SystemExit("stop: the copy differs")
for name in ("tables_agreed_v1.md", "tables_agreed_v2.md", "cells_v2.json"):
    b = (R / name).read_bytes()
    print("OUT\\reconcile\\%s kept:" % name, len(b), "bytes, sha256", sha(b))
