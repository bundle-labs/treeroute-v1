# Skeptic (version 4 check, item 4): every hit, with a wider context, of the do-not-use names whose standing use needs
# a reading by eye (does it stand for its glossary concept?): "the model", "Model", "cell", "site", "unit", "bank",
# "answer", "kept", "features", "guard", "freeze", "climatology", "visit" (outside "survey visit"), "fallback", "pass".
# Visible text of tables_agreed.md version 4 (HTML comments and code spans removed). Read-only; prints only.
import os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
L = open(os.path.join(OUT, "reconcile", "tables_agreed.md"), encoding="utf-8").read().split("\n")[:-1]
vis = [re.sub(r"`[^`]*`", " ", re.sub(r"<!--.*?-->", " ", x)) for x in L]
pats = {"the model": r"(?i)(?<![\w-])the models?(?![\w-])", "Model": r"(?<![\w-])Models?(?![\w-])",
        "cell": r"(?i)(?<![\w-])cells?(?![\w-])", "site": r"(?i)(?<![\w-])sites?(?![\w-])",
        "unit": r"(?i)(?<![\w-])units?(?![\w-])", "bank": r"(?i)(?<![\w-])bank(?![\w-])",
        "answer": r"(?i)(?<![\w-])answers?(?![\w-])", "kept": r"(?i)(?<![\w-])kept(?![\w-])",
        "features": r"(?i)(?<![\w-])features?(?![\w-])", "guard": r"(?i)(?<![\w-])guards?(?![\w-])",
        "freeze": r"(?i)(?<![\w-])freez\w*", "climatology": r"(?i)climatolog\w*",
        "visit": r"(?i)(?<![\w-])visits?(?![\w-])", "fallback": r"(?i)fall ?back\w*", "pass": r"(?i)(?<![\w-])pass(?:es)?(?![\w-])"}
for name, rx in pats.items():
    hs = [(i + 1, m.start(), m.end()) for i, x in enumerate(vis) for m in re.finditer(rx, x)]
    print("== %s: %d hits" % (name, len(hs)))
    seen = set()
    for i, s, e in hs:
        x = vis[i - 1]
        ctx = x[max(0, s - 60):e + 50].strip()
        key = re.sub(r"\d", "#", ctx)
        if key in seen:
            continue
        seen.add(key)
        print("   L%d: ...%s..." % (i, ctx))
