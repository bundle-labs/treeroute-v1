"""Report check 3: (1) are s41's 30 pair-levels exactly the pair-levels where a model of the pair has an exact
zero inside J (so that no other pair-level can have a tie-only member)? (2) which files the 16 byte reads are.
Read-only. Run: py -3.9 -I -B c07_ties_and_bytes.py
"""
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    A = load(V + r"\A\results.json")
    s41 = load(V + r"\skeptic\numbers\work\s41_tie_artifacts.json")
    with_zero = set()
    total = 0
    for p, P in A["problems"].items():
        for lev, L in P["levels"].items():
            nJ = L["active_set"]["n_J"]
            nJ = nJ["value"] if isinstance(nJ, dict) else nJ
            nz = {}
            for m, M in L["models"].items():
                v = M.get("n_nonzero")
                nz[m] = v["value"] if isinstance(v, dict) else v
            for pr in L.get("pairs", {}):
                total += 1
                a, b = pr.split("|")
                za = (nz.get(a) is not None and nz[a] < nJ)
                zb = (nz.get(b) is not None and nz[b] < nJ)
                if za or zb:
                    with_zero.add("%s/%s/%s" % (p, lev, pr))
    s41k = set(s41.keys())
    print("pair-levels in A:", total, "| with an exact zero inside J in either model:", len(with_zero),
          "| in s41:", len(s41k))
    print("in s41 but no zero in J:", sorted(s41k - with_zero))
    print("zero in J but not in s41:", sorted(with_zero - s41k))
    # s41's own zeros_in_J: does every listed pair have a zero?
    nozero = [k for k, r in s41.items() if not any((v or 0) > 0 for v in r["zeros_in_J"].values())]
    print("s41 pair-levels whose zeros_in_J are all 0:", nozero if nozero else "none")
    print()
    rows = [json.loads(x) for x in open(V + r"\reconcile\work\opened_official.jsonl", encoding="utf-8") if x.strip()]
    b = [r for r in rows if "bytes" in r["by"]]
    print("byte reads:", len(b), "| files:", sorted(set(r["file"] for r in b)))


if __name__ == "__main__":
    main()
