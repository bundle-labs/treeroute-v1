# n08: structure of the named source files (read-only): per_lead.json, AW4_main_row.json, gates.json, sample_manifest
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
S = r"D:\treeroute\analysis\shap_v1"


def load(p):
    with open(p, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def shape(o, depth=0, maxd=2):
    if isinstance(o, dict):
        if depth >= maxd:
            return "{%d keys}" % len(o)
        return "{" + ", ".join("%s: %s" % (k, shape(v, depth + 1, maxd)) for k, v in o.items()) + "}"
    if isinstance(o, list):
        return "[%d]" % len(o)
    if isinstance(o, str):
        return repr(o[:60])
    return repr(o)


pl = load(os.path.join(S, r"out\coral\lead_0\compare\per_lead.json"))
print("per_lead coral:", shape(pl, 0, 2)[:3000])
aw = load(os.path.join(S, r"out\coral\lead_0\compare\AW4_main_row.json"))
print("\nAW4 coral:", shape(aw, 0, 3)[:2000])
g = load(os.path.join(S, r"rebuild\coral\lead_0\gates.json"))
print("\ngates coral keys:", list(g.keys()))
for k, v in g.get("gates", {}).items():
    print("  ", k, shape(v, 0, 2)[:400])
sm = load(os.path.join(S, r"sample\coral\sample_manifest.json"))
print("\nsample_manifest coral:", shape(sm, 0, 2)[:1500])
