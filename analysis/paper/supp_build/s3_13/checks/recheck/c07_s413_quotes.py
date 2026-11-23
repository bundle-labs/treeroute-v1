"""Check every quoted string of Table S4.13 rows AW-BB (staged S4) against the rulings file (read only).

A quoted string is text between straight double quotes in the row's visible text (HTML comments removed).
Each must occur, character for character, in engine/OWNER_RULINGS_2026-10-06.md. Also checks that each
quote in the words column lies inside the rulings file's section of that row's letters.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
S4 = os.path.join(OUT, "stage", "paper", "draft", "S4_provenance.md")
RUL = os.path.join(ROOT, "engine", "OWNER_RULINGS_2026-10-06.md")


def sections(text):
    out = {}
    cur = None
    buf = []
    for ln in text.split("\n"):
        m = re.match(r"^## ([A-Z]{1,2})\. ", ln)
        if m:
            if cur:
                out[cur] = "\n".join(buf)
            cur = m.group(1)
            buf = [ln]
        elif cur:
            if ln.startswith("## "):
                out[cur] = "\n".join(buf)
                cur = None
                buf = []
            else:
                buf.append(ln)
    if cur:
        out[cur] = "\n".join(buf)
    return out


def main():
    with open(S4, "r", encoding="utf-8") as fh:
        s4 = fh.read().replace("\r\n", "\n")
    with open(RUL, "r", encoding="utf-8") as fh:
        rul = fh.read().replace("\r\n", "\n")
    secs = sections(rul)
    bad = 0
    n = 0
    for letters in ("AW", "AX", "AY", "AZ", "BA", "BB"):
        rows = [ln for ln in s4.split("\n") if ln.startswith("| %s | " % letters)]
        if len(rows) != 1:
            print(letters, "rows found:", len(rows))
            bad += 1
            continue
        row = re.sub(r"<!--.*?-->", "", rows[0])
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        words = cells[-1]
        for cellname, cell in (("summary", cells[2]), ("words", words)):
            for q in re.findall(r'"([^"]+)"', cell):
                n += 1
                in_file = q in rul
                in_sec = q in secs.get(letters, "")
                flag = "ok" if (in_file and (cellname == "summary" or in_sec)) else "MISSING"
                if flag != "ok":
                    bad += 1
                print("%s %-7s %-7s in_file=%s in_section=%s  %r" % (letters, cellname, flag, in_file, in_sec, q[:110]))
    print("quotes checked:", n, "problems:", bad)
    return 0


if __name__ == "__main__":
    sys.exit(main())
