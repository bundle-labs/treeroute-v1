# n10: recompute the SHA-256 values printed in staged S4 (Table S4.11 row 628 and its comment; Table S4.14's Part 628
# groups) and fact A27; check file times of the SHAP scripts; recount Table S4.14 (live and staged). Read-only.
import datetime
import hashlib
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
OUT = os.path.join(ROOT, r"paper\supp_build\s3_13")
S = r"D:\treeroute\analysis\shap_v1"
S4_STAGE = os.path.join(OUT, r"stage\paper\draft\S4_provenance.md")
S4_LIVE = os.path.join(ROOT, r"paper\draft\S4_provenance.md")
FACTS = os.path.join(OUT, r"stage\paper\PAPER_FACTS.md")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# the scripts folders, names only (no content listing beyond .py)
sc = sorted(e.name for e in os.scandir(os.path.join(S, "scripts")) if e.is_file() and e.name.endswith(".py"))
st = sorted(e.name for e in os.scandir(os.path.join(S, "scripts", "tests")) if e.is_file() and e.name.endswith(".py"))
print("scripts/*.py:", len(sc), sc)
print("scripts/tests/*.py:", len(st), st)
others = sorted(e.name for e in os.scandir(os.path.join(S, "scripts")) if e.is_file() and not e.name.endswith(".py"))
print("scripts/ non-.py files:", others)
files = {}
for n in sc:
    files["scripts/" + n] = os.path.join(S, "scripts", n)
for n in st:
    files["scripts/tests/" + n] = os.path.join(S, "scripts", "tests", n)
files["A/scripts/build_tables.py"] = os.path.join(OUT, r"A\scripts\build_tables.py")
files["B/scripts/build_tables.py"] = os.path.join(OUT, r"B\scripts\build_tables.py")
H = {}
for k, p in files.items():
    H[k] = sha(p)
    m = datetime.datetime.fromtimestamp(os.stat(p).st_mtime)
    print("%-40s %s  mtime(local) %s" % (k, H[k], m.strftime("%Y-%m-%d %H:%M:%S")))

s4 = open(S4_STAGE, "rb").read().decode("utf-8")
# Table S4.11 row 628
row = [l for l in s4.split("\n") if l.startswith("| 628 |")]
print("\nS4.11 row 628 found:", len(row))
cells = row[0].split(" | ")
names = cells[2].split("; ")
prefs = cells[3].rstrip(" |\r").split("; ")
print("names", len(names), "prefixes", len(prefs))
# expand names: 'scripts/bardl_shap.py' then bare names inherit the folder until the next folder prefix
cur = ""
full = []
for n in names:
    if "/" in n:
        cur = n.rsplit("/", 1)[0] + "/"
        full.append(n)
    else:
        full.append(cur + n)
bad = 0
for n, p in zip(full, prefs):
    ok = n in H and H[n][:8] == p
    bad += not ok
    print("  S4.11 %-40s %s %s" % (n, p, "OK" if ok else "BAD (computed %s)" % H.get(n, "?")[:8]))
print("S4.11 row names cover all 19 hashed files:", sorted(full) == sorted(H.keys()))
# comment full hashes
for k, v in H.items():
    nm = k.split("/", 1)[1] if k.startswith(("A/", "B/")) else k
    pat = re.escape(k) + " " + v
    c = len(re.findall(pat, s4))
    print("  S4.11 comment %-40s full hash present %d" % (k, c))
# Table S4.14 rows
for k, v in H.items():
    rr = [l for l in s4.split("\n") if l.startswith("| " + k + " | file | `" + v + "` |")]
    print("  S4.14 %-40s %s" % (k, "OK" if len(rr) == 1 else "BAD (%d)" % len(rr)))


def s414_count(text):
    lines = text.replace("\r\n", "\n").split("\n")
    i0 = [i for i, l in enumerate(lines) if l.startswith("**Table S4.14")][0]
    vals = []
    for l in lines[i0 + 1:]:
        if l.startswith("**Table S4.") or l.startswith("## "):
            break
        if l.startswith("|"):
            vals += re.findall(r"`([0-9a-f]{64})`", l)
    return vals


for name, path in (("live", S4_LIVE), ("staged", S4_STAGE)):
    t = open(path, "rb").read().decode("utf-8")
    v = s414_count(t)
    pre = {}
    for x in set(v):
        pre.setdefault(x[:8], set()).add(x)
    clash = {k: s for k, s in pre.items() if len(s) > 1}
    print("Table S4.14 %s: %d values, %d distinct, prefix clashes %d" % (name, len(v), len(set(v)), len(clash)))
    # every 64-hex string in the file present in the table?
    allhex = set(re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", t))
    print("   64-hex strings in file: %d, not in table: %d" % (len(allhex), len(allhex - set(v))))

# A27 and tables/cells hashes
for k in (r"A\tables.md", r"B\tables.md", r"reconcile\tables_agreed.md", r"A\cells.json", r"B\cells.json", r"reconcile\cells.json"):
    print("A27 %-30s %s" % (k, sha(os.path.join(OUT, k))))
facts = open(FACTS, "rb").read().decode("utf-8")
a27 = re.search(r"^- \*\*A27 .*$", facts, flags=re.M).group(0)
print("A27 prefixes in fact:", re.findall(r"\b[0-9a-f]{8}\.\.\.", a27))
