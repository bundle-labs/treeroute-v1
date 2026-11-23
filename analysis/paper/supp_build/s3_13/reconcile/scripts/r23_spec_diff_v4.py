# r23 (version 4, exploration): the diff of OUT\spec\TABLE_SPEC_v3.md with OUT\spec\TABLE_SPEC.md (version 4), to
# see which inputs of the reconciler's scripts version 4 changed. Read-only; prints the changed hunks (v3 and v4
# line numbers; the new section 11 only by its line range) and the fenced blocks whose content or first line changed.
import sys, difflib, hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2]
b3 = (OUT / "spec" / "TABLE_SPEC_v3.md").read_bytes()
b4 = (OUT / "spec" / "TABLE_SPEC.md").read_bytes()
print("TABLE_SPEC_v3.md", len(b3), "bytes,", b3.count(b"\n"), "LF, sha256", hashlib.sha256(b3).hexdigest())
print("TABLE_SPEC.md   ", len(b4), "bytes,", b4.count(b"\n"), "LF, sha256", hashlib.sha256(b4).hexdigest())
L3, L4 = b3.decode("utf-8").split("\n"), b4.decode("utf-8").split("\n")
sm = difflib.SequenceMatcher(None, L3, L4, autojunk=False)
n = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    n += 1
    print("== hunk %d: %s v3 %d-%d -> v4 %d-%d" % (n, tag, i1 + 1, i2, j1 + 1, j2))
    for k in range(i1, i2):
        print("  - v3 %4d: %s" % (k + 1, L3[k]))
    if j2 - j1 > 12:
        print("  + v4 %d-%d: %d lines (first: %s)" % (j1 + 1, j2, j2 - j1, L4[j1][:100]))
        continue
    for k in range(j1, j2):
        print("  + v4 %4d: %s" % (k + 1, L4[k]))
print("hunks:", n)


def blocks(L):
    out, cur, start = [], None, None
    for i, l in enumerate(L):
        if l.startswith("```"):
            if cur is None:
                cur, start = [], i + 1
            else:
                out.append((start, cur))
                cur = None
            continue
        if cur is not None:
            cur.append(l)
    return out


B3, B4 = blocks(L3), blocks(L4)
print("fenced blocks: v3", len(B3), "v4", len(B4))
for k, ((s3, x), (s4, y)) in enumerate(zip(B3, B4), 1):
    if x != y or s3 != s4:
        print("block %d (v3 L%d / v4 L%d): %d -> %d lines; first line %s" % (k, s3, s4, len(x), len(y), "same" if x[:1] == y[:1] else "CHANGED"))
        if x[:1] != y[:1]:
            print("   v3 first:", x[0][:120])
            print("   v4 first:", y[0][:120])
for k, (s4, y) in enumerate(B4[len(B3):], len(B3) + 1):
    print("block %d only in v4 (L%d), %d lines; first: %s" % (k, s4, len(y), y[0][:100] if y else ""))
