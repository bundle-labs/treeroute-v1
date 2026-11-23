"""Shared helpers of writer s3 (Supplement S3.13 write-up, 2026-11-17): paths, number formats and the prose tokens.

Every prose number is formatted ONCE here from its stored value (paper/supp_build/s3_13/reconcile/cells.json, a
stored file of the SHAP analysis, or a named run record), and each token is checked against the printed string of
the agreed tables where the tables print it. Read only; nothing here writes a file.
"""
import hashlib
import json
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.abspath(os.path.join(STAGE, ".."))
ROOT = os.path.abspath(os.path.join(OUT, "..", "..", ".."))
SHAP = r"D:\treeroute\analysis\shap_v1"
TABLES = os.path.join(OUT, "reconcile", "tables_agreed.md")
CELLS = os.path.join(OUT, "reconcile", "cells.json")
LEAD_OUT = os.path.join(OUT, "_brief", "lead_checks", "verify_v5_claims_out.txt")
PROTOCOL = os.path.join(SHAP, "PROTOCOL.md")
REGISTER = os.path.join(SHAP, "SAMPLE_REGISTER.txt")
PROTOCOL_SHA = "32daa77b893cf7af378b3145a285fa71c0cec61b0b3a51420195415658618abc"
TABLES_SHA_NOTE = "tables_agreed.md version 5"
PROBLEMS = ("pm25", "ndvi", "fire", "defo", "coral")
WORDS = {0: "none", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
         9: "nine", 10: "ten"}


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


def minus(s):
    return s.replace("-", "\u2212")


def f2(x):
    """A statistic with two decimals, the tables' format (U+2212 for a minus)."""
    s = "%.2f" % x
    if s in ("-0.00",):
        raise ValueError("negative zero would print: %r" % x)
    return minus(s)


def pct1(x):
    """A share in percent with one decimal, the tables' format."""
    s = "%.1f%%" % (100.0 * x)
    s2 = format(x, ".1%")
    if s != s2:
        raise ValueError("percent formats disagree for %r: %s vs %s" % (x, s, s2))
    return s


def intc(n):
    if isinstance(n, float):
        if n != math.floor(n):
            raise ValueError("not an integer: %r" % n)
        n = int(n)
    return format(n, ",")


class Cells:
    def __init__(self, path=CELLS):
        with open(path, encoding="utf-8") as f:
            self.d = json.load(f)
        self.entries = self.d["entries"]

    def find(self, table, line, row=None, column=None, part=None, panel=None):
        out = []
        for e in self.entries:
            if e["table"] != table or e.get("line") != line:
                continue
            if row is not None and e.get("row") != row:
                continue
            if column is not None and e.get("column") != column:
                continue
            if part is not None and e.get("part") != part:
                continue
            if panel is not None and e.get("panel") != panel:
                continue
            out.append(e)
        return out

    def one(self, table, line, row=None, column=None, part=None, panel=None):
        r = self.find(table, line, row, column, part, panel)
        if len(r) != 1:
            raise KeyError("%d entries for %s L%s %s/%s/%s/%s" % (len(r), table, line, panel, row, column, part))
        e = r[0]
        if len(e["stored"]) != 1:
            raise ValueError("stored is not one value: %r" % e)
        return e


def stat_ci(cells, table, line, row, column):
    """'v [lo, hi]' from three entries, each formatted once and checked against its printed string."""
    parts = []
    stored = []
    srcs = set()
    for part in ("value", "ci_low", "ci_high"):
        e = cells.one(table, line, row=row, column=column, part=part)
        x = e["stored"][0]
        s = f2(x)
        if s != e["printed"]:
            raise ValueError("format %s != printed %s (%s %s %s %s)" % (s, e["printed"], table, line, row, column))
        parts.append(s)
        stored.append(x)
        srcs.add((e["source"], e["selector"]))
    return "%s [%s, %s]" % tuple(parts), stored, sorted(srcs)


def pct_ci(cells, table, line, row, column):
    parts = []
    stored = []
    srcs = set()
    for part in ("value", "ci_low", "ci_high"):
        e = cells.one(table, line, row=row, column=column, part=part)
        x = e["stored"][0]
        s = pct1(x)
        if s != e["printed"]:
            raise ValueError("format %s != printed %s" % (s, e["printed"]))
        parts.append(s)
        stored.append(x)
        srcs.add((e["source"], e["selector"]))
    return "%s [%s, %s]" % tuple(parts), stored, sorted(srcs)


def read_lead_check():
    with open(LEAD_OUT, encoding="utf-8") as f:
        lines = f.read().split("\n")
    m = None
    for ln in lines:
        m = re.match(r"background pairs: (\d+); same reef site: (\d+) in (\d+) sample rows; "
                     r"dated on/after the explained visit: (\d+)$", ln.strip())
        if m:
            break
    if not m:
        raise ValueError("coral line not found in the lead check output")
    pairs, same, rows_same, later = (int(g) for g in m.groups())
    dups = {}
    for ln in lines:
        m2 = re.match(r"(\w+)\s+(\w+)\s+duplicates_merged: (\d+)$", ln.strip())
        if m2:
            dups[(m2.group(1), m2.group(2))] = int(m2.group(3))
    return {"pairs": pairs, "same": same, "rows_same": rows_same, "later": later, "dups": dups}


def read_protocol():
    with open(PROTOCOL, "rb") as f:
        b = f.read()
    if sha256_bytes(b) != PROTOCOL_SHA:
        raise ValueError("PROTOCOL.md is not the hash-pinned version")
    return b.decode("utf-8")


def read_per_lead(p):
    with open(os.path.join(SHAP, "out", p, "lead_0", "compare", "per_lead.json"), encoding="utf-8") as f:
        d = json.load(f)
    return {k: d[k] for k in ("rows", "draws", "regions", "j_rule", "salt", "main_set", "lead")}


def read_register():
    rows = []
    with open(REGISTER, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            m = re.match(r"(\S+) problem=(\w+) tag=(\w+) leads=(\S+) n=(\d+) ", ln)
            rows.append({"time": m.group(1), "problem": m.group(2), "n": int(m.group(5))})
    return rows


def tokens():
    """Every prose token of S3.13 with its value, stored values and sources (for the facts)."""
    c = Cells()
    t = {}
    src = {}
    # N, regions, locations per region (Table S3.19)
    ns = set()
    regions = {}
    locs = {}
    for p, line in zip(PROBLEMS, (75, 76, 77, 78, 79)):
        ns.add(c.one("S3.19", line, row=p, column="sample_rows", part="value")["stored"][0])
        regions[p] = c.one("S3.19", line, row=p, column="regions", part="value")["stored"][0]
        locs[p] = c.one("S3.19", line, row=p, column="locations", part="value")["stored"][0]
    assert ns == {1000}, ns
    pl = {p: read_per_lead(p) for p in PROBLEMS}
    assert all(pl[p]["rows"] == 1000 and pl[p]["draws"] == 2000 and pl[p]["lead"] == 0 for p in PROBLEMS)
    assert all(pl[p]["regions"] == regions[p] for p in PROBLEMS)
    assert all("> 1e-12" in pl[p]["j_rule"] for p in PROBLEMS)
    t["N"] = intc(1000)
    t["B"] = intc(pl["pm25"]["draws"])
    t["REG_MIN"] = intc(min(regions.values()))
    t["REG_MAX"] = intc(max(regions.values()))
    lpr = {}
    for p in ("pm25", "ndvi", "fire", "defo"):
        q, r = divmod(locs[p], regions[p])
        assert r == 0, (p, locs[p], regions[p])
        lpr[p] = q
    assert lpr["pm25"] == lpr["ndvi"]
    t["LPR_PM25"] = WORDS[lpr["pm25"]]
    t["LPR_FIRE"] = WORDS[lpr["fire"]]
    t["LPR_DEFO"] = WORDS[lpr["defo"]]
    src["samples"] = {"regions": regions, "locations": locs, "per_lead": pl}
    # protocol text constants
    prot = read_protocol()
    m = re.search(r"computed SHAP values on (\d+)-(\d+) rows of the real coral headline", prot.replace("\n", " "))
    t["SMOKE_ROWS"] = intc(int(m.group(2)))
    src["smoke_rows"] = (int(m.group(1)), int(m.group(2)))
    m = re.search(r"top-20 when J has (\d+) or more players", prot.replace("\n", " "))
    t["J200"] = intc(int(m.group(1)))
    # coral background and NDVI duplicates (lead check output)
    lc = read_lead_check()
    pairs_cells = c.one("S3.19", 79, row="coral", column="background_pairs", part="value")["stored"][0]
    assert lc["pairs"] == pairs_cells == 50000
    t["CORAL_SAME"] = intc(lc["same"])
    t["CORAL_PAIRS"] = intc(lc["pairs"])
    t["CORAL_ROWS_SAME"] = intc(lc["rows_same"])
    assert lc["later"] == 0
    t["CORAL_LATER"] = WORDS[lc["later"]]
    nd = lc["dups"][("ndvi", "treeroute")]
    for m_ in ("rival_lgbm", "rival_rf", "rival_ridge", "treeroute_B1"):
        assert lc["dups"][("ndvi", m_)] == nd
    assert lc["dups"][("ndvi", "rival_bardl_h1")] == 0
    assert all(v == 0 for (p, m_), v in lc["dups"].items() if p != "ndvi")
    t["NDVI_DUPS"] = WORDS[nd]
    src["lead_check"] = lc
    # BARDL and NDVI's J (Tables S3.24 and S3.19)
    bv = c.one("S3.24", 314, column="rival_bardl_h1", part="count")["stored"][0]
    bf = c.one("S3.24", 330, column="rival_bardl_h1", part="count")["stored"][0]
    jv = c.one("S3.19", 76, row="ndvi", column="variable", part="J")["stored"][0]
    jf = c.one("S3.19", 76, row="ndvi", column="feature", part="J")["stored"][0]
    t["BARDL_VARS"] = WORDS[bv]
    t["BARDL_COLS"] = WORDS[bf]
    t["NDVI_JV"] = intc(jv)
    t["NDVI_JF"] = intc(jf)
    t["BARDL_ZERO_VARS"] = intc(jv - bv)
    t["BARDL_ZERO_PLAYERS"] = intc(jf - bf)
    with open(TABLES, encoding="utf-8") as f:
        tab = f.read().split("\n")
    assert tab[317].startswith("| Rank | treeroute v1 | Ridge | Random forest | LightGBM | BARDL‡ |"), tab[317]
    bardl_cells = [ln.split("|")[6].strip() for ln in tab[319:329]]  # S3.24 e rows 1-10 (lines 320-329), BARDL
    lag_names = sorted({x for x in bardl_cells if x.startswith("`x__hist_last_")})
    assert len(lag_names) == 3, lag_names
    t["BARDL_LAGS"] = WORDS[len(lag_names)]
    src["bardl"] = {"nonzero_variables": bv, "nonzero_players": bf, "J_variables": jv, "J_players": jf,
                    "hist_lags": lag_names}
    # exactness: coral E8 rows (Table S3.21)
    e8 = c.one("S3.21", 143, row="E8", column="coral", part="rows")["stored"][0]
    t["CORAL_E8"] = intc(e8)
    # main-text row (Table S3.22)
    for p, k in (("pm25", "PM25"), ("ndvi", "NDVI"), ("defo", "DEFO"), ("coral", "CORAL")):
        t["W_" + k], src["W_" + k], _ = stat_ci(c, "S3.22", 157, "kendall_w", p)
        t["SP_" + k], src["SP_" + k], _ = stat_ci(c, "S3.22", 159, "spearman_median", p)
        t["RBO_" + k], src["RBO_" + k], _ = stat_ci(c, "S3.22", 161, "rbo_vs_consensus", p)
    for p, k in (("pm25", "PM25"), ("ndvi", "NDVI"), ("defo", "DEFO"), ("fire", "FIRE")):
        t["OH_TR_" + k], src["OH_TR_" + k], _ = stat_ci(c, "S3.22", 164, "own_history_treeroute", p)
    for p, k in (("pm25", "PM25"), ("ndvi", "NDVI"), ("defo", "DEFO")):
        t["OH_MED_" + k], src["OH_MED_" + k], _ = stat_ci(c, "S3.22", 166, "own_history_median_rivals", p)
    wf = c.one("S3.22", 157, row="kendall_w", column="fire", part="value")
    assert wf["stored"] == [None] and wf["printed"] == "undefined"
    # both NDVI and PM2.5 Spearman intervals include 0
    for k in ("PM25", "NDVI"):
        lo, hi = src["SP_" + k][1], src["SP_" + k][2]
        assert lo < 0 < hi, (k, lo, hi)
    # rows with a forecast above 0 (Table S3.25 g)
    nz = c.one("S3.25", 448, row="rows", column="treeroute", part="count")["stored"][0]
    t["FIRE_NZ"] = intc(nz)
    # coral context and calendar (Table S3.27 f), main set
    cc = {}
    for m_ in ("treeroute", "rival_rf", "rival_lgbm", "rival_hgb_l1", "rival_ridge", "rival_lgbm_tweedie"):
        e = c.one("S3.27", 642, row="context and calendar", column=m_, part="share")
        cc[m_] = (e["stored"][0], e["printed"])
        assert pct1(e["stored"][0]) == e["printed"]
    main = ("treeroute", "rival_rf", "rival_lgbm", "rival_hgb_l1")
    lo_m = min(main, key=lambda m_: cc[m_][0])
    hi_m = max(main, key=lambda m_: cc[m_][0])
    assert lo_m == "treeroute" and hi_m == "rival_lgbm", (lo_m, hi_m)
    t["CC_CORAL_TR"] = cc["treeroute"][1]
    t["CC_CORAL_LGBM"] = cc["rival_lgbm"][1]
    src["coral_cc"] = cc
    # B1 (Tables S3.29, S3.30)
    for p, k in (("pm25", "PM25"), ("ndvi", "NDVI"), ("fire", "FIRE")):
        t["B1SN_" + k], src["B1SN_" + k], _ = pct_ci(c, "S3.29", 721, "seasonal_normal", p)
    ids = [c.one("S3.30", 777, row="max_abs_diff_phi", column="result", part="value")["stored"][0],
           c.one("S3.30", 778, row="max_abs_diff_phiv", column="result", part="value")["stored"][0]]
    assert ids == [0.0, 0.0]
    t["DEFO_ID"] = "0"
    # B1 top variable is normal on all three (Table S3.29 b) and B2 seasonal normal exactly 0 (S3.23-S3.25 f)
    top3_line = tab[726]
    assert top3_line.startswith("| Top 3 (share) |") and top3_line.count("`normal` ") == 3, top3_line
    for tb, line in (("S3.23", 249), ("S3.24", 340), ("S3.25", 432)):
        es = c.find(tb, line, row="seasonal normal", part="share")
        assert es and all(e["stored"] == [0.0] for e in es), (tb, line)
    # BB1 thin intervals
    thin = [e for e in c.entries if e.get("part") == "n_finite"]
    assert len(thin) == 3 and all(e["table"] == "S3.25" and e["line"] in (354, 355, 356) for e in thin)
    assert all(e["stored"][0] < 2000 for e in thin)
    t["THIN"] = WORDS[len(thin)]
    src["thin"] = [(e["row"], e["stored"][0], e["printed"]) for e in thin]
    # sample registrations (timeline)
    src["register"] = read_register()
    return t, src, c


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    tt, ss, _ = tokens()
    for k in sorted(tt):
        print("%-20s %s" % (k, tt[k]))
