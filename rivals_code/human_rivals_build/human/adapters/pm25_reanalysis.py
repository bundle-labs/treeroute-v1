"""PM2.5 human rivals: monthly reanalysis surface PM2.5 (CAMS EAC4, MERRA-2) on the export's rows.

SPEC_HUMAN.txt section 4 (Builder C). Kind N (already in target units). One index table per rival x lead
(SPEC_HUMAN 1.4): keys, x__<stat>, info_end, target_obs_end, product_cell, src.

Plain idea: for each row (unit, time t, issue i, lead L) read the product's month m = i + month_offset
(registry option; -1 for the parity P row "t-1", 0 for the same-month A row), bilinearly interpolate the
product field at the unit centre, and multiply to ug m-3. Nothing here reads a label: info_end = m and
target_obs_end = m (both reanalyses assimilate MODIS AOD, the target's own source; SPEC_HUMAN 4). The tool's
`check` decides from those two columns whether the row is P (passes T1/T2) or A (must break one).

The placebo (SPEC_HUMAN 4 "Placebo"; research_pm25.md section 3): the same unit and calendar month, the product
of PLACEBO_SHIFT_YEARS earlier (m' = m - 12 x shift). A row whose m' has no product file is not covered. Never
a later year, so the placebo never reads past its own row's month (it passes T1/T2 like the P row it shadows).

EAC4 is NOT on disk until D1 is fetched: availability() says "waiting for D1" and build() REFUSES with the
plain line of the rival's registry option `missing_message` (SPEC_HUMAN 4 Inputs).

The AdapterCtx calls used here (builder A's contract, BUILD_NOTES_shared.txt "ADAPTER CONTRACT"; requests in
BUILD_NOTES_pm25_ndvi.txt):
  ctx.run                       the common harness Run (H:451-560): .derived (R17 steps_per_year)
  ctx.keys("stage")             keys (unit, group, time, issue, lead) of every row of this index-table stage
  ctx.product_available(pid)    True when the product's manifest exists (requested; see availability())
  ctx.product_files(pid)        the file names the product manifest lists
  ctx.open_product(pid, name)   the path of one manifest-listed file, after its sha256 check
  ctx.log(message)              one plain log line
Unit centres are a product too (the engine's static cell table, registry option unit_centres.product), so their
file is sha-checked like any product file.
No `import` of the common harness, the engine or rivals.py / pm25_rivals.py (their clip caps at 1, PROT:194).
"""
import io
import math
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

ADAPTER_FORMAT = "human-adapter-pm25-reanalysis/1"
KEYS = ("unit", "group", "time", "issue", "lead")
X_PREFIX = "x__"
PLACEBO_SHIFT_YEARS = 4          # old MP arm (pm25_products_map.py:9-13): 4 years earlier; pre-registered
MONTHS_PER_YEAR = 12
GRID_TOL = 1e-6                  # regular-grid check on the product axes (degrees)
DEFAULT_MISSING = "product %s is not on disk (no product_manifest.json): fetch and hash it first"
READERS = ("monthly_files", "netcdf_zip")


class Pm25AdapterRefusal(RuntimeError):
    """A PM2.5 adapter rule refused (fail loud; nothing catches it)."""


def _refuse(message: str, fix: Optional[str] = None):
    raise Pm25AdapterRefusal(message + ("" if not fix else "  FIX: " + fix))


# ---------------------------------------------------------------------------------------------------
# Steps and months. The engine's step index: year x steps_per_year + position (1..steps_per_year)
# (treeroute/fit/context.py:264-277 season_keys_of; checked on the pm25 run: test times 24241..24288 =
# 2020-01..2023-12, test_preds.parquet `year`).
def steps_per_year(run: Any) -> int:
    spy = int(run.derived["R17"]["inputs"]["steps_per_year"])
    if spy != MONTHS_PER_YEAR:
        _refuse("the run has %d steps per year; a monthly reanalysis rival needs a monthly run (12)" % spy)
    return spy


def step_to_year_month(step: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    s = np.asarray(step, dtype=np.int64)
    return (s - 1) // MONTHS_PER_YEAR, (s - 1) % MONTHS_PER_YEAR + 1


def year_month_to_step(year: Any, month: Any) -> np.ndarray:
    return np.asarray(year, dtype=np.int64) * MONTHS_PER_YEAR + np.asarray(month, dtype=np.int64)


# ---------------------------------------------------------------------------------------------------
# Rival options (registry/<pkg>.yaml `options`; data, not code)
def _options(rival: Mapping[str, Any]) -> Dict[str, Any]:
    opt = dict(rival.get("options") or {})
    for k in ("product", "reader", "variables", "scale", "month_offset", "unit_centres", "units_attr"):
        if k not in opt:
            _refuse("rival %s: registry options lack %r" % (rival.get("id"), k))
    if opt["reader"] not in READERS:
        _refuse("rival %s: unknown reader %r (known: %s)" % (rival.get("id"), opt["reader"], ", ".join(READERS)))
    if opt["reader"] == "monthly_files" and "file_pattern" not in opt:
        _refuse("rival %s: reader monthly_files needs options.file_pattern" % rival.get("id"))
    stats = list(rival.get("stats") or [])
    if len(stats) != 1:
        _refuse("rival %s: a reanalysis rival has exactly one stat (the monthly mean), got %s" % (rival.get("id"), stats))
    opt["stat"] = str(stats[0]) if str(stats[0]).startswith(X_PREFIX) else X_PREFIX + str(stats[0])
    opt["month_offset"] = int(opt["month_offset"])
    opt["placebo_shift_years"] = int(opt.get("placebo_shift_years", 0) or 0)
    if opt["placebo_shift_years"] < 0:
        _refuse("rival %s: placebo_shift_years must be >= 0" % rival.get("id"))
    return opt


def product_available(ctx: Any, pid: str) -> bool:
    """True when the product's manifest exists (never refuses). ctx.product_available when the ctx has it
    (requested from builder A); else the tool's own rivals_human.index.product_status(ctx.cfg, ctx.products, pid)."""
    f = getattr(ctx, "product_available", None)
    if f is not None:
        return bool(f(pid))
    if hasattr(ctx, "cfg") and hasattr(ctx, "products"):
        from rivals_human import index as _ix
        ok, _line = _ix.product_status(ctx.cfg, ctx.products, pid)
        return bool(ok)
    _refuse("the adapter ctx offers no way to ask whether product %s is on disk" % pid)


def availability(ctx: Any, rival: Mapping[str, Any]) -> Tuple[bool, str]:
    """(on disk?, plain line). `init` lists a rival whose product is missing as waiting (SPEC_HUMAN 4)."""
    opt = _options(rival)
    pid = opt["product"]
    if not product_available(ctx, pid):
        return False, str(opt.get("missing_message") or DEFAULT_MISSING % pid)
    return True, "product %s on disk" % pid


def require_product(ctx: Any, rival: Mapping[str, Any]) -> List[str]:
    """The product's file names; refuses with the registry's plain line when the product is not on disk."""
    ok, line = availability(ctx, rival)
    if not ok:
        _refuse(line)
    return sorted(str(n) for n in ctx.product_files(_options(rival)["product"]))


# ---------------------------------------------------------------------------------------------------
# Unit centres (SPEC_HUMAN 4: every slim unit must match one cell_id of the engine's static table)
def unit_centres(ctx: Any, rival: Mapping[str, Any], units: Sequence[str]) -> pd.DataFrame:
    import pyarrow.dataset as ds

    uc = _options(rival)["unit_centres"]
    path = Path(str(ctx.open_product(str(uc["product"]), str(uc["file"]))))
    idc, latc, lonc = str(uc["id"]), str(uc["lat"]), str(uc["lon"])
    want = sorted(set(str(u) for u in units))
    tab = ds.dataset(str(path), format="parquet").to_table(
        columns=[idc, latc, lonc], filter=ds.field(idc).isin(want)).to_pandas()
    if tab[idc].duplicated().any():
        _refuse("unit centres file %s names a cell twice (%s)" % (path, tab.loc[tab[idc].duplicated(), idc].iloc[0]))
    missing = sorted(set(want) - set(tab[idc].astype(str)))
    if missing:
        _refuse("%d unit(s) match no %s in %s (first %s)" % (len(missing), idc, path, missing[:3]))
    out = tab.rename(columns={idc: "unit", latc: "lat", lonc: "lon"}).set_index("unit").loc[want].reset_index()
    if not (np.isfinite(out["lat"]).all() and np.isfinite(out["lon"]).all()):
        _refuse("unit centres hold a missing latitude or longitude")
    return out


# ---------------------------------------------------------------------------------------------------
# The product grid and bilinear interpolation (research_pm25.md section 3; R-PM:113-117)
class Grid(object):
    """A regular global lat/lon grid with ascending axes (latitude may arrive north->south: flipped)."""

    def __init__(self, lat: np.ndarray, lon: np.ndarray):
        lat = np.asarray(lat, dtype=np.float64)
        lon = np.asarray(lon, dtype=np.float64)
        self.flip_lat = bool(lat.size > 1 and lat[1] < lat[0])
        self.lat = lat[::-1].copy() if self.flip_lat else lat.copy()
        order = np.argsort(np.mod(lon, 360.0), kind="stable")
        self.lon_order = order
        self.lon = np.mod(lon, 360.0)[order]
        for name, ax in (("latitude", self.lat), ("longitude", self.lon)):
            if ax.size < 2:
                _refuse("product %s axis has %d value(s)" % (name, ax.size))
            d = np.diff(ax)
            if not (np.abs(d - d[0]) <= GRID_TOL).all() or d[0] <= 0:
                _refuse("product %s axis is not regular and ascending" % name)
        # the step over the FULL span (a float32 axis makes lat[1] - lat[0] drift; same fix as coral_crw OfficialMmm)
        self.dlat = float((self.lat[-1] - self.lat[0]) / (self.lat.size - 1))
        self.dlon = float((self.lon[-1] - self.lon[0]) / (self.lon.size - 1))
        if abs(self.lon.size * self.dlon - 360.0) > 1e-4:
            _refuse("product longitude axis does not close the globe (%d x %.6f deg); the wrap needs a global grid"
                    % (self.lon.size, self.dlon))

    def orient(self, field: np.ndarray) -> np.ndarray:
        """A (lat, lon) field in the product's own axis order -> ascending axes."""
        f = np.asarray(field, dtype=np.float64)
        if f.shape != (self.lat.size, self.lon.size):
            _refuse("product field shape %s differs from its axes (%d, %d)" % (f.shape, self.lat.size, self.lon.size))
        if self.flip_lat:
            f = f[::-1, :]
        return f[:, self.lon_order]

    def weights(self, qlat: np.ndarray, qlon: np.ndarray) -> Dict[str, np.ndarray]:
        """Bilinear corner indices and weights. Longitude wraps at the seam; latitude beyond the first or last
        row is held at that row (pre-registered)."""
        qlat = np.asarray(qlat, dtype=np.float64)
        qlon = np.asarray(qlon, dtype=np.float64)
        fi = (qlat - self.lat[0]) / self.dlat
        i0 = np.clip(np.floor(fi).astype(np.int64), 0, self.lat.size - 2)
        wi = np.clip(fi - i0, 0.0, 1.0)
        fj = np.mod(qlon - self.lon[0], 360.0) / self.dlon
        j0 = np.floor(fj).astype(np.int64) % self.lon.size
        wj = fj - np.floor(fj)
        j1 = (j0 + 1) % self.lon.size
        return {"i0": i0, "i1": i0 + 1, "j0": j0, "j1": j1, "wi": wi, "wj": wj}

    @staticmethod
    def interpolate(field: np.ndarray, w: Mapping[str, np.ndarray]) -> np.ndarray:
        """Bilinear value; a missing corner makes the value missing (no renormalisation; pre-registered)."""
        f = field
        return ((1 - w["wi"]) * (1 - w["wj"]) * f[w["i0"], w["j0"]] + (1 - w["wi"]) * w["wj"] * f[w["i0"], w["j1"]]
                + w["wi"] * (1 - w["wj"]) * f[w["i1"], w["j0"]] + w["wi"] * w["wj"] * f[w["i1"], w["j1"]])

    @staticmethod
    def box_id(w: Mapping[str, np.ndarray]) -> np.ndarray:
        """The product grid box holding the point (ascending-axis corner indices): the resolution-matched key."""
        return np.array(["r%d_c%d" % (a, b) for a, b in zip(w["i0"], w["j0"])], dtype=object)


def _axis(ds: Any, names: Sequence[str]) -> np.ndarray:
    for n in names:
        if n in ds.variables:
            return np.asarray(ds.variables[n][:], dtype=np.float64)
    _refuse("product file has none of the axes %s" % list(names))


def _months_of(ds: Any) -> List[Tuple[int, int]]:
    import netCDF4

    for n in ("valid_time", "time", "forecast_reference_time"):
        if n in ds.variables:
            v = ds.variables[n]
            dates = netCDF4.num2date(v[:], v.units, getattr(v, "calendar", "standard"))
            return [(int(d.year), int(d.month)) for d in np.atleast_1d(dates)]
    _refuse("product file has no time coordinate (valid_time / time / forecast_reference_time)")


def _check_units(var: Any, name: str, want: str):
    got = str(getattr(var, "units", "")).replace("**", "").replace("^", "").strip()
    if got.replace(" ", "") != str(want).replace(" ", ""):
        _refuse("product variable %s has units %r; the registry expects %r" % (name, getattr(var, "units", None), want))


def _field(ds: Any, k: int, opt: Mapping[str, Any]) -> np.ndarray:
    """sum(weight x variable) at time index k, in product units (masked/fill -> NaN)."""
    total = None
    for name, wgt in dict(opt["variables"]).items():
        if name not in ds.variables:
            _refuse("product file lacks the variable %s" % name)
        var = ds.variables[name]
        _check_units(var, name, opt["units_attr"])
        a = var[k] if var.ndim == 3 else var[:]
        a = np.ma.filled(np.ma.asarray(a, dtype=np.float64), np.nan)
        a = np.squeeze(a)
        total = float(wgt) * a if total is None else total + float(wgt) * a
    return total


class Product(object):
    """Month -> (opened dataset, time index). Opens the manifest-listed files only (each after its sha256 check
    by ctx.open_product)."""

    def __init__(self, ctx: Any, rival: Mapping[str, Any]):
        import netCDF4

        self.opt = _options(rival)
        self.pid = self.opt["product"]
        names = require_product(ctx, rival)
        if not names:
            _refuse("product %s: its manifest lists no file" % self.pid)
        self._ds: Dict[str, Any] = {}
        self.where: Dict[Tuple[int, int], Tuple[str, int]] = {}
        self.grid: Optional[Grid] = None
        if self.opt["reader"] == "monthly_files":
            for name in names:
                ym = _parse_pattern(str(self.opt["file_pattern"]), name)
                if ym is None:
                    continue
                path = ctx.open_product(self.pid, name)
                ds = netCDF4.Dataset(str(path), "r")
                self._add(name, ds, expect=ym)
        else:
            for name in names:
                if not name.lower().endswith(".zip"):
                    continue
                path = ctx.open_product(self.pid, name)
                with zipfile.ZipFile(str(path), "r") as zf:
                    for member in sorted(zf.namelist()):
                        if not member.lower().endswith(".nc"):
                            continue
                        data = zf.read(member)
                        ds = netCDF4.Dataset("%s::%s" % (name, member), mode="r", memory=data)
                        self._add("%s::%s" % (name, member), ds, expect=None)
        if not self.where:
            _refuse("product %s: no month found in its files" % self.pid)
        ctx.log("product %s: %d months %04d-%02d..%04d-%02d" % ((self.pid, len(self.where)) + min(self.where)
                                                                + max(self.where)))

    def _add(self, name: str, ds: Any, expect: Optional[Tuple[int, int]]):
        lat = _axis(ds, ("lat", "latitude"))
        lon = _axis(ds, ("lon", "longitude"))
        g = Grid(lat, lon)
        if self.grid is None:
            self.grid = g
        elif not (np.array_equal(g.lat, self.grid.lat) and np.array_equal(g.lon, self.grid.lon)):
            _refuse("product %s: file %s is on another grid" % (self.pid, name))
        months = _months_of(ds)
        if expect is not None and months != [expect]:
            _refuse("product %s: file %s holds months %s, its name says %04d-%02d" % ((self.pid, name, months) + expect))
        self._ds[name] = ds
        for k, ym in enumerate(months):
            if ym in self.where:
                _refuse("product %s: month %04d-%02d appears twice (%s and %s)" % (self.pid, ym[0], ym[1],
                                                                                 self.where[ym][0], name))
            self.where[ym] = (name, k)

    def field(self, year: int, month: int) -> Tuple[Optional[np.ndarray], str]:
        hit = self.where.get((int(year), int(month)))
        if hit is None:
            return None, ""
        name, k = hit
        f = _field(self._ds[name], k, self.opt) * float(self.opt["scale"])
        return self.grid.orient(f), name.split("::")[0]

    def close(self):
        for ds in self._ds.values():
            try:
                ds.close()
            except Exception as exc:          # never swallowed silently
                raise Pm25AdapterRefusal("closing a product file failed: %s" % exc)
        self._ds = {}


def _parse_pattern(pattern: str, name: str) -> Optional[Tuple[int, int]]:
    """'aer_{year:04d}{month:02d}.nc' -> (year, month) of a matching file name, else None."""
    import re

    rx = re.escape(pattern).replace(re.escape("{year:04d}"), r"(?P<year>\d{4})").replace(
        re.escape("{month:02d}"), r"(?P<month>\d{2})")
    m = re.fullmatch(rx, name)
    if not m:
        return None
    return int(m.group("year")), int(m.group("month"))


# ---------------------------------------------------------------------------------------------------
# The adapter (SPEC_HUMAN section 6 contract)
def product_months(keys: pd.DataFrame, opt: Mapping[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
    """(m, m_read): the row's product month m = issue + month_offset, and the month actually read (the placebo
    reads m - 12 x placebo_shift_years)."""
    m = keys["issue"].to_numpy(np.int64) + int(opt["month_offset"])
    read = m - MONTHS_PER_YEAR * int(opt["placebo_shift_years"])
    return m, read


def build(ctx: Any, rival: Mapping[str, Any], lead: int, stage: str) -> pd.DataFrame:
    """The index table of one rival x lead (SPEC_HUMAN 1.4)."""
    opt = _options(rival)
    steps_per_year(ctx.run)
    tiers = rival.get("leads") or {}
    tier = (tiers.get(int(lead)) or tiers.get(str(int(lead))) or {}).get("tier")
    if tier in (None, "none"):
        _refuse("rival %s has no row at lead %d (registry: %s)" % (rival.get("id"), int(lead), tier))
    if rival.get("reads_target_in_test_window"):
        _refuse("rival %s: a reanalysis reads no label; reads_target_in_test_window must be false" % rival.get("id"))
    keys = ctx.keys("stage")
    missing = [k for k in KEYS if k not in keys.columns]
    if missing:
        _refuse("index keys lack %s" % missing)
    keys = keys[list(KEYS)].reset_index(drop=True)
    if keys.duplicated(subset=["unit", "time", "issue"]).any():
        _refuse("index keys name a (unit, time, issue) twice")
    if (keys["lead"].to_numpy(np.int64) != int(lead)).any():
        _refuse("index keys hold rows of another lead")
    product = Product(ctx, rival)
    try:
        centres = unit_centres(ctx, rival, keys["unit"].astype(str).unique())
        w = product.grid.weights(centres["lat"].to_numpy(), centres["lon"].to_numpy())
        boxes = Grid.box_id(w)
        upos = pd.Index(centres["unit"].astype(str)).get_indexer(keys["unit"].astype(str))
        m, read = product_months(keys, opt)
        x = np.full(len(keys), np.nan)
        src = np.full(len(keys), "", dtype=object)
        ry, rm = step_to_year_month(read)
        n_missing_month = 0
        for step in np.unique(read):
            rows = np.flatnonzero(read == step)
            f, name = product.field(int(ry[rows[0]]), int(rm[rows[0]]))
            if f is None:
                n_missing_month += rows.size
                continue
            vals = Grid.interpolate(f, w)
            x[rows] = vals[upos[rows]]
            src[rows] = name
        if np.isinf(x).any():
            _refuse("rival %s: the interpolated product holds +-inf" % rival.get("id"))
        covered = np.isfinite(x)
        out = keys.copy()
        out[opt["stat"]] = x
        out["info_end"] = read.astype(np.int64)
        out["target_obs_end"] = np.where(covered, read.astype(np.float64), np.nan)
        out["product_cell"] = boxes[upos]
        out["src"] = np.where(covered, src, "")
        ctx.log("rival %s lead %d stage %s: %d rows, %d covered, %d rows without a product month, month offset %d, "
                "placebo shift %d y" % (rival.get("id"), int(lead), stage, len(out), int(covered.sum()), n_missing_month,
                                        int(opt["month_offset"]), int(opt["placebo_shift_years"])))
        return out
    finally:
        product.close()


__all__ = ["ADAPTER_FORMAT", "PLACEBO_SHIFT_YEARS", "Pm25AdapterRefusal", "availability", "require_product",
           "unit_centres", "product_available", "Grid", "Product", "product_months", "build", "step_to_year_month", "year_month_to_step"]
