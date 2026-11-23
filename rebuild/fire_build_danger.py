"""OPERATIONAL FIRE-DANGER INDICES, built from the monthly panel.

WHY THIS EXISTS. Every benchmark so far compared the architecture against generic tabular learners --
RF, XGBoost, Tweedie -- plus climatology and persistence. Not one of them is what a fire agency
actually runs. The wildfire literature and every operational service on earth use FIRE-DANGER INDICES:
physically-motivated drought and fire-weather accumulators with decades of validation behind them. A
paper that omits them is not benchmarked against the field, and a referee will say so.

WHAT IS BUILT, and why each one is here.

  mdc        MONTHLY DROUGHT CODE (Girardin & Wotton 2009). The published monthly form of the
             Canadian FWI System's Drought Code -- the deep-duff moisture accumulator. This is the
             single most defensible index available from monthly data, because it was DESIGNED for
             monthly inputs by the people who maintain the FWI System. Two half-month steps per
             month, day-length factor Lf by calendar month, hemisphere-flipped south of the equator.

  kbdi       KEETCH-BYRAM DROUGHT INDEX, monthly recursion. The US operational standard, used by
             most American state and federal fire agencies. Cumulative moisture deficiency in the
             upper soil, 0-800, driven by max temperature and reset by rain.

  nesterov   NESTEROV INDEX. The Russian/Eurasian operational standard, used across the boreal and
             steppe zones that make up a third of our regions. Accumulates T*(T-Td) over rainless
             days and resets on rain.

  angstrom   ANGSTROM INDEX. The Scandinavian index, RH/20 + (27-T)/10. LOW values mean DANGEROUS,
             so it is stored NEGATED so that every column in this file points the same way.

  ffwi       FOSBERG FIRE WEATHER INDEX. The US spread-potential index: equilibrium fuel moisture
             from temperature and humidity, multiplied by a wind term. The only index here that uses
             wind, which is why it is included despite the monthly averaging blunting it.

  rh_pct     relative humidity, derived from saturation vapour pressure and the panel's VPD rather
             than from tc_vapor_pressure, because VPD is explicitly in kPa and the vapour-pressure
             column's units are not documented. RH is an input to three of the indices above and is
             a baseline in its own right.

THE HONEST LIMITATION, stated here so it is not discovered by a reviewer. The FWI System proper --
FFMC, ISI, BUI and the FWI itself -- is a DAILY system with 2/3-hour and 12-day memory constants.
Those cannot be computed from monthly means and are NOT approximated here; fire_fwi.py implements
them correctly and is waiting on the AgERA5 daily fetch. What this file provides is the subset of
operational indices that are either defined on monthly inputs (MDC) or whose accumulators have time
constants long enough that a monthly step is a documented approximation (KBDI, Nesterov). Each is
labelled as such. Monthly averaging necessarily blunts every one of them, which biases this
comparison IN THE ARCHITECTURE'S FAVOUR -- and that must be said in the paper, not hidden.

  py -3.9 -u fire_build_danger.py
  py -3.9 -u fire_build_danger.py --force=1
"""
import os
import sys
import time
import glob

import numpy as np
import pandas as pd

ARG = {a.split("=")[0]: a.split("=")[1] for a in sys.argv[1:] if "=" in a}
YEARS = list(range(2002, 2023))
FORCE = int(ARG.get("--force", 0))
DRV = r"D:\fire\drivers\joined"
OUT = ARG.get("--out", r"D:\fire\drivers\danger")
PANEL = "D:/monthly_panel/%s_monthly_%d.parquet"
NEED = ["lat", "lon", "year", "month", "V01_mean_temp_C", "diurnal_temp_range_C",
        "V02_total_precip_mm", "V05_mean_vpd_kPa", "V09_mean_wind_ms"]
DAYS = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
# Van Wagner's day-length adjustment for the Drought Code, by calendar month (northern hemisphere).
LF_N = np.array([-1.6, -1.6, -1.6, 0.9, 3.8, 5.8, 6.4, 5.0, 2.4, 0.4, -1.6, -1.6])


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def es_kpa(t):
    """Saturation vapour pressure, Tetens. t in C, result kPa."""
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def build(region):
    frames = []
    for y in YEARS:
        fp = PANEL % (region, y)
        if not os.path.exists(fp):
            return None
        frames.append(pd.read_parquet(fp, columns=NEED))
    P = pd.concat(frames, ignore_index=True)
    P["t"] = P.year * 12 + P.month
    P["cell"] = (np.round(P.lat.values.astype(np.float64), 5) * 1e5).astype(np.int64) \
        * 100000000 + (np.round(P.lon.values.astype(np.float64), 5) * 1e5).astype(np.int64)
    P = P.sort_values(["cell", "t"]).reset_index(drop=True)

    # NoData SENTINELS, and the project's earlier guard did not catch these. The panel writes missing
    # driver values as raster NoData rather than NaN: -2147483648 (int32) in precipitation, and
    # -32768 (INT16) in temperature, VPD and wind. The int32 form was guarded in 2026-08; the int16
    # form was not, so -32768 has been reaching models as if it were a temperature in Celsius. It is
    # a COASTLINE MASK -- cells partly over water -- affecting 11 of 40 regions, 7 of the 10 held-out
    # ones, worst in greece_mainland at 0.80% of rows. fillna() never touched it because it is not
    # NaN. Here it is fatal rather than marginal: one sentinel temperature drives the Angstrom index
    # to -3284 and the drought accumulators to nonsense for every later month in that cell, because
    # they are RECURSIVE. Blank them first, then interpolate within the cell so the recursion has
    # something to carry forward.
    for c in ("V01_mean_temp_C", "diurnal_temp_range_C", "V02_total_precip_mm",
              "V05_mean_vpd_kPa", "V09_mean_wind_ms"):
        v = P[c].values.astype(np.float64)
        P[c] = np.where(np.abs(v) >= 32000.0, np.nan, v)
    g = P.groupby("cell", sort=False)
    for c in ("V01_mean_temp_C", "diurnal_temp_range_C", "V02_total_precip_mm",
              "V05_mean_vpd_kPa", "V09_mean_wind_ms"):
        P[c] = g[c].transform(lambda z: z.interpolate(limit_direction="both"))
        P[c] = P[c].fillna(P[c].median())

    T = P.V01_mean_temp_C.values.astype(np.float64)
    DTR = np.nan_to_num(P.diurnal_temp_range_C.values.astype(np.float64), nan=8.0)
    TMAX = T + DTR / 2.0
    PR = np.clip(np.nan_to_num(P.V02_total_precip_mm.values.astype(np.float64)), 0, None)
    VPD = np.clip(np.nan_to_num(P.V05_mean_vpd_kPa.values.astype(np.float64)), 0, None)
    WS = np.clip(np.nan_to_num(P.V09_mean_wind_ms.values.astype(np.float64), nan=2.0), 0, None)
    MO = P.month.values.astype(int)
    ES = es_kpa(np.clip(T, -60, 60))
    RH = np.clip(100.0 * (1.0 - VPD / np.maximum(ES, 1e-6)), 1.0, 100.0)
    # dew point back out of actual vapour pressure, for Nesterov
    EA = np.maximum(ES - VPD, 1e-4)
    lg = np.log(EA / 0.6108)
    TD = 243.04 * lg / np.maximum(17.625 - lg, 1e-6)

    # hemisphere: the day-length factor must flip south of the equator, or the drought code peaks in
    # the wet season for half the planet.
    south = P.lat.values < 0
    lf = np.where(south, LF_N[(MO + 5) % 12], LF_N[MO - 1])
    nd = DAYS[MO - 1]

    # mean annual precipitation per cell -- KBDI's denominator term
    ann = P.groupby("cell").V02_total_precip_mm.transform("mean").values * 12.0
    ann_in = np.clip(np.nan_to_num(ann), 25.0, None) / 25.4

    cell = P.cell.values
    newcell = np.empty(len(P), bool)
    newcell[0] = True
    newcell[1:] = cell[1:] != cell[:-1]

    mdc = np.zeros(len(P))
    kbdi = np.zeros(len(P))
    nest = np.zeros(len(P))
    m_prev = 0.0
    k_prev = 0.0
    n_prev = 0.0
    for i in range(len(P)):
        if newcell[i]:
            m_prev, k_prev, n_prev = 0.0, 0.0, 0.0
        # ---- MONTHLY DROUGHT CODE, two half-month steps (Girardin & Wotton 2009) ----------------
        m = m_prev
        for _ in (0, 1):
            q = 800.0 * np.exp(-m / 400.0)
            rain = 0.83 * (PR[i] / 2.0) - 1.27          # effective rain, half the month
            if rain > 0:
                q = q + 3.937 * rain
                m = max(0.0, 400.0 * np.log(800.0 / max(q, 1e-6)))
            e = max(0.0, 0.5 * (0.36 * (TMAX[i] + 2.8) + lf[i]))
            m = max(0.0, m + e)
        mdc[i] = m
        m_prev = m
        # ---- KEETCH-BYRAM, monthly recursion -----------------------------------------------------
        # net rain removes deficiency first; then the daily drying factor times days in month.
        k = max(0.0, k_prev - max(0.0, PR[i] - 5.1))
        tf = np.clip(TMAX[i] * 9.0 / 5.0 + 32.0, -40, 150)   # KBDI is defined in Fahrenheit
        dq = ((800.0 - k) * (0.968 * np.exp(0.0486 * tf) - 8.30)
              / (1.0 + 10.88 * np.exp(-0.0441 * ann_in[i])) * 1e-3)
        k = float(np.clip(k + nd[i] * max(dq, 0.0), 0.0, 800.0))
        kbdi[i] = k
        k_prev = k
        # ---- NESTEROV, monthly approximation -----------------------------------------------------
        # resets when the month is wet, otherwise accumulates T*(T-Td) over the rainless fraction.
        if PR[i] > 20.0:
            n = 0.0
        else:
            dry = nd[i] * float(np.clip(1.0 - PR[i] / 20.0, 0.0, 1.0))
            n = n_prev + dry * max(0.0, TMAX[i]) * max(0.0, TMAX[i] - TD[i])
        nest[i] = n
        n_prev = n

    # ---- non-recursive indices -------------------------------------------------------------------
    ang = RH / 20.0 + (27.0 - T) / 10.0            # LOW = dangerous, so store negated
    mm = np.clip(RH, 1, 100)
    m1 = np.where(mm < 10, 0.03 + 0.281073 * mm - 0.000578 * mm * T,
                  np.where(mm < 50, 2.22749 + 0.160107 * mm - 0.014784 * T,
                           21.0606 + 0.005565 * mm ** 2 - 0.00035 * mm * T - 0.483199 * mm))
    r = np.clip(m1, 0, 30) / 30.0
    eta = 1.0 - 2.0 * r + 1.5 * r ** 2 - 0.5 * r ** 3
    ffwi = eta * np.sqrt(1.0 + (WS * 2.23694) ** 2) / 0.3002   # wind in mph

    P["mdc"] = mdc
    P["kbdi"] = kbdi
    P["nesterov"] = nest
    P["angstrom_neg"] = -ang
    P["ffwi"] = ffwi
    P["rh_pct"] = RH
    made = ["mdc", "kbdi", "nesterov", "angstrom_neg", "ffwi", "rh_pct"]
    for c in made:
        P[c] = P[c].replace([np.inf, -np.inf], np.nan)
    return P[["lat", "lon", "year", "month"] + made], made


def main():
    os.makedirs(OUT, exist_ok=True)
    regs = sorted(os.path.basename(f)[:-8] for f in glob.glob(os.path.join(DRV, "*.parquet")))
    log("=" * 104)
    log("OPERATIONAL FIRE-DANGER INDICES | %d regions | MDC, KBDI, Nesterov, Angstrom, FFWI, RH"
        % len(regs))
    log("  the DAILY FWI System (FFMC/ISI/BUI/FWI) is NOT approximated here -- see the docstring")
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
        skel = pd.read_parquet(os.path.join(DRV, "%s.parquet" % r),
                               columns=["lat", "lon", "year", "month"])
        res = skel.merge(P, on=["lat", "lon", "year", "month"], how="left")
        assert len(res) == len(skel), "join changed row count (%d -> %d)" % (len(skel), len(res))
        res.to_parquet(dst + ".part", index=False)
        os.replace(dst + ".part", dst)
        q = res[made].quantile([0.5, 0.99]).round(2)
        log("[%2d/%d] %-30s %.1f%% complete | median mdc %.0f kbdi %.0f nesterov %.0f | %.1f min"
            % (i + 1, len(regs), r, 100 * res[made].notna().all(axis=1).mean(),
               q.loc[0.5, "mdc"], q.loc[0.5, "kbdi"], q.loc[0.5, "nesterov"],
               (time.time() - t0) / 60))
    log("done -- wire in with fire_architecture's USE_DANGER / DANGER_DIR")


if __name__ == "__main__":
    main()
