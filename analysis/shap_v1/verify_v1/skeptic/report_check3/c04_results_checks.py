"""Report check 3: numbers of A5 point 1 and A6 against A's and B's results.json, and NDVI's BARDL J sizes.
Read-only. Run: py -3.9 -I -B c04_results_checks.py
"""
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
S41 = V + r"\skeptic\numbers\work\s41_tie_artifacts.json"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def walk(o, path=""):
    if isinstance(o, dict):
        yield path, o
        for k, v in o.items():
            yield from walk(v, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, path + "[%d]" % i)


def main():
    A = load(V + r"\A\results.json")
    B = load(V + r"\B\results.json")
    print("A top keys:", list(A.keys())[:12])
    fire_pairs_A = A["problems"]["fire"]["levels"]["variable"]["pairs"]
    fire_pairs_B = B["problems"]["fire"]["levels"]["variable"]["pairs"]
    print("fire variable pairs:", sorted(fire_pairs_A.keys()))
    for pr in ("rival_ridge|treeroute", "rival_lgbm|treeroute", "rival_rf|treeroute"):
        for tag, P in (("A", fire_pairs_A), ("B", fire_pairs_B)):
            sa = P.get(pr, {}).get("sign_agreement")
            print("   %s %-24s sign_agreement: %s" % (tag, pr, json.dumps(sa)[:300]))
    # every interval record with 0 < n_finite < 2000 in A and in B (main problems and b1)
    for tag, R in (("A", A), ("B", B)):
        thin = []
        zero = 0
        nrec = 0
        for path, o in walk(R):
            if "n_finite" in o and isinstance(o.get("n_finite"), int):
                nrec += 1
                n = o["n_finite"]
                if n == 0:
                    zero += 1
                elif n < 2000:
                    thin.append((path, n, o.get("value"), o.get("ci_low"), o.get("ci_high")))
        print("%s: records with n_finite: %d; with n_finite 0: %d; with 0 < n_finite < 2000: %d" % (tag, nrec, zero, len(thin)))
        for t in thin:
            print("    ", t)
    # B1 nonzero counts in results.json
    for tag, R in (("A", A), ("B", B)):
        b1 = R.get("b1", {})
        for p in ("fire", "pm25", "ndvi", "defo", "coral"):
            if p not in b1:
                print("%s b1 has no %s" % (tag, p))
                continue
            for lev in ("feature", "variable"):
                imp = b1[p].get(lev, {}).get("importance") if isinstance(b1[p].get(lev), dict) else None
                if imp is None:
                    print("%s b1/%s/%s: no importance (keys %s)" % (tag, p, lev, list(b1[p].keys())[:10]))
                    continue
                print("%s b1/%s/%s/importance: n_nonzero=%s n_nonzero_before_merge=%s | keys: %s" % (
                    tag, p, lev, imp.get("n_nonzero"), imp.get("n_nonzero_before_merge"),
                    [k for k in imp.keys() if k != "players"][:12]))
    # NDVI J sizes for the BARDL pairs, both levels
    s41 = load(S41)
    for lev in ("variable", "feature"):
        L = A["problems"]["ndvi"]["levels"][lev]
        Jkeys = [k for k in L.keys()]
        print("ndvi %s level keys: %s" % (lev, Jkeys[:15]))
        J = L.get("J")
        if isinstance(J, dict):
            print("   J fields:", list(J.keys())[:10])
        for pr in ("rival_bardl_h1|treeroute", "rival_bardl_h1|rival_ridge"):
            rec = L["pairs"].get(pr, {})
            nj = None
            for k in ("n_J", "J_size", "pair_J", "nJ"):
                if k in rec:
                    nj = rec[k]
            print("   pair %s: fields %s | n_J %s" % (pr, list(rec.keys())[:20], json.dumps(nj)[:80]))
        z = s41["ndvi/%s/rival_bardl_h1|treeroute" % lev]["zeros_in_J"]["rival_bardl_h1"]
        print("   s41 zeros_in_J for BARDL at %s level: %s" % (lev, z))


if __name__ == "__main__":
    main()
