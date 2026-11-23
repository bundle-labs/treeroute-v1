import pyarrow.parquet as pq, numpy as np, pandas as pd, os
E = r'D:/treeroute/rival_export/pm25/20261007_74e67609'
R = r'D:/treeroute/runs/pm25/headline/20261007_74e67609'
ours = pq.read_table(R + '/test_preds.parquet', columns=['unit','group','time','y','normal']).to_pandas()
ylab = ours.set_index(['unit','time'])['y']
gs = sorted(os.listdir(E + '/lead_0/test'))[::25]
for L in (0, 6, 12):
    res = []
    for gf in gs:
        t = pq.read_table(E + '/lead_%d/test/%s' % (L, gf), columns=['unit','time','issue','x__hist_last_1','x__hist_last_2','nfit__identity']).to_pandas()
        k = 1 if L == 0 else L
        key = pd.MultiIndex.from_arrays([t['unit'], t['time'] - k])
        prev = ylab.reindex(key).values
        ok = ~np.isnan(prev)
        res.append((gf, int(ok.sum()), float(np.nanmax(np.abs(t['x__hist_last_1'].values[ok] - prev[ok]))) if ok.any() else None,
                    # check that hist_last_1 is NOT equal to y at t (the target)
                    float(np.mean(np.isclose(t['x__hist_last_1'].values, ylab.reindex(pd.MultiIndex.from_arrays([t['unit'], t['time']])).values)))))
    print('lead', L, 'hist_last_1 vs y(t-%d): ' % (1 if L == 0 else L), res)
# our normal vs rival nfit normal on test rows at lead 0
nf = []
for gf in sorted(os.listdir(E + '/lead_0/test'))[::10]:
    t = pq.read_table(E + '/lead_0/test/%s' % gf, columns=['unit','time','nfit__identity']).to_pandas()
    j = t.merge(ours, on=['unit','time'])
    nf.append(float(np.max(np.abs(j['nfit__identity'] - j['normal']))))
print('max |rival nfit__identity - our normal| lead0 sample groups:', max(nf))
