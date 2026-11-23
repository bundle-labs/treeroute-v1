# Skeptic (version 3 check, item 2/5): Table 9's new sentence names the five families and glosses own history as "the
# lags and trailing means of the location's own labels". Per problem: the family names in per_lead.json's map, the
# variables of the own-history family, and the feature-level players of those variables; also the consensus
# (the mean of the main-set rivals' importance shares) against AW4's consensus top 3. Read-only; prints only.
import json, sys
from collections import Counter
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    C = SHAP + r"\out\%s\lead_0\compare" % p
    PL = json.load(open(C + r"\per_lead.json", encoding="utf-8"))
    fam = PL["families"]
    IM = pd.read_parquet(C + r"\importance.parquet")
    fams = Counter(fam.values())
    own = sorted(v for v, f in fam.items() if f == "own history")
    fe = sorted(set(IM[(IM.level == "feature") & IM.player.str.contains("hist")].player))
    hvars = sorted(v for v in fam if v.startswith("h_") or "hist" in v)
    print("%-5s families %s" % (p, dict(fams)))
    print("      own-history variables: %s | variables named h_* or *hist*: %s (families %s)" % (
        own, hvars, sorted(set(fam[v] for v in hvars))))
    print("      feature players containing 'hist': %s" % fe)
    try:
        AW = json.load(open(C + r"\AW4_main_row.json", encoding="utf-8"))
        riv = [m for m in PL["main_set"] if m != "treeroute"]
        q = IM[(IM.level == "variable") & IM.model.isin(riv) & IM.active]
        cons = q.groupby("player").share.mean().reset_index().sort_values(["share", "player"], ascending=[False, True])
        print("      consensus (mean of %d rivals' shares) top 3: %s | AW4 consensus_top3: %s" % (
            len(riv), list(cons.player[:3]), AW.get("consensus_top3")))
    except Exception as ex:
        print("      consensus check skipped:", type(ex).__name__, ex)
