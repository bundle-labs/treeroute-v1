# Read-only. Print the BARDL pairs' values under the three collations from s41 (A4, the numbers, item 1).
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
d = json.load(open(V + r"\skeptic\numbers\work\s41_tie_artifacts.json", encoding="utf-8"))
for k, v in d.items():
    if "bardl" not in k:
        continue
    print("==", k, "zeros_in_J", v.get("zeros_in_J"))
    for s in ("jaccard_top5", "jaccard_top10", "jaccard_top20", "rho20", "rbo090", "rbo095"):
        vals = [v[c].get(s) for c in ("base", "tie_ci", "tie_desc")]
        print("   %-13s base %-8s ci %-8s desc %-8s" % (s, *("%.4f" % x if isinstance(x, (int, float)) else str(x)
                                                         for x in vals)))
