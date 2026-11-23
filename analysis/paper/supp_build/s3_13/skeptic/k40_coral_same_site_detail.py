# Skeptic (version 4 check, item 2, V4-3): detail of k39. Of coral's 50,000 background visits, those at the explained
# visit's own site key (the part of the visit key before "|"): their dates against the explained visit's (strictly
# earlier?), how many background visits share the explained visit's date, the count per explained row, and three
# examples (keys shortened to the site key's region code). Read-only; prints only.
import sys
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
base = SHAP + r"\out\coral\lead_0\treeroute"
B = pd.read_parquet(base + r"\background_keys.parquet")
R = pd.read_parquet(base + r"\rows.parquet", columns=["row", "unit", "time", "group"])
M = B.merge(R.rename(columns={"unit": "x_unit", "time": "x_time"}), on="row", how="left")
site = lambda u: str(u).split("|")[0]
M["same_site"] = M.unit.map(site) == M.x_unit.map(site)
S = M[M.same_site]
print("same-site background visits: %d; strictly earlier than the explained visit: %d; same date: %d" % (
    len(S), int((S.time < S.x_time).sum()), int((S.time == S.x_time).sum())))
print("all background visits on the explained visit's date: %d" % int((M.time == M.x_time).sum()))
c = S.groupby("row").size()
print("explained rows with a same-site background visit: %d; per such row: min %d, median %d, max %d" % (
    len(c), c.min(), int(c.median()), c.max()))
print("regions (groups) of those explained rows: %d of %d" % (R[R.row.isin(c.index)].group.nunique(), R.group.nunique()))
for r in list(c.sort_values(ascending=False).index[:3]):
    x = R[R.row == r].iloc[0]
    same = S[S.row == r]
    print("   example row %d: explained visit date %s | %d of its 50 background visits at the same site key, dates %s" % (
        r, str(x.unit).split("|")[1], len(same), sorted(str(u).split("|")[1] for u in same.unit)[:6]))
