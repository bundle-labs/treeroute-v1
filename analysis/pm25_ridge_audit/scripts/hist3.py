import numpy as np, pandas as pd, pyarrow.parquet as pq, sys
E = r"D:/treeroute/rival_export/pm25/20261007_74e67609"
R = r"D:/treeroute/runs/pm25/headline/20261007_74e67609"
g = sys.argv[1]
tp = pq.read_table(f"{R}/test_preds.parquet", columns=["unit","group","time","y"]).to_pandas()
tp = tp[tp["group"].astype(str)==g][["unit","time","y"]]; tp["unit"]=tp["unit"].astype(str)
tr0 = pq.read_table(f"{E}/lead_0/train/{g}.parquet", columns=["unit","time","y"]).to_pandas(); tr0["unit"]=tr0["unit"].astype(str)
lab = pd.concat([tr0, tp]).drop_duplicates(["unit","time"])
piv = lab.pivot(index="time", columns="unit", values="y").sort_index()
csum = piv.fillna(0).cumsum(); ccnt = piv.notna().cumsum()
for L in (0,6,12):
    tr = pq.read_table(f"{E}/lead_{L}/train/{g}.parquet").to_pandas(); tr["unit"]=tr["unit"].astype(str)
    te = pq.read_table(f"{E}/lead_{L}/test/{g}.parquet").to_pandas(); te["unit"]=te["unit"].astype(str)
    gs = pq.read_table(f"{E}/lead_{L}/guardside/{g}.parquet").to_pandas(); gs["unit"]=gs["unit"].astype(str)
    def exp_all(df, end):
        out = np.full(len(df), np.nan)
        for i,(u,e) in enumerate(zip(df["unit"], end)):
            if u in csum.columns and e in csum.index and ccnt.at[e,u]>0: out[i]=csum.at[e,u]/ccnt.at[e,u]
        return out
    end_fit = (te["issue"] if L>0 else te["time"]-1).to_numpy()
    for name, df in (("refit", tr[tr["r_refit"]]), ("test", te)):
        end = (df["issue"] if L>0 else df["time"]-1).to_numpy()
        e = exp_all(df, end); v = df["x__hist_mean_all"].to_numpy(np.float64); ok=np.isfinite(e)&np.isfinite(v)
        print(g,"lead",L,name,"hist_mean_all == expanding mean of y through issue (lead0: t-1): %.4f (n=%d of %d)" % (np.isclose(v[ok],e[ok],rtol=1e-4,atol=1e-3).mean(), ok.sum(), len(df)))
    # guardside: which rows differ and what are h__ values
    m = tr.merge(gs, on=["unit","time","issue"], how="inner")
    a = m["x__hist_last_1"].to_numpy(np.float64); b = m["h__hist_last_1"].to_numpy(np.float64)
    diff = ~((np.isnan(a)&np.isnan(b)) | np.isclose(a,b,equal_nan=False))
    print("   guardside rows", len(m), "x__ != h__ hist_last_1:", int(diff.sum()), "| of which x finite & h NaN:", int((diff & np.isfinite(a) & np.isnan(b)).sum()),
          "| time range of differing rows:", (int(m.loc[diff,"time"].min()), int(m.loc[diff,"time"].max())) if diff.any() else None)
    # guard-cut: h__ for guard rows (time > guard cut) -- is hist_last_1 the y at issue or NaN beyond guard cut?
    dd = m.loc[diff, ["unit","time","issue","x__hist_last_1","h__hist_last_1"]].head(5)
    print(dd.to_string())
