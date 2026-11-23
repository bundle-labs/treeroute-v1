"""derive_all on a synthetic package under leave one region out: the order, the guards (R8 covers the
kept columns, the G-EPOCH stand-in, R23 against independently rebuilt donor rows, each shown refusing a
planted fault), F2, the LORO unit lists, the fallback units over every router cut, the inner-cut bank
plan, the plan-time label reader's lock and label-window rule, and determinism.

The package is written with conftest.make_package and loaded with treeroute.package.load; the target
table and the column reader are synthetic (no store is read). Group names are generic.
"""

import dataclasses
import datetime as dt
import json
from types import SimpleNamespace

import numpy as np
import pytest

from conftest import make_package
from treeroute import derive as D
from treeroute import split as SP
from treeroute.errors import RefusedError
from treeroute.package.load import load_package

STORE = """\
store: toy_store
description: a synthetic store for derive_all
columns:
  x1:
    dtype: float32
    units: "1"
    cadence: {kind: regular, length: 1, unit: month}
    scope: unit
    stamp: period_end
    window: {length: 1, unit: month, align: backward}
  a1:
    dtype: float32
    units: "1"
    cadence: {kind: regular, length: 1, unit: year}
    scope: unit
    stamp: period_end
    window: {length: 1, unit: year, align: backward}
    absent_groups: {g_e: no file for this group}
  s1:
    dtype: float32
    units: "1"
    cadence: {kind: static}
    scope: unit
    stamp: period_end
  e1:
    dtype: float32
    units: "1"
    cadence: {kind: epoch}
    scope: unit
    stamp: period_end
  c1:
    dtype: float32
    units: "1"
    cadence: {kind: regular, length: 1, unit: month}
    scope: unit
    stamp: period_end
    window: {length: 1, unit: month, align: backward}
"""

CATALOG = """\
columns:
  unit_id: {role: key_unit}
  group_id: {role: key_group}
  step_year: {role: key_time, calendar_part: year}
  step_month: {role: key_time, calendar_part: month}
  y:
    role: target
    legal_range: [0, 1]
    legal_range_source: a documented valid range
    window: {length: 1, unit: month, align: backward}
    stamp: period_end
  x1: {role: driver, co_measured_with_target: false, co_measured_evidence: Part 1}
  a1: {role: driver, co_measured_with_target: false, co_measured_evidence: Part 1}
  s1: {role: driver}
  e1: {role: driver}
  c1: {role: router_context, co_measured_with_target: false, co_measured_evidence: Part 1}
"""

BAN = """\
verdicts:
  y: {verdict: ban, reason: label, evidence: the target is forced to ban}
  x1: {verdict: keep, reason: reviewed, evidence: Part 1}
  a1: {verdict: keep_unreviewed, reason: not yet reviewed}
  s1: {verdict: keep, reason: reviewed, evidence: Part 1}
  e1: {verdict: freeze, reason: one pre-window epoch, evidence: Part 2}
  c1: {verdict: keep, reason: reviewed, evidence: Part 1}
"""

SPLIT = """\
excluded: {g_z: no coverage}
seen_during_design: [g_b]
"""

FIRST_YEAR, LAST_YEAR, LAST_DRIVER_YEAR = 2000, 2012, 2011
UNITS = {"g_a": 30, "g_b": 30, "g_c": 30, "g_d": 30, "g_e": 12, "g_z": 5}
SHORT = ("g_b_u000", "g_b_u001")           # short histories: the fallback units of a per-unit package


def day(y, m, d):
    return dt.date(y, m, d).toordinal()


def package(tmp_path, catalog=CATALOG, ban=BAN, split=SPLIT):
    pkg = make_package(tmp_path, store_text=STORE)
    (pkg / "catalog.yaml").write_text(catalog, encoding="utf-8")
    (pkg / "ban.yaml").write_text(ban, encoding="utf-8")
    (pkg / "split.yaml").write_text(split, encoding="utf-8")
    return load_package(pkg)


def target_table(test_window_values=None, late_start=()):
    """late_start: units whose labels are NaN until June 2002 (30 valid inner-fit rows, but only 19 at
    the lead-12 guard cut)."""
    units, groups, years, months, y = [], [], [], [], []
    for g, n in UNITS.items():
        for i in range(n):
            u = "%s_u%03d" % (g, i)
            for yr in range(FIRST_YEAR, LAST_YEAR + 1):
                for m in range(1, 13):
                    units.append(u), groups.append(g), years.append(yr), months.append(m)
                    value = 0.5 + 0.4 * np.sin(0.37 * (yr * 12 + m) + 0.11 * i + len(g))
                    if u in SHORT and yr <= 2005:
                        value = np.nan                     # at most 0 valid inner-fit rows
                    if u == "g_a_u005" and yr == 2003:
                        value = np.nan
                    if u in late_start and (yr, m) <= (2002, 6):
                        value = np.nan
                    y.append(value)
    y = np.array(y)
    years = np.array(years)
    if test_window_values is not None:
        late = years >= 2008
        y[late & np.isfinite(y)] = test_window_values
    return SimpleNamespace(unit_ids=np.array(units, dtype=object), group_ids=np.array(groups, dtype=object),
                           time_columns={"step_year": years, "step_month": np.array(months)}, y=y)


class Reader(object):
    """The column reader derive_all calls: driver presence (F2), content epochs (R9), shares (R30)."""

    def __init__(self, last_driver_year=LAST_DRIVER_YEAR):
        self.last = last_driver_year
        self.calls = []

    def drivers_present(self, unit_ids, group_ids, time_columns, columns):
        self.calls.append(("drivers_present", tuple(columns)))
        return np.asarray(time_columns["step_year"]) <= self.last

    def content_epochs(self, column):
        self.calls.append(("content_epochs", column))
        return [day(2000, 6, 30), day(2005, 6, 30), day(2011, 6, 30)]

    def measure(self, donor, lags, test_years):
        self.calls.append(("measure", donor.unit_scope, tuple(test_years)))
        return D.MissingShares(donor_row_key_hash=donor.row_key_hash, donor_unit_scope=donor.unit_scope,
                               donor_training_missing_share={"x1": 0.0, "a1": 0.3, "s1": 0.0, "e1": 0.1},
                               donor_training_zero_share={"x1": 0.02, "a1": 0.0, "s1": 0.0, "e1": 0.0},
                               test_year_missing_share={("x1", 2011): 1.0, ("a1", 2010): 0.4})


@pytest.fixture(scope="module")
def derived(tmp_path_factory):
    pkg = package(tmp_path_factory.mktemp("derive_all"))
    reader = Reader()
    return pkg, reader, D.derive_all(pkg, target_table(), reader)


def test_every_plan_time_rule_has_an_entry(derived):
    _, _, out = derived
    leads = ["R23:lead=%d" % lead for lead in (0, 6, 12)]          # owner ruling I1: 6 and 12 months
    assert list(out) == (["R1", "R2", "R8", "R4", "R18:groups", "R3", "R5", "R6", "R7", "R10", "R11", "R9",
                          "R12", "R13", "R14", "R17", "R18:bank", "R18", "R18:units",
                          "R12:constant_history_share", "R19", "R19:inner_cut", "R20", "R20:fallback_rows",
                          "R21", "R22"]
                         + leads + ["R28", "R30"])
    doc = D.derived_document(out)
    assert json.loads(json.dumps(doc)) == doc


def test_windows_follow_the_joined_rows_f2(derived):
    _, reader, out = derived
    assert out["R4"].value == FIRST_YEAR + 1                 # the annual driver lags one year
    assert out["R3"].value == LAST_DRIVER_YEAR               # labels run on, the drivers stop
    assert out["R5"].value.test_years == (2008, 2009, 2010, 2011)
    assert out["R7"].value.inner_fit == (2001, 2004) and out["R6"].value == 2007
    assert reader.calls[0] == ("drivers_present", ("x1", "a1", "s1", "e1", "c1"))


def test_groups_are_the_data_minus_the_exclusions(derived):
    _, _, out = derived
    groups = out["R18:groups"].value
    assert groups == ("g_a", "g_b", "g_c", "g_d", "g_e")
    assert out["R18:groups"].inputs["excluded"] == {"g_z": "no coverage"}
    assert out["R3"].inputs["groups"] == list(groups)
    assert out["R21"].value["groups"] == ["g_a", "g_b", "g_c", "g_d"]
    assert out["R20"].value["batch_order"] == list(groups)


def test_router_kind_surface_design_and_history(derived):
    _, _, out = derived
    assert out["R12"].value == D.RouterKind.PER_UNIT
    assert out["R12"].inputs["h"] == 48.0 and out["R12"].inputs["fallback_units"] == 2
    assert out["R13"].value == (D.LoroSurfaceKind.INNER_WINDOW, ())
    assert out["R14"].value.columns == ("intercept", "normal", "context", "trees")
    assert out["R17"].value.trailing_steps == (12, 60) and out["R17"].value.start_offset_steps == 0
    assert out["R8"].inputs["static"] == ["s1"] and out["R8"].inputs["epoch"] == ["e1"]


def test_unit_counts_and_lists(derived):
    _, _, out = derived
    n, bank = out["R18:bank"].value
    assert n == 100 and bank == {"g_a": 30, "g_b": 30, "g_c": 30, "g_d": 30, "g_e": 12}
    assert "capped:g_e" in out["R18:bank"].flags
    counts = out["R18"].value
    assert counts.scored_by_group == bank            # floor(20 x 100 / 5) = 400, capped at the bank
    lists = out["R18:units"].value
    assert lists.bank["g_e"] == tuple("g_e_u%03d" % i for i in range(12))
    # the plan's formulas, written here (not split's code): bank = c[::max(1, len(c) // n)][:n] over the
    # sorted candidates (all when len(c) <= n); scored = positions floor(i x (N-1) / (m-1)) of the bank
    for g, b in bank.items():
        c = tuple(sorted("%s_u%03d" % (g, i) for i in range(UNITS[g])))
        assert lists.bank[g] == (c if len(c) <= b else c[::max(1, len(c) // b)][:b])
        N, m = len(lists.bank[g]), counts.scored_by_group[g]
        assert lists.scored[g] == tuple(lists.bank[g][(i * (N - 1)) // (m - 1)] for i in range(m))
    assert out["R18:units"].inputs["bank_units_hash"]["g_a"] == SP.unit_ids_hash(lists.bank["g_a"])
    assert out["R18"].inputs["event_rate"]["rows"] > 0
    assert out["R18"].inputs["donor_all"]["unit_scope"] == "all_donor_units"


def test_bank_plan_links_c_and_fallback_rows(derived):
    _, reader, out = derived
    assert out["R19"].value["bank_trees"] == 500
    assert out["R19"].inputs["donor"]["unit_scope"] == "picked"
    assert out["R22"].value == (D.Link.IDENTITY, D.Link.LOG_C, D.Link.ARCSINE)
    assert out["R22"].input_hashes["donor_row_key_hash"] == out["R19"].input_hashes["donor_row_key_hash"]
    cuts = out["R11"].value
    for lead in (0, 6, 12):
        entry = out["R23:lead=%d" % lead]
        assert entry.inputs["donor"]["lead"] == lead and entry.inputs["donor"]["cut"] == cuts[lead].fit_cut
    assert sorted(cuts) == [0, 6, 12]                                  # no lead 1 or 3 anywhere
    assert cuts[12].fit_cut < cuts[6].fit_cut < cuts[0].fit_cut
    fallback = out["R20:fallback_rows"]
    assert set(fallback.value) == {"g_b"} and fallback.value["g_b"]["fallback_units"] == 2
    assert out["R12:constant_history_share"].value == 0.0


def test_freeze_epochs_and_missing_flags(derived):
    _, reader, out = derived
    assert out["R9"].value["e1"][0] == {"fit": day(2005, 6, 30), "guard": day(2000, 6, 30)}
    assert ("content_epochs", "e1") in reader.calls
    assert out["R30"].value == {"a1": ("over_threshold",), "x1": ("vanishes:2011",)}
    assert out["R30"].inputs["absent_groups"] == {"a1": ["g_e"]}
    assert ("measure", "picked", (2008, 2009, 2010, 2011)) in reader.calls


def test_test_window_label_values_never_reach_derived_json(tmp_path):
    """G-LOCK at plan time: changing the VALUES of the test-window labels changes nothing (validity
    is unchanged); changing a donor-window label changes the donor rows' hash."""
    pkg = package(tmp_path)
    base = D.derived_sha256(D.derive_all(pkg, target_table(), Reader()))
    assert D.derived_sha256(D.derive_all(pkg, target_table(), Reader())) == base            # deterministic
    assert D.derived_sha256(D.derive_all(pkg, target_table(test_window_values=0.99), Reader())) == base
    moved = target_table()
    moved.y[0] = 0.123                                    # a donor-window label
    assert D.derived_sha256(D.derive_all(pkg, moved, Reader())) != base


def test_derive_all_refusals(tmp_path):
    pkg = package(tmp_path / "a")
    t = target_table()

    class NoPresence(Reader):
        drivers_present = None
    with pytest.raises(RefusedError, match="drivers_present"):
        D.derive_all(pkg, t, NoPresence())
    two = target_table()
    two.group_ids = two.group_ids.copy()
    two.group_ids[0] = "g_b"                              # g_a_u000's first row now claims g_b
    with pytest.raises(RefusedError) as info:
        D.derive_all(pkg, two, Reader())
    assert info.value.rule == "G-DISJOINT"
    no_facts = package(tmp_path / "b", catalog=CATALOG + "  c2: {role: router_context}\n",
                       ban=BAN + "  c2: {verdict: keep, reason: reviewed, evidence: Part 1}\n")
    with pytest.raises(RefusedError, match="no store facts"):
        D.derive_all(no_facts, t, Reader())
    unknown = package(tmp_path / "c", split="excluded: {g_q: not in the data}\n")
    with pytest.raises(RefusedError):
        D.derive_all(unknown, t, Reader())
    closed = package(tmp_path / "d", ban=BAN.replace("  c1: {verdict: keep, reason: reviewed, "
                                                     "evidence: Part 1}\n", ""))
    with pytest.raises(RefusedError) as info:
        D.derive_all(closed, t, Reader())
    assert info.value.rule == "G-CLOSED"


def test_the_plan_time_label_reader_never_reads_the_test_window(derived):
    from treeroute.derive.orchestrate import _PlanLabels
    t = target_table()
    steps = t.time_columns["step_year"] * 12 + t.time_columns["step_month"]
    pkg, _, out = derived
    labels = _PlanLabels(t.unit_ids, t.group_ids, steps, t.y, out["R1"].value,
                         SimpleNamespace(name="y", window=pkg.catalog.columns["y"].window,
                                         stamp="period_end"))
    with pytest.raises(RefusedError, match="before the test window is fixed"):
        labels.donor_labels(("g_a",), int(steps.min()), D.CutKind.FIT, 0, None, "links")
    labels.set_test_first_step(2008 * 12 + 1)
    with pytest.raises(RefusedError, match="reaches the test window"):
        labels.donor_labels(("g_a",), 2008 * 12 + 1, D.CutKind.FIT, 0, None, "links")
    with pytest.raises(RefusedError, match="fixed already"):
        labels.set_test_first_step(2008 * 12 + 1)
    view = labels.donor_labels(("g_a",), 2007 * 12 + 12, D.CutKind.FIT, 0, None, "links")
    assert view.unit_scope == "all_donor_units" and int(view.times.max()) == 2007 * 12 + 12
    with pytest.raises(RefusedError, match="not units of the donor groups"):
        labels.donor_labels(("g_a",), 2007 * 12 + 12, D.CutKind.FIT, 0, ["g_b_u000"], "links")


def test_a_target_window_past_its_step_drops_the_cut_steps_label(derived):
    """timing's rule: a donor row is usable only when its own label window has ended by the cut."""
    from treeroute.derive.orchestrate import _PlanLabels
    from treeroute.package.schema import Window
    pkg, _, out = derived
    t = target_table()
    steps = t.time_columns["step_year"] * 12 + t.time_columns["step_month"]
    reach = Window(length=1, unit="month", align="backward", reach_after_max={"value": 10, "unit": "day"})
    labels = _PlanLabels(t.unit_ids, t.group_ids, steps, t.y, out["R1"].value,
                         SimpleNamespace(name="y", window=reach, stamp="period_end"))
    labels.set_test_first_step(2008 * 12 + 1)
    view = labels.donor_labels(("g_a",), 2007 * 12 + 12, D.CutKind.FIT, 0, None, "links")
    assert int(view.times.max()) == 2007 * 12 + 11                 # December's window ends in January


def test_events_wait_for_m8(tmp_path, monkeypatch):
    from treeroute.derive import orchestrate as O
    pkg = package(tmp_path)
    events = D.Cadence(D.CadenceKind.IRREGULAR)
    monkeypatch.setattr(O.R, "derive_r01_cadence",
                        lambda *a: D.make_derived("R1", events, {}))
    monkeypatch.setattr(O.R, "derive_r02_season_key",
                        lambda *a: D.make_derived("R2", D.SeasonKeySpec(D.SeasonKeyKind.EVENT_MONTH, None), {}))
    with pytest.raises(NotImplementedError, match="M8"):
        D.derive_all(pkg, target_table(), Reader())


def test_shares_measured_on_other_rows_and_sentinel_labels_are_refused(tmp_path):
    pkg = package(tmp_path)

    class OtherRows(Reader):
        def measure(self, donor, lags, test_years):
            shares = Reader.measure(self, donor, lags, test_years)
            return D.MissingShares(**{**shares.__dict__, "donor_row_key_hash": "00" * 32})
    with pytest.raises(RefusedError, match="measured on other rows"):
        D.derive_all(pkg, target_table(), OtherRows())
    bad = target_table()
    bad.y[5] = 1e31                                      # a fill value the ingest should have made NaN
    with pytest.raises(RefusedError) as info:
        D.derive_all(pkg, bad, Reader())
    assert info.value.rule == "G-SENTINEL"


def test_a_region_package_records_the_region_routers_fit_budget(tmp_path, monkeypatch):
    """Short histories make the kind region; the region router's fit keeps whole, evenly spaced bank
    units within the row budget (R14, L2 rule 2)."""
    from treeroute import engine_constants as K
    pkg = package(tmp_path)
    t = target_table()
    keep = np.isin(t.time_columns["step_month"], (1, 4, 7, 10))   # monthly rows, a label a quarter:
    t.y = np.where(keep, t.y, np.nan)                                # 16 valid rows over the inner fit
    monkeypatch.setattr(K, "REGION_ROUTER_ROW_BUDGET", 300)
    out = D.derive_all(pkg, t, Reader())
    assert out["R12"].value == D.RouterKind.REGION
    fit = out["R14:region_fit"]
    n, bank = out["R18:bank"].value
    assert n == 300 // 16 and bank["g_a"] == 18                # floor(300 / 16) = 18 bank units
    # 18 units x 16 rows, less the 4 quarter-month rows g_a_u005 lacks in its missing year
    assert fit.value["g_a"]["inner_surface_units"] == 18 and fit.value["g_a"]["inner_surface_rows"] == 284
    assert fit.value["g_a"]["test_pass_units"] < 18 and "capped:test_pass:g_a" in fit.flags
    assert fit.value["g_a"]["test_pass_rows"] <= 300



def test_the_inner_cut_bank_has_its_own_plan(derived):
    """L6 b (A7.inner_cut_bank_refit): the bank refit at the inner cut is pinned by its own R19 entry,
    built from the bank units' rows at lead 0's guard cut (the inner-fit end)."""
    _, _, out = derived
    inner, nowcast = out["R19:inner_cut"], out["R19"]
    cuts = out["R11"].value
    assert inner.inputs["donor"]["cut"] == cuts[0].guard_cut and inner.inputs["donor"]["cut_kind"] == "guard"
    assert nowcast.inputs["donor"]["cut"] == cuts[0].fit_cut
    assert inner.inputs["constants"]["A7.inner_cut_bank_refit"] is True
    # 30 units x 60 months to the end of 2004, less g_a_u005's missing 2003 (12 rows)
    assert inner.value["rows_per_group"]["g_a"] == 30 * 60 - 12
    assert nowcast.value["rows_per_group"]["g_a"] == 30 * 96 - 12
    assert inner.input_hashes["donor_row_key_hash"] != nowcast.input_hashes["donor_row_key_hash"]


def test_a_unit_short_only_at_a_forecast_guard_cut_falls_back(tmp_path):
    """L2 rule 3 over every router cut: g_c_u000 has 30 valid inner-fit rows but 19 at the lead-12
    guard cut (July 2002 to January 2004), under 24, so its group's bank rows are listed too."""
    pkg = package(tmp_path)
    out = D.derive_all(pkg, target_table(late_start=("g_c_u000",)), Reader())
    assert out["R12"].inputs["fallback_units"] == 2              # R12 counts the inner-fit rows only
    fallback = out["R20:fallback_rows"]
    assert set(fallback.value) == {"g_b", "g_c"}
    assert fallback.value["g_c"]["units"] == ["g_c_u000"] and fallback.value["g_b"]["fallback_units"] == 2
    cuts = out["R11"].value
    assert fallback.inputs["short_at_cuts"]["g_c_u000"] == [cuts[12].guard_cut]
    # g_b's short units reach 24 fit rows only at the nowcast fit cut (2006-2007)
    assert cuts[0].fit_cut not in fallback.inputs["short_at_cuts"]["g_b_u000"]
    assert fallback.inputs["router_cuts"] == sorted({c.fit_cut for c in cuts.values()}
                                                    | {c.guard_cut for c in cuts.values()})


def test_a_kept_epoch_column_without_freeze_is_refused(tmp_path):
    """G-EPOCH stand-in: R8 gives an epoch column no lag and R9 freezes only 'freeze' columns, so a
    kept epoch column with a 'keep' verdict would enter unlagged and unfrozen."""
    ban = BAN.replace("e1: {verdict: freeze, reason: one pre-window epoch, evidence: Part 2}",
                      "e1: {verdict: keep, reason: reviewed, evidence: Part 2}")
    assert ban != BAN
    pkg = package(tmp_path, ban=ban)
    with pytest.raises(RefusedError) as info:
        D.derive_all(pkg, target_table(), Reader())
    assert info.value.rule == "G-EPOCH" and "e1" in str(info.value)


def test_guard_2_refuses_a_plan_time_view_that_differs_from_the_rebuilt_rows(tmp_path, monkeypatch):
    """A planted fault in the plan-time donor view (one row of lead 12's view dropped, its hash
    recomputed as a consistent but wrong view would have it) is caught by guard 2, which compares the
    R23 entry with donor rows rebuilt without donor_labels."""
    from treeroute.derive import orchestrate as O
    pkg = package(tmp_path)
    original = O._PlanLabels.donor_labels

    def planted(self, groups, cut, cut_kind, lead, unit_ids, purpose):
        view = original(self, groups, cut, cut_kind, lead, unit_ids, purpose)
        if purpose != "links" or lead != 12:
            return view
        keep = slice(0, len(view.y) - 1)
        units, times = view.unit_ids[keep], view.times[keep]
        return dataclasses.replace(view, unit_ids=units, times=times, group_of_row=view.group_of_row[keep],
                                   y=view.y[keep], row_key_hash=D.sha256_of_json(
                                       [D.sha256_of_array(units.astype(object)), D.sha256_of_array(times)]))
    monkeypatch.setattr(O._PlanLabels, "donor_labels", planted)
    with pytest.raises(RefusedError) as info:
        D.derive_all(pkg, target_table(), Reader())
    assert info.value.rule == "R23" and "lead 12" in str(info.value) and "differ from plan's" in str(info.value)


def _reach_labels(out, pkg):
    from treeroute.derive.orchestrate import _PlanLabels
    from treeroute.package.schema import Window
    t = target_table()
    steps = t.time_columns["step_year"] * 12 + t.time_columns["step_month"]
    reach = Window(length=1, unit="month", align="backward", reach_after_max={"value": 10, "unit": "day"})
    labels = _PlanLabels(t.unit_ids, t.group_ids, steps, t.y, out["R1"].value,
                         SimpleNamespace(name="y", window=reach, stamp="period_end"))
    labels.set_test_first_step(2008 * 12 + 1)
    return labels


def test_the_rebuilt_rows_follow_the_label_window_rule_independently(derived):
    """rebuild_donor_rows agrees with donor_labels on a target whose window reaches past its step; when
    the view's cached label windows are planted wrong (the reach ignored), the view keeps December's
    labels at a December cut, the rebuild does not, and guard 2 refuses."""
    from treeroute.derive import orchestrate as O
    from treeroute.io.steps import step_bounds
    pkg, _, out = derived
    labels = _reach_labels(out, pkg)
    lists = {"g_a": tuple("g_a_u%03d" % i for i in range(30)), "g_b": ("g_b_u003", "g_b_u007")}
    cut = 2007 * 12 + 12
    units = lists["g_a"] + lists["g_b"]
    view = labels.donor_labels(("g_a", "g_b"), cut, D.CutKind.FIT, 0, units, "links")
    rebuilt = labels.rebuild_donor_rows(lists, cut)
    assert rebuilt.row_key_hash == view.row_key_hash and np.array_equal(rebuilt.y, view.y)
    assert int(rebuilt.times.max()) == cut - 1                     # December's window ends in January
    O._check_r23_plan_time(D.derive_r23_c_for_cut(view), 0, cut, rebuilt)
    _, last = step_bounds(labels._steps, labels._cadence)
    labels._window_end = last.astype(np.int64)                      # planted: the reach ignored
    wrong = labels.donor_labels(("g_a", "g_b"), cut, D.CutKind.FIT, 0, units, "links")
    assert int(wrong.times.max()) == cut
    with pytest.raises(RefusedError, match="differ from plan's"):
        O._check_r23_plan_time(D.derive_r23_c_for_cut(wrong), 0, cut, labels.rebuild_donor_rows(lists, cut))
    with pytest.raises(RefusedError) as info:
        labels.rebuild_donor_rows({"g_a": ("g_b_u000",)}, cut)
    assert info.value.rule == "G-DONOR"
    with pytest.raises(RefusedError, match="reaches the test window"):
        labels.rebuild_donor_rows(lists, 2008 * 12 + 1)


def test_fit_row_counts_drop_labels_whose_window_ends_after_the_cut(derived):
    """Router fit rows (region budget, fallback units) are the label-usable rows at the cut: with a
    10-day reach, December's label is not usable at a December cut."""
    pkg, _, out = derived
    labels = _reach_labels(out, pkg)
    counts = labels.fit_row_counts(("g_a_u000", "g_a_u005", "g_z_u000"), 2001 * 12 + 1, 2004 * 12 + 12)
    assert counts == {"g_a_u000": 47, "g_a_u005": 35, "g_z_u000": 47}
    assert labels.fit_row_counts(("g_a_u000",), 2001 * 12 + 1, 2004 * 12 + 11) == {"g_a_u000": 46}


def test_no_fit_row_for_the_constant_history_share_is_refused(tmp_path, monkeypatch):
    """R12's report-only share has no silent fallback: no fit row at all stops the derivation."""
    from treeroute.derive import orchestrate as O
    pkg = package(tmp_path)
    monkeypatch.setattr(O._PlanLabels, "fit_rows",
                        lambda self, *a: (np.zeros(0, dtype=object), np.zeros(0)))
    with pytest.raises(RefusedError) as info:
        D.derive_all(pkg, target_table(), Reader())
    assert info.value.rule == "R12" and "no fit row" in str(info.value)
