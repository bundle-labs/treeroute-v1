import os, datetime
SHAP = r"D:\treeroute\analysis\shap_v1"
cut = datetime.datetime(2026, 11, 16, 17, 9, 0).timestamp()
nfiles = 0
ndirs = 0
newest = (0, None)
newest_c = (0, None)
late = []
for root, dirs, files in os.walk(SHAP):
    rel = os.path.relpath(root, SHAP)
    if rel == ".":
        dirs[:] = [d for d in dirs if d != "verify_v1"]
    if os.path.normcase(rel) == os.path.normcase("smoke"):
        dirs[:] = [d for d in dirs if d != "bardl_fix"]
    ndirs += len(dirs)
    for f in files:
        p = os.path.join(root, f)
        st = os.stat(p)
        nfiles += 1
        if st.st_mtime > newest[0]:
            newest = (st.st_mtime, os.path.relpath(p, SHAP))
        if st.st_ctime > newest_c[0]:
            newest_c = (st.st_ctime, os.path.relpath(p, SHAP))
        if st.st_mtime >= cut or st.st_ctime >= cut:
            late.append(os.path.relpath(p, SHAP))
fmt = lambda t: datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")
print("files", nfiles, "folders", ndirs)
print("newest mtime", fmt(newest[0]), newest[1])
print("newest ctime", fmt(newest_c[0]), newest_c[1])
print("created/changed at or after 17:09:", len(late), late[:10])
