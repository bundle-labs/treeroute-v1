# Exploration only (builder B): list the fenced blocks of the spec (index, start line, line count, first line). Writes nothing.
import sys, os
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "spec", "TABLE_SPEC.md")
with open(SPEC, "r", encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")
blocks = []
inside = False
for i, ln in enumerate(lines, 1):
    if ln == "```":
        if not inside:
            inside = True
            start = i + 1
            cur = []
        else:
            inside = False
            blocks.append((start, cur))
    elif inside:
        cur.append(ln)
for k, (start, b) in enumerate(blocks):
    print("%2d line %4d n=%d | %s" % (k, start, len(b), (b[0][:110] if b else "<empty>")))
