# Exploration only (builder B): rebuild gates, sample register and manifests. Writes nothing.
import sys, json, os
sys.stdout.reconfigure(encoding="utf-8")

SHAP = r"D:\treeroute\analysis\shap_v1"
PROBS = ["pm25", "ndvi", "fire", "defo", "coral"]


def jl(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def short(o, depth=0, maxd=2):
    if isinstance(o, dict):
        if depth >= maxd:
            return "{...%d keys}" % len(o)
        return "{" + ", ".join("%s: %s" % (k, short(v, depth + 1, maxd)) for k, v in o.items()) + "}"
    if isinstance(o, list):
        if len(o) > 4:
            return "[%d items: %s ...]" % (len(o), ", ".join(short(x, depth + 1, maxd) for x in o[:2]))
        return "[" + ", ".join(short(x, depth + 1, maxd) for x in o) + "]"
    if isinstance(o, str) and len(o) > 80:
        return repr(o[:80] + "...")
    return repr(o)


for p in PROBS:
    g = jl(os.path.join(SHAP, "rebuild", p, "lead_0", "gates.json"))
    print("=" * 20, p, "top keys", list(g.keys()))
    print("  stopped_at", g.get("stopped_at"))
    print("  result", short(g.get("result"), maxd=1))
    for name, gv in g["gates"].items():
        print("  gate", name, "pass", gv.get("pass"), "keys", list(gv.keys()))
        print("      values", short(gv.get("values"), maxd=2))

print()
with open(os.path.join(SHAP, "SAMPLE_REGISTER.txt"), "r", encoding="utf-8") as f:
    for i, line in enumerate(f.read().split("\n"), 1):
        print("REG line", i, repr(line))
for p in PROBS:
    m = jl(os.path.join(SHAP, "sample", p, "sample_manifest.json"))
    print("MAN", p, "keys", list(m.keys()))
    print("   n", m.get("n"), "frame_rows", m.get("frame_rows"), "regions_in_sample", m.get("regions_in_sample"), "units_in_sample", m.get("units_in_sample"))
    print("   background_rows", m.get("background_rows"))
    print("   sha256", m.get("sha256"))
