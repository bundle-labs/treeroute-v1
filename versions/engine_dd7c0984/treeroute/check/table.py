"""'check' on a table package (SPEC_TABLE_MODE.md 3.1, 2.1): run_table_quick and run_table_deep.

Owner ruling U1 (the owner rulings file, section U): a table package (dataset.yaml input: table) supplies ready
rows, one table per lead; the grid checks of check/quick.py and check/deep.py read store listings, store facts, the
target reader and the census, none of which a table has. So the quick and deep passes dispatch a table package here
(their first line, guarded: any read error keeps the grid path). Each returns the same CheckContext shape the CLI and
the report writer read (results: [(label, GuardResult)]; deep_selection: ruling M2's checked_groups record).

Quick: G-SPLIT on the lead-0 file's groups; G-CLOSED and the key roles (package.table.table_spec: the verdicts over the
non-key columns, the nine key roles, the target facts of section 1.5, T-NAMES); the contract read on every row
(package.table.read_tables: T-FILES, T-COLUMNS, T-ROWID, T-UNITTIME, T-UNIT, T-ISSUE, T-FEATEND, T-LEADSET, T-RANGE,
T-FINITE); G-FACTS: the target's facts must be signed (verified) for a headline (owner item O21; feature timing is
recorded as vouched, U2). Deep: the quick checks, then derive/table.derive_all_table on the R21 smoke groups (ruling
M2: T-MARK, R3-R12, the kind check, the bank cuts of O13, R22, R23, R30), as a smoke run derives.
A refusal never stops the other checks: every check reports.
"""
# Provenance: SPEC_TABLE_MODE.md 2.1, 3.1, 7 (O21); check/quick.py and check/deep.py (the CheckContext shape, the
# result helpers, ruling M2's selection); OWNER_RULINGS_2026-10-06.md U1, U2.

from typing import Any, Callable, Optional, Sequence

from treeroute.errors import RefusedError

from . import guards as G
from . import report as REP
from .quick import CheckContext

TABLE_LABEL = "U1 (table contract)"


def run_table_quick(package_path: Any, echo: Callable[[str], None] = print) -> CheckContext:
    """The quick checks of a table package (module docstring). Raises PackageError when the package does not load."""
    from treeroute import split as SP
    from treeroute.package import table as T
    from treeroute.package.load import load_package

    loaded = load_package(package_path)
    ctx = CheckContext(facts=None, results=[], cadence=None, cadence_source="declared by the table option (U1)",
                       lags={}, input="table", loaded=loaded)
    results = ctx.results

    def add(label: str, res: Any) -> None:
        results.append((label, res))

    ctx.spec = None
    try:
        ctx.spec = T.table_spec(loaded)
        add("G-CLOSED", G.result("G-CLOSED", G.PASS, (), "every non-key column has a verdict; the nine key roles are "
                                 "declared once each; %d tree features, %d context columns, %d strata"
                                 % (len(ctx.spec.tree_features), len(ctx.spec.context), len(ctx.spec.strata))))
    except RefusedError as exc:
        add("G-CLOSED", G.refusal_result(exc, "G-CLOSED"))
    ctx.data_groups = ()
    if ctx.spec is not None:
        try:
            ctx.data_groups = T.table_groups(loaded, ctx.spec)
        except RefusedError as exc:
            add("G-SUPPORT (lead files)", G.refusal_result(exc, "G-SUPPORT"))
    add("G-SPLIT", G.check_g_split(loaded.split, tuple(ctx.data_groups)))
    try:
        ctx.groups = SP.groups_under_loro(SP.loro_split_sets(loaded.split), tuple(ctx.data_groups))
    except RefusedError:
        ctx.groups = tuple(ctx.data_groups)
    ctx.table = None
    if ctx.spec is not None:
        try:
            ctx.table = T.read_tables(loaded, ctx.spec, T.table_leads(), tuple(sorted(loaded.split.excluded)))
            gaps = {str(L): t.max_feature_end_gap for L, t in sorted(ctx.table.leads.items())}
            add(TABLE_LABEL, G.result("U1", G.PASS, (), "the lead files %s pass T-FILES to T-FINITE and T-LEADSET "
                                      "(%d rows); the largest feature-end minus issue day per lead: %s (always below "
                                      "0); feature timing is vouched by the package owner (U2)"
                                      % (list(T.table_leads()), len(ctx.table.row_ids), gaps)))
        except RefusedError as exc:
            add(TABLE_LABEL, G.refusal_result(exc, "U1"))
        target = loaded.catalog.columns[ctx.spec.target_col]
        status = getattr(target, "fact_status", "unverified")
        add("G-FACTS", G.result("G-FACTS", G.PASS if status == "verified" else G.FLAG, (ctx.spec.target_col,),
                                "the target's facts are %s; a table's feature timing is vouched by the package owner "
                                "(U2), not a store fact (owner item O21)" % status,
                                fix="" if status == "verified" else "sign the target's facts before a headline run"))
    return ctx


def run_table_deep(package_path: Any, echo: Callable[[str], None] = print, groups: Optional[Sequence[str]] = None,
                   ctx: Optional[CheckContext] = None) -> CheckContext:
    """The quick checks, then derive_all_table on ruling M2's groups (R21's smoke groups; module docstring)."""
    from treeroute import engine_constants as K
    from treeroute.derive.table import derive_all_table
    from treeroute.package import table as T

    if ctx is None:
        ctx = run_table_quick(package_path, echo=echo)
    loaded = ctx.loaded
    try:
        selection = REP.smoke_group_selection(ctx.groups, ctx.data_groups) if groups is None else \
            REP.caller_selection(groups, ctx.groups, ctx.data_groups)
    except RefusedError as exc:
        ctx.deep_selection = REP.refused_selection(ctx.groups, ctx.data_groups, str(exc))
        ctx.results.append(("G-SUPPORT (deep)", G.refusal_result(exc, "G-SUPPORT")))
        return ctx
    ctx.deep_selection = selection
    echo("check --deep: " + REP.selection_text(selection))
    if ctx.spec is None or ctx.table is None:
        ctx.results.append(("derive (table)", G.result("U1", G.BLOCK, (), "the table contract refused; derive is not "
                                                       "run (see the %s line)" % TABLE_LABEL)))
        return ctx
    try:
        run_groups = tuple(selection["groups"])
        data = T.read_tables(loaded, ctx.spec, T.table_leads(), tuple(sorted(loaded.split.excluded)),
                             keep_groups=run_groups, smoke_units_per_group=int(K.SMOKE_UNITS_PER_GROUP))
        view = loaded._replace(split=loaded.split.__class__(
            excluded={g: r for g, r in loaded.split.excluded.items() if g in run_groups},
            seen_during_design=[g for g in loaded.split.seen_during_design if g in run_groups]))
        derived = derive_all_table(view, ctx.spec, data, T.table_leads())
        ctx.results.append(("derive (table)", G.result("U1", G.PASS, (), "derive_all_table on the R21 smoke groups %s: "
                                                       "%d entries; router %s; test years %s"
                                                       % (list(run_groups), len(derived),
                                                          getattr(derived["R12"].value, "value", ""),
                                                          list(derived["R7"].value.test_years)))))
    except RefusedError as exc:
        ctx.results.append(("derive (table)", G.refusal_result(exc, "U1")))
    return ctx


__all__ = ["run_table_quick", "run_table_deep", "TABLE_LABEL"]
