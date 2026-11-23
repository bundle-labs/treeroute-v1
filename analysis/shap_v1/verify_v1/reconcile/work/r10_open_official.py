"""First opening of the official compare outputs (structure and small files), every open logged with its time.

py -3.9 -I -B r10_open_official.py
"""
import json
import os
import sys

sys.path.insert(0, r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile")
import rlib as R  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 90)
WHO = "work\\r10_open_official.py"

for p in R.PROBLEMS:
    d = R.compare_dir(p)
    print("=" * 40, p)
    per = R.read_official_json(os.path.join(d, "per_lead.json"), WHO)
    print("per_lead keys:", list(per.keys()))
    for k, v in per.items():
        if k in ("variable", "feature"):
            print(" ", k, {kk: (vv if not isinstance(vv, list) else "list[%d]" % len(vv)) for kk, vv in v.items()})
        elif k == "families":
            print("  families: %d variables; values %s" % (len(v), sorted(set(v.values()))))
        elif k == "global_columns":
            print("  global_columns[%d]:" % len(v), v)
        elif k == "nonzero_forecast_rows":
            print("  nonzero_forecast_rows:", json.dumps(v)[:1500])
        else:
            print(" ", k, ":", json.dumps(v)[:300])
    D, sha = R.read_official_npy(os.path.join(d, "bootstrap_draws.npy"), WHO)
    print("draws", D.shape, D.dtype, "sha matches per_lead:", sha == per.get("draws_sha256"))
    imp = R.read_official_parquet(os.path.join(d, "importance.parquet"), WHO)
    print("importance.parquet", imp.shape, dict(imp.dtypes.astype(str)))
    print(imp.groupby(["level", "model"]).agg(n=("player", "size"), active=("active", "sum"),
                                              det=("sign_determined", "sum")))
    print(imp.head(3))
    fam = R.read_official_parquet(os.path.join(d, "families.parquet"), WHO)
    print("families.parquet", fam.shape, dict(fam.dtypes.astype(str)))
    print(fam)
    pr = R.read_official_parquet(os.path.join(d, "pairs.parquet"), WHO)
    print("pairs.parquet", pr.shape, dict(pr.dtypes.astype(str)))
    print("statistics:", pr.groupby(["level", "statistic"]).size().to_dict())
    print("labels:", sorted(pr.pair_label.unique()))
    print(pr.head(12))
    bs = R.read_official_parquet(os.path.join(d, "bootstrap_stats.parquet"), WHO)
    print("bootstrap_stats.parquet", bs.shape, dict(bs.dtypes.astype(str)))
    print(bs.head(3))
    print("draw range", bs["draw"].min(), bs["draw"].max(), "pairs", bs["pair"].nunique(), "levels",
          sorted(bs["level"].unique()))
    mr = R.read_official_json(os.path.join(d, "AW4_main_row.json"), WHO)
    print("AW4_main_row.json:", json.dumps(mr, indent=1))
    t3 = R.read_official_text(os.path.join(d, "AW3_table.md"), WHO)
    lines = t3.splitlines()
    print("AW3_table.md: %d lines" % len(lines))
    if p in ("coral", "fire"):
        print(t3)
    else:
        for ln in lines[:12]:
            print("   |", ln[:300])
    t4 = R.read_official_text(os.path.join(d, "AW4_table.md"), WHO)
    print("AW4_table.md:\n" + t4)
    dj = R.read_official_json(os.path.join(d, "pairs.parquet.done.json"), WHO)
    print("pairs.parquet.done.json:", json.dumps(dj, indent=1)[:2500])
