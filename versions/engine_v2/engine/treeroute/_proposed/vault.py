"""PROPOSED signatures: treeroute/labels/vault.py (plan 4.2). SCIENCE: owner signature AND owner review
of the body -- it is the test-label lock.

LabelView is the ONLY object that holds target labels (G-LOCK by structure): the target table's y
goes into its constructor and nowhere else. The dense grid holds keys only, and the feature source
holds no label, so no science signature can reach a label except through a method below:
    validity(first, last)     label validity only, never a value (R3, R12, R18 counts)
    donor_labels(...)         label-only donor view at or before a cut, for plan-time rules
    asof(cut)                 every label at or before a cut (FitContext is the only caller)
    asof_rows(...)            per-row as-of reads for history, persistence and target-derived checks
    open_test_labels(...)     test-window labels, per scoring pass, against that pass's locked adoption
Test labels open per SCORING PASS: the nowcast test pass after lock_adoption, and each forecast
lead's test pass after lock_lead_adoption for that lead (A6 default a: as-of view + adoption lock).
The run folder is optional until a lock is used, so `plan` and `check --deep` can build a view.
"""
# Provenance for the module: pm25_forecast.py:601-606 (each rung's adoption on disk before any test row
# is routed); plan 5 G-LOCK; plan 9.2 A6.
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from .common import Adoption, CutKind, DenseGrid, LeadAdoption, SplitSets, TargetTable


@dataclass(frozen=True)
class LabelSlice:
    """Labels visible at one cut: rows (unit, step or day) and y, with the cut recorded."""
    cut: int
    unit_ids: np.ndarray
    times: np.ndarray
    y: np.ndarray


@dataclass(frozen=True)
class DonorLabels:
    """Label-only donor view: donor-group rows with valid labels at or before one cut whose own label
    window has ended by then (the same rule as FitContext.donor_rows), with NO features and no run
    folder. Constructed ONLY by LabelView.donor_labels.

    It exists so plan-time rules can read donor y before any feature pool, FitContext or run folder
    exists. G-DONOR accepts it wherever only donor y is read at plan time: the R18 event rate, R19
    bag sizes, R22 links, the R30 row set, and the G-SUPPORT and G-RANGE donor checks. At the nowcast
    fit cut with the picked units its row_key_hash must equal FitContext.donor_rows' at the same cut
    (the run refuses otherwise, as it refuses a derived.json that differs from plan's)."""
    groups: Tuple[str, ...]
    cut: int
    cut_kind: CutKind
    lead: int
    unit_scope: str                     # 'picked' or 'all_donor_units'
    unit_ids: np.ndarray
    times: np.ndarray
    group_of_row: np.ndarray
    y: np.ndarray
    row_key_hash: str


@dataclass(frozen=True)
class TestLabels:
    """Test-window labels of one scoring pass, released only by LabelView.open_test_labels."""
    lead: int                           # 0 = the nowcast test pass
    adoption_sha256: str
    unit_ids: np.ndarray
    times: np.ndarray
    y: np.ndarray


class LabelView:
    """The only object that hands out labels.

    Rule: A6, G-LOCK, G-FITCUT.  Needed: Tue 29 Sep (derive v1 reads validity and donor labels); lock Sat 3 Oct.
    """

    # Provenance: plan 4.2 labels/vault.py; plan 2.1 R11 (labels at or before the cut whose own window
    # has ended); plan 1.2 target table (NaN y = a label the ingest declared invalid).
    def __init__(self, grid: Optional[DenseGrid], target: TargetTable, times: np.ndarray,
                 test_first_time: int, label_window_last_day: np.ndarray,
                 run_folder: Optional[Path]) -> None:
        """Take the target table's labels into the vault, aligned to the dense grid (or kept per
        visit for events).

        Rule: A6, G-LOCK.  Needed: Tue 29 Sep (derive v1).

        Contract (plan 4.2, 5 G-LOCK, 9.2 A6):
            The ONLY consumer of TargetTable.y. Labels are aligned to the keys-only grid (grids) or
            kept one per visit (events, grid None, M8). Every later read is recorded (who, cut, row
            count, max label time) for the fitctx_log and the manifest. With run_folder None the
            view serves validity, donor labels and as-of reads (plan, check --deep) but can never
            lock an adoption or open test labels.
        Inputs:
            grid: the keys-only dense grid, or None for events.
            target: the target table as read.
            times: integer step (grids) or Day (events) per target row (io_science.step_index).
            test_first_time: the first step (or day) of the test window (R5).
            label_window_last_day: last day of each row's own label window (for R11's window rule).
            run_folder: the run folder that will hold the adoption files, or None.
        Returns:
            None.
        Refuses:
            - a target row whose (unit, step) is not on the grid, or duplicate (unit, time).
            - a run folder that already holds opened test labels from another adoption.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 2.1 R3 ("reads only whether rows exist, never their values"), R12 (valid rows
    # only), R18 (candidates = units with at least one valid row at or before the train end).
    def validity(self, first_time: int, last_time: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Label validity (valid or NaN) of every row inside [first_time, last_time]; never a value.

        Rule: R3, R12, R18, G-LOCK.  Needed: Tue 29 Sep (derive v1).

        Contract (plan 2.1 R3, R12, R18):
            Returns keys and a validity flag only. The window may span the test window only for R3,
            which reads whether valid rows exist there (see the R3 decision); R12 and R18 pass windows
            ending at the inner-fit end or the donor train end. The read is logged.
        Inputs:
            first_time, last_time: the window, inclusive (steps or days).
        Returns:
            (unit ids, times, is_valid) per row in the window.
        Refuses:
            - first_time > last_time.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 2.1 R11 and 5 G-DONOR (donor groups, dated at or before the cut); plan 4.1 step 2
    # (derive runs before any feature pool or FitContext exists).
    def donor_labels(self, split: SplitSets, cut: int, cut_kind: CutKind, lead: int,
                     unit_ids: Optional[Tuple[str, ...]], purpose: str) -> DonorLabels:
        """Label-only donor rows at or before a cut, for plan-time rules.

        Rule: R11, G-DONOR; R18, R19, R22, R30.  Needed: Tue 29 Sep (derive v1).

        Contract (plan 2.1 R11, 5 G-DONOR):
            Donor groups only (sorted), rows at or before the cut whose own label window has ended
            (timing.label_usable), valid labels only. unit_ids restricts to those donor units (the
            R18 picks, scope 'picked'); None takes every donor-group unit (scope 'all_donor_units',
            used only where the pick size itself depends on the value, the R18 event rate). The
            hand-out is logged; derive records its row_key_hash in derived.json.
        Inputs:
            split: the split sets.
            cut: the cut (from derive_r11, never computed here).
            cut_kind: FIT or GUARD.
            lead: the lead the cut belongs to (0 = nowcast).
            unit_ids: donor units to keep, or None.
            purpose: 'event_rate', 'bank_plan', 'links', 'missing_shares', 'support', 'range'.
        Returns:
            DonorLabels.
        Refuses:
            - a unit that belongs to a test group or to no donor group.
            - a cut at or after test_first_time.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 4.2 (LabelView.asof(cut)); plan 2.1 R11.
    def asof(self, cut: int) -> LabelSlice:
        """Every label dated at or before the cut whose own window has ended by then.

        Rule: R11, G-FITCUT.  Needed: Wed 30 Sep (FitContext reads it); vault complete Sat 3 Oct.

        Contract (plan 2.1 R11, 4.2):
            FitContext is the only caller for fitted objects. No fitted object is ever cut inside the
            test window (every fit and guard cut is at or before the donor train end), so a cut
            inside it is always refused.
        Inputs:
            cut: a step (grids) or a Day (events).
        Returns:
            LabelSlice.
        Refuses:
            - a cut at or after test_first_time.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 5 G-LOCK ("history, persistence and pools read labels through the as-of view");
    # plan 2.3 R17; plan 4.1 steps 4 and 8.
    def asof_rows(self, unit_rows: np.ndarray, newest_readable: np.ndarray, k_back: int) -> np.ndarray:
        """Per-row as-of reads: for each row, the same unit's label exactly k_back steps before its
        newest readable step, or NaN.

        Rule: R17, R31, G-LOCK, G-CALENDAR.  Needed: Sat 3 Oct (vault); used Mon 5 Oct (G-HIST) and Thu 8 Oct (history).

        Contract (plan 5 G-LOCK, G-CALENDAR):
            Serves the history block, persistence baselines, neighbour pools and the recompute of
            target-derived columns. Every read is in the same unit and dated at or before the row's
            newest readable step (timing.latest_label_step, or the row's step - 1 for a
            target-derived column), through the dense-grid predecessor lookup.
        Inputs:
            unit_rows: grid row (unit) per request.
            newest_readable: newest readable step per request.
            k_back: 0 for the newest readable label itself, k for k steps before it.
        Returns:
            float64 labels, NaN where absent or invalid.
        Refuses:
            - k_back < 0.
        OWNER DECISION: test rows' history and persistence need test-window labels BEFORE each
            row's issue step, and the plan builds history (4.1 step 4) before the adoption hash
            (step 8). Option (a): asof_rows serves them before the hash, because each is known at
            its row's issue time and decide() never sees test rows. Option (b): test rows' history
            and persistence are built only after that pass's lock.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    # Provenance: plan 4.1 steps 8-9 and 11 (adoption hashed before the test labels open; the ladder per
    # lead); plan 5 G-LOCK; pm25_forecast.py:601-606.
    def open_test_labels(self, adoption_sha256: str, lead: int) -> TestLabels:
        """Release the test-window labels for ONE scoring pass, only against the hash of the adoption
        that pass uses.

        Rule: R27, R29, G-LOCK.  Needed: Sat 3 Oct (nowcast pass); per lead Fri 9 Oct.

        Contract (plan 2.4 R27, R29, 4.1 steps 8-9 and 11, 5 G-LOCK):
            One call per scoring pass: lead 0 is the nowcast test pass (lock_adoption), lead L is
            that lead's test pass (lock_lead_adoption). It opens only if that pass's adoption file
            exists in the run folder, its SHA-256 equals the given hash and the hash the lock
            recorded, and it was written before this call. The opening is logged. Once a pass is
            open its adoption can never change (a second lock for that pass is refused); a later
            pass needs its own lock first.
        Inputs:
            adoption_sha256: the hash returned by the pass's lock.
            lead: the pass (0 = nowcast).
        Returns:
            TestLabels.
        Refuses:
            - no run folder; no locked adoption for that pass; a hash mismatch.
            - a lead pass whose nowcast adoption was never locked.
        """
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.4 R27 ("adoption.json is hashed before test labels open"); plan 7.1 (written
# once, atomically: temp file, fsync, rename -- the writer is boilerplate, pm25_forecast.py:347-356).
def lock_adoption(adoption: Adoption, labels: LabelView, run_folder: Path) -> str:
    """Write the nowcast's adoption.json once and return its SHA-256; after this the nowcast adoption
    cannot change.

    Rule: R27, G-LOCK.  Needed: Sat 3 Oct (vault + adoption lock).

    Contract (plan 2.4 R27, 7.1):
        The adoption (arm, link, tool, weighting, penalty, or 'declined', with the best tree arm
        and its penalty) is written atomically and hashed. The hash goes into the manifest before
        any test label is opened. Type 3 runs only after this hash.
    Inputs:
        adoption: the layer's decision (layer.select_adoption).
        labels: the vault, built with this run folder.
        run_folder: the run folder.
    Returns:
        the SHA-256 hex digest.
    Refuses:
        - any test labels already opened in this run.
        - an existing adoption.json with different content.
        - a vault built without this run folder.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.4 R29 (the N2 guard at each lead on the inner guard's cut; a pinned arm);
# pm25_forecast.py:601-606 (each rung's adoption written to disk before any test row is routed).
def lock_lead_adoption(lead_adoption: LeadAdoption, nowcast: Adoption, nowcast_sha256: str,
                       labels: LabelView, run_folder: Path) -> str:
    """Write one forecast lead's adoption file once and return its SHA-256, before any of that lead's
    test rows is scored.

    Rule: R29, R27 (N2), G-LOCK.  Needed: Fri 9 Oct (forecast ladder).

    Contract (plan 2.4 R29, 4.1 step 11, 5 G-LOCK):
        Each lead makes its own guard decision (adopt the pinned arm or decline), so each lead has
        its own lock. The file (lead, pinned arm, penalty, guard result, adopted or declined, placebo
        flag) is written atomically and hashed; the hash goes into the manifest; only then may
        open_test_labels(hash, lead) release that lead's test labels. The pin must equal R29's pin:
        the nowcast's adopted link, tool, weighting and penalty, or its best tree arm and that
        arm's penalty when the nowcast declined.
    Inputs:
        lead_adoption: layer.forecast_adoption for this lead.
        nowcast: the nowcast Adoption.
        nowcast_sha256: the hash lock_adoption returned (it must be the recorded one).
        labels: the vault, built with this run folder.
        run_folder: the run folder.
    Returns:
        the SHA-256 hex digest.
    Refuses:
        - lead 0 (the nowcast uses lock_adoption).
        - a nowcast hash that lock_adoption did not record.
        - a pin that differs from R29's pin.
        - this lead's test labels already open; an existing file for this lead with different content.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")
