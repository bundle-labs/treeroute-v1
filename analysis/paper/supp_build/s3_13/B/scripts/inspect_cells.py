# Inspection only (builder B): prints selected cells.json entries and summary counts. Writes nothing.
import sys, os, json, collections
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_B = os.path.dirname(HERE)
with open(os.path.join(OUT_B, "cells.json"), "r", encoding="utf-8") as f:
    raw = f.read()
doc = json.loads(raw)
print("top keys", list(doc.keys()), doc["tables_file"], doc["spec"])
E = doc["entries"]
print("entries", len(E))
print("first 600 chars of the file:")
print(raw[:600])
cnt = collections.Counter((e["table"], e["panel"]) for e in E)
for k in sorted(cnt, key=lambda k: (k[0] != "9", k)):
    print("  ", k, cnt[k])
parts = collections.Counter(e["part"] for e in E)
print("parts", dict(parts))
print("undefined entries:")
for e in E:
    if e["printed"] == "undefined":
        print("  ", e["line"], e["table"], e["panel"], e["row"], e["column"], e["part"], e["source"], e["selector"], e["stored"])
print("n_finite entries:")
for e in E:
    if e["part"] == "n_finite":
        print("  ", e["line"], e["table"], e["panel"], e["row"], e["column"], e["printed"], e["source"], e["selector"], e["stored"])
print("note entries:")
for e in E:
    if e["row"] == "note":
        print("  ", e["line"], e["table"], repr(e["panel"]), e["column"], e["part"], e["printed"], e["source"], e["selector"], e["stored"])
print("some S3.19/S3.20/S3.21/S3.30 entries:")
for e in E:
    if e["table"] in ("S3.19", "S3.21", "S3.30") or (e["table"] == "S3.20" and e["row"].startswith("fire:")):
        print("  ", e["line"], e["table"], e["panel"], e["row"], e["column"], e["part"], e["printed"], e["source"], e["selector"], e["stored"])
keys_order = set(tuple(e.keys()) for e in E)
print("entry key orders", keys_order)
# line order is non-decreasing
print("lines non-decreasing:", all(E[i]["line"] <= E[i + 1]["line"] for i in range(len(E) - 1)))
