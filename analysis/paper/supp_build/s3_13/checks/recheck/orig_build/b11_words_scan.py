"""Small word scans of the new visible text: 'owner' (S1 and S4 say 'the author', ruling AT20), 'we'/'our'
in S1/S4, 'fire'/'defo'/'pm25'/'ndvi'/'coral' code names outside code spans, bare 'coral' before 'coral bleaching'
in a part, 'post hoc' labels near numbers in 5.4. Read-only. Run: py -3.9 -I -B b11_words_scan.py
"""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from b04_lib import PAIRS, STAGE, read_bytes, text_of, blank_comments, blank_code, line_at, new_spans, in_spans, ctx

live = dict(PAIRS)
for rel, pats in (("paper/draft/S1_disclosures.md", [r"\b[Oo]wner'?s?\b", r"\b(?:we|our|us)\b"]),
                  ("paper/draft/S4_provenance.md", [r"\b[Oo]wner'?s?\b", r"\b(?:we|our|us)\b"]),
                  ("paper/draft/S3_posthoc.md", [r"\b[Oo]wner'?s?\b", r"\b(?:fire|defo|pm25|ndvi)\b"]),
                  ("paper/draft/05_rivals.md", [r"\b[Oo]wner'?s?\b", r"\b(?:fire|defo|pm25|ndvi)\b"]),
                  ("paper/draft/tables/table_9.md", [r"\b[Oo]wner'?s?\b", r"\b(?:fire|defo|pm25|ndvi)\b"])):
    st = text_of(read_bytes(STAGE / rel))
    lp = live.get(rel)
    lt = text_of(read_bytes(lp)) if lp is not None else ""
    vs, vl = blank_code(blank_comments(st)), blank_code(blank_comments(lt))
    spans, _ = new_spans(vl, vs)
    for p in pats:
        for m in re.finditer(p, vs):
            if in_spans(m.start(), m.end(), spans):
                print("%s L%d '%s': %s" % (rel, line_at(vs, m.start()), m.group(0), ctx(vs, m.start(), m.end(), 60)[:220]))
