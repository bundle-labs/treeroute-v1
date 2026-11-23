# Skeptic (version 3 check, item 2e): gate E3m checks a moved file against "every freeze-lock record of its recorded
# path"; version 3's text says "the run's locks". What do the named lock files record? Prints only top-level keys and
# short non-path scalar values (path-like values are masked). Read-only; prints only.
import json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
REG = r"D:\treeroute\registry\freeze"
pathlike = re.compile(r"(?i)[a-z]:[\\/]|[\\/]users[\\/]|\\\\")
for p in ["pm25", "ndvi", "fire"]:
    g = json.load(open(SHAP + r"\rebuild\%s\lead_0\gates.json" % p, encoding="utf-8"))
    files = g["gates"]["E3m_recorded_path_map"]["values"]["files"]
    for f in files:
        print("==", p, "| locks named by E3m:", f["locks"])
        for name in f["locks"]:
            fp = os.path.join(REG, name)
            if not os.path.exists(fp):
                print("   ", name, "not found")
                continue
            d = json.load(open(fp, encoding="utf-8"))
            short = {}
            for k, v in d.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    s = str(v)
                    short[k] = "<path>" if pathlike.search(s) else s[:60]
                else:
                    short[k] = "<%s of %d>" % (type(v).__name__, len(v))
            print("   ", name, json.dumps(short, ensure_ascii=False)[:900])
