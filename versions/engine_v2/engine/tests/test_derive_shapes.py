"""derive/'s shapes and signatures against the approved contract.

The approved shapes live in treeroute/_proposed/common.py and the approved signatures in
treeroute/_proposed/derive_rules.py. Tests may not IMPORT proposed code (loading it makes the run
manifest refuse, G-FINGERPRINT), so both are checked by PARSING their source:
  - every record and enum derive/ copies has the approved field names (in order) and member values;
  - every derive/ function that shares a name with an approved signature takes the same parameters;
  - the label-only donor view the tests build (DonorView below) mirrors vault.DonorLabels.
"""

import ast
import inspect
from dataclasses import dataclass, fields
from enum import Enum
from typing import Any, Tuple

import numpy as np
import pytest

from conftest import TREEROUTE_DIR
from treeroute import derive as D
from treeroute.derive import shapes as S

PROPOSED = TREEROUTE_DIR / "_proposed"


def _classes(path):
    """{class name: (annotated field names in order, {member: constant value})} parsed from a file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        names = [n.target.id for n in node.body
                 if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)]
        members = {n.targets[0].id: n.value.value for n in node.body
                   if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                   and isinstance(n.targets[0], ast.Name) and not n.targets[0].id.startswith("__")}
        out[node.name] = (names, members)
    return out


def _signatures(path):
    """{function name: [parameter names]} of the module-level functions parsed from a file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: [a.arg for a in node.args.args] for node in tree.body
            if isinstance(node, ast.FunctionDef)}


@dataclass(frozen=True)
class DonorView:
    """Test mirror of the approved vault.DonorLabels (label-only donor rows at one cut)."""
    groups: Tuple[str, ...]
    cut: int
    cut_kind: Any
    lead: int
    unit_scope: str
    unit_ids: np.ndarray
    times: np.ndarray
    group_of_row: np.ndarray
    y: np.ndarray
    row_key_hash: str


COPIED_RECORDS = (S.Cadence, S.Derived, S.SeasonKeySpec, S.TestWindowPlan, S.Windows, S.LeadPlan,
                  S.GridPoint, S.RouterDesign, S.HistorySpec)
COPIED_ENUMS = (S.CadenceKind, S.StepUnit, S.CalendarPart, S.SeasonKeyKind, S.LeadUnit, S.Link,
                S.CutKind, S.RouterKind)
# copies of approved shapes that live outside the common module: {shape: its approved source file}
OTHER_SOURCES = {S.MissingShares: "derive_rules.py", S.DonorLabels: "vault.py",
                 S.LoroSurfaceKind: "loro_additions.py"}
# LORO addendum ("Files that must follow"): derive_r03_coverage_end's argument test_groups is renamed
# groups; {function: {approved parameter: engine parameter}}
RENAMED_PARAMETERS = {"derive_r03_coverage_end": {"test_groups": "groups"}}


def test_copied_records_match_the_approved_shapes():
    approved = _classes(PROPOSED / "common.py")
    for cls in COPIED_RECORDS:
        assert [f.name for f in fields(cls)] == approved[cls.__name__][0], cls.__name__


def test_copied_enums_match_the_approved_shapes():
    approved = _classes(PROPOSED / "common.py")
    for enum in COPIED_ENUMS:
        members = approved[enum.__name__][1]
        assert {m.name: m.value for m in enum} == members, enum.__name__


def test_copies_of_shapes_from_other_approved_files_match():
    for shape, source in OTHER_SOURCES.items():
        names, members = _classes(PROPOSED / source)[shape.__name__]
        if isinstance(shape, type) and issubclass(shape, Enum):
            assert {m.name: m.value for m in shape} == members, shape.__name__
        else:
            assert [f.name for f in fields(shape)] == names, shape.__name__


def test_the_router_and_split_copies_agree_with_derive():
    """derive, route and split each hold copies of shared shapes; their values must line up (compared
    by field and enum value, never by class identity)."""
    from treeroute import split as SP
    approved = _classes(PROPOSED / "loro_additions.py")
    assert [f.name for f in fields(SP.UnitCounts)] == approved["UnitCounts"][0]
    assert [f.name for f in fields(SP.UnitLists)] == approved["UnitLists"][0]
    try:
        from treeroute.route import kinds as RK
    except Exception as exc:                      # the router is built in parallel: report, never hide
        pytest.skip("route.kinds does not import (%s)" % exc)
    assert {m.name: m.value for m in RK.RouterKind} == {m.name: m.value for m in S.RouterKind}
    assert [f.name for f in fields(RK.RouterDesign)] == [f.name for f in fields(S.RouterDesign)]
    assert [f.name for f in fields(RK.GridPoint)] == [f.name for f in fields(S.GridPoint)]


def test_timing_records_are_the_ones_derive_returns():
    from treeroute.timing import CutPair, Lag
    assert S.Lag is Lag and S.CutPair is CutPair
    approved = _classes(PROPOSED / "common.py")
    assert [f.name for f in fields(Lag)] == approved["Lag"][0]
    assert [f.name for f in fields(CutPair)] == approved["CutPair"][0]


def test_the_test_donor_view_mirrors_the_vault_donor_labels():
    approved = _classes(PROPOSED / "vault.py")
    assert [f.name for f in fields(DonorView)] == approved["DonorLabels"][0]


def test_shared_names_take_the_approved_parameters():
    approved = dict(_signatures(PROPOSED / "derive_rules.py"))
    approved.update(_signatures(PROPOSED / "loro_additions.py"))
    shared = [name for name in D.__all__ if name in approved]
    assert set(shared) >= {"borderline_flags", "derive_r01_cadence", "derive_r02_season_key",
                           "derive_r03_coverage_end", "derive_r04_first_year",
                           "derive_r05_test_window", "derive_r06_train_end",
                           "derive_r07_inner_windows", "derive_r08_feature_lags",
                           "derive_r09_freeze_epochs", "derive_r10_leads", "derive_r11_cuts",
                           "count_valid_rows_per_unit", "constant_history_share",
                           "derive_r12_router_kind", "derive_r13_surface_loro",
                           "derive_r14_router_design", "derive_r17_history_spec",
                           "derive_r18_bank_count", "derive_r18_scored_count",
                           "derive_r19_bank_plan", "derive_r20_batching",
                           "derive_r21_smoke_plan_loro", "derive_r22_links",
                           "derive_r30_missing_flags", "derive_all"}
    for name in shared:
        params = list(inspect.signature(getattr(D, name)).parameters)
        renamed = RENAMED_PARAMETERS.get(name, {})
        assert params == [renamed.get(p, p) for p in approved[name]], name


def test_superseded_signatures_are_not_exported():
    approved = _signatures(PROPOSED / "derive_rules.py")
    loro = _signatures(PROPOSED / "loro_additions.py")
    for old, new in D.SUPERSEDED.items():
        assert old in approved and not hasattr(D, old), old
        for name in new:
            assert name in loro and callable(getattr(D, name)), name


def test_r23_takes_the_layer_signature_shape():
    # the approved c_for_cut takes the donor rows of one cut and nothing else; derive's R23 entry
    # takes the plan-time label-only view of the same rows
    approved = _signatures(PROPOSED / "layer.py")
    assert approved["c_for_cut"] == ["donor_rows"]
    assert list(inspect.signature(D.derive_r23_c_for_cut).parameters) == ["donor"]


def _approved_rule_home():
    tree = ast.parse((PROPOSED / "derive_rules.py").read_text(encoding="utf-8"))
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else (
            node.targets[0] if isinstance(node, ast.Assign) else None)
        if isinstance(target, ast.Name) and target.id == "RULE_HOME":
            return ast.literal_eval(node.value)
    raise AssertionError("no RULE_HOME in the approved derive_rules.py")


def test_rule_home_names_real_functions_at_their_approved_home():
    import importlib
    approved = _approved_rule_home()
    for rule, where in D.RULE_HOME.items():
        module, name = where.rsplit(".", 1)
        assert module in ("derive.rules", "derive.router_rules", "derive.unit_rules"), rule
        assert getattr(importlib.import_module("treeroute." + module), name) is getattr(D, name), rule
        home = approved[rule]
        assert home.startswith("derive_rules."), rule
        old = home.split(".", 1)[1]
        assert old == name or name in D.SUPERSEDED.get(old, ()), rule
    assert set(D.RULE_HOME) == {"R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11",
                                "R12", "R13", "R14", "R17", "R18", "R19", "R20", "R21", "R22", "R30"}
    # every approved derive_rules home is built (R15, R16, R23-R29 and R31-R36 live elsewhere)
    assert {r for r, h in approved.items() if h.startswith("derive_rules.")} == set(D.RULE_HOME)


def test_plan_time_records_name_the_approved_home_elsewhere():
    approved = _approved_rule_home()
    assert set(D.PLAN_TIME_RECORDS) == {"R23", "R28"}
    assert not set(D.PLAN_TIME_RECORDS) & set(D.RULE_HOME)       # one home per rule
    for rule, (record, home) in D.PLAN_TIME_RECORDS.items():
        assert record.startswith("derive.rules.") and callable(getattr(D, record.rsplit(".", 1)[1]))
        assert home == approved[rule] and not home.startswith("derive_rules."), rule
