# Comparison only (builder B): version 2 of OUT\B\tables.md and cells.json against version 1 (OUT\B\tables_v1.md and
# cells_v1.json, byte copies made before the rebuild). Writes nothing.
# Since the version-3 rebuild, tables.md and cells.json hold version 3, so version 2 is read from its byte copies
# OUT\B\tables_v2.md and cells_v2.json (V2_MD and V2_CJ below); the checks are unchanged.
#
# 1. Lists every changed line of tables.md (difflib, and the line map below).
# 2. Builds the expected version 2 from version 1 by the change order's OLD/NEW printed texts, as quoted in
#    OUT\spec\CHANGES_v2.md (each also found in OUT\_brief\fix_order_v2.md), and requires it equal to version 2.
# 3. Compares the cells.json entries one by one: only `line` (by the line map), `part` (G1: panel f value -> share) and
#    `cell` (where the note line itself changed) may differ.
# 4. Scans the number tokens of every line: unchanged lines have the same tokens; on a changed line the tokens added or
#    removed are tokens of the order's NEW or OLD texts (constants), never a data number.
# Run as: py -3.9 -I -B <this file>
import sys
import os
import re
import json
import difflib
import hashlib
import collections

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_B = os.path.dirname(HERE)
OUT_DIR = os.path.dirname(OUT_B)
CHANGES = os.path.join(OUT_DIR, "spec", "CHANGES_v2.md")
ORDER = os.path.join(OUT_DIR, "_brief", "fix_order_v2.md")

fails = []


def bad(msg):
    fails.append(msg)


def need(cond, msg):
    if not cond:
        bad(msg)
    return bool(cond)


def rb(name):
    with open(os.path.join(OUT_B, name), "rb") as f:
        return f.read()


V2_MD, V2_CJ = "tables_v2.md", "cells_v2.json"  # the version-2 outputs (byte copies made before the version-3 rebuild)
raw = {n: rb(n) for n in ("tables_v1.md", V2_MD, "cells_v1.json", V2_CJ)}
for n, b in raw.items():
    print("%-14s sha256 %s  %d bytes" % (n, hashlib.sha256(b).hexdigest(), len(b)))
for n in ("tables_v1.md", V2_MD):
    need(raw[n].endswith(b"\n") and not raw[n].endswith(b"\n\n") and b"\r" not in raw[n], n + ": line ends")
L1 = raw["tables_v1.md"].decode("utf-8")[:-1].split("\n")
L2 = raw[V2_MD].decode("utf-8")[:-1].split("\n")
print("lines: v1 %d, v2 %d" % (len(L1), len(L2)))

# ---------------------------------------------------------------------------------------------------------------------
# The order's printed texts, from CHANGES_v2.md (single-line fenced blocks whose label says "printed text")

with open(CHANGES, "r", encoding="utf-8") as f:
    ch_lines = f.read().split("\n")
blocks, section, inside, cur, label = [], None, False, None, None
for i, ln in enumerate(ch_lines):
    if not inside and ln.startswith("## "):
        section = ln[3:].split(".")[0]
    if ln == "```":
        if inside:
            blocks.append((section, label, cur))
            inside = False
        else:
            j = i - 1
            while j >= 0 and ch_lines[j] == "":
                j -= 1
            label, cur, inside = ch_lines[j], [], True
    elif inside:
        cur.append(ln)
need(not inside, "CHANGES_v2.md: an unclosed fence")
PRINTED = collections.OrderedDict()
for sec, lab, body in blocks:
    if "printed text" in lab:
        PRINTED.setdefault(sec, []).append((lab, body))


def pt(sec, idx, must):
    lab, body = PRINTED[sec][idx]
    need(must in lab, "CHANGES_v2.md %s printed block %d has label %r, expected %r" % (sec, idx, lab, must))
    need(len(body) == 1, "CHANGES_v2.md %s printed block %d has %d lines" % (sec, idx, len(body)))
    return body[0]


want_counts = {"C1": 7, "C2": 4, "C3": 4, "C4": 6, "C5": 2, "C6": 4, "C7": 2, "C8": 2, "C9": 1}
for sec, n in want_counts.items():
    need(len(PRINTED.get(sec, [])) == n, "CHANGES_v2.md %s: %d printed blocks, expected %d" % (sec, len(PRINTED.get(sec, [])), n))

T = {
    "C1_t9_old": pt("C1", 0, "Table 9 caption, OLD"), "C1_t9_new": pt("C1", 1, "NEW"),
    "C1_aw3_old": pt("C1", 2, "S3.23-S3.27, OLD"), "C1_aw3_new_de": pt("C1", 3, "NEW printed text (S3.23, S3.24, S3.26)"),
    "C1_aw3_new_deg": pt("C1", 4, "NEW printed text (S3.25, S3.27)"),
    "C1_s329_old": pt("C1", 5, "S3.29, OLD"), "C1_s329_new": pt("C1", 6, "NEW"),
    "C2_a_old": pt("C2", 0, "Note ᵃ, OLD"), "C2_a_new": pt("C2", 1, "NEW"),
    "C2_b_old": pt("C2", 2, "Note ᵇ, OLD"), "C2_b_new": pt("C2", 3, "NEW"),
    "C3_1_old": pt("C3", 0, "OLD printed text (first sentence)"), "C3_1_new": pt("C3", 1, "NEW"),
    "C3_2_old": pt("C3", 2, "OLD printed text (second sentence"), "C3_2_new": pt("C3", 3, "NEW"),
    "C4_drop": pt("C4", 0, "Dropped row, OLD"), "C4_base_old": pt("C4", 1, "Baselines row, OLD"),
    "C4_base_new": pt("C4", 2, "NEW"), "C4_note_new": pt("C4", 3, "New note line"),
    "C4_s330_old": pt("C4", 4, "S3.30 note, OLD"), "C4_s330_new": pt("C4", 5, "NEW"),
    "C5_old": pt("C5", 0, "OLD"), "C5_new": pt("C5", 1, "NEW"),
    "C6_e10_old": pt("C6", 0, "E10, OLD"), "C6_e10_new": pt("C6", 1, "NEW"),
    "C6_a_old": pt("C6", 2, "Note ᵃ, OLD"), "C6_a_new": pt("C6", 3, "NEW"),
    "C7_old": pt("C7", 0, "OLD"), "C7_new": pt("C7", 1, "NEW"),
    "C8_old": pt("C8", 0, "OLD"), "C8_new": pt("C8", 1, "NEW"),
    "C9_new": pt("C9", 0, "NEW printed text"),
}

# each text is also in the change order itself (its backticked spans, with the order's line wraps read as spaces);
# the dropped row is abbreviated there, so only its start is looked for
with open(ORDER, "r", encoding="utf-8") as f:
    order_flat = re.sub(r"\n[ ]*", " ", f.read())
for k, v in T.items():
    probe = "`| Coral bleaching | CRW Outlook | ... |`" if k == "C4_drop" else "`" + v + "`"
    need(probe in order_flat, "fix_order_v2.md does not hold the text %s" % k)
need(T["C4_drop"].startswith("| Coral bleaching | CRW Outlook | "), "the dropped row's start")

# ---------------------------------------------------------------------------------------------------------------------
# The expected version 2: version 1 with the order's changes applied; ORIG[j] = the v1 index of expected line j

EXP = list(L1)
ORIG = list(range(len(L1)))
APPLIED = collections.defaultdict(list)  # v1 index -> list of (old, new)


def rep(key_old, key_new, n_lines, where=lambda i, ln: True, wrap=("", "")):
    old = wrap[0] + T[key_old] + wrap[1]
    new = wrap[0] + T[key_new] + wrap[1]
    hits = [i for i, ln in enumerate(EXP) if old in ln and where(i, ln)]
    need(len(hits) == n_lines, "%s: in %d lines, expected %d" % (key_old, len(hits), n_lines))
    for i in hits:
        need(EXP[i].count(old) == 1, "%s: more than once on v1 line %d" % (key_old, ORIG[i] + 1))
        EXP[i] = EXP[i].replace(old, new)
        APPLIED[ORIG[i]].append((key_old.split("_")[0], old, new))
    return hits


def table_of(prefixes):
    return lambda i, ln: any(ln.startswith("**Table S3.%s (post hoc).**" % x) for x in prefixes)


# C9: the new sentence after the header comment's first sentence (line 1 only)
FIRST = "the nowcast of each problem. "
need(EXP[0].count(FIRST) == 1, "C9: the header's first sentence")
APPLIED[0].append(("C9", FIRST, FIRST + T["C9_new"] + " "))
EXP[0] = EXP[0].replace(FIRST, FIRST + T["C9_new"] + " ")
rep("C1_t9_old", "C1_t9_new", 1)
rep("C1_aw3_old", "C1_aw3_new_de", 3, where=table_of(("23", "24", "26")))
rep("C1_aw3_old", "C1_aw3_new_deg", 2, where=table_of(("25", "27")))
rep("C1_s329_old", "C1_s329_new", 1)
rep("C2_a_old", "C2_a_new", 1, where=lambda i, ln: ln.startswith("ᵃ Rows checked:"))
rep("C2_b_old", "C2_b_new", 1, where=lambda i, ln: ln.startswith("ᵇ Ridge outside coral bleaching"))
rep("C3_1_old", "C3_1_new", 1, where=lambda i, ln: ln.startswith("‡ BARDL reads"))
rep("C3_2_old", "C3_2_new", 1, where=lambda i, ln: ln.startswith("‡ BARDL reads"))
rep("C4_base_old", "C4_base_new", 1, where=lambda i, ln: ln == T["C4_base_old"])
rep("C4_s330_old", "C4_s330_new", 1, where=lambda i, ln: ln == T["C4_s330_old"])
rep("C5_old", "C5_new", 1, where=lambda i, ln: ln.startswith("| " + T["C5_old"] + " | "), wrap=("| ", " | "))
rep("C6_e10_old", "C6_e10_new", 1, where=lambda i, ln: ln.startswith("| E10 | "), wrap=("| ", " | "))
rep("C6_a_old", "C6_a_new", 1, where=lambda i, ln: ln.startswith("ᵃ E5 is informational"))
rep("C7_old", "C7_new", 5, where=lambda i, ln: ln.startswith("Sign agreement: "))
rep("C8_old", "C8_new", 1, where=lambda i, ln: ln.startswith("ᵈ Coral bleaching's table"))
# C4: the dropped row, then the new note line before the S3.18 note group's "ᵃ Failed" line (after the blank line)
drop = [i for i, ln in enumerate(EXP) if ln == T["C4_drop"]]
DROPPED = []
if need(len(drop) == 1, "C4: the dropped row is on %d lines" % len(drop)):
    DROPPED.append(ORIG[drop[0]])
    del EXP[drop[0]]
    del ORIG[drop[0]]
fa = [i for i, ln in enumerate(EXP) if ln.startswith("ᵃ Failed:")]
if need(len(fa) == 1 and EXP[fa[0] - 1] == "", "C4: the S3.18 note group's first line"):
    EXP.insert(fa[0], T["C4_note_new"])
    ORIG.insert(fa[0], None)

same = (EXP == L2)
need(same, "the expected version 2 (version 1 with the order's texts) differs from tables.md")
if not same:
    for op in difflib.SequenceMatcher(None, EXP, L2, autojunk=False).get_opcodes():
        if op[0] != "equal":
            print("EXPECTED vs BUILT", op)
print("expected version 2 == built version 2:", same, "| changes applied on", len(APPLIED), "v1 lines,",
      len(DROPPED), "line dropped, 1 inserted")

# the line map v1 -> v2 (valid when same is true)
V1TO2 = {}
for j, i in enumerate(ORIG):
    if i is not None:
        V1TO2[i + 1] = j + 1

# ---------------------------------------------------------------------------------------------------------------------
# 1. The changed lines

print("\n== changed lines of tables.md (difflib opcodes, 1-based)")
for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, L1, L2, autojunk=False).get_opcodes():
    if tag != "equal":
        print("  %-7s v1 %s -> v2 %s" % (tag, "%d-%d" % (i1 + 1, i2) if i2 > i1 else "(none)",
                                         "%d-%d" % (j1 + 1, j2) if j2 > j1 else "(none)"))

NUMTOK = re.compile(r"[0-9](?:[0-9,.]*[0-9])?|[⁰¹²³⁴-⁹⁻]+")


def toks(s):
    return collections.Counter(NUMTOK.findall(s))


def fmt_c(c):
    return "[" + ", ".join(sorted(c.elements())) + "]" if c else "[]"


def what(line):
    return line[:70] + ("..." if len(line) > 70 else "")


print("\n== changed lines (v1 line -> v2 line), the order items applied, and the number tokens removed / added")
CHANGED = []
for j, i in enumerate(ORIG):
    if i is None:
        add = toks(L2[j])
        newt = toks(T["C4_note_new"])
        need(not (add - newt), "inserted v2 line %d: tokens outside the new note" % (j + 1))
        CHANGED.append(("inserted", None, j + 1, collections.Counter(), add))
        print("  (inserted) -> v2 %d [C4]: %s | removed [] added %s" % (j + 1, what(L2[j]), fmt_c(add)))
    elif L1[i] != L2[j]:
        rem, add = toks(L1[i]) - toks(L2[j]), toks(L2[j]) - toks(L1[i])
        olds = collections.Counter()
        news = collections.Counter()
        for cid, o, n in APPLIED[i]:
            olds += toks(o)
            news += toks(n)
        need(not (rem - olds), "v1 line %d: removed tokens %s outside the OLD texts" % (i + 1, fmt_c(rem - olds)))
        need(not (add - news), "v1 line %d: added tokens %s outside the NEW texts" % (i + 1, fmt_c(add - news)))
        CHANGED.append(("changed", i + 1, j + 1, rem, add))
        ids = "+".join(sorted(set(cid for cid, o, n in APPLIED[i])))
        print("  v1 %d -> v2 %d [%s]: %s | removed %s added %s" % (i + 1, j + 1, ids, what(L2[j]), fmt_c(rem), fmt_c(add)))
    else:
        need(toks(L1[i]) == toks(L2[j]), "unchanged line with different tokens")
        need(i not in APPLIED, "v1 line %d: a change applied but the line is unchanged" % (i + 1))
for i in DROPPED:
    rem = toks(L1[i])
    CHANGED.append(("dropped", i + 1, None, rem, collections.Counter()))
    print("  v1 %d -> (dropped) [C4]: %s | removed %s added []" % (i + 1, what(L1[i]), fmt_c(rem)))

pos_changed = sorted(k + 1 for k in range(max(len(L1), len(L2))) if k >= len(L1) or k >= len(L2) or L1[k] != L2[k])
print("\nline positions whose text differs (same number in both files):", pos_changed)
want_pos = [1, 5, 65, 66, 67, 121, 122, 144, 146, 155, 171, 174, 251, 256, 342, 344, 348, 451, 457, 543, 548, 661, 711, 784]
need(pos_changed == want_pos, "the differing line positions are not those of CHANGES_v2.md")
shift = [(i, j) for i, j in V1TO2.items() if i != j]
print("v1 -> v2 line shifts:", "none" if not shift else ("%d lines, all between v1 %d and v1 %d" % (len(shift), min(shift)[0], max(shift)[0])))

T1, T2 = toks("\n".join(L1)), toks("\n".join(L2))
print("number tokens in the whole file: v1 %d, v2 %d; removed %s; added %s"
      % (sum(T1.values()), sum(T2.values()), fmt_c(T1 - T2), fmt_c(T2 - T1)))

# ---------------------------------------------------------------------------------------------------------------------
# 3. cells.json

d1 = json.loads(raw["cells_v1.json"].decode("utf-8"))
d2 = json.loads(raw[V2_CJ].decode("utf-8"))
need(list(d1.keys()) == list(d2.keys()) == ["tables_file", "spec", "entries"], "cells.json top keys")
need(d1["tables_file"] == d2["tables_file"] and d1["spec"] == d2["spec"], "cells.json header values")
E1, E2 = d1["entries"], d2["entries"]
need(len(E1) == len(E2), "cells.json: %d entries in v1, %d in v2" % (len(E1), len(E2)))
SAME_KEYS = ["table", "panel", "row", "column", "printed", "source", "selector", "stored"]
AW3 = ("S3.23", "S3.24", "S3.25", "S3.26", "S3.27")
n_line, n_part, n_cell = 0, collections.Counter(), collections.Counter()
for k, (a, b) in enumerate(zip(E1, E2)):
    need(list(a.keys()) == list(b.keys()), "entry %d: keys" % k)
    for key in SAME_KEYS:
        need(a[key] == b[key], "entry %d (v1 line %d): %s differs: %r -> %r" % (k, a["line"], key, a[key], b[key]))
    need(V1TO2.get(a["line"]) == b["line"], "entry %d: line %d -> %d, map says %r" % (k, a["line"], b["line"], V1TO2.get(a["line"])))
    if a["line"] != b["line"]:
        n_line += 1
    if a["part"] != b["part"]:
        if need(a["part"] == "value" and b["part"] == "share" and b["table"] in AW3 and b["panel"] == "f",
                "entry %d: part %r -> %r outside G1" % (k, a["part"], b["part"])):
            n_part[b["table"]] += 1
    elif b["table"] in AW3 and b["panel"] == "f":
        bad("entry %d: a panel-f entry whose part did not change (%r)" % (k, b["part"]))
    if a["cell"] != b["cell"]:
        ok = (a["cell"] == L1[a["line"] - 1] and b["cell"] == L2[b["line"] - 1] and L1[a["line"] - 1] != L2[b["line"] - 1])
        if need(ok, "entry %d: cell changed but it is not a changed note line" % k):
            n_cell[b["line"]] += 1
            # the printed token sits in the new cell as it sat in the old one: same tokens before it
            need(b["printed"] in b["cell"], "entry %d: printed token not in the new cell" % k)
# the printed tokens of each cell, in order, are those of version 1
by_cell = collections.defaultdict(lambda: [[], []])
for a, b in zip(E1, E2):
    by_cell[(b["line"], b["table"], b["panel"], b["row"], b["column"])][0].append(a["printed"])
    by_cell[(b["line"], b["table"], b["panel"], b["row"], b["column"])][1].append(b["printed"])
need(all(x == y for x, y in by_cell.values()), "a cell whose printed tokens differ")
print("\n== cells.json: %d entries in v1 and v2; line changed on %d; part changed on %d (%s); cell changed on %d (%s)"
      % (len(E1), n_line, sum(n_part.values()), dict(sorted(n_part.items())), sum(n_cell.values()), dict(sorted(n_cell.items()))))
need(n_line == 0, "line numbers of entries shifted")
need(dict(n_part) == {"S3.23": 20, "S3.24": 25, "S3.25": 25, "S3.26": 25, "S3.27": 30}, "the G1 part changes per table")
need(dict(n_cell) == {122: 8, 344: 12}, "the cell changes per line")
# entries on changed lines: which keep their cell
on_changed = collections.Counter(b["line"] for b in E2 if b["line"] in pos_changed)
print("entries on changed lines:", dict(sorted(on_changed.items())))

print("\nfailures:", len(fails))
for m in fails[:50]:
    print("FAIL", m)
sys.exit(1 if fails else 0)
