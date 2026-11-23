# Count-only privacy check of this writer's own outputs: STAGE/changes_records.md and STAGE/_scripts/records/
# (without work/base/, which holds byte copies of the live files). Prints file names with a hit and the pattern
# label only, never the matched text.
import os, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.normpath(os.path.join(HERE, '..', '..'))
spec = importlib.util.spec_from_file_location('pc', os.path.join(HERE, 'privacy_count_out.py'))
pc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pc)

targets = [os.path.join(STAGE, 'changes_records.md')]
for dp, dn, fn in os.walk(HERE):
    if os.path.normcase(os.path.join(HERE, 'work', 'base')) in os.path.normcase(dp):
        continue
    for f in fn:
        targets.append(os.path.join(dp, f))
n_hit = 0
for p in targets:
    with open(p, 'rb') as fh:
        t, e = pc.decode(fh.read())
    hits = [k for k, rx in pc.PATS.items() if rx.search(t)]
    if hits:
        n_hit += 1
        print(os.path.relpath(p, STAGE), hits)
print('files checked', len(targets), 'files with a hit', n_hit)
