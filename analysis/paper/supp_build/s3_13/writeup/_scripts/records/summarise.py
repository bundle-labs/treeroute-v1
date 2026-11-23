# Summarise work/listing_<name>.json (written by list_folders.py): counts and bytes per folder level and per extension.
# Reads only the two listing files. Usage: summarise.py <shap|out> <depth> [prefix]
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))


def ext_of(rel):
    base = rel.rsplit('/', 1)[-1]
    if '.' not in base:
        return '(none)'
    return '.' + base.rsplit('.', 1)[-1].lower()


def main():
    name = sys.argv[1]
    depth = int(sys.argv[2])
    prefix = sys.argv[3] if len(sys.argv) > 3 else ''
    with open(os.path.join(HERE, 'work', 'listing_%s.json' % name), encoding='utf-8') as f:
        rec = json.load(f)
    files = [r for r in rec['files'] if r[0].replace('\\', '/').startswith(prefix)]
    grp = collections.OrderedDict()
    for rel, size, mt, rp in files:
        rel = rel.replace('\\', '/')
        rest = rel[len(prefix):].lstrip('/')
        parts = rest.split('/')
        key = '/'.join(parts[:depth]) if len(parts) > depth else ('(file) ' + rest if len(parts) <= depth and len(parts) == 1 else '/'.join(parts[:-1]) + '/(files)')
        g = grp.setdefault(key, [0, 0, collections.Counter(), '', ''])
        g[0] += 1
        g[1] += size
        g[2][ext_of(rel)] += 1
        g[3] = min(g[3], mt) if g[3] else mt
        g[4] = max(g[4], mt)
    for k in sorted(grp):
        n, b, ex, m0, m1 = grp[k]
        exs = ', '.join('%s %d' % (e, c) for e, c in ex.most_common(8))
        print('%-70s %6d %15s  [%s]  %s..%s' % (k[:70], n, format(b, ','), exs, m0, m1))
    print('TOTAL', len(files), format(sum(r[1] for r in files), ','))


if __name__ == '__main__':
    main()
