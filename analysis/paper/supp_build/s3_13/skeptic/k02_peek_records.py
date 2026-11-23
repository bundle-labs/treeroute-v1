# Skeptic peek 2: run records (gates.json keys/values for the S3.21 gates, exactness, manifest, register,
# bardl_maxima first block, B1 log lines). Read-only; prints only.
import json, sys, re
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
V = SHAP + r"\verify_v1"

for p in ["pm25", "defo", "coral"]:
    g = json.load(open(SHAP + r"\rebuild\%s\lead_0\gates.json" % p, encoding="utf-8"))
    print("== gates", p, "top keys:", list(g.keys()))
    print("   result:", json.dumps(g.get("result"))[:400])
    print("   stopped_at:", g.get("stopped_at"))
    for k, v in g["gates"].items():
        vals = v.get("values")
        s = json.dumps(vals)
        print("   ", k, "pass=", v.get("pass"), "values:", s[:300])

for p in ["pm25", "fire"]:
    for m in ["rival_rf", "rival_ridge"]:
        e = json.load(open(SHAP + r"\out\%s\lead_0\%s\exactness.json" % (p, m), encoding="utf-8"))
        print("== exactness", p, m, {k: e.get(k) for k in ["pass", "rows", "bit_equal_rows", "max_abs_diff"]}, "raw" in e)
    e = json.load(open(SHAP + r"\out\%s\lead_0\rival_ridge\ridge_shap_exactness.json" % p, encoding="utf-8"))
    print("== ridge_shap_exactness", p, {k: e.get(k) for k in ["pass", "stage", "rows", "bit_equal_rows", "max_abs_diff"]}, e.get("raw", {}).get("bit_equal_rows") if isinstance(e.get("raw"), dict) else e.get("raw"))
e = json.load(open(SHAP + r"\out\ndvi\lead_0\rival_bardl_h1\exactness.json", encoding="utf-8"))
print("== exactness ndvi bardl", {k: e.get(k) for k in ["pass", "rows", "bit_equal_rows", "max_abs_diff"]}, e.get("raw"))
m = json.load(open(SHAP + r"\out\fire\lead_0\treeroute\meta.json", encoding="utf-8"))
print("== meta fire treeroute keys:", list(m.keys()))
print({k: m.get(k) for k in ["rows", "pass", "checks_passed", "link", "guard", "max_abs_additivity_error", "max_abs_additivity_error_variable", "structural_zero_violations", "pairs", "arm"]})
m = json.load(open(SHAP + r"\out\fire\lead_0\rival_ridge\meta.json", encoding="utf-8"))
print({k: m.get(k) for k in ["rows", "pass", "checks_passed", "link", "guard", "max_abs_additivity_error", "max_abs_additivity_error_variable", "structural_zero_violations"]})
mf = json.load(open(SHAP + r"\sample\ndvi\sample_manifest.json", encoding="utf-8"))
print("== manifest ndvi", {k: mf.get(k) for k in ["n", "frame_rows", "regions_in_sample", "units_in_sample"]}, mf.get("background_rows", {}).get("0"))
print("== SAMPLE_REGISTER.txt")
raw = open(SHAP + r"\SAMPLE_REGISTER.txt", "rb").read()
print("bytes", len(raw), "CRLF" if b"\r\n" in raw else "LF")
for i, line in enumerate(raw.decode("utf-8").splitlines(), 1):
    print(i, line[:260])
print("== bardl_maxima.txt first 12 lines")
raw = open(V + r"\_lead\outputs\bardl_maxima.txt", "rb").read()
print("BOM" if raw.startswith(b"\xef\xbb\xbf") else "noBOM", "CRLF" if b"\r\n" in raw else "LF")
for i, line in enumerate(raw.decode("utf-8-sig").splitlines()[:12], 1):
    print(i, line)
for p in ["pm25", "ndvi", "fire", "defo"]:
    lines = open(SHAP + r"\logs\tr_shap_%s_lead0.log" % p, encoding="utf-8", errors="replace").read().splitlines()
    print("== log", p, "lines", len(lines))
    for i, line in enumerate(lines, 1):
        if "background pairs" in line or "done in" in line:
            print(i, line[:220])
