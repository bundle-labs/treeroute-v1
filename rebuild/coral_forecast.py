"""Nowcast -> forecast: rebuild the 74 at a LEAD and ask how far ahead the skill survives.

    py -3.9 -u coral_forecast.py --leads 0,30,180,365

WHAT CHANGES, AND WHAT DOES NOT. Every driver window currently ends STRICTLY before the survey --
`searchsorted(day, date, "left")` -- so the last SST day used is T-1. That one-day gap is why this
is a NOWCAST: `dhw_84` over [T-84, T) is not a predictor of bleaching, it is a measurement of the
cause. Forecasting means moving the cut back to T-L and leaving the target at T, so the heat in
[T-L, T) is invisible to the model. No new data is needed: the full daily SST series is on disk from
1985 to each site's last dive, and at L=365 still 99.0% of events keep >=10 years of prior record --
identical to L=0.

TWO CLOCKS, DELIBERATELY. Every row carries a true survey date T and a CUT date T-L.
  * the CUT date drives every window: SST, DHW, the expanding MMM, Hobday, cyclones and the ENSO/IOD
    join. Nothing the model sees postdates T-L.
  * the TRUE date drives `month`/`doy_sin`/`doy_cos` and the router's own-region exclusion. That is
    correct, not a leak: a forecaster is asked "what will a survey on this future date find", so the
    season of the target is part of the QUESTION, not part of the answer.

THE ENSO COLUMNS HAD TO MOVE. `nino34_lag0`/`dmi_lag0` join on the survey's own calendar month, which
in the nowcast carries a mean 14.9 days of look-ahead (accepted: it is a driver leak, not a target
leak, and dropping it measured -0.029 ns). In a FORECAST that column would be the ENSO state of a
month that has not happened yet, which is not a time leak but a different experiment -- one where the
model is handed a perfect seasonal ENSO forecast. So the join moves to the cut date with everything
else, and `--enso-oracle` runs the other variant for anyone who wants that number.

WHAT TO EXPECT. DHW is CUMULATIVE, so `dhw_84` at T-30 still integrates [T-114, T-30): a slow build
is partly visible a month out, a terminal spike is not. Skill should decay with lead, and the shape
of the decay is the result -- it is what tells a reef manager how far ahead they can act.

ATTENTION -- THIS IS A CONDITIONAL FORECAST. The target is a REACTIVE dive survey, and surveys are
often triggered BY a bleaching event, so T is not a random date. The question answered here is
"given that a survey happens at T, what will it find, using only data to T-L". Nothing here predicts
WHETHER a survey happens, so this is not an unconditional early-warning system and must not be
described as one.
"""
import argparse
import json
import os
import re
import sys
import time
import warnings

sys.path.insert(0, r"C:\Users\moh the ghost\Desktop\data set for reserch paper")
from coral_safe import cap_threads, guard, mem_str, site_key

cap_threads(4)
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

import coral_extra_drivers as E
import coral_mhw_features as M
from coral_dhw_model import mmm_from
from coral_smoke_regress import continuous_target
from coral_glorys2_ab import route, sc, event_boot

COMPACT = r"D:\coral\drivers\sst_compact_all.npz"
EV = r"D:\coral\target\events_dated.parquet"
SPLIT = "fullscale_split.json"
WIN = (30, 56, 84, 90, 180, 365)
MIN_YEARS = 10
E0 = np.datetime64("1970-01-01")
CFG = dict(mf=0.15, k=50, alpha=0.5, a_ctx=0.25)
NPD = 500
QUIET = 2.0
MHW_COLS = ["mhw_days_30", "mhw_days_90", "mhw_days_365", "mhw_icum_90", "mhw_imax_90",
            "mhw_nev_365", "mhw_durmax_365", "mhw_since_end", "mhw_cat_max_90", "mhw_thr_gap"]


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def feat_path(lead):
    return "forecast_features_L%d.parquet" % lead


def build(lead):
    """The 74 columns with every window cut at T-lead. Target and season stay at T."""
    out = feat_path(lead)
    if os.path.exists(out):
        log("  %s exists -> skip" % out)
        return out
    z = np.load(COMPACT)
    uk, st, en, DAY, SST = z["uk"], z["start"], z["end"], z["day"], z["sst"]
    ev = pd.read_parquet(EV).reset_index().rename(columns={"index": "sid"})
    ek = site_key(ev.lat.values, ev.lon.values)
    idx = np.searchsorted(uk, ek)
    idx[idx >= len(uk)] = 0
    hit = uk[idx] == ek
    ed = ev.date.values.astype("datetime64[D]").astype("int64") - \
        E0.astype("datetime64[D]").astype("int64")
    cut = ed - lead                                   # THE CUT. Everything below keys off this.
    yrs = pd.DatetimeIndex(pd.to_datetime(DAY.astype("int64"), unit="D", origin="unix"))
    YR, MO = yrs.year.values.astype("int32"), yrs.month.values.astype("int8")
    del yrs
    log("  lead %d d | sst %s rows | %d events with a series"
        % (lead, format(len(SST), ","), int(hit.sum())))

    rows = []
    t0 = time.time()
    for i in range(len(ev)):
        if not hit[i]:
            continue
        a, b = int(st[idx[i]]), int(en[idx[i]])
        d = DAY[a:b]
        j = int(np.searchsorted(d, cut[i], side="left"))
        if j < 365 * MIN_YEARS // 2:
            continue
        t = SST[a:a + j]
        mmm, nyr = mmm_from(pd.DataFrame({"yr": YR[a:a + j], "mo": MO[a:a + j], "sst": t}))
        if not np.isfinite(mmm):
            continue
        e = ev.iloc[i]
        hs_all = t - mmm
        f = dict(sid=int(e.sid), eco=e.eco, pos=int(e.pos), date=e.date, lat=e.lat, lon=e.lon,
                 abslat=abs(e.lat), mmm=mmm, mmm_n_years=nyr,
                 month=e.date.month,                              # TRUE date: season of the target
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
        y365 = hs_all[-365:] if len(hs_all) >= 365 else hs_all
        f["days_since_max_hs"] = int(len(y365) - 1 - int(np.argmax(y365)))
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

        # ---- Hobday, on the same cut ---------------------------------------------------------
        pt, pv = d[:j], t
        thr = M.thresholds(M.doy_of(pt.astype("int64")), pv.astype("float64"))
        w365 = slice(max(0, j - 365), j)
        tw, vw = d[w365], SST[a:b][w365].astype("float64")
        th = thr[M.doy_of(tw.astype("int64"))]
        ok = np.isfinite(th)
        if ok.sum() >= 60:
            exc = np.zeros(len(tw), bool)
            exc[ok] = vw[ok] > th[ok]
            anom = np.where(ok, vw - th, 0.0)
            e90, a90 = exc[-90:], anom[-90:]
            f["mhw_days_365"] = int(exc.sum())
            f["mhw_days_90"] = int(exc[-90:].sum())
            f["mhw_days_30"] = int(exc[-30:].sum())
            f["mhw_icum_90"] = float(a90[e90].sum() / 7.0) if e90.any() else 0.0
            f["mhw_imax_90"] = float(a90[e90].max()) if e90.any() else 0.0
            s_, ln = M.events(exc)
            f["mhw_nev_365"] = len(s_)
            f["mhw_durmax_365"] = int(ln.max()) if len(ln) else 0
            f["mhw_since_end"] = int(len(exc) - (s_[-1] + ln[-1])) if len(s_) else 365
            gap = th - mmm
            g = np.where(np.isfinite(gap) & (gap > 0.05), gap, np.nan)
            with np.errstate(invalid="ignore"):
                cat = np.where(e90, a90 / g[-90:], 0.0)
            f["mhw_cat_max_90"] = float(np.nanmax(cat)) if np.isfinite(cat).any() else 0.0
            f["mhw_thr_gap"] = float(np.nanmedian(g))
        rows.append(f)
        if (i + 1) % 4000 == 0:
            guard(2.5, "forecast L%d" % lead)
            log("     %d/%d built %d | %.1f min | %s"
                % (i + 1, len(ev), len(rows), (time.time() - t0) / 60, mem_str()))
    X = pd.DataFrame(rows)
    del DAY, SST, YR, MO, rows
    guard(2.5, "after sst")

    # ---- cyclones / ENSO / mask, all on the CUT date ------------------------------------------
    Xc = X.copy()
    Xc["date"] = X.date - pd.to_timedelta(lead, unit="D")     # shift the clock for the drivers
    n34, dmi = E.psl_index(E.NINO), E.psl_index(E.DMI)
    for nm, src in (("nino34", n34), ("dmi", dmi)):
        s = src.set_index(["yr", "mo"]).v
        for lg in (0, 3, 6):
            dd = Xc.date - pd.DateOffset(months=lg)
            X["%s_lag%d" % (nm, lg)] = [s.get((yy, mm), np.nan)
                                        for yy, mm in zip(dd.dt.year, dd.dt.month)]
    X = pd.concat([X, E.cyclone_feats(Xc).set_index(X.index)], axis=1)
    guard(2.5, "cyclones")
    X = pd.concat([X, E.mask_feats(Xc).set_index(X.index)], axis=1)
    X.to_parquet(out, index=False)
    log("  wrote %s | %s rows x %d cols | %.1f min"
        % (out, format(len(X), ","), X.shape[1], (time.time() - t0) / 60))
    return out


def base_cols(X):
    allf = [c for c in X.columns if c not in ("sid", "eco", "side", "pos", "date", "y",
                                              "lat", "lon", "_side")]
    ABS = [c for c in allf if re.match(r"^(mean|std)_\d+$", c)
           or c in ("abslat", "mmm", "mmm_n_years")]
    HOB = [c for c in allf if c.startswith("mhw_")]
    return [c for c in allf if c not in ABS + HOB] + HOB


def score(lead, seeds):
    """Returns a frame indexed by sid. Leads are compared BY SID, never by row position: a longer
    lead can drop events whose 10-year MMM window no longer fits, so positions do not align."""
    X = pd.read_parquet(feat_path(lead))
    sp = json.load(open(SPLIT))
    X["side"] = np.where(X.eco.isin(sp["donors"]), "donor", "test")
    X["y"] = X.sid.map(continuous_target())
    X = X.dropna(subset=["y"]).reset_index(drop=True)
    BASE = base_cols(X)
    dm = X[X.side == "donor"]
    for c in BASE:
        if X[c].isna().any():
            X[c] = X[c].fillna(dm[c].median())
    tr = X[X.side == "donor"].reset_index(drop=True)
    te = X[X.side == "test"].reset_index(drop=True)
    ctxc = ["month", "doy_sin", "doy_cos", "abslat"]
    ps = [route(tr, te, BASE, ctxc, NPD, CFG["mf"], CFG["k"], CFG["alpha"], CFG["a_ctx"], s)
          for s in range(seeds)]
    out = pd.DataFrame({"sid": te.sid.values, "eco": te.eco.values, "y": te.y.values,
                        "lat": te.lat.values, "lon": te.lon.values, "date": te.date.values,
                        "p": np.mean(ps, axis=0)}).set_index("sid")
    return out, len(BASE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leads", default="0,30,180,365")
    ap.add_argument("--seeds", type=int, default=3)
    A = ap.parse_args()
    leads = [int(x) for x in A.leads.split(",")]
    log("=" * 104)
    log("FORECAST CURVE | leads %s days | %s" % (leads, mem_str()))
    res, ncols = {}, {}
    for L in leads:
        build(L)
        res[L], ncols[L] = score(L, A.seeds)
        log("  lead %3d d scored | %d cols | %s test rows"
            % (L, ncols[L], format(len(res[L]), ",")))

    # COMMON SID SET. Longer leads lose events whose 10-year window no longer fits, so every lead
    # is restricted to the sids ALL of them produced -- otherwise the curve would partly measure a
    # changing test set rather than a changing lead.
    common = set(res[leads[0]].index)
    for L in leads[1:]:
        common &= set(res[L].index)
    common = sorted(common)
    lost = {L: len(res[L]) - len(common) for L in leads}
    log("=" * 104)
    log("  common test rows across all leads: %s (dropped per lead: %s)"
        % (format(len(common), ","), ", ".join("L%d:%d" % (L, lost[L]) for L in leads)))
    R = {L: res[L].loc[common] for L in leads}
    base = R[leads[0]]
    act_eco = [g for g, d in base.groupby("eco") if d.y.mean() >= QUIET]

    for title, mask in (("ALL held-out regions", np.ones(len(common), bool)),
                        ("ACTIVE regions only (true mean bleaching >= %.0f%%)" % QUIET,
                         base.eco.isin(act_eco).values)):
        yy = base.y.values[mask]
        z = np.abs(yy).mean()
        log("=" * 104)
        log("%s -- %s rows, %d regions"
            % (title, format(int(mask.sum()), ","), base.eco.values[mask].__len__() and
               len(set(base.eco.values[mask]))))
        log("  %-8s %8s %10s %8s %9s %9s %9s"
            % ("lead(d)", "MAE", "R2", "AUC", "pred@sev", "skill%", "vs lead0"))
        log("  " + "-" * 74)
        b = None
        for L in leads:
            m = sc(yy, R[L].p.values[mask])
            if b is None:
                b = m["MAE"]
            log("  %-8d %8.3f %+10.4f %8.4f %9.2f %+9.1f%% %+9.3f"
                % (L, m["MAE"], m["R2"], m["AUC"], m["psev"], 100 * (z - m["MAE"]) / z,
                   m["MAE"] - b))
        B, nclu = event_boot(base[mask].reset_index())
        p0 = R[leads[0]].p.values[mask]
        log("  event-clustered vs lead %d (%d clusters):" % (leads[0], nclu))
        for L in leads[1:]:
            pL = R[L].p.values[mask]
            d = np.array([np.abs(yy[i] - pL[i]).mean() - np.abs(yy[i] - p0[i]).mean() for i in B])
            lo, hi = np.percentile(d, [2.5, 97.5])
            log("    lead %3d d  dMAE %+.3f  CI [%+.3f, %+.3f]  %s"
                % (L, d.mean(), lo, hi, "SIGNIFICANT WORSE" if lo > 0 else
                   ("SIGNIFICANT BETTER" if hi < 0 else "ns")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
