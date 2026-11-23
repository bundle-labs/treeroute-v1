"""Fixture builders of the fire (Part B) tests (SPEC_HUMAN_PARTB.txt section 5, builder B3).

Everything a test writes lives under its pytest basetemp (D:/treeroute/human_rivals_build/pt/tests/<fresh>):
  - small subsets of the old CEMS netCDFs in D:/fire/cems/raw (read-only, never written), keeping the RAW layout
    (dims and their order, attrs, latitude descending, 0-360 western longitudes, float32 with NaN fill, the scalar
    `surface` coordinate); the SEAS5 step coordinate is relabelled to the D3 daily leads 150..184 (+ 12 h) and
    valid_time recomputed (= time + step);
  - synthetic long products in the same layout (ERA5 2003-2019, SEAS5 starts 2002-08..2019-02), for the percentile
    and timing tests that need the facts' cuts;
  - fake fetcher folders: the netCDFs + a product_manifest.json in the FETCHER's format (fetch_products.py:724-809:
    files {name: {request_id, bytes, sha256, started, finished, seconds, served_by}}, requests {id: {id, file, request,
    expected_bytes, regions[, starts]}}, complete);
  - the toy unit-centre table: real coordinates of 8 bank units (3 great_plains, 2 cerrado, 3 greece_mainland incl. a
    coastal one), read once from the fire package static table and written below, plus synthetic units;
  - FakeRun / FakeCtx: the AdapterCtx names an adapter or a runner may use (rivals_human/index.py:188-347), with the
    product calls delegated to the tool's own index.product_manifest / product_root / verify_product_file.
No fire label is read: the refs toy (T-F09) writes its own synthetic lat/lon-keyed target store.
"""
# Provenance: SPEC_HUMAN_PARTB.txt 2.2-2.4 (rival options), 3.1-3.7 (adapter rules), 4 (runner contract), 5 (fixtures);
# D:/treeroute/human_tools/fetch_products.py:206-359 (requests, file names), :724-809 (manifest); tests_builder_b/
# conftest.py:21-60 and tests_builder_c/test_pm25_ndvi_adapters.py:279-310 (stand-in ctx style).

import contextlib
import datetime as _dt
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pytest

sys.dont_write_bytecode = True

TESTS_DIR = Path(__file__).resolve().parent
HUMAN_ROOT = TESTS_DIR.parent                                   # D:/treeroute/human_rivals_build/human
WRITE_ROOT = HUMAN_ROOT.parent                                  # D:/treeroute/human_rivals_build
ENGINE_ROOT = Path(os.environ.get("RIVALS_ENGINE_ROOT",
                                  r"C:\Users\<user>\Desktop\data set for reserch paper\engine"))
RAW = Path(r"D:\fire\cems\raw")                                 # read-only: copied in small subsets only
RUN_DIR = Path(r"D:\treeroute\runs\fire\headline\20261017_869d1f38")
EXPORT_DIR = Path(r"D:\treeroute\rival_export\fire\20261017_869d1f38")
PRODUCTION_CONFIG = HUMAN_ROOT / "human_rivals_production.yaml"
TARGET_READER = ENGINE_ROOT / "datasets" / "fire" / "ingest" / "target_reader.py"
MOVED = WRITE_ROOT / "_moved"

KEYS = ["unit", "group", "time", "issue", "lead"]
STATS = ["x__fwi_mean", "x__fwi_pct"]
LINKS = ["identity", "log_c", "arcsine"]
FACT_CUTS = {0: {"fit_cut": 24228, "guard_cut": 24192}, 6: {"fit_cut": 24223, "guard_cut": 24187},
             12: {"fit_cut": 24217, "guard_cut": 24181}}             # RUN derived R11 (spec facts)
TEST_START = 24229                                              # 2019-01: the first test step at every lead
OFFSET = 1                                                      # RUN derived R17 start_offset_steps
FWI_T1 = ["V01_mean_temp_C", "V02_total_precip_mm", "V09_mean_wind_ms", "rmin_pct", "era5l_d2m"]
SPI_T1 = ["spi_01m", "spi_03m", "spi_06m", "spi_12m", "spi_24m"]
SPI_COLS = ["x__" + c for c in SPI_T1]
SEAS_LEADS = list(range(150, 185))                              # FP:81 SEAS_LEADS
EARTH_R = 6371.0
RANDOM_STATE = 20261025                                         # the one fixed random_state of these toys

ERA5_PID = "cems_geff_era5_fwi"
SEAS5_PID = "cems_geff_seas5_fwi"
STATIC_PID = "fire_static_cells"
TARGET_PID = "fire_target_2018"
STORE_PID = "fire_refs_label_store"
ERA5_WAITING = "D2 (CEMS GEFF-ERA5 FWI) is not on disk, not complete or still the UNSET_OD6 placeholder (toy line)"
SEAS5_WAITING = "D3 (CEMS GEFF-SEAS5 FWI) is not on disk, not complete or still the UNSET_OD6 placeholder (toy line)"
ERA5_DATASET = "cems-fire-historical-v1"
SEAS5_DATASET = "cems-fire-seasonal"
ERA5_FOLDER = "geff_era5_v4_1_consolidated_fwi_2003-2022_region"
SEAS5_FOLDER = "geff_seas5_r5_fwi_starts200208-202207_L150-184_region_y1"


def step(y: int, m: int) -> int:
    """The run's step: year x 12 + month (24037 = 2003-01; spec facts)."""
    return int(y) * 12 + int(m)


def year_month(s: int) -> Tuple[int, int]:
    s = int(s)
    return (s - 1) // 12, (s - 1) % 12 + 1


def days_in(y: int, m: int) -> int:
    nxt = _dt.date(y + (m == 12), m % 12 + 1, 1)
    return (nxt - _dt.date(y, m, 1)).days


def sha256_file(path: Any) -> str:
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_json(path: Any, obj: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return p


def read_json(path: Any) -> Any:
    with open(str(path), "r", encoding="utf-8") as fh:
        return json.load(fh)


# ===================================================================================================== refusals
INTERFACE_ERRORS = (TypeError, AttributeError, NameError, ImportError, NotImplementedError, SyntaxError,
                    UnboundLocalError, KeyError, IndexError)


def tool_refusals() -> tuple:
    from rivals_human.common import HumanRefusal
    from rivals_human.config import ConfigRefusal
    return HumanRefusal, ConfigRefusal


def refuses(fn: Callable, *args: Any, kinds: Optional[tuple] = None, words: Sequence[str] = (), **kwargs: Any):
    """fn must refuse: raise an exception that is not an interface error (a TypeError / KeyError / ... is a broken
    call, never a refusal; tests_builder style, hooks.refuses). kinds: the refusal classes allowed (default: any
    other exception); words: one of them must appear in the message (case-insensitive). Returns the exception."""
    try:
        fn(*args, **kwargs)
    except INTERFACE_ERRORS as exc:
        pytest.fail("expected a refusal; got an interface error %s: %s" % (type(exc).__name__, exc))
    except Exception as exc:                          # the refusal classes; checked below
        if kinds is not None and not isinstance(exc, kinds):
            pytest.fail("expected a refusal of %s; got %s: %s" % ([k.__name__ for k in kinds], type(exc).__name__, exc))
        if words:
            low = str(exc).lower()
            assert any(str(w).lower() in low for w in words), "refused, but the message names none of %s: %s" % (
                list(words), exc)
        return exc
    pytest.fail("expected a refusal; %s returned normally" % getattr(fn, "__name__", fn))


# ===================================================================================================== geometry
def haversine(lat1: Any, lon1: Any, lat2: Any, lon2: Any) -> np.ndarray:
    """Great-circle km on a sphere of 6371 km (the hand oracle of fire_geff.haversine_km; inputs cast first)."""
    p1, p2 = np.radians(np.asarray(lat1, np.float64)), np.radians(np.asarray(lat2, np.float64))
    dl = np.radians(np.asarray(lon2, np.float64) - np.asarray(lon1, np.float64))
    a = np.sin((p2 - p1) / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2.0) ** 2
    return 2.0 * EARTH_R * np.arcsin(np.sqrt(np.minimum(a, 1.0)))


def expected_point(grid_lat: Sequence[float], grid_lon: Sequence[float], valid: np.ndarray, lat: float, lon: float,
                   window: int) -> Dict[str, Any]:
    """Brute force of spec 3.3 for one unit: the nearest point by haversine over ALL points (first minimum in
    latitude-major order); a sea (invalid) nearest point takes the nearest VALID point inside |di|, |dj| <= window;
    none -> uncovered."""
    gl = np.asarray(grid_lat, np.float64)
    go = np.asarray(grid_lon, np.float64)
    LA, LO = np.meshgrid(gl, go, indexing="ij")
    d = haversine(lat, lon, LA, LO)
    k = int(np.argmin(d.ravel()))
    i, j = divmod(k, go.size)
    if valid[i, j]:
        return {"i": i, "j": j, "substituted": False, "uncovered": False, "dist_km": float(d[i, j])}
    best = None
    for ii in range(max(0, i - window), min(gl.size, i + window + 1)):
        for jj in range(max(0, j - window), min(go.size, j + window + 1)):
            if valid[ii, jj] and (best is None or d[ii, jj] < d[best]):
                best = (ii, jj)
    if best is None:
        return {"i": i, "j": j, "substituted": False, "uncovered": True, "dist_km": float("nan")}
    return {"i": best[0], "j": best[1], "substituted": True, "uncovered": False, "dist_km": float(d[best])}


def wrap(lon: Any) -> np.ndarray:
    return np.mod(np.asarray(lon, np.float64) + 180.0, 360.0) - 180.0


# ===================================================================================================== units
# Real bank units, read once (2026-10-25) from engine/datasets/fire/data/static/part-0.parquet (float64 lat / lon kept
# exactly) and EXP lead_0/units.parquet (is_scored). Coordinates only: no label.
REAL_UNITS = [
    ("great_plains_-2866_1182", "great_plains", 39.0581169128418, -102.96489715576172, -2866, 1182, True),
    ("great_plains_-2861_1172", "great_plains", 38.77854919433594, -102.78523254394531, -2861, 1172, True),
    ("great_plains_-2834_1212", "great_plains", 39.89020538330078, -101.81505584716797, -2834, 1212, True),
    ("cerrado_-1529_-427", "cerrado", -15.145723342895508, -54.922996520996094, -1529, -427, True),
    ("cerrado_-1500_-429", "cerrado", -15.215080261230469, -53.880950927734375, -1500, -429, True),
    ("greece_mainland_603_1131", "greece_mainland", 37.62083435058594, 21.685331344604492, 603, 1131, True),
    ("greece_mainland_604_1146", "greece_mainland", 38.0465202331543, 21.721263885498047, 604, 1146, True),
    ("greece_mainland_595_1135", "greece_mainland", 37.734588623046875, 21.397871017456055, 595, 1135, False),  # coast
]
GREECE_SHIFT = (256.00 - 20.75) - 360.0                         # the ERA5 western copy: lon 20.75 -> 256.00 (-104.0)
SYN_UNITS = [
    # a greece unit whose nearest 0.25-deg point (37.25, 20.75) is sea: substituted inside the 5 x 5 window
    ("greece_mainland_syn_sea", "greece_mainland", 37.27, 20.80, 0, 0, True),
    # the prime-meridian copy (lon 358.75 .. 0.5, non-monotonic in 0-360)
    ("prime_m020", "prime_meridian", 37.6, -0.2, 0, 0, True),
    ("prime_m010", "prime_meridian", 37.6, -0.1, 0, 0, True),
    ("prime_p010", "prime_meridian", 37.6, 0.1, 0, 0, True),
    ("prime_p020", "prime_meridian", 37.6, 0.2, 0, 0, False),
    # the synthetic long products (ERA5 0.25 deg 11.0..10.0 x 20.0..21.0; SEAS5 1 deg 11/10 x 20/21)
    ("synth_a", "synth_region", 10.9, 20.1, 0, 0, True),
    ("synth_b", "synth_region", 10.2, 20.9, 0, 0, True),
    ("synth_c", "synth_region", 10.1, 20.2, 0, 0, False),        # ERA5: nearest point (10.0, 20.25) is sea
]
SYN_UNITS += [("west_" + u, "greece_west", la, lo + GREECE_SHIFT, ix, iy, sc)
              for (u, g, la, lo, ix, iy, sc) in REAL_UNITS + SYN_UNITS[:1] if g == "greece_mainland"]


def static_table() -> pd.DataFrame:
    rows = REAL_UNITS + SYN_UNITS
    return pd.DataFrame({"cell_id": [r[0] for r in rows], "region": [r[1] for r in rows],
                         "lat": np.array([r[2] for r in rows], np.float64),
                         "lon": np.array([r[3] for r in rows], np.float64),
                         "grid_ix": np.array([r[4] for r in rows], np.int64),
                         "grid_iy": np.array([r[5] for r in rows], np.int64)})


def units_of(groups: Sequence[str], extra: Sequence[Tuple[str, str, bool]] = ()) -> pd.DataFrame:
    """units.parquet of a toy slim (unit, group, is_scored, seen_during_design) for the named groups."""
    rows = [(r[0], r[1], bool(r[6])) for r in REAL_UNITS + SYN_UNITS if r[1] in groups] + list(extra)
    return pd.DataFrame({"unit": [r[0] for r in rows], "group": [r[1] for r in rows],
                         "is_scored": [bool(r[2]) for r in rows], "seen_during_design": [False] * len(rows)})


def unit_coords(unit: str) -> Tuple[float, float]:
    for r in REAL_UNITS + SYN_UNITS:
        if r[0] == unit:
            return float(r[2]), float(r[3])
    raise KeyError(unit)


# ===================================================================================================== keys
SET_FLAG = {"refit": "r_refit", "tune": "r_tune", "inner": "r_inner", "guardfit": "r_guardfit", "guard": "r_guard"}


def key_table(units: pd.DataFrame, times: Iterable[int], lead: int, cuts: Mapping[int, Mapping[str, int]],
              offset: int = OFFSET, test_start: Optional[int] = None) -> pd.DataFrame:
    """Slim-like keys of one lead: one row per (unit, target time), issue = time - lead, with the role flags of the
    export (spec facts, EXP roles): refit t <= fit_cut - offset; tune (lead 0) / guardfit (lead >= 1) t <= guard_cut -
    offset; inner / guard: nowcast guard cut < t <= fit_cut - offset; test t >= test_start (default fit_cut + 1);
    the steps between are held by no set (as Dec 2018 at lead 0)."""
    L = int(lead)
    fit, gc = int(cuts[L]["fit_cut"]), int(cuts[L]["guard_cut"])
    g0 = int(cuts[0]["guard_cut"]) if 0 in cuts else gc
    ts = int(test_start) if test_start is not None else fit + 1
    rows = []
    for u, g in zip(units["unit"].astype(str), units["group"].astype(str)):
        for t in times:
            rows.append((u, g, int(t)))
    k = pd.DataFrame(rows, columns=["unit", "group", "time"])
    k["time"] = k["time"].astype(np.int64)
    k["issue"] = (k["time"] - L).astype(np.int64)
    k["lead"] = np.int64(L)
    t = k["time"].to_numpy(np.int64)
    k["r_refit"] = t <= fit - offset
    side = t <= gc - offset
    mid = (t > g0) & (t <= fit - offset)
    k["r_tune"] = side if L == 0 else False
    k["r_guardfit"] = side if L != 0 else False
    k["r_inner"] = mid if L == 0 else False
    k["r_guard"] = mid if L != 0 else False
    k["is_test"] = t >= ts
    keep = k["r_refit"].to_numpy() | k["is_test"].to_numpy()
    return k[keep].reset_index(drop=True)


def keys_of(table: pd.DataFrame, name: str) -> pd.DataFrame:
    if name == "train":
        sel = ~table["is_test"].to_numpy(bool)
    elif name == "test":
        sel = table["is_test"].to_numpy(bool)
    elif name == "all":
        return pd.concat([keys_of(table, "train"), keys_of(table, "test")], ignore_index=True)
    elif name in SET_FLAG:
        sel = table[SET_FLAG[name]].to_numpy(bool)
    else:
        raise ValueError("unknown set %r" % name)
    out = table.loc[sel, KEYS].reset_index(drop=True)
    for c in ("time", "issue", "lead"):
        out[c] = out[c].astype(np.int64)
    out["unit"] = out["unit"].astype(str)
    out["group"] = out["group"].astype(str)
    return out


# ===================================================================================================== run and ctx
def fact_r8(**steps: int) -> Dict[str, Dict[str, int]]:
    """RUN derived R8 `steps` of the columns the fire rivals name (spec facts), with overrides."""
    r8 = {c: {"steps": 0} for c in ["V01_mean_temp_C", "V02_total_precip_mm", "V05_mean_vpd_kPa", "V09_mean_wind_ms",
                                    "rmin_pct", "era5l_d2m"] + SPI_T1}
    r8.update({"oni": {"steps": 3}, "tni": {"steps": 3}, "nino12": {"steps": 2}, "nino3": {"steps": 2},
               "nino34": {"steps": 2}, "nino4": {"steps": 2}})
    for k, v in steps.items():
        r8[k] = {"steps": int(v)}
    return r8


class FakeRun(object):
    """What the adapters, runners, index.Timing and methods read of an H.Run: cuts, derived R2 / R8 / R17, plan."""

    def __init__(self, cuts: Optional[Mapping[int, Mapping[str, int]]] = None, r8: Optional[Mapping[str, Any]] = None,
                 offset: int = OFFSET, plan: Optional[Mapping[str, Any]] = None):
        self.cuts = {int(L): dict(v) for L, v in (cuts or FACT_CUTS).items()}
        self.leads = sorted(self.cuts)
        self.derived = {"R2": {"value": {"kind": "month_of_year", "steps_per_year": 12}},
                        "R8": {"value": dict(r8 if r8 is not None else fact_r8())},
                        "R17": {"inputs": {"steps_per_year": 12}, "value": {"start_offset_steps": int(offset)}}}
        self.plan = dict(plan or {"history_columns": ["hist_last_1", "hist_last_2", "hist_last_3", "hist_mean_12",
                                                      "hist_mean_60", "hist_mean_all"], "links": list(LINKS)})
        self.links = list(LINKS)
        self.legal = (0.0, 1.0)
        self.ub = 1.0
        self.fingerprint = "toy_fire_fingerprint"
        self.package = "fire"
        self.name = "toy_fire_run"
        self.folder = Path("toy_fire_run")

    def c(self, lead: int) -> float:
        return 0.012987012987012988


class FakeCtx(object):
    """A stand-in of rivals_human.index.AdapterCtx (spec 1.2 / 1.3 names) on toy folders. Product calls go through the
    tool's own index functions (manifest refusals, sha256 check of every opened file); keys come from a slim-like key
    table; runner sets from `sets` (features never carry y; fit_labels answers only its own fit set inside a fit scope,
    opened by _fitting as methods.run_fit does for the real ctx)."""

    FIT_SETS = ("refit", "tune", "guardfit")

    def __init__(self, base: Path, run: FakeRun, rival: Mapping[str, Any], lead: int, stage: str = "all",
                 products: Optional[Mapping[str, Mapping[str, Any]]] = None, key_table: Optional[pd.DataFrame] = None,
                 units: Optional[pd.DataFrame] = None, sets: Optional[Mapping[str, Mapping[str, Any]]] = None):
        from rivals_human import index as IX
        self.base = Path(base)
        self.run = run
        self.rival = dict(rival)
        self.lead = int(lead)
        self.stage = stage
        self.products = {k: dict(v) for k, v in (products or {}).items()}
        self.cfg = {"out_root": str(self.base / "_hout"), "on_disk_products": str(self.base / "_toy_products.yaml")}
        self._table = key_table
        self._units = units
        self._sets = dict(sets or {})
        self.opened: Dict[str, Dict[str, str]] = {}
        self.log_lines: List[str] = []
        self.label_calls: List[str] = []
        self.feature_calls: List[str] = []
        self.extra_listed: Dict[str, List[str]] = {}
        self._fit_set: Optional[str] = None
        self.timing = IX.Timing(run, rival, lead)
        self.season = {"kind": "month_of_year", "steps_per_year": 12}
        self.steps_per_year = 12
        self.is_table = False

    # --- refusals: the tool's own class -----------------------------------------------------------
    @staticmethod
    def _refuse(message: str):
        from rivals_human.common import refuse
        refuse(message)

    # --- rows -------------------------------------------------------------------------------------
    def keys(self, set_name: str = "stage") -> pd.DataFrame:
        if set_name == "stage":
            set_name = {"all": "all", "train": "train", "test": "test"}[self.stage]
        if set_name in ("test", "all") and self.stage == "train":
            self._refuse("stage train of rival %s may not read test keys" % self.rival.get("id"))
        if set_name in self._sets:
            return self._sets[set_name]["keys"][KEYS].copy()
        if self._table is None:
            self._refuse("the toy ctx holds no key table")
        return keys_of(self._table, set_name)

    def units(self) -> pd.DataFrame:
        return self._units.copy()

    def extras(self, set_name: str) -> pd.DataFrame:
        s = self._sets[set_name]
        return pd.concat([s["keys"][KEYS].reset_index(drop=True), s["extras"].reset_index(drop=True)], axis=1)

    @contextlib.contextmanager
    def _fitting(self, fit_set: str):
        if self._fit_set is not None:
            self._refuse("internal: a label scope is already open")
        self._fit_set = fit_set
        try:
            yield self
        finally:
            self._fit_set = None

    def fit_labels(self, set_name: str):
        if set_name not in self.FIT_SETS:
            self._refuse("labels of set %r refused: only the fit sets %s give labels" % (set_name, self.FIT_SETS))
        if self._fit_set is None:
            self._refuse("labels of %r asked outside a runner's fit (the stand-in ctx refuses, as the tool's)" % set_name)
        if set_name != self._fit_set:
            self._refuse("a fit on %r asked the labels of %r" % (self._fit_set, set_name))
        self.label_calls.append(set_name)
        s = self._sets[set_name]
        return s["keys"][KEYS].copy(), np.asarray(s["y"], np.float64).copy(), {
            l: np.asarray(v, np.float64).copy() for l, v in s["normal"].items()}

    def features(self, set_name: str):
        self.feature_calls.append(set_name)
        s = self._sets[set_name]
        n = len(s["keys"])
        return SimpleNamespace(name=set_name, keys=s["keys"][KEYS].copy(), y=None,
                               normal={l: np.asarray(v, np.float64).copy() for l, v in s["normal"].items()},
                               history=pd.DataFrame(index=pd.RangeIndex(n)), extras=s["extras"].copy())

    # --- time helpers (AdapterCtx) ------------------------------------------------------------------
    def season_keys(self, times: Any) -> np.ndarray:
        return np.mod(np.asarray(times, np.int64) - 1, 12) + 1

    def step_year(self, s: Any) -> np.ndarray:
        return (np.asarray(s, np.int64) - 1) // 12

    def step_position(self, s: Any) -> np.ndarray:
        return np.mod(np.asarray(s, np.int64) - 1, 12) + 1

    def step_of(self, year: Any, position: Any) -> np.ndarray:
        return np.asarray(year, np.int64) * 12 + np.asarray(position, np.int64)

    @staticmethod
    def day_to_date(ordinal: int) -> _dt.date:
        return _dt.date.fromordinal(int(ordinal))

    @staticmethod
    def date_to_day(d: _dt.date) -> int:
        return int(d.toordinal())

    def t1_boundary(self, keys: pd.DataFrame) -> np.ndarray:
        return self.timing.t1_boundary(keys)

    def t2_step(self, keys: pd.DataFrame) -> np.ndarray:
        return self.timing.t2_step(keys)

    # --- products (the tool's own rules) -------------------------------------------------------------
    def _allowed(self, pid: str) -> None:
        if pid not in (self.rival.get("products") or []):
            self._refuse("rival %s opened product %r, which its registry entry does not list"
                         % (self.rival.get("id"), pid))

    def product_available(self, pid: str) -> bool:
        from rivals_human import index as IX
        self._allowed(pid)
        return bool(IX.product_status(self.cfg, self.products, pid)[0])

    def product_files(self, pid: str) -> List[str]:
        from rivals_human import index as IX
        self._allowed(pid)
        names = set(IX.product_manifest(self.cfg, self.products, pid)["files"])
        return sorted(names | set(self.extra_listed.get(pid, [])))

    def product_root(self, pid: str) -> Path:
        from rivals_human import index as IX
        self._allowed(pid)
        return IX.product_root(self.cfg, self.products, pid)

    def open_product(self, pid: str, name: str) -> Path:
        from rivals_human import index as IX
        self._allowed(pid)
        m = IX.product_manifest(self.cfg, self.products, pid)
        e = m["files"].get(name)
        if e is None:
            self._refuse("product %s's manifest does not list %r" % (pid, name))
        p = IX.product_root(self.cfg, self.products, pid) / name
        if not p.is_file():
            self._refuse("product file %s is missing" % p)
        IX.verify_product_file(p, str(e["sha256"]))
        self.opened.setdefault(pid, {})[name] = str(e["sha256"])
        return p

    def require_human_lock(self) -> Any:
        self._refuse("the toy ctx holds no human lock")

    # --- writes -------------------------------------------------------------------------------------
    def work_dir(self) -> Path:
        d = self.base / "_index" / self.run.package / self.run.name / "_work" / str(self.rival["id"])
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_bytes(self, path: Any, data: bytes) -> Path:
        p = Path(path)
        try:
            p.resolve().relative_to(self.work_dir().resolve())
        except ValueError:
            self._refuse("an adapter writes only under its work folder %s, not %s" % (self.work_dir(), p))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def log(self, message: Any) -> None:
        self.log_lines.append(str(message))


def manifests_of(ctx: FakeCtx) -> Dict[str, Dict[str, Any]]:
    """{pid: manifest} of every product the ctx opened (what index.adapt hands check_frame)."""
    from rivals_human import index as IX
    return {pid: IX.product_manifest(ctx.cfg, ctx.products, pid) for pid in ctx.opened}


# ===================================================================================================== netCDF writing
def _xr():
    import xarray as xr
    return xr


def write_nc(ds: Any, path: Path) -> Path:
    """Write a dataset in the RAW layout: data variables float32 with NaN fill (zlib), times as int64 seconds, the
    step as int64 seconds (decoded back to timedelta64), coordinates without a fill value. Encodings inherited from
    the source file are dropped first (shapes changed)."""
    ds = ds.copy()
    for v in list(ds.variables):
        ds[v].encoding = {}
    enc: Dict[str, Dict[str, Any]] = {}
    for name in ds.data_vars:
        enc[name] = {"dtype": "float32", "_FillValue": np.float32(np.nan), "zlib": True, "complevel": 1}
    for name in ds.coords:
        dt = ds[name].dtype
        if np.issubdtype(dt, np.datetime64):
            enc[name] = {"units": "seconds since 1970-01-01 00:00:00", "dtype": "int64"}
        elif np.issubdtype(dt, np.timedelta64):
            enc[name] = {"units": "seconds", "dtype": "int64"}
        elif np.issubdtype(dt, np.floating):
            enc[name] = {"_FillValue": None}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(str(path), encoding=enc, engine="netcdf4")
    return path


def open_nc(path: Path) -> Any:
    xr = _xr()
    with xr.open_dataset(str(path)) as ds:
        return ds.load()


def relabel_steps(ds: Any) -> Any:
    """SEAS5 subset: step coordinate -> 150..184 days + 12 h (in order), valid_time recomputed = time + step."""
    n = ds.sizes["step"]
    step_attrs = dict(ds["step"].attrs)
    vt_attrs = dict(ds["valid_time"].attrs) if "valid_time" in ds.coords else {"standard_name": "time"}
    steps = (np.array(SEAS_LEADS[:n], dtype="int64") * 86400 + 43200).astype("timedelta64[s]").astype(
        "timedelta64[ns]")
    ds = ds.assign_coords(step=("step", steps, step_attrs))
    t = ds["time"].values
    if np.ndim(t) == 0:
        vt = np.datetime64(t, "ns") + steps
        ds = ds.assign_coords(valid_time=("step", vt, vt_attrs))
    else:
        vt = np.asarray(t, "datetime64[ns]")[:, None] + steps[None, :]
        ds = ds.assign_coords(valid_time=(("time", "step"), vt, vt_attrs))
    return ds


# --- RAW subsets (built once per session) ---------------------------------------------------------------------
ERA5_GREECE_ISEL = {"latitude": slice(8, 14), "longitude": slice(0, 6)}          # 38.25..37.0 x 20.75..22.0
ERA5_PRIME_ISEL = {"latitude": slice(8, 14), "longitude": slice(0, 8)}           # 8 longitudes for the prime copy
PRIME_LONS = np.array([358.75, 359.0, 359.25, 359.5, 359.75, 0.0, 0.25, 0.5])
SEAS_GP_ISEL = {"latitude": [6, 7, 8], "longitude": [0, 1, 2]}                   # 40.5..38.5 x 256.25..258.25
SEAS_CE_ISEL = {"latitude": [2, 3, 4], "longitude": [0, 1, 2]}                   # -13.75..-15.75 x 304.5..306.5


def build_raw_subsets(out: Path) -> Dict[str, Path]:
    """The RAW subsets of section 5 (each keeps the scalar `surface` coordinate):
      era5_greece   SMOKE_hist_multiyear.nc 2018-2019 x 6 x 6 points (sea points incl.) + an extra data variable
                    `kbdi` (a renamed, changed copy of fwinx, written FIRST) that must be ignored
      era5_plain    the same without `surface` and without `kbdi` (must read byte-equal)
      era5_west     same values, longitudes rewritten to 256.00..257.25 (western, 0-360)
      era5_prime    6 x 8 points, longitudes 358.75 .. 0.5 (non-monotonic)
      seas_gp_2019  seas_great_plains_2019.nc: 2 starts (2019-01, -02) x members 0..25 x steps 0..34 x 3 x 3,
                    steps relabelled 150..184 d + 12 h
      seas_ce_2019  seas_cerrado_2019.nc likewise
      seas_gp_2015  the great_plains subset with starts relabelled 2015-09 / 2015-10 (targets Feb 2016, 29 days at
                    leads 153..181, and Mar 2016)"""
    xr = _xr()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, Path] = {}
    with xr.open_dataset(str(RAW / "SMOKE_hist_multiyear.nc")) as src:
        days = pd.DatetimeIndex(src["valid_time"].values)
        sel = np.flatnonzero((days.year >= 2018) & (days.year <= 2019))
        base = src.isel(valid_time=sel, **ERA5_GREECE_ISEL).load()
        prime = src.isel(valid_time=sel, **ERA5_PRIME_ISEL).load()
    assert "surface" in base.coords and base["surface"].ndim == 0, "RAW layout changed: no scalar surface"
    kbdi = (base["fwinx"] * 2.0 + 7.0).astype(np.float32)
    kbdi.attrs = dict(base["fwinx"].attrs, long_name="toy extra variable (must be ignored)")
    greece = xr.Dataset({"kbdi": kbdi, "fwinx": base["fwinx"]}, coords=base.coords, attrs=base.attrs)
    paths["era5_greece"] = write_nc(greece, out / "era5_greece.nc")
    plain = base.drop_vars("surface")
    paths["era5_plain"] = write_nc(plain, out / "era5_plain.nc")
    west = base.assign_coords(longitude=("longitude", base["longitude"].values + (256.00 - 20.75)))
    west["longitude"].attrs = dict(base["longitude"].attrs)
    paths["era5_west"] = write_nc(west, out / "era5_west.nc")
    pr = prime.assign_coords(longitude=("longitude", PRIME_LONS.copy()))
    pr["longitude"].attrs = dict(prime["longitude"].attrs)
    paths["era5_prime"] = write_nc(pr, out / "era5_prime.nc")
    for key, fname, isel in (("seas_gp_2019", "seas_great_plains_2019.nc", SEAS_GP_ISEL),
                             ("seas_ce_2019", "seas_cerrado_2019.nc", SEAS_CE_ISEL)):
        with xr.open_dataset(str(RAW / fname)) as src:
            sub = src.isel(number=slice(0, 26), time=slice(0, 2), step=slice(0, 35), **isel).load()
        assert "surface" in sub.coords and sub["fwinx"].dims == ("number", "time", "step", "latitude", "longitude")
        paths[key] = write_nc(relabel_steps(sub), out / (key + ".nc"))
    gp = open_nc(paths["seas_gp_2019"])
    leap = gp.assign_coords(time=("time", np.array(["2015-09-01", "2015-10-01"], dtype="datetime64[ns]")))
    leap["time"].attrs = dict(gp["time"].attrs)
    paths["seas_gp_2015"] = write_nc(relabel_steps(leap), out / "seas_gp_2015.nc")
    return paths


# --- synthetic long products ----------------------------------------------------------------------------------
SYN_ERA5_LAT = np.array([11.0, 10.75, 10.5, 10.25, 10.0])
SYN_ERA5_LON = np.array([20.0, 20.25, 20.5, 20.75, 21.0])
SYN_ERA5_SEA = (4, 1)                                             # (10.0, 20.25): all-NaN (sea)
SYN_SEAS_LAT = np.array([11.0, 10.0])
SYN_SEAS_LON = np.array([20.0, 21.0])
SYN_AREA = [11.0, 20.0, 10.0, 21.0]                               # N, W, S, E


def _surface() -> Dict[str, Any]:
    return {"surface": ((), 0.0, {"long_name": "original GRIB coordinate for key: level(surface)", "units": "1"})}


def synth_era5_ds(y0: int, y1: int, rng: np.random.Generator) -> Any:
    xr = _xr()
    days = pd.date_range("%d-01-01" % y0, "%d-12-31" % y1, freq="D")
    v = rng.gamma(2.0, 6.0, size=(days.size, SYN_ERA5_LAT.size, SYN_ERA5_LON.size)).astype(np.float32)
    v[:, SYN_ERA5_SEA[0], SYN_ERA5_SEA[1]] = np.nan
    return xr.Dataset({"fwinx": (("valid_time", "latitude", "longitude"), v, {"units": "Numeric", "long_name":
                                                                                  "Forest fire weather index"})},
                      coords={"valid_time": ("valid_time", days.values.astype("datetime64[ns]"),
                                             {"standard_name": "time"}),
                              "latitude": ("latitude", SYN_ERA5_LAT, {"units": "degrees_north"}),
                              "longitude": ("longitude", SYN_ERA5_LON, {"units": "degrees_east"}),
                              "surface": ((), 0.0)},
                      attrs={"Conventions": "CF-1.7", "institution": "toy"})


def synth_seas_ds(year: int, months: Sequence[int], members: int, rng: np.random.Generator) -> Any:
    xr = _xr()
    starts = np.array(["%04d-%02d-01" % (year, m) for m in months], dtype="datetime64[ns]")
    v = rng.gamma(2.0, 6.0, size=(members, len(months), len(SEAS_LEADS), SYN_SEAS_LAT.size,
                                  SYN_SEAS_LON.size)).astype(np.float32)
    ds = xr.Dataset({"fwinx": (("number", "time", "step", "latitude", "longitude"), v,
                               {"units": "Numeric", "long_name": "Forest fire weather index"})},
                    coords={"number": ("number", np.arange(members, dtype=np.int64)),
                            "time": ("time", starts, {"standard_name": "forecast_reference_time"}),
                            "step": ("step", np.zeros(len(SEAS_LEADS), dtype="timedelta64[ns]")),
                            "latitude": ("latitude", SYN_SEAS_LAT, {"units": "degrees_north"}),
                            "longitude": ("longitude", SYN_SEAS_LON, {"units": "degrees_east"}),
                            "surface": ((), 0.0)},
                    attrs={"Conventions": "CF-1.7", "institution": "toy"})
    return relabel_steps(ds)


def d3_starts(first: Tuple[int, int] = (2002, 8), last: Tuple[int, int] = (2019, 2)) -> List[Tuple[int, List[int]]]:
    out = []
    for y in range(first[0], last[0] + 1):
        ms = [m for m in range(1, 13) if first <= (y, m) <= last]
        if ms:
            out.append((y, ms))
    return out


# ===================================================================================================== fetcher folders
def era5_request(area: Sequence[float], years: Sequence[int]) -> Dict[str, Any]:
    """The request of fetch_products.py spec_D2 (:301-305)."""
    return {"product_type": ["reanalysis"], "variable": ["fire_weather_index"],
            "dataset_type": "consolidated_dataset", "system_version": ["4_1"],
            "year": [str(y) for y in years], "month": ["%02d" % m for m in range(1, 13)],
            "day": ["%02d" % d for d in range(1, 32)], "grid": "0.25/0.25", "area": [float(a) for a in area],
            "data_format": "netcdf"}


def seas5_request(area: Sequence[float], year: int, months: Sequence[int]) -> Dict[str, Any]:
    """The request of fetch_products.py seas_request (:206-210)."""
    return {"variable": ["fire_weather_index"], "release_version": ["5"], "year": [str(year)],
            "month": ["%02d" % m for m in months], "day": ["01"],
            "leadtime_hour": [str(12 + 24 * k) for k in SEAS_LEADS], "area": [float(a) for a in area],
            "data_format": "netcdf"}


def area_of(lat: Sequence[float], lon360: Sequence[float]) -> List[float]:
    """[N, W, S, E] in -180..180 as the fetcher writes boxes (FP:162-174)."""
    lo = wrap(lon360)
    return [float(np.max(lat)), float(np.min(lo)), float(np.min(lat)), float(np.max(lo))]


def write_fetcher_folder(folder: Path, dataset: str, entries: Sequence[Mapping[str, Any]],
                         complete: Optional[bool] = True, product: str = "toy_product") -> Path:
    """A fetcher product folder: each entry {file, src (a netCDF to copy) | data (bytes), request, regions[, starts]}
    is written, hashed and listed in product_manifest.json exactly as fetch_products.py writes it; complete=None
    leaves the `complete` key out (a first or killed fetcher run, FP:726-735, :801)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    now = "2026-10-25T12:00:00+02:00"
    man: Dict[str, Any] = {"product": product, "version": folder.name, "label": "toy " + product,
                           "dataset": dataset, "source_url": "https://ewds.climate.copernicus.eu/datasets/" + dataset,
                           "licence": "CC-BY-4.0 (toy)", "store": "ewds", "note": "toy folder (tests_fire)",
                           "created": now, "tool": {"sha256": "toy"}, "approval": "toy", "requests": {}, "files": {},
                           "runs": [{"started": now, "tool": {"sha256": "toy"}, "argv": ["toy"]}]}
    for e in entries:
        name = str(e["file"])
        dst = folder / name
        if "src" in e:
            dst.write_bytes(Path(e["src"]).read_bytes())
        else:
            dst.write_bytes(e["data"])
        rid = e.get("request_id") or name[:-3].split("_", 1)[1]
        req = {"id": rid, "file": e.get("request_file", name), "request": dict(e["request"]),
               "expected_bytes": int(dst.stat().st_size), "regions": list(e["regions"])}
        if e.get("starts") is not None:
            req["starts"] = int(e["starts"])
        man["requests"][rid] = req
        man["files"][name] = {"request_id": rid, "bytes": int(dst.stat().st_size), "sha256": sha256_file(dst),
                              "started": now, "finished": now, "seconds": 1.0,
                              "served_by": "https://ewds.climate.copernicus.eu/datasets/" + dataset}
    if complete is not None:
        man["runs"][-1].update({"finished": now, "new": len(entries), "skipped": 0, "failed": 0})
        man["total_bytes"] = int(sum(v["bytes"] for v in man["files"].values()))
        man["complete"] = bool(complete)
    write_json(folder / "product_manifest.json", man)
    return folder


def write_tool_manifest(folder: Path, out_manifest: Path, product: str) -> Path:
    """The tool's own manifest of a product on disk (`manifest --product <id>` format: files {name: {bytes, sha256}})."""
    files = {}
    for p in sorted(Path(folder).glob("*")):
        if p.is_file() and p.name != "product_manifest.json":
            files[p.name] = {"bytes": int(p.stat().st_size), "sha256": sha256_file(p)}
    return write_json(out_manifest, {"format": "human-product-manifest/1", "product": product,
                                     "root": str(folder).replace("\\", "/"), "files": files})


def static_product(base: Path) -> Dict[str, Any]:
    """The toy fire_static_cells product (part-0.parquet) with the tool's manifest under <out_root>/_products."""
    folder = Path(base) / "_static"
    folder.mkdir(parents=True, exist_ok=True)
    static_table().to_parquet(str(folder / "part-0.parquet"), index=False)
    write_tool_manifest(folder, Path(base) / "_hout" / "_products" / STATIC_PID / "product_manifest.json", STATIC_PID)
    return {"path": str(folder), "patterns": ["part-0.parquet"], "label": "toy unit centres"}


def decoy_product(base: Path, pid: str, names: Sequence[str]) -> Dict[str, Any]:
    """A product the index path must never open (T-F17): files exist, hashed, listed."""
    folder = Path(base) / ("_decoy_" + pid)
    folder.mkdir(parents=True, exist_ok=True)
    for n in names:
        pd.DataFrame({"cell_id": ["x"], "year": [2018], "month": [1], "burned_frac": [0.5]}).to_parquet(
            str(folder / n), index=False)
    write_tool_manifest(folder, Path(base) / "_hout" / "_products" / pid / "product_manifest.json", pid)
    return {"path": str(folder), "patterns": list(names)}


# ===================================================================================================== toy rivals
def unit_centres_option() -> Dict[str, str]:
    return {"product": STATIC_PID, "file": "part-0.parquet", "id": "cell_id", "lat": "lat", "lon": "lon"}


def era5_options(**over: Any) -> Dict[str, Any]:
    """registry/fire.yaml geff_era5 options (spec 2.2), the refs store pointing at the package reader."""
    opt = {"kind": "era5_daily", "product": ERA5_PID, "dataset": ERA5_DATASET,
           "request_check": {"product_type": ["reanalysis"], "dataset_type": "consolidated_dataset",
                             "system_version": ["4_1"], "grid": "0.25/0.25", "variable": ["fire_weather_index"]},
           "variable": "fwinx", "target_months_offset": 0, "unit_centres": unit_centres_option(),
           "min_day_share": 0.8, "sea_window_steps": 2, "max_uncovered_unit_share": 0.01,
           "pct_reference_end": "lead_guard_cut", "pct_min_reference": 10,
           "refs_store": {"target_product": TARGET_PID, "static_product": STATIC_PID, "years": [2018],
                          "out_dir": "refs_store", "file_pattern": "{group}_labels_{year}.parquet",
                          "target_file_pattern": "{group}_{year}.parquet", "target_reader": str(TARGET_READER)}}
    opt.update(over)
    return opt


def seas5_options(**over: Any) -> Dict[str, Any]:
    """registry/fire.yaml geff_seas5 options (spec 2.3)."""
    opt = {"kind": "seas5_daily_leads", "product": SEAS5_PID, "dataset": SEAS5_DATASET,
           "request_check": {"variable": ["fire_weather_index"], "release_version": ["5"], "day": ["01"]},
           "variable": "fwinx", "start_months_before_target": 5, "lead_days": [150, 184], "members": [0, 24],
           "unit_centres": unit_centres_option(), "min_day_share": 0.8, "sea_window_steps": 2,
           "max_uncovered_unit_share": 0.01, "pct_reference_end": "lead_guard_cut", "pct_min_reference": 10}
    opt.update(over)
    return opt


def era5_rival(**opt_over: Any) -> Dict[str, Any]:
    return {"id": "geff_era5", "kind": "I", "label": "F-ERA5 (toy)", "adapter": "adapters.fire_geff:build",
            "availability": "adapters.fire_geff:availability", "prep": "adapters.fire_refs_prep:run_prep",
            "products": [ERA5_PID, STATIC_PID, TARGET_PID, STORE_PID], "stats": list(STATS),
            "families": ["F2", "F3", "F4", "F5", "F6"], "links": "all", "t1_kind_columns": list(FWI_T1),
            "reads_target_in_test_window": False,
            "leads": {0: {"tier": "P"}, 6: {"tier": "none", "reason": "toy"}, 12: {"tier": "none", "reason": "toy"}},
            "score_without_net": [], "pick": "nowcast_inner", "slim_extra_columns": [], "optional": False,
            "resolution_matched": True, "coverage": "x_finite", "options": era5_options(**opt_over)}


def seas5_rival(**opt_over: Any) -> Dict[str, Any]:
    return {"id": "geff_seas5", "kind": "I", "label": "F-SEAS5 (toy)", "adapter": "adapters.fire_geff:build",
            "availability": "adapters.fire_geff:availability", "products": [SEAS5_PID, STATIC_PID],
            "stats": list(STATS), "families": ["F2", "F3", "F4", "F5", "F6"], "links": "all",
            "t1_kind_columns": list(FWI_T1), "reads_target_in_test_window": False,
            "leads": {0: {"tier": "none", "reason": "toy"}, 6: {"tier": "P"}, 12: {"tier": "none", "reason": "toy"}},
            "score_without_net": [], "pick": "lowest_covered_lead_guard", "slim_extra_columns": [],
            "optional": False, "resolution_matched": True, "coverage": "x_finite", "options": seas5_options(**opt_over)}


ENSO_OPTIONS = {"form": "E1", "index_column": "x__oni", "index_abs_max": 5.0, "min_fit_rows": 100,
                "fire_season_months": 3, "min_month_rows": 100}
TURCO_OPTIONS = {"form": "T1", "scales": list(SPI_COLS), "fixed_scale": "x__spi_03m",
                 "two_scales": ["x__spi_03m", "x__spi_12m"], "fire_season_months": 3, "spi_abs_max": 3.5,
                 "min_fit_rows": 100}


def enso_rival(form: str = "E1", **over: Any) -> Dict[str, Any]:
    opt = dict(ENSO_OPTIONS, form=form)
    opt.update(over)
    return {"id": "enso_lag", "kind": "M", "runner": "adapters.fire_enso", "products": [],
            "t1_kind_columns": ["oni"], "reads_target_in_test_window": False,
            "leads": {0: {"tier": "none", "reason": "toy"}, 6: {"tier": "P"}, 12: {"tier": "X", "label": "toy"}},
            "pick": "lowest_covered_lead_guard", "slim_extra_columns": ["x__oni"], "optional": True,
            "coverage": "all_rows", "options": opt}


def turco_rival(form: str = "T1", **over: Any) -> Dict[str, Any]:
    opt = dict(TURCO_OPTIONS, form=form)
    opt.update(over)
    return {"id": "turco_spi", "kind": "M", "runner": "adapters.fire_turco", "products": [],
            "t1_kind_columns": list(SPI_T1), "reads_target_in_test_window": False,
            "leads": {0: {"tier": "none", "reason": "toy"}, 6: {"tier": "P"}, 12: {"tier": "X", "label": "toy"}},
            "pick": "lowest_covered_lead_guard", "slim_extra_columns": list(SPI_COLS), "optional": True,
            "coverage": "all_rows", "options": opt}


# ===================================================================================================== product toys
class Toy(object):
    """One adapter toy: base folder, run, units, key table, products; ctx() builds a fresh FakeCtx."""

    def __init__(self, base: Path, run: FakeRun, rival: Mapping[str, Any], lead: int, units: pd.DataFrame,
                 table: pd.DataFrame, products: Mapping[str, Mapping[str, Any]]):
        self.base, self.run, self.rival, self.lead = Path(base), run, dict(rival), int(lead)
        self.units, self.table, self.products = units, table, {k: dict(v) for k, v in products.items()}

    def ctx(self, **over: Any) -> FakeCtx:
        kw = dict(base=self.base, run=self.run, rival=self.rival, lead=self.lead, products=self.products,
                  key_table=self.table, units=self.units)
        kw.update(over)
        return FakeCtx(**kw)


RAW_ERA5_CUTS = {0: {"fit_cut": step(2019, 4), "guard_cut": step(2018, 7)}}        # tune <= 2018-06, inner to 2019-03
RAW_ERA5_TIMES = list(range(step(2018, 1), step(2020, 1) + 1))                      # 2020-01: outside the product
GREECE_AREA = [38.25, 20.75, 37.0, 22.0]


def era5_toy(base: Path, raw: Mapping[str, Path], key: str = "era5_greece", group: str = "greece_mainland",
             box: Optional[str] = None, area: Optional[Sequence[float]] = None, rival: Optional[Mapping] = None,
             extra_units: Sequence[Tuple[str, str, bool]] = (), files: Optional[Sequence[Mapping]] = None,
             complete: Optional[bool] = True, dataset: str = ERA5_DATASET, cuts: Optional[Mapping] = None,
             times: Optional[Sequence[int]] = None, units: Optional[pd.DataFrame] = None) -> Toy:
    """A fake D2 folder with one RAW-subset file hist_<box>_2018-2019.nc (or `files`), the static product, the
    keys of the units of `group` at lead 0 (2018-01 .. 2020-01) and a FakeRun."""
    base = Path(base)
    box = box or group
    if files is None:
        src = Path(raw[key])
        if area is None:
            ds = open_nc(src)
            area = area_of(ds["latitude"].values, ds["longitude"].values)
        files = [{"file": "hist_%s_2018-2019.nc" % box, "src": src, "request": era5_request(area, [2018, 2019]),
                  "regions": [group]}]
    folder = write_fetcher_folder(base / "human_products" / "cems_fire_historical_fwi" / ERA5_FOLDER,
                                  dataset, files, complete=complete, product="cems_fire_historical_fwi")
    products = {ERA5_PID: {"manifest": str(folder / "product_manifest.json"), "waiting_line": ERA5_WAITING},
                STATIC_PID: static_product(base),
                TARGET_PID: decoy_product(base, TARGET_PID, ["%s_2018.parquet" % group]),
                STORE_PID: decoy_product(base, STORE_PID, ["%s_labels_2018.parquet" % group])}
    cuts = dict(cuts or RAW_ERA5_CUTS)
    run = FakeRun(cuts=cuts)
    u = units if units is not None else units_of(sorted(set(f["regions"][0] for f in files) | {group}), extra_units)
    table = key_table(u, times or RAW_ERA5_TIMES, 0, cuts)
    return Toy(base, run, rival or era5_rival(), 0, u, table, products)


RAW_SEAS_CUTS = {0: {"fit_cut": step(2019, 6), "guard_cut": step(2016, 4)},
                 6: {"fit_cut": step(2019, 6), "guard_cut": step(2016, 3)}}
RAW_SEAS_TIMES = [step(2016, 2), step(2016, 3), step(2019, 6), step(2019, 7), step(2019, 8)]


def seas5_raw_files(raw: Mapping[str, Path], which: Sequence[str] = ("gp_2015", "gp_2019", "ce_2019"),
                    srcs: Optional[Mapping[str, Path]] = None) -> List[Dict[str, Any]]:
    spec = {"gp_2015": ("great_plains", 2015, [9, 10]), "gp_2019": ("great_plains", 2019, [1, 2]),
            "ce_2019": ("cerrado", 2019, [1, 2])}
    out = []
    for w in which:
        box, year, months = spec[w]
        src = Path((srcs or {}).get(w) or raw["seas_" + w])
        ds = open_nc(src)
        area = area_of(ds["latitude"].values, ds["longitude"].values)
        out.append({"file": "seas_%s_%d.nc" % (box, year), "src": src, "request": seas5_request(area, year, months),
                    "regions": [box], "starts": len(months)})
    return out


def seas5_toy(base: Path, raw: Mapping[str, Path], files: Optional[Sequence[Mapping]] = None,
              rival: Optional[Mapping] = None, complete: Optional[bool] = True, dataset: str = SEAS5_DATASET,
              groups: Sequence[str] = ("great_plains", "cerrado"), times: Optional[Sequence[int]] = None,
              cuts: Optional[Mapping] = None, units: Optional[pd.DataFrame] = None) -> Toy:
    """A fake D3 folder (RAW subsets: seas_great_plains_2015/2019.nc, seas_cerrado_2019.nc), keys at lead 6 of the
    great_plains + cerrado units for targets Feb/Mar 2016 (guardfit), Jun 2019 (guard), Jul 2019 (test) and Aug 2019
    (test, outside the product). The toy run keeps no R17 offset (guard and test rows of one subset year)."""
    base = Path(base)
    files = files if files is not None else seas5_raw_files(raw)
    folder = write_fetcher_folder(base / "human_products" / "cems_fire_seasonal_fwi" / SEAS5_FOLDER,
                                  dataset, files, complete=complete, product="cems_fire_seasonal_fwi")
    products = {SEAS5_PID: {"manifest": str(folder / "product_manifest.json"), "waiting_line": SEAS5_WAITING},
                STATIC_PID: static_product(base)}
    cuts = dict(cuts or RAW_SEAS_CUTS)
    run = FakeRun(cuts=cuts, offset=0)
    u = units if units is not None else units_of(groups)
    table = key_table(u, times or RAW_SEAS_TIMES, 6, cuts, offset=0)
    return Toy(base, run, rival or seas5_rival(), 6, u, table, products)


def build_synth_products(out: Path) -> Dict[str, Any]:
    """The synthetic long products (one fixed random_state): ERA5 2003-2019 in the fetcher's 5-year blocks, and
    SEAS5 starts 2002-08 .. 2019-02 (25 members to 2016, 26 = 0..25 from 2017), box `synth`, region synth_region."""
    out = Path(out)
    rng = np.random.default_rng(RANDOM_STATE)
    era5 = []
    for y0, y1 in ((2003, 2007), (2008, 2012), (2013, 2017), (2018, 2019)):
        p = write_nc(synth_era5_ds(y0, y1, rng), out / ("hist_synth_%d-%d.nc" % (y0, y1)))
        era5.append({"file": p.name, "src": p, "request": era5_request(SYN_AREA, list(range(y0, y1 + 1))),
                     "regions": ["synth_region"]})
    seas = []
    for y, ms in d3_starts():
        p = write_nc(synth_seas_ds(y, ms, 25 if y <= 2016 else 26, rng), out / ("seas_synth_%d.nc" % y))
        seas.append({"file": p.name, "src": p, "request": seas5_request(SYN_AREA, y, ms), "regions": ["synth_region"],
                     "starts": len(ms)})
    return {"era5": era5, "seas": seas}


SYNTH_ERA5_TIMES = list(range(step(2003, 1), step(2020, 1) + 1))
SYNTH_SEAS_TIMES = list(range(step(2003, 1), step(2019, 8) + 1))


def synth_era5_toy(base: Path, synth: Mapping[str, Any], cuts: Optional[Mapping] = None,
                   rival: Optional[Mapping] = None) -> Toy:
    """Lead 0 at the facts' cuts (tune <= 24191, inner 24193..24227, test from 24229)."""
    base = Path(base)
    folder = write_fetcher_folder(base / "human_products" / "cems_fire_historical_fwi" / ERA5_FOLDER, ERA5_DATASET,
                                  synth["era5"], product="cems_fire_historical_fwi")
    products = {ERA5_PID: {"manifest": str(folder / "product_manifest.json"), "waiting_line": ERA5_WAITING},
                STATIC_PID: static_product(base),
                TARGET_PID: decoy_product(base, TARGET_PID, ["synth_region_2018.parquet"]),
                STORE_PID: decoy_product(base, STORE_PID, ["synth_region_labels_2018.parquet"])}
    cuts = dict(cuts or FACT_CUTS)
    run = FakeRun(cuts=cuts)
    u = units_of(["synth_region"])
    table = key_table(u, SYNTH_ERA5_TIMES, 0, cuts, test_start=TEST_START)
    return Toy(base, run, rival or era5_rival(), 0, u, table, products)


def synth_seas5_toy(base: Path, synth: Mapping[str, Any], cuts: Optional[Mapping] = None,
                    rival: Optional[Mapping] = None) -> Toy:
    """Lead 6 at the facts' cuts (guardfit <= 24186, guard 24193..24222, test from 24229)."""
    base = Path(base)
    folder = write_fetcher_folder(base / "human_products" / "cems_fire_seasonal_fwi" / SEAS5_FOLDER, SEAS5_DATASET,
                                  synth["seas"], product="cems_fire_seasonal_fwi")
    products = {SEAS5_PID: {"manifest": str(folder / "product_manifest.json"), "waiting_line": SEAS5_WAITING},
                STATIC_PID: static_product(base)}
    cuts = dict(cuts or FACT_CUTS)
    run = FakeRun(cuts=cuts)
    u = units_of(["synth_region"])
    table = key_table(u, SYNTH_SEAS_TIMES, 6, cuts, test_start=TEST_START)
    return Toy(base, run, rival or seas5_rival(), 6, u, table, products)


# ===================================================================================================== hand oracles
def grid_of(path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(latitude, longitude as stored, valid mask = finite in at least one value) of a netCDF subset."""
    ds = open_nc(path)
    v = ds["fwinx"].values
    axes = tuple(range(v.ndim - 2))
    return ds["latitude"].values.astype(np.float64), ds["longitude"].values.astype(np.float64), \
        np.isfinite(v).any(axis=axes)


def era5_monthly_hand(path: Path, i: int, j: int, min_share: float = 0.8) -> Dict[int, float]:
    """{step: mean of the finite daily FWI at point (i, j)} per calendar month of the file (MINDAYS rule)."""
    ds = open_nc(path)
    v = ds["fwinx"].values[:, i, j].astype(np.float64)
    days = pd.DatetimeIndex(ds["valid_time"].values)
    out = {}
    for (y, m), idx in pd.Series(np.arange(days.size)).groupby([days.year, days.month]).groups.items():
        vals = v[np.asarray(idx)]
        fin = np.isfinite(vals)
        out[step(y, m)] = float(vals[fin].mean()) if fin.sum() / float(days_in(y, m)) >= min_share else float("nan")
    return out


def seas5_target_hand(path: Path, start: str, i: int, j: int, members: Sequence[int] = range(25),
                      min_share: float = 0.8) -> Tuple[int, float]:
    """(target step, mean over members 0..24 (by number value) x the days of the target month (start + 5 months))."""
    ds = open_nc(path)
    s = pd.Timestamp(start)
    ty, tm = (s.year + (s.month + 5 - 1) // 12, (s.month + 5 - 1) % 12 + 1)
    fw = ds["fwinx"].sel(number=list(members))
    if "time" in fw.dims:
        fw = fw.sel(time=np.datetime64(s.to_datetime64(), "ns"))
    k = (ds["step"].values / np.timedelta64(1, "D")).astype(np.float64)
    vdate = [(s + pd.Timedelta(days=float(np.floor(kk)))) for kk in k]
    sel = np.array([(d.year, d.month) == (ty, tm) for d in vdate])
    vals = fw.values[:, sel, i, j].astype(np.float64)
    fin = np.isfinite(vals)
    share = fin.sum() / float(len(members) * days_in(ty, tm))
    return step(ty, tm), (float(vals[fin].mean()) if share >= min_share else float("nan"))


def mid_rank(x: float, ref: Sequence[float]) -> float:
    r = np.asarray(ref, np.float64)
    return float(((r < x).sum() + 0.5 * (r == x).sum()) / r.size)


def pct_hand(unit: Sequence[Any], time: Sequence[int], x: Sequence[float], t_ref: int, min_ref: int) -> np.ndarray:
    """Spec 3.6 by hand: R(u, t) = {x(u, t'): t' <= t_ref, same calendar month, t' != t, finite}; mid-rank; |R| <
    min_ref or x NaN -> NaN."""
    u = np.asarray(unit).astype(str)
    t = np.asarray(time, np.int64)
    v = np.asarray(x, np.float64)
    mon = np.mod(t - 1, 12)
    out = np.full(v.size, np.nan)
    for k in range(v.size):
        if not np.isfinite(v[k]):
            continue
        sel = (u == u[k]) & (mon == mon[k]) & (t <= t_ref) & (t != t[k]) & np.isfinite(v)
        if sel.sum() >= min_ref:
            out[k] = mid_rank(v[k], v[sel])
    return out


def audit_units(doc: Any) -> Dict[str, Any]:
    """{unit: record} of the 3.3 audit file map_units_lead_<L>.json, whatever its container (a mapping keyed by unit
    or a list of records with a `unit` field, under units / per_unit / unit_map, or the document itself)."""
    for key in ("units", "per_unit", "unit_map"):
        v = doc.get(key) if isinstance(doc, dict) else None
        if isinstance(v, dict):
            return {str(k): r for k, r in v.items()}
        if isinstance(v, list):
            return {str(r.get("unit")): r for r in v}
    if isinstance(doc, list):
        return {str(r.get("unit")): r for r in doc}
    pytest.fail("the audit file names no per-unit block (units / per_unit / unit_map): %s" % sorted(doc)[:10])


# ===================================================================================================== real files
def real_registry_cfg():
    """(config module, a config mapping) that reads the REAL registry folder and product registry (read-only), as
    rivals_human/tests/test_h20_nonames.py:76-83 does; every write root points at an unused folder name."""
    from rivals_human import config as C
    from rivals_human.tests import hooks as HK
    keys = {k: "D:/treeroute/human_rivals_build/_unused" for k in C.ROOT_KEYS + C.PATH_EXTRA_KEYS}
    keys.update(registry_dir=str(HUMAN_ROOT / "registry"),
                on_disk_products=str(HUMAN_ROOT / "registry" / "_products.yaml"),
                common_build_root=str(HK.COMMON_ROOT), common_harness_sha256=HK.COMMON_SHA)
    return C, C.load_config(keys)


def baseline_file(rel: str, sha: str) -> Path:
    """The Part B baseline copy _moved/<utc>_partB_baseline/<rel> whose sha256 is `sha` (spec 2.7, 4.4)."""
    hits = [p for p in sorted(MOVED.glob("*_partB_baseline/" + rel)) if sha256_file(p) == sha]
    if not hits:
        pytest.fail("no baseline copy %s with sha256 %s under %s/*_partB_baseline (spec 2.7 / 4.4: the builder copies "
                    "the file there BEFORE editing it)" % (rel, sha[:16], MOVED))
    return hits[0]


def load_module_from(path: Path, name: str) -> Any:
    """A module loaded from a file under another name (no bytecode written)."""
    import importlib.util
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===================================================================================================== read spy
class ReadSpy(object):
    """Records every path opened while installed: builtins.open and io.open (pathlib's read_bytes / open), pyarrow.
    parquet (read_table, read_schema, read_metadata, ParquetFile, ParquetDataset), pyarrow.dataset.dataset, pandas
    read_parquet / read_csv, xarray open_dataset / load_dataset / open_mfdataset / open_dataarray (also through
    xarray.backends.api). netCDF4.Dataset is NOT wrapped (xarray checks isinstance against it); a netCDF read through
    xarray is recorded by the xarray wrappers."""

    def __init__(self):
        self.paths: List[str] = []

    def _add(self, obj: Any) -> None:
        if isinstance(obj, (str, os.PathLike)):
            self.paths.append(os.path.normcase(os.path.abspath(str(obj))))
        elif isinstance(obj, (list, tuple)):
            for o in obj:
                self._add(o)
        else:
            name = getattr(obj, "name", None) or getattr(obj, "path", None)
            if isinstance(name, (str, os.PathLike)):
                self.paths.append(os.path.normcase(os.path.abspath(str(name))))

    def _wrap(self, fn: Callable) -> Callable:
        spy = self

        def wrapped(*a, **k):
            if a:
                spy._add(a[0])
            for key in ("source", "path", "filename_or_obj", "paths", "where"):
                if key in k:
                    spy._add(k[key])
            return fn(*a, **k)
        return wrapped

    def install(self, monkeypatch: Any) -> "ReadSpy":
        import builtins
        import io
        import pyarrow.dataset as pds
        import pyarrow.parquet as pq
        monkeypatch.setattr(builtins, "open", self._wrap(builtins.open))
        monkeypatch.setattr(io, "open", self._wrap(io.open))
        for name in ("read_table", "read_schema", "read_metadata", "ParquetFile", "ParquetDataset"):
            monkeypatch.setattr(pq, name, self._wrap(getattr(pq, name)))
        monkeypatch.setattr(pds, "dataset", self._wrap(pds.dataset))
        monkeypatch.setattr(pd, "read_parquet", self._wrap(pd.read_parquet))
        monkeypatch.setattr(pd, "read_csv", self._wrap(pd.read_csv))
        try:
            import xarray as xr
            import xarray.backends.api as xapi
            for name in ("open_dataset", "load_dataset", "open_mfdataset", "open_dataarray"):
                if hasattr(xr, name):
                    monkeypatch.setattr(xr, name, self._wrap(getattr(xr, name)))
                if hasattr(xapi, name):
                    monkeypatch.setattr(xapi, name, self._wrap(getattr(xapi, name)))
        except ImportError:                                # pragma: no cover (xarray is installed)
            pass
        return self

    def under(self, folder: Any) -> List[str]:
        root = os.path.normcase(os.path.abspath(str(folder)))
        return [p for p in self.paths if p == root or p.startswith(root + os.sep)]

    def named(self, *words: str) -> List[str]:
        return [p for p in self.paths if any(w.lower() in p.lower() for w in words)]


def decoy_slim(base: Path) -> Path:
    """Slim-like train / test parquet files and a test_preds.parquet that no adapter or prep may open (T-F17)."""
    d = Path(base) / "_decoy_slim" / "slim" / "lead_0"
    for part in ("train", "test"):
        (d / part).mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"unit": ["x"], "time": [1], "y": [0.5]}).to_parquet(str(d / part / "g.parquet"), index=False)
    pd.DataFrame({"unit": ["x"], "y": [0.5]}).to_parquet(str(Path(base) / "_decoy_slim" / "test_preds.parquet"),
                                                         index=False)
    return d.parent.parent


# ===================================================================================================== runner toys
def runner_frame(lead: int, cuts: Mapping[int, Mapping[str, int]] = FACT_CUTS, groups: Sequence[str] = ("g1", "g2", "g3"),
                 units_per_group: int = 8, first: int = step(2003, 1), last: int = step(2022, 12),
                 peak: Optional[Mapping[str, int]] = None, seed: int = RANDOM_STATE) -> pd.DataFrame:
    """Every (unit, target time) row of a runner toy at one lead with role flags (key_table rules, test from 24229),
    the identity normal N (per unit x calendar month: a 3-month peak around the group's `peak` month, zero in the
    four months opposite it), ONI of issue - 3 (one global series), the five SPI scales at the issue (independent,
    per unit)."""
    rng = np.random.default_rng(seed)
    peak = dict(peak or {"g1": 7, "g2": 1, "g3": 4})
    units = pd.DataFrame({"unit": ["%s_u%02d" % (g, k) for g in groups for k in range(units_per_group)],
                          "group": [g for g in groups for _ in range(units_per_group)]})
    tab = key_table(units, range(first, last + 1), lead, cuts, test_start=TEST_START)
    months_all = np.arange(1, 13)
    nrm = {}
    for u, g in zip(units["unit"], units["group"]):
        base = 0.002 + 0.004 * rng.random()
        dist = np.minimum(np.abs(months_all - peak.get(g, 7)), 12 - np.abs(months_all - peak.get(g, 7)))
        v = base * (1.0 + 4.0 * np.exp(-0.5 * dist.astype(float) ** 2))
        v[dist >= 4] = 0.0
        nrm[u] = v
    iss = np.arange(first - lead - 3, last + 1)
    oni = pd.Series(np.round(np.clip(rng.normal(0.0, 0.9, iss.size), -2.4, 2.4), 3), index=iss)
    mon = np.mod(tab["time"].to_numpy(np.int64) - 1, 12) + 1
    tab["month"] = mon
    tab["N"] = [nrm[u][m - 1] for u, m in zip(tab["unit"], mon)]
    tab["x__oni"] = oni.reindex(tab["issue"].to_numpy(np.int64)).to_numpy(np.float64)
    for c in SPI_COLS:
        tab[c] = np.round(np.clip(rng.normal(0.0, 1.0, len(tab)), -3.09, 3.09), 4)
    return tab


def runner_sets(frame: pd.DataFrame, y: np.ndarray, extras: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    """{set: {keys, y, normal, extras}} from a runner frame (sets refit, tune / guardfit, inner / guard, test)."""
    out = {}
    names = ["refit", "tune", "inner", "guardfit", "guard", "test"]
    for name in names:
        sel = frame["is_test"].to_numpy(bool) if name == "test" else frame[SET_FLAG[name]].to_numpy(bool)
        if not sel.any():
            continue
        f = frame[sel].reset_index(drop=True)
        k = f[KEYS].copy()
        for c in ("time", "issue", "lead"):
            k[c] = k[c].astype(np.int64)
        N = f["N"].to_numpy(np.float64)
        out[name] = {"keys": k, "y": np.asarray(y)[sel].astype(np.float64),
                     "normal": {"identity": N, "log_c": np.log(np.maximum(N, 0.0) + 0.01),
                                "arcsine": np.arcsin(np.sqrt(np.maximum(N, 0.0)))},
                     "extras": f[list(extras)].reset_index(drop=True).astype(np.float64)}
    return out


def runner_ctx(base: Path, rival: Mapping[str, Any], lead: int, sets: Mapping[str, Mapping[str, Any]],
               r8: Optional[Mapping[str, Any]] = None, cuts: Mapping = FACT_CUTS) -> FakeCtx:
    return FakeCtx(base, FakeRun(cuts=cuts, r8=r8), rival, lead, stage="all", sets=sets)


def fit_in_scope(runner: Any, ctx: FakeCtx, rival: Mapping[str, Any], lead: int, fit_set: str) -> Any:
    """runner.fit inside the label scope of fit_set (what methods.run_fit opens on the real AdapterCtx)."""
    with ctx._fitting(fit_set):
        return runner.fit(ctx, dict(rival), int(lead), fit_set)
