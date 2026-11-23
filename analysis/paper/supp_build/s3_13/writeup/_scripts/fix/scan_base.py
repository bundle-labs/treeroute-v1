# scan_base.py - count-only privacy scan (patterns of privacy_two.py) of this fixer's byte copies in work/base/,
# to decide which copies may be kept (a copy that holds a pre-existing name or id is not kept). Counts only.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import privacy_two as P
from fix_lib import BASE

for p in sorted(BASE.iterdir()):
    t = P.decode(p.read_bytes())
    hits = [k for k, rx in P.PATS.items() if rx.search(t)]
    print(p.name, 'hits:', len(hits), ('(' + ', '.join(hits) + ')') if hits else '')
