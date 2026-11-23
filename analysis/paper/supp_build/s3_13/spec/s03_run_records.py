"""Spec writer's helper (read-only): the check fields of every piece's run records.

Usage: py -3.9 -I -B s03_run_records.py
Per problem and piece: meta.json without its long lists (players, variables, variable_map; their lengths are shown),
exactness.json, ridge_shap_exactness.json (top-level keys and the stage/pass/bit-count fields), rows.parquet.done.json
(keys, seconds, finished). Long strings are cut. Opens only SHAP\\out\\<p>\\lead_0\\<piece>\\ records. Writes nothing.
"""
import json
import os

SHAP = r"D:\treeroute\analysis\shap_v1"
PROBLEMS = ["coral", "fire", "pm25", "defo", "ndvi"]
LONG = {"players", "variables", "variable_map", "structural_zero_violation_players"}


def short(v, n=160):
    s = json.dumps(v)
    return s if len(s) <= n else s[:n] + "...(%d chars)" % len(s)


def show(d, ind=4, depth=0, maxdepth=3):
    for k, v in d.items():
        if k in LONG and isinstance(v, (list, dict)):
            print(" " * ind + "%s: <%s of %d>" % (k, type(v).__name__, len(v)))
        elif isinstance(v, dict) and depth < maxdepth and len(json.dumps(v)) > 160:
            print(" " * ind + "%s:" % k)
            show(v, ind + 2, depth + 1, maxdepth)
        else:
            print(" " * ind + "%s: %s" % (k, short(v)))


def main():
    for p in PROBLEMS:
        base = os.path.join(SHAP, "out", p, "lead_0")
        for piece in sorted(os.listdir(base)):
            if piece == "compare":
                continue
            d = os.path.join(base, piece)
            print("=" * 100)
            print(p, piece)
            for fn in ("meta.json", "exactness.json", "ridge_shap_exactness.json", "rows.parquet.done.json"):
                fp = os.path.join(d, fn)
                if not os.path.exists(fp):
                    continue
                with open(fp, encoding="utf-8") as f:
                    x = json.load(f)
                print("  -- %s" % fn)
                if isinstance(x, dict):
                    show(x)
                else:
                    print("    " + short(x, 400))


if __name__ == "__main__":
    main()
