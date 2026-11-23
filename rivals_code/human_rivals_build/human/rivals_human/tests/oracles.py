"""Hand computations the tests compare the tool against (SPEC_HUMAN.txt section 7). Written from the spec text
only, never from the tool's code; each one is itself checked (test_oracles.py) against a saved engine column or an
exact closed form before any tool test leans on it.

  persistence_parity      1.10: nowcast-style persistence / damped persistence rebuilt from the export at a lead
                          L >= 1 with the LIVE engine's metrics functions (MET:436, :447, :461, :534); must equal the
                          run's saved base__persistence / base__damped_persistence byte for byte.
  last_visit              1.10 / Q23: the label of the latest earlier visit of the same site strictly before the
                          issue day (TLAD:390-396 last_label_before).
  dhw_baa                 2: CRW DHW over d*-83..d* (HotSpot >= 1 only, / 7) and the 5-level BAA, BAA7d = max over
                          d*-6..d*; a missing day -> NaN.
  bilinear                4: bilinear interpolation on a regular grid (any axis order, longitude wrap at 360).
  forest_mask, vt0007_quantity  3: forest(T) and the quantity scaling with the pixel cap and the cell sum.
  isotonic_l1             1.6 L1 print: weighted-median pool-adjacent-violators.
  f5_shrunk               1.6 F5: per-unit OLS shrunk toward the pooled F3 line with K rows.
"""

import math
from types import SimpleNamespace
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


# ===================================================================================================== persistence
def season_key_grid(steps: np.ndarray, steps_per_year: int) -> np.ndarray:
    """Grid step index = year x P + position (1..P); the season key is the position (engine D28 form)."""
    s = np.asarray(steps, dtype=np.int64)
    return (s - 1) % int(steps_per_year) + 1


def read_export_part(lead_dir, part: str, columns: Optional[Sequence[str]] = None) -> pd.DataFrame:
    import pyarrow.parquet as pq
    files = sorted((lead_dir / part).glob("*.parquet"))
    assert files, "no %s/*.parquet in %s" % (part, lead_dir)
    return pd.concat([pq.read_table(str(f), columns=list(columns) if columns else None).to_pandas() for f in files],
                     ignore_index=True)


def unit_normal_table(frames: Sequence[pd.DataFrame], steps_per_year: int, column: str = "nfit__identity"
                      ) -> Dict[Tuple[str, int], float]:
    """{(unit, season key): normal} from rows that carry the fit-cut identity normal of their own step. Refuses
    (assert) a (unit, key) with two different values: the normal is one number per unit and key at one cut."""
    out: Dict[Tuple[str, int], float] = {}
    for f in frames:
        keys = season_key_grid(f["time"].to_numpy(), steps_per_year)
        for u, k, v in zip(f["unit"].astype(str).tolist(), keys.tolist(), f[column].to_numpy(np.float64).tolist()):
            old = out.get((u, k))
            assert old is None or old == v or (math.isnan(old) and math.isnan(v)), \
                "two fit-cut normals for unit %s key %d: %r vs %r" % (u, k, old, v)
            out[(u, k)] = v
    return out


def unit_histories(frame: pd.DataFrame, cut: int, steps_per_year: int, units: Optional[Sequence[str]] = None):
    """Duck-typed UnitHistory objects (unit_id, times, season_keys, y, cut; MET:306-320) from labelled rows at or
    before the cut, times ascending, one label per time."""
    f = frame[frame["time"].to_numpy(np.int64) <= int(cut)]
    f = f[np.isfinite(f["y"].to_numpy(np.float64))]
    f = f.drop_duplicates(subset=["unit", "time"]).sort_values(["unit", "time"], kind="mergesort")
    out = {}
    want = None if units is None else set(str(u) for u in units)
    for u, g in f.groupby(f["unit"].astype(str), sort=True):
        if want is not None and u not in want:
            continue
        t = g["time"].to_numpy(np.int64)
        out[u] = SimpleNamespace(unit_id=u, times=t, season_keys=season_key_grid(t, steps_per_year),
                                 y=g["y"].to_numpy(np.float64), cut=int(cut))
    return out


def label_table(export_dir0, saved_test0: pd.DataFrame) -> Dict[Tuple[str, int], float]:
    """{(unit, step): y} from every lead-0 export train row (float64 y) and the run's saved lead-0 test rows (y; a
    test reads them only after the tool's lock and score)."""
    tr = read_export_part(export_dir0, "train", ["unit", "time", "y"])
    lab = pd.concat([tr, saved_test0[["unit", "time", "y"]]], ignore_index=True)
    lab = lab[np.isfinite(lab["y"].to_numpy(np.float64))]
    out: Dict[Tuple[str, int], float] = {}
    for u, t, y in zip(lab["unit"].astype(str).tolist(), lab["time"].astype(np.int64).tolist(),
                       lab["y"].to_numpy(np.float64).tolist()):
        old = out.get((u, t))
        assert old is None or old == y, "two labels for (%s, %d)" % (u, t)
        out[(u, t)] = y
    return out


def persistence_parity(run_folder, export_dirs: Mapping[int, object], lead: int, offset: int,
                       steps_per_year: int, legal: Tuple[float, float], fit_cut: int,
                       history_source: str = "lead0_refit",
                       labels: Optional[Mapping[Tuple[str, int], float]] = None) -> pd.DataFrame:
    """The 1.10 reference rows at a lead (L >= 1: the parity form; L = 0: the nowcast rows), built from the export
    only (no saved test label):
    persistence = clip(y_issue); damped = normal(t) + phi x (y_issue - normal(issue step)), where y_issue is the label
    at the T2 step (labels given: the float64 label of (unit, T2 step); labels None: the export's x__hist_last_1, which
    the export stores as float32), normal(t) = nfit__identity of the row, normal(issue step) = the unit's fit-cut
    identity normal at the season key of the T2 step, phi per unit on the unit's labels at or before the lead's fit
    cut with the gap of the T2 step. history_source: 'lead0_refit' (lead-0 refit rows cut at the lead's fit cut; the
    spec's nowcast recipe) or 'lead_refit' (the lead's own refit rows)."""
    from treeroute.report import metrics as MET

    L = int(lead)
    d = export_dirs[L]
    test = read_export_part(d, "test", ["unit", "group", "time", "issue", "lead", "x__hist_last_1", "nfit__identity"])
    train_L = read_export_part(d, "train", ["unit", "time", "r_refit", "y", "nfit__identity"])
    normals = unit_normal_table([train_L, test], steps_per_year)
    gap = (1 if L == 0 else L) + int(offset)          # latest_label_step(t, L) = t - 1 at the nowcast, t - L at L
    label_step = test["time"].to_numpy(np.int64) - gap
    lk = season_key_grid(label_step, steps_per_year)
    units = test["unit"].astype(str).tolist()
    normal_issue = np.array([normals[(u, int(k))] for u, k in zip(units, lk.tolist())], dtype=np.float64)
    if history_source == "lead0_refit":
        src = read_export_part(export_dirs[0], "train", ["unit", "time", "r_refit", "y"])
    else:
        src = train_L
    src = src[src["r_refit"].to_numpy(bool)]
    hist = unit_histories(src, fit_cut, steps_per_year, units=sorted(set(units)))
    same = MET.shares_season_key(gap, int(steps_per_year))
    phi = MET.damped_persistence_phi(hist, gap, same)
    if labels is None:
        y_issue = test["x__hist_last_1"].to_numpy(np.float64)
    else:
        y_issue = np.array([labels.get((u, int(s)), np.nan) for u, s in zip(units, label_step.tolist())],
                           dtype=np.float64)
    phi_rows = np.array([phi[u] for u in units], dtype=np.float64)
    out = test[["unit", "time", "lead"]].copy()
    out["persistence"] = MET.baseline_persistence(y_issue, legal)
    out["damped_persistence"] = MET.baseline_damped_persistence(test["nfit__identity"].to_numpy(np.float64),
                                                                normal_issue, y_issue, phi_rows, legal)
    return out


def last_visit(labels: pd.DataFrame, rows: pd.DataFrame, legal: Tuple[float, float],
               site_of: Optional[Mapping[str, str]] = None) -> np.ndarray:
    """For each row (unit, issue): the label of the latest visit of the same site strictly before the issue day.
    The site key: site_of[unit] when given (a package whose unit id is the visit row id and whose site is another
    column, as the engine's table toy), else the part of the unit id before '|' (the whole id when there is none;
    the coral export's 'site|date' units). NaN when there is none. labels: unit, time, y (every labelled visit).
    Clipped as baseline_persistence (NaN kept)."""
    from treeroute.report import metrics as MET

    def site(u: str) -> str:
        return str(site_of[u]) if site_of is not None else str(u).split("|")[0]

    lab = labels[np.isfinite(labels["y"].to_numpy(np.float64))].copy()
    lab["site"] = [site(u) for u in lab["unit"].astype(str).tolist()]
    lab = lab.drop_duplicates(subset=["site", "time"]).sort_values(["site", "time"], kind="mergesort")
    by_site = {s: (g["time"].to_numpy(np.int64), g["y"].to_numpy(np.float64)) for s, g in lab.groupby("site")}
    out = np.full(len(rows), np.nan)
    sites = [site(u) for u in rows["unit"].astype(str).tolist()]
    issues = rows["issue"].to_numpy(np.int64)
    for i, (s, iss) in enumerate(zip(sites, issues.tolist())):
        if s not in by_site:
            continue
        t, y = by_site[s]
        j = int(np.searchsorted(t, iss, side="left")) - 1
        if j >= 0:
            out[i] = y[j]
    return MET.baseline_persistence(out, legal)


# ===================================================================================================== coral rule
def baa_level(hs: float, dhw: float) -> int:
    """The 5-level BAA scale of 2016-19 (NOAA levels 5-7 merged into 4), applied in order."""
    if hs <= 0:
        return 0
    if hs < 1:
        return 1
    if dhw < 4:
        return 2
    if dhw < 8:
        return 3
    return 4


def dhw_at(sst_by_day: Mapping[int, float], mmm: float, d: int) -> float:
    """DHW(d) = sum over d-83..d of HotSpot where HotSpot >= 1, divided by 7; NaN when a day is missing."""
    total = 0.0
    for day in range(d - 83, d + 1):
        v = sst_by_day.get(day)
        if v is None or not math.isfinite(v):
            return float("nan")
        hs = (round(v * 100.0) - round(mmm * 100.0)) / 100.0   # NOAA's 2-decimal arithmetic (SST and MMM in 0.01)
        if hs >= 1.0:
            total += hs
    return total / 7.0


def dhw_baa(sst_by_day: Mapping[int, float], mmm: float, d_star: int) -> Tuple[float, float]:
    """(DHW(d*), BAA7d(d*)): BAA7d = max over d*-6..d* of the day's level (from that day's HotSpot and DHW)."""
    dhw = dhw_at(sst_by_day, mmm, d_star)
    levels = []
    for day in range(d_star - 6, d_star + 1):
        v = sst_by_day.get(day)
        dd = dhw_at(sst_by_day, mmm, day)
        if v is None or not math.isfinite(v) or not math.isfinite(dd):
            return dhw, float("nan")
        levels.append(baa_level((round(v * 100.0) - round(mmm * 100.0)) / 100.0, dd))
    return dhw, float(max(levels))


# ===================================================================================================== PM2.5 readers
def bilinear(lat_axis: np.ndarray, lon_axis: np.ndarray, field: np.ndarray, lat: float, lon: float,
             lon_period: Optional[float] = 360.0) -> float:
    """Bilinear interpolation at (lat, lon) on a regular grid whose axes may run either way; longitudes wrap with
    the period (the cell between the last and the first column is used). Written index by index (no library)."""
    la = np.asarray(lat_axis, dtype=np.float64)
    lo = np.asarray(lon_axis, dtype=np.float64)
    f = np.asarray(field, dtype=np.float64)
    if la[0] > la[-1]:                       # north -> south: flip to ascending
        la, f = la[::-1], f[::-1, :]
    i = int(np.searchsorted(la, lat, side="right")) - 1
    i = min(max(i, 0), la.size - 2)
    wy = (lat - la[i]) / (la[i + 1] - la[i])
    x = float(lon)
    if lon_period is not None:
        lo0 = lo[0]
        x = lo0 + ((x - lo0) % lon_period)
        lo_ext = np.append(lo, lo[0] + lon_period)
        f_ext = np.concatenate([f, f[:, :1]], axis=1)
    else:
        lo_ext, f_ext = lo, f
    j = int(np.searchsorted(lo_ext, x, side="right")) - 1
    j = min(max(j, 0), lo_ext.size - 2)
    wx = (x - lo_ext[j]) / (lo_ext[j + 1] - lo_ext[j])
    v00, v01 = f_ext[i, j], f_ext[i, j + 1]
    v10, v11 = f_ext[i + 1, j], f_ext[i + 1, j + 1]
    return float((1 - wy) * ((1 - wx) * v00 + wx * v01) + wy * ((1 - wx) * v10 + wx * v11))


# ===================================================================================================== defo rule
def forest_mask(treecover2000: np.ndarray, datamask: np.ndarray, lossyear: np.ndarray, T: int) -> np.ndarray:
    """forest(T) = treecover2000 >= 30 AND datamask land (1) AND NOT (1 <= lossyear <= T - 2000)."""
    ly = np.asarray(lossyear, dtype=np.int64)
    lost = (ly >= 1) & (ly <= int(T) - 2000)
    return (np.asarray(treecover2000) >= 30) & (np.asarray(datamask) == 1) & ~lost


def vt0007_quantity(p: np.ndarray, quantity: float, iters: int = 200) -> np.ndarray:
    """Pixel expected loss min(1, s p) with s chosen so the total equals the quantity (both 3 rules: 'scaled so the
    group's total equals Q' and 'each pixel capped at 1'), found by bisection on s (an algorithm independent of the
    tool's sorted water-filling). Q above the number of pixels with p > 0: every such pixel is 1."""
    p = np.asarray(p, dtype=np.float64)
    q = float(quantity)
    if q <= 0 or not (p > 0).any():
        return np.zeros_like(p)
    if q >= float((p > 0).sum()):
        return np.where(p > 0, 1.0, 0.0)
    lo, hi = 0.0, 1.0
    while float(np.minimum(1.0, hi * p).sum()) < q:
        hi *= 2.0
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if float(np.minimum(1.0, mid * p).sum()) < q:
            lo = mid
        else:
            hi = mid
    return np.minimum(1.0, hi * p)


def cell_value(expected: np.ndarray, cell_of_pixel: np.ndarray, forest2000_px: Mapping[int, float]) -> Dict[int, float]:
    """x__vt0007 per cell = sum of expected loss pixels in the cell / forest2000_px of the cell."""
    out: Dict[int, float] = {}
    e = np.asarray(expected, dtype=np.float64).ravel()
    c = np.asarray(cell_of_pixel).ravel()
    for cell in np.unique(c).tolist():
        if cell < 0:
            continue
        den = float(forest2000_px[cell])
        out[int(cell)] = float(e[c == cell].sum()) / den if den > 0 else float("nan")
    return out


# ===================================================================================================== maps
def pav_l1(x: np.ndarray, y: np.ndarray, increasing: bool = True) -> np.ndarray:
    """L1 isotonic regression by pool-adjacent-violators with the block median (lower median of each block),
    fitted values in the input order. Ties in x are pooled first (one block per distinct x)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    sign = 1.0 if increasing else -1.0
    order = np.argsort(x, kind="mergesort")
    xs, ys = x[order], sign * y[order]
    blocks: List[List[float]] = []
    bx: List[float] = []
    for xi, yi in zip(xs.tolist(), ys.tolist()):
        if bx and xi == bx[-1]:
            blocks[-1].append(yi)
        else:
            blocks.append([yi])
            bx.append(xi)

    def med(vals: List[float]) -> float:
        v = sorted(vals)
        return v[(len(v) - 1) // 2]

    stack: List[List[float]] = []
    sizes: List[int] = []
    for b in blocks:
        stack.append(list(b))
        sizes.append(len(b))
        while len(stack) > 1 and med(stack[-2]) > med(stack[-1]):
            top = stack.pop()
            sizes.pop()
            stack[-1].extend(top)
            sizes[-1] = len(stack[-1])
    fitted_sorted = []
    for b in stack:
        m = med(b)
        fitted_sorted.extend([m] * len(b))
    out = np.empty_like(y)
    out[order] = sign * np.asarray(fitted_sorted)
    return out


def ols(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    """(intercept, slope) of y on x by least squares (closed form)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    xm, ym = x.mean(), y.mean()
    sxx = float(((x - xm) ** 2).sum())
    b = float(((x - xm) * (y - ym)).sum()) / sxx if sxx > 0 else 0.0
    return float(ym - b * xm), b


def f5_shrunk(xa: np.ndarray, r: np.ndarray, units: np.ndarray, k: int = 10, min_rows: int = 3
              ) -> Tuple[Dict[str, Tuple[float, float]], Tuple[float, float], List[str]]:
    """F5 by hand: pooled (a, b) = OLS of r on xa (r = link(y) - z0, xa = x - xbar); per unit with n_u >= min_rows:
    a_u* = (n_u a_u + K a) / (n_u + K), b_u* likewise; a unit below min_rows takes the pooled line (listed)."""
    a, b = ols(xa, r)
    out: Dict[str, Tuple[float, float]] = {}
    fallback: List[str] = []
    u = np.asarray(units).astype(str)
    for name in sorted(set(u.tolist())):
        m = u == name
        n = int(m.sum())
        if n < min_rows:
            out[name] = (a, b)
            fallback.append(name)
            continue
        au, bu = ols(xa[m], r[m])
        out[name] = ((n * au + k * a) / (n + k), (n * bu + k * b) / (n + k))
    return out, (a, b), fallback


def xbar_table(x: np.ndarray, units: np.ndarray, season: np.ndarray, min_rows: int = 3) -> np.ndarray:
    """1.6 xbar per row: the unit x season-key mean of x over the given rows; a (unit, key) with fewer than
    min_rows rows takes the pooled key mean."""
    f = pd.DataFrame({"x": np.asarray(x, np.float64), "u": np.asarray(units).astype(str),
                      "k": np.asarray(season, np.int64)})
    cell = f.groupby(["u", "k"])["x"].agg(["mean", "size"])
    pooled = f.groupby("k")["x"].mean()
    out = np.empty(len(f))
    for i, (u, k) in enumerate(zip(f["u"].tolist(), f["k"].tolist())):
        m, n = cell.loc[(u, k)]
        out[i] = m if n >= min_rows else pooled.loc[k]
    return out
