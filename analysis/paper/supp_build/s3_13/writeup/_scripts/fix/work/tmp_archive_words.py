import re, sys
sys.path.insert(0, r'.')
from fix_lib import STAGE, visible
for rel in ['paper/draft/S3_posthoc.md', 'paper/draft/S1_disclosures.md']:
    t = visible((STAGE / rel).read_text(encoding='utf-8'))
    for m in re.finditer(r'[^.\n]{0,160}\barchiv\w*[^.\n]{0,160}', t):
        print(rel, '|', m.group(0).strip()[:330])
