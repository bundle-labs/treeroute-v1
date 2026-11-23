# Skeptic: claims of the draft notes that the data can settle. Read-only; prints only.
#  1. Table S3.19 note: structural zeros are "exactly 0 in every model at that level".
#  2. Table S3.29 note: every B1 player (both levels) has I, share and signed mean with an interval in results.json.
#  3. Table S3.21 note on D8: fire's and coral's E8 licence is gate E5a at this lead.
#  4. Table S3.25/S3.27 panel g: the nonzero-forecast top 10 are sorted by share (stored order), no tie at rank 10/11.
#  5. Table 9 note b: PM2.5 consensus top variable vs treeroute's top variable (the claim's premise).
#  6. Table S3.20 note a/b: which script wrote each rival exactness record (the record's own fields).
import json, sys, math
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
V = SHAP + r"\verify_v1"
PROBS = ["pm25", "ndvi", "fire", "defo", "coral"]

for p in PROBS:
    C = SHAP + r"\out\%s\lead_0\compare" % p
    PL = json.load(open(C + r"\per_lead.json", encoding="utf-8"))
    IM = pd.read_parquet(C + r"\importance.parquet")
    for L in ["variable", "feature"]:
        sz = PL[L]["structural_zero"]
        q = IM[(IM.level == L) & (IM.player.isin(sz))]
        n_rows = len(q)
        nz = q[q.mean_abs != 0.0]
        print("1.", p, L, "structural zeros", len(sz), "rows in importance.parquet", n_rows,
              "models", q.model.nunique(), "nonzero mean_abs:", len(nz),
              ("max %r" % float(nz.mean_abs.max())) if len(nz) else "")
        inact = IM[(IM.level == L) & (~IM.active)]
        print("   inactive players in importance.parquet:", inact.player.nunique(), "equal to the list:",
              sorted(inact.player.unique()) == sorted(sz))

A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
for p in ["pm25", "ndvi", "fire"]:
    for L in ["variable", "feature"]:
        pl = A["b1"][p][L]["importance"]["players"]
        ok = all(all(isinstance(o.get(k), dict) and o[k].get("n_finite") is not None for k in ["I", "share", "signed_mean"])
                 for o in pl.values())
        nfin = sorted(set(o["share"]["n_finite"] for o in pl.values()))
        print("2.", p, L, "B1 players", len(pl), "all with I/share/signed_mean intervals:", ok, "share n_finite values:", nfin)

for p in ["fire", "coral"]:
    g = json.load(open(SHAP + r"\rebuild\%s\lead_0\gates.json" % p, encoding="utf-8"))
    v = g["gates"]["E8_predictions"]["values"]
    print("3.", p, "E8 d8_licence:", v.get("d8_licence"), "| bit_identical", v["bit_identical"], "| rows_outside_tolerance",
          v["rows_outside_tolerance"], "| within_relative_tolerance", v.get("within_relative_tolerance"), "| tolerance", v.get("tolerance"))

for p in ["fire", "coral"]:
    PL = json.load(open(SHAP + r"\out\%s\lead_0\compare\per_lead.json" % p, encoding="utf-8"))
    for m, o in PL["nonzero_forecast_rows"].items():
        sh = [s for _, s in o["top10"]]
        print("4.", p, m, "rows", o["rows"], "sorted desc:", all(sh[i] >= sh[i + 1] for i in range(9)),
              "distinct:", len(set(sh)) == 10, "keys:", list(o.keys()))

IM = pd.read_parquet(SHAP + r"\out\pm25\lead_0\compare\importance.parquet")
AW = json.load(open(SHAP + r"\out\pm25\lead_0\compare\AW4_main_row.json", encoding="utf-8"))
riv = [m for m in AW["models_in_main_set"] if m != "treeroute"]
sh = IM[(IM.level == "variable") & (IM.active) & (IM.model.isin(riv))].pivot(index="player", columns="model", values="share")
c = sh.mean(axis=1).sort_values(ascending=False)
print("5. pm25 consensus top 4:", [(k, round(float(v), 5)) for k, v in c.iloc[:4].items()], "| treeroute top 1:", AW["treeroute_top3"][0])

for p in ["pm25", "coral"]:
    for m in ["rival_ridge", "rival_rf"]:
        e = json.load(open(SHAP + r"\out\%s\lead_0\%s\exactness.json" % (p, m), encoding="utf-8"))
        ks = [k for k in e.keys() if k in ("script", "writer", "tool", "by", "source", "note", "stage")]
        print("6.", p, m, {k: e[k] for k in ks}, "| keys:", list(e.keys())[:25])
