"""n07: finite counts of the main pairs' intervals in A and B (A5 point 1's three thin fire sign-agreement
intervals; group 2's 7 pair-levels with 0 finite; any other interval under 2,000). Read-only; prints only."""
import json
from collections import Counter

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
B = json.load(open(V + r"\B\results.json", encoding="utf-8"))


def iter_intervals(x, path):
    if isinstance(x, dict):
        if "n_finite" in x and ("ci_low" in x or "value" in x):
            yield path, x
        for k, v in x.items():
            if isinstance(v, (dict, list)):
                yield from iter_intervals(v, path + "/" + k)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            if isinstance(v, (dict, list)):
                yield from iter_intervals(v, path + "/%d" % i)


for who, R in (("A", A), ("B", B)):
    print("=====", who)
    n_pl = 0
    sign = []
    for p, P in R["problems"].items():
        for lev, L in P["levels"].items():
            for pair, Q in L["pairs"].items():
                n_pl += 1
                sa = Q.get("sign_agreement")
                if sa is None:
                    sign.append((p, lev, pair, None))
                    continue
                sign.append((p, lev, pair, sa.get("value"), sa.get("ci_low"), sa.get("ci_high"), sa.get("n_finite")))
    print("pair-levels:", n_pl)
    nf = Counter()
    for s in sign:
        nf[s[-1] if len(s) > 4 else "no entry"] += 1
    print("sign agreement n_finite distribution:", sorted(nf.items(), key=lambda kv: str(kv[0])))
    for s in sign:
        if len(s) > 4 and s[-1] not in (2000,):
            print("   ", s)
    # every interval anywhere under problems with 0 < n_finite < 2000 (other than sign agreement)
    other = []
    zero = Counter()
    for path, e in iter_intervals(R["problems"], "problems"):
        n = e.get("n_finite")
        if n is None:
            continue
        if n == 0:
            zero[path.split("/")[-1]] += 1
        if 0 < n < 2000 and not path.endswith("sign_agreement"):
            other.append((path, n))
    print("intervals with 0 finite (by last key):", dict(zero))
    print("other intervals with 0 < n_finite < 2000:", len(other))
    for o in other[:30]:
        print("   ", o)
    # B1 intervals with n_finite != 2000
    b1bad = [(path, e.get("n_finite")) for path, e in iter_intervals(R["b1"], "b1")
             if e.get("n_finite") is not None and e.get("n_finite") != 2000]
    print("b1 intervals with n_finite != 2000:", len(b1bad), b1bad[:10])
