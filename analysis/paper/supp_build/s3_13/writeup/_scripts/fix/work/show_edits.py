import sys, difflib, json
sys.path.insert(0, r'..')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from fix_lib import STAGE, WORK
ap = json.loads((WORK / 'applied_edits.json').read_text(encoding='utf-8'))
for rel in [r for r in ap['edits'] if r in sys.argv[1:]]:
    for eid, old, new in ap['edits'][rel]:
        sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
        out = []
        for op, a1, a2, b1, b2 in sm.get_opcodes():
            if op == 'equal':
                s = old[a1:a2]
                out.append(s if len(s) < 80 else s[:35] + ' ... ' + s[-35:])
            elif op == 'delete':
                out.append('[-' + old[a1:a2] + '-]')
            elif op == 'insert':
                out.append('{+' + new[b1:b2] + '+}')
            else:
                out.append('[-' + old[a1:a2] + '-]{+' + new[b1:b2] + '+}')
        print('==', eid); print(''.join(out)); print()

