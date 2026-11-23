# r28 (version 5, exploration): the diff of OUT\spec\TABLE_SPEC_v4.md with OUT\spec\TABLE_SPEC.md (version 5), to
# see which inputs of the reconciler's scripts version 5 changed. Read-only; prints the changed hunks (v4 and v5
# line numbers; the new section 12 only by its line range) and the fenced blocks whose content or first line changed.
import sys, difflib, hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2]
b4 = (OUT / "spec" / "TABLE_SPEC_v4.md").read_bytes()
b5 = (OUT / "spec" / "TABLE_SPEC.md").read_bytes()
print("TABLE_SPEC_v4.md", len(b4), "bytes,", b4.count(b"\n"), "LF, sha256", hashlib.sha256(b4).hexdigest())
print("TABLE_SPEC.md   ", len(b5), "bytes,", b5.count(b"\n"), "LF, sha256", hashlib.sha256(b5).hexdigest())
L4, L5 = b4.decode("utf-8").split("\n"), b5.decode("utf-8").split("\n")
sm = difflib.SequenceMatcher(None, L4, L5, autojunk=False)
n = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    n += 1
    print("== hunk %d: %s v4 %d-%d -> v5 %d-%d" % (n, tag, i1 + 1, i2, j1 + 1, j2))
    for k in range(i1, i2):
        print("  - v4 %4d: %s" % (k + 1, L4[k]))
    if j2 - j1 > 12:
        print("  + v5 %d-%d: %d lines (first: %s)" % (j1 + 1, j2, j2 - j1, L5[j1][:100]))
        continue
    for k in range(j1, j2):
        print("  + v5 %4d: %s" % (k + 1, L5[k]))
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


B4, B5 = blocks(L4), blocks(L5)
print("fenced blocks: v4", len(B4), "v5", len(B5))
for k, ((s4, x), (s5, y)) in enumerate(zip(B4, B5), 1):
    if x != y or s4 != s5:
        print("block %d (v4 L%d / v5 L%d): %d -> %d lines; first line %s; first 24 characters %s" % (
            k, s4, s5, len(x), len(y), "same" if x[:1] == y[:1] else "CHANGED", "same" if x[0][:24] == y[0][:24] else "CHANGED"))
        if x[:1] != y[:1]:
            print("   v4 first:", x[0][:120])
            print("   v5 first:", y[0][:120])
for k, (s5, y) in enumerate(B5[len(B4):], len(B4) + 1):
    print("block %d only in v5 (L%d), %d lines; first: %s" % (k, s5, len(y), y[0][:100] if y else ""))
