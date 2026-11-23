import json, glob, os
import numpy as np, pyarrow.parquet as pq
BASE = r"D:\treeroute\rival_export\pm25\20261007_74e67609\lead_0\train"
ys_t, ys_r = [], []
for f in sorted(glob.glob(os.path.join(BASE, "*.parquet"))):
    t = pq.read_table(f, columns=["y", "r_tune", "r_refit"]).to_pandas()
    ys_t.append(t.y[t.r_tune].to_numpy()); ys_r.append(t.y[t.r_refit].to_numpy())
for name, ys in (("tune (<= guard cut 24204)", ys_t), ("refit (<= fit cut 24240)", ys_r)):
    y = np.concatenate(ys); pos = y[np.isfinite(y) & (y > 0)]
    print(name, "rows", y.size, "positive", pos.size, "1st percentile", float(np.percentile(pos, 1)))
