"""Skeptic (numbers lens): merge share-by-position lines of top-k lists into one line per list; write the final list."""
import os, re, json
from collections import OrderedDict
OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\numbers\work"
src = open(os.path.join(OUT, "s91_checked_condensed.txt"), encoding="utf-8").read().splitlines()
pat = re.compile(r"^(?P<key>.+?)/(?:b1_)?(?P<list>top10|top3|treeroute_top3|consensus_top3)/share(?P<i>\d+)(?::| \|) mine (?P<m>\S+) \| A (?P<a>\S+) \| B (?P<b>\S+)(?: \| (?:off|official) (?P<o>\S+))?")
merged = OrderedDict()
out = []
for ln in src:
    mt = pat.match(ln)
    if mt:
        k = mt.group("key") + "/" + mt.group("list") + " shares"
        merged.setdefault(k, {"mine": [], "A": [], "B": [], "official": []})
        for s, g in [("mine", "m"), ("A", "a"), ("B", "b"), ("official", "o")]:
            v = mt.group(g)
            merged[k][s].append("-" if v in (None, "-") else "%.6g" % float(v))
        if k not in out:
            out.append(k)
    else:
        out.append(ln)
final = []
for x in out:
    if x in merged:
        d = merged[x]
        same = all(abs(float(a) - float(b)) < 1e-9 for a, b in zip(d["mine"], d["A"])) and \
            all(abs(float(a) - float(b)) < 1e-9 for a, b in zip(d["mine"], d["B"]))
        offs = "official [" + ", ".join(d["official"]) + "]" if any(v != "-" for v in d["official"]) else "official -"
        final.append("%s: mine [%s] | A, B equal to mine within 1e-9: %s | %s" % (x, ", ".join(d["mine"]), same, offs))
    else:
        final.append(x.replace(" | off ", " | official "))
open(os.path.join(OUT, "s92_final_lines.json"), "w", encoding="utf-8").write(json.dumps(final, indent=0))
print(len(final))
