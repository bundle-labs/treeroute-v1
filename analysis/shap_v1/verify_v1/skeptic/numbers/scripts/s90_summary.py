"""Skeptic (numbers lens): condense my comparisons into the 'checked' lines (mine | A | B | official)."""
import os, json, re
OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\numbers\work"


def fmt(x):
    if isinstance(x, float):
        return "%.12g" % x
    if isinstance(x, list):
        return "[" + ", ".join(fmt(y) for y in x) + "]"
    return str(x)


lines = []
rows = json.load(open(os.path.join(OUT, "s30_compare.json"), encoding="utf-8"))
coral_share = [r for r in rows if r["key"].startswith("coral/feature/treeroute/share/") or r["key"].startswith("coral/feature/treeroute/I/")]
other = [r for r in rows if r not in coral_share]


def maxdiff(rs, src):
    m = 0.0
    n = 0
    for r in rs:
        a, b = r["mine"], r[src]
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            m = max(m, abs(a - b) / max(1.0, abs(a)))
            n += 1
    return m, n


for r in other:
    lines.append("%s: mine %s | A %s | B %s | official %s" % (r["key"], fmt(r["mine"]), fmt(r["A"]), fmt(r["B"]),
                                                            fmt(r["official"]) if r["official"] is not None else "(no official)"))
for src in ["A", "B", "official"]:
    m, n = maxdiff(coral_share, src)
    lines.append("coral/feature/treeroute: all 68 players' I, share (value, ci_low, ci_high) and n_finite: largest |mine - %s| = %.3g (absolute; every value < 1) over %d numbers" % (src, m, n))
for fn, pref in [("s31_compare_b1.out.txt", "b1/"), ("s11_other_rows.out.txt", "main_row/"), ("s21_b1_more.out.txt", "b1/"),
                 ("s12_pairs_spot.out.txt", "pairs/")]:
    for ln in open(os.path.join(OUT, fn), encoding="utf-8").read().splitlines():
        ln = re.sub(r"np\.float64\(([^)]*)\)", r"\1", ln)
        if ln.startswith("differences"):
            continue
        lines.append(pref + ln)
open(os.path.join(OUT, "s90_checked_lines.txt"), "w", encoding="utf-8").write("\n".join(lines))
print(len(lines))
for ln in lines:
    print(ln)
