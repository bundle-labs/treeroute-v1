"""Skeptic check: do the exported lead-0 driver values carry their R8 lag, measured against the RAW stores?
For each exported x__ column, compare x(u,t) with raw(u, t-k) for k = 0..26 and report the match share per k.
Read-only. One group at a time; raw files filtered to the group's 100 exported units."""
import sys, os, json, numpy as np, pandas as pd, pyarrow.parquet as pq, pyarrow as pa, pyarrow.compute as pc
EXP = r'D:\treeroute\rival_export\pm25\20261007_74e67609'
RUN = r'D:\treeroute\runs\pm25\headline\20261007_74e67609'
P0 = 2002 * 12 + 1          # step of Jan 2002 (year*12 + month)
NS = 22 * 12
LAG12 = ("spei_01m", "spei_03m", "spei_06m", "V06_spei_12m", "spei_24m", "amo")
HOLD = ("aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats", "aglw_total_lsu")
d8 = json.load(open(RUN + r'\derived.json'))['R8']['inputs']['columns']

def r8_months(c):
    v = d8.get(c)
    if v is None:
        return 0
    return v['steps'] * (12 if v['cadence']['unit'] == 'year' else 1)

groups = sys.argv[1].split(',')
KS = list(range(0, 27))
rows = []
for g in groups:
    tr = pq.read_table(EXP + rf'\lead_0\train\{g}.parquet').to_pandas()
    te = pq.read_table(EXP + rf'\lead_0\test\{g}.parquet').to_pandas()
    xcols = [c for c in tr.columns if c.startswith('x__') and not c.startswith('x__hist_')]
    d = pd.concat([tr[['unit', 'time'] + xcols], te[['unit', 'time'] + xcols]], ignore_index=True)
    units = sorted(d.unit.unique()); ui = {u: i for i, u in enumerate(units)}
    base = [c[3:] for c in xcols]
    need = set()
    for b in base:
        if b.endswith('_lag12'):
            need.add(b[:-6])
        elif b.endswith('_hold2021'):
            need.add(b[:-9])
        elif b != 'burn_frac':
            need.add(b)
    raw = {c: np.full((len(units), NS), np.nan) for c in need | {'burn_frac'}}
    uarr = pa.array(units)
    for y in range(2002, 2024):
        f = rf'D:\monthly_panel\{g}_monthly_{y}.parquet'
        sch = pq.read_schema(f).names
        cols = ['cell_id', 'year', 'month'] + [c for c in need if c in sch]
        t = pq.read_table(f, columns=cols)
        t = t.filter(pc.is_in(t['cell_id'], value_set=uarr)).to_pandas()
        iu = t.cell_id.map(ui).values; s = (t.year.values * 12 + t.month.values) - P0
        for c in need:
            if c in t:
                raw[c][iu, s] = t[c].values
        try:
            b = pq.read_table(rf'D:\gfed_burn\{g}_burn_{y}.parquet', columns=['cell_id', 'year', 'month', 'burn_frac'])
            b = b.filter(pc.is_in(b['cell_id'], value_set=uarr)).to_pandas()
            raw['burn_frac'][b.cell_id.map(ui).values, (b.year.values * 12 + b.month.values) - P0] = b.burn_frac.values
        except FileNotFoundError:
            pass
    # engineered raw versions
    for p in HOLD:
        if p in raw:
            h = raw[p].copy()
            y2021_dec = (2021 * 12 + 12) - P0
            for s in range(y2021_dec + 1, NS):
                h[:, s] = raw[p][:, (2021 * 12 + ((s + P0 - 1) % 12) + 1) - P0]
            raw[p + '_hold2021'] = h
    for p in LAG12:
        if p in raw:
            raw[p + '_lag12'] = raw[p]   # compare at shift; expect best k = 12
    iu = d.unit.map(ui).values; st = d.time.values - P0
    for xc, b in zip(xcols, base):
        if b.startswith('ctx:'):
            continue
        R = raw.get(b)
        if R is None:
            rows.append(dict(group=g, col=b, note='no raw')); continue
        x = d[xc].values.astype(float)
        exp_k = r8_months(b) + (12 if b.endswith('_lag12') else 0)
        rec = dict(group=g, col=b, exp_k=exp_k)
        best, bestk = -1, None
        for k in KS:
            s = st - k; ok = s >= 0
            r = np.full(len(d), np.nan); r[ok] = R[iu[ok], s[ok]]
            m = np.isfinite(x) & np.isfinite(r)
            if m.sum() == 0:
                continue
            sh = np.isclose(x[m], r[m], rtol=1e-5, atol=1e-7).mean()
            rec[f'k{k}'] = round(float(sh), 4)
            if sh > best + 1e-9:
                best, bestk = sh, k
        rec['best_k'] = bestk; rec['best'] = round(float(best), 4)
        # test rows only, at the expected k
        tm = d.time.values >= 24241
        s = st - exp_k; ok = (s >= 0) & tm
        r = np.full(len(d), np.nan); r[ok] = R[iu[ok], s[ok]]
        m = np.isfinite(x) & np.isfinite(r) & tm
        rec['test_n'] = int(m.sum()); rec['test_match_expk'] = round(float(np.isclose(x[m], r[m], rtol=1e-5, atol=1e-7).mean()), 4) if m.sum() else None
        rec['x_nan_share_train'] = round(float(np.isnan(x[~tm]).mean()), 4)
        rec['x_nan_share_test'] = round(float(np.isnan(x[tm]).mean()), 4)
        rows.append(rec)
    pd.DataFrame([r for r in rows if r.get('group') == g]).to_csv(sys.argv[2].replace('.csv', '_inc.csv'), mode='a', index=False, header=not os.path.exists(sys.argv[2].replace('.csv', '_inc.csv')))
    print(g, flush=True)
out = pd.DataFrame(rows)
out.to_csv(sys.argv[2], index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 2000)
print(out[['group', 'col', 'exp_k', 'best_k', 'best', 'k0', 'test_n', 'test_match_expk', 'x_nan_share_train', 'x_nan_share_test']].to_string())
