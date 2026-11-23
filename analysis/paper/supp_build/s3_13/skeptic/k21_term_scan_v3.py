# Skeptic (version 3 check, item 4): whole-file term scan of tables_agreed.md against GLOSSARY.md's "do not use" names
# (column 2), on the visible text (HTML comments and backtick code spans removed): captions, notes, row labels, column
# headers and text cells. A hit that lies inside a paper term of column 1 (for example "guard" inside "skill guard")
# is counted apart and not listed. Also: AI terms and "agent" anywhere in tables_agreed.md and in cells.json's cell
# texts. Read-only; prints only.
import json, os, re, sys
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
T = open(os.path.join(OUT, "reconcile", "tables_agreed.md"), encoding="utf-8").read()
L = T.split("\n")[:-1]
vis = [re.sub(r"`[^`]*`", " ", re.sub(r"<!--.*?-->", " ", x)) for x in L]

G = open(os.path.join(ROOT, "paper", "draft", "GLOSSARY.md"), encoding="utf-8").read().split("\n")
names, terms = [], set()
for x in G:
    if not x.startswith("| **"):
        continue
    c = [y.strip() for y in x.strip().strip("|").split("|")]
    c0 = re.sub(r"<!--.*?-->", "", c[0])
    bold = re.findall(r"\*\*(.+?)\*\*", c0)
    row = bold[0]
    for b in bold:
        if b == "arithmetic / geometric / arcsine-scale normal":
            terms.update(["arithmetic normal", "geometric normal", "arcsine-scale normal"])
        elif " / " in b:
            terms.update(p.strip() for p in b.split(" / "))
        else:
            terms.add(b)
    # paper-term phrases from the definitions that the paper uses as terms
    for extra in re.findall(r"\*\*(.+?)\*\*", c[2] if len(c) > 2 else ""):
        terms.add(extra)
    raw = re.sub(r"<!--.*?-->", "", c[1])
    for n in re.split(r",\s*", raw):
        n = n.strip()
        n = re.sub(r"\s*\((?:banned|coral|C9 name|nowcast row|rivals|ours)\)", "", n)
        n = n.replace('"', "").strip()
        if not n or n == "—":
            continue
        if " / " in n and n not in ("plain / corrector", "keep / watch / conditional / ban verdicts"):
            parts = [p.strip() for p in n.split(" / ")]
            if n == "the shipped / LIVE engine":
                parts = ["the shipped engine", "the LIVE engine"]
            if n == "legal minimum / maximum":
                parts = ["legal minimum", "legal maximum"]
            for p in parts:
                names.append((p, row))
        else:
            names.append((n, row))
terms |= {"rival board", "skill guard", "router fit rows", "survey visit", "survey visits", "dataset package",
          "written rules", "identity tolerance", "identity tolerances", "tree bank", "tree answers", "corrected answers",
          "trees-off fit", "seasonal normal", "router context", "own-history features", "naive baselines",
          "per-location router", "region router", "neighbour router", "router type", "answer type", "forecast leads",
          "error-weighted", "uniformly weighted", "absolute-error booster", "Tweedie booster", "published rivals",
          "CEMS seasonal fire weather index forecast (SEAS5)", "test window", "training median", "declared bounds",
          "last-5-years normals", "climatology-identity check", "identity-link twin", "adopted arm", "final answer",
          "decline target", "scored locations", "bank locations", "tree inputs", "the nowcast"}
terms = sorted(terms, key=len, reverse=True)
print("GLOSSARY: %d do-not-use names, %d paper-term phrases" % (len(names), len(terms)))


def inside_term(text, s, e):
    low = text.lower()
    for P in terms:
        pl = P.lower()
        hit = low[s:e]
        o = pl.find(hit)
        while o >= 0:
            a = s - o
            if a >= 0 and low[a:a + len(pl)] == pl:
                return P
            o = pl.find(hit, o + 1)
    return None


hits = defaultdict(list)
inside = defaultdict(int)
for n, row in names:
    flags = 0 if len(n) <= 2 or n in ("Model", "Bank") else re.I
    plural = r"(?:s|es)?" if len(n) > 2 and n[-1].isalpha() else ""
    rx = re.compile(r"(?<![\w-])" + re.escape(n) + plural + r"(?![\w-])", flags)
    for i, x in enumerate(vis, 1):
        for m in rx.finditer(x):
            P = inside_term(x, m.start(), m.end())
            if P:
                inside[(n, P)] += 1
                continue
            hits[(n, row)].append((i, x[max(0, m.start() - 45):m.end() + 45].strip()))
print("hits inside a paper term (not listed): %d, e.g. %s" % (sum(inside.values()), sorted(inside.items(), key=lambda z: -z[1])[:12]))
print("do-not-use names with hits outside a paper term: %d" % len(hits))
for (n, row), hs in sorted(hits.items(), key=lambda z: (z[0][1], z[0][0])):
    ls = sorted(set(i for i, _ in hs))
    print("== %r (glossary row: %s): %d hits on lines %s" % (n, row, len(hs), ls[:40] + (["..."] if len(ls) > 40 else [])))
    seen = set()
    for i, ctx in hs:
        key = re.sub(r"\d", "#", ctx)
        if key in seen:
            continue
        seen.add(key)
        print("      L%d: ...%s..." % (i, ctx))
        if len(seen) >= 4:
            break

ai = re.compile(r"(?i)\b(agents?|agentic|AI|LLMs?|Claude|Anthropic|OpenAI|GPT|chatbot|assistants?|subagents?|workflows?|"
                r"language models?|generated by|automated|automatically|prompts?|copilot|bots?)\b")
print("AI terms anywhere in tables_agreed.md (comments included):", [(i + 1, m.group(0)) for i, x in enumerate(L) for m in ai.finditer(x)])
J = json.load(open(os.path.join(OUT, "reconcile", "cells.json"), encoding="utf-8"))
print("AI terms in cells.json cell texts:", sorted(set(m.group(0) for e in J["entries"] for m in ai.finditer(e["cell"]))))
