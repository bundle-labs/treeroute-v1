"""Print each problem's rebuild gates.json: result, and per gate its pass flag and scalar values (read only).

Usage: py -3.9 -I -B gates_peek.py [<gate-substring>]
With a gate substring, also prints that gate's values in full (json).
"""
import json
import os
import sys

REB = r"D:\treeroute\analysis\shap_v1\rebuild"


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else None
    for p in ("pm25", "ndvi", "fire", "defo", "coral"):
        f = os.path.join(REB, p, "lead_0", "gates.json")
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        print("==", p, "top keys:", list(d.keys()))
        print("   result:", d.get("result"))
        gates = d.get("gates", {})
        for g, v in gates.items():
            if isinstance(v, dict):
                scal = {k: x for k, x in v.items() if isinstance(x, (int, float, str, bool)) or x is None}
                print("   %s: %s" % (g, scal))
                if want and want in g:
                    print("      values:", json.dumps(v.get("values"), ensure_ascii=True)[:1500])
            else:
                print("   %s: %r" % (g, v))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
