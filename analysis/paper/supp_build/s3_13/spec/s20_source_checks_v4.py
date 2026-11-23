# s20_source_checks_v4.py - version 4 of TABLE_SPEC.md (2026-11-17): cheap read-only checks of the claims of the
# change order OUT\_brief\fix_order_v4.md against the sources it names. Prints the source lines with their line
# numbers and the E3a and E3m values of the five rebuild records; writes nothing; runs no script of SHAP, V or the
# engine. Any string that holds a user folder is masked before printing.
# Run from this folder: py -3.9 -I -B s20_source_checks_v4.py
import hashlib
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)                                  # ROOT\paper\supp_build\s3_13
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
SHAP = "D:/treeroute/analysis/shap_v1"
PROBLEMS = ["pm25", "ndvi", "fire", "defo", "coral"]


def mask(s):
    return re.sub(r"(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\"']+", "<user folder>", s)


def lines_of(path, enc="utf-8"):
    with open(path, encoding=enc) as fh:
        return fh.read().split("\n")


def show(label, L, nums):
    print("--", label)
    for n in nums:
        print("   L{}: {}".format(n, mask(L[n - 1])))


def short(v, width=150):
    s = mask(json.dumps(v, ensure_ascii=False))
    return s if len(s) <= width else s[:width] + " ...({} chars)".format(len(s))


print("== 1. SHAP\\rebuild\\<p>\\lead_0\\gates.json: E3a and E3m")
for p in PROBLEMS:
    with open(SHAP + "/rebuild/" + p + "/lead_0/gates.json", encoding="utf-8") as fh:
        g = json.load(fh)
    gates = g["gates"]
    for k in sorted(gates):
        if not k.startswith("E3a") and not k.startswith("E3m"):
            continue
        v = gates[k].get("values")
        print("  {} {} pass={}".format(p, k, gates[k].get("pass")))
        if isinstance(v, dict):
            for kk in v:
                if kk == "files" and isinstance(v[kk], list):
                    for i, f in enumerate(v[kk]):
                        if isinstance(f, dict):
                            print("     files[{}] keys {}".format(i, list(f)))
                            for fk, fv in f.items():
                                if isinstance(fv, list):
                                    print("       {}: list of {}".format(fk, len(fv)))
                                    for j, item in enumerate(fv):
                                        print("         [{}] {}".format(j, short(item, 200)))
                                else:
                                    print("       {}: {}".format(fk, short(fv)))
                        else:
                            print("     files[{}] {}".format(i, short(f)))
                elif kk == "checked" and isinstance(v[kk], (list, dict)):
                    keys = list(v[kk]) if isinstance(v[kk], dict) else v[kk]
                    print("     checked ({}): {}".format(len(keys), short(keys, 900)))
                else:
                    print("     {}: {}".format(kk, short(v[kk], 300)))
        else:
            print("     values: {}".format(short(v, 300)))

print()
print("== 2. SHAP\\PROTOCOL.md")
P = lines_of(SHAP + "/PROTOCOL.md")
show("E3a, E3m, E3 (section 4.1)", P, [175, 176, 177, 178, 179, 180])
show("E5 (what the bank fingerprint covers; V4-6)", P, [182])
show("E8", P, [198])
show("B2 on coral", P, [375])
show("context columns and families (section 8)", P, [487, 488, 489, 490, 491, 492])

print()
print("== 3. ROOT\\paper\\draft\\GLOSSARY.md (rows by paper term)")
G = lines_of(os.path.join(ROOT, "paper", "draft", "GLOSSARY.md"))
for t in ["location", "router context", "tree answer", "tree bank", "tree inputs", "survey visit", "answer type",
          "reference", "naive baseline"]:
    hits = [i for i, ln in enumerate(G, 1) if re.match(r"^\| \*\*" + re.escape(t) + r"\*\*", ln)]
    if len(hits) != 1:
        print("   {}: found {} rows".format(t, len(hits)))
    for i in hits:
        print("   L{}: {}".format(i, mask(G[i - 1])))

print()
print("== 4. ROOT\\paper\\draft\\03_protocol.md L17-25 (headings and the baselines and reference paragraphs)")
D = lines_of(os.path.join(ROOT, "paper", "draft", "03_protocol.md"))
show("03_protocol.md", D, [17, 21, 23, 25])

print()
print("== 5. OUT\\reconcile\\tables_agreed.md (version 3 of tables.md)")
with open(os.path.join(OUT, "reconcile", "tables_agreed.md"), "rb") as fh:
    raw = fh.read()
print("   sha256 {}  lines {}".format(hashlib.sha256(raw).hexdigest(), raw.count(b"\n")))
A = raw.decode("utf-8").split("\n")
hits = [i for i, ln in enumerate(A, 1) if ln.startswith("ᵃ Rows checked:")]
show("Table S3.20 note a", A, hits)
show("S3.25 lines 354-375 (Link cell only)", [ln.split(" | ")[1] if ln.startswith("| ") and " | " in ln else ln
                                              for ln in A], list(range(354, 376)))
