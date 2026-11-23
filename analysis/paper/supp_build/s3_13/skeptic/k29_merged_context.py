# Skeptic (version 4 check, item 2, V4-4): PROTOCOL L393-397 and L650-654: a router-context column that is an exact copy
# of a tree column is the SAME player as that tree column ("NDVI's main run merged five"), and at the variable level a
# duplicate context column is its tree column's variable. If so, the family "context and calendar" is not the whole
# router context on that problem. Per problem and model, from SHAP\out\<p>\lead_0\<model>\meta.json: the top-level
# keys, `duplicates_merged`, and the variable and family of each merged column (per_lead.json `families`).
# Read-only; prints only (names and short values; path-like strings masked).
import json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
pathlike = re.compile(r"(?i)[a-z]:[\\/]|[\\/]users[\\/]|\\\\")


def short(v, n=700):
    s = json.dumps(v, ensure_ascii=False)
    s = "<path>" if pathlike.search(s) and len(s) < 200 else s
    return s if len(s) <= n else s[:n] + " ...(%d chars)" % len(s)


for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    base = SHAP + r"\out\%s\lead_0" % p
    PL = json.load(open(base + r"\compare\per_lead.json", encoding="utf-8"))
    fam = PL["families"]
    models = PL["models"] if isinstance(PL["models"], list) else list(PL["models"])
    print("=" * 20, p, "| models:", models)
    for m in models:
        f = os.path.join(base, m, "meta.json")
        if not os.path.exists(f):
            print("  %-20s meta.json not found" % m)
            continue
        M = json.load(open(f, encoding="utf-8"))
        dm = M.get("duplicates_merged")
        vm = M.get("variable_map") or M.get("variables_map") or M.get("variable") or None
        if m == models[0] or m == "treeroute":
            print("  %-20s meta.json keys: %s" % (m, list(M)))
        print("  %-20s duplicates_merged: %s" % (m, short(dm)))
        if isinstance(vm, dict):
            ctxp = {k: v for k, v in vm.items() if "ctx" in k or "calendar" in str(v) or k.startswith("c__")}
            print("  %-20s variable map: %d entries; context entries: %s" % (m, len(vm), short(ctxp, 900)))
        if isinstance(dm, (list, dict)) and dm:
            items = dm.items() if isinstance(dm, dict) else enumerate(dm)
            for k, v in items:
                tgt = v if isinstance(v, str) else (v.get("tree") or v.get("into") or v) if isinstance(v, dict) else v
                vv = vm.get(tgt) if isinstance(vm, dict) and isinstance(tgt, str) else None
                print("      merged %s -> %s | variable %r | family %r" % (k, short(v, 200), vv,
                                                                          fam.get(vv) if isinstance(vv, str) else None))
