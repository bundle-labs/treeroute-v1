# Skeptic (version 4 check, item 2, V4-4): on NDVI the five router-context columns ctx:top5:* are merged with the tree
# columns they copy (meta.json duplicates_merged), so their attribution counts in "local drivers", not in "context and
# calendar". How large are those five variables, and what does the "context and calendar" family get, per model?
# From SHAP\out\ndvi\lead_0\compare\importance.parquet (variable level) and families.parquet. Read-only; prints only.
import json, sys
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
C = SHAP + r"\out\ndvi\lead_0\compare"
IM = pd.read_parquet(C + r"\importance.parquet")
FA = pd.read_parquet(C + r"\families.parquet")
PL = json.load(open(C + r"\per_lead.json", encoding="utf-8"))
five = ["mean_temp_C", "total_ref_ET_mm", "era5l_d2m", "era5l_slhf", "sph_kgkg"]
print("families of the five variables:", {v: PL["families"].get(v) for v in five})
for m in PL["models"]:
    q = IM[(IM.level == "variable") & (IM.model == m)].set_index("player")
    s = {v: round(float(q.share.get(v, float("nan"))), 4) for v in five}
    tot = sum(x for x in s.values() if x == x)
    f = FA[FA.model == m].set_index("family").share
    print("%-16s variable shares of the five: %s (sum %.4f) | family 'context and calendar' share %.4f | 'local drivers' %.4f" % (
        m, s, tot, float(f.get("context and calendar", float("nan"))), float(f.get("local drivers", float("nan")))))
