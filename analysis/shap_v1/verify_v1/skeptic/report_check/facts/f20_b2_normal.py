import pandas as pd, json
SHAP = r"D:\treeroute\analysis\shap_v1"
for p in ["fire", "pm25", "ndvi"]:
    fam = pd.read_parquet(SHAP + "\\out\\" + p + r"\lead_0\compare\families.parquet")
    t = fam[(fam.model == "treeroute")]
    print(p, {r.family: (r.mean_abs, r.share) for r in t.itertuples()})
# A's main-run counts vs B1: check 'nonzero' main J sizes and A-B 'b1' n_nonzero vs meta
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
print("A b1 defo identity:", json.dumps(A["b1"]["defo"].get("identity"))[:600])
print("A b1 defo run:", json.dumps(A["b1"]["defo"].get("run"))[:600])
