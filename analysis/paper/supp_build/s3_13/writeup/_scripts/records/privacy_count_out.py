# Count-only privacy scan of the S3.13 table build folder (OUT) outside stage/: which files hold the account name,
# the profile-prefix form, the host name, a session-id-shaped UUID, a workflow id, an e-mail address or a
# Windows-default host name. Names are taken at run time from the environment and are never printed or written; the
# output gives counts per folder and pattern only. Decodes each file by its byte-order mark, without loss.
import os, re, sys, json, collections, codecs

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
FOLDERS = ['spec', 'A', 'B', 'reconcile', 'skeptic', '_brief']

acct = os.path.basename(os.environ.get('USERPROFILE', '') or '')
host = os.environ.get('COMPUTERNAME', '') or ''
assert acct and host
PATS = collections.OrderedDict([
    ('account name', re.compile(re.escape(acct), re.I)),
    ('profile prefix (Users + 3 letters)', re.compile(r'users[\\/]+' + re.escape(acct[:3]), re.I)),
    ('drive-letter Users path', re.compile(r'[A-Za-z]:(\\\\|\\|/)+users(\\\\|\\|/)+', re.I)),
    ('session-folder form', re.compile(r'[A-Za-z]--users-', re.I)),
    ('host name', re.compile(re.escape(host), re.I)),
    ('Windows default host form', re.compile(r'DESKTOP-[A-Z0-9]{7}', re.I)),
    ('UUID-shaped id', re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.I)),
    ('workflow id (wf_)', re.compile(r'\bwf_[0-9a-f]{6,}', re.I)),
    ('e-mail address', re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')),
])


def decode(b):
    if b.startswith(codecs.BOM_UTF8):
        return b[3:].decode('utf-8', 'surrogateescape'), 'utf-8-sig'
    if b.startswith(codecs.BOM_UTF16_LE):
        return b[2:].decode('utf-16-le', 'surrogatepass'), 'utf-16-le'
    return b.decode('utf-8', 'surrogateescape'), 'utf-8'


def main():
    import datetime
    print('scan start UTC', datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))
    res = collections.OrderedDict()
    enc = collections.Counter()
    for top in FOLDERS:
        base = os.path.join(OUT, top)
        per = collections.Counter()
        nfiles = 0
        for dp, dn, fn in os.walk(base):
            for n in fn:
                p = os.path.join(dp, n)
                with open(p, 'rb') as f:
                    b = f.read()
                t, e = decode(b)
                enc[e] += 1
                nfiles += 1
                for k, rx in PATS.items():
                    if rx.search(t):
                        per[k] += 1
        res[top] = (nfiles, dict(per))
    for top, (n, per) in res.items():
        print('%-10s files %4d  ' % (top, n) + '; '.join('%s: %d' % (k, per.get(k, 0)) for k in PATS))
    tot = collections.Counter()
    for top, (n, per) in res.items():
        tot.update(per)
    print('ALL       files %4d  ' % sum(v[0] for v in res.values()) + '; '.join('%s: %d' % (k, tot.get(k, 0)) for k in PATS))
    print('encodings', dict(enc))
    print('scan end UTC', datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))


if __name__ == '__main__':
    main()
