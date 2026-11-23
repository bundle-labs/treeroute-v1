# n09: re-read the named source files (read-only) and check the values the facts A10-A24 print, independently of
# cells.json. Prints one line per check: OK or BAD.
import json
import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
S = r"D:\treeroute\analysis\shap_v1"
P = ["pm25", "ndvi", "fire", "defo", "coral"]
nbad = 0


def load(p):
    with open(p, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def chk(name, got, want):
    global nbad
    ok = got == want
    if not ok:
        nbad += 1
    print("%-4s %s: got %r want %r" % ("OK" if ok else "BAD", name, got, want))


def f2(x):
    s = format(x, ".2f")
    return ("\u2212" + s[1:]) if s.startswith("-") and s != "-0.00" else ("0.00" if s == "-0.00" else s)


def fp(x):
    return format(x * 100, ".1f") + "%"


pl = {p: load(os.path.join(S, "out", p, "lead_0", "compare", "per_lead.json")) for p in P}
aw = {p: load(os.path.join(S, "out", p, "lead_0", "compare", "AW4_main_row.json")) for p in P}
gt = {p: load(os.path.join(S, "rebuild", p, "lead_0", "gates.json")) for p in P}
sm = {p: load(os.path.join(S, "sample", p, "sample_manifest.json")) for p in P}

# A10
for p in P:
    chk("A10 %s rows" % p, pl[p]["rows"], 1000)
    chk("A10 %s draws" % p, pl[p]["draws"], 2000)
    chk("A10 %s salt" % p, pl[p]["salt"], "shap_v1|AW4|%s|0" % p)
    chk("A10 %s j_rule" % p, pl[p]["j_rule"], "player active when some model gives it > 1e-12 of its total")
chk("A10/A14 regions range", (min(pl[p]["regions"] for p in P), max(pl[p]["regions"] for p in P)), (37, 133))

# A14 samples
want14 = {"pm25": (91428, 127, 254), "ndvi": (94527, 133, 266), "fire": (94702, 40, 280), "defo": (369096, 42, 252),
          "coral": (2312, 37, 1000)}
for p in P:
    chk("A14 %s frame/regions/units" % p, (sm[p]["frame_rows"], sm[p]["regions_in_sample"], sm[p]["units_in_sample"]), want14[p])
    chk("A14 %s n" % p, sm[p]["n"], 1000)
    if p != "coral":
        per = sm[p]["units_in_sample"] / sm[p]["regions_in_sample"]
        import math
        ceil = math.ceil(1000 / (sm[p]["regions_in_sample"] * 4))
        chk("A14 %s per-region units = ceil(N/(G*4))" % p, (per, ceil), (float(ceil), ceil))
    print("     %s rows_per_year %s per_lead regions %s" % (p, sm[p].get("rows_per_year"), pl[p]["regions"]))

# A11
mc = load(os.path.join(S, r"out\coral\lead_0\treeroute\meta.json"))
chk("A11 coral pairs", mc["pairs"], 50000)
chk("A11 coral background_rows lead0", sm["coral"]["background_rows"]["0"], sm["coral"]["background_rows"]["0"])
print("     coral background_rows['0'] =", sm["coral"]["background_rows"]["0"])

# A13 duplicates_merged in meta.json of every piece
for p in P:
    d = os.path.join(S, "out", p, "lead_0")
    for m in sorted(os.listdir(d)):
        mp = os.path.join(d, m, "meta.json")
        if m != "compare" and os.path.isfile(mp):
            mm = load(mp)
            dm = mm.get("duplicates_merged")
            dmv = dm if not isinstance(dm, (list, dict)) else len(dm)
            print("     %s %s duplicates_merged=%r s_zero_viol=%r pairs=%r" % (p, m, dmv, mm.get("structural_zero_violations"), mm.get("pairs")))

# A15 BARDL
v = pl["ndvi"]["variable"]
f = pl["ndvi"]["feature"]
chk("A15 bardl nonzero vars", v["nonzero_players"]["rival_bardl_h1"], 3)
chk("A15 bardl nonzero players", f["nonzero_players"]["rival_bardl_h1"], 9)
chk("A15 ndvi J var/feat", (v["active"], f["active"]), (96, 479))
chk("A15 93 of 96 / 470 of 479", (v["active"] - 3, f["active"] - 9), (93, 470))
print("     ndvi main_set", pl["ndvi"]["main_set"], "links bardl", pl["ndvi"]["links"].get("rival_bardl_h1"), "treeroute", pl["ndvi"]["links"].get("treeroute"))

# A16-A18 from AW4_main_row
A16 = {"pm25": "0.85 [0.85, 0.86]", "ndvi": "0.62 [0.61, 0.62]", "defo": "0.80 [0.78, 0.81]", "coral": "0.73 [0.69, 0.76]"}
A17s = {"pm25": "\u22120.02 [\u22120.08, 0.07]", "ndvi": "0.07 [\u22120.01, 0.12]", "defo": "0.20 [0.14, 0.29]", "coral": "0.48 [0.39, 0.55]"}
A17r = {"pm25": "0.37 [0.36, 0.57]", "ndvi": "0.40 [0.38, 0.43]", "defo": "0.63 [0.61, 0.75]", "coral": "0.67 [0.61, 0.78]"}
A18t = {"pm25": "0.19 [0.16, 0.21]", "ndvi": "0.24 [0.22, 0.27]", "defo": "0.29 [0.25, 0.33]", "coral": "0.00 [0.00, 0.00]"}
A18m = {"pm25": "0.30 [0.28, 0.32]", "ndvi": "0.26 [0.24, 0.28]", "defo": "0.35 [0.32, 0.40]", "coral": "0.00 [0.00, 0.00]"}


def cell(o):
    return "%s [%s, %s]" % (f2(o["value"]), f2(o["ci"][0]), f2(o["ci"][1]))


for p in ["pm25", "ndvi", "defo", "coral"]:
    a = aw[p]
    chk("A16 %s W" % p, cell(a["kendall_w"]), A16[p])
    chk("A17 %s spearman" % p, cell(a["treeroute_vs_same_link_rivals_median_spearman_top20_union"]), A17s[p])
    chk("A17 %s rbo" % p, cell(a["rbo_vs_consensus_p0.9"]), A17r[p])
    chk("A18 %s own tr" % p, cell(a["own_history_share_treeroute"]), A18t[p])
    chk("A18 %s own med" % p, cell(a["own_history_share_median_rival"]), A18m[p])
    print("     %s finite reps W %s sp %s rbo %s" % (p, a["kendall_w"]["ci"][2], a["treeroute_vs_same_link_rivals_median_spearman_top20_union"]["ci"][2], a["rbo_vs_consensus_p0.9"]["ci"][2]))
chk("A16 fire W undefined", aw["fire"]["kendall_w"]["value"], None)
print("     fire AW4:", json.dumps(aw["fire"])[:800])

# results.json
R = load(os.path.join(S, r"verify_v1\A\results.json"))
fm = R["problems"]["fire"]["main_row"]
o = fm["own_history_share_treeroute"]
chk("A18 fire own tr (results)", "%s [%s, %s]" % (f2(o["value"]), f2(o["ci_low"]), f2(o["ci_high"])), "0.14 [0.11, 0.16]")
print("     fire main_row keys:", list(fm.keys()))
print("     fire main_row top3:", fm.get("treeroute_top3"))
for p, want in (("pm25", ("70.3%", "67.4%", "73.1%")), ("ndvi", ("44.3%", "40.5%", "48.0%")), ("fire", ("81.1%", "71.6%", "87.3%"))):
    sn = R["b1"][p]["variable"]["families"]["seasonal_normal"]
    chk("A22 %s B1 seasonal normal" % p, (fp(sn["value"]), fp(sn["ci_low"]), fp(sn["ci_high"])), want)
    t3 = R["b1"][p]["variable"]["top3"]
    print("     %s B1 top3 %s" % (p, t3))
for p, w in (("pm25", "44.5%"), ("ndvi", "32.1%"), ("fire", "54.2%")):
    t3 = R["b1"][p]["variable"]["top3"]
    chk("A22 %s top var normal share" % p, (t3[0][0], fp(t3[0][1])), ("normal", w))
idn = R["b1"]["defo"]["identity"]
print("     defo identity:", idn)
chk("A21 defo identity", (idn["max_abs_diff_phi"], idn["max_abs_diff_phiv"], idn["n_rows_main"], idn["n_rows_b1"],
                          idn["n_players_main"], idn["n_players_b1"], idn["n_variables_main"], idn["n_variables_b1"]),
    (0.0, 0.0, 1000, 1000, 309, 309, 121, 121))
pairs = R["problems"]["fire"]["levels"]["variable"]["pairs"]
for k, w in (("rival_ridge|treeroute", 64), ("rival_lgbm|treeroute", 1140), ("rival_rf|treeroute", 1380)):
    sa = pairs[k]["sign_agreement"]
    chk("A24 %s n_finite" % k, sa["n_finite"], w)
    chk("A24 %s ci" % k, (f2(sa["ci_low"]), f2(sa["ci_high"])), ("0.00", "1.00"))
    print("     %s sign_agreement %s" % (k, {kk: vv for kk, vv in sa.items() if kk not in ("draws",)}))
# every sign-agreement n_finite in results.json below 2000 (all problems, both levels)
low = []
for p in P:
    for lv in ("feature", "variable"):
        for k, pr in R["problems"][p]["levels"][lv]["pairs"].items():
            sa = pr.get("sign_agreement")
            if sa and sa.get("n_finite") is not None and sa["n_finite"] < 2000:
                low.append((p, lv, k, sa["n_finite"]))
chk("A24 thin intervals (all problems, levels)", sorted(low), sorted([("fire", "variable", "rival_ridge|treeroute", 64), ("fire", "variable", "rival_lgbm|treeroute", 1140), ("fire", "variable", "rival_rf|treeroute", 1380)]))

# A19
w19 = {("fire", "treeroute"): 226, ("coral", "treeroute"): 973, ("coral", "rival_rf"): 1000, ("coral", "rival_lgbm"): 995, ("coral", "rival_hgb_l1"): 983}
for (p, m), w in w19.items():
    chk("A19 %s %s nonzero rows" % (p, m), pl[p]["nonzero_forecast_rows"][m]["rows"], w)
for p in P:
    print("     %s nonzero_forecast_rows models: %s" % (p, list(pl[p].get("nonzero_forecast_rows", {}).keys())))

# A12 gates
for p in P:
    g = gt[p]["gates"]
    e8 = g["E8_predictions"]["values"]
    print("     %s result=%s E5.pass=%s E8 rows=%s pre_bit_equal=%s max_rel_pre=%r E5a=%s" % (
        p, gt[p]["result"], g["E5_bank_fingerprint"]["pass"], e8["rows_checked"], e8["pre_bit_equal"], e8.get("max_rel_pre"),
        {k: g["E5a_identity_twin"]["values"].get(k) for k in ("rows_checked", "pre_bit_equal")} if "E5a_identity_twin" in g else None))
    print("        E5 role: %s" % g["E5_bank_fingerprint"]["values"].get("role"))
e3a = gt["coral"]["gates"]["E3a_inputs_before_read"]["values"]
print("     coral E3a:", json.dumps(e3a)[:1500])
import hashlib
print("     sha256('[]') =", hashlib.sha256(b"[]").hexdigest())

# families.parquet
for p in P:
    fam = pd.read_parquet(os.path.join(S, "out", p, "lead_0", "compare", "families.parquet"))
    if p == "pm25":
        print("     families columns:", list(fam.columns), "rows", len(fam))
    lvcol = "level" if "level" in fam.columns else None
    sub = fam[fam[lvcol] == "variable"] if lvcol else fam
    for fname in ("own history", "context and calendar", "seasonal normal"):
        r = sub[sub["family"] == fname]
        print("     %s %s: %s" % (p, fname, {row["model"]: row["share"] for _, row in r.iterrows()}))
print("BAD:", nbad)
