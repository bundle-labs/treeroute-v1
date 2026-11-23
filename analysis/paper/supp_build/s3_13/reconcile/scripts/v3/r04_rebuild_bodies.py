# r04: the reconciler's own re-derivation of every table body cell of tables.md (Table 9, S3.18 a, S3.19-S3.30)
# and of the note lines with data placeholders, from the sources of TABLE_SPEC.md section 1, by the spec's
# cell rules (written here independently of both builders). Compares cell by cell with OUT\A\tables.md.
# Read-only; prints a summary and every difference.
# Version 2 (2026-11-17): only the four constant texts that the change order rewords and that this script
# re-derives were changed, to the order's NEW texts: S3.20 note b (C2), the S3.24 double-dagger note (C3), the
# S3.22 row label (C5) and E10's "What it checks" (C6). The original is kept as scripts\v1\r04_rebuild_bodies.py.
# Version 3 (2026-11-17): only the constant texts that the version-3 change order rewords and that this script
# re-derives were changed, to the order's NEW texts: treeroute's skill-guard cell of S3.18 a and S3.20, the random
# forest's method, the S3.21 first row label and the "What it checks" texts of E3a, E3m, E3, E6 and E10, and the
# printed words P of the S3.25 Link cells, the source label still being tested with M (V3-6); the S3.22 row label
# (V3-5); the second sentence of the S3.24 double-dagger note (V3-4). Version 2 is kept as scripts\v2\.
import sys, re, json, math, itertools, collections, hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F401,F403
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
selftest()
text = (OUT / "A" / "tables.md").read_text(encoding="utf-8")
LINES, TABLES, NOTES = parse_tables(text)
A = load_json(V / "A" / "results.json", strict=True)
DAG, DDAG, SECT = "†", "‡", "§"
SA, SB, SC, SD = "ᵃ", "ᵇ", "ᶜ", "ᵈ"

PL, AW4, PAIRS, IMP, FAM, META, EX, REX, GATES, MAN = {}, {}, {}, {}, {}, {}, {}, {}, {}, {}
for p in PROBS:
    PL[p] = load_json(comp(p) / "per_lead.json")
    AW4[p] = load_json(comp(p) / "AW4_main_row.json")
    PAIRS[p] = pd.read_parquet(comp(p) / "pairs.parquet")
    IMP[p] = pd.read_parquet(comp(p) / "importance.parquet")
    FAM[p] = pd.read_parquet(comp(p) / "families.parquet")
    GATES[p] = load_json(SHAP / "rebuild" / p / "lead_0" / "gates.json")
    MAN[p] = load_json(SHAP / "sample" / p / "sample_manifest.json")
    for m in PL[p]["models"]:
        META[(p, m)] = load_json(model_dir(p, m) / "meta.json")
        f = model_dir(p, m) / "exactness.json"
        if f.exists():
            EX[(p, m)] = load_json(f)
        f = model_dir(p, m) / "ridge_shap_exactness.json"
        if f.exists():
            REX[(p, m)] = load_json(f)
REG = {}
for i, l in enumerate((SHAP / "SAMPLE_REGISTER.txt").read_bytes().decode("utf-8").replace("\r\n", "\n").split("\n"), 1):
    if l.strip():
        kv = dict(x.split("=", 1) for x in l.split(" ")[1:])
        REG[kv["problem"]] = kv

# ---------------- section 3 checks re-run (a subset, independently) ----------------
chk = collections.Counter()
fails = []


def need(cond, what):
    chk["checks"] += 1
    if not cond:
        fails.append(what)


for p in PROBS:
    pl, man = PL[p], MAN[p]
    need(pl["rows"] == 1000 == int(REG[p]["n"]) == man["n"], "3.1 rows " + p)
    need(pl["draws"] == 2000, "3.1 draws " + p)
    need(REG[p]["sample"] == man["sha256"]["sample.parquet"] == pl["sample_sha256"], "3.1 sample hash " + p)
    for m in pl["models"]:
        need(META[(p, m)]["sample_sha256"] == pl["sample_sha256"], "3.1 meta sample hash %s %s" % (p, m))
    need(hashlib.sha256((comp(p) / "bootstrap_draws.npy").read_bytes()).hexdigest() == pl["draws_sha256"], "3.1 draws hash " + p)
    need(pl["regions"] == man["regions_in_sample"], "3.1 regions " + p)
    need("treeroute_B1" not in pl["models"], "3.2 B1 not in models " + p)
    for m in pl["models"]:
        mt = META[(p, m)]
        need(m in ORDER, "3.2 model known %s %s" % (p, m))
        need(mt["rows"] == 1000 and mt["pass"] is True and all(mt["checks_passed"][k] is True for k in ("S-ADD", "S-EVAL", "S-RESID", "S-ZERO")) and mt["structural_zero_violations"] == 0, "3.2 meta %s %s" % (p, m))
    need(GATES[p]["stopped_at"] is None, "3.2 stopped_at " + p)
    # 3.3 links share c and ub
    cs = {tuple(l.split("|")[1:]) for l in pl["links"].values()}
    need(len(cs) == 1, "3.3 c/ub " + p)
    # 3.7 main row
    if p != "fire":
        aw = AW4[p]
        kw = pl["variable"]["kendall_w_main_set"]
        need(aw["kendall_w"]["value"] == kw["value"] and aw["kendall_w"]["ci"][0:2] == kw["ci"] and aw["kendall_w"]["ci"][2] == kw["finite_replicates"], "3.7 W " + p)
        need(set(aw["models_in_main_set"]) == set(pl["main_set"]), "3.7 main set " + p)
        rivals = [m for m in pl["main_set"] if m != "treeroute"]
        df = PAIRS[p]
        vals = []
        for r in rivals:
            a, b = sorted([r, "treeroute"])
            row = df[(df.level == "variable") & (df.model_a == a) & (df.model_b == b) & (df.statistic == "spearman_top20_union")]
            vals.append(row.iloc[0]["value"].item())
        med = aw["treeroute_vs_same_link_rivals_median_spearman_top20_union"]
        need(abs(min(vals) - med["range"][0]) <= 1e-12 and abs(max(vals) - med["range"][1]) <= 1e-12 and abs(float(np.median(vals)) - med["value"]) <= 1e-12, "3.7 median " + p)
        fm = FAM[p]
        oh = [fm[(fm.model == r) & (fm.family == "own history")].iloc[0]["share"].item() for r in rivals]
        need(abs(float(np.median(oh)) - aw["own_history_share_median_rival"]["value"]) <= 1e-12, "3.7 own-history median " + p)
        if p in ("pm25", "defo"):
            lg = fm[(fm.model == "rival_lgbm") & (fm.family == "own history")].iloc[0]["share"].item()
            need(abs(lg - aw["own_history_share_median_rival"]["value"]) <= 1e-12, "3.7 lgbm median " + p)
        if p == "ndvi":
            s = sorted(oh)
            need(len(s) == 4 and abs((s[1] + s[2]) / 2 - aw["own_history_share_median_rival"]["value"]) <= 1e-12, "3.7 ndvi mean of middle two")
    else:
        aw = AW4[p]
        need(aw["models_in_main_set"] == ["treeroute"] and aw["cross_link_models"] == ["rival_lgbm", "rival_lgbm_tweedie", "rival_rf"] and aw["declined_models"] == ["rival_ridge"], "3.7 fire lists")
        need(math.isnan(aw["kendall_w"]["value"]) and math.isnan(aw["kendall_w"]["ci"][0]) and math.isnan(aw["kendall_w"]["ci"][1]) and aw["kendall_w"]["ci"][2] == 0, "3.7 fire W")

# ---------------- helpers ----------------
def mlist(ms):
    ms = [m for m in ORDER if m in ms]
    return ", ".join(INLINE[m] for m in ms) if ms else "none"


def nlist(names):
    return ", ".join("`" + n + "`" for n in names)


def linkd(s):
    return LINKDISP[s.split("|")[0]]


def prow(p, L, a, b, s):
    df = PAIRS[p]
    x, y = sorted([a, b])
    r = df[(df.level == L) & (df.model_a == x) & (df.model_b == y) & (df.statistic == s)]
    if len(r) != 1:
        raise Stop("pairs row %s %s %s %s %s: %d" % (p, L, x, y, s, len(r)))
    r = r.iloc[0]
    return {k: (nan2none(r[k].item()) if hasattr(r[k], "item") else r[k]) for k in r.index}


def ci_aw(o):
    return CI2(nan2none(o["value"]), nan2none(o["ci"][0]), nan2none(o["ci"][1]), o["ci"][2])


def ci_a(o):
    return CI2(o["value"], o["ci_low"], o["ci_high"], o["n_finite"])


def ranking(p, L, m):
    df = IMP[p]
    sub = df[(df.level == L) & (df.model == m) & (df.active)]
    rows = sorted(((-r.mean_abs, r.player, r.share) for r in sub.itertuples()), key=lambda t: (t[0], t[1]))
    return [(pl_, sh) for _, pl_, sh in rows]


def fam_share(p, m, f):
    fm = FAM[p]
    r = fm[(fm.model == m) & (fm.family == f)]
    if len(r) != 1:
        raise Stop("families %s %s %s" % (p, m, f))
    return r.iloc[0]["share"].item()


def empty_family(p, f):
    return f not in set(PL[p]["families"].values())


# ---------------- expected tables ----------------
EXP = {}   # (tid, panel) -> list of rows (lists of cells)
ENOTE = {}  # (tid, key) -> note line text (data notes only)

# Table 9
rows = []
for p in PROBS:
    aw = AW4[p]
    if p == "fire":
        fm = A["problems"]["fire"]["main_row"]
        rows.append([PDISP[p], "treeroute v1 only" + SA, "undefined" if not finite(nan2none(aw["kendall_w"]["value"])) else "?", ENDASH, ENDASH,
                     nlist([x[0] for x in fm["treeroute_top3"]]) + DAG, ENDASH, ci_a(fm["own_history_share_treeroute"]) + DAG, ENDASH])
        continue
    med = aw["treeroute_vs_same_link_rivals_median_spearman_top20_union"]
    lab = " (no own-history input)" if p == "coral" else ""
    rows.append([PDISP[p], mlist(aw["models_in_main_set"]), ci_aw(aw["kendall_w"]),
                 ci_aw(med) + " (" + NUM2(med["range"][0]) + " to " + NUM2(med["range"][1]) + ")",
                 ci_aw(aw["rbo_vs_consensus_p0.9"]) + (SB if p == "pm25" else ""),
                 nlist(aw["treeroute_top3"]), nlist(aw["consensus_top3"]),
                 ci_aw(aw["own_history_share_treeroute"]) + lab, ci_aw(aw["own_history_share_median_rival"]) + lab])
EXP[("9", "")] = rows

# Table S3.18 a
METHOD = {"treeroute": "the adopted arm: tree bank and router; exact interventional TreeSHAP of the trees, router terms exactly linear",
          "rival_ridge": "ridge regression; exact linear SHAP",
          "rival_rf": "random forest, rebuilt from the rival board's records; exact interventional TreeSHAP",
          "rival_lgbm": "LightGBM; exact interventional TreeSHAP",
          "rival_lgbm_tweedie": "LightGBM with a Tweedie loss; exact interventional TreeSHAP",
          "rival_hgb_l1": "gradient booster on absolute error; exact interventional TreeSHAP",
          "rival_bardl_h1": "published rain-lag Bayesian distributed-lag model, per location; exact linear SHAP over its nine input columns"}
rows = []
for p in PROBS:
    pl = PL[p]
    for m in [x for x in ORDER if x in pl["models"]]:
        guard = "passed (the adopted arm)" if m == "treeroute" else ("passed" if META[(p, m)]["guard"]["passed"] is True else "failed" + SA)
        if m in pl["main_set"]:
            inm = "yes"
        else:
            rs = []
            if pl["links"][m] != pl["links"]["treeroute"]:
                rs.append("another link")
            if m in pl["declined_by_guard"]:
                rs.append("skill guard failed")
            inm = "no: " + "; ".join(rs)
        rows.append([PDISP[p], INLINE[m] + " (`" + m + "`)", METHOD[m], linkd(pl["links"][m]), guard, inm])
EXP[("S3.18", "a")] = rows

# Table S3.19 and its notes
rows = []
for p in PROBS:
    man, pl = MAN[p], PL[p]
    b = man["background_rows"]["0"]
    bg = COUNT(b["min"]) if b["min"] == b["max"] else COUNT(b["min"]) + ENDASH + COUNT(b["max"]) + " (median " + MED(b["median"]) + ")"
    lv = lambda L: COUNT(pl[L]["players"]) + " / " + COUNT(pl[L]["active"]) + " / " + COUNT(len(pl[L]["structural_zero"]))  # noqa: E731
    rows.append([PDISP[p], COUNT(man["frame_rows"]), COUNT(int(REG[p]["n"])), COUNT(man["regions_in_sample"]), COUNT(man["units_in_sample"]),
                 bg, COUNT(META[(p, "treeroute")]["pairs"]), lv("feature"), lv("variable")])
    ENOTE[("S3.19", p)] = "%s: variable level (%s) %s; feature level (%s) %s." % (
        PDISP[p], COUNT(len(pl["variable"]["structural_zero"])), nlist(pl["variable"]["structural_zero"]),
        COUNT(len(pl["feature"]["structural_zero"])), nlist(pl["feature"]["structural_zero"]))
EXP[("S3.19", "")] = rows

# Table S3.20 and note b
rows = []
for p in PROBS:
    for m in [x for x in ORDER if x in PL[p]["models"]]:
        ridge_loader = (m == "rival_ridge" and p in ("fire", "pm25", "defo", "ndvi"))
        if m == "treeroute":
            e8 = GATES[p]["gates"]["E8_predictions"]["values"]
            n, pre, clip, mx = e8["rows_checked"], e8["pre_bit_equal"], e8["arm_bit_equal"], e8["max_abs_pre"]
            if e8["bit_identical"] is True:
                sx = "bit-identical"
            else:
                need(e8["within_relative_tolerance"] is True and e8["rows_outside_tolerance"] == 0, "S3.20 D8 " + p)
                sx = "within the D8 tolerance" + SC + " (largest relative difference " + SCI2(e8["max_rel_pre"]) + ")"
        else:
            rec = REX[(p, m)] if ridge_loader else EX[(p, m)]
            n, pre, mx = rec["rows"], rec["bit_equal_rows"], rec["max_abs_diff"]
            clip = rec["raw"]["bit_equal_rows"] if (ridge_loader or "raw" in rec) else None
            need(rec["pass"] is True and pre == n and (clip is None or clip == n), "S3.20 rival exact %s %s" % (p, m))
            if ridge_loader:
                need(REX[(p, m)]["stage"] == "bits" and EX[(p, m)]["pass"] is False, "3.2 ridge records " + p)
            sx = "bit-identical"
        mt = META[(p, m)]
        guard = "passed (the adopted arm)" if m == "treeroute" else ("passed" if mt["guard"]["passed"] is True else "failed" + SD)
        rows.append([PDISP[p], INLINE[m] + (SB if ridge_loader else ""), COUNT(n), COUNT(pre) + " / " + (COUNT(clip) if clip is not None else ENDASH),
                     SCI2(mx), sx, SCI2(mt["max_abs_additivity_error"]) + " / " + SCI2(mt["max_abs_additivity_error_variable"]),
                     COUNT(mt["structural_zero_violations"]), "all passed", guard])
EXP[("S3.20", "")] = rows
rb = {p: (COUNT(EX[(p, "rival_ridge")]["bit_equal_rows"]), COUNT(EX[(p, "rival_ridge")]["rows"])) for p in ("pm25", "ndvi", "fire", "defo")}
ENOTE[("S3.20", "b")] = ("ᵇ Ridge outside coral bleaching is explained by a loader that repeats the rival board's own block-wise scoring, which reproduces every saved prediction. "
                         "The rivals' SHAP script's own check of its row-by-row copy of the design, kept as a record, matched %s of %s rows on PM2.5, %s of %s on NDVI, %s of %s on burned fraction and %s of %s on forest loss, because that copy adds the same terms in another order."
                         % (rb["pm25"] + rb["ndvi"] + rb["fire"] + rb["defo"]))

# Table S3.21
GATE_ROWS = ["Adopted arm", "E1", "E2", "E0", "E3a", "E3m", "E3", "E4", "E5" + SA, "E5a", "E6", "E7", "E9", "E8", "E10"]
WHAT = {"Adopted arm": "link, answer type and weighting; router type", "E1": "engine code hash equals the run manifest's",
        "E2": "library versions and Python equal the manifest's", "E0": "the engine's RAM pre-flight predicts no refusal",
        "E3a": "inputs, before the labels are read, equal the manifest's (dataset package, regions, constants, file lists, features)",
        "E3m": "a moved dataset package file has the content, size and time that the run's locks record (path map)",
        "E3": "dataset package fingerprint, the settings that the written rules set, and run fingerprint, after the written rules are applied",
        "E4": "training rows: count and row-key hash",
        "E5" + SA: "bank fingerprint over every tree array (informational)",
        "E5a": "arcsine arm only: its identity-link twin is bit-identical on every checked row",
        "E6": "c and the identity tolerances (one per link) equal the run's records", "E7": "error-weighted arm only: the error-weight model equals its record",
        "E9": "captured router coefficients reproduce the engine's kernel bit for bit",
        "E8": "kept predictions, pre-clip and clipped, on every test row of every sampled location",
        "E10": "exported trees and evaluator reproduce the engine's tree answers bit for bit, on one sampled location's router fit rows and test rows (forest loss: every sampled location; coral bleaching: one survey visit's router fit rows and test row)"}
GKEY = {"E1": "E1_engine_code", "E2": "E2_versions", "E0": "E0_ram_preflight", "E3a": "E3a_inputs_before_read", "E3m": "E3m_recorded_path_map",
        "E3": "E3_inputs", "E4": "E4_donor_rows", "E5" + SA: "E5_bank_fingerprint", "E5a": "E5a_identity_twin", "E6": "E6_c_and_tolerances",
        "E7": "E7_gls_weight_model", "E9": "E9_coefficients_reproduce_the_kernel", "E8": "E8_predictions", "E10": "E10_exported_trees"}
rows = []
for g in GATE_ROWS:
    r = [g, WHAT[g]]
    for p in PROBS:
        G, R = GATES[p]["gates"], GATES[p]["result"]
        if g == "Adopted arm":
            r.append(LINKDISP[R["link"]] + ", " + {"plain": "plain answers", "corrector": "corrected answers"}[R["table_kind"]] + ", "
                     + ("error-weighted" if R["weighted"] is True else "uniformly weighted") + "; "
                     + {"per_unit": "per-location router", "region": "region router", "neighbour": "neighbour router"}[R["kind"]])
            continue
        key = GKEY[g]
        if key in G:
            need(G[key]["pass"] is (key != "E5_bank_fingerprint"), "3.10 pass %s %s" % (p, key))
        Vv = G[key]["values"] if key in G else None
        if g in ("E1", "E2", "E3a", "E3", "E6"):
            r.append("passed")
        elif g == "E0":
            r.append("passed (warning overridden)" if Vv["ignored"] is True else "passed")
        elif g == "E3m":
            need((key in G) == (G["E3a_inputs_before_read"]["values"]["path_map"] is True), "3.10 E3m presence " + p)
            if key in G:
                need(all(f["equal"] is True for f in Vv["files"]), "3.10 E3m files " + p)
                n = len(Vv["files"])
                r.append("passed (" + COUNT(n) + (" file)" if n == 1 else " files)"))
            else:
                r.append("not used (no moved file)")
        elif g == "E4":
            need(Vv["rows"][0] == Vv["rows"][1] and Vv["row_key_hash"][0] == Vv["row_key_hash"][1], "3.10 E4 " + p)
            r.append("passed (" + COUNT(Vv["rows"][0]) + " rows)")
        elif g == "E5" + SA:
            r.append("differs (informational)")
        elif g == "E5a":
            need((key in G) == (R["link"] == "arcsine"), "3.10 E5a presence " + p)
            if key in G:
                need(Vv["pre_bit_equal"] == Vv["rows_checked"] == Vv["arm_bit_equal"], "E5a counts " + p)
                r.append("passed (" + COUNT(Vv["pre_bit_equal"]) + " of " + COUNT(Vv["rows_checked"]) + " rows)")
            else:
                r.append("not applicable")
        elif g == "E7":
            need((key in G) == (R["weighted"] is True), "3.10 E7 presence " + p)
            r.append("passed" if key in G else "not applicable")
        elif g == "E9":
            need(Vv["fits_whose_X_b_differs_from_the_kernel"] == 0, "3.10 E9 " + p)
            if Vv["region_proof"] is None:
                r.append("passed (all " + COUNT(Vv["fits_captured"]) + " fits)")
            else:
                rp = Vv["region_proof"]
                need(rp["answers_equal"] is True and rp["eta_ours_equal"] is True and rp["eta_store_equal"] is True and not rp["errors"], "E9 region proof " + p)
                r.append("passed (all " + COUNT(Vv["fits_captured"]) + " region fits; region proof on " + COUNT(rp["score_rows"]) + " score rows and "
                         + COUNT(rp["background_rows"]) + " background rows)")
        elif g == "E8":
            if Vv["bit_identical"] is True:
                r.append("bit-identical (" + COUNT(Vv["pre_bit_equal"]) + " of " + COUNT(Vv["rows_checked"]) + " rows)")
            else:
                r.append(COUNT(Vv["pre_bit_equal"]) + " of " + COUNT(Vv["rows_checked"]) + " rows bit-identical; the rest within the D8 tolerance (largest relative difference "
                         + SCI2(Vv["max_rel_pre"]) + ")")
        elif g == "E10":
            if "rows_x_trees" in Vv:
                r.append("passed (" + COUNT(Vv["rows_x_trees"][0]) + " rows, " + COUNT(Vv["rows_x_trees"][1]) + " trees)")
            else:
                r.append("passed (every sampled location of the " + COUNT(Vv["regions"]) + " regions)")
    rows.append(r)
EXP[("S3.21", "")] = rows
for p in PROBS:
    R = GATES[p]["result"]
    need(META[(p, "treeroute")]["arm"] == "%s_%s_%s" % (R["link"], R["table_kind"], "gls" if R["weighted"] else "unweighted"), "3.10 arm " + p)

# Table S3.22
QROWS = ["Link of the main set", "Main set", "Rivals in another link that passed their skill guard", "Rivals declined by their skill guard", "Kendall's W of the main set [95% CI]",
         "Spearman of treeroute v1 with each same-link rival", "Median of those [95% CI]", "Range (lowest to highest)",
         "RBO with the rivals' consensus, p = 0.9 [95% CI]", "treeroute v1's top 3", "Consensus top 3", "Own-history share, treeroute v1 [95% CI]",
         "Own-history share of each same-link rival", "Own-history share, median of the rivals" + SC + " [95% CI]"]
cols = {}
for p in PROBS:
    aw = AW4[p]
    rivals = [m for m in ORDER if m in aw["models_in_main_set"] and m != "treeroute"]
    lab = " (no own-history input)" if p == "coral" else ""
    c = {"Link of the main set": linkd(aw["reference_link"]),
         "Main set": ("treeroute v1 only" + SA) if p == "fire" else mlist(aw["models_in_main_set"]),
         "Rivals in another link that passed their skill guard": mlist(aw["cross_link_models"]), "Rivals declined by their skill guard": mlist(aw["declined_models"])}
    if p == "fire":
        fm = A["problems"]["fire"]["main_row"]
        c["Kendall's W of the main set [95% CI]"] = "undefined"
        for q in ("Spearman of treeroute v1 with each same-link rival", "Median of those [95% CI]", "Range (lowest to highest)",
                  "RBO with the rivals' consensus, p = 0.9 [95% CI]", "Consensus top 3", "Own-history share of each same-link rival",
                  "Own-history share, median of the rivals" + SC + " [95% CI]"):
            c[q] = ENDASH
        c["treeroute v1's top 3"] = nlist([x[0] for x in fm["treeroute_top3"]]) + DAG
        c["Own-history share, treeroute v1 [95% CI]"] = ci_a(fm["own_history_share_treeroute"]) + DAG
    else:
        med = aw["treeroute_vs_same_link_rivals_median_spearman_top20_union"]
        c["Kendall's W of the main set [95% CI]"] = ci_aw(aw["kendall_w"])
        c["Spearman of treeroute v1 with each same-link rival"] = "; ".join(INLINE[r] + " " + NUM2(prow(p, "variable", r, "treeroute", "spearman_top20_union")["value"]) for r in rivals)
        c["Median of those [95% CI]"] = ci_aw(med)
        c["Range (lowest to highest)"] = NUM2(med["range"][0]) + " to " + NUM2(med["range"][1])
        c["RBO with the rivals' consensus, p = 0.9 [95% CI]"] = ci_aw(aw["rbo_vs_consensus_p0.9"]) + (SB if p == "pm25" else "")
        c["treeroute v1's top 3"] = nlist(aw["treeroute_top3"])
        c["Consensus top 3"] = nlist(aw["consensus_top3"])
        c["Own-history share, treeroute v1 [95% CI]"] = ci_aw(aw["own_history_share_treeroute"]) + lab
        c["Own-history share of each same-link rival"] = "; ".join(INLINE[r] + " " + NUM2(fam_share(p, r, "own history")) for r in rivals) + lab
        c["Own-history share, median of the rivals" + SC + " [95% CI]"] = ci_aw(aw["own_history_share_median_rival"]) + lab
    cols[p] = c
EXP[("S3.22", "")] = [[q] + [cols[p][q] for p in PROBS] for q in QROWS]

# Tables S3.23-S3.27
TID = {"pm25": "S3.23", "ndvi": "S3.24", "fire": "S3.25", "defo": "S3.26", "coral": "S3.27"}
STATS_V = ["spearman", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10", "rbo_p0.9", "rbo_p0.95", "tvd"]
rank = {m: i for i, m in enumerate(ORDER)}
sign_stats = collections.Counter()
for p in PROBS:
    tid, pl = TID[p], PL[p]
    models = [m for m in ORDER if m in pl["models"]]
    pairs = sorted(itertools.combinations(models, 2), key=lambda t: (rank[t[0]], rank[t[1]]))
    for pan, L in (("a", "variable"), ("b", "feature")):
        has20 = L == "feature" and pl["feature"]["active"] >= 200
        stats = STATS_V[:5] + (["jaccard_top20"] if has20 else []) + STATS_V[5:]
        rows = []
        for a, b in pairs:
            pt = INLINE[a] + " vs " + INLINE[b] + (DDAG if (p == "ndvi" and "rival_bardl_h1" in (a, b)) else "")
            lab = prow(p, L, a, b, "spearman")["pair_label"]
            labs = {prow(p, L, a, b, s)["pair_label"] for s in stats + ["sign_agreement_top10"]}
            need(len(labs) == 1, "one label per pair-level %s %s %s %s" % (p, L, a, b))
            M = "; raw model, declined by its guard: "
            P = "; raw model, declined by its skill guard: "
            if M in lab:
                pre, nm = lab.split(M)
                lab = pre + P + ", ".join(INLINE[x] for x in nm.split(", "))
            cells = [pt, lab]
            for s in stats:
                r = prow(p, L, a, b, s)
                cells.append(CI2(r["value"], r["ci_low"], r["ci_high"], r["finite_replicates"]))
                if r["finite_replicates"] < D:
                    sign_stats["pair statistic with fewer than 2000 finite draws"] += 1
            r = prow(p, "variable", a, b, "tvd_family")
            cells.append(CI2(r["value"], r["ci_low"], r["ci_high"], r["finite_replicates"]))
            r = prow(p, L, a, b, "sign_agreement_top10")
            x, y = sorted([a, b])
            sa = A["problems"][p]["levels"][L]["pairs"][x + "|" + y]
            S = sa["sign_agreement"]
            need((S["value"] is None and r["value"] is None) or (S["value"] is not None and r["value"] is not None and abs(S["value"] - r["value"]) <= 1e-12), "3.4 value %s %s %s" % (p, L, x + y))
            need(sa["sign_n_determined"]["value"] == r["signs_compared"], "3.4 count %s %s %s" % (p, L, x + y))
            need((S["n_finite"] > 0) == (S["ci_low"] is not None and S["ci_high"] is not None), "3.4 ci presence")
            cells.append(SIGN(r["value"], r["signs_compared"], S["ci_low"], S["ci_high"], S["n_finite"]))
            rows.append(cells)
        EXP[(tid, pan)] = rows
    rows = []
    for q, key in (("Kendall's W of the main set [95% CI]", "kendall_w_main_set"), ("Mean pairwise Spearman of the main set [95% CI]", "mean_pairwise_spearman_main_set")):
        cl = [q]
        for L in ("variable", "feature"):
            o = pl[L][key]
            t = CI2(nan2none(o["value"]), nan2none(o["ci"][0]), nan2none(o["ci"][1]), o["finite_replicates"])
            if p == "fire":
                need(t == "undefined", "fire panel c undefined")
                t += SA
            cl.append(t)
        rows.append(cl)
    for m in models:
        rows.append(["Stability under region resampling: " + INLINE[m]] + [NUM2(pl[L]["stability_under_region_resampling"][m]) for L in ("variable", "feature")])
    EXP[(tid, "c")] = rows
    for pan, L, last in (("d", "variable", "Nonzero variables"), ("e", "feature", "Nonzero players")):
        rk = {m: ranking(p, L, m) for m in models}
        rows = [[str(k)] + [TOP(*rk[m][k - 1]) for m in models] for k in range(1, 11)]
        rows.append([last] + [COUNT(pl[L]["nonzero_players"][m]) for m in models])
        EXP[(tid, pan)] = rows
        if L == "variable":
            for m in models:
                if m == "treeroute":
                    pass
    rows = []
    for fname, f in zip(["Own history", "Global indices", "Local drivers", "Context and calendar", "Seasonal normal"], FAMS):
        rows.append([fname] + [PCT1(fam_share(p, m, f)) + ((" " + FAMLABEL[f]) if empty_family(p, f) else "") for m in models])
    EXP[(tid, "f")] = rows
    nz = pl["nonzero_forecast_rows"]
    if nz:
        gm = [m for m in ORDER if m in nz]
        rows = [[str(k)] + [TOP(nz[m]["top10"][k - 1][0], nz[m]["top10"][k - 1][1]) for m in gm] for k in range(1, 11)]
        rows.append(["Rows with a forecast above 0"] + [COUNT(nz[m]["rows"]) for m in gm])
        EXP[(tid, "g")] = rows
# 3.5: treeroute's first three equal AW4 / A
for p in PROBS:
    top3 = [x[0] for x in ranking(p, "variable", "treeroute")[:3]]
    if p == "fire":
        need(top3 == [x[0] for x in A["problems"]["fire"]["main_row"]["treeroute_top3"]], "3.5 fire top3")
        need(abs(A["problems"]["fire"]["main_row"]["own_history_share_treeroute"]["value"] - fam_share("fire", "treeroute", "own history")) <= 1e-12, "3.5 fire own history")
    else:
        need(top3 == AW4[p]["treeroute_top3"], "3.5 top3 " + p)
# 3.6 empty families
emp = sorted((p, f) for p in PROBS for f in FAMS if empty_family(p, f))
need(emp == [("coral", "own history"), ("defo", "context and calendar")], "3.6 empty families %r" % (emp,))
for p, f in emp:
    need(all(fam_share(p, m, f) == 0.0 for m in PL[p]["models"]), "3.6 zero shares")

# ndvi note (BB3)
raw = (V / "_lead" / "outputs" / "bardl_maxima.txt").read_bytes().decode("utf-8")
ML = raw.lstrip("﻿").replace("\r\n", "\n").split("\n")
need(ML[0] == "== BARDL pair-levels", "maxima header")
MAXL = re.compile(r"^\s+(jaccard_top5|jaccard_top10|jaccard_top20|rho20|rbo090|rbo095)\s+spread ([0-9.]+) -> \S+ \(3 sig\. \S+\) at (\w+)/(\w+)/(\S+); values ([0-9.\-]+) / ([0-9.\-]+) / ([0-9.\-]+)$")
mx = {}
for l in ML[1:7]:
    m = MAXL.match(l)
    need(m is not None, "maxima line " + l)
    need(m.group(1) not in mx, "maxima twice")
    mx[m.group(1)] = m
need(set(mx) == {"jaccard_top5", "jaccard_top10", "jaccard_top20", "rho20", "rbo090", "rbo095"}, "maxima six")


def at(m):
    a, b = m.group(5).split("|")
    a, b = sorted([a, b], key=lambda x: rank[x])
    return ("variable level" if m.group(4) == "variable" else "feature level") + ", " + INLINE[a] + " vs " + INLINE[b]


j5 = mx["jaccard_top5"]
a_, b_ = j5.group(5).split("|")
need(abs(float(j5.group(6)) - prow("ndvi", j5.group(4), a_, b_, "jaccard_top5")["value"]) <= 1e-9, "3.9 jaccard top5 value")
pln = PL["ndvi"]
need(pln["variable"]["nonzero_players"]["rival_bardl_h1"] == 3 and pln["feature"]["nonzero_players"]["rival_bardl_h1"] == 9, "3.9 bardl nonzero")
bt5 = ranking("ndvi", "variable", "rival_bardl_h1")[:5]
need("aet_total_mm" in [x[0] for x in bt5] and dict(bt5)["aet_total_mm"] == 0.0, "3.9 aet in top5")
ENOTE[("S3.24", "ddag")] = (
    DDAG + " BARDL reads three variables (nine columns) by design and gives exactly 0 to the other %s of the %s variables of J (%s of the %s players at the feature level). "
    "Beyond its three variables (variable level) and nine columns (feature level), its ranking is therefore filled by name order, the tie rule applied in code-point ascending order, and so are its top-5, top-10 and top-20 sets where they reach that far; the cells of its pairs that read that part of its ranking (the Jaccard similarities, the top-20-union Spearman and the RBO) depend on that order. "
    "Across the three orders tried (code-point ascending, as printed; case-insensitive ascending; and descending), the largest spread (highest minus lowest value) of each statistic over BARDL's eight pair-levels is: "
    "Jaccard top 5, %s (%s); Jaccard top 10, %s (%s); Jaccard top 20, %s (%s); top-20-union Spearman, %s (%s); RBO p = 0.9, %s (%s); RBO p = 0.95, %s (%s). "
    "For example, BARDL's Jaccard top 5 with treeroute v1 at the variable level is %s with the tie-only `aet_total_mm` in its top 5, and %s without it (ruling BB3)."
    % (COUNT(pln["variable"]["active"] - pln["variable"]["nonzero_players"]["rival_bardl_h1"]), COUNT(pln["variable"]["active"]),
       COUNT(pln["feature"]["active"] - pln["feature"]["nonzero_players"]["rival_bardl_h1"]), COUNT(pln["feature"]["active"]),
       NUM2(float(mx["jaccard_top5"].group(2))), at(mx["jaccard_top5"]), NUM2(float(mx["jaccard_top10"].group(2))), at(mx["jaccard_top10"]),
       NUM2(float(mx["jaccard_top20"].group(2))), at(mx["jaccard_top20"]), NUM2(float(mx["rho20"].group(2))), at(mx["rho20"]),
       NUM2(float(mx["rbo090"].group(2))), at(mx["rbo090"]), NUM2(float(mx["rbo095"].group(2))), at(mx["rbo095"]),
       NUM2(float(j5.group(6))), NUM2(float(j5.group(8)))))

# Tables S3.28-S3.30 (B1, from results.json and the logs)
B1P = ["pm25", "ndvi", "fire"]
need(A["b1"]["coral"]["status"]["numbers"] == "none" and A["b1"]["defo"]["status"]["numbers"] == "identity" and all(A["b1"][p]["status"]["numbers"] == "full" for p in B1P), "3.8 status")
need(A["b1"]["defo"]["identity"]["as_expected"] is True, "3.8 defo identity")
QB = [("n_J", None), ("n_nonzero", None), ("spearman_J", "Spearman over J"), ("spearman_top20_union", "Spearman, top-20 union"),
      ("kendall_tau_b", "Kendall's tau-b"), ("jaccard_top5", "Jaccard top 5"), ("jaccard_top10", "Jaccard top 10"), ("jaccard_top20", "Jaccard top 20"),
      ("rbo_p090", "RBO, p = 0.9"), ("rbo_p095", "RBO, p = 0.95"), ("tv_shares", "Share distance (TV)"), ("tv_family_shares", None),
      ("sign_agreement", "Sign agreement, top-10 union"), ("sign_counts", "Signs determined in both runs / of those, agreeing")]
for pan, L in (("a", "variable"), ("b", "feature")):
    rows = []
    for key, first in QB:
        if key == "n_J":
            rows.append([("Variables" if L == "variable" else "Players") + " in the pair's J"] + [COUNT(A["b1"][p][L]["pair_main_b1"]["n_J"]["value"]) for p in B1P])
        elif key == "n_nonzero":
            rows.append(["Nonzero in the B1 run"] + [COUNT(A["b1"][p][L]["importance"]["n_nonzero"]["value"]) for p in B1P])
        elif key == "jaccard_top20":
            objs = [A["b1"][p][L]["pair_main_b1"]["jaccard_top20"] for p in B1P]
            if any(o is not None for o in objs):
                rows.append([first] + [ci_a(o) if o is not None else ENDASH for o in objs])
        elif key == "tv_family_shares":
            rows.append(["Family-share distance (TV)" + ("" if L == "variable" else SECT)] + [ci_a(A["b1"][p]["variable"]["pair_main_b1"]["tv_family_shares"]) for p in B1P])
        elif key == "sign_counts":
            rows.append([first] + [COUNT(A["b1"][p][L]["pair_main_b1"]["sign_n_determined"]["value"]) + " / " + COUNT(A["b1"][p][L]["pair_main_b1"]["sign_n_agree"]["value"]) for p in B1P])
        else:
            rows.append([first] + [ci_a(A["b1"][p][L]["pair_main_b1"][key]) for p in B1P])
    EXP[("S3.28", pan)] = rows
FK = [("Own history", "own_history"), ("Global indices", "global_indices"), ("Local drivers", "local_drivers"),
      ("Context and calendar", "context_and_calendar"), ("Seasonal normal", "seasonal_normal")]
EXP[("S3.29", "a")] = [[fn] + [CIP(A["b1"][p]["variable"]["families"][fk]["value"], A["b1"][p]["variable"]["families"][fk]["ci_low"],
                                   A["b1"][p]["variable"]["families"][fk]["ci_high"], A["b1"][p]["variable"]["families"][fk]["n_finite"]) for p in B1P] for fn, fk in FK]
EXP[("S3.29", "b")] = [["Top 3 (share)"] + [", ".join(TOP(n, s) for n, s in A["b1"][p]["variable"]["top3"]) for p in B1P],
                       ["Own-history share [95% CI]"] + [ci_a(A["b1"][p]["variable"]["own_history_share"]) for p in B1P]]
for pan, L in (("c", "variable"), ("d", "feature")):
    EXP[("S3.29", pan)] = [[str(k)] + [TOP(*A["b1"][p][L]["top10"][k - 1]) for p in B1P] for k in range(1, 11)]
SETUP = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] (\w+) lead 0: (\d+) rows, (\d+) background pairs,")
DONE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] treeroute SHAP (\w+) lead 0 done in ([0-9.]+) s \(tree SHAP ([0-9.]+) s\)$")
rows = []
for p in ["pm25", "ndvi", "fire", "defo"]:
    L_ = (SHAP / "logs" / ("tr_shap_%s_lead0.log" % p)).read_bytes().decode("utf-8").replace("\r\n", "\n").split("\n")
    su = [i for i, l in enumerate(L_) if SETUP.match(l)]
    i0 = su[-1]
    m0 = SETUP.match(L_[i0])
    need(m0.group(1) >= "2026-11-15 23:06:00" and m0.group(2) == p and m0.group(3) == "1000", "3.8 setup " + p)
    dn = next(i for i in range(i0 + 1, len(L_)) if DONE.match(L_[i]))
    m1 = DONE.match(L_[dn])
    need(m1.group(2) == p, "done line problem " + p)
    run = A["b1"][p]["run"] if p != "defo" else A["b1"]["defo"]["identity"]
    b1meta = load_json(model_dir(p, "treeroute_B1") / "meta.json")
    b1done = load_json(model_dir(p, "treeroute_B1") / "rows.parquet.done.json")
    need(int(m0.group(4)) == run["pairs_log"] == b1meta["pairs"], "3.8 pairs " + p)
    need(float(m1.group(3)) == run["total_seconds_log"] == b1done["seconds"], "3.8 total seconds " + p)
    need(float(m1.group(4)) == run["tree_shap_seconds_log"] == b1meta["tree_shap_seconds"], "3.8 tree seconds " + p)
    need(b1meta["sample_sha256"] == PL[p]["sample_sha256"], "B1 sample hash " + p)
    rows.append([PDISP[p], COUNT(int(m0.group(4))), SECS(float(m1.group(3))), SECS(float(m1.group(4)))])
EXP[("S3.30", "a")] = rows
I = A["b1"]["defo"]["identity"]
yn = lambda b: "yes" if b is True else "no"  # noqa: E731
EXP[("S3.30", "b")] = [["Largest absolute difference of the SHAP values, feature level (every row and player)", SCI2(I["max_abs_diff_phi"])],
                       ["Largest absolute difference of the SHAP values, variable level (every row and variable)", SCI2(I["max_abs_diff_phiv"])],
                       ["Rows, main run / B1 run", COUNT(I["n_rows_main"]) + " / " + COUNT(I["n_rows_b1"])],
                       ["Players, main run / B1 run", COUNT(I["n_players_main"]) + " / " + COUNT(I["n_players_b1"])],
                       ["Variables, main run / B1 run", COUNT(I["n_variables_main"]) + " / " + COUNT(I["n_variables_b1"])],
                       ["Same rows / players / variables", " / ".join(yn(I[k]) for k in ("same_rows", "same_players", "same_variables"))]]

# ---------------- compare ----------------
ncell, diffs = 0, []
for key, rows in EXP.items():
    got = TABLES.get(key)
    if got is None:
        diffs.append((key, "table missing"))
        continue
    if len(got["rows"]) != len(rows):
        diffs.append((key, "row count", len(got["rows"]), len(rows)))
    for r_exp, r_got, ln in zip(rows, got["rows"], got["lines"]):
        if len(r_exp) != len(r_got):
            diffs.append((key, ln, "cell count", len(r_got), len(r_exp)))
            continue
        for c_exp, c_got in zip(r_exp, r_got):
            ncell += 1
            if c_exp != c_got:
                diffs.append((key, ln, "got: " + c_got, "exp: " + c_exp))
missing_tables = sorted(set(TABLES) - set(EXP) - {("S3.18", "b")})
nnote = 0
allnotes = {t: [x[1] for x in v] for t, v in NOTES.items()}
for (tid, k), want in ENOTE.items():
    nnote += 1
    if want not in allnotes.get(tid, []):
        diffs.append(((tid, "note", k), "note line not found", want[:120]))
print("section-3 checks re-run:", chk["checks"], "failed:", len(fails), fails[:10])
print("pair statistics with fewer than 2,000 finite draws:", sign_stats.get("pair statistic with fewer than 2000 finite draws", 0))
print("tables re-derived:", len(EXP), "body cells compared:", ncell, "data note lines compared:", nnote)
print("table blocks of tables.md not re-derived:", missing_tables)
print("differences:", len(diffs))
for d in diffs[:60]:
    print("  ", d)
