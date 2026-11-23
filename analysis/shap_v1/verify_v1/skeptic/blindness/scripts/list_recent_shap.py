# List SHAP's files and folders (outside V) whose modification or creation time is at or after a cut-off.
# Names and times only: no file is opened. V (verify_v1) is pruned, and smoke\bardl_fix is never entered:
# only its own directory entry (from the listing of smoke) is reported, with its times.
# Usage: py -3.9 -I -B list_recent_shap.py "2026-11-16 17:09"
import datetime as dt
import os
import sys

SHAP = r"D:\treeroute\analysis\shap_v1"
PRUNE = {os.path.normcase(os.path.join(SHAP, "verify_v1"))}
NO_ENTER = {os.path.normcase(os.path.join(SHAP, "smoke", "bardl_fix"))}
cut = dt.datetime.strptime(sys.argv[1], "%Y-%m-%d %H:%M").timestamp()


def fmt(t):
    return dt.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")


n_files = n_dirs = 0
hits = []
newest = (0.0, "")
stack = [SHAP]
while stack:
    d = stack.pop()
    with os.scandir(d) as it:
        for e in it:
            full = os.path.normcase(e.path)
            st = e.stat(follow_symlinks=False)
            rel = "SHAP" + e.path[len(SHAP):]
            if e.is_dir(follow_symlinks=False):
                n_dirs += 1
                if full in PRUNE:
                    continue
                if full in NO_ENTER:
                    hits.append(("dir(not entered)", rel, fmt(st.st_mtime), fmt(st.st_ctime),
                                 st.st_mtime >= cut or st.st_ctime >= cut))
                    continue
                if st.st_mtime >= cut or st.st_ctime >= cut:
                    hits.append(("dir", rel, fmt(st.st_mtime), fmt(st.st_ctime), True))
                stack.append(e.path)
            else:
                n_files += 1
                if st.st_mtime > newest[0]:
                    newest = (st.st_mtime, rel)
                if st.st_mtime >= cut or st.st_ctime >= cut:
                    hits.append(("file", rel, fmt(st.st_mtime), fmt(st.st_ctime), True))
print("cut-off (local):", sys.argv[1], "| files scanned:", n_files, "| folders scanned:", n_dirs)
print("newest file outside V by modification time:", newest[1], fmt(newest[0]) if newest[0] else "-")
for kind, rel, m, c, recent in sorted(hits, key=lambda h: h[1]):
    print("%-17s %-6s modified %s created %s  %s" % (kind, "RECENT" if recent else "", m, c, rel))
print("entries at or after the cut-off:", sum(1 for h in hits if h[4]))
