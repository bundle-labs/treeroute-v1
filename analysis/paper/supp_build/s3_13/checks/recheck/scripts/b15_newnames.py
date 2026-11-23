"""The do-not-use names of the NEW glossary rows (staged GLOSSARY.md rows absent from the live one), searched in the
visible prose (comments and code spans blanked) of every file the build reads, staged copies in place of live ones
(the copy/ folder of this check). Lead's rule: whole word, case-insensitive. Read-only.
Run: py -3.9 -I -B b15_newnames.py
"""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from b04_lib import CHK, ROOT, STAGE, read_bytes, text_of, blank_comments, blank_code, line_at, ctx, glossary_names

new = set(glossary_names(STAGE / "paper/draft/GLOSSARY.md")) - set(glossary_names(ROOT / "paper/draft/GLOSSARY.md"))
print("new do-not-use names:", len(new))
base = CHK / "copy" / "paper"
files = sorted(list((base / "draft").glob("*.md")) + list((base / "draft" / "tables").glob("*.md"))
               + list((base / "draft" / "submission").glob("*.md")) + list((base / "figures").rglob("*_caption.md")))
hits = 0
for p in files:
    if p.name == "GLOSSARY.md":
        continue
    t = blank_code(blank_comments(text_of(p.read_bytes())))
    for n, term in sorted(new):
        for m in re.finditer(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", t, re.I):
            hits += 1
            print("%s L%d %r (%s): %s" % (p.relative_to(base).as_posix(), line_at(t, m.start()), n, term, ctx(t, m.start(), m.end(), 50)[:200]))
print("hits:", hits)
