"""POST-HOC replay of the twin-disagreement alarm on saved engine v1 headline runs (owner ruling AE4; read-only).

HONESTY NOTE (owner ruling AE3, binding): the alarm was designed AFTER the engine v1 headline runs, from the diagnosis
of Parts 601-604. Everything this script writes is a POST-HOC replay, labelled post-hoc in every file. Only runs on new
data under engine v2 count as pre-registered for the alarm.

What it does, per run folder (nowcast only):
  - reads ONLY adoption.json (adopted arm, penalty, eligible arms), inner_preds.parquet (the adopted arm and its twin at
    the adopted point), test_preds.parquet (keys, issue, label, the adopted and twin columns before and after the clip,
    the reference column, normal and legal range; pyarrow column reads, so RAM stays small), verdict.json (band,
    tolerance, floor, reference), run_record.json (the run kind) and derived.json (cadence R1, overlap blocks R14);
  - applies the EXACT engine v2 rule (treeroute.layer.alarm: twin_of, twin_is_simpler, twin_eligible_nowcast,
    reference_gap, batch_keys, pass_status, decide_alarm; the A8 constants), and scores without and with the alarm
    with the engine's own functions (treeroute.report.metrics score_table; treeroute.pipeline.alarm_pass.verdict_with);
  - writes ONLY under <out>/<package>/<run id>/: alarm_replay.json (the alarm record's fields, post_hoc true, the AE3
    sentence) and alarm_replay_scores.csv (pooled, per year and per group: MAE without and with, the reference).
The v1 leads never routed the twin (a lead routes only its pinned arm), and routing it now would be a re-run, which
is not allowed: the leads are NOT replayed and every record says so.

Usage, from the engine folder (engine v2):
    py -3.9 tools/alarm_replay.py <run folder> [<run folder> ...] --out <replay folder>
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Sequence

ENGINE_DIR = Path(__file__).resolve().parents[1]
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

LEADS_NOTE = "not replayable (twin not saved in v1): a v1 lead routed only its pinned arm; routing the twin is a re-run"
SCORES_FILE = "alarm_replay_scores.csv"
RECORD_FILE = "alarm_replay.json"


class ReplayRefusal(Exception):
    """The replay refused (fail loudly)."""


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _arm(doc: Dict[str, Any]) -> Any:
    from treeroute.derive.shapes import Link
    from treeroute.layer import arms as LA

    return LA.ArmSpec(link=Link(doc["link"]), tool=LA.Tool(doc["tool"]), weighting=LA.Weighting(doc["weighting"]),
                      selectable=bool(doc["selectable"]))


def _cadence(doc: Dict[str, Any]) -> Optional[Any]:
    """derived.json R1 as the engine's Cadence; None for an irregular (day-dated, table) target."""
    from treeroute.derive.shapes import Cadence, CadenceKind, StepUnit

    kind = CadenceKind(doc["kind"])
    if kind is CadenceKind.IRREGULAR:
        return None
    return Cadence(kind=kind, length=doc.get("length"), unit=StepUnit(doc["unit"]) if doc.get("unit") else None,
                   composites_per_year=doc.get("composites_per_year"), composite_days=doc.get("composite_days"))


def _num(x: Any) -> Optional[float]:
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def _write_once(path: Path, text: str) -> None:
    """Write once; an existing file must hold the same text (a replay never changes what it wrote)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ReplayRefusal("%s exists with other content; write the replay to a new --out folder" % path)
        return
    with open(path, "x", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def replay_run(folder: Any, out_root: Any) -> Dict[str, Any]:
    """The nowcast alarm of one saved v1 run, replayed post hoc (module docstring). Returns the record written."""
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq

    from treeroute.layer import alarm as LAL
    from treeroute.layer import arms as LA
    from treeroute.pipeline import alarm_pass as AP
    from treeroute.report import metrics as M
    from treeroute.route.kinds import GridPoint

    folder = Path(folder)
    out_root = Path(out_root).resolve()
    if folder.resolve() in out_root.parents or folder.resolve() == out_root:
        raise ReplayRefusal("the replay never writes inside a run folder (%s)" % folder)
    adoption = _read_json(folder / "adoption.json")
    verdict = _read_json(folder / "verdict.json")
    record = _read_json(folder / "run_record.json")
    derived = _read_json(folder / "derived.json")
    package, run_id = str(verdict["package"]), folder.name
    kind = verdict["router_kind"]
    weightings = (LA.Weighting.UNWEIGHTED,) if kind == "region" else (LA.Weighting.UNWEIGHTED, LA.Weighting.GLS)
    declined = bool(adoption["declined"])
    reference_col = verdict["reference"]
    adopted_col = verdict.get("adopted_column") or (M.ARM_PREFIX + verdict["adopted"])
    rule = M.REFERENCE_DONOR_ROW_MEDIAN if verdict.get("reference_rule") == M.REFERENCE_DONOR_ROW_MEDIAN \
        else M.REFERENCE_OWN_LINK_TREES_OFF
    cadence = _cadence(derived["R1"]["value"])
    facts: Dict[str, Any] = {"declined": declined, "twin": None, "kind": None, "simpler": None, "eligible": None}
    ref = None
    if not declined:
        adopted = _arm(adoption["adopted"])
        point = GridPoint(float(adoption["penalty"]["level"]),
                          None if adoption["penalty"]["ratio"] is None else float(adoption["penalty"]["ratio"]))
        twin, tkind = LAL.twin_of(adopted, weightings)
        facts.update(twin=twin, kind=tkind, simpler=LAL.twin_is_simpler(adopted, twin),
                     eligible=LAL.twin_eligible_nowcast(twin, [_arm(a) for a in adoption.get("eligible") or []]))
        ref = AP.nowcast_reference(folder, adopted, twin, point)
    names = set(pq.read_schema(str(folder / "test_preds.parquet")).names)
    want = ["unit", "group", "time", "year", "lead", "issue", "y", "normal", "legal_min", "legal_max", adopted_col,
            reference_col]
    pre_ad = M.PRE_PREFIX + adopted_col[len(M.ARM_PREFIX):] if adopted_col.startswith(M.ARM_PREFIX) else None
    twin_col = pre_tw = None
    if facts["twin"] is not None:
        twin_col = M.ARM_PREFIX + LA.arm_name(facts["twin"])
        pre_tw = M.PRE_PREFIX + LA.arm_name(facts["twin"])
        want += [twin_col, pre_tw]
    if pre_ad is not None and pre_ad in names:
        want.append(pre_ad)
    if reference_col.startswith(M.ARM_PREFIX):
        pre_ref = M.PRE_PREFIX + reference_col[len(M.ARM_PREFIX):]
        if pre_ref in names:
            want.append(pre_ref)
    want = list(dict.fromkeys(want))
    missing = [c for c in want if c not in names]
    if missing:
        raise ReplayRefusal("%s: test_preds.parquet lacks %s" % (folder, missing))
    t = pq.read_table(str(folder / "test_preds.parquet"), columns=want).to_pandas()
    a_v = t[adopted_col].to_numpy(dtype=np.float64)
    a_pre = t[pre_ad].to_numpy(dtype=np.float64) if (pre_ad is not None and pre_ad in t.columns) else a_v
    tw = t[twin_col].to_numpy(dtype=np.float64) if twin_col else None
    tw_pre = t[pre_tw].to_numpy(dtype=np.float64) if pre_tw else None
    gap = None if ref is None else ref["gap"]
    status = LAL.pass_status(declined, facts["simpler"], facts["eligible"], gap)
    batch = LAL.batch_keys(t["issue"].to_numpy(dtype=np.int64), cadence)
    rec = LAL.decide_alarm(status, a_v, a_pre, tw, tw_pre, batch, gap)
    frame = t.copy()
    frame[LAL.WITH_ALARM_COLUMN] = np.asarray(rec.with_alarm, dtype=np.float64)
    if pre_ad is not None and pre_ad in t.columns:
        frame[LAL.PRE_WITH_ALARM_COLUMN] = np.asarray(rec.pre_with_alarm, dtype=np.float64)
    tol, floor = float(verdict["hit_tolerance"]), verdict.get("measurement_error_floor")
    run_kind = record["kind"]
    blocks = {g: int(i) for g, i in derived["R14:overlap_blocks"]["value"]["block_of_group"].items()}
    w = AP.verdict_with(frame, reference_col, adopted_col, float(verdict["band"]), declined, rule, tol, floor,
                        run_kind, blocks)
    if not math.isclose(w["pooled_mae_adopted"], float(verdict["pooled_mae_adopted"]), rel_tol=0.0, abs_tol=0.0):
        raise ReplayRefusal("%s: the adopted pooled MAE recomputed (%r) is not verdict.json's (%r)"
                            % (folder, w["pooled_mae_adopted"], verdict["pooled_mae_adopted"]))
    lines = []
    for by, label in (((), "pooled"), (("year",), "year"), (("group",), "group")):
        table = M.score_table(frame[["unit", "group", "time", "year", "y", "normal", "legal_min", "legal_max",
                                     adopted_col, reference_col, LAL.WITH_ALARM_COLUMN]], by, tol, floor, run_kind)
        line = M.LINE_POOLED if not by else M.LINE_KEY
        sel = table[(table["line"] == line) & (table["rows_basis"] == M.ROWS_BASIS_ALL)]
        keys = [None] if not by else sorted(set(sel[by[0]].tolist()))
        for k in keys:
            sub = sel if k is None else sel[sel[by[0]] == k]

            def mae(col):
                hit = sub[sub["column"] == col]
                return float(hit["mae"].iloc[0]) if len(hit) == 1 else float("nan")
            lines.append({"tag": LAL.POST_HOC_TAG, "package": package, "run": run_id, "lead": 0, "line": label,
                          "key": "" if k is None else str(k), "mae_without": mae(adopted_col),
                          "mae_with": mae(LAL.WITH_ALARM_COLUMN), "mae_reference": mae(reference_col),
                          "n": int(sub[sub["column"] == adopted_col]["n"].iloc[0])})
    scores = pd.DataFrame(lines)
    out_dir = out_root / package / run_id
    scores_text = scores.to_csv(index=False, lineterminator="\n")
    context = {"lead": 0, "pass": "nowcast test pass (POST-HOC replay of a saved v1 run)",
               "adoption_file": "adoption.json",
               "adoption_sha256": hashlib.sha256((folder / "adoption.json").read_bytes()).hexdigest(),
               "adopted_arm": verdict["adopted"], "adopted_column": adopted_col,
               "twin_arm": None if facts["twin"] is None else LA.arm_name(facts["twin"]), "twin_kind": facts["kind"],
               "twin_simpler": facts["simpler"], "twin_eligible": facts["eligible"],
               "eligibility_basis": {"basis": "Adoption.eligible of the saved adoption.json"},
               "twin_routed": facts["twin"] is not None,
               "reference": None if ref is None else dict(ref, gap=_num(ref["gap"])),
               "batch_rule": AP.BATCH_RULE, "test_rows": int(a_v.size)}
    doc = LAL.alarm_document(rec, context)
    doc.update({"post_hoc": True, "tag": LAL.POST_HOC_TAG, "package": package, "run_id": run_id,
                "run_folder": str(folder), "leads": LEADS_NOTE,
                "scores": {"pooled_mae_without": w["pooled_mae_adopted"], "pooled_mae_with": w["pooled_mae"],
                           "pooled_mae_reference": w["pooled_mae_reference"],
                           "verdict_without": verdict["verdict"], "verdict_with": w["verdict"],
                           "blocked_jackknife_with": w["blocked_jackknife"], "band": float(verdict["band"])},
                "scores_file": SCORES_FILE,
                "scores_sha256": hashlib.sha256(scores_text.encode("utf-8")).hexdigest()})
    doc = json.loads(json.dumps(M._json_safe(doc), sort_keys=True))
    _write_once(out_dir / SCORES_FILE, scores_text)
    _write_once(out_dir / RECORD_FILE, json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="tools/alarm_replay.py",
                                     description="POST-HOC replay (AE3) of the twin-disagreement alarm on saved v1 runs "
                                                 "(nowcast only, read-only).")
    parser.add_argument("runs", nargs="+", help="saved v1 run folders")
    parser.add_argument("--out", required=True, help="the replay folder (never inside a run folder)")
    ns = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    from treeroute.layer import alarm as LAL

    print(LAL.ALARM_ORIGIN)
    for run in ns.runs:
        d = replay_run(run, ns.out)
        s = d["scores"]
        print("%s %s %s: %s %s -> twin %s, status %s, %d of %d batch(es) switched (%d rows); pooled MAE without %.6g, "
              "with %.6g" % (LAL.POST_HOC_TAG, d["package"], d["run_id"], d["adopted_arm"], d["adopted_column"],
                             d["twin_arm"], d["status"], d["batches_fired"], len(d["batches"]), d["rows_switched"],
                             s["pooled_mae_without"], s["pooled_mae_with"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
