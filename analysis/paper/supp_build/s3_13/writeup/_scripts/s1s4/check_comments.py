# Read-only: comment delimiters balanced and not nested in this writer's staged files; year tokens and
# capitalised word + year pairs in the new visible text (possible author-year citations) listed.
import os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.normpath(os.path.join(HERE, "..", ".."))
WORK = os.path.join(HERE, "work")
YEAR_TOKEN_RE = re.compile(r"(?<![\w\-–/.])(?:(?P<y>(?:1[6-9]|20)\d\d[a-z]?)(?![\w])(?![\-–/.]\d)|(?P<nd>n\.d\.))")
for rel in ("paper/draft/S1_disclosures.md", "paper/draft/S4_provenance.md", "paper/PAPER_FACTS.md"):
    t = open(os.path.join(STAGE, *rel.split("/")), "rb").read().decode("utf-8").replace("\r\n", "\n")
    depth, bad, i = 0, [], 0
    for m in re.finditer(r"<!--|-->", t):
        if m.group(0) == "<!--":
            if depth:
                bad.append(("nested open", t.count("\n", 0, m.start()) + 1))
            depth += 1
        else:
            if not depth:
                bad.append(("stray close", t.count("\n", 0, m.start()) + 1))
            depth = max(0, depth - 1)
    if depth:
        bad.append(("unclosed at end", 0))
    print(rel, "opens", t.count("<!--"), "closes", t.count("-->"), "problems", bad[:5])
    b = open(os.path.join(WORK, rel.replace("/", "__") + ".base"), "rb").read().decode("utf-8").replace("\r\n", "\n")
    vis = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    visb = re.sub(r"<!--.*?-->", " ", b, flags=re.S)
    yrs = [(m.group(0), vis[max(0, m.start()-30):m.start()].replace("\n", " ")) for m in YEAR_TOKEN_RE.finditer(vis)]
    yrsb = [(m.group(0), visb[max(0, m.start()-30):m.start()].replace("\n", " ")) for m in YEAR_TOKEN_RE.finditer(visb)]
    new = [y for y in yrs if y not in yrsb]
    print("   year tokens in visible text: staged %d, base %d; new ones:" % (len(yrs), len(yrsb)))
    for y, ctx in new[:40]:
        print("      %s  <- ...%s" % (y, ctx))
