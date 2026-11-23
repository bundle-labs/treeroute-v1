# From work/listing_<name>.json only: folders whose name contains a pattern (count and bytes of the files below them).
# Usage: find_dirs.py <shap|out> <pattern> [pattern ...]
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    name, pats = sys.argv[1], [p.lower() for p in sys.argv[2:]]
    with open(os.path.join(HERE, 'work', 'listing_%s.json' % name), encoding='utf-8') as f:
        rec = json.load(f)
    grp = collections.OrderedDict()
    for rel, size, mt, rp in rec['files']:
        parts = rel.replace('\\', '/').split('/')
        for i, comp in enumerate(parts[:-1]):
            if any(p in comp.lower() for p in pats):
                key = '/'.join(parts[:i + 1])
                g = grp.setdefault(key, [0, 0])
                g[0] += 1
                g[1] += size
                break
    for k in sorted(grp):
        print('%-90s %6d %15s' % (k, grp[k][0], format(grp[k][1], ',')))
    print('folders', len(grp), 'files', sum(v[0] for v in grp.values()), 'bytes', format(sum(v[1] for v in grp.values()), ','))


if __name__ == '__main__':
    main()
