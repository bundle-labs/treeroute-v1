"""LAGGED VEGETATION AS FUEL. Build the leak-free form of the columns fire_ban.py set aside.

WHY THESE COLUMNS DO NOT EXIST YET. V11_mean_ndvi, V12_mean_evi and gpp_kgC_m2 sit in
fire_ban.CONDITIONAL_LAG1, so the model has never seen a vegetation index at all. They were excluded
because a burn scar depresses the SAME MONTH's NDVI -- the fire causes the signal, so predicting the
fire from it is circular. At lag 1 that circularity is gone: vegetation in month t-1 cannot have been
affected by a fire in month t. That is exactly what CONDITIONAL_LAG1 means, and the lagged form was
simply never built.

RATIOS AND ANOMALIES, NOT LEVELS -- the rule fire_ban.py states in the same comment. A raw NDVI
level mostly says "this is a rainforest cell"; it fingerprints the biome rather than the fuel state,
and the biome is already encoded a dozen other ways. Every column here is either a deviation from
that cell's own seasonal normal or a ratio against its own recent history, so it means "how much
fuel is standing here RIGHT NOW compared with how this place usually looks".

THE COLUMNS.
  ndvi_lag1_anom    last month's NDVI minus this cell's <=TRAIN_END mean FOR LAST MONTH's
                    calendar month -- the value and its normal must describe the same month, or the
                    column measures the seasonal step instead of the anomaly (see the note in
                    build()). Positive = an unusually green season = more fuel than normal.
  ndvi_cure         1 - lag1 / (max NDVI over the previous 12 months). The fire-science CURING
                    index: how far the vegetation has dried back from its own annual peak. Grass
                    that grew and then cured is the classic fuel; grass still green is not.
  ndvi_ratio_1_3    lag1 / lag3 -- the drying TREND over the last quarter.
  ndvi_ratio_1_12   lag1 / the mean of the previous 12 months -- standing biomass against its own
                    recent baseline.
  ndvi_lag1_raw     the raw level, carried ONLY so the ratios-not-levels rule can be tested rather
                    than assumed. Excluded by default; --raw=1 includes it.

Same for EVI, which is less saturation-prone in dense canopy.

LEAK CONTROL. Every column uses month t-1 or earlier, and the seasonal normal is computed from
<=TRAIN_END only, so no test-window vegetation defines what "normal" means for a test row.

  py -3.9 -u fire_build_ndvi_lags.py
  py -3.9 -u fire_build_ndvi_lags.py --force=1      # rebuild over an existing set
  py -3.9 -u fire_build_ndvi_lags.py --raw=1
"""
import os, sys, time, glob
import numpy as np
import pandas as pd

ARG = {a.split("=")[0]: a.split("=")[1] for a in sys.argv[1:] if "=" in a}
YEARS = list(range(2002, 2023))
TRAIN_END = int(ARG.get("--trainend", 2018))
RAW = int(ARG.get("--raw", 0))
FORCE = int(ARG.get("--force", 0))     # rebuild files that already exist
DRV = r"D:\fire\drivers\joined"
OUT = ARG.get("--out", r"D:\fire\drivers\ndvi")
PANEL = "D:/monthly_panel/%s_monthly_%d.parquet"
SRC = [("ndvi", "V11_mean_ndvi"), ("evi", "V12_mean_evi")]


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def build(region):
    """Per cell, walk the months in order and derive the lag features."""
    frames = []
    for y in YEARS:
        fp = PANEL % (region, y)
        if not os.path.exists(fp):
            return None
        cols = ["lat", "lon", "year", "month"] + [c for _, c in SRC]
        d = pd.read_parquet(fp, columns=[c for c in cols])
        frames.append(d)
    P = pd.concat(frames, ignore_index=True)
    P["t"] = P.year * 12 + P.month
    P["cell"] = (np.round(P.lat.values.astype(np.float64), 5) * 1e5).astype(np.int64) \
        * 100000000 + (np.round(P.lon.values.astype(np.float64), 5) * 1e5).astype(np.int64)
    P = P.sort_values(["cell", "t"]).reset_index(drop=True)
    g = P.groupby("cell", sort=False)

    for tag, col in SRC:
        v = P[col]
        l1, l3 = g[col].shift(1), g[col].shift(3)
        # rolling window on the SHIFTED series, so month t never sees its own value
        s = g[col].shift(1)
        mx12 = s.groupby(P.cell, sort=False).rolling(12, min_periods=3).max().reset_index(level=0, drop=True)
        mn12 = s.groupby(P.cell, sort=False).rolling(12, min_periods=3).mean().reset_index(level=0, drop=True)
        # seasonal normal from <=TRAIN_END ONLY -- a test row's "normal" must not come from test years
        tr = P[P.year <= TRAIN_END]
        clim = tr.groupby(["cell", "month"])[col].mean()
        norm = pd.Series(P.set_index(["cell", "month"]).index.map(clim), index=P.index).astype(float)
        # THE NORMAL MUST BE SHIFTED TOO, and the first build of this file did not shift it. `norm`
        # is aligned to the CURRENT row's calendar month, so subtracting it from a month t-1 VALUE
        # measures the seasonal STEP from t-1 to t rather than an anomaly. Measured on
        # angola_zambia_fire_belt: 77.4% of the unshifted column's variance was the pure seasonal
        # cycle, and the variance of its twelve monthly means was 3,676x the shifted version's. It
        # was a calendar wearing an anomaly's name. The shift below is the same one l1 gets, so the
        # value and its normal now describe the same month.
        norm_l1 = norm.groupby(P.cell, sort=False).shift(1)
        P["%s_lag1_anom" % tag] = l1 - norm_l1
        P["%s_cure" % tag] = 1.0 - l1 / mx12.replace(0, np.nan)
        P["%s_ratio_1_3" % tag] = l1 / l3.replace(0, np.nan)
        P["%s_ratio_1_12" % tag] = l1 / mn12.replace(0, np.nan)
        if RAW:
            P["%s_lag1_raw" % tag] = l1
    made = [c for c in P.columns if any(c.startswith(t + "_") for t, _ in SRC)]
    for c in made:
        P[c] = P[c].replace([np.inf, -np.inf], np.nan)
    # FAIL LOUD IF AN "ANOMALY" IS STILL A CALENDAR. A de-seasonalised column's twelve monthly means
    # must all be ~0, so the between-month share of its variance is the direct test. This is the
    # check that would have caught the unshifted-normal defect on the first build instead of after
    # the ablation had already been run on it.
    for c in [c for c in made if c.endswith("_lag1_anom")]:
        v = P[[c, "month"]].dropna()
        if len(v) < 1000:
            continue
        share = float(v.groupby("month")[c].mean().var() / max(v[c].var(), 1e-12))
        if share > 0.10:
            raise SystemExit(
                "%s: %.1f%% of %s is the bare seasonal cycle. An anomaly must be de-seasonalised, "
                "so the lag and its seasonal normal have drifted out of alignment again -- fix that "
                "rather than relaxing this threshold." % (region, 100 * share, c))
    return P[["lat", "lon", "year", "month"] + made], made


def main():
    os.makedirs(OUT, exist_ok=True)
    regs = sorted(os.path.basename(f)[:-8] for f in glob.glob(os.path.join(DRV, "*.parquet")))
    log("=" * 100)
    log("LAGGED VEGETATION FUEL COLUMNS | %d regions | seasonal normal from <=%d only"
        % (len(regs), TRAIN_END))
    log("  raw levels %s (ratios-not-levels rule, fire_ban.py)" % ("INCLUDED" if RAW else "excluded"))
    for i, r in enumerate(regs):
        dst = os.path.join(OUT, "%s.parquet" % r)
        if os.path.exists(dst) and not FORCE:
            log("[%2d/%d] %-30s already done" % (i + 1, len(regs), r))
            continue
        t0 = time.time()
        out = build(r)
        if out is None:
            log("[%2d/%d] %-30s PANEL INCOMPLETE -- skipped" % (i + 1, len(regs), r))
            continue
        P, made = out
        # the join skeleton is copied VERBATIM from the existing driver file: cells_1000 stores
        # float32 lat/lon while the driver files are float64 and key() rounds to 5 dp, so rebuilt
        # coordinates silently produce an all-NaN join.
        skel = pd.read_parquet(os.path.join(DRV, "%s.parquet" % r),
                               columns=["lat", "lon", "year", "month"])
        res = skel.merge(P, on=["lat", "lon", "year", "month"], how="left")
        assert len(res) == len(skel), "join changed the row count (%d -> %d)" % (len(skel), len(res))
        res.to_parquet(dst + ".part", index=False)
        os.replace(dst + ".part", dst)
        fill = 100.0 * res[made].notna().all(axis=1).mean()
        log("[%2d/%d] %-30s %d cols | %.1f%% of rows complete | %.1f min"
            % (i + 1, len(regs), r, len(made), fill, (time.time() - t0) / 60))
    log("done -- wire it in with fire_architecture's USE_NDVI / NDVI_DIR")


if __name__ == "__main__":
    main()
