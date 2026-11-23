"""posthoc_B.py -- implementer B of the paper post-hoc spec (M34, R12, R13, R14, R15, P29, R3b, RC12, A1, A2).

POST HOC: every number here is computed AFTER the test labels were opened. Nothing here changes a
pre-registered verdict. Light compute only: pandas/pyarrow on saved predictions and CSVs; no refit,
no re-routing, no engine import (the engine formulas are re-implemented below and cited by line).

Run:  py -3.9 -I D:/treeroute/analysis/paper_posthoc/posthoc_B.py
Writes ONLY D:/treeroute/analysis/paper_posthoc/result_B.json (everything else is read-only).

Engine definitions replicated (C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/treeroute):
  report/metrics.py mae() 569, anomaly_r2() 580 (NaN under 10 rows or SSE(normal) == 0), corr2() 604,
  hit_rate() 688 (inclusive), score_table() 846 (labelled & finite rows; groupby indices order),
  group_jackknife() 1032 (z = 1.96, NaN under 3 groups), contrast_tag() 1097 (IDENTICAL_ATOL 1e-12),
  _paired_contrast() 1123 (sorted group order; d = reference - arm).
No seed variation anywhere; every interval is a leave-one-REGION(group)-out jackknife.
Every CSV is read with float_precision='round_trip' (pandas' default fast parser can be 1 ulp off the
written repr, which breaks rtol-1e-12 re-derivations of small contrasts).
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
RESULT = OUT_DIR + "/result_B.json"
RUNS_ROOT = "D:/treeroute/runs"
RUN = {
    "pm25": RUNS_ROOT + "/pm25/headline/20261007_74e67609",
    "ndvi": RUNS_ROOT + "/ndvi/headline/20261016_d1de3158",
    "fire": RUNS_ROOT + "/fire/headline/20261017_869d1f38",
    "defo": RUNS_ROOT + "/defo/headline/20261017_d71c61f4",
    "coral": RUNS_ROOT + "/coral/headline/20261020_f3b8e3da",
}
HT = RUNS_ROOT + "/_headline_tables"
HEADLINE_CSV = {"pm25": HT + "/headline_93b64854d1f9.csv", "ndvi": HT + "/ndvi/headline_9e5590eab94b.csv",
                "fire": HT + "/fire/headline_85a9134089e4.csv", "defo": HT + "/defo/headline_1571da960aa6.csv",
                "coral": HT + "/coral/headline_344838cf7de1.csv"}
VERDICTS_CSV = {"pm25": HT + "/verdicts_9abcea419ce2.csv", "ndvi": HT + "/ndvi/verdicts_c4cd7e7c2610.csv",
                "fire": HT + "/fire/verdicts_7ee7167afe8d.csv", "defo": HT + "/defo/verdicts_bf99c6741bce.csv",
                "coral": HT + "/coral/verdicts_a9d948cbf26b.csv"}
RIV = {"pm25": "D:/treeroute/rivals/pm25/20261007_74e67609", "ndvi": "D:/treeroute/rivals/ndvi/20261016_d1de3158",
       "fire": "D:/treeroute/rivals/fire/20261017_869d1f38", "defo": "D:/treeroute/rivals/defo/20261017_d71c61f4",
       "coral": "D:/treeroute/rivals/coral/20261020_f3b8e3da"}
HUM = {"pm25": "D:/treeroute/rivals_human/pm25/20261007_74e67609",
       "ndvi": "D:/treeroute/rivals_human/ndvi/20261016_d1de3158",
       "defo": "D:/treeroute/rivals_human/defo/20261017_d71c61f4",
       "coral": "D:/treeroute/rivals_human/coral/20261020_f3b8e3da"}
LEADS = {"pm25": [0, 6, 12], "ndvi": [0, 6, 12], "fire": [0, 6, 12], "defo": [0, 1], "coral": [0, 183, 365]}
RIVALS_TABLE = "D:/treeroute/rivals_table/20261025T162302876402Z/RIVALS_TABLE.csv"
CORAL_REPORT = HT + "/coral/coral_report"

# sha256 prefixes stated by the spec for every input (checked; a mismatch stops the script)
EXPECT = {
    RUN["pm25"] + "/test_preds.parquet": "9e62fe4256c08c50", RUN["ndvi"] + "/test_preds.parquet": "87c0b1414af7e370",
    RUN["fire"] + "/test_preds.parquet": "86e9c97a58a9b714", RUN["defo"] + "/test_preds.parquet": "3a002e9a9deb006a",
    RUN["coral"] + "/test_preds.parquet": "dd07762558023d5f",
    RUN["pm25"] + "/score_pooled.csv": "8a7d2f44f00a9e7c", RUN["ndvi"] + "/score_pooled.csv": "3a7e09b6156e4449",
    RUN["fire"] + "/score_pooled.csv": "9236a25380d9aede", RUN["defo"] + "/score_pooled.csv": "8f1c161ad318e32c",
    RUN["coral"] + "/score_pooled.csv": "bbaa21aa184a1054",
    RUN["pm25"] + "/score_by_group.csv": "6fed1e7be9456655", RUN["ndvi"] + "/score_by_group.csv": "be1381c5568d225e",
    RUN["fire"] + "/score_by_group.csv": "03585591911c6e01", RUN["defo"] + "/score_by_group.csv": "d02e8f48ddef39ce",
    RUN["coral"] + "/score_by_group.csv": "08dd01c06c8eedc2",
    RUN["pm25"] + "/jackknife.csv": "25624a91d0879ae2", RUN["ndvi"] + "/jackknife.csv": "533c7dd30d5b5f5b",
    RUN["fire"] + "/jackknife.csv": "b8557782d9cdd703", RUN["defo"] + "/jackknife.csv": "aa7a8cd183eb5108",
    RUN["coral"] + "/jackknife.csv": "04178dc5d388f9f7",
    RUN["pm25"] + "/verdict.json": "af031ef5a44dbe67", RUN["ndvi"] + "/verdict.json": "535ef992b5057ed7",
    RUN["fire"] + "/verdict.json": "6c744bc1a0647e37", RUN["defo"] + "/verdict.json": "34d090aae96fed3c",
    RUN["coral"] + "/verdict.json": "6bf9b04970173323",
    RUN["pm25"] + "/adoption.json": "b6408c90560b4585", RUN["ndvi"] + "/adoption.json": "d5ae6f1dd6728681",
    RUN["fire"] + "/adoption.json": "75f70e5cd22039b6", RUN["defo"] + "/adoption.json": "d8ebdd4cc458b276",
    RUN["coral"] + "/adoption.json": "2106a36efee4f9fc",
    RUN["pm25"] + "/derived.json": "3e2d692b74ad6472", RUN["ndvi"] + "/derived.json": "8ecc92b58cbd5f65",
    RUN["fire"] + "/derived.json": "9255562ca6959e9e", RUN["defo"] + "/derived.json": "e17b92cfe8ba31cc",
    RUN["coral"] + "/derived.json": "5fd02863f8b91573",
    HEADLINE_CSV["pm25"]: "93b64854d1f9c6bf", HEADLINE_CSV["ndvi"]: "9e5590eab94b7373",
    HEADLINE_CSV["fire"]: "85a9134089e47a61", HEADLINE_CSV["defo"]: "1571da960aa6540e",
    HEADLINE_CSV["coral"]: "344838cf7de1df55",
    VERDICTS_CSV["pm25"]: "9abcea419ce2fe63", VERDICTS_CSV["ndvi"]: "c4cd7e7c2610e218",
    VERDICTS_CSV["fire"]: "7ee7167afe8d7a52", VERDICTS_CSV["defo"]: "bf99c6741bcee256",
    VERDICTS_CSV["coral"]: "a9d948cbf26be365",
    RIV["pm25"] + "/board_lead_0.csv": "4b2b7550b77ebe78", RIV["pm25"] + "/board_lead_6.csv": "1b88a644d9110a3e",
    RIV["pm25"] + "/board_lead_12.csv": "37abd537cd3e0f69",
    RIV["ndvi"] + "/board_lead_0.csv": "b8208282f1c27ccc", RIV["ndvi"] + "/board_lead_6.csv": "0d48164188f8dfe5",
    RIV["ndvi"] + "/board_lead_12.csv": "972572216dcbf949",
    RIV["fire"] + "/board_lead_0.csv": "031a261083ce6964", RIV["fire"] + "/board_lead_6.csv": "b9d7636d26f8ad71",
    RIV["fire"] + "/board_lead_12.csv": "02236b90973a9c87",
    RIV["defo"] + "/board_lead_0.csv": "0ca58e02d963f54e", RIV["defo"] + "/board_lead_1.csv": "6e9086b1decc531d",
    RIV["coral"] + "/board_lead_0.csv": "3220b5c8967f0570", RIV["coral"] + "/board_lead_183.csv": "1cba4ab97d3197a0",
    RIV["coral"] + "/board_lead_365.csv": "393d7ff606d7b76e",
    HUM["pm25"] + "/human_board_lead_0.csv": "e8d72653cfc47bb1",
    HUM["pm25"] + "/human_board_lead_6.csv": "2281408c408f5fd8",
    HUM["pm25"] + "/human_board_lead_12.csv": "a097e9b97b33810e",
    HUM["ndvi"] + "/human_board_lead_0.csv": "50db5b3db4a694c8",
    HUM["ndvi"] + "/human_board_lead_6.csv": "18ba49e839e9a178",
    HUM["ndvi"] + "/human_board_lead_12.csv": "ce304d4cdf002620",
    HUM["defo"] + "/human_board_lead_0.csv": "b912d3b3c726a7cc",
    HUM["defo"] + "/human_board_lead_1.csv": "fc9dd957167b9b3d",
    HUM["coral"] + "/human_board_lead_0.csv": "8fa769680440d5e5",
    HUM["coral"] + "/human_board_lead_183.csv": "7b57584131254f9c",
    HUM["coral"] + "/human_board_lead_365.csv": "7e7e8602d6a216f3",
    RIVALS_TABLE: "1ccac0e7eb9defc0",
    RIV["coral"] + "/lead_0/preds_ridge.parquet": "f84ad92e63f9855c",
    RIV["coral"] + "/lead_0/preds_rf.parquet": "36830d55b5092fb7",
    RIV["coral"] + "/lead_0/preds_lgbm.parquet": "3e1d4b01737efbbf",
    RIV["coral"] + "/lead_0/preds_lgbm_tweedie.parquet": "41f5fa63b5ebb276",
    RIV["coral"] + "/lead_0/preds_hgb_l1.parquet": "7039e548bf4ead04",
    RIV["fire"] + "/lead_0/preds_ridge.parquet": "83f991a07a8cd126",
    RIV["fire"] + "/lead_0/preds_rf.parquet": "7634c4a48a959eec",
    RIV["fire"] + "/lead_0/preds_lgbm.parquet": "954ca794d932bac1",
    RIV["fire"] + "/lead_0/preds_lgbm_tweedie.parquet": "17979c68252cfd2d",
    CORAL_REPORT + "/magnitude_edges.csv": "d6571f1f6d8f314d",
    CORAL_REPORT + "/magnitude_bins.csv": "6cafcee415a42ed0",
}

Z = 1.96                 # engine_constants.py S2.jackknife_z, line 323
IDENTICAL_ATOL = 1e-12   # report/metrics.py line 112
ANOMALY_R2_MIN_ROWS = 10  # report/metrics.py line 115
RTOL = 1e-12

# ============================================================================== input bookkeeping
_SHA = {}
_CUR = None
FAILED = []


def use(path):
    """Hash a file once, check the spec's prefix, record it for the current item."""
    p = path.replace("\\", "/")
    if p not in _SHA:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _SHA[p] = h.hexdigest()
    full = _SHA[p]
    exp = EXPECT.get(p)
    if exp is None:
        raise SystemExit("input not in the spec's list: %s" % p)
    if not full.startswith(exp):
        raise SystemExit("SHA256 MISMATCH %s: spec %s, file %s" % (p, exp, full[:16]))
    if _CUR is not None:
        _CUR["inputs"][p] = full[:16]
    return p


class Item:
    def __init__(self, iid, what, population, formula):
        global _CUR
        self.d = {"id": iid, "what": what, "post_hoc": True, "population": population, "formula": formula,
                  "inputs": {}, "checks": [], "values": {}, "notes": []}
        _CUR = self.d
        print("\n" + "=" * 110)
        print("%s  (POST HOC: computed after the test labels were opened; changes no pre-registered verdict)" % iid)
        print(what)
        print("Population: " + population)
        print("=" * 110)

    def close(self, what, got, want, rtol=RTOL):
        got = None if got is None else float(got)
        want = None if want is None else float(want)
        if got is None or want is None:
            ok = got is None and want is None
        elif math.isnan(got) or math.isnan(want):
            ok = math.isnan(got) and math.isnan(want)
        else:
            ok = math.isclose(got, want, rel_tol=rtol, abs_tol=0.0)
        rec = {"check": what, "got": got, "want": want, "rtol": rtol, "ok": bool(ok)}
        self.d["checks"].append(rec)
        if not ok:
            FAILED.append((self.d["id"], what, got, want))
            print("  CHECK FAILED: %s got %r want %r" % (what, got, want))
        return ok

    def true(self, what, cond, detail=None):
        rec = {"check": what, "ok": bool(cond)}
        if detail is not None:
            rec["detail"] = detail
        self.d["checks"].append(rec)
        if not cond:
            FAILED.append((self.d["id"], what, detail, None))
            print("  CHECK FAILED: %s %s" % (what, "" if detail is None else detail))
        return bool(cond)

    def note(self, s):
        self.d["notes"].append(s)
        print("NOTE: " + s)

    def summary(self):
        n = len(self.d["checks"])
        bad = sum(1 for c in self.d["checks"] if not c["ok"])
        print("-- %s checks: %d run, %d failed; inputs: %s" % (self.d["id"], n, bad,
              ", ".join("%s [%s]" % (k, v) for k, v in self.d["inputs"].items())))
        return self.d


# ============================================================================== engine metric replicas
def mae(y, p):
    return float(np.mean(np.abs(y - p)))


def anomaly_r2(y, p, n):
    if y.size < ANOMALY_R2_MIN_ROWS:
        return float("nan")
    ay, ap = y - n, p - n
    s0 = float(np.sum(ay ** 2))
    if not s0 > 0:
        return float("nan")
    return 1.0 - float(np.sum((ay - ap) ** 2)) / s0


def corr2(y, p):
    if y.max() == y.min() or p.max() == p.min():
        return float("nan")
    yc, pc = y - y.mean(), p - p.mean()
    syy, spp = float(np.sum(yc * yc)), float(np.sum(pc * pc))
    if not (syy > 0 and spp > 0):
        return float("nan")
    r = float(np.sum(yc * pc)) / math.sqrt(syy * spp)
    return r * r


def hit_rate(y, p, tol):
    return float(np.mean(np.abs(y - p) <= tol))


def jackknife(v):
    v = np.asarray(v, dtype=np.float64)
    n = int(v.size)
    if n < 3:
        return {"mean": float(v.mean()), "se": float("nan"), "low": float("nan"), "high": float("nan"),
                "n_groups": n}
    jk = np.array([np.delete(v, i).mean() for i in range(n)])
    se = float(np.sqrt((n - 1) / n * ((jk - jk.mean()) ** 2).sum()))
    return {"mean": float(v.mean()), "se": se, "low": float(v.mean() - Z * se), "high": float(v.mean() + Z * se),
            "n_groups": n}


def tag_rule(low, high, mean, band):
    """D74 after the IDENTICAL step (contrast_tag lines 1112-1120)."""
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
    if np.all(np.abs(dv) <= IDENTICAL_ATOL):
        return "identical", jk
    return tag_rule(jk["low"], jk["high"], jk["mean"], band), jk


def paired(ref_map, arm_map):
    """_paired_contrast: sorted groups, d = ref - arm."""
    assert set(ref_map) == set(arm_map), "different group sets"
    groups = sorted(ref_map)
    return groups, np.array([float(ref_map[g]) - float(arm_map[g]) for g in groups])


def fmt(x, d=6):
    if x is None:
        return "None"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    x = float(x)
    if math.isnan(x):
        return "NaN"
    return "%.*g" % (d, x)


def contrast_record(dv, band, groups):
    tag, jk = contrast_tag(dv, band)
    return {"tag": tag, "mean": jk["mean"], "se": jk["se"], "low": jk["low"], "high": jk["high"],
            "n_groups": jk["n_groups"], "groups_positive": int((dv > 0).sum()), "groups": len(groups)}


# ============================================================================== cached readers
_PRED = {}
_SCORE = {}
_JSON = {}


def read_json(path):
    use(path)
    if path not in _JSON:
        with open(path, "r", encoding="utf-8") as f:
            _JSON[path] = json.load(f)
    return _JSON[path]


def verdict(run):
    return read_json(RUN[run] + "/verdict.json")


def adoption(run):
    return read_json(RUN[run] + "/adoption.json")


def preds(run):
    """Saved test rows: keys, y, normal, legal range and every scored column (arm__/placebo__/base__)."""
    path = use(RUN[run] + "/test_preds.parquet")
    if run not in _PRED:
        names = pq.ParquetFile(path).schema_arrow.names
        keys = [c for c in ("unit", "group", "time", "year", "lead", "programme", "y", "normal", "legal_min",
                            "legal_max") if c in names]
        scored = [c for c in names if c.startswith(("arm__", "placebo__", "base__"))]
        df = pq.read_table(path, columns=keys + scored).to_pandas()
        _PRED[run] = (df, scored)
    return _PRED[run]


def score_csv(run, name):
    path = use(RUN[run] + "/" + name)
    key = (run, name)
    if key not in _SCORE:
        _SCORE[key] = pd.read_csv(path, float_precision="round_trip")
    return _SCORE[key]


def pooled_line(run, col, basis="all"):
    sp = score_csv(run, "score_pooled.csv")
    r = sp[(sp["line"] == "pooled") & (sp["column"] == col) & (sp["rows_basis"] == basis)]
    assert len(r) == 1, (run, col, len(r))
    return r.iloc[0]


def by_group_map(run, col, metric="mae"):
    sg = score_csv(run, "score_by_group.csv")
    r = sg[(sg["line"] == "key") & (sg["column"] == col) & (sg["rows_basis"] == "all")]
    assert (r["rows_missing"] == 0).all()
    keys = r["group"].astype(str).tolist()
    assert len(set(keys)) == len(keys)
    return {k: float(v) for k, v in zip(keys, r[metric].tolist())}


_RS = {}


def run_scores(run):
    """Every R34 metric needed, pooled and per group, recomputed from the saved rows (engine replicas)."""
    if run in _RS:
        return _RS[run]
    df, scored = preds(run)
    V = verdict(run)
    tol = float(V["hit_tolerance"])
    floor = V.get("measurement_error_floor")
    y = df["y"].to_numpy(np.float64)
    lab = np.isfinite(y)
    normal = df["normal"].to_numpy(np.float64)
    normal_ok = bool(np.isfinite(normal[lab]).any())
    units = df["unit"].to_numpy()
    gidx = df.groupby("group", sort=True).indices
    pooled, per_group = {}, {}
    for c in scored:
        v = df[c].to_numpy(np.float64)
        m = lab & np.isfinite(v)
        rows = np.flatnonzero(m)
        yy, pp = y[rows], v[rows]
        pooled[c] = {"n": int(rows.size), "n_units": int(np.unique(units[rows]).size), "mae": mae(yy, pp),
                     "anom_r2": anomaly_r2(yy, pp, normal[rows]) if normal_ok else float("nan"),
                     "corr2": corr2(yy, pp), "hit": hit_rate(yy, pp, tol),
                     "hit_floor": hit_rate(yy, pp, float(floor)) if floor is not None else float("nan"),
                     "mean_pred": float(np.mean(pp))}
        pg = {}
        for g in sorted(gidx):
            idx = np.asarray(gidx[g])
            rr = idx[m[idx]]
            pg[str(g)] = mae(y[rr], v[rr])
        per_group[c] = pg
    lab_rows = np.flatnonzero(lab)
    pop = {"saved_rows": int(len(df)), "labelled_rows": int(lab.sum()),
           "units": int(np.unique(units[lab_rows]).size),
           "groups": int(np.unique(df["group"].to_numpy()[lab_rows].astype(str)).size),
           "years": sorted(int(x) for x in np.unique(df["year"].to_numpy()[lab_rows])),
           "leads": sorted(int(x) for x in np.unique(df["lead"].to_numpy()))}
    _RS[run] = {"pooled": pooled, "per_group": per_group, "pop": pop, "scored": scored, "tol": tol,
                "floor": floor}
    return _RS[run]


def pop_str(run, extra=""):
    p = run_scores(run)["pop"]
    return ("%s lead %s: %d labelled rows of %d saved, %d units, %d groups, years %d-%d%s"
            % (run, "/".join(map(str, p["leads"])), p["labelled_rows"], p["saved_rows"], p["units"], p["groups"],
               p["years"][0], p["years"][-1], extra))


def check_pooled(it, run, cols, metrics=("mae",)):
    rs = run_scores(run)
    for c in cols:
        line = pooled_line(run, c)
        it.close("%s %s n" % (run, c), rs["pooled"][c]["n"], line["n"], 0.0)
        for m in metrics:
            it.close("%s %s pooled %s vs score_pooled.csv" % (run, c, m), rs["pooled"][c][m], float(line[m]))


def check_groups(it, run, cols):
    rs = run_scores(run)
    worst = 0.0
    bad = 0
    for c in cols:
        sg = by_group_map(run, c)
        mine = rs["per_group"][c]
        if set(sg) != set(mine):
            it.true("%s %s group set equals score_by_group.csv" % (run, c), False,
                    "%d vs %d groups" % (len(sg), len(mine)))
            continue
        for g in sg:
            a, b = mine[g], sg[g]
            r = abs(a - b) / abs(b) if b != 0 else abs(a - b)
            worst = max(worst, r)
            if not math.isclose(a, b, rel_tol=RTOL, abs_tol=0.0):
                bad += 1
    it.true("%s per-group MAE of %d columns recomputed == score_by_group.csv (rtol 1e-12)" % (run, len(cols)),
            bad == 0, {"mismatches": bad, "max_rel_err": worst})


# ============================================================================== M34
def item_M34():
    it = Item("M34", "Climatology identity: identity-link trees-off (TO) vs guess-normal (GN) on the saved test rows",
              "Lead 0 labelled rows: pm25 91,428 / 1,905 units / 127 groups / 2020-2023; ndvi 94,527 / 1,983 / 133; "
              "fire 94,702 / 2,000 / 40 / 2019-2022; defo 369,096 / 92,274 / 42 / 2020-2023. maxdev over every saved "
              "row (pm25 91,440, ndvi 95,184, fire 96,000, defo 369,096). Coral excluded (neighbour: no normal).",
              "MAE_TO = mean|y-TO|, MAE_GN = mean|y-GN| over labelled rows; diff = MAE_TO - MAE_GN; rel = diff/MAE_GN; "
              "maxdev = max over all saved rows |TO-GN|; GN == clip(normal, legal_min, legal_max) exactly; anomaly R2 "
              "of TO = 1 - sum((y-n)-(TO-n))^2 / sum((y-n)^2); tolerance = verdict.json tolerances.tolerance.identity "
              "(O4: max(k*s_identity, floor)).")
    out = {}
    rows_print = []
    for run in ["pm25", "ndvi", "fire", "defo"]:
        df, _ = preds(run)
        rs = run_scores(run)
        V = verdict(run)
        y = df["y"].to_numpy(np.float64)
        lab = np.isfinite(y)
        TO = df["arm__identity_trees_off_unweighted"].to_numpy(np.float64)
        GN = df["base__guess_normal"].to_numpy(np.float64)
        nrm = df["normal"].to_numpy(np.float64)
        lo = df["legal_min"].to_numpy(np.float64)
        hi = df["legal_max"].to_numpy(np.float64)
        clip = np.clip(nrm, lo, hi)
        exact = bool(np.array_equal(GN, clip))
        n_clip_active = int(np.sum(clip != nrm))
        it.true("%s GN == clip(normal, legal_min, legal_max) exactly on all %d saved rows" % (run, len(df)), exact)
        mto, mgn = mae(y[lab], TO[lab]), mae(y[lab], GN[lab])
        diff = mto - mgn
        dev = np.abs(TO - GN)
        imax = int(np.argmax(dev))
        maxdev = float(dev[imax])
        maxdev_lab = float(dev[lab].max())
        ar2_to = anomaly_r2(y[lab], TO[lab], nrm[lab])
        ar2_gn = anomaly_r2(y[lab], GN[lab], nrm[lab])
        tl = V["tolerances"]
        tol = float(tl["tolerance"]["identity"])
        rebuilt = max(float(tl["k"]) * float(tl["s"]["identity"]), float(tl["floor"]))
        it.close("%s identity tolerance == max(k*s_identity, floor)" % run, rebuilt, tol)
        it.close("%s MAE_TO" % run, mto, pooled_line(run, "arm__identity_trees_off_unweighted")["mae"])
        it.close("%s MAE_GN" % run, mgn, pooled_line(run, "base__guess_normal")["mae"])
        it.close("%s anomaly R2 TO" % run, ar2_to, pooled_line(run, "arm__identity_trees_off_unweighted")["anom_r2"])
        it.close("%s anomaly R2 GN" % run, ar2_gn, pooled_line(run, "base__guess_normal")["anom_r2"])
        it.close("%s verdict.json beside arithmetic_normal_mae == MAE_TO" % run, mto,
                 V["beside"]["arithmetic_normal_mae"])
        it.close("%s verdict.json beside base__guess_normal_mae@all == MAE_GN" % run, mgn,
                 V["beside"]["base__guess_normal_mae@all"])
        if run == "ndvi":
            h = pd.read_csv(use(HEADLINE_CSV["ndvi"]), float_precision="round_trip")
            r = h[(h["lead"] == 0) & (h["rows"] == "all") & (h["line"] == "pooled")].iloc[0]
            it.true("ndvi headline lead-0 reference is the identity trees-off",
                    r["reference"] == "arm__identity_trees_off_unweighted", r["reference"])
            it.close("ndvi headline mae_reference == MAE_TO", mto, r["mae_reference"])
            it.close("ndvi headline anom_r2_reference == anomaly R2 TO", ar2_to, r["anom_r2_reference"])
            it.close("ndvi headline mae_guess_normal == MAE_GN", mgn, r["mae_guess_normal"])
        p = rs["pop"]
        out[run] = {"MAE_TO": mto, "MAE_GN": mgn, "MAE_TO_6sig": fmt(mto), "MAE_GN_6sig": fmt(mgn),
                    "diff_exact": repr(diff), "rel_diff": diff / mgn, "maxdev_all_saved_rows": maxdev,
                    "maxdev_row_index": imax, "maxdev_labelled_rows": maxdev_lab,
                    "identity_tolerance": tol, "tolerance_k": float(tl["k"]), "tolerance_s_identity":
                        float(tl["s"]["identity"]), "tolerance_floor": float(tl["floor"]),
                    "maxdev_within_tolerance": bool(maxdev <= tol), "maxdev_over_tolerance": maxdev / tol,
                    "anomaly_r2_TO": ar2_to, "anomaly_r2_GN": ar2_gn, "GN_equals_clip_normal_exactly": exact,
                    "rows_where_clip_changes_normal": n_clip_active,
                    "labelled_rows": p["labelled_rows"], "saved_rows": p["saved_rows"], "units": p["units"],
                    "groups": p["groups"], "years": p["years"]}
        rows_print.append([run, p["labelled_rows"], p["saved_rows"], p["units"], p["groups"], fmt(mto), fmt(mgn),
                           repr(diff), "%.3g" % (diff / mgn), "%.3g" % maxdev, "%.3g" % tol,
                           "yes" if maxdev <= tol else "NO", "%.3g" % ar2_to, exact])
    print(pd.DataFrame(rows_print, columns=["run", "lab_rows", "saved", "units", "groups", "MAE_TO", "MAE_GN",
                                            "diff (exact)", "rel", "maxdev", "tol_id", "within",
                                            "anomR2_TO", "GN==clip"]).to_string(index=False))
    it.d["values"] = out
    it.note("max |rel diff| over the four runs = %.3g (wording: 'equal within 1e-8 relative' holds iff < 1e-8)"
            % max(abs(v["rel_diff"]) for v in out.values()))
    return it.summary()


# ============================================================================== R12
def item_R12():
    it = Item("R12", "Fire nowcast pooled-MAE ordering (log trees-off, predict-zero, log arms, adopted, arcsine TO, "
                     "identity normal) + report-only per-region contrasts of the adopted arm",
              "Fire, lead 0, labelled rows 94,702 (1,298 unlabelled saved rows excluded), 2,000 units, 40 groups, "
              "2019-2022; contrasts over the 40 groups.",
              "Pooled MAE over labelled rows, sorted ascending; d_g = MAE_ref(g) - MAE_adopted(g) (positive = adopted "
              "better), ref = arm__log_c_trees_off_unweighted and ref = base__predict_zero; group jackknife z=1.96; "
              "tag D74 with the fire band.")
    run = "fire"
    rs = run_scores(run)
    V = verdict(run)
    band = float(V["band"])
    adopted = "arm__" + V["adopted"]
    it.true("fire adopted column is arm__arcsine_corrector_gls", adopted == "arm__arcsine_corrector_gls", adopted)
    cols = ["arm__log_c_trees_off_unweighted", "base__predict_zero", "arm__log_c_plain_unweighted",
            "arm__log_c_plain_gls", "arm__log_c_corrector_unweighted", "arm__log_c_corrector_gls",
            "arm__arcsine_corrector_gls", "arm__arcsine_trees_off_unweighted", "arm__identity_trees_off_unweighted",
            "base__guess_normal"]
    check_pooled(it, run, cols)
    check_groups(it, run, cols)
    order = sorted(cols, key=lambda c: rs["pooled"][c]["mae"])
    print("Pooled MAE, ascending (n = %d labelled rows):" % rs["pooled"][adopted]["n"])
    for i, c in enumerate(order, 1):
        print("  %2d. %-42s %.10g%s" % (i, c, rs["pooled"][c]["mae"], "   <- adopted" if c == adopted else ""))
    vals = {"band": band, "ordering": [{"rank": i + 1, "column": c, "pooled_mae": rs["pooled"][c]["mae"]}
                                       for i, c in enumerate(order)], "contrasts_report_only": {}}
    print("Report-only per-region contrasts (d_g = MAE_ref - MAE_adopted; + = adopted better), band %.10g:" % band)
    for ref in ["arm__log_c_trees_off_unweighted", "base__predict_zero"]:
        groups, dv = paired(by_group_map(run, ref), by_group_map(run, adopted))
        rec = contrast_record(dv, band, groups)
        rec["pooled_contrast"] = rs["pooled"][ref]["mae"] - rs["pooled"][adopted]["mae"]
        rec["groups_adopted_better"] = rec.pop("groups_positive")
        vals["contrasts_report_only"][ref] = rec
        print("  vs %-34s mean %+.4g se %.4g CI [%+.4g, %+.4g] G=%d, adopted better in %d/%d, pooled %+.4g -> %s"
              % (ref, rec["mean"], rec["se"], rec["low"], rec["high"], rec["n_groups"], rec["groups_adopted_better"],
                 rec["groups"], rec["pooled_contrast"], rec["tag"].upper()))
    # final part, re-read (not recomputed): adoption.json surface MAEs; jackknife.csv tags of the log arms
    A = adoption(run)
    sm = A["surface_mae"]
    grid = A["decision"]["grid"]
    surf = {"log_c_trees_off_unweighted": sm["log_c_trees_off_unweighted"]}
    eligible = {"%s_%s_%s" % (e["link"], e["tool"], e["weighting"]) for e in A["eligible"]}
    print("adoption.json decision-surface MAEs (re-read): log trees-off %.10g" % sm["log_c_trees_off_unweighted"])
    for arm in ["log_c_plain_unweighted", "log_c_plain_gls", "log_c_corrector_unweighted", "log_c_corrector_gls",
                "arcsine_corrector_gls", "arcsine_trees_off_unweighted"]:
        if arm.endswith("trees_off_unweighted"):
            surf[arm] = {"surface_mae": sm[arm]}
            print("  %-30s surface %.10g" % (arm, sm[arm]))
            continue
        best_v, best_pt = None, None
        for pt in grid:              # penalty_search: first grid point on ties (strict <)
            key = "%s@level=%r,ratio=%r" % (arm, float(pt["level"]), None if pt["ratio"] is None else float(pt["ratio"]))
            v = sm[key]
            if best_v is None or v < best_v:
                best_v, best_pt = v, pt
        link = arm.split("_")[0] if not arm.startswith("log_c") else "log_c"
        n2 = best_v < sm["%s_trees_off_unweighted" % link]
        surf[arm] = {"surface_pick_mae": best_v, "pick_point": best_pt, "own_trees_off_surface_mae":
                     sm["%s_trees_off_unweighted" % link], "n2_eligible_recomputed": bool(n2),
                     "eligible_in_adoption_json": arm in eligible}
        it.true("fire %s N2 eligibility recomputed from surface == adoption.json eligible" % arm,
                bool(n2) == (arm in eligible))
        print("  %-30s pick %.10g at %s; own TO %.10g; N2 eligible %s (adoption.json: %s)"
              % (arm, best_v, best_pt, sm["%s_trees_off_unweighted" % link], n2, arm in eligible))
    vals["adoption_surface_reread"] = surf
    jk = pd.read_csv(use(RUN[run] + "/jackknife.csv"), float_precision="round_trip")
    sel = jk[(jk["kind"] == "band_pair") & (jk["arm"].str.startswith("arm__log_c_"))]
    rer = []
    for _, r in sel.iterrows():
        groups, dv = paired(by_group_map(run, r["reference"]), by_group_map(run, r["arm"]))
        tg, j = contrast_tag(dv, band)
        for k in ("mean", "se", "low", "high"):
            it.close("fire jackknife.csv %s vs %s %s re-derived" % (r["arm"], r["reference"], k), j[k], r[k])
        it.true("fire jackknife.csv %s vs %s tag re-derived" % (r["arm"], r["reference"]), tg == r["tag"],
                (tg, r["tag"]))
        rer.append({"reference": r["reference"], "arm": r["arm"], "mean": float(r["mean"]), "se": float(r["se"]),
                    "low": float(r["low"]), "high": float(r["high"]), "tag": r["tag"], "rederived_tag": tg})
        print("  jackknife.csv %-34s vs %-46s %+.4g [%+.4g, %+.4g] %s"
              % (r["arm"], r["reference"], r["mean"], r["low"], r["high"], r["tag"].upper()))
    vals["jackknife_csv_log_arm_rows"] = rer
    it.d["values"] = vals
    return it.summary()


# ============================================================================== R13
ARM_RE = re.compile(r"^(arm|placebo)__(identity|log_c|arcsine)_(plain|corrector|placebo_corrector|trees_off)_"
                    r"(unweighted|gls)$")


def parse_cols(scored):
    out = {}
    for c in scored:
        m = ARM_RE.match(c)
        if m:
            out[c] = {"prefix": m.group(1), "link": m.group(2), "tool": m.group(3), "weighting": m.group(4)}
    return out


def item_R13():
    it = Item("R13", "Corrector vs placebo vs plain pooled MAE per link x weighting, and re-derived placebo band pairs",
              "Lead 0 labelled rows: pm25 91,428 / 127 groups; ndvi 94,527 / 133; fire 94,702 / 40; defo 369,096 / "
              "42; coral 2,312 / 37.",
              "Pooled MAE per column over labelled rows; corrector - placebo and corrector - plain; for every placebo__ "
              "band_pair row of jackknife.csv: d_g = MAE_placebo(g) - MAE_corrector(g) from score_by_group.csv, group "
              "jackknife 1.96, tag D74 with the run band, compared with jackknife.csv (rtol 1e-12).")
    vals = {}
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        rs = run_scores(run)
        V = verdict(run)
        band = float(V["band"])
        A = adoption(run)
        ad = A["adopted"]
        pc = parse_cols(rs["scored"])
        triples = sorted({(v["link"], v["weighting"]) for v in pc.values() if v["tool"] == "corrector"})
        rows = []
        cols_used = []
        for link, w in triples:
            c, p, pl = ("arm__%s_corrector_%s" % (link, w), "placebo__%s_placebo_corrector_%s" % (link, w),
                        "arm__%s_plain_%s" % (link, w))
            cols_used += [c, p, pl]
            mc, mp, mpl = rs["pooled"][c]["mae"], rs["pooled"][p]["mae"], rs["pooled"][pl]["mae"]
            rows.append({"link": link, "weighting": w, "adopted_triple": (link == ad["link"] and w == ad["weighting"]),
                         "corrector": mc, "placebo": mp, "plain": mpl, "corrector_minus_placebo": mc - mp,
                         "corrector_minus_plain": mc - mpl})
        check_pooled(it, run, cols_used)
        check_groups(it, run, cols_used)
        jk = pd.read_csv(use(RUN[run] + "/jackknife.csv"), float_precision="round_trip")
        pl_rows = jk[(jk["kind"] == "band_pair") & (jk["reference"].str.startswith("placebo__"))]
        rer = []
        for _, r in pl_rows.iterrows():
            groups, dv = paired(by_group_map(run, r["reference"]), by_group_map(run, r["arm"]))
            tg, j = contrast_tag(dv, band)
            for k in ("mean", "se", "low", "high"):
                it.close("%s %s vs %s %s" % (run, r["arm"], r["reference"], k), j[k], r[k])
            it.close("%s %s vs %s n_groups" % (run, r["arm"], r["reference"]), j["n_groups"], r["n_groups"], 0.0)
            it.true("%s %s vs %s tag" % (run, r["arm"], r["reference"]), tg == r["tag"], (tg, r["tag"]))
            rer.append({"placebo": r["reference"], "corrector": r["arm"], "mean": j["mean"], "se": j["se"],
                        "low": j["low"], "high": j["high"], "n_groups": j["n_groups"], "tag": tg,
                        "jackknife_csv_tag": r["tag"]})
        vals[run] = {"adopted": "%s_%s_%s" % (ad["link"], ad["tool"], ad["weighting"]), "band": band,
                     "n_labelled_rows": rs["pop"]["labelled_rows"], "n_groups": rs["pop"]["groups"],
                     "triples": rows, "placebo_band_pairs_rederived": rer}
        print("%s (adopted %s_%s_%s; band %.6g; %d labelled rows, %d groups)" % (run, ad["link"], ad["tool"],
              ad["weighting"], band, rs["pop"]["labelled_rows"], rs["pop"]["groups"]))
        print(pd.DataFrame([{"triple": "%s/%s%s" % (r["link"], r["weighting"], "  *ADOPTED*" if r["adopted_triple"]
                                                       else ""), "corrector": "%.10g" % r["corrector"],
                             "placebo": "%.10g" % r["placebo"], "plain": "%.10g" % r["plain"],
                             "corr-plac": "%+.4g" % r["corrector_minus_placebo"],
                             "corr-plain": "%+.4g" % r["corrector_minus_plain"]} for r in rows]).to_string(index=False))
        for r in rer:
            print("   placebo pair %-46s d=plac-corr %+.4g se %.4g [%+.4g, %+.4g] G=%d %s (csv %s)"
                  % (r["corrector"], r["mean"], r["se"], r["low"], r["high"], r["n_groups"], r["tag"].upper(),
                     r["jackknife_csv_tag"]))
    it.d["values"] = vals
    return it.summary()


# ============================================================================== R14
def item_R14():
    it = Item("R14", "Implied absolute penalties of each run's adopted grid point",
              "One adopted point per run at lead 0 (adoption.json penalty); no rows.",
              "per_unit/neighbour: a_tree = centre[0] * level, a_ctx = a_tree * ratio (0.0 when ratio is null); "
              "region: lambda = centre[0] * level; centre from derived.json R14.value.centre.")
    vals = {}
    rows = []
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        A = adoption(run)
        D = read_json(RUN[run] + "/derived.json")["R14"]
        kind, centre, grid = D["value"]["kind"], D["value"]["centre"], D["value"]["grid"]
        pt = A["penalty"]
        it.true("%s penalty == best_tree_penalty" % run, pt == A["best_tree_penalty"], (pt, A["best_tree_penalty"]))
        it.true("%s not declined" % run, A["declined"] is False)
        it.true("%s adopted point is in derived R14 grid" % run, pt in grid)
        level, ratio = float(pt["level"]), pt["ratio"]
        consts = D["inputs"]["constants"]
        if kind in ("per_unit", "neighbour"):
            ck = "C12.per_unit_trees_centre" if kind == "per_unit" else "C12.neighbour_trees_centre"
            it.close("%s derived centre[0] == %s" % (run, ck), centre[0], consts[ck])
            a_tree = float(centre[0]) * level
            a_ctx = 0.0 if ratio is None else a_tree * float(ratio)
            v = {"kind": kind, "centre": centre, "level": level, "ratio": ratio, "a_tree": a_tree, "a_ctx": a_ctx,
                 "context_centre_unused": centre[1] if len(centre) > 1 else None}
            rows.append([run, kind, centre, level, ratio, a_tree, a_ctx, ""])
        elif kind == "region":
            it.close("%s derived centre[0] == C12.region_lambda_centre" % run, centre[0],
                     consts["C12.region_lambda_centre"])
            lam = float(centre[0]) * level
            v = {"kind": kind, "centre": centre, "level": level, "ratio": ratio, "lambda": lam}
            rows.append([run, kind, centre, level, ratio, "", "", lam])
        else:
            raise SystemExit("unknown R14 kind %r" % kind)
        vals[run] = v
    print(pd.DataFrame(rows, columns=["run", "kind", "centre", "level", "ratio", "a_tree", "a_ctx", "lambda"])
          .to_string(index=False))
    it.note("The M47 pinning of this point at every kept lead is not re-checked here (adoption_lead_*.json are not "
            "in the spec's input list).")
    it.d["values"] = vals
    return it.summary()


# ============================================================================== R15
def item_R15():
    it = Item("R15", "AK4(a) cheap ablation table: every saved column at the nowcast, adopted regret, report-only "
                     "per-region contrasts and factor summaries (NOT a test of the per-unit axis, M56)",
              "Lead 0 labelled rows: pm25 91,428 / 127 groups (17 cols); ndvi 94,527 / 133 (10); fire 94,702 / 40 "
              "(24); defo 369,096 / 42 (15); coral 2,312 / 37 (23).",
              "Per column pooled MAE, anomaly R2 (saved normal; NaN on coral), corr2, hit at verdict hit_tolerance, "
              "hit_floor at measurement_error_floor; selectable = arm__ without 'trees_off'; best = lowest selectable "
              "MAE; regret_abs = MAE(adopted)-MAE(best), regret_rel = regret_abs/MAE(best); report-only d_g = MAE_a(g) "
              "- MAE_adopted(g), group jackknife 1.96, D74 tag with the run band; weighting effect = MAE(unw)-MAE(gls); "
              "tool effect = MAE(plain)-MAE(corrector); link effect = best selectable arm per link.")
    vals = {}
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        rs = run_scores(run)
        V = verdict(run)
        A = adoption(run)
        band = float(V["band"])
        adopted = "arm__" + V["adopted"]
        ad = A["adopted"]
        it.true("%s verdict.json adopted == adoption.json adopted" % run,
                V["adopted"] == "%s_%s_%s" % (ad["link"], ad["tool"], ad["weighting"]))
        eligible = {"arm__%s_%s_%s" % (e["link"], e["tool"], e["weighting"]) for e in A["eligible"]}
        cols = rs["scored"]
        kinds = {c: c.split("__")[0] for c in cols}
        n_arm = sum(1 for c in cols if kinds[c] == "arm")
        n_pl = sum(1 for c in cols if kinds[c] == "placebo")
        n_b = sum(1 for c in cols if kinds[c] == "base")
        selectable = [c for c in cols if kinds[c] == "arm" and "trees_off" not in c]
        metrics = ["mae", "anom_r2", "corr2", "hit"] + (["hit_floor"] if rs["floor"] is not None else [])
        check_pooled(it, run, cols, metrics)
        check_groups(it, run, cols)
        best = min(selectable, key=lambda c: rs["pooled"][c]["mae"])
        lowest = min(cols, key=lambda c: rs["pooled"][c]["mae"])
        reg = rs["pooled"][adopted]["mae"] - rs["pooled"][best]["mae"]
        table = []
        for c in sorted(cols, key=lambda c: rs["pooled"][c]["mae"]):
            p = rs["pooled"][c]
            table.append({"column": c, "kind": kinds[c], "selectable": c in selectable, "eligible": c in eligible,
                          "adopted": c == adopted, "n": p["n"], "mae": p["mae"], "anom_r2": p["anom_r2"],
                          "corr2": p["corr2"], "hit": p["hit"], "hit_floor": p["hit_floor"]})
        print("%s: %d columns (%d arms, %d placebos, %d baselines), %d selectable; hit tol %.6g%s; band %.6g"
              % (run, len(cols), n_arm, n_pl, n_b, len(selectable), rs["tol"],
                 "" if rs["floor"] is None else ", floor %.6g" % rs["floor"], band))
        print(pd.DataFrame([{"column": t["column"] + ("  *ADOPTED*" if t["adopted"] else "") +
                             ("  [eligible]" if t["eligible"] else ""), "MAE": "%.10g" % t["mae"],
                             "anomR2": fmt(t["anom_r2"], 5), "corr2": fmt(t["corr2"], 5), "hit": fmt(t["hit"], 5),
                             "hit_floor": fmt(t["hit_floor"], 5)} for t in table]).to_string(index=False))
        print("   best selectable %s %.10g; adopted %.10g; regret %.6g (%.4g%%); lowest column overall %s %.10g"
              % (best, rs["pooled"][best]["mae"], rs["pooled"][adopted]["mae"], reg,
                 100 * reg / rs["pooled"][best]["mae"], lowest, rs["pooled"][lowest]["mae"]))
        contrasts = []
        amap = by_group_map(run, adopted)
        for a in selectable:
            if a == adopted:
                continue
            groups, dv = paired(by_group_map(run, a), amap)
            rec = contrast_record(dv, band, groups)
            rec["arm"] = a
            rec["groups_adopted_better"] = rec.pop("groups_positive")
            rec["pooled_contrast"] = rs["pooled"][a]["mae"] - rs["pooled"][adopted]["mae"]
            contrasts.append(rec)
        print("   report-only per-region contrasts vs the adopted arm (d_g = MAE_arm - MAE_adopted; + = adopted better):")
        for r in contrasts:
            print("     %-40s %+.4g se %.4g [%+.4g, %+.4g] G=%d adopted better %d/%d -> %s"
                  % (r["arm"], r["mean"], r["se"], r["low"], r["high"], r["n_groups"], r["groups_adopted_better"],
                     r["groups"], r["tag"].upper()))
        pc = parse_cols(selectable)
        mae_of = {(v["link"], v["tool"], v["weighting"]): rs["pooled"][c]["mae"] for c, v in pc.items()}
        w_eff = {"%s_%s" % (l, t): mae_of[(l, t, "unweighted")] - mae_of[(l, t, "gls")]
                 for (l, t, w) in mae_of if w == "unweighted" and (l, t, "gls") in mae_of}
        t_eff = {"%s_%s" % (l, w): mae_of[(l, "plain", w)] - mae_of[(l, "corrector", w)]
                 for (l, t, w) in mae_of if t == "plain" and (l, "corrector", w) in mae_of}
        links = sorted({v["link"] for v in pc.values()})
        l_eff = {}
        for l in links:
            cand = [c for c, v in pc.items() if v["link"] == l]
            b = min(cand, key=lambda c: rs["pooled"][c]["mae"])
            to = "arm__%s_trees_off_unweighted" % l
            l_eff[l] = {"best_arm": b, "best_mae": rs["pooled"][b]["mae"],
                        "trees_off_mae": rs["pooled"][to]["mae"] if to in rs["pooled"] else None}
        print("   weighting effect MAE(unw)-MAE(gls): %s" % ({k: "%+.4g" % v for k, v in w_eff.items()} or "n/a (no GLS arms)"))
        print("   tool effect MAE(plain)-MAE(corrector): %s" % {k: "%+.4g" % v for k, v in t_eff.items()})
        print("   link effect (best selectable arm per link): %s"
              % {l: "%s %.6g (TO %s)" % (v["best_arm"], v["best_mae"], fmt(v["trees_off_mae"])) for l, v in l_eff.items()})
        vals[run] = {"n_columns": len(cols), "n_arms": n_arm, "n_placebos": n_pl, "n_baselines": n_b,
                     "n_selectable": len(selectable), "n_labelled_rows": rs["pop"]["labelled_rows"],
                     "n_groups": rs["pop"]["groups"], "hit_tolerance": rs["tol"], "hit_floor": rs["floor"],
                     "band": band, "adopted": adopted, "eligible": sorted(eligible), "best_selectable": best,
                     "best_selectable_mae": rs["pooled"][best]["mae"], "adopted_mae": rs["pooled"][adopted]["mae"],
                     "regret_abs": reg, "regret_rel": reg / rs["pooled"][best]["mae"],
                     "lowest_column_overall": lowest, "lowest_column_mae": rs["pooled"][lowest]["mae"],
                     "table": table, "contrasts_report_only_post_hoc": contrasts,
                     "weighting_effect_unw_minus_gls": w_eff, "tool_effect_plain_minus_corrector": t_eff,
                     "link_effect_best_per_link": l_eff}
    it.d["values"] = vals
    return it.summary()


# ============================================================================== P29
VERDICT_WORD = {"BEATS": "helps", "LOSES": "hurts", "CANNOT TELL": "cannot_tell", "EQUIVALENT":
                "does_not_help_equivalent", "IDENTICAL": "identical"}


def scale_close(a, b, scale, rtol=1e-9):
    return abs(a - b) <= rtol * max(abs(scale), 1e-300)


def item_P29():
    it = Item("P29", "Sensitivity of every deciding verdict to the interval method (t(G-1) vs z=1.96), p-values, "
                     "re-applied tag, Holm over the five nowcasts, band share (report-only, post hoc)",
              "79 deciding verdict rows: 14 own (lead 0 'all' rows from verdict.json; leads > 0 'common' rows from "
              "ladder.json; 6 declined) + 65 RIVALS_TABLE decides rows (53 common + 12 human; 12 IDENTICAL). G = the "
              "row's n_groups. Holm: the 5 lead-0 own verdicts.",
              "SE and mean from the row's source; check SE == (high-low)/(2*1.96) and CI == mean +- 1.96 SE (rtol 1e-9 "
              "of max(|mean|, 1.96 SE)); t CI = mean +- t_{0.975,G-1} SE; p_z = 2*(1-Phi(|mean/SE|)), p_t = "
              "2*(1-T_{G-1}(|mean/SE|)) (computed with the survival functions); tag_t = D74 with the t CI and the "
              "row's band (declined/identical keep their tag); Holm step-down alpha 0.05, adjusted p_(i) = "
              "max_{j<=i} min(1,(m-j+1) p_(j)), m = 5; band share = 100*band/mae_reference (lead-0 'all' pooled).")
    rows = []
    for prob in ["pm25", "ndvi", "fire", "defo", "coral"]:
        v = pd.read_csv(use(VERDICTS_CSV[prob]), float_precision="round_trip")
        sel = v[((v["lead"] == 0) & (v["rows"] == "all")) | ((v["lead"] > 0) & (v["rows"] == "common"))]
        it.true("%s own verdict rows = %d leads" % (prob, len(LEADS[prob])), len(sel) == len(LEADS[prob]))
        for _, r in sel.iterrows():
            it.true("%s lead %d own recomputed_equals_recorded" % (prob, r["lead"]), bool(r["recomputed_equals_recorded"]))
            rows.append({"problem": prob, "lead": int(r["lead"]), "source": "own (%s)" % r["source"],
                         "name": "ours vs %s" % r["reference"], "mean": float(r["contrast_mean"]),
                         "se": float(r["contrast_se"]), "low": float(r["contrast_low"]),
                         "high": float(r["contrast_high"]), "G": int(r["n_groups"]), "band": float(r["band"]),
                         "tag": r["tag"], "rt_key": None})
    boards = []
    for prob in ["pm25", "ndvi", "fire", "defo", "coral"]:
        for L in LEADS[prob]:
            b = pd.read_csv(use(RIV[prob] + "/board_lead_%d.csv" % L), float_precision="round_trip")
            for _, r in b[b["decides"] == True].iterrows():  # noqa: E712
                boards.append({"problem": prob, "lead": int(r["lead"]), "source": "common board",
                               "name": "ours vs %s" % r["learner"], "rival": r["learner"], "rival_type": "common",
                               "mean": float(r["d_mean"]), "se": float(r["d_se"]), "low": float(r["d_low"]),
                               "high": float(r["d_high"]), "G": int(r["n_groups"]), "band": float(r["band"]),
                               "tag": r["tag"]})
            if prob in HUM:
                h = pd.read_csv(use(HUM[prob] + "/human_board_lead_%d.csv" % L), float_precision="round_trip")
                for _, r in h[h["decides"] == True].iterrows():  # noqa: E712
                    boards.append({"problem": prob, "lead": int(r["lead"]), "source": "human board",
                                   "name": "ours vs %s" % r["rival"], "rival": r["rival"], "rival_type": "human",
                                   "mean": float(r["d_mean"]), "se": float(r["d_se"]), "low": float(r["d_low"]),
                                   "high": float(r["d_high"]), "G": int(r["n_groups"]), "band": float(r["band"]),
                                   "tag": r["tag"]})
    rt = pd.read_csv(use(RIVALS_TABLE), float_precision="round_trip")
    rtd = rt[rt["decides"] == True]  # noqa: E712
    it.true("RIVALS_TABLE decides rows == 65", len(rtd) == 65, len(rtd))
    used = set()
    for _, r in rtd.iterrows():
        m = [i for i, b in enumerate(boards) if b["problem"] == r["problem"] and b["lead"] == int(r["lead"])
             and b["rival"] == r["rival"] and b["rival_type"] == r["rival_type"]]
        if not it.true("RIVALS_TABLE row %s/%s/%s matches exactly one board row" % (r["problem"], r["lead"], r["rival"]),
                       len(m) == 1, len(m)):
            continue
        i = m[0]
        used.add(i)
        b = boards[i]
        word = str(r["verdict"]).split(" (")[0]
        it.true("RIVALS_TABLE verdict word matches board tag %s/%s/%s" % (r["problem"], r["lead"], r["rival"]),
                VERDICT_WORD.get(word) == b["tag"], (word, b["tag"]))
        sc = max(abs(b["mean"]), Z * b["se"])
        for k, col in (("mean", "d_mean"), ("low", "d_low"), ("high", "d_high")):
            it.true("RIVALS_TABLE %s == board %s/%s/%s" % (col, r["problem"], r["lead"], r["rival"]),
                    scale_close(float(r[col]), b[k], sc) or (sc == 0 and float(r[col]) == b[k]),
                    (float(r[col]), b[k]))
        it.true("RIVALS_TABLE groups == board n_groups %s/%s/%s" % (r["problem"], r["lead"], r["rival"]),
                int(r["groups"]) == b["G"], (r["groups"], b["G"]))
    it.true("every deciding board row is in RIVALS_TABLE", used == set(range(len(boards))),
            "%d used of %d" % (len(used), len(boards)))
    for b in boards:
        rows.append(b)
    it.true("deciding verdict rows == 79", len(rows) == 79, len(rows))
    table = []
    for r in rows:
        mean, se, G, band = r["mean"], r["se"], r["G"], r["band"]
        sc = max(abs(mean), Z * se)
        if sc > 0:
            it.true("%s %s lead %d SE == (high-low)/(2*1.96)" % (r["problem"], r["name"], r["lead"]),
                    scale_close(se, (r["high"] - r["low"]) / (2 * Z), max(se, 1e-300)))
            it.true("%s %s lead %d CI == mean +- 1.96 SE" % (r["problem"], r["name"], r["lead"]),
                    scale_close(r["low"], mean - Z * se, sc) and scale_close(r["high"], mean + Z * se, sc))
        else:
            it.true("%s %s lead %d zero contrast has zero CI" % (r["problem"], r["name"], r["lead"]),
                    r["low"] == 0 and r["high"] == 0)
        tcrit = float(stats.t.ppf(0.975, G - 1))
        keep = r["tag"] in ("declined", "identical")
        if se > 0 and math.isfinite(se):
            zst = abs(mean / se)
            p_z = float(2 * stats.norm.sf(zst))
            p_t = float(2 * stats.t.sf(zst, G - 1))
            lo_t, hi_t = mean - tcrit * se, mean + tcrit * se
        else:
            p_z = p_t = lo_t = hi_t = float("nan")
        tag_z = r["tag"] if keep else tag_rule(r["low"], r["high"], mean, band)
        if not keep:
            it.true("%s %s lead %d D74 re-applied with the z CI == recorded tag" % (r["problem"], r["name"], r["lead"]),
                    tag_z == r["tag"], (tag_z, r["tag"]))
        tag_t = r["tag"] if keep else tag_rule(lo_t, hi_t, mean, band)
        table.append(dict(r, tcrit=tcrit, low_t=lo_t, high_t=hi_t, p_z=p_z, p_t=p_t, tag_t=tag_t,
                          changed=(tag_t != r["tag"])))
    df = pd.DataFrame(table)
    show = df[["problem", "lead", "source", "name", "G", "mean", "se", "low", "high", "tcrit", "low_t", "high_t",
               "p_z", "p_t", "tag", "tag_t", "changed"]].copy()
    with pd.option_context("display.width", 260, "display.max_rows", 200, "display.max_colwidth", 40):
        print(show.to_string(index=False, float_format=lambda x: "%.4g" % x))
    changed = df[df["changed"]]
    # Holm over the 5 lead-0 own verdicts
    own0 = df[(df["lead"] == 0) & (df["source"].str.startswith("own"))].copy()
    it.true("5 lead-0 own verdicts", len(own0) == 5)
    holm = {}
    for pcol in ("p_z", "p_t"):
        o = own0.sort_values(pcol).reset_index(drop=True)
        m = len(o)
        adj, running = [], 0.0
        for j in range(m):
            running = max(running, min(1.0, (m - j) * float(o.loc[j, pcol])))
            adj.append(running)
        o["holm_adj"] = adj
        holm[pcol] = [{"problem": o.loc[j, "problem"], "p": float(o.loc[j, pcol]), "holm_adjusted": adj[j],
                       "survives_0.05": bool(adj[j] <= 0.05)} for j in range(m)]
        print("Holm (%s): %s" % (pcol, "; ".join("%s p=%.5g adj=%.5g %s" % (h["problem"], h["p"], h["holm_adjusted"],
                                                                           "survives" if h["survives_0.05"] else "FAILS")
                                                  for h in holm[pcol])))
    # band share
    share = {}
    for prob in ["pm25", "ndvi", "fire", "defo", "coral"]:
        h = pd.read_csv(use(HEADLINE_CSV[prob]), float_precision="round_trip")
        r = h[(h["lead"] == 0) & (h["rows"] == "all") & (h["line"] == "pooled")]
        it.true("%s one lead-0 all pooled headline row" % prob, len(r) == 1)
        r = r.iloc[0]
        band = float(own0[own0["problem"] == prob]["band"].iloc[0])
        share[prob] = {"band": band, "mae_reference": float(r["mae_reference"]), "reference": r["reference"],
                       "band_share_pct": 100 * band / float(r["mae_reference"])}
    print("Band share of the deciding reference MAE: %s"
          % "; ".join("%s %.4f%% (%s %.6g)" % (k, v["band_share_pct"], v["reference"], v["mae_reference"])
                      for k, v in share.items()))
    jk = pd.read_csv(use(RUN["fire"] + "/jackknife.csv"), float_precision="round_trip")
    bj = jk[jk["kind"] == "blocked_jackknife (report only)"].iloc[0]
    fire_bj = {"mean": float(bj["mean"]), "se": float(bj["se"]), "low": float(bj["low"]), "high": float(bj["high"]),
               "n_blocks": int(bj["n_groups"])}
    print("Fire blocked jackknife (jackknife.csv, report only): mean %.4g se %.4g CI [%.4g, %.4g], %d blocks"
          % (fire_bj["mean"], fire_bj["se"], fire_bj["low"], fire_bj["high"], fire_bj["n_blocks"]))
    print("Rows whose tag changes under t(G-1): %d" % len(changed))
    for _, r in changed.iterrows():
        print("   %s lead %d %s (%s): %s -> %s; t%d=%.4f CI [%.4g, %.4g]; p_z %.5g p_t %.5g"
              % (r["problem"], r["lead"], r["name"], r["source"], r["tag"], r["tag_t"], r["G"] - 1, r["tcrit"],
                 r["low_t"], r["high_t"], r["p_z"], r["p_t"]))
    counts = {"rows": int(len(df)), "own": int(df["source"].str.startswith("own").sum()),
              "own_declined": int(((df["tag"] == "declined") & df["source"].str.startswith("own")).sum()),
              "common": int((df["source"] == "common board").sum()), "human": int((df["source"] == "human board").sum()),
              "identical": int((df["tag"] == "identical").sum()), "changed_under_t": int(len(changed))}
    print("Counts: %s" % counts)
    recs = json.loads(df.to_json(orient="records"))
    it.d["values"] = {"counts": counts, "rows": recs, "changed": json.loads(changed.to_json(orient="records")),
                      "holm": holm, "band_share": share, "fire_blocked_jackknife": fire_bj}
    return it.summary()


# ============================================================================== R3b
def item_R3b():
    it = Item("R3b", "Model (adopted arm) against the best naive baseline at the nowcast, all five problems",
              "Lead 0 labelled rows: pm25 91,428 / 127 groups; ndvi 94,527 / 133; fire 94,702 / 40; defo 369,096 / "
              "42; coral 2,312 / 37.",
              "Candidates: base__guess_normal, base__last5_normal, base__predict_zero and arm__<link>_trees_off_"
              "unweighted per link (coral: base__donor_median, base__predict_zero only); best = lowest pooled MAE over "
              "labelled rows; change% = 100*(MAE_model - MAE_best)/MAE_best; fire also vs predict-zero.")
    vals = {}
    rows = []
    for run in ["pm25", "ndvi", "fire", "defo", "coral"]:
        rs = run_scores(run)
        V = verdict(run)
        model = "arm__" + V["adopted"]
        if run == "coral":
            cand = ["base__donor_median", "base__predict_zero"]
        else:
            cand = ["base__guess_normal", "base__last5_normal", "base__predict_zero"] + \
                   [c for c in rs["scored"] if c.startswith("arm__") and c.endswith("_trees_off_unweighted")]
        for c in cand + [model]:
            it.true("%s %s finite on every labelled row" % (run, c),
                    rs["pooled"][c]["n"] == rs["pop"]["labelled_rows"])
        check_pooled(it, run, cand + [model])
        h = pd.read_csv(use(HEADLINE_CSV[run]), float_precision="round_trip")
        hr = h[(h["lead"] == 0) & (h["rows"] == "all") & (h["line"] == "pooled")].iloc[0]
        it.close("%s headline mae_adopted" % run, rs["pooled"][model]["mae"], hr["mae_adopted"])
        it.close("%s headline mae_predict_zero" % run, rs["pooled"]["base__predict_zero"]["mae"], hr["mae_predict_zero"])
        if run != "coral":
            it.close("%s headline mae_guess_normal" % run, rs["pooled"]["base__guess_normal"]["mae"],
                     hr["mae_guess_normal"])
            it.close("%s headline mae_last5_normal" % run, rs["pooled"]["base__last5_normal"]["mae"],
                     hr["mae_last5_normal"])
        it.close("%s headline mae_reference" % run, rs["pooled"][hr["reference"]]["mae"], hr["mae_reference"])
        best = min(cand, key=lambda c: rs["pooled"][c]["mae"])
        mm, mb = rs["pooled"][model]["mae"], rs["pooled"][best]["mae"]
        v = {"model": model, "model_mae": mm, "candidates": {c: rs["pooled"][c]["mae"] for c in cand},
             "best": best, "best_mae": mb, "change_pct": 100 * (mm - mb) / mb,
             "n_labelled_rows": rs["pop"]["labelled_rows"], "n_groups": rs["pop"]["groups"]}
        if run == "fire":
            pz = rs["pooled"]["base__predict_zero"]["mae"]
            v["change_pct_vs_predict_zero"] = 100 * (mm - pz) / pz
        vals[run] = v
        rows.append([run, model, "%.10g" % mm, best, "%.10g" % mb, "%+.3f%%" % v["change_pct"],
                     "%+.3f%%" % v["change_pct_vs_predict_zero"] if run == "fire" else ""])
        print("%s candidates: %s" % (run, {c: "%.8g" % x for c, x in v["candidates"].items()}))
    print(pd.DataFrame(rows, columns=["run", "model", "MAE_model", "best baseline", "MAE_best", "change%",
                                      "fire vs PZ"]).to_string(index=False))
    it.d["values"] = vals
    return it.summary()


# ============================================================================== rival joins
def join_rivals(run, learners, d):
    out = {}
    for L in learners:
        path = use(RIV[run] + "/lead_0/preds_%s.parquet" % L)
        p = pq.read_table(path, columns=["unit", "group", "time", "lead", "arm__rival_" + L,
                                         "arm__rival_%s_raw" % L, "guard_passed"]).to_pandas()
        p = p.rename(columns={"group": "group_rival"})
        j = d[["unit", "time", "lead", "group"]].merge(p, on=["unit", "time", "lead"], how="left",
                                                       validate="one_to_one")
        assert len(j) == len(d) == len(p), (L, len(j), len(d), len(p))
        assert j["arm__rival_" + L].notna().all() and j["arm__rival_%s_raw" % L].notna().all()
        assert (j["group"].astype(str).to_numpy() == j["group_rival"].astype(str).to_numpy()).all()
        gp = j["guard_passed"].unique().tolist()
        assert len(gp) == 1, gp
        out[L] = {"guarded": j["arm__rival_" + L].to_numpy(np.float64),
                  "raw": j["arm__rival_%s_raw" % L].to_numpy(np.float64), "guard_passed": bool(gp[0])}
    return out


def stratum_table(y, groups, cols, mask, ours_key, band, contrast_keys):
    """Per column: n, groups, mean y, mean pred, MAE; per contrast key: d_g = MAE_key(g) - MAE_ours(g)."""
    rows = np.flatnonzero(mask)
    g = groups[rows]
    ug = sorted(set(g.tolist()))
    res = {"n": int(rows.size), "n_groups": len(ug), "mean_y": float(np.mean(y[rows])), "columns": {},
           "contrasts": {}}
    for k, v in cols.items():
        res["columns"][k] = {"mean_pred": float(np.mean(v[rows])), "mae": mae(y[rows], v[rows])}
    gi = {}
    for i, gg in zip(rows, g):
        gi.setdefault(gg, []).append(i)
    per = {k: {gg: mae(y[np.array(ix)], cols[k][np.array(ix)]) for gg, ix in gi.items()} for k in cols}
    for k in contrast_keys:
        groups_s, dv = paired(per[k], per[ours_key])
        rec = contrast_record(dv, band, groups_s)
        rec["groups_ours_better"] = rec.pop("groups_positive")
        res["contrasts"][k] = rec
    return res


def print_stratum(name, s, ours_key, contrast_keys):
    print("  [%s] n=%d groups=%d mean y=%.6g" % (name, s["n"], s["n_groups"], s["mean_y"]))
    for k, v in s["columns"].items():
        line = "     %-28s MAE %-12s mean pred %-12s" % (k, "%.6g" % v["mae"], "%.6g" % v["mean_pred"])
        if k in s["contrasts"]:
            c = s["contrasts"][k]
            line += " d=%+.5g se %s [%s, %s] G=%d ours better %d/%d %s" % (
                c["mean"], fmt(c["se"], 4), fmt(c["low"], 5), fmt(c["high"], 5), c["n_groups"],
                c["groups_ours_better"], c["groups"], c["tag"].upper())
        print(line)


# ============================================================================== RC12
def item_RC12():
    it = Item("RC12", "Coral nowcast by target magnitude: ours vs the five common rivals (hgb_l1 in focus), "
                      "predict-zero and donor median (outcome-defined strata, report-only, post hoc)",
              "Coral lead 0, all 2,312 test visits (37 groups, 2016-2019); engine bins with the lead-0 positive donor "
              "quartile edges (B0 y=0, B1 (0,q25], B2 (q25,q50], B3 (q50,q75], B4 >q75) and severe y >= 50.",
              "Join on (unit,time,lead) one-to-one; bin = B0 if y==0 else searchsorted([q25,q50,q75], y, 'left'); per "
              "stratum and column n, groups, mean y, mean pred, MAE; d_g = MAE_rival(g) - MAE_ours(g) over the groups "
              "with a row in the stratum, group jackknife 1.96, D74 tag with the coral band (G<3 -> cannot tell).")
    run = "coral"
    d, _ = preds(run)
    V = verdict(run)
    band = float(V["band"])
    ours = "arm__arcsine_corrector_gls"
    it.true("coral adopted == %s" % ours, "arm__" + V["adopted"] == ours)
    y = d["y"].to_numpy(np.float64)
    it.true("coral all 2,312 rows labelled", bool(np.isfinite(y).all()) and len(y) == 2312, len(y))
    groups = d["group"].astype(str).to_numpy()
    learners = ["ridge", "rf", "lgbm", "lgbm_tweedie", "hgb_l1"]
    R = join_rivals(run, learners, d)
    cols = {"ours": d[ours].to_numpy(np.float64)}
    for L in learners:
        cols[L] = R[L]["guarded"]
    cols["predict_zero"] = d["base__predict_zero"].to_numpy(np.float64)
    cols["donor_median"] = d["base__donor_median"].to_numpy(np.float64)
    board = pd.read_csv(use(RIV[run] + "/board_lead_0.csv"), float_precision="round_trip")
    for L in learners:
        for kind, key in (("guarded_vs_headline", "guarded"), ("raw_vs_raw", "raw")):
            br = board[(board["learner"] == L) & (board["contrast"] == kind)].iloc[0]
            it.close("coral board %s %s rival_mae (all rows)" % (L, kind), mae(y, R[L][key]), br["rival_mae"])
            it.close("coral board %s %s ours_mae (all rows)" % (L, kind), mae(y, cols["ours"]), br["ours_mae"])
        it.true("coral %s guard_passed" % L, R[L]["guard_passed"])
    e = pd.read_csv(use(CORAL_REPORT + "/magnitude_edges.csv"), float_precision="round_trip")
    e0 = e[e["lead"] == 0].iloc[0]
    edges = np.asarray([e0["pos_q25"], e0["pos_q50"], e0["pos_q75"]], dtype=np.float64)
    names = ["B1 (0, q25]", "B2 (q25, q50]", "B3 (q50, q75]", "B4 (q75, max]"]
    idx = np.searchsorted(edges, y, side="left")
    bins = np.array(["B0 zero" if y[i] == 0 else names[int(idx[i])] for i in range(y.size)], dtype=object)
    strata = [(b, bins == b) for b in ["B0 zero"] + names] + [("severe y >= 50", y >= 50), ("ALL rows", y == y)]
    mb = pd.read_csv(use(CORAL_REPORT + "/magnitude_bins.csv"), float_precision="round_trip")
    ckeys = learners + ["predict_zero", "donor_median"]
    vals = {"edges": {"pos_q25": float(edges[0]), "pos_q50": float(edges[1]), "pos_q75": float(edges[2]),
                      "positive_donor_rows": int(e0["positive_donor_rows"]), "donor_rows": int(e0["donor_rows"])},
            "band": band, "strata": {}}
    print("edges (lead 0, %d donor rows, %d positive): q25 %r q50 %r q75 %r" % (e0["donor_rows"],
          e0["positive_donor_rows"], edges[0], edges[1], edges[2]))
    for name, mask in strata:
        s = stratum_table(y, groups, cols, mask, "ours", band, ckeys)
        vals["strata"][name] = s
        print_stratum(name, s, "ours", ckeys)
        if name.startswith("B"):
            for col, key in ((ours, "ours"), ("base__predict_zero", "predict_zero"),
                             ("base__donor_median", "donor_median")):
                r = mb[(mb["lead"] == 0) & (mb["rows_basis"] == "all") & (mb["stratum_value"] == "ALL")
                       & (mb["bin"] == name) & (mb["column"] == col)]
                if not it.true("magnitude_bins.csv has %s %s" % (name, col), len(r) == 1, len(r)):
                    continue
                r = r.iloc[0]
                it.close("magnitude_bins %s %s n" % (name, col), s["n"], r["n"], 0.0)
                it.close("magnitude_bins %s %s n_groups" % (name, col), s["n_groups"], r["n_groups"], 0.0)
                it.close("magnitude_bins %s %s mean_y" % (name, col), s["mean_y"], r["mean_y"])
                it.close("magnitude_bins %s %s mean_pred" % (name, col), s["columns"][key]["mean_pred"], r["mean_pred"])
                it.close("magnitude_bins %s %s mae" % (name, col), s["columns"][key]["mae"], r["mae"])
    it.note("y >= 50 strict alternative y > 50: %d rows" % int((y > 50).sum()))
    it.d["values"] = vals
    return it.summary()


# ============================================================================== A1
def item_A1():
    it = Item("A1", "Fire active cells, stratified: ours vs LightGBM-Tweedie (others and predict-zero beside); "
                    "outcome-conditional, post hoc",
              "Fire lead 0 labelled rows 94,702 (40 groups, 2019-2022): y == 0; y > 0; top 1% y >= q99 (q99 = "
              "numpy.quantile of the 94,702 TEST labels at 0.99, linear); 0 < y < q99.",
              "Join each rival on (unit,time,lead); per stratum n, groups, mean y, mean prediction, MAE (rival = "
              "arm__rival_<L>; ridge raw beside); d_g = MAE_Tweedie(g) - MAE_ours(g) over the stratum's groups, group "
              "jackknife 1.96, groups ours better, D74 tag with the fire band (report-only).")
    run = "fire"
    d, _ = preds(run)
    V = verdict(run)
    band = float(V["band"])
    ours = "arm__arcsine_corrector_gls"
    it.true("fire adopted == %s" % ours, "arm__" + V["adopted"] == ours)
    learners = ["ridge", "rf", "lgbm", "lgbm_tweedie"]
    R = join_rivals(run, learners, d)
    yall = d["y"].to_numpy(np.float64)
    lab = np.isfinite(yall)
    y = yall[lab]
    groups = d["group"].astype(str).to_numpy()[lab]
    gn_all = d["base__guess_normal"].to_numpy(np.float64)
    to_all = d["arm__identity_trees_off_unweighted"].to_numpy(np.float64)
    ridge_is_gn = bool(np.array_equal(R["ridge"]["guarded"], gn_all))
    ridge_is_to = bool(np.array_equal(R["ridge"]["guarded"], to_all))
    ridge_gn_maxdev = float(np.max(np.abs(R["ridge"]["guarded"] - gn_all)))
    it.true("fire ridge guard failed (guarded column replaced)", R["ridge"]["guard_passed"] is False)
    it.true("fire ridge guarded column == the run's normal (arm__identity_trees_off_unweighted, the R16 decline "
            "target) exactly on all saved rows", ridge_is_to)
    it.note("fire ridge guarded column vs base__guess_normal: exactly equal %s, max |diff| %.3g over %d saved rows "
            "(it is the identity trees-off column, which equals guess-normal only within the M34 tolerance)"
            % (ridge_is_gn, ridge_gn_maxdev, len(gn_all)))
    ridge_is_normal = {"equals_identity_trees_off_exactly": ridge_is_to, "equals_guess_normal_exactly": ridge_is_gn,
                       "max_abs_diff_vs_guess_normal": ridge_gn_maxdev}
    it.true("fire lgbm_tweedie guard passed and guarded == raw", R["lgbm_tweedie"]["guard_passed"] and
            bool(np.array_equal(R["lgbm_tweedie"]["guarded"], R["lgbm_tweedie"]["raw"])))
    cols = {"ours": d[ours].to_numpy(np.float64)[lab]}
    for L in learners:
        cols[L] = R[L]["guarded"][lab]
    cols["ridge_raw"] = R["ridge"]["raw"][lab]
    cols["predict_zero"] = d["base__predict_zero"].to_numpy(np.float64)[lab]
    board = pd.read_csv(use(RIV[run] + "/board_lead_0.csv"), float_precision="round_trip")
    for L in learners:
        for kind, key in (("guarded_vs_headline", "guarded"), ("raw_vs_raw", "raw")):
            br = board[(board["learner"] == L) & (board["contrast"] == kind)].iloc[0]
            it.close("fire board %s %s rival_mae" % (L, kind), mae(y, R[L][key][lab]), br["rival_mae"])
            it.close("fire board %s %s ours_mae" % (L, kind), mae(y, cols["ours"]), br["ours_mae"])
            it.true("fire board %s guard_passed column" % L, bool(br["guard_passed"]) == R[L]["guard_passed"])
    q99 = float(np.quantile(y, 0.99))
    strata = [("all labelled", np.ones(y.size, bool)), ("y == 0", y == 0), ("y > 0", y > 0),
              ("top 1% (y >= q99)", y >= q99), ("0 < y < q99", (y > 0) & (y < q99))]
    ckeys = ["lgbm_tweedie", "ridge", "rf", "lgbm", "ridge_raw", "predict_zero"]
    vals = {"q99": q99, "q99_strict_gt_rows": int((y > q99).sum()), "band": band, "strata": {},
            "ridge_guarded_column": ridge_is_normal}
    print("q99 = %r (6 d.p. %.6f); rows y >= q99: %d; strict y > q99: %d" % (q99, q99, int((y >= q99).sum()),
                                                                          int((y > q99).sum())))
    for name, mask in strata:
        s = stratum_table(y, groups, cols, mask, "ours", band, ckeys)
        s["share_of_labelled_pct"] = 100.0 * s["n"] / y.size
        vals["strata"][name] = s
        print_stratum(name + " (%.2f%% of labelled)" % s["share_of_labelled_pct"], s, "ours", ckeys)
    it.note("Only the Tweedie contrast is the spec's; the other rivals' and predict-zero's per-group contrasts are "
            "printed beside (report-only, same rule).")
    it.d["values"] = vals
    return it.summary()


# ============================================================================== A2
def item_A2():
    it = Item("A2", "Coral bleached (y > 0) surveys at the nowcast: ours vs each of the five common rivals "
                    "(outcome-conditional, post hoc)",
              "Coral lead 0 visits with y > 0: 1,024 of 2,312 (36 of the 37 scored groups), 2016-2019.",
              "Join on (unit,time,lead); keep y > 0; pooled MAE ours / arm__rival_<L> (guarded == raw asserted) / "
              "predict-zero / donor median; mean y and mean predictions; per rival d_g = MAE_rival(g) - MAE_ours(g) "
              "over the 36 groups, group jackknife 1.96, groups ours better, D74 tag with the coral band.")
    run = "coral"
    d, _ = preds(run)
    V = verdict(run)
    band = float(V["band"])
    ours = "arm__arcsine_corrector_gls"
    y = d["y"].to_numpy(np.float64)
    groups = d["group"].astype(str).to_numpy()
    learners = ["ridge", "rf", "lgbm", "lgbm_tweedie", "hgb_l1"]
    R = join_rivals(run, learners, d)
    cols = {"ours": d[ours].to_numpy(np.float64)}
    for L in learners:
        it.true("coral %s guard passed and guarded == raw" % L, R[L]["guard_passed"] and
                bool(np.array_equal(R[L]["guarded"], R[L]["raw"])))
        cols[L] = R[L]["guarded"]
    cols["predict_zero"] = d["base__predict_zero"].to_numpy(np.float64)
    cols["donor_median"] = d["base__donor_median"].to_numpy(np.float64)
    board = pd.read_csv(use(RIV[run] + "/board_lead_0.csv"), float_precision="round_trip")
    for L in learners:
        br = board[(board["learner"] == L) & (board["contrast"] == "guarded_vs_headline")].iloc[0]
        it.close("coral board %s rival_mae (all rows)" % L, mae(y, cols[L]), br["rival_mae"])
        it.close("coral board %s ours_mae (all rows)" % L, mae(y, cols["ours"]), br["ours_mae"])
    ckeys = learners + ["predict_zero", "donor_median"]
    s = stratum_table(y, groups, cols, y > 0, "ours", band, ckeys)
    print_stratum("y > 0", s, "ours", ckeys)
    order = sorted(cols, key=lambda k: s["columns"][k]["mae"])
    print("  ranking by MAE on y > 0: %s" % ", ".join("%s %.4f" % (k, s["columns"][k]["mae"]) for k in order))
    s["band"] = band
    s["ranking"] = order
    it.d["values"] = s
    return it.summary()


# ============================================================================== main
def sanitize(o):
    if isinstance(o, dict):
        return {str(k): sanitize(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [sanitize(v) for v in o]
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return f if math.isfinite(f) else None
    return o


def main():
    results = {}
    for fn in (item_M34, item_R12, item_R13, item_R14, item_R15, item_P29, item_R3b, item_RC12, item_A1, item_A2):
        d = fn()
        results[d["id"]] = d
    doc = {"script": "D:/treeroute/analysis/paper_posthoc/posthoc_B.py", "implementer": "B", "post_hoc": True,
           "note": "POST HOC numbers (computed after the test labels were opened); they never change a "
                   "pre-registered verdict. NaN/inf are written as null.",
           "python": sys.version, "numpy": np.__version__, "pandas": pd.__version__,
           "inputs_sha256": {k: v for k, v in sorted(_SHA.items())},
           "failed_checks": [list(map(str, f)) for f in FAILED], "results": results}
    with open(RESULT, "w", encoding="utf-8") as f:
        json.dump(sanitize(doc), f, indent=1, allow_nan=False)
    print("\nwrote %s; %d inputs hashed; %d checks failed" % (RESULT, len(_SHA), len(FAILED)))
    for f in FAILED:
        print("  FAILED: %s" % (f,))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
