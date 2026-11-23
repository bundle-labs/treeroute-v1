# Recompute hist_mean_12/60/all and hist_last_1..3 for every lead-0 TEST row (all 127 groups) from labels
# (lead-0 train export y for t<=24240, the run's saved test y for t>=24241), windows ending at t-1.
import numpy as np, pandas as pd, pyarrow.parquet as pq, os
E = r'D:/treeroute/rival_export/pm25/20261007_74e67609/lead_0'
R = r'D:/treeroute/runs/pm25/headline/20261007_74e67609'
ty = pq.read_table(R + '/test_preds.parquet', columns=['unit','time','y']).to_pandas(); ty['unit'] = ty['unit'].astype(str)
groups = sorted(f[:-8] for f in os.listdir(E + '/test') if f.endswith('.parquet'))
H = ['hist_last_1','hist_last_2','hist_last_3','hist_mean_12','hist_mean_60','hist_mean_all']
tot = {h: [0, 0, 0] for h in H}   # checked, equal, skipped(no label in window)
first_steps = set(); worst = {h: 0.0 for h in H}
for g in groups:
    te = pq.read_table(f'{E}/test/{g}.parquet', columns=['unit','time'] + ['x__' + h for h in H]).to_pandas(); te['unit'] = te['unit'].astype(str)
    units = te['unit'].unique()
    tr = pq.read_table(f'{E}/train/{g}.parquet', columns=['unit','time','y']).to_pandas(); tr['unit'] = tr['unit'].astype(str)
    tr = tr[tr['unit'].isin(units)]
    lab = pd.concat([tr, ty[ty['unit'].isin(units)]], ignore_index=True)
    t0 = int(tr['time'].min()); first_steps.add(t0)
    T = np.arange(t0, 24289)
    for u, tu in te.groupby('unit'):
        lu = lab[lab['unit'] == u]
        s = pd.Series(np.nan, index=T); s.loc[lu['time'].to_numpy()] = lu['y'].to_numpy()
        v = s.to_numpy(); fin = np.isfinite(v); cs = np.r_[0, np.cumsum(np.where(fin, v, 0))]; cn = np.r_[0, np.cumsum(fin)]
        for _, r in tu.iterrows():
            i = int(r['time']) - t0     # index of t; newest readable = i-1
            for h in H:
                x = float(r['x__' + h])
                if h.startswith('hist_last_'):
                    k = int(h[-1]); j = i - k
                    if j < 0 or not fin[j]: tot[h][2] += 1; continue
                    ref = v[j]
                else:
                    w = {'hist_mean_12': 12, 'hist_mean_60': 60, 'hist_mean_all': 10**6}[h]
                    a = max(0, i - w); b = i
                    n = cn[b] - cn[a]
                    if n == 0: tot[h][2] += 1; continue
                    ref = (cs[b] - cs[a]) / n
                tot[h][0] += 1
                err = abs(x - ref) / max(1.0, abs(ref)); worst[h] = max(worst[h], err)
                tot[h][1] += err < 1e-5
print('label start steps:', sorted(first_steps))
for h in H:
    print(f'{h}: checked {tot[h][0]}, equal (rel<1e-5) {tot[h][1]}, skipped (no label: fill chain) {tot[h][2]}, worst rel err {worst[h]:.2e}')
