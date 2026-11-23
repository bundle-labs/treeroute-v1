# r05: the B1 numbers of Tables S3.28-S3.30 against V\A\results.json directly (values, not printouts): every
# printed B1 number is parsed back and compared with A's stored double (it must lie within half a unit of its
# last printed digit, and be the one-step format of it); every B1 quantity the spec names is printed once.
# Also a consistency look at V\reconcile\report.md A6 (three decimals), which is secondary. Read-only.
import sys, re, json, math, collections
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F401,F403

sys.stdout.reconfigure(encoding="utf-8")
A = load_json(V / "A" / "results.json", strict=True)
cells = load_json(OUT / "A" / "cells.json")["entries"]
b1 = [e for e in cells if e["table"] in ("S3.28", "S3.29", "S3.30")]
print("B1 entries in cells.json:", len(b1), collections.Counter(e["table"] for e in b1))


def jp(obj, sel):
    cur = obj
    for tok in re.findall(r'\["[^"]*"\]|\[\d+\]|[A-Za-z_][A-Za-z0-9_]*', sel):
        if tok.startswith('["'):
            cur = cur[json.loads(tok[1:-1])]
        elif tok.startswith("["):
            cur = cur[int(tok[1:-1])]
        else:
            cur = cur[tok]
    return cur


def back(tok):
    """parse a printed token back to a number and its half unit"""
    t = tok.replace(MINUS, "-").replace(",", "")
    if t == "<0.1%":
        return None, None
    if t.endswith("%"):
        x = float(t[:-1]) / 100.0
        dec = len(t[:-1].split(".")[1]) if "." in t else 0
        return x, 0.5 * 10 ** (-dec) / 100.0
    if "×" in t:
        return None, None
    if t == "0":
        return 0.0, 0.0
    dec = len(t.split(".")[1]) if "." in t else 0
    return float(t), 0.5 * 10 ** (-dec)


worst = 0.0
nnum, nexact, nlt, probs = 0, 0, 0, []
seen = collections.Counter()
for e in b1:
    src = e["source"]
    if src == "V\\A\\results.json":
        v = jp(A, e["selector"])
        if [v] != e["stored"]:
            probs.append(("stored != results.json", e["selector"]))
        seen[re.sub(r"^b1\.(pm25|ndvi|fire|defo)\.", "b1.<p>.", e["selector"])] += 1
        x, h = back(e["printed"])
        nnum += 1
        if x is None:
            if e["printed"] == "<0.1%":
                nlt += 1
                if not (0 < v < 0.0005):
                    probs.append(("<0.1% for", v, e["selector"]))
            else:   # SCI2
                if v != 0.0 and not math.isclose(float(e["printed"].split(" ")[0]), float(format(abs(v), ".1e").split("e")[0])):
                    probs.append(("sci", v, e["printed"]))
            continue
        if h == 0.0:
            if x != v:
                probs.append(("exact", v, e["printed"]))
            nexact += 1
            continue
        d = abs(x - v)
        worst = max(worst, d / h)
        if d > h * (1 + 1e-9):
            probs.append(("beyond half unit", v, e["printed"], e["selector"]))
    else:  # the logs
        nnum += 1
        seen["log " + e["selector"].split(": ")[1]] += 1
print("B1 numbers checked:", nnum, "of which exact counts/zeros:", nexact, "'<0.1%' tokens:", nlt,
      "largest |printed - value| / half unit:", round(worst, 6), "problems:", len(probs))
for p_ in probs:
    print("  ", p_)
for k, c in sorted(seen.items()):
    print("   %3d  %s" % (c, k))

# the spec's B1 list: is each quantity printed for each problem it applies to?
want = []
for p in ("pm25", "ndvi", "fire"):
    for L in ("variable", "feature"):
        for s in ("n_J", "spearman_J", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10", "rbo_p090",
                  "rbo_p095", "tv_shares", "sign_agreement", "sign_n_determined", "sign_n_agree"):
            want.append("b1.%s.%s.pair_main_b1.%s.value" % (p, L, s))
        if A["b1"][p][L]["pair_main_b1"]["jaccard_top20"] is not None:
            want.append("b1.%s.%s.pair_main_b1.jaccard_top20.value" % (p, L))
        want.append("b1.%s.%s.importance.n_nonzero.value" % (p, L))
        for k in range(10):
            want.append("b1.%s.%s.top10[%d][1]" % (p, L, k))
    want.append("b1.%s.variable.pair_main_b1.tv_family_shares.value" % p)
    for f in ("own_history", "global_indices", "local_drivers", "context_and_calendar", "seasonal_normal"):
        want.append("b1.%s.variable.families.%s.value" % (p, f))
    want.append("b1.%s.variable.own_history_share.value" % p)
    for k in range(3):
        want.append("b1.%s.variable.top3[%d][1]" % (p, k))
for k in ("max_abs_diff_phi", "max_abs_diff_phiv", "n_rows_main", "n_rows_b1", "n_players_main", "n_players_b1", "n_variables_main", "n_variables_b1"):
    want.append("b1.defo.identity." + k)
have = collections.Counter(e["selector"] for e in b1 if e["source"] == "V\\A\\results.json")
missing = [w for w in want if have[w] == 0]
print("spec B1 quantities:", len(want), "printed:", len(want) - len(missing), "missing:", missing[:10])
# intervals printed with each statistic: ci_low and ci_high entries exist wherever the value is printed with an interval
ivl = collections.Counter()
for e in b1:
    if e["part"] in ("ci_low", "ci_high"):
        ivl[e["part"]] += 1
print("B1 interval ends printed:", dict(ivl), "n_finite printed:", sum(1 for e in b1 if e["part"] == "n_finite"))
# n_finite of every B1 interval object used
nf = collections.Counter()
for p in ("pm25", "ndvi", "fire"):
    for L in ("variable", "feature"):
        for s, o in A["b1"][p][L]["pair_main_b1"].items():
            if isinstance(o, dict) and "n_finite" in o and s not in ("n_J",):
                nf[o["n_finite"]] += 1
    for f, o in A["b1"][p]["variable"]["families"].items():
        if isinstance(o, dict) and "n_finite" in o:
            nf[o["n_finite"]] += 1
    nf[A["b1"][p]["variable"]["own_history_share"]["n_finite"]] += 1
print("n_finite of the B1 interval objects:", dict(nf))

# secondary: report.md A6 three-decimal numbers against the same values (consistency only)
rep = (V / "reconcile" / "report.md").read_text(encoding="utf-8").split("\n")
i0 = next(i for i, l in enumerate(rep) if l.startswith("### A6."))
i1 = next(i for i, l in enumerate(rep) if l.startswith("### A7."))
blk = rep[i0:i1]
ROWS = {"Spearman over J": "spearman_J", "top-20-union Spearman": "spearman_top20_union", "Kendall tau-b": "kendall_tau_b",
        "Jaccard top 5": "jaccard_top5", "Jaccard top 10": "jaccard_top10", "Jaccard top 20": "jaccard_top20", "RBO p 0.9": "rbo_p090",
        "RBO p 0.95": "rbo_p095", "share distance (TV)": "tv_shares", "sign agreement": "sign_agreement"}
lev = None
n6, bad6 = 0, []
for l in blk:
    if l.startswith("**Feature level: the pair"):
        lev = "feature"
    elif l.startswith("**Variable level: the pair"):
        lev = "variable"
    elif l.startswith("**"):
        lev = None
    if lev and l.startswith("| ") and not l.startswith("| statistic") and not l.startswith("|---"):
        c = [x.strip() for x in l.strip("|").split("|")]
        if c[0] in ROWS:
            for p, cell in zip(("fire", "pm25", "ndvi"), c[1:]):
                m = re.match(r"^(-?\d\.\d{3}) \[(-?\d\.\d{3}), (-?\d\.\d{3})\]$", cell)
                if not m:
                    continue
                o = A["b1"][p][lev]["pair_main_b1"][ROWS[c[0]]]
                for tok, v in zip(m.groups(), (o["value"], o["ci_low"], o["ci_high"])):
                    n6 += 1
                    if format(v, ".3f") != tok:
                        bad6.append((p, lev, c[0], tok, v))
print("A6 three-decimal pair numbers re-formatted from results.json:", n6, "differing:", len(bad6), bad6[:5])
