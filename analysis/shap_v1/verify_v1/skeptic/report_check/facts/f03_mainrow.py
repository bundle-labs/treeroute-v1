import json
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
SHAP = r"D:\treeroute\analysis\shap_v1"
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
B = json.load(open(V + r"\B\results.json", encoding="utf-8"))
print("A top keys", list(A.keys()))
print("B top keys", list(B.keys()))
for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    print("=" * 30, p)
    ma = A["problems"][p]["main_row"]
    mb = B["problems"][p]["main_row"]
    print("A main_row:", json.dumps(ma, indent=None)[:4000])
    print("B main_row:", json.dumps(mb, indent=None)[:4000])
    off = json.load(open(SHAP + "\\out\\" + p + r"\lead_0\compare\AW4_main_row.json", encoding="utf-8"))
    print("OFFICIAL:", json.dumps(off, indent=None)[:4000])
