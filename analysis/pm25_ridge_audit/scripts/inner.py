import pyarrow.parquet as pq, numpy as np, pandas as pd
from scipy.stats import spearmanr, pearsonr
R = r'D:/treeroute/runs/pm25/headline/20261007_74e67609'
B = r'D:/treeroute/rivals/pm25/20261007_74e67609'
OUT = r'C:/Users/<user>/AppData/Local/Temp/claude/<session-folder>/<session-folder>/scratchpad'
A = 'log_c_corrector_unweighted@level=30.0,ratio=1.0'
o = pq.read_table(R + '/inner_preds.parquet', columns=['unit','group','time','y', A, 'log_c_trees_off_unweighted']).to_pandas()
r = pq.read_table(B + '/trials/ridge/ridge__log_c__alphas/inner_preds.parquet', columns=['unit','group','time','pred__1000.0','pre__1000.0']).to_pandas()
print('inner rows ours', len(o), 'ridge', len(r), 'same order', all((o[k].values == r[k].values).all() for k in ['unit','group','time']))
g = pq.read_table(B + '/lead_0/guard_ridge.parquet').to_pandas()
print('lead0 guard_ridge rows', len(g), 'same keys as ours', all((o[k].values == g[k].values).all() for k in ['unit','group','time']), 'y equal', bool(np.allclose(o['y'], g['y'])),
      'pred equal to trial pred__1000', bool(np.allclose(g['arm__rival_ridge'], r['pred__1000.0'])))
j = o.merge(r, on=['unit','group','time'])
j['year'] = (j['time'] - 1) // 12
j['eo'] = (j.y - j[A]).abs(); j['er'] = (j.y - j['pred__1000.0']).abs(); j['et'] = (j.y - j['log_c_trees_off_unweighted']).abs()
print('INNER pooled MAE ours(adopted, pick on inner among 282) %.4f ridge(alpha pick on inner among 16) %.4f trees_off %.4f d %.4f' % (j.eo.mean(), j.er.mean(), j.et.mean(), j.er.mean() - j.eo.mean()))
yy = j.groupby('year').agg(n=('y','size'), mo=('eo','mean'), mr=('er','mean'), bo=(A, 'mean'), br=('pred__1000.0','mean'), y=('y','mean'))
yy['d'] = yy.mr - yy.mo; yy['bias_o'] = yy.bo - yy.y; yy['bias_r'] = yy.br - yy.y
print(yy[['n','mo','mr','d','bias_o','bias_r']].round(4).to_string())
gi = j.groupby('group').agg(mo=('eo','mean'), mr=('er','mean'), n=('y','size'))
gi['d_inner'] = gi.mr - gi.mo
print('inner groups', len(gi), 'ridge wins', int((gi.d_inner < 0).sum()), 'median d', round(gi.d_inner.median(), 4), 'mean-of-groups d', round(gi.d_inner.mean(), 4))
print(gi.sort_values('d_inner').head(8).round(3).to_string())
gd = pd.read_csv(OUT + '/group_d.csv')
for L in (0, 6, 12):
    t = gd[gd.lead == L].set_index('group')
    k = gi.join(t[['d']], how='inner')
    print('lead', L, 'spearman(inner d, test d) = %.3f  pearson = %.3f; n=%d; sign agreement %.3f' % (spearmanr(k.d_inner, k.d).correlation, pearsonr(k.d_inner, k.d)[0], len(k), np.mean(np.sign(k.d_inner) == np.sign(k.d))))
    k2 = k.drop('north_china_plain', errors='ignore')
    print('        without NCP spearman %.3f pearson %.3f' % (spearmanr(k2.d_inner, k2.d).correlation, pearsonr(k2.d_inner, k2.d)[0]))
print('NCP inner:', gi.loc['north_china_plain'].round(3).to_dict() if 'north_china_plain' in gi.index else None)
# guard windows at leads 6/12: our pinned arm vs ridge guard fit, same rows
for L in (6, 12):
    og = pq.read_table(R + '/ladder/lead_%d/guard_preds.parquet' % L, columns=['unit','group','time','issue','y','arm__log_c_corrector_unweighted','arm__log_c_trees_off_unweighted']).to_pandas()
    rg = pq.read_table(B + '/lead_%d/guard_ridge.parquet' % L, columns=['unit','group','time','issue','y','arm__rival_ridge']).to_pandas()
    m = og.merge(rg, on=['unit','group','time','issue'], suffixes=('', '_r'))
    print('lead', L, 'guard rows', len(og), len(rg), 'merged', len(m), 'y equal', bool(np.allclose(m.y, m.y_r)))
    eo = (m.y - m.arm__log_c_corrector_unweighted).abs(); er = (m.y - m.arm__rival_ridge).abs(); et = (m.y - m.arm__log_c_trees_off_unweighted).abs()
    m['eo'] = eo; m['er'] = er
    gg = m.groupby('group').agg(mo=('eo','mean'), mr=('er','mean')); gg['d'] = gg.mr - gg.mo
    m['year'] = (m['time'] - 1) // 12
    yy = m.groupby('year').apply(lambda v: pd.Series({'n': len(v), 'mo': v.eo.mean(), 'mr': v.er.mean()}))
    print('   GUARD MAE ours(pinned arm) %.4f ridge %.4f trees_off %.4f d %.4f; groups ridge wins %d/%d; per year:' % (eo.mean(), er.mean(), et.mean(), er.mean() - eo.mean(), int((gg.d < 0).sum()), len(gg)))
    print(yy.round(4).to_string())
