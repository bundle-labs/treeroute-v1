"""Skeptic (numbers lens): apply section 8's variable rule to every player name and compare with meta.json variable_map.

Rule: strip lag (_lag<k>), aggregate (_mean, _min, _max) and window (_<k>, _<k>m, _<k>mo, _roll<k>, _wytd, _all)
suffixes repeatedly and drop a catalog code V<nn>_; own-history columns keep their stem (hist_last, hist_mean);
context columns are calendar (month and harmonics) or ctx:<name>; a duplicate context column is its tree column's variable.
"""
import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s_lib as L

OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\numbers\work"
SUF = [r"_lag\d+$", r"_(mean|min|max)$", r"_\d+$", r"_\d+m$", r"_\d+mo$", r"_roll\d+$", r"_wytd$", r"_all$"]
CAL = {"month", "sin1", "cos1", "sin2", "cos2", "doy_sin", "doy_cos"}


def rule(player):
    if player == "normal":
        return "normal"
    if player.startswith("c__"):
        rest = player[3:]
        if rest.startswith("ctx:top5:"):
            return rule("x__" + rest[len("ctx:top5:"):])
        if rest.startswith("ctx:"):
            nm = rest[4:]
        elif rest.startswith("ctx_"):
            nm = rest[4:]
        else:
            return "?" + rest
        return "calendar" if nm in CAL else "ctx:" + nm
    nm = player[3:]
    for stem in ("hist_last", "hist_mean"):
        if nm.startswith(stem):
            return stem
    nm = re.sub(r"^V\d\d_", "", nm)
    changed = True
    while changed:
        changed = False
        for s in SUF:
            new = re.sub(s, "", nm)
            if new != nm and new != "":
                nm = new
                changed = True
    return nm


res = {}
for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    pl = L.per_lead(p)
    mods = list(pl["models"])
    if os.path.exists(os.path.join(L.piece(p, "treeroute_B1"), "meta.json")):
        mods.append("treeroute_B1")
    diffs = {}
    for m in mods:
        vm = L.meta(p, m)["variable_map"]
        for k, v in vm.items():
            r = rule(k)
            if r != v:
                diffs.setdefault(k, set()).add((v, r))
    res[p] = {k: sorted(list(x)) for k, x in sorted(diffs.items())}
    print(p, "players whose map differs from my reading of the rule:", len(diffs))
    for k, x in sorted(diffs.items()):
        print("   ", k, "-> map", [a for a, b in x], "| rule", [b for a, b in x])
with open(os.path.join(OUT, "s02_varmap.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1)
