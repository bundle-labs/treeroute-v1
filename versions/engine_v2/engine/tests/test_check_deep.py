"""'check --deep' plumbing: the worker processes of pass 1 cannot change a result (V5.check_deep_workers is
plumbing), the data passes check the package's R21 smoke groups (owner ruling M2) and a caller-given subset checks
only those groups and says so, and the streamed counts are sums over files (the decision is taken once on the whole
column)."""

import numpy as np
import pandas as pd
import pytest

from planted import build as B
from planted import faults as F
from treeroute import engine_constants as K
from treeroute.check import guards as G
from treeroute.check import report as R
from treeroute.check.deep import GROUPS_LABEL, run_deep
from treeroute.check.report import guard_rows
from treeroute.package.load import load_package


def _quiet(_text):
    return None


@pytest.mark.parametrize("fault", [None, F.pf_range_under_share, F.pf_missing_group_year])
def test_one_worker_and_two_workers_give_identical_reports(tmp_path, fault):
    pkg = B.make_clean_package(tmp_path / "p")
    if fault is not None:
        fault(pkg)
    one = run_deep(pkg, echo=_quiet, workers=1)
    two = run_deep(pkg, echo=_quiet, workers=2)
    assert guard_rows(one.results) == guard_rows(two.results)
    d1 = {label: res.details for label, res in one.results}
    d2 = {label: res.details for label, res in two.results}
    assert repr(d1) == repr(d2)


def test_a_group_subset_checks_only_those_groups(tmp_path):
    pkg = B.make_clean_package(tmp_path / "p")
    F.pf_missing_group_year(pkg)                      # grp_c only
    sub = run_deep(pkg, echo=_quiet, groups=("grp_a", "grp_b"), workers=1)
    res = dict(sub.results)
    assert res["G-MISSING (deep)"].status.value == "pass"
    assert sub.deep_groups == ("grp_a", "grp_b")
    # a caller-given subset is recorded as such, and its line says the freeze refuses the report unless the groups
    # are exactly the R21 smoke groups (the freeze compares the groups, test_report_freeze)
    assert sub.deep_selection["selection"] == R.CALLER_SELECTION and sub.deep_selection["groups"] == ["grp_a", "grp_b"]
    assert res[GROUPS_LABEL].status.value == "flag" and "freeze refuses" in res[GROUPS_LABEL].reason
    assert "unless these groups are exactly the package's R21 smoke groups" in res[GROUPS_LABEL].reason


# ------------------------------------------------------------------- ruling M2: the R21 smoke groups
def six_group_package(root, without_drivers=()):
    """The clean planted package with three more groups (copies of grp_c's rows under new names) and grp_a
    excluded in split.yaml: 6 groups in the data, 5 after the exclusion. The groups in without_drivers get no
    driver file (a G-MISSING (files) refusal wherever they are checked)."""
    pkg = B.make_clean_package(root)
    t, d = B.frames()
    extra = ("grp_d", "grp_e", "grp_f")
    for frame, writer, skip in ((t, B.write_target, ()), (d, B.write_drivers, tuple(without_drivers))):
        parts = []
        for g in extra:
            if g in skip:
                continue
            sub = frame[frame["group_id"] == "grp_c"].copy()
            sub["group_id"] = g
            sub["unit_id"] = sub["unit_id"].str.replace("grp_c", g, regex=False)
            parts.append(sub)
        writer(pkg, pd.concat(parts, ignore_index=True))
    groups = tuple(B.GROUPS) + extra
    static = pd.DataFrame([(u, g, 10.0 + i, 20.0 + gi, i, gi) for gi, g in enumerate(groups)
                           for i, u in enumerate(B.units_of(g))],
                          columns=["unit_id", "group_id", "lat", "lon", "grid_ix", "grid_iy"])
    static.to_parquet(pkg / "data" / "static" / "part-0.parquet", index=False)
    (pkg / "split.yaml").write_text("excluded: {grp_a: kept out of the test}\n", encoding="utf-8")
    return pkg


SMOKE = ("grp_b", "grp_c", "grp_d", "grp_e")[:int(K.SMOKE_GROUPS)]       # sorted, after the exclusion


def test_the_default_checks_exactly_the_r21_smoke_groups(tmp_path):
    from treeroute.derive.unit_rules import derive_r21_smoke_plan_loro

    pkg = six_group_package(tmp_path / "p", without_drivers=("grp_f",))      # grp_f is outside the smoke groups
    lines = []
    ctx = run_deep(pkg, echo=lines.append, workers=1)
    assert ctx.deep_groups == SMOKE
    rec = ctx.deep_selection
    assert rec == {"groups": list(SMOKE), "selection": R.M2_SELECTION, "rule": "R21",
                   "constants": {"C13.smoke_groups": K.SMOKE_GROUPS, "C15.min_groups": K.MIN_GROUPS},
                   "package_groups": 5, "data_groups": 6, "refused": None}
    # the engine's own smoke rule, and the freeze's recount, give the same groups
    after = ("grp_b", "grp_c", "grp_d", "grp_e", "grp_f")
    assert rec["groups"] == list(derive_r21_smoke_plan_loro(after).value["groups"])
    assert rec == R.package_smoke_groups(load_package(pkg))
    res = dict(ctx.results)
    assert res[GROUPS_LABEL].status.value == "pass" and res[GROUPS_LABEL].rule_id == "R21"
    assert res["G-MISSING (files)"].status.value == "pass", res["G-MISSING (files)"].reason   # grp_f not read
    assert res["windows (R3-R11)"].status.value == "pass"
    assert any(ln.startswith("check --deep: ruling-M2 subset") and ln.endswith(", ".join(SMOKE)) for ln in lines)
    assert any(ln.startswith("check --deep: %d groups," % len(SMOKE)) for ln in lines)


def test_a_caller_subset_with_the_unchecked_group_finds_its_fault(tmp_path):
    pkg = six_group_package(tmp_path / "p", without_drivers=("grp_f",))
    ctx = run_deep(pkg, echo=_quiet, groups=("grp_f", "grp_b", "grp_c"), workers=1)
    assert ctx.deep_groups == ("grp_b", "grp_c", "grp_f")
    assert ctx.deep_selection["selection"] == R.CALLER_SELECTION
    assert (ctx.deep_selection["package_groups"], ctx.deep_selection["data_groups"]) == (5, 6)
    res = dict(ctx.results)
    assert res["G-MISSING (files)"].status.value == "block" and "grp_f" in res["G-MISSING (files)"].reason


@pytest.mark.parametrize("groups", [("grp_zz",), ("grp_a", "grp_b"), (), ("grp_b", "grp_b"), "grp_b"])
def test_a_caller_subset_outside_the_package_groups_fails_loudly(tmp_path, groups):
    pkg = six_group_package(tmp_path / "p")                   # grp_a is excluded, grp_zz does not exist
    with pytest.raises(ValueError, match="groups"):
        run_deep(pkg, echo=_quiet, groups=groups, workers=1)


def test_too_few_groups_refuses_the_group_choice_and_reads_no_data(tmp_path):
    pkg = B.make_clean_package(tmp_path / "p")
    (pkg / "split.yaml").write_text("excluded: {grp_c: kept out}\n", encoding="utf-8")   # 2 groups left
    lines = []
    ctx = run_deep(pkg, echo=lines.append, workers=1)
    rec = ctx.deep_selection
    assert rec["groups"] == [] and rec["refused"] and "R21" in rec["refused"] and rec["package_groups"] == 2
    res = dict(ctx.results)
    assert res[GROUPS_LABEL].status.value == "block" and "no group checked" in res[GROUPS_LABEL].reason
    assert "G-JOIN" not in res and "windows (R3-R11)" not in res and ctx.deep_groups == ()
    assert not any(ln.startswith("check --deep: pass 1") for ln in lines)


def test_streamed_counts_add_up_to_the_whole_column():
    cols = {"a": NSCol(legal_range=(0.0, 1.0))}
    whole = pd.DataFrame({"a": np.r_[np.zeros(999), 5.0, np.zeros(1000)]})
    total = {}
    for part in (whole.iloc[:1000], whole.iloc[1000:]):
        G.add_counts(total, G.range_counts(part, cols))
    assert total == G.range_counts(whole, cols)
    # one value in 2,000 is under D95's share: a flag on the whole column, as on the summed counts
    assert G.decide_range(total, cols).status.value == "flag"


class NSCol(object):
    def __init__(self, **kw):
        self.role = "driver"
        self.sum_group = None
        self.units = "1"
        self.derived_from = ()
        self.operation = None
        self.has_store_facts = True
        for k, v in kw.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------- the windows (R3-R11)
def _joined_counts_by_hand(target, drivers, from_year):
    """count_valid_rows_per_group_year on the planted frames: a valid label and a driver row (the one store)."""
    from treeroute.derive.rules import count_valid_rows_per_group_year

    have = set(zip(drivers["unit_id"], drivers["step_year"], drivers["step_month"]))
    present = np.array([k in have for k in zip(target["unit_id"], target["step_year"], target["step_month"])])
    keep = target["step_year"].to_numpy() >= from_year
    t = target[keep]
    return dict(count_valid_rows_per_group_year(t["group_id"].to_numpy(dtype=object), t["step_year"].to_numpy(),
                                                np.isfinite(t["y"].to_numpy()), present[keep], B.GROUPS))


def test_the_windows_are_r3_on_the_joined_rows_not_the_last_label_year(tmp_path):
    pkg = B.make_clean_package(tmp_path / "p")
    F.pf_epoch_target_outlasts_drivers(pkg)                 # labels 2011-2012 with no driver row
    ctx = run_deep(pkg, echo=_quiet, workers=1)
    win = ctx.windows
    assert (win.y0, win.y_end, win.train_end, win.test_years) == (2002, 2010, 2006, (2007, 2008, 2009, 2010))
    t, d = B.frames()
    extra = t[t["step_year"] >= 2009].copy()
    extra["step_year"] += 2
    target = pd.concat([t, extra], ignore_index=True)
    want = {"%s/%d" % k: n for k, n in sorted(_joined_counts_by_hand(target, d, win.y0).items())}
    assert win.details["joined_rows_per_group_year"] == want
    # every R11 cut is compared: 3 leads x (fit, guard)
    assert len(dict(ctx.results)["G-EPOCH"].details["cuts"]) == 6


def test_a_refused_rule_refuses_the_windows_and_nothing_estimates_them(tmp_path):
    pkg = B.make_clean_package(tmp_path / "p")
    F.pf_missing_files(pkg)                                  # grp_c has no driver file: no joined row
    res = dict(run_deep(pkg, echo=_quiet, workers=1).results)
    assert res["windows (R3-R11)"].status.value == "block" and "grp_c" in res["windows (R3-R11)"].reason
    for label in ("G-EPOCH", "G-MISSING"):
        assert res[label].status.value == "block" and "not judged" in res[label].reason, label
    assert "not judged" in res["G-RANGE"].reason and "not judged" in res["G-SUPPORT (deep)"].reason


def test_the_all_zero_unit_flag_counts_donor_years_only(tmp_path):
    pkg = B.make_clean_package(tmp_path / "p")
    # grp_a_0: zero labels from Y0 to the train end (2002-2006), positive after; grp_b_0: zero in the test years only
    B.rewrite_target(pkg, lambda t: t.assign(y=np.where(
        ((t["unit_id"] == "grp_a_0") & (t["step_year"].between(2002, 2006)))
        | ((t["unit_id"] == "grp_b_0") & (t["step_year"] >= 2007)), 0.0, t["y"])))
    res = dict(run_deep(pkg, echo=_quiet, workers=1).results)["G-SUPPORT (deep)"]
    assert res.details["all_zero_units"] == 1
    assert "no unit's labels are all zero" not in res.reason


def test_a_missing_year_file_counts_its_rows_as_missing_and_unjoined(tmp_path):
    pkg = B.make_clean_package(tmp_path / "p")
    F.pf_missing_year_file(pkg)                             # grp_a 2009: 4 units x 12 months
    res = dict(run_deep(pkg, echo=_quiet, workers=1).results)
    assert res["G-MISSING (files)"].status.value == "block" and "('grp_a', 2009)" in res["G-MISSING (files)"].reason
    assert sum(res["G-JOIN"].details["rows_without_file"].values()) == 48
    assert "grp_a/2009" in res["G-MISSING (deep)"].details["all_missing_group_years"]["x1"]
