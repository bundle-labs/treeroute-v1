import json, yaml, sys
ban = yaml.safe_load(open(r"C:\Users\<user>\Desktop\data set for reserch paper\engine\datasets\pm25\ban.yaml", encoding="utf-8"))
v = ban["verdicts"]
from collections import Counter
print("verdict counts", Counter(x["verdict"] for x in v.values()))
for L in (0,6,12):
    m = json.load(open(r"D:\treeroute\rival_export\pm25\20261007_74e67609\lead_%d\export_manifest.json" % L))
    cols = m["columns"]["tree"] + m["columns"]["context"]
    bad = [(c, v[c]["verdict"]) for c in cols if c in v and v[c]["verdict"] not in ("keep", "watch")]
    notin = [c for c in cols if c not in v]
    print("lead", L, "n cols", len(cols), "non-keep/watch:", bad, "not in ban.yaml:", notin)
kept = sorted(c for c, x in v.items() if x["verdict"] in ("keep", "watch"))
m0 = json.load(open(r"D:\treeroute\rival_export\pm25\20261007_74e67609\lead_0\export_manifest.json"))
exp = set(m0["columns"]["tree"] + m0["columns"]["context"])
print("keep/watch in ban.yaml but NOT exported:", [c for c in kept if c not in exp])
print("ctx verdicts", v["ctx:month"]["verdict"], v["ctx:lat"]["verdict"])
