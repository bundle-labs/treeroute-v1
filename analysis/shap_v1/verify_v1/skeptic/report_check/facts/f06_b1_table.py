import json, math
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
B = json.load(open(V + r"\B\results.json", encoding="utf-8"))

def r3(x):
    if x is None:
        return "None"
    return format(x, ".3f")

def iv(o):
    if o is None:
        return "None"
    s = r3(o["value"])
    if o.get("ci_low") is not None:
        s += f" [{r3(o['ci_low'])}, {r3(o['ci_high'])}]"
    s += f" n={o.get('n_finite')}"
    return s

def full(o):
    if o is None:
        return "None"
    return f"{o['value']!r} [{o.get('ci_low')!r}, {o.get('ci_high')!r}] n={o.get('n_finite')}"

def same(oa, ob):
    if oa is None or ob is None:
        return oa is None and ob is None
    for k in ("value", "ci_low", "ci_high"):
        a, b = oa.get(k), ob.get(k)
        if a is None or b is None:
            if not (a is None and b is None):
                return False
            continue
        if abs(a - b) > 1e-9 * max(1, abs(a), abs(b)):
            return False
    return oa.get("n_finite") == ob.get("n_finite")

stats = ["n_J", "spearman_J", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10", "jaccard_top20",
         "rbo_p090", "rbo_p095", "tv_shares", "tv_family_shares", "sign_agreement", "sign_n_determined", "sign_n_agree"]
for p in ["fire", "pm25", "ndvi"]:
    for lev in ["feature", "variable"]:
        pa = A["b1"][p][lev]["pair_main_b1"]
        pb = B["b1"][p][lev]["pair_main_b1"]
        print("=" * 10, p, lev)
        for st in stats:
            oa, ob = pa.get(st), pb.get(st)
            flag = "AB=" + str(same(oa, ob))
            print(f"  {st:22s} A: {iv(oa):40s} B: {iv(ob):40s} {flag}")
            print(f"  {'':22s} A full: {full(oa)}")
    # variable-level top3, families, own-history
    va = A["b1"][p]["variable"]; vb = B["b1"][p]["variable"]
    print("  top3 A", va["top3"])
    print("  top3 B", vb["top3"])
    for fam in ["own_history", "global_indices", "local_drivers", "context_and_calendar", "seasonal_normal"]:
        print(f"  fam {fam:22s} A {iv(va['families'][fam]):40s} B {iv(vb['families'][fam]):40s} AB={same(va['families'][fam], vb['families'][fam])}")
        print(f"      full A {full(va['families'][fam])}")
    print("  own_history_share A", iv(va["own_history_share"]), "B", iv(vb["own_history_share"]), "full A", full(va["own_history_share"]))
    # nonzero counts
    for lev in ["feature", "variable"]:
        ia = A["b1"][p][lev]["importance"]; ib = B["b1"][p][lev]["importance"]
        print("  nonzero", lev, "A", ia.get("n_nonzero"), "before merge", ia.get("n_nonzero_before_merge"), "extra", ia.get("extra"))
        print("  nonzero", lev, "B", ib.get("n_nonzero"), "before merge", ib.get("n_nonzero_before_merge"), "extra", ib.get("extra"))
