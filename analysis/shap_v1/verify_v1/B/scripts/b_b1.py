# Implementer B, round 14: brief item 9, treeroute's B1 sensitivity (PROTOCOL.md section 10, B1 bullet), lead 0.
# Reads: the B1 pieces SHAP\out\<p>\lead_0\treeroute_B1\ (meta.json, rows.parquet, rows.parquet.done.json,
# FAILED.json if any, background_keys.parquet), the main runs SHAP\out\<p>\lead_0\treeroute\ (same files),
# per_lead.json's structural keys `models` and `draws_sha256`, compare\bootstrap_draws.npy, SHAP\SAMPLE_REGISTER.txt,
# SHAP\logs\tr_shap_<p>_lead0.log and V\B\work\global_<p>.json (items 1-3's global-index rule).
# Order: the defo identity check first; only if it gives 0 with the same rows, players and variables are the
# fire, pm25 and ndvi numbers computed. Writes V\B\work\b1.json and V\B\draws\b1_<p>.npz.
import datetime
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pyarrow.parquet as pq
import b_lib as L

PROBLEMS = ["coral", "defo", "fire", "pm25", "ndvi"]
FULL = ["fire", "pm25", "ndvi"]
META_FIELDS = ["pass", "checks_passed", "rows", "background", "pairs", "trees_used", "sample_sha256", "duplicates_merged"]
LOG_FROM = datetime.datetime(2026, 11, 15, 23, 6, 0)
CTX = "c__ctx:top5:"
WHY_NJ = "The pair's J is fixed at the full sample (choices.md C07, as for the main pairs), so its count has no interval (C08)."


def registered_samples():
    reg = {}
    for line in (L.SHAP / "SAMPLE_REGISTER.txt").read_text(encoding="utf-8").splitlines():
        mp = re.search(r"\bproblem=(\S+)", line)
        ms = re.search(r"\bsample=([0-9a-f]{64})\b", line)
        ml = re.search(r"\bleads=(\S+)", line)
        if mp and ms:
            reg.setdefault(mp.group(1), []).append({"sample": ms.group(1), "leads": ml.group(1) if ml else None})
    return reg


def per_lead_struct(p):
    pl = json.loads((L.SHAP / "out" / p / "lead_0" / "compare" / "per_lead.json").read_text(encoding="utf-8"))
    out = {"models": list(pl["models"]), "draws_sha256": pl["draws_sha256"]}
    del pl
    return out


def status(p, reg, pls):
    f = L.SHAP / "out" / p / "lead_0" / "treeroute_B1"
    st = {"folder_exists": f.is_dir()}
    st["has_done_json"] = (f / "rows.parquet.done.json").is_file()
    st["has_failed_json"] = (f / "FAILED.json").is_file()
    st["finished"] = st["has_done_json"] and not st["has_failed_json"]
    if st["has_failed_json"]:
        fj = json.loads((f / "FAILED.json").read_text(encoding="utf-8"))
        gate = fj.get("gate")
        if not gate and isinstance(fj.get("checks_passed"), dict):
            gate = ",".join(sorted(k for k, v in fj["checks_passed"].items() if v is False))
        st["failed_stop"] = gate or "FAILED.json names no stop"
    else:
        st["failed_stop"] = None
        st["failed_stop_why"] = ("No FAILED.json in the folder." if st["folder_exists"] else
                                 "No treeroute_B1 folder (B1 is not defined for coral, section 5)." if p == "coral" else
                                 "No treeroute_B1 folder.")
    meta = None
    if st["finished"]:
        meta = json.loads((f / "meta.json").read_text(encoding="utf-8"))
        st["meta"] = {k: meta[k] for k in META_FIELDS}
        st["background_is_B1"] = meta["background"] == "B1"
    else:
        why = "Not a finished B1 piece, so there is no meta.json to copy."
        st["meta"] = None
        st["meta_why"] = why
        st["background_is_B1"] = None
        st["background_is_B1_why"] = why
    entries = [e for e in reg.get(p, []) if e["leads"] is None or "0" in e["leads"].split(",")]
    if len(entries) == 1:
        st["sample_sha256_registered"] = entries[0]["sample"]
    else:
        st["sample_sha256_registered"] = None
        st["sample_sha256_registered_why"] = "SAMPLE_REGISTER.txt has %d lines for this problem's lead 0." % len(entries)
    if meta is not None and st["sample_sha256_registered"] is not None:
        st["sample_sha256_is_registered"] = meta["sample_sha256"] == st["sample_sha256_registered"]
    else:
        st["sample_sha256_is_registered"] = None
        st["sample_sha256_is_registered_why"] = "No finished B1 piece whose sample SHA-256 could be compared."
    st["per_lead_models_lists_treeroute_B1"] = "treeroute_B1" in pls["models"]
    return st, meta


def log_facts(p, meta_b1, done_b1):
    path = L.SHAP / "logs" / ("tr_shap_%s_lead0.log" % p)
    out = {"log_file": "SHAP\\logs\\tr_shap_%s_lead0.log" % p}
    setup = done = None
    n_setup = n_done = 0
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        m = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[\d.]+s\] (.*)$", line)
        if not m:
            continue
        ts = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        if ts < LOG_FROM:
            continue
        rest = m.group(2)
        ms = re.search(r"(\d+) rows, (\d+) background pairs", rest)
        if ms:
            n_setup += 1
            if setup is None:
                setup = (i, int(ms.group(2)))
        md = re.search(r"done in ([\d.]+) s \(tree SHAP ([\d.]+) s\)", rest)
        if md and setup is not None:
            n_done += 1
            if done is None:
                done = (i, float(md.group(1)), float(md.group(2)))
    why_s = "No set-up line ('background pairs') written from 2026-11-15 23:06 in the log."
    why_d = "No 'done in' line after the B1 set-up line in the log."
    out["log_setup_line_number"] = setup[0] if setup else None
    if not setup:
        out["log_setup_line_number_why"] = why_s
    out["log_done_line_number"] = done[0] if done else None
    if not done:
        out["log_done_line_number_why"] = why_d
    out["pairs_log"] = setup[1] if setup else None
    if not setup:
        out["pairs_log_why"] = why_s
    out["pairs_meta"] = meta_b1.get("pairs") if meta_b1 else None
    if out["pairs_meta"] is None:
        out["pairs_meta_why"] = "No pairs field in a finished B1 meta.json."
    out["total_seconds_log"] = done[1] if done else None
    if not done:
        out["total_seconds_log_why"] = why_d
    out["total_seconds_done_json"] = done_b1.get("seconds") if done_b1 else None
    if out["total_seconds_done_json"] is None:
        out["total_seconds_done_json_why"] = "No seconds field in a finished B1 rows.parquet.done.json."
    out["tree_shap_seconds_log"] = done[2] if done else None
    if not done:
        out["tree_shap_seconds_log_why"] = why_d
    out["tree_shap_seconds_meta"] = meta_b1.get("tree_shap_seconds") if meta_b1 else None
    if out["tree_shap_seconds_meta"] is None:
        out["tree_shap_seconds_meta_why"] = "No tree_shap_seconds field in a finished B1 meta.json."
    return out, {"setup_lines_from_2026-11-15_23:06": n_setup, "done_lines_after_setup": n_done}


def identity_defo(meta_b1, done_b1):
    d0 = L.SHAP / "out" / "defo" / "lead_0"
    main = pq.read_table(d0 / "treeroute" / "rows.parquet").to_pandas()
    b1 = pq.read_table(d0 / "treeroute_B1" / "rows.parquet").to_pandas()
    rm, rb = set(main["row"].tolist()), set(b1["row"].tolist())
    pm = [c[5:] for c in main.columns if c.startswith("phi__")]
    pb = [c[5:] for c in b1.columns if c.startswith("phi__")]
    vm = [c[6:] for c in main.columns if c.startswith("phiv__")]
    vb = [c[6:] for c in b1.columns if c.startswith("phiv__")]
    common_rows = sorted(rm & rb)
    mi = main.set_index("row").loc[common_rows]
    bi = b1.set_index("row").loc[common_rows]

    def maxdiff(cols):
        if not cols:
            return None
        a = mi[cols].to_numpy(dtype=np.float64)
        b = bi[cols].to_numpy(dtype=np.float64)
        assert np.isfinite(a).all() and np.isfinite(b).all()
        return float(np.max(np.abs(b - a)))

    cp = ["phi__" + n for n in sorted(set(pm) & set(pb))]
    cv = ["phiv__" + n for n in sorted(set(vm) & set(vb))]
    out = {"max_abs_diff_phi": maxdiff(cp), "max_abs_diff_phiv": maxdiff(cv)}
    for k in ("max_abs_diff_phi", "max_abs_diff_phiv"):
        if out[k] is None:
            out[k + "_why"] = "No common column of this kind."
    out.update({"same_rows": rm == rb, "same_players": set(pm) == set(pb), "same_variables": set(vm) == set(vb),
                "n_rows_main": len(main), "n_rows_b1": len(b1), "n_players_main": len(pm), "n_players_b1": len(pb),
                "n_variables_main": len(vm), "n_variables_b1": len(vb),
                "rows_only_in_main": sorted(int(x) for x in rm - rb), "rows_only_in_b1": sorted(int(x) for x in rb - rm),
                "players_only_in_main": sorted(set(pm) - set(pb)), "players_only_in_b1": sorted(set(pb) - set(pm)),
                "variables_only_in_main": sorted(set(vm) - set(vb)), "variables_only_in_b1": sorted(set(vb) - set(vm))})
    out["as_expected"] = (out["max_abs_diff_phi"] == 0.0 and out["max_abs_diff_phiv"] == 0.0 and out["same_rows"]
                          and out["same_players"] and out["same_variables"]
                          and len(main) == len(rm) and len(b1) == len(rb))
    # diagnostics: the other columns and the background keys
    other = {}
    for c in ("base", "eta", "eta_model", "pre", "resid", "gap", "add_err"):
        other[c] = float(np.max(np.abs(bi[c].to_numpy(dtype=np.float64) - mi[c].to_numpy(dtype=np.float64))))
    for c in ("unit", "group", "time", "year", "resid_flag"):
        other[c + "_equal"] = bool((bi[c].to_numpy() == mi[c].to_numpy()).all())
    other["phi_column_order_equal"] = pm == pb
    other["phiv_column_order_equal"] = vm == vb
    other["rows_file_sha256_equal"] = L.sha256_file(d0 / "treeroute" / "rows.parquet") == L.sha256_file(d0 / "treeroute_B1" / "rows.parquet")
    other["background_keys_file_sha256_equal"] = (L.sha256_file(d0 / "treeroute" / "background_keys.parquet") ==
                                                  L.sha256_file(d0 / "treeroute_B1" / "background_keys.parquet"))
    out["extra"] = {"other_columns_max_abs_diff_or_equal": other}
    facts, fx = log_facts("defo", meta_b1, done_b1)
    out.update(facts)
    out["extra"]["log_lines"] = fx
    return out


def merge_context(players, X, dup_main, dup_b1):
    """Sum the B1 run's tree player and context player of each column the main run merged and B1 did not."""
    summed = []
    players = list(players)
    for key in sorted(set(dup_main) - set(dup_b1)):
        assert key.startswith(CTX), key
        v = key[len(CTX):]
        tree, ctx = "x__" + v, "c__ctx:top5:" + v
        if tree in players and ctx in players:
            it, ic = players.index(tree), players.index(ctx)
            X = X.copy()
            X[:, it] = X[:, it] + X[:, ic]
            keep = [k for k in range(len(players)) if k != ic]
            X = X[:, keep]
            players = [players[k] for k in keep]
            summed.append(tree)
    return players, X, sorted(summed)


def b1_problem(p, st, meta_b1):
    t0 = time.time()
    lead = L.SHAP / "out" / p / "lead_0"
    pls = per_lead_struct(p)
    dpath = lead / "compare" / "bootstrap_draws.npy"
    sha = L.sha256_file(dpath)
    draws = np.load(dpath, allow_pickle=False)
    B, G = draws.shape
    Cs = np.vstack([np.ones((1, G)), L.draw_counts(draws, G)])
    meta_main = json.loads((lead / "treeroute" / "meta.json").read_text(encoding="utf-8"))
    done_b1 = json.loads((lead / "treeroute_B1" / "rows.parquet.done.json").read_text(encoding="utf-8"))
    gl = json.loads((L.VB / "work" / ("global_%s.json" % p)).read_text(encoding="utf-8"))
    gi = set(gl["global_indices"])
    rows = {}
    keys = {}
    for run, folder in (("main", "treeroute"), ("b1", "treeroute_B1")):
        for level in ("feature", "variable"):
            k, players, X = L.load_rows(lead / folder / "rows.parquet", level, ("row", "group"))
            assert np.isfinite(X).all()
            rows[(run, level)] = (players, X)
            keys[run] = k
    assert keys["main"]["row"].tolist() == keys["b1"]["row"].tolist()
    assert keys["main"]["group"].tolist() == keys["b1"]["group"].tolist()
    regions = sorted(keys["main"]["group"].unique().tolist())
    assert len(regions) == G
    rix = {r: i for i, r in enumerate(regions)}
    region = np.array([rix[g] for g in keys["main"]["group"]])
    # merged context columns (feature level only)
    pf, Xf = rows[("b1", "feature")]
    n_before = {"players": list(pf), "X": Xf}
    pf2, Xf2, summed = merge_context(pf, Xf, meta_main["duplicates_merged"], meta_b1["duplicates_merged"])
    rows[("b1", "feature")] = (pf2, Xf2)
    # families (variable-level phi; items 1-3's families and global-index rule)
    allvars = sorted(set(rows[("main", "variable")][0]) | set(rows[("b1", "variable")][0]))
    vf = {v: L.family_of(v, gi) for v in allvars}
    fam = {run: L.family_stack(rows[(run, "variable")][0], rows[(run, "variable")][1], vf, region, G, Cs)
           for run in ("main", "b1")}
    D = L.Draws()
    res = {}
    for level in ("feature", "variable"):
        U = sorted(set(rows[("main", level)][0]) | set(rows[("b1", level)][0]))
        ui = {n: k for k, n in enumerate(U)}
        I_all, S_all, own = {}, {}, {}
        for run in ("main", "b1"):
            players, X = rows[(run, level)]
            Xu = np.zeros((X.shape[0], len(U)))
            cols = [ui[n] for n in players]
            Xu[:, cols] = X
            own[run] = np.zeros(len(U), dtype=bool)
            own[run][cols] = True
            A, _ = L.region_means(np.abs(Xu), region, G)
            Ag, _ = L.region_means(Xu, region, G)
            I_all[run] = L.weighted_over_regions(Cs, A)
            S_all[run] = L.weighted_over_regions(Cs, Ag)
        inJ = np.zeros(len(U), dtype=bool)
        for run in ("main", "b1"):
            inJ |= I_all[run][0] > L.ACTIVE_REL * I_all[run][0].sum()
        J = [n for n, f in zip(U, inJ) if f]
        jidx = np.flatnonzero(inJ)
        MB = {run: L.model_block(I_all[run], S_all[run], jidx) for run in ("main", "b1")}
        tau = L.kendall_tau_b_all({"main": MB["main"]["IJ"], "b1": MB["b1"]["IJ"]}, [("main", "b1")])[("main", "b1")]
        stats, _, _ = L.pair_block(D, [level, "pair_main_b1"], J, MB["main"], MB["b1"], fam["main"], fam["b1"], tau)
        pair = {"pair": "treeroute|treeroute_B1", "J": J, "n_J": L.no_interval(len(J), WHY_NJ),
                "main_shares": {J[i]: float(MB["main"]["SH"][0, i]) for i in range(len(J))},
                "main_ranking": [J[i] for i in MB["main"]["ORD"][0]]}
        pair.update(stats)
        pair["extra"] = {"players_in_pair_J_not_in_main_J_rule": [J[i] for i in range(len(J))
                                                                   if not (I_all["main"][0, jidx[i]] > L.ACTIVE_REL * I_all["main"][0].sum())],
                         "main_players_nonzero_in_pair_J": int((MB["main"]["IJ"][0] > 0).sum())}
        b = MB["b1"]
        nz = (I_all["b1"] > 0) & own["b1"][None, :]
        imp = {"players": D.players([level, "importance", "players"], J, b["IJ"], b["SH"], b["SG"], b["DET"]),
               "n_nonzero": D.iv([level, "importance", "n_nonzero"], nz.sum(axis=1).astype(np.float64)),
               "ranking": [J[i] for i in b["ORD"][0]]}
        if level == "feature":
            # before any summing of merged context columns
            Ub = n_before["players"]
            Xb = n_before["X"]
            A, _ = L.region_means(np.abs(Xb), region, G)
            Ib = L.weighted_over_regions(Cs, A)
            imp["n_nonzero_before_merge"] = D.iv([level, "importance", "n_nonzero_before_merge"],
                                                 (Ib > 0).sum(axis=1).astype(np.float64))
            imp["extra"] = {"meta_players_nonzero": meta_b1.get("players_nonzero"), "n_players_before_merge": len(Ub)}
        else:
            imp["extra"] = {"meta_variables_nonzero": meta_b1.get("variables_nonzero")}
        e = {"importance": imp, "top10": L.top_list(J, b["ORD"][0], b["SH"][0], 10), "pair_main_b1": pair}
        if level == "variable":
            e["families"] = {f: D.iv([level, "families", f], fam["b1"][:, k]) for k, f in enumerate(L.FAMILIES)}
            e["top3"] = L.top_list(J, b["ORD"][0], b["SH"][0], 3)
            e["own_history_share"] = D.iv([level, "own_history_share"], fam["b1"][:, L.FAMILIES.index("own_history")])
            e["extra"] = {"main_family_shares_full_sample": {f: float(fam["main"][0, k]) for k, f in enumerate(L.FAMILIES)},
                          "variable_family_used": {v: vf[v] for v in allvars}}
        res[level] = e
    facts, fx = log_facts(p, meta_b1, done_b1)
    run = dict(facts)
    run.update({"duplicates_merged_main": sorted(meta_main["duplicates_merged"]),
                "duplicates_merged_b1": sorted(meta_b1["duplicates_merged"]),
                "context_columns_summed": summed,
                "draws_sha256_match": sha == pls["draws_sha256"],
                "npz": "V\\B\\draws\\b1_%s.npz" % p,
                "extra": {"log_lines": fx, "draws_sha256_computed": sha, "seconds": round(time.time() - t0, 1)}})
    np.savez_compressed(L.VB / "draws" / ("b1_%s.npz" % p), **D.a)
    return run, res


def main():
    t_all = time.time()
    reg = registered_samples()
    out = {}
    metas = {}
    for p in PROBLEMS:
        st, meta = status(p, reg, per_lead_struct(p))
        out[p] = {"status": st}
        metas[p] = meta
    out["coral"]["status"]["numbers"] = "none"
    out["coral"]["status"]["numbers_why"] = ("B1 is not defined for coral (section 5: the neighbour kind); there is no "
                                             "treeroute_B1 piece, so coral gets no B1 numbers.")
    # 1. defo: the identity check first
    sd = out["defo"]["status"]
    defo_ok = False
    if sd["finished"]:
        done_b1 = json.loads((L.SHAP / "out" / "defo" / "lead_0" / "treeroute_B1" / "rows.parquet.done.json").read_text(encoding="utf-8"))
        ident = identity_defo(metas["defo"], done_b1)
        out["defo"]["identity"] = ident
        sd["numbers"] = "identity"
        defo_ok = ident["as_expected"]
        sd["numbers_why"] = ("Defo's B1 background equals its main run's (annual data), so only the identity check is "
                             "reported (section 10)" + (": it gives 0 with the same rows, players and variables." if defo_ok else
                             ": it does NOT give 0 with the same rows, players and variables; the other B1 numbers are held back."))
        print("defo identity:", {k: ident[k] for k in ("max_abs_diff_phi", "max_abs_diff_phiv", "same_rows", "same_players",
                                                       "same_variables", "as_expected")})
    else:
        sd["numbers"] = "none"
        sd["numbers_why"] = "Defo has no finished B1 piece, so neither its identity check nor any other B1 number can be computed."
    # 2. fire, pm25, ndvi only when the defo check holds
    for p in FULL:
        s = out[p]["status"]
        if not defo_ok:
            s["numbers"] = "none"
            s["numbers_why"] = ("Defo's identity check did not give 0 with the same rows, players and variables (or could "
                                "not be made), so no B1 number of fire, PM2.5 or NDVI is computed (section 10; the brief).")
            continue
        if not s["finished"]:
            s["numbers"] = "none"
            s["numbers_why"] = "No finished B1 piece (%s), so this problem gets no B1 numbers." % (
                "stopped at %s" % s["failed_stop"] if s["has_failed_json"] else "no rows.parquet.done.json")
            continue
        t0 = time.time()
        run, res = b1_problem(p, s, metas[p])
        out[p]["run"] = run
        out[p].update(res)
        s["numbers"] = "full"
        s["numbers_why"] = ("A finished B1 piece (rows.parquet.done.json, no FAILED.json) and defo's identity check held, "
                            "so every number of section 10's B1 bullet is computed.")
        print("%s B1 done in %.1f s (pair J feature %d, variable %d)" % (p, time.time() - t0, len(res["feature"]["pair_main_b1"]["J"]),
                                                                       len(res["variable"]["pair_main_b1"]["J"])))
    L.dump_json(out, L.VB / "work" / "b1.json")
    print("item 9 done in %.1f s" % (time.time() - t_all))


if __name__ == "__main__":
    main()
