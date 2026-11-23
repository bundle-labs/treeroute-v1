# n13: count byte-order marks in the 226 archived files of OUT (spec, A, B, reconcile, skeptic, _brief): first bytes only,
# and whether each decodes as UTF-8. Prints counts and the BOM files' relative paths. Read-only.
import collections
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
c = collections.Counter()
bom_files = []
bad = []
n = 0
for top in ("spec", "A", "B", "reconcile", "skeptic", "_brief"):
    for dp, dn, fn in os.walk(os.path.join(OUT, top)):
        for f in fn:
            p = os.path.join(dp, f)
            n += 1
            b = open(p, "rb").read()
            if b.startswith(b"\xef\xbb\xbf"):
                c["utf-8-sig"] += 1
                bom_files.append(os.path.relpath(p, OUT))
            elif b.startswith((b"\xff\xfe", b"\xfe\xff")):
                c["utf-16"] += 1
                bom_files.append(os.path.relpath(p, OUT))
            else:
                try:
                    b.decode("utf-8")
                    c["utf-8"] += 1
                except UnicodeDecodeError:
                    c["not utf-8"] += 1
                    bad.append(os.path.relpath(p, OUT))
print("files", n, dict(c))
print("BOM files:", bom_files)
print("not utf-8:", bad)
