"""Skeptic: latent-gap probes.
  1. Item 8: are there exact ties among the arcsine models' nonzero-forecast importances around the top 10
     (compare_shap.py orders them with np.argsort, without the name tie rule)?
  2. The reconciler's verdict ignores AOd/BOd: count official-derived keys that A or B lack (they would count as
     'match').
  3. The reconciler's classify() never looks at the AB status: per group, how many keys have AB != match (from the
     rerun's mismatches.json), next to what the group's diagnosis says.
  4. The official internal checks the reconciler ran (names only).
Read-only; stdout only."""
import collections
import json
import os

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
RER = V + r"\skeptic\reconcile\rerun"
RA = json.load(open(os.path.join(V, "A", "results.json"), encoding="utf-8"))
for p in ("coral", "fire"):
    nz = RA["problems"][p]["nonzero_forecast"]
    for m, d in nz["models"].items():
        sh = sorted(((v["share"]["value"], j) for j, v in d["players"].items()), key=lambda t: -t[0])
        top = sh[:12]
        ties = [(a, b) for a, b in zip(top, top[1:]) if a[0] == b[0]]
        print("item8", p, m, "rows", d["rows_used"], "12 largest shares distinct:", not ties, ties[:3])

M = json.load(open(os.path.join(RER, "mismatches.json"), encoding="utf-8"))
S = json.load(open(os.path.join(RER, "work", "summary.json"), encoding="utf-8"))
print("derived second check:", S["derived_second_check"])
ab = collections.defaultdict(collections.Counter)
for rec in M["keys"]:
    st = dict(x.split("=") for x in rec[3].split())
    ab[rec[1]][st["AB"]] += 1
diag = {g["group"]: g["diagnosis"] for g in M["groups"]}
for g, c in ab.items():
    says_agree = ("A and B" in diag[g] and ("agree" in diag[g] or "equal" in diag[g])) or "A = B" in diag[g]
    print("%-30s AB statuses %s ; diagnosis asserts A/B agreement: %s" % (g, dict(c), says_agree))
print("official internal checks (coral):")
for c, ok in S["official_internal_checks"]["coral"][:12]:
    print("   ", ok, c)
print("   ... total per problem:", {p: len(v) for p, v in S["official_internal_checks"].items()})
