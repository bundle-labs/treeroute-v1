import json, collections
import pandas as pd
SHAP = r"D:\treeroute\analysis\shap_v1"
d = SHAP + r"\out\fire\lead_0\compare"
imp = pd.read_parquet(d + r"\importance.parquet")
fam = pd.read_parquet(d + r"\families.parquet")
t = imp[(imp.level == "variable") & (imp.model == "treeroute") & (imp.active)].sort_values(["share", "player"], ascending=[False, True])
print(t[["player", "share"]].head(4).to_string())
print(fam[fam.model == "treeroute"].to_string())
for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    per = json.load(open(SHAP + "\\out\\" + p + r"\lead_0\compare\per_lead.json", encoding="utf-8"))
    c = collections.Counter(per["families"].values())
    print(p, "families of variables:", dict(c))
# pairs.parquet: sign agreement rows with finite_replicates
for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    pr = pd.read_parquet(SHAP + "\\out\\" + p + r"\lead_0\compare\pairs.parquet")
    sa = pr[pr.statistic == "sign_agreement_top10"]
    print(p, "sign rows", len(sa), "finite_replicates values", sorted(sa.finite_replicates.unique().tolist()),
          "ci_low all NaN", bool(sa.ci_low.isna().all()), "value NaN count", int(sa.value.isna().sum()))
