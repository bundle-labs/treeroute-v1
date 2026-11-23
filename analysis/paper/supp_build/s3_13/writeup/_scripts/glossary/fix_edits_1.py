"""Fix 1 to the glossary writer's staged edits (STAGED copies only).

Usage: py -3.9 -I -B fix_edits_1.py <STAGE root>
(a) GLOSSARY.md, family row: the other names drop the results.json family keys
    (own_history is a label of Supplement S6's tables, so listing it as a
    do-not-use name would flag S6), and give families.parquet and own_history_share.
(b) PAPER_FACTS.md, status-key line for Part 628: the protocol's D:/ path leaves the
    visible text (the write-up's rule: no absolute local path in visible text).
Each old text must occur exactly once; encoding and line endings are kept.
"""
import os
import sys

FIXES = [
    (os.path.join("paper", "draft", "GLOSSARY.md"),
     "| own_history, global_indices, local_drivers, context_and_calendar, seasonal_normal (results.json keys) |",
     "| families.parquet, own_history_share (code) |"),
    (os.path.join("paper", "PAPER_FACTS.md"),
     "by the post hoc SHAP analysis of Part 628 (protocol D:/treeroute/analysis/shap_v1/PROTOCOL.md; rulings AW, AY, AZ1, "
     "BA and BB), from its output files and run records.",
     "by the post hoc SHAP analysis of Part 628 (rulings AW, AY, AZ1, BA and BB), from its output files and run records."),
]


def main():
    stage = sys.argv[1]
    for rel, old, new in FIXES:
        path = os.path.join(stage, rel)
        with open(path, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8")
        n = text.count(old)
        if n != 1:
            raise SystemExit("%s: old text count %d" % (rel, n))
        text = text.replace(old, new, 1)
        with open(path, "wb") as f:
            f.write(text.encode("utf-8"))
        print("fixed:", rel)


if __name__ == "__main__":
    main()
