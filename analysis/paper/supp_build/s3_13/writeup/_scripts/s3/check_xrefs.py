"""Cross-reference check of the staged S3_posthoc.md, with the build's regular expressions (writer s3; read only).

Usage: py -3.9 -I -B check_xrefs.py
Supplement headings and table captions come from the live supplement drafts (paper/draft/S*.md), with the staged
S3_posthoc.md in place of the live one; main-text headings from paper/draft/0*.md. Prints every reference in the
staged file's visible text (HTML comments removed) that names no existing supplement heading, section or
supplement table, split into S3.13's own prose, S3.13's tables (as agreed) and the rest of the file. Writes nothing.
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("s3lib", os.path.join(HERE, "s3lib.py"))
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)
spec2 = importlib.util.spec_from_file_location("build_s3", os.path.join(HERE, "build_s3.py"))
B = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(B)

D = os.path.join(L.ROOT, "paper", "draft")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$", re.M)
CAPTION_TABLE_RE = re.compile(r"^\*\*Table\s+(S?\d+(?:\.\d+)?[a-z]?)\b", re.M)
SEC_REF_RE = re.compile(r"\bSections?\s+(?P<first>\d+(?:\.\d+)*)(?P<more>(?:\s*(?:,|and|or|to|–|-)\s*\d+(?:\.\d+)*)*)")
SUP_REF_RE = re.compile(r"\b(?:Supplements?|Sections?)\s+(?P<first>S\d+(?:\.\d+)*)(?P<more>(?:\s*(?:,|and|or|to|–|-)\s*S\d+(?:\.\d+)*)*)")
BARE_SUP_RE = re.compile(r"(?<!Table )(?<!Tables )(?<!Supplement )(?<!Supplements )(?<!Section )(?<!Sections )"
                         r"(?<![\w.])(S\d+\.\d+(?:\.\d+)?)(?=[,;)\s])")


def heading_number(h):
    m = re.match(r"^(S?\d+(?:\.\d+)*)\s", h + " ")
    return m.group(1) if m else None


def base_of(num):
    m = re.match(r"^(S?\d+(?:\.\d+)?)", num)
    return m.group(1) if m else num


def vis(text):
    return re.sub(r"<!--.*?-->", lambda m: " " * len(m.group(0)), text, flags=re.S)


def main():
    staged = open(B.DST, encoding="utf-8").read()
    sup_heads, sup_tables, man_heads = set(), set(), set()
    for name in sorted(os.listdir(D)):
        if not name.endswith(".md"):
            continue
        if name.startswith("S"):
            txt = staged if name == "S3_posthoc.md" else open(os.path.join(D, name), encoding="utf-8").read()
            v = vis(txt)
            sup_heads |= {heading_number(h.group(2)) for h in HEADING_RE.finditer(v)}
            sup_tables |= {base_of(m.group(1)) for m in CAPTION_TABLE_RE.finditer(v)}
        elif name[:2].isdigit():
            v = vis(open(os.path.join(D, name), encoding="utf-8").read())
            man_heads |= {heading_number(h.group(2)) for h in HEADING_RE.finditer(v)}
    sup_heads.discard(None)
    man_heads.discard(None)
    v = vis(staged)
    s0 = v.index("## S3.13 ")
    s1 = v.index("<!-- Cross-check pass") if "<!-- Cross-check pass" in v else len(v)
    blocks, _ = B.table_blocks()
    spans = []
    for name in B.ORDER:
        blk = vis(blocks[name].replace(B.S321_OLD, B.S321_NEW))
        i = v.index(blk)
        spans.append((i, i + len(blk)))

    def where(pos):
        if any(a <= pos < b for a, b in spans):
            return "S3.13 tables"
        return "S3.13 prose" if s0 <= pos else "rest of file"
    problems = []
    for m in BARE_SUP_RE.finditer(v):
        if m.group(1) not in sup_heads:
            problems.append((where(m.start()), "bare '%s' is not a supplement heading" % m.group(1),
                             v[max(0, m.start() - 50):m.end() + 10].replace("\n", " ")))
    for m in SEC_REF_RE.finditer(v):
        for n in [m.group("first")] + re.findall(r"\d+(?:\.\d+)*", m.group("more") or ""):
            if n not in man_heads:
                problems.append((where(m.start()), "Section %s does not exist" % n, v[m.start():m.end() + 10]))
    for m in SUP_REF_RE.finditer(v):
        for n in [m.group("first")] + re.findall(r"S\d+(?:\.\d+)*", m.group("more") or ""):
            if n not in sup_heads:
                problems.append((where(m.start()), "'%s' is not a supplement heading" % n, v[m.start():m.end() + 10]))
    for m in re.finditer(r"\bTables?\s+(S\d+\.\d+)", v):
        if base_of(m.group(1)) not in sup_tables:
            problems.append((where(m.start()), "Table %s does not exist" % m.group(1), v[m.start():m.end() + 10]))
    print("supplement headings:", len(sup_heads), "supplement tables:", len(sup_tables), "main headings:", len(man_heads))
    for w in ("S3.13 prose", "S3.13 tables", "rest of file"):
        ps = [p for p in problems if p[0] == w]
        print("== %s: %d" % (w, len(ps)))
        for p in ps:
            print("   %s | ...%s..." % (p[1], p[2]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
