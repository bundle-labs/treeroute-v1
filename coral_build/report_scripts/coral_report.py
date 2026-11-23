"""coral_report.py -- REPORT-ONLY tables over the SAVED rows of a FINISHED table-option (neighbour) run.

Pre-registration: D:/treeroute/coral_build/PREREGISTRATION_DRAFT_coral.md section 6.1, 6.2 and section 12 item 8.
It reads saved files only and writes CSV and Markdown into a NEW folder. It never fits, never picks, never edits the
run, and nothing it prints can change a choice or the verdict.

    py -3.9 coral_report.py <run folder> --package <package folder> --out <new folder>

It refuses any run that is not a headline-eligible headline run (run_record kind 'headline', headline_eligible true),
so that no smoke's test scores are read before the freeze; --toy (tests only) admits a run of a synthetic toy package.

Reads (and records the SHA-256 of each, in inputs_manifest.json):
  run folder: DONE.json, run_record.json, derived.json, verdict.json, decision_checks.json, test_pass_router.json,
  fitctx_log.parquet, test_preds.parquet, pools_*.parquet, context_missing/*.parquet, ladder/ladder.json,
  ladder/lead_<L>/{lead.json, test_preds.parquet, pools_guard.parquet, pools_test_pass.parquet,
  issue_missing_rows.parquet}; the package's catalog.yaml (column roles only); the lead tables named in derived.json
  (U1:table inputs; their SHA-256 must equal the recorded one) for the donor rows' labels and, for the R30 counts,
  the R30 tree columns and the mhw_* columns; adoption.json, adoption_lead_<L>.json and run.log (the penalty picks
  and the engine's printed decision lines); the data builder's month-precision list (not an engine file; pinned by
  MONTH_PRECISION_SHA256 for a non-toy run, optional for a toy run).
Writes (exclusive create; the folder must be new or empty, outside the run folder and outside every protected root):
  per_programme.csv, programme_verdicts.csv, magnitude_edges.csv, magnitude_bins.csv, flattening_guard.csv,
  per_year_macro.csv, per_ecoregion.csv, counts_no_tree.csv, counts_pool_fallback.csv, counts_left_out.csv,
  guard_reference.csv, r30_missing.csv, pools_month_precision.csv, penalty_edge_picks.csv,
  programme_blocked_jackknife.csv, coral_report.md, inputs_manifest.json.
A fact the engine does not save is printed as 'not saved by the engine', or counted from saved rows and the lead
tables and labelled 'counted from the lead table (not an engine record)'; never rebuilt from engine internals.
A saved record that the engine always writes but that is missing or disagrees is a refusal (exit 2), not a blank.

Definitions (README.md lists them; the ones marked CHOSEN were not fixed by the pre-registration draft):
  - Donor rows of lead L: the run's bank rows (derived.json R18:units 'bank') present in lead L's table, target date
    at or before lead L's fit cut (derived.json R11), finite label. Checked against the engine: the count equals
    fitctx_log's 'bank' hand-out at that cut, and their median equals the saved base__donor_median.
  - Quartiles: numpy's default (linear) quantile, as the engine's stratum_edges (metrics.py:722-740).
  - Magnitude bins: 'zero' (label == 0), then the positive labels in right-closed bins of the donor rows' positive
    labels' quartiles: (0, q25], (q25, q50], (q50, q75], (q75, inf) (D73 convention, metrics.py:743-760).
  - Flattening guard: rows with label >= the severe edge; mean prediction vs observed mean, every column.
    Both edges are printed, each labelled (owner ruling X4, 2026-10-20, chose (b) as the default):
    (a) q75 of ALL donor-row labels (the draft's words) -- printed beside the default since owner ruling X4;
    (b) q75 of the POSITIVE donor-row labels (the top magnitude bin's lower edge) -- the DEFAULT (owner ruling X4).
    The labels are built from EDGE_DEFAULT (edge_roles).
  - Predict-zero and the donor-row median MAE are printed beside every MAE, on the same rows.
  - A stratum value with fewer than MIN_ROWS_FOR_METRICS rows is shown with n only (CHOSEN, 10).
  - Macro = unweighted mean over the scored groups of the per-group MAE (draft 6.1).
  - Programme verdict lines: the engine's D74 rule (metrics.py:1097-1120) on the groups holding the value; report
    only; the run's band (the nowcast band at every lead); 'declined' when the layer declined at that lead. The ALL
    line must reproduce the engine's verdict record (verdict.json, ladder.json), or the script refuses.
  - R33 top-10% detection: printed per programme, and on the pooled (ALL) line labelled "source statistic, not
    severe-tail skill" (draft 6.1) -- CHOSEN to keep the number with the label rather than blank it.
  - Common rows: (unit, time) keys with a finite label and adopted prediction at every lead (table_ladder.py:606-611).
"""

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

SCRIPT_NAME = "coral_report.py"
SCRIPT_VERSION = "1.2.0"

# --- constants (each one cited; none is tuned on any result) --------------------------------------------------
MIN_ROWS_FOR_METRICS = 10          # CHOSEN: like metrics.py ANOMALY_R2_MIN_ROWS (10) and S2.detection_min_events (10)
QUARTILES = (0.25, 0.5, 0.75)      # metrics.py:126 STRATUM_QUANTILES (R34)
MIN_DISTINCT_POSITIVE = 4          # metrics.py:127 STRATUM_MIN_DISTINCT (R34)
JACKKNIFE_Z = 1.96                 # engine_constants.py S2.jackknife_z (grid Q19 a)
IDENTICAL_ATOL = 1e-12             # metrics.py:111
DETECTION_TOP_SHARE = 0.10         # engine_constants.py S2.detection_top_share (R33)
DETECTION_MIN_EVENTS = 10          # engine_constants.py S2.detection_min_events
DETECTION_MAX_EVENT_SHARE = 0.50   # engine_constants.py S2.detection_max_event_share
HIT_TOLERANCE_SHARE = 0.5          # engine_constants.py S2.hit_tolerance_deviation_share (R32), used for the check
PRED_PREFIXES = ("arm__", "placebo__", "base__")
PREDICT_ZERO = "base__predict_zero"
DONOR_MEDIAN = "base__donor_median"
ALL = "ALL"
ALL_LABEL = "pooled (mixes programmes)"
EDGE_PRIMARY = "q75_all_donor_labels"          # option (a), printed beside the default (owner ruling X4)
EDGE_POSITIVE = "q75_positive_donor_labels"     # option (b), the default (owner ruling X4)
EDGE_DEFAULT = EDGE_POSITIVE                    # owner ruling X4 (OWNER_RULINGS_2026-10-06.md section X, 2026-10-20): (b)
EDGE_BASE = {EDGE_PRIMARY: "(a) q75 of all donor-row labels", EDGE_POSITIVE: "(b) q75 of positive donor-row labels"}
NOT_SAVED = "not saved by the engine"
COUNTED = "counted from the lead table (not an engine record)"
BORDERLINE_SHARE = 0.20            # engine_constants.py:166 C10.borderline_share (blocked jackknife flag, metrics.py:1080)
MHW_PREFIX = "mhw_"                # coral marine-heatwave columns (datasets/coral_draft/catalog.yaml:182-211)
MHW_DAYS = "mhw_days_365"          # NaN exactly when under 60 thresholded days (coral_tables/build_tables.py:315-330);
#                                    mhw_thr_gap can be NaN for another reason (no gap above 0.05, :329-334)
LOG_MAE_TOL = 5e-7 + 1e-12         # run.log prints each arm's MAE with %.6f (decide.py:1096)
# The data builder's month-precision list (coral_tables/build_visits.py:295-297; NOT an engine file), pinned by SHA-256.
# A non-toy run always reads this list (or a --month-precision-rows file with the same SHA-256).
MONTH_PRECISION_LIST = Path("D:/treeroute/coral_build/coral_data/month_precision_rows.csv")
MONTH_PRECISION_SHA256 = "cfa18268198ca9be48feb26f384287e7fe694c6f1ca7b221773af1994d838bf5"
DEFAULT_ROOTS = Path("D:/treeroute/registry/protected_roots.txt")
# --toy lets a non-headline run through only when its package is one of these SYNTHETIC packages (the engine's toy
# table package, engine/tests/table_toy.py). Any other run must be a headline-eligible headline run: the script reads
# test scores, and the read rule (PREREGISTRATION_DRAFT_coral.md section 12 item 4) forbids that before the freeze.
TOY_PACKAGES = ("toy_table",)
DETECTION_POOLED_LABEL = "source statistic, not severe-tail skill"   # draft 6.1 (CORAL_ENGINE_PLAN.md:226)


class ReportRefusal(Exception):
    """Fail loud: the saved files are not what this script expects."""


def refuse(msg: str) -> None:
    raise ReportRefusal(msg)


def edge_roles() -> Dict[str, str]:
    """The two flattening-guard edges' labels, built from EDGE_DEFAULT at call time (owner ruling X4)."""
    return {r: EDGE_BASE[r] + (" -- DEFAULT (owner ruling X4)" if r == EDGE_DEFAULT
                               else " -- printed beside, not the default (owner ruling X4)") for r in EDGE_BASE}


# =============================================================================================== reading
class Reader:
    """Reads saved files and records each file's SHA-256 (inputs_manifest.json)."""

    def __init__(self) -> None:
        self.read: Dict[str, str] = {}

    def _note(self, path: Path) -> None:
        self.read[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()

    def json(self, path: Path) -> Any:
        if not path.is_file():
            refuse("missing saved file: %s" % path)
        self._note(path)
        return json.loads(path.read_text(encoding="utf-8"))

    def parquet(self, path: Path, columns: Optional[Sequence[str]] = None) -> pd.DataFrame:
        if not path.is_file():
            refuse("missing saved file: %s" % path)
        self._note(path)
        return pd.read_parquet(path, columns=list(columns) if columns is not None else None)

    def text(self, path: Path) -> str:
        if not path.is_file():
            refuse("missing saved file: %s" % path)
        self._note(path)
        return path.read_text(encoding="utf-8", errors="replace")

    def yaml(self, path: Path) -> Any:
        import yaml

        if not path.is_file():
            refuse("missing package file: %s" % path)
        self._note(path)
        return yaml.safe_load(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _roles(catalog: Any) -> Dict[str, str]:
    cols = (catalog or {}).get("columns") or {}
    out: Dict[str, str] = {}
    for name, spec in cols.items():
        role = (spec or {}).get("role") if isinstance(spec, dict) else None
        if role in ("key_row", "key_group", "key_time", "key_mark", "target"):
            if role in out:
                refuse("catalog names role %r twice (%s, %s)" % (role, out[role], name))
            out[role] = str(name)
    missing = [r for r in ("key_row", "key_group", "key_time", "target") if r not in out]
    if missing:
        refuse("catalog.yaml has no column with role(s) %s" % missing)
    return out


def _days(values: pd.Series) -> np.ndarray:
    """Calendar days as proleptic ordinals (the engine's 'time' unit)."""
    if np.issubdtype(values.dtype, np.datetime64):
        return np.asarray([d.toordinal() for d in pd.to_datetime(values).dt.date], dtype=np.int64)
    return np.asarray([d.toordinal() for d in values], dtype=np.int64)


class Run:
    """The saved files of one finished run (read only)."""

    def __init__(self, folder: Any, package: Any, reader: Reader, stratum: Optional[str] = None,
                 toy: bool = False) -> None:
        self.folder = Path(folder).resolve()
        self.r = reader
        f = self.folder
        if not (f / "DONE.json").is_file():
            refuse("the run is not finished (no DONE.json): %s" % f)
        reader._note(f / "DONE.json")
        self.record = reader.json(f / "run_record.json")
        # the read gate, before any score file is opened
        kind, eligible, pkg = self.record.get("kind"), self.record.get("headline_eligible"), self.record.get("package")
        if toy:
            if pkg not in TOY_PACKAGES:
                refuse("--toy is for the synthetic toy packages %s only; this run's package is %r"
                       % (list(TOY_PACKAGES), pkg))
        elif not (kind == "headline" and eligible is True):
            refuse("this run is not a headline-eligible headline run (run_record kind %r, headline_eligible %r): its "
                   "test scores are not read (read rule, PREREGISTRATION_DRAFT_coral.md section 12 item 4); "
                   "--toy is only for the synthetic toy packages" % (kind, eligible))
        if self.record.get("input") != "table":
            refuse("not a table-option run (run_record input = %r)" % self.record.get("input"))
        self.verdict = reader.json(f / "verdict.json")
        if self.verdict.get("router_kind") != "neighbour":
            refuse("not a neighbour-router run (verdict router_kind = %r)" % self.verdict.get("router_kind"))
        self.derived = reader.json(f / "derived.json")
        self.ladder = reader.json(f / "ladder" / "ladder.json")
        self.leads = [0] + [int(x) for x in self.ladder["leads"]]
        self.preds: Dict[int, pd.DataFrame] = {0: reader.parquet(f / "test_preds.parquet")}
        self.lead_json: Dict[int, Any] = {}
        for L in self.leads[1:]:
            d = f / "ladder" / ("lead_%d" % L)
            self.preds[L] = reader.parquet(d / "test_preds.parquet")
            self.lead_json[L] = reader.json(d / "lead.json")
        self.adopted = {0: str(self.verdict["adopted_column"])}
        self.declined = {0: bool(self.verdict["declined"])}
        for L in self.leads[1:]:
            self.adopted[L] = str(self.lead_json[L]["test"]["adopted_column"])
            self.declined[L] = bool(self.lead_json[L]["declined_at_lead"])
        for L in self.leads:
            lv = (self.ladder.get("verdicts") or {}).get(str(L))
            if lv is not None and str(lv.get("adopted")) != self.adopted[L]:
                refuse("lead %d: ladder.json adopted %r but the lead record says %r" % (L, lv.get("adopted"),
                                                                                         self.adopted[L]))
        self.reference = str(self.verdict["reference"])
        self.pinned = ("arm__" + str(self.ladder["pinned"])) if self.ladder.get("pinned") else ""
        band = self.verdict.get("band")
        self.band = float(band) if band is not None and math.isfinite(float(band)) and float(band) > 0 else None
        self.tol = {0: float(self.verdict["hit_tolerance"])}
        for L in self.leads[1:]:
            self.tol[L] = float(self.ladder["hit_tolerance"])
        strata = list(self.record.get("strata") or [])
        if stratum is None:
            if len(strata) != 1:
                refuse("the run declares strata %s; name one with --stratum" % strata)
            stratum = strata[0]
        elif stratum not in strata:
            refuse("--stratum %r is not a stratum of this run (%s)" % (stratum, strata))
        self.stratum = str(stratum)
        self.kind = str(self.record.get("kind"))
        self.headline_eligible = bool(self.record.get("headline_eligible"))
        self.not_headline = list(self.record.get("not_headline_reasons") or [])
        self.groups = [str(g) for g in self.record["groups"]]
        self.cuts = {int(k): v for k, v in self.derived["R11"]["value"].items()}
        bank = self.derived["R18:units"]["value"]["bank"]
        self.bank_ids = set(str(u) for v in bank.values() for u in v)
        self.fitctx = reader.parquet(f / "fitctx_log.parquet")
        # the package's column roles and the lead tables
        self.catalog = reader.yaml(Path(package) / "catalog.yaml")
        self.catalog_roles = _roles(self.catalog)
        # R30 (derive/table.py:251-266) is written for every table run; its columns are the tree columns
        r30 = self.derived.get("R30")
        if not isinstance(r30, dict):
            refuse("derived.json has no R30 record (the engine writes it for every table run, derive/table.py:251-266)")
        self.r30_columns = sorted(str(c) for c in ((r30.get("inputs") or {}).get("filled_share") or {}))
        cat_cols = [str(c) for c in ((self.catalog or {}).get("columns") or {})]
        self.mhw_columns = sorted({c for c in cat_cols + self.r30_columns if c.startswith(MHW_PREFIX)})
        self.feature_columns = sorted(set(self.r30_columns) | set(self.mhw_columns))
        self.features: Dict[int, pd.DataFrame] = {}
        files = self.derived["U1:table"]["inputs"]["files"]
        self.tables: Dict[int, pd.DataFrame] = {}
        rr = self.catalog_roles
        want = [rr["key_row"], rr["key_group"], rr["key_time"], rr["target"]] + \
            ([rr["key_mark"]] if "key_mark" in rr else [])
        import pyarrow.parquet as pq

        for item in files:
            L = int(item["lead"])
            if L not in self.leads:
                continue
            path = Path(item["path"])
            got = sha256_file(path)
            if got != item["sha256"]:
                refuse("lead %d table %s: SHA-256 %s differs from the run's recorded %s" % (L, path, got,
                                                                                          item["sha256"]))
            self.r.read[str(path)] = got
            names = set(pq.read_schema(path).names)
            absent = [c for c in self.feature_columns if c not in names]
            if absent:
                refuse("lead %d table %s has no column(s) %s (derived.json R30 tree columns, catalog mhw_* columns)"
                       % (L, path, absent[:5]))
            cols = list(dict.fromkeys(want + [self.stratum] + self.feature_columns))
            t = pd.read_parquet(path, columns=cols)
            self.features[L] = t[self.feature_columns].reset_index(drop=True)
            out = pd.DataFrame({"row_id": t[rr["key_row"]].astype(str).to_numpy(dtype=object),
                                "group": t[rr["key_group"]].astype(str).to_numpy(dtype=object),
                                "time": _days(t[rr["key_time"]]),
                                "y": t[rr["target"]].to_numpy(dtype=np.float64),
                                "stratum": t[self.stratum].to_numpy(dtype=object)})
            if "key_mark" in rr:
                out["mark"] = t[rr["key_mark"]].astype(str).to_numpy(dtype=object)
            self.tables[L] = out
        missing = [L for L in self.leads if L not in self.tables]
        if missing:
            refuse("derived.json U1:table names no table for lead(s) %s" % missing)
        self._check_saved_rows()

    def _check_saved_rows(self) -> None:
        """Every saved scored row is a row of its lead table, with the same target day and label."""
        for L in self.leads:
            p = self.preds[L]
            for c in ("unit", "group", "time", "year", "y", self.stratum):
                if c not in p.columns:
                    refuse("lead %d test_preds has no column %r" % (L, c))
            t = self.tables[L].set_index("row_id")
            units = p["unit"].astype(str)
            absent = sorted(set(units) - set(t.index))
            if absent:
                refuse("lead %d: %d saved rows are not in the lead table (e.g. %s)" % (L, len(absent), absent[:3]))
            tt = t.loc[units.tolist()]
            if not np.array_equal(tt["time"].to_numpy(np.int64), p["time"].to_numpy(np.int64)):
                refuse("lead %d: saved 'time' differs from the lead table's target day" % L)
            y = p["y"].to_numpy(np.float64)
            ok = np.isfinite(y)
            if not np.array_equal(tt["y"].to_numpy(np.float64)[ok], y[ok]):
                refuse("lead %d: saved labels differ from the lead table's labels" % L)

    # ------------------------------------------------------------------ donor rows
    def donor_rows(self, L: int) -> pd.DataFrame:
        cut = int(self.cuts[L]["fit_cut"])
        t = self.tables[L]
        sel = t["row_id"].isin(self.bank_ids).to_numpy() & (t["time"].to_numpy() <= cut) & \
            np.isfinite(t["y"].to_numpy(np.float64))
        d = t[sel]
        if "mark" in d.columns and (d["mark"] != "train").any():
            refuse("lead %d: %d donor rows are not train-marked" % (L, int((d["mark"] != "train").sum())))
        if len(d) == 0:
            refuse("lead %d: no donor row at the fit cut %d" % (L, cut))
        return d

    def feature_frame(self, L: int, which: str) -> pd.DataFrame:
        """The R30 tree columns and the mhw_* columns, as read from lead L's table, on its donor rows ('donor') or on
        the scored rows of its test_preds ('scored': rows with a finite label)."""
        f = self.features[L]
        if which == "donor":
            return f.loc[self.donor_rows(L).index].reset_index(drop=True)
        if which != "scored":
            refuse("unknown row set %r" % which)
        t = self.tables[L]
        if t["row_id"].duplicated().any():
            refuse("lead %d table: row ids are not unique" % L)
        p = self.preds[L]
        p = p[np.isfinite(p["y"].to_numpy(np.float64))]
        pos = pd.Index(t["row_id"]).get_indexer(p["unit"].astype(str).tolist())
        if (pos < 0).any():
            refuse("lead %d: %d scored rows are not in the lead table" % (L, int((pos < 0).sum())))
        return f.iloc[pos].reset_index(drop=True)

    def engine_donor_count(self, L: int) -> Optional[int]:
        f = self.fitctx
        cut = int(self.cuts[L]["fit_cut"])
        sel = (f["object_kind"] == "donor_rows") & (f["purpose"] == "bank") & (f["cut_kind"] == "fit") & \
            (f["lead"].astype(float) == float(L)) & (f["cut"].astype(float) == float(cut))
        vals = sorted(set(int(v) for v in f.loc[sel, "n_rows"].tolist()))
        if not vals:
            return None
        if len(vals) > 1:
            refuse("lead %d: fitctx_log holds different 'bank' donor counts %s" % (L, vals))
        return vals[0]

    def frame(self, L: int, basis: str, common: set) -> pd.DataFrame:
        p = self.preds[L]
        if basis == "all":
            return p.reset_index(drop=True)
        k = _keys(p)
        return p[np.isin(k, np.asarray(sorted(common), dtype=object))].reset_index(drop=True)


def _keys(p: pd.DataFrame) -> np.ndarray:
    return np.asarray(["%s\t%d" % (u, t) for u, t in zip(p["unit"].astype(str).tolist(),
                                                        p["time"].to_numpy(np.int64).tolist())], dtype=object)


def common_keys(run: Run) -> set:
    """Rows scored at every lead (table_ladder.py:606-611): finite label and adopted prediction at each lead."""
    common = None
    for L in run.leads:
        p = run.preds[L]
        ok = np.isfinite(p["y"].to_numpy(np.float64)) & np.isfinite(p[run.adopted[L]].to_numpy(np.float64))
        k = set(_keys(p[ok]).tolist())
        common = k if common is None else common & k
    return common or set()


# =============================================================================================== metrics
def pred_columns(p: pd.DataFrame) -> List[str]:
    return [c for c in p.columns if isinstance(c, str) and c.startswith(PRED_PREFIXES)]


def column_kind(c: str) -> str:
    return "arm" if c.startswith("arm__") else ("placebo" if c.startswith("placebo__") else "baseline")


def corr2(y: np.ndarray, p: np.ndarray) -> float:
    if y.size == 0 or y.max() == y.min() or p.max() == p.min():
        return float("nan")
    yc, pc = y - y.mean(), p - p.mean()
    syy, spp = float(np.sum(yc * yc)), float(np.sum(pc * pc))
    if not (syy > 0 and spp > 0):
        return float("nan")
    r = float(np.sum(yc * pc)) / math.sqrt(syy * spp)
    return r * r


def detection(y: np.ndarray, p: np.ndarray) -> Tuple[float, int]:
    """R33 (metrics.py:700-719): strict top-10% events and hits."""
    if y.size == 0:
        return float("nan"), 0
    q = 1.0 - DETECTION_TOP_SHARE
    ev = y > np.quantile(y, q)
    n = int(ev.sum())
    if n < DETECTION_MIN_EVENTS or n / float(y.size) > DETECTION_MAX_EVENT_SHARE:
        return float("nan"), n
    return float(np.mean(p[ev] > np.quantile(p, q))), n


def mae(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean(np.abs(y - p))) if y.size else float("nan")


def line(frame: pd.DataFrame, col: str, tol: float, n_only: bool = False) -> Dict[str, Any]:
    """One column on the frame's rows with a finite label and a finite prediction; predict-zero and the donor-row
    median scored on the SAME rows, beside."""
    y_all = frame["y"].to_numpy(np.float64)
    p_all = frame[col].to_numpy(np.float64)
    ok = np.isfinite(y_all) & np.isfinite(p_all)
    y, p = y_all[ok], p_all[ok]
    rec: Dict[str, Any] = {"n": int(ok.sum()), "n_groups": int(frame.loc[ok, "group"].nunique())}
    keys = ("zero_share", "mean_y", "mean_pred", "mae", "mae_predict_zero", "mae_donor_median",
            "gain_vs_predict_zero", "gain_vs_donor_median", "corr2", "hit", "calibration_ratio",
            "detection_top10", "detection_events")
    if n_only or rec["n"] == 0:
        rec.update({k: float("nan") for k in keys})
        rec["n_only"] = bool(n_only)
        return rec
    pz = frame[PREDICT_ZERO].to_numpy(np.float64)[ok] if PREDICT_ZERO in frame.columns else None
    pm = frame[DONOR_MEDIAN].to_numpy(np.float64)[ok] if DONOR_MEDIAN in frame.columns else None
    rec["zero_share"] = float(np.mean(y == 0))
    rec["mean_y"] = float(np.mean(y))
    rec["mean_pred"] = float(np.mean(p))
    rec["mae"] = mae(y, p)
    rec["mae_predict_zero"] = mae(y, pz) if pz is not None else float("nan")
    rec["mae_donor_median"] = mae(y, pm) if pm is not None else float("nan")
    rec["gain_vs_predict_zero"] = rec["mae_predict_zero"] - rec["mae"]
    rec["gain_vs_donor_median"] = rec["mae_donor_median"] - rec["mae"]
    rec["corr2"] = corr2(y, p)
    rec["hit"] = float(np.mean(np.abs(y - p) <= tol))
    my = float(np.mean(y))
    rec["calibration_ratio"] = float(np.mean(p)) / my if my != 0 else float("nan")
    rec["detection_top10"], rec["detection_events"] = detection(y, p)
    rec["n_only"] = False
    return rec


def jackknife(v: np.ndarray) -> Dict[str, float]:
    """Leave-one-group-out jackknife (metrics.py:1032-1055)."""
    n = int(v.size)
    if n == 0:
        return {"mean": float("nan"), "se": float("nan"), "low": float("nan"), "high": float("nan"), "n_groups": 0}
    if n < 3:
        return {"mean": float(v.mean()), "se": float("nan"), "low": float("nan"), "high": float("nan"),
                "n_groups": n}
    jk = np.array([np.delete(v, i).mean() for i in range(n)])
    se = float(np.sqrt((n - 1) / n * ((jk - jk.mean()) ** 2).sum()))
    return {"mean": float(v.mean()), "se": se, "low": float(v.mean() - JACKKNIFE_Z * se),
            "high": float(v.mean() + JACKKNIFE_Z * se), "n_groups": n}


def d74_tag(dv: np.ndarray, band: Optional[float], declined: bool) -> Tuple[str, Dict[str, float]]:
    """The engine's D74 reading rule (metrics.py:1097-1120, single_verdict :1141-1172)."""
    jk = jackknife(dv)
    if dv.size == 0:
        return "no rows", jk
    if band is None:
        tag = "no band (R35)"
    elif np.all(np.abs(dv) <= IDENTICAL_ATOL):
        tag = "identical"
    elif not (math.isfinite(jk["low"]) and math.isfinite(jk["high"])):
        tag = "cannot_tell"
    elif -band <= jk["low"] and jk["high"] <= band:
        tag = "equivalent"
    elif jk["low"] > 0 and jk["mean"] >= band:
        tag = "helps"
    elif jk["high"] < 0 and jk["mean"] <= -band:
        tag = "hurts"
    else:
        tag = "cannot_tell"
    if declined:
        tag = "declined"
    return tag, jk


# =============================================================================================== edges
def magnitude_edges(run: Run, L: int) -> Dict[str, Any]:
    d = run.donor_rows(L)
    y = d["y"].to_numpy(np.float64)
    pos = y[y > 0]
    if np.unique(pos).size < MIN_DISTINCT_POSITIVE:
        refuse("lead %d: %d distinct positive donor labels; quartiles need at least %d (R34)"
               % (L, np.unique(pos).size, MIN_DISTINCT_POSITIVE))
    q = np.quantile(pos, QUARTILES)
    med = float(np.median(y))
    eng_n = run.engine_donor_count(L)
    if eng_n is None:
        refuse("lead %d: fitctx_log holds no 'bank' donor_rows record at the fit cut, so the rebuilt donor rows "
               "cannot be checked against the engine" % L)
    if eng_n != int(y.size):
        refuse("lead %d: %d donor rows rebuilt, the engine handed out %d (fitctx_log 'bank')" % (L, y.size, eng_n))
    p = run.preds[L]
    if DONOR_MEDIAN not in p.columns or not len(p):
        refuse("lead %d: test_preds holds no %s value, so the rebuilt donor-row median cannot be checked"
               % (L, DONOR_MEDIAN))
    vals = np.unique(p[DONOR_MEDIAN].to_numpy(np.float64))
    if vals.size != 1:
        refuse("lead %d: base__donor_median is not one value (%s)" % (L, vals[:5]))
    eng_med = float(vals[0])
    if not math.isclose(eng_med, med, rel_tol=1e-9, abs_tol=1e-12):
        refuse("lead %d: rebuilt donor-row median %r differs from the saved %r" % (L, med, eng_med))
    tol_rebuilt = HIT_TOLERANCE_SHARE * float(np.mean(np.abs(y - med)))
    return {"lead": L, "fit_cut": int(run.cuts[L]["fit_cut"]), "donor_rows": int(y.size),
            "donor_rows_engine": eng_n, "donor_median": med, "donor_median_saved": eng_med,
            "positive_donor_rows": int(pos.size), "pos_q25": float(q[0]), "pos_q50": float(q[1]),
            "pos_q75": float(q[2]), EDGE_PRIMARY: float(np.quantile(y, 0.75)), EDGE_POSITIVE: float(q[2]),
            "hit_tolerance_used": run.tol[L], "hit_tolerance_rebuilt_fit_cut": tol_rebuilt}


def magnitude_bin(y: np.ndarray, e: Dict[str, Any]) -> np.ndarray:
    edges = np.asarray([e["pos_q25"], e["pos_q50"], e["pos_q75"]], dtype=np.float64)
    out = np.empty(y.size, dtype=object)
    names = ["B1 (0, q25]", "B2 (q25, q50]", "B3 (q50, q75]", "B4 (q75, max]"]
    idx = np.searchsorted(edges, y, side="left")
    for i in range(y.size):
        out[i] = "B0 zero" if y[i] == 0 else names[int(idx[i])]
    return out


BIN_ORDER = ["B0 zero", "B1 (0, q25]", "B2 (q25, q50]", "B3 (q50, q75]", "B4 (q75, max]"]


# =============================================================================================== tables
def _stratum_values(run: Run) -> List[str]:
    vals = set()
    for L in run.leads:
        t = run.tables[L]
        vals |= set(_sv(t.loc[t["group"].isin(run.groups), "stratum"]).tolist())
    return sorted(vals)


def _sv(s: pd.Series) -> np.ndarray:
    return np.asarray(["(none)" if (v is None or (isinstance(v, float) and math.isnan(v))) else str(v)
                       for v in s.tolist()], dtype=object)


def _subsets(run: Run, frame: pd.DataFrame, values: List[str]):
    sv = _sv(frame[run.stratum])
    yield ALL, frame
    for v in values:
        yield v, frame[sv == v].reset_index(drop=True)


def _bases(run: Run, common: set):
    for L in run.leads:
        for basis in ("all", "common"):
            yield L, basis, run.frame(L, basis, common)


def per_programme(run: Run, common: set, values: List[str]) -> pd.DataFrame:
    rows = []
    for L, basis, frame in _bases(run, common):
        for v, sub in _subsets(run, frame, values):
            n_value = int(np.isfinite(sub["y"].to_numpy(np.float64)).sum())
            n_only = v != ALL and n_value < MIN_ROWS_FOR_METRICS
            for c in pred_columns(frame):
                rec = {"lead": L, "rows_basis": basis, "stratum_column": run.stratum, "stratum_value": v,
                       "label": ALL_LABEL if v == ALL else "", "column": c, "column_kind": column_kind(c),
                       "adopted": c == run.adopted[L], "n_value_rows": n_value}
                rec.update(line(sub, c, run.tol[L], n_only))
                # R33 pooled over programmes measures the programme mix (draft 6.1): kept, and labelled
                rec["detection_label"] = DETECTION_POOLED_LABEL if v == ALL else "within programme"
                rows.append(rec)
    return pd.DataFrame(rows)


def programme_verdicts(run: Run, common: set, values: List[str]) -> pd.DataFrame:
    rows = []
    plan = [(0, "all")] + [(L, "common") for L in run.leads]
    for L, basis in plan:
        frame = run.frame(L, basis, common)
        ad, ref = run.adopted[L], run.reference
        for v, sub in _subsets(run, frame, values):
            y = sub["y"].to_numpy(np.float64)
            ok = np.isfinite(y) & np.isfinite(sub[ad].to_numpy(np.float64)) & \
                np.isfinite(sub[ref].to_numpy(np.float64))
            s = sub[ok]
            groups, dv = _group_contrasts(s, ad, ref)
            dv_a = np.asarray(dv, dtype=np.float64)
            tag, jk = d74_tag(dv_a, run.band, run.declined[L])
            pooled = mae(s["y"].to_numpy(np.float64), s[ref].to_numpy(np.float64)) - \
                mae(s["y"].to_numpy(np.float64), s[ad].to_numpy(np.float64)) if len(s) else float("nan")
            flips = []
            if len(s) and math.isfinite(pooled) and pooled != 0:
                flips = [g for g, d in zip(groups, dv) if d != 0 and np.sign(d) != np.sign(pooled)]
            rec = {"lead": L, "rows_basis": basis, "stratum_column": run.stratum, "stratum_value": v,
                   "label": ("the registered verdict's rows; " + ALL_LABEL) if v == ALL else "report only",
                   "adopted_column": ad, "reference_column": ref, "declined": run.declined[L], "band": run.band,
                   "n_rows": int(len(s)), "tag": tag, "pooled_contrast": pooled,
                   "groups_better": int((dv_a > 0).sum()), "sign_flip_groups": ";".join(flips)}
            rec.update({k: jk[k] for k in ("mean", "se", "low", "high", "n_groups")})
            rec.update(_engine_match(run, L, basis, v, rec))
            rows.append(rec)
    return pd.DataFrame(rows)


def _group_contrasts(s: pd.DataFrame, ad: str, ref: str) -> Tuple[List[str], List[float]]:
    """Per group: MAE(reference) - MAE(adopted) on the group's rows (positive = the adopted column is better)."""
    groups = sorted(s["group"].astype(str).unique().tolist())
    dv = []
    for g in groups:
        gs = s[s["group"].astype(str) == g]
        gy = gs["y"].to_numpy(np.float64)
        dv.append(mae(gy, gs[ref].to_numpy(np.float64)) - mae(gy, gs[ad].to_numpy(np.float64)))
    return groups, dv


def _scored_subset(sub: pd.DataFrame, ad: str, ref: str) -> pd.DataFrame:
    ok = np.isfinite(sub["y"].to_numpy(np.float64)) & np.isfinite(sub[ad].to_numpy(np.float64)) & \
        np.isfinite(sub[ref].to_numpy(np.float64))
    return sub[ok]


def _engine_match(run: Run, L: int, basis: str, v: str, rec: Dict[str, Any]) -> Dict[str, Any]:
    """For the ALL line: does this script reproduce the engine's own verdict record?"""
    if v != ALL:
        return {"engine_tag": "", "engine_mean": float("nan"), "engine_se": float("nan"), "matches_engine": ""}
    if L == 0 and basis == "all":
        ev = run.verdict["verdict"]
    else:
        ev = (run.ladder.get("verdicts") or {}).get(str(L))
    if not ev:
        return {"engine_tag": "absent", "engine_mean": float("nan"), "engine_se": float("nan"),
                "matches_engine": ""}
    em, es = float(ev["contrast"]["mean"]), ev["contrast"]["se"]
    es = float("nan") if es is None else float(es)
    same = str(ev["tag"]) == rec["tag"] and math.isclose(em, rec["mean"], rel_tol=1e-9, abs_tol=1e-9) and \
        ((math.isnan(es) and math.isnan(rec["se"])) or math.isclose(es, rec["se"], rel_tol=1e-9, abs_tol=1e-9))
    return {"engine_tag": str(ev["tag"]), "engine_mean": em, "engine_se": es, "matches_engine": bool(same)}


def magnitude_table(run: Run, common: set, values: List[str], edges: Dict[int, Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for L, basis, frame in _bases(run, common):
        y = frame["y"].to_numpy(np.float64)
        b = np.full(y.size, "(no label)", dtype=object)
        ok = np.isfinite(y)
        b[ok] = magnitude_bin(y[ok], edges[L])
        frame = frame.assign(_bin=b)
        for v, sub in _subsets(run, frame, values):
            n_value = int(np.isfinite(sub["y"].to_numpy(np.float64)).sum())
            n_only = v != ALL and n_value < MIN_ROWS_FOR_METRICS
            for bn in BIN_ORDER:
                bs = sub[sub["_bin"] == bn].reset_index(drop=True)
                for c in pred_columns(frame):
                    rec = {"lead": L, "rows_basis": basis, "stratum_column": run.stratum, "stratum_value": v,
                           "bin": bn, "label": "a target-defined diagnostic, not a headline", "column": c,
                           "column_kind": column_kind(c), "adopted": c == run.adopted[L], "n_value_rows": n_value}
                    r = line(bs, c, run.tol[L], n_only)
                    rec.update({k: r[k] for k in ("n", "n_groups", "mean_y", "mean_pred", "mae", "mae_predict_zero",
                                                  "mae_donor_median", "n_only")})
                    rows.append(rec)
    return pd.DataFrame(rows)


def flattening_table(run: Run, common: set, values: List[str], edges: Dict[int, Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for L, basis, frame in _bases(run, common):
        roles = edge_roles()
        for rule in (EDGE_PRIMARY, EDGE_POSITIVE):
            edge = float(edges[L][rule])
            y = frame["y"].to_numpy(np.float64)
            sev = np.isfinite(y) & (y >= edge)
            fs = frame[sev].reset_index(drop=True)
            for v, sub in _subsets(run, fs, values):
                n_value = int(len(sub))
                n_only = v != ALL and n_value < MIN_ROWS_FOR_METRICS
                for c in pred_columns(frame):
                    p = sub[c].to_numpy(np.float64)
                    yy = sub["y"].to_numpy(np.float64)
                    ok = np.isfinite(p)
                    n = int(ok.sum())
                    obs = float(np.mean(yy[ok])) if n else float("nan")
                    mp = float(np.mean(p[ok])) if n else float("nan")
                    if n_only:
                        obs = mp = float("nan")
                    rows.append({"lead": L, "rows_basis": basis, "edge_rule": rule,
                                 "edge_role": roles[rule], "is_default": rule == EDGE_DEFAULT,
                                 "edge": edge, "edge_is_zero": edge == 0,
                                 "stratum_column": run.stratum, "stratum_value": v, "column": c,
                                 "column_kind": column_kind(c), "adopted": c == run.adopted[L],
                                 "n_severe_value_rows": n_value, "n": n, "observed_mean": obs, "mean_pred": mp,
                                 "mean_pred_minus_observed": mp - obs, "ratio_pred_to_observed":
                                 (mp / obs) if (n and obs != 0 and not n_only) else float("nan"),
                                 "n_only": n_only, "label": "report only, never a choice"})
    return pd.DataFrame(rows)


def per_year_macro(run: Run, common: set) -> pd.DataFrame:
    rows = []
    for L, basis, frame in _bases(run, common):
        years = sorted(int(x) for x in frame["year"].dropna().unique())
        for c in pred_columns(frame):
            base = {"lead": L, "rows_basis": basis, "column": c, "column_kind": column_kind(c),
                    "adopted": c == run.adopted[L]}
            for yr in years:
                r = line(frame[frame["year"] == yr].reset_index(drop=True), c, run.tol[L])
                rows.append(dict(base, line="year", year=yr, **_pick(r)))
            r = line(frame, c, run.tol[L])
            rows.append(dict(base, line="pooled", year=None, **_pick(r)))
            gm = []
            for g in sorted(frame["group"].astype(str).unique()):
                rg = line(frame[frame["group"].astype(str) == g].reset_index(drop=True), c, run.tol[L])
                if rg["n"]:
                    gm.append((rg["mae"], rg["mae_predict_zero"], rg["mae_donor_median"]))
            arr = np.asarray(gm, dtype=np.float64) if gm else np.full((0, 3), np.nan)
            rows.append(dict(base, line="macro_over_groups", year=None, n=int(r["n"]), n_groups=len(gm),
                             mae=float(np.mean(arr[:, 0])) if len(gm) else float("nan"),
                             mae_predict_zero=float(np.mean(arr[:, 1])) if len(gm) else float("nan"),
                             mae_donor_median=float(np.mean(arr[:, 2])) if len(gm) else float("nan"),
                             corr2=float("nan"), hit=float("nan")))
    return pd.DataFrame(rows)


def _pick(r: Dict[str, Any]) -> Dict[str, Any]:
    return {k: r[k] for k in ("n", "n_groups", "mae", "mae_predict_zero", "mae_donor_median", "corr2", "hit")}


def per_ecoregion(run: Run, values: List[str]) -> pd.DataFrame:
    """n, zero share and programme mix per scored group, sorted by name; never ranked by MAE."""
    rows = []
    for L in run.leads:
        p = run.preds[L]
        y = p["y"].to_numpy(np.float64)
        sv = _sv(p[run.stratum])
        for g in sorted(p["group"].astype(str).unique()):
            m = (p["group"].astype(str) == g).to_numpy()
            ok = m & np.isfinite(y)
            rec = {"lead": L, "group": g, "n": int(ok.sum()),
                   "zero_share": float(np.mean(y[ok] == 0)) if ok.any() else float("nan")}
            for v in values:
                rec["n_%s" % v] = int((ok & (sv == v)).sum())
            rows.append(rec)
    return pd.DataFrame(rows)


# =============================================================================================== counts
def _arm_records(arms: Any) -> List[Tuple[str, str, Dict[str, Any]]]:
    out = []
    for arm, parts in (arms or {}).items():
        for part, rec in (parts or {}).items():
            if isinstance(rec, dict):
                out.append((str(arm), str(part), rec))
    return out


def counts_no_tree(run: Run) -> pd.DataFrame:
    f = run.folder
    sources = [("decision_surface", 0, run.r.json(f / "decision_checks.json").get("neighbour", {}).get("arms")),
               ("test_pass", 0, run.r.json(f / "test_pass_router.json")["records"].get("neighbour", {}).get("arms"))]
    for L in run.leads[1:]:
        lj = run.lead_json[L]
        sources.append(("guard", L, ((lj.get("guard") or {}).get("router") or {}).get("neighbour", {}).get("arms")))
        sources.append(("test_pass", L, ((lj.get("test") or {}).get("router") or {}).get("neighbour", {}).get("arms")))
    rows = []
    for pas, L, arms in sources:
        agg: Dict[str, Dict[str, int]] = {}
        for arm, part, rec in _arm_records(arms):
            a = agg.setdefault(arm, {"parts": 0, "n_rows": 0, "n_rows_no_tree": 0, "n_rows_pool_fallback": 0})
            a["parts"] += 1
            a["n_rows"] += int(rec.get("n_rows") or 0)
            a["n_rows_no_tree"] += int(rec.get("n_rows_no_tree") or 0)
            a["n_rows_pool_fallback"] += int(rec.get("n_rows_pool_fallback") or 0)
        for arm in sorted(agg):
            a = agg[arm]
            rows.append({"pass": pas, "lead": L, "arm": arm, "parts": a["parts"], "n_rows": a["n_rows"],
                         "n_rows_no_tree": a["n_rows_no_tree"],
                         "share_no_tree": a["n_rows_no_tree"] / a["n_rows"] if a["n_rows"] else float("nan"),
                         "n_rows_pool_fallback_record": a["n_rows_pool_fallback"]})
    return pd.DataFrame(rows)


def _pool_files(run: Run) -> List[Tuple[str, int, Path]]:
    f = run.folder
    files = [("decision_surface", 0, f / "pools_decision_surface.parquet"), ("test_pass", 0, f / "pools_test_pass.parquet")]
    for L in run.leads[1:]:
        d = f / "ladder" / ("lead_%d" % L)
        files += [("guard", L, d / "pools_guard.parquet"), ("test_pass", L, d / "pools_test_pass.parquet")]
    return files


def counts_pool_fallback(run: Run, no_tree: pd.DataFrame) -> pd.DataFrame:
    f = run.folder
    rows = []
    for pas, L, path in _pool_files(run):
        t = run.r.parquet(path, columns=["row_id", "pool_fallback"])
        nfb = int(t["pool_fallback"].astype(bool).sum())
        sel = no_tree[(no_tree["pass"] == pas) & (no_tree["lead"] == L)] if len(no_tree) else no_tree
        rec_vals = sorted(set(int(x) for x in sel["n_rows_pool_fallback_record"])) if len(sel) else []
        rec_rows = sorted(set(int(x) for x in sel["n_rows"])) if len(sel) else []
        rows.append({"pass": pas, "lead": L, "pools_file": path.relative_to(f).as_posix(), "rows": int(len(t)),
                     "rows_pool_fallback": nfb, "share_pool_fallback": nfb / len(t) if len(t) else float("nan"),
                     "record_rows_pool_fallback": ";".join(str(x) for x in rec_vals),
                     "record_rows": ";".join(str(x) for x in rec_rows),
                     "matches_record": (rec_vals == [nfb] and rec_rows == [int(len(t))]) if rec_vals else ""})
    return pd.DataFrame(rows)


def counts_left_out(run: Run) -> pd.DataFrame:
    f = run.folder
    rows = []
    for L in run.leads[1:]:
        lj = run.lead_json[L]
        im = lj.get("issue_features_missing") or {}
        path = f / "ladder" / ("lead_%d" % L) / "issue_missing_rows.parquet"
        n_file = int(len(run.r.parquet(path, columns=["unit"]))) if path.is_file() else 0
        rows.append({"what": "H4 test rows absent at the lead (left out of scoring)", "lead": L, "source":
                     "lead.json issue_features_missing / issue_missing_rows.parquet",
                     "rows_record": int(im.get("rows_left_out") or 0), "rows_file": n_file})
    cm = f / "context_missing"
    if cm.is_dir():
        for path in sorted(cm.glob("*.parquet")):
            t = run.r.parquet(path)
            purposes = t["purpose"].astype(str) if "purpose" in t.columns else pd.Series(["?"] * len(t))
            for pur in sorted(set(purposes.tolist())) or ["(none)"]:
                n = int((purposes == pur).sum())
                rows.append({"what": "S1/G1 rows with missing router context, left out", "lead":
                             int(t["lead"].iloc[0]) if len(t) and "lead" in t.columns else None,
                             "source": "context_missing/%s (%s)" % (path.name, pur), "rows_record": n,
                             "rows_file": n})
    return pd.DataFrame(rows)


# =============================================================================================== saved records
# Draft 6.1 ("Per lead") and 6.2 items 1 and 6. Each fact is read from the file the engine saved it in. A fact the
# engine does not save is printed as NOT_SAVED ('not saved by the engine'); nothing is rebuilt from engine internals.
def _point(doc: Any) -> Optional[Tuple[float, Optional[float]]]:
    """A saved penalty point {level, ratio} as a tuple; None when the record holds no point."""
    if not doc:
        return None
    r = doc.get("ratio")
    return (float(doc["level"]), None if r is None else float(r))


def _point_text(p: Optional[Tuple[float, Optional[float]]]) -> str:
    return "" if p is None else "level %r ratio %r" % (p[0], p[1])


def edge_axes(point: Tuple[float, Optional[float]], grid: Sequence[Tuple[float, Optional[float]]]
              ) -> Dict[str, Optional[str]]:
    """The engine's edge rule (layer/decide.py:214-229) applied to a SAVED pick and the SAVED grid: per axis 'top',
    'bottom' or None; an axis with fewer than two distinct values has no edge. A lookup, not a pick."""
    pts = list(grid)
    if point not in pts:
        refuse("the saved pick %r is not a point of the saved grid" % (point,))
    out: Dict[str, Optional[str]] = {"level": None, "ratio": None}
    levels = sorted({q[0] for q in pts})
    if len(levels) > 1:
        out["level"] = "top" if point[0] == levels[-1] else ("bottom" if point[0] == levels[0] else None)
    ratios = sorted({q[1] for q in pts if q[1] is not None})
    if len(ratios) > 1 and point[1] is not None:
        out["ratio"] = "top" if point[1] == ratios[-1] else ("bottom" if point[1] == ratios[0] else None)
    return out


def _edge_text(ax: Dict[str, Optional[str]]) -> str:
    """The engine's printed form (decide.py:1095-1098): 'level bottom, ratio bottom'; '' when not at an edge."""
    return ", ".join("%s %s" % (a, ax[a]) for a in ("level", "ratio") if ax.get(a))


_LOG_HEAD = re.compile(r"^\[[^\]]*\] decision surface: (\d+) rows, (\d+) candidates")
_LOG_PICK = re.compile(r"^\[[^\]]*\]\s+(?P<arm>\S+)\s+MAE (?P<mae>\S+) at (?:no grid|level (?P<level>\S+) ratio "
                       r"(?P<ratio>\S+))(?: \| EDGE PICK: (?P<edge>[^|]+?))? \| pre-clip ")
_LOG_END = re.compile(r"^\[[^\]]*\]\s+predict-zero MAE ")


def log_blocks(text: str) -> int:
    """The number of decision blocks ('decision surface: ...' header lines, decide.py:1086) in run.log."""
    return sum(1 for raw in text.splitlines() if _LOG_HEAD.match(raw))


def log_picks(text: str) -> List[Dict[str, Any]]:
    """The per-arm penalty picks the engine PRINTS in run.log (decide.py:1084-1098, one block per decision surface).
    Only the printed text is read; trees-off lines ('no grid') carry no penalty and are skipped."""
    out: List[Dict[str, Any]] = []
    block = 0
    inside = False
    for raw in text.splitlines():
        if _LOG_HEAD.match(raw):
            block += 1
            inside = True
            continue
        if not inside:
            continue
        if _LOG_END.match(raw):
            inside = False
            continue
        m = _LOG_PICK.match(raw)
        if m is None or m.group("level") is None:
            continue
        ratio = m.group("ratio")
        out.append({"block": block, "arm": m.group("arm"), "surface_mae": float(m.group("mae")),
                    "point": (float(m.group("level")), None if ratio == "None" else float(ratio)),
                    "printed_edge": (m.group("edge") or "").strip()})
    return out


def penalty_edge_picks(run: Run) -> pd.DataFrame:
    """Draft 3.6 and 6.2 item 6: picks at the penalty grid's edge (flagged, never extended). The saved picks
    (adoption.json, adoption_lead_<L>.json) are looked up against the saved grid (adoption.json decision.grid) with
    the engine's own edge rule; each arm's pick is read from the engine's printed decision lines in run.log, the only
    place the engine keeps it."""
    f = run.folder
    ad = run.r.json(f / "adoption.json")
    grid_doc = (ad.get("decision") or {}).get("grid")
    if not grid_doc:
        refuse("adoption.json holds no decision.grid, so no pick can be placed on the penalty grid")
    grid = [_point(g) for g in grid_doc]
    rows: List[Dict[str, Any]] = []

    def add(source: str, lead: int, arm: str, p: Optional[Tuple[float, Optional[float]]], printed: Any = None,
            note: str = "") -> None:
        rec = {"source": source, "lead": lead, "arm": arm, "point": _point_text(p), "level": p[0] if p else float("nan"),
               "ratio": (p[1] if p[1] is not None else float("nan")) if p else float("nan"),
               "edge_level": "", "edge_ratio": "", "at_edge": "", "engine_printed_edge": "",
               "matches_engine_print": "", "note": note}
        if p is not None:
            ax = edge_axes(p, grid)
            rec.update({"edge_level": ax["level"] or "", "edge_ratio": ax["ratio"] or "",
                        "at_edge": bool(ax["level"] or ax["ratio"])})
            if printed is not None:
                rec["engine_printed_edge"] = printed
                rec["matches_engine_print"] = printed == _edge_text(ax)
        rows.append(rec)

    adopted = str(run.verdict.get("adopted") or "")
    add("adoption.json penalty (the adopted pick)", 0, adopted, _point(ad.get("penalty")),
        note="" if ad.get("penalty") else "no penalty point: the layer declined (or a trees-off arm was adopted)")
    best = str(run.verdict.get("best_tree_arm") or "")
    add("adoption.json best_tree_penalty", 0, best, _point(ad.get("best_tree_penalty")))
    for L in run.leads[1:]:
        lj = run.lead_json[L]
        name = str(lj.get("adoption_file") or "adoption_lead_%d.json" % L)
        al = run.r.json(f / name)
        add("%s penalty (the pinned arm at the lead)" % name, L, str(lj.get("pinned") or ""), _point(al.get("penalty")))
    for pk in checked_log_picks(run, ad):
        note = "decision block %d; MAE %r as printed, checked against adoption.json surface_mae" % (pk["block"],
                                                                                                  pk["surface_mae"])
        if pk["arm"] == best:
            note += "; same point as the saved best_tree_penalty (checked)"
        add("run.log (the engine's printed decision line)", 0, pk["arm"], pk["point"], pk["printed_edge"], note)
    return pd.DataFrame(rows)


def checked_log_picks(run: Any, ad: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """The per-arm picks printed in run.log, each checked against the saved adoption.json. The engine always writes
    run.log and prints one decision block per run (decide.py:1078-1099), so every gap is a refusal:
    run.log absent; not exactly one decision block; no parsed line; the parsed arms differ from the tree arms of
    decision.candidate_order (trees-off and missing arms left out); a printed MAE differs from surface_mae at the printed
    point by more than the %.6f rounding; the best tree arm's printed point differs from best_tree_penalty."""
    log = run.folder / "run.log"
    if not log.is_file():
        refuse("run.log is absent: the engine always writes it, and each arm's penalty pick is printed only there "
               "(decide.py:1078-1099)")
    text = run.r.text(log)
    heads = log_blocks(text)
    if heads != 1:
        refuse("run.log holds %d decision blocks; one is expected (decide.py:1086)" % heads)
    picks = log_picks(text)
    if not picks:
        refuse("run.log holds a decision block but no parsed per-arm line (decide.py:1096-1099 format)")
    dec = ad.get("decision") or {}
    missing_arms = set(str(a) for a in (dec.get("missing_arms") or []))
    want = sorted(str(a) for a in (dec.get("candidate_order") or [])
                  if "_trees_off" not in str(a) and str(a) not in missing_arms)
    got = sorted(pk["arm"] for pk in picks)
    if got != want:
        refuse("run.log's parsed tree arms %s differ from adoption.json decision.candidate_order's tree arms %s"
               % (got, want))
    surface = ad.get("surface_mae") or {}
    for pk in picks:
        sm = _surface_lookup(surface, pk["arm"], pk["point"])
        if not math.isfinite(sm):
            refuse("adoption.json surface_mae holds no entry for %s at %s (printed in run.log)"
                   % (pk["arm"], _point_text(pk["point"])))
        if abs(sm - pk["surface_mae"]) > LOG_MAE_TOL:
            refuse("run.log prints MAE %r for %s at %s; adoption.json surface_mae holds %r"
                   % (pk["surface_mae"], pk["arm"], _point_text(pk["point"]), sm))
    best = str(run.verdict.get("best_tree_arm") or "")
    saved_best = _point(ad.get("best_tree_penalty"))
    if best and saved_best is not None:
        bp = [pk for pk in picks if pk["arm"] == best]
        if len(bp) != 1:
            refuse("run.log prints %d lines for the best tree arm %s; one is expected" % (len(bp), best))
        if bp[0]["point"] != saved_best:
            refuse("run.log prints the best tree arm %s at %s; adoption.json best_tree_penalty is %s"
                   % (best, _point_text(bp[0]["point"]), _point_text(saved_best)))
    return picks


def _surface_lookup(surface: Mapping[str, Any], name: str, point: Optional[Tuple[float, Optional[float]]]) -> float:
    """adoption.json surface_mae: keys 'arm@level=X,ratio=Y' for a tree arm, the bare name without a grid."""
    for k, v in surface.items():
        arm, _, rest = str(k).partition("@")
        if arm != name:
            continue
        if point is None and not rest:
            return float(v)
        if point is not None and rest:
            kv = dict(x.split("=", 1) for x in rest.split(","))
            r = kv.get("ratio")
            if (float(kv["level"]), None if r in (None, "None") else float(r)) == point:
                return float(v)
    return float("nan")


def guard_reference(run: Run) -> pd.DataFrame:
    """Draft 6.1 'Per lead' (ruling V1): the guard reference and the decline object, with the pinned arm's
    guard-surface MAE and the reference's MAE side by side. Leads: lead.json guard.* and test.decline_target.
    Nowcast: decision_checks.json / adoption.json decline_baseline and adoption.json surface_mae."""
    f = run.folder
    rows = []
    ad = run.r.json(f / "adoption.json")
    dc = run.r.json(f / "decision_checks.json")
    db = dc.get("decline_baseline") or {}
    dd = (ad.get("decision") or {}).get("decline_baseline") or {}
    if db and dd and (str(db.get("key")) != str(dd.get("key")) or
                      not math.isclose(float(db["mae"]), float(dd["mae"]), rel_tol=1e-12, abs_tol=1e-12)):
        refuse("decision_checks.json and adoption.json hold different decline baselines: %r vs %r" % (db, dd))
    surface = ad.get("surface_mae") or {}
    best = str(run.verdict.get("best_tree_arm") or "")
    bp = _point(run.verdict.get("best_tree_penalty"))
    link = str((ad.get("best_tree_arm") or {}).get("link") or "")
    off = [k for k in surface if "@" not in str(k) and link and str(k).startswith(link + "_trees_off")]
    pinned_mae = _surface_lookup(surface, best, bp)
    ref_mae = float(db["mae"]) if db.get("mae") is not None else float("nan")
    if run.verdict.get("decline_target"):
        # V1: the engine always saves the decline baseline and the best tree arm's surface MAE (fail loud)
        if not db or db.get("mae") is None:
            refuse("verdict.json names a decline target (%r) but decision_checks.json holds no decline_baseline MAE"
                   % run.verdict.get("decline_target"))
        if not math.isfinite(pinned_mae):
            refuse("adoption.json surface_mae holds no entry for the best tree arm %r at %s"
                   % (best, _point_text(bp)))
    per_fold = db.get("per_fold_median") or {}
    rows.append({"lead": 0, "surface": "decision surface (nowcast N2 check)", "surface_rows": dc.get("surface_rows"),
                 "bank_cut": None, "reference_column": db.get("key", ""), "reference_value": float("nan"),
                 "reference_value_text": "per fold: " + "; ".join("%s=%r" % (g, per_fold[g]) for g in sorted(per_fold))
                 if per_fold else NOT_SAVED, "reference_donor_rows": float("nan"), "reference_mae": ref_mae,
                 "pinned_arm": best, "pinned_point": _point_text(bp), "pinned_mae": pinned_mae,
                 "pinned_minus_reference": pinned_mae - ref_mae,
                 "own_trees_off_mae": float(surface[off[0]]) if len(off) == 1 else float("nan"),
                 "passed": not run.declined[0], "decline_target": run.verdict.get("decline_target", ""),
                 "guard_and_decline_one_object": str(db.get("key", "")) == str(run.verdict.get("decline_target", "")),
                 "adopted_column": run.adopted[0], "declined": run.declined[0],
                 "not_saved": "reference_value (one median per fold, not one value); reference_donor_rows",
                 "source": "decision_checks.json decline_baseline; adoption.json surface_mae, best_tree_penalty"})
    for L in run.leads[1:]:
        lj = run.lead_json[L]
        g = lj.get("guard") or {}
        t = lj.get("test") or {}
        missing = [k for k in ("baseline_column", "baseline_value", "baseline_donor_rows", "baseline_mae",
                               "pinned_mae", "own_trees_off_mae", "passed") if g.get(k) is None]
        if t.get("decline_target"):
            # V1: the engine always writes these fields (table_ladder.py:356-357, :368-371)
            if missing:
                refuse("lead %d: the guard record (lead.json guard) lacks %s although the lead names a decline "
                       "target (%r)" % (L, missing, t.get("decline_target")))
            if bool(g["passed"]) != (not run.declined[L]):
                refuse("lead %d: lead.json guard.passed is %r but declined_at_lead is %r (table_ladder.py:548, :558)"
                       % (L, g["passed"], run.declined[L]))

        def num(k: str) -> float:
            v = g.get(k)
            return float(v) if v is not None else float("nan")

        rows.append({"lead": L, "surface": "lead guard surface (H2)", "surface_rows": g.get("surface_rows"),
                     "bank_cut": g.get("bank_cut"), "reference_column": g.get("baseline_column", ""),
                     "reference_value": num("baseline_value"), "reference_value_text": "",
                     "reference_donor_rows": num("baseline_donor_rows"), "reference_mae": num("baseline_mae"),
                     "pinned_arm": str(lj.get("pinned") or ""), "pinned_point": _point_text(_point(lj.get("penalty"))),
                     "pinned_mae": num("pinned_mae"), "pinned_minus_reference": num("pinned_mae") - num("baseline_mae"),
                     "own_trees_off_mae": num("own_trees_off_mae"), "passed": g.get("passed"),
                     "decline_target": t.get("decline_target", ""),
                     "guard_and_decline_one_object": str(g.get("baseline_column", "")) == str(t.get("decline_target", "")),
                     "adopted_column": run.adopted[L], "declined": run.declined[L],
                     "not_saved": ";".join(missing), "source": "ladder/lead_%d/lead.json guard.*, test.decline_target" % L})
    return pd.DataFrame(rows)


ROW_SETS = (("donor", "donor rows at the lead's fit cut"), ("scored", "scored test rows (finite label)"))


def r30_missing(run: Any) -> pd.DataFrame:
    """Draft 3.8 and 6.2 item 6: the R30 0-filled share of every tree column and the marine-heatwave NaN rows.
    Saved by the engine once (derived.json R30, derive/table.py:251-266, unit_rules.py:595-603): per tree column, the
    share missing before the 0-fill on the donor rows at the lead-0 fit cut, and per test year on the lead-0 table's
    rows. Not saved: the shares at leads 183 and 365, and any count of marine-heatwave NaN rows. Those are COUNTED here
    from the lead tables (the run's recorded tables, SHA-256 checked), on each lead's donor rows and scored rows, and
    labelled 'counted from the lead table (not an engine record)'. At lead 0 the counted donor-row share of every
    tree column must equal R30 filled_share, or the script refuses."""
    rows: List[Dict[str, Any]] = []
    r30 = run.derived.get("R30")
    if not isinstance(r30, dict):
        refuse("derived.json has no R30 record (the engine writes it for every table run, derive/table.py:251-266)")
    inp = r30.get("inputs") or {}
    filled = inp.get("filled_share") or {}
    zeros = inp.get("real_zero_share") or {}
    by_year = inp.get("test_year_missing_share") or {}
    thr = (inp.get("constants") or {}).get("C15.missing_flag_share")
    if thr is None:
        refuse("derived.json R30 records no C15.missing_flag_share")
    thr = float(thr)
    flags = r30.get("value") or {}
    for c in sorted(filled):
        rec = {"lead": 0, "what": "0-filled share (R30), donor rows at the lead-0 fit cut", "rows_set": ROW_SETS[0][1],
               "column": c, "marine_heatwave": c.startswith(MHW_PREFIX), "tree_column": True,
               "filled_share": float(filled[c]),
               "real_zero_share": float(zeros[c]) if c in zeros else float("nan"), "flag_threshold": thr,
               "over_threshold": float(filled[c]) > thr, "engine_flags": ";".join(flags.get(c) or []),
               "status": "saved: derived.json R30"}
        for yr, s in sorted((by_year.get(c) or {}).items()):
            rec["test_year_missing_share_%s" % yr] = float(s)
        rows.append(rec)
    mhw_tree = [c for c in filled if c.startswith(MHW_PREFIX)]
    rows.append({"lead": 0, "what": "largest 0-filled share over the marine-heatwave tree columns (%s*), donor rows"
                 % MHW_PREFIX, "rows_set": ROW_SETS[0][1], "column": "(%d marine-heatwave columns)" % len(mhw_tree),
                 "marine_heatwave": True, "tree_column": True,
                 "filled_share": max(float(filled[c]) for c in mhw_tree) if mhw_tree else float("nan"),
                 "status": "saved: the largest of the per-column shares above" if mhw_tree
                 else "no %s* column in derived.json R30" % MHW_PREFIX})
    cols, mhw = list(run.feature_columns), list(run.mhw_columns)
    missing_r30 = [c for c in filled if c not in cols]
    if missing_r30:
        refuse("R30 columns %s were not read from the lead tables" % missing_r30[:5])
    for L in run.leads:
        for which, label in ROW_SETS:
            f = run.feature_frame(L, which)
            n = int(len(f))
            nan = f.isna() if n else pd.DataFrame({c: np.zeros(0, bool) for c in cols})
            for c in cols:
                k = int(nan[c].sum()) if c in nan.columns else 0
                share = k / n if n else float("nan")
                status = COUNTED
                saved = float("nan")
                if L == 0 and which == "donor" and c in filled:
                    saved = float(filled[c])
                    if not (n and math.isclose(share, saved, rel_tol=0.0, abs_tol=1e-12)):
                        refuse("lead 0: the NaN share of %s on the %d donor rows, counted from the lead table, is %r; "
                               "derived.json R30 filled_share is %r" % (c, n, share, saved))
                    status = COUNTED + "; equals derived.json R30 filled_share (checked)"
                rows.append({"lead": L, "what": "NaN share before the 0-fill (R30 measure), per column",
                             "rows_set": label, "column": c, "marine_heatwave": c.startswith(MHW_PREFIX),
                             "tree_column": c in filled, "n_rows": n, "n_nan": k, "nan_share": share,
                             "r30_saved_share": saved, "flag_threshold": thr,
                             "over_threshold": bool(n) and share > thr, "status": status})
            if mhw:
                k_any = int(nan[mhw].any(axis=1).sum()) if n else 0
                st_any = COUNTED
            else:
                k_any, st_any = float("nan"), "no %s* column in the catalog or derived.json R30" % MHW_PREFIX
            rows.append({"lead": L, "what": "rows with a NaN in any marine-heatwave column (count)", "rows_set": label,
                         "column": "(%d %s* columns)" % (len(mhw), MHW_PREFIX), "marine_heatwave": True,
                         "n_rows": n, "n_nan": k_any,
                         "nan_share": (k_any / n) if (n and mhw) else float("nan"), "status": st_any})
            if MHW_DAYS in cols:
                k_days = int(nan[MHW_DAYS].sum()) if n else 0
                st_days = COUNTED + "; NaN exactly when under 60 thresholded days (build_tables.py:315)"
            else:
                k_days, st_days = float("nan"), "no %s column in the catalog or derived.json R30" % MHW_DAYS
            rows.append({"lead": L, "what": "rows with a NaN in %s (under 60 thresholded days; count)" % MHW_DAYS,
                         "rows_set": label, "column": MHW_DAYS, "marine_heatwave": True, "n_rows": n,
                         "n_nan": k_days, "nan_share": (k_days / n) if (n and MHW_DAYS in cols) else float("nan"),
                         "status": st_days})
    return pd.DataFrame(rows)


def load_month_precision_rows(reader: Reader, path: Path) -> set:
    """The data builder's month-precision list (coral_data/month_precision_rows.csv, build_visits.py:295-297; NOT an
    engine file): its row_id column. Its SHA-256 goes into inputs_manifest.json."""
    if not path.is_file():
        refuse("the month-precision list %s does not exist" % path)
    reader._note(path)
    t = pd.read_csv(path, dtype=str)
    if "row_id" not in t.columns:
        refuse("the month-precision list %s has no row_id column" % path)
    return set(t["row_id"].dropna().astype(str).tolist())


def month_precision_ids(reader: Reader, run: Any, given: Optional[Any], toy: bool) -> Tuple[Optional[set], str]:
    """Which month-precision list is read. A toy run without --month-precision-rows: none (the count prints 'not
    saved by the engine'). A non-toy run: the given file or, without one, MONTH_PRECISION_LIST; either way its
    SHA-256 must equal MONTH_PRECISION_SHA256. Every listed row id must be a row of the lead-0 table
    (build_visits.py:295 lists only rows present at lead 0), so a row-id format mismatch cannot print 0 silently."""
    if given is None and toy:
        return None, ""
    path = Path(given if given is not None else MONTH_PRECISION_LIST).resolve()
    ids = load_month_precision_rows(reader, path)
    sha = reader.read[str(path)]
    if not toy and sha != MONTH_PRECISION_SHA256:
        refuse("the month-precision list %s has SHA-256 %s; the pinned list (MONTH_PRECISION_SHA256) is %s"
               % (path, sha, MONTH_PRECISION_SHA256))
    absent = sorted(ids - set(run.tables[0]["row_id"].astype(str).tolist()))
    if absent:
        refuse("%d listed month-precision row ids are not rows of the lead-0 table (e.g. %s)" % (len(absent),
                                                                                              absent[:3]))
    return ids, "%s (SHA-256 %s)" % (path, sha[:16])


def _ids(cell: Any) -> List[str]:
    if isinstance(cell, str):
        return [str(x) for x in json.loads(cell)]
    return [str(x) for x in list(cell)]


def pools_month_precision(run: Run, mp_ids: Optional[set], mp_source: str = "") -> pd.DataFrame:
    """Draft 6.2 item 6: pools holding a month-precision row (exceptions.yaml:91-96). The engine saves every pool
    (pools_<pass>.parquet, pool_row_ids) but no month-precision flag: the lead tables carry no precision column and no
    run record counts them. The count uses the builder's pinned list (month_precision_ids); only a toy run without a
    list prints NOT_SAVED."""
    rows = []
    for pas, L, path in _pool_files(run):
        rec = {"pass": pas, "lead": L, "pools_file": path.relative_to(run.folder).as_posix()}
        if mp_ids is None:
            t = run.r.parquet(path, columns=["row_id"])
            rec.update({"pools": int(len(t)), "pools_holding_month_precision_row": float("nan"),
                        "share_pools_holding": float("nan"), "distinct_month_precision_rows_in_pools": float("nan"),
                        "status": NOT_SAVED + ": no month-precision flag in the lead tables or the run records"})
        else:
            t = run.r.parquet(path, columns=["row_id", "pool_row_ids"])
            hold, seen = 0, set()
            for cell in t["pool_row_ids"].tolist():
                hit = mp_ids.intersection(_ids(cell))
                hold += bool(hit)
                seen |= hit
            rec.update({"pools": int(len(t)), "pools_holding_month_precision_row": hold,
                        "share_pools_holding": hold / len(t) if len(t) else float("nan"),
                        "distinct_month_precision_rows_in_pools": len(seen),
                        "status": "counted from the saved pools and the builder's list %s (not an engine record)"
                        % mp_source})
        rows.append(rec)
    return pd.DataFrame(rows)


def blocked_jackknife(per_group: Mapping[str, float], block_of_group: Mapping[str, int]) -> Dict[str, float]:
    """The engine's report-only blocked jackknife (metrics.py:1058-1077): each overlap block's value is the mean of
    its groups' values, blocks in index order, then the group jackknife over the block values."""
    absent = sorted(g for g in per_group if g not in block_of_group)
    if absent:
        refuse("groups without an overlap block (derived.json R14:overlap_blocks): %s" % absent[:5])
    members: Dict[int, List[float]] = {}
    for g in sorted(per_group):
        members.setdefault(int(block_of_group[g]), []).append(float(per_group[g]))
    jk = jackknife(np.asarray([float(np.mean(members[b])) for b in sorted(members)], dtype=np.float64))
    return {"mean": jk["mean"], "se": jk["se"], "low": jk["low"], "high": jk["high"], "n_blocks": jk["n_groups"]}


def blocked_flag(group_se: float, blocked_se: float) -> bool:
    """metrics.py:1080-1087: 'group jackknife may be too narrow' when the blocked SE is more than C10.borderline_share
    above the group SE; False when either SE is undefined."""
    if not (math.isfinite(group_se) and math.isfinite(blocked_se)):
        return False
    return blocked_se > (1.0 + BORDERLINE_SHARE) * group_se


def programme_blocked_jackknife(run: Run, common: set, values: List[str]) -> pd.DataFrame:
    """Draft 6.2 item 1 and section 8: the blocked jackknife per programme, report only. The engine saves it once,
    over all groups at the nowcast (verdict.json blocked_jackknife); per programme and at the leads it is not saved.
    Here it is computed from the saved rows and the saved blocks (derived.json R14:overlap_blocks) by the engine's
    rule; the ALL line at the nowcast must equal verdict.json, or the script refuses."""
    bog = {str(g): int(b) for g, b in run.derived["R14:overlap_blocks"]["value"]["block_of_group"].items()}
    saved = run.verdict.get("blocked_jackknife")
    rows = []
    plan = [(0, "all")] + [(L, "common") for L in run.leads]
    for L, basis in plan:
        frame = run.frame(L, basis, common)
        ad, ref = run.adopted[L], run.reference
        for v, sub in _subsets(run, frame, values):
            s = _scored_subset(sub, ad, ref)
            groups, dv = _group_contrasts(s, ad, ref)
            gj = jackknife(np.asarray(dv, dtype=np.float64))
            if groups:
                bj = blocked_jackknife(dict(zip(groups, dv)), bog)
            else:
                bj = {"mean": float("nan"), "se": float("nan"), "low": float("nan"), "high": float("nan"),
                      "n_blocks": 0}
            flag = blocked_flag(gj["se"], bj["se"])
            rec = {"lead": L, "rows_basis": basis, "stratum_column": run.stratum, "stratum_value": v,
                   "label": "report only; the group jackknife decides (D74)", "adopted_column": ad,
                   "reference_column": ref, "declined": run.declined[L], "n_rows": int(len(s)), "n_groups": len(groups),
                   "blocks": ";".join(str(b) for b in sorted({bog[g] for g in groups})),
                   "group_se": gj["se"], "flag": "group jackknife may be too narrow" if flag else ""}
            rec.update({k: bj[k] for k in ("mean", "se", "low", "high", "n_blocks")})
            if v == ALL and L == 0 and basis == "all":
                if not saved:
                    refuse("verdict.json records no blocked_jackknife, so the ALL line cannot be checked")
                es = saved.get("se")
                es = float("nan") if es is None else float(es)
                same = math.isclose(float(saved["mean"]), rec["mean"], rel_tol=1e-9, abs_tol=1e-9) and \
                    ((math.isnan(es) and math.isnan(rec["se"])) or math.isclose(es, rec["se"], rel_tol=1e-9,
                                                                               abs_tol=1e-9)) and \
                    int(saved["n_blocks"]) == int(rec["n_blocks"]) and bool(saved["flag"]) == flag
                rec.update({"engine_record": "verdict.json blocked_jackknife", "engine_mean": float(saved["mean"]),
                            "engine_se": es, "matches_engine": bool(same)})
            else:
                rec.update({"engine_record": NOT_SAVED, "engine_mean": float("nan"), "engine_se": float("nan"),
                            "matches_engine": ""})
            rows.append(rec)
    return pd.DataFrame(rows)


# =============================================================================================== markdown
def _fmt(x: Any, nd: int = 3) -> str:
    if x is None:
        return ""
    if isinstance(x, (bool, np.bool_)):
        return "yes" if x else "no"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    if isinstance(x, (float, np.floating)):
        return "" if math.isnan(float(x)) else ("%.*f" % (nd, float(x)))
    return str(x)


def _md_table(df: pd.DataFrame, cols: List[str]) -> str:
    if df is None or len(df) == 0:
        return "(no rows)\n"
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for i in range(len(df)):                      # per-column access keeps each column's dtype (iterrows upcasts)
        out.append("| " + " | ".join(_fmt(df[c].iloc[i]) for c in cols) + " |")
    return "\n".join(out) + "\n"


def _key_columns(run: Run, frame_cols: List[str], L: int) -> List[str]:
    keep = [run.adopted[L], run.pinned] + [c for c in frame_cols if c.startswith("base__")] + \
        [c for c in frame_cols if "trees_off" in c]
    return list(dict.fromkeys(c for c in keep if c in frame_cols))


def markdown(run: Run, t: Dict[str, pd.DataFrame], edges: Dict[int, Dict[str, Any]], script_sha: str) -> str:
    md = ["# Coral report-only tables (%s %s)" % (SCRIPT_NAME, SCRIPT_VERSION), ""]
    if not run.headline_eligible:
        md += ["**NOT HEADLINE: %s**" % "; ".join(run.not_headline or ["run_record headline_eligible is false"]), ""]
    md += ["- Run folder: `%s` (kind %s, package %s)" % (run.folder, run.kind, run.record.get("package")),
           "- Script SHA-256: `%s`; every input file's SHA-256 is in inputs_manifest.json." % script_sha,
           "- Report only: nothing here changes a fit, a pick or the verdict (draft section 6.2).",
           "- Every forecast is read as \"given a survey on this date\". The 365-day row is risk stratification.",
           "- Predict-zero and the donor-row median MAE are printed beside every MAE, on the same rows.", ""]
    pp = t["per_programme"]
    md += ["## 1. Per programme (stratum `%s`)" % run.stratum, "",
           "Values with fewer than %d rows are shown with n only. Full metrics for every column are in "
           "per_programme.csv." % MIN_ROWS_FOR_METRICS, ""]
    for L in run.leads:
        cols = _key_columns(run, list(pp.loc[pp["lead"] == L, "column"].unique()), L)
        s = pp[(pp["lead"] == L) & (pp["rows_basis"] == "all") & pp["column"].isin(cols)]
        md += ["### Lead %d (all rows; adopted `%s`%s)" % (L, run.adopted[L], ", declined" if run.declined[L] else ""),
               "", _md_table(s, ["stratum_value", "column", "n", "zero_share", "mae", "mae_predict_zero",
                                 "mae_donor_median", "hit", "corr2", "n_only"])]
        ad = pp[(pp["lead"] == L) & (pp["rows_basis"] == "all") & (pp["column"] == run.adopted[L]) &
                (pp["stratum_value"] != ALL) & (~pp["n_only"].astype(bool))]
        for _, r in ad.iterrows():
            if r["n"] and r["mae_predict_zero"] < r["mae"]:
                md.append("- Predict-zero beats the adopted answer on %s at lead %d (MAE %s vs %s)."
                          % (r["stratum_value"], L, _fmt(r["mae_predict_zero"]), _fmt(r["mae"])))
        md.append("")
    md += ["### Programme verdict lines (D74 rule, report only; the ALL line is the registered verdict's rows)", "",
           _md_table(t["programme_verdicts"], ["lead", "rows_basis", "stratum_value", "n_rows", "n_groups", "mean",
                                               "se", "low", "high", "tag", "matches_engine"])]
    md += ["### Blocked jackknife per programme (report only; the group jackknife decides)", "",
           "Overlap blocks from derived.json R14:overlap_blocks. The engine saves only the ALL line at the nowcast "
           "(verdict.json); every other line is computed here from the saved rows, by the engine's rule.", "",
           _md_table(t["programme_blocked_jackknife"], ["lead", "rows_basis", "stratum_value", "n_rows", "n_groups",
                                                        "n_blocks", "mean", "se", "group_se", "flag", "engine_record",
                                                        "matches_engine"])]
    md += ["## 2. By magnitude (a target-defined diagnostic, not a headline)", "",
           "Edges from the donor rows at each lead's fit cut (train rows only):", "",
           _md_table(pd.DataFrame(list(edges.values())), ["lead", "fit_cut", "donor_rows", "donor_rows_engine",
                                                          "donor_median", "positive_donor_rows", "pos_q25", "pos_q50",
                                                          "pos_q75", EDGE_PRIMARY, EDGE_POSITIVE])]
    mb = t["magnitude_bins"]
    for L in run.leads:
        s = mb[(mb["lead"] == L) & (mb["rows_basis"] == "all") & mb["column"].isin([run.adopted[L], run.pinned])]
        md += ["### Lead %d, adopted `%s`, pinned `%s`" % (L, run.adopted[L], run.pinned), "",
               _md_table(s, ["stratum_value", "bin", "column", "n", "mean_y", "mean_pred", "mae", "mae_predict_zero",
                             "mae_donor_median", "n_only"])]
    fg = t["flattening_guard"]
    md += ["## 3. Flattening guard (report only, never a choice)", "",
           "Rows with label at or above the edge; every arm and baseline in flattening_guard.csv. "
           "Two edges are printed; the owner chose (b) as the default (owner ruling X4, 2026-10-20):", "",
           "- %s." % edge_roles()[EDGE_PRIMARY], "- %s." % edge_roles()[EDGE_POSITIVE], ""]
    for L in run.leads:
        s = fg[(fg["lead"] == L) & (fg["rows_basis"] == "all") & (fg["stratum_value"] == ALL)]
        md += ["### Lead %d" % L, "", _md_table(s, ["edge_rule", "is_default", "edge", "column", "n", "observed_mean",
                                                     "mean_pred", "mean_pred_minus_observed"])]
    py = t["per_year_macro"]
    md += ["## 4. Pooled second (%s): pooled, macro over ecoregions, per test year" % ALL_LABEL, "",
           "No claim is made from a pooled margin.", ""]
    for L in run.leads:
        cols = _key_columns(run, list(py.loc[py["lead"] == L, "column"].unique()), L)
        s = py[(py["lead"] == L) & (py["rows_basis"] == "all") & py["column"].isin(cols)]
        md += ["### Lead %d" % L, "", _md_table(s, ["column", "line", "year", "n", "n_groups", "mae",
                                                     "mae_predict_zero", "mae_donor_median"])]
    pe = t["per_ecoregion"]
    md += ["## 5. Per ecoregion (n, zero share, programme mix; never ranked by MAE)", "",
           _md_table(pe[pe["lead"] == 0], [c for c in pe.columns if c != "lead"])]
    md += ["## 6. Counts", "", "### Rows left with no tree (V2 pool tree drop), per arm and pass", "",
           _md_table(t["counts_no_tree"], ["pass", "lead", "arm", "n_rows", "n_rows_no_tree", "share_no_tree"]),
           "### Pool fallbacks (under 12 valid pool rows)", "",
           _md_table(t["counts_pool_fallback"], ["pass", "lead", "pools_file", "rows", "rows_pool_fallback",
                                                 "matches_record"]),
           "### Rows left out", "", _md_table(t["counts_left_out"], ["what", "lead", "source", "rows_record",
                                                                        "rows_file"])]
    r30 = t["r30_missing"]
    is_counted = r30["what"].astype(str).str.startswith(("NaN share", "rows with"))
    saved, counted = r30[~is_counted], r30[is_counted]
    per_col = counted["what"].astype(str).str.startswith("NaN share")
    shown = counted[~per_col | (counted["n_nan"].fillna(0) > 0)].copy()
    for c in ("n_rows", "n_nan"):                     # counts as integers ('' when not counted)
        shown[c] = [("" if (v is None or (isinstance(v, float) and math.isnan(v))) else str(int(v)))
                    for v in shown[c].tolist()]
    md += ["### R30 missing tree features (0-filled share) and marine-heatwave NaN rows", "",
           "Saved once by the engine (derived.json R30): donor rows at the lead-0 fit cut. Per-year shares are in "
           "r30_missing.csv.", "",
           _md_table(saved, [c for c in ("lead", "what", "column", "filled_share", "flag_threshold", "over_threshold",
                                         "engine_flags", "status") if c in saved.columns]),
           "Counted from the lead tables (not an engine record), at every lead, on the donor rows at the lead's fit "
           "cut and on the scored test rows. At lead 0 the donor-row shares were checked equal to R30. Below: the "
           "marine-heatwave counts, and every column with at least one NaN row (all columns are in r30_missing.csv).",
           "",
           _md_table(shown, [c for c in ("lead", "rows_set", "what", "column", "n_rows", "n_nan", "nan_share",
                                         "over_threshold", "status") if c in shown.columns])]
    md += ["### Pools holding a month-precision row", "",
           _md_table(t["pools_month_precision"], ["pass", "lead", "pools_file", "pools",
                                                  "pools_holding_month_precision_row", "status"])]
    md += ["### Picks at the penalty grid edge (flagged, never extended)", "",
           _md_table(t["penalty_edge_picks"], ["source", "lead", "arm", "point", "at_edge", "edge_level",
                                               "edge_ratio", "engine_printed_edge", "note"])]
    md += ["## 7. Leads", "", "Leads %s; the ladder rows are scored on the rows common to all leads "
           "(rows_basis 'common' in every CSV), with all rows beside." % run.leads, "",
           "### Guard reference and decline object per lead (ruling V1: one object)", "",
           "The pinned arm's MAE and the reference's MAE on the guard surface, side by side.", "",
           _md_table(t["guard_reference"], ["lead", "surface", "surface_rows", "reference_column", "reference_value",
                                            "reference_value_text", "reference_mae", "pinned_arm", "pinned_mae",
                                            "pinned_minus_reference", "own_trees_off_mae", "passed",
                                            "decline_target", "guard_and_decline_one_object", "not_saved"])]
    return "\n".join(md) + "\n"


# =============================================================================================== main
def _protected_roots(path: Path) -> List[Path]:
    if not path.is_file():
        refuse("the protected-roots file %s is missing: --out cannot be checked (give --protected-roots)" % path)
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if s and not s.startswith("#"):
            out.append(Path(s).resolve())
    return out


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _check_out(out: Path, run_folder: Path, roots_file: Path) -> None:
    out = out.resolve()
    if _inside(out, run_folder.resolve()):
        refuse("--out %s is inside the run folder; the run is never written to" % out)
    for root in _protected_roots(roots_file):
        if _inside(out, root):
            refuse("--out %s is under the protected root %s" % (out, root))
    if out.exists() and any(out.iterdir()):
        refuse("--out %s exists and is not empty; nothing is overwritten, give a new folder" % out)


def _write(path: Path, text: str) -> None:
    with open(path, "x", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def build(run_folder: Any, package: Any, stratum: Optional[str] = None, toy: bool = False,
          month_precision_rows: Optional[Any] = None) -> Tuple[Run, Dict[str, pd.DataFrame], Dict[int, Dict[str, Any]]]:
    reader = Reader()
    run = Run(run_folder, package, reader, stratum, toy)
    mp_ids, mp_source = month_precision_ids(reader, run, month_precision_rows, toy)
    run.month_precision_source = mp_source or NOT_SAVED
    edges = {L: magnitude_edges(run, L) for L in run.leads}
    if not math.isclose(edges[0]["hit_tolerance_rebuilt_fit_cut"], run.tol[0], rel_tol=1e-9):
        refuse("lead 0 hit tolerance rebuilt %r differs from verdict.json %r"
               % (edges[0]["hit_tolerance_rebuilt_fit_cut"], run.tol[0]))
    common = common_keys(run)
    values = _stratum_values(run)
    tables = {"per_programme": per_programme(run, common, values),
              "programme_verdicts": programme_verdicts(run, common, values),
              "magnitude_bins": magnitude_table(run, common, values, edges),
              "flattening_guard": flattening_table(run, common, values, edges),
              "per_year_macro": per_year_macro(run, common),
              "per_ecoregion": per_ecoregion(run, values)}
    tables["counts_no_tree"] = counts_no_tree(run)
    tables["counts_pool_fallback"] = counts_pool_fallback(run, tables["counts_no_tree"])
    tables["counts_left_out"] = counts_left_out(run)
    tables["guard_reference"] = guard_reference(run)
    tables["r30_missing"] = r30_missing(run)
    tables["pools_month_precision"] = pools_month_precision(run, mp_ids, mp_source)
    tables["penalty_edge_picks"] = penalty_edge_picks(run)
    tables["programme_blocked_jackknife"] = programme_blocked_jackknife(run, common, values)
    pv = tables["programme_verdicts"]
    bad = pv[(pv["stratum_value"] == ALL) & pv["matches_engine"].apply(lambda x: isinstance(x, (bool, np.bool_)) and not x)]
    if len(bad):
        refuse("the recomputed registered verdict disagrees with the engine's record at %s: %s"
               % ([(int(r["lead"]), r["rows_basis"]) for _, r in bad.iterrows()],
                  [(r["tag"], r["engine_tag"], r["mean"], r["engine_mean"]) for _, r in bad.iterrows()]))
    pb = tables["programme_blocked_jackknife"]
    bad = pb[pb["matches_engine"].apply(lambda x: isinstance(x, (bool, np.bool_)) and not x)]
    if len(bad):
        refuse("the recomputed blocked jackknife disagrees with verdict.json: %s"
               % [(r["mean"], r["engine_mean"], r["se"], r["engine_se"]) for _, r in bad.iterrows()])
    pe = tables["penalty_edge_picks"]
    bad = pe[pe["matches_engine_print"].apply(lambda x: isinstance(x, (bool, np.bool_)) and not x)]
    if len(bad):
        refuse("the edge of a pick read from the saved grid differs from the engine's printed EDGE PICK: %s"
               % [(r["arm"], r["engine_printed_edge"]) for _, r in bad.iterrows()])
    return run, tables, edges


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Report-only coral tables over a finished run's saved rows.")
    ap.add_argument("run_folder")
    ap.add_argument("--out", required=True, help="a NEW (or empty) folder for the CSV and Markdown")
    ap.add_argument("--package", required=True, help="the package folder (its catalog.yaml gives the column roles)")
    ap.add_argument("--stratum", default=None, help="the report_stratum column (default: the run's only one)")
    ap.add_argument("--protected-roots", default=str(DEFAULT_ROOTS))
    ap.add_argument("--toy", action="store_true",
                    help="tests only: allow a non-headline run whose package is a synthetic toy package")
    ap.add_argument("--month-precision-rows", default=None,
                    help="the data builder's month_precision_rows.csv (column row_id; not an engine file). A non-toy "
                         "run reads %s when this is not given, and the list's SHA-256 must be %s. A toy run without "
                         "it prints 'not saved by the engine'" % (MONTH_PRECISION_LIST, MONTH_PRECISION_SHA256[:16]))
    args = ap.parse_args(argv)
    run_folder, out = Path(args.run_folder), Path(args.out)
    _check_out(out, run_folder, Path(args.protected_roots))
    script_sha = sha256_file(Path(__file__))
    run, tables, edges = build(run_folder, args.package, args.stratum, args.toy, args.month_precision_rows)
    out.mkdir(parents=True, exist_ok=True)
    tables = dict(tables, magnitude_edges=pd.DataFrame(list(edges.values())))
    for name, df in tables.items():
        _write(out / ("%s.csv" % name), df.to_csv(index=False, lineterminator="\n"))
    _write(out / "coral_report.md", markdown(run, tables, edges, script_sha))
    manifest = {"script": SCRIPT_NAME, "script_version": SCRIPT_VERSION, "script_sha256": script_sha,
                "run_folder": str(run.folder), "run_kind": run.kind, "headline_eligible": run.headline_eligible,
                "toy": bool(args.toy), "stratum": run.stratum, "leads": run.leads,
                "month_precision_rows": run.month_precision_source, "default_flattening_edge": EDGE_DEFAULT,
                "inputs_sha256": dict(sorted(run.r.read.items())),
                "outputs": sorted("%s.csv" % n for n in tables) + ["coral_report.md"]}
    _write(out / "inputs_manifest.json", json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print("coral_report: wrote %d files to %s" % (len(manifest["outputs"]) + 1, out.resolve()))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ReportRefusal as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        sys.exit(2)
