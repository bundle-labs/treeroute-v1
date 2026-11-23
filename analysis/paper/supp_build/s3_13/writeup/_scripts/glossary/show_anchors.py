"""Print the anchor lines of the staged PAPER_FACTS.md and GLOSSARY.md (read only).

Usage: py -3.9 -I -B show_anchors.py <PAPER_FACTS.md> <GLOSSARY.md>
Prints repr() of the lines the edits anchor on, so quotes, dashes and line
endings are seen exactly, and counts each anchor's occurrences.
"""
import sys


def main():
    sys.stdout.reconfigure(encoding="ascii", errors="backslashreplace")
    pf, gl = sys.argv[1], sys.argv[2]
    with open(pf, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8")
    lines = text.split("\n")
    for i in (16, 17, 18, 22, 23, 24, 25, 26):
        print("PF L%d: %r" % (i + 1, lines[i][:220]))
    stale = 'which hold ONI and GPCC SPI values, both "Not until confirmed" in S9.2; Part B never ran.'
    print("PF stale count:", text.count(stale))
    idx = text.find(stale)
    print("PF stale context:", repr(text[idx - 120: idx + len(stale) + 5]))
    key = "  - **final, post hoc (Part 622)**:"
    print("PF status-key Part 622 count:", text.count(key))
    print("PF 'Part 628' count:", text.count("Part 628"))
    print("PF 'Not until confirmed' count:", text.count("Not until confirmed"))
    with open(gl, "rb") as f:
        graw = f.read()
    gtext = graw.decode("utf-8")
    glines = gtext.split("\r\n")
    for i, ln in enumerate(glines):
        if ln.startswith("| **reference gap**") or ln.startswith("<!-- Cross-check pass"):
            print("GL L%d: %r" % (i + 1, ln[:160]))
            print("GL L%d next: %r" % (i + 2, glines[i + 1][:80] if i + 1 < len(glines) else None))
    print("GL lines (split on CRLF):", len(glines), "last item:", repr(glines[-1]))
    print("GL bare LF count:", graw.count(b"\n") - graw.count(b"\r\n"))


if __name__ == "__main__":
    main()
