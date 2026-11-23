"""The engine-constants table of a run's manifest vs LIVE's table (read-only; no test file opened).
    py -3.9 -B constants_diff.py <run folder>"""
import json, sys
sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\<user>\Desktop\data set for reserch paper\engine")
from treeroute import engine_constants as K
run = sys.argv[1]
m = json.load(open(run + "/manifest.json", encoding="utf-8"))
old = m["engine_constants"]; new = K.table()
def keyed(t):
    out = {}
    for e in t:
        k = e.get("id") or e.get("name") or json.dumps(e, sort_keys=True)
        out[k] = e
    return out
print("example entry", json.dumps(old[0], sort_keys=True))
o, n = keyed(old), keyed(new)
print("run %d entries (hash %s), LIVE %d entries (hash %s)" % (len(o), m["engine_constants_hash"][:8], len(n), K.constants_hash()[:8]))
for k in sorted(set(n) - set(o)): print(" added in LIVE:", json.dumps(n[k], sort_keys=True))
for k in sorted(set(o) - set(n)): print(" only in run:", json.dumps(o[k], sort_keys=True))
for k in sorted(set(o) & set(n)):
    if o[k] != n[k]: print(" changed:", k, json.dumps(o[k], sort_keys=True), "->", json.dumps(n[k], sort_keys=True))
