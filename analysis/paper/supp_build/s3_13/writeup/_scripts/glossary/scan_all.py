"""Count hits of every do-not-use name of a glossary in a Markdown file's prose (read only).

Usage: py -3.9 -I -B scan_all.py <GLOSSARY.md> <file.md>
Same rule as the lead's glossary scan: names from column 2 of the rows that start
with "| **", split at commas, with the listed parentheticals and quotes stripped;
prose without HTML comments and backtick code spans; whole word, case-insensitive.
Prints each name that hits, with its count and one context.
"""
import re
import sys

STRIP = r"\((banned|coral|C9 name|ours|nowcast row|rivals)\)"


def main():
    sys.stdout.reconfigure(encoding="ascii", errors="backslashreplace")
    names = []
    with open(sys.argv[1], encoding="utf-8") as f:
        for line in f:
            if not line.startswith("| **"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4:
                continue
            term = re.sub(r"\*\*", "", cells[0])
            for raw in re.sub(r"<!--.*?-->", "", cells[1]).split(","):
                n = re.sub(STRIP, "", raw.strip()).strip().strip('"').strip("'").strip()
                if n and n != "—":
                    names.append((n, term))
    with open(sys.argv[2], encoding="utf-8") as f:
        text = f.read()
    text = re.sub(r"<!--.*?-->", lambda m: " " * len(m.group(0)), text, flags=re.S)
    lines = [re.sub(r"`[^`]*`", " ", ln) for ln in text.split("\n")]
    for n, term in names:
        pat = re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", re.I)
        cnt, first = 0, None
        for i, ln in enumerate(lines, 1):
            for m in pat.finditer(ln):
                cnt += 1
                if first is None:
                    a, b = max(0, m.start() - 35), min(len(ln), m.end() + 35)
                    first = "L%d ...%s..." % (i, ln[a:b].strip())
        if cnt:
            print("%-28s %4d  (%s)  %s" % (n, cnt, term[:40], first))


if __name__ == "__main__":
    main()
