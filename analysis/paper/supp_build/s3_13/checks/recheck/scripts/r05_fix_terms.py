"""Recheck (2026-11-17): the build checker's glossary rule (b07: column 2 of the staged GLOSSARY.md, whole word,
case-insensitive, plus a plural 's') applied to the text the FIX PASS added: the token diff of each edited paper file
from its pre-fix state (rebuilt in memory by undoing STAGE/_scripts/fix/work/applied_edits.json) to the staged file.
Comments and code spans blanked. Also the build's AI expressions over the same new text, and, for the visible text of
the whole staged S3.13, S1 rows PH22-PH30 and GLOSSARY rows, the names the checks flagged before the fix (B3, B4, B5).
Read-only. Run: py -3.9 -I -B r05_fix_terms.py
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from b04_lib import (STAGE, text_of, read_bytes, blank_comments, blank_code, line_at, new_spans, in_spans, ctx,
                     glossary_names, AI_STRONG, AI_WEAK, AI_SOFT)

FIXW = STAGE / "_scripts" / "fix" / "work"
ap = json.loads((FIXW / "applied_edits.json").read_text(encoding="utf-8"))
names = glossary_names(STAGE / "paper/draft/GLOSSARY.md")
for rel, edits in ap["edits"].items():
    if not rel.startswith("paper/draft/"):
        continue
    post = (STAGE / rel).read_bytes().decode("utf-8")
    pre = post
    for eid, old, new in reversed(edits):
        assert pre.count(new) == 1, (rel, eid)
        pre = pre.replace(new, old)
    vs = blank_code(blank_comments(text_of(post.encode("utf-8"))))
    vp = blank_code(blank_comments(text_of(pre.encode("utf-8"))))
    spans, _ = new_spans(vp, vs)
    print("=" * 90)
    print(rel, "| visible characters added by the fix:", sum(e - s for s, e in spans))
    for s, e in spans:
        print("   NEW L%d: %s" % (line_at(vs, s), ctx(vs, s, e, 0)[:400]))
    hits = defaultdict(list)
    for n, term in names:
        for plural in (False, True):
            pat = re.compile(r"(?<![\w-])" + re.escape(n) + (r"s?" if plural else "") + r"(?![\w-])", re.I)
            for m in pat.finditer(vs):
                if not in_spans(m.start(), m.end(), spans):
                    continue
                if plural and m.group(0).lower() == n.lower():
                    continue
                hits[(n, term)].append((line_at(vs, m.start()), ctx(vs, m.start(), m.end(), 55)))
    for (n, term), hs in sorted(hits.items()):
        for ln, c in hs:
            print("   TERM %r (paper term: %s) L%d: %s" % (n, term, ln, c[:200]))
    for label, rx in (("AI_STRONG", AI_STRONG), ("AI_WEAK", AI_WEAK), ("soft", AI_SOFT)):
        for m in rx.finditer(vs):
            if in_spans(m.start(), m.end(), spans):
                print("   %s L%d '%s': %s" % (label, line_at(vs, m.start()), m.group(0), ctx(vs, m.start(), m.end(), 60)[:200]))

# the names flagged before the fix, over the whole visible text of the parts concerned
print("=" * 90)
s3 = blank_code(blank_comments(text_of(read_bytes(STAGE / "paper/draft/S3_posthoc.md"))))
a = s3.index("## S3.13 ")
b = s3.find("\n## ", a + 5)
sec = s3[a:b if b > 0 else len(s3)]
s1 = blank_code(blank_comments(text_of(read_bytes(STAGE / "paper/draft/S1_disclosures.md"))))
ph = "\n".join(l for l in s1.split("\n") if re.match(r"^\| PH(2[2-9]|30) \|", l))
gl = blank_code(blank_comments(text_of(read_bytes(STAGE / "paper/draft/GLOSSARY.md"))))
for label, txt in (("S3.13 visible", sec), ("S1 PH22-PH30 visible", ph), ("GLOSSARY visible", gl)):
    for pat in (r"\bheadline runs?\b", r"\bboards?\b", r"\bcatalog\b", r"\bsample rows?\b", r"\bcoral bleaching rows?\b",
                r"\b250 coral bleaching\b[^.;)]{0,20}", r"\bthe owner\b", r"\bvisits?\b"):
        for m in re.finditer(pat, txt, re.I):
            pre_ctx = txt[max(0, m.start() - 25):m.start()]
            if pat == r"\bvisits?\b" and re.search(r"survey\s*$", pre_ctx):
                continue
            if pat == r"\bboards?\b" and re.search(r"rival\s*$", pre_ctx):
                continue
            print("%s: %-28s %s" % (label, pat, ctx(txt, m.start(), m.end(), 60)[:220]))
