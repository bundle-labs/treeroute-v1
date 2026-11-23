"""Report check 3: the A/B B1 records in summary.json (A1 item 19) and NDVI's J sizes for BARDL (A4, A5 point 3).
Read-only. Run: py -3.9 -I -B c05_summary_b1_and_J.py
"""
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    S = load(V + r"\reconcile\work\summary.json")
    b1 = S["b1"]
    n_pairs = n_eq = 0
    for p, rec in b1.items():
        a = sorted(k[2:] for k in rec if k.startswith("A_"))
        b = sorted(k[2:] for k in rec if k.startswith("B_"))
        others = sorted(k for k in rec if not (k.startswith("A_") or k.startswith("B_")))
        print("%-6s A fields %s | B fields %s | B-only %s | A-only %s | other fields %s" % (
            p, a, b, sorted(set(b) - set(a)), sorted(set(a) - set(b)), others))
        for x in sorted(set(a) | set(b)):
            va, vb = rec.get("A_" + x), rec.get("B_" + x)
            eq = json.dumps(va, sort_keys=True) == json.dumps(vb, sort_keys=True)
            n_pairs += 1
            n_eq += eq
            if not eq:
                print("    DIFFERENT", x)
            if va is None or vb is None:
                print("    one side missing or null:", x, va is None, vb is None)
        if "identity_reconciler" in rec:
            ir = rec["identity_reconciler"]
            ai = rec.get("A_identity")
            bi = rec.get("B_identity")
            print("    identity_reconciler: max phi %s (over %s values), max phiv %s (over %s values), same_rows %s"
                  % (ir.get("max_abs_diff_phi"), ir.get("n_values_compared_phi"), ir.get("max_abs_diff_phiv"),
                     ir.get("n_values_compared_phiv"), ir.get("same_rows")))
            for tag, ii in (("A", ai), ("B", bi)):
                print("    %s_identity: max phi %s, max phiv %s, rows %s/%s, players %s/%s, variables %s/%s, as_expected %s"
                      % (tag, ii.get("max_abs_diff_phi"), ii.get("max_abs_diff_phiv"), ii.get("n_rows_main"),
                         ii.get("n_rows_b1"), ii.get("n_players_main"), ii.get("n_players_b1"),
                         ii.get("n_variables_main"), ii.get("n_variables_b1"), ii.get("as_expected")))
        # other fields that hold the reconciler's own readings (to see what an assert would also compare)
        for k in others:
            v = rec[k]
            print("    other field %s: %s" % (k, json.dumps(v, sort_keys=True)[:240]))
    print("A/B field pairs: %d; equal: %d" % (n_pairs, n_eq))
    print()
    A = load(V + r"\A\results.json")
    for lev in ("variable", "feature"):
        L = A["problems"]["ndvi"]["levels"][lev]
        act = L["active_set"]
        if isinstance(act, dict):
            print("ndvi %s active_set fields: %s" % (lev, list(act.keys())[:10]))
            for k in ("J", "players", "members", "n"):
                if k in act:
                    v = act[k]
                    print("   %s: %s" % (k, len(v) if isinstance(v, list) else v))
        elif isinstance(act, list):
            print("ndvi %s active_set: list of %d" % (lev, len(act)))
        m = L["models"].get("rival_bardl_h1", {})
        imp = m.get("importance", m)
        nz = imp.get("n_nonzero") if isinstance(imp, dict) else None
        print("   rival_bardl_h1 model fields: %s | n_nonzero: %s" % (list(m.keys())[:12], json.dumps(nz)[:120]))


if __name__ == "__main__":
    main()
