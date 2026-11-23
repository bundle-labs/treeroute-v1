# trend_strata.py -- POST-HOC (owner question 2026-10-22): is our model stronger than Ridge where PM2.5 has no trend?
# Units (the 1,905 scored test locations) are grouped by information known BEFORE the test years:
#   S1 pre-test slope: OLS slope of the unit's yearly mean PM2.5 over 2013-2019, in % of its 2013-2019 mean per year;
#   S2 pre-test drift: mean of (y - unit-month normal) over 2017-2019, in % of the unit's mean normal
#      (normal = per unit, per calendar month mean of 2003-2019 labels, as the engine's identity normal).
# A third, OUTCOME-CONDITIONAL grouping (S3, test-years drift) is printed separately and must be labelled so.
# Scores: our pinned model (arm__log_c_corrector_unweighted), our headline answer (= the normal at lead 12), the
# rivals' guarded answers (the deciding column) and the normal. d = rival MAE - ours, averaged over groups (regions) as on
# the board, with a leave-one-group-out jackknife 95% interval. Read-only; writes only into this folder.
import os, glob, numpy as np, pandas as pd, pyarrow.parquet as pq

RUN = r"D:\treeroute\runs\pm25\headline\20261007_74e67609"
BOARD = r"D:\treeroute\rivals\pm25\20261007_74e67609"
EXP0 = r"D:\treeroute\rival_export\pm25\20261007_74e67609\lead_0"
HERE = os.path.dirname(os.path.abspath(__file__))

def preds(L):
    p = os.path.join(RUN, "test_preds.parquet") if L == 0 else os.path.join(RUN, "ladder", "lead_%d" % L, "test_preds.parquet")
    d = pq.read_table(p, columns=["unit", "group", "time", "y", "normal", "arm__log_c_corrector_unweighted"]).to_pandas()
    d = d.rename(columns={"arm__log_c_corrector_unweighted": "ours"})
    d["answer"] = d["normal"] if L == 12 else d["ours"]           # lead 12: our guard failed, the headline is the normal
    for r in ("ridge", "rf", "lgbm"):
        q = pq.read_table(os.path.join(BOARD, "lead_%d" % L, "preds_%s.parquet" % r), columns=["unit", "time", "arm__rival_" + r]).to_pandas()
        d = d.merge(q.rename(columns={"arm__rival_" + r: r}), on=["unit", "time"], how="left", validate="one_to_one")
    assert len(d) == 91440
    return d[np.isfinite(d.y)]

# --- pre-test unit features from the export's lead-0 training labels (2003-2019) ---
units = set(pq.read_table(os.path.join(RUN, "test_preds.parquet"), columns=["unit"]).to_pandas().unit)
hist = []
for f in sorted(glob.glob(os.path.join(EXP0, "train", "*.parquet"))):
    t = pq.read_table(f, columns=["unit", "time", "y", "r_refit"]).to_pandas()
    hist.append(t[t.unit.isin(units) & t.r_refit.astype(bool)][["unit", "time", "y"]])
h = pd.concat(hist, ignore_index=True)
h["year"] = (h.time - 1) // 12; h["month"] = (h.time - 1) % 12 + 1
assert h.year.min() == 2003 and h.year.max() == 2019
norm = h.groupby(["unit", "month"]).y.mean().rename("nm")
h = h.join(norm, on=["unit", "month"])
feat = []
for u, g in h.groupby("unit"):
    a = g[g.year >= 2013].groupby("year").y.mean().dropna()
    slope = 100 * np.polyfit(a.index.values, a.values, 1)[0] / a.mean() if len(a) >= 5 and a.mean() > 0 else np.nan
    r = g[g.year >= 2017].dropna(subset=["y"])
    drift = 100 * (r.y - r.nm).mean() / g.nm.mean() if len(r) and g.nm.mean() > 0 else np.nan
    feat.append((u, slope, drift))
feat = pd.DataFrame(feat, columns=["unit", "slope_pct", "drift_pct"]).set_index("unit")

def jk(df, col):
    """Board-style d: mean over groups of (MAE rival - MAE ours) on the stratum's rows; LOGO jackknife 95% CI."""
    m = df.assign(e_r=(df[col] - df.y).abs(), e_o=(df["answer"] - df.y).abs()).groupby("group")[["e_r", "e_o"]].mean()
    dg = (m.e_r - m.e_o).values; G = len(dg)
    if G < 3: return np.nan, np.nan, np.nan, G
    th = dg.mean(); loo = (dg.sum() - dg) / (G - 1)
    se = np.sqrt((G - 1) / G * ((loo - loo.mean()) ** 2).sum())
    return th, th - 1.96 * se, th + 1.96 * se, G

def strata_table(d, key, bins, labels, title, out_rows, L):
    s = pd.cut(d[key], bins=bins, labels=labels)
    for lab in labels:
        x = d[s == lab]
        if len(x) == 0: continue
        row = dict(lead=L, grouping=title, stratum=lab, units=x.unit.nunique(), regions=x.group.nunique(), rows=len(x))
        for c in ("answer", "ours", "ridge", "rf", "lgbm", "normal"):
            row["mae_" + c] = (x[c] - x.y).abs().mean()
        for r in ("ridge", "rf", "lgbm"):
            th, lo, hi, G = jk(x, r)
            row["d_%s" % r] = th; row["d_%s_lo" % r] = lo; row["d_%s_hi" % r] = hi
        uw = x.assign(e_r=(x.ridge - x.y).abs(), e_o=(x.answer - x.y).abs()).groupby("unit")[["e_r", "e_o"]].mean()
        row["units_ours_better_than_ridge"] = int((uw.e_o < uw.e_r).sum())
        out_rows.append(row)

rows = []
for L in (0, 6, 12):
    d = preds(L).join(feat, on="unit")
    td = d.groupby("unit").apply(lambda g: 100 * (g.y - g.normal).mean() / g.normal.mean()).rename("test_drift_pct")
    d = d.join(td, on="unit")
    sb = [-np.inf, -3, -1, 1, 3, np.inf]; sl = ["falling >3%/yr", "falling 1-3%/yr", "flat (within 1%/yr)", "rising 1-3%/yr", "rising >3%/yr"]
    strata_table(d, "slope_pct", sb, sl, "S1 pre-test slope 2013-19", rows, L)
    db = [-np.inf, -15, -5, 5, 15, np.inf]; dl = ["below normal >15%", "below normal 5-15%", "near normal (within 5%)", "above normal 5-15%", "above normal >15%"]
    strata_table(d, "drift_pct", db, dl, "S2 pre-test drift 2017-19", rows, L)
    strata_table(d, "test_drift_pct", db, dl, "S3 OUTCOME-CONDITIONAL test drift 2020-23", rows, L)
    strata_table(d.assign(one=0.0), "one", [-1, 1], ["all rows"], "all", rows, L)
    if L == 12:                                                   # secondary: our model the guard set aside
        dm = d.assign(answer=d.ours)
        strata_table(dm, "slope_pct", sb, sl, "S1 pre-test slope 2013-19 [our REJECTED model, secondary]", rows, L)
        strata_table(dm, "drift_pct", db, dl, "S2 pre-test drift 2017-19 [our REJECTED model, secondary]", rows, L)
        strata_table(dm.assign(one=0.0), "one", [-1, 1], ["all rows"], "all [our REJECTED model, secondary]", rows, L)
res = pd.DataFrame(rows)
res.to_csv(os.path.join(HERE, "trend_strata.csv"), index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
for (L, gname), t in res.groupby(["lead", "grouping"], sort=False):
    print("\n== lead %d | %s" % (L, gname))
    print(t[["stratum", "units", "regions", "mae_answer", "mae_ridge", "mae_rf", "mae_lgbm", "mae_normal", "d_ridge", "d_ridge_lo", "d_ridge_hi",
             "d_rf", "d_lgbm", "units_ours_better_than_ridge"]].round(3).to_string(index=False))
