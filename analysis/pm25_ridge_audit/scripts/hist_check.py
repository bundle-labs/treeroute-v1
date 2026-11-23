import sys, numpy as np, pandas as pd, pyarrow.parquet as pq
E = r"D:/treeroute/rival_export/pm25/20261007_74e67609"
R = r"D:/treeroute/runs/pm25/headline/20261007_74e67609"
groups = sys.argv[1].split(",")
H = ["hist_last_1","hist_last_2","hist_last_3","hist_mean_12","hist_mean_60","hist_mean_all"]
DRV = ["x__V01_mean_temp_C","x__V02_total_precip_mm","x__nino34","x__ntl","x__burn_frac","x__era5l_d2m"]
for g in groups:
    tr0 = pq.read_table(f"{E}/lead_0/train/{g}.parquet", columns=["unit","time","issue","lead","y","r_refit"]+["x__"+h for h in H]+DRV).to_pandas()
    tr0["unit"]=tr0["unit"].astype(str)
    # label series per unit from lead-0 train (times <= 24240)
    lab = tr0[["unit","time","y"]].copy()
    # test labels from the run's saved test (y for 2020-2023, 15 scored units)
    tp = pq.read_table(f"{R}/test_preds.parquet", columns=["unit","group","time","y"]).to_pandas()
    tp = tp[tp["group"].astype(str)==g][["unit","time","y"]]; tp["unit"]=tp["unit"].astype(str)
    lab = pd.concat([lab, tp]).drop_duplicates(["unit","time"]).set_index(["unit","time"])["y"]
    for L in (0,6,12):
        tr = pq.read_table(f"{E}/lead_{L}/train/{g}.parquet", columns=["unit","time","issue","lead","y","r_refit"]+["x__"+h for h in H]+DRV).to_pandas()
        te = pq.read_table(f"{E}/lead_{L}/test/{g}.parquet", columns=["unit","time","issue","lead"]+["x__"+h for h in H]+DRV).to_pandas()
        for name, t in (("refit", tr[tr["r_refit"].astype(bool)]), ("test", te)):
            t = t.copy(); t["unit"]=t["unit"].astype(str)
            out=[]
            for k in (1,2,3):
                key = pd.MultiIndex.from_arrays([t["unit"], t["issue"]-(k-1)])
                ref = lab.reindex(key).to_numpy()
                v = t["x__hist_last_%d"%k].to_numpy(np.float64)
                ok = np.isfinite(ref)&np.isfinite(v)
                eq = np.isclose(v[ok], ref[ok], rtol=1e-5, atol=1e-4).mean() if ok.any() else float('nan')
                # alt: equal to y at time t-k (lead-0 style)?
                key2 = pd.MultiIndex.from_arrays([t["unit"], t["time"]-k]); ref2 = lab.reindex(key2).to_numpy()
                ok2 = np.isfinite(ref2)&np.isfinite(v)
                eq2 = np.isclose(v[ok2], ref2[ok2], rtol=1e-5, atol=1e-4).mean() if ok2.any() else float('nan')
                # same-time label?
                key3 = pd.MultiIndex.from_arrays([t["unit"], t["time"]]); ref3 = lab.reindex(key3).to_numpy()
                ok3 = np.isfinite(ref3)&np.isfinite(v)
                eq3 = np.isclose(v[ok3], ref3[ok3], rtol=1e-5, atol=1e-4).mean() if ok3.any() else float('nan')
                out.append("last_%d: =y(issue-%d) %.4f (n=%d) | =y(t-%d) %.4f | =y(t) %.4f" % (k,k-1,eq,ok.sum(),k,eq2,eq3))
            # hist_mean_12 = mean of y over (issue-11..issue)?
            v = t["x__hist_mean_12"].to_numpy(np.float64)
            refs = np.column_stack([lab.reindex(pd.MultiIndex.from_arrays([t["unit"], t["issue"]-j])).to_numpy() for j in range(12)])
            m12 = np.nanmean(refs, axis=1) if True else None
            okm = np.isfinite(v)&np.isfinite(refs).all(axis=1)
            eqm = np.isclose(v[okm], m12[okm], rtol=1e-4, atol=1e-3).mean() if okm.any() else float('nan')
            print(g, "lead", L, name, "rows", len(t), "issue==time-lead", bool((t["issue"]==t["time"]-L).all()),
                  "time range", int(t["time"].min()), int(t["time"].max()), "issue max", int(t["issue"].max()))
            print("   ", " ; ".join(out), "; mean12 over issue-11..issue: %.4f (n=%d)" % (eqm, okm.sum()))
