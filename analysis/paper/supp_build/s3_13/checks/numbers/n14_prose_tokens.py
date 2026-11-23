# n14: number tokens of the new visible text, each looked up in the facts its comment cites (or the row's Source cell).
# Visible text = the added lines of the live->staged diff, HTML comments removed; tables of S3.13 removed.
# Prints every token that is not found verbatim in a cited fact, for manual review. Read-only.
import difflib
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
OUT = os.path.join(ROOT, r"paper\supp_build\s3_13")
ST = os.path.join(OUT, "stage")
HERE = os.path.dirname(os.path.abspath(__file__))
facts = open(os.path.join(ST, r"paper\PAPER_FACTS.md"), "rb").read().decode("utf-8")
F = {}
for m in re.finditer(r"^- \*\*([A-Z]{1,3}\d+[a-z]?) \((?:final|provisional)[^\n]*$", facts, flags=re.M):
    F[m.group(1)] = m.group(0)


def norm(s):
    return s.replace("\u2212", "-").replace("\u00a0", " ")


num_re = re.compile(r"(?<![\w.\-])[\u2212-]?\d[\d,]*(?:\.\d+)?(?:%)?(?![\w])|10⁻[⁰¹²³⁴⁵⁶⁷⁸⁹]+")


def added_lines(rel, live):
    s = open(os.path.join(ST, rel), "rb").read().decode("utf-8").replace("\r\n", "\n").split("\n")
    l = open(live, "rb").read().decode("utf-8").replace("\r\n", "\n").split("\n") if os.path.exists(live) else []
    sm = difflib.SequenceMatcher(None, l, s, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("insert", "replace"):
            out += s[j1:j2]
    return out


def strip_tables(text):
    agreed = open(os.path.join(OUT, r"reconcile\tables_agreed.md"), "rb").read().decode("utf-8")
    return "\n".join(l for l in text.split("\n") if not l.startswith("|") and not l.startswith("**Table S3.") and not re.match(r"^[ᵃᵇᶜᵈᵉᶠᵍ†‡§*]", l) and not l.startswith("**a.") and not l.startswith("**b.") and not l.startswith("**c.") and not l.startswith("**d.") and not l.startswith("**e.") and not l.startswith("**f.") and not l.startswith("**g."))


CONST = {"1,000", "2,000", "0.9", "0.95", "95%", "10⁻¹²", "10⁻⁹", "1", "2", "3", "5", "10", "20", "0"}


def check(label, text):
    # split into (visible, following comment)
    pos = 0
    segs = []
    for m in re.finditer(r"<!--(.*?)-->", text, flags=re.S):
        segs.append((text[pos:m.start()], m.group(1)))
        pos = m.end()
    segs.append((text[pos:], ""))
    miss = []
    ntok = 0
    for vis, com in segs:
        # mask dates, section numbers, rule/ID tokens before scanning
        v = re.sub(r"\b\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?\b", " DATE ", vis)
        v = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", " TIME ", v)
        v = re.sub(r"\b(S\d+(\.\d+)*|Table S?\d+(\.\d+)?|Tables S3\.\d+|Section \d+(\.\d+)?|Part \d+|Parts? \d+|[A-Z]{1,3}\d+[a-z]?|E\d+[a-z]?|D\d+|C\d+|B\d|V\d+_?|p = 0\.9 and 0\.95|p = 0\.9|UTC\+\d|MERRA-2|EAC4|VT0007|v\d+|log\(y \+ c\)|top-\d+|top \d+|Lundberg and Lee 2017|Janzing et al\. 2020|Lundberg et al\. 2020|Webber et al\. 2010|Kendall and Babington Smith 1939|Kraft et al\. \(2019\)|lines? \d+(-\d+)?|item \d+|items \d+-\d+|\d+-\d+ local)\b", " X ", v)
        toks = num_re.findall(v)
        ids = set(re.findall(r"\b([A-Z]{1,3}\d+[a-z]?)\b", com))
        src = " ".join(norm(F[i]) for i in ids if i in F)
        for t in toks:
            ntok += 1
            tt = norm(t)
            if tt in CONST or t in CONST:
                continue
            if tt in src:
                continue
            ctx = vis[max(0, vis.find(t) - 70): vis.find(t) + len(t) + 40].replace("\n", " ")
            miss.append((t, sorted(ids), ctx))
    print("== %s: tokens %d, not found in a cited fact: %d" % (label, ntok, len(miss)))
    for t, ids, ctx in miss:
        print("   %r ids=%s :: ...%s..." % (t, ids, ctx))


s3 = "\n".join(added_lines(r"paper\draft\S3_posthoc.md", os.path.join(ROOT, r"paper\draft\S3_posthoc.md")))
i = s3.find("## S3.13 ")
check("S3.13 prose", strip_tables(s3[i:]))
check("S3 header/S3.0", s3[:i])
check("05_rivals 5.4", "\n".join(added_lines(r"paper\draft\05_rivals.md", os.path.join(ROOT, r"paper\draft\05_rivals.md"))))
s1 = added_lines(r"paper\draft\S1_disclosures.md", os.path.join(ROOT, r"paper\draft\S1_disclosures.md"))
for l in s1:
    if l.startswith("| PH") or l.startswith("| RP18"):
        # Source cell facts count as cited
        cells = l.split(" | ")
        srcs = cells[-1] if len(cells) > 3 else ""
        check(l[:7], l.replace(" -->", " " + srcs + " -->", 0) + " <!-- " + srcs + " -->")
s4 = added_lines(r"paper\draft\S4_provenance.md", os.path.join(ROOT, r"paper\draft\S4_provenance.md"))
for l in s4:
    if l.startswith("| 2026-11-1") or l.startswith("| A") or l.startswith("| B") or l.startswith("| 628") or l.startswith("- **Times") or l.startswith("Table S4.1") or l.startswith("All five"):
        check("S4 " + l[:30], l + " <!-- A9 A10 A24 A25 A26 A28 -->")
g = added_lines(r"paper\draft\GLOSSARY.md", os.path.join(ROOT, r"paper\draft\GLOSSARY.md"))
check("GLOSSARY", "\n".join(g) + " <!-- A10 -->")
