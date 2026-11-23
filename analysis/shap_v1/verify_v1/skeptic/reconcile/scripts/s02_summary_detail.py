"""Skeptic: print the parts of the reconciler's summary.json that hold checks (not the matched numbers)."""
import json
import os

RC = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile"
with open(os.path.join(RC, "work", "summary.json"), encoding="utf-8") as f:
    S = json.load(f)

print("== derived_disagreements")
for d in S["derived_disagreements"]:
    print(json.dumps(d)[:600])

print("== official_internal_checks (False only)")
for p, lst in S["official_internal_checks"].items():
    bad = [c for c, ok in lst if not ok]
    print(p, "n=%d" % len(lst), "false:", bad)

print("== second_checks")
for p, d in S["second_checks"].items():
    print(p, {k: d[k] for k in ("n", "official_table_eq_unrounded", "A_eq", "B_eq")}, "not_ok:", len(d["not_ok"]))
    for r in d["not_ok"]:
        print("   ", json.dumps(r)[:300])

print("== per_draw")
for p, d in S["per_draw"].items():
    for kind, v in d.items():
        if kind.startswith("bootstrap"):
            print(p, kind, {k: v[k] for k in ("n", "n_ok", "max_abs_diff")}, "bad:", len(v["bad"]))
            for k, x in list(v["bad"].items())[:10]:
                print("    ", k, x)
        else:
            print(p, kind, {k: v[k] for k in ("keys_A", "keys_B", "n_ok")}, "only_A:", len(v["only_A"]),
                  "only_B:", len(v["only_B"]), "bad:", len(v["bad"]))
            for k in v["only_A"][:15]:
                print("    only_A", k)
            for k in v["only_B"][:15]:
                print("    only_B", k)
            for k, x in list(v["bad"].items())[:15]:
                print("    bad", k, x)

print("== b1")
print(json.dumps(S["b1"], indent=1)[:20000])
print("== independence")
print(json.dumps(S["independence"], indent=1))
print("== b1_feature_family_tvd")
print(json.dumps(S["b1_feature_family_tvd"], indent=1))
print("== no_number_key_patterns")
print(json.dumps(S["no_number_key_patterns"], indent=1))
print("== group_patterns")
for g, pats in S["group_patterns"].items():
    print("--", g)
    for pt, n in pats:
        print("    %6d %s" % (n, pt))
