# n01: compare every table block of tables_agreed.md (v5) with the staged S3_posthoc.md and table_9.md.
# Read-only on all inputs; prints to screen only.
import difflib
import hashlib
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
OUT = os.path.join(ROOT, r"paper\supp_build\s3_13")
STAGE = os.path.join(OUT, "stage")
AGREED = os.path.join(OUT, r"reconcile\tables_agreed.md")
S3 = os.path.join(STAGE, r"paper\draft\S3_posthoc.md")
T9 = os.path.join(STAGE, r"paper\draft\tables\table_9.md")


def rb(p):
    with open(p, "rb") as f:
        return f.read()


def info(p):
    b = rb(p)
    return "%s bytes=%d sha256=%s BOM=%s CR=%d LF=%d finalLF=%s" % (
        os.path.basename(p), len(b), hashlib.sha256(b).hexdigest(), b.startswith(b"\xef\xbb\xbf"),
        b.count(b"\r"), b.count(b"\n"), b.endswith(b"\n"))


for p in (AGREED, S3, T9):
    print(info(p))

agreed = rb(AGREED).decode("utf-8")
lines = agreed.split("\n")
cap_re = re.compile(r"^\*\*Table (9|S3\.\d+)[ .]")
starts = [i for i, l in enumerate(lines) if cap_re.match(l)]
blocks = []
for k, s in enumerate(starts):
    e = len(lines)
    for j in range(s + 1, len(lines)):
        if cap_re.match(lines[j]) or lines[j].startswith("## "):
            e = j
            break
    while e > s and lines[e - 1].strip() == "":
        e -= 1
    name = cap_re.match(lines[s]).group(1)
    blocks.append((name, s + 1, e, "\n".join(lines[s:e])))

print("blocks:", [(n, a, b) for n, a, b, _ in blocks])

s3 = rb(S3).decode("utf-8")
t9 = rb(T9).decode("utf-8")

for name, a, b, text in blocks:
    target = t9 if name == "9" else s3
    tname = "table_9.md" if name == "9" else "S3_posthoc.md"
    # exact match as whole lines
    pat = "\n" + text + "\n"
    cnt = ("\n" + target).count(pat)
    print("\n=== Table %s (agreed lines %d-%d, %d bytes) in %s: exact whole-line occurrences = %d" % (
        name, a, b, len(text.encode("utf-8")), tname, cnt))
    if cnt == 1:
        continue
    # find the caption line in the target and diff the same number of lines
    tl = target.split("\n")
    cap = text.split("\n")[0]
    cap_key = cap[:40]
    idx = [i for i, l in enumerate(tl) if l.startswith(cap_key)]
    print("  caption-key matches in target at lines:", [i + 1 for i in idx])
    if not idx:
        continue
    i0 = idx[0]
    nlines = len(text.split("\n"))
    # extend to the next caption or heading in the target for the diff
    j = i0 + 1
    while j < len(tl) and not cap_re.match(tl[j]) and not tl[j].startswith("## ") and not tl[j].startswith("**treeroute"):
        j += 1
    seg = tl[i0:i0 + nlines]
    d = list(difflib.unified_diff(text.split("\n"), seg, "agreed", tname, lineterm="", n=0))
    for x in d:
        if len(x) > 600:
            print("  " + x[:600] + " ...[%d chars]" % len(x))
        else:
            print("  " + x)
    # character-level detail for changed lines
    sm = difflib.SequenceMatcher(None, text.split("\n"), seg, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        for ii, jj in zip(range(i1, i2), range(j1, j2)):
            A = text.split("\n")[ii]
            B = seg[jj]
            cm = difflib.SequenceMatcher(None, A, B, autojunk=False)
            for t2, x1, x2, y1, y2 in cm.get_opcodes():
                if t2 != "equal":
                    print("   char %s: agreed[%d:%d]=%r -> staged[%d:%d]=%r" % (t2, x1, x2, A[x1:x2], y1, y2, B[y1:y2]))
