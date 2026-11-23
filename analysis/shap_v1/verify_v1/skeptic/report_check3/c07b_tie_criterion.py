"""Report check 3: which pair-levels have a tie (two or more exact zeros inside J in one model of the pair), and
does s41 list exactly those? Also the smallest nonzero count of any non-BARDL model (a tie-only top-k member
needs fewer than k nonzero players). Read-only. Run: py -3.9 -I -B c07b_tie_criterion.py
"""
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def val(x):
    return x["value"] if isinstance(x, dict) else x


def main():
    A = load(V + r"\A\results.json")
    s41 = load(V + r"\skeptic\numbers\work\s41_tie_artifacts.json")
    tie2 = set()
    min_nz = None
    for p, P in A["problems"].items():
        for lev, L in P["levels"].items():
            nJ = val(L["active_set"]["n_J"])
            zeros = {m: nJ - val(M["n_nonzero"]) for m, M in L["models"].items() if M.get("n_nonzero") is not None}
            for m, M in L["models"].items():
                if "bardl" not in m and M.get("n_nonzero") is not None:
                    nz = val(M["n_nonzero"])
                    if min_nz is None or nz < min_nz[0]:
                        min_nz = (nz, p, lev, m)
            for pr in L.get("pairs", {}):
                a, b = pr.split("|")
                if zeros.get(a, 0) >= 2 or zeros.get(b, 0) >= 2:
                    tie2.add("%s/%s/%s" % (p, lev, pr))
    s = set(s41)
    print("pair-levels with >= 2 exact zeros inside J in a model of the pair:", len(tie2), "| s41:", len(s))
    print("   in s41, not tied:", sorted(s - tie2))
    print("   tied, not in s41:", sorted(tie2 - s))
    print("smallest nonzero count of a non-BARDL model (value, problem, level, model):", min_nz)
    # zeros_in_J from s41 against A's counts for the listed pairs
    bad = []
    for k, r in s41.items():
        p, lev, pr = k.split("/")
        L = A["problems"][p]["levels"][lev]
        nJ = val(L["active_set"]["n_J"])
        for m, z in r["zeros_in_J"].items():
            za = nJ - val(L["models"][m]["n_nonzero"])
            if za != z:
                bad.append((k, m, z, za))
    print("s41 zeros_in_J that differ from A's n_J - n_nonzero:", bad if bad else "none")


if __name__ == "__main__":
    main()
