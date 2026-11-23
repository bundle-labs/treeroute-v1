# Skeptic peek 3: A's results.json key names that the checks need (pairs' sign keys, model objects, B1 objects).
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
r = json.load(open(V + r"\A\results.json", encoding="utf-8"))
pv = r["problems"]["ndvi"]["levels"]["variable"]
print("level keys:", list(pv.keys()))
pk = pv["pairs"]["rival_bardl_h1|treeroute"]
print("pair keys:", list(pk.keys()))
for k in ["sign_agreement", "sign_n_determined", "sign_n_agree"]:
    if k in pk:
        print(k, json.dumps(pk[k])[:300])
print("models keys:", list(pv["models"].keys()))
mo = pv["models"]["treeroute"]
print("model obj keys:", list(mo.keys()))
for k, v in mo.items():
    print("  ", k, type(v).__name__, json.dumps(v)[:200])
print("per_problem keys:", list(pv["per_problem"].keys()))
print("families keys:", json.dumps(pv["families"])[:600])
b = r["b1"]["pm25"]
print("b1 pm25 variable keys:", list(b["variable"].keys()))
print("b1 pm25 variable importance keys:", list(b["variable"]["importance"].keys()))
print("n_nonzero:", b["variable"]["importance"]["n_nonzero"])
pl = b["variable"]["importance"].get("players")
if isinstance(pl, dict):
    k0 = list(pl.keys())[0]
    print("players[0]:", k0, json.dumps(pl[k0])[:400])
elif isinstance(pl, list):
    print("players[0]:", json.dumps(pl[0])[:400])
print("families:", json.dumps(b["variable"]["families"])[:900])
print("own_history_share:", json.dumps(b["variable"]["own_history_share"]))
print("pair keys:", list(b["variable"]["pair_main_b1"].keys()))
print("feature pair jaccard_top20:", json.dumps(r["b1"]["ndvi"]["feature"]["pair_main_b1"]["jaccard_top20"])[:300])
print("feature pair tv_family_shares:", json.dumps(r["b1"]["ndvi"]["feature"]["pair_main_b1"].get("tv_family_shares"))[:300])
print("fire feature importance n_nonzero:", r["b1"]["fire"]["feature"]["importance"]["n_nonzero"])
print("defo identity:", json.dumps(r["b1"]["defo"]["identity"])[:1500])
print("coral status:", json.dumps(r["b1"]["coral"]["status"])[:600])
