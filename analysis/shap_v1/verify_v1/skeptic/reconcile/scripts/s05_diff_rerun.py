"""Skeptic: compare the rerun's mismatches.json and summary.json with the reconciler's, ignoring run times."""
import json
import os

ORIG = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile"
RER = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\reconcile\rerun"
TIME_KEYS = {"written_at", "run_started", "run_finished", "seconds"}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in TIME_KEYS}
    if isinstance(o, list):
        return [strip(x) for x in o]
    return o


def diff(a, b, path="", out=None, lim=50):
    out = [] if out is None else out
    if len(out) >= lim:
        return out
    if type(a) != type(b):
        out.append((path, "type", type(a).__name__, type(b).__name__))
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append((path + "/" + k, "missing in " + ("orig" if k not in a else "rerun")))
            else:
                diff(a[k], b[k], path + "/" + k, out, lim)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append((path, "len", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, path + "[%d]" % i, out, lim)
    elif a != b:
        out.append((path, "value", a, b))
    return out


for fn in ("mismatches.json", os.path.join("work", "summary.json")):
    a = strip(load(os.path.join(ORIG, fn)))
    b = strip(load(os.path.join(RER, fn)))
    d = diff(a, b)
    print(fn, "differences (time keys ignored):", len(d))
    for x in d[:50]:
        print("   ", x)
