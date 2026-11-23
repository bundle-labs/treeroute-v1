import json
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
t = json.load(open(V + r"\skeptic\numbers\work\s41_tie_artifacts.json", encoding="utf-8"))

def walk(o, path="", depth=0, maxd=3):
    if depth > maxd:
        return
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, (dict, list)):
                print("  " * depth + f"{k}: {type(v).__name__}({len(v)})  {json.dumps(v)[:300]}")
                walk(v, path + "/" + k, depth + 1, maxd)
            else:
                print("  " * depth + f"{k}: {repr(v)[:300]}")
    elif isinstance(o, list):
        for i, v in enumerate(o[:6]):
            if isinstance(v, (dict, list)):
                print("  " * depth + f"[{i}] {json.dumps(v)[:400]}")
            else:
                print("  " * depth + f"[{i}] {repr(v)[:200]}")

print("S41 top keys", list(t.keys()) if isinstance(t, dict) else type(t))
walk(t, maxd=2)
f = json.load(open(V + r"\skeptic\numbers\work\s92_final_lines.json", encoding="utf-8"))
print("S92 type", type(f).__name__, len(f))
if isinstance(f, dict):
    for k, v in f.items():
        print("S92", k, json.dumps(v)[:800])
else:
    for x in f[:200]:
        s = json.dumps(x)
        if any(w in s for w in ("91.1", "rbo", "RBO", "3e-5", "collation", "29", "1.5e-15", "bardl", "aet_total_mm", "SHA", "sha")):
            print("S92", s[:700])
