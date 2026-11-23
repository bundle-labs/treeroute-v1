import json, os
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
a = json.load(open(V + r"\reconcile\mismatches.json", encoding="utf-8"))
b = json.load(open(V + r"\skeptic\reconcile\rerun\mismatches.json", encoding="utf-8"))
diff = [k for k in set(a) | set(b) if a.get(k) != b.get(k)]
print("mismatches.json top-level fields differing:", diff, a.get("written_at"), b.get("written_at"))
sa = json.load(open(V + r"\reconcile\work\summary.json", encoding="utf-8"))
p = V + r"\skeptic\reconcile\rerun\work\summary.json"
print("rerun summary exists", os.path.exists(p))
if os.path.exists(p):
    sb = json.load(open(p, encoding="utf-8"))
    d2 = [k for k in set(sa) | set(sb) if sa.get(k) != sb.get(k)]
    print("summary.json fields differing:", d2)
    for k in d2:
        print("  ", k, str(sa.get(k))[:80], "|", str(sb.get(k))[:80])
