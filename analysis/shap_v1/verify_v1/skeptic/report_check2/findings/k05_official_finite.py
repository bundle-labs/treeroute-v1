# Read-only. Distribution of finite_replicates in the official pairs.parquet files (all problems), to see
# whether compare_shap's outputs already give intervals with fewer than 2,000 finite replicates.
import collections
import pandas as pd

SHAP = r"D:\treeroute\analysis\shap_v1"
for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    f = SHAP + r"\out\%s\lead_0\compare\pairs.parquet" % p
    df = pd.read_parquet(f)
    cols = list(df.columns)
    if p == "coral":
        print("columns:", cols)
    c = collections.Counter()
    thin = []
    for _, r in df.iterrows():
        n = r.get("finite_replicates")
        st = r.get("statistic")
        c[(st, int(n) if pd.notna(n) else None)] += 1
        if pd.notna(n) and 0 < int(n) < 2000:
            thin.append((r.get("level"), r.get("pair") if "pair" in cols else (r.get("model_a"), r.get("model_b")),
                         st, r.get("value"), r.get("ci_low"), r.get("ci_high"), int(n)))
    print("==", p, "rows", len(df))
    for k in sorted(c, key=lambda x: (str(x[0]), -1 if x[1] is None else x[1])):
        if k[1] != 2000:
            print("   statistic %-28s finite %-6s rows %d" % (k[0], k[1], c[k]))
    for t in thin:
        print("   THIN:", t)
