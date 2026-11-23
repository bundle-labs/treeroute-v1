# Implementer B, round 14: inspection of the structure (no statistic is computed here).
# Reads: per_lead.json (structural keys only), bootstrap_draws.npy, each piece's meta.json, rows.parquet schema.
import json, hashlib, sys
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq

SHAP = Path(r"D:\treeroute\analysis\shap_v1")
PROBLEMS = ["coral", "defo", "fire", "pm25", "ndvi"]
STRUCT = ["models", "main_set", "declined_by_guard", "links", "rows", "sample_sha256", "draws_sha256"]


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


for p in PROBLEMS:
    print("=" * 30, p)
    lead = SHAP / "out" / p / "lead_0"
    pl = json.loads((lead / "compare" / "per_lead.json").read_text(encoding="utf-8"))
    for k in STRUCT:
        print(" per_lead", k, "=", pl.get(k, "<absent>"))
    d = np.load(lead / "compare" / "bootstrap_draws.npy", mmap_mode="r")
    arr = np.asarray(d)
    print(" draws shape", arr.shape, arr.dtype, "min", int(arr.min()), "max", int(arr.max()),
          "C-contig", arr.flags["C_CONTIGUOUS"], "fortran", np.isfortran(arr))
    print(" draws sha(file)", sha_file(lead / "compare" / "bootstrap_draws.npy"))
    print(" draws sha(data C order)", hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest())
    print(" first row", arr[0, :12].tolist())
    del d, arr
    for piece in sorted(x.name for x in lead.iterdir() if x.is_dir()):
        if piece == "compare":
            continue
        m = json.loads((lead / piece / "meta.json").read_text(encoding="utf-8"))
        sch = pq.read_schema(lead / piece / "rows.parquet")
        cols = sch.names
        nphi = sum(c.startswith("phi__") for c in cols)
        nphiv = sum(c.startswith("phiv__") for c in cols)
        print(" --", piece, "| link", m.get("link"), "c", m.get("c"), "ub", m.get("ub"), "| background", m.get("background"),
              "| rows", m.get("rows"), "| players", len(m.get("players", [])), "vars", len(m.get("variables", [])),
              "| nonzero", m.get("players_nonzero"), m.get("variables_nonzero"), "| phi cols", nphi, "phiv cols", nphiv,
              "| pass", m.get("pass"), "| dup", m.get("duplicates_merged"), "| guard", m.get("guard"))
        nonattr = [c for c in cols if not (c.startswith("phi__") or c.startswith("phiv__"))]
        print("    non-attr cols", nonattr)
