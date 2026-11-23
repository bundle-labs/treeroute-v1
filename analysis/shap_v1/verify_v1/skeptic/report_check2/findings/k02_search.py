# Read-only: search report.md (v2) and report.md.before_fix1 (v1) for given strings, with line numbers.
import sys

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
files = {"v2": V + r"\reconcile\report.md", "v1": V + r"\reconcile\report.md.before_fix1"}
terms = sys.argv[1:]
for tag, p in files.items():
    lines = open(p, encoding="utf-8").read().split("\n")
    for t in terms:
        hits = [(i + 1, l.strip()) for i, l in enumerate(lines) if t in l]
        print("[%s] %r: %d" % (tag, t, len(hits)))
        for n, l in hits:
            print("   %4d  %s" % (n, l[:200]))
