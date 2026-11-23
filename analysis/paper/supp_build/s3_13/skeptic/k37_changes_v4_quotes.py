# Skeptic (version 4 check, item 1): every fenced text of CHANGES_v4.md, with the label line above it, and where it
# occurs: tables v3 / v4, spec v3 / v4, CHANGES_v3.md. An "OLD" text must be in v3 and (outside its NEW) not in v4;
# a "NEW" text must be in v4. Read-only; prints only.
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
rd = lambda *p: open(os.path.join(OUT, *p), encoding="utf-8", newline="").read()
src = {"T3": rd("reconcile", "tables_agreed_v3.md"), "T4": rd("reconcile", "tables_agreed.md"),
       "S3": rd("spec", "TABLE_SPEC_v3.md"), "S4": rd("spec", "TABLE_SPEC.md"), "C3": rd("spec", "CHANGES_v3.md")}
L = rd("spec", "CHANGES_v4.md").split("\n")
i, n = 0, 0
while i < len(L):
    if L[i].startswith("```"):
        j = i + 1
        while not L[j].startswith("```"):
            j += 1
        body = "\n".join(L[i + 1:j])
        lab = next((L[k] for k in range(i - 1, -1, -1) if L[k].strip()), "")
        n += 1
        occ = {k: (body in v) for k, v in src.items()}
        print("%2d L%-4d %-60s | %s" % (n, i + 1, lab[:60], " ".join("%s:%s" % (k, "y" if v else "-") for k, v in occ.items())))
        i = j + 1
    else:
        i += 1
print("fenced texts:", n)
