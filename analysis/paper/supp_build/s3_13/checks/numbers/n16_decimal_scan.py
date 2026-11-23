# n16: every decimal number of the added lines of each staged file (comments included), with three or more decimals or a
# percent, listed for a re-rounding review; and every two-decimal number checked against the set of values that
# cells.json prints (so a prose two-decimal value must be a table value or come from a fact's stored double).
import difflib
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
OUT = os.path.join(ROOT, r"paper\supp_build\s3_13")
ST = os.path.join(OUT, "stage")
S = r"D:\treeroute\analysis\shap_v1"
PAIRS = [
    (r"paper\draft\S3_posthoc.md", os.path.join(ROOT, r"paper\draft\S3_posthoc.md")),
    (r"paper\draft\05_rivals.md", os.path.join(ROOT, r"paper\draft\05_rivals.md")),
    (r"paper\draft\S1_disclosures.md", os.path.join(ROOT, r"paper\draft\S1_disclosures.md")),
    (r"paper\draft\S4_provenance.md", os.path.join(ROOT, r"paper\draft\S4_provenance.md")),
    (r"paper\draft\GLOSSARY.md", os.path.join(ROOT, r"paper\draft\GLOSSARY.md")),
    (r"paper\PAPER_FACTS.md", os.path.join(ROOT, r"paper\PAPER_FACTS.md")),
    (r"paper\PAPER_OUTLINE.md", os.path.join(ROOT, r"paper\PAPER_OUTLINE.md")),
    (r"engine\PENDING_PARTS.md", os.path.join(ROOT, r"engine\PENDING_PARTS.md")),
    (r"_archive_plan\ARCHIVE_MANIFEST_DRAFT.md", os.path.join(ROOT, r"_archive_plan\ARCHIVE_MANIFEST_DRAFT.md")),
    (r"shap\PROTOCOL.md", os.path.join(S, "PROTOCOL.md")),
]
cells = json.loads(open(os.path.join(OUT, r"reconcile\cells.json"), "rb").read().decode("utf-8"))["entries"]
printed = set(e["printed"].replace("\u2212", "-") for e in cells)
agreed = open(os.path.join(OUT, r"reconcile\tables_agreed.md"), "rb").read().decode("utf-8")
for rel, live in PAIRS:
    s = open(os.path.join(ST, rel), "rb").read().decode("utf-8").replace("\r\n", "\n").split("\n")
    l = open(live, "rb").read().decode("utf-8").replace("\r\n", "\n").split("\n")
    sm = difflib.SequenceMatcher(None, l, s, autojunk=False)
    add = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("insert", "replace"):
            add += s[j1:j2]
    # remove lines that are table-block lines copied from tables_agreed (S3 only)
    if rel.endswith("S3_posthoc.md"):
        add = [x for x in add if x not in agreed.split("\n")]
    txt = "\n".join(add)
    long_dec = sorted(set(re.findall(r"(?<![\w.])[\u2212-]?\d+\.\d{3,}(?:e-?\d+)?\b", txt)))
    two_dec = sorted(set(re.findall(r"(?<![\w.\d])[\u2212-]?\d+\.\d{2}(?![\d\w])", txt)))
    pct = sorted(set(re.findall(r"(?<![\w.\d])\d+\.\d%", txt)))
    not_printed = [x for x in two_dec if x.replace("\u2212", "-") not in printed]
    pct_np = [x for x in pct if x not in printed]
    print("== %s: added lines %d" % (rel, len(add)))
    print("   3+ decimals (excluding 'stored' doubles shown below):", [x for x in long_dec if len(x.split(".")[1].split("e")[0]) <= 5][:40])
    print("   two-decimal values not printed by any table cell:", not_printed[:60])
    print("   one-decimal percents not printed by any table cell:", pct_np[:40])
