"""Print the text of a PDF's content streams (standard library only).

Usage: py -3.9 -I -B pdf_text.py <pdf> <max_chars> [keyword ...]

Reads the PDF as bytes, inflates every FlateDecode stream it can, and pulls the
strings of the text operators (Tj, TJ, ', ") out of streams that hold text
objects. Prints the first <max_chars> characters of the text, then every
keyword's hits with 300 characters of context on each side. Non-ASCII bytes are
printed as \\xNN so that nothing is guessed. Reads only the file named; writes
nothing.
"""
import re
import sys
import zlib


def inflate_all(data):
    out = []
    for m in re.finditer(rb"stream\r?\n", data):
        start = m.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        raw = data[start:end]
        try:
            d = zlib.decompressobj().decompress(raw)
        except zlib.error:
            continue
        if d:
            out.append(d)
    return out


def parse_string(s, i):
    """s[i] == '(' ; return (bytes, next_index)."""
    depth = 0
    buf = bytearray()
    i += 1
    while i < len(s):
        c = s[i]
        if c == 0x5C:  # backslash
            i += 1
            if i >= len(s):
                break
            e = s[i]
            if e in b"nrtbf":
                buf += {0x6E: b"\n", 0x72: b"\r", 0x74: b"\t", 0x62: b"\b", 0x66: b"\f"}[e]
                i += 1
            elif 0x30 <= e <= 0x37:
                j = i
                while j < len(s) and j < i + 3 and 0x30 <= s[j] <= 0x37:
                    j += 1
                buf.append(int(s[i:j], 8) & 0xFF)
                i = j
            elif e in b"\r\n":
                i += 1
            else:
                buf.append(e)
                i += 1
            continue
        if c == 0x28:
            depth += 1
        elif c == 0x29:
            if depth == 0:
                return bytes(buf), i + 1
            depth -= 1
        buf.append(c)
        i += 1
    return bytes(buf), i


def text_of(stream):
    s = stream
    out = bytearray()
    i = 0
    n = len(s)
    in_array = False
    while i < n:
        c = s[i]
        if c == 0x28:  # (
            b, i = parse_string(s, i)
            out += b
            continue
        if c == 0x5B:  # [
            in_array = True
            i += 1
            continue
        if c == 0x5D:  # ]
            in_array = False
            i += 1
            continue
        if in_array and (c == 0x2D or 0x30 <= c <= 0x39 or c == 0x2E):
            m = re.match(rb"-?[0-9.]+", s[i:i + 20])
            if m:
                try:
                    v = float(m.group(0))
                except ValueError:
                    v = 0.0
                if v < -180:
                    out += b" "
                i += len(m.group(0))
                continue
        m = re.match(rb"(T\*|Td|TD|Tm|ET|')(?![A-Za-z])", s[i:i + 3])
        if m and (i == 0 or s[i - 1] in b" \r\n\t"):
            out += b"\n" if m.group(1) in (b"T*", b"ET", b"'") else b" "
            i += len(m.group(1))
            continue
        i += 1
    return bytes(out)


def show(b):
    return "".join(chr(x) if (32 <= x < 127 or x in (10,)) else "\\x%02X" % x for x in b)


def main():
    path, max_chars = sys.argv[1], int(sys.argv[2])
    keys = sys.argv[3:]
    data = open(path, "rb").read()
    streams = inflate_all(data)
    texts = [text_of(st) for st in streams if b"BT" in st and (b"Tj" in st or b"TJ" in st)]
    full = b"\n=====\n".join(texts)
    full = re.sub(rb"[ \t]+", b" ", full)
    print("streams inflated:", len(streams), "text streams:", len(texts), "text bytes:", len(full))
    print(show(full[:max_chars]))
    low = full.lower()
    for k in keys:
        kb = k.lower().encode("ascii")
        hits = [m.start() for m in re.finditer(re.escape(kb), low)]
        print("\n##### keyword", repr(k), "hits:", len(hits))
        for h in hits[:6]:
            print("---", h)
            print(show(full[max(0, h - 300):h + 300]))


if __name__ == "__main__":
    main()
