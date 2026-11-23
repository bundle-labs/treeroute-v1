"""Print the top-level keys of each problem's compare/per_lead.json and its scalar fields (read only).

Usage: py -3.9 -I -B per_lead_keys.py
Nested dicts and lists are summarised by their type and size only.
"""
import json
import os
import sys

OUT = r"D:\treeroute\analysis\shap_v1\out"


def main():
    for p in ("pm25", "ndvi", "fire", "defo", "coral"):
        f = os.path.join(OUT, p, "lead_0", "compare", "per_lead.json")
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        print("==", p)
        for k in d:
            v = d[k]
            if isinstance(v, (int, float, str, bool)) or v is None:
                print("  %s = %r" % (k, v))
            elif isinstance(v, dict):
                print("  %s: dict(%d) keys %s" % (k, len(v), list(v.keys())[:12]))
            elif isinstance(v, list):
                print("  %s: list(%d) %s" % (k, len(v), v[:6] if all(isinstance(x, (str, int, float)) for x in v[:6]) else "..."))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
