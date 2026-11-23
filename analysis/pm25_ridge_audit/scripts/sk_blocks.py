"""Skeptic check: Ridge's link-space prediction minus normal, split into blocks, mean by test year; plus missing-flag
prevalence train(2017-19 refit rows) vs test. Read-only; all 127 groups; leads 0/6/12."""
import json, numpy as np, pandas as pd, pyarrow.parquet as pq, os
RV = r'D:\treeroute\rivals\pm25\20261007_74e67609'; EX = r'D:\treeroute\rival_export\pm25\20261007_74e67609'
SC = r'D:\treeroute\rivals_scratch\pm25\20261007_74e67609'
groups = sorted(f[:-8] for f in os.listdir(EX + r'\lead_0\test'))
IDX = {'sst/nino/oni/pdo indices': ('sst_anom', 'nino', 'oni', 'tni', 'pdo', 'soi', 'tna', 'tsa', 'iod', 'noi', '__ao', 'nao', 'pna', '__wp', 'epo', 'sam', 'amo')}
for L in (0, 6, 12):
    cols = json.load(open(SC + rf'\lead_{L}_refit.json'))['columns']
    m = json.load(open(RV + rf'\lead_{L}\model_ridge.json'))
    names = m['names']; mu = np.array(m['mean']); coef = np.array(m['coef']['1000.0'])
    raw = cols + ['__normal__']
    vi = [raw.index(n) for n in names if not n.startswith('missing__')]
    fi = [raw.index(n[9:]) for n in names if n.startswith('missing__')]
    imp = np.zeros(len(raw)); imp[vi] = mu[:len(vi)]
    def blk(n):
        if n.startswith('missing__'): return 'flags'
        if 'hist_' in n: return 'history'
        if n == '__normal__': return 'normal'
        b = n[3:] if n.startswith('x__') else n
        if b.startswith('sst_anom') or b.startswith('nino') or b in ('oni', 'tni', 'pdo', 'soi', 'tna', 'tsa', 'iod', 'noi', 'ao', 'nao', 'pna', 'wp', 'epo', 'sam', 'amo_lag12'):
            return 'climate indices'
        return 'other drivers+ctx'
    bl = np.array([blk(n) for n in names]); B = sorted(set(bl))
    acc = []; fl_tr = np.zeros(len(fi)); n_tr = 0; fl_te = np.zeros(len(fi)); n_te = 0
    for g in groups:
        for role in ('test', 'train'):
            cc = ['time'] + cols + (['nfit__log_c'] if True else []) + (['r_refit'] if role == 'train' else [])
            d = pq.read_table(EX + rf'\lead_{L}\{role}\{g}.parquet', columns=cc).to_pandas()
            if role == 'train':
                d = d[d.r_refit.astype(bool) & (d.time >= 24205)]
            r = np.empty((len(d), len(raw))); r[:, :-1] = d[cols].values; r[:, -1] = d.nfit__log_c.values
            nan = np.isnan(r); F = nan[:, fi].astype(float); r = np.where(nan, imp[None, :], r)
            Z = np.concatenate([r[:, vi], F], axis=1) - mu[None, :]
            contrib = Z * coef[None, :]
            out = pd.DataFrame({b: contrib[:, bl == b].sum(1) for b in B}); out['total'] = contrib.sum(1)
            out['year'] = (d.time.values - 1) // 12; out['role'] = role
            acc.append(out)
            if role == 'train': fl_tr += F.sum(0); n_tr += len(F)
            else: fl_te += F.sum(0); n_te += len(F)
    a = pd.concat(acc)
    print(f'== lead {L}: mean link-space contribution (log units) by year; train = refit rows 2017-2019')
    print(a.groupby(['role', 'year'])[B + ['total']].mean().round(4).to_string())
    fn = [n for n in names if n.startswith('missing__')]
    ft = pd.DataFrame({'flag': fn, 'share_train1719': fl_tr / n_tr, 'share_test': fl_te / n_te,
                       'coef_x_1': coef[len(vi):]})
    ft['test_minus_train_contrib'] = (ft.share_test - ft.share_train1719) * ft.coef_x_1
    print(ft.reindex(ft.test_minus_train_contrib.abs().sort_values(ascending=False).index).head(6).round(5).to_string())
