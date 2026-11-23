# Self-test of privacy_count_out.py's patterns: synthetic strings (built at run time, so this file holds none of the
# patterns' text), then a count over OUT/stage (not archived) as a positive control. Prints counts only.
import os, re, sys, importlib.util, collections

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('pc', os.path.join(HERE, 'privacy_count_out.py'))
pc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pc)

acct = pc.acct
bs, us = chr(92), 'Us' + 'ers'
hexs = '0123456789abcdef'
samples = {
    'win path': 'X:' + bs + us + bs + acct + bs + 'Downloads',
    'json path': 'X:' + bs * 2 + us + bs * 2 + acct + bs * 2 + 'Downloads',
    'fwd path': 'x:/' + us.lower() + '/' + acct.upper() + '/a',
    'uuid': 'id ' + '-'.join([hexs[:8], hexs[:4], hexs[4:8], hexs[8:12], hexs[:12]]) + ' here',
    'wf': 'workflow ' + 'wf' + '_' + hexs[:8] + '-123',
}
for name, s in samples.items():
    hits = [k for k, rx in pc.PATS.items() if rx.search(s)]
    print('%-10s -> %d patterns hit' % (name, len(hits)))

stage = os.path.join(pc.OUT, 'stage')
per = collections.Counter()
n = 0
for dp, dn, fn in os.walk(stage):
    for f in fn:
        with open(os.path.join(dp, f), 'rb') as fh:
            t, e = pc.decode(fh.read())
        n += 1
        for k, rx in pc.PATS.items():
            if rx.search(t):
                per[k] += 1
print('stage files', n, '; '.join('%s: %d' % (k, per.get(k, 0)) for k in pc.PATS))
