import json, glob, os
import numpy as np, pandas as pd, pyarrow.parquet as pq
BASE = r"D:\treeroute\rival_export\pm25\20261007_74e67609"
man = json.load(open(BASE + r"\lead_0\export_manifest.json"))
xs = man["columns"]["x"]; plain = [c for c in xs if not c.startswith("x__hist_")]
for f in sorted(glob.glob(BASE + r"\lead_0\train\*.parquet")):
    g = os.path.basename(f)
    cols = ["unit", "time"] + plain
    z = pd.concat([pq.read_table(f, columns=cols).to_pandas(), pq.read_table(BASE + r"\lead_0\test\%s" % g, columns=cols).to_pandas()]).drop_duplicates(["unit", "time"])
    keys = set(zip(z.unit, z.time))
    for L in (6, 12):
        te = pq.read_table(BASE + r"\lead_%d\test\%s" % (L, g), columns=["unit", "time"]).to_pandas()
        miss = [(u, t) for u, t in zip(te.unit, te.time) if (u, t - L) not in keys]
        if miss: print("lead", L, g, "test rows whose issue row (u, t-L) is not in the lead-0 export files:", [(u, t, t - L) for u, t in miss])
