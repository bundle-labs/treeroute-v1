"""n02: print the structure of A's and B's results.json under b1 (keys and small values only). Read-only."""
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def walk(x, path, depth, maxdepth, out):
    if isinstance(x, dict):
        keys = list(x.keys())
        if depth >= maxdepth:
            out.append("%s: dict(%d) %s" % (path, len(keys), keys[:12]))
            return
        for k in keys:
            walk(x[k], path + "/" + str(k), depth + 1, maxdepth, out)
    elif isinstance(x, list):
        s = json.dumps(x)
        out.append("%s: list(%d) %s" % (path, len(x), s[:200]))
    else:
        out.append("%s: %r" % (path, x))


for who in ("A", "B"):
    R = load(V + "\\" + who + r"\results.json")
    print("=====", who, "top-level keys:", list(R.keys()))
    b1 = R["b1"]
    print("b1 keys:", list(b1.keys()))
    for p in b1:
        print("--", p, "keys:", list(b1[p].keys()) if isinstance(b1[p], dict) else type(b1[p]))
    out = []
    fire = b1["fire"]
    for lev in ("feature", "variable"):
        lv = fire[lev]
        print("fire", lev, "keys:", list(lv.keys()))
        for k in lv:
            if k == "importance":
                imp = lv[k]
                print("  importance keys:", list(imp.keys()) if isinstance(imp, dict) else type(imp))
                if isinstance(imp, dict):
                    for kk in imp:
                        v = imp[kk]
                        if isinstance(v, dict):
                            ks = list(v.keys())
                            print("    ", kk, "dict(%d)" % len(ks), ks[:5])
                            if ks:
                                print("       first:", json.dumps(v[ks[0]])[:400])
                        elif isinstance(v, list):
                            print("    ", kk, "list(%d)" % len(v), json.dumps(v[:2])[:400])
                        else:
                            print("    ", kk, repr(v)[:200])
            else:
                walk(lv[k], "fire/%s/%s" % (lev, k), 0, 3, out)
    for line in out:
        print(line[:400])
    for k in fire:
        if k not in ("feature", "variable"):
            print("fire/%s:" % k, json.dumps(fire[k])[:1500])
    for p in ("coral", "defo"):
        if p in b1:
            print("%s:" % p, json.dumps(b1[p])[:1500])
