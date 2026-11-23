"""The merged facts of a loaded package, for the validators (boilerplate: reads, merges, never decides).

One namespace per catalog column: the package catalog row (role and the problem-relative facts) merged
with the column's physical facts from the included store catalogs or from the feature script's declared
outputs (features/build.py OUTPUTS, validated by pipeline.data.feature_outputs). Store facts win for the
physical and timing fields, as derive does (derive/orchestrate.py _Facts); the package row's legal range
wins when it gives one. A column declared by two store catalogs with different facts, an output declared
by a store catalog too, and an output without a catalog row are recorded as problems (G-CLOSED reports
them), never resolved silently.
"""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Mapping, Optional, Tuple

KEY_ROLES = ("key_unit", "key_group", "key_time")
FEATURE_STORE = "features/build.py"
STORE_FIELDS = ("dtype", "units", "cadence", "scope", "stamp", "window", "legal_range", "fill_values",
                "near_sentinel_optout", "product_family", "sum_group", "content_epoch", "observed_through",
                "release_date", "snapshot_date", "baseline_period", "absent_groups", "derived_from", "operation",
                "reads_target", "fact_status", "reviewed_by", "date", "provenance")
PACKAGE_FIELDS = ("legal_range_source", "co_measured_with_target", "co_measured_evidence", "data_selected",
                  "calibration_through", "computed_from", "measurement_error_floor")


def _v(x: Any) -> Any:
    return getattr(x, "value", x)


def _dump(model: Any) -> Any:
    return model.model_dump() if hasattr(model, "model_dump") else model


class PackageFacts(SimpleNamespace):
    """loaded, outputs ({column: StoreColumn}), hook (the feature script module or None), hook_source
    (its text or None), store_of ({column: store catalog key}), columns ({name: merged facts}, every
    catalog column), keys ({name: role}), time_facts ({key_time column: calendar part}), unit_col,
    group_col, target (the target's facts), problems ({rule: [text]})."""


def merged_column(name: str, pcol: Any, scol: Any, store: Optional[str]) -> SimpleNamespace:
    ns = SimpleNamespace(name=name, role=_v(getattr(pcol, "role", None)) if pcol is not None else None,
                         has_store_facts=scol is not None, store=store)
    for field in STORE_FIELDS:
        setattr(ns, field, getattr(scol, field, None) if scol is not None else None)
    lineage = getattr(scol, "lineage", None) if scol is not None else None
    ns.lineage_assimilates = tuple(getattr(lineage, "assimilates", ()) or ())
    ns.lineage_trained_on = tuple(getattr(lineage, "trained_on", ()) or ())
    ns.fill_values = tuple(ns.fill_values or ())
    ns.derived_from = tuple(ns.derived_from or ())
    ns.absent_groups = dict(ns.absent_groups or {})
    ns.near_sentinel_optout = bool(ns.near_sentinel_optout)
    for field in PACKAGE_FIELDS:
        setattr(ns, field, getattr(pcol, field, None) if pcol is not None else None)
    ns.computed_from = tuple(ns.computed_from or ())
    if pcol is not None and getattr(pcol, "legal_range", None) is not None:
        ns.legal_range = pcol.legal_range
    ns.package_fact_status = getattr(pcol, "fact_status", None) if pcol is not None else None
    if scol is None and pcol is not None:
        # no physical facts: the package row's own facts (the target's window and stamp live there)
        ns.fact_status = getattr(pcol, "fact_status", None)
        ns.reviewed_by = getattr(pcol, "reviewed_by", None)
        ns.window = getattr(pcol, "window", None)
        ns.stamp = getattr(pcol, "stamp", None)
    return ns


def package_facts(loaded: Any) -> PackageFacts:
    """Merge the loaded package's facts. The feature script is executed as a private module (the pipeline's
    own hook loader) so its declared outputs are read; a refusal there is recorded under its rule."""
    from treeroute.errors import RefusedError
    from treeroute.pipeline import data as D

    problems: Dict[str, List[str]] = {}
    hook, outputs, source = None, {}, None
    script = Path(loaded.root) / D.FEATURE_SCRIPT
    if script.is_file():
        source = script.read_text(encoding="utf-8")
        try:
            hook = D.load_hook(loaded.root, D.FEATURE_SCRIPT)
            outputs = D.feature_outputs(hook)
        except RefusedError as exc:
            rule = getattr(exc, "rule", None) or "G-DERIVED"
            problems.setdefault(rule, []).append(str(exc).replace("[%s] " % rule, "", 1))
            outputs = {}
    store: Dict[str, Any] = {}
    store_of: Dict[str, str] = {}
    for key, catalog in sorted(loaded.stores.items()):
        for column, facts in catalog.columns.items():
            if column in store and _dump(store[column]) != _dump(facts):
                problems.setdefault("G-CLOSED", []).append(
                    "column %s is declared by the store catalogs %s and %s with different facts"
                    % (column, store_of[column], key))
                continue
            store.setdefault(column, facts)
            store_of.setdefault(column, key)
    for column, facts in sorted(outputs.items()):
        if column in store:
            problems.setdefault("G-CLOSED", []).append(
                "feature output %s is also declared by the store catalog %s" % (column, store_of[column]))
            continue
        store[column] = facts
        store_of[column] = FEATURE_STORE
    pcols = loaded.catalog.columns
    for column in sorted(outputs):
        if column not in pcols:
            problems.setdefault("G-CLOSED", []).append("feature output %s has no row in catalog.yaml" % column)
    columns = {c: merged_column(c, p, store.get(c), store_of.get(c)) for c, p in pcols.items()}
    keys = {c: _v(p.role) for c, p in pcols.items() if _v(p.role) in KEY_ROLES}
    time_facts = {c: _v(p.calendar_part) for c, p in pcols.items() if _v(p.role) == "key_time"}
    unit_cols = [c for c, r in keys.items() if r == "key_unit"]
    group_cols = [c for c, r in keys.items() if r == "key_group"]
    targets = [c for c, p in pcols.items() if _v(p.role) == "target"]
    target = None
    if len(targets) == 1:
        t = columns[targets[0]]
        tp = pcols[targets[0]]
        target = SimpleNamespace(name=targets[0], window=getattr(tp, "window", None) or t.window,
                                 stamp=getattr(tp, "stamp", None) or t.stamp, computed_from=tuple(tp.computed_from),
                                 fact_status=tp.fact_status, legal_range=t.legal_range,
                                 legal_range_source=tp.legal_range_source, calibration_through=tp.calibration_through,
                                 product_family=t.product_family, measurement_error_floor=tp.measurement_error_floor,
                                 cadence=None)
    else:
        problems.setdefault("G-CLOSED", []).append("the catalog declares %d target columns, one is needed"
                                                   % len(targets))
    return PackageFacts(loaded=loaded, outputs=outputs, hook=hook, hook_source=source, store_of=store_of,
                        columns=columns, keys=keys, time_facts=time_facts,
                        unit_col=unit_cols[0] if len(unit_cols) == 1 else None,
                        group_col=group_cols[0] if len(group_cols) == 1 else None, target=target,
                        problems=problems)


def non_key(facts: PackageFacts) -> Tuple[str, ...]:
    return tuple(c for c, f in facts.columns.items() if f.role not in KEY_ROLES)


__all__ = ["PackageFacts", "package_facts", "merged_column", "non_key", "KEY_ROLES", "FEATURE_STORE"]
