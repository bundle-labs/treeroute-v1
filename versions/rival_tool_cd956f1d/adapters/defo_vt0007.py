"""Defo human rivals vt0007_shipped, vt0007_cal, vt0007_frozen2019: Verra VT0007 "UDef-A" risk-map allocation with
the VMD0055 quantity, rebuilt on our Hansen tiles (counts from defo_prep.py).

SPEC_HUMAN.txt section 3 (Builder B). Kind M index table: x__vt0007 on the target scale (loss_px / forest2000_px).
The tool maps it: vt0007_shipped F0 (as shipped), vt0007_cal F2 / F4 (isotonic), vt0007_frozen2019 F0.

For issue year t (HRP = t-10 .. t-1; T1 = end of t-11; T3 = end of t-1), per group (= jurisdiction):
  1. NRT = the distance (at T1) holding 99.5% of the group's HRP loss pixels, snapped up to a fine-bin edge.
  2. 30 classes: 29 geometric classes with edges e_k = e0 (NRT / e0)^(k/29), k = 1..29 (e0 = min(d0, NRT / 2),
     d0 = 30 m), plus class 30 beyond the NRT. A fine bin takes the class of its upper edge.
  3. Frequency per (division, class) = HRP loss pixels / forest(T1) pixels; a (division, class) without forest(T1)
     pixels uses the group's pooled class frequency (counted).
  4. Each forest(T3) pixel gets its (division, class) frequency f; expected loss = min(1, s f), s chosen so the group
     total equals Q = HRP loss pixels / 10 (the VMD0055 mean annual rate, no trend), exactly (water-filling with the
     pixel cap at 1; if Q exceeds the pixels that can carry loss, every such pixel is 1: counted).
  5. x__vt0007(cell) = sum of expected loss pixels in the cell / forest2000_px(cell).
Frozen form (option frozen_year f): every issue year t > f + 1 uses the t = f + 1 map (HRP f-9..f, distance at end f).
Coverage (label-free, fixed): issue year t >= first_loss_year + hrp_years (2011) and forest2000_px > 0; else NaN.
target_obs_end = t_eff - 1 (the newest Hansen loss year read: a target observation, guarded by T2); info_end = the
registry option driver_info_end (2000: treecover2000 / datamask, the newest non-label input; GADM is fixed geography).
Leads 0 and 1 give identical values per (unit, time) by construction (the value depends on the cell and the target
year only).

Stages (A2, A7): stage "train" uses prep files of stage train only and refuses a row that would need a later loss
year; stage "test" needs the human lock and the prep test files.
AdapterCtx calls used: ctx.keys("stage"), ctx.run (cuts), ctx.open_product, ctx.work_dir, ctx.log,
ctx.require_human_lock (stage test).
"""
# Provenance: research_defo.md:34-87 (method, quantity, coverage), SPEC_HUMAN.txt 3 (exact computation),
# VT0007 v1.0 sections 5.3.1-5.3.2 (as summarised in research_defo.md; class-edge rule pre-registered here).

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from adapters import defo_prep as DP

ADAPTER_FORMAT = "human-adapter-defo-vt0007/1"
KEYS = ("unit", "group", "time", "issue", "lead")
N_CLASSES = 30                   # VT0007 5.3.1
NRT_SHARE = 0.995                # the distance holding 99.5% of HRP loss
D0_M = 30.0                      # geometric start (one nominal 30 m pixel); e0 = min(D0_M, NRT / 2)
QTY_RTOL = 1e-9
DP_SEP = ";"                     # several src files on one row (rivals_human/config.py SRC_SEPARATOR)


class VT0007Refusal(RuntimeError):
    """A VT0007 adapter rule refused (fail loud)."""


def _refuse(message: str, fix: Optional[str] = None):
    raise VT0007Refusal("refused [defo vt0007]: " + message + ("" if not fix else "  FIX: " + fix))


# ---------------------------------------------------------------------------------------------------- prep loading
class PrepFiles(object):
    """The prep outputs, read as a hashed product when the registry names one (option prep_product: every file is
    opened through ctx.open_product, so `check` can verify each src name), else straight from the prep owner's work
    folder (toy tests only; the tool's check refuses a src that is not a product file)."""

    def __init__(self, ctx: Any, rival: Mapping[str, Any]):
        self.ctx = ctx
        self.pid = (rival.get("options") or {}).get("prep_product")
        if self.pid:
            self.names = sorted(str(n).replace("\\", "/") for n in ctx.product_files(self.pid))
            self.base = None
        else:
            self.base = DP.prep_dir(ctx, rival)
            self.names = sorted(p.relative_to(self.base).as_posix() for p in self.base.rglob("*") if p.is_file())

    def has(self, name: str) -> bool:
        return name in self.names

    def path(self, name: str) -> Path:
        if name not in self.names:
            _refuse("the prep file %s is missing (run the defo prep, then hash it with `manifest --product %s`)"
                    % (name, self.pid))
        return Path(self.ctx.open_product(self.pid, name)) if self.pid else self.base / name

    def read_json(self, name: str) -> Dict[str, Any]:
        with open(str(self.path(name)), encoding="utf-8") as f:
            return json.load(f)


class RegionCounts(object):
    """Every map of one region across the given stages: forest[T] (ncell, NB1) and loss[(T, year)] sparse, with the
    prep file each count came from (the row's src)."""

    def __init__(self, files: PrepFiles, region: str, stages: Sequence[str], ncell: int, bins: "DP.FineBins"):
        self.ncell, self.nb1 = int(ncell), bins.n + 1
        self.forest: Dict[int, Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        self.loss: Dict[Tuple[int, int], Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        self.forest_src: Dict[int, str] = {}
        self.loss_src: Dict[Tuple[int, int], str] = {}
        self.parity_forest = None
        self.maps: Dict[str, Any] = {}
        for st in stages:
            man_name = DP.MANIFEST_FILE % st
            if not files.has(man_name):
                _refuse("the prep manifest %s is missing (run the defo prep stage %s first)" % (man_name, st))
            man = files.read_json(man_name)
            if man["bins"] != bins.as_dict():
                _refuse("prep stage %s used bins %s, the registry says %s" % (st, man["bins"], bins.as_dict()))
            pat = re.compile(r"^%s/map_T(\d+)__%s\.json$" % (re.escape(region), st))
            for jn in [n for n in files.names if pat.match(n)]:
                meta = files.read_json(jn)
                npz_name = jn[:-len(".json")] + ".npz"
                p = files.path(npz_name)
                with open(str(p), "rb") as f:
                    data = f.read()
                if DP.sha256_bytes(data) != meta["npz_sha256"] or man["files_sha256"].get(npz_name) != meta["npz_sha256"]:
                    _refuse("%s differs from its meta / the stage manifest" % npz_name)
                z = DP.load_map(p)
                T = int(meta["T"])
                self.maps["%s:T%d" % (st, T)] = {"ymax": meta["ymax"], "loss_years": meta["loss_years"]}
                fe = (z["forest_cell"].astype(np.int64), z["forest_bin"].astype(np.int64), z["forest_n"])
                if T in self.forest:
                    if not all(np.array_equal(a, b) for a, b in zip(self.forest[T], fe)):
                        _refuse("%s: map T%d forest counts differ between stages" % (region, T))
                else:
                    self.forest[T] = fe
                    self.forest_src[T] = npz_name
                for y in sorted(set(z["loss_year"].astype(int).tolist()) | set(meta["loss_years"])):
                    s = z["loss_year"].astype(int) == y
                    le = (z["loss_cell"][s].astype(np.int64), z["loss_bin"][s].astype(np.int64), z["loss_n"][s])
                    if (T, y) in self.loss:
                        if not all(np.array_equal(a, b) for a, b in zip(self.loss[(T, y)], le)):
                            _refuse("%s: map T%d loss year %d differs between stages" % (region, T, y))
                    else:
                        self.loss[(T, y)] = le
                        self.loss_src[(T, y)] = npz_name
                if self.parity_forest is None:
                    self.parity_forest = z["parity_forest"].astype(np.int64)

    def src_of(self, T1: int, T3: int, years: Sequence[int]) -> List[str]:
        names = {self.forest_src[T1], self.forest_src[T3]} | {self.loss_src[(T1, y)] for y in years}
        return sorted(names)

    def forest_dense(self, T: int) -> np.ndarray:
        if T not in self.forest:
            _refuse("map T%d is not in the prep files of these stages" % T)
        c, b, n = self.forest[T]
        out = np.zeros((self.ncell, self.nb1), np.float64)
        np.add.at(out, (c, b), n)
        return out

    def loss_dense(self, T: int, years: Sequence[int]) -> np.ndarray:
        out = np.zeros((self.ncell, self.nb1), np.float64)
        for y in years:
            if (T, y) not in self.loss:
                _refuse("map T%d holds no loss count for year %d in these stages" % (T, y))
            c, b, n = self.loss[(T, y)]
            np.add.at(out, (c, b), n)
        return out


# ---------------------------------------------------------------------------------------------------- the method
def class_of_bins(bins: "DP.FineBins", nrt: float, d0: float = D0_M, n_classes: int = N_CLASSES) -> np.ndarray:
    """Class 1..n_classes of every fine bin (overflow included) from its upper edge."""
    e0 = min(float(d0), nrt / 2.0)
    k = np.arange(1, n_classes, dtype=np.float64)
    e = e0 * (nrt / e0) ** (k / float(n_classes - 1))
    e[-1] = nrt
    return np.searchsorted(e * (1.0 + 1e-12), bins.upper(), side="left") + 1


def solve_scale(P: np.ndarray, f: np.ndarray, Q: float) -> Tuple[float, bool]:
    """s >= 0 with sum P min(1, s f) = Q (P pixel counts, f frequencies). Returns (s, all_capped)."""
    m = (P > 0) & (f > 0)
    P, f = P[m], f[m]
    if Q <= 0 or not len(P):
        return 0.0, False
    if Q >= P.sum():
        return float("inf"), True
    o = np.argsort(-f, kind="mergesort")
    P, f = P[o], f[o]
    C = np.concatenate([[0.0], np.cumsum(P)])                    # C[j] = pixels of the j largest f (capped)
    R = np.concatenate([np.cumsum((P * f)[::-1])[::-1], [0.0]])  # R[j] = sum over i >= j of P f
    m = len(P)
    with np.errstate(divide="ignore", invalid="ignore"):
        s_all = np.where(R[:m] > 0, (Q - C[:m]) / R[:m], np.inf)   # s if exactly the j largest f are capped
    prev = np.concatenate([[np.inf], f[:-1]])
    ok = (s_all * f <= 1.0 + 1e-12) & (s_all * prev >= 1.0 - 1e-12) & np.isfinite(s_all)
    if not ok.any():
        _refuse("the quantity scaling found no solution (Q %.6g)" % Q)
    return float(s_all[int(np.argmax(ok))]), False


def vt0007_region(F1: np.ndarray, Lh: np.ndarray, F3: np.ndarray, div: np.ndarray, forest2000: np.ndarray,
                  bins: "DP.FineBins", hrp_years: int, d0: float = D0_M, n_classes: int = N_CLASSES,
                  share: float = NRT_SHARE) -> Tuple[np.ndarray, Dict[str, Any]]:
    """x per cell (NaN where forest2000 == 0) and a report. F1, Lh, F3: (ncell, NB1) counts; div: (ncell,) codes."""
    ncell = F1.shape[0]
    total = float(Lh.sum())
    Q = total / float(hrp_years)
    rep = {"hrp_loss_px": total, "Q": Q}
    x = np.full(ncell, np.nan)
    has = forest2000 > 0
    if total <= 0:
        x[has] = 0.0
        rep.update({"nrt_m": None, "scale": 0.0, "note": "no HRP loss in the group: every cell 0"})
        return x, rep
    hist = Lh.sum(axis=0)
    cum = np.cumsum(hist)
    b_star = int(np.searchsorted(cum, share * total - 1e-9 * total, side="left"))
    if b_star >= bins.n:
        _refuse("the NRT lies beyond d_max %.0f m (HRP loss in the overflow bin); raise d_max_m" % bins.d_max)
    nrt = float(bins.upper()[b_star])
    cls = class_of_bins(bins, nrt, d0, n_classes)
    M = np.zeros((bins.n + 1, n_classes + 1))
    M[np.arange(bins.n + 1), cls] = 1.0
    F1c, Lc, F3c = F1 @ M, Lh @ M, F3 @ M
    ndiv = int(div.max()) + 1 if len(div) else 0
    Fd = np.zeros((ndiv, n_classes + 1))
    Ld = np.zeros((ndiv, n_classes + 1))
    np.add.at(Fd, div, F1c)
    np.add.at(Ld, div, Lc)
    Fp, Lp = Fd.sum(axis=0), Ld.sum(axis=0)
    pooled = np.where(Fp > 0, Lp / np.where(Fp > 0, Fp, 1.0), 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        freq = np.where(Fd > 0, Ld / np.where(Fd > 0, Fd, 1.0), np.nan)
    fc = freq[div]
    fb = np.isnan(fc)
    fallback_px = float((F3c * fb).sum())
    fc = np.where(fb, pooled[None, :], fc)
    s, all_capped = solve_scale(F3c.ravel(), fc.ravel(), Q)
    with np.errstate(invalid="ignore"):
        e = np.minimum(1.0, (s * fc) if np.isfinite(s) else np.where(fc > 0, 1.0, 0.0))
    exp_cell = (F3c * e).sum(axis=1)
    got = float(exp_cell.sum())
    if not all_capped and abs(got - Q) > QTY_RTOL * max(1.0, Q):
        _refuse("the allocated total %.9g differs from the quantity %.9g" % (got, Q))
    x[has] = exp_cell[has] / forest2000[has]
    rep.update({"nrt_m": nrt, "nrt_bin": b_star, "e0_m": min(float(d0), nrt / 2.0), "scale": s,
                "all_capped": bool(all_capped), "capped_px": float((F3c * (e >= 1.0)).sum()),
                "fallback_px": fallback_px, "forest_T3_px": float(F3c.sum()), "allocated": got,
                "divisions": ndiv})
    return x, rep


# ---------------------------------------------------------------------------------------------------- build
def _division_codes(files: "PrepFiles", region: str, cell_id: np.ndarray) -> Tuple[np.ndarray, str]:
    import pyarrow.parquet as pq
    name = "%s/%s" % (region, DP.DIVISION_FILE)
    d = pq.read_table(str(files.path(name))).to_pandas()
    if list(d["cell_id"].astype(str)) != list(cell_id):
        _refuse("%s: the division table's cells differ from the static cells (order or set)" % name)
    codes, _ = pd.factorize(d["division"].astype(str), sort=True)
    return codes.astype(np.int64), name


def build(ctx: Any, rival: Mapping[str, Any], lead: int, stage: str) -> pd.DataFrame:
    """The VT0007 index table of one lead and stage (SPEC_HUMAN 3)."""
    opt = lambda n, d=None: DP.opt(rival, n, d)  # noqa: E731
    if stage not in ("train", "test"):
        _refuse("VT0007 reads target observations in the test window; it is built in stages train / test, not %r"
                % stage)
    if stage == "test":
        DP.require_lock(ctx, "VT0007 stage test of %s" % rival.get("id"))
    stages = ["train"] if stage == "train" else ["train", "test"]
    keys = ctx.keys("stage")[list(KEYS)].reset_index(drop=True)
    if (keys["lead"].astype("int64") != int(lead)).any():
        _refuse("ctx.keys gave rows of another lead")
    fit_cut = int(ctx.run.cuts[0]["fit_cut"])
    hrp = int(opt("hrp_years"))
    t_min = int(opt("first_loss_year")) + hrp
    frozen = rival.get("options", {}).get("frozen_year")
    bins = DP.FineBins(float(opt("d_lo_m")), float(opt("d_max_m")), int(opt("n_bins")))
    files = PrepFiles(ctx, rival)
    static = DP._static_cells(ctx, rival)
    static_name = str(opt("static_file"))
    t = keys["time"].astype("int64").values
    t_eff = t.copy() if frozen is None else np.minimum(t, int(frozen) + 1)
    if stage == "train" and (t > fit_cut).any():
        _refuse("stage train got a row with issue year after the fit cut %d" % fit_cut)

    n = len(keys)
    x = np.full(n, np.nan)
    src = np.array([static_name] * n, dtype=object)
    reports: Dict[str, Any] = {}
    for reg in sorted(keys["group"].astype(str).unique()):
        cells = static[static["region"].astype(str) == reg].reset_index(drop=True)
        cid = cells["cell_id"].astype(str).values
        pos = pd.Series(np.arange(len(cid)), index=cid)
        rsel = np.where(keys["group"].astype(str).values == reg)[0]
        units = keys["unit"].astype(str).values[rsel]
        missing = ~pd.Index(units).isin(pos.index)
        if missing.any():
            _refuse("unit %s of group %s is not a static cell of that region" % (units[missing][0], reg))
        ci = pos.loc[units].values
        f2000 = cells["forest2000_px"].astype("float64").values
        need_years = sorted(set(t_eff[rsel][t_eff[rsel] >= t_min].tolist()))
        if not need_years:
            continue
        rc = RegionCounts(files, reg, stages, len(cid), bins)
        if rc.parity_forest is None or not np.array_equal(rc.parity_forest.astype("float64"), f2000):
            _refuse("%s: the static forest2000_px differs from the prep's parity count" % reg)
        div, div_name = _division_codes(files, reg, cid)
        for ty in need_years:
            T1, T3 = ty - hrp - 1, ty - 1
            years = list(range(ty - hrp, ty))
            if max(years) > ty - 1 or T3 > ty - 1:
                _refuse("issue year %d would read loss past t - 1" % ty)
            xc, rep = vt0007_region(rc.forest_dense(T1), rc.loss_dense(T1, years), rc.forest_dense(T3), div, f2000,
                                    bins, hrp)
            reports["%s:%d" % (reg, ty)] = rep
            rows = rsel[t_eff[rsel] == ty]
            x[rows] = xc[pos.loc[keys["unit"].astype(str).values[rows]].values]
            src[rows] = DP_SEP.join(rc.src_of(T1, T3, years) + [div_name, static_name])
    covered = (t >= t_min)
    x[~covered] = np.nan
    # timing (review issue 1): the loss years t_eff-10 .. t_eff-1 and the forest map at the end of t_eff-1 are TARGET
    # observations (the target is Hansen loss), so they go to target_obs_end and T2 guards them (labels to t-1 at
    # lead 0 and lead 1). info_end is the newest NON-label input: treecover2000 / datamask (registry option
    # driver_info_end, the year 2000); GADM is fixed geography (disclosed). Writing info_end = t-1 made T1 (issue - S,
    # S = 1 on the run's R8) refuse every lead-1 row.
    drv_end = int(opt("driver_info_end"))
    if drv_end >= t_min:
        _refuse("driver_info_end %d is not before the first covered target year %d" % (drv_end, t_min))
    out = keys.copy()
    out[str(opt("stat"))] = x
    out["info_end"] = np.full(n, drv_end, dtype="int64")
    out["target_obs_end"] = (t_eff - 1).astype("float64")
    out["product_cell"] = keys["unit"].astype(str).values
    out["src"] = src.astype(str)
    report = {"format": ADAPTER_FORMAT, "rival": rival.get("id"), "lead": int(lead), "stage": stage,
              "frozen_year": frozen, "t_min": t_min, "rows": n, "covered": int(np.isfinite(x).sum()),
              "not_covered_years_before_t_min": int((~covered).sum()),
              "not_covered_no_forest2000": int((covered & ~np.isfinite(x)).sum()), "groups_years": reports}
    out.attrs["adapter_report"] = report
    ctx.log("%s lead %d stage %s: %d rows, covered %d (issue years from %d; frozen %s)"
            % (rival.get("id"), lead, stage, n, report["covered"], t_min, frozen))
    return out
