import json, re
ENG = r'C:/Users/<user>/Desktop/data set for reserch paper/engine'
R = r'D:/treeroute/runs/pm25/headline/20261007_74e67609'
S = r'D:/treeroute/rivals_scratch/pm25/20261007_74e67609'
plan = json.load(open(R + '/plan.json'))
def find(o, key, path=''):
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key: out.append((path + '/' + k, v))
            out += find(v, key, path + '/' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o[:50]): out += find(v, key, path + '[%d]' % i)
    return out
hc = find(plan, 'history_columns'); ctx = find(plan, 'context')
print('plan history_columns:', hc[:2]); print('plan context:', [c for c in ctx if isinstance(c[1], list)][:2])
tc = find(plan, 'tree_columns') + find(plan, 'features') + find(plan, 'kept_columns')
print('plan tree col keys:', [(p, len(v) if isinstance(v, list) else v) for p, v in tc][:6])
# ban.yaml verdicts (plain-text parse: column name lines followed by verdict)
import yaml
b = yaml.safe_load(open(ENG + '/datasets/pm25/ban.yaml', encoding='utf-8'))
ver = {}
def walk(o):
    if isinstance(o, dict):
        if 'verdict' in o and ('column' in o or 'name' in o):
            ver[o.get('column', o.get('name'))] = o['verdict']
        for k, v in o.items():
            if isinstance(v, dict) and 'verdict' in v: ver.setdefault(k, v['verdict'])
            walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(b)
print('ban.yaml entries parsed:', len(ver), 'verdict counts:', {v: list(ver.values()).count(v) for v in set(ver.values())})
for L in (0, 6, 12):
    cols = json.load(open(f'{S}/lead_{L}_refit.json'))['columns']
    names = [c.split('__', 1)[1] for c in cols]
    bad = [(n, ver.get(n)) for n in names if ver.get(n) not in ('keep', 'watch')]
    kw = [n for n, v in ver.items() if v in ('keep', 'watch')]
    missing = [n for n in kw if n not in names]
    print(f'lead {L}: {len(cols)} cols; not keep/watch: {bad}; keep/watch not given to rivals: {missing}')
