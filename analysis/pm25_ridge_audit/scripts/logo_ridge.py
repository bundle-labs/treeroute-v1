"""Skeptic check: does pooled Ridge's PM2.5 win survive when it is denied the test unit's own group?
Read-only. One pass over the lead's refit .f32 (memmap slices only) accumulating per-group sufficient
statistics, then refits Ridge (alpha 1000, log_c, the harness's exact design rules) with variants.
Usage: py -3.9 -I logo_ridge.py <lead>
"""
import sys, json, time, numpy as np, pandas as pd, pyarrow.parquet as pq

L = int(sys.argv[1])
S = r'D:/treeroute/rivals_scratch/pm25/20261007_74e67609'
B = r'D:/treeroute/rivals/pm25/20261007_74e67609'
E = r'D:/treeroute/rival_export/pm25/20261007_74e67609'
R = r'D:/treeroute/runs/pm25/headline/20261007_74e67609'
OUT = sys.argv[2] if len(sys.argv) > 2 else None
C = 1.5
ALPHA = 1000.0
CH = 32768

t0 = time.time()
meta = json.load(open(f'{S}/lead_{L}_refit.json'))
cols = meta['columns']; P = len(cols); N = meta['rows']
X = np.memmap(f'{S}/lead_{L}_refit.f32', dtype=np.float32, mode='r', shape=(N, P))
model = json.load(open(f'{B}/lead_{L}/model_ridge.json'))
raw = cols + ['__normal__']
assert model['dropped'] == []
assert model['names'][:P + 1] == raw, 'model kept columns != raw order'
flags = [f[len('missing__'):] for f in model['flags']]
Fidx = [raw.index(f) for f in flags]
nF = len(Fidx)
s = np.array(model['mean'][:P + 1], dtype=np.float64)   # shift = full-model means
D = P + 1 + nF + 2
i1, iT = P + 1 + nF, P + 2 + nF

idx = pq.read_table(f'{S}/lead_{L}_refit.index.parquet', columns=['unit', 'group', 'y', 'n__log_c']).to_pandas()
gcat = idx['group'].astype('category'); groups = list(gcat.cat.categories); gc = gcat.cat.codes.to_numpy()
ucat = idx['unit'].astype('category'); units_all = list(ucat.cat.categories); uc = ucat.cat.codes.to_numpy()
y = idx['y'].to_numpy(np.float64); nrm = idx['n__log_c'].to_numpy(np.float64)
tgt = np.log(y + C) - nrm
assert np.isfinite(tgt).all()
del idx
G = len(groups)
GG = np.zeros((G, D, D)); lo = np.full((G, P + 1), np.inf); hi = np.full((G, P + 1), -np.inf)

def amat(blk, a, b):
    nanm = np.isnan(blk)
    A = np.empty((b - a, D))
    xs = blk - s[None, :P]; xs[nanm] = 0.0
    A[:, :P] = xs
    A[:, P] = nrm[a:b] - s[P]
    full_nan = np.concatenate([nanm, np.zeros((b - a, 1), bool)], axis=1)
    A[:, P + 1:P + 1 + nF] = full_nan[:, Fidx]
    A[:, i1] = 1.0; A[:, iT] = tgt[a:b]
    if (nanm.any(axis=0) & ~np.isin(np.arange(P), Fidx)).any():
        raise SystemExit('a column has NaN but no flag in the saved model')
    vals = np.concatenate([blk, (nrm[a:b])[:, None]], axis=1)
    return A, vals, full_nan

for a in range(0, N, CH):
    b = min(N, a + CH)
    blk = np.asarray(X[a:b], dtype=np.float64)
    A, vals, nanm = amat(blk, a, b)
    g = gc[a:b]
    cut = np.flatnonzero(np.diff(g)) + 1
    starts = np.r_[0, cut]; ends = np.r_[cut, b - a]
    for st, en in zip(starts, ends):
        k = g[st]
        Ar = A[st:en]
        GG[k] += Ar.T @ Ar
        v = vals[st:en]; m = nanm[st:en]
        lo[k] = np.minimum(lo[k], np.where(m, np.inf, v).min(0))
        hi[k] = np.maximum(hi[k], np.where(m, -np.inf, v).max(0))
print(f'lead {L}: pass done {time.time()-t0:.0f}s, N {N}, P {P}, flags {nF}, groups {G}', flush=True)
GT = GG.sum(0); loT = lo.min(0); hiT = hi.max(0)


def fit(Gm, lo_, hi_, drop_raw=(), drop_flags=False):
    n = Gm[i1, i1]; St = Gm[i1, iT]
    sums = Gm[i1, :]
    nan_cnt = np.zeros(P + 1); nan_cnt[Fidx] = sums[P + 1:P + 1 + nF]
    cnt = n - nan_cnt
    delta = np.where(cnt > 0, sums[:P + 1] / np.maximum(cnt, 1), 0.0)
    keep = [j for j in range(P + 1) if cnt[j] > 0 and lo_[j] < hi_[j] and raw[j] not in drop_raw]
    fl = [k for k, j in enumerate(Fidx) if 0 < nan_cnt[j] < n and not drop_flags and raw[j] not in drop_raw]
    q = len(keep) + len(fl)
    T = np.zeros((q, D))
    for r, j in enumerate(keep):
        T[r, j] = 1.0
        if j in Fidx:
            T[r, P + 1 + Fidx.index(j)] = delta[j]
    for r2, k in enumerate(fl):
        T[len(keep) + r2, P + 1 + k] = 1.0
    Sdd = T @ Gm @ T.T
    Sd = T @ Gm[:, i1]
    Sdt = T @ Gm[:, iT]
    mu = Sd / n
    Cm = Sdd - n * np.outer(mu, mu)
    gv = Sdt - mu * St
    sd = np.sqrt(np.diag(Cm) / n)
    if not (sd > 0).all():
        raise SystemExit('sd 0')
    A = Cm / np.outer(sd, sd); bv = gv / sd
    Lc = np.linalg.cholesky(A + ALPHA * np.eye(q))
    w = np.linalg.solve(Lc.T, np.linalg.solve(Lc, bv)) / sd
    true_mu_val = s + delta
    names = [raw[j] for j in keep] + ['missing__' + raw[Fidx[k]] for k in fl]
    dmean = np.r_[true_mu_val[keep], nan_cnt[[Fidx[k] for k in fl]] / n]
    return dict(keep=keep, fl=fl, w=w, tbar=St / n, imp=true_mu_val, dmean=dmean, names=names, n=n)


def predict(m, Xs, z0):
    """Xs: score rows raw [x (P) | normal]; z0: offset (n__log_c)."""
    nan = np.isnan(Xs)
    V = np.where(nan, m['imp'][None, :], Xs)
    Dm = np.concatenate([V[:, m['keep']], nan[:, [Fidx[k] for k in m['fl']]].astype(float)], axis=1)
    z = m['tbar'] + (Dm - m['dmean'][None, :]) @ m['w']
    return np.maximum(np.exp(z0 + z) - C, 0.0), np.exp(z0 + z) - C

# 1) full refit reproduces the saved model
full = fit(GT, loT, hiT)
saved_w = np.array(model['coef']['1000.0']); saved_names = model['names']
mine = dict(zip(full['names'], full['w']))
dif = max(abs(mine[nm] - w) / (abs(w) + 1e-12) for nm, w in zip(saved_names, saved_w))
print(f'  full refit vs saved coef: names equal {full["names"] == saved_names}, max rel diff {dif:.2e}, intercept {full["tbar"]:.3e} vs {model["intercept"]:.3e}')

variants = {
    'full': lambda g, u: (GT, loT, hiT, {}),
    'full_nolat': lambda g, u: (GT, loT, hiT, dict(drop_raw=('c__ctx:lat',))),
    'full_noflags_noctx': lambda g, u: (GT, loT, hiT, dict(drop_raw=('c__ctx:lat', 'c__ctx:month'), drop_flags=True)),
    'full_nohist': lambda g, u: (GT, loT, hiT, dict(drop_raw=tuple('x__hist_' + h for h in ('last_1', 'last_2', 'last_3', 'mean_12', 'mean_60', 'mean_all')))),
}
fixed = {k: fit(*v(None, None)[:3], **v(None, None)[3]) for k, v in variants.items()}

# test rows + labels + ours
tp_path = f'{R}/test_preds.parquet' if L == 0 else f'{R}/ladder/lead_{L}/test_preds.parquet'
head_col = 'arm__identity_trees_off_unweighted' if L == 12 else 'arm__log_c_corrector_unweighted'
tp = pq.read_table(tp_path, columns=list(dict.fromkeys(['unit', 'group', 'time', 'lead', 'y', 'arm__log_c_corrector_unweighted', head_col,
                                     'arm__log_c_trees_off_unweighted', 'base__last5_normal', 'base__guess_normal']))).to_pandas()
rp = pq.read_table(f'{B}/lead_{L}/preds_ridge.parquet', columns=['unit', 'time', 'lead', 'pre__rival_ridge', 'arm__rival_ridge_raw']).to_pandas()
for c_ in ('unit', 'group'):
    tp[c_] = tp[c_].astype(str)
rp['unit'] = rp['unit'].astype(str)

# per-unit own-row ranges in the refit index (rows are contiguous per unit?)
ustart = {}; uend = {}
cut = np.flatnonzero(np.diff(uc)) + 1
st_all = np.r_[0, cut]; en_all = np.r_[cut, N]
for st, en in zip(st_all, en_all):
    nm = units_all[uc[st]]
    if nm in ustart:
        raise SystemExit('unit rows not contiguous: ' + nm)
    ustart[nm] = st; uend[nm] = en

rows_out = []
for gi, gname in enumerate(groups):
    te = pq.read_table(f'{E}/lead_{L}/test/{gname}.parquet').to_pandas()
    te['unit'] = te['unit'].astype(str)
    Xs = np.concatenate([te[cols].to_numpy(np.float64), te[['nfit__log_c']].to_numpy(np.float64)], axis=1)
    z0 = te['nfit__log_c'].to_numpy(np.float64)
    Xs[:, P] = z0
    res = pd.DataFrame({'unit': te['unit'], 'time': te['time'].astype(np.int64), 'lead': te['lead'].astype(np.int64)})
    for k, m in fixed.items():
        res['p_' + k], pre = predict(m, Xs, z0)
        if k == 'full':
            res['pre_full'] = pre
    Glogo = GT - GG[gi]
    lo_r = np.delete(lo, gi, 0).min(0); hi_r = np.delete(hi, gi, 0).max(0)
    m_logo = fit(Glogo, lo_r, hi_r)
    res['p_logo'], _ = predict(m_logo, Xs, z0)
    m_logo_s = fit(Glogo, lo_r, hi_r, drop_raw=('c__ctx:lat',), drop_flags=True)
    res['p_logo_strict'], _ = predict(m_logo_s, Xs, z0)
    # LOGO + the scored unit's own pre-cut rows (what our per-unit router sees)
    po = np.full(len(te), np.nan); pos = np.full(len(te), np.nan)
    for un in te['unit'].unique():
        a, b = ustart[un], uend[un]
        blk = np.asarray(X[a:b], dtype=np.float64)
        A, vals, nanm = amat(blk, a, b)
        Gu = A.T @ A
        lo_u = np.minimum(lo_r, np.where(nanm, np.inf, vals).min(0)); hi_u = np.maximum(hi_r, np.where(nanm, -np.inf, vals).max(0))
        mu_ = fit(Glogo + Gu, lo_u, hi_u)
        mus = fit(Glogo + Gu, lo_u, hi_u, drop_raw=('c__ctx:lat',), drop_flags=True)
        sel = (te['unit'] == un).to_numpy()
        po[sel] = predict(mu_, Xs[sel], z0[sel])[0]
        pos[sel] = predict(mus, Xs[sel], z0[sel])[0]
    res['p_logo_own'] = po; res['p_logo_own_strict'] = pos
    res['group'] = gname
    rows_out.append(res)
    if gi % 20 == 0:
        print(f'  group {gi} {gname} done {time.time()-t0:.0f}s', flush=True)

P_ = pd.concat(rows_out, ignore_index=True)
j = tp.merge(P_, on=['unit', 'time', 'lead'], how='inner', suffixes=('', '_x'), validate='one_to_one')
j = j.merge(rp, on=['unit', 'time', 'lead'], how='inner', validate='one_to_one')
print(f'  joined rows {len(j)} (saved {len(tp)}, ridge {len(rp)}); reproduce saved pre-clip: max |diff| {np.abs(j["pre_full"] - j["pre__rival_ridge"]).max():.3e}')
j = j[np.isfinite(j['y'])].copy()
yv = j['y'].to_numpy()


def jk(d):
    n = len(d); m = d.mean(); loo = (d.sum() - d) / (n - 1)
    se = np.sqrt((n - 1) / n * ((loo - loo.mean()) ** 2).sum())
    return m, m - 1.96 * se, m + 1.96 * se

cands = {'ours_pinned': 'arm__log_c_corrector_unweighted', 'ours_headline': head_col, 'saved_ridge': 'arm__rival_ridge_raw',
         'log_c_trees_off': 'arm__log_c_trees_off_unweighted', 'last5_normal': 'base__last5_normal'}
for k in ['full', 'full_nolat', 'full_noflags_noctx', 'full_nohist', 'logo', 'logo_strict', 'logo_own', 'logo_own_strict']:
    cands['ridge_' + k] = 'p_' + k
for k, c_ in cands.items():
    j['e_' + k] = np.abs(j[c_].to_numpy() - yv)
gm = j.groupby('group')[['e_' + k for k in cands]].mean()
print(f'  lead {L}: rows {len(j)}, groups {len(gm)}')
summary = {}
for k in cands:
    mae = j['e_' + k].mean()
    d_p = jk((gm['e_' + k] - gm['e_ours_pinned']).to_numpy())
    d_h = jk((gm['e_' + k] - gm['e_ours_headline']).to_numpy())
    wins = int(((gm['e_' + k] - gm['e_ours_pinned']) < 0).sum())
    summary[k] = dict(mae=mae, d_pinned=d_p, d_headline=d_h, wins_vs_pinned=wins)
    print(f'   {k:26s} MAE {mae:.4f} | d vs pinned {d_p[0]:+.4f} [{d_p[1]:+.4f}, {d_p[2]:+.4f}] wins {wins}/127 | d vs headline {d_h[0]:+.4f} [{d_h[1]:+.4f}, {d_h[2]:+.4f}]')
# per group: how much LOGO changes Ridge in the driver groups
for gname in ('north_china_plain', 'pearl_river_delta'):
    if gname in gm.index:
        r = gm.loc[gname]
        print(f'   {gname}: ours {r.e_ours_pinned:.3f} ridge_full {r.e_ridge_full:.3f} logo {r.e_ridge_logo:.3f} logo_own {r.e_ridge_logo_own:.3f} logo_own_strict {r.e_ridge_logo_own_strict:.3f}')
if OUT:
    json.dump({k: {kk: (list(vv) if isinstance(vv, tuple) else vv) for kk, vv in v.items()} for k, v in summary.items()}, open(OUT, 'w'), indent=1)
print(f'  total {time.time()-t0:.0f}s')
