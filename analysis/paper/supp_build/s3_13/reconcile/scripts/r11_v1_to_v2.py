# r11 (version 2, step 2b): diff of version 1 (OUT\reconcile\tables_agreed_v1.md) with version 2 (the builders'
# common tables.md, OUT\A\tables.md = OUT\B\tables.md). Read-only; prints; stops on any failure.
#  1. The order's texts are the code spans of the bullets of OUT\_brief\fix_order_v2.md, sections C1-C9 (a bullet's
#     wrapped lines joined with one space). Each printed text is also a single-line fenced text of
#     OUT\spec\CHANGES_v2.md; the dropped row, abbreviated in the order, is taken in full from there.
#  2. Version 1 with exactly those changes applied, each in the table and on the kind of line the order names and
#     the expected number of times, must give the builders' version 2 byte for byte (so nothing else changed).
#  3. A difflib alignment of the two files must find changed, dropped and added lines exactly where step 2
#     applied a change; each such line is attributed to one change of the order.
#  4. Number tokens: per changed line and over the whole file, the tokens added and removed are exactly those of
#     the order's NEW and OLD texts; no cells.json entry's printed token lies in a replaced span (v1 or v2).
#  5. cells.json: version 2 entry by entry against both builders' version-1 copies; every v1 entry's cell and
#     token lie on its line of version 1, every v2 entry's on its line of version 2.
import sys, re, json, difflib, hashlib, collections
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2]
AW3T = ("S3.23", "S3.24", "S3.25", "S3.26", "S3.27")


def stop(msg):
    raise SystemExit("stop: " + msg)


def sha(b):
    return hashlib.sha256(b).hexdigest()


# ---------------- 1. the order's texts ----------------
order = (OUT / "_brief" / "fix_order_v2.md").read_text(encoding="utf-8").split("\n")
bullets, cur, inb = collections.OrderedDict(), None, False
for l in order:
    m = re.match(r"^## (C\d)\. ", l)
    if m:
        cur, inb = m.group(1), False
        bullets[cur] = []
        continue
    if l.startswith("## "):
        cur, inb = None, False
        continue
    if cur is None:
        continue
    if l.startswith("- "):
        bullets[cur].append(l[2:])
        inb = True
    elif inb and l.startswith("  ") and l.strip():
        bullets[cur][-1] += " " + l.strip()
    else:
        inb = False
SP = {c: [re.findall(r"`([^`]*)`", b) for b in bl] for c, bl in bullets.items()}
WANT = {"C1": [2, 2, 1, 2, 0], "C2": [2, 2], "C3": [2, 3], "C4": [2, 4, 2, 2], "C5": [4], "C6": [4, 2], "C7": [2],
        "C8": [2], "C9": [1]}
got = {c: [len(x) for x in v] for c, v in SP.items()}
print("order: sections and code spans per bullet:", got)
if got != WANT:
    stop("the order's bullets are not as expected")
if "OLD: the same sentence" not in bullets["C1"][2]:
    stop("C1, third bullet: OLD is not 'the same sentence'")
T = collections.OrderedDict([
    ("C1 Table 9 caption", SP["C1"][0][:2]),
    ("C1 S3.23-S3.27 captions", [SP["C1"][1][0], SP["C1"][1][1], SP["C1"][2][0]]),  # OLD, NEW (d, e), NEW (d, e, g)
    ("C1 S3.29 caption", SP["C1"][3][:2]),
    ("C2 S3.20 note a", SP["C2"][0][:2]),
    ("C2 S3.20 note b", SP["C2"][1][:2]),
    ("C3 S3.24 note ddag, 2nd sentence", SP["C3"][0][:2]),
    ("C3 S3.24 note ddag, 3rd sentence", SP["C3"][1][:2]),
    ("C4 S3.18 b CRW Outlook row (abbreviated)", [SP["C4"][0][0]]),
    ("C4 S3.18 b baselines row", SP["C4"][1][:2]),
    ("C4 S3.18 new note: the line it goes before", [SP["C4"][2][0]]),
    ("C4 S3.18 new note", [SP["C4"][2][1]]),
    ("C4 S3.30 note", SP["C4"][3][:2]),
    ("C5 S3.22 row label", SP["C5"][0][:2]),
    ("C6 S3.21 E10, what it checks", SP["C6"][0][:2]),
    ("C6 S3.21 note a", SP["C6"][1][:2]),
    ("C7 sign-agreement note", SP["C7"][0][:2]),
    ("C8 S3.22 note d", SP["C8"][0][:2]),
    ("C9 header comment sentence", SP["C9"][0][:1]),
])
ch = (OUT / "spec" / "CHANGES_v2.md").read_text(encoding="utf-8")
CHL = ch.split("\n")
single, i = [], 0
while i < len(CHL):
    if CHL[i].startswith("```"):
        j = i + 1
        while not CHL[j].startswith("```"):
            j += 1
        if j == i + 2:
            single.append(CHL[i + 1])
        i = j + 1
    else:
        i += 1
crw = [s for s in single if s.startswith("| Coral bleaching | CRW Outlook | ")]
if len(crw) != 1:
    stop("CHANGES_v2.md: the dropped row")
CRW = crw[0]
ab_pre, ab_post = T["C4 S3.18 b CRW Outlook row (abbreviated)"][0].split(" ... ")
if not (CRW.startswith(ab_pre + " ") and CRW.endswith(" " + ab_post)):
    stop("the dropped row of CHANGES_v2.md does not fit the order's abbreviation")
printed = [t for k, v in T.items() if "abbreviated" not in k and "goes before" not in k for t in v]
notin = [t for t in printed if t not in single]
print("order: printed texts", len(printed), "+ the dropped row in full =", len(printed) + 1,
      "; not a single-line fenced text of CHANGES_v2.md:", notin)
if notin:
    stop("an order text is not quoted in CHANGES_v2.md")

# ---------------- 2. version 1 + the order's changes ----------------
v1b = (OUT / "reconcile" / "tables_agreed_v1.md").read_bytes()
v2b = (OUT / "A" / "tables.md").read_bytes()
if v2b != (OUT / "B" / "tables.md").read_bytes():
    stop("OUT\\A\\tables.md and OUT\\B\\tables.md differ")
print("version 1 (tables_agreed_v1.md):", len(v1b), "bytes,", v1b.count(b"\n"), "lines (LF), sha256", sha(v1b))
print("version 2 (A = B tables.md):    ", len(v2b), "bytes,", v2b.count(b"\n"), "lines (LF), sha256", sha(v2b))
s1, s2 = v1b.decode("utf-8"), v2b.decode("utf-8")
L1, L2 = s1.split("\n"), s2.split("\n")


def tables_of(L):
    out, cur = [], None
    for t in L:
        m = re.match(r"^\*\*Table (9|S3\.\d+)\b", t)
        if m:
            cur = m.group(1)
        elif t.startswith("## ") or t.startswith("<!--"):
            cur = None
        out.append(cur)
    return out


tab1 = tables_of(L1)
work = [dict(text=t, v1=i + 1, tab=tab1[i], ap=[]) for i, t in enumerate(L1)]
dropped = []


def apply(cid, old, new, n, tabs, prefix):
    """replace OLD by NEW: n occurrences in version 1, one per line, each in one of `tabs` on a line starting `prefix`"""
    if s1.count(old) != n:
        stop("%s: OLD occurs %d times in version 1, not %d: %r" % (cid, s1.count(old), n, old[:80]))
    ks = [k for k, it in enumerate(work) if old in it["text"]]
    if len(ks) != n:
        stop("%s: OLD on %d lines" % (cid, len(ks)))
    for k in ks:
        it = work[k]
        if it["text"].count(old) != 1 or it["tab"] not in tabs or not it["text"].startswith(prefix):
            stop("%s: OLD in an unexpected place (line %s, table %s)" % (cid, it["v1"], it["tab"]))
        nw = new(it) if callable(new) else new
        s = it["text"].index(old)
        it["ap"].append((cid, old, nw))
        it["text"] = it["text"][:s] + nw + it["text"][s + len(old):]
    return [work[k]["tab"] for k in ks]


# C9: the sentence after the header comment's first sentence
t0 = work[0]["text"]
if not t0.startswith("<!-- "):
    stop("line 1 is not the header comment")
k = t0.index(". ")
if not t0[:k + 1].endswith("the nowcast of each problem."):
    stop("the header comment's first sentence")
ins = " " + T["C9 header comment sentence"][0]
work[0]["ap"].append(("C9", "", ins))
work[0]["text"] = t0[:k + 1] + ins + t0[k + 1:]
# C1
apply("C1", *T["C1 Table 9 caption"], 1, {"9"}, "**Table 9.** ")
o, nde, ndeg = T["C1 S3.23-S3.27 captions"]
got_t = apply("C1", o, lambda it: ndeg if it["tab"] in ("S3.25", "S3.27") else nde, 5, set(AW3T), "**Table S3.2")
if sorted(got_t) != list(AW3T):
    stop("C1: the five AW3 captions")
apply("C1", *T["C1 S3.29 caption"], 1, {"S3.29"}, "**Table S3.29 ")
# C2
apply("C2", *T["C2 S3.20 note a"], 1, {"S3.20"}, "ᵃ Rows checked")
apply("C2", *T["C2 S3.20 note b"], 1, {"S3.20"}, "ᵇ Ridge outside coral bleaching")
# C3
apply("C3", *T["C3 S3.24 note ddag, 2nd sentence"], 1, {"S3.24"}, "‡ BARDL reads")
apply("C3", *T["C3 S3.24 note ddag, 3rd sentence"], 1, {"S3.24"}, "‡ BARDL reads")
# C4: drop the CRW Outlook row, reword the baselines row, insert the note line before 'ᵃ Failed', S3.30 note
ks = [k for k, it in enumerate(work) if it["text"].startswith(ab_pre + " ")]
if len(ks) != 1 or work[ks[0]]["text"] != CRW or work[ks[0]]["tab"] != "S3.18":
    stop("C4: the CRW Outlook row of version 1")
dropped.append(work.pop(ks[0]))
apply("C4", *T["C4 S3.18 b baselines row"], 1, {"S3.18"}, "| All five | ")
before = T["C4 S3.18 new note: the line it goes before"][0]
ks = [k for k, it in enumerate(work) if it["tab"] == "S3.18" and it["text"].startswith(before)]
if len(ks) != 1:
    stop("C4: the line that starts 'ᵃ Failed'")
k = ks[0]
if work[k - 1]["text"] != "" or not work[k - 2]["text"].startswith("| All five | "):
    stop("C4: the note line would not follow the panel b table")
note = T["C4 S3.18 new note"][0]
work.insert(k, dict(text=note, v1=None, tab="S3.18", ap=[("C4", "", note)]))
apply("C4", *T["C4 S3.30 note"], 1, {"S3.30"}, "Coral bleaching: B1 is not defined")
# C5: the row label, as the row's first cell
o, nw = T["C5 S3.22 row label"]
if s1.count(o) != 1:
    stop("C5: the label occurs %d times in version 1" % s1.count(o))
apply("C5", "| " + o + " |", "| " + nw + " |", 1, {"S3.22"}, "| " + o + " |")
# C6
apply("C6", *T["C6 S3.21 E10, what it checks"], 1, {"S3.21"}, "| E10 | ")
apply("C6", *T["C6 S3.21 note a"], 1, {"S3.21"}, "ᵃ E5 is informational")
# C7
got_t = apply("C7", *T["C7 sign-agreement note"], 5, set(AW3T), "Sign agreement: of the players")
if sorted(got_t) != list(AW3T):
    stop("C7: the five AW3 tables")
# C8
apply("C8", *T["C8 S3.22 note d"], 1, {"S3.22"}, "ᵈ Coral bleaching's table")

exp = "\n".join(it["text"] for it in work).encode("utf-8")
print("version 1 + the order's changes == version 2, byte for byte:", exp == v2b, "; sha256", sha(exp))
if exp != v2b:
    E = exp.decode("utf-8").split("\n")
    for i, (x, y) in enumerate(zip(E, L2), 1):
        if x != y:
            print("first differing line", i, "\n  expected :", x[:300], "\n  version 2:", y[:300])
            break
    stop("the rebuild differs from version 2")

# ---------------- 3. alignment and attribution ----------------
changed = []   # (change id, v1 line or None, v2 line or None, table, kind)
for j, it in enumerate(work, 1):
    if it["ap"]:
        ids = sorted({a[0] for a in it["ap"]})
        if len(ids) != 1:
            stop("two changes on one line")
        kind = "added" if it["v1"] is None else "changed"
        changed.append((ids[0], it["v1"], j, it["tab"], kind))
for it in dropped:
    changed.append(("C4", it["v1"], None, it["tab"], "dropped"))
sm = difflib.SequenceMatcher(None, L1, L2, autojunk=False)
ne1, ne2, shifts, ops = set(), set(), [], []
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        shifts += [(a + 1, b + 1) for a, b in zip(range(i1, i2), range(j1, j2)) if a != b]
    else:
        ops.append((tag, "v1 %d-%d" % (i1 + 1, i2), "v2 %d-%d" % (j1 + 1, j2)))
        ne1.update(range(i1 + 1, i2 + 1))
        ne2.update(range(j1 + 1, j2 + 1))
m1 = {c[1] for c in changed if c[1] is not None}
m2 = {c[2] for c in changed if c[2] is not None}
mine_shift = [(it["v1"], j) for j, it in enumerate(work, 1) if not it["ap"] and it["v1"] != j]
print("difflib opcodes other than equal:", len(ops), ops)
print("difflib's unequal lines == the lines where a change was applied: version 1", ne1 == m1, "; version 2", ne2 == m2)
print("unchanged lines that moved (v1 -> v2), difflib:", shifts, "; from the rebuild:", mine_shift)
print("changed lines that moved (v1 -> v2):", [(c[1], c[2]) for c in changed if c[1] and c[2] and c[1] != c[2]])
if ne1 != m1 or ne2 != m2 or shifts != mine_shift:
    stop("the alignment does not agree with the rebuild")
pos = [i + 1 for i in range(max(len(L1), len(L2))) if (L1[i] if i < len(L1) else None) != (L2[i] if i < len(L2) else None)]
mm = re.search(r"The lines that change \(1-based\): ([\d, ]+?) \(line 66", re.sub(r"\s+", " ", ch))
listed = [int(x) for x in mm.group(1).split(", ")]
print("lines that differ by position:", len(pos), pos)
print("equal to CHANGES_v2.md's list of changed lines:", pos == listed)
mm = re.search(r"tables\.md keeps its ([\d,]+) lines", re.sub(r"\s+", " ", ch))
print("CHANGES_v2.md says tables.md keeps", mm.group(1), "lines; version 1 has", v1b.count(b"\n"), "and version 2",
      v2b.count(b"\n"), "line feeds (", len(L1), "and", len(L2), "pieces when split on LF, the last one empty )")
by = collections.OrderedDict((c, []) for c in ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9"])
for c in changed:
    by[c[0]].append(c)
for c, lst in by.items():
    lst.sort(key=lambda t: (t[1] or t[2] - 0.5))
    print("%s: %d lines: %s" % (c, len(lst), "; ".join("%s %s -> %s (%s)" % (t[4], t[1] or "-", t[2] or "-", t[3]) for t in lst)))

# ---------------- 4. number tokens ----------------
NUMRE = re.compile(r"[−-]?\d+(?:[.,]\d+)*%?|[⁰¹²³⁴-⁹⁻]+")


def toks(s):
    return collections.Counter(NUMRE.findall(s))


def signed(new, old):
    d = collections.Counter(toks(new))
    d.subtract(toks(old))
    return {k: v for k, v in d.items() if v}


bad, expect_all = [], collections.Counter()
for j, it in enumerate(work, 1):
    if not it["ap"]:
        continue
    act = signed(it["text"], L1[it["v1"] - 1] if it["v1"] else "")
    e = collections.Counter()
    for cid, o, n in it["ap"]:
        e.update(toks(n))
        e.subtract(toks(o))
    e = {k: v for k, v in e.items() if v}
    if act != e:
        bad.append((it["v1"], j, act, e))
    expect_all.update(e)
for it in dropped:
    expect_all.subtract(toks(it["text"]))
act_all = signed(s2, s1)
expect_all = {k: v for k, v in expect_all.items() if v}
print("number tokens (regex %s): version 1 %d, version 2 %d" % (NUMRE.pattern, sum(toks(s1).values()), sum(toks(s2).values())))
print("   added:", sorted((k, v) for k, v in act_all.items() if v > 0))
print("   removed:", sorted((k, -v) for k, v in act_all.items() if v < 0))
print("per changed line, tokens added/removed == those of the order's NEW/OLD texts:", not bad, bad[:5])
print("whole file, tokens added/removed == those of the order's texts (incl. the dropped row):", act_all == expect_all)
if bad or act_all != expect_all:
    stop("number tokens")

# ---------------- 5. cells.json ----------------
c2b = (OUT / "A" / "cells.json").read_bytes()
if c2b != (OUT / "B" / "cells.json").read_bytes():
    stop("OUT\\A\\cells.json and OUT\\B\\cells.json differ")
D2 = json.loads(c2b.decode("utf-8"))
E2 = D2["entries"]


def cells_of(s):
    if s.startswith("| ") and s.endswith(" |"):
        out, p = [], 2
        for c in s[2:-2].split(" | "):
            out.append((p, c))
            p += len(c) + 3
        return out
    return [(0, s)]


def locate(L, ents):
    """for each entry (in file order): the position of its printed token on its line, inside its cell, left to right"""
    res, cursor = [], {}
    for e in ents:
        s = L[e["line"] - 1]
        tok, cur0 = e["printed"], cursor.get(e["line"], 0)
        cl, found = cells_of(s), None
        k = s.find(tok, cur0)
        while k != -1:
            pv = s[k - 1] if k > 0 else " "
            pv2 = s[k - 2] if k > 1 else " "
            nx = s[k + len(tok)] if k + len(tok) < len(s) else " "
            nx2 = s[k + len(tok) + 1] if k + len(tok) + 1 < len(s) else " "
            okb = not (pv.isdigit() or (pv in ".," and pv2.isdigit()) or pv in "−-") and \
                not (nx.isdigit() or (nx in ".," and nx2.isdigit()) or nx == "%")
            if okb and any(cp <= k and k + len(tok) <= cp + len(ct) and ct == e["cell"] for cp, ct in cl):
                found = k
                break
            k = s.find(tok, k + 1)
        res.append(found)
        if found is not None:
            cursor[e["line"]] = found + len(tok)
    return res


P2 = locate(L2, E2)
print("version 2: entries", len(E2), "; printed token found in its cell on its line, in reading order:",
      sum(1 for x in P2 if x is not None), "; not found:", sum(1 for x in P2 if x is None))
if any(x is None for x in P2):
    stop("a version-2 entry is not on its line")
# no entry's token in a replaced span
spans2 = collections.defaultdict(list)
spans1 = collections.defaultdict(list)
repl1 = collections.defaultdict(list)   # v1 line -> (start in v1, length of OLD, length of NEW)
for j, it in enumerate(work, 1):
    for cid, o, n in it["ap"]:
        s = it["text"].find(n)
        if it["text"].count(n) != 1:
            stop("a NEW text twice on one line")
        spans2[j].append((s, s + len(n)))
        if o:
            s = L1[it["v1"] - 1].find(o)
            spans1[it["v1"]].append((s, s + len(o)))
            repl1[it["v1"]].append((s, len(o), len(n)))
hit2 = [(e["line"], e["printed"]) for e, p in zip(E2, P2) for a, b in spans2.get(e["line"], []) if p < b and p + len(e["printed"]) > a]
on_changed = [e for e in E2 if e["line"] in spans2]
print("version-2 entries on changed lines:", len(on_changed), dict(collections.Counter(e["line"] for e in on_changed)),
      "; tokens inside a NEW span:", hit2)
if hit2:
    stop("a data number inside a changed text")
SKEY = lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True)  # noqa: E731
for X in ("A", "B"):
    b1 = (OUT / X / "cells_v1.json").read_bytes()
    D1 = json.loads(b1.decode("utf-8"))
    E1 = D1["entries"]
    print("OUT\\%s\\cells_v1.json:" % X, len(b1), "bytes, sha256", sha(b1), "; entries", len(E1))
    if list(D1) != list(D2) or D1["tables_file"] != D2["tables_file"] or D1["spec"] != D2["spec"] or len(E1) != len(E2):
        stop("top level of %s's version-1 cells.json" % X)
    P1 = locate(L1, E1)
    if any(x is None for x in P1):
        stop("a version-1 entry of %s is not on its line of version 1" % X)
    hit1 = [(e["line"], e["printed"]) for e, p in zip(E1, P1) for a, b in spans1.get(e["line"], []) if p < b and p + len(e["printed"]) > a]
    dk, wh = collections.Counter(), collections.defaultdict(collections.Counter)
    moved_tok, off_place = 0, 0
    for e1, e2, p1, p2 in zip(E1, E2, P1, P2):
        if list(e1) != list(e2):
            stop("key order")
        if p2 != p1 + sum(ln - lo for s, lo, ln in repl1.get(e1["line"], []) if s + lo <= p1):
            off_place += 1
        for kk in e1:
            if SKEY(e1[kk]) != SKEY(e2[kk]):
                dk[kk] += 1
                if kk == "part":
                    wh[kk][(e1["table"], e1["panel"], e1[kk] + " -> " + e2[kk])] += 1
                else:
                    wh[kk][(e1["table"], e1["panel"], "line %d" % e1["line"])] += 1
        if p1 != p2:
            moved_tok += 1
    print("   every v1 entry's token found in its cell on its line of version 1; tokens inside an OLD span:", hit1)
    print("   v1 -> v2, entry keys that differ:", dict(dk))
    for kk, cnt in wh.items():
        print("     ", kk, dict(sorted(cnt.items())))
    print("   entries whose token sits at another position of its line in v2 than in v1:", moved_tok,
          "; of all entries, not at its v1 position plus the length change of the replaced texts before it:", off_place)
    same =all(SKEY(e1[kk]) == SKEY(e2[kk]) for e1, e2 in zip(E1, E2) for kk in ("line", "table", "panel", "row", "column", "printed", "source", "selector", "stored"))
    print("   line, table, panel, row, column, printed, source, selector and stored equal on every entry:", same)
    if hit1 or not same or off_place:
        stop("cells.json version 1 -> 2")
