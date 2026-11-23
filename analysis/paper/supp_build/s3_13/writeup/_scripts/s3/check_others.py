"""Line diff of this writer's other staged files against their start points (writer s3; read only).

Usage: py -3.9 -I -B check_others.py
PAPER_FACTS.md and GLOSSARY.md against the glossary writer's staged copies (work/*.base), REFERENCES.md against the
live file. Prints each changed block (kind, line ranges, the first 160 characters of each new line), the encoding,
BOM and line endings, and the SHA-256 of start and staged files. Writes nothing.
"""
import difflib
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("s3lib", os.path.join(HERE, "s3lib.py"))
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)

PAIRS = [
    (os.path.join(HERE, "work", "paper__PAPER_FACTS.md.base"), os.path.join(L.STAGE, "paper", "PAPER_FACTS.md")),
    (os.path.join(HERE, "work", "paper__draft__GLOSSARY.md.base"), os.path.join(L.STAGE, "paper", "draft", "GLOSSARY.md")),
    (os.path.join(L.ROOT, "paper", "draft", "REFERENCES.md"), os.path.join(L.STAGE, "paper", "draft", "REFERENCES.md")),
]


def main():
    for a_path, b_path in PAIRS:
        with open(a_path, "rb") as f:
            a = f.read()
        with open(b_path, "rb") as f:
            b = f.read()
        print("==", os.path.relpath(b_path, L.STAGE))
        print("   start sha256", L.sha256_bytes(a), "staged sha256", L.sha256_bytes(b), "bytes", len(a), "->", len(b))
        print("   BOM", b.startswith(b"\xef\xbb\xbf"), "CRLF", b.count(b"\r\n"), "LF", b.count(b"\n"),
              "start CRLF", a.count(b"\r\n"), "start LF", a.count(b"\n"))
        al = a.decode("utf-8").splitlines(keepends=True)
        bl = b.decode("utf-8").splitlines(keepends=True)
        sm = difflib.SequenceMatcher(a=al, b=bl, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            print("   %s start %d-%d -> staged %d-%d" % (op, i1 + 1, i2, j1 + 1, j2))
            for ln in bl[j1:j2]:
                print("      + " + ln.rstrip("\r\n")[:160])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
