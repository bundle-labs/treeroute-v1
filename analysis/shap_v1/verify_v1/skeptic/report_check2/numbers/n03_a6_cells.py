"""n03: check every cell of report.md A6 against A's and B's results.json (key b1), rounded once to 3 decimals.

Independent of the lead's b1_tables.py: the report's cells are parsed from report.md, and the expected text is built
here from A's and from B's numbers with two rounding methods (exact binary value, half-even; shortest repr,
half-up). Interval ends and finite counts are checked too. Read-only; prints only.
"""
import json
import math
import re
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
REPORT = V + r"\reconcile\report.md"

with open(V + r"\A\results.json", encoding="utf-8") as f:
    A = json.load(f)["b1"]
with open(V + r"\B\results.json", encoding="utf-8") as f:
    B = json.load(f)["b1"]

text = open(REPORT, encoding="utf-8").read()
i = text.index("### A6.")
j = text.index("### A7.")
a6 = text[i:j]
lines = a6.split("\n")

# ---- parse the tables under each bold heading
tables = {}
cur = None
for ln in lines:
    m = re.match(r"^\*\*(.+)\*\*$", ln.strip())
    if m:
        cur = m.group(1)
        tables[cur] = []
        continue
    if cur and ln.startswith("|"):
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(set(c) <= set("-") for c in cells):
            continue
        tables[cur].append(cells)
print("tables found:", list(tables.keys()))
for k, v in tables.items():
    print("  ", k, "rows:", len(v), "header:", v[0])

PROBLEMS = ["fire", "pm25", "ndvi"]
problems = []
n_cells = 0
n_numbers = 0
alt_round_diffs = []
ab_max = 0.0


def r3_exact(x):
    d = Decimal(x).quantize(Decimal("0.001"), rounding=ROUND_HALF_EVEN)
    s = format(d, "f")
    if s == "-0.000":
        s = "-0.000"
    return s


def r3_repr_up(x):
    d = Decimal(repr(float(x))).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return format(d, "f")


def r3(x, tag):
    global n_numbers
    n_numbers += 1
    a = r3_exact(x)
    b = r3_repr_up(x)
    if a != b:
        alt_round_diffs.append((tag, x, a, b))
    return a


def ab_close(tag, a, b, tol=1e-12):
    global ab_max
    if a is None or b is None:
        if not (a is None and b is None):
            problems.append("A/B presence differs at %s: A %r B %r" % (tag, a, b))
        return
    if isinstance(a, str) or isinstance(b, str):
        if a != b:
            problems.append("A/B differ at %s: %r %r" % (tag, a, b))
        return
    if math.isnan(a) or math.isnan(b):
        if not (math.isnan(a) and math.isnan(b)):
            problems.append("A/B NaN differs at %s" % tag)
        return
    d = abs(a - b)
    ab_max = max(ab_max, d)
    if d > tol * max(1.0, abs(a), abs(b)):
        problems.append("A/B differ at %s: %r %r" % (tag, a, b))


def interval_text(e, tag, finite_note=True):
    """value [lo, hi] (n finite) from an entry dict."""
    v, lo, hi, n = e.get("value"), e.get("ci_low"), e.get("ci_high"), e.get("n_finite")
    s = "undefined" if v is None else r3(v, tag + "/value")
    if lo is not None and hi is not None:
        s += " [%s, %s]" % (r3(lo, tag + "/ci_low"), r3(hi, tag + "/ci_high"))
    if finite_note and n is not None and n != 2000:
        s += " (%s finite)" % format(int(n), ",")
    return s, n


def entry_ab(p, lev, key, sub=None):
    if sub is None:
        ea = A[p][lev]["pair_main_b1"].get(key)
        eb = B[p][lev]["pair_main_b1"].get(key)
    else:
        ea = A[p][lev][sub].get(key) if isinstance(A[p][lev][sub], dict) else None
        eb = B[p][lev][sub].get(key) if isinstance(B[p][lev][sub], dict) else None
    return ea, eb


def cmp_entry(tag, ea, eb):
    if isinstance(ea, dict) and isinstance(eb, dict):
        for k in ("value", "ci_low", "ci_high", "n_finite"):
            ab_close(tag + "/" + k, ea.get(k), eb.get(k))
    else:
        ab_close(tag, ea, eb)


PAIR_ROWS = {
    "Spearman over J": "spearman_J", "top-20-union Spearman": "spearman_top20_union",
    "Kendall tau-b": "kendall_tau_b", "Jaccard top 5": "jaccard_top5", "Jaccard top 10": "jaccard_top10",
    "Jaccard top 20": "jaccard_top20", "RBO p 0.9": "rbo_p090", "RBO p 0.95": "rbo_p095",
    "share distance (TV)": "tv_shares", "family-share distance (TV)": "tv_family_shares",
    "sign agreement": "sign_agreement",
}
finite_seen = {}

for lev, title in (("feature", "Feature level: the pair (main run, B1 run)"),
                   ("variable", "Variable level: the pair (main run, B1 run)")):
    rows = tables[title]
    hdr = rows[0]
    assert hdr == ["statistic", "fire", "pm25", "ndvi"], hdr
    labels_seen = []
    for row in rows[1:]:
        label = row[0]
        labels_seen.append(label)
        for k, p in enumerate(PROBLEMS):
            got = row[k + 1]
            n_cells += 1
            tag = "%s/%s/%s" % (p, lev, label)
            pa = A[p][lev]["pair_main_b1"]
            pb = B[p][lev]["pair_main_b1"]
            if label.startswith("pair J"):
                cmp_entry(tag, pa["n_J"], pb["n_J"])
                exp = format(int(pa["n_J"]["value"]), ",")
                # also: pair J equals the length of the J list
                if len(pa["J"]) != int(pa["n_J"]["value"]) or len(pb["J"]) != int(pb["n_J"]["value"]):
                    problems.append("%s: J list length != n_J" % tag)
                if sorted(pa["J"]) != sorted(pb["J"]):
                    problems.append("%s: A and B J lists differ" % tag)
            elif label.startswith("signs determined in both"):
                nd_a, nd_b = pa.get("sign_n_determined"), pb.get("sign_n_determined")
                na_a, na_b = pa.get("sign_n_agree"), pb.get("sign_n_agree")
                cmp_entry(tag + "/nd", nd_a, nd_b)
                cmp_entry(tag + "/na", na_a, na_b)
                exp = "%d / %d" % (int(nd_a["value"]), int(na_a["value"]))
                # count consistency: determined-in-both list length, and agreement = agree / determined
                if len(pa.get("sign_determined_both", [])) != int(nd_a["value"]):
                    problems.append("%s: len(sign_determined_both) %d != sign_n_determined %s" % (
                        tag, len(pa.get("sign_determined_both", [])), nd_a["value"]))
                sa = pa["sign_agreement"]["value"]
                if abs(sa - na_a["value"] / nd_a["value"]) > 1e-12:
                    problems.append("%s: sign agreement %r != agree/determined" % (tag, sa))
            else:
                key = PAIR_ROWS[label]
                ea, eb = pa.get(key), pb.get(key)
                if key == "tv_family_shares" and lev == "feature":
                    if ea is not None:
                        problems.append("%s: A has a feature-level family distance" % tag)
                    s, n = interval_text(eb, "B:" + tag)
                    finite_seen[("B", tag)] = n
                    exp = "A none (C15); B " + s
                    # B's feature value equals B's and A's variable-level value?
                    bv = B[p]["variable"]["pair_main_b1"]["tv_family_shares"]
                    av = A[p]["variable"]["pair_main_b1"]["tv_family_shares"]
                    for kk in ("value", "ci_low", "ci_high", "n_finite"):
                        if abs(eb[kk] - bv[kk]) > 1e-12 or abs(eb[kk] - av[kk]) > 1e-12:
                            problems.append("%s: B feature family distance %s != variable-level" % (tag, kk))
                elif key == "jaccard_top20" and ea is None:
                    cmp_entry(tag, ea, eb)
                    nj = int(pa["n_J"]["value"])
                    if nj >= 200:
                        problems.append("%s: Jaccard top 20 missing although J = %d" % (tag, nj))
                    exp = "not defined (J < 200)"
                else:
                    cmp_entry(tag, ea, eb)
                    s, n = interval_text(ea, tag)
                    finite_seen[("A", tag)] = n
                    finite_seen[("B", tag)] = eb.get("n_finite")
                    exp = s
                    if key == "jaccard_top20":
                        nj = int(pa["n_J"]["value"])
                        if nj < 200:
                            problems.append("%s: Jaccard top 20 given although J = %d" % (tag, nj))
            if got != exp:
                problems.append("CELL MISMATCH %s: report %r, expected %r" % (tag, got, exp))
    print(lev, "pair rows:", labels_seen)
    # Every pair statistic key present in results.json covered by a row?
    keys_in_json = [k for k in A["fire"][lev]["pair_main_b1"].keys()]
    print("  pair_main_b1 keys in A:", keys_in_json)

# ---- families, own-history share, top 3
FAM = {"own history": "own_history", "global indices": "global_indices", "local drivers": "local_drivers",
       "context and calendar": "context_and_calendar", "seasonal normal": "seasonal_normal"}
rows = tables["Variable level: the B1 run's family shares, top 3 and own-history share"]
assert rows[0] == ["family share", "fire", "pm25", "ndvi"], rows[0]
for row in rows[1:]:
    label = row[0]
    for k, p in enumerate(PROBLEMS):
        got = row[k + 1]
        n_cells += 1
        tag = "%s/variable/%s" % (p, label)
        if label in FAM:
            ea = A[p]["variable"]["families"][FAM[label]]
            eb = B[p]["variable"]["families"][FAM[label]]
            cmp_entry(tag, ea, eb)
            exp, n = interval_text(ea, tag)
            finite_seen[("A", tag)] = n
            finite_seen[("B", tag)] = eb.get("n_finite")
        elif label.startswith("own-history share"):
            ea = A[p]["variable"]["own_history_share"]
            eb = B[p]["variable"]["own_history_share"]
            cmp_entry(tag, ea, eb)
            exp, n = interval_text(ea, tag)
            finite_seen[("A", tag)] = n
            finite_seen[("B", tag)] = eb.get("n_finite")
            # equals the own-history family share?
            fa = A[p]["variable"]["families"]["own_history"]
            if abs(fa["value"] - ea["value"]) > 1e-12:
                problems.append("%s: own-history share != own_history family" % tag)
        elif label.startswith("top 3"):
            ta, tb = A[p]["variable"]["top3"], B[p]["variable"]["top3"]
            if [t[0] for t in ta] != [t[0] for t in tb]:
                problems.append("%s: A/B top3 names differ" % tag)
            for x, y in zip(ta, tb):
                ab_close(tag + "/" + x[0], x[1], y[1])
            exp = ", ".join("%s %s" % (t[0], r3(t[1], tag + "/" + t[0])) for t in ta)
            # top3 = first three of top10?
            t10 = A[p]["variable"]["top10"][:3]
            if [t[0] for t in t10] != [t[0] for t in ta]:
                problems.append("%s: top3 != top10[:3]" % tag)
        else:
            problems.append("unknown row %s" % label)
            continue
        if got != exp:
            problems.append("CELL MISMATCH %s: report %r, expected %r" % (tag, got, exp))

# family shares sum to 1
for p in PROBLEMS:
    s = sum(A[p]["variable"]["families"][k]["value"] for k in FAM.values())
    print("family shares sum", p, s)

# ---- top-10 tables
for lev, title in (("feature", "Feature level: the B1 run's top 10 (share; no interval for a top-k list)"),
                   ("variable", "Variable level: the B1 run's top 10 (share; no interval for a top-k list)")):
    rows = tables[title]
    assert rows[0] == ["rank", "fire", "pm25", "ndvi"], rows[0]
    assert len(rows) == 11, len(rows)
    for r, row in enumerate(rows[1:]):
        assert row[0] == str(r + 1)
        for k, p in enumerate(PROBLEMS):
            got = row[k + 1]
            n_cells += 1
            tag = "%s/%s/top10/%d" % (p, lev, r + 1)
            ta, tb = A[p][lev]["top10"], B[p][lev]["top10"]
            if ta[r][0] != tb[r][0]:
                problems.append("%s: A/B names differ" % tag)
            ab_close(tag, ta[r][1], tb[r][1])
            exp = "%s %s" % (ta[r][0], r3(ta[r][1], tag))
            if got != exp:
                problems.append("CELL MISMATCH %s: report %r, expected %r" % (tag, got, exp))
    # top10 consistent with ranking and the importance shares?
    for p in PROBLEMS:
        imp = A[p][lev]["importance"]
        rk = imp["ranking"][:10]
        if rk != [t[0] for t in A[p][lev]["top10"]]:
            problems.append("%s/%s: top10 names != ranking[:10]" % (p, lev))
        for nm, sh in A[p][lev]["top10"]:
            if abs(imp["players"][nm]["share"]["value"] - sh) > 1e-12:
                problems.append("%s/%s: top10 share of %s != players share" % (p, lev, nm))
        # ties near rank 10/11 boundary?
        shares = sorted(((imp["players"][n]["share"]["value"], n) for n in imp["players"]), reverse=True)
        print("%s %s rank10 %.6g rank11 %.6g (gap %.3g)" % (p, lev, shares[9][0], shares[10][0],
                                                          shares[9][0] - shares[10][0]))

# ---- finite counts: every interval printed must have 2,000 (none shown)
bad_finite = {k: v for k, v in finite_seen.items() if v != 2000}
print("interval cells checked for n_finite:", len(finite_seen), "not 2000:", bad_finite)

print("cells compared:", n_cells, "numbers rounded:", n_numbers)
print("A-B largest abs difference over printed numbers: %.3g" % ab_max)
print("rounding-method differences (exact half-even vs repr half-up):", alt_round_diffs)
print("problems:", len(problems))
for x in problems:
    print("  ", x)

# ---- the text claims of A6 around the tables
print("A6 B1 'players' path exists:", all(isinstance(A[p][lev]["importance"]["players"], dict)
                                         for p in PROBLEMS for lev in ("feature", "variable")))
# how many players carry I, share, signed_mean with intervals and n_finite 2000?
cnt = 0
non2000 = 0
for p in PROBLEMS:
    for lev in ("feature", "variable"):
        for nm, e in A[p][lev]["importance"]["players"].items():
            for k in ("I", "share", "signed_mean"):
                cnt += 1
                if e[k]["n_finite"] != 2000:
                    non2000 += 1
print("player-level I/share/signed_mean entries:", cnt, "with n_finite != 2000:", non2000)
