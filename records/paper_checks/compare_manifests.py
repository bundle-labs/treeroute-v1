"""Read-only: does every file hashed in the stage-train manifest keep its sha256 in the live (stage-test) manifest?

Usage: py -3.12 -I compare_manifests.py <old_manifest.json> <new_manifest.json>
"""
import json
import sys


def entries(obj):
    """Find the dict of file entries (path -> {sha256, ...}) wherever it sits in the manifest."""
    best = {}
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            vals = list(cur.values())
            if vals and all(isinstance(v, dict) and "sha256" in v for v in vals):
                if len(cur) > len(best):
                    best = cur
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return best


old = json.load(open(sys.argv[1], encoding="utf-8"))
new = json.load(open(sys.argv[2], encoding="utf-8"))
eo, en = entries(old), entries(new)
same = [k for k in eo if k in en and en[k]["sha256"] == eo[k]["sha256"]]
changed = [k for k in eo if k in en and en[k]["sha256"] != eo[k]["sha256"]]
missing = [k for k in eo if k not in en]
added = [k for k in en if k not in eo]
print(f"old entries {len(eo)}, new entries {len(en)}")
print(f"kept with the same sha256: {len(same)}; changed: {len(changed)}; missing from new: {len(missing)}; added in new: {len(added)}")
print("changed:", changed[:10])
print("missing:", missing[:10])
tags = sorted({k.split("/")[-1].split("__")[-1] for k in added})
print("added name endings:", tags[:20])
print("added sample:", added[:6])
top_old = {k: v for k, v in old.items() if not isinstance(v, (dict, list))}
top_new = {k: v for k, v in new.items() if not isinstance(v, (dict, list))}
print("old top-level scalars:", top_old)
print("new top-level scalars:", top_new)
