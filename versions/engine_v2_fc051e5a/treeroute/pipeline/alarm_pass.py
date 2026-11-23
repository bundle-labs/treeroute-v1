"""The twin-disagreement alarm in the pipeline (owner ruling AE with the AE1 amendment): the shared step every scoring
pass runs after its adoption is locked and BEFORE its test labels open, and the "with alarm" reports.

One code path for grid and table runs, nowcast and every lead (layer/alarm.py holds the rule):
  - run_pass_alarm: from the pass's label-free test predictions (the adopted column and the twin's, clipped and
    before the clip), its reference gap and its status, decide every issue batch (layer.alarm.decide_alarm), write
    alarm_preds.parquet (one row per saved test row, in test_preds order; NO label column) once, then the pass's alarm
    record alarm_lead_<L>.json and its lock (labels.vault.lock_alarm). Returns the record's hash, which
    open_test_labels requires. A resumed pass recomputes the same bytes; other bytes are refused (start a new run).
  - nowcast_reference: the nowcast's reference gap from inner_preds.parquet (the decision surface, every candidate
    clipped at every grid point, written before the adoption lock) at the adopted point.
  - write_alarm_report / write_alarm_ladder: the scores WITH and WITHOUT the alarm (ruling AE2) with the engine's
    own signed functions (report.metrics score_table, metric_by_key, single_verdict, blocked_jackknife), in new
    alarm_* files beside the existing ones (no existing file or column changes). "arm__with_alarm" lives only there.
Nothing here reads a test label before the pass's labels open: run_pass_alarm takes no y, and alarm_preds holds none.

HONESTY NOTE (ruling AE3): the alarm was designed after the engine v1 headline runs; layer.alarm.ALARM_ORIGIN is
written into every alarm record and report.
"""
# Provenance for the module: OWNER_RULINGS_2026-10-06.md section AE and the AE1 amendment (2026-10-21);
# D:/treeroute/engine_v2/SPEC_ALARM.txt sections 3-8.

import hashlib
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from treeroute.labels.vault import ALARM_FILE, ALARM_LOCK_SUFFIX, lock_alarm, row_key_hash
from treeroute.layer import alarm as LAL
from treeroute.layer import arms as LA
from treeroute.report import metrics as M
from treeroute.runs.atomic import read_json

from . import record as REC

ALARM_PREDS = "alarm_preds.parquet"
ALARM_GUARD_PREDS = "alarm_guard_preds.parquet"
ALARM_VERDICT = "alarm_verdict.json"
ALARM_SCORE_POOLED = "alarm_score_pooled.csv"
ALARM_SCORE_BY_GROUP = "alarm_score_by_group.csv"
ALARM_PER_YEAR = "alarm_per_year.csv"
ALARM_LADDER_TABLE = "alarm_ladder_table.csv"
ALARM_LADDER_RECORD = "alarm_ladder.json"
BATCH_RULE = ("AE1 amendment: a batch is the rows sharing the issue calendar month (a grid step of one month or "
              "more: the issue step itself; a finer step or a day-dated row: the calendar month of the issue's first "
              "day); a batch below A8.alarm_min_batch_rows rows is not tested")
PREDS_COLUMNS = ("unit", "group", "time", "year", "lead", "issue", "batch", "adopted", "twin", "with_alarm",
                 "pre_with_alarm", "fired")


class AlarmPassRefusal(LAL.AlarmRefusal):
    """The alarm step of a pass refused (fail loudly)."""


def _sha_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _num(x: Any) -> Optional[float]:
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def point_column(arm: Any, point: Any) -> str:
    """The inner_preds.parquet column of an arm at a grid point (pipeline/passes.py _point_name)."""
    return "%s@level=%r,ratio=%r" % (LA.arm_name(arm), point.level, point.ratio)


def nowcast_reference(folder: Path, adopted: Any, twin: Any, point: Any) -> Dict[str, Any]:
    """The nowcast's reference gap: mean |A - T| over the decision surface's rows at the adopted point, from
    inner_preds.parquet (clipped, as decide scored them; written before the adoption lock), and the surface's hash
    from decision_checks.json. Reads only the two columns."""
    import pyarrow.parquet as pq

    from .passes import DECISION_CHECKS

    path = Path(folder) / REC.INNER_PREDS
    cols = [point_column(adopted, point), point_column(twin, point)]
    have = set(pq.read_schema(str(path)).names)
    missing = [c for c in cols if c not in have]
    if missing:
        raise AlarmPassRefusal("AE1", "the decision surface (%s) holds no column %s: the reference gap needs the "
                               "adopted arm and its twin at the adopted point" % (path.name, missing))
    table = pq.read_table(str(path), columns=cols)
    a = table.column(0).to_numpy()
    t = table.column(1).to_numpy()
    checks = read_json(Path(folder) / DECISION_CHECKS)
    return {"surface": "decision surface", "surface_sha256": checks.get("surface_sha256"),
            "file": REC.INNER_PREDS, "columns": cols,
            "point": {"level": float(point.level), "ratio": None if point.ratio is None else float(point.ratio)},
            "rows": int(a.size), "gap": LAL.reference_gap(a, t)}


def nowcast_twin(adoption: Any, weightings: Sequence[Any]) -> Dict[str, Any]:
    """The nowcast's twin facts from the locked adoption: the twin, its kind, simpler, eligible (Adoption.eligible)."""
    if adoption.declined:
        return {"declined": True, "twin": None, "kind": None, "simpler": None, "eligible": None}
    twin, kind = LAL.twin_of(adoption.adopted, weightings)
    return {"declined": False, "twin": twin, "kind": kind, "simpler": LAL.twin_is_simpler(adoption.adopted, twin),
            "eligible": LAL.twin_eligible_nowcast(twin, adoption.eligible)}


def lead_twin(pinned: Any, guard_passed: bool, weightings: Sequence[Any]) -> Dict[str, Any]:
    """A lead's twin facts known BEFORE any extra routing: declined when its guard failed; the twin, its kind and
    simpler. Eligibility needs the twin's guard MAE (routed only when the lead may be active)."""
    twin, kind = LAL.twin_of(pinned, weightings)
    return {"declined": not guard_passed, "twin": twin, "kind": kind, "simpler": LAL.twin_is_simpler(pinned, twin),
            "eligible": None}


def may_be_active(facts: Mapping[str, Any]) -> bool:
    """True when the pass's status can still be 'active' from the arm alone (not declined, twin simpler): only then
    does a lead route its twin."""
    return (not facts["declined"]) and bool(facts["simpler"])


def run_pass_alarm(state: Any, *, lead: int, pass_name: str, out_dir: Path, adoption_file: str, adoption_sha256: str,
                   labels: Any, adopted_name: str, adopted_column: str, facts: Mapping[str, Any],
                   eligibility_basis: Mapping[str, Any], reference: Optional[Mapping[str, Any]],
                   keys: Mapping[str, np.ndarray], adopted: np.ndarray, pre_adopted: np.ndarray,
                   twin: Optional[np.ndarray], pre_twin: Optional[np.ndarray], cadence: Any,
                   guard_preds_file: Optional[str] = None) -> Tuple[str, Any]:
    """The alarm of one scoring pass, decided, saved and locked BEFORE its test labels open (module docstring).
    keys: unit, group, time, year, lead, issue per saved test row (test_preds order); adopted / pre_adopted: the
    adopted column clipped and before the clip (the decline target's column when the pass declined); twin /
    pre_twin: the twin's, or None when it was not routed (a lead whose status cannot be active); cadence: the grid's
    target cadence, or None for day-dated rows; reference: {surface, surface_sha256, point, rows, gap, ...} or None
    (a pass that cannot be active); facts: nowcast_twin / lead_twin with 'eligible' set. Returns (the alarm record's
    SHA-256, the AlarmRecord)."""
    folder = Path(state.p.folder)
    gap = None if reference is None else reference.get("gap")
    status = LAL.pass_status(bool(facts["declined"]), facts.get("simpler"), facts.get("eligible"), gap)
    if status == LAL.STATUS_ACTIVE and twin is None:
        raise AlarmPassRefusal("AE1", "internal: %s is active but its twin was not routed" % pass_name)
    issue = np.asarray(keys["issue"], dtype=np.int64)
    batch = LAL.batch_keys(issue, cadence)
    rec = LAL.decide_alarm(status, adopted, pre_adopted, twin, pre_twin, batch, gap)
    n = int(np.asarray(adopted).size)
    frame = pd.DataFrame({"unit": np.asarray(keys["unit"], dtype=object),
                          "group": np.asarray(keys["group"], dtype=object),
                          "time": np.asarray(keys["time"], dtype=np.int64),
                          "year": np.asarray(keys["year"], dtype=np.int64),
                          "lead": np.full(n, int(lead), dtype=np.int64), "issue": issue,
                          "batch": np.asarray(rec.batch, dtype=object),
                          "adopted": np.asarray(adopted, dtype=np.float64),
                          "twin": (np.asarray(twin, dtype=np.float64) if twin is not None else np.full(n, np.nan)),
                          "with_alarm": np.asarray(rec.with_alarm, dtype=np.float64),
                          "pre_with_alarm": np.asarray(rec.pre_with_alarm, dtype=np.float64),
                          "fired": np.asarray(rec.fired, dtype=bool)})
    from .passes import _write_parquet_once

    out_dir = Path(out_dir)
    path = out_dir / ALARM_PREDS
    _write_parquet_once(frame, path)
    rel = path.relative_to(folder).as_posix()
    twin_arm = facts.get("twin")
    context = {
        "lead": int(lead), "pass": pass_name, "adoption_file": adoption_file, "adoption_sha256": adoption_sha256,
        "adopted_arm": adopted_name, "adopted_column": adopted_column,
        "twin_arm": None if twin_arm is None else LA.arm_name(twin_arm), "twin_kind": facts.get("kind"),
        "twin_simpler": facts.get("simpler"), "twin_eligible": facts.get("eligible"),
        "eligibility_basis": dict(eligibility_basis), "twin_routed": twin is not None,
        "reference": None if reference is None else dict(reference, gap=_num(reference.get("gap"))),
        "batch_rule": BATCH_RULE, "alarm_preds_file": rel, "alarm_preds_sha256": _sha_file(path),
        "test_rows": n, "test_row_key_hash": row_key_hash(np.asarray(keys["unit"], dtype=object),
                                                           np.asarray(keys["time"], dtype=np.int64)),
        "alarm_guard_preds_file": guard_preds_file,
        "alarm_guard_preds_sha256": (_sha_file(folder / guard_preds_file) if guard_preds_file else None)}
    doc = LAL.alarm_document(rec, context)
    sha = lock_alarm(doc, int(lead), labels, folder)
    state.log("%s: twin-disagreement alarm (owner ruling AE; designed after the v1 runs, AE3): adopted %s, twin %s "
              "(%s), status %s, reference gap %s, %d batch(es), %d tested, %d took the twin (%d rows); locked %s "
              "(SHA-256 %s) before the test labels open"
              % (pass_name, adopted_name, context["twin_arm"], facts.get("kind"), status,
                 "n/a" if gap is None else "%.6g" % float(gap), len(rec.batches), rec.batches_tested,
                 rec.batches_fired, rec.rows_switched, ALARM_FILE % int(lead), sha[:16]))
    return sha, rec


def alarm_lock_record(folder: Path, lead: int) -> Optional[Dict[str, Any]]:
    """{alarm_file, alarm_sha256, lock_file} of a pass's locked alarm record, or None when there is none."""
    name = ALARM_FILE % int(lead)
    lock = Path(folder) / (name + ALARM_LOCK_SUFFIX)
    if not lock.is_file():
        return None
    rec = read_json(lock)
    return {"alarm_file": name, "alarm_sha256": rec["sha256"], "lock_file": lock.name}


# ------------------------------------------------------------------------------------------------ the reports
def _bits(values: Any) -> bytes:
    return np.ascontiguousarray(np.asarray(values, dtype=np.float64)).tobytes()


def with_alarm_frame(preds: pd.DataFrame, alarm: pd.DataFrame, adopted_column: str) -> pd.DataFrame:
    """The saved test rows with the 'with alarm' column (and its pre-clip column when the adopted column has one),
    joined from alarm_preds by row order, which must be the same (unit, time) rows; the alarm's adopted column must
    equal the saved adopted column bit for bit."""
    if len(preds) != len(alarm) or not (
            np.array_equal(preds[M.COL_UNIT].to_numpy(dtype=object), alarm["unit"].to_numpy(dtype=object))
            and np.array_equal(preds[M.COL_TIME].to_numpy(dtype=np.int64), alarm["time"].to_numpy(dtype=np.int64))):
        raise AlarmPassRefusal("AE2", "alarm_preds.parquet's rows are not the saved test rows, in order")
    if adopted_column not in preds.columns or _bits(preds[adopted_column]) != _bits(alarm["adopted"]):
        raise AlarmPassRefusal("AE2", "alarm_preds.parquet's adopted column is not the saved %s, bit for bit"
                               % adopted_column)
    out = preds.copy()
    out[LAL.WITH_ALARM_COLUMN] = alarm["with_alarm"].to_numpy(dtype=np.float64)
    pre = M.PRE_PREFIX + adopted_column[len(M.ARM_PREFIX):] if adopted_column.startswith(M.ARM_PREFIX) else None
    if pre is not None and pre in preds.columns:
        out[LAL.PRE_WITH_ALARM_COLUMN] = alarm["pre_with_alarm"].to_numpy(dtype=np.float64)
    return out


def _pooled(table: pd.DataFrame, col: str) -> float:
    sel = table[(table["line"] == M.LINE_POOLED) & (table["column"] == col) & (table["rows_basis"] == M.ROWS_BASIS_ALL)]
    return float(sel["mae"].iloc[0])


def verdict_with(frame: pd.DataFrame, ref_col: str, adopted_col: str, band: float, declined: bool,
                 reference_rule: str, tol: float, floor: Optional[float], kind: Any,
                 block_of_group: Optional[Mapping[str, int]] = None) -> Dict[str, Any]:
    """The with-alarm verdict on these rows with the signed functions (single_verdict against the pass's own
    reference, under the given band), the pooled MAEs and, given the blocks, the blocked jackknife."""
    tg = M.score_table(frame, ("group",), tol, floor, kind)
    tp = M.score_table(frame, (), tol, floor, kind)
    per_ref = M.metric_by_key(tg, ref_col, "mae", "group")
    per_with = M.metric_by_key(tg, LAL.WITH_ALARM_COLUMN, "mae", "group")
    per_ad = M.metric_by_key(tg, adopted_col, "mae", "group")
    v = M.single_verdict(per_ref, per_with, _pooled(tp, ref_col), _pooled(tp, LAL.WITH_ALARM_COLUMN), band, declined,
                         reference_rule)
    out = {"column": LAL.WITH_ALARM_COLUMN, "pooled_mae": _pooled(tp, LAL.WITH_ALARM_COLUMN),
           "pooled_mae_adopted": _pooled(tp, adopted_col), "pooled_mae_reference": _pooled(tp, ref_col),
           "verdict": M.verdict_record(v), "per_group": {"with": per_with, "without": per_ad, "reference": per_ref}}
    if block_of_group is not None:
        contrast = {g: per_ref[g] - per_with[g] for g in per_ref}
        blocked = M.blocked_jackknife(contrast, {g: block_of_group[g] for g in contrast})
        out["blocked_jackknife"] = {"mean": blocked.mean, "se": blocked.se, "low": blocked.low, "high": blocked.high,
                                    "n_blocks": blocked.n_groups,
                                    "flag": M.blocked_jackknife_flag(v.contrast, blocked)}
    return out


def write_alarm_report(state: Any, preds: pd.DataFrame, adopted_column: str, ref_column: str, band: float,
                       declined: bool, reference_rule: str, verdict_rec: Mapping[str, Any], tol: float,
                       floor: Optional[float], block_of_group: Mapping[str, int]) -> Dict[str, Any]:
    """The nowcast's scores WITH and WITHOUT the alarm (ruling AE2): alarm_score_pooled.csv, alarm_score_by_group.csv,
    alarm_per_year.csv (score_table on the saved rows plus 'arm__with_alarm', every column, so with and without sit
    side by side on the same rows) and alarm_verdict.json. When no batch took the twin, the two pooled MAEs must be
    equal bit for bit (asserted)."""
    p = state.p
    folder = Path(p.folder)
    lock = alarm_lock_record(folder, 0)
    if lock is None:
        raise AlarmPassRefusal("AE2", "the nowcast has no locked alarm record; every run reports with and without "
                               "the alarm")
    doc = read_json(folder / lock["alarm_file"])
    alarm = pd.read_parquet(folder / ALARM_PREDS)
    frame = with_alarm_frame(preds, alarm, adopted_column)
    kind = p.kind
    t_pooled = M.score_table(frame, (), tol, floor, kind)
    t_group = M.score_table(frame, ("group",), tol, floor, kind)
    t_year = M.score_table(frame, ("year",), tol, floor, kind)
    for name, table in ((ALARM_SCORE_POOLED, t_pooled), (ALARM_SCORE_BY_GROUP, t_group), (ALARM_PER_YEAR, t_year)):
        REC.write_text_once_or_same(folder / name, REC.csv_text(table))
    w = verdict_with(frame, ref_column, adopted_column, band, declined, reference_rule, tol, floor, kind,
                     block_of_group)
    fired = int(doc["batches_fired"])
    if fired == 0 and _bits([w["pooled_mae"]]) != _bits([w["pooled_mae_adopted"]]):
        raise AlarmPassRefusal("AE2", "no batch took the twin, yet the with-alarm pooled MAE %r differs from the "
                               "adopted %r" % (w["pooled_mae"], w["pooled_mae_adopted"]))
    per_year_with = M.metric_by_key(t_year, LAL.WITH_ALARM_COLUMN, "mae", "year")
    per_year_ad = M.metric_by_key(t_year, adopted_column, "mae", "year")
    per_year_ref = M.metric_by_key(t_year, ref_column, "mae", "year")
    rec = {"alarm_origin": LAL.ALARM_ORIGIN, "rule": LAL.ALARM_RULE, "post_hoc": False,
           "alarm_file": lock["alarm_file"], "alarm_sha256": lock["alarm_sha256"], "status": doc["status"],
           "twin_arm": doc.get("twin_arm"), "batches_tested": int(doc["batches_tested"]), "batches_fired": fired,
           "rows_switched": int(doc["rows_switched"]),
           "without": {"adopted_column": adopted_column, "pooled_mae_adopted": verdict_rec["pooled_mae_adopted"],
                       "verdict": verdict_rec["verdict"]},
           "with": {"column": LAL.WITH_ALARM_COLUMN, "pooled_mae": w["pooled_mae"], "verdict": w["verdict"],
                    "blocked_jackknife": w["blocked_jackknife"]},
           "reference": ref_column, "band": band,
           "per_group": [{"group": g, "mae_without": w["per_group"]["without"][g], "mae_with": w["per_group"]["with"][g],
                          "mae_reference": w["per_group"]["reference"][g]} for g in sorted(w["per_group"]["with"])],
           "per_year": [{"year": int(y), "mae_without": per_year_ad[y], "mae_with": per_year_with[y],
                         "mae_reference": per_year_ref[y]} for y in sorted(per_year_with)]}
    if not _same_json(verdict_rec["pooled_mae_adopted"], w["pooled_mae_adopted"]):
        raise AlarmPassRefusal("AE2", "internal: the adopted pooled MAE on the alarm frame differs from verdict.json's")
    path = folder / ALARM_VERDICT
    if path.exists():
        from .passes import PassRefusal, _without

        if _without(read_json(path), "__none__") != _without(rec, "__none__"):
            raise PassRefusal("G-FINGERPRINT", "%s exists with another record" % path, fix="start a new run")
    else:
        M.write_json_once(rec, path)
    state.log("alarm report (AE2): status %s, %d batch(es) took the twin (%d rows); pooled MAE without %.6g, with "
              "%.6g; verdict without %s, with %s"
              % (rec["status"], fired, rec["rows_switched"], verdict_rec["pooled_mae_adopted"], w["pooled_mae"],
                 verdict_rec["verdict"]["tag"], w["verdict"]["tag"]))
    return rec


def _same_json(a: Any, b: Any) -> bool:
    return _bits([a]) == _bits([b])


def write_alarm_ladder(state: Any, ladder_folder: Path, frames: Mapping[int, pd.DataFrame],
                       info: Mapping[int, Mapping[str, Any]], common: Any, band: float, reference_rule: str,
                       tol: float, floor: Optional[float], verdicts: Mapping[int, Mapping[str, Any]]) -> Dict[str, Any]:
    """The ladder WITH and WITHOUT the alarm (ruling AE2): ladder/alarm_ladder_table.csv (per lead and rows basis,
    the adopted and the with-alarm pooled lines; the common rows are the ladder's own, R34) and
    ladder/alarm_ladder.json (per lead: status, batches, rows switched and the with-alarm verdict on the common rows
    under the nowcast band, beside the existing one). Lead 0's alarm is the nowcast's (alarm_lead_0.json)."""
    p = state.p
    folder = Path(p.folder)
    lines, per_lead = [], {}
    common = np.asarray(sorted(common), dtype=object)
    for L, f in sorted(frames.items()):
        lock = alarm_lock_record(folder, L)
        if lock is None:
            raise AlarmPassRefusal("AE2", "lead %d has no locked alarm record" % L)
        doc = read_json(folder / lock["alarm_file"])
        alarm = pd.read_parquet(folder / doc["alarm_preds_file"])
        ad_c, ref_c = info[L]["adopted_column"], info[L]["reference_column"]
        fw = with_alarm_frame(f, alarm, ad_c)
        k = np.asarray(["%s\t%d" % (u, t) for u, t in zip(fw["unit"].to_numpy(dtype=object).tolist(),
                                                        fw["time"].to_numpy(dtype=np.int64).tolist())], dtype=object)
        sub = fw[np.isin(k, common)].reset_index(drop=True)
        for basis, frame in (("common", sub), ("all", fw)):
            t = M.score_table(frame, (), tol, floor, p.kind)
            t = t[(t["line"] == M.LINE_POOLED) & (t["rows_basis"] == M.ROWS_BASIS_ALL)
                  & t["column"].isin([ad_c, ref_c, LAL.WITH_ALARM_COLUMN])].copy()
            t.insert(0, "ladder_rows", basis)
            t.insert(0, "lead", L)
            t.insert(2, "role", ["with_alarm" if c == LAL.WITH_ALARM_COLUMN else ("adopted" if c == ad_c else
                                                                               "reference")
                                 for c in t["column"].tolist()])
            lines.append(t)
        w = verdict_with(sub, ref_c, ad_c, band, bool(info[L]["declined"]), reference_rule, tol, floor, p.kind)
        if int(doc["batches_fired"]) == 0 and _bits([w["pooled_mae"]]) != _bits([w["pooled_mae_adopted"]]):
            raise AlarmPassRefusal("AE2", "lead %d: no batch took the twin, yet the with-alarm pooled MAE differs" % L)
        per_lead[str(L)] = {"status": doc["status"], "twin_arm": doc.get("twin_arm"),
                            "alarm_file": lock["alarm_file"], "alarm_sha256": lock["alarm_sha256"],
                            "batches_tested": int(doc["batches_tested"]), "batches_fired": int(doc["batches_fired"]),
                            "rows_switched": int(doc["rows_switched"]), "common_rows": int(len(sub)),
                            "without": dict(verdicts[L]),
                            "with": dict(w["verdict"], column=LAL.WITH_ALARM_COLUMN, reference_column=ref_c,
                                         pooled_mae=w["pooled_mae"], pooled_mae_adopted=w["pooled_mae_adopted"])}
    table = pd.concat(lines, ignore_index=True)
    REC.write_text_once_or_same(Path(ladder_folder) / ALARM_LADDER_TABLE, REC.csv_text(table))
    rec = {"alarm_origin": LAL.ALARM_ORIGIN, "rule": LAL.ALARM_RULE, "post_hoc": False, "band": band,
           "band_source": "the nowcast's band (F57)", "common_rows": int(common.size), "by_lead": per_lead}
    import json

    from treeroute.runs.atomic import dumps

    REC.write_once_or_same(Path(ladder_folder) / ALARM_LADDER_RECORD, json.loads(dumps(M._json_safe(rec))))
    for L, v in sorted(per_lead.items(), key=lambda kv: int(kv[0])):
        state.log("alarm ladder lead %s: status %s, %d batch(es) took the twin; verdict without %s, with %s"
                  % (L, v["status"], v["batches_fired"], v["without"].get("tag"), v["with"].get("tag")))
    return rec


__all__ = ["ALARM_PREDS", "ALARM_GUARD_PREDS", "ALARM_VERDICT", "ALARM_SCORE_POOLED", "ALARM_SCORE_BY_GROUP",
           "ALARM_PER_YEAR", "ALARM_LADDER_TABLE", "ALARM_LADDER_RECORD", "BATCH_RULE", "AlarmPassRefusal",
           "point_column", "nowcast_reference", "nowcast_twin", "lead_twin", "may_be_active", "run_pass_alarm",
           "alarm_lock_record", "with_alarm_frame", "verdict_with", "write_alarm_report", "write_alarm_ladder"]
