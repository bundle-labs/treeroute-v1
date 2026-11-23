import json, collections
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
m = json.load(open(V + r"\reconcile\mismatches.json", encoding="utf-8"))
print("columns", m["columns"])
print("status_codes", json.dumps(m["status_codes"], indent=1))
print("key_counts", m["key_counts"], "number_counts", m["number_counts"], "n_mismatch_keys", m["n_mismatch_keys"])
print("len keys", len(m["keys"]))
print("no-number keys", len(m["keys_without_a_number_anywhere"]["keys"]))
grp_order = [g["group"] for g in m["groups"]]
print("group order", grp_order)
for g in m["groups"]:
    print("GROUP", g["group"], g["kind"], g["n_keys"], g["affects_reported_numbers"])
cnt = collections.OrderedDict((g, collections.Counter()) for g in grp_order)
nkeys = collections.Counter()
sec = collections.Counter()
sec_pairs = collections.Counter()
derived = collections.defaultdict(collections.Counter)
for row in m["keys"]:
    key, grp, secg, status, a, b, off, offd = row
    nkeys[grp] += 1
    parts = dict(p.split("=", 1) for p in status.split())
    for k in ("AB", "AO", "BO"):
        cnt[grp][k + "=" + parts.get(k, "<none>")] += 1
    for k in ("AOd", "BOd"):
        if k in parts:
            derived[grp][k + "=" + parts[k]] += 1
    for k in parts:
        if k not in ("AB", "AO", "BO", "AOd", "BOd"):
            cnt[grp]["OTHERKEY " + k] += 1
    for s in secg:
        sec[(grp, s)] += 1
print()
tot = 0
for g in grp_order:
    tot += nkeys[g]
    print(g, nkeys[g])
    for k, v in sorted(cnt[g].items()):
        print("    ", k, v)
    if derived[g]:
        print("   derived:", dict(derived[g]))
print("total", tot)
print("secondary groups:", dict(sec))
# also check: which groups have keys whose A value and B value both None etc
