"""n11: names and times of the files in SHAP outside verify_v1, without entering smoke\\bardl_fix (A4's scan:
10,801 files, none created or changed at or after 2026-11-16 17:09, newest RUN_COMMANDS.md 17:05:41).
os.scandir / os.stat only; no file is opened. Prints only."""
import datetime
import os

ROOT = r"D:\treeroute\analysis\shap_v1"
SINCE = datetime.datetime(2026, 11, 16, 17, 9).timestamp()
n_files = 0
n_dirs = 0
newest = (0.0, "")
hits = []
stack = [ROOT]
while stack:
    d = stack.pop()
    n_dirs += 1
    with os.scandir(d) as it:
        for e in it:
            rel = os.path.relpath(e.path, ROOT)
            if e.is_dir(follow_symlinks=False):
                if os.path.normcase(rel) in (os.path.normcase("verify_v1"),
                                             os.path.normcase(os.path.join("smoke", "bardl_fix"))):
                    continue
                stack.append(e.path)
            else:
                st = e.stat(follow_symlinks=False)
                n_files += 1
                t = max(st.st_mtime, st.st_ctime)
                if t > newest[0]:
                    newest = (t, rel)
                if t >= SINCE:
                    hits.append((t, rel))
fmt = lambda t: datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")
print("files:", n_files, "folders (root included):", n_dirs)
print("newest:", fmt(newest[0]), newest[1])
print("at or after 17:09:", len(hits))
for t, p in sorted(hits)[:20]:
    print("  ", fmt(t), p)
