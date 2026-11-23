"""Stage 1 of the coral table builder: the VISIT table, the split marks and the census (package-side, not engine).

    py -3.9 -u build_visits.py [--test-years 2016-2019] [--out D:/treeroute/coral_build/coral_data]

Written 2026-10-19 for D:/treeroute/coral_build/SPEC_CORAL_TABLES.md (sections 1, 2 and 4). Reads only:
  - the GCBD SQLite (read-only URI), the authoritative label and key source;
  - D:/coral/target/events_dated.parquet, as a CROSS-CHECK of lat, lon, ecoregion and date per Sample_ID;
  - D:/coral/drivers/sst_compact_all.npz members uk/start/end (small) and day (memory-mapped by offset,
    npz_map.py), to know which visits keep enough SST history before each lead's feature anchor.
It never opens D:/coral/drivers/sst_full_merged.parquet and never reads the sst member here.
Writes only under --out: visits.parquet, month_precision_rows.csv, visits_census.json.

Recipe and its sources:
  label      coral_smoke_regress.py:56-77 (continuous_target) unchanged: Reef_Check Population rows (level 1) ->
             mean of S1..S4; AGRRA, FRRP, McClanahan, Donner -> Percent_Bleached; Kumagai and Safaie excluded
             (ordinal only); mean per Sample_ID; rows outside [0, 100] dropped, not clipped.
  date       built from Sample_Event_tbl Date_Year/Month/Day (the events_dated 'date' column clamps the day at 28,
             CORAL_STATE.md:148-151, so it is not used). Precision 'month' when the source is Donner or Safaie
             and the day is 15 (CORAL_DATA_AUDIT.md:65-69: the day was imputed and cannot be recovered).
  dates      target date T = the survey day; for 'month' precision T = the LAST day of the month (the label is
             surely known by then) and the feature anchor = the FIRST day of the month (features end before
             the month starts). For 'day' precision the anchor is T. At lead L the issue date is T - L and every
             feature ends strictly before anchor - L, which is never later than the issue date.
  site       coral_safe.site_key(lat, lon) at 4 decimals (1e-4 degree, about 11 m; coral_safe.py:97-107), the same
             int64 key the SST compact uses. Package unit = ecoregion id + site key; lat/lon are written back from
             the key (so every visit of a unit has the same coordinates).
  visit      (unit, T). Labels of several Sample_IDs at one visit are AVERAGED (ruling-free default, CORAL_ENGINE_PLAN
             Q7 a); the merges are counted.
  group      the ecoregion NAME from Ecoregion_Name_LUT (Site_Info_tbl.Ecoregion_Name is an integer key into it).
  SST rule   coral_forecast.py:106-116: a series must exist, at least 365*10//2 = 1,825 daily values must lie
             strictly before the cut, and the MMM needs 10 distinct years before the cut (coral_dhw_model.py:69-78).
             Here the cut is anchor - L. The MMM's per-month test (60 values and 3 years in one month) is not
             checked here; stage 2 applies the full rule and drops (and logs) any extra row.
"""
import argparse
import datetime as dt
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, r"C:\Users\moh the ghost\Desktop\data set for reserch paper")  # coral_safe only (read)
from coral_safe import cap_threads, guard, mem_str, site_key  # noqa: E402

cap_threads(4)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from npz_map import member_map  # noqa: E402

DB = r"D:\coral\target\raw\gcbd\Global_Coral_Bleaching_Database_SQLite_11_24_21.db"
EV = r"D:\coral\target\events_dated.parquet"
COMPACT = r"D:\coral\drivers\sst_compact_all.npz"
LEADS = (0, 183, 365)                       # ruling I1 (OWNER_RULINGS_2026-09-28.md:104)
MIN_SST_VALUES = 365 * 10 // 2              # coral_forecast.py:64, 111
MIN_SST_YEARS = 10                          # coral_dhw_model.py:65, 75
INNER_SCORE_YEARS = 3                       # engine C2 (R7): the inner score is the 3 years before the test window
LABEL_SOURCES = ("Reef_Check", "AGRRA", "FRRP", "McClanahan", "Donner")
IMPUTED_DAY_SOURCES = ("Donner", "Safaie")
EPOCH = dt.date(1970, 1, 1)


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def read_gcbd():
    c = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    t = pd.read_sql("""
        SELECT b.Sample_ID sid, ds.Data_Source src, b.Bleaching_Level lvl,
               b.Percent_Bleached pct, b.S1, b.S2, b.S3, b.S4,
               se.Date_Year yr, se.Date_Month mo, se.Date_Day dy,
               si.Latitude_Degrees lat, si.Longitude_Degrees lon, si.Ecoregion_Name eco
        FROM Bleaching_tbl b
        JOIN Sample_Event_tbl se ON se.Sample_ID = b.Sample_ID
        JOIN Site_Info_tbl si    ON si.Site_ID   = se.Site_ID
        JOIN Data_Source_LUT ds  ON ds.Data_Source_ID = si.Data_Source""", c)
    lut = pd.read_sql("SELECT Ecoregion_ID, Ecoregion_Name FROM Ecoregion_Name_LUT", c)
    c.close()
    return t, dict(zip(lut.Ecoregion_ID.astype(int), lut.Ecoregion_Name.astype(str)))


def label_per_sample(t):
    """coral_smoke_regress.py:65-76, unchanged in substance; also keeps the keys of each Sample_ID."""
    for k in ("pct", "S1", "S2", "S3", "S4", "lvl"):
        t[k] = pd.to_numeric(t[k], errors="coerce")
    rc = t[(t.src == "Reef_Check") & (t.lvl == 1)].copy()
    rc["y"] = rc[["S1", "S2", "S3", "S4"]].mean(axis=1)
    ot = t[t.src.isin(["AGRRA", "FRRP", "McClanahan", "Donner"]) & t.pct.notna()].copy()
    ot["y"] = ot.pct
    keys = ["sid", "src", "yr", "mo", "dy", "lat", "lon", "eco"]
    y = pd.concat([rc[keys + ["y"]], ot[keys + ["y"]]], ignore_index=True).dropna(subset=["y"])
    n_rows = y.groupby("sid").size()
    agg = y.groupby("sid").agg(y=("y", "mean"), src=("src", "first"), yr=("yr", "first"),
                               mo=("mo", "first"), dy=("dy", "first"), lat=("lat", "first"),
                               lon=("lon", "first"), eco=("eco", "first"))
    agg["n_label_rows"] = n_rows
    out_of_range = int(((agg.y < 0) | (agg.y > 100)).sum())
    agg = agg[(agg.y >= 0) & (agg.y <= 100)]
    return agg.reset_index(), out_of_range


def cross_check(s):
    ev = pd.read_parquet(EV)
    m = s.set_index("sid").join(ev[["lat", "lon", "eco", "yr", "mo", "dy"]], rsuffix="_ev", how="left")
    out = {"samples_not_in_events_dated": int(m.lat_ev.isna().sum())}
    for k in ("lat", "lon", "eco", "yr", "mo", "dy"):
        a, b = m[k].astype("float64"), m[k + "_ev"].astype("float64")
        both = a.notna() & b.notna()
        out["mismatch_" + k] = int((both & ~np.isclose(a, b, rtol=0, atol=1e-9)).sum())
    return out


def build_visits(s, names):
    s = s[s.eco.notna()].copy()
    s["eco_id"] = s.eco.astype(int)
    unknown = sorted(set(s.eco_id) - set(names))
    if unknown:
        raise SystemExit("ecoregion ids missing from Ecoregion_Name_LUT: %s" % unknown)
    s["group"] = s.eco_id.map(names)
    yr, mo, dy = s.yr.astype(int).values, s.mo.astype(int).values, s.dy.astype(int).values
    day_date = [dt.date(a, b, c) for a, b, c in zip(yr, mo, dy)]          # raises on an impossible date
    month_first = [dt.date(a, b, 1) for a, b in zip(yr, mo)]
    month_last = [(dt.date(a + (b == 12), b % 12 + 1, 1) - dt.timedelta(days=1)) for a, b in zip(yr, mo)]
    imputed = s.src.isin(IMPUTED_DAY_SOURCES).values & (dy == 15)
    s["date_precision"] = np.where(imputed, "month", "day")
    s["target_date"] = [ml if f else d for d, ml, f in zip(day_date, month_last, imputed)]
    s["anchor_date"] = [mf if f else d for d, mf, f in zip(day_date, month_first, imputed)]
    s["survey_date_recorded"] = day_date
    key = site_key(s.lat.values, s.lon.values)
    s["site_key"] = key
    scale = 10 ** 4
    a, b = key // (360 * scale + 1), key % (360 * scale + 1)
    s["lat4"] = a / scale - 90.0
    s["lon4"] = b / scale - 180.0
    s["unit_id"] = ["%03d_%.4f_%.4f" % (e, la, lo) for e, la, lo in zip(s.eco_id, s.lat4, s.lon4)]
    g = s.groupby(["unit_id", "target_date"], sort=True)
    v = g.agg(group=("group", "first"), eco_id=("eco_id", "first"), lat=("lat4", "first"),
              lon=("lon4", "first"), site_key=("site_key", "first"), y=("y", "mean"),
              y_min=("y", "min"), y_max=("y", "max"), n_samples=("sid", "size"),
              n_programmes=("src", "nunique"), programme=("src", "first"),
              date_precision=("date_precision", "max"), anchor_date=("anchor_date", "min"),
              n_precisions=("date_precision", "nunique"),
              sids=("sid", lambda x: ";".join(str(int(i)) for i in sorted(x)))).reset_index()
    v.loc[v.n_programmes > 1, "programme"] = "mixed"
    # A visit that merges a month-precision sample with a day-precision one on the month's last day takes
    # month precision ("month" > "day" as text) and the earliest anchor: features end before the month starts.
    v["mixed_precision"] = v.n_precisions > 1
    v["row_id"] = v.unit_id + "|" + v.target_date.map(lambda d: d.isoformat())
    return s, v.drop(columns=["n_precisions"])


def sst_history(v):
    """Per visit and lead: SST values and distinct years strictly before anchor - L (one pass per site)."""
    uk = np.asarray(member_map(COMPACT, "uk.npy"))
    st = np.asarray(member_map(COMPACT, "start.npy"))
    en = np.asarray(member_map(COMPACT, "end.npy"))
    day = member_map(COMPACT, "day.npy")                    # int32 days since 1970-01-01, mapped, not loaded
    anchor = np.array([(d - EPOCH).days for d in v.anchor_date], dtype="int64")
    pos = np.searchsorted(uk, v.site_key.values)
    pos[pos >= len(uk)] = 0
    has = uk[pos] == v.site_key.values
    res = {L: (np.zeros(len(v), "int64"), np.zeros(len(v), "int64")) for L in LEADS}
    first = np.full(len(v), -1, "int64")
    order = np.argsort(pos, kind="stable")
    done_sites = 0
    i = 0
    while i < len(order):
        k = pos[order[i]]
        j = i
        while j < len(order) and pos[order[j]] == k:
            j += 1
        rows = order[i:j]
        rows = rows[has[rows]]
        if len(rows):
            d = np.asarray(day[int(st[k]):int(en[k])], dtype="int64")
            yrs = (d.astype("datetime64[D]").astype("datetime64[Y]").astype("int64") + 1970)
            ychange = np.r_[0, np.cumsum(np.diff(yrs) != 0)]          # distinct-year counter (sorted days)
            first[rows] = d[0] if len(d) else -1
            for L in LEADS:
                n = np.searchsorted(d, anchor[rows] - L, side="left")
                res[L][0][rows] = n
                res[L][1][rows] = np.where(n > 0, ychange[np.maximum(n - 1, 0)] + 1, 0)
            done_sites += 1
            if done_sites % 1000 == 0:
                guard(2.5, "sst history")
        i = j
    for L in LEADS:
        v["sst_n_before_L%d" % L] = res[L][0]
        v["sst_years_before_L%d" % L] = res[L][1]
        v["present_L%d" % L] = has & (res[L][0] >= MIN_SST_VALUES) & (res[L][1] >= MIN_SST_YEARS)
    v["has_sst_series"] = has
    return v


def census(v, test_years, s_counts):
    y0_test, y1_test = test_years
    t = pd.to_datetime(v.target_date)
    v["mark"] = np.where(t < pd.Timestamp(y0_test, 1, 1), "train",
                         np.where(t <= pd.Timestamp(y1_test, 12, 31), "test", "unused"))
    train_end = dt.date(y0_test - 1, 12, 31)
    inner_end = dt.date(y0_test - 1 - INNER_SCORE_YEARS, 12, 31)
    first_test, first_inner = dt.date(y0_test, 1, 1), dt.date(y0_test - INNER_SCORE_YEARS, 1, 1)
    cuts = {"L0_fit": (0, train_end), "L0_inner": (0, inner_end)}
    for L in LEADS[1:]:
        cuts["L%d_fit" % L] = (L, first_test - dt.timedelta(days=L))
        cuts["L%d_guard" % L] = (L, first_inner - dt.timedelta(days=L))
    sample = v[v.present_L0 & (v.mark != "unused")]
    out = dict(s_counts)
    out["test_years"] = [y0_test, y1_test]
    out["cuts"] = {k: [L, c.isoformat()] for k, (L, c) in cuts.items()}
    out["visits_all"] = int(len(v))
    out["visits_merged_from_more_than_one_sample"] = int((v.n_samples > 1).sum())
    out["samples_absorbed_by_merges"] = int((v.n_samples - 1).sum())
    out["merged_visits_with_disagreeing_labels"] = int(((v.n_samples > 1) & (v.y_max > v.y_min)).sum())
    out["merged_visits_mixed_programme"] = int((v.programme == "mixed").sum())
    out["merged_visits_mixed_precision"] = int(v.mixed_precision.sum())
    out["visits_unused_after_window"] = int((v.mark == "unused").sum())
    out["visits_no_sst_series"] = int((~v.has_sst_series & (v.mark != "unused")).sum())
    out["visits_short_sst_history_L0"] = int((v.has_sst_series & ~v.present_L0 & (v.mark != "unused")).sum())
    out["month_precision_visits_in_sample"] = int((sample.date_precision == "month").sum())
    out["month_precision_by_mark"] = sample[sample.date_precision == "month"].mark.value_counts().to_dict()
    yrs = pd.to_datetime(sample.target_date).dt.year
    mp = sample.date_precision == "month"
    out["month_precision_in_inner_score_years"] = int((mp & yrs.between(y0_test - INNER_SCORE_YEARS,
                                                                          y0_test - 1)).sum())
    out["sample_rows"] = int(len(sample))
    out["sample_first_year"] = int(yrs.min())
    per = {}
    for mark in ("train", "test"):
        m = sample[sample.mark == mark]
        per[mark] = {"rows": int(len(m)), "groups": int(m.group.nunique()), "units": int(m.unit_id.nunique()),
                     "programmes": m.programme.value_counts().to_dict()}
    out["split"] = per
    for L in LEADS:
        m = sample[sample["present_L%d" % L]]
        out["rows_present_L%d" % L] = {mk: int((m.mark == mk).sum()) for mk in ("train", "test")}
    groups = sorted(sample.group.unique())
    gtab = {}
    for g in groups:
        m = sample[sample.group == g]
        row = {"rows": int(len(m)), "train": int((m.mark == "train").sum()), "test": int((m.mark == "test").sum()),
               "units": int(m.unit_id.nunique()), "programmes": sorted(m.programme.unique().tolist())}
        td = m.target_date
        for name, (L, c) in cuts.items():
            row[name] = int(((td <= c) & m["present_L%d" % L] & (m.mark == "train")).sum())
        row["inner_score_rows"] = int(((pd.to_datetime(td).dt.year >= y0_test - INNER_SCORE_YEARS)
                                       & (m.mark == "train")).sum())
        vis = m[(m.mark == "train") & (pd.to_datetime(td).dt.year.between(int(yrs.min()), inner_end.year))]
        per_unit = vis.groupby("unit_id").size()
        cand = m[m.mark == "train"].unit_id.unique()
        row["h_median_rows_per_candidate_unit"] = float(np.median(per_unit.reindex(cand).fillna(0).values)) \
            if len(cand) else None
        gtab[g] = row
    out["groups"] = gtab
    out["groups_zero_rows_at_a_cut"] = {name: [g for g in groups if gtab[g][name] == 0] for name in cuts}
    out["groups_one_unit"] = [g for g in groups if gtab[g]["units"] == 1]
    cand_all = sample[sample.mark == "train"]
    vis = cand_all[pd.to_datetime(cand_all.target_date).dt.year <= inner_end.year].groupby("unit_id").size()
    out["R12_h_all"] = float(np.median(vis.reindex(cand_all.unit_id.unique()).fillna(0).values))
    shared = sample.groupby("site_key").group.nunique()
    out["site_keys_in_two_or_more_groups"] = int((shared > 1).sum())
    return v, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-years", default="2016-2019")
    ap.add_argument("--out", default=r"D:\treeroute\coral_build\coral_data")
    A = ap.parse_args()
    ty = tuple(int(x) for x in A.test_years.split("-"))
    if not os.path.abspath(A.out).lower().startswith(r"d:\treeroute\coral_build".lower()):
        raise SystemExit("refused: --out must be under D:\\treeroute\\coral_build")
    os.makedirs(A.out, exist_ok=True)
    log("GCBD read | %s" % mem_str())
    t, names = read_gcbd()
    counts = {"gcbd_bleaching_rows": int(len(t)),
              "gcbd_rows_by_source": t.src.value_counts().to_dict()}
    s, oor = label_per_sample(t)
    counts["samples_with_label"] = int(len(s))
    counts["samples_dropped_out_of_range"] = oor
    counts["samples_with_label_by_source"] = s.src.value_counts().to_dict()
    counts["samples_averaged_over_label_rows"] = int((s.n_label_rows > 1).sum())
    counts["samples_no_ecoregion"] = int(s.eco.isna().sum())
    counts["events_dated_cross_check"] = cross_check(s)
    log("labels %d samples | cross-check %s" % (len(s), counts["events_dated_cross_check"]))
    s, v = build_visits(s, names)
    log("visits %d from %d samples | %s" % (len(v), len(s), mem_str()))
    v = sst_history(v)
    v, out = census(v, ty, counts)
    v.to_parquet(os.path.join(A.out, "visits.parquet"), index=False)
    mp = v[(v.date_precision == "month") & v.present_L0 & (v.mark != "unused")]
    mp[["row_id", "group", "programme", "target_date", "anchor_date", "mark", "sids"]].to_csv(
        os.path.join(A.out, "month_precision_rows.csv"), index=False)
    with open(os.path.join(A.out, "visits_census.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    log("wrote visits.parquet (%d), month_precision_rows.csv (%d), visits_census.json | %s"
        % (len(v), len(mp), mem_str()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
