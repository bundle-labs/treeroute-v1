# r17 (version 3, exploration): the diff of OUT\spec\TABLE_SPEC_v2.md with OUT\spec\TABLE_SPEC.md (version 3), to
# see which inputs of the reconciler's scripts version 3 changed. Read-only; prints the changed hunks (v2 and v3
# line numbers) and the fenced blocks whose content or first line changed.
import sys, difflib, hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2]
b2 = (OUT / "spec" / "TABLE_SPEC_v2.md").read_bytes()
b3 = (OUT / "spec" / "TABLE_SPEC.md").read_bytes()
print("TABLE_SPEC_v2.md", len(b2), "bytes, sha256", hashlib.sha256(b2).hexdigest())
print("TABLE_SPEC.md   ", len(b3), "bytes, sha256", hashlib.sha256(b3).hexdigest())
L2, L3 = b2.decode("utf-8").split("\n"), b3.decode("utf-8").split("\n")
sm = difflib.SequenceMatcher(None, L2, L3, autojunk=False)
n = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    n += 1
    print("== hunk %d: %s v2 %d-%d -> v3 %d-%d" % (n, tag, i1 + 1, i2, j1 + 1, j2))
    for k in range(i1, i2):
        print("  - v2 %4d: %s" % (k + 1, L2[k]))
    for k in range(j1, j2):
        print("  + v3 %4d: %s" % (k + 1, L3[k]))
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


B2, B3 = blocks(L2), blocks(L3)
print("fenced blocks: v2", len(B2), "v3", len(B3))
for k, ((s2, x), (s3, y)) in enumerate(zip(B2, B3), 1):
    if x != y:
        print("block %d (v2 L%d / v3 L%d): %d -> %d lines; first line %s" % (k, s2, s3, len(x), len(y), "same" if x[:1] == y[:1] else "CHANGED"))
        if x[:1] != y[:1]:
            print("   v2 first:", x[0][:120])
            print("   v3 first:", y[0][:120])
