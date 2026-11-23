"""NDVI human rival H1: per-unit Bayesian autoregressive distributed lag (BARDL / AstroCast family).

SPEC_HUMAN.txt section 5 (Builder C); research_ndvi.md section 3; PLAN :66-68; rulings Q8 a, Q9 (published
inputs only: precipitation and soil moisture, no VPD).

Kind M (a published method, F0: no extra map). Per scored unit u and lead L, a direct model:
    target      a(t) = y(t) - z0          z0 = the row's identity normal (ngd__ on guard-side sets, nfit__ on
                                          refit/test; the slim reader gives each set its own normal)
    predictors  (11 columns)
      NDVI anomaly lags k = 1..3: hist_last_k minus the unit's identity normal at the season key of that label
                  step (T2 step - (k - 1)); a missing lag or normal -> 0 (= the normal), counted
      precipitation and soil-moisture anomalies at the issue step i, i-1, i-2 (registry `climate` columns),
                  minus the unit x calendar-month mean of the column's own month over the SAME fit set's rows,
                  and their 3-month means (mean of the three anomalies) -> 3 + 3 + 2 = 8
    fit         sklearn BayesianRidge (defaults; deterministic) per unit on the fit set's rows with a finite
                target and finite climate anomalies ("complete" rows); < MIN_FIT_ROWS complete rows -> the unit
                predicts its normal (counted, disclosed; PLAN R12)
    predict     pre = z0 + a_hat (pre-clip; the tool clips with clip_to_legal and keeps pre, PROT H9)
Scored units only (per-unit methods predict the units they were fitted on, PROT H7); rows of other units get no
prediction (not covered).

Timing (SPEC_HUMAN 1.5): info_end = the issue step i (climate read at i; R8 steps 0 for the V02/V30 columns);
target_obs_end = the T2 step = latest_label_step(t, L) - R17 start_offset_steps (treeroute/timing/cuts.py:50-60:
t-1 at lead 0, t-L at L >= 1), the step hist_last_1 reads (pipeline/ladder.py:880-893).
reads_target_in_test_window = true: the tool runs predict on test rows only after the human lock (A2).

The AdapterCtx calls used here (contract in BUILD_NOTES_pm25_ndvi.txt; SPEC_HUMAN section 6):
  ctx.run                          the common harness Run: .derived (R17), .cuts
  ctx.units                        units.parquet as a DataFrame (unit, group, is_scored, ...)
  ctx.index_keys(lead, stage)      keys of the rows of an index-table stage (build only)
  ctx.read_inputs(lead, set_name)  (keys, {link: normal}, history DataFrame, extras DataFrame) of one slim set,
                                   NO labels; guard-side substitution applied (H:859-877)
  ctx.fit_labels(lead, set_name)   y of a FIT set (tune, refit, guardfit) in read_inputs row order; refuses others
  ctx.log(message)
"""
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

ADAPTER_FORMAT = "human-adapter-ndvi-bardl/1"
PARAMS_FORMAT = "human-bardl-params/1"
KEYS = ("unit", "group", "time", "issue", "lead")
MIN_FIT_ROWS = 36                # research_ndvi.md section 3 "fewer than 36 complete train rows -> the normal"
N_LAGS = 3                       # BARDL's 3 NDVI lags (Barrett AR order p = 3)
CLIMATE_LAGS = (0, 1, 2)         # climate at i, i-1, i-2 (PLAN :66)
LINK = "identity"                # H1 works in NDVI units (F0)
FIT_SETS = ("tune", "refit", "guardfit")
SCORE_OF = {"tune": "inner", "guardfit": "guard", "refit": "test"}
NORMAL_TOL = 1e-12               # a unit's normal must be one value per season key inside one set


class BardlRefusal(RuntimeError):
    """An H1 rule refused (fail loud)."""


def _refuse(message: str, fix: Optional[str] = None):
    raise BardlRefusal(message + ("" if not fix else "  FIX: " + fix))


# ---------------------------------------------------------------------------------------------------
# Run facts (read, never hand-set)
def run_timing(run: Any) -> Tuple[int, int]:
    """(steps_per_year, R17 start_offset_steps) from derived.json."""
    r17 = run.derived["R17"]
    spy = int(r17["inputs"]["steps_per_year"])
    off = int(r17["value"]["start_offset_steps"])
    if spy < 1 or off < 0:
        _refuse("derived R17 steps_per_year %d / start_offset_steps %d are not usable" % (spy, off))
    return spy, off


def season_key(step: np.ndarray, spy: int) -> np.ndarray:
    """R2's season key ((step - 1) mod steps per year) + 1 (treeroute/fit/context.py:264-277)."""
    return np.mod(np.asarray(step, dtype=np.int64) - 1, int(spy)) + 1


def t2_step(time: np.ndarray, lead: int, offset: int) -> np.ndarray:
    """The newest label step a row may read: latest_label_step(t, L) - offset (cuts.py:50-60; LAD:880-893)."""
    t = np.asarray(time, dtype=np.int64)
    latest = t - 1 if int(lead) == 0 else t - int(lead)
    return latest - int(offset)


def _options(rival: Mapping[str, Any]) -> Dict[str, Any]:
    opt = dict(rival.get("options") or {})
    for k in ("history", "climate"):
        if k not in opt:
            _refuse("rival %s: registry options lack %r" % (rival.get("id"), k))
    hist = list(opt["history"])
    if len(hist) != N_LAGS:
        _refuse("rival %s: options.history must name %d history columns (hist_last_1..3), got %s"
                % (rival.get("id"), N_LAGS, hist))
    clim = dict(opt["climate"])
    for var, cols in clim.items():
        if len(list(cols)) != len(CLIMATE_LAGS):
            _refuse("rival %s: climate %s must name %d columns (issue, issue-1, issue-2)" % (rival.get("id"), var,
                                                                                          len(CLIMATE_LAGS)))
    opt["history"] = hist
    opt["climate"] = {str(v): [str(c) for c in cols] for v, cols in clim.items()}
    opt["min_fit_rows"] = int(opt.get("min_fit_rows", MIN_FIT_ROWS))
    return opt


def feature_names(opt: Mapping[str, Any]) -> List[str]:
    names = ["ndvi_anom_lag%d" % k for k in range(1, N_LAGS + 1)]
    for var in opt["climate"]:
        names += ["%s_anom_l%d" % (var, l) for l in CLIMATE_LAGS]
    names += ["%s_anom_mean3" % var for var in opt["climate"]]
    return names


def _col(df: pd.DataFrame, name: str) -> np.ndarray:
    """A slim column by its bare name, accepting the export prefixes (x__ fit side, h__ guard side)."""
    for c in (name, "x__" + name, "h__" + name):
        if c in df.columns:
            return df[c].to_numpy(np.float64)
    _refuse("slim set lacks the column %s (x__/h__ prefixes tried); the slim copy must carry it "
            "(registry slim_extra_columns, SPEC_HUMAN A5)" % name)


def _scored_units(ctx: Any) -> set:
    u = ctx.units
    if "is_scored" not in u.columns:
        _refuse("units.parquet has no is_scored column; H1 fits scored units only (PROT H7)")
    return set(u.loc[u["is_scored"].astype(bool), "unit"].astype(str))


def _inputs(ctx: Any, lead: int, set_name: str):
    got = ctx.read_inputs(int(lead), set_name)
    if not (isinstance(got, tuple) and len(got) == 4):
        _refuse("ctx.read_inputs must return (keys, normals, history, extras)")
    keys, normals, history, extras = got
    if LINK not in normals:
        _refuse("slim set %s holds no %s normal" % (set_name, LINK))
    keys = keys[list(KEYS)].reset_index(drop=True)
    z0 = np.asarray(normals[LINK], dtype=np.float64)
    if len(z0) != len(keys) or len(history) != len(keys) or len(extras) != len(keys):
        _refuse("slim set %s: keys, normals, history and extras differ in length" % set_name)
    if (keys["lead"].to_numpy(np.int64) != int(lead)).any():
        _refuse("slim set %s holds rows of another lead" % set_name)
    return keys, z0, history.reset_index(drop=True), extras.reset_index(drop=True)


# ---------------------------------------------------------------------------------------------------
# The design matrix (pure functions; toy-tested)
def unit_normals(units: np.ndarray, sk: np.ndarray, z0: np.ndarray) -> Dict[Tuple[str, int], float]:
    """(unit, season key) -> the set's identity normal (one value per key inside one set, else refuse)."""
    df = pd.DataFrame({"u": units.astype(str), "k": sk.astype(np.int64), "z": z0})
    df = df[np.isfinite(df["z"].to_numpy())]
    g = df.groupby(["u", "k"], sort=True)["z"]
    lo, hi = g.min(), g.max()
    bad = (hi - lo).abs() > NORMAL_TOL
    if bad.any():
        u, k = bad[bad].index[0]
        _refuse("the identity normal of unit %s, season key %d takes %d values inside one set" % (u, k, int(bad.sum())))
    return {(str(u), int(k)): float(v) for (u, k), v in lo.items()}


def climate_means(units: np.ndarray, issue: np.ndarray, extras: pd.DataFrame, opt: Mapping[str, Any],
                  spy: int) -> Dict[str, Dict[str, float]]:
    """{var: {"unit|month": mean}}: the unit x calendar-month mean of the column read AT its own step (the
    issue-step column) over the fit set's rows."""
    out = {}
    cm = season_key(issue, spy)
    for var, cols in opt["climate"].items():
        v = _col(extras, cols[0])
        df = pd.DataFrame({"u": units.astype(str), "k": cm, "v": v})
        df = df[np.isfinite(df["v"].to_numpy())]
        m = df.groupby(["u", "k"], sort=True)["v"].mean()
        out[var] = {"%s|%d" % (u, int(k)): float(x) for (u, k), x in m.items()}
    return out


def design(keys: pd.DataFrame, z0: np.ndarray, history: pd.DataFrame, extras: pd.DataFrame,
           means: Mapping[str, Mapping[str, float]], opt: Mapping[str, Any], lead: int, spy: int,
           offset: int) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
    """(X n x 11, climate_complete bool n, counts). NDVI lag anomalies with missing -> 0; climate anomalies NaN
    where the value or its unit x month mean is missing (the caller decides: fit drops, predict fills 0)."""
    units = keys["unit"].astype(str).to_numpy()
    t = keys["time"].to_numpy(np.int64)
    i = keys["issue"].to_numpy(np.int64)
    nrm = unit_normals(units, season_key(t, spy), z0)
    t2 = t2_step(t, lead, offset)
    cols, counts = [], {}
    n_missing_lag = 0
    for k in range(1, N_LAGS + 1):
        h = _col(history, opt["history"][k - 1])
        sk = season_key(t2 - (k - 1), spy)
        base = np.array([nrm.get((u, int(s)), np.nan) for u, s in zip(units, sk)], dtype=np.float64)
        a = h - base
        miss = ~np.isfinite(a)
        n_missing_lag += int(miss.sum())
        a[miss] = 0.0
        cols.append(a)
    counts["ndvi_lag_values_missing_set_to_0"] = n_missing_lag
    clim_ok = np.ones(len(keys), dtype=bool)
    means3 = []
    for var, names in opt["climate"].items():
        mv = means.get(var) or {}
        an = []
        for l, name in zip(CLIMATE_LAGS, names):
            v = _col(extras, name)
            cm = season_key(i - l, spy)
            mu = np.array([mv.get("%s|%d" % (u, int(c)), np.nan) for u, c in zip(units, cm)], dtype=np.float64)
            a = v - mu
            clim_ok &= np.isfinite(a)
            an.append(a)
            cols.append(a)
        means3.append(np.mean(np.vstack(an), axis=0))
    cols += means3
    X = np.column_stack(cols).astype(np.float64)
    counts["rows_climate_incomplete"] = int((~clim_ok).sum())
    return X, clim_ok, counts


# ---------------------------------------------------------------------------------------------------
# The M runner (SPEC_HUMAN section 6): fit(ctx, rival, lead, fit_set) -> params; predict(...) -> DataFrame
def fit(ctx: Any, rival: Mapping[str, Any], lead: int, fit_set: str) -> Dict[str, Any]:
    from sklearn.linear_model import BayesianRidge

    if fit_set not in FIT_SETS:
        _refuse("H1 fits on a fit set (%s), not %r" % ("/".join(FIT_SETS), fit_set))
    opt = _options(rival)
    spy, offset = run_timing(ctx.run)
    keys, z0, history, extras = _inputs(ctx, lead, fit_set)
    y = np.asarray(ctx.fit_labels(int(lead), fit_set), dtype=np.float64)
    if y.shape != (len(keys),):
        _refuse("fit labels of %s hold %s values for %d rows" % (fit_set, y.shape, len(keys)))
    scored = _scored_units(ctx)
    units = keys["unit"].astype(str).to_numpy()
    keep = np.array([u in scored for u in units], dtype=bool)
    keys, z0, y = keys[keep].reset_index(drop=True), z0[keep], y[keep]
    history, extras = history[keep].reset_index(drop=True), extras[keep].reset_index(drop=True)
    units = units[keep]
    means = climate_means(units, keys["issue"].to_numpy(np.int64), extras, opt, spy)
    X, clim_ok, counts = design(keys, z0, history, extras, means, opt, lead, spy, offset)
    a = y - z0
    ok = clim_ok & np.isfinite(a)
    models: Dict[str, Any] = {}
    n_fallback = 0
    okpos = np.flatnonzero(ok)
    by_unit = pd.Series(okpos).groupby(units[okpos], sort=True).indices if okpos.size else {}
    for u in sorted(scored):
        rows = okpos[by_unit[u]] if u in by_unit else np.zeros(0, dtype=np.int64)
        if rows.size < opt["min_fit_rows"]:
            models[u] = {"fallback": True, "n": int(rows.size)}
            n_fallback += 1
            continue
        m = BayesianRidge()
        m.fit(X[rows], a[rows])
        models[u] = {"fallback": False, "n": int(rows.size), "coef": [float(c) for c in m.coef_],
                     "intercept": float(m.intercept_), "alpha": float(m.alpha_), "lambda": float(m.lambda_)}
    counts.update({"units_scored": len(scored), "units_fallback_normal": n_fallback,
                   "rows_fit_set": int(len(keys)), "rows_complete": int(ok.sum())})
    ctx.log("H1 %s lead %d fit on %s: %d units, %d fall back to the normal (< %d complete rows), %d complete rows "
            "of %d" % (rival.get("id"), int(lead), fit_set, len(scored), n_fallback, opt["min_fit_rows"],
                       int(ok.sum()), len(keys)))
    return {"format": PARAMS_FORMAT, "adapter": ADAPTER_FORMAT, "rival": rival.get("id"), "lead": int(lead),
            "fit_set": fit_set, "features": feature_names(opt), "min_fit_rows": opt["min_fit_rows"],
            "steps_per_year": spy, "start_offset_steps": offset, "climate_means": means, "units": models,
            "counts": counts, "estimator": "sklearn.linear_model.BayesianRidge() defaults"}


def predict(ctx: Any, rival: Mapping[str, Any], lead: int, params: Mapping[str, Any],
            score_set: str) -> pd.DataFrame:
    """DataFrame(keys, pre, info_end, target_obs_end) for the scored units' rows of the score set. No label is
    read here (fit_labels is never called)."""
    opt = _options(rival)
    if params.get("format") != PARAMS_FORMAT or int(params.get("lead", -1)) != int(lead):
        _refuse("H1 params are not %s params of lead %d" % (PARAMS_FORMAT, int(lead)))
    if params["features"] != feature_names(opt):
        _refuse("H1 params were fitted with other predictors %s" % params["features"])
    want = SCORE_OF.get(str(params.get("fit_set")))
    if want is not None and score_set != want:
        _refuse("H1 params fitted on %s score the %s set, not %r" % (params.get("fit_set"), want, score_set))
    spy, offset = run_timing(ctx.run)
    if spy != int(params["steps_per_year"]) or offset != int(params["start_offset_steps"]):
        _refuse("H1 params were fitted under another R17 (steps per year / start offset)")
    keys, z0, history, extras = _inputs(ctx, lead, score_set)
    models = params["units"]
    units = keys["unit"].astype(str).to_numpy()
    keep = np.array([u in models for u in units], dtype=bool)
    keys, z0 = keys[keep].reset_index(drop=True), z0[keep]
    history, extras = history[keep].reset_index(drop=True), extras[keep].reset_index(drop=True)
    units = units[keep]
    X, clim_ok, counts = design(keys, z0, history, extras, params["climate_means"], opt, lead, spy, offset)
    filled = ~np.isfinite(X)
    X = np.where(filled, 0.0, X)
    a_hat = np.zeros(len(keys))
    n_fallback_rows = 0
    for u, rows in pd.Series(np.arange(len(units))).groupby(units, sort=True).indices.items():
        m = models[u]
        if m["fallback"]:
            n_fallback_rows += rows.size
            continue
        a_hat[rows] = float(m["intercept"]) + X[rows] @ np.asarray(m["coef"], dtype=np.float64)
    if not np.isfinite(z0).all():
        _refuse("H1 %s: %d score rows have no normal" % (score_set, int((~np.isfinite(z0)).sum())))
    out = keys.copy()
    out["pre"] = z0 + a_hat
    out["info_end"] = keys["issue"].to_numpy(np.int64)
    out["target_obs_end"] = t2_step(keys["time"].to_numpy(np.int64), lead, offset).astype(np.int64)
    ctx.log("H1 %s lead %d predict on %s: %d rows, %d rows of fallback units (normal), %d rows with a climate value "
            "filled by 0 (its unit x month mean), %d NDVI lag values missing -> 0"
            % (rival.get("id"), int(lead), score_set, len(out), n_fallback_rows,
               int(filled.any(axis=1).sum()), counts["ndvi_lag_values_missing_set_to_0"]))
    return out


# ---------------------------------------------------------------------------------------------------
# The index table (SPEC_HUMAN 1.4): timing and label-free coverage, no stat value (kind M)
def build(ctx: Any, rival: Mapping[str, Any], lead: int, stage: str) -> pd.DataFrame:
    """Keys, x__covered (1.0 on scored units, NaN elsewhere; the registry's label-free coverage rule), info_end
    (issue), target_obs_end (T2 step), product_cell (the unit: H1 is per unit), src ("slim")."""
    _options(rival)
    spy, offset = run_timing(ctx.run)
    keys = ctx.index_keys(int(lead), stage)[list(KEYS)].reset_index(drop=True)
    scored = _scored_units(ctx)
    cov = np.array([u in scored for u in keys["unit"].astype(str)], dtype=bool)
    out = keys.copy()
    out["x__covered"] = np.where(cov, 1.0, np.nan)
    out["info_end"] = keys["issue"].to_numpy(np.int64)
    out["target_obs_end"] = t2_step(keys["time"].to_numpy(np.int64), lead, offset).astype(np.float64)
    out["product_cell"] = keys["unit"].astype(str).to_numpy()
    out["src"] = "slim"
    return out


__all__ = ["ADAPTER_FORMAT", "PARAMS_FORMAT", "MIN_FIT_ROWS", "BardlRefusal", "run_timing", "season_key", "t2_step",
           "feature_names", "unit_normals", "climate_means", "design", "fit", "predict", "build"]
