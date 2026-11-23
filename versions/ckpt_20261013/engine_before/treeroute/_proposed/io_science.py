"""PROPOSED signatures: the SCIENCE parts of treeroute/io/ (plan 4.2). Owner signatures, agent bodies,
owner review.

Science here: the integer step index (incl. composite-of-year), sentinel masking, 1:1 joins,
applying computed lags, bans and freezes, the column-set and missing-file checks, the dense grid and
its predecessor lookup, the history block (R17), the events' as-of driver join (M8) and the
aggregation operations. Boilerplate (NOT here): path-template readers and file listing.

Rule for every function: no groupby.shift, no row-order lags. Every look-back goes through
predecessor_index (G-CALENDAR). Sentinels are masked at read, before anything is derived. No
function here takes a raw label array: the dense grid (common.DenseGrid) is keys only, and own-target
reads go through the label vault (vault.LabelView) only (G-LOCK).
"""
# Provenance for the module: pm25_architecture.py:124-135, 155-160; panel_sentinel.py:27-84 +
# presplit_cc/leak_audit.py:66; forecast_arms.py:127-171; pm25_forecast.py:122-159.
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Set, Tuple

import numpy as np
import pandas as pd

from .common import (AggStat, Cadence, CalendarPart, ColumnFacts, Day, DenseGrid, HistorySpec, Lag,
                     OperationDecl, Role, Step, VerdictDecl)
from .fit_context import UnitHistory
from .vault import LabelView


@dataclass(frozen=True)
class SentinelReport:
    """Per column: values masked (declared fill or abs >= 1e30) and values flagged (abs >= 2^30)."""
    masked: Mapping[str, int]
    flagged_near_sentinel: Mapping[str, int]


@dataclass(frozen=True)
class JoinReport:
    """Row counts of one 1:1 join."""
    what: str
    left_rows: int
    right_rows: int
    out_rows: int
    unmatched_left: int


@dataclass(frozen=True)
class ColumnSets:
    """Where each entering column may go (plan 1.3 roles, G-KEYS)."""
    tree_features: Tuple[str, ...]
    router_context: Tuple[str, ...]
    report_only: Tuple[str, ...]        # support, report_stratum, external_product
    frozen: Tuple[str, ...]
    listed_in_reports: Tuple[str, ...]  # keep_unreviewed and watch


@dataclass(frozen=True)
class MissingFileReport:
    """Expected (group, period) pairs against the files found."""
    store: str
    missing: Tuple[Tuple[str, int], ...]
    absent_by_fact: Tuple[Tuple[str, int], ...]
    unexpected: Tuple[Tuple[str, int], ...]


# Provenance: plan 2.1 R1 ("the step index is year x composites per year + composite number");
# pm25_forecast.py:103 and pm25_architecture.py:166 (monthly t = year x 12 + month).
def step_index(time_columns: Mapping[str, np.ndarray], time_facts: Mapping[str, CalendarPart],
               cadence: Cadence) -> np.ndarray:
    """Integer step index (int64) for every row, from its calendar parts. Never a timestamp.

    Rule: R1.  Needed: Tue 29 Sep (M1).

    Contract (plan 2.1 R1, 4.3):
        Monthly: year x months-per-year + month. Annual: year. Composite-of-year: year x
        composites per year + composite number, with the spacing checked within each year. Other
        regular steps: position counted from a fixed origin in whole steps. The index prevents the
        timestamp[ns] bug class (F1): every cut and window compares integers.
    Inputs:
        time_columns: {time column: values per row}.
        time_facts: {time column: calendar part}.
        cadence: R1 outcome.
    Returns:
        int64 array, one step per row.
    Refuses:
        - a calendar part out of range (month 13, day_of_year 367).
        - composite spacing that breaks inside a year.
        - IRREGULAR cadence (events use Day ordinals, not steps).
    OWNER DECISION: index origin -- propose the source form (monthly: year x months-per-year +
        month, without subtracting 1) so the harness compares integers directly.
    OWNER DECISION: origin of a regular N-day step without a year reset -- propose the first
        observed day of the whole target table.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R1 (the last composite of a year is 5-6 days long).
def step_bounds(steps: np.ndarray, cadence: Cadence) -> Tuple[np.ndarray, np.ndarray]:
    """First and last calendar day (Day ordinals) covered by each integer step.

    Rule: R1, R8.  Needed: Tue 29 Sep (M1).

    Contract (plan 2.1 R1):
        The inverse of step_index for timing rules. Composite-of-year: the last composite of a year
        ends on 31 December, so it is shorter than the rest.
    Inputs:
        steps: integer steps.
        cadence: R1 outcome.
    Returns:
        (first_day, last_day) arrays, inclusive.
    Refuses:
        - IRREGULAR, STATIC or EPOCH cadence.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: panel_sentinel.py:27-84 (exact codes, abs >= 1e30, never mask keys/targets, cast ints
# to float first); presplit_cc/leak_audit.py:66; plan 1.3 (fill_values, near_sentinel_optout),
# plan 5 G-SENTINEL. The panel's codes are STORE facts, never engine literals.
def mask_sentinels(frame: pd.DataFrame, facts: Mapping[str, ColumnFacts]) -> Tuple[pd.DataFrame, SentinelReport]:
    """Mask declared fill values and abs >= 1e30 to NaN at read, before anything is derived; flag
    abs >= 2^30.

    Rule: G-SENTINEL (read).  Needed: Tue 29 Sep (M1).

    Contract (plan 1.3, 5 G-SENTINEL):
        For every non-key measurement column: values equal to a declared fill value, and any value
        with abs >= 1e30, become NaN. Values with abs >= 2^30 are FLAGGED (counted), not masked,
        unless the column opts out (near_sentinel_optout). Integer columns are cast to float first
        so a sentinel is removed, never recast. Key-role columns are never masked. Order matters:
        this runs before any lag, window, aggregation or fill. The legal range is the real check
        (G-RANGE), not this function.
    Inputs:
        frame: one freshly read table.
        facts: facts of its columns (fill_values, near_sentinel_optout, role).
    Returns:
        (masked frame, SentinelReport).
    Refuses:
        - a column in the frame without facts.
    OWNER DECISION: the target column -- propose it is never masked but REFUSED if it holds a
        declared fill or abs >= 1e30 (the ingest must write invalid labels as NaN; the source never
        masked targets).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_architecture.py:155-160 (left merge + row-count assert); plan 5 G-JOIN.
def join_one_to_one(left: pd.DataFrame, right: pd.DataFrame, keys: Tuple[str, ...], what: str) -> Tuple[pd.DataFrame, JoinReport]:
    """Join 1:1 on keys with a row-count assert.

    Rule: G-JOIN (runtime).  Needed: Tue 29 Sep (M1).

    Contract (plan 4.1 step 3, 5 G-JOIN):
        Keys must be unique on both sides. The output has exactly the left row count, in left
        order. Unmatched left rows are counted in the report.
    Inputs:
        left: the frame that defines the rows (the dense grid or the event table).
        right: the frame joined on.
        keys: join key columns.
        what: a label for the report and any refusal.
    Returns:
        (joined frame, JoinReport).
    Refuses:
        - duplicate keys on either side.
        - any change in row count.
        - a right column name that collides with a left column.
    OWNER DECISION: unmatched left rows -- propose they are allowed as NaN and counted (they then
        fall under R30), as the source's left join does; the alternative refuses any unmatched row.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_architecture.py:139-160 (share of cell-years with >1 distinct non-NaN value must
# be <= 0.001, else stop; then first value per cell-year; the lag is applied to that collapsed table,
# year + 1, BEFORE the 1:1 join, :152-160); plan 5 G-CADENCE.
def join_coarser_column(grid_frame: pd.DataFrame, column_frame: pd.DataFrame, column: str,
                        column_cadence: Cadence, target_cadence: Cadence, lag: Lag) -> pd.DataFrame:
    """Join a column stored at a finer table but declared at a coarser cadence (an annual column
    inside monthly rows), after asserting it is constant within each unit x coarse period, with its
    R8 lag applied to the collapsed table before the join.

    Rule: G-CADENCE (annual joins), R8, G-CALENDAR.  Needed: Tue 29 Sep (M1).

    Contract (plan 5 G-CADENCE, 2.1 R8):
        Annual joins happen after a constancy assert: the share of unit x coarse periods holding
        more than one distinct non-NaN value must not exceed 0.1%. Then one value per unit x
        period is kept. The lag is applied on that one-value-per-unit-x-period table, in the
        column's own steps, through predecessor_index: the value of period P serves the target
        rows of period P + lag.steps (an annual lag of 1: year Y-1 serves every month of year Y).
        A missing predecessor period gives NaN (then R30). Only then is the table joined 1:1
        (join_one_to_one) onto the target-step frame. apply_lags never sees a coarser column.
    Inputs:
        grid_frame: the target-step frame.
        column_frame: the stored rows holding the column.
        column: the column name.
        column_cadence: its declared cadence.
        target_cadence: the target's cadence.
        lag: the column's R8 lag from derived.json (column steps).
    Returns:
        grid_frame with the lagged column joined.
    Refuses:
        - constancy share above 0.1% (the premise of the declared cadence is wrong).
        - a declared cadence finer than the target's, or a lag for another column.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R8 + 5 G-CALENDAR (lags only through the dense-grid predecessor lookup).
def apply_lags(frame: pd.DataFrame, unit_codes: np.ndarray, steps: np.ndarray,
               lags: Mapping[str, Lag], target_cadence: Cadence) -> pd.DataFrame:
    """Move each column that lives at the target's own step back by its computed lag, through
    predecessor_index.

    Rule: R8, G-CALENDAR.  Needed: Tue 29 Sep (M1).

    Contract (plan 2.1 R8, 4.1 step 3, 5 G-CALENDAR):
        For columns at the target's cadence (including aggregate_time outputs, whose cadence is the
        target's): a row's value of column c becomes the value of the same unit exactly
        lags[c].steps target steps earlier. A missing predecessor gives NaN (then R30), never a
        neighbour's value. No groupby.shift. Coarser columns are lagged inside join_coarser_column,
        on their one-value-per-period table, before the join.
    Inputs:
        frame: the joined frame (one row per unit x target step).
        unit_codes: integer unit code per row.
        steps: integer target step per row.
        lags: R8 lags from derived.json, for the columns of the frame to lag.
        target_cadence: R1.
    Returns:
        the frame with lagged columns (same rows, same order).
    Refuses:
        - a column with no lag in derived.json, or a lag not in derived.json.
        - a lag whose column cadence differs from the target's (it belongs to join_coarser_column).
        - any predecessor read that is not in the same unit or not exactly L steps back.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_forecast.py:265-305 (at lead L the whole feature row moves back to the issue step).
def features_at_issue_step(features: np.ndarray, unit_codes: np.ndarray, steps: np.ndarray,
                           lead_steps: int) -> np.ndarray:
    """At lead L, give each target row the feature row of its issue step t - L (same unit).

    Rule: R8, R11.  Needed: Fri 9 Oct (forecast ladder).

    Contract (plan 1.5, 2.1 R8):
        At lead L the engine moves the WHOLE feature row back to the issue step. Columns keep their
        R8 lags relative to that step. A missing issue row gives NaN, never a shifted neighbour.
    Inputs:
        features: feature matrix, one row per dense-grid row.
        unit_codes, steps: keys per row.
        lead_steps: L (0 returns the input unchanged).
    Returns:
        feature matrix aligned to the target rows.
    Refuses:
        - lead_steps < 0.
        - any read outside the unit or not exactly L steps back (G-CALENDAR).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 1.4 (verdicts), 1.3 (roles), 5 G-CLOSED and G-KEYS; pm25_architecture.py:78
# (DROP_CONDITIONAL = True).
def apply_verdicts(columns: Tuple[str, ...], verdicts: Mapping[str, VerdictDecl],
                   roles: Mapping[str, Role]) -> ColumnSets:
    """Decide where every non-key column goes: tree features, router context, report only, or out.

    Rule: plan 1.4, G-CLOSED, G-KEYS.  Needed: Tue 29 Sep (M1).

    Contract (plan 1.3, 1.4):
        keep, keep_unreviewed, watch and freeze enter; ban and conditional leave every engine run.
        router_context goes to the router only, never the trees. support, report_stratum and
        external_product are report-only (never a feature, router input, selector or selection
        baseline). keep_unreviewed and watch are listed in every report. Key roles never become
        tree features.
    Inputs:
        columns: every non-key column in the data.
        verdicts: ban.yaml.
        roles: package roles.
    Returns:
        ColumnSets.
    Refuses:
        - a column without a verdict, or a verdict for an absent column (closed world).
        - the target or a target_twin with any verdict other than ban.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.1 R9; defo_ban.py:14-15, 76 ("usable only as ONE pre-window epoch").
def apply_freezes(frame: pd.DataFrame, unit_codes: np.ndarray, content_epoch_of_row: Mapping[str, np.ndarray],
                  epochs: Mapping[str, Day]) -> pd.DataFrame:
    """Hold each 'freeze' column at its computed epoch.

    Rule: R9.  Needed: Tue 29 Sep (M1).

    Contract (plan 1.4, 2.1 R9):
        For a frozen column, every row takes the unit's value at the epoch R9 computed for the cut
        in use. The epoch differs per lead, so this runs per cut.
    Inputs:
        frame: the joined frame.
        unit_codes: integer unit code per row.
        content_epoch_of_row: {column: content epoch (Day) of each row's stored value}.
        epochs: {column: the R9 epoch for this cut}, read from derived.json under the key
            (column, lead, cut kind) of the cut in use.
    Returns:
        the frame with frozen columns replaced.
    Refuses:
        - a unit with no value at the epoch (it cannot be frozen; its value is NaN and counted, or
          the run stops -- see decision).
    OWNER DECISION: propose ALL rows take the epoch value (the source rule is "ONE pre-window
        epoch"); the alternative keeps each earlier row's own value and freezes only later rows.
    OWNER DECISION: a unit missing a value at the epoch -- propose NaN, counted (R30).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-JOIN ("the observed column set equals the catalog"), G-CLOSED; the assembler
# that reverted 49 columns while printing OK (Part 326).
def check_column_set(observed: Tuple[str, ...], catalog: Tuple[str, ...], table: str) -> None:
    """The observed column set of a table must equal its catalog's column set.

    Rule: G-JOIN, G-CLOSED.  Needed: Tue 29 Sep (M1).

    Contract (plan 5):
        Set equality, compared as sets (order carries no meaning). A listed-but-absent column is an
        error; a present-but-undeclared column is an error.
    Inputs:
        observed: columns read from the table's files.
        catalog: columns its catalog declares.
        table: table name for the message.
    Returns:
        None.
    Refuses:
        - any difference, naming every missing and every extra column.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 1.2 (missing-file check), 1.3 absent_groups; pm25_architecture.py:170-176 skipped
# missing files silently (the defect this replaces).
def check_missing_files(expected: Set[Tuple[str, int]], found: Set[Tuple[str, int]],
                        absent_groups: Mapping[str, str], store: str) -> MissingFileReport:
    """Expected (group, period) pairs from the target against the files found in a store.

    Rule: G-MISSING (files).  Needed: Tue 29 Sep (M1).

    Contract (plan 1.2, 1.3, 2.4 R30):
        A missing file stops the run unless the store declares that group absent (absent_groups);
        declared-absent groups get NaN and are counted. Nothing is skipped silently.
    Inputs:
        expected: (group, period) pairs the target needs from this store.
        found: pairs present on disk (file listing is boilerplate).
        absent_groups: the store's absent_groups fact.
        store: store name for the message.
    Returns:
        MissingFileReport.
    Refuses:
        - any missing pair whose group is not declared absent.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 4.1 step 3, 2.4 R30 (the dense grid holds every unit x step); pm25_forecast.py:
# 122-159 (dense cell x month grid).
def build_dense_grid(unit_ids: np.ndarray, group_ids: np.ndarray, steps: np.ndarray,
                     coverage: Tuple[Step, Step]) -> DenseGrid:
    """Build the KEYS-ONLY dense unit x step grid over every row of the target census.

    Rule: R30, G-SUPPORT (census), G-LOCK.  Needed: Tue 29 Sep (derive v1 builds the vault on it).

    Contract (plan 1.2 target table, 2.4 R30, 4.1 step 3, 5 G-LOCK):
        The target is a complete census: one row per unit and step inside the coverage, (unit,
        step) unique. The grid takes keys only and never a label: rows with a NaN label leave fit
        and score sets (the vault knows which) but stay in the grid for feature and history
        lookup. Units are sorted by id.
    Inputs:
        unit_ids, group_ids, steps: target keys (TargetTable keys; never its y).
        coverage: first and last step of the coverage.
    Returns:
        DenseGrid (keys only).
    Refuses:
        - duplicate (unit, step).
        - a missing unit x step inside the coverage (a hole in the census).
        - a unit in two groups.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: forecast_arms.py:127-171 (prev_index: search for (unit, step - lead), re-verify unit
# and step, -1 when absent, asserts never cross a unit).
def predecessor_index(unit_codes: np.ndarray, steps: np.ndarray, k: int) -> np.ndarray:
    """Position of each row's predecessor exactly k steps back in the same unit, or -1.

    Rule: G-CALENDAR.  Needed: Wed 30 Sep (pool reader).

    Contract (plan 5 G-CALENDAR; source: provenance comment):
        Rows may come in any order; the result indexes that same order. The predecessor is found by
        an actual search for (unit, step - k), never assumed to be the adjacent row. Every hit is
        re-verified: same unit and exactly k steps back. A unit with a gap has no predecessor there
        (-1), never an imputed or shifted one.
    Inputs:
        unit_codes: integer unit code per row.
        steps: integer step per row.
        k: steps back (>= 1).
    Returns:
        int64 positions, -1 where absent.
    Refuses:
        - k < 1.
        - duplicate (unit, step) in the input.
        - (internal assert) any hit that crosses a unit or is not exactly k back.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.3 R17; pm25_forecast.py:122-159 (history_block: dense grid, rmean over
# available months only, missing lag -> own 12-month mean, never 0); Q4 a, Q12.
def history_block(grid: DenseGrid, spec: HistorySpec, target_steps: np.ndarray, unit_rows: np.ndarray,
                  lead_steps: int, labels: LabelView,
                  normal_fill: Mapping[str, UnitHistory]) -> Tuple[np.ndarray, Mapping[str, float]]:
    """The engine's own-history block for each target row, ending at the issue step.

    Rule: R17, G-HIST, G-CALENDAR, G-LOCK.  Needed: Thu 8 Oct (history block for all; signature at M2 start).

    Contract (plan 2.3 R17, 5 G-LOCK):
        For a row predicting step t at lead L, the block reads the unit's own labels up to
        timing.latest_label_step(t, L) (t-1 for a nowcast), moved back by spec.start_offset_steps.
        Columns: the last 3 values, trailing means over 1 and 5 years in steps, and the mean of all
        history so far, as listed in spec (duplicates already dropped). Positions come from the
        keys-only grid; every label comes from LabelView.asof_rows, the only label source. A
        missing lag takes the unit's own 1-year mean, then its 5-year mean, then its normal, never
        0. The filled share per column is returned and printed.
    Inputs:
        grid: the keys-only dense grid (positions).
        spec: R17 spec.
        target_steps: step t per target row.
        unit_rows: grid row (unit) per target row.
        lead_steps: L.
        labels: the label vault (as-of reads only).
        normal_fill: {unit id: UnitHistory at the cut} for the last-resort normal (identity link).
    Returns:
        (float32 matrix rows x spec.columns, {column: filled share}).
    Refuses:
        - any read of a label after the row's newest readable step (G-HIST).
        - a non-finite value left after the fill chain.
    OWNER DECISION: trailing means use AVAILABLE steps only with no minimum count (the source rule);
        confirm, or set a minimum.
    OWNER DECISION: "mean of all history so far" -- propose it starts at the first step of the dense
        grid (the first data year), not at Y0.
    OWNER DECISION: test rows need test-window labels before their issue step; the plan builds the
        block (4.1 step 4) before the adoption hash (step 8) -- see vault.LabelView.asof_rows.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.3 R17 (events with repeat visits); 9.1 item 2e. M8 under the fast track.
def event_history_block(unit_ids: np.ndarray, issue_days: np.ndarray, event_start_days: np.ndarray,
                        lead_days: int, labels: LabelView,
                        normal_fill: Mapping[str, UnitHistory]) -> Tuple[np.ndarray, Mapping[str, float]]:
    """Own-history block for events with repeat visits, read from the as-of label view.

    Rule: R17 (events).  Needed: M8 (event rules; fast track).

    Contract (plan 2.3 R17):
        The last 3 valid labels before the issue date, the means over the trailing 365 and 1,826
        days, and the mean of all history. A label counts only if its own window ends at or before
        the issue date (at lead 0, before the event's own window starts). Missing values take the
        same fill chain as the grid block, never 0. Empty for the neighbour kind.
    Inputs:
        unit_ids: site per event row.
        issue_days: issue date per row (event date minus the lead).
        event_start_days: first day of each event's own window (lead-0 rule).
        lead_days: lead in days.
        labels: the label vault.
        normal_fill: {unit id: UnitHistory at the cut}.
    Returns:
        (matrix, {column: filled share}).
    Refuses:
        - any label read in another unit or dated after the issue date (G-CALENDAR).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 1.2 driver tables ("For events the ENGINE does the as-of join at each row's issue
# date, using each column's computed reach (R8)"). M8 under the fast track.
def asof_driver_join(events: pd.DataFrame, driver: pd.DataFrame, reach: Mapping[str, Lag]) -> pd.DataFrame:
    """For each event row, the newest driver value whose content ends at or before the row's issue
    date.

    Rule: R8 (events), G-JOIN.  Needed: M8 (event rules; fast track).

    Contract (plan 1.2, 2.1 R8):
        Datasets no longer write one table per lead or stamp their own as-of dates; the engine
        joins per row using each column's computed reach. Row count unchanged (1:1).
    Inputs:
        events: event rows with unit id and issue date.
        driver: dated driver rows (unit id, date, columns).
        reach: R8 lag/reach per driver column.
    Returns:
        events with driver columns joined.
    Refuses:
        - any joined value whose content ends after the issue date.
        - any change in row count.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 1.5 (aggregate_time; an aggregate inherits units, legal range for mean/min/max,
# lineage and product family; its window and stamp are computed); defo_matrix.py:21-25.
def aggregate_time(frame: pd.DataFrame, column: str, facts: ColumnFacts, target_cadence: Cadence,
                   stat: AggStat, season_months: Optional[Tuple[int, ...]]) -> Tuple[pd.DataFrame, ColumnFacts]:
    """Aggregate a finer column to the target's step (monthly to annual, or to a growing season).

    Rule: plan 1.5 aggregate_time.  Needed: Tue 29 Sep (M1).

    Contract (plan 1.5):
        stat is mean, min, max or sum over each unit x target period (or over the declared season
        months inside it). The output facts are COMPUTED: units inherited; legal range inherited for
        mean/min/max; lineage and product family inherited; window and stamp computed from the
        aggregation span, never typed. Trailing only: a period's aggregate uses only content inside
        that period.
    Inputs:
        frame: the finer rows (sentinels already masked).
        column: source column.
        facts: its facts.
        target_cadence: the step to aggregate to.
        stat: the declared statistic.
        season_months: optional month set inside the year (growing season).
    Returns:
        (aggregated rows keyed unit x target step, computed facts of the new column).
    Refuses:
        - a source cadence that is not finer than the target's.
    OWNER DECISION: missing values inside a period -- propose NaN if any sub-period is missing
        (strict), versus aggregating over the available sub-periods.
    OWNER DECISION: legal range of a SUM -- not inherited by the plan; propose computed as
        [n x min, n x max] for n sub-periods, or require a declaration.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 1.5 (aggregate_space {unit_map, stat}); plan 1.1 tables/unit_map.parquet.
def aggregate_space(frame: pd.DataFrame, column: str, facts: ColumnFacts, unit_map: pd.DataFrame,
                    stat: AggStat) -> Tuple[pd.DataFrame, ColumnFacts]:
    """Aggregate source units to package units through the unit_map (grid cells to polygons).

    Rule: plan 1.5 aggregate_space.  Needed: Tue 29 Sep (M1; reserved, no current package uses it).

    Contract (plan 1.5, 1.1):
        unit_map rows are (source unit, unit, weight). The output facts are computed and inherited
        as in aggregate_time.
    Inputs:
        frame: source-unit rows.
        column: source column.
        facts: its facts.
        unit_map: the package's unit_map table.
        stat: the declared statistic.
    Returns:
        (rows keyed unit x step, computed facts).
    Refuses:
        - a source unit in the frame that the map does not list, or map weights that are not
          positive.
    OWNER DECISION: how weights enter -- propose a weighted mean for MEAN and weighted sum for SUM;
        MIN and MAX ignore weights.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 1.5 (the full operation list; trailing only; target-derived columns use y strictly
# before their own row); plan 5 G-DERIVED (recompute on a stride sample).
def recompute_declared_operation(decl: OperationDecl, sources: pd.DataFrame, grid: DenseGrid,
                                 labels: LabelView, rows: np.ndarray,
                                 adjacency: Optional[pd.DataFrame]) -> np.ndarray:
    """Recompute one engineered column on given rows from its declaration (the reference G-DERIVED
    compares the feature script against).

    Rule: plan 1.5, G-DERIVED, G-LOCK.  Needed: Sat 10 Oct (check --deep green).

    Contract (plan 1.5, 5 G-LOCK):
        Operations: lag k; trailing mean, sum, min or max over w; cumulative; years since;
        neighbour aggregate (grid or adjacency table); aggregate_time; aggregate_space. Trailing
        only: a driver-derived column ends at its own stamp; a target-derived column uses y
        strictly BEFORE its own row. Look-backs go through predecessor_index on the keys-only
        grid; target labels are read ONLY through LabelView.asof_rows with the row's step - 1 as
        its newest readable step (which rows may be sampled: validators.check_g_derived).
    Inputs:
        decl: the column's declaration.
        sources: the source columns (masked; driver columns only, never the target).
        grid: the keys-only dense grid (positions).
        labels: the label vault (target-derived operations).
        rows: the sample rows to recompute.
        adjacency: the package adjacency table, when the operation needs one.
    Returns:
        recomputed values for the sample rows.
    Refuses:
        - an operation not in the list.
        - a lag or window of the unit's own y (that is the engine's history block, G-HIST).
    OWNER DECISION: "years since" with no earlier event -- NaN (propose) or a declared cap.
    OWNER DECISION: grid neighbour aggregate -- which neighbours (propose the 8 surrounding cells by
        grid_ix, grid_iy) when no adjacency table is given.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")
