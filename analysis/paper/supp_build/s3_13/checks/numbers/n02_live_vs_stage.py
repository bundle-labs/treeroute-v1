# n02: line diff live -> staged for every staged file (read-only). Prints a summary and, with an argument,
# the full unified diff of one file to a text file in this folder.
import difflib
import hashlib
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
OUT = os.path.join(ROOT, r"paper\supp_build\s3_13")
STAGE = os.path.join(OUT, "stage")
HERE = os.path.dirname(os.path.abspath(__file__))
SHAP = r"D:\treeroute\analysis\shap_v1"

PAIRS = [
    ("paper/draft/S3_posthoc.md", os.path.join(ROOT, r"paper\draft\S3_posthoc.md")),
    ("paper/draft/05_rivals.md", os.path.join(ROOT, r"paper\draft\05_rivals.md")),
    ("paper/draft/tables/table_9.md", os.path.join(ROOT, r"paper\draft\tables\table_9.md")),
    ("paper/draft/TABLE_NUMBERS.md", os.path.join(ROOT, r"paper\draft\TABLE_NUMBERS.md")),
    ("paper/draft/S1_disclosures.md", os.path.join(ROOT, r"paper\draft\S1_disclosures.md")),
    ("paper/draft/S4_provenance.md", os.path.join(ROOT, r"paper\draft\S4_provenance.md")),
    ("paper/draft/GLOSSARY.md", os.path.join(ROOT, r"paper\draft\GLOSSARY.md")),
    ("paper/draft/REFERENCES.md", os.path.join(ROOT, r"paper\draft\REFERENCES.md")),
    ("paper/PAPER_FACTS.md", os.path.join(ROOT, r"paper\PAPER_FACTS.md")),
    ("paper/PAPER_OUTLINE.md", os.path.join(ROOT, r"paper\PAPER_OUTLINE.md")),
    ("engine/PENDING_PARTS.md", os.path.join(ROOT, r"engine\PENDING_PARTS.md")),
    ("_archive_plan/ARCHIVE_MANIFEST_DRAFT.md", os.path.join(ROOT, r"_archive_plan\ARCHIVE_MANIFEST_DRAFT.md")),
    ("shap/PROTOCOL.md", os.path.join(SHAP, "PROTOCOL.md")),
]


def rb(p):
    with open(p, "rb") as f:
        return f.read()


want = sys.argv[1] if len(sys.argv) > 1 else None
for rel, live in PAIRS:
    st = os.path.join(STAGE, rel.replace("/", "\\"))
    sb = rb(st)
    lb = rb(live) if os.path.exists(live) else b""
    print("%-42s live %s %8d  staged %s %8d" % (rel, hashlib.sha256(lb).hexdigest()[:8] if lb else "absent  ", len(lb),
                                                hashlib.sha256(sb).hexdigest()[:8], len(sb)))
    if want and want == rel:
        L = lb.decode("utf-8").replace("\r\n", "\n").split("\n")
        S = sb.decode("utf-8").replace("\r\n", "\n").split("\n")
        d = difflib.unified_diff(L, S, "live", "staged", lineterm="", n=0)
        outp = os.path.join(HERE, "diff_" + rel.replace("/", "__") + ".txt")
        with open(outp, "w", encoding="utf-8", newline="\n") as f:
            for x in d:
                f.write(x + "\n")
        print("  wrote", outp)
