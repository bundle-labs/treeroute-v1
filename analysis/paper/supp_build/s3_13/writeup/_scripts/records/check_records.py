# Checks of this writer's staged files against their base copies (work/base/). Read-only; prints a report.
#  1. The diff is insertions only, apart from the listed replacements (printed old and new).
#  2. UTF-8 without BOM, LF only, one final LF.
#  3. PROTOCOL.md: inserted lines ASCII and at most 120 characters; sections 3 and 8 byte-identical (SHA-256 printed).
#  4. Privacy: no account or host name, Users path, UUID-shaped id or workflow id in any inserted line.
#  5. Numbers: each number token of the inserted lines of PENDING_PARTS.md, PROTOCOL.md and PAPER_OUTLINE.md is
#     looked up in the source texts (fact sheet section 9, PROTOCOL.md, RUN_COMMANDS.md, the rulings, the lead's
#     check output, the table rounds' read record); tokens not found are printed for review.
#  6. Manifest: every number token of its inserted lines is in work/tokens.json, in the base manifest or in a short
#     list of plain words (dates, section numbers); others are printed.
import os, sys, re, json, hashlib, difflib

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.normpath(os.path.join(HERE, '..', '..'))
OUT = os.path.normpath(os.path.join(STAGE, '..'))
ROOT = os.path.normpath(os.path.join(OUT, '..', '..', '..'))
BASE = os.path.join(HERE, 'work', 'base')
FILES = ['shap/PROTOCOL.md', 'engine/PENDING_PARTS.md', 'paper/PAPER_OUTLINE.md', '_archive_plan/ARCHIVE_MANIFEST_DRAFT.md']
ALLOWED_REPLACE = {
    'engine/PENDING_PARTS.md': 1,
    '_archive_plan/ARCHIVE_MANIFEST_DRAFT.md': 4,
}


def rb(p):
    with open(p, 'rb') as f:
        return f.read()


def section(text, num):
    m = re.search(r'^## %d\. .*$' % num, text, re.M)
    n = re.search(r'^## %d\. .*$' % (num + 1), text, re.M)
    return text[m.start():n.start()]


def main():
    acct = os.path.basename(os.environ.get('USERPROFILE', '') or '').lower()
    host = (os.environ.get('COMPUTERNAME', '') or '').lower()
    priv = [re.compile(r'[A-Za-z]:(\\|/)+users(\\|/)', re.I), re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.I),
            re.compile(r'\bwf_[0-9a-f]{6,}', re.I), re.compile(r'[A-Za-z]--users-', re.I)]
    src = []
    src.append(rb(os.path.join(STAGE, 'paper', 'PAPER_FACTS.md')).decode('utf-8'))
    src.append(rb(r'D:\treeroute\analysis\shap_v1\PROTOCOL.md').decode('utf-8'))
    src.append(rb(r'D:\treeroute\analysis\shap_v1\RUN_COMMANDS.md').decode('utf-8'))
    src.append(rb(os.path.join(ROOT, 'engine', 'OWNER_RULINGS_2026-10-06.md')).decode('utf-8'))
    src.append(rb(os.path.join(OUT, '_brief', 'lead_checks', 'verify_v5_claims_out.txt')).decode('utf-8'))
    src.append(rb(os.path.join(OUT, '_brief', 'reads_tables.md')).decode('utf-8'))
    src.append(rb(os.path.join(OUT, '_brief', 'brief_text.md')).decode('utf-8'))
    src_all = '\n'.join(src).replace('\u2212', '-')
    with open(os.path.join(HERE, 'work', 'tokens.json'), encoding='utf-8') as f:
        tok = json.load(f)
    tokvals = set(tok.values())
    for rel in FILES:
        base_b = rb(os.path.join(BASE, rel.replace('/', '__')))
        new_b = rb(os.path.join(STAGE, *rel.split('/')))
        print('==', rel, 'base', hashlib.sha256(base_b).hexdigest(), 'staged', hashlib.sha256(new_b).hexdigest())
        ok_fmt = (not new_b.startswith(b'\xef\xbb\xbf')) and (b'\r' not in new_b) and new_b.endswith(b'\n') and not new_b.endswith(b'\n\n')
        new_b.decode('utf-8')
        print('   format: utf-8, no BOM, LF only, one final LF:', ok_fmt)
        a = base_b.decode('utf-8').split('\n')
        b = new_b.decode('utf-8').split('\n')
        sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
        ins, rep = [], []
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'equal':
                continue
            if op == 'insert':
                ins.extend(b[j1:j2])
            elif op == 'replace':
                rep.append((a[i1:i2], b[j1:j2]))
                ins.extend(b[j1:j2])
            else:
                print('   !! DELETE of lines', i1, i2, a[i1:i2])
        print('   inserted lines (incl. replacements):', len(ins), '; replace blocks:', len(rep),
              '(allowed %d)' % ALLOWED_REPLACE.get(rel, 0))
        for old, new in rep:
            if len(old) == 1 and len(new) == 1:
                print('   old line kept as the prefix of the new line:', new[0].startswith(old[0]))
            for o in old:
                # old text must survive inside the new lines (log keeps old text) or be a number row
                print('   replaced old: %s' % (o[:160] + ('...' if len(o) > 160 else '')))
            for n in new:
                print('        new  : %s' % (n[:160] + ('...' if len(n) > 160 else '')))
        joined = '\n'.join(ins)
        hits = [p.pattern for p in priv if p.search(joined)]
        if acct and acct in joined.lower():
            hits.append('account name')
        if host and host in joined.lower():
            hits.append('host name')
        print('   privacy hits in inserted text:', hits)
        if rel == 'shap/PROTOCOL.md':
            long_ = [l for l in ins if len(l) > 120]
            nonascii = [l for l in ins if any(ord(c) > 127 for c in l)]
            print('   PROTOCOL inserted lines > 120 chars:', len(long_), '; non-ASCII lines:', len(nonascii),
                  '; max length', max(len(l) for l in ins))
            bt, nt = base_b.decode('utf-8'), new_b.decode('utf-8')
            for s in (3, 8):
                hb = hashlib.sha256(section(bt, s).encode('utf-8')).hexdigest()
                hn = hashlib.sha256(section(nt, s).encode('utf-8')).hexdigest()
                print('   section %d sha256 live %s staged %s equal %s (%d bytes)' % (s, hb, hn, hb == hn,
                                                                                    len(section(bt, s).encode('utf-8'))))
            print('   @@LATER_READS@@ lines:', sum(1 for l in b if l == '@@LATER_READS@@'),
                  '; @@SNAP@@ count:', nt.count('@@SNAP@@'),
                  '; longest line holding @@SNAP@@:', max(len(l) for l in b if '@@SNAP@@' in l))
            print('   whole-file max line length', max(len(l) for l in b), '; lines > 120:',
                  sum(1 for l in b if len(l) > 120))
        if rel == 'engine/PENDING_PARTS.md':
            print('   non-ASCII chars inserted:', sum(1 for c in joined if ord(c) > 127))
        # numbers
        nums = re.findall(r'(?<![A-Za-z0-9_.])-?\d[\d,]*(?:\.\d+)?(?:e-?\d+)?', joined)
        if rel == '_archive_plan/ARCHIVE_MANIFEST_DRAFT.md':
            base_t = base_b.decode('utf-8')
            miss = sorted(set(n for n in nums if n not in tokvals and n not in base_t and n.lstrip('-') not in base_t))
            print('   manifest number tokens not in tokens.json or the base manifest:', miss)
        else:
            miss = sorted(set(n for n in nums if n not in src_all))
            print('   number tokens not found in the sources:', miss)


if __name__ == '__main__':
    main()
