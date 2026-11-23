# Implementer B, round 14: regions of the rows and the draw matrix (identifications I01, I02). No statistic.
import json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

SHAP = Path(r"D:\treeroute\analysis\shap_v1")
EXPORT = {"coral": r"D:\treeroute\rival_export\coral\20261020_f3b8e3da",
          "defo": r"D:\treeroute\rival_export\defo\20261017_d71c61f4",
          "fire": r"D:\treeroute\rival_export\fire\20261017_869d1f38",
          "pm25": r"D:\treeroute\rival_export\pm25\20261007_74e67609",
          "ndvi": r"D:\treeroute\rival_export\ndvi\20261016_d1de3158"}

for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    lead = SHAP / "out" / p / "lead_0"
    draws = np.load(lead / "compare" / "bootstrap_draws.npy")
    G = draws.shape[1]
    keys = {}
    for piece in sorted(x.name for x in lead.iterdir() if x.is_dir() and x.name != "compare"):
        t = pq.read_table(lead / piece / "rows.parquet", columns=["row", "unit", "group", "time", "year"]).to_pandas()
        keys[piece] = t
    ref = keys["treeroute"]
    same = all(k[["row", "unit", "group", "time", "year"]].reset_index(drop=True).equals(ref[["row", "unit", "group", "time", "year"]].reset_index(drop=True)) for k in keys.values())
    groups_sorted = sorted(ref["group"].unique().tolist())
    man = json.loads((Path(EXPORT[p]) / "lead_0" / "export_manifest.json").read_text(encoding="utf-8"))
    mg = man.get("groups")
    print("==", p, "G", G, "n groups in rows", len(groups_sorted), "| keys identical over pieces:", same,
          "| export groups == sorted:", mg == groups_sorted, "| export groups sorted?", mg == sorted(mg) if mg else None,
          "| export counts", man.get("counts"))
    print("   rows per group: min", ref.groupby("group").size().min(), "max", ref.groupby("group").size().max(),
          "| units", ref["unit"].nunique(), "| row ids unique", ref["row"].is_unique, "min/max", ref["row"].min(), ref["row"].max())
    # sample.parquet: what columns (keys only)
    sm = pq.read_schema(SHAP / "sample" / p / "sample.parquet")
    print("   sample.parquet columns", sm.names)
    # generator attempts (layout of the matrix)
    salt = "shap_v1|AW4|%s|%d" % (p, 0)
    tries = {
        "b|k": lambda b, k: "%s|%d|%d" % (salt, b, k),
        "b|k(1-based b)": lambda b, k: "%s|%d|%d" % (salt, b + 1, k),
        "draw b|k": lambda b, k: "%s|draw|%d|%d" % (salt, b, k),
    }
    for name, f in tries.items():
        ok = True
        for b in range(3):
            for k in range(G):
                h = hashlib.sha256(f(b, k).encode("utf-8")).digest()
                v = int.from_bytes(h[:8], "big") % G
                if v != draws[b, k]:
                    ok = False
                    break
            if not ok:
                break
        print("   generator try", name, "reproduces first 3 rows:", ok)
