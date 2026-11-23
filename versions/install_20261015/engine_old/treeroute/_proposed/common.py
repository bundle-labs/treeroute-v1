"""Shared PROPOSED types for the science signatures (owner approval pending).

Nothing here computes anything. Enums and frozen dataclasses name the shapes that the science
functions pass to each other. Field names follow plan Section 1.3 (column facts) and Section 2
(derived values). The package loader (package/schema.py, boilerplate, pydantic with extra='forbid')
builds these views from the package files. The owner reviews which fields are required there.

Shapes that several modules share live here, so every module imports them at run time and no
annotation depends on a TYPE_CHECKING-only import (typing.get_type_hints resolves every signature
in its own module): the keys-only dense grid, the target table as read, the label-free feature
source, the bank, and the layer's adoption records.

Module-wide.  Rule: all rules (shared shapes).  Needed: Tue 29 Sep (M1; with the first functions).
OWNER DECISION: approve these shapes together with the functions that use them. They are the
    contract between the science modules. The package schema must be able to fill every field.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Mapping, NewType, Optional, Protocol, Tuple, TypeVar

import numpy as np

# ------------------------------------------------------------------------------------------------
# Scalar aliases
# ------------------------------------------------------------------------------------------------
Step = NewType("Step", int)
"""Integer step index of a grid (R1). Never a timestamp (prevents the timestamp bug class, F1)."""

Day = NewType("Day", int)
"""A calendar day as a proleptic Gregorian ordinal (datetime.date.toordinal). Used for events."""

UnitId = NewType("UnitId", str)
GroupId = NewType("GroupId", str)


class Refusal(Exception):
    """Raised when a rule refuses. The message names the rule id, the columns, the fix and a Part
    number. The lesson text lives in docs/lessons.yaml, never in the message. The final exception
    type lives in boilerplate; this one is a stand-in for the signatures."""


# ------------------------------------------------------------------------------------------------
# Enums (plan 1.3, 1.4, Section 2)
# ------------------------------------------------------------------------------------------------
class CadenceKind(Enum):
    """Store fact 'cadence' (plan 1.3)."""
    REGULAR = "regular"                      # a regular step {length, unit}
    COMPOSITE_OF_YEAR = "composite_of_year"  # N-day composites that restart every 1 January
    STATIC = "static"
    EPOCH = "epoch"
    IRREGULAR = "irregular"                  # events


class StepUnit(Enum):
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


class CalendarPart(Enum):
    """Package fact on each key_time column (plan 1.3): which calendar part it holds."""
    YEAR = "year"
    MONTH = "month"
    DAY_OF_YEAR = "day_of_year"
    DATE = "date"


class Scope(Enum):
    UNIT = "unit"
    GLOBAL = "global"


class Stamp(Enum):
    PERIOD_START = "period_start"
    PERIOD_CENTRE = "period_centre"
    PERIOD_END = "period_end"
    EVENT_DATE = "event_date"


class Align(Enum):
    BACKWARD = "backward"
    CENTRED = "centred"
    FORWARD = "forward"
    UNKNOWN = "unknown"


class FactStatus(Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    ASSUMED = "assumed"          # signed by the owner


class Role(Enum):
    """Package fact 'role' (plan 1.3). A role in a store catalog is refused."""
    KEY_UNIT = "key_unit"
    KEY_GROUP = "key_group"
    KEY_TIME = "key_time"
    TARGET = "target"
    TARGET_TWIN = "target_twin"
    DRIVER = "driver"
    ROUTER_CONTEXT = "router_context"
    SUPPORT = "support"
    REPORT_STRATUM = "report_stratum"
    ENGINEERED = "engineered"
    EXTERNAL_PRODUCT = "external_product"


class Verdict(Enum):
    """Ban verdicts (plan 1.4). There is no 'lag' verdict."""
    KEEP = "keep"
    KEEP_UNREVIEWED = "keep_unreviewed"
    FREEZE = "freeze"
    BAN = "ban"
    CONDITIONAL = "conditional"
    WATCH = "watch"


class BanReason(Enum):
    LABEL = "label"
    COPRODUCT = "coproduct"
    TARGET_DERIVED = "target_derived"
    REPLACED_BY_ENGINE = "replaced_by_engine"
    POST_EVENT_STATE = "post_event_state"
    LOOKAHEAD_UNFIXABLE = "lookahead_unfixable"
    TREND_PROXY = "trend_proxy"
    INCOMPLETE = "incomplete"
    STRUCTURAL = "structural"
    POST_WINDOW_SNAPSHOT = "post_window_snapshot"


class OperationKind(Enum):
    """Declared feature-script operations (plan 1.5)."""
    LAG = "lag"
    TRAILING_MEAN = "trailing_mean"
    TRAILING_SUM = "trailing_sum"
    TRAILING_MIN = "trailing_min"
    TRAILING_MAX = "trailing_max"
    CUMULATIVE = "cumulative"
    YEARS_SINCE = "years_since"
    NEIGHBOUR_AGGREGATE = "neighbour_aggregate"
    AGGREGATE_TIME = "aggregate_time"
    AGGREGATE_SPACE = "aggregate_space"


class AggStat(Enum):
    MEAN = "mean"
    MIN = "min"
    MAX = "max"
    SUM = "sum"


class RouterKind(Enum):
    """R12 outcome."""
    PER_UNIT = "per_unit"
    REGION = "region"
    NEIGHBOUR = "neighbour"


class SurfaceKind(Enum):
    """R13 outcome."""
    INNER_WINDOW = "inner_window"
    DONOR_FOLDS = "donor_folds"


class FoldPurpose(Enum):
    """Why a donor-fold FitContext exists (R13 and plan 1.6 are separate uses)."""
    DECISION_SURFACE = "decision_surface"    # R13 neighbour folds, cut at the inner-fit end
    TYPE3 = "type3"                          # plan 1.6 donor_fold_predict, cut at the parent's cut


class SeasonKeyKind(Enum):
    """R2 outcome."""
    MONTH_OF_YEAR = "month_of_year"
    COMPOSITE_NUMBER = "composite_number"
    STEP_POSITION_IN_YEAR = "step_position_in_year"
    CONSTANT = "constant"            # annual data: one class
    EVENT_MONTH = "event_month"      # events: month of the event date


class ReferenceKind(Enum):
    """R8 reference instant."""
    NOWCAST = "nowcast"              # end of the target's own window
    ISSUE_STEP = "issue_step"        # end of the issue step (lead >= 1); events: the issue date


class LeadUnit(Enum):
    STEPS = "steps"
    DAYS = "days"


class CutKind(Enum):
    FIT = "fit"                      # the lead's fit cut (R11)
    GUARD = "guard"                  # the inner guard's cut (R11)


class Link(Enum):
    """R22 link set."""
    IDENTITY = "identity"
    LOG_C = "log_c"                  # log(y + c), c from R23
    ARCSINE = "arcsine"              # only with a finite legal upper bound


class Tool(Enum):
    """R24 arm tools."""
    PLAIN = "plain"
    CORRECTOR = "corrector"
    PLACEBO_CORRECTOR = "placebo_corrector"   # scrambled residual, never selectable
    TREES_OFF = "trees_off"                   # intercept + normal only (R16)


class Weighting(Enum):
    UNWEIGHTED = "unweighted"
    GLS = "gls"


class SeedRole(Enum):
    """R19: the three seeds of each tree."""
    BAG = "bag"
    TREE = "tree"
    CORRECTOR = "corrector"


class GuardStatus(Enum):
    PASS = "pass"
    FLAG = "flag"                    # report only, never a choice
    BLOCK = "block"                  # stops the run


class VerdictTag(Enum):
    """Single-verdict outcomes (R34, G-DECIDE)."""
    HELPS = "helps"
    HURTS = "hurts"
    EQUIVALENT = "does_not_help_equivalent"
    CANNOT_TELL = "cannot_tell"
    IDENTICAL = "identical"
    DECLINED = "declined"


class RunKind(Enum):
    """Stamped on every score line (plan 7.1). Only the headline-table builder refuses a kind."""
    HEADLINE = "headline"
    SMOKE = "smoke"
    LEGACY = "legacy"


# ------------------------------------------------------------------------------------------------
# Facts (plan 1.3). Resolved views: store facts + package facts for one column.
# ------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Cadence:
    """Store fact 'cadence'. length/unit for REGULAR; composites_per_year and composite_days for
    COMPOSITE_OF_YEAR; all None for STATIC, EPOCH and IRREGULAR."""
    kind: CadenceKind
    length: Optional[int] = None
    unit: Optional[StepUnit] = None
    composites_per_year: Optional[int] = None
    composite_days: Optional[int] = None


@dataclass(frozen=True)
class Window:
    """Store fact 'window' (or the target's own window, a package fact). An index whose smoothing
    cannot be found is declared align=UNKNOWN with max_length and fact_status=ASSUMED (signed)."""
    length: Optional[int]
    unit: Optional[StepUnit]
    align: Align
    max_length: Optional[int] = None
    fact_status: FactStatus = FactStatus.UNVERIFIED


@dataclass(frozen=True)
class OperationDecl:
    """Declaration of one engineered column (plan 1.5)."""
    kind: OperationKind
    sources: Tuple[str, ...]
    window: Optional[int] = None
    window_unit: Optional[StepUnit] = None
    stat: Optional[AggStat] = None
    k: Optional[int] = None                    # lag k
    unit_map: Optional[str] = None             # aggregate_space / neighbour aggregate
    adjacency: Optional[str] = None
    season_months: Optional[Tuple[int, ...]] = None   # aggregate_time to a growing season


@dataclass(frozen=True)
class DataSelected:
    """Package fact 'data_selected' (plan 1.3) for a column list chosen from data."""
    method: str
    rows: int
    latest_date: _dt.date
    groups: Tuple[str, ...]


@dataclass(frozen=True)
class ColumnFacts:
    """Every fact about one non-key column: store facts (physical, shared) plus package facts
    (problem-relative). Field meanings are exactly plan 1.3."""
    name: str
    dtype: str
    units: str
    cadence: Cadence
    scope: Scope
    stamp: Stamp
    window: Window
    legal_range: Tuple[float, float]
    fill_values: Tuple[float, ...]
    near_sentinel_optout: bool
    product_family: Optional[str]
    lineage_assimilates: Tuple[str, ...]
    lineage_trained_on: Tuple[str, ...]
    sum_group: Optional[str]
    content_epoch: Optional[_dt.date]
    observed_through: Optional[_dt.date]
    release_date: Optional[_dt.date]
    snapshot_date: Optional[_dt.date]
    baseline_period: Optional[Tuple[int, int]]
    absent_groups: Mapping[str, str]
    derived_from: Tuple[str, ...]
    operation: Optional[OperationDecl]
    reads_target: bool
    fact_status: FactStatus
    reviewed_by: Optional[str]
    role: Role
    co_measured_with_target: Optional[bool]
    co_measured_part: Optional[int]
    data_selected: Optional[DataSelected]


@dataclass(frozen=True)
class TargetFacts:
    """Package facts of the one target column (plan 1.3)."""
    name: str
    legal_range: Tuple[float, float]
    legal_range_source: str
    cadence: Cadence
    stamp: Stamp
    window: Window
    time_columns: Mapping[str, CalendarPart]
    measurement_error_floor: Optional[float]
    calibration_through: Optional[int]
    computed_from: Tuple[str, ...]
    product_family: Optional[str]


@dataclass(frozen=True)
class VerdictDecl:
    """One ban.yaml entry (plan 1.4), aligned with package/schema.py: every verdict carries a
    free-text reason; for a ban the reason is exactly one BanReason value, parsed into ban_reason
    (None for every other verdict); evidence is a Part number (see validators.check_g_closed for
    whether keep_unreviewed needs one)."""
    column: str
    verdict: Verdict
    reason: str
    ban_reason: Optional[BanReason]
    evidence_part: Optional[int]


@dataclass(frozen=True)
class SplitSets:
    """split.yaml (plan 1.2). Lists are sets; the engine sorts them by name."""
    donor_groups: Tuple[str, ...]
    test_groups: Tuple[str, ...]
    excluded: Mapping[str, str]
    seen_during_design: Tuple[str, ...]


@dataclass(frozen=True)
class ExceptionEntry:
    """One exceptions.yaml entry (plan 1.2): provenance flags, disclosed defects and test-exposure
    disclosures only. It can never relax a time rule, hold a timing value or set a derived value."""
    check_or_column: str
    decision: str
    reason: str
    owner: str
    date: _dt.date


# ------------------------------------------------------------------------------------------------
# Data shapes shared across modules (plan 1.2, 4.1 step 3)
# ------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class TargetTable:
    """The target table as read by the boilerplate reader (plan 1.2): keys, time columns and y, one
    row per unit x step (grids) or per visit (events). Its y is handed ONLY to vault.LabelView
    (G-LOCK). Every other consumer reads keys (io_science.build_dense_grid), validity
    (LabelView.validity) or donor labels (LabelView.donor_labels) from the vault."""
    unit_ids: np.ndarray
    group_ids: np.ndarray
    time_columns: Mapping[str, np.ndarray]
    y: np.ndarray


@dataclass(frozen=True)
class DenseGrid:
    """KEYS ONLY: every unit x step inside the coverage, not only labelled rows (plan 2.4 R30, 4.1
    step 3). It holds no label and no feature: labels live only in vault.LabelView, features only in
    a FeatureSource. Units are sorted by id; grid position of (unit r, step first_step + j) is
    r x n_steps + j (unit by unit, step order, the tree-answer store's row order)."""
    unit_ids: Tuple[str, ...]
    group_of_unit: Tuple[str, ...]
    first_step: Step
    n_steps: int


class FeatureSource(Protocol):
    """The joined feature pool on the dense grid (plan 4.1 step 3: sentinels masked, 1:1 joins,
    computed lags, verdicts and freezes applied; the out-of-core pool reader, boilerplate). Rows are
    addressed by dense-grid position. It holds NO target label, so reading it can never leak one."""
    tree_columns: Tuple[str, ...]
    context_columns: Tuple[str, ...]

    def tree_features(self, grid_rows: np.ndarray) -> np.ndarray:
        """Kept tree features on the given grid rows, float32, NaN kept (the R30 0-fill is applied
        by FitContext and the tree-answer store, never here)."""
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")

    def context(self, grid_rows: np.ndarray) -> np.ndarray:
        """router_context columns on the given grid rows, float32, NaN kept."""
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# ------------------------------------------------------------------------------------------------
# Derived values (Section 2)
# ------------------------------------------------------------------------------------------------
T = TypeVar("T")


@dataclass(frozen=True)
class Derived(Generic[T]):
    """One derived.json entry: the value, the inputs it read (with hashes) and its margin to each
    threshold. A value within 20% of a threshold carries the flag 'borderline' (report only)."""
    rule_id: str
    value: T
    inputs: Mapping[str, Any]
    input_hashes: Mapping[str, str]
    margins: Mapping[str, float]
    flags: Tuple[str, ...]


@dataclass(frozen=True)
class SeasonKeySpec:
    """R2 outcome."""
    kind: SeasonKeyKind
    steps_per_year: Optional[int]      # None for events


@dataclass(frozen=True)
class TestWindowPlan:
    """R5 outcome: the test years and the inner-score length the short-record ladder leaves."""
    test_years: Tuple[int, ...]
    inner_score_years: int
    ladder_steps: Tuple[str, ...]      # e.g. ('short record: inner score 2',)


@dataclass(frozen=True)
class Windows:
    """R3-R7 together."""
    y0: int
    y_end: int
    test_years: Tuple[int, ...]
    train_end: int
    inner_fit: Tuple[int, int]         # first and last year, inclusive
    inner_score: Tuple[int, ...]


@dataclass(frozen=True)
class Lag:
    """R8: one fixed lag per column, counted in the column's OWN steps (see timing.compute_lag)."""
    column: str
    steps: int
    column_cadence: Cadence
    floor_reason: Optional[str]        # 'co_measured' or 'computed_from' when the 1-step floor bit


@dataclass(frozen=True)
class LeadPlan:
    """R10 outcome."""
    requested_months: Tuple[int, ...]
    leads: Tuple[int, ...]             # in steps (grids) or days (events); lead 0 not listed
    lead_unit: LeadUnit
    merged: Mapping[int, Tuple[int, ...]]   # lead -> the requested months that merged into it
    not_supplied: Tuple[int, ...]      # requested months that rounded to 0 steps
    contract_lead_zero: bool           # always True: lead 0 runs as the contract


@dataclass(frozen=True)
class CutPair:
    """R11: both cuts of one lead, in steps (grids) or days (events)."""
    lead: int
    lead_unit: LeadUnit
    fit_cut: int
    guard_cut: int


@dataclass(frozen=True)
class GridPoint:
    """One penalty grid point (R14). ratio is None on the region grid and on a context-free grid."""
    level: float
    ratio: Optional[float]


@dataclass(frozen=True)
class RouterDesign:
    """R14 outcome: column layout, which blocks are penalised, the grid and any fit-row cap."""
    kind: RouterKind
    columns: Tuple[str, ...]           # block names in order, e.g. intercept, normal, context, trees
    unpenalised: Tuple[str, ...]
    centre: Tuple[float, ...]          # penalty centre(s) from engine constants (C12)
    grid: Tuple[GridPoint, ...]
    fit_row_cap: Optional[int]         # region only (C7)


@dataclass(frozen=True)
class HistorySpec:
    """R17 outcome."""
    columns: Tuple[str, ...]
    last_values: int                   # 3
    trailing_steps: Tuple[int, ...]    # (1 year, 5 years) counted in steps; grids
    trailing_days: Tuple[int, ...]     # (365, 1826) for events with repeat visits
    all_history_mean: bool
    start_offset_steps: int            # extra steps back when the target window reaches past its step
    dropped_duplicates: Tuple[str, ...]


@dataclass(frozen=True)
class ArmSpec:
    """One Type-2 candidate (R24)."""
    link: Link
    tool: Tool
    weighting: Weighting
    selectable: bool                   # False for placebo and trees-off


@dataclass(frozen=True)
class GuardResult:
    """What every validator returns. Messages print a rule id, the columns, the fix and a Part."""
    rule_id: str
    status: GuardStatus
    columns: Tuple[str, ...]
    reason: str
    fix: str
    part: Optional[int]
    details: Mapping[str, Any]


@dataclass(frozen=True)
class BankManifest:
    """What every bank (fold banks included) carries for G-DISJOINT: the groups, units and label
    times it saw, and the cut it was fitted at."""
    bank_fingerprint: str
    groups: Tuple[str, ...]
    unit_ids_hash: str
    n_units: int
    min_label_time: int
    max_label_time: int
    cut: int
    cut_kind: CutKind
    lead: int
    held_out_fold: Tuple[str, ...]     # empty unless a fold bank


@dataclass(frozen=True)
class FitCtxLogRow:
    """One fitctx_log.parquet row (G-FITCUT): every fitted object's cut, max label time and
    row-key hash."""
    object_kind: str                   # bank, corrector, placebo, router, normal, c, fill, scaler,
    purpose: str                       # gls, phi, type3_blind ...
    lead: int
    cut_kind: CutKind
    cut: int
    max_label_time: int
    n_rows: int
    groups_hash: str
    row_key_hash: str
    fold: Optional[int]
    fold_purpose: Optional[FoldPurpose]


# ------------------------------------------------------------------------------------------------
# Protocols for objects owned by boilerplate modules (listed so the science signatures can name them)
# ------------------------------------------------------------------------------------------------
class FittedTree(Protocol):
    """A fitted tree, corrector or forest (sklearn object). Owned by fit/ (boilerplate storage)."""

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Answer for each row of X."""
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


class TreeAnswerStore(Protocol):
    """The row-keyed tree-answer store (plan 4.5, boilerplate gated by byte identity). Keyed by bank
    fingerprint + table kind (plain, corrector, placebo) + row key. Built once per row."""

    def answers(self, row_keys: np.ndarray, table_kind: Tool) -> np.ndarray:
        """Every tree's answer for the given rows, float32, shape (rows, trees), rows in the order
        given."""
        raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


class PackageView(Protocol):
    """The loaded, fingerprinted package (package/load.py, boilerplate)."""
    target: TargetFacts
    columns: Mapping[str, ColumnFacts]
    verdicts: Mapping[str, VerdictDecl]
    split: SplitSets
    exceptions: Tuple[ExceptionEntry, ...]
    fingerprint: str


# ------------------------------------------------------------------------------------------------
# The bank (R19; built by bank_recipe.fit_donor_bank, returned by FitContext.fit_bank)
# ------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Bank:
    """A fitted bank. trees[i] belongs to donor tree_group[i] with tree number tree_number[i];
    correctors[i] and placebo_correctors[i] are None when the tree had too few out-of-bag rows."""
    trees: Tuple[FittedTree, ...]
    correctors: Tuple[Optional[FittedTree], ...]
    placebo_correctors: Tuple[Optional[FittedTree], ...]
    tree_group: Tuple[str, ...]
    tree_number: Tuple[int, ...]
    oob_share: Mapping[str, float]
    manifest: BankManifest


# ------------------------------------------------------------------------------------------------
# Layer outcomes (R26, R27, R29; built in layer.py, locked by vault.py)
# ------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class PenaltyPick:
    """R26 outcome for one arm."""
    arm: ArmSpec
    point: Optional[GridPoint]         # None for trees-off
    mae: float
    mae_by_point: Mapping[GridPoint, float]
    edge: bool


@dataclass(frozen=True)
class Adoption:
    """R27 outcome, the content of adoption.json (the nowcast pass)."""
    adopted: Optional[ArmSpec]         # None = declined to the decline target
    penalty: Optional[GridPoint]
    declined: bool
    best_tree_arm: ArmSpec
    best_tree_penalty: GridPoint
    eligible: Tuple[ArmSpec, ...]
    surface_mae: Mapping[str, float]   # every candidate, trees-off included
    beside: Mapping[str, float]        # predict-zero MAE, corr2 per arm (printed, never used)


@dataclass(frozen=True)
class LeadAdoption:
    """R29 outcome at one lead: the content of that lead's adoption file."""
    lead: int
    pinned: ArmSpec
    penalty: GridPoint
    guard_passed: bool
    adopted: Optional[ArmSpec]         # None = declined at this lead
    placebo_built: bool                # True only at the longest lead
