# Skeptic (version 4 check, item 2, V4-3): Table 9 and S3.19 note c now say coral's background is "survey visits at
# other locations" (a location = a reef site). PROTOCOL L375: "other sites' visits". Look at the coral background keys
# (SHAP\out\coral\lead_0\treeroute\background_keys.parquet, PROTOCOL L377) and the sample rows: their columns, and, if
# a site key is present, whether any background visit is at the explained visit's own site. Read-only; prints only.
import os, sys
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
base = SHAP + r"\out\coral\lead_0\treeroute"
f = base + r"\background_keys.parquet"
if not os.path.exists(f):
    print("background_keys.parquet not found")
    sys.exit(0)
B = pd.read_parquet(f)
print("background_keys columns:", list(B.columns), "| rows:", len(B))
print(B.head(3).to_string()[:1200])
R = pd.read_parquet(base + r"\rows.parquet", columns=None)
keys = [c for c in R.columns if not c.startswith(("phi", "phiv", "x__", "c__"))][:20]
print("rows.parquet key-like columns:", keys)
sitecols = [c for c in B.columns if "site" in c.lower()]
print("site-like columns in background keys:", sitecols)
