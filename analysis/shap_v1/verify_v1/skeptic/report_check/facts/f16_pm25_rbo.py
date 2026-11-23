import numpy as np, json
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
z = np.load(V + r"\A\draws\pm25.npz", allow_pickle=False)
keys = [k for k in z.files if "main_row" in k]
print("main_row keys:", keys[:40])
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
val = A["problems"]["pm25"]["main_row"]["rbo_p090_vs_consensus"]["value"]
for k in keys:
    if "rbo" in k:
        x = z[k]
        x = x[np.isfinite(x)]
        print(k, x.shape, "frac above full-sample", float((x > val).mean()), "frac >=", float((x >= val).mean()), "median", float(np.median(x)))
        q = np.percentile(x, [2.5, 97.5])
        print("  percentiles", q)
z2 = np.load(V + r"\A\draws\ndvi.npz", allow_pickle=False)
val2 = A["problems"]["ndvi"]["main_row"]["rbo_p090_vs_consensus"]["value"]
for k in z2.files:
    if "main_row" in k and "rbo" in k:
        x = z2[k]; x = x[np.isfinite(x)]
        print("ndvi", k, "frac above", float((x > val2).mean()))
