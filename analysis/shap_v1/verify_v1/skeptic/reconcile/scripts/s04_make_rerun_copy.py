"""Skeptic: copy V\\reconcile\\reconcile.py and rlib.py into V\\skeptic\\reconcile\\rerun\\, changing ONLY the folder the
copy writes into (rlib.RC) and the folder it imports rlib from (reconcile.py's sys.path line). Every substitution
must apply exactly once; the originals are read, never written."""
import hashlib
import os

SRC = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile"
DST = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\reconcile\rerun"
os.makedirs(DST, exist_ok=True)


def sub_once(txt, old, new, what):
    n = txt.count(old)
    if n != 1:
        raise SystemExit("%s: expected 1 occurrence, found %d" % (what, n))
    return txt.replace(old, new)


with open(os.path.join(SRC, "rlib.py"), "r", encoding="utf-8") as f:
    rl = f.read()
with open(os.path.join(SRC, "reconcile.py"), "r", encoding="utf-8") as f:
    rc = f.read()
print("source rlib.py sha256", hashlib.sha256(rl.encode("utf-8")).hexdigest())
print("source reconcile.py sha256", hashlib.sha256(rc.encode("utf-8")).hexdigest())

rl2 = sub_once(rl, 'RC = V + r"\\reconcile"', 'RC = V + r"\\skeptic\\reconcile\\rerun"', "rlib RC")
rc2 = sub_once(rc, 'sys.path.insert(0, r"D:\\treeroute\\analysis\\shap_v1\\verify_v1\\reconcile")',
               'sys.path.insert(0, r"D:\\treeroute\\analysis\\shap_v1\\verify_v1\\skeptic\\reconcile\\rerun")',
               "reconcile sys.path")
for fn, txt in (("rlib.py", rl2), ("reconcile.py", rc2)):
    p = os.path.join(DST, fn)
    assert os.path.normpath(p).lower().startswith(os.path.normpath(DST).lower())
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)
    print("wrote", p)
# show every remaining absolute path literal in the copies (must point at SHAP read paths or the rerun folder)
import re
for fn, txt in (("rlib.py", rl2), ("reconcile.py", rc2)):
    for m in re.finditer(r'r"(D:[^"]*)"', txt):
        print(fn, "path literal:", m.group(1))
