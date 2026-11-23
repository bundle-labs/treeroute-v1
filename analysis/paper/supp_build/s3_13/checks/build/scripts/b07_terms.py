"""Glossary scan of the NEW visible text of the staged paper files (comments and code spans blanked; token diff
against the live file). Names: column 2 of the staged GLOSSARY.md (the live rows and the new ones), split at commas,
whole word, case-insensitive (the lead's rule); a second pass also allows a plural 's'. Each hit is printed with its
context, for judgement. Read-only. Run: py -3.9 -I -B b07_terms.py [file-substring]
"""
import re
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from b04_lib import (PAIRS, STAGE, read_bytes, text_of, blank_comments, blank_code, line_at, new_spans, in_spans, ctx,
                     glossary_names)

FILES = ["paper/draft/S3_posthoc.md", "paper/draft/05_rivals.md", "paper/draft/tables/table_9.md",
         "paper/draft/S1_disclosures.md", "paper/draft/S4_provenance.md", "paper/draft/GLOSSARY.md",
         "paper/draft/TABLE_NUMBERS.md"]


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    names = glossary_names(STAGE / "paper/draft/GLOSSARY.md")
    live = dict(PAIRS)
    for rel in FILES:
        if only and only not in rel:
            continue
        st = text_of(read_bytes(STAGE / rel))
        lp = live.get(rel)
        lt = text_of(read_bytes(lp)) if lp is not None else ""
        vs, vl = blank_code(blank_comments(st)), blank_code(blank_comments(lt))
        spans, _ = new_spans(vl, vs)
        print("=" * 100)
        print(rel, "new visible characters:", sum(e - s for s, e in spans))
        hits = defaultdict(list)
        for n, term in names:
            for plural in (False, True):
                pat = re.compile(r"(?<![\w-])" + re.escape(n) + (r"s?" if plural else "") + r"(?![\w-])", re.I)
                for m in pat.finditer(vs):
                    if not in_spans(m.start(), m.end(), spans):
                        continue
                    if plural and m.group(0).lower() == n.lower():
                        continue    # counted in the exact pass
                    hits[(n + ("(s)" if plural else ""), term)].append((line_at(vs, m.start()), ctx(vs, m.start(), m.end(), 55)))
        for (n, term), hs in sorted(hits.items(), key=lambda kv: (-len(kv[1]), kv[0][0])):
            print("-- %r (paper term: %s): %d" % (n, term, len(hs)))
            seen = set()
            for ln, c in hs:
                if c in seen:
                    continue
                seen.add(c)
                print("     L%d: %s" % (ln, c[:200]))


if __name__ == "__main__":
    main()
