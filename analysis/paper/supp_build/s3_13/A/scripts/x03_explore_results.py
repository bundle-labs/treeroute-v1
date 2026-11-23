# Exploration only (prints to console): the key tree of V\A\results.json and the objects the spec names.
import sys, json

sys.stdout.reconfigure(encoding="utf-8")
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
with open(V + r"\A\results.json", "r", encoding="utf-8") as f:
    R = json.load(f)


def tree(d, depth, maxdepth, prefix=""):
    if depth > maxdepth:
        return
    if isinstance(d, dict):
        keys = list(d.keys())
        shown = keys if len(keys) <= 25 else keys[:25]
        for k in shown:
            v = d[k]
            t = type(v).__name__
            extra = ""
            if isinstance(v, (int, float, str, bool)) or v is None:
                extra = " = " + repr(v)[:80]
            elif isinstance(v, list):
                extra = " len " + str(len(v)) + (" first " + repr(v[0])[:80] if v else "")
            print("  " * depth + prefix + str(k) + " (" + t + ")" + extra)
            if isinstance(v, dict):
                tree(v, depth + 1, maxdepth)
        if len(keys) > 25:
            print("  " * depth + "... " + str(len(keys) - 25) + " more keys")


print("top:", list(R.keys()))
tree(R, 0, 2)
print("=" * 40)
pr = R["problems"]
print("problems keys:", list(pr.keys()))
for p in pr:
    print("--", p, list(pr[p].keys()))
    print("   levels:", list(pr[p]["levels"].keys()))
    for L in pr[p]["levels"]:
        lv = pr[p]["levels"][L]
        print("   ", L, "keys:", list(lv.keys()))
        pairs = lv["pairs"]
        print("     pair keys:", list(pairs.keys()))
        k0 = list(pairs.keys())[0]
        print("     first pair keys:", list(pairs[k0].keys()))
        for k in pairs:
            print("      ", k, "sign_agreement:", pairs[k]["sign_agreement"], "n_det:", pairs[k].get("sign_n_determined"))
print("fire main_row:", json.dumps(pr["fire"].get("main_row"), indent=1)[:3000])
print("=" * 40)
b1 = R["b1"]
print("b1 keys:", list(b1.keys()))
for p in b1:
    print("--", p, list(b1[p].keys()))
    print("   status:", b1[p].get("status"))
    if "run" in b1[p]:
        print("   run:", b1[p]["run"])
    if "identity" in b1[p]:
        print("   identity:", b1[p]["identity"])
    for L in ["variable", "feature"]:
        if L in b1[p]:
            x = b1[p][L]
            print("  ", L, "keys:", list(x.keys()))
            print("     pair_main_b1 keys:", list(x["pair_main_b1"].keys()))
            for k, v in x["pair_main_b1"].items():
                print("       ", k, v)
            print("     importance keys:", list(x["importance"].keys()))
            print("     n_nonzero:", x["importance"].get("n_nonzero"))
            print("     top10:", x.get("top10"))
            if L == "variable":
                print("     families:", x.get("families"))
                print("     top3:", x.get("top3"))
                print("     own_history_share:", x.get("own_history_share"))
