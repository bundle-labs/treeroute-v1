# r02: compare every printed cell of OUT\A\tables.md (= OUT\B\tables.md) that has a counterpart in the
# official printouts SHAP\out\<p>\lead_0\compare\AW3_table.md and AW4_table.md with that counterpart.
# Read-only; prints every comparison class and every mismatch. Normalisations applied before comparing are
# the spec's layout and display changes only (Unicode minus, display names, order, backticks, marks).
# Version 2 (2026-11-17): the S3.22 row read for the cross-link rivals is found by its version-2 label
# "Guard-passing rivals in another link" (C5); nothing else changed. Original: scripts\v1\r02_official_compare.py.
# Version 3 (2026-11-17): changed only where version 3 changed this script's input: the S3.22 row is found by its
# version-3 label "Rivals in another link that passed their skill guard" (V3-5); treeroute's expected skill-guard text
# in S3.18 a is the spec's "passed (the adopted arm)" (V3-6); and a Link cell, which now prints the words P = "; raw
# model, declined by its skill guard: " where the source label holds M = "; raw model, declined by its guard: " (spec
# 4.7, V3-6), is turned back to the label's words before the comparison with the printout's label, like the display
# names after it. Version 2 is kept as scripts\v2\r02_official_compare.py.
# Version 4 (2026-11-17): changed only where version 4 changed this script's input: the S3.22 row read for the
# cross-link rivals is found by its version-4 label "Rivals that explain in another link and passed their skill guard"
# (V4-8); nothing else changed. Version 3 is kept as scripts\v3\r02_official_compare.py.
import sys, re, json, collections
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2]
SHAP = Path("D:/treeroute/analysis/shap_v1")
MINUS = "\u2212"
MARKS = "\u2020\u2021\u00a7\u1d43\u1d47\u1d9c\u1d48"  # dagger, double dagger, section, a b c d superscripts
ENDASH = "\u2013"
PROBS = ["pm25", "ndvi", "fire", "defo", "coral"]
PDISP = {"PM2.5": "pm25", "NDVI": "ndvi", "Burned fraction": "fire", "Forest loss": "defo", "Coral bleaching": "coral"}
TID = {"pm25": "S3.23", "ndvi": "S3.24", "fire": "S3.25", "defo": "S3.26", "coral": "S3.27"}
MINLINE = {"treeroute v1": "treeroute", "Ridge": "rival_ridge", "random forest": "rival_rf", "LightGBM": "rival_lgbm",
           "Tweedie booster": "rival_lgbm_tweedie", "absolute-error booster": "rival_hgb_l1", "BARDL": "rival_bardl_h1"}
MHEAD = {"treeroute v1": "treeroute", "Ridge": "rival_ridge", "Random forest": "rival_rf", "LightGBM": "rival_lgbm",
         "Tweedie booster": "rival_lgbm_tweedie", "Absolute-error booster": "rival_hgb_l1", "BARDL": "rival_bardl_h1"}
LINKDISP = {"identity": "identity", "log_c": "log(y + c)", "log_mu": "log \u03bc", "arcsine": "arcsine"}
BB4 = [" (no own-history input)", " (no global-index input)", " (no local-driver input)",
       " (no context or calendar input)", " (no seasonal-normal input)"]
FAMROW = {"Own history": "own history", "Global indices": "global indices", "Local drivers": "local drivers",
          "Context and calendar": "context and calendar", "Seasonal normal": "seasonal normal"}
STATCOL = {"Spearman over J": "spearman", "Spearman, top-20 union": "spearman_top20_union",
           "Kendall's tau-b": "kendall_tau_b", "Jaccard top 5": "jaccard_top5", "Jaccard top 10": "jaccard_top10",
           "Jaccard top 20": "jaccard_top20", "RBO, p = 0.9": "rbo_p0.9", "RBO, p = 0.95": "rbo_p0.95",
           "Share distance (TV)": "tvd", "Family-share distance (TV)": "tvd_family",
           "Family-share distance (TV)\u00a7": "tvd_family",
           "Sign agreement, top-10 union (signs)\u2020": "sign_agreement_top10"}


def strip_marks(s):
    return "".join(ch for ch in s if ch not in MARKS)


def norm(s):
    """layout normalisation only: Unicode minus -> ASCII hyphen, marks removed, backticks removed"""
    return strip_marks(s).replace(MINUS, "-").replace("`", "")


# ---------------- our tables ----------------
text = (OUT / "A" / "tables.md").read_text(encoding="utf-8")
assert text == (OUT / "B" / "tables.md").read_text(encoding="utf-8")
lines = text.split("\n")
tables, notes = {}, collections.defaultdict(list)
cur, pan, i = None, "", 0
while i < len(lines):
    ln = lines[i]
    m = re.match(r"^\*\*Table (9|S3\.\d+)\b", ln)
    if m:
        cur, pan = m.group(1), ""
        i += 1
        continue
    m = re.match(r"^\*\*([a-g])\. ", ln)
    if m:
        pan = m.group(1)
        i += 1
        continue
    if ln.startswith("| ") and i + 1 < len(lines) and lines[i + 1].startswith("|---"):
        header = ln[2:-2].split(" | ")
        rows, nums = [], []
        j = i + 2
        while j < len(lines) and lines[j].startswith("| "):
            rows.append(lines[j][2:-2].split(" | "))
            nums.append(j + 1)
            j += 1
        assert (cur, pan) not in tables
        tables[(cur, pan)] = dict(header=header, rows=rows, lines=nums)
        i = j
        continue
    if ln and cur and not ln.startswith("#") and not ln.startswith("**") and not ln.startswith("<!--"):
        notes[cur].append((i + 1, ln))
    i += 1
print("our tables parsed:", len(tables), "table blocks;", sum(len(v) for v in notes.values()), "note lines")


def rowmap(t, keycol=0):
    return {r[keycol]: (r, ln) for r, ln in zip(t["rows"], t["lines"])}


# ---------------- official printouts ----------------
def cells_of(row):
    return [c.strip() for c in re.split(r"\s\|\s", " " + row.strip()[1:-1] + " ")]


def parse_aw3(p):
    L = (SHAP / "out" / p / "lead_0" / "compare" / "AW3_table.md").read_text(encoding="utf-8").split("\n")
    d = {"levels": {}, "top10": {}, "nonzero": {}, "families": {}, "nzf": {}}
    m = re.match(r"^(\d+) rows in (\d+) regions; .* from (\d+) paired region draws\.", L[2])
    d["rows"], d["regions"], d["draws"] = int(m.group(1)), int(m.group(2)), int(m.group(3))
    assert L[4].startswith("Models and links: ")
    d["links"], d["declined"] = {}, set()
    for it in L[4][len("Models and links: "):].split("; "):
        m = re.match(r"^(\w+) \((\S+?)(, declined by its guard)?\)$", it)
        d["links"][m.group(1)] = m.group(2)
        if m.group(3):
            d["declined"].add(m.group(1))
    assert L[6].startswith("Main set: ")
    d["main_set"] = L[6][len("Main set: "):].split(", ")
    lev = None
    k = 0
    while k < len(L):
        ln = L[k]
        m = re.match(r"^## (variable|feature) level \((\d+) players, (\d+) active; structural zeros: (.*)\)$", ln)
        if m:
            lev = m.group(1)
            d["levels"][lev] = dict(players=int(m.group(2)), active=int(m.group(3)), sz=m.group(4).split(", "),
                                    pairs={}, top10={}, nonzero={})
            k += 1
            continue
        if ln.startswith("| Pair | label |"):
            hdr = cells_of(ln)
            k += 2
            while k < len(L) and L[k].startswith("| "):
                c = cells_of(L[k])
                assert len(c) == len(hdr), (p, L[k])
                d["levels"][lev]["pairs"][c[0]] = dict(zip(hdr, c))
                k += 1
            continue
        m = re.match(r"^Kendall's W \(main set\) = (.+); mean pairwise Spearman \(main set\) = (.+)\.$", ln)
        if m:
            d["levels"][lev]["W"], d["levels"][lev]["MS"] = m.group(1), m.group(2)
        m = re.match(r"^Stability under region resampling \((.*)\): (.*)$", ln)
        if m:
            d["levels"][lev]["stab"] = dict(x.rsplit(" ", 1) for x in m.group(2).split(", "))
        m = re.match(r"^- (\w+) top-10 \((\d+) nonzero\): (.*)$", ln)
        if m:
            d["levels"][lev]["top10"][m.group(1)] = [x.rsplit(" ", 1) for x in m.group(3).split("; ")]
            d["levels"][lev]["nonzero"][m.group(1)] = int(m.group(2))
        if ln.startswith("| Family |"):
            hdr = cells_of(ln)
            k += 2
            while k < len(L) and L[k].startswith("| "):
                c = cells_of(L[k])
                for mod, v in zip(hdr[1:], c[1:]):
                    d["families"][(c[0], mod)] = v
                k += 1
            continue
        m = re.match(r"^- (\w+), (\d+) rows: (.*)$", ln)
        if m:
            d["nzf"][m.group(1)] = (int(m.group(2)), [x.rsplit(" ", 1) for x in m.group(3).split("; ")])
        k += 1
    return d


def parse_aw4(p):
    L = (SHAP / "out" / p / "lead_0" / "compare" / "AW4_table.md").read_text(encoding="utf-8").split("\n")
    hdr = cells_of(L[0])
    row = cells_of(L[2])
    assert len(hdr) == len(row) == 8, (p, len(hdr), len(row))
    return dict(zip(hdr, row))


AW3 = {p: parse_aw3(p) for p in PROBS}
AW4 = {p: parse_aw4(p) for p in PROBS}

# ---------------- comparison bookkeeping ----------------
compared = collections.Counter()      # class -> number of our cells compared
mism = []                            # (class, where, ours, official, explained, why)
expl_counts = collections.Counter()


def cmp(cls, where, ours, off, ours_n=None, off_n=None, explain=None):
    """compare normalised texts; explain=(True/False, why) applies only when they differ"""
    compared[cls] += 1
    a = norm(ours) if ours_n is None else ours_n
    b = off if off_n is None else off_n
    if a != b:
        e = explain if explain else (False, "")
        mism.append((cls, where, ours, off, e[0], e[1]))
        return False
    return True


# ---------- Table 9 and Table S3.22 (AW4) ----------
t9 = rowmap(tables[("9", "")])
t22 = tables[("S3.22", "")]
h22 = t22["header"]
q22 = {r[0]: r for r in t22["rows"]}
col22 = {PDISP[strip_marks(h)]: j for j, h in enumerate(h22) if strip_marks(h) in PDISP}


def model_list(s):
    s = strip_marks(s)
    if s == "treeroute v1 only":
        return ["treeroute"]
    if s == "none":
        return []
    return [MINLINE[x] for x in s.split(", ")]


for disp, p in PDISP.items():
    r, ln = t9[disp]
    a4 = AW4[p]
    a3 = AW3[p]
    where9 = "Table 9 line %d (%s)" % (ln, disp)
    # main set (as a set; order and names are the spec's display rules)
    compared["T9 main set"] += 1
    if set(model_list(r[1])) != set(a4["Main set"].split(", ")):
        mism.append(("T9 main set", where9, r[1], a4["Main set"], False, ""))
    if p == "fire":
        cmp("T9 W", where9 + " W", r[2], a4["W [95% CI]"],
            explain=(True, "spec 2.6/2.7 and decision 4: Kendall's W of a one-model main set is NaN with 0 finite draws, printed 'undefined' with no interval (the printout's 'nan [nan, nan]')"))
        for j, key in ((3, "treeroute vs same-link rivals: median rho, top-20 union [CI] (range)"),
                       (4, "RBO vs consensus [CI]"), (6, "consensus top 3")):
            cmp("T9 fire rival cells", where9 + " col %d" % (j + 1), r[j], a4[key],
                explain=(True, "spec 4.1 and 2.7: fire's cells that need a rival print the en dash, with note a (the printout writes its explanation text in the median cell and leaves the RBO and consensus cells empty)"))
        cmp("T9 fire BB1", where9 + " treeroute top 3", r[5], a4["treeroute top 3"],
            explain=(True, "ruling BB1: fire's treeroute top 3 comes from V\\A\\results.json (the comparison writes no main row without a same-link rival); it equals the first three names of the printout's AW3 variable-level treeroute top-10 (%s)" % ", ".join(x[0] for x in a3["levels"]["variable"]["top10"]["treeroute"][:3])))
        cmp("T9 fire BB1", where9 + " own-history share, treeroute", r[7], a4["own history: treeroute [CI] / median rival [CI]"],
            explain=(True, "ruling BB1: fire's own-history share [CI] comes from V\\A\\results.json; the printout's AW3 families table gives treeroute's own history as %s" % a3["families"][("own history", "treeroute")]))
        cmp("T9 fire rival cells", where9 + " own-history share, median rival", r[8], a4["own history: treeroute [CI] / median rival [CI]"],
            explain=(True, "spec 4.1: no rival in fire's main set, so the en dash"))
        if sorted(x[0] for x in a3["levels"]["variable"]["top10"]["treeroute"][:3]) != sorted(strip_marks(r[5]).replace("`", "").split(", ")) or \
                [x[0] for x in a3["levels"]["variable"]["top10"]["treeroute"][:3]] != strip_marks(r[5]).replace("`", "").split(", "):
            mism.append(("T9 fire BB1 cross-check", where9, r[5], str(a3["levels"]["variable"]["top10"]["treeroute"][:3]), False, "BB1 top 3 differs from the AW3 ranking"))
    else:
        cmp("T9 W", where9 + " W", r[2], a4["W [95% CI]"])
        cmp("T9 median Spearman (range)", where9 + " Spearman", r[3], a4["treeroute vs same-link rivals: median rho, top-20 union [CI] (range)"])
        cmp("T9 RBO", where9 + " RBO", r[4], a4["RBO vs consensus [CI]"])
        cmp("T9 top 3", where9 + " treeroute top 3", r[5], a4["treeroute top 3"])
        cmp("T9 top 3", where9 + " consensus top 3", r[6], a4["consensus top 3"])
        oh = a4["own history: treeroute [CI] / median rival [CI]"].split(" / ")
        for j, o in ((7, oh[0]), (8, oh[1])):
            a = norm(r[j])
            for lab in BB4:
                a = a.replace(lab, "")
            ok = cmp("T9 own-history share", where9 + " col %d" % (j + 1), r[j], o, ours_n=a)
            if ok and norm(r[j]) != a:
                expl_counts["BB4 label on an equal Table 9 own-history cell"] += 1

    # ---- Table S3.22 column p ----
    j = col22[p]
    w22 = "Table S3.22 column %s" % disp
    cmp("S3.22 link", w22 + " link", q22["Link of the main set"][j], "", ours_n=strip_marks(q22["Link of the main set"][j]),
        off_n=LINKDISP[a3["links"]["treeroute"].split("|")[0]])
    compared["S3.22 main set"] += 1
    if set(model_list(q22["Main set"][j])) != set(a4["Main set"].split(", ")):
        mism.append(("S3.22 main set", w22, q22["Main set"][j], a4["Main set"], False, ""))
    tr_link = a3["links"]["treeroute"]
    cross = {m for m, l in a3["links"].items() if l != tr_link} - a3["declined"]
    compared["S3.22 rivals in another link"] += 1
    if set(model_list(q22["Rivals that explain in another link and passed their skill guard"][j])) != cross:
        mism.append(("S3.22 rivals in another link", w22, q22["Rivals that explain in another link and passed their skill guard"][j], str(sorted(cross)), False, ""))
    compared["S3.22 declined"] += 1
    if set(model_list(q22["Rivals declined by their skill guard"][j])) != a3["declined"]:
        mism.append(("S3.22 declined", w22, q22["Rivals declined by their skill guard"][j], str(sorted(a3["declined"])), False, ""))
    if p == "fire":
        cmp("S3.22 W", w22 + " W", q22["Kendall's W of the main set [95% CI]"][j], a4["W [95% CI]"],
            explain=(True, "spec 2.6/2.7 and decision 4: undefined W of a one-model main set, no interval (printout 'nan [nan, nan]')"))
        for qq in ("Spearman of treeroute v1 with each same-link rival", "Median of those [95% CI]", "Range (lowest to highest)",
                   "RBO with the rivals' consensus, p = 0.9 [95% CI]", "Consensus top 3", "Own-history share of each same-link rival",
                   "Own-history share, median of the rivals\u1d9c [95% CI]"):
            compared["S3.22 fire rival cells"] += 1
            if q22[qq][j] != ENDASH:
                mism.append(("S3.22 fire rival cells", w22 + " " + qq, q22[qq][j], "", False, "expected en dash"))
            else:
                expl_counts["S3.22 fire rival cell printed as en dash (printout empty or explanation text)"] += 1
        cmp("S3.22 fire BB1", w22 + " treeroute top 3", q22["treeroute v1's top 3"][j], a4["treeroute top 3"],
            explain=(True, "ruling BB1 (as Table 9)"))
        cmp("S3.22 fire BB1", w22 + " own-history share, treeroute", q22["Own-history share, treeroute v1 [95% CI]"][j], "",
            explain=(True, "ruling BB1 (as Table 9)"))
        continue
    cmp("S3.22 W", w22 + " W", q22["Kendall's W of the main set [95% CI]"][j], a4["W [95% CI]"])
    med = a4["treeroute vs same-link rivals: median rho, top-20 union [CI] (range)"]
    mm = re.match(r"^(.*) \((\S+) to (\S+)\)$", med)
    cmp("S3.22 median", w22 + " median", q22["Median of those [95% CI]"][j], mm.group(1))
    cmp("S3.22 range", w22 + " range", q22["Range (lowest to highest)"][j], "%s to %s" % (mm.group(2), mm.group(3)))
    cmp("S3.22 RBO", w22 + " RBO", q22["RBO with the rivals' consensus, p = 0.9 [95% CI]"][j], a4["RBO vs consensus [CI]"])
    cmp("S3.22 top 3", w22 + " treeroute top 3", q22["treeroute v1's top 3"][j], a4["treeroute top 3"])
    cmp("S3.22 top 3", w22 + " consensus top 3", q22["Consensus top 3"][j], a4["consensus top 3"])
    oh = a4["own history: treeroute [CI] / median rival [CI]"].split(" / ")
    for qq, o in (("Own-history share, treeroute v1 [95% CI]", oh[0]), ("Own-history share, median of the rivals\u1d9c [95% CI]", oh[1])):
        a = norm(q22[qq][j])
        for lab in BB4:
            a = a.replace(lab, "")
        cmp("S3.22 own-history share", w22 + " " + qq, q22[qq][j], o, ours_n=a)
    # per-rival Spearman: the AW3 variable-level pair row's spearman_top20_union head
    for item in q22["Spearman of treeroute v1 with each same-link rival"][j].split("; "):
        name, val = item.rsplit(" ", 1)
        m_ = MINLINE[name]
        key = " vs ".join(sorted([m_, "treeroute"]))
        offv = a3["levels"]["variable"]["pairs"][key]["spearman_top20_union"].split(" [")[0]
        cmp("S3.22 per-rival Spearman", w22 + " " + name, val, offv)
    # per-rival own-history share: AW3 families (percent, one decimal) against ours (fraction, two decimals)
    cell = q22["Own-history share of each same-link rival"][j]
    for lab in BB4:
        cell = cell.replace(lab, "")
    for item in cell.split("; "):
        name, val = item.rsplit(" ", 1)
        m_ = MINLINE[name]
        offp = a3["families"][("own history", m_)]
        compared["S3.22 per-rival own-history share (consistency, other precision)"] += 1
        x = float(val.replace(MINUS, "-"))
        y = float(offp.rstrip("%")) / 100.0
        if abs(x - y) > 0.005 + 0.0005 + 1e-12:
            mism.append(("S3.22 per-rival own-history", w22 + " " + name, val, offp, False, "inconsistent beyond the two roundings"))

# ---------- Table S3.18 panel a (AW3 'Models and links' and 'Main set') ----------
t18 = tables[("S3.18", "a")]
for r, ln in zip(t18["rows"], t18["lines"]):
    p = PDISP[r[0]]
    m_ = MINLINE[r[1].split(" (`")[0]]
    a3 = AW3[p]
    w = "Table S3.18a line %d (%s, %s)" % (ln, r[0], m_)
    cmp("S3.18 link", w + " link", r[3], "", ours_n=r[3], off_n=LINKDISP[a3["links"][m_].split("|")[0]])
    guard_ours = strip_marks(r[4])
    guard_off = "failed" if m_ in a3["declined"] else ("passed (the adopted arm)" if m_ == "treeroute" else "passed")
    cmp("S3.18 guard", w + " guard", r[4], "", ours_n=guard_ours, off_n=guard_off)
    inmain = m_ in a3["main_set"]
    reasons = []
    if a3["links"][m_] != a3["links"]["treeroute"]:
        reasons.append("another link")
    if m_ in a3["declined"]:
        reasons.append("skill guard failed")
    exp = "yes" if inmain else "no: " + "; ".join(reasons)
    cmp("S3.18 main set", w + " in main set", r[5], "", ours_n=r[5], off_n=exp)

# ---------- Table S3.19 (AW3 header lines) ----------
t19 = rowmap(tables[("S3.19", "")])
for disp, p in PDISP.items():
    r, ln = t19[disp]
    a3 = AW3[p]
    w = "Table S3.19 line %d (%s)" % (ln, disp)
    cmp("S3.19 sample rows", w + " sample rows", r[2], "", ours_n=r[2].replace(",", ""), off_n=str(a3["rows"]))
    cmp("S3.19 regions", w + " regions", r[3], "", ours_n=r[3].replace(",", ""), off_n=str(a3["regions"]))
    for j, lev in ((7, "feature"), (8, "variable")):
        o = a3["levels"][lev]
        cmp("S3.19 players/J/zeros", w + " " + lev, r[j], "", ours_n=r[j].replace(",", ""),
            off_n="%d / %d / %d" % (o["players"], o["active"], len(o["sz"])))
for ln, nt in notes["S3.19"]:
    m = re.match(r"^(PM2\.5|NDVI|Burned fraction|Forest loss|Coral bleaching): variable level \((\d+)\) (.*); feature level \((\d+)\) (.*)\.$", nt)
    if not m:
        continue
    p = PDISP[m.group(1)]
    for lev, cnt, lst in (("variable", m.group(2), m.group(3)), ("feature", m.group(4), m.group(5))):
        names = lst.replace("`", "").split(", ")
        o = AW3[p]["levels"][lev]["sz"]
        cmp("S3.19 structural-zero list", "Table S3.19 note line %d (%s, %s)" % (ln, p, lev), lst, "",
            ours_n="%s|%s" % (cnt, ", ".join(names)), off_n="%d|%s" % (len(o), ", ".join(o)))

# ---------- Tables S3.23-S3.27 ----------
bb1_sign = collections.Counter()
p_for_m = []   # pair labels printed with P where the source label holds M (spec 4.7, version 3)
for p in PROBS:
    tid = TID[p]
    a3 = AW3[p]
    for pan, lev in (("a", "variable"), ("b", "feature")):
        t = tables[(tid, pan)]
        hdr = t["header"]
        offlev = a3["levels"][lev]
        assert len(t["rows"]) == len(offlev["pairs"]), (p, lev)
        for r, ln in zip(t["rows"], t["lines"]):
            ms = [MINLINE[x] for x in strip_marks(r[0]).split(" vs ")]
            key = " vs ".join(sorted(ms))
            orow = offlev["pairs"][key]
            w = "Table %s%s line %d (%s)" % (tid, pan, ln, key)
            # link label: the spec prints the declined names as display names
            lab = r[1]
            M = "; raw model, declined by its guard: "
            P = "; raw model, declined by its skill guard: "
            if P in lab:
                pre, names = lab.split(P)
                lab_n = pre + M + ", ".join(MINLINE[x] for x in names.split(", "))
                p_for_m.append(w)
            else:
                lab_n = lab
            cmp("AW3 pair label", w + " label", r[1], orow["label"], ours_n=lab_n)
            for jj, hname in enumerate(hdr[2:], start=2):
                st = STATCOL[hname]
                cell = r[jj]
                if st == "sign_agreement_top10":
                    mo = re.match(r"^(undefined|\u2212?\d\.\d\d)(?: \[(\S+), (\S+)\])? \((\d+) signs?(?:; ([\d,]+) finite draws)?\)$", cell)
                    mf = re.match(r"^(nan|-?\d\.\d\d) \((\d+) signs\)$", orow[st])
                    assert mo and mf, (cell, orow[st])
                    head_o = "nan" if mo.group(1) == "undefined" else mo.group(1).replace(MINUS, "-")
                    cmp("AW3 sign agreement value and count", w + " sign agreement", cell, orow[st],
                        ours_n="%s (%s)" % (head_o, mo.group(4)), off_n="%s (%s)" % (mf.group(1), mf.group(2)))
                    if mo.group(2) is not None:
                        bb1_sign["interval added (BB1)"] += 1
                    else:
                        bb1_sign["no interval (0 finite draws)"] += 1
                    if mo.group(5):
                        bb1_sign["finite-draw count printed"] += 1
                    if mo.group(1) == "undefined":
                        bb1_sign["undefined for nan"] += 1
                    if mo.group(4) == "1":
                        bb1_sign["singular '1 sign' for '1 signs'"] += 1
                    continue
                if st == "tvd_family" and lev == "feature":
                    # BB2: the feature-level cell repeats the variable-level value; the printout has no such column
                    offv = a3["levels"]["variable"]["pairs"][key]["tvd_family"]
                    cmp("AW3 feature-level family-share distance vs the variable-level printout (BB2)", w + " tvd_family", cell, offv)
                    continue
                cmp("AW3 pair statistic", w + " " + st, cell, orow[st])
        # panel c
    tc = rowmap(tables[(tid, "c")])
    for lev, jj in (("variable", 1), ("feature", 2)):
        o = a3["levels"][lev]
        for qq, key in (("Kendall's W of the main set [95% CI]", "W"), ("Mean pairwise Spearman of the main set [95% CI]", "MS")):
            r, ln = tc[qq]
            w = "Table %sc line %d %s %s" % (tid, ln, key, lev)
            if p == "fire":
                cmp("AW3 W / mean Spearman", w, r[jj], o[key],
                    explain=(True, "spec 4.7 panel c and decision 4: fire's main set is one model, value NaN with 0 finite draws, printed 'undefined' with note a (printout 'nan [nan, nan]')"))
            else:
                cmp("AW3 W / mean Spearman", w, r[jj], o[key])
        for rk, (r, ln) in tc.items():
            if rk.startswith("Stability under region resampling: "):
                m_ = MINLINE[rk[len("Stability under region resampling: "):]]
                cmp("AW3 stability", "Table %sc line %d %s %s" % (tid, ln, m_, lev), r[jj], o["stab"][m_])
    # panels d and e
    for pan, lev in (("d", "variable"), ("e", "feature")):
        t = tables[(tid, pan)]
        mods = [MHEAD[strip_marks(h)] for h in t["header"][1:]]
        o = a3["levels"][lev]
        assert set(mods) == set(o["top10"]), (p, lev)
        for r, ln in zip(t["rows"], t["lines"]):
            for m_, cell in zip(mods, r[1:]):
                w = "Table %s%s line %d (%s, rank %s)" % (tid, pan, ln, m_, r[0])
                if r[0] in ("Nonzero variables", "Nonzero players"):
                    cmp("AW3 nonzero count", w, cell, str(o["nonzero"][m_]), ours_n=cell.replace(",", ""))
                else:
                    k = int(r[0]) - 1
                    nm, sh = o["top10"][m_][k]
                    cmp("AW3 top-10 entry", w, cell, "%s %s" % (nm, sh))
    # panel f
    t = tables[(tid, "f")]
    mods = [MHEAD[strip_marks(h)] for h in t["header"][1:]]
    for r, ln in zip(t["rows"], t["lines"]):
        fam = FAMROW[r[0]]
        for m_, cell in zip(mods, r[1:]):
            a = cell
            lab_hit = False
            for lab in BB4:
                if lab in a:
                    a = a.replace(lab, "")
                    lab_hit = True
            ok = cmp("AW3 family share", "Table %sf line %d (%s, %s)" % (tid, ln, fam, m_), cell, a3["families"][(fam, m_)], ours_n=norm(a))
            if ok and lab_hit:
                expl_counts["BB4 label on an equal family-share cell"] += 1
    # panel g
    if (tid, "g") in tables:
        t = tables[(tid, "g")]
        mods = [MHEAD[strip_marks(h)] for h in t["header"][1:]]
        assert set(mods) == set(a3["nzf"]), (p, mods, list(a3["nzf"]))
        for r, ln in zip(t["rows"], t["lines"]):
            for m_, cell in zip(mods, r[1:]):
                w = "Table %sg line %d (%s, %s)" % (tid, ln, m_, r[0])
                if r[0] == "Rows with a forecast above 0":
                    cmp("AW3 nonzero-forecast rows", w, cell, str(a3["nzf"][m_][0]), ours_n=cell.replace(",", ""))
                else:
                    nm, sh = a3["nzf"][m_][1][int(r[0]) - 1]
                    cmp("AW3 nonzero-forecast top-10 entry", w, cell, "%s %s" % (nm, sh))
    else:
        assert not a3["nzf"], p

# ---------------- report ----------------
tot = sum(compared.values())
print("cells compared with an official counterpart:", tot)
for k, v in sorted(compared.items()):
    print("  %5d  %s" % (v, k))
print("sign-agreement cells:", dict(bb1_sign))
print("pair labels printed with P where the source label holds M (spec 4.7, V3-6), turned back to M before the comparison:",
      len(p_for_m), [w.split(" (")[0] for w in p_for_m])
print("equal cells that carry a BB4 label or an en dash:", dict(expl_counts))
print("mismatches:", len(mism), "explained:", sum(1 for x in mism if x[4]), "unexplained:", sum(1 for x in mism if not x[4]))
for cls, where, ours, off, ex, why in mism:
    print("--", "EXPLAINED" if ex else "UNEXPLAINED", "|", cls, "|", where)
    print("     ours:", ours)
    print("     official:", off if off != "" else "(empty)")
    if why:
        print("     why:", why)
