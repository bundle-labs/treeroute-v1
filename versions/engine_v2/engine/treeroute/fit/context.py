"""FitContext: the ONLY gateway to rows for every fitted object in R11 (banks, correctors, router rows,
normals, c, fills, scalers, the GLS model, persistence phi, Type-3 blind constants).

SCIENCE bodies for the owner-approved signatures of treeroute/_proposed/fit_context.py (owner rulings
A-F), with the LORO addendum ("same signature, changed contract"): picks is split.UnitLists (every
group's bank and scored units); DonorRows are every group's BANK units at or before the cut, in
ascending grid order (owner rulings E: the docstring fix); router_rows accepts bank or scored units.

Three separate sources, so no single object carries both features and labels:
    DenseGrid       keys only (unit ids, groups, steps)
    FeatureSource   the joined, label-free feature pool (tree features and router context)
    LabelView       the vault, the only label source (G-LOCK)
and three containers, each constructed ONLY by its FitContext method (a direct construction, or
dataclasses.replace, is refused):
    DonorRows    donor rows at or before the cut. c, UB checks, tolerances, the GLS model and its clip
                 bounds and Type-3 blind constants accept ONLY DonorRows (G-DONOR).
    UnitHistory  one unit's own rows at or before the cut. Normals and history fills accept ONLY
                 UnitHistory (G-DONOR).
    RouterRows   a router's fit rows (and the only rows a scaler may see).
Every hand-out writes a fitctx_log row (object kind, purpose, lead, cut kind, cut, newest label time,
row count, groups hash, row-key hash, fold). Labels are read through the vault's as-of rule (R11: at
or before the cut, own window ended), so no hand-out can hold a label after its cut (G-FITCUT); an
internal assert re-checks it.

Both cuts per lead (R11): a context is bound to one lead and one cut kind, read from derived.json's
R11 entry (never computed here). for_lead gives the same run at another lead or cut kind.

The INNER-cut bank (owner rulings E, L6 option b; engine constant A7.inner_cut_bank_refit): the nowcast's
inner decision uses a bank (and correctors) refit at the INNER cut (lead 0's guard cut), so the trees
behind the decision hold no row after the inner-fit end; the test pass uses the bank at the fit cut.
bank_plan(derived) lists the banks a run fits and what each serves; FitContext(0, GUARD).donor_rows
hands out the inner bank's rows, and layer.decide.decide() takes that GUARD context and runs
check_inner_score_rows on its surface (G-FITCUT). At a forecast lead (owner ruling H2: L6 b
at every lead) the lagtrain bank at the lead's fit cut serves its test pass and a second bank, refit at the
lead's GUARD cut, serves its guard surface, so no guard row sits inside a bank trained on its labels; only
with A7.inner_cut_bank_refit off (L6 a) does the fit-cut bank serve both, and that entry carries
L6_LEAD_GUARD_DISCLOSURE.

Not built here: fold contexts (for_fold: the neighbour kind's leave-one-group-out surface uses ONE
inner-cut bank with a column drop, milestone M8; the Type-3 purpose is not needed under LORO) and the
Type-3 services fit_bank and donor_fold_predict (milestone M4; they answer only through the own-block
mask). Each raises NotImplementedError naming its milestone.
"""
# Provenance for the module: pm25_adaptation.py:546-549, 572-582, 621-650 (the frames, c and the bank
# read rows at or before the cut); plan 2.1 R11, R13; plan 4.1 steps 3, 5, 6; plan 5 G-FITCUT,
# G-DONOR, G-DISJOINT; owner rulings D, E (L6 b), F.

import threading
from contextlib import contextmanager
from dataclasses import dataclass, fields
from enum import Enum
from numbers import Integral
from types import MappingProxyType
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

import numpy as np

from treeroute import engine_constants as K
from treeroute.derive.derived import sha256_of_json
from treeroute.derive.shapes import CutKind, Derived
from treeroute import split as _split
from treeroute.errors import RefusedError
from treeroute.io.steps import as_int_array
from treeroute.labels.vault import LabelView, row_key_hash


class FitContextRefusal(RefusedError):
    """A FitContext rule refused (R11, R13, G-FITCUT, G-DONOR, G-DISJOINT)."""


# ---------------------------------------------------------------------------------------------------
# Construction guard: the containers are handed out by FitContext only
_ISSUING = threading.local()


@contextmanager
def _issuing():
    depth = getattr(_ISSUING, "depth", 0)
    _ISSUING.depth = depth + 1
    try:
        yield
    finally:
        _ISSUING.depth = depth


def _require_issued(name: str) -> None:
    if not getattr(_ISSUING, "depth", 0):
        raise FitContextRefusal("G-DONOR", "%s is handed out by FitContext only; a direct construction "
                                "(or dataclasses.replace) is refused" % name,
                                fix="ask the run's FitContext for the rows")


class FoldPurpose(Enum):
    """Why a donor-fold FitContext exists (R13 and plan 1.6 are separate uses)."""
    DECISION_SURFACE = "decision_surface"    # R13 neighbour folds, cut at the inner-fit end
    TYPE3 = "type3"                          # plan 1.6 donor_fold_predict, cut at the parent's cut


@dataclass(frozen=True)
class DonorRows:
    """Donor-group rows dated at or before one cut, labels valid (plan 2.1 R11, 5 G-DONOR): every
    group's BANK units, in ascending grid order (unit id, then step).

    Constructed ONLY by FitContext.donor_rows. Any function that needs donor data types its
    parameter as DonorRows, so passing test rows is a type error before it is a leak."""
    groups: Tuple[str, ...]
    cut: int
    cut_kind: CutKind
    lead: int
    fold: Optional[int]
    unit_ids: np.ndarray
    times: np.ndarray
    group_of_row: np.ndarray
    grid_rows: np.ndarray               # dense-grid positions of the rows
    y: np.ndarray                       # from the vault (LabelView.asof)
    X: np.ndarray                       # kept tree features from the FeatureSource, 0-filled (R30), float32
    row_key_hash: str

    def __post_init__(self):
        _require_issued("DonorRows")


class LazyDonorFeatures(object):
    """DonorRows.X read on demand (plan R20's per-group batching; FitContext.donor_rows_lazy): the donor
    rows' kept tree features from the context's FeatureSource with R30's 0-fill, only the rows asked for
    (X[positions]: a float32 copy, the bytes the eager X holds at those rows); the whole matrix is never held.
    shape, dtype and ndim are the eager X's. Reading it whole (numpy's __array__) is refused: a caller that needs
    every row at once takes the eager hand-out."""
    lazy_rows = True

    def __init__(self, ctx: "FitContext", positions: np.ndarray) -> None:
        self._ctx = ctx
        self._pos = np.asarray(positions, dtype=np.int64)
        self.shape = (int(self._pos.size), len(tuple(ctx.features.tree_columns)))
        self.dtype = np.dtype(np.float32)
        self.ndim = 2

    def __len__(self) -> int:
        return self.shape[0]

    def __getitem__(self, idx: Any) -> np.ndarray:
        pos = self._pos[idx]
        return self._ctx._tree_features(np.asarray(pos, dtype=np.int64).reshape(-1))

    def __array__(self, dtype: Any = None) -> np.ndarray:
        raise FitContextRefusal("R20", "internal: lazy donor features were asked for whole; take the eager "
                                "FitContext.donor_rows hand-out where every row is needed at once")


@dataclass(frozen=True)
class UnitHistory:
    """One unit's own labelled rows at or before one cut (plan 5 G-DONOR).

    Constructed ONLY by FitContext.unit_history."""
    unit_id: str
    group: str
    cut: int
    cut_kind: CutKind
    lead: int
    times: np.ndarray
    season_keys: np.ndarray
    y: np.ndarray

    def __post_init__(self):
        _require_issued("UnitHistory")


@dataclass(frozen=True)
class RouterRows:
    """Fit rows of the router at one cut: the listed units' own labelled rows at or before the cut
    (per-unit, region), or a neighbour pool. Also the only rows scalers may be fitted on."""
    cut: int
    cut_kind: CutKind
    lead: int
    unit_ids: np.ndarray
    times: np.ndarray
    row_positions: np.ndarray           # rows in the tree-answer store's row-key order
    y: np.ndarray                       # from the vault
    context: np.ndarray                 # router_context on these rows, from the FeatureSource (NaN kept)

    def __post_init__(self):
        _require_issued("RouterRows")


@dataclass(frozen=True)
class FitCtxLogRow:
    """One fitctx_log.parquet row (G-FITCUT): every fitted object's cut, max label time and
    row-key hash. max_label_time is -1 when the hand-out held no row."""
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


@dataclass(frozen=True)
class BankPlanEntry:
    """One bank a run fits (L6): its lead and cut kind, the cut, what it serves ('decision_surface',
    'test_pass', 'guard_surface'), the other leads whose bank sits at the same cut (flagged, never
    merged: each lead's bank reads its features at that lead's issue step, so two leads at one cut fit
    two different banks), and the disclosure an entry carries ('' when none)."""
    lead: int
    cut_kind: CutKind
    cut: int
    serves: Tuple[str, ...]
    shares_cut_with: Tuple[int, ...]
    disclosure: str


# The disclosure of a forecast lead's guard surface when A7.inner_cut_bank_refit is off (L6 a). Under L6 b
# owner ruling H2 (2026-10-05) gives every lead a GUARD-cut bank, and no lead entry carries a disclosure.
L6_LEAD_GUARD_DISCLOSURE = (
    "A7.inner_cut_bank_refit is off (L6 a): this lead's N2 guard surface is scored by the lagtrain bank at the "
    "lead's FIT cut, whose trees saw the inner-score years (the A7 bias that L6 b, ruled at every lead by "
    "owner ruling H2, removes)")


# ---------------------------------------------------------------------------------------------------
def _int(value: Any, what: str, rule: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise FitContextRefusal(rule, "%s must be a whole number, got %r" % (what, value))
    return int(value)


def _cut_kind(value: Any) -> CutKind:
    raw = getattr(value, "value", value)
    try:
        return CutKind(raw)
    except ValueError:
        raise FitContextRefusal("R11", "cut_kind must be FIT or GUARD, got %r" % (value,)) from None


def _purpose(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise FitContextRefusal("G-FITCUT", "every hand-out names its purpose (bank, c, gls, normal, "
                                "router, ...), got %r" % (value,))
    return value


def cuts_of(derived: Mapping[str, Any]) -> Mapping[int, Any]:
    """{lead: CutPair} from derived.json's R11 entry (never computed here)."""
    if not isinstance(derived, Mapping) or "R11" not in derived:
        raise FitContextRefusal("R11", "derived.json has no R11 entry (the cuts)", fix="run plan first")
    entry = derived["R11"]
    if not isinstance(entry, Derived) or entry.rule_id != "R11":
        raise FitContextRefusal("R11", "derived['R11'] must be R11's Derived, got %s" % type(entry).__name__)
    cuts = entry.value
    if not isinstance(cuts, Mapping) or 0 not in cuts:
        raise FitContextRefusal("R11", "R11's value must map every lead (0 included) to its CutPair")
    for lead, pair in cuts.items():
        for field in ("fit_cut", "guard_cut"):
            _int(getattr(pair, field, None), "R11 lead %r %s" % (lead, field), "R11")
    return cuts


# Provenance: plan 2.1 R2 (the season key: the step's position within its year; annual data one class);
# D28 (step = year x steps per year + position, positions counted from 1).
def season_keys_of(steps: np.ndarray, season: Any) -> np.ndarray:
    """R2's season key of integer steps: ((step - 1) mod steps per year) + 1, the step's position in
    its year under the step index of io.steps (year x steps per year + position); one constant class
    (1) on annual data. Events (the month of the event date) are milestone M8."""
    kind = getattr(getattr(season, "kind", None), "value", getattr(season, "kind", None))
    if kind == "event_month":
        raise NotImplementedError("event season keys are built at milestone M8 (the event rules)")
    if kind not in ("month_of_year", "composite_number", "step_position_in_year", "constant"):
        raise FitContextRefusal("R2", "unknown season key kind %r" % (kind,), fix="pass derived.json's R2")
    per_year = _int(getattr(season, "steps_per_year", None), "R2 steps_per_year", "R2")
    if per_year < 1:
        raise FitContextRefusal("R2", "R2 steps_per_year must be at least 1, got %d" % per_year)
    s = as_int_array(steps, "steps", rule="R2")
    return np.mod(s - 1, per_year) + 1


def feature_block_rows(n_columns: int) -> int:
    """The rows of one block of the eager donor feature matrix (FitContext._tree_feature_matrix): P5.donor_block_values
    values a block, at least one row. Any block size gives the same bytes; it bounds RAM only (fit.weights.gls_ram_bytes
    counts one block's temporaries at the build)."""
    return max(int(K.DONOR_BLOCK_VALUES) // max(int(n_columns), 1), 1)


# Provenance: owner rulings E, L6 option (b); engine constant A7.inner_cut_bank_refit; plan 4.1 steps 6
# and 11; pm25_forecast.py:566-606 (the lead's lag bank serves its guard and its test pass), :13-14
# (lagtrain reads the predecessor month's features, so two leads at one cut fit two banks).
def bank_plan(derived: Mapping[str, Any]) -> Tuple[BankPlanEntry, ...]:
    """The banks a run fits and what each serves (L6).

    Nowcast (lead 0): with A7.inner_cut_bank_refit (L6 b) a bank at the FIT cut serves the test pass
    and a bank refit at the GUARD (inner) cut serves the decision surface; without it (the legacy
    reading, one bank) the fit-cut bank serves both. Each forecast lead, the same rule (owner ruling H2:
    L6 b at every lead): the lagtrain bank at the lead's fit cut serves its test pass and a bank refit at
    the lead's GUARD cut serves its guard surface; without A7.inner_cut_bank_refit the lead's fit-cut bank
    serves both, with L6_LEAD_GUARD_DISCLOSURE.
    Entries of different leads at the same cut are NOT merged: a lead's lagtrain bank reads its tree
    features at the lead's issue step (the shipped ladder reads them from the predecessor step t-L;
    plan R11 "every fitted object cut at the issue date"), so lead 1 at lead 0's fit cut is another
    bank. Each entry names the other leads at its cut (shares_cut_with), so an orchestrator sees the
    shared cut and never fits the same (lead, cut kind, cut) twice.
    Returns the entries, lead 0 first, then the leads in ascending order.
    Refuses: whatever cuts_of refuses.
    """
    cuts = cuts_of(derived)
    zero = cuts[0]
    raw: List[Tuple[int, CutKind, int, Tuple[str, ...], str]] = []
    if K.INNER_CUT_BANK_REFIT:
        raw.append((0, CutKind.FIT, int(zero.fit_cut), ("test_pass",), ""))
        raw.append((0, CutKind.GUARD, int(zero.guard_cut), ("decision_surface",), ""))
    else:
        raw.append((0, CutKind.FIT, int(zero.fit_cut), ("decision_surface", "test_pass"), ""))
    for lead in sorted(int(k) for k in cuts if int(k) != 0):
        pair = {int(k): v for k, v in cuts.items()}[lead]
        if K.INNER_CUT_BANK_REFIT:
            raw.append((lead, CutKind.FIT, int(pair.fit_cut), ("test_pass",), ""))
            raw.append((lead, CutKind.GUARD, int(pair.guard_cut), ("guard_surface",), ""))
        else:
            raw.append((lead, CutKind.FIT, int(pair.fit_cut), ("test_pass", "guard_surface"),
                        L6_LEAD_GUARD_DISCLOSURE))
    keys = [(lead, kind, cut) for lead, kind, cut, _, _ in raw]
    if len(set(keys)) != len(keys):
        raise FitContextRefusal("R11", "internal: the bank plan names one (lead, cut kind, cut) twice")
    out = []
    for lead, kind, cut, serves, note in raw:
        shared = tuple(sorted({other for other, _, c, _, _ in raw if c == cut and other != lead}))
        out.append(BankPlanEntry(lead, kind, cut, serves, shared, note))
    return tuple(out)


# ---------------------------------------------------------------------------------------------------
class FitContext:
    """The gateway for every fitted object at one (lead, cut kind[, fold]).

    Rule: R11, G-FITCUT, G-DONOR. Attributes (read-only): features (the label-free FeatureSource, so
    the route and scoring code may read score rows' router context from it), lead, cut_kind, cut,
    picks, groups.
    """

    # Provenance: plan 2.1 R11; plan 4.1 steps 3, 5 and 6.
    def __init__(self, derived: Mapping[str, Derived], split: Any, grid: Any, labels: LabelView,
                 features: Any, picks: Any, lead: int, cut_kind: CutKind, fold: Optional[int] = None,
                 fold_purpose: Optional[FoldPurpose] = None) -> None:
        """Bind one cut from derived.json; never compute a cut here.

        Rule: R11, R13. The cut is read from derived.json's R11 entry for this lead and cut kind.
        The groups come from the split (split.groups_under_loro over the grid's groups); picks
        (split.UnitLists) decide which units each hand-out may return; when derived.json holds the
        R18 unit lists ('R18:units') the picks must equal them. Keys come from the grid, features
        from the FeatureSource, labels from the vault.
        Refuses: a lead not in derived.json; a fold without fold_purpose, or fold_purpose without a
        fold; picks that name a unit outside its group, a unit off the grid, a scored unit outside
        its bank list, or a group outside the split; picks that differ from derived.json's; a vault
        built on another grid; a feature source without the FeatureSource methods. Fold contexts
        raise NotImplementedError (milestone M8; see the module docstring).
        """
        self._derived = derived
        self._cuts = cuts_of(derived)
        self._lead = _int(lead, "lead", "R11")
        if self._lead not in {int(k) for k in self._cuts}:
            raise FitContextRefusal("R11", "lead %d is not in derived.json (leads %s)"
                                    % (self._lead, sorted(int(k) for k in self._cuts)),
                                    fix="the leads come from R10 / R11")
        self._pair = {int(k): v for k, v in self._cuts.items()}[self._lead]
        self._kind = _cut_kind(cut_kind)
        if (fold is None) != (fold_purpose is None):
            raise FitContextRefusal("R13", "a fold context needs both fold and fold_purpose (got fold %r, "
                                    "purpose %r)" % (fold, fold_purpose))
        if fold is not None:
            _int(fold, "fold", "R13")
            FoldPurpose(getattr(fold_purpose, "value", fold_purpose))
            raise NotImplementedError(
                "fold contexts are not built: under leave one region out the neighbour kind's decision "
                "surface drops one overlap block's tree columns from ONE inner-cut bank (milestone M8), "
                "and the Type-3 purpose is not needed (own-block-masked services, milestone M4)")
        self._fold = None
        self._fold_purpose = None
        for field in ("unit_ids", "group_of_unit", "first_step", "n_steps"):
            if not hasattr(grid, field):
                raise FitContextRefusal("G-LOCK", "grid must be the keys-only DenseGrid (no %r)" % field)
        self._grid = grid
        if not isinstance(labels, LabelView):
            raise FitContextRefusal("G-LOCK", "labels must be the run's LabelView (the only label source)")
        lg = labels.grid
        if (tuple(lg.unit_ids) != tuple(grid.unit_ids) or int(lg.first_step) != int(grid.first_step)
                or int(lg.n_steps) != int(grid.n_steps)):
            raise FitContextRefusal("G-LOCK", "the vault was built on another grid")
        self._labels = labels
        for name in ("tree_features", "context"):
            if not callable(getattr(features, name, None)):
                raise FitContextRefusal("R30", "features must be a FeatureSource (no %s())" % name)
        for name in ("tree_columns", "context_columns"):
            if not hasattr(features, name):
                raise FitContextRefusal("R30", "features must be a FeatureSource (no %s)" % name)
        self._features = features
        self._split = split
        self._row_of = {str(u): i for i, u in enumerate(grid.unit_ids)}
        self._group_of = tuple(str(g) for g in grid.group_of_unit)
        split_groups = _split.groups_under_loro(split, tuple(sorted(set(self._group_of))))
        self._picks = self._check_picks(picks, split_groups)
        self._groups = tuple(sorted(self._picks.bank))
        self._bank_rows = np.asarray(sorted(self._row_of[u] for g in self._groups
                                            for u in self._picks.bank[g]), dtype=np.int64)
        self._picked = {u for g in self._groups for u in self._picks.bank[g]}
        self._log: List[FitCtxLogRow] = []

    def _check_picks(self, picks: Any, split_groups: Tuple[str, ...]) -> Any:
        for field in ("bank", "scored"):
            if not isinstance(getattr(picks, field, None), Mapping):
                raise FitContextRefusal("R18", "picks must be split.UnitLists (bank and scored lists)")
        if set(picks.scored) - set(picks.bank):
            raise FitContextRefusal("R18", "groups with scored units but no bank list: %s"
                                    % sorted(set(picks.scored) - set(picks.bank)))
        if not picks.bank:
            raise FitContextRefusal("R18", "the picks name no group")
        outside = sorted(set(picks.bank) - set(split_groups))
        if outside:
            raise FitContextRefusal("G-SPLIT", "the picks name group(s) %s outside the split's groups"
                                    % outside[:5])
        seen: Dict[str, str] = {}
        for g in sorted(picks.bank):
            bank = tuple(picks.bank[g])
            if not bank:
                raise FitContextRefusal("R18", "group %r has no bank unit" % g)
            for u in bank:
                row = self._row_of.get(u)
                if row is None:
                    raise FitContextRefusal("R18", "bank unit %r of group %r is not on the grid" % (u, g))
                if self._group_of[row] != g:
                    raise FitContextRefusal("G-DISJOINT", "bank unit %r is listed under group %r but its "
                                            "grid group is %r" % (u, g, self._group_of[row]))
                if u in seen:
                    raise FitContextRefusal("R18", "unit %r is picked twice" % u)
                seen[u] = g
            extra = sorted(set(picks.scored.get(g, ())) - set(bank))
            if extra:
                raise FitContextRefusal("R18", "group %r: scored units outside its bank list: %s"
                                        % (g, extra[:5]))
        planned = self._derived.get("R18:units") if isinstance(self._derived, Mapping) else None
        if planned is not None:
            value = getattr(planned, "value", None)
            same = (value is not None
                    and {g: tuple(v) for g, v in value.bank.items()} == {g: tuple(v) for g, v in picks.bank.items()}
                    and {g: tuple(v) for g, v in value.scored.items()} == {g: tuple(v) for g, v in picks.scored.items()})
            if not same:
                raise FitContextRefusal("R18", "the picks differ from derived.json's R18 unit lists",
                                        fix="the run uses the lists plan derived")
        return picks

    # ---------------------------------------------------------------- read-only views
    @property
    def features(self) -> Any:
        return self._features

    @property
    def lead(self) -> int:
        return self._lead

    @property
    def cut_kind(self) -> CutKind:
        return self._kind

    @property
    def cut(self) -> int:
        return int(self._pair.fit_cut if self._kind is CutKind.FIT else self._pair.guard_cut)

    @property
    def picks(self) -> Any:
        return self._picks

    @property
    def groups(self) -> Tuple[str, ...]:
        return self._groups

    @property
    def derived(self) -> Mapping[str, Any]:
        """derived.json's entries this context was bound with (a read-only view; decide() reads R22)."""
        return MappingProxyType(dict(self._derived))

    def unit_row(self, unit_id: str) -> int:
        """The dense-grid row of a unit (refuses a unit off the grid)."""
        row = self._row_of.get(unit_id)
        if row is None:
            raise FitContextRefusal("R18", "unit %r is not on the grid" % (unit_id,))
        return row

    # Provenance: plan 2.1 R11.
    def cut_pair(self) -> Any:
        """Both cuts of this context's lead, from derived.json (read-only)."""
        return self._pair

    # ---------------------------------------------------------------- hand-outs
    def _record(self, object_kind: str, purpose: str, times: np.ndarray, groups: Tuple[str, ...],
                key_hash: str) -> None:
        self._log.append(FitCtxLogRow(
            object_kind=object_kind, purpose=purpose, lead=self._lead, cut_kind=self._kind,
            cut=self.cut, max_label_time=int(times.max()) if times.size else -1, n_rows=int(times.size),
            groups_hash=sha256_of_json(list(groups)), row_key_hash=key_hash, fold=self._fold,
            fold_purpose=self._fold_purpose))

    def _assert_within_cut(self, times: np.ndarray, what: str) -> None:
        if times.size and int(times.max()) > self.cut:
            raise FitContextRefusal("G-FITCUT", "internal: %s holds a label at %d, after the cut %d"
                                    % (what, int(times.max()), self.cut))

    def _labelled(self, unit_rows: np.ndarray, purpose: str, method: str):
        pos = self._labels._asof_positions(self.cut, unit_rows, purpose, method)
        units, times, y = self._labels._label_values(pos)
        self._assert_within_cut(times, method)
        return pos, units, times, y

    def _source_tree_read(self, pos: np.ndarray, rows_handed_out: Optional[int] = None) -> np.ndarray:
        """The feature source's read of rows pos's kept tree features (the source's own array, NaN kept), its shape
        checked (R30). rows_handed_out: the hand-out's row count when pos is one row block of it (the refusal names
        the block)."""
        X = np.asarray(self._features.tree_features(pos))
        n_cols = len(tuple(self._features.tree_columns))
        if X.ndim != 2 or X.shape != (pos.size, n_cols):
            block = "" if rows_handed_out is None else " (one row block of the %d rows handed out)" % rows_handed_out
            raise FitContextRefusal("R30", "the feature source returned shape %s for %d rows%s of %d tree "
                                    "columns" % (X.shape, pos.size, block, n_cols))
        return X

    def _tree_feature_block(self, pos: np.ndarray, out: np.ndarray, rows_handed_out: int) -> int:
        """Rows pos's kept tree features written into out (float32 rows x tree columns, the caller's), R30's 0-fill
        applied; returns how many values are infinite (the caller refuses). The float32 cast of the source's values is
        numpy's per-value cast (the bytes np.array(read, dtype=float32) gives), and the 0-fill and the infinite count
        are per value, so a row's values never depend on the other rows read beside it."""
        X = self._source_tree_read(pos, rows_handed_out)
        out[...] = X
        del X                                    # the source's read is freed before the masks
        n_inf = int(np.count_nonzero(np.isinf(out)))
        out[np.isnan(out)] = 0.0                 # R30: tree features are 0-filled
        return n_inf

    @staticmethod
    def _refuse_infinite(n_inf: int) -> None:
        if n_inf:
            raise FitContextRefusal("R30", "%d tree feature values are infinite; sentinels are masked at "
                                    "read" % n_inf)

    def _tree_features(self, pos: np.ndarray) -> np.ndarray:
        """The rows' kept tree features (float32, 0-filled, R30) in one read: a lazy hand-out's rows. The float32 copy
        is made once the source's read has returned, so it never sits beside the source's own working arrays (a pool's
        gather and its reordered copy); the eager matrix is _tree_feature_matrix's (one preallocated array)."""
        X = np.array(self._source_tree_read(pos), dtype=np.float32, copy=True)
        self._refuse_infinite(int(np.count_nonzero(np.isinf(X))))
        X[np.isnan(X)] = 0.0                     # R30: tree features are 0-filled
        return X

    # Provenance: the GLS weight model's RAM (agent A's estimate, 2026-10-06: full-size NDVI's 4.69 GiB donor matrix
    # needed about 10.5 GiB while built in one piece); plan 1.7 (RAM decides go or refuse, never a number).
    def _tree_feature_matrix(self, pos: np.ndarray, alloc: Optional[Callable[[Tuple[int, int], Any], Any]] = None
                             ) -> np.ndarray:
        """The eager DonorRows.X: every row's kept tree features (float32, 0-filled, R30), read in row blocks of
        feature_block_rows rows straight into ONE preallocated float32 matrix, so the source's read and the masks
        exist for one block at a time, never for the whole matrix. The bytes are _tree_features' on the same rows:
        a feature source reads each row on its own, and the cast, the 0-fill and the infinite count are per value.
        An infinite value is refused once every block is read, with the count over the whole matrix. The matrix is
        allocated before the first block's read, so one block's read sits beside it (fit.weights.gls_ram_bytes'
        build moment). alloc(shape, dtype): where the matrix lives (None: np.empty in RAM; the GLS weight model
        passes a C-ordered float32 temp memmap, RAM tactic 6: the same values, written by the same blocks)."""
        n_cols = len(tuple(self._features.tree_columns))
        n = int(pos.size)
        out = np.empty((n, n_cols), dtype=np.float32) if alloc is None else alloc((n, n_cols), np.float32)
        if out.shape != (n, n_cols) or out.dtype != np.float32 or not out.flags.c_contiguous:
            raise FitContextRefusal("G-DISK", "internal: the donor matrix's allocator gave %s %s (C-ordered %s), not "
                                    "a C-ordered float32 (%d, %d)" % (out.dtype, out.shape, out.flags.c_contiguous,
                                                                      n, n_cols))
        step = feature_block_rows(n_cols)
        n_inf = 0
        for a0 in range(0, n, step):
            b0 = min(a0 + step, n)
            n_inf += self._tree_feature_block(pos[a0:b0], out[a0:b0], n)
        self._refuse_infinite(n_inf)
        return out

    # Provenance: plan 5 G-DONOR (c, UB checks, tolerance, GLS model and clip bounds, Type-3 blind
    # constants accept only DonorRows); Tier 1 reading test labels at adaptation.py:1702-1709.
    def donor_rows(self, purpose: str, unit_ids: Optional[Tuple[str, ...]] = None) -> DonorRows:
        """Donor-group rows with valid labels at or before this context's cut.

        Rule: R11, G-DONOR, G-FITCUT (LORO: every group's bank units). Only bank units of the picked
        groups, only rows at or before the cut whose label window has ended (the vault's as-of rule),
        only valid labels; ascending grid order (unit id, then step), so the row-key hash equals the
        vault's DonorLabels at the same cut and units. y comes from the vault, X from the
        FeatureSource with the R30 0-fill (read in row blocks into one float32 matrix,
        _tree_feature_matrix). Writes a fitctx_log row.
        Returns DonorRows (groups = the groups of the units handed out).
        Refuses: a unit that is not a bank unit (not picked); no row at all; an infinite feature;
        (internal assert) any row after the cut.
        """
        return self._donor_rows(purpose, unit_ids, False)

    def donor_rows_lazy(self, purpose: str, unit_ids: Optional[Tuple[str, ...]] = None) -> DonorRows:
        """donor_rows with X a LazyDonorFeatures (plan R20's per-group batching): the same rows, labels, row-key
        hash and fitctx log row (object kind 'donor_rows'); the tree features are read from the FeatureSource only
        for the rows asked (fit.bank reads one group's rows at a time), so the matrix of every group's rows is
        never held. An infinite feature is refused when the rows holding it are read."""
        return self._donor_rows(purpose, unit_ids, True)

    def donor_rows_checked(self, purpose: str, check: Callable[[np.ndarray, int], None],
                           alloc: Optional[Callable[[Tuple[int, int], Any], Any]] = None) -> DonorRows:
        """donor_rows (every bank unit, the eager X) with a go/refuse between the label read and the feature read:
        check(group_of_row, n_tree_columns) is called once the rows are known (each row's group, in the rows'
        order) and BEFORE the feature matrix is built; it raises to refuse (fit.weights' RAM check of the GLS
        weight model). The same rows, labels, X, row-key hash, vault as-of read and fitctx log row as
        donor_rows(purpose). alloc: where X lives (_tree_feature_matrix; None: in RAM)."""
        if not callable(check):
            raise FitContextRefusal("G-DISK", "internal: donor_rows_checked needs a callable check, got %r" % (check,))
        return self._donor_rows(purpose, None, False, check, alloc)

    def _donor_rows(self, purpose: str, unit_ids: Optional[Tuple[str, ...]], lazy: bool,
                    check: Optional[Callable[[np.ndarray, int], None]] = None,
                    alloc: Optional[Callable[[Tuple[int, int], Any], Any]] = None) -> DonorRows:
        purpose = _purpose(purpose)
        if unit_ids is None:
            rows = self._bank_rows
        else:
            wanted = [str(u) for u in unit_ids]
            bad = sorted(u for u in set(wanted) if u not in self._picked)
            if bad:
                raise FitContextRefusal("G-DONOR", "unit(s) %s are not bank units of the picked groups"
                                        % bad[:5], fix="donor rows are every group's bank units (R18)")
            rows = np.asarray(sorted({self._row_of[u] for u in wanted}), dtype=np.int64)
        pos, units, times, y = self._labelled(rows, purpose, "donor_rows")
        if pos.size == 0:
            raise FitContextRefusal("G-DONOR", "no donor row at the cut %d for purpose %r" % (self.cut, purpose))
        group_of_row = np.asarray(self._group_of, dtype=object)[pos // int(self._grid.n_steps)]
        groups = tuple(sorted(set(group_of_row.tolist())))
        if check is not None:
            check(group_of_row, len(tuple(self._features.tree_columns)))
        if lazy:
            X = LazyDonorFeatures(self, pos)
        else:
            X = self._tree_feature_matrix(pos) if alloc is None else self._tree_feature_matrix(pos, alloc)
        key = row_key_hash(units, times)
        with _issuing():
            out = DonorRows(groups=groups, cut=self.cut, cut_kind=self._kind, lead=self._lead,
                            fold=self._fold, unit_ids=units, times=times, group_of_row=group_of_row,
                            grid_rows=pos.astype(np.int64), y=y, X=X, row_key_hash=key)
        self._record("donor_rows", purpose, times, groups, key)
        return out

    # Provenance: APP_PLAN.md R13 (the neighbour kind's fold g: its c and GLS model from the rows outside g's block
    # at or before the inner-fit end), R25 ("per held-out group for neighbour"); SPEC_TABLE_MODE.md 5.11. ADDITIVE:
    # no line above changes; only the table option's neighbour pass calls it (owner item O19: a signature for review).
    def donor_rows_outside(self, purpose: str, left_out_groups: Tuple[str, ...], fold: int) -> DonorRows:
        """The rows donor_rows(purpose) would hand out, less every row of the listed groups, in the same order (a
        decision-surface fold's donor rows: R13, R25). The hand-out is logged with the fold index and the fold
        purpose DECISION_SURFACE (FitCtxLogRow carries both); the DonorRows carry the fold.
        Refuses: a fold that is not a whole number at or above 0; no row left; whatever donor_rows refuses."""
        purpose = _purpose(purpose)
        fold = _int(fold, "fold", "R13")
        if fold < 0:
            raise FitContextRefusal("R13", "fold %d is negative" % fold)
        left = {str(g) for g in left_out_groups}
        rows = np.asarray([r for r in self._bank_rows.tolist() if self._group_of[r] not in left], dtype=np.int64)
        pos, units, times, y = self._labelled(rows, purpose, "donor_rows")
        if pos.size == 0:
            raise FitContextRefusal("G-DONOR", "no donor row at the cut %d outside the groups %s for purpose %r"
                                    % (self.cut, sorted(left), purpose))
        group_of_row = np.asarray(self._group_of, dtype=object)[pos // int(self._grid.n_steps)]
        groups = tuple(sorted(set(group_of_row.tolist())))
        X = self._tree_feature_matrix(pos)
        key = row_key_hash(units, times)
        with _issuing():
            out = DonorRows(groups=groups, cut=self.cut, cut_kind=self._kind, lead=self._lead, fold=fold,
                            unit_ids=units, times=times, group_of_row=group_of_row, grid_rows=pos.astype(np.int64),
                            y=y, X=X, row_key_hash=key)
        self._log.append(FitCtxLogRow(
            object_kind="donor_rows", purpose=purpose, lead=self._lead, cut_kind=self._kind, cut=self.cut,
            max_label_time=int(times.max()) if times.size else -1, n_rows=int(times.size),
            groups_hash=sha256_of_json(list(groups)), row_key_hash=key, fold=fold,
            fold_purpose=FoldPurpose.DECISION_SURFACE))
        return out

    # Provenance: plan 5 G-DONOR (normals and history fills accept only UnitHistory); plan 2.2 R15.
    def unit_history(self, unit_id: str, purpose: str) -> UnitHistory:
        """One unit's own labelled rows at or before this context's cut.

        Rule: R15, R17, G-DONOR. Rows of that unit only, at or before the cut, valid labels only,
        with their R2 season keys (season_keys_of over derived.json's R2). Logged. A unit with no row
        gets an empty history (R15's fallback chain then applies).
        Returns UnitHistory.
        Refuses: a unit that is not picked; a derived.json without R2; (internal assert) any row after
        the cut or from another unit.
        """
        purpose = _purpose(purpose)
        unit_id = str(unit_id)
        if unit_id not in self._picked:
            raise FitContextRefusal("G-DONOR", "unit %r is not a picked unit" % unit_id)
        season = self._derived.get("R2") if isinstance(self._derived, Mapping) else None
        if season is None:
            raise FitContextRefusal("R2", "derived.json has no R2 entry (the season key)")
        row = self._row_of[unit_id]
        pos, units, times, y = self._labelled(np.asarray([row], dtype=np.int64), purpose, "unit_history")
        if units.size and set(units.tolist()) != {unit_id}:
            raise FitContextRefusal("G-DONOR", "internal: a unit history holds another unit's rows")
        keys = season_keys_of(times, getattr(season, "value", season))
        group = self._group_of[row]
        with _issuing():
            out = UnitHistory(unit_id=unit_id, group=group, cut=self.cut, cut_kind=self._kind,
                              lead=self._lead, times=times, season_keys=keys, y=y)
        self._record("unit_history", purpose, times, (group,), row_key_hash(units, times))
        return out

    # Provenance: plan 2.1 R6 ("every router row is at or before [the train end]"); plan 2.3 R20
    # (router standardisation constants come from fit rows at or before the cut); pm25_adaptation.py:
    # 326-327 (cut asserts, now on the integer step).
    def router_rows(self, unit_ids: Tuple[str, ...], purpose: str) -> RouterRows:
        """The router's fit rows (and the only rows a scaler may see) for the listed units.

        Rule: R11, R14, R20, G-FITCUT. The listed units' own valid rows at or before the cut, in the
        tree-answer store's row-key order (grid order: unit by unit, step order), with their router
        context from the FeatureSource (NaN kept). Logged.
        Returns RouterRows.
        Refuses: a unit that is not picked (bank or scored); no unit; (internal assert) any row after
        the cut.
        """
        purpose = _purpose(purpose)
        wanted = [str(u) for u in unit_ids]
        if not wanted:
            raise FitContextRefusal("R14", "router_rows needs at least one unit")
        bad = sorted(u for u in set(wanted) if u not in self._picked)
        if bad:
            raise FitContextRefusal("G-DONOR", "unit(s) %s are not picked units" % bad[:5])
        rows = np.asarray(sorted({self._row_of[u] for u in wanted}), dtype=np.int64)
        pos, units, times, y = self._labelled(rows, purpose, "router_rows")
        ctx = np.asarray(self._features.context(pos))
        n_ctx = len(tuple(self._features.context_columns))
        if ctx.ndim != 2 or ctx.shape != (pos.size, n_ctx):
            raise FitContextRefusal("R20", "the feature source returned context of shape %s for %d rows "
                                    "of %d context columns" % (ctx.shape, pos.size, n_ctx))
        groups = tuple(sorted({self._group_of[r] for r in rows.tolist()}))
        key = row_key_hash(units, times)
        with _issuing():
            out = RouterRows(cut=self.cut, cut_kind=self._kind, lead=self._lead, unit_ids=units,
                             times=times, row_positions=pos.astype(np.int64), y=y,
                             context=np.array(ctx, dtype=np.float32, copy=True))
        self._record("router_rows", purpose, times, groups, key)
        return out

    # Provenance: plan 5 G-FITCUT ("every inner score row issued at or after the inner guard's cut",
    # pm25_forecast.py:566-574).
    def check_inner_score_rows(self, issue_times: np.ndarray) -> None:
        """Assert every inner score row is issued at or after the inner guard's cut.

        Rule: G-FITCUT. Applies to GUARD contexts at every lead; a row issued before the guard cut
        would be scored by objects that saw its label.
        Refuses: a FIT context; any row issued before the guard cut.
        """
        if self._kind is not CutKind.GUARD:
            raise FitContextRefusal("G-FITCUT", "check_inner_score_rows applies to the GUARD context of a "
                                    "lead (the inner guard's cut)")
        t = as_int_array(issue_times, "issue times", rule="G-FITCUT")
        early = int(np.count_nonzero(t < self.cut))
        if early:
            raise FitContextRefusal("G-FITCUT", "%d inner score row(s) are issued before the guard cut %d "
                                    "(earliest %d); objects fitted at the cut saw their labels"
                                    % (early, self.cut, int(t.min())),
                                    fix="score only rows issued at or after the inner guard's cut")

    # Provenance: plan 2.1 R11 (both cuts per lead); plan 4.1 step 11.
    def for_lead(self, lead: int, cut_kind: CutKind) -> "FitContext":
        """A new context at another lead and cut kind, same derived.json, split, grid, features, picks
        and vault. Refuses a lead not in derived.json."""
        return FitContext(self._derived, self._split, self._grid, self._labels, self._features,
                          self._picks, lead, cut_kind)

    # Provenance: plan 2.1 R13; plan 1.6; LORO addendum (DECISION_SURFACE uses the one inner-cut bank
    # with a column drop; TYPE3 no longer needed).
    def for_fold(self, fold: int, purpose: FoldPurpose) -> "FitContext":
        """A context for donor fold i. Not built under leave one region out (module docstring):
        raises NotImplementedError (milestone M8) after checking its arguments."""
        _int(fold, "fold", "R13")
        FoldPurpose(getattr(purpose, "value", purpose))
        raise NotImplementedError("for_fold is not built: the neighbour kind's leave-one-group-out "
                                  "surface (milestone M8) drops one block's tree columns from one "
                                  "inner-cut bank; the Type-3 purpose is not needed under LORO")

    # Provenance: plan 1.6 (ctx.fit_bank); M4 (Type-3 slot); LORO addendum (a service that answers only
    # through own_block_masked_answers, never a raw Bank).
    def fit_bank(self, target_transform: Optional[Callable[[np.ndarray], np.ndarray]] = None) -> Any:
        """Type-3 service. Milestone M4 (answers only through the own-block mask)."""
        raise NotImplementedError("fit_bank is a Type-3 service, built at milestone M4 (it answers only "
                                  "through the own-block-masked gateway, never a raw Bank)")

    def donor_fold_predict(self, rows: np.ndarray) -> np.ndarray:
        """Type-3 service. Milestone M4 (D98: the plug-in's author declares its return)."""
        raise NotImplementedError("donor_fold_predict is a Type-3 service, built at milestone M4")

    # Provenance: plan 7.1 (fitctx_log.parquet in the run folder); plan 5 G-FITCUT.
    def log(self) -> Tuple[FitCtxLogRow, ...]:
        """Every row hand-out this context made, for fitctx_log.parquet (one row per hand-out)."""
        return tuple(self._log)


def log_records(rows: Tuple[FitCtxLogRow, ...]) -> Tuple[Dict[str, Any], ...]:
    """fitctx_log rows as plain records (enums as their values), for the parquet writer."""
    out = []
    for row in rows:
        rec = {}
        for f in fields(FitCtxLogRow):
            v = getattr(row, f.name)
            rec[f.name] = v.value if isinstance(v, Enum) else v
        out.append(rec)
    return tuple(out)


__all__ = ["FitContextRefusal", "FoldPurpose", "DonorRows", "UnitHistory", "RouterRows", "FitCtxLogRow",
           "BankPlanEntry", "L6_LEAD_GUARD_DISCLOSURE", "cuts_of", "season_keys_of", "bank_plan",
           "FitContext", "log_records", "feature_block_rows"]
