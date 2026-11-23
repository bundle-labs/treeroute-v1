"""Check that every number in S3.13's prose is in a fact that the following comment cites (writer s3; read only).

Usage: py -3.9 -I -B check_numbers.py
Splits S3.13's text (outside its 13 table blocks) at its HTML comments; for each piece, collects the number tokens of
its visible text (decimals, integers with thousands commas, percentages, powers of ten and the number words two to
ten) and the fact IDs (A9-A25) of the comment that ends it, and checks that each token occurs in the text of one of
those facts in the staged PAPER_FACTS.md. Names, dates, rulings, gates, sections, tables and Parts are skipped. Also
checks that each date of the visible text is in A9 or A25. Writes nothing.
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("s3lib", os.path.join(HERE, "s3lib.py"))
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)
spec2 = importlib.util.spec_from_file_location("build_s3", os.path.join(HERE, "build_s3.py"))
B = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(B)

WORDS = ["two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
SKIP_RE = re.compile(
    r"(Sections?|Tables?|Supplements?|Part|Parts|lead|version|ruling|rulings|decision|gate|gates)\s+[\w.()\-–]+"
    r"|\b(?:AW|AY|AZ|BA|BB|AT|AG|AK|AS|AB|AV|O|D|E|S)\d+[a-z]?\b(?:\s*\([a-z]\))?|\bS3\.\d+\b|\bS1\.\d+\b"
    r"|\bB[12]\b|\bv[123]\b|PM2\.5|S-[A-Z]+|top-\d+|top \d+|`[^`]*`|\$[^$]*\$|\bI_m\(j\)"
    r"|\d{4}-\d{2}-\d{2}|\b\d{2}:\d{2}\b|\bp = 0\.9(?:5)?\b|0\.95|95%|verify_v1/A/results\.json|\bA\b|\bB\b")


def facts_text():
    with open(os.path.join(L.STAGE, "paper", "PAPER_FACTS.md"), encoding="utf-8") as f:
        t = f.read()
    out = {}
    for m in re.finditer(r"^- \*\*(A\d+) \(final, post hoc \(Part 628\)\)\..*$", t, flags=re.M):
        out[m.group(1)] = m.group(0)
    return out


def norm(s):
    return s.replace("−", "-")


def main():
    facts = facts_text()
    print("facts found:", sorted(facts, key=lambda k: int(k[1:])))
    with open(B.DST, encoding="utf-8") as f:
        staged = f.read()
    sec = staged[staged.index("## S3.13 "):staged.index("<!-- Cross-check pass")]
    blocks, _ = B.table_blocks()
    for name in B.ORDER:
        blk = blocks[name].replace(B.S321_OLD, B.S321_NEW)
        sec = sec.replace(blk, "\n@@T@@\n")
    pieces = re.split(r"(<!--.*?-->)", sec, flags=re.S)
    problems = 0
    checked = 0
    for k in range(0, len(pieces) - 1, 2):
        text, com = pieces[k], pieces[k + 1]
        ids = re.findall(r"\bA(?:9|1\d|2[0-5])\b", com)
        vis = SKIP_RE.sub(" ", text)
        pat = r"\d+(?:,\d{3})*(?:\.\d+)?%?|10⁻\S+|\b(?:" + "|".join(WORDS) + r")\b"
        toks = re.findall(pat, vis, flags=re.I)
        ftxt = norm(" ".join(facts.get(i, "") for i in ids)).lower()
        for tkn in toks:
            checked += 1
            tl = norm(tkn).lower()
            ok = tl in ftxt or (tl.startswith("10⁻") and tl.replace("10⁻¹²", "1e-12").replace("10⁻⁹", "1e-9")
                                  .rstrip(".,;)") in ftxt)
            if tl in WORDS:
                num = str(WORDS.index(tl) + 2)
                ok = ok or re.search(r"\b%s\b" % num, ftxt) is not None
            if not ok:
                problems += 1
                print("NOT IN CITED FACTS %s: %r in ...%s..." % (ids, tkn, text.strip()[-160:].replace("\n", " ")))
    dates = set(re.findall(r"\d{4}-\d{2}-\d{2}", re.sub(r"<!--.*?-->", " ", sec, flags=re.S)))
    for d in sorted(dates):
        if d not in facts["A9"] and d not in facts["A25"]:
            print("date not in A9 or A25:", d)
            problems += 1
    print("number tokens checked: %d; problems: %d; dates: %s" % (checked, problems, sorted(dates)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
