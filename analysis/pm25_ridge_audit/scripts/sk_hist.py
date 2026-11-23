"""Skeptic check: recompute the 6 history columns from labels, all groups, leads 0/6/12, train+test rows.
Read-only. Labels: lead-0 export train y (all 100 units, <= 24240) + run test_preds y (scored units, 24241-24288)."""
import sys, numpy as np, pandas as pd, pyarrow.parquet as pq, os, json
EXP = r'D:\treeroute\rival_export\pm25\20261007_74e67609'
RUN = r'D:\treeroute\runs\pm25\headline\20261007_74e67609'
HC = ['hist_last_1', 'hist_last_2', 'hist_last_3', 'hist_mean_12', 'hist_mean_60', 'hist_mean_all']
S0, S1 = 24037, 24288
tp = pq.read_table(RUN + r'\test_preds.parquet', columns=['unit', 'group', 'time', 'y']).to_pandas()
groups = sorted(f[:-8] for f in os.listdir(EXP + r'\lead_0\train'))
if len(sys.argv) > 1:
    groups = groups[:int(sys.argv[1])]
acc = {}  # (lead, role, col, variant) -> [n, match]

def add(k, n, m):
    a = acc.setdefault(k, [0, 0]); a[0] += n; a[1] += m

for g in groups:
    tr0 = pq.read_table(EXP + rf'\lead_0\train\{g}.parquet', columns=['unit', 'time', 'y']).to_pandas()
    lab = pd.concat([tr0, tp[tp.group == g][['unit', 'time', 'y']]])
    units = sorted(lab.unit.unique()); ui = {u: i for i, u in enumerate(units)}
    Y = np.full((len(units), S1 - S0 + 1), np.nan)
    Y[lab.unit.map(ui).values, lab.time.values - S0] = lab.y.values
    for L in (0, 6, 12):
        for role in ('train', 'test'):
            cols = ['unit', 'time'] + ['x__' + c for c in HC]
            d = pq.read_table(EXP + rf'\lead_{L}\{role}\{g}.parquet', columns=cols).to_pandas()
            iu = d.unit.map(ui).values; t = d.time.values
            newest = t - 1 if L == 0 else t - L          # newest readable label step
            for variant, nw in (('rule', newest), ('incl_t', t)):
                exp = {}
                for k in (1, 2, 3):
                    s = nw - k + 1 - S0
                    ok = s >= 0
                    v = np.full(len(d), np.nan); v[ok] = Y[iu[ok], s[ok]]
                    exp[f'hist_last_{k}'] = v
                fin = np.isfinite(Y)
                C = np.concatenate([np.zeros((len(units), 1)), np.cumsum(np.where(fin, Y, 0.0), axis=1)], axis=1)
                N = np.concatenate([np.zeros((len(units), 1)), np.cumsum(fin, axis=1)], axis=1)
                for name, w in (('hist_mean_12', 12), ('hist_mean_60', 60), ('hist_mean_all', 10_000)):
                    hi = np.clip(nw - S0 + 1, 0, Y.shape[1])
                    lo = np.clip(hi - w, 0, None)
                    cnt = N[iu, hi] - N[iu, lo]
                    sm = C[iu, hi] - C[iu, lo]
                    with np.errstate(invalid='ignore', divide='ignore'):
                        v = np.where(cnt > 0, sm / np.maximum(cnt, 1), np.nan)
                    exp[name] = v
                for c in HC:
                    x = d['x__' + c].values.astype(float); e = exp[c]
                    m = np.isfinite(e) & np.isfinite(x)
                    mt = np.isclose(x[m], e[m], rtol=2e-6, atol=1e-6)
                    add((L, role, c, variant), int(m.sum()), int(mt.sum()))
                    if variant == 'rule':
                        # rows where x finite but expected NaN (empty history fill)
                        add((L, role, c, 'fill_rows'), int((np.isfinite(x) & ~np.isfinite(e)).sum()), 0)
    print(g, flush=True, end=' ')
print()
out = []
for (L, role, c, v), (n, m) in sorted(acc.items()):
    out.append(dict(lead=L, role=role, col=c, variant=v, n=n, match=m, share=(m / n if n else None)))
df = pd.DataFrame(out)
pd.set_option('display.width', 200); pd.set_option('display.max_rows', 500)
print(df.to_string())
