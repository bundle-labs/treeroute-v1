# Skeptic (version 4 check, item 2, V4-3): are coral's background survey visits at other locations (reef sites)?
# The coral visit key is "<site>|<date>" (site = region code, latitude, longitude). For each of the 1,000 explained
# visits (rows.parquet `row`, `unit`) and its 50 background visits (background_keys.parquet `row`, `unit`): how many
# background visits share the explained visit's site, and how many are the explained visit itself. Read-only.
import sys
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
base = SHAP + r"\out\coral\lead_0\treeroute"
B = pd.read_parquet(base + r"\background_keys.parquet")
R = pd.read_parquet(base + r"\rows.parquet", columns=["row", "unit", "time"])
print("explained rows %d, distinct explained units %d; background rows %d; per row: %s" % (
    len(R), R.unit.nunique(), len(B), B.groupby("row").size().describe().to_dict()))
site = lambda u: str(u).split("|")[0]
print("unit keys contain '|': explained %s, background %s" % (R.unit.astype(str).str.contains(r"\|").all(),
                                                               B.unit.astype(str).str.contains(r"\|").all()))
M = B.merge(R.rename(columns={"unit": "x_unit", "time": "x_time"}), on="row", how="left")
M["same_site"] = M.unit.map(site) == M.x_unit.map(site)
M["same_visit"] = M.unit == M.x_unit
print("background visits at the explained visit's own site: %d of %d (explained rows with any: %d); the explained visit itself: %d" % (
    int(M.same_site.sum()), len(M), int(M.groupby("row").same_site.any().sum()), int(M.same_visit.sum())))
print("background visits dated after the explained visit: %d" % int((M.time > M.x_time).sum()))
print("distinct sites: explained %d, background %d" % (R.unit.map(site).nunique(), B.unit.map(site).nunique()))
