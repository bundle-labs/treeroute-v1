"""The headline tables, built FROM SAVED ROW-LEVEL PREDICTIONS of finished headline runs (plan 7.1
'headline_table.csv / .html: built from saved headline rows only; refuses smoke and legacy rows; re-checks scored
units = derived units'; plan 8.1 M7; R31-R35).

Usage, from the engine folder:

    py -3.9 -m treeroute_report.table <run_root>                     every finished headline run under it
    py -3.9 -m treeroute_report.table <run folder> [<run folder> ...] those runs only
    options: --out DIR (default <run root>/_headline_tables), --registry-dir DIR (default: the machine file's)
    TEST ONLY: --smoke-watermark renders finished SMOKE run folders, every file stamped 'SMOKE - NOT HEADLINE'

What it refuses (fail loudly; nothing is written then):
  - a DRAFT run, a smoke run, a legacy run, a run with a not-headline reason or an unfinished run, through the
    engine's own pipeline.record.check_headline_run, and saved rows that do not score exactly the derived scored
    units (pipeline.record.check_scored_units, G-SPLIT on the outputs; the units owner ruling S1 left with no
    scored row are not expected and are disclosed, kind score_context_left_out); with --smoke-watermark only kind 'smoke';
  - two finished headline runs of one package under a run root (name the run folders instead), and a package
    under a run root whose headline runs are all unfinished (it would drop out of the tables silently; an
    unfinished run beside a finished one of the same package is skipped and noted);
  - a run whose recorded verdicts differ from the ones recomputed here from its saved rows: the nowcast verdict
    (verdict.json), each band pair, the blocked jackknife (a verdict.json without one refuses too), the band
    itself when the run derived it from its own contrasts, and every lead's verdict on the ladder's common rows
    (ladder/ladder.json). A band from another source (registry/bands.csv, once the engine writes it) is taken as
    recorded and NOT recomputed: the verdict row's band_check says so, and the markdown names those runs;
  - a headline run whose continuity groups (continuity_groups.yaml) are not all scored, or a package with no entry
    there (an empty list says the package has no old split).

Every score comes from the engine's signed treeroute.report.metrics functions on the saved rows (score_table,
metric_by_key, single_verdict, contrast_tag, group_jackknife, blocked_jackknife, equivalence_band, common_rows);
no formula is re-implemented here. The hit tolerance and the declared measurement floor are read from the run's
verdict.json (they are fitted on donor rows, which a run does not save). Uncertainty is over groups (the jackknife
at 1.96, Q19 a); no multiplicity correction (Q21 a); never R2 alone: MAE, anomaly R2 against the per-unit normal,
corr2 and the hit rate are printed together, each beside guess-normal and the last-5-years normal.

Rows bases (R34): 'all' = every saved row of the lead; 'common' = the rows with a label and an adopted prediction
at EVERY lead, lead 0 included (the ladder's basis). The nowcast verdict is the 'all' verdict of lead 0
(verdict.json); each lead's verdict is its 'common' verdict (ladder.json).

Outputs (CSV with LF line ends, and one markdown file), each named by its content's SHA-256 (12 hex), written
once; a clean re-run on the same runs rebuilds the same bytes and the same names:
  headline_<h>.csv     per package x lead x rows basis x line (pooled; macro = unweighted mean over groups):
                       MAE, anomaly R2, corr2, hit rate (R32 tolerance; and at the declared floor), calibration
                       ratio, pre-clip rate, the strict top-10% detection score and its event count (R33) for the
                       adopted arm, its reference (own-link trees-off), guess-normal and the last-5-years normal;
                       predict-zero, persistence and damped persistence MAE beside
  per_year_<h>.csv     the same per test year;   per_group_<h>.csv  the same per group (with the noise note)
  per_stratum_<h>.csv  R34 per declared report stratum (lead 0, every line): COPIED from the engine's
                       per_stratum.csv, NOT recomputed (the units' stratum values and the donor-row edges are not in
                       the saved rows); its stratum columns are checked against run_record.json and its edges
                       against verdict.json, and a declared stratum without the file refuses
  continuity_<h>.csv   the old hard-split test groups alone, from the same run, 'continuity, not a replication',
                       with their own jackknife and the package's band
  subsets_<h>.csv      reporting-only subset rows: without the seen_during_design groups (Q49) and the year subsets
                       of report_rows.yaml (NDVI's 2021-2023 row, Q40 a)
  verdicts_<h>.csv     recorded and recomputed verdicts side by side (always equal, or the build refuses)
  scores_long_<h>.csv  every line of every score table behind the others
  disclosures_<h>.csv  each run's limits, departures, not-headline reasons and listed columns
  headline_<h>.md      the tables above as markdown;   manifest_<h>.json  inputs and outputs with their hashes

The twin-disagreement alarm (owner ruling AE, engine v2; AE2: every run is reported WITH and WITHOUT it). A run whose
passes locked an alarm record carries alarm_preds.parquet per lead: its 'with alarm' column joins the saved rows as
'arm__with_alarm' (role with_alarm), so the headline, per-year and per-group tables gain *_with_alarm columns and
verdicts_<h>.csv one 'with alarm' row per lead beside the 'adopted' one (column verdict_of). The build REFUSES a run
whose alarm_preds adopted column is not the saved adopted column bit for bit, or whose recorded with-alarm verdicts
(alarm_verdict.json, ladder/alarm_ladder.json) differ from the ones recomputed here. A run with no alarm record (an
engine v1 run) gets NaN with-alarm columns and the disclosure 'no alarm recorded (engine v1 run)'. --alarm-replay DIR
adds the post-hoc replay of saved v1 runs (tools/alarm_replay.py) as alarm_replay_<h>.csv, every row tagged
'POST-HOC (AE3)'. The markdown's section on the alarm opens with ruling AE3's sentence: the alarm was designed after
the v1 headline runs.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from treeroute.errors import TreerouteError
from treeroute_report import common as C
from treeroute_report.common import ReportRefusal

WATERMARK = "SMOKE - NOT HEADLINE"
SMOKE_PREFIX = "SMOKE_NOT_HEADLINE_"
CONTINUITY_FILE = C.REPORT_DIR / "continuity_groups.yaml"
HISTORY_FILE = C.REPORT_DIR / "history_bands.yaml"
ROWS_FILE = C.REPORT_DIR / "report_rows.yaml"
DEFAULT_OUT = "_headline_tables"
CONTINUITY_LABEL = "continuity, not a replication"
BASIS_ALL = "all"
BASIS_COMMON = "common"
ROLES = ("adopted", "reference", "guess_normal", "last5_normal", "with_alarm")
WITH_ALARM = "arm__with_alarm"                 # layer/alarm.py WITH_ALARM_COLUMN (never a real arm name)
PRE_WITH_ALARM = "pre__with_alarm"
NO_ALARM_TEXT = "no alarm recorded (engine v1 run)"
VERDICT_OF_ADOPTED = "adopted"
VERDICT_OF_ALARM = "with alarm"
BASELINE_OF_ROLE = {"guess_normal": "base__guess_normal", "last5_normal": "base__last5_normal"}
BESIDE_MAE = ("base__predict_zero", "base__persistence", "base__damped_persistence")
METRICS = ("mae", "anom_r2", "corr2", "hit", "hit_floor", "calibration_ratio", "preclip_rate", "detection",
           "detection_events")
LADDER_DIR = "ladder"
# R34 per declared report stratum: the engine's report pass writes per_stratum.csv from the same saved rows, but the
# units' stratum values and the donor-row quartile edges are not in the saved rows, so this builder copies the
# engine's table (checking its stratum columns against run_record.json and its edges against verdict.json) and
# says it is NOT recomputed here
STRATUM_SOURCE = ("copied from the engine's per_stratum.csv (report pass, the same saved rows); NOT recomputed here: "
                  "the units' stratum values and the donor-row edges are not in the saved rows")
STRATUM_EDGE_COLUMNS = ("edge_q25", "edge_q50", "edge_q75")
LADDER_FILE = "ladder.json"
LEAD_FILE = "lead.json"
OWN_BAND_SOURCE = "this run's own"
# the band column of a verdict row: recomputed from the run's own D75 contrasts, or taken as the run recorded it
# (a band from registry/bands.csv; the engine does not write that file yet, so this builder cannot check it)
BAND_RECOMPUTED = "recomputed from this run's D75 contrasts, equal"
BAND_AS_RECORDED = "taken as recorded, NOT recomputed (band from another source)"
NOISE_NOTE = ("one group's score is noisy (%d scored units); the pooled headline and the all-group jackknife decide, "
              "never one group (R34)")
EXIT_REFUSED = 4


class TableRefusal(ReportRefusal):
    """The table builder refused."""


def _yaml(path: Path) -> Dict[str, Any]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TableRefusal("TABLE", "%s is not a mapping" % path)
    return data


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _same(a: Any, b: Any) -> bool:
    """Exact equality of JSON-like values; NaN equals NaN and None (a recorded NaN is written as null)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    na = a is None or (isinstance(a, float) and math.isnan(a))
    nb = b is None or (isinstance(b, float) and math.isnan(b))
    if na or nb:
        return na and nb
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    return a == b


# ===================================================================================== the runs
class Run(object):
    """One finished run folder, read (never written)."""

    def __init__(self, folder: Path, watermark: bool):
        from treeroute.pipeline import record as REC
        from treeroute.report import metrics as M

        self.folder = Path(folder)
        if watermark:
            rec_path = self.folder / REC.RUN_RECORD
            if not rec_path.is_file():
                raise TableRefusal("G-LEGACY", "run %s: no %s: not a pipeline run" % (self.folder, REC.RUN_RECORD))
            self.record = _read_json(rec_path)
            if self.record.get("kind") != REC.KIND_SMOKE:
                raise TableRefusal("TABLE", "run %s: --smoke-watermark renders smoke runs only, not a %r run"
                                   % (self.folder, self.record.get("kind")))
            if not (self.folder / "DONE.json").is_file():
                raise TableRefusal("G-LEGACY", "run %s has not finished" % self.folder)
            self.verdict = _read_json(self.folder / REC.VERDICT_FILE)
        else:
            checked = REC.check_headline_run(self.folder)
            REC.check_scored_units(self.folder)
            self.record, self.verdict = checked["record"], checked["verdict"]
        self.package = self.record["package"]
        self.kind = self.record["kind"]
        self.derived = _read_json(self.folder / REC.DERIVED_FILE)
        self.tol = self.verdict["hit_tolerance"]
        self.floor = self.verdict.get("measurement_error_floor")
        self.band = float(self.verdict["band"])
        blocks = self.derived["R14:overlap_blocks"]["value"]
        self.block_of_group = {g: int(i) for g, i in blocks["block_of_group"].items()}
        self.block_members = {int(i): "+".join(m) for i, m in enumerate(blocks["members"])}
        self.frames = {0: M.read_rows(self.folder / REC.TEST_PREDS)}
        self.files = {"test_preds_lead_0": self.folder / REC.TEST_PREDS, "verdict": self.folder / REC.VERDICT_FILE,
                      "run_record": self.folder / REC.RUN_RECORD, "derived": self.folder / REC.DERIVED_FILE}
        declined = bool(self.verdict["declined"])
        # owner ruling V1: a table run's verdict names its adopted column (base__donor_median when the neighbour
        # nowcast declined); grid verdicts carry no such key, so the old expression runs for them
        self.info = {0: {"adopted": self.verdict.get("adopted_column") or M.ARM_PREFIX + self.verdict["adopted"],
                         "reference": self.verdict["reference"],
                         "declined": declined}}
        self.per_stratum = self._read_strata()
        derived_leads = list(self.derived["R10"]["value"].get("leads") or [])
        ladder_path = self.folder / LADDER_DIR / LADDER_FILE
        self.ladder = None
        if ladder_path.is_file():
            self.ladder = _read_json(ladder_path)
            self.files["ladder"] = ladder_path
            if list(self.ladder["leads"]) != derived_leads:
                raise TableRefusal("TABLE", "run %s: ladder.json runs leads %s, derived.json R10 says %s"
                                   % (self.folder, self.ladder["leads"], derived_leads))
            if not (_same(self.ladder["hit_tolerance"], self.tol)
                    and _same(self.ladder.get("measurement_error_floor"), self.floor)):
                raise TableRefusal("TABLE", "run %s: the ladder's hit tolerance or floor differs from verdict.json's"
                                   % self.folder)
            for lead in self.ladder["leads"]:
                lead_dir = self.folder / LADDER_DIR / ("lead_%d" % int(lead))
                self.frames[int(lead)] = M.read_rows(lead_dir / REC.TEST_PREDS)
                self.files["test_preds_lead_%d" % int(lead)] = lead_dir / REC.TEST_PREDS
                lr = _read_json(lead_dir / LEAD_FILE)
                self.info[int(lead)] = {"adopted": lr["test"]["adopted_column"],
                                        "reference": lr["test"]["reference_column"],
                                        "declined": bool(lr["declined_at_lead"])}
        elif derived_leads:
            raise TableRefusal("TABLE", "run %s derives leads %s but holds no %s/%s: the ladder is missing"
                               % (self.folder, derived_leads, LADDER_DIR, LADDER_FILE))
        for lead, frame in self.frames.items():
            leads = sorted(set(int(v) for v in frame["lead"].tolist()))
            if leads != [lead]:
                raise TableRefusal("TABLE", "run %s: the saved rows of lead %d hold leads %s" % (self.folder, lead, leads))
            for role in ("adopted", "reference"):
                if self.info[lead][role] not in frame.columns:
                    raise TableRefusal("TABLE", "run %s lead %d: the %s column %r is not saved"
                                       % (self.folder, lead, role, self.info[lead][role]))
        self._read_alarm()

    def _read_alarm(self) -> None:
        """Owner ruling AE: every pass's alarm record and its with-alarm column joined to the saved rows (refused when
        its adopted column is not the saved one bit for bit, or only some passes have one); none at all: an engine v1
        run (NaN with-alarm columns)."""
        import numpy as np
        import pandas as pd

        from treeroute.labels.vault import ALARM_FILE
        from treeroute.pipeline import alarm_pass as AP

        self.alarm: Dict[int, Dict[str, Any]] = {}
        self.alarm_verdict = None
        self.alarm_ladder = None
        found = {}
        for lead in self.frames:
            base = self.folder if lead == 0 else self.folder / LADDER_DIR / ("lead_%d" % lead)
            found[lead] = (base / AP.ALARM_PREDS, self.folder / (ALARM_FILE % lead))
        have = {lead: p.is_file() and d.is_file() for lead, (p, d) in found.items()}
        if not any(have.values()):
            return
        if not all(have.values()):
            raise TableRefusal("AE2", "run %s: the alarm is recorded for leads %s but not for %s"
                               % (self.folder, sorted(k for k, v in have.items() if v),
                                  sorted(k for k, v in have.items() if not v)))
        for lead, (path, doc_path) in sorted(found.items()):
            doc = _read_json(doc_path)
            alarm = pd.read_parquet(path)
            if "y" in alarm.columns:
                raise TableRefusal("AE1", "run %s lead %d: %s holds a label column" % (self.folder, lead, path.name))
            try:
                joined = AP.with_alarm_frame(self.frames[lead], alarm, self.info[lead]["adopted"])
            except TreerouteError as exc:
                raise TableRefusal("AE2", "run %s lead %d: %s" % (self.folder, lead, exc)) from exc
            if doc.get("adopted_column") != self.info[lead]["adopted"]:
                raise TableRefusal("AE2", "run %s lead %d: the alarm record names the adopted column %r, the run %r"
                                   % (self.folder, lead, doc.get("adopted_column"), self.info[lead]["adopted"]))
            fired = alarm["fired"].to_numpy(dtype=bool)
            if int(fired.sum()) != int(doc["rows_switched"]) or not np.array_equal(
                    alarm["with_alarm"].to_numpy(dtype=np.float64)[~fired],
                    alarm["adopted"].to_numpy(dtype=np.float64)[~fired]):
                raise TableRefusal("AE2", "run %s lead %d: the with-alarm column differs from the adopted arm outside "
                                   "the rows the record says switched" % (self.folder, lead))
            self.frames[lead] = joined
            self.alarm[lead] = doc
            self.files["alarm_preds_lead_%d" % lead] = path
            self.files["alarm_record_lead_%d" % lead] = doc_path
        vpath = self.folder / AP.ALARM_VERDICT
        if not vpath.is_file():
            raise TableRefusal("AE2", "run %s records the alarm but holds no %s" % (self.folder, AP.ALARM_VERDICT))
        self.alarm_verdict = _read_json(vpath)
        self.files["alarm_verdict"] = vpath
        if self.ladder is not None:
            lpath = self.folder / LADDER_DIR / AP.ALARM_LADDER_RECORD
            if not lpath.is_file():
                raise TableRefusal("AE2", "run %s records the alarm but holds no %s/%s"
                                   % (self.folder, LADDER_DIR, AP.ALARM_LADDER_RECORD))
            self.alarm_ladder = _read_json(lpath)
            self.files["alarm_ladder"] = lpath

    def _read_strata(self) -> Optional[Any]:
        """The engine's per_stratum.csv when the run declared report strata (run_record.json 'strata'): its stratum
        columns must be the declared ones and its edges the ones verdict.json records; a declared stratum without
        the file refuses."""
        import pandas as pd
        from treeroute.pipeline.passes import PER_STRATUM

        declared = sorted(str(s) for s in (self.record.get("strata") or []))
        path = self.folder / PER_STRATUM
        if not declared:
            if path.is_file():
                raise TableRefusal("R34", "run %s holds %s but run_record.json declares no report stratum"
                                   % (self.folder, PER_STRATUM))
            return None
        if not path.is_file():
            raise TableRefusal("R34", "run %s declares report strata %s but holds no %s" % (self.folder, declared,
                                                                                         PER_STRATUM))
        table = pd.read_csv(path)
        found = sorted(set(str(s) for s in table["stratum_column"].tolist()))
        if found != declared:
            raise TableRefusal("R34", "run %s: %s covers strata %s, run_record.json declares %s"
                               % (self.folder, PER_STRATUM, found, declared))
        recorded = self.verdict.get("strata") or {}
        for col in declared:
            sel = table[table["stratum_column"] == col]
            if "edges" not in (recorded.get(col) or {"edges": None}) and (recorded.get(col) or {}).get("values") is not None:
                # the table option (owner item O18): a string stratum is scored per value and records no edges; grid
                # runs always record edges, so they never take this branch
                continue
            edges = sorted(set(tuple(float(x) for x in r) for r in sel[list(STRATUM_EDGE_COLUMNS)].to_numpy()))
            want = (recorded.get(col) or {}).get("edges")
            if len(edges) != 1 or want is None or not _same(list(edges[0]), list(want)):
                raise TableRefusal("R34", "run %s: the %s edges in %s (%s) differ from verdict.json's (%s)"
                                   % (self.folder, col, PER_STRATUM, edges, want))
        self.files["per_stratum"] = path
        return table

    def column(self, lead: int, role: str) -> Optional[str]:
        if role in ("adopted", "reference"):
            return self.info[lead][role]
        if role == "with_alarm":
            return WITH_ALARM if WITH_ALARM in self.frames[lead].columns else None
        col = BASELINE_OF_ROLE[role]
        return col if col in self.frames[lead].columns else None

    def bases(self) -> Dict[int, Dict[str, Any]]:
        """{lead: {basis: rows}}: 'all' for every lead; 'common' for every lead when a ladder exists."""
        import numpy as np
        from treeroute.report import metrics as M

        out = {lead: {BASIS_ALL: f} for lead, f in self.frames.items()}
        if self.ladder is None:
            return out

        def keys(f, col=None):
            ok = np.ones(len(f), dtype=bool)
            if col is not None:
                ok = np.isfinite(f["y"].to_numpy(dtype=np.float64)) & np.isfinite(f[col].to_numpy(dtype=np.float64))
            return np.asarray(["%s\t%d" % (u, t) for u, t in zip(f["unit"].to_numpy(dtype=object)[ok].tolist(),
                                                               f["time"].to_numpy(dtype=np.int64)[ok].tolist())],
                              dtype=object)
        common = M.common_rows({L: keys(f, self.info[L]["adopted"]) for L, f in self.frames.items()})
        self.common_rows = int(len(common))
        for lead, f in self.frames.items():
            out[lead][BASIS_COMMON] = f[np.isin(keys(f), common)].reset_index(drop=True)
        return out


def find_runs(paths: Sequence[Any], watermark: bool) -> Tuple[List[Path], List[str], Optional[Path]]:
    """(run folders, notes on skipped unfinished runs, the run root when one was named)."""
    from treeroute.pipeline import record as REC

    folders, notes, root = [], [], None
    for raw in paths:
        p = Path(raw)
        if (p / REC.RUN_RECORD).is_file():
            folders.append(p)
            continue
        if not p.is_dir():
            raise TableRefusal("TABLE", "%s is neither a run folder nor a run root" % p)
        if watermark:
            raise TableRefusal("TABLE", "--smoke-watermark takes smoke run folders, not a run root (%s)" % p)
        root = p
        found, unfinished = {}, {}
        for pkg_dir in sorted(q for q in p.iterdir() if q.is_dir()):
            kind_dir = pkg_dir / REC.KIND_HEADLINE
            if not kind_dir.is_dir():
                continue
            for run in sorted(q for q in kind_dir.iterdir() if q.is_dir()):
                if not (run / "DONE.json").is_file():
                    unfinished.setdefault(pkg_dir.name, []).append(run)
                    continue
                found.setdefault(pkg_dir.name, []).append(run)
        # a package whose only headline runs are unfinished would drop out of the tables silently: refuse
        only_unfinished = sorted(set(unfinished) - set(found))
        if only_unfinished:
            raise TableRefusal("TABLE", "package(s) %s under %s have unfinished headline runs and no finished one: %s"
                               % (", ".join(only_unfinished), p,
                                  ", ".join(str(r) for k in only_unfinished for r in unfinished[k])),
                               fix="finish the run, or name the run folders to tabulate (leaving the package out "
                                   "on purpose)")
        for pkg, runs in sorted(unfinished.items()):
            notes += ["unfinished headline run skipped (package %s has a finished one): %s" % (pkg, r) for r in runs]
        for pkg, runs in sorted(found.items()):
            if len(runs) > 1:
                raise TableRefusal("TABLE", "%d finished headline runs of package %s under %s: %s"
                                   % (len(runs), pkg, p, ", ".join(r.name for r in runs)),
                                   fix="name the run folders to tabulate")
            folders.extend(runs)
    if not folders:
        raise TableRefusal("G-LEGACY", "no finished headline run to tabulate under %s" % ", ".join(map(str, paths)))
    names = [f.resolve() for f in folders]
    if len(set(names)) != len(names):
        raise TableRefusal("TABLE", "a run folder is named twice")
    return folders, notes, root


# ======================================================================================= tables
def _line(table: Any, column: str, line: str, basis: str = None) -> Optional[Dict[str, Any]]:
    from treeroute.report import metrics as M

    basis = basis or M.ROWS_BASIS_ALL
    sel = table[(table["column"] == column) & (table["line"] == line) & (table["rows_basis"] == basis)]
    if sel.empty:
        return None
    if len(sel) != 1:
        raise TableRefusal("R34", "the score table holds %d %s lines for %s" % (len(sel), line, column))
    return sel.iloc[0].to_dict()


def _role_metrics(table: Any, run: Run, lead: int, line: str, key: Optional[Tuple[str, Any]] = None) -> Dict[str, Any]:
    """{<metric>_<role>: value, n_<role>: rows} for the four roles (NaN where a baseline is not saved)."""
    out: Dict[str, Any] = {}
    sub = table if key is None else table[table[key[0]] == key[1]]
    for role in ROLES:
        col = run.column(lead, role)
        rec = _line(sub, col, line) if col is not None else None
        for m in METRICS:
            out["%s_%s" % (m, role)] = float(rec[m]) if rec is not None else float("nan")
        out["n_%s" % role] = int(rec["n"]) if rec is not None else 0
        out["rows_missing_%s" % role] = int(rec["rows_missing"]) if rec is not None else 0
    for col in BESIDE_MAE:
        rec = _line(sub, col, line) if col in run.frames[lead].columns else None
        out["mae_%s" % col[len("base__"):]] = float(rec["mae"]) if rec is not None else float("nan")
    return out


def _verdict_of(run: Run, frame: Any, lead: int, tol: float, floor: Optional[float], groups=None, column=None):
    """single_verdict on these rows (the engine's own function), and the per-group contrast. column: the scored
    column (the adopted one by default; WITH_ALARM for the with-alarm verdict)."""
    from treeroute.report import metrics as M

    if groups is not None:
        frame = frame[frame["group"].isin(groups)].reset_index(drop=True)
    tg = M.score_table(frame, ("group",), tol, floor, run.kind)
    tp = M.score_table(frame, (), tol, floor, run.kind)
    ref, ad = run.info[lead]["reference"], (column or run.info[lead]["adopted"])
    per_ref = M.metric_by_key(tg, ref, "mae", "group")
    per_ad = M.metric_by_key(tg, ad, "mae", "group")

    def pooled(col):
        return float(_line(tp, col, M.LINE_POOLED)["mae"])
    # the table option's neighbour runs record reference_rule donor_row_median (signed R34); grid runs record none
    rule = M.REFERENCE_DONOR_ROW_MEDIAN if run.verdict.get("reference_rule") == M.REFERENCE_DONOR_ROW_MEDIAN \
        else M.REFERENCE_OWN_LINK_TREES_OFF
    v = M.single_verdict(per_ref, per_ad, pooled(ref), pooled(ad), run.band, run.info[lead]["declined"], rule)
    contrast = {g: per_ref[g] - per_ad[g] for g in per_ref}
    return v, contrast, per_ref, per_ad, tg, (pooled(ref), pooled(ad))


def _refuse_mismatch(run: Run, what: str, recorded: Any, recomputed: Any) -> None:
    raise TableRefusal("R34-RECOMPUTE", "run %s: %s as recorded differs from the one recomputed from the saved rows: "
                       "recorded %s; recomputed %s" % (run.folder, what, json.dumps(recorded, default=str)[:600],
                                                       json.dumps(recomputed, default=str)[:600]),
                       fix="the run's records and its saved rows disagree: find out why before any table is built")


def check_verdicts(run: Run, bases: Mapping[int, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Recompute every verdict the run recorded and check it equals the record. Returns the verdict rows."""
    import numpy as np
    from treeroute.report import metrics as M

    rows = []
    hist = run.history_band
    v, contrast, per_ref, per_ad, tg, (p_ref, p_ad) = _verdict_of(run, bases[0][BASIS_ALL], 0, run.tol, run.floor)
    rec_now = M.verdict_record(v)
    if not _same(run.verdict["verdict"], rec_now):
        _refuse_mismatch(run, "the nowcast verdict (verdict.json)", run.verdict["verdict"], rec_now)
    if not (_same(run.verdict["pooled_mae_adopted"], p_ad) and _same(run.verdict["pooled_mae_reference"], p_ref)):
        _refuse_mismatch(run, "the nowcast pooled MAEs", [run.verdict["pooled_mae_adopted"],
                                                          run.verdict["pooled_mae_reference"]], [p_ad, p_ref])
    # band pairs (D75) and the band
    per_group = {c: M.metric_by_key(tg, c, "mae", "group")
                 for c in tg["column"].unique().tolist() if c.startswith((M.ARM_PREFIX, M.PLACEBO_PREFIX))}
    ses = []
    for pair in run.verdict.get("band_pairs") or []:
        ref, arm = pair["reference"], pair["arm"]
        groups = sorted(per_group[ref])
        dv = np.array([per_group[ref][g] - per_group[arm][g] for g in groups])
        tag, jk = M.contrast_tag(dv, run.band)
        identical = bool(np.all(np.abs(dv) <= M.IDENTICAL_ATOL))
        now = M._json_safe({"reference": ref, "arm": arm, "mean": jk.mean, "se": jk.se, "low": jk.low, "high": jk.high,
                            "n_groups": jk.n_groups, "identical": identical, "tag": tag.value})
        if not _same(pair, now):
            _refuse_mismatch(run, "band pair %s vs %s" % (arm, ref), pair, now)
        if not identical:
            ses.append(jk.se)
    own_band = str(run.verdict.get("band_source", "")).startswith(OWN_BAND_SOURCE)
    if own_band:
        band_now = M.equivalence_band(ses)
        if not _same(run.band, band_now):
            _refuse_mismatch(run, "the band (the median SE of the non-identical band pairs)", run.band, band_now)
    # the blocked jackknife (report only); a verdict.json without it is refused, never skipped
    blocked = M.blocked_jackknife(contrast, {g: run.block_of_group[g] for g in contrast})
    flag = M.blocked_jackknife_flag(v.contrast, blocked)
    bj_now = M._json_safe({"mean": blocked.mean, "se": blocked.se, "low": blocked.low, "high": blocked.high,
                           "n_blocks": blocked.n_groups, "flag": flag})
    if "blocked_jackknife" not in run.verdict:
        raise TableRefusal("R34-RECOMPUTE", "run %s: verdict.json records no blocked_jackknife, so the table cannot "
                           "check the one it recomputes (%s)" % (run.folder, json.dumps(bj_now, default=str)[:300]),
                           fix="the engine's report pass writes it (pipeline/passes.py): find out why it is missing")
    if not _same(run.verdict["blocked_jackknife"], bj_now):
        _refuse_mismatch(run, "the blocked jackknife", run.verdict["blocked_jackknife"], bj_now)
    rows.append(_verdict_row(run, 0, BASIS_ALL, "verdict.json", rec_now, own_band, hist, bj_now))
    # every lead on the common rows (ladder.json)
    if run.ladder is not None:
        if not _same(run.ladder["band"], run.band):
            _refuse_mismatch(run, "the ladder's band", run.ladder["band"], run.band)
        if not _same(run.ladder["common_rows"], run.common_rows):
            _refuse_mismatch(run, "the ladder's common-row count", run.ladder["common_rows"], run.common_rows)
        for lead in sorted(run.frames):
            v, _, _, _, _, _ = _verdict_of(run, bases[lead][BASIS_COMMON], lead, run.tol, run.floor)
            now = dict(M.verdict_record(v), adopted=run.info[lead]["adopted"], reference=run.info[lead]["reference"],
                       guard_passed=(None if lead == 0 else not run.info[lead]["declined"]),
                       common_rows=int(len(bases[lead][BASIS_COMMON])))
            recorded = run.ladder["verdicts"][str(lead)]
            if not _same(recorded, now):
                _refuse_mismatch(run, "the lead-%d verdict on the common rows (ladder.json)" % lead, recorded, now)
            rows.append(_verdict_row(run, lead, BASIS_COMMON, "ladder/ladder.json", now, own_band, hist, None))
    rows += _check_alarm_verdicts(run, bases, own_band, hist)
    return rows


def _check_alarm_verdicts(run: Run, bases: Mapping[int, Mapping[str, Any]], own_band: bool,
                          hist: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Owner ruling AE2: recompute every recorded with-alarm verdict (the nowcast's in alarm_verdict.json on all rows,
    each lead's in ladder/alarm_ladder.json on the common rows) and check it equals the record; one 'with alarm'
    verdict row per lead. A run with no alarm record gives none."""
    from treeroute.report import metrics as M

    if not run.alarm:
        return []
    rows = []
    v, contrast, _, _, _, (p_ref, p_with) = _verdict_of(run, bases[0][BASIS_ALL], 0, run.tol, run.floor,
                                                        column=WITH_ALARM)
    rec = M.verdict_record(v)
    recorded = run.alarm_verdict["with"]
    if not (_same(recorded["verdict"], rec) and _same(recorded["pooled_mae"], p_with)):
        _refuse_mismatch(run, "the nowcast's with-alarm verdict (alarm_verdict.json)",
                         [recorded["verdict"], recorded["pooled_mae"]], [rec, p_with])
    blocked = M.blocked_jackknife(contrast, {g: run.block_of_group[g] for g in contrast})
    bj = M._json_safe({"mean": blocked.mean, "se": blocked.se, "low": blocked.low, "high": blocked.high,
                       "n_blocks": blocked.n_groups, "flag": M.blocked_jackknife_flag(v.contrast, blocked)})
    if not _same(recorded.get("blocked_jackknife"), bj):
        _refuse_mismatch(run, "the nowcast's with-alarm blocked jackknife", recorded.get("blocked_jackknife"), bj)
    rows.append(_verdict_row(run, 0, BASIS_ALL, "alarm_verdict.json", rec, own_band, hist, bj, VERDICT_OF_ALARM))
    if run.alarm_ladder is not None:
        for lead in sorted(run.frames):
            v, _, _, _, _, (_, p_with) = _verdict_of(run, bases[lead][BASIS_COMMON], lead, run.tol, run.floor,
                                                     column=WITH_ALARM)
            now = M.verdict_record(v)
            got = run.alarm_ladder["by_lead"][str(lead)]["with"]
            want = {k: got[k] for k in now}
            if not (_same(want, now) and _same(got.get("pooled_mae"), p_with)):
                _refuse_mismatch(run, "the lead-%d with-alarm verdict (ladder/alarm_ladder.json)" % lead,
                                 [want, got.get("pooled_mae")], [now, p_with])
            rows.append(_verdict_row(run, lead, BASIS_COMMON, "ladder/alarm_ladder.json", now, own_band, hist, None,
                                     VERDICT_OF_ALARM))
    return rows


def _verdict_row(run: Run, lead: int, basis: str, source: str, rec: Mapping[str, Any], own_band: bool,
                 hist: Optional[Mapping[str, Any]], blocked: Optional[Mapping[str, Any]],
                 verdict_of: str = VERDICT_OF_ADOPTED) -> Dict[str, Any]:
    c = rec["contrast"]
    row = {"package": run.package, "run": run.folder.name, "lead": lead, "rows": basis, "verdict_of": verdict_of,
           "source": source, "recomputed_equals_recorded": True, "tag": rec["tag"],
           "adopted": run.info[lead]["adopted"] if verdict_of == VERDICT_OF_ADOPTED else WITH_ALARM,
           "reference": run.info[lead]["reference"], "declined": run.info[lead]["declined"],
           "contrast_mean": c["mean"], "contrast_se": c["se"], "contrast_low": c["low"], "contrast_high": c["high"],
           "n_groups": c["n_groups"], "pooled_contrast": rec["pooled_contrast"], "groups_better": rec["groups_better"],
           "sign_flip_groups": " ".join(rec["sign_flip_groups"]), "band": rec["band"],
           "band_source": run.verdict.get("band_source") if not own_band else "this run's own D75 contrasts",
           "band_check": BAND_RECOMPUTED if own_band else BAND_AS_RECORDED,
           "history_band": hist["band"] if hist else None, "history_band_source": hist["source"] if hist else None,
           "blocked_jackknife_se": blocked["se"] if blocked else None,
           "blocked_jackknife_flag": blocked["flag"] if blocked else None}
    return row


def build(run_folders: Sequence[Path], watermark: bool = False, notes: Sequence[str] = (),
          alarm_replay: Optional[Any] = None) -> Dict[str, Any]:
    """Every table, as DataFrames, plus the runs' input hashes (no file written). alarm_replay: the folder of the
    post-hoc replay (tools/alarm_replay.py) or None."""
    import pandas as pd
    from treeroute.report import metrics as M

    continuity = _yaml(CONTINUITY_FILE)
    history = _yaml(HISTORY_FILE)
    extra_rows = _yaml(ROWS_FILE)
    runs = [Run(f, watermark) for f in run_folders]
    packages = [r.package for r in runs]
    dup = sorted(set(p for p in packages if packages.count(p) > 1))
    if dup:
        raise TableRefusal("TABLE", "two runs of package(s) %s: one headline run per package" % dup)
    head, years, groups, cont, verdicts, longs, disc, inputs, subsets = [], [], [], [], [], [], [], [], []
    strata = []
    for run in sorted(runs, key=lambda r: r.package):
        if run.per_stratum is not None:
            t = run.per_stratum.copy()
            for k, v in reversed([("package", run.package), ("run", run.folder.name), ("lead", 0),
                                  ("adopted", run.info[0]["adopted"]), ("reference", run.info[0]["reference"]),
                                  ("source", STRATUM_SOURCE)]):
                t.insert(0, k, v)
            strata.append(t)
        run.history_band = history.get(run.package)
        if run.package not in continuity:
            raise TableRefusal("TABLE", "package %s has no entry in %s" % (run.package, CONTINUITY_FILE.name),
                               fix="add one (continuity_groups: [] when the package has no old hard split)")
        centry = continuity[run.package]
        clist = sorted(centry.get("continuity_groups") or [])
        bases = run.bases()
        verdicts += check_verdicts(run, bases)
        for lead in sorted(bases):
            for basis, frame in sorted(bases[lead].items()):
                t_group = M.score_table(frame, ("group",), run.tol, run.floor, run.kind)
                t_year = M.score_table(frame, ("year",), run.tol, run.floor, run.kind)
                t_pooled = M.score_table(frame, (), run.tol, run.floor, run.kind)
                ident = {"package": run.package, "run": run.folder.name, "lead": lead, "rows": basis}
                n_groups = int(frame["group"].nunique())
                for line, table in ((M.LINE_POOLED, t_pooled), (M.LINE_MACRO, t_group)):
                    row = dict(ident, line=line, adopted=run.info[lead]["adopted"],
                               reference=run.info[lead]["reference"], declined=run.info[lead]["declined"],
                               n_groups=n_groups, scored_units=int(frame["unit"].nunique()),
                               rows_saved=int(len(frame)))
                    row.update(_role_metrics(table, run, lead, line))
                    head.append(row)
                for name, table in (("by_group", t_group), ("by_year", t_year), ("pooled", t_pooled)):
                    t = table.copy()
                    for k, v in reversed(list(dict(ident, table=name).items())):
                        t.insert(0, k, v)
                    longs.append(t)
                for year in sorted(set(int(y) for y in frame["year"].tolist())):
                    years.append(dict(ident, year=year, **_role_metrics(t_year, run, lead, M.LINE_KEY, ("year", year))))
                for g in sorted(set(frame["group"].tolist())):
                    rm = _role_metrics(t_group, run, lead, M.LINE_KEY, ("group", g))
                    units = int(frame.loc[frame["group"] == g, "unit"].nunique())
                    groups.append(dict(ident, group=g, scored_units=units,
                                       overlap_block=run.block_members[run.block_of_group[g]],
                                       contrast=rm["mae_reference"] - rm["mae_adopted"], noise_note=NOISE_NOTE % units,
                                       **rm))
                cont.append(_continuity_row(run, lead, basis, frame, centry, clist, watermark, ident))
                subsets += _subset_rows(run, lead, frame, extra_rows.get(run.package) or [], ident)
        for kind, key in (("limit", "limits"), ("departure", "departures"),
                          ("not_headline_reason", "not_headline_reasons")):
            for text in run.record.get(key) or []:
                disc.append({"package": run.package, "run": run.folder.name, "kind": kind, "text": str(text)})
        listed = run.record.get("listed_in_reports") or []
        if listed:
            disc.append({"package": run.package, "run": run.folder.name, "kind": "listed_in_reports",
                         "text": "listed in every report (watch / keep_unreviewed): %s" % ", ".join(listed)})
        disc += _alarm_disclosures(run)
        donor_only = _donor_only_disclosure(run.record)
        if donor_only:
            disc.append({"package": run.package, "run": run.folder.name, "kind": "donor_only_groups",
                         "text": donor_only})
        # owner ruling S1: scored rows left out for missing router context (G-SPLIT tolerates the nowcast's unscored
        # units, pipeline.record.check_scored_units); disclosed per pass and lead
        s1 = run.record.get("score_context_left_out") or {}
        for what, d in sorted((s1.get("by_pass") or {}).items()):
            disc.append({"package": run.package, "run": run.folder.name, "kind": "score_context_left_out",
                         "text": "%s (lead %d): %d of %d scored rows of %d units left out of scoring for missing "
                                 "router context (owner ruling S1, never filled); units with no scored row: %s; rows "
                                 "saved in %s" % (what, int(d["lead"]), int(d["rows_left_out"]),
                                                  int(d["scored_rows_before"]), int(d["units_with_rows_left_out"]),
                                                  ", ".join(d.get("units_unscored") or []) or "none", d.get("rows_file"))})
        if run.ladder is not None:
            for key, text in sorted((run.ladder.get("readings") or {}).items()):
                disc.append({"package": run.package, "run": run.folder.name, "kind": "ladder_reading:%s" % key,
                             "text": str(text)})
        for name, path in sorted(run.files.items()):
            inputs.append({"package": run.package, "run": str(run.folder), "file": name,
                           "path": str(path), "sha256": C.sha256_file(path)})
    frames = {"headline": pd.DataFrame(head), "per_year": pd.DataFrame(years), "per_group": pd.DataFrame(groups),
              "continuity": pd.DataFrame(cont), "verdicts": pd.DataFrame(verdicts),
              "subsets": pd.DataFrame(subsets, columns=list(subsets[0]) if subsets else ["package", "label"]),
              "scores_long": pd.concat(longs, ignore_index=True),
              "disclosures": pd.DataFrame(disc, columns=["package", "run", "kind", "text"]),
              "per_stratum": (pd.concat(strata, ignore_index=True) if strata else
                              pd.DataFrame(columns=["package", "run", "lead", "adopted", "reference", "source"]))}
    alarm_rows = []
    for run in sorted(runs, key=lambda r: r.package):
        alarm_rows += _alarm_rows(run)
    frames["alarm"] = pd.DataFrame(alarm_rows, columns=list(alarm_rows[0]) if alarm_rows else
                                   ["package", "run", "lead", "status", "note"])
    if alarm_replay is not None:
        frames["alarm_replay"], replay_inputs = _replay_frame(Path(alarm_replay))
        inputs += replay_inputs
    if watermark:
        for name in frames:
            frames[name].insert(0, "watermark", WATERMARK)
    return {"frames": frames, "runs": runs, "inputs": inputs, "notes": list(notes),
            "continuity_sha256": C.sha256_file(CONTINUITY_FILE), "history_sha256": C.sha256_file(HISTORY_FILE),
            "rows_sha256": C.sha256_file(ROWS_FILE)}


def _alarm_disclosures(run: Run) -> List[Dict[str, Any]]:
    """Owner ruling AE: the alarm's disclosure lines of a run (the AE3 origin and each pass's status), or the v1
    note."""
    from treeroute.layer import alarm as LAL

    if not run.alarm:
        return [{"package": run.package, "run": run.folder.name, "kind": "alarm", "text": NO_ALARM_TEXT}]
    out = [{"package": run.package, "run": run.folder.name, "kind": "alarm_origin", "text": LAL.ALARM_ORIGIN}]
    for lead, doc in sorted(run.alarm.items()):
        out.append({"package": run.package, "run": run.folder.name, "kind": "alarm",
                    "text": "lead %d: adopted %s, twin %s (%s), status %s; %d of %d batch(es) took the twin (%d rows)"
                            % (lead, doc.get("adopted_arm"), doc.get("twin_arm"), doc.get("twin_kind"), doc["status"],
                               int(doc["batches_fired"]), len(doc.get("batches") or []), int(doc["rows_switched"]))})
    return out


def _alarm_rows(run: Run) -> List[Dict[str, Any]]:
    """One row per lead: the alarm's status and counts, MAE without and with it (pooled, every saved row), and the
    two verdicts (the nowcast's on all rows, each lead's on the common rows)."""
    if not run.alarm:
        return [{"package": run.package, "run": run.folder.name, "lead": lead, "status": None, "note": NO_ALARM_TEXT}
                for lead in sorted(run.frames)]
    out = []
    for lead, doc in sorted(run.alarm.items()):
        if lead == 0:
            without = run.verdict["verdict"]["tag"]
            with_ = run.alarm_verdict["with"]["verdict"]["tag"]
            mae_without, mae_with = run.verdict["pooled_mae_adopted"], run.alarm_verdict["with"]["pooled_mae"]
            basis = BASIS_ALL
        else:
            got = run.alarm_ladder["by_lead"][str(lead)]
            without, with_ = got["without"]["tag"], got["with"]["tag"]
            mae_without, mae_with = got["with"]["pooled_mae_adopted"], got["with"]["pooled_mae"]
            basis = BASIS_COMMON
        out.append({"package": run.package, "run": run.folder.name, "lead": lead, "status": doc["status"],
                    "adopted": doc.get("adopted_arm"), "twin": doc.get("twin_arm"), "twin_kind": doc.get("twin_kind"),
                    "batches": len(doc.get("batches") or []), "batches_tested": int(doc["batches_tested"]),
                    "batches_fired": int(doc["batches_fired"]), "rows_switched": int(doc["rows_switched"]),
                    "rows": basis, "mae_without": mae_without, "mae_with": mae_with, "verdict_without": without,
                    "verdict_with": with_, "post_hoc": False, "note": ""})
    return out


def _replay_frame(folder: Path) -> Tuple[Any, List[Dict[str, Any]]]:
    """The post-hoc replay's rows (tools/alarm_replay.py: <folder>/<package>/<run id>/alarm_replay.json), every one
    tagged POST-HOC (AE3); refuses a replay record not marked post-hoc."""
    import pandas as pd

    from treeroute.layer import alarm as LAL

    rows, inputs = [], []
    paths = sorted(folder.glob("*/*/alarm_replay.json"))
    if not paths:
        raise TableRefusal("AE3", "--alarm-replay %s holds no <package>/<run>/alarm_replay.json" % folder)
    for path in paths:
        doc = _read_json(path)
        if doc.get("post_hoc") is not True or doc.get("alarm_origin") != LAL.ALARM_ORIGIN:
            raise TableRefusal("AE3", "%s is not marked post-hoc with the AE3 sentence" % path)
        s = doc.get("scores") or {}
        rows.append({"tag": LAL.POST_HOC_TAG, "package": doc.get("package"), "run": doc.get("run_id"), "lead": 0,
                     "status": doc.get("status"), "adopted": doc.get("adopted_arm"), "twin": doc.get("twin_arm"),
                     "batches": len(doc.get("batches") or []), "batches_tested": doc.get("batches_tested"),
                     "batches_fired": doc.get("batches_fired"), "rows_switched": doc.get("rows_switched"),
                     "mae_without": s.get("pooled_mae_without"), "mae_with": s.get("pooled_mae_with"),
                     "leads": doc.get("leads")})
        inputs.append({"package": doc.get("package"), "run": str(path.parent), "file": "alarm_replay",
                       "path": str(path), "sha256": C.sha256_file(path)})
    return pd.DataFrame(rows), inputs


def _donor_only_disclosure(record: Mapping[str, Any]) -> str:
    """V6 b (PLAN_V6B.md E6): the disclosure text of a run record's donor-only groups ('' when the record has none:
    every grid record, and a table run whose groups all have a test row)."""
    d = record.get("donor_only_groups") or {}
    groups = [str(g) for g in (d.get("groups") or [])]
    if not groups:
        return ""
    return ("%d groups trained only (no test row): their trees serve every bank and their rows every pool and the "
            "decision surface; nothing is scored for them (%d train rows with a valid label): %s. A scored group's "
            "overlap_block (per_group.csv) can name one of them: that names a block partner, not a scored group"
            % (len(groups), int(d.get("train_rows") or 0), ", ".join(groups)))


def _subset_rows(run: Run, lead: int, frame: Any, entries: Sequence[Mapping[str, Any]],
                 ident: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Reporting-only subset rows: the run without its seen_during_design groups (Q49, from derived.json R18:groups)
    and the package's year subsets (report_rows.yaml). Pooled and macro, same functions, same saved rows."""
    from treeroute.report import metrics as M

    wanted = []
    seen = sorted((run.derived.get("R18:groups", {}).get("inputs") or {}).get("seen_during_design") or [])
    if seen:
        wanted.append(("without seen_during_design (Q49): %s" % ", ".join(seen), ~frame["group"].isin(seen)))
    for entry in entries:
        years = [int(y) for y in entry["years"]]
        wanted.append((str(entry["label"]), frame["year"].isin(years)))
    out = []
    for label, mask in wanted:
        sub = frame[mask.to_numpy()].reset_index(drop=True)
        if sub.empty or not sub["y"].notna().any():
            out.append(dict(ident, label=label, line=None, note="no saved row in this subset"))
            continue
        tp = M.score_table(sub, (), run.tol, run.floor, run.kind)
        tg = M.score_table(sub, ("group",), run.tol, run.floor, run.kind)
        for line, table in ((M.LINE_POOLED, tp), (M.LINE_MACRO, tg)):
            out.append(dict(ident, label=label, line=line, n_groups=int(sub["group"].nunique()),
                            scored_units=int(sub["unit"].nunique()), **_role_metrics(table, run, lead, line)))
    return out


def _continuity_row(run: Run, lead: int, basis: str, frame: Any, centry: Mapping[str, Any], clist: Sequence[str],
                    watermark: bool, ident: Mapping[str, Any]) -> Dict[str, Any]:
    from treeroute.report import metrics as M

    present = sorted(set(clist) & set(frame["group"].tolist()))
    missing = sorted(set(clist) - set(present))
    row = dict(ident, label=CONTINUITY_LABEL, groups_listed=len(clist), groups_scored=len(present),
               groups_missing=" ".join(missing), old_test_units=centry.get("old_test_units"),
               source=centry.get("source"))
    if missing and not watermark:
        raise TableRefusal("R34", "run %s lead %d: continuity groups not scored: %s (every group is tested under LORO)"
                           % (run.folder, lead, missing[:10]))
    if not present:
        row.update(scored_units=0, note="no continuity group in this run")
        return row
    sub = frame[frame["group"].isin(present)].reset_index(drop=True)
    row["scored_units"] = int(sub["unit"].nunique())
    tp = M.score_table(sub, (), run.tol, run.floor, run.kind)
    tg = M.score_table(sub, ("group",), run.tol, run.floor, run.kind)
    for line, table in ((M.LINE_POOLED, tp), (M.LINE_MACRO, tg)):
        rm = _role_metrics(table, run, lead, line)
        row.update({"%s_%s" % (k, line): v for k, v in rm.items() if k.split("_")[0] in ("mae", "anom", "corr2", "hit")})
    v, _, _, _, _, _ = _verdict_of(run, sub, lead, run.tol, run.floor)
    c = M.verdict_record(v)
    row.update(tag=c["tag"], contrast_mean=c["contrast"]["mean"], contrast_se=c["contrast"]["se"],
               contrast_low=c["contrast"]["low"], contrast_high=c["contrast"]["high"],
               n_groups=c["contrast"]["n_groups"], pooled_contrast=c["pooled_contrast"], band=c["band"],
               note="the package's band judges this row (R35); its jackknife is over these groups only")
    return row


# ===================================================================================== markdown
def _fmt(v: Any) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        if math.isnan(v):
            return "n/a"
        return "%.4g" % v
    return str(v).replace("|", "/")


def _md_table(rows: Sequence[Mapping[str, Any]], cols: Sequence[Tuple[str, str]]) -> List[str]:
    out = ["| " + " | ".join(h for _, h in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in rows:
        out.append("| " + " | ".join(_fmt(r.get(k)) for k, _ in cols) + " |")
    return out


def _stratum_md_rows(table: Any) -> List[Dict[str, Any]]:
    """One markdown row per package x stratum column x stratum (the key lines on all rows), with the adopted arm,
    its own-link trees-off, guess-normal and the last-5-years normal side by side."""
    import pandas as pd

    from treeroute.report import metrics as M

    key = table[(table["line"] == M.LINE_KEY) & (table["rows_basis"] == M.ROWS_BASIS_ALL)]
    out = []
    for (pkg, col, stratum), sel in key.groupby(["package", "stratum_column", "stratum"], sort=True):
        first = sel.iloc[0]

        def pick(column, metric):
            hit = sel[sel["column"] == column]
            return float(hit.iloc[0][metric]) if len(hit) == 1 else float("nan")
        ad, ref = first["adopted"], first["reference"]
        # exact edges; a string stratum of the table option (owner item O18) has none: its edge columns are absent,
        # or NaN when a numeric stratum shares the joined frame (grids always hold finite edges); some edges
        # missing and some present is refused (R34)
        no_edge = [c not in first.index or pd.isna(first[c]) for c in STRATUM_EDGE_COLUMNS]
        if any(no_edge) and not all(no_edge):
            raise TableRefusal("R34", "package %s stratum %s = %r: only some of the edges %s are recorded"
                               % (pkg, col, stratum, list(STRATUM_EDGE_COLUMNS)))
        out.append({"package": pkg, "stratum_column": col, "stratum": stratum,
                    "edges": ("per value" if all(no_edge)
                              else " / ".join(repr(float(first[c])) for c in STRATUM_EDGE_COLUMNS)),
                    "n": int(sel[sel["column"] == ad].iloc[0]["n"]) if (sel["column"] == ad).any() else 0,
                    "mae_adopted": pick(ad, "mae"), "mae_reference": pick(ref, "mae"),
                    "mae_guess": pick(BASELINE_OF_ROLE["guess_normal"], "mae"),
                    "mae_last5": pick(BASELINE_OF_ROLE["last5_normal"], "mae"),
                    "anom_r2_adopted": pick(ad, "anom_r2"), "corr2_adopted": pick(ad, "corr2"),
                    "hit_adopted": pick(ad, "hit"), "detection_adopted": pick(ad, "detection")})
    return out


def _alarm_markdown(f: Mapping[str, Any]) -> List[str]:
    """Owner ruling AE2/AE3: the section on the twin-disagreement alarm; its first line is ruling AE3's sentence."""
    from treeroute.layer import alarm as LAL

    lines = ["## With and without the twin-disagreement alarm", "", LAL.ALARM_ORIGIN, "",
             "Each run's alarm was decided and locked before its test labels opened (owner ruling AE1); the adopted "
             "column is never changed, and the 'with alarm' column takes the twin only in the batches the alarm "
             "switched. A run with no alarm record is an engine v1 run.", ""]
    lines += _md_table(f["alarm"].to_dict("records"),
                       [("package", "package"), ("lead", "lead"), ("status", "alarm status"), ("twin", "twin"),
                        ("batches_tested", "batches tested"), ("batches_fired", "batches switched"),
                        ("rows_switched", "rows switched"), ("rows", "rows"), ("mae_without", "MAE without"),
                        ("mae_with", "MAE with"), ("verdict_without", "verdict without"),
                        ("verdict_with", "verdict with"), ("note", "note")]) + [""]
    if "alarm_replay" in f:
        lines += ["### %s: the alarm replayed on saved engine v1 runs (nowcast only)" % LAL.POST_HOC_TAG, "",
                  "These rows are a post-hoc replay: the alarm was designed after these runs (AE3). They are not "
                  "pre-registered results.", ""]
        lines += _md_table(f["alarm_replay"].to_dict("records"),
                           [("tag", "tag"), ("package", "package"), ("run", "run"), ("status", "alarm status"),
                            ("twin", "twin"), ("batches_tested", "batches tested"),
                            ("batches_fired", "batches switched"), ("rows_switched", "rows switched"),
                            ("mae_without", "MAE without"), ("mae_with", "MAE with"), ("leads", "leads")]) + [""]
    return lines


def render_markdown(built: Mapping[str, Any], names: Mapping[str, str], watermark: bool) -> str:
    f = built["frames"]
    lines: List[str] = []
    title = "# Headline tables" + (" -- %s" % WATERMARK if watermark else "")
    lines += [title, ""]
    if watermark:
        lines += ["> **%s.** Rendered from smoke run folders for testing only (--smoke-watermark). Smoke deltas carry "
                  "no sign information; nothing here is a headline number." % WATERMARK, ""]
    as_recorded = sorted(set(r["package"] for r in f["verdicts"].to_dict("records")
                             if r.get("band_check") == BAND_AS_RECORDED))
    band_note = ("The band was recomputed from each run's own contrasts and is equal." if not as_recorded else
                 "The band of %s was TAKEN AS RECORDED (from another source) and NOT recomputed; every other recorded "
                 "number was recomputed and is equal." % ", ".join(as_recorded))
    lines += ["Built by treeroute_report.table from SAVED row-level predictions (test_preds.parquet) with the engine's "
              "treeroute.report.metrics functions. Every recorded verdict, band pair and blocked jackknife was "
              "recomputed from the saved rows and is equal. %s MAE, anomaly R2 against the per-unit normal, corr2 and "
              "the hit rate are printed together, each beside guess-normal and the last-5-years normal; never R2 "
              "alone. Uncertainty is over groups (jackknife at 1.96); no multiplicity correction." % band_note, "",
              "Files: " + ", ".join("`%s`" % names[k] for k in sorted(names)), ""]
    lines += ["## Runs", ""]
    run_rows = [{"package": r.package, "folder": str(r.folder), "kind": r.kind,
                 "run_fp": str(r.record.get("run_fingerprint"))[:16], "pkg_fp": str(r.record.get("package_fingerprint"))[:16],
                 "leads": ", ".join(str(L) for L in sorted(r.frames)), "groups": int(r.frames[0]["group"].nunique()),
                 "units": int(r.frames[0]["unit"].nunique())} for r in built["runs"]]
    lines += _md_table(run_rows, [("package", "package"), ("folder", "run folder"), ("kind", "kind"),
                                  ("run_fp", "run fingerprint"), ("pkg_fp", "package fingerprint"),
                                  ("leads", "leads"), ("groups", "groups"), ("units", "scored units")]) + [""]
    if built["notes"]:
        lines += ["Notes: " + "; ".join(built["notes"]), ""]
    lines += ["## Headline: pooled and macro (unweighted mean over groups)", "",
              "Lead 0 is the nowcast. Rows 'all' = every saved row of the lead; 'common' = rows scored at every lead "
              "(the ladder's basis, R34).", ""]
    metric_names = (("mae", "MAE"), ("anom_r2", "anomaly R2"), ("corr2", "corr2"), ("hit", "hit rate"),
                    ("hit_floor", "hit rate at the declared floor"), ("calibration_ratio", "calibration ratio"),
                    ("preclip_rate", "pre-clip rate"), ("detection", "strict top-10% detection (R33)"),
                    ("detection_events", "detection events"))
    rows = []
    for r in f["headline"].to_dict("records"):
        for m, label in metric_names:
            rows.append({"package": r["package"], "lead": r["lead"], "rows": r["rows"], "line": r["line"],
                         "metric": label, "adopted": r["%s_adopted" % m], "reference": r["%s_reference" % m],
                         "guess": r["%s_guess_normal" % m], "last5": r["%s_last5_normal" % m],
                         "zero": r["mae_predict_zero"] if m == "mae" else None,
                         "pers": r.get("mae_persistence") if m == "mae" else None,
                         "damped": r.get("mae_damped_persistence") if m == "mae" else None})
    lines += _md_table(rows, [("package", "package"), ("lead", "lead"), ("rows", "rows"), ("line", "line"),
                              ("metric", "metric"), ("adopted", "adopted"), ("reference", "own-link trees-off"),
                              ("guess", "guess-normal"), ("last5", "last-5-years normal"), ("zero", "predict-zero"),
                              ("pers", "persistence"), ("damped", "damped persistence")]) + [""]
    lines += ["## Verdicts (D74 rule; recomputed = recorded)", ""]
    lines += _md_table(f["verdicts"].to_dict("records"),
                       [("package", "package"), ("lead", "lead"), ("rows", "rows"), ("tag", "verdict"),
                        ("contrast_mean", "contrast"), ("contrast_low", "CI low"), ("contrast_high", "CI high"),
                        ("contrast_se", "SE"), ("n_groups", "groups"), ("band", "band"), ("band_check", "band check"),
                        ("history_band", "history band (beside, never used)"), ("pooled_contrast", "pooled contrast"),
                        ("groups_better", "groups better"), ("sign_flip_groups", "sign flips"),
                        ("blocked_jackknife_flag", "blocked-jackknife flag")]) + [""]
    lines += _alarm_markdown(f)
    lines += ["## Per test year", ""]
    lines += _md_table(f["per_year"].to_dict("records"),
                       [("package", "package"), ("lead", "lead"), ("rows", "rows"), ("year", "year"),
                        ("mae_adopted", "MAE adopted"), ("mae_reference", "MAE trees-off"),
                        ("mae_guess_normal", "MAE guess-normal"), ("mae_last5_normal", "MAE last-5"),
                        ("anom_r2_adopted", "anomaly R2"), ("corr2_adopted", "corr2"), ("hit_adopted", "hit rate"),
                        ("hit_guess_normal", "hit guess-normal"), ("detection_adopted", "detection"),
                        ("detection_guess_normal", "detection guess-normal"), ("n_adopted", "rows")]) + [""]
    lines += ["## Continuity row (the old hard-split test groups alone, same run): %s" % CONTINUITY_LABEL, ""]
    lines += _md_table(f["continuity"].to_dict("records"),
                       [("package", "package"), ("lead", "lead"), ("rows", "rows"), ("groups_listed", "groups listed"),
                        ("groups_scored", "groups scored"), ("scored_units", "scored units"),
                        ("old_test_units", "old test units"), ("mae_adopted_pooled", "MAE adopted"),
                        ("mae_reference_pooled", "MAE trees-off"), ("mae_guess_normal_pooled", "MAE guess-normal"),
                        ("mae_last5_normal_pooled", "MAE last-5"), ("anom_r2_adopted_pooled", "anomaly R2"),
                        ("tag", "verdict"), ("contrast_mean", "contrast"), ("contrast_low", "CI low"),
                        ("contrast_high", "CI high"), ("band", "band"), ("note", "note")]) + [""]
    if len(f["subsets"]) and "line" in f["subsets"].columns:
        lines += ["## Subset rows (reporting only)", ""]
        lines += _md_table(f["subsets"].to_dict("records"),
                           [("package", "package"), ("lead", "lead"), ("rows", "rows"), ("label", "row"),
                            ("line", "line"), ("n_groups", "groups"), ("mae_adopted", "MAE adopted"),
                            ("mae_reference", "MAE trees-off"), ("mae_guess_normal", "MAE guess-normal"),
                            ("mae_last5_normal", "MAE last-5"), ("anom_r2_adopted", "anomaly R2"),
                            ("corr2_adopted", "corr2"), ("hit_adopted", "hit rate"), ("note", "note")]) + [""]
    if len(f["per_stratum"]):
        lines += ["## Per report stratum (R34; lead 0, rows 'all')", "",
                  "The stratum tables are %s. Strata are the donor rows' quartiles, right-closed (D73)."
                  % STRATUM_SOURCE, ""]
        lines += _md_table(_stratum_md_rows(f["per_stratum"]),
                           [("package", "package"), ("stratum_column", "stratum column"), ("stratum", "stratum"),
                            ("edges", "edges q25 / q50 / q75"), ("n", "rows"), ("mae_adopted", "MAE adopted"),
                            ("mae_reference", "MAE trees-off"), ("mae_guess", "MAE guess-normal"),
                            ("mae_last5", "MAE last-5"), ("anom_r2_adopted", "anomaly R2"),
                            ("corr2_adopted", "corr2"), ("hit_adopted", "hit rate"),
                            ("detection_adopted", "detection")]) + [""]
    lines += ["## Per group (rows 'all')", "",
              "Each group's score is noisy; the pooled headline and the all-group jackknife decide, never one group.", ""]
    pg = [r for r in f["per_group"].to_dict("records") if r["rows"] == BASIS_ALL]
    lines += _md_table(pg, [("package", "package"), ("lead", "lead"), ("group", "group"),
                            ("scored_units", "scored units"), ("overlap_block", "overlap block"),
                            ("mae_adopted", "MAE adopted"), ("mae_reference", "MAE trees-off"),
                            ("mae_guess_normal", "MAE guess-normal"), ("mae_last5_normal", "MAE last-5"),
                            ("contrast", "contrast"), ("anom_r2_adopted", "anomaly R2"),
                            ("hit_adopted", "hit rate")]) + [""]
    lines += ["## Disclosures (from each run's records)", ""]
    for pkg in sorted(set(f["disclosures"]["package"].tolist())):
        lines += ["### %s" % pkg, ""]
        for r in f["disclosures"][f["disclosures"]["package"] == pkg].to_dict("records"):
            lines.append("- **%s:** %s" % (r["kind"], r["text"]))
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


# ====================================================================================== writing
def write(built: Mapping[str, Any], out_dir: Path, watermark: bool) -> Dict[str, Any]:
    """Write every output once under content-hashed names (an identical file is kept, not rewritten)."""
    from treeroute.pipeline import record as REC
    from treeroute.runs.atomic import dumps

    prefix = SMOKE_PREFIX if watermark else ""
    out_dir.mkdir(parents=True, exist_ok=True)
    texts, names = {}, {}
    for key in ("headline", "per_year", "per_group", "continuity", "subsets", "verdicts", "scores_long",
                "disclosures", "per_stratum", "alarm") + (("alarm_replay",) if "alarm_replay" in built["frames"]
                                                          else ()):
        text = REC.csv_text(built["frames"][key])
        names[key] = "%s%s_%s.csv" % (prefix, key, C.sha256_text(text)[:12])
        texts[key] = text
    md = render_markdown(built, names, watermark)
    names["markdown"] = "%sheadline_%s.md" % (prefix, C.sha256_text(md)[:12])
    texts["markdown"] = md
    manifest = {"tool": "treeroute_report.table", "watermark": WATERMARK if watermark else None,
                "inputs": built["inputs"], "notes": built["notes"],
                "continuity_groups_sha256": built["continuity_sha256"], "history_bands_sha256": built["history_sha256"],
                "report_rows_sha256": built["rows_sha256"],
                "outputs": {k: {"file": names[k], "sha256": C.sha256_text(texts[k])} for k in sorted(names)}}
    mtext = dumps(manifest) + "\n"
    names["manifest"] = "%smanifest_%s.json" % (prefix, C.sha256_text(mtext)[:12])
    texts["manifest"] = mtext
    paths = {}
    for key, name in names.items():
        path = out_dir / name
        REC.write_text_once_or_same(path, texts[key])
        paths[key] = path
    return paths


def run_tables(paths: Sequence[Any], out: Optional[Any] = None, registry_dir: Optional[Any] = None,
               watermark: bool = False, echo: Callable[[str], None] = print,
               alarm_replay: Optional[Any] = None) -> Dict[str, Any]:
    from treeroute.runs.registry import Registry

    folders, notes, root = find_runs(paths, watermark)
    if out is None:
        base = root if root is not None else folders[0].parents[2]
        out = Path(base) / DEFAULT_OUT
    registry_dir = registry_dir if registry_dir is not None else C.machine_defaults()["registry_dir"]
    out_dir = Registry(registry_dir).assert_writable(Path(out))
    built = build(folders, watermark=watermark, notes=notes, alarm_replay=alarm_replay)
    written = write(built, out_dir, watermark)
    for note in notes:
        echo(note)
    for key in sorted(written):
        echo("%s: %s" % (key, written[key]))
    return {"paths": written, "built": built}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m treeroute_report.table",
                                     description="Headline tables from saved row-level predictions of finished "
                                                 "headline runs.")
    parser.add_argument("paths", nargs="+", help="a run root, or run folders")
    parser.add_argument("--out", default=None, help="output folder (default: <run root>/%s)" % DEFAULT_OUT)
    parser.add_argument("--registry-dir", default=None, help="registry folder (default: the machine file's)")
    parser.add_argument("--smoke-watermark", action="store_true",
                        help="TEST ONLY: render smoke run folders, stamped '%s'" % WATERMARK)
    parser.add_argument("--alarm-replay", default=None,
                        help="the post-hoc alarm replay folder (tools/alarm_replay.py); its rows are tagged POST-HOC (AE3)")
    ns = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    try:
        run_tables(ns.paths, ns.out, ns.registry_dir, ns.smoke_watermark, alarm_replay=ns.alarm_replay)
        return 0
    except TreerouteError as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return EXIT_REFUSED


if __name__ == "__main__":
    sys.exit(main())
