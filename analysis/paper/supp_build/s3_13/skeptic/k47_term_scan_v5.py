# Skeptic (version 5 check, item 4): the whole-file term scan of k32, re-run on version 5 (tables_agreed.md) and on
# version 4 (tables_agreed_v4.md), against GLOSSARY.md's "do not use" names (column 2), on the visible text (HTML
# comments and backtick code spans removed). A hit inside a paper term of column 1 is counted apart and not listed.
# Prints (1) every v4 hit grouped by name, (2) the hits that are new in v4 (not on the same line with the same context
# in v3), (3) the v3 hits that are gone in v4; and the AI-term scan of both files and of cells.json. Read-only.
# The code and its printed labels are k32's: here "v4" stands for version 5 and "v3" for version 4.
import json, os, re, sys
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))


def load(name):
    T = open(os.path.join(OUT, "reconcile", name), encoding="utf-8").read()
    L = T.split("\n")[:-1]
    return L, [re.sub(r"`[^`]*`", " ", re.sub(r"<!--.*?-->", " ", x)) for x in L]


L4, vis4 = load("tables_agreed.md")  # here: version 5
L3, vis3 = load("tables_agreed_v4.md")  # here: version 4

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
          "decline target", "scored locations", "bank locations", "tree inputs", "the nowcast", "plain tree answers",
          "tree-bank", "tree answer"}
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


def scan(vis):
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
    return hits, inside


h4, in4 = scan(vis4)
h3, in3 = scan(vis3)
print("v4: hits inside a paper term (not listed): %d; v3: %d" % (sum(in4.values()), sum(in3.values())))
print("v4 inside-term counts that differ from v3:", {k: (in3.get(k, 0), v) for k, v in in4.items() if in3.get(k, 0) != v},
      {k: (v, 0) for k, v in in3.items() if k not in in4})
print("do-not-use names with hits outside a paper term: v4 %d, v3 %d" % (len(h4), len(h3)))
print()
print("### (1) every v4 hit, by name")
for (n, row), hs in sorted(h4.items(), key=lambda z: (z[0][1], z[0][0])):
    ls = sorted(set(i for i, _ in hs))
    print("== %r (glossary row: %s): %d hits on lines %s" % (n, row, len(hs), ls[:40] + (["..."] if len(ls) > 40 else [])))
    seen = set()
    for i, ctx in hs:
        key = re.sub(r"\d", "#", ctx)
        if key in seen:
            continue
        seen.add(key)
        print("      L%d: ...%s..." % (i, ctx))
        if len(seen) >= 3:
            break
print()
print("### (2) hits new in v4 (name, line, context not in v3)")
s3 = {(k[0], i, c) for k, hs in h3.items() for i, c in hs}
s4 = {(k[0], i, c) for k, hs in h4.items() for i, c in hs}
for n, i, c in sorted(s4 - s3, key=lambda z: (z[1], z[0])):
    print("   NEW  %r L%d: ...%s..." % (n, i, c))
print("### (3) v3 hits gone in v4")
for n, i, c in sorted(s3 - s4, key=lambda z: (z[1], z[0])):
    print("   GONE %r L%d: ...%s..." % (n, i, c))
# counts by name on the changed lines
chg = [i + 1 for i in range(len(L4)) if L3[i] != L4[i]]
print("### per changed line: names hit in v3 -> v4")
for k in chg:
    a = sorted(n for (n, row), hs in h3.items() for i, _ in hs if i == k)
    b = sorted(n for (n, row), hs in h4.items() for i, _ in hs if i == k)
    if a != b:
        print("   L%d: %s -> %s" % (k, a, b))

ai = re.compile(r"(?i)\b(agents?|agentic|AI|LLMs?|Claude|Anthropic|OpenAI|GPT|chatbot|assistants?|subagents?|workflows?|"
                r"language models?|generated by|automated|automatically|prompts?|copilot|bots?)\b")
print("AI terms anywhere in tables_agreed.md v4 (comments included):", [(i + 1, m.group(0)) for i, x in enumerate(L4) for m in ai.finditer(x)])
J = json.load(open(os.path.join(OUT, "reconcile", "cells.json"), encoding="utf-8"))
print("AI terms in cells.json cell texts:", sorted(set(m.group(0) for e in J["entries"] for m in ai.finditer(e["cell"]))))
