# Implementer B, round 14: variable maps, flags and the export's test-set columns (no statistic).
import json
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
    pl = json.loads((lead / "compare" / "per_lead.json").read_text(encoding="utf-8"))
    models = pl["models"]
    vmap = {}
    conflicts = []
    allplayers, allvars = set(), set()
    flags = {}
    for m in models + (["treeroute_B1"] if (lead / "treeroute_B1").exists() else []):
        meta = json.loads((lead / m / "meta.json").read_text(encoding="utf-8"))
        cols = pq.read_schema(lead / m / "rows.parquet").names
        phi = [c[5:] for c in cols if c.startswith("phi__")]
        phiv = [c[6:] for c in cols if c.startswith("phiv__")]
        assert set(phi) == set(meta["players"]), (p, m, "players")
        assert set(phiv) == set(meta["variables"]), (p, m, "variables")
        assert set(meta["variable_map"]) == set(meta["players"]), (p, m, "vmap keys")
        assert set(meta["variable_map"].values()) == set(meta["variables"]), (p, m, "vmap values")
        for k, v in meta["variable_map"].items():
            if k in vmap and vmap[k] != v:
                conflicts.append((m, k, vmap[k], v))
            vmap.setdefault(k, v)
        if m != "treeroute_B1":
            allplayers |= set(phi)
            allvars |= set(phiv)
        t = pq.read_table(lead / m / "rows.parquet", columns=["resid_flag", "pre"]).to_pandas()
        flags[m] = (int(t["resid_flag"].sum()), meta.get("rows_flagged_resid"), int((t["pre"] > 0).sum()), len(t))
    print("==", p, "players(union)", len(allplayers), "variables(union)", len(allvars), "map conflicts", conflicts[:5])
    print("   flagged / meta flagged / pre>0 / rows:", flags)
    nonx = sorted(v for v in allvars if v.startswith("hist") or v.startswith("ctx") or v in ("calendar", "normal"))
    print("   special variables:", nonx)
    print("   non-x players:", sorted(k for k in allplayers if not k.startswith("x__")))
    hist_players = sorted(k for k in allplayers if vmap[k].startswith("hist"))
    print("   players of hist_* variables:", hist_players)
    # export test files
    fs = sorted((Path(EXPORT[p]) / "lead_0" / "test").glob("*.parquet"))
    sch = pq.read_schema(fs[0])
    names = set(sch.names)
    missing = sorted(k for k in allplayers if k != "normal" and k not in names)
    print("   export test files", len(fs), "| key cols", [n for n in sch.names if not (n.startswith("x__") or n.startswith("c__"))][:12])
    print("   players without an export column:", missing[:20], len(missing))
    t = pq.read_table(fs[0], columns=["unit", "time"] + (["issue"] if "issue" in names else [])).to_pandas()
    print("   first test file: rows", len(t), "time range", t["time"].min(), t["time"].max(), "| units", t["unit"].nunique())
