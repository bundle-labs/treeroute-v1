"""Compare A's and B's B1 records stored side by side in V\\reconcile\\work\\summary.json (key b1).

Usage: py -3.12 -X utf8 -I -B compare_b1_records.py <summary.json>
For every problem, every field named A_<x> is compared with B_<x> (exact equality of the stored JSON values); for
defo, both identity records are printed beside the reconciler's own recomputation (identity_reconciler).
"""
import json
import sys


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        s = json.load(f)
    b1 = s["b1"]
    n_pairs = n_equal = 0
    for p, rec in b1.items():
        fields = sorted(k[2:] for k in rec if k.startswith("A_"))
        for x in fields:
            a, b = rec.get("A_" + x), rec.get("B_" + x)
            eq = json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
            n_pairs += 1
            n_equal += eq
            print("%-6s A_%-14s == B_%-14s %s" % (p, x, x, "EQUAL" if eq else "DIFFERENT"))
            if not eq:
                print("        A:", json.dumps(a, sort_keys=True)[:400])
                print("        B:", json.dumps(b, sort_keys=True)[:400])
        if "identity_reconciler" in rec:
            print("%-6s identity_reconciler: %s" % (p, json.dumps(rec["identity_reconciler"], sort_keys=True)[:600]))
            print("%-6s A_identity:          %s" % (p, json.dumps(rec.get("A_identity"), sort_keys=True)[:600]))
    print()
    print("field pairs compared: %d; equal: %d; different: %d" % (n_pairs, n_equal, n_pairs - n_equal))


if __name__ == "__main__":
    main()
