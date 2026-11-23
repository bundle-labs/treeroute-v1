"""Fact builders for the timing tests, on MIRRORS of the approved shared shapes.

The approved shapes are drafted in treeroute/_proposed/common.py. The tests may not import that module:
loading proposed code into the test process makes the run manifest refuse (G-FINGERPRINT), rightly.
So this file mirrors the shapes the timing rules read, field for field, and
test_mirrors_match_the_approved_shapes checks the mirrors against common.py by PARSING its source.
The timing rules read facts by attribute name, so a field-identical mirror exercises exactly the
contract. RWindow is the approved Window plus the two reach facts the owner ruled in (part B item 8
(a)); the shared Window gains them when the shapes move into the engine.
"""

import ast
import datetime as dt
from dataclasses import dataclass, fields
from enum import Enum
from types import SimpleNamespace
from typing import Any, Mapping, Optional, Tuple

from conftest import TREEROUTE_DIR
from treeroute.timing import Reach


class CadenceKind(Enum):
    REGULAR = "regular"
    COMPOSITE_OF_YEAR = "composite_of_year"
    STATIC = "static"
    EPOCH = "epoch"
    IRREGULAR = "irregular"


class StepUnit(Enum):
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


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
    ASSUMED = "assumed"


class Role(Enum):
    DRIVER = "driver"


class ReferenceKind(Enum):
    NOWCAST = "nowcast"
    ISSUE_STEP = "issue_step"


class LeadUnit(Enum):
    STEPS = "steps"
    DAYS = "days"


@dataclass(frozen=True)
class Cadence:
    kind: CadenceKind
    length: Optional[int] = None
    unit: Optional[StepUnit] = None
    composites_per_year: Optional[int] = None
    composite_days: Optional[int] = None


@dataclass(frozen=True)
class Window:
    length: Optional[int]
    unit: Optional[StepUnit]
    align: Align
    max_length: Optional[int] = None
    fact_status: FactStatus = FactStatus.UNVERIFIED


@dataclass(frozen=True)
class ColumnFacts:
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
    content_epoch: Any
    observed_through: Any
    release_date: Any
    snapshot_date: Any
    baseline_period: Any
    absent_groups: Mapping[str, str]
    derived_from: Tuple[str, ...]
    operation: Any
    reads_target: bool
    fact_status: FactStatus
    reviewed_by: Optional[str]
    role: Role
    co_measured_with_target: Optional[bool]
    co_measured_part: Optional[int]
    data_selected: Any


@dataclass(frozen=True)
class TargetFacts:
    name: str
    legal_range: Tuple[float, float]
    legal_range_source: str
    cadence: Cadence
    stamp: Stamp
    window: Window
    time_columns: Mapping[str, Any]
    measurement_error_floor: Optional[float]
    calibration_through: Optional[int]
    computed_from: Tuple[str, ...]
    product_family: Optional[str]


@dataclass(frozen=True)
class Windows:
    y0: int
    y_end: int
    test_years: Tuple[int, ...]
    train_end: int
    inner_fit: Tuple[int, int]
    inner_score: Tuple[int, ...]


@dataclass(frozen=True)
class LeadPlan:
    requested_months: Tuple[int, ...]
    leads: Tuple[int, ...]
    lead_unit: LeadUnit
    merged: Mapping[int, Tuple[int, ...]]
    not_supplied: Tuple[int, ...]
    contract_lead_zero: bool


C = SimpleNamespace(CadenceKind=CadenceKind, StepUnit=StepUnit, Scope=Scope, Stamp=Stamp,
                    Align=Align, FactStatus=FactStatus, Role=Role, ReferenceKind=ReferenceKind,
                    LeadUnit=LeadUnit, Cadence=Cadence, Window=Window, ColumnFacts=ColumnFacts,
                    TargetFacts=TargetFacts, Windows=Windows, LeadPlan=LeadPlan)
MIRRORED_DATACLASSES = (Cadence, Window, ColumnFacts, TargetFacts, Windows, LeadPlan)
MIRRORED_ENUMS = (CadenceKind, StepUnit, Scope, Stamp, Align, FactStatus, ReferenceKind, LeadUnit)

MONTH = C.Cadence(C.CadenceKind.REGULAR, length=1, unit=C.StepUnit.MONTH)
YEAR = C.Cadence(C.CadenceKind.REGULAR, length=1, unit=C.StepUnit.YEAR)
DAILY = C.Cadence(C.CadenceKind.REGULAR, length=1, unit=C.StepUnit.DAY)
QUARTER = C.Cadence(C.CadenceKind.REGULAR, length=3, unit=C.StepUnit.MONTH)
EVENTS = C.Cadence(C.CadenceKind.IRREGULAR)
STATIC = C.Cadence(C.CadenceKind.STATIC)
EPOCH = C.Cadence(C.CadenceKind.EPOCH)


def composite(days, per_year=None):
    return C.Cadence(C.CadenceKind.COMPOSITE_OF_YEAR, composites_per_year=per_year,
                     composite_days=days)


@dataclass(frozen=True)
class RWindow(C.Window):
    """The approved Window with the ruled reach facts."""
    reach_after_max: Optional[Reach] = None
    reach_before_max: Optional[Reach] = None


A = C.Align
U = C.StepUnit
S = C.Stamp


def win(length=None, unit=U.MONTH, align=A.CENTRED, max_length=None,
        status=C.FactStatus.UNVERIFIED, after=None, before=None):
    return RWindow(length=length, unit=unit, align=align, max_length=max_length,
                   fact_status=status, reach_after_max=after, reach_before_max=before)


PLAIN_MONTH = win(1, U.MONTH, A.BACKWARD)           # store spelling: period_end + 1 month backward
CENTRED_MONTH = win(1, U.MONTH, A.CENTRED)          # audit spelling: period_centre + 1 month centred
PLAIN_YEAR = win(1, U.YEAR, A.BACKWARD)


def column(name, cadence=MONTH, stamp=S.PERIOD_END, window=PLAIN_MONTH, co_measured=None,
           fact_status=C.FactStatus.UNVERIFIED):
    return C.ColumnFacts(
        name=name, dtype="float32", units="1", cadence=cadence, scope=C.Scope.UNIT, stamp=stamp,
        window=window, legal_range=(0.0, 1.0), fill_values=(), near_sentinel_optout=False,
        product_family=None, lineage_assimilates=(), lineage_trained_on=(), sum_group=None,
        content_epoch=None, observed_through=None, release_date=None, snapshot_date=None,
        baseline_period=None, absent_groups={}, derived_from=(), operation=None,
        reads_target=False, fact_status=fact_status, reviewed_by=None, role=C.Role.DRIVER,
        co_measured_with_target=co_measured, co_measured_part=None, data_selected=None)


def target(name="y", cadence=MONTH, stamp=S.PERIOD_END, window=PLAIN_MONTH, computed_from=()):
    return C.TargetFacts(
        name=name, legal_range=(0.0, 1.0), legal_range_source="a documented valid range",
        cadence=cadence, stamp=stamp, window=window, time_columns={},
        measurement_error_floor=None, calibration_through=None,
        computed_from=tuple(computed_from), product_family=None)


def day(y, m, d):
    return dt.date(y, m, d).toordinal()


def month_period(y, m):
    first = dt.date(y, m, 1)
    nxt = dt.date(y + (m == 12), m % 12 + 1, 1)
    return first.toordinal(), nxt.toordinal() - 1


def year_period(y):
    return day(y, 1, 1), day(y, 12, 31)


# ---- the targets of the four packages, with the facts the rulings of 2026-09-28 sign ----
MONTHLY_TARGET = target()                                              # one calendar month
ANNUAL_TARGET = target(cadence=YEAR, window=PLAIN_YEAR)               # one calendar year
# V11 (MOD13C2): the month plus up to 15 days on each side (INDEX_WINDOW_AUDIT.md T9; ruling item 8)
REACH_TARGET = target(stamp=S.PERIOD_CENTRE,
                      window=win(1, after=Reach(15, "day"), before=Reach(15, "day")))


def detection_target(after):
    """A monthly burned-area target whose detection looks past the month end (ruling R-D (b)):
    the month plus a signed reach-after bound."""
    return target(window=win(1, U.MONTH, A.BACKWARD, after=after))


# ---------------------------------------------------------------------------------------------------
def _approved_shapes():
    """{class name: (field names in order, {member: value})} parsed from _proposed/common.py."""
    tree = ast.parse((TREEROUTE_DIR / "_proposed" / "common.py").read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        names = [n.target.id for n in node.body
                 if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)]
        members = {n.targets[0].id: n.value.value for n in node.body
                   if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                   and isinstance(n.targets[0], ast.Name)}
        out[node.name] = (names, members)
    return out


def test_mirrors_match_the_approved_shapes():
    approved = _approved_shapes()
    for cls in MIRRORED_DATACLASSES:
        assert [f.name for f in fields(cls)] == approved[cls.__name__][0], cls.__name__
    for enum in MIRRORED_ENUMS:
        approved_members = approved[enum.__name__][1]
        for member in enum:
            assert approved_members[member.name] == member.value, (enum.__name__, member.name)
        if enum is not Role:
            assert len(approved_members) == len(enum), enum.__name__
    assert approved["Lag"][0] == ["column", "steps", "column_cadence", "floor_reason"]
    assert approved["CutPair"][0] == ["lead", "lead_unit", "fit_cut", "guard_cut"]


def test_timing_records_match_the_approved_shapes():
    from treeroute.timing import CutPair, Lag
    approved = _approved_shapes()
    assert [f.name for f in fields(Lag)] == approved["Lag"][0]
    assert [f.name for f in fields(CutPair)] == approved["CutPair"][0]


def test_builders_make_the_mirrored_shapes():
    col = column("x")
    assert isinstance(col, ColumnFacts) and isinstance(col.window, Window)
    assert isinstance(MONTHLY_TARGET, TargetFacts)
    assert REACH_TARGET.window.reach_after_max == Reach(15, "day")


def test_period_helpers():
    assert month_period(2020, 2) == (day(2020, 2, 1), day(2020, 2, 29))
    assert month_period(2019, 12) == (day(2019, 12, 1), day(2019, 12, 31))
    assert year_period(2019) == (day(2019, 1, 1), day(2019, 12, 31))
