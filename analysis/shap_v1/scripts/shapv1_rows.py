"""Row-level SHAP output of one model at one problem-lead (PROTOCOL.md sections 5 and 9, v3), shared by every model.

rows.parquet columns: row (the sample's row index), unit, group, time, year, base, eta (the model's link-space value
by our evaluator, the value the attributions add up to), eta_model (the model's or engine's own link value), pre
(y units before the legal clip), resid (R: the unattributed float32 addition residual), gap (G: eta_model - eta, the
engine's float32 dot rounding of the region kind; 0 elsewhere), add_err (base + sum phi + R - eta, feature level),
resid_flag, then phi__<player> (feature level: one player per distinct column, exact duplicates merged) and
phiv__<variable> (variable level: the exact Shapley values of the grouped game, PROTOCOL.md 8). Link space only:
the y-unit view of v1/v2 was removed in v3 (its error measurement was never built).
background_keys.parquet: (row, unit, time) of every background row of every explained row (compare_shap.py refuses
models whose background keys differ). meta.json: players, variables, link, tolerances, maxima, checks.

Stop rules checked here (no file but FAILED.json is written when one fails, exit 3):
  S-ADD    additivity at both levels <= ADD_TOL on every explained row; no NaN in eta, eta_model, base or phi;
  S-EVAL   our evaluator against the model's own value <= the evaluator tolerance on every explained row and on
           every background row given (the region kind: |G| within the float32 summation bound instead);
  S-ZERO   a player whose columns equal the explained row's on every background row has phi exactly 0;
  S-RESID  rows whose unattributed part |R| + |G| exceeds 1% of |eta - base| (+1e-9) are flagged; the model stops
           when more than 1% of the rows are flagged.
"""
import os

import numpy as np
import pandas as pd

import shapv1_common as C

ADD_TOL = 1e-9          # link units (PROTOCOL.md 5, stop rule S-ADD)
EVAL_TOL = 1e-9         # our evaluator vs the model's own link value (S-EVAL)
RESID_SHARE = 0.01      # S-RESID: flag a row whose unattributed part exceeds this share of |eta - base|
RESID_ROWS = 0.01       # S-RESID: stop when more than this share of rows is flagged


def constant_mask(Xe, Xb, px, pb, poc, nplay):
    """(n_x, nplay) bool: True where every background row of explained row i equals row i on every column of the
    player (bitwise, NaN equal to NaN). Such a player is structurally zero for that row in an exact interventional
    game (S-ZERO)."""
    Xe = np.asarray(Xe)
    Xb = np.asarray(Xb)
    n = Xe.shape[0]
    poc = np.asarray(poc, np.int64)
    neq = np.zeros((n, nplay), bool)
    # per pair and column: differs?  (chunked over pairs to bound memory)
    step = max(1, int(5e6 // max(1, Xe.shape[1])))
    for a in range(0, px.size, step):
        xi = Xe[px[a:a + step]]
        xb = Xb[pb[a:a + step]]
        d = ~((xi == xb) | (np.isnan(xi) & np.isnan(xb)))
        if not d.any():
            continue
        r, c = np.nonzero(d)
        neq[px[a:a + step][r], poc[c]] = True
    return ~neq


def linear_constant(lin_e, lin_pairs, px, n):
    """(n, L) bool: True where the linear design value of every background pair equals the explained row's."""
    d = lin_pairs != lin_e[px]
    out = np.ones((n, lin_e.shape[1]), bool)
    r, c = np.nonzero(d)
    out[px[r], c] = False
    return out


def _check_zero(phi, const, names, what):
    if const is None:
        return 0, []
    bad = const & (phi != 0)
    cols = sorted(set(np.nonzero(bad)[1].tolist()))
    return int(bad.sum()), [names[j] for j in cols[:10]]


def write(out_dir, sample_rows, players, phi, variables, phiv, base, eta, eta_model, pre, resid, meta, log,
          bg_keys, const=None, constv=None, gap_bound=None, eta_bg=None, eta_bg_model=None, eta_bg_bound=None,
          eval_tol=None):
    """Checks S-ADD, S-EVAL, S-ZERO and S-RESID, then writes rows.parquet, background_keys.parquet and meta.json.
    gap_bound (region kind only): the per-row float32 summation bound of G = eta_model - eta; eta_bg_bound likewise
    for the background rows. Returns the meta record. Refuses (SystemExit 3) when a check fails: only FAILED.json
    is written then."""
    phi = np.asarray(phi, np.float64)
    phiv = np.asarray(phiv, np.float64)
    n = phi.shape[0]
    base = np.asarray(base, np.float64)
    eta = np.asarray(eta, np.float64)
    eta_model = np.asarray(eta_model, np.float64)
    resid = np.zeros(n) if resid is None else np.asarray(resid, np.float64)
    gap = (eta_model - eta) if gap_bound is not None else np.zeros(n)
    tol = EVAL_TOL if eval_tol is None else float(eval_tol)
    add = base + phi.sum(1) + resid - eta
    addv = base + phiv.sum(1) + resid - eta
    finite = bool(np.isfinite(eta).all() and np.isfinite(eta_model).all() and np.isfinite(base).all()
                  and np.isfinite(phi).all() and np.isfinite(phiv).all() and np.isfinite(resid).all())
    rec = dict(meta)
    if gap_bound is None:                                   # per-unit, neighbour kinds and rivals
        ev = np.abs(eta - eta_model)
        ev_ok = bool(np.all(ev <= tol))
        rec["max_abs_evaluator_minus_model"] = float(ev.max()) if n else 0.0
    else:                                                   # region kind: the engine's float32 dot (G)
        gb = np.asarray(gap_bound, np.float64)
        ev_ok = bool(np.isfinite(gap).all() and np.all(np.abs(gap) <= gb))
        rec["max_abs_gap_float32_dot"] = float(np.abs(gap).max()) if n else 0.0
        rec["max_gap_over_bound"] = float(np.max(np.abs(gap) / np.maximum(gb, 1e-300))) if n else 0.0
    bg_ok, bg_max = True, None
    if eta_bg is not None and eta_bg_model is not None:
        d = np.abs(np.asarray(eta_bg, np.float64) - np.asarray(eta_bg_model, np.float64))
        bg_tol = tol if eta_bg_bound is None else np.asarray(eta_bg_bound, np.float64)
        bg_ok = bool(np.isfinite(d).all() and np.all(d <= bg_tol))
        bg_max = float(d.max()) if d.size else 0.0
    elif eta_bg is not None or eta_bg_model is not None:
        bg_ok = False                                       # a background check was announced but not given
    nz, nz_names = _check_zero(phi, const, players, "feature")
    nzv, nzv_names = _check_zero(phiv, constv, variables, "variable")
    tot = np.abs(eta - base)
    unatt = np.abs(resid) + np.abs(gap)
    flag = unatt > RESID_SHARE * tot + 1e-9
    share = unatt / np.maximum(tot, 1e-300)
    rec.update({"rows": int(n), "players": list(players), "variables": list(variables),
                "max_abs_additivity_error": float(np.abs(add).max()) if n else 0.0,
                "max_abs_additivity_error_variable": float(np.abs(addv).max()) if n else 0.0,
                "max_abs_resid": float(np.abs(resid).max()) if n else 0.0,
                "max_abs_eta_minus_base": float(tot.max()) if n else 0.0,
                "max_unattributed_share": float(share.max()) if n else 0.0,
                "rows_flagged_resid": int(flag.sum()),
                "max_abs_background_evaluator_minus_model": bg_max,
                "all_finite": finite, "structural_zero_violations": nz + nzv,
                "structural_zero_violation_players": nz_names + nzv_names,
                "tolerances": {"additivity": ADD_TOL, "evaluator": tol, "resid_share": RESID_SHARE,
                               "resid_rows": RESID_ROWS},
                "players_nonzero": int((np.abs(phi).max(0) > 0).sum()) if phi.size else 0,
                "variables_nonzero": int((np.abs(phiv).max(0) > 0).sum()) if phiv.size else 0})
    checks = {"S-ADD": finite and rec["max_abs_additivity_error"] <= ADD_TOL
              and rec["max_abs_additivity_error_variable"] <= ADD_TOL,
              "S-EVAL": ev_ok and bg_ok, "S-ZERO": nz + nzv == 0,
              "S-RESID": flag.sum() <= RESID_ROWS * max(n, 1)}
    rec["checks_passed"] = checks
    rec["pass"] = bool(all(checks.values()))
    C.makedirs(out_dir)
    if not rec["pass"]:
        C.write_json(os.path.join(out_dir, "FAILED.json"), rec)
        log("STOP %s: %s %s: no SHAP value is written" % ([k for k, v in checks.items() if not v], meta.get("model"),
                                                         {k: rec.get(k) for k in (
                                                             "max_abs_additivity_error", "max_abs_evaluator_minus_model",
                                                             "max_abs_gap_float32_dot", "structural_zero_violations",
                                                             "rows_flagged_resid", "all_finite")}))
        raise SystemExit(3)
    if os.path.isfile(os.path.join(out_dir, "FAILED.json")):
        os.remove(C.assert_writable(os.path.join(out_dir, "FAILED.json")))
    df = sample_rows[["row", "unit", "group", "time", "year"]].reset_index(drop=True).copy()
    df["base"], df["eta"], df["eta_model"], df["pre"] = base, eta, eta_model, pre
    df["resid"], df["gap"], df["add_err"], df["resid_flag"] = resid, gap, add, flag
    cols = {"phi__" + p: phi[:, j] for j, p in enumerate(players)}
    cols.update({"phiv__" + v: phiv[:, j] for j, v in enumerate(variables)})
    df = pd.concat([df, pd.DataFrame(cols)], axis=1)
    path = C.write_parquet(os.path.join(out_dir, "rows.parquet"), df)
    bk = pd.DataFrame(bg_keys).reset_index(drop=True)[["row", "unit", "time"]]
    bk["unit"] = bk["unit"].astype(str)
    bk["time"] = bk["time"].astype(np.int64)
    bpath = C.write_parquet(os.path.join(out_dir, "background_keys.parquet"),
                            bk.sort_values(["row", "unit", "time"]).reset_index(drop=True))
    rec["rows_sha256"] = C.sha256_file(path)
    rec["background_keys_sha256"] = C.sha256_file(bpath)
    C.write_json(os.path.join(out_dir, "meta.json"), rec)
    log("%s: %d rows, %d players (%d nonzero), %d variables (%d nonzero); additivity max %.2e / %.2e; evaluator "
        "%s; resid max %.2e; flagged %d; structural-zero violations 0"
        % (meta.get("model"), n, len(players), rec["players_nonzero"], len(variables), rec["variables_nonzero"],
           rec["max_abs_additivity_error"], rec["max_abs_additivity_error_variable"],
           ("max %.2e" % rec["max_abs_evaluator_minus_model"]) if "max_abs_evaluator_minus_model" in rec else
           ("gap max %.2e (%.2f of the float32 bound)" % (rec["max_abs_gap_float32_dot"], rec["max_gap_over_bound"])),
           rec["max_abs_resid"], rec["rows_flagged_resid"]))
    return rec
