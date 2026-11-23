# Skeptic of the S3.13 tables: re-derive printed cells of OUT\reconcile\tables_agreed.md from the stored values,
# with this script's own source reads and selection logic, and check that every number is one rounding of its stored
# double. Read-only on every source; writes only OUT\skeptic\k01_checks.json. Run: py -3.9 -I -B k01_rederive.py
import json, math, os, re, sys
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)                      # OUT = ROOT\paper\supp_build\s3_13
SHAP = r"D:\treeroute\analysis\shap_v1"
V = SHAP + r"\verify_v1"
AGREED = os.path.join(OUT, "reconcile", "tables_agreed.md")

PROBS = ["pm25", "ndvi", "fire", "defo", "coral"]
PDISP = {"pm25": "PM2.5", "ndvi": "NDVI", "fire": "Burned fraction", "defo": "Forest loss", "coral": "Coral bleaching"}
ORDER = ["treeroute", "rival_ridge", "rival_rf", "rival_lgbm", "rival_lgbm_tweedie", "rival_hgb_l1", "rival_bardl_h1"]
INL = {"treeroute": "treeroute v1", "rival_ridge": "Ridge", "rival_rf": "random forest", "rival_lgbm": "LightGBM",
       "rival_lgbm_tweedie": "Tweedie booster", "rival_hgb_l1": "absolute-error booster", "rival_bardl_h1": "BARDL"}
HDR = dict(INL, rival_rf="Random forest", rival_hgb_l1="Absolute-error booster")
LINKD = {"identity": "identity", "log_c": "log(y + c)", "log_mu": "log \u03bc", "arcsine": "arcsine"}
TID = {"pm25": "S3.23", "ndvi": "S3.24", "fire": "S3.25", "defo": "S3.26", "coral": "S3.27"}
FAMS = ["own history", "global indices", "local drivers", "context and calendar", "seasonal normal"]
FAMROW = {"own history": "Own history", "global indices": "Global indices", "local drivers": "Local drivers",
          "context and calendar": "Context and calendar", "seasonal normal": "Seasonal normal"}
FAMLAB = {"own history": "(no own-history input)", "global indices": "(no global-index input)",
          "local drivers": "(no local-driver input)", "context and calendar": "(no context or calendar input)",
          "seasonal normal": "(no seasonal-normal input)"}
MINUS, NDASH = "\u2212", "\u2013"
D = 2000

# ---------------------------------------------------------------- formats (my own code, from spec 2.5 and 2.6)
def fin(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)

def NUM2(x):
    assert fin(x), x
    if x == 0.0:
        return "0.00"
    s = format(x, ".2f")
    return MINUS + s[1:] if s[0] == "-" else s

def PCT1(x):
    assert fin(x) and x >= 0, x
    if x == 0.0:
        return "0.0%"
    y = 100.0 * x
    if y < 0.05:
        return "<0.1%"
    return format(y, ".1f") + "%"

def COUNT(n):
    if isinstance(n, float):
        assert n.is_integer(), n
    return format(int(n), ",")

SUP = str.maketrans("0123456789-", "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207b")
def SCI2(x):
    if x == 0.0:
        return "0"
    m, e = format(abs(x), ".1e").split("e")
    return (MINUS if x < 0 else "") + m + " \u00d7 10" + str(int(e)).translate(SUP)

def SECS(x):
    return format(x, ",.1f")

def MED(x):
    return COUNT(x) if float(x).is_integer() else format(x, ".1f")

def CI2(v, lo, hi, nf):
    head = NUM2(v) if fin(v) else "undefined"
    if nf is None or nf == 0:
        return head
    s = head + " [" + NUM2(lo) + ", " + NUM2(hi) + "]"
    if nf < D:
        s += " (" + COUNT(nf) + " finite draws)"
    return s

def CIP(v, lo, hi, nf):
    head = PCT1(v) if fin(v) else "undefined"
    if nf is None or nf == 0:
        return head
    s = head + " [" + PCT1(lo) + ", " + PCT1(hi) + "]"
    if nf < D:
        s += " (" + COUNT(nf) + " finite draws)"
    return s

def SIGN(v, k, lo, hi, nf):
    head = NUM2(v) if fin(v) else "undefined"
    if nf > 0:
        head += " [" + NUM2(lo) + ", " + NUM2(hi) + "]"
    ex = [COUNT(k) + (" sign" if k == 1 else " signs")]
    if 0 < nf < D:
        ex.append(COUNT(nf) + " finite draws")
    return head + " (" + "; ".join(ex) + ")"

def TOP(name, share):
    return "`" + name + "` " + PCT1(share)

def mlist(ms):
    ms = sorted(ms, key=ORDER.index)
    return ", ".join(INL[m] for m in ms) if ms else "none"

def names(ns):
    return ", ".join("`" + n + "`" for n in ns)

# ---------------------------------------------------------------- rounding-once bookkeeping
NUMS = []   # (where, kind, stored double, printed token)

def note_num(where, kind, x, printed=None):
    NUMS.append((where, kind, x, printed))

def alt_num2(x):
    """What a second rounding (via a 3-decimal printout) would print."""
    t3 = format(x, ".3f")
    a = NUM2(float(t3)) if float(t3) != 0.0 else "0.00"
    q = Decimal(t3).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    b = format(q, "f")
    b = "0.00" if Decimal(b) == 0 else (MINUS + b[1:] if b[0] == "-" else b)
    return a, b

# ---------------------------------------------------------------- parse the agreed tables
lines = open(AGREED, encoding="utf-8", newline="").read().split("\n")
TABLES, NOTES = {}, {}
tid, panel, i = None, "", 0
while i < len(lines):
    L = lines[i]
    m = re.match(r"^\*\*Table (9|S3\.\d+)[\. ]", L)
    if m:
        tid, panel = m.group(1), ""
        i += 1
        continue
    m = re.match(r"^\*\*([a-g])\. ", L)
    if m:
        panel = m.group(1)
        i += 1
        continue
    if L.startswith("| "):
        hdr = L[2:-2].split(" | ")
        rows, rl = [], []
        j = i + 2
        while j < len(lines) and lines[j].startswith("| "):
            rows.append(lines[j][2:-2].split(" | "))
            rl.append(j + 1)
            j += 1
        assert all(len(r) == len(hdr) for r in rows), (tid, panel)
        TABLES[(tid, panel)] = {"hdr": hdr, "rows": rows, "lines": rl}
        i = j
        continue
    if tid and L and not L.startswith("#") and not L.startswith("**") and not L.startswith("<!--"):
        NOTES.setdefault(tid, []).append((i + 1, L))
    i += 1

CHECKS = []

def check(t, p, row, col, expected, kind, stored=None):
    T = TABLES[(t, p)]
    ci = T["hdr"].index(col)
    hits = [(r, ln) for r, ln in zip(T["rows"], T["lines"]) if r[0] == row]
    if not hits:
        CHECKS.append(dict(table=t, panel=p, row=row, col=col, ok=False, printed=None, expected=expected, kind=kind,
                           why="row not found"))
        return
    r, ln = hits[0]
    ok = r[ci] == expected
    CHECKS.append(dict(table=t, panel=p, row=row, col=col, line=ln, ok=ok, printed=r[ci], expected=expected,
                       kind=kind, stored=stored))

def check_rowcell(t, p, ridx, cidx, expected, kind, stored=None):
    T = TABLES[(t, p)]
    r, ln = T["rows"][ridx], T["lines"][ridx]
    CHECKS.append(dict(table=t, panel=p, row=r[0], col=T["hdr"][cidx], line=ln, ok=(r[cidx] == expected),
                       printed=r[cidx], expected=expected, kind=kind, stored=stored))

# ---------------------------------------------------------------- sources
def jload(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

A = jload(V + r"\A\results.json")
S = {}
for p in PROBS:
    C = SHAP + r"\out\%s\lead_0\compare" % p
    s = {"PL": jload(C + r"\per_lead.json"), "AW": jload(C + r"\AW4_main_row.json"),
         "PR": pd.read_parquet(C + r"\pairs.parquet"), "IM": pd.read_parquet(C + r"\importance.parquet"),
         "FA": pd.read_parquet(C + r"\families.parquet"),
         "G": jload(SHAP + r"\rebuild\%s\lead_0\gates.json" % p),
         "MF": jload(SHAP + r"\sample\%s\sample_manifest.json" % p)}
    s["META"], s["EX"], s["RX"] = {}, {}, {}
    for m in s["PL"]["models"]:
        P = SHAP + r"\out\%s\lead_0\%s" % (p, m)
        s["META"][m] = jload(P + r"\meta.json")
        if m != "treeroute":
            s["EX"][m] = jload(P + r"\exactness.json")
        if m == "rival_ridge" and p != "coral":
            s["RX"][m] = jload(P + r"\ridge_shap_exactness.json")
    S[p] = s

REG = {}
for ln, line in enumerate(open(SHAP + r"\SAMPLE_REGISTER.txt", encoding="utf-8").read().splitlines(), 1):
    f = dict(t.split("=", 1) for t in line.split()[1:] if "=" in t)
    REG[f["problem"]] = (ln, f)

def prow(p, L, a, b, stat):
    PR = S[p]["PR"]
    lo, hi = sorted([a, b])
    q = PR[(PR.level == L) & (PR.model_a == lo) & (PR.model_b == hi) & (PR.statistic == stat)]
    assert len(q) == 1, (p, L, a, b, stat, len(q))
    return q.iloc[0]

def fv(x):
    """parquet / json value to a Python float or None"""
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None

# ---------------------------------------------------------------- global facts behind the formats
FACTS = {}
bad_nf = []
for p in PROBS:
    PR = S[p]["PR"]
    nsign = PR[PR.statistic != "sign_agreement_top10"]
    bad = nsign[nsign.finite_replicates != D]
    for _, r in bad.iterrows():
        bad_nf.append((p, r.level, r.model_a, r.model_b, r.statistic, int(r.finite_replicates), r.value))
    assert S[p]["PL"]["draws"] == D
FACTS["pairs_parquet_non_sign_rows_with_finite_ne_2000"] = bad_nf
a_sign_thin = []
for p in PROBS:
    for L in ["variable", "feature"]:
        for k, o in A["problems"][p]["levels"][L]["pairs"].items():
            nf = o["sign_agreement"]["n_finite"]
            if nf != D:
                a_sign_thin.append((p, L, k, nf, o["sign_agreement"]["value"], o["sign_agreement"]["ci_low"],
                                    o["sign_agreement"]["ci_high"]))
FACTS["A_sign_agreement_n_finite_ne_2000"] = a_sign_thin

# ---------------------------------------------------------------- Table 9 and Table S3.22
def main_set_rivals(p):
    return [m for m in sorted(S[p]["AW"]["models_in_main_set"], key=ORDER.index) if m != "treeroute"]

for p in PROBS:
    AW, PL, FA, IM = S[p]["AW"], S[p]["PL"], S[p]["FA"], S[p]["IM"]
    row = PDISP[p]
    if p == "fire":
        mr = A["problems"]["fire"]["main_row"]
        tops = [n for n, _ in mr["treeroute_top3"]]
        oh = mr["own_history_share_treeroute"]
        exp9 = {"Main set": "treeroute v1 only\u1d43", "W [95% CI]": "undefined",
                "Spearman of treeroute v1 with its same-link rivals: median [95% CI] (range)": NDASH,
                "RBO with the rivals' consensus, p = 0.9 [95% CI]": NDASH,
                "treeroute v1's top 3": names(tops) + "\u2020", "Consensus top 3": NDASH,
                "Own-history share, treeroute v1 [95% CI]": CI2(oh["value"], oh["ci_low"], oh["ci_high"], oh["n_finite"]) + "\u2020",
                "Own-history share, median of the rivals\u1d9c [95% CI]": NDASH}
        for k in ["value", "ci_low", "ci_high"]:
            note_num("9/fire/own_history_treeroute/" + k, "NUM2", oh[k])
        assert not fin(AW["kendall_w"]["value"]) and AW["kendall_w"]["ci"][2] == 0
        # cross-checks of BB1 cells against the compare files
        r_imp = IM[(IM.level == "variable") & (IM.model == "treeroute") & (IM.active)].sort_values(
            ["mean_abs", "player"], ascending=[False, True])
        FACTS["fire_top3_A_equals_importance_order"] = list(r_imp.player[:3]) == tops
        fam = FA[(FA.model == "treeroute") & (FA.family == "own history")].share.iloc[0]
        FACTS["fire_own_history_A_minus_families"] = abs(float(fam) - oh["value"])
    else:
        sp = AW["treeroute_vs_same_link_rivals_median_spearman_top20_union"]
        rb = AW["rbo_vs_consensus_p0.9"]
        lab = " (no own-history input)" if p == "coral" else ""
        ot, om, kw = AW["own_history_share_treeroute"], AW["own_history_share_median_rival"], AW["kendall_w"]
        exp9 = {"Main set": mlist(AW["models_in_main_set"]),
                "W [95% CI]": CI2(kw["value"], kw["ci"][0], kw["ci"][1], kw["ci"][2]),
                "Spearman of treeroute v1 with its same-link rivals: median [95% CI] (range)":
                    CI2(sp["value"], sp["ci"][0], sp["ci"][1], sp["ci"][2]) + " (" + NUM2(sp["range"][0]) + " to " + NUM2(sp["range"][1]) + ")",
                "RBO with the rivals' consensus, p = 0.9 [95% CI]": CI2(rb["value"], rb["ci"][0], rb["ci"][1], rb["ci"][2]) + ("\u1d47" if p == "pm25" else ""),
                "treeroute v1's top 3": names(AW["treeroute_top3"]),
                "Consensus top 3": names(AW["consensus_top3"]),
                "Own-history share, treeroute v1 [95% CI]": CI2(ot["value"], ot["ci"][0], ot["ci"][1], ot["ci"][2]) + lab,
                "Own-history share, median of the rivals\u1d9c [95% CI]": CI2(om["value"], om["ci"][0], om["ci"][1], om["ci"][2]) + lab}
        for nm, o in [("W", kw), ("rho_med", sp), ("rbo", rb), ("oh_tr", ot), ("oh_med", om)]:
            for j, x in enumerate([o["value"], o["ci"][0], o["ci"][1]]):
                note_num("9/%s/%s/%d" % (p, nm, j), "NUM2", x)
        note_num("9/%s/range0" % p, "NUM2", sp["range"][0]); note_num("9/%s/range1" % p, "NUM2", sp["range"][1])
        # cross-checks of AW4 against the other compare files (my own median / range / order / shares)
        riv = main_set_rivals(p)
        rhos = [float(prow(p, "variable", "treeroute", m, "spearman_top20_union").value) for m in riv]
        FACTS["%s_median_rho_minus_AW4" % p] = abs(float(np.median(rhos)) - sp["value"])
        FACTS["%s_range_equal" % p] = (min(rhos) == sp["range"][0] and max(rhos) == sp["range"][1])
        ohs = [float(FA[(FA.model == m) & (FA.family == "own history")].share.iloc[0]) for m in riv]
        FACTS["%s_median_own_history_minus_AW4" % p] = abs(float(np.median(ohs)) - om["value"])
        tro = IM[(IM.level == "variable") & (IM.model == "treeroute") & (IM.active)].sort_values(
            ["mean_abs", "player"], ascending=[False, True])
        FACTS["%s_treeroute_top3_equal" % p] = list(tro.player[:3]) == AW["treeroute_top3"]
        ftr = float(FA[(FA.model == "treeroute") & (FA.family == "own history")].share.iloc[0])
        FACTS["%s_own_history_tr_minus_families" % p] = abs(ftr - ot["value"])
        assert kw["ci"][2] == D and sp["ci"][2] == D and rb["ci"][2] == D and ot["ci"][2] == D and om["ci"][2] == D
        # consensus top 3 rebuilt: mean of the rivals' variable shares
        sh = IM[(IM.level == "variable") & (IM.active) & (IM.model.isin(riv))].pivot(index="player", columns="model", values="share")
        cons = sh.mean(axis=1).reset_index()
        cons.columns = ["player", "c"]
        cons = cons.sort_values(["c", "player"], ascending=[False, True])
        FACTS["%s_consensus_top3_equal" % p] = list(cons.player[:3]) == AW["consensus_top3"]
    for col, e in exp9.items():
        check("9", "", row, col, e, "table9")
    # Table S3.22, column = problem
    col = PDISP[p] + ("\u1d48" if p == "coral" else "")
    if p == "fire":
        e22 = {"Link of the main set": LINKD[AW["reference_link"].split("|")[0]],
               "Main set": "treeroute v1 only\u1d43",
               "Rivals in another link": mlist(AW["cross_link_models"]),
               "Rivals declined by their skill guard": mlist(AW["declined_models"]),
               "Kendall's W of the main set [95% CI]": "undefined",
               "Spearman of treeroute v1 with each same-link rival": NDASH, "Median of those [95% CI]": NDASH,
               "Range (lowest to highest)": NDASH, "RBO with the rivals' consensus, p = 0.9 [95% CI]": NDASH,
               "treeroute v1's top 3": exp9["treeroute v1's top 3"], "Consensus top 3": NDASH,
               "Own-history share, treeroute v1 [95% CI]": exp9["Own-history share, treeroute v1 [95% CI]"],
               "Own-history share of each same-link rival": NDASH,
               "Own-history share, median of the rivals\u1d9c [95% CI]": NDASH}
    else:
        riv = main_set_rivals(p)
        lab = " (no own-history input)" if p == "coral" else ""
        per_rho = "; ".join(INL[m] + " " + NUM2(float(prow(p, "variable", "treeroute", m, "spearman_top20_union").value)) for m in riv)
        per_oh = "; ".join(INL[m] + " " + NUM2(float(FA[(FA.model == m) & (FA.family == "own history")].share.iloc[0])) for m in riv) + lab
        for m in riv:
            note_num("S3.22/%s/rho/%s" % (p, m), "NUM2", float(prow(p, "variable", "treeroute", m, "spearman_top20_union").value))
            note_num("S3.22/%s/oh/%s" % (p, m), "NUM2", float(FA[(FA.model == m) & (FA.family == "own history")].share.iloc[0]))
        e22 = {"Link of the main set": LINKD[AW["reference_link"].split("|")[0]],
               "Main set": exp9["Main set"], "Rivals in another link": mlist(AW["cross_link_models"]),
               "Rivals declined by their skill guard": mlist(AW["declined_models"]),
               "Kendall's W of the main set [95% CI]": exp9["W [95% CI]"],
               "Spearman of treeroute v1 with each same-link rival": per_rho,
               "Median of those [95% CI]": CI2(sp["value"], sp["ci"][0], sp["ci"][1], sp["ci"][2]),
               "Range (lowest to highest)": NUM2(sp["range"][0]) + " to " + NUM2(sp["range"][1]),
               "RBO with the rivals' consensus, p = 0.9 [95% CI]": exp9["RBO with the rivals' consensus, p = 0.9 [95% CI]"],
               "treeroute v1's top 3": exp9["treeroute v1's top 3"], "Consensus top 3": exp9["Consensus top 3"],
               "Own-history share, treeroute v1 [95% CI]": exp9["Own-history share, treeroute v1 [95% CI]"],
               "Own-history share of each same-link rival": per_oh,
               "Own-history share, median of the rivals\u1d9c [95% CI]": exp9["Own-history share, median of the rivals\u1d9c [95% CI]"]}
    for rk, e in e22.items():
        check("S3.22", "", rk, col, e, "s322")

# ---------------------------------------------------------------- Table S3.18 a (links, guard, main set)
T = TABLES[("S3.18", "a")]
exp_rows = []
for p in PROBS:
    PL = S[p]["PL"]
    for m in sorted(PL["models"], key=ORDER.index):
        link = PL["links"][m]
        if m == "treeroute":
            guard = "passed (the kept arm)"
        else:
            guard = "passed" if S[p]["META"][m]["guard"]["passed"] else "failed\u1d43"
        if m in PL["main_set"]:
            ms = "yes"
        else:
            rs = []
            if link != PL["links"]["treeroute"]:
                rs.append("another link")
            if m in PL["declined_by_guard"]:
                rs.append("skill guard failed")
            ms = "no: " + "; ".join(rs)
        exp_rows.append([PDISP[p], INL[m] + " (`" + m + "`)", LINKD[link.split("|")[0]], guard, ms])
for k, (r, e) in enumerate(zip(T["rows"], exp_rows)):
    for cidx, eidx in [(0, 0), (1, 1), (3, 2), (4, 3), (5, 4)]:
        check_rowcell("S3.18", "a", k, cidx, e[eidx], "s318")
FACTS["S3.18a_rows"] = (len(T["rows"]), len(exp_rows))

# ---------------------------------------------------------------- Table S3.19 (samples, backgrounds, J)
for p in PROBS:
    MF, PL = S[p]["MF"], S[p]["PL"]
    b = MF["background_rows"]["0"]
    bg = COUNT(b["min"]) if b["min"] == b["max"] else COUNT(b["min"]) + NDASH + COUNT(b["max"]) + " (median " + MED(b["median"]) + ")"
    e = {"Frame rows\u1d43": COUNT(MF["frame_rows"]), "Sample rows": COUNT(int(REG[p][1]["n"])),
         "Regions": COUNT(MF["regions_in_sample"]), "Locations\u1d47": COUNT(MF["units_in_sample"]),
         "Background rows per sample row\u1d9c": bg, "Background pairs": COUNT(S[p]["META"]["treeroute"]["pairs"]),
         "Feature level: players / J / structural zeros": " / ".join(COUNT(x) for x in [PL["feature"]["players"], PL["feature"]["active"], len(PL["feature"]["structural_zero"])]),
         "Variable level: players / J / structural zeros": " / ".join(COUNT(x) for x in [PL["variable"]["players"], PL["variable"]["active"], len(PL["variable"]["structural_zero"])])}
    for col, x in e.items():
        check("S3.19", "", PDISP[p], col, x, "s319")
    assert PL["feature"]["players"] - PL["feature"]["active"] == len(PL["feature"]["structural_zero"])
    assert PL["variable"]["players"] - PL["variable"]["active"] == len(PL["variable"]["structural_zero"])
    # the structural-zero note line
    want = "%s: variable level (%s) %s; feature level (%s) %s." % (
        PDISP[p], COUNT(len(PL["variable"]["structural_zero"])), names(PL["variable"]["structural_zero"]),
        COUNT(len(PL["feature"]["structural_zero"])), names(PL["feature"]["structural_zero"]))
    got = [t for _, t in NOTES["S3.19"] if t.startswith(PDISP[p] + ": variable level")]
    CHECKS.append(dict(table="S3.19", panel="", row="note", col="structural zeros " + p, ok=(got == [want]),
                       printed=got[0] if got else None, expected=want, kind="s319note"))

# ---------------------------------------------------------------- Table S3.20 (S-EXACT, additivity, S-ZERO, guard)
T = TABLES[("S3.20", "")]
k = 0
for p in PROBS:
    PL = S[p]["PL"]
    for m in sorted(PL["models"], key=ORDER.index):
        me = S[p]["META"][m]
        if m == "treeroute":
            ev = S[p]["G"]["gates"]["E8_predictions"]["values"]
            rows_, pre, clip, mx = ev["rows_checked"], ev["pre_bit_equal"], ev["arm_bit_equal"], ev["max_abs_pre"]
            sx = "bit-identical" if ev["bit_identical"] else \
                "within the D8 tolerance\u1d9c (largest relative difference " + SCI2(ev["max_rel_pre"]) + ")"
            guard = "passed (the kept arm)"
        else:
            if m in S[p]["RX"]:
                rec = S[p]["RX"][m]
                clip = rec["raw"]["bit_equal_rows"]
            else:
                rec = S[p]["EX"][m]
                clip = rec["raw"]["bit_equal_rows"] if isinstance(rec.get("raw"), dict) else None
            rows_, pre, mx = rec["rows"], rec["bit_equal_rows"], rec["max_abs_diff"]
            assert rec["pass"] and pre == rows_ and (clip is None or clip == rows_)
            sx = "bit-identical"
            guard = "passed" if me["guard"]["passed"] else "failed\u1d48"
        assert me["pass"] and all(me["checks_passed"][c] for c in ["S-ADD", "S-EVAL", "S-RESID", "S-ZERO"])
        mname = INL[m] + ("\u1d47" if (m == "rival_ridge" and p != "coral") else "")
        e = [PDISP[p], mname, COUNT(rows_), COUNT(pre) + " / " + (COUNT(clip) if clip is not None else NDASH), SCI2(mx), sx,
             SCI2(me["max_abs_additivity_error"]) + " / " + SCI2(me["max_abs_additivity_error_variable"]),
             COUNT(me["structural_zero_violations"]), "all passed", guard]
        for cidx in range(10):
            check_rowcell("S3.20", "", k, cidx, e[cidx], "s320")
        k += 1
FACTS["S3.20_rows"] = (len(T["rows"]), k)
# note b placeholders
nb = [t for _, t in NOTES["S3.20"] if t.startswith("\u1d47 ")][0]
for p, word in [("pm25", "PM2.5"), ("ndvi", "NDVI"), ("fire", "burned fraction"), ("defo", "forest loss")]:
    ex = S[p]["EX"]["rival_ridge"]
    frag = "%s of %s" % (COUNT(ex["bit_equal_rows"]), COUNT(ex["rows"]))
    CHECKS.append(dict(table="S3.20", panel="", row="note b", col=p, ok=(frag in nb), printed=None, expected=frag, kind="s320note"))

# ---------------------------------------------------------------- Table S3.21 (gates)
for p in PROBS:
    G, R = S[p]["G"]["gates"], S[p]["G"]["result"]
    col = PDISP[p]
    rk = {"per_unit": "per-location router", "region": "region router", "neighbour": "neighbour router"}[R["kind"]]
    e = {"Kept arm": LINKD[R["link"]] + ", " + {"plain": "plain answers", "corrector": "corrected answers"}[R["table_kind"]] + ", " +
         ("error-weighted" if R["weighted"] else "uniformly weighted") + "; " + rk}
    e["E0"] = "passed (warning overridden)" if G["E0_ram_preflight"]["values"]["ignored"] else "passed"
    e["E3m"] = ("passed (" + COUNT(len(G["E3m_recorded_path_map"]["values"]["files"])) +
                (" file)" if len(G["E3m_recorded_path_map"]["values"]["files"]) == 1 else " files)")) if "E3m_recorded_path_map" in G else "not used (no moved file)"
    e["E4"] = "passed (" + COUNT(G["E4_donor_rows"]["values"]["rows"][0]) + " rows)"
    e["E5\u1d43"] = "differs (informational)"
    if "E5a_identity_twin" in G:
        v = G["E5a_identity_twin"]["values"]
        assert v["pre_bit_equal"] == v["arm_bit_equal"] == v["rows_checked"]
        e["E5a"] = "passed (" + COUNT(v["pre_bit_equal"]) + " of " + COUNT(v["rows_checked"]) + " rows)"
    else:
        e["E5a"] = "not applicable"
    e["E7"] = "passed" if "E7_gls_weight_model" in G else "not applicable"
    v = G["E9_coefficients_reproduce_the_kernel"]["values"]
    if v["region_proof"] is None:
        e["E9"] = "passed (all " + COUNT(v["fits_captured"]) + " fits)"
    else:
        rp = v["region_proof"]
        e["E9"] = "passed (all " + COUNT(v["fits_captured"]) + " region fits; region proof on " + COUNT(rp["score_rows"]) + " score rows and " + COUNT(rp["background_rows"]) + " background rows)"
    v = G["E8_predictions"]["values"]
    e["E8"] = ("bit-identical (" + COUNT(v["pre_bit_equal"]) + " of " + COUNT(v["rows_checked"]) + " rows)") if v["bit_identical"] else \
        (COUNT(v["pre_bit_equal"]) + " of " + COUNT(v["rows_checked"]) + " rows bit-identical; the rest within the D8 tolerance (largest relative difference " + SCI2(v["max_rel_pre"]) + ")")
    v = G["E10_exported_trees"]["values"]
    e["E10"] = ("passed (" + COUNT(v["rows_x_trees"][0]) + " rows, " + COUNT(v["rows_x_trees"][1]) + " trees)") if "rows_x_trees" in v else \
        ("passed (every sampled location of the " + COUNT(v["regions"]) + " regions)")
    FACTS["E10_scope_" + p] = v.get("unit") or v.get("what")
    for g in ["E1", "E2", "E3a", "E3", "E6"]:
        e[g] = "passed"
    # every gate passes but E5; E5 fails on all five
    for gname, gv in G.items():
        if gname == "E5_bank_fingerprint":
            assert gv["pass"] is False
        else:
            assert gv["pass"] is True, (p, gname)
    assert S[p]["G"]["stopped_at"] is None
    for g, x in e.items():
        check("S3.21", "", g, col, x, "s321")

# ---------------------------------------------------------------- Tables S3.23-S3.27
def pair_text(a, b, p):
    x, y = sorted([a, b], key=ORDER.index)
    t = INL[x] + " vs " + INL[y]
    if p == "ndvi" and "rival_bardl_h1" in (a, b):
        t += "\u2021"
    return t

def my_link_label(p, a, b):
    PL = S[p]["PL"]
    lab = "same-link" if PL["links"][a] == PL["links"][b] else "cross-link (not comparable in scale or rank)"
    dec = [m for m in sorted([a, b]) if m in PL["declined_by_guard"]]
    if dec:
        lab += "; raw model, declined by its guard: " + ", ".join(INL[m] for m in dec)
    return lab

STATCOL = [("Spearman over J", "spearman"), ("Spearman, top-20 union", "spearman_top20_union"),
           ("Kendall's tau-b", "kendall_tau_b"), ("Jaccard top 5", "jaccard_top5"), ("Jaccard top 10", "jaccard_top10"),
           ("Jaccard top 20", "jaccard_top20"), ("RBO, p = 0.9", "rbo_p0.9"), ("RBO, p = 0.95", "rbo_p0.95"),
           ("Share distance (TV)", "tvd")]
AKEY = {"spearman": "spearman_J", "spearman_top20_union": "spearman_top20_union", "kendall_tau_b": "kendall_tau_b",
        "jaccard_top5": "jaccard_top5", "jaccard_top10": "jaccard_top10", "jaccard_top20": "jaccard_top20",
        "rbo_p0.9": "rbo_p090", "rbo_p0.95": "rbo_p095", "tvd": "tv_shares", "tvd_family": "tv_family_shares"}
max_A_minus_parquet = 0.0
for p in PROBS:
    t = TID[p]
    PL = S[p]["PL"]
    models = sorted(PL["models"], key=ORDER.index)
    pairs = [(models[i], models[j]) for i in range(len(models)) for j in range(i + 1, len(models))]
    for L, pan in [("variable", "a"), ("feature", "b")]:
        T = TABLES[(t, pan)]
        FACTS["%s_%s_pair_order" % (p, pan)] = [r[0] for r in T["rows"]] == [pair_text(a, b, p) for a, b in pairs]
        has20 = "Jaccard top 20" in T["hdr"]
        FACTS["%s_%s_jaccard20_column_iff_active_ge_200" % (p, pan)] = (has20 == (PL[L]["active"] >= 200))
        for a, b in pairs:
            rk = pair_text(a, b, p)
            key = "|".join(sorted([a, b]))
            Ao = A["problems"][p]["levels"][L]["pairs"][key]
            lab_pq = prow(p, L, a, b, "spearman").pair_label
            for nm in PL["declined_by_guard"]:
                lab_pq = lab_pq.replace("guard: " + nm, "guard: " + INL[nm])
            check(t, pan, rk, "Link", my_link_label(p, a, b), "pairlabel")
            CHECKS.append(dict(table=t, panel=pan, row=rk, col="Link (vs pairs.parquet label)", ok=(lab_pq == my_link_label(p, a, b)),
                               printed=lab_pq, expected=my_link_label(p, a, b), kind="pairlabel_src"))
            for colname, st in STATCOL:
                if colname not in T["hdr"]:
                    continue
                r = prow(p, L, a, b, st)
                v, lo, hi, nf = fv(r.value), fv(r.ci_low), fv(r.ci_high), int(r.finite_replicates)
                check(t, pan, rk, colname, CI2(v, lo, hi, nf), "pairstat", [v, lo, hi, nf])
                for j, x in enumerate([v, lo, hi]):
                    note_num("%s/%s/%s/%s/%d" % (t, pan, key, st, j), "NUM2", x)
                ao = Ao[AKEY[st]]
                if ao is not None and v is not None:
                    max_A_minus_parquet = max(max_A_minus_parquet, abs(ao["value"] - v), abs(ao["ci_low"] - lo), abs(ao["ci_high"] - hi))
            # family-share distance: the variable-level row in both panels
            r = prow(p, "variable", a, b, "tvd_family")
            v, lo, hi, nf = fv(r.value), fv(r.ci_low), fv(r.ci_high), int(r.finite_replicates)
            fcol = "Family-share distance (TV)" + ("\u00a7" if pan == "b" else "")
            check(t, pan, rk, fcol, CI2(v, lo, hi, nf), "tvd_family", [v, lo, hi, nf])
            # sign agreement
            r = prow(p, L, a, b, "sign_agreement_top10")
            sa = Ao["sign_agreement"]
            v = fv(r.value)
            kk = int(r.signs_compared)
            assert (v is None) == (sa["value"] is None) and (v is None or abs(v - sa["value"]) <= 1e-12)
            assert kk == int(Ao["sign_n_determined"]["value"])
            nf = sa["n_finite"]
            check(t, pan, rk, "Sign agreement, top-10 union (signs)\u2020", SIGN(v, kk, sa["ci_low"], sa["ci_high"], nf), "sign",
                  [v, kk, sa["ci_low"], sa["ci_high"], nf])
            if v is not None:
                note_num("%s/%s/%s/sign/v" % (t, pan, key), "NUM2", v)
            if nf > 0:
                note_num("%s/%s/%s/sign/lo" % (t, pan, key), "NUM2", sa["ci_low"])
                note_num("%s/%s/%s/sign/hi" % (t, pan, key), "NUM2", sa["ci_high"])
    # panel c
    for L, col in [("variable", "Variable level"), ("feature", "Feature level")]:
        for rk, key in [("Kendall's W of the main set [95% CI]", "kendall_w_main_set"),
                        ("Mean pairwise Spearman of the main set [95% CI]", "mean_pairwise_spearman_main_set")]:
            o = PL[L][key]
            if p == "fire":
                assert not fin(o["value"]) and o["finite_replicates"] == 0
                e = "undefined\u1d43"
            else:
                assert o["finite_replicates"] == D
                e = CI2(o["value"], o["ci"][0], o["ci"][1], o["finite_replicates"])
                for j, x in enumerate([o["value"], o["ci"][0], o["ci"][1]]):
                    note_num("%s/c/%s/%s/%d" % (t, L, key, j), "NUM2", x)
            check(t, "c", rk, col, e, "panel_c")
        for m in models:
            x = PL[L]["stability_under_region_resampling"][m]
            check(t, "c", "Stability under region resampling: " + INL[m], col, NUM2(x), "stability", x)
            note_num("%s/c/%s/stab/%s" % (t, L, m), "NUM2", x)
    # panels d and e
    IM = S[p]["IM"]
    for L, pan, last in [("variable", "d", "Nonzero variables"), ("feature", "e", "Nonzero players")]:
        T = TABLES[(t, pan)]
        want_hdr = ["Rank"] + [HDR[m] + ("\u2021" if m == "rival_bardl_h1" else "") for m in models]
        FACTS["%s_%s_header" % (p, pan)] = T["hdr"] == want_hdr
        for m in models:
            q = IM[(IM.level == L) & (IM.model == m) & (IM.active)].sort_values(["mean_abs", "player"], ascending=[False, True])
            colh = HDR[m] + ("\u2021" if m == "rival_bardl_h1" else "")
            for kk in range(10):
                check(t, pan, str(kk + 1), colh, TOP(q.player.iloc[kk], float(q.share.iloc[kk])), "top10", float(q.share.iloc[kk]))
            check(t, pan, last, colh, COUNT(PL[L]["nonzero_players"][m]), "nonzero")
            FACTS["%s_%s_%s_nonzero_equals_count_share_gt0" % (p, L, m)] = int((q.share > 0).sum()) == PL[L]["nonzero_players"][m]
            # A's (independent) ranking gives the same top 10 names
            at = [n for n, _ in A["problems"][p]["levels"][L]["models"][m]["top10"]]
            FACTS["%s_%s_%s_top10_names_equal_A" % (p, L, m)] = at == list(q.player.iloc[:10])
    # panel f
    FA = S[p]["FA"]
    empty = [f for f in FAMS if f not in set(PL["families"].values())]
    FACTS["%s_families_with_no_variable" % p] = empty
    for f in FAMS:
        for m in models:
            x = float(FA[(FA.model == m) & (FA.family == f)].share.iloc[0])
            e = PCT1(x) + ((" " + FAMLAB[f]) if f in empty else "")
            check(t, "f", FAMROW[f], HDR[m], e, "family", x)
    # panel g
    if (t, "g") in TABLES:
        nz = PL["nonzero_forecast_rows"]
        gm = sorted(nz.keys(), key=ORDER.index)
        FACTS["%s_g_models_are_arcsine" % p] = all(PL["links"][m].startswith("arcsine") for m in gm) and \
            all((m in gm) == PL["links"][m].startswith("arcsine") for m in models)
        for m in gm:
            for kk in range(10):
                n_, s_ = nz[m]["top10"][kk]
                check(t, "g", str(kk + 1), HDR[m], TOP(n_, s_), "top10_nonzero", s_)
            check(t, "g", "Rows with a forecast above 0", HDR[m], COUNT(nz[m]["rows"]), "nonzero_rows")

# NDVI's BARDL note
nd = [x for _, x in NOTES["S3.24"] if x.startswith("\u2021 ")][0]
PLn = S["ndvi"]["PL"]
frag = "the other %s of the %s variables of J (%s of the %s players at the feature level)" % (
    COUNT(PLn["variable"]["active"] - PLn["variable"]["nonzero_players"]["rival_bardl_h1"]), COUNT(PLn["variable"]["active"]),
    COUNT(PLn["feature"]["active"] - PLn["feature"]["nonzero_players"]["rival_bardl_h1"]), COUNT(PLn["feature"]["active"]))
CHECKS.append(dict(table="S3.24", panel="", row="note \u2021", col="counts", ok=(frag in nd), printed=None, expected=frag, kind="bardlnote"))
mx = open(V + r"\_lead\outputs\bardl_maxima.txt", encoding="utf-8-sig").read().splitlines()
blk = mx[1:7]
SNAME = {"jaccard_top5": "Jaccard top 5", "jaccard_top10": "Jaccard top 10", "jaccard_top20": "Jaccard top 20",
         "rho20": "top-20-union Spearman", "rbo090": "RBO p = 0.9", "rbo095": "RBO p = 0.95"}
for line in blk:
    m = re.match(r"^\s+(\w+)\s+spread ([0-9.]+) -> \S+ \(3 sig\. \S+\) at (\w+)/(\w+)/(\S+); values ([0-9.\-]+) / ([0-9.\-]+) / ([0-9.\-]+)$", line)
    st, spread, pp, lev, pk, v1, v2, v3 = m.groups()
    a_, b_ = pk.split("|")
    frag = "%s, %s (%s level, %s)" % (SNAME[st], NUM2(float(spread)), lev, pair_text(a_, b_, "x"))
    CHECKS.append(dict(table="S3.24", panel="", row="note \u2021", col=st, ok=(frag in nd), printed=None, expected=frag, kind="bardlnote"))
    vals = [float(v1), float(v2), float(v3)]
    FACTS["bardl_%s_spread_equals_range" % st] = abs((max(vals) - min(vals)) - float(spread)) < 1e-9
    FACTS["bardl_%s_codepoint_is_extreme" % st] = vals[0] in (max(vals), min(vals))
    FACTS["bardl_%s_max_move_from_codepoint" % st] = max(abs(vals[1] - vals[0]), abs(vals[2] - vals[0]))
    if st == "jaccard_top5":
        ex = "is %s with the tie-only `aet_total_mm` in its top 5, and %s without it" % (NUM2(vals[0]), NUM2(vals[2]))
        CHECKS.append(dict(table="S3.24", panel="", row="note \u2021", col="example", ok=(ex in nd), printed=None, expected=ex, kind="bardlnote"))
        jv = float(prow("ndvi", "variable", "treeroute", "rival_bardl_h1", "jaccard_top5").value)
        FACTS["bardl_example_first_value_minus_pairs"] = abs(jv - vals[0])

# ---------------------------------------------------------------- Tables S3.28 and S3.29 (B1)
B1P = ["pm25", "ndvi", "fire"]
ROWS28 = [("Spearman over J", "spearman_J"), ("Spearman, top-20 union", "spearman_top20_union"),
          ("Kendall's tau-b", "kendall_tau_b"), ("Jaccard top 5", "jaccard_top5"), ("Jaccard top 10", "jaccard_top10"),
          ("RBO, p = 0.9", "rbo_p090"), ("RBO, p = 0.95", "rbo_p095"), ("Share distance (TV)", "tv_shares"),
          ("Sign agreement, top-10 union", "sign_agreement")]
for L, pan in [("variable", "a"), ("feature", "b")]:
    for p in B1P:
        Bo = A["b1"][p][L]
        Q = Bo["pair_main_b1"]
        col = PDISP[p]
        check("S3.28", pan, ("Variables" if L == "variable" else "Players") + " in the pair's J", col, COUNT(Q["n_J"]["value"]), "b1count")
        check("S3.28", pan, "Nonzero in the B1 run", col, COUNT(Bo["importance"]["n_nonzero"]["value"]), "b1count")
        for rk, key in ROWS28:
            o = Q[key]
            check("S3.28", pan, rk, col, CI2(o["value"], o["ci_low"], o["ci_high"], o["n_finite"]), "b1stat", o)
            assert o["n_finite"] == D
            for j, x in enumerate([o["value"], o["ci_low"], o["ci_high"]]):
                note_num("S3.28/%s/%s/%s/%d" % (pan, p, key, j), "NUM2", x)
        o = A["b1"][p]["variable"]["pair_main_b1"]["tv_family_shares"]
        check("S3.28", pan, "Family-share distance (TV)" + ("\u00a7" if pan == "b" else ""), col,
              CI2(o["value"], o["ci_low"], o["ci_high"], o["n_finite"]), "b1stat", o)
        check("S3.28", pan, "Signs determined in both runs / of those, agreeing", col,
              COUNT(Q["sign_n_determined"]["value"]) + " / " + COUNT(Q["sign_n_agree"]["value"]), "b1count")
        if pan == "b":
            o = Q["jaccard_top20"]
            check("S3.28", pan, "Jaccard top 20", col, CI2(o["value"], o["ci_low"], o["ci_high"], o["n_finite"]) if o else NDASH, "b1stat", o)
            FACTS["b1_%s_feature_J_ge_200_iff_jaccard20" % p] = (Q["n_J"]["value"] >= 200) == (o is not None)
    FACTS["b1_%s_jaccard20_row_present" % pan] = any(r[0] == "Jaccard top 20" for r in TABLES[("S3.28", pan)]["rows"])
B1F = [("Own history", "own_history"), ("Global indices", "global_indices"), ("Local drivers", "local_drivers"),
       ("Context and calendar", "context_and_calendar"), ("Seasonal normal", "seasonal_normal")]
for p in B1P:
    col = PDISP[p]
    Bv = A["b1"][p]["variable"]
    for rk, f in B1F:
        o = Bv["families"][f]
        assert o["n_finite"] == D
        check("S3.29", "a", rk, col, CIP(o["value"], o["ci_low"], o["ci_high"], o["n_finite"]), "b1family", o)
    check("S3.29", "b", "Top 3 (share)", col, ", ".join(TOP(n, s) for n, s in Bv["top3"]), "b1top3")
    o = Bv["own_history_share"]
    check("S3.29", "b", "Own-history share [95% CI]", col, CI2(o["value"], o["ci_low"], o["ci_high"], o["n_finite"]), "b1oh", o)
    for j, x in enumerate([o["value"], o["ci_low"], o["ci_high"]]):
        note_num("S3.29/b/%s/oh/%d" % (p, j), "NUM2", x)
    FACTS["b1_%s_own_history_equals_family" % p] = (o["value"] == Bv["families"]["own_history"]["value"])
    for L, pan in [("variable", "c"), ("feature", "d")]:
        for kk, (n, s) in enumerate(A["b1"][p][L]["top10"]):
            check("S3.29", pan, str(kk + 1), col, TOP(n, s), "b1top10", s)
        # my own ranking of the B1 run from its per-player shares
        pl_ = A["b1"][p][L]["importance"]["players"]
        rank = sorted(pl_.keys(), key=lambda n: (-pl_[n]["I"]["value"], n))
        FACTS["b1_%s_%s_top10_equals_own_ranking" % (p, L)] = rank[:10] == [n for n, _ in A["b1"][p][L]["top10"]]
    FACTS["b1_%s_context_calendar_share" % p] = Bv["families"]["context_and_calendar"]["value"]
    FACTS["b1_%s_players_have_I_share_signed_mean_ci" % p] = all(
        all(k in o and o[k] is not None and o[k].get("n_finite") is not None for k in ["I", "share", "signed_mean"])
        for o in A["b1"][p]["variable"]["importance"]["players"].values())

# ---------------------------------------------------------------- Table S3.30 (logs, identity)
for p in ["pm25", "ndvi", "fire", "defo"]:
    lg = open(SHAP + r"\logs\tr_shap_%s_lead0.log" % p, encoding="utf-8").read().splitlines()
    setup = [(n, l) for n, l in enumerate(lg) if re.match(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] (\w+) lead 0: (\d+) rows, (\d+) background pairs,", l)]
    n0, l0 = setup[-1]
    m0 = re.match(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] (\w+) lead 0: (\d+) rows, (\d+) background pairs,", l0)
    assert m0.group(1) >= "2026-11-15 23:06:00" and m0.group(2) == p and m0.group(3) == "1000"
    done = None
    for l in lg[n0 + 1:]:
        md = re.match(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] treeroute SHAP (\w+) lead 0 done in ([0-9.]+) s \(tree SHAP ([0-9.]+) s\)$", l)
        if md:
            done = md
            break
    e = [COUNT(int(m0.group(4))), SECS(float(done.group(3))), SECS(float(done.group(4)))]
    for c, x in zip(["Background pairs", "Total seconds", "Tree-SHAP seconds"], e):
        check("S3.30", "a", PDISP[p], c, x, "s330")
    run = A["b1"][p]["run"] if p != "defo" else A["b1"]["defo"]["identity"]
    FACTS["s330_%s_log_equals_A" % p] = (int(m0.group(4)) == run["pairs_log"] and float(done.group(3)) == run["total_seconds_log"]
                                         and float(done.group(4)) == run["tree_shap_seconds_log"])
    mb1 = jload(SHAP + r"\out\%s\lead_0\treeroute_B1\meta.json" % p)
    dn = jload(SHAP + r"\out\%s\lead_0\treeroute_B1\rows.parquet.done.json" % p)
    FACTS["s330_%s_log_equals_meta_done" % p] = (mb1["pairs"] == int(m0.group(4)) and mb1["tree_shap_seconds"] == float(done.group(4))
                                                 and dn["seconds"] == float(done.group(3)))
I = A["b1"]["defo"]["identity"]
e30 = {"Largest absolute difference of the SHAP values, feature level (every row and player)": SCI2(I["max_abs_diff_phi"]),
       "Largest absolute difference of the SHAP values, variable level (every row and variable)": SCI2(I["max_abs_diff_phiv"]),
       "Rows, main run / B1 run": COUNT(I["n_rows_main"]) + " / " + COUNT(I["n_rows_b1"]),
       "Players, main run / B1 run": COUNT(I["n_players_main"]) + " / " + COUNT(I["n_players_b1"]),
       "Variables, main run / B1 run": COUNT(I["n_variables_main"]) + " / " + COUNT(I["n_variables_b1"]),
       "Same rows / players / variables": " / ".join("yes" if I[k] else "no" for k in ["same_rows", "same_players", "same_variables"])}
for rk, x in e30.items():
    check("S3.30", "b", rk, "Result", x, "s330b")
FACTS["defo_identity_exact_zero"] = (I["max_abs_diff_phi"] == 0.0 and I["max_abs_diff_phiv"] == 0.0 and I["as_expected"])
FACTS["b1_status"] = {p: A["b1"][p]["status"]["numbers"] for p in PROBS}

# ---------------------------------------------------------------- rounding once: traps
traps = []
for where, kind, x, _ in NUMS:
    if kind != "NUM2" or not fin(x):
        continue
    s = NUM2(x)
    a, b = alt_num2(x)
    if a != s or b != s:
        traps.append((where, x, s, a, b))
# percent cells: exact-decimal rounding against the float product
pct_flags = []
for c in CHECKS:
    if c["kind"] in ("family", "top10", "top10_nonzero", "b1top10") and fin(c.get("stored")) and c["stored"] > 0:
        x = c["stored"]
        exact = (Decimal(x) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_EVEN)
        if 100.0 * x >= 0.05 and format(exact, "f") != format(100.0 * x, ".1f"):
            pct_flags.append((c["table"], c["panel"], c["row"], c["col"], x))
FACTS["pct_float_product_vs_exact_decimal_differences"] = pct_flags

# a check that the trap cells print the single rounding: find each trap's printed token in its checked cell
n_ok = sum(1 for c in CHECKS if c["ok"])
bad = [c for c in CHECKS if not c["ok"]]
print("cells checked:", len(CHECKS), "ok:", n_ok, "mismatches:", len(bad))
for c in bad[:60]:
    print("MISMATCH", c["table"], c["panel"], c["row"], "|", c["col"], "| printed:", c["printed"], "| expected:", c["expected"])
by_table = {}
for c in CHECKS:
    by_table.setdefault(c["table"], [0, 0])
    by_table[c["table"]][0] += 1
    by_table[c["table"]][1] += 1 if c["ok"] else 0
print("per table (checked, ok):", by_table)
print("numbers formatted with NUM2 behind the checked cells:", sum(1 for n in NUMS if n[1] == "NUM2"))
print("double-rounding traps among them (a 3-decimal re-rounding would print otherwise):", len(traps))
for t_ in traps[:40]:
    print("  TRAP", t_)
print("FACTS:")
for k_, v_ in FACTS.items():
    print("  ", k_, "=", v_)
print("max |A - pairs.parquet| over the checked pair statistics:", max_A_minus_parquet)
json.dump({"checks": CHECKS, "traps": traps, "facts": {k: (v if not isinstance(v, float) else v) for k, v in FACTS.items()}},
          open(os.path.join(HERE, "k01_checks.json"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1, default=str)
