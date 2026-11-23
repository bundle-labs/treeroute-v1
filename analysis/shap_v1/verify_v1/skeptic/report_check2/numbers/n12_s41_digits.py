"""n12: does any printed digit of a pair WITHOUT BARDL move under the three collations of s41? (2, 3, 4 decimals)
Read-only; prints only."""
import json
from decimal import Decimal, ROUND_HALF_EVEN

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
T = json.load(open(V + r"\skeptic\numbers\work\s41_tie_artifacts.json", encoding="utf-8"))


def r(x, nd):
    return format(Decimal(x).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_EVEN), "f")


for nd in (2, 3, 4):
    moved = []
    for k, e in T.items():
        if "bardl" in k:
            continue
        for s in ("jaccard_top5", "jaccard_top10", "jaccard_top20", "rho20", "rbo090", "rbo095"):
            if s not in e["base"]:
                continue
            vals = {c: r(e[c][s], nd) for c in ("base", "tie_ci", "tie_desc")}
            if len(set(vals.values())) > 1:
                moved.append((k, s, vals))
    print("decimals %d: non-BARDL cells whose printed value moves: %d" % (nd, len(moved)))
    for m in moved:
        print("   ", m)
