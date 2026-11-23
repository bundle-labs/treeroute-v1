#!/usr/bin/env python3
"""reconcile_AB.py -- reconciles result_A.json against result_B.json and the fact sheet (SPEC.json).

POST HOC: every number here was computed after the test labels were opened; nothing here changes a
pre-registered verdict.

Run:  py -3.9 -I D:/treeroute/analysis/paper_posthoc/reconcile_AB.py
Reads: SPEC.json, result_A.json, result_B.json (this folder), and every input file named by A or B
(hashed only, except the light spot checks C1-C3 below).
Writes ONLY D:/treeroute/analysis/paper_posthoc/reconcile_AB.json.

Agreement rule: a numeric leaf agrees when both sides print it at full float precision and
|A-B| <= 1e-12 * max(|A|,|B|) (or both 0), or, when one side printed fewer significant digits,
when |A-B| <= half a unit in the last printed digit of the shorter print. Strings and booleans must be
equal. Leaves that only one side reports are listed as coverage, not as disagreement.
"""
import hashlib
import json
import math
import re
import sys
from decimal import Decimal

D = "D:/treeroute/analysis/paper_posthoc"
OUT = D + "/reconcile_AB.json"

with open(D + "/SPEC.json", encoding="utf-8") as f:
    SPEC = json.load(f)
with open(D + "/result_A.json", encoding="utf-8") as f:
    RA = json.load(f)
with open(D + "/result_B.json", encoding="utf-8") as f:
    RB = json.load(f)
A = RA["items"]
B = RB["results"]
ITEMS = [it["id"] for it in SPEC["items"]]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------------- flatten helpers
def flat(o, p=""):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(flat(v, p + "/" + str(k)))
    elif isinstance(o, list) and o and all(not isinstance(x, (dict, list)) for x in o):
        out[p] = list(o)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out.update(flat(v, p + "[%d]" % i))
    else:
        out[p] = o
    return out


def keyed(lst, keyf):
    d = {}
    for x in lst:
        k = keyf(x)
        assert k not in d, ("duplicate key", k)
        d[k] = x
    return d


def rename(d, mapping):
    return {mapping.get(k, k): v for k, v in d.items()}


def drop(d, keys):
    return {k: v for k, v in d.items() if k not in keys}


COLMAP = {"arm__arcsine_corrector_gls": "ours", "base__predict_zero": "predict_zero",
          "base__donor_median": "donor_median"}


def colname(c):
    if c in COLMAP:
        return COLMAP[c]
    if c.startswith("arm__rival_"):
        return c[len("arm__rival_"):]
    return c


# ----------------------------------------------------------------------------- per-item canonical forms
def years_str(y):
    if isinstance(y, list):
        return "%d-%d" % (min(y), max(y))
    return y


def canon_M34(v, side):
    out = {}
    for run in ["pm25", "ndvi", "fire", "defo"]:
        r = dict(v[run])
        if side == "A":
            pop = r.pop("population")
            r.update({"labelled_rows": pop["labelled_rows"], "saved_rows": pop["saved_rows"],
                      "units": pop["units"], "groups": pop["groups"], "years": pop["years"]})
            r["identity_tolerance"] = r.pop("tolerance_identity")
            r.pop("ndvi_headline_table", None)
        else:
            r["years"] = years_str(r["years"])
        out[run] = r
    return out


def surface_point(s):
    if s is None:
        return None
    if isinstance(s, dict):
        return "level=%r,ratio=%r" % (float(s["level"]), None if s["ratio"] is None else float(s["ratio"]))
    return s


def canon_R12(v, side):
    out = {"band": v["band"]}
    if side == "A":
        out["ordering"] = {str(x["rank"]): {"column": x["column"], "mae": x["mae"]} for x in v["pooled_mae_ascending"]}
        out["contrasts"] = {k: drop(c, ["label"]) for k, c in v["report_only_contrasts"].items()}
        s = v["final_reread_adoption_surface"]
        surf = {}
        for arm in ["log_c_plain_unweighted", "log_c_plain_gls", "log_c_corrector_unweighted",
                    "log_c_corrector_gls", "arcsine_corrector_gls"]:
            pa = s["per_arm"][arm]
            surf[arm] = {"surface_pick_mae": pa["min_over_grid"], "pick_point": pa["argmin_point"],
                         "eligible_in_adoption_json": pa["eligible"]}
        surf["log_c_trees_off_unweighted"] = s["per_arm"]["log_c_trees_off_unweighted"]["at_adopted_point"]
        surf["arcsine_trees_off_unweighted"] = s["per_arm"]["arcsine_trees_off_unweighted"]["at_adopted_point"]
        out["surface"] = surf
        out["jk_log_rows"] = {x["reference"] + "|" + x["arm"]: {"mean": x["mean"], "se": x["se"], "low": x["low"],
                                                                "high": x["high"], "tag_file": x["file_tag"],
                                                                "tag_rederived": x["tag"]}
                              for x in v["final_jackknife_log_rows"]}
    else:
        out["ordering"] = {str(x["rank"]): {"column": x["column"], "mae": x["pooled_mae"]} for x in v["ordering"]}
        out["contrasts"] = {k: drop(c, ["groups"]) for k, c in v["contrasts_report_only"].items()}
        s = v["adoption_surface_reread"]
        surf = {}
        for arm in ["log_c_plain_unweighted", "log_c_plain_gls", "log_c_corrector_unweighted",
                    "log_c_corrector_gls", "arcsine_corrector_gls"]:
            pa = s[arm]
            surf[arm] = {"surface_pick_mae": pa["surface_pick_mae"], "pick_point": surface_point(pa["pick_point"]),
                         "eligible_in_adoption_json": pa["eligible_in_adoption_json"]}
        surf["log_c_trees_off_unweighted"] = s["log_c_trees_off_unweighted"]
        surf["arcsine_trees_off_unweighted"] = s["arcsine_trees_off_unweighted"]["surface_mae"]
        out["surface"] = surf
        out["jk_log_rows"] = {x["reference"] + "|" + x["arm"]: {"mean": x["mean"], "se": x["se"], "low": x["low"],
                                                                "high": x["high"], "tag_file": x["tag"],
                                                                "tag_rederived": x["rederived_tag"]}
                              for x in v["jackknife_csv_log_arm_rows"]}
    return out


def canon_R13(v, side):
    out = {}
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        r = v[run]
        o = {"band": r["band"]}
        o["triples"] = {t["link"] + "|" + t["weighting"]: drop(t, ["link", "weighting"]) for t in r["triples"]}
        if side == "A":
            o["labelled_rows"] = r["population"]["labelled_rows"]
            o["groups"] = r["population"]["groups"]
            o["pairs"] = {x["reference"] + "|" + x["arm"]: {"mean": x["mean"], "se": x["se"], "low": x["low"],
                                                            "high": x["high"], "n_groups": x["n_groups"],
                                                            "tag_rederived": x["tag"], "tag_file": x["file_tag"]}
                          for x in r["placebo_pairs_rederived"]}
        else:
            o["labelled_rows"] = r["n_labelled_rows"]
            o["groups"] = r["n_groups"]
            o["pairs"] = {x["placebo"] + "|" + x["corrector"]: {"mean": x["mean"], "se": x["se"], "low": x["low"],
                                                                "high": x["high"], "n_groups": x["n_groups"],
                                                                "tag_rederived": x["tag"],
                                                                "tag_file": x["jackknife_csv_tag"]}
                          for x in r["placebo_band_pairs_rederived"]}
        out[run] = o
    return out


def canon_R14(v, side):
    return {run: drop(v[run], ["grid_points", "context_centre_unused"]) for run in v}


def canon_R15(v, side):
    out = {}
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        r = v[run]
        o = {}
        for k in ["n_columns", "n_arms", "n_placebos", "n_baselines", "n_selectable", "hit_tolerance", "band",
                  "adopted", "best_selectable", "regret_abs", "regret_rel", "lowest_column_mae"]:
            o[k] = r[k]
        o["eligible"] = sorted(r["eligible"])
        if side == "A":
            o["hit_floor"] = r["measurement_error_floor"]
            o["adopted_mae"] = r["mae_adopted"]
            o["best_selectable_mae"] = r["mae_best"]
            o["lowest_column_overall"] = r["lowest_column_any_kind"]
            o["labelled_rows"] = r["population"]["labelled_rows"]
            o["groups"] = r["population"]["groups"]
            o["table"] = {c: drop(dict(x, kind={"baseline": "base"}.get(x["kind"], x["kind"])), [])
                          for c, x in r["columns"].items()}
            o["contrasts"] = {a: drop(c, ["label"]) for a, c in r["report_only_contrasts_vs_adopted"].items()}
            o["weighting_unw_minus_gls"] = {x["link"] + "_" + x["tool"]: x["unweighted_minus_gls"]
                                            for x in r["factor_weighting"]}
            o["tool_plain_minus_corrector"] = {x["link"] + "_" + x["weighting"]: x["plain_minus_corrector"]
                                               for x in r["factor_tool"]}
            o["link_best"] = {x["link"]: drop(x, ["link"]) for x in r["factor_link"]}
        else:
            o["hit_floor"] = r["hit_floor"]
            o["adopted_mae"] = r["adopted_mae"]
            o["best_selectable_mae"] = r["best_selectable_mae"]
            o["lowest_column_overall"] = r["lowest_column_overall"]
            o["labelled_rows"] = r["n_labelled_rows"]
            o["groups"] = r["n_groups"]
            o["table"] = {x["column"]: drop(x, ["column", "adopted"]) for x in r["table"]}
            o["contrasts"] = {x["arm"]: drop(x, ["arm", "groups"]) for x in r["contrasts_report_only_post_hoc"]}
            o["weighting_unw_minus_gls"] = dict(r["weighting_effect_unw_minus_gls"])
            o["tool_plain_minus_corrector"] = dict(r["tool_effect_plain_minus_corrector"])
            o["link_best"] = dict(r["link_effect_best_per_link"])
        out[run] = o
    return out


def p29_key_A(x):
    return "%s|%s|%s|%s" % (x["who"], x["problem"], x["lead"], "ours" if x["who"] == "own" else x["name"])


def p29_key_B(x):
    who = "own" if x["source"].startswith("own") else ("human" if x["source"].startswith("human") else "common")
    return "%s|%s|%s|%s" % (who, x["problem"], x["lead"], "ours" if who == "own" else x["rival"])


def canon_P29(v, side):
    out = {}
    if side == "A":
        rows = v["rows"]
        out["counts"] = {"rows": v["n_rows"], "own": v["n_own"], "common": v["n_common"], "human": v["n_human"],
                         "changed_under_t": v["n_changed_tag_under_t"],
                         "own_declined": sum(1 for r in rows if r["who"] == "own" and r["tag"] == "declined"),
                         "identical": sum(1 for r in rows if r["tag"] == "identical")}
        out["rows"] = {p29_key_A(r): {"G": r["G"], "band": r["band"], "mean": r["mean"], "se": r["se"],
                                      "low": r["low"], "high": r["high"], "tcrit": r["t_quantile"],
                                      "low_t": r["low_t"], "high_t": r["high_t"], "p_z": r["p_z"], "p_t": r["p_t"],
                                      "tag": r["tag"], "tag_t": r["tag_t"], "changed": r["changes"],
                                      "name_own": r["name"] if r["who"] == "own" else None}
                       for r in rows}
        out["changed"] = sorted(p29_key_A(r) for r in v["changed"])
        out["holm"] = {h["problem"]: {"p_z": h["p_z"], "adj_z": h["holm_adj_p_z"], "survives_z": h["survives_z"],
                                      "p_t": h["p_t"], "adj_t": h["holm_adj_p_t"], "survives_t": h["survives_t"]}
                       for h in v["holm_lead0_own"]}
        out["band_share"] = v["band_share"]
        out["fire_blocked_jackknife"] = drop(v["fire_blocked_jackknife_read"], ["kind"])
    else:
        rows = v["rows"]
        c = v["counts"]
        out["counts"] = {"rows": c["rows"], "own": c["own"], "common": c["common"], "human": c["human"],
                         "changed_under_t": c["changed_under_t"], "own_declined": c["own_declined"],
                         "identical": c["identical"]}
        out["rows"] = {p29_key_B(r): {"G": r["G"], "band": r["band"], "mean": r["mean"], "se": r["se"],
                                      "low": r["low"], "high": r["high"], "tcrit": r["tcrit"],
                                      "low_t": r["low_t"], "high_t": r["high_t"], "p_z": r["p_z"], "p_t": r["p_t"],
                                      "tag": r["tag"], "tag_t": r["tag_t"], "changed": r["changed"],
                                      "name_own": r["name"] if r["source"].startswith("own") else None}
                       for r in rows}
        out["changed"] = sorted(p29_key_B(r) for r in v["changed"])
        hz = {h["problem"]: h for h in v["holm"]["p_z"]}
        ht = {h["problem"]: h for h in v["holm"]["p_t"]}
        out["holm"] = {p: {"p_z": hz[p]["p"], "adj_z": hz[p]["holm_adjusted"], "survives_z": hz[p]["survives_0.05"],
                           "p_t": ht[p]["p"], "adj_t": ht[p]["holm_adjusted"], "survives_t": ht[p]["survives_0.05"]}
                       for p in hz}
        out["band_share"] = v["band_share"]
        out["fire_blocked_jackknife"] = dict(v["fire_blocked_jackknife"])
    return out


def canon_R3b(v, side):
    out = {}
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        r = v[run]
        if side == "A":
            o = {"model": r["model"], "model_mae": r["mae_model"], "candidates": r["candidates"],
                 "best": r["best_baseline"], "best_mae": r["mae_best"], "change_pct": r["change_pct_vs_best"],
                 "labelled_rows": r["population"]["labelled_rows"], "groups": r["population"]["groups"]}
        else:
            o = {"model": r["model"], "model_mae": r["model_mae"], "candidates": r["candidates"],
                 "best": r["best"], "best_mae": r["best_mae"], "change_pct": r["change_pct"],
                 "labelled_rows": r["n_labelled_rows"], "groups": r["n_groups"]}
        if "change_pct_vs_predict_zero" in r:
            o["change_pct_vs_predict_zero"] = r["change_pct_vs_predict_zero"]
        out[run] = o
    return out


STRATUM = {"ALL": "ALL", "ALL rows": "ALL", "severe y>=50": "severe", "severe y >= 50": "severe",
           "ALL labelled": "all", "all labelled": "all", "top 1% y >= q99": "top1", "top 1% (y >= q99)": "top1"}


def canon_strata(st, side):
    out = {}
    for name, s in st.items():
        o = {"n": s["n"], "n_groups": s["n_groups"], "mean_y": s["mean_y"]}
        if "share_of_labelled_pct" in s:
            o["share_pct"] = s["share_of_labelled_pct"]
        o["columns"] = {colname(c) if side == "A" else c: dict(x) for c, x in s["columns"].items()}
        o["contrasts"] = {(colname(c) if side == "A" else c): drop(x, ["label", "groups"])
                          for c, x in s["contrasts"].items()}
        out[STRATUM.get(name, name)] = o
    return out


def canon_RC12(v, side):
    out = {"band": v["band"]}
    e = v["edges_lead0"] if side == "A" else v["edges"]
    out["edges"] = {k: e[k] for k in ["pos_q25", "pos_q50", "pos_q75", "donor_rows"]}
    out["strata"] = canon_strata(v["strata"], side)
    return out


def canon_A1(v, side):
    out = {"band": v["band"], "q99": v["q99"]}
    if side == "A":
        out["q99_strict_gt_rows"] = v["top1_strict_gt_rows"]
        out["ridge_guarded_equals_identity_trees_off_exactly"] = v["ridge_guarded_minus_identity_trees_off_maxabs"] == 0.0
        out["ridge_guarded_max_abs_diff_vs_guess_normal"] = v["ridge_guarded_minus_guess_normal_maxabs"]
    else:
        out["q99_strict_gt_rows"] = v["q99_strict_gt_rows"]
        out["ridge_guarded_equals_identity_trees_off_exactly"] = v["ridge_guarded_column"]["equals_identity_trees_off_exactly"]
        out["ridge_guarded_max_abs_diff_vs_guess_normal"] = v["ridge_guarded_column"]["max_abs_diff_vs_guess_normal"]
    out["strata"] = canon_strata(v["strata"], side)
    return out


def canon_A2(v, side):
    if side == "A":
        s = v["active_y_gt_0"]
        cols = {colname(c): dict(x) for c, x in s["columns"].items()}
        o = {"n": s["n"], "n_groups": s["n_groups"], "mean_y": s["mean_y"], "columns": cols,
             "contrasts": {colname(c): drop(x, ["label"]) for c, x in s["contrasts"].items()},
             "ranking": sorted(cols, key=lambda c: cols[c]["mae"])}
    else:
        o = {"n": v["n"], "n_groups": v["n_groups"], "mean_y": v["mean_y"], "columns": v["columns"],
             "contrasts": {c: drop(x, ["groups"]) for c, x in v["contrasts"].items()}, "ranking": v["ranking"]}
    o["band"] = v["band"]
    return o


CANON = {"M34": canon_M34, "R12": canon_R12, "R13": canon_R13, "R14": canon_R14, "R15": canon_R15,
         "P29": canon_P29, "R3b": canon_R3b, "RC12": canon_RC12, "A1": canon_A1, "A2": canon_A2}


# ----------------------------------------------------------------------------- comparison
def sig_digits(x):
    """Significant digits in Python's shortest repr of float x."""
    s = repr(float(x)).lower()
    if s in ("nan", "inf", "-inf"):
        return 17
    mant = s.split("e")[0].lstrip("-").replace(".", "").lstrip("0")
    return max(len(mant.rstrip("0")) if "e" in s or "." in s else len(mant), 1)


def num_agree(a, b):
    """Return (agree, rel_diff, mode)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b, None, "bool"
    if isinstance(a, int) and isinstance(b, int):
        return a == b, (0.0 if a == b else float("inf")), "int"
    a = float(a)
    b = float(b)
    if a == b:
        return True, 0.0, "exact"
    if math.isnan(a) or math.isnan(b):
        return False, None, "nan"
    m = max(abs(a), abs(b))
    rel = abs(a - b) / m
    pa, pb = sig_digits(a), sig_digits(b)
    p = min(pa, pb)
    if p >= 15:
        return rel <= 1e-12, rel, "full"
    short = a if pa <= pb else b
    e = math.floor(math.log10(abs(short))) if short != 0 else 0
    tol = 0.5 * 10 ** (e - p + 1) * (1 + 1e-9)
    return abs(a - b) <= tol, rel, "printed%d" % p


def compare(ca, cb):
    fa, fb = flat(ca), flat(cb)
    common = sorted(set(fa) & set(fb))
    only_a = sorted(set(fa) - set(fb))
    only_b = sorted(set(fb) - set(fa))
    disagree = []
    n_num = n_exact = n_printed = n_int = 0
    max_rel_full = 0.0
    for k in common:
        a, b = fa[k], fb[k]
        if a is None or b is None:
            if not (a is None and b is None):
                disagree.append({"leaf": k, "A": a, "B": b, "why": "null on one side"})
            continue
        if isinstance(a, list) or isinstance(b, list):
            if a != b:
                disagree.append({"leaf": k, "A": a, "B": b, "why": "list differs"})
            continue
        if isinstance(a, str) or isinstance(b, str):
            if str(a) != str(b):
                disagree.append({"leaf": k, "A": a, "B": b, "why": "string differs"})
            continue
        ok, rel, mode = num_agree(a, b)
        if mode not in ("bool",):
            n_num += 1
            if mode == "exact":
                n_exact += 1
            if mode == "int":
                n_int += 1
            if mode.startswith("printed"):
                n_printed += 1
            if mode == "full" and rel is not None:
                max_rel_full = max(max_rel_full, rel)
        if not ok:
            disagree.append({"leaf": k, "A": a, "B": b, "why": "numeric " + mode, "rel": rel})
    return {"n_common_leaves": len(common), "n_numeric": n_num, "n_int": n_int, "n_float_bit_identical": n_exact,
            "n_compared_at_printed_precision": n_printed, "max_rel_diff_full_precision": max_rel_full,
            "n_disagree": len(disagree), "disagreements": disagree,
            "only_in_A": only_a, "only_in_B": only_b}


# ----------------------------------------------------------------------------- fact-sheet comparison
def dec_tol(stated):
    """Half a unit in the last printed digit of a stated value such as '0.004385', '-4.19e-05', '1.20'."""
    s = stated.strip().lstrip("+")
    d = Decimal(s)
    return float(Decimal(1).scaleb(d.as_tuple().exponent)) / 2.0


def fs_num(label, stated, value):
    tol = dec_tol(stated)
    ok = abs(float(value) - float(Decimal(stated.lstrip("+")))) <= tol * (1 + 1e-9)
    return {"label": label, "stated": stated, "agreed": value, "status": "MATCHES" if ok else "DIFFERS"}


def fs_exact(label, stated, value, rtol=1e-12):
    s = float(stated)
    ok = (s == value) or abs(s - value) <= rtol * max(abs(s), abs(value))
    return {"label": label, "stated": stated, "agreed": value, "status": "MATCHES" if ok else "DIFFERS"}


def fs_claim(label, stated, ok, detail):
    return {"label": label, "stated": stated, "agreed": detail, "status": "MATCHES" if ok else "DIFFERS"}


def fs_note(label, stated, ok, detail):
    """Wording notes: the numbers match but a symbol or phrase is not literally true (not a numeric DIFFERS)."""
    return {"label": label, "stated": stated, "agreed": detail, "status": "MATCHES" if ok else "WORDING"}


def fact_sheet(sc):
    fs = {}
    # ---------------- M34
    m = A["M34"]["values"]
    L = []
    for run, s6 in [("pm25", "4.03161"), ("ndvi", "0.0394141"), ("defo", "0.00840486")]:
        L.append(fs_num(run + " MAE_TO (6 sig)", s6, m[run]["MAE_TO"]))
        L.append(fs_num(run + " MAE_GN (6 sig)", s6, m[run]["MAE_GN"]))
    L.append(fs_num("ndvi TO anomaly R2", "1.45e-09", m["ndvi"]["anomaly_r2_TO"]))
    for run, to, gn in [("pm25", "4.031610558456933", "4.031610558674801"),
                        ("ndvi", "0.039414114188559106", "0.03941411443328163"),
                        ("fire", "0.006258758011328549", "0.006258757880478231"),
                        ("defo", "0.008404857347564031", "0.008404857347226244")]:
        L.append(fs_exact(run + " MAE_TO (frozen score_pooled)", to, m[run]["MAE_TO"]))
        L.append(fs_exact(run + " MAE_GN (frozen score_pooled)", gn, m[run]["MAE_GN"]))
    for run, s in zip(["pm25", "ndvi", "fire", "defo"], ["5.16e-11", "1.45e-09", "5.52e-09", "2.02e-10"]):
        L.append(fs_num(run + " TO anomaly R2", s, m[run]["anomaly_r2_TO"]))
    for run, s in zip(["pm25", "ndvi", "fire", "defo"], ["4.1e-09", "1.76e-07", "8.09e-07", "4.76e-09"]):
        L.append(fs_num(run + " maxdev (probe)", s, m[run]["maxdev_all_saved_rows"]))
    L.append(fs_claim("GN == clip(normal) exactly in all four", "true",
                      all(m[r]["GN_equals_clip_normal_exactly"] for r in ["pm25", "ndvi", "fire", "defo"]), "true in all four"))
    L.append(fs_num("fire MAE_TO (added, 6 sig)", "0.00625876", m["fire"]["MAE_TO"]))
    L.append(fs_num("fire MAE_GN (added, 6 sig)", "0.00625876", m["fire"]["MAE_GN"]))
    six = all(m[r]["MAE_TO_6sig"] == m[r]["MAE_GN_6sig"] for r in ["pm25", "ndvi", "fire", "defo"])
    L.append(fs_claim("'equal to every printed digit' (6 sig) in all four", "true", six,
                      {r: (m[r]["MAE_TO_6sig"], m[r]["MAE_GN_6sig"]) for r in ["pm25", "ndvi", "fire", "defo"]}))
    maxrel = max(abs(m[r]["rel_diff"]) for r in ["pm25", "ndvi", "fire", "defo"])
    L.append(fs_claim("proposed wording 'equal within 1e-8 relative' (all four runs)", "max |rel| <= 1e-8",
                      maxrel <= 1e-8, "max |rel| = %.4g (fire); pm25 %.3g, ndvi %.3g, defo %.3g" % (
                          maxrel, m["pm25"]["rel_diff"], m["ndvi"]["rel_diff"], m["defo"]["rel_diff"])))
    L.append(fs_claim("maxdev within the run's identity tolerance (R16/R36)", "true",
                      all(m[r]["maxdev_within_tolerance"] for r in ["pm25", "ndvi", "fire", "defo"]),
                      {r: m[r]["maxdev_over_tolerance"] for r in ["pm25", "ndvi", "fire", "defo"]}))
    fs["M34"] = L
    # ---------------- R12
    r = A["R12"]["values"]
    o = {x["column"]: x["mae"] for x in r["pooled_mae_ascending"]}
    L = []
    for col, s in [("arm__log_c_trees_off_unweighted", "0.004281"), ("base__predict_zero", "0.004284"),
                   ("arm__arcsine_corrector_gls", "0.004385"), ("arm__arcsine_trees_off_unweighted", "0.004428"),
                   ("arm__identity_trees_off_unweighted", "0.006259")]:
        L.append(fs_num(col, s, o[col]))
    logs = [o[c] for c in ["arm__log_c_plain_unweighted", "arm__log_c_plain_gls", "arm__log_c_corrector_unweighted",
                           "arm__log_c_corrector_gls"]]
    L.append(fs_num("log tree arms min", "0.004296", min(logs)))
    L.append(fs_num("log tree arms max", "0.004322", max(logs)))
    order = [x["column"] for x in r["pooled_mae_ascending"]]
    exp = ["arm__log_c_trees_off_unweighted", "base__predict_zero"]
    ok = order[:2] == exp and set(order[2:6]) == {"arm__log_c_plain_unweighted", "arm__log_c_plain_gls",
                                                  "arm__log_c_corrector_unweighted", "arm__log_c_corrector_gls"} \
        and order[6:8] == ["arm__arcsine_corrector_gls", "arm__arcsine_trees_off_unweighted"] \
        and o["arm__arcsine_trees_off_unweighted"] < o["arm__identity_trees_off_unweighted"]
    L.append(fs_claim("ordering logTO < PZ < log arms < adopted < arcsine TO < identity normal", "as stated", ok, order))
    for col, s in [("arm__log_c_trees_off_unweighted", "0.004281302312816825"), ("base__predict_zero", "0.004284114619241937"),
                   ("arm__log_c_corrector_gls", "0.0042957948726572255"), ("arm__log_c_plain_gls", "0.004296987722157366"),
                   ("arm__log_c_corrector_unweighted", "0.004320857403502066"),
                   ("arm__log_c_plain_unweighted", "0.004322425347543649"),
                   ("arm__arcsine_corrector_gls", "0.004385064558301006"),
                   ("arm__arcsine_trees_off_unweighted", "0.00442826356638935"),
                   ("arm__identity_trees_off_unweighted", "0.006258758011328549"),
                   ("base__guess_normal", "0.006258757880478231")]:
        L.append(fs_exact(col + " (frozen score_pooled)", s, o[col]))
    jk = {x["arm"] + "|" + x["reference"]: x for x in r["final_jackknife_log_rows"]}
    a = jk["arm__log_c_plain_unweighted|arm__log_c_trees_off_unweighted"]
    L += [fs_num("jk log plain unw mean", "-4.19e-05", a["mean"]), fs_num("jk log plain unw low", "-6.88e-05", a["low"]),
          fs_num("jk log plain unw high", "-1.50e-05", a["high"]),
          fs_claim("jk log plain unw tag", "hurts", a["file_tag"] == "hurts" and a["tag"] == "hurts", a["tag"])]
    a = jk["arm__log_c_corrector_unweighted|arm__log_c_trees_off_unweighted"]
    L += [fs_num("jk log corrector unw mean", "-4.03e-05", a["mean"]), fs_num("jk log corrector unw low", "-6.66e-05", a["low"]),
          fs_num("jk log corrector unw high", "-1.40e-05", a["high"]),
          fs_claim("jk log corrector unw tag", "hurts", a["file_tag"] == "hurts" and a["tag"] == "hurts", a["tag"])]
    g = [jk["arm__log_c_plain_gls|arm__log_c_trees_off_unweighted"], jk["arm__log_c_corrector_gls|arm__log_c_trees_off_unweighted"]]
    L.append(fs_claim("jk log GLS arms tag", "cannot_tell", all(x["tag"] == "cannot_tell" == x["file_tag"] for x in g),
                      [x["tag"] for x in g]))
    L.append(fs_claim("new report-only contrasts (adopted vs log TO, vs PZ)", "not in fact sheet yet", True,
                      {k: (c["mean"], c["low"], c["high"], c["tag"]) for k, c in r["report_only_contrasts"].items()}))
    fs["R12"] = L
    # ---------------- R13
    r = A["R13"]["values"]
    L = []
    adopted = {"pm25": "log_c|unweighted", "ndvi": "identity|unweighted", "fire": "arcsine|gls",
               "defo": "log_c|unweighted", "coral": "arcsine|gls"}
    prov = {"fire": ("0.004385", "0.004383", "0.004386"), "defo": ("0.0054158", "0.0054195", "0.0054164"),
            "pm25": ("3.58809", "3.59157", "3.59645"), "ndvi": ("0.0314975", "0.0316536", "0.0314606"),
            "coral": ("6.698", "6.732", "6.736")}
    froz = {"fire": ("0.004385064558", "0.004383043171", "0.004385670290"),
            "defo": ("0.005415798422", "0.005419502142", "0.005416406367"),
            "pm25": ("3.588091134", "3.591572881", "3.596454184"),
            "ndvi": ("0.03149747357", "0.03165363992", "0.03146059686"),
            "coral": ("6.697989245", "6.731545728", "6.735936796")}
    for run in ["fire", "defo", "pm25", "ndvi", "coral"]:
        t = {x["link"] + "|" + x["weighting"]: x for x in r[run]["triples"]}[adopted[run]]
        for i, k in enumerate(["corrector", "placebo", "plain"]):
            L.append(fs_num("%s %s %s (provisional)" % (run, adopted[run], k), prov[run][i], t[k]))
            L.append(fs_num("%s %s %s (frozen, 10 sig)" % (run, adopted[run], k), froz[run][i], t[k]))
    tags = {}
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        for x in r[run]["placebo_pairs_rederived"]:
            tags[run + ":" + x["arm"]] = x["tag"]
    exc = {k: v for k, v in tags.items() if v != "does_not_help_equivalent"}
    expected = {"defo:arm__identity_corrector_unweighted": "cannot_tell",
                "fire:arm__identity_corrector_unweighted": "hurts", "fire:arm__identity_corrector_gls": "hurts"}
    L.append(fs_claim("every placebo pair equivalent except defo identity unw (cannot_tell), fire identity x2 (hurts)",
                      "as stated", exc == expected, {"n_pairs": len(tags), "exceptions": exc}))
    fs["R13"] = L
    # ---------------- R14
    r = A["R14"]["values"]
    L = []
    for run, at, ac in [("pm25", "15", "15"), ("ndvi", "0.5", "0.03125"), ("fire", "50", "50"), ("coral", "50", "50")]:
        L.append(fs_exact(run + " a_tree", at, r[run]["a_tree"], 0))
        L.append(fs_exact(run + " a_ctx", ac, r[run]["a_ctx"], 0))
    L.append(fs_exact("defo lambda", "10", r["defo"]["lambda"], 0))
    for run, c in [("pm25", [0.5, 0.25]), ("ndvi", [0.5, 0.25]), ("fire", [0.5, 0.25]), ("defo", [100.0]), ("coral", [0.5, 0.25])]:
        L.append(fs_claim(run + " derived centre", str(c), r[run]["centre"] == c, r[run]["centre"]))
    fs["R14"] = L
    # ---------------- R15
    r = A["R15"]["values"]
    col = lambda run, c: r[run]["columns"][c]["mae"]
    L = []
    p = r["pm25"]
    L += [fs_num("pm25 best log corrector GLS", "3.5875", p["mae_best"]),
          fs_claim("pm25 best arm", "arm__log_c_corrector_gls", p["best_selectable"] == "arm__log_c_corrector_gls", p["best_selectable"]),
          fs_num("pm25 adopted log corrector unw", "3.5881", p["mae_adopted"]),
          fs_num("pm25 regret", "0.0006", p["regret_abs"]),
          fs_num("pm25 regret (score_pooled line)", "0.00061", p["regret_abs"]),
          fs_num("pm25 best (score_pooled line, 10 dp)", "3.5874804069", p["mae_best"]),
          fs_num("pm25 adopted (score_pooled line, 10 dp)", "3.5880911341", p["mae_adopted"]),
          fs_num("pm25 plain unw", "3.5965", col("pm25", "arm__log_c_plain_unweighted")),
          fs_num("pm25 corrector unw", "3.5881", col("pm25", "arm__log_c_corrector_unweighted"))]
    ids = [col("pm25", c) for c in r["pm25"]["columns"] if c.startswith("arm__identity") and "trees_off" not in c]
    L += [fs_num("pm25 identity arms min", "3.724", min(ids)), fs_num("pm25 identity arms max", "3.778", max(ids)),
          fs_num("pm25 log trees-off", "3.853", col("pm25", "arm__log_c_trees_off_unweighted"))]
    n = r["ndvi"]
    L += [fs_num("ndvi adopted identity plain unw", "0.03146", n["mae_adopted"]),
          fs_claim("ndvi adopted is best (regret 0)", "regret 0", n["regret_abs"] == 0.0, n["regret_abs"])]
    oth = [col("ndvi", c) for c in n["columns"] if n["columns"][c]["selectable"] and c != n["adopted"]]
    L += [fs_num("ndvi other arms min", "0.03148", min(oth)), fs_num("ndvi other arms max", "0.03151", max(oth))]
    f = r["fire"]
    logs = [col("fire", c) for c in f["columns"] if c.startswith("arm__log_c") and "trees_off" not in c]
    idf = [col("fire", c) for c in f["columns"] if c.startswith("arm__identity") and "trees_off" not in c]
    L += [fs_num("fire best log corrector GLS", "0.004296", f["mae_best"]),
          fs_num("fire adopted", "0.004385", f["mae_adopted"]),
          fs_num("fire regret rel % (fact sheet)", "2.1", 100 * f["regret_rel"]),
          fs_num("fire regret rel % (score_pooled line)", "2.08", 100 * f["regret_rel"]),
          fs_claim("fire all four log arms beat adopted", "true", all(x < f["mae_adopted"] for x in logs), logs),
          fs_num("fire log arms min", "0.004296", min(logs)), fs_num("fire log arms max", "0.004322", max(logs)),
          fs_claim("fire log trees-off beats them all", "true",
                   col("fire", "arm__log_c_trees_off_unweighted") < min(logs) and f["lowest_column_any_kind"] == "arm__log_c_trees_off_unweighted",
                   col("fire", "arm__log_c_trees_off_unweighted")),
          fs_num("fire log trees-off", "0.004281", col("fire", "arm__log_c_trees_off_unweighted")),
          fs_num("fire identity arms min", "0.00648", min(idf)), fs_num("fire identity arms max", "0.00669", max(idf)),
          fs_claim("fire identity arms > identity normal", "true",
                   min(idf) > col("fire", "arm__identity_trees_off_unweighted"), col("fire", "arm__identity_trees_off_unweighted")),
          fs_num("fire identity normal", "0.006259", col("fire", "arm__identity_trees_off_unweighted"))]
    d = r["defo"]
    ars = [col("defo", c) for c in d["columns"] if c.startswith("arm__arcsine") and "trees_off" not in c]
    idd = [col("defo", c) for c in d["columns"] if c.startswith("arm__identity") and "trees_off" not in c]
    L += [fs_num("defo adopted", "0.0054158", d["mae_adopted"]),
          fs_num("defo log plain", "0.0054164", col("defo", "arm__log_c_plain_unweighted")),
          fs_claim("defo regret 0", "0", d["regret_abs"] == 0.0, d["regret_abs"]),
          fs_note("defo 'adopted = log plain' (wording)", "equal",
                   d["mae_adopted"] == col("defo", "arm__log_c_plain_unweighted"),
                   "adopted %.10f < log plain %.10f (diff %.3g); '=' is not literal" % (
                       d["mae_adopted"], col("defo", "arm__log_c_plain_unweighted"),
                       col("defo", "arm__log_c_plain_unweighted") - d["mae_adopted"])),
          fs_num("defo arcsine arms min", "0.00573", min(ars)), fs_num("defo arcsine arms max", "0.00573", max(ars)),
          fs_num("defo identity arms min", "0.00791", min(idd)), fs_num("defo identity arms max", "0.00797", max(idd)),
          fs_num("defo predict-zero", "0.00612", col("defo", "base__predict_zero")),
          fs_claim("defo identity arms > PZ", "true", min(idd) > col("defo", "base__predict_zero"), min(idd))]
    c = r["coral"]
    unw = [col("coral", k) for k in c["columns"] if (k.startswith("arm__arcsine") or k.startswith("arm__log_c"))
           and k.endswith("_unweighted") and "trees_off" not in k]
    L += [fs_claim("coral every unweighted arcsine/log arm beats adopted", "true", all(x < c["mae_adopted"] for x in unw), unw),
          fs_num("coral unweighted arcsine/log min", "6.147", min(unw)), fs_num("coral unweighted arcsine/log max", "6.376", max(unw)),
          fs_num("coral adopted", "6.698", c["mae_adopted"]),
          fs_claim("coral best arm", "arm__arcsine_corrector_unweighted", c["best_selectable"] == "arm__arcsine_corrector_unweighted", c["best_selectable"]),
          fs_num("coral best", "6.147", c["mae_best"]),
          fs_num("coral regret", "0.55", c["regret_abs"]), fs_num("coral regret (score_pooled line)", "0.5505", c["regret_abs"]),
          fs_num("coral regret rel % (fact sheet)", "9.0", 100 * c["regret_rel"]),
          fs_num("coral regret rel % (score_pooled line)", "8.95", 100 * c["regret_rel"]),
          fs_num("coral best (score_pooled line, 10 dp)", "6.1474857630", c["mae_best"]),
          fs_num("coral adopted (score_pooled line, 10 dp)", "6.6979892451", c["mae_adopted"]),
          fs_num("fire best (score_pooled line)", "0.0042957949", f["mae_best"]),
          fs_num("fire adopted (score_pooled line)", "0.0043850646", f["mae_adopted"])]
    fs["R15"] = L
    # ---------------- P29
    r = A["P29"]["values"]
    ch = {x["problem"] + "|" + str(x["lead"]) + "|" + x["who"]: x for x in r["changed"]}
    fz = ch["fire|0|own"]
    cr = ch["coral|183|human"]
    hz = {h["problem"]: h for h in r["holm_lead0_own"]}
    L = [fs_num("fire t39", "2.023", fz["t_quantile"]), fs_num("fire t lower bound", "-1.2e-06", fz["low_t"]),
         fs_num("fire p_t", "0.056", fz["p_t"]), fs_num("fire z lower bound", "+1.46e-07", fz["low"]),
         fs_num("fire p_z", "0.049", fz["p_z"]), fs_num("fire p_z (probe)", "0.04921", fz["p_z"]),
         fs_num("fire p_t (probe)", "0.05635", fz["p_t"]),
         fs_claim("fire HELPS -> CANNOT TELL", "helps -> cannot_tell", (fz["tag"], fz["tag_t"]) == ("helps", "cannot_tell"),
                  (fz["tag"], fz["tag_t"])),
         fs_claim("coral CRW 183 d, 32 groups", "crw_dhw, G 32", cr["name"] == "crw_dhw" and cr["G"] == 32, (cr["name"], cr["G"])),
         fs_num("coral CRW t31 low", "-0.073", cr["low_t"]), fs_num("coral CRW t31 high", "3.773", cr["high_t"]),
         fs_num("coral CRW p_z (probe)", "0.04976", cr["p_z"]), fs_num("coral CRW p_t (probe)", "0.05879", cr["p_t"]),
         fs_claim("coral CRW BEATS -> CANNOT TELL", "helps -> cannot_tell", (cr["tag"], cr["tag_t"]) == ("helps", "cannot_tell"),
                  (cr["tag"], cr["tag_t"])),
         fs_claim("every other deciding verdict unchanged (exactly 2 change)", "2", r["n_changed_tag_under_t"] == 2,
                  r["n_changed_tag_under_t"]),
         fs_claim("Holm z: all five survive, fire last", "all survive", all(h["survives_z"] for h in hz.values())
                  and max(hz, key=lambda k: hz[k]["p_z"]) == "fire", {k: h["holm_adj_p_z"] for k, h in hz.items()}),
         fs_claim("Holm t: fire fails, others survive", "fire fails",
                  (not hz["fire"]["survives_t"]) and all(hz[k]["survives_t"] for k in hz if k != "fire"),
                  {k: h["holm_adj_p_t"] for k, h in hz.items()})]
    for run, s2, s4 in [("pm25", "1.20", "1.1993"), ("ndvi", "1.52", "1.5159"), ("fire", "0.31", "0.3064"),
                        ("defo", "1.93", "1.9328"), ("coral", "11.06", "11.0623")]:
        L.append(fs_num(run + " band share %", s2, r["band_share"][run]["band_share_pct"]))
        L.append(fs_num(run + " band share % (probe)", s4, r["band_share"][run]["band_share_pct"]))
    L.append(fs_claim("'About 80 verdicts'", "about 80", abs(r["n_rows"] - 80) <= 1,
                      "exactly %d deciding rows (14 own + 53 common + 12 human); say 79" % r["n_rows"]))
    L.append(fs_exact("count of deciding rows (probe)", "79", r["n_rows"], 0))
    fb = r["fire_blocked_jackknife_read"]
    L += [fs_num("fire blocked jk mean", "4.078e-05", fb["mean"]), fs_num("fire blocked jk se", "2.187e-05", fb["se"]),
          fs_num("fire blocked jk low", "-2.08e-06", fb["low"]), fs_num("fire blocked jk high", "8.37e-05", fb["high"]),
          fs_exact("fire blocked jk blocks", "39", fb["n_blocks"], 0)]
    fs["P29"] = L
    # ---------------- R3b
    r = A["R3b"]["values"]
    L = [fs_num("fire model", "0.004385", r["fire"]["mae_model"]), fs_num("fire log TO", "0.004281", r["fire"]["mae_best"]),
         fs_claim("fire best naive is log trees-off", "arm__log_c_trees_off_unweighted",
                  r["fire"]["best_baseline"] == "arm__log_c_trees_off_unweighted", r["fire"]["best_baseline"]),
         fs_num("fire PZ", "0.004284", r["fire"]["candidates"]["base__predict_zero"]),
         fs_num("fire change % vs best", "+2.4", r["fire"]["change_pct_vs_best"]),
         fs_num("fire change % vs PZ", "+2.4", r["fire"]["change_pct_vs_predict_zero"]),
         fs_num("fire change % vs best (expected)", "+2.424", r["fire"]["change_pct_vs_best"]),
         fs_num("fire change % vs PZ (expected)", "+2.356", r["fire"]["change_pct_vs_predict_zero"])]
    for run, mm, bb, bn, pc, pc2 in [("pm25", "3.588", "3.853", "arm__log_c_trees_off_unweighted", "-6.9", "-6.88"),
                                      ("ndvi", "0.03146", "0.03934", "base__last5_normal", "-20.0", "-20.02"),
                                      ("defo", "0.005416", "0.005715", "arm__log_c_trees_off_unweighted", "-5.2", "-5.23"),
                                      ("coral", "6.698", "8.100", "base__predict_zero", "-17.3", "-17.31")]:
        L += [fs_num(run + " model", mm, r[run]["mae_model"]), fs_num(run + " best naive", bb, r[run]["mae_best"]),
              fs_claim(run + " best naive column", bn, r[run]["best_baseline"] == bn, r[run]["best_baseline"]),
              fs_num(run + " change %", pc, r[run]["change_pct_vs_best"]),
              fs_num(run + " change % (expected)", pc2, r[run]["change_pct_vs_best"])]
    fs["R3b"] = L
    # ---------------- RC12
    s = A["RC12"]["values"]["strata"]
    g = lambda st, c: s[st]["columns"][c]["mae"]
    O, H = "arm__arcsine_corrector_gls", "arm__rival_hgb_l1"
    L = [fs_num("B0 ours (notes)", "1.39", g("B0 zero", O)), fs_num("B0 hgb_l1 (notes)", "2.12", g("B0 zero", H)),
         fs_num("severe hgb_l1 (notes)", "38.7", g("severe y>=50", H)), fs_num("severe ours (notes)", "53.1", g("severe y>=50", O))]
    bleached = ["B1 (0, q25]", "B2 (q25, q50]", "B3 (q50, q75]", "B4 (q75, max]", "severe y>=50"]
    l1wins = {b: g(b, H) < g(b, O) for b in bleached}
    L.append(fs_claim("'L1 wins on every bleached stratum'", "true on every bleached stratum", all(l1wins.values()),
                      {b: "hgb_l1 lower" if w else "ours lower" for b, w in l1wins.items()}))
    for st, so, sh in [("B0 zero", "1.393", "2.116"), ("B1 (0, q25]", "2.248", "2.489"), ("B2 (q25, q50]", "4.571", "5.769"),
                       ("B3 (q50, q75]", "8.396", "9.469"), ("B4 (q75, max]", "41.052", "31.151"),
                       ("severe y>=50", "53.125", "38.660")]:
        L.append(fs_num(st + " ours (probe)", so, g(st, O)))
        L.append(fs_num(st + " hgb_l1 (probe)", sh, g(st, H)))
    allc = s["ALL"]["contrasts"][H]
    L += [fs_num("final ALL hgb_l1", "6.356", g("ALL", H)), fs_num("final ALL ours", "6.698", g("ALL", O)),
          fs_num("final ALL d", "-2.30", allc["mean"]), fs_num("final ALL low", "-4.21", allc["low"]),
          fs_num("final ALL high", "-0.39", allc["high"])]
    cut = sc["RC12_probe_cuts_single_implementation"]["cuts"]["(0,10]"]
    for lab, stv, val in [("probe cut (0,10] ours (single implementation C, not A/B-reconciled)", "3.71", cut["ours"]),
                          ("probe cut (0,10] hgb_l1 (single implementation C, not A/B-reconciled)", "4.41", cut["hgb_l1"])]:
        x = fs_num(lab, stv, val)
        x["status"] += " (C only)"
        L.append(x)
    fs["RC12"] = L
    # ---------------- A1
    s = A["A1"]["values"]["strata"]
    O, T = "arm__arcsine_corrector_gls", "arm__rival_lgbm_tweedie"
    yp, t1, z0 = s["y > 0"], s["top 1% y >= q99"], s["y == 0"]
    c = yp["contrasts"][T]
    L = [fs_exact("y>0 rows", "1759", yp["n"], 0), fs_exact("y>0 groups", "33", yp["n_groups"], 0),
         fs_num("y>0 ours", "0.191", yp["columns"][O]["mae"]), fs_num("y>0 Tweedie", "0.201", yp["columns"][T]["mae"]),
         fs_num("y>0 d", "+0.0047", c["mean"]), fs_num("y>0 low", "+0.0024", c["low"]), fs_num("y>0 high", "+0.0071", c["high"]),
         fs_exact("y>0 groups ours better", "25", c["groups_ours_better"], 0),
         fs_num("y>0 ours (probe)", "0.191107", yp["columns"][O]["mae"]), fs_num("y>0 Tweedie (probe)", "0.200700", yp["columns"][T]["mae"]),
         fs_num("y>0 d (probe)", "0.0047162", c["mean"]), fs_num("y>0 low (probe)", "0.0023708", c["low"]),
         fs_num("y>0 high (probe)", "0.0070615", c["high"]),
         fs_exact("top1% rows", "949", t1["n"], 0), fs_exact("top1% groups (probe)", "31", t1["n_groups"], 0),
         fs_num("top1% ours", "0.308", t1["columns"][O]["mae"]), fs_num("top1% Tweedie", "0.335", t1["columns"][T]["mae"]),
         fs_num("top1% ours (probe)", "0.3082", t1["columns"][O]["mae"]), fs_num("top1% Tweedie (probe)", "0.3350", t1["columns"][T]["mae"]),
         fs_num("top1% mean pred ours", "0.098", t1["columns"][O]["mean_pred"]),
         fs_num("top1% mean pred Tweedie", "0.062", t1["columns"][T]["mean_pred"]),
         fs_num("top1% mean y", "0.391", t1["mean_y"]), fs_num("top1% mean y (probe)", "0.3913", t1["mean_y"]),
         fs_exact("top1% strict > rows (probe)", "938", A["A1"]["values"]["top1_strict_gt_rows"], 0),
         fs_num("q99 (6 dp)", "0.102941", A["A1"]["values"]["q99"]),
         fs_exact("zero rows", "92943", z0["n"], 0), fs_num("zero-row share %", "98.1", z0["share_of_labelled_pct"]),
         fs_num("zero-row share % (probe)", "98.14", z0["share_of_labelled_pct"]),
         fs_num("zero rows mean pred ours", "0.00085", z0["columns"][O]["mean_pred"]),
         fs_num("zero rows mean pred Tweedie", "0.00032", z0["columns"][T]["mean_pred"]),
         fs_num("zero rows mean pred ours (probe)", "0.000851", z0["columns"][O]["mean_pred"]),
         fs_num("zero rows mean pred Tweedie (probe)", "0.000321", z0["columns"][T]["mean_pred"]),
         fs_note("spec wording: Ridge guarded column 'is the normal'", "guarded == guess-normal",
                  A["A1"]["values"]["ridge_guarded_minus_guess_normal_maxabs"] == 0.0,
                  "guarded == arm__identity_trees_off_unweighted exactly; differs from base__guess_normal by up to %.3g" %
                  A["A1"]["values"]["ridge_guarded_minus_guess_normal_maxabs"])]
    fs["A1"] = L
    # ---------------- A2
    s = A["A2"]["values"]["active_y_gt_0"]
    cols, cons = s["columns"], s["contrasts"]
    L = [fs_exact("visits", "1024", s["n"], 0), fs_exact("groups", "36", s["n_groups"], 0),
         fs_num("ours", "13.37", cols["arm__arcsine_corrector_gls"]["mae"]),
         fs_num("ours (probe)", "13.370", cols["arm__arcsine_corrector_gls"]["mae"])]
    for k, s2, s3, d, lo, hi, gb in [("hgb_l1", "11.69", "11.688", "-1.896", "-4.758", "+0.967", "17"),
                                     ("lgbm", "12.70", "12.704", "-0.745", "-3.298", "+1.808", "18"),
                                     ("rf", "12.87", "12.867", "-0.781", "-3.156", "+1.595", "19"),
                                     ("lgbm_tweedie", "13.62", "13.617", "+0.337", "-1.232", "+1.906", "17"),
                                     ("ridge", "14.48", "14.478", "+1.808", "-1.805", "+5.420", "23")]:
        cc = cons["arm__rival_" + k]
        L += [fs_num(k + " MAE", s2, cols["arm__rival_" + k]["mae"]), fs_num(k + " MAE (probe)", s3, cols["arm__rival_" + k]["mae"]),
              fs_num(k + " d (probe)", d, cc["mean"]), fs_num(k + " low (probe)", lo, cc["low"]),
              fs_num(k + " high (probe)", hi, cc["high"]),
              fs_exact(k + " groups ours better (probe)", gb, cc["groups_ours_better"], 0)]
    cc = cons["arm__rival_hgb_l1"]
    L += [fs_num("vs L1 d (notes)", "-1.90", cc["mean"]), fs_num("vs L1 low (notes)", "-4.76", cc["low"]),
          fs_num("vs L1 high (notes)", "+0.97", cc["high"]),
          fs_claim("every per-region rival contrast CANNOT TELL", "cannot_tell x5",
                   all(cons["arm__rival_" + k]["tag"] == "cannot_tell" for k in ["ridge", "rf", "lgbm", "lgbm_tweedie", "hgb_l1"]),
                   {k: cons["arm__rival_" + k]["tag"] for k in ["ridge", "rf", "lgbm", "lgbm_tweedie", "hgb_l1"]}),
          fs_claim("mid-pack: L1, LightGBM, RF better; Tweedie, Ridge worse", "as stated",
                   all(cols["arm__rival_" + k]["mae"] < cols["arm__arcsine_corrector_gls"]["mae"] for k in ["hgb_l1", "lgbm", "rf"])
                   and all(cols["arm__rival_" + k]["mae"] > cols["arm__arcsine_corrector_gls"]["mae"] for k in ["lgbm_tweedie", "ridge"]),
                   "as stated")]
    fs["A2"] = L
    return fs


# ----------------------------------------------------------------------------- spot checks (C)
def spot_checks():
    """Independent light re-computation of the numbers that change a statement (M34 rel diff / maxdev,
    P29 t quantiles / p-values from the recorded mean and SE, R3b fire change %)."""
    import numpy as np
    import pyarrow.parquet as pq
    from scipy import stats
    out = {}
    runs = {"pm25": "D:/treeroute/runs/pm25/headline/20261007_74e67609",
            "ndvi": "D:/treeroute/runs/ndvi/headline/20261016_d1de3158",
            "fire": "D:/treeroute/runs/fire/headline/20261017_869d1f38",
            "defo": "D:/treeroute/runs/defo/headline/20261017_d71c61f4"}
    m34 = {}
    for run, d in runs.items():
        cols = ["y", "normal", "legal_min", "legal_max", "arm__identity_trees_off_unweighted", "base__guess_normal"]
        if run == "fire":
            cols += ["arm__log_c_trees_off_unweighted", "base__predict_zero", "arm__arcsine_corrector_gls"]
        t = pq.read_table(d + "/test_preds.parquet", columns=cols).to_pandas()
        lab = np.isfinite(t["y"].to_numpy())
        y = t["y"].to_numpy()[lab]
        to = t["arm__identity_trees_off_unweighted"].to_numpy()
        gn = t["base__guess_normal"].to_numpy()
        mto = float(np.mean(np.abs(y - to[lab])))
        mgn = float(np.mean(np.abs(y - gn[lab])))
        clip = np.clip(t["normal"].to_numpy(), t["legal_min"].to_numpy(), t["legal_max"].to_numpy())
        m34[run] = {"labelled": int(lab.sum()), "saved": int(len(t)), "MAE_TO": mto, "MAE_GN": mgn,
                    "rel": (mto - mgn) / mgn, "maxdev": float(np.max(np.abs(to - gn))),
                    "GN_eq_clip": bool(np.array_equal(gn, clip))}
        if run == "fire":
            mf = {c: float(np.mean(np.abs(y - t[c].to_numpy()[lab]))) for c in
                  ["arm__log_c_trees_off_unweighted", "base__predict_zero", "arm__arcsine_corrector_gls"]}
            out["R3b_fire"] = {"mae": mf,
                               "change_pct_vs_logTO": 100 * (mf["arm__arcsine_corrector_gls"] - mf["arm__log_c_trees_off_unweighted"]) / mf["arm__log_c_trees_off_unweighted"],
                               "change_pct_vs_PZ": 100 * (mf["arm__arcsine_corrector_gls"] - mf["base__predict_zero"]) / mf["base__predict_zero"]}
        del t
    out["M34"] = m34
    p29 = {}
    for x in A["P29"]["values"]["changed"]:
        G, mu, se = x["G"], x["mean"], x["se"]
        q = float(stats.t.ppf(0.975, G - 1))
        p29["%s|%s|%s" % (x["who"], x["problem"], x["lead"])] = {
            "G": G, "t_quantile": q, "low_t": mu - q * se, "high_t": mu + q * se,
            "p_z": float(2 * stats.norm.sf(abs(mu / se))), "p_t": float(2 * stats.t.sf(abs(mu / se), G - 1)),
            "low_z": mu - 1.96 * se}
    out["P29_changed"] = p29
    # coral (0,10] / (10,50] / (50,inf) cuts of the fact-sheet probe: pooled MAE ours vs hgb_l1 (single implementation C)
    cd = "D:/treeroute/runs/coral/headline/20261020_f3b8e3da/test_preds.parquet"
    rd = "D:/treeroute/rivals/coral/20261020_f3b8e3da/lead_0/preds_hgb_l1.parquet"
    t = pq.read_table(cd, columns=["unit", "time", "lead", "group", "y", "arm__arcsine_corrector_gls"]).to_pandas()
    r = pq.read_table(rd, columns=["unit", "time", "lead", "arm__rival_hgb_l1"]).to_pandas()
    j = t.merge(r, on=["unit", "time", "lead"], how="left", validate="one_to_one", indicator=True)
    assert len(j) == len(t) == 2312 and bool((j["_merge"] == "both").all())
    y = j["y"].to_numpy(np.float64)
    cuts = {}
    for name, m in [("(0,10]", (y > 0) & (y <= 10)), ("(10,50]", (y > 10) & (y <= 50)), ("(50,inf)", y > 50)]:
        cuts[name] = {"n": int(m.sum()), "n_groups": int(j.loc[m, "group"].nunique()),
                      "ours": float(np.mean(np.abs(y[m] - j["arm__arcsine_corrector_gls"].to_numpy()[m]))),
                      "hgb_l1": float(np.mean(np.abs(y[m] - j["arm__rival_hgb_l1"].to_numpy()[m])))}
    out["RC12_probe_cuts_single_implementation"] = {"inputs": {cd: sha(cd)[:16], rd: sha(rd)[:16]}, "cuts": cuts}
    return out


# ----------------------------------------------------------------------------- comparator self-test
def selftest():
    """The comparator must flag a 1e-10 relative change at full precision, a change of more than half a unit in the
    last printed digit, a flipped tag and a missing value; and must accept a correctly rounded print."""
    base = {"x": 0.004385064558301006, "p": 0.04921011488404211, "t": "helps", "n": 40, "z": None}
    cases = {
        "identical": (dict(base), True),
        "rel 1e-10 at full precision": (dict(base, x=base["x"] * (1 + 1e-10)), False),
        "correct 10-sig print": (dict(base, p=0.04921011488), True),
        "print off by one in last digit": (dict(base, p=0.04921011489), False),
        "flipped tag": (dict(base, t="cannot_tell"), False),
        "int differs": (dict(base, n=39), False),
        "null on one side": (dict(base, z=1.0), False),
    }
    res = {}
    for name, (other, expect_agree) in cases.items():
        got = compare(base, other)["n_disagree"] == 0
        res[name] = {"expect_agree": expect_agree, "got_agree": got, "ok": got == expect_agree}
    return res


# ----------------------------------------------------------------------------- main
def main():
    doc = {"script": D + "/reconcile_AB.py", "post_hoc": True,
           "note": "POST HOC reconciliation; never changes a pre-registered verdict.",
           "result_A_sha256": sha(D + "/result_A.json"), "result_B_sha256": sha(D + "/result_B.json"),
           "posthoc_A_sha256": sha(D + "/posthoc_A.py"), "posthoc_B_sha256": sha(D + "/posthoc_B.py"),
           "SPEC_sha256": sha(D + "/SPEC.json"),
           "A_failed_checks": len(RA["failed_checks"]), "B_failed_checks": len(RB["failed_checks"]),
           "items": {}}
    # input hashes: union of the files A and B say they read
    files = {}
    for it in ITEMS:
        for p, h in A[it]["inputs_sha256_prefix"].items():
            files.setdefault(p, {})["A"] = h
        for p, h in B[it]["inputs"].items():
            files.setdefault(p, {})["B"] = h
    spec_inputs = {}
    for it in SPEC["items"]:
        for s in it["inputs"]:
            mm = re.match(r"(\S+) \[sha256 ([0-9a-f]{16})\]", s)
            if mm:
                spec_inputs[mm.group(1)] = mm.group(2)
    hashes = {}
    for p in sorted(files):
        full = sha(p)
        hashes[p] = {"sha256": full, "prefix": full[:16], "A": files[p].get("A"), "B": files[p].get("B"),
                     "spec": spec_inputs.get(p),
                     "ok": all(v is None or v == full[:16] for v in (files[p].get("A"), files[p].get("B"), spec_inputs.get(p)))}
    doc["input_hashes"] = hashes
    doc["n_input_files"] = len(hashes)
    doc["n_input_hash_mismatch"] = sum(1 for v in hashes.values() if not v["ok"])
    doc["spec_inputs_not_read_by_A_or_B"] = sorted(set(spec_inputs) - set(files))
    for it in ITEMS:
        ca = CANON[it](A[it]["values"], "A")
        cb = CANON[it](B[it]["values"], "B")
        cmp_ = compare(ca, cb)
        cmp_["A_checks"] = {"n": A[it]["n_checks"], "failed": A[it]["n_failed_checks"]}
        cmp_["B_checks"] = {"n": len(B[it]["checks"]), "failed": sum(1 for c in B[it]["checks"] if not c.get("ok", False))}
        cmp_["verdict"] = "AGREE" if cmp_["n_disagree"] == 0 else "DISAGREE"
        cmp_["A_inputs"] = A[it]["inputs_sha256_prefix"]
        cmp_["B_inputs"] = B[it]["inputs"]
        doc["items"][it] = cmp_
    doc["spot_checks_C"] = spot_checks()
    sc, cmpv = doc["spot_checks_C"], {}
    for run, x in sc["M34"].items():
        a = A["M34"]["values"][run]
        for k, ak in [("MAE_TO", "MAE_TO"), ("MAE_GN", "MAE_GN"), ("rel", "rel_diff"), ("maxdev", "maxdev_all_saved_rows"),
                      ("GN_eq_clip", "GN_equals_clip_normal_exactly")]:
            cmpv["M34/%s/%s" % (run, k)] = {"C": x[k], "A": a[ak], "equal": x[k] == a[ak]}
        for k, ak in [("labelled", "labelled_rows"), ("saved", "saved_rows")]:
            cmpv["M34/%s/%s" % (run, k)] = {"C": x[k], "A": a["population"][ak], "equal": x[k] == a["population"][ak]}
    chA = {"%s|%s|%s" % (x["who"], x["problem"], x["lead"]): x for x in A["P29"]["values"]["changed"]}
    for key, x in sc["P29_changed"].items():
        for k, ak in [("t_quantile", "t_quantile"), ("low_t", "low_t"), ("high_t", "high_t"), ("p_z", "p_z"),
                      ("p_t", "p_t"), ("low_z", "low")]:
            cmpv["P29/%s/%s" % (key, k)] = {"C": x[k], "A": chA[key][ak], "equal": x[k] == chA[key][ak]}
    fa = A["R3b"]["values"]["fire"]
    for k, ak in [("change_pct_vs_logTO", "change_pct_vs_best"), ("change_pct_vs_PZ", "change_pct_vs_predict_zero")]:
        cmpv["R3b/fire/" + k] = {"C": sc["R3b_fire"][k], "A": fa[ak], "equal": sc["R3b_fire"][k] == fa[ak]}
    doc["spot_checks_C_vs_A"] = cmpv
    print("spot checks C equal to A: %d / %d" % (sum(1 for v in cmpv.values() if v["equal"]), len(cmpv)))
    doc["fact_sheet"] = fact_sheet(doc["spot_checks_C"])
    doc["comparator_selftest"] = selftest()
    assert all(v["ok"] for v in doc["comparator_selftest"].values()), doc["comparator_selftest"]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, default=str)
    # console summary
    print("inputs hashed:", doc["n_input_files"], "mismatches:", doc["n_input_hash_mismatch"],
          "spec inputs not read:", doc["spec_inputs_not_read_by_A_or_B"])
    for it in ITEMS:
        c = doc["items"][it]
        fsl = doc["fact_sheet"][it]
        nd = [x for x in fsl if x["status"] == "DIFFERS"]
        print("%-5s %-8s leaves %4d numeric %4d float-bit-identical %4d printed-prec %3d maxrel %.2e | A-only %3d B-only %3d | "
              "fact sheet %d checked, %d DIFFERS" % (
                  it, c["verdict"], c["n_common_leaves"], c["n_numeric"], c["n_float_bit_identical"],
                  c["n_compared_at_printed_precision"], c["max_rel_diff_full_precision"],
                  len(c["only_in_A"]), len(c["only_in_B"]), len(fsl), len(nd)))
        for x in c["disagreements"][:20]:
            print("    DISAGREE", x)
        for x in nd:
            print("    DIFFERS", x["label"], "| stated", x["stated"], "| agreed", x["agreed"])
        for x in fsl:
            if x["status"] not in ("MATCHES", "DIFFERS"):
                print("    ", x["status"], x["label"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
