"""The twin-disagreement alarm (owner ruling AE with the AE1 amendment): the pure rule, no I/O.

After a pass's adoption is locked and BEFORE any of its test labels opens, the alarm compares the adopted arm A with
its twin T on the pass's test rows, batch by batch, against the disagreement the two show on the pass's reference
surface at the adopted point:
  - the twin (twin_of): the WEIGHTING twin (same link and tool, the other weighting) when that weighting is routed in
    the pass's router kind; otherwise the TOOL twin (same link and weighting, plain <-> corrector);
  - the twin is SIMPLER (twin_is_simpler) when it is unweighted and A is GLS-weighted, or it is plain and A is a
    corrector; otherwise the alarm is inert for the pass (nothing can switch);
  - the twin is ELIGIBLE when it passed the layer's own N2 test on the surface: at the nowcast, it is in the locked
    Adoption.eligible (layer/decide.py select_adoption, the donor-row median for the neighbour kind under ruling V1);
    at a lead, its MAE on the lead's guard surface is strictly below the baseline the lead's own guard used
    (twin_eligible_lead, the same strict comparison as n2_eligible);
  - the reference gap R (reference_gap): mean |A - T| over the reference surface's rows at the adopted point, both
    clipped; R not finite or zero means "not tested" (a ratio over zero means nothing);
  - batches (batch_keys, the AE1 amendment): the rows sharing the issue calendar month: for a grid whose step covers a
    calendar month or more (monthly, annual) the issue step itself; for anything finer (composite steps, event rows
    dated by day ordinals) the calendar month of the issue's first day;
  - per batch with at least A8.alarm_min_batch_rows rows (decide_alarm): g = mean |A - T| over its rows; the batch
    takes the twin when g / R > A8.alarm_ratio_threshold (strict) and the pass is active. Every other row keeps A.
The adopted column itself is never changed: the alarm writes a separate "with alarm" column, so a run reports results
with and without it (ruling AE2).

HONESTY NOTE (ruling AE3, binding): the alarm was designed after the engine v1 headline runs, from the diagnosis of
Parts 601-604; its effect on those runs is a post-hoc replay. ALARM_ORIGIN carries that sentence into every record.
"""
# Provenance for the module: OWNER_RULINGS_2026-10-06.md section AE (AE1-AE4) and the AE1 amendment, recorded
# 2026-10-21; D:/treeroute/engine_v2/SPEC_ALARM.txt sections 2 and 3 (written before any v2 code).

import datetime as _dt
import math
from dataclasses import dataclass
from numbers import Integral, Real
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np

from treeroute import engine_constants as K

from .arms import SELECTABLE_TOOLS, ArmSpec, LayerRefusal, Tool, Weighting, arm_name, check_arm

ALARM_RULE = ("owner ruling AE1 with the AE1 amendment (the owner rulings file, section AE): per issue batch, the mean "
              "absolute gap between the adopted arm and its twin on the test rows, over the same gap on the pass's "
              "reference surface at the adopted point; above the threshold, and only when the twin is the simpler arm "
              "and was eligible on the surface, the batch's rows take the twin; recorded and locked before the pass's "
              "test labels open")
ALARM_ORIGIN = ("owner ruling AE3: the twin-disagreement alarm was designed AFTER the engine v1 headline runs, from the "
                "diagnosis of Parts 601-604. Its effect on any engine v1 run is a POST-HOC replay, labelled post-hoc. "
                "Only runs on new data under engine v2 count as pre-registered for the alarm.")
POST_HOC_TAG = "POST-HOC (AE3)"

STATUS_ACTIVE = "active"
STATUS_NOT_SIMPLER = "inert_twin_not_simpler"
STATUS_NOT_ELIGIBLE = "inert_twin_not_eligible"
STATUS_DECLINED = "not_applicable_declined"
STATUS_ZERO_GAP = "not_tested_zero_reference_gap"
STATUS_HARNESS = "not_applicable_harness"      # a legacy harness replay that scores no arm (not a declined pass)
STATUSES = (STATUS_ACTIVE, STATUS_NOT_SIMPLER, STATUS_NOT_ELIGIBLE, STATUS_DECLINED, STATUS_ZERO_GAP, STATUS_HARNESS)

TWIN_WEIGHTING = "weighting"
TWIN_TOOL = "tool"
STEP_KEY_PREFIX = "step:"
WITH_ALARM_COLUMN = "arm__with_alarm"          # never a real arm name (arms are <link>_<tool>_<weighting>)
PRE_WITH_ALARM_COLUMN = "pre__with_alarm"


class AlarmRefusal(LayerRefusal):
    """The alarm rule refused (fail loudly)."""


@dataclass(frozen=True)
class BatchResult:
    """One issue batch of a pass: its key, its rows, its gap (None when the twin was not routed), its ratio (None when
    not computed), whether it was tested (enough rows and a usable reference gap) and whether it took the twin."""
    batch: str
    rows: int
    gap: Optional[float]
    ratio: Optional[float]
    tested: bool
    fired: bool


@dataclass(frozen=True)
class AlarmRecord:
    """decide_alarm's outcome for one pass (arrays are read-only, one value per saved test row in pass order)."""
    status: str
    reference_gap: Optional[float]
    threshold: float
    min_batch_rows: int
    batches: Tuple[BatchResult, ...]
    batch: np.ndarray            # the batch key of each row
    fired: np.ndarray            # bool per row: the row's batch took the twin
    with_alarm: np.ndarray       # clipped: the twin where fired, the adopted arm elsewhere
    pre_with_alarm: np.ndarray   # before the clip, the same choice

    @property
    def batches_tested(self) -> int:
        return int(sum(1 for b in self.batches if b.tested))

    @property
    def batches_fired(self) -> int:
        return int(sum(1 for b in self.batches if b.fired))

    @property
    def rows_switched(self) -> int:
        return int(np.count_nonzero(self.fired))


def constants() -> Dict[str, Any]:
    """The A8 constants as read NOW (module attributes, so a test may set them), by id."""
    return {"A8.alarm_ratio_threshold": float(K.ALARM_RATIO_THRESHOLD),
            "A8.alarm_min_batch_rows": int(K.ALARM_MIN_BATCH_ROWS)}


# ---------------------------------------------------------------------------------------------------
def twin_of(arm: ArmSpec, weightings: Sequence[Weighting]) -> Tuple[ArmSpec, str]:
    """The twin of a selectable tree arm and its kind ('weighting' or 'tool'). weightings: the weightings the pass's
    router kind routes (GLS is absent for a kind with no weighted solve). The weighting twin is preferred; the tool
    twin is used only when the other weighting is not routed. Refuses a trees-off or placebo arm, a weighting set
    that does not hold the arm's own weighting."""
    check_arm(arm)
    if not arm.selectable or arm.tool not in SELECTABLE_TOOLS:
        raise AlarmRefusal("AE1", "only a selectable tree arm has a twin, got %s" % arm_name(arm))
    ws = tuple(weightings)
    if not ws or any(not isinstance(w, Weighting) for w in ws):
        raise AlarmRefusal("AE1", "the routed weightings must be Weighting members, got %r" % (ws,))
    if arm.weighting not in ws:
        raise AlarmRefusal("AE1", "%s's weighting is not among the routed weightings %s"
                           % (arm_name(arm), [w.value for w in ws]))
    other_w = Weighting.GLS if arm.weighting is Weighting.UNWEIGHTED else Weighting.UNWEIGHTED
    if other_w in ws:
        return ArmSpec(link=arm.link, tool=arm.tool, weighting=other_w, selectable=True), TWIN_WEIGHTING
    other_t = Tool.PLAIN if arm.tool is Tool.CORRECTOR else Tool.CORRECTOR
    return ArmSpec(link=arm.link, tool=other_t, weighting=arm.weighting, selectable=True), TWIN_TOOL


def twin_is_simpler(arm: ArmSpec, twin: ArmSpec) -> bool:
    """True when the twin is the simpler arm: unweighted against a GLS-weighted arm of the same link and tool, or
    plain against a corrector of the same link and weighting."""
    check_arm(arm)
    check_arm(twin)
    if arm.link != twin.link:
        return False
    if arm.tool is twin.tool:
        return arm.weighting is Weighting.GLS and twin.weighting is Weighting.UNWEIGHTED
    if arm.weighting is twin.weighting:
        return arm.tool is Tool.CORRECTOR and twin.tool is Tool.PLAIN
    return False


def twin_eligible_nowcast(twin: ArmSpec, eligible: Sequence[ArmSpec]) -> bool:
    """Nowcast: the twin passed the layer's N2 test on the decision surface (it is in the locked Adoption.eligible)."""
    check_arm(twin)
    return any(twin == a for a in eligible)


def _finite(x: Any, what: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (Real, np.floating, np.integer)) or not math.isfinite(float(x)):
        raise AlarmRefusal("AE1", "%s must be a finite number, got %r" % (what, x))
    return float(x)


def twin_eligible_lead(twin_guard_mae: float, baseline_mae: float) -> bool:
    """A lead: the twin's MAE on the lead's guard surface is STRICTLY below the baseline the lead's own guard used
    (its link's trees-off MAE, or the donor-row median MAE under ruling V1): n2_eligible's comparison."""
    return _finite(twin_guard_mae, "the twin's guard MAE") < _finite(baseline_mae, "the guard baseline's MAE")


def _pair(a: Any, b: Any, what: str) -> Tuple[np.ndarray, np.ndarray]:
    av = np.asarray(a, dtype=np.float64)
    bv = np.asarray(b, dtype=np.float64)
    if av.ndim != 1 or av.shape != bv.shape:
        raise AlarmRefusal("AE1", "%s: the adopted and twin columns must be 1-D and of one length, got %s and %s"
                           % (what, av.shape, bv.shape))
    return av, bv


def reference_gap(adopted: Any, twin: Any) -> float:
    """R: mean |adopted - twin| over the reference surface's rows (both clipped, at the adopted point). Returns NaN
    for no row; a non-finite value stays non-finite (the caller records 'not tested')."""
    a, t = _pair(adopted, twin, "the reference surface")
    if a.size == 0:
        return float("nan")
    return float(np.mean(np.abs(a - t)))


# ---------------------------------------------------------------------------------------------------
def _month_key(ordinals: np.ndarray) -> np.ndarray:
    distinct, inverse = np.unique(np.asarray(ordinals, dtype=np.int64), return_inverse=True)
    names = []
    for d in distinct.tolist():
        try:
            day = _dt.date.fromordinal(int(d))
        except (ValueError, OverflowError) as exc:
            raise AlarmRefusal("AE1", "issue day ordinal %r is not a calendar day (%s)" % (d, exc)) from exc
        names.append("%04d-%02d" % (day.year, day.month))
    return np.asarray(names, dtype=object)[np.asarray(inverse).reshape(-1)]


def batch_keys(issue: Any, cadence: Any = None) -> np.ndarray:
    """The batch key of each row from its issue (AE1 amendment). cadence None: the issue is a day ordinal (table and
    event rows): the key is its calendar month 'YYYY-MM'. A grid cadence whose step covers one calendar month or
    more (regular, one month or one year): the key is the issue step itself, 'step:<n>'. A finer grid step
    (composite-of-year): the calendar month of the issue step's first day (io/steps.py step_bounds). Refuses any
    other cadence (a step with no calendar bounds)."""
    s = np.asarray(issue)
    if s.ndim != 1 or s.dtype.kind not in "iu":
        raise AlarmRefusal("AE1", "issue must be one whole number per row, got %s %s" % (s.dtype, s.shape))
    s = s.astype(np.int64)
    if cadence is None:
        return _month_key(s)
    from treeroute.io.steps import COMPOSITE_OF_YEAR, REGULAR, cadence_view, step_bounds

    view = cadence_view(cadence)
    if view.kind == REGULAR and view.unit in ("month", "year") and view.length == 1:
        return np.asarray(["%s%d" % (STEP_KEY_PREFIX, int(v)) for v in s.tolist()], dtype=object)
    if view.kind == COMPOSITE_OF_YEAR:
        first, _ = step_bounds(s, cadence)
        return _month_key(np.asarray(first, dtype=np.int64))
    raise AlarmRefusal("AE1", "a %s cadence (%r %r) has no issue batch: the alarm batches rows by the issue's "
                       "calendar month" % (view.kind, view.length, view.unit))


def _batch_order(key: str) -> Tuple[int, Any]:
    if key.startswith(STEP_KEY_PREFIX):
        return 0, int(key[len(STEP_KEY_PREFIX):])
    return 1, key


def pass_status(declined: bool, simpler: Optional[bool], eligible: Optional[bool],
                gap: Optional[float]) -> str:
    """The pass's status, in this order: a declined pass is not applicable; a twin that is not simpler leaves the
    alarm inert; a twin that is not eligible too; a reference gap that is not finite or is zero is not tested;
    otherwise active. Refuses a negative reference gap (a mean of absolute values cannot be negative)."""
    if gap is not None and math.isfinite(float(gap)) and float(gap) < 0.0:
        raise AlarmRefusal("AE1", "the reference gap is negative (%r): a mean absolute gap cannot be" % (gap,))
    if declined:
        return STATUS_DECLINED
    if not simpler:
        return STATUS_NOT_SIMPLER
    if not eligible:
        return STATUS_NOT_ELIGIBLE
    if gap is None or not math.isfinite(float(gap)) or float(gap) == 0.0:
        return STATUS_ZERO_GAP
    return STATUS_ACTIVE


def decide_alarm(status: str, adopted: Any, pre_adopted: Any, twin: Optional[Any], pre_twin: Optional[Any],
                 batch: Any, gap: Optional[float], *, threshold: Optional[float] = None,
                 min_batch_rows: Optional[int] = None) -> AlarmRecord:
    """AE1 on one pass's saved test rows (pass order). status: pass_status's; adopted / pre_adopted: the adopted
    column clipped and before the clip; twin / pre_twin: the twin's (None when it was not routed: an inert or
    not-applicable lead); batch: batch_keys of the rows; gap: R. threshold and min_batch_rows default to the A8
    constants as read now. A batch is tested when it has at least min_batch_rows rows and R is finite and above 0;
    it takes the twin when tested, its ratio is STRICTLY above the threshold and the status is active (a batch of an
    inert pass records its gap and ratio but is never tested). Batches are
    recorded in a fixed order (steps by number, months by text). Refuses an unknown status, an active pass without
    the twin, arrays of different lengths, a non-finite adopted or twin value on a row."""
    if status not in STATUSES:
        raise AlarmRefusal("AE1", "unknown alarm status %r" % (status,))
    thr = float(K.ALARM_RATIO_THRESHOLD if threshold is None else threshold)
    min_rows = K.ALARM_MIN_BATCH_ROWS if min_batch_rows is None else min_batch_rows
    if isinstance(min_rows, bool) or not isinstance(min_rows, Integral) or int(min_rows) < 1:
        raise AlarmRefusal("AE1", "the minimum batch size must be a whole number of at least 1, got %r" % (min_rows,))
    min_rows = int(min_rows)
    if gap is not None and math.isfinite(float(gap)) and float(gap) < 0.0:
        raise AlarmRefusal("AE1", "the reference gap is negative (%r): a mean absolute gap cannot be" % (gap,))
    a = np.asarray(adopted, dtype=np.float64)
    pa = np.asarray(pre_adopted, dtype=np.float64)
    keys = np.asarray(batch, dtype=object)
    if a.ndim != 1 or pa.shape != a.shape or keys.shape != a.shape:
        raise AlarmRefusal("AE1", "the adopted column (%s), its pre-clip values (%s) and the batch keys (%s) must be "
                           "one per row" % (a.shape, pa.shape, keys.shape))
    has_twin = twin is not None
    if has_twin:
        _, t = _pair(a, twin, "the test rows")
        pt = np.asarray(pre_twin, dtype=np.float64)
        if pt.shape != a.shape:
            raise AlarmRefusal("AE1", "the twin's pre-clip values (%s) are not one per row (%s)" % (pt.shape, a.shape))
        if a.size and not (np.isfinite(a).all() and np.isfinite(t).all()):
            raise AlarmRefusal("AE1", "the adopted or twin prediction is missing on a test row; an arm predicts every "
                               "saved row (R28)")
    elif status == STATUS_ACTIVE:
        raise AlarmRefusal("AE1", "an active pass needs its twin's predictions on the test rows")
    usable_gap = gap is not None and math.isfinite(float(gap)) and float(gap) > 0.0
    fired = np.zeros(a.size, dtype=bool)
    out = []
    names = sorted(set(str(k) for k in keys.tolist()), key=_batch_order)
    keys_s = keys.astype(str)
    for name in names:
        rows = np.flatnonzero(keys_s == name)
        g = float(np.mean(np.abs(a[rows] - t[rows]))) if has_twin else None
        ratio = (g / float(gap)) if (g is not None and usable_gap) else None
        tested = bool(rows.size >= min_rows and usable_gap and has_twin and status == STATUS_ACTIVE)
        took = bool(tested and status == STATUS_ACTIVE and ratio is not None and ratio > thr)
        if took:
            fired[rows] = True
        out.append(BatchResult(batch=name, rows=int(rows.size), gap=g, ratio=ratio, tested=tested, fired=took))
    with_alarm = a.copy()
    pre_with = pa.copy()
    if fired.any():
        with_alarm[fired] = t[fired]
        pre_with[fired] = pt[fired]
    for arr in (keys, fired, with_alarm, pre_with):
        arr.setflags(write=False)
    return AlarmRecord(status=status, reference_gap=None if gap is None else float(gap), threshold=thr,
                       min_batch_rows=min_rows, batches=tuple(out), batch=keys, fired=fired, with_alarm=with_alarm,
                       pre_with_alarm=pre_with)


def with_alarm_column(adopted: Any, twin: Optional[Any], fired: Any) -> np.ndarray:
    """The 'with alarm' column from its parts: the twin where fired, the adopted arm elsewhere (a check helper for
    the report and the replay)."""
    a = np.asarray(adopted, dtype=np.float64)
    f = np.asarray(fired, dtype=bool)
    if f.shape != a.shape:
        raise AlarmRefusal("AE1", "fired flags (%s) are not one per row (%s)" % (f.shape, a.shape))
    out = a.copy()
    if f.any():
        if twin is None:
            raise AlarmRefusal("AE1", "rows took the twin but no twin column is given")
        t = np.asarray(twin, dtype=np.float64)
        out[f] = t[f]
    return out


def _num(x: Optional[float]) -> Optional[float]:
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def alarm_document(record: AlarmRecord, context: Mapping[str, Any]) -> Dict[str, Any]:
    """The alarm's record for one pass (alarm_lead_<L>.json): the rule, the AE3 origin sentence, the constants, the
    caller's context (lead, pass, adoption file and hash, adopted and twin arms, eligibility, reference, files and
    hashes) and the outcome (status, every batch, counts). JSON values only (NaN and inf as null)."""
    doc: Dict[str, Any] = {"rule": ALARM_RULE, "alarm_origin": ALARM_ORIGIN,
                           "constants": {"A8.alarm_ratio_threshold": record.threshold,
                                         "A8.alarm_min_batch_rows": record.min_batch_rows}}
    doc.update(dict(context))
    doc.update({"status": record.status,
                "batches": [{"batch": b.batch, "rows": b.rows, "gap": _num(b.gap), "ratio": _num(b.ratio),
                             "tested": b.tested, "fired": b.fired} for b in record.batches],
                "batches_tested": record.batches_tested, "batches_fired": record.batches_fired,
                "rows_switched": record.rows_switched})
    return doc


def not_applicable_document(lead: int, adoption_file: str, adoption_sha256: str, reason: str) -> Dict[str, Any]:
    """A pass with no alarm to decide (a harness replay that scores no arm): status not_applicable_harness (it did
    not decline; it scores no arm), no batch, with the reason; locked like any alarm record so the pass's test labels
    can open."""
    if isinstance(lead, bool) or not isinstance(lead, Integral) or int(lead) < 0:
        raise AlarmRefusal("AE1", "lead must be a whole number of at least 0, got %r" % (lead,))
    if not isinstance(reason, str) or not reason.strip():
        raise AlarmRefusal("AE1", "a not-applicable alarm record names its reason")
    return {"rule": ALARM_RULE, "alarm_origin": ALARM_ORIGIN, "constants": constants(), "lead": int(lead),
            "pass": "nowcast" if int(lead) == 0 else "lead %d" % int(lead), "adoption_file": str(adoption_file),
            "adoption_sha256": str(adoption_sha256), "status": STATUS_HARNESS, "reason": reason, "batches": [],
            "batches_tested": 0, "batches_fired": 0, "rows_switched": 0}


__all__ = ["ALARM_RULE", "ALARM_ORIGIN", "POST_HOC_TAG", "STATUSES", "STATUS_ACTIVE", "STATUS_NOT_SIMPLER",
           "STATUS_NOT_ELIGIBLE", "STATUS_DECLINED", "STATUS_ZERO_GAP", "STATUS_HARNESS", "TWIN_WEIGHTING", "TWIN_TOOL",
           "WITH_ALARM_COLUMN", "PRE_WITH_ALARM_COLUMN", "AlarmRefusal", "BatchResult", "AlarmRecord", "constants",
           "twin_of", "twin_is_simpler", "twin_eligible_nowcast", "twin_eligible_lead", "reference_gap", "batch_keys",
           "pass_status", "decide_alarm", "with_alarm_column", "alarm_document", "not_applicable_document"]
