"""Skeptic (numbers lens): check per_lead.json's non-structural keys against my own readings (regions, salt, draws,
global columns, families, J rule) and regenerate the draw matrices from the protocol's salt."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s_lib as L

OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\numbers\work"
GL = json.load(open(os.path.join(OUT, "s01_global_coral_fire_pm25_ndvi.json"), encoding="utf-8"))
GL.update(json.load(open(os.path.join(OUT, "s01_global_defo.json"), encoding="utf-8")))
res = {}
for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    pl = L.per_lead(p)
    d, sha = L.load_draws(p)
    rows, groups, pre, phi = L.load(p, "treeroute", "variable")
    regs = sorted(set(groups.tolist()))
    first_app = list(dict.fromkeys(groups.tolist()))
    regen = L.regen_draws(p, len(regs))
    r = {
        "salt": pl.get("salt"),
        "j_rule": pl.get("j_rule"),
        "reference_link": pl.get("reference_link"),
        "draws_key": pl.get("draws") if not isinstance(pl.get("draws"), list) else "list of %d" % len(pl.get("draws")),
        "sorted_groups_equal_first_appearance": regs == first_app,
        "n_regions_per_lead": pl.get("regions"),
        "n_regions_rows": len(regs),
        "regen_equals_saved": bool(np.array_equal(regen, d)),
        "global_columns_official_n": len(pl.get("global_columns") or []),
        "global_columns_equal_mine": sorted(pl.get("global_columns") or []) == sorted(GL[p]["global_columns"]),
        "global_columns_only_official": sorted(set(pl.get("global_columns") or []) - set(GL[p]["global_columns"])),
        "global_columns_only_mine": sorted(set(GL[p]["global_columns"]) - set(pl.get("global_columns") or [])),
    }
    fam = pl.get("families") or {}
    myfam = {}
    allv = set()
    for m in pl["models"]:
        allv |= set(L.meta(p, m)["variables"])
    for v in sorted(allv):
        myfam[v] = L.family_of(v, set(GL[p]["global_vars"]))
    name = {"own history": "own_history", "global indices": "global_indices", "local drivers": "local_drivers",
            "context and calendar": "context_and_calendar", "seasonal normal": "seasonal_normal"}
    offam = {v: name.get(f, f) for v, f in fam.items()} if isinstance(fam, dict) else {}
    r["families_type"] = type(fam).__name__
    r["families_n"] = len(offam)
    r["families_differ"] = {v: (offam.get(v), myfam.get(v)) for v in sorted(set(offam) | set(myfam)) if offam.get(v) != myfam.get(v)}
    r["variables"] = sorted(allv)
    res[p] = r
    print(p, json.dumps({k: v for k, v in r.items() if k != "variables"}))
with open(os.path.join(OUT, "s03_perlead_checks.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1)
