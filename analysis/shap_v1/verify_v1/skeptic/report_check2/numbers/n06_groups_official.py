"""n06: what the official files hold in the groups where AO or BO is 'diff' (A1 item 8's 'three groups'), and
summary.json's B1 records A against B (A1 item 17), second checks and verdicts (A1 items 5, 6). Read-only."""
import json
import math
from collections import Counter, defaultdict

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
M = json.load(open(V + r"\reconcile\mismatches.json", encoding="utf-8"))
S = json.load(open(V + r"\reconcile\work\summary.json", encoding="utf-8"))
print("columns:", M["columns"])
cols = M["columns"]
ix = {c: k for k, c in enumerate(cols)}

by_group = defaultdict(list)
for row in M["keys"]:
    by_group[row[1]].append(row)

# groups with a 'diff' against the official files (AO or BO)
print("\n== groups with AO=diff or BO=diff ==")
for g, rows in by_group.items():
    st = Counter()
    for r in rows:
        s = r[3]
        parts = dict(p.split("=") for p in s.split())
        st[(parts.get("AO"), parts.get("BO"))] += 1
    has_diff = any("diff" in (k[0] or "", ) or "diff" in (k[1] or "",) for k in st)
    if any(k[0] == "diff" or k[1] == "diff" for k in st):
        print(g, dict(st))
        # show 3 examples with diff
        shown = 0
        for r in rows:
            parts = dict(p.split("=") for p in r[3].split())
            if parts.get("AO") == "diff" or parts.get("BO") == "diff":
                print("    ", json.dumps(r)[:300])
                shown += 1
                if shown >= 3:
                    break
        # kinds of official values in diff rows
        ov = Counter()
        for r in rows:
            parts = dict(p.split("=") for p in r[3].split())
            if parts.get("AO") == "diff" or parts.get("BO") == "diff":
                o = r[ix["official"]] if "official" in ix else r[-1]
                if o is None:
                    ov["None"] += 1
                elif isinstance(o, float) and math.isnan(o):
                    ov["nan"] += 1
                elif isinstance(o, str):
                    ov["str:" + o[:10]] += 1
                elif isinstance(o, (int, float)):
                    ov["num:%r" % o if o == 0 else "num"] += 1
                else:
                    ov[type(o).__name__] += 1
        print("    official values in diff rows:", dict(ov))

# ---- summary.json b1 records: A vs B (A1 item 17)
print("\n== summary.json b1: A_* vs B_* ==")
for p, v in S["b1"].items():
    pairs = [(k, "B" + k[1:]) for k in v if k.startswith("A_")]
    res = []
    for ka, kb in pairs:
        res.append("%s %s" % (ka[2:], "equal" if v[ka] == v.get(kb) else "DIFF"))
    print(p, "; ".join(res))
    if "identity_reconciler" in v:
        print("   identity_reconciler:", json.dumps(v["identity_reconciler"])[:400])
        print("   A_identity:", json.dumps(v["A_identity"])[:400])

print("\n== second checks ==")
tot = Counter()
for p, v in S["second_checks"].items():
    for k in ("n", "official_table_eq_unrounded", "A_eq", "B_eq"):
        tot[k] += v[k]
    print(p, v["n"], v["official_table_eq_unrounded"], v["A_eq"], v["B_eq"], "not_ok", len(v["not_ok"]))
print("totals", dict(tot))
print("verdicts", S["verdicts"], "b1 total", S["verdicts"]["b1 match"] + S["verdicts"]["b1 mismatch"])
print("key_counts", json.dumps(S["key_counts"]))
print("closeness", json.dumps(S["closeness"])[:800])
print("pairs_with_no_sign_determined_in_both", len(S["pairs_with_no_sign_determined_in_both"]))
print("b1_feature_family_tvd", json.dumps(S["b1_feature_family_tvd"])[:600])
print("independence", json.dumps(S["independence"])[:1500])
