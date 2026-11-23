"""Pydantic v2 models for the dataset package files (plan Section 1).

Structure only: which keys exist, their types and their allowed values. Every model forbids unknown
keys (``extra='forbid'``). The semantic guards that read these files (G-CLOSED, G-LAG, G-SPLIT,
G-SUPPORT, G-FACTS, ...) are science validators and are NOT here; they come after the owner signs
their signatures.

G-NOKNOB (closed doors, plan 1.7): a key that is not a declared field of its model and names a
derived setting is refused with "derived: see derived.json, rule Rn". A declared field is part of
the owner-reviewed schema and is never refused by that check, so a physical fact such as a store
column's ``units`` is accepted where it is declared and refused anywhere else.

Numbers are strict: a number field takes a YAML number as written (an integer is accepted where a
float is expected) and refuses a string, a boolean or, for an integer field, a float. So '8' or
8.0 never becomes 8 silently. Ranges must be ordered (min <= max).

Written for pydantic 2.x (2.13 installed) on Python 3.9: annotations use ``typing`` generics.
"""

import re
from typing import Annotated, Any, ClassVar, Dict, List, Literal, Optional, Tuple

import pydantic

if int(pydantic.VERSION.split(".")[0]) < 2:
    raise ImportError("treeroute's package schema needs pydantic 2.x; found %s" % pydantic.VERSION)

from pydantic import (AfterValidator, BaseModel, ConfigDict, Field, Strict, StrictBool,  # noqa: E402
                      StrictInt, model_validator)

# ---------------------------------------------------------------------------------------------------
# G-NOKNOB: keys that name a derived setting, with the rule that derives it.
# Matching is on whole tokens of the key (split on '_', '-', '.', spaces and camelCase), so
# 'n_trees' and 'treesPerDonor' are caught, and on whole phrases for multi-word settings.
DERIVED_SETTING_TOKENS: Dict[str, str] = {
    # R12 / R14 router kind and design
    "router": "R12", "routers": "R12", "routing": "R12",
    # R14 / R26 penalties and grid
    "penalty": "R14", "penalties": "R14", "alpha": "R14", "lambda": "R14", "lam": "R14",
    "grid": "R14", "ratio": "R14", "ratios": "R14", "level": "R14", "levels": "R14",
    "actx": "R14",
    # R22 links, R23 c
    "link": "R22", "links": "R22", "c": "R23",
    # R15 normal
    "normal": "R15", "climatology": "R15",
    # R3-R7 windows ('window' is a declared column fact where it belongs, and a knob elsewhere)
    "window": "R3-R7", "windows": "R3-R7", "inner": "R7", "calib": "R3-R7",
    # R8 lags (a verdict or fact never types a lag)
    "lag": "R8", "lags": "R8", "shift": "R8",
    # R10 leads, R11 cuts
    "lead": "R10", "leads": "R10", "horizon": "R10", "horizons": "R10",
    "cut": "R11", "cuts": "R11", "cutoff": "R11",
    # R13 folds
    "fold": "R13", "folds": "R13",
    # R17 history block
    "history": "R17",
    # R18 units per group
    "units": "R18", "cells": "R18", "dcells": "R18",
    # R19 bank recipe and seeds
    "trees": "R19", "tree": "R19", "depth": "R19", "estimators": "R19", "bag": "R19",
    "bags": "R19", "bagging": "R19", "sampler": "R19", "criterion": "R19", "seed": "R19",
    "seeds": "R19", "rng": "R19", "leaf": "R19", "leaves": "R19", "npd": "R19", "mf": "R19",
    "ntrees": "R19", "maxfeatures": "R19", "cdepth": "R19",
    # R21 smoke size
    "smoke": "R21",
    # R24 arms
    "arm": "R24", "arms": "R24", "corrector": "R24", "correctors": "R24", "placebo": "R24",
    # R25 weights
    "weights": "R25", "weight": "R25", "gls": "R25", "weighting": "R25",
    # R27 selection and guard
    "selection": "R27", "selector": "R27", "select": "R27", "guard": "R27",
    # R28 clip
    "clip": "R28",
    # R31 baselines
    "baselines": "R31", "baseline": "R31", "persistence": "R31",
    # R32 / R36 tolerances
    "tolerance": "R32/R36", "tolerances": "R32/R36", "tol": "R32/R36",
    # R35 band
    "band": "R35", "equivalence": "R35",
    # engine constants and closed doors (plan 1.7)
    "threads": "C14", "thread": "C14", "jobs": "C14", "workers": "C14", "backend": "C14",
    "blas": "C14",
    "storage": "plan 1.7 / 4.5", "layout": "plan 1.7 / 4.5",
    "order": "plan 1.7", "ordering": "plan 1.7",
    "mode": "plan 1.7", "preset": "plan 1.7", "recipe": "plan 1.7",
}

DERIVED_SETTING_PHRASES: Dict[str, str] = {
    "train_end": "R6", "test_years": "R5", "test_window": "R5", "train_years": "R6",
    "first_year": "R4", "coverage_end": "R3", "y0": "R4", "y_end": "R3",
    "max_features": "R19", "random_state": "R19", "min_leaf": "R19", "n_jobs": "C14",
    "min_samples_leaf": "R19", "samples_leaf": "R19",
}

# Keys that would hand-set a donor or test set, or type the split as counts or offsets (the old
# --donors / --tests / --from knobs, plan 1.7). Leave one region out (owner rulings D, E L7): there is
# no donor or test list; every group in the data that is not excluded is trained and tested, so any
# such key is refused wherever it appears. Matching: the whole key 'from', or any whole token below.
SPLIT_SET_KEYS: Dict[str, str] = {"donors": "split", "tests": "split", "from": "split"}
SPLIT_SET_TOKENS = ("donor", "donors", "test", "tests")
# The old hard-split continuity list is not package input under L7 (b): it lives in legacy_harness/ and
# treeroute_report/, which may name problems.
CONTINUITY_TOKENS = ("continuity",)

_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SPLIT = re.compile(r"[^A-Za-z0-9]+")


def key_tokens(key):
    """Lower-case tokens of a key: 'nTrees_perDonor' -> ['n', 'trees', 'per', 'donor']."""
    spaced = _CAMEL.sub("_", key)
    return [t.lower() for t in _SPLIT.split(spaced) if t]


def derived_setting_rule(key):
    """Rule id if ``key`` names a derived setting, else None."""
    if not isinstance(key, str):
        return None
    tokens = key_tokens(key)
    phrase = "_".join(tokens)
    if phrase in DERIVED_SETTING_PHRASES:
        return DERIVED_SETTING_PHRASES[phrase]
    for i in range(len(tokens) - 1):
        pair = tokens[i] + "_" + tokens[i + 1]
        if pair in DERIVED_SETTING_PHRASES:
            return DERIVED_SETTING_PHRASES[pair]
    for tok in tokens:
        if tok in DERIVED_SETTING_TOKENS:
            return DERIVED_SETTING_TOKENS[tok]
    return None


def derived_refusal(key, rule):
    return ("'%s' is refused (G-NOKNOB): it names a derived setting. derived: see derived.json, "
            "rule %s" % (key, rule))


def split_set_key(key):
    """True if ``key`` would hand-set a donor or test set, a group count or a start offset: the whole
    key 'donors', 'tests' or 'from', or any whole token 'donor', 'donors', 'test' or 'tests'
    (donor_groups, test_groups, n_donors, testSet, ...)."""
    if not isinstance(key, str):
        return False
    tokens = key_tokens(key)
    if "_".join(tokens) in SPLIT_SET_KEYS:
        return True
    return any(tok in SPLIT_SET_TOKENS for tok in tokens)


def split_set_refusal(key):
    return ("'%s' is refused (G-NOKNOB): derived: every group is tested. Under leave one region out "
            "every group in the data that is not excluded trains its own trees and is tested (rules "
            "R18-R20); there is no donor or test list, group count or start offset. split.yaml holds "
            "only excluded and seen_during_design (plan 1.2)" % key)


def continuity_key(key):
    """True if ``key`` names the old hard-split continuity list (any whole token 'continuity')."""
    if not isinstance(key, str):
        return False
    return any(tok in CONTINUITY_TOKENS for tok in key_tokens(key))


def continuity_refusal(key):
    return ("'%s' is refused (G-NOKNOB): the old hard-split lists are not package input under leave "
            "one region out. The continuity groups are kept in legacy_harness/ and treeroute_report/ "
            "(owner rulings, L7 b); split.yaml holds only excluded and seen_during_design (plan 1.2)"
            % key)


# ---------------------------------------------------------------------------------------------------
class StrictModel(BaseModel):
    """Base for every package model: unknown keys forbidden, instances frozen, G-NOKNOB applied."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # key -> pointed message for keys that belong in another file (for example a role in a store
    # catalog). Checked only for keys that are not declared fields of the model.
    MISPLACED: ClassVar[Dict[str, str]] = {}

    @model_validator(mode="before")
    @classmethod
    def _closed_doors(cls, data):
        if not isinstance(data, dict):
            return data
        declared = set(cls.model_fields)
        for key in data:
            if not isinstance(key, str):
                raise ValueError("key %r is not a string (quote it in the YAML file)" % (key,))
            if key in declared:
                continue
            if key in cls.MISPLACED:
                raise ValueError("'%s' is refused here: %s" % (key, cls.MISPLACED[key]))
            rule = derived_setting_rule(key)
            if rule is not None:
                raise ValueError(derived_refusal(key, rule))
            if split_set_key(key):
                raise ValueError(split_set_refusal(key))
            if continuity_key(key):
                raise ValueError(continuity_refusal(key))
        return data


PackageName = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$")]
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
NonEmptyStr = Annotated[str, Field(min_length=1)]
# Strict numbers: an integer or float as written; a string or a boolean is refused.
Number = Annotated[float, Strict()]
PositiveNumber = Annotated[float, Strict(), Field(gt=0, allow_inf_nan=False)]
NonNegativeNumber = Annotated[float, Strict(), Field(ge=0, allow_inf_nan=False)]
PositiveInt = Annotated[StrictInt, Field(gt=0)]


def _ordered_range(value):
    low, high = value
    if not low <= high:  # also refuses NaN
        raise ValueError("a range is [min, max] with min <= max, got [%r, %r]" % (low, high))
    return value


LegalRange = Annotated[Tuple[Number, Number], AfterValidator(_ordered_range)]
StepUnit = Literal["day", "month", "year"]
Stamp = Literal["period_start", "period_centre", "period_end", "event_date"]
FactStatus = Literal["verified", "unverified", "assumed"]


# ---------------------------------------------------------------------------------------------------
# dataset.yaml
class StorePaths(StrictModel):
    """Store path templates. A template may use key-role placeholders or name one folder. ``static`` is
    required for a grid package (DatasetFile checks it) and absent for a table package (input: table)."""

    target: NonEmptyStr
    static: Optional[NonEmptyStr] = None
    drivers: List[NonEmptyStr] = []
    globals: Optional[NonEmptyStr] = None
    features: Optional[NonEmptyStr] = None


class Include(StrictModel):
    """A shared store catalog, included by path (relative to the package folder) and sha256."""

    path: NonEmptyStr
    sha256: Sha256Hex


# The table option (owner ruling U1, OWNER_RULINGS_2026-10-06.md section U; SPEC_TABLE_MODE.md 1.1): a package
# that supplies ready rows, one parquet file per lead, names the lead in its target template with this one
# placeholder; package/table.py fills it (it is not a listing placeholder, io/listing.py).
LEAD_PLACEHOLDER = "{lead}"
INPUT_GRID = "grid"
INPUT_TABLE = "table"


class DatasetFile(StrictModel):
    """dataset.yaml: name, version, owner, one-line description, the input kind, store paths, includes.
    Nothing else.

    ``input`` (owner ruling U1): 'grid' (the default: every package before the table option) or 'table'
    (ready rows, one file per lead, SPEC_TABLE_MODE.md 1.1). A grid package names its static table and no
    {lead} placeholder. A table package names one target template whose only placeholder is {lead}, and no
    static, driver, global or feature store, and no include (a table has no store facts)."""

    name: PackageName
    version: NonEmptyStr
    owner: NonEmptyStr
    description: NonEmptyStr
    input: Literal["grid", "table"] = "grid"
    stores: StorePaths
    includes: List[Include] = []

    @model_validator(mode="after")
    def _input_kind(self):
        st = self.stores
        templates = [st.target, st.static, st.globals, st.features] + list(st.drivers)
        if self.input == INPUT_GRID:
            if st.static is None:
                raise ValueError("stores.static: Field required (a grid package names its static table)")
            if any(t is not None and LEAD_PLACEHOLDER in t for t in templates):
                raise ValueError("the %s placeholder is for a table package (input: table) only"
                                 % LEAD_PLACEHOLDER)
            return self
        holes = re.findall(r"\{[^{}]*\}", st.target)
        if holes != [LEAD_PLACEHOLDER]:
            raise ValueError("input: table needs stores.target with exactly one placeholder, %s, and no other; "
                             "got %s" % (LEAD_PLACEHOLDER, holes))
        extra = [name for name, value in (("static", st.static), ("globals", st.globals),
                                          ("features", st.features)) if value is not None]
        if st.drivers:
            extra.append("drivers")
        if extra:
            raise ValueError("input: table takes no %s store (the rows are ready; SPEC_TABLE_MODE.md 1.1)"
                             % ", ".join(extra))
        if self.includes:
            raise ValueError("input: table takes no include (a table has no store facts)")
        return self

    @model_validator(mode="after")
    def _one_line(self):
        if "\n" in self.description or "\r" in self.description:
            raise ValueError("description must be one line")
        return self


# ---------------------------------------------------------------------------------------------------
# Shared store catalogs (datasets/_stores/<store>.yaml): physical facts
class Cadence(StrictModel):
    """A regular step {length, unit}, a composite-of-year step (N-day composites restarting every
    1 January), static, epoch, or irregular."""

    kind: Literal["regular", "composite_of_year", "static", "epoch", "irregular"]
    length: Optional[PositiveInt] = None
    unit: Optional[StepUnit] = None

    @model_validator(mode="after")
    def _shape(self):
        if self.kind == "regular":
            if self.length is None or self.unit is None:
                raise ValueError("a regular cadence needs length and unit")
        elif self.kind == "composite_of_year":
            if self.length is None or self.unit != "day":
                raise ValueError("a composite_of_year cadence needs length and unit: day")
        elif self.length is not None or self.unit is not None:
            raise ValueError("a %s cadence takes no length or unit" % self.kind)
        return self


# origin: OWNER_RULINGS_2026-09-28.md part B item 8 (a) and part C 'Reach across a step edge';
# engine/datasets/_stores/INDEX_WINDOW_AUDIT.md open item 8 (a) (the 16-day composites of the monthly
# vegetation index; the burned-area detection window, ruling R-D (b)).
class Reach(StrictModel):
    """How far a column's content reaches past an edge of its window: {value, unit}."""

    value: PositiveNumber
    unit: StepUnit


class Window(StrictModel):
    """A column's own window. ``align: unknown`` carries no length; it may carry a signed maximum.

    ``reach_after_max`` / ``reach_before_max`` (owner rulings, part B item 8 (a), index audit):
    the most the content reaches past the END / before the START of the window. For a window equal to
    its stored step this is the reach across the step edge (16-day composites averaged into a month,
    a detection window that looks past the month end). Optional; either may be given alone.
    """

    length: Optional[PositiveNumber] = None
    unit: Optional[StepUnit] = None
    align: Literal["backward", "centred", "forward", "unknown"]
    max_length: Optional[PositiveNumber] = None
    reach_after_max: Optional[Reach] = None
    reach_before_max: Optional[Reach] = None

    @model_validator(mode="after")
    def _shape(self):
        if self.align == "unknown":
            if self.length is not None:
                raise ValueError("align: unknown takes no length (use max_length for a bound)")
            if self.max_length is not None and self.unit is None:
                raise ValueError("max_length needs a unit")
        else:
            if self.length is None or self.unit is None:
                raise ValueError("align: %s needs length and unit" % self.align)
            if self.max_length is not None:
                raise ValueError("max_length is only for align: unknown")
        return self


class Lineage(StrictModel):
    assimilates: List[NonEmptyStr] = []
    trained_on: List[NonEmptyStr] = []


_STORE_MISPLACED = (
    "it is a package fact: declare it in the package's catalog.yaml, not in a shared store "
    "catalog (plan 1.3)")


class StoreColumn(StrictModel):
    """Physical facts of one stored column, shared by every package that reads the store."""

    MISPLACED: ClassVar[Dict[str, str]] = {
        k: _STORE_MISPLACED for k in (
            "role", "calendar_part", "legal_range_source", "measurement_error_floor",
            "calibration_through", "computed_from", "co_measured_with_target",
            "co_measured_evidence", "data_selected")}

    dtype: NonEmptyStr
    units: NonEmptyStr
    cadence: Cadence
    scope: Literal["unit", "global"]
    stamp: Stamp
    window: Optional[Window] = None
    legal_range: Optional[LegalRange] = None
    fill_values: List[Number] = []
    near_sentinel_optout: StrictBool = False
    product_family: Optional[NonEmptyStr] = None
    lineage: Optional[Lineage] = None
    sum_group: Optional[NonEmptyStr] = None
    content_epoch: Optional[NonEmptyStr] = None
    observed_through: Optional[NonEmptyStr] = None
    release_date: Optional[NonEmptyStr] = None
    snapshot_date: Optional[NonEmptyStr] = None
    baseline_period: Optional[Tuple[NonEmptyStr, NonEmptyStr]] = None
    absent_groups: Dict[str, NonEmptyStr] = {}
    derived_from: List[NonEmptyStr] = []
    operation: Optional[NonEmptyStr] = None
    reads_target: Optional[StrictBool] = None
    fact_status: FactStatus = "unverified"
    reviewed_by: Optional[NonEmptyStr] = None
    date: Optional[NonEmptyStr] = None
    provenance: Optional[NonEmptyStr] = None


class StoreCatalog(StrictModel):
    """One shared store catalog file."""

    store: NonEmptyStr
    description: Optional[NonEmptyStr] = None
    columns: Dict[str, StoreColumn] = Field(min_length=1)


# ---------------------------------------------------------------------------------------------------
# catalog.yaml: problem-relative facts
# The last six roles are the table option's key roles (owner ruling U1; SPEC_TABLE_MODE.md 1.3): only a table
# package (input: table) may declare them, and it must (package/load.py checks both).
ROLES = ("key_unit", "key_group", "key_time", "target", "target_twin", "driver", "router_context",
         "support", "report_stratum", "engineered", "external_product",
         "key_row", "key_lat", "key_lon", "key_issue", "key_feature_end", "key_mark")
Role = Literal["key_unit", "key_group", "key_time", "target", "target_twin", "driver",
               "router_context", "support", "report_stratum", "engineered", "external_product",
               "key_row", "key_lat", "key_lon", "key_issue", "key_feature_end", "key_mark"]
TABLE_ONLY_ROLES = ("key_row", "key_lat", "key_lon", "key_issue", "key_feature_end", "key_mark")

_PACKAGE_MISPLACED = (
    "it is a store fact: declare it in the shared store catalog (datasets/_stores/), not in the "
    "package catalog (plan 1.3)")


class DataSelected(StrictModel):
    """For a column list chosen from data (for example a top-k driver list)."""

    method: NonEmptyStr
    rows: NonEmptyStr
    latest_date: NonEmptyStr
    groups: List[NonEmptyStr]


class PackageColumn(StrictModel):
    """Problem-relative facts of one column. The target's window and stamp live here too."""

    MISPLACED: ClassVar[Dict[str, str]] = {
        k: _PACKAGE_MISPLACED for k in (
            "dtype", "units", "cadence", "scope", "fill_values", "near_sentinel_optout",
            "product_family", "lineage", "sum_group", "content_epoch", "observed_through",
            "release_date", "snapshot_date", "baseline_period", "absent_groups", "derived_from",
            "operation", "reads_target")}

    role: Role
    calendar_part: Optional[Literal["year", "month", "day_of_year", "date"]] = None
    legal_range: Optional[LegalRange] = None
    legal_range_source: Optional[NonEmptyStr] = None
    window: Optional[Window] = None
    stamp: Optional[Stamp] = None
    measurement_error_floor: Optional[NonNegativeNumber] = None
    calibration_through: Optional[StrictInt] = None
    computed_from: List[NonEmptyStr] = []
    co_measured_with_target: Optional[StrictBool] = None
    co_measured_evidence: Optional[NonEmptyStr] = None
    data_selected: Optional[DataSelected] = None
    fact_status: FactStatus = "unverified"
    reviewed_by: Optional[NonEmptyStr] = None
    date: Optional[NonEmptyStr] = None
    provenance: Optional[NonEmptyStr] = None

    @model_validator(mode="after")
    def _calendar_part(self):
        if self.role == "key_time" and self.calendar_part is None:
            raise ValueError("a key_time column needs its calendar_part")
        if self.role != "key_time" and self.calendar_part is not None:
            raise ValueError("calendar_part is only for key_time columns")
        return self


class PackageCatalog(StrictModel):
    """catalog.yaml."""

    columns: Dict[str, PackageColumn] = Field(min_length=1)


# ---------------------------------------------------------------------------------------------------
# ban.yaml
VERDICTS = ("keep", "keep_unreviewed", "freeze", "ban", "conditional", "watch")
BAN_REASONS = ("label", "coproduct", "target_derived", "replaced_by_engine", "post_event_state",
               "lookahead_unfixable", "trend_proxy", "incomplete", "structural",
               "post_window_snapshot")


class Verdict(StrictModel):
    """One verdict. A verdict never types a number (there is no 'lag' verdict)."""

    verdict: Literal["keep", "keep_unreviewed", "freeze", "ban", "conditional", "watch"]
    reason: NonEmptyStr
    evidence: Optional[NonEmptyStr] = None

    @model_validator(mode="after")
    def _shape(self):
        if self.verdict == "ban" and self.reason not in BAN_REASONS:
            raise ValueError("a ban needs one of the reasons %s, got %r"
                             % (", ".join(BAN_REASONS), self.reason))
        if self.verdict != "keep_unreviewed" and self.evidence is None:
            raise ValueError("verdict %r needs evidence (a Part number)" % self.verdict)
        return self


class BanFile(StrictModel):
    """ban.yaml: one verdict per non-key column (closed world, checked later by G-CLOSED)."""

    verdicts: Dict[str, Verdict] = Field(min_length=1)


# ---------------------------------------------------------------------------------------------------
# split.yaml
class SplitFile(StrictModel):
    """split.yaml under leave one region out (owner rulings D and E, L7 b; plan 1.2): the exclusions
    {group: reason} and the optional seen_during_design groups, nothing else.

    There is no donor or test list: every group in the data that is not excluded trains its own trees
    and is tested (the groups are derived: treeroute.split.groups_under_loro). A donor or test key
    (donor_groups, test_groups, donors, tests, ...) is refused with "derived: every group is tested";
    a continuity key is refused with a pointer to legacy_harness/ and treeroute_report/, where the old
    hard-split lists live. Lists are sets: the engine sorts them, so order carries no meaning. Set
    checks (duplicates, every listed group in the data, no reported group excluded) are G-SPLIT, a
    science check (treeroute.split.loro_split_differences)."""

    excluded: Dict[str, NonEmptyStr] = {}
    seen_during_design: List[NonEmptyStr] = []


# ---------------------------------------------------------------------------------------------------
# exceptions.yaml
class ExceptionEntry(StrictModel):
    """A provenance flag, a disclosed defect or a test-exposure disclosure. It cannot relax a time
    rule, hold a timing value or set a derived value."""

    kind: Literal["provenance_flag", "disclosed_defect", "test_exposure"]
    check: Optional[NonEmptyStr] = None
    column: Optional[NonEmptyStr] = None
    decision: NonEmptyStr
    reason: NonEmptyStr
    owner: NonEmptyStr
    date: NonEmptyStr

    @model_validator(mode="after")
    def _addressed(self):
        if self.check is None and self.column is None:
            raise ValueError("an exception entry names a check id or a column")
        return self


class ExceptionsFile(StrictModel):
    """exceptions.yaml (may be empty)."""

    entries: List[ExceptionEntry] = []


# ---------------------------------------------------------------------------------------------------
# config/machine.yaml (outside the engine): paths only
class MachineFile(StrictModel):
    """The machine file: paths only (plan 1.7). Thread counts are engine constants, not here."""

    run_root: NonEmptyStr
    temp_dir: NonEmptyStr
    registry_dir: NonEmptyStr


# ---------------------------------------------------------------------------------------------------
# Reserved optional tables (parquet, hashed into the package fingerprint). Required columns only;
# reading and checking them is io/ work that comes later.
RESERVED_TABLES: Dict[str, Tuple[str, ...]] = {
    "unit_map": ("source_unit", "unit", "weight"),
    "adjacency": ("unit", "neighbour", "weight"),
}

# File name -> model, for the loader and the JSON Schema export.
PACKAGE_FILE_MODELS: Dict[str, Any] = {
    "dataset.yaml": DatasetFile,
    "catalog.yaml": PackageCatalog,
    "ban.yaml": BanFile,
    "split.yaml": SplitFile,
    "exceptions.yaml": ExceptionsFile,
}


def json_schemas():
    """JSON Schema of every package file model, the store catalog and the machine file (for the
    later GUI)."""
    out = {name: model.model_json_schema() for name, model in PACKAGE_FILE_MODELS.items()}
    out["store_catalog"] = StoreCatalog.model_json_schema()
    out["machine.yaml"] = MachineFile.model_json_schema()
    return out
