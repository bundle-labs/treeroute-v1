"""rescore_B.py -- POST HOC re-score of the MERRA-2 PM2.5 human rivals with the GMAO PM2.5 formula.

Owner ruling AM1 (2026-10-27); spec D:/treeroute/analysis/paper_posthoc/merra2_formula/SPEC.md. Implementer B
(INDEPENDENT PATH): no tool pipeline function is imported. The MERRA-2 files are read with h5py, the unit-centre
bilinear interpolation, the candidate map families F0-F5, the pick rule, the guard (N2) and the refit are written
here from reading the tool's code:
  adapters/pm25_reanalysis.py           (unchanged since 2026-10-23, before the index tables were built)
  rivals_human/board.py                 (unchanged since 2026-10-22)
  rivals_human/maps.py                  BASELINE copy _moved/20261025T194657Z_partB_baseline/rivals_human/maps.py
                                        (the live maps.py was edited 2026-10-25 22:51 local, after the PM2.5 board ran
                                        at 18:07 local; the edit is F6 / weighted-isotonic only)
  rivals_human/slim.py, config.py       (unchanged since 2026-10-22)
  rivals/harness.py, rivals/models.py   (common harness: comparator, clip, links)
Only the final contrast/verdict cross-check imports the ENGINE's metric functions read-only
(treeroute/report/metrics.py: mae, corr2, calibration_ratio, contrast_tag), as merra2_runaway/sens_B.py does.

Run:  py -3.9 -I "D:/treeroute/analysis/paper_posthoc/merra2_formula/B/rescore_B.py"

Writes ONLY into its own folder: result_B.json and preds_<rival>_<variant>.parquet. Never names a cause for any
forecast; numbers only. Post hoc: the locked verdicts never change.
"""
import sys

sys.dont_write_bytecode = True          # set before ANY import of engine code: no __pycache__ in locked folders

import os                                # noqa: E402

# The tool pins the BLAS/OpenMP pools to 8 threads before numpy loads (rivals_human/cli.py PIN_VARS / PIN_VALUE;
# board human_board.json threadpool_info). np.dot's partial sums depend on the thread count, so the same pin is
# needed to reproduce the board's floats bit for bit (the tool's fixed setting, like a fixed random_state).
PIN_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
PIN_VALUE = "8"
if "numpy" in sys.modules:
    raise SystemExit("REFUSED: numpy imported before the thread pins")
for _v in PIN_VARS:
    os.environ[_v] = PIN_VALUE

import hashlib                           # noqa: E402
import json                              # noqa: E402
import math                              # noqa: E402
import re                                # noqa: E402
import time                              # noqa: E402
from datetime import datetime, timedelta  # noqa: E402
from pathlib import Path                 # noqa: E402

import h5py                              # noqa: E402
import numpy as np                       # noqa: E402
import pandas as pd                      # noqa: E402
import pyarrow as pa                     # noqa: E402
import pyarrow.dataset as pads           # noqa: E402
import pyarrow.parquet as pq             # noqa: E402

T0 = time.time()

# ------------------------------------------------------------------------------------------------ paths (read only)
OUT_DIR = Path(r"D:/treeroute/analysis/paper_posthoc/merra2_formula/B")
BOARD = Path(r"D:/treeroute/rivals_human/pm25/20261007_74e67609")
LEAD0 = BOARD / "lead_0"
SLIM = BOARD / "slim" / "lead_0"
INDEX_ROOT = Path(r"D:/treeroute/human_index/pm25/20261007_74e67609")
PRODUCT_DIR = Path(r"D:/pm25_products/merra2")
STATIC = Path(r"C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/datasets/pm25/data/static/part-0.parquet")
RUN = Path(r"D:/treeroute/runs/pm25/headline/20261007_74e67609")
TABLE = Path(r"D:/treeroute/rivals_table/20261025T162302876402Z/RIVALS_TABLE.csv")
ENGINE = Path(r"C:/Users/moh the ghost/Desktop/data set for reserch paper/engine")
TOOL_FILES_READ = [  # code read to write this script (hashed for provenance; never imported)
    Path(r"D:/treeroute/human_rivals_build/human/adapters/pm25_reanalysis.py"),
    Path(r"D:/treeroute/human_rivals_build/human/rivals_human/board.py"),
    Path(r"D:/treeroute/human_rivals_build/_moved/20261025T194657Z_partB_baseline/rivals_human/maps.py"),
    Path(r"D:/treeroute/human_rivals_build/human/rivals_human/maps.py"),
    Path(r"D:/treeroute/human_rivals_build/human/rivals_human/slim.py"),
    Path(r"D:/treeroute/human_rivals_build/human/rivals_human/config.py"),
    Path(r"D:/treeroute/human_rivals_build/human/registry/pm25.yaml"),
    Path(r"D:/treeroute/rivals_build/rivals/harness.py"),
    Path(r"D:/treeroute/rivals_build/rivals/models.py"),
]

# ------------------------------------------------------------------------------------------------ the formulas
COMPONENTS = ("DUSMASS25", "SSSMASS25", "BCSMASS", "OCSMASS", "SO4SMASS")     # registry dict order (sum order)
FORMULAS = {
    "locked": {"DUSMASS25": 1.0, "SSSMASS25": 1.0, "BCSMASS": 1.0, "OCSMASS": 1.4, "SO4SMASS": 1.375},
    "oc1": {"DUSMASS25": 1.0, "SSSMASS25": 1.0, "BCSMASS": 1.0, "OCSMASS": 1.0, "SO4SMASS": 1.375},
    "oc1_so4gmao": {"DUSMASS25": 1.0, "SSSMASS25": 1.0, "BCSMASS": 1.0, "OCSMASS": 1.0,
                    "SO4SMASS": 132.14 / 96.06},
}
SCALE = 1.0e9                      # kg m-3 -> ug m-3 (registry options.scale)
UNITS_ATTR = "kg m-3"
FILE_RX = re.compile(r"aer_(\d{4})(\d{2})\.nc")
GRID_TOL = 1e-6
MONTHS = 12

# ------------------------------------------------------------------------------------------------ the rivals
RIVALS = {
    "merra2_lag1": {"month_offset": -1, "placebo_shift_years": 0, "tier": "P"},
    "merra2_same": {"month_offset": 0, "placebo_shift_years": 0, "tier": "A"},
    "merra2_lag1_placebo": {"month_offset": -1, "placebo_shift_years": 4, "tier": "X", "placebo_of": "merra2_lag1"},
}
FAMILIES = ("F0", "F1", "F2", "F3", "F4", "F5")    # registry `families` of merra2_lag1 / merra2_same

# ------------------------------------------------------------------------------------------------ tool constants
SHRINK_K = 10            # config.py:129
MIN_FIT_ROWS = 100       # config.py:130
MIN_FIT_GROUPS = 3       # config.py:131
MIN_UNIT_ROWS = 3        # config.py:132
MIN_GROUP_TEST_ROWS = 10  # config.py:133
THRESH = 1000.0          # spec step 4
YAKUTIA = ("yakutia_larch_3553_2232", 2021, 8)
VERDICT_WORDS = {"helps": "BEATS", "hurts": "LOSES", "does_not_help_equivalent": "EQUIVALENT",
                 "cannot_tell": "CANNOT TELL", "identical": "IDENTICAL"}
TIME_SHIFT = 20          # key = unit_code << 20 | time  (time < 2^20 checked)

INPUTS = {}              # path -> sha256 of every input file read


def log(msg):
    print("[%7.1f s] %s" % (time.time() - T0, msg), flush=True)


def refuse(msg):
    raise SystemExit("REFUSED (STOP): " + msg)


def sha256(path):
    path = Path(path)
    key = str(path)
    if key in INPUTS:
        return INPUTS[key]
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    INPUTS[key] = h.hexdigest()
    return INPUTS[key]


def read_json(path):
    sha256(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_parquet(path, columns=None, **kw):
    sha256(path)
    return pq.read_table(str(path), columns=columns, **kw).to_pandas()


def step_ym(step):
    s = int(step)
    return (s - 1) // MONTHS, (s - 1) % MONTHS + 1


def ym_step(year, month):
    return int(year) * MONTHS + int(month)


def nan_max_abs(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    na, nb = np.isnan(a), np.isnan(b)
    ok = ~na & ~nb
    return {"nan_pattern_equal": bool(np.array_equal(na, nb)),
            "max_abs_diff": float(np.max(np.abs(a[ok] - b[ok]))) if ok.any() else 0.0,
            "max_rel_diff": float(np.max(np.abs(a[ok] - b[ok]) / np.maximum(np.abs(b[ok]), 1e-300)))
            if ok.any() else 0.0,
            "rows_compared": int(ok.sum()),
            "bit_exact": bool(np.array_equal(na, nb) and a[ok].tobytes() == b[ok].tobytes())}


# ==================================================================================================== 1. the product
class Merra2(object):
    """Own reader of the 252 monthly MERRA-2 aerosol files (h5py), the regular-grid orientation and the bilinear
    unit-centre interpolation of adapters/pm25_reanalysis.py (Grid.weights / Grid.interpolate)."""

    def __init__(self, folder):
        self.files = {}
        for p in sorted(Path(folder).iterdir()):
            m = FILE_RX.fullmatch(p.name)
            if m:
                self.files[(int(m.group(1)), int(m.group(2)))] = p
        if len(self.files) != 252:
            refuse("expected 252 MERRA-2 files, found %d" % len(self.files))
        self.grid = None
        self.masked_cells = {}

    @staticmethod
    def _month_of(f):
        t = f["time"]
        units = t.attrs["units"]
        units = units.decode() if isinstance(units, bytes) else str(units)
        m = re.fullmatch(r"minutes since (\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})", units.strip())
        if not m:
            refuse("unparsed time units %r" % units)
        base = datetime(*[int(v) for v in m.groups()])
        vals = np.atleast_1d(t[:])
        return [((base + timedelta(minutes=float(v))).year, (base + timedelta(minutes=float(v))).month) for v in vals]

    def _set_grid(self, lat, lon):
        lat = np.asarray(lat, dtype=np.float64)
        lon = np.asarray(lon, dtype=np.float64)
        flip = bool(lat.size > 1 and lat[1] < lat[0])
        lat_a = lat[::-1].copy() if flip else lat.copy()
        order = np.argsort(np.mod(lon, 360.0), kind="stable")
        lon_a = np.mod(lon, 360.0)[order]
        for name, ax in (("lat", lat_a), ("lon", lon_a)):
            d = np.diff(ax)
            if not (np.abs(d - d[0]) <= GRID_TOL).all() or d[0] <= 0:
                refuse("product %s axis is not regular ascending" % name)
        g = {"flip": flip, "lat": lat_a, "lon": lon_a, "order": order,
             "dlat": float((lat_a[-1] - lat_a[0]) / (lat_a.size - 1)),
             "dlon": float((lon_a[-1] - lon_a[0]) / (lon_a.size - 1))}
        if abs(lon_a.size * g["dlon"] - 360.0) > 1e-4:
            refuse("longitude axis does not close the globe")
        if self.grid is None:
            self.grid = g
        elif not (np.array_equal(g["lat"], self.grid["lat"]) and np.array_equal(g["lon"], self.grid["lon"])):
            refuse("a product file is on another grid")

    def fields(self, ym, formulas):
        """{formula: (lat, lon) field in ug m-3 on ascending axes}; masked/fill values -> NaN (as netCDF4's
        auto-mask then np.ma.filled(nan)). The sum is taken in the registry order, weight x component, then x scale."""
        p = self.files[ym]
        sha256(p)
        with h5py.File(str(p), "r") as f:
            self._set_grid(f["lat"][:], f["lon"][:])
            months = self._month_of(f)
            if months != [ym]:
                refuse("file %s holds months %s" % (p.name, months))
            comp = {}
            for name in COMPONENTS:
                d = f[name]
                u = d.attrs.get("units")
                u = u.decode() if isinstance(u, bytes) else str(u)
                if u.replace("**", "").replace("^", "").replace(" ", "") != UNITS_ATTR.replace(" ", ""):
                    refuse("%s units %r" % (name, u))
                a = d[0] if d.ndim == 3 else d[:]
                a = np.asarray(a)
                bad = ~np.isfinite(a)
                for attr in ("_FillValue", "missing_value"):
                    if attr in d.attrs:
                        for fv in np.atleast_1d(d.attrs[attr]):
                            bad |= (a == np.asarray(fv, dtype=a.dtype))
                if "valid_range" in d.attrs:
                    vr = np.asarray(d.attrs["valid_range"], dtype=a.dtype)
                    bad |= (a < vr[0]) | (a > vr[1])
                v = a.astype(np.float64)
                v[bad] = np.nan
                self.masked_cells[name] = self.masked_cells.get(name, 0) + int(bad.sum())
                comp[name] = np.squeeze(v)
        out = {}
        for fname, w in formulas.items():
            total = None
            for name in COMPONENTS:                       # adapter _field: total = w*a, then total + w*a
                total = float(w[name]) * comp[name] if total is None else total + float(w[name]) * comp[name]
            fld = total * float(SCALE)
            if self.grid["flip"]:
                fld = fld[::-1, :]
            out[fname] = fld[:, self.grid["order"]]
        return out

    def weights(self, qlat, qlon):
        g = self.grid
        qlat = np.asarray(qlat, dtype=np.float64)
        qlon = np.asarray(qlon, dtype=np.float64)
        fi = (qlat - g["lat"][0]) / g["dlat"]
        i0 = np.clip(np.floor(fi).astype(np.int64), 0, g["lat"].size - 2)
        wi = np.clip(fi - i0, 0.0, 1.0)
        fj = np.mod(qlon - g["lon"][0], 360.0) / g["dlon"]
        j0 = np.floor(fj).astype(np.int64) % g["lon"].size
        wj = fj - np.floor(fj)
        j1 = (j0 + 1) % g["lon"].size
        return {"i0": i0, "i1": i0 + 1, "j0": j0, "j1": j1, "wi": wi, "wj": wj}

    @staticmethod
    def interpolate(f, w):
        return ((1 - w["wi"]) * (1 - w["wj"]) * f[w["i0"], w["j0"]] + (1 - w["wi"]) * w["wj"] * f[w["i0"], w["j1"]]
                + w["wi"] * (1 - w["wj"]) * f[w["i1"], w["j0"]] + w["wi"] * w["wj"] * f[w["i1"], w["j1"]])


def unit_month_table(units):
    """{formula: array (n_files_months, n_units)} of interpolated values, the month list, the product boxes."""
    prod = Merra2(PRODUCT_DIR)
    yms = sorted(prod.files)
    # grid from the first file, then the weights
    prod.fields(yms[0], {"locked": FORMULAS["locked"]})
    st = pads.dataset(str(STATIC), format="parquet").to_table(
        columns=["cell_id", "lat", "lon"], filter=pads.field("cell_id").isin(list(units))).to_pandas()
    sha256(STATIC)
    if st["cell_id"].duplicated().any():
        refuse("static table names a cell twice")
    st = st.set_index("cell_id").loc[list(units)].reset_index()
    if not (np.isfinite(st["lat"]).all() and np.isfinite(st["lon"]).all()):
        refuse("unit centres hold a missing lat/lon")
    w = prod.weights(st["lat"].to_numpy(), st["lon"].to_numpy())
    boxes = np.array(["r%d_c%d" % (a, b) for a, b in zip(w["i0"], w["j0"])], dtype=object)
    tab = {k: np.full((len(yms), len(units)), np.nan) for k in FORMULAS}
    for i, ym in enumerate(yms):
        flds = prod.fields(ym, FORMULAS)
        for k in FORMULAS:
            tab[k][i] = Merra2.interpolate(flds[k], w)
    for k in FORMULAS:
        if np.isinf(tab[k]).any():
            refuse("an interpolated value is infinite (%s)" % k)
    return tab, [ym_step(*ym) for ym in yms], boxes, prod


# ==================================================================================================== 2. the slim sets
class Codes(object):
    def __init__(self, units, groups):
        self.units = list(units)
        self.groups = list(groups)

    def ucode(self, arr):
        c = pd.Categorical(np.asarray(arr).astype(str), categories=self.units).codes.astype(np.int64)
        if (c < 0).any():
            refuse("a unit is not in the index table")
        return c

    def gcode(self, arr):
        c = pd.Categorical(np.asarray(arr).astype(str), categories=self.groups).codes.astype(np.int64)
        if (c < 0).any():
            refuse("a group is not known")
        return c


def make_key(ucode, t):
    t = np.asarray(t, dtype=np.int64)
    if (t < 0).any() or (t >= (1 << TIME_SHIFT)).any():
        refuse("time out of key range")
    return (np.asarray(ucode, dtype=np.int64) << TIME_SHIFT) | t


class SetRows(object):
    """One set: unit code, group code, time, season key, y, normals by link, index-row positions."""

    def __init__(self, name, u, g, t, y, normal):
        self.name, self.u, self.g, self.t, self.y, self.normal = name, u, g, t, y, normal
        self.k = np.mod(t - 1, MONTHS) + 1                  # R2 month_of_year season key
        self.pos = None

    def take(self, mask):
        s = SetRows(self.name, self.u[mask], self.g[mask], self.t[mask],
                    None if self.y is None else self.y[mask], {l: v[mask] for l, v in self.normal.items()})
        s.pos = None if self.pos is None else self.pos[mask]
        return s


def load_slim_sets(codes, links):
    man = read_json(SLIM / "slim_manifest.json")
    files = {}
    for f in man["files"]:
        files.setdefault(f["part"], {})[f["stem"]] = f
    train_stems = sorted(files.get("train", {}))
    test_stems = sorted(files.get("test", {}))
    acc = {s: {"u": [], "g": [], "t": [], "y": [], "n": {l: [] for l in links}} for s in ("refit", "tune", "inner")}
    flags = {"refit": "r_refit", "tune": "r_tune", "inner": "r_inner"}
    for stem in train_stems:
        e = files["train"][stem]
        p = SLIM / e["path"]
        if sha256(p) != e["sha256"]:
            refuse("slim file %s does not match its manifest" % p)
        t = read_parquet(p, columns=["unit", "group", "time", "issue", "lead", "r_refit", "r_tune", "r_inner", "y"]
                         + ["nfit__" + l for l in links])
        if not ((t["lead"].to_numpy() == 0).all() and (t["issue"].to_numpy() == t["time"].to_numpy()).all()):
            refuse("slim train rows with lead != 0 or issue != time")
        ge = files["guardside"][stem]
        gp = SLIM / ge["path"]
        if sha256(gp) != ge["sha256"]:
            refuse("slim file %s does not match its manifest" % gp)
        gs = read_parquet(gp, columns=["unit", "time", "issue"] + ["ngd__" + l for l in links])
        union = t["r_tune"].to_numpy(bool) | t["r_inner"].to_numpy(bool)
        if len(gs) != int(union.sum()):
            refuse("guardside/%s rows %d vs flagged %d" % (stem, len(gs), int(union.sum())))
        ucode = codes.ucode(t["unit"].to_numpy())
        gcode = codes.gcode(t["group"].to_numpy())
        for s, flag in flags.items():
            m = t[flag].to_numpy(bool)
            if not m.any():
                continue
            acc[s]["u"].append(ucode[m])
            acc[s]["g"].append(gcode[m])
            acc[s]["t"].append(t["time"].to_numpy(np.int64)[m])
            acc[s]["y"].append(t["y"].to_numpy(np.float64)[m])
            if s in ("tune", "inner"):              # guard-side sets: ngd__ normals (slim.read_set)
                pos = (np.cumsum(union) - 1)[m]
                gsel = gs.iloc[pos]
                if not (np.array_equal(gsel["unit"].astype(str).to_numpy(), t["unit"].astype(str).to_numpy()[m])
                        and np.array_equal(gsel["time"].to_numpy(), t["time"].to_numpy()[m])):
                    refuse("guardside/%s not in train order" % stem)
                for l in links:
                    acc[s]["n"][l].append(gsel["ngd__" + l].to_numpy(np.float64))
            else:
                for l in links:
                    acc[s]["n"][l].append(t["nfit__" + l].to_numpy(np.float64)[m])
        del t, gs
    sets = {}
    for s, a in acc.items():
        sets[s] = SetRows(s, np.concatenate(a["u"]), np.concatenate(a["g"]), np.concatenate(a["t"]),
                          np.concatenate(a["y"]), {l: np.concatenate(v) for l, v in a["n"].items()})
        if not np.isfinite(sets[s].y).all():
            refuse("slim set %s holds a missing label" % s)
    # test rows: keys + nfit__ normals (no labels in the slim); saved order from the run's test_preds
    parts = []
    for stem in test_stems:
        e = files["test"][stem]
        p = SLIM / e["path"]
        if sha256(p) != e["sha256"]:
            refuse("slim file %s does not match its manifest" % p)
        parts.append(read_parquet(p, columns=["unit", "time", "issue", "lead"] + ["nfit__" + l for l in links]))
    st = pd.concat(parts, ignore_index=True)
    counts = {s: int(sets[s].y.size) for s in sets}
    counts["test_slim"] = int(len(st))
    for s, want in man["counts"].items():
        if s in counts and counts[s] != int(want):
            refuse("slim set %s holds %d rows, manifest %d" % (s, counts[s], int(want)))
    return sets, st, man, counts


# ==================================================================================================== 3. the maps
class Links(object):
    def __init__(self, c, ub):
        self.c, self.ub = float(c), ub

    def fwd(self, v, link):
        v = np.asarray(v, dtype=np.float64)
        if not np.isfinite(v).all():
            refuse("link_forward of a non-finite value")
        if link == "identity":
            return v.copy()
        if link == "log_c":
            if not ((v + self.c) > 0).all():
                refuse("log_c domain")
            return np.log(v + self.c)
        refuse("link %s" % link)

    def inv(self, z, link):
        z = np.asarray(z, dtype=np.float64)
        if not np.isfinite(z).all():
            refuse("link_inverse of a non-finite value")
        if link == "identity":
            return z.copy()
        if link == "log_c":
            return np.exp(z) - self.c
        refuse("link %s" % link)


class NotCalibratable(Exception):
    pass


def check_calibratable(y, g):
    n = int(np.asarray(y).size)
    ng = int(np.unique(g).size)
    if n < MIN_FIT_ROWS or ng < MIN_FIT_GROUPS:
        raise NotCalibratable("%d rows in %d groups" % (n, ng))


def ols(x, t):
    x = np.asarray(x, dtype=np.float64)
    t = np.asarray(t, dtype=np.float64)
    xm, tm = float(x.mean()), float(t.mean())
    dx = x - xm
    v = float(np.dot(dx, dx))
    b = float(np.dot(dx, t - tm)) / v if v > 0 else 0.0
    return tm - b * xm, b


def spearman_sign(x, y):
    from scipy.stats import spearmanr
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.size < 2 or np.all(x == x[0]) or np.all(y == y[0]):
        return True, None
    rho = float(spearmanr(x, y).correlation)
    if not math.isfinite(rho):
        return True, None
    return rho >= 0.0, rho


class Iso(object):
    def __init__(self, x, t, increasing, rho):
        from sklearn.isotonic import IsotonicRegression
        m = IsotonicRegression(increasing=bool(increasing), out_of_bounds="clip")
        m.fit(np.asarray(x, dtype=np.float64), np.asarray(t, dtype=np.float64))
        self.xk = np.asarray(m.X_thresholds_, dtype=np.float64)
        self.yk = np.asarray(m.y_thresholds_, dtype=np.float64)
        self.increasing, self.rho = bool(increasing), rho

    def __call__(self, x):
        x = np.asarray(x, dtype=np.float64)
        if self.xk.size == 1:
            return np.full(x.shape, float(self.yk[0]))
        return np.interp(x, self.xk, self.yk)


class XBar(object):
    """The index's own mean per unit x season key over the fit rows (cells with >= MIN_UNIT_ROWS rows); else the
    season-key pooled mean; else the pooled mean."""

    def __init__(self, x, u, k, n_units):
        f = pd.DataFrame({"u": np.asarray(u, dtype=np.int64), "k": np.asarray(k, dtype=np.int64),
                          "x": np.asarray(x, dtype=np.float64)})
        g = f.groupby(["u", "k"], sort=True)["x"].agg(["mean", "size"])
        self.cell = np.zeros((n_units, MONTHS + 1))
        self.has_cell = np.zeros((n_units, MONTHS + 1), dtype=bool)
        uu = g.index.get_level_values(0).to_numpy(np.int64)
        kk = g.index.get_level_values(1).to_numpy(np.int64)
        ok = g["size"].to_numpy(np.int64) >= MIN_UNIT_ROWS
        self.cell[uu[ok], kk[ok]] = g["mean"].to_numpy(np.float64)[ok]
        self.has_cell[uu[ok], kk[ok]] = True
        km = f.groupby("k", sort=True)["x"].mean()
        self.key = np.zeros(MONTHS + 1)
        self.has_key = np.zeros(MONTHS + 1, dtype=bool)
        self.key[km.index.to_numpy(np.int64)] = km.to_numpy(np.float64)
        self.has_key[km.index.to_numpy(np.int64)] = True
        self.pooled = float(f["x"].mean())
        self.n_cells = int(ok.sum())

    def __call__(self, u, k):
        u = np.asarray(u, dtype=np.int64)
        k = np.asarray(k, dtype=np.int64)
        hc = self.has_cell[u, k]
        out = np.where(hc, self.cell[u, k], np.where(self.has_key[k], self.key[k], self.pooled))
        return out

    def counts(self, u, k):
        hc = self.has_cell[np.asarray(u), np.asarray(k)]
        hk = ~hc & self.has_key[np.asarray(k)]
        return {"unit_key_mean": int(hc.sum()), "pooled_key_mean": int(hk.sum()),
                "pooled_mean": int(hc.size - hc.sum() - hk.sum())}


class MapModel(object):
    """A fitted F0..F5 map (maps.py baseline). predict -> link-space z (F0: x as shipped)."""

    def __init__(self, family, link, L, n_units):
        self.family, self.link, self.L, self.n_units = family, link, L, n_units
        self.info = {}

    @classmethod
    def fit(cls, family, link, L, x, y, z0, u, k, g, n_units):
        m = cls(family, link, L, n_units)
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        z0 = np.asarray(z0, dtype=np.float64)
        if family == "F0":
            m.info = {"rule": "pred = x as shipped"}
            return m
        check_calibratable(y, g)
        if family == "F1":
            xd = np.maximum(x, 0.0) if link == "log_c" else x
            m.a, m.b = ols(L.fwd(xd, link), L.fwd(y, link))
            m.info = {"a": m.a, "b": m.b, "rows": int(y.size)}
        elif family == "F2":
            inc, rho = spearman_sign(x, y)
            m.iso = Iso(x, L.fwd(y, link), inc, rho)
            m.info = {"increasing": inc, "spearman": rho, "knots": int(m.iso.xk.size), "rows": int(y.size)}
        elif family in ("F3", "F4", "F5"):
            m.xbar = XBar(x, u, k, n_units)
            xa = x - m.xbar(u, k)
            t = L.fwd(y, link) - z0
            if family == "F3":
                m.a, m.b = ols(xa, t)
                m.info = {"a": m.a, "b": m.b, "rows": int(y.size)}
            elif family == "F4":
                inc, rho = spearman_sign(xa, t)
                m.iso = Iso(xa, t, inc, rho)
                m.info = {"increasing": inc, "spearman": rho, "knots": int(m.iso.xk.size), "rows": int(y.size)}
            else:
                m.a_pool, m.b_pool = ols(xa, t)
                m.au = np.zeros(n_units)
                m.bu = np.zeros(n_units)
                m.hu = np.zeros(n_units, dtype=bool)
                m.nu = np.zeros(n_units, dtype=np.int64)
                K = float(SHRINK_K)
                order = np.argsort(np.asarray(u, dtype=np.int64), kind="stable")   # rows of a unit in fit order
                us = np.asarray(u, dtype=np.int64)[order]
                starts = np.flatnonzero(np.r_[True, us[1:] != us[:-1]])
                ends = np.r_[starts[1:], us.size]
                pooled_units = flat_units = 0
                for s0, s1 in zip(starts, ends):
                    unit = int(us[s0])
                    n = int(s1 - s0)
                    if n < MIN_UNIT_ROWS:
                        pooled_units += 1
                        continue
                    idx = order[s0:s1]
                    xv, tv = xa[idx], t[idx]
                    if float(np.dot(xv - xv.mean(), xv - xv.mean())) > 0:
                        a_u, b_u = ols(xv, tv)
                    else:
                        flat_units += 1
                        b_u = m.b_pool
                        a_u = float(np.mean(tv - m.b_pool * xv))
                    m.au[unit] = (n * a_u + K * m.a_pool) / (n + K)
                    m.bu[unit] = (n * b_u + K * m.b_pool) / (n + K)
                    m.hu[unit] = True
                    m.nu[unit] = n
                m.info = {"a_pool": m.a_pool, "b_pool": m.b_pool, "shrink_k": SHRINK_K, "rows": int(t.size),
                          "units_fitted": int(m.hu.sum()), "units_pooled_fewer_than_min_rows": pooled_units,
                          "units_without_x_spread_pooled_slope": flat_units}
            m.info["xbar_rows"] = m.xbar.counts(u, k)
            m.info["xbar_cells"] = m.xbar.n_cells
        else:
            refuse("family %s" % family)
        return m

    def predict_z(self, x, z0, u, k):
        x = np.asarray(x, dtype=np.float64)
        z0 = np.asarray(z0, dtype=np.float64)
        if self.family == "F0":
            return x.copy()
        if self.family == "F1":
            xd = np.maximum(x, 0.0) if self.link == "log_c" else x
            return self.a + self.b * self.L.fwd(xd, self.link)
        if self.family == "F2":
            return self.iso(x)
        xa = x - self.xbar(u, k)
        if self.family == "F3":
            return z0 + self.a + self.b * xa
        if self.family == "F4":
            return z0 + self.iso(xa)
        uu = np.asarray(u, dtype=np.int64)
        a = np.where(self.hu[uu], self.au[uu], self.a_pool)
        b = np.where(self.hu[uu], self.bu[uu], self.b_pool)
        self.info["predict_rows_on_pooled_map"] = int((~self.hu[uu]).sum())
        return z0 + a + b * xa

    def predict(self, x, z0, u, k, legal):
        """(pre, clipped): link_inverse (no smearing) except F0, then the legal clip [low, high]."""
        z = self.predict_z(x, z0, u, k)
        pre = self.L.inv(z, self.link) if self.family != "F0" else np.asarray(z, dtype=np.float64)
        if np.isinf(pre).any() or np.isnan(pre).any():
            refuse("a prediction is non-finite (%s %s)" % (self.family, self.link))
        pred = pre.copy()
        lo, hi = legal
        pred[pred < lo] = lo
        pred[pred > hi] = hi
        return pre, pred


def candidates(links):
    out = []
    for fi, f in enumerate(FAMILIES):
        for li, link in enumerate([None] if f == "F0" else links):
            out.append({"id": "pm25__%s__%s" % (f, link or "native"), "family": f, "link": link,
                        "order": (0, fi, li)})
    return out


# ---------------------------------------------------------------------------------------------- metrics (own)
def mae(y, p):
    y = np.asarray(y, dtype=np.float64)
    p = np.asarray(p, dtype=np.float64)
    if y.shape != p.shape or not y.size or not (np.isfinite(y).all() and np.isfinite(p).all()):
        refuse("mae on bad input")
    return float(np.mean(np.abs(y - p)))


def corr2(y, p):
    y = np.asarray(y, dtype=np.float64)
    p = np.asarray(p, dtype=np.float64)
    if y.max() == y.min() or p.max() == p.min():
        return float("nan")
    yc, pc = y - y.mean(), p - p.mean()
    syy, spp = float(np.sum(yc * yc)), float(np.sum(pc * pc))
    if not (syy > 0 and spp > 0):
        return float("nan")
    r = float(np.sum(yc * pc)) / math.sqrt(syy * spp)
    return r * r


def calibration_ratio(y, p):
    my = float(np.mean(np.asarray(y, dtype=np.float64)))
    return float("nan") if my == 0 else float(np.mean(np.asarray(p, dtype=np.float64))) / my


# ==================================================================================================== 4. procedure
class Context(object):
    """Everything fixed across variants: sets, test frame, comparator inputs, run facts."""
    pass


def x_of(set_rows, x_index):
    return x_index[set_rows.pos]


def run_trials(C, x_index, cands):
    tune, inner = C.sets["tune"], C.sets["inner"]
    xt = x_of(tune, x_index)
    ok = np.isfinite(xt) & np.isfinite(tune.y)
    fit = tune.take(ok)
    xf = xt[ok]
    xi = x_of(inner, x_index)
    cov = np.isfinite(xi)
    sc = inner.take(cov)
    xs = xi[cov]
    recs = []
    for cand in cands:
        link = cand["link"] or "identity"
        t1 = time.time()
        try:
            model = MapModel.fit(cand["family"], cand["link"], C.L, xf, fit.y, fit.normal[link], fit.u, fit.k, fit.g,
                                 C.n_units)
        except NotCalibratable as exc:
            recs.append(dict(cand, status="not_calibratable", reason=str(exc)))
            continue
        pre, pred = model.predict(xs, sc.normal[link], sc.u, sc.k, C.legal)
        recs.append(dict(cand, status="ok", pick_mae=mae(sc.y, pred), corr2=corr2(sc.y, pred),
                         calibration_ratio=calibration_ratio(sc.y, pred), rows_score=int(sc.y.size),
                         rows_fit=int(fit.y.size), info=model.info))
        log("  trial %-22s inner MAE %.16g (%.1f s)" % (cand["id"], recs[-1]["pick_mae"], time.time() - t1))
    return recs


def pick_of(recs):
    best = None
    for r in sorted(recs, key=lambda r: tuple(r["order"])):
        if r["status"] != "ok":
            continue
        v = float(r["pick_mae"])
        if not math.isfinite(v):
            refuse("non-finite pick MAE")
        if best is None or v < float(best["pick_mae"]):
            best = r
    return best


def comparator_inner(C, sc, link):
    """N2 comparator on the covered inner rows: inner_preds.parquet <link>_trees_off_unweighted, key-joined by
    (unit, time); the labels must equal the slim labels byte for byte (harness _inner_comparator)."""
    col = (link or "identity") + "_trees_off_unweighted"
    ip = C.inner_preds
    key = make_key(sc.u, sc.t)
    pos = np.searchsorted(ip["_key_sorted"], key)
    if (pos >= ip["_key_sorted"].size).any() or not np.array_equal(ip["_key_sorted"][np.minimum(pos, ip["_key_sorted"].size - 1)], key):
        refuse("a guard row has no inner_preds row")
    rows = ip["_order"][pos]
    yv = ip["y"][rows]
    if yv.tobytes() != np.asarray(sc.y, dtype=np.float64).tobytes():
        refuse("inner labels differ from inner_preds.parquet")
    return col, ip[col][rows]


def guard_and_refit(C, x_index, cand, saved_pick_mae=None):
    """Lead 0: guard = the pick fitted on the tune rows, scored on the covered inner rows, vs the N2 comparator;
    refit on the refit rows; raw and guarded predictions on the covered test rows (saved order)."""
    link = cand["link"] or "identity"
    tune, inner, refit = C.sets["tune"], C.sets["inner"], C.sets["refit"]
    # guard
    xt = x_of(tune, x_index)
    ok = np.isfinite(xt) & np.isfinite(tune.y)
    fit = tune.take(ok)
    gmodel = MapModel.fit(cand["family"], cand["link"], C.L, xt[ok], fit.y, fit.normal[link], fit.u, fit.k, fit.g,
                          C.n_units)
    xi = x_of(inner, x_index)
    gcov = np.isfinite(xi)
    gsc = inner.take(gcov)
    g_pre, g_pred = gmodel.predict(xi[gcov], gsc.normal[link], gsc.u, gsc.k, C.legal)
    comp_name, comp = comparator_inner(C, gsc, cand["link"])
    g_mae, c_mae = mae(gsc.y, g_pred), mae(gsc.y, comp)
    passed = bool(g_mae < c_mae)                       # layer/decide.py n2_eligible: strictly lower
    if saved_pick_mae is not None and g_mae != float(saved_pick_mae):
        refuse("determinism: the guard MAE %r differs from the trial MAE %r" % (g_mae, saved_pick_mae))
    # refit
    xr = x_of(refit, x_index)
    okr = np.isfinite(xr) & np.isfinite(refit.y)
    rf = refit.take(okr)
    model = MapModel.fit(cand["family"], cand["link"], C.L, xr[okr], rf.y, rf.normal[link], rf.u, rf.k, rf.g,
                         C.n_units)
    # test rows in saved order
    xs = x_index[C.test_pos]
    mask = np.isfinite(xs)
    T = C.test
    t_pre = np.full(len(xs), np.nan)
    pre_c, raw_c = model.predict(xs[mask], T["normal"][link][mask], T["u"][mask], T["k"][mask], C.legal)
    t_pre[mask] = pre_c
    t_raw = np.full(len(xs), np.nan)
    t_raw[mask] = raw_c
    guarded = np.where(mask, t_raw if passed else C.fb, np.nan)
    guard = {"rows": int(gsc.y.size), "rival_mae": g_mae, "comparator": comp_name, "comparator_mae": c_mae,
             "passed": passed, "rival_corr2": corr2(gsc.y, g_pred), "rival_calibration_ratio":
                 calibration_ratio(gsc.y, g_pred)}
    return {"candidate": cand["id"], "family": cand["family"], "link": cand["link"], "guard": guard,
            "guard_frame": {"u": gsc.u, "t": gsc.t, "y": gsc.y, "pre": g_pre, "pred": g_pred, "comparator": comp},
            "refit_info": model.info, "guard_fit_info": gmodel.info, "refit_rows": int(rf.y.size),
            "mask": mask, "x": xs, "pre": t_pre, "raw": t_raw, "guarded": guarded}


# ==================================================================================================== 5. scoring
def per_group_mae(frame, col):
    y = frame["y"].to_numpy(np.float64)
    p = frame[col].to_numpy(np.float64)
    if np.isinf(y).any() or np.isinf(p).any():
        refuse("infinite value in y or %s" % col)
    out = {}
    for g, idx in sorted(frame.groupby("group", sort=True).indices.items(), key=lambda kv: str(kv[0])):
        idx = np.asarray(idx)
        if (np.isfinite(y[idx]) & ~np.isfinite(p[idx])).any():
            refuse("arm %s missing on a labelled row of group %s" % (col, g))
        rows = idx[np.isfinite(y[idx]) & np.isfinite(p[idx])]
        if not rows.size:
            refuse("group %s has no scored row" % g)
        out[str(g)] = (float(np.mean(np.abs(y[rows] - p[rows]))), int(rows.size))
    return out


def jackknife(v, z):
    v = np.asarray(v, dtype=np.float64)
    n = int(v.size)
    jk = np.array([np.delete(v, i).mean() for i in range(n)])
    se = float(np.sqrt((n - 1) / n * ((jk - jk.mean()) ** 2).sum()))
    mean = float(v.mean())
    return {"mean": mean, "se": se, "low": float(mean - z * se), "high": float(mean + z * se), "n_groups": n}


def tag_of(dv, jk, band, atol):
    if np.all(np.abs(dv) <= atol):
        return "identical"
    if not (math.isfinite(jk["low"]) and math.isfinite(jk["high"])):
        return "cannot_tell"
    if -band <= jk["low"] and jk["high"] <= band:
        return "does_not_help_equivalent"
    if jk["low"] > 0 and jk["mean"] >= band:
        return "helps"
    if jk["high"] < 0 and jk["mean"] <= -band:
        return "hurts"
    return "cannot_tell"


def contrast(C, fd, rcol, ocol):
    """Board _contrast on the deciding rows: per-group MAE (rows with finite y and forecast), d = rival - ours per
    group, leave-one-group-out jackknife at the engine's z, the run's band; cross-checked with the engine's own
    metrics.contrast_tag on the same d vector (read-only import)."""
    M = C.M
    rmap, omap = per_group_mae(fd, rcol), per_group_mae(fd, ocol)
    if set(rmap) != set(omap):
        refuse("the two MAE maps hold different groups")
    groups = sorted(rmap)
    dv = np.array([rmap[g][0] - omap[g][0] for g in groups])
    jk = jackknife(dv, C.Z)
    tag = tag_of(dv, jk, C.band, C.atol)
    etag, ejk = M.contrast_tag(dv, C.band)
    engine_agrees = bool(etag.value == tag and ejk.mean == jk["mean"] and ejk.low == jk["low"]
                         and ejk.high == jk["high"])
    if not engine_agrees:
        refuse("own jackknife/tag differs from the engine's contrast_tag")
    members = {}
    for g, d in zip(groups, dv.tolist()):
        members.setdefault(int(C.block_of_group[g]), []).append(float(d))
    bj = jackknife(np.array([float(np.mean(members[b])) for b in sorted(members)]), C.Z)
    y = fd["y"].to_numpy(np.float64)
    pr = fd[rcol].to_numpy(np.float64)
    po = fd[ocol].to_numpy(np.float64)
    okr = np.isfinite(y) & np.isfinite(pr)
    oko = np.isfinite(y) & np.isfinite(po)
    if not np.array_equal(okr, oko):
        refuse("pooled rows differ between arms")
    return {"verdict": VERDICT_WORDS[tag], "tag": tag, "d_mean": jk["mean"], "d_se": jk["se"], "d_low": jk["low"],
            "d_high": jk["high"], "n_groups": jk["n_groups"], "blocked_mean": bj["mean"], "blocked_se": bj["se"],
            "rival_mae": M.mae(y[okr], pr[okr]), "ours_mae_same_rows": M.mae(y[oko], po[oko]),
            "corr2": M.corr2(y[okr], pr[okr]), "calibration_ratio": M.calibration_ratio(y[okr], pr[okr]),
            "ours_corr2": M.corr2(y[oko], po[oko]), "scored_rows": int(okr.sum()), "rows": int(len(fd)),
            "groups_rival_worse": int((dv > 0).sum()), "groups_rival_better": int((dv < 0).sum()),
            "engine_contrast_tag_agrees_bit_exact": engine_agrees}


def score_variant(C, guarded, raw, mask):
    f = C.frame.copy()
    f["arm__rival"] = guarded
    f["arm__rival_raw"] = raw
    fc = f.loc[mask].reset_index(drop=True)
    gcount = fc.groupby("group").size()
    dec = sorted(gcount.index[gcount >= MIN_GROUP_TEST_ROWS].astype(str).tolist())
    fd = fc[fc["group"].astype(str).isin(dec)].reset_index(drop=True)
    out = {"rows_covered": int(mask.sum()), "rows_total": int(mask.size), "groups": len(dec),
           "groups_covered": int(len(gcount))}
    out["guarded_vs_headline"] = contrast(C, fd, "arm__rival", "arm__ours")
    out["raw_vs_raw"] = contrast(C, fd, "arm__rival_raw", "arm__ours_raw")
    return out


def extremes(C, res, x_locked_test):
    """Largest guarded forecast, count > 1,000 ug/m3 (guarded and raw), the yakutia 2021-08 row."""
    g = res["guarded"]
    r = res["raw"]
    T = C.test
    i = int(np.nanargmax(g))
    yr, mo = step_ym(T["time"][i])
    ir = int(np.nanargmax(r))
    yk = np.flatnonzero((T["unit"] == YAKUTIA[0]) & (T["time"] == ym_step(YAKUTIA[1], YAKUTIA[2])))
    if yk.size != 1:
        refuse("the yakutia row is not one saved test row")
    j = int(yk[0])
    return {
        "largest_guarded_forecast": {"value_ug_m3": float(g[i]), "unit": str(T["unit"][i]),
                                     "group": str(T["group"][i]), "month": "%d-%02d" % (yr, mo),
                                     "x_new": float(res["x"][i]), "x_locked": float(x_locked_test[i]),
                                     "y": float(C.frame["y"].iloc[i]), "ours": float(C.frame["arm__ours"].iloc[i])},
        "largest_raw_forecast": {"value_ug_m3": float(r[ir]), "unit": str(T["unit"][ir]),
                                 "month": "%d-%02d" % step_ym(T["time"][ir]), "x_new": float(res["x"][ir])},
        "count_guarded_gt_1000": int(np.sum(np.where(np.isfinite(g), g, -np.inf) > THRESH)),
        "count_raw_gt_1000": int(np.sum(np.where(np.isfinite(r), r, -np.inf) > THRESH)),
        "test_rows": int(g.size),
        "yakutia_row": {"unit": YAKUTIA[0], "month": "%d-%02d" % YAKUTIA[1:], "guarded": float(g[j]),
                        "raw": float(r[j]), "pre": float(res["pre"][j]), "x_new": float(res["x"][j]),
                        "x_locked": float(x_locked_test[j]), "y": float(C.frame["y"].iloc[j]),
                        "ours": float(C.frame["arm__ours"].iloc[j])},
    }


def x_change(x_new, x_old):
    ok = np.isfinite(x_new) & np.isfinite(x_old)
    if not np.array_equal(np.isfinite(x_new), np.isfinite(x_old)):
        refuse("the corrected x changes which rows are finite")
    r = x_new[ok] / x_old[ok]
    return {"rows": int(ok.sum()), "ratio_median": float(np.median(r)), "ratio_p99": float(np.percentile(r, 99)),
            "ratio_p01": float(np.percentile(r, 1)), "ratio_min": float(r.min()), "ratio_max": float(r.max()),
            "share_moved_more_than_10pct": float(np.mean(np.abs(r - 1.0) > 0.10)),
            "rows_moved_more_than_10pct": int(np.sum(np.abs(r - 1.0) > 0.10))}


def save_preds(C, rival, variant, res, x_locked_test):
    T = C.test
    frame = pd.DataFrame({"unit": T["unit"], "group": T["group"], "time": T["time"], "issue": T["issue"],
                          "lead": T["lead"], "x_locked": x_locked_test, "x_new": res["x"], "covered": res["mask"],
                          "pre": res["pre"], "raw": res["raw"], "guarded": res["guarded"],
                          "guard_passed": bool(res["guard"]["passed"]), "family": res["family"],
                          "link": res["link"] or "native"})
    p = OUT_DIR / ("preds_%s_%s.parquet" % (rival, variant))
    if p.exists():
        refuse("%s already exists (never overwritten; move it aside by hand)" % p)
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), str(p))
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    return {"file": str(p), "sha256": h, "rows": int(len(frame))}


def variant_record(C, rival, variant, res, trials=None, picked=None, x_locked_test=None, save=True, selection=""):
    rec = {"rival": rival, "variant": variant, "selection": selection, "picked_family": res["family"],
           "picked_link": res["link"],
           "candidate": res["candidate"], "guard": res["guard"], "refit_rows": res["refit_rows"],
           "refit_map_info": {k: v for k, v in res["refit_info"].items()}}
    if trials is not None:
        rec["trials"] = [{"candidate": t["id"], "status": t["status"], "inner_mae": t.get("pick_mae"),
                          "corr2": t.get("corr2"), "calibration_ratio": t.get("calibration_ratio"),
                          "rows_score": t.get("rows_score")} for t in trials]
        rec["pick_rule"] = "lowest inner MAE over the calibratable candidates; ties by the fixed order"
    rec["score"] = score_variant(C, res["guarded"], res["raw"], res["mask"])
    if x_locked_test is not None:
        rec["extremes"] = extremes(C, res, x_locked_test)
        if save:
            rec["preds_file"] = save_preds(C, rival, variant, res, x_locked_test)
    return rec


# ==================================================================================================== main
def main():
    global OUT_DIR
    # optional: --out <folder> (a scratch folder for a trial run) and --stop-after 0a|0b|0c (trial runs only)
    args = sys.argv[1:]
    stop_after = None
    if "--out" in args:
        OUT_DIR = Path(args[args.index("--out") + 1])
    if "--stop-after" in args:
        stop_after = args[args.index("--stop-after") + 1]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if (OUT_DIR / "result_B.json").exists():
        refuse("result_B.json exists already (never overwritten)")
    script = Path(__file__).resolve()
    report = {"what": "POST HOC re-score of the MERRA-2 PM2.5 human rivals with the GMAO PM2.5 formula "
                      "(OCSMASS x1.0 instead of x1.4; sulfate factor kept at the locked 1.375). Implementer B, "
                      "independent path. The locked verdicts never change; these are sensitivities.",
              "script": str(script), "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
              "code_basis": {"maps": "BASELINE copy (pre-Part-B edit) of maps.py; the live maps.py differs only in "
                                     "F6 / weighted isotonic, not used by these rivals",
                             "tool_files_read_sha256": {str(p): sha256(p) for p in TOOL_FILES_READ}},
              "formulas": {k: dict(v) for k, v in FORMULAS.items()}}

    # ---- run facts
    derived = read_json(RUN / "derived.json")
    plan = read_json(RUN / "plan.json")
    verdict = read_json(RUN / "verdict.json")
    links = list(plan["links"])
    if links != list(derived["R22"]["value"]):
        refuse("plan links differ from R22")
    c = float(derived["R23:lead=0"]["value"])
    lg = derived["R28"]["value"]
    legal = (float(lg[0]), float(lg[1]))
    ub = legal[1] if math.isfinite(legal[1]) else None
    band = float(verdict["band"])
    headline = "arm__" + verdict["adopted"]
    if verdict.get("declined"):
        refuse("declined run")
    fb_col = "arm__identity_trees_off_unweighted"
    sys.path.insert(0, str(ENGINE))
    from treeroute import engine_constants as K      # noqa: E402  read-only
    from treeroute.report import metrics as M         # noqa: E402  read-only
    for mod in (K, M):
        sha256(mod.__file__)
    import threadpoolctl                              # noqa: E402  (report the pools actually in use)
    report["threadpool_info"] = sorted([str(i.get("user_api")), str(i.get("internal_api")), str(i.get("prefix")),
                                        int(i.get("num_threads"))] for i in threadpoolctl.threadpool_info())
    report["thread_pins"] = {v: os.environ.get(v) for v in PIN_VARS}
    C = Context()
    C.M, C.Z, C.atol = M, float(K.JACKKNIFE_Z), float(M.IDENTICAL_ATOL)
    C.L = Links(c, ub)
    C.legal, C.band = legal, band
    C.block_of_group = derived["R14:overlap_blocks"]["value"]["block_of_group"]
    report["run_facts"] = {"links": links, "c": c, "legal": [legal[0], str(legal[1])], "band": band,
                           "headline_column": headline, "fallback_column": fb_col, "jackknife_z": C.Z}
    log("run facts: links %s c %r legal %s band %r" % (links, c, legal, band))

    # ---- index tables (keys identical across the three rivals?)
    idx = {}
    for rid in RIVALS:
        p = INDEX_ROOT / rid / "lead_0.parquet"
        js = read_json(INDEX_ROOT / rid / "lead_0.json")
        if js["stages"]["all"]["sha256"] != sha256(p):
            refuse("index %s sha differs from its json" % rid)
        idx[rid] = {"frame": read_parquet(p, columns=["unit", "time", "issue", "lead", "info_end", "product_cell",
                                                       "x__pm25"], read_dictionary=["unit", "product_cell"]),
                    "json": js}
    base = idx["merra2_lag1"]["frame"]
    units = sorted(set(base["unit"].astype(str).unique().tolist()))
    for rid in RIVALS:
        fr = idx[rid]["frame"]
        if not (np.array_equal(fr["unit"].astype(str).to_numpy(), base["unit"].astype(str).to_numpy())
                and np.array_equal(fr["time"].to_numpy(), base["time"].to_numpy())
                and np.array_equal(fr["issue"].to_numpy(), base["issue"].to_numpy())
                and (fr["lead"].to_numpy() == 0).all() and (fr["issue"].to_numpy() == fr["time"].to_numpy()).all()):
            refuse("index %s keys differ from merra2_lag1's (or lead/issue rule)" % rid)
    log("index tables: %d rows, %d units" % (len(base), len(units)))

    # ---- product -> unit x month table (three formulas)
    tab, steps, boxes, prod = unit_month_table(units)
    n_match = {}
    for rid in RIVALS:
        opened_ = idx[rid]["json"]["stages"]["all"]["opened"]["merra2_aer_monthly"]
        n_match[rid] = 0
        for (y_, m_), p in prod.files.items():
            want_sha = opened_.get(p.name)
            if want_sha is None:
                continue
            if want_sha != sha256(p):
                refuse("product file %s sha differs from the %s index build's" % (p.name, rid))
            n_match[rid] += 1
    report["product"] = {"files": len(prod.files), "masked_cells_by_component": prod.masked_cells,
                         "files_sha256_equal_to_index_build_record": n_match,
                         "grid": {"nlat": int(prod.grid["lat"].size), "nlon": int(prod.grid["lon"].size),
                                  "dlat": prod.grid["dlat"], "dlon": prod.grid["dlon"]}}
    log("product table built: %d months x %d units" % (len(steps), len(units)))
    step_pos = {s: i for i, s in enumerate(steps)}
    ucode_idx = pd.Categorical(base["unit"].astype(str).to_numpy(), categories=units).codes.astype(np.int64)
    issue = base["issue"].to_numpy(np.int64)

    # ---- gate 0a: rebuild x with the locked formula at every index row
    xs = {}
    gate0a = {}
    for rid, opt in RIVALS.items():
        fr = idx[rid]["frame"]
        read = issue + opt["month_offset"] - MONTHS * opt["placebo_shift_years"]
        if not np.array_equal(read, fr["info_end"].to_numpy(np.int64)):
            refuse("%s: info_end differs from issue + offset - 12 x shift" % rid)
        mpos = {int(s): step_pos.get(int(s), -1) for s in np.unique(read)}
        rpos = pd.Series(read).map(mpos).to_numpy(np.int64)
        have = rpos >= 0
        xs[rid] = {}
        for fname in FORMULAS:
            x = np.full(len(fr), np.nan)
            x[have] = tab[fname][rpos[have], ucode_idx[have]]
            xs[rid][fname] = x
        cmp_ = nan_max_abs(xs[rid]["locked"], fr["x__pm25"].to_numpy(np.float64))
        pc_ok = bool(np.array_equal(boxes[ucode_idx], fr["product_cell"].astype(str).to_numpy()))
        cmp_["product_cell_equal"] = pc_ok
        cmp_["rows"] = int(len(fr))
        cmp_["rows_finite"] = int(np.isfinite(xs[rid]["locked"]).sum())
        cmp_["passed"] = bool(cmp_["nan_pattern_equal"] and cmp_["max_rel_diff"] <= 1e-6 and pc_ok)
        gate0a[rid] = cmp_
        log("gate 0a %s: %s" % (rid, cmp_))
        if not cmp_["passed"]:
            report["gate_0a"] = gate0a
            _dump_partial(report)
            refuse("gate 0a failed for %s: %s" % (rid, cmp_))
    report["gate_0a"] = gate0a
    if stop_after == "0a":
        _dump_partial(report)
        return
    # the locked rebuild equals the index: from here on, x_locked = the index column itself
    for rid in RIVALS:
        xs[rid]["index"] = idx[rid]["frame"]["x__pm25"].to_numpy(np.float64)
    del tab

    # ---- slim sets and positions into the index rows
    groups = sorted(set(read_parquet(SLIM / "units.parquet")["group"].astype(str).tolist())) \
        if "group" in pq.read_schema(str(SLIM / "units.parquet")).names else None
    if groups is None:
        refuse("units.parquet has no group column")
    codes = Codes(units, groups)
    C.n_units = len(units)
    sets, slim_test, man, counts = load_slim_sets(codes, links)
    if abs(float(man["c"]) - c) != 0:
        refuse("slim c differs from the run's")
    idx_key = make_key(ucode_idx, base["time"].to_numpy(np.int64))
    order = np.argsort(idx_key, kind="stable")
    ks = idx_key[order]
    if (np.diff(ks) == 0).any():
        refuse("the index names a key twice")

    def positions(u, t, what):
        k = make_key(u, t)
        p = np.searchsorted(ks, k)
        p = np.minimum(p, ks.size - 1)
        if not np.array_equal(ks[p], k):
            refuse("%s: %d keys have no index row" % (what, int((ks[p] != k).sum())))
        return order[p]

    for s in sets.values():
        s.pos = positions(s.u, s.t, "set %s" % s.name)
    log("slim sets: %s" % counts)
    C.sets = sets

    # ---- saved test rows (saved order), labels + our columns (the board already opened them)
    opened = read_json(BOARD / "test_labels_opened_human_lead_0.json")
    tp_path = Path(opened["file"])
    if sha256(tp_path) != opened["test_preds_sha256"]:
        refuse("test_preds.parquet differs from the file the board opened")
    saved = read_parquet(tp_path, columns=["unit", "group", "time", "year", "lead", "issue", "y", "normal",
                                           headline, fb_col])
    saved["unit"] = saved["unit"].astype(str)
    saved["group"] = saved["group"].astype(str)
    su = codes.ucode(saved["unit"].to_numpy())
    st_ = slim_test.copy()
    st_u = codes.ucode(st_["unit"].astype(str).to_numpy())
    sk = make_key(st_u, st_["time"].to_numpy(np.int64))
    so = np.argsort(sk)
    want = make_key(su, saved["time"].to_numpy(np.int64))
    pp = np.minimum(np.searchsorted(sk[so], want), sk.size - 1)
    if not np.array_equal(sk[so][pp], want) or len(st_) != len(saved):
        refuse("slim test keys do not match the saved test rows")
    tpos = so[pp]
    C.test = {"unit": saved["unit"].to_numpy(), "group": saved["group"].to_numpy(),
              "time": saved["time"].to_numpy(np.int64), "issue": saved["issue"].to_numpy(np.int64),
              "lead": saved["lead"].to_numpy(np.int64), "u": su,
              "k": np.mod(saved["time"].to_numpy(np.int64) - 1, MONTHS) + 1,
              "normal": {l: st_["nfit__" + l].to_numpy(np.float64)[tpos] for l in links}}
    C.test_pos = positions(su, saved["time"].to_numpy(np.int64), "saved test rows")
    C.fb = saved[fb_col].to_numpy(np.float64)
    if not np.isfinite(C.fb).all():
        refuse("fallback missing on a saved test row")
    frame = saved[["unit", "group", "time", "year", "lead", "issue", "y", "normal"]].copy()
    frame["arm__ours"] = saved[headline].to_numpy(np.float64)
    frame["arm__ours_raw"] = saved[headline].to_numpy(np.float64)   # lead 0 not declined: pinned arm = adopted
    C.frame = frame
    # inner_preds (N2 comparator)
    ip = read_parquet(RUN / "inner_preds.parquet", columns=["unit", "time", "y", "identity_trees_off_unweighted",
                                                            "log_c_trees_off_unweighted"])
    ik = make_key(codes.ucode(ip["unit"].astype(str).to_numpy()), ip["time"].to_numpy(np.int64))
    io = np.argsort(ik, kind="stable")
    if (np.diff(ik[io]) == 0).any():
        refuse("inner_preds names a (unit, time) twice")
    C.inner_preds = {"_key_sorted": ik[io], "_order": io, "y": ip["y"].to_numpy(np.float64),
                     "identity_trees_off_unweighted": ip["identity_trees_off_unweighted"].to_numpy(np.float64),
                     "log_c_trees_off_unweighted": ip["log_c_trees_off_unweighted"].to_numpy(np.float64)}
    del ip
    log("test rows %d; inner_preds rows %d" % (len(saved), io.size))
    cands = candidates(links)

    # ================================================================== gate 0b: locked procedure, merra2_lag1
    trials_csv = pd.read_csv(BOARD / "trials.csv", float_precision="round_trip")
    sha256(BOARD / "trials.csv")

    def check_trials(rid, recs):
        out = {}
        worst = 0.0
        exact = True
        for r in recs:
            row = trials_csv[(trials_csv["rival"] == rid) & (trials_csv["candidate"] == r["id"])]
            if len(row) != 1:
                refuse("trials.csv has no %s %s" % (rid, r["id"]))
            row = row.iloc[0]
            d = {k: (r.get(k2), float(row[k])) for k, k2 in (("mae", "pick_mae"), ("corr2", "corr2"),
                                                               ("calibration_ratio", "calibration_ratio"))}
            for k, (a, b) in d.items():
                worst = max(worst, abs(a - b))
                exact = exact and (a == b)
            out[r["id"]] = {"inner_mae_mine": r["pick_mae"], "inner_mae_board": float(row["mae"]),
                            "rows": r["rows_score"], "rows_board": int(row["rows_score"])}
            if r["rows_score"] != int(row["rows_score"]):
                refuse("trial rows differ for %s %s" % (rid, r["id"]))
        return out, worst, exact

    log("gate 0b: merra2_lag1 locked, all %d candidates" % len(cands))
    recs = run_trials(C, xs["merra2_lag1"]["index"], cands)
    tr_cmp, tr_worst, tr_exact = check_trials("merra2_lag1", recs)
    pick = pick_of(recs)
    res = guard_and_refit(C, xs["merra2_lag1"]["index"], pick, pick["pick_mae"])
    done = read_json(LEAD0 / "done_merra2_lag1.json")
    lp = LEAD0 / "preds_merra2_lag1.parquet"
    if sha256(lp) != done["preds_sha256"]:
        refuse("the locked preds file changed")
    lpf = read_parquet(lp)
    lpf["unit"] = lpf["unit"].astype(str)
    if not (np.array_equal(lpf["unit"].to_numpy(), C.test["unit"]) and
            np.array_equal(lpf["time"].to_numpy(np.int64), C.test["time"])):
        refuse("the locked preds file is not in the saved order")
    gfile = read_parquet(LEAD0 / "guard_merra2_lag1.parquet")
    g_cmp = {k: nan_max_abs(res["guard_frame"][k2], gfile[k].to_numpy(np.float64))
             for k, k2 in (("y", "y"), ("pre", "pre"), ("pred", "pred"), ("comparator", "comparator"))}
    mapj = read_json(LEAD0 / "map_merra2_lag1.json")
    map_cmp = {k: {"mine": res["refit_info"].get(k), "board": mapj["refit"]["info"].get(k)}
               for k in ("a_pool", "b_pool", "rows", "units_fitted", "units_pooled_fewer_than_min_rows",
                         "units_without_x_spread_pooled_slope")}
    map_cmp["guard_a_pool"] = {"mine": res["guard_fit_info"]["a_pool"], "board": mapj["guard"]["info"]["a_pool"]}
    map_cmp["guard_b_pool"] = {"mine": res["guard_fit_info"]["b_pool"], "board": mapj["guard"]["info"]["b_pool"]}
    preds_cmp = {k: nan_max_abs(res[k], lpf[k].to_numpy(np.float64)) for k in ("x", "pre", "raw", "guarded")}
    preds_cmp["covered_equal"] = bool(np.array_equal(res["mask"], lpf["covered"].to_numpy(bool)))
    gd = done["guard"]
    guard_cmp = {"rival_mae": [res["guard"]["rival_mae"], gd["rival_mae"]],
                 "comparator_mae": [res["guard"]["comparator_mae"], gd["comparator_mae"]],
                 "rows": [res["guard"]["rows"], gd["rows"]], "passed": [res["guard"]["passed"], gd["passed"]],
                 "comparator": [res["guard"]["comparator"], gd["comparator"]]}
    ok0b = (pick["family"] == "F5" and pick["link"] == "log_c" and res["guard"]["rival_mae"] == gd["rival_mae"]
            and res["guard"]["comparator_mae"] == gd["comparator_mae"] and res["guard"]["rows"] == gd["rows"]
            and res["guard"]["passed"] == gd["passed"] and preds_cmp["covered_equal"]
            and preds_cmp["guarded"]["nan_pattern_equal"] and preds_cmp["guarded"]["max_rel_diff"] <= 1e-9
            and all(map_cmp[k]["mine"] == map_cmp[k]["board"] for k in map_cmp))
    report["gate_0b"] = {"passed": bool(ok0b), "picked": pick["id"], "trials_vs_trials_csv": tr_cmp,
                         "trials_max_abs_diff_mae_corr2_cal": tr_worst, "trials_all_bit_exact": tr_exact,
                         "guard_vs_done_file": guard_cmp, "guard_rows_vs_guard_file": g_cmp,
                         "refit_map_vs_map_file": map_cmp, "test_preds_vs_preds_file": preds_cmp}
    log("gate 0b: passed=%s pick %s guard %r vs %r; preds guarded %s" % (ok0b, pick["id"], res["guard"]["rival_mae"],
                                                                       res["guard"]["comparator_mae"],
                                                                       preds_cmp["guarded"]))
    if not ok0b:
        _dump_partial(report)
        refuse("gate 0b failed (see result_B.partial.json)")
    if stop_after == "0b":
        _dump_partial(report)
        return
    x_lock_test = {rid: xs[rid]["index"][C.test_pos] for rid in RIVALS}

    # ================================================================== gate 0c: the locked deciding contrast
    tb = pd.read_csv(TABLE, float_precision="round_trip")
    sha256(TABLE)
    trow = tb[(tb["problem"] == "pm25") & (tb["lead"] == 0) & (tb["rival"] == "merra2_lag1")
              & (tb["contrast"] == "guarded_vs_headline")]
    bl = pd.read_csv(BOARD / "human_board_lead_0.csv", float_precision="round_trip")
    sha256(BOARD / "human_board_lead_0.csv")
    brow = bl[(bl["rival"] == "merra2_lag1") & (bl["contrast"] == "guarded_vs_headline")]
    if len(trow) != 1 or len(brow) != 1:
        refuse("table/board rows not unique")
    trow, brow = trow.iloc[0], brow.iloc[0]
    sc_file = score_variant(C, lpf["guarded"].to_numpy(np.float64), lpf["raw"].to_numpy(np.float64),
                            lpf["covered"].to_numpy(bool))
    sc_mine = score_variant(C, res["guarded"], res["raw"], res["mask"])
    g0c = {}
    worst = 0.0
    for src, sc in (("from_locked_preds_file", sc_file), ("from_my_reproduced_preds", sc_mine)):
        cg = sc["guarded_vs_headline"]
        chk = {}
        for k in ("d_mean", "d_low", "d_high", "rival_mae", "ours_mae_same_rows", "corr2", "calibration_ratio"):
            chk[k] = {"mine": cg[k], "rivals_table": float(trow[k]), "board_csv": float(brow[k]),
                      "abs_diff_table": abs(cg[k] - float(trow[k])), "abs_diff_board": abs(cg[k] - float(brow[k]))}
            worst = max(worst, chk[k]["abs_diff_table"], chk[k]["abs_diff_board"])
        chk["d_se"] = {"mine": cg["d_se"], "board_csv": float(brow["d_se"])}
        chk["verdict"] = {"mine": cg["verdict"], "rivals_table": trow["verdict"], "board_csv": brow["verdict"]}
        chk["rows"] = {"mine": cg["rows"], "rivals_table": int(trow["rows"])}
        chk["groups"] = {"mine": cg["n_groups"], "rivals_table": int(trow["groups"])}
        g0c[src] = chk
        if not (cg["verdict"] == trow["verdict"] == brow["verdict"] and cg["rows"] == int(trow["rows"])
                and cg["n_groups"] == int(trow["groups"])):
            report["gate_0c"] = g0c
            _dump_partial(report)
            refuse("gate 0c: verdict/rows/groups not reproduced (%s)" % src)
    g0c["max_abs_diff"] = worst
    g0c["passed"] = bool(worst <= 1e-9)
    report["gate_0c"] = g0c
    log("gate 0c: max abs diff %r passed=%s" % (worst, g0c["passed"]))
    if not g0c["passed"]:
        _dump_partial(report)
        refuse("gate 0c failed")
    report["locked_merra2_lag1_extremes"] = extremes(C, res, x_lock_test["merra2_lag1"])
    if stop_after == "0c":
        _dump_partial(report)
        return
    save_info = save_preds(C, "merra2_lag1", "locked_repro", res, x_lock_test["merra2_lag1"])
    report["locked_merra2_lag1_repro_preds_file"] = save_info

    # ---- extra validation of the same code on the other two locked rivals (not required by the spec)
    extra = {}
    log("extra check: merra2_same locked, all candidates")
    recs_s = run_trials(C, xs["merra2_same"]["index"], cands)
    cmp_s, worst_s, exact_s = check_trials("merra2_same", recs_s)
    pick_s = pick_of(recs_s)
    res_s = guard_and_refit(C, xs["merra2_same"]["index"], pick_s, pick_s["pick_mae"])
    done_s = read_json(LEAD0 / "done_merra2_same.json")
    pf_s = read_parquet(LEAD0 / "preds_merra2_same.parquet", columns=["guarded"])
    extra["merra2_same"] = {"picked": pick_s["id"], "trials_max_abs_diff": worst_s, "trials_all_bit_exact": exact_s,
                            "guard": [res_s["guard"]["rival_mae"], done_s["guard"]["rival_mae"],
                                      res_s["guard"]["comparator_mae"], done_s["guard"]["comparator_mae"]],
                            "guarded_vs_preds_file": nan_max_abs(res_s["guarded"], pf_s["guarded"].to_numpy())}
    log("extra merra2_same: %s" % extra["merra2_same"])
    res_p = guard_and_refit(C, xs["merra2_lag1_placebo"]["index"], pick)
    done_p = read_json(LEAD0 / "done_merra2_lag1_placebo.json")
    pf_p = read_parquet(LEAD0 / "preds_merra2_lag1_placebo.parquet", columns=["raw", "guarded"])
    extra["merra2_lag1_placebo"] = {"pick_from_parent": pick["id"],
                                    "guard": [res_p["guard"]["rival_mae"], done_p["guard"]["rival_mae"],
                                              res_p["guard"]["comparator_mae"], done_p["guard"]["comparator_mae"],
                                              res_p["guard"]["passed"], done_p["guard"]["passed"]],
                                    "raw_vs_preds_file": nan_max_abs(res_p["raw"], pf_p["raw"].to_numpy()),
                                    "guarded_vs_preds_file": nan_max_abs(res_p["guarded"], pf_p["guarded"].to_numpy())}
    log("extra placebo: %s" % extra["merra2_lag1_placebo"])
    report["extra_validation_locked"] = extra
    del recs_s, res_s, res_p

    # ================================================================== 1-5: the corrected input (OC x1.0)
    results = {}
    report["x_change_test_rows"] = {}
    for fname in ("oc1", "oc1_so4gmao"):
        report["x_change_test_rows"][fname] = {rid: x_change(xs[rid][fname][C.test_pos], x_lock_test[rid])
                                               for rid in RIVALS}
    report["x_change_all_index_rows_oc1"] = {rid: x_change(xs[rid]["oc1"], xs[rid]["index"]) for rid in RIVALS}
    log("x change (test rows, oc1): %s" % report["x_change_test_rows"]["oc1"]["merra2_lag1"])

    # (i) merra2_lag1 full procedure
    log("step 2(i): merra2_lag1 corrected input, all candidates")
    recs_n = run_trials(C, xs["merra2_lag1"]["oc1"], cands)
    pick_n = pick_of(recs_n)
    res_n = guard_and_refit(C, xs["merra2_lag1"]["oc1"], pick_n, pick_n["pick_mae"])
    results["merra2_lag1__oc1_full"] = variant_record(C, "merra2_lag1", "oc1_full", res_n, recs_n, pick_n,
                                                      x_lock_test["merra2_lag1"], selection="full pick")
    log("  (i) pick %s guard %s" % (pick_n["id"], res_n["guard"]))
    # (ii) forced F5 log_c
    f5 = [cd for cd in cands if cd["family"] == "F5" and cd["link"] == "log_c"][0]
    f5_trial = [r for r in recs_n if r["id"] == f5["id"]][0]
    res_f = guard_and_refit(C, xs["merra2_lag1"]["oc1"], f5, f5_trial["pick_mae"])
    results["merra2_lag1__oc1_forcedF5logc"] = variant_record(C, "merra2_lag1", "oc1_forcedF5logc", res_f, None,
                                                              None, x_lock_test["merra2_lag1"],
                                                              selection="forced: the locked family F5 log_c")
    log("  (ii) forced F5 log_c guard %s" % res_f["guard"])
    # step 3: merra2_same full; placebo through the parent's (corrected) pick
    log("step 3: merra2_same corrected input, all candidates")
    recs_sn = run_trials(C, xs["merra2_same"]["oc1"], cands)
    pick_sn = pick_of(recs_sn)
    res_sn = guard_and_refit(C, xs["merra2_same"]["oc1"], pick_sn, pick_sn["pick_mae"])
    results["merra2_same__oc1_full"] = variant_record(C, "merra2_same", "oc1_full", res_sn, recs_sn, pick_sn,
                                                      x_lock_test["merra2_same"], selection="full pick")
    log("  same pick %s guard %s" % (pick_sn["id"], res_sn["guard"]))
    res_pn = guard_and_refit(C, xs["merra2_lag1_placebo"]["oc1"], pick_n)
    results["merra2_lag1_placebo__oc1_full"] = variant_record(C, "merra2_lag1_placebo", "oc1_full", res_pn, None,
                                                              None, x_lock_test["merra2_lag1_placebo"],
                                                              selection="parent's pick (placebo_of merra2_lag1)")
    results["merra2_lag1_placebo__oc1_full"]["pick_rule"] = (
        "placebo: takes its parent's pick (board lock: placebo_of merra2_lag1), here the parent's corrected-input "
        "pick %s; fitted on the placebo's own corrected x" % pick_n["id"])
    log("  placebo guard %s" % res_pn["guard"])
    # side check: sulfate 132.14/96.06, forced F5 log_c only (one line)
    res_g = guard_and_refit(C, xs["merra2_lag1"]["oc1_so4gmao"], f5)
    side = variant_record(C, "merra2_lag1", "oc1_so4gmao_forcedF5logc", res_g, None, None,
                          x_lock_test["merra2_lag1"], save=True,
                          selection="side check: OC x1.0 and SO4 x 132.14/96.06, forced F5 log_c")
    results["merra2_lag1__oc1_so4gmao_forcedF5logc"] = side
    report["results"] = results
    report["inputs_sha256"] = dict(sorted(INPUTS.items()))
    report["seconds"] = time.time() - T0
    with open(OUT_DIR / "result_B.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1, allow_nan=True, default=_jsonable)
    # ---- plain summary
    print("\n==== SUMMARY (post hoc; locked verdicts unchanged) ====")
    print("gate 0a max rel diff: %s" % {r: gate0a[r]["max_rel_diff"] for r in RIVALS})
    print("gate 0b passed: %s (trials bit-exact %s, guarded max abs diff %r)" % (ok0b, tr_exact,
                                                                                preds_cmp["guarded"]["max_abs_diff"]))
    print("gate 0c passed: %s (max abs diff %r)" % (g0c["passed"], worst))
    for k, r in results.items():
        cg = r["score"]["guarded_vs_headline"]
        e = r.get("extremes", {})
        print("%-42s %s %s | guard %.6f vs %.6f %s | test rival %.6f ours %.6f | d %+.6f [%+.6f, %+.6f] %s | "
              "max %.2f, >1000: %s" % (k, r["picked_family"], r["picked_link"], r["guard"]["rival_mae"],
                                       r["guard"]["comparator_mae"], "PASS" if r["guard"]["passed"] else "FAIL",
                                       cg["rival_mae"], cg["ours_mae_same_rows"], cg["d_mean"], cg["d_low"],
                                       cg["d_high"], cg["verdict"],
                                       e.get("largest_guarded_forecast", {}).get("value_ug_m3", float("nan")),
                                       e.get("count_guarded_gt_1000")))
    print("result: %s" % (OUT_DIR / "result_B.json"))


def _jsonable(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def _dump_partial(report):
    report["inputs_sha256"] = dict(sorted(INPUTS.items()))
    p = OUT_DIR / "result_B.partial.json"
    n = 0
    while p.exists():
        n += 1
        p = OUT_DIR / ("result_B.partial_%d.json" % n)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1, allow_nan=True, default=_jsonable)


if __name__ == "__main__":
    main()
