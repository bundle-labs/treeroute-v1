import sys, re
sys.path.insert(0, r'.')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from fix_lib import STAGE, visible
t = (STAGE / 'paper/draft/S3_posthoc.md').read_text(encoding='utf-8').split('\n')
for i in (667, 669, 1336, 1460):
    print('S3 line', i + 1, ':', re.sub(r'\s+', ' ', visible(t[i]))[:3000]); print()
u = (STAGE / 'paper/draft/S1_disclosures.md').read_text(encoding='utf-8').split('\n')
for i in (244, 245, 248, 251):
    print('S1 line', i + 1, ':', re.sub(r'\s+', ' ', visible(u[i]))[:2600]); print()
