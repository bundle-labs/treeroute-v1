# Read-only listing of the SHAP analysis folder and the S3.13 table build folder, by os.scandir / os.stat only.
# No file is opened. SHAP\smoke\bardl_fix\ is never entered (its path is pruned before any scandir call).
# Reparse points (junctions, symlinks) are recorded and not followed.
# Output: work/listing_<name>.json with [relpath, size, mtime_utc_iso, is_reparse] per file, plus pruned and reparse dirs.
# Paths are written relative to the listed root; any path component holding the account or host name is redacted.
import os, sys, json, datetime, stat

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, 'work')

SHAP = r'D:\treeroute\analysis\shap_v1'
OUT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))  # stage\_scripts\records -> s3_13
PRUNE = {os.path.normcase(os.path.join(SHAP, 'smoke', 'bardl_fix'))}

_acct = os.path.basename(os.environ.get('USERPROFILE', '') or '').lower()
_host = (os.environ.get('COMPUTERNAME', '') or '').lower()


def redact(rel):
    parts = rel.split(os.sep)
    out = []
    for p in parts:
        lp = p.lower()
        if (_acct and _acct in lp) or (_host and _host in lp):
            out.append('<redacted>')
        else:
            out.append(p)
    return '/'.join(out)


def walk(root):
    files, pruned, reparse, errors = [], [], [], []
    stack = [root]
    while stack:
        d = stack.pop()
        if os.path.normcase(d) in PRUNE:
            pruned.append(redact(os.path.relpath(d, root)))
            continue
        try:
            with os.scandir(d) as it:
                entries = list(it)
        except OSError as e:
            errors.append([redact(os.path.relpath(d, root)), type(e).__name__])
            continue
        for e in entries:
            p = e.path
            try:
                st = e.stat(follow_symlinks=False)
            except OSError as ex:
                errors.append([redact(os.path.relpath(p, root)), type(ex).__name__])
                continue
            attrs = getattr(st, 'st_file_attributes', 0)
            is_rp = bool(attrs & 0x400) or stat.S_ISLNK(st.st_mode)
            if stat.S_ISDIR(st.st_mode) or (is_rp and e.is_dir(follow_symlinks=True)):
                if is_rp:
                    reparse.append(redact(os.path.relpath(p, root)))
                    continue
                if os.path.normcase(p) in PRUNE:
                    pruned.append(redact(os.path.relpath(p, root)))
                    continue
                stack.append(p)
            else:
                mt = datetime.datetime.utcfromtimestamp(st.st_mtime).strftime('%Y-%m-%dT%H:%M:%SZ')
                files.append([redact(os.path.relpath(p, root)), st.st_size, mt, is_rp])
    files.sort(key=lambda r: r[0])
    return files, sorted(pruned), sorted(reparse), errors


def main():
    os.makedirs(WORK, exist_ok=True)
    stamp = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    for name, root in (('shap', SHAP), ('out', OUT)):
        t0 = datetime.datetime.utcnow()
        files, pruned, reparse, errors = walk(root)
        t1 = datetime.datetime.utcnow()
        rec = {'root_label': 'SHAP' if name == 'shap' else 'OUT', 'listed_utc_start': t0.strftime('%Y-%m-%dT%H:%M:%SZ'),
               'listed_utc_end': t1.strftime('%Y-%m-%dT%H:%M:%SZ'), 'files': files, 'pruned_not_entered': pruned,
               'reparse_points_not_followed': reparse, 'errors': errors}
        with open(os.path.join(WORK, 'listing_%s.json' % name), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(rec, f, indent=0)
        tot = sum(r[1] for r in files)
        print('%s: %d files, %d bytes; pruned %s; reparse %d; errors %d; %s-%s' % (
            rec['root_label'], len(files), tot, pruned, len(reparse), len(errors), rec['listed_utc_start'], rec['listed_utc_end']))
    print('run at', stamp)


if __name__ == '__main__':
    main()
