"""Regression smoke: predict PERCENT BLEACHED, and report MAE + R2 + hit-rate together.

    py -3.9 -u coral_smoke_regress.py

WHY THIS EXISTS SEPARATELY FROM coral_smoke_rf.py. That script fits a CLASSIFIER (bleached / not),
so R2 and MAE are undefined for it. The underlying target is continuous, and the project's reporting
rule is MAE + R2 + hit-rate against a stated baseline, never one of them alone. This fits a
RandomForestRegressor on the same features and reports the bundle.

HOW THE CONTINUOUS TARGET IS BUILT, AND WHAT IS DELIBERATELY EXCLUDED.
  * Reef Check  -> mean(S1..S4) of the POPULATION rows only. The segments are already percentages
    (max 100, 90.5% are exact multiples of 2.5), so they are AVERAGED, never summed -- summing
    inflates 4x. Population is prevalence; the Colony rows are severity, a different quantity
    (r = 0.57, 2.85x apart in level), and mixing them is the defect that plausibly explains the
    field's coin-flip DHW result.
  * AGRRA, FRRP, McClanahan, and the Donner rows that carry it -> Percent_Bleached directly.
  * Kumagai and Safaie are EXCLUDED. They carry only an ordinal code, and converting an ordinal to a
    percentage requires substituting class midpoints -- which is precisely the fabrication found in
    the BCO-DMO flat CSV, where 100% of Kumagai's percentages are invented and four values carry
    56.8% of all mass. Inventing numbers to enlarge n is not a gain.

BASELINES, because an R2 without one is meaningless on a zero-inflated target:
  * global train mean  -- the naive constant.
  * PER-REGION train mean -- "guess the regional average". This is the honest baseline here, the
    analogue of per-cell-month climatology in the NDVI work, and it is much harder to beat.
  Note the per-region baseline uses each TEST region's own TRAIN-side mean where one exists; for a
  region with no training rows it falls back to the global mean, which is the realistic deployment
  case for a region the model has never seen.
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "8")

import numpy as np
import pandas as pd
import sqlite3

try:
    from sklearnex import patch_sklearn
    patch_sklearn(verbose=False)
except Exception:
    pass

from sklearn.ensemble import RandomForestRegressor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coral_smoke_rf import load_sst, features, WINDOWS

DB = r"D:\coral\target\raw\gcbd\Global_Coral_Bleaching_Database_SQLite_11_24_21.db"
EV = r"D:\coral\target\events_dated.parquet"


def continuous_target():
    c = sqlite3.connect(DB)
    t = pd.read_sql("""
        SELECT b.Sample_ID sid, ds.Data_Source src, b.Bleaching_Level lvl,
               b.Percent_Bleached pct, b.S1, b.S2, b.S3, b.S4
        FROM Bleaching_tbl b
        JOIN Sample_Event_tbl se ON se.Sample_ID = b.Sample_ID
        JOIN Site_Info_tbl si    ON si.Site_ID   = se.Site_ID
        JOIN Data_Source_LUT ds  ON ds.Data_Source_ID = si.Data_Source""", c)
    for k in ("pct", "S1", "S2", "S3", "S4", "lvl"):
        t[k] = pd.to_numeric(t[k], errors="coerce")
    rc = t[(t.src == "Reef_Check") & (t.lvl == 1)].copy()          # Population = prevalence
    rc["y"] = rc[["S1", "S2", "S3", "S4"]].mean(axis=1)            # AVERAGE, never sum
    ot = t[t.src.isin(["AGRRA", "FRRP", "McClanahan", "Donner"]) & t.pct.notna()].copy()
    ot["y"] = ot.pct
    y = pd.concat([rc[["sid", "y", "src"]], ot[["sid", "y", "src"]]], ignore_index=True)
    y = y.dropna(subset=["y"]).groupby("sid").agg(y=("y", "mean"), src=("src", "first"))
    y = y[(y.y >= 0) & (y.y <= 100)]
    print("   continuous target built for %s events" % format(len(y), ","))
    print("   by source: %s" % dict(y.src.value_counts()))
    print("   EXCLUDED Kumagai + Safaie (ordinal only -- midpoint substitution is fabrication)")
    return y["y"]


def report(name, yt, yp):
    err = yp - yt
    mae = np.abs(err).mean()
    ss_res = float(((yt - yp) ** 2).sum())
    ss_tot = float(((yt - yt.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    hits = {p: float((np.abs(err) <= p).mean()) for p in (5, 10, 20)}
    print("   %-26s MAE %6.2f pp | R2 %+.4f | hit +/-5 %.3f  +/-10 %.3f  +/-20 %.3f"
          % (name, mae, r2, hits[5], hits[10], hits[20]))
    return dict(name=name, mae=mae, r2=r2, **{"hit%d" % k: v for k, v in hits.items()})


def main():
    print("=" * 84); print("TARGET"); print("=" * 84)
    y = continuous_target()

    print("\n" + "=" * 84); print("FEATURES"); print("=" * 84)
    sst = load_sst()
    ev = pd.read_parquet(EV)
    ev["key"] = ev.lat.round(4).astype(str) + "|" + ev.lon.round(4).astype(str)
    ev = ev[ev.key.isin(sst.key.unique())]
    ev = ev[ev.index.isin(y.index)]
    print("   observations with tile AND continuous target: %s" % format(len(ev), ","))
    X = features(ev, sst)
    X["y"] = X.sid.map(y)
    X = X.dropna(subset=["y"])
    fcols = [c for c in X.columns if c not in ("sid", "eco", "side", "pos", "date", "y")]
    print("   %s rows x %d features" % (format(len(X), ","), len(fcols)))

    tr, te = X[X.side == "donor"], X[X.side == "test"]
    if len(te) < 30:
        ecos = tr.eco.drop_duplicates().sample(frac=1, random_state=0)
        cut = ecos.iloc[:max(1, int(0.3 * len(ecos)))]
        te, tr = tr[tr.eco.isin(cut)], tr[~tr.eco.isin(cut)]
        print("   test side thin -> grouped 70/30 split within donors")
    print("\n   TRAIN %s rows, %d ecoregions | target mean %.1f pp, median %.1f, %% zero %.1f"
          % (format(len(tr), ","), tr.eco.nunique(), tr.y.mean(), tr.y.median(), 100 * (tr.y == 0).mean()))
    print("   TEST  %s rows, %d ecoregions | target mean %.1f pp, median %.1f, %% zero %.1f"
          % (format(len(te), ","), te.eco.nunique(), te.y.mean(), te.y.median(), 100 * (te.y == 0).mean()))

    print("\n" + "=" * 84); print("RESULTS on the held-out regions"); print("=" * 84)
    rf = RandomForestRegressor(n_estimators=500, min_samples_leaf=5, n_jobs=-1, random_state=0)
    rf.fit(tr[fcols].fillna(0).values.astype(np.float32), tr.y.values)
    pred = rf.predict(te[fcols].fillna(0).values.astype(np.float32))

    gmean = tr.y.mean()
    rmean = tr.groupby("eco").y.mean()
    per_region = te.eco.map(rmean).fillna(gmean).values

    rows = [report("random forest", te.y.values, pred),
            report("baseline: global mean", te.y.values, np.full(len(te), gmean)),
            report("baseline: regional mean", te.y.values, per_region)]
    b = rows[1]["mae"]
    print("\n   forest vs global-mean baseline : %+.1f%% MAE" % (100 * (rows[0]["mae"] - b) / b))
    b2 = rows[2]["mae"]
    print("   forest vs regional-mean baseline: %+.1f%% MAE   <- the honest comparison"
          % (100 * (rows[0]["mae"] - b2) / b2))

    print("\n   per-region MAE (test regions with >=20 obs):")
    te2 = te.assign(pred=pred, base=per_region)
    r = []
    for e, g in te2.groupby("eco"):
        if len(g) < 20:
            continue
        r.append(dict(eco=int(e), n=len(g), mean_y=g.y.mean(),
                      mae_rf=np.abs(g.pred - g.y).mean(),
                      mae_base=np.abs(g.base - g.y).mean()))
    t2 = pd.DataFrame(r)
    t2["gain_pct"] = (100 * (t2.mae_base - t2.mae_rf) / t2.mae_base).round(1)
    print(t2.sort_values("gain_pct", ascending=False).to_string(index=False))
    w = int((t2.mae_rf < t2.mae_base).sum())
    print("\n   forest beats the regional-mean baseline in %d of %d regions" % (w, len(t2)))

    imp = pd.Series(rf.feature_importances_, index=fcols).sort_values(ascending=False)
    print("\n   top 10 features: %s" % ", ".join("%s %.3f" % (k, v) for k, v in imp.head(10).items()))
    te2.to_csv("smoke_regress_predictions.csv", index=False)
    print("\n   saved -> smoke_regress_predictions.csv")
    print("\n   SAME LIMITS AS THE CLASSIFIER RUN: no DHW, no local climatology, no light/flow/depth,")
    print("   and only 5.8% of the tiles. MAE in PERCENTAGE POINTS of coral bleached.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
