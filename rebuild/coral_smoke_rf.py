"""Smoke test: build heat features from the cached SST, fit a random forest, score it honestly.

    py -3.9 -u coral_smoke_rf.py
    py -3.9 -u coral_smoke_rf.py --trees 600 --seed 1

WHAT THIS IS. The first end-to-end pass: observations -> features -> model -> metrics, on whatever
tiles coral_fetch_sst.py has cached. It exists to find out whether the pipeline produces a signal at
all, not to produce a publishable number.

THE ONE LIMITATION THAT MATTERS, STATED UP FRONT. Every CRW heat-stress product (DHW, HotSpot, SSTA,
alert level) is defined against a MAXIMUM MONTHLY MEAN climatology, and a climatology needs decades of
history per pixel. The tile cache holds only ~370 days before each observation, because that is what
makes the fetch affordable. So THIS SMOKE HAS NO CLIMATOLOGY-BASED FEATURES AND THEREFORE NO DHW.

What it uses instead is legitimate but weaker:
  * absolute thermal statistics over windows ending at the observation date,
  * accumulated degree-days above fixed physiological thresholds (29 C, 30 C) -- a DHW-shaped feature
    with a GLOBAL threshold rather than a local one,
  * the site's own trailing-year baseline as a crude anomaly reference,
  * seasonal position and absolute latitude.
Because the thresholds are global rather than per-reef, this smoke CANNOT express the single thing
the architecture is supposed to exploit -- that the same heat means different things on different
reefs. Expect it to underperform, and do not read a weak result as a verdict on the design.

Adding real DHW means pulling each site's full 1985-to-observation history and computing an
expanding-window MMM with EPOCH pinned at 1988.2857 (a current-epoch MMM drives DHW to 0.000 because
warming has lifted the modern climatology above observed SST). That is the full run, not this one.

LEAK DISCIPLINE HELD HERE. Every feature is computed strictly from SST dated BEFORE the observation.
No raw latitude/longitude is used as a model input -- only |latitude|, which is solar geometry rather
than an address; raw coordinates would let the forest memorise the region and would break the
donor-to-test transfer claim by construction.
"""
import argparse
import glob
import os
import warnings

warnings.filterwarnings("ignore")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "8")

import numpy as np
import pandas as pd

try:                                     # ~11x faster forests on this machine, identical semantics
    from sklearnex import patch_sklearn
    patch_sklearn(verbose=False)
except Exception:
    pass

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, confusion_matrix

SST = r"D:\coral\drivers\sst"
EV = r"D:\coral\target\events_dated.parquet"
WINDOWS = (7, 14, 30, 56, 84, 180, 365)


def load_sst():
    fs = sorted(glob.glob(os.path.join(SST, "*.parquet")))
    if not fs:
        raise SystemExit("no tiles in %s -- run coral_fetch_sst.py first" % SST)
    d = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    d = d.dropna(subset=["sst"])
    d["key"] = d.site_lat.round(4).astype(str) + "|" + d.site_lon.round(4).astype(str)
    print("   tiles %d | sst rows %s | sites %d | span %s .. %s"
          % (len(fs), format(len(d), ","), d.key.nunique(),
             d.time.min().date(), d.time.max().date()))
    return d


def features(ev, sst):
    """One row per observation. Every statistic uses only SST strictly before the dive date."""
    by = {k: g.sort_values("time") for k, g in sst.groupby("key")}
    rows = []
    for _, e in ev.iterrows():
        k = "%.4f|%.4f" % (e.lat, e.lon)
        g = by.get(k)
        if g is None:
            continue
        h = g[g.time < e.date]
        if len(h) < 120:                        # too little history to characterise the site
            continue
        t = h.sst.values
        tm = h.time.values
        f = dict(sid=e.name, eco=e.eco, side=e.side, pos=int(e.pos), date=e.date,
                 abslat=abs(e.lat), match_km=float(g.match_km.iloc[0]),
                 month=e.date.month,
                 doy_sin=np.sin(2 * np.pi * e.date.dayofyear / 365.25),
                 doy_cos=np.cos(2 * np.pi * e.date.dayofyear / 365.25))
        base = t[-365:] if len(t) >= 365 else t
        f["base_mean"] = base.mean()
        f["base_max"] = base.max()
        for w in WINDOWS:
            v = t[-w:]
            if len(v) < max(3, w // 4):
                continue
            f["mean_%d" % w] = v.mean()
            f["max_%d" % w] = v.max()
            f["min_%d" % w] = v.min()
            f["std_%d" % w] = v.std()
            f["anom_%d" % w] = v.mean() - f["base_mean"]        # site-relative, not climatological
            for thr in (29.0, 30.0):
                ex = np.clip(v - thr, 0, None)
                f["dd%d_%d" % (int(thr), w)] = ex.sum() / 7.0   # degree-WEEKS above a fixed threshold
                f["nday%d_%d" % (int(thr), w)] = int((v > thr).sum())
        f["slope_30"] = np.polyfit(np.arange(min(30, len(t))), t[-30:], 1)[0] if len(t) >= 30 else 0.0
        f["slope_90"] = np.polyfit(np.arange(min(90, len(t))), t[-90:], 1)[0] if len(t) >= 90 else 0.0
        yr = t[-365:] if len(t) >= 365 else t
        f["days_since_max"] = int(len(yr) - 1 - int(np.argmax(yr)))
        rows.append(f)
    return pd.DataFrame(rows)


def bundle(y, p, thr):
    """The accuracy bundle: never a bare AUC."""
    yhat = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, yhat, labels=[0, 1]).ravel()
    n = tn + fp + fn + tp
    hit = tp / max(tp + fn, 1)
    far = fp / max(fp + tp, 1)                       # false-alarm RATIO
    fpr = fp / max(fp + tn, 1)
    ref = (tp + fp) * (tp + fn) / max(n, 1)
    ets = (tp - ref) / max(tp + fp + fn - ref, 1e-9)
    tss = hit - fpr
    return dict(thr=thr, tp=tp, fp=fp, fn=fn, tn=tn, hit_rate=hit,
                false_alarm_ratio=far, ets=ets, tss=tss, acc=(tp + tn) / max(n, 1))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trees", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    A = ap.parse_args()

    print("=" * 78); print("LOADING"); print("=" * 78)
    sst = load_sst()
    ev = pd.read_parquet(EV)
    ev["key"] = ev.lat.round(4).astype(str) + "|" + ev.lon.round(4).astype(str)
    ev = ev[ev.key.isin(sst.key.unique())]
    print("   observations with a cached tile: %s" % format(len(ev), ","))

    print("\n" + "=" * 78); print("FEATURES"); print("=" * 78)
    X = features(ev, sst)
    if not len(X):
        raise SystemExit("no observation had enough history")
    fcols = [c for c in X.columns if c not in ("sid", "eco", "side", "pos", "date")]
    print("   built %s rows x %d features | donor %s | test %s"
          % (format(len(X), ","), len(fcols),
             format(int((X.side == "donor").sum()), ","),
             format(int((X.side == "test").sum()), ",")))
    print("   pixel match distance: median %.2f km, max %.2f km"
          % (X.match_km.median(), X.match_km.max()))

    tr, te = X[X.side == "donor"], X[X.side == "test"]
    if len(te) < 30 or te.pos.nunique() < 2:
        print("\n   TEST SIDE TOO THIN (%d rows, %d classes) -- falling back to a 70/30 split"
              " WITHIN the donor regions, grouped by ecoregion." % (len(te), te.pos.nunique()))
        ecos = tr.eco.drop_duplicates().sample(frac=1, random_state=A.seed)
        cut = ecos.iloc[:max(1, int(0.3 * len(ecos)))]
        te, tr = tr[tr.eco.isin(cut)], tr[~tr.eco.isin(cut)]
    print("\n   TRAIN %s rows, %d ecoregions, %.1f%% positive"
          % (format(len(tr), ","), tr.eco.nunique(), 100 * tr.pos.mean()))
    print("   TEST  %s rows, %d ecoregions, %.1f%% positive"
          % (format(len(te), ","), te.eco.nunique(), 100 * te.pos.mean()))

    print("\n" + "=" * 78); print("RANDOM FOREST"); print("=" * 78)
    Xtr = tr[fcols].fillna(0).values.astype(np.float32)
    Xte = te[fcols].fillna(0).values.astype(np.float32)
    rf = RandomForestClassifier(n_estimators=A.trees, min_samples_leaf=5, n_jobs=-1,
                                random_state=A.seed, class_weight="balanced_subsample",
                                oob_score=True, bootstrap=True)
    rf.fit(Xtr, tr.pos.values)
    p = rf.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(te.pos.values, p)

    # baselines
    base_rate = tr.pos.mean()
    p_base = np.full(len(te), base_rate)
    heat = te["max_84"].fillna(te["max_84"].median()).values if "max_84" in te else np.zeros(len(te))
    auc_heat = roc_auc_score(te.pos.values, heat)

    print("   AUC  random forest      : %.4f" % auc)
    print("   AUC  max SST in 84 d    : %.4f   <- single-feature 'heat only' baseline" % auc_heat)
    print("   AUC  always-base-rate   : 0.5000 (by construction)")
    # THRESHOLD IS CHOSEN ON TRAIN OUT-OF-BAG PREDICTIONS AND THEN FROZEN.
    # Choosing it by maximising TSS on the TEST predictions -- which an earlier version of this
    # script did -- is threshold tuning on the test set. It inflates every metric in the bundle and
    # is exactly the kind of quiet optimism this project bans elsewhere. The test set is scored once,
    # at a threshold it never saw.
    oob = rf.oob_decision_function_[:, 1]
    ok = np.isfinite(oob)
    cand = np.quantile(oob[ok], np.linspace(0.05, 0.95, 37))
    tuned = max((bundle(tr.pos.values[ok], oob[ok], t) for t in cand), key=lambda b: b["tss"])
    thr = tuned["thr"]
    print("\n   threshold %.4f chosen on TRAIN out-of-bag (TSS %.4f there), frozen for TEST:"
          % (thr, tuned["tss"]))
    best = bundle(te.pos.values, p, thr)
    for k in ("thr", "tp", "fp", "fn", "tn"):
        print("      %-18s %s" % (k, best[k]))
    for k in ("hit_rate", "false_alarm_ratio", "ets", "tss", "acc"):
        print("      %-18s %.4f" % (k, best[k]))
    print("\n   anchors to beat: ETS 0.150 (DeCarlo 2020, 100 sites, 1982-2016);"
          " DHW-only AUC 0.568 at 'any bleaching'")

    imp = pd.Series(rf.feature_importances_, index=fcols).sort_values(ascending=False)
    print("\n   top 12 features:")
    for k, v in imp.head(12).items():
        print("      %-18s %.4f" % (k, v))

    out = "smoke_rf_predictions.csv"
    te.assign(pred=p)[["eco", "side", "date", "pos", "pred"]].to_csv(out, index=False)
    print("\n   saved -> %s" % out)
    print("\n   READ THIS RESULT AS: 'can a forest on GLOBAL-threshold heat features transfer"
          " off-region at all', NOT as a verdict on the architecture. No DHW, no local threshold,"
          " no light/flow/depth drivers are present yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
