# Skeptic (version 5 check, item 1): every fenced text of CHANGES_v5.md, with the label line above it, and where it
# occurs: tables v4 / v5, spec v4 / v5 (sections 0-11 and section 12 apart). An "OLD" or "v4 spec" text must be in
# v4 and (outside its NEW) not in v5; a "NEW" or "v5 spec" text must be in v5. Also the quotes of its last section
# (in double quotes) against PROTOCOL.md, GLOSSARY.md and tr_rebuild.py. Adapted from k37. Read-only; prints only.
import os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
SHAP = r"D:\treeroute\analysis\shap_v1"
rd = lambda *p: open(os.path.join(OUT, *p), encoding="utf-8", newline="").read()
S5 = rd("spec", "TABLE_SPEC.md")
cut = S5.index("\n## 12. Version 5")
src = {"T4": rd("reconcile", "tables_agreed_v4.md"), "T5": rd("reconcile", "tables_agreed.md"),
       "S4": rd("spec", "TABLE_SPEC_v4.md"), "S5a": S5[:cut], "S5s12": S5[cut:]}
L = rd("spec", "CHANGES_v5.md").split("\n")
i, n, prev_new = 0, 0, {}
while i < len(L):
    if L[i].startswith("```"):
        j = i + 1
        while not L[j].startswith("```"):
            j += 1
        body = "\n".join(L[i + 1:j])
        lab = next((L[k] for k in range(i - 1, -1, -1) if L[k].strip()), "")
        n += 1
        occ = {k: (body in v) for k, v in src.items()}
        print("%2d L%-4d %-58s | %s" % (n, i + 1, lab[:58], " ".join("%s:%s" % (k, "y" if v else "-") for k, v in occ.items())))
        i = j + 1
    else:
        i += 1
print("fenced texts:", n)
P = open(SHAP + r"\PROTOCOL.md", encoding="utf-8").read()
G = open(os.path.join(ROOT, "paper", "draft", "GLOSSARY.md"), encoding="utf-8").read()
TR = open(SHAP + r"\scripts\tr_rebuild.py", encoding="utf-8").read()
norm = lambda s: re.sub(r"\s+", " ", s)
tail = "\n".join(L[next(k for k, x in enumerate(L) if x.startswith("## The order's sources")):])
for q in re.findall(r"\"([^\"]{12,})\"", norm(tail)):
    q2 = q.rstrip(".")
    print("   quote %-70r PROTOCOL %s | GLOSSARY %s | tr_rebuild %s" % (q[:70], q2 in norm(P), q2 in norm(G), q2 in norm(TR)))
