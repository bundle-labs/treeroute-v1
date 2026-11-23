"""Skeptic check: leave-one-GROUP-out Ridge at one lead, exact up to the imputation means (kept at the full-fit values).
1) stream the harness's refit .f32 (memmap, blocks), accumulate per-group centred cross-products of the Ridge design;
2) per-group nan-aware column sums/counts of the .f32 -> compare with the export train r_refit rows (all groups);
3) full fit from the totals -> compare sd/coef with model_ridge.json and test predictions with preds_ridge.parquet;
4) for each group h, refit without group h's rows; predict group h's test rows; score vs labels and vs ours.
Read-only. Usage: py -3.9 -I sk_logo.py <lead> <out_csv>"""
import sys, json, numpy as np, pandas as pd, pyarrow.parquet as pq
L = int(sys.argv[1]); OUT = sys.argv[2]
SC = r'D:\treeroute\rivals_scratch\pm25\20261007_74e67609'
RV = r'D:\treeroute\rivals\pm25\20261007_74e67609'
EX = r'D:\treeroute\rival_export\pm25\20261007_74e67609'
RUN = r'D:\treeroute\runs\pm25\headline\20261007_74e67609'
meta = json.load(open(SC + rf'\lead_{L}_refit.json'))
cols = meta['columns']; P = len(cols); N = meta['rows']
idx = pq.read_table(SC + rf'\lead_{L}_refit.index.parquet', columns=['group', 'time', 'y', 'n__log_c'], read_dictionary=['group']).to_pandas()
assert len(idx) == N
X = np.memmap(SC + rf'\lead_{L}_refit.f32', dtype=np.float32, mode='r', shape=(N, P))
c = json.load(open(RUN + r'\derived.json'))[f'R23:lead={L}']
cval = None
for k in ('value',):
    v = c.get(k)
    cval = v.get('c') if isinstance(v, dict) else v
print('R23 value', c.get('value'))
cval = float(cval)
m = json.load(open(RV + rf'\lead_{L}\model_ridge.json'))
names = m['names']; mu = np.array(m['mean']); sd_saved = np.array(m['sd']); coef_saved = np.array(m['coef']['1000.0'])
raw_names = cols + ['__normal__']
val_idx = [raw_names.index(n) for n in names if not n.startswith('missing__')]
flag_idx = [raw_names.index(n[len('missing__'):]) for n in names if n.startswith('missing__')]
nv = len(val_idx)
imp = np.zeros(len(raw_names)); imp[val_idx] = mu[:nv]       # imputation mean = design mean of value columns
q = len(names)

def design(src, normal):
    raw = np.empty((src.shape[0], len(raw_names))); raw[:, :-1] = src; raw[:, -1] = normal
    nan = np.isnan(raw)
    fl = nan[:, flag_idx].astype(np.float64)
    raw = np.where(nan, imp[None, :], raw)
    return np.concatenate([raw[:, val_idx], fl], axis=1) - mu[None, :]

t_all = np.log(idx.y.values + cval) - idx.n__log_c.values
groups = sorted(map(str, idx.group.unique())); gi = {g: i for i, g in enumerate(groups)}; G = len(groups)
gcode = idx.group.astype(str).map(gi).values.astype(np.int64)
S = np.zeros((G, q, q)); s1 = np.zeros((G, q)); n_g = np.zeros(G); T1 = np.zeros(G); ZT = np.zeros((G, q))
xs = np.zeros((G, P)); xc = np.zeros((G, P), dtype=np.int64)
B = 50_000
for a in range(0, N, B):
    b = min(N, a + B)
    src = np.asarray(X[a:b], dtype=np.float64)
    Z = design(src, idx.n__log_c.values[a:b]); t = t_all[a:b]; gc = gcode[a:b]
    for g in np.unique(gc):
        r = gc == g; Zg = Z[r]
        S[g] += Zg.T @ Zg; s1[g] += Zg.sum(0); n_g[g] += r.sum(); T1[g] += t[r].sum(); ZT[g] += Zg.T @ t[r]
        sg = src[r]; ok = ~np.isnan(sg)
        xs[g] += np.where(ok, sg, 0).sum(0); xc[g] += ok.sum(0)
    if (a // B) % 5 == 0:
        print('block', a, flush=True)
del X

def solve(St, s, n, Tt, ZTt, alpha=1000.0):
    zbar = s / n; tbar = Tt / n
    C = St - n * np.outer(zbar, zbar)
    gv = ZTt - n * zbar * tbar
    sd = np.sqrt(np.clip(np.diag(C), 0, None) / n)
    ok = sd > 0
    A = C[np.ix_(ok, ok)] / np.outer(sd[ok], sd[ok]); bv = gv[ok] / sd[ok]
    Lc = np.linalg.cholesky(A + alpha * np.eye(ok.sum()))
    w = np.linalg.solve(Lc.T, np.linalg.solve(Lc, bv))
    coef = np.zeros(len(s)); coef[ok] = w / sd[ok]
    return coef, zbar, tbar, sd

St, s_t, n_t, T_t, ZT_t = S.sum(0), s1.sum(0), n_g.sum(), T1.sum(), ZT.sum(0)
coef_f, zbar_f, tbar_f, sd_f = solve(St, s_t, n_t, T_t, ZT_t)
print('n', n_t, 'max|sd-saved|/sd', np.max(np.abs(sd_f - sd_saved) / sd_saved), 'max|coef*sd - saved*sd|', np.max(np.abs((coef_f - coef_saved) * sd_saved)), 'tbar', tbar_f, 'saved intercept', m['intercept'])

# export train r_refit sums per group (closes the .f32 content check on every group)
maxrel = 0.0; cntbad = 0; worst = None
for g in groups:
    tr = pq.read_table(EX + rf'\lead_{L}\train\{g}.parquet', columns=['r_refit'] + cols).to_pandas()
    tr = tr[tr.r_refit.astype(bool)]
    e = tr[cols].values.astype(np.float64); ok = ~np.isnan(e)
    es = np.where(ok, e, 0).sum(0); ec = ok.sum(0)
    if (ec != xc[gi[g]]).any():
        cntbad += 1
    rel = np.abs(es - xs[gi[g]]) / np.maximum(1e-9, np.abs(es) + 1e-6)
    if rel.max() > maxrel:
        maxrel = rel.max(); worst = (g, cols[int(rel.argmax())])
    if len(tr) != n_g[gi[g]]:
        print('ROWCOUNT MISMATCH', g, len(tr), n_g[gi[g]])
print('f32 vs export: groups with non-NaN count mismatch', cntbad, 'max rel sum diff', maxrel, worst)

# test predictions
pr = pq.read_table(RV + rf'\lead_{L}\preds_ridge.parquet').to_pandas()
lab_f = RUN + r'\test_preds.parquet' if L == 0 else RUN + rf'\ladder\lead_{L}\test_preds.parquet'
lab = pq.read_table(lab_f, columns=['unit', 'time', 'lead', 'y']).to_pandas()
rows = []; allp = []
for g in groups:
    te = pq.read_table(EX + rf'\lead_{L}\test\{g}.parquet', columns=['unit', 'time', 'lead', 'nfit__log_c'] + cols).to_pandas()
    Z = design(te[cols].values.astype(np.float64), te.nfit__log_c.values)
    full = te.nfit__log_c.values + tbar_f + (Z - zbar_f[None, :]) @ coef_f
    h = gi[g]
    coef_h, zbar_h, tbar_h, _ = solve(St - S[h], s_t - s1[h], n_t - n_g[h], T_t - T1[h], ZT_t - ZT[h])
    logo = te.nfit__log_c.values + tbar_h + (Z - zbar_h[None, :]) @ coef_h
    d = te[['unit', 'time', 'lead']].copy(); d['group'] = g
    d['full_pre'] = np.exp(full) - cval; d['logo_pre'] = np.exp(logo) - cval
    allp.append(d)
P_ = pd.concat(allp).merge(pr[['unit', 'time', 'lead', 'pre__rival_ridge', 'arm__rival_ridge']], on=['unit', 'time', 'lead'], how='left')
P_ = P_.merge(lab, on=['unit', 'time', 'lead'], how='left')
print('reproduce saved pre: max abs diff', np.nanmax(np.abs(P_.full_pre - P_.pre__rival_ridge)), 'rows', len(P_))
P_['full'] = np.clip(P_.full_pre, 0, None); P_['logo'] = np.clip(P_.logo_pre, 0, None)
P_ = P_[np.isfinite(P_.y)]
gm = P_.groupby('group').apply(lambda d: pd.Series(dict(n=len(d), mae_saved=np.abs(d.arm__rival_ridge - d.y).mean(),
                                                         mae_full=np.abs(d.full - d.y).mean(), mae_logo=np.abs(d.logo - d.y).mean())))
gm.to_csv(OUT)
P_.to_parquet(OUT.replace('.csv', '_rows.parquet'))
print('pooled MAE saved', np.abs(P_.arm__rival_ridge - P_.y).mean(), 'full', np.abs(P_.full - P_.y).mean(), 'logo', np.abs(P_.logo - P_.y).mean())
