"""Print the key structure (no values) of the 'b1' part of the re-computation's results file.

Read only. For each problem and level under b1, prints the keys, and for per-player blocks the sub-keys
and the number of entries, so that the claim "every B1 player's importance, share and signed mean, each
with its interval, is in results.json key b1" can be checked without printing any number.
"""
import json
import sys

PATH = r"D:\treeroute\analysis\shap_v1\verify_v1\A\results.json"


def shape(x, depth=0, maxdepth=3):
    pad = "  " * depth
    if isinstance(x, dict):
        keys = list(x.keys())
        if depth >= maxdepth:
            return pad + "dict(%d keys: %s%s)" % (len(keys), ", ".join(map(str, keys[:8])), "..." if len(keys) > 8 else "")
        out = [pad + "dict(%d keys)" % len(keys)]
        shown = keys if len(keys) <= 12 else keys[:6]
        for k in shown:
            out.append(pad + "  [" + str(k) + "]")
            out.append(shape(x[k], depth + 2, maxdepth))
        if len(keys) > 12:
            out.append(pad + "  ... (%d more keys)" % (len(keys) - 6))
        return "\n".join(out)
    if isinstance(x, list):
        t = type(x[0]).__name__ if x else "-"
        return pad + "list(len %d, first item type %s)" % (len(x), t)
    return pad + type(x).__name__


def main():
    with open(PATH, "r", encoding="utf-8") as fh:
        res = json.load(fh)
    print("top-level keys:", list(res.keys()))
    b1 = res.get("b1")
    if not isinstance(b1, dict):
        print("no b1 dict")
        return 1
    print("b1 keys:", list(b1.keys()))
    for p, blk in b1.items():
        print("== b1.%s keys: %s" % (p, list(blk.keys()) if isinstance(blk, dict) else type(blk).__name__))
        if not isinstance(blk, dict):
            continue
        for lev in ("variable", "feature"):
            if lev in blk:
                L = blk[lev]
                print("   b1.%s.%s keys: %s" % (p, lev, list(L.keys()) if isinstance(L, dict) else type(L).__name__))
                if isinstance(L, dict) and "importance" in L:
                    imp = L["importance"]
                    if isinstance(imp, dict):
                        print("      importance keys:", list(imp.keys())[:20])
                        for k, v in imp.items():
                            if isinstance(v, dict):
                                print("        importance.%s: dict(%d keys)" % (k, len(v)))
                                first = next(iter(v.values())) if v else None
                                if isinstance(first, dict):
                                    print("          first entry keys:", list(first.keys()))
                            elif isinstance(v, list):
                                print("        importance.%s: list(len %d)" % (k, len(v)))
                                if v and isinstance(v[0], dict):
                                    print("          first item keys:", list(v[0].keys()))
                            else:
                                print("        importance.%s: %s" % (k, type(v).__name__))
                    elif isinstance(imp, list):
                        print("      importance: list(len %d)" % len(imp))
                        if imp and isinstance(imp[0], dict):
                            print("        first item keys:", list(imp[0].keys()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
