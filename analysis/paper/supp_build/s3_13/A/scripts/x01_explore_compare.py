# Exploration only (prints to console): schemas and contents of the compare files.
import sys, json
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
PROBLEMS = ["pm25", "ndvi", "fire", "defo", "coral"]
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_rows", 400)
pd.set_option("display.max_colwidth", 120)

for p in PROBLEMS:
    C = SHAP + "\\out\\" + p + "\\lead_0\\compare\\"
    print("=" * 30, p)
    pr = pd.read_parquet(C + "pairs.parquet")
    print("pairs dtypes:", dict(pr.dtypes.astype(str)))
    print("pairs rows:", len(pr))
    for L in ["variable", "feature"]:
        s = pr[pr.level == L]
        print(L, "stats:", sorted(s.statistic.unique()))
        print(L, "pair labels:")
        for (a, b), g in s.groupby(["model_a", "model_b"]):
            print("   ", a, b, "|", sorted(g.pair_label.unique()))
    print(pr.head(3).to_string())
    sa = pr[pr.statistic == "sign_agreement_top10"]
    print(sa.to_string())
    fr = pr[pr.finite_replicates != 2000]
    print("finite != 2000:")
    print(fr.to_string())
    im = pd.read_parquet(C + "importance.parquet")
    print("importance dtypes:", dict(im.dtypes.astype(str)), len(im))
    print(im.head(3).to_string())
    fa = pd.read_parquet(C + "families.parquet")
    print("families dtypes:", dict(fa.dtypes.astype(str)), len(fa))
    print(fa.to_string())
