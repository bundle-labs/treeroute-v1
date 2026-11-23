"""Scan the agreed S3.13 tables' prose for the GLOSSARY's do-not-use names.

Usage: py -3.12 -X utf8 -I -B gloss_scan.py <GLOSSARY.md> <tables.md>
Prose = the file with HTML comments and backtick code spans removed.
"""
import re
import sys
from collections import defaultdict


def names_from_glossary(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("| **"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4:
                continue
            term = re.sub(r"\*\*", "", cells[0])
            others = re.sub(r"<!--.*?-->", "", cells[1])
            for raw in others.split(","):
                n = raw.strip()
                n = re.sub(r"\((banned|coral|C9 name|ours|nowcast row|rivals)\)", "", n).strip()
                n = n.strip('"').strip("'").strip()
                if not n or n == "—":
                    continue
                rows.append((n, term))
    return rows


def prose_lines(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    text = re.sub(r"<!--.*?-->", lambda m: " " * len(m.group(0)), text, flags=re.S)
    out = []
    for i, line in enumerate(text.split("\n"), 1):
        line = re.sub(r"`[^`]*`", " ", line)
        out.append((i, line))
    return out


def main():
    gl, tb = sys.argv[1], sys.argv[2]
    names = names_from_glossary(gl)
    lines = prose_lines(tb)
    hits = defaultdict(list)
    for n, term in names:
        pat = re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", re.I)
        for i, line in lines:
            for m in pat.finditer(line):
                a, b = max(0, m.start() - 45), min(len(line), m.end() + 45)
                hits[(n, term)].append((i, line[a:b].replace("\n", " ")))
    for (n, term), hs in sorted(hits.items(), key=lambda kv: -len(kv[1])):
        print("== %r (paper term: %s): %d hits" % (n, term, len(hs)))
        seen = set()
        k = 0
        for i, ctx in hs:
            key = ctx.strip()
            if key in seen:
                continue
            seen.add(key)
            print("   L%d: ...%s..." % (i, ctx.strip()))
            k += 1
            if k >= 4:
                break


if __name__ == "__main__":
    main()
