"""Report check 3: the BARDL collation figures of A4 (the numbers, item 1) against the skeptic's s41 file.
Read-only. Run: py -3.9 -I -B c03_s41_collation.py
"""
import json
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP

S41 = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\numbers\work\s41_tie_artifacts.json"
LOG = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile\work\opened_official.jsonl"
STATS = ["jaccard_top5", "jaccard_top10", "jaccard_top20", "rho20", "rbo090", "rbo095"]
COLL = ["base", "tie_ci", "tie_desc"]


def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x


def r3(x, nd=3):
    """One rounding step of the exact binary value, half-even and half-up (they should agree)."""
    q = Decimal(1).scaleb(-nd)
    a = Decimal(x).quantize(q, rounding=ROUND_HALF_EVEN)
    b = Decimal(x).quantize(q, rounding=ROUND_HALF_UP)
    return str(a) if a == b else "%s|%s" % (a, b)


def main():
    with open(S41, encoding="utf-8") as f:
        d = json.load(f)
    print("s41 pair-levels:", len(d), "| BARDL:", sum("rival_bardl_h1" in k for k in d),
          "| other:", sum("rival_bardl_h1" not in k for k in d))
    k0 = next(iter(d))
    print("record fields:", sorted(d[k0].keys()))
    print("base fields:", sorted(d[k0]["base"].keys()))
    # what makes a pair-level appear in s41? look at a non-BARDL record's non-collation fields
    other_keys = [k for k in d if "rival_bardl_h1" not in k]
    for k in other_keys[:2]:
        rec = d[k]
        extra = {kk: rec[kk] for kk in rec if kk not in COLL}
        print("example non-BARDL record", k, "extra fields:", json.dumps(extra)[:400])
    print()
    for grp in ("BARDL", "other"):
        keys = [k for k in d if (("rival_bardl_h1" in k) == (grp == "BARDL"))]
        print("== %s pairs (%d pair-levels)" % (grp, len(keys)))
        for s in STATS:
            best = None
            mixed = []
            for k in keys:
                vals = [d[k][c].get(s) for c in COLL]
                isn = [num(v) for v in vals]
                if any(isn) and not all(isn):
                    mixed.append((k, vals))
                if all(isn):
                    sp = max(vals) - min(vals)
                    if best is None or sp > best[0]:
                        best = (sp, k, vals)
            if best is None:
                print("   %-13s no numeric triple" % s)
                continue
            sp, k, vals = best
            print("   %-13s largest spread %.10f -> 3 dp %s (2 sig %.1e) at %s; values %s; mixed numeric/None: %s"
                  % (s, sp, r3(sp), sp, k, ["%.6f" % v for v in vals], mixed if mixed else "none"))
            # runner-up, to see how close the maximum is
            spreads = sorted(((max(v) - min(v)), kk) for kk in keys
                             for v in [[d[kk][c].get(s) for c in COLL]] if all(num(x) for x in v))
            if len(spreads) > 1:
                print("   %-13s runner-up %.10f at %s" % ("", spreads[-2][0], spreads[-2][1]))
        # tie-only members
        co = []
        for k in keys:
            for c in COLL:
                for kk in ("coincidental_top5", "coincidental_top10", "coincidental_top20"):
                    v = d[k][c].get(kk)
                    if v:
                        co.append((k, c, kk, v))
        print("   tie-only members (all collations):", co if co else "none")
        if grp == "other":
            # does any printed digit move at 2, 3 or 4 decimals?
            for nd in (2, 3, 4):
                moved = []
                for k in keys:
                    for s in STATS:
                        vals = [d[k][c].get(s) for c in COLL]
                        if all(num(v) for v in vals):
                            rr = set(r3(v, nd) for v in vals)
                            if len(rr) > 1:
                                moved.append((k, s, sorted(rr)))
                print("   digits moving at %d decimals: %d %s" % (nd, len(moved), moved if nd < 4 else moved[:6]))
            # per statistic: how many of the 22 move at all (> 0) and above 1e-12
            for s in STATS:
                n0 = n12 = 0
                for k in keys:
                    vals = [d[k][c].get(s) for c in COLL]
                    if all(num(v) for v in vals):
                        sp = max(vals) - min(vals)
                        n0 += sp > 0
                        n12 += sp > 1e-12
                print("   %-13s pairs with spread > 0: %d; > 1e-12: %d" % (s, n0, n12))
            # rho20/jaccard None counts among the 22
            for s in STATS:
                nn = sum(1 for k in keys if not all(num(d[k][c].get(s)) for c in COLL))
                print("   %-13s pair-levels with a non-numeric value in some collation: %d" % (s, nn))
        print()
    # A4's example cells
    ex = [
        ("ndvi/variable/rival_bardl_h1|treeroute", "jaccard_top5"),
        ("ndvi/variable/rival_bardl_h1|treeroute", "jaccard_top10"),
        ("ndvi/variable/rival_bardl_h1|treeroute", "rbo090"),
        ("ndvi/variable/rival_bardl_h1|rival_rf", "rho20"),
        ("ndvi/variable/rival_bardl_h1|rival_rf", "rbo095"),
        ("ndvi/variable/rival_bardl_h1|rival_lgbm", "rho20"),
        ("ndvi/feature/rival_bardl_h1|treeroute", "jaccard_top20"),
        ("ndvi/feature/rival_bardl_h1|treeroute", "rho20"),
        ("ndvi/feature/rival_bardl_h1|rival_ridge", "rho20"),
    ]
    for k, s in ex:
        vals = [d[k][c].get(s) for c in COLL]
        print("example %-42s %-13s %s" % (k, s, " / ".join(r3(v) if num(v) else str(v) for v in vals)))
    print()
    for k in d:
        if "rival_bardl_h1" in k:
            print("zeros_in_J", k, json.dumps(d[k].get("zeros_in_J")), "| n_J:", d[k].get("n_J", d[k]["base"].get("n_J")))


if __name__ == "__main__":
    main()
