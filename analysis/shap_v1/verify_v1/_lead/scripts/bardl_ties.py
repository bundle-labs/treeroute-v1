"""Summarise the numbers skeptic's tie-collation file (s41_tie_artifacts.json): how far each statistic moves.

Usage: py -3.12 -X utf8 -I -B bardl_ties.py <s41_tie_artifacts.json>
For each pair-level, the three collations are base (code-point ascending, the one all sources used), tie_ci
(case-insensitive) and tie_desc (descending). Prints every BARDL pair-level in full, the largest spread per
statistic among BARDL pairs and among the other pairs, and any tie-only (coincidental) top-k member.
"""
import json
import sys

STATS = ["jaccard_top5", "jaccard_top10", "jaccard_top20", "rho20", "rbo090", "rbo095"]
COLL = ["base", "tie_ci", "tie_desc"]


def num(x):
    return isinstance(x, (int, float)) and x == x


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        d = json.load(f)
    groups = {"BARDL": {}, "other": {}}
    coincidental = {"BARDL": [], "other": []}
    for key, rec in d.items():
        g = "BARDL" if "rival_bardl_h1" in key else "other"
        for s in STATS:
            vals = [rec[c].get(s) for c in COLL]
            if all(num(v) for v in vals):
                spread = max(vals) - min(vals)
                best = groups[g].get(s)
                if best is None or spread > best[0]:
                    groups[g][s] = (spread, key, vals)
        for k in ("coincidental_top5", "coincidental_top10", "coincidental_top20"):
            if rec["base"].get(k):
                coincidental[g].append((key, k, rec["base"][k]))
        if g == "BARDL":
            print("==", key, "| zeros_in_J:", json.dumps(rec.get("zeros_in_J")))
            for s in STATS:
                vals = [rec[c].get(s) for c in COLL]
                txt = " / ".join(("%.4f" % v) if num(v) else str(v) for v in vals)
                print("   %-13s %s" % (s, txt))
    for g in ("BARDL", "other"):
        n = sum(1 for k in d if (("rival_bardl_h1" in k) == (g == "BARDL")))
        print()
        print("largest spread per statistic, %s pairs (%d pair-levels):" % (g, n))
        for s in STATS:
            if s in groups[g]:
                sp, key, vals = groups[g][s]
                print("   %-13s %.3g  at %s  (%s)" % (s, sp, key, " / ".join("%.6f" % v for v in vals)))
        print("tie-only (coincidental) top-k members under base, %s pairs:" % g, coincidental[g] or "none")


if __name__ == "__main__":
    main()
