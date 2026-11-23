"""n08: collation spreads in the numbers skeptic's s41_tie_artifacts.json, BARDL pairs against the rest (A4, the
numbers, item 1). Read-only; prints only."""
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
T = json.load(open(V + r"\skeptic\numbers\work\s41_tie_artifacts.json", encoding="utf-8"))
print("entries:", len(T))
rows = []
for k, e in T.items():
    bardl = "bardl" in k
    sp = e["spread"]
    coinc = {c: e["base"].get(c) for c in ("coincidental_top5", "coincidental_top10", "coincidental_top20")
             if e["base"].get(c)}
    rows.append((bardl, k, sp, coinc))
for bardl in (False, True):
    print("==== BARDL pairs" if bardl else "==== pairs without BARDL")
    mx = {}
    for b, k, sp, coinc in rows:
        if b != bardl:
            continue
        for s, v in sp.items():
            if v > mx.get(s, (0, ""))[0]:
                mx[s] = (v, k)
        if not bardl and coinc:
            print("  tie-only overlap in a non-BARDL pair:", k, coinc)
    for s, (v, k) in sorted(mx.items()):
        print("  max spread %-13s %.3g  (%s)" % (s, v, k))
    n_above = sum(1 for b, k, sp, c in rows if b == bardl and any(v > 1e-12 for v in sp.values()))
    print("  pairs with any spread > 1e-12:", n_above, "of", sum(1 for r in rows if r[0] == bardl))

# The BARDL figures quoted in report.md A4 item 1 / A5 point 3
def g(k, c, s):
    return T[k][c][s]

q = [
    ("ndvi/variable/rival_bardl_h1|treeroute", "jaccard_top5", "0.25 (base)"),
    ("ndvi/variable/rival_bardl_h1|treeroute", "jaccard_top10", "0.25 (base)"),
    ("ndvi/variable/rival_bardl_h1|treeroute", "rbo090", "0.365 / 0.325"),
    ("ndvi/variable/rival_bardl_h1|rival_rf", "rho20", "0.162 / 0.038"),
    ("ndvi/variable/rival_bardl_h1|rival_rf", "rbo095", "0.241 / 0.322"),
    ("ndvi/variable/rival_bardl_h1|rival_lgbm", "rho20", "0.111 / 0.030"),
    ("ndvi/feature/rival_bardl_h1|treeroute", "jaccard_top20", "0.111 / 0.143 (ci)"),
    ("ndvi/feature/rival_bardl_h1|treeroute", "rho20", "-0.064 / -0.126 / 0.003"),
    ("ndvi/feature/rival_bardl_h1|rival_ridge", "rho20", "-0.471 / -0.393 / -0.362"),
    ("ndvi/variable/rival_bardl_h1|rival_ridge", "rho20", "(not quoted)"),
    ("ndvi/variable/rival_bardl_h1|rival_ridge", "rbo090", "(not quoted)"),
    ("ndvi/variable/rival_bardl_h1|rival_ridge", "rbo095", "(not quoted)"),
    ("ndvi/variable/rival_bardl_h1|rival_ridge", "jaccard_top10", "(not quoted)"),
    ("ndvi/variable/rival_bardl_h1|rival_lgbm", "rbo090", "(not quoted)"),
    ("ndvi/variable/rival_bardl_h1|rival_lgbm", "rbo095", "(not quoted)"),
    ("ndvi/variable/rival_bardl_h1|rival_lgbm", "jaccard_top10", "(not quoted)"),
    ("ndvi/variable/rival_bardl_h1|rival_rf", "rbo090", "(not quoted)"),
    ("ndvi/variable/rival_bardl_h1|treeroute", "rbo095", "(not quoted)"),
    ("ndvi/feature/rival_bardl_h1|treeroute", "rbo095", "(not quoted)"),
    ("ndvi/feature/rival_bardl_h1|rival_ridge", "rbo095", "(not quoted)"),
]
print("\n==== quoted figures: base / case-insensitive / descending")
for k, s, quoted in q:
    print("  %-42s %-14s %8.4f %8.4f %8.4f   report: %s" % (k, s, g(k, "base", s), g(k, "tie_ci", s),
                                                            g(k, "tie_desc", s), quoted))
# Jaccard top-5 without aet_total_mm (1/9) and top-10 without it (3/17)
print("1/9 =", 1 / 9, "3/17 =", 3 / 17)
print("zeros_in_J BARDL variable:", T["ndvi/variable/rival_bardl_h1|treeroute"]["zeros_in_J"],
      "feature:", T["ndvi/feature/rival_bardl_h1|treeroute"]["zeros_in_J"])
