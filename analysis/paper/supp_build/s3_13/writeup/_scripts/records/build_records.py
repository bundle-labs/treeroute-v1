# Build this writer's staged files from the hash-checked base copies in work/base/ (made by stage_copy.py):
#   STAGE/engine/PENDING_PARTS.md, STAGE/_archive_plan/ARCHIVE_MANIFEST_DRAFT.md, STAGE/paper/PAPER_OUTLINE.md and
#   STAGE/shap/PROTOCOL.md. Every edit is an insertion at an exact anchor (asserted unique), except the listed
#   replacements (Part 628's heading; the manifest's 2.5 total row and section 7's three total rows).
# Numbers of the manifest are filled from work/classify.json and work/listing_shap.json, never typed.
# Keeps each file's encoding (UTF-8, no BOM) and LF line endings. Reads only the base copies and the work files.
import os, sys, json, hashlib, collections, re

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.normpath(os.path.join(HERE, '..', '..'))
WORK = os.path.join(HERE, 'work')
BASE = os.path.join(WORK, 'base')
sys.path.insert(0, HERE)
import texts_protocol, texts_pending, texts_outline, texts_manifest  # noqa: E402

BASE_SHA = {
    'engine/PENDING_PARTS.md': '0380e743511a0b02bef1f7f12743eb70f129ade2159adc7ae6ecc38bb9a112fd',
    '_archive_plan/ARCHIVE_MANIFEST_DRAFT.md': '5a6894015ed37a0ceec96a596c4bd7cb69052b0551bbba570fb551a9fcbdace2',
    'paper/PAPER_OUTLINE.md': 'd6d80bd1ee245b54b7dbd2d94ef33ce9545b70b4c45046b9d3c646db33d0ac66',
    'shap/PROTOCOL.md': '32daa77b893cf7af378b3145a285fa71c0cec61b0b3a51420195415658618abc',
}


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read_base(rel):
    p = os.path.join(BASE, rel.replace('/', '__'))
    with open(p, 'rb') as f:
        b = f.read()
    assert sha_bytes(b) == BASE_SHA[rel], 'base changed: ' + rel
    assert not b.startswith(b'\xef\xbb\xbf') and b'\r' not in b and b.endswith(b'\n'), rel
    return b.decode('utf-8')


def write_stage(rel, text):
    b = text.encode('utf-8')
    assert b'\r' not in b and not b.startswith(b'\xef\xbb\xbf') and b.endswith(b'\n') and not b.endswith(b'\n\n'), rel
    p = os.path.join(STAGE, *rel.split('/'))
    with open(p, 'wb') as f:
        f.write(b)
    return sha_bytes(b), len(b)


def once(text, anchor, label):
    n = text.count(anchor)
    assert n == 1, '%s: anchor found %d times: %r' % (label, n, anchor[:90])
    return text.index(anchor)


def apply_edit(text, kind, anchor, new, label):
    i = once(text, anchor, label)
    j = i + len(anchor)
    if kind == 'after':
        return text[:j] + new + text[j:]
    if kind == 'before':
        return text[:i] + new + text[i:]
    if kind == 'replace':
        return text[:i] + new + text[j:]
    if kind == 'append_line':
        assert anchor.endswith('\n')
        return text[:j - 1] + new + '\n' + text[j:]
    raise ValueError(kind)


def fmt(n):
    return format(n, ',')


def tokens():
    with open(os.path.join(WORK, 'classify.json'), encoding='utf-8') as f:
        cl = json.load(f)
    with open(os.path.join(WORK, 'listing_shap.json'), encoding='utf-8') as f:
        ls = json.load(f)
    G, O = cl['shap']['groups'], cl['out']['groups']

    def g(k, f='files'):
        return G[k][f]

    t = {}
    sh_arch = [k for k in G if k.startswith('A')]
    shap_arch_files = sum(G[k]['files'] for k in sh_arch)
    shap_arch_bytes = sum(G[k]['bytes'] for k in sh_arch)
    shap_gh_files = sum(G[k]['github_files'] for k in sh_arch)
    shap_gh_bytes = sum(G[k]['github_bytes'] for k in sh_arch)
    shap_parquet = cl['shap']['archived_ext']['.parquet'][0]
    out_arch = [k for k in O if k.startswith('O-A')]
    out_arch_files = sum(O[k]['files'] for k in out_arch)
    out_arch_bytes = sum(O[k]['bytes'] for k in out_arch)
    out_gh_files = sum(O[k]['github_files'] for k in out_arch)
    out_gh_bytes = sum(O[k]['github_bytes'] for k in out_arch)
    i_keys = [k for k in G if k.startswith('K')]
    i_files = sum(G[k]['files'] for k in i_keys)
    i_bytes = sum(G[k]['bytes'] for k in i_keys)
    assert shap_arch_files + i_files + g('L1 smoke (appendix A)') == cl['shap']['n_files']
    # the old totals, as the base manifest prints them
    OLD = dict(main=(4920, 4562805109), gh=(2231, 118565849), ko=(16703, 43637674656), m5=(7719, 5218791471),
               an=(382, 481916962), an_gh=(305, 10277331), a5=(2799, 655986362))
    main = (OLD['main'][0] + shap_arch_files + out_arch_files, OLD['main'][1] + shap_arch_bytes + out_arch_bytes)
    gh = (OLD['gh'][0] + shap_gh_files + out_gh_files, OLD['gh'][1] + shap_gh_bytes + out_gh_bytes)
    ko = (OLD['ko'][0] + i_files, OLD['ko'][1] + i_bytes)
    m5 = (main[0] + OLD['a5'][0], main[1] + OLD['a5'][1])
    assert OLD['m5'] == (OLD['main'][0] + OLD['a5'][0], OLD['main'][1] + OLD['a5'][1])
    an = (OLD['an'][0] + shap_arch_files + out_arch_files, OLD['an'][1] + shap_arch_bytes + out_arch_bytes)
    an_gh = (OLD['an_gh'][0] + shap_gh_files + out_gh_files, OLD['an_gh'][1] + shap_gh_bytes + out_gh_bytes)
    # smoke engine folders, RF trees per problem, gridded row files per problem
    smoke_eng = [r for r in ls['files'] if r[0].replace('\\', '/').startswith('smoke/') and
                 any(('engine_runs' in c or 'engine_tmp' in c) for c in r[0].replace('\\', '/').split('/')[1:-1])]
    rf = collections.Counter()
    for r in ls['files']:
        p = r[0].replace('\\', '/').split('/')
        if p[0] == 'work' and p[-2] == 'rf_trees' and re.match(r'tree_\d+\.npz$', p[-1]):
            rf[p[1]] += 1
    assert len(set(rf.values())) == 1, rf
    k2 = collections.Counter()
    for r in ls['files']:
        p = r[0].replace('\\', '/').split('/')
        if p[0] == 'out' and len(p) == 5 and p[1] != 'coral' and p[3] != 'compare' and p[4] == 'rows.parquet':
            k2[p[1]] += 1
    assert sum(k2.values()) == g('K2 gridded row-level SHAP values')
    ext_s, ext_o = cl['shap']['archived_ext'], cl['out']['archived_ext']

    def ext(e):
        return ext_s.get(e, [0])[0] + ext_o.get(e, [0])[0]
    largest = max(G['A10 verify_v1']['largest'])[0]
    with open(os.path.join(WORK, 'privacy_count_out.txt'), 'rb') as f:
        raw = f.read()
    ptxt = raw.decode('utf-16') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else raw.decode('utf-8')
    m0 = re.search(r'scan start UTC \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z', ptxt)
    m1 = re.search(r'scan end UTC \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z', ptxt)
    menc = re.search(r"encodings \{'utf-8': (\d+), 'utf-8-sig': (\d+)\}", ptxt)
    mall = re.search(r'ALL\s+files\s+(\d+)\s+(.*)', ptxt)
    assert m0 and m1 and menc and mall and int(mall.group(1)) == out_arch_files
    assert all(int(x) == 0 for x in re.findall(r': (\d+)', mall.group(2))), 'privacy hits'
    t.update({
        'list_start': cl['shap']['listed_utc'][0][11:19], 'list_end': cl['out']['listed_utc'][1][11:19],
        'scan_start': m0.group(1), 'scan_end': m1.group(1),
        'enc_utf8': menc.group(1), 'enc_utf8sig': menc.group(2),
        'shap_all_files': fmt(cl['shap']['n_files']), 'shap_all_bytes': fmt(cl['shap']['bytes']),
        'shap_arch_files': fmt(shap_arch_files), 'shap_arch_bytes': fmt(shap_arch_bytes),
        'shap_gh_files': fmt(shap_gh_files), 'shap_gh_bytes': fmt(shap_gh_bytes), 'shap_parquet_files': fmt(shap_parquet),
        'out_all_files': fmt(cl['out']['n_files']), 'out_all_bytes': fmt(cl['out']['bytes']),
        'out_arch_files': fmt(out_arch_files), 'out_arch_bytes': fmt(out_arch_bytes),
        'stage_files': fmt(O['O-L stage (appendix A)']['files']), 'stage_bytes': fmt(O['O-L stage (appendix A)']['bytes']),
        'a1_files': g('A1 top-level records'), 'a2_files': g('A2 scripts'), 'a3_files': g('A3 logs'),
        'a4_files': g('A4 _snapshots'), 'a6_files': g('A6 compare outputs'), 'a7_files': g('A7 piece records'),
        'a7b_files': g('A7b gridded background keys'), 'a8_files': g('A8 gridded samples'),
        'a8b_files': g('A8b coral sample manifest'), 'a9_files': g('A9 rebuild records'),
        'a9b_files': g('A9b gridded rebuild check files'), 'a10_files': g('A10 verify_v1'),
        'i_files': fmt(i_files), 'i_bytes': fmt(i_bytes),
        'k1_files': fmt(g('K1 coral row-level files')), 'k1_bytes': fmt(g('K1 coral row-level files', 'bytes')),
        'k2_files': fmt(g('K2 gridded row-level SHAP values')), 'k2_bytes': fmt(g('K2 gridded row-level SHAP values', 'bytes')),
        'k2_fire': k2['fire'], 'k2_pm25': k2['pm25'], 'k2_defo': k2['defo'], 'k2_ndvi': k2['ndvi'],
        'k3_files': fmt(g('K3 engine_runs')), 'k3_bytes': fmt(g('K3 engine_runs', 'bytes')),
        'k4a_files': fmt(g('K4a rebuilt banks and routers')), 'k4a_bytes': fmt(g('K4a rebuilt banks and routers', 'bytes')),
        'k4b_files': fmt(g('K4b rebuilt random forests (work)')),
        'k4b_bytes': fmt(g('K4b rebuilt random forests (work)', 'bytes')),
        'k4_files': fmt(g('K4a rebuilt banks and routers') + g('K4b rebuilt random forests (work)')),
        'k4_bytes': fmt(g('K4a rebuilt banks and routers', 'bytes') + g('K4b rebuilt random forests (work)', 'bytes')),
        'rf_trees': fmt(list(rf.values())[0]),
        'k5a_files': g('K5a compare bootstrap_draws.npy'), 'k5b_files': g('K5b verify_v1 NumPy'),
        'k5c_files': g('K5c verify_v1 compressed'),
        'k5_files': fmt(g('K5a compare bootstrap_draws.npy') + g('K5b verify_v1 NumPy') + g('K5c verify_v1 compressed')),
        'k5_bytes': fmt(g('K5a compare bootstrap_draws.npy', 'bytes') + g('K5b verify_v1 NumPy', 'bytes') +
                        g('K5c verify_v1 compressed', 'bytes')),
        'smoke_files': fmt(g('L1 smoke (appendix A)')), 'smoke_bytes': fmt(g('L1 smoke (appendix A)', 'bytes')),
        'smoke_eng_files': fmt(len(smoke_eng)), 'smoke_eng_bytes': fmt(sum(r[1] for r in smoke_eng)),
        'rowlevel_files': fmt(g('A7b gridded background keys') + ext_parquet_count(G['A8 gridded samples']) +
                              g('A9b gridded rebuild check files')),
        'main_files': fmt(main[0]), 'main_bytes': fmt(main[1]), 'main_gb': '%.2f' % (main[1] / 1e9),
        'main_gib': '%.2f' % (main[1] / 2 ** 30),
        'm5_files': fmt(m5[0]), 'm5_bytes': fmt(m5[1]), 'm5_gb': '%.2f' % (m5[1] / 1e9), 'm5_gib': '%.2f' % (m5[1] / 2 ** 30),
        'gh_files': fmt(gh[0]), 'gh_bytes': fmt(gh[1]), 'gh_gb': '%.2f' % (gh[1] / 1e9), 'gh_gib': '%.2f' % (gh[1] / 2 ** 30),
        'ko_files': fmt(ko[0]), 'ko_bytes': fmt(ko[1]),
        'an_files': fmt(an[0]), 'an_bytes': fmt(an[1]), 'an_gh_files': fmt(an_gh[0]), 'an_gh_bytes': fmt(an_gh[1]),
        'an_mb': '%.1f' % (an[1] / 1e6),
        'add_files': fmt(shap_arch_files + out_arch_files), 'add_bytes': fmt(shap_arch_bytes + out_arch_bytes),
        'add_gh_files': fmt(shap_gh_files + out_gh_files), 'add_gh_bytes': fmt(shap_gh_bytes + out_gh_bytes),
        'ext_py': fmt(ext('.py')), 'ext_py_shap': fmt(ext_s['.py'][0]), 'ext_py_out': fmt(ext_o['.py'][0]),
        'ext_json': fmt(ext('.json')), 'ext_parquet': fmt(ext('.parquet')), 'ext_md': fmt(ext('.md')),
        'ext_log': fmt(ext('.log')), 'ext_txt': fmt(ext('.txt')), 'ext_jsonl': fmt(ext('.jsonl')),
        'ext_yaml': fmt(ext('.yaml')),
        'ext_before': ext('.before_fix1') + ext('.before_fix2') + ext('.before_fix3'),
        'ext_md_out': ext_o['.md'][0], 'ext_json_out': ext_o['.json'][0], 'ext_txt_out': ext_o['.txt'][0],
        'py_bytes': fmt(ext_s['.py'][1] + ext_o['.py'][1]),
        'mism_bytes': fmt(largest),
        'stage_need_gb': '%.1f' % (main[1] / 1e9), 'stage_need_5a_gb': '%.1f' % (m5[1] / 1e9),
    })
    t['rowlevel_bytes'] = fmt(G['A7b gridded background keys']['bytes'] + parquet_bytes_of_samples(ls) +
                              G['A9b gridded rebuild check files']['bytes'])
    total_ext = sum(v[0] for v in ext_s.values()) + sum(v[0] for v in ext_o.values())
    assert total_ext == shap_arch_files + out_arch_files
    return {k: str(v) for k, v in t.items()}


def ext_parquet_count(grp):
    return grp['ext'].get('.parquet', 0)


def parquet_bytes_of_samples(ls):
    tot = 0
    for r in ls['files']:
        p = r[0].replace('\\', '/').split('/')
        if p[0] == 'sample' and p[1] != 'coral' and p[-1].endswith('.parquet'):
            tot += r[1]
    return tot


def fill(text, t):
    out = re.sub(r'<<([a-z0-9_]+)>>', lambda m: t[m.group(1)], text)
    assert '<<' not in out and '>>' not in out.replace('->', ''), 'unfilled token'
    return out


def main():
    t = tokens()
    results = {}
    # 1. PROTOCOL.md: append the entry at the end of section 14 (the end of the file)
    rel = 'shap/PROTOCOL.md'
    base = read_base(rel)
    assert base.endswith('nothing in this entry changes that label.\n')
    new = base + texts_protocol.ENTRY
    results[rel] = (base, new)
    # 2. PENDING_PARTS.md: Part 628's heading, then the addendum at the end of Part 628 (the end of the file)
    rel = 'engine/PENDING_PARTS.md'
    base = read_base(rel)
    new = apply_edit(base, 'replace', texts_pending.HEADING_OLD, texts_pending.HEADING_NEW, rel)
    tail = 'It registers the coral sample and so freezes protocol sections 3 and 8.\n'
    assert new.endswith(tail)
    new = new + texts_pending.ADDENDUM
    results[rel] = (base, new)
    # 3. PAPER_OUTLINE.md: O3's RULED bullet
    rel = 'paper/PAPER_OUTLINE.md'
    base = read_base(rel)
    new = apply_edit(base, 'after', texts_outline.O3_LINE, texts_outline.O3_BULLET, rel)
    results[rel] = (base, new)
    # 4. ARCHIVE_MANIFEST_DRAFT.md
    rel = '_archive_plan/ARCHIVE_MANIFEST_DRAFT.md'
    base = read_base(rel)
    new = base
    for n, (kind, anchor, text) in enumerate(texts_manifest.EDITS):
        new = apply_edit(new, kind, anchor, fill(text, t), '%s edit %d' % (rel, n + 1))
    assert new.endswith('kept out (15:20 UTC), 16,703 files, 43,637,674,656 B.\n')
    new = new + fill(texts_manifest.APPENDIX_B, t)
    results[rel] = (base, new)
    for rel, (base, new) in results.items():
        h, n = write_stage(rel, new)
        print('%-42s base %s -> staged %s (%d bytes, +%d)' % (rel, BASE_SHA[rel][:12], h, n, n - len(base.encode('utf-8'))))
    with open(os.path.join(WORK, 'tokens.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(t, f, indent=1, sort_keys=True)


if __name__ == '__main__':
    main()
