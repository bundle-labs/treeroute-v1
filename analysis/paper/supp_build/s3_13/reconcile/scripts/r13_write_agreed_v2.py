# r13 (version 2, step 4): write OUT\reconcile\tables_agreed.md and OUT\reconcile\cells.json as byte copies of the
# builders' common version-2 files, so that the header comment's "every printed number is listed in cells.json
# beside this file" holds. Nothing is written unless OUT\A\tables.md == OUT\B\tables.md and OUT\A\cells.json ==
# OUT\B\cells.json byte for byte, the reconciler's reconstruction (r06, which runs r04) equals that tables.md, the
# cells.json is in the spec's json.dumps form with every entry on its line, OUT\reconcile\tables_agreed_v1.md holds
# version 1 (r10), and the file to be replaced is version 1 (or already version 2). The written files are read back
# and compared. Last, every file in OUT\reconcile is scanned for the user name, the home folder, the host name, a
# user-folder path, an e-mail address and a UUID-like id; the names are taken from the environment at run time and
# are not written anywhere.
import sys, os, re, json, hashlib, runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import OUT, Stop  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def sha(b):
    return hashlib.sha256(b).hexdigest()


ta, tb = (OUT / "A" / "tables.md").read_bytes(), (OUT / "B" / "tables.md").read_bytes()
ca, cb = (OUT / "A" / "cells.json").read_bytes(), (OUT / "B" / "cells.json").read_bytes()
print("byte-identical, A and B: tables.md", ta == tb, "; cells.json", ca == cb)
if ta != tb or ca != cb:
    raise Stop("the builders' files differ: nothing written")
v1 = (OUT / "reconcile" / "tables_agreed_v1.md").read_bytes()
if not (sha(v1).startswith("5f414a11") and sha(v1).endswith("beae03")):
    raise Stop("OUT\\reconcile\\tables_agreed_v1.md is not version 1: nothing written")
dest_t, dest_c = OUT / "reconcile" / "tables_agreed.md", OUT / "reconcile" / "cells.json"
if dest_t.read_bytes() not in (v1, ta):
    raise Stop("OUT\\reconcile\\tables_agreed.md is neither version 1 nor the builders' version 2: nothing written")
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
with open(dest_t, "wb") as fh:
    fh.write(ta)
with open(dest_c, "wb") as fh:
    fh.write(ca)
gt, gc = dest_t.read_bytes(), dest_c.read_bytes()
print("OUT\\reconcile\\tables_agreed.md written:", len(gt), "bytes,", gt.count(b"\n"), "lines, sha256", sha(gt),
      "; equal to A, B and the reconstruction:", gt == ta == tb == G["mine"])
print("OUT\\reconcile\\cells.json written:", len(gc), "bytes,", len(doc["entries"]), "entries, sha256", sha(gc),
      "; equal to A and B:", gc == ca == cb)
print("cells.json keys: tables_file", repr(doc["tables_file"]), "; spec", repr(doc["spec"]))
if not (gt == ta and gc == ca):
    raise Stop("a written file differs from its source")
# privacy scan of everything in OUT\reconcile
me = os.environ.get("USERNAME", "") or Path.home().name
host = os.environ.get("COMPUTERNAME", "")
alts = [re.escape(x) for x in sorted({me, host, str(Path.home())}) if x]
alts += [r"users[\\/]", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}", r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"]
bad = re.compile("(?i)" + "|".join(alts))
hits, scanned, other = [], 0, []
for f in sorted(p for p in (OUT / "reconcile").rglob("*") if p.is_file()):
    if f.suffix not in (".py", ".md", ".json", ".txt"):
        other.append(str(f.relative_to(OUT)))
        continue
    scanned += 1
    for i, l in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
        if bad.search(l):
            hits.append((str(f.relative_to(OUT)), i))
print("privacy scan of OUT\\reconcile:", scanned, "text files; other files:", other,
      "; lines with a user name, home or host name, user-folder path, e-mail address or UUID-like id:", hits)
