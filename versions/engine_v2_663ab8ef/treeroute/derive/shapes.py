"""Shapes the derive rules return: FIELD-IDENTICAL engine copies of the approved shared shapes.

The approved shapes are drafted in the proposed signatures' common module, which engine code may not
import (G-IMPORT). Until they get their engine home, this module holds copies of the records and enums
the derive rules build (tests/test_derive_shapes.py checks every field and member against that source
by parsing it). The timing records (Lag, CutPair) are the timing package's own copies, re-exported.

Inputs are read by attribute name (duck typing), and enum-valued facts are compared by their value
string, so a rule accepts these enums, the approved enums, the package schema's plain strings or any
object with the same field names.

Copies from other approved sources: RouterKind, GridPoint, RouterDesign and HistorySpec (the common
module); LoroSurfaceKind (the LORO additions); MissingShares (the derive_rules module); DonorLabels
(the vault module). The router's own copies of RouterKind, GridPoint and RouterDesign live in
route/kinds.py; values are compared by field and enum value, never by class identity.

One record here is NOT an approved shape: CutDays, the day form of R11's cuts that R9 reads (the
approved R9 signature takes the cuts but no calendar, and a freeze epoch is a day; see
derive.rules.cut_days). It is flagged for the owner.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Mapping, Optional, Tuple, TypeVar

import numpy as np

from treeroute.timing.shapes import CutPair, Lag

__all__ = ["CadenceKind", "StepUnit", "CalendarPart", "SeasonKeyKind", "LeadUnit", "Link", "CutKind",
           "Cadence", "Derived", "SeasonKeySpec", "TestWindowPlan", "Windows", "LeadPlan", "Lag",
           "CutPair", "RouterKind", "GridPoint", "RouterDesign", "HistorySpec", "LoroSurfaceKind",
           "MissingShares", "DonorLabels", "CutDays"]


class CadenceKind(Enum):
    """Store fact 'cadence' (plan 1.3)."""
    REGULAR = "regular"
    COMPOSITE_OF_YEAR = "composite_of_year"
    STATIC = "static"
    EPOCH = "epoch"
    IRREGULAR = "irregular"


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


class SeasonKeyKind(Enum):
    """R2 outcome."""
    MONTH_OF_YEAR = "month_of_year"
    COMPOSITE_NUMBER = "composite_number"
    STEP_POSITION_IN_YEAR = "step_position_in_year"
    CONSTANT = "constant"
    EVENT_MONTH = "event_month"


class LeadUnit(Enum):
    STEPS = "steps"
    DAYS = "days"


class CutKind(Enum):
    FIT = "fit"
    GUARD = "guard"


class Link(Enum):
    """R22 link set."""
    IDENTITY = "identity"
    LOG_C = "log_c"
    ARCSINE = "arcsine"


@dataclass(frozen=True)
class Cadence:
    """Store fact 'cadence'. length/unit for REGULAR; composites_per_year and composite_days for
    COMPOSITE_OF_YEAR; all None for STATIC, EPOCH and IRREGULAR."""
    kind: CadenceKind
    length: Optional[int] = None
    unit: Optional[StepUnit] = None
    composites_per_year: Optional[int] = None
    composite_days: Optional[int] = None


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
    steps_per_year: Optional[int]


@dataclass(frozen=True)
class TestWindowPlan:
    """R5 outcome: the test years and the inner-score length the short-record ladder leaves."""
    __test__ = False                   # not a pytest test class, whatever its name says
    test_years: Tuple[int, ...]
    inner_score_years: int
    ladder_steps: Tuple[str, ...]


@dataclass(frozen=True)
class Windows:
    """R3-R7 together."""
    y0: int
    y_end: int
    test_years: Tuple[int, ...]
    train_end: int
    inner_fit: Tuple[int, int]
    inner_score: Tuple[int, ...]


@dataclass(frozen=True)
class LeadPlan:
    """R10 outcome."""
    requested_months: Tuple[int, ...]
    leads: Tuple[int, ...]
    lead_unit: LeadUnit
    merged: Mapping[int, Tuple[int, ...]]
    not_supplied: Tuple[int, ...]
    contract_lead_zero: bool


class RouterKind(Enum):
    """R12 outcome."""
    PER_UNIT = "per_unit"
    REGION = "region"
    NEIGHBOUR = "neighbour"


class LoroSurfaceKind(Enum):
    """R13 outcome under LORO (replaces the common module's SurfaceKind for the neighbour kind)."""
    INNER_WINDOW = "inner_window"
    LEAVE_ONE_GROUP_OUT = "leave_one_group_out"


@dataclass(frozen=True)
class GridPoint:
    """One penalty grid point (R14). ratio is None on the region grid and on a context-free grid."""
    level: float
    ratio: Optional[float]


@dataclass(frozen=True)
class RouterDesign:
    """R14 outcome: column layout, which blocks are penalised, the grid and any fit-row cap."""
    kind: RouterKind
    columns: Tuple[str, ...]
    unpenalised: Tuple[str, ...]
    centre: Tuple[float, ...]
    grid: Tuple[GridPoint, ...]
    fit_row_cap: Optional[int]


@dataclass(frozen=True)
class HistorySpec:
    """R17 outcome."""
    columns: Tuple[str, ...]
    last_values: int
    trailing_steps: Tuple[int, ...]
    trailing_days: Tuple[int, ...]
    all_history_mean: bool
    start_offset_steps: int
    dropped_duplicates: Tuple[str, ...]


@dataclass(frozen=True)
class MissingShares:
    """R30 inputs, measured by the boilerplate column reader over ONE declared donor row set (a
    DonorLabels), so the rows behind every share are traceable."""
    donor_row_key_hash: str
    donor_unit_scope: str
    donor_training_missing_share: Mapping[str, float]
    donor_training_zero_share: Mapping[str, float]
    test_year_missing_share: Mapping[Tuple[str, int], float]


@dataclass(frozen=True)
class DonorLabels:
    """Label-only donor view: rows with valid labels at or before one cut whose own label window has
    ended by then, with no features. Under LORO the donor groups are every group; unit_scope is
    'picked' (every group's BANK units) or 'all_donor_units' (every candidate unit, R18's event
    rate only)."""
    groups: Tuple[str, ...]
    cut: int
    cut_kind: CutKind
    lead: int
    unit_scope: str
    unit_ids: np.ndarray
    times: np.ndarray
    group_of_row: np.ndarray
    y: np.ndarray
    row_key_hash: str


@dataclass(frozen=True)
class CutDays:
    """NOT an approved shape (flagged for the owner): one lead's two cuts as Day ordinals, the form
    R9 compares content epochs with. Grids: the last day of the cut step (derive.rules.cut_days);
    events: the cut days themselves."""
    lead: int
    lead_unit: LeadUnit
    fit_cut_day: int
    guard_cut_day: int
