# peek_fire_w.py - read-only: prints only the raw JSON text of the kendall_w entry of burned fraction's
# AW4_main_row.json (to check whether the stored value is NaN or null, for fact A16), and the cells.json entries of
# Table S3.22's W row (stored values as cells.json writes them). Nothing else of either file is printed.
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fix_lib import SHAP, OUT

p = SHAP / 'out' / 'fire' / 'lead_0' / 'compare' / 'AW4_main_row.json'
t = p.read_text(encoding='utf-8')
i = t.find('"kendall_w"')
j = t.find('}', i)
print('AW4_main_row.json (fire):', re.sub(r'\s+', ' ', t[i:j + 1]))
cells = json.loads((OUT / 'reconcile' / 'cells.json').read_text(encoding='utf-8'))
n = 0
items = cells if isinstance(cells, list) else cells.get('cells', cells)
if isinstance(items, dict):
    items = list(items.values())
for c in items:
    s = json.dumps(c, ensure_ascii=True)
    if 'kendall_w' in s and 'fire' in s and ('S3.22' in s or '"9"' in s or 'table": 9' in s):
        print('cells.json:', s[:400])
        n += 1
        if n >= 4:
            break
