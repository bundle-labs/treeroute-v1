"""Leak-free expanding MMM, real DHW, and the model that finally has a LOCAL thermal reference.

    py -3.9 -u coral_dhw_model.py
    py -3.9 -u coral_dhw_model.py --trees 800 --seed 1

WHAT CHANGED FROM coral_smoke_rf.py. That run had no climatology, so its heat features were
degree-days above GLOBAL cutoffs (29 C, 30 C) and anomalies against the site's own trailing year.
It scored AUC 0.639, and its top importances were the site-relative anomalies -- a hint that a real
LOCAL reference was the missing ingredient. This script builds that reference properly.

THE MMM, AND WHY IT IS LEAK-FREE. For an observation at date t, the climatology uses ONLY that
pixel's SST strictly BEFORE t:
  * mean SST per calendar month per year, over the pre-t record;
  * for each calendar month, a linear fit of that monthly mean against year;
  * each fit evaluated at EPOCH 1988.2857 -- which de-trends the warming so the threshold does not
    drift upward as the ocean warms;
  * MMM = the maximum of the twelve re-centred monthly values.
Every observation therefore gets a climatology its own future never touched. The operational CRW
product cannot say that: its MMM is fixed at 1985-2012, so for any dive before 2012 the baseline
contains the dive's own future.

WHY THE EPOCH IS PINNED AND NOT "CURRENT". Measured at Ofu on 2024-06-04 over the same 84 days:
published MMM 28.900 -> DHW 16.763; expanding MMM at epoch 1988.2857 -> DHW 16.635; expanding MMM at
CURRENT epoch -> MMM 29.886 and DHW 0.000. Warming has lifted the modern climatology above observed
SST, so a current-epoch baseline erases the entire heat-stress signal. EPOCH is a constant here and
must stay one.

DHW FOLLOWS CRW'S DEFINITION. HotSpot = SST - MMM. Only HotSpots of 1 C or more accumulate. DHW is
their sum over the trailing 84 days divided by 7, in degree-weeks. Note the consequence of the 1 C
gate: 0.9 C sustained for twelve weeks scores exactly zero while 1.0 C scores 12. That cliff is a
property of the metric, not a bug in this code, and it is one of the things a learned model can
exploit.

MIN_YEARS = 10 is required before an MMM is emitted, and mmm_n_years is carried as a column so a thin
early fit can be down-weighted rather than trusted equally. All 4,758 pilot sites start in 1985 and
have at least 14 years, so nothing is actually lost here -- but the guard stays for other regions.
"""
import argparse
import os
import sys
import warnings

warnings.filterwarnings("ignore")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "8")

import numpy as np
import pandas as pd

try:
    from sklearnex import patch_sklearn
    patch_sklearn(verbose=False)
except Exception:
    pass

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coral_smoke_rf import bundle

SST = r"D:\coral\drivers\sst_full_merged.parquet"
EV = r"D:\coral\target\events_dated.parquet"
PILOT = [6, 110, 17, 71, 93, 62, 40, 77, 2, 13]
EPOCH = 1988.2857
MIN_YEARS = 10
WIN = (30, 56, 84, 90, 180, 365)


def mmm_from(h, epoch=EPOCH):
    """Re-centred maximum monthly mean from a pre-t history. Returns (mmm, n_years) or (nan, 0)."""
    if len(h) < 365:
        return np.nan, 0
    yr = h["yr"].values
    mo = h["mo"].values
    s = h["sst"].values
    nyr = len(np.unique(yr))
    if nyr < MIN_YEARS:
        return np.nan, nyr
    best = -1e9
    for m in range(1, 13):
        sel = mo == m
        if sel.sum() < 60:
            continue
        yy, ss = yr[sel], s[sel]
        uy = np.unique(yy)
        if len(uy) < 3:
            continue
        means = np.array([ss[yy == u].mean() for u in uy])
        b, a = np.polyfit(uy.astype(float), means, 1)   # slope, intercept
        v = a + b * epoch
        if v > best:
            best = v
    return (best if best > -1e8 else np.nan), nyr


def build(ev, sst):
    by = {k: g.sort_values("time") for k, g in sst.groupby("key")}
    rows = []
    for i, (idx, e) in enumerate(ev.iterrows()):
        g = by.get(e.key)
        if g is None:
            continue
        h = g[g.time < e.date]
        if len(h) < 365 * MIN_YEARS // 2:
            continue
        mmm, nyr = mmm_from(h)
        if not np.isfinite(mmm):
            continue
        t = h["sst"].values
        tm = h["time"].values
        hs_all = t - mmm                                   # HotSpot over the whole pre-t record
        f = dict(sid=idx, eco=e.eco, side=e.side, pos=int(e.pos), date=e.date,
                 abslat=abs(e.lat), mmm=mmm, mmm_n_years=nyr,
                 month=e.date.month,
                 doy_sin=np.sin(2 * np.pi * e.date.dayofyear / 365.25),
                 doy_cos=np.cos(2 * np.pi * e.date.dayofyear / 365.25))
        for w in WIN:
            v = t[-w:]
            hs = hs_all[-w:]
            if len(v) < max(10, w // 4):
                continue
            gated = np.where(hs >= 1.0, np.clip(hs, 0, None), 0.0)
            f["dhw_%d" % w] = gated.sum() / 7.0            # CRW definition: >=1 C gate, /7
            f["hs_max_%d" % w] = float(np.max(hs))
            f["n_above_mmm_%d" % w] = int((hs > 0).sum())
            f["n_above_mmm1_%d" % w] = int((hs >= 1).sum())
            f["mean_%d" % w] = v.mean()
            f["std_%d" % w] = v.std()
            f["cool_%d" % w] = float(np.clip(-hs, 0, None).sum() / 7.0)   # cooling accumulation
        yr = hs_all[-365:] if len(hs_all) >= 365 else hs_all
        f["days_since_max_hs"] = int(len(yr) - 1 - int(np.argmax(yr)))
        f["slope_90"] = np.polyfit(np.arange(min(90, len(t))), t[-90:], 1)[0] if len(t) >= 90 else 0.0
        # C19 prior thermal stress -- acclimatisation / memory, strictly from the pre-t record
        gated_all = np.where(hs_all >= 1.0, np.clip(hs_all, 0, None), 0.0)
        roll = pd.Series(gated_all).rolling(84, min_periods=84).sum().values / 7.0
        roll = roll[np.isfinite(roll)]
        f["lifetime_dhw"] = float(gated_all.sum() / 7.0)
        f["n_dhw_ge4_before"] = int((roll >= 4).sum())
        f["n_dhw_ge8_before"] = int((roll >= 8).sum())
        f["max_dhw_before"] = float(roll.max()) if len(roll) else 0.0
        if len(roll):
            last = np.where(roll >= 4)[0]
            f["days_since_dhw4"] = int(len(roll) - 1 - last[-1]) if len(last) else 99999
        else:
            f["days_since_dhw4"] = 99999
        rows.append(f)
        if (i + 1) % 1500 == 0:
            print("   ... %d/%d" % (i + 1, len(ev)), flush=True)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trees", type=int, default=600)
    ap.add_argument("--seed", type=int, default=0)
    A = ap.parse_args()

    print("=" * 80); print("LOAD"); print("=" * 80)
    sst = pd.read_parquet(SST)
    sst["key"] = sst.site_lat.round(4).astype(str) + "|" + sst.site_lon.round(4).astype(str)
    sst["yr"] = sst.time.dt.year
    sst["mo"] = sst.time.dt.month
    ev = pd.read_parquet(EV)
    ev = ev[ev.eco.isin(PILOT)].copy()
    ev["key"] = ev.lat.round(4).astype(str) + "|" + ev.lon.round(4).astype(str)
    ev = ev[ev.key.isin(sst.key.unique())]
    print("   sst %s rows / %d sites | pilot events %s"
          % (format(len(sst), ","), sst.key.nunique(), format(len(ev), ",")))

    print("\n" + "=" * 80); print("LEAK-FREE MMM + DHW"); print("=" * 80)
    X = build(ev, sst)
    fcols = [c for c in X.columns if c not in ("sid", "eco", "side", "pos", "date")]
    print("   %s rows x %d features" % (format(len(X), ","), len(fcols)))
    print("   MMM: median %.2f C | range %.2f .. %.2f | baseline years median %d"
          % (X.mmm.median(), X.mmm.min(), X.mmm.max(), X.mmm_n_years.median()))
    print("   DHW at the dive (84 d): median %.2f | p90 %.2f | max %.2f | %% >=4  %.1f%%"
          % (X.dhw_84.median(), X.dhw_84.quantile(.9), X.dhw_84.max(), 100 * (X.dhw_84 >= 4).mean()))

    tr, te = X[X.side == "donor"], X[X.side == "test"]
    print("\n   TRAIN %s rows, %d ecoregions, %.1f%% positive"
          % (format(len(tr), ","), tr.eco.nunique(), 100 * tr.pos.mean()))
    print("   TEST  %s rows, %d ecoregions, %.1f%% positive"
          % (format(len(te), ","), te.eco.nunique(), 100 * te.pos.mean()))

    print("\n" + "=" * 80); print("RESULTS on the held-out regions"); print("=" * 80)
    rf = RandomForestClassifier(n_estimators=A.trees, min_samples_leaf=5, n_jobs=-1,
                                random_state=A.seed, class_weight="balanced_subsample",
                                oob_score=True, bootstrap=True)
    rf.fit(tr[fcols].fillna(0).values.astype(np.float32), tr.pos.values)
    p = rf.predict_proba(te[fcols].fillna(0).values.astype(np.float32))[:, 1]

    auc_rf = roc_auc_score(te.pos.values, p)
    auc_dhw = roc_auc_score(te.pos.values, te.dhw_84.fillna(0).values)
    auc_hs = roc_auc_score(te.pos.values, te.hs_max_84.fillna(0).values)
    n1, n2 = int(te.pos.sum()), int((1 - te.pos).sum())
    Q1, Q2 = auc_rf / (2 - auc_rf), 2 * auc_rf ** 2 / (1 + auc_rf)
    se = np.sqrt((auc_rf * (1 - auc_rf) + (n1 - 1) * (Q1 - auc_rf ** 2)
                  + (n2 - 1) * (Q2 - auc_rf ** 2)) / (n1 * n2))
    print("   AUC  random forest (local MMM)  : %.4f   95%% CI [%.4f, %.4f]"
          % (auc_rf, auc_rf - 1.96 * se, auc_rf + 1.96 * se))
    print("   AUC  DHW alone (84 d)           : %.4f   <- the operational heat-stress metric" % auc_dhw)
    print("   AUC  max HotSpot alone (84 d)   : %.4f" % auc_hs)
    print("   [previous run, no climatology   : 0.6392 forest / 0.5721 heat-only]")

    print("\n   THE OPERATIONAL ALERT, scored as a manager would use it (DHW >= 4):")
    b = bundle(te.pos.values, te.dhw_84.fillna(0).values, 4.0)
    for k in ("tp", "fp", "fn", "tn"):
        print("      %-18s %s" % (k, b[k]))
    for k in ("hit_rate", "false_alarm_ratio", "ets", "tss"):
        print("      %-18s %.4f" % (k, b[k]))

    oob = rf.oob_decision_function_[:, 1]
    ok = np.isfinite(oob)
    cand = np.quantile(oob[ok], np.linspace(0.05, 0.95, 37))
    tuned = max((bundle(tr.pos.values[ok], oob[ok], t) for t in cand), key=lambda x: x["tss"])
    print("\n   THE FOREST, threshold %.4f chosen on TRAIN out-of-bag and frozen:" % tuned["thr"])
    bf = bundle(te.pos.values, p, tuned["thr"])
    for k in ("tp", "fp", "fn", "tn"):
        print("      %-18s %s" % (k, bf[k]))
    for k in ("hit_rate", "false_alarm_ratio", "ets", "tss"):
        print("      %-18s %.4f" % (k, bf[k]))
    print("\n   ETS: forest %.4f vs operational alert %.4f  (anchor to beat: 0.150)"
          % (bf["ets"], b["ets"]))

    print("\n   per-region AUC (test regions with >=20 obs and both classes):")
    te2 = te.assign(pred=p)
    r = []
    for e, g in te2.groupby("eco"):
        if len(g) < 20 or g.pos.nunique() < 2:
            continue
        r.append(dict(eco=int(e), n=len(g), pos=int(g.pos.sum()),
                      auc_rf=roc_auc_score(g.pos, g.pred),
                      auc_dhw=roc_auc_score(g.pos, g.dhw_84.fillna(0))))
    t2 = pd.DataFrame(r).sort_values("auc_rf", ascending=False)
    print(t2.to_string(index=False))
    if len(t2):
        w = int((t2.auc_rf > t2.auc_dhw).sum())
        print("\n   forest beats DHW-alone in %d of %d regions" % (w, len(t2)))

    imp = pd.Series(rf.feature_importances_, index=fcols).sort_values(ascending=False)
    print("\n   top 14 features:")
    for k, v in imp.head(14).items():
        print("      %-20s %.4f" % (k, v))
    X.to_parquet("dhw_features.parquet", index=False)
    te2.to_csv("dhw_predictions.csv", index=False)
    print("\n   saved -> dhw_features.parquet, dhw_predictions.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
