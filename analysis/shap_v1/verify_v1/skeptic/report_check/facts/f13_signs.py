import json, collections
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
B = json.load(open(V + r"\B\results.json", encoding="utf-8"))
n = 0
zero_fin = []
for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    for lev in ["feature", "variable"]:
        pairs = A["problems"][p]["levels"][lev]["pairs"]
        for pk, pv in pairs.items():
            n += 1
            sa = pv.get("sign_agreement")
            sb = B["problems"][p]["levels"][lev]["pairs"][pk].get("sign_agreement")
            nd = pv.get("sign_n_determined")
            if sa is None:
                print("None SA", p, lev, pk)
                continue
            if sa.get("n_finite") in (0, None) or sa.get("value") is None:
                zero_fin.append((p, lev, pk, sa, nd.get("value") if nd else None))
            if p == "fire" and lev == "variable" and "ridge" in pk and "treeroute" in pk:
                print("FIRE ridge|treeroute var A", sa, "B", sb, "n_det", nd)
print("pair-levels", n)
print("with n_finite 0 or value None:", len(zero_fin))
for z in zero_fin:
    print("  ", z)
# median rival per-rival shares ndvi
for p in ["defo", "pm25", "ndvi", "coral"]:
    print(p, "own_history_share_per_rival A", A["problems"][p]["main_row"].get("own_history_share_per_rival"))
# item 8 ranking: 12 largest distinct?
for p in ["coral", "fire"]:
    nf = A["problems"][p].get("nonzero_forecast", {})
    for m, mv in nf.get("models", {}).items():
        pl = mv.get("players", {})
        vals = sorted(((v["I"]["value"] if isinstance(v.get("I"), dict) else v.get("I")), k) for k, v in pl.items())[::-1]
        top12 = [x[0] for x in vals[:12]]
        print(p, m, "n players", len(pl), "12 largest distinct", len(set(top12)) == 12, "rows", mv.get("n_rows") or mv.get("rows"))
# BARDL variable-level zero count
bl = A["problems"]["ndvi"]["levels"]["variable"]["models"]["rival_bardl_h1"]["players"]
nz = [k for k, v in bl.items() if (v["I"]["value"] if isinstance(v.get("I"), dict) else v.get("I")) == 0]
print("ndvi BARDL variable players", len(bl), "exactly zero", len(nz), "nonzero", sorted(set(bl) - set(nz)))
print("ndvi variable J size", len(A["problems"]["ndvi"]["levels"]["variable"]["active_set"]["J"]) if "active_set" in A["problems"]["ndvi"]["levels"]["variable"] else None)
