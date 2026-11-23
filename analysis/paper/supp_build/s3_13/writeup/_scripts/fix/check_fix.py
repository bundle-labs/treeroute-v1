# check_fix.py - read-only checks of the fixer's edits (S3.13 write-up, 2026-11-17). Prints results only, except the
# changed-line diffs pre-fix -> post-fix, written to work/fixdiff_<file>.txt.
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fix_lib import STAGE, WORK, D, FILES, sha, form, visible, base_name
import privacy_two as P

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
applied = json.loads((WORK / 'applied_edits.json').read_text(encoding='utf-8'))
pre = json.loads((WORK / 'base_hashes.json').read_text(encoding='utf-8'))
ok = True


def bad(msg):
    global ok
    ok = False
    print('PROBLEM:', msg)


# 1. pre-fix text by undoing the recorded edits; forms; comments; placeholders; diffs
for rel, edits in applied['edits'].items():
    b = (STAGE / rel).read_bytes()
    t = b.decode('utf-8')
    u = t
    for eid, old, new in reversed(edits):
        assert u.count(new) == 1, (rel, eid)
        u = u.replace(new, old)
    if sha(u.encode('utf-8')) != pre[rel]['base_sha']:
        bad('%s: undo does not give the pre-fix hash' % rel)
    f0, f1 = form(u.encode('utf-8')), form(b)
    if f1['bom'] or not f1['utf8'] or not f1['final_newline'] or f1['double_final']:
        bad('%s: form %s' % (rel, f1))
    if f0['crlf'] and (f1['bare_lf'] or f1['bare_cr']):
        bad('%s: CRLF file gained a bare LF or CR' % rel)
    if not f0['crlf'] and (f1['crlf'] or f1['bare_cr']):
        bad('%s: LF file gained a CR' % rel)
    for ph in ('@@SNAP@@', '@@LATER_READS@@'):
        if u.count(ph) != t.count(ph):
            bad('%s: placeholder %s count changed' % (rel, ph))
    # comments: closed, not nested, no "--" inside (whole file)
    i = 0
    while True:
        j = t.find('<!--', i)
        if j < 0:
            break
        k = t.find('-->', j + 4)
        if k < 0:
            bad('%s: unclosed comment at %d' % (rel, j))
            break
        inner = t[j + 4:k]
        if '<!--' in inner:
            bad('%s: nested comment at %d' % (rel, j))
        if '--' in inner:
            bad('%s: "--" inside a comment at %d' % (rel, j))
        i = k + 3
    d = list(difflib.unified_diff(u.splitlines(), t.splitlines(), 'pre-fix', 'post-fix', n=0, lineterm=''))
    (WORK / ('fixdiff_' + base_name(rel) + '.txt')).write_text('\n'.join(d) + '\n', encoding='utf-8')
    print('%-42s form ok: bom=%s crlf=%d lf=%d | changed lines: -%d +%d' % (
        rel, f1['bom'], f1['crlf'], f1['bare_lf'], sum(1 for x in d if x.startswith('-') and not x.startswith('---')),
        sum(1 for x in d if x.startswith('+') and not x.startswith('+++'))))

# 2. PROTOCOL.md rules
pt = (STAGE / 'shap/PROTOCOL.md').read_text(encoding='utf-8')
live_p = FILES['shap/PROTOCOL.md'].read_bytes()
if not (STAGE / 'shap/PROTOCOL.md').read_bytes().startswith(live_p):
    bad('PROTOCOL.md: the live file is no longer a byte prefix of the staged one')
new_part = pt[len(live_p.decode('utf-8')):]
for n, ln in enumerate(new_part.split('\n'), 1):
    if len(ln) > 120:
        bad('PROTOCOL.md new line %d has %d characters' % (n, len(ln)))
    if any(ord(c) > 127 for c in ln):
        bad('PROTOCOL.md new line %d is not ASCII' % n)


def section(text, start, end):
    a = text.index(start)
    b = text.index(end, a)
    return text[a:b].encode('utf-8')


s3 = section(pt, '## 3. The sample', '## 4. Rebuild')
s8 = section(pt, '## 8. Comparison and statistics', '## 9. Outputs')
print('PROTOCOL section 3', hashlib.sha256(s3).hexdigest()[:12], len(s3), '| section 8', hashlib.sha256(s8).hexdigest()[:12],
      len(s8), '| longest new line', max(len(x) for x in new_part.split('\n')))
if hashlib.sha256(s3).hexdigest()[:12] != '28d54cbd9df9' or hashlib.sha256(s8).hexdigest()[:12] != '4c03d6ed5974':
    bad('PROTOCOL.md sections 3 or 8 changed')

# 3. cross-references with the build's expressions (build_docx.py lines 1455-1458, 1494)
SEC_REF_RE = re.compile(r"\bSections?\s+(?P<first>\d+(?:\.\d+)*)(?P<more>(?:\s*(?:,|and|or|to|–|-)\s*\d+(?:\.\d+)*)*)")
SUP_REF_RE = re.compile(r"\b(?:Supplements?|Sections?)\s+(?P<first>S\d+(?:\.\d+)*)(?P<more>(?:\s*(?:,|and|or|to|–|-)\s*S\d+(?:\.\d+)*)*)")
BARE_SUP_RE = re.compile(r"(?<!Table )(?<!Tables )(?<!Supplement )(?<!Supplements )(?<!Section )(?<!Sections )"
                         r"(?<![\w.])(S\d+\.\d+(?:\.\d+)?)(?=[,;)\s])")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$", re.M)
CAPTION_TABLE_RE = re.compile(r"^\*\*Table\s+(S?\d+(?:\.\d+)?[a-z]?)\b", re.M)


def src(p):
    sp = STAGE / 'paper' / 'draft' / p.relative_to(D)
    return sp if sp.exists() else p


def hnum(h):
    m = re.match(r"^(S?\d+(?:\.\d+)*)\s", h + " ")
    return m.group(1) if m else None


sup_files = sorted(D.glob('S*.md')) + sorted(D.glob('tables/table_S*.md'))
man_files = sorted(D.glob('0*.md')) + sorted(D.glob('tables/table_[0-9]*.md')) + [D / 'tables' / 'table_9.md']
sup_heads, man_heads, sup_tables = set(), set(), set()
for p in sup_files:
    t = src(p).read_text(encoding='utf-8', errors='replace')
    sup_heads |= {hnum(m.group(2)) for m in HEADING_RE.finditer(t)}
    sup_tables |= {re.match(r"^(S?\d+(?:\.\d+)?)", m.group(1)).group(1) for m in CAPTION_TABLE_RE.finditer(visible(t))}
for p in man_files:
    q = src(p)
    if q.exists():
        man_heads |= {hnum(m.group(2)) for m in HEADING_RE.finditer(q.read_text(encoding='utf-8', errors='replace'))}
sup_heads.discard(None)
man_heads.discard(None)
for rel in ('paper/draft/S3_posthoc.md', 'paper/draft/S1_disclosures.md', 'paper/draft/S4_provenance.md',
            'paper/draft/05_rivals.md', 'paper/draft/tables/table_9.md'):
    t = visible((STAGE / rel).read_text(encoding='utf-8'))
    t = re.sub(r"\[(?:PENDING|OWNER):[^\]]*\]", lambda m: ' ' * len(m.group(0)), t)
    probs = []
    for m in BARE_SUP_RE.finditer(t):
        if m.group(1) not in sup_heads:
            probs.append('bare ' + m.group(1))
    for m in SEC_REF_RE.finditer(t):
        for n in [m.group('first')] + re.findall(r"\d+(?:\.\d+)*", m.group('more') or ''):
            if n not in man_heads:
                probs.append('Section ' + n)
    for m in SUP_REF_RE.finditer(t):
        for n in [m.group('first')] + re.findall(r"S\d+(?:\.\d+)*", m.group('more') or ''):
            if n not in sup_heads:
                probs.append('Supplement ' + n)
    for m in re.finditer(r"\bTables?\s+(S\d+\.\d+)", t):
        if re.match(r"^(S?\d+(?:\.\d+)?)", m.group(1)).group(1) not in sup_tables:
            probs.append('Table ' + m.group(1))
    print('cross-references %-32s problems: %d %s' % (rel, len(probs), sorted(set(probs))[:8]))
    if probs:
        bad('%s cross-references: %s' % (rel, sorted(set(probs))))

# 4. AI terms (build_docx.py lines 1506-1507) outside S1 and S4; absolute paths in visible text
AI_STRONG = re.compile(r"\bAI\b|(?i:\bartificial intelligence\b|\bgenerative\b|\blarge language models?\b|\bLLMs?\b|\bchatgpt\b|\bcopilot\b|\bclaude\b|\banthropic\b)|\bGPT-?\d")
AI_WEAK = re.compile(r"(?i)\bagents?\b")
for rel in ('paper/draft/S3_posthoc.md', 'paper/draft/05_rivals.md', 'paper/draft/tables/table_9.md', 'paper/draft/GLOSSARY.md'):
    t = visible((STAGE / rel).read_text(encoding='utf-8'))
    n1, n2 = len(AI_STRONG.findall(t)), len(AI_WEAK.findall(t))
    print('AI terms in visible %-34s strong %d, weak %d' % (rel, n1, n2))
    if n1 or n2:
        bad('%s: AI term in visible text' % rel)
for rel in ('paper/draft/S3_posthoc.md', 'paper/draft/S1_disclosures.md', 'paper/draft/S4_provenance.md',
            'paper/draft/GLOSSARY.md', 'paper/draft/05_rivals.md', 'paper/draft/tables/table_9.md'):
    t = visible((STAGE / rel).read_text(encoding='utf-8'))
    hits = re.findall(r"\b[A-Za-z]:[\\/][^\s|)]*", t)
    print('absolute paths in visible %-30s %d' % (rel, len(hits)))
    if hits:
        bad('%s: absolute path in visible text: %s' % (rel, hits[:3]))

# 5. the new visible text of each edit: privacy patterns, glossary do-not-use names, number tokens
names = []
for line in (STAGE / 'paper/draft/GLOSSARY.md').read_text(encoding='utf-8').split('\n'):
    if not line.startswith('| **'):
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    if len(cells) < 4:
        continue
    term = re.sub(r"\*\*", "", cells[0])
    for raw in re.sub(r"<!--.*?-->", "", cells[1]).split(','):
        n = re.sub(r"\((banned|coral|C9 name|ours|nowcast row|rivals)\)", "", raw.strip()).strip().strip('"').strip("'").strip()
        if n and n != '—':
            names.append((n, term))
paper_files = {'paper/draft/S3_posthoc.md', 'paper/draft/S1_disclosures.md', 'paper/draft/S4_provenance.md',
               'paper/draft/GLOSSARY.md', 'paper/draft/REFERENCES.md'}
for rel, edits in applied['edits'].items():
    for eid, old, new in edits:
        for k, rx in P.PATS.items():
            if rx.search(new):
                bad('%s %s: privacy pattern %s in the new text' % (rel, eid, k))
        if rel not in paper_files:
            continue
        nv = visible(new) if new.count('<!--') == new.count('-->') else new
        ov = visible(old) if old.count('<!--') == old.count('-->') else old
        nv2 = re.sub(r"`[^`]*`", " ", nv)
        ov2 = re.sub(r"`[^`]*`", " ", ov)
        hits = []
        for n, term in names:
            pat = re.compile(r"(?<![\w-])" + re.escape(n) + r"s?(?![\w-])", re.I)
            a, b = len(pat.findall(nv2)), len(pat.findall(ov2))
            if a > b:
                hits.append('%s (%s) +%d' % (n, term, a - b))
        nums_new = set(re.findall(r"\d[\d,.]*", nv)) - set(re.findall(r"\d[\d,.]*", ov))
        if hits or nums_new:
            print('%s | %s | added do-not-use names: %s | new number tokens: %s' % (rel, eid, hits, sorted(nums_new)))
        # the build's year-token expression (build_docx.py line 534): a new year token could start a citation
        YEAR_TOKEN_RE = re.compile(r"(?<![\w\-–/.])(?:(?P<y>(?:1[6-9]|20)\d\d[a-z]?)(?![\w])(?![\-–/.]\d)|(?P<nd>n\.d\.))")
        if rel != 'paper/draft/REFERENCES.md':
            ny = [m.group(0) for m in YEAR_TOKEN_RE.finditer(nv)]
            oy = [m.group(0) for m in YEAR_TOKEN_RE.finditer(ov)]
            if sorted(ny) != sorted(oy):
                print('%s | %s | year tokens in visible text: old %s, new %s' % (rel, eid, oy, ny))

# 6. no pointer to the stage folder is left in the 13 files; S4's visible archive paths
for rel in FILES:
    t = (STAGE / rel).read_text(encoding='utf-8')
    n = len(re.findall(r"supp_build[/\\]s3_13[/\\]stage[/\\]", t))
    if n:
        bad('%s: %d pointers to the stage folder' % (rel, n))
s4v = visible((STAGE / 'paper/draft/S4_provenance.md').read_text(encoding='utf-8'))
print('S4 visible paths with supp_build:', sorted(set(re.findall(r"`?[\w/]*supp_build/s3_13/`?", s4v))),
      '| with shap_v1:', sorted(set(re.findall(r"`?analysis/shap_v1/[\w/.]*`?", s4v))))
print('ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED')
