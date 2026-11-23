import sys, json, os, math
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(os.path.dirname(HERE), "cells.json"), "r", encoding="utf-8") as f:
    E = json.load(f)["entries"]
ties = []
for e in E:
    st = e["stored"]
    if len(st) == 1 and isinstance(st[0], float):
        x = st[0]
        # exact binary ties at the second decimal: 100*x has fractional part exactly .5
        y = x * 100.0
        if (y - math.floor(y)) == 0.5 and e["printed"][-1:].isdigit() and "%" not in e["printed"]:
            ties.append(e)
        if e["printed"].endswith("%"):
            z = x * 1000.0
            if (z - math.floor(z)) == 0.5:
                ties.append(e)
for e in ties:
    print(e["line"], e["table"], e["panel"], e["row"], e["column"], e["part"], e["printed"], e["stored"])
neg = [e for e in E if e["printed"].startswith("\u2212")]
print("negative printed:", len(neg))
und = [e for e in E if e["printed"] == "undefined"]
print("undefined:", len(und))
for e in und:
    print("  ", e["line"], e["table"], e["panel"], e["row"], e["column"], e["cell"])
fin = [e for e in E if e["part"] == "n_finite"]
print("n_finite printed:", len(fin))
for e in fin:
    print("  ", e["line"], e["table"], e["panel"], e["row"], e["column"], e["cell"])
lt = [e for e in E if e["printed"] == "<0.1%"]
print("<0.1%:", len(lt))
for e in lt:
    print("  ", e["line"], e["table"], e["panel"], e["row"], e["column"], e["part"], e["stored"])
