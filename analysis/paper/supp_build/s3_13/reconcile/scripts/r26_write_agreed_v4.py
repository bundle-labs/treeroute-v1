# r26 (version 4, step 4): write OUT\reconcile\tables_agreed.md and OUT\reconcile\cells.json as byte copies of the
# builders' common version-4 files. Nothing is written unless: OUT\A\tables.md == OUT\B\tables.md and OUT\A\cells.json
# == OUT\B\cells.json byte for byte; the version-3 copies of r22 hold version 3 (tables_agreed_v3.md with the SHA-256
# that CHANGES_v4.md gives, cells_v3.json equal to both builders' cells_v3.json), the version-2 copies still hold
# version 2 (tables_agreed_v2.md with the SHA-256 that CHANGES_v3.md gives, cells_v2.json equal to both builders'
# cells_v2.json) and tables_agreed_v1.md still holds version 1; the files to be replaced are version 3 (or already
# version 4); r25 (version 3 + the order's changes == version 4, numbers and cells.json) passes; the reconciler's
# reconstruction (r06, which runs r04) equals that tables.md; the cells.json is in the spec's json.dumps form with
# every entry's cell and token on its line. The written files are read back and compared. Last, every file in
# OUT\reconcile is scanned for the user name, the home folder, the host name, a user-folder path, an e-mail address and
# a UUID-like id; the names are taken from the environment at run time and are not written anywhere.
import sys, os, re, json, hashlib, runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import OUT, Stop  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def sha(b):
    return hashlib.sha256(b).hexdigest()


R = OUT / "reconcile"
ta, tb = (OUT / "A" / "tables.md").read_bytes(), (OUT / "B" / "tables.md").read_bytes()
ca, cb = (OUT / "A" / "cells.json").read_bytes(), (OUT / "B" / "cells.json").read_bytes()
print("byte-identical, A and B: tables.md", ta == tb, "; cells.json", ca == cb)
if ta != tb or ca != cb:
    raise Stop("the builders' files differ: nothing written")
v3sha = set(re.findall(r"\b(86f7eb2a[0-9a-f]{50}5919d7)\b", (OUT / "spec" / "CHANGES_v4.md").read_text(encoding="utf-8")))
v2sha = set(re.findall(r"\b(a7710171[0-9a-f]{50}6570c9)\b", (OUT / "spec" / "CHANGES_v3.md").read_text(encoding="utf-8")))
t3, c3 = (R / "tables_agreed_v3.md").read_bytes(), (R / "cells_v3.json").read_bytes()
t2, c2, t1 = (R / "tables_agreed_v2.md").read_bytes(), (R / "cells_v2.json").read_bytes(), (R / "tables_agreed_v1.md").read_bytes()
ok3 = len(v3sha) == 1 and sha(t3) in v3sha and all((OUT / X / "cells_v3.json").read_bytes() == c3 and (OUT / X / "tables_v3.md").read_bytes() == t3 for X in ("A", "B"))
ok2 = len(v2sha) == 1 and sha(t2) in v2sha and all((OUT / X / "cells_v2.json").read_bytes() == c2 for X in ("A", "B"))
ok1 = sha(t1).startswith("5f414a11") and sha(t1).endswith("beae03")
print("version-3 copies hold version 3:", ok3, "; version-2 copies hold version 2:", ok2, "; tables_agreed_v1.md holds version 1:", ok1)
if not (ok3 and ok2 and ok1):
    raise Stop("the kept copies are not as expected: nothing written")
dest_t, dest_c = R / "tables_agreed.md", R / "cells.json"
if dest_t.read_bytes() not in (t3, ta) or dest_c.read_bytes() not in (c3, ca):
    raise Stop("a file to be replaced is neither version 3 nor the builders' version 4: nothing written")
try:
    runpy.run_path(str(HERE / "r25_v3_to_v4.py"), run_name="r25")
except SystemExit as ex:
    raise Stop("r25 did not pass (%s): nothing written" % ex)
G = runpy.run_path(str(HERE / "r06_rebuild_document.py"), run_name="r06")
if G["mine"] != ta:
    raise Stop("the reconciler's reconstruction differs from the builders' tables.md: nothing written")
txt = ca.decode("utf-8")
doc = json.loads(txt)
if txt != json.dumps(doc, ensure_ascii=False, indent=1, allow_nan=False) + "\n" or list(doc) != ["tables_file", "spec", "entries"]:
    raise Stop("cells.json is not in the spec's form: nothing written")
L = ta.decode("utf-8").split("\n")
off = [e for e in doc["entries"] if not (1 <= e["line"] <= len(L) - 1 and e["cell"] in L[e["line"] - 1] and e["printed"] in e["cell"])]
if off:
    raise Stop("%d entries do not sit on their line of tables.md: nothing written" % len(off))
print("---- r26: all conditions hold; writing")
with open(dest_t, "wb") as fh:
    fh.write(ta)
with open(dest_c, "wb") as fh:
    fh.write(ca)
gt, gc = dest_t.read_bytes(), dest_c.read_bytes()
print("OUT\\reconcile\\tables_agreed.md written:", len(gt), "bytes,", gt.count(b"\n"), "lines, sha256", sha(gt),
      "; equal to A, B and the reconstruction:", gt == ta == tb == G["mine"])
print("OUT\\reconcile\\cells.json written:", len(gc), "bytes,", len(doc["entries"]), "entries, sha256", sha(gc),
      "; equal to A and B:", gc == ca == cb, "; equal to version 3 (cells_v3.json):", gc == c3)
print("cells.json keys: tables_file", repr(doc["tables_file"]), "; spec", repr(doc["spec"]))
for name in ("tables_agreed_v3.md", "cells_v3.json", "tables_agreed_v2.md", "cells_v2.json", "tables_agreed_v1.md"):
    print("kept: %-20s sha256 %s" % (name, sha((R / name).read_bytes())))
if not (gt == ta and gc == ca):
    raise Stop("a written file differs from its source")
# privacy scan of everything in OUT\reconcile
me = os.environ.get("USERNAME", "") or Path.home().name
host = os.environ.get("COMPUTERNAME", "")
alts = [re.escape(x) for x in sorted({me, host, str(Path.home())}) if x]
alts += [r"users[\\/]", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}", r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"]
bad = re.compile("(?i)" + "|".join(alts))
hits, scanned, other = [], 0, []
for f in sorted(p for p in R.rglob("*") if p.is_file()):
    if f.suffix not in (".py", ".md", ".json", ".txt"):
        other.append(str(f.relative_to(OUT)))
        continue
    scanned += 1
    for i, l in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
        if bad.search(l):
            hits.append((str(f.relative_to(OUT)), i))
print("privacy scan of OUT\\reconcile:", scanned, "text files; other files:", other,
      "; lines with a user name, home or host name, user-folder path, e-mail address or UUID-like id:", hits)
