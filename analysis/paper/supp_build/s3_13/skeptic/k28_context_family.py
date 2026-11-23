# Skeptic (version 4 check, item 2, V4-4): Table 9 now glosses the family "context and calendar" as "the router
# context". PROTOCOL section 8: context columns are `calendar` (month and harmonics) or `ctx:<name>`; "a duplicate
# context column is its tree column's variable". Per problem, from SHAP\out\<p>\lead_0\compare\per_lead.json (the
# variable -> family map) and the feature-level players of importance.parquet: the members of the family, every
# context feature (c__*) with its variable and family, and every member of the family that is not a context column.
# Read-only; prints only (key lists and short values).
import json, sys
from collections import Counter
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    C = SHAP + r"\out\%s\lead_0\compare" % p
    PL = json.load(open(C + r"\per_lead.json", encoding="utf-8"))
    print("=" * 20, p, "| per_lead.json keys:", list(PL))
    fam = PL["families"]
    print("  family sizes:", dict(Counter(fam.values())))
    cc = sorted(v for v, f in fam.items() if f.lower().startswith("context"))
    print("  'context and calendar' members (%d): %s" % (len(cc), cc))
    # any map of feature -> variable in per_lead.json
    for k, v in PL.items():
        if isinstance(v, dict) and k != "families":
            vals = list(v.items())[:3]
            print("  key %r: dict of %d, e.g. %s" % (k, len(v), json.dumps(vals, ensure_ascii=False)[:300]))
    IM = pd.read_parquet(C + r"\importance.parquet")
    print("  importance.parquet columns:", list(IM.columns), "| levels:", sorted(IM.level.unique()))
    feats = sorted(set(IM[IM.level == "feature"].player))
    cfe = [f for f in feats if f.startswith("c__")]
    other = [f for f in feats if not f.startswith(("c__", "x__")) ]
    print("  feature players: %d; c__ players (%d): %s" % (len(feats), len(cfe), cfe))
    print("  feature players neither c__ nor x__: %s" % other)
    # look for a variable map (feature -> variable)
    vm = None
    for k in ("variable_map", "variables", "var_map", "feature_to_variable", "player_map"):
        if k in PL and isinstance(PL[k], dict):
            vm = PL[k]
            print("  variable map found under %r (%d entries)" % (k, len(vm)))
            break
    if vm is not None:
        for f in cfe:
            key = f if f in vm else f[3:] if f[3:] in vm else None
            v = vm.get(key) if key else None
            print("    %s -> variable %r -> family %r" % (f, v, fam.get(v) if isinstance(v, str) else None))
        notctx = [v for v in cc if not any((vm.get(f) == v or vm.get(f[3:]) == v) for f in cfe)]
        print("  family members with no c__ feature mapped to them:", notctx)
