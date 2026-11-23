"""The largest collation move of each statistic, at full precision, from the skeptic's s41_tie_artifacts.json.

Usage: py -3.12 -X utf8 -I -B bardl_maxima.py <s41_tie_artifacts.json>
For BARDL pair-levels and for the others: per statistic, the largest (max - min) over the three collations, its
pair-level, the three values, and the spread rounded ONCE to three decimals (and, for tiny spreads, to three
significant digits). Figures for the report are to be taken from this output, rounded once.
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
    for g in ("BARDL", "other"):
        print("== %s pair-levels" % g)
        for s in STATS:
            best = None
            for key, rec in d.items():
                if ("rival_bardl_h1" in key) != (g == "BARDL"):
                    continue
                vals = [rec[c].get(s) for c in COLL]
                if not all(num(v) for v in vals):
                    continue
                sp = max(vals) - min(vals)
                if best is None or sp > best[0]:
                    best = (sp, key, vals)
            if best is None:
                continue
            sp, key, vals = best
            print("   %-13s spread %.10f -> %.3f (3 sig. %s) at %s; values %s" % (
                s, sp, sp, "%.3g" % sp, key, " / ".join("%.10f" % v for v in vals)))


if __name__ == "__main__":
    main()
