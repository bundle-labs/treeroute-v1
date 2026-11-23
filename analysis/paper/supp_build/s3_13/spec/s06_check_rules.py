"""Spec writer's helper (read-only): do the checks of TABLE_SPEC.md section 3 hold on the data?

Usage: py -3.9 -I -B s06_check_rules.py
Tests checks 3.1, 3.3, 3.6, 3.7, 3.9 and 3.10 as the spec words them and prints PASS/FAIL lines only (plus the
values a FAIL needs). Opens the compare files, the rebuild gates.json, the sample register and manifests,
bootstrap_draws.npy (bytes, for its SHA-256) and V\\_lead\\outputs\\bardl_maxima.txt. Writes nothing.
"""
import hashlib
import itertools
import json
import math
import os
import re

import numpy as np
import pandas as pd

SHAP = r"D:\treeroute\analysis\shap_v1"
PROBLEMS = ["pm25", "ndvi", "fire", "defo", "coral"]
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    reg = {}
    with open(os.path.join(SHAP, "SAMPLE_REGISTER.txt"), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                kv = dict(t.split("=", 1) for t in line.split()[1:])
                reg[kv["problem"]] = kv
    for p in PROBLEMS:
        C = os.path.join(SHAP, "out", p, "lead_0", "compare")
        PL = load(os.path.join(C, "per_lead.json"))
        AW = load(os.path.join(C, "AW4_main_row.json"))
        man = load(os.path.join(SHAP, "sample", p, "sample_manifest.json"))
        pairs = pd.read_parquet(os.path.join(C, "pairs.parquet"))
        imp = pd.read_parquet(os.path.join(C, "importance.parquet"))
        fam = pd.read_parquet(os.path.join(C, "families.parquet"))
        # 3.1
        with open(os.path.join(C, "bootstrap_draws.npy"), "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        ok(p + " 3.1", PL["rows"] == 1000 == int(reg[p]["n"]) == man["n"] and PL["draws"] == 2000
           and reg[p]["sample"] == man["sha256"]["sample.parquet"] == PL["sample_sha256"]
           and sha == PL["draws_sha256"] and PL["regions"] == man["regions_in_sample"])
        # 3.3
        models = PL["models"]
        cub = set(tuple(PL["links"][m].split("|")[1:]) for m in models)
        ok(p + " 3.3 c/ub shared", len(cub) == 1, str(cub))
        for L in ("variable", "feature"):
            sub = pairs[pairs.level == L]
            want = {"spearman", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10", "rbo_p0.9",
                    "rbo_p0.95", "tvd", "sign_agreement_top10"}
            if L == "variable":
                want.add("tvd_family")
            if PL[L]["active"] >= 200:
                want.add("jaccard_top20")
            for a, b in itertools.combinations(sorted(models), 2):
                s = sub[(sub.model_a == a) & (sub.model_b == b)]
                ok("%s 3.3 %s %s|%s stats" % (p, L, a, b), set(s.statistic) == want and len(s) == len(want))
                labels = set(s.pair_label)
                ok("%s 3.3 %s %s|%s one label" % (p, L, a, b), len(labels) == 1, str(labels))
                lab = labels.pop()
                same = PL["links"][a] == PL["links"][b]
                base = "same-link" if same else "cross-link (not comparable in scale or rank)"
                dec = [m for m in (a, b) if m in PL["declined_by_guard"]]
                exp = base + ("; raw model, declined by its guard: " + ", ".join(dec) if dec else "")
                ok("%s 3.3 %s %s|%s label" % (p, L, a, b), lab == exp, lab + " vs " + exp)
        # 3.6
        counts = {}
        for v, fn in PL["families"].items():
            counts[fn] = counts.get(fn, 0) + 1
        empty = [f for f in ["own history", "global indices", "local drivers", "context and calendar", "seasonal normal"]
                 if counts.get(f, 0) == 0]
        expect = {"coral": ["own history"], "defo": ["context and calendar"]}.get(p, [])
        ok(p + " 3.6 empty families", empty == expect, str(empty))
        for f in empty:
            ok(p + " 3.6 zero share " + f, (fam[fam.family == f].share == 0.0).all())
        # 3.7
        if p != "fire":
            w = PL["variable"]["kendall_w_main_set"]
            ok(p + " 3.7 W", AW["kendall_w"]["value"] == w["value"] and AW["kendall_w"]["ci"][:2] == w["ci"])
            ok(p + " 3.7 main set", set(AW["models_in_main_set"]) == set(PL["main_set"]))
            rivals = [m for m in AW["models_in_main_set"] if m != "treeroute"]
            vals = []
            for r in rivals:
                a, b = sorted([r, "treeroute"])
                s = pairs[(pairs.level == "variable") & (pairs.model_a == a) & (pairs.model_b == b) &
                          (pairs.statistic == "spearman_top20_union")]
                vals.append(float(s.value.iloc[0]))
            med = AW["treeroute_vs_same_link_rivals_median_spearman_top20_union"]
            ok(p + " 3.7 range", abs(min(vals) - med["range"][0]) <= 1e-12 and abs(max(vals) - med["range"][1]) <= 1e-12)
            ok(p + " 3.7 median rho20", abs(float(np.median(vals)) - med["value"]) <= 1e-12, "%r %r" % (np.median(vals), med["value"]))
            oh = [float(fam[(fam.model == r) & (fam.family == "own history")].share.iloc[0]) for r in rivals]
            ohm = AW["own_history_share_median_rival"]["value"]
            ok(p + " 3.7 median own history", abs(float(np.median(oh)) - ohm) <= 1e-12)
            if p in ("pm25", "defo"):
                lg = float(fam[(fam.model == "rival_lgbm") & (fam.family == "own history")].share.iloc[0])
                ok(p + " 3.7 lgbm is the median", abs(lg - ohm) <= 1e-12)
            if p == "ndvi":
                so = sorted(oh)
                ok(p + " 3.7 mean of two middle", len(so) == 4 and abs((so[1] + so[2]) / 2 - ohm) <= 1e-12)
            tr = imp[(imp.level == "variable") & (imp.model == "treeroute") & imp.active]
            tr = tr.assign(neg=-tr.mean_abs).sort_values(["neg", "player"], kind="mergesort")
            ok(p + " 3.5 top3", tr.player.tolist()[:3] == AW["treeroute_top3"])
        else:
            ok("fire 3.7 lists", AW["models_in_main_set"] == ["treeroute"] and AW["cross_link_models"] ==
               ["rival_lgbm", "rival_lgbm_tweedie", "rival_rf"] and AW["declined_models"] == ["rival_ridge"]
               and math.isnan(AW["kendall_w"]["value"]) and math.isnan(AW["kendall_w"]["ci"][0])
               and math.isnan(AW["kendall_w"]["ci"][1]) and AW["kendall_w"]["ci"][2] == 0)
        # 3.10
        gj = load(os.path.join(SHAP, "rebuild", p, "lead_0", "gates.json"))
        G, R = gj["gates"], gj["result"]
        ok(p + " 3.10 stopped_at", gj["stopped_at"] is None)
        for k, v in G.items():
            if k == "E5_bank_fingerprint":
                ok(p + " 3.10 E5 false", v["pass"] is False)
            else:
                ok(p + " 3.10 " + k, v["pass"] is True)
        ok(p + " 3.10 E3m", ("E3m_recorded_path_map" in G) == bool(G["E3a_inputs_before_read"]["values"]["path_map"]))
        if "E3m_recorded_path_map" in G:
            ok(p + " 3.10 E3m files", all(x["equal"] for x in G["E3m_recorded_path_map"]["values"]["files"]))
        ok(p + " 3.10 E5a", ("E5a_identity_twin" in G) == (R["link"] == "arcsine"))
        ok(p + " 3.10 E7", ("E7_gls_weight_model" in G) == bool(R["weighted"]))
        e4 = G["E4_donor_rows"]["values"]
        ok(p + " 3.10 E4", e4["rows"][0] == e4["rows"][1] and e4["row_key_hash"][0] == e4["row_key_hash"][1])
        ok(p + " 3.10 E9", G["E9_coefficients_reproduce_the_kernel"]["values"]["fits_whose_X_b_differs_from_the_kernel"] == 0)
        meta = load(os.path.join(SHAP, "out", p, "lead_0", "treeroute", "meta.json"))
        arm = "%s_%s_%s" % (R["link"], R["table_kind"], "gls" if R["weighted"] else "unweighted")
        ok(p + " 3.10 arm", meta["arm"] == arm, meta["arm"] + " vs " + arm)
        if p == "ndvi":
            ok("ndvi 3.9 nonzero", PL["variable"]["nonzero_players"]["rival_bardl_h1"] == 3 and
               PL["feature"]["nonzero_players"]["rival_bardl_h1"] == 9)
            b = imp[(imp.level == "variable") & (imp.model == "rival_bardl_h1") & imp.active]
            b = b.assign(neg=-b.mean_abs).sort_values(["neg", "player"], kind="mergesort")
            top5 = b.head(5)
            ok("ndvi 3.9 aet in top5", "aet_total_mm" in top5.player.tolist() and
               float(top5[top5.player == "aet_total_mm"].share.iloc[0]) == 0.0, str(top5.player.tolist()))
            with open(os.path.join(SHAP, "verify_v1", "_lead", "outputs", "bardl_maxima.txt"), encoding="utf-8") as f:
                lines = f.read().split("\n")
            rx = re.compile(r"^\s+(jaccard_top5|jaccard_top10|jaccard_top20|rho20|rbo090|rbo095)\s+spread ([0-9.]+) -> \S+ \(3 sig\. \S+\) at (\w+)/(\w+)/(\S+); values ([0-9.\-]+) / ([0-9.\-]+) / ([0-9.\-]+)$")
            block = []
            for ln in lines[1:]:
                if ln.startswith("=="):
                    break
                m = rx.match(ln)
                if m:
                    block.append(m.groups())
            ok("ndvi 3.9 maxima six", sorted(g[0] for g in block) == sorted(
                ["jaccard_top5", "jaccard_top10", "jaccard_top20", "rho20", "rbo090", "rbo095"]), str(block))
            j5 = [g for g in block if g[0] == "jaccard_top5"][0]
            a, bb = j5[4].split("|")
            s = pairs[(pairs.level == j5[3]) & (pairs.model_a == a) & (pairs.model_b == bb) & (pairs.statistic == "jaccard_top5")]
            ok("ndvi 3.9 base value", abs(float(j5[5]) - float(s.value.iloc[0])) <= 1e-9, "%s %r" % (j5[5], float(s.value.iloc[0])))
            for g in block:
                print("   maxima %-13s %s %s %s -> %s | ex %s / %s" % (g[0], g[3], g[4], g[1], format(float(g[1]), ".2f"), g[5], g[7]))
    bad = [r for r in results if not r[1]]
    print("checks: %d, failed: %d" % (len(results), len(bad)))
    for r in bad:
        print("FAIL", r[0], r[2])


if __name__ == "__main__":
    main()
