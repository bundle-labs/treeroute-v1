"""NOAA CRW 4-MONTH BLEACHING OUTLOOK AS A BASELINE FOR THE CORAL MODEL.

This is the one external baseline in this project that is a genuine operational rival rather than
a textbook model we re-implemented. CRW's Outlook is what reef managers actually read. If our model
cannot beat it we should say so.

WHAT THE PRODUCT IS. Weekly, global, 0.5 degrees, from the CFSv2 seasonal forecast. Each issue
carries CRW_BAA_Week_01..Week_20 -- the predicted Bleaching Alert Area at leads of one to twenty
weeks -- plus a four-month composite. BAA is an ordinal heat-stress class, not a bleaching percent:

    0 No Stress   1 Watch   2 Warning   3 Alert Level 1   4 Alert Level 2      (fill = -5, land)

Week_N covers [icwk + 1 + 7(N-1), icwk + 1 + 7N). Verified against the per-variable start_time
attribute on the first file read, and the run ABORTS if that formula ever disagrees.

THREE THINGS THAT MAKE THIS A FAIR FIGHT RATHER THAN A RIGGED ONE.

  1  CRW predicts HEAT STRESS; we predict PERCENT BLEACHED. They are not on the same scale, so a
     raw MAE against BAA would be meaningless. We fit an isotonic map BAA -> percent bleached and
     we fit it ON DONOR ECOREGIONS ONLY. This is the same treatment fire_final.py gives MDC and
     KBDI. It gives CRW a calibration it does not natively ship with, which favours CRW, and it
     obeys project rule 1: nothing is fitted on a target region.

  2  The archive starts in 2011; our surveys start in 1994. Only rows from 2011 onward can be
     scored. Our own model is re-scored ON EXACTLY THOSE ROWS, never on its full test set, so the
     two numbers describe the same reefs on the same days.

  3  At 0.5 degrees a coastal reef can land on a land pixel. We search outward for the nearest
     ocean pixel and RECORD how far we had to go. The count is reported, not hidden.

    py -3.9 -u coral_crw.py --step=fetch                 # ~470 files, ~180 MB, resumable
    py -3.9 -u coral_crw.py --step=extract               # BAA at leads 1..20 for every survey
    py -3.9 -u coral_crw.py --step=score                 # the leaderboard
"""
import os
import sys
import json
import time
import numpy as np
import pandas as pd

ARG = {a.split("=")[0]: a.split("=")[1] for a in sys.argv[1:] if "=" in a}
STEP = ARG.get("--step", "fetch")
PERC = ARG.get("--perc", "060")
Y0 = int(ARG.get("--y0", 2010))
Y1 = int(ARG.get("--y1", 2020))
RAW = ARG.get("--raw", r"D:\coral\crw\nc")
OUT = ARG.get("--out", r"D:\coral\crw")
FEAT = "forecast_features_L0.parquet"
SPLIT = "fullscale_split.json"
BASE = "https://www.star.nesdis.noaa.gov/pub/sod/mecb/crw/data/outlook/v5/nc/v1/outlook"
NLEAD = 20
MAXRING = int(ARG.get("--maxring", 3))       # 3 cells at 0.5 deg = ~150 km, generous but bounded


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


# ---------------------------------------------------------------------------------------------
# STEP 1  FETCH
# ---------------------------------------------------------------------------------------------
def fetch():
    import re
    from urllib.request import urlopen

    os.makedirs(RAW, exist_ok=True)
    log("=" * 108)
    log("FETCH | CRW outlook v5 | %s pct probability product | issue years %d-%d" % (PERC, Y0, Y1))
    pat = r"(cfsv2_outlook-" + PERC + r"perc[^\"<>]+\.nc)"
    got = tot = skip = fail = 0
    for yr in range(Y0, Y1 + 1):
        url = "%s/%d/" % (BASE, yr)
        try:
            html = urlopen(url, timeout=120).read().decode("utf-8", "replace")
        except Exception as e:
            log("  %d  DIRECTORY UNREADABLE (%s) -- this year contributes nothing" % (yr, e))
            continue
        names = sorted(set(re.findall(pat, html)))
        log("  %d  %d files listed" % (yr, len(names)))
        for n in names:
            tot += 1
            dst = os.path.join(RAW, n)
            if os.path.exists(dst) and os.path.getsize(dst) > 1000:
                skip += 1
                continue
            try:
                b = urlopen(url + n, timeout=300).read()
                with open(dst, "wb") as f:
                    f.write(b)
                got += 1
                if got % 25 == 0:
                    log("     %d downloaded, %d already present" % (got, skip))
            except Exception as e:
                fail += 1
                log("     FAILED %s (%s)" % (n, e))
    log("FETCH DONE | %d new | %d already present | %d failed | %d listed" % (got, skip, fail, tot))
    if fail:
        log("  re-run the same command; it skips what is on disk and retries only the failures")


# ---------------------------------------------------------------------------------------------
# STEP 2  EXTRACT
# ---------------------------------------------------------------------------------------------
def _grid_index(lat, lon):
    """CRW grid: lat 89.75 -> -89.75 step -0.5, lon 0.25 -> 359.75 step +0.5."""
    i = np.rint((89.75 - lat) / 0.5).astype(np.int64)
    j = np.rint(((lon % 360.0) - 0.25) / 0.5).astype(np.int64)
    return np.clip(i, 0, 359), np.clip(j, 0, 719)


def _nearest_ocean(arr, i, j, maxring):
    """arr is (360,720) int8 with -5 on land. Return (value, ring); ring -1 if no ocean in range.

    Within a ring we take the MAXIMUM alert, which is how a manager reads a map: if any adjacent
    water is under an alert, the reef is under an alert. Taking the mean would quietly dilute
    CRW's warnings against a coastline and make it look worse than it is.
    """
    if arr[i, j] >= 0:
        return int(arr[i, j]), 0
    for r in range(1, maxring + 1):
        best = -5
        for di in range(-r, r + 1):
            for dj in range(-r, r + 1):
                if max(abs(di), abs(dj)) != r:
                    continue
                a, b = i + di, (j + dj) % 720
                if 0 <= a < 360 and arr[a, b] >= 0:
                    v = int(arr[a, b])
                    if v > best:
                        best = v
        if best >= 0:
            return best, r
    return -5, -1


def extract():
    import re
    import netCDF4
    from datetime import datetime, timedelta

    X = pd.read_parquet(FEAT)
    sp = json.load(open(SPLIT))
    X["side"] = np.where(X.eco.isin(sp["donors"]), "donor", "test")
    X["date"] = pd.to_datetime(X["date"])
    X = X[["sid", "eco", "side", "date", "lat", "lon"]].reset_index(drop=True)
    X["i"], X["j"] = _grid_index(X.lat.values, X.lon.values)
    log("=" * 108)
    log("EXTRACT | %s surveys | donor eco %d / test eco %d"
        % (format(len(X), ","), X[X.side == "donor"].eco.nunique(),
           X[X.side == "test"].eco.nunique()))

    files = sorted(f for f in os.listdir(RAW)
                   if f.endswith(".nc") and ("-" + PERC + "perc") in f)
    if not files:
        log("  NO FILES in %s -- run --step=fetch first" % RAW)
        return
    log("  %d outlook files on disk" % len(files))

    d0 = datetime(2000, 1, 1)
    X["dnum"] = (X.date - pd.Timestamp(d0)).dt.days.values
    sid = X.sid.values
    eco = X.eco.values
    side = X.side.values
    dnum = X.dnum.values
    ii = X.i.values
    jj = X.j.values

    rows = []
    checked = False
    nfile = 0
    t0 = time.time()
    for fn in files:
        m = re.search(r"icwk(\d{8})", fn)
        if not m:
            continue
        ic = datetime.strptime(m.group(1), "%Y%m%d")
        icn = (ic - d0).days
        lo, hi = icn + 1, icn + 1 + 7 * NLEAD
        sel = np.where((dnum >= lo) & (dnum < hi))[0]
        if not sel.size:
            continue
        ds = netCDF4.Dataset(os.path.join(RAW, fn))
        ds.set_auto_mask(False)
        if not checked:
            got = str(getattr(ds.variables["CRW_BAA_Week_01"], "start_time", ""))[:8]
            want = (ic + timedelta(days=1)).strftime("%Y%m%d")
            if got != want:
                raise SystemExit(
                    "WEEK-WINDOW FORMULA IS WRONG. %s Week_01 start_time=%s but icwk+1=%s. Every "
                    "lead in this run would be mislabelled -- fix the window math before trusting "
                    "any number from it." % (fn, got, want))
            log("  window formula verified on %s: Week_01 starts icwk+1 = %s" % (fn, got))
            checked = True
        cache = {}
        for k in sel:
            lead = int((dnum[k] - (icn + 1)) // 7) + 1
            if lead < 1 or lead > NLEAD:
                continue
            key = "CRW_BAA_Week_%02d" % lead
            if key not in cache:
                cache[key] = np.array(ds.variables[key][0])
            val, ring = _nearest_ocean(cache[key], int(ii[k]), int(jj[k]), MAXRING)
            rows.append((sid[k], eco[k], side[k], dnum[k], lead, val, ring, m.group(1)))
        ds.close()
        nfile += 1
        if nfile % 50 == 0:
            log("  %d files | %s pairs | %.1f min"
                % (nfile, format(len(rows), ","), (time.time() - t0) / 60))

    R = pd.DataFrame(rows, columns=["sid", "eco", "side", "dnum", "lead", "baa", "ring", "icwk"])
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "crw_baa_%sperc.parquet" % PERC)
    R.to_parquet(dst, index=False)
    log("EXTRACT DONE | %s (survey,lead) pairs -> %s" % (format(len(R), ","), dst))
    ok = R[R.baa >= 0]
    log("  distinct surveys covered: %s" % format(R.sid.nunique(), ","))
    log("  no ocean pixel within %d cells: %s pairs (%.2f%%)"
        % (MAXRING, format(int((R.baa < 0).sum()), ","), 100.0 * (R.baa < 0).mean()))
    log("  ring used: " + "  ".join("%d:%s" % (k, format(v, ","))
                                    for k, v in ok.ring.value_counts().sort_index().items()))
    log("  BAA class: " + "  ".join("%d:%s" % (k, format(v, ","))
                                    for k, v in ok.baa.value_counts().sort_index().items()))



# ---------------------------------------------------------------------------------------------
# STEP 3  SCORE
# ---------------------------------------------------------------------------------------------
def _mae(y, p):
    return float(np.mean(np.abs(y - p)))


def _r2(y, p):
    d = float(np.sum((y - y.mean()) ** 2))
    return float(1.0 - np.sum((y - p) ** 2) / d) if d > 0 else float("nan")


def score():
    """CRW's operational outlook against our model, on identical rows, lead by lead."""
    from sklearn.isotonic import IsotonicRegression
    from coral_final_benchmark import base_cols, SHAPE, build_pop
    from coral_smoke_regress import continuous_target
    from coral_confound_audit import source_map
    from coral_glorys2_ab import route

    seeds = int(ARG.get("--seeds", 1))
    leads = [int(v) for v in ARG.get("--leads", "1,4,8,12,16,20").split(",")]

    src_f = os.path.join(OUT, "crw_baa_%sperc.parquet" % PERC)
    C = pd.read_parquet(src_f)
    C = C[C.baa >= 0]
    log("=" * 108)
    log("SCORE | CRW %s pct | %s valid (survey,lead) pairs | %s surveys"
        % (PERC, format(len(C), ","), format(C.sid.nunique(), ",")))

    X = pd.read_parquet(FEAT)
    sp = json.load(open(SPLIT))
    X["side"] = np.where(X.eco.isin(sp["donors"]), "donor", "test")
    X["y"] = X.sid.map(continuous_target())
    X["src"] = X.sid.map(source_map())
    X = X.dropna(subset=["y"]).reset_index(drop=True)
    X = build_pop(X)
    B74 = [c for c in base_cols(X) if c not in SHAPE and c != "src"]
    BASE = B74 + SHAPE
    dm = X[X.side == "donor"]
    for c in BASE:
        if X[c].isna().any():
            X[c] = X[c].fillna(dm[c].median())
    ctxc = ["month", "doy_sin", "doy_cos", "abslat"]
    tr = X[X.side == "donor"].reset_index(drop=True)
    te = X[X.side == "test"].reset_index(drop=True)

    # OUR MODEL, run once on the FULL test set exactly as it ships, then subset for scoring.
    # Fitting it only on the CRW-coverable rows would change the model; subsetting the scores
    # does not. This is the shipped model being asked about a subset of the reefs it already
    # predicted, which is the only comparison that means anything.
    log("  running the shipped architecture on the full test set (%d seed%s)..."
        % (seeds, "" if seeds == 1 else "s"))
    t0 = time.time()
    ours = np.mean([route(tr, te, BASE, ctxc, 500, 0.15, 50, 0.5, 0.25, s)
                    for s in range(seeds)], axis=0)
    log("  done in %.1f min" % ((time.time() - t0) / 60))

    te = te.reset_index(drop=True)
    te["ours"] = ours
    tr_y = tr.y.values

    rows = []
    dumps = []
    for L in leads:
        cl = C[C.lead == L]
        dtr = cl[cl.side == "donor"].merge(tr[["sid", "y"]], on="sid", how="inner")
        dte = cl[cl.side == "test"].merge(te[["sid", "y", "ours", "src"]], on="sid", how="inner")
        if len(dtr) < 50 or len(dte) < 30:
            log("  lead %2d: donor %d / test %d -- TOO FEW ROWS, skipped" % (L, len(dtr), len(dte)))
            continue
        # isotonic BAA -> percent bleached, FITTED ON DONORS ONLY (project rule 1)
        iso = IsotonicRegression(out_of_bounds="clip").fit(dtr.baa.values.astype(float),
                                                           dtr.y.values)
        crw = iso.predict(dte.baa.values.astype(float))
        y = dte.y.values
        # DECOMPOSITION ARM. Our own features carry dhw_84 and mmm -- the very quantities CRW's
        # method is built on. So CRW can lose for two quite different reasons and we should not
        # confuse them:
        #     its SST FORECAST was wrong          (a forecasting failure)
        #     its FIXED THRESHOLDS are crude      (a modelling failure)
        # This arm applies NOAA's operational DHW bands to our OBSERVED dhw_84 and isotonic-maps
        # them on donors, exactly as the CRW arm is treated. It is CRW's decision rule with
        # perfect foresight of the heat stress. The gap between it and the CRW arm is forecast
        # error; the gap between it and ours is what LEARNING buys over a fixed lookup table.
        obs = None
        if "dhw_84" in tr.columns:
            bnd = lambda v: np.digitize(v, [1.0, 4.0, 8.0]).astype(float)
            iso_o = IsotonicRegression(out_of_bounds="clip").fit(
                bnd(tr.set_index("sid").loc[dtr.sid.values, "dhw_84"].values), dtr.y.values)
            obs = iso_o.predict(bnd(te.set_index("sid").loc[dte.sid.values, "dhw_84"].values))

        base = {"CRW outlook (isotonic)": crw,
                "predict-zero": np.zeros(len(y)),
                "donor mean": np.full(len(y), tr_y.mean()),
                "donor median": np.full(len(y), np.median(tr_y)),
                "OURS (77-col arch)": dte.ours.values}
        if obs is not None:
            base["NOAA DHW bands (observed)"] = obs
        for nm, p in base.items():
            rows.append(dict(lead=L, arm=nm, n=len(y), mae=_mae(y, p), r2=_r2(y, p),
                             mean_pred=float(p.mean()), mean_truth=float(y.mean())))
        d_ = dte[["sid", "eco", "src", "y", "ours", "baa"]].copy()
        d_["lead"] = L
        for nm, p in base.items():
            d_[nm] = p
        dumps.append(d_)
        log("  lead %2d | n=%s donors=%s | BAA mix %s"
            % (L, format(len(dte), ","), format(len(dtr), ","),
               dict(dte.baa.value_counts().sort_index())))

    if dumps:
        pd.concat(dumps, ignore_index=True).to_parquet(
            os.path.join(OUT, "crw_rows_%sperc.parquet" % PERC), index=False)
    D = pd.DataFrame(rows)
    dst = os.path.join(OUT, "crw_scores_%sperc.csv" % PERC)
    D.to_csv(dst, index=False)

    log("=" * 108)
    log("CRW OUTLOOK vs THE SHIPPED MODEL -- identical rows, identical days")
    log("  %-24s %5s %6s %9s %9s %10s" % ("arm", "lead", "n", "MAE", "R2", "mean pred"))
    for L in sorted(D.lead.unique()):
        d = D[D.lead == L].sort_values("mae")
        for _, r in d.iterrows():
            log("  %-24s %5d %6d %9.4f %9.4f %10.3f"
                % (r.arm, r.lead, r.n, r.mae, r.r2, r.mean_pred))
        log("  " + "-" * 74)
    log("")
    log("  READ THE LEAD COLUMN BEFORE READING THE MARGIN. Our model is a NOWCAST: its DHW and")
    log("  MMM features are observed AT the survey date. CRW at lead N is a real forecast issued")
    log("  N weeks earlier. So every row of this table is generous to us, and increasingly so as")
    log("  the lead grows. Lead 1 is the only near-fair head-to-head; beyond it CRW is answering")
    log("  a harder question than we are, and a win there is not a win on equal terms.")
    log("")
    log("  The NOAA DHW bands arm is the control that separates the two ways CRW can lose:")
    log("    CRW outlook  vs  NOAA DHW bands  =  how much its SST FORECAST cost it")
    log("    NOAA DHW bands  vs  OURS         =  what LEARNING buys over the fixed lookup table")
    log("")
    log("  MAE is minimised by the MEDIAN and this target is mostly zeros, so an arm can win")
    log("  mostly zeros, so an arm can win on MAE by predicting near-nothing. Read mean pred")
    log("  next to MAE: an arm whose mean pred is far below mean truth is timid, not skilful.")
    log("  Written to %s" % dst)

    # PER PROGRAMME. Part 448/451: the pooled coral number is inflated by between-programme
    # contrast, and within Reef_Check our model loses to predict-zero. A pooled-only CRW
    # comparison would inherit exactly that flaw, so it is broken out here rather than trusted.
    L1 = min(leads)
    cl = C[(C.lead == L1) & (C.side == "test")].merge(
        te[["sid", "y", "ours", "src"]], on="sid", how="inner")
    dtr = C[(C.lead == L1) & (C.side == "donor")].merge(tr[["sid", "y"]], on="sid", how="inner")
    if len(cl) and len(dtr) >= 50:
        iso = IsotonicRegression(out_of_bounds="clip").fit(dtr.baa.values.astype(float),
                                                           dtr.y.values)
        cl["crw"] = iso.predict(cl.baa.values.astype(float))
        log("")
        log("PER PROGRAMME at lead %d -- the pooled row above is not quotable on its own" % L1)
        log("  %-18s %5s %7s %8s %8s %8s %8s %8s" % ("programme", "n", "truth", "MAE ours",
                                                        "MAE CRW", "MAE zero", "R2 ours", "R2 CRW"))
        for g, d in cl.groupby("src"):
            if len(d) < 15:
                continue
            yv = d.y.values
            log("  %-18s %5d %7.2f %8.4f %8.4f %8.4f %8.4f %8.4f"
                % (str(g)[:18], len(d), yv.mean(), _mae(yv, d.ours.values),
                   _mae(yv, d.crw.values), _mae(yv, np.zeros(len(d))),
                   _r2(yv, d.ours.values), _r2(yv, d.crw.values)))
        log("")
        log("  SKILL vs predict-zero, 1 - MAE/MAE_zero. Negative means the arm is WORSE than")
        log("  assuming no bleaching at all -- which is the only honest way to read a target")
        log("  this close to zero on most rows.")
        log("  %-18s %5s %10s %10s" % ("programme", "n", "skill ours", "skill CRW"))
        for g, d in cl.groupby("src"):
            if len(d) < 15:
                continue
            yv = d.y.values
            mz = _mae(yv, np.zeros(len(d)))
            log("  %-18s %5d %10.4f %10.4f"
                % (str(g)[:18], len(d), 1 - _mae(yv, d.ours.values) / mz if mz else float("nan"),
                   1 - _mae(yv, d.crw.values) / mz if mz else float("nan")))


# ---------------------------------------------------------------------------------------------
# STEP 4  LEAD TEST -- our FORECAST against CRW's, at CRW's own maximum horizon and beyond
# ---------------------------------------------------------------------------------------------
def lead_test():
    """The question Part 456 could not answer: CRW's outlook stops at 20 weeks. Ours does not.

    Part 456 compared our NOWCAST against CRW's forecast, which is generous to us and says so in
    its own output. This step removes that handicap by cutting our features at T-lead with the
    same two-clock machinery that produced the published forecast curve (coral_forecast77.prep,
    reused rather than reimplemented so the numbers stay commensurable with Parts 447/455).

    Three arms that answer three different questions:

      lead 140  MATCHED. CRW's maximum horizon is 20 weeks = 140 days. Both models forecast the
                same 140 days ahead. This is the only genuinely fair head-to-head in the project.
      lead 365  BEYOND. We forecast 2.6x further ahead than CRW is able to. If we still win, the
                claim is not "more accurate" but "accurate at a horizon the operational product
                does not reach".
      lead 0    the nowcast, carried so Part 456's number is visible in the same table.

    The DHW-bands control is carried at BOTH clocks, because the distinction matters here:
      "@T (ORACLE)" uses dhw_84 at T -- what CRW would score with perfect heat foresight
      "@T-L"        uses dhw_84 from the lead-L file -- what a manager could actually compute
    Labelling the oracle as an oracle is the whole point; the honest baseline is the second.
    """
    from sklearn.isotonic import IsotonicRegression
    import coral_forecast as F
    from coral_forecast77 import prep
    from coral_glorys2_ab import route

    seeds = int(ARG.get("--seeds", 1))
    leads = [int(v) for v in ARG.get("--leads", "0,140,365").split(",")]
    crwlead = int(ARG.get("--crwlead", 20))          # in WEEKS; 20 wk = 140 d = CRW's maximum
    ctxc = ["month", "doy_sin", "doy_cos", "abslat"]

    log("=" * 108)
    log("LEAD TEST | our forecast vs CRW at %d weeks (%d days) | leads %s | %d seed(s)"
        % (crwlead, crwlead * 7, leads, seeds))

    for L in leads:
        if not os.path.exists(F.feat_path(L)):
            log("  building %s -- reads the 932 MB SST array, ~13 min" % F.feat_path(L))
            F.build(L)

    preds = {}
    for L in leads:
        t0 = time.time()
        X, B74, B77 = prep(L)
        tr = X[X.side == "donor"].reset_index(drop=True)
        te = X[X.side == "test"].reset_index(drop=True)
        p = np.mean([route(tr, te, B77, ctxc, 500, 0.15, 50, 0.5, 0.25, s)
                     for s in range(seeds)], axis=0)
        dh_te = te["dhw_84"].values if "dhw_84" in te.columns else np.full(len(te), np.nan)
        dh_tr = tr["dhw_84"].values if "dhw_84" in tr.columns else np.full(len(tr), np.nan)
        preds[L] = pd.DataFrame({"sid": te.sid.values, "y": te.y.values, "src": te.src.values,
                                 "eco": te.eco.values, "p": p,
                                 "dhw": dh_te}).set_index("sid")
        preds[("donor", L)] = pd.DataFrame({"sid": tr.sid.values, "y": tr.y.values,
                                            "dhw": dh_tr}).set_index("sid")
        log("  lead %3d | %s test rows | %.1f min"
            % (L, format(len(te), ","), (time.time() - t0) / 60))

    C = pd.read_parquet(os.path.join(OUT, "crw_baa_%sperc.parquet" % PERC))
    C = C[(C.baa >= 0) & (C.lead == crwlead)]
    cte = C[C.side == "test"].drop_duplicates("sid").set_index("sid")
    cdo = C[C.side == "donor"].drop_duplicates("sid").set_index("sid")

    # COMMON ROW SET. Every arm is scored on the identical sids -- a longer lead drops events whose
    # MMM window no longer fits, and CRW drops everything before 2011, so an unrestricted table
    # would be partly measuring a changing test set rather than a changing model.
    common = set(cte.index)
    for L in leads:
        common &= set(preds[L].index)
    common = sorted(common)
    if len(common) < 50:
        log("  ONLY %d COMMON ROWS -- too few to score. Nothing is reported." % len(common))
        return
    log("  common row set across every arm and CRW: %s surveys" % format(len(common), ","))

    y = preds[leads[0]].loc[common, "y"].values
    src = preds[leads[0]].loc[common, "src"].values
    baa = cte.loc[common, "baa"].values.astype(float)

    dsid = sorted(set(cdo.index) & set(preds[("donor", leads[0])].index))
    iso = IsotonicRegression(out_of_bounds="clip").fit(
        cdo.loc[dsid, "baa"].values.astype(float),
        preds[("donor", leads[0])].loc[dsid, "y"].values)
    arms = {}
    arms["CRW outlook @%dwk" % crwlead] = iso.predict(baa)
    log("  isotonic link fitted on %s donor surveys" % format(len(dsid), ","))

    def bnd(v):
        return np.digitize(v, [1.0, 4.0, 8.0]).astype(float)

    for L in leads:
        nm = "OURS nowcast @0d" if L == 0 else "OURS forecast @%dd" % L
        arms[nm] = preds[L].loc[common, "p"].values
        dv = preds[("donor", L)]
        ds2 = sorted(set(dv.index) & set(dsid))
        dvals = dv.loc[ds2, "dhw"].values
        if len(ds2) > 50 and np.isfinite(dvals).sum() > 50:
            ok = np.isfinite(dvals)
            io_ = IsotonicRegression(out_of_bounds="clip").fit(
                bnd(dvals[ok]), dv.loc[ds2, "y"].values[ok])
            bn = "NOAA DHW bands @T (ORACLE)" if L == 0 else "NOAA DHW bands @T-%dd" % L
            tv = preds[L].loc[common, "dhw"].values
            arms[bn] = io_.predict(bnd(np.where(np.isfinite(tv), tv, 0.0)))
    arms["predict-zero"] = np.zeros(len(common))

    mz = _mae(y, np.zeros(len(y)))
    rows = []
    for nm, p in arms.items():
        rows.append(dict(arm=nm, n=len(y), mae=_mae(y, p), r2=_r2(y, p),
                         skill=1 - _mae(y, p) / mz if mz else float("nan"),
                         mean_pred=float(p.mean())))
    D = pd.DataFrame(rows).sort_values("mae").reset_index(drop=True)
    D.to_csv(os.path.join(OUT, "crw_leadtest_%sperc.csv" % PERC), index=False)
    # ROW DUMP. The per-programme table below is printed only; a lost shell takes it with it.
    # Persisting the rows makes every follow-up question arithmetic rather than another 10-minute
    # re-run of the router.
    RD = pd.DataFrame({"sid": common, "y": y, "src": src, "baa": baa})
    for nm, pv in arms.items():
        RD[nm] = pv
    RD.to_parquet(os.path.join(OUT, "crw_leadrows_%sperc.parquet" % PERC), index=False)

    log("=" * 108)
    log("FORECAST HEAD-TO-HEAD | %s surveys | truth mean %.3f" % (format(len(y), ","), y.mean()))
    log("  %-32s %6s %9s %9s %9s %10s" % ("arm", "n", "MAE", "R2", "skill", "mean pred"))
    for _, r in D.iterrows():
        log("  %-32s %6d %9.4f %9.4f %9.4f %10.3f"
            % (r.arm, r.n, r.mae, r.r2, r.skill, r.mean_pred))
    log("")
    log("  MATCHED COMPARISON is OURS@%dd against CRW@%dwk -- same horizon, same rows, same days."
        % (crwlead * 7, crwlead))
    log("  OURS@365d is a horizon CRW does not reach at all; its outlook stops at 20 weeks.")
    log("  skill = 1 - MAE/MAE_zero. NEGATIVE means worse than assuming no bleaching at all.")

    log("")
    log("PER PROGRAMME, MAE -- the pooled row is not quotable on its own (Parts 448/451/456)")
    log("  %-14s %6s %8s  " % ("programme", "n", "truth")
        + "  ".join("%22s" % a[:22] for a in D.arm))
    for g in pd.unique(src):
        m = src == g
        if m.sum() < 15:
            continue
        log("  %-14s %6d %8.2f  " % (str(g)[:14], int(m.sum()), y[m].mean())
            + "  ".join("%22.4f" % _mae(y[m], arms[a][m]) for a in D.arm))
    log("")
    log("  Written to %s" % os.path.join(OUT, "crw_leadtest_%sperc.csv" % PERC))

if __name__ == "__main__":
    if STEP == "fetch":
        fetch()
    elif STEP == "extract":
        extract()
    elif STEP == "score":
        score()
    elif STEP == "lead":
        lead_test()
    else:
        log("unknown --step=%s  (fetch | extract | score)" % STEP)
