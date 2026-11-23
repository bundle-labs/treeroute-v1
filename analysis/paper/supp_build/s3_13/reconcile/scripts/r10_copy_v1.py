# r10 (version 2, step 2a): byte copy of the version-1 agreed file OUT\reconcile\tables_agreed.md to
# OUT\reconcile\tables_agreed_v1.md, made before any other version-2 step writes in OUT\reconcile. Stops (and
# writes nothing) if the copy exists already or if tables_agreed.md is not the version-1 file: its SHA-256 must
# start 5f414a11 and end beae03 (the change order's abbreviation) and its bytes must equal both builders'
# version-1 copies OUT\A\tables_v1.md and OUT\B\tables_v1.md. Paths are found from this file's place.
import sys, hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2]
src = OUT / "reconcile" / "tables_agreed.md"
dst = OUT / "reconcile" / "tables_agreed_v1.md"
if dst.exists():
    raise SystemExit("stop: OUT\\reconcile\\tables_agreed_v1.md exists already; nothing written")
b = src.read_bytes()
h = hashlib.sha256(b).hexdigest()
print("OUT\\reconcile\\tables_agreed.md:", len(b), "bytes, sha256", h)
if not (h.startswith("5f414a11") and h.endswith("beae03")):
    raise SystemExit("stop: tables_agreed.md is not the version-1 agreed file (order: 5f414a11...beae03)")
for X in ("A", "B"):
    v1 = (OUT / X / "tables_v1.md").read_bytes()
    print("equal to OUT\\%s\\tables_v1.md:" % X, v1 == b)
    if v1 != b:
        raise SystemExit("stop: the builders' version-1 copy differs from the agreed version 1")
with open(dst, "xb") as fh:
    fh.write(b)
got = dst.read_bytes()
print("OUT\\reconcile\\tables_agreed_v1.md written:", len(got), "bytes, sha256", hashlib.sha256(got).hexdigest(),
      "; byte-identical to tables_agreed.md:", got == b)
if got != b:
    raise SystemExit("stop: the copy differs")
