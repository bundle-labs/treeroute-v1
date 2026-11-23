# Read-only: count the rows and values of Table S4.14 in the base and staged S4, and list duplicates.
import collections, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.normpath(os.path.join(HERE, "..", ".."))
for label, p in (("base", os.path.join(HERE, "work", "paper__draft__S4_provenance.md.base")),
                 ("staged", os.path.join(STAGE, "paper", "draft", "S4_provenance.md"))):
    t = open(p, "rb").read().decode("utf-8").replace("\r\n", "\n")
    i0 = t.index("**Table S4.14. Full hashes.**")
    i1 = t.index("<!-- Table S4.14 generated", i0)
    lines = t[i0:i1].split("\n")
    rows = [l for l in lines if re.match(r"^\| .+ \| [a-z ]+ \| `[0-9a-f]{64}` \|$", l)]
    other = [l for l in lines if "`" in l and l not in rows]
    vals = [re.search(r"`([0-9a-f]{64})`", l).group(1) for l in rows]
    dup = [v for v, n in collections.Counter(vals).items() if n > 1]
    print(label, "rows with a value:", len(rows), "distinct:", len(set(vals)), "duplicated values:", len(dup))
    for v in dup:
        print("   dup", v[:8], [l.split(" | ")[0][2:] for l in rows if v in l])
    for l in other:
        print("   other line with a backtick:", l[:120])
    groups = [l for l in lines if l.startswith("| **")]
    print("   group headings:", len(groups))
