"""Resolve the author-year citations of the staged S3_posthoc.md against the staged REFERENCES.md (writer s3; read only).

Usage: py -3.9 -I -B check_cites.py
Loads the references writer's copy of the build's entry parser and citation scanner
(STAGE/_scripts/refs/check_entries.py; functions only, its main() is not run), parses section A of the staged
REFERENCES.md, checks that the build's sort key puts the five new entries where they stand, and scans the visible
text (HTML comments removed) of S3.13 and of the whole staged S3_posthoc.md. Writes nothing.
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.abspath(os.path.join(HERE, "..", ".."))
spec = importlib.util.spec_from_file_location("check_entries", os.path.join(STAGE, "_scripts", "refs", "check_entries.py"))
CE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CE)
NEW = ["Janzing2020_interventional", "KendallBabingtonSmith1939_W", "LundbergLee2017_SHAP", "Lundberg2020_TreeSHAP",
       "Webber2010_RBO"]


def main():
    with open(os.path.join(STAGE, "paper", "draft", "REFERENCES.md"), encoding="utf-8") as f:
        ref = f.read()
    with open(os.path.join(STAGE, "paper", "draft", "S3_posthoc.md"), encoding="utf-8") as f:
        s3 = f.read()
    ents = CE.parse_references(ref)
    a = [e for e in ents if e["section"] == "A"]
    print("section A entries:", len(a), "A2:", len(ents) - len(a))
    keys = [e["key"] for e in a]
    for k in NEW:
        print(k, "present", keys.count(k))
    srt = sorted(a, key=CE.sort_key)
    pos = {e["key"]: i for i, e in enumerate(srt)}
    for k in NEW:
        i = pos[k]
        print("%-28s sorts between %s and %s" % (k, srt[i - 1]["key"], srt[i + 1]["key"]))
    # file order equals sort order around the new entries
    file_order = [e["key"] for e in a]
    for k in NEW:
        i = file_order.index(k)
        print("%-28s stands between %s and %s" % (k, file_order[i - 1], file_order[i + 1]))
    index, labels = CE.build_index(ents)
    vis = re.sub(r"<!--.*?-->", " ", s3, flags=re.S)
    sec = vis[vis.index("## S3.13 "):]
    print("--- S3.13 visible text:")
    for r in CE.scan(sec, index, labels):
        print("  ", r)
    print("--- whole file, unresolved or ambiguous only:")
    bad = [r for r in CE.scan(vis, index, labels) if r.startswith(("UNRESOLVED", "AMBIGUOUS", "BUILD ERROR"))]
    print("  ", bad if bad else "none")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
