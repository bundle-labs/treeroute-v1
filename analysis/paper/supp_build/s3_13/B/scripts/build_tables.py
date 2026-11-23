# Builder B of the S3.13 tables: main-text Table 9 and Supplement Tables S3.18 to S3.30.
#
# Written from OUT\spec\TABLE_SPEC.md only. Reads the spec (for its exact texts, which are copied from its fenced
# blocks or checked against it) and the data files of the spec's section 1; runs the checks of section 3 (any failure
# stops before a file is written); writes OUT\B\tables.md and OUT\B\cells.json and nothing else.
# Every printed number is formatted once from a stored value (spec 2.5).
# Version 2 of the spec (2026-11-17, its section 9): the changed texts of fenced blocks are read from the spec as
# before; the three changed texts outside fenced blocks (E10's "What it checks", the S3.22 row label of
# `cross_link_models`, the two values of `{shares_sentence}`) are taken from the spec's lines by spec_match(); panel
# b of S3.18 has 10 lines and its note group 3; panel f's family shares use part `share` (G1); the text sources are
# read as section 1's text formats say (G2). The version-1 outputs are kept as OUT\B\tables_v1.md and cells_v1.json.
# Version 3 of the spec (2026-11-17, its section 10): the changed texts of fenced blocks are read from the spec as
# before (the panel b label and the notes of S3.18, blocks 14 and 16, are found by their new first lines); the changed
# texts outside fenced blocks are taken from the spec's lines by spec_match(): the two values of `{shares_sentence}`
# (its bullet's first line now names version 3), `{extra_src}`, treeroute's skill-guard cell of S3.18 a and of S3.20,
# the random forest's "Model and SHAP method", the first row of S3.21 and the "What it checks" of E3a, E3m, E3 and E6
# (E10 and the S3.22 row label as in version 2), and M and P of the Link cell rule of 4.7: S3.25's Link cells print P
# where the source label holds M, and check 3.3 still tests the source label with M. The version-2 outputs are kept
# as OUT\B\tables_v2.md and cells_v2.json.
# Version 4 of the spec (2026-11-17, its section 11): the changed texts of fenced blocks are read from the spec as
# before (the panel b table of S3.18, block 15, is found by the new start of its first line, which is taken from the
# spec's section 11); the changed texts outside fenced blocks are taken from the spec's lines: the "What it checks" of
# E5ᵃ and E8 from their rows of 4.5 (as E3a, E3m and E3 already were; their texts changed too), the plain arm's
# answer type from the rule of the `Adopted arm` row, and the S3.22 row label as before. The version-3 outputs are
# kept as OUT\B\tables_v3.md and cells_v3.json.
# Version 5 of the spec (2026-11-17, its section 12): no change of code is needed. The changed texts of fenced blocks
# (the header comment, Table 9's caption and the notes of S3.19 and S3.21: the spec's blocks 4, 8, 19 and 26, here
# BLOCKS[3], [7], [18] and [25], whose first lines keep the starts used below) are read from the spec as before, and
# the "What it checks" of E3m (V5-4) and E5ᵃ (V5-3) from their rows of 4.5 by s321_what(), as in versions 3 and 4.
# The version-4 outputs are kept as OUT\B\tables_v4.md and cells_v4.json.
# Run as: py -3.9 -I -B <this file>
import sys
import os
import re
import json
import math
import hashlib
import itertools

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_B = os.path.dirname(HERE)
OUT_DIR = os.path.dirname(OUT_B)
SPEC_FILE = os.path.join(OUT_DIR, "spec", "TABLE_SPEC.md")
TABLES_MD = os.path.join(OUT_B, "tables.md")
CELLS_JSON = os.path.join(OUT_B, "cells.json")

SHAP = "D:\\treeroute\\analysis\\shap_v1"
VDIR = SHAP + "\\verify_v1"


class Stop(Exception):
    pass


def stop(msg):
    raise Stop(msg)


def need(cond, msg):
    if not cond:
        raise Stop(msg)


# ----------------------------------------------------------------------------------------------------------------------
# Paths (named in outputs by their short form, spec 0 and 5)

def p_compare(p, f):
    return SHAP + "\\out\\" + p + "\\lead_0\\compare\\" + f


def p_model(p, m, f):
    return SHAP + "\\out\\" + p + "\\lead_0\\" + m + "\\" + f


def p_gates(p):
    return SHAP + "\\rebuild\\" + p + "\\lead_0\\gates.json"


def p_manifest(p):
    return SHAP + "\\sample\\" + p + "\\sample_manifest.json"


def p_log(p):
    return SHAP + "\\logs\\tr_shap_" + p + "_lead0.log"


P_REGISTER = SHAP + "\\SAMPLE_REGISTER.txt"
P_A = VDIR + "\\A\\results.json"
P_MAXIMA = VDIR + "\\_lead\\outputs\\bardl_maxima.txt"


def short(path):
    if path.startswith(VDIR + "\\"):
        return "V\\" + path[len(VDIR) + 1:]
    if path.startswith(SHAP + "\\"):
        return "SHAP\\" + path[len(SHAP) + 1:]
    stop("a path outside SHAP: " + path)


# ----------------------------------------------------------------------------------------------------------------------
# Number formats (spec 2.5): one formatting call per printed number

MINUS = "\u2212"
NDASH = "\u2013"
TIMES = "\u00d7"
DAGGER = "\u2020"
DDAGGER = "\u2021"
SECTION = "\u00a7"
SUP_A, SUP_B, SUP_C, SUP_D = "\u1d43", "\u1d47", "\u1d9c", "\u1d48"
SUPMAP = {"0": "\u2070", "1": "\u00b9", "2": "\u00b2", "3": "\u00b3", "4": "\u2074", "5": "\u2075", "6": "\u2076",
          "7": "\u2077", "8": "\u2078", "9": "\u2079", "-": "\u207b"}


def isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def finite(x):
    return isnum(x) and math.isfinite(x)


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
    need(not isinstance(n, bool), "COUNT of a bool: %r" % (n,))
    if isinstance(n, int):
        return format(n, ",")
    need(isinstance(n, float) and n.is_integer(), "COUNT of %r" % (n,))
    return format(int(n), ",")


def SCI2(x):
    need(finite(x), "SCI2 of %r" % (x,))
    if x == 0.0:
        return "0"
    m, e = format(abs(x), ".1e").split("e")
    sup = "".join(SUPMAP[ch] for ch in str(int(e)))
    return (MINUS if x < 0 else "") + m + " " + TIMES + " 10" + sup


def SECS(x):
    need(finite(x), "SECS of %r" % (x,))
    return format(x, ",.1f")


def MED(x):
    need(finite(x), "MED of %r" % (x,))
    if float(x).is_integer():
        return COUNT(x)
    return format(x, ".1f")


def self_test():
    vec = [
        (NUM2(0.625), "0.62"), (NUM2(0.875), "0.88"), (NUM2(-0.004), MINUS + "0.00"), (NUM2(-0.0), "0.00"),
        (NUM2(-0.1214), MINUS + "0.12"), (PCT1(0.0625), "6.2%"), (PCT1(0.0002), "<0.1%"), (PCT1(0.0), "0.0%"),
        (PCT1(0.14169933950641164), "14.2%"), (COUNT(1140), "1,140"), (COUNT(10.0), "10"),
        (SCI2(9.237055564881302e-14), "9.2 " + TIMES + " 10\u207b\u00b9\u2074"),
        (SCI2(2.220446049250313e-16), "2.2 " + TIMES + " 10\u207b\u00b9\u2076"), (SECS(2636.6), "2,636.6"),
    ]
    for got, want in vec:
        need(got == want, "format self-test: %r != %r" % (got, want))


# ----------------------------------------------------------------------------------------------------------------------
# The spec's exact texts

with open(SPEC_FILE, "r", encoding="utf-8", newline="") as _f:
    SPEC_TEXT = _f.read()


def _spec_blocks():
    need("\r" not in SPEC_TEXT, "the spec has carriage returns")
    blocks, cur, inside = [], None, False
    for ln in SPEC_TEXT.split("\n"):
        if ln == "```":
            if inside:
                blocks.append(cur)
                inside = False
            else:
                cur, inside = [], True
        elif inside:
            cur.append(ln)
    need(not inside, "an unclosed fence in the spec")
    need(len(blocks) == 63, "the spec has %d fenced blocks, expected 63" % len(blocks))
    return blocks


BLOCKS = _spec_blocks()


def blk(i, prefix, n):
    b = BLOCKS[i]
    need(len(b) == n and b[0].startswith(prefix), "spec block %d is not the expected one (%r)" % (i, prefix))
    return list(b)


# A Markdown soft line break inside a backticked or quoted span reads as a space ("`Seasonal\nnormal`").
SPEC_FLAT = SPEC_TEXT.replace("\n", " ")


def bconst(s):
    need(("`" + s + "`") in SPEC_FLAT, "a backticked constant not in the spec: %r" % s)
    return s


def qconst(s):
    need(('"' + s + '"') in SPEC_FLAT, "a quoted constant not in the spec: %r" % s)
    return s


def spec_match(pattern, what):
    # version 2: the one place in the spec text that matches a regular expression (multi-line mode), so that a text
    # outside a fenced block is taken from the spec, not retyped; stop unless there is exactly one match
    hits = list(re.finditer(pattern, SPEC_TEXT, re.M))
    need(len(hits) == 1, "the spec has %d places for %s, expected 1" % (len(hits), what))
    return hits[0]


# Version 2 (C1): the two values of `{shares_sentence}` (spec 4.7), each on its own line as one code span; version 3
# (V3-1): the values changed and the bullet's first line names version 3.
_SS = spec_match(r"^- `\{shares_sentence\}` \(version 2, C1; version 3, V3-1\): fire and coral \(the tables with panel g\)\n"
                 r"  `([^`\n]+)`;\n  else \(pm25, ndvi, defo\)\n  `([^`\n]+)`$", "the {shares_sentence} bullet of 4.7")
SHARES_G, SHARES_NOG = bconst(_SS.group(1)), bconst(_SS.group(2))
# Version 2 (C6): E10's "What it checks", from the E10 row of the spec's row table of 4.5.
E10_WHAT = bconst(spec_match(r"^\| `E10` \| `([^`\n]+)` \| ", "the E10 row of 4.5").group(1))
# Version 2 (C5): the label of the S3.22 row whose cells are AW4 `cross_link_models` (spec 4.6).
CROSS_LABEL = bconst(spec_match(r"^\| `([^`\n]+)` \| AW4 `cross_link_models` as a model list \|$",
                                "the cross-link row of 4.6").group(1))
# Version 3 (V3-3): the value of `{extra_src}` for ndvi (spec 4.7).
EXTRA_SRC_NDVI = bconst(spec_match(r"^- `\{extra_src\}`: ndvi `([^`\n]+)`;$", "the {extra_src} bullet of 4.7").group(1))
# Version 3 (V3-6): treeroute's skill-guard cell, from the cell rules of S3.18 a (4.2) and of S3.20 (4.4).
TR_GUARD_S318 = bconst(spec_match(r"^\| Skill guard at the nowcast \| treeroute: `([^`\n]+)`; a rival: ",
                                  "the skill-guard rule of 4.2").group(1))
TR_GUARD_S320 = bconst(spec_match(r"^\| Skill guard \| treeroute: `([^`\n]+)`; a rival: ",
                                  "the skill-guard rule of 4.4").group(1))
# Version 3 (V3-6): the random forest's "Model and SHAP method", from the constants table of 4.2.
RF_METHOD = bconst(spec_match(r"^\| rival_rf \| `([^`\n]+)` \|$", "the rival_rf constant of 4.2").group(1))
# Version 3 (V3-6): the first row of S3.21 (its gate cell and "What it checks"), the first row after the header and
# separator of the row table of 4.5, and the "What it checks" of E3a, E3m, E3 and E6 from their rows.
_ARM = spec_match(r"^\| Gate cell \| What it checks \| Problem cell \|\n\|---\|---\|---\|\n\| `([^`\n]+)` \| `([^`\n]+)` \| ",
                  "the first row of 4.5")
ARM_FIRST, ARM_WHAT = bconst(_ARM.group(1)), bconst(_ARM.group(2))


def s321_what(gid):
    return bconst(spec_match(r"^\| `" + re.escape(gid) + r"` \| `([^`\n]+)` \| ", "the %s row of 4.5" % gid).group(1))


E3A_WHAT, E3M_WHAT, E3_WHAT, E6_WHAT = (s321_what(g) for g in ("E3a", "E3m", "E3", "E6"))
# Version 4 (V4-6, V4-11): the "What it checks" of E5ᵃ and E8, from their rows of 4.5 (V4-2, V4-1 and V4-10 changed
# the texts of E3a, E3m and E3, which are read above). Version 5 (V5-4, V5-3) changed the texts of E3m and E5ᵃ again;
# both are read here as before.
E5_WHAT, E8_WHAT = s321_what("E5" + SUP_A), s321_what("E8")
# Version 4 (V4-5): the plain arm's answer type, from the rule of the `Adopted arm` row of 4.5 (the first row); the
# corrector's text is unchanged.
_ANS = spec_match(r'^\| `' + re.escape(ARM_FIRST) + r'` \| `' + re.escape(ARM_WHAT) + r'` \| [^\n]*?'
                  r'\("([^"\n]+)" if R `table_kind` == plain, "([^"\n]+)" if corrector\)',
                  "the answer type of the rule of the first row of 4.5")
ANS_PLAIN = qconst(_ANS.group(1))
# Version 4 (V4-7): the new start of the first line of block 15 (the panel b table of S3.18), from section 11.
PANEL_B_START = bconst(spec_match(r"\(block 15, now starting\n`([^`\n]+)`\)", "the start of block 15 in section 11").group(1))
# Version 3 (V3-6): the Link cell rule of 4.7. M is the source label's words (check 3.3 tests the source labels with
# them, as before); P is the printed words that take M's place in the Link cell.
_MP = spec_match(r'with M = "([^"\n]+)" \(the source label\'s words, check 3\.3\) and P = "([^"\n]+)" \(the printed '
                 r'words; version 3, V3-6\)', "the M and P of the Link cell rule of 4.7")
M_DECL, P_DECL = qconst(_MP.group(1)), qconst(_MP.group(2))
bconst(M_DECL + "<names>")  # check 3.3's words: `; raw model, declined by its guard: <names>`
_LINK_EX = spec_match(r"So `([^`\n]+)` prints `([^`\n]+)` \|$", "the example of the Link cell rule of 4.7")


# ----------------------------------------------------------------------------------------------------------------------
# Names (spec 2.1-2.4, 2.7)

PROBS = ["pm25", "ndvi", "fire", "defo", "coral"]
PDISP = {"pm25": "PM2.5", "ndvi": "NDVI", "fire": "Burned fraction", "defo": "Forest loss",
         "coral": "Coral bleaching"}
MODELS = ["treeroute", "rival_ridge", "rival_rf", "rival_lgbm", "rival_lgbm_tweedie", "rival_hgb_l1",
          "rival_bardl_h1"]
MINL = {"treeroute": "treeroute v1", "rival_ridge": "Ridge", "rival_rf": "random forest", "rival_lgbm": "LightGBM",
        "rival_lgbm_tweedie": "Tweedie booster", "rival_hgb_l1": "absolute-error booster", "rival_bardl_h1": "BARDL"}
MHDR = {"treeroute": "treeroute v1", "rival_ridge": "Ridge", "rival_rf": "Random forest", "rival_lgbm": "LightGBM",
        "rival_lgbm_tweedie": "Tweedie booster", "rival_hgb_l1": "Absolute-error booster", "rival_bardl_h1": "BARDL"}
LINKD = {"identity": "identity", "log_c": "log(y + c)", "log_mu": "log \u03bc", "arcsine": "arcsine"}
FAMS = ["own history", "global indices", "local drivers", "context and calendar", "seasonal normal"]
FAM_ROW = {"own history": "Own history", "global indices": "Global indices", "local drivers": "Local drivers",
           "context and calendar": "Context and calendar", "seasonal normal": "Seasonal normal"}
FAM_LABEL = {"own history": "(no own-history input)", "global indices": "(no global-index input)",
             "local drivers": "(no local-driver input)", "context and calendar": "(no context or calendar input)",
             "seasonal normal": "(no seasonal-normal input)"}
FAM_A = {"own history": "own_history", "global indices": "global_indices", "local drivers": "local_drivers",
         "context and calendar": "context_and_calendar", "seasonal normal": "seasonal_normal"}
METHOD = {
    "treeroute": "the adopted arm: tree bank and router; exact interventional TreeSHAP of the trees, router terms "
                 "exactly linear",
    "rival_ridge": "ridge regression; exact linear SHAP",
    "rival_rf": RF_METHOD,  # version 3 (V3-6): taken from the spec's constants table of 4.2
    "rival_lgbm": "LightGBM; exact interventional TreeSHAP",
    "rival_lgbm_tweedie": "LightGBM with a Tweedie loss; exact interventional TreeSHAP",
    "rival_hgb_l1": "gradient booster on absolute error; exact interventional TreeSHAP",
    "rival_bardl_h1": "published rain-lag Bayesian distributed-lag model, per location; exact linear SHAP over its "
                      "nine input columns",
}
RIDGE4 = ("pm25", "ndvi", "fire", "defo")
B1P = ["pm25", "ndvi", "fire"]


def check_name_constants():
    for d in (PDISP, MINL, MHDR, LINKD, FAM_LABEL, METHOD):
        for v in d.values():
            bconst(v)
    for v in FAM_ROW.values():
        bconst(v)
    for v in ("burned fraction", "forest loss", "coral bleaching"):
        bconst(v)


def dsort(models):
    for m in models:
        need(m in MODELS, "a model outside the display table: %r" % m)
    return sorted(models, key=MODELS.index)


def mlist(models):
    ms = dsort(models)
    return ", ".join(MINL[m] for m in ms) if ms else "none"


def nlist(names):
    return ", ".join("`" + n + "`" for n in names)


def pair_text(a, b):
    x, y = dsort([a, b])
    return MINL[x] + " vs " + MINL[y]


def link_of(s):
    lk = s.split("|")[0]
    need(lk in LINKD, "an unknown link %r" % s)
    return lk


IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def jp(*segs):
    out = ""
    for s in segs:
        if isinstance(s, int) and not isinstance(s, bool):
            out += "[%d]" % s
        elif IDENT.match(s):
            out += ("." if out else "") + s
        else:
            out += "[" + json.dumps(s) + "]"
    return out


def psel(level, a, b, stat, col):
    return "level=%s; model_a=%s; model_b=%s; statistic=%s; column=%s" % (level, a, b, stat, col)


# ----------------------------------------------------------------------------------------------------------------------
# Values, cells and lines

def nan2none(x):
    if isinstance(x, float) and math.isnan(x):
        return None
    return x


class Val(object):
    def __init__(self, x, source, selector, stored=None):
        self.x = nan2none(x)
        self.source = source
        self.selector = selector
        self.stored = [self.x] if stored is None else [nan2none(s) for s in stored]


class Cell(object):
    def __init__(self, row=None, col=None):
        self.buf = []
        self.toks = []
        self.row = row
        self.col = col

    def t(self, s):
        self.buf.append(s)
        return self

    def n(self, printed, part, val, row=None, col=None):
        r = row if row is not None else self.row
        c = col if col is not None else self.col
        need(r is not None and c is not None, "a number without a row or column key: %r" % printed)
        self.buf.append(printed)
        self.toks.append({"row": r, "column": c, "part": part, "printed": printed, "source": val.source,
                          "selector": val.selector, "stored": list(val.stored)})
        return self

    def text(self):
        return "".join(self.buf)


class Line(object):
    def __init__(self, text, cells=None, table=None, panel=None):
        self.text = text
        self.cells = cells or []
        self.table = table
        self.panel = panel


DOC = []  # blocks; a block is a list of Line


def add_text(texts):
    DOC.append([Line(t) for t in texts])


def split_header(h):
    need(h.startswith("| ") and h.endswith(" |"), "a header line that is not a table line: %r" % h)
    return h[2:-2].split(" | ")


def add_table(tid, panel, header, sep, rows):
    hc = split_header(header)
    ncol = len(hc)
    need(sep == "|" + "---|" * ncol, "a separator that does not fit its header: %r" % sep)
    for c in hc:
        need("|" not in c and "\n" not in c and c == c.strip() and c, "a bad header cell %r" % c)
    lines = [Line(header), Line(sep)]
    for cells in rows:
        need(len(cells) == ncol, "a row with %d cells under a header of %d" % (len(cells), ncol))
        texts = [c.text() for c in cells]
        for t in texts:
            need(t and t == t.strip() and "|" not in t and "\n" not in t and "\t" not in t, "a bad cell %r" % t)
        lines.append(Line("| " + " | ".join(texts) + " |", cells, tid, panel))
    DOC.append(lines)


def note_line(tid, cell):
    return Line(cell.text(), [cell], tid, "")


def plain_note(text):
    return Line(text)


def add_notes(lines):
    for ln in lines:
        need(ln.text and "\n" not in ln.text, "a bad note line")
    DOC.append(lines)


PH_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def fill(cell, template, mapping):
    pos = 0
    used = set()
    for m in PH_RE.finditer(template):
        cell.t(template[pos:m.start()])
        key = m.group(1)
        need(key in mapping, "a placeholder without a value: %s" % key)
        item = mapping[key]
        if isinstance(item, str):
            cell.t(item)
        else:
            printed, part, val, col = item
            cell.n(printed, part, val, col=col)
        used.add(key)
        pos = m.end()
    cell.t(template[pos:])
    need(used == set(mapping), "values for placeholders that the template lacks: %r" % (set(mapping) - used))
    need("{" not in cell.text() and "}" not in cell.text(), "a placeholder left in %r" % cell.text())
    return cell


def w_ci2(c, v, lo, hi, nf, D, fmt=NUM2):
    if finite(v.x):
        c.n(fmt(v.x), "value", v)
    else:
        c.n("undefined", "value", v)
    nfx = None if nf is None else nf.x
    if nfx is None or nfx == 0:
        return c
    need(isinstance(nfx, int) and not isinstance(nfx, bool), "a finite count that is not an int: %r" % (nfx,))
    c.t(" [").n(fmt(lo.x), "ci_low", lo).t(", ").n(fmt(hi.x), "ci_high", hi).t("]")
    if nfx < D:
        c.t(" (").n(COUNT(nfx), "n_finite", nf).t(" finite draws)")
    return c


def w_sign(c, v, k, lo, hi, nf, D):
    if finite(v.x):
        c.n(NUM2(v.x), "value", v)
    else:
        c.n("undefined", "value", v)
    nfx = nf.x
    need(isinstance(nfx, int) and not isinstance(nfx, bool), "a sign-agreement finite count %r" % (nfx,))
    if nfx > 0:
        c.t(" [").n(NUM2(lo.x), "ci_low", lo).t(", ").n(NUM2(hi.x), "ci_high", hi).t("]")
    c.t(" (").n(COUNT(k.x), "signs", k).t(" sign" if k.x == 1 else " signs")
    if 0 < nfx < D:
        c.t("; ").n(COUNT(nfx), "n_finite", nf).t(" finite draws")
    c.t(")")
    return c


def w_top(c, name, share, part="share"):
    c.t("`" + name + "` ").n(PCT1(share.x), part, share)
    return c


# ----------------------------------------------------------------------------------------------------------------------
# Loading (section 1 files only)

def jload(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def jload_strict(path):
    def bad(c):
        stop("a non-strict JSON constant %s in %s" % (c, short(path)))
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f, parse_constant=bad)


def read_lines(path):
    # spec section 1, text formats (version 2, G2): text mode with universal newlines (every "\r\n" becomes "\n") and
    # encoding utf-8-sig (a leading byte-order mark is dropped), then split on "\n"; line numbers count from 1 on these
    # lines, and every field and regex is applied to a line without its line end
    with open(path, "r", encoding="utf-8-sig") as f:
        lines = f.read().split("\n")
    for ln in lines:
        need("\r" not in ln, "a line end left in a line of %s" % short(path))
    return lines


PL, AW4, PAIRS, IMP, FAMP, META, EXACT, RIDGEX, GATES, MAN, B1META, B1DONE = ({} for _ in range(12))


def load_all():
    for p in PROBS:
        PL[p] = jload(p_compare(p, "per_lead.json"))
        AW4[p] = jload(p_compare(p, "AW4_main_row.json"))
        df = pd.read_parquet(p_compare(p, "pairs.parquet"))
        cols = ["level", "model_a", "model_b", "pair_label", "statistic", "value", "ci_low", "ci_high",
                "finite_replicates", "signs_compared"]
        lists = {c: df[c].tolist() for c in cols}
        recs = {}
        for i in range(len(df)):
            key = (lists["level"][i], lists["model_a"][i], lists["model_b"][i], lists["statistic"][i])
            need(key not in recs, "a duplicate pairs.parquet row %r in %s" % (key, p))
            recs[key] = {c: lists[c][i] for c in cols}
        PAIRS[p] = recs
        df = pd.read_parquet(p_compare(p, "importance.parquet"))
        cols = ["level", "model", "player", "active", "mean_abs", "share"]
        lists = {c: df[c].tolist() for c in cols}
        by = {}
        for i in range(len(df)):
            by.setdefault((lists["level"][i], lists["model"][i]), []).append({c: lists[c][i] for c in cols})
        IMP[p] = by
        df = pd.read_parquet(p_compare(p, "families.parquet"))
        fm = {}
        for mo, fa, sh in zip(df["model"].tolist(), df["family"].tolist(), df["share"].tolist()):
            need((mo, fa) not in fm, "a duplicate families.parquet row in %s" % p)
            fm[(mo, fa)] = sh
        FAMP[p] = fm
        META[p], EXACT[p] = {}, {}
        for m in PL[p]["models"]:
            META[p][m] = jload(p_model(p, m, "meta.json"))
            if m != "treeroute":
                EXACT[p][m] = jload(p_model(p, m, "exactness.json"))
        rx = p_model(p, "rival_ridge", "ridge_shap_exactness.json")
        need(os.path.exists(rx) == (p in RIDGE4), "ridge_shap_exactness.json exists outside the four problems or is missing")
        if p in RIDGE4:
            RIDGEX[p] = jload(rx)
        GATES[p] = jload(p_gates(p))
        MAN[p] = jload(p_manifest(p))
        b1 = p_model(p, "treeroute_B1", "meta.json")
        if os.path.exists(b1):
            B1META[p] = jload(b1)
            B1DONE[p] = jload(p_model(p, "treeroute_B1", "rows.parquet.done.json"))


REG = {}


def load_register():
    lines = read_lines(P_REGISTER)
    for i, ln in enumerate(lines, 1):
        if not ln:
            continue
        toks = ln.split(" ")
        fields = {}
        for t in toks[1:]:
            need("=" in t, "a register field without '=': %r" % t)
            k, v = t.split("=", 1)
            fields[k] = v
        p = fields.get("problem")
        need(p in PROBS and p not in REG, "a register line for %r" % p)
        REG[p] = (i, fields)
    need(set(REG) == set(PROBS), "the register lacks a problem")


LOGB1 = {}


def load_logs():
    setup_re = re.compile(blk(58, "^\\[(\\d{4}", 1)[0])
    done_re = re.compile(blk(59, "^\\[(\\d{4}", 1)[0])
    for p in ["pm25", "ndvi", "fire", "defo"]:
        lines = read_lines(p_log(p))
        idx = [i for i, ln in enumerate(lines) if setup_re.match(ln)]
        need(idx, "no set-up line in the log of %s" % p)
        si = idx[-1]
        m = setup_re.match(lines[si])
        tstamp, prob, rows, pairs = m.group(1), m.group(2), m.group(3), m.group(4)
        need(tstamp >= "2026-11-15 23:06:00", "the B1 set-up line of %s is before 2026-11-15 23:06:00" % p)
        need(prob == p and int(rows) == 1000, "the B1 set-up line of %s names %s, %s rows" % (p, prob, rows))
        di = None
        for j in range(si + 1, len(lines)):
            if done_re.match(lines[j]):
                di = j
                break
        need(di is not None, "no 'done in' line after the B1 set-up line of %s" % p)
        md = done_re.match(lines[di])
        need(md.group(2) == p, "the 'done in' line of %s names %s" % (p, md.group(2)))
        LOGB1[p] = {"setup_line": si + 1, "done_line": di + 1, "pairs": int(pairs), "total": float(md.group(3)),
                    "tree": float(md.group(4))}


MAXI = {}


def load_maxima():
    rx = re.compile(blk(0, "^\\s+(jaccard_top5", 1)[0])
    lines = read_lines(P_MAXIMA)
    heads = [i for i, ln in enumerate(lines) if ln.startswith("==")]
    need(heads and lines[heads[0]] == "== BARDL pair-levels", "the maxima file does not start with its BARDL block")
    end = heads[1] if len(heads) > 1 else len(lines)
    for i in range(heads[0] + 1, end):
        ln = lines[i]
        if not ln:
            continue
        m = rx.match(ln)
        need(m is not None, "a line of the BARDL block does not match: %r" % ln)
        s = m.group(1)
        need(s not in MAXI, "the statistic %s appears twice in the BARDL block" % s)
        MAXI[s] = {"line": i + 1, "spread": m.group(2), "problem": m.group(3), "level": m.group(4),
                   "pair": m.group(5), "v1": m.group(6), "v2": m.group(7), "v3": m.group(8)}
    for s in ["jaccard_top5", "jaccard_top10", "jaccard_top20", "rho20", "rbo090", "rbo095"]:
        need(s in MAXI, "the statistic %s is missing from the BARDL block" % s)


# ----------------------------------------------------------------------------------------------------------------------
# Derived lookups

def pair_row(p, level, a, b, stat):
    x, y = sorted([a, b])
    key = (level, x, y, stat)
    need(key in PAIRS[p], "no pairs.parquet row %r in %s" % (key, p))
    return PAIRS[p][key]


def pair_val(p, level, a, b, stat, col):
    x, y = sorted([a, b])
    r = pair_row(p, level, x, y, stat)
    return Val(r[col], short(p_compare(p, "pairs.parquet")), psel(level, x, y, stat, col))


def ranking(p, level, m):
    rows = [r for r in IMP[p].get((level, m), []) if r["active"] is True]
    for r in rows:
        need(finite(r["mean_abs"]) and finite(r["share"]), "a non-finite importance in %s %s %s" % (p, level, m))
    return sorted(rows, key=lambda r: (-r["mean_abs"], r["player"]))


MISSING = {}


def gate_key(G, gid):
    ks = [k for k in G if k.split("_")[0] == gid]
    need(len(ks) <= 1, "two gates named %s" % gid)
    return ks[0] if ks else None


def aobj(o, path):
    src = short(P_A)
    return (Val(o["value"], src, jp(*(path + ["value"]))), Val(o["ci_low"], src, jp(*(path + ["ci_low"]))),
            Val(o["ci_high"], src, jp(*(path + ["ci_high"]))), Val(o["n_finite"], src, jp(*(path + ["n_finite"]))))


def awobj(p, key):
    src = short(p_compare(p, "AW4_main_row.json"))
    o = AW4[p][key]
    need(isinstance(o["ci"], list) and len(o["ci"]) == 3, "an AW4 interval that is not [low, high, finite]")
    return (Val(o["value"], src, jp(key, "value")), Val(o["ci"][0], src, jp(key, "ci", 0)),
            Val(o["ci"][1], src, jp(key, "ci", 1)), Val(o["ci"][2], src, jp(key, "ci", 2)))


# ----------------------------------------------------------------------------------------------------------------------
# Section 3: checks before building

STATS_COMMON = ["spearman", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10", "rbo_p0.9",
                "rbo_p0.95", "tvd", "sign_agreement_top10"]
# M_DECL (the source label's words) and P_DECL (the printed words) are taken from the spec's rule of 4.7 above
# (version 3, V3-6).


def link_cell(lab):
    # spec 4.7, the Link cell: if the source label holds M, the text before M + P + the inline names (2.2) of the data
    # names after M (split on ", ") joined by ", "; else the label as it stands
    if M_DECL in lab:
        before, after = lab.split(M_DECL, 1)
        names = after.split(", ")
        for nm in names:
            need(nm in MINL, "an unknown declined model %r" % nm)
        return before + P_DECL + ", ".join(MINL[nm] for nm in names)
    return lab


def check_link_rule():
    # version 3: the rule applied to the spec's own example gives the spec's printed example
    need(link_cell(_LINK_EX.group(1)) == _LINK_EX.group(2), "the Link cell rule does not print the spec's example")


def isnan(x):
    return isinstance(x, float) and math.isnan(x)


def checks():
    A = RESULTS
    for p in PROBS:
        pl = PL[p]
        # 3.1
        ln, reg = REG[p]
        need(pl["rows"] == 1000 and int(reg["n"]) == 1000 and MAN[p]["n"] == 1000, "3.1 rows of %s" % p)
        need(pl["draws"] == 2000, "3.1 draws of %s" % p)
        need(reg["sample"] == MAN[p]["sha256"]["sample.parquet"] == pl["sample_sha256"], "3.1 sample hash of %s" % p)
        for m in pl["models"]:
            need(META[p][m]["sample_sha256"] == pl["sample_sha256"], "3.1 sample hash of %s %s" % (p, m))
        if p in B1META:
            need(B1META[p]["sample_sha256"] == pl["sample_sha256"], "3.1 sample hash of %s treeroute_B1" % p)
        with open(p_compare(p, "bootstrap_draws.npy"), "rb") as f:
            need(hashlib.sha256(f.read()).hexdigest() == pl["draws_sha256"], "3.1 draws hash of %s" % p)
        need(pl["regions"] == MAN[p]["regions_in_sample"], "3.1 regions of %s" % p)
        # 3.2
        for m in pl["models"]:
            need(m in MODELS and os.path.isdir(SHAP + "\\out\\" + p + "\\lead_0\\" + m), "3.2 model %s of %s" % (m, p))
        need("treeroute_B1" not in pl["models"] and "treeroute" in pl["models"], "3.2 models of %s" % p)
        for m in pl["models"]:
            mt = META[p][m]
            need(mt["rows"] == 1000 and mt["pass"] is True and mt["structural_zero_violations"] == 0,
                 "3.2 meta of %s %s" % (p, m))
            for k in ("S-ADD", "S-EVAL", "S-RESID", "S-ZERO"):
                need(mt["checks_passed"][k] is True, "3.2 %s of %s %s" % (k, p, m))
            if m != "treeroute":
                if m == "rival_ridge" and p in RIDGE4:
                    # version 2 (C2): exactness.json is the rivals' SHAP script's own row-by-row check
                    need(EXACT[p][m]["pass"] is False, "3.2 the rivals' SHAP script's own ridge check of %s" % p)
                    need(RIDGEX[p]["stage"] == "bits" and RIDGEX[p]["pass"] is True, "3.2 ridge_shap of %s" % p)
                else:
                    need(EXACT[p][m]["pass"] is True, "3.2 exactness of %s %s" % (p, m))
        need(GATES[p]["stopped_at"] is None, "3.2 gates of %s stopped" % p)
        # 3.3
        links = pl["links"]
        cub = None
        for m in pl["models"]:
            parts = links[m].split("|")
            need(len(parts) == 3 and parts[1].startswith("c=") and parts[2].startswith("ub="), "3.3 link %r" % links[m])
            need(cub is None or cub == parts[1:], "3.3 c and ub differ within %s" % p)
            cub = parts[1:]
        models = sorted(pl["models"])
        for L in ("variable", "feature"):
            stats = list(STATS_COMMON)
            if L == "variable":
                stats.append("tvd_family")
            if pl[L]["active"] >= 200:
                stats.append("jaccard_top20")
            keys = [k for k in PAIRS[p] if k[0] == L]
            need(len(keys) == len(stats) * len(models) * (len(models) - 1) // 2, "3.3 row count %s %s" % (p, L))
            for a, b in itertools.combinations(models, 2):
                labs = set()
                for s in stats:
                    need((L, a, b, s) in PAIRS[p], "3.3 missing %s %s %s %s" % (p, L, a + "|" + b, s))
                    labs.add(PAIRS[p][(L, a, b, s)]["pair_label"])
                need(len(labs) == 1, "3.3 more than one label for %s %s %s" % (p, L, a + "|" + b))
                lab = labs.pop()
                pre = "same-link" if links[a] == links[b] else "cross-link (not comparable in scale or rank)"
                decl = [x for x in (a, b) if x in pl["declined_by_guard"]]
                need(lab.startswith(pre), "3.3 label start %r" % lab)
                need((M_DECL in lab) == bool(decl), "3.3 declined mark %r" % lab)
                want = pre + (M_DECL + ", ".join(decl) if decl else "")
                need(lab == want, "3.3 label %r, expected %r" % (lab, want))
            for k in keys:
                need(k[1] < k[2], "3.3 model_a not before model_b")
        # 3.4
        for L in ("variable", "feature"):
            for a, b in itertools.combinations(models, 2):
                r = PAIRS[p][(L, a, b, "sign_agreement_top10")]
                o = A["problems"][p]["levels"][L]["pairs"][a + "|" + b]
                sa = o["sign_agreement"]
                v, av = r["value"], sa["value"]
                need((av is None and isnan(v)) or (finite(av) and finite(v) and abs(av - v) <= 1e-12),
                     "3.4 sign agreement %s %s %s" % (p, L, a + "|" + b))
                need(o["sign_n_determined"]["value"] == r["signs_compared"], "3.4 signs %s %s" % (p, a + "|" + b))
                nf = sa["n_finite"]
                need(isinstance(nf, int) and not isinstance(nf, bool) and nf >= 0, "3.4 n_finite %r" % (nf,))
                if nf > 0:
                    need(finite(sa["ci_low"]) and finite(sa["ci_high"]), "3.4 interval %s %s" % (p, a + "|" + b))
                else:
                    need(sa["ci_low"] is None and sa["ci_high"] is None, "3.4 null interval %s %s" % (p, a + "|" + b))
        # 3.5
        for L in ("variable", "feature"):
            for m in pl["models"]:
                rk = ranking(p, L, m)
                need(len(rk) == pl[L]["active"], "3.5 active rows %s %s %s" % (p, L, m))
        top3 = [r["player"] for r in ranking(p, "variable", "treeroute")[:3]]
        if p == "fire":
            want = [e[0] for e in A["problems"]["fire"]["main_row"]["treeroute_top3"]]
            ov = A["problems"]["fire"]["main_row"]["own_history_share_treeroute"]["value"]
            need(abs(ov - FAMP[p][("treeroute", "own history")]) <= 1e-12, "3.5 fire's own-history share")
        else:
            want = AW4[p]["treeroute_top3"]
        need(top3 == want, "3.5 treeroute's top 3 of %s: %r != %r" % (p, top3, want))
        # 3.6
        fams_used = set(pl["families"].values())
        need(fams_used <= set(FAMS), "3.6 an unknown family in %s" % p)
        MISSING[p] = [f for f in FAMS if f not in fams_used]
        want_missing = {"coral": ["own history"], "defo": ["context and calendar"]}.get(p, [])
        need(MISSING[p] == want_missing, "3.6 families without a variable in %s: %r" % (p, MISSING[p]))
        for f in MISSING[p]:
            for m in pl["models"]:
                need(FAMP[p][(m, f)] == 0.0, "3.6 share of %s %s %s" % (p, m, f))
        for m in pl["models"]:
            for f in FAMS:
                need((m, f) in FAMP[p], "families.parquet lacks %s %s %s" % (p, m, f))
        # 3.7
        aw = AW4[p]
        if p != "fire":
            kw = pl["variable"]["kendall_w_main_set"]
            need(aw["kendall_w"]["value"] == kw["value"] and aw["kendall_w"]["ci"][0:2] == kw["ci"]
                 and aw["kendall_w"]["ci"][2] == kw["finite_replicates"], "3.7 W of %s" % p)
            need(set(aw["models_in_main_set"]) == set(pl["main_set"]), "3.7 main set of %s" % p)
            rivals = [m for m in aw["models_in_main_set"] if m != "treeroute"]
            sp = [pair_row(p, "variable", m, "treeroute", "spearman_top20_union")["value"] for m in rivals]
            med = aw["treeroute_vs_same_link_rivals_median_spearman_top20_union"]
            need(abs(med["range"][0] - min(sp)) <= 1e-12 and abs(med["range"][1] - max(sp)) <= 1e-12,
                 "3.7 range of %s" % p)
            need(abs(float(np.median(np.array(sp))) - med["value"]) <= 1e-12, "3.7 median of %s" % p)
            oh = [FAMP[p][(m, "own history")] for m in rivals]
            ohm = aw["own_history_share_median_rival"]["value"]
            need(abs(float(np.median(np.array(oh))) - ohm) <= 1e-12, "3.7 median own history of %s" % p)
            if p in ("pm25", "defo"):
                need(abs(FAMP[p][("rival_lgbm", "own history")] - ohm) <= 1e-12, "3.7 LightGBM's share, %s" % p)
            if p == "ndvi":
                need(len(oh) == 4, "3.7 ndvi has four rivals")
                so = sorted(oh)
                need(abs((so[1] + so[2]) / 2.0 - ohm) <= 1e-12, "3.7 ndvi's two middle shares")
        else:
            need(aw["models_in_main_set"] == ["treeroute"], "3.7 fire's main set")
            need(aw["cross_link_models"] == ["rival_lgbm", "rival_lgbm_tweedie", "rival_rf"], "3.7 fire cross-link")
            need(aw["declined_models"] == ["rival_ridge"], "3.7 fire declined")
            ci = aw["kendall_w"]["ci"]
            need(isnan(aw["kendall_w"]["value"]) and isnan(ci[0]) and isnan(ci[1]) and ci[2] == 0 and len(ci) == 3,
                 "3.7 fire's W")
    # 3.8
    want_status = {"coral": "none", "defo": "identity", "fire": "full", "pm25": "full", "ndvi": "full"}
    for p in PROBS:
        need(A["b1"][p]["status"]["numbers"] == want_status[p], "3.8 B1 status of %s" % p)
    need(A["b1"]["defo"]["identity"]["as_expected"] is True, "3.8 defo identity")
    for p in ["defo", "fire", "pm25", "ndvi"]:
        lg = LOGB1[p]
        rec = A["b1"][p]["identity"] if p == "defo" else A["b1"][p]["run"]
        need(lg["pairs"] == rec["pairs_log"] == B1META[p]["pairs"], "3.8 pairs of %s" % p)
        need(lg["total"] == rec["total_seconds_log"] == B1DONE[p]["seconds"], "3.8 total seconds of %s" % p)
        need(lg["tree"] == rec["tree_shap_seconds_log"] == B1META[p]["tree_shap_seconds"], "3.8 tree seconds of %s" % p)
    # 3.9
    pl = PL["ndvi"]
    need(pl["variable"]["nonzero_players"]["rival_bardl_h1"] == 3 and pl["feature"]["nonzero_players"]["rival_bardl_h1"] == 9,
         "3.9 BARDL's nonzero counts")
    t5 = ranking("ndvi", "variable", "rival_bardl_h1")[:5]
    hit = [r for r in t5 if r["player"] == "aet_total_mm"]
    need(len(hit) == 1 and hit[0]["share"] == 0.0, "3.9 aet_total_mm in BARDL's top 5")
    mx = MAXI["jaccard_top5"]
    a, b = mx["pair"].split("|")
    need(mx["problem"] == "ndvi", "3.9 maxima problem")
    jr = pair_row("ndvi", mx["level"], a, b, "jaccard_top5")["value"]
    need(abs(float(mx["v1"]) - jr) <= 1e-9, "3.9 jaccard_top5 of the maxima line")
    # 3.10
    for p in PROBS:
        G, R = GATES[p]["gates"], GATES[p]["result"]
        for k in G:
            need(k.split("_")[0] in ("E0", "E1", "E2", "E3", "E3a", "E3m", "E4", "E5", "E5a", "E6", "E7", "E8", "E9",
                                     "E10"), "3.10 a gate outside Table S3.21: %s" % k)
        for gid in ("E1", "E2", "E0", "E3a", "E3", "E4", "E5", "E6", "E9", "E8", "E10"):
            need(gate_key(G, gid) is not None, "3.10 gate %s missing in %s" % (gid, p))
        for k, g in G.items():
            if k.split("_")[0] == "E5":
                need(g["pass"] is False, "3.10 E5 of %s" % p)
            else:
                need(g["pass"] is True, "3.10 gate %s of %s" % (k, p))
        e3a = G[gate_key(G, "E3a")]["values"]
        k3m = gate_key(G, "E3m")
        need((k3m is not None) == (e3a["path_map"] is True), "3.10 E3m and path_map of %s" % p)
        if k3m is not None:
            for fo in G[k3m]["values"]["files"]:
                need(fo["equal"] is True, "3.10 E3m files of %s" % p)
        need((gate_key(G, "E5a") is not None) == (R["link"] == "arcsine"), "3.10 E5a of %s" % p)
        need((gate_key(G, "E7") is not None) == (R["weighted"] is True), "3.10 E7 of %s" % p)
        e4 = G[gate_key(G, "E4")]["values"]
        need(e4["rows"][0] == e4["rows"][1] and e4["row_key_hash"][0] == e4["row_key_hash"][1], "3.10 E4 of %s" % p)
        need(G[gate_key(G, "E9")]["values"]["fits_whose_X_b_differs_from_the_kernel"] == 0, "3.10 E9 of %s" % p)
        arm = "%s_%s_%s" % (R["link"], R["table_kind"], "gls" if R["weighted"] is True else "unweighted")
        need(META[p]["treeroute"]["arm"] == arm, "3.10 arm of %s" % p)


# ----------------------------------------------------------------------------------------------------------------------
# The tables (spec section 4)

def build_table9():
    A = RESULTS
    tid = "9"
    add_text([blk(7, "**Table 9.**", 1)[0]])
    hdr = blk(8, "| Problem | Main set |", 2)
    rows = []
    for p in PROBS:
        aw = AW4[p]
        D = PL[p]["draws"]
        src = short(p_compare(p, "AW4_main_row.json"))
        cells = [Cell().t(PDISP[p])]
        if p == "fire":
            need(isnan(aw["kendall_w"]["value"]), "fire's W is not NaN")
            cells.append(Cell().t(bconst("treeroute v1 only" + SUP_A)))
            cells.append(Cell(p, "kendall_w").n("undefined", "value", Val(aw["kendall_w"]["value"], src, "kendall_w.value")))
            cells.append(Cell().t(NDASH))
            cells.append(Cell().t(NDASH))
            mr = A["problems"]["fire"]["main_row"]
            cells.append(Cell().t(nlist([e[0] for e in mr["treeroute_top3"]]) + DAGGER))
            cells.append(Cell().t(NDASH))
            c = Cell(p, "own_history_treeroute")
            w_ci2(c, *aobj(mr["own_history_share_treeroute"], ["problems", "fire", "main_row", "own_history_share_treeroute"]), D=D)
            c.t(DAGGER)
            cells.append(c)
            cells.append(Cell().t(NDASH))
        else:
            cells.append(Cell().t(mlist(aw["models_in_main_set"])))
            c = Cell(p, "kendall_w")
            w_ci2(c, *awobj(p, "kendall_w"), D=D)
            cells.append(c)
            K = "treeroute_vs_same_link_rivals_median_spearman_top20_union"
            c = Cell(p, "spearman_top20_union_median")
            w_ci2(c, *awobj(p, K), D=D)
            rg = aw[K]["range"]
            c.t(" (").n(NUM2(rg[0]), "range_min", Val(rg[0], src, jp(K, "range", 0))).t(" to ")
            c.n(NUM2(rg[1]), "range_max", Val(rg[1], src, jp(K, "range", 1))).t(")")
            cells.append(c)
            c = Cell(p, "rbo_vs_consensus")
            w_ci2(c, *awobj(p, "rbo_vs_consensus_p0.9"), D=D)
            if p == "pm25":
                c.t(SUP_B)
            cells.append(c)
            cells.append(Cell().t(nlist(aw["treeroute_top3"])))
            cells.append(Cell().t(nlist(aw["consensus_top3"])))
            for key, col in (("own_history_share_treeroute", "own_history_treeroute"),
                             ("own_history_share_median_rival", "own_history_median_rivals")):
                c = Cell(p, col)
                w_ci2(c, *awobj(p, key), D=D)
                if "own history" in MISSING[p]:
                    c.t(" " + FAM_LABEL["own history"])
                cells.append(c)
        rows.append(cells)
    add_table(tid, "", hdr[0], hdr[1], rows)
    add_notes([plain_note(t) for t in blk(9, SUP_A + " Burned fraction", 4)])


def build_s318():
    tid = "S3.18"
    add_text([blk(10, "**Table S3.18 (post hoc).**", 1)[0]])
    add_text([blk(11, "**a. Explained models.**", 1)[0]])
    hdr = blk(12, "| Problem | Model (data name) |", 2)
    rows = []
    for p in PROBS:
        pl = PL[p]
        trl = pl["links"]["treeroute"]
        for m in dsort(pl["models"]):
            cells = [Cell().t(PDISP[p]), Cell().t(MINL[m] + " (`" + m + "`)"), Cell().t(METHOD[m]),
                     Cell().t(LINKD[link_of(pl["links"][m])])]
            if m == "treeroute":
                g = TR_GUARD_S318  # version 3 (V3-6): taken from the spec's cell rule of 4.2
            else:
                gp = META[p][m]["guard"]["passed"]
                need(isinstance(gp, bool), "guard.passed of %s %s" % (p, m))
                g = bconst("passed") if gp else bconst("failed" + SUP_A)
            cells.append(Cell().t(g))
            reasons = []
            if pl["links"][m] != trl:
                reasons.append(bconst("another link"))
            if m in pl["declined_by_guard"]:
                reasons.append(bconst("skill guard failed"))
            if m in pl["main_set"]:
                need(not reasons, "%s %s is in the main set with %r" % (p, m, reasons))
                ms = bconst("yes")
            else:
                need(reasons, "%s %s is outside the main set without a reason" % (p, m))
                ms = qconst("no: ") + "; ".join(reasons)
            cells.append(Cell().t(ms))
            rows.append(cells)
    add_table(tid, "a", hdr[0], hdr[1], rows)
    # version 3 (V3-2): block 14 (the panel b label) has a new first line
    add_text([blk(13, "**b. Rivals and naive baselines left out.**", 1)[0]])
    # version 2 (C4): panel b has 8 rows (10 lines with the header and separator), its note group 3 lines, the new
    # line first (block 16's first line is new), before the line that starts "ᵃ Failed"; version 3 (V3-2): the last
    # row and block 16's first line reworded, the counts unchanged; version 4 (V4-7): block 15's header line (its first
    # line) is new, found by the start that section 11 gives
    tb = blk(14, PANEL_B_START, 10)
    hc = split_header(tb[0])
    need(tb[1] == "|" + "---|" * len(hc), "panel b separator of S3.18")
    for ln in tb[2:]:
        need(len(split_header(ln)) == len(hc), "panel b row of S3.18")
    DOC.append([Line(t) for t in tb])
    nb = blk(15, "Panel b lists the nowcast's rivals and naive baselines", 3)  # version 3 (V3-2): new first line
    need(nb[1].startswith(SUP_A + " Failed:"), "the note group of S3.18 does not have its new line first")
    add_notes([plain_note(t) for t in nb])


def build_s319():
    tid = "S3.19"
    add_text([blk(16, "**Table S3.19 (post hoc).**", 1)[0]])
    hdr = blk(17, "| Problem | Frame rows", 2)
    rows = []
    for p in PROBS:
        man = MAN[p]
        msrc = short(p_manifest(p))
        psrc = short(p_compare(p, "per_lead.json"))
        rl, reg = REG[p]
        cells = [Cell().t(PDISP[p])]
        cells.append(Cell(p, "frame_rows").n(COUNT(man["frame_rows"]), "value", Val(man["frame_rows"], msrc, "frame_rows")))
        nreg = int(reg["n"])
        cells.append(Cell(p, "sample_rows").n(COUNT(nreg), "value", Val(nreg, short(P_REGISTER), "line %d: n" % rl)))
        cells.append(Cell(p, "regions").n(COUNT(man["regions_in_sample"]), "value",
                                          Val(man["regions_in_sample"], msrc, "regions_in_sample")))
        cells.append(Cell(p, "locations").n(COUNT(man["units_in_sample"]), "value",
                                            Val(man["units_in_sample"], msrc, "units_in_sample")))
        b = man["background_rows"]["0"]
        c = Cell(p, "background_rows")
        c.n(COUNT(b["min"]), "min", Val(b["min"], msrc, jp("background_rows", "0", "min")))
        if b["min"] != b["max"]:
            c.t(NDASH).n(COUNT(b["max"]), "max", Val(b["max"], msrc, jp("background_rows", "0", "max")))
            c.t(" (median ").n(MED(b["median"]), "median", Val(b["median"], msrc, jp("background_rows", "0", "median"))).t(")")
        cells.append(c)
        tp = META[p]["treeroute"]["pairs"]
        cells.append(Cell(p, "background_pairs").n(COUNT(tp), "value", Val(tp, short(p_model(p, "treeroute", "meta.json")), "pairs")))
        for L in ("feature", "variable"):
            d = PL[p][L]
            c = Cell(p, L)
            c.n(COUNT(d["players"]), "players", Val(d["players"], psrc, jp(L, "players"))).t(" / ")
            c.n(COUNT(d["active"]), "J", Val(d["active"], psrc, jp(L, "active"))).t(" / ")
            nsz = len(d["structural_zero"])
            c.n(COUNT(nsz), "structural_zeros", Val(nsz, psrc, "len(" + jp(L, "structural_zero") + ")"))
            cells.append(c)
        rows.append(cells)
    add_table(tid, "", hdr[0], hdr[1], rows)
    notes = [plain_note(t) for t in blk(18, SUP_A + " Frame:", 4)]
    tmpl = blk(19, "{Problem}: variable level", 1)[0]
    for p in PROBS:
        psrc = short(p_compare(p, "per_lead.json"))
        szv, szf = PL[p]["variable"]["structural_zero"], PL[p]["feature"]["structural_zero"]
        c = Cell("note")
        fill(c, tmpl, {
            "Problem": PDISP[p],
            "nv": (COUNT(len(szv)), "count", Val(len(szv), psrc, "len(variable.structural_zero)"),
                   "structural_zeros:%s:variable" % p),
            "names_v": nlist(szv),
            "nf": (COUNT(len(szf)), "count", Val(len(szf), psrc, "len(feature.structural_zero)"),
                   "structural_zeros:%s:feature" % p),
            "names_f": nlist(szf),
        })
        notes.append(note_line(tid, c))
    add_notes(notes)


def sexact_record(p, m):
    if m == "treeroute":
        src = short(p_gates(p))
        g = GATES[p]["gates"]["E8_predictions"]["values"]
        base = ["gates", "E8_predictions", "values"]
        return {"rows": Val(g["rows_checked"], src, jp(*(base + ["rows_checked"]))),
                "pre": Val(g["pre_bit_equal"], src, jp(*(base + ["pre_bit_equal"]))),
                "clipped": Val(g["arm_bit_equal"], src, jp(*(base + ["arm_bit_equal"]))),
                "max": Val(g["max_abs_pre"], src, jp(*(base + ["max_abs_pre"])))}
    if m == "rival_ridge" and p in RIDGE4:
        ex = RIDGEX[p]
        src = short(p_model(p, m, "ridge_shap_exactness.json"))
        clipped = Val(ex["raw"]["bit_equal_rows"], src, "raw.bit_equal_rows")
    else:
        ex = EXACT[p][m]
        src = short(p_model(p, m, "exactness.json"))
        clipped = Val(ex["raw"]["bit_equal_rows"], src, "raw.bit_equal_rows") if "raw" in ex else None
    need(ex["pass"] is True, "the S-EXACT record of %s %s did not pass" % (p, m))
    return {"rows": Val(ex["rows"], src, "rows"), "pre": Val(ex["bit_equal_rows"], src, "bit_equal_rows"),
            "clipped": clipped, "max": Val(ex["max_abs_diff"], src, "max_abs_diff")}


def build_s320():
    tid = "S3.20"
    add_text([blk(20, "**Table S3.20 (post hoc).**", 1)[0]])
    hdr = blk(21, "| Problem | Model | Rows checked", 2)
    rows = []
    for p in PROBS:
        for m in dsort(PL[p]["models"]):
            rk = p + ":" + m
            rec = sexact_record(p, m)
            msrc = short(p_model(p, m, "meta.json"))
            mt = META[p][m]
            ridge4 = (m == "rival_ridge" and p in RIDGE4)
            cells = [Cell().t(PDISP[p]), Cell().t(MINL[m] + (SUP_B if ridge4 else ""))]
            cells.append(Cell(rk, "rows_checked").n(COUNT(rec["rows"].x), "value", rec["rows"]))
            c = Cell(rk, "bit_identical").n(COUNT(rec["pre"].x), "pre", rec["pre"]).t(" / ")
            if rec["clipped"] is not None:
                c.n(COUNT(rec["clipped"].x), "clipped", rec["clipped"])
            else:
                c.t(NDASH)
            cells.append(c)
            cells.append(Cell(rk, "max_abs_diff").n(SCI2(rec["max"].x), "value", rec["max"]))
            if m == "treeroute":
                e8 = GATES[p]["gates"]["E8_predictions"]["values"]
                if e8["bit_identical"] is True:
                    need(rec["pre"].x == rec["rows"].x and rec["clipped"].x == rec["rows"].x, "E8 counts of %s" % p)
                    cells.append(Cell().t(bconst("bit-identical")))
                else:
                    need(e8["within_relative_tolerance"] is True and e8["rows_outside_tolerance"] == 0,
                         "treeroute's E8 of %s is outside the D8 tolerance" % p)
                    c = Cell(rk, "s_exact").t(qconst("within the D8 tolerance" + SUP_C + " (largest relative difference "))
                    c.n(SCI2(e8["max_rel_pre"]), "max_rel",
                        Val(e8["max_rel_pre"], short(p_gates(p)), "gates.E8_predictions.values.max_rel_pre")).t(")")
                    cells.append(c)
            else:
                need(rec["pre"].x == rec["rows"].x and (rec["clipped"] is None or rec["clipped"].x == rec["rows"].x),
                     "S-EXACT of %s %s is not bit-identical" % (p, m))
                cells.append(Cell().t(bconst("bit-identical")))
            c = Cell(rk, "additivity")
            c.n(SCI2(mt["max_abs_additivity_error"]), "feature",
                Val(mt["max_abs_additivity_error"], msrc, "max_abs_additivity_error")).t(" / ")
            c.n(SCI2(mt["max_abs_additivity_error_variable"]), "variable",
                Val(mt["max_abs_additivity_error_variable"], msrc, "max_abs_additivity_error_variable"))
            cells.append(c)
            cells.append(Cell(rk, "s_zero_violations").n(COUNT(mt["structural_zero_violations"]), "value",
                                                          Val(mt["structural_zero_violations"], msrc,
                                                              "structural_zero_violations")))
            cells.append(Cell().t(bconst("all passed")))
            if m == "treeroute":
                g = TR_GUARD_S320  # version 3 (V3-6): taken from the spec's cell rule of 4.4
            else:
                gp = mt["guard"]["passed"]
                need(isinstance(gp, bool), "guard.passed of %s %s" % (p, m))
                g = bconst("passed") if gp else bconst("failed" + SUP_D)
            cells.append(Cell().t(g))
            rows.append(cells)
    add_table(tid, "", hdr[0], hdr[1], rows)
    nt = blk(22, SUP_A + " Rows checked:", 4)
    mapping = {}
    for p in RIDGE4:
        ex = EXACT[p]["rival_ridge"]
        src = short(p_model(p, "rival_ridge", "exactness.json"))
        mapping["bit_" + p] = (COUNT(ex["bit_equal_rows"]), "bit_equal_rows", Val(ex["bit_equal_rows"], src, "bit_equal_rows"),
                               "ridge_copy:" + p)
        mapping["rows_" + p] = (COUNT(ex["rows"]), "rows", Val(ex["rows"], src, "rows"), "ridge_copy:" + p)
    c = Cell("note")
    fill(c, nt[1], mapping)
    add_notes([plain_note(nt[0]), note_line(tid, c), plain_note(nt[2]), plain_note(nt[3])])


S321_ROWS = [
    ("arm", ARM_FIRST, ARM_WHAT),  # version 3 (V3-6): taken from the spec's first row of 4.5
    ("E1", "E1", "engine code hash equals the run manifest's"),
    ("E2", "E2", "library versions and Python equal the manifest's"),
    ("E0", "E0", "the engine's RAM pre-flight predicts no refusal"),
    ("E3a", "E3a", E3A_WHAT),  # version 3 (V3-6): taken from the spec's E3a row
    ("E3m", "E3m", E3M_WHAT),  # version 3 (V3-6): taken from the spec's E3m row
    ("E3", "E3", E3_WHAT),  # version 3 (V3-6): taken from the spec's E3 row
    ("E4", "E4", "training rows: count and row-key hash"),
    ("E5", "E5" + SUP_A, E5_WHAT),  # version 4 (V4-6): taken from the spec's E5ᵃ row
    ("E5a", "E5a", "arcsine arm only: its identity-link twin is bit-identical on every checked row"),
    ("E6", "E6", E6_WHAT),  # version 3 (V3-6): taken from the spec's E6 row
    ("E7", "E7", "error-weighted arm only: the error-weight model equals its record"),
    ("E9", "E9", "captured router coefficients reproduce the engine's kernel bit for bit"),
    ("E8", "E8", E8_WHAT),  # version 4 (V4-11): taken from the spec's E8 row
    ("E10", "E10", E10_WHAT),  # version 2 (C6): taken from the spec's E10 row
]


def s321_cell(p, gid):
    G, R = GATES[p]["gates"], GATES[p]["result"]
    src = short(p_gates(p))
    if gid == "arm":
        ans = {"plain": ANS_PLAIN, "corrector": qconst("corrected answers")}  # version 4 (V4-5): ANS_PLAIN from the rule
        rt = {"per_unit": qconst("per-location router"), "region": qconst("region router"),
              "neighbour": qconst("neighbour router")}
        need(R["table_kind"] in ans and R["kind"] in rt and isinstance(R["weighted"], bool), "the adopted arm of %s" % p)
        wt = qconst("error-weighted") if R["weighted"] else qconst("uniformly weighted")
        return Cell().t(LINKD[link_of(R["link"])] + ", " + ans[R["table_kind"]] + ", " + wt + "; " + rt[R["kind"]])
    k = gate_key(G, gid)
    if gid in ("E1", "E2", "E3a", "E3", "E6"):
        need(k is not None and G[k]["pass"] is True, "gate %s of %s" % (gid, p))
        return Cell().t(bconst("passed"))
    if gid == "E0":
        ig = G[k]["values"]["ignored"]
        need(isinstance(ig, bool), "E0 ignored of %s" % p)
        return Cell().t(bconst("passed (warning overridden)") if ig else bconst("passed"))
    if gid == "E3m":
        if k is None:
            return Cell().t(bconst("not used (no moved file)"))
        nfl = len(G[k]["values"]["files"])
        c = Cell("E3m", p).t(qconst("passed (")).n(COUNT(nfl), "files", Val(nfl, src, "len(" + jp("gates", k, "values", "files") + ")"))
        return c.t(qconst(" file)") if nfl == 1 else qconst(" files)"))
    if gid == "E4":
        r0 = G[k]["values"]["rows"][0]
        return Cell("E4", p).t(qconst("passed (")).n(COUNT(r0), "rows", Val(r0, src, jp("gates", k, "values", "rows", 0))).t(qconst(" rows)"))
    if gid == "E5":
        return Cell().t(bconst("differs (informational)"))
    if gid == "E5a":
        if k is None:
            return Cell().t(bconst("not applicable"))
        v = G[k]["values"]
        need(v["pre_bit_equal"] == v["rows_checked"] and v["arm_bit_equal"] == v["rows_checked"], "E5a of %s" % p)
        c = Cell("E5a", p).t("passed (").n(COUNT(v["pre_bit_equal"]), "bit_equal",
                                            Val(v["pre_bit_equal"], src, jp("gates", k, "values", "pre_bit_equal")))
        c.t(qconst(" of ")).n(COUNT(v["rows_checked"]), "rows", Val(v["rows_checked"], src, jp("gates", k, "values", "rows_checked")))
        return c.t(" rows)")
    if gid == "E7":
        return Cell().t(bconst("passed") if k is not None else bconst("not applicable"))
    if gid == "E9":
        v = G[k]["values"]
        rp = v["region_proof"]
        c = Cell("E9", p).t(qconst("passed (all ")).n(COUNT(v["fits_captured"]), "fits",
                                                       Val(v["fits_captured"], src, jp("gates", k, "values", "fits_captured")))
        if rp is None:
            return c.t(qconst(" fits)"))
        need(rp["answers_equal"] is True and rp["eta_ours_equal"] is True and rp["eta_store_equal"] is True
             and rp["errors"] == [], "E9 region proof of %s" % p)
        c.t(qconst(" region fits; region proof on ")).n(COUNT(rp["score_rows"]), "score_rows",
                                                         Val(rp["score_rows"], src, jp("gates", k, "values", "region_proof", "score_rows")))
        c.t(qconst(" score rows and ")).n(COUNT(rp["background_rows"]), "background_rows",
                                           Val(rp["background_rows"], src, jp("gates", k, "values", "region_proof", "background_rows")))
        return c.t(qconst(" background rows)"))
    if gid == "E8":
        v = G[k]["values"]
        pre = Val(v["pre_bit_equal"], src, jp("gates", k, "values", "pre_bit_equal"))
        rows = Val(v["rows_checked"], src, jp("gates", k, "values", "rows_checked"))
        if v["bit_identical"] is True:
            c = Cell("E8", p).t(qconst("bit-identical (")).n(COUNT(pre.x), "bit_equal", pre).t(" of ")
            return c.n(COUNT(rows.x), "rows", rows).t(" rows)")
        c = Cell("E8", p).n(COUNT(pre.x), "bit_equal", pre).t(" of ").n(COUNT(rows.x), "rows", rows)
        c.t(qconst(" rows bit-identical; the rest within the D8 tolerance (largest relative difference "))
        c.n(SCI2(v["max_rel_pre"]), "max_rel", Val(v["max_rel_pre"], src, jp("gates", k, "values", "max_rel_pre")))
        return c.t(")")
    if gid == "E10":
        v = G[k]["values"]
        if "rows_x_trees" in v:
            rx = v["rows_x_trees"]
            c = Cell("E10", p).t("passed (").n(COUNT(rx[0]), "rows", Val(rx[0], src, jp("gates", k, "values", "rows_x_trees", 0)))
            c.t(qconst(" rows, ")).n(COUNT(rx[1]), "trees", Val(rx[1], src, jp("gates", k, "values", "rows_x_trees", 1)))
            return c.t(qconst(" trees)"))
        c = Cell("E10", p).t(qconst("passed (every sampled location of the "))
        c.n(COUNT(v["regions"]), "regions", Val(v["regions"], src, jp("gates", k, "values", "regions")))
        return c.t(qconst(" regions)"))
    stop("an unknown gate row %s" % gid)


def build_s321():
    tid = "S3.21"
    add_text([blk(23, "**Table S3.21 (post hoc).**", 1)[0]])
    hdr = blk(24, "| Gate | What it checks |", 2)
    rows = []
    for gid, first, what in S321_ROWS:
        cells = [Cell().t(bconst(first)), Cell().t(bconst(what))]
        for p in PROBS:
            cells.append(s321_cell(p, gid))
        rows.append(cells)
    add_table(tid, "", hdr[0], hdr[1], rows)
    add_notes([plain_note(t) for t in blk(25, SUP_A + " E5 is informational", 2)])


def build_s322():
    A = RESULTS
    tid = "S3.22"
    add_text([blk(26, "**Table S3.22 (post hoc).**", 1)[0]])
    hdr = blk(27, "| Quantity | PM2.5 |", 2)

    def rivals(p):
        return [m for m in dsort(AW4[p]["models_in_main_set"]) if m != "treeroute"]

    def q_link(p):
        return Cell().t(LINKD[link_of(AW4[p]["reference_link"])])

    def q_main(p):
        return Cell().t(bconst("treeroute v1 only" + SUP_A) if p == "fire" else mlist(AW4[p]["models_in_main_set"]))

    def q_cross(p):
        return Cell().t(mlist(AW4[p]["cross_link_models"]))

    def q_decl(p):
        return Cell().t(mlist(AW4[p]["declined_models"]))

    def q_w(p):
        if p == "fire":
            need(isnan(AW4[p]["kendall_w"]["value"]), "fire's W is not NaN")
            return Cell("kendall_w", p).n("undefined", "value", Val(AW4[p]["kendall_w"]["value"],
                                                                    short(p_compare(p, "AW4_main_row.json")), "kendall_w.value"))
        return w_ci2(Cell("kendall_w", p), *awobj(p, "kendall_w"), D=PL[p]["draws"])

    def q_sp_each(p):
        if p == "fire":
            return Cell().t(NDASH)
        c = Cell("spearman_per_rival", p)
        for i, m in enumerate(rivals(p)):
            if i:
                c.t("; ")
            v = pair_val(p, "variable", m, "treeroute", "spearman_top20_union", "value")
            c.t(MINL[m] + " ").n(NUM2(v.x), m, v)
        return c

    K = "treeroute_vs_same_link_rivals_median_spearman_top20_union"

    def q_sp_med(p):
        if p == "fire":
            return Cell().t(NDASH)
        return w_ci2(Cell("spearman_median", p), *awobj(p, K), D=PL[p]["draws"])

    def q_sp_range(p):
        if p == "fire":
            return Cell().t(NDASH)
        src = short(p_compare(p, "AW4_main_row.json"))
        rg = AW4[p][K]["range"]
        c = Cell("spearman_range", p).n(NUM2(rg[0]), "min", Val(rg[0], src, jp(K, "range", 0))).t(" to ")
        return c.n(NUM2(rg[1]), "max", Val(rg[1], src, jp(K, "range", 1)))

    def q_rbo(p):
        if p == "fire":
            return Cell().t(NDASH)
        c = w_ci2(Cell("rbo_vs_consensus", p), *awobj(p, "rbo_vs_consensus_p0.9"), D=PL[p]["draws"])
        if p == "pm25":
            c.t(SUP_B)
        return c

    def q_top3(p):
        if p == "fire":
            return Cell().t(nlist([e[0] for e in A["problems"]["fire"]["main_row"]["treeroute_top3"]]) + DAGGER)
        return Cell().t(nlist(AW4[p]["treeroute_top3"]))

    def q_cons(p):
        if p == "fire":
            return Cell().t(NDASH)
        return Cell().t(nlist(AW4[p]["consensus_top3"]))

    def label(p, c):
        if "own history" in MISSING[p]:
            c.t(" " + FAM_LABEL["own history"])
        return c

    def q_oh_tr(p):
        if p == "fire":
            mr = A["problems"]["fire"]["main_row"]
            c = w_ci2(Cell("own_history_treeroute", p), *aobj(mr["own_history_share_treeroute"],
                                                             ["problems", "fire", "main_row", "own_history_share_treeroute"]),
                      D=PL[p]["draws"])
            return c.t(DAGGER)
        return label(p, w_ci2(Cell("own_history_treeroute", p), *awobj(p, "own_history_share_treeroute"), D=PL[p]["draws"]))

    def q_oh_each(p):
        if p == "fire":
            return Cell().t(NDASH)
        c = Cell("own_history_per_rival", p)
        fsrc = short(p_compare(p, "families.parquet"))
        for i, m in enumerate(rivals(p)):
            if i:
                c.t("; ")
            x = FAMP[p][(m, "own history")]
            c.t(MINL[m] + " ").n(NUM2(x), m, Val(x, fsrc, "model=%s; family=own history; column=share" % m))
        return label(p, c)

    def q_oh_med(p):
        if p == "fire":
            return Cell().t(NDASH)
        return label(p, w_ci2(Cell("own_history_median_rivals", p), *awobj(p, "own_history_share_median_rival"),
                              D=PL[p]["draws"]))

    spec_rows = [
        ("Link of the main set", q_link), ("Main set", q_main), (CROSS_LABEL, q_cross),  # version 2 (C5)
        ("Rivals declined by their skill guard", q_decl), ("Kendall's W of the main set [95% CI]", q_w),
        ("Spearman of treeroute v1 with each same-link rival", q_sp_each), ("Median of those [95% CI]", q_sp_med),
        ("Range (lowest to highest)", q_sp_range), ("RBO with the rivals' consensus, p = 0.9 [95% CI]", q_rbo),
        ("treeroute v1's top 3", q_top3), ("Consensus top 3", q_cons),
        ("Own-history share, treeroute v1 [95% CI]", q_oh_tr), ("Own-history share of each same-link rival", q_oh_each),
        ("Own-history share, median of the rivals" + SUP_C + " [95% CI]", q_oh_med),
    ]
    rows = []
    for first, fn in spec_rows:
        rows.append([Cell().t(bconst(first))] + [fn(p) for p in PROBS])
    add_table(tid, "", hdr[0], hdr[1], rows)
    add_notes([plain_note(t) for t in blk(28, SUP_A + " Burned fraction", 5)])


def build_aw3(p, nn):
    A = RESULTS
    tid = "S3." + nn
    pl = PL[p]
    D = pl["draws"]
    models = dsort(pl["models"])
    plsrc = short(p_compare(p, "per_lead.json"))
    isrc = short(p_compare(p, "importance.parquet"))
    fsrc = short(p_compare(p, "families.parquet"))
    asrc = short(P_A)
    g_clause = bconst("; and the arcsine-link models' top 10 on their rows with a forecast above 0 (g)") if p in ("fire", "coral") else ""
    extra_src = EXTRA_SRC_NDVI if p == "ndvi" else ""  # version 3 (V3-3): taken from the spec's bullet of 4.7
    extra_rulings = {"ndvi": bconst(", BB3"), "defo": bconst(", BB4"), "coral": bconst(", BB4")}.get(p, "")
    shares_sentence = SHARES_G if p in ("fire", "coral") else SHARES_NOG  # version 2 (C1): the tables with panel g
    cap = Cell()
    fill(cap, blk(29, "**Table S3.{nn} (post hoc).**", 1)[0],
         {"nn": nn, "Problem": PDISP[p], "g_clause": g_clause, "p": p, "extra_src": extra_src,
          "extra_rulings": extra_rulings, "shares_sentence": shares_sentence})
    add_text([cap.text()])
    # panels a and b
    hdr_a = blk(32, "| Pair | Link |", 2)
    base_cells = split_header(hdr_a[0])
    for L, lab_i, lab_p in (("variable", 30, "**a. Variable level"), ("feature", 31, "**b. Feature level")):
        add_text([blk(lab_i, lab_p, 1)[0]])
        stats = ["spearman", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10", "rbo_p0.9",
                 "rbo_p0.95", "tvd", "tvd_family", "sign_agreement_top10"]
        hc = list(base_cells)
        j20 = pl[L]["active"] >= 200
        if L == "variable":
            need(not j20, "a variable-level top-20 Jaccard, which the spec does not place")
            header, sep = hdr_a[0], hdr_a[1]
        else:
            i = hc.index("Family-share distance (TV)")
            hc[i] = "Family-share distance (TV)" + SECTION
            if j20:
                hc.insert(hc.index("Jaccard top 10") + 1, bconst("Jaccard top 20"))
                stats.insert(stats.index("jaccard_top10") + 1, "jaccard_top20")
            header = "| " + " | ".join(hc) + " |"
            sep = "|" + "---|" * len(hc)
        rows = []
        for a, b in itertools.combinations(models, 2):
            x, y = sorted([a, b])
            key = x + "|" + y
            pt = pair_text(a, b) + (DDAGGER if (p == "ndvi" and "rival_bardl_h1" in (a, b)) else "")
            lab = pair_row(p, L, x, y, "spearman")["pair_label"]
            lab = link_cell(lab)  # version 3 (V3-6): P in place of M
            cells = [Cell().t(pt), Cell().t(lab)]
            for s in stats:
                c = Cell(key, s)
                if s == "sign_agreement_top10":
                    ao = A["problems"][p]["levels"][L]["pairs"][key]["sign_agreement"]
                    ab = ["problems", p, "levels", L, "pairs", key, "sign_agreement"]
                    w_sign(c, pair_val(p, L, x, y, s, "value"), pair_val(p, L, x, y, s, "signs_compared"),
                           Val(ao["ci_low"], asrc, jp(*(ab + ["ci_low"]))), Val(ao["ci_high"], asrc, jp(*(ab + ["ci_high"]))),
                           Val(ao["n_finite"], asrc, jp(*(ab + ["n_finite"]))), D)
                else:
                    Ls = "variable" if s == "tvd_family" else L
                    w_ci2(c, pair_val(p, Ls, x, y, s, "value"), pair_val(p, Ls, x, y, s, "ci_low"),
                          pair_val(p, Ls, x, y, s, "ci_high"), pair_val(p, Ls, x, y, s, "finite_replicates"), D)
                cells.append(c)
            rows.append(cells)
        add_table(tid, "a" if L == "variable" else "b", header, sep, rows)
    # panel c
    add_text([blk(33, "**c. Agreement within the main set", 1)[0]])
    hdr_c = blk(34, "| Statistic | Variable level | Feature level |", 2)
    rows = []
    for rkey, first, field in (("kendall_w", "Kendall's W of the main set [95% CI]", "kendall_w_main_set"),
                               ("mean_pairwise_spearman", "Mean pairwise Spearman of the main set [95% CI]",
                                "mean_pairwise_spearman_main_set")):
        cells = [Cell().t(bconst(first))]
        for L in ("variable", "feature"):
            o = pl[L][field]
            need(isinstance(o["ci"], list) and len(o["ci"]) == 2, "an interval of %s %s" % (p, field))
            c = Cell(rkey, L)
            w_ci2(c, Val(o["value"], plsrc, jp(L, field, "value")), Val(o["ci"][0], plsrc, jp(L, field, "ci", 0)),
                  Val(o["ci"][1], plsrc, jp(L, field, "ci", 1)),
                  Val(o["finite_replicates"], plsrc, jp(L, field, "finite_replicates")), D)
            if p == "fire":
                need(isnan(o["value"]) and o["finite_replicates"] == 0, "fire's %s is defined" % field)
                c.t(SUP_A)
            cells.append(c)
        rows.append(cells)
    for m in models:
        cells = [Cell().t(qconst("Stability under region resampling: ") + MINL[m])]
        for L in ("variable", "feature"):
            xv = pl[L]["stability_under_region_resampling"][m]
            cells.append(Cell("stability:" + m, L).n(NUM2(xv), "value",
                                                     Val(xv, plsrc, jp(L, "stability_under_region_resampling", m))))
        rows.append(cells)
    add_table(tid, "c", hdr_c[0], hdr_c[1], rows)
    # panels d and e
    for L, lab_i, lab_p, last in (("variable", 35, "**d. Variable level", "Nonzero variables"),
                                  ("feature", 36, "**e. Feature level", "Nonzero players")):
        add_text([blk(lab_i, lab_p, 1)[0]])
        hn = [(bconst("BARDL" + DDAGGER) if (p == "ndvi" and m == "rival_bardl_h1") else MHDR[m]) for m in models]
        header = "| Rank | " + " | ".join(hn) + " |"
        sep = "|" + "---|" * (len(models) + 1)
        rk = {m: ranking(p, L, m) for m in models}
        for m in models:
            need(len(rk[m]) >= 10, "fewer than 10 active players for %s %s %s" % (p, L, m))
        rows = []
        for k in range(1, 11):
            cells = [Cell().t(str(k))]
            for m in models:
                r = rk[m][k - 1]
                c = Cell("rank_%d" % k, m)
                w_top(c, r["player"], Val(r["share"], isrc, "level=%s; model=%s; player=%s; column=share" % (L, m, r["player"])))
                cells.append(c)
            rows.append(cells)
        cells = [Cell().t(bconst(last))]
        for m in models:
            xv = pl[L]["nonzero_players"][m]
            cells.append(Cell("nonzero", m).n(COUNT(xv), "count", Val(xv, plsrc, jp(L, "nonzero_players", m))))
        rows.append(cells)
        add_table(tid, "d" if L == "variable" else "e", header, sep, rows)
    # panel f
    add_text([blk(37, "**f. Family shares", 1)[0]])
    header = "| Family | " + " | ".join(MHDR[m] for m in models) + " |"
    sep = "|" + "---|" * (len(models) + 1)
    rows = []
    for f in FAMS:
        cells = [Cell().t(FAM_ROW[f])]
        for m in models:
            xv = FAMP[p][(m, f)]
            # version 2 (G1): part `share`, as the other shares printed without an interval
            c = Cell(f, m).n(PCT1(xv), "share", Val(xv, fsrc, "model=%s; family=%s; column=share" % (m, f)))
            if f in MISSING[p]:
                c.t(" " + FAM_LABEL[f])
            cells.append(c)
        rows.append(cells)
    add_table(tid, "f", header, sep, rows)
    # panel g
    nzf = pl["nonzero_forecast_rows"]
    has_g = p in ("fire", "coral")
    need(bool(nzf) == has_g, "nonzero_forecast_rows of %s does not fit the spec's panel g" % p)
    if has_g:
        add_text([blk(38, "**g. Arcsine-link models", 1)[0]])
        gm = dsort(list(nzf.keys()))
        header = "| Rank | " + " | ".join(MHDR[m] for m in gm) + " |"
        sep = "|" + "---|" * (len(gm) + 1)
        rows = []
        for m in gm:
            need(len(nzf[m]["top10"]) == 10, "a nonzero-forecast top 10 that is not 10 long")
        for k in range(1, 11):
            cells = [Cell().t(str(k))]
            for m in gm:
                e = nzf[m]["top10"][k - 1]
                c = Cell("rank_%d" % k, m)
                w_top(c, e[0], Val(e[1], plsrc, jp("nonzero_forecast_rows", m, "top10", k - 1, 1)))
                cells.append(c)
            rows.append(cells)
        cells = [Cell().t(bconst("Rows with a forecast above 0"))]
        for m in gm:
            xv = nzf[m]["rows"]
            cells.append(Cell("rows", m).n(COUNT(xv), "count", Val(xv, plsrc, jp("nonzero_forecast_rows", m, "rows"))))
        rows.append(cells)
        add_table(tid, "g", header, sep, rows)
    # notes
    notes = []
    if p == "fire":
        notes += [plain_note(t) for t in blk(39, SUP_A + " The main set is treeroute v1 alone", 1)]
    notes += [plain_note(t) for t in blk(40, "Sign agreement:", 2)]
    if p == "ndvi":
        tmpl = blk(41, DDAGGER + " BARDL reads", 1)[0]
        msrc = short(P_MAXIMA)
        jv, jf = pl["variable"]["active"], pl["feature"]["active"]
        nzv, nzf_ = pl["variable"]["nonzero_players"]["rival_bardl_h1"], pl["feature"]["nonzero_players"]["rival_bardl_h1"]
        mp = {
            "z_var": (COUNT(jv - nzv), "number", Val(jv - nzv, plsrc, "variable.active - variable.nonzero_players.rival_bardl_h1",
                                                     stored=[jv, nzv]), "z_var"),
            "j_var": (COUNT(jv), "number", Val(jv, plsrc, "variable.active"), "j_var"),
            "z_feat": (COUNT(jf - nzf_), "number", Val(jf - nzf_, plsrc, "feature.active - feature.nonzero_players.rival_bardl_h1",
                                                       stored=[jf, nzf_]), "z_feat"),
            "j_feat": (COUNT(jf), "number", Val(jf, plsrc, "feature.active"), "j_feat"),
        }
        for s in ["jaccard_top5", "jaccard_top10", "jaccard_top20", "rho20", "rbo090", "rbo095"]:
            mx = MAXI[s]
            need(mx["problem"] == "ndvi" and mx["level"] in ("variable", "feature"), "a maxima line of %s" % s)
            sv = float(mx["spread"])
            mp["m_" + s] = (NUM2(sv), "number", Val(sv, msrc, "line %d: spread" % mx["line"]), "m_" + s)
            pa, pb = mx["pair"].split("|")
            mp["at_" + s] = ("variable level" if mx["level"] == "variable" else "feature level") + ", " + pair_text(pa, pb)
        mx = MAXI["jaccard_top5"]
        v1, v3 = float(mx["v1"]), float(mx["v3"])
        mp["ex_base"] = (NUM2(v1), "number", Val(v1, msrc, "line %d: value 1" % mx["line"]), "ex_base")
        mp["ex_desc"] = (NUM2(v3), "number", Val(v3, msrc, "line %d: value 3" % mx["line"]), "ex_desc")
        c = Cell("note")
        fill(c, tmpl, mp)
        notes.append(note_line(tid, c))
    notes += [plain_note(t) for t in blk(42, SECTION + " Families are sums", 2)]
    if p in ("fire", "coral"):
        notes += [plain_note(t) for t in blk(43, "Panel g:", 1)]
    add_notes(notes)


def build_s328():
    A = RESULTS
    tid = "S3.28"
    asrc = short(P_A)
    add_text([blk(44, "**Table S3.28 (post hoc; sensitivity).**", 1)[0]])
    hdr = blk(47, "| Statistic | PM2.5 | NDVI | Burned fraction |", 2)
    for L, lab_i, lab_p in (("variable", 45, "**a. Variable level"), ("feature", 46, "**b. Feature level")):
        add_text([blk(lab_i, lab_p, 1)[0]])
        rows = []
        first = "Variables in the pair's J" if L == "variable" else "Players in the pair's J"
        cells = [Cell().t(bconst(first))]
        for p in B1P:
            q = A["b1"][p][L]["pair_main_b1"]["n_J"]["value"]
            cells.append(Cell("n_J", p).n(COUNT(q), "count", Val(q, asrc, jp("b1", p, L, "pair_main_b1", "n_J", "value"))))
        rows.append(cells)
        cells = [Cell().t(bconst("Nonzero in the B1 run"))]
        for p in B1P:
            q = A["b1"][p][L]["importance"]["n_nonzero"]["value"]
            cells.append(Cell("n_nonzero", p).n(COUNT(q), "count", Val(q, asrc, jp("b1", p, L, "importance", "n_nonzero", "value"))))
        rows.append(cells)
        for key, first in (("spearman_J", "Spearman over J"), ("spearman_top20_union", "Spearman, top-20 union"),
                           ("kendall_tau_b", "Kendall's tau-b"), ("jaccard_top5", "Jaccard top 5"),
                           ("jaccard_top10", "Jaccard top 10"), ("jaccard_top20", "Jaccard top 20"),
                           ("rbo_p090", "RBO, p = 0.9"), ("rbo_p095", "RBO, p = 0.95"),
                           ("tv_shares", "Share distance (TV)")):
            objs = [A["b1"][p][L]["pair_main_b1"][key] for p in B1P]
            if key == "jaccard_top20" and all(o is None for o in objs):
                continue
            cells = [Cell().t(bconst(first))]
            for p, o in zip(B1P, objs):
                if o is None:
                    need(key == "jaccard_top20", "a null B1 statistic %s of %s" % (key, p))
                    cells.append(Cell().t(NDASH))
                else:
                    cells.append(w_ci2(Cell(key, p), *aobj(o, ["b1", p, L, "pair_main_b1", key]), D=PL[p]["draws"]))
            rows.append(cells)
        cells = [Cell().t(bconst("Family-share distance (TV)" + ("" if L == "variable" else SECTION)))]
        for p in B1P:
            o = A["b1"][p]["variable"]["pair_main_b1"]["tv_family_shares"]
            cells.append(w_ci2(Cell("tv_family_shares", p), *aobj(o, ["b1", p, "variable", "pair_main_b1", "tv_family_shares"]),
                               D=PL[p]["draws"]))
        rows.append(cells)
        cells = [Cell().t(bconst("Sign agreement, top-10 union"))]
        for p in B1P:
            o = A["b1"][p][L]["pair_main_b1"]["sign_agreement"]
            cells.append(w_ci2(Cell("sign_agreement", p), *aobj(o, ["b1", p, L, "pair_main_b1", "sign_agreement"]), D=PL[p]["draws"]))
        rows.append(cells)
        cells = [Cell().t(bconst("Signs determined in both runs / of those, agreeing"))]
        for p in B1P:
            q = A["b1"][p][L]["pair_main_b1"]
            nd, na = q["sign_n_determined"]["value"], q["sign_n_agree"]["value"]
            c = Cell("sign_counts", p).n(COUNT(nd), "determined", Val(nd, asrc, jp("b1", p, L, "pair_main_b1", "sign_n_determined", "value")))
            c.t(" / ").n(COUNT(na), "agree", Val(na, asrc, jp("b1", p, L, "pair_main_b1", "sign_n_agree", "value")))
            cells.append(c)
        rows.append(cells)
        add_table(tid, "a" if L == "variable" else "b", hdr[0], hdr[1], rows)
    add_notes([plain_note(t) for t in blk(48, NDASH + ": not defined", 2)])


def b1_header(first):
    return "| " + first + " | PM2.5 | NDVI | Burned fraction |", "|---|---|---|---|"


def build_s329():
    A = RESULTS
    tid = "S3.29"
    asrc = short(P_A)
    add_text([blk(49, "**Table S3.29 (post hoc; sensitivity).**", 1)[0]])
    # a
    add_text([blk(50, "**a. Variable level: the B1 run's family shares", 1)[0]])
    rows = []
    for p in B1P:
        need(not MISSING[p], "a B1 problem with a family without a variable")
    for f in FAMS:
        cells = [Cell().t(FAM_ROW[f])]
        for p in B1P:
            o = A["b1"][p]["variable"]["families"][FAM_A[f]]
            cells.append(w_ci2(Cell(FAM_A[f], p), *aobj(o, ["b1", p, "variable", "families", FAM_A[f]]), D=PL[p]["draws"], fmt=PCT1))
        rows.append(cells)
    h, s = b1_header(bconst("Family"))
    add_table(tid, "a", h, s, rows)
    # b
    add_text([blk(51, "**b. Variable level: the B1 run's top 3", 1)[0]])
    rows = []
    cells = [Cell().t(bconst("Top 3 (share)"))]
    for p in B1P:
        t3 = A["b1"][p]["variable"]["top3"]
        need(len(t3) == 3, "B1's top 3 of %s" % p)
        c = Cell("top3", p)
        for i, e in enumerate(t3):
            if i:
                c.t(", ")
            w_top(c, e[0], Val(e[1], asrc, jp("b1", p, "variable", "top3", i, 1)), part="share_%d" % (i + 1))
        cells.append(c)
    rows.append(cells)
    cells = [Cell().t(bconst("Own-history share [95% CI]"))]
    for p in B1P:
        o = A["b1"][p]["variable"]["own_history_share"]
        cells.append(w_ci2(Cell("own_history_share", p), *aobj(o, ["b1", p, "variable", "own_history_share"]), D=PL[p]["draws"]))
    rows.append(cells)
    h, s = b1_header(bconst("Quantity"))
    add_table(tid, "b", h, s, rows)
    # c and d
    for L, lab_i, lab_p, panel in (("variable", 52, "**c. Variable level", "c"), ("feature", 53, "**d. Feature level", "d")):
        add_text([blk(lab_i, lab_p, 1)[0]])
        rows = []
        for p in B1P:
            need(len(A["b1"][p][L]["top10"]) == 10, "B1's top 10 of %s %s" % (p, L))
        for k in range(1, 11):
            cells = [Cell().t(str(k))]
            for p in B1P:
                e = A["b1"][p][L]["top10"][k - 1]
                cells.append(w_top(Cell("rank_%d" % k, p), e[0], Val(e[1], asrc, jp("b1", p, L, "top10", k - 1, 1))))
            rows.append(cells)
        h, s = b1_header(bconst("Rank"))
        add_table(tid, panel, h, s, rows)
    add_notes([plain_note(t) for t in blk(54, "Under B1 the month", 1)])


def build_s330():
    A = RESULTS
    tid = "S3.30"
    asrc = short(P_A)
    add_text([blk(55, "**Table S3.30 (post hoc; sensitivity).**", 1)[0]])
    add_text([blk(56, "**a. Background pairs and seconds", 1)[0]])
    hdr = blk(57, "| Problem | Background pairs |", 2)
    rows = []
    for p in ["pm25", "ndvi", "fire", "defo"]:
        lg = LOGB1[p]
        lsrc = short(p_log(p))
        rows.append([Cell().t(PDISP[p]),
                     Cell(p, "pairs").n(COUNT(lg["pairs"]), "value", Val(lg["pairs"], lsrc, "line %d: background pairs" % lg["setup_line"])),
                     Cell(p, "total_seconds").n(SECS(lg["total"]), "value", Val(lg["total"], lsrc, "line %d: total seconds" % lg["done_line"])),
                     Cell(p, "tree_shap_seconds").n(SECS(lg["tree"]), "value",
                                                    Val(lg["tree"], lsrc, "line %d: tree SHAP seconds" % lg["done_line"]))])
    add_table(tid, "a", hdr[0], hdr[1], rows)
    add_text([blk(60, "**b. Forest loss: the B1 run against the main run.**", 1)[0]])
    hdr = blk(61, "| Check | Result |", 2)
    I = A["b1"]["defo"]["identity"]
    base = ["b1", "defo", "identity"]
    rows = []
    for key, first in (("max_abs_diff_phi", "Largest absolute difference of the SHAP values, feature level (every row and player)"),
                       ("max_abs_diff_phiv", "Largest absolute difference of the SHAP values, variable level (every row and variable)")):
        rows.append([Cell().t(bconst(first)), Cell(key, "result").n(SCI2(I[key]), "value", Val(I[key], asrc, jp(*(base + [key]))))])
    for key, first in (("rows", "Rows, main run / B1 run"), ("players", "Players, main run / B1 run"),
                       ("variables", "Variables, main run / B1 run")):
        km, kb = "n_%s_main" % key, "n_%s_b1" % key
        c = Cell(key, "result").n(COUNT(I[km]), "main", Val(I[km], asrc, jp(*(base + [km])))).t(" / ")
        c.n(COUNT(I[kb]), "b1", Val(I[kb], asrc, jp(*(base + [kb]))))
        rows.append([Cell().t(bconst(first)), c])
    yn = []
    for k in ("same_rows", "same_players", "same_variables"):
        need(isinstance(I[k], bool), "identity %s is not a bool" % k)
        yn.append("yes" if I[k] else "no")
    rows.append([Cell().t(bconst("Same rows / players / variables")), Cell().t(" / ".join(yn))])
    add_table(tid, "b", hdr[0], hdr[1], rows)
    add_notes([plain_note(t) for t in blk(62, "Coral bleaching: B1 is not defined", 2)])


# ----------------------------------------------------------------------------------------------------------------------
# Assembly, validation and writing

def assemble():
    add_text([blk(3, "<!-- Draft tables of Supplement S3.13", 1)[0]])
    add_text([blk(4, "## Main text: Table 9", 1)[0]])
    build_table9()
    add_text([blk(5, "## Supplement S3.13: SHAP comparison", 1)[0]])
    build_s318()
    build_s319()
    build_s320()
    build_s321()
    build_s322()
    for p, nn in (("pm25", "23"), ("ndvi", "24"), ("fire", "25"), ("defo", "26"), ("coral", "27")):
        build_aw3(p, nn)
    add_text([blk(6, "## Supplement S3.13: treeroute v1's B1 sensitivity", 1)[0]])
    build_s328()
    build_s329()
    build_s330()
    out, entries, percell = [], [], []
    for bi, bl in enumerate(DOC):
        need(bl, "an empty block")
        if bi:
            out.append("")
        for ln in bl:
            out.append(ln.text)
            no = len(out)
            for c in ln.cells:
                ct = c.text()
                if c.toks:
                    percell.append((ct, [tk["printed"] for tk in c.toks]))
                for tk in c.toks:
                    entries.append({"line": no, "table": ln.table, "panel": ln.panel, "row": tk["row"],
                                    "column": tk["column"], "part": tk["part"], "printed": tk["printed"], "cell": ct,
                                    "source": tk["source"], "selector": tk["selector"], "stored": tk["stored"]})
    return out, entries, percell


def validate(out, entries, percell):
    for i, ln in enumerate(out, 1):
        need("\t" not in ln and "\r" not in ln and "\n" not in ln, "a tab or line break on line %d" % i)
        need(ln == ln.rstrip(" "), "a trailing space on line %d" % i)
        if not ln:
            need(i > 1 and out[i - 2] != "", "two blank lines at line %d" % i)
    need(out[0] != "" and out[-1] != "", "a blank first or last line")
    for e in entries:
        ln = out[e["line"] - 1]
        need(e["cell"] in ln, "an entry's cell is not on its line: %r" % e["cell"])
        need(e["printed"] in e["cell"], "an entry's printed token is not in its cell: %r" % e["printed"])
        need(e["table"] in ["9"] + ["S3.%d" % k for k in range(18, 31)], "a bad table id %r" % e["table"])
    # within a cell, the printed tokens appear in order
    for ct, toks in percell:
        pos = 0
        for t in toks:
            j = ct.find(t, pos)
            need(j >= 0, "tokens out of order in %r" % ct)
            pos = j + len(t)


def main():
    try:
        self_test()
        check_name_constants()
        check_link_rule()
        load_all()
        global RESULTS
        RESULTS = jload_strict(P_A)
        load_register()
        load_logs()
        load_maxima()
        checks()
        out, entries, percell = assemble()
        validate(out, entries, percell)
        text = "\n".join(out) + "\n"
        doc = {"tables_file": "tables.md", "spec": "OUT\\spec\\TABLE_SPEC.md", "entries": entries}
        cj = json.dumps(doc, ensure_ascii=False, indent=1, allow_nan=False) + "\n"
    except Stop as e:
        print("STOP: " + str(e))
        sys.exit(2)
    with open(TABLES_MD, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    with open(CELLS_JSON, "w", encoding="utf-8", newline="\n") as f:
        f.write(cj)
    with open(TABLES_MD, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    ntab = len([ln for ln in out if ln.startswith("**Table ")])
    print("tables.md: %d lines, sha256 %s" % (len(out), sha))
    print("cells.json: %d entries; tables: %d" % (len(entries), ntab))


RESULTS = None

if __name__ == "__main__":
    main()
