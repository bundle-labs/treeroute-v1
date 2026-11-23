"""replay_B.py -- implementer B of owner ruling AN2: POST HOC re-computation of the engine-v2 alarm replay.

Everything this script computes is POST HOC (the alarm was specified after the five v1 runs were locked, run and
scored). On coral bleaching the replay is also CIRCULAR (the rule was designed from the same coral test window, whose
2016-2019 span was set by hand). No locked number, verdict or adoption changes.

Approach B: written from D:/treeroute/analysis/paper_posthoc/v2_replay/SPEC.md (section 2, the rule) and the saved
row files only. No engine or tool code is imported, copied or opened; numpy, pandas and pyarrow only.

Run:   py -3.9 -I -B D:/treeroute/analysis/paper_posthoc/v2_replay/B/replay_B.py
Reads: only files listed in INPUTS_SHA256.txt (each re-hashed before use; any mismatch stops the script), plus
       SPEC.md and INPUTS_SHA256.txt themselves (hashed and recorded).
Writes: only into D:/treeroute/analysis/paper_posthoc/v2_replay/B/ (result_B.json, rows_<package>_lead_<L>.parquet).
Order: the reproduction gate (G0-G9) first; if any of G0-G8 fails, result_B.json records the failure and nothing
       new (section 6) is computed.
"""
import sys

sys.dont_write_bytecode = True

import hashlib
import json
import math
import os
import platform
import re
import struct
import traceback
from datetime import date

import numpy as np
import pandas as pd
import pyarrow
import pyarrow.parquet as pq

# ----------------------------------------------------------------------------------------------------------------
# Fixed settings (SPEC.md sections 2-7). The threshold and the row floor are fixed; the other thresholds are the
# information-only check of Q9 / G6 (exactly these four, no others).
# ----------------------------------------------------------------------------------------------------------------
OUT = 'D:/treeroute/analysis/paper_posthoc/v2_replay/B'
SPEC = 'D:/treeroute/analysis/paper_posthoc/v2_replay/SPEC.md'
INPUTS_LIST = 'D:/treeroute/analysis/paper_posthoc/v2_replay/INPUTS_SHA256.txt'
RUNS_ROOT = 'D:/treeroute/runs'
GATE = 'D:/treeroute/engine_v2/replay_af2_20261021'
HISTORY_WW = 'D:/treeroute/engine_v2/replay/WITH_WITHOUT.csv'
EDGES = 'D:/treeroute/runs/_headline_tables/coral/coral_report/magnitude_edges.csv'
PART604 = 'D:/treeroute/analysis/guidance/coral/results_coral.json'

THRESHOLD = 2.0          # A8.alarm_ratio_threshold (strict >), fixed
MIN_ROWS = 30            # A8.alarm_min_batch_rows, fixed
INFO_THRESHOLDS = (1.5, 2.0, 2.5, 3.0)
REL_TOL = 1e-12
Z = 1.96
BLOCK_FLAG_FACTOR = 1.2  # report-only: blocked SE more than 20% above the group SE

RUNS = (
    ('pm25', '20261007_74e67609', (6, 12)),
    ('ndvi', '20261016_d1de3158', (6, 12)),
    ('fire', '20261017_869d1f38', (6, 12)),
    ('defo', '20261017_d71c61f4', (1,)),
    ('coral', '20261020_f3b8e3da', (183, 365)),
)

PLAIN = {
    'inert_twin_not_simpler': 'cannot switch: twin not simpler',
    'not_applicable_declined': 'nothing to switch: declined',
    'inert_twin_not_eligible': 'cannot switch: twin fails its skill guard',
    'active': 'can switch',
    'not_replayable_twin_not_saved': 'not replayable: twin not saved',
    'not_tested_zero_reference_gap': 'not tested: zero reference gap',
}

# Spec section 2 table: the status each pass must get (confirmed by the gate file too).
SPEC_STATUS = {
    ('pm25', 0): 'inert_twin_not_simpler', ('pm25', 6): 'inert_twin_not_simpler',
    ('pm25', 12): 'not_applicable_declined',
    ('ndvi', 0): 'inert_twin_not_simpler', ('ndvi', 6): 'not_applicable_declined',
    ('ndvi', 12): 'not_applicable_declined',
    ('fire', 0): 'inert_twin_not_eligible', ('fire', 6): 'not_applicable_declined',
    ('fire', 12): 'not_applicable_declined',
    ('defo', 0): 'active', ('defo', 1): 'not_replayable_twin_not_saved',
    ('coral', 0): 'active', ('coral', 183): 'not_replayable_twin_not_saved',
    ('coral', 365): 'not_applicable_declined',
}

# Gate values stated in SPEC.md section 5 that have no machine-readable gate file (G4, G6) or that the spec restates.
SPEC_G4 = {'coral_small_batches': 15, 'coral_small_rows': 275, 'coral_2016_07_ratio': 25.529655201638473,
           'coral_2016_07_rows': 16}
SPEC_G6 = {1.5: 6.109, 2.5: 6.100, 3.0: 6.100}
SPEC_G2_INERT_MAX = {'pm25': 1.753861864808271, 'ndvi': 1.749949522314697, 'fire': 1.847279910383901}
SPEC_CORAL = {'fired': ['2016-01', '2016-02', '2016-03', '2016-04', '2016-05', '2016-06', '2016-08', '2017-03',
                        '2017-12', '2019-05', '2019-06'],
              'rows_switched': 737, 'batches': 48, 'tested': 33, 'R': 0.34056479282671, 'R_rows': 2046,
              'mae_without': 6.69798924506233, 'mae_with': 6.119956002798195, 'max_ratio': 29.105817502602708}

# ----------------------------------------------------------------------------------------------------------------
# Input hashing (G0)
# ----------------------------------------------------------------------------------------------------------------
EXPECTED = {}
INPUTS = {}
G0_LOG = {'files_checked': 0, 'mismatches': [], 'not_listed': []}


class GateStop(Exception):
    pass


def _norm(path):
    return os.path.normpath(path).replace('\\', '/')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(1 << 22)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load_expected():
    with open(INPUTS_LIST, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            h, p = line.split(' *', 1)
            EXPECTED[_norm(p)] = h.lower()


def checked(path):
    p = _norm(path)
    if p in INPUTS:
        return p
    got = sha256_file(p)
    INPUTS[p] = got
    if p not in EXPECTED:
        G0_LOG['not_listed'].append(p)
        raise GateStop('G0: input not listed in INPUTS_SHA256.txt: %s' % p)
    G0_LOG['files_checked'] += 1
    if got != EXPECTED[p]:
        G0_LOG['mismatches'].append({'path': p, 'expected': EXPECTED[p], 'obtained': got})
        raise GateStop('G0: sha256 mismatch: %s' % p)
    return p


def read_json(path):
    with open(checked(path), 'rb') as f:
        return json.loads(f.read().decode('utf-8'))


def read_parquet(path, columns):
    return pq.read_table(checked(path), columns=list(columns)).to_pandas()


def parquet_columns(path):
    return list(pq.read_schema(checked(path)).names)


def read_csv(path, **kw):
    return pd.read_csv(checked(path), float_precision='round_trip', **kw)


# ----------------------------------------------------------------------------------------------------------------
# Comparison helpers (gate equality rules: exact for ints/strings/bools/keys; floats bit-equal, else |rel| <= 1e-12)
# ----------------------------------------------------------------------------------------------------------------
def _missing(v):
    if v is None:
        return True
    if isinstance(v, (float, np.floating)) and math.isnan(float(v)):
        return True
    return False


def _isbool(v):
    return isinstance(v, (bool, np.bool_))


def _isint(v):
    return isinstance(v, (int, np.integer)) and not _isbool(v)


def _bits(x):
    return struct.pack('<d', float(x))


def compare(e, o):
    """Return (ok, bit_equal, rel)."""
    if _missing(e) or _missing(o):
        return (_missing(e) and _missing(o), True, None)
    if _isbool(e) or _isbool(o):
        return (_isbool(e) and _isbool(o) and bool(e) == bool(o), True, None)
    if isinstance(e, str) or isinstance(o, str):
        return (isinstance(e, str) and isinstance(o, str) and e == o, True, None)
    if isinstance(e, (list, tuple)) or isinstance(o, (list, tuple)):
        if not (isinstance(e, (list, tuple)) and isinstance(o, (list, tuple))) or len(e) != len(o):
            return (False, False, None)
        res = [compare(a, b) for a, b in zip(e, o)]
        rels = [r[2] for r in res if r[2] is not None]
        return (all(r[0] for r in res), all(r[1] for r in res), max(rels) if rels else None)
    fe, fo = float(e), float(o)
    if _isint(e) or _isint(o):
        return (fe == fo, True, None)
    if _bits(fe) == _bits(fo):
        return (True, True, 0.0)
    if not (math.isfinite(fe) and math.isfinite(fo)):
        return (False, False, None)
    rel = abs(fe - fo) / max(abs(fe), abs(fo))
    return (rel <= REL_TOL, False, rel)


class Cmp:
    def __init__(self):
        self.n = 0
        self.fails = []
        self.not_bit_equal = []

    def eq(self, item, expected, obtained):
        self.n += 1
        ok, bit, rel = compare(expected, obtained)
        if not ok:
            self.fails.append({'item': item, 'expected': expected, 'obtained': obtained})
        elif not bit:
            self.not_bit_equal.append({'item': item, 'expected': expected, 'obtained': obtained, 'rel_diff': rel})
        return ok

    def check(self, item, cond, detail=None):
        self.n += 1
        if not cond:
            self.fails.append({'item': item, 'expected': True, 'obtained': False, 'detail': detail})
        return cond

    def result(self, **extra):
        d = {'items_compared': self.n, 'n_failures': len(self.fails), 'failures': self.fails[:40],
             'n_not_bit_equal': len(self.not_bit_equal), 'not_bit_equal': self.not_bit_equal}
        d.update(extra)
        return {'pass': len(self.fails) == 0, 'details': d}


# ----------------------------------------------------------------------------------------------------------------
# The rule (SPEC.md section 2, R1-R11)
# ----------------------------------------------------------------------------------------------------------------
def arm_name(d):
    return '%s_%s_%s' % (d['link'], d['tool'], d['weighting'])


def point_text(level, ratio):
    return 'level=%r,ratio=%r' % (level, ratio)


def routed_weightings(router_kind):
    # R2: the region router routes unweighted arms only; the per-unit grid and the neighbour router both.
    return ('unweighted',) if router_kind == 'region' else ('unweighted', 'gls')


def twin_of(arm, weightings):
    # R3: the other weighting when it is routed, else the other tool.
    link, tool, w = arm['link'], arm['tool'], arm['weighting']
    if tool not in ('plain', 'corrector') or w not in ('unweighted', 'gls'):
        raise RuntimeError('no twin for arm %r' % (arm,))
    other_w = 'gls' if w == 'unweighted' else 'unweighted'
    if other_w in weightings:
        return {'link': link, 'tool': tool, 'weighting': other_w}, 'weighting'
    other_t = 'corrector' if tool == 'plain' else 'plain'
    return {'link': link, 'tool': other_t, 'weighting': w}, 'tool'


def twin_is_simpler(a, t):
    # R4
    if a['link'] == t['link'] and a['tool'] == t['tool'] and t['weighting'] == 'unweighted' and a['weighting'] == 'gls':
        return True
    if a['link'] == t['link'] and a['weighting'] == t['weighting'] and t['tool'] == 'plain' and a['tool'] == 'corrector':
        return True
    return False


def batch_keys(issue, cadence):
    # R7
    if cadence['kind'] == 'irregular':
        return np.array([date.fromordinal(int(i)).strftime('%Y-%m') for i in issue], dtype=object)
    if cadence['kind'] == 'regular' and cadence['unit'] in ('month', 'year') and cadence['length'] == 1:
        return np.array(['step:%d' % int(i) for i in issue], dtype=object)
    raise RuntimeError('cadence not covered by the rule: %r' % (cadence,))


def batch_order(keys):
    u = set(keys.tolist())
    steps = [k for k in u if k.startswith('step:')]
    if steps and len(steps) != len(u):
        raise RuntimeError('mixed batch keys')
    if steps:
        return sorted(u, key=lambda k: int(k[5:]))
    return sorted(u)


def decide(a, t, bidx, order, R, status, threshold=THRESHOLD):
    """R8/R9. Returns (batch records, fired row mask, with column)."""
    r_ok = (R is not None) and math.isfinite(R) and R > 0
    fired_rows = np.zeros(len(a), dtype=bool)
    recs = []
    for k in order:
        ix = bidx[k]
        if t is not None:
            gap = float(np.mean(np.abs(a[ix] - t[ix])))
            with np.errstate(divide='ignore', invalid='ignore'):
                ratio = float(np.float64(gap) / np.float64(R))
        else:
            gap = None
            ratio = None
        tested = bool(status == 'active' and len(ix) >= MIN_ROWS and r_ok)
        fired = bool(tested and ratio > threshold)
        if fired:
            fired_rows[ix] = True
        recs.append({'batch': k, 'rows': int(len(ix)), 'gap': gap, 'ratio': ratio, 'tested': tested, 'fired': fired})
    w = a.copy()
    if t is not None and fired_rows.any():
        w[fired_rows] = t[fired_rows]
    return recs, fired_rows, w


def mae_sel(y, p, sel):
    """R11: mean |y - p| over the selected rows (sel already restricted to labelled rows), saved row order."""
    yy = y[sel]
    if yy.size == 0:
        return None
    pp = p[sel]
    if not np.all(np.isfinite(pp)):
        raise RuntimeError('non-finite prediction on a labelled row')
    return float(np.mean(np.abs(yy - pp)))


# ----------------------------------------------------------------------------------------------------------------
# Verdict (re-implemented from its definition: D74 tag order, group jackknife, blocked jackknife)
# ----------------------------------------------------------------------------------------------------------------
def jackknife(values):
    v = np.asarray(values, dtype=float)
    n = len(v)
    mean = float(np.mean(v)) if n else None
    if n < 3:
        return {'mean': mean, 'se': None, 'low': None, 'high': None, 'n': n}
    loo = np.array([np.mean(np.delete(v, i)) for i in range(n)])
    se = float(np.sqrt((n - 1) / n * np.sum((loo - np.mean(loo)) ** 2)))
    return {'mean': mean, 'se': se, 'low': mean - Z * se, 'high': mean + Z * se, 'n': n}


def d74_tag(declined, d, jk, band):
    if declined:
        return 'declined'
    if len(d) and np.all(d == 0):
        return 'identical'
    if jk['se'] is None or not math.isfinite(jk['se']):
        return 'cannot_tell'
    low, high, mean = jk['low'], jk['high'], jk['mean']
    if low >= -band and high <= band:
        return 'does_not_help_equivalent'
    if low > 0 and mean >= band:
        return 'helps'
    if high < 0 and mean <= -band:
        return 'hurts'
    return 'cannot_tell'


def verdict_block(P, col, ref_label, blocks_of_group):
    """Per-group MAE(reference) - MAE(column) over labelled rows; jackknife; D74 tag; blocked jackknife."""
    y, ref, grp = P['y'], P['ref'], P['group']
    lab = np.isfinite(y)
    glist = sorted(set(grp[lab].tolist()))
    d = []
    for g in glist:
        sel = lab & (grp == g)
        d.append(mae_sel(y, ref, sel) - mae_sel(y, col, sel))
    d = np.array(d, dtype=float)
    jk = jackknife(d)
    tag = d74_tag(False, d, jk, P['band'])
    mean = jk['mean']
    flips = [g for g, v in zip(glist, d) if (mean > 0 and v < 0) or (mean < 0 and v > 0)]
    pooled_contrast = mae_sel(y, ref, lab) - mae_sel(y, col, lab)
    # blocked jackknife: each block valued at the mean of its scored groups' contrasts
    bid = [blocks_of_group[g] for g in glist]
    bvals = []
    for b in sorted(set(bid)):
        bvals.append(float(np.mean(np.array([v for v, bb in zip(d, bid) if bb == b]))))
    bj = jackknife(bvals)
    flag = bool(bj['se'] is not None and jk['se'] is not None and bj['se'] > BLOCK_FLAG_FACTOR * jk['se'])
    verdict = {'band': P['band'],
               'contrast': {'high': jk['high'], 'low': jk['low'], 'mean': jk['mean'], 'n_groups': jk['n'],
                            'se': jk['se']},
               'groups_better': int(np.sum(d > 0)), 'pooled_contrast': pooled_contrast, 'reference': ref_label,
               'sign_flip_groups': flips, 'tag': tag}
    blocked = {'flag': flag, 'high': bj['high'], 'low': bj['low'], 'mean': bj['mean'], 'n_blocks': bj['n'],
               'se': bj['se']}
    return verdict, blocked, dict(zip(glist, d.tolist()))


# ----------------------------------------------------------------------------------------------------------------
# Loading the passes
# ----------------------------------------------------------------------------------------------------------------
def run_dir(pkg, run):
    return '%s/%s/headline/%s' % (RUNS_ROOT, pkg, run)


def load_run(pkg, run, leads):
    d = run_dir(pkg, run)
    ctx = {'package': pkg, 'run': run, 'leads': leads, 'dir': d}
    ctx['adoption'] = read_json(d + '/adoption.json')
    ctx['verdict'] = read_json(d + '/verdict.json')
    ctx['derived'] = read_json(d + '/derived.json')
    ctx['checks'] = read_json(d + '/decision_checks.json')
    ctx['run_record'] = read_json(d + '/run_record.json')
    ctx['ladder'] = read_json(d + '/ladder/ladder.json')
    ctx['adoption_lead'] = {L: read_json(d + '/adoption_lead_%d.json' % L) for L in leads}
    v = ctx['derived']['R1']['value']
    ctx['cadence'] = {'kind': v['kind'], 'unit': v['unit'], 'length': v['length']}
    ctx['blocks'] = ctx['derived']['R14:overlap_blocks']['value']['block_of_group']
    sp = read_csv(d + '/score_pooled.csv')
    ctx['score_pooled'] = sp
    return ctx


def _frame_arrays(P, df, cols_extra=()):
    P['unit'] = df['unit'].to_numpy(dtype=object)
    P['group'] = df['group'].to_numpy(dtype=object)
    P['time'] = df['time'].to_numpy(dtype=np.int64)
    P['year'] = df['year'].to_numpy(dtype=np.int64)
    P['issue'] = df['issue'].to_numpy(dtype=np.int64)
    P['lead_col'] = df['lead'].to_numpy(dtype=np.int64)
    P['y'] = df['y'].to_numpy(dtype=np.float64)
    P['programme'] = df['programme'].to_numpy(dtype=object) if 'programme' in df.columns else None


def nowcast_pass(ctx):
    pkg, run, d = ctx['package'], ctx['run'], ctx['dir']
    adoption, verdict = ctx['adoption'], ctx['verdict']
    declined = bool(adoption['declined'])
    A = adoption['adopted']
    if A is None:
        raise RuntimeError('declined nowcast without an adopted arm: not covered (none of the five runs)')
    A_name = arm_name(A)
    level, ratio = adoption['penalty']['level'], adoption['penalty']['ratio']
    pt = point_text(level, ratio)
    W = routed_weightings(verdict['router_kind'])
    T, tkind = twin_of(A, W)
    T_name = arm_name(T)
    simpler = twin_is_simpler(A, T)
    # R5 skill guard of the twin at the adopted point
    twin_key = '%s@%s' % (T_name, pt)
    twin_mae = adoption['surface_mae'][twin_key]
    db = adoption['decision'].get('decline_baseline')
    base_key = db['key'] if (isinstance(db, dict) and db.get('key')) else '%s_trees_off_unweighted' % A['link']
    base_mae = adoption['surface_mae'][base_key]
    eligible = bool(twin_mae < base_mae)
    in_list = any(arm_name(e) == T_name for e in adoption['eligible'])
    # R6 reference gap on the decision surface
    ca, ct = '%s@%s' % (A_name, pt), '%s@%s' % (T_name, pt)
    ip = read_parquet(d + '/inner_preds.parquet', [ca, ct])
    ra, rt = ip[ca].to_numpy(dtype=np.float64), ip[ct].to_numpy(dtype=np.float64)
    del ip
    R = float(np.mean(np.abs(ra - rt)))
    R_rows = int(len(ra))
    if declined:
        status = 'not_applicable_declined'
    elif not simpler:
        status = 'inert_twin_not_simpler'
    elif not eligible:
        status = 'inert_twin_not_eligible'
    elif not (math.isfinite(R) and R > 0):
        status = 'not_tested_zero_reference_gap'
    else:
        status = 'active'
    # test rows
    tp = d + '/test_preds.parquet'
    cols = parquet_columns(tp)
    without_col = verdict['decline_target'] if declined else 'arm__' + A_name
    twin_col = 'arm__' + T_name
    twin_saved = twin_col in cols
    ref_col = verdict['reference']
    want = ['unit', 'group', 'time', 'year', 'lead', 'issue', 'y']
    if 'programme' in cols:
        want.append('programme')
    for c in (without_col, twin_col if twin_saved else None, ref_col):
        if c is not None and c not in want:
            want.append(c)
    df = read_parquet(tp, want)
    P = {'package': pkg, 'run': run, 'lead': 0, 'pass_name': 'nowcast', 'status': status, 'replayable': True,
         'adopted_arm': A_name, 'adopted_column': without_col, 'twin_arm': T_name, 'twin_kind': tkind,
         'twin_simpler': simpler, 'twin_eligible': eligible, 'twin_saved': twin_saved, 'declined': declined,
         'eligibility': {'twin_key': twin_key, 'twin_mae': twin_mae, 'baseline': base_key, 'baseline_mae': base_mae,
                         'eligible': eligible, 'in_adoption_eligible_list': in_list,
                         'point': {'level': level, 'ratio': ratio}},
         'R': R, 'R_rows': R_rows, 'ref_columns': [ca, ct], 'surface_sha256': ctx['checks']['surface_sha256'],
         'band': verdict['band'], 'reference_col': ref_col, 'cadence': ctx['cadence']}
    _frame_arrays(P, df)
    if not np.all(P['lead_col'] == 0):
        raise RuntimeError('nowcast rows with lead != 0')
    P['a'] = df[without_col].to_numpy(dtype=np.float64)
    P['t'] = df[twin_col].to_numpy(dtype=np.float64) if twin_saved else None
    P['ref'] = df[ref_col].to_numpy(dtype=np.float64)
    if P['t'] is not None and not (np.all(np.isfinite(P['a'])) and np.all(np.isfinite(P['t']))):
        raise RuntimeError('non-finite adopted or twin prediction in %s nowcast' % pkg)
    P['keys'] = batch_keys(P['issue'], ctx['cadence'])
    P['order'] = batch_order(P['keys'])
    P['bidx'] = {k: np.flatnonzero(P['keys'] == k) for k in P['order']}
    recs, fired_rows, w = decide(P['a'], P['t'], P['bidx'], P['order'], R, status)
    P['recs'], P['fired_rows'], P['w'] = recs, fired_rows, w
    return P


def lead_pass(ctx, L):
    pkg, run, d = ctx['package'], ctx['run'], ctx['dir']
    al = ctx['adoption_lead'][L]
    pinned = al['pinned']
    pinned_name = arm_name(pinned)
    gp = bool(al['guard_passed'])
    W = routed_weightings(ctx['verdict']['router_kind'])
    T, tkind = twin_of(pinned, W)
    T_name = arm_name(T)
    simpler = twin_is_simpler(pinned, T)
    lv = ctx['ladder']['verdicts'][str(L)]
    if not gp:
        status = 'not_applicable_declined'
        without_col = lv['adopted']                      # the lead's decline target (v1 final answer)
        if al['adopted'] is not None:
            raise RuntimeError('declined lead with an adopted arm')
    else:
        without_col = 'arm__' + pinned_name
        if lv['adopted'] != without_col or arm_name(al['adopted']) != pinned_name:
            raise RuntimeError('lead %d: pinned arm and ladder record differ' % L)
        status = 'inert_twin_not_simpler' if not simpler else 'not_replayable_twin_not_saved'
    replayable = status != 'not_replayable_twin_not_saved'
    tp = d + '/ladder/lead_%d/test_preds.parquet' % L
    cols = parquet_columns(tp)
    twin_saved = ('arm__' + T_name) in cols
    if status == 'not_replayable_twin_not_saved' and twin_saved:
        raise RuntimeError('lead %d: the twin IS saved; spec R10 does not hold' % L)
    want = ['unit', 'group', 'time', 'year', 'lead', 'issue', 'y']
    if 'programme' in cols:
        want.append('programme')
    want.append(without_col)
    df = read_parquet(tp, want)
    P = {'package': pkg, 'run': run, 'lead': L, 'pass_name': 'lead %d' % L, 'status': status,
         'replayable': replayable, 'adopted_arm': pinned_name, 'adopted_column': without_col, 'twin_arm': T_name,
         'twin_kind': tkind, 'twin_simpler': simpler, 'twin_eligible': None, 'twin_saved': twin_saved,
         'declined': not gp, 'guard_passed': gp, 'R': None, 'R_rows': None, 'band': ctx['verdict']['band'],
         'cadence': ctx['cadence']}
    _frame_arrays(P, df)
    if not np.all(P['lead_col'] == L):
        raise RuntimeError('lead %d rows with another lead' % L)
    P['a'] = df[without_col].to_numpy(dtype=np.float64)
    P['t'] = None
    P['ref'] = None
    P['keys'] = batch_keys(P['issue'], ctx['cadence'])
    P['order'] = batch_order(P['keys'])
    P['bidx'] = {k: np.flatnonzero(P['keys'] == k) for k in P['order']}
    if replayable:
        recs, fired_rows, w = decide(P['a'], None, P['bidx'], P['order'], None, status)
        if fired_rows.any() or not np.array_equal(w.view(np.int64), P['a'].view(np.int64)):
            raise RuntimeError('lead %d: with != without on a pass that cannot switch' % L)
    else:
        recs = [{'batch': k, 'rows': int(len(P['bidx'][k])), 'gap': None, 'ratio': None, 'tested': None,
                 'fired': None} for k in P['order']]
        fired_rows, w = None, None
    P['recs'], P['fired_rows'], P['w'] = recs, fired_rows, w
    return P


# ----------------------------------------------------------------------------------------------------------------
# Pass summaries
# ----------------------------------------------------------------------------------------------------------------
def pass_totals(P):
    lab = np.isfinite(P['y'])
    out = {'saved_rows': int(len(P['y'])), 'labelled_rows': int(lab.sum()), 'batches': len(P['recs'])}
    out['mae_without'] = mae_sel(P['y'], P['a'], lab)
    if P['replayable']:
        out['mae_with'] = mae_sel(P['y'], P['w'], lab)
        out['batches_tested'] = int(sum(r['tested'] for r in P['recs']))
        out['batches_fired'] = int(sum(r['fired'] for r in P['recs']))
        out['rows_switched'] = int(P['fired_rows'].sum())
        out['labelled_rows_switched'] = int((P['fired_rows'] & lab).sum())
        if P['t'] is not None:
            out['rows_value_changed'] = int((P['fired_rows'] & (P['t'] != P['a'])).sum())
        else:
            out['rows_value_changed'] = 0
        out['change'] = out['mae_with'] - out['mae_without']
        out['change_pct'] = out['change'] / out['mae_without'] * 100.0
        tested = [r['ratio'] for r in P['recs'] if r['tested']]
        out['max_ratio_tested'] = max(tested) if tested else None
        out['fired_batches'] = [r['batch'] for r in P['recs'] if r['fired']]
    else:
        for k in ('mae_with', 'batches_tested', 'batches_fired', 'rows_switched', 'labelled_rows_switched',
                  'rows_value_changed', 'change', 'change_pct', 'max_ratio_tested'):
            out[k] = None
        out['fired_batches'] = None
    out['batches_ge30'] = int(sum(r['rows'] >= MIN_ROWS for r in P['recs']))
    out['rows_in_small_batches'] = int(sum(r['rows'] for r in P['recs'] if r['rows'] < MIN_ROWS))
    if P['t'] is not None:
        ge = [r['ratio'] for r in P['recs'] if r['rows'] >= MIN_ROWS]
        out['max_ratio_ge30'] = max(ge) if ge else None
        out['max_ratio_computed'] = max(r['ratio'] for r in P['recs'])
    else:
        out['max_ratio_ge30'] = None
        out['max_ratio_computed'] = None
    return out


def subset_masks(P, q75):
    y = P['y']
    lab = np.isfinite(y)
    with np.errstate(invalid='ignore'):
        return [
            ('all', lab, None),
            ('y_gt_0', lab & (y > 0), 'y > 0'),
            ('y_eq_0', lab & (y == 0), 'y == 0'),
            ('y_ge_50', lab & (y >= 50), 'y >= 50'),
            ('y_lt_50', lab & (y < 50), 'y < 50'),
            ('y_gt_q75', lab & (y > q75), 'y > %r' % q75),
            ('y_le_q75', lab & (y <= q75), 'y <= %r' % q75),
        ]


def ww_lines(P, T, q75):
    """The lines of WITH_WITHOUT.csv this pass gives (all rows, and the coral subsets)."""
    y = P['y']
    lab = np.isfinite(y)
    subs = [('all rows', lab)]
    if P['package'] == 'coral':
        with np.errstate(invalid='ignore'):
            subs += [('positive label (y > 0)', lab & (y > 0)),
                     ("severe (y > %r: q75 of positive donor labels at the lead's fit cut)" % q75, lab & (y > q75)),
                     ('severe (y >= 50)', lab & (y >= 50))]
    lines = []
    for label, sel in subs:
        mw = mae_sel(y, P['a'], sel)
        mwith = mae_sel(y, P['w'], sel) if P['replayable'] else None
        ch = (mwith - mw) if mwith is not None else None
        lines.append({
            'package': P['package'], 'run': P['run'], 'lead': P['lead'],
            'pass': 'nowcast' if P['lead'] == 0 else 'lead %d' % P['lead'], 'subset': label,
            'n': int(sel.sum()), 'status': P['status'], 'replayable': P['replayable'], 'batches': T['batches'],
            'batches_tested': T['batches_tested'], 'batches_fired': T['batches_fired'],
            'rows_switched': T['rows_switched'], 'mae_without': mw, 'mae_with': mwith, 'change': ch,
            'change_pct': (ch / mw * 100.0) if ch is not None else None,
            'adopted_column': P['adopted_column'], 'twin_arm': P['twin_arm'], 'twin_kind': P['twin_kind'],
            'twin_simpler': P['twin_simpler'], 'twin_eligible': P['twin_eligible'],
            'reference_gap': P['R'], 'max_ratio_tested': T['max_ratio_tested'],
            'fired_batches': (' '.join(T['fired_batches']) if T['fired_batches'] else None),
        })
    return lines


def score_lines(P):
    """pooled / year / group lines: MAE without, with, reference and n over labelled rows."""
    y = P['y']
    lab = np.isfinite(y)
    out = {}

    def one(sel):
        return {'mae_without': mae_sel(y, P['a'], sel), 'mae_with': mae_sel(y, P['w'], sel),
                'mae_reference': mae_sel(y, P['ref'], sel), 'n': int(sel.sum())}
    out[('pooled', '')] = one(lab)
    for yr in sorted(set(P['year'][lab].tolist())):
        out[('year', int(yr))] = one(lab & (P['year'] == yr))
    for g in sorted(set(P['group'][lab].tolist())):
        out[('group', g)] = one(lab & (P['group'] == g))
    return out


def rows_frame(P, gate_style=True):
    cols = {'unit': P['unit'], 'group': P['group'], 'time': P['time'], 'year': P['year'], 'issue': P['issue'],
            'y': P['y'], 'batch': P['keys'], 'adopted': P['a']}
    if gate_style:
        if P['t'] is not None:
            cols['twin'] = P['t']
    else:
        cols['twin'] = P['t'] if P['t'] is not None else np.full(len(P['a']), np.nan)
    if P['replayable']:
        cols['with_alarm'] = P['w']
        cols['fired'] = P['fired_rows']
    return pd.DataFrame(cols)


def frames_equal(mine, gate):
    """pandas equals after reset_index, plus a NaN-aware bitwise check of every float column."""
    out = {'columns_expected': list(gate.columns), 'columns_obtained': list(mine.columns)}
    if list(mine.columns) != list(gate.columns) or len(mine) != len(gate):
        out['equal'] = False
        out['rows_expected'] = len(gate)
        out['rows_obtained'] = len(mine)
        return out
    m, g = mine.reset_index(drop=True), gate.reset_index(drop=True)
    pandas_equals = bool(m.equals(g))
    bad_cols, first_rows = [], {}
    for c in g.columns:
        a, b = m[c].to_numpy(), g[c].to_numpy()
        if g[c].dtype.kind == 'f':
            a = a.astype(np.float64)
            b = b.astype(np.float64)
            na, nb = np.isnan(a), np.isnan(b)
            diff = (na != nb) | (~na & ~nb & (a.view(np.int64) != b.view(np.int64)))
        else:
            diff = ~(a == b)
        if diff.any():
            bad_cols.append(c)
            ix = np.flatnonzero(diff)[:5]
            first_rows[c] = [{'row': int(i), 'expected': g[c].iloc[i], 'obtained': m[c].iloc[i]} for i in ix]
    out['pandas_equals'] = pandas_equals
    out['bitwise_columns_differing'] = bad_cols
    out['first_differing_rows'] = first_rows
    out['equal'] = pandas_equals and not bad_cols
    return out


# ----------------------------------------------------------------------------------------------------------------
# JSON helpers
# ----------------------------------------------------------------------------------------------------------------
def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return f if math.isfinite(f) else None
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    return o


def libraries():
    return {'python': sys.version, 'executable': sys.executable, 'flags_isolated': bool(sys.flags.isolated),
            'dont_write_bytecode': bool(sys.dont_write_bytecode), 'numpy': np.__version__,
            'pandas': pd.__version__, 'pyarrow': pyarrow.__version__, 'platform': platform.platform()}


DRY_RUN = '--dry-run' in sys.argv[1:]


def write_result(result):
    path = OUT + '/result_B.json'
    if DRY_RUN:
        print('DRY RUN: result_B.json not written')
        return path + ' (not written)'
    txt = json.dumps(clean(result), indent=1, allow_nan=False, ensure_ascii=False)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(txt + '\n')
    return path


# ----------------------------------------------------------------------------------------------------------------
# The gate
# ----------------------------------------------------------------------------------------------------------------
def gate_g1(passes, totals, edges, ww_gate):
    c = Cmp()
    mine = []
    for key, P in passes.items():
        q75 = edges.get(P['lead']) if P['package'] == 'coral' else None
        mine.extend(ww_lines(P, totals[key], q75))
    c.eq('line count', len(ww_gate), len(mine))
    gate_rows = ww_gate.to_dict('records')
    fields = ['status', 'replayable', 'adopted_column', 'twin_arm', 'twin_kind', 'twin_simpler', 'twin_eligible',
              'reference_gap', 'batches', 'batches_tested', 'batches_fired', 'rows_switched', 'n', 'mae_without',
              'mae_with', 'max_ratio_tested', 'fired_batches', 'change', 'change_pct', 'pass', 'run']
    for i, g in enumerate(gate_rows):
        if i >= len(mine):
            break
        m = mine[i]
        tag = '%s/%s/%s' % (g['package'], g['lead'], g['subset'])
        c.eq(tag + ' package', g['package'], m['package'])
        c.eq(tag + ' lead', int(g['lead']), m['lead'])
        c.eq(tag + ' subset label', g['subset'], m['subset'])
        for f in fields:
            c.eq('%s %s' % (tag, f), g[f], m[f])
    # spec section 2 statuses
    for key, P in passes.items():
        c.eq('spec section 2 status %s/%d' % key, SPEC_STATUS[key], P['status'])
    # spec headline restatements (coral nowcast)
    Tc = totals[('coral', 0)]
    Pc = passes[('coral', 0)]
    c.eq('spec coral fired batches', SPEC_CORAL['fired'], Tc['fired_batches'])
    c.eq('spec coral rows switched', SPEC_CORAL['rows_switched'], Tc['rows_switched'])
    c.eq('spec coral batches', SPEC_CORAL['batches'], Tc['batches'])
    c.eq('spec coral tested', SPEC_CORAL['tested'], Tc['batches_tested'])
    c.eq('spec coral R', SPEC_CORAL['R'], Pc['R'])
    c.eq('spec coral R rows', SPEC_CORAL['R_rows'], Pc['R_rows'])
    c.eq('spec coral mae without', SPEC_CORAL['mae_without'], Tc['mae_without'])
    c.eq('spec coral mae with', SPEC_CORAL['mae_with'], Tc['mae_with'])
    c.eq('spec coral max ratio tested', SPEC_CORAL['max_ratio'], Tc['max_ratio_tested'])
    # without = the locked pooled MAE of the adopted column (verdict.json) at every nowcast
    for key, P in passes.items():
        if P['lead'] == 0:
            c.eq('verdict.json pooled_mae_adopted %s' % key[0], P['verdict_pooled_mae_adopted'],
                 totals[key]['mae_without'])
    # not-replayable notes: "<k> of <n> batches have >= 30 rows"
    for g in gate_rows:
        if g['status'] == 'not_replayable_twin_not_saved' and g['subset'] == 'all rows':
            mt = re.search(r'(\d+) of (\d+) batches have >= 30 rows', str(g['note']))
            T = totals[(g['package'], int(g['lead']))]
            c.check('%s/%s note parsed' % (g['package'], g['lead']), mt is not None)
            if mt:
                c.eq('%s/%s note batches >= 30 rows' % (g['package'], g['lead']), int(mt.group(1)), T['batches_ge30'])
                c.eq('%s/%s note batches' % (g['package'], g['lead']), int(mt.group(2)), T['batches'])
    return c.result(lines_obtained=len(mine)), mine


def gate_g2(passes, totals, gate_json):
    c = Cmp()
    for pkg, run, _ in RUNS:
        P, T, G = passes[(pkg, 0)], totals[(pkg, 0)], gate_json[pkg]
        c.eq(pkg + ' status', G['status'], P['status'])
        c.eq(pkg + ' adopted_arm', G['adopted_arm'], P['adopted_arm'])
        c.eq(pkg + ' adopted_column', G['adopted_column'], P['adopted_column'])
        c.eq(pkg + ' twin_arm', G['twin_arm'], P['twin_arm'])
        c.eq(pkg + ' twin_kind', G['twin_kind'], P['twin_kind'])
        c.eq(pkg + ' twin_simpler', G['twin_simpler'], P['twin_simpler'])
        c.eq(pkg + ' twin_eligible', G['twin_eligible'], P['twin_eligible'])
        c.eq(pkg + ' twin_routed', G['twin_routed'], P['twin_saved'])
        c.eq(pkg + ' test_rows', G['test_rows'], T['saved_rows'])
        c.eq(pkg + ' batches_tested', G['batches_tested'], T['batches_tested'])
        c.eq(pkg + ' batches_fired', G['batches_fired'], T['batches_fired'])
        c.eq(pkg + ' rows_switched', G['rows_switched'], T['rows_switched'])
        c.eq(pkg + ' constant min rows', G['constants']['A8.alarm_min_batch_rows'], MIN_ROWS)
        c.eq(pkg + ' constant threshold', G['constants']['A8.alarm_ratio_threshold'], THRESHOLD)
        eb = G['eligibility_basis']
        E = P['eligibility']
        c.eq(pkg + ' eligibility twin_key', eb['twin_key'], E['twin_key'])
        c.eq(pkg + ' eligibility twin_mae', eb['twin_mae'], E['twin_mae'])
        c.eq(pkg + ' eligibility baseline', eb['baseline'], E['baseline'])
        c.eq(pkg + ' eligibility baseline_mae', eb['baseline_mae'], E['baseline_mae'])
        c.eq(pkg + ' eligibility eligible', eb['eligible'], E['eligible'])
        c.eq(pkg + ' eligibility in list (information)', eb['in_adoption_eligible_list'],
             E['in_adoption_eligible_list'])
        c.eq(pkg + ' eligibility point level', eb['point']['level'], E['point']['level'])
        c.eq(pkg + ' eligibility point ratio', eb['point']['ratio'], E['point']['ratio'])
        rf = G['reference']
        c.eq(pkg + ' reference columns', rf['columns'], P['ref_columns'])
        c.eq(pkg + ' reference rows', rf['rows'], P['R_rows'])
        c.eq(pkg + ' reference gap', rf['gap'], P['R'])
        c.eq(pkg + ' reference surface_sha256 (decision_checks.json)', rf['surface_sha256'], P['surface_sha256'])
        c.eq(pkg + ' batch count', len(G['batches']), len(P['recs']))
        for gb, mb in zip(G['batches'], P['recs']):
            for f in ('batch', 'rows', 'gap', 'ratio', 'tested', 'fired'):
                c.eq('%s batch %s %s' % (pkg, gb['batch'], f), gb[f], mb[f])
        if pkg in SPEC_G2_INERT_MAX:
            c.eq(pkg + ' largest computed (not tested) ratio vs spec', SPEC_G2_INERT_MAX[pkg], T['max_ratio_computed'])
            c.eq(pkg + ' largest computed ratio vs gate json', max(b['ratio'] for b in G['batches']),
                 T['max_ratio_computed'])
            c.eq(pkg + ' tested batches (code sense)', 0, T['batches_tested'])
    return c.result()


def gate_g3(passes, gate_scores):
    c = Cmp()
    lines_out = {}
    for pkg, run, _ in RUNS:
        P = passes[(pkg, 0)]
        mine = score_lines(P)
        lines_out[pkg] = mine
        g = gate_scores[pkg]
        gkeys = []
        for r in g.to_dict('records'):
            line = r['line']
            if line == 'pooled':
                k = ('pooled', '')
            elif line == 'year':
                k = ('year', int(float(r['key'])))
            elif line == 'group':
                k = ('group', r['key'])
            else:
                c.check('%s unknown line kind %s' % (pkg, line), False)
                continue
            gkeys.append(k)
            if k not in mine:
                c.check('%s line %s present' % (pkg, k), False)
                continue
            for f in ('mae_without', 'mae_with', 'mae_reference', 'n'):
                c.eq('%s %s %s %s' % (pkg, k[0], k[1], f), r[f], mine[k][f])
        c.eq(pkg + ' line keys', sorted(map(str, gkeys)), sorted(map(str, mine.keys())))
    # coral year lines restated in the spec
    cy = lines_out['coral']
    spec_years = {2016: (873, 12.406328256098309, 10.681069664805374), 2017: (565, 3.5692507744181308, 3.6880301411805525),
                  2018: (443, 1.280418254929322, 1.280418254929322), 2019: (431, 4.805509495430039, 5.043624464950422)}
    for yr, (n, wo, wi) in spec_years.items():
        c.eq('spec coral year %d n' % yr, n, cy[('year', yr)]['n'])
        c.eq('spec coral year %d without' % yr, wo, cy[('year', yr)]['mae_without'])
        c.eq('spec coral year %d with' % yr, wi, cy[('year', yr)]['mae_with'])
    return c.result(), lines_out


def gate_g4(passes, totals):
    c = Cmp()
    det = {}
    for pkg, run, _ in RUNS:
        P = passes[(pkg, 0)]
        small = [r for r in P['recs'] if r['rows'] < MIN_ROWS]
        det[pkg] = {'small_batches': len(small), 'rows': int(sum(r['rows'] for r in small))}
        if pkg == 'coral':
            c.eq('coral small batches', SPEC_G4['coral_small_batches'], len(small))
            c.eq('coral small rows', SPEC_G4['coral_small_rows'], det[pkg]['rows'])
            r07 = [r for r in P['recs'] if r['batch'] == '2016-07']
            c.check('coral 2016-07 present', len(r07) == 1)
            if r07:
                c.eq('coral 2016-07 ratio', SPEC_G4['coral_2016_07_ratio'], r07[0]['ratio'])
                c.eq('coral 2016-07 rows', SPEC_G4['coral_2016_07_rows'], r07[0]['rows'])
                c.eq('coral 2016-07 tested', False, r07[0]['tested'])
        else:
            c.eq(pkg + ' small batches', 0, len(small))
    return c.result(per_nowcast=det)


def gate_g5(passes, gate_rows):
    c = Cmp()
    det = {}
    for key, P in passes.items():
        g = gate_rows[key]
        mine = rows_frame(P, gate_style=True)
        r = frames_equal(mine, g)
        det['%s/%d' % key] = {'equal': r['equal'], 'columns': r['columns_expected'],
                              'pandas_equals': r.get('pandas_equals'),
                              'bitwise_columns_differing': r.get('bitwise_columns_differing'),
                              'first_differing_rows': r.get('first_differing_rows')}
        c.check('rows %s/%d equal' % key, r['equal'], det['%s/%d' % key])
    return c.result(files=det)


def gate_g6(passes):
    c = Cmp()
    P = passes[('coral', 0)]
    out = {}
    for th in INFO_THRESHOLDS:
        recs, fr, w = decide(P['a'], P['t'], P['bidx'], P['order'], P['R'], P['status'], threshold=th)
        m = mae_sel(P['y'], w, np.isfinite(P['y']))
        out[repr(th)] = {'mae_with': m, 'rounded_3': round(m, 3), 'batches_switched': int(sum(r['fired'] for r in recs))}
        if th in SPEC_G6:
            c.eq('coral threshold %r pooled MAE with (3 decimals)' % th, SPEC_G6[th], round(m, 3))
    # everything else as at 2.0: defo switches nothing at any of these thresholds; inert passes cannot act
    D = passes[('defo', 0)]
    for th in INFO_THRESHOLDS:
        recs, fr, w = decide(D['a'], D['t'], D['bidx'], D['order'], D['R'], D['status'], threshold=th)
        c.eq('defo threshold %r batches switched' % th, 0, int(sum(r['fired'] for r in recs)))
    return c.result(coral=out)


def gate_g7(passes, totals, gate_json, ctxs):
    c = Cmp()
    out = {}
    for pkg, run, _ in RUNS:
        P, G = passes[(pkg, 0)], gate_json[pkg]['scores']
        V = ctxs[pkg]['verdict']
        ref_label = V['verdict']['reference']
        vw, bw, dw = verdict_block(P, P['w'], ref_label, ctxs[pkg]['blocks'])
        vo, bo, do = verdict_block(P, P['a'], ref_label, ctxs[pkg]['blocks'])
        lab = np.isfinite(P['y'])
        pm = {'with': mae_sel(P['y'], P['w'], lab), 'without': mae_sel(P['y'], P['a'], lab),
              'reference': mae_sel(P['y'], P['ref'], lab)}
        out[pkg] = {'verdict_with': vw, 'blocked_jackknife_with': bw, 'verdict_without_recomputed': vo,
                    'blocked_jackknife_without_recomputed': bo, 'verdict_without_locked': V['verdict'],
                    'blocked_jackknife_without_locked': V['blocked_jackknife'], 'band': V['band'],
                    'pooled_mae_with': pm['with'], 'pooled_mae_without': pm['without'],
                    'pooled_mae_reference': pm['reference'], 'group_contrast_with': dw}
        c.eq(pkg + ' band', G['band'], V['band'])
        c.eq(pkg + ' pooled_mae_with', G['pooled_mae_with'], pm['with'])
        c.eq(pkg + ' pooled_mae_without', G['pooled_mae_without'], pm['without'])
        c.eq(pkg + ' pooled_mae_reference', G['pooled_mae_reference'], pm['reference'])
        for name, gv, mv in (('verdict_with', G['verdict_with'], vw), ('verdict_without', G['verdict_without'], vo),
                             ('verdict.json verdict vs recomputed without', V['verdict'], vo)):
            c.eq('%s %s tag' % (pkg, name), gv['tag'], mv['tag'])
            c.eq('%s %s band' % (pkg, name), gv['band'], mv['band'])
            c.eq('%s %s groups_better' % (pkg, name), gv['groups_better'], mv['groups_better'])
            c.eq('%s %s pooled_contrast' % (pkg, name), gv['pooled_contrast'], mv['pooled_contrast'])
            c.eq('%s %s reference' % (pkg, name), gv['reference'], mv['reference'])
            c.eq('%s %s sign_flip_groups' % (pkg, name), gv['sign_flip_groups'], mv['sign_flip_groups'])
            for f in ('mean', 'low', 'high', 'se', 'n_groups'):
                c.eq('%s %s contrast %s' % (pkg, name, f), gv['contrast'][f], mv['contrast'][f])
        for name, gv, mv in (('blocked_jackknife_with', G['blocked_jackknife_with'], bw),
                             ('verdict.json blocked_jackknife vs recomputed without', V['blocked_jackknife'], bo)):
            for f in ('flag', 'mean', 'low', 'high', 'se', 'n_blocks'):
                c.eq('%s %s %s' % (pkg, name, f), gv[f], mv[f])
    return c.result(), out


def gate_g8(passes, p604):
    c = Cmp()
    P = passes[('coral', 0)]
    y, a, t = P['y'], P['a'], P['t']
    lab = np.isfinite(y)
    prog = P['programme']
    blend = 0.5 * a + 0.5 * t
    M = p604['methods']
    obt = {}
    for meth, col in (('C', a), ('T', t), ('M1', t), ('M2', blend), ('M3', blend)):
        obt[meth] = {'mae': mae_sel(y, col, lab), 'per_programme': {}, 'per_year': {},
                     'bleached_mae': mae_sel(y, col, lab & (y > 0))}
        c.eq('%s pooled MAE' % meth, M[meth]['mae'], obt[meth]['mae'])
        c.eq('%s bleached (y > 0) MAE' % meth, M[meth]['bleached_mae'], obt[meth]['bleached_mae'])
        for pg, rec in M[meth]['per_programme'].items():
            sel = lab & (prog == pg)
            obt[meth]['per_programme'][pg] = {'n': int(sel.sum()), 'mae': mae_sel(y, col, sel)}
            c.eq('%s %s n' % (meth, pg), rec['n'], int(sel.sum()))
            c.eq('%s %s MAE' % (meth, pg), rec['mae'], obt[meth]['per_programme'][pg]['mae'])
        for yr, v in M[meth]['per_year'].items():
            sel = lab & (P['year'] == int(yr))
            obt[meth]['per_year'][yr] = mae_sel(y, col, sel)
            c.eq('%s year %s MAE' % (meth, yr), v, obt[meth]['per_year'][yr])
    c.eq('C programme set', sorted(M['C']['per_programme'].keys()), sorted(set(prog.tolist())))
    fin = np.isfinite(a) & np.isfinite(t)
    ww_ratio = float(np.mean(np.abs(a[fin] - t[fin]))) / P['R']
    obt['whole_window_ratio'] = ww_ratio
    obt['whole_window_rows'] = int(fin.sum())
    c.eq('whole-window ratio (Part 603 sanity, now)', p604['sanity_part603']['alarm_ratio']['now'], ww_ratio)
    c.eq('whole-window rows', 2312, int(fin.sum()))
    c.eq('M1 = twin on every row (spec 6.14748576299595)', 6.14748576299595, obt['M1']['mae'])
    c.eq('M2 = even blend on every row (spec 6.393951387338696)', 6.393951387338696, obt['M2']['mae'])
    return c.result(obtained=obt)


def gate_g9(ww_gate):
    c = Cmp()
    hist = read_csv(HISTORY_WW, dtype={'fired_batches': object})
    c.eq('history row count', len(ww_gate), len(hist))
    c.eq('history columns', list(ww_gate.columns), list(hist.columns))
    if len(hist) == len(ww_gate) and list(hist.columns) == list(ww_gate.columns):
        for col in ww_gate.columns:
            if col == 'note':
                continue
            for i, (e, o) in enumerate(zip(ww_gate[col].tolist(), hist[col].tolist())):
                c.eq('row %d %s' % (i, col), e, o)
    return c.result(note='information: replay/WITH_WITHOUT.csv (build 663ab8ef, before AF2) vs the gate file, '
                         'every column except "note"')


# ----------------------------------------------------------------------------------------------------------------
# Section 6 quantities (only after G0-G8 pass)
# ----------------------------------------------------------------------------------------------------------------
def flag_of(w, wo):
    if w is None or wo is None:
        return None
    if _bits(w) == _bits(wo):
        return 'same'
    return 'better' if w < wo else 'worse'


def q1_passes(passes, totals):
    out = {}
    for key, P in passes.items():
        T = totals[key]
        if P['lead'] == 0:
            guard = P['twin_eligible']
        elif P['status'] == 'not_replayable_twin_not_saved':
            guard = 'not saved'
        else:
            guard = 'not needed'
        e = {'package': P['package'], 'run': P['run'], 'lead': P['lead'], 'pass': P['pass_name'],
             'status': P['status'], 'plain_status': PLAIN[P['status']], 'adopted_column': P['adopted_column'],
             'twin_arm': P['twin_arm'], 'twin_kind': P['twin_kind'], 'twin_simpler': P['twin_simpler'],
             'twin_passes_skill_guard': guard, 'twin_saved': P['twin_saved'], 'replayable': P['replayable'],
             'saved_rows': T['saved_rows'], 'labelled_rows': T['labelled_rows'], 'batches': T['batches'],
             'batches_ge30_saved_rows': T['batches_ge30'], 'saved_rows_in_batches_lt30': T['rows_in_small_batches'],
             'batches_tested': T['batches_tested'], 'batches_switched': T['batches_fired'],
             'saved_rows_switched': T['rows_switched'], 'labelled_rows_switched': T['labelled_rows_switched'],
             'rows_value_changed': T['rows_value_changed'], 'mae_without': T['mae_without'],
             'mae_with': T['mae_with'], 'change': T['change'], 'change_pct': T['change_pct'],
             'band': P['band'],
             'change_in_band_units': (T['change'] / P['band']) if T['change'] is not None else None,
             'reference_gap': P['R'], 'reference_gap_rows': P['R_rows'], 'max_ratio_tested': T['max_ratio_tested'],
             'max_ratio_ge30': T['max_ratio_ge30'], 'switched_batches': T['fired_batches'],
             'post_hoc': True, 'circular': P['package'] == 'coral'}
        if P['lead'] == 0 and P['status'] != 'active':
            e['max_ratio_ge30_note'] = 'information only: the rule could not act'
        if P['lead'] == 0:
            e['twin_guard_basis'] = P['eligibility']
        out['%s/%d' % key] = e
    return out


def q2_batches(passes):
    out = {}
    for pkg, run, _ in RUNS:
        P = passes[(pkg, 0)]
        lab = np.isfinite(P['y'])
        for r in P['recs']:
            ix = P['bidx'][r['batch']]
            yrs = sorted(set(P['year'][ix].tolist()))
            if len(yrs) != 1:
                raise RuntimeError('%s nowcast batch %s spans years %r' % (pkg, r['batch'], yrs))
            sel = np.zeros(len(P['y']), dtype=bool)
            sel[ix] = True
            sel &= lab
            mw, mwi = mae_sel(P['y'], P['a'], sel), mae_sel(P['y'], P['w'], sel)
            fr = P['fired_rows'][ix]
            out['%s/0/%s' % (pkg, r['batch'])] = {
                'package': pkg, 'lead': 0, 'batch': r['batch'], 'year': int(yrs[0]), 'saved_rows': r['rows'],
                'labelled_rows': int(sel.sum()), 'gap': r['gap'], 'ratio': r['ratio'], 'tested': r['tested'],
                'switched': r['fired'], 'small_batch_lt30': r['rows'] < MIN_ROWS,
                'ratio_above_threshold': bool(r['ratio'] > THRESHOLD),
                'saved_rows_switched': int(fr.sum()), 'labelled_rows_switched': int((fr & lab[ix]).sum()),
                'rows_value_changed': int((fr & (P['t'][ix] != P['a'][ix])).sum()),
                'mae_without': mw, 'mae_with': mwi, 'change': (mwi - mw) if mw is not None else None,
                'note': ('ratio computed; not tested: the rule cannot act on this pass'
                         if P['status'] != 'active' else None)}
    return out


def q3_by_year(passes):
    out = {}
    worse = []
    for key, P in passes.items():
        if not P['replayable']:
            continue
        lab = np.isfinite(P['y'])
        batch_years = {}
        for r in P['recs']:
            ix = P['bidx'][r['batch']]
            batch_years[r['batch']] = sorted(set(P['year'][ix].tolist()))
            if P['lead'] == 0 and len(batch_years[r['batch']]) != 1:
                raise RuntimeError('batch spans years at lead 0')
        any_switch = bool(P['fired_rows'].any())
        for yr in sorted(set(P['year'].tolist())):
            sel = lab & (P['year'] == yr)
            mw, mwi = mae_sel(P['y'], P['a'], sel), mae_sel(P['y'], P['w'], sel)
            if not any_switch and mw is not None and _bits(mw) != _bits(mwi):
                raise RuntimeError('with != without in a year of a pass where nothing switched')
            in_year = [r for r in P['recs'] if yr in batch_years[r['batch']]]
            ysel = P['year'] == yr
            fl = flag_of(mwi, mw)
            e = {'package': P['package'], 'lead': P['lead'], 'year': int(yr), 'n': int(sel.sum()),
                 'saved_rows': int(ysel.sum()), 'mae_without': mw, 'mae_with': mwi,
                 'change': (mwi - mw) if mw is not None else None, 'flag': fl,
                 'batches': len(in_year), 'batches_tested': int(sum(r['tested'] for r in in_year)),
                 'batches_switched': int(sum(r['fired'] for r in in_year)),
                 'saved_rows_switched': int((P['fired_rows'] & ysel).sum()),
                 'labelled_rows_switched': int((P['fired_rows'] & sel).sum())}
            if P['lead'] != 0:
                e['batches_spanning_two_years'] = int(sum(len(batch_years[r['batch']]) > 1 for r in in_year))
            out['%s/%d/%d' % (P['package'], P['lead'], yr)] = e
            if P['lead'] == 0 and fl == 'worse':
                worse.append('%s/%d' % (P['package'], yr))
    return out, worse


def q4_q5_programme(P):
    y, a, w, prog, yr = P['y'], P['a'], P['w'], P['programme'], P['year']
    lab = np.isfinite(y)
    N = int(lab.sum())
    pooled_wo, pooled_w = mae_sel(y, a, lab), mae_sel(y, w, lab)
    pooled_change = pooled_w - pooled_wo
    fired_batches = [r['batch'] for r in P['recs'] if r['fired']]

    def cell(sel, savedsel):
        mw, mwi = mae_sel(y, a, sel), mae_sel(y, w, sel)
        held = sum(1 for b in fired_batches if np.any(savedsel[P['bidx'][b]]))
        n = int(sel.sum())
        contrib = (n / N) * (mwi - mw)
        return {'n': n, 'mae_without': mw, 'mae_with': mwi, 'change': mwi - mw, 'flag': flag_of(mwi, mw),
                'saved_rows_switched': int((P['fired_rows'] & savedsel).sum()),
                'switched_batches_holding_visits': held}, contrib
    progs = sorted(set(prog.tolist()))
    by_p, by_py, con_p, con_py = {}, {}, {}, {}
    for pg in progs:
        saved = prog == pg
        e, cb = cell(lab & saved, saved)
        if pg == 'AGRRA' and e['n'] == 1:
            e['note'] = 'n = 1, not interpretable'
        by_p[pg] = e
        con_p[pg] = {'n': e['n'], 'contrib': cb, 'share': cb / pooled_change}
        for yy in sorted(set(yr[saved].tolist())):
            saved2 = saved & (yr == yy)
            e2, cb2 = cell(lab & saved2, saved2)
            if pg == 'AGRRA' and e2['n'] == 1:
                e2['note'] = 'n = 1, not interpretable'
            by_py['%s/%d' % (pg, yy)] = e2
            con_py['%s/%d' % (pg, yy)] = {'n': e2['n'], 'contrib': cb2, 'share': cb2 / pooled_change}
    contributions = {
        'formula': 'contrib = (n_cell / N) x (MAE_with(cell) - MAE_without(cell)); share = contrib / (pooled MAE_with '
                   '- pooled MAE_without)',
        'N': N, 'pooled_mae_without': pooled_wo, 'pooled_mae_with': pooled_w, 'pooled_change': pooled_change,
        'by_programme': con_p,
        'by_programme_residual': float(sum(v['contrib'] for v in con_p.values())) - pooled_change,
        'by_programme_year': con_py,
        'by_programme_year_residual': float(sum(v['contrib'] for v in con_py.values())) - pooled_change,
        'note': 'shares above 100% occur when other cells lose; the residual is rounding only'}
    return by_p, by_py, contributions


def q6_q7(passes, edges):
    P = passes[('coral', 0)]
    y, a, t, w, fr = P['y'], P['a'], P['t'], P['w'], P['fired_rows']
    lab = np.isfinite(y)
    blend = 0.5 * a + 0.5 * t
    f2 = a.copy()
    f2[fr] = blend[fr]
    forms_cols = {'F1': w, 'F2': f2, 'F3': t.copy(), 'F4': blend}
    labels = {'F1': 'per-batch switch: the fixed v2 rule (the with-alarm column)',
              'F2': 'per-batch even blend on the same 11 switched batches: INFORMATION ONLY, not the rule',
              'F3': "whole-window switch (twin on every row, Part 603 guard = Part 604 M1): cross-check only, not "
                    "the alarm's value (C6)",
              'F4': 'whole-window even blend (Part 603 blend = Part 604 M2 = M3): cross-check only'}
    q75 = edges[0]
    subs = subset_masks(P, q75)
    pooled_wo = mae_sel(y, a, lab)
    forms = {}
    for F, col in forms_cols.items():
        d = {'label': labels[F], 'post_hoc': True, 'circular': True}
        pm = mae_sel(y, col, lab)
        d['pooled'] = {'n': int(lab.sum()), 'mae': pm, 'mae_without': pooled_wo, 'change': pm - pooled_wo}
        d['by_year'] = {}
        for yr in sorted(set(P['year'][lab].tolist())):
            sel = lab & (P['year'] == yr)
            m, mw = mae_sel(y, col, sel), mae_sel(y, a, sel)
            d['by_year'][str(yr)] = {'n': int(sel.sum()), 'mae': m, 'mae_without': mw, 'change': m - mw,
                                     'flag': flag_of(m, mw)}
        d['by_programme'] = {}
        for pg in sorted(set(P['programme'].tolist())):
            sel = lab & (P['programme'] == pg)
            m, mw = mae_sel(y, col, sel), mae_sel(y, a, sel)
            d['by_programme'][pg] = {'n': int(sel.sum()), 'mae': m, 'mae_without': mw, 'change': m - mw,
                                     'flag': flag_of(m, mw)}
        d['subsets'] = {}
        for sid, sel, edge in subs:
            m, mw = mae_sel(y, col, sel), mae_sel(y, a, sel)
            d['subsets'][sid] = {'n': int(sel.sum()), 'edge': edge, 'mae': m, 'mae_without': mw, 'change': m - mw,
                                 'outcome_defined': sid != 'all'}
        diff = col.view(np.int64) != a.view(np.int64)
        d['rows_differing'] = {'saved_rows': int(diff.sum()), 'labelled_rows': int((diff & lab).sum())}
        forms[F] = d
    # defo: nothing switched, so F1 = F2 = without (asserted); F3/F4 not computed for defo
    D = passes[('defo', 0)]
    if D['fired_rows'].any():
        raise RuntimeError('defo switched rows: spec Q6 assumption fails')
    d_f2 = D['a'].copy()
    if not (np.array_equal(D['w'].view(np.int64), D['a'].view(np.int64))
            and np.array_equal(d_f2.view(np.int64), D['a'].view(np.int64))):
        raise RuntimeError('defo F1/F2 differ from without')
    # Q7 subsets for the coral nowcast and the coral leads
    subsets = {}
    for L in (0, 183, 365):
        Pl = passes[('coral', L)]
        yl = Pl['y']
        for sid, sel, edge in subset_masks(Pl, edges[L]):
            mw = mae_sel(yl, Pl['a'], sel)
            e = {'package': 'coral', 'lead': L, 'subset': sid, 'edge': edge, 'q75_edge': edges[L],
                 'label': ('outcome-defined (selected on the test label)' if sid != 'all' else 'all labelled rows'),
                 'n': int(sel.sum()), 'mae_without': mw, 'status': Pl['status'], 'post_hoc': True,
                 'circular': True}
            if Pl['replayable']:
                mwi = mae_sel(yl, Pl['w'], sel)
                e.update({'mae_with': mwi, 'change': mwi - mw, 'change_pct': (mwi - mw) / mw * 100.0,
                          'rows_switched_in_subset': int((Pl['fired_rows'] & sel).sum())})
            else:
                e.update({'mae_with': None, 'change': None, 'change_pct': None, 'rows_switched_in_subset': None})
            if L == 0:
                for F in ('F2', 'F3', 'F4'):
                    m = mae_sel(yl, forms_cols[F], sel)
                    e['mae_' + F] = m
                    e['change_' + F] = m - mw
            subsets['coral/%d/%s' % (L, sid)] = e
    return forms, subsets, forms_cols


def q8_small(passes, totals):
    out = {}
    for pkg, run, _ in RUNS:
        P = passes[(pkg, 0)]
        lab = np.isfinite(P['y'])
        small = []
        for r in P['recs']:
            if r['rows'] < MIN_ROWS:
                ix = P['bidx'][r['batch']]
                small.append({'batch': r['batch'], 'saved_rows': r['rows'], 'labelled_rows': int(lab[ix].sum()),
                              'ratio': r['ratio'], 'ratio_above_2': bool(r['ratio'] > THRESHOLD),
                              'tested': r['tested']})
        above = [s for s in small if s['ratio_above_2']]
        e = {'package': pkg, 'lead': 0, 'batches_lt30': small, 'count': len(small),
             'saved_rows': int(sum(s['saved_rows'] for s in small)),
             'largest_ratio': max((s['ratio'] for s in small), default=None),
             'count_ratio_above_2': len(above), 'saved_rows_ratio_above_2': int(sum(s['saved_rows'] for s in above)),
             'note': 'information only: batches below 30 saved rows are not tested; the 30-row floor stays fixed'}
        if pkg == 'coral':
            fr = P['fired_rows'].copy()
            for s in above:
                fr[P['bidx'][s['batch']]] = True
            w2 = P['a'].copy()
            w2[fr] = P['t'][fr]
            m = mae_sel(P['y'], w2, lab)
            e['counterfactual_if_small_batches_above_2_also_switched'] = {
                'information_only': True, 'batches_added': [s['batch'] for s in above], 'saved_rows_switched': int(fr.sum()),
                'pooled_mae_with': m, 'pooled_mae_without': totals[(pkg, 0)]['mae_without'],
                'pooled_mae_with_fixed_rule': totals[(pkg, 0)]['mae_with']}
        out['%s/0' % pkg] = e
    for key in (('defo', 1), ('coral', 183)):
        P = passes[key]
        small = [r for r in P['recs'] if r['rows'] < MIN_ROWS]
        out['%s/%d' % key] = {'package': key[0], 'lead': key[1], 'status': P['status'], 'batches': len(P['recs']),
                              'count_lt30': len(small), 'saved_rows_lt30': int(sum(r['rows'] for r in small)),
                              'batches_lt30': [{'batch': r['batch'], 'saved_rows': r['rows']} for r in small],
                              'note': 'not replayable: the twin was not saved, so no ratio exists'}
    return out


def q9_threshold(passes):
    out = {}
    for pkg in ('coral', 'defo'):
        P = passes[(pkg, 0)]
        lab = np.isfinite(P['y'])
        wo = mae_sel(P['y'], P['a'], lab)
        for th in INFO_THRESHOLDS:
            recs, fr, w = decide(P['a'], P['t'], P['bidx'], P['order'], P['R'], P['status'], threshold=th)
            m = mae_sel(P['y'], w, lab)
            e = {'package': pkg, 'lead': 0, 'threshold': th, 'information_only': th != THRESHOLD,
                 'batches_tested': int(sum(r['tested'] for r in recs)),
                 'batches_switched': int(sum(r['fired'] for r in recs)),
                 'switched_batches': [r['batch'] for r in recs if r['fired']], 'saved_rows_switched': int(fr.sum()),
                 'labelled_rows_switched': int((fr & lab).sum()), 'pooled_mae_with': m, 'pooled_mae_without': wo,
                 'change': m - wo}
            if pkg == 'coral':
                e['by_year'] = {}
                for yr in sorted(set(P['year'][lab].tolist())):
                    sel = lab & (P['year'] == yr)
                    mw, mwi = mae_sel(P['y'], P['a'], sel), mae_sel(P['y'], w, sel)
                    e['by_year'][str(yr)] = {'n': int(sel.sum()), 'mae_without': mw, 'mae_with': mwi,
                                             'change': mwi - mw, 'flag': flag_of(mwi, mw)}
            out['%s/0/%r' % (pkg, th)] = e
    return out


def q10_silence(passes, totals):
    out = {}
    for pkg, run, _ in RUNS:
        P, T = passes[(pkg, 0)], totals[(pkg, 0)]
        sw = bool(T['batches_fired'])
        if sw:
            why = None
            kind = 'active, switched'
        elif P['status'] == 'active':
            kind = 'active, nothing switched'
            why = 'can switch, but no tested batch ratio exceeded 2.0 (largest tested ratio %r)' % T['max_ratio_tested']
        else:
            kind = 'inert (cannot act)'
            why = PLAIN[P['status']]
        out['%s/0' % pkg] = {'package': pkg, 'switched_any_batch': sw, 'status': P['status'], 'kind': kind,
                             'why_not': why, 'largest_ratio_tested': T['max_ratio_tested'],
                             'largest_ratio_computed_information': T['max_ratio_computed'],
                             'batches_switched': T['batches_fired']}
    return out


def q11_regions(passes, g7):
    P = passes[('coral', 0)]
    lab = np.isfinite(P['y'])
    lines = {}
    cnt = {'better': 0, 'same': 0, 'worse': 0}
    for g in sorted(set(P['group'][lab].tolist())):
        sel = lab & (P['group'] == g)
        mw, mwi, mr = mae_sel(P['y'], P['a'], sel), mae_sel(P['y'], P['w'], sel), mae_sel(P['y'], P['ref'], sel)
        fl = flag_of(mwi, mw)
        cnt[fl] += 1
        lines[g] = {'n': int(sel.sum()), 'mae_without': mw, 'mae_with': mwi, 'mae_reference': mr,
                    'change': mwi - mw, 'flag': fl,
                    'saved_rows_switched': int((P['fired_rows'] & (P['group'] == g)).sum())}
    return {'coral/0': {'lines': lines, 'counts': cnt, 'n_regions': len(lines),
                        'verdict_with': g7['coral']['verdict_with'],
                        'blocked_jackknife_with': g7['coral']['blocked_jackknife_with'],
                        'note': 'information; whether S5 uses it is owner item O2; post hoc, circular'}}


def summary_lines(passes, totals, by_year, worse, prog, subsets, forms, small, thr, sil, regions, verdicts):
    L = []
    L.append('POST HOC: the fixed v2 alarm rule replayed on the predictions the five v1 runs saved; nothing refitted '
             'or re-routed; no locked v1 number, verdict or adoption changes.')
    for key, P in passes.items():
        T = totals[key]
        tagc = ', CIRCULAR' if P['package'] == 'coral' else ''
        if P['replayable']:
            L.append('POST HOC%s: %s %s: %s (%s); MAE without %r, with %r (change %r; %r%%); batches %d, tested %s, '
                     'switched %s, saved rows switched %s.' % (
                         tagc, P['package'], P['pass_name'], PLAIN[P['status']], P['status'], T['mae_without'],
                         T['mae_with'], T['change'], T['change_pct'], T['batches'], T['batches_tested'],
                         T['batches_fired'], T['rows_switched']))
        else:
            L.append('POST HOC%s: %s %s: %s; MAE without %r; with not computed; %d batches, %d with >= 30 saved rows.'
                     % (tagc, P['package'], P['pass_name'], PLAIN[P['status']], T['mae_without'], T['batches'],
                        T['batches_ge30']))
    Tc = totals[('coral', 0)]
    L.append('POST HOC, CIRCULAR: coral nowcast switched batches: %s; reference gap %r on %d decision-surface rows; '
             'largest tested ratio %r.' % (' '.join(Tc['fired_batches']), passes[('coral', 0)]['R'],
                                           passes[('coral', 0)]['R_rows'], Tc['max_ratio_tested']))
    yrs = []
    for yr in (2016, 2017, 2018, 2019):
        e = by_year.get('coral/0/%d' % yr)
        if e:
            yrs.append('%d %r -> %r (%s)' % (yr, e['mae_without'], e['mae_with'],
                                             'unchanged' if e['flag'] == 'same' else e['flag']))
    L.append('POST HOC, CIRCULAR: coral nowcast by test year (the 2016-2019 window was set by hand): ' + '; '.join(yrs))
    L.append('POST HOC: test years in which the alarm made a nowcast worse: %s.' % (', '.join(worse) or 'none'))
    L.append('POST HOC, CIRCULAR: coral nowcast by survey programme: ' + '; '.join(
        '%s n %d %r -> %r (%s)%s' % (pg, e['n'], e['mae_without'], e['mae_with'],
                                     'unchanged' if e['flag'] == 'same' else e['flag'],
                                     ' [n = 1, not interpretable]' if e.get('note') else '')
        for pg, e in prog.items()))
    for sid in ('y_gt_0', 'y_eq_0', 'y_ge_50', 'y_lt_50', 'y_gt_q75', 'y_le_q75'):
        e = subsets['coral/0/%s' % sid]
        L.append('POST HOC, CIRCULAR, outcome-defined (selected on the test label): coral nowcast %s (n %d): %r -> %r '
                 '(change %r); rows switched in this subset %d.' % (e['edge'], e['n'], e['mae_without'],
                                                                    e['mae_with'], e['change'],
                                                                    e['rows_switched_in_subset']))
    L.append('POST HOC, CIRCULAR: coral nowcast pooled MAE by form: F1 fixed rule %r; F2 per-batch even blend '
             '(information only) %r; F3 twin on every row (not the alarm value) %r; F4 even blend on every row %r.' % (
                 forms['F1']['pooled']['mae'], forms['F2']['pooled']['mae'], forms['F3']['pooled']['mae'],
                 forms['F4']['pooled']['mae']))
    cf = small['coral/0'].get('counterfactual_if_small_batches_above_2_also_switched')
    L.append('POST HOC, CIRCULAR, information only: coral nowcast has %d batches below 30 saved rows (%d rows), %d of '
             'them with ratio above 2.0; had those also switched, pooled MAE would be %r (the 30-row floor stays '
             'fixed).' % (small['coral/0']['count'], small['coral/0']['saved_rows'],
                          small['coral/0']['count_ratio_above_2'], cf['pooled_mae_with']))
    L.append('POST HOC, information only (threshold 2.0 stays fixed): coral pooled MAE with at thresholds ' + '; '.join(
        '%s -> %r (%d switched)' % (k.split('/')[-1], v['pooled_mae_with'], v['batches_switched'])
        for k, v in thr.items() if k.startswith('coral')) + '; defo switched batches at each threshold: ' + ', '.join(
        '%s -> %d' % (k.split('/')[-1], v['batches_switched']) for k, v in thr.items() if k.startswith('defo')) + '.')
    for k, v in sil.items():
        L.append('POST HOC%s: %s nowcast: %s; switched any batch: %s%s.' % (
            ', CIRCULAR' if k.startswith('coral') else '', k.split('/')[0], v['kind'],
            'yes' if v['switched_any_batch'] else 'no', ('; ' + v['why_not']) if v['why_not'] else ''))
    rc = regions['coral/0']['counts']
    vw = verdicts['coral']['verdict_with']
    L.append('POST HOC, CIRCULAR: coral nowcast regions with the alarm vs without: %d better, %d same, %d worse (of %d). '
             'With-alarm verdict vs the donor median: %s, contrast %r [%r, %r], %d groups, %d better.' % (
                 rc['better'], rc['same'], rc['worse'], regions['coral/0']['n_regions'], vw['tag'],
                 vw['contrast']['mean'], vw['contrast']['low'], vw['contrast']['high'], vw['contrast']['n_groups'],
                 vw['groups_better']))
    return L


# ----------------------------------------------------------------------------------------------------------------
def main():
    os.makedirs(OUT, exist_ok=True)
    script_path = _norm(os.path.abspath(__file__))
    libs = libraries()
    libs['script_path'] = script_path
    result = {'implementer': 'B', 'script_sha256': sha256_file(script_path), 'python_and_libraries': libs,
              'inputs': INPUTS, 'engine_v2_hash': None, 'read_engine_code': [], 'gates': {}}
    load_expected()
    INPUTS[_norm(SPEC)] = sha256_file(SPEC)
    INPUTS[_norm(INPUTS_LIST)] = sha256_file(INPUTS_LIST)
    gates = result['gates']
    try:
        # ---------------- load and replay every pass ----------------
        ctxs, passes, totals = {}, {}, {}
        for pkg, run, leads in RUNS:
            ctx = load_run(pkg, run, leads)
            ctxs[pkg] = ctx
            P = nowcast_pass(ctx)
            P['verdict_pooled_mae_adopted'] = ctx['verdict']['pooled_mae_adopted']
            passes[(pkg, 0)] = P
            for L in leads:
                passes[(pkg, L)] = lead_pass(ctx, L)
        for key, P in passes.items():
            totals[key] = pass_totals(P)
        edges_df = read_csv(EDGES)
        edges = {int(r['lead']): float(r['q75_positive_donor_labels']) for r in edges_df.to_dict('records')}
        # gate targets
        ww_gate = read_csv(GATE + '/WITH_WITHOUT.csv', dtype={'fired_batches': object})
        gate_json, gate_scores, gate_rows = {}, {}, {}
        for pkg, run, leads in RUNS:
            gj = GATE + '/%s/%s/alarm_replay.json' % (pkg, run)
            gate_json[pkg] = read_json(gj)
            gate_scores[pkg] = read_csv(GATE + '/%s/%s/alarm_replay_scores.csv' % (pkg, run), dtype={'key': str})
            for L in (0,) + tuple(leads):
                gate_rows[(pkg, L)] = pq.read_table(
                    checked(GATE + '/rows/%s_%s_lead_%d.parquet' % (pkg, run, L))).to_pandas()
        p604 = read_json(PART604)
        # score_pooled.csv cross-check of the adopted column's pooled MAE (rows basis all)
        sp_c = Cmp()
        for pkg, run, _ in RUNS:
            sp = ctxs[pkg]['score_pooled']
            P = passes[(pkg, 0)]
            r = sp[(sp['rows_basis'] == 'all') & (sp['column'] == P['adopted_column']) & (sp['line'] == 'pooled')]
            sp_c.eq(pkg + ' score_pooled.csv adopted rows', 1, len(r))
            if len(r) == 1:
                sp_c.eq(pkg + ' score_pooled.csv adopted MAE', float(r['mae'].iloc[0]), totals[(pkg, 0)]['mae_without'])
                sp_c.eq(pkg + ' score_pooled.csv adopted n', int(r['n'].iloc[0]), totals[(pkg, 0)]['labelled_rows'])
            sp_c.eq(pkg + ' run_record kind', 'headline', ctxs[pkg]['run_record'].get('kind'))
        # ---------------- the gate ----------------
        gates['G1'], ww_mine = gate_g1(passes, totals, edges, ww_gate)
        gates['G1']['details']['score_pooled_crosscheck'] = sp_c.result()
        if not gates['G1']['details']['score_pooled_crosscheck']['pass']:
            gates['G1']['pass'] = False
        gates['G2'] = gate_g2(passes, totals, gate_json)
        gates['G3'], score_out = gate_g3(passes, gate_scores)
        gates['G4'] = gate_g4(passes, totals)
        gates['G5'] = gate_g5(passes, gate_rows)
        gates['G6'] = gate_g6(passes)
        gates['G7'], g7 = gate_g7(passes, totals, gate_json, ctxs)
        gates['G8'] = gate_g8(passes, p604)
        gates['G9'] = gate_g9(ww_gate)
        gates['G0'] = {'pass': not G0_LOG['mismatches'] and not G0_LOG['not_listed'],
                       'details': dict(G0_LOG, listed_not_read=sorted(p for p in EXPECTED if p not in INPUTS),
                                       listed_not_read_reason='not needed by implementer B; engine and tool code '
                                                              'is never opened by B (SPEC.md section 4)')}
        gates['G7']['details']['definitions'] = (
            'SPEC.md section 4 gives the per-group contrast, the group jackknife and the blocked jackknife over '
            'derived.json R14 blocks. Not in SPEC.md and taken from documents (no code): the D74 tag order and '
            'tests (engine/PREREGISTRATION_DRAFT.md section 7; PAPER_FACTS P14), the jackknife SE formula and '
            '"each block valued at the mean of its groups\' values" (PAPER_FACTS K47), the blocked flag rule '
            '"SE more than 20% above the group SE" (PREREGISTRATION_DRAFT.md section 8). Read from the gate record '
            'itself: groups_better = groups with contrast > 0; sign_flip_groups = groups whose contrast sign is '
            'opposite to the contrast mean, sorted by name; pooled_contrast = pooled MAE(reference) - pooled '
            'MAE(column); the reference label is verdict.json "verdict"."reference". All matched bit for bit.')
    except GateStop as e:
        gates['G0'] = {'pass': False, 'details': dict(G0_LOG, stop=str(e))}
        result['stopped'] = 'gate G0 failed: ' + str(e)
        print(write_result(result))
        print('STOPPED at G0:', e)
        return 2
    except Exception as e:  # fail loud, but record what happened
        result['stopped'] = 'error before the gate completed: %r' % (e,)
        result['traceback'] = traceback.format_exc()
        print(write_result(result))
        raise
    result['gates'] = {k: gates[k] for k in ('G0', 'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9')}
    blocking = [k for k in ('G0', 'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8') if not gates[k]['pass']]
    if blocking:
        result['stopped'] = 'reproduction gate failed: ' + ', '.join(blocking) + '; nothing new computed'
        print(write_result(result))
        for k in blocking:
            print(k, 'FAILED:', json.dumps(clean(gates[k]['details'].get('failures', gates[k]['details'])))[:3000])
        return 1

    # ---------------- section 6 (POST HOC) ----------------
    result['passes'] = q1_passes(passes, totals)
    batches = q2_batches(passes)
    result['batches'] = batches
    by_year, worse = q3_by_year(passes)
    result['by_year'] = by_year
    prog, prog_year, contributions = q4_q5_programme(passes[('coral', 0)])
    # Q4 row alignment: programme comes from the same test_preds rows as the replay rows (asserted vs gate rows)
    gr = gate_rows[('coral', 0)]
    Pc = passes[('coral', 0)]
    if not (np.array_equal(gr['unit'].to_numpy(dtype=object), Pc['unit'])
            and np.array_equal(gr['time'].to_numpy(), Pc['time'])
            and np.array_equal(gr['y'].to_numpy().view(np.int64), Pc['y'].view(np.int64))):
        raise RuntimeError('coral programme rows not aligned with the replay rows')
    result['coral_programme'] = prog
    result['coral_programme_year'] = prog_year
    result['contributions'] = contributions
    forms, subsets, forms_cols = q6_q7(passes, edges)
    result['forms'] = forms
    result['subsets'] = subsets
    small = q8_small(passes, totals)
    result['small_batches'] = small
    thr = q9_threshold(passes)
    result['threshold_check'] = thr
    sil = q10_silence(passes, totals)
    result['silence'] = sil
    regions = q11_regions(passes, g7)
    result['regions'] = regions
    verdicts = {}
    for pkg, run, _ in RUNS:
        v = dict(g7[pkg])
        v.pop('group_contrast_with', None)
        v['post_hoc'] = True
        v['circular'] = pkg == 'coral'
        v['note'] = 'verdict_with is post hoc; verdict_without_locked is the locked v1 verdict (unchanged)'
        verdicts[pkg] = v
    result['verdicts'] = verdicts
    result['summary_text'] = summary_lines(passes, totals, by_year, worse, prog, subsets, forms, small, thr, sil,
                                           regions, verdicts)
    # ---------------- Q12 row-level outputs ----------------
    written = {}
    for key, P in passes.items():
        if not P['replayable']:
            continue
        df = rows_frame(P, gate_style=False)
        df = df[['unit', 'group', 'time', 'year', 'issue', 'y', 'batch', 'adopted', 'twin', 'with_alarm', 'fired']]
        if key == ('coral', 0):
            df['programme'] = P['programme']
            df['blend_batch'] = forms_cols['F2']
            df['twin_all'] = forms_cols['F3']
            df['blend_all'] = forms_cols['F4']
        path = OUT + '/rows_%s_lead_%d.parquet' % key
        if DRY_RUN:
            written[path] = 'dry run: not written (%d rows, columns %s)' % (len(df), list(df.columns))
            continue
        df.to_parquet(path, index=False, engine='pyarrow')
        written[path] = sha256_file(path)
    for key in passes:
        e = result['passes']['%s/%d' % key]
        path = OUT + '/rows_%s_lead_%d.parquet' % key
        e['row_file'] = path if path in written else None
        e['row_file_sha256'] = written.get(path)
    if DRY_RUN:
        print('DRY RUN: nothing written')
        print(json.dumps(clean({k: v['pass'] for k, v in result['gates'].items()})))
        print('\n'.join(result['summary_text']))
        return 0
    path = write_result(result)
    print('result:', path, sha256_file(path))
    print('\n'.join(result['summary_text']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
