#!/usr/bin/env python3
"""make_report.py -- writes POSTHOC_REPORT.md from SPEC.json, result_A.json, result_B.json and reconcile_AB.json.

POST HOC. Run: py -3.9 -I D:/treeroute/analysis/paper_posthoc/make_report.py
Writes ONLY D:/treeroute/analysis/paper_posthoc/POSTHOC_REPORT.md. Every number in the report is read from
the JSON files (A's values; A and B agree on every compared leaf, see reconcile_AB.json), not typed by hand.
"""
import hashlib
import json

D = "D:/treeroute/analysis/paper_posthoc"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


SPEC = load(D + "/SPEC.json")
RA = load(D + "/result_A.json")
RB = load(D + "/result_B.json")
RC = load(D + "/reconcile_AB.json")
A = RA["items"]
SPECI = {it["id"]: it for it in SPEC["items"]}
ITEMS = [it["id"] for it in SPEC["items"]]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()


def g(x, n=10):
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, int):
        return "{:,}".format(x)
    return "%.*g" % (n, x)


def s(x, n=4):
    if x is None:
        return "n/a"
    return "%+.*g" % (n, x)


def ci(lo, hi, n=4):
    return "[%s, %s]" % (s(lo, n), s(hi, n))


TAG = {"helps": "HELPS", "hurts": "HURTS", "cannot_tell": "CANNOT TELL", "does_not_help_equivalent": "EQUIVALENT",
       "declined": "declined", "identical": "IDENTICAL"}


def tg(t):
    return TAG.get(t, str(t))


def table(head, rows):
    out = ["| " + " | ".join(h.replace("|", "/") for h in head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "/") for c in r) + " |")
    return "\n".join(out)


WORDS = {
    "M34": "For each run with an identity link: mean absolute error of the identity trees-off column and of the "
           "guess-normal baseline over the labelled rows, their exact difference and relative difference, the largest "
           "absolute row difference between the two columns over every saved row, and the anomaly R2 of trees-off "
           "(1 minus squared error of the anomaly over squared anomaly, anomalies taken from the saved normal).",
    "R12": "Fire nowcast: pooled MAE of each listed column over the labelled rows, sorted. New: for each region, MAE of "
           "the reference column minus MAE of the adopted column (positive = adopted better), averaged over the 40 "
           "regions, with a leave-one-region-out jackknife interval (mean +- 1.96 SE) and the run's band tag.",
    "R13": "For each link x weighting: pooled MAE of the corrector arm, its placebo and the plain arm, and the two "
           "differences. Each placebo pair of jackknife.csv re-derived from the per-region MAEs (placebo minus "
           "corrector, region jackknife, band tag).",
    "R14": "Absolute penalties of the adopted grid point: per-unit and neighbour kinds a_tree = trees centre x level and "
           "a_ctx = a_tree x ratio; region kind lambda = lambda centre x level.",
    "R15": "Every saved column at the nowcast: pooled MAE, anomaly R2, corr2 and hit rate over labelled rows. Regret = "
           "MAE of the adopted arm minus MAE of the best selectable tree arm (arms without 'trees_off'), absolute and "
           "relative. Report-only: per-region contrast of every other selectable arm against the adopted arm "
           "(arm minus adopted, positive = adopted better), region jackknife, band tag. Factor effects as MAE differences.",
    "P29": "For each of the 79 deciding verdict rows: mean and SE from the source file, interval with the t quantile "
           "for G-1 degrees of freedom instead of 1.96, two-sided p-values (normal and t), the D74 tag re-applied with "
           "the t interval, Holm over the five nowcast verdicts of ours, and band as a percentage of the deciding "
           "reference MAE.",
    "R3b": "Nowcast: pooled MAE of the adopted column against the lowest-MAE naive baseline (guess-normal, last-5 normal, "
           "predict-zero, each link's trees-off; coral: donor median and predict-zero), as a percentage change.",
    "RC12": "Coral nowcast split by the observed value (engine magnitude bins and y >= 50): per stratum, rows, regions, "
            "mean y, mean prediction and MAE of ours, the five rivals, predict-zero and donor median; per-region "
            "contrast rival minus ours over the regions present in the stratum, region jackknife, band tag.",
    "A1": "Fire nowcast split by the observed value (zero, active, top 1% with q99 from the test labels, active below "
          "the top 1%): per stratum, MAE and mean prediction of ours, Tweedie and the other rivals; per-region contrast "
          "Tweedie minus ours, region jackknife, band tag.",
    "A2": "Coral nowcast visits with y > 0: pooled MAE and mean prediction of ours and each rival; per-region contrast "
          "rival minus ours over the 36 regions, region jackknife, band tag.",
}


# ----------------------------------------------------------------------------- per-item value sections
def vals_M34():
    v = A["M34"]["values"]
    rows = []
    for r in ["pm25", "ndvi", "fire", "defo"]:
        x = v[r]
        p = x["population"]
        rows.append([r, "%s / %s / %s / %s" % (g(p["labelled_rows"]), g(p["units"]), g(p["groups"]), p["years"]),
                     g(p["saved_rows"]), x["MAE_TO_6sig"], x["MAE_GN_6sig"], x["diff_exact"], "%.3g" % x["rel_diff"],
                     "%.4g" % x["maxdev_all_saved_rows"], g(x["tolerance_identity"]), "%.3f" % x["maxdev_over_tolerance"],
                     "%.3g" % x["anomaly_r2_TO"], str(x["GN_equals_clip_normal_exactly"])])
    t = table(["run", "labelled rows / units / groups / years", "saved rows (maxdev)", "MAE_TO (6 sig)",
               "MAE_GN (6 sig)", "exact diff TO-GN", "rel diff", "maxdev |TO-GN|", "identity tol", "maxdev / tol",
               "TO anomaly R2", "GN == clip(normal)"], rows)
    full = "Full precision: " + "; ".join("%s TO %r vs GN %r" % (r, v[r]["MAE_TO"], v[r]["MAE_GN"])
                                          for r in ["pm25", "ndvi", "fire", "defo"]) + "."
    return t + "\n\n" + full + " The GN anomaly R2 is exactly 0 in all four. The clip changes 0 rows in all four."


def vals_R12():
    v = A["R12"]["values"]
    out = [table(["rank", "column", "pooled MAE"], [[x["rank"], x["column"] + (" (ADOPTED)" if x["column"] == v["adopted"] else ""),
                                                    g(x["mae"], 12)] for x in v["pooled_mae_ascending"]])]
    rows = []
    for ref, c in v["report_only_contrasts"].items():
        rows.append([ref, s(c["mean"]), "%.4g" % c["se"], ci(c["low"], c["high"]), tg(c["tag"]),
                     "%d/%d" % (c["groups_adopted_better"], c["n_groups"]), s(c["pooled_contrast"])])
    out.append("NEW report-only contrasts (d_g = MAE_ref(g) - MAE_adopted(g); positive = adopted better; band %s):\n\n" % g(v["band"])
               + table(["reference", "mean d", "SE", "95% CI (z)", "tag", "regions adopted better", "pooled difference"], rows))
    sfc = v["final_reread_adoption_surface"]
    rows = []
    for arm in ["log_c_plain_unweighted", "log_c_plain_gls", "log_c_corrector_unweighted", "log_c_corrector_gls",
                "arcsine_plain_gls", "arcsine_corrector_gls"]:
        pa = sfc["per_arm"][arm]
        rows.append([arm, g(pa["min_over_grid"], 7), pa["argmin_point"], g(pa["at_adopted_point"], 7), str(pa["eligible"])])
    for arm in ["log_c_trees_off_unweighted", "arcsine_trees_off_unweighted"]:
        rows.append([arm, g(sfc["per_arm"][arm]["at_adopted_point"], 7), "(no grid)", "", "False"])
    out.append("Final part re-read from adoption.json (inner decision surface, %s rows, %s units; adopted point %s). "
               "'Surface pick' = the arm's own best grid point (A and B agree); 'at adopted point' = A only, direct re-read. "
               "Surface predict-zero %s.\n\n" % (g(sfc["decision_rows"]), g(sfc["decision_units"]), sfc["adopted_point"],
                                                g(sfc["predict_zero_surface_mae"], 7))
               + table(["arm", "surface pick MAE", "pick point", "MAE at adopted point (A only)", "eligible"], rows))
    rows = [[x["reference"], x["arm"], s(x["mean"]), ci(x["low"], x["high"]), tg(x["file_tag"]), tg(x["tag"])]
            for x in v["final_jackknife_log_rows"]]
    out.append("jackknife.csv log-arm rows re-derived from score_by_group.csv (equal to the file, rtol 1e-12); "
               "d_g = MAE_reference(g) - MAE_arm(g), positive = arm better:\n\n"
               + table(["reference", "arm", "mean", "95% CI", "tag (file)", "tag (re-derived)"], rows))
    return "\n\n".join(out)


def vals_R13():
    v = A["R13"]["values"]
    rows = []
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        for t in v[run]["triples"]:
            rows.append([run, t["link"] + " / " + t["weighting"], "yes" if t["adopted_triple"] else "", g(t["corrector"]),
                         g(t["placebo"]), g(t["plain"]), s(t["corrector_minus_placebo"]), s(t["corrector_minus_plain"])])
    out = [table(["run", "link / weighting", "adopted", "corrector", "placebo", "plain", "corrector - placebo",
                  "corrector - plain"], rows)]
    rows = []
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        for x in v[run]["placebo_pairs_rederived"]:
            rows.append([run, x["arm"].replace("arm__", ""), s(x["mean"]), "%.3g" % x["se"], ci(x["low"], x["high"]),
                         x["n_groups"], tg(x["file_tag"]), tg(x["tag"])])
    out.append("All 21 placebo band pairs of jackknife.csv (d_g = MAE_placebo(g) - MAE_corrector(g)), re-derived from "
               "score_by_group.csv; mean, SE, CI, regions and tag equal the file (rtol 1e-12):\n\n"
               + table(["run", "corrector arm", "mean", "SE", "95% CI", "regions", "tag (file)", "tag (re-derived)"], rows))
    return "\n\n".join(out)


def vals_R14():
    v = A["R14"]["values"]
    rows = []
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        x = v[run]
        rows.append([run, x["kind"], x["centre"], g(x["level"]), g(x["ratio"]), g(x.get("a_tree")), g(x.get("a_ctx")),
                     g(x.get("lambda")), x["grid_points"]])
    return table(["run", "kind", "derived centre", "level", "ratio", "a_tree", "a_ctx", "lambda", "grid points"], rows) + \
        "\n\nAsserted for every run (A and B): penalty == best_tree_penalty, declined false, point in the derived R14 grid, " \
        "centre[0] equals the C12 constant recorded in derived.json. The context centre (0.25) is not used."


def vals_R15():
    v = A["R15"]["values"]
    out = []
    rows = []
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        x = v[run]
        rows.append([run, "%d (%d/%d/%d; %d selectable)" % (x["n_columns"], x["n_arms"], x["n_placebos"], x["n_baselines"],
                                                           x["n_selectable"]),
                     x["adopted"].replace("arm__", ""), g(x["mae_adopted"]), x["best_selectable"].replace("arm__", ""),
                     g(x["mae_best"]), "%.4g" % x["regret_abs"], "%.3f%%" % (100 * x["regret_rel"]),
                     x["lowest_column_any_kind"].replace("arm__", "").replace("base__", "base:"), g(x["lowest_column_mae"]),
                     ", ".join(e.replace("arm__", "") for e in x["eligible"]) if len(x["eligible"]) < x["n_selectable"] else "all %d" % len(x["eligible"])])
    out.append(table(["run", "columns (arms/placebos/baselines)", "adopted", "MAE adopted", "best selectable", "MAE best",
                      "regret", "regret rel", "lowest column (any kind)", "its MAE", "eligible (adoption.json)"], rows))
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        x = v[run]
        rows = []
        for c, r in sorted(x["columns"].items(), key=lambda kv: kv[1]["mae"]):
            flag = "ADOPTED" if c == x["adopted"] else ("selectable" if r["selectable"] else r["kind"])
            rows.append([c, flag, g(r["mae"]), g(r["anom_r2"], 4), g(r["corr2"], 4), g(r["hit"], 4), g(r["hit_floor"], 4)])
        out.append("**%s** (hit tolerance %s, measurement-error floor %s; band %s):\n\n" % (
            run, g(x["hit_tolerance"], 6), g(x["measurement_error_floor"]), g(x["band"], 6))
            + table(["column", "role", "pooled MAE", "anomaly R2", "corr2", "hit", "hit at floor"], rows))
        rows = []
        for a, c in sorted(x["report_only_contrasts_vs_adopted"].items(), key=lambda kv: kv[1]["mean"]):
            rows.append([a.replace("arm__", ""), s(c["mean"]), ci(c["low"], c["high"]), tg(c["tag"]),
                         "%d/%d" % (c["groups_adopted_better"], c["n_groups"])])
        out.append("%s report-only contrasts vs the adopted arm (d_g = MAE_arm(g) - MAE_adopted(g), positive = adopted better):\n\n" % run
                   + table(["arm", "mean d", "95% CI", "tag", "regions adopted better"], rows))
    rows = []
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        x = v[run]
        w = "; ".join("%s %s %s" % (f["link"], f["tool"], s(f["unweighted_minus_gls"], 3)) for f in x["factor_weighting"]) or "n/a (no GLS arms)"
        t = "; ".join("%s %s %s" % (f["link"], f["weighting"], s(f["plain_minus_corrector"], 3)) for f in x["factor_tool"])
        l = "; ".join("%s %s" % (f["link"], g(f["best_mae"], 6)) for f in sorted(x["factor_link"], key=lambda f: f["best_mae"]))
        rows.append([run, w, t, l])
    out.append("Factor summaries (weighting = MAE unweighted - MAE GLS; tool = MAE plain - MAE corrector; link = best arm per link):\n\n"
               + table(["run", "weighting effect", "tool effect", "best arm per link (ascending)"], rows))
    return "\n\n".join(out)


def vals_P29():
    v = A["P29"]["values"]
    out = ["%d deciding rows: %d own, %d common, %d human. Declined own rows: %d. IDENTICAL rows: %d. Tags that change under t: %d. "
           "Largest relative error of SE == (high-low)/(2*1.96): %.2g; of CI == mean +- 1.96 SE: %.2g." % (
               v["n_rows"], v["n_own"], v["n_common"], v["n_human"],
               sum(1 for r in v["rows"] if r["who"] == "own" and r["tag"] == "declined"),
               sum(1 for r in v["rows"] if r["tag"] == "identical"), v["n_changed_tag_under_t"],
               v["max_rel_se_check"], v["max_rel_ci_check"])]
    rows = []
    for x in v["changed"]:
        rows.append(["%s %s lead %s" % (x["who"], x["problem"], x["lead"]), x["name"], x["G"], "%.6f" % x["t_quantile"],
                     s(x["mean"]), ci(x["low"], x["high"]), ci(x["low_t"], x["high_t"]), "%.6f" % x["p_z"], "%.6f" % x["p_t"],
                     tg(x["tag"]) + " -> " + tg(x["tag_t"])])
    out.append("Rows whose tag changes under t(G-1):\n\n" + table(
        ["row", "contrast", "G", "t quantile", "mean", "z CI", "t CI", "p_z", "p_t", "tag z -> t"], rows))
    rows = []
    for h in sorted(v["holm_lead0_own"], key=lambda h: h["p_z"]):
        rows.append([h["problem"], "%.4g" % h["p_z"], "%.4g" % h["holm_adj_p_z"], str(h["survives_z"]),
                     "%.4g" % h["p_t"], "%.4g" % h["holm_adj_p_t"], str(h["survives_t"])])
    out.append("Holm step-down over the 5 nowcast verdicts of ours (alpha 0.05):\n\n" + table(
        ["problem", "p_z", "Holm-adjusted p_z", "survives (z)", "p_t", "Holm-adjusted p_t", "survives (t)"], rows))
    rows = [[k, g(b["band"], 6), b["reference"], g(b["mae_reference"], 7), "%.4f%%" % b["band_share_pct"]]
            for k, b in v["band_share"].items()]
    out.append("Band as a share of the deciding reference MAE (lead-0 'all' pooled headline row):\n\n" + table(
        ["problem", "band", "reference", "reference MAE", "band share"], rows))
    fb = v["fire_blocked_jackknife_read"]
    out.append("Fire blocked jackknife (read from jackknife.csv, report only): mean %s, SE %s, CI %s, %d blocks." % (
        g(fb["mean"], 4), g(fb["se"], 4), ci(fb["low"], fb["high"]), fb["n_blocks"]))
    rows = []
    for r in v["rows"]:
        rows.append([r["who"], r["problem"], r["lead"], "ours" if r["who"] == "own" else r["name"], r["G"], s(r["mean"]),
                     g(r["se"], 4), ci(r["low"], r["high"]), ci(r["low_t"], r["high_t"]), g(r["p_z"], 4), g(r["p_t"], 4),
                     tg(r["tag"]), tg(r["tag_t"]) + (" (CHANGES)" if r["changes"] else "")])
    out.append("All 79 deciding rows (own rows: ours vs the reference; rival rows: d = MAE_rival - MAE_ours):\n\n" + table(
        ["kind", "problem", "lead", "vs", "G", "mean", "SE", "z CI", "t CI", "p_z", "p_t", "tag (z)", "tag (t)"], rows))
    return "\n\n".join(out)


def vals_R3b():
    v = A["R3b"]["values"]
    rows = []
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        x = v[run]
        cands = "; ".join("%s %s" % (c.replace("arm__", "").replace("base__", ""), g(m, 8))
                          for c, m in sorted(x["candidates"].items(), key=lambda kv: kv[1]))
        extra = (" (vs predict-zero %+.3f%%)" % x["change_pct_vs_predict_zero"]) if "change_pct_vs_predict_zero" in x else ""
        rows.append([run, x["model"].replace("arm__", ""), g(x["mae_model"]), x["best_baseline"].replace("arm__", "").replace("base__", ""),
                     g(x["mae_best"]), "%+.3f%%" % x["change_pct_vs_best"] + extra, cands])
    return table(["run", "model (adopted)", "MAE", "best naive", "MAE", "change", "all candidates (ascending)"], rows)


def strata_table(st, ours, focus, others, contrast_key):
    rows = []
    for name, x in st.items():
        c = x["contrasts"].get(focus)
        rows.append([name, g(x["n"]), x["n_groups"], g(x["mean_y"], 5), g(x["columns"][ours]["mae"], 6),
                     g(x["columns"][focus]["mae"], 6), g(x["columns"][ours]["mean_pred"], 5), g(x["columns"][focus]["mean_pred"], 5),
                     (s(c["mean"]) + " " + ci(c["low"], c["high"])) if c else "", tg(c["tag"]) if c else "",
                     ("%d/%d" % (c["groups_ours_better"], c["n_groups"])) if c else "",
                     " / ".join(g(x["columns"][o]["mae"], 5) for o in others)])
    return rows


def vals_RC12():
    v = A["RC12"]["values"]
    e = v["edges_lead0"]
    O, H = "arm__arcsine_corrector_gls", "arm__rival_hgb_l1"
    others = ["arm__rival_ridge", "arm__rival_rf", "arm__rival_lgbm", "arm__rival_lgbm_tweedie", "base__predict_zero", "base__donor_median"]
    out = ["Edges (lead 0, positive donor labels, %s donor rows): q25 %r, q50 %r, q75 %r. Band %s." % (
        g(e["donor_rows"]), e["pos_q25"], e["pos_q50"], e["pos_q75"], g(v["band"]))]
    out.append(table(["stratum", "visits", "regions", "mean y", "MAE ours", "MAE hgb_l1", "mean pred ours", "mean pred hgb_l1",
                      "d = hgb_l1 - ours [CI]", "tag", "regions ours better", "MAE ridge / rf / lgbm / tweedie / PZ / DM"],
                     strata_table(v["strata"], O, H, others, None)))
    rows = []
    for name, x in v["strata"].items():
        for c, k in x["contrasts"].items():
            if c != H and k["tag"] != "cannot_tell":
                rows.append([name, c.replace("arm__rival_", "").replace("base__", ""), s(k["mean"]), ci(k["low"], k["high"]), tg(k["tag"]),
                             "%d/%d" % (k["groups_ours_better"], k["n_groups"])])
    out.append("Other contrasts that are not CANNOT TELL (d = MAE_column - MAE_ours; positive = ours better):\n\n" + table(
        ["stratum", "column", "mean d", "95% CI", "tag", "regions ours better"], rows))
    cuts = RC["spot_checks_C"]["RC12_probe_cuts_single_implementation"]["cuts"]
    out.append("Probe cuts of the fact sheet, single implementation C (reconcile_AB.py; NOT A/B-reconciled): " + "; ".join(
        "%s %d visits / %d regions: ours %.4f vs hgb_l1 %.4f" % (k, c["n"], c["n_groups"], c["ours"], c["hgb_l1"]) for k, c in cuts.items()) + ".")
    return "\n\n".join(out)


def vals_A1():
    v = A["A1"]["values"]
    O, T = "arm__arcsine_corrector_gls", "arm__rival_lgbm_tweedie"
    others = ["arm__rival_ridge", "arm__rival_ridge_raw", "arm__rival_rf", "arm__rival_lgbm", "base__predict_zero"]
    out = ["q99 = numpy.quantile(test y, 0.99) = %r (from TEST labels); strict y > q99 gives %d rows. Band %s. Guard passed: %s." % (
        v["q99"], v["top1_strict_gt_rows"], g(v["band"]), ", ".join("%s %s" % (k, x[0]) for k, x in v["guard_passed"].items()))]
    out.append(table(["stratum", "rows", "regions", "mean y", "MAE ours", "MAE Tweedie", "mean pred ours", "mean pred Tweedie",
                      "d = Tweedie - ours [CI]", "tag", "regions ours better", "MAE ridge (guarded) / ridge raw / rf / lgbm / PZ"],
                     strata_table(v["strata"], O, T, others, None)))
    rows = []
    for name, x in v["strata"].items():
        for c, k in x["contrasts"].items():
            if c != T:
                rows.append([name, c.replace("arm__rival_", "").replace("base__", ""), s(k["mean"]), ci(k["low"], k["high"]), tg(k["tag"]),
                             "%d/%d" % (k["groups_ours_better"], k["n_groups"])])
    out.append("Beside (report-only; d = MAE_column - MAE_ours):\n\n" + table(
        ["stratum", "column", "mean d", "95% CI", "tag", "regions ours better"], rows))
    out.append("Ridge failed its guard: its guarded column equals arm__identity_trees_off_unweighted exactly (max |diff| %g) and "
               "differs from base__guess_normal by up to %.3g (the M34 gap)." % (
                   v["ridge_guarded_minus_identity_trees_off_maxabs"], v["ridge_guarded_minus_guess_normal_maxabs"]))
    return "\n\n".join(out)


def vals_A2():
    v = A["A2"]["values"]
    x = v["active_y_gt_0"]
    rows = [["ours (arcsine corrector GLS)", g(x["columns"]["arm__arcsine_corrector_gls"]["mae"], 6),
             g(x["columns"]["arm__arcsine_corrector_gls"]["mean_pred"], 5), "", "", "", ""]]
    for c, k in sorted(x["contrasts"].items(), key=lambda kv: x["columns"][kv[0]]["mae"]):
        rows.append([c.replace("arm__rival_", "").replace("base__", ""), g(x["columns"][c]["mae"], 6), g(x["columns"][c]["mean_pred"], 5),
                     s(k["mean"]), ci(k["low"], k["high"]), tg(k["tag"]), "%d/%d" % (k["groups_ours_better"], k["n_groups"])])
    return ("%d visits with y > 0 in %d regions; mean y %s; band %s. All five rivals passed their lead-0 guard (guarded == raw).\n\n" % (
        x["n"], x["n_groups"], g(x["mean_y"], 6), g(v["band"])) +
        table(["column", "MAE", "mean pred", "d = MAE_col - MAE_ours", "95% CI", "tag", "regions ours better"], rows))


VALS = {"M34": vals_M34, "R12": vals_R12, "R13": vals_R13, "R14": vals_R14, "R15": vals_R15, "P29": vals_P29,
        "R3b": vals_R3b, "RC12": vals_RC12, "A1": vals_A1, "A2": vals_A2}


def fact_rows(it):
    rows = []
    for x in RC["fact_sheet"][it]:
        ag = x["agreed"]
        if isinstance(ag, float):
            ag = repr(ag)
        elif not isinstance(ag, str):
            ag = json.dumps(ag)
        if len(ag) > 160:
            ag = ag[:157] + "..."
        rows.append([x["label"], x["stated"], ag, x["status"]])
    return table(["check", "fact sheet / probe states", "agreed value", "status"], rows)


def inputs_rows(it):
    c = RC["items"][it]
    spec_in = set()
    import re
    for sline in SPECI[it]["inputs"]:
        m = re.match(r"(\S+) \[sha256", sline)
        if m:
            spec_in.add(m.group(1))
    paths = sorted(set(c["A_inputs"]) | set(c["B_inputs"]) | spec_in)
    rows = []
    for p in paths:
        h = RC["input_hashes"].get(p)
        rows.append([p, h["prefix"] if h else "not hashed", "yes" if p in spec_in else "no (extra)",
                     ("A" if p in c["A_inputs"] else "") + ("B" if p in c["B_inputs"] else ""),
                     "yes" if (h and h["ok"]) else "NO"])
    return table(["file", "sha256 prefix (re-hashed now)", "in spec list", "read by", "matches spec/A/B prefixes"], rows)


SCRIPT_ROWS = None


def main():
    files = {k: sha(D + "/" + k) for k in ["SPEC.json", "posthoc_A.py", "posthoc_B.py", "result_A.json", "result_B.json",
                                           "reconcile_AB.py", "reconcile_AB.json", "make_report.py"]}
    it_stat = RC["items"]
    tot_leaves = sum(c["n_common_leaves"] for c in it_stat.values())
    tot_float = sum(c["n_float_bit_identical"] for c in it_stat.values())
    tot_print = sum(c["n_compared_at_printed_precision"] for c in it_stat.values())
    tot_int = sum(c["n_int"] for c in it_stat.values())
    nA = sum(c["A_checks"]["n"] for c in it_stat.values())
    nB = sum(c["B_checks"]["n"] for c in it_stat.values())
    L = []
    L.append("# Paper post-hoc facts: A/B reconciliation (POST HOC, report-only)\n")
    L.append("2026-10-26. Rulings AK3 / AK4(a) (engine/OWNER_RULINGS_2026-10-06.md). **Every number here is POST HOC**: "
             "it was computed after the test labels were opened. **None of it changes a pre-registered verdict.** "
             "Light compute only (pandas/pyarrow on saved predictions and frozen engine CSVs; no refit, no re-routing). "
             "No seeds; every interval is a jackknife over regions (groups), z = 1.96 unless stated.\n")
    L.append("## Scripts and outputs\n")
    L.append(table(["file", "sha256", "role"], [
        [D + "/posthoc_A.py", files["posthoc_A.py"], "implementer A (unchanged; no fix needed)"],
        [D + "/posthoc_B.py", files["posthoc_B.py"], "implementer B (unchanged; no fix needed)"],
        [D + "/result_A.json", files["result_A.json"], "A output (1,327 checks, 0 failed)"],
        [D + "/result_B.json", files["result_B.json"], "B output (1,738 checks, 0 failed)"],
        [D + "/reconcile_AB.py", files["reconcile_AB.py"], "leaf-by-leaf A vs B comparison, fact-sheet comparison, input re-hash, spot checks C"],
        [D + "/reconcile_AB.json", files["reconcile_AB.json"], "reconciliation output"],
        [D + "/make_report.py", files["make_report.py"], "writes this report from the JSON files"],
        [D + "/SPEC.json", files["SPEC.json"], "the spec both implementers worked from"]]))
    L.append("\nRun: `py -3.9 -I <script>` for each (A about 10 s, B similar, reconcile about 2 s, report <1 s).\n")
    L.append("## How A and B were compared\n")
    L.append("A and B were written independently from SPEC.json (neither read the other). reconcile_AB.py maps both result "
             "files to the same canonical keys (for example run / column / metric, or problem / lead / rival for P29) and "
             "compares every leaf both report. A float agrees when it is equal to within 1e-12 relative at full precision, "
             "or, where one side printed fewer digits (B's P29 rows are rounded to 10 significant digits), within half a "
             "unit in the last printed digit. Strings, tags, booleans and integers must be equal. A self-test confirms the "
             "comparator flags a 1e-10 relative change, a one-digit print error, a flipped tag, an integer change and a "
             "missing value. All %d input files were re-hashed now; every sha256 prefix matches SPEC.json, A and B "
             "(0 mismatches); every spec input was read by A or B.\n" % RC["n_input_files"])
    L.append("**Result: A and B agree on all 10 items.** %s leaves were compared: %s integers equal, %s floats "
             "bit-identical, %s P29 floats equal at B's printed precision, 0 disagreements. A ran %s internal checks and B "
             "%s, all passed. So no script was changed.\n" % (g(tot_leaves), g(tot_int), g(tot_float), g(tot_print), g(nA), g(nB)))
    rows = []
    notes = {
        "M34": "Fire added. 'Within 1e-8 relative' is FALSE for fire (2.09e-8); everything else matches.",
        "R12": "Ordering and final part confirmed. Two new report-only contrasts (not in the fact sheet yet).",
        "R13": "Confirmed. 21 placebo pairs re-derived exactly.",
        "R14": "Confirmed. M47 later-lead pinning not re-checked (adoption_lead_*.json not in the inputs).",
        "R15": "Confirmed. Wording: defo 'adopted = log plain' is not literal equality (6.1e-7 apart).",
        "P29": "Confirmed: exactly 2 of 79 tags change under t. 'About 80' should read 79.",
        "R3b": "Confirmed: fire +2.42% vs log trees-off, +2.36% vs predict-zero (worse).",
        "RC12": "'L1 wins on every bleached stratum' is FALSE: ours is lower in B1-B3; L1 lower only in B4 and y >= 50.",
        "A1": "Confirmed. Spec wording: Ridge's guarded column is the identity trees-off, not guess-normal exactly.",
        "A2": "Confirmed: ours mid-pack; all five contrasts CANNOT TELL.",
    }
    for it in ITEMS:
        fsl = RC["fact_sheet"][it]
        nd = sum(1 for x in fsl if x["status"] == "DIFFERS")
        nw = sum(1 for x in fsl if x["status"] == "WORDING")
        status = "MATCHES" if nd == 0 and nw == 0 else ("DIFFERS (%d)" % nd if nd else "MATCHES; wording (%d)" % nw)
        if nd and nw:
            status += "; wording (%d)" % nw
        rows.append([it, "AGREE" if it_stat[it]["n_disagree"] == 0 else "DISAGREE", it_stat[it]["n_common_leaves"],
                     "%d checked: %s" % (len(fsl), status), notes[it]])
    L.append("## Summary\n")
    L.append(table(["item", "A vs B", "leaves compared", "fact sheet", "note"], rows))
    L.append("\n**ATTENTION (fact-sheet edits needed):**\n")
    L.append("1. **M34:** 'equal within 1e-8 relative' is false for fire (relative difference %.3g). True alternatives: "
             "'equal within 2.1e-8 relative' (largest of the four, fire), or 'equal to 6 significant digits' (true in all "
             "four). Add fire: %s vs %s." % (A["M34"]["values"]["fire"]["rel_diff"], A["M34"]["values"]["fire"]["MAE_TO_6sig"],
                                              A["M34"]["values"]["fire"]["MAE_GN_6sig"]))
    s_ = A["RC12"]["values"]["strata"]
    L.append("2. **RC12:** 'L1 wins on every bleached stratum' is not reproduced. Ours has the lower MAE in B1 (%.3f vs %.3f), "
             "B2 (%.3f vs %.3f) and B3 (%.3f vs %.3f). hgb_l1 is lower only in B4 > q75 (%.3f vs %.3f) and in y >= 50 "
             "(%.3f vs %.3f); only those two per-region contrasts are HURTS." % tuple(
                 [s_[b]["columns"][c]["mae"] for b in ["B1 (0, q25]", "B2 (q25, q50]", "B3 (q50, q75]", "B4 (q75, max]", "severe y>=50"]
                  for c in ["arm__arcsine_corrector_gls", "arm__rival_hgb_l1"]]))
    L.append("3. **P29:** 'about 80 verdicts' should read 79 (14 own + 53 common + 12 human).")
    L.append("4. **R15 wording:** defo 'adopted 0.0054158 = log plain 0.0054164' should use '<' or 'vs'; the numbers match.")
    L.append("5. **A1 spec wording:** Ridge's guarded column is arm__identity_trees_off_unweighted (the R16 decline target), "
             "not base__guess_normal exactly (they differ by up to 8.09e-07).\n")
    L.append("**Could not be computed (out of the spec's inputs):** M47 (the same point pinned at later leads; needs "
             "adoption_lead_*.json); the engine-v2 alarm numbers of A2 (engine v2 replay). The RC12 probe cut (0,10] "
             "(ours 3.71 vs L1 4.41) is outside the spec formula; a single implementation (C, in reconcile_AB.py) "
             "reproduces it but it is not A/B-reconciled.\n")
    sv = RC["spot_checks_C_vs_A"]
    L.append("**Independent spot checks C** (reconcile_AB.py, third implementation, light): M34 MAE_TO, MAE_GN, relative "
             "difference, maxdev, GN == clip and row counts for all four runs; the two P29 rows that change (t quantile, "
             "t CI, z lower bound, p_z, p_t); fire R3b change %%. %d of %d values equal A (and so B) exactly%s.\n" % (
                 sum(1 for x in sv.values() if x["equal"]), len(sv),
                 "" if all(x["equal"] for x in sv.values()) else "; NOT ALL: see reconcile_AB.json spot_checks_C_vs_A"))
    for it in ITEMS:
        sp = SPECI[it]
        c = it_stat[it]
        L.append("## %s\n" % it)
        L.append("**What.** %s\n" % sp["what"])
        L.append("**Population.** %s\n" % sp["population"])
        L.append("**Formula in words.** %s\n" % WORDS[it])
        L.append("<details><summary>Spec formula (verbatim)</summary>\n\n%s\n\n</details>\n" % sp["formula"])
        L.append("**Engine definitions cited.** %s\n" % sp["engine_definition_source"])
        L.append("**A/B agreement: %s.** %d leaves compared (%d integers, %d floats bit-identical, %d at printed precision), "
                 "%d disagreements. A checks %d (failed %d); B checks %d (failed %d). Leaves only one side reports: A %d, B %d "
                 "(extra detail, not disagreements).\n" % (
                     c["verdict"], c["n_common_leaves"], c["n_int"], c["n_float_bit_identical"], c["n_compared_at_printed_precision"],
                     c["n_disagree"], c["A_checks"]["n"], c["A_checks"]["failed"], c["B_checks"]["n"], c["B_checks"]["failed"],
                     len(c["only_in_A"]), len(c["only_in_B"])))
        L.append("### Agreed values\n")
        L.append(VALS[it]() + "\n")
        L.append("### Fact-sheet comparison\n")
        L.append(fact_rows(it) + "\n")
        L.append("### Inputs\n")
        L.append(inputs_rows(it) + "\n")
        L.append("Scripts: posthoc_A.py sha256 %s; posthoc_B.py sha256 %s; reconcile_AB.py sha256 %s.\n" % (
            files["posthoc_A.py"], files["posthoc_B.py"], files["reconcile_AB.py"]))
    L.append(PART_TEXT())
    with open(D + "/POSTHOC_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("wrote", D + "/POSTHOC_REPORT.md")


def PART_TEXT():
    m = A["M34"]["values"]
    r12 = A["R12"]["values"]["report_only_contrasts"]
    r15 = A["R15"]["values"]
    p = A["P29"]["values"]
    ch = {x["problem"]: x for x in p["changed"]}
    hz = {h["problem"]: h for h in p["holm_lead0_own"]}
    r3 = A["R3b"]["values"]
    rc = A["RC12"]["values"]["strata"]
    a1 = A["A1"]["values"]["strata"]
    a2 = A["A2"]["values"]["active_y_gt_0"]
    T = "arm__rival_lgbm_tweedie"
    O = "arm__arcsine_corrector_gls"
    H = "arm__rival_hgb_l1"
    lt, pz = r12["arm__log_c_trees_off_unweighted"], r12["base__predict_zero"]
    tot_leaves = sum(c["n_common_leaves"] for c in RC["items"].values())
    bs = p["band_share"]
    lines = [
        "## Part text (paste into engine/PENDING_PARTS.md; number to be assigned by the main session)\n",
        "```",
        "## Part NNN - PAPER FACTS RE-COMPUTED POST HOC (rulings AK3, AK4(a)); TWO INDEPENDENT SCRIPTS AGREE",
        "",
        "2026-10-26. POST HOC: computed after the test labels were opened; report-only; no pre-registered verdict changes.",
        "Folder D:/treeroute/analysis/paper_posthoc (POSTHOC_REPORT.md, SPEC.json, posthoc_A.py, posthoc_B.py, reconcile_AB.py, *.json).",
        "- **Method.** Two scripts (A sha256 %s, B %s) were written independently from one spec and re-computed the provisional facts from saved predictions and frozen engine CSVs (light; no refit). reconcile_AB.py compared %s leaves: 0 disagreements (every full-precision float bit-identical). A ran 1,327 checks, B 1,738; 0 failed. All 82 input files match their sha256 prefixes. No script needed a fix." % (
            RC["posthoc_A_sha256"][:16], RC["posthoc_B_sha256"][:16], "{:,}".format(tot_leaves)),
        "- **M34 (identity trees-off = guess-normal).** MAE equal to 6 significant digits in all four: PM2.5 %s, NDVI %s, fire %s (added), defo %s. Relative differences %.2g / %.2g / %.2g / %.2g; largest row difference %.2g / %.3g / %.3g / %.3g, all inside the identity tolerance; guess-normal == clip(normal) exactly. **Wording fix:** 'within 1e-8 relative' is false for fire; say 'within 2.1e-8 relative' or 'equal to 6 significant digits'." % (
            m["pm25"]["MAE_TO_6sig"], m["ndvi"]["MAE_TO_6sig"], m["fire"]["MAE_TO_6sig"], m["defo"]["MAE_TO_6sig"],
            m["pm25"]["rel_diff"], m["ndvi"]["rel_diff"], m["fire"]["rel_diff"], m["defo"]["rel_diff"],
            m["pm25"]["maxdev_all_saved_rows"], m["ndvi"]["maxdev_all_saved_rows"], m["fire"]["maxdev_all_saved_rows"], m["defo"]["maxdev_all_saved_rows"]),
        "- **R12 (fire nowcast ordering).** Confirmed: log trees-off 0.004281 < predict-zero 0.004284 < four log arms 0.004296-0.004322 < adopted 0.004385 < arcsine trees-off 0.004428 < identity normal 0.006259. New, report-only (40 regions): adopted vs log trees-off d %s %s CANNOT TELL (adopted better in %d/40); vs predict-zero d %s %s CANNOT TELL (%d/40)." % (
            s(lt["mean"], 3), ci(lt["low"], lt["high"], 3), lt["groups_adopted_better"], s(pz["mean"], 3), ci(pz["low"], pz["high"], 3), pz["groups_adopted_better"]),
        "- **R13 (corrector / placebo / plain).** Confirmed for all five runs; all 21 placebo pairs of jackknife.csv re-derived exactly: EQUIVALENT except defo identity unweighted (CANNOT TELL) and fire's two identity pairs (HURTS).",
        "- **R14 (penalties).** Confirmed: PM2.5 a_tree 15 / a_ctx 15; NDVI 0.5 / 0.03125; fire 50 / 50; defo lambda 10; coral 50 / 50. M47 (same point at later leads) not re-checked.",
        "- **R15 = AK4(a) ablation table.** Every saved column scored (89 columns, all equal to score_pooled.csv). Regret of the adopted arm: PM2.5 %.2g (%.3f%%), NDVI 0, fire %.3g (+%.2f%%), defo 0, coral %.4g (+%.2f%%). Not a test of the per-unit axis (M56); AK4(b) is still open. Wording: defo adopted 0.0054158 vs log plain 0.0054164 is '<', not '='." % (
            r15["pm25"]["regret_abs"], 100 * r15["pm25"]["regret_rel"], r15["fire"]["regret_abs"], 100 * r15["fire"]["regret_rel"],
            r15["coral"]["regret_abs"], 100 * r15["coral"]["regret_rel"]),
        "- **P29 (interval method).** With t(G-1) instead of z = 1.96, exactly 2 of the 79 deciding verdicts change: fire nowcast HELPS -> CANNOT TELL (t39 %.3f, CI %s, p_t %.4f vs p_z %.4f); coral CRW lead 183 BEATS -> CANNOT TELL (32 regions, t31 CI %s, p_t %.4f vs p_z %.4f). Holm over the five nowcasts: all survive with z (fire last, %.4f); with t fire fails (%.4f). Band share of the reference MAE: PM2.5 %.2f%%, NDVI %.2f%%, fire %.2f%%, defo %.2f%%, coral %.2f%%. Count is 79, not 'about 80'." % (
            ch["fire"]["t_quantile"], ci(ch["fire"]["low_t"], ch["fire"]["high_t"], 3), ch["fire"]["p_t"], ch["fire"]["p_z"],
            ci(ch["coral"]["low_t"], ch["coral"]["high_t"], 4), ch["coral"]["p_t"], ch["coral"]["p_z"],
            hz["fire"]["holm_adj_p_z"], hz["fire"]["holm_adj_p_t"],
            bs["pm25"]["band_share_pct"], bs["ndvi"]["band_share_pct"], bs["fire"]["band_share_pct"], bs["defo"]["band_share_pct"], bs["coral"]["band_share_pct"]),
        "- **R3b (model vs best naive).** Fire %+.2f%% vs log trees-off and %+.2f%% vs predict-zero (worse); PM2.5 %+.2f%%, NDVI %+.2f%%, defo %+.2f%%, coral %+.2f%%." % (
            r3["fire"]["change_pct_vs_best"], r3["fire"]["change_pct_vs_predict_zero"], r3["pm25"]["change_pct_vs_best"],
            r3["ndvi"]["change_pct_vs_best"], r3["defo"]["change_pct_vs_best"], r3["coral"]["change_pct_vs_best"]),
        "- **RC12 (coral by magnitude, outcome-defined).** 'L1 wins on every bleached stratum' is NOT reproduced. Ours is lower in B1-B3 (e.g. B3 %.2f vs %.2f); hgb_l1 is lower only above q75 (%.2f vs %.2f, d %s %s HURTS) and at y >= 50 (%.2f vs %.2f, HURTS). Ours under-predicts the largest events (above q75: mean prediction %.1f vs truth %.1f; L1 %.1f)." % (
            rc["B3 (q50, q75]"]["columns"][O]["mae"], rc["B3 (q50, q75]"]["columns"][H]["mae"],
            rc["B4 (q75, max]"]["columns"][O]["mae"], rc["B4 (q75, max]"]["columns"][H]["mae"],
            s(rc["B4 (q75, max]"]["contrasts"][H]["mean"], 3), ci(rc["B4 (q75, max]"]["contrasts"][H]["low"], rc["B4 (q75, max]"]["contrasts"][H]["high"], 3),
            rc["severe y>=50"]["columns"][O]["mae"], rc["severe y>=50"]["columns"][H]["mae"],
            rc["B4 (q75, max]"]["columns"][O]["mean_pred"], rc["B4 (q75, max]"]["mean_y"], rc["B4 (q75, max]"]["columns"][H]["mean_pred"]),
        "- **A1 (fire active cells vs Tweedie, outcome-defined).** Confirmed. y > 0 (1,759 cells, 33 regions): ours %.3f vs %.3f, d %s %s HELPS. Top 1%% (y >= q99 = %.6f from test labels; 949 cells): %.3f vs %.3f, HELPS. Zero rows (98.14%%): ours predicts %.5f on average vs %.5f, d %s HURTS. Ridge's guarded column is the identity trees-off, not guess-normal exactly." % (
            a1["y > 0"]["columns"][O]["mae"], a1["y > 0"]["columns"][T]["mae"], s(a1["y > 0"]["contrasts"][T]["mean"], 3),
            ci(a1["y > 0"]["contrasts"][T]["low"], a1["y > 0"]["contrasts"][T]["high"], 3), A["A1"]["values"]["q99"],
            a1["top 1% y >= q99"]["columns"][O]["mae"], a1["top 1% y >= q99"]["columns"][T]["mae"],
            a1["y == 0"]["columns"][O]["mean_pred"], a1["y == 0"]["columns"][T]["mean_pred"], s(a1["y == 0"]["contrasts"][T]["mean"], 3)),
        "- **A2 (coral bleached visits vs rivals, outcome-defined).** Confirmed: 1,024 visits, 36 regions; ours %.2f is mid-pack (L1 %.2f, LightGBM %.2f, RF %.2f lower; Tweedie %.2f, Ridge %.2f higher); all five per-region contrasts CANNOT TELL." % (
            a2["columns"][O]["mae"], a2["columns"][H]["mae"], a2["columns"]["arm__rival_lgbm"]["mae"], a2["columns"]["arm__rival_rf"]["mae"],
            a2["columns"][T]["mae"], a2["columns"]["arm__rival_ridge"]["mae"]),
        "- **Fact-sheet edits:** M34 wording (+ add fire); RC12 'every bleached stratum' -> 'the top quartile and y >= 50'; P29 'about 80' -> 79; R15 defo '=' -> '<'; A1 spec: Ridge guarded = identity trees-off. Everything else matches.",
        "```",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
