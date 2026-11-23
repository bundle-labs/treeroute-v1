"""The planted-fault table (tests/planted/PLANTED_FAULTS.md): every planted fault is caught by its named guard,
and the clean planted package has no refusal (plan 5, plan 8.1 M4 'every planted fault refused')."""

import re
from pathlib import Path

import pytest

from planted import build as B
from planted.faults import DEEP, FAULTS, QUICK, VALIDATOR
from treeroute.check.deep import run_deep
from treeroute.check.quick import run_quick

TABLE = Path(__file__).resolve().parent / "planted" / "PLANTED_FAULTS.md"
STATUS = {"refuse": "block", "flag": "flag"}


def _quiet(_text):
    return None


def _by_label(ctx):
    return {label: res for label, res in ctx.results}


@pytest.fixture(scope="module")
def clean_run(tmp_path_factory):
    pkg = B.make_clean_package(tmp_path_factory.mktemp("clean"))
    return run_deep(pkg, echo=_quiet)


def test_the_clean_package_has_no_refusal(clean_run):
    refused = {label: res.reason for label, res in clean_run.results if res.status.value == "block"}
    assert refused == {}, refused
    labels = set(_by_label(clean_run))
    for fault in FAULTS:
        if fault["mode"] != VALIDATOR:
            assert fault["guard"] in labels, fault["guard"]


def test_the_clean_package_passes_the_deep_guards_it_should(clean_run):
    got = {label: res.status.value for label, res in clean_run.results}
    for label in ("G-CLOSED", "G-KEYS", "G-LAG", "G-SPLIT", "G-FACTS", "G-HIST", "G-RANGE", "G-CADENCE", "G-JOIN",
                  "G-MISSING", "G-MISSING (deep)", "G-SENTINEL (deep)", "G-EPOCH", "G-CALENDAR",
                  "G-DERIVED (recompute)", "G-HIST (sample)", "G-LINEAGE (deep)", "G-DERIVED", "G-MISSING (files)",
                  "windows (R3-R11)"):
        assert got[label] == "pass", (label, got[label], _by_label(clean_run)[label].reason)
    # 3 groups: below the 14-group flag (report only), and no all-zero unit
    assert got["G-SUPPORT"] == "flag" and got["G-SUPPORT (deep)"] == "flag"


@pytest.mark.parametrize("fault", FAULTS, ids=[f["id"] for f in FAULTS])
def test_each_planted_fault_is_caught_by_its_guard(fault, tmp_path):
    if fault["mode"] == VALIDATOR:
        res = fault["apply"]()
        assert res.status.value == STATUS[fault["expect"]], res.reason
        assert res.rule_id == fault["guard"]
        return
    pkg = B.make_clean_package(tmp_path)
    fault["apply"](pkg)
    ctx = run_deep(pkg, echo=_quiet) if fault["mode"] == DEEP else run_quick(pkg, echo=_quiet)
    found = _by_label(ctx)
    assert fault["guard"] in found, (fault["id"], sorted(found))
    res = found[fault["guard"]]
    assert res.status.value == STATUS[fault["expect"]], (fault["id"], res.status, res.reason)
    assert res.reason and res.rule_id.startswith("G-")
    if res.status.value == "block":
        assert res.fix, fault["id"]


def test_the_markdown_table_lists_the_same_faults():
    rows = [ln for ln in TABLE.read_text(encoding="utf-8").splitlines() if re.match(r"^\| PF\d\d ", ln)]
    parsed = []
    for ln in rows:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        parsed.append((cells[0], cells[1], cells[2], cells[3], cells[4]))
    expected = [(f["id"], f["guard"], f["mode"], f["expect"], f["kind"]) for f in FAULTS]
    assert parsed == expected


def test_every_plan_guard_of_the_check_has_a_planted_fault():
    guards = {f["guard"].split(" ")[0] for f in FAULTS}
    for g in ("G-CLOSED", "G-LAG", "G-EPOCH", "G-LINEAGE", "G-HIST", "G-KEYS", "G-SPLIT", "G-SUPPORT", "G-FACTS",
              "G-MISSING", "G-CADENCE", "G-CALENDAR", "G-DERIVED", "G-SENTINEL", "G-RANGE", "G-JOIN"):
        assert g in guards, g
