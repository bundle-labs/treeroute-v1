"""The forecast ladder (plan 4.1 step 11; R10, R11, R17, R29, R31, R34, R35; D86; Part 559 / F45; F57; owner
rulings G1, H2-H5 and I1), run after the nowcast's report on the same RunState.

Leads (R10, owner ruling I1): 6 and 12 months in the data's own step, plus lead 0, which always runs as the
contract (monthly data: leads 6 and 12; annual data: both round to 1 year and merge into one lead).
Per derived lead L (R11's cut pair per lead):
  1  the lead's pool: every kept feature column moved to the issue step t - L with the approved
     io.apply.features_at_issue_step (the WHOLE feature row, plan 1.5: tree features and router context,
     owner ruling H3; each column keeps its R8 lag relative to that step, and R8's lag already covers the
     issue-step reference, D24), applied on the run's base rows of the bank units (the pre-Y0 lag year
     included), plus the own-history block rebuilt at lead L (R17: the newest readable label is t - L moved
     back by the start offset; its fallbacks read the unit histories and the donor-row mean at the lead's
     fit cut, F1). A row whose issue row is absent gets NaN (never a shifted neighbour); the count is
     recorded (lead.json fits.issue_row_absent). A router FIT row whose moved context is missing or
     non-finite leaves the lead's router fit, as a row with a missing label does (owner ruling G1,
     pipeline.stages.drop_missing_context; nothing is filled), counted per unit for the guard and the test
     pass in lead.json context_missing, each row saved in the run folder's context_missing/ (the record's
     rows_file).
  2  lagtrain (R29): the bank (trees, correctors, placebo correctors) refit on the donor rows at the
     lead's FIT cut through FitContext(lead L); c at the lead's cut (R23:lead=L); R36's tolerances at the
     lead's cut; the GLS weight model refit at the lead's cut ONLY when the pinned arm is weighted
     (R25). The pin (R29, layer.decide.pin_of): the nowcast's adopted arm and penalty, or its best tree
     arm and that arm's penalty when it declined.
  3  the guard objects (owner ruling H2: L6 b at every lead, H2_RULE): a SECOND bank, its correctors and
     placebo correctors, refit on the donor rows at the lead's GUARD cut (FitContext(lead L, GUARD) over the
     lead pool whose history block is rebuilt at the guard cut: F1's fallbacks read the unit histories and
     the donor-row mean at the guard cut, passes.HistoryOverride), exactly as the nowcast's inner decision
     stands at the inner cut. So no guard row sits inside a bank trained on its labels: asserted (H2) and
     recorded (lead.json guard.guard_rows_in_bank_label_window = 0). As at the nowcast's inner decision,
     the guard reads the lead's fit-cut c (ruling D63 a), R36 tolerances and (a weighted pin) GLS weight
     model's tree answers (R25 / D57; as the nowcast's, READINGS guard_gls_answers): GUARD_FIT_CUT_RULE.
     The guard objects are released after the guard. With A7.inner_cut_bank_refit off (L6 a) the guard reads the
     lead's fit-cut objects instead, and nothing is asserted. The nowcast's own banks are released before
     the first lead (RunState.release_bank: the inner-cut bank when the ladder starts, the fit-cut bank
     after the lead-0 contract), so a guard runs with two banks in memory (lead.json guard.banks_in_memory).
  4  the N2 guard (R29, Q7 a) on the lead's inner guard surface: router fit rows at the lead's GUARD cut,
     score rows the scored units' valid rows after the inner-fit end up to the lead's fit cut whose own
     window ended by then (the vault's decision_surface at the lead's fit cut), every one issued at or
     after the guard cut (G-FITCUT, check_inner_score_rows). The pinned arm at the pinned penalty against
     its link's trees-off: layer.decide.forecast_adoption; a pinned arm that fails the guard adopts the
     decline target (the identity link's trees-off) at that lead (D86). The lead searches its OWN R12
     fallback level on this guard surface (owner ruling H5, H5_RULE: pipeline.router search_levels; the
     lambda centre below C15's 10 fallback units; at the longest lead a plain pin also searches its
     corrector table's level, for the placebo). A guard row whose issue row is absent refuses (H4 names
     test rows only; READINGS guard_issue_rows). The guard rows are saved, then the lead's adoption is
     hashed (vault.lock_lead_adoption) before any of its test labels opens.
  5  persistence inputs (R31): each test row's NEWEST READABLE label, read through the vault's as-of
     rows (D54 a) BEFORE the lead's lock: timing.latest_label_step(t, L) moved back by R17's
     start_offset_steps, the same step the history block's hist_last_1 reads (t - L - offset; the
     offset is 1 for a target whose window reaches past its step, so its label at the issue step is
     not known there yet). Damped persistence's phi per unit from the unit histories at the lead's
     fit cut, on (y(t), y(t - gap)) pairs with gap = L + offset, and the season-key rule (U-2:
     metrics.shares_season_key) on that gap; the issue-side normal is the one of the label's step.
  6  the lead's test pass: a test row whose issue-step features are missing (its issue row is absent, so
     every moved feature is NaN) is LEFT OUT of scoring (owner ruling H4, H4_RULE): never routed, absent
     from test_preds.parquet and every score, saved in ladder/lead_<L>/issue_missing_rows.parquet with the
     flag issue_features_missing and counted per unit and lead (lead.json issue_features_missing). A
     test row whose issue row exists but holds a non-finite moved feature is counted, not left out
     (READINGS issue_missing_scope; lead.json fits.issue_features_partly_missing). Every test row not
     left out: the arms of layer.arms.lead_arms (the pinned arm, its link's trees-off, and at the
     LONGEST lead only the pinned arm's placebo, Part 559 / F45) plus the identity trees-off (the decline
     target), routed at the pinned penalty through pipeline.router (the run's router kind, the R12
     fallback at the level the lead's own guard surface found, H5); baselines predict-zero, guess-normal,
     the last-5-years normal, persistence and damped persistence, all clipped; EVERY scored row saved
     (ladder/lead_<L>/test_preds.parquet, guard_preds.parquet, lead.json).
The lead-0 contract (plan 4.1 step 11, G-PLUMB 'lead 0 = nowcast'): the ladder's own per-lead code run
at L = 0 reproduces the nowcast exactly. It runs the lead path (_objects: the lead pool opened and filled
by fill_pool from the moved features and the history block at lead 0, FitContext(lead 0, FIT) on that pool,
the bank's donor rows, c, R36's tolerances, the donor-row link means, the GLS weight model refit when the
pin is weighted) and then the test pass's route and row assembly (_route_arms at the nowcast decision
surface's fallback levels, _common_baselines, _rows_frame) on it, and checks: the lead-0 pool equals the
nowcast's pool byte for byte, row block by row block; the bank's donor rows (row keys, grid rows, features,
labels) equal the nowcast bank's inputs byte for byte, so the lead-0 bank, fitted by the deterministic
name-seed recipe on the same inputs, IS the nowcast's bank (it is not refitted); c, the tolerances, the
donor-row means and the GLS weight model's record equal the nowcast's; and every column the lead path
assembles (keys, lead, issue, y, the normal, the pinned arm and the trees-offs before and after the
clip, predict-zero, guess-normal, the last-5-years normal) equals the nowcast's saved column byte for
byte. Not covered (no lead-0 counterpart): the N2 guard and its guard-cut bank (the nowcast decides on the
inner-cut bank, L6 b) and persistence (R31: leads of at least one step).
The ladder table (R34, R35, F57): every lead scored on the rows common to all leads (lead 0 included),
all scored rows beside (H4's left-out rows are in no score); each lead's single verdict (adopted vs its own
link's trees-off; declined leads compare the decline target with itself) under the NOWCAST's band.

Rulings recorded in ladder.json (RULINGS: H2, H3, H4, H5, I1) and the readings still open for the owner
(READINGS; run.py departure ladder_h_readings).
"""

import json
import time
from contextlib import ExitStack
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute.derive.shapes import CutKind, Link
from treeroute.errors import RefusedError
from treeroute.fit.bank import fit_donor_bank
from treeroute.fit.context import FitContext, season_keys_of
from treeroute.fit.pool import open_pool
from treeroute.fit.tables import TreeAnswerStore
from treeroute.fit.weights import weight_model_for_cut, weight_model_record
from treeroute.io.apply import features_at_issue_step
from treeroute.io.steps import predecessor_index, step_bounds
from treeroute.labels.vault import LEAD_ADOPTION_FILE, LOCK_SUFFIX, lock_lead_adoption
from treeroute.layer import arms as LA
from treeroute.layer import decide as LD
from treeroute.layer.links import c_for_cut_against_plan, clip_to_legal
from treeroute.report import metrics as M
from treeroute.route import kinds as RK
from treeroute.runs.atomic import dumps, read_json
from treeroute.timing import latest_label_step

from . import record as REC
from . import router as PR
from . import stages as ST
from .data import _years_of_steps
from . import passes as P
from .passes import HistoryOverride, _write_parquet_once

LADDER_DIR = "ladder"
# what H2 leaves at the lead's fit cut, and why: c and the tolerances by earlier rulings (not a reading); a
# weighted pin's GLS answers as the nowcast's (the one reading left, READINGS guard_gls_answers)
GUARD_FIT_CUT_RULE = ("The guard reads the lead's FIT-cut c and R36 tolerances, exactly as the nowcast's inner "
                      "decision does: c by ruling D63 a (one c per lead, from its FIT cut, serves that lead's guard "
                      "surface and its test pass; layer.c_for_cut refuses guard-cut donor rows); R36's tolerances "
                      "are the identity-check tolerances, which move no prediction. A weighted pin's GLS weight "
                      "model (R25 / D57: its donor rows at the lead's guard cut) reads its error target's tree "
                      "answers from the lead's fit-cut bank, as the nowcast's does (fit.weights.L6_ANSWERS_DISCLOSURE; "
                      "READINGS guard_gls_answers)")
PHASE_CONTRACT = "ladder_contract"
PHASE_LEAD = "ladder_lead_%d"
PHASE_TABLE = "ladder"
CONTRACT_FILE = "contract_lead_0.json"
LADDER_TABLE = "ladder_table.csv"
LADDER_RECORD = "ladder.json"
GUARD_PREDS = "guard_preds.parquet"
LEAD_RECORD = "lead.json"
ISSUE_MISSING_ROWS = "issue_missing_rows.parquet"   # owner ruling H4: the test rows a lead left out
ISSUE_FLAG = "issue_features_missing"                # the flag column of those rows (True on every one)
ISSUE_REASON_ABSENT = "issue_row_absent"             # why: the issue row t - L is not a base row
BLOCK_ROWS = 50000
ROWS_BASIS_COMMON = "common"
ROWS_BASIS_ALL = "all"
H2_RULE = ("owner ruling H2 (L6 b at every lead): each lead refits its bank, correctors and placebo correctors at "
           "the lead's GUARD cut and builds its guard history block there (F1's fallbacks at the guard cut), as "
           "the nowcast's inner decision does at the inner cut, so no guard row sits inside a bank trained on its "
           "labels (asserted: guard_rows_in_bank_label_window is 0); one more bank per lead. %s" % GUARD_FIT_CUT_RULE)
H3_RULE = ("owner ruling H3: at a lead the router context moves to the issue step with the whole feature row "
           "(plan 1.5, io.apply.features_at_issue_step)")
H4_RULE = ("owner ruling H4: a test row whose issue-step features are missing (its issue row t - L is absent from "
           "the base rows, so every moved feature and context value is NaN) is LEFT OUT of scoring: never routed, "
           "absent from test_preds.parquet and from every score, saved in ladder/lead_<L>/%s with the flag %s, "
           "and counted per unit and lead (lead.json issue_features_missing); it is never scored on NaN features"
           % (ISSUE_MISSING_ROWS, ISSUE_FLAG))
H5_RULE = ("owner ruling H5: each lead searches its own R12 fallback level on its own guard surface (the guard "
           "routed at the pinned penalty, the level searched on that surface's pooled fallback rows, the lambda "
           "centre below C15's 10 fallback units); the lead's test pass reads the levels its guard found; lead 0 "
           "(the contract) reads the nowcast decision surface's levels")
I1_RULE = ("owner ruling I1: the leads are 6 and 12 months (C6.lead_months), generic for every package, plus lead "
           "0 (the contract); on annual data both round to 1 year and merge; the pinned placebo is built at the "
           "longest lead")
PARTLY_MISSING_NOTE = ("counted for the owner's reading of H4 (READINGS issue_missing_scope), nothing left out: test "
                       "rows whose issue row t - L EXISTS but holds a non-finite moved tree feature (the trees read "
                       "it 0-filled, R30; the row is scored) or a non-finite moved context value (a scored row with "
                       "one is refused by the router, G1); the nowcast's own rows are counted the same way at lead 0 "
                       "(contract_lead_0.json)")
RULINGS = {"H2": H2_RULE, "H3": H3_RULE, "H4": H4_RULE, "H5": H5_RULE, "I1": I1_RULE}
READINGS = {
    "guard_gls_answers": "a weighted pin's guard GLS weight model reads its error target's tree answers from the "
                         "lead's FIT-cut bank (whose trees saw the guard window's labels), as the nowcast's inner "
                         "decision does under L6 b (fit.weights.L6_ANSWERS_DISCLOSURE: L6 b as ruled names the bank "
                         "and correctors; L6's add-on, the inner GLS target on the refit bank, +0.9-2.4 h over the "
                         "nowcasts, was priced separately and is not ruled). Only a weighted pin reads it. One owner "
                         "answer covers the nowcast and every lead (owner confirms, or both move to the refit bank)",
    "issue_missing_scope": "H4 is read as: a test row whose issue row t - L is absent from the base rows (every "
                           "moved feature NaN: the case departure ladder_readings c put to the owner, 'a row whose "
                           "issue row is absent ... (owner confirms, or they are dropped from scoring and saved "
                           "flagged)'). A test row whose issue row exists keeps R30's 0-fill for a missing tree "
                           "feature and G1's refusal for missing context, as the nowcast's own rows do at lead 0 (a "
                           "broader H4 applied at the leads only would score the nowcast and the leads on different "
                           "row rules). Such rows are counted per lead, lead 0 included (lead.json "
                           "fits.issue_features_partly_missing, ladder.json issue_features_partly_missing), not left "
                           "out. Under the dense census (G-SUPPORT) a test row's issue row lies inside the coverage "
                           "at leads of up to 12 months, so the left-out count is 0 on the four packages (owner "
                           "confirms)",
    "guard_issue_rows": "H4 names test rows; a GUARD-surface row whose issue row is absent refuses loudly (never "
                        "scored on NaN features, never left out without a ruling); owner: rule whether H4 also "
                        "leaves such guard rows out",
    "lead0_bank": "the lead-0 contract runs the lead path at lead 0 (the lead pool, FitContext(lead 0) and its "
                  "donor rows, c, tolerances, donor-row means, the GLS refit when the pin is weighted, the route "
                  "and the row assembly) and proves the bank's inputs (donor row keys, grid rows, features, "
                  "labels) equal the nowcast bank's byte for byte; the bank itself is not refitted (deterministic "
                  "name seeds on the same inputs give the same fit). The guard (and its guard-cut bank) and "
                  "persistence have no lead-0 counterpart and are not covered",
    "g1_normal": "owner ruling G1 with R15: at a pass where G1 left fit rows out, the normal of each unit that lost "
                 "rows is the mean over its KEPT fit rows (pipeline.stages G1_NORMAL), so that pass's saved normal "
                 "column, guess-normal, the decline target and, at the test pass, damped persistence's normal follow "
                 "the G1 fit rows, while damped persistence's phi is fitted on every label of the unit's history at "
                 "the lead's fit cut (two row sets in one baseline); kept as built; context_missing in lead.json "
                 "names the units and steps it touches",
}
LEAD0_COVERS = ("the moved features and the history block at lead 0 filled into a lead pool (fill_pool); "
                "FitContext(lead 0) on that pool: the bank's donor rows, c, R36's tolerances, the donor-row link "
                "means, the GLS weight model when the pin is weighted; the pinned route and the trees-offs at the "
                "nowcast decision surface's fallback levels; the test rows' assembly (keys, lead, issue, y, normal, "
                "arms before and after the clip, predict-zero, guess-normal, last-5-years normal)")
LEAD0_NOT_COVERED = ("the bank refit (its inputs are proven equal instead: READINGS lead0_bank); the N2 guard and its "
                     "guard-cut bank (the nowcast decides on the inner-cut bank, L6 b); persistence and damped "
                     "persistence (R31: leads of at least one step)")


def _newest_label_steps(target_steps: np.ndarray, lead: int, offset: int) -> np.ndarray:
    """The newest label a row predicting step t may read at lead L (R11, R17): timing.latest_label_step(t, L)
    (computed once per distinct step), moved back by R17's start_offset_steps, as the history block does."""
    steps = np.asarray(target_steps, dtype=np.int64)
    if steps.size == 0:
        return steps.copy()
    distinct, inverse = np.unique(steps, return_inverse=True)
    newest = np.fromiter((latest_label_step(int(t), int(lead)) for t in distinct.tolist()), dtype=np.int64,
                         count=distinct.size)
    return newest[np.asarray(inverse).reshape(-1)] - int(offset)


def _rows_differ(a: np.ndarray, b: np.ndarray) -> int:
    """The rows of two feature blocks that are not the same bytes (NaN equals NaN); a dtype or shape that
    differs counts every row."""
    if a.dtype != b.dtype or a.shape != b.shape:
        return max(int(a.shape[0]) if a.ndim else 1, 1)
    same = (a == b) | (np.isnan(a) & np.isnan(b))
    return int((~same).reshape(same.shape[0], -1).any(axis=1).sum()) if same.ndim else int(not bool(same))


def _same_array(a: Any, b: Any) -> bool:
    """Same dtype, shape and values (NaN equals NaN for floats)."""
    x, z = np.asarray(a), np.asarray(b)
    if x.dtype != z.dtype or x.shape != z.shape:
        return False
    return bool(np.array_equal(x, z, equal_nan=True)) if x.dtype.kind == "f" else bool(np.array_equal(x, z))


def _same_features(a: Any, b: Any) -> bool:
    """_same_array on two donor feature matrices, eager or lazy (fit.context.LazyDonorFeatures, plan R20: read and
    compared in blocks of rows, never whole)."""
    if not (getattr(a, "lazy_rows", False) or getattr(b, "lazy_rows", False)):
        return _same_array(a, b)
    if tuple(a.shape) != tuple(b.shape) or np.dtype(a.dtype) != np.dtype(b.dtype):
        return False
    for a0 in range(0, int(a.shape[0]), BLOCK_ROWS):
        idx = np.arange(a0, min(a0 + BLOCK_ROWS, int(a.shape[0])), dtype=np.int64)
        if not _same_array(a[idx], b[idx]):
            return False
    return True


def _same_float(a: Optional[float], b: Optional[float]) -> bool:
    """Both absent, or the same float (NaN equals NaN)."""
    if a is None or b is None:
        return a is None and b is None
    fa, fb = float(a), float(b)
    return fa == fb or (np.isnan(fa) and np.isnan(fb))


def _counts(values: np.ndarray) -> Dict[str, int]:
    """{value as text: count}, sorted by value."""
    v = np.asarray(values)
    if v.size == 0:
        return {}
    uniq, n = np.unique(v.astype(str) if v.dtype.kind in "OUS" else v, return_counts=True)
    return {str(u): int(k) for u, k in zip(uniq.tolist(), n.tolist())}


def _partly_missing(values: Optional[np.ndarray], columns: Sequence[str], keep: np.ndarray,
                    units: np.ndarray) -> Dict[str, Any]:
    """Among the rows picked by keep (test rows whose issue row exists), the rows with at least one non-finite
    value in values (rows x columns), the count per column (columns with none left out) and the units touched.
    Counted only: what H4's reading (READINGS issue_missing_scope) leaves these rows to is unchanged."""
    keep = np.asarray(keep, dtype=bool)
    if values is None or not len(columns):
        return {"rows": 0, "units": 0, "by_column": {}}
    out_rows = np.zeros(keep.size, dtype=bool)
    by_col = np.zeros(len(columns), dtype=np.int64)
    idx = np.flatnonzero(keep)
    for a0 in range(0, idx.size, BLOCK_ROWS):
        r = idx[a0:a0 + BLOCK_ROWS]
        bad = ~np.isfinite(np.asarray(values[r], dtype=np.float64))
        out_rows[r] = bad.any(axis=1)
        by_col += bad.sum(axis=0)
    return {"rows": int(out_rows.sum()), "units": int(np.unique(np.asarray(units, dtype=object)[out_rows].astype(str)).size),
            "by_column": {str(c): int(k) for c, k in zip(columns, by_col.tolist()) if k}}


class _PoolRows(object):
    """values[r] for _partly_missing under per-group batching: rows r of the test keys read back from the filled
    lead pool (its first `width` tree columns, the moved tree features, or its context columns), float32 as
    written: the same values the whole path's moved arrays hold."""

    def __init__(self, pool: Any, keys: np.ndarray, width: int, tree: bool) -> None:
        self.pool, self.keys, self.width, self.tree = pool, np.asarray(keys, dtype=np.int64), int(width), bool(tree)

    def __getitem__(self, r: Any) -> np.ndarray:
        rows = self.keys[np.asarray(r)]
        if self.tree:
            return np.asarray(self.pool.tree_features(rows))[:, :self.width]
        return np.asarray(self.pool.context(rows))


def _context_missing_summary(router_records: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """Owner ruling G1 at one pass of a lead: the fit rows left out for missing router context (the pass's
    full record, per unit, is in its router records); None when the pass's router reads no context."""
    rec = router_records.get("context_missing")
    if rec is None:
        return None
    return {"fit_rows": int(rec["fit_rows"]), "rows_left_out": int(rec["rows_left_out"]),
            "units_in_fit": int(rec["units_in_fit"]), "units_with_rows_left_out": int(rec["units_with_rows_left_out"]),
            "flagged_units": list(rec["flagged_units"]), "flag_share": rec["flag_share"],
            "by_column": dict(rec["by_column"]), "by_step": dict(rec["by_step"]),
            "rows_file": rec.get("rows_file")}


class LadderRefusal(RefusedError):
    """The forecast ladder refused (fail loudly)."""


def lead_plan(derived: Mapping[str, Any]) -> Tuple[Tuple[int, ...], Mapping[int, Any]]:
    """(R10's leads in steps, ascending; {lead: R11 cut pair}, lead 0 included). Refuses a lead plan that is
    not in steps (events: M8), a lead without its cut pair, and a lead-0 contract that is off."""
    lp = derived["R10"].value
    unit = getattr(getattr(lp, "lead_unit", None), "value", getattr(lp, "lead_unit", None))
    if unit != "steps":
        raise NotImplementedError("the forecast ladder for leads in %s (events) is built at milestone M8" % (unit,))
    if not bool(getattr(lp, "contract_lead_zero", False)):
        raise LadderRefusal("R10", "the lead plan has no lead-0 contract; lead 0 always runs as the contract")
    leads = tuple(sorted(int(x) for x in lp.leads))
    cuts = {int(k): v for k, v in derived["R11"].value.items()}
    missing = [L for L in (0,) + leads if L not in cuts]
    if missing:
        raise LadderRefusal("R11", "leads %s have no cut pair in derived.json" % missing)
    if any(L < 1 for L in leads):
        raise LadderRefusal("R10", "the ladder's leads must be at least 1 step (lead 0 is the contract), got %s"
                            % (leads,))
    return leads, cuts


def phase_names(derived: Mapping[str, Any]) -> List[str]:
    """The ladder's phases in run order: the lead-0 contract, one per lead, the ladder table."""
    leads, _ = lead_plan(derived)
    return [PHASE_CONTRACT] + [PHASE_LEAD % L for L in leads] + [PHASE_TABLE]


def log_parts(derived: Mapping[str, Any]) -> List[str]:
    """The fitctx log parts the ladder writes (one per phase)."""
    return phase_names(derived)


@dataclass
class LeadObjects:
    """Everything one lead fits at its FIT cut (all through FitContext at that lead's cuts). ctx_guard is the
    lead's GUARD-cut context over the lead pool (the fit-cut history block): the guard history block's F1
    fallbacks and, for a weighted pin, the GLS weight model's guard rows read it."""
    lead: int
    cuts: Any
    ctx_fit: Any
    ctx_guard: Any
    pool: Any
    store: Any
    masks: Any
    bank: Any
    c: Optional[float]
    tol: Dict[Any, float]
    tol_record: Dict[str, Any]
    donor_mean_fit: Dict[Any, float]
    weights: Any
    record: Dict[str, Any]
    issue_absent: Any = None                # per grid row: the issue row t - L is not a base row
    donor0: Any = None                      # lead 0 only: the bank's donor rows, checked by the contract


@dataclass
class GuardObjects:
    """What one lead's N2 guard routes through (owner ruling H2): the lead's GUARD-cut context over the guard
    features (the lead pool with the history block rebuilt at the guard cut), the bank refit there, its store
    and own-block masks, and the donor-row link means at the guard cut. refit False: A7 is off (L6 a), and
    these are the lead's fit-cut objects."""
    ctx: Any
    features: Any
    bank: Any
    store: Any
    masks: Any
    donor_mean: Dict[Any, float]
    refit: bool
    record: Dict[str, Any]


def _json(obj: Any) -> Any:
    return json.loads(dumps(M._json_safe(obj)))


class Ladder(object):
    """The ladder of one run (module docstring). state: the RunState after the nowcast (adoption locked or
    read back, the fit-cut bank and its store, the pool); run() releases the nowcast's banks once the ladder
    no longer reads them (RunState.release_bank)."""

    def __init__(self, state: Any) -> None:
        self.s = state
        self.p = state.p
        self.leads, self.cuts = lead_plan(state.derived)
        self.longest = max(self.leads) if self.leads else None
        self.folder = self.p.folder / LADDER_DIR
        self.pinned, self.pin_point = LD.pin_of(state.adoption)
        self.levels = state.decided_levels()                 # the nowcast decision surface's: lead 0 only (H5)
        self.n = int(state.vg.grid.n_steps)

    # ------------------------------------------------------------------ helpers
    def _log(self, msg: str) -> None:
        self.s._beat("ladder", msg)

    def _lead_dir(self, L: int):
        d = self.folder / ("lead_%d" % L)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _decline_links(self) -> Tuple[Any, ...]:
        return () if self.pinned.link == Link.IDENTITY else (Link.IDENTITY,)

    def _test_rows(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        s = self.s
        keys = ST.unit_positions(s.vg, s.scored_units, s.vg.test_first, None)
        return keys, s.vg.unit_ids[keys], s.vg.steps[keys]

    def _moved(self, L: int) -> Tuple[np.ndarray, Optional[np.ndarray], np.ndarray]:
        """The kept tree features and router context of every grid row, moved to its issue step t - L
        (io.apply.features_at_issue_step on the base rows of the bank units, pre-Y0 lag year included),
        and a per-grid-row flag: the issue row is absent from the base rows."""
        s, p = self.s, self.p
        reader = p.reader
        lagged = reader.lagged(s.derived["R8"].value)
        units = np.asarray(reader.units, dtype=object).astype(str)
        sub = np.flatnonzero(np.isin(units, np.asarray(s.bank_units, dtype=object).astype(str)))
        codes, steps = reader.codes[sub], reader.steps[sub]
        tcols, ccols = list(p.spec.tree_features), list(p.spec.context)
        X = lagged[tcols].to_numpy(dtype=np.float32)[sub] if tcols else np.zeros((sub.size, 0), dtype=np.float32)
        moved = features_at_issue_step(X, codes, steps, L)
        moved_c = None
        if ccols:
            moved_c = features_at_issue_step(lagged[ccols].to_numpy(dtype=np.float32)[sub], codes, steps, L)
        inv = np.full(units.size, -1, dtype=np.int64)
        inv[sub] = np.arange(sub.size, dtype=np.int64)
        base = reader.base_rows(s.vg.unit_ids, s.vg.steps)
        gpos = inv[base]
        if (gpos < 0).any():
            raise LadderRefusal("R8", "internal: %d grid rows are not base rows of a bank unit" % int((gpos < 0).sum()))
        absent = (predecessor_index(codes, steps, L) < 0)[gpos] if L > 0 else np.zeros(gpos.size, dtype=bool)
        return moved[gpos], (moved_c[gpos] if moved_c is not None else None), absent

    def _moved_group(self, L: int, rows: np.ndarray, tree_v: np.ndarray, ctx_v: Optional[np.ndarray],
                     absent: np.ndarray) -> Tuple[np.ndarray, Optional[np.ndarray], np.ndarray]:
        """Per-group batching (plan R20): one group's moved tree features, router context and 'issue row absent'
        flags on its grid rows (ascending), as RunState.fill_pool_by_group writes them into the lead pool; returned
        unchanged. The seam the whole path's _moved is: a test plants a fault on either."""
        return tree_v, ctx_v, absent

    def _history(self, ctx: Any, L: int) -> Tuple[np.ndarray, Dict[str, float], Optional[float]]:
        """R17's block at lead L (newest readable label t - L), its fallbacks at ctx's cut (F1)."""
        s = self.s
        spec17 = s.derived["R17"].value
        rows = np.arange(len(s.vg.grid.unit_ids) * self.n, dtype=np.int64)
        if not spec17.columns:
            return np.zeros((rows.size, 0), dtype=np.float32), {}, None
        fill, donor_mean = ST.history_inputs(ctx, s.vg, self.p.split_sets, s.bank_units)
        hist, filled = ST.history_block(s.vg.grid, spec17, s.vg.steps, rows // self.n, L, s.labels, fill,
                                        season_keys_of(s.vg.steps, s.season), donor_mean)
        return hist, dict(filled), donor_mean

    def _tree_columns(self) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
        spec17 = self.s.derived["R17"].value
        return tuple(self.p.spec.tree_features) + tuple(spec17.columns), tuple(self.p.spec.context)

    # ------------------------------------------------------------------ the lead-0 contract
    def _pool_gap(self, mine: Any, theirs: Any) -> Tuple[int, int, int]:
        """(grid rows compared, rows whose tree features and history differ, rows whose context differs)
        between two pools over every grid row, block by block (NaN equals NaN; a dtype or shape that differs
        counts every row of the block)."""
        if tuple(mine.tree_columns) != tuple(theirs.tree_columns) or \
                tuple(mine.context_columns) != tuple(theirs.context_columns):
            raise LadderRefusal("G-PLUMB", "lead-0 contract: the lead pool's columns %s / %s are not the nowcast "
                                "pool's %s / %s" % (list(mine.tree_columns), list(mine.context_columns),
                                                    list(theirs.tree_columns), list(theirs.context_columns)))
        rows = np.arange(len(self.s.vg.grid.unit_ids) * self.n, dtype=np.int64)
        bad_tree = bad_ctx = 0
        for a0 in range(0, rows.size, BLOCK_ROWS):
            r = rows[a0:a0 + BLOCK_ROWS]
            bad_tree += _rows_differ(np.asarray(mine.tree_features(r)), np.asarray(theirs.tree_features(r)))
            if tuple(mine.context_columns):
                bad_ctx += _rows_differ(np.asarray(mine.context(r)), np.asarray(theirs.context(r)))
        return int(rows.size), int(bad_tree), int(bad_ctx)

    def _check_lead0_donor(self, donor: Any) -> Dict[str, Any]:
        """At lead 0 the bank is not refitted (READINGS lead0_bank): its inputs, the donor rows FitContext(lead
        0) hands out on the LEAD pool, must be the nowcast bank's inputs byte for byte."""
        ref = self.s.donor_fit
        checks = {"row_key_hash": donor.row_key_hash == ref.row_key_hash,
                  "cut": (int(donor.cut), int(donor.lead)) == (int(ref.cut), int(ref.lead)),
                  "groups": tuple(donor.groups) == tuple(ref.groups),
                  "grid_rows": _same_array(donor.grid_rows, ref.grid_rows),
                  "unit_ids": np.array_equal(np.asarray(donor.unit_ids, dtype=object),
                                             np.asarray(ref.unit_ids, dtype=object)),
                  "times": _same_array(donor.times, ref.times),
                  "y": _same_array(donor.y, ref.y),
                  "X": _same_features(donor.X, ref.X)}
        bad = sorted(k for k, ok in checks.items() if not ok)
        if bad:
            raise LadderRefusal("G-PLUMB", "lead-0 contract: the lead-0 bank's donor rows differ from the nowcast "
                                "bank's in %s, so the nowcast's bank cannot stand for the lead-0 bank" % bad)
        return {"donor_rows": int(np.asarray(donor.y).size), "row_key_hash": donor.row_key_hash,
                "identical": sorted(checks)}

    def _check_lead0_fits(self, o: "LeadObjects") -> Dict[str, bool]:
        """The lead path's lead-0 c, tolerances, donor-row link means and (a weighted pin) GLS weight model
        equal the nowcast's."""
        s = self.s

        def same_map(a: Mapping[Any, Any], b: Mapping[Any, Any]) -> bool:
            return set(a) == set(b) and all(_same_float(a[k], b[k]) for k in a)
        checks = {"c": _same_float(o.c, s.c),
                  "tolerances": same_map(o.tol, s.tol) and _json(o.tol_record) == _json(s.tol_record),
                  "donor_link_means": same_map(o.donor_mean_fit, s.donor_mean_fit)}
        if o.weights is not None:
            from treeroute.derive.derived import derived_entry

            checks["gls_weight_model"] = s.weights is not None and \
                _json(derived_entry(weight_model_record(o.weights))) == _json(derived_entry(weight_model_record(s.weights)))
        bad = sorted(k for k, ok in checks.items() if not ok)
        if bad:
            raise LadderRefusal("G-PLUMB", "lead-0 contract: the lead path's %s differ(s) from the nowcast's at the "
                                "same cut" % bad)
        return {k: True for k in sorted(checks)}

    def contract(self) -> Dict[str, Any]:
        """Lead 0 through the ladder's own per-lead code reproduces the nowcast exactly (module docstring)."""
        s, p = self.s, self.p
        t0 = time.time()
        self._log("lead-0 contract: the ladder's lead path at lead 0 against the nowcast")
        cut0 = self.cuts[0]
        if (int(cut0.fit_cut), int(cut0.guard_cut)) != (int(s.cuts.fit_cut), int(s.cuts.guard_cut)):
            raise LadderRefusal("R11", "the lead-0 cut pair %s is not the nowcast's %s" % (cut0, s.cuts))
        t_keys, t_units, t_steps = self._test_rows()
        now = M.read_rows(p.folder / REC.TEST_PREDS)
        if not (np.array_equal(now[M.COL_UNIT].to_numpy(dtype=object), np.asarray(t_units, dtype=object))
                and np.array_equal(now[M.COL_TIME].to_numpy(dtype=np.int64), np.asarray(t_steps, dtype=np.int64))):
            raise LadderRefusal("G-PLUMB", "lead-0 contract: the nowcast's saved rows are not the ladder's test rows")
        name = LA.arm_name(self.pinned)
        off_name = LA.arm_name(LA.trees_off_of(self.pinned.link))
        with ExitStack() as stack:
            o = self._objects(0, stack)
            n_rows, bad_tree, bad_ctx = self._pool_gap(o.pool, s.pool)
            if bad_tree or bad_ctx:
                raise LadderRefusal("G-PLUMB", "lead-0 contract: the ladder's lead-0 pool differs from the nowcast "
                                    "pool on %d rows (tree features and history) and %d rows (context)"
                                    % (bad_tree, bad_ctx))
            bank_inputs = self._check_lead0_donor(o.donor0)
            o.donor0 = None
            fits = self._check_lead0_fits(o)
            arms, placebos, pre, normal_id, routed = self._route_arms(o, t_keys, t_units, t_steps, [self.pinned],
                                                                     "lead 0 contract", "router_lead0_contract",
                                                                     self.levels)
            baselines = self._common_baselines(o, t_keys, t_units, t_steps, normal_id)
            frame = self._rows_frame(0, t_units, t_steps, now[M.COL_Y].to_numpy(dtype=np.float64), normal_id, arms,
                                     placebos, pre, baselines)
            bank_print = o.bank.manifest.bank_fingerprint
            partly = o.record["issue_features_partly_missing"]
            del o
        missing = [c for c in frame.columns if c not in now.columns]
        differ = [c for c in frame.columns if c in now.columns
                  and not frame[c].reset_index(drop=True).equals(now[c].reset_index(drop=True))]
        p_pre, off_pre = pre[name], pre[off_name]
        now_pre = now[M.PRE_PREFIX + name].to_numpy(dtype=np.float64)
        now_off = now[M.PRE_PREFIX + off_name].to_numpy(dtype=np.float64)
        plumb = LD.check_plumbing(off_pre, now_off, p_pre, now_pre, None, None, p_pre, now_pre,
                                  float(s.tol[self.pinned.link]))
        if missing or differ or plumb.status is LD.GuardStatus.BLOCK:
            gap = float(np.max(np.abs(p_pre - now_pre))) if p_pre.size else 0.0
            raise LadderRefusal("G-PLUMB", "lead-0 contract FAILED: the ladder's lead-0 path is not the nowcast's: "
                                "columns %s differ%s (largest gap of %s: %.3g; trees-off equal: %s)"
                                % (differ, ("; %s are not nowcast columns" % missing) if missing else "", name, gap,
                                   bool(np.array_equal(off_pre, now_off))))
        rec = {"lead": 0, "pinned": name, "penalty": {"level": self.pin_point.level, "ratio": self.pin_point.ratio},
               "rows": int(t_keys.size), "pool_rows_compared": n_rows, "pool_identical": True,
               "pinned_pre_clip_identical": True, "trees_off_identical": True,
               "columns_identical": [str(c) for c in frame.columns], "fits_identical": fits,
               "bank_inputs": bank_inputs, "g_plumb": dict(plumb.details),
               "cuts": {"fit_cut": int(cut0.fit_cut), "guard_cut": int(cut0.guard_cut)},
               "bank": READINGS["lead0_bank"], "bank_fingerprint": bank_print,
               "fallback_levels": "the nowcast decision surface's (lead 0 is the nowcast; H5 applies at leads >= 1)",
               "covers": LEAD0_COVERS, "not_covered": LEAD0_NOT_COVERED,
               "issue_features_partly_missing": partly, "router": _json(routed.records)}
        self.folder.mkdir(parents=True, exist_ok=True)
        REC.write_once_or_same(self.folder / CONTRACT_FILE, _json(rec))
        self._log("lead-0 contract holds: the ladder's lead path at lead 0 equals the nowcast byte for byte (pool, "
                  "bank inputs, c, tolerances, donor means, %d saved columns of %d rows) in %.1f s"
                  % (len(frame.columns), t_keys.size, time.time() - t0))
        return rec

    # ------------------------------------------------------------------ one lead: the fit-cut objects
    def _objects(self, L: int, stack: ExitStack) -> LeadObjects:
        s, p = self.s, self.p
        cuts = self.cuts[L]
        tree_cols, ctx_cols = self._tree_columns()
        rows = np.arange(len(s.vg.grid.unit_ids) * self.n, dtype=np.int64)
        pool = stack.enter_context(open_pool(p.temp_dir, "pool_lead_%d" % L, rows, tree_cols, ctx_cols))
        ctx_fit = FitContext(s.derived, p.split_sets, s.vg.grid, s.labels, pool, s.lists, L, CutKind.FIT)
        s.extra_contexts.append(("ctx_fit_lead_%d" % L, ctx_fit))
        hist, filled, dmean = self._history(ctx_fit, L)
        t_keys, t_units, _ = self._test_rows()
        tcols, ccols = list(p.spec.tree_features), list(p.spec.context)
        if s.per_group:
            # plan R20's per-group batching: the moved features filled group by group (RunState.fill_pool_by_group);
            # the test rows' features read back from the pool (the same float32 values Ladder._moved gives)
            absent = s.fill_pool_by_group(pool, hist, L, move=features_at_issue_step,
                                          adjust=lambda rows, tv, cv, ab: self._moved_group(L, rows, tv, cv, ab))
            tree_v = _PoolRows(pool, t_keys, len(tcols), True) if tcols else None
            ctx_v = _PoolRows(pool, t_keys, len(ccols), False) if ccols else None
            present = ~absent[t_keys]
            part_tree = _partly_missing(tree_v, tcols, present, t_units)
            part_ctx = _partly_missing(ctx_v, ccols, present, t_units)
        else:
            tree_v, ctx_v, absent = self._moved(L)
            ST.fill_pool(pool, s.vg, lambda r: tree_v[r],
                         (lambda r: ctx_v[r]) if ctx_v is not None else (lambda r: None), hist, s.log)
            present = ~absent[t_keys]
            part_tree = _partly_missing(tree_v[t_keys] if tcols else None, tcols, present, t_units)
            part_ctx = _partly_missing(ctx_v[t_keys] if ctx_v is not None else None, ccols, present, t_units)
        rec: Dict[str, Any] = {"history_filled_share": filled, "history_donor_mean": dmean,
                               "issue_row_absent": {"grid_rows": int(absent.sum()), "test_rows": int(absent[t_keys].sum())},
                               "issue_features_partly_missing": {
                                   "reading": PARTLY_MISSING_NOTE, "test_rows_with_issue_row": int(present.sum()),
                                   "tree_features": part_tree, "context": part_ctx}}
        if L > 0 and (part_tree["rows"] or part_ctx["rows"]):
            s.log("lead %d: %d test row(s) of %d unit(s) have an issue row with a non-finite tree feature (read "
                  "0-filled by the trees, R30) and %d a non-finite context value (refused if scored, G1); counted, "
                  "not left out (READINGS issue_missing_scope)" % (L, part_tree["rows"], part_tree["units"],
                                                                    part_ctx["rows"]))
        del tree_v, ctx_v, hist
        # the GUARD-cut context over this pool: the guard history block's F1 fallbacks and the GLS weight model
        ctx_guard = ctx_fit.for_lead(L, CutKind.GUARD)
        s.extra_contexts.append(("ctx_guard_history_lead_%d" % L, ctx_guard))
        if L == 0:
            # the lead-0 contract: the nowcast's bank stands for the lead-0 bank once the contract proves its
            # inputs (these donor rows) equal (_check_lead0_donor)
            donor = s.donor(ctx_fit, "bank")
            bank, store, masks = s.bank_fit, s.store_fit, s.masks_fit
        else:
            self._log("lead %d: lagtrain bank at the lead's fit cut %d (%d groups x %d trees)"
                      % (L, cuts.fit_cut, len(s.groups), p.trees_per_group))
            donor = s.donor(ctx_fit, "bank")
            bank = fit_donor_bank(donor, p.trees_per_group)
            s._check_bank(bank, "lead-%d" % L)
            store = stack.enter_context(TreeAnswerStore.from_bank(bank, ST.row_group_of(s.vg), p.temp_dir, p.registry,
                                                                  echo=p.log))
            masks = ST.block_masks(bank.tree_group, p.blocks)
        c = c_for_cut_against_plan(donor, s.derived) if Link.LOG_C in s.links else None
        tol, tol_record = ST.guard_tolerances(donor, s.links, c, s.ub, p.smoke)
        dm_fit = ST.donor_link_means(donor, s.links, c, s.ub)
        weights = None
        if self.pinned.weighting is LA.Weighting.GLS:
            self._log("lead %d: the pinned arm is weighted: GLS weight model refit at the lead's guard cut %d"
                      % (L, cuts.guard_cut))
            # RAM tactic 6: the donor matrix is a temp memmap in the run's temp folder (byte-identical forest); its
            # notes and the room check's "[waiting]" notes go to the run's echo (run.log), as in the nowcast's fit
            weights = weight_model_for_cut(ctx_fit, ctx_guard, s.answers_once(store), bank.tree_group, blocks=p.blocks,
                                           matrix_dir=p.temp_dir, echo=p.log)
            if L > 0:
                from treeroute.derive.derived import derived_entry

                REC.write_once_or_same(self._lead_dir(L) / "gls_weight_model.json",
                                       derived_entry(weight_model_record(weights)))
        rec.update({"bank": {"fingerprint": bank.manifest.bank_fingerprint, "trees": len(bank.trees),
                             "cut": int(bank.manifest.cut), "max_label_time": int(bank.manifest.max_label_time),
                             "donor_rows": int(np.asarray(donor.y).size), "donor_row_key_hash": donor.row_key_hash},
                    "c": c, "tolerances": tol_record,
                    "gls_weight_model": ("refit at the lead's cut (the pinned arm is weighted)" if weights is not None
                                         else "not refit (the pinned arm is unweighted, R25)")})
        out = LeadObjects(lead=L, cuts=cuts, ctx_fit=ctx_fit, ctx_guard=ctx_guard, pool=pool, store=store,
                          masks=masks, bank=bank, c=c, tol=tol, tol_record=tol_record, donor_mean_fit=dm_fit,
                          weights=weights, record=rec, issue_absent=absent, donor0=donor if L == 0 else None)
        del donor
        return out

    # ------------------------------------------------------------------ one lead: the guard-cut objects (H2)
    def _guard_objects(self, o: LeadObjects, stack: ExitStack) -> GuardObjects:
        """Owner ruling H2 (L6 b at every lead; module docstring step 3): the lead's guard history block at its
        guard cut, written over the lead pool's history columns (HistoryOverride), and the bank, correctors and
        placebo correctors refit on the donor rows at the guard cut through FitContext(lead L, GUARD) over those
        features. With A7.inner_cut_bank_refit off (L6 a) the guard reads the lead's fit-cut objects."""
        s, p = self.s, self.p
        L = o.lead
        if L < 1:
            raise LadderRefusal("R29", "internal: lead 0 has no guard (it is the contract)")
        if not K.INNER_CUT_BANK_REFIT:
            dm = ST.donor_link_means(s.donor(o.ctx_guard, "normal_fallback"), s.links, o.c, s.ub)
            return GuardObjects(ctx=o.ctx_guard, features=o.pool, bank=o.bank, store=o.store, masks=o.masks,
                                donor_mean=dm, refit=False,
                                record={"refit": False, "rule": "A7.inner_cut_bank_refit is off (L6 a): the guard "
                                                                "reads the lead's fit-cut bank, history block, c and "
                                                                "tolerances"})
        spec17 = s.derived["R17"].value
        features = o.pool
        hist_rec: Any = "no history block (R17 has no column)"
        if spec17.columns:
            hist, filled, dmean = self._history(o.ctx_guard, L)
            rows = np.arange(len(s.vg.grid.unit_ids) * self.n, dtype=np.int64)
            hpool = stack.enter_context(open_pool(p.temp_dir, "pool_guard_history_lead_%d" % L, rows,
                                                  tuple(spec17.columns), ()))
            for a0 in range(0, rows.size, BLOCK_ROWS):
                hpool.write(rows[a0:a0 + BLOCK_ROWS], hist[a0:a0 + BLOCK_ROWS], None)
            hpool.require_complete()
            del hist
            features = HistoryOverride(o.pool, hpool)
            hist_rec = {"cut": int(o.ctx_guard.cut), "filled_share": filled, "donor_mean": dmean}
            self._log("lead %d: guard history block at the lead's guard cut %d: donor-row mean %.6g (fit cut %.6g)"
                      % (L, o.ctx_guard.cut, dmean, o.record["history_donor_mean"]))
        ctx = FitContext(s.derived, p.split_sets, s.vg.grid, s.labels, features, s.lists, L, CutKind.GUARD)
        s.extra_contexts.append(("ctx_guard_lead_%d" % L, ctx))
        self._log("lead %d: guard bank refit at the lead's guard cut %d (owner ruling H2, L6 b at every lead: %d "
                  "groups x %d trees)" % (L, ctx.cut, len(s.groups), p.trees_per_group))
        donor = s.donor(ctx, "bank_guard")
        bank = fit_donor_bank(donor, p.trees_per_group)
        s._check_bank(bank, "lead-%d guard-cut" % L)
        store = stack.enter_context(TreeAnswerStore.from_bank(bank, ST.row_group_of(s.vg), p.temp_dir, p.registry,
                                                              echo=p.log))
        masks = ST.block_masks(bank.tree_group, p.blocks)
        dm = ST.donor_link_means(donor, s.links, o.c, s.ub)
        rec = {"refit": True, "rule": H2_RULE,
               "bank": {"fingerprint": bank.manifest.bank_fingerprint, "trees": len(bank.trees),
                        "cut": int(bank.manifest.cut), "max_label_time": int(bank.manifest.max_label_time),
                        "donor_rows": int(np.asarray(donor.y).size), "donor_row_key_hash": donor.row_key_hash},
               "history": hist_rec,
               "c_tolerances_weights": GUARD_FIT_CUT_RULE}
        del donor
        return GuardObjects(ctx=ctx, features=features, bank=bank, store=store, masks=masks, donor_mean=dm,
                            refit=True, record=rec)

    def _placebo_level_tables(self, L: int) -> Tuple[Tuple[Any, str], ...]:
        """Owner ruling H5 with R12's rule that the placebo takes its corrector's fallback level: at the longest
        lead (where the placebo is built) a PLAIN pin's guard also searches its link's corrector level."""
        if self.s.kind != PR.KIND_PER_UNIT or L != self.longest or self.pinned.tool is not LA.Tool.PLAIN:
            return ()
        return ((self.pinned.link, "corrector"),)

    def _guard(self, o: LeadObjects, g: GuardObjects) -> Tuple[Any, Dict[str, Any], Dict[str, Any]]:
        """R29's N2 guard on the lead's inner guard surface (module docstring, step 4), routed through the
        guard objects (H2), with the lead's own fallback level search (H5); returns the LeadAdoption, the guard
        record and the fallback levels the guard surface found, with the guard rows saved."""
        s, p = self.s, self.p
        L = o.lead
        fit_cut, guard_cut = int(o.cuts.fit_cut), int(o.cuts.guard_cut)
        first = int(s.cuts.guard_cut) + 1                         # the inner score window's first step
        row_of = {u: i for i, u in enumerate(s.vg.grid.unit_ids)}
        vu, vt, vv = s.labels.validity(first, fit_cut)
        pos = np.fromiter((row_of[u] for u in vu.tolist()), dtype=np.int64, count=vu.size) * self.n \
            + (vt - s.vg.first_step)
        scored = np.isin(vu, np.asarray(s.scored_units, dtype=object))
        last_day = int(step_bounds(np.array([fit_cut], dtype=np.int64), p.cadence)[1][0])
        ended = s.vg.window_end[pos] <= last_day
        pick = scored & vv & ended
        if not pick.any():
            raise LadderRefusal("R29", "lead %d: the inner guard surface (steps %d..%d) holds no scored row with a "
                                "valid label" % (L, first, fit_cut))
        g.ctx.check_inner_score_rows(vt[pick] - L)                  # G-FITCUT: issued at or after the guard cut
        absent = np.asarray(o.issue_absent, dtype=bool)[pos[pick]]
        if absent.any():
            bu, bt = vu[pick][absent], vt[pick][absent]
            raise LadderRefusal("H4", "lead %d: %d guard-surface row(s) have no issue row at t - %d (first %s); owner "
                                "ruling H4 leaves out TEST rows only, and a guard row is never scored on NaN features"
                                % (L, int(absent.sum()), L, ", ".join("%s@%d" % (u, int(t)) for u, t in
                                                                     list(zip(bu.tolist(), bt.tolist()))[:5])),
                                fix="owner item (READINGS guard_issue_rows): rule whether H4 also leaves such guard "
                                    "rows out")
        surface = s.labels.decision_surface(vu[pick], vt[pick], fit_cut, purpose="lead_%d_guard" % L)
        g_keys = pos[pick]
        units = np.asarray(surface.unit_ids, dtype=object)
        times = np.asarray(surface.times, dtype=np.int64)
        y = np.asarray(surface.y, dtype=np.float64)
        bank_newest = int(g.bank.manifest.max_label_time)
        in_window = int((times <= bank_newest).sum())
        if g.refit and in_window:
            raise LadderRefusal("H2", "lead %d: %d guard row(s) are dated at or before the guard bank's newest label "
                                "%d; L6 b at every lead keeps every guard row outside its bank's label window"
                                % (L, in_window, bank_newest))
        nowcast_held = s.banks_held()          # [] under Ladder.run (RunState.release_bank)
        kind = LA.table_kind(self.pinned)
        sched = s._pass_tables(g.store, g.features, (kind,), fit_cut, "ladder")
        inp = PR.PassInput("lead %d guard" % L, g.ctx, g.store, g.masks, g.features, units, times, g_keys, o.tol,
                           g.donor_mean, "router_lead_guard", o.c, schedule=sched)
        wfn = s.weights_fn(o.weights, o.pool) if o.weights is not None else None
        router = PR.PassRouter(s, inp, s.kind, weights=wfn, search_levels=True)
        routed = router.route([self.pinned], self.pin_point, y_surface=y, extra_trees_off=self._decline_links(),
                              level_tables=self._placebo_level_tables(L))
        link = self.pinned.link
        name = LA.arm_name(self.pinned)
        p_pre = ST.inverse(routed.predictions[name][:, 0], link, o.c, s.ub)
        off_pre = ST.inverse(routed.trees_off[link], link, o.c, s.ub)
        p_pin = clip_to_legal(p_pre, s.legal, False)[0]
        p_off = clip_to_legal(off_pre, s.legal, False)[0]
        mae_pin, mae_off = LD.surface_mae(y, p_pin), LD.surface_mae(y, p_off)
        la = LD.forecast_adoption(s.adoption, L, mae_pin, mae_off, self.longest)
        frame = pd.DataFrame({"unit": units, "group": [s.unit_group[u] for u in units.tolist()],
                              "time": times, "issue": times - L, "y": y,
                              M.ARM_PREFIX + name: p_pin, M.PRE_PREFIX + name: p_pre,
                              M.ARM_PREFIX + LA.arm_name(LA.trees_off_of(link)): p_off,
                              M.PRE_PREFIX + LA.arm_name(LA.trees_off_of(link)): off_pre})
        for Ld in self._decline_links():
            v = ST.inverse(routed.trees_off[Ld], Ld, o.c, s.ub)
            frame[M.ARM_PREFIX + LA.arm_name(LA.trees_off_of(Ld))] = clip_to_legal(v, s.legal, False)[0]
            frame[M.PRE_PREFIX + LA.arm_name(LA.trees_off_of(Ld))] = v
        _write_parquet_once(frame, self._lead_dir(L) / GUARD_PREDS)
        levels = dict(router.levels_found)
        rec = {"surface_rows": int(y.size), "score_steps": [first, fit_cut], "fit_cut": fit_cut,
               "guard_cut": guard_cut, "surface_sha256": str(surface.sha256), "pinned_mae": mae_pin,
               "own_trees_off_mae": mae_off, "passed": bool(la.guard_passed),
               "bank": ("the lead's guard-cut bank (owner ruling H2: L6 b at every lead)" if g.refit
                        else "the lead's fit-cut bank (A7.inner_cut_bank_refit off, L6 a)"),
               "bank_cut": int(g.bank.manifest.cut), "bank_max_label_time": bank_newest,
               "guard_rows_in_bank_label_window": in_window,
               "h2_check": ("asserted: every guard row is dated after the guard bank's newest label (%d < %d)"
                            % (bank_newest, int(times.min())) if g.refit else "not asserted (L6 a)"),
               "issue_row_absent_rows": 0,
               "nowcast_banks_held": nowcast_held,
               "banks_in_memory": len(nowcast_held) + (2 if g.refit else 1),
               "fallback_levels": {"rule": H5_RULE, "levels": levels},
               "router": _json(routed.records)}
        self._log("lead %d guard: %s MAE %.6g vs its trees-off %.6g on %d rows (bank cut %d, %d rows inside its label "
                  "window; fallback levels %s) -> %s"
                  % (L, name, mae_pin, mae_off, y.size, rec["bank_cut"], in_window,
                     {k: v["level"] for k, v in levels.items()} or "none (region kind)",
                     "PASSES: the pinned arm is adopted" if la.guard_passed else
                     "FAILS: the lead adopts the decline target (identity trees-off, D86)"))
        return la, rec, levels

    def _lock(self, la: Any, L: int) -> str:
        """vault.lock_lead_adoption; a resumed lead whose file is already locked (its test labels possibly
        open) is read back and must equal the adoption recomputed now (never re-decided)."""
        s = self.s
        folder = self.p.folder
        name = LEAD_ADOPTION_FILE % L
        lock = folder / (name + LOCK_SUFFIX)
        if lock.is_file():
            text = dumps(LD.lead_adoption_document(la, s.adoption_sha)) + "\n"
            if (folder / name).read_bytes() != text.encode("utf-8"):
                raise LadderRefusal("G-LOCK", "lead %d: the locked %s differs from the adoption recomputed on "
                                    "resume; a locked lead adoption never changes" % (L, name),
                                    fix="start a new run")
            sha = read_json(lock)["sha256"]
            self._log("lead %d: resumed from the locked %s (SHA-256 %s)" % (L, name, sha[:16]))
            return sha
        return lock_lead_adoption(la, s.adoption, s.adoption_sha, s.labels, folder)

    def _persistence_inputs(self, o: LeadObjects, t_keys: np.ndarray, t_units: np.ndarray,
                            t_steps: np.ndarray) -> Dict[str, Any]:
        """R31 at lead L, read BEFORE the lead's lock (D54 a): each test row's newest readable label
        (_newest_label_steps: timing.latest_label_step(t, L) moved back by R17's start_offset_steps, the step
        the history block's hist_last_1 reads) through the vault's as-of rows; phi per unit at the lead's
        fit cut on (y(t), y(t - gap)) pairs, gap = L + offset, with the U-2 season-key rule on that gap."""
        s = self.s
        L = o.lead
        offset = int(s.derived["R17"].value.start_offset_steps)
        label_step = _newest_label_steps(t_steps, L, offset)
        gaps = np.unique(np.asarray(t_steps, dtype=np.int64) - label_step)
        if gaps.size != 1 or int(gaps[0]) != L + offset or offset < 0:
            raise LadderRefusal("R17", "internal: lead %d with start offset %d reads labels %s steps back, not %d"
                                % (L, offset, gaps.tolist(), L + offset))
        gap = L + offset
        y_issue = s.labels.asof_rows(t_keys // self.n, label_step, 0, purpose="persistence_lead_%d" % L)
        same = M.shares_season_key(gap, int(s.season.steps_per_year))
        hist = {u: o.ctx_fit.unit_history(u, "damped_persistence_phi") for u in s.scored_units}
        phi = M.damped_persistence_phi(hist, gap, same)
        return {"y_issue": y_issue, "phi": phi, "same_season_key": same, "label_step": label_step,
                "start_offset_steps": offset, "gap": gap}

    def _route_arms(self, o: LeadObjects, t_keys: np.ndarray, t_units: np.ndarray, t_steps: np.ndarray,
                    tree_arms: Sequence[Any], what: str, purpose: str,
                    levels: Mapping[str, Any]) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray],
                                                        Dict[str, np.ndarray], np.ndarray, Any]:
        """The test rows routed at the pinned penalty through the lead's fit-cut objects: the tree arms, the
        pinned link's trees-off and the decline target's (identity trees-off), clipped (R28) and before the
        clip, and the identity normal of each row; R12's fallback at the given levels (the lead's own guard
        surface's, H5; the nowcast decision surface's for the lead-0 contract). Returns (arms, placebos,
        pre-clip, normal, the routed pass)."""
        s = self.s
        kinds = tuple(dict.fromkeys(LA.table_kind(a) for a in tree_arms))
        sched = s._pass_tables(o.store, o.pool, kinds, None, "ladder")
        inp = PR.PassInput(what, o.ctx_fit, o.store, o.masks, o.pool, t_units, t_steps, t_keys,
                           o.tol, o.donor_mean_fit, purpose, o.c, schedule=sched)
        wfn = s.weights_fn(o.weights, o.pool) if o.weights is not None else None
        routed = PR.PassRouter(s, inp, s.kind, weights=wfn, fallback_levels=levels).route(
            list(tree_arms), self.pin_point, extra_trees_off=self._decline_links())
        arms, placebos, pre = {}, {}, {}
        for a in tree_arms:
            nm = LA.arm_name(a)
            v = ST.inverse(routed.predictions[nm][:, 0], a.link, o.c, s.ub)
            (placebos if a.tool is LA.Tool.PLACEBO_CORRECTOR else arms)[nm] = clip_to_legal(v, s.legal, False)[0]
            pre[nm] = v
        for Lk in (self.pinned.link,) + self._decline_links():
            nm = LA.arm_name(LA.trees_off_of(Lk))
            v = ST.inverse(routed.trees_off[Lk], Lk, o.c, s.ub)
            arms[nm] = clip_to_legal(v, s.legal, False)[0]
            pre[nm] = v
        normal_id = np.asarray(routed.score_normal[Link.IDENTITY], dtype=np.float64)
        return arms, placebos, pre, normal_id, routed

    def _cut_year(self, o: LeadObjects) -> int:
        """The year of the lead's fit cut (the last-5-years normal's last year)."""
        return int(_years_of_steps(np.array([int(o.cuts.fit_cut)], dtype=np.int64), self.p.cadence)[0])

    def _common_baselines(self, o: LeadObjects, t_keys: np.ndarray, t_units: np.ndarray, t_steps: np.ndarray,
                          normal_id: np.ndarray) -> Dict[str, np.ndarray]:
        """The baselines every lead shares with the nowcast: predict-zero, guess-normal, the last-5-years normal
        at the lead's cut (R31, Q26), all clipped."""
        s = self.s
        return {"predict_zero": M.baseline_predict_zero(t_keys.size, s.legal),
                "guess_normal": M.baseline_guess_normal(normal_id, s.legal),
                "last5_normal": s._last5(t_units, t_steps, o.ctx_fit, self._cut_year(o))}

    def _rows_frame(self, L: int, t_units: np.ndarray, t_steps: np.ndarray, y: np.ndarray, normal_id: np.ndarray,
                    arms: Mapping[str, np.ndarray], placebos: Mapping[str, np.ndarray], pre: Mapping[str, np.ndarray],
                    baselines: Mapping[str, np.ndarray]) -> pd.DataFrame:
        """The saved rows of the lead (report.metrics.assemble_rows), issued at t - L."""
        s = self.s
        years = _years_of_steps(t_steps, self.p.cadence)
        return M.assemble_rows({"unit": t_units, "group": np.asarray([s.unit_group[u] for u in t_units.tolist()],
                                                                     dtype=object),
                                "time": t_steps, "year": years},
                               L, t_steps - L, y, normal_id, arms, placebos, pre, baselines, s.legal)

    def _save_issue_missing(self, L: int, units: np.ndarray, steps: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Owner ruling H4: the test rows lead L leaves out of scoring (their issue row is absent), saved once
        as ladder/lead_<L>/issue_missing_rows.parquet (keys, lead, issue, the label, the flag and the reason;
        only when a row is left out) and counted per unit and step; printed (one line, and each unit's count in
        run.log)."""
        s = self.s
        units = np.asarray(units, dtype=object)
        steps = np.asarray(steps, dtype=np.int64)
        n = int(units.size)
        rec: Dict[str, Any] = {"rule": H4_RULE, "rows_left_out": n, "units_with_rows_left_out": len(set(units.tolist())),
                               "by_unit": _counts(units), "by_step": _counts(steps), "rows_file": None}
        if not n:
            s.log("lead %d test pass: H4: every test row has its issue row at t - %d; none left out of scoring" % (L, L))
            return rec
        frame = pd.DataFrame({"unit": units, "group": np.asarray([s.unit_group[u] for u in units.tolist()], dtype=object),
                              "time": steps, "year": _years_of_steps(steps, self.p.cadence),
                              "lead": np.full(n, int(L), dtype=np.int64), "issue": steps - int(L),
                              "y": np.asarray(y, dtype=np.float64), ISSUE_FLAG: np.ones(n, dtype=bool),
                              "reason": np.full(n, ISSUE_REASON_ABSENT, dtype=object)})
        _write_parquet_once(frame, self._lead_dir(L) / ISSUE_MISSING_ROWS)
        rec["rows_file"] = "%s/lead_%d/%s" % (LADDER_DIR, L, ISSUE_MISSING_ROWS)
        s.log("lead %d test pass: H4 left %d test row(s) of %d unit(s) out of scoring (issue row at t - %d absent; "
              "never scored on NaN features); rows saved in %s" % (L, n, rec["units_with_rows_left_out"], L,
                                                                   rec["rows_file"]))
        for u, k in rec["by_unit"].items():
            s.log.file_only("lead %d test pass: H4 unit %s: %d test row(s) left out" % (L, u, k))
        return rec

    def _test(self, o: LeadObjects, la: Any, sha: str, pers: Mapping[str, Any],
              levels: Mapping[str, Any]) -> Dict[str, Any]:
        s = self.s
        L = o.lead
        t_keys, t_units, t_steps = self._test_rows()
        missing = np.asarray(o.issue_absent, dtype=bool)[t_keys]          # owner ruling H4
        keep = ~missing
        if not keep.any():
            raise LadderRefusal("H4", "lead %d: every one of the %d test rows has no issue row at t - %d: nothing is "
                                "left to score" % (L, t_keys.size, L))
        tl = s.labels.open_test_labels(sha, L)
        y_of = pd.Series(np.asarray(tl.y, dtype=np.float64),
                         index=pd.MultiIndex.from_arrays([np.asarray(tl.unit_ids, dtype=object),
                                                          np.asarray(tl.times, dtype=np.int64)]))
        y_all = y_of.reindex(pd.MultiIndex.from_arrays([t_units, t_steps])).to_numpy(dtype=np.float64)
        h4 = self._save_issue_missing(L, t_units[missing], t_steps[missing], y_all[missing])
        k_keys, k_units, k_steps, y = t_keys[keep], t_units[keep], t_steps[keep], y_all[keep]
        lead_arms = LA.lead_arms(self.pinned, L, self.longest)
        tree_arms = [a for a in lead_arms if a.tool is not LA.Tool.TREES_OFF]
        arms, placebos, pre, normal_id, routed = self._route_arms(o, k_keys, k_units, k_steps, tree_arms,
                                                                  "lead %d test pass" % L, "router_lead_test", levels)
        # the identity normal at the season key of each row's persisted label (its newest readable step), at
        # the lead's cut, for damped persistence
        tables = None
        if (routed.records.get("context_missing") or {}).get("rows_left_out"):
            # owner ruling G1: the pass's own normal, which left the same rows out (R15 on the kept fit rows)
            tables = routed.normal_tables[Link.IDENTITY]
        if tables is None:
            tables = ST.unit_normals(o.ctx_fit, s.scored_units, Link.IDENTITY, None, None,
                                     o.donor_mean_fit[Link.IDENTITY], s.season)
        label_step = np.asarray(pers["label_step"], dtype=np.int64)[keep]
        y_issue = np.asarray(pers["y_issue"], dtype=np.float64)[keep]
        normal_issue = ST._normals_on(tables, np.asarray(k_units, dtype=object), season_keys_of(label_step, s.season),
                                      Link.IDENTITY, int(o.ctx_fit.cut), None)
        phi_rows = np.array([pers["phi"][str(u)] for u in np.asarray(k_units, dtype=object).tolist()], dtype=np.float64)
        baselines = self._common_baselines(o, k_keys, k_units, k_steps, normal_id)
        baselines.update({"persistence": M.baseline_persistence(y_issue, s.legal),
                          "damped_persistence": M.baseline_damped_persistence(normal_id, normal_issue, y_issue,
                                                                              phi_rows, s.legal)})
        frame = self._rows_frame(L, k_units, k_steps, y, normal_id, arms, placebos, pre, baselines)
        path = self._lead_dir(L) / REC.TEST_PREDS
        if path.exists():
            if not M.read_rows(path).equals(frame):
                raise LadderRefusal("G-FINGERPRINT", "%s exists with other rows" % path, fix="start a new run")
        else:
            M.write_rows_once(frame, path)
        adopted = self.pinned if la.guard_passed else LA.trees_off_of(Link.IDENTITY)
        phis = np.array(list(pers["phi"].values()), dtype=np.float64)
        return {"rows": int(len(frame)), "test_rows": int(t_keys.size), "labelled_rows": int(np.isfinite(y).sum()),
                "issue_features_missing": h4,
                "arms": sorted(arms), "placebos": sorted(placebos),
                "adopted_column": M.ARM_PREFIX + LA.arm_name(adopted),
                "reference_column": M.ARM_PREFIX + LA.arm_name(LA.trees_off_of(adopted.link)),
                "persistence_rows_with_issue_label": int(np.isfinite(y_issue).sum()),
                "persistence_label": {"start_offset_steps": int(pers["start_offset_steps"]), "gap_steps": int(pers["gap"]),
                                      "rule": "the newest readable label: timing.latest_label_step(t, L) minus R17's "
                                              "start offset (the history block's hist_last_1 step); damped "
                                              "persistence pairs and the season-key rule at the same gap"},
                "same_season_key": bool(pers["same_season_key"]),
                "phi": {"median": float(np.median(phis)) if phis.size else None,
                        "min": float(phis.min()) if phis.size else None,
                        "max": float(phis.max()) if phis.size else None},
                "fallback_levels": "the lead's own guard surface's (owner ruling H5)",
                "router": _json(routed.records)}

    def run_lead(self, L: int) -> Dict[str, Any]:
        s = self.s
        t0 = time.time()
        with ExitStack() as stack:
            o = self._objects(L, stack)
            with ExitStack() as guard_stack:                      # the guard objects live only for the guard
                g = self._guard_objects(o, guard_stack)
                la, guard, levels = self._guard(o, g)
                guard_fits = g.record
                del g
            t_keys, t_units, t_steps = self._test_rows()
            pers = self._persistence_inputs(o, t_keys, t_units, t_steps)
            sha = self._lock(la, L)
            test = self._test(o, la, sha, pers, levels)
            rec = {"lead": L, "cuts": {"fit_cut": int(o.cuts.fit_cut), "guard_cut": int(o.cuts.guard_cut)},
                   "pinned": LA.arm_name(self.pinned),
                   "penalty": {"level": self.pin_point.level, "ratio": self.pin_point.ratio},
                   "adopted": LA.arm_name(la.adopted) if la.adopted is not None else None,
                   "declined_at_lead": la.adopted is None, "placebo_built": bool(la.placebo_built),
                   "adoption_file": LEAD_ADOPTION_FILE % L, "adoption_sha256": sha,
                   "guard": guard, "test": test, "fits": o.record, "guard_fits": guard_fits,
                   "longest_lead": self.longest,
                   "fallback_levels": {"rule": H5_RULE, "source": "the lead's own guard surface", "levels": levels},
                   "issue_features_missing": test["issue_features_missing"],
                   "context_missing": {"rule": ST.G1_RULE,
                                       "guard": _context_missing_summary(guard["router"]),
                                       "test": _context_missing_summary(test["router"])}}
            REC.write_once_or_same(self._lead_dir(L) / LEAD_RECORD, _json(rec))
            s.write_log_part(PHASE_LEAD % L)
            del o
        s.extra_contexts = []
        self._log("lead %d done in %.1f s: %s adopted" % (L, time.time() - t0, rec["adopted"] or "the decline target"))
        left_out = {k: (v["rows_left_out"] if v is not None else None)
                    for k, v in rec["context_missing"].items() if k != "rule"}
        return {"adopted": rec["adopted"], "guard_passed": not rec["declined_at_lead"], "rows": test["rows"],
                "issue_rows_left_out": int(test["issue_features_missing"]["rows_left_out"]),
                "guard_rows_in_bank_label_window": int(guard["guard_rows_in_bank_label_window"]),
                "context_rows_left_out": left_out, "seconds": round(time.time() - t0, 2)}

    # ------------------------------------------------------------------ the ladder table
    def table(self) -> Dict[str, Any]:
        """R34 / R35 / F57: every lead on the common rows and on all scored rows; each lead's verdict under the
        nowcast band (module docstring). H4's left-out rows are not in a lead's test_preds, so no score holds
        them."""
        s, p = self.s, self.p
        tol, floor = s.hit_tolerance()
        verdict = read_json(p.folder / REC.VERDICT_FILE)
        band = float(verdict["band"])
        frames = {0: M.read_rows(p.folder / REC.TEST_PREDS)}
        context_missing: Dict[str, Any] = {}
        issue_missing: Dict[str, Any] = {}
        guard_window: Dict[str, Any] = {}

        def partly_of(doc: Mapping[str, Any]) -> Dict[str, Any]:
            return {"test_rows_with_issue_row": int(doc["test_rows_with_issue_row"]),
                    "rows_with_a_nonfinite_tree_feature": int(doc["tree_features"]["rows"]),
                    "rows_with_a_nonfinite_context_value": int(doc["context"]["rows"])}
        partly = {"0": partly_of(read_json(self.folder / CONTRACT_FILE)["issue_features_partly_missing"])}
        info = {0: {"adopted_column": M.ARM_PREFIX + verdict["adopted"], "reference_column": verdict["reference"],
                    "declined": bool(verdict["declined"])}}
        for L in self.leads:
            frames[L] = M.read_rows(self._lead_dir(L) / REC.TEST_PREDS)
            lr = read_json(self._lead_dir(L) / LEAD_RECORD)
            info[L] = {"adopted_column": lr["test"]["adopted_column"], "reference_column": lr["test"]["reference_column"],
                       "declined": bool(lr["declined_at_lead"]),
                       "guard_passed": not lr["declined_at_lead"]}
            g1 = lr.get("context_missing") or {}
            context_missing[str(L)] = {k: (v["rows_left_out"] if v is not None else None)
                                       for k, v in g1.items() if k in ("guard", "test")}
            h4 = lr["issue_features_missing"]
            issue_missing[str(L)] = {"rows_left_out": int(h4["rows_left_out"]), "by_unit": dict(h4["by_unit"]),
                                     "rows_file": h4["rows_file"]}
            partly[str(L)] = partly_of(lr["fits"]["issue_features_partly_missing"])
            guard_window[str(L)] = {"bank_cut": lr["guard"]["bank_cut"],
                                    "guard_rows_in_bank_label_window": lr["guard"]["guard_rows_in_bank_label_window"]}

        def keys_of(f, col):
            ok = np.isfinite(f["y"].to_numpy(dtype=np.float64)) & np.isfinite(f[col].to_numpy(dtype=np.float64))
            return np.asarray(["%s\t%d" % (u, t) for u, t in zip(f["unit"].to_numpy(dtype=object)[ok].tolist(),
                                                               f["time"].to_numpy(dtype=np.int64)[ok].tolist())],
                              dtype=object)
        common = set(M.common_rows({L: keys_of(f, info[L]["adopted_column"]) for L, f in frames.items()}).tolist())
        lines, verdicts = [], {}
        wanted = ("baseline",)
        for L, f in sorted(frames.items()):
            k = np.asarray(["%s\t%d" % (u, t) for u, t in zip(f["unit"].to_numpy(dtype=object).tolist(),
                                                            f["time"].to_numpy(dtype=np.int64).tolist())], dtype=object)
            sub = f[np.isin(k, np.asarray(sorted(common), dtype=object))].reset_index(drop=True)
            for basis, frame in ((ROWS_BASIS_COMMON, sub), (ROWS_BASIS_ALL, f)):
                t = M.score_table(frame, (), tol, floor, p.kind)
                t = t[(t["line"] == M.LINE_POOLED) & (t["rows_basis"] == M.ROWS_BASIS_ALL)].copy()
                pinned_col = M.ARM_PREFIX + LA.arm_name(self.pinned)
                keep = t["column"].isin([info[L]["adopted_column"], info[L]["reference_column"], pinned_col]) | \
                    t["column_kind"].isin(wanted + ("placebo",))
                t = t[keep]
                t.insert(0, "ladder_rows", basis)
                t.insert(0, "lead", L)
                t.insert(2, "adopted", t["column"] == info[L]["adopted_column"])
                lines.append(t)
            tg = M.score_table(sub, ("group",), tol, floor, p.kind)
            ref_c, ad_c = info[L]["reference_column"], info[L]["adopted_column"]
            per_ref = M.metric_by_key(tg, ref_c, "mae", "group")
            per_ad = M.metric_by_key(tg, ad_c, "mae", "group")
            tp = M.score_table(sub, (), tol, floor, p.kind)

            def pooled(col):
                sel = tp[(tp["line"] == M.LINE_POOLED) & (tp["column"] == col) & (tp["rows_basis"] == M.ROWS_BASIS_ALL)]
                return float(sel["mae"].iloc[0])
            v = M.single_verdict(per_ref, per_ad, pooled(ref_c), pooled(ad_c), band, info[L]["declined"],
                                 M.REFERENCE_OWN_LINK_TREES_OFF)
            verdicts[L] = dict(M.verdict_record(v), adopted=ad_c, reference=ref_c,
                               guard_passed=info[L].get("guard_passed"), common_rows=int(len(sub)))
        table = pd.concat(lines, ignore_index=True)
        self.folder.mkdir(parents=True, exist_ok=True)
        REC.write_text_once_or_same(self.folder / LADDER_TABLE, REC.csv_text(table))
        rec = {"leads": list(self.leads), "longest_lead": self.longest, "band": band,
               "band_source": "the nowcast's band (F57: the nowcast band decides at every lead)",
               "pinned": LA.arm_name(self.pinned),
               "penalty": {"level": self.pin_point.level, "ratio": self.pin_point.ratio},
               "common_rows": len(common), "rows_basis": {"common": "rows with a label and an adopted prediction at "
                                                                    "every lead, lead 0 included (R34)",
                                                          "all": "every scored (saved) row of the lead; H4's left-out "
                                                                 "rows are in no score"},
               "verdicts": {str(L): v for L, v in sorted(verdicts.items())},
               "context_rows_left_out": {"rule": ST.G1_RULE, "by_lead": context_missing},
               "issue_rows_left_out": {"rule": H4_RULE, "by_lead": issue_missing},
               "issue_features_partly_missing": {"note": PARTLY_MISSING_NOTE, "by_lead": partly},
               "guard_bank_label_window": {"rule": H2_RULE, "by_lead": guard_window},
               "hit_tolerance": tol, "measurement_error_floor": floor, "rulings": RULINGS, "readings": READINGS}
        if p.draft.is_draft:
            rec = dict({"DRAFT": "DRAFT: %s -- never a headline number" % p.draft.stamp}, **rec)
        REC.write_once_or_same(self.folder / LADDER_RECORD, _json(rec))
        for L, v in sorted(verdicts.items()):
            self._log("ladder lead %d: %s (%s vs %s, contrast %.6g, common rows %d)"
                      % (L, v["tag"], v["adopted"], v["reference"], v["contrast"]["mean"] if isinstance(v.get("contrast"), dict) else float("nan"),
                         v["common_rows"]))
        return {"leads": list(self.leads), "common_rows": len(common),
                "verdicts": {str(L): v["tag"] for L, v in verdicts.items()}}

    # ------------------------------------------------------------------ the whole ladder
    def run(self, phases: Any) -> Dict[str, Any]:
        """Every ladder phase not done yet, in order, each marked done after its records are written."""
        s = self.s
        out: Dict[str, Any] = {}
        # nothing in the ladder reads the nowcast's inner-cut bank (its decision is locked and the test pass
        # wrote tables.json): released before the contract (RunState.release_bank)
        s.release_bank(P.BANK_INNER, "the nowcast's decision is locked and its test pass is done; the ladder "
                                     "never reads the inner-cut bank")
        if not phases.done(PHASE_CONTRACT):
            self.s.p._phase = PHASE_CONTRACT
            rec = self.contract()
            s.write_log_part(PHASE_CONTRACT)
            s.extra_contexts = []
            phases.mark_done(PHASE_CONTRACT, {"pinned": rec["pinned"], "rows": rec["rows"]})
        # the lead-0 contract was the fit-cut bank's last reader: released before the first lead, so a lead's
        # guard holds two banks (the lead's fit-cut bank and its H2 guard-cut bank), never four
        s.release_bank(P.BANK_FIT, "the lead-0 contract is done; leads of one step or more fit their own banks")
        for L in self.leads:
            name = PHASE_LEAD % L
            if phases.done(name):
                continue
            self.s.p._phase = name
            phases.mark_done(name, self.run_lead(L))
        if not phases.done(PHASE_TABLE):
            self.s.p._phase = PHASE_TABLE
            out = self.table()
            s.write_log_part(PHASE_TABLE)
            phases.mark_done(PHASE_TABLE, out)
        return out


__all__ = ["Ladder", "LadderRefusal", "LeadObjects", "GuardObjects", "lead_plan", "phase_names", "log_parts",
           "LADDER_DIR", "PHASE_CONTRACT", "PHASE_LEAD", "PHASE_TABLE", "READINGS", "RULINGS", "H2_RULE", "H3_RULE",
           "H4_RULE", "H5_RULE", "I1_RULE", "ISSUE_MISSING_ROWS", "ISSUE_FLAG", "ISSUE_REASON_ABSENT"]
