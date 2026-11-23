"""Check a built set of coral lead tables against the table contract (package-side checker, not engine code).

SENSITIVITY COPY (2026-10-28, owner ruling AN3; declared coral 2017-2020 sensitivity row, ruling V3,
engine/PREREGISTRATION_DRAFT_coral.md 4.2 step 3). Copied from D:/treeroute/coral_build/coral_tables/check_tables.py
(SHA-256 13756d9b...). The ONLY change is the declared option `--visits-dir DIR` (REQUIRED here, under
D:/treeroute/analysis/coral_sens_2017_2020): it sets the folder that holds visits_census.json and <build>/.

    py -3.9 -u check_tables.py --build full --visits-dir D:/treeroute/analysis/coral_sens_2017_2020/coral_data

Original usage (headline copy):
    py -3.9 -u check_tables.py [--build tiny]
    py -3.9 -u check_tables.py --build tiny --negative-control    # the checker must see a one-day look-ahead

Written 2026-10-19 for D:/treeroute/coral_build/SPEC_CORAL_TABLES.md (tiny-mode acceptance) and the table contract
D:/treeroute/coral_build/SPEC_TABLE_MODE.md sections 1.2-1.6 and 2.1. It re-reads the lead files on their own and
does NOT import build_tables.py, so its look-ahead test is an independent recomputation. Reads only; writes nothing
except check_report.json in the build folder.

Part A, contract (SPEC 2.1 ids): T-FILES, T-COLUMNS (names, order, dtypes), T-ROWID (+ row_id = unit|date, rows
sorted by row id in code-point order), T-UNITTIME, T-UNIT, T-ISSUE, T-FEATEND, T-LEADSET, T-RANGE, T-FINITE, T-MARK
(train before 1 January of the first test year, test inside the test years), T-NAMES.
Part B, no feature input after the issue date (independent): for every row and lead (every row in tiny mode) the
checker takes the SST record strictly before C - g, the IBTrACS points strictly before C - g and the index months
whose content ends before C (C = anchor - L, anchor from rows_audit.parquet, g from build_manifest.json), with its
OWN code: the MMM (monthly means per year in float64, a linear fit per calendar month read at epoch 1988.2857, the
largest month), the 30 SST heat columns, the 15 window cyclone columns, the 3 nino34a columns and the season context.
The MMM must match within 1e-4 C (own float64 means vs the legacy float32 means); the heat columns are then
recomputed with the table's MMM and must match within relative 1e-9 (counts exactly), as the rest; cyc_mindist within relative 1e-6 (the
legacy haversine evaluates cos(lat2) in float32). Then it checks the bound itself:
C - g - 1 <= feature_end < issue date. A match proves that THE CHECKED COLUMNS need no data on or after C - g (SST,
cyclones) or C (indices), and C <= issue date.
Reach (FIX_REPORT.md, correctness review item 4): Part B recomputes 53 of the 74 numeric columns: ctx_mmm, the 30
SST heat columns, the 15 window cyclone columns, nino34a_lag3/6/9 and the season context (ctx_month, ctx_doy_sin,
ctx_doy_cos, ctx_abslat). It does NOT recompute 21 columns: the 7 heat-history columns, the 10 marine-heatwave
columns, cyc_days_since_close and dmi_lag3/6/9. Those rest on the builder's own look-ahead canary and its g = 0
replay only; an independent recompute of them is an open item.
"""
import argparse
import datetime as dt
import io
import json
import os
import sys

sys.path.insert(0, r"C:\Users\moh the ghost\Desktop\data set for reserch paper")
from coral_safe import cap_threads, guard  # noqa: E402

cap_threads(4)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from columns import COLUMNS  # noqa: E402
from npz_map import member_map  # noqa: E402

DATA = r"D:\treeroute\coral_build\coral_data"
COMPACT = r"D:\coral\drivers\sst_compact_all.npz"
IBT = r"D:\coral\drivers\static\IBTrACS.ALL.v04r01.nc"
NINO = r"D:\coral\drivers\climate\nina34.txt"
E0 = dt.date(1970, 1, 1)
LEADS = (0, 183, 365)
SENTINEL = 1e30                     # engine S5.sentinel_mask_abs (treeroute/engine_constants.py:325)
RESERVED = {"unit", "group", "time", "year", "lead", "issue", "y", "normal", "legal_min", "legal_max"}  # metrics.py:157
RTOL, ATOL = 1e-9, 1e-9           # float64 arithmetic in a different order
MINDIST_RTOL = 1e-6                 # the legacy hav (coral_extra_drivers.py:39-43) multiplies the float32 track
                                    # latitude by a Python float, so numpy 2 evaluates cos(lat2) in float32 (3e-8)
MMM_ATOL = 1e-4                     # deg C: own float64 monthly means vs the builder's float32 means (legacy mmm_from)
EPOCH_YEAR = 1988.2857              # coral_dhw_model.py:64
WIN = (30, 56, 84, 90, 180, 365)


def dnum(d):
    return (d - E0).days


class Report:
    def __init__(self):
        self.fail, self.ok = [], []

    def check(self, cond, cid, msg):
        (self.ok if cond else self.fail).append("%s %s" % (cid, msg))
        print(("  ok   " if cond else "  FAIL ") + cid + " " + msg, flush=True)


# ---------------------------------------------------------------------------------------------------- Part A
def part_a(R, folder, census):
    roles = {c["name"]: c["role"] for c in COLUMNS}
    names = [c["name"] for c in COLUMNS]
    files = sorted(f for f in os.listdir(folder) if f.startswith("lead_") and f.endswith(".parquet"))
    R.check(files == sorted("lead_%d.parquet" % L for L in LEADS), "T-FILES", "files %s" % files)
    want_type = {}
    for n, r in roles.items():
        if r in ("key_row", "key_unit", "key_group", "key_mark", "report_stratum"):
            want_type[n] = pa.string()
        elif r in ("key_time", "key_issue", "key_feature_end"):
            want_type[n] = pa.date32()
        else:
            want_type[n] = pa.float64()
    T = {}
    for L in LEADS:
        t = pq.read_table(os.path.join(folder, "lead_%d.parquet" % L))
        R.check(t.column_names == names, "T-COLUMNS", "lead %d: %d columns in columns.py order" % (L, t.num_columns))
        bad = [n for n in names if n in t.column_names and t.schema.field(n).type != want_type[n]]
        R.check(not bad, "T-COLUMNS", "lead %d dtypes (strings / date32 / float64); wrong: %s" % (L, bad))
        df = t.to_pandas()
        for c in ("target_date", "issue_date", "feature_end"):
            df[c] = [dnum(x) for x in df[c]]
        T[L] = df
        rid = df.row_id
        R.check(rid.is_unique and (rid.str.len() > 0).all(), "T-ROWID", "lead %d: %d unique non-empty ids" % (L, len(df)))
        R.check(list(rid) == sorted(rid), "T-ROWID", "lead %d rows sorted by row id (code points)" % L)
        rebuilt = df.unit_id + "|" + [(E0 + dt.timedelta(days=int(x))).isoformat() for x in df.target_date]
        R.check((rebuilt == rid).all(), "T-ROWID", "lead %d row_id = unit_id|target_date" % L)
        R.check(not df.duplicated(["unit_id", "target_date"]).any(), "T-UNITTIME", "lead %d (unit, date) unique" % L)
        R.check((df.issue_date == df.target_date - L).all(), "T-ISSUE", "lead %d issue = target - %d" % (L, L))
        gap = (df.feature_end - df.issue_date)
        R.check((gap < 0).all(), "T-FEATEND", "lead %d feature_end < issue on every row (max gap %d days)" % (L, gap.max()))
        y = df.pct_bleached
        R.check(np.isfinite(y).all() and ((y >= 0) & (y <= 100)).all(), "T-RANGE", "lead %d labels finite in [0, 100]" % L)
        num = [n for n in names if want_type[n] == pa.float64() and roles[n] not in ("key_lat", "key_lon", "target")]
        X = df[num].to_numpy("float64")
        R.check(not np.isinf(X).any() and not (np.abs(X[np.isfinite(X)]) >= SENTINEL).any(), "T-FINITE",
                "lead %d: no inf, nothing at the sentinel size (%d numeric columns; NaN cells %d)"
                % (L, len(num), int(np.isnan(X).sum())))
        R.check(df.lat.between(-90, 90).all() and df.lon.between(-180, 180).all()
                and np.isfinite(df[["lat", "lon"]].to_numpy()).all(), "T-UNIT", "lead %d lat/lon finite, in range" % L)
        R.check(set(df.mark) <= {"train", "test"}, "T-MARK", "lead %d marks %s" % (L, sorted(set(df.mark))))
        y0, y1 = census["test_years"]
        td = pd.to_datetime([E0 + dt.timedelta(days=int(x)) for x in df.target_date])
        tr, te = (df.mark == "train").values, (df.mark == "test").values
        R.check((td[tr] < pd.Timestamp(y0, 1, 1)).all(), "T-MARK", "lead %d train rows before %d-01-01" % (L, y0))
        R.check(((td[te] >= pd.Timestamp(y0, 1, 1)) & (td[te] <= pd.Timestamp(y1, 12, 31))).all(), "T-MARK",
                "lead %d test rows inside %d-%d" % (L, y0, y1))
        R.check(((td.year >= y0) == te).all(), "T-MARK", "lead %d mark = test exactly when the year is in the window" % L)
    allu = pd.concat([T[L][["unit_id", "group", "lat", "lon"]] for L in LEADS]).drop_duplicates()
    R.check(not allu.unit_id.duplicated().any(), "T-UNIT", "a unit has one group and one (lat, lon) in every file "
                                                           "(%d units)" % allu.unit_id.nunique())
    base = T[0].set_index("row_id")
    same = ["unit_id", "group", "lat", "lon", "target_date", "mark", "programme"]
    for L in LEADS[1:]:
        d = T[L].set_index("row_id")
        sub = d.index.isin(base.index).all()
        eq = sub and all((d[c] == base.loc[d.index, c]).all() for c in same)
        lab = sub and (d.pct_bleached.to_numpy().tobytes() == base.loc[d.index, "pct_bleached"].to_numpy().tobytes())
        R.check(sub and eq and lab, "T-LEADSET", "lead %d: %d ids in lead 0, same keys, mark, stratum, label bytes"
                % (L, len(d)))
    pc = [c["name"] for c in COLUMNS if c["role"] in ("key_unit", "report_stratum")]
    R.check(not any(c in RESERVED or c.startswith(("arm__", "pre__", "base__")) for c in pc), "T-NAMES",
            "unit and stratum names %s not reserved" % pc)
    return T


# ---------------------------------------------------------------------------------------------------- Part B
def psl(path):
    rows, miss = [], None
    for ln in io.open(path, encoding="utf-8", errors="replace"):
        p = ln.split()
        if len(p) == 13 and p[0].isdigit():
            rows += [(int(p[0]), m, float(x)) for m, x in enumerate(p[1:], 1)]
        elif len(p) == 1:
            try:
                miss = float(p[0])
            except ValueError:
                pass
    d = pd.DataFrame(rows, columns=["yr", "mo", "v"])
    d.loc[(d.v == miss) | (d.v < -900), "v"] = np.nan
    return d


def own_mmm(days, sst):
    dd = days.astype("int64").astype("datetime64[D]")
    yr = dd.astype("datetime64[Y]").astype("int64") + 1970
    mo = dd.astype("datetime64[M]").astype("int64") % 12 + 1
    df = pd.DataFrame({"yr": yr, "mo": mo, "v": sst.astype("float64")})
    if len(df) < 365 or df.yr.nunique() < 10:
        return np.nan
    best = np.nan
    for m, g in df.groupby("mo"):
        if len(g) < 60:
            continue
        means = g.groupby("yr").v.mean()
        if len(means) < 3:
            continue
        b, a = np.polyfit(means.index.values.astype(float), means.values, 1)
        val = a + b * EPOCH_YEAR
        best = val if not np.isfinite(best) or val > best else best
    return best


def own_heat(sst, mmm):
    out = {}
    hs_all = sst.astype("float64") - mmm
    for w in WIN:
        hs = hs_all[-w:]
        out["dhw_%d" % w] = hs[hs >= 1.0].sum() / 7.0
        out["hs_max_%d" % w] = hs.max()
        out["n_above_mmm_%d" % w] = float((hs > 0).sum())
        out["n_above_mmm1_%d" % w] = float((hs >= 1).sum())
        out["cool_%d" % w] = np.maximum(-hs, 0).sum() / 7.0
    return out


def own_cyc(lat, lon, end, tn, la, lo, w):
    out = {}
    r = np.pi / 180
    for days in (30, 90, 365):
        m = (tn >= end - days) & (tn < end)
        if not m.any():
            out["cyc_mindist_%d" % days] = 9999.0
            for rad in (200, 500):
                out["cyc_maxw_%d_%d" % (rad, days)] = 0.0
                out["cyc_n_%d_%d" % (rad, days)] = 0.0
            continue
        p1, p2 = lat * r, la[m].astype("float64") * r
        h = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin((lo[m].astype("float64") - lon) * r / 2) ** 2
        dist = 2 * 6371.0 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))
        out["cyc_mindist_%d" % days] = min(dist.min(), 9999.0)
        for rad in (200, 500):
            k = dist <= rad
            out["cyc_maxw_%d_%d" % (rad, days)] = float(w[m][k].max()) if k.any() else 0.0
            out["cyc_n_%d_%d" % (rad, days)] = float(k.sum())
    return out


def part_b(R, folder, T, man):
    g = int(man["params"]["sst_gap_days"])
    audit = pd.read_parquet(os.path.join(folder, "rows_audit.parquet")).set_index("row_id")
    from netCDF4 import Dataset
    ds = Dataset(IBT)
    lat = np.ma.filled(ds.variables["lat"][:], np.nan).astype("float64").ravel()
    lon = np.ma.filled(ds.variables["lon"][:], np.nan).astype("float64").ravel()
    wnd = np.ma.filled(ds.variables["usa_wind"][:].astype("float64"), np.nan).ravel()
    tim = np.ma.filled(ds.variables["time"][:], np.nan).astype("float64").ravel()
    units = ds.variables["time"].units
    ds.close()
    base = dnum(dt.date.fromisoformat(units.split("since")[-1].strip().split()[0]))
    ok = np.isfinite(lat) & np.isfinite(lon) & np.isfinite(tim)
    tn = (base + np.floor(tim[ok])).astype("int64")
    # track coordinates rounded to float32, as the builder keeps them (legacy coral_extra_drivers.py:73-74, 85)
    la = lat[ok].astype("float32").astype("float64")
    lo = (((lon[ok].astype("float32") + 180) % 360) - 180).astype("float64")
    w = np.where(np.isfinite(wnd[ok]), wnd[ok], 0.0)
    o = np.argsort(tn, kind="stable")
    tn, la, lo, w = tn[o], la[o], lo[o], w[o]
    n34 = psl(NINO)
    clim = n34[(n34.yr >= 1951) & (n34.yr <= 1980)].groupby("mo").v.mean()
    n34["a"] = n34.v - n34.mo.map(clim)
    n34_tab = {(int(a), int(b)): x for a, b, x in zip(n34.yr, n34.mo, n34.a)}
    uk = np.asarray(member_map(COMPACT, "uk.npy"))
    st = np.asarray(member_map(COMPACT, "start.npy"))
    en = np.asarray(member_map(COMPACT, "end.npy"))
    DAY, SST = member_map(COMPACT, "day.npy"), member_map(COMPACT, "sst.npy")

    heat_cols = list(own_heat(np.ones(400, "float32"), 0.0))
    cyc_cols = list(own_cyc(0.0, 0.0, 0, np.zeros(1, "int64"), np.zeros(1), np.zeros(1), np.zeros(1)))
    stats = {"row_leads": 0, "bad_cells": 0, "max_rel": {}, "bound_fail": 0, "first_bad": [], "bad_by_col": {},
             "mmm_max_abs_diff": 0.0}
    sites = {}
    from coral_safe import site_key
    for L in LEADS:
        df = T[L]
        for r in df.itertuples(index=False):
            A = dnum(pd.Timestamp(audit.loc[r.row_id, "anchor_date"]).date())
            C = A - L
            if not (C - g - 1 <= r.feature_end < r.issue_date and C <= r.issue_date):
                stats["bound_fail"] += 1
            key = int(site_key(r.lat, r.lon))
            if key not in sites:
                k = int(np.searchsorted(uk, key))
                if k >= len(uk) or uk[k] != key:
                    raise SystemExit("no SST series for %s" % r.row_id)
                sites[key] = (np.asarray(DAY[int(st[k]):int(en[k])]).astype("int64"), int(st[k]))
            days, a0 = sites[key]
            j = int(np.searchsorted(days, C - g, side="left"))       # strictly before C - g
            sst = np.asarray(SST[a0:a0 + j])
            mmm = own_mmm(days[:j], sst)
            mmm_diff = abs(mmm - r.ctx_mmm) if np.isfinite(mmm) else np.inf
            stats["mmm_max_abs_diff"] = max(stats["mmm_max_abs_diff"], float(mmm_diff))
            if not mmm_diff <= MMM_ATOL:
                stats["bad_cells"] += 1
                stats["bad_by_col"]["ctx_mmm"] = stats["bad_by_col"].get("ctx_mmm", 0) + 1
            # heat columns from the SST cut at C - g, against the table's own MMM (checked just above), so that
            # float32-vs-float64 mean noise does not hide or fake a window difference
            want = own_heat(sst, float(r.ctx_mmm))
            want.update(own_cyc(float(r.lat), float(r.lon), C - g, tn, la, lo, w))
            cd = E0 + dt.timedelta(days=C)
            for k_ in (3, 6, 9):
                mm = cd.year * 12 + cd.month - 1 - k_
                want["nino34a_lag%d" % k_] = n34_tab.get((mm // 12, mm % 12 + 1), np.nan)
            doy = cd.timetuple().tm_yday
            want["ctx_month"] = float(cd.month)
            want["ctx_doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
            want["ctx_doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
            want["ctx_abslat"] = abs(float(r.lat))
            for c, x in want.items():
                y = getattr(r, c)
                exact = c.startswith(("n_above", "cyc_n_", "cyc_maxw", "ctx_month"))
                if np.isnan(x) and np.isnan(y):
                    good, rel = True, 0.0
                else:
                    diff = abs(x - y)
                    rel = diff / max(abs(x), abs(y), 1e-300)
                    rt = MINDIST_RTOL if c.startswith("cyc_mindist") else RTOL
                    good = (diff == 0) if exact else (diff <= ATOL + rt * max(abs(x), abs(y)))
                stats["max_rel"][c] = max(stats["max_rel"].get(c, 0.0), float(rel))
                if not good:
                    stats["bad_cells"] += 1
                    stats["bad_by_col"][c] = stats["bad_by_col"].get(c, 0) + 1
                    if len(stats["first_bad"]) < 10:
                        stats["first_bad"].append((r.row_id, L, c, float(x), float(y)))
            stats["row_leads"] += 1
        guard(2.5, "check_tables part B lead %d" % L)
    n_cols = len(heat_cols) + len(cyc_cols) + 3 + 5
    R.check(stats["bound_fail"] == 0, "LOOKAHEAD-BOUND", "C - g - 1 <= feature_end < issue and C <= issue on %d "
                                                         "row-leads (fails %d)" % (stats["row_leads"], stats["bound_fail"]))
    worst = max(stats["max_rel"], key=stats["max_rel"].get)
    R.check(stats["bad_cells"] == 0, "LOOKAHEAD-RECOMPUTE",
            "%d row-leads x %d columns recomputed from data cut at C - g (SST, cyclones) / C (nino34a): %d cells "
            "differ; max relative diff %.3g (%s)" % (stats["row_leads"], n_cols, stats["bad_cells"],
                                                     stats["max_rel"][worst], worst))
    print("    MMM max |own - table| %.3g C (allowed %.0e); cells differing by column: %s"
          % (stats["mmm_max_abs_diff"], MMM_ATOL, stats["bad_by_col"] or "none"))
    for b in stats["first_bad"]:
        print("    differs:", b)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="tiny")
    ap.add_argument("--negative-control", action="store_true",
                    help="recompute with the cut one day LATER (g - 1); the check passes only if part B then fails")
    ap.add_argument("--visits-dir", required=True,
                    help="sensitivity copy: the folder holding visits_census.json and the <build>/ folder")
    A = ap.parse_args()
    global DATA
    vd = os.path.abspath(A.visits_dir)
    if not vd.lower().startswith(r"d:\treeroute\analysis\coral_sens_2017_2020".lower()):
        raise SystemExit("refused: --visits-dir must be under D:\\treeroute\\analysis\\coral_sens_2017_2020")
    DATA = vd
    folder = os.path.join(DATA, A.build)
    man = json.load(open(os.path.join(folder, "build_manifest.json")))
    census = json.load(open(os.path.join(DATA, "visits_census.json")))
    R = Report()
    if A.negative_control:
        man["params"]["sst_gap_days"] = int(man["params"]["sst_gap_days"]) - 1
        T = part_a(Report(), folder, census)
        st = part_b(Report(), folder, T, man)
        print("NEGATIVE CONTROL: %d of %d row-leads x columns differ with a cut one day later -> %s"
              % (st["bad_cells"], st["row_leads"], "PASS (the checker sees a one-day look-ahead)"
                 if st["bad_cells"] > 0 else "FAIL (the checker is blind)"))
        return 0 if st["bad_cells"] > 0 else 1
    print("Part A: table contract", flush=True)
    T = part_a(R, folder, census)
    print("Part B: no feature input after the issue date (independent recompute)", flush=True)
    st = part_b(R, folder, T, man)
    out = {"build": A.build, "passed": not R.fail, "n_ok": len(R.ok), "fail": R.fail, "ok": R.ok,
           "lookahead": {k: v for k, v in st.items() if k != "first_bad"}, "first_bad": st["first_bad"]}
    with open(os.path.join(folder, "check_report.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print("RESULT: %s (%d checks ok, %d failed)" % ("PASS" if not R.fail else "FAIL", len(R.ok), len(R.fail)))
    return 0 if not R.fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
