"""'check': the quick checks (plan 6.1; plan 8.1 M1): package facts and verdicts only, in seconds.

What it reads: the package files (package.load), the feature script's declared outputs (its module is
executed as the pipeline does), the store listings (file names), the parquet footer of the first file of
each driver store and of the static table, and ONE target file, through the package's own target reader, for
R1's cadence (the same rule, derive_r01_cadence, on that file's rows). It reads no data pass: G-SUPPORT's donor
and census parts, G-MISSING's R30 flags, G-EPOCH's cut comparison and every deep guard wait for 'check --deep'.

The columns 'in the data' (G-CLOSED): the target reader's columns, every declared driver store's columns (a
store no run reads included: a column nobody declared is what the closed world catches), the static table's
columns except its plan 1.2 structure, and the feature outputs. Owner ruling J4: a stored column with store
facts but no catalog row and no verdict, named in derived_from by catalog columns, is declared through them
(listed in the G-CLOSED line, never refused).

Order: G-SPLIT, G-LINEAGE (its flags feed G-CLOSED), G-CLOSED, G-KEYS, G-LAG (with R4's first-year note),
G-EPOCH, G-HIST (declared), G-SUPPORT (groups), G-FACTS (headline: the freeze gate), G-MISSING, G-DERIVED
(the static scan of the feature script). A refusal never stops the other guards: every guard reports.
"""
# Provenance: plan 5 (the quick guards), 6.1 (check), 8.1 M1; owner rulings A, D, F, J5, L.

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from treeroute.errors import RefusedError

from . import guards as G
from .facts import FEATURE_STORE, KEY_ROLES, package_facts

ENTERING_ROLES_TREES = ("driver", "engineered")


class CheckContext(SimpleNamespace):
    """What the quick pass learned and the deep pass reuses: facts (check.facts.PackageFacts), target_listing,
    data_groups, groups (after exclusions), cadence (R1), cadence_source, data_columns, column_sets,
    entering ({name: facts} of tree features and router context), store_listings ([(template, listing,
    footer names)]), lags ({column: Lag} of R8), r4 (R4 note), results ([(part label, GuardResult)])."""


def _v(x: Any) -> Any:
    return getattr(x, "value", x)


def _target_spec(facts: Any) -> Any:
    """The pipeline's PackageSpec, or a keys-only stand-in when the closed world refuses (the readers need only
    the key columns and the target)."""
    from treeroute.pipeline import data as D

    try:
        return D.package_spec(D.augment_package(facts.loaded, facts.outputs)), None
    except RefusedError as exc:
        spec = D.PackageSpec(unit_col=facts.unit_col, group_col=facts.group_col, time_facts=dict(facts.time_facts),
                             target_col=facts.target.name, legal_range=tuple(facts.target.legal_range or (0.0, 0.0)),
                             measurement_error_floor=None, roles={c: f.role for c, f in facts.columns.items()},
                             store_facts={}, tree_features=(), context=(), frozen=(), listed_in_reports=(),
                             feature_outputs=tuple(sorted(facts.outputs)))
        return spec, str(exc)


def read_r1(ctx: CheckContext, echo: Callable[[str], None]) -> None:
    """R1's cadence from the first target file (sorted listing), through the package's target reader."""
    from treeroute.derive.rules import derive_r01_cadence
    from treeroute.pipeline import data as D

    facts = ctx.facts
    key, path = ctx.target_listing.files[0]
    hook = D.load_hook(facts.loaded.root, D.TARGET_READER)
    kd = dict(zip(ctx.target_listing.key_names, key))
    reader = getattr(hook, "read_target_file", None) if hook is not None else None
    frame = reader(path, kd) if reader is not None else D._read_target_generic(path, kd, ctx.spec)
    units = D.shared_str_ids(frame[facts.unit_col], "unit id")
    times = {c: np.asarray(frame[c].to_numpy(), dtype=np.int64) for c in facts.time_facts}
    r1 = derive_r01_cadence(units, times, facts.time_facts)
    ctx.cadence = r1.value
    ctx.cadence_source = "R1 (derive_r01_cadence) on the first target file %s (%d rows)" % (Path(path).name, len(frame))
    ctx.target_columns_read = tuple(str(c) for c in frame.columns)
    echo("R1: %s %s %s (%s)" % (_v(getattr(r1.value, "kind", None)), getattr(r1.value, "length", None),
                                _v(getattr(r1.value, "unit", None)), ctx.cadence_source))


def _static_columns(ctx: CheckContext) -> Tuple[str, ...]:
    """The static table's non-key columns (its first file's footer): the report strata and any other column it
    holds. Its plan 1.2 structure (lat, lon, grid_ix, grid_iy: pipeline.data.read_static) counts only when the
    catalog lists it (the plan defines those columns, so they need no row)."""
    from treeroute.io.listing import list_store
    from treeroute.io.readers import read_footer
    from treeroute.pipeline import data as D

    facts = ctx.facts
    template = getattr(facts.loaded.dataset.stores, "static", None)
    if not template:
        return ()
    listing = list_store(template, base=facts.loaded.root)
    if not listing.files:
        return ()                      # a missing static table is R14's refusal at plan time, not a column fact
    structural = {D.STATIC_LAT, D.STATIC_LON} | set(D.STATIC_GRID)
    return tuple(str(c) for c in read_footer(listing.files[0][1]).names
                 if c not in facts.keys and (c not in structural or c in facts.columns))


def _observed_columns(ctx: CheckContext) -> Tuple[str, ...]:
    """Non-key columns the data hold: the target reader's columns, the footer of the first file of each driver
    store, the static table's columns (_static_columns) and the feature script's outputs."""
    from treeroute.io.listing import list_store
    from treeroute.io.readers import read_footer

    facts = ctx.facts
    keys = set(facts.keys)
    seen: List[str] = []
    for c in getattr(ctx, "target_columns_read", ()):
        if c not in keys and c not in seen:
            seen.append(c)
    ctx.store_listings = []
    for template in facts.loaded.dataset.stores.drivers:
        listing = list_store(template, base=facts.loaded.root)
        names: Tuple[str, ...] = ()
        if listing.files:
            names = tuple(read_footer(listing.files[0][1]).names)
        ctx.store_listings.append((template, listing, names))
        for c in names:
            if c not in keys and c not in seen:
                seen.append(c)
    ctx.static_columns = _static_columns(ctx)
    for c in ctx.static_columns:
        if c not in seen:
            seen.append(c)
    for c in sorted(facts.outputs):
        if c not in seen:
            seen.append(c)
    return tuple(seen)


def declared_through(facts: Any, data_columns: Sequence[str]) -> Dict[str, Tuple[str, ...]]:
    """Owner ruling J4 (a package's bookkeeping rows removed, each stored parent 'declared through' the
    derived columns that carry its family's verdict, plan 1.4): a column the data hold that has no catalog row and
    no verdict but HAS physical facts in an included store catalog, and that catalog columns name in derived_from.
    Such a column never enters (it has no role), and its derived columns carry the verdicts. A row-less column WITH
    a verdict stays G-CLOSED's refusal. {column: its derived columns}."""
    verdicts = facts.loaded.ban.verdicts
    out: Dict[str, Tuple[str, ...]] = {}
    for c in data_columns:
        if c in facts.columns or c in verdicts or c not in facts.store_of or facts.store_of[c] == FEATURE_STORE:
            continue
        derived = tuple(sorted(d for d, f in facts.columns.items() if c in (f.derived_from or ())))
        if derived:
            out[c] = derived
    return out


def _column_sets(ctx: CheckContext) -> Any:
    """io.apply_verdicts' sets over the columns that have a verdict and a non-key role (the closed world itself
    is G-CLOSED's to report)."""
    from treeroute.io.apply import apply_verdicts

    facts = ctx.facts
    verdicts = facts.loaded.ban.verdicts
    cols = tuple(c for c, f in facts.columns.items() if f.role not in KEY_ROLES and c in verdicts)
    roles = {c: facts.columns[c].role for c in cols}
    try:
        return apply_verdicts(cols, {c: verdicts[c] for c in cols}, roles)
    except RefusedError:
        keep = tuple(c for c in cols if facts.columns[c].role not in ("target", "target_twin"))
        return apply_verdicts(keep, {c: verdicts[c] for c in keep}, {c: roles[c] for c in keep})


def _forward_reach(ctx: CheckContext, names: Sequence[str]) -> Dict[str, int]:
    from treeroute import timing

    out = {}
    if ctx.cadence is None:
        return out
    periods = list(timing.reference_periods(timing.target_grid(ctx.cadence, "target", "A5")))
    for c in names:
        f = ctx.facts.columns.get(c)
        if f is None or not f.has_store_facts or G._cadence_kind(f) in G.UNLAGGED_KINDS:
            continue
        try:
            out[c] = int(timing.max_forward_reach_days(f, periods))
        except RefusedError:
            out[c] = 1           # an unknown window: its reach cannot be bounded, so it is not allowed unreviewed
    return out


def _r8_lags(ctx: CheckContext) -> Dict[str, Any]:
    """R8 per entering column (derive_r08_feature_lags on one column at a time, so one refusal does not hide the
    others; G-LAG reports the refused ones)."""
    from treeroute.derive.rules import derive_r08_feature_lags

    out = {}
    for name, f in sorted(ctx.entering.items()):
        if G._cadence_kind(f) in G.UNLAGGED_KINDS:
            continue
        try:
            out.update(derive_r08_feature_lags({name: f}, ctx.facts.target, ctx.cadence).value)
        except RefusedError:
            continue
    return out


def _r4_note(ctx: CheckContext) -> Dict[str, Any]:
    """R4's look-back per column (R8's lag plus a declared lag operation's look-back: orchestrate._r04_lags,
    owner ruling J5) and the first year of each driver store from its listing's year keys. Report only."""
    from treeroute.derive.orchestrate import _r04_lags

    store = {c: f for c, f in ctx.facts.columns.items() if f.has_store_facts}
    try:
        lags, record = _r04_lags(SimpleNamespace(store=store), ctx.lags)
    except RefusedError as exc:
        return {"refused": str(exc)}
    first_years = []
    for template, listing, _ in ctx.store_listings:
        if "year" in listing.key_names and listing.files:
            i = listing.key_names.index("year")
            first_years.append(min(int(k[i]) for k, _ in listing.files))
    cad = ctx.cadence
    per_year = 1
    if _v(getattr(cad, "unit", None)) == "month":
        from treeroute import engine_constants as K
        per_year = int(K.MONTHS_PER_YEAR)
    in_target = {}
    for c, lag in lags.items():
        lc = lag.column_cadence
        steps = int(lag.steps)
        if _v(getattr(lc, "unit", None)) == "year" and per_year != 1:
            steps *= per_year
        in_target[c] = steps
    if not in_target:
        return {"first_years": first_years}
    top = max(in_target.values())
    setters = sorted(c for c, s in in_target.items() if s == top)
    counted = record.get("counted", {})
    engineered_only = bool(setters) and all(c in counted and counted[c]["operation_steps"] > 0 for c in setters)
    r8_top = max((int(ctx.lags[c].steps) * (per_year if _v(getattr(ctx.lags[c].column_cadence, "unit", None)) == "year"
                                            and per_year != 1 else 1) for c in ctx.lags), default=0)
    note = {"largest_lookback_steps": top, "set_by": setters, "first_driver_year": min(first_years) if first_years else None,
            "set_only_by_declared_lag_operations": engineered_only and top > r8_top,
            "largest_r8_lag_steps": r8_top}
    if note["first_driver_year"] is not None:
        years = -(-top // per_year)
        note["first_year_estimate"] = note["first_driver_year"] + years
    return note


def run_quick(package_path: Any, echo: Callable[[str], None] = print) -> CheckContext:
    """Every quick guard on the package. Raises PackageError when the package does not load (exit 5)."""
    from treeroute.package.load import load_package
    from treeroute.pipeline import data as D

    loaded = load_package(package_path)
    facts = package_facts(loaded)
    ctx = CheckContext(facts=facts, results=[], cadence=None, cadence_source=None, lags={})
    verdicts = loaded.ban.verdicts
    results = ctx.results

    def add(label: str, res: Any) -> None:
        results.append((label, res))

    ctx.spec, ctx.spec_refusal = _target_spec(facts)
    try:
        ctx.target_listing = D.list_target(facts.loaded)
        ctx.data_groups = D.listed_groups(ctx.target_listing) or ()
    except RefusedError as exc:
        ctx.target_listing, ctx.data_groups = None, ()
        add("G-SUPPORT (target store)", G.refusal_result(exc, "G-SUPPORT"))
    if ctx.target_listing is not None and facts.target is not None:
        try:
            read_r1(ctx, echo)
        except RefusedError as exc:
            add("R1", G.refusal_result(exc, "R1", "R1 refused on the first target file: "))
    if facts.target is not None:
        facts.target.cadence = ctx.cadence
    ctx.data_columns = _observed_columns(ctx)

    # G-SPLIT
    split_res = G.check_g_split(loaded.split, tuple(ctx.data_groups))
    add("G-SPLIT", split_res)
    try:
        from treeroute import split as SP
        ctx.groups = SP.groups_under_loro(SP.loro_split_sets(loaded.split), tuple(ctx.data_groups))
    except RefusedError:
        ctx.groups = tuple(ctx.data_groups)

    ctx.column_sets = _column_sets(ctx)
    entering_names = tuple(ctx.column_sets.tree_features) + tuple(ctx.column_sets.router_context)
    ctx.entering = {c: facts.columns[c] for c in entering_names}

    # G-LINEAGE (quick): its flags feed G-CLOSED
    lineage = G.check_g_lineage(facts.columns, facts.target, verdicts, loaded.exceptions.entries) \
        if facts.target is not None else G.result("G-LINEAGE", G.BLOCK, (), "no single target column")
    add("G-LINEAGE", lineage)
    flagged = set(lineage.details.get("flagged", {})) if lineage.details else set()

    # G-CLOSED (and the facts problems found while merging)
    unreviewed = [c for c in ctx.data_columns if G.verdict_of(verdicts, c) == "keep_unreviewed"]
    reach = _forward_reach(ctx, unreviewed)
    ctx.declared_through = declared_through(facts, ctx.data_columns)
    closed = G.check_g_closed(tuple(c for c in ctx.data_columns if c not in ctx.declared_through),
                              {c: f for c, f in facts.columns.items() if f.role not in KEY_ROLES},
                              verdicts, reach, flagged)
    if ctx.declared_through:
        note = ("; %d stored columns have no catalog row but are declared through the derived columns that carry "
                "their verdicts (owner ruling J4; they never enter): %s"
                % (len(ctx.declared_through), G._fmt("%s -> %s" % (c, G._fmt(d, 3))
                                                     for c, d in sorted(ctx.declared_through.items()))))
        closed = G.result("G-CLOSED", closed.status, closed.columns, closed.reason + note, closed.fix, closed.part,
                          dict(closed.details, declared_through={c: list(d) for c, d in ctx.declared_through.items()}))
    merge_problems = facts.problems.get("G-CLOSED", [])
    if merge_problems:
        closed = G.result("G-CLOSED", G.BLOCK, closed.columns, "; ".join(merge_problems + (
            [closed.reason] if closed.status is G.BLOCK else [])), fix=closed.fix or "declare each column once",
            details=closed.details)
    add("G-CLOSED", closed)

    add("G-KEYS", G.check_g_keys(facts.columns, ctx.column_sets))

    # G-LAG, with R4's first-year note
    if ctx.cadence is not None and facts.target is not None:
        ctx.lags = _r8_lags(ctx)
        lag_res = G.check_g_lag(ctx.entering, facts.target, ctx.cadence, ctx.lags)
        ctx.r4 = _r4_note(ctx)
        details = dict(lag_res.details)
        details["r4"] = ctx.r4
        if lag_res.status is G.PASS and ctx.r4.get("set_only_by_declared_lag_operations"):
            lag_res = G.result("G-LAG", G.FLAG, ctx.r4["set_by"],
                               "every lag is computed; R4 note: the first data year is set by declared lag "
                               "operations alone (%s reads %d target steps back, R8's largest lag is %d), so Y0 is "
                               "about %s (first driver-store year %s); an owner decision when it moves Y0"
                               % (G._fmt(ctx.r4["set_by"], 4), ctx.r4["largest_lookback_steps"],
                                  ctx.r4["largest_r8_lag_steps"], ctx.r4.get("first_year_estimate"),
                                  ctx.r4.get("first_driver_year")),
                               fix="confirm the engineered look-back (or shorten it) before the freeze",
                               details=details)
        else:
            lag_res = G.result("G-LAG", lag_res.status, lag_res.columns, lag_res.reason, lag_res.fix, lag_res.part,
                               details)
        add("G-LAG", lag_res)
    else:
        add("G-LAG", G.result("G-LAG", G.BLOCK, (), "R1's cadence is unknown, so no lag can be recomputed",
                              fix="fix the target store first (R1)"))
        ctx.r4 = {}

    # G-EPOCH (no cut known to the quick check)
    add("G-EPOCH", G.check_g_epoch(facts.columns, verdicts, {}, facts.target, None, loaded.exceptions.entries)
        if facts.target is not None else G.result("G-EPOCH", G.BLOCK, (), "no single target column"))

    # G-HIST (declared); a refusal while reading the feature script's outputs is reported here or by G-DERIVED
    hist = G.check_g_hist_declared(facts.columns, facts.target) if facts.target is not None else None
    if facts.problems.get("G-HIST"):
        hist = G.result("G-HIST", G.BLOCK, (), "; ".join(facts.problems["G-HIST"]),
                        fix="the engine builds the own-history block (R17)", part=G.PART_DERIVED)
    if hist is not None:
        add("G-HIST", hist)

    # G-SUPPORT (groups only)
    n = len(ctx.groups)
    add("G-SUPPORT", G.check_g_support(None, None, False, None, n, n, None))

    # G-FACTS at the headline (the freeze gate)
    cands = G.list_co_measured_candidates(facts.columns, facts.target) if facts.target is not None else ()
    add("G-FACTS", G.check_g_facts(facts.columns, verdicts, facts.target, cands, None, tuple(ctx.groups),
                                   loaded.exceptions.entries, headline=True))

    # G-MISSING (R30's flags come from the data)
    add("G-MISSING", G.check_g_missing(None, verdicts))

    # G-DERIVED: the static scan of the feature script, and any refusal reading its outputs
    if facts.problems.get("G-DERIVED"):
        add("G-DERIVED", G.result("G-DERIVED", G.BLOCK, (), "; ".join(facts.problems["G-DERIVED"]),
                                  fix="declare every output with its facts (plan 1.5)"))
    elif facts.hook_source is not None:
        add("G-DERIVED", G.scan_feature_script(facts.hook_source))
    return ctx


__all__ = ["CheckContext", "run_quick", "read_r1"]
