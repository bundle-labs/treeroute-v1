"""Word counts of the new parts with the build's count_words rule (copied from build_docx.py): S3.13 as a whole
and split into prose paragraphs, table captions, table rows and notes; the S3.0 row; Section 5.4's new paragraph;
the new S1 rows and the new S4 text (by token diff, approximately). Read-only. Run: py -3.9 -I -B b10_words.py
"""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from b04_lib import STAGE, ROOT, read_bytes, text_of, new_spans


def clean_visible(raw):
    DROP = "\x00"
    t = re.sub(r"<!--.*?-->", DROP, raw, flags=re.S)
    out = []
    for ln in t.split("\n"):
        if DROP in ln and ln.replace(DROP, "").strip() == "":
            continue
        out.append(ln.replace(DROP, "").rstrip())
    txt = "\n".join(out)
    txt = re.sub(r"(?<=\S)\n(?=[ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ†‡§] )", "\n\n", txt)
    return re.sub(r"\n{3,}", "\n\n", txt).strip("\n") + "\n"


def count_words(md):
    t = re.sub(r"^\s*\|?\s*:?-{3,}.*$", " ", md, flags=re.M)
    t = re.sub(r"^:::.*$", " ", t, flags=re.M)
    t = t.replace("|", " ")
    t = re.sub(r"^#{1,6}\s+", "", t, flags=re.M)
    t = re.sub(r"\$\$.*?\$\$", " MATH ", t, flags=re.S)
    t = re.sub(r"\$[^$\n]+\$", " MATH ", t)
    return sum(1 for w in t.split() if re.search(r"[0-9A-Za-zÀ-ÿͰ-Ͽ]", w))


def main():
    s3 = clean_visible(text_of(read_bytes(STAGE / "paper/draft/S3_posthoc.md")))
    a = s3.index("## S3.13 ")
    part = s3[a:]
    blocks = [b for b in re.split(r"\n\s*\n", part) if b.strip()]
    kinds = {"prose": 0, "caption": 0, "table": 0, "note/panel": 0}
    for b in blocks:
        n = count_words(b)
        s = b.lstrip()
        if s.startswith("**Table"):
            kinds["caption"] += n
        elif s.startswith("|"):
            kinds["table"] += n
        elif re.match(r"^(?:[ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ†‡§]|\*\*[a-z]\. )", s):
            kinds["note/panel"] += n
        elif s.startswith("**") or s.startswith("##") or s[0].isalpha() or s[0] in "`(":
            # prose paragraphs; table notes without a marker (lines after a note) also land here
            kinds["prose"] += n
        else:
            kinds["prose"] += n
    print("S3.13 total words:", count_words(part), kinds)
    row = [ln for ln in s3.split("\n") if ln.startswith("| S3.13 |")]
    print("S3.0 row words:", count_words(row[0]) if row else None)
    live_s3 = clean_visible(text_of(read_bytes(ROOT / "paper/draft/S3_posthoc.md")))
    print("S3 visible words: live %d, staged %d (difference %d)" % (count_words(live_s3), count_words(s3),
                                                                  count_words(s3) - count_words(live_s3)))
    r5 = clean_visible(text_of(read_bytes(STAGE / "paper/draft/05_rivals.md")))
    para = [b for b in re.split(r"\n\s*\n", r5) if b.startswith("Table 9 compares")]
    print("5.4 new paragraph words:", count_words(para[0]) if para else None)
    for rel in ("paper/draft/S1_disclosures.md", "paper/draft/S4_provenance.md"):
        lv = clean_visible(text_of(read_bytes(ROOT / rel)))
        sv = clean_visible(text_of(read_bytes(STAGE / rel)))
        print(rel, "visible words: live %d, staged %d (difference %d)" % (count_words(lv), count_words(sv),
                                                                         count_words(sv) - count_words(lv)))


if __name__ == "__main__":
    main()
