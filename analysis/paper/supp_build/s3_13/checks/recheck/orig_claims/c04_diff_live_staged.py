"""Unified line diffs of every staged file against its live file (read only), written to this folder.

Live paths: ROOT-relative for the paper and engine files; SHAP/PROTOCOL.md for STAGE/shap/PROTOCOL.md;
ROOT/_archive_plan for the manifest. A staged file with no live file (table_9.md) is listed as new.
Output: one diff file per staged file in work/, and a summary on screen (lines added, removed).
"""
import difflib
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(os.path.dirname(HERE))  # .../supp_build/s3_13
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))  # research-paper folder
STAGE = os.path.join(OUT, "stage")
SHAP = r"D:\treeroute\analysis\shap_v1"

PAIRS = [
    ("paper/draft/S3_posthoc.md", os.path.join(ROOT, "paper", "draft", "S3_posthoc.md")),
    ("paper/draft/05_rivals.md", os.path.join(ROOT, "paper", "draft", "05_rivals.md")),
    ("paper/draft/tables/table_9.md", os.path.join(ROOT, "paper", "draft", "tables", "table_9.md")),
    ("paper/draft/TABLE_NUMBERS.md", os.path.join(ROOT, "paper", "draft", "TABLE_NUMBERS.md")),
    ("paper/draft/S1_disclosures.md", os.path.join(ROOT, "paper", "draft", "S1_disclosures.md")),
    ("paper/draft/S4_provenance.md", os.path.join(ROOT, "paper", "draft", "S4_provenance.md")),
    ("paper/draft/GLOSSARY.md", os.path.join(ROOT, "paper", "draft", "GLOSSARY.md")),
    ("paper/draft/REFERENCES.md", os.path.join(ROOT, "paper", "draft", "REFERENCES.md")),
    ("paper/PAPER_FACTS.md", os.path.join(ROOT, "paper", "PAPER_FACTS.md")),
    ("paper/PAPER_OUTLINE.md", os.path.join(ROOT, "paper", "PAPER_OUTLINE.md")),
    ("engine/PENDING_PARTS.md", os.path.join(ROOT, "engine", "PENDING_PARTS.md")),
    ("_archive_plan/ARCHIVE_MANIFEST_DRAFT.md", os.path.join(ROOT, "_archive_plan", "ARCHIVE_MANIFEST_DRAFT.md")),
    ("shap/PROTOCOL.md", os.path.join(SHAP, "PROTOCOL.md")),
]


def read_lines(path):
    with open(path, "rb") as fh:
        data = fh.read()
    return data, data.decode("utf-8").splitlines()


def main():
    work = os.path.join(HERE, "work")
    os.makedirs(work, exist_ok=True)
    for rel, live in PAIRS:
        staged = os.path.join(STAGE, *rel.split("/"))
        sdata, slines = read_lines(staged)
        sh = hashlib.sha256(sdata).hexdigest()
        if not os.path.exists(live):
            print("%-45s NEW (no live file); staged sha256 %s, %d lines" % (rel, sh[:12], len(slines)))
            continue
        ldata, llines = read_lines(live)
        lh = hashlib.sha256(ldata).hexdigest()
        diff = list(difflib.unified_diff(llines, slines, "live/" + rel, "staged/" + rel, n=0, lineterm=""))
        add = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
        rem = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
        name = rel.replace("/", "__") + ".diff.txt"
        with open(os.path.join(work, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(diff) + "\n")
        print("%-45s live %s staged %s  +%d -%d" % (rel, lh[:12], sh[:12], add, rem))
    return 0


if __name__ == "__main__":
    sys.exit(main())
