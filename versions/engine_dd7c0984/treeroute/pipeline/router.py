"""The router-kind dispatch of one pipeline pass (plan 4.1 steps 8, 9 and 11; R12, R14-R16, R24, R25; owner
rulings C, E (L2 rules 2-4, L4)).

Orchestration only: every rule is its approved module's. One PassRouter routes the arms of one pass (the
decision surface at the guard cut, the test pass at the fit cut, a forecast lead's guard or test pass)
through the router kind derive_all wrote (R12):

  per_unit   route.kinds' kernels, one ridge per scored unit on its own fit rows (unweighted arms, and GLS
             arms through the kernels' fit_weights: route.solve's weighted solve, a NEW formula for the
             owner's review). A short-history unit (fewer than PER_UNIT_MIN_VALID_ROWS fit rows, R12) is
             routed by its group's FALLBACK region router, fitted on the group's BANK units (L2 rule 3),
             through route/region.py's fallback service: fallback_plan, route_fallback_grid /
             route_fallback_at, fallback_surface_mae + search_fallback_level on the decision surface
             (once per arm's link and table; the nowcast's test pass reuses the level the decision
             surface found; a table the surface never routed, the placebo, takes its corrector's level),
             fill_fallback. A forecast lead searches its OWN level on its own guard surface (owner ruling
             H5): its guard pass is routed at the pinned penalty with search_levels=True (the fallback
             level is searched on that surface, the lambda centre below C15's fallback-unit count, as on
             the decision surface), and the lead's test pass reads the levels its guard found; at the
             longest lead the guard also searches the corrector table's level (level_tables) when the
             pinned arm is plain, for the placebo. The fallback region router has no weighted form, so a
             GLS arm's short-history rows come from the same (unweighted) fallback router as its
             unweighted twin (recorded). A pass in which EVERY scored unit is short (possible at a
             long lead, whose guard fit rows end L - 1 steps earlier) is not sent to the kernels, which
             refuse a pass with no unit to fit: its rows start NaN and the fallback routers fill them
             all (recorded as all_short).
  region     route/region.py's kernels, one pooled ridge per group on its capped BANK units (the whole-
             unit cap is applied inside the kernel), scoring its scored units; the tree block's Gram is
             formed once per group and table and shared across the links (L4: region_shared_gram). No
             weighted solve exists for this kind, so its GLS arms are absent under a declared reason
             (REGION_GLS_ABSENT) and no weight model is fitted.
  neighbour  not built (milestone M8): refused before any fit.

The FitContext-level wrappers the owner approved (route_per_unit_loro, route_region_loro) are not built
(their signatures pass score rows as grid positions only, and FitContext has no public reader of a
position's unit and step), so this module feeds the kernels itself and carries the wrappers' obligations:
the normal columns come from NormalTables built at the pass's cut and link (R15, stages._normals_on
refuses a table of another cut, link or c); the masks come only from own_block_tree_columns over the
overlap blocks (R14, G-DISJOINT; the kernels check them against the store's own trees); a short-history
unit's NaN rows are filled by the fallback router before any score, and a NaN router row left after the
fill is refused.

Every table a router reads is built here before the router reads it (the store computes only rows not
built yet): the scored units' pass rows are built by the caller; this module adds the bank units' fit
rows of the region kind and of every group with a fallback unit.

Per-group batching (plan R20, made real for full-size runs; PassInput.schedule, a GroupTables): instead of
the caller building every group's tables before the pass, the pass walks the groups in sorted order and,
for each one, builds that group's scored-unit rows (the rows the caller would have built: GroupTables.build),
routes that group's units for every arm (route.kinds' kernels with only_group: the unit plan and the
reference check stay the whole pass's), adds the group's bank rows when it has a fallback unit or the kind is
region, computes the group's fallback router outputs, and drops every table of the group (GroupTables.drop)
before the next group. Everything that reads no table runs before the walk in the whole pass's order (the
FitContext hand-outs: router rows, histories, normals, the fallback groups' router rows; so fitctx_log is
unchanged), and everything that pools the groups runs after it on the kept outputs (the fallback level search,
the fill, G-PLUMB), in the whole pass's order: the same rows, the same arithmetic, the same bytes. One group's
tables are on disk at a time.

Owner ruling G1 (owner rulings, section G): the per-unit pass's fit rows come from stages.pass_rows, which
leaves out a fit row whose router context (read at the pass's issue step) is missing or non-finite, as R30
leaves out a row with a missing label, and refuses a scored row with missing context as a last guard only (owner
ruling S1 leaves such scored rows out before the pass: RunState.leave_out_score_context); nothing is filled. The
pass's normal (R15: the mean over the unit's own fit rows) of a unit that lost rows comes from its kept fit
rows, so trees-off still equals the normal (R16; stages.context_kept_histories). A unit left with fewer than
PER_UNIT_MIN_VALID_ROWS fit rows is a short-history unit (R12) like any other. The count is printed per unit
and pass (each lead's guard and test pass) and recorded as records['context_missing']; the rows left out are
saved one by one through the run state (save_context_missing_rows; the record's rows_file names the file),
and the fitctx_log twins of the trimmed hand-outs (the router rows, each trimmed unit's normal history) go to
the run state's log (log_g1_kept), so the log records the rows actually fitted. The region kernels read no
context, so the region kind and the R12 fallback rows are not filtered (stages.G1_SCOPE).
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from treeroute import engine_constants as K
from treeroute.derive.shapes import Link
from treeroute.errors import RefusedError
from treeroute.layer import arms as LA
from treeroute.layer.links import clip_to_legal, link_forward
from treeroute.route import kinds as RK
from treeroute.route import region as RR

from . import stages as ST

KIND_PER_UNIT = "per_unit"
KIND_REGION = "region"
KIND_NEIGHBOUR = "neighbour"
REGION_GLS_ABSENT = ("the region router kind has no weighted solve: route/region.py's trace-normalised ridge "
                     "takes no row weights, and a weighted form is a new formula awaiting the owner's review; "
                     "the GLS weight model is not fitted for a region package (its only use is the GLS arms)")
FALLBACK_GLS_NOTE = ("the fallback region router (R12) has no weighted form: a GLS arm's short-history rows "
                     "take the same fallback predictions as its unweighted twin")


class RouterRefusal(RefusedError):
    """The router dispatch refused (fail loudly)."""


def router_kind(derived: Mapping[str, Any]) -> str:
    """R12's outcome from derived.json: 'per_unit' or 'region'. The neighbour kind is not built
    (milestone M8): NotImplementedError before any fit."""
    value = getattr(derived["R12"].value, "value", derived["R12"].value)
    if value == KIND_NEIGHBOUR:
        raise NotImplementedError("the neighbour router kind (R12: fewer than %d valid rows per unit) is built "
                                  "at milestone M8 (neighbour track); nothing was fitted"
                                  % int(K.REGION_MIN_VALID_ROWS))
    if value not in (KIND_PER_UNIT, KIND_REGION):
        raise RouterRefusal("R12", "derived.json's router kind %r is not per_unit, region or neighbour" % (value,))
    return value


def link_arg(link: Any, c: Optional[float], ub: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
    """The (c, ub) a link's transform takes: c for log_c only, ub for arcsine only."""
    return (c if link == Link.LOG_C else None), (ub if link == Link.ARCSINE else None)


def to_y(z: np.ndarray, link: Any, c: Optional[float], ub: Optional[float], legal: Tuple[float, float]) -> np.ndarray:
    """Link space to y units with the legal clip (R28): what the fallback level search scores."""
    return clip_to_legal(ST.inverse(z, link, c, ub), legal, False)[0]


@dataclass
class PassInput:
    """One pass: its FitContext (the cut), the tree-answer store and masks of its bank, the feature source
    its tables are built from, the score rows (pass order: unit, step, grid position), the R36
    tolerance and the donor-row link mean per link (R15's last fallback), the router_rows purpose, and
    the log_c link's c at the pass's lead cut (R23: one c per lead cut; None without log_c)."""
    what: str
    ctx: Any
    store: Any
    masks: Any
    features: Any
    score_units: np.ndarray
    score_steps: np.ndarray
    score_keys: np.ndarray
    tol: Mapping[Any, float]
    donor_mean: Mapping[Any, float]
    purpose: str
    c: Optional[float]
    schedule: Any = None            # GroupTables: per-group batching (module docstring); None: tables prebuilt


@dataclass
class GroupTables:
    """Plan R20's per-group batching of one pass's tree-answer tables (module docstring). groups: every group
    whose scored-unit rows the whole schedule builds before the pass, in that order; build(group) builds them
    (the same ids, kinds and order as RunState._build_tables); drop(group) releases every table of the group
    (TreeAnswerStore.drop_group). drops counts the groups released."""
    groups: Tuple[str, ...]
    build: Callable[[str], None]
    drop: Callable[[str], Any]
    drops: int = 0


@dataclass
class RoutedPass:
    """What one pass routed, in LINK space: every arm's predictions (rows, points), each routed link's
    trees-off and score-row normal, and the fallback / region records."""
    grid: Tuple[Any, ...]
    predictions: Dict[str, np.ndarray] = field(default_factory=dict)
    trees_off: Dict[Any, np.ndarray] = field(default_factory=dict)
    score_normal: Dict[Any, np.ndarray] = field(default_factory=dict)
    normal_tables: Dict[Any, Any] = field(default_factory=dict)     # per-unit kind: each link's NormalTables
    records: Dict[str, Any] = field(default_factory=dict)
    plumbing: Dict[str, Any] = field(default_factory=dict)


class PassRouter(object):
    """Routes the arms of one pass by the run's router kind (module docstring).

    state: the run's RunState (lists, unit_group, season, c, ub, legal, scored_units, vg). kind: 'per_unit'
    or 'region'. weights: a callable fit grid positions -> R25 weights (one per row), or None when no GLS
    arm is routed. fallback_levels: {'<link>|<table>': {'level': ...}} found on a surface (the decision
    surface's for the nowcast's test pass, a lead's guard surface's for that lead's test pass); None on a
    surface that searches its own. search_levels: the pass is a surface routed at ONE point whose R12
    fallback level is searched on its own rows (a forecast lead's guard, owner ruling H5); it needs the
    surface labels (route's y_surface) and takes no fallback_levels."""

    def __init__(self, state: Any, inp: PassInput, kind: str, weights: Optional[Callable[[np.ndarray], np.ndarray]] = None,
                 fallback_levels: Optional[Mapping[str, Any]] = None, search_levels: bool = False) -> None:
        if search_levels and fallback_levels:
            raise RouterRefusal("R12", "%s: a pass that searches its own fallback level (owner ruling H5) reads no "
                                "other surface's levels" % inp.what)
        self.s = state
        self.inp = inp
        self.kind = kind
        self.weights_fn = weights
        self.search_levels = bool(search_levels)
        self.levels_in = dict(fallback_levels or {})
        self.levels_found: Dict[str, Any] = {}
        self._rows = None
        self._w = None
        self._pr: Dict[Any, Any] = {}
        self._normal_tables: Dict[Any, Any] = {}
        self._fb_router_rows: Dict[str, Any] = {}
        self._fb_rows: Dict[Any, Any] = {}
        self._fb_out: Dict[Tuple[str, str], Any] = {}
        self._all_short: Dict[Any, int] = {}
        self.records_fallback: Dict[str, Any] = {}
        # per-group batching (module docstring): the walk's fallback outputs per (link, table) and group
        self._grouped = inp.schedule is not None
        self._fb_groups: Dict[Tuple[str, str], Dict[str, Any]] = {}

    # ------------------------------------------------------------------ shared pieces
    def _c_ub(self, link: Any) -> Tuple[Optional[float], Optional[float]]:
        return link_arg(link, self.inp.c, self.s.ub)

    def _build(self, group: str, table_kind: str, keys: np.ndarray) -> None:
        """Build the store rows a router will read (rows already built are not recomputed)."""
        ids = np.asarray(keys, dtype=np.int64)
        if ids.size:
            self.inp.store.build(group, table_kind, ids, ST.zero_filled(self.inp.features))

    def _group_of_rows(self, units: np.ndarray) -> np.ndarray:
        ug = self.s.unit_group
        return np.asarray([ug[u] for u in units.tolist()], dtype=object)

    # ------------------------------------------------------------------ per-unit
    def _pass_rows(self) -> Any:
        if self._rows is None:
            rows = ST.pass_rows(self.inp.ctx, self.s.scored_units, self.inp.score_units, self.inp.score_steps,
                                self.inp.score_keys, self.inp.purpose)
            # owner ruling G1: the kept router rows' log twin, and every row left out, saved before any fit
            self.s.log_g1_kept(self.inp.ctx, rows.fit_log)
            if rows.left_out is not None:
                rows.context_missing["rows_file"] = self.s.save_context_missing_rows(
                    self.inp.what, rows.left_out.frame(self.inp.what, self.inp.purpose))
            self._rows = rows
            self._print_context_missing(rows.context_missing)
        return self._rows

    def _print_context_missing(self, rec: Optional[Mapping[str, Any]]) -> None:
        """Owner ruling G1: the fit rows this pass left out for missing router context, printed (one line;
        each unit's count on its own line, in run.log, and on the console too when the unit is flagged)."""
        if rec is None:
            return
        log, what = self.s.log, self.inp.what
        if not rec["rows_left_out"]:
            log("%s: G1: all %d router fit rows of %d units have their context; none left out"
                % (what, rec["fit_rows"], rec["units_in_fit"]))
            return
        shares = [d["share"] for d in rec["by_unit"].values()]
        counts = [d["left_out"] for d in rec["by_unit"].values()]
        steps = sorted(int(t) for t in rec["by_step"])
        log("%s: G1 left %d of %d router fit rows out (router context missing or non-finite; nothing filled): "
            "%d of %d units, %d to %d rows each (largest share %.1f%%), steps %d..%d, by column %s; flagged above "
            "%.0f%% of a unit's fit rows: %s; rows saved in %s"
            % (what, rec["rows_left_out"], rec["fit_rows"], rec["units_with_rows_left_out"], rec["units_in_fit"],
               min(counts), max(counts), 100.0 * max(shares), steps[0], steps[-1], rec["by_column"],
               100.0 * rec["flag_share"], ("%d units" % len(rec["flagged_units"])) if rec["flagged_units"] else "none",
               rec.get("rows_file")))
        for u in sorted(rec["by_unit"]):
            d = rec["by_unit"][u]
            line = ("%s: G1 unit %s: %d of %d fit rows left out (%.1f%%)%s"
                    % (what, u, d["left_out"], d["fit_rows"], 100.0 * d["share"], " FLAGGED" if d["flagged"] else ""))
            if d["flagged"]:
                log(line)
            else:
                log.file_only(line)

    def _per_unit_rows(self, link: Any) -> Any:
        if link not in self._pr:
            rows = self._pass_rows()
            # G1: a unit that lost fit rows for missing context takes its normal from its kept fit rows (R15),
            # its trimmed history logged as the 'normal' hand-out's twin
            hist, kept_log = ST.context_kept_histories(self.inp.ctx, self.s.scored_units, rows)
            self.s.log_g1_kept(self.inp.ctx, kept_log)
            normals = ST.unit_normals(self.inp.ctx, self.s.scored_units, link, self.inp.c, self.s.ub,
                                      self.inp.donor_mean[link], self.s.season, histories=hist)
            self._normal_tables[link] = normals
            self._pr[link] = ST.per_unit_rows(rows, link, self.inp.c, self.s.ub, normals, self.s.season,
                                              self.s.unit_group)
        return self._pr[link]

    def fit_weights(self) -> np.ndarray:
        """The R25 weights of the per-unit pass's fit rows (one per row, in the rows' order)."""
        if self._w is None:
            if self.weights_fn is None:
                raise RouterRefusal("R25", "%s: a GLS arm was asked for, but no weight model serves this pass"
                                    % self.inp.what)
            keys = np.asarray(self._pass_rows().fit.row_positions, dtype=np.int64)
            w = np.asarray(self.weights_fn(keys), dtype=np.float64)
            if w.shape != keys.shape:
                raise RouterRefusal("R25", "%s: %d weights for %d fit rows" % (self.inp.what, w.size, keys.size))
            self._w = w
        return self._w

    def _fallback_region_rows(self, pr: Any, plan: Any, link: Any) -> Dict[str, Any]:
        """RegionRows of each group with a short-history unit: fit rows = the group's BANK units' valid
        rows at or before the cut (L2 rule 3), score rows = the short units' rows of this pass (their
        positions in the pass as score_rows, so fill_fallback puts them back)."""
        key = link
        if key in self._fb_rows:
            return self._fb_rows[key]
        ctx = self.inp.ctx
        c, _ = self._c_ub(link)
        out = {}
        for g in sorted(plan.by_group):
            bank = tuple(sorted(self.s.lists.bank[g]))
            rr = self._fb_router_rows.get(g)
            if rr is None:
                rr = ctx.router_rows(bank, self.inp.purpose + ":fallback")
                self._fb_router_rows[g] = rr
            normals = ST.unit_normals(ctx, bank, link, self.inp.c, self.s.ub, self.inp.donor_mean[link], self.s.season)
            fu = np.asarray(rr.unit_ids, dtype=object)
            ft = np.asarray(rr.times, dtype=np.int64)
            cc, uu = self._c_ub(link)
            fy = link_forward(np.asarray(rr.y, dtype=np.float64), link, cc, uu)
            fn = ST._normals_on(normals, fu, ST.season_keys_of(ft, self.s.season), link, int(ctx.cut), c)
            sel = np.flatnonzero(np.isin(np.asarray(pr.score_unit, dtype=object),
                                         np.asarray(plan.by_group[g], dtype=object)))
            out[g] = RR.RegionRows(cut=int(ctx.cut), group=g, fit_units=bank, scored_units=tuple(plan.by_group[g]),
                                   fit_unit=fu, fit_time=ft, fit_y=fy, fit_normal=fn,
                                   fit_keys=np.asarray(rr.row_positions, dtype=np.int64),
                                   score_unit=np.asarray(pr.score_unit, dtype=object)[sel],
                                   score_time=np.asarray(pr.score_time, dtype=np.int64)[sel],
                                   score_normal=np.asarray(pr.score_normal, dtype=np.float64)[sel],
                                   score_keys=np.asarray(pr.score_keys, dtype=np.int64)[sel], score_rows=sel)
        self._fb_rows[key] = out
        return out

    def _level_key(self, link: Any, table_kind: str) -> str:
        return "%s|%s" % (getattr(link, "value", link), table_kind)

    def _decided_level(self, link: Any, table_kind: str) -> Any:
        """The fallback level of this link and table: the one this pass just found, or the one the surface
        it reads found (the decision surface's for the nowcast's test pass, the lead's guard surface's for a
        lead's test pass, owner ruling H5). The placebo, never on a surface, takes its corrector's level."""
        for name in (table_kind, "corrector") if table_kind == "placebo_corrector" else (table_kind,):
            key = self._level_key(link, name)
            doc = self.levels_found.get(key) or self.levels_in.get(key)
            if doc is not None:
                return RK.GridPoint(float(doc["level"]), None)
        raise RouterRefusal("R12", "%s: no fallback level was found on the surface this pass reads for %s; the "
                            "level is searched on a surface (the decision surface, or a lead's own guard surface)"
                            % (self.inp.what, self._level_key(link, table_kind)),
                            fix="the surface records a level for every link and table it routes")

    def _searches(self, point: Any) -> bool:
        """True when this pass searches its own fallback level: the decision surface (every grid point) or a
        surface routed at one point with search_levels (a lead's guard, owner ruling H5)."""
        return point is None or self.search_levels

    def _centre_level(self, key: str) -> None:
        """No short-history unit on this surface for a link and table: C15's rule for fewer than
        FALLBACK_MIN_UNITS_FOR_SEARCH fallback units gives the centre (0 units here)."""
        if key not in self.levels_found:
            self.levels_found[key] = {"level": float(RR.region_centre().level), "used_centre": True,
                                      "fallback_units_scored": 0, "surface_mae_by_level": None}

    def _search_outputs(self, pr: Any, plan: Any, rows: Mapping[str, Any], link: Any, table_kind: str,
                        y_surface: Optional[np.ndarray]) -> Any:
        """R12's level search on this pass's own surface: each group's fallback region router at every region
        level (route_fallback_grid, kept per link and table), scored on the fallback units' surface rows
        pooled across groups (fallback_surface_mae, search_fallback_level: the lambda centre below C15's
        count). The level found goes to levels_found. Returns the grid outputs."""
        bank = {g: tuple(sorted(self.s.lists.bank[g])) for g in rows}
        ck = (getattr(link, "value", link), table_kind)
        c, ub = self._c_ub(link)
        outs = self._fb_out.get(ck)
        if outs is None:
            self._not_grouped(ck)
            outs = RR.route_fallback_grid(rows, bank, plan, self.inp.store, table_kind, self.inp.masks,
                                          self.inp.tol[link])
            self._fb_out[ck] = outs
        key = self._level_key(link, table_kind)
        if key not in self.levels_found:
            if y_surface is None:
                raise RouterRefusal("R12", "internal: the fallback level search needs the surface labels")
            y_true = {g: np.asarray(y_surface, dtype=np.float64)[np.asarray(o.row_positions, dtype=np.int64)]
                      for g, o in outs.items()}
            units = {g: np.asarray(pr.score_unit, dtype=object)[np.asarray(o.row_positions, dtype=np.int64)]
                     for g, o in outs.items()}
            mae, n_units = RR.fallback_surface_mae(outs, y_true, units,
                                                   lambda z, L=link: to_y(z, L, c, ub, self.s.legal))
            level, used_centre = RR.search_fallback_level(mae, n_units, RR.region_centre())
            self.levels_found[key] = {"level": float(level.level), "used_centre": bool(used_centre),
                                      "fallback_units_scored": int(n_units),
                                      "surface_mae_by_level": {repr(float(p.level)): float(v)
                                                               for p, v in mae.items()}}
        return outs

    def search_level_only(self, link: Any, table_kind: str, y_surface: np.ndarray) -> None:
        """R12 / owner ruling H5: search this surface's fallback level for a link and table no arm of this pass
        routes (at the longest lead the placebo takes its corrector's level; when the pinned arm is plain, the
        guard surface searches the corrector table's level here). The short units' surface rows and their
        groups' bank rows are built in that table first. A surface without a short-history unit gives the
        centre (0 units). Per-unit kind, search mode only."""
        if not self.search_levels or self.kind != KIND_PER_UNIT:
            raise RouterRefusal("R12", "internal: %s does not search its own fallback level (a per-unit pass "
                                "with search_levels does)" % self.inp.what)
        key = self._level_key(link, table_kind)
        if key in self.levels_found:
            return
        pr = self._per_unit_rows(link)
        plan = RR.fallback_plan(RK.valid_fit_rows(pr), pr.unit_group)
        if not plan.short_units:
            self._centre_level(key)
            return
        rows = self._fallback_region_rows(pr, plan, link)
        if not self._grouped:          # per-group batching: the walk built these rows and routed each group
            for g, r in rows.items():
                self._build(g, table_kind, np.concatenate([np.asarray(r.fit_keys, dtype=np.int64),
                                                           np.asarray(r.score_keys, dtype=np.int64)]))
        self._search_outputs(pr, plan, rows, link, table_kind, y_surface)
        rec = self.records_fallback.setdefault(key, {})
        rec.update({"short_units": list(plan.short_units), "share": plan.share, "flagged": plan.flagged,
                    "groups": {g: list(v) for g, v in plan.by_group.items()},
                    "level": float(self.levels_found[key]["level"]),
                    "level_only": "searched for a table no arm of this pass routes (the placebo's corrector)"})

    def _fill_fallback(self, out: Any, pr: Any, link: Any, table_kind: str, point: Any,
                       y_surface: Optional[np.ndarray]) -> Any:
        """R12: fill the short-history units' NaN rows with their groups' fallback region routers (route/
        region.py's service). On a surface that searches its own level (the decision surface, point None; a
        lead's guard, search_levels, owner ruling H5) the level is searched once per link and table on the
        pooled fallback rows; later passes read it."""
        if not out.n_units_fallback:
            return out
        plan = RR.fallback_plan(RK.valid_fit_rows(pr), pr.unit_group)
        rows = self._fallback_region_rows(pr, plan, link)
        bank = {g: tuple(sorted(self.s.lists.bank[g])) for g in rows}
        if not self._grouped:          # per-group batching: the walk built these rows and routed each group
            for g, r in rows.items():
                self._build(g, table_kind, r.fit_keys)
        ck = (getattr(link, "value", link), table_kind)
        if self._searches(point):
            outs = self._search_outputs(pr, plan, rows, link, table_kind, y_surface)
            level = RK.GridPoint(float(self.levels_found[self._level_key(link, table_kind)]["level"]), None)
            filled = RR.fill_fallback(out, outs, level)
        else:
            level = self._decided_level(link, table_kind)
            outs = self._fb_out.get(ck)
            if outs is None:
                self._not_grouped(ck)
                outs = RR.route_fallback_at(rows, bank, plan, self.inp.store, table_kind, self.inp.masks, level,
                                            self.inp.tol[link])
                self._fb_out[ck] = outs
            filled = RR.fill_fallback(out, outs, level)
        rec = self.records_fallback.setdefault(self._level_key(link, table_kind), {})
        rec.update({"short_units": list(plan.short_units), "share": plan.share, "flagged": plan.flagged,
                    "groups": {g: list(v) for g, v in plan.by_group.items()}, "level": float(level.level)})
        return filled

    def _n_all_short(self, link: Any, pr: Any) -> int:
        """R12: the number of scored units of this pass when EVERY one of them is short (fewer than
        PER_UNIT_MIN_VALID_ROWS fit rows), else 0. The kernels refuse such a pass (they would fit no unit); it
        is routed whole by the fallback region routers instead (at a long lead the guard's fit rows end L - 1
        steps earlier, so a whole pass can fall short)."""
        if link not in self._all_short:
            plan, short = RK.per_unit_plan(pr)
            self._all_short[link] = 0 if plan else len(short)
        return self._all_short[link]

    def _all_short_output(self, pr: Any, point: Any, n_short: int) -> Any:
        """The per-unit output of an all-short pass: every row NaN (no unit fitted), n_units_fallback the
        short units, for _fill_fallback to fill (the point is checked as the kernels check it)."""
        has_ctx = pr.fit_context is not None
        if point is None:
            grid = RK.per_unit_grid(has_ctx)
        else:
            RK.point_penalties(point, has_ctx)
            grid = (point,)
        ns = int(np.asarray(pr.score_rows).size)
        return RK.RouteOutput(row_positions=np.asarray(pr.score_rows).copy(), predictions=np.full((ns, len(grid)), np.nan),
                              trees_off=np.full(ns, np.nan), grid=tuple(grid), n_units_fitted=0,
                              n_units_fallback=int(n_short), n_rows_pool_fallback=0)

    def _per_unit_route(self, pr: Any, table_kind: str, link: Any, point: Any, fit_weights: Optional[np.ndarray],
                        y_surface: Optional[np.ndarray]) -> Any:
        n_all = self._n_all_short(link, pr)
        if n_all:
            out = self._all_short_output(pr, point, n_all)
        elif point is None:
            out = RK._route_per_unit_grid(pr, self.inp.store, table_kind, self.inp.masks, self.inp.tol[link],
                                          fit_weights=fit_weights)
        else:
            out = RK._route_per_unit_at(pr, self.inp.store, table_kind, self.inp.masks, point, self.inp.tol[link],
                                        fit_weights=fit_weights)
        out = self._fill_fallback(out, pr, link, table_kind, point, y_surface)
        self._no_nan(out, "%s %s %s" % (self.inp.what, getattr(link, "value", link), table_kind))
        return out

    def _no_nan(self, out: Any, what: str) -> None:
        if np.isnan(out.predictions).any() or np.isnan(out.trees_off).any():
            raise RouterRefusal("R12", "%s: the router left NaN rows; a NaN router row is never scored" % what)

    def _trees_off_per_unit(self, link: Any) -> np.ndarray:
        """Trees-off alone (no tree answer read) with the fallback trees-off on short-history rows."""
        pr = self._per_unit_rows(link)
        n_all = self._n_all_short(link, pr)
        if n_all:
            p0, n_short = np.full(int(np.asarray(pr.score_rows).size), np.nan), n_all
        else:
            p0, _, n_short = RK._trees_off_per_unit(pr, self.inp.tol[link])
        if n_short:
            plan = RR.fallback_plan(RK.valid_fit_rows(pr), pr.unit_group)
            for g, r in self._fallback_region_rows(pr, plan, link).items():
                p0[np.asarray(r.score_rows, dtype=np.int64)] = self._region_trees_off(r, link)
        if np.isnan(p0).any():
            raise RouterRefusal("R12", "%s: trees-off left NaN rows" % self.inp.what)
        return p0

    # ------------------------------------------------------------------ region
    def _region_trees_off(self, rows: Any, link: Any) -> np.ndarray:
        """The region router's trees-off without its tree block: intercept + normal on the capped fit rows
        (the kernel's own cap and trees-off, route/region.py _route), asserted equal to the normal."""
        fu = np.array([str(u) for u in np.asarray(rows.fit_unit, dtype=object).tolist()], dtype=object)
        counts = {u: 0 for u in rows.fit_units}
        uniq, cnt = np.unique(fu.astype(str), return_counts=True)
        for u, n in zip(uniq.tolist(), cnt.tolist()):
            counts[u] = int(n)
        kept = RR.region_cap_units(tuple(rows.fit_units), counts, int(K.REGION_ROUTER_ROW_BUDGET))
        pos = np.flatnonzero(np.isin(fu, np.asarray(kept, dtype=object)))
        return RK._trees_off_checked(np.asarray(rows.fit_normal, dtype=np.float64)[pos],
                                     np.asarray(rows.fit_y, dtype=np.float64)[pos],
                                     np.asarray(rows.score_normal, dtype=np.float64), self.inp.tol[link],
                                     "group %s region router" % rows.group)

    def _region_groups(self) -> List[Tuple[str, np.ndarray]]:
        """(group, pass row indices of its scored units' rows) for every group with a row in the pass."""
        groups = self._group_of_rows(np.asarray(self.inp.score_units, dtype=object))
        out = []
        for g in sorted(set(groups.tolist())):
            out.append((g, np.flatnonzero(groups == g)))
        return out

    def _region_rows(self, g: str, sel: np.ndarray, link: Any, rr: Any) -> Any:
        ctx = self.inp.ctx
        bank = tuple(sorted(self.s.lists.bank[g]))
        scored = tuple(sorted(self.s.lists.scored[g]))
        c, _ = self._c_ub(link)
        cc, uu = self._c_ub(link)
        normals = ST.unit_normals(ctx, bank, link, self.inp.c, self.s.ub, self.inp.donor_mean[link], self.s.season)
        fu = np.asarray(rr.unit_ids, dtype=object)
        ft = np.asarray(rr.times, dtype=np.int64)
        su = np.asarray(self.inp.score_units, dtype=object)[sel]
        st = np.asarray(self.inp.score_steps, dtype=np.int64)[sel]
        return RR.RegionRows(
            cut=int(ctx.cut), group=g, fit_units=bank, scored_units=scored, fit_unit=fu, fit_time=ft,
            fit_y=link_forward(np.asarray(rr.y, dtype=np.float64), link, cc, uu),
            fit_normal=ST._normals_on(normals, fu, ST.season_keys_of(ft, self.s.season), link, int(ctx.cut), c),
            fit_keys=np.asarray(rr.row_positions, dtype=np.int64), score_unit=su, score_time=st,
            score_normal=ST._normals_on(normals, su, ST.season_keys_of(st, self.s.season), link, int(ctx.cut), c),
            score_keys=np.asarray(self.inp.score_keys, dtype=np.int64)[sel], score_rows=sel)

    def _route_region(self, arms: Sequence[Any], point: Any, extra_trees_off: Sequence[Any],
                      plumbing: bool) -> RoutedPass:
        grid = RR.region_grid() if point is None else (point,)
        n = int(np.asarray(self.inp.score_units).size)
        res = RoutedPass(grid=tuple(grid))
        links = _links_of(arms, extra_trees_off)
        for arm in arms:
            if arm.weighting is LA.Weighting.GLS:
                raise RouterRefusal("R25", "%s: %s" % (self.inp.what, REGION_GLS_ABSENT))
            res.predictions[LA.arm_name(arm)] = np.full((n, len(grid)), np.nan)
        for L in links:
            res.trees_off[L] = np.full(n, np.nan)
            res.score_normal[L] = np.full(n, np.nan)
        centre = RR.region_centre()
        unswept = {L: np.full(n, np.nan) for L in links} if plumbing else {}
        kept_units = {}
        with_rows = self._region_groups()
        if self._grouped:
            sel_of = dict(with_rows)
            stray = sorted(set(sel_of) - set(self.inp.schedule.groups))
            if stray:
                raise RouterRefusal("R20", "%s: groups %s hold score rows but are not in the pass's group walk"
                                    % (self.inp.what, stray[:5]))
            walk = [(g, sel_of.get(g)) for g in self.inp.schedule.groups]
        else:
            walk = with_rows
        for g, sel in walk:
            if self._grouped:
                self._walk_build(g)
                if sel is None:                   # no score row of this group in the pass
                    self._walk_drop(g)
                    continue
            bank = tuple(sorted(self.s.lists.bank[g]))
            rr = self.inp.ctx.router_rows(bank, self.inp.purpose)
            rows = {L: self._region_rows(g, sel, L, rr) for L in links}
            kinds = []
            for arm in arms:
                k = LA.table_kind(arm)
                if k not in kinds:
                    kinds.append(k)
            for L in links:
                res.score_normal[L][sel] = rows[L].score_normal
            for k in kinds:
                self._build(g, k, np.concatenate([np.asarray(rr.row_positions, dtype=np.int64),
                                                  np.asarray(self.inp.score_keys, dtype=np.int64)[sel]]))
                arms_k = [a for a in arms if LA.table_kind(a) == k]
                link_order = [L for L in links if any(a.link == L for a in arms_k)]
                gram = RR.region_shared_gram(rows[link_order[0]], self.inp.store, k, self.inp.masks)
                for L in link_order:
                    if point is None:
                        out = RR._route_region_grid(rows[L], self.inp.store, k, self.inp.masks, self.inp.tol[L],
                                                    gram=gram)
                    else:
                        out = RR._route_region_at(rows[L], self.inp.store, k, self.inp.masks, point, self.inp.tol[L],
                                                  gram=gram)
                    pos = np.asarray(out.row_positions, dtype=np.int64)
                    for a in arms_k:
                        if a.link == L:
                            res.predictions[LA.arm_name(a)][pos, :] = out.predictions
                    res.trees_off[L][pos] = out.trees_off
                    kept_units[g] = int(out.n_units_fitted)
                    if plumbing and k == "plain" and point is None:
                        one = RR._route_region_at(rows[L], self.inp.store, k, self.inp.masks, centre, self.inp.tol[L],
                                                  gram=gram)
                        unswept[L][pos] = one.predictions[:, 0]
                del gram
            for L in extra_trees_off:
                if np.isnan(res.trees_off[L][sel]).any():
                    res.trees_off[L][sel] = self._region_trees_off(rows[L], L)
            if self._grouped:
                self._walk_drop(g)
        for name, v in res.predictions.items():
            if np.isnan(v).any():
                raise RouterRefusal("R14", "%s: arm %s left NaN rows" % (self.inp.what, name))
        for L, v in res.trees_off.items():
            if np.isnan(v).any():
                raise RouterRefusal("R16", "%s: trees-off of %s left NaN rows" % (self.inp.what, L.value))
        res.records["region"] = {"capped_units_fitted_by_group": kept_units,
                                 "row_budget": int(K.REGION_ROUTER_ROW_BUDGET),
                                 "shared_gram": "one tree-block Gram per group and table, shared across the links "
                                                "(L4, region_shared_gram)"}
        if plumbing and point is None:
            k = list(grid).index(centre)
            for L in links:
                name = LA.arm_name(LA.ArmSpec(L, LA.Tool.PLAIN, LA.Weighting.UNWEIGHTED, True))
                if name in res.predictions:
                    res.plumbing[L.value] = _plumb(res.trees_off[L], res.score_normal[L],
                                                   res.predictions[name][:, k], unswept[L], None, None,
                                                   self.inp.tol[L], "%s %s" % (self.inp.what, L.value))
        return res

    # ------------------------------------------------------------------ entry point
    def route(self, arms: Sequence[Any], point: Any = None, y_surface: Optional[np.ndarray] = None,
              extra_trees_off: Sequence[Any] = (), plumbing: bool = False,
              level_tables: Sequence[Tuple[Any, str]] = ()) -> RoutedPass:
        """Route the given tree arms (LA.ArmSpec, plain / corrector / placebo, unweighted or GLS) at every
        grid point (point None: the decision surface) or at one point; trees-off of every arm's link, and
        of each link in extra_trees_off (the decline target's link at a lead). plumbing (decision
        surface only): G-PLUMB per link (trees-off = normal; the centre point reproduces the un-swept
        route; for a GLS arm, equal weights reproduce the unweighted arm). level_tables (a pass with
        search_levels only): (link, table kind) pairs whose R12 fallback level this surface also searches
        without routing an arm (search_level_only; the placebo's corrector at the longest lead)."""
        for arm in arms:
            LA.check_arm(arm)
            if arm.tool is LA.Tool.TREES_OFF:
                raise RouterRefusal("R24", "trees-off is routed with its link, not as an arm")
        if self.search_levels and y_surface is None:
            raise RouterRefusal("R12", "%s: a pass that searches its own fallback level needs its surface labels"
                                % self.inp.what)
        if level_tables and not self.search_levels:
            raise RouterRefusal("R12", "%s: level_tables are searched only by a pass with search_levels"
                                % self.inp.what)
        if self.kind == KIND_REGION:
            return self._route_region(arms, point, tuple(extra_trees_off), plumbing)
        if self._grouped:
            return self._route_per_unit_grouped(arms, point, y_surface, tuple(extra_trees_off), plumbing,
                                                tuple(level_tables))
        has_ctx = bool(tuple(self.inp.ctx.features.context_columns))
        grid = RK.per_unit_grid(has_ctx) if point is None else (point,)
        res = RoutedPass(grid=tuple(grid))
        links = _links_of(arms, extra_trees_off)
        for L in links:
            pr = self._per_unit_rows(L)
            res.score_normal[L] = np.asarray(pr.score_normal, dtype=np.float64)
            res.normal_tables[L] = self._normal_tables[L]
            for arm in [a for a in arms if a.link == L]:
                k = LA.table_kind(arm)
                fw = self.fit_weights() if arm.weighting is LA.Weighting.GLS else None
                out = self._per_unit_route(pr, k, L, point, fw, y_surface)
                if self._searches(point):
                    # no short-history unit on the surface for this link and table: the centre (0 units)
                    self._centre_level(self._level_key(L, k))
                res.predictions[LA.arm_name(arm)] = out.predictions
                if L not in res.trees_off:
                    res.trees_off[L] = out.trees_off
                if plumbing and point is None and arm.tool is LA.Tool.PLAIN and arm.weighting is LA.Weighting.UNWEIGHTED:
                    res.plumbing[L.value] = self._plumbing(pr, out, L, has_ctx, arms)
            if L not in res.trees_off:
                res.trees_off[L] = self._trees_off_per_unit(L)
        for L, k in level_tables:
            self.search_level_only(L, k, np.asarray(y_surface, dtype=np.float64))
        if self._rows is not None and self._rows.context_missing is not None:
            res.records["context_missing"] = self._rows.context_missing          # owner ruling G1
        if any(self._all_short.values()):
            res.records["all_short"] = {getattr(L, "value", str(L)): n for L, n in self._all_short.items() if n}
        if self.records_fallback:
            res.records["fallback"] = dict(self.records_fallback)
            if any(a.weighting is LA.Weighting.GLS for a in arms):
                res.records["fallback_gls_note"] = FALLBACK_GLS_NOTE
        if self.levels_found:
            res.records["fallback_levels"] = dict(self.levels_found)
        return res

    # ------------------------------------------------------------------ per-group batching (module docstring)
    def _not_grouped(self, ck: Any) -> None:
        """A grouped pass routes no table after its walk: the fallback outputs must come from the walk."""
        if self._grouped:
            raise RouterRefusal("R20", "internal: %s: the fallback outputs of %s were not computed in the group walk; "
                                "a grouped pass reads no table after its walk" % (self.inp.what, ck))

    def _walk_build(self, g: str) -> None:
        self.inp.schedule.build(g)

    def _walk_drop(self, g: str) -> None:
        self.inp.schedule.drop(g)
        self.inp.schedule.drops += 1

    def _walk_fallback(self, g: str, link: Any, table_kind: str, point: Any, with_score_rows: bool) -> None:
        """One group's fallback region router for (link, table) inside the walk, while the group's tables are on
        disk: its bank units' fit rows built (and the short units' score rows for a table no arm of the pass
        built: search_level_only's case), then the region grid on a surface that searches its level, or the one
        level the surface this pass reads found. Kept per (link, table) and group; the level search and the
        fill run after the walk on these outputs."""
        ck = (getattr(link, "value", link), table_kind)
        done = self._fb_groups.setdefault(ck, {})
        if g in done:
            return
        r = self._fb_rows[link][g]
        keys = np.asarray(r.fit_keys, dtype=np.int64)
        if with_score_rows:
            keys = np.concatenate([keys, np.asarray(r.score_keys, dtype=np.int64)])
        self._build(g, table_kind, keys)
        if self._searches(point):
            done[g] = RR._route_region_grid(r, self.inp.store, table_kind, self.inp.masks, self.inp.tol[link])
        else:
            done[g] = RR._route_region_at(r, self.inp.store, table_kind, self.inp.masks,
                                          self._decided_level(link, table_kind), self.inp.tol[link])

    def _merge(self, acc: List[Any], out: Any, rows_g: np.ndarray) -> None:
        acc[0][rows_g] = out.predictions[rows_g]
        acc[1][rows_g] = out.trees_off[rows_g]
        acc[2] += int(out.n_units_fitted)

    def _merged(self, pr: Any, acc: List[Any], grid: Sequence[Any], n_short: int) -> Any:
        return RK.RouteOutput(row_positions=np.asarray(pr.score_rows).copy(), predictions=acc[0], trees_off=acc[1],
                              grid=tuple(grid), n_units_fitted=int(acc[2]), n_units_fallback=int(n_short),
                              n_rows_pool_fallback=0)

    def _route_per_unit_grouped(self, arms: Sequence[Any], point: Any, y_surface: Optional[np.ndarray],
                                extra_trees_off: Sequence[Any], plumbing: bool,
                                level_tables: Sequence[Tuple[Any, str]]) -> RoutedPass:
        """The per-unit pass of route(), one group at a time (module docstring): the same outputs, records and
        fitctx hand-outs, with one group's tables on disk at a time."""
        sched = self.inp.schedule
        has_ctx = bool(tuple(self.inp.ctx.features.context_columns))
        grid = RK.per_unit_grid(has_ctx) if point is None else (point,)
        res = RoutedPass(grid=tuple(grid))
        links = _links_of(arms, extra_trees_off)
        # 1. before the walk, in the whole pass's order: every FitContext hand-out (the pass rows, the normals,
        # the fallback groups' router rows and normals), the unit plans and the fallback plans
        plans: Dict[Any, Any] = {}
        n_short: Dict[Any, int] = {}
        for L in list(links) + [L for L, _ in level_tables if L not in links]:
            pr = self._per_unit_rows(L)
            _, short = RK.per_unit_plan(pr)
            n_short[L] = len(short)
            if short:
                plan = RR.fallback_plan(RK.valid_fit_rows(pr), pr.unit_group)
                rows = self._fallback_region_rows(pr, plan, L)
                RR._check_fallback_rows(rows, {g: tuple(sorted(self.s.lists.bank[g])) for g in rows}, plan)
                plans[L] = plan
        ns = int(np.asarray(self.inp.score_units).size)
        score_group = self._group_of_rows(np.asarray(self.inp.score_units, dtype=object))
        stray = sorted(set(score_group.tolist()) - set(sched.groups))
        if stray:
            raise RouterRefusal("R20", "%s: groups %s hold score rows but are not in the pass's group walk"
                                % (self.inp.what, stray[:5]))
        acc = {LA.arm_name(a): [np.full((ns, len(grid)), np.nan), np.full(ns, np.nan), 0] for a in arms}
        centre = RK.per_unit_centre(has_ctx)
        plumb: Dict[Any, Dict[str, Any]] = {}
        if plumbing and point is None:
            for L in links:
                if any(a.link == L and a.tool is LA.Tool.PLAIN and a.weighting is LA.Weighting.UNWEIGHTED for a in arms):
                    gls = any(a.link == L and a.weighting is LA.Weighting.GLS for a in arms)
                    w = self.fit_weights() if gls else None
                    plumb[L] = {"one": [np.full((ns, 1), np.nan), np.full(ns, np.nan), 0],
                                "eq": [np.full((ns, 1), np.nan), np.full(ns, np.nan), 0] if gls else None,
                                "equal": np.full(w.size, float(np.median(w))) if gls else None}
        arm_keys = {(a.link, LA.table_kind(a)) for a in arms}
        # 2. the walk: one group's tables on disk at a time
        for g in sched.groups:
            self._walk_build(g)
            rows_g = np.flatnonzero(score_group == g)
            if rows_g.size:
                for L in links:
                    pr = self._pr[L]
                    n_all = self._n_all_short(L, pr)
                    fb_here = L in plans and g in plans[L].by_group
                    for arm in [a for a in arms if a.link == L]:
                        k = LA.table_kind(arm)
                        if not n_all:
                            fw = self.fit_weights() if arm.weighting is LA.Weighting.GLS else None
                            if point is None:
                                out = RK._route_per_unit_grid(pr, self.inp.store, k, self.inp.masks, self.inp.tol[L],
                                                              fit_weights=fw, only_group=g)
                            else:
                                out = RK._route_per_unit_at(pr, self.inp.store, k, self.inp.masks, point,
                                                            self.inp.tol[L], fit_weights=fw, only_group=g)
                            self._merge(acc[LA.arm_name(arm)], out, rows_g)
                        if fb_here:
                            self._walk_fallback(g, L, k, point, False)
                    if L in plumb and not n_all:
                        one = RK._route_per_unit_at(pr, self.inp.store, "plain", self.inp.masks, centre,
                                                    self.inp.tol[L], fit_weights=None, only_group=g)
                        self._merge(plumb[L]["one"], one, rows_g)
                        if plumb[L]["eq"] is not None:
                            eq = RK._route_per_unit_at(pr, self.inp.store, "plain", self.inp.masks, centre,
                                                       self.inp.tol[L], fit_weights=plumb[L]["equal"], only_group=g)
                            self._merge(plumb[L]["eq"], eq, rows_g)
                for L, k in level_tables:
                    if (L, k) not in arm_keys and L in plans and g in plans[L].by_group:
                        self._walk_fallback(g, L, k, point, True)
            self._walk_drop(g)
        for ck, done in self._fb_groups.items():
            want = sorted(next(plans[L] for L in plans if getattr(L, "value", L) == ck[0]).by_group)
            if sorted(done) != want:
                raise RouterRefusal("R20", "internal: %s: the walk routed the fallback groups %s of %s, the plan's are %s"
                                    % (self.inp.what, sorted(done), ck, want))
            self._fb_out[ck] = {g: done[g] for g in sorted(done)}
        # 3. after the walk, in the whole pass's order: the fills (and the level searches), G-PLUMB, trees-off
        for L in links:
            pr = self._pr[L]
            res.score_normal[L] = np.asarray(pr.score_normal, dtype=np.float64)
            res.normal_tables[L] = self._normal_tables[L]
            n_all = self._n_all_short(L, pr)
            for arm in [a for a in arms if a.link == L]:
                k = LA.table_kind(arm)
                out = self._all_short_output(pr, point, n_all) if n_all else \
                    self._merged(pr, acc[LA.arm_name(arm)], grid, n_short[L])
                out = self._fill_fallback(out, pr, L, k, point, y_surface)
                self._no_nan(out, "%s %s %s" % (self.inp.what, getattr(L, "value", L), k))
                if self._searches(point):
                    self._centre_level(self._level_key(L, k))
                res.predictions[LA.arm_name(arm)] = out.predictions
                if L not in res.trees_off:
                    res.trees_off[L] = out.trees_off
                if L in plumb and arm.tool is LA.Tool.PLAIN and arm.weighting is LA.Weighting.UNWEIGHTED:
                    res.plumbing[L.value] = self._plumbing_grouped(pr, out, L, has_ctx, plumb[L], n_all, n_short[L])
            if L not in res.trees_off:
                res.trees_off[L] = self._trees_off_per_unit(L)
        for L, k in level_tables:
            self.search_level_only(L, k, np.asarray(y_surface, dtype=np.float64))
        if self._rows is not None and self._rows.context_missing is not None:
            res.records["context_missing"] = self._rows.context_missing          # owner ruling G1
        if any(self._all_short.values()):
            res.records["all_short"] = {getattr(L, "value", str(L)): n for L, n in self._all_short.items() if n}
        if self.records_fallback:
            res.records["fallback"] = dict(self.records_fallback)
            if any(a.weighting is LA.Weighting.GLS for a in arms):
                res.records["fallback_gls_note"] = FALLBACK_GLS_NOTE
        if self.levels_found:
            res.records["fallback_levels"] = dict(self.levels_found)
        return res

    def _plumbing_grouped(self, pr: Any, out: Any, link: Any, has_ctx: bool, accs: Mapping[str, Any], n_all: int,
                          n_short: int) -> Dict[str, Any]:
        """_plumbing on the walk's centre-point outputs (the same routes, filled after the walk)."""
        centre = RK.per_unit_centre(has_ctx)
        k = list(RK.per_unit_grid(has_ctx)).index(centre)
        what = "%s %s %s" % (self.inp.what, getattr(link, "value", link), "plain")

        def filled(acc):
            o = self._all_short_output(pr, centre, n_all) if n_all else self._merged(pr, acc, (centre,), n_short)
            o = self._fill_fallback(o, pr, link, "plain", centre, None)
            self._no_nan(o, what)
            return o
        one = filled(accs["one"])
        eq = unw = None
        if accs["eq"] is not None:
            eq = filled(accs["eq"]).predictions[:, 0]
            unw = out.predictions[:, k]
        return _plumb(out.trees_off, pr.score_normal, out.predictions[:, k], one.predictions[:, 0], eq, unw,
                      self.inp.tol[link], "%s %s" % (self.inp.what, getattr(link, "value", link)))

    def _plumbing(self, pr: Any, out: Any, link: Any, has_ctx: bool, arms: Sequence[Any]) -> Dict[str, Any]:
        """G-PLUMB on the plain arm of one link: trees-off equals the normal; the grid's centre point
        reproduces the un-swept route (one solve at that point); when the link has a GLS arm, the plain
        arm with EQUAL weights (every weight the median R25 weight of the pass) reproduces the unweighted
        arm at the centre (the trace-normalised penalty cancels a common factor)."""
        centre = RK.per_unit_centre(has_ctx)
        k = list(RK.per_unit_grid(has_ctx)).index(centre)
        one = self._per_unit_route(pr, "plain", link, centre, None, None)
        eq = unw = None
        if any(a.link == link and a.weighting is LA.Weighting.GLS for a in arms):
            w = self.fit_weights()
            equal = np.full(w.size, float(np.median(w)))
            eq = self._per_unit_route(pr, "plain", link, centre, equal, None).predictions[:, 0]
            unw = out.predictions[:, k]
        return _plumb(out.trees_off, pr.score_normal, out.predictions[:, k], one.predictions[:, 0], eq, unw,
                      self.inp.tol[link], "%s %s" % (self.inp.what, getattr(link, "value", link)))


def _links_of(arms: Sequence[Any], extra: Sequence[Any]) -> List[Any]:
    out: List[Any] = []
    for a in list(arms):
        if a.link not in out:
            out.append(a.link)
    for L in extra:
        if L not in out:
            out.append(L)
    return out


def _plumb(trees_off, normal, base, unswept, weighted_equal, unweighted, tol, what) -> Dict[str, Any]:
    from treeroute.layer import decide as LD

    result = LD.check_plumbing(trees_off, normal, base, unswept, weighted_equal, unweighted, None, None, tol)
    if result.status is LD.GuardStatus.BLOCK:
        raise RouterRefusal("G-PLUMB", "%s: %s (%s)" % (what, result.reason, result.details))
    return dict(result.details)


__all__ = ["KIND_PER_UNIT", "KIND_REGION", "KIND_NEIGHBOUR", "REGION_GLS_ABSENT", "FALLBACK_GLS_NOTE",
           "RouterRefusal", "router_kind", "link_arg", "to_y", "PassInput", "RoutedPass", "PassRouter"]
