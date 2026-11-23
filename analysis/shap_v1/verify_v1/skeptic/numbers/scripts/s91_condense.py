"""Skeptic (numbers lens): one line per statistic: mine | A | B | official (value [ci_low, ci_high] n_finite)."""
import os, re, json
from collections import OrderedDict
OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\numbers\work"
src = open(os.path.join(OUT, "s90_checked_lines.txt"), encoding="utf-8").read().splitlines()
pat = re.compile(r"^(?P<key>[^:|]+?)(?::| \|) mine (?P<m>.*?) \| A (?P<a>.*?) \| B (?P<b>.*?)(?: \| (?:off|official) (?P<o>.*?))?(?:\s+<-- DIFF)?\s*$")
groups = OrderedDict()
singles = []
for ln in src:
    mt = pat.match(ln)
    if not mt:
        singles.append(ln)
        continue
    key = mt.group("key").strip()
    vals = {s: (mt.group(g) or "").strip() for s, g in [("mine", "m"), ("A", "a"), ("B", "b"), ("official", "o")]}
    for s in vals:
        if vals[s] in ("(no official)", "", "None"):
            vals[s] = "-"
    m2 = re.match(r"^(.*)/(value|ci_low|ci_high|n_finite)$", key)
    if m2:
        groups.setdefault(m2.group(1), {}).setdefault(m2.group(2), vals)
    else:
        singles.append("%s: mine %s | A %s | B %s | official %s" % (key, vals["mine"], vals["A"], vals["B"], vals["official"]))


def short(x):
    try:
        f = float(x)
        if f == int(f) and abs(f) >= 1 and "." not in x.rstrip("0").rstrip(".") or x.endswith(".0") and abs(f) >= 1:
            return str(int(f))
        return "%.10g" % f
    except Exception:
        return x


lines = []
for g, parts in groups.items():
    seg = []
    for s in ["mine", "A", "B", "official"]:
        v = short(parts.get("value", {}).get(s, "-"))
        lo = short(parts.get("ci_low", {}).get(s, "-"))
        hi = short(parts.get("ci_high", {}).get(s, "-"))
        n = short(parts.get("n_finite", {}).get(s, "-"))
        if lo == "-" and hi == "-" and n == "-":
            seg.append("%s %s" % (s, v))
        else:
            seg.append("%s %s [%s, %s] n=%s" % (s, v, lo, hi, n))
    lines.append("%s: %s" % (g, " | ".join(seg)))
lines += [s for s in singles if not s.startswith("differences")]
open(os.path.join(OUT, "s91_checked_condensed.txt"), "w", encoding="utf-8").write("\n".join(lines))
print(len(lines))
