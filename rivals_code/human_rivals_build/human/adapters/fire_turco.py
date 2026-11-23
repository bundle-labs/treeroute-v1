"""Fire human rival turco_spi: SPI-lag climate-fire model (Turco et al. 2018, Nat. Commun. 9:2718; our
implementation, not an operational product).

SPEC_HUMAN_PARTB.txt section 4 (common rules), 4.2 (forms; OWNER DECISION OD-1), 4.3 (params); PLAN :281 (Q20 a:
"observed SPI at the issue month from panel precipitation", a second optional rival beside ENSO-lag).
NO functional form is written in any plan file (PENDING_PARTS Part 620 :1004); the forms below follow the paper's
STRUCTURE as the plan states it - fire-season burned area explained by antecedent SPI, the accumulation scale chosen
on training data, observed (antecedent) SPI only; the paper's seasonal-forecast SPI of the fire season is NOT used (no
SEAS5 precipitation: D5 not approved, Q10). NOT verified against the paper text (no network): an owner decision.

Kind M (a published method, F0: no extra map). Per group (region) g, fitted on the fit set's rows:
    T1 (recommended)  fire season F_g (fire_season_months consecutive months of largest summed normal over the
                      group's fit rows); on the rows in F_g with EVERY scale valid: for each k in options.scales,
                      b_k = least squares through the origin of y - N on N SPI_k, SSE_k = sum (y - N (1 + b_k SPI_k))^2,
                      k* = argmin SSE_k (ties -> the order of options.scales; fewer than min_fit_rows such rows -> the
                      group predicts the normal, flagged); then b_g = the same fit on the rows in F_g with a valid
                      SPI_k*; y_hat = N (1 + b_g SPI_k*(issue)) inside F_g, N outside
    T2                all months, one fixed scale (options.fixed_scale): y_hat = N (1 + b_g SPI)
    T3                inside F_g, two antecedent terms (options.two_scales): y - N = b1 N SPI_a + b2 N SPI_b through
                      the origin (2 x 2 normal equations; singular -> the normal, flagged), N outside F_g
    N    the row's identity normal as the slim gives the set (ngd__ on guardfit / guard, nfit__ on refit / test)
    SPI  the engine's x__spi_* columns at the issue month (R8 steps 0); |SPI| > spi_abs_max (3.5; the panel caps
         at +-3.09, beyond = corrupt, e.g. the precipitation NoData sentinel) or NaN = missing
    b    fire_lag_common.fit_ratio / fit_ratio2; < min_fit_rows usable rows or no spread -> b = 0 (the normal)
The scale choice is part of the method's fit on the fit set's rows only (Turco selects the accumulation from the
data); it is not a pick on inner or guard rows. Sign free.
Prediction: pre-clip on the target scale; a missing SPI -> 0 (pre = N), a group unseen in the params -> N, N <= 0
-> N, all counted; a NaN normal refuses. Every score row gets a finite pre (coverage all_rows).

Timing: info_end = issue - S, S = max R8 steps of t1_kind_columns at fit (spi_* -> 0); target_obs_end = run.cuts[L]
["guard_cut"] - R17 offset on guard rows, ["fit_cut"] - offset on test rows.

The ctx calls used here (SPEC_HUMAN section 6; rivals_human/index.py AdapterCtx):
  ctx.run                  .derived (R2, R8, R17), .cuts[L]["guard_cut" | "fit_cut"]
  ctx.features(set_name)   keys, normal {link: array}, extras (the registry slim_extra_columns); never y
  ctx.fit_labels(fit_set)  (keys, y, normal) of the fit set being fitted, inside fit only (fire_lag_common.labels)
  ctx.log(message)
"""
from typing import Any, Dict, List, Mapping, Tuple

import numpy as np
import pandas as pd

from adapters import fire_lag_common as L
from adapters.fire_lag_common import fire_season, fit_ratio, fit_ratio2, FireLagRefusal

ADAPTER_FORMAT = "human-adapter-fire-turco/1"
PARAMS_FORMAT = "human-fire-turco-params/1"
FORMS = ("T1", "T2", "T3")
DEFAULTS = {"fire_season_months": 3,    # spec 2.4: T1, T3
            "spi_abs_max": 3.5,         # spec 2.4: beyond = corrupt -> missing (counted)
            "min_fit_rows": 100}        # spec 2.4: per group (Q2.HQ9 row floor)
SCALE_KEYS = ("scales", "fixed_scale", "two_scales")
REQUIRED = ("form",)
FORM_SCALES = {"T1": "scales", "T2": "fixed_scale", "T3": "two_scales"}


def _options(rival: Mapping[str, Any]) -> Dict[str, Any]:
    opt = dict(rival.get("options") or {})
    if "form" not in opt:
        L._refuse("rival %s: registry options lack 'form' (OWNER DECISION OD-1)" % rival.get("id"))
    unknown = sorted(k for k in opt if k not in REQUIRED and k not in DEFAULTS and k not in SCALE_KEYS)
    if unknown:
        L._refuse("rival %s: unknown registry options %s (allowed %s)"
                  % (rival.get("id"), unknown, list(REQUIRED) + sorted(DEFAULTS) + list(SCALE_KEYS)))
    out = dict(DEFAULTS)
    out.update(opt)
    out["form"] = str(out["form"])
    if out["form"] not in FORMS:
        L._refuse("rival %s: options.form %r is not one of %s (OWNER DECISION OD-1)" % (rival.get("id"), out["form"],
                                                                                        FORMS))
    need = FORM_SCALES[out["form"]]
    if need not in opt:
        L._refuse("rival %s: form %s needs options.%s" % (rival.get("id"), out["form"], need))
    out["fire_season_months"] = int(out["fire_season_months"])
    out["spi_abs_max"] = float(out["spi_abs_max"])
    out["min_fit_rows"] = int(out["min_fit_rows"])
    if not out["spi_abs_max"] > 0 or out["min_fit_rows"] < 1:
        L._refuse("rival %s: options spi_abs_max / min_fit_rows must be positive" % rival.get("id"))
    columns(out["form"], out)                         # checks the scale names of the form
    return out


def _form(form: Any, opt: Mapping[str, Any]) -> str:
    """The form of a pure-function call: the explicit one (fit_groups' argument, the params' form), else opt's."""
    f = str(form if form is not None else opt.get("form"))
    if f not in FORMS:
        L._refuse("SPI-lag form %r is not one of %s" % (f, FORMS))
    return f


def _opt(opt: Mapping[str, Any], key: str) -> Any:
    """An option of a pure-function call (the runner passes _options(rival); a direct call may leave defaults out)."""
    return opt[key] if key in opt else DEFAULTS[key]


def columns(form: str, opt: Mapping[str, Any]) -> List[str]:
    """The SPI columns a form reads, in the options' order."""
    key = FORM_SCALES[_form(form, opt)]
    if key not in opt:
        L._refuse("SPI-lag form %s needs options.%s" % (form, key))
    v = opt[key]
    cols = [str(v)] if key == "fixed_scale" else [str(c) for c in (v or [])]
    if not cols or len(set(cols)) != len(cols):
        L._refuse("SPI-lag options.%s must name distinct columns, got %r" % (key, v))
    if key == "two_scales" and len(cols) != 2:
        L._refuse("SPI-lag options.two_scales must name exactly 2 columns, got %r" % (v,))
    return cols


# ---------------------------------------------------------------------------------------------------
# The fit and the prediction (pure functions; toy-tested)
def _spi(spi: Any, cols: List[str], abs_max: float, n: int, what: str) -> Tuple[Dict[str, np.ndarray],
                                                                                Dict[str, int]]:
    """{column: values with invalid -> NaN}, counts per column."""
    if not isinstance(spi, pd.DataFrame):
        L._refuse("%s: spi must be a DataFrame with the columns %s" % (what, cols))
    miss = [c for c in cols if c not in spi.columns]
    if miss:
        L._refuse("%s: spi lacks the columns %s" % (what, miss))
    out, counts = {}, {}
    for c in cols:
        v, n_nan, n_oor = L.valid_predictor(spi[c].to_numpy(np.float64), abs_max)
        if v.shape != (n,):
            L._refuse("%s: spi column %s holds %d rows, the keys %d" % (what, c, v.size, n))
        out[c] = v
        counts["rows_missing__%s" % c] = n_nan
        counts["rows_out_of_range__%s" % c] = n_oor
    return out, counts


def fit_groups(groups: Any, months: Any, y: Any, N: Any, spi: pd.DataFrame, form: str,
               opt: Mapping[str, Any]) -> Dict[str, Any]:
    """{"form", "groups": {g: {scale | scales, b | b1 b2, n, sse_by_scale, season, fallback}}, "counts"} - the
    fitted part of the params (spec 4.3). months = the target calendar month of each row (1..12)."""
    form = _form(form, opt)
    cols = columns(form, opt)
    g = np.asarray(groups).astype(str)
    m = np.asarray(months, dtype=np.int64)
    y = np.asarray(y, dtype=np.float64)
    N = np.asarray(N, dtype=np.float64)
    if not (g.shape == m.shape == y.shape == N.shape):
        L._refuse("fit_groups: groups, months, y and N differ in length")
    S, counts = _spi(spi, cols, float(_opt(opt, "spi_abs_max")), g.size, "SPI-lag fit_groups")
    min_rows = int(_opt(opt, "min_fit_rows"))
    seasons = fire_season(g, m, N, int(_opt(opt, "fire_season_months"))) if form in ("T1", "T3") else {}
    out: Dict[str, Any] = {}
    for grp in sorted(set(g.tolist())):
        sel = g == grp
        season = seasons.get(grp)
        if season is not None:
            sel = sel & np.isin(m, season)
        if form == "T1":
            allv = sel & L.usable(N, y, *[S[c] for c in cols])
            n_sel = int(allv.sum())
            sse: Dict[str, float] = {}
            for c in cols:
                b_c, _, _ = fit_ratio(N[allv], S[c][allv], y[allv], min_rows)
                r = y[allv] - N[allv] * (1.0 + b_c * S[c][allv])
                sse[c] = float(np.dot(r, r))
            if n_sel < min_rows:
                rec = {"scale": None, "b": 0.0, "n": 0, "n_select": n_sel, "sse_by_scale": sse, "season": season,
                       "fallback": True}
            else:
                best = cols[0]
                for c in cols[1:]:
                    if sse[c] < sse[best]:            # strict: a tie keeps the earlier scale of options.scales
                        best = c
                b, n, fb = fit_ratio(N[sel], S[best][sel], y[sel], min_rows)
                rec = {"scale": best, "b": b, "n": n, "n_select": n_sel, "sse_by_scale": sse, "season": season,
                       "fallback": fb}
        elif form == "T2":
            c = cols[0]
            b, n, fb = fit_ratio(N[sel], S[c][sel], y[sel], min_rows)
            rec = {"scale": c, "b": b, "n": n, "sse_by_scale": None, "season": None, "fallback": fb}
        else:
            b1, b2, n, fb = fit_ratio2(N[sel], S[cols[0]][sel], S[cols[1]][sel], y[sel], min_rows)
            rec = {"scales": list(cols), "b1": b1, "b2": b2, "n": n, "sse_by_scale": None, "season": season,
                   "fallback": fb}
        out[grp] = rec
    counts.update({"rows": int(g.size), "rows_used": int(sum(r["n"] for r in out.values())),
                   "rows_normal_missing": int((~np.isfinite(N)).sum()),
                   "rows_nonpositive_normal": int((np.isfinite(N) & (N <= 0)).sum()),
                   "groups": len(out), "groups_fallback_normal": int(sum(1 for r in out.values() if r["fallback"]))})
    if form == "T1":
        chosen: Dict[str, int] = {}
        for r in out.values():
            k = str(r["scale"]) if r["scale"] is not None else "none"
            chosen[k] = chosen.get(k, 0) + 1
        counts["groups_by_scale"] = dict(sorted(chosen.items()))
    return {"form": form, "groups": out, "counts": counts}


def predict_values(groups: Any, months: Any, N: Any, spi: pd.DataFrame, params: Mapping[str, Any],
                   opt: Mapping[str, Any]) -> Tuple[np.ndarray, Dict[str, Any]]:
    """(pre, counts): pre = N (1 + slope terms) with the form's terms per row; a missing SPI -> 0 (its term drops);
    outside the season (T1, T3), a fallback group, an unseen group or N <= 0 -> N. params = the runner's params or
    fit_groups' result."""
    form = _form(params.get("form") if isinstance(params, Mapping) else None, opt)
    cols = columns(form, opt)
    P = L.group_params(params)
    g = np.asarray(groups).astype(str)
    m = np.asarray(months, dtype=np.int64)
    N = np.asarray(N, dtype=np.float64)
    if not (g.shape == m.shape == N.shape):
        L._refuse("predict_values: groups, months and N differ in length")
    S, counts = _spi(spi, cols, float(_opt(opt, "spi_abs_max")), g.size, "SPI-lag predict_values")
    term = np.zeros(g.size, dtype=np.float64)
    invalid_used = np.zeros(g.size, dtype=bool)       # rows whose model term needed a missing SPI
    unseen = outside = fallback_rows = 0
    for grp in sorted(set(g.tolist())):
        sel = g == grp
        rec = P.get(grp)
        if rec is None:
            unseen += int(sel.sum())
            continue
        if bool(rec.get("fallback")):
            fallback_rows += int(sel.sum())
        season = rec.get("season")
        if season is not None:
            ins = sel & np.isin(m, [int(v) for v in season])
            outside += int((sel & ~ins).sum())
        else:
            ins = sel
        if form in ("T1", "T2"):
            c = rec.get("scale")
            if c is None:                              # T1 group without a scale choice: the normal
                continue
            if c not in S:
                L._refuse("SPI-lag params name the scale %r, not one of the options' %s" % (c, cols))
            v = S[c]
            ok = np.isfinite(v)
            term[ins & ok] = float(rec["b"]) * v[ins & ok]
            invalid_used |= ins & ~ok
        else:
            names = list(rec["scales"])
            if names != cols:
                L._refuse("SPI-lag params name the scales %s, the options %s" % (names, cols))
            for c, b in ((names[0], float(rec["b1"])), (names[1], float(rec["b2"]))):
                v = S[c]
                ok = np.isfinite(v)
                term[ins & ok] += b * v[ins & ok]
                invalid_used |= ins & ~ok
    pre = L.anchored(N, term)
    counts.update({"rows": int(g.size), "rows_spi_invalid_predict_term_0": int((invalid_used & (N > 0)).sum()),
                   "rows_group_unseen_normal": unseen, "rows_outside_season_normal": outside,
                   "rows_of_fallback_groups": fallback_rows, "rows_nonpositive_normal": int((N <= 0).sum())})
    return pre, counts


# ---------------------------------------------------------------------------------------------------
# The M runner (methods.py): fit(ctx, rival, lead, fit_set) -> params; predict(...) -> DataFrame
def fit(ctx: Any, rival: Mapping[str, Any], lead: int, fit_set: str) -> Dict[str, Any]:
    if fit_set not in L.FIT_SETS:
        L._refuse("SPI-lag fits on %s, not %r (no lead-0 row; spec 4)" % ("/".join(L.FIT_SETS), fit_set))
    L.check_lead(lead)
    opt = _options(rival)
    cols = columns(opt["form"], opt)
    L.check_monthly(ctx.run)
    offset = L.run_offset(ctx.run)
    s_steps = L.t1_steps(ctx.run, rival)
    keys, N, X = L.inputs(ctx, lead, fit_set, cols)
    y = L.labels(ctx, fit_set, keys)
    groups = keys["group"].astype(str).to_numpy()
    months = L.target_months(keys["time"].to_numpy(np.int64))
    res = fit_groups(groups, months, y, N, X, opt["form"], opt)
    c = res["counts"]
    ctx.log("SPI-lag %s lead %d form %s fit on %s: %d rows, %d used, %d groups (%d on the normal), non-positive "
            "normal %d%s" % (rival.get("id"), int(lead), opt["form"], fit_set, c["rows"], c["rows_used"], c["groups"],
                             c["groups_fallback_normal"], c["rows_nonpositive_normal"],
                             (", scales chosen %s" % c["groups_by_scale"]) if "groups_by_scale" in c else ""))
    return {"format": PARAMS_FORMAT, "adapter": ADAPTER_FORMAT, "rival": rival.get("id"), "lead": int(lead),
            "fit_set": fit_set, "form": res["form"], "columns": cols, "options": opt, "t1_steps": int(s_steps),
            "start_offset_steps": int(offset), "groups": res["groups"], "counts": res["counts"]}


def predict(ctx: Any, rival: Mapping[str, Any], lead: int, params: Mapping[str, Any],
            score_set: str) -> pd.DataFrame:
    """DataFrame(keys, pre, info_end, target_obs_end): one row per key of the score set, every pre finite. No label
    is read here (fit_labels is never called)."""
    opt = _options(rival)
    cols = columns(opt["form"], opt)
    if params.get("format") != PARAMS_FORMAT or int(params.get("lead", -1)) != int(lead):
        L._refuse("SPI-lag params are not %s params of lead %d" % (PARAMS_FORMAT, int(lead)))
    L.score_set_of(params, score_set, "SPI-lag")
    if params.get("form") != opt["form"] or list(params.get("columns") or []) != cols:
        L._refuse("SPI-lag params were fitted with form %r on %s; the registry says %r on %s"
                  % (params.get("form"), params.get("columns"), opt["form"], cols))
    L.check_monthly(ctx.run)
    offset = L.run_offset(ctx.run)
    s_steps = L.fitted_t1_steps(ctx, rival, params, "SPI-lag")
    keys, N, X = L.inputs(ctx, lead, score_set, cols)
    months = L.target_months(keys["time"].to_numpy(np.int64))
    pre, counts = predict_values(keys["group"].astype(str).to_numpy(), months, N, X, params, opt)
    out = keys.copy()
    out["pre"] = pre
    out["info_end"] = L.info_end(keys, s_steps).astype(np.int64)
    out["target_obs_end"] = np.full(len(keys), float(L.target_obs_end(ctx.run, lead, score_set, offset)))
    text = ", ".join("%s %d" % kv for kv in sorted(counts.items()))
    ctx.log("SPI-lag %s lead %d form %s predict on %s: %s" % (rival.get("id"), int(lead), opt["form"], score_set, text))
    return out


__all__ = ["ADAPTER_FORMAT", "PARAMS_FORMAT", "FORMS", "DEFAULTS", "FireLagRefusal", "fire_season", "fit_ratio",
           "fit_ratio2", "columns", "fit_groups", "predict_values", "fit", "predict"]
