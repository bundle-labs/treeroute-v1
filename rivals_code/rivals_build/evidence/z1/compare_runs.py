"""Compare two smoke run folders file by file. Usage: py -3.9 compare_runs.py <folder A> <folder B>
GATE files (must be byte-identical): derived.json, every *preds*.parquet, every score/table csv."""
import hashlib, sys
from pathlib import Path

a, b = Path(sys.argv[1]), Path(sys.argv[2])
def files(r):
    return {p.relative_to(r).as_posix(): p for p in r.rglob("*") if p.is_file()}
fa, fb = files(a), files(b)
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def gate(name):
    n = name.split("/")[-1]
    return n == "derived.json" or ("preds" in n and n.endswith(".parquet")) or n.endswith(".csv")
same, diff, gate_bad = [], [], []
for k in sorted(set(fa) | set(fb)):
    if k not in fa or k not in fb:
        diff.append(k + " (only in %s)" % ("A" if k in fa else "B"))
        if gate(k):
            gate_bad.append(k)
        continue
    if sha(fa[k]) == sha(fb[k]):
        same.append(k)
    else:
        diff.append(k)
        if gate(k):
            gate_bad.append(k)
g = [k for k in same if gate(k)]
print("A:", a); print("B:", b)
print("gate files byte-identical: %d %s" % (len(g), g))
print("GATE FAILURES: %s" % (gate_bad or "none"))
print("other identical files: %d" % (len(same) - len(g)))
print("differing non-gate files: %s" % [k for k in diff if k not in gate_bad])
