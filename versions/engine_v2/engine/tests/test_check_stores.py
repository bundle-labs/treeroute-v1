"""Which columns are 'in the data' and which stores a run reads (check/quick.py, check/deep.py):
the static table's columns count for G-CLOSED; owner ruling J4's parents declared through their derived columns;
the pipeline reader's first-store rule decides which store's join and column-set problems refuse; a store's
declared column set may come from two included catalogs; a declared driver store with no file is refused."""

from pathlib import Path
from types import SimpleNamespace as NS

import pandas as pd

from planted import build as B
from treeroute.check.deep import declared_set, read_plan, run_deep
from treeroute.check.quick import declared_through, run_quick


def _quiet(_text):
    return None


def _by_label(ctx):
    return {label: res for label, res in ctx.results}


# ------------------------------------------------------------------------------------- unit level
def test_declared_through_needs_store_facts_no_row_no_verdict_and_a_derived_column():
    facts = NS(columns={"a_max": NS(derived_from=("a",)), "b_max": NS(derived_from=("b",)),
                        "d_lag": NS(derived_from=("d",)), "e": NS(derived_from=())},
               store_of={"a": "cat", "b": "cat", "a_max": "cat", "d": "features/build.py", "c": "cat"},
               loaded=NS(ban=NS(verdicts={"b": NS(verdict="ban")})))
    got = declared_through(facts, ("a", "b", "c", "d", "e", "z"))
    # a: parent of a_max with store facts -> through; b: has a verdict (stays G-CLOSED's); c: no derived column;
    # d: a feature output, not a store column; e: has a row; z: no store facts
    assert got == {"a": ("a_max",)}


def test_read_plan_takes_each_column_from_the_first_store_that_holds_it():
    ctx = NS(facts=NS(outputs={"o1": NS(derived_from=("s",))}, keys={"u": "key_unit"},
                      columns={"st": NS(role="report_stratum"), "x": NS(role="driver")}),
             entering={"x": None, "z": None, "o1": None},
             store_listings=[("first", None, ("u", "x", "s")), ("second", None, ("u", "x", "z", "st")),
                             ("third", None, ("u", "x"))])
    plan = read_plan(ctx)
    assert plan == {"first": ("x", "s"), "second": ("z", "st"), "third": ()}


def test_a_store_declared_set_takes_columns_another_catalog_declares():
    stores = {"own": NS(columns={"a": 1, "b": 1}), "other": NS(columns={"c": 1})}
    facts = NS(loaded=NS(stores=stores), store_of={"a": "own", "b": "own", "c": "other"}, outputs={"o": 1},
               keys={"u": "key_unit"})
    key, declared = declared_set(("u", "a", "b", "c", "o", "stray"), facts)
    assert key == "own"
    assert set(declared) == {"a", "b", "c", "o", "u"}            # 'stray' stays extra: no catalog declares it
    assert declared_set(("stray",), facts) is None


# ---------------------------------------------------------------------------------- package level
STRATUM_ROW = "  st1: {role: report_stratum}\n"
STRATUM_BAN = "  st1: {verdict: ban, reason: structural, evidence: Part 1}\n"


def _add_static_stratum(pkg):
    path = Path(pkg) / "data" / "static" / "part-0.parquet"
    static = pd.read_parquet(path)
    static["st1"] = range(len(static))
    static.to_parquet(path, index=False)
    B.edit(pkg, "catalog.yaml", "  x1_lag1:", STRATUM_ROW + "  x1_lag1:")
    B.edit(pkg, "ban.yaml", "  x1_lag1:", STRATUM_BAN + "  x1_lag1:")


def test_a_stratum_only_the_static_table_holds_is_in_the_data(tmp_path):
    pkg = B.make_clean_package(tmp_path)
    _add_static_stratum(pkg)
    ctx = run_quick(pkg, echo=_quiet)
    assert "st1" in ctx.static_columns and "lat" not in ctx.static_columns      # structure without a row
    assert _by_label(ctx)["G-CLOSED"].status.value == "pass", _by_label(ctx)["G-CLOSED"].reason


SIDE_STORE = """\
store: side_store
description: a second planted store
columns:
  zz:
    dtype: float32
    units: '1'
    cadence: {kind: regular, length: 1, unit: month}
    scope: unit
    stamp: period_end
    window: {length: 1, unit: month, align: backward}
    fact_status: verified
"""


def _add_side_store(pkg, verdict):
    """A second driver store holding one column zz, every unit x month row written TWICE (a join that duplicates
    rows), with its own store catalog and the given verdict."""
    _, d = B.frames()
    d["zz"] = 1.0
    side = pd.concat([d, d], ignore_index=True)
    for group, sub in side.groupby("group_id"):
        out = Path(pkg) / "data" / "side" / ("group=%s" % group)
        out.mkdir(parents=True, exist_ok=True)
        frame = sub[["unit_id", "step_year", "step_month", "zz"]].copy()
        frame["zz"] = frame["zz"].astype("float32")
        frame.to_parquet(out / "part-0.parquet", index=False)
    side_catalog = Path(pkg).parent / "_stores" / "side_store.yaml"
    side_catalog.write_text(SIDE_STORE, encoding="utf-8")
    B.edit(pkg, "dataset.yaml", "  drivers: ['data/drivers/group={group}/year={year}/part-0.parquet']",
           "  drivers: ['data/drivers/group={group}/year={year}/part-0.parquet', "
           "'data/side/group={group}/part-0.parquet']")
    path = Path(pkg) / "dataset.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "  - {path: ../_stores/side_store.yaml, sha256: %s}\n"
                    % B.sha256_of(side_catalog), encoding="utf-8")
    row = "  zz: {role: driver, co_measured_with_target: false, co_measured_evidence: Part 1}\n"
    B.edit(pkg, "catalog.yaml", "  x1_lag1:", row + "  x1_lag1:")
    ban = ("  zz: {verdict: ban, reason: structural, evidence: Part 1}\n" if verdict == "ban"
           else "  zz: {verdict: keep, reason: reviewed, evidence: Part 1}\n")
    B.edit(pkg, "ban.yaml", "  x1_lag1:", ban + "  x1_lag1:")


def test_a_store_no_run_reads_is_flagged_not_refused(tmp_path):
    pkg = B.make_clean_package(tmp_path)
    _add_side_store(pkg, "ban")
    found = _by_label(run_deep(pkg, echo=_quiet, workers=1))
    assert found["G-JOIN"].status.value == "flag", found["G-JOIN"].reason
    assert "data/side" in found["G-JOIN"].reason
    assert found["G-CLOSED"].status.value == "pass", found["G-CLOSED"].reason


def test_the_same_store_refuses_when_a_run_reads_from_it(tmp_path):
    pkg = B.make_clean_package(tmp_path)
    _add_side_store(pkg, "keep")
    found = _by_label(run_deep(pkg, echo=_quiet, workers=1))
    assert found["G-JOIN"].status.value == "block", found["G-JOIN"].reason
    assert found["G-JOIN"].fix


def test_a_declared_driver_store_with_no_file_is_refused(tmp_path):
    pkg = B.make_clean_package(tmp_path)
    (Path(pkg) / "data" / "empty").mkdir(parents=True)
    B.edit(pkg, "dataset.yaml", "  drivers: ['data/drivers/group={group}/year={year}/part-0.parquet']",
           "  drivers: ['data/drivers/group={group}/year={year}/part-0.parquet', "
           "'data/empty/group={group}/part-0.parquet']")
    found = _by_label(run_deep(pkg, echo=_quiet, workers=1))
    res = found["G-MISSING (files)"]
    assert res.status.value == "block" and "holds no file" in res.reason, res.reason


# ------------------------------------------------------------------------------------ signed exceptions
def test_an_unsigned_placeholder_owner_does_not_sign_an_exception():
    from treeroute.check.guards import exception_signed

    assert exception_signed(NS(owner="tester"))
    assert not exception_signed(NS(owner="UNSIGNED -- basis: ruling K3"))
    assert not exception_signed(NS(owner="unsigned"))
    assert not exception_signed(NS(owner="  "))


def test_a_signed_exception_turns_the_coproduct_refusal_into_a_disclosed_flag(tmp_path):
    from planted import faults as F

    pkg = B.make_clean_package(tmp_path)
    F.pf_lineage_unsigned_exception(pkg)
    res = _by_label(run_quick(pkg, echo=_quiet))["G-LINEAGE"]
    assert res.status.value == "block" and "not signed" in res.reason, res.reason
    B.edit(pkg, "exceptions.yaml", "owner: 'UNSIGNED -- basis: a ruling'", "owner: tester")
    res = _by_label(run_quick(pkg, echo=_quiet))["G-LINEAGE"]
    assert res.status.value == "flag" and "frac" in res.columns, res.reason
