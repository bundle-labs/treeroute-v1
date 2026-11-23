import json, math
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
SHAP = r"D:\treeroute\analysis\shap_v1"
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
B = json.load(open(V + r"\B\results.json", encoding="utf-8"))

def iv(o):
    if o is None:
        return None
    return (o.get("value"), o.get("ci_low"), o.get("ci_high"), o.get("n_finite"))

def offiv(o):
    if o is None:
        return None
    ci = o.get("ci", [None, None, None])
    return (o.get("value"), ci[0], ci[1], ci[2])

def close(a, b):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, float) and math.isnan(a):
        return isinstance(b, float) and math.isnan(b)
    return abs(a - b) <= 1e-9 * max(1, abs(a), abs(b))

for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    print("=" * 20, p)
    ma = A["problems"][p]["main_row"]
    mb = B["problems"][p]["main_row"]
    off = json.load(open(SHAP + "\\out\\" + p + r"\lead_0\compare\AW4_main_row.json", encoding="utf-8"))
    print("A keys", sorted(ma.keys()))
    print("B keys", sorted(mb.keys()))
    pairs = [
        ("kendall_w", "kendall_w"),
        ("spearman_top20_union_median", "treeroute_vs_same_link_rivals_median_spearman_top20_union"),
        ("rbo_p090_vs_consensus", "rbo_vs_consensus_p0.9"),
        ("own_history_share_treeroute", "own_history_share_treeroute"),
        ("own_history_share_median_rival", "own_history_share_median_rival"),
    ]
    for ka, ko in pairs:
        a = iv(ma.get(ka)) if isinstance(ma.get(ka), dict) else ma.get(ka)
        b = iv(mb.get(ka)) if isinstance(mb.get(ka), dict) else mb.get(ka)
        o = offiv(off.get(ko)) if isinstance(off.get(ko), dict) else off.get(ko)
        ok_ab = (a is None and b is None) or (a is not None and b is not None and all(close(x, y) for x, y in zip(a, b)))
        ok_ao = (o is None) or (a is not None and all(close(x, y) for x, y in zip(a, o)))
        ok_bo = (o is None) or (b is not None and all(close(x, y) for x, y in zip(b, o)))
        print(f"  {ka}: A={a} B={b} O={o} AB={ok_ab} AO={ok_ao} BO={ok_bo}")
    for k in ["spearman_top20_union_min", "spearman_top20_union_max"]:
        print("  ", k, "A", iv(ma.get(k)) if isinstance(ma.get(k), dict) else ma.get(k), "B", iv(mb.get(k)) if isinstance(mb.get(k), dict) else mb.get(k))
    print("   official range", off.get("treeroute_vs_same_link_rivals_median_spearman_top20_union", {}).get("range"))
    for k in ["treeroute_top3", "consensus_top3"]:
        print("  ", k, "A", ma.get(k), "B", mb.get(k), "O", off.get(k))
    for k in ["median_rival_name", "rivals", "main_set"]:
        print("  ", k, "A", ma.get(k), "B", mb.get(k))
    print("   consensus_top3_shares A", ma.get("consensus_top3_shares"), "B", mb.get("consensus_top3_shares"))
