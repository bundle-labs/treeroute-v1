"""Exploration: view groups of work\\mismatches_raw.json and parts of work\\summary.json."""
import json, sys, collections

sys.path.insert(0, r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile")
import rlib as R  # noqa: E402

M = json.load(open(R.WORK + r"\mismatches_raw.json", encoding="utf-8"))
S = json.load(open(R.WORK + r"\summary.json", encoding="utf-8"))
what = sys.argv[1]
if what == "group":
    g = sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    ks = [x for x in M["keys"] if x["group"] == g]
    print(g, len(ks))
    pats = collections.Counter((R.pattern(x["key"]), json.dumps(x["status"], sort_keys=True)) for x in ks)
    for (pt, st), c in pats.most_common(40):
        print("  %5d %s %s" % (c, pt, st))
    for x in ks[:n]:
        print(json.dumps(x)[:700])
elif what == "summary":
    for k in sys.argv[2:]:
        print("=====", k)
        print(json.dumps(S[k], indent=1)[:12000])
