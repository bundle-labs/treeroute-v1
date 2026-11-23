# Skeptic: what the family shares (and so the own-history share of Table 9) are shares of.
# Compares, per problem and model, families.parquet's family share with the sum of the variable-level shares
# (importance.parquet, share = mean_abs / sum over J) of that family's variables. Read-only; prints only.
import json, sys
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    C = SHAP + r"\out\%s\lead_0\compare" % p
    PL = json.load(open(C + r"\per_lead.json", encoding="utf-8"))
    IM = pd.read_parquet(C + r"\importance.parquet")
    FA = pd.read_parquet(C + r"\families.parquet")
    fam = PL["families"]
    for m in sorted(PL["models"]):
        q = IM[(IM.level == "variable") & (IM.model == m) & (IM.active)].copy()
        tot = q.mean_abs.sum()
        dev = float((q.share - q.mean_abs / tot).abs().max())
        q["family"] = q.player.map(fam)
        vs = q.groupby("family").share.sum()
        f = FA[FA.model == m].set_index("family").share
        own_f = float(f.get("own history", float("nan")))
        own_v = float(vs.get("own history", 0.0))
        loc_f, loc_v = float(f.get("local drivers")), float(vs.get("local drivers", 0.0))
        print("%-6s %-20s share=mean_abs/sumJ (max dev %.1e) | family shares sum %.6f | own history: family %.4f vs sum of its variable shares %.4f | local drivers: %.4f vs %.4f"
              % (p, m, dev, float(f.sum()), own_f, own_v, loc_f, loc_v))
