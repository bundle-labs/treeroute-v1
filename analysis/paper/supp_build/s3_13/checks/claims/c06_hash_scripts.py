"""SHA-256 and file times of the SHAP analysis scripts and the two table builders' scripts (read only).

Lists every file directly in SHAP/scripts and SHAP/scripts/tests (names, sizes, local and UTC modification
times) and hashes the .py files, then hashes OUT/A/scripts/build_tables.py and OUT/B/scripts/build_tables.py,
and the builders' final tables.md and cells.json against the agreed copies. No script is run or imported.
"""
import datetime
import hashlib
import os
import sys

SHAP = r"D:\treeroute\analysis\shap_v1"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(os.path.dirname(HERE))


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def when(path):
    st = os.stat(path)
    loc = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    utc = datetime.datetime.utcfromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return st.st_size, loc, utc


def main():
    for sub in ("scripts", os.path.join("scripts", "tests")):
        d = os.path.join(SHAP, sub)
        names = sorted(n for n in os.listdir(d) if os.path.isfile(os.path.join(d, n)))
        print("== %s: %d files" % (sub, len(names)))
        for n in names:
            p = os.path.join(d, n)
            size, loc, utc = when(p)
            hx = sha(p) if n.endswith(".py") else "-"
            print("  %-28s %8d  local %s  utc %s  %s" % (n, size, loc, utc, hx))
    print("== builders")
    for b in ("A", "B"):
        p = os.path.join(OUT, b, "scripts", "build_tables.py")
        size, loc, utc = when(p)
        print("  %s/scripts/build_tables.py %8d  local %s  %s" % (b, size, loc, sha(p)))
    print("== final tables and cells")
    agreed_t = sha(os.path.join(OUT, "reconcile", "tables_agreed.md"))
    agreed_c = sha(os.path.join(OUT, "reconcile", "cells.json"))
    print("  reconcile/tables_agreed.md", agreed_t)
    print("  reconcile/cells.json      ", agreed_c)
    for b in ("A", "B"):
        t = sha(os.path.join(OUT, b, "tables.md"))
        c = sha(os.path.join(OUT, b, "cells.json"))
        print("  %s/tables.md %s equal %s; %s/cells.json %s equal %s" % (b, t[:12], t == agreed_t, b, c[:12], c == agreed_c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
