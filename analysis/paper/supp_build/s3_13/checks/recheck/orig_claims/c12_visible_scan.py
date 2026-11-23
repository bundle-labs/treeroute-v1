"""Scan the visible text (HTML comments removed) of the new S3.13, the new 5.4 paragraph and table_9.md for
AI terms, 'agent', absolute local paths and the words 'archived'/'archive' (read only).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(os.path.dirname(HERE))
D = os.path.join(OUT, "stage", "paper", "draft")

TERMS = [r"\bAI\b", r"\bagents?\b", r"\bClaude\b", r"\bLLM\b", r"\bworkflow", r"\bsubagent", r"\bmodel knowledge\b",
         r"[A-Za-z]:[\\/]", r"\barchiv", r"\bskeptic", r"\bowner\b"]


def visible(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def scan(name, text):
    vis = visible(text)
    for t in TERMS:
        for m in re.finditer(t, vis):
            s = max(0, m.start() - 70)
            print("%s: %-14s ...%s..." % (name, t, vis[s:m.end() + 70].replace("\n", " ")))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    with open(os.path.join(D, "S3_posthoc.md"), "r", encoding="utf-8") as fh:
        s3 = fh.read()
    a = s3.index("## S3.13 ")
    b = s3.index("<!-- Cross-check pass (2026-10-27", a)
    scan("S3.13", s3[a:b])
    with open(os.path.join(D, "05_rivals.md"), "r", encoding="utf-8") as fh:
        r5 = fh.read()
    i = r5.index("Table 9 compares, post hoc")
    j = r5.index("\n", i)
    scan("5.4", r5[i:j])
    with open(os.path.join(D, "tables", "table_9.md"), "r", encoding="utf-8") as fh:
        scan("Table 9", fh.read())
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
