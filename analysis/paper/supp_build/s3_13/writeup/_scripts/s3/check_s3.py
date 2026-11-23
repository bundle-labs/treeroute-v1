"""Check the staged S3_posthoc.md against the live file, the agreed tables and the paper rules (writer s3; read only).

Usage: py -3.9 -I -B check_s3.py
Prints: the line diff (live -> staged) by kind; the table blocks found; the order of first citations and placements;
privacy, AI-term and path checks on the visible text of S3.13; the author-year citations of S3.13's visible text;
and the glossary do-not-use names found in S3.13's prose outside its tables (the lead's scan rule).
Writes one file: work/s313_prose_only.md (S3.13's prose without tables, for the scan), inside STAGE.
"""
import difflib
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

STAGED = B.DST
GLOSS = os.path.join(L.STAGE, "paper", "draft", "GLOSSARY.md")
TAB_REF_RE = re.compile(r"\bTables?\s+(?P<first>S?\d+(?:\.\d+)?[a-z]?)(?P<more>(?:\s*(?:,|and|or|to|–|-)\s*S?\d+(?:\.\d+)?[a-z]?)*)")
AI_STRONG = re.compile(r"\bAI\b|(?i:\bartificial intelligence\b|\bgenerative\b|\blarge language models?\b|\bLLMs?\b|\bchatgpt\b|\bcopilot\b|\bclaude\b|\banthropic\b)|\bGPT-?\d")
AI_WEAK = re.compile(r"(?i)\bagents?\b")
YEAR_TOKEN_RE = re.compile(r"(?<![\w\-–/.])(?:(?P<y>(?:1[6-9]|20)\d\d[a-z]?)(?![\w])(?![\-–/.]\d)|(?P<nd>n\.d\.))")


def strip_comments(s):
    return re.sub(r"<!--.*?-->", lambda m: " " * len(m.group(0)), s, flags=re.S)


def main():
    with open(B.LIVE, encoding="utf-8", newline="") as f:
        live = f.read()
    with open(STAGED, "rb") as f:
        raw = f.read()
    print("staged sha256", L.sha256_bytes(raw), "bytes", len(raw), "BOM", raw.startswith(b"\xef\xbb\xbf"),
          "CR", b"\r" in raw, "ends LF", raw.endswith(b"\n"))
    staged = raw.decode("utf-8")
    a, b = live.split("\n"), staged.split("\n")
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        print("diff %s live %d-%d -> staged %d-%d" % (op, i1 + 1, i2, j1 + 1, j2))
    # table blocks
    blocks, _ = B.table_blocks()
    blocks["S3.21"] = blocks["S3.21"].replace(B.S321_OLD, B.S321_NEW)
    for name in B.ORDER:
        print("block %s occurrences in staged: %d" % (name, staged.count(blocks[name])))
    # first citations and placements (visible text)
    vis = strip_comments(staged)
    sec_start = vis.index("## S3.13 ")
    caps = {}
    for m in re.finditer(r"^\*\*Table (S3\.\d+)", vis, flags=re.M):
        caps.setdefault(m.group(1), m.start())
    first = {}
    for m in TAB_REF_RE.finditer(vis):
        names = [m.group("first")] + re.findall(r"S?\d+(?:\.\d+)?[a-z]?", m.group("more") or "")
        # a caption's own "Table S3.NN" is not a citation
        line_start = vis.rfind("\n", 0, m.start()) + 1
        if vis.startswith("**Table", line_start) and m.start() == line_start + 2:
            continue
        for k, n in enumerate(names):
            n = re.sub(r"[a-z]$", "", n)
            first.setdefault(n, (m.start(), k))
    prev = (-1, -1)
    for name in B.ORDER:
        fc, cp = first.get(name), caps.get(name)
        ok = fc is not None and cp is not None and fc[0] < cp and fc[0] > sec_start and fc > prev
        print("%s first cited at %s, caption at %s: %s" % (name, fc, cp, "OK" if ok else "PROBLEM"))
        prev = fc if fc is not None else prev
    # every caption after the paragraph that first cites it: no other caption between the citation and it,
    # except the captions of tables first cited in the same paragraph
    for name in B.ORDER:
        fc, cp = first[name], caps[name]
        para_start = vis.rfind("\n\n", 0, fc[0])
        para_end = vis.find("\n\n", fc[0])
        between = [n for n in B.ORDER if fc[0] < caps[n] < cp]
        same_para = [n for n in B.ORDER if para_start < first[n][0] < para_end]
        bad = [n for n in between if n not in same_para]
        print("%s placed after its citing paragraph: %s" % (name, "OK" if not bad and cp > para_end else bad))
    caps_order = sorted(B.ORDER, key=lambda n: caps[n])
    print("captions in order:", caps_order == B.ORDER)
    # S3.13 prose only (no table blocks), visible text
    sec_raw = staged[staged.index("## S3.13 "):staged.index("<!-- Cross-check pass")]
    prose_raw = sec_raw
    for name in B.ORDER:
        prose_raw = prose_raw.replace(blocks[name], "")
    os.makedirs(os.path.join(HERE, "work"), exist_ok=True)
    with open(os.path.join(HERE, "work", "s313_prose_only.md"), "w", encoding="utf-8", newline="") as f:
        f.write(prose_raw)
    pv = strip_comments(prose_raw)
    sv = strip_comments(sec_raw)
    for rx, what in ((AI_STRONG, "AI term"), (AI_WEAK, "agent")):
        hits = [sv[max(0, m.start() - 40):m.end() + 40] for m in rx.finditer(sv)]
        print("%s hits in S3.13 visible text: %d %s" % (what, len(hits), hits[:3]))
    paths = re.findall(r"[A-Za-z]:[\\/][^\s)]*", sv)
    print("absolute paths in S3.13 visible text:", paths[:5])
    for w in ("fire", "defo", "unit", "units", "cell", "cells", "group", "groups", "lead 0", "test years", "donor",
              "pool", "GLS", "guard", "kind", "tool", "ours", "climatology", "horizon"):
        rx = re.compile(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", re.I)
        txt = re.sub(r"`[^`]*`", " ", pv)
        hs = [txt[max(0, m.start() - 30):m.end() + 30].replace("\n", " ") for m in rx.finditer(txt)]
        if hs:
            print("prose word %r: %d" % (w, len(hs)), hs[:4])
    # bare "visit" not preceded by "survey "
    txt = re.sub(r"`[^`]*`", " ", pv)
    bare = [txt[max(0, m.start() - 30):m.end() + 10] for m in re.finditer(r"(?<!survey )\bvisits?\b", txt)]
    print("bare 'visit' in prose:", len(bare), bare[:3])
    # author-year citations in S3.13 visible text
    for m in YEAR_TOKEN_RE.finditer(sv):
        ctx = sv[max(0, m.start() - 45):m.end() + 2].replace("\n", " ")
        print("year token:", repr(ctx))
    # glossary do-not-use names in S3.13 prose (the lead's scan rule)
    names = []
    with open(GLOSS, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("| **"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4:
                continue
            term = re.sub(r"\*\*", "", cells[0])
            others = re.sub(r"<!--.*?-->", "", cells[1])
            for raw_n in others.split(","):
                n = raw_n.strip()
                n = re.sub(r"\((banned|coral|C9 name|ours|nowcast row|rivals)\)", "", n).strip()
                n = n.strip('"').strip("'").strip()
                if n and n != "—":
                    names.append((n, term))
    counts = {}
    for n, term in names:
        rx = re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", re.I)
        k = len(rx.findall(txt))
        if k:
            counts[(n, term)] = k
    for (n, term), k in sorted(counts.items(), key=lambda kv: -kv[1]):
        print("gloss name %r (term %s): %d" % (n, term, k))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
