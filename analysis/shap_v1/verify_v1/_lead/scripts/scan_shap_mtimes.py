"""List files in SHAP (outside verify_v1, without entering smoke\\bardl_fix) created or modified at or after a time.

Usage: py -3.12 -X utf8 -I scan_shap_mtimes.py <SHAP root> "<YYYY-MM-DD HH:MM>"
Uses os.stat only; no file is opened.
"""
import datetime
import os
import sys


def main():
    root, since_txt = sys.argv[1], sys.argv[2]
    since = datetime.datetime.strptime(since_txt, "%Y-%m-%d %H:%M").timestamp()
    n_files = n_dirs = 0
    newest = (0.0, "")
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        if rel == ".":
            dirnames[:] = [d for d in dirnames if d != "verify_v1"]
        if os.path.normcase(rel) == os.path.normcase("smoke"):
            dirnames[:] = [d for d in dirnames if d != "bardl_fix"]
        n_dirs += 1
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            st = os.stat(p)
            n_files += 1
            t = max(st.st_mtime, st.st_ctime)
            if t > newest[0]:
                newest = (t, os.path.relpath(p, root))
            if t >= since:
                hits.append((t, os.path.relpath(p, root)))
    fmt = lambda t: datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")
    print("scanned %d files in %d folders (verify_v1 and smoke\\bardl_fix not entered)" % (n_files, n_dirs))
    print("newest (max of modified, created):", fmt(newest[0]), newest[1])
    print("files at or after %s: %d" % (since_txt, len(hits)))
    for t, p in sorted(hits):
        print("  ", fmt(t), p)
    bf = os.path.join(root, "smoke", "bardl_fix")
    if os.path.isdir(bf):
        print("bardl_fix folder entry modified:", fmt(os.stat(bf).st_mtime))


if __name__ == "__main__":
    main()
