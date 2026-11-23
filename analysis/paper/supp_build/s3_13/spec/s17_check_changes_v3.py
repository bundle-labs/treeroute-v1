# s17_check_changes_v3.py - version 3 of TABLE_SPEC.md (2026-11-17). Read-only check of CHANGES_v3.md (as
# s12_check_changes_file.py did for CHANGES_v2.md): every fenced text in it is labelled by the paragraph before it and
# is found where its label says:
#   "OLD printed text": in OUT\reconcile\tables_agreed.md (version 2 of tables.md) and in TABLE_SPEC_v2.md;
#   "NEW printed text": in TABLE_SPEC.md and not in tables_agreed.md;
#   "v2 spec text": in TABLE_SPEC_v2.md;   "v3 spec text": in TABLE_SPEC.md;
#   "CHANGES_v2.md text before the correction": no longer in CHANGES_v2.md;
#   "CHANGES_v2.md text after the correction": in CHANGES_v2.md, marked "(corrected in version 3)".
# Also checks the SHA-256 and line counts that CHANGES_v3.md states. Prints only.
# Run from this folder: py -3.9 -I -B s17_check_changes_v3.py
import hashlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")


def rd(p):
    with open(p, "rb") as fh:
        raw = fh.read()
    return raw, raw.decode("utf-8")


_, ch = rd("CHANGES_v3.md")
_, c2 = rd("CHANGES_v2.md")
r2, s2 = rd("TABLE_SPEC_v2.md")
r3, s3 = rd("TABLE_SPEC.md")
ra, ag = rd("../reconcile/tables_agreed.md")
ok = True


def fail(m):
    global ok
    ok = False
    print("FAIL:", m)


flat = re.sub(r"\s+", " ", ch)
for raw, name in ((r2, "version 2"), (r3, "version 3")):
    h, n = hashlib.sha256(raw).hexdigest(), raw.count(b"\n")
    if h not in flat:
        fail(name + " SHA-256 not stated in CHANGES_v3.md: " + h)
    if "{:,} lines".format(n) not in flat:
        fail(name + " line count {} not stated".format(n))
    print("{}: sha256 {}..., {} lines".format(name, h[:12], n))
ha = hashlib.sha256(ra).hexdigest()
if ha not in flat or "{} lines".format(ra.count(b"\n")) not in flat:
    fail("tables_agreed.md SHA-256 or line count not stated")
n_mark = c2.count("(corrected in version 3)")
print("CHANGES_v2.md: '(corrected in version 3)' {} times".format(n_mark))
if n_mark != 2:
    fail("CHANGES_v2.md should carry the mark twice (the two corrections of V3-7)")

KINDS = ["OLD printed text", "NEW printed text", "v2 spec text", "v3 spec text",
         "CHANGES_v2.md text before the correction", "CHANGES_v2.md text after the correction"]
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
counts = {}
for at, label, text in blocks:
    found = [(label.rfind(x), x) for x in KINDS if x in label]
    if not found:
        fail("line {}: block without a label: {!r}".format(at, label[-80:]))
        continue
    kind = max(found)[1]
    counts[kind] = counts.get(kind, 0) + 1
    if kind == "OLD printed text":
        good = text in ag and text in s2
    elif kind == "NEW printed text":
        good = text in s3 and text not in ag
    elif kind == "v2 spec text":
        good = text in s2
    elif kind == "v3 spec text":
        good = text in s3
    elif kind == "CHANGES_v2.md text before the correction":
        good = text not in c2
    else:
        good = text in c2 and "(corrected in version 3)" in text
    if not good:
        fail("line {}: {} not found where it should be: {!r}".format(at, kind, text[:80]))
print("fenced texts in CHANGES_v3.md:", len(blocks), counts)
print("RESULT:", "every quoted text is where its label says" if ok else "FAILED")
sys.exit(0 if ok else 1)
