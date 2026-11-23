# r00b: print the shapes of the run-record sources used by the tables (read-only; nothing written).
import sys, json, re
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SHAP = Path("D:/treeroute/analysis/shap_v1")
V = SHAP / "verify_v1"


def shape(x, depth=0, maxd=3):
    if isinstance(x, dict):
        if depth >= maxd:
            return "{%d keys}" % len(x)
        return "{" + ", ".join("%s: %s" % (k, shape(v, depth + 1, maxd)) for k, v in list(x.items())[:25]) + (", ..." if len(x) > 25 else "") + "}"
    if isinstance(x, list):
        return "[%d: %s]" % (len(x), shape(x[0], depth + 1, maxd) if x else "")
    return repr(x)[:60]


print("== SAMPLE_REGISTER.txt")
raw = (SHAP / "SAMPLE_REGISTER.txt").read_bytes()
print("bytes", len(raw), "CRLF" if b"\r\n" in raw else "LF", "BOM" if raw.startswith(b"\xef\xbb\xbf") else "noBOM")
for i, l in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
    print(i, l[:300])
print("== bardl_maxima.txt")
raw = (V / "_lead" / "outputs" / "bardl_maxima.txt").read_bytes()
print("bytes", len(raw), "CRLF" if b"\r\n" in raw else "LF", "BOM" if raw.startswith(b"\xef\xbb\xbf") else "noBOM")
for i, l in enumerate(raw.decode("utf-8-sig").splitlines()[:12], 1):
    print(i, l)
for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    print("== log", p)
    lg = (SHAP / "logs" / ("tr_shap_%s_lead0.log" % p))
    if not lg.exists():
        print("  (no log)")
        continue
    L = lg.read_text(encoding="utf-8-sig").splitlines()
    for i, l in enumerate(L, 1):
        if re.match(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] (\w+) lead 0: (\d+) rows, (\d+) background pairs,", l) or " done in " in l:
            print("  ", i, l[:200])
for p in ["pm25", "coral"]:
    g = json.loads((SHAP / "rebuild" / p / "lead_0" / "gates.json").read_text(encoding="utf-8"))
    print("== gates", p, "stopped_at", g.get("stopped_at"), "result", g.get("result"))
    for k, v in g["gates"].items():
        print("   ", k, "pass", v.get("pass"), shape(v.get("values"), 0, 2)[:400])
r = json.loads((V / "A" / "results.json").read_text(encoding="utf-8"))
print("== results.json top", list(r.keys()))
print("b1 keys", {p: list(v.keys()) for p, v in r["b1"].items()})
print("b1.pm25.variable", shape(r["b1"]["pm25"]["variable"], 0, 2)[:1500])
print("b1.pm25.feature.pair_main_b1", shape(r["b1"]["pm25"]["feature"]["pair_main_b1"], 0, 2)[:1500])
print("b1.pm25.run", r["b1"]["pm25"]["run"])
print("b1.pm25.status", r["b1"]["pm25"]["status"])
print("b1.defo", shape(r["b1"]["defo"], 0, 2)[:1500])
print("b1.coral", shape(r["b1"]["coral"], 0, 2)[:600])
print("problems.fire.main_row", shape(r["problems"]["fire"]["main_row"], 0, 3)[:1500])
k0 = list(r["problems"]["pm25"]["levels"]["variable"]["pairs"].keys())[0]
print("a pair", k0, shape(r["problems"]["pm25"]["levels"]["variable"]["pairs"][k0], 0, 2)[:1500])
for p in ["pm25", "coral"]:
    for m in ["treeroute", "rival_ridge", "rival_rf"]:
        f = SHAP / "out" / p / "lead_0" / m / "meta.json"
        print("== meta", p, m, shape(json.loads(f.read_text(encoding="utf-8")), 0, 2)[:900])
        for nm in ("exactness.json", "ridge_shap_exactness.json"):
            f = SHAP / "out" / p / "lead_0" / m / nm
            if f.exists():
                print("   ", nm, shape(json.loads(f.read_text(encoding="utf-8")), 0, 2)[:600])
man = json.loads((SHAP / "sample" / "ndvi" / "sample_manifest.json").read_text(encoding="utf-8"))
print("== manifest ndvi", shape(man, 0, 2)[:1200])
