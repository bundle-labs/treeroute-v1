# Read-only. Scan the numbers skeptic's s41_tie_artifacts.json: per pair, the largest spread across collations
# and any tie-only ("coincidental") top-k members; split BARDL pairs from the rest.
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
d = json.load(open(V + r"\skeptic\numbers\work\s41_tie_artifacts.json", encoding="utf-8"))
print("pairs in s41:", len(d))
rows = []
for k, v in d.items():
    sp = v.get("spread", {})
    mx = max((abs(x) for x in sp.values() if isinstance(x, (int, float))), default=0.0)
    arg = max(sp, key=lambda s: abs(sp[s]) if isinstance(sp[s], (int, float)) else -1) if sp else None
    coinc = {c: v["base"].get(c) for c in ("coincidental_top5", "coincidental_top10", "coincidental_top20")
             if v.get("base", {}).get(c)}
    rows.append((k, "bardl" in k, mx, arg, coinc))
for flag in (False, True):
    sel = [r for r in rows if r[1] == flag]
    print("== %s: %d pairs" % ("BARDL pairs" if flag else "pairs without BARDL", len(sel)))
    above = [r for r in sel if r[2] > 1e-12]
    print("   spread > 1e-12: %d" % len(above))
    for r in sorted(above, key=lambda r: -r[2])[:40]:
        print("     %-55s max spread %.3g (%s)" % (r[0], r[2], r[3]))
    withc = [r for r in sel if r[4]]
    print("   with tie-only top-k members: %d" % len(withc))
    for r in withc:
        print("     %-55s %s" % (r[0], r[4]))
# which statistic drives the spreads above 1e-12 among non-BARDL pairs
import collections
c = collections.Counter()
for k, v in d.items():
    if "bardl" in k:
        continue
    for s, x in v.get("spread", {}).items():
        if isinstance(x, (int, float)) and abs(x) > 1e-12:
            c[s] += 1
print("non-BARDL spreads > 1e-12 by statistic:", dict(c))
