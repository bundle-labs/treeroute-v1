"""The whole corpus, end to end: fetch 112 ecoregions, build the 74, split 20/92, route 10,000 trees.

    py -3.9 -u coral_fullscale.py --plan                 # what each stage will do; runs nothing
    py -3.9 -u coral_fullscale.py                        # everything, resumable, ~24 h
    py -3.9 -u coral_fullscale.py --from 3               # skip the fetch, start at features
    py -3.9 -u coral_fullscale.py --only 5               # just the train/test stage

WHAT THIS IS FOR. Every coral number so far comes from 10 pilot ecoregions: 7,820 events, 5 donor
regions, 2,500 trees. The DECIDED experiment is 20 donors against everything else, over all 112
ecoregions and 23,258 events -- roughly three times the data and four times the bank. This script
is that experiment, start to finish, with every stage resumable so it can be left running.

FIVE STAGES. Each writes one artefact and is SKIPPED if that artefact already exists, so a kill at
any point costs only the stage in flight.

  1 FETCH     CoralTemp SST, 1985 -> each site's last dive, for all 112 regions.
              401 clusters, 5,137 requests, ~20 h at 4 threads. THE ONLY STAGE THAT NEEDS NETWORK.
  2 COMPACT   the 1,061+ raw tiles -> one int64-keyed flat array.
  3 FEATURES  the 74 columns: SST windows + leak-free expanding MMM + DHW, then cyclones/ENSO/mask,
              then the Hobday marine-heatwave block.
  4 SPLIT     20 donor ecoregions / the rest held out.
  5 ROUTE     500 trees per donor x 20 donors = 10,000, then score the held-out regions.

WHY THE FETCH IS THE *ONLY* DOWNLOAD. The shipped 74 columns trace back to four sources and only
one of them is per-region: 47 columns are SST-derived (the windows, the MMM, DHW, and Hobday),
16 are IBTrACS cyclones (one global track file, already on disk), 6 are ENSO/IOD (two global text
series, already on disk), 2 are the CRW land mask and 3 are the date. **Nothing else needs
fetching.** GLORYS, OC-CCI, WAVERYS, HAMTIDE, GSHHG, REEF/MPA, light, OHC, sea state and sea
surface height are all absent from the 74 -- every one of them was tested and failed (Parts 438,
441), so re-fetching them corpus-wide would cost days to feed columns the model does not use.

WHY STAGE 2 NEVER BUILDS THE STRING-KEYED PARQUET. The pilot pipeline made
`sst_full_merged.parquet` with a STRING key column and then did `sst.groupby("key")` on 57M rows.
That pattern froze this machine three times and is recorded as a standing rule. At full scale the
table is ~132M rows, where a string key would be roughly 13 GB of object array on a box with ~9 GB
free -- not slow, impossible. Stage 2 therefore goes straight to the int64 form, accumulating per
site so there is never a global sort of 132M rows, and stage 3 works in flat numpy slices with
per-site boundaries. Same numbers, no object arrays anywhere.

WHY STAGE 3 REIMPLEMENTS ONE FUNCTION AND IMPORTS THE OTHER TWO. `coral_dhw_model.build()` is the
one that does the fatal groupby, so its logic is reproduced here against the compact arrays --
`mmm_from` is imported verbatim rather than retyped, so the climatology cannot drift between the
pilot and full-scale runs. The cyclone/ENSO/mask features are imported as FUNCTIONS
(`psl_index`, `cyclone_feats`, `mask_feats`) instead of by calling that script's `main()`, which
would overwrite the pilot's `dhw_features_plus.parquet`. The Hobday builder already works on the
compact int64 form, so it is called with its module constants pointed at the full-scale files.

THE SPLIT IS DETERMINISTIC AND PRINTED. Donors are the 20 ecoregions with the most events, which
guarantees every donor has enough rows to fit a 500-tree specialist bank. That is a CHOICE, not a
law -- `--donors` overrides it with an explicit list, and the chosen 20 are printed with their event
counts so the decision is visible and reproducible rather than buried.
"""
import argparse
import glob
import json
import os
import re
import sys
import time
import warnings

sys.path.insert(0, r"C:\Users\<user>\Desktop\data set for reserch paper")
from coral_safe import cap_threads, guard, mem_str, site_key

cap_threads(4)
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

RAW = r"D:\coral\drivers\sst_full"
COMPACT = r"D:\coral\drivers\sst_compact_all.npz"
EV = r"D:\coral\target\events_dated.parquet"
F_DHW = "fullscale_dhw.parquet"
F_PLUS = "fullscale_plus.parquet"
F_FEAT = "fullscale_features.parquet"
F_SPLIT = "fullscale_split.json"
CACHE = "fullscale_cache.json"
N_DONORS = 20
NPD = 500                     # 500 x 20 donors = 10,000 trees
CFG = dict(mf=0.15, k=50, alpha=0.5, a_ctx=0.25)
WIN = (30, 56, 84, 90, 180, 365)
MIN_YEARS = 10
EPOCH0 = np.datetime64("1970-01-01")


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def hdr(n, name, art):
    log("=" * 104)
    log("STAGE %d -- %s" % (n, name))
    if art:
        log("  artefact: %s%s" % (art, "   [EXISTS -> SKIP]" if os.path.exists(art) else ""))


def bar(k, tot, t0, extra=""):
    fill = int(38 * k / max(tot, 1))
    el = time.time() - t0
    eta = (tot - k) * (el / max(k, 1))
    log("  [%s%s] %6d/%d %5.1f%% | %s | ETA %dh%02dm | %s"
        % ("#" * fill, "." * (38 - fill), k, tot, 100.0 * k / max(tot, 1), extra,
           int(eta // 3600), int((eta % 3600) // 60), mem_str()))


# ---------------------------------------------------------------------------------------------
# STAGE 1 -- fetch
# ---------------------------------------------------------------------------------------------
def stage1(plan, threads):
    hdr(1, "FETCH CoralTemp SST for all 112 ecoregions", None)
    import coral_fetch_sst_full as S
    jobs = S.build_plan("all")
    n = len(jobs) if not isinstance(jobs, tuple) else len(jobs[0])
    log("  delegating to coral_fetch_sst_full --regions all (its own resume logic applies)")
    if plan:
        sys.argv = ["coral_fetch_sst_full.py", "--regions", "all", "--plan"]
        return S.main()
    sys.argv = ["coral_fetch_sst_full.py", "--regions", "all",
                "--threads", str(threads)]
    return S.main()


# ---------------------------------------------------------------------------------------------
# STAGE 2 -- compact
# ---------------------------------------------------------------------------------------------
def stage2(plan):
    fs = sorted(glob.glob(os.path.join(RAW, "*.parquet")))
    # STALENESS GUARD. The artefact-exists skip is wrong here on its own: stage 1 keeps ADDING raw
    # tiles, so a compact built from today's 1,061 files would be silently reused after the fetch
    # has grown it to ~2,400 -- and stages 3-5 would then report a 10-region answer wearing a
    # 112-region label. The manifest is (file count, total bytes); if it moved, rebuild.
    man = np.array([len(fs), sum(os.path.getsize(f) for f in fs)], dtype="int64")
    hdr(2, "COMPACT the raw tiles into one int64-keyed array", COMPACT)
    if os.path.exists(COMPACT):
        try:
            old = np.load(COMPACT)["manifest"]
            if np.array_equal(old, man):
                log("  manifest matches (%d files, %.0f MB) -> SKIP" % (man[0], man[1] / 1e6))
                return 0
            log("  STALE: built from %d files / %.0f MB, now %d files / %.0f MB -> REBUILD"
                % (old[0], old[1] / 1e6, man[0], man[1] / 1e6))
        except Exception:
            log("  no manifest in the existing artefact -> REBUILD")
    log("  %d raw tile files" % len(fs))
    if plan:
        log("  --plan: would build %s" % COMPACT)
        return 0
    # Accumulate PER SITE. This is the whole reason there is never a global sort of ~132M rows:
    # each site's days are sorted inside its own short array, and the sites are then written out
    # in ascending key order, which is exactly the layout stage 3 searchsorts against.
    acc = {}
    t0 = time.time()
    for i, f in enumerate(fs):
        d = pd.read_parquet(f, columns=["time", "sst", "site_lat", "site_lon"])
        if not len(d):
            continue
        k = site_key(d.site_lat.values, d.site_lon.values)
        day = (d.time.values.astype("datetime64[D]") - EPOCH0).astype("int64").astype("int32")
        v = d.sst.values.astype("float32")
        order = np.argsort(k, kind="mergesort")
        k, day, v = k[order], day[order], v[order]
        edges = np.r_[0, np.flatnonzero(np.diff(k)) + 1, len(k)]
        for a, b in zip(edges[:-1], edges[1:]):
            acc.setdefault(int(k[a]), []).append((day[a:b], v[a:b]))
        del d, k, day, v, order
        if (i + 1) % 100 == 0:
            guard(2.5, "compact")
            bar(i + 1, len(fs), t0, "%d sites so far" % len(acc))
    log("  %d distinct sites accumulated | %s" % (len(acc), mem_str()))
    uk = np.array(sorted(acc), dtype="int64")
    days, ssts, start, end = [], [], [], []
    p = 0
    for i, key in enumerate(uk):
        parts = acc.pop(int(key))
        dd = np.concatenate([x[0] for x in parts])
        vv = np.concatenate([x[1] for x in parts])
        o = np.argsort(dd, kind="mergesort")
        dd, vv = dd[o], vv[o]
        u, first = np.unique(dd, return_index=True)      # a site can appear in overlapping tiles
        dd, vv = u, vv[first]
        days.append(dd)
        ssts.append(vv)
        start.append(p)
        p += len(dd)
        end.append(p)
        if (i + 1) % 2000 == 0:
            guard(2.5, "compact assemble")
            bar(i + 1, len(uk), t0, "%s rows" % format(p, ","))
    day = np.concatenate(days).astype("int32")
    sst = np.concatenate(ssts).astype("float32")
    del days, ssts
    np.savez(COMPACT, uk=uk, start=np.array(start, "int64"), end=np.array(end, "int64"),
             day=day, sst=sst, manifest=man)
    log("  wrote %s | %s rows | %d sites | %.0f MB"
        % (COMPACT, format(len(day), ","), len(uk), os.path.getsize(COMPACT) / 1e6))
    return 0


# ---------------------------------------------------------------------------------------------
# STAGE 3 -- features
# ---------------------------------------------------------------------------------------------
def stage3(plan):
    hdr(3, "FEATURES: SST windows + MMM + DHW, cyclones/ENSO/mask, Hobday", F_FEAT)
    # Same staleness logic as stage 2, one level down: if the compact is NEWER than a feature file,
    # that feature file describes a smaller corpus and must not be reused.
    for f in (F_DHW, F_PLUS, F_FEAT):
        if os.path.exists(f) and os.path.exists(COMPACT) and                 os.path.getmtime(f) < os.path.getmtime(COMPACT):
            log("  %s predates the compact array -> stale, removing" % f)
            os.remove(f)
    if os.path.exists(F_FEAT):
        return 0
    if plan:
        log("  --plan: would write %s, %s, %s" % (F_DHW, F_PLUS, F_FEAT))
        return 0

    # ---- 3a: SST windows, expanding MMM, DHW -------------------------------------------------
    if not os.path.exists(F_DHW):
        from coral_dhw_model import mmm_from       # imported verbatim: the climatology must NOT
        z = np.load(COMPACT)                       # differ between the pilot and full-scale runs
        uk, st, en, DAY, SST = z["uk"], z["start"], z["end"], z["day"], z["sst"]
        log("  sst %s rows | %d sites | %s" % (format(len(SST), ","), len(uk), mem_str()))
        ev = pd.read_parquet(EV).reset_index()
        ev = ev.rename(columns={"index": "sid"})
        ek = site_key(ev.lat.values, ev.lon.values)
        idx = np.searchsorted(uk, ek)
        idx[idx >= len(uk)] = 0
        hit = uk[idx] == ek
        log("  events %s | with an SST series %d (%.1f%%)"
            % (format(len(ev), ","), hit.sum(), 100 * hit.mean()))
        ed = ev.date.values.astype("datetime64[D]").astype("int64") - \
            (EPOCH0.astype("datetime64[D]").astype("int64"))
        yrs = pd.DatetimeIndex(pd.to_datetime(DAY.astype("int64"), unit="D", origin="unix"))
        YR = yrs.year.values.astype("int32")
        MO = yrs.month.values.astype("int8")
        del yrs
        guard(2.5, "3a setup")
        rows = []
        t0 = time.time()
        for i in range(len(ev)):
            if not hit[i]:
                continue
            a, b = int(st[idx[i]]), int(en[idx[i]])
            d = DAY[a:b]
            j = int(np.searchsorted(d, ed[i], side="left"))      # STRICTLY before the dive
            if j < 365 * MIN_YEARS // 2:
                continue
            t = SST[a:a + j]
            h = pd.DataFrame({"yr": YR[a:a + j], "mo": MO[a:a + j], "sst": t})
            mmm, nyr = mmm_from(h)
            if not np.isfinite(mmm):
                continue
            e = ev.iloc[i]
            hs_all = t - mmm
            f = dict(sid=int(e.sid), eco=e.eco, side="", pos=int(e.pos), date=e.date,
                     lat=e.lat, lon=e.lon, abslat=abs(e.lat), mmm=mmm, mmm_n_years=nyr,
                     month=e.date.month,
                     doy_sin=np.sin(2 * np.pi * e.date.dayofyear / 365.25),
                     doy_cos=np.cos(2 * np.pi * e.date.dayofyear / 365.25))
            for w in WIN:
                v, hs = t[-w:], hs_all[-w:]
                if len(v) < max(10, w // 4):
                    continue
                f["dhw_%d" % w] = np.where(hs >= 1.0, np.clip(hs, 0, None), 0.0).sum() / 7.0
                f["hs_max_%d" % w] = float(np.max(hs))
                f["n_above_mmm_%d" % w] = int((hs > 0).sum())
                f["n_above_mmm1_%d" % w] = int((hs >= 1).sum())
                f["mean_%d" % w] = v.mean()
                f["std_%d" % w] = v.std()
                f["cool_%d" % w] = float(np.clip(-hs, 0, None).sum() / 7.0)
            yr365 = hs_all[-365:] if len(hs_all) >= 365 else hs_all
            f["days_since_max_hs"] = int(len(yr365) - 1 - int(np.argmax(yr365)))
            f["slope_90"] = (np.polyfit(np.arange(min(90, len(t))), t[-90:], 1)[0]
                             if len(t) >= 90 else 0.0)
            gated = np.where(hs_all >= 1.0, np.clip(hs_all, 0, None), 0.0)
            roll = pd.Series(gated).rolling(84, min_periods=84).sum().values / 7.0
            roll = roll[np.isfinite(roll)]
            f["lifetime_dhw"] = float(gated.sum() / 7.0)
            f["n_dhw_ge4_before"] = int((roll >= 4).sum())
            f["n_dhw_ge8_before"] = int((roll >= 8).sum())
            f["max_dhw_before"] = float(roll.max()) if len(roll) else 0.0
            last = np.where(roll >= 4)[0] if len(roll) else []
            f["days_since_dhw4"] = int(len(roll) - 1 - last[-1]) if len(last) else 99999
            rows.append(f)
            if (i + 1) % 2000 == 0:
                guard(2.5, "3a")
                bar(i + 1, len(ev), t0, "%d built" % len(rows))
        X = pd.DataFrame(rows)
        X.to_parquet(F_DHW, index=False)
        log("  wrote %s | %s rows x %d cols" % (F_DHW, format(len(X), ","), X.shape[1]))
        del DAY, SST, YR, MO, rows
        guard(2.5, "after 3a")

    # ---- 3b: cyclones, ENSO/IOD, CRW mask ----------------------------------------------------
    if not os.path.exists(F_PLUS):
        import coral_extra_drivers as E
        X = pd.read_parquet(F_DHW)
        log("  3b: cyclones + ENSO/IOD + mask on %s rows" % format(len(X), ","))
        n34, dmi = E.psl_index(E.NINO), E.psl_index(E.DMI)
        for nm, src in (("nino34", n34), ("dmi", dmi)):
            s = src.set_index(["yr", "mo"]).v
            for lag in (0, 3, 6):
                d = X.date - pd.DateOffset(months=lag)
                X["%s_lag%d" % (nm, lag)] = [s.get((y, m), np.nan)
                                             for y, m in zip(d.dt.year, d.dt.month)]
        X = pd.concat([X, E.cyclone_feats(X)], axis=1)
        guard(2.5, "3b cyclones")
        X = pd.concat([X, E.mask_feats(X)], axis=1)
        X.to_parquet(F_PLUS, index=False)
        log("  wrote %s | %d cols" % (F_PLUS, X.shape[1]))

    # ---- 3c: Hobday marine heatwaves ---------------------------------------------------------
    import coral_mhw_features as M
    M.SST, M.FEAT, M.OUT = COMPACT, F_PLUS, F_FEAT
    log("  3c: Hobday block (module constants repointed at the full-scale files)")
    M.main()
    return 0


# ---------------------------------------------------------------------------------------------
# STAGE 4 -- split
# ---------------------------------------------------------------------------------------------
def stage4(plan, donors_arg):
    hdr(4, "SPLIT %d donor ecoregions / the rest held out" % N_DONORS, F_SPLIT)
    if not os.path.exists(F_FEAT):
        if not plan:
            log("  %s missing -- run stage 3 first" % F_FEAT)
            return 2
        # PREVIEW ONLY. The real split counts rows that survived the MMM's 10-year requirement;
        # this previews against the raw event table so the donor CHOICE is visible before the
        # 20-hour fetch, and it is labelled so the two are never confused.
        X = pd.read_parquet(EV)
        log("  PREVIEW against the raw event table -- stage 3 has not run, so these counts are")
        log("  events, not feature rows; sites failing the 10-year MMM will drop out.")
    else:
        X = pd.read_parquet(F_FEAT)
    cnt = X.eco.value_counts()
    if donors_arg:
        donors = [float(x) for x in donors_arg.split(",")]
    else:
        if len(cnt) <= N_DONORS:
            # Taking the top 20 of 10 leaves NOTHING held out, and stage 5 would then "score" an
            # empty test set. Refuse rather than emit a split that cannot be evaluated.
            log("  ONLY %d ecoregions present but %d donors requested -- stage 1 has not fetched"
                % (len(cnt), N_DONORS))
            log("  the full corpus yet. Pass --donors explicitly to split what IS here.")
            return 2
        donors = [float(e) for e in cnt.index[:N_DONORS]]
    test = [float(e) for e in cnt.index if float(e) not in donors]
    log("  DONORS (%d) -- the %s ecoregions, chosen by event count:"
        % (len(donors), "listed" if donors_arg else "%d largest" % N_DONORS))
    for e in donors:
        log("     eco %-7s %6d events" % (e, int(cnt.get(e, 0))))
    log("  HELD OUT: %d ecoregions, %s events"
        % (len(test), format(int(sum(cnt.get(e, 0) for e in test)), ",")))
    log("  donor rows %s | test rows %s"
        % (format(int(X.eco.isin(donors).sum()), ","),
           format(int((~X.eco.isin(donors)).sum()), ",")))
    if plan:
        return 0
    with open(F_SPLIT + ".part", "w") as fh:
        json.dump({"donors": donors, "test": test}, fh)
    os.replace(F_SPLIT + ".part", F_SPLIT)
    return 0


# ---------------------------------------------------------------------------------------------
# STAGE 5 -- route
# ---------------------------------------------------------------------------------------------
def stage5(plan, seeds):
    hdr(5, "ROUTE %d trees (%d per donor x %d donors) and score the held-out regions"
        % (NPD * N_DONORS, NPD, N_DONORS), None)
    if not (os.path.exists(F_FEAT) and os.path.exists(F_SPLIT)):
        log("  needs %s and %s from stages 3-4; nothing to preview until then."
            % (F_FEAT, F_SPLIT))
        return 0 if plan else 2
    from coral_smoke_regress import continuous_target
    from coral_glorys2_ab import route, sc, event_boot
    X = pd.read_parquet(F_FEAT)
    with open(F_SPLIT) as fh:
        sp = json.load(fh)
    X["side"] = np.where(X.eco.isin(sp["donors"]), "donor", "test")
    X["y"] = X.sid.map(continuous_target())
    X = X.dropna(subset=["y"]).reset_index(drop=True)
    allf = [c for c in X.columns if c not in ("sid", "eco", "side", "pos", "date", "y",
                                              "lat", "lon", "_side")]
    ABS = [c for c in allf if re.match(r"^(mean|std)_\d+$", c) or c in ("abslat", "mmm", "mmm_n_years")]
    HOB = [c for c in allf if c.startswith("mhw_")]
    CORE = [c for c in allf if c not in ABS + HOB]
    BASE = CORE + HOB
    dm = X[X.side == "donor"]
    for c in BASE:
        if X[c].isna().any():
            X[c] = X[c].fillna(dm[c].median())
    ctxc = ["month", "doy_sin", "doy_cos", "abslat"]
    tr = X[X.side == "donor"].reset_index(drop=True)
    te = X[X.side == "test"].reset_index(drop=True)
    log("  BASE %d columns | donor %s rows / %d eco | test %s rows / %d eco"
        % (len(BASE), format(len(tr), ","), tr.eco.nunique(),
           format(len(te), ","), te.eco.nunique()))
    log("  bank = %d trees; the A matrix alone is %.1f GB"
        % (NPD * tr.eco.nunique(), (len(tr) + len(te)) * NPD * tr.eco.nunique() * 4 / 1e9))
    if plan:
        return 0
    cache = {}
    if os.path.exists(CACHE):
        try:
            cache = json.load(open(CACHE))
        except Exception:
            pass
    y = te.y.values
    B, nclu = event_boot(te)
    ps = []
    t0 = time.time()
    for s in range(seeds):
        kk = "route|s%d|npd%d|n%d|te%d" % (s, NPD, len(BASE), len(te))
        if kk in cache:
            ps.append(np.asarray(cache[kk], dtype=float))
            log("  seed %d from cache" % s)
            continue
        p = route(tr, te, BASE, ctxc, NPD, CFG["mf"], CFG["k"], CFG["alpha"], CFG["a_ctx"], s)
        cache[kk] = [float(v) for v in p]
        tmp = CACHE + ".part"
        json.dump(cache, open(tmp, "w"))
        os.replace(tmp, CACHE)
        ps.append(p)
        guard(2.5, "route s%d" % s)
        log("  seed %d done in %.1f min | %s" % (s, (time.time() - t0) / 60, mem_str()))
    P = np.mean(ps, axis=0)
    m = sc(y, P)
    log("=" * 104)
    log("FULL-SCALE RESULT -- %d donor ecoregions, %d held out, %d trees"
        % (tr.eco.nunique(), te.eco.nunique(), NPD * tr.eco.nunique()))
    log("  MAE %.3f | R2 %+.4f | hit5 %.3f | AUC %.4f | AUC50 %.4f | mean pred on severe %.2f"
        % (m["MAE"], m["R2"], m["hit5"], m["AUC"], m["AUC50"], m["psev"]))
    zero = np.abs(y - 0).mean()
    mean = np.abs(y - tr.y.mean()).mean()
    log("  baselines on the SAME rows: predict-zero MAE %.3f | predict-donor-mean MAE %.3f"
        % (zero, mean))
    log("  skill vs predict-zero %+.1f%% | vs donor-mean %+.1f%%"
        % (100 * (zero - m["MAE"]) / zero, 100 * (mean - m["MAE"]) / mean))
    d = np.array([np.abs(y[i] - P[i]).mean() - np.abs(y[i] - 0).mean() for i in B])
    lo, hi = np.percentile(d, [2.5, 97.5])
    log("  event-clustered (%d clusters) vs predict-zero: %+.3f CI [%+.3f, %+.3f] %s"
        % (nclu, d.mean(), lo, hi, "SIGNIFICANT" if (hi < 0 or lo > 0) else "ns"))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--donors", default="", help="explicit comma-separated ecoregion ids")
    ap.add_argument("--from", type=int, default=1, dest="start")
    ap.add_argument("--only", type=int, default=0)
    A = ap.parse_args()
    t0 = time.time()
    log("#" * 104)
    log("CORAL FULL SCALE -- 112 ecoregions, 20 donors, %d trees | %s" % (NPD * N_DONORS, mem_str()))
    steps = [A.only] if A.only else [s for s in (1, 2, 3, 4, 5) if s >= A.start]
    fns = {1: lambda: stage1(A.plan, A.threads), 2: lambda: stage2(A.plan),
           3: lambda: stage3(A.plan), 4: lambda: stage4(A.plan, A.donors),
           5: lambda: stage5(A.plan, A.seeds)}
    for s in steps:
        rc = fns[s]()
        if rc:
            log("STAGE %d returned %s -- stopping" % (s, rc))
            return rc
    log("=" * 104)
    log("ALL STAGES COMPLETE in %.1f h" % ((time.time() - t0) / 3600))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
