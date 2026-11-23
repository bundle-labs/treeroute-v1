# relist_out.py - re-lists, by os.scandir / os.stat only (no file is opened), the six folders of the S3.13 table
# build that the archive plan archives (spec, A, B, reconcile, skeptic, _brief), and compares the result with the
# records writer's listing of 2026-11-17 09:34 UTC (STAGE/_scripts/records/work/listing_out.json, paths relative
# to OUT). Prints counts, bytes, extensions and every file whose size or presence differs; paths relative to OUT.
import collections
import datetime
import json
import os
import stat
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fix_lib import OUT, STAGE, WORK

FOLDERS = ['spec', 'A', 'B', 'reconcile', 'skeptic', '_brief']


def walk(root):
    files = {}
    reparse = []
    stack = [root]
    while stack:
        d = stack.pop()
        with os.scandir(d) as it:
            entries = list(it)
        for e in entries:
            st = e.stat(follow_symlinks=False)
            attrs = getattr(st, 'st_file_attributes', 0)
            is_rp = bool(attrs & 0x400) or stat.S_ISLNK(st.st_mode)
            if is_rp:
                reparse.append(os.path.relpath(e.path, OUT))
                continue
            if stat.S_ISDIR(st.st_mode):
                stack.append(e.path)
            else:
                rel = os.path.relpath(e.path, OUT).replace(os.sep, '/')
                mt = datetime.datetime.utcfromtimestamp(st.st_mtime).strftime('%Y-%m-%dT%H:%M:%SZ')
                files[rel] = (st.st_size, mt)
    return files, reparse


def main():
    t0 = datetime.datetime.utcnow()
    now = {}
    rp = []
    for f in FOLDERS:
        fs, r = walk(os.path.join(str(OUT), f))
        now.update(fs)
        rp += r
    t1 = datetime.datetime.utcnow()
    old_rec = json.loads((STAGE / '_scripts' / 'records' / 'work' / 'listing_out.json').read_text(encoding='utf-8'))
    old = {}
    for rel, size, mt, isrp in old_rec['files']:
        top = rel.split('/')[0]
        if top in FOLDERS:
            old[rel] = (size, mt)
    print('re-listed UTC %s to %s; reparse points %d' % (t0.strftime('%H:%M:%S'), t1.strftime('%H:%M:%S'), len(rp)))
    print('records listing: %s to %s' % (old_rec['listed_utc_start'], old_rec['listed_utc_end']))
    for label, d in (('old', old), ('now', now)):
        by_top = collections.OrderedDict((f, [0, 0]) for f in FOLDERS)
        ext = collections.Counter()
        extb = collections.Counter()
        for rel, (size, mt) in d.items():
            by_top[rel.split('/')[0]][0] += 1
            by_top[rel.split('/')[0]][1] += size
            e = os.path.splitext(rel)[1].lower()
            ext[e] += 1
            extb[e] += size
        print(label, 'files', len(d), 'bytes', '{:,}'.format(sum(s for s, m in d.values())),
              '| ' + '; '.join('%s %d/%s' % (k, v[0], '{:,}'.format(v[1])) for k, v in by_top.items()))
        print('   ext', dict(ext), '| .py bytes', '{:,}'.format(extb['.py']))
    only_old = sorted(set(old) - set(now))
    only_now = sorted(set(now) - set(old))
    changed = sorted(r for r in set(old) & set(now) if old[r][0] != now[r][0])
    same_size_new_time = sorted(r for r in set(old) & set(now) if old[r][0] == now[r][0] and old[r][1] != now[r][1])
    print('only in old:', only_old)
    print('only now:', only_now)
    for r in changed:
        print('size changed:', r, old[r], '->', now[r], 'delta', now[r][0] - old[r][0])
    for r in same_size_new_time:
        print('same size, new time:', r, old[r], '->', now[r])
    out = {'relisted_utc': [t0.strftime('%Y-%m-%dT%H:%M:%SZ'), t1.strftime('%Y-%m-%dT%H:%M:%SZ')],
           'files': len(now), 'bytes': sum(s for s, m in now.values()),
           'py_bytes_out_now': sum(s for r, (s, m) in now.items() if r.lower().endswith('.py')),
           'py_bytes_out_old': sum(s for r, (s, m) in old.items() if r.lower().endswith('.py')),
           'old_files': len(old), 'old_bytes': sum(s for s, m in old.values()),
           'changed': {r: [old[r], now[r]] for r in changed}, 'only_old': only_old, 'only_now': only_now}
    (WORK / 'relist_out.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k not in ('changed',)}, indent=0))


if __name__ == '__main__':
    main()
