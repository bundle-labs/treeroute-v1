# Print the files of work/listing_<name>.json under a prefix (relpath, size, mtime UTC), at most <limit> lines.
# Reads only the listing file. Usage: names.py <shap|out> <prefix> [limit] [depth]
# With depth, files below that many path levels under the prefix are grouped into their folder (count, bytes).
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    name, prefix = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    depth = int(sys.argv[4]) if len(sys.argv) > 4 else None
    with open(os.path.join(HERE, 'work', 'listing_%s.json' % name), encoding='utf-8') as f:
        rec = json.load(f)
    rows = [r for r in rec['files'] if r[0].replace('\\', '/').startswith(prefix)]
    if depth is None:
        for r in rows[:limit]:
            print('%-100s %14s %s' % (r[0].replace('\\', '/'), format(r[1], ','), r[2]))
    else:
        grp = collections.OrderedDict()
        for r in rows:
            rel = r[0].replace('\\', '/')[len(prefix):].lstrip('/')
            parts = rel.split('/')
            key = rel if len(parts) <= depth else '/'.join(parts[:depth]) + '/...'
            g = grp.setdefault(key, [0, 0])
            g[0] += 1
            g[1] += r[1]
        for k in list(grp)[:limit]:
            print('%-100s %6d %14s' % (k, grp[k][0], format(grp[k][1], ',')))
    print('rows', len(rows), 'bytes', format(sum(r[1] for r in rows), ','))


if __name__ == '__main__':
    main()
