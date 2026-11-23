"""Where do the binary name hits of b13 come from? (1) Each .docx of the test build: XML/rels parts decompressed
and scanned (as the build does) and, apart, its media files; (2) each figure PNG: the text chunks (tEXt, zTXt, iTXt)
and the raw bytes. Names are taken in memory (environment, user folders, earlier account names found in the
live files) and never printed; only part names, chunk keys and counts are printed. Read-only.
Run: py -3.9 -I -B b14_docx_png.py
"""
import re
import struct
import sys
import zipfile
import zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from b04_lib import CHK, PAIRS, NAME_PATS, read_bytes, text_of

cands = set()
for rel, live in PAIRS:
    if live is None:
        continue
    t = text_of(read_bytes(live))
    for m in re.finditer(r"(?i)[A-Za-z]:[\\/]+Users[\\/]+([^\\/\s`'\")]+)", t):
        cands.add(m.group(1))
    for m in re.finditer(r"(?i)[A-Za-z]--Users-([A-Za-z0-9_.-]+?)-(?:Desktop|Downloads|Documents|OneDrive)", t):
        cands.add(m.group(1))
cands = {c for c in cands if len(c) >= 3 and c.casefold() not in {"public", "default", "<user>", "user"}}
env_pats = list(NAME_PATS)
old_pats = [re.compile(r"(?<![A-Za-z0-9])" + r"(?:[\s_.\-]|%20)*".join(re.escape(w) for w in re.split(r"[\s_.\-]+", c) if w)
                       + r"(?![A-Za-z0-9])", re.I) for c in sorted(cands)]


def count(t):
    return sum(len(list(p.finditer(t))) for p in env_pats), sum(len(list(p.finditer(t))) for p in old_pats)


for d in ("copy", "copy_live"):
    for name in ("manuscript_REVIEW.docx", "supplement_REVIEW.docx", "highlights_REVIEW.docx"):
        p = CHK / d / "paper" / "build" / name
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                b = z.read(n)
                t = b.decode("utf-8", "replace") if n.endswith((".xml", ".rels")) else b.decode("latin-1")
                e, o = count(t)
                if e or o:
                    print("%s/%s part %s: environment names %d, earlier names %d" % (d, name, n, e, o))
for p in sorted((CHK / "copy" / "paper" / "figures").rglob("*.png")):
    b = p.read_bytes()
    i = 8
    chunks = []
    while i + 8 <= len(b):
        ln = struct.unpack(">I", b[i:i + 4])[0]
        typ = b[i + 4:i + 8].decode("latin-1")
        data = b[i + 8:i + 8 + ln]
        if typ in ("tEXt", "zTXt", "iTXt"):
            key = data.split(b"\x00", 1)[0].decode("latin-1")
            body = data.split(b"\x00", 1)[1] if b"\x00" in data else b""
            if typ == "zTXt":
                try:
                    body = zlib.decompress(body[1:])
                except zlib.error:
                    pass
            e, o = count(body.decode("latin-1"))
            chunks.append("%s[%s] (%d B; names %d/%d)" % (typ, key, len(body), e, o))
        i += 12 + ln
        if typ == "IEND":
            break
    e, o = count(b.decode("latin-1"))
    print("%s: text chunks %s; raw-byte name matches %d/%d" % (p.relative_to(CHK).as_posix(), chunks or "none", e, o))
