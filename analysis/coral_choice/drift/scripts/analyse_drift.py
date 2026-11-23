"""Analysis 2 (GLS weight drift) on the rebuilt weights (rebuild_weights.py output, byte-identical
records to the headline run). Plain python; reads the run read-only; writes under drift/out."""
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

RUN = Path(r"D:\treeroute\runs\coral\headline\20261020_f3b8e3da")
OUT = Path(r"D:\treeroute\analysis\coral_choice\drift\out")
m = pd.read_parquet(OUT / "rows.parquet")
key_of = {r: i for i, r in enumerate(m.row_id.tolist())}
names = json.loads((OUT / "fold_names.json").read_text())
fidx = {g: i for i, g in enumerate(names)}
sigF = np.load(OUT / "sig_folds.npy"); wF = np.load(OUT / "w_folds.npy"); fitF = np.load(OUT / "fit_folds.npy")
donor = pd.read_parquet(OUT / "donor_fit.parquet")
y_all = np.full(len(m), np.nan); y_all[donor.key.values] = donor.y.values
m["y"] = y_all
m["year"] = [dt.date.fromordinal(int(d)).year for d in m.day]
CUT_IN, CUT_FIT = 734868, 735963
m["period"] = np.where(m.day <= CUT_IN, "<=2012", np.where(m.day <= CUT_FIT, "2013-15", "test"))
lines = []


def P(s=""):
    print(s); lines.append(str(s))


def ybin(y):
    return pd.cut(y, [-0.001, 0.0, 20, 50, 101], labels=["0", "(0,20]", "(20,50]", ">50"])


def dbin(x):
    return pd.cut(x, [-1e9, 0.0, 4, 8, 1e9], labels=["0", "(0,4]", "(4,8]", ">8"])


# ------------------------------------------------------------------ A. the two kinds of model on the SAME rows
P("A. cut of every weight model: test %s, folds %s" % (CUT_IN, sorted(set(json.loads(json.dumps(
    [int(x) for x in [CUT_IN]])))) ))
don = m[m.period != "test"].copy()
k = don.index.values
mean_fold_sig = sigF[:, k].mean(axis=0)
don["sig_foldmean"] = mean_fold_sig
don["w_foldmean"] = wF[:, k].mean(axis=0)
# for each donor row, the fold model of the row's own group (what a surface row of that group uses)
own = np.array([fidx.get(g, -1) for g in don.group])
ok = own >= 0
don["w_ownfold"] = np.nan; don["sig_ownfold"] = np.nan
don.loc[ok, "w_ownfold"] = wF[own[ok], k[ok]]
don.loc[ok, "sig_ownfold"] = sigF[own[ok], k[ok]]
for per in ["<=2012", "2013-15"]:
    d = don[don.period == per]
    P("  %s donor rows %d: sigma test-model mean %.3f, fold-mean %.3f; corr(sig_T, sig_foldmean) %.4f; "
      "median |w_T/w_foldmean - 1| %.4f; max %.4f" % (
          per, len(d), d.sig_T.mean(), d.sig_foldmean.mean(), np.corrcoef(d.sig_T, d.sig_foldmean)[0, 1],
          np.median(np.abs(d.w_T / d.w_foldmean - 1)), np.max(np.abs(d.w_T / d.w_foldmean - 1))))
tab = don.groupby([don.period, ybin(don.y)], observed=True).agg(
    n=("y", "size"), err=("err_target", "mean"), sig_T=("sig_T", "mean"), sig_fold=("sig_foldmean", "mean"),
    w_T_x1e3=("w_T", lambda v: 1e3 * v.mean()), w_fold_x1e3=("w_foldmean", lambda v: 1e3 * v.mean()))
P("\nA1. sigma and weight by donor-row y level (err = cross-region error target; NaN after 2012: not a fit row)")
P(tab.round(3).to_string())
tab = don.groupby([don.period, don.s_programme], observed=True).agg(
    n=("y", "size"), ymean=("y", "mean"), sig_T=("sig_T", "mean"), sig_fold=("sig_foldmean", "mean"),
    w_T_x1e3=("w_T", lambda v: 1e3 * v.mean()), w_fold_x1e3=("w_foldmean", lambda v: 1e3 * v.mean()))
P("\nA2. by programme")
P(tab.round(3).to_string())
tab = don.groupby([don.period, dbin(don.f_dhw_84)], observed=True).agg(
    n=("y", "size"), ymean=("y", "mean"), sig_T=("sig_T", "mean"), sig_fold=("sig_foldmean", "mean"),
    w_T_x1e3=("w_T", lambda v: 1e3 * v.mean()), w_fold_x1e3=("w_foldmean", lambda v: 1e3 * v.mean()))
P("\nA3. by recent heat stress (dhw_84)")
P(tab.round(3).to_string())
P("\nA4. share of donor rows at the clip bounds (test model): low clip %.3f, high clip %.3f" % (
    (m.sig_T <= 6.5227).mean(), (m.sig_T >= 33.0154).mean()))
hy = don[(don.y > 50)]
P("    donor rows y>50: %d (<=2012 %d, 2013-15 %d); at high clip under test model %.3f, under fold-mean %.3f" % (
    len(hy), (hy.period == "<=2012").sum(), (hy.period == "2013-15").sum(), (hy.sig_T >= 33.0154).mean(),
    (hy.sig_foldmean >= 33.0).mean()))

# ------------------------------------------------------------------ B. pools
tp = pd.read_parquet(RUN / "test_preds.parquet")
ip = pd.read_parquet(RUN / "inner_preds.parquet", columns=["unit", "group", "time", "y"])
pt = pd.read_parquet(RUN / "pools_test_pass.parquet")
ps = pd.read_parquet(RUN / "pools_decision_surface.parquet")
ty = dict(zip(tp.unit, tp.y)); sy = dict(zip(ip.unit, ip.y))
tprog = dict(zip(tp.unit, tp.programme))
y_pool = m.y.values.copy()
for r, v in sy.items():                    # surface rows (2013-15) are donor rows of the test pass
    y_pool[key_of[r]] = v
arc = lambda y: np.arcsin(np.sqrt(np.clip(y, 0, 100) / 100.0))   # arcsine link of a percent (display only)


def pool_stats(row_id, pool_ids, wvec, yrow):
    kk = np.array([key_of[x] for x in pool_ids])
    yp = y_pool[kk]
    w = wvec[kk]; w = w / w.sum(); u = np.full(kk.size, 1.0 / kk.size)
    hi = yp > 50; ze = yp == 0
    newer = m.day.values[kk] > CUT_IN
    return {"row": row_id, "y": yrow, "n": kk.size, "ymean_u": yp.mean(), "ymean_w": (w * yp).sum(),
            "arc_u": (u * arc(yp)).sum(), "arc_w": (w * arc(yp)).sum(),
            "share_hi_u": hi.mean(), "share_hi_w": w[hi].sum(), "share_zero_u": ze.mean(), "share_zero_w": w[ze].sum(),
            "share_1315_u": newer.mean(), "share_1315_w": w[newer].sum(),
            "ess": 1.0 / (w ** 2).sum(), "w_ratio_hi": (w[hi].mean() / w[~hi].mean()) if hi.any() and (~hi).any() else np.nan}


def sev(y):
    return pd.cut(pd.Series(y), [-0.001, 0, 20, 50, 101], labels=["zero", "(0,20]", "(20,50]", "severe>=50"]).values


rows_t, rows_t_cf = [], []
for r in pt.itertuples():
    ids = json.loads(r.pool_row_ids)
    if not ids:
        continue
    rows_t.append(pool_stats(r.row_id, ids, m.w_T.values, ty[r.row_id]))
    g = m.group.values[key_of[r.row_id]]
    if g in fidx:                           # counterfactual: the fold model of the row's own group
        rows_t_cf.append(pool_stats(r.row_id, ids, wF[fidx[g]], ty[r.row_id]))
T = pd.DataFrame(rows_t); TC = pd.DataFrame(rows_t_cf)
T["sev"] = sev(T.y); TC["sev"] = sev(TC.y); T["prog"] = T.row.map(tprog)
rows_s = []
for r in ps.itertuples():
    ids = json.loads(r.pool_row_ids)
    if not ids:
        continue
    rows_s.append(pool_stats(r.row_id, ids, wF[fidx[r.part]], sy[r.row_id]))
S = pd.DataFrame(rows_s); S["sev"] = sev(S.y)
cols = ["n", "ymean_u", "ymean_w", "arc_u", "arc_w", "share_hi_u", "share_hi_w", "share_zero_u", "share_zero_w",
        "share_1315_u", "share_1315_w", "ess", "w_ratio_hi"]
agg = lambda D: D.groupby("sev", observed=True)[cols].mean().assign(rows=D.groupby("sev", observed=True).size())
P("\nB1. TEST pools (cut 2015, weights from the test-pass model), mean over scored rows by the row's own y")
P(agg(T).round(3).to_string())
P("\nB2. TEST pools re-weighted with the FOLD model of the row's own group (counterfactual; %d rows)" % len(TC))
P(agg(TC).round(3).to_string())
P("\nB3. SURFACE pools (cut 2012, weights from each row's fold model)")
P(agg(S).round(3).to_string())
P("\nB4. TEST severe rows by programme")
P(T[T.sev == "severe>=50"].groupby("prog")[["ymean_u", "ymean_w", "share_hi_u", "share_hi_w", "share_1315_u",
                                             "share_1315_w", "w_ratio_hi"]].mean().assign(
    rows=T[T.sev == "severe>=50"].groupby("prog").size()).round(3).to_string())
both = T.merge(TC[["row", "share_hi_w", "ymean_w"]], on="row", suffixes=("", "_cf"))
P("\nB5. test-model vs own-fold-model weights on the SAME test pools: mean |share_hi_w - share_hi_w_cf| %.4f; "
  "mean |ymean_w - ymean_w_cf| %.4f pct points" % (np.abs(both.share_hi_w - both.share_hi_w_cf).mean(),
                                                   np.abs(both.ymean_w - both.ymean_w_cf).mean()))
# pool candidates' periods
newest = lambda D, P_: None
T.to_parquet(OUT / "test_pool_stats.parquet"); S.to_parquet(OUT / "surface_pool_stats.parquet")
TC.to_parquet(OUT / "test_pool_stats_foldcf.parquet")
(OUT / "analysis_output.txt").write_text("\n".join(lines), encoding="utf-8")
