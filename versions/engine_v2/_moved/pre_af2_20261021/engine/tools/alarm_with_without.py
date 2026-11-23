"""POST-HOC with/without table of the twin-disagreement alarm on saved engine v1 runs, nowcast AND leads (owner rulings
AE2, AE4; read-only).

HONESTY NOTE (owner ruling AE3, binding): the alarm was designed AFTER the engine v1 headline runs, from the diagnosis
of Parts 601-604. Every row this script writes is a POST-HOC replay and carries the tag "POST-HOC (AE3)". Only runs on
new data under engine v2 count as pre-registered for the alarm.

Per run folder:
  - nowcast (lead 0): the exact v2 rule, as tools/alarm_replay.py applies it (twin_of, twin_is_simpler,
    twin_eligible_nowcast on adoption.json's eligible list, nowcast_reference on inner_preds.parquet, batch_keys,
    pass_status, decide_alarm). If <out>/<package>/<run id>/alarm_replay.json exists, its pooled MAEs and fired batch
    count must equal the ones recomputed here (else refuse);
  - every lead L (adoption_lead_<L>.json): the lead's twin facts from its pinned arm and its guard result
    (alarm_pass.lead_twin, the same call ladder.py / table_ladder.py make). A lead that is declined (guard failed) or
    whose twin is not simpler can never fire, needs no twin, and IS replayed (decide_alarm with no twin: with = without,
    asserted). A lead that may be active (guard passed, twin simpler) needs the twin's predictions on the lead's guard
    surface (eligibility, reference gap) and on its test rows; a v1 lead routed only its pinned arm (layer/arms.py
    lead_arms), so such a lead is NOT replayable: its without-MAE is printed, with-MAE left empty;
  - scores: the engine's own score_table pooled MAE on the rows (all rows; and, when --magnitude-edges is given for the
    package, the positive-label rows (y > 0), the rows above that lead's q75 of positive donor labels (the edge the
    package's pre-registered magnitude report uses), and, with --abs-edge, the rows at or above that value). The
    v1 adopted pooled MAE is checked against verdict.json (nowcast) / ladder_table.csv (leads).
Writes ONLY: <out>/WITH_WITHOUT.csv and <out>/rows/<package>_<run id>_lead_<L>.parquet (row-level adopted, twin when
saved, with_alarm, fired, batch, y: predictions are kept, not only scores).

Usage, from the engine folder (engine v2):
    py -3.9 tools/alarm_with_without.py <run folder> [...] --out <replay folder>
        [--magnitude-edges <package>=<edges csv> ...] [--abs-edge <value>]
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

ENGINE_DIR = Path(__file__).resolve().parents[1]
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

OUT_FILE = "WITH_WITHOUT.csv"
NOT_REPLAYABLE = "not_replayable_twin_not_saved"
NOTE_NOT_REPLAYABLE = ("the lead may be active (guard passed, twin simpler) but v1 routed only the pinned arm at a lead: "
                       "the twin's guard MAE (eligibility), the guard reference gap and the twin's test predictions "
                       "are not saved; routing them now is a re-run (not allowed)")


class WithWithoutRefusal(Exception):
    """Fail loudly."""


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _pooled_mae(frame: Any, col: str, tol: float, floor: Optional[float], run_kind: Any) -> Dict[str, Any]:
    from treeroute.report import metrics as M

    t = M.score_table(frame, (), tol, floor, run_kind)
    sel = t[(t["line"] == M.LINE_POOLED) & (t["rows_basis"] == M.ROWS_BASIS_ALL) & (t["column"] == col)]
    if len(sel) != 1:
        raise WithWithoutRefusal("no single pooled line for %s" % col)
    return {"mae": float(sel["mae"].iloc[0]), "n": int(sel["n"].iloc[0])}


def _subsets(y: Any, edge: Optional[float], abs_edge: Optional[float]) -> List[Any]:
    import numpy as np

    out = [("all rows", np.ones(y.size, dtype=bool))]
    if edge is not None:
        out.append(("positive label (y > 0)", np.isfinite(y) & (y > 0)))
        out.append(("severe (y > %.6g: q75 of positive donor labels at the lead's fit cut)" % edge,
                    np.isfinite(y) & (y > edge)))
    if abs_edge is not None and edge is not None:
        out.append(("severe (y >= %.6g)" % abs_edge, np.isfinite(y) & (y >= abs_edge)))
    return out


def _score_rows(frame: Any, adopted_col: str, with_col: Optional[str], tol: float, floor: Optional[float],
                run_kind: Any, edge: Optional[float], abs_edge: Optional[float]) -> List[Dict[str, Any]]:
    import numpy as np

    keep = ["unit", "group", "time", "year", "y", "normal", "legal_min", "legal_max", adopted_col]
    if with_col is not None:
        keep.append(with_col)
    lines = []
    y = frame["y"].to_numpy(dtype=np.float64)
    for name, mask in _subsets(y, edge, abs_edge):
        sub = frame.loc[mask, keep]
        w = _pooled_mae(sub, adopted_col, tol, floor, run_kind)
        mw = _pooled_mae(sub, with_col, tol, floor, run_kind)["mae"] if with_col is not None else None
        lines.append({"subset": name, "n": w["n"], "mae_without": w["mae"], "mae_with": mw})
    return lines


def _write_rows(out_root: Path, package: str, run_id: str, lead: int, frame: Any) -> None:
    path = out_root / "rows" / ("%s_%s_lead_%d.parquet" % (package, run_id, lead))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        import pandas as pd
        old = pd.read_parquet(path)
        if not old.equals(frame.reset_index(drop=True)):
            raise WithWithoutRefusal("%s exists with other rows; use a new --out folder" % path)
        return
    frame.reset_index(drop=True).to_parquet(path, index=False)


def _nowcast(folder: Path, out_root: Path, edge: Optional[float], abs_edge: Optional[float]) -> List[Dict[str, Any]]:
    import numpy as np
    import pyarrow.parquet as pq

    import alarm_replay as AR
    from treeroute.layer import alarm as LAL
    from treeroute.layer import arms as LA
    from treeroute.pipeline import alarm_pass as AP
    from treeroute.report import metrics as M
    from treeroute.route.kinds import GridPoint

    adoption = _read_json(folder / "adoption.json")
    verdict = _read_json(folder / "verdict.json")
    record = _read_json(folder / "run_record.json")
    derived = _read_json(folder / "derived.json")
    package, run_id = str(verdict["package"]), folder.name
    weightings = (LA.Weighting.UNWEIGHTED,) if verdict["router_kind"] == "region" \
        else (LA.Weighting.UNWEIGHTED, LA.Weighting.GLS)
    declined = bool(adoption["declined"])
    adopted_col = verdict.get("adopted_column") or (M.ARM_PREFIX + verdict["adopted"])
    cadence = AR._cadence(derived["R1"]["value"])
    twin = kind = simpler = eligible = None
    ref = None
    if not declined:
        adopted = AR._arm(adoption["adopted"])
        point = GridPoint(float(adoption["penalty"]["level"]),
                          None if adoption["penalty"]["ratio"] is None else float(adoption["penalty"]["ratio"]))
        twin, kind = LAL.twin_of(adopted, weightings)
        simpler = LAL.twin_is_simpler(adopted, twin)
        eligible = LAL.twin_eligible_nowcast(twin, [AR._arm(a) for a in adoption.get("eligible") or []])
        ref = AP.nowcast_reference(folder, adopted, twin, point)
    gap = None if ref is None else ref["gap"]
    status = LAL.pass_status(declined, simpler, eligible, gap)
    names = set(pq.read_schema(str(folder / "test_preds.parquet")).names)
    want = ["unit", "group", "time", "year", "issue", "y", "normal", "legal_min", "legal_max", adopted_col]
    pre_ad = M.PRE_PREFIX + adopted_col[len(M.ARM_PREFIX):]
    if pre_ad in names:
        want.append(pre_ad)
    twin_col = pre_tw = None
    if twin is not None:
        twin_col, pre_tw = M.ARM_PREFIX + LA.arm_name(twin), M.PRE_PREFIX + LA.arm_name(twin)
        want += [twin_col, pre_tw]
    want = list(dict.fromkeys(want))
    t = pq.read_table(str(folder / "test_preds.parquet"), columns=want).to_pandas()
    a_v = t[adopted_col].to_numpy(dtype=np.float64)
    a_pre = t[pre_ad].to_numpy(dtype=np.float64) if pre_ad in t.columns else a_v
    tw = t[twin_col].to_numpy(dtype=np.float64) if twin_col else None
    tw_pre = t[pre_tw].to_numpy(dtype=np.float64) if pre_tw else None
    batch = LAL.batch_keys(t["issue"].to_numpy(dtype=np.int64), cadence)
    rec = LAL.decide_alarm(status, a_v, a_pre, tw, tw_pre, batch, gap)
    t[LAL.WITH_ALARM_COLUMN] = np.asarray(rec.with_alarm, dtype=np.float64)
    tol, floor, run_kind = float(verdict["hit_tolerance"]), verdict.get("measurement_error_floor"), record["kind"]
    lines = _score_rows(t, adopted_col, LAL.WITH_ALARM_COLUMN, tol, floor, run_kind, edge, abs_edge)
    if lines[0]["mae_without"] != float(verdict["pooled_mae_adopted"]):
        raise WithWithoutRefusal("%s nowcast: adopted MAE %r is not verdict.json's %r"
                                 % (folder, lines[0]["mae_without"], verdict["pooled_mae_adopted"]))
    prior = out_root / package / run_id / AR.RECORD_FILE
    if prior.is_file():
        d = _read_json(prior)
        if (d["scores"]["pooled_mae_with"] != lines[0]["mae_with"] or d["batches_fired"] != rec.batches_fired
                or d["status"] != status):
            raise WithWithoutRefusal("%s nowcast: differs from the earlier replay record %s" % (folder, prior))
    _write_rows(out_root, package, run_id, 0, t[["unit", "group", "time", "year", "issue", "y"]].assign(
        batch=np.asarray(rec.batch, dtype=str), adopted=a_v,
        twin=tw if tw is not None else np.full(a_v.size, np.nan),
        with_alarm=np.asarray(rec.with_alarm, dtype=np.float64), fired=np.asarray(rec.fired, dtype=bool)))
    fired = [b.batch for b in rec.batches if b.fired]
    base = {"tag": LAL.POST_HOC_TAG, "package": package, "run": run_id, "lead": 0, "pass": "nowcast",
            "adopted_column": adopted_col, "twin_arm": None if twin is None else LA.arm_name(twin),
            "twin_kind": kind, "twin_simpler": simpler, "twin_eligible": eligible, "status": status,
            "replayable": True, "reference_gap": gap, "batches": len(rec.batches),
            "batches_tested": rec.batches_tested, "batches_fired": rec.batches_fired,
            "rows_switched": rec.rows_switched, "fired_batches": " ".join(fired),
            "max_ratio_tested": max([b.ratio for b in rec.batches if b.tested and b.ratio is not None] or [float("nan")]),
            "note": "reference = decision surface at the adopted point; eligibility = adoption.json eligible list"}
    return [dict(base, **ln) for ln in lines]


def _leads(folder: Path, out_root: Path, edges: Optional[Dict[int, float]], abs_edge: Optional[float]
           ) -> List[Dict[str, Any]]:
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq

    import alarm_replay as AR
    from treeroute.layer import alarm as LAL
    from treeroute.layer import arms as LA
    from treeroute.pipeline import alarm_pass as AP

    verdict = _read_json(folder / "verdict.json")
    record = _read_json(folder / "run_record.json")
    derived = _read_json(folder / "derived.json")
    ladder = _read_json(folder / "ladder" / "ladder.json")
    package, run_id = str(verdict["package"]), folder.name
    weightings = (LA.Weighting.UNWEIGHTED,) if verdict["router_kind"] == "region" \
        else (LA.Weighting.UNWEIGHTED, LA.Weighting.GLS)
    cadence = AR._cadence(derived["R1"]["value"])
    lt = pd.read_csv(folder / "ladder" / "ladder_table.csv",
                     usecols=["lead", "ladder_rows", "adopted", "rows_basis", "column", "line", "mae"])
    tol, floor, run_kind = float(ladder["hit_tolerance"]), ladder.get("measurement_error_floor"), record["kind"]
    out = []
    for L in sorted(int(x) for x in ladder["leads"]):
        la = _read_json(folder / ("adoption_lead_%d.json" % L))
        pinned = AR._arm(la["pinned"])
        guard_passed = bool(la["guard_passed"])
        facts = AP.lead_twin(pinned, guard_passed, weightings)
        sel = lt[(lt["lead"] == L) & (lt["adopted"] == True) & (lt["line"] == "pooled")  # noqa: E712
                 & (lt["rows_basis"] == "all") & (lt["ladder_rows"] == "all")]
        if len(sel) != 1:
            raise WithWithoutRefusal("%s lead %d: no single adopted pooled line in ladder_table.csv" % (folder, L))
        adopted_col = str(sel["column"].iloc[0])
        tp = folder / "ladder" / ("lead_%d" % L) / "test_preds.parquet"
        names = set(pq.read_schema(str(tp)).names)
        want = ["unit", "group", "time", "year", "issue", "y", "normal", "legal_min", "legal_max", adopted_col]
        pre_ad = "pre__" + adopted_col[len("arm__"):] if adopted_col.startswith("arm__") else None
        if pre_ad is not None and pre_ad in names:
            want.append(pre_ad)
        twin_col = "arm__" + LA.arm_name(facts["twin"])
        twin_saved = twin_col in names
        t = pq.read_table(str(tp), columns=list(dict.fromkeys(want))).to_pandas()
        a_v = t[adopted_col].to_numpy(dtype=np.float64)
        a_pre = t[pre_ad].to_numpy(dtype=np.float64) if (pre_ad is not None and pre_ad in t.columns) else a_v
        batch = LAL.batch_keys(t["issue"].to_numpy(dtype=np.int64), cadence)
        edge = None if edges is None else edges[L]
        base = {"tag": LAL.POST_HOC_TAG, "package": package, "run": run_id, "lead": L, "pass": "lead %d" % L,
                "adopted_column": adopted_col, "twin_arm": LA.arm_name(facts["twin"]), "twin_kind": facts["kind"],
                "twin_simpler": facts["simpler"], "reference_gap": None, "max_ratio_tested": float("nan")}
        if AP.may_be_active(facts):
            if twin_saved:
                raise WithWithoutRefusal("%s lead %d: the twin is saved; this tool does not replay that case" % (folder, L))
            counts = pd.Series(np.asarray(batch, dtype=str)).value_counts()
            from treeroute import engine_constants as K
            lines = _score_rows(t, adopted_col, None, tol, floor, run_kind, edge, abs_edge)
            row = dict(base, twin_eligible=None, status=NOT_REPLAYABLE, replayable=False, batches=int(counts.size),
                       batches_tested=None, batches_fired=None, rows_switched=None, fired_batches="",
                       note="%s; %d of %d batches have >= %d rows and would be tested"
                            % (NOTE_NOT_REPLAYABLE, int((counts >= int(K.ALARM_MIN_BATCH_ROWS)).sum()),
                               int(counts.size), int(K.ALARM_MIN_BATCH_ROWS)))
            _write_rows(out_root, package, run_id, L, t[["unit", "group", "time", "year", "issue", "y"]].assign(
                batch=np.asarray(batch, dtype=str), adopted=a_v))
        else:
            status = LAL.pass_status(facts["declined"], facts["simpler"], None, None)
            rec = LAL.decide_alarm(status, a_v, a_pre, None, None, batch, None)
            if rec.rows_switched != 0 or not np.array_equal(rec.with_alarm, a_v, equal_nan=True):
                raise WithWithoutRefusal("%s lead %d: an inert pass switched rows" % (folder, L))
            t[LAL.WITH_ALARM_COLUMN] = np.asarray(rec.with_alarm, dtype=np.float64)
            lines = _score_rows(t, adopted_col, LAL.WITH_ALARM_COLUMN, tol, floor, run_kind, edge, abs_edge)
            why = ("guard failed: the lead adopts its decline target (v1), nothing to switch"
                   if facts["declined"] else "the twin is not the simpler arm: the alarm is inert")
            row = dict(base, twin_eligible=None, status=status, replayable=True, batches=len(rec.batches),
                       batches_tested=rec.batches_tested, batches_fired=rec.batches_fired,
                       rows_switched=rec.rows_switched, fired_batches="", note=why + "; no twin needed")
            _write_rows(out_root, package, run_id, L, t[["unit", "group", "time", "year", "issue", "y"]].assign(
                batch=np.asarray(rec.batch, dtype=str), adopted=a_v,
                with_alarm=np.asarray(rec.with_alarm, dtype=np.float64), fired=np.asarray(rec.fired, dtype=bool)))
        if lines[0]["mae_without"] != float(sel["mae"].iloc[0]):
            if not math.isclose(lines[0]["mae_without"], float(sel["mae"].iloc[0]), rel_tol=1e-12):
                raise WithWithoutRefusal("%s lead %d: adopted MAE %r is not ladder_table's %r"
                                         % (folder, L, lines[0]["mae_without"], float(sel["mae"].iloc[0])))
        out += [dict(row, **ln) for ln in lines]
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    import numpy as np
    import pandas as pd

    p = argparse.ArgumentParser(prog="tools/alarm_with_without.py", description=__doc__.splitlines()[0])
    p.add_argument("runs", nargs="+")
    p.add_argument("--out", required=True)
    p.add_argument("--magnitude-edges", action="append", default=[],
                   help="<package>=<csv with columns lead, q75_positive_donor_labels>")
    p.add_argument("--abs-edge", type=float, default=None)
    ns = p.parse_args(list(sys.argv[1:] if argv is None else argv))
    out_root = Path(ns.out).resolve()
    edges_by_pkg: Dict[str, Dict[int, float]] = {}
    for item in ns.magnitude_edges:
        pkg, path = item.split("=", 1)
        e = pd.read_csv(path)
        edges_by_pkg[pkg] = {int(r.lead): float(r.q75_positive_donor_labels) for r in e.itertuples()}
    from treeroute.layer import alarm as LAL

    print(LAL.ALARM_ORIGIN)
    rows: List[Dict[str, Any]] = []
    for run in ns.runs:
        folder = Path(run)
        if folder.resolve() == out_root or folder.resolve() in out_root.parents:
            raise WithWithoutRefusal("never write inside a run folder")
        pkg = str(_read_json(folder / "verdict.json")["package"])
        edges = edges_by_pkg.get(pkg)
        rows += _nowcast(folder, out_root, None if edges is None else edges[0], ns.abs_edge)
        rows += _leads(folder, out_root, edges, ns.abs_edge)
    df = pd.DataFrame(rows)
    df["change"] = df["mae_with"] - df["mae_without"]
    df["change_pct"] = 100.0 * df["change"] / df["mae_without"]
    cols = ["tag", "package", "run", "lead", "pass", "subset", "n", "status", "replayable", "batches",
            "batches_tested", "batches_fired", "rows_switched", "mae_without", "mae_with", "change", "change_pct",
            "adopted_column", "twin_arm", "twin_kind", "twin_simpler", "twin_eligible", "reference_gap",
            "max_ratio_tested", "fired_batches", "note"]
    df = df[cols]
    path = out_root / OUT_FILE
    text = df.to_csv(index=False, lineterminator="\n")
    out_root.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise WithWithoutRefusal("%s exists with other content; use a new --out folder" % path)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 40):
        print(df[["package", "lead", "subset", "n", "status", "batches_tested", "batches_fired", "mae_without",
                  "mae_with", "change"]].to_string(index=False))
    print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
