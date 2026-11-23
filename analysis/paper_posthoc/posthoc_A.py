#!/usr/bin/env python3
"""posthoc_A.py -- implementer A of the paper post-hoc spec (SPEC.json in this folder).

POST HOC: every number here is computed AFTER the test labels were opened. Nothing here changes a
pre-registered verdict; report-only contrasts are labelled as such.

Run (light compute, pandas/pyarrow on saved predictions and CSVs only):
    py -3.9 -I D:/treeroute/analysis/paper_posthoc/posthoc_A.py

Writes ONLY D:/treeroute/analysis/paper_posthoc/result_A.json. Every other path is read-only.
Engine definitions replicated (not imported), from
C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/treeroute/report/metrics.py:
mae (569), anomaly_r2 (580), corr2 (604), hit_rate (688), group_jackknife (1032), contrast_tag (1097),
_paired_contrast (1123), score_table row selection (846: a column is scored on the labelled rows where
it is finite; per-group lines from groupby('group', sort=True).indices in saved row order).
No seeds. Jackknife over groups (regions) only, z = JACKKNIFE_Z = 1.96.
"""
import hashlib
import json
import math
import re
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy import stats

OUT_DIR = "D:/treeroute/analysis/paper_posthoc"
OUT_JSON = OUT_DIR + "/result_A.json"
SPEC_JSON = OUT_DIR + "/SPEC.json"

PROBS = ["pm25", "ndvi", "fire", "defo", "coral"]
RUN = {
    "pm25": "D:/treeroute/runs/pm25/headline/20261007_74e67609",
    "ndvi": "D:/treeroute/runs/ndvi/headline/20261016_d1de3158",
    "fire": "D:/treeroute/runs/fire/headline/20261017_869d1f38",
    "defo": "D:/treeroute/runs/defo/headline/20261017_d71c61f4",
    "coral": "D:/treeroute/runs/coral/headline/20261020_f3b8e3da",
}
RIVAL = {
    "pm25": "D:/treeroute/rivals/pm25/20261007_74e67609",
    "ndvi": "D:/treeroute/rivals/ndvi/20261016_d1de3158",
    "fire": "D:/treeroute/rivals/fire/20261017_869d1f38",
    "defo": "D:/treeroute/rivals/defo/20261017_d71c61f4",
    "coral": "D:/treeroute/rivals/coral/20261020_f3b8e3da",
}
HUMAN = {
    "pm25": "D:/treeroute/rivals_human/pm25/20261007_74e67609",
    "ndvi": "D:/treeroute/rivals_human/ndvi/20261016_d1de3158",
    "defo": "D:/treeroute/rivals_human/defo/20261017_d71c61f4",
    "coral": "D:/treeroute/rivals_human/coral/20261020_f3b8e3da",
}
HEADLINE = {
    "pm25": "D:/treeroute/runs/_headline_tables/headline_93b64854d1f9.csv",
    "ndvi": "D:/treeroute/runs/_headline_tables/ndvi/headline_9e5590eab94b.csv",
    "fire": "D:/treeroute/runs/_headline_tables/fire/headline_85a9134089e4.csv",
    "defo": "D:/treeroute/runs/_headline_tables/defo/headline_1571da960aa6.csv",
    "coral": "D:/treeroute/runs/_headline_tables/coral/headline_344838cf7de1.csv",
}
VERDICTS = {
    "pm25": "D:/treeroute/runs/_headline_tables/verdicts_9abcea419ce2.csv",
    "ndvi": "D:/treeroute/runs/_headline_tables/ndvi/verdicts_c4cd7e7c2610.csv",
    "fire": "D:/treeroute/runs/_headline_tables/fire/verdicts_7ee7167afe8d.csv",
    "defo": "D:/treeroute/runs/_headline_tables/defo/verdicts_bf99c6741bce.csv",
    "coral": "D:/treeroute/runs/_headline_tables/coral/verdicts_a9d948cbf26b.csv",
}
RIVALS_TABLE = "D:/treeroute/rivals_table/20261025T162302876402Z/RIVALS_TABLE.csv"
CORAL_EDGES = "D:/treeroute/runs/_headline_tables/coral/coral_report/magnitude_edges.csv"
CORAL_BINS = "D:/treeroute/runs/_headline_tables/coral/coral_report/magnitude_bins.csv"
LEADS = {"pm25": [0, 6, 12], "ndvi": [0, 6, 12], "fire": [0, 6, 12], "defo": [0, 1], "coral": [0, 183, 365]}
HUMAN_LEADS = {"pm25": [0, 6, 12], "ndvi": [0, 6, 12], "defo": [0, 1], "coral": [0, 183, 365]}
CORAL_LEARNERS = ["ridge", "rf", "lgbm", "lgbm_tweedie", "hgb_l1"]
FIRE_LEARNERS = ["ridge", "rf", "lgbm", "lgbm_tweedie"]

Z = 1.96                 # engine_constants.py JACKKNIFE_Z (S2.jackknife_z), line 323
IDENTICAL_ATOL = 1e-12   # report/metrics.py line 112
RTOL = 1e-12
NAN = float("nan")

# ------------------------------------------------------------------------------------------- plumbing
_SHA = {}


def sha256_file(path):
    if path not in _SHA:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 23), b""):
                h.update(chunk)
        _SHA[path] = h.hexdigest()
    return _SHA[path]


def _spec_prefixes():
    """path -> expected sha256 prefix, per item id, from the shared SPEC.json (read-only)."""
    out = {}
    try:
        with open(SPEC_JSON, encoding="utf-8") as f:
            spec = json.load(f)
    except OSError:
        return out
    for it in spec.get("items", []):
        d = {}
        for s in it.get("inputs", []):
            m = re.match(r"^(.*?) \[sha256 ([0-9a-f]+)\]", s)
            if m:
                d[m.group(1).strip()] = m.group(2)
        out[it.get("id")] = d
    return out


SPEC_PREFIX = _spec_prefixes()
ALL_FAILS = []


class Item:
    def __init__(self, iid, formula, population):
        self.id = iid
        self.formula = formula
        self.population = population
        self.inputs = {}
        self.checks = []
        self.values = {}
        self.notes = []
        print("\n" + "=" * 110 + "\n" + iid + "\n" + "=" * 110)

    def use(self, path):
        self.inputs[path] = sha256_file(path)[:16]
        return path

    def check(self, what, ok, detail=""):
        ok = bool(ok)
        self.checks.append({"check": what, "ok": ok, "detail": detail})
        if not ok:
            ALL_FAILS.append((self.id, what, detail))
            print("  **CHECK FAILED** %s %s" % (what, detail))

    def close(self):
        exp = SPEC_PREFIX.get(self.id, {})
        for p, pre in sorted(self.inputs.items()):
            if p in exp:
                self.check("sha256 prefix of %s equals the spec's" % p, pre == exp[p],
                           "computed %s, spec %s" % (pre, exp[p]))
        extra = sorted(set(self.inputs) - set(exp))
        missing = sorted(set(exp) - set(self.inputs))
        if extra:
            self.notes.append("files read beyond the spec's input list (named by the formula, e.g. verdict.json band or adopted, or used for "
                              "consistency checks): %s" % extra)
        if missing:
            self.notes.append("spec inputs not read: %s" % missing)
        nf = sum(1 for c in self.checks if not c["ok"])
        print("  [%s] %d checks, %d failed; %d input files" % (self.id, len(self.checks), nf, len(self.inputs)))
        return {"id": self.id, "values": self.values, "population": self.population,
                "inputs_sha256_prefix": self.inputs, "formula": self.formula,
                "checks": self.checks, "n_checks": len(self.checks), "n_failed_checks": nf,
                "notes": self.notes, "post_hoc": True}


def rparquet(item, path, cols):
    item.use(path)
    return pq.read_table(path, columns=list(cols)).to_pandas()


def rcsv(item, path):
    item.use(path)
    return pd.read_csv(path, float_precision="round_trip")


def rjson(item, path):
    item.use(path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def close(a, b, rtol=RTOL, atol=0.0):
    a = float(a)
    b = float(b)
    if math.isnan(a) and math.isnan(b):
        return True
    if math.isnan(a) or math.isnan(b):
        return False
    return abs(a - b) <= max(rtol * max(abs(a), abs(b)), atol)


def reld(a, b):
    a, b = float(a), float(b)
    if a == b:
        return 0.0
    if math.isnan(a) and math.isnan(b):
        return 0.0
    return abs(a - b) / max(abs(a), abs(b))


def g6(x):
    return "nan" if x is None or (isinstance(x, float) and math.isnan(x)) else "%.6g" % x


# ------------------------------------------------------------------------- engine metric replicas
def mae(y, p):
    return float(np.mean(np.abs(y - p)))


def anomaly_r2(y, p, n):
    if y.size < 10:
        return NAN
    ay, ap = y - n, p - n
    s0 = float(np.sum(ay ** 2))
    if not s0 > 0:
        return NAN
    return 1.0 - float(np.sum((ay - ap) ** 2)) / s0


def corr2(y, p):
    if y.max() == y.min() or p.max() == p.min():
        return NAN
    yc, pc = y - y.mean(), p - p.mean()
    syy, spp = float(np.sum(yc * yc)), float(np.sum(pc * pc))
    if not (syy > 0 and spp > 0):
        return NAN
    r = float(np.sum(yc * pc)) / math.sqrt(syy * spp)
    return r * r


def hit_rate(y, p, tol):
    return float(np.mean(np.abs(y - p) <= tol))


def jackknife(v):
    v = np.asarray(v, dtype=np.float64)
    n = int(v.size)
    if n < 3:
        return {"mean": float(v.mean()), "se": NAN, "low": NAN, "high": NAN, "n_groups": n}
    jk = np.array([np.delete(v, i).mean() for i in range(n)])
    se = float(np.sqrt((n - 1) / n * ((jk - jk.mean()) ** 2).sum()))
    return {"mean": float(v.mean()), "se": se, "low": float(v.mean() - Z * se),
            "high": float(v.mean() + Z * se), "n_groups": n}


def tag_from_interval(mean, low, high, band, identical=False):
    """D74 / contrast_tag order: identical; undefined interval -> cannot_tell; equivalent; helps; hurts."""
    if identical:
        return "identical"
    if not (math.isfinite(low) and math.isfinite(high)):
        return "cannot_tell"
    if -band <= low and high <= band:
        return "does_not_help_equivalent"
    if low > 0 and mean >= band:
        return "helps"
    if high < 0 and mean <= -band:
        return "hurts"
    return "cannot_tell"


def contrast_tag(dv, band):
    dv = np.asarray(dv, dtype=np.float64)
    jk = jackknife(dv)
    ident = bool(np.all(np.abs(dv) <= IDENTICAL_ATOL))
    jk["tag"] = tag_from_interval(jk["mean"], jk["low"], jk["high"], band, ident)
    jk["identical"] = ident
    return jk


def paired(ref_map, arm_map):
    """_paired_contrast: same group sets, sorted(groups), d = ref - arm."""
    assert set(ref_map) == set(arm_map), "different group sets"
    groups = sorted(ref_map)
    return groups, np.array([float(ref_map[g]) - float(arm_map[g]) for g in groups])


def group_indices(df):
    return df.groupby("group", sort=True).indices


def group_mae(df, col, gidx, mask=None):
    y = df["y"].to_numpy(np.float64)
    p = df[col].to_numpy(np.float64)
    ok = np.isfinite(y) & np.isfinite(p)
    if mask is not None:
        ok = ok & mask
    out = {}
    for g, idx in gidx.items():
        rows = idx[ok[idx]]
        if rows.size:
            out[g] = float(np.mean(np.abs(y[rows] - p[rows])))
    return out


def pooled_lookup(sp, col):
    s = sp[(sp["column"] == col) & (sp["line"] == "pooled") & (sp["rows_basis"] == "all")]
    if len(s) != 1:
        raise RuntimeError("score_pooled.csv has %d pooled 'all' lines for %s" % (len(s), col))
    return s.iloc[0]


def sbg_maps(sbg):
    s = sbg[(sbg["line"] == "key") & (sbg["rows_basis"] == "all")]
    out = {}
    for col, d in s.groupby("column"):
        if (d["rows_missing"] > 0).any():
            raise RuntimeError("score_by_group: %s has rows_missing > 0" % col)
        out[col] = dict(zip(d["group"].tolist(), d["mae"].astype(float).tolist()))
    return out


def check_group_maps(item, label, mine, rec):
    ok = set(mine) == set(rec)
    worst = 0.0
    if ok:
        for g in mine:
            worst = max(worst, reld(mine[g], rec[g]))
    item.check("%s per-group MAE recomputed == score_by_group.csv (rtol 1e-12)" % label,
               ok and worst <= RTOL, "groups %d/%d, max rel diff %.3g" % (len(mine), len(rec), worst))


def jk_record(jk, extra=None):
    d = {k: jk[k] for k in ("mean", "se", "low", "high", "n_groups")}
    if "tag" in jk:
        d["tag"] = jk["tag"]
    if extra:
        d.update(extra)
    return d


def labelled_population(df):
    lab = np.isfinite(df["y"].to_numpy(np.float64))
    pop = {"saved_rows": int(len(df)), "labelled_rows": int(lab.sum()),
           "unlabelled_rows": int((~lab).sum())}
    if "unit" in df.columns:
        pop["units"] = int(df.loc[lab, "unit"].nunique())
    if "group" in df.columns:
        pop["groups"] = int(df.loc[lab, "group"].nunique())
    if "year" in df.columns:
        yrs = sorted(int(v) for v in df.loc[lab, "year"].unique())
        pop["years"] = "%d-%d" % (yrs[0], yrs[-1]) if yrs else ""
    if "lead" in df.columns:
        pop["leads"] = sorted(int(v) for v in df["lead"].unique())
    return lab, pop


# ================================================================================================= M34
def item_M34():
    it = Item("M34",
              "TO = arm__identity_trees_off_unweighted, GN = base__guess_normal. MAE_TO = mean|y-TO|, "
              "MAE_GN = mean|y-GN| over labelled rows; diff = MAE_TO - MAE_GN; rel = diff/MAE_GN; maxdev = "
              "max over every saved row of |TO-GN|; GN == clip(normal, legal_min, legal_max) asserted exactly; "
              "anomaly R2 of TO = 1 - sum(((y-normal)-(TO-normal))^2)/sum((y-normal)^2); maxdev compared "
              "with verdict.json tolerances.tolerance.identity (= max(k*s_identity, floor), ruling O4).",
              "Lead 0 (nowcast). MAE/anomaly R2 over labelled rows: pm25 91,428 rows/1,905 units/127 groups/"
              "2020-2023; ndvi 94,527/1,983/133/2020-2023; fire 94,702/2,000/40/2019-2022; defo 369,096/"
              "92,274/42/2020-2023. maxdev over every saved row (pm25 91,440; ndvi 95,184; fire 96,000; "
              "defo 369,096). Coral excluded (neighbour kind: no normal, no guess-normal).")
    TO, GN = "arm__identity_trees_off_unweighted", "base__guess_normal"
    print("%-5s %8s %6s %6s %-9s | %-12s %-12s | %-24s %-10s | %-10s %-10s %-9s | %-10s" %
          ("prob", "n_lab", "units", "grps", "years", "MAE_TO", "MAE_GN", "diff (exact)", "rel",
           "maxdev", "tol_id", "<=tol", "anomR2_TO"))
    for prob in ["pm25", "ndvi", "fire", "defo"]:
        run = RUN[prob]
        df = rparquet(it, run + "/test_preds.parquet",
                      ["unit", "group", "year", "lead", "y", "normal", "legal_min", "legal_max", TO, GN])
        lab, pop = labelled_population(df)
        y = df["y"].to_numpy(np.float64)
        to = df[TO].to_numpy(np.float64)
        gn = df[GN].to_numpy(np.float64)
        nrm = df["normal"].to_numpy(np.float64)
        lo = df["legal_min"].to_numpy(np.float64)
        hi = df["legal_max"].to_numpy(np.float64)
        clipped = np.minimum(np.maximum(nrm, lo), hi)
        it.check("%s GN == clip(normal, legal_min, legal_max) exactly on all %d saved rows" % (prob, len(df)),
                 np.array_equal(gn, clipped, equal_nan=True),
                 "rows differing: %d" % int(np.sum(~((gn == clipped) | (np.isnan(gn) & np.isnan(clipped))))))
        it.check("%s TO and GN finite on every labelled row" % prob,
                 np.isfinite(to[lab]).all() and np.isfinite(gn[lab]).all())
        yl, tol_, gnl, nl = y[lab], to[lab], gn[lab], nrm[lab]
        m_to, m_gn = mae(yl, tol_), mae(yl, gnl)
        diff = m_to - m_gn
        rel = diff / m_gn
        dev = np.abs(to - gn)
        fin = np.isfinite(dev)
        maxdev = float(np.max(dev[fin]))
        maxdev_lab = float(np.max(dev[lab & fin]))
        imax = int(np.flatnonzero(fin)[np.argmax(dev[fin])])
        maxdev_normal = float(np.max(np.abs(to - nrm)[fin]))
        a_to = anomaly_r2(yl, tol_, nl)
        a_gn = anomaly_r2(yl, gnl, nl)
        v = rjson(it, run + "/verdict.json")
        tl = v["tolerances"]
        tol_id = float(tl["tolerance"]["identity"])
        rebuilt = max(float(tl["k"]) * float(tl["s"]["identity"]), float(tl["floor"]))
        it.check("%s verdict tolerance.identity == max(k*s_identity, floor)" % prob,
                 close(tol_id, rebuilt, 1e-9), "recorded %r rebuilt %r" % (tol_id, rebuilt))
        sp = rcsv(it, run + "/score_pooled.csv")
        r_to, r_gn = pooled_lookup(sp, TO), pooled_lookup(sp, GN)
        it.check("%s MAE_TO == score_pooled (rtol 1e-12)" % prob, close(m_to, r_to["mae"]),
                 "%r vs %r" % (m_to, r_to["mae"]))
        it.check("%s MAE_GN == score_pooled (rtol 1e-12)" % prob, close(m_gn, r_gn["mae"]),
                 "%r vs %r" % (m_gn, r_gn["mae"]))
        it.check("%s anomaly R2 TO == score_pooled (rtol 1e-12)" % prob, close(a_to, r_to["anom_r2"]),
                 "%r vs %r" % (a_to, r_to["anom_r2"]))
        it.check("%s anomaly R2 GN == score_pooled (rtol 1e-12)" % prob, close(a_gn, r_gn["anom_r2"]),
                 "%r vs %r" % (a_gn, r_gn["anom_r2"]))
        it.check("%s score_pooled n == labelled rows" % prob,
                 int(r_to["n"]) == pop["labelled_rows"] and int(r_to["n_units"]) == pop["units"],
                 "n %s units %s" % (r_to["n"], r_to["n_units"]))
        rec = {"population": pop, "MAE_TO": m_to, "MAE_GN": m_gn, "MAE_TO_6sig": g6(m_to),
               "MAE_GN_6sig": g6(m_gn), "diff_exact": repr(diff), "diff": diff, "rel_diff": rel,
               "abs_rel_diff_below_1e-8": bool(abs(rel) < 1e-8),
               "maxdev_all_saved_rows": maxdev, "maxdev_rows_n": int(fin.sum()),
               "maxdev_labelled_rows": maxdev_lab, "maxdev_row_index": imax,
               "max_abs_TO_minus_unclipped_normal": maxdev_normal,
               "tolerance_identity": tol_id, "maxdev_within_tolerance": bool(maxdev <= tol_id),
               "maxdev_over_tolerance": maxdev / tol_id,
               "anomaly_r2_TO": a_to, "anomaly_r2_GN": a_gn,
               "GN_equals_clip_normal_exactly": bool(np.array_equal(gn, clipped, equal_nan=True)),
               "score_pooled_MAE_TO": float(r_to["mae"]), "score_pooled_MAE_GN": float(r_gn["mae"]),
               "score_pooled_anom_r2_TO": float(r_to["anom_r2"])}
        if prob == "ndvi":
            h = rcsv(it, HEADLINE["ndvi"])
            hr = h[(h["lead"] == 0) & (h["rows"] == "all") & (h["line"] == "pooled")].iloc[0]
            it.check("ndvi headline table reference is the identity trees-off",
                     hr["reference"] == TO, str(hr["reference"]))
            it.check("ndvi headline mae_reference == MAE_TO (rtol 1e-12)", close(hr["mae_reference"], m_to),
                     "%r vs %r" % (hr["mae_reference"], m_to))
            it.check("ndvi headline anom_r2_reference == anomR2_TO (rtol 1e-12)",
                     close(hr["anom_r2_reference"], a_to), "%r vs %r" % (hr["anom_r2_reference"], a_to))
            it.check("ndvi headline mae_guess_normal == MAE_GN (rtol 1e-12)", close(hr["mae_guess_normal"], m_gn),
                     "%r vs %r" % (hr["mae_guess_normal"], m_gn))
            rec["ndvi_headline_table"] = {"mae_reference": float(hr["mae_reference"]),
                                          "anom_r2_reference": float(hr["anom_r2_reference"]),
                                          "mae_guess_normal": float(hr["mae_guess_normal"])}
        it.values[prob] = rec
        print("%-5s %8d %6d %6d %-9s | %-12s %-12s | %-24r %-10.3g | %-10.3g %-10.3g %-9s | %-10.3g" %
              (prob, pop["labelled_rows"], pop["units"], pop["groups"], pop["years"], g6(m_to), g6(m_gn),
               diff, rel, maxdev, tol_id, maxdev <= tol_id, a_to))
    it.values["summary"] = ("identity-link trees-off MAE equals guess-normal MAE within %.2g relative "
                            "(max |rel diff| over the four runs); maxdev within the identity tolerance in all "
                            "four: %s" % (max(abs(it.values[p]["rel_diff"]) for p in ["pm25", "ndvi", "fire", "defo"]),
                                          all(it.values[p]["maxdev_within_tolerance"] for p in ["pm25", "ndvi", "fire", "defo"])))
    print("  " + it.values["summary"])
    print("  |rel diff| < 1e-8: " + ", ".join("%s %s (%.3g)" % (p, it.values[p]["abs_rel_diff_below_1e-8"],
                                                               it.values[p]["rel_diff"]) for p in ["pm25", "ndvi", "fire", "defo"]))
    return it.close()


# ================================================================================================= R12
def item_R12():
    it = Item("R12",
              "Pooled MAE = mean|y-p| over labelled rows per column, sorted ascending (checked vs score_pooled.csv, "
              "rtol 1e-12). Report-only contrasts: d_g = MAE_ref(g) - MAE_adopted(g) (positive = adopted better), "
              "ref = arm__log_c_trees_off_unweighted and, separately, base__predict_zero; per-group MAE recomputed "
              "and checked vs score_by_group.csv; group jackknife z 1.96; D74 tag with the fire band. Final part: "
              "adoption.json surface MAEs and jackknife.csv log-arm tags re-read; jackknife.csv log rows "
              "re-derived from score_by_group.csv.",
              "Fire, lead 0, labelled rows: 94,702 cell-months (1,298 unlabelled saved rows excluded), 2,000 units, "
              "40 groups, test years 2019-2022. Contrasts over the 40 groups.")
    run = RUN["fire"]
    ADOPT = "arm__arcsine_corrector_gls"
    cols = ["arm__log_c_trees_off_unweighted", "base__predict_zero", "arm__log_c_plain_unweighted",
            "arm__log_c_plain_gls", "arm__log_c_corrector_unweighted", "arm__log_c_corrector_gls", ADOPT,
            "arm__arcsine_trees_off_unweighted", "arm__identity_trees_off_unweighted", "base__guess_normal"]
    df = rparquet(it, run + "/test_preds.parquet", ["unit", "group", "year", "lead", "y"] + cols)
    lab, pop = labelled_population(df)
    it.values["population"] = pop
    sp = rcsv(it, run + "/score_pooled.csv")
    sbg = rcsv(it, run + "/score_by_group.csv")
    jkc = rcsv(it, run + "/jackknife.csv")
    v = rjson(it, run + "/verdict.json")
    band = float(v["band"])
    adoption = rjson(it, run + "/adoption.json")
    it.check("verdict adopted is arcsine_corrector_gls", v["adopted"] == "arcsine_corrector_gls", v["adopted"])
    y = df["y"].to_numpy(np.float64)[lab]
    pooled = {}
    for c in cols:
        pooled[c] = mae(y, df[c].to_numpy(np.float64)[lab])
        r = pooled_lookup(sp, c)
        it.check("pooled MAE %s == score_pooled" % c, close(pooled[c], r["mae"]), "%r vs %r" % (pooled[c], r["mae"]))
    order = sorted(cols, key=lambda c: pooled[c])
    print("  pooled MAE, ascending (fire lead 0, %d labelled rows):" % pop["labelled_rows"])
    for i, c in enumerate(order):
        print("   %2d %-40s %.10g" % (i + 1, c, pooled[c]))
    it.values["pooled_mae_ascending"] = [{"rank": i + 1, "column": c, "mae": pooled[c]} for i, c in enumerate(order)]
    it.values["adopted"] = ADOPT
    it.values["band"] = band
    gidx = group_indices(df)
    maps = sbg_maps(sbg)
    mine = {c: group_mae(df, c, gidx) for c in [ADOPT, "arm__log_c_trees_off_unweighted", "base__predict_zero"]}
    for c in mine:
        check_group_maps(it, c, mine[c], maps[c])
    contr = {}
    print("  report-only per-region contrasts (d_g = MAE_ref(g) - MAE_adopted(g); positive = adopted better):")
    for ref in ["arm__log_c_trees_off_unweighted", "base__predict_zero"]:
        groups, d = paired(maps[ref], maps[ADOPT])
        jk = contrast_tag(d, band)
        rec = jk_record(jk, {"groups_adopted_better": int((d > 0).sum()), "n_groups": len(groups),
                             "pooled_contrast": pooled[ref] - pooled[ADOPT],
                             "label": "report-only, post hoc"})
        contr[ref] = rec
        print("   ref %-34s mean %+.6g se %.6g CI [%+.6g, %+.6g] tag %s; adopted better in %d/%d; pooled %+.6g" %
              (ref, jk["mean"], jk["se"], jk["low"], jk["high"], jk["tag"], rec["groups_adopted_better"],
               len(groups), rec["pooled_contrast"]))
    it.values["report_only_contrasts"] = contr
    # final part: re-read adoption.json and jackknife.csv; re-derive jackknife.csv log rows
    pen = adoption["penalty"]
    key_pt = "level=%r,ratio=%r" % (float(pen["level"]), None if pen["ratio"] is None else float(pen["ratio"]))
    surf = adoption["surface_mae"]
    eligible = ["%s_%s_%s" % (e["link"], e["tool"], e["weighting"]) for e in adoption["eligible"]]
    arms = sorted(set(k.split("@")[0] for k in surf))
    sre = {}
    for a in arms:
        at = surf.get("%s@%s" % (a, key_pt), surf.get(a))
        pts = {k.split("@", 1)[1]: val for k, val in surf.items() if k.split("@")[0] == a and "@" in k}
        best = min(pts.items(), key=lambda kv: kv[1]) if pts else (None, surf.get(a))
        sre[a] = {"at_adopted_point": at, "min_over_grid": best[1], "argmin_point": best[0],
                  "eligible": a in eligible}
    it.values["final_reread_adoption_surface"] = {"adopted_point": key_pt, "eligible_arms": eligible,
                                                  "predict_zero_surface_mae": adoption["beside"].get("predict_zero_mae"),
                                                  "per_arm": sre,
                                                  "decision_rows": adoption["decision"].get("n_rows"),
                                                  "decision_units": adoption["decision"].get("n_units")}
    print("  final part, adoption.json surface MAE (inner decision surface, %s rows), at adopted point %s:" %
          (adoption["decision"].get("n_rows"), key_pt))
    for a in arms:
        print("   %-32s at-point %-12s grid-min %-12s eligible %s" % (a, g6(sre[a]["at_adopted_point"]),
                                                                       g6(sre[a]["min_over_grid"]), sre[a]["eligible"]))
    logrows = jkc[(jkc["kind"] == "band_pair") & (jkc["reference"].str.contains("log_c") | jkc["arm"].str.contains("log_c"))]
    rd = []
    for _, r in logrows.iterrows():
        groups, d = paired(maps[r["reference"]], maps[r["arm"]])
        jk = contrast_tag(d, band)
        ok = all(close(jk[k], r[k]) for k in ("mean", "se", "low", "high")) and jk["tag"] == r["tag"] \
            and int(jk["n_groups"]) == int(r["n_groups"]) and bool(jk["identical"]) == (str(r["identical"]) == "True")
        it.check("jackknife.csv %s vs %s re-derived from score_by_group (rtol 1e-12)" % (r["reference"], r["arm"]), ok,
                 "mine %s / file %s" % ((jk["mean"], jk["se"], jk["tag"]), (r["mean"], r["se"], r["tag"])))
        rd.append({"reference": r["reference"], "arm": r["arm"], "mean": jk["mean"], "se": jk["se"],
                   "low": jk["low"], "high": jk["high"], "tag": jk["tag"], "file_tag": r["tag"], "matches_file": ok})
        print("   jackknife.csv %-46s vs %-34s mean %+.4g [%+.4g, %+.4g] tag %s (file %s)" %
              (r["reference"], r["arm"], jk["mean"], jk["low"], jk["high"], jk["tag"], r["tag"]))
    it.values["final_jackknife_log_rows"] = rd
    return it.close()


# ================================================================================================= R13
R13_TRIPLE = {"pm25": ("log_c", "unweighted"), "ndvi": ("identity", "unweighted"), "fire": ("arcsine", "gls"),
              "defo": ("log_c", "unweighted"), "coral": ("arcsine", "gls")}


def item_R13():
    it = Item("R13",
              "Pooled MAE = mean|y-p| over labelled rows of corrector arm__<link>_corrector_<w>, placebo "
              "placebo__<link>_placebo_corrector_<w> and plain arm__<link>_plain_<w> (checked vs score_pooled.csv); "
              "differences corrector-placebo and corrector-plain. Every placebo__ band_pair row of jackknife.csv "
              "re-derived: d_g = MAE_placebo(g) - MAE_corrector(g) from score_by_group.csv, group jackknife z 1.96, "
              "D74 tag with the run band; asserted equal to jackknife.csv (rtol 1e-12).",
              "Lead 0 labelled rows: pm25 91,428 / 127 groups; ndvi 94,527 / 133; fire 94,702 / 40; defo 369,096 / 42; "
              "coral 2,312 / 37. Adopted triples: pm25 log_c/unweighted; ndvi identity/unweighted (adopted arm is plain); "
              "fire arcsine/gls; defo log_c/unweighted; coral arcsine/gls.")
    print("  %-5s %-9s %-10s %-8s | %-14s %-14s %-14s | %-12s %-12s" %
          ("prob", "link", "weight", "adopted", "corrector", "placebo", "plain", "corr-plac", "corr-plain"))
    for prob in PROBS:
        run = RUN[prob]
        schema = pq.ParquetFile(run + "/test_preds.parquet").schema_arrow.names
        cand = [c for c in schema if re.match(r"^(arm__.*_(corrector|plain)_(gls|unweighted)|placebo__.*)$", c)]
        df = rparquet(it, run + "/test_preds.parquet", ["unit", "group", "year", "lead", "y"] + cand)
        lab, pop = labelled_population(df)
        sp = rcsv(it, run + "/score_pooled.csv")
        sbg = rcsv(it, run + "/score_by_group.csv")
        jkc = rcsv(it, run + "/jackknife.csv")
        v = rjson(it, run + "/verdict.json")
        band = float(v["band"])
        y = df["y"].to_numpy(np.float64)[lab]
        triples = []
        for c in cand:
            m = re.match(r"^placebo__(.+)_placebo_corrector_(gls|unweighted)$", c)
            if m:
                triples.append((m.group(1), m.group(2)))
        adopted_t = R13_TRIPLE[prob]
        assert adopted_t in triples, (prob, adopted_t, triples)
        triples = [adopted_t] + sorted(t for t in triples if t != adopted_t)
        recs = []
        for (link, w) in triples:
            cc, pc, pl = ("arm__%s_corrector_%s" % (link, w), "placebo__%s_placebo_corrector_%s" % (link, w),
                          "arm__%s_plain_%s" % (link, w))
            m3 = {}
            for c in (cc, pc, pl):
                m3[c] = mae(y, df[c].to_numpy(np.float64)[lab])
                r = pooled_lookup(sp, c)
                it.check("%s pooled MAE %s == score_pooled" % (prob, c), close(m3[c], r["mae"]),
                         "%r vs %r" % (m3[c], r["mae"]))
            rec = {"link": link, "weighting": w, "adopted_triple": (link, w) == adopted_t,
                   "corrector": m3[cc], "placebo": m3[pc], "plain": m3[pl],
                   "corrector_minus_placebo": m3[cc] - m3[pc], "corrector_minus_plain": m3[cc] - m3[pl]}
            recs.append(rec)
            print("  %-5s %-9s %-10s %-8s | %-14.10g %-14.10g %-14.10g | %+-12.4g %+-12.4g" %
                  (prob, link, w, rec["adopted_triple"], m3[cc], m3[pc], m3[pl], rec["corrector_minus_placebo"],
                   rec["corrector_minus_plain"]))
        maps = sbg_maps(sbg)
        gidx = group_indices(df)
        prow = jkc[(jkc["kind"] == "band_pair") & jkc["reference"].str.startswith("placebo__")]
        jrecs = []
        for _, r in prow.iterrows():
            mine_p = group_mae(df, r["reference"], gidx)
            mine_c = group_mae(df, r["arm"], gidx)
            check_group_maps(it, "%s %s" % (prob, r["reference"]), mine_p, maps[r["reference"]])
            check_group_maps(it, "%s %s" % (prob, r["arm"]), mine_c, maps[r["arm"]])
            groups, d = paired(maps[r["reference"]], maps[r["arm"]])
            jk = contrast_tag(d, band)
            ok = all(close(jk[k], r[k]) for k in ("mean", "se", "low", "high")) and jk["tag"] == r["tag"] \
                and int(jk["n_groups"]) == int(r["n_groups"])
            it.check("%s jackknife.csv %s vs %s re-derived (rtol 1e-12)" % (prob, r["reference"], r["arm"]), ok,
                     "mine %r %r %s / file %r %r %s" % (jk["mean"], jk["se"], jk["tag"], r["mean"], r["se"], r["tag"]))
            jrecs.append({"reference": r["reference"], "arm": r["arm"], "mean": jk["mean"], "se": jk["se"],
                          "low": jk["low"], "high": jk["high"], "n_groups": jk["n_groups"], "tag": jk["tag"],
                          "file_tag": r["tag"], "matches_file": ok})
            print("     placebo pair %-46s mean %+.4g se %.4g [%+.4g, %+.4g] G %d tag %s (file %s)" %
                  (r["reference"], jk["mean"], jk["se"], jk["low"], jk["high"], jk["n_groups"], jk["tag"], r["tag"]))
        it.values[prob] = {"population": pop, "band": band, "triples": recs, "placebo_pairs_rederived": jrecs}
    return it.close()


# ================================================================================================= R14
def item_R14():
    it = Item("R14",
              "kind and centre from derived.json R14 (value.kind, value.centre); (level, ratio) from adoption.json "
              "'penalty'; asserted penalty == best_tree_penalty, declined false, point in derived R14 grid. per_unit: "
              "a_tree = centre[0]*level, a_ctx = a_tree*ratio (0.0 when ratio is null); neighbour: same with the "
              "neighbour centre; region: lambda = centre[0]*level. The context centre (centre[1]) is not used.",
              "One adopted point per run at lead 0: pm25 level 30 ratio 1.0 (per_unit); ndvi level 1 ratio 0.0625 "
              "(per_unit); fire level 100 ratio 1.0 (per_unit); defo level 0.1 ratio null (region); coral level 100 "
              "ratio 1.0 (neighbour). No rows.")
    for prob in PROBS:
        run = RUN[prob]
        a = rjson(it, run + "/adoption.json")
        d = rjson(it, run + "/derived.json")["R14"]
        val = d["value"]
        kind = val.get("kind", d["inputs"].get("kind"))
        it.check("%s derived R14 value.kind == inputs.kind" % prob, kind == d["inputs"].get("kind"),
                 "%s / %s" % (kind, d["inputs"].get("kind")))
        centre = [float(x) for x in val["centre"]]
        pen = a["penalty"]
        level = float(pen["level"])
        ratio = None if pen["ratio"] is None else float(pen["ratio"])
        it.check("%s penalty == best_tree_penalty" % prob, a["penalty"] == a["best_tree_penalty"],
                 "%s / %s" % (a["penalty"], a["best_tree_penalty"]))
        it.check("%s not declined" % prob, a["declined"] is False, str(a["declined"]))
        grid = [(float(g["level"]), None if g["ratio"] is None else float(g["ratio"])) for g in val["grid"]]
        it.check("%s adopted point in derived R14 grid" % prob, (level, ratio) in grid, str((level, ratio)))
        consts = d["inputs"].get("constants", {})
        rec = {"kind": kind, "centre": centre, "level": level, "ratio": ratio, "grid_points": len(grid)}
        if kind in ("per_unit", "neighbour"):
            ck = "C12.per_unit_trees_centre" if kind == "per_unit" else "C12.neighbour_trees_centre"
            if ck in consts:
                it.check("%s centre[0] == %s" % (prob, ck), close(centre[0], consts[ck]), "%s / %s" % (centre[0], consts[ck]))
            a_tree = centre[0] * level
            a_ctx = 0.0 if ratio is None else a_tree * ratio
            rec.update({"a_tree": a_tree, "a_ctx": a_ctx})
            print("  %-5s %-9s centre %-12s level %-6g ratio %-7s -> a_tree %g, a_ctx %g" %
                  (prob, kind, centre, level, ratio, a_tree, a_ctx))
        elif kind == "region":
            if "C12.region_lambda_centre" in consts:
                it.check("%s centre[0] == C12.region_lambda_centre" % prob,
                         close(centre[0], consts["C12.region_lambda_centre"]), "")
            lam = centre[0] * level
            rec.update({"lambda": lam})
            print("  %-5s %-9s centre %-12s level %-6g ratio %-7s -> lambda %g" % (prob, kind, centre, level, ratio, lam))
        else:
            it.check("%s known router kind" % prob, False, kind)
        it.values[prob] = rec
    return it.close()


# ================================================================================================= R15
def item_R15():
    it = Item("R15",
              "Per saved column (arm__/placebo__/base__), over labelled rows where the column is finite: pooled MAE, "
              "anomaly R2 vs the saved normal (NaN on coral), corr2, hit at verdict hit_tolerance and hit_floor at "
              "the declared measurement_error_floor; each checked vs score_pooled.csv (rtol 1e-12). Selectable = arm__ "
              "without 'trees_off'. best = lowest-MAE selectable arm; regret_abs = MAE(adopted)-MAE(best); "
              "regret_rel = regret_abs/MAE(best). Report-only: d_g = MAE_a(g) - MAE_adopted(g) (positive = adopted "
              "better) from score_by_group.csv, group jackknife z 1.96, D74 tag with the run band. Factors: weighting "
              "= MAE(unweighted)-MAE(gls); tool = MAE(plain)-MAE(corrector); link = best selectable arm per link. "
              "NOT a test of the per-unit axis (M56).",
              "Lead 0 labelled rows: pm25 91,428 / 127 groups (17 columns: 10 arms, 4 placebos, 3 baselines; 8 "
              "selectable); ndvi 94,527 / 133 (10: 5, 2, 3; 4); fire 94,702 / 40 (24: 15, 6, 3; 12); defo 369,096 / "
              "42 (15: 9, 3, 3; 6); coral 2,312 / 37 (23: 15, 6, 2; 12).")
    for prob in PROBS:
        run = RUN[prob]
        schema = pq.ParquetFile(run + "/test_preds.parquet").schema_arrow.names
        scored = [c for c in schema if c.startswith(("arm__", "placebo__", "base__"))]
        df = rparquet(it, run + "/test_preds.parquet",
                      ["unit", "group", "year", "lead", "y", "normal", "legal_min", "legal_max"] + scored)
        lab, pop = labelled_population(df)
        sp = rcsv(it, run + "/score_pooled.csv")
        sbg = rcsv(it, run + "/score_by_group.csv")
        v = rjson(it, run + "/verdict.json")
        a = rjson(it, run + "/adoption.json")
        band = float(v["band"])
        tol = float(v["hit_tolerance"])
        floor = v.get("measurement_error_floor")
        floor = None if floor is None else float(floor)
        adopted = "arm__" + v["adopted"]
        ad_a = "arm__%s_%s_%s" % (a["adopted"]["link"], a["adopted"]["tool"], a["adopted"]["weighting"])
        it.check("%s verdict adopted == adoption adopted" % prob, adopted == ad_a, "%s / %s" % (adopted, ad_a))
        eligible = set("arm__%s_%s_%s" % (e["link"], e["tool"], e["weighting"]) for e in a["eligible"])
        y_all = df["y"].to_numpy(np.float64)
        n_all = df["normal"].to_numpy(np.float64)
        normal_ok = bool(np.isfinite(n_all[lab]).any())
        kinds = {"arm": 0, "placebo": 0, "baseline": 0}
        table = {}
        for c in scored:
            p_all = df[c].to_numpy(np.float64)
            m = lab & np.isfinite(p_all)
            yy, pp = y_all[m], p_all[m]
            rec = {"kind": "arm" if c.startswith("arm__") else ("placebo" if c.startswith("placebo__") else "baseline"),
                   "n": int(m.sum()), "mae": mae(yy, pp),
                   "anom_r2": anomaly_r2(yy, pp, n_all[m]) if normal_ok else NAN,
                   "corr2": corr2(yy, pp), "hit": hit_rate(yy, pp, tol),
                   "hit_floor": hit_rate(yy, pp, floor) if floor is not None else NAN}
            kinds[rec["kind"]] += 1
            rec["selectable"] = rec["kind"] == "arm" and "trees_off" not in c
            rec["eligible"] = c in eligible
            r = pooled_lookup(sp, c)
            for k in ("mae", "anom_r2", "corr2", "hit", "hit_floor"):
                it.check("%s %s %s == score_pooled" % (prob, c, k), close(rec[k], r[k]), "%r vs %r" % (rec[k], r[k]))
            table[c] = rec
        sel = [c for c in scored if table[c]["selectable"]]
        best = min(sel, key=lambda c: table[c]["mae"])
        low_any = min(scored, key=lambda c: table[c]["mae"])
        reg_abs = table[adopted]["mae"] - table[best]["mae"]
        reg_rel = reg_abs / table[best]["mae"]
        it.check("%s column counts" % prob, True, "%d columns: %d arms, %d placebos, %d baselines; %d selectable" %
                 (len(scored), kinds["arm"], kinds["placebo"], kinds["baseline"], len(sel)))
        print("\n  %s: %d labelled rows, %d groups; %d columns (%d arms, %d placebos, %d baselines), %d selectable; "
              "tol %.6g floor %s; band %.6g" % (prob, pop["labelled_rows"], pop["groups"], len(scored), kinds["arm"],
                                                kinds["placebo"], kinds["baseline"], len(sel), tol, floor, band))
        print("   %-48s %-5s %-4s %-4s %-13s %-11s %-9s %-9s %-9s" % ("column", "sel", "elig", "adpt", "MAE", "anomR2",
                                                                    "corr2", "hit", "hit_flr"))
        for c in sorted(scored, key=lambda c: table[c]["mae"]):
            t = table[c]
            print("   %-48s %-5s %-4s %-4s %-13.8g %-11.4g %-9.4g %-9.4g %-9.4g" %
                  (c, "Y" if t["selectable"] else "-", "Y" if t["eligible"] else "-", "Y" if c == adopted else "-",
                   t["mae"], t["anom_r2"], t["corr2"], t["hit"], t["hit_floor"]))
        print("   best selectable %s %.10g; adopted %s %.10g; regret %.6g (%.4f%%); lowest any column %s %.10g" %
              (best, table[best]["mae"], adopted, table[adopted]["mae"], reg_abs, 100 * reg_rel, low_any, table[low_any]["mae"]))
        # report-only contrasts vs adopted
        maps = sbg_maps(sbg)
        gidx = group_indices(df)
        mine_ad = group_mae(df, adopted, gidx)
        check_group_maps(it, "%s %s" % (prob, adopted), mine_ad, maps[adopted])
        contr = {}
        for c in sorted(sel, key=lambda c: table[c]["mae"]):
            if c == adopted:
                continue
            check_group_maps(it, "%s %s" % (prob, c), group_mae(df, c, gidx), maps[c])
            groups, d = paired(maps[c], maps[adopted])
            jk = contrast_tag(d, band)
            contr[c] = jk_record(jk, {"groups_adopted_better": int((d > 0).sum()),
                                      "pooled_contrast": table[c]["mae"] - table[adopted]["mae"],
                                      "label": "report-only, post hoc"})
            print("     vs %-44s d %+.5g se %.4g [%+.5g, %+.5g] %-25s adopted better %d/%d" %
                  (c, jk["mean"], jk["se"], jk["low"], jk["high"], jk["tag"], int((d > 0).sum()), len(groups)))
        # factors
        def nm(link, tool, w):
            return "arm__%s_%s_%s" % (link, tool, w)
        links = sorted(set(re.match(r"^arm__(.+)_(plain|corrector|trees_off)_(gls|unweighted)$", c).group(1)
                           for c in scored if c.startswith("arm__")))
        wfx, tfx, lfx = [], [], []
        for link in links:
            for tool in ("plain", "corrector"):
                if nm(link, tool, "unweighted") in table and nm(link, tool, "gls") in table:
                    wfx.append({"link": link, "tool": tool,
                                "unweighted_minus_gls": table[nm(link, tool, "unweighted")]["mae"] - table[nm(link, tool, "gls")]["mae"]})
            for w in ("unweighted", "gls"):
                if nm(link, "plain", w) in table and nm(link, "corrector", w) in table:
                    tfx.append({"link": link, "weighting": w,
                                "plain_minus_corrector": table[nm(link, "plain", w)]["mae"] - table[nm(link, "corrector", w)]["mae"]})
            ls = [c for c in sel if c.startswith("arm__%s_" % link) and re.match(r"^arm__%s_(plain|corrector)_" % re.escape(link), c)]
            bl = min(ls, key=lambda c: table[c]["mae"])
            to = nm(link, "trees_off", "unweighted")
            lfx.append({"link": link, "best_arm": bl, "best_mae": table[bl]["mae"],
                        "trees_off_mae": table[to]["mae"] if to in table else NAN})
        print("   factors: weighting (unw - gls): %s" % ", ".join("%s/%s %+.4g" % (f["link"], f["tool"], f["unweighted_minus_gls"]) for f in wfx))
        print("            tool (plain - corrector): %s" % ", ".join("%s/%s %+.4g" % (f["link"], f["weighting"], f["plain_minus_corrector"]) for f in tfx))
        print("            link (best arm): %s" % ", ".join("%s %s %.6g (TO %.6g)" % (f["link"], f["best_arm"], f["best_mae"], f["trees_off_mae"]) for f in lfx))
        it.values[prob] = {"population": pop, "n_columns": len(scored), "n_arms": kinds["arm"],
                           "n_placebos": kinds["placebo"], "n_baselines": kinds["baseline"], "n_selectable": len(sel),
                           "hit_tolerance": tol, "measurement_error_floor": floor, "band": band,
                           "adopted": adopted, "best_selectable": best, "mae_adopted": table[adopted]["mae"],
                           "mae_best": table[best]["mae"], "regret_abs": reg_abs, "regret_rel": reg_rel,
                           "lowest_column_any_kind": low_any, "lowest_column_mae": table[low_any]["mae"],
                           "eligible": sorted(eligible), "columns": table, "report_only_contrasts_vs_adopted": contr,
                           "factor_weighting": wfx, "factor_tool": tfx, "factor_link": lfx}
    return it.close()


# ================================================================================================= P29
def _holm(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [NAN] * m
    run = 0.0
    for j, i in enumerate(order):
        val = min(1.0, (m - j) * pvals[i])
        run = max(run, val)
        adj[i] = run
    return adj


def item_P29():
    it = Item("P29",
              "Per deciding row: mean, SE from its source (own: contrast_mean/contrast_se; common: board d_mean/d_se; "
              "human: human board d_mean/d_se); checked SE == (high-low)/(2*1.96) and CI == mean +- 1.96 SE (rtol 1e-9); "
              "RIVALS_TABLE d_mean/d_low/d_high/verdict cross-checked. t CI = mean +- t_{0.975,G-1}*SE; p_z = "
              "2*(1-Phi(|mean/SE|)); p_t = 2*(1-T_{G-1}(|mean/SE|)); tag_t = D74 rule with the t CI and the row's band "
              "(declined/identical keep their tag). Holm step-down (alpha 0.05) over the 5 lead-0 own verdicts with p_z "
              "and p_t separately: adj p_(i) = max_{j<=i} min(1,(m-j+1)p_(j)), m=5. Band share = 100*band/mae_reference "
              "of the lead-0 'all' pooled headline row.",
              "79 deciding rows: 14 own (pm25 0/6/12, ndvi 0/6/12, fire 0/6/12, defo 0/1, coral 0/183/365; lead 0 = "
              "verdicts 'all' (verdict.json), leads > 0 = 'common' (ladder.json); 6 declined) + 65 RIVALS_TABLE rows "
              "with decides True (53 common, 12 human; 12 identical). G = row n_groups. Holm over the 5 lead-0 own.")
    rows = []
    for prob in PROBS:
        v = rcsv(it, VERDICTS[prob])
        for _, r in v.iterrows():
            L = int(r["lead"])
            if (L == 0 and r["rows"] == "all") or (L > 0 and r["rows"] == "common"):
                exp_src = "verdict.json" if L == 0 else "ladder.json"
                it.check("%s lead %d own source" % (prob, L), exp_src in str(r["source"]), str(r["source"]))
                rows.append({"who": "own", "problem": prob, "lead": L, "name": "ours vs %s" % r["reference"],
                             "mean": float(r["contrast_mean"]), "se": float(r["contrast_se"]),
                             "low": float(r["contrast_low"]), "high": float(r["contrast_high"]),
                             "G": int(r["n_groups"]), "band": float(r["band"]), "tag": str(r["tag"]),
                             "declined": bool(r["declined"]) if not isinstance(r["declined"], str) else r["declined"] == "True"})
        for L in LEADS[prob]:
            b = rcsv(it, "%s/board_lead_%d.csv" % (RIVAL[prob], L))
            for _, r in b[b["decides"].astype(str) == "True"].iterrows():
                rows.append({"who": "common", "problem": prob, "lead": L, "name": r["learner"],
                             "mean": float(r["d_mean"]), "se": float(r["d_se"]), "low": float(r["d_low"]),
                             "high": float(r["d_high"]), "G": int(r["n_groups"]), "band": float(r["band"]),
                             "tag": str(r["tag"]), "declined": False})
        for L in HUMAN_LEADS.get(prob, []):
            b = rcsv(it, "%s/human_board_lead_%d.csv" % (HUMAN[prob], L))
            for _, r in b[b["decides"].astype(str) == "True"].iterrows():
                rows.append({"who": "human", "problem": prob, "lead": L, "name": r["rival"],
                             "mean": float(r["d_mean"]), "se": float(r["d_se"]), "low": float(r["d_low"]),
                             "high": float(r["d_high"]), "G": int(r["n_groups"]), "band": float(r["band"]),
                             "tag": str(r["tag"]), "declined": False})
    n_own = sum(1 for r in rows if r["who"] == "own")
    n_com = sum(1 for r in rows if r["who"] == "common")
    n_hum = sum(1 for r in rows if r["who"] == "human")
    it.check("row counts 14 own + 53 common + 12 human = 79", (n_own, n_com, n_hum) == (14, 53, 12),
             "%d + %d + %d = %d" % (n_own, n_com, n_hum, len(rows)))
    it.check("6 own rows declined", sum(1 for r in rows if r["who"] == "own" and r["tag"] == "declined") == 6, "")
    it.check("12 rival rows identical", sum(1 for r in rows if r["who"] != "own" and r["tag"] == "identical") == 12,
             str(sum(1 for r in rows if r["who"] != "own" and r["tag"] == "identical")))
    # RIVALS_TABLE cross-check
    rt = rcsv(it, RIVALS_TABLE)
    rtd = rt[rt["decides"].astype(str) == "True"]
    it.check("RIVALS_TABLE decides==True rows = 65", len(rtd) == 65, str(len(rtd)))
    word = {"BEATS": "helps", "LOSES": "hurts", "CANNOT TELL": "cannot_tell", "EQUIVALENT": "does_not_help_equivalent",
            "IDENTICAL": "identical"}
    rtk = {}
    for _, r in rtd.iterrows():
        rtk[(r["problem"], int(r["lead"]), r["rival"])] = r
    matched = 0
    for r in rows:
        if r["who"] == "own":
            continue
        t = rtk.get((r["problem"], r["lead"], r["name"]))
        if t is None:
            it.check("RIVALS_TABLE has %s lead %d %s" % (r["problem"], r["lead"], r["name"]), False)
            continue
        matched += 1
        w = str(t["verdict"]).split(" (")[0].strip()
        ok = close(t["d_mean"], r["mean"], 1e-9, 1e-15) and close(t["d_low"], r["low"], 1e-9, 1e-15) and \
            close(t["d_high"], r["high"], 1e-9, 1e-15) and word.get(w) == r["tag"] and int(t["groups"]) == r["G"] \
            and str(t["rival_type"]) == r["who"]
        it.check("RIVALS_TABLE row %s lead %d %s agrees with its board" % (r["problem"], r["lead"], r["name"]), ok,
                 "table %s %r [%r,%r] G %s / board %s %r [%r,%r] G %d" % (w, t["d_mean"], t["d_low"], t["d_high"], t["groups"],
                                                                          r["tag"], r["mean"], r["low"], r["high"], r["G"]))
    it.check("every RIVALS_TABLE deciding row matched", matched == len(rtd), "%d/%d" % (matched, len(rtd)))
    # per-row computations
    worst_se, worst_ci = 0.0, 0.0
    for r in rows:
        keep = r["tag"] in ("declined", "identical")
        se_rb = (r["high"] - r["low"]) / (2 * Z)
        if r["se"] > 0:
            worst_se = max(worst_se, abs(r["se"] - se_rb) / r["se"])
            worst_ci = max(worst_ci, abs(r["low"] - (r["mean"] - Z * r["se"])) / max(abs(r["mean"]), r["se"]),
                           abs(r["high"] - (r["mean"] + Z * r["se"])) / max(abs(r["mean"]), r["se"]))
        else:
            it.check("%s %s lead %d zero-SE row is declined/identical with a zero CI" % (r["who"], r["problem"], r["lead"]),
                     keep and r["low"] == r["high"] == r["mean"] == 0.0, r["tag"])
        G = r["G"]
        tq = float(stats.t.ppf(0.975, G - 1))
        r["t_quantile"] = tq
        if r["se"] > 0:
            zz = abs(r["mean"] / r["se"])
            r["p_z"] = float(2 * stats.norm.sf(zz))
            r["p_t"] = float(2 * stats.t.sf(zz, G - 1))
            r["low_t"] = r["mean"] - tq * r["se"]
            r["high_t"] = r["mean"] + tq * r["se"]
        else:
            r["p_z"] = r["p_t"] = r["low_t"] = r["high_t"] = NAN
        if keep:
            r["tag_z_reapplied"] = r["tag"]
            r["tag_t"] = r["tag"]
        else:
            r["tag_z_reapplied"] = tag_from_interval(r["mean"], r["low"], r["high"], r["band"])
            r["tag_t"] = tag_from_interval(r["mean"], r["low_t"], r["high_t"], r["band"])
        it.check("%s %s lead %d %s: D74 re-applied on the recorded z CI == recorded tag" %
                 (r["who"], r["problem"], r["lead"], r["name"]), r["tag_z_reapplied"] == r["tag"],
                 "%s vs %s" % (r["tag_z_reapplied"], r["tag"]))
        r["changes"] = r["tag_t"] != r["tag"]
    it.check("SE == (high-low)/(2*1.96) for every row (rtol 1e-9)", worst_se <= 1e-9, "max rel %.3g" % worst_se)
    it.check("CI == mean +- 1.96 SE for every row (rtol 1e-9)", worst_ci <= 1e-9, "max rel %.3g" % worst_ci)
    print("  %-6s %-5s %4s %-26s %4s %-11s %-10s %-27s %-27s %-9s %-9s %-26s %-26s" %
          ("who", "prob", "lead", "name", "G", "mean", "se", "z CI", "t CI", "p_z", "p_t", "tag (recorded)", "tag_t"))
    for r in rows:
        print("  %-6s %-5s %4d %-26s %4d %+-11.4g %-10.4g [%+.4g, %+.4g]%s [%+.4g, %+.4g]%s %-9.4g %-9.4g %-26s %-26s%s" %
              (r["who"], r["problem"], r["lead"], r["name"][:26], r["G"], r["mean"], r["se"], r["low"], r["high"], "",
               r["low_t"], r["high_t"], "", r["p_z"], r["p_t"], r["tag"], r["tag_t"], "  <-- CHANGES" if r["changes"] else ""))
    changed = [r for r in rows if r["changes"]]
    # Holm over the 5 lead-0 own verdicts
    own0 = [r for r in rows if r["who"] == "own" and r["lead"] == 0]
    it.check("5 lead-0 own verdicts", len(own0) == 5, str(len(own0)))
    hz = _holm([r["p_z"] for r in own0])
    ht = _holm([r["p_t"] for r in own0])
    holm = []
    for r, az, at in zip(own0, hz, ht):
        holm.append({"problem": r["problem"], "p_z": r["p_z"], "holm_adj_p_z": az, "survives_z": az <= 0.05,
                     "p_t": r["p_t"], "holm_adj_p_t": at, "survives_t": at <= 0.05})
        print("  Holm %-5s p_z %.5g adj %.5g %s | p_t %.5g adj %.5g %s" % (r["problem"], r["p_z"], az,
              "survives" if az <= 0.05 else "FAILS", r["p_t"], at, "survives" if at <= 0.05 else "FAILS"))
    # band share
    share = {}
    for prob in PROBS:
        h = rcsv(it, HEADLINE[prob])
        hr = h[(h["lead"] == 0) & (h["rows"] == "all") & (h["line"] == "pooled")]
        it.check("%s one lead-0 all pooled headline row" % prob, len(hr) == 1, str(len(hr)))
        hr = hr.iloc[0]
        b = [r["band"] for r in own0 if r["problem"] == prob][0]
        share[prob] = {"band": b, "mae_reference": float(hr["mae_reference"]), "reference": hr["reference"],
                       "band_share_pct": 100.0 * b / float(hr["mae_reference"])}
        print("  band share %-5s band %.6g / %s MAE %.6g = %.4f%%" % (prob, b, hr["reference"], hr["mae_reference"],
                                                                    share[prob]["band_share_pct"]))
    # fire blocked jackknife (report only), read
    jkc = rcsv(it, RUN["fire"] + "/jackknife.csv")
    bj = jkc[jkc["kind"].str.startswith("blocked_jackknife")].iloc[0]
    fire_bj = {"mean": float(bj["mean"]), "se": float(bj["se"]), "low": float(bj["low"]), "high": float(bj["high"]),
               "n_blocks": int(bj["n_groups"]), "kind": bj["kind"]}
    print("  fire blocked jackknife (report only, read): mean %.4g se %.4g CI [%.4g, %.4g] blocks %d" %
          (fire_bj["mean"], fire_bj["se"], fire_bj["low"], fire_bj["high"], fire_bj["n_blocks"]))
    for r in changed:
        print("  CHANGE: %s %s lead %d %s G %d: z CI [%+.6g, %+.6g] p_z %.5g tag %s -> t CI [%+.6g, %+.6g] p_t %.5g tag %s" %
              (r["who"], r["problem"], r["lead"], r["name"], r["G"], r["low"], r["high"], r["p_z"], r["tag"],
               r["low_t"], r["high_t"], r["p_t"], r["tag_t"]))
    it.values = {"n_rows": len(rows), "n_own": n_own, "n_common": n_com, "n_human": n_hum,
                 "n_changed_tag_under_t": len(changed),
                 "changed": [{k: r[k] for k in ("who", "problem", "lead", "name", "G", "mean", "se", "low", "high",
                                                 "low_t", "high_t", "t_quantile", "p_z", "p_t", "tag", "tag_t")} for r in changed],
                 "holm_lead0_own": holm, "band_share": share, "fire_blocked_jackknife_read": fire_bj,
                 "max_rel_se_check": worst_se, "max_rel_ci_check": worst_ci,
                 "rows": [{k: r[k] for k in ("who", "problem", "lead", "name", "G", "band", "mean", "se", "low", "high",
                                             "t_quantile", "low_t", "high_t", "p_z", "p_t", "tag", "tag_t", "changes")} for r in rows]}
    return it.close()


# ================================================================================================= R3b
def item_R3b():
    it = Item("R3b",
              "Model = adopted arm column (verdict.json 'adopted'). Candidates: base__guess_normal, base__last5_normal, "
              "base__predict_zero and arm__<link>_trees_off_unweighted for every link of the run; coral: base__donor_median "
              "and base__predict_zero only. best = lowest pooled MAE over labelled rows; change% = 100*(MAE_model - "
              "MAE_best)/MAE_best (fire also vs predict-zero). MAEs checked vs score_pooled.csv and the headline table.",
              "Lead 0 labelled rows: pm25 91,428 / 127 groups; ndvi 94,527 / 133; fire 94,702 / 40; defo 369,096 / 42; "
              "coral 2,312 / 37.")
    for prob in PROBS:
        run = RUN[prob]
        schema = pq.ParquetFile(run + "/test_preds.parquet").schema_arrow.names
        v = rjson(it, run + "/verdict.json")   # read for 'adopted' (not in the spec list; the formula names it)
        model = "arm__" + v["adopted"]
        if prob == "coral":
            cands = ["base__donor_median", "base__predict_zero"]
        else:
            cands = [c for c in ("base__guess_normal", "base__last5_normal", "base__predict_zero") if c in schema] + \
                    sorted(c for c in schema if re.match(r"^arm__.+_trees_off_unweighted$", c))
        df = rparquet(it, run + "/test_preds.parquet", ["unit", "group", "year", "lead", "y", model] + cands)
        lab, pop = labelled_population(df)
        sp = rcsv(it, run + "/score_pooled.csv")
        y = df["y"].to_numpy(np.float64)
        res = {}
        for c in [model] + cands:
            p = df[c].to_numpy(np.float64)
            m = lab & np.isfinite(p)
            it.check("%s %s finite on every labelled row" % (prob, c), m.sum() == lab.sum(), "%d/%d" % (m.sum(), lab.sum()))
            res[c] = mae(y[m], p[m])
            r = pooled_lookup(sp, c)
            it.check("%s %s MAE == score_pooled" % (prob, c), close(res[c], r["mae"]), "%r vs %r" % (res[c], r["mae"]))
        best = min(cands, key=lambda c: res[c])
        chg = 100.0 * (res[model] - res[best]) / res[best]
        h = rcsv(it, HEADLINE[prob])
        hr = h[(h["lead"] == 0) & (h["rows"] == "all") & (h["line"] == "pooled")].iloc[0]
        it.check("%s headline mae_adopted == model MAE" % prob, close(hr["mae_adopted"], res[model]),
                 "%r vs %r" % (hr["mae_adopted"], res[model]))
        it.check("%s headline mae_predict_zero == PZ MAE" % prob, close(hr["mae_predict_zero"], res["base__predict_zero"]),
                 "%r vs %r" % (hr["mae_predict_zero"], res["base__predict_zero"]))
        if "base__guess_normal" in res:
            it.check("%s headline mae_guess_normal" % prob, close(hr["mae_guess_normal"], res["base__guess_normal"]), "")
        if "base__last5_normal" in res:
            it.check("%s headline mae_last5_normal" % prob, close(hr["mae_last5_normal"], res["base__last5_normal"]), "")
        if hr["reference"] in res:
            it.check("%s headline mae_reference" % prob, close(hr["mae_reference"], res[hr["reference"]]), "")
        rec = {"population": pop, "model": model, "mae_model": res[model], "candidates": {c: res[c] for c in cands},
               "best_baseline": best, "mae_best": res[best], "change_pct_vs_best": chg}
        line = "  %-5s model %-34s %.10g vs best %-36s %.10g -> %+.3f%%" % (prob, model, res[model], best, res[best], chg)
        if prob == "fire":
            rec["change_pct_vs_predict_zero"] = 100.0 * (res[model] - res["base__predict_zero"]) / res["base__predict_zero"]
            line += "; vs PZ %.10g -> %+.3f%%" % (res["base__predict_zero"], rec["change_pct_vs_predict_zero"])
        print(line)
        print("        candidates: " + ", ".join("%s %.8g" % (c, res[c]) for c in sorted(cands, key=lambda c: res[c])))
        it.values[prob] = rec
    return it.close()


# ======================================================================================== rival joins
def join_rivals(it, saved, rdir, learners):
    out = saved.copy()
    gp = {}
    for L in learners:
        p = rparquet(it, "%s/lead_0/preds_%s.parquet" % (rdir, L),
                     ["unit", "time", "lead", "arm__rival_" + L, "arm__rival_%s_raw" % L, "guard_passed"])
        it.check("preds_%s rows == saved rows" % L, len(p) == len(saved), "%d / %d" % (len(p), len(saved)))
        it.check("preds_%s keys unique" % L, not p.duplicated(["unit", "time", "lead"]).any(), "")
        gvals = sorted(set(bool(x) for x in p["guard_passed"].tolist()))
        gp[L] = gvals
        p = p.rename(columns={"guard_passed": "guard_passed_" + L})
        j = out.merge(p, on=["unit", "time", "lead"], how="left", validate="one_to_one", indicator=True)
        it.check("preds_%s joins one-to-one on (unit, time, lead), every saved row matched" % L,
                 len(j) == len(saved) and bool((j["_merge"] == "both").all()), "")
        out = j.drop(columns=["_merge"])
    return out, gp


def per_stratum(it, df, mask, cols, band, ours, label, contrast_cols):
    """n, groups, mean y, mean prediction, MAE per column; per-group contrasts (col - ours) for contrast_cols."""
    y = df["y"].to_numpy(np.float64)
    rows = mask & np.isfinite(y)
    rec = {"n": int(rows.sum()), "n_groups": int(df.loc[rows, "group"].nunique()),
           "mean_y": float(np.mean(y[rows])) if rows.any() else NAN, "columns": {}}
    for c in cols:
        p = df[c].to_numpy(np.float64)
        it.check("%s: %s finite on every stratum row" % (label, c), np.isfinite(p[rows]).all(), "")
        rec["columns"][c] = {"mae": mae(y[rows], p[rows]), "mean_pred": float(np.mean(p[rows]))}
    gidx = group_indices(df)
    om = group_mae(df, ours, gidx, mask=rows)
    rec["contrasts"] = {}
    for c in contrast_cols:
        cm = group_mae(df, c, gidx, mask=rows)
        groups, d = paired(cm, om)
        jk = contrast_tag(d, band)
        rec["contrasts"][c] = jk_record(jk, {"groups_ours_better": int((d > 0).sum()), "n_groups": len(groups),
                                             "label": "report-only, post hoc, outcome-defined stratum"})
    return rec


def print_stratum(name, rec, cols, ours):
    print("  stratum %-16s n %-6d groups %-3d mean y %-10.5g" % (name, rec["n"], rec["n_groups"], rec["mean_y"]))
    for c in cols:
        cc = rec["columns"][c]
        line = "     %-36s MAE %-11.6g mean pred %-11.5g" % (c, cc["mae"], cc["mean_pred"])
        if c in rec["contrasts"]:
            k = rec["contrasts"][c]
            line += " | d %+.5g se %.4g [%+.5g, %+.5g] %-25s ours better %d/%d" % (
                k["mean"], k["se"], k["low"], k["high"], k["tag"], k["groups_ours_better"], k["n_groups"])
        print(line)


# ================================================================================================ RC12
def item_RC12():
    it = Item("RC12",
              "Join each rival preds_<L>.parquet on (unit, time, lead) one-to-one (2,312 rows). Bin (coral_report.py "
              "magnitude_bin): B0 if y == 0, else searchsorted([q25, q50, q75], y, side='left') -> B1..B4 "
              "(right-closed), lead-0 edges of positive donor labels. Per stratum and column (ours = "
              "arm__arcsine_corrector_gls, arm__rival_<L> x5, base__predict_zero, base__donor_median): n, n_groups, "
              "mean y, mean prediction, MAE. Ours per bin checked vs magnitude_bins.csv. Report-only per-group contrast: "
              "d_g = MAE_rival(g) - MAE_ours(g) over the groups with >=1 row in the stratum, group jackknife z 1.96, D74 "
              "tag with the coral band (G < 3 -> cannot tell).",
              "Coral lead 0, all 2,312 test visits (37 scored groups, 2016-2019). Strata: B0 y = 0; B1 (0, q25]; B2 "
              "(q25, q50]; B3 (q50, q75]; B4 > q75 with q25 1.91619047625, q50 7.255, q75 23.9575 (11,338 donor rows); "
              "severe y >= 50. Outcome-defined strata: report-only, post hoc.")
    run, rdir = RUN["coral"], RIVAL["coral"]
    OURS = "arm__arcsine_corrector_gls"
    saved = rparquet(it, run + "/test_preds.parquet",
                     ["unit", "group", "time", "lead", "year", "programme", "y", OURS, "base__donor_median", "base__predict_zero"])
    df, gp = join_rivals(it, saved, rdir, CORAL_LEARNERS)
    lab, pop = labelled_population(df)
    v = rjson(it, run + "/verdict.json")
    band = float(v["band"])
    e = rcsv(it, CORAL_EDGES)
    e0 = e[e["lead"] == 0].iloc[0]
    edges = np.asarray([e0["pos_q25"], e0["pos_q50"], e0["pos_q75"]], dtype=np.float64)
    names = ["B1 (0, q25]", "B2 (q25, q50]", "B3 (q50, q75]", "B4 (q75, max]"]
    y = df["y"].to_numpy(np.float64)
    idx = np.searchsorted(edges, y, side="left")
    bins = np.array(["B0 zero" if y[i] == 0 else names[int(idx[i])] for i in range(y.size)], dtype=object)
    rcols = ["arm__rival_" + L for L in CORAL_LEARNERS]
    cols = [OURS] + rcols + ["base__predict_zero", "base__donor_median"]
    ccols = rcols + ["base__predict_zero", "base__donor_median"]
    strata = [("ALL", np.ones(len(df), bool))] + [(b, bins == b) for b in ["B0 zero"] + names] + [("severe y>=50", y >= 50)]
    res = {}
    for name, mask in strata:
        res[name] = per_stratum(it, df, mask, cols, band, OURS, "coral " + name, ccols)
        print_stratum(name, res[name], cols, OURS)
    # check vs magnitude_bins.csv
    mb = rcsv(it, CORAL_BINS)
    mb0 = mb[(mb["lead"] == 0) & (mb["stratum_value"] == "ALL") & (mb["rows_basis"] == "all")]
    for b in ["B0 zero"] + names:
        for c in (OURS, "base__predict_zero", "base__donor_median"):
            s = mb0[(mb0["bin"] == b) & (mb0["column"] == c)]
            if len(s) != 1:
                it.check("magnitude_bins.csv has %s %s" % (b, c), False, str(len(s)))
                continue
            s = s.iloc[0]
            r = res[b]
            ok = int(s["n"]) == r["n"] and int(s["n_groups"]) == r["n_groups"] and close(s["mean_y"], r["mean_y"]) and \
                close(s["mean_pred"], r["columns"][c]["mean_pred"]) and close(s["mae"], r["columns"][c]["mae"])
            it.check("magnitude_bins.csv %s %s (n, groups, mean y, mean pred, MAE; rtol 1e-12)" % (b, c), ok,
                     "file n %s g %s mae %r / mine n %d g %d mae %r" % (s["n"], s["n_groups"], s["mae"], r["n"],
                                                                         r["n_groups"], r["columns"][c]["mae"]))
    # board check
    bd = rcsv(it, rdir + "/board_lead_0.csv")
    bdg = bd[bd["contrast"] == "guarded_vs_headline"]
    for L in CORAL_LEARNERS:
        r = bdg[bdg["learner"] == L].iloc[0]
        it.check("board rival_mae %s == all-rows pooled MAE" % L, close(r["rival_mae"], res["ALL"]["columns"]["arm__rival_" + L]["mae"]),
                 "%r vs %r" % (r["rival_mae"], res["ALL"]["columns"]["arm__rival_" + L]["mae"]))
        it.check("board ours_mae (%s row) == all-rows pooled MAE ours" % L, close(r["ours_mae"], res["ALL"]["columns"][OURS]["mae"]),
                 "%r vs %r" % (r["ours_mae"], res["ALL"]["columns"][OURS]["mae"]))
        it.check("board ALL-rows contrast %s re-derived (mean, se; rtol 1e-9)" % L,
                 close(r["d_mean"], res["ALL"]["contrasts"]["arm__rival_" + L]["mean"], 1e-9) and
                 close(r["d_se"], res["ALL"]["contrasts"]["arm__rival_" + L]["se"], 1e-9) and
                 r["tag"] == res["ALL"]["contrasts"]["arm__rival_" + L]["tag"],
                 "board %r %r %s / mine %r %r %s" % (r["d_mean"], r["d_se"], r["tag"], res["ALL"]["contrasts"]["arm__rival_" + L]["mean"],
                                                    res["ALL"]["contrasts"]["arm__rival_" + L]["se"], res["ALL"]["contrasts"]["arm__rival_" + L]["tag"]))
    it.values = {"population": pop, "edges_lead0": {"pos_q25": float(edges[0]), "pos_q50": float(edges[1]),
                                                    "pos_q75": float(edges[2]), "donor_rows": int(e0["donor_rows"])},
                 "band": band, "guard_passed": gp, "strata": res,
                 "focus_hgb_l1": {k: {"ours_mae": res[k]["columns"][OURS]["mae"],
                                      "hgb_l1_mae": res[k]["columns"]["arm__rival_hgb_l1"]["mae"],
                                      "lower": "ours" if res[k]["columns"][OURS]["mae"] < res[k]["columns"]["arm__rival_hgb_l1"]["mae"] else "hgb_l1",
                                      "n": res[k]["n"], "n_groups": res[k]["n_groups"]} for k in res}}
    print("  focus hgb_l1: " + "; ".join("%s ours %.4g vs L1 %.4g (%s lower)" % (k, v_["ours_mae"], v_["hgb_l1_mae"], v_["lower"])
                                         for k, v_ in it.values["focus_hgb_l1"].items()))
    return it.close()


# ================================================================================================== A1
def item_A1():
    it = Item("A1",
              "Join each rival on (unit, time, lead). Per stratum: n, n_groups, mean y, mean prediction, MAE for ours "
              "(arm__arcsine_corrector_gls), arm__rival_<L> (deciding guarded column), Ridge raw beside, predict-zero. "
              "Per-group contrast d_g = MAE_Tweedie(g) - MAE_ours(g) over the stratum's groups (other rivals beside), "
              "group jackknife z 1.96, groups where ours is better (d_g > 0), D74 tag with the fire band (report-only). "
              "q99 = numpy.quantile(y over the 94,702 labelled rows, 0.99, linear). All-rows pooled MAEs checked vs "
              "board_lead_0.csv rival_mae / ours_mae (rtol 1e-12).",
              "Fire lead 0 labelled rows 94,702 (40 groups, 2019-2022). Strata: y == 0; y > 0; top 1% y >= q99 (q99 from "
              "TEST labels); 0 < y < q99. Outcome-conditional, post hoc.")
    run, rdir = RUN["fire"], RIVAL["fire"]
    OURS = "arm__arcsine_corrector_gls"
    saved = rparquet(it, run + "/test_preds.parquet",
                     ["unit", "group", "time", "lead", "year", "y", OURS, "base__predict_zero", "base__guess_normal",
                      "arm__identity_trees_off_unweighted"])
    df, gp = join_rivals(it, saved, rdir, FIRE_LEARNERS)
    lab, pop = labelled_population(df)
    v = rjson(it, run + "/verdict.json")
    band = float(v["band"])
    y = df["y"].to_numpy(np.float64)
    q99 = float(np.quantile(y[lab], 0.99))
    ridge_eq_to = float(np.nanmax(np.abs(df["arm__rival_ridge"].to_numpy(np.float64)[lab]
                                         - df["arm__identity_trees_off_unweighted"].to_numpy(np.float64)[lab])))
    tw, twr = "arm__rival_lgbm_tweedie", "arm__rival_lgbm_tweedie_raw"
    it.check("Tweedie guard passed and guarded == raw on every row", gp["lgbm_tweedie"] == [True] and
             np.array_equal(df[tw].to_numpy(np.float64), df[twr].to_numpy(np.float64), equal_nan=True), str(gp["lgbm_tweedie"]))
    ridge = df["arm__rival_ridge"].to_numpy(np.float64)
    gn = df["base__guess_normal"].to_numpy(np.float64)
    it.check("Ridge guard failed (guard_passed False)", gp["ridge"] == [False], str(gp["ridge"]))
    ridge_eq_gn = float(np.nanmax(np.abs(ridge[lab] - gn[lab])))
    rcols = ["arm__rival_" + L for L in FIRE_LEARNERS]
    cols = [OURS] + rcols + ["arm__rival_ridge_raw", "base__predict_zero"]
    ccols = [tw] + [c for c in rcols if c != tw] + ["arm__rival_ridge_raw", "base__predict_zero"]
    strata = [("ALL labelled", lab), ("y == 0", lab & (y == 0)), ("y > 0", lab & (y > 0)),
              ("top 1% y >= q99", lab & (y >= q99)), ("0 < y < q99", lab & (y > 0) & (y < q99))]
    res = {}
    for name, mask in strata:
        res[name] = per_stratum(it, df, mask, cols, band, OURS, "fire " + name, ccols)
        res[name]["share_of_labelled_pct"] = 100.0 * res[name]["n"] / pop["labelled_rows"]
        print_stratum(name, res[name], cols, OURS)
    strict = int((lab & (y > q99)).sum())
    print("  q99 = %.9g (6 d.p. %.6f); y >= q99: %d rows; y > q99 (strict): %d rows; max |ridge guarded - guess_normal| on "
          "labelled rows = %.3g; max |ridge guarded - identity trees-off| = %.3g" %
          (q99, q99, res["top 1% y >= q99"]["n"], strict, ridge_eq_gn, ridge_eq_to))
    bd = rcsv(it, rdir + "/board_lead_0.csv")
    bdg = bd[bd["contrast"] == "guarded_vs_headline"]
    for L in FIRE_LEARNERS:
        r = bdg[bdg["learner"] == L].iloc[0]
        it.check("board rival_mae %s == all-rows pooled MAE" % L, close(r["rival_mae"], res["ALL labelled"]["columns"]["arm__rival_" + L]["mae"]),
                 "%r vs %r" % (r["rival_mae"], res["ALL labelled"]["columns"]["arm__rival_" + L]["mae"]))
        it.check("board ours_mae (%s row) == all-rows pooled MAE ours" % L, close(r["ours_mae"], res["ALL labelled"]["columns"][OURS]["mae"]),
                 "%r vs %r" % (r["ours_mae"], res["ALL labelled"]["columns"][OURS]["mae"]))
    tws = {k: {"n": res[k]["n"], "n_groups": res[k]["n_groups"], "mean_y": res[k]["mean_y"],
               "ours_mae": res[k]["columns"][OURS]["mae"], "tweedie_mae": res[k]["columns"][tw]["mae"],
               "ours_mean_pred": res[k]["columns"][OURS]["mean_pred"], "tweedie_mean_pred": res[k]["columns"][tw]["mean_pred"],
               "contrast_tweedie_minus_ours": res[k]["contrasts"][tw]} for k in res}
    it.values = {"population": pop, "band": band, "q99": q99, "q99_6dp": "%.6f" % q99, "top1_strict_gt_rows": strict,
                 "guard_passed": gp, "ridge_guarded_minus_guess_normal_maxabs": ridge_eq_gn,
                 "ridge_guarded_minus_identity_trees_off_maxabs": ridge_eq_to,
                 "tweedie_focus": tws, "strata": res}
    return it.close()


# ================================================================================================== A2
def item_A2():
    it = Item("A2",
              "Join on (unit, time, lead); keep y > 0. Pooled MAE for ours (arm__arcsine_corrector_gls), each "
              "arm__rival_<L> (guarded == raw asserted), predict-zero and donor median; mean y and mean predictions. "
              "Per rival: d_g = MAE_rival(g) - MAE_ours(g) over the groups, group jackknife z 1.96, groups where ours is "
              "better (d_g > 0), D74 tag with the coral band (report-only). All-rows pooled MAEs checked vs "
              "board_lead_0.csv rival_mae / ours_mae (rtol 1e-12).",
              "Coral lead 0 visits with y > 0: 1,024 of 2,312 (36 of the 37 scored groups), 2016-2019. Outcome-conditional, "
              "post hoc.")
    run, rdir = RUN["coral"], RIVAL["coral"]
    OURS = "arm__arcsine_corrector_gls"
    saved = rparquet(it, run + "/test_preds.parquet",
                     ["unit", "group", "time", "lead", "year", "y", OURS, "base__donor_median", "base__predict_zero"])
    df, gp = join_rivals(it, saved, rdir, CORAL_LEARNERS)
    lab, pop = labelled_population(df)
    v = rjson(it, run + "/verdict.json")
    band = float(v["band"])
    for L in CORAL_LEARNERS:
        it.check("%s guard passed and guarded == raw on every row" % L, gp[L] == [True] and np.array_equal(
            df["arm__rival_" + L].to_numpy(np.float64), df["arm__rival_%s_raw" % L].to_numpy(np.float64), equal_nan=True), str(gp[L]))
    y = df["y"].to_numpy(np.float64)
    rcols = ["arm__rival_" + L for L in CORAL_LEARNERS]
    cols = [OURS] + rcols + ["base__predict_zero", "base__donor_median"]
    allr = per_stratum(it, df, lab, cols, band, OURS, "coral ALL", rcols)
    act = per_stratum(it, df, lab & (y > 0), cols, band, OURS, "coral y>0", rcols + ["base__predict_zero", "base__donor_median"])
    print_stratum("ALL", allr, cols, OURS)
    print_stratum("y > 0", act, cols, OURS)
    bd = rcsv(it, rdir + "/board_lead_0.csv")
    bdg = bd[bd["contrast"] == "guarded_vs_headline"]
    for L in CORAL_LEARNERS:
        r = bdg[bdg["learner"] == L].iloc[0]
        it.check("board rival_mae %s == all-rows pooled MAE" % L, close(r["rival_mae"], allr["columns"]["arm__rival_" + L]["mae"]),
                 "%r vs %r" % (r["rival_mae"], allr["columns"]["arm__rival_" + L]["mae"]))
        it.check("board ours_mae (%s row) == all-rows pooled MAE ours" % L, close(r["ours_mae"], allr["columns"][OURS]["mae"]), "")
    it.values = {"population": pop, "band": band, "guard_passed": gp, "active_y_gt_0": act, "all_rows": allr,
                 "summary": {L: {"rival_mae": act["columns"]["arm__rival_" + L]["mae"], "ours_mae": act["columns"][OURS]["mae"],
                                 "d_mean": act["contrasts"]["arm__rival_" + L]["mean"],
                                 "d_low": act["contrasts"]["arm__rival_" + L]["low"],
                                 "d_high": act["contrasts"]["arm__rival_" + L]["high"],
                                 "tag": act["contrasts"]["arm__rival_" + L]["tag"],
                                 "groups_ours_better": act["contrasts"]["arm__rival_" + L]["groups_ours_better"],
                                 "n_groups": act["contrasts"]["arm__rival_" + L]["n_groups"]} for L in CORAL_LEARNERS}}
    return it.close()


# ================================================================================================ main
def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating,)):
        o = float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, float) and not math.isfinite(o):
        return None if math.isnan(o) else ("inf" if o > 0 else "-inf")
    return o


def main():
    print("posthoc_A.py -- POST HOC numbers (test labels already opened); report-only; no verdict changes.")
    print("python %s, numpy %s, pandas %s, scipy %s" % (sys.version.split()[0], np.__version__, pd.__version__,
                                                        __import__("scipy").__version__))
    results = {}
    for fn in (item_M34, item_R12, item_R13, item_R14, item_R15, item_P29, item_R3b, item_RC12, item_A1, item_A2):
        r = fn()
        results[r["id"]] = r
    doc = {"implementer": "A", "script": "D:/treeroute/analysis/paper_posthoc/posthoc_A.py",
           "post_hoc": "computed after the test labels were opened; never changes a pre-registered verdict",
           "spec_sha256_prefix": sha256_file(SPEC_JSON)[:16] if SPEC_PREFIX else None,
           "nan_encoding": "NaN written as null",
           "failed_checks": [{"item": a, "check": b, "detail": c} for a, b, c in ALL_FAILS],
           "items": results}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(_clean(doc), f, indent=1, allow_nan=False)
    print("\nwrote %s" % OUT_JSON)
    print("FAILED CHECKS: %d" % len(ALL_FAILS))
    for a, b, c in ALL_FAILS:
        print("  %s: %s %s" % (a, b, c))


if __name__ == "__main__":
    main()
