# r15 (version 2): the one line that r03's completeness check flags, tables.md line 344 (the S3.24 double-dagger
# note). r03 compares a data note's number tokens with the printed tokens of that line's cells.json entries, but
# this note's fixed text holds numbers of its own (top 5, 10 and 20, RBO p = 0.9 and 0.95, "exactly 0"), which r03
# does not remove. Here the fixed text's tokens are taken with r03's token regex from the spec's note template
# (backticked names removed, each placeholder replaced by X): line 344's tokens must be exactly those plus the
# printed tokens of its entries, in version 2 (TABLE_SPEC.md, OUT\A\tables.md, OUT\A\cells.json) and in version 1
# (TABLE_SPEC_v1.md, OUT\reconcile\tables_agreed_v1.md, OUT\A\cells_v1.json). Read-only; prints.
# Version 3 (2026-11-17): TABLE_SPEC.md, OUT\A\tables.md and OUT\A\cells.json now hold version 3, so the two
# versions compared are version 3 (those files) and version 2 (TABLE_SPEC_v2.md, OUT\reconcile\tables_agreed_v2.md,
# OUT\reconcile\cells_v2.json); nothing else changed. Version 2 is kept as scripts\v2\r15_note344_tokens.py.
import sys, re, json, collections
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2]
TOKRE = re.compile(r"(?<![\w.,−-])(<0\.1%|undefined|−?\d[\d,]*\.\d × 10[⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+|−?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|−?\d+(?:\.\d+)?%?)(?![\w.,]\d|\d)")


def template(spec_path):
    L = spec_path.read_text(encoding="utf-8").split("\n")
    hits = [L[i + 1] for i in range(len(L) - 2) if L[i].startswith("```") and L[i + 1].startswith("‡ BARDL reads three variables") and L[i + 2].startswith("```")]
    if len(hits) != 1:
        raise SystemExit("stop: the note template in " + spec_path.name)
    return hits[0]


res = []
for ver, spec, tables, cells in (("version 3", OUT / "spec" / "TABLE_SPEC.md", OUT / "A" / "tables.md", OUT / "A" / "cells.json"),
                                 ("version 2", OUT / "spec" / "TABLE_SPEC_v2.md", OUT / "reconcile" / "tables_agreed_v2.md", OUT / "reconcile" / "cells_v2.json")):
    tm = template(spec)
    const = collections.Counter(TOKRE.findall(re.sub(r"\{[a-z0-9_]+\}", "X", re.sub(r"`[^`]*`", "", tm))))
    line = tables.read_text(encoding="utf-8").split("\n")[343]
    if not line.startswith("‡ BARDL reads"):
        raise SystemExit("stop: line 344 of " + tables.name)
    got = collections.Counter(TOKRE.findall(re.sub(r"`[^`]*`", "", line)))
    ents = [e["printed"] for e in json.loads(cells.read_text(encoding="utf-8"))["entries"] if e["line"] == 344]
    want = const + collections.Counter(ents)
    res.append((sorted(const.elements()), sorted(ents)))
    print(ver, "- template's own tokens:", sorted(const.elements()), "; entries on line 344:", len(ents),
          "; line tokens == template tokens + entries' printed tokens:", got == want)
print("the template's own tokens are the same in both versions:", res[0][0] == res[1][0],
      "; the entries' printed tokens are the same:", res[0][1] == res[1][1])
