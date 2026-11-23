# s21_check_changes_v4.py - version 4 of TABLE_SPEC.md (2026-11-17). Read-only check of CHANGES_v4.md (as
# s17_check_changes_v3.py did for CHANGES_v3.md): every fenced text in it is labelled by the paragraph before it and
# is found where its label says:
#   "OLD printed text": in OUT\reconcile\tables_agreed.md (version 3 of tables.md) and in TABLE_SPEC_v3.md;
#   "NEW printed text": in TABLE_SPEC.md (version 4) and not in tables_agreed.md;
#   "OLD printed cell, made by the rule": in tables_agreed.md (a cell that a rule of the spec composes);
#   "NEW printed cell, made by the rule": not in tables_agreed.md; with the version-4 literal of the rule put back to
#       its version-3 literal it is a cell of tables_agreed.md, and the version-4 spec holds the version-4 literal;
#   "v3 spec text": in TABLE_SPEC_v3.md;   "v4 spec text": in TABLE_SPEC.md;
#   "CHANGES_v3.md text before the correction": no longer in CHANGES_v3.md;
#   "CHANGES_v3.md text after the correction": in CHANGES_v3.md, marked "(corrected in version 4)".
# Also checks the SHA-256 and line counts that CHANGES_v4.md states, the encoding of both CHANGES files, and that
# undoing the correction gives CHANGES_v3.md its size before version 4 (28,945 bytes in the folder listing taken before
# any edit). Prints only. Run from this folder: py -3.9 -I -B s21_check_changes_v4.py
import hashlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
RULE_LITERALS = [("plain tree answers", "plain answers")]  # V4-5: (version-4 literal, version-3 literal)
CHANGES_V3_SIZE_BEFORE = 28945


def rd(p):
    with open(p, "rb") as fh:
        raw = fh.read()
    return raw, raw.decode("utf-8")


rc, ch = rd("CHANGES_v4.md")
r3c, c3 = rd("CHANGES_v3.md")
r3, s3 = rd("TABLE_SPEC_v3.md")
r4, s4 = rd("TABLE_SPEC.md")
ra, ag = rd("../reconcile/tables_agreed.md")
ok = True


def fail(m):
    global ok
    ok = False
    print("FAIL:", m)


for name, raw in (("CHANGES_v4.md", rc), ("CHANGES_v3.md", r3c)):
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or b"\t" in raw or not raw.endswith(b"\n") \
            or raw.endswith(b"\n\n") or re.search(rb" \n", raw):
        fail(name + ": not UTF-8 without BOM, LF only, no tab, no trailing space, one final LF")
flat = re.sub(r"\s+", " ", ch)
for raw, name in ((r3, "version 3"), (r4, "version 4")):
    h, n = hashlib.sha256(raw).hexdigest(), raw.count(b"\n")
    if h not in flat:
        fail(name + " SHA-256 not stated in CHANGES_v4.md: " + h)
    if "{:,} lines".format(n) not in flat:
        fail(name + " line count {} not stated".format(n))
    print("{}: sha256 {}..., {} lines".format(name, h[:12], n))
ha =hashlib.sha256(ra).hexdigest()
if ha not in flat or "{} lines".format(ra.count(b"\n")) not in flat:
    fail("tables_agreed.md SHA-256 or line count not stated")
print("tables_agreed.md: sha256 {}..., {} lines".format(ha[:12], ra.count(b"\n")))
n_mark = c3.count("(corrected in version 4)")
print("CHANGES_v3.md: '(corrected in version 4)' {} times".format(n_mark))
if n_mark != 1:
    fail("CHANGES_v3.md should carry the mark once (the correction of V4-13)")

KINDS = ["OLD printed text", "NEW printed text", "OLD printed cell, made by the rule",
         "NEW printed cell, made by the rule", "v3 spec text", "v4 spec text",
         "CHANGES_v3.md text before the correction", "CHANGES_v3.md text after the correction"]
lines = ch.split("\n")
blocks, i = [], 0
while i < len(lines):
    if lines[i].startswith("```"):
        j = i + 1
        while j < len(lines) and not lines[j].startswith("```"):
            j += 1
        k = i - 1
        while k >= 0 and not lines[k].strip():
            k -= 1
        para = []
        while k >= 0 and lines[k].strip() and not lines[k].startswith("```"):
            para.insert(0, lines[k])
            k -= 1
        blocks.append((i + 1, re.sub(r"\s+", " ", " ".join(para)), "\n".join(lines[i + 1:j])))
        i = j + 1
    else:
        i += 1
ag_cells = set(c for ln in ag.split("\n") if ln.startswith("| ") for c in ln[2:-2].split(" | "))
counts = {}
before_after = {}
for at, label, text in blocks:
    found = [(label.rfind(x), x) for x in KINDS if x in label]
    if not found:
        fail("line {}: block without a label: {!r}".format(at, label[-80:]))
        continue
    kind = max(found)[1]
    counts[kind] = counts.get(kind, 0) + 1
    if kind == "OLD printed text":
        good = text in ag and text in s3
    elif kind == "NEW printed text":
        good = text in s4 and text not in ag
    elif kind == "OLD printed cell, made by the rule":
        good = text in ag_cells
    elif kind == "NEW printed cell, made by the rule":
        back = text
        for new_lit, old_lit in RULE_LITERALS:
            back = back.replace(new_lit, old_lit)
        good = text not in ag and back != text and back in ag_cells and \
            all('"' + new_lit + '"' in s4 and '"' + old_lit + '"' in s3 for new_lit, old_lit in RULE_LITERALS)
    elif kind == "v3 spec text":
        good = text in s3
    elif kind == "v4 spec text":
        good = text in s4
    elif kind == "CHANGES_v3.md text before the correction":
        good = text not in c3
        before_after["before"] = text
    else:
        good = text in c3 and "(corrected in version 4)" in text
        before_after["after"] = text
    if not good:
        fail("line {}: {} not found where it should be: {!r}".format(at, kind, text[:80]))
print("fenced texts in CHANGES_v4.md:", len(blocks), counts)

# Undoing the correction gives CHANGES_v3.md its version-3 size and line count, so nothing else in it changed size.
if "before" in before_after and "after" in before_after:
    b, a = before_after["before"], before_after["after"]
    if c3.count(a) != 1:
        fail("the corrected text is not in CHANGES_v3.md exactly once")
    undone = c3.replace(a, b).encode("utf-8")
    print("CHANGES_v3.md: now {} bytes, {} lines; with the correction undone {} bytes, {} lines (before version 4: {}"
          " bytes)".format(len(r3c), r3c.count(b"\n"), len(undone), undone.count(b"\n"), CHANGES_V3_SIZE_BEFORE))
    if len(undone) != CHANGES_V3_SIZE_BEFORE or undone.count(b"\n") != r3c.count(b"\n"):
        fail("CHANGES_v3.md changed elsewhere, or the correction changed its line count")
else:
    fail("the before and after texts of the CHANGES_v3.md correction are not both quoted")
print("RESULT:", "every quoted text is where its label says" if ok else "FAILED")
sys.exit(0 if ok else 1)
