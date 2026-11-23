# -*- coding: utf-8 -*-
# Builder A of the S3.13 tables, written from OUT\spec\TABLE_SPEC.md.
# Reads only the sources of the spec's section 1, runs the checks of section 3, and writes
# OUT\A\tables.md and OUT\A\cells.json (sections 2, 4 and 5). On any failed check or rule it stops
# with a message and writes neither file.
# Run as: py -3.9 -I -B <this script>

import sys
import os
import re
import json
import math
import hashlib

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))  # OUT\A\scripts
OUT_X = os.path.dirname(HERE)  # OUT\A
SHAP = "D:\\treeroute\\analysis\\shap_v1"
VDIR = SHAP + "\\verify_v1"


class Stop(Exception):
    pass


def stop(msg):
    raise Stop(msg)


def need(cond, msg):
    if not cond:
        stop(msg)


# ---------------------------------------------------------------------------------------------
# 2.1-2.4 names
# ---------------------------------------------------------------------------------------------

PROBLEMS = ["pm25", "ndvi", "fire", "defo", "coral"]
P_DISP = {"pm25": "PM2.5", "ndvi": "NDVI", "fire": "Burned fraction", "defo": "Forest loss",
          "coral": "Coral bleaching"}
P_INL = {"pm25": "PM2.5", "ndvi": "NDVI", "fire": "burned fraction", "defo": "forest loss",
         "coral": "coral bleaching"}
MODELS = ["treeroute", "rival_ridge", "rival_rf", "rival_lgbm", "rival_lgbm_tweedie", "rival_hgb_l1",
          "rival_bardl_h1"]
M_INL = {"treeroute": "treeroute v1", "rival_ridge": "Ridge", "rival_rf": "random forest",
         "rival_lgbm": "LightGBM", "rival_lgbm_tweedie": "Tweedie booster",
         "rival_hgb_l1": "absolute-error booster", "rival_bardl_h1": "BARDL"}
M_HDR = {"treeroute": "treeroute v1", "rival_ridge": "Ridge", "rival_rf": "Random forest",
         "rival_lgbm": "LightGBM", "rival_lgbm_tweedie": "Tweedie booster",
         "rival_hgb_l1": "Absolute-error booster", "rival_bardl_h1": "BARDL"}
LINK_DISP = {"identity": "identity", "log_c": "log(y + c)", "log_mu": "log μ", "arcsine": "arcsine"}
FAMS = ["own history", "global indices", "local drivers", "context and calendar", "seasonal normal"]
FAM_ROW = {"own history": "Own history", "global indices": "Global indices", "local drivers": "Local drivers",
           "context and calendar": "Context and calendar", "seasonal normal": "Seasonal normal"}
FAM_LABEL = {"own history": "(no own-history input)", "global indices": "(no global-index input)",
             "local drivers": "(no local-driver input)",
             "context and calendar": "(no context or calendar input)",
             "seasonal normal": "(no seasonal-normal input)"}
FAM_B1KEY = {"own history": "own_history", "global indices": "global_indices", "local drivers": "local_drivers",
             "context and calendar": "context_and_calendar", "seasonal normal": "seasonal_normal"}
RIDGE4 = ("fire", "pm25", "defo", "ndvi")
AW3_ID = {"pm25": "S3.23", "ndvi": "S3.24", "fire": "S3.25", "defo": "S3.26", "coral": "S3.27"}
B1P = ["pm25", "ndvi", "fire"]
B1LOGP = ["pm25", "ndvi", "fire", "defo"]

MINUS = "\u2212"
EN = "\u2013"
TIMES = "\u00d7"
DAG = "\u2020"
DDAG = "\u2021"
SECT = "\u00a7"
SA = "\u1d43"
SB = "\u1d47"
SC = "\u1d9c"
SD = "\u1d48"
SUPD = {"0": "\u2070", "1": "\u00b9", "2": "\u00b2", "3": "\u00b3", "4": "\u2074", "5": "\u2075",
        "6": "\u2076", "7": "\u2077", "8": "\u2078", "9": "\u2079", "-": "\u207b"}


def by_display(models):
    for m in models:
        need(m in MODELS, "model not in the table of 2.2: %r" % (m,))
    return sorted(models, key=MODELS.index)


def model_list(models):
    ms = by_display(list(models))
    if not ms:
        return "none"
    return ", ".join(M_INL[m] for m in ms)


def name_list(names):
    return ", ".join("`" + n + "`" for n in names)


def link_base(s):
    need(isinstance(s, str) and len(s) > 0, "bad link string %r" % (s,))
    b = s.split("|", 1)[0]
    need(b in LINK_DISP, "unknown link %r" % (b,))
    return b


def display_pairs(models):
    ms = by_display(list(models))
    out = []
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            out.append((ms[i], ms[j]))
    return out


def pair_text(e, l):
    return M_INL[e] + " vs " + M_INL[l]


# ---------------------------------------------------------------------------------------------
# 2.5 number formats
# ---------------------------------------------------------------------------------------------

def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def finite(x):
    return is_num(x) and math.isfinite(x)


def is_undef(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def NUM2(x):
    need(finite(x), "NUM2 of a value that is not finite: %r" % (x,))
    if x == 0.0:
        return "0.00"
    s = format(x, ".2f")
    if s[0] == "-":
        s = MINUS + s[1:]
    return s


def PCT1(x):
    need(finite(x) and x >= 0, "PCT1 of %r" % (x,))
    if x == 0.0:
        return "0.0%"
    y = 100.0 * x
    if y < 0.05:
        return "<0.1%"
    return format(y, ".1f") + "%"


def COUNT(n):
    need(not isinstance(n, bool), "COUNT of a bool")
    if isinstance(n, int):
        return format(n, ",")
    if isinstance(n, float) and n.is_integer():
        return format(int(n), ",")
    stop("COUNT of %r" % (n,))


def SCI2(x):
    need(finite(x), "SCI2 of %r" % (x,))
    if x == 0.0:
        return "0"
    m, e = format(abs(x), ".1e").split("e")
    sup = "".join(SUPD[c] for c in str(int(e)))
    return (MINUS if x < 0 else "") + m + " " + TIMES + " 10" + sup


def SECS(x):
    need(finite(x), "SECS of %r" % (x,))
    return format(x, ",.1f")


def MED(x):
    need(finite(x), "MED of %r" % (x,))
    return COUNT(x) if float(x).is_integer() else format(x, ".1f")


def self_test():
    vec = [(NUM2(0.625), "0.62"), (NUM2(0.875), "0.88"), (NUM2(-0.004), MINUS + "0.00"), (NUM2(-0.0), "0.00"),
           (NUM2(-0.1214), MINUS + "0.12"), (PCT1(0.0625), "6.2%"), (PCT1(0.0002), "<0.1%"), (PCT1(0.0), "0.0%"),
           (PCT1(0.14169933950641164), "14.2%"), (COUNT(1140), "1,140"), (COUNT(10.0), "10"),
           (SCI2(9.237055564881302e-14), "9.2 × 10⁻¹⁴"), (SCI2(2.220446049250313e-16), "2.2 × 10⁻¹⁶"),
           (SECS(2636.6), "2,636.6")]
    for got, want in vec:
        need(got == want, "format self-test failed: %r != %r" % (got, want))


# ---------------------------------------------------------------------------------------------
# cells.json entries and Markdown lines
# ---------------------------------------------------------------------------------------------

class Num(object):
    __slots__ = ("table", "panel", "row", "column", "part", "printed", "source", "selector", "stored")

    def __init__(self, ctx, part, printed, source, selector, stored):
        self.table = ctx["table"]
        self.panel = ctx["panel"]
        self.row = ctx["row"]
        self.column = ctx["column"]
        self.part = part
        self.printed = printed
        self.source = source
        self.selector = selector
        self.stored = stored


def st(x):
    if isinstance(x, float):
        need(not math.isinf(x), "infinite stored value")
        if math.isnan(x):
            return None
    need(x is None or is_num(x), "stored value is not a number: %r" % (x,))
    return x


def N(ctx, part, printed, source, selector, stored):
    return Num(ctx, part, printed, source, selector, [st(v) for v in stored])


def C(table, panel, row, column):
    return {"table": table, "panel": panel, "row": row, "column": column}


def text_of(frags):
    out = []
    for f in frags:
        if isinstance(f, Num):
            out.append(f.printed)
        else:
            need(isinstance(f, str), "bad fragment %r" % (f,))
            out.append(f)
    return "".join(out)


class Line(object):
    __slots__ = ("text", "nums")

    def __init__(self, text, nums=None):
        need("\n" not in text and "\r" not in text, "line break inside a line")
        self.text = text
        self.nums = nums or []


def const_line(text):
    return Line(text, [])


def note_line(frags):
    t = text_of(frags)
    return Line(t, [(f, t) for f in frags if isinstance(f, Num)])


def row_line(cells, ncols):
    need(len(cells) == ncols, "row with %d cells, header has %d" % (len(cells), ncols))
    texts = []
    nums = []
    for frags in cells:
        t = text_of(frags)
        need("|" not in t and "\n" not in t, "cell holds | or a line break: %r" % (t,))
        need(t == t.strip() and t != "", "cell with padding or empty: %r" % (t,))
        texts.append(t)
        for f in frags:
            if isinstance(f, Num):
                nums.append((f, t))
    return Line("| " + " | ".join(texts) + " |", nums)


def header_line(names):
    for n in names:
        need("|" not in n and n == n.strip() and n != "", "bad header cell %r" % (n,))
    return Line("| " + " | ".join(names) + " |", [])


def sep_line(ncols):
    return Line("|" + "---|" * ncols, [])


def ncols_of(header_text):
    need(header_text.startswith("| ") and header_text.endswith(" |"), "bad header %r" % (header_text,))
    return len(header_text[2:-2].split(" | "))


# selectors
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def jpath(*segs):
    out = ""
    for s in segs:
        if isinstance(s, int) and not isinstance(s, bool):
            out += "[" + str(s) + "]"
        else:
            need(isinstance(s, str), "bad path segment %r" % (s,))
            if IDENT.match(s):
                out += ("" if out == "" else ".") + s
            else:
                out += "[" + json.dumps(s) + "]"
    return out


def psel(keys, column):
    return "; ".join("%s=%s" % (k, v) for k, v in keys) + "; column=" + column


def sels_pairs(keys):
    return {"value": psel(keys, "value"), "ci_low": psel(keys, "ci_low"), "ci_high": psel(keys, "ci_high"),
            "n_finite": psel(keys, "finite_replicates")}


def sels_aw4(key):
    return {"value": jpath(key, "value"), "ci_low": jpath(key, "ci", 0), "ci_high": jpath(key, "ci", 1),
            "n_finite": jpath(key, "ci", 2)}


def sels_pl(level, key):
    return {"value": jpath(level, key, "value"), "ci_low": jpath(level, key, "ci", 0),
            "ci_high": jpath(level, key, "ci", 1), "n_finite": jpath(level, key, "finite_replicates")}


def sels_obj(*path):
    return {"value": jpath(*(path + ("value",))), "ci_low": jpath(*(path + ("ci_low",))),
            "ci_high": jpath(*(path + ("ci_high",))), "n_finite": jpath(*(path + ("n_finite",)))}


# 2.6 composite cells (as fragment lists)

def ci2(ctx, D, v, lo, hi, nf, src, sels, fmt=None):
    fmt = fmt or NUM2
    out = []
    if finite(v):
        out.append(N(ctx, "value", fmt(v), src, sels["value"], [v]))
    else:
        need(is_undef(v), "value neither finite nor undefined: %r" % (v,))
        out.append(N(ctx, "value", "undefined", src, sels["value"], [None]))
    if nf is None or nf == 0:
        return out
    need(is_num(nf) and float(nf).is_integer() and nf > 0, "bad finite count %r" % (nf,))
    out += [" [", N(ctx, "ci_low", fmt(lo), src, sels["ci_low"], [lo]), ", ",
            N(ctx, "ci_high", fmt(hi), src, sels["ci_high"], [hi]), "]"]
    if nf < D:
        out += [" (", N(ctx, "n_finite", COUNT(nf), src, sels["n_finite"], [nf]), " finite draws)"]
    return out


def cip(ctx, D, v, lo, hi, nf, src, sels):
    return ci2(ctx, D, v, lo, hi, nf, src, sels, fmt=PCT1)


def sign_cell(ctx, D, v, k, lo, hi, nf, src_p, sel_v, sel_k, src_a, sel_lo, sel_hi, sel_nf):
    out = []
    if finite(v):
        out.append(N(ctx, "value", NUM2(v), src_p, sel_v, [v]))
    else:
        need(is_undef(v), "sign value neither finite nor undefined: %r" % (v,))
        out.append(N(ctx, "value", "undefined", src_p, sel_v, [None]))
    need(isinstance(nf, int) and not isinstance(nf, bool) and nf >= 0, "bad A n_finite %r" % (nf,))
    if nf > 0:
        out += [" [", N(ctx, "ci_low", NUM2(lo), src_a, sel_lo, [lo]), ", ",
                N(ctx, "ci_high", NUM2(hi), src_a, sel_hi, [hi]), "]"]
    out.append(" (")
    out.append(N(ctx, "signs", COUNT(k), src_p, sel_k, [k]))
    out.append(" sign" if k == 1 else " signs")
    if 0 < nf < D:
        out += ["; ", N(ctx, "n_finite", COUNT(nf), src_a, sel_nf, [nf]), " finite draws"]
    out.append(")")
    return out


def top_frags(ctx, name, share, src, sel):
    need(isinstance(name, str) and name != "", "bad player name %r" % (name,))
    return ["`" + name + "` ", N(ctx, "share", PCT1(share), src, sel, [share])]


# ---------------------------------------------------------------------------------------------
# 1. sources
# ---------------------------------------------------------------------------------------------

def s_cmp(p, f):
    return "SHAP\\out\\%s\\lead_0\\compare\\%s" % (p, f)


def s_piece(p, m, f):
    return "SHAP\\out\\%s\\lead_0\\%s\\%s" % (p, m, f)


def s_gates(p):
    return "SHAP\\rebuild\\%s\\lead_0\\gates.json" % p


def s_man(p):
    return "SHAP\\sample\\%s\\sample_manifest.json" % p


def s_log(p):
    return "SHAP\\logs\\tr_shap_%s_lead0.log" % p


S_REG = "SHAP\\SAMPLE_REGISTER.txt"
S_A = "V\\A\\results.json"
S_MAX = "V\\_lead\\outputs\\bardl_maxima.txt"


def real(short):
    if short.startswith("SHAP\\"):
        return SHAP + short[4:]
    if short.startswith("V\\"):
        return VDIR + short[1:]
    stop("unknown short path %r" % (short,))


def load_json(short):
    with open(real(short), "r", encoding="utf-8") as f:
        return json.load(f)


def load_parquet(short, cols):
    df = pd.read_parquet(real(short))
    for c in cols:
        need(c in df.columns, "%s has no column %s" % (short, c))
    lists = {c: df[c].tolist() for c in cols}
    return [{c: lists[c][i] for c in cols} for i in range(len(df))]


PL, AW4, PAIRS, PAIRS_ROWS, IMP, FAM, META, EXACT, RIDGE, GATES, MAN, REG, B1META, B1DONE, LOGB = (
    {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})
R = None
MAXI = None
NOVAR = {}
RANK = {}


def load_all():
    global R, MAXI
    for p in PROBLEMS:
        PL[p] = load_json(s_cmp(p, "per_lead.json"))
        AW4[p] = load_json(s_cmp(p, "AW4_main_row.json"))
        rows = load_parquet(s_cmp(p, "pairs.parquet"),
                            ["level", "model_a", "model_b", "pair_label", "statistic", "value", "ci_low", "ci_high",
                             "finite_replicates", "signs_compared"])
        PAIRS_ROWS[p] = rows
        d = {}
        for r in rows:
            k = (r["level"], r["model_a"], r["model_b"], r["statistic"])
            need(k not in d, "pairs.parquet %s: duplicate row %r" % (p, k))
            d[k] = r
        PAIRS[p] = d
        IMP[p] = load_parquet(s_cmp(p, "importance.parquet"), ["level", "model", "player", "active", "mean_abs", "share"])
        fam = {}
        for r in load_parquet(s_cmp(p, "families.parquet"), ["model", "family", "share"]):
            k = (r["model"], r["family"])
            need(k not in fam, "families.parquet %s: duplicate %r" % (p, k))
            fam[k] = r["share"]
        FAM[p] = fam
        META[p] = {}
        EXACT[p] = {}
        for m in PL[p]["models"]:
            META[p][m] = load_json(s_piece(p, m, "meta.json"))
            if m != "treeroute":
                EXACT[p][m] = load_json(s_piece(p, m, "exactness.json"))
        rpath = real(s_piece(p, "rival_ridge", "ridge_shap_exactness.json"))
        if p in RIDGE4:
            need(os.path.isfile(rpath), "%s: ridge_shap_exactness.json missing" % p)
            RIDGE[p] = load_json(s_piece(p, "rival_ridge", "ridge_shap_exactness.json"))
        GATES[p] = load_json(s_gates(p))
        MAN[p] = load_json(s_man(p))
        if p in B1LOGP:
            B1META[p] = load_json(s_piece(p, "treeroute_B1", "meta.json"))
            B1DONE[p] = load_json(s_piece(p, "treeroute_B1", "rows.parquet.done.json"))
    # register
    with open(real(S_REG), "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    for i, line in enumerate(lines, 1):
        if line.strip() == "":
            continue
        toks = line.split(" ")
        fields = {}
        for t in toks[1:]:
            need("=" in t, "register line %d: field without '=': %r" % (i, t))
            k, v = t.split("=", 1)
            fields[k] = v
        p = fields.get("problem")
        need(p is not None, "register line %d has no problem" % i)
        if p in PROBLEMS:
            need(p not in REG, "register: problem %s twice" % p)
            need("n" in fields and "sample" in fields, "register line %d lacks n or sample" % i)
            REG[p] = {"line": i, "n_text": fields["n"], "sample": fields["sample"]}
    for p in PROBLEMS:
        need(p in REG, "register: no line for %s" % p)
    R = load_json(S_A)
    MAXI = parse_maxima()
    for p in B1LOGP:
        LOGB[p] = parse_log(p)


MAX_RE = re.compile(r"^\s+(jaccard_top5|jaccard_top10|jaccard_top20|rho20|rbo090|rbo095)\s+spread ([0-9.]+) -> \S+ "
                    r"\(3 sig\. \S+\) at (\w+)/(\w+)/(\S+); values ([0-9.\-]+) / ([0-9.\-]+) / ([0-9.\-]+)$")
MAX_STATS = ["jaccard_top5", "jaccard_top10", "jaccard_top20", "rho20", "rbo090", "rbo095"]


def parse_maxima():
    with open(real(S_MAX), "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    first = lines[0].lstrip("\ufeff")
    need(first == "== BARDL pair-levels", "maxima: first line is %r" % (first,))
    out = {}
    i = 1
    while i < len(lines) and not lines[i].startswith("=="):
        line = lines[i]
        mo = MAX_RE.match(line)
        need(mo is not None, "maxima line %d does not match: %r" % (i + 1, line))
        s = mo.group(1)
        need(s not in out, "maxima: %s twice in the first block" % s)
        out[s] = {"line": i + 1, "spread": mo.group(2), "problem": mo.group(3), "level": mo.group(4),
                  "pair": mo.group(5), "v1": mo.group(6), "v2": mo.group(7), "v3": mo.group(8)}
        i += 1
    for s in MAX_STATS:
        need(s in out, "maxima: %s missing in the first block" % s)
    return out


SETUP_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] (\w+) lead 0: (\d+) rows, (\d+) "
                      r"background pairs,")
DONE_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] treeroute SHAP (\w+) lead 0 done in "
                     r"([0-9.]+) s \(tree SHAP ([0-9.]+) s\)$")


def parse_log(p):
    with open(real(s_log(p)), "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    last = None
    for i, line in enumerate(lines, 1):
        mo = SETUP_RE.match(line)
        if mo:
            last = (i, mo)
    need(last is not None, "%s log: no set-up line" % p)
    si, smo = last
    need(smo.group(1) >= "2026-11-15 23:06:00", "%s log: B1 set-up time %s is too early" % (p, smo.group(1)))
    need(smo.group(2) == p, "%s log: set-up line names %s" % (p, smo.group(2)))
    need(smo.group(3) == "1000", "%s log: set-up rows %s" % (p, smo.group(3)))
    done = None
    for j in range(si, len(lines)):
        mo = DONE_RE.match(lines[j])
        if mo:
            done = (j + 1, mo)
            break
    need(done is not None, "%s log: no done line after the B1 set-up line" % p)
    di, dmo = done
    need(dmo.group(2) == p, "%s log: done line names %s" % (p, dmo.group(2)))
    return {"setup_line": si, "pairs_text": smo.group(4), "done_line": di, "total_text": dmo.group(3),
            "tree_text": dmo.group(4), "time": smo.group(1)}


# ---------------------------------------------------------------------------------------------
# 3. checks
# ---------------------------------------------------------------------------------------------

def gate_get(p, gid):
    gs = GATES[p]["gates"]
    ks = [k for k in gs if k.startswith(gid + "_")]
    need(len(ks) <= 1, "%s: gate id %s is ambiguous" % (p, gid))
    if not ks:
        return None
    return gs[ks[0]]


def exact_record(p, m):
    """(source, {rows, pre, clipped, max}: (value, selector) or None, pass)."""
    if m == "treeroute":
        v = GATES[p]["gates"]["E8_predictions"]["values"]
        b = ("gates", "E8_predictions", "values")
        return (s_gates(p), {"rows": (v["rows_checked"], jpath(*(b + ("rows_checked",)))),
                             "pre": (v["pre_bit_equal"], jpath(*(b + ("pre_bit_equal",)))),
                             "clipped": (v["arm_bit_equal"], jpath(*(b + ("arm_bit_equal",)))),
                             "max": (v["max_abs_pre"], jpath(*(b + ("max_abs_pre",))))},
                GATES[p]["gates"]["E8_predictions"]["pass"])
    if m == "rival_ridge" and p in RIDGE4:
        r = RIDGE[p]
        return (s_piece(p, m, "ridge_shap_exactness.json"),
                {"rows": (r["rows"], "rows"), "pre": (r["bit_equal_rows"], "bit_equal_rows"),
                 "clipped": (r["raw"]["bit_equal_rows"], "raw.bit_equal_rows"),
                 "max": (r["max_abs_diff"], "max_abs_diff")}, r["pass"])
    e = EXACT[p][m]
    rec = {"rows": (e["rows"], "rows"), "pre": (e["bit_equal_rows"], "bit_equal_rows"),
           "clipped": None, "max": (e["max_abs_diff"], "max_abs_diff")}
    if "raw" in e:
        rec["clipped"] = (e["raw"]["bit_equal_rows"], "raw.bit_equal_rows")
    return (s_piece(p, m, "exactness.json"), rec, e["pass"])


def ranking(p, L, m):
    rows = [r for r in IMP[p] if r["level"] == L and r["model"] == m and r["active"] is True]
    names = [r["player"] for r in rows]
    need(len(names) == len(set(names)), "%s %s %s: duplicate players in importance.parquet" % (p, L, m))
    rows.sort(key=lambda r: (-r["mean_abs"], r["player"]))
    return rows


def run_checks():
    n_checks = [0]

    def ck(cond, msg):
        n_checks[0] += 1
        need(cond, "check failed: " + msg)

    for p in PROBLEMS:
        pl = PL[p]
        # 3.1
        ck(pl["rows"] == 1000 and int(REG[p]["n_text"]) == 1000 and MAN[p]["n"] == 1000, "%s: rows / n" % p)
        ck(pl["draws"] == 2000, "%s: draws" % p)
        sha = REG[p]["sample"]
        ck(sha == MAN[p]["sha256"]["sample.parquet"] == pl["sample_sha256"], "%s: sample sha" % p)
        for m in pl["models"]:
            ck(META[p][m]["sample_sha256"] == sha, "%s %s: meta sample sha" % (p, m))
        if p in B1META:
            ck(B1META[p]["sample_sha256"] == sha, "%s B1: meta sample sha" % p)
        with open(real(s_cmp(p, "bootstrap_draws.npy")), "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        ck(h == pl["draws_sha256"], "%s: draws sha" % p)
        ck(pl["regions"] == MAN[p]["regions_in_sample"], "%s: regions" % p)
        # 3.2
        for m in pl["models"]:
            ck(m in MODELS, "%s: model %s not in 2.2" % (p, m))
            ck(os.path.isdir(real("SHAP\\out\\%s\\lead_0\\%s" % (p, m))), "%s: folder of %s" % (p, m))
        ck("treeroute_B1" not in pl["models"], "%s: treeroute_B1 in models" % p)
        ck("treeroute" in pl["models"], "%s: treeroute not in models" % p)
        for m in pl["models"]:
            mt = META[p][m]
            cp = mt["checks_passed"]
            ck(mt["rows"] == 1000 and mt["pass"] is True and mt["structural_zero_violations"] == 0,
               "%s %s: meta rows/pass/S-ZERO" % (p, m))
            ck(all(cp[k] is True for k in ("S-ADD", "S-EVAL", "S-RESID", "S-ZERO")), "%s %s: checks_passed" % (p, m))
            if m != "treeroute":
                ck(exact_record(p, m)[2] is True, "%s %s: S-EXACT record pass" % (p, m))
        if p in RIDGE4:
            ck(EXACT[p]["rival_ridge"]["pass"] is False, "%s: ridge exactness.json pass is not false" % p)
            ck(RIDGE[p]["stage"] == "bits" and RIDGE[p]["pass"] is True, "%s: ridge_shap_exactness" % p)
        else:
            ck(not os.path.exists(real(s_piece(p, "rival_ridge", "ridge_shap_exactness.json"))),
               "%s: unexpected ridge_shap_exactness.json" % p)
        ck(GATES[p]["stopped_at"] is None, "%s: gates stopped_at" % p)
        # guard and main-set consistency (labels of Tables S3.18 and S3.20)
        trl = pl["links"]["treeroute"]
        for m in pl["models"]:
            if m != "treeroute":
                ck((META[p][m]["guard"]["passed"] is True) == (m not in pl["declined_by_guard"]),
                   "%s %s: guard vs declined_by_guard" % (p, m))
            ck((m in pl["main_set"]) == (pl["links"][m] == trl and m not in pl["declined_by_guard"]),
               "%s %s: main set membership" % (p, m))
        ck(AW4[p]["reference_link"] == pl["reference_link"] == trl, "%s: reference link" % p)
        # 3.3
        tails = set()
        for m in pl["models"]:
            parts = pl["links"][m].split("|")
            link_base(pl["links"][m])
            ck(len(parts) == 3 and parts[1].startswith("c=") and parts[2].startswith("ub="),
               "%s %s: link string form" % (p, m))
            tails.add((parts[1], parts[2]))
        ck(len(tails) == 1, "%s: link strings differ in c or ub" % p)
        ms = pl["models"]
        upairs = set()
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                upairs.add(tuple(sorted([ms[i], ms[j]])))
        rows = PAIRS_ROWS[p]
        for L in ("variable", "feature"):
            stats = ["spearman", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10",
                     "rbo_p0.9", "rbo_p0.95", "tvd", "sign_agreement_top10"]
            if L == "variable":
                stats.append("tvd_family")
            if pl[L]["active"] >= 200:
                stats.append("jaccard_top20")
            got = set(r["statistic"] for r in rows if r["level"] == L)
            ck(got == set(stats), "%s %s: statistics %r" % (p, L, sorted(got)))
            for s in stats:
                prs = [(r["model_a"], r["model_b"]) for r in rows if r["level"] == L and r["statistic"] == s]
                ck(len(prs) == len(set(prs)) and set(prs) == upairs, "%s %s %s: pairs" % (p, L, s))
                for a, b in prs:
                    ck(a < b, "%s: model_a < model_b" % p)
            for a, b in upairs:
                labels = set(r["pair_label"] for r in rows if r["level"] == L and r["model_a"] == a
                             and r["model_b"] == b)
                ck(len(labels) == 1, "%s %s %s|%s: one label" % (p, L, a, b))
                lab = labels.pop()
                base = ("same-link" if pl["links"][a] == pl["links"][b]
                        else "cross-link (not comparable in scale or rank)")
                dec = [x for x in (a, b) if x in pl["declined_by_guard"]]
                want = base + ("; raw model, declined by its guard: " + ", ".join(dec) if dec else "")
                ck(lab == want, "%s %s %s|%s: label %r" % (p, L, a, b, lab))
        need(pl["variable"]["active"] < 200, "%s: variable-level J of 200 or more (no layout in the spec)" % p)
        # 3.4
        for L in ("variable", "feature"):
            apairs = R["problems"][p]["levels"][L]["pairs"]
            ck(set(apairs.keys()) == set(a + "|" + b for a, b in upairs), "%s %s: A pair keys" % (p, L))
            for a, b in upairs:
                sa = apairs[a + "|" + b]["sign_agreement"]
                nd = apairs[a + "|" + b]["sign_n_determined"]
                r = PAIRS[p][(L, a, b, "sign_agreement_top10")]
                if is_undef(r["value"]) or is_undef(sa["value"]):
                    ck(is_undef(r["value"]) and is_undef(sa["value"]), "%s %s %s|%s: sign undefined" % (p, L, a, b))
                else:
                    ck(abs(sa["value"] - r["value"]) <= 1e-12, "%s %s %s|%s: sign value" % (p, L, a, b))
                ck(nd["value"] == r["signs_compared"], "%s %s %s|%s: signs" % (p, L, a, b))
                nf = sa["n_finite"]
                ck(isinstance(nf, int) and nf >= 0, "%s %s %s|%s: n_finite" % (p, L, a, b))
                if nf > 0:
                    ck(finite(sa["ci_low"]) and finite(sa["ci_high"]), "%s %s %s|%s: sign ci" % (p, L, a, b))
                else:
                    ck(sa["ci_low"] is None and sa["ci_high"] is None, "%s %s %s|%s: sign ci null" % (p, L, a, b))
        # 3.5
        RANK[p] = {}
        for L in ("variable", "feature"):
            RANK[p][L] = {}
            for m in pl["models"]:
                RANK[p][L][m] = ranking(p, L, m)
                ck(len(RANK[p][L][m]) == pl[L]["active"], "%s %s %s: active rows = J" % (p, L, m))
        top3 = [r["player"] for r in RANK[p]["variable"]["treeroute"][:3]]
        if p == "fire":
            ck(top3 == [x[0] for x in R["problems"]["fire"]["main_row"]["treeroute_top3"]], "fire: top 3 vs A")
            ck(abs(R["problems"]["fire"]["main_row"]["own_history_share_treeroute"]["value"]
                   - FAM[p][("treeroute", "own history")]) <= 1e-12, "fire: A own history")
        else:
            ck(top3 == AW4[p]["treeroute_top3"], "%s: top 3 vs AW4" % p)
        # 3.6
        present = set(pl["families"].values())
        ck(present <= set(FAMS), "%s: unknown family" % p)
        NOVAR[p] = set(FAMS) - present
        want = {"coral": {"own history"}, "defo": {"context and calendar"}}.get(p, set())
        ck(NOVAR[p] == want, "%s: families with no variable %r" % (p, NOVAR[p]))
        for m in pl["models"]:
            for f in FAMS:
                ck((m, f) in FAM[p], "%s: families.parquet lacks %s %s" % (p, m, f))
            for f in NOVAR[p]:
                ck(FAM[p][(m, f)] == 0.0, "%s %s: empty family share is not 0" % (p, m))
        ck(set(k[0] for k in FAM[p]) == set(pl["models"]), "%s: families.parquet models" % p)
        # 3.7
        a4 = AW4[p]
        if p == "fire":
            ck(a4["models_in_main_set"] == ["treeroute"], "fire: AW4 main set")
            ck(a4["cross_link_models"] == ["rival_lgbm", "rival_lgbm_tweedie", "rival_rf"], "fire: cross-link")
            ck(a4["declined_models"] == ["rival_ridge"], "fire: declined")
            kw = a4["kendall_w"]
            ck(is_undef(kw["value"]) and is_undef(kw["ci"][0]) and is_undef(kw["ci"][1]) and kw["ci"][2] == 0,
               "fire: AW4 W")
        else:
            kw = a4["kendall_w"]
            pw = pl["variable"]["kendall_w_main_set"]
            ck(kw["value"] == pw["value"] and kw["ci"][0:2] == pw["ci"] and kw["ci"][2] == pw["finite_replicates"],
               "%s: AW4 W vs per_lead" % p)
            ck(set(a4["models_in_main_set"]) == set(pl["main_set"]), "%s: AW4 main set" % p)
            rivals = [m for m in a4["models_in_main_set"] if m != "treeroute"]
            sp = a4["treeroute_vs_same_link_rivals_median_spearman_top20_union"]
            vals = [PAIRS[p][("variable",) + tuple(sorted([m, "treeroute"])) + ("spearman_top20_union",)]["value"]
                    for m in rivals]
            ck(abs(min(vals) - sp["range"][0]) <= 1e-12 and abs(max(vals) - sp["range"][1]) <= 1e-12,
               "%s: range" % p)
            ck(abs(float(np.median(vals)) - sp["value"]) <= 1e-12, "%s: median Spearman" % p)
            shares = [FAM[p][(m, "own history")] for m in rivals]
            om = a4["own_history_share_median_rival"]["value"]
            ck(abs(float(np.median(shares)) - om) <= 1e-12, "%s: median own history" % p)
            if p in ("pm25", "defo"):
                ck(abs(FAM[p][("rival_lgbm", "own history")] - om) <= 1e-12, "%s: median = LightGBM" % p)
            if p == "ndvi":
                ss = sorted(shares)
                ck(len(ss) == 4 and abs((ss[1] + ss[2]) / 2.0 - om) <= 1e-12, "ndvi: median of four")
            ck(abs(a4["own_history_share_treeroute"]["value"] - FAM[p][("treeroute", "own history")]) <= 1e-12,
               "%s: AW4 treeroute own history vs families" % p)
            cross = [m for m in pl["models"] if pl["links"][m] != pl["links"]["treeroute"]]
            ck(set(a4["cross_link_models"]) == set(cross), "%s: AW4 cross-link models" % p)
            ck(set(a4["declined_models"]) == set(pl["declined_by_guard"]), "%s: AW4 declined" % p)
    # 3.8
    b1 = R["b1"]
    ck(b1["coral"]["status"]["numbers"] == "none", "B1 coral status")
    ck(b1["defo"]["status"]["numbers"] == "identity", "B1 defo status")
    for p in B1P:
        ck(b1[p]["status"]["numbers"] == "full", "B1 %s status" % p)
    ck(b1["defo"]["identity"]["as_expected"] is True, "B1 defo identity")
    for p in B1LOGP:
        lg = LOGB[p]
        rec = b1["defo"]["identity"] if p == "defo" else b1[p]["run"]
        pairs = int(lg["pairs_text"])
        tot = float(lg["total_text"])
        tree = float(lg["tree_text"])
        ck(pairs == rec["pairs_log"] == B1META[p]["pairs"], "B1 %s pairs" % p)
        ck(tot == rec["total_seconds_log"] == B1DONE[p]["seconds"], "B1 %s total seconds" % p)
        ck(tree == rec["tree_shap_seconds_log"] == B1META[p]["tree_shap_seconds"], "B1 %s tree seconds" % p)
    # 3.9
    pl = PL["ndvi"]
    ck(pl["variable"]["nonzero_players"]["rival_bardl_h1"] == 3, "BARDL variable nonzero")
    ck(pl["feature"]["nonzero_players"]["rival_bardl_h1"] == 9, "BARDL feature nonzero")
    top5 = RANK["ndvi"]["variable"]["rival_bardl_h1"][:5]
    hit = [r for r in top5 if r["player"] == "aet_total_mm"]
    ck(len(hit) == 1 and hit[0]["share"] == 0.0, "BARDL: aet_total_mm in the top 5 with share 0")
    for s in MAX_STATS:
        ck(MAXI[s]["problem"] == "ndvi", "maxima %s problem" % s)
        a, b = MAXI[s]["pair"].split("|")
        ck("rival_bardl_h1" in (a, b) and a < b, "maxima %s pair" % s)
        ck(MAXI[s]["level"] in ("variable", "feature"), "maxima %s level" % s)
    j5 = MAXI["jaccard_top5"]
    ck(j5["level"] == "variable" and j5["pair"] == "rival_bardl_h1|treeroute", "maxima jaccard_top5 pair (note text)")
    a, b = j5["pair"].split("|")
    ck(abs(float(j5["v1"]) - PAIRS["ndvi"][(j5["level"], a, b, "jaccard_top5")]["value"]) <= 1e-9,
       "maxima jaccard_top5 value 1")
    # 3.10
    for p in PROBLEMS:
        G = GATES[p]
        res = G["result"]
        for gid in ("E1", "E2", "E0", "E3a", "E3", "E4", "E5", "E6", "E8", "E9", "E10"):
            ck(gate_get(p, gid) is not None, "%s: gate %s missing" % (p, gid))
        for gid in ("E1", "E2", "E0", "E3a", "E3m", "E3", "E4", "E5a", "E6", "E7", "E9", "E8", "E10"):
            g = gate_get(p, gid)
            if g is not None:
                ck(g["pass"] is True, "%s: gate %s pass" % (p, gid))
        ck(gate_get(p, "E5")["pass"] is False, "%s: E5 pass is not false" % p)
        pm = gate_get(p, "E3a")["values"]["path_map"]
        e3m = gate_get(p, "E3m")
        ck((e3m is not None) == (pm is True), "%s: E3m vs path_map" % p)
        if e3m is not None:
            ck(all(x["equal"] is True for x in e3m["values"]["files"]), "%s: E3m files equal" % p)
        ck((gate_get(p, "E5a") is not None) == (res["link"] == "arcsine"), "%s: E5a vs arcsine" % p)
        ck((gate_get(p, "E7") is not None) == (res["weighted"] is True), "%s: E7 vs weighted" % p)
        e4 = gate_get(p, "E4")["values"]
        ck(e4["rows"][0] == e4["rows"][1] and e4["row_key_hash"][0] == e4["row_key_hash"][1], "%s: E4" % p)
        ck(gate_get(p, "E9")["values"]["fits_whose_X_b_differs_from_the_kernel"] == 0, "%s: E9" % p)
        arm = "%s_%s_%s" % (res["link"], res["table_kind"], "gls" if res["weighted"] is True else "unweighted")
        ck(META[p]["treeroute"]["arm"] == arm, "%s: treeroute arm" % p)
        ck(res["link"] == link_base(PL[p]["links"]["treeroute"]), "%s: gates link vs per_lead" % p)
    return n_checks[0]


# ---------------------------------------------------------------------------------------------
# 4. exact texts
# ---------------------------------------------------------------------------------------------

HEADER_COMMENT = "<!-- Draft tables of Supplement S3.13 (Tables S3.18 to S3.30) and of the main-text Table 9: the post hoc SHAP comparison of scope (i), the nowcast of each problem. Built from the stored values with one rounding step per printed number, by the rules of paper/supp_build/s3_13/spec/TABLE_SPEC.md; every printed number is listed in cells.json beside this file. Captions and notes are drafts: the text writers may polish the wording, never the numbers. Rulings AK (post hoc), BA1-BA3 and BB1-BB6 (engine/OWNER_RULINGS_2026-10-06.md). -->"
HEADING1 = "## Main text: Table 9 (Section 5.4, Post hoc analyses)"
HEADING2 = "## Supplement S3.13: SHAP comparison of the main runs"
HEADING3 = "## Supplement S3.13: treeroute v1's B1 sensitivity (kept apart from the main set)"

CAP9 = "**Table 9.** SHAP agreement between treeroute v1 and its rivals at the nowcast, variable level (post hoc). Computed after the test labels were opened, on a fixed sample of 1,000 test rows per problem; report-only, never deciding, and not headline results. Each model is explained in its own link space against a background of the same location's router fit rows of the same calendar month (forest loss, annual: all of them; coral bleaching: other sites' survey visits). Main set: treeroute v1 and its rivals that explain in its link and passed their skill guard. W: Kendall's W of the main set's rankings. Spearman: rank correlation over the union of two models' top-20 variables, here of treeroute v1 with each same-link rival. RBO: rank-biased overlap of treeroute v1's full ranking with the rivals' consensus (the mean of their shares). Own-history share: the share of a model's total mean absolute SHAP value that goes to the location's own lagged labels. Percentile 95% intervals over 2,000 paired bootstrap draws of regions. Every pair, at both levels: Supplement S3.13. <!-- src: D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/compare/AW4_main_row.json (every number but the two cells marked with a dagger); D:/treeroute/analysis/shap_v1/verify_v1/A/results.json problems.fire.main_row (the cells marked with a dagger, ruling BB1); pairs.parquet, importance.parquet and families.parquet for checks only; rulings AK, BA1, BB1, BB4 -->"
HDR9 = "| Problem | Main set | W [95% CI] | Spearman of treeroute v1 with its same-link rivals: median [95% CI] (range) | RBO with the rivals' consensus, p = 0.9 [95% CI] | treeroute v1's top 3 | Consensus top 3 | Own-history share, treeroute v1 [95% CI] | Own-history share, median of the rivalsᶜ [95% CI] |"
NOTES9 = [
    "ᵃ Burned fraction: every rival explains in another link (LightGBM, the random forest and Ridge in log(y + c), the Tweedie booster in log μ), and Ridge also failed its skill guard, so the main set is treeroute v1 alone. W needs two models and is undefined, and the cells that need a rival are empty (–): agreement between treeroute v1 and a rival cannot separate the link from the model there. The cross-link pairs are in Table S3.25.",
    "ᵇ PM2.5: the interval of the RBO with the consensus is asymmetric because the consensus's top variable changes across the region draws.",
    "ᶜ The median of the main-set rivals' own-history shares: on PM2.5 and forest loss LightGBM's share; on NDVI, with four rivals, the mean of the two middle shares.",
    "† From the independent re-computation of the comparison (two implementations that agree): the comparison's output files leave these two cells empty, because they are written only when treeroute v1 has a same-link rival.",
]

CAP18 = "**Table S3.18 (post hoc).** The models explained at the nowcast (a), and the rivals left out, with the reason (b). <!-- src: D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/compare/per_lead.json (models, links, main_set, declined_by_guard); D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/<model>/meta.json (guard.passed); D:/treeroute/analysis/shap_v1/PROTOCOL.md sections 5 and 7 and engine/PENDING_PARTS.md Part 628 (methods; rivals left out and why); rulings AW2, AY1, BA1 -->"
LAB18A = "**a. Explained models.**"
HDR18A = "| Problem | Model (data name) | Model and SHAP method | Link | Skill guard at the nowcast | In the main set |"
SHAP_METHOD = {
    "treeroute": "the adopted arm: tree bank and router; exact interventional TreeSHAP of the trees, router terms exactly linear",
    "rival_ridge": "ridge regression; exact linear SHAP",
    "rival_rf": "random forest, rebuilt from the board's records; exact interventional TreeSHAP",
    "rival_lgbm": "LightGBM; exact interventional TreeSHAP",
    "rival_lgbm_tweedie": "LightGBM with a Tweedie loss; exact interventional TreeSHAP",
    "rival_hgb_l1": "gradient booster on absolute error; exact interventional TreeSHAP",
    "rival_bardl_h1": "published rain-lag Bayesian distributed-lag model, per location; exact linear SHAP over its nine input columns",
}
LAB18B = "**b. Rivals left out.**"
TAB18B = [
    "| Problem | Rival | Why it has no SHAP value |",
    "|---|---|---|",
    "| PM2.5 | MERRA-2 PM2.5: lagged one month, same month, and the placebo entry | One-input calibration maps of the product, fitted per location: the attribution would be 100% on that one input. |",
    "| PM2.5 | CAMS EAC4 | Never run: not obtained (ruling AG1). |",
    "| NDVI | LSTM of Kraft et al. (2019) | Not bit-reproducible without its original deep-learning library, so left out until the owner rules (decision D7); its skill guard failed at the nowcast. |",
    "| Burned fraction | The published rivals, among them the CEMS seasonal fire weather index forecast (SEAS5) | Never run (ruling AS). |",
    "| Forest loss | VT0007, calibrated | One-input map (isotonic on anomalies): the attribution would be 100% on that one input. |",
    "| Forest loss | VT0007, as shipped; VT0007, frozen at 2019 | Not a function of the rows' input columns: the index value as the product gives it. |",
    "| Coral bleaching | NOAA Coral Reef Watch degree heating weeks (nowcast rule) | One-input map (isotonic on degree heating weeks): the attribution would be 100% on that one input. |",
    "| Coral bleaching | CRW Outlook | One-input linear map on anomalies; it could instead be shown as a labelled reference row (decision D15, left at its default). |",
    "| All five | The baselines: the seasonal normal, the last-5-years normal, predict-zero, persistence and damped persistence; on coral bleaching the training median and the last visit | No input feature: there is no SHAP value to compute. |",
]
NOTES18 = [
    "ᵃ Failed: the raw model is explained, labelled, and kept out of Kendall's W, the consensus and the main-text row (decision D6).",
    "Links: identity; log(y + c), with c the problem's constant; log μ, the log of the Tweedie booster's mean; arcsine, the arcsine square root. Within each problem every model has the same c and upper bound, so two models are same-link exactly when their links are the same. The main set is treeroute v1 with its same-link rivals that passed their skill guard.",
]

CAP19 = "**Table S3.19 (post hoc).** The registered samples, their backgrounds and the active sets, nowcast. J: the players to which some model gives more than 10⁻¹² of its total mean absolute SHAP value; the others are structural zeros. <!-- src: D:/treeroute/analysis/shap_v1/SAMPLE_REGISTER.txt (n, sample); D:/treeroute/analysis/shap_v1/sample/<problem>/sample_manifest.json (frame_rows, regions_in_sample, units_in_sample, background_rows); D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/treeroute/meta.json (pairs); D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/compare/per_lead.json (players, active, structural_zero) -->"
HDR19 = "| Problem | Frame rowsᵃ | Sample rows | Regions | Locationsᵇ | Background rows per sample rowᶜ | Background pairs | Feature level: players / J / structural zeros | Variable level: players / J / structural zeros |"
NOTES19 = [
    "ᵃ Frame: the labelled test rows that every compared model covers; the sample is drawn from it, stratified by region and test year.",
    "ᵇ Coral bleaching: a location is a survey visit.",
    "ᶜ Background (B2): the same location's router fit rows of the sample row's calendar month at or before the cut (forest loss, annual: all of them); coral bleaching: the visit's saved pool of other sites' visits. Shown as the lowest to highest number per sample row, with the median.",
    "Structural zeros (exactly 0 in every model at that level, so outside J):",
]

CAP20 = "**Table S3.20 (post hoc).** Checks of every explained model, nowcast: the rebuild or reload reproduces the saved predictions (S-EXACT), the attributions add up to the model's output (S-ADD), its evaluator equals the model (S-EVAL), the unattributed part stays small (S-RESID), and a player that equals the explained row on every background row gets exactly 0 (S-ZERO). <!-- src: D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/<model>/exactness.json, ridge_shap_exactness.json (Ridge outside coral bleaching) and meta.json; D:/treeroute/analysis/shap_v1/rebuild/<problem>/lead_0/gates.json (treeroute v1, gate E8); D:/treeroute/analysis/shap_v1/PROTOCOL.md sections 4 and 11 -->"
HDR20 = "| Problem | Model | Rows checkedᵃ | Bit-identical rows, pre-clip / clippedᵃ | Largest absolute difference, rebuilt − saved (pre-clip, y units) | S-EXACT | Largest additivity error, feature / variable level | S-ZERO violations | S-ADD, S-EVAL, S-RESID, S-ZERO | Skill guard |"
NOTE20A = "ᵃ Rows checked: every test row of the rival's saved predictions; for treeroute v1, every test row of every sampled location (coral bleaching: every test survey visit). Pre-clip: the prediction before the declared bounds are applied; clipped: after. The comparison script checks a rival's pre-clip column only (–: not read)."
NOTE20B_PARTS = [
    "ᵇ Ridge outside coral bleaching is explained by a loader that repeats the rival board's own block-wise scoring, which reproduces every saved prediction. The comparison script's own check of its row-by-row copy of the design, kept as a record, matched ",
    ("pm25", " of ", " rows on PM2.5, "),
    ("ndvi", " of ", " on NDVI, "),
    ("fire", " of ", " on burned fraction and "),
    ("defo", " of ", " on forest loss, because that copy adds the same terms in another order."),
]
NOTE20C = "ᶜ D8: on the arcsine arms of burned fraction and coral bleaching the owner allowed a relative difference of at most 10⁻¹² (ruling AY3), licensed by the bit-identical identity-link twin (gate E5a, Table S3.21)."
NOTE20D = "ᵈ Failed: the raw model is explained, labelled, and kept out of Kendall's W, the consensus and the main-text row (decision D6)."

CAP21 = "**Table S3.21 (post hoc).** treeroute v1's rebuild gates, nowcast, in the order they run. The fitted trees were not kept, so each problem's tree bank and the sampled locations' routers were rebuilt with the run's own engine code; a failed gate stops the problem, except E5, which is informational. <!-- src: D:/treeroute/analysis/shap_v1/rebuild/<problem>/lead_0/gates.json (result; gates.<gate>.pass and .values); D:/treeroute/analysis/shap_v1/PROTOCOL.md sections 4.1 and 11; rulings AY2 (path map, gate E3m) and AY3 (D8) -->"
HDR21 = "| Gate | What it checks | PM2.5 | NDVI | Burned fraction | Forest loss | Coral bleaching |"
GATE_ROWS = [
    ("kept", "Kept arm", "link, answer type and weighting; router type"),
    ("E1", "E1", "engine code hash equals the run manifest's"),
    ("E2", "E2", "library versions and Python equal the manifest's"),
    ("E0", "E0", "the engine's RAM pre-flight predicts no refusal"),
    ("E3a", "E3a", "inputs before the read equal the manifest's (package, groups, constants, file lists, features)"),
    ("E3m", "E3m", "a moved package file has the content, size and time that the freeze locks record (path map)"),
    ("E3", "E3", "package fingerprint, derived settings and run fingerprint after the derive"),
    ("E4", "E4", "training rows: count and row-key hash"),
    ("E5", "E5ᵃ", "bank fingerprint over every tree array (informational)"),
    ("E5a", "E5a", "arcsine arm only: its identity-link twin is bit-identical on every checked row"),
    ("E6", "E6", "c and the guard tolerances equal the run's records"),
    ("E7", "E7", "error-weighted arm only: the error-weight model equals its record"),
    ("E9", "E9", "captured router coefficients reproduce the engine's kernel bit for bit"),
    ("E8", "E8", "kept predictions, pre-clip and clipped, on every test row of every sampled location"),
    ("E10", "E10", "exported trees and evaluator reproduce the engine's tree answers bit for bit"),
]
NOTES21 = [
    "ᵃ E5 is informational: the rebuilt bank's fingerprint differs from the run's on all five problems, while every checked prediction matches (E5a, E8, E10); the cause is not established.",
    "D8 (gate E8 on burned fraction and coral bleaching): a relative difference of at most 10⁻¹² on arcsine arms only (ruling AY3), licensed at this lead by gate E5a.",
]

CAP22 = "**Table S3.22 (post hoc).** The main-text row (Table 9) with its components, nowcast, variable level. From the comparison's output files, except the cells marked †. <!-- src: D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/compare/AW4_main_row.json; pairs.parquet (spearman_top20_union of treeroute v1 with each same-link rival); families.parquet (each same-link rival's own-history share); D:/treeroute/analysis/shap_v1/verify_v1/A/results.json problems.fire.main_row (the cells marked with a dagger, ruling BB1); rulings BB1, BB4, BB6 -->"
HDR22 = "| Quantity | PM2.5 | NDVI | Burned fraction | Forest loss | Coral bleachingᵈ |"
NOTES22 = [
    "ᵃ Burned fraction: every rival explains in another link (LightGBM, the random forest and Ridge in log(y + c), the Tweedie booster in log μ), and Ridge also failed its skill guard, so the main set is treeroute v1 alone. W needs two models and is undefined, and the cells that need a rival are empty (–): agreement between treeroute v1 and a rival cannot separate the link from the model there.",
    "ᵇ PM2.5: the interval of the RBO with the consensus is asymmetric because the consensus's top variable changes across the region draws.",
    "ᶜ The median of the main-set rivals' own-history shares: on PM2.5 and forest loss LightGBM's share; on NDVI, with four rivals, the mean of the two middle shares.",
    "ᵈ Coral bleaching's table of these statistics (AW4_table.md, written on 2026-11-13 at 00:06) was read by an agent on 2026-11-13 at about 15:31, before the independent re-computation; the re-computation's implementers A and B never opened it (ruling BB6).",
    "† From the independent re-computation of the comparison (two implementations that agree): the comparison's output files leave these cells empty, because they are written only when treeroute v1 has a same-link rival (ruling BB1).",
]

CAP_AW3 = "**Table S3.{nn} (post hoc).** {Problem}, nowcast: agreement of the models' SHAP attributions, every pair at the variable level (a) and at the feature level (b); the main set's agreement and each model's stability (c); each model's top 10 at both levels (d, e) and its family shares (f){g_clause}. Link space. Percentile 95% intervals over 2,000 paired region draws, with the number of finite draws where a statistic is defined on fewer of them. Same-link pairs are comparable; cross-link pairs are shown for completeness and are not comparable in scale or rank. Shares are of a model's total mean absolute SHAP value over J, without intervals, as in the comparison's files. <!-- src: D:/treeroute/analysis/shap_v1/out/{p}/lead_0/compare/pairs.parquet, per_lead.json, importance.parquet and families.parquet; D:/treeroute/analysis/shap_v1/verify_v1/A/results.json problems.{p}.levels.<level>.pairs (the sign agreement's intervals, ruling BB1){extra_src}; rulings BB1, BB2{extra_rulings}, BB5 -->"
G_CLAUSE = "; and the arcsine-link models' top 10 on their rows with a forecast above 0 (g)"
EXTRA_SRC_NDVI = "; D:/treeroute/analysis/shap_v1/verify_v1/_lead/outputs/bardl_maxima.txt (the collation moves of the footnote, ruling BB3)"
LAB_A = "**a. Variable level: every pair.**"
LAB_B = "**b. Feature level: every pair.**"
HDR_A = ["Pair", "Link", "Spearman over J", "Spearman, top-20 union", "Kendall's tau-b", "Jaccard top 5",
         "Jaccard top 10", "RBO, p = 0.9", "RBO, p = 0.95", "Share distance (TV)", "Family-share distance (TV)",
         "Sign agreement, top-10 union (signs)†"]
LAB_C = "**c. Agreement within the main set, and each model's stability.**"
HDR_C = "| Statistic | Variable level | Feature level |"
LAB_D = "**d. Variable level: each model's top 10 (share).**"
LAB_E = "**e. Feature level: each model's top 10 (share).**"
LAB_F = "**f. Family shares (sums of the variable-level attributions per row).**"
LAB_G = "**g. Arcsine-link models, rows with a forecast above 0: top 10 (share).**"
NOTE_AW3_FIRE = "ᵃ The main set is treeroute v1 alone: every rival explains in another link, and Ridge also failed its skill guard. Kendall's W and the mean pairwise Spearman need two models and are undefined; agreement between treeroute v1 and a rival cannot separate the link from the model."
NOTES_AW3_ALL1 = [
    "Sign agreement: of the players in the union of the two top-10 sets whose sign is determined in both models (the bootstrap 95% interval of the signed mean excludes 0), the share whose signs agree; in brackets, the number of such players (\"signs\") and, where fewer than 2,000, the number of draws on which the statistic is defined. Undefined: no player qualifies on the full sample.",
    "† The sign agreement's interval is from the independent re-computation of the comparison (two implementations, A and B, that agree; ruling BB1): the comparison script evaluates the sign agreement on the full sample only, so its files hold no interval. The value and its number of signs are the comparison's.",
]
NOTES_AW3_ALL2 = [
    "§ Families are sums of variable-level attributions, so at the feature level the family-share distance is the variable-level value repeated (ruling BB2).",
    "Stability (panel c): the mean Spearman of a model's full-sample importances with its own bootstrap replicates; descriptive, not a ceiling on between-model agreement. Nonzero (panels d and e): the players of J to which the model gives a nonzero share.",
]
NOTE_AW3_G = "Panel g: each arcsine-link model's variable-level shares on its rows with a forecast above 0, over every variable of the problem, in the comparison file's order."
NOTE_NDVI_PARTS = [
    "‡ BARDL reads three variables (nine columns) by design and gives exactly 0 to the other ", "z_var", " of the ",
    "j_var", " variables of J (", "z_feat", " of the ", "j_feat",
    " players at the feature level). Its top-5, top-10 and top-20 sets are therefore filled by name order, the tie rule applied in code-point ascending order, at both levels, and the cells of its pairs that use those sets depend on that order. Under the other two orders tried (case-insensitive ascending, and descending), the largest move of each statistic over BARDL's eight pair-levels is: Jaccard top 5, ",
    "m_jaccard_top5", " (", "at_jaccard_top5", "); Jaccard top 10, ", "m_jaccard_top10", " (", "at_jaccard_top10",
    "); Jaccard top 20, ", "m_jaccard_top20", " (", "at_jaccard_top20", "); top-20-union Spearman, ", "m_rho20", " (",
    "at_rho20", "); RBO p = 0.9, ", "m_rbo090", " (", "at_rbo090", "); RBO p = 0.95, ", "m_rbo095", " (", "at_rbo095",
    "). For example, BARDL's Jaccard top 5 with treeroute v1 at the variable level is ", "ex_base",
    " with the tie-only `aet_total_mm` in its top 5, and ", "ex_desc", " without it (ruling BB3).",
]
NOTE_NDVI_SLOTS = {"z_var", "j_var", "z_feat", "j_feat", "m_jaccard_top5", "m_jaccard_top10", "m_jaccard_top20",
                   "m_rho20", "m_rbo090", "m_rbo095", "at_jaccard_top5", "at_jaccard_top10", "at_jaccard_top20",
                   "at_rho20", "at_rbo090", "at_rbo095", "ex_base", "ex_desc"}

CAP28 = "**Table S3.28 (post hoc; sensitivity).** treeroute v1's B1 sensitivity, nowcast: the pair (main run, B1 run) at the variable level (a) and the feature level (b). B1 explains the same 1,000 sample rows against all of each location's router fit rows at or before the cut, not only those of the same calendar month (B2), so the month and the seasonal normal can take credit. treeroute v1 only; B1 is never pooled with the main set: it enters no Kendall's W, consensus or main-text row and is compared with no rival. J is the pair's own (the players to which either run gives more than 10⁻¹² of its total), so Spearman over J, Kendall's tau-b and RBO are not read against the main pairs' values number for number. Every number is from the independent re-computation (two implementations that agree); percentile 95% intervals over the problem's 2,000 saved region draws; counts without intervals. Coral bleaching: B1 is not defined; forest loss: the identity check of Table S3.30. <!-- src: D:/treeroute/analysis/shap_v1/verify_v1/A/results.json b1.<problem>.<level>.pair_main_b1 and b1.<problem>.<level>.importance.n_nonzero; rulings BA3, BB2 -->"
LAB28A = "**a. Variable level: the pair (main run, B1 run).**"
LAB28B = "**b. Feature level: the pair (main run, B1 run).**"
HDR_B1 = "| Statistic | PM2.5 | NDVI | Burned fraction |"
NOTES28 = [
    "–: not defined, because the pair's J has fewer than 200 players (the top-20 Jaccard is given only from 200 players).",
    "§ Families are sums of variable-level attributions, so at the feature level the family-share distance is the variable-level value repeated (ruling BB2; an exception to the rule that B1's numbers follow the main comparison's choices).",
]

CAP29 = "**Table S3.29 (post hoc; sensitivity).** treeroute v1's B1 run, nowcast: family shares [95% CI] (a), top 3 and own-history share (b), and top 10 at both levels (c, d; no interval for a top-k list). Shares are of the B1 run's total mean absolute SHAP value over the pair's J. From the independent re-computation (two implementations that agree). <!-- src: D:/treeroute/analysis/shap_v1/verify_v1/A/results.json b1.<problem>.variable.families, b1.<problem>.variable.top3, b1.<problem>.variable.own_history_share, b1.<problem>.<level>.top10; rulings BA3, BB5 -->"
LAB29A = "**a. Variable level: the B1 run's family shares [95% CI].**"
LAB29B = "**b. Variable level: the B1 run's top 3 and own-history share.**"
LAB29C = "**c. Variable level: the B1 run's top 10 (share).**"
LAB29D = "**d. Feature level: the B1 run's top 10 (share).**"
NOTES29 = [
    "Under B1 the month and the seasonal normal can take credit; under B2 they are exactly 0 on these three problems. The own-history share is the own-history family's share. Each B1 player's importance, share and signed mean, with its interval, is in the re-computation's results file (verify_v1/A/results.json, key b1).",
]

CAP30 = "**Table S3.30 (post hoc; sensitivity).** treeroute v1's B1 runs: background pairs and seconds, from each run's log (a), and forest loss's identity check (b). Forest loss is annual, so its B1 background equals its main run's, and its B1 run must repeat the main run exactly. <!-- src: D:/treeroute/analysis/shap_v1/logs/tr_shap_<problem>_lead0.log (the B1 run's set-up and \"done in\" lines); D:/treeroute/analysis/shap_v1/verify_v1/A/results.json b1.defo.identity; rulings BA3 -->"
LAB30A = "**a. Background pairs and seconds of each B1 run, from its log.**"
HDR30A = "| Problem | Background pairs | Total seconds | Tree-SHAP seconds |"
LAB30B = "**b. Forest loss: the B1 run against the main run.**"
HDR30B = "| Check | Result |"
NOTES30 = [
    "Coral bleaching: B1 is not defined (its router reads a pool of other sites' survey visits), so it has no B1 run.",
    "The identity check matches rows by their sample row and players and variables by name; it is from the independent re-computation (two implementations that agree), and it held exactly, so the B1 numbers of PM2.5, NDVI and burned fraction are reported (Tables S3.28 and S3.29).",
]


# ---------------------------------------------------------------------------------------------
# 4. the tables (each returns a list of blocks; a block is a list of Line)
# ---------------------------------------------------------------------------------------------

def table_block(header_text, row_lines):
    n = ncols_of(header_text)
    return [Line(header_text, []), sep_line(n)] + row_lines


def label_suffix(p, family):
    return (" " + FAM_LABEL[family]) if family in NOVAR[p] else ""


def build_table9():
    blocks = [[const_line(CAP9)]]
    n = ncols_of(HDR9)
    rows = []
    for p in PROBLEMS:
        D = PL[p]["draws"]
        a4 = AW4[p]
        src = s_cmp(p, "AW4_main_row.json")

        def ctx(col):
            return C("9", "", p, col)

        cells = [[P_DISP[p]]]
        if p == "fire":
            cells.append(["treeroute v1 only" + SA])
            kw = a4["kendall_w"]
            c = ci2(ctx("kendall_w"), D, kw["value"], kw["ci"][0], kw["ci"][1], kw["ci"][2], src, sels_aw4("kendall_w"))
            need(text_of(c) == "undefined", "fire: Table 9 W cell is not undefined")
            cells.append(c)
            cells.append([EN])
            cells.append([EN])
            mr = R["problems"]["fire"]["main_row"]
            cells.append([name_list([x[0] for x in mr["treeroute_top3"]]) + DAG])
            cells.append([EN])
            o = mr["own_history_share_treeroute"]
            c = ci2(ctx("own_history_treeroute"), D, o["value"], o["ci_low"], o["ci_high"], o["n_finite"], S_A,
                    sels_obj("problems", "fire", "main_row", "own_history_share_treeroute"))
            cells.append(c + [DAG])
            cells.append([EN])
        else:
            cells.append([model_list(a4["models_in_main_set"])])
            kw = a4["kendall_w"]
            cells.append(ci2(ctx("kendall_w"), D, kw["value"], kw["ci"][0], kw["ci"][1], kw["ci"][2], src,
                             sels_aw4("kendall_w")))
            k = "treeroute_vs_same_link_rivals_median_spearman_top20_union"
            sp = a4[k]
            cx = ctx("spearman_top20_union_median")
            c = ci2(cx, D, sp["value"], sp["ci"][0], sp["ci"][1], sp["ci"][2], src, sels_aw4(k))
            c += [" (", N(cx, "range_min", NUM2(sp["range"][0]), src, jpath(k, "range", 0), [sp["range"][0]]), " to ",
                  N(cx, "range_max", NUM2(sp["range"][1]), src, jpath(k, "range", 1), [sp["range"][1]]), ")"]
            cells.append(c)
            k = "rbo_vs_consensus_p0.9"
            rb = a4[k]
            c = ci2(ctx("rbo_vs_consensus"), D, rb["value"], rb["ci"][0], rb["ci"][1], rb["ci"][2], src, sels_aw4(k))
            if p == "pm25":
                c.append(SB)
            cells.append(c)
            cells.append([name_list(a4["treeroute_top3"])])
            cells.append([name_list(a4["consensus_top3"])])
            k = "own_history_share_treeroute"
            o = a4[k]
            c = ci2(ctx("own_history_treeroute"), D, o["value"], o["ci"][0], o["ci"][1], o["ci"][2], src, sels_aw4(k))
            cells.append(c + [label_suffix(p, "own history")] if label_suffix(p, "own history") else c)
            k = "own_history_share_median_rival"
            o = a4[k]
            c = ci2(ctx("own_history_median_rivals"), D, o["value"], o["ci"][0], o["ci"][1], o["ci"][2], src,
                    sels_aw4(k))
            cells.append(c + [label_suffix(p, "own history")] if label_suffix(p, "own history") else c)
        rows.append(row_line(cells, n))
    blocks.append(table_block(HDR9, rows))
    blocks.append([const_line(x) for x in NOTES9])
    return blocks


def build_s318():
    blocks = [[const_line(CAP18)], [const_line(LAB18A)]]
    n = ncols_of(HDR18A)
    rows = []
    for p in PROBLEMS:
        pl = PL[p]
        trl = pl["links"]["treeroute"]
        for m in by_display(pl["models"]):
            if m == "treeroute":
                guard = "passed (the kept arm)"
            else:
                guard = "passed" if META[p][m]["guard"]["passed"] is True else "failed" + SA
            if m in pl["main_set"]:
                inm = "yes"
            else:
                reasons = []
                if pl["links"][m] != trl:
                    reasons.append("another link")
                if m in pl["declined_by_guard"]:
                    reasons.append("skill guard failed")
                need(reasons, "%s %s: not in the main set without a reason" % (p, m))
                inm = "no: " + "; ".join(reasons)
            cells = [[P_DISP[p]], [M_INL[m] + " (`" + m + "`)"], [SHAP_METHOD[m]],
                     [LINK_DISP[link_base(pl["links"][m])]], [guard], [inm]]
            rows.append(row_line(cells, n))
    blocks.append(table_block(HDR18A, rows))
    blocks.append([const_line(LAB18B)])
    blocks.append([const_line(x) for x in TAB18B])
    blocks.append([const_line(x) for x in NOTES18])
    return blocks


def build_s319():
    blocks = [[const_line(CAP19)]]
    n = ncols_of(HDR19)
    rows = []
    for p in PROBLEMS:
        man = MAN[p]
        sm = s_man(p)
        spl = s_cmp(p, "per_lead.json")

        def ctx(col):
            return C("S3.19", "", p, col)

        cells = [[P_DISP[p]]]
        cells.append([N(ctx("frame_rows"), "value", COUNT(man["frame_rows"]), sm, "frame_rows", [man["frame_rows"]])])
        nv = int(REG[p]["n_text"])
        cells.append([N(ctx("sample_rows"), "value", COUNT(nv), S_REG, "line %d: n" % REG[p]["line"], [nv])])
        cells.append([N(ctx("regions"), "value", COUNT(man["regions_in_sample"]), sm, "regions_in_sample",
                        [man["regions_in_sample"]])])
        cells.append([N(ctx("locations"), "value", COUNT(man["units_in_sample"]), sm, "units_in_sample",
                        [man["units_in_sample"]])])
        b = man["background_rows"]["0"]
        cx = ctx("background_rows")
        c = [N(cx, "min", COUNT(b["min"]), sm, jpath("background_rows", "0", "min"), [b["min"]])]
        if b["min"] != b["max"]:
            c += [EN, N(cx, "max", COUNT(b["max"]), sm, jpath("background_rows", "0", "max"), [b["max"]]),
                  " (median ", N(cx, "median", MED(b["median"]), sm, jpath("background_rows", "0", "median"),
                                 [b["median"]]), ")"]
        cells.append(c)
        tp = META[p]["treeroute"]["pairs"]
        cells.append([N(ctx("background_pairs"), "value", COUNT(tp), s_piece(p, "treeroute", "meta.json"), "pairs",
                        [tp])])
        for L in ("feature", "variable"):
            q = PL[p][L]
            cx = ctx(L)
            nz = len(q["structural_zero"])
            cells.append([N(cx, "players", COUNT(q["players"]), spl, jpath(L, "players"), [q["players"]]), " / ",
                          N(cx, "J", COUNT(q["active"]), spl, jpath(L, "active"), [q["active"]]), " / ",
                          N(cx, "structural_zeros", COUNT(nz), spl, "len(" + jpath(L, "structural_zero") + ")", [nz])])
        rows.append(row_line(cells, n))
    blocks.append(table_block(HDR19, rows))
    notes = [const_line(x) for x in NOTES19]
    for p in PROBLEMS:
        spl = s_cmp(p, "per_lead.json")
        sv = PL[p]["variable"]["structural_zero"]
        sf = PL[p]["feature"]["structural_zero"]
        frags = [P_DISP[p] + ": variable level (",
                 N(C("S3.19", "", "note", "structural_zeros:%s:variable" % p), "count", COUNT(len(sv)), spl,
                   "len(" + jpath("variable", "structural_zero") + ")", [len(sv)]),
                 ") " + name_list(sv) + "; feature level (",
                 N(C("S3.19", "", "note", "structural_zeros:%s:feature" % p), "count", COUNT(len(sf)), spl,
                   "len(" + jpath("feature", "structural_zero") + ")", [len(sf)]),
                 ") " + name_list(sf) + "."]
        notes.append(note_line(frags))
    blocks.append(notes)
    return blocks


def build_s320():
    blocks = [[const_line(CAP20)]]
    n = ncols_of(HDR20)
    rows = []
    for p in PROBLEMS:
        for m in by_display(PL[p]["models"]):
            rk = "%s:%s" % (p, m)

            def ctx(col):
                return C("S3.20", "", rk, col)

            src, rec, _ = exact_record(p, m)
            cells = [[P_DISP[p]], [M_INL[m] + (SB if (m == "rival_ridge" and p in RIDGE4) else "")]]
            rows_v, rows_s = rec["rows"]
            cells.append([N(ctx("rows_checked"), "value", COUNT(rows_v), src, rows_s, [rows_v])])
            pre_v, pre_s = rec["pre"]
            c = [N(ctx("bit_identical"), "pre", COUNT(pre_v), src, pre_s, [pre_v]), " / "]
            if rec["clipped"] is None:
                c.append(EN)
            else:
                cv, cs = rec["clipped"]
                c.append(N(ctx("bit_identical"), "clipped", COUNT(cv), src, cs, [cv]))
            cells.append(c)
            mx_v, mx_s = rec["max"]
            cells.append([N(ctx("max_abs_diff"), "value", SCI2(mx_v), src, mx_s, [mx_v])])
            if m == "treeroute":
                e8 = GATES[p]["gates"]["E8_predictions"]["values"]
                if e8["bit_identical"] is True:
                    cells.append(["bit-identical"])
                else:
                    need(e8["within_relative_tolerance"] is True and e8["rows_outside_tolerance"] == 0,
                         "%s: E8 neither bit-identical nor within D8" % p)
                    cells.append(["within the D8 tolerance" + SC + " (largest relative difference ",
                                  N(ctx("s_exact"), "max_rel", SCI2(e8["max_rel_pre"]), s_gates(p),
                                    jpath("gates", "E8_predictions", "values", "max_rel_pre"), [e8["max_rel_pre"]]),
                                  ")"])
            else:
                need(pre_v == rows_v and (rec["clipped"] is None or rec["clipped"][0] == rows_v),
                     "%s %s: S-EXACT rows not all bit-identical" % (p, m))
                cells.append(["bit-identical"])
            mt = META[p][m]
            smeta = s_piece(p, m, "meta.json")
            cx = ctx("additivity")
            cells.append([N(cx, "feature", SCI2(mt["max_abs_additivity_error"]), smeta, "max_abs_additivity_error",
                            [mt["max_abs_additivity_error"]]), " / ",
                          N(cx, "variable", SCI2(mt["max_abs_additivity_error_variable"]), smeta,
                            "max_abs_additivity_error_variable", [mt["max_abs_additivity_error_variable"]])])
            cells.append([N(ctx("s_zero_violations"), "value", COUNT(mt["structural_zero_violations"]), smeta,
                            "structural_zero_violations", [mt["structural_zero_violations"]])])
            cells.append(["all passed"])
            if m == "treeroute":
                cells.append(["passed (the kept arm)"])
            else:
                cells.append(["passed" if mt["guard"]["passed"] is True else "failed" + SD])
            rows.append(row_line(cells, n))
    blocks.append(table_block(HDR20, rows))
    frags = [NOTE20B_PARTS[0]]
    for p, mid, tail in NOTE20B_PARTS[1:]:
        e = EXACT[p]["rival_ridge"]
        src = s_piece(p, "rival_ridge", "exactness.json")
        cx = C("S3.20", "", "note", "ridge_copy:%s" % p)
        frags += [N(cx, "bit_equal_rows", COUNT(e["bit_equal_rows"]), src, "bit_equal_rows", [e["bit_equal_rows"]]),
                  mid, N(cx, "rows", COUNT(e["rows"]), src, "rows", [e["rows"]]), tail]
    blocks.append([const_line(NOTE20A), note_line(frags), const_line(NOTE20C), const_line(NOTE20D)])
    return blocks


def build_s321():
    blocks = [[const_line(CAP21)]]
    n = ncols_of(HDR21)
    rows = []
    for key, gcell, what in GATE_ROWS:
        cells = [[gcell], [what]]
        for p in PROBLEMS:
            G = GATES[p]
            res = G["result"]
            sg = s_gates(p)

            def ctx(part_row=key):
                return C("S3.21", "", part_row, p)

            if key == "kept":
                tk = {"plain": "plain answers", "corrector": "corrected answers"}
                kd = {"per_unit": "per-location router", "region": "region router", "neighbour": "neighbour router"}
                need(res["table_kind"] in tk and res["kind"] in kd and isinstance(res["weighted"], bool),
                     "%s: unknown kept arm" % p)
                need(res["link"] in ("identity", "log_c", "arcsine"), "%s: kept arm link %r" % (p, res["link"]))
                cells.append([LINK_DISP[res["link"]] + ", " + tk[res["table_kind"]] + ", "
                              + ("error-weighted" if res["weighted"] is True else "uniformly weighted") + "; "
                              + kd[res["kind"]]])
            elif key in ("E1", "E2", "E3a", "E3", "E6"):
                need(gate_get(p, key) is not None, "%s: gate %s missing" % (p, key))
                cells.append(["passed"])
            elif key == "E0":
                g = gate_get(p, "E0")
                cells.append(["passed (warning overridden)" if g["values"]["ignored"] is True else "passed"])
            elif key == "E3m":
                g = gate_get(p, "E3m")
                if g is None:
                    cells.append(["not used (no moved file)"])
                else:
                    nfl = len(g["values"]["files"])
                    cells.append(["passed (", N(ctx(), "files", COUNT(nfl), sg,
                                                "len(" + jpath("gates", "E3m_recorded_path_map", "values", "files") + ")",
                                                [nfl]), " file)" if nfl == 1 else " files)"])
            elif key == "E4":
                g = gate_get(p, "E4")
                v = g["values"]["rows"][0]
                cells.append(["passed (", N(ctx(), "rows", COUNT(v), sg, jpath("gates", "E4_donor_rows", "values", "rows", 0),
                                            [v]), " rows)"])
            elif key == "E5":
                cells.append(["differs (informational)"])
            elif key == "E5a":
                g = gate_get(p, "E5a")
                if g is None:
                    cells.append(["not applicable"])
                else:
                    v = g["values"]
                    need(v["pre_bit_equal"] == v["rows_checked"] and v["arm_bit_equal"] == v["rows_checked"],
                         "%s: E5a not bit-identical on every row" % p)
                    b = ("gates", "E5a_identity_twin", "values")
                    cells.append(["passed (", N(ctx(), "bit_equal", COUNT(v["pre_bit_equal"]), sg,
                                                jpath(*(b + ("pre_bit_equal",))), [v["pre_bit_equal"]]), " of ",
                                  N(ctx(), "rows", COUNT(v["rows_checked"]), sg, jpath(*(b + ("rows_checked",))),
                                    [v["rows_checked"]]), " rows)"])
            elif key == "E7":
                cells.append(["passed" if gate_get(p, "E7") is not None else "not applicable"])
            elif key == "E9":
                v = gate_get(p, "E9")["values"]
                b = ("gates", "E9_coefficients_reproduce_the_kernel", "values")
                if v["region_proof"] is None:
                    cells.append(["passed (all ", N(ctx(), "fits", COUNT(v["fits_captured"]), sg,
                                                    jpath(*(b + ("fits_captured",))), [v["fits_captured"]]), " fits)"])
                else:
                    rp = v["region_proof"]
                    need(rp["answers_equal"] is True and rp["eta_ours_equal"] is True and rp["eta_store_equal"] is True
                         and rp["errors"] == [], "%s: E9 region proof" % p)
                    cells.append(["passed (all ", N(ctx(), "fits", COUNT(v["fits_captured"]), sg,
                                                    jpath(*(b + ("fits_captured",))), [v["fits_captured"]]),
                                  " region fits; region proof on ",
                                  N(ctx(), "score_rows", COUNT(rp["score_rows"]), sg,
                                    jpath(*(b + ("region_proof", "score_rows"))), [rp["score_rows"]]),
                                  " score rows and ",
                                  N(ctx(), "background_rows", COUNT(rp["background_rows"]), sg,
                                    jpath(*(b + ("region_proof", "background_rows"))), [rp["background_rows"]]),
                                  " background rows)"])
            elif key == "E8":
                v = gate_get(p, "E8")["values"]
                b = ("gates", "E8_predictions", "values")
                nb = N(ctx(), "bit_equal", COUNT(v["pre_bit_equal"]), sg, jpath(*(b + ("pre_bit_equal",))),
                       [v["pre_bit_equal"]])
                nr = N(ctx(), "rows", COUNT(v["rows_checked"]), sg, jpath(*(b + ("rows_checked",))),
                       [v["rows_checked"]])
                if v["bit_identical"] is True:
                    cells.append(["bit-identical (", nb, " of ", nr, " rows)"])
                else:
                    cells.append([nb, " of ", nr, " rows bit-identical; the rest within the D8 tolerance (largest "
                                                  "relative difference ",
                                  N(ctx(), "max_rel", SCI2(v["max_rel_pre"]), sg, jpath(*(b + ("max_rel_pre",))),
                                    [v["max_rel_pre"]]), ")"])
            elif key == "E10":
                v = gate_get(p, "E10")["values"]
                b = ("gates", "E10_exported_trees", "values")
                if "rows_x_trees" in v:
                    cells.append(["passed (", N(ctx(), "rows", COUNT(v["rows_x_trees"][0]), sg,
                                                jpath(*(b + ("rows_x_trees", 0))), [v["rows_x_trees"][0]]), " rows, ",
                                  N(ctx(), "trees", COUNT(v["rows_x_trees"][1]), sg, jpath(*(b + ("rows_x_trees", 1))),
                                    [v["rows_x_trees"][1]]), " trees)"])
                else:
                    cells.append(["passed (every sampled location of the ",
                                  N(ctx(), "regions", COUNT(v["regions"]), sg, jpath(*(b + ("regions",))),
                                    [v["regions"]]), " regions)"])
            else:
                stop("unknown gate row %s" % key)
        rows.append(row_line(cells, n))
    blocks.append(table_block(HDR21, rows))
    blocks.append([const_line(x) for x in NOTES21])
    return blocks


def build_s322():
    blocks = [[const_line(CAP22)]]
    n = ncols_of(HDR22)
    rows = []

    def rivals_of(p):
        return [m for m in by_display(AW4[p]["models_in_main_set"]) if m != "treeroute"]

    spec_rows = ["link", "main", "cross", "declined", "kendall_w", "spearman_per_rival", "spearman_median",
                 "spearman_range", "rbo_vs_consensus", "top3", "consensus", "own_history_treeroute",
                 "own_history_per_rival", "own_history_median_rivals"]
    first = {"link": "Link of the main set", "main": "Main set", "cross": "Rivals in another link",
             "declined": "Rivals declined by their skill guard", "kendall_w": "Kendall's W of the main set [95% CI]",
             "spearman_per_rival": "Spearman of treeroute v1 with each same-link rival",
             "spearman_median": "Median of those [95% CI]", "spearman_range": "Range (lowest to highest)",
             "rbo_vs_consensus": "RBO with the rivals' consensus, p = 0.9 [95% CI]",
             "top3": "treeroute v1's top 3", "consensus": "Consensus top 3",
             "own_history_treeroute": "Own-history share, treeroute v1 [95% CI]",
             "own_history_per_rival": "Own-history share of each same-link rival",
             "own_history_median_rivals": "Own-history share, median of the rivalsᶜ [95% CI]"}
    for rk in spec_rows:
        cells = [[first[rk]]]
        for p in PROBLEMS:
            a4 = AW4[p]
            D = PL[p]["draws"]
            src = s_cmp(p, "AW4_main_row.json")
            cx = C("S3.22", "", rk, p)
            fire = (p == "fire")
            lab = label_suffix(p, "own history")
            if rk == "link":
                cells.append([LINK_DISP[link_base(a4["reference_link"])]])
            elif rk == "main":
                cells.append(["treeroute v1 only" + SA] if fire else [model_list(a4["models_in_main_set"])])
            elif rk == "cross":
                cells.append([model_list(a4["cross_link_models"])])
            elif rk == "declined":
                cells.append([model_list(a4["declined_models"])])
            elif rk == "kendall_w":
                kw = a4["kendall_w"]
                c = ci2(cx, D, kw["value"], kw["ci"][0], kw["ci"][1], kw["ci"][2], src, sels_aw4("kendall_w"))
                if fire:
                    need(text_of(c) == "undefined", "fire: S3.22 W cell is not undefined")
                cells.append(c)
            elif fire and rk in ("spearman_per_rival", "spearman_median", "spearman_range", "rbo_vs_consensus",
                                 "consensus", "own_history_per_rival", "own_history_median_rivals"):
                cells.append([EN])
            elif rk == "spearman_per_rival":
                c = []
                sp_src = s_cmp(p, "pairs.parquet")
                for i, m in enumerate(rivals_of(p)):
                    a, b = sorted([m, "treeroute"])
                    r = PAIRS[p][("variable", a, b, "spearman_top20_union")]
                    keys = [("level", "variable"), ("model_a", a), ("model_b", b), ("statistic", "spearman_top20_union")]
                    if i > 0:
                        c.append("; ")
                    c += [M_INL[m] + " ", N(C("S3.22", "", rk, p), m, NUM2(r["value"]), sp_src, psel(keys, "value"),
                                            [r["value"]])]
                cells.append(c)
            elif rk == "spearman_median":
                k = "treeroute_vs_same_link_rivals_median_spearman_top20_union"
                sp = a4[k]
                cells.append(ci2(cx, D, sp["value"], sp["ci"][0], sp["ci"][1], sp["ci"][2], src, sels_aw4(k)))
            elif rk == "spearman_range":
                k = "treeroute_vs_same_link_rivals_median_spearman_top20_union"
                sp = a4[k]
                cells.append([N(cx, "min", NUM2(sp["range"][0]), src, jpath(k, "range", 0), [sp["range"][0]]), " to ",
                              N(cx, "max", NUM2(sp["range"][1]), src, jpath(k, "range", 1), [sp["range"][1]])])
            elif rk == "rbo_vs_consensus":
                k = "rbo_vs_consensus_p0.9"
                rb = a4[k]
                c = ci2(cx, D, rb["value"], rb["ci"][0], rb["ci"][1], rb["ci"][2], src, sels_aw4(k))
                if p == "pm25":
                    c.append(SB)
                cells.append(c)
            elif rk == "top3":
                if fire:
                    cells.append([name_list([x[0] for x in R["problems"]["fire"]["main_row"]["treeroute_top3"]]) + DAG])
                else:
                    cells.append([name_list(a4["treeroute_top3"])])
            elif rk == "consensus":
                cells.append([name_list(a4["consensus_top3"])])
            elif rk == "own_history_treeroute":
                if fire:
                    o = R["problems"]["fire"]["main_row"]["own_history_share_treeroute"]
                    c = ci2(cx, D, o["value"], o["ci_low"], o["ci_high"], o["n_finite"], S_A,
                            sels_obj("problems", "fire", "main_row", "own_history_share_treeroute"))
                    cells.append(c + [DAG])
                else:
                    k = "own_history_share_treeroute"
                    o = a4[k]
                    c = ci2(cx, D, o["value"], o["ci"][0], o["ci"][1], o["ci"][2], src, sels_aw4(k))
                    cells.append(c + ([lab] if lab else []))
            elif rk == "own_history_per_rival":
                c = []
                fsrc = s_cmp(p, "families.parquet")
                for i, m in enumerate(rivals_of(p)):
                    sh = FAM[p][(m, "own history")]
                    if i > 0:
                        c.append("; ")
                    c += [M_INL[m] + " ", N(cx, m, NUM2(sh), fsrc,
                                            psel([("model", m), ("family", "own history")], "share"), [sh])]
                cells.append(c + ([lab] if lab else []))
            elif rk == "own_history_median_rivals":
                k = "own_history_share_median_rival"
                o = a4[k]
                c = ci2(cx, D, o["value"], o["ci"][0], o["ci"][1], o["ci"][2], src, sels_aw4(k))
                cells.append(c + ([lab] if lab else []))
            else:
                stop("unknown S3.22 row %s" % rk)
        rows.append(row_line(cells, n))
    blocks.append(table_block(HDR22, rows))
    blocks.append([const_line(x) for x in NOTES22])
    return blocks


def pair_link_text(label):
    M = "; raw model, declined by its guard: "
    if M in label:
        before, after = label.split(M, 1)
        names = after.split(", ")
        for x in names:
            need(x in M_INL, "label names an unknown model %r" % (x,))
        return before + M + ", ".join(M_INL[x] for x in names)
    return label


def build_aw3(p):
    tid = AW3_ID[p]
    pl = PL[p]
    D = pl["draws"]
    ms = by_display(pl["models"])
    nn = tid.split(".")[1]
    cap = CAP_AW3.replace("{nn}", nn).replace("{Problem}", P_DISP[p]).replace("{p}", p)
    cap = cap.replace("{g_clause}", G_CLAUSE if p in ("fire", "coral") else "")
    cap = cap.replace("{extra_src}", EXTRA_SRC_NDVI if p == "ndvi" else "")
    cap = cap.replace("{extra_rulings}", {"ndvi": ", BB3", "defo": ", BB4", "coral": ", BB4"}.get(p, ""))
    need("{" not in cap and "}" not in cap, "%s: caption placeholder left" % p)
    blocks = [[const_line(cap)]]
    sp_src = s_cmp(p, "pairs.parquet")
    pl_src = s_cmp(p, "per_lead.json")
    # panels a and b
    for L, lab, panel in (("variable", LAB_A, "a"), ("feature", LAB_B, "b")):
        with_j20 = any(k[0] == L and k[3] == "jaccard_top20" for k in PAIRS[p])
        need(not (with_j20 and L == "variable"), "%s: variable-level jaccard_top20 (no layout)" % p)
        hdr = list(HDR_A)
        if L == "feature":
            hdr[10] = "Family-share distance (TV)" + SECT
            if with_j20:
                hdr.insert(7, "Jaccard top 20")
        hl = header_line(hdr)
        n = len(hdr)
        stats = ["spearman", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10"]
        if with_j20:
            stats.append("jaccard_top20")
        stats += ["rbo_p0.9", "rbo_p0.95", "tvd"]
        rows = []
        for e, l in display_pairs(pl["models"]):
            a, b = sorted([e, l])
            key = a + "|" + b
            ptxt = pair_text(e, l) + (DDAG if (p == "ndvi" and "rival_bardl_h1" in (e, l)) else "")
            labels = set(r["pair_label"] for r in PAIRS_ROWS[p] if r["level"] == L and r["model_a"] == a
                         and r["model_b"] == b)
            need(len(labels) == 1, "%s %s %s: pair label" % (p, L, key))
            cells = [[ptxt], [pair_link_text(labels.pop())]]
            for s in stats:
                r = PAIRS[p][(L, a, b, s)]
                keys = [("level", L), ("model_a", a), ("model_b", b), ("statistic", s)]
                cells.append(ci2(C(tid, panel, key, s), D, r["value"], r["ci_low"], r["ci_high"],
                                 r["finite_replicates"], sp_src, sels_pairs(keys)))
            r = PAIRS[p][("variable", a, b, "tvd_family")]
            keys = [("level", "variable"), ("model_a", a), ("model_b", b), ("statistic", "tvd_family")]
            cells.append(ci2(C(tid, panel, key, "tvd_family"), D, r["value"], r["ci_low"], r["ci_high"],
                             r["finite_replicates"], sp_src, sels_pairs(keys)))
            r = PAIRS[p][(L, a, b, "sign_agreement_top10")]
            keys = [("level", L), ("model_a", a), ("model_b", b), ("statistic", "sign_agreement_top10")]
            sa = R["problems"][p]["levels"][L]["pairs"][key]["sign_agreement"]
            ap = ("problems", p, "levels", L, "pairs", key, "sign_agreement")
            cells.append(sign_cell(C(tid, panel, key, "sign_agreement_top10"), D, r["value"], r["signs_compared"],
                                   sa["ci_low"], sa["ci_high"], sa["n_finite"], sp_src, psel(keys, "value"),
                                   psel(keys, "signs_compared"), S_A, jpath(*(ap + ("ci_low",))),
                                   jpath(*(ap + ("ci_high",))), jpath(*(ap + ("n_finite",)))))
            rows.append(row_line(cells, n))
        blocks.append([const_line(lab)])
        blocks.append([hl, sep_line(n)] + rows)
    # panel c
    rows = []
    n = ncols_of(HDR_C)
    for first, key, rk in (("Kendall's W of the main set [95% CI]", "kendall_w_main_set", "kendall_w"),
                           ("Mean pairwise Spearman of the main set [95% CI]", "mean_pairwise_spearman_main_set",
                            "mean_pairwise_spearman")):
        cells = [[first]]
        for L in ("variable", "feature"):
            o = pl[L][key]
            c = ci2(C(tid, "c", rk, L), D, o["value"], o["ci"][0], o["ci"][1], o["finite_replicates"], pl_src,
                    sels_pl(L, key))
            if p == "fire":
                need(is_undef(o["value"]) and o["finite_replicates"] == 0 and text_of(c) == "undefined",
                     "fire: panel c %s is not undefined" % key)
                c.append(SA)
            cells.append(c)
        rows.append(row_line(cells, n))
    for m in ms:
        cells = [["Stability under region resampling: " + M_INL[m]]]
        for L in ("variable", "feature"):
            v = pl[L]["stability_under_region_resampling"][m]
            cells.append([N(C(tid, "c", "stability:" + m, L), "value", NUM2(v), pl_src,
                            jpath(L, "stability_under_region_resampling", m), [v])])
        rows.append(row_line(cells, n))
    blocks.append([const_line(LAB_C)])
    blocks.append(table_block(HDR_C, rows))
    # panels d and e
    imp_src = s_cmp(p, "importance.parquet")
    for L, lab, panel, last in (("variable", LAB_D, "d", "Nonzero variables"),
                                ("feature", LAB_E, "e", "Nonzero players")):
        hdr = ["Rank"] + [M_HDR[m] + (DDAG if (p == "ndvi" and m == "rival_bardl_h1") else "") for m in ms]
        n = len(hdr)
        rows = []
        for k in range(1, 11):
            cells = [[str(k)]]
            for m in ms:
                rk = RANK[p][L][m]
                need(len(rk) >= k, "%s %s %s: fewer than %d ranked players" % (p, L, m, k))
                r = rk[k - 1]
                cells.append(top_frags(C(tid, panel, "rank_%d" % k, m), r["player"], r["share"], imp_src,
                                       psel([("level", L), ("model", m), ("player", r["player"])], "share")))
            rows.append(row_line(cells, n))
        cells = [[last]]
        for m in ms:
            v = pl[L]["nonzero_players"][m]
            cells.append([N(C(tid, panel, "nonzero", m), "count", COUNT(v), pl_src, jpath(L, "nonzero_players", m), [v])])
        rows.append(row_line(cells, n))
        blocks.append([const_line(lab)])
        blocks.append([header_line(hdr), sep_line(n)] + rows)
    # panel f
    fam_src = s_cmp(p, "families.parquet")
    hdr = ["Family"] + [M_HDR[m] for m in ms]
    n = len(hdr)
    rows = []
    for f in FAMS:
        cells = [[FAM_ROW[f]]]
        for m in ms:
            sh = FAM[p][(m, f)]
            c = [N(C(tid, "f", f, m), "share", PCT1(sh), fam_src, psel([("model", m), ("family", f)], "share"), [sh])]
            if f in NOVAR[p]:
                c.append(" " + FAM_LABEL[f])
            cells.append(c)
        rows.append(row_line(cells, n))
    blocks.append([const_line(LAB_F)])
    blocks.append([header_line(hdr), sep_line(n)] + rows)
    # panel g
    nzf = pl["nonzero_forecast_rows"]
    if p in ("fire", "coral"):
        need(len(nzf) > 0, "%s: no nonzero_forecast_rows" % p)
        gm = by_display(list(nzf.keys()))
        for m in gm:
            need(link_base(pl["links"][m]) == "arcsine", "%s %s: panel g model is not arcsine-link" % (p, m))
        hdr = ["Rank"] + [M_HDR[m] for m in gm]
        n = len(hdr)
        rows = []
        for k in range(1, 11):
            cells = [[str(k)]]
            for m in gm:
                t10 = nzf[m]["top10"]
                need(len(t10) == 10, "%s %s: nonzero top10 length" % (p, m))
                name, share = t10[k - 1]
                cells.append(top_frags(C(tid, "g", "rank_%d" % k, m), name, share, pl_src,
                                       jpath("nonzero_forecast_rows", m, "top10", k - 1, 1)))
            rows.append(row_line(cells, n))
        cells = [["Rows with a forecast above 0"]]
        for m in gm:
            v = nzf[m]["rows"]
            cells.append([N(C(tid, "g", "rows", m), "count", COUNT(v), pl_src, jpath("nonzero_forecast_rows", m, "rows"),
                            [v])])
        rows.append(row_line(cells, n))
        blocks.append([const_line(LAB_G)])
        blocks.append([header_line(hdr), sep_line(n)] + rows)
    else:
        need(len(nzf) == 0, "%s: unexpected nonzero_forecast_rows" % p)
    # notes
    notes = []
    if p == "fire":
        notes.append(const_line(NOTE_AW3_FIRE))
    notes += [const_line(x) for x in NOTES_AW3_ALL1]
    if p == "ndvi":
        notes.append(ndvi_note())
    notes += [const_line(x) for x in NOTES_AW3_ALL2]
    if p in ("fire", "coral"):
        notes.append(const_line(NOTE_AW3_G))
    blocks.append(notes)
    return blocks


def ndvi_note():
    pl = PL["ndvi"]
    spl = s_cmp("ndvi", "per_lead.json")
    val = {}

    def cx(col):
        return C("S3.24", "", "note", col)

    for L, zk, jk in (("variable", "z_var", "j_var"), ("feature", "z_feat", "j_feat")):
        act = pl[L]["active"]
        nz = pl[L]["nonzero_players"]["rival_bardl_h1"]
        val[zk] = N(cx(zk), "number", COUNT(act - nz), spl,
                    jpath(L, "active") + " - " + jpath(L, "nonzero_players", "rival_bardl_h1"), [act, nz])
        val[jk] = N(cx(jk), "number", COUNT(act), spl, jpath(L, "active"), [act])
    for s in MAX_STATS:
        mx = MAXI[s]
        f = float(mx["spread"])
        val["m_" + s] = N(cx("m_" + s), "number", NUM2(f), S_MAX, "line %d: spread" % mx["line"], [f])
        a, b = mx["pair"].split("|")
        e, l = by_display([a, b])
        val["at_" + s] = ("variable level" if mx["level"] == "variable" else "feature level") + ", " + pair_text(e, l)
    j5 = MAXI["jaccard_top5"]
    f1 = float(j5["v1"])
    f3 = float(j5["v3"])
    val["ex_base"] = N(cx("ex_base"), "number", NUM2(f1), S_MAX, "line %d: value 1" % j5["line"], [f1])
    val["ex_desc"] = N(cx("ex_desc"), "number", NUM2(f3), S_MAX, "line %d: value 3" % j5["line"], [f3])
    frags = []
    for part in NOTE_NDVI_PARTS:
        if part in NOTE_NDVI_SLOTS:
            frags.append(val[part])
        else:
            frags.append(part)
    return note_line(frags)


def build_s328():
    blocks = [[const_line(CAP28)]]
    n = ncols_of(HDR_B1)
    b1 = R["b1"]
    for L, lab, panel in (("variable", LAB28A, "a"), ("feature", LAB28B, "b")):
        rows = []
        spec = [("n_J", "Variables in the pair's J" if L == "variable" else "Players in the pair's J"),
                ("n_nonzero", "Nonzero in the B1 run"), ("spearman_J", "Spearman over J"),
                ("spearman_top20_union", "Spearman, top-20 union"), ("kendall_tau_b", "Kendall's tau-b"),
                ("jaccard_top5", "Jaccard top 5"), ("jaccard_top10", "Jaccard top 10"),
                ("jaccard_top20", "Jaccard top 20"), ("rbo_p090", "RBO, p = 0.9"), ("rbo_p095", "RBO, p = 0.95"),
                ("tv_shares", "Share distance (TV)"),
                ("tv_family_shares", "Family-share distance (TV)" + ("" if L == "variable" else SECT)),
                ("sign_agreement", "Sign agreement, top-10 union"),
                ("sign_counts", "Signs determined in both runs / of those, agreeing")]
        for rk, first in spec:
            if rk == "jaccard_top20":
                objs = [b1[p][L]["pair_main_b1"]["jaccard_top20"] for p in B1P]
                for o in objs:
                    need(o is None or isinstance(o, dict), "B1 jaccard_top20 neither null nor an object")
                if not any(isinstance(o, dict) for o in objs):
                    continue
            cells = [[first]]
            for p in B1P:
                D = PL[p]["draws"]
                Bq = b1[p][L]
                Q = Bq["pair_main_b1"]
                cx = C("S3.28", panel, rk, p)
                qpath = ("b1", p, L, "pair_main_b1")
                if rk == "n_J":
                    v = Q["n_J"]["value"]
                    cells.append([N(cx, "count", COUNT(v), S_A, jpath(*(qpath + ("n_J", "value"))), [v])])
                elif rk == "n_nonzero":
                    v = Bq["importance"]["n_nonzero"]["value"]
                    cells.append([N(cx, "count", COUNT(v), S_A, jpath("b1", p, L, "importance", "n_nonzero", "value"),
                                    [v])])
                elif rk == "jaccard_top20":
                    o = Q["jaccard_top20"]
                    if o is None:
                        cells.append([EN])
                    else:
                        cells.append(ci2(cx, D, o["value"], o["ci_low"], o["ci_high"], o["n_finite"], S_A,
                                         sels_obj(*(qpath + ("jaccard_top20",)))))
                elif rk == "tv_family_shares":
                    vp = ("b1", p, "variable", "pair_main_b1", "tv_family_shares")
                    o = b1[p]["variable"]["pair_main_b1"]["tv_family_shares"]
                    need(isinstance(o, dict), "B1 %s: variable tv_family_shares missing" % p)
                    cells.append(ci2(cx, D, o["value"], o["ci_low"], o["ci_high"], o["n_finite"], S_A, sels_obj(*vp)))
                elif rk == "sign_counts":
                    d = Q["sign_n_determined"]["value"]
                    g = Q["sign_n_agree"]["value"]
                    cells.append([N(cx, "determined", COUNT(d), S_A, jpath(*(qpath + ("sign_n_determined", "value"))),
                                    [d]), " / ",
                                  N(cx, "agree", COUNT(g), S_A, jpath(*(qpath + ("sign_n_agree", "value"))), [g])])
                else:
                    o = Q[rk]
                    need(isinstance(o, dict), "B1 %s %s %s: not an object" % (p, L, rk))
                    cells.append(ci2(cx, D, o["value"], o["ci_low"], o["ci_high"], o["n_finite"], S_A,
                                     sels_obj(*(qpath + (rk,)))))
            rows.append(row_line(cells, n))
        blocks.append([const_line(lab)])
        blocks.append(table_block(HDR_B1, rows))
    blocks.append([const_line(x) for x in NOTES28])
    return blocks


def build_s329():
    blocks = [[const_line(CAP29)]]
    b1 = R["b1"]
    # a
    hdr = "| Family | PM2.5 | NDVI | Burned fraction |"
    n = ncols_of(hdr)
    rows = []
    for f in FAMS:
        fk = FAM_B1KEY[f]
        cells = [[FAM_ROW[f]]]
        for p in B1P:
            need(f not in NOVAR[p], "B1 %s: family %s has no variable" % (p, f))
            o = b1[p]["variable"]["families"][fk]
            cells.append(cip(C("S3.29", "a", fk, p), PL[p]["draws"], o["value"], o["ci_low"], o["ci_high"],
                             o["n_finite"], S_A, sels_obj("b1", p, "variable", "families", fk)))
        rows.append(row_line(cells, n))
    blocks.append([const_line(LAB29A)])
    blocks.append(table_block(hdr, rows))
    # b
    hdr = "| Quantity | PM2.5 | NDVI | Burned fraction |"
    n = ncols_of(hdr)
    rows = []
    cells = [["Top 3 (share)"]]
    for p in B1P:
        t3 = b1[p]["variable"]["top3"]
        need(len(t3) == 3, "B1 %s: top3 length" % p)
        c = []
        for i, (name, share) in enumerate(t3):
            if i > 0:
                c.append(", ")
            fr = top_frags(C("S3.29", "b", "top3", p), name, share, S_A, jpath("b1", p, "variable", "top3", i, 1))
            fr[1].part = "share_%d" % (i + 1)
            c += fr
        cells.append(c)
    rows.append(row_line(cells, n))
    cells = [["Own-history share [95% CI]"]]
    for p in B1P:
        o = b1[p]["variable"]["own_history_share"]
        cells.append(ci2(C("S3.29", "b", "own_history_share", p), PL[p]["draws"], o["value"], o["ci_low"], o["ci_high"],
                         o["n_finite"], S_A, sels_obj("b1", p, "variable", "own_history_share")))
    rows.append(row_line(cells, n))
    blocks.append([const_line(LAB29B)])
    blocks.append(table_block(hdr, rows))
    # c, d
    hdr = "| Rank | PM2.5 | NDVI | Burned fraction |"
    n = ncols_of(hdr)
    for L, lab, panel in (("variable", LAB29C, "c"), ("feature", LAB29D, "d")):
        rows = []
        for k in range(1, 11):
            cells = [[str(k)]]
            for p in B1P:
                t10 = b1[p][L]["top10"]
                need(len(t10) == 10, "B1 %s %s: top10 length" % (p, L))
                name, share = t10[k - 1]
                cells.append(top_frags(C("S3.29", panel, "rank_%d" % k, p), name, share, S_A,
                                       jpath("b1", p, L, "top10", k - 1, 1)))
            rows.append(row_line(cells, n))
        blocks.append([const_line(lab)])
        blocks.append(table_block(hdr, rows))
    blocks.append([const_line(x) for x in NOTES29])
    return blocks


def build_s330():
    blocks = [[const_line(CAP30)]]
    n = ncols_of(HDR30A)
    rows = []
    for p in B1LOGP:
        lg = LOGB[p]
        sl = s_log(p)
        pv = int(lg["pairs_text"])
        tv = float(lg["total_text"])
        rv = float(lg["tree_text"])
        cells = [[P_DISP[p]],
                 [N(C("S3.30", "a", p, "pairs"), "value", COUNT(pv), sl, "line %d: background pairs" % lg["setup_line"],
                    [pv])],
                 [N(C("S3.30", "a", p, "total_seconds"), "value", SECS(tv), sl, "line %d: total seconds" % lg["done_line"],
                    [tv])],
                 [N(C("S3.30", "a", p, "tree_shap_seconds"), "value", SECS(rv), sl,
                    "line %d: tree SHAP seconds" % lg["done_line"], [rv])]]
        rows.append(row_line(cells, n))
    blocks.append([const_line(LAB30A)])
    blocks.append(table_block(HDR30A, rows))
    I = R["b1"]["defo"]["identity"]
    ip = ("b1", "defo", "identity")
    n = ncols_of(HDR30B)
    rows = []

    def yn(x):
        need(isinstance(x, bool), "identity flag is not a bool")
        return "yes" if x else "no"

    rows.append(row_line([["Largest absolute difference of the SHAP values, feature level (every row and player)"],
                          [N(C("S3.30", "b", "max_abs_diff_phi", "result"), "value", SCI2(I["max_abs_diff_phi"]), S_A,
                             jpath(*(ip + ("max_abs_diff_phi",))), [I["max_abs_diff_phi"]])]], n))
    rows.append(row_line([["Largest absolute difference of the SHAP values, variable level (every row and variable)"],
                          [N(C("S3.30", "b", "max_abs_diff_phiv", "result"), "value", SCI2(I["max_abs_diff_phiv"]), S_A,
                             jpath(*(ip + ("max_abs_diff_phiv",))), [I["max_abs_diff_phiv"]])]], n))
    for rk, first, km, kb in (("rows", "Rows, main run / B1 run", "n_rows_main", "n_rows_b1"),
                              ("players", "Players, main run / B1 run", "n_players_main", "n_players_b1"),
                              ("variables", "Variables, main run / B1 run", "n_variables_main", "n_variables_b1")):
        cx = C("S3.30", "b", rk, "result")
        rows.append(row_line([[first], [N(cx, "main", COUNT(I[km]), S_A, jpath(*(ip + (km,))), [I[km]]), " / ",
                                        N(cx, "b1", COUNT(I[kb]), S_A, jpath(*(ip + (kb,))), [I[kb]])]], n))
    rows.append(row_line([["Same rows / players / variables"],
                          [" / ".join([yn(I["same_rows"]), yn(I["same_players"]), yn(I["same_variables"])])]], n))
    blocks.append([const_line(LAB30B)])
    blocks.append(table_block(HDR30B, rows))
    blocks.append([const_line(x) for x in NOTES30])
    return blocks


# ---------------------------------------------------------------------------------------------
# 5. assembly and output
# ---------------------------------------------------------------------------------------------

def assemble():
    blocks = [[const_line(HEADER_COMMENT)], [const_line(HEADING1)]]
    blocks += build_table9()
    blocks.append([const_line(HEADING2)])
    blocks += build_s318()
    blocks += build_s319()
    blocks += build_s320()
    blocks += build_s321()
    blocks += build_s322()
    for p in PROBLEMS:
        blocks += build_aw3(p)
    blocks.append([const_line(HEADING3)])
    blocks += build_s328()
    blocks += build_s329()
    blocks += build_s330()
    lines = []
    for i, b in enumerate(blocks):
        need(len(b) > 0, "empty block")
        if i > 0:
            lines.append(Line("", []))
        lines += b
    entries = []
    texts = []
    for ln, line in enumerate(lines, 1):
        t = line.text
        need("\t" not in t and t == t.rstrip(" "), "tab or trailing space on line %d" % ln)
        texts.append(t)
        for num, cell in line.nums:
            need(num.printed in cell and cell in t, "entry not in its cell or line, line %d" % ln)
            entries.append({"line": ln, "table": num.table, "panel": num.panel, "row": num.row,
                            "column": num.column, "part": num.part, "printed": num.printed, "cell": cell,
                            "source": num.source, "selector": num.selector, "stored": num.stored})
    need(texts[-1] != "", "blank last line")
    md = "\n".join(texts) + "\n"
    doc = {"tables_file": "tables.md", "spec": "OUT\\spec\\TABLE_SPEC.md", "entries": entries}
    js = json.dumps(doc, ensure_ascii=False, indent=1, allow_nan=False) + "\n"
    return md, js, len(texts), len(entries)


def main():
    try:
        self_test()
        load_all()
        nck = run_checks()
        md, js, nlines, nent = assemble()
    except Stop as e:
        print("STOP: " + str(e))
        print("Neither file was written.")
        return 1
    p_md = os.path.join(OUT_X, "tables.md")
    p_js = os.path.join(OUT_X, "cells.json")
    with open(p_md, "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    with open(p_js, "w", encoding="utf-8", newline="\n") as f:
        f.write(js)
    with open(p_md, "rb") as f:
        raw = f.read()
    print("checks passed: %d" % nck)
    print("tables.md: %d lines, %d bytes, sha256 %s" % (nlines, len(raw), hashlib.sha256(raw).hexdigest()))
    with open(p_js, "rb") as f:
        rawj = f.read()
    print("cells.json: %d entries, %d bytes, sha256 %s" % (nent, len(rawj), hashlib.sha256(rawj).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
