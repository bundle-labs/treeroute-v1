"""Fire human rival enso_lag: ENSO-lag regression (Chen et al. 2011, Science 334:787; 2016, Nat. Clim. Change 6:906;
our implementation, not an operational product).

SPEC_HUMAN_PARTB.txt section 4 (common rules), 4.1 (forms; OWNER DECISION OD-2), 4.3 (params); PLAN :71; Q17 (an
optional rival); research_fire.md :49 (the E1 form, written before any score of it).

Kind M (a published method, F0: no extra map). Per group (region) g, fitted on the fit set's rows:
    E1 (recommended)  y_hat = N (1 + b_g ONI)               all months
    E2                E1 inside the group's fire season F_g (fire_season_months consecutive months of largest summed
                      normal), y_hat = N outside
    E3                y_hat = N (1 + b_{g,m} ONI)           one slope per group x target calendar month m; a month
                      with < min_month_rows usable rows (or no spread) takes the group's E1 slope b_g
    N    the row's identity normal as the slim gives the set (ngd__ on guardfit / guard, nfit__ on refit / test; in
         sample on the fit rows, as the published regressions use an in-sample climatology; spec 4)
    ONI  options.index_column = x__oni, the engine's own lagged column (ONI of issue - 3; catalogue rule, owner
         2026-09-27 "lagged, not dropped"); |ONI| > index_abs_max or NaN = missing
    b    least squares through the origin of y - N on N ONI (fire_lag_common.fit_ratio); < min_fit_rows usable rows
         or sum((N ONI)^2) == 0 -> b = 0 (the normal), flagged
Prediction: pre = N (1 + b ONI) (pre-clip; the tool clips to the legal range and keeps pre). A missing ONI -> 0 (pre
= N), a group unseen in the params -> N, N <= 0 -> N (= 0 on the zero-normal rows), all counted; a NaN normal refuses.
Every score row gets a finite pre (coverage all_rows).

Timing: info_end = issue - S, S = max R8 steps of t1_kind_columns at fit ([oni] -> 3); target_obs_end = run.cuts[L]
["guard_cut"] - R17 offset on guard rows, ["fit_cut"] - offset on test rows (the newest label behind N and b).
reads_target_in_test_window = false: no label is read at prediction (fit_labels only inside fit).

The ctx calls used here (SPEC_HUMAN section 6; rivals_human/index.py AdapterCtx):
  ctx.run                  .derived (R2, R8, R17), .cuts[L]["guard_cut" | "fit_cut"]
  ctx.features(set_name)   keys, normal {link: array}, extras (the registry slim_extra_columns); never y
  ctx.fit_labels(fit_set)  (keys, y, normal) of the fit set being fitted, inside fit only (fire_lag_common.labels)
  ctx.log(message)
"""
from typing import Any, Dict, Mapping, Tuple

import numpy as np
import pandas as pd

from adapters import fire_lag_common as L
from adapters.fire_lag_common import fire_season, fit_ratio, FireLagRefusal

ADAPTER_FORMAT = "human-adapter-fire-enso/1"
PARAMS_FORMAT = "human-fire-enso-params/1"
FORMS = ("E1", "E2", "E3")
DEFAULTS = {"index_abs_max": 5.0,       # spec 2.4: |ONI| > 5 -> missing (counted)
            "min_fit_rows": 100,        # spec 2.4: per group (Q2.HQ9 row floor)
            "fire_season_months": 3,    # spec 2.4: E2 only
            "min_month_rows": 100}      # spec 2.4: E3 only
REQUIRED = ("form", "index_column")


def _options(rival: Mapping[str, Any]) -> Dict[str, Any]:
    opt = dict(rival.get("options") or {})
    miss = [k for k in REQUIRED if k not in opt]
    if miss:
        L._refuse("rival %s: registry options lack %s" % (rival.get("id"), miss))
    unknown = sorted(k for k in opt if k not in REQUIRED and k not in DEFAULTS)
    if unknown:
        L._refuse("rival %s: unknown registry options %s (allowed %s)" % (rival.get("id"), unknown,
                                                                          list(REQUIRED) + sorted(DEFAULTS)))
    out = dict(DEFAULTS)
    out.update(opt)
    out["form"] = str(out["form"])
    if out["form"] not in FORMS:
        L._refuse("rival %s: options.form %r is not one of %s (OWNER DECISION OD-2)" % (rival.get("id"), out["form"],
                                                                                        FORMS))
    out["index_column"] = str(out["index_column"])
    out["index_abs_max"] = float(out["index_abs_max"])
    for k in ("min_fit_rows", "fire_season_months", "min_month_rows"):
        out[k] = int(out[k])
    if not out["index_abs_max"] > 0 or out["min_fit_rows"] < 1 or out["min_month_rows"] < 1:
        L._refuse("rival %s: options index_abs_max / min_fit_rows / min_month_rows must be positive" % rival.get("id"))
    return out


def _form(form: Any, opt: Mapping[str, Any]) -> str:
    """The form of a pure-function call: the explicit one (fit_groups' argument, the params' form), else opt's."""
    f = str(form if form is not None else opt.get("form"))
    if f not in FORMS:
        L._refuse("ENSO-lag form %r is not one of %s" % (f, FORMS))
    return f


def _opt(opt: Mapping[str, Any], key: str) -> Any:
    """An option of a pure-function call (the runner passes _options(rival); a direct call may leave defaults out)."""
    return opt[key] if key in opt else DEFAULTS[key]


# ---------------------------------------------------------------------------------------------------
# The fit and the prediction (pure functions; toy-tested)
def fit_groups(groups: Any, months: Any, y: Any, N: Any, oni: Any, form: str,
               opt: Mapping[str, Any]) -> Dict[str, Any]:
    """{"form", "groups": {g: {b, n, fallback, season[, b_m, n_m, months_on_group_slope]}}, "counts"} - the fitted
    part of the params (spec 4.3). months = the target calendar month of each row (1..12)."""
    form = _form(form, opt)
    g = np.asarray(groups).astype(str)
    m = np.asarray(months, dtype=np.int64)
    y = np.asarray(y, dtype=np.float64)
    N = np.asarray(N, dtype=np.float64)
    s, n_nan, n_oor = L.valid_predictor(oni, float(_opt(opt, "index_abs_max")))
    if not (g.shape == m.shape == y.shape == N.shape == s.shape):
        L._refuse("fit_groups: groups, months, y, N and the index differ in length")
    seasons = fire_season(g, m, N, int(_opt(opt, "fire_season_months"))) if form == "E2" else {}
    out: Dict[str, Any] = {}
    for grp in sorted(set(g.tolist())):
        sel = g == grp
        if form == "E2":
            sel = sel & np.isin(m, seasons[grp])
        b, n, fb = fit_ratio(N[sel], s[sel], y[sel], int(_opt(opt, "min_fit_rows")))
        rec: Dict[str, Any] = {"b": b, "n": n, "fallback": fb, "season": seasons.get(grp)}
        if form == "E3":
            b_m, n_m, on_group = {}, {}, []
            for mm in range(1, L.MONTHS_PER_YEAR + 1):
                sm = sel & (m == mm)
                bm, nm, fbm = fit_ratio(N[sm], s[sm], y[sm], int(_opt(opt, "min_month_rows")))
                n_m[str(mm)] = nm
                if fbm:
                    b_m[str(mm)] = b
                    on_group.append(mm)
                else:
                    b_m[str(mm)] = bm
            rec.update(b_m=b_m, n_m=n_m, months_on_group_slope=on_group)
        out[grp] = rec
    use = L.usable(N, y, s)
    counts = {"rows": int(g.size), "rows_usable": int(use.sum()),
              "rows_used": int(sum(r["n"] for r in out.values())),
              "rows_index_missing": n_nan, "rows_index_out_of_range": n_oor,
              "rows_normal_missing": int((~np.isfinite(N)).sum()),
              "rows_nonpositive_normal": int((np.isfinite(N) & (N <= 0)).sum()),
              "groups": len(out), "groups_fallback_normal": int(sum(1 for r in out.values() if r["fallback"]))}
    if form == "E3":
        counts["group_months_on_group_slope"] = int(sum(len(r["months_on_group_slope"]) for r in out.values()))
    return {"form": form, "groups": out, "counts": counts}


def predict_values(groups: Any, months: Any, N: Any, oni: Any, params: Mapping[str, Any],
                   opt: Mapping[str, Any]) -> Tuple[np.ndarray, Dict[str, int]]:
    """(pre, counts): pre = N (1 + b ONI) with the form's slope per row; a missing ONI -> 0 (pre = N); outside the
    E2 season, an unseen group or N <= 0 -> N. params = the runner's params or fit_groups' result."""
    form = _form(params.get("form") if isinstance(params, Mapping) else None, opt)
    P = L.group_params(params)
    g = np.asarray(groups).astype(str)
    m = np.asarray(months, dtype=np.int64)
    N = np.asarray(N, dtype=np.float64)
    s, n_nan, n_oor = L.valid_predictor(oni, float(_opt(opt, "index_abs_max")))
    if not (g.shape == m.shape == N.shape == s.shape):
        L._refuse("predict_values: groups, months, N and the index differ in length")
    slope = np.zeros(g.size, dtype=np.float64)
    applies = np.zeros(g.size, dtype=bool)          # rows on which the form applies a slope
    unseen = outside = fallback_rows = 0
    for grp in sorted(set(g.tolist())):
        sel = g == grp
        rec = P.get(grp)
        if rec is None:
            unseen += int(sel.sum())
            continue
        if bool(rec.get("fallback")):
            fallback_rows += int(sel.sum())
        if form == "E1":
            slope[sel] = float(rec["b"])
            applies |= sel
        elif form == "E2":
            ins = sel & np.isin(m, [int(v) for v in rec["season"]])
            slope[ins] = float(rec["b"])
            applies |= ins
            outside += int((sel & ~ins).sum())
        else:
            bm = rec["b_m"]
            for mm in range(1, L.MONTHS_PER_YEAR + 1):
                sm = sel & (m == mm)
                slope[sm] = float(bm[str(mm)])
            applies |= sel
    bad = ~np.isfinite(s)
    term = slope * np.where(bad, 0.0, s)
    pre = L.anchored(N, term)
    counts = {"rows": int(g.size), "rows_index_missing": n_nan, "rows_index_out_of_range": n_oor,
              "rows_index_invalid_predict_normal": int((bad & applies & (N > 0)).sum()),
              "rows_group_unseen_normal": unseen, "rows_outside_season_normal": outside,
              "rows_of_fallback_groups": fallback_rows, "rows_nonpositive_normal": int((N <= 0).sum())}
    return pre, counts


# ---------------------------------------------------------------------------------------------------
# The M runner (methods.py): fit(ctx, rival, lead, fit_set) -> params; predict(...) -> DataFrame
def fit(ctx: Any, rival: Mapping[str, Any], lead: int, fit_set: str) -> Dict[str, Any]:
    if fit_set not in L.FIT_SETS:
        L._refuse("ENSO-lag fits on %s, not %r (no lead-0 row; spec 4)" % ("/".join(L.FIT_SETS), fit_set))
    L.check_lead(lead)
    opt = _options(rival)
    L.check_monthly(ctx.run)
    offset = L.run_offset(ctx.run)
    s_steps = L.t1_steps(ctx.run, rival)
    keys, N, X = L.inputs(ctx, lead, fit_set, [opt["index_column"]])
    y = L.labels(ctx, fit_set, keys)
    groups = keys["group"].astype(str).to_numpy()
    months = L.target_months(keys["time"].to_numpy(np.int64))
    res = fit_groups(groups, months, y, N, X[opt["index_column"]].to_numpy(np.float64), opt["form"], opt)
    c = res["counts"]
    ctx.log("ENSO-lag %s lead %d form %s fit on %s: %d rows, %d usable, %d groups (%d on the normal: < %d rows), "
            "index missing %d, out of range %d, non-positive normal %d"
            % (rival.get("id"), int(lead), opt["form"], fit_set, c["rows"], c["rows_usable"], c["groups"],
               c["groups_fallback_normal"], opt["min_fit_rows"], c["rows_index_missing"], c["rows_index_out_of_range"],
               c["rows_nonpositive_normal"]))
    return {"format": PARAMS_FORMAT, "adapter": ADAPTER_FORMAT, "rival": rival.get("id"), "lead": int(lead),
            "fit_set": fit_set, "form": res["form"], "index_column": opt["index_column"], "options": opt,
            "t1_steps": int(s_steps), "start_offset_steps": int(offset), "groups": res["groups"],
            "counts": res["counts"]}


def predict(ctx: Any, rival: Mapping[str, Any], lead: int, params: Mapping[str, Any],
            score_set: str) -> pd.DataFrame:
    """DataFrame(keys, pre, info_end, target_obs_end): one row per key of the score set, every pre finite. No label
    is read here (fit_labels is never called)."""
    opt = _options(rival)
    if params.get("format") != PARAMS_FORMAT or int(params.get("lead", -1)) != int(lead):
        L._refuse("ENSO-lag params are not %s params of lead %d" % (PARAMS_FORMAT, int(lead)))
    L.score_set_of(params, score_set, "ENSO-lag")
    if params.get("form") != opt["form"] or params.get("index_column") != opt["index_column"]:
        L._refuse("ENSO-lag params were fitted with form %r on %r; the registry says %r on %r"
                  % (params.get("form"), params.get("index_column"), opt["form"], opt["index_column"]))
    L.check_monthly(ctx.run)
    offset = L.run_offset(ctx.run)
    s_steps = L.fitted_t1_steps(ctx, rival, params, "ENSO-lag")
    keys, N, X = L.inputs(ctx, lead, score_set, [opt["index_column"]])
    months = L.target_months(keys["time"].to_numpy(np.int64))
    pre, counts = predict_values(keys["group"].astype(str).to_numpy(), months, N,
                                 X[opt["index_column"]].to_numpy(np.float64), params, opt)
    out = keys.copy()
    out["pre"] = pre
    out["info_end"] = L.info_end(keys, s_steps).astype(np.int64)
    out["target_obs_end"] = np.full(len(keys), float(L.target_obs_end(ctx.run, lead, score_set, offset)))
    text = ", ".join("%s %d" % kv for kv in sorted(counts.items()))
    ctx.log("ENSO-lag %s lead %d form %s predict on %s: %s" % (rival.get("id"), int(lead), opt["form"], score_set,
                                                                text))
    return out


__all__ = ["ADAPTER_FORMAT", "PARAMS_FORMAT", "FORMS", "DEFAULTS", "FireLagRefusal", "fire_season", "fit_ratio",
           "fit_groups", "predict_values", "fit", "predict"]
