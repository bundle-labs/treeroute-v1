"""Shared pieces of the two fire lag runners: adapters/fire_enso.py (ENSO-lag regression) and adapters/fire_turco.py
(SPI-lag climate-fire model). SPEC_HUMAN_PARTB.txt section 4 (common rules), 4.3; the M-runner contract of
rivals_human/methods.py; adapters/ndvi_bardl.py as the style template.

Both runners are normal-anchored ratio models fitted per group (region) on the fit set's rows:
    y_hat = N (1 + b s)        N = the row's identity normal as the slim gives the set (ngd__ on guardfit / guard,
                                   nfit__ on refit / test; in sample on fit rows), s = a lagged climate index
    b = sum(N s (y - N)) / sum((N s)^2)   least squares through the origin of y - N on N s (fit_ratio); fewer than
                                   min_fit_rows usable rows, or sum((N s)^2) == 0 -> b = 0 (the normal), flagged
Usable fit row: finite y, finite N > 0 (a zero normal gives no ratio), valid predictor (finite, |s| <= the rival's
cap). At prediction an invalid predictor is set to 0 (pre = N, counted; the AG3 rule of H1), a group unseen in the
params predicts N (counted), a row with N <= 0 predicts N (no ratio; 0 on the zero-normal rows), a NaN normal refuses.
Fire season of a group: the `width` consecutive calendar months (cyclic, Dec-Jan-Feb allowed) of largest summed N
over the group's fit rows; ties -> the earliest start month (fire_season).

Sets: fit on "guardfit" (scored on "guard") or "refit" (scored on "test"); no lead-0 row (registry tier none).
Timing (index.Timing; methods.run_predict checks it): info_end = issue - S, S = max R8 `steps` of the rival's
t1_kind_columns (read from ctx.run at fit, kept in the params); target_obs_end = the newest label step behind the
row's normal and b = run.cuts[L]["guard_cut"] - R17 offset on guard rows, run.cuts[L]["fit_cut"] - offset on test
rows (the engine's own convention).

Label access (review test R02, review_tests/test_r02_runner_label_scope.py:71-88): the one label call is written
literally ctx.fit_labels(fit_set), in a helper whose parameter is named fit_set, called only from a runner's fit. No
code here touches the slim reader, the harness context or the lock token.
"""
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

KEYS = ("unit", "group", "time", "issue", "lead")
LINK = "identity"                       # both forms work in burned-fraction units on the identity normal
FIT_SETS = ("guardfit", "refit")        # spec 4: fit sets of the lag runners (no lead-0 "tune")
SCORE_OF = {"guardfit": "guard", "refit": "test"}
CUT_OF = {"guard": "guard_cut", "test": "fit_cut"}   # the cut whose labels stand behind a score set's normal
MONTHS_PER_YEAR = 12                    # calendar months of the monthly fire panel (R2 month_of_year)
SINGULAR_TOL = 1e-10                    # fit_ratio2: det <= SINGULAR_TOL * a11 * a22 (|corr| ~ 1) -> singular


class FireLagRefusal(RuntimeError):
    """A fire lag-runner rule refused (fail loud; never caught inside the runners)."""


def _refuse(message: str, fix: Optional[str] = None):
    raise FireLagRefusal(message + ("" if not fix else "  FIX: " + fix))


# ---------------------------------------------------------------------------------------------------
# Run facts (read, never hand-set)
def run_offset(run: Any) -> int:
    """R17 start_offset_steps, read as the tool's Timing reads it (0 when the run keeps none)."""
    v = (run.derived.get("R17") or {}).get("value") or {}
    return int(v.get("start_offset_steps") or 0)


def check_monthly(run: Any) -> None:
    """The forms use calendar months of the target: refuse a run that states another number of steps per year
    (R2 value, else R17 inputs)."""
    spy = ((run.derived.get("R2") or {}).get("value") or {}).get("steps_per_year")
    if spy is None:
        spy = ((run.derived.get("R17") or {}).get("inputs") or {}).get("steps_per_year")
    if spy is not None and int(spy) != MONTHS_PER_YEAR:
        _refuse("the fire lag runners use calendar months; the run has %r steps per year" % (spy,))


def t1_steps(run: Any, rival: Mapping[str, Any]) -> int:
    """S = max R8 `steps` over the rival's t1_kind_columns (enso_lag: oni 3; turco_spi: spi_* 0)."""
    cols = [str(c) for c in (rival.get("t1_kind_columns") or [])]
    if not cols:
        _refuse("rival %s names no t1_kind_columns; the runner's info_end is issue - max R8 steps of them"
                % rival.get("id"))
    r8 = (run.derived.get("R8") or {}).get("value") or {}
    unknown = [c for c in cols if c not in r8]
    if unknown:
        _refuse("rival %s: t1_kind_columns %s are not R8 entries of the run" % (rival.get("id"), unknown))
    steps = []
    for c in cols:
        e = r8[c]
        if not isinstance(e, Mapping) or e.get("steps") is None:
            _refuse("R8 entry %s of the run holds no steps" % c)
        steps.append(int(e["steps"]))
    return max(steps)


def fitted_t1_steps(ctx: Any, rival: Mapping[str, Any], params: Mapping[str, Any], what: str) -> int:
    """S of a prediction = the R8 steps the params were fitted under (read from ctx.run at fit): the lag of the
    predictor the model was built on. The run's R8 is re-read; a difference is logged and left to the tool's T1 check
    (methods.run_predict), which refuses a lag shorter than the run allows and passes a longer one. An R17 offset that
    differs from the fit's refuses (the labels behind b would not be the run's)."""
    now = t1_steps(ctx.run, rival)
    fitted = int(params["t1_steps"])
    if int(params["start_offset_steps"]) != run_offset(ctx.run):
        _refuse("%s params were fitted under R17 offset %s; the run has %d"
                % (what, params.get("start_offset_steps"), run_offset(ctx.run)))
    if now != fitted:
        ctx.log("%s: the params were fitted with R8 steps %d, the run now says %d; info_end = issue - %d (the tool's "
                "T1 check decides)" % (what, fitted, now, fitted))
    return fitted


def check_lead(lead: int) -> None:
    if int(lead) < 1:
        _refuse("the fire lag runners have no lead-0 row (registry tier none at the nowcast); lead %d asked"
                % int(lead))


def target_months(time: Any) -> np.ndarray:
    """Calendar month (1..12) of the TARGET step t: ((t - 1) mod 12) + 1 (step = year x 12 + month)."""
    return np.mod(np.asarray(time, dtype=np.int64) - 1, MONTHS_PER_YEAR) + 1


def info_end(keys: pd.DataFrame, s_steps: int) -> np.ndarray:
    return keys["issue"].to_numpy(np.int64) - int(s_steps)


def target_obs_end(run: Any, lead: int, score_set: str, offset: int) -> int:
    if score_set not in CUT_OF:
        _refuse("the fire lag runners score %s only, not %r" % (sorted(CUT_OF), score_set))
    return int(run.cuts[int(lead)][CUT_OF[score_set]]) - int(offset)


def score_set_of(params: Mapping[str, Any], score_set: str, what: str) -> None:
    """Refuse any pairing but guardfit -> guard and refit -> test."""
    fs = str(params.get("fit_set"))
    if fs not in SCORE_OF:
        _refuse("%s params were fitted on %r, not a fit set %s" % (what, fs, FIT_SETS))
    if score_set != SCORE_OF[fs]:
        _refuse("%s params fitted on %s score the %s set, not %r" % (what, fs, SCORE_OF[fs], score_set))


# ---------------------------------------------------------------------------------------------------
# Slim access (features of any set; labels of the fit set inside fit only)
def inputs(ctx: Any, lead: int, set_name: str, columns: Sequence[str]) -> Tuple[pd.DataFrame, np.ndarray,
                                                                              pd.DataFrame]:
    """(keys, N identity normal, the named extra columns as float64) of a set; never y."""
    ss = ctx.features(set_name)
    if getattr(ss, "y", None) is not None:
        _refuse("ctx.features(%s) handed a label column to the runner; labels come only through fit_labels"
                % set_name)
    normals = ss.normal
    if LINK not in normals:
        _refuse("slim set %s holds no %s normal" % (set_name, LINK))
    keys = ss.keys[list(KEYS)].reset_index(drop=True)
    N = np.asarray(normals[LINK], dtype=np.float64)
    extras = ss.extras.reset_index(drop=True)
    miss = [c for c in columns if c not in extras.columns]
    if miss:
        _refuse("slim set %s lacks the extra columns %s; the registry's slim_extra_columns must name them"
                % (set_name, miss))
    if len(N) != len(keys) or len(extras) != len(keys):
        _refuse("slim set %s: keys, normal and extras differ in length" % set_name)
    if (keys["lead"].to_numpy(np.int64) != int(lead)).any():
        _refuse("slim set %s holds rows of another lead" % set_name)
    X = pd.DataFrame({c: extras[c].to_numpy(np.float64) for c in columns})
    return keys, N, X


def labels(ctx: Any, fit_set: str, keys: pd.DataFrame) -> np.ndarray:
    """y of the fit set, aligned row for row with the features' keys (refuses any difference). Called from fit only."""
    lk, y, _ = ctx.fit_labels(fit_set)
    lk = lk.reset_index(drop=True)
    y = np.asarray(y, dtype=np.float64)
    if len(lk) != len(keys) or y.shape != (len(keys),):
        _refuse("fit labels of %s hold %d rows, the features %d" % (fit_set, len(lk), len(keys)))
    for k in ("unit", "time", "issue"):
        if not np.array_equal(lk[k].to_numpy(), keys[k].to_numpy()):
            _refuse("fit labels of %s are not in the features' row order (key %s)" % (fit_set, k))
    return y


# ---------------------------------------------------------------------------------------------------
# The fits (pure functions; toy-tested)
def valid_predictor(v: Any, abs_max: float) -> Tuple[np.ndarray, int, int]:
    """(v with invalid values set to NaN, rows missing, rows beyond +-abs_max)."""
    v = np.asarray(v, dtype=np.float64)
    nan = ~np.isfinite(v)
    oor = np.isfinite(v) & (np.abs(v) > float(abs_max))
    out = v.copy()
    out[nan | oor] = np.nan
    return out, int(nan.sum()), int(oor.sum())


def fire_season(groups: Any, months: Any, normal: Any, width: int) -> Dict[str, List[int]]:
    """{group: [m1, .., m_width]}: the `width` consecutive calendar months (cyclic) with the largest sum of the
    finite normal over the group's rows, listed from the start month (a Dec-Jan-Feb season is [12, 1, 2]); ties ->
    the earliest start month (January first)."""
    width = int(width)
    if not 1 <= width <= MONTHS_PER_YEAR:
        _refuse("fire_season_months %d is not in 1..%d" % (width, MONTHS_PER_YEAR))
    g = np.asarray(groups).astype(str)
    m = np.asarray(months, dtype=np.int64)
    n = np.asarray(normal, dtype=np.float64)
    if g.shape != m.shape or m.shape != n.shape:
        _refuse("fire_season: groups, months and normal differ in length")
    if ((m < 1) | (m > MONTHS_PER_YEAR)).any():
        _refuse("fire_season: a calendar month outside 1..%d" % MONTHS_PER_YEAR)
    ok = np.isfinite(n)
    out: Dict[str, List[int]] = {}
    for grp in sorted(set(g.tolist())):
        sel = ok & (g == grp)
        tot = np.bincount(m[sel] - 1, weights=n[sel], minlength=MONTHS_PER_YEAR)
        best_s, best_v = 0, None
        for s in range(MONTHS_PER_YEAR):
            v = 0.0
            for i in range(width):
                v += float(tot[(s + i) % MONTHS_PER_YEAR])
            if best_v is None or v > best_v:          # strict: a tie keeps the earlier start
                best_s, best_v = s, v
        out[grp] = [int((best_s + i) % MONTHS_PER_YEAR) + 1 for i in range(width)]
    return out


def usable(N: np.ndarray, y: np.ndarray, *preds: np.ndarray) -> np.ndarray:
    """Rows a fit may use: finite y, finite N > 0, every predictor finite (invalid ones are NaN already)."""
    ok = np.isfinite(y) & np.isfinite(N) & (N > 0)
    for p in preds:
        ok &= np.isfinite(p)
    return ok


def fit_ratio(N: Any, s: Any, y: Any, min_rows: int) -> Tuple[float, int, bool]:
    """(b, n, fallback) of y = N (1 + b s) by least squares through the origin of y - N on N s, over the usable
    rows; < min_rows usable rows or sum((N s)^2) == 0 -> (0.0, n, True) = the normal."""
    N = np.asarray(N, dtype=np.float64)
    s = np.asarray(s, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    use = usable(N, y, s)
    n = int(use.sum())
    a = N[use] * s[use]
    den = float(np.dot(a, a))
    if n < int(min_rows) or not den > 0.0:
        return 0.0, n, True
    return float(np.dot(a, y[use] - N[use])) / den, n, False


def fit_ratio2(N: Any, s1: Any, s2: Any, y: Any, min_rows: int) -> Tuple[float, float, int, bool]:
    """(b1, b2, n, fallback) of y - N = b1 N s1 + b2 N s2 through the origin (2 x 2 normal equations) over the rows
    where both predictors are valid; < min_rows rows, a zero column or a singular system (det <= SINGULAR_TOL x
    a11 x a22) -> (0.0, 0.0, n, True)."""
    N = np.asarray(N, dtype=np.float64)
    s1 = np.asarray(s1, dtype=np.float64)
    s2 = np.asarray(s2, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    use = usable(N, y, s1, s2)
    n = int(use.sum())
    a1, a2 = N[use] * s1[use], N[use] * s2[use]
    t = y[use] - N[use]
    a11, a22, a12 = float(np.dot(a1, a1)), float(np.dot(a2, a2)), float(np.dot(a1, a2))
    det = a11 * a22 - a12 * a12
    if n < int(min_rows) or not (a11 > 0.0 and a22 > 0.0) or not det > SINGULAR_TOL * a11 * a22:
        return 0.0, 0.0, n, True
    r1, r2 = float(np.dot(a1, t)), float(np.dot(a2, t))
    return (a22 * r1 - a12 * r2) / det, (a11 * r2 - a12 * r1) / det, n, False


def anchored(N: np.ndarray, term: np.ndarray) -> np.ndarray:
    """pre = N (1 + term) where N > 0; N itself where N <= 0 (no ratio: 0 on a zero normal). A NaN N refuses."""
    N = np.asarray(N, dtype=np.float64)
    term = np.asarray(term, dtype=np.float64)
    if not np.isfinite(N).all():
        _refuse("%d score rows have no finite normal (never seen on the export; coverage all_rows needs one)"
                % int((~np.isfinite(N)).sum()))
    return np.where(N > 0, N * (1.0 + term), N)


def group_params(params: Mapping[str, Any]) -> Mapping[str, Any]:
    """The per-group block of a runner's params (the whole params, or fit_groups' result, or the block itself)."""
    g = params.get("groups") if isinstance(params, Mapping) else None
    return g if isinstance(g, Mapping) else params


__all__ = ["KEYS", "LINK", "FIT_SETS", "SCORE_OF", "CUT_OF", "MONTHS_PER_YEAR", "SINGULAR_TOL", "FireLagRefusal",
           "run_offset", "check_monthly", "t1_steps", "fitted_t1_steps", "check_lead", "target_months", "info_end",
           "target_obs_end", "score_set_of", "inputs", "labels", "valid_predictor", "fire_season", "usable",
           "fit_ratio", "fit_ratio2", "anchored", "group_params"]
