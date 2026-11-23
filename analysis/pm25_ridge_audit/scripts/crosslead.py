import json, glob, os
import numpy as np, pandas as pd, pyarrow.parquet as pq
BASE = r"D:\treeroute\rival_export\pm25\20261007_74e67609"
man = json.load(open(BASE + r"\lead_0\export_manifest.json"))
xs = man["columns"]["x"]; cs = man["columns"]["c"]
hist = [c for c in xs if c.startswith("x__hist_")]
plain = [c for c in xs if c not in hist]
res = {6: dict(rows=0, plain_bad=0, plain_cells=0, ctx_bad=0, h1_bad=0, h1_n=0, cols_bad=set()), 12: dict(rows=0, plain_bad=0, plain_cells=0, ctx_bad=0, h1_bad=0, h1_n=0, cols_bad=set())}
for f in sorted(glob.glob(BASE + r"\lead_0\train\*.parquet")):
    g = os.path.basename(f)
    cols = ["unit", "time"] + plain + hist + cs
    a0 = pq.read_table(f, columns=cols).to_pandas()
    b0 = pq.read_table(BASE + r"\lead_0\test\%s" % g, columns=cols).to_pandas()
    z = pd.concat([a0, b0]).drop_duplicates(["unit", "time"]).set_index(["unit", "time"])
    for L in (6, 12):
        te = pq.read_table(BASE + r"\lead_%d\test\%s" % (L, g), columns=cols).to_pandas()
        ref = z.reindex(pd.MultiIndex.from_arrays([te.unit, te.time - L]))
        A = ref[plain].to_numpy(np.float64); B = te[plain].to_numpy(np.float64)
        diff = ~((np.isnan(A) & np.isnan(B)) | np.isclose(A, B, atol=0, rtol=0))
        r = res[L]; r["rows"] += len(te); r["plain_cells"] += diff.size; r["plain_bad"] += int(diff.sum())
        for j in np.flatnonzero(diff.any(axis=0)): r["cols_bad"].add(plain[j])
        cm = ref["c__ctx:month"].to_numpy(); r["ctx_bad"] += int((cm != te["c__ctx:month"].to_numpy()).sum())
        ref1 = z.reindex(pd.MultiIndex.from_arrays([te.unit, te.time - L + 1]))["x__hist_last_1"].to_numpy(np.float64)
        ok = np.isfinite(ref1)
        r["h1_n"] += int(ok.sum()); r["h1_bad"] += int((~np.isclose(ref1[ok], te["x__hist_last_1"].to_numpy(np.float64)[ok], atol=1e-6)).sum())
for L, r in res.items():
    r["cols_bad"] = sorted(r["cols_bad"])
    print("lead", L, json.dumps(r))
