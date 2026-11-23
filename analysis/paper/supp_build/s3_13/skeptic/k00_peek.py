# Skeptic peek: structure of the sources (keys only, a few values). Read-only.
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
V = SHAP + r"\verify_v1"

def keys(d, depth=0, maxdepth=2, prefix=""):
    if not isinstance(d, dict) or depth > maxdepth:
        return
    for k, v in d.items():
        t = type(v).__name__
        extra = ""
        if isinstance(v, (int, float, str, bool)) or v is None:
            extra = " = " + repr(v)[:80]
        elif isinstance(v, list):
            extra = " len=%d first=%s" % (len(v), repr(v[:3])[:100])
        print("  " * depth + prefix + str(k) + " (" + t + ")" + extra)
        keys(v, depth + 1, maxdepth)

pl = json.load(open(SHAP + r"\out\fire\lead_0\compare\per_lead.json", encoding="utf-8"))
print("== fire per_lead.json")
keys(pl, maxdepth=2)
aw = json.load(open(SHAP + r"\out\pm25\lead_0\compare\AW4_main_row.json", encoding="utf-8"))
print("== pm25 AW4_main_row.json")
keys(aw, maxdepth=2)
aw = json.load(open(SHAP + r"\out\fire\lead_0\compare\AW4_main_row.json", encoding="utf-8"))
print("== fire AW4_main_row.json")
keys(aw, maxdepth=2)
r = json.load(open(V + r"\A\results.json", encoding="utf-8"))
print("== results.json top")
keys(r, maxdepth=0)
print("== results.json problems.fire")
keys(r["problems"]["fire"], maxdepth=1)
print("== results.json problems.fire.levels.variable (keys)")
print(list(r["problems"]["fire"]["levels"]["variable"].keys()))
pk = r["problems"]["fire"]["levels"]["variable"]["pairs"]
print(list(pk.keys())[:20])
print(json.dumps(pk["rival_ridge|treeroute"], indent=0)[:1500])
print("== results.json problems.fire.main_row")
print(json.dumps(r["problems"]["fire"]["main_row"], indent=0)[:2500])
print("== results.json b1 keys")
keys(r["b1"], maxdepth=1)
print("== b1.fire keys")
keys(r["b1"]["fire"], maxdepth=1)
print(list(r["b1"]["fire"]["variable"].keys()))
print(json.dumps(r["b1"]["fire"]["variable"]["pair_main_b1"], indent=0)[:2500])
