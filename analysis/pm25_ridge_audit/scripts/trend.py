import pyarrow.parquet as pq, numpy as np, pandas as pd, os
from scipy.stats import spearmanr, pearsonr
E = r'D:/treeroute/rival_export/pm25/20261007_74e67609/lead_0/train'
OUT = r'C:/Users/<user>/AppData/Local/Temp/claude/<session-folder>/<session-folder>/scratchpad'
rows = []
tmin = tmax = None
for gf in sorted(os.listdir(E)):
    t = pq.read_table(E + '/' + gf, columns=['group','unit','time','y','r_refit']).to_pandas()
    t = t[t['r_refit'].astype(bool)]
    tmin = t['time'].min() if tmin is None else min(tmin, t['time'].min()); tmax = t['time'].max() if tmax is None else max(tmax, t['time'].max())
    m = t.groupby('time')['y'].mean()          # group-mean monthly series
    x = (m.index.values - 24240) / 12.0        # years relative to the fit cut
    # deseasonalise: remove month-of-year means
    mo = m.index.values % 12
    ds = m.values - pd.Series(m.values).groupby(mo).transform('mean').values
    s_all = np.polyfit(x, ds, 1)[0]
    last = x >= -5
    s_5 = np.polyfit(x[last], ds[last], 1)[0]
    mean_all = m.mean(); mean_5 = m.values[last].mean(); mean_1 = m.values[x >= -1].mean()
    rows.append(dict(group=gf[:-8], n_train=len(t), y_mean_train=mean_all, slope_all=s_all, slope_5y=s_5,
                     rel_slope_all=s_all / mean_all, rel_slope_5y=s_5 / mean_all,
                     gap_60_all=mean_5 - mean_all, gap_12_all=mean_1 - mean_all, rel_gap_60_all=(mean_5 - mean_all) / mean_all))
tr = pd.DataFrame(rows)
print('train refit time range', tmin, tmax, '=', tmin / 12, tmax / 12)
gd = pd.read_csv(OUT + '/group_d.csv')
tr.to_csv(OUT + '/group_trend.csv', index=False)
for L in (0, 6, 12):
    j = gd[gd['lead'] == L].merge(tr, on='group')
    j['adv'] = -j['d']   # ridge advantage = ours MAE - ridge MAE (>0 ridge better)
    j['rel_adv'] = j['adv'] / j['mae_ours']
    print('== lead', L, 'n groups', len(j))
    for c in ['slope_all', 'slope_5y', 'rel_slope_all', 'rel_slope_5y', 'gap_60_all', 'rel_gap_60_all']:
        r1 = spearmanr(j['adv'], j[c]).correlation; r2 = spearmanr(j['adv'], j[c].abs()).correlation
        r3 = spearmanr(j['rel_adv'], j[c]).correlation; r4 = spearmanr(j['rel_adv'], j[c].abs()).correlation
        print('   %-15s spearman(adv, signed)=%+.3f  (adv, |.|)=%+.3f   (rel_adv, signed)=%+.3f (rel_adv, |.|)=%+.3f' % (c, r1, r2, r3, r4))
    # terciles of 5-y slope
    j['tert'] = pd.qcut(j['rel_slope_5y'], 3, labels=['most_declining', 'middle', 'most_rising'])
    print(j.groupby('tert').agg(n=('adv','size'), rel_slope_5y=('rel_slope_5y','median'), adv_mean=('adv','mean'), adv_median=('adv','median'),
                                ridge_wins=('adv', lambda v: int((v > 0).sum())), bias_ours=('bias_ours','mean'), bias_ridge=('bias_ridge','mean')).round(4).to_string())
    # same without north_china_plain
    k = j[j['group'] != 'north_china_plain']
    print('   without north_china_plain: mean adv %.4f; spearman(adv, rel_slope_5y)=%+.3f' % (k['adv'].mean(), spearmanr(k['adv'], k['rel_slope_5y']).correlation))
print(tr.sort_values('rel_slope_5y').head(8).round(3).to_string())
print(tr[tr.group.isin(['north_china_plain','pearl_river_delta','poland_central','hungarian_puszta','congo_basin_drc','mesopotamia','eastern_us_deciduous'])].round(3).to_string())
