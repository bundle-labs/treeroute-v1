"""The validators of treeroute/check/guards.py and the declared-operation recompute, one by one (plan 5; owner
ruling A: D44, D79, D91-D97 accepted defaults)."""

from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

from treeroute import engine_constants as K
from treeroute.check import guards as G
from treeroute.check.recompute import RecomputeRefusal, recompute_declared_operation
from treeroute.io.steps import DenseGrid

MONTH = NS(kind="regular", length=1, unit="month")
YEAR = NS(kind="regular", length=1, unit="year")
STATIC = NS(kind="static", length=None, unit=None)


def V(verdict, reason="reviewed", evidence="Part 1"):
    return NS(verdict=verdict, reason=reason, evidence=evidence)


def col(name, role="driver", **kw):
    base = dict(name=name, role=role, cadence=MONTH, fact_status="verified", reviewed_by=None, has_store_facts=True,
                derived_from=(), computed_from=(), operation=None, reads_target=False, sum_group=None, units="1",
                product_family=None, lineage_assimilates=(), lineage_trained_on=(), snapshot_date=None,
                content_epoch=None, baseline_period=None, legal_range=None, fill_values=(), near_sentinel_optout=False,
                co_measured_with_target=False, co_measured_evidence="Part 1", data_selected=None, dtype="float64",
                absent_groups={}, store="s")
    base.update(kw)
    return NS(**base)


def status(res):
    return res.status.value


# ---------------------------------------------------------------------------------------------- G-CLOSED
def test_closed_world_passes_and_lists_keep_unreviewed():
    cols = {"a": col("a"), "b": col("b", fact_status="assumed", reviewed_by="owner")}
    res = G.check_g_closed(("a", "b"), cols, {"a": V("keep"), "b": V("keep_unreviewed", "signed", None)}, {}, set())
    assert status(res) == "pass" and res.details["keep_unreviewed"] == ["b"]


@pytest.mark.parametrize("case", ["no_verdict", "absent", "unreviewed_unsigned", "reach", "lineage", "no_evidence"])
def test_closed_world_refuses(case):
    cols = {"a": col("a"), "b": col("b")}
    verdicts = {"a": V("keep"), "b": V("keep")}
    data, reach, flagged = ("a", "b"), {}, set()
    if case == "no_verdict":
        del verdicts["b"]
    elif case == "absent":
        data = ("a",)
    elif case == "unreviewed_unsigned":
        cols["b"] = col("b", fact_status="assumed")
        verdicts["b"] = V("keep_unreviewed", "x", None)
    elif case == "reach":
        verdicts["b"] = V("keep_unreviewed", "x", None)
        reach = {"b": 15}
    elif case == "lineage":
        verdicts["b"] = V("keep_unreviewed", "x", None)
        flagged = {"b"}
    elif case == "no_evidence":
        verdicts["b"] = V("keep", "x", None)
    res = G.check_g_closed(data, cols, verdicts, reach, flagged)
    assert status(res) == "block" and "b" in res.columns and res.fix


# --------------------------------------------------------------------------------------------- G-SPLIT
def test_split_differences_refuse_and_counts_print():
    ok = G.check_g_split(NS(excluded={"g3": "x"}, seen_during_design=["g1"]), ("g1", "g2", "g3", "g4"))
    assert status(ok) == "pass" and "3 after exclusions" in ok.reason
    bad = G.check_g_split(NS(excluded={"gx": "x"}, seen_during_design=[]), ("g1", "g2"))
    assert status(bad) == "block" and bad.part == G.PART_SPLIT
    both = G.check_g_split(NS(excluded={"g1": "x"}, seen_during_design=["g1"]), ("g1", "g2"))
    assert status(both) == "block"


# ------------------------------------------------------------------------------------------- G-SUPPORT
def test_support_thresholds_are_the_signed_ones():
    assert status(G.check_g_support(None, None, False, None, K.MIN_GROUPS - 1, 0, None)) == "block"
    assert status(G.check_g_support(None, None, False, None, K.FLAG_GROUPS_BELOW - 1, 0, None)) == "flag"
    assert status(G.check_g_support(None, None, False, None, K.FLAG_GROUPS_BELOW, 0, None)) == "pass"


def test_support_refuses_one_donor_value_a_holed_census_and_presence_only_events():
    assert status(G.check_g_support(NS(y=np.array([1.0, 1.0])), True, False, 1, 20, 20, True)) == "block"
    holed = G.check_g_support(NS(y=np.array([1.0, 2.0])), False, False, 1, 20, 20, True)
    assert status(holed) == "block" and "grid it to unit x step with zeros" in holed.fix
    assert status(G.check_g_support(NS(y=np.array([1.0, 2.0])), True, True, 0, 20, 20, True)) == "block"
    assert status(G.check_g_support(NS(y=np.array([1.0, 2.0])), True, False, 5, 20, 20, False)) == "flag"


# --------------------------------------------------------------------------------------------- G-FACTS
def test_facts_block_at_the_headline_and_flag_otherwise():
    cols = {"a": col("a", fact_status="unverified"), "b": col("b", fact_status="assumed"),
            "c": col("c", co_measured_with_target=None)}
    verdicts = {c: V("keep") for c in cols}
    target = NS(name="y", legal_range_source=None)
    head = G.check_g_facts(cols, verdicts, target, ("c",), None, ("g1",), (), headline=True)
    assert status(head) == "block" and {"a", "b", "c", "y"} <= set(head.columns)
    assert "no reviewer" in head.reason
    assert status(G.check_g_facts(cols, verdicts, target, ("c",), None, ("g1",), (), headline=False)) == "flag"


def test_facts_data_selected_list_needs_a_test_exposure_disclosure():
    ds = NS(method="top-k", rows="donor", latest_date="2019-12", groups=["g1", "g2"])
    cols = {"a": col("a", data_selected=ds)}
    target = NS(name="y", legal_range_source="guide")
    res = G.check_g_facts(cols, {"a": V("keep")}, target, (), None, ("g1", "g2"), (), True)
    assert status(res) == "block" and "test groups" in res.reason
    disclosed = (NS(kind="test_exposure", column="a", check=None, owner="owner"),)
    assert status(G.check_g_facts(cols, {"a": V("keep")}, target, (), None, ("g1", "g2"), disclosed, True)) == "pass"


# ------------------------------------------------------------------------------------------- G-MISSING
def test_missing_quick_rules():
    assert status(G.check_g_missing(None, {})) == "flag"
    flags = NS(value={"a": ("over_threshold",), "b": ("vanishes:7",), "c": ("over_threshold",)})
    res = G.check_g_missing(flags, {"a": V("keep_unreviewed", "x", None), "b": V("ban", "incomplete"),
                                    "c": V("keep")})
    assert status(res) == "block" and res.columns == ("a",)
    assert status(G.check_g_missing({"b": ("x",)}, {"b": V("ban", "incomplete")})) == "flag"
    assert status(G.check_g_missing({}, {})) == "pass"


def test_missing_deep_separates_declared_absences_and_never_blocks():
    shares = {("a", "g1", 5): 1.0, ("a", "g2", 5): 0.1, ("b", "g3", 5): 1.0}
    res = G.check_g_missing_deep(shares, {"b": {"g3": "store fact"}})
    assert status(res) == "flag" and res.columns == ("a",)
    assert res.details["declared_absent_group_years"] == {"b": 1}
    assert status(G.check_g_missing_deep({("b", "g3", 5): 1.0}, {"b": {"g3": "x"}})) == "pass"


# ------------------------------------------------------------------------------------------- G-CADENCE
def _monthly_frame(values_of_unit_year):
    codes, steps, vals = [], [], []
    for u in range(3):
        for year in (2001, 2002):
            for m in range(1, 13):
                codes.append(u)
                steps.append(year * 12 + m)
                vals.append(values_of_unit_year(u, year, m))
    return np.array(codes), np.array(steps), np.array(vals, dtype=np.float64)


def test_cadence_refuses_a_fake_monthly_column():
    codes, steps, vals = _monthly_frame(lambda u, y, m: u + 0.1 * y)
    res = G.check_g_cadence(pd.DataFrame({"a": vals}), codes, steps, {"a": col("a")}, MONTH)
    assert status(res) == "block" and res.columns == ("a",) and res.part == G.PART_CADENCE


def test_cadence_spares_a_sparse_monthly_count_the_conflict_lesson():
    # zero almost everywhere, but it varies in the one unit-year where events happen
    codes, steps, vals = _monthly_frame(lambda u, y, m: 3.0 if (u, y, m) == (1, 2002, 4) else 0.0)
    res = G.check_g_cadence(pd.DataFrame({"a": vals}), codes, steps, {"a": col("a")}, MONTH)
    assert status(res) == "pass"


def test_cadence_refuses_an_annual_column_that_varies_inside_its_year():
    codes, steps, vals = _monthly_frame(lambda u, y, m: float(m))
    res = G.check_g_cadence(pd.DataFrame({"a": vals}), codes, steps, {"a": col("a", cadence=YEAR)}, MONTH)
    assert status(res) == "block" and "contradicted" in res.reason
    codes, steps, vals = _monthly_frame(lambda u, y, m: float(y))
    assert status(G.check_g_cadence(pd.DataFrame({"a": vals}), codes, steps, {"a": col("a", cadence=YEAR)},
                                    MONTH)) == "pass"


def test_cadence_findings_on_columns_that_do_not_enter_are_flagged():
    counts = {"a": {"judged_as": "fine", "judged": 10, "varying": 0}}
    assert status(G.decide_cadence(counts, entering={"b"})) == "flag"
    assert status(G.decide_cadence(counts, entering={"a"})) == "block"


# ------------------------------------------------------------------------------------------ G-SENTINEL
def test_sentinel_deep_flags_undeclared_codes_and_near_sentinels_only():
    frame = pd.DataFrame({"a": np.array([1.0, -9999.0, 2.0]), "b": np.array([-32768.0, 1.0, 2.0]),
                          "c": np.array([2.0 ** 31 - 5, 1.0, 1.0]), "d": np.array([2.0 ** 31 - 5, 1.0, 1.0])})
    cols = {"a": col("a"), "b": col("b", fill_values=(-32768.0,)), "c": col("c"),
            "d": col("d", near_sentinel_optout=True)}
    res = G.check_g_sentinel_deep(frame, cols)
    assert status(res) == "flag" and set(res.columns) == {"a", "c"}
    f32 = pd.DataFrame({"e": np.array([9.96921e36, 1.0], dtype=np.float32)})
    counts = G.sentinel_counts(f32, {"e": col("e")})
    assert counts["e"]["undeclared_codes"], counts


# --------------------------------------------------------------------------------------------- G-RANGE
def test_range_refuses_above_the_signed_share_and_flags_below():
    n = 10000
    v = np.zeros(n)
    v[: int(n * K.RANGE_REFUSE_SHARE) + 1] = 5.0
    cols = {"a": col("a", legal_range=(0.0, 1.0))}
    assert status(G.check_g_range(pd.DataFrame({"a": v}), cols, NS(name="y", legal_range=(0, 1)), None)) == "block"
    v = np.zeros(n)
    v[0] = 5.0
    res = G.check_g_range(pd.DataFrame({"a": v}), cols, NS(name="y", legal_range=(0, 1)), None)
    assert status(res) == "flag" and "1 of %d" % n in res.reason


def test_range_one_unit_per_sum_group_and_per_copy():
    cols = {"a": col("a", sum_group="g", units="%"), "b": col("b", sum_group="g", units="1")}
    assert status(G.decide_range({}, cols)) == "block"
    cols = {"a": col("a", units="m"), "b": col("b", units="mm", derived_from=("a",), operation="lag k=1 unit=month")}
    assert status(G.decide_range({}, cols)) == "block"


# ---------------------------------------------------------------------------------------------- G-JOIN
def test_join_refuses_a_changed_row_count_a_refusal_or_a_column_set():
    rep = NS(what="j", left_rows=10, right_rows=10, out_rows=10, unmatched_left=2)
    assert status(G.check_g_join((rep,), {"t": True})) == "pass"
    assert status(G.check_g_join((NS(what="j", left_rows=10, right_rows=12, out_rows=12, unmatched_left=0),),
                                 {"t": True})) == "block"
    assert status(G.check_g_join((rep,), {"t": False})) == "block"
    assert status(G.check_g_join((rep,), {"t": True}, {"join t": "[G-JOIN] duplicated key"})) == "block"


# ------------------------------------------------------------------------------------------ G-CALENDAR
def test_calendar_events_must_read_before_the_issue_date():
    u = np.array([1, 1])
    assert status(G.check_g_calendar(u, np.array([5, 9]), u, np.array([10, 10]), None, True)) == "pass"
    assert status(G.check_g_calendar(u, np.array([5, 10]), u, np.array([10, 10]), None, True)) == "block"
    assert status(G.check_g_calendar(np.array([1, 2]), np.array([9, 9]), u, np.array([10, 10]), 1, False)) == "block"


# ------------------------------------------------------------------------------- G-DERIVED static, G-HIST
def test_feature_script_scan():
    assert status(G.scan_feature_script("import numpy as np\nx = np.ones(3)\n")) == "pass"
    assert status(G.scan_feature_script("m.fit(x, y)\n")) == "block"
    assert status(G.scan_feature_script("w = model.feature_importances_\n")) == "block"
    assert status(G.scan_feature_script("def f(:\n")) == "block"


def test_hist_declared_refuses_a_lag_of_y_and_allows_years_since_and_neighbours():
    target = NS(name="y")
    bad = {"y": col("y", role="target"), "h": col("h", derived_from=("y",), operation="lag k=1 unit=month")}
    assert status(G.check_g_hist_declared(bad, target)) == "block"
    ok = {"h1": col("h1", derived_from=("y",), operation="years since the unit's last event"),
          "h2": col("h2", reads_target=True, operation="neighbour aggregate of the target, years before t")}
    assert status(G.check_g_hist_declared(ok, target)) == "pass"


def test_keys_never_reach_the_trees():
    cols = {"month": col("month", role="key_time"), "m": col("m", role="engineered", derived_from=("month",)),
            "c": col("c", role="router_context", derived_from=("month",))}
    assert status(G.check_g_keys(cols, NS(tree_features=("m",), router_context=("c",)))) == "block"
    assert status(G.check_g_keys(cols, NS(tree_features=(), router_context=("c",)))) == "pass"


# ------------------------------------------------------------------------------------------- G-LINEAGE
def test_lineage_rules():
    target = NS(name="y", product_family="P")
    cols = {"y": col("y", role="target"), "a": col("a", product_family="P"), "b": col("b", derived_from=("r",)),
            "r": col("r")}
    verdicts = {"y": V("ban", "label"), "a": V("keep"), "b": V("keep"), "r": V("ban", "incomplete")}
    res = G.check_g_lineage(cols, target, verdicts, ())
    assert status(res) == "block" and "a" in res.columns                       # an undisclosed co-product
    ex = (NS(kind="provenance_flag", column="a", check="G-LINEAGE", owner="owner"),)
    res = G.check_g_lineage(cols, target, verdicts, ex)
    assert status(res) == "flag" and set(res.details["flagged"]) == {"a", "b"}
    verdicts["r"] = V("ban", "coproduct")
    # derived from a leak-banned source: a READING for the owner, flagged (the approved contract does not refuse it)
    res = G.check_g_lineage(cols, target, verdicts, ex)
    assert status(res) == "flag" and set(res.details["leak_parent"]) == {"b"} and "READING" in res.reason
    signed = ex + (NS(kind="provenance_flag", check="G-LINEAGE lag ends before the year (b)", owner="owner"),)
    res = G.check_g_lineage(cols, target, verdicts, signed)
    assert status(res) == "flag" and not res.details["leak_parent"] and "signed" in res.details["flagged"]["b"]
    verdicts["y"] = V("keep")
    assert status(G.check_g_lineage({"y": col("y", role="target")}, target, verdicts, ())) == "block"


def test_co_measured_candidates_share_family_at_no_coarser_cadence():
    target = NS(name="y", product_family="P", cadence=MONTH)
    cols = {"a": col("a", product_family="P"), "b": col("b", lineage_assimilates=("P",)),
            "c": col("c", product_family="P", cadence=YEAR), "d": col("d")}
    assert G.list_co_measured_candidates(cols, target) == ("a", "b")


# --------------------------------------------------------------------------------------------- G-EPOCH
def test_epoch_rules():
    cuts = {0: G._date_day("2019-12-31")}
    cols = {"e": col("e", cadence=NS(kind="epoch", length=None, unit=None), content_epoch="2018"),
            "c": col("c", cadence=STATIC, content_epoch="2021-06"), "b": col("b", baseline_period=("1981", "2020")),
            # snapshot and release dates are never used (plan 1.3)
            "s": col("s", snapshot_date="2025-06", release_date="2026-01")}
    verdicts = {"e": V("keep"), "c": V("keep"), "b": V("keep"), "s": V("keep")}
    res = G.check_g_epoch(cols, verdicts, cuts, NS(name="y", calibration_through=None), 2019, ())
    assert status(res) == "block" and set(res.columns) == {"e", "c"}
    verdicts.update(e=V("freeze"), c=V("freeze"))
    res = G.check_g_epoch(cols, verdicts, cuts, NS(name="y", calibration_through=None), 2019, ())
    assert status(res) == "pass" and res.details["baseline_disclosures"]
    late = NS(name="y", calibration_through=2021)
    assert status(G.check_g_epoch({}, {}, cuts, late, 2019, ())) == "block"
    ex = (NS(kind="disclosed_defect", column="y", check="G-EPOCH", owner="owner"),)
    assert status(G.check_g_epoch({}, {}, cuts, late, 2019, ex)) == "pass"


def test_epoch_checks_every_r11_cut_and_names_the_ones_an_epoch_lies_after():
    from treeroute.derive.rules import cut_days
    from treeroute.timing import cuts_for_leads

    windows = NS(y0=2003, y_end=2023, test_years=(2020, 2021, 2022, 2023), train_end=2019, inner_fit=(2003, 2016),
                 inner_score=(2017, 2018, 2019))
    leads = NS(leads=(6, 12), lead_unit="steps")
    days = cut_days(cuts_for_leads(windows, leads, MONTH), MONTH)
    assert len(days) == 3
    # guard cuts: lead 0 December 2016, lead 6 July 2016, lead 12 January 2016 (December 2016 moved back 11
    # months); an August 2016 epoch lies after two of the six cuts
    cols = {"c": col("c", cadence=STATIC, content_epoch="2016-08")}
    res = G.check_g_epoch(cols, {"c": V("keep")}, days, NS(name="y", calibration_through=None), 2019, ())
    assert status(res) == "block" and "after 2 of the 6 cuts" in res.reason, res.reason
    assert min(d["day"] for d in res.details["cuts"]) == "2016-01-31"
    cols = {"c": col("c", cadence=STATIC, content_epoch="2015")}
    assert status(G.check_g_epoch(cols, {"c": V("keep")}, days, NS(name="y", calibration_through=None), 2019,
                                  ())) == "pass"
    with pytest.raises(Exception):          # a step-unit cut is not a day
        G.check_g_epoch(cols, {"c": V("keep")}, {0: NS(lead=0, fit_cut=1, guard_cut=1)}, NS(name="y"), 2019, ())


def test_epoch_observed_through_static_refuses_regular_is_the_record_end():
    """UPDATED 2026-10-06: owner ruling N S23 (OWNER_RULINGS_2026-10-06.md N): a regular column's observed_through
    is its record end, never compared with a cut and never flagged (it was an owner-decision flag before)."""
    cuts = {0: G._date_day("2019-12-31")}
    target = NS(name="y", calibration_through=None)
    # a static column observed once: observed_through is its one observation epoch
    res = G.check_g_epoch({"s": col("s", cadence=STATIC, observed_through="2026")}, {"s": V("keep")}, cuts, target,
                          2019, ())
    assert status(res) == "block" and res.columns == ("s",)
    # a regular column: observed_through after the cut is its record end (listed, not flagged, not refused)
    res = G.check_g_epoch({"r": col("r", observed_through="2021"), "o": col("o", observed_through="2015")},
                          {"r": V("watch"), "o": V("keep")}, cuts, target, 2019, ())
    assert status(res) == "pass" and "OWNER DECISION" not in res.reason and "S23" in res.reason
    assert len(res.details["observed_through_record_end"]) == 2
    # in the quick check (no cut) the same: listed only
    res = G.check_g_epoch({"r": col("r", observed_through="2021")}, {"r": V("watch")}, {}, target, None, ())
    assert status(res) == "pass" and res.details["observed_through_record_end"]
    # an unreadable observed_through on a regular column is still refused
    res = G.check_g_epoch({"r": col("r", observed_through="late 2021")}, {"r": V("watch")}, cuts, target, 2019, ())
    assert status(res) == "block" and "cannot be read" in res.reason
    # a fact date that cannot be read is refused
    res = G.check_g_epoch({"r": col("r", content_epoch="mid-2010")}, {"r": V("keep")}, cuts, target, 2019, ())
    assert status(res) == "block" and "cannot be read" in res.reason


def test_epoch_static_map_dating_rule_n2():
    """Owner ruling N2 (OWNER_RULINGS_2026-10-06.md N): an entering static map is physical (content_epoch
    'timeless', never compared with a cut) or dated (compared with every cut); one that is neither is refused by
    name, with or without cuts; 'timeless' on a non-static column is refused."""
    cuts = {0: G._date_day("2019-12-31")}
    target = NS(name="y", calibration_through=None)
    cols = {"phys": col("phys", cadence=STATIC, content_epoch=G.TIMELESS_EPOCH),
            "built": col("built", cadence=STATIC, content_epoch="2005"),
            "bare": col("bare", cadence=STATIC), "gone": col("gone", cadence=STATIC)}
    verdicts = {"phys": V("keep"), "built": V("keep"), "bare": V("watch"), "gone": V("ban")}
    for c in (cuts, {}):
        res = G.check_g_epoch(cols, verdicts, c, target, 2019 if c else None, ())
        assert status(res) == "block" and res.columns == ("bare",), res.reason
        assert "neither physical" in res.reason and "N2" in res.reason and res.details["static_undated"] == ["bare"]
    del cols["bare"]
    assert status(G.check_g_epoch(cols, verdicts, cuts, target, 2019, ())) == "pass"
    res = G.check_g_epoch(cols, verdicts, {}, target, None, ())
    assert status(res) == "flag" and res.columns == ("built",)       # dated, compared only by check --deep
    res = G.check_g_epoch({"r": col("r", content_epoch=G.TIMELESS_EPOCH)}, {"r": V("keep")}, cuts, target, 2019, ())
    assert status(res) == "block" and res.columns == ("r",) and "not static" in res.reason


# ---------------------------------------------------------------------------------- the exception shape
def test_an_exception_addresses_a_column_by_its_column_field_or_a_check_text_that_names_it():
    signed = dict(kind="provenance_flag", owner="owner")
    assert G._exception_for((NS(column="a", check=None, **signed),), "a", "G-LINEAGE")
    assert G._exception_for((NS(column=None, check="G-LINEAGE", **signed),), "a", "G-LINEAGE")
    assert G._exception_for((NS(column=None, check="G-LINEAGE co-product (frac, a)", **signed),), "a", "G-LINEAGE")
    # a check text that does not name the column, names a longer column, or starts with another rule
    assert not G._exception_for((NS(column=None, check="G-LINEAGE co-product (frac)", **signed),), "a", "G-LINEAGE")
    assert not G._exception_for((NS(column=None, check="G-LINEAGE (a_lag2)", **signed),), "a", "G-LINEAGE")
    assert not G._exception_for((NS(column=None, check="AGLW extension (a)", **signed),), "a", "G-LINEAGE")
    assert not G._exception_for((NS(column="a", check="G-SENTINEL fill", **signed),), "a", "G-LINEAGE")
    # placeholder owners disclose, never sign
    for owner in ("UNSIGNED -- basis: a ruling", "TBD -- awaiting owner", "todo", "N/A", "?", "pending review"):
        assert not G.exception_signed(NS(owner=owner)), owner
    assert G.exception_signed(NS(owner="The Owner")) and G.exception_signed(NS(owner="Nonero"))
    assert "names the" in G.EXCEPTION_SHAPE


# ---------------------------------------------------------------------------------- the reconstruction flag
def test_reconstruction_of_a_banned_sum_group_member_is_flagged():
    a = np.array([0.2, 0.5, 0.7], dtype=np.float32)
    frame = pd.DataFrame({"a": a, "b": (1.0 - a.astype(np.float64)).astype(np.float32)})
    cols = {"a": col("a", sum_group="g", dtype="float32"), "b": col("b", sum_group="g", dtype="float32")}
    res = G.flag_lineage_reconstructions(frame, cols, {"a": V("keep"), "b": V("ban", "structural")})
    assert status(res) == "flag"
    frame["b"] = np.array([0.1, 0.9, 0.3])
    assert status(G.flag_lineage_reconstructions(frame, cols, {"a": V("keep"), "b": V("ban", "structural")})) == "pass"


# -------------------------------------------------------------------------------------------- G-HIST sample
class _Labels(object):
    """The label vault's asof_rows on a dense grid (unit row r, step first + j)."""

    def __init__(self, y, first):
        self.y, self.first = y, first

    def asof_rows(self, unit_rows, newest, k, purpose="rows"):
        read = np.asarray(newest) - k - self.first
        out = np.full(len(unit_rows), np.nan)
        ok = read >= 0
        out[ok] = self.y[np.asarray(unit_rows)[ok], read[ok]]
        return out


def test_hist_sample_catches_a_copy_of_the_own_target_one_step_back():
    rng = np.random.default_rng(3)
    y = rng.normal(5, 1, size=(2, 30))
    grid = DenseGrid(unit_ids=("u0", "u1"), group_of_unit=("g", "g"), first_step=100, n_steps=30)
    copy = np.full((2, 30), np.nan)
    copy[:, 1:] = y[:, :-1]
    values = pd.DataFrame({"x": copy.reshape(-1), "z": rng.normal(size=60)})
    rows = np.arange(60)
    res = G.check_g_hist_sample({"x": col("x"), "z": col("z")}, values, grid, _Labels(y, 100), rows)
    assert status(res) == "block" and res.columns == ("x",) and "lag 1" in res.reason


# ------------------------------------------------------------------------------------------- the recompute
def _grid(n_units=2, n=30, first=2001 * 12 + 1):
    return DenseGrid(unit_ids=tuple("u%d" % i for i in range(n_units)), group_of_unit=("g",) * n_units,
                     first_step=first, n_steps=n)


def _decl(op, src="s", dtype="float64"):
    return NS(name="o", operation=op, derived_from=(src,), reads_target=False, cadence=MONTH, dtype=dtype)


def test_recompute_lag_hold_trailing_and_cumulative():
    grid = _grid()
    rng = np.random.default_rng(1)
    v = rng.normal(size=60)
    v[7] = np.nan
    src = pd.DataFrame({"s": v})
    rows = np.arange(60)
    m = v.reshape(2, 30)
    lag = recompute_declared_operation(_decl("lag k=2 unit=month"), src, grid, None, rows, None, MONTH).reshape(2, 30)
    assert np.isnan(lag[:, :2]).all() and np.allclose(lag[:, 2:], m[:, :-2], equal_nan=True)
    tm = recompute_declared_operation(_decl("trailing_mean w=3 unit=month min_count=1"), src, grid, None, rows, None,
                                      MONTH).reshape(2, 30)
    assert np.isclose(tm[1, 5], np.nanmean(m[1, 3:6]))
    cs = recompute_declared_operation(_decl("cumulative stat=sum reset_month=6 unit=month"), src, grid, None, rows,
                                      None, MONTH).reshape(2, 30)
    assert np.isclose(cs[1, 5], m[1, 5]) and np.isclose(cs[1, 6], m[1, 5] + m[1, 6])     # June restarts the sum
    ewm = recompute_declared_operation(_decl("cumulative stat=ewm_mean alpha=0.1 adjust=false unit=month"), src, grid,
                                       None, rows, None, MONTH).reshape(2, 30)
    ref = pd.Series(m[0]).ewm(alpha=0.1, adjust=False, ignore_na=False).mean().to_numpy()
    assert np.allclose(ewm[0], ref, equal_nan=True)
    hold = recompute_declared_operation(_decl("hold_last_observed through_year=2002 unit=year"), src, grid, None, rows,
                                        None, MONTH).reshape(2, 30)
    assert np.allclose(hold[:, :24], m[:, :24], equal_nan=True) and np.allclose(hold[:, 24:], m[:, 12:18])


def test_recompute_years_since_harmonic_copy_and_refusals():
    grid = _grid(1, 12)
    v = np.array([5, 20, 1, 1, np.nan, 2, 30, 3, 1, 1, 1, 1], dtype=float)
    src = pd.DataFrame({"s": v, "step_month": np.arange(1, 13)})
    rows = np.arange(12)
    ys = recompute_declared_operation(_decl("years_since event='s >= 10' unit=month no_event=nan"), src, grid, None,
                                      rows, None, MONTH)
    assert np.isnan(ys[0]) and ys[1] == 0 and ys[3] == 2 and np.isnan(ys[4]) and np.isnan(ys[5]) and ys[7] == 1
    h = recompute_declared_operation(_decl("calendar_harmonic sin order=1 angle=2*pi*(month-0.5)/12", "step_month"),
                                     src, grid, None, rows, None, MONTH)
    assert np.allclose(h, np.sin(2 * np.pi * (np.arange(1, 13) - 0.5) / 12))
    copy = recompute_declared_operation(_decl(None, "step_month"), src, grid, None, rows, None, MONTH)
    assert np.array_equal(copy, np.arange(1, 13))
    with pytest.raises(RecomputeRefusal):
        recompute_declared_operation(_decl("free text smoothing"), src, grid, None, rows, None, MONTH)
    with pytest.raises(RecomputeRefusal):
        recompute_declared_operation(NS(name="o", operation="lag k=1 unit=month", derived_from=("y",),
                                        reads_target=True, cadence=MONTH), src, grid, None, rows, None, MONTH)


def test_derived_compares_through_the_declared_dtype():
    grid = _grid(1, 12)
    v = np.linspace(0.1, 1.3, 12)
    src = pd.DataFrame({"s": v})
    script = pd.DataFrame({"o": v.astype(np.float32).astype(np.float64)})
    rows = np.arange(12)
    assert status(G.check_g_derived({"o": _decl(None, dtype="float32")}, script, rows, grid, None, src, None,
                                    target_cadence=MONTH)) == "pass"
    assert status(G.check_g_derived({"o": _decl(None, dtype="float64")}, script, rows, grid, None, src, None,
                                    target_cadence=MONTH)) == "block"


def test_join_problems_of_a_store_no_run_reads_are_report_only():
    rep = NS(what="j", left_rows=10, right_rows=10, out_rows=10, unmatched_left=0)
    res = G.check_g_join((rep,), {}, {}, {"join store s": "no unit key"})
    assert status(res) == "flag" and "remove an unused store" in res.fix
    assert status(G.check_g_join((rep,), {}, {"join store t": "dup"}, {"join store s": "x"})) == "block"
