"""Count whole-word, case-insensitive hits of candidate names in a Markdown file's prose.

Usage: py -3.9 -I -B name_hits.py <file.md> <names.txt>
Prose = the file with HTML comments and backtick code spans removed (the same
rule as the lead's glossary scan). names.txt holds one candidate name per line.
Read only; prints each name with its hit count and up to three contexts.
"""
import re
import sys


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
    sys.stdout.reconfigure(encoding="ascii", errors="backslashreplace")
    lines = prose_lines(sys.argv[1])
    with open(sys.argv[2], encoding="utf-8") as f:
        names = [n.strip() for n in f if n.strip()]
    for n in names:
        pat = re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", re.I)
        hits = []
        for i, line in lines:
            for m in pat.finditer(line):
                a, b = max(0, m.start() - 40), min(len(line), m.end() + 40)
                hits.append((i, line[a:b]))
        print("%-45s %d" % (n, len(hits)))
        for i, ctx in hits[:3]:
            print("      L%d: ...%s..." % (i, ctx.strip()))


if __name__ == "__main__":
    main()
