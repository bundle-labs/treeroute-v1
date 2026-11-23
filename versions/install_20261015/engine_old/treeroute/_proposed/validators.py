"""PROPOSED signatures: the SCIENCE validators of treeroute/check/ (plan 4.2, Section 5). Owner
signatures, agent bodies, owner review -- for EVERY validator below.

Science validators (plan 4.2): the leak validators G-LAG, G-EPOCH, G-LINEAGE, G-HIST, G-DERIVED,
G-CADENCE, G-CALENDAR; the range, support and missing-value validators with their thresholds
(G-RANGE, G-SUPPORT, G-MISSING); G-CLOSED, G-KEYS, G-SPLIT, G-SENTINEL, G-JOIN, G-FACTS.
Boilerplate (NOT here): report writing, fingerprint files, the fixture runner, and the static or
runtime guards the plan does not list as science (G-NOKNOB, G-NONAMES, G-IMPORT, G-THREADS,
G-NOOVERWRITE, G-FINGERPRINT, G-DISK, G-LEGACY, G-NODRAW). Runtime guards enforced inside science
modules live there: G-DISJOINT (split), G-FITCUT and G-DONOR (fit_context), G-LOCK (vault),
G-CLIP and G-PLUMB (layer), G-DECIDE (metrics).

Every validator returns a GuardResult. Messages print a rule id, the columns, the fix and a Part
number; the plain-words lesson lives in docs/lessons.yaml. Declarations are ENFORCED, not detected:
a wrong window or lineage fact passes, so the planted-fault table says 'rule enforcement'.
"""
# Provenance for the module: desertflow_framework/validators.py:32-37, 90-166, 189-242;
# pm25_ban.py:168-184.
from __future__ import annotations

from typing import Mapping, Optional, Set, Tuple

import numpy as np
import pandas as pd

from .common import (Cadence, ColumnFacts, CutPair, DenseGrid, Derived, ExceptionEntry, GuardResult, Lag,
                     Role, SplitSets, TargetFacts, VerdictDecl)
from .io_science import ColumnSets, JoinReport
from .vault import DonorLabels, LabelView


# ---------------------------------------------------------------------------------------- quick checks
# Provenance: plan 5 G-CLOSED; plan 1.4, 9.2 A5; default-in feature lists (pm25_architecture.py:219-221);
# a silent skip (defo_ban.py:149-173).
def check_g_closed(data_columns: Tuple[str, ...], columns: Mapping[str, ColumnFacts],
                   verdicts: Mapping[str, VerdictDecl], forward_reach: Mapping[str, int],
                   lineage_flagged: Set[str]) -> GuardResult:
    """G-CLOSED: every non-key column has facts and a verdict (closed world).

    Rule: G-CLOSED, A5.  Needed: Tue 29 Sep (quick checks).

    Contract (plan 5 G-CLOSED, 1.4, 9.2 A5):
        Every non-key column in the data has facts and exactly one verdict; a listed-but-absent
        column is an error. Every verdict carries a free-text reason (VerdictDecl.reason); a ban's
        reason is exactly one BanReason label (VerdictDecl.ban_reason), as package/schema.py
        enforces. Evidence (a Part number) as the decision below. keep_unreviewed is allowed only
        with signed timing facts, no forward reach and no lineage flag, and is listed in every
        report.
    Inputs:
        data_columns: non-key columns observed in the data.
        columns: their facts.
        verdicts: ban.yaml.
        forward_reach: {column: days of forward reach} (timing.forward_reach_days, max over periods).
        lineage_flagged: columns G-LINEAGE flags.
    Returns:
        GuardResult (BLOCK on any violation; the keep_unreviewed list in details).
    Refuses (BLOCK):
        - a column without facts or verdict; a verdict or fact for an absent column.
        - a verdict without a reason; a ban without its BanReason label; a missing evidence Part
          where the decision below requires one.
        - keep_unreviewed with unsigned timing facts, forward reach > 0, or a lineage flag.
    OWNER DECISION: does keep_unreviewed need an evidence Part? Propose NO, as package/schema.py
        already does: the verdict is unreviewed by definition, so plan 1.4's "each verdict carries
        a reason and evidence" reads as every REVIEWED verdict (keep, freeze, ban, conditional,
        watch). The alternative refuses keep_unreviewed without a Part, and schema.py changes.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-LAG; centred indices (Q2); window-centre dating (fire_ban.py:33-37); product-year
# dating (defo_ban.py:28-29); F10.
def check_g_lag(columns: Mapping[str, ColumnFacts], target: TargetFacts, target_cadence: Cadence,
                lags: Derived[Mapping[str, Lag]]) -> GuardResult:
    """G-LAG: every lag is COMPUTED from facts (R8); nothing types a lag; an unknown window is refused.

    Rule: G-LAG, R8.  Needed: Tue 29 Sep (quick checks).

    Contract (plan 5 G-LAG, 2.1 R8):
        Every entering time-varying column has a lag in derived.json equal to timing.compute_lag on
        its facts; no column enters with forward reach at lag 0; an unknown window without a signed
        bound is refused.
    Inputs:
        columns: facts of entering columns.
        target, target_cadence: target facts and R1.
        lags: the R8 entry of derived.json.
    Returns:
        GuardResult.
    Refuses (BLOCK):
        - a missing lag, a lag that differs from its recomputation, or an unknown window.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-EPOCH; post-window snapshots, projections, extrapolations (defo_ban.py:80-111);
# Q43 a (base periods allowed and disclosed).
def check_g_epoch(columns: Mapping[str, ColumnFacts], verdicts: Mapping[str, VerdictDecl],
                  cuts: Mapping[int, CutPair], target: TargetFacts, train_end: int,
                  exceptions: Tuple[ExceptionEntry, ...]) -> GuardResult:
    """G-EPOCH: a column whose content is observed after the cut is refused unless 'freeze'; a target
    calibrated past the donor train end is refused unless recalibrated or disclosed.

    Rule: G-EPOCH, R9.  Needed: Tue 29 Sep (quick checks).

    Contract (plan 5 G-EPOCH, 1.3):
        Release dates and anomaly base periods (baseline_period) never trigger it; a base period past
        the cut is listed as a disclosure (Q43 a). A target whose calibration_through is after the
        donor train end is refused unless the ingest recalibrates or an exceptions.yaml entry
        discloses it.
    Inputs:
        columns: facts of entering columns.
        verdicts: ban.yaml.
        cuts: R11 cuts per lead.
        target: target facts (calibration_through).
        train_end: R6.
        exceptions: exceptions.yaml.
    Returns:
        GuardResult (disclosures in details).
    Refuses (BLOCK):
        - a non-freeze column observed after a cut; an undisclosed target calibrated past train end.
    OWNER DECISION: "observed after the cut" -- propose: observed_through (or a snapshot's content
        epoch) later than the cut, checked against EVERY cut the column is used at (each lead's fit
        cut and guard cut).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-LINEAGE; plan 1.4 (sum groups share one verdict; target and twins forced to ban);
# a sum group rebuilt from its members (defo_ban.py:28-34); a product constrained by the target source;
# classifiers trained on the target (Q35); F16.
def check_g_lineage(columns: Mapping[str, ColumnFacts], target: TargetFacts,
                    verdicts: Mapping[str, VerdictDecl], exceptions: Tuple[ExceptionEntry, ...]) -> GuardResult:
    """G-LINEAGE (quick): provenance facts checked against the target.

    Rule: G-LINEAGE.  Needed: Tue 29 Sep (quick checks).

    Contract (plan 5 G-LINEAGE, 1.3, 1.4):
        product_family, derived_from, trained_on, computed_from and sum groups are checked against
        the target. The target and its twins are forced to ban. A co-product (same product family,
        or a lineage that assimilates or was trained on the target) needs a signed exceptions.yaml
        entry. All members of a sum group get the same verdict.
    Inputs:
        columns: facts of every non-key column.
        target: target facts.
        verdicts: ban.yaml.
        exceptions: exceptions.yaml.
    Returns:
        GuardResult (flagged columns in details; G-CLOSED reads them).
    Refuses (BLOCK):
        - the target or a twin not banned; an unsigned co-product; a sum group with mixed verdicts.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 1.3 co_measured_with_target ("No default: the checker lists every column that shares
# product family or sensor lineage with the target in the same period").
def list_co_measured_candidates(columns: Mapping[str, ColumnFacts], target: TargetFacts) -> Tuple[str, ...]:
    """Every column that must carry an explicit co_measured_with_target answer.

    Rule: G-LINEAGE, G-FACTS, R8.  Needed: Tue 29 Sep (quick checks).

    Contract (plan 1.3):
        A candidate shares product family or sensor lineage with the target in the same period.
        Each candidate needs an explicit true/false with a Part number (G-FACTS). A true answer
        gives a lag of at least 1 step (R8).
    Inputs:
        columns: facts of every non-key column.
        target: target facts.
    Returns:
        candidate column names, sorted.
    Refuses:
        - nothing (a listing).
    OWNER DECISION: "sensor lineage" has no dedicated fact; propose: same product_family, or the
        target's product family appears in lineage_assimilates or lineage_trained_on, at a cadence no
        coarser than the target's.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-HIST (quick: by declaration); y(t) at lead 0 (pm25_forecast.py:99); F22.
def check_g_hist_declared(columns: Mapping[str, ColumnFacts], target: TargetFacts) -> GuardResult:
    """G-HIST (quick): refuse dataset columns DECLARED as a lag, trailing or cumulative sum or mean of
    the unit's own target.

    Rule: G-HIST, R17.  Needed: Tue 29 Sep (quick checks).

    Contract (plan 5 G-HIST, 1.5):
        The engine builds the own-history block (R17); a dataset column whose declaration is lag,
        trailing mean/sum or cumulative of the target (reads_target) is refused. Allowed target-
        derived transforms (event counts, years since the last event, neighbour aggregates) pass.
    Inputs:
        columns: facts of engineered columns.
        target: target facts.
    Returns:
        GuardResult.
    Refuses (BLOCK):
        - any such column.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-KEYS (memorised calendar posing as skill); plan 1.3 roles.
def check_g_keys(columns: Mapping[str, ColumnFacts], column_sets: ColumnSets) -> GuardResult:
    """G-KEYS: keys are never tree features; a key-derived column may only be router context.

    Rule: G-KEYS.  Needed: Tue 29 Sep (quick checks).

    Contract (plan 5 G-KEYS, 1.3, 1.5):
        No key-role column is a tree feature. Any column derived from a key role may only be
        router_context. router_context columns and the normal are read only by the router.
    Inputs:
        columns: facts (role, derived_from).
        column_sets: io_science.apply_verdicts outcome.
    Returns:
        GuardResult.
    Refuses (BLOCK):
        - a key or key-derived column among tree features; router context among tree features.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-SPLIT; NDVI 25-vs-44 (Part 426); pm25_split.check() never called (pm25_split.py:
# 192-197).
def check_g_split(split: SplitSets, data_groups: Tuple[str, ...]) -> GuardResult:
    """G-SPLIT (quick): split lists are sets, sorted by the engine; the data's groups equal the split's.

    Rule: G-SPLIT.  Needed: Tue 29 Sep (quick checks).

    Contract (plan 5 G-SPLIT, 1.2):
        Uses split.as_sorted_set and split.split_differences. Counts are printed but never used as
        the check. The output re-check (scored units = derived units) is split.check_scored_units.
    Inputs:
        split: split.yaml.
        data_groups: groups in the target table.
    Returns:
        GuardResult.
    Refuses (BLOCK):
        - duplicates, donor/test overlap, or any set difference.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-SUPPORT (NEW); 9.1 item 2f (thresholds owner-signed); Q19 (the 1.96 interval is more
# than 10% narrower than t(n-1) below 14 groups).
def check_g_support(donor: DonorLabels, census_complete: bool, is_events: bool,
                    n_zero_observations: int, n_test_groups: int, n_donor_groups: int,
                    any_all_zero_unit: bool) -> GuardResult:
    """G-SUPPORT: enough support to learn and to judge.

    Rule: G-SUPPORT, C15.  Needed: Tue 29 Sep (quick checks).

    Contract (plan 5 G-SUPPORT):
        Donor y has at least 2 distinct values. A grid target holds a row for every unit x step in
        coverage (NaN only as a declared-invalid label); an event target keeps its zero
        observations. Presence-only tables are refused ("grid it to unit x step with zeros"). A unit
        set with no all-zero unit is flagged (the unit set is declared in AUDIT_CHECKLIST). Fewer
        than 3 test groups or 2 donor groups are refused. Fewer than 14 test groups are flagged;
        fewer than 5 donor groups are flagged. Flags are report only.
    Inputs:
        donor: plan-time donor labels at the nowcast fit cut (vault.LabelView.donor_labels).
        census_complete: io_science.build_dense_grid succeeded without holes.
        is_events: True for events.
        n_zero_observations: zero labels in the event table.
        n_test_groups, n_donor_groups: split sizes.
        any_all_zero_unit: whether any unit's labels are all zero.
    Returns:
        GuardResult.
    Refuses (BLOCK):
        - fewer than 2 distinct donor values; an incomplete census; fewer than 3 test or 2 donor
          groups; a presence-only table.
    OWNER DECISION: sign the thresholds (3 / 2 refuse; 14 / 5 flag); the alternative flags under
        10 test groups instead of 14.
    OWNER DECISION: the plan states the presence-only refusal but not its test; the census check
        covers grids, and an event rule is needed (for example: no zero observation at all while the
        legal minimum is 0). Both label counts (zero observations, all-zero units) are proposed on
        labels at or before the donor train end (LabelView.asof), so the check reads no test-window
        label.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-FACTS (NEW; headline + pre-registration); plan 1.3 data_selected; F15; NDVI's top-5
# context list (cross_region_run89.py:887).
def check_g_facts(columns: Mapping[str, ColumnFacts], verdicts: Mapping[str, VerdictDecl], target: TargetFacts,
                  co_measured_candidates: Tuple[str, ...], earliest_fit_cut_day: int,
                  test_groups: Tuple[str, ...], exceptions: Tuple[ExceptionEntry, ...],
                  headline: bool) -> GuardResult:
    """G-FACTS: unsigned timing facts cannot enter the headline.

    Rule: G-FACTS.  Needed: Tue 29 Sep (quick checks); BLOCKS at the freeze (Sat 10 Oct).

    Contract (plan 5 G-FACTS, 1.3):
        Every kept column's timing facts (stamp, window, cadence, content epoch) are verified or
        signed 'assumed'. co_measured_with_target is explicit (true/false with a Part) for every
        listed candidate. The target's legal range cites a documented source. Roles appear only in
        package catalogs. A data-selected column list is declared, and is refused if it read test
        groups or rows after the earliest fit cut, unless an exceptions.yaml entry discloses it as
        test-exposed.
    Inputs:
        columns, verdicts, target: facts and verdicts.
        co_measured_candidates: list_co_measured_candidates.
        earliest_fit_cut_day: the earliest fit cut of any lead, as a Day.
        test_groups: the sorted test set.
        exceptions: exceptions.yaml.
        headline: True for a headline run or the pre-registration (BLOCK); False flags only.
    Returns:
        GuardResult.
    Refuses (BLOCK when headline):
        - any unsigned timing fact on a kept column; a missing co_measured answer; an uncited legal
          range; an undisclosed data-selected list that read test groups or late rows.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-MISSING; plan 2.4 R30, 1.4 (a flagged column needs keep with evidence or ban;
# keep_unreviewed is not enough); SPEI/AMO vanishing in the last year.
def check_g_missing(flags: Derived[Mapping[str, Tuple[str, ...]]], verdicts: Mapping[str, VerdictDecl]) -> GuardResult:
    """G-MISSING (quick): every column R30 flags carries keep-with-evidence or ban.

    Rule: G-MISSING, R30.  Needed: Tue 29 Sep (quick checks).

    Contract (plan 5 G-MISSING, 2.4 R30):
        A flagged column is refused only without an explicit keep (with an evidence Part) or ban
        verdict from the Q34 review; keep_unreviewed is not enough. Shares are reported.
    Inputs:
        flags: the R30 entry of derived.json.
        verdicts: ban.yaml.
    Returns:
        GuardResult.
    Refuses (BLOCK):
        - a flagged column whose verdict is keep_unreviewed, or keep without an evidence Part.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# ----------------------------------------------------------------------------------------- deep checks
# Provenance: plan 5 G-MISSING (deep: missingness per year; "absent groups only by store fact; any other
# missing FILE stops the run"); plan 2.4 R30; plan 3.2 and 3.3 flag 7 (columns all-NaN in most groups,
# inside files that exist, are FLAGGED for the Q34 review, never blocked); plan 6.1 check --deep.
def check_g_missing_deep(missing_share_by_group_year: Mapping[Tuple[str, str, int], float],
                         absent_groups: Mapping[str, Mapping[str, str]]) -> GuardResult:
    """G-MISSING (deep): missing shares per column x group x year, with store-declared absences
    separated. Report only.

    Rule: G-MISSING, R30.  Needed: Sat 10 Oct (check --deep green).

    Contract (plan 5 G-MISSING, 2.4 R30, 6.1):
        REPORT ONLY (FLAG or PASS, never BLOCK). The file-level stop lives in
        io_science.check_missing_files: a missing FILE stops the run unless its group is declared
        absent. A column that is all-NaN for a group inside files that exist is listed here (with
        store-declared absences shown apart) and feeds the R30 flags; G-MISSING (quick,
        check_g_missing) refuses it only when the flagged column has no keep-with-evidence or ban
        verdict.
    Inputs:
        missing_share_by_group_year: {(column, group, year): share missing before the 0-fill}.
        absent_groups: {column: its store's absent_groups}.
    Returns:
        GuardResult (FLAG with the share table and the all-missing groups in details, or PASS).
    Refuses:
        - nothing (report only).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-CADENCE (deep, ALL units); fake-monthly column (Part 549); a misread count column
# (pm25_ban.py:139-140); the constancy assert pm25_architecture.py:139-160.
def check_g_cadence(frame: pd.DataFrame, unit_codes: np.ndarray, steps: np.ndarray,
                    columns: Mapping[str, ColumnFacts], target_cadence: Cadence) -> GuardResult:
    """G-CADENCE: declared versus observed step on every unit; fake-fine columns refused.

    Rule: G-CADENCE.  Needed: Sat 10 Oct (check --deep green).

    Contract (plan 5 G-CADENCE):
        Each column's observed step is compared with its declared cadence on ALL units. A column
        constant within every unit x next-coarser period is refused as fake-fine. Annual joins
        happen after the constancy assert (io_science.join_coarser_column).
    Inputs:
        frame: column values on the dense grid (masked).
        unit_codes, steps: keys per row.
        columns: facts (declared cadence).
        target_cadence: R1.
    Returns:
        GuardResult.
    Refuses (BLOCK):
        - a declared cadence the data contradict; a fake-fine column.
    OWNER DECISION: "next-coarser period" per cadence -- propose month -> year, N-day composite ->
        month, year -> none (annual columns cannot be fake-fine).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-DERIVED (deep); plan 1.5; lags rebuilt at leads (Q33); history copied from the
# target row at a lead (Part 526).
def check_g_derived(columns: Mapping[str, ColumnFacts], script_values: pd.DataFrame, sample_rows: np.ndarray,
                    grid: DenseGrid, labels: LabelView, sources: pd.DataFrame,
                    adjacency: Optional[pd.DataFrame]) -> GuardResult:
    """G-DERIVED (recompute): every engineered column recomputed on a stride sample from its declaration.

    Rule: G-DERIVED, plan 1.5, G-LOCK.  Needed: Sat 10 Oct (check --deep green).

    Contract (plan 5 G-DERIVED, 1.5):
        io_science.recompute_declared_operation on stride-sampled rows must match the feature
        script's output; trailing only; target-derived columns use y strictly before their own row,
        read only through the label vault. Aggregations are included.
    Inputs:
        columns: facts of engineered columns (operation declarations).
        script_values: the feature script's outputs.
        sample_rows: stride-sampled row positions (no draw).
        grid: the keys-only dense grid.
        labels: the label vault (target-derived columns; built without a run folder at check time).
        sources, adjacency: what the recompute needs.
    Returns:
        GuardResult.
    Refuses (BLOCK):
        - any mismatch; an undeclared engineered column.
    OWNER DECISION: the stride sample size and the match tolerance (the plan names neither).
    OWNER DECISION: which rows a TARGET-derived column is sampled on. check --deep runs before any
        adoption exists, so a test-window row's recompute reads test-window labels before any lock.
        Follow the vault decision (LabelView.asof_rows): under (a) the sample spans every row;
        under (b) target-derived columns are sampled only on rows at or before the donor train end.
        Driver-derived columns are sampled on every row either way.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-DERIVED ("no model fitted on the target inside a feature script": a static scan for
# .fit and feature_importances_); plan 1.5 Forbidden list.
def scan_feature_script(source_text: str) -> GuardResult:
    """G-DERIVED (static): refuse a feature script that fits a model.

    Rule: G-DERIVED, plan 1.5.  Needed: Sat 10 Oct (check --deep green).

    Contract (plan 1.5, 5 G-DERIVED):
        A static scan of features/build.py for model fitting (.fit calls and feature_importances_).
    Inputs:
        source_text: the script's source.
    Returns:
        GuardResult.
    Refuses (BLOCK):
        - any match.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-HIST (runtime: "by a sample match").
def check_g_hist_sample(columns: Mapping[str, ColumnFacts], values: pd.DataFrame, grid: DenseGrid,
                        labels: LabelView, sample_rows: np.ndarray) -> GuardResult:
    """G-HIST (runtime): refuse any dataset column that MATCHES a lag or trailing mean of the unit's own
    target on a sample, whatever its declaration says.

    Rule: G-HIST, G-LOCK.  Needed: Mon 5 Oct (first package's features).

    Contract (plan 5 G-HIST, G-LOCK):
        Declarations can be wrong; the sample match catches an own-target copy. The own-target
        look-backs are read only through LabelView.asof_rows; the grid gives positions only.
    Inputs:
        columns: facts of dataset columns.
        values: their values on the sample rows.
        grid: the keys-only dense grid (positions).
        labels: the label vault (own target history).
        sample_rows: stride-sampled rows.
    Returns:
        GuardResult.
    Refuses (BLOCK):
        - a match.
    OWNER DECISION: which look-backs are tested (propose lags 0 to 3 and the R17 trailing windows),
        the match tolerance, and the sample rows (propose stride rows at or before the donor train
        end, so no test-window label is read before any adoption lock).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-CALENDAR (runtime); forecast_arms.py:127-171; row-shift lags across gaps
# (fire_architecture.py:273, 294-304); F1.
def check_g_calendar(read_unit: np.ndarray, read_time: np.ndarray, row_unit: np.ndarray, row_time: np.ndarray,
                     expected_back: Optional[int], is_events: bool) -> GuardResult:
    """G-CALENDAR: every look-back read is in the same unit and exactly where it should be.

    Rule: G-CALENDAR.  Needed: Sat 10 Oct (check --deep green; the lookup asserts from Wed 30 Sep).

    Contract (plan 5 G-CALENDAR):
        Grids: lags, rolls and history only through the dense-grid predecessor lookup, each read
        exactly L steps back in the same unit. Events: only through the as-of label view, each read
        in the same unit and dated before the issue date. Integer time only; no groupby.shift in the
        API (a test scans for it).
    Inputs:
        read_unit, read_time: the unit and time of each value read.
        row_unit, row_time: the unit and time (or issue date) of the row it served.
        expected_back: L for grid reads; None for event as-of reads.
        is_events: True for events.
    Returns:
        GuardResult.
    Refuses (BLOCK):
        - any read in another unit, at the wrong step, or dated at or after the issue date (events).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-SENTINEL (deep: flags known codes present but undeclared); the -2^31 poison in
# 47/133 regions; a derived near-sentinel missed by panel_sentinel.py:15-20; a provider float fill.
def check_g_sentinel_deep(frame: pd.DataFrame, columns: Mapping[str, ColumnFacts]) -> GuardResult:
    """G-SENTINEL (deep): known fill codes present but undeclared; near-sentinel magnitudes.

    Rule: G-SENTINEL.  Needed: Sat 10 Oct (check --deep green).

    Contract (plan 5 G-SENTINEL, 1.3):
        On raw (unmasked) values: flag any known provider fill code present in a column that does not
        declare it; flag abs >= 2^30 unless the column opts out. Masking itself happens at read
        (io_science.mask_sentinels).
    Inputs:
        frame: raw values.
        columns: facts (fill_values, near_sentinel_optout).
    Returns:
        GuardResult (FLAG; counts in details).
    Refuses:
        - nothing (flags); the read-time mask handles declared codes.
    OWNER DECISION: the list of "known codes" the deep scan looks for must be an engine constant
        (propose the common integer and float fill values, each with its origin comment).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-RANGE (deep); Kelvin columns; a density column at 368,684; negative predictions of a
# non-negative target.
def check_g_range(frame: pd.DataFrame, columns: Mapping[str, ColumnFacts], target: TargetFacts,
                  donor: DonorLabels) -> GuardResult:
    """G-RANGE: units and legal ranges on inputs and outputs; one unit per physical quantity.

    Rule: G-RANGE.  Needed: Sat 10 Oct (check --deep green).

    Contract (plan 5 G-RANGE, 1.3):
        Values outside each column's physical legal range are counted. The target's donor rows are
        checked against the cited range (the share outside and at the bounds is printed). One unit
        per physical quantity across columns. Output-side pre-clip rate and calibration ratio per arm
        come from metrics and are listed here.
    Inputs:
        frame: masked input values.
        columns: facts (units, legal_range).
        target: target facts.
        donor: donor labels at the nowcast fit cut (vault.LabelView.donor_labels).
    Returns:
        GuardResult.
    Refuses (BLOCK or FLAG -- see decision):
        - values outside a legal range; two units for one physical quantity.
    OWNER DECISION: refuse or flag an out-of-range input, and at what share (the plan gives no
        tolerance).
    OWNER DECISION: how a "physical quantity" is identified from UDUNITS strings (propose: UDUNITS
        dimension equality).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-JOIN (deep + runtime); the assembler reverting 49 columns while printing OK
# (Part 326).
def check_g_join(reports: Tuple[JoinReport, ...], column_set_ok: Mapping[str, bool]) -> GuardResult:
    """G-JOIN (deep): every join was 1:1 with an unchanged row count; every table's column set equals
    its catalog.

    Rule: G-JOIN.  Needed: Sat 10 Oct (check --deep green; runtime asserts from Tue 29 Sep).

    Contract (plan 5 G-JOIN):
        Re-reads the join reports of every file (deep) and the column-set results
        (io_science.check_column_set).
    Inputs:
        reports: every JoinReport of the deep pass.
        column_set_ok: {table: column set equals catalog}.
    Returns:
        GuardResult.
    Refuses (BLOCK):
        - any changed row count or column-set difference.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 5 G-LINEAGE ("deep flags reconstructions"); a sum-group member rebuilt from the others
# (defo_ban.py:28-34).
def flag_lineage_reconstructions(frame: pd.DataFrame, columns: Mapping[str, ColumnFacts],
                                 verdicts: Mapping[str, VerdictDecl]) -> GuardResult:
    """G-LINEAGE (deep): flag kept columns that reconstruct a banned one.

    Rule: G-LINEAGE.  Needed: Sat 10 Oct (check --deep green).

    Contract (plan 5 G-LINEAGE):
        Flags only (report); a flagged reconstruction then needs a verdict.
    Inputs:
        frame: masked values on a stride sample.
        columns: facts (sum_group).
        verdicts: ban.yaml.
    Returns:
        GuardResult (FLAG).
    Refuses:
        - nothing (flags).
    OWNER DECISION: the reconstruction test is not specified; propose checking declared sum groups
        only (a banned member recoverable as the group total minus the kept members).
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")
