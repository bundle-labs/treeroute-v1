import json, collections
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
s = json.load(open(V + r"\reconcile\work\summary.json", encoding="utf-8"))
print("closeness", json.dumps(s["closeness"], indent=1))
# official internal checks
n = 0; npass = 0
for p, lst in s["official_internal_checks"].items():
    c = len(lst); ok = sum(1 for x in lst if x[1] is True)
    print("internal", p, c, ok)
    n += c; npass += ok
print("internal total", n, npass)
# second checks
tn = 0; ta = 0; tb = 0; to = 0
for p, d in s["second_checks"].items():
    print("second", p, {k: v for k, v in d.items() if k != "not_ok"}, "not_ok", len(d.get("not_ok", [])))
    tn += d["n"]; ta += d["A_eq"]; tb += d["B_eq"]; to += d["official_table_eq_unrounded"]
print("second totals n", tn, "official_eq", to, "A_eq", ta, "B_eq", tb, "A not eq", tn - ta)
for p, d in s["second_checks"].items():
    for x in d.get("not_ok", []):
        print("   not_ok", p, x)
# per draw
for p, d in s["per_draw"].items():
    if isinstance(d, dict):
        out = {}
        for k, v in d.items():
            if isinstance(v, dict):
                out[k] = {kk: vv for kk, vv in v.items() if kk in ("n", "n_ok", "max_abs_diff", "bad", "n_keys", "n_equal", "max_diff", "n_common", "n_ok_common")}
                if "only_A" in v: out[k]["only_A_len"] = len(v["only_A"])
                if "only_B" in v: out[k]["only_B_len"] = len(v["only_B"])
                for kk, vv in v.items():
                    if kk not in out[k] and not isinstance(vv, list):
                        out[k][kk] = vv
            else:
                out[k] = v
        print("per_draw", p, json.dumps(out)[:2500])
    else:
        print("per_draw", p, json.dumps(d)[:800])
print("verdicts", s["verdicts"])
print("derived_second_check", s["derived_second_check"])
print("derived_disagreements keys", [d["key"] for d in s["derived_disagreements"]])
print("by_item", s["by_item"])
print("structural_zero_rows_official", s["structural_zero_rows_official"])
print("b1_feature_family_tvd", json.dumps(s["b1_feature_family_tvd"], indent=1))
print("pairs_with_no_sign_determined_in_both", s["pairs_with_no_sign_determined_in_both"])
print("seconds", s["seconds"], s["run_started"], s["run_finished"])
print("top keys", list(s.keys()))
