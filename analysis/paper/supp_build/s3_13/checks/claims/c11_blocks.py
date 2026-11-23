"""Are the agreed table blocks in the staged S3 and table_9.md, byte for byte? (read only)

Splits OUT/reconcile/tables_agreed.md into blocks, each starting at a '**Table S3.xx' or '**Table 9.' caption
line and running to the line before the next caption or '## ' heading (trailing blank lines dropped). Each block
must occur once in the staged S3_posthoc.md (S3 tables) or in staged tables/table_9.md (Table 9). For a block
not found, prints the first differing line. Also prints the first line of tables_agreed.md (its comment) cut.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(os.path.dirname(HERE))
AGREED = os.path.join(OUT, "reconcile", "tables_agreed.md")
S3 = os.path.join(OUT, "stage", "paper", "draft", "S3_posthoc.md")
T9 = os.path.join(OUT, "stage", "paper", "draft", "tables", "table_9.md")


def blocks(lines):
    out = []
    cur = None
    for ln in lines:
        if ln.startswith("**Table S3.") or ln.startswith("**Table 9."):
            if cur:
                out.append(cur)
            cur = [ln]
        elif ln.startswith("## "):
            if cur:
                out.append(cur)
            cur = None
        elif cur is not None:
            cur.append(ln)
    if cur:
        out.append(cur)
    res = []
    for b in out:
        while b and b[-1] == "":
            b = b[:-1]
        res.append(b)
    return res


def main():
    with open(AGREED, "r", encoding="utf-8", newline="") as fh:
        agreed = fh.read()
    with open(S3, "r", encoding="utf-8", newline="") as fh:
        s3 = fh.read()
    with open(T9, "r", encoding="utf-8", newline="") as fh:
        t9 = fh.read()
    print("agreed CR:", agreed.count("\r"), "s3 CR:", s3.count("\r"), "t9 CR:", t9.count("\r"))
    lines = agreed.split("\n")
    print("agreed line 1 (cut):", lines[0][:300])
    s3_lines = s3.split("\n")
    for b in blocks(lines):
        text = "\n".join(b)
        target = t9 if b[0].startswith("**Table 9.") else s3
        cnt = target.count(text)
        name = b[0][:22]
        if cnt == 1:
            print("%-24s found once (%d lines)" % (name, len(b)))
            continue
        print("%-24s found %d times (%d lines); without its caption line: found %d times" % (
            name, cnt, len(b), target.count("\n".join(b[1:]))))
        # locate the caption's line in the staged file and show the first differing line
        tl = target.split("\n")
        starts = [i for i, l in enumerate(tl) if l.startswith(b[0][:40])]
        for st in starts[:1]:
            for k, ln in enumerate(b):
                if st + k >= len(tl) or tl[st + k] != ln:
                    print("   first difference at block line %d:" % (k + 1))
                    print("   agreed: %s" % ln[:400])
                    print("   staged: %s" % (tl[st + k][:400] if st + k < len(tl) else "<end>"))
                    break
    return 0


if __name__ == "__main__":
    sys.exit(main())
