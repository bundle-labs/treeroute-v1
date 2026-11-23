import json, numpy as np, pandas as pd, pyarrow.parquet as pq
S = r"D:\treeroute\rivals_scratch\pm25\20261007_74e67609"
E = r"D:\treeroute\rival_export\pm25\20261007_74e67609"
G = "ganges_plain"
for L, sets in ((0, ("tune", "refit")), (6, ("guardfit", "refit")), (12, ("guardfit", "refit"))):
    tr = pq.read_table(E + r"\lead_%d\train\%s.parquet" % (L, G)).to_pandas()
    gs = pq.read_table(E + r"\lead_%d\guardside\%s.parquet" % (L, G)).to_pandas()
    for st in sets:
        meta = json.load(open(S + r"\lead_%d_%s.json" % (L, st)))
        cols = meta["columns"]; n = meta["rows"]
        idx = pq.read_table(S + r"\lead_%d_%s.index.parquet" % (L, st)).to_pandas()
        sel = np.flatnonzero(idx.group.values == G)
        X = np.memmap(S + r"\lead_%d_%s.f32" % (L, st), dtype=np.float32, mode="r", shape=(n, len(cols)))
        Xg = np.array(X[sel[0]:sel[-1] + 1]); del X
        assert sel[-1] - sel[0] + 1 == sel.size
        keys = idx.iloc[sel][["unit", "time"]].reset_index(drop=True)
        flag = "r_" + st
        ref = tr[tr[flag]].reset_index(drop=True)
        assert (ref.unit.values == keys.unit.values).all() and (ref.time.values == keys.time.values).all()
        hcols = [c for c in cols if c.startswith("x__hist_")]
        if st == "refit":
            want = ref[hcols].to_numpy(np.float32); nwant = ref["nfit__log_c"].to_numpy()
            src = "train x__ / nfit"
        else:
            union = tr[tr["r_" + st] | tr["r_inner" if L == 0 else "r_guard"]].reset_index(drop=True)
            m = union["r_" + st].to_numpy(bool)
            g2 = gs[m].reset_index(drop=True)
            want = g2[["h__" + c[3:] for c in hcols]].to_numpy(np.float32); nwant = g2["ngd__log_c"].to_numpy()
            src = "guardside h__ / ngd"
        got = Xg[:, [cols.index(c) for c in hcols]]
        same = np.array_equal(np.nan_to_num(got, nan=-9e9), np.nan_to_num(want, nan=-9e9))
        nd = np.max(np.abs(idx.iloc[sel]["n__log_c"].to_numpy() - nwant))
        print("lead %d %-8s group %s rows %d: memmap hist cols == %s: %s ; index n__log_c max|d| vs %s: %.3g"
              % (L, st, G, sel.size, src, same, src, nd))
