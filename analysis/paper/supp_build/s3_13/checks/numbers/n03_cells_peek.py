# n03: structure of reconcile/cells.json (read-only)
import json
import os
import hashlib

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
CELLS = os.path.join(ROOT, r"paper\supp_build\s3_13\reconcile\cells.json")
b = open(CELLS, "rb").read()
print("sha256", hashlib.sha256(b).hexdigest(), len(b))
d = json.loads(b.decode("utf-8"))
print(type(d))
if isinstance(d, dict):
    print("keys:", list(d.keys())[:20])
    for k, v in list(d.items())[:3]:
        print(k, type(v), (json.dumps(v)[:1500]))
elif isinstance(d, list):
    print("len", len(d))
    for x in d[:5]:
        print(json.dumps(x)[:800])
