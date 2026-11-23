"""Writer main (S3.13 write-up, 2026-11-17): build the three staged files of the main-text part.

Run: py -3.9 -I -B build_main.py
Inputs (read only): the base copies in work/ (byte-for-byte copies of the live D/05_rivals.md and D/TABLE_NUMBERS.md,
made by stage_copy_main.py; SHA-256 checked again here), OUT/reconcile/tables_agreed.md (version 5; SHA-256 checked)
and OUT/reconcile/cells.json (every printed data number with its source, selector and stored value).
Outputs (under STAGE only):
  STAGE/paper/draft/tables/table_9.md   new: header comment + the Table 9 block of tables_agreed.md, byte for byte
  STAGE/paper/draft/05_rivals.md        Section 5.4 gains one paragraph (three sentences); one edit-history comment
  STAGE/paper/draft/TABLE_NUMBERS.md    one row for Table 9; one edit-history note in the closing paragraph
Every prose number is formatted ONCE from its stored double (cells.json, table 9 entries) and checked equal to the
printed string of Table 9; nothing is typed from a printout. Line endings LF, UTF-8 without BOM, as the inputs.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.dirname(STAGE)
WORK = os.path.join(HERE, "work")
TABLES = os.path.join(OUT, "reconcile", "tables_agreed.md")
CELLS = os.path.join(OUT, "reconcile", "cells.json")
TABLES_SHA = "d05a6856019d90cfe6d2c5aa798a57bc9f9f1f38bad76e5367d28753df3b467c"
BASES = {
    "05_rivals.md": ("paper__draft__05_rivals.md.base",
                     "c439966f79efcf9dc9c23362dfa389f1dca6b3d65dd6871e53b8540b39b2fb59"),
    "TABLE_NUMBERS.md": ("paper__draft__TABLE_NUMBERS.md.base",
                         "4bd98584a116a68e2b50c8d9aab51ba2f02a963c548fb9d0f5a3fef617c0be36"),
}
DST = {
    "05_rivals.md": os.path.join(STAGE, "paper", "draft", "05_rivals.md"),
    "TABLE_NUMBERS.md": os.path.join(STAGE, "paper", "draft", "TABLE_NUMBERS.md"),
    "table_9.md": os.path.join(STAGE, "paper", "draft", "tables", "table_9.md"),
}
HEADING = "## Main text: Table 9 (Section 5.4, Post hoc analyses)"
PROBLEM_LINE = {"pm25": 9, "ndvi": 10, "fire": 11, "defo": 12, "coral": 13}
ROW_LABEL = {"pm25": "PM2.5", "ndvi": "NDVI", "fire": "Burned fraction", "defo": "Forest loss",
             "coral": "Coral bleaching"}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read_checked(path, want):
    with open(path, "rb") as fh:
        b = fh.read()
    if sha(b) != want:
        sys.exit("SHA-256 of %s is %s, expected %s: stop" % (os.path.basename(path), sha(b), want))
    if b.startswith(b"\xef\xbb\xbf") or b"\r" in b or not b.endswith(b"\n"):
        sys.exit("%s is not UTF-8 without BOM with LF line ends: stop" % os.path.basename(path))
    return b.decode("utf-8")


def minus(s):
    return s.replace("-", "\u2212")


def f2(x):
    """Two decimals, the tables' format for statistics (U+2212 for a minus); refuses a negative zero."""
    s = "%.2f" % x
    if s == "-0.00":
        raise ValueError("negative zero would print: %r" % x)
    return minus(s)


def intc(n):
    if isinstance(n, float):
        if n != int(n):
            raise ValueError("not an integer: %r" % n)
        n = int(n)
    return format(n, ",")


class Cells:
    def __init__(self):
        with open(CELLS, encoding="utf-8") as fh:
            self.entries = json.load(fh)["entries"]

    def one(self, table, line, row, column, part):
        r = [e for e in self.entries if e["table"] == table and e.get("line") == line and e.get("row") == row
             and e.get("column") == column and e.get("part") == part]
        if len(r) != 1 or len(r[0]["stored"]) != 1:
            raise KeyError("%d entries for %s line %s %s %s %s" % (len(r), table, line, row, column, part))
        return r[0]


def stat_ci(cells, tab_lines, p, column):
    """'v [lo, hi]' for Table 9, problem p: each part formatted once from its stored double, checked against the
    printed string, the S3.22 entry with the same stored value, and the printed table line."""
    line = PROBLEM_LINE[p]
    parts, stored = [], []
    for part in ("value", "ci_low", "ci_high"):
        e = cells.one("9", line, p, column, part)
        x = e["stored"][0]
        s = f2(x)
        if s != e["printed"]:
            raise ValueError("format %s != printed %s (%s %s %s)" % (s, e["printed"], p, column, part))
        parts.append(s)
        stored.append(x)
    txt = "%s [%s, %s]" % tuple(parts)
    e0 = cells.one("9", line, p, column, "value")
    if not e0["cell"].startswith(txt):
        raise ValueError("token %r is not the start of the cell %r" % (txt, e0["cell"]))
    row = tab_lines[line - 1]
    if not row.startswith("| %s |" % ROW_LABEL[p]) or ("| %s" % e0["cell"]) not in row:
        raise ValueError("cell %r not on line %d of tables_agreed.md" % (e0["cell"], line))
    s322_col = {"kendall_w": ("kendall_w", 157), "spearman_top20_union_median": ("spearman_median", 159)}[column]
    for part, x in zip(("value", "ci_low", "ci_high"), stored):
        e322 = cells.one("S3.22", s322_col[1], s322_col[0], p, part)
        if e322["stored"][0] != x:
            raise ValueError("Table 9 and Table S3.22 store different values for %s %s %s" % (p, column, part))
    return txt, stored


def tokens(tab_lines):
    c = Cells()
    t, st = {}, {}
    for p, k in (("pm25", "PM25"), ("ndvi", "NDVI"), ("defo", "DEFO"), ("coral", "CORAL")):
        t["W_" + k], st["W_" + k] = stat_ci(c, tab_lines, p, "kendall_w")
        t["SP_" + k], st["SP_" + k] = stat_ci(c, tab_lines, p, "spearman_top20_union_median")
    wf = c.one("9", PROBLEM_LINE["fire"], "fire", "kendall_w", "value")
    if wf["stored"] != [None] or wf["printed"] != "undefined":
        raise ValueError("burned fraction's W is not the undefined cell: 'Where defined' would be wrong")
    ws = {k: st["W_" + k][0] for k in ("PM25", "NDVI", "DEFO", "CORAL")}
    if min(ws, key=ws.get) != "NDVI" or max(ws, key=ws.get) != "PM25":
        raise ValueError("W range ends are not NDVI (lowest) and PM2.5 (highest): %r" % ws)
    for k in ("PM25", "NDVI"):
        lo, hi = st["SP_" + k][1], st["SP_" + k][2]
        if not lo < 0 < hi:
            raise ValueError("%s Spearman interval does not include 0: %r" % (k, st["SP_" + k]))
    return t, st


def table9_block(text):
    """The Table 9 block of tables_agreed.md: from the first line after the heading's blank line to the last
    non-blank line before the next '## ' heading, each line with its LF."""
    lines = text.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln == HEADING]
    if len(idx) != 1:
        raise ValueError("Table 9 heading found %d times" % len(idx))
    i = idx[0] + 1
    if lines[i] != "":
        raise ValueError("no blank line after the heading")
    i += 1
    j = i
    while not lines[j].startswith("## "):
        j += 1
    k = j
    while lines[k - 1] == "":
        k -= 1
    blk = lines[i:k]
    if not blk[0].startswith("**Table 9.** ") or "<!-- src: " not in blk[0] or not blk[0].endswith(" -->"):
        raise ValueError("block does not start with the Table 9 caption and its source comment")
    if blk[1] != "" or not blk[2].startswith("| Problem | Main set |") or not blk[3].startswith("|---|"):
        raise ValueError("unexpected table head")
    for n, p in enumerate(("pm25", "ndvi", "fire", "defo", "coral")):
        if not blk[4 + n].startswith("| %s |" % ROW_LABEL[p]):
            raise ValueError("row %d is not %s" % (n, ROW_LABEL[p]))
    if blk[9] != "" or [b[:1] for b in blk[10:]] != ["ᵃ", "ᵇ", "ᶜ", "†"]:
        raise ValueError("unexpected notes: %r" % [b[:12] for b in blk[9:]])
    block = "\n".join(blk) + "\n"
    if text.count(block) != 1:
        raise ValueError("block is not unique in tables_agreed.md")
    first_line = i + 1  # 1-based number of the caption line
    return block, first_line, first_line + len(blk) - 1


def caption_title(block):
    cap = block.split("\n", 1)[0][len("**Table 9.** "):]
    return cap[:cap.index(", ")]


HEADER_T9 = (
    "<!-- S3.13 write-up, 2026-11-17: new file, so there is no pre-edit copy (there was no live file). Table 9 "
    "(Section 5.4), post hoc and report-only (ruling AK): the main-text row of the post hoc SHAP comparison of Part 628 "
    "(rulings AW, AY, AZ1, BA and BB; SHAP protocol D:/treeroute/analysis/shap_v1/PROTOCOL.md, section 8, main-text "
    "row, and section 10), one row per problem at the nowcast, at the variable level. The caption with its source "
    "comment, the table and its four notes (a, b, c and \u2020) are copied by script, byte for byte, from the Table 9 "
    "block of paper/supp_build/s3_13/reconcile/tables_agreed.md (version 5, the final checked tables; lines {L0} to "
    "{L1}; SHA-256 {TSHA}), without its draft heading; no caption, note, label or cell was changed. That file was "
    "built twice from the stored values with one rounding step per printed number, by "
    "paper/supp_build/s3_13/A/scripts/build_tables.py and paper/supp_build/s3_13/B/scripts/build_tables.py under "
    "paper/supp_build/s3_13/spec/TABLE_SPEC.md, and reconciled; versions 2 to 5 reworded captions, notes, labels and "
    "cells after four checks and changed no number. paper/supp_build/s3_13/reconcile/cells.json lists every printed "
    "data number of this table (its table 9 entries, lines 9 to 13 of tables_agreed.md) with its source, selector and "
    "stored value. As the caption's source comment says, the cells are from "
    "D:/treeroute/analysis/shap_v1/out/<problem>/lead_0/compare/AW4_main_row.json, except the two cells marked \u2020 "
    "(burned fraction's treeroute v1 top 3 and own-history share), which are from "
    "D:/treeroute/analysis/shap_v1/verify_v1/A/results.json problems.fire.main_row (ruling BB1). Rulings in the notes "
    "and labels: note a, burned fraction's main set is treeroute v1 alone (protocol "
    "section 8's fire row); note b, ruling BB4's note on PM2.5's RBO with the consensus; note c and the column label "
    "\"median of the rivals\", ruling BB4; the label \"(no own-history input)\" on coral bleaching's own-history "
    "shares, ruling BB4; \u2020, ruling BB1. Facts (final, post hoc (Part 628)): A16 (W), A17 (median Spearman "
    "correlation and RBO), A18 (own-history shares), A10 (fixed settings) and A14 (the samples); Section 5.4 cites "
    "A10, A16 and A17. Table S3.22 of Supplement S3.13 repeats this table with its components. -->"
)

PARA = (
    "Table 9 compares, post hoc, the SHAP values (Lundberg and Lee 2017) of treeroute v1 and its rivals at the nowcast "
    "(Supplement S3.13). <!-- Part 628, rulings AW, AY, AZ1, BA and BB; post hoc and report-only, ruling AK --> Where "
    "defined, Kendall's W of the main set's full rankings is {W_NDVI} (NDVI) to {W_PM25} (PM2.5). <!-- A16 --> Over "
    "the variables in either model's top 20, treeroute v1's median Spearman correlation with its same-link rivals is "
    "{SP_PM25} on PM2.5 and {SP_NDVI} on NDVI, both intervals including 0, and {SP_DEFO} on forest loss and {SP_CORAL} "
    "on coral bleaching. <!-- A17; A10 (the top-20 union) --> SHAP values show what a model uses, not what causes the "
    "outcome, and agreement between rankings is not correctness. <!-- SHAP protocol section 10 (\"Not claimed\"); "
    "Supplement S3.13, \"Not claimed\" -->"
)

TRAIL_05 = (
    "<!-- S3.13 write-up, 2026-11-17 (pre-edit copy in draft/_snapshots/@@SNAP@@/): 5.4 gains a last paragraph of "
    "four sentences on the post hoc SHAP comparison of Part 628 (rulings AW, AY, AZ1, BA and BB; Supplement S3.13), "
    "after the coral bleaching paragraph. It cites the new Table 9 (draft/tables/table_9.md, first cited after Table 8; "
    "draft/TABLE_NUMBERS.md), Lundberg and Lee 2017 (in REFERENCES.md section A since this pass) and Supplement S3.13; "
    "gives Kendall's W of the main set and treeroute v1's median top-20-union Spearman correlation with its same-link "
    "rivals, with their intervals (facts A16 and A17, with A10 for the settings; each number formatted once from its "
    "stored value in paper/supp_build/s3_13/reconcile/cells.json and equal to Table 9's printed cell); and says what "
    "the comparison does not claim (SHAP protocol section 10). No existing sentence or number changed. -->"
)

ANCHOR_05 = "<!-- RC12, C16, K80 -->\n\n<!-- Cross-check pass (2026-10-27;"
END_05 = "No number changed. -->\n"
ROW_ANCHOR = ("| 7 (panels 7A-7C) | 8 (panels 8A-8C) | `tables/table_7.md` | Outcome-defined strata | "
              "5.4 Post hoc analyses |\n")
ROW_NEW = "| \u2013 | 9 | `tables/table_9.md` | {TITLE} | 5.4 Post hoc analyses |\n"
NOTE_ANCHOR = "Pre-edit copy under draft/_snapshots/20261112T2139Z_tier1/apply_crosscut/.\n"
NOTE_NEW = (
    " S3.13 write-up, 2026-11-17: Table 9 (Section 5.4; the post hoc SHAP comparison of Supplement S3.13) is new, so "
    "it has no old number, and its file, `tables/table_9.md`, carries its own number (no file is named "
    "`table_8.md`). The Word build places it after the last paragraph of 5.4, which first cites it, after Table 8; no "
    "table was renumbered. Pre-edit copy under draft/_snapshots/@@SNAP@@/."
)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    b = text.encode("utf-8")
    with open(path, "wb") as fh:
        fh.write(b)
    return sha(b), len(b)


def main():
    tab = read_checked(TABLES, TABLES_SHA)
    tab_lines = tab.split("\n")
    t, st = tokens(tab_lines)
    block, l0, l1 = table9_block(tab)
    title = caption_title(block)
    # table_9.md
    hdr = HEADER_T9.replace("{L0}", str(l0)).replace("{L1}", str(l1)).replace("{TSHA}", TABLES_SHA)
    if "{" in hdr or hdr.count("<!--") != 1 or hdr.count("-->") != 1 or "--" in hdr[4:-3]:
        raise ValueError("header comment malformed")
    t9 = hdr + "\n\n" + block
    # 05_rivals.md
    r = read_checked(os.path.join(WORK, BASES["05_rivals.md"][0]), BASES["05_rivals.md"][1])
    if r.count(ANCHOR_05) != 1 or not r.endswith(END_05):
        raise ValueError("05_rivals.md anchors not found exactly once")
    cpos = r.index(ANCHOR_05)
    para_start = r.rfind("\n", 0, cpos) + 1
    if not r.startswith("On coral bleaching at the nowcast, the absolute-error booster", para_start):
        raise ValueError("the paragraph before the anchor is not the coral bleaching paragraph")
    para = PARA
    for k, v in t.items():
        para = para.replace("{" + k + "}", v)
    if "{" in para:
        raise ValueError("unfilled token in the paragraph")
    r2 = r.replace(ANCHOR_05, "<!-- RC12, C16, K80 -->\n\n" + para + "\n\n<!-- Cross-check pass (2026-10-27;", 1)
    r2 = r2 + "\n" + TRAIL_05 + "\n"
    # TABLE_NUMBERS.md
    n = read_checked(os.path.join(WORK, BASES["TABLE_NUMBERS.md"][0]), BASES["TABLE_NUMBERS.md"][1])
    if n.count(ROW_ANCHOR) != 1 or n.count(NOTE_ANCHOR) != 1 or not n.endswith(NOTE_ANCHOR):
        raise ValueError("TABLE_NUMBERS.md anchors not found exactly once")
    n2 = n.replace(ROW_ANCHOR, ROW_ANCHOR + ROW_NEW.replace("{TITLE}", title), 1)
    n2 = n2[:-len(NOTE_ANCHOR)] + NOTE_ANCHOR[:-1] + NOTE_NEW + "\n"
    for name, text in (("table_9.md", t9), ("05_rivals.md", r2), ("TABLE_NUMBERS.md", n2)):
        if "\r" in text or not text.endswith("\n") or text.endswith("\n\n"):
            raise ValueError("line-end rule broken in %s" % name)
        h, size = write(DST[name], text)
        print("%-17s staged SHA-256 %s (%d bytes)" % (name, h, size))
    print("Table 9 block: lines %d-%d of tables_agreed.md (%d bytes); caption title: %s" % (l0, l1, len(block.encode("utf-8")), title))
    for k in sorted(t):
        print("token %-9s %s   stored %s" % (k, t[k], st[k]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
