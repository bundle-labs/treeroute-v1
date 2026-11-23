# privacy_two.py - count-only privacy scan of the two files of OUT/_brief/lead_checks/ that were rewritten after the
# records writer's listing and scan (verify_v5_claims.py and verify_v5_claims_out.txt), with the patterns of
# STAGE/_scripts/records/privacy_count_out.py, plus this fixer's own outputs (STAGE/_scripts/fix/ and
# STAGE/changes_fix.md, outside work/base/, which holds byte copies of the staged files). Names are taken from the
# environment at run time and never printed or written; the output gives counts only.
import codecs
import collections
import datetime
import os
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fix_lib import OUT, STAGE, HERE

acct = os.path.basename(os.environ.get('USERPROFILE', '') or '')
host = os.environ.get('COMPUTERNAME', '') or ''
assert acct and host
PATS = collections.OrderedDict([
    ('account name', re.compile(re.escape(acct), re.I)),
    ('profile prefix (Users + 3 letters)', re.compile(r'users[\\/]+' + re.escape(acct[:3]), re.I)),
    ('drive-letter Users path', re.compile(r'[A-Za-z]:(\\\\|\\|/)+users(\\\\|\\|/)+', re.I)),
    ('session-folder form', re.compile(r'[A-Za-z]--users-', re.I)),
    ('host name', re.compile(re.escape(host), re.I)),
    ('Windows default host form', re.compile(r'(DESKTOP|LAPTOP)-[A-Z0-9]{7}', re.I)),
    ('UUID-shaped id', re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.I)),
    ('workflow id (wf_)', re.compile(r'\bwf_[0-9a-f]{6,}', re.I)),
    ('e-mail address', re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')),
])


def decode(b):
    if b.startswith(codecs.BOM_UTF8):
        return b[3:].decode('utf-8', 'surrogateescape')
    if b.startswith(codecs.BOM_UTF16_LE):
        return b[2:].decode('utf-16-le', 'surrogatepass')
    return b.decode('utf-8', 'surrogateescape')


def scan(paths, label):
    per = collections.Counter()
    for p in paths:
        t = decode(Path(p).read_bytes())
        for k, rx in PATS.items():
            if rx.search(t):
                per[k] += 1
    print('%s: files %d; ' % (label, len(paths)) + '; '.join('%s: %d' % (k, per.get(k, 0)) for k in PATS))


def main():
    print('scan start UTC', datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))
    two = [OUT / '_brief' / 'lead_checks' / 'verify_v5_claims.py', OUT / '_brief' / 'lead_checks' / 'verify_v5_claims_out.txt']
    scan(two, 'two rewritten files')
    own = []
    for dp, dn, fn in os.walk(HERE):
        if os.path.normcase(os.path.join(HERE, 'work', 'base')) in os.path.normcase(dp):
            continue
        for n in fn:
            if n.endswith('.pyc'):
                continue
            own.append(os.path.join(dp, n))
    cf = STAGE / 'changes_fix.md'
    if cf.exists():
        own.append(str(cf))
    scan(own, 'fixer outputs (outside work/base)')
    print('scan end UTC', datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))


if __name__ == '__main__':
    main()
