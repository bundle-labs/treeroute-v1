# Classify the os.stat listings of SHAP and OUT (work/listing_*.json) into the archive plan's groups, by rule.
# Reads only the two listing files; writes work/classify.json; prints counts and bytes per group.
# Rules (archive plan, 2026-11-17, S3.13 write-up):
#   SHAP archived: top-level records; scripts/; logs/; _snapshots/; out/<p>/RUN_SUMMARY_*.json; compare/ without the
#     NumPy draws; every piece's records (meta.json, exactness.json, ridge_shap_exactness.json, rows.parquet.done.json);
#     the gridded pieces' background_keys.parquet; sample/ of the four gridded problems and coral's sample_manifest.json;
#     rebuild/<p>/lead_0/ records (gates.json, DONE.json, precheck.json) and the gridded preds_check.parquet and
#     rows.parquet; verify_v1/ without *.npz and *.gz.
#   SHAP kept out: coral row-level files (D13); the gridded pieces' rows.parquet (row-level SHAP values; a default);
#     engine_runs/ (D13, account name); rebuilt models (rebuild/*/bank.npz, routers.npz; work/); NumPy and compressed
#     record files (compare/bootstrap_draws.npy; verify_v1 *.npz, *.gz).
#   SHAP left out (appendix A): smoke/ (bardl_fix/ not entered, not counted).
#   OUT archived: spec/, A/, B/, reconcile/, skeptic/, _brief/. OUT left out (appendix A): stage/.
# GitHub part: archived files that are not Parquet and are under 25 MiB (the analysis/ rule of section 1).
import os, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
GRIDDED = ('pm25', 'ndvi', 'fire', 'defo')
MIB25 = 25 * 1024 * 1024


def ext_of(rel):
    base = rel.rsplit('/', 1)[-1]
    return '.' + base.rsplit('.', 1)[-1].lower() if '.' in base else '(none)'


def shap_group(rel):
    p = rel.split('/')
    top = p[0]
    name = p[-1]
    ext = ext_of(rel)
    if len(p) == 1:
        return 'A1 top-level records'
    if top == 'scripts':
        return 'A2 scripts'
    if top == 'logs':
        return 'A3 logs'
    if top == '_snapshots':
        return 'A4 _snapshots'
    if top == 'engine_runs':
        return 'K3 engine_runs'
    if top == 'work':
        return 'K4b rebuilt random forests (work)'
    if top == 'smoke':
        return 'L1 smoke (appendix A)'
    if top == 'out':
        prob = p[1]
        if len(p) == 3:
            return 'A5 out run summaries'
        model = p[3]
        if model == 'compare':
            return 'K5a compare bootstrap_draws.npy' if name == 'bootstrap_draws.npy' else 'A6 compare outputs'
        if name in ('meta.json', 'exactness.json', 'ridge_shap_exactness.json', 'rows.parquet.done.json'):
            return 'A7 piece records'
        if name in ('rows.parquet', 'background_keys.parquet'):
            if prob == 'coral':
                return 'K1 coral row-level files'
            if name == 'background_keys.parquet':
                return 'A7b gridded background keys'
            return 'K2 gridded row-level SHAP values'
        return 'UNCLASSIFIED'
    if top == 'sample':
        prob = p[1]
        if prob == 'coral':
            return 'A8b coral sample manifest' if name == 'sample_manifest.json' else 'K1 coral row-level files'
        return 'A8 gridded samples'
    if top == 'rebuild':
        prob = p[1]
        if name in ('gates.json', 'DONE.json', 'precheck.json'):
            return 'A9 rebuild records'
        if name in ('bank.npz', 'routers.npz'):
            return 'K4a rebuilt banks and routers'
        if prob == 'coral':
            return 'K1 coral row-level files'
        if name in ('preds_check.parquet', 'rows.parquet'):
            return 'A9b gridded rebuild check files'
        return 'UNCLASSIFIED'
    if top == 'verify_v1':
        if ext == '.npz':
            return 'K5b verify_v1 NumPy'
        if ext == '.gz':
            return 'K5c verify_v1 compressed'
        return 'A10 verify_v1'
    return 'UNCLASSIFIED'


def out_group(rel):
    top = rel.split('/')[0]
    if top in ('spec', 'A', 'B', 'reconcile', 'skeptic', '_brief'):
        return 'O-A ' + top
    if top == 'stage':
        return 'O-L stage (appendix A)'
    return 'UNCLASSIFIED'


def summarise(rows, fn):
    g = collections.OrderedDict()
    for rel, size, mt, rp in rows:
        rel = rel.replace('\\', '/')
        k = fn(rel)
        d = g.setdefault(k, {'files': 0, 'bytes': 0, 'ext': collections.Counter(), 'github_files': 0,
                             'github_bytes': 0, 'largest': []})
        d['files'] += 1
        d['bytes'] += size
        d['ext'][ext_of(rel)] += 1
        if k.startswith(('A', 'O-A')) and ext_of(rel) != '.parquet' and size < MIB25:
            d['github_files'] += 1
            d['github_bytes'] += size
        d['largest'].append((size, rel))
    for d in g.values():
        d['largest'] = sorted(d['largest'], reverse=True)[:3]
        d['ext'] = dict(d['ext'])
    return g


def main():
    res = {}
    for name, fn in (('shap', shap_group), ('out', out_group)):
        with open(os.path.join(HERE, 'work', 'listing_%s.json' % name), encoding='utf-8') as f:
            rec = json.load(f)
        g = summarise(rec['files'], fn)
        res[name] = {'listed_utc': [rec['listed_utc_start'], rec['listed_utc_end']], 'groups': g,
                     'pruned_not_entered': rec['pruned_not_entered'], 'n_files': len(rec['files']),
                     'bytes': sum(r[1] for r in rec['files'])}
        print('==', name, res[name]['listed_utc'], 'files', res[name]['n_files'], 'bytes', format(res[name]['bytes'], ','))
        tot = collections.Counter()
        for k in sorted(g):
            d = g[k]
            print('%-42s %6d %15s  gh %5d %13s  %s' % (k, d['files'], format(d['bytes'], ','), d['github_files'],
                                                     format(d['github_bytes'], ','), d['ext']))
            cls = 'archived' if k.startswith(('A', 'O-A')) else ('kept out' if k.startswith('K') else 'appendix A' if k.startswith(('L', 'O-L')) else k)
            tot[cls + ' files'] += d['files']
            tot[cls + ' bytes'] += d['bytes']
            if cls == 'archived':
                tot['github files'] += d['github_files']
                tot['github bytes'] += d['github_bytes']
        for k in sorted(tot):
            print('   %-22s %s' % (k, format(tot[k], ',')))
        res[name]['totals'] = dict(tot)
        arch_ext = collections.Counter()
        arch_ext_b = collections.Counter()
        gh_ext = collections.Counter()
        for rel, size, mt, rp in rec['files']:
            rel = rel.replace('\\', '/')
            k = fn(rel)
            if k.startswith(('A', 'O-A')):
                arch_ext[ext_of(rel)] += 1
                arch_ext_b[ext_of(rel)] += size
                if ext_of(rel) != '.parquet' and size < MIB25:
                    gh_ext[ext_of(rel)] += 1
        res[name]['archived_ext'] = {e: [arch_ext[e], arch_ext_b[e], gh_ext[e]] for e in sorted(arch_ext)}
        print('   archived by extension:', res[name]['archived_ext'])
        big = sorted(((r[1], r[0]) for r in rec['files'] if fn(r[0].replace('\\', '/')).startswith(('A', 'O-A'))), reverse=True)[:6]
        print('   largest archived:', big)
    with open(os.path.join(HERE, 'work', 'classify.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(res, f, indent=1, default=list)


if __name__ == '__main__':
    main()
