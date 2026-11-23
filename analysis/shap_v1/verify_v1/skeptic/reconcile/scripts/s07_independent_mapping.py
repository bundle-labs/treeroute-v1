"""Skeptic: an independent re-mapping of the official compare outputs onto A's and B's results.json (own code, not
the reconciler's official()/flatten()), plus checks of the reconciler's group claims:
  1. every row of pairs.parquet, importance.parquet (active rows), families.parquet, per_lead.json (W, mean rho,
     stability, nonzero players, item 8) and AW4_main_row.json against A's and B's value at the key the spec names;
  2. duplicate (key) rows in the official parquet files (a later row would silently overwrite an earlier one);
  3. the O-only importance rows: is every one outside J?
  4. item 8: is (all variable-level players) minus (A's/B's J) exactly the variable-level structural zeros, and is
     every structural-zero column exactly 0 on every row of every model's row file?
  5. the AW3 header lists at most 30 structural zeros: which levels have more?
Read-only; writes nothing but stdout."""
import json
import math
import os
import collections

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

SHAP = r"D:\treeroute\analysis\shap_v1"
V = SHAP + r"\verify_v1"
PROBLEMS = ("coral", "defo", "fire", "pm25", "ndvi")
STAT = {"spearman": "spearman_J", "spearman_top20_union": "spearman_top20_union", "kendall_tau_b": "kendall_tau_b",
        "jaccard_top5": "jaccard_top5", "jaccard_top10": "jaccard_top10", "jaccard_top20": "jaccard_top20",
        "rbo_p0.9": "rbo_p090", "rbo_p0.95": "rbo_p095", "tvd": "tv_shares", "tvd_family": "tv_family_shares",
        "sign_agreement_top10": "sign_agreement"}
FAM = {"own history": "own_history", "global indices": "global_indices", "local drivers": "local_drivers",
       "context and calendar": "context_and_calendar", "seasonal normal": "seasonal_normal"}


def load(X):
    with open(os.path.join(V, X, "results.json"), encoding="utf-8") as f:
        return json.load(f)


RES = {"A": load("A"), "B": load("B")}


def num(x):
    if x is None:
        return None
    x = float(x)
    return None if not math.isfinite(x) else x


def close(a, b):
    a, b = num(a) if not isinstance(a, bool) else a, num(b) if not isinstance(b, bool) else b
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    return abs(a - b) <= 1e-12 or abs(a - b) <= 1e-12 * max(abs(a), abs(b))


def get(d, *path):
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return "ABSENT"
        d = d[p]
    return d


tally = collections.Counter()
bad = []


def check(tag, official, X, val):
    if val == "ABSENT":
        tally[(tag, X, "absent")] += 1
        bad.append((tag, X, "absent", official))
        return
    ok = close(official, val)
    tally[(tag, X, "ok" if ok else "DIFF")] += 1
    if not ok:
        bad.append((tag, X, official, val))


def iv_check(tag, X, obj, value, lo=None, hi=None, nf=None, with_ci=True):
    if obj == "ABSENT" or obj is None:
        if obj is None and all(v is None or (isinstance(v, float) and not math.isfinite(v)) for v in (value, lo, hi)):
            tally[(tag, X, "null-both")] += 1
            return
        tally[(tag, X, "absent")] += 1
        bad.append((tag, X, "absent/null", value))
        return
    check(tag + "/value", value, X, obj.get("value"))
    if with_ci:
        check(tag + "/ci_low", lo, X, obj.get("ci_low"))
        check(tag + "/ci_high", hi, X, obj.get("ci_high"))
        o_nf = None if nf is None else int(nf)
        a_nf = obj.get("n_finite")
        ok = (o_nf == a_nf) or (o_nf == 0 and a_nf is None and num(value) is None)
        tally[(tag + "/n_finite", X, "ok" if ok else "DIFF")] += 1
        if not ok:
            bad.append((tag + "/n_finite", X, o_nf, a_nf))


extra_facts = {}
for p in PROBLEMS:
    d = os.path.join(SHAP, "out", p, "lead_0", "compare")
    per = json.load(open(os.path.join(d, "per_lead.json"), encoding="utf-8"))
    imp = pq.read_table(os.path.join(d, "importance.parquet")).to_pandas()
    fam = pq.read_table(os.path.join(d, "families.parquet")).to_pandas()
    pr = pq.read_table(os.path.join(d, "pairs.parquet")).to_pandas()
    mr = json.load(open(os.path.join(d, "AW4_main_row.json"), encoding="utf-8"))
    # 2. duplicates
    dups = {"importance": int(imp.duplicated(["level", "model", "player"]).sum()),
            "families": int(fam.duplicated(["model", "family"]).sum()),
            "pairs": int(pr.duplicated(["level", "model_a", "model_b", "statistic"]).sum()),
            "pairs_order_ok": bool((pr.model_a < pr.model_b).all())}
    print(p, "duplicates:", dups)
    for X, R in RES.items():
        P = R["problems"][p]
        # 1a. pairs
        for r in pr.itertuples():
            obj = get(P, "levels", r.level, "pairs", "%s|%s" % (r.model_a, r.model_b), STAT[r.statistic])
            iv_check("pairs/" + r.statistic, X, obj, r.value, r.ci_low, r.ci_high, r.finite_replicates)
            if r.statistic == "sign_agreement_top10":
                o2 = get(P, "levels", r.level, "pairs", "%s|%s" % (r.model_a, r.model_b), "sign_n_determined")
                check("pairs/sign_n_determined", r.signs_compared, X, o2.get("value") if isinstance(o2, dict) else o2)
        # 1b. importance (active rows) and the O-only rows
        for r in imp.itertuples():
            pl = get(P, "levels", r.level, "models", r.model, "players", r.player)
            if not r.active:
                tally[("imp_inactive_present_in_" + X, "", str(pl != "ABSENT"))] += 1
                continue
            if pl == "ABSENT":
                tally[("imp_active_absent_in_" + X, "", "")] += 1
                bad.append(("imp active absent", X, p, r.level, r.model, r.player))
                continue
            check("imp/I", r.mean_abs, X, pl["I"]["value"])
            check("imp/share", r.share, X, pl["share"]["value"])
            check("imp/signed_mean", r.signed_mean, X, pl["signed_mean"]["value"])
            check("imp/sign_determined", bool(r.sign_determined), X, pl["sign_determined"])
        # 3. J: active players of importance.parquet vs A's J
        for L in ("feature", "variable"):
            Jo = sorted(imp[(imp.level == L) & imp.active].player.unique())
            Ja = get(P, "levels", L, "active_set", "J")
            tally[("J", X, "ok" if Ja == Jo else "DIFF")] += 1
            zo = sorted(per[L]["structural_zero"])
            za = get(P, "levels", L, "active_set", "structural_zeros")
            tally[("structural_zeros", X, "ok" if za == zo else "DIFF")] += 1
        # 1c. families
        for r in fam.itertuples():
            obj = get(P, "levels", "variable", "models", r.model, "family_shares", FAM[r.family])
            if obj is None or obj == "ABSENT":
                tally[("fam_share", X, "null/absent official=%s" % r.share)] += 1
                continue
            check("fam_share", r.share, X, obj.get("value"))
        # 1d. per_lead
        for L in ("feature", "variable"):
            lv = per[L]
            iv_check("W", X, get(P, "levels", L, "per_problem", "kendall_w"), lv["kendall_w_main_set"]["value"],
                     lv["kendall_w_main_set"]["ci"][0], lv["kendall_w_main_set"]["ci"][1],
                     lv["kendall_w_main_set"]["finite_replicates"])
            iv_check("mean_rho", X, get(P, "levels", L, "per_problem", "mean_pairwise_spearman"),
                     lv["mean_pairwise_spearman_main_set"]["value"], lv["mean_pairwise_spearman_main_set"]["ci"][0],
                     lv["mean_pairwise_spearman_main_set"]["ci"][1],
                     lv["mean_pairwise_spearman_main_set"]["finite_replicates"])
            for m, v in lv["stability_under_region_resampling"].items():
                st = get(P, "levels", L, "per_problem", "stability", m)
                check("stability", v, X, st.get("value") if isinstance(st, dict) else st)
            for m, v in lv["nonzero_players"].items():
                nzv = get(P, "levels", L, "models", m, "n_nonzero")
                check("n_nonzero", v, X, nzv.get("value") if isinstance(nzv, dict) else nzv)
        # 1e. item 8
        nz = per["nonzero_forecast_rows"]
        cov = get(P, "nonzero_forecast", "models_covered")
        tally[("item8 models_covered", X, "ok" if sorted(nz) == cov else "DIFF %s vs %s" % (sorted(nz), cov))] += 1
        allv = sorted(imp[imp.level == "variable"].player.unique())
        for m, v in nz.items():
            mm = get(P, "nonzero_forecast", "models", m)
            check("item8 rows", v["rows"], X, mm["rows_used"])
            t10 = mm["top10"]
            tally[("item8 top10 names", X, "ok" if [x[0] for x in t10] == [x[0] for x in v["top10"]] else "DIFF")] += 1
            for (n1, s1), (n2, s2) in zip(v["top10"], t10):
                check("item8 top10 share", s1, X, s2)
            # item 8's J vs all variables minus the structural zeros
            Ja = mm["J"]
            sz = sorted(per["variable"]["structural_zero"])
            tally[("item8 J == allv - structural zeros", X, str(Ja == sorted(set(allv) - set(sz))))] += 1
        # 1f. main row
        M = P["main_row"]
        iv_check("main W", X, M.get("kendall_w", "ABSENT"), mr["kendall_w"]["value"], mr["kendall_w"]["ci"][0],
                 mr["kendall_w"]["ci"][1], mr["kendall_w"]["ci"][2])
        k = "treeroute_vs_same_link_rivals_median_spearman_top20_union"
        if k in mr:
            x = mr[k]
            iv_check("main median rho", X, M["spearman_top20_union_median"], x["value"], x["ci"][0], x["ci"][1],
                     x["ci"][2])
            check("main range min", x["range"][0], X, M["spearman_top20_union_min"]["value"])
            check("main range max", x["range"][1], X, M["spearman_top20_union_max"]["value"])
            x = mr["rbo_vs_consensus_p0.9"]
            iv_check("main rbo", X, M["rbo_p090_vs_consensus"], x["value"], x["ci"][0], x["ci"][1], x["ci"][2])
            tally[("main tr top3", X, "ok" if [a[0] for a in M["treeroute_top3"]] == mr["treeroute_top3"] else
                   "DIFF")] += 1
            tally[("main cons top3", X, "ok" if [a[0] for a in M["consensus_top3"]] == mr["consensus_top3"] else
                   "DIFF")] += 1
            for kk in ("own_history_share_treeroute", "own_history_share_median_rival"):
                x = mr[kk]
                iv_check("main " + kk, X, M.get(kk), x["value"], x["ci"][0], x["ci"][1], x["ci"][2])
        else:
            tally[("main (no rival) keys", X, ",".join(sorted(kk for kk, vv in M.items() if vv is not None and
                                                              not kk.endswith("_why"))))] += 1
    # 4. structural zeros are exactly 0 on every row of every model's file; 5. AW3 truncation
    for L, pref in (("feature", "phi__"), ("variable", "phiv__")):
        zs = per[L]["structural_zero"]
        mx = 0.0
        for m in per["models"]:
            f = os.path.join(SHAP, "out", p, "lead_0", m, "rows.parquet")
            names = pq.read_schema(f).names
            cols = [pref + z for z in zs if pref + z in names]
            if cols:
                t = pq.read_table(f, columns=cols).to_pandas().to_numpy(np.float64)
                mx = max(mx, float(np.abs(t).max()))
        extra_facts[(p, L)] = {"n_structural_zero": len(zs), "max_abs_phi_on_any_row": mx,
                               "AW3_header_truncated_at_30": len(zs) > 30}
print()
for k, v in sorted(tally.items()):
    print("%-60s %s" % (" | ".join(str(x) for x in k), v))
print("bad (first 40):", len(bad))
for b in bad[:40]:
    print("   ", b)
print()
for k, v in extra_facts.items():
    print(k, v)
