import re, sys
sys.stdout.reconfigure(encoding='ascii', errors='replace')
sys.path.insert(0, r'.')
from fix_lib import STAGE, D, visible
from pathlib import Path
files = sorted(p for p in D.glob('*.md')) + sorted(D.glob('tables/*.md'))
staged = {p.name: STAGE / 'paper' / 'draft' / p.name for p in D.glob('*.md')}
cnt = {}
for p in files:
    src = p
    sp = STAGE / 'paper' / 'draft' / p.relative_to(D)
    if sp.exists():
        src = sp
    t = visible(src.read_text(encoding='utf-8', errors='replace'))
    hits = [m.group(0) for m in re.finditer(r'.{0,60}\b[Oo]wner\b.{0,60}', t)]
    if hits:
        cnt[str(p.relative_to(D))] = (len(hits), hits[:2])
for k, v in cnt.items():
    print(k, v[0], '|', ' || '.join(h.replace('\n', ' ') for h in v[1]))

