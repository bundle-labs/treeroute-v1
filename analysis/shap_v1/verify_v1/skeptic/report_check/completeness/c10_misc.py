"""Read-only: a few small checks of statements in report.md."""
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
S = json.load(open(V + r"\reconcile\work\summary.json", encoding="utf-8"))
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
B = json.load(open(V + r"\B\results.json", encoding="utf-8"))

oc = S["official_internal_checks"]
n = sum(len(v) for v in oc.values())
t = sum(1 for v in oc.values() for row in v if row[1] is True)
print("official internal checks:", t, "of", n, "true")

for X, R in (("A", A), ("B", B)):
    sa = R["problems"]["fire"]["levels"]["variable"]["pairs"]["rival_ridge|treeroute"]["sign_agreement"]
    nd = R["problems"]["fire"]["levels"]["variable"]["pairs"]["rival_ridge|treeroute"].get("sign_n_determined")
    print(X, "fire variable rival_ridge|treeroute sign_agreement", json.dumps(sa), "n_det", json.dumps(nd))

# how many of the 95 evaluated sign-agreement pair-levels have fewer than 2,000 finite replicates (A)
low = []
for p, P in A["problems"].items():
    for lev, L in P["levels"].items():
        for pair, pr in L.get("pairs", {}).items():
            sa = pr.get("sign_agreement")
            if isinstance(sa, dict) and sa.get("n_finite") is not None and sa.get("n_finite") < 2000:
                low.append((p, lev, pair, sa.get("value"), sa.get("ci_low"), sa.get("ci_high"), sa.get("n_finite")))
print("sign-agreement pair-levels with n_finite < 2000 (A):", len(low))
for r in sorted(low, key=lambda r: r[-1]):
    print("   ", r)

# the coral main-row own-history entries in B and A (C15)
for X, R in (("A", A), ("B", B)):
    mr = R["problems"]["coral"]["main_row"]
    print(X, "coral own_history_share_treeroute", json.dumps(mr.get("own_history_share_treeroute")),
          "why:", str(mr.get("own_history_share_treeroute_why"))[:200])
