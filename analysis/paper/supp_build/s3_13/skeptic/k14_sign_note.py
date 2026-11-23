# Skeptic (version 2 check of C7 and of the AW3 caption): the sign-agreement cells against A's finite-draw counts, and
# every interval cell of Tables S3.23-S3.27 whose finite count is below 2,000. Read-only; prints only.
import json, os, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
SHAP = r"D:\treeroute\analysis\shap_v1"
A = json.load(open(SHAP + r"\verify_v1\A\results.json", encoding="utf-8"))
J = json.load(open(os.path.join(OUT, "reconcile", "cells.json"), encoding="utf-8"))
P = {"S3.23": "pm25", "S3.24": "ndvi", "S3.25": "fire", "S3.26": "defo", "S3.27": "coral"}
LV = {"a": "variable", "b": "feature"}
kinds = Counter()
seen = set()
for e in J["entries"]:
    if e["table"] in P and e["column"] == "sign_agreement_top10" and e["part"] == "value":
        p, L = P[e["table"]], LV[e["panel"]]
        s = A["problems"][p]["levels"][L]["pairs"][e["row"]]["sign_agreement"]
        nf = s["n_finite"]
        undefined = e["printed"] == "undefined"
        has_ci = "[" in e["cell"]
        kinds[(undefined, has_ci, "nf=0" if nf == 0 else ("nf<2000" if nf < 2000 else "nf=2000"))] += 1
print("sign-agreement cells by (undefined on the full sample, interval printed, A n_finite):")
for k, v in sorted(kinds.items()):
    print("   ", k, v)
# interval cells of the AW3 tables with fewer than 2,000 finite draws, any statistic (from the stored records)
low = []
for p in P.values():
    import pandas as pd
    PR = pd.read_parquet(SHAP + r"\out\%s\lead_0\compare\pairs.parquet" % p)
    q = PR[(PR.statistic != "sign_agreement_top10") & (PR.finite_replicates < 2000)]
    for r in q.itertuples():
        low.append((p, r.level, r.model_a, r.model_b, r.statistic, int(r.finite_replicates), r.value))
    PL = json.load(open(SHAP + r"\out\%s\lead_0\compare\per_lead.json" % p, encoding="utf-8"))
    for L in ["variable", "feature"]:
        for k in ["kendall_w_main_set", "mean_pairwise_spearman_main_set"]:
            if PL[L][k]["finite_replicates"] < 2000:
                low.append((p, L, "main set", "", k, PL[L][k]["finite_replicates"], PL[L][k]["value"]))
print("non-sign interval statistics of the AW3 tables with fewer than 2,000 finite draws:", low)
