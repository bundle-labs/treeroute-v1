# Round 14, implementer A: print meta.json fields other than the long lists (structure only).
import json, os, sys

SHAP = r"D:\treeroute\analysis\shap_v1"
SKIP = {"players", "variables", "variable_map"}


def show(p, m):
    path = os.path.join(SHAP, "out", p, "lead_0", m, "meta.json")
    with open(path, "r", encoding="utf-8") as fh:
        meta = json.load(fh)
    print("=" * 20, p, m)
    for k in sorted(meta):
        if k in SKIP:
            continue
        s = json.dumps(meta[k])
        if len(s) > 1500:
            s = s[:1500] + "..."
        print(" ", k, "=", s)


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        p, m = arg.split(":")
        show(p, m)
