# r09: write OUT\reconcile\tables_agreed.md as the builders' common file (a byte copy of OUT\A\tables.md, which
# is byte-identical to OUT\B\tables.md and to the reconciler's own reconstruction of r06), then verify it.
# Also: the always-run rebuild gates exist on every problem, and no written file names a user folder.
# Version 2 (2026-11-17): the user name that version 1 wrote into the privacy regex below is now taken from the
# environment at run time, so no file holds it. Version 2's agreed files are written by r13, not by this script.
import sys, os, json, hashlib, runpy, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import *  # noqa: E402,F401,F403

sys.stdout.reconfigure(encoding="utf-8")
ta = (OUT / "A" / "tables.md").read_bytes()
tb = (OUT / "B" / "tables.md").read_bytes()
if ta != tb:
    raise Stop("the builders' tables.md differ; no common file to copy")
G = runpy.run_path(str(HERE / "r06_rebuild_document.py"), run_name="r06")
mine = G["mine"]
if mine != ta:
    raise Stop("the reconciler's reconstruction differs from the builders' common file")
for p in PROBS:
    g = load_json(SHAP / "rebuild" / p / "lead_0" / "gates.json")["gates"]
    for k in ("E0_ram_preflight", "E1_engine_code", "E2_versions", "E3a_inputs_before_read", "E3_inputs", "E4_donor_rows",
              "E5_bank_fingerprint", "E6_c_and_tolerances", "E8_predictions", "E9_coefficients_reproduce_the_kernel", "E10_exported_trees"):
        if k not in g:
            raise Stop("gate %s missing on %s" % (k, p))
    if g["E5_bank_fingerprint"]["pass"] is not False:
        raise Stop("E5 not false on " + p)
print("always-run gates present on all five problems; E5 false on all five")
dest = OUT / "reconcile" / "tables_agreed.md"
with open(dest, "wb") as fh:
    fh.write(ta)
got = dest.read_bytes()
print("tables_agreed.md written:", len(got), "bytes; sha256", hashlib.sha256(got).hexdigest(), "; equal to A, B and the reconstruction:", got == ta == tb == mine)
# privacy scan of what this step wrote (the agreed file and the reconciler's scripts)
_me = os.environ.get("USERNAME", "") or Path.home().name
bad = re.compile(r"(?i)users[\\/][^~]|" + (re.escape(_me) if _me else r"(?!x)x") + r"|@[a-z0-9-]+\.[a-z]|desktop-|session|workflow id")
hits = []
for f in [dest] + sorted((OUT / "reconcile" / "scripts").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    for i, l in enumerate(t.split("\n"), 1):
        if bad.search(l) and "bad = re.compile" not in l:
            hits.append((f.name, i, l[:120]))
print("privacy scan hits:", hits)
