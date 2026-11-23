# Skeptic (version 2 check): structure of a rows.parquet and of the gate records E5, E5a, E8, E10. Read-only; prints only.
import json, sys
import pyarrow.parquet as pq
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
f = SHAP + r"\out\pm25\lead_0\treeroute\rows.parquet"
sch = pq.read_schema(f)
names = sch.names
print("pm25 treeroute rows.parquet columns:", len(names))
print("non-phi columns:", [n for n in names if not n.startswith("phi")])
print("phi__ count:", sum(n.startswith("phi__") for n in names), "phiv__ count:", sum(n.startswith("phiv__") for n in names))
print("first phiv:", [n for n in names if n.startswith("phiv__")][:5])
for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    g = json.load(open(SHAP + r"\rebuild\%s\lead_0\gates.json" % p, encoding="utf-8"))
    G = g["gates"]
    print("==", p, "result:", g.get("result"))
    for k in G:
        if k.startswith(("E5", "E8", "E10")):
            v = G[k].get("values")
            print("  ", k, "pass:", G[k].get("pass"), "values:", json.dumps(v, ensure_ascii=False)[:900])
