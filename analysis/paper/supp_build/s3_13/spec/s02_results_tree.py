"""Spec writer's helper (read-only): the key tree of V\\A\\results.json and the values the spec needs to name.

Usage: py -3.9 -I -B s02_results_tree.py
Prints the key tree (maps keyed by player, variable or pair names collapsed to one example), the sign-agreement
objects of every pair-level, fire's main row, the B1 status/run/identity objects and A's choices C08-C25.
Opens only V\\A\\results.json. Writes nothing.
"""
import json

RES = r"D:\treeroute\analysis\shap_v1\verify_v1\A\results.json"
COLLAPSE = {"players", "pairs", "models", "stability", "variable_family", "consensus_shares", "main_shares",
            "spearman_top20_union_per_rival", "own_history_share_per_rival"}


def tree(d, path, depth, out):
    if isinstance(d, dict):
        keys = list(d.keys())
        last = path.split(".")[-1] if path else ""
        if last in COLLAPSE and len(keys) > 1:
            out.append("%s{%d keys, e.g. %r}" % ("  " * depth, len(keys), keys[:3]))
            tree(d[keys[0]], path + "." + keys[0], depth + 1, out)
            return
        for k in keys:
            v = d[k]
            if isinstance(v, (dict, list)):
                if isinstance(v, list):
                    ex = v[:3]
                    out.append("%s%s: list[%d] %s" % ("  " * depth, k, len(v), json.dumps(ex)[:150]))
                else:
                    out.append("%s%s:" % ("  " * depth, k))
                    tree(v, path + "." + k if path else k, depth + 1, out)
            else:
                out.append("%s%s: %s" % ("  " * depth, k, json.dumps(v)[:120]))


def main():
    with open(RES, encoding="utf-8") as f:
        R = json.load(f)
    out = []
    print("TOP:", list(R.keys()))
    print("problems:", list(R["problems"].keys()))
    # one problem's full collapsed tree
    tree(R["problems"]["fire"], "problems.fire", 0, out)
    print("\n".join(out))
    out = []
    print("=" * 100)
    tree(R["b1"]["fire"], "b1.fire", 0, out)
    print("\n".join(out))
    print("=" * 100)
    print("b1.defo:", json.dumps(R["b1"]["defo"], indent=1)[:6000])
    print("b1.coral:", json.dumps(R["b1"]["coral"], indent=1)[:3000])
    print("b1.fire.status:", json.dumps(R["b1"]["fire"]["status"], indent=1))
    print("b1.fire.run:", json.dumps(R["b1"]["fire"]["run"], indent=1))
    for p in ("pm25", "ndvi"):
        print("b1.%s.run:" % p, json.dumps(R["b1"][p]["run"], indent=1))
    print("=" * 100)
    for p, P in R["problems"].items():
        for L in ("feature", "variable"):
            for pk, pr in P["levels"][L]["pairs"].items():
                sa = pr.get("sign_agreement")
                nd = pr.get("sign_n_determined")
                na = pr.get("sign_n_agree")
                print("%s %s %s | sa=%s | nd=%s | na=%s" % (p, L, pk, json.dumps(sa), json.dumps(nd), json.dumps(na)))
    print("=" * 100)
    print("fire main_row:", json.dumps(R["problems"]["fire"]["main_row"], indent=1)[:5000])
    print("coral main_row own:", json.dumps(R["problems"]["coral"]["main_row"]["own_history_share_treeroute"]),
          json.dumps(R["problems"]["coral"]["main_row"]["own_history_share_median_rival"]))
    print("=" * 100)
    for k, v in R["choices"].items():
        print(k, ":", v)
    print("software:", R.get("software"), "written_at:", R.get("written_at"), "schema:", R.get("schema_version"))


if __name__ == "__main__":
    main()
