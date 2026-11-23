"""PROPOSED signatures: treeroute/derive/ (plan 4.2, Section 2). SCIENCE: owner signatures, agent bodies.

Each rule is a pure function. It returns a Derived value: the value, the inputs it read (with
hashes) and its margin to any threshold, written to derived.json. A value within 20% of a threshold
is flagged 'borderline'; the flag is reported, never a choice. Every constant sits in
engine_constants.py with its origin (C1-C15). No named fixtures: acceptance values live in each
package's expected_derived.json, never here.

RULE_HOME below maps every rule R1-R36 to the function that computes it. Rules that need fitted
objects or run-time data live in the module the plan assigns them to; derive_all records their
values in derived.json (or adoption.json for run-time selections).

Plan time has no feature pool, no FitContext and no run folder. Rules that read labels get them from
the vault only: label validity (LabelView.validity) or the label-only donor view (vault.DonorLabels,
from LabelView.donor_labels, built with the same cut rule as FitContext.donor_rows).
"""
# Provenance for the module: generalises derive_tier1 (adaptation.py:330-352) MINUS its 100-row
# threshold (:346), {1, 100} upper-bound guess (:339-350), hurdle rule (:374) and swallowed
# exception (:378); and pm25_adaptation.py:122-177 (the old CLI constants).
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Protocol, Sequence, Tuple

import numpy as np

from .common import (Cadence, CalendarPart, ColumnFacts, CutKind, CutPair, Derived, HistorySpec, Lag,
                     LeadPlan, Link, PackageView, RouterDesign, RouterKind, SeasonKeySpec,
                     SplitSets, SurfaceKind, TargetFacts, TargetTable, TestWindowPlan, Windows, Window)
from .vault import DonorLabels


@dataclass(frozen=True)
class MissingShares:
    """R30 inputs, measured by the boilerplate column reader over ONE declared donor row set (a
    DonorLabels), so the rows behind every share are traceable."""
    donor_row_key_hash: str             # DonorLabels.row_key_hash of the rows measured
    donor_unit_scope: str               # DonorLabels.unit_scope
    donor_training_missing_share: Mapping[str, float]
    donor_training_zero_share: Mapping[str, float]
    test_year_missing_share: Mapping[Tuple[str, int], float]


class MissingShareReader(Protocol):
    """Boilerplate column reader (io stores) that measures the R30 shares; listed so derive_all can
    name it. It reads driver columns only, never a label."""

    def measure(self, donor: DonorLabels, lags: Mapping[str, Lag], test_years: Tuple[int, ...]) -> MissingShares:
        """Missing and real-zero shares of every entering column on the donor rows (after the R8
        lags, before the R30 0-fill), and the pooled missing share per test year."""
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

RULE_HOME: Mapping[str, str] = {
    "R1": "derive_rules.derive_r01_cadence",
    "R2": "derive_rules.derive_r02_season_key",
    "R3": "derive_rules.derive_r03_coverage_end",
    "R4": "derive_rules.derive_r04_first_year",
    "R5": "derive_rules.derive_r05_test_window",
    "R6": "derive_rules.derive_r06_train_end",
    "R7": "derive_rules.derive_r07_inner_windows",
    "R8": "derive_rules.derive_r08_feature_lags",          # per column: timing.compute_lag
    "R9": "derive_rules.derive_r09_freeze_epochs",         # per column: timing.freeze_epoch
    "R10": "derive_rules.derive_r10_leads",
    "R11": "derive_rules.derive_r11_cuts",                 # per lead: timing.cuts_for_leads
    "R12": "derive_rules.derive_r12_router_kind",          # fallback router: route_kinds
    "R13": "derive_rules.derive_r13_decision_surface",     # folds: split.make_donor_folds
    "R14": "derive_rules.derive_r14_router_design",        # grid and cap: route_kinds
    "R15": "route_kinds.unit_season_normal",
    "R16": "route_kinds.trees_off_with_normal",
    "R17": "derive_rules.derive_r17_history_spec",         # block: io_science.history_block
    "R18": "derive_rules.derive_r18_unit_count",           # picks: split.pick_units
    "R19": "derive_rules.derive_r19_bank_plan",            # seeds and fits: bank_recipe
    "R20": "derive_rules.derive_r20_batching",
    "R21": "derive_rules.derive_r21_smoke_plan",
    "R22": "derive_rules.derive_r22_links",                # transforms: layer.link_forward
    "R23": "layer.c_for_cut",
    "R24": "layer.candidate_arms",
    "R25": "weights_gls.weight_model_for_cut",
    "R26": "layer.penalty_search",
    "R27": "layer.select_adoption",
    "R28": "layer.clip_to_legal",
    "R29": "layer.forecast_adoption",
    "R30": "derive_rules.derive_r30_missing_flags",
    "R31": "metrics.baseline_persistence",                 # and the other metrics.baseline_*
    "R32": "metrics.hit_tolerance",
    "R33": "metrics.top10_detection",
    "R34": "metrics.single_verdict",                       # and metrics.score_table
    "R35": "metrics.equivalence_band",
    "R36": "metrics.guard_tolerance",
}


# Provenance: plan Section 2 preamble ("A value within 20% of a threshold is flagged 'borderline'").
def borderline_flags(value: float, thresholds: Mapping[str, float]) -> Tuple[Mapping[str, float], Tuple[str, ...]]:
    """Margin of a derived value to each of its thresholds, and a 'borderline' flag within 20%.

    Rule: Section 2 (all rules).  Needed: Tue 29 Sep (derive v1).

    Contract (plan Section 2):
        For every threshold the rule compares against, record the margin. A value within 20% of a
        threshold is flagged 'borderline'. The flag is reported only, never a choice.
    Inputs:
        value: the number the rule compared.
        thresholds: {threshold name: threshold value}, from engine constants.
    Returns:
        ({name: margin}, flags) where flags holds 'borderline:<name>' entries.
    Refuses:
        - a non-finite value.
    OWNER DECISION: "within 20%" is proposed as |value - threshold| <= 0.2 x |threshold|, i.e.
        relative to the threshold; a zero threshold then uses the absolute margin only.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R1; composite-of-year clause (8- and 16-day composites restart 1 January).
def derive_r01_cadence(unit_ids: np.ndarray, time_values: Mapping[str, np.ndarray],
                       time_facts: Mapping[str, CalendarPart]) -> Derived[Cadence]:
    """The target's cadence and step: one regular step (grid), a composite-of-year grid, or events.

    Rule: R1.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R1):
        The target's key_time facts say which calendar part each time column holds. If all units
        share one regular step, the data are a grid with that step (1 month, 1 year, or N days). A
        (year, composite-of-year) calendar is a grid too: composites restart every 1 January, so the
        last one of a year is shorter (5-6 days); its spacing is checked WITHIN each year. If dates
        are irregular per unit, the data are events (single or repeat visits). The spacing is
        checked on EVERY unit, never a sample.
    Inputs:
        unit_ids: unit id per target row.
        time_values: {time column: values per target row}.
        time_facts: {time column: its calendar part} from the package catalog.
    Returns:
        Derived[Cadence]; inputs record the observed spacings and how many units had each.
    Refuses:
        - a time column without a calendar-part fact, or a fact without a column.
        - a composite-of-year calendar whose spacing breaks inside a year.
        - an empty target table.
    OWNER DECISION: units that are each regular but with DIFFERENT steps fit neither outcome;
        propose a refusal (plan names only 'all share one step' -> grid and 'irregular' -> events).
    OWNER DECISION: the calendar-part list has no 'composite number'; propose the composite number
        comes from day_of_year and the composite length from the observed within-year spacing.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R2; U-2 (annual data: one constant class).
def derive_r02_season_key(cadence: Cadence, observed_composites_per_year: Optional[int]) -> Derived[SeasonKeySpec]:
    """The season key (a step's position within its year) and the number of steps per year.

    Rule: R2.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R2):
        Month-of-year for monthly data; composite number for N-day composite steps; the step's
        position within its year for other regular steps. Steps per year = the composites per year
        in the data, or 365.25 / N rounded when there is no year reset. Annual data get ONE constant
        class, so target and predecessor always share it (U-2). Events: the month of the event date
        (steps per year is None). The key serves the normal (R15) and persistence (R31).
    Inputs:
        cadence: R1 outcome.
        observed_composites_per_year: composites per year seen in the data (composite grids only).
    Returns:
        Derived[SeasonKeySpec].
    Refuses:
        - STATIC or EPOCH cadence for a target.
    OWNER DECISION: "365.25 / N rounded" -- propose round half up, as R10 rounds.
    OWNER DECISION: the season key of a regular N-day step WITHOUT a year reset is not defined by
        the plan (steps drift across years); a definition is needed before such data can run.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R3; convention C3 (robust to a few late groups).
def derive_r03_coverage_end(rows_per_group_year: Mapping[Tuple[str, int], int],
                            test_groups: Tuple[str, ...], is_events: bool) -> Derived[int]:
    """Y_end: the last year in which at least half the test groups have at least 90% of their usual
    yearly rows.

    Rule: R3.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R3, C3):
        Grid: the last year in which at least half the test groups have at least 90% of their own
        median yearly row count. Events: the last year with any test rows. It reads only whether
        rows exist, never their values.
    Inputs:
        rows_per_group_year: {(group, year): row count} over the test groups.
        test_groups: the sorted test-group set.
        is_events: True when R1 gave events.
    Returns:
        Derived[int] (Y_end); margins record, for the chosen year, the share of qualifying groups.
    Refuses:
        - no year qualifies.
        - a test group with no rows at all.
    OWNER DECISION: on a complete census every unit x step is a row (NaN labels included), so
        counting census rows gives the table's last year; propose counting rows with a VALID
        (non-NaN) label, which reads NaN-ness only -- confirm this is within "never their values".
    OWNER DECISION: "their own median yearly count" -- propose the median over every calendar year
        from the group's first to its last row, zero-row years included.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R4; C4; pm25_architecture.py:64-72 (the first data year read only as a lag
# source).
def derive_r04_first_year(first_data_year: int, lags: Mapping[str, Lag]) -> Derived[int]:
    """Y0: the first data year plus the largest computed lag, rounded up to whole years.

    Rule: R4.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R4, C4):
        Only lag sources count: the earlier year is read only to feed lagged values. A column that
        starts late does not move Y0; it falls under R30. The history block does not count (R4
        counts R8 lags; the block's means use available steps only).
    Inputs:
        first_data_year: the first year of the target table.
        lags: R8 lags of every kept column.
    Returns:
        Derived[int] (Y0).
    Refuses:
        - an empty lag map when kept columns exist (R8 must run first).
    OWNER DECISION: "first data year" is proposed as the first year of the target table (the
        shipped reading, where that year is read only as the lag source).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R5; C1; plan 3.3 (the five packages never reach the ladder).
def derive_r05_test_window(y0: int, y_end: int) -> Derived[TestWindowPlan]:
    """The test window: the last 4 years up to Y_end, with the short-record ladder.

    Rule: R5.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R5, C1, C2):
        Normally 4 test years and 3 inner-score years, which need 8 years from Y0 to Y_end
        (4 + 3 + 1 inner fit). The ladder is used only when fewer than 8 years exist: first the
        inner score window drops to 2 years (needs 7); if still short, the test window drops to 3
        years (needs 6); under 6 years the package is refused. Each ladder step is flagged
        'short record'.
    Inputs:
        y0: R4 first year.
        y_end: R3 coverage end.
    Returns:
        Derived[TestWindowPlan] (test years, inner-score length, ladder steps taken).
    Refuses:
        - fewer than 6 years from Y0 to Y_end (3 test + 2 inner score + 1 inner fit).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R6.
def derive_r06_train_end(test_years: Tuple[int, ...]) -> Derived[int]:
    """Donor train end: the year before the test window.

    Rule: R6.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R6):
        Every donor label and every router row is at or before this year (enforced by FitContext).
    Inputs:
        test_years: R5 test years (consecutive).
    Returns:
        Derived[int].
    Refuses:
        - test years that are not consecutive.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R7; C2.
def derive_r07_inner_windows(y0: int, y_end: int, plan: TestWindowPlan, train_end: int) -> Derived[Windows]:
    """Inner windows: score = the years before the test window; fit = Y0 to the year before score.

    Rule: R7.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R7):
        Score = the 3 years before the test window (2 under the short-record ladder). Fit = Y0 to
        the year before the score window.
    Inputs:
        y0, y_end: R4 and R3.
        plan: R5 outcome (inner-score length).
        train_end: R6.
    Returns:
        Derived[Windows] with every window filled.
    Refuses:
        - an inner-fit window shorter than 1 year.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R8 (see timing.compute_lag for the ruled cases).
def derive_r08_feature_lags(columns: Mapping[str, ColumnFacts], target: TargetFacts,
                            target_cadence: Cadence) -> Derived[Mapping[str, Lag]]:
    """One computed lag for every kept, time-varying non-key column.

    Rule: R8.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R8, 5 G-LAG):
        Calls timing.compute_lag for every column whose verdict lets it enter a run. Nothing types
        a lag. derived.json records each lag with the facts it read (stamp, window, cadence,
        co_measured, computed_from) and the reason when the 1-step floor applied.
    Inputs:
        columns: facts of the columns that enter the run (after verdicts).
        target: target facts.
        target_cadence: R1.
    Returns:
        Derived[{column: Lag}].
    Refuses:
        - any column compute_lag refuses (unknown window without a signed bound).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R9.
def derive_r09_freeze_epochs(freeze_epochs_available: Mapping[str, Sequence[int]],
                             cuts: Mapping[int, CutPair]) -> Derived[Mapping[Tuple[str, int, CutKind], int]]:
    """The frozen epoch of every 'freeze' column at both cuts of every lead.

    Rule: R9.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R9):
        Calls timing.freeze_epoch per (column, lead, cut kind): at the lead's FIT cut, and at its
        GUARD cut. Under timing.freeze_epoch's decision the guard entry is the epoch at or before
        the guard's own cut; under the alternative it repeats the FIT entry. Both keys are always
        written, so io_science.apply_freezes reads the entry of the cut in use.
    Inputs:
        freeze_epochs_available: {column: its content epochs as Day ordinals}.
        cuts: R11 cuts per lead.
    Returns:
        Derived[{(column, lead, cut kind): epoch Day}].
    Refuses:
        - any column with no epoch at or before a cut.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R10; C6; Q41 a (1/3/6/12 months); plan 3.2 (the annual case: 6 and 12
# months merge into 1 year, 1 and 3 months round to 0).
def derive_r10_leads(season: SeasonKeySpec, is_events: bool) -> Derived[LeadPlan]:
    """Leads: 1, 3, 6 and 12 months in the data's own step, rounded half up, merged when equal.

    Rule: R10.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R10, C6):
        Grids: steps = months x steps_per_year / (months in a year), rounded half up. The "under one
        step" test comes AFTER rounding: a lead that rounds to 0 steps is not run and is reported
        "not supplied". Leads that round to the same step are merged, and plan prints the merge.
        Events have no step: a lead is round(months x 365.25 / months in a year) days, rounded half
        up (30, 91, 183, 365), and the issue date is the event date minus the lead. Lead 0 always
        runs as the contract. In-season sub-step leads are reserved for M8.
    Inputs:
        season: R2 outcome (steps per year).
        is_events: True when R1 gave events.
    Returns:
        Derived[LeadPlan].
    Refuses:
        - a grid with steps_per_year missing.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R11 (see timing.fit_cut_step, timing.guard_cut_step).
def derive_r11_cuts(windows: Windows, leads: LeadPlan, target_cadence: Cadence) -> Derived[Mapping[int, CutPair]]:
    """Both cuts for every lead, lead 0 included, written to derived.json.

    Rule: R11.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R11):
        Calls timing.cuts_for_leads. FitContext reads only these cuts; no module recomputes one.
    Inputs:
        windows, leads, target_cadence: R3-R7, R10, R1.
    Returns:
        Derived[{lead: CutPair}].
    Refuses:
        - whatever timing.cuts_for_leads refuses.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R12 (valid rows only; test-window rows never read).
def count_valid_rows_per_unit(unit_ids: np.ndarray, steps: np.ndarray, label_is_valid: np.ndarray,
                              first_step: int, last_step: int) -> Mapping[str, int]:
    """Number of VALID target rows per unit inside [first_step, last_step].

    Rule: R12, R18.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R12, R18):
        NaN labels do not count. Rows outside the window are never read (the caller passes Y0 to
        the inner-fit end, so test-window rows are never read). For events the count is the unit's
        valid visits in the window.
    Inputs:
        unit_ids, steps, label_is_valid: LabelView.validity over the window (steps are Day
            ordinals for events); validity only, never a value.
        first_step, last_step: the window, inclusive.
    Returns:
        {unit id: valid row count} (units with 0 included).
    Refuses:
        - mismatched array lengths.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R12 ("The share of units whose whole fit history is one value is printed").
def constant_history_share(unit_ids: np.ndarray, y_fit_rows: np.ndarray) -> float:
    """Share of units whose whole fit history is one value (report only).

    Rule: R12.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R12):
        Printed in plan and in reports; it never changes a setting.
    Inputs:
        unit_ids: unit per fit row of the test units (valid labels only, at or before the
            inner-fit end), from LabelView.asof(inner-fit end).
        y_fit_rows: the labels of those rows (same source).
    Returns:
        the share in [0, 1].
    Refuses:
        - no rows.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R12; C5; MIN_HIST = 24 at pm25_adaptation.py:143. Replaces the donor-wide mean
# fallback at pm25_adaptation.py:342-344 (route_percell's gmean).
def derive_r12_router_kind(valid_rows_per_test_unit: Mapping[str, int]) -> Derived[RouterKind]:
    """Router kind by one rule: per-unit if h >= 24, region if 2 <= h < 24, neighbour if h < 2.

    Rule: R12.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R12, C5, C10):
        h = the median number of VALID target rows per test unit from Y0 to the inner-fit end.
        PER-UNIT if h >= 24 (MIN_HIST); REGION if 2 <= h < 24; NEIGHBOUR if h < 2. In a per-unit
        dataset a unit with fewer than 24 valid rows uses its group's region router (see
        route_kinds.fallback_units); those units are counted and flagged above 5% of units.
        Margins record h against 24 and 2 (borderline within 20%).
    Inputs:
        valid_rows_per_test_unit: from count_valid_rows_per_unit over Y0..inner-fit end.
    Returns:
        Derived[RouterKind]; inputs record h, the fallback count and share.
    Refuses:
        - an empty unit map.
    OWNER DECISION: which test units enter h -- propose ALL candidate test units (R18 candidates)
        before the stride pick, because the pick size itself depends on the router kind.
    OWNER DECISION: median of an even count -- propose the midpoint (numpy median), so h may be
        a half-integer.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R13; C8 (a shipped decision used 5 folds).
def derive_r13_decision_surface(kind: RouterKind, donor_groups: Tuple[str, ...]) -> Derived[Tuple[SurfaceKind, Tuple[Tuple[str, ...], ...]]]:
    """Decision surface: the inner window (per-unit, region) or K donor folds (neighbour).

    Rule: R13.  Needed: Tue 29 Sep (derive v1); folds used only in M8 (neighbour track).

    Contract (plan 2.1 R13, C8):
        Per-unit and region: the inner window. Neighbour: K = min(5, donor groups) folds,
        round-robin over the sorted donor names (split.make_donor_folds). Fold i's bank,
        correctors, placebo, GLS model and c are built from the OTHER donor groups only, with rows
        at or before the inner-fit end; its scored rows are the held-out groups' rows in the inner
        score years, never after the donor train end.
    Inputs:
        kind: R12 outcome.
        donor_groups: the sorted donor set.
    Returns:
        Derived[(surface kind, held-out groups per fold)] (empty fold tuple for the inner window).
    Refuses:
        - neighbour kind with fewer than 2 donor groups (G-SUPPORT refuses earlier).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R14; C12; per-unit grid pm25_adaptation.py:176-177 (origin
# fire_architecture.py:102-103): LEVELS 0.1,0.3,1,3,10,30,100 x RATIOS 0.0625,0.125,0.25,0.5,1
# around ALPHA 0.5 / A_CTX 0.25; region lambda 100 at adaptation.py:1214; cap 60,000 at
# adaptation.py:1213; neighbour centre adaptation.py:1434.
def derive_r14_router_design(kind: RouterKind, context_columns: Tuple[str, ...]) -> Derived[RouterDesign]:
    """The router's column layout, unpenalised columns, penalty grid and fit-row cap.

    Rule: R14.  Needed: Tue 29 Sep (derive v1); used Fri 2 Oct (per-unit) and Tue 6 Oct (region).

    Contract (plan 2.1 R14, C7, C12):
        Per-unit: intercept, normal (unpenalised), context (level x ratio), trees (level); 7
        levels (0.1-100x) x 5 ratios (0.0625-1) around trees 0.5 / context 0.25, 35 points; the
        grid collapses to the 7 levels when no context is declared (plan says so). Region:
        intercept, normal (unpenalised, U-1), trees (trace-normalised ridge); 7 levels 0.1-100x
        around lambda 100; fit rows capped at 60,000 by keeping whole units (route_kinds.
        region_cap_units). Context declared under a region outcome is unused, and plan says so.
        Neighbour: intercept, context, trees; 35 points around 0.5 / 0.25. The base grid point
        (level 1, ratio 0.5) reproduces the un-swept route (G-PLUMB).
    Inputs:
        kind: R12 outcome.
        context_columns: router_context columns declared by the package (may be empty).
    Returns:
        Derived[RouterDesign].
    Refuses:
        - nothing beyond an unknown kind.
    OWNER DECISION: the plan gives the level RANGE only; propose the source values
        (0.1, 0.3, 1, 3, 10, 30, 100), not log-even values, on every grid including the region's.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R17; Q4 a, Q12 (the engine block replaces own-past columns; all-history mean
# keeps the cumulative column's memory); extends pm25_forecast.py:122-159.
def derive_r17_history_spec(season: SeasonKeySpec, target_window: Window, target_cadence: Cadence,
                            kind: RouterKind, is_events: bool) -> Derived[HistorySpec]:
    """Which own-history columns the engine builds, and where the block starts.

    Rule: R17.  Needed: Tue 29 Sep (derive v1); block built Thu 8 Oct.

    Contract (plan 2.1 R17, 9.1 item 2d):
        The last 3 target values, trailing means over 1 year and 5 years (counted in steps), and
        the mean of all history so far. The block ends at the issue step (t-1 for a nowcast). If
        the target's own window reaches past its step (overlapping composites), the block starts
        one more step back, computed from the target's window fact. Duplicate columns are dropped
        (on annual data the 1-year mean equals the last value). Empty for neighbour. Events with
        repeat visits: the last 3 valid labels before the issue date, means over the trailing 365
        and 1,826 days, and the all-history mean.
    Inputs:
        season: R2 (steps per year).
        target_window: the target's own window fact.
        target_cadence: R1.
        kind: R12 outcome.
        is_events: True for events.
    Returns:
        Derived[HistorySpec].
    Refuses:
        - an unknown target window (align UNKNOWN or no length).
    OWNER DECISION: "one more step back" versus "computed from the window fact" -- propose the
        offset = the number of whole steps the target window reaches past its step, rounded up
        (1 for a composite that spills into the next month).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R18; C7; Q39 a (100 cells); pm25_adaptation.py:122-123; region budget
# adaptation.py:1149-1150, 1213.
def derive_r18_unit_count(kind: RouterKind, season: SeasonKeySpec, donor_all: DonorLabels,
                          test_window_rows_per_unit: int, median_inner_fit_rows_per_unit: float,
                          available_units: Mapping[str, int],
                          pooled_fit_rows_per_group: Mapping[str, int],
                          n_router_columns: int) -> Derived[Mapping[str, int]]:
    """Units per group, from the data only (never the disk).

    Rule: R18.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R18, C7):
        Per-unit: 100. At steps finer than a month: min(100, ceil(1,200 / steps per year)), which
        keeps the 1,200 rows per group-year of 100 monthly units. The count is then raised if
        needed, so each group expects at least 10 test-window events at the donor event rate
        (event = y strictly above the donor rows' 90th percentile; the rate is computed here from
        donor_all and recorded). The floor is skipped, and plan prints why, when the donor event
        rate is 0 (donor q90 equals the target maximum; R33 then gives NaN detection). Region:
        floor(60,000 / median inner-fit rows per unit). Neighbour: every unit. The count is always
        capped at the units available; a group smaller than the rule uses all its units and is
        flagged 'thin' if its pooled fit rows fall below 20 per router column. The same count
        applies to donor and test groups.
    Inputs:
        kind: R12 outcome.
        season: R2 (steps per year).
        donor_all: plan-time donor labels at the nowcast fit cut over EVERY donor-group unit
            (LabelView.donor_labels with unit_ids None), because the pick size depends on the rate.
        test_window_rows_per_unit: census rows per unit in the test window.
        median_inner_fit_rows_per_unit: median valid inner-fit rows per unit (region).
        available_units: {group: candidate units} (split.candidate_units).
        pooled_fit_rows_per_group: {group: pooled fit rows at the chosen count} (thin flag).
        n_router_columns: router columns per unit fit (thin flag).
    Returns:
        Derived[{group: unit count}]; inputs record the event rate and donor_all's row-key hash;
        flags carry 'thin:<group>' and the skipped-floor reason.
    Refuses:
        - donor_all with a scope other than 'all_donor_units', or with no row.
    OWNER DECISION: the event floor's formula -- propose count >= ceil(10 / (test_window_rows_per_unit
        x the donor event rate)), i.e. expected events = units x test rows per unit x rate.
    OWNER DECISION: which donor rows give the event rate -- propose every labelled donor-group row
        at or before the train end (the nowcast fit cut), before any pick (the pick size depends on
        it): donor_all is LabelView.donor_labels with unit_ids None.
    OWNER DECISION: which columns count as "router columns" for the thin flag -- all columns
        including the tree block (then nearly every per-unit group is thin), or the non-tree
        columns only.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R19; C13; pm25_adaptation.py:636-648 (bag max(30, int(0.5 n)); depth 8,
# leaf 5, max_features 0.1); adaptation.py:454-477 (correctors depth 6, leaf 10).
def derive_r19_bank_plan(donor: DonorLabels, smoke: bool) -> Derived[Mapping[str, Any]]:
    """The bank recipe as data: trees per donor, bag size per donor group, tree and corrector
    constants, and the seed formula id.

    Rule: R19.  Needed: Tue 29 Sep (derive v1); bank built Wed 30 Sep.

    Contract (plan 2.1 R19, R21, C13):
        Engine constants: per donor group 100 trees (12 in smoke, R21); each tree fits a bag of
        max(30, half the group's rows) drawn with replacement; depth 8, min leaf 5, max_features
        10%, squared error; float32. Three seeds per tree from the donor NAME (bank_recipe.
        name_seed). Correctors out-of-bag, depth 6, leaf 10, with the expected held-out share per
        group from the bag size. Donors are taken in sorted order. Rows per donor group are
        counted from `donor`, the same rows the bank will see (its row-key hash is recorded).
    Inputs:
        donor: plan-time donor labels at the nowcast fit cut over the PICKED donor units.
        smoke: True only for the smoke command (R21 constants).
    Returns:
        Derived[{'trees_per_donor', 'bag_size' per group, 'expected_oob_share' per group, tree and
        corrector constants, 'seed_formula'}].
    Refuses:
        - a donor group with 0 rows; a DonorLabels whose scope is not 'picked'.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R20; plan 4.5 speedup 1 (row key).
def derive_r20_batching(is_events: bool, test_groups: Tuple[str, ...]) -> Derived[Mapping[str, Any]]:
    """Matrix batching: tree-answer tables per test group, in row blocks, keyed by row.

    Rule: R20.  Needed: Tue 29 Sep (derive v1); store built Thu 1 Oct.

    Contract (plan 2.1 R20, 4.5):
        Tables are built per test group in row blocks, keyed by row and built once per row. The row
        key is unit + step for grids, and unit + event date + issue date for events, because event
        features depend on the issue date. Router standardisation constants come from fit rows at
        or before the cut, after the batched = whole proof. Batching changes hours, never a number.
    Inputs:
        is_events: True for events.
        test_groups: the sorted test set (batch order).
    Returns:
        Derived[{'row_key': [...], 'batch_order': [...]}].
    Refuses:
        - nothing.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R21; pm25_adaptation.py:122-126 (40 cells, 12 trees in smoke).
def derive_r21_smoke_plan(split: SplitSets) -> Derived[Mapping[str, Any]]:
    """The fixed smoke plan: 40 units per group, 12 trees per donor, the first 2 donor and 2 test
    groups in sorted order.

    Rule: R21.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R21):
        Engine constants, never a flag. Plumbing only: smoke deltas carry no sign information.
    Inputs:
        split: the split sets (sorted by the engine).
    Returns:
        Derived[{'units_per_group', 'trees_per_donor', 'donor_groups', 'test_groups'}].
    Refuses:
        - fewer than 2 donor or 2 test groups.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R22; replaces the upper-bound guess at adaptation.py:341-350; Q36 a (a legal
# minimum below 0 gives identity only).
def derive_r22_links(legal_range: Tuple[float, float], donor: DonorLabels) -> Derived[Tuple[Link, ...]]:
    """The link set: identity always; log(y+c) and arcsine only when the facts and donor rows allow.

    Rule: R22, G-DONOR.  Needed: Tue 29 Sep (derive v1).

    Contract (plan 2.1 R22, 5 G-DONOR):
        Identity always. log(y+c) when the legal minimum is >= 0, donor rows have positive values,
        and donor y has more than 2 distinct values. Arcsine when the legal range is [0, UB] with UB
        finite (from the cited fact, never guessed from the data) and donor y has more than 2
        distinct values. Donor y comes from the plan-time label-only view (no FitContext exists at
        plan time); its row-key hash is recorded, and the run refuses if FitContext.donor_rows at
        the same cut hands out different rows.
    Inputs:
        legal_range: the target's cited legal range.
        donor: plan-time donor labels at the nowcast fit cut (LabelView.donor_labels).
    Returns:
        Derived[links in the fixed order identity, log_c, arcsine].
    Refuses:
        - a legal range with min >= max.
        - a DonorLabels whose scope differs from the decision below.
    OWNER DECISION: which donor units the donor-row rules read. Propose: R22 links, R23 c, the R19
        bag sizes and the R30 shares read the PICKED donor units' rows (the rows the bank and the
        router actually see; derive_all computes the picks right after R18); only the R18 event
        rate reads EVERY donor-group unit, because the pick size depends on it. The alternative
        reads every donor-group unit everywhere at plan time, which can disagree with the c that
        FitContext computes on the picked units.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R30; 9.1 item 2f (the 25% threshold is owner-signed); zero-fill as today at
# pm25_adaptation.py:621.
def derive_r30_missing_flags(shares: MissingShares,
                             absent_groups: Mapping[str, Mapping[str, str]]) -> Derived[Mapping[str, Tuple[str, ...]]]:
    """Missing-value flags: a column over 25% missing in donor training rows, or vanishing in a test
    year, needs an explicit verdict in the Q34 review.

    Rule: R30.  Needed: Tue 29 Sep (derive v1; quick-check listing).

    Contract (plan 2.1 R30, 1.4, 5 G-MISSING):
        Tree features are 0-filled (today's rule). Per column the filled share and the share of
        real zeros are printed. A column is FLAGGED, not banned, if it is more than 25% missing in
        donor training rows or vanishes (pooled over groups) in a test year. It then needs keep with
        evidence or ban; keep_unreviewed is not enough (G-MISSING enforces). A late-starting driver
        is handled the same way. Groups a store declares absent get NaN and are counted. The
        "donor training rows" are the rows of one plan-time DonorLabels (scope as derive_r22's
        decision); MissingShares carries its row-key hash, which is recorded.
    Inputs:
        shares: MissingShareReader.measure over the donor training rows: {column: share missing,
            before fill}, {column: share of real zeros}, {(column, test year): share missing,
            pooled over groups}.
        absent_groups: {column: its store's absent_groups}.
    Returns:
        Derived[{column: reasons}] (reasons: 'over_threshold', 'vanishes:<year>').
    Refuses:
        - shares outside [0, 1].
    OWNER DECISION: sign the 25% threshold (9.1 item 2f).
    OWNER DECISION: "vanishes (pooled over groups)" -- propose 100% missing over ALL groups' rows of
        that test year (donor and test groups together).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 4.1 steps 1-2 (the run refuses if derived.json differs from the one plan showed).
def derive_all(package: PackageView, target: TargetTable,
               share_reader: MissingShareReader) -> Mapping[str, Derived[Any]]:
    """Run every plan-time rule in dependency order and return the derived.json content.

    Rule: R1-R22, R30 (orchestration).  Needed: Tue 29 Sep (derive v1).

    Contract (plan Section 2, 4.1 steps 1-2, 5 G-LOCK):
        Order: R1, R2, R8 (needs R1), R4, R3, R5, R6, R7, R10, R11, R9, R12 (needs R7), R13, R14,
        R17, R18, the unit picks (split.candidate_units, split.pick_units), R19, R20, R21, R22,
        R30. Labels: target.y is handed ONLY to a vault.LabelView built on the keys-only grid
        (io_science.build_dense_grid) with no run folder; rules then read validity
        (LabelView.validity) or plan-time donor labels (LabelView.donor_labels at the nowcast fit
        cut from R11), never target.y. No feature pool, FitContext or run folder is built here. R30
        shares come from share_reader over the same donor rows. Run-time rules (R15, R16, R23-R29,
        R31-R36) are recorded by their own modules. The run refuses to start if its derived.json
        differs from the one `treeroute plan` showed. Pure: reads the package and data, writes
        nothing itself.
    Inputs:
        package: the loaded, fingerprinted package.
        target: the target table as read (keys, time columns, y).
        share_reader: the boilerplate column reader for the R30 shares.
    Returns:
        {rule id: Derived value}.
    Refuses:
        - the first rule that refuses stops the whole derivation (fail loudly).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")
