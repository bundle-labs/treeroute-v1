"""Read-only: names-and-times scan of SHAP outside V, never entering V or smoke\\bardl_fix.
Prints counts and the newest entries only (relative paths inside SHAP; no file contents are read)."""
import datetime as dt
import os

SHAP = r"D:\treeroute\analysis\shap_v1"
SKIP = {os.path.normcase(os.path.join(SHAP, "verify_v1")), os.path.normcase(os.path.join(SHAP, "smoke", "bardl_fix"))}
CUT = dt.datetime(2026, 11, 16, 17, 9, 0).timestamp()

n_files = 0
n_dirs = 0
newest = []
late = []
skipped = []
stack = [SHAP]
while stack:
    d = stack.pop()
    try:
        it = list(os.scandir(d))
    except OSError as e:
        print("cannot list", os.path.relpath(d, SHAP), type(e).__name__)
        continue
    for e in it:
        p = os.path.normcase(e.path)
        if e.is_dir(follow_symlinks=False):
            if p in SKIP:
                skipped.append(os.path.relpath(e.path, SHAP))
                continue
            n_dirs += 1
            stack.append(e.path)
        else:
            n_files += 1
            st = e.stat(follow_symlinks=False)
            t = max(st.st_mtime, st.st_ctime)
            newest.append((st.st_mtime, os.path.relpath(e.path, SHAP)))
            if st.st_mtime >= CUT or st.st_ctime >= CUT:
                late.append((dt.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                             dt.datetime.fromtimestamp(st.st_ctime).isoformat(timespec="seconds"),
                             os.path.relpath(e.path, SHAP)))
newest.sort(reverse=True)
print("files", n_files, "dirs", n_dirs, "skipped", skipped)
print("files created or modified at or after 2026-11-16 17:09:", len(late))
for row in late[:20]:
    print("   ", row)
print("newest 5 by mtime:")
for t, p in newest[:5]:
    print("   ", dt.datetime.fromtimestamp(t).isoformat(timespec="seconds"), p)
