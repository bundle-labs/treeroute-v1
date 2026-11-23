import numpy as np, pandas as pd, pyarrow.parquet as pq
E = r"D:/treeroute/rival_export/pm25/20261007_74e67609"
R = r"D:/treeroute/runs/pm25/headline/20261007_74e67609"
g = "thar_desert"
tp = pq.read_table(f"{R}/test_preds.parquet", columns=["unit","group","time","y"]).to_pandas()
tp = tp[tp["group"].astype(str)==g][["unit","time","y"]]; tp["unit"]=tp["unit"].astype(str)
for L in (0,6):
    tr = pq.read_table(f"{E}/lead_{L}/train/{g}.parquet").to_pandas(); tr["unit"]=tr["unit"].astype(str)
    lab = pd.concat([tr[["unit","time","y"]], tp]).drop_duplicates(["unit","time"]).sort_values(["unit","time"])
    first = lab.groupby("unit")["time"].min()
    labi = lab.set_index(["unit","time"])["y"]
    gs = pq.read_table(f"{E}/lead_{L}/guardside/{g}.parquet").to_pandas(); gs["unit"]=gs["unit"].astype(str)
    te = pq.read_table(f"{E}/lead_{L}/test/{g}.parquet").to_pandas(); te["unit"]=te["unit"].astype(str)
    # expanding mean through the issue time (lead>0) or through t-1 (lead 0), and 60-month mean
    def expected(df, kind):
        end = df["issue"] if L>0 else df["time"]-1
        out=[]
        for u, e in zip(df["unit"], end):
            s = lab[(lab["unit"]==u)]
            if kind=="all": w = s[s["time"]<=e]["y"]
            else: w = s[(s["time"]<=e)&(s["time"]>e-60)]["y"]
            out.append(w.mean() if len(w) else np.nan)
        return np.array(out)
    for name, df, col in (("refit", tr[tr["r_refit"]].sample(300, random_state=0), "x__"),
                          ("test", te.sample(200, random_state=0), "x__")):
        for kind, c in (("all","hist_mean_all"),("60","hist_mean_60")):
            e = expected(df, kind); v = df[col+c].to_numpy(np.float64)
            ok = np.isfinite(e)&np.isfinite(v)
            print("lead",L,name,c,"= expanding mean through issue: %.3f (n=%d)" % (np.isclose(v[ok],e[ok],rtol=1e-4,atol=1e-3).mean(), ok.sum()))
    # guardside h__ vs x__ on guard-side rows
    m = tr.merge(gs, on=["unit","time","issue"], how="inner")
    for c in ("hist_last_1","hist_mean_12","hist_mean_all"):
        a = m["x__"+c].to_numpy(np.float64); b = m["h__"+c].to_numpy(np.float64); ok=np.isfinite(a)&np.isfinite(b)
        print("lead",L,"guardside rows",len(m), c, "x__ == h__ share %.4f" % np.isclose(a[ok],b[ok]).mean())
    # nfit vs ngd normal; normal = cell x month climatology? check constant per unit x month
    for col in ("nfit__identity",):
        s = tr.groupby(["unit", tr["time"]%12])[col].nunique().max()
        print("lead",L,col,"max distinct values per unit x month on train:", s)
    s = te.groupby(["unit", te["time"]%12])["nfit__identity"].nunique().max()
    print("lead",L,"test nfit max distinct per unit x month:", s)
    # does test nfit equal the mean of y over train rows <= fit cut per unit x month?
    fc = int(tr["time"].max())
    clim = tr[tr["time"]<=fc].groupby(["unit", tr["time"]%12])["y"].mean()
    k = pd.MultiIndex.from_arrays([te["unit"], te["time"]%12])
    print("lead",L,"test nfit vs plain unit x month mean of y<=fit cut: max abs gap %.4f" % np.nanmax(np.abs(te["nfit__identity"].to_numpy()-clim.reindex(k).to_numpy())))
