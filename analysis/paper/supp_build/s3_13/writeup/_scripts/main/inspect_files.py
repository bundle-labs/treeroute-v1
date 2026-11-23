"""Read-only: encoding, line endings and SHA-256 of the files this writer touches or copies from.

Run: py -3.9 -I -B inspect_files.py
Prints, per file: size, SHA-256, BOM, CRLF count, bare-LF count, bare-CR count, final newline.
Paths are built from this script's own location (STAGE/_scripts/main/), so no user path is written here.
"""
import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.dirname(os.path.dirname(HERE))          # .../s3_13/stage
OUT = os.path.dirname(STAGE)                             # .../s3_13
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))  # research-paper folder
D = os.path.join(ROOT, "paper", "draft")

FILES = [
    ("D/05_rivals.md", os.path.join(D, "05_rivals.md")),
    ("D/TABLE_NUMBERS.md", os.path.join(D, "TABLE_NUMBERS.md")),
    ("D/tables/table_6.md", os.path.join(D, "tables", "table_6.md")),
    ("D/tables/table_7.md", os.path.join(D, "tables", "table_7.md")),
    ("D/tables/table_9.md", os.path.join(D, "tables", "table_9.md")),
    ("OUT/reconcile/tables_agreed.md", os.path.join(OUT, "reconcile", "tables_agreed.md")),
    ("STAGE/paper/PAPER_FACTS.md", os.path.join(STAGE, "paper", "PAPER_FACTS.md")),
    ("STAGE/paper/draft/05_rivals.md", os.path.join(STAGE, "paper", "draft", "05_rivals.md")),
    ("STAGE/paper/draft/TABLE_NUMBERS.md", os.path.join(STAGE, "paper", "draft", "TABLE_NUMBERS.md")),
    ("STAGE/paper/draft/tables/table_9.md", os.path.join(STAGE, "paper", "draft", "tables", "table_9.md")),
]


def describe(path):
    if not os.path.exists(path):
        return "absent"
    with open(path, "rb") as fh:
        data = fh.read()
    sha = hashlib.sha256(data).hexdigest()
    bom = data.startswith(b"\xef\xbb\xbf")
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    cr = data.count(b"\r") - crlf
    final = "LF" if data.endswith(b"\n") else ("none" if data else "empty")
    try:
        data.decode("utf-8")
        utf8 = "utf-8 ok"
    except UnicodeDecodeError as exc:
        utf8 = "NOT utf-8 (%s)" % exc
    return "%d bytes; sha256 %s; BOM %s; CRLF %d; bare LF %d; bare CR %d; final %s; %s" % (
        len(data), sha, bom, crlf, lf, cr, final, utf8)


for label, path in FILES:
    print("%-40s %s" % (label, describe(path)))
