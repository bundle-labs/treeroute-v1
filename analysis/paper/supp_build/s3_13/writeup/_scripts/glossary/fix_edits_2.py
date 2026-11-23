"""Fix 2 to the glossary writer's staged GLOSSARY.md rows (STAGED copy only).

Usage: py -3.9 -I -B fix_edits_2.py <STAGE root>
(a) background: the month is not constant within a location; under B2 the static
    columns, the month and the seasonal normal equal the explained row's values on
    every background row (protocol section 5; the S-ZERO condition, Table S3.20).
(b) player: "as an input or an offset" clashed with the glossary's anchor and offset
    senses (row anchor); the calendar clause read as a list of three.
(c) same-link: the clause on c and the upper bound made explicit (Table S3.18 note).
Each old text must occur exactly once; encoding and CRLF line endings are kept.
"""
import os
import sys

FIXES = [
    ("so that on the gridded problems columns constant within a location, such as the static columns, the month and the "
     "seasonal normal, are exactly 0;",
     "so that on the gridded problems the static columns, the month and the seasonal normal, which equal the explained row's "
     "values on every background row, are exactly 0;"),
    ("one distinct input column, or normal (the seasonal normal, as an input or an offset), a router-context column",
     "one distinct input column, or normal (the seasonal normal, in whatever form a model takes it), a router-context column"),
    ("(own-history columns keep their stem, such as hist_last; context columns are calendar, the month and its harmonics, or "
     "ctx: followed by their name, as in ctx:lat)",
     "(own-history columns keep their stem, such as hist_last; the month and its harmonics form the variable calendar, and "
     "another context column is ctx: followed by its name, as in ctx:lat)"),
    ("(the same link, constant c and upper bound; within each problem, the same link), else cross-link;",
     "(the same link, constant c and upper bound, which within a problem comes down to the same link), else cross-link;"),
]


def main():
    path = os.path.join(sys.argv[1], "paper", "draft", "GLOSSARY.md")
    with open(path, "rb") as f:
        text = f.read().decode("utf-8")
    for old, new in FIXES:
        n = text.count(old)
        if n != 1:
            raise SystemExit("old text count %d: %r" % (n, old[:60]))
        text = text.replace(old, new, 1)
    if "\n" in text.replace("\r\n", ""):
        raise SystemExit("bare LF would be written")
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))
    print("fixed rows:", len(FIXES))


if __name__ == "__main__":
    main()
