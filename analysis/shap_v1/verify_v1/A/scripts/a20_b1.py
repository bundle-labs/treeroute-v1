# Round 14, implementer A: brief item 9, treeroute's B1 sensitivity at lead 0 (PROTOCOL.md sections 5 and 10).
# Order: status of every problem; defo's identity check FIRST; the fire, pm25 and ndvi numbers only when the
# identity check holds exactly (0 with the same rows, players and variables). Uses the same code (a_core) and so
# the same open choices as the main pairs. Writes V\A\work\b1.json and V\A\draws\b1_<p>.npz.
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

import a_lib as L
import a_core as C

META_FIELDS = ["pass", "checks_passed", "rows", "background", "pairs", "trees_used", "sample_sha256", "duplicates_merged"]
B1_FROM = "2026-11-15 23:06"
LINE_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*([0-9.]+)s\] (.*)$")


def registered_samples():
    path = os.path.join(L.SHAP, "SAMPLE_REGISTER.txt")
    L.note_open(path)
    reg = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            m = re.search(r"problem=(\S+)", line)
            if not m:
                continue
            leads = re.search(r"leads=(\S+)", line).group(1).split(",")
            sm = re.search(r"\bsample=([0-9a-f]{64})", line).group(1)
            reg.setdefault(m.group(1), []).append((leads, sm, line.split()[0]))
    return reg


def status(p, reg, pl_models):
    folder = os.path.join(L.SHAP, "out", p, "lead_0", "treeroute_B1")
    st = {"folder_exists": os.path.isdir(folder)}
    st["has_done_json"] = os.path.isfile(os.path.join(folder, "rows.parquet.done.json"))
    st["has_failed_json"] = os.path.isfile(os.path.join(folder, "FAILED.json"))
    st["finished"] = bool(st["has_done_json"] and os.path.isfile(os.path.join(folder, "rows.parquet")))
    if st["has_failed_json"]:
        fp = os.path.join(folder, "FAILED.json")
        L.note_open(fp)
        with open(fp, "r", encoding="utf-8") as fh:
            fj = json.load(fh)
        txt = json.dumps(fj)
        hit = [s for s in ("S-ADD", "S-EVAL", "S-ZERO", "S-RESID") if s in txt]
        st["failed_stop"] = hit[0] if hit else None
        if not hit:
            st["failed_stop_why"] = "FAILED.json names none of S-ADD, S-EVAL, S-ZERO or S-RESID."
    else:
        st["failed_stop"] = None
        st["failed_stop_why"] = ("No FAILED.json in the folder." if st["folder_exists"] else
                                 "No treeroute_B1 folder exists for this problem.")
    if st["finished"]:
        meta = L.read_meta(p, "treeroute_B1")
        st["meta"] = {k: meta[k] for k in META_FIELDS}
        st["background_is_B1"] = meta["background"] == "B1"
        ent = [sm for leads, sm, ts in reg.get(p, []) if "0" in leads]
        st["sample_sha256_registered"] = ent[0] if len(ent) == 1 else None
        if len(ent) != 1:
            st["sample_sha256_registered_why"] = "SAMPLE_REGISTER.txt has %d lead-0 entries for this problem." % len(ent)
            st["sample_sha256_is_registered"] = None
            st["sample_sha256_is_registered_why"] = "No single registered entry to compare with."
        else:
            st["sample_sha256_is_registered"] = meta["sample_sha256"] == ent[0]
    else:
        why = "No finished B1 piece (no rows.parquet.done.json) for this problem."
        st["meta"] = None; st["meta_why"] = why
        st["background_is_B1"] = None; st["background_is_B1_why"] = why
        ent = [sm for leads, sm, ts in reg.get(p, []) if "0" in leads]
        if len(ent) == 1:
            st["sample_sha256_registered"] = ent[0]
        else:
            st["sample_sha256_registered"] = None
            st["sample_sha256_registered_why"] = "SAMPLE_REGISTER.txt has %d lead-0 entries for this problem." % len(ent)
        st["sample_sha256_is_registered"] = None; st["sample_sha256_is_registered_why"] = why
    st["per_lead_models_lists_treeroute_B1"] = "treeroute_B1" in pl_models
    return st


def log_facts(p):
    path = os.path.join(L.SHAP, "logs", "tr_shap_%s_lead0.log" % p)
    L.note_open(path)
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    setup = done = None
    for i, line in enumerate(lines, start=1):
        m = LINE_RE.match(line)
        if not m or m.group(1)[:16] < B1_FROM:
            continue
        if setup is None and "background pairs" in m.group(3):
            setup = (i, m.group(3))
        if "done in" in m.group(3):
            done = (i, m.group(3))
    out = {"log_file": "SHAP\\logs\\tr_shap_%s_lead0.log" % p}
    if setup:
        out["log_setup_line_number"] = setup[0]
        out["pairs_log"] = int(re.search(r"rows, (\d+) background pairs", setup[1]).group(1))
    else:
        out["log_setup_line_number"] = None; out["log_setup_line_number_why"] = "No B1 set-up line in the log."
        out["pairs_log"] = None; out["pairs_log_why"] = "No B1 set-up line in the log."
    if done:
        out["log_done_line_number"] = done[0]
        out["total_seconds_log"] = float(re.search(r"done in ([0-9.]+) s", done[1]).group(1))
        out["tree_shap_seconds_log"] = float(re.search(r"\(tree SHAP ([0-9.]+) s\)", done[1]).group(1))
    else:
        for k in ("log_done_line_number", "total_seconds_log", "tree_shap_seconds_log"):
            out[k] = None; out[k + "_why"] = "No B1 'done in' line in the log."
    meta = L.read_meta(p, "treeroute_B1")
    done_j = L.read_done(p, "treeroute_B1")
    out["pairs_meta"] = int(meta["pairs"])
    out["total_seconds_done_json"] = float(done_j["seconds"])
    out["tree_shap_seconds_meta"] = float(meta["tree_shap_seconds"])
    return out


def identity_check(p):
    a = L.read_rows(p, "treeroute")
    b = L.read_rows(p, "treeroute_B1")
    ra, rb = a["keys"]["row"], b["keys"]["row"]
    sa, sb = set(ra.tolist()), set(rb.tolist())
    common = sorted(sa & sb)
    ia = np.searchsorted(ra, common); ib = np.searchsorted(rb, common)
    res = {}
    for lev, key, mat, lab in (("feature", "players", "phi", "phi"), ("variable", "variables", "phiv", "phiv")):
        na, nb = a[key], b[key]
        cm = sorted(set(na) & set(nb))
        ca = [na.index(n) for n in cm]; cb = [nb.index(n) for n in cm]
        diff = np.abs(a[mat][np.ix_(ia, ca)] - b[mat][np.ix_(ib, cb)])
        res[lab] = (float(diff.max()) if diff.size else None, sorted(set(na) - set(nb)), sorted(set(nb) - set(na)),
                    len(na), len(nb), int((diff != 0).sum()))
    keys_same = all(np.array_equal(a["keys"][c][ia], b["keys"][c][ib]) for c in L.KEYCOLS)
    d = {"max_abs_diff_phi": res["phi"][0], "max_abs_diff_phiv": res["phiv"][0],
         "same_rows": sa == sb and len(ra) == len(rb), "same_players": not res["phi"][1] and not res["phi"][2],
         "same_variables": not res["phiv"][1] and not res["phiv"][2],
         "n_rows_main": int(len(ra)), "n_rows_b1": int(len(rb)),
         "n_players_main": res["phi"][3], "n_players_b1": res["phi"][4],
         "n_variables_main": res["phiv"][3], "n_variables_b1": res["phiv"][4],
         "rows_only_in_main": sorted(int(x) for x in sa - sb), "rows_only_in_b1": sorted(int(x) for x in sb - sa),
         "players_only_in_main": res["phi"][1], "players_only_in_b1": res["phi"][2],
         "variables_only_in_main": res["phiv"][1], "variables_only_in_b1": res["phiv"][2]}
    d["as_expected"] = bool(d["max_abs_diff_phi"] == 0.0 and d["max_abs_diff_phiv"] == 0.0 and d["same_rows"]
                            and d["same_players"] and d["same_variables"])
    for k in ("max_abs_diff_phi", "max_abs_diff_phiv"):
        if d[k] is None:
            d[k + "_why"] = "The two runs share no row or no column at this level."
    d["extra"] = {"cells_differing_phi": res["phi"][5], "cells_differing_phiv": res["phiv"][5],
                  "keys_unit_group_time_year_equal_on_matched_rows": bool(keys_same),
                  "rows_matched_by": "row", "columns_matched_by": "name"}
    d.update(log_facts(p))
    return d


def merge_context(rows, main_keys, b1_keys):
    """Brief item 9: if the B1 run lacks a merge that the main run made, sum phi__x__<v> and phi__c__ctx:top5:<v>
    of the B1 run into x__<v>. Returns the merged rows and the names formed."""
    summed = []
    for k in sorted(set(main_keys) - set(b1_keys)):
        v = k[len("c__ctx:top5:"):]
        x, c = "x__" + v, k
        pl = rows["players"]
        if x in pl and c in pl:
            ix, ic = pl.index(x), pl.index(c)
            rows["phi"][:, ix] = rows["phi"][:, ix] + rows["phi"][:, ic]
            keep = [i for i in range(len(pl)) if i != ic]
            rows["phi"] = rows["phi"][:, keep]
            rows["players"] = [pl[i] for i in keep]
            summed.append(x)
    return rows, summed


def b1_problem(p, pl):
    t0 = time.time()
    out = L.Out()
    draws, dsha, dpath = L.load_draws(p)
    main = L.read_rows(p, "treeroute")
    b1 = L.read_rows(p, "treeroute_B1")
    for c in L.KEYCOLS:
        if not np.array_equal(main["keys"][c], b1["keys"][c]):
            raise SystemExit("%s: B1 keys differ from the main run" % p)
    meta_m = L.read_meta(p, "treeroute")
    meta_b = L.read_meta(p, "treeroute_B1")
    dm_main = sorted(meta_m["duplicates_merged"].keys())
    dm_b1 = sorted(meta_b["duplicates_merged"].keys())
    nz_before = None
    regions, reg = L.region_index(main["keys"]["group"])
    G = len(regions)
    counts = L.draw_counts(draws, G)
    Wd = counts / float(G)
    M, has, cnt = L.region_mean_matrix(reg, G)
    # B1's nonzero players before any summing (feature level), over its own columns
    Ib_before = (M @ np.abs(b1["phi"])).mean(axis=0)
    Ib_before_d = Wd @ (M @ np.abs(b1["phi"]))
    nz_before = (int((Ib_before > 0).sum()), (Ib_before_d > 0).sum(axis=1).astype(np.float64))
    b1, summed = merge_context(b1, dm_main, dm_b1)
    with open(os.path.join(L.V_A, "work", "global_rule_%s.json" % p), "r", encoding="utf-8") as fh:
        var_family = json.load(fh)["variable_family"]
    run = log_facts(p)
    run.update({"duplicates_merged_main": dm_main, "duplicates_merged_b1": dm_b1, "context_columns_summed": sorted(summed),
                "draws_sha256_match": dsha == pl["draws_sha256"], "npz": "V\\A\\draws\\b1_%s.npz" % p})
    res = {"run": run}
    for level, key, mat in (("feature", "players", "phi"), ("variable", "variables", "phiv")):
        names = sorted(set(main[key]) | set(b1[key]))
        st = {}
        for lab, rows in (("treeroute", main), ("treeroute_B1", b1)):
            X, own = C.union_matrix(rows, key, mat, names)
            st[lab] = C.region_stats(X, M, Wd) + (own,)
        active = np.zeros(len(names), bool)
        for lab in st:
            I_f = st[lab][0]
            active |= I_f > L.THRESH * I_f.sum()
        jj = np.flatnonzero(active)
        Jn = [names[j] for j in jj]
        fam_ex = None
        mls = {}
        for lab, rows in (("treeroute", main), ("treeroute_B1", b1)):
            I_f, I_d, S_f, S_d, own = st[lab]
            fam = None
            if level == "variable":
                Fx = C.family_matrix(rows, var_family)
                FA = M @ np.abs(Fx)
                fam = (FA.mean(axis=0), Wd @ FA)
            mls[lab] = C.prepare(I_f, I_d, S_f, S_d, own, jj, Jn, fam)
        if level == "variable":
            fams = set(var_family[v] for v in names)
            fam_ex = [f in fams for f in L.FAMILIES]
        A, B = mls["treeroute"], mls["treeroute_B1"]
        base = [level]
        imp = {"players": out.players(base + ["importance", "players"], Jn, B.IJ_f, B.IJ_d, B.sh_f, B.sh_d, B.SJ_f,
                                      B.SJ_d, B.det),
               "n_nonzero": out.iv(base + ["importance", "n_nonzero"], B.nz_f, B.nz_d),
               "ranking": B.ranking}
        if level == "feature":
            imp["n_nonzero_before_merge"] = out.iv(base + ["importance", "n_nonzero_before_merge"], nz_before[0], nz_before[1])
        imp["extra"] = {"meta_players_nonzero": meta_b.get("players_nonzero"),
                        "meta_variables_nonzero": meta_b.get("variables_nonzero"),
                        "own_columns": int(B.own.sum()), "sign_determined_count": int(B.detb.sum())}
        tau = C.tau_b_pairs(mls, [("treeroute", "treeroute_B1")])[("treeroute", "treeroute_B1")]
        pr = {"pair": "treeroute|treeroute_B1", "J": Jn,
              "n_J": L.Out.iv_noci(len(Jn), "The pair's J is fixed at the full sample (the main pairs' choice C07), so its size has no interval."),
              "main_shares": {Jn[j]: float(A.sh_f[j]) for j in range(len(Jn))},
              "main_ranking": A.ranking}
        pr.update(C.pair_stats(out, base + ["pair_main_b1"], A, B, Jn, level, tau, fam_ex))
        pr["extra"].update({"names_in_pair": len(names), "structural_zeros_of_pair": sorted(n for n in names if n not in set(Jn)),
                            "J_players_exactly_zero_in_main": sorted(Jn[j] for j in range(len(Jn)) if A.IJ_f[j] == 0.0)})
        lv = {"importance": imp, "top10": B.top10, "pair_main_b1": pr}
        if level == "variable":
            fobj = {}
            for k, f in enumerate(L.FAMILIES):
                if fam_ex[k]:
                    fobj[f] = out.iv(base + ["families", f], B.fs_f[k], B.fs_d[:, k])
                else:
                    fobj[f] = None
                    fobj[f + "_why"] = "The problem has no variable of this family, so the family has no share."
            fobj["extra"] = {"main_run_family_shares": {f: L.fnum(A.fs_f[k]) for k, f in enumerate(L.FAMILIES) if fam_ex[k]}}
            lv["families"] = fobj
            lv["top3"] = B.top3
            oh = L.FAMILIES.index("own_history")
            if fam_ex[oh]:
                lv["own_history_share"] = out.iv(base + ["own_history_share"], B.fs_f[oh], B.fs_d[:, oh])
            else:
                lv["own_history_share"] = None
                lv["own_history_share_why"] = "The problem has no own-history (hist_*) variable."
        res[level] = lv
    np.savez_compressed(os.path.join(L.V_A, "draws", "b1_%s.npz" % p), **out.npz)
    print("b1 %s: done in %.1f s; pair J feature %d, variable %d" % (p, time.time() - t0, len(res["feature"]["pair_main_b1"]["J"]),
                                                                    len(res["variable"]["pair_main_b1"]["J"])))
    return res


def main():
    t0 = time.time()
    reg = registered_samples()
    out = {}
    pls = {p: L.read_per_lead_struct(p) for p in L.PROBLEMS}
    for p in L.PROBLEMS:
        out[p] = {"status": status(p, reg, pls[p]["models"])}
    # coral: B1 is not defined (section 5)
    cst = out["coral"]["status"]
    cst["numbers"] = "none"
    cst["numbers_why"] = ("B1 is not defined for coral (PROTOCOL.md section 5; tr_shap.py refuses the neighbour kind), "
                          "and no treeroute_B1 folder exists, so coral has no B1 number.")
    # defo: the identity check FIRST
    dst = out["defo"]["status"]
    if dst["finished"]:
        ident = identity_check("defo")
        out["defo"]["identity"] = ident
        dst["numbers"] = "identity"
        dst["numbers_why"] = ("Defo's B1 background equals its main run's (annual data; section 10), so only the identity "
                              "check with its pairs and seconds is reported; it %s." % (
                                  "holds exactly (0, the same rows, players and variables)" if ident["as_expected"] else
                                  "does NOT hold, which stops the B1 work"))
        ok = ident["as_expected"]
    else:
        dst["numbers"] = "none"
        dst["numbers_why"] = "Defo has no finished B1 piece, so no identity check can be made."
        ok = False
    for p in ("fire", "pm25", "ndvi"):
        st = out[p]["status"]
        if not ok:
            st["numbers"] = "none"
            st["numbers_why"] = ("Defo's identity check did not hold (or could not be made); the brief stops the B1 work "
                                 "there and holds back every fire, pm25 and ndvi B1 number until the cause is recorded.")
            continue
        if not st["finished"]:
            st["numbers"] = "none"
            st["numbers_why"] = "No finished B1 piece for this problem (no rows.parquet.done.json), so it gets no B1 numbers."
            continue
        if not st["background_is_B1"] or not st["sample_sha256_is_registered"]:
            st["numbers"] = "none"
            st["numbers_why"] = "The B1 piece's background is not 'B1' or its sample is not the registered one."
            continue
        out[p].update(b1_problem(p, pls[p]))
        st["numbers"] = "full"
        st["numbers_why"] = ("A finished B1 piece (background B1, registered sample, all four checks passed) and defo's "
                             "identity check held, so section 10's B1 list is computed.")
    with open(os.path.join(L.V_A, "work", "b1.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, allow_nan=False)
    with open(os.path.join(L.V_A, "work", "opened_b1.json"), "w", encoding="utf-8") as fh:
        json.dump(sorted(L.OPENED), fh, indent=1)
    print("b1 total %.1f s; defo identity:" % (time.time() - t0),
          {k: out["defo"].get("identity", {}).get(k) for k in ("max_abs_diff_phi", "max_abs_diff_phiv", "same_rows",
                                                              "same_players", "same_variables", "as_expected")})


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--identity-only":
        reg = registered_samples()
        pl = L.read_per_lead_struct("defo")
        st = status("defo", reg, pl["models"])
        print("defo status:", {k: v for k, v in st.items() if k != "meta"})
        d = identity_check("defo")
        print({k: d[k] for k in ("max_abs_diff_phi", "max_abs_diff_phiv", "same_rows", "same_players", "same_variables",
                                 "n_rows_main", "n_rows_b1", "n_players_main", "n_players_b1", "n_variables_main",
                                 "n_variables_b1", "as_expected", "log_setup_line_number", "log_done_line_number",
                                 "pairs_log", "pairs_meta", "total_seconds_log", "total_seconds_done_json",
                                 "tree_shap_seconds_log", "tree_shap_seconds_meta")}, d["extra"])
    else:
        main()
