"""treeroute v1: exact link-space SHAP of the rebuilt kept arm on the registered sample (PROTOCOL.md section 5, v3).
Reads rebuild/<problem>/lead_<L>/ (written by tr_rebuild.py; its DONE.json must hold and name the same registered
sample) and the sample; no engine import.

  py -3.9 -I -B tr_shap.py --problem coral --lead 0 [--rebuild DIR] [--sample-root DIR] [--register FILE]
        [--rows K] [--out-root DIR] [--background B2|B1]

For row i with router coefficients b (per unit, per visit, or per region):
  eta_i = b_lin . lin_i + sum_k b_k A_k(x_i),  A_k = fl32(T_k) (+ fl32(C_k), added in float32, on corrector arms)
  phi_ij = sum_k b_k [phi_j(T_k) + phi_j(C_k)] (interventional TreeSHAP, background B(x_i)) + linear terms
  linear terms: b_l * mean_b (lin_il - lin_bl), per-pair differences first (a player equal on every background row
  gets exactly 0)
  R_i = sum_k b_k (eps_k(x_i) - mean_B eps_k), eps = A - (fl32 T + fl32 C): the float32 addition residual
  region kind: the engine evaluates the tree block as a float32 dot product; G_i = eta_engine - eta_ours is checked
  against the float32 summation bound per row (explained and background rows) and reported apart from R
Two levels (PROTOCOL.md 8): feature (one player per distinct column; an exact duplicate context column, proven on the
data, is merged into its tree column) and variable (the exact Shapley values of the grouped game: the same walk with
the variable map, plus the linear terms per variable).
Outputs out/<problem>/lead_<L>/treeroute/: rows.parquet, background_keys.parquet, meta.json, rows.parquet.done.json.
"""
import argparse
import os
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shapv1_common as C  # noqa: E402

C.pin_threads(1)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

import shapv1_rows as RW  # noqa: E402
import shapv1_treeshap as TS  # noqa: E402

U32 = 2.0 ** -24


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", required=True, choices=sorted(C.PROBLEMS))
    ap.add_argument("--lead", type=int, required=True)
    ap.add_argument("--rebuild", default=None)
    ap.add_argument("--sample-root", default=None)
    ap.add_argument("--register", default=None)
    ap.add_argument("--rows", type=int, default=0)
    ap.add_argument("--out-root", default=None)
    ap.add_argument("--background", default="B2", choices=("B2", "B1"))
    return ap.parse_args()


def load_npz(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def tree(Z, k, corr=False):
    p = "c_" if corr else ""
    o = Z[p + "off"]
    s, e = int(o[k]), int(o[k + 1])
    return TS.from_arrays(Z[p + "left"][s:e], Z[p + "right"][s:e], Z[p + "feat"][s:e], Z[p + "thr"][s:e],
                          Z[p + "val"][s:e], leaf_float32=True)


def export_columns(problem, lead):
    man = C.read_json(os.path.join(C.PROBLEMS[problem]["export"], "lead_%d" % lead, "export_manifest.json"))
    return list(man["columns"]["x"]), list(man["columns"]["c"])


def setup(a, log):
    """Per kind: the explained rows' coefficient rows, features, linear parts, and their background rows."""
    rb = a.rebuild or C.rebuild_dir(a.problem, a.lead)
    done = C.read_json(os.path.join(rb, "DONE.json"))
    for f, h in done["files"].items():
        if C.sha256_file(os.path.join(rb, f)) != h:
            raise SystemExit("REFUSED: %s changed since the rebuild finished" % f)
    sroot = a.sample_root or C.sample_dir(a.problem)
    ident = C.sample_identity(a.problem, sroot, a.register, lead=a.lead)
    if done.get("sample_sha256") != ident["sample_sha256"]:
        raise SystemExit("STOP S-SAMPLE: the rebuild was made for sample %s, the registered sample is %s"
                         % (str(done.get("sample_sha256"))[:16], ident["sample_sha256"][:16]))
    S = pq.read_table(os.path.join(sroot, "sample.parquet")).to_pandas()
    Bk = pq.read_table(os.path.join(sroot, "background_lead_%d.parquet" % a.lead)).to_pandas()
    if a.rows:
        S = S.iloc[:a.rows].copy()
    S = S.reset_index(drop=True)
    Bk = Bk[Bk["row"].isin(S["row"])].reset_index(drop=True)
    Z = load_npz(os.path.join(rb, "routers.npz"))
    xcols, ccols = export_columns(a.problem, a.lead)
    kind = done["kind"]
    tf = [str(t) for t in Z["tree_features"]] if "tree_features" in Z else None
    d = {"kind": kind, "done": done, "S": S, "rb": rb, "ident": ident, "Bk": Bk}
    if tf is not None and ["x__" + t for t in tf] != xcols:
        raise SystemExit("REFUSED: the engine's tree columns are not the export's x__ columns, in order")
    d["tree_players"] = xcols
    if kind == "neighbour":
        if a.background == "B1":
            raise SystemExit("REFUSED: B1 is not defined for the neighbour kind (its background is the visit's pool)")
        rows = [str(u) for u in Z["rows"]]
        pos = {u: i for i, u in enumerate(rows)}
        sel = np.asarray([pos[str(u)] for u in S["unit"]], np.int64)
        ctxn = ["c__" + str(c) for c in Z["context_columns"]]
        if ctxn != ccols:
            raise SystemExit("REFUSED: context columns %s are not the export's %s" % (ctxn, ccols))
        d.update(Bt=Z["b_tree"][sel], Bm=Z["b_mask"][sel], b_lin=Z["b_lin"][sel], lin_e=Z["lin_e"][sel],
                 eta_e=Z["eta_e"][sel], Xe=Z["x_e"][sel].astype(np.float64), Xb=Z["x_bg"].astype(np.float64),
                 lin_players=[None] + ccols)
        ptr, idx = Z["bg_ptr"], Z["bg_idx"]
        ids = [str(u) for u in Z["bg_ids"]]
        bg_lists, bg_lin, bg_eta = [], [], []
        want = Bk.groupby("row")["unit"].apply(lambda s: set(map(str, s))).to_dict()
        for r_local, r in enumerate(sel):
            lst = idx[ptr[r]:ptr[r + 1]]
            got = set(ids[j] for j in lst)
            if got != want[int(S["row"].iloc[r_local])]:
                raise SystemExit("STOP S-BG: row %d: the router's pool is not the registered background" % r_local)
            bg_lists.append(lst)
            bg_lin.append(Z["bg_lin"][ptr[r]:ptr[r + 1]])
            bg_eta.append(Z["bg_eta"][ptr[r]:ptr[r + 1]])
        d.update(bg_lists=bg_lists, bg_lin_pairs=np.concatenate(bg_lin), bg_eta_pairs=np.concatenate(bg_eta),
                 ctx_dup={})
        return d
    R = pq.read_table(os.path.join(rb, "rows.parquet")).to_pandas()
    key_fit = {(str(u), int(t)): i for i, (u, t, role) in enumerate(zip(R["unit"], R["time"], R["role"]))
               if role == "fit"}
    bgrows = Bk.groupby("row")
    bg_lists, missing = [], []
    for r_local, (u, t) in enumerate(zip(S["unit"].astype(str), S["time"].astype(int))):
        keys = bgrows.get_group(int(S["row"].iloc[r_local]))
        if a.background == "B1":
            lst = [i for (uu, tt), i in key_fit.items() if uu == u]
        else:
            lst = []
            for tt in keys["time"].astype(int):
                if (u, int(tt)) in key_fit:
                    lst.append(key_fit[(u, int(tt))])
                else:
                    missing.append((u, int(tt)))
        bg_lists.append(np.asarray(sorted(lst), np.int64))
    if missing:                                     # PROTOCOL 5: the registered B2 must be router fit rows
        raise SystemExit("STOP S-BG: %d registered background keys are not treeroute router fit rows (first %s); "
                         "make_sample.py removes the rows the run left out for missing context, so this one is "
                         "another rule: the background would differ between models" % (len(missing), missing[:3]))
    if a.background == "B1":                        # the keys actually used (a treeroute-only sensitivity)
        ru_, rt_ = R["unit"].astype(str).to_numpy(), R["time"].to_numpy(np.int64)
        d["Bk"] = pd.DataFrame([(int(S["row"].iloc[r]), ru_[i], int(rt_[i])) for r, lst in enumerate(bg_lists)
                                for i in lst], columns=["row", "unit", "time"])
    if kind == "per_unit":
        units = [str(u) for u in Z["units"]]
        upos = {u: i for i, u in enumerate(units)}
        lin_cols = sorted([c for c in R.columns if c.startswith("lin_")], key=lambda s: int(s[4:]))
        ctxn = ["c__" + str(c) for c in Z["context_columns"]]
        if ctxn != ccols:
            raise SystemExit("REFUSED: context columns %s are not the export's %s" % (ctxn, ccols))
        key_te = {(u, int(t)): i for i, (u, t, role) in enumerate(zip(R["unit"], R["time"], R["role"]))
                  if role == "test"}
        ei = np.asarray([key_te[(str(u), int(t))] for u, t in zip(S["unit"], S["time"])], np.int64)
        ui = np.asarray([upos[str(u)] for u in S["unit"]], np.int64)
        lin = R[lin_cols].to_numpy(np.float64)
        X = Z["x"].astype(np.float64)
        # exact duplicate context columns (NDVI c__ctx:top5:<v> = x__<v>), proven on every row read here
        ctx_dup = {}
        craw = Z.get("ctx_raw")
        rows_used = np.unique(np.concatenate([ei] + bg_lists))
        for ci, cname in enumerate(ccols):
            tgt = C.duplicate_target(cname, xcols)
            if tgt is None or craw is None or craw.shape[1] != len(ccols):
                continue
            xa = Z["x"][rows_used, xcols.index(tgt)]
            ca = craw[rows_used, ci]
            if np.array_equal(xa.view(np.uint32), ca.astype(np.float32).view(np.uint32)):
                ctx_dup[cname] = tgt
            else:
                log("context column %s is not an exact copy of %s on these rows: kept as its own player"
                    % (cname, tgt))
        d.update(Bt=Z["b_tree"][ui], Bm=Z["b_mask"][ui], b_lin=Z["b_lin"][ui], lin_e=lin[ei],
                 eta_e=R["eta"].to_numpy(np.float64)[ei], Xe=X[ei], Xb=X, lin_bg_all=lin,
                 eta_bg_all=R["eta"].to_numpy(np.float64), lin_players=[None, "normal"] + ccols,
                 bg_lists=bg_lists, ctx_dup=ctx_dup)
        return d
    # region kind
    regs = [str(g) for g in Z["regions"]]
    gpos = {g: i for i, g in enumerate(regs)}
    allpos = {(str(u), int(t)): i for i, (u, t) in enumerate(zip(Z["all_units"], Z["all_time"]))}
    Rt = R.set_index(["unit", "time"])
    Rte = R[R["role"] == "test"].set_index(["unit", "time"])
    ei = np.asarray([allpos[(str(u), int(t))] for u, t in zip(S["unit"], S["time"])], np.int64)
    gi = np.asarray([gpos[str(g)] for g in S["group"]], np.int64)
    n_e = np.asarray([float(Rte.loc[(str(u), int(t)), "normal"]) for u, t in zip(S["unit"], S["time"])])
    eta_e = np.asarray([float(Rte.loc[(str(u), int(t)), "eta"]) for u, t in zip(S["unit"], S["time"])])
    X = Z["x"].astype(np.float64)
    lin = Z["lin"]                                           # intercept, g, normal centre per region
    ru, rt = R["unit"].astype(str).to_numpy(), R["time"].to_numpy(np.int64)
    bg_all = [np.asarray([allpos[(ru[i], int(rt[i]))] for i in lst], np.int64) for lst in bg_lists]
    # background rows (indices into R): their engine eta (region_predict, float32 dot) and their own normal
    bg_eta_eng = [R["eta"].to_numpy(np.float64)[lst] for lst in bg_lists]
    bg_norm = [R["normal"].to_numpy(np.float64)[lst] for lst in bg_lists]
    lin_e = np.column_stack([np.ones(len(S)), n_e - lin[gi, 2]])
    d.update(Bt=Z["w"][gi], Bm=Z["w_mask"][gi], b_lin=np.column_stack([lin[gi, 0], lin[gi, 1]]), lin_e=lin_e,
             eta_e=eta_e, Xe=X[ei], Xb=X, lin_players=[None, "normal"], bg_lists=bg_all,
             region_lin_pairs=np.column_stack([np.ones(sum(map(len, bg_lists))),
                                               np.concatenate(bg_norm) - np.repeat(lin[gi, 2], [len(x) for x in
                                                                                                 bg_lists])]),
             region_bg_eta_engine=np.concatenate(bg_eta_eng), ctx_dup={})
    return d


def main():
    a = parse()
    log = C.Log("tr_shap_%s_lead%d" % (a.problem, a.lead))
    t0 = time.time()
    d = setup(a, log)
    done, S, kind = d["done"], d["S"], d["kind"]
    out = C.makedirs(os.path.join(a.out_root or C.out_dir(a.problem, a.lead),
                                  "treeroute" if a.background == "B2" else "treeroute_B1"))
    inputs = {"problem": a.problem, "lead": a.lead, "rows": a.rows, "background": a.background,
              "rebuild": done["files"], "sample": d["ident"]["sample_sha256"],
              "background_file": d["ident"]["background_sha256"],
              "scripts": {f: C.sha256_file(os.path.join(HERE, f)) for f in
                          ("tr_shap.py", "shapv1_treeshap.py", "shapv1_rows.py", "shapv1_common.py")}}
    if C.piece_done(os.path.join(out, "rows.parquet"), inputs):
        log("treeroute %s lead %d: finished piece found with matching hashes: skipped" % (a.problem, a.lead))
        return
    Zb = load_npz(os.path.join(d["rb"], "bank.npz"))
    n_bank = int(Zb["off"].size - 1)
    corrector = done["table_kind"] == "corrector"
    tree_players = d["tree_players"]
    lin_players = d["lin_players"]
    dup = d["ctx_dup"]
    players = list(tree_players) + [p for p in lin_players if p is not None and p not in tree_players
                                    and p not in dup]
    pidx = {p: j for j, p in enumerate(players)}
    lin_target = {p: dup.get(p, p) for p in lin_players if p is not None}
    vmap, variables = C.variable_map(players)
    vidx = {v: j for j, v in enumerate(variables)}
    nplay, nvar = len(players), len(variables)
    ntf = len(tree_players)
    poc = np.arange(ntf)
    pocv = np.asarray([vidx[vmap[p]] for p in tree_players], np.int64)
    Xe, Xb, Bt, Bm = d["Xe"], d["Xb"], d["Bt"], d["Bm"]
    n = Xe.shape[0]
    px, pb, pw = TS.pairs_for(d["bg_lists"])
    phi = np.zeros((n, nplay))
    phiv = np.zeros((n, nvar))
    A_e = np.zeros(n)
    eps_e = np.zeros(n)
    A_pair = np.zeros(px.size)
    eps_pair = np.zeros(px.size)
    absA_e = np.zeros(n)                                      # region kind: sum_k |w_k A_k| for the float32 bound
    absA_pair = np.zeros(px.size)
    used = np.flatnonzero(Bm.any(0))
    log("%s lead %d: %d rows, %d background pairs, %d of %d bank trees used, corrector arm %s; %d players, %d "
        "variables; duplicates merged %s" % (a.problem, a.lead, n, px.size, used.size, n_bank, corrector, nplay,
                                             nvar, dup))
    t1 = time.time()
    for c, k in enumerate(used):
        rows_k = np.flatnonzero(Bm[:, k])
        T = tree(Zb, int(k))
        te = TS.predict(T, Xe).astype(np.float32)
        tb = TS.predict(T, Xb).astype(np.float32)
        Ce = Cb = None
        if corrector and bool(Zb["has_corr"][int(k)]):
            Ct = tree(Zb, int(k), True)
            Ce, Cb = TS.predict(Ct, Xe).astype(np.float32), TS.predict(Ct, Xb).astype(np.float32)
            ae, ab = te + Ce, tb + Cb                                         # float32 addition, as the engine
            ee = ae.astype(np.float64) - (te.astype(np.float64) + Ce.astype(np.float64))
            eb = ab.astype(np.float64) - (tb.astype(np.float64) + Cb.astype(np.float64))
        else:
            ae, ab, ee, eb = te, tb, np.zeros(n), np.zeros(Xb.shape[0])
        bk = Bt[:, k]
        A_e += bk * ae.astype(np.float64)
        eps_e += bk * ee
        A_pair += bk[px] * ab.astype(np.float64)[pb]
        eps_pair += bk[px] * eb[pb]
        if kind == "region":
            absA_e += np.abs(bk * ae.astype(np.float64))
            absA_pair += np.abs(bk[px] * ab.astype(np.float64)[pb])
        sel = np.isin(px, rows_k)
        if sel.any():
            part = np.zeros((n, ntf))
            partv = np.zeros((n, nvar))
            TS.itreeshap(T, Xe, Xb, px[sel], pb[sel], pw[sel], poc, ntf, part)
            TS.itreeshap(T, Xe, Xb, px[sel], pb[sel], pw[sel], pocv, nvar, partv)
            if Ce is not None:
                TS.itreeshap(Ct, Xe, Xb, px[sel], pb[sel], pw[sel], poc, ntf, part)
                TS.itreeshap(Ct, Xe, Xb, px[sel], pb[sel], pw[sel], pocv, nvar, partv)
            phi[:, :ntf] += part * bk[:, None]
            phiv += partv * bk[:, None]
        if (c + 1) % 1000 == 0:
            log("  %d of %d trees (%.0f s)" % (c + 1, used.size, time.time() - t1))
    tsec = time.time() - t1
    # linear terms (normal, context): per-pair differences first, so equal values give exactly 0
    b_lin, lin_e = d["b_lin"], d["lin_e"]
    if kind == "neighbour":
        lin_pairs = d["bg_lin_pairs"]
    elif kind == "per_unit":
        lin_pairs = d["lin_bg_all"][pb]
    else:
        lin_pairs = d["region_lin_pairs"]
    lin_const = RW.linear_constant(lin_e, lin_pairs, px, n)
    for l, p in enumerate(lin_players):
        if p is None:
            continue
        diff = np.bincount(px, weights=(lin_e[px, l] - lin_pairs[:, l]) * pw, minlength=n)
        term = b_lin[:, l] * diff
        phi[:, pidx[lin_target[p]]] += term
        phiv[:, vidx[vmap[lin_target[p]]]] += term
    eta_lin_e = (b_lin * lin_e).sum(1)
    eta_ours = eta_lin_e + A_e
    eta_pair = (b_lin[px] * lin_pairs).sum(1) + A_pair
    base = np.bincount(px, weights=eta_pair * pw, minlength=n)
    resid = eps_e - np.bincount(px, weights=eps_pair * pw, minlength=n)
    # S-ZERO masks: tree columns and linear columns of each player equal on every background row
    const = RW.constant_mask(Xe, Xb, px, pb, poc, nplay)
    constv = RW.constant_mask(Xe, Xb, px, pb, pocv, nvar)
    for l, p in enumerate(lin_players):
        if p is None:
            continue
        const[:, pidx[lin_target[p]]] &= lin_const[:, l]
        constv[:, vidx[vmap[lin_target[p]]]] &= lin_const[:, l]
    # a player with no column at all in this model (none here) stays constant -> 0
    checks, gap_bound, eta_bg, eta_bg_model, eta_bg_bound = {}, None, None, None, None
    if kind in ("neighbour", "per_unit"):
        eng_bg = d["bg_eta_pairs"] if kind == "neighbour" else d["eta_bg_all"][pb]
        eta_bg, eta_bg_model = eta_pair, eng_bg
        eta_w, eta_model = eta_ours, d["eta_e"]
    else:
        ncol = int(Bm.sum(1).max()) if Bm.size else 0
        gam = (ncol + 1) * U32 / (1 - (ncol + 1) * U32)
        gap_bound = 1.01 * (gam * absA_e + 4 * 2.0 ** -53 * (np.abs(d["eta_e"]) + np.abs(eta_lin_e) + 1.0))
        eta_bg, eta_bg_model = eta_pair, d["region_bg_eta_engine"]
        eta_bg_bound = 1.01 * (gam * absA_pair + 4 * 2.0 ** -53 * (np.abs(eta_bg_model) + 1.0))
        eta_w, eta_model = eta_ours, d["eta_e"]
        checks["float32_dot_terms_max"] = ncol
    pc = pq.read_table(os.path.join(d["rb"], "preds_check.parquet")).to_pandas()
    pre = S[["unit", "time"]].merge(pc[["unit", "time", "pre_rebuilt"]], on=["unit", "time"], how="left")[
        "pre_rebuilt"].to_numpy(np.float64)
    link, cc, ub = done["link"], done.get("c"), done.get("ub")
    meta = {"model": "treeroute", "problem": a.problem, "lead": a.lead, "arm": done["arm"], "link": link, "c": cc,
            "ub": ub, "kind": kind, "background": a.background, "trees_used": int(used.size),
            "corrector_arm": corrector, "tree_shap_seconds": round(tsec, 1), "pairs": int(px.size),
            "value_function": "interventional, per-row background", "checks": checks,
            "duplicates_merged": dup, "variable_map": vmap, "guard": {"passed": True, "source": "the kept arm"},
            "sample_sha256": d["ident"]["sample_sha256"], "d8_licence": done.get("d8_licence"),
            "rebuild_e8_bit_identical": done.get("e8_bit_identical")}
    Bk = d["Bk"]
    rec = RW.write(out, S, players, phi, variables, phiv, base, eta_w, eta_model, pre, resid, meta, log, Bk,
                   const=const, constv=constv, gap_bound=gap_bound, eta_bg=eta_bg, eta_bg_model=eta_bg_model,
                   eta_bg_bound=eta_bg_bound)
    C.mark_done(os.path.join(out, "rows.parquet"), inputs, {"seconds": round(time.time() - t0, 1),
                                                            "sample_sha256": d["ident"]["sample_sha256"],
                                                            "background_keys_sha256": rec["background_keys_sha256"]})
    log("treeroute SHAP %s lead %d done in %.1f s (tree SHAP %.1f s)" % (a.problem, a.lead, time.time() - t0, tsec))


if __name__ == "__main__":
    main()
