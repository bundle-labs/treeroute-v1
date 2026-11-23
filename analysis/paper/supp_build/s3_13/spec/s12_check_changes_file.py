# s12_check_changes_file.py - version 2 of TABLE_SPEC.md (2026-11-17). Read-only check of CHANGES_v2.md: every
# fenced text in it is labelled by the line before it and is found where its label says:
#   "OLD printed text": in OUT\reconcile\tables_agreed.md and in TABLE_SPEC_v1.md;
#   "NEW printed text": in TABLE_SPEC.md and not in tables_agreed.md;
#   "v1 spec text": in TABLE_SPEC_v1.md;   "v2 spec text": in TABLE_SPEC.md.
# Also checks the SHA-256 and line counts that CHANGES_v2.md states. Prints only.
# Run from this folder: py -3.9 -I -B s12_check_changes_file.py
import hashlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")


def rd(p):
    with open(p, "rb") as fh:
        raw = fh.read()
    return raw, raw.decode("utf-8")


_, ch = rd("CHANGES_v2.md")
r1, s1 = rd("TABLE_SPEC_v1.md")
r2, s2 = rd("TABLE_SPEC.md")
_, ag = rd("../reconcile/tables_agreed.md")
ok = True


def fail(m):
    global ok
    ok = False
    print("FAIL:", m)


h1, h2 = hashlib.sha256(r1).hexdigest(), hashlib.sha256(r2).hexdigest()
for h, n, name in ((h1, s1.count("\n"), "version 1"), (h2, s2.count("\n"), "version 2")):
    if h not in ch:
        fail(name + " SHA-256 not stated in CHANGES_v2.md: " + h)
    if "{:,} lines".format(n) not in ch and "{:,}\n  lines".format(n) not in ch:
        fail(name + " line count {} not stated".format(n))
print("version 1", h1[:12], s1.count("\n"), "lines; version 2", h2[:12], s2.count("\n"), "lines")

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
        blocks.append((i + 1, lines[k] if k >= 0 else "", "\n".join(lines[i + 1:j])))
        i = j + 1
    else:
        i += 1
counts = {}
for at, label, text in blocks:
    kinds = [x for x in ("OLD printed text", "NEW printed text", "v1 spec text", "v2 spec text") if x in label]
    if len(kinds) != 1:
        fail("line {}: block without one clear label: {!r}".format(at, label))
        continue
    kind = kinds[0]
    counts[kind] = counts.get(kind, 0) + 1
    if kind == "OLD printed text":
        good = text in ag and text in s1
    elif kind == "NEW printed text":
        good = text in s2 and text not in ag
    elif kind == "v1 spec text":
        good = text in s1
    else:
        good = text in s2
    if not good:
        fail("line {}: {} not found where it should be: {!r}".format(at, kind, text[:80]))
print("fenced texts in CHANGES_v2.md:", len(blocks), counts)
print("RESULT:", "every quoted text is where its label says" if ok else "FAILED")
sys.exit(0 if ok else 1)
