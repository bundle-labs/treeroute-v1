"""Search a PDF's raw bytes and its inflated streams for byte patterns.

Usage: py -3.9 -I -B pdf_grep.py <pdf> <pattern> [pattern ...]

Patterns are plain ASCII text, matched case-insensitively. For each hit prints
where it was found (raw file or stream number) and 160 bytes of context on each
side, non-ASCII bytes as \\xNN. Reads only the file named; writes nothing.
"""
import re
import sys
import zlib


def show(b):
    return "".join(chr(x) if 32 <= x < 127 else "\\x%02X" % x for x in b)


def main():
    path = sys.argv[1]
    pats = [p.lower().encode("ascii") for p in sys.argv[2:]]
    data = open(path, "rb").read()
    blobs = [("raw", data)]
    k = 0
    for m in re.finditer(rb"stream\r?\n", data):
        end = data.find(b"endstream", m.end())
        if end < 0:
            continue
        try:
            d = zlib.decompressobj().decompress(data[m.end():end])
        except zlib.error:
            continue
        if d:
            k += 1
            blobs.append(("stream %d" % k, d))
    for p in pats:
        n = 0
        for name, b in blobs:
            low = b.lower()
            for h in re.finditer(re.escape(p), low):
                n += 1
                if n <= 6:
                    s = h.start()
                    print("[%s] %s @%d: %s" % (p.decode(), name, s, show(b[max(0, s - 160):s + 160])))
        print("== %s: %d hits" % (p.decode(), n))


if __name__ == "__main__":
    main()
