# Print the inserted or changed lines of one staged file against its base copy, with their staged line numbers.
# Usage: show_inserts.py <rel path, e.g. engine/PENDING_PARTS.md>
import os, sys, difflib

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.normpath(os.path.join(HERE, '..', '..'))
rel = sys.argv[1]
with open(os.path.join(HERE, 'work', 'base', rel.replace('/', '__')), encoding='utf-8', newline='') as f:
    a = f.read().split('\n')
with open(os.path.join(STAGE, *rel.split('/')), encoding='utf-8', newline='') as f:
    b = f.read().split('\n')
sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op == 'equal':
        continue
    print('--- %s base %d-%d -> staged %d-%d' % (op, i1 + 1, i2, j1 + 1, j2))
    for k in range(j1, j2):
        print('%5d: %s' % (k + 1, b[k]))
