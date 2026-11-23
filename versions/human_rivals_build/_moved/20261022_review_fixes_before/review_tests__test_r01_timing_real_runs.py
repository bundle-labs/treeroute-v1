"""R01: date safety at the issue date, checked with the tool's OWN timing rules (rivals_human/index.py:42-125) on the
REAL headline runs' plan.json / derived.json (read-only, a few MB; no export, no product, no label).

Each rival's rows are built with the adapter's own info_end / target_obs_end formula (cited per test) on keys shaped
like the run's saved test rows (time - issue = lead, checked on the real test_preds key columns 2026-10-22).
"""
import numpy as np
import pandas as pd
import pytest

from rivals_human import index as IX
from adapters import ndvi_bardl as BD
from adapters import ndvi_kraft as KR

from review_tests.conftest import rival_of

pytestmark = pytest.mark.runjson


def _grid_keys(times, lead):
    t = np.asarray(times, dtype=np.int64)
    return pd.DataFrame({"unit": "u", "group": "g", "time": t, "issue": t - int(lead), "lead": int(lead)})


def _breaks(run, rival, lead, keys, info_end, toe):
    tm = IX.Timing(run, rival, lead)
    b1, b2 = IX.timing_breaks(tm, keys, np.asarray(info_end, np.int64), np.asarray(toe, np.float64))
    return tm, b1, b2


# ------------------------------------------------------------------------------------------------ defo (VT0007)
def _vt_rows(t, lead, frozen=None):
    """defo_vt0007.py:275 and :316-317: t_eff = min(t, frozen + 1); info_end = target_obs_end = t_eff - 1."""
    keys = _grid_keys(t, lead)
    te = np.asarray(t) if frozen is None else np.minimum(np.asarray(t), frozen + 1)
    return keys, te - 1, (te - 1).astype(float)


def test_r01_defo_run_facts(runjson):
    """The facts the VT0007 timing depends on: defo R8 has steps-1 entries, so S = 1 for a rival naming no
    t1_kind_columns (index.py:67-71), and R17 start_offset_steps = 0."""
    run = runjson("defo")
    r8 = run.derived["R8"]["value"]
    assert max(int(v["steps"]) for v in r8.values()) == 1
    assert rival_of("defo", "vt0007_shipped")["t1_kind_columns"] == []
    tm = IX.Timing(run, rival_of("defo", "vt0007_shipped"), 1)
    assert tm.s_steps == 1 and tm.t1_shift == -1 and tm.offset == 0


@pytest.mark.parametrize("rid", ["vt0007_shipped", "vt0007_cal", "vt0007_frozen2019"])
def test_r01_vt0007_lead0_is_date_safe(runjson, rid):
    run = runjson("defo")
    r = rival_of("defo", rid)
    frozen = (r.get("options") or {}).get("frozen_year")
    keys, ie, toe = _vt_rows(range(2011, 2024), 0, frozen)
    _, b1, b2 = _breaks(run, r, 0, keys, ie, toe)
    assert not b1.any() and not b2.any()


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="ISSUE 1: VT0007 writes info_end = t-1 (a LABEL-derived input) and the T1 boundary at lead 1 "
                          "is issue - S = t-2, so `adapt` refuses every lead-1 row on the real defo run")
@pytest.mark.parametrize("rid", ["vt0007_shipped", "vt0007_cal", "vt0007_frozen2019"])
def test_r01_vt0007_lead1_passes_the_real_run_timing(runjson, rid):
    run = runjson("defo")
    r = rival_of("defo", rid)
    frozen = (r.get("options") or {}).get("frozen_year")
    keys, ie, toe = _vt_rows(range(2011, 2024), 1, frozen)
    tm, b1, b2 = _breaks(run, r, 1, keys, ie, toe)
    assert not b2.any(), "T2 (labels to t-1) holds at lead 1"
    assert not b1.any(), "T1 breaks on %d of %d rows (%s)" % (int(b1.sum()), b1.size, tm.t1_rule)


def test_r01_vt0007_proposed_fix_keeps_t2_honest(runjson):
    """Proposed fix: info_end = the newest NON-label input (treecover2000 / datamask: year 2000), target_obs_end =
    t_eff - 1 (the loss years read). Both leads then pass, and a row that read the target year itself still breaks T2."""
    run = runjson("defo")
    r = rival_of("defo", "vt0007_shipped")
    for lead in (0, 1):
        keys, _, toe = _vt_rows(range(2011, 2024), lead)
        _, b1, b2 = _breaks(run, r, lead, keys, np.full(len(keys), 2000), toe)
        assert not b1.any() and not b2.any()
        _, _, b2_bad = _breaks(run, r, lead, keys, np.full(len(keys), 2000), keys["time"].to_numpy(float))
        assert b2_bad.all(), "a row reading loss of the target year must break T2"


# ------------------------------------------------------------------------------------------------ PM2.5
def _pm_rows(keys, month_offset, shift_years=0):
    """pm25_reanalysis.py:341-346 and :393-394: m = issue + month_offset, read = m - 12 x shift; info_end =
    target_obs_end = read."""
    m = keys["issue"].to_numpy(np.int64) + int(month_offset)
    read = m - 12 * int(shift_years)
    return read, read.astype(float)


@pytest.mark.parametrize("rid", ["eac4_lag1", "merra2_lag1", "eac4_lag1_placebo", "merra2_lag1_placebo"])
def test_r01_pm25_parity_rows_are_date_safe(runjson, rid):
    run = runjson("pm25")
    r = rival_of("pm25", rid)
    keys = _grid_keys(np.arange(2003 * 12 + 2, 2023 * 12 + 13), 0)
    ie, toe = _pm_rows(keys, r["options"]["month_offset"], r["options"].get("placebo_shift_years", 0))
    tm, b1, b2 = _breaks(run, r, 0, keys, ie, toe)
    assert tm.s_steps == 1, "burn_frac (the co-measured column) has R8 steps 1"
    assert not b1.any() and not b2.any()


@pytest.mark.parametrize("rid", ["eac4_same", "merra2_same"])
def test_r01_pm25_same_month_rows_break_both_rules_so_never_decide(runjson, rid):
    run = runjson("pm25")
    r = rival_of("pm25", rid)
    keys = _grid_keys(np.arange(2003 * 12 + 2, 2023 * 12 + 13), 0)
    ie, toe = _pm_rows(keys, r["options"]["month_offset"])
    tm, b1, b2 = _breaks(run, r, 0, keys, ie, toe)
    assert b1.all() and b2.all()
    rec = IX.check_tier_timing("A", tm, keys, ie, toe, np.ones(len(keys), bool), "review")
    assert rec["t1_breaks"] == len(keys)
    with pytest.raises(Exception, match="break the timing rules"):
        IX.check_tier_timing("P", tm, keys, ie, toe, np.ones(len(keys), bool), "review")


def test_r01_pm25_registry_month_offsets_match_tiers():
    """Every P / X (placebo) row reads a month <= issue - 1; every A row the issue month itself."""
    from review_tests.conftest import real_registry
    for r in real_registry("pm25")["rivals"]:
        tier = r["leads"][0]["tier"]
        off = int(r["options"]["month_offset"]) - 12 * int(r["options"].get("placebo_shift_years", 0) or 0)
        assert (off <= -1) if tier in ("P", "X") else (off == 0), (r["id"], tier, off)


# ------------------------------------------------------------------------------------------------ NDVI
@pytest.mark.parametrize("lead,tier", [(0, "P"), (6, "X"), (12, "X")])
def test_r01_ndvi_h1_rows_are_date_safe(runjson, lead, tier):
    """ndvi_bardl.py:354-357: info_end = issue (climate at i); target_obs_end = t2_step (BD.t2_step, the tool's T2)."""
    run = runjson("ndvi")
    r = rival_of("ndvi", "bardl_h1")
    keys = _grid_keys(np.arange(2003 * 12 + 1, 2023 * 12 + 13), lead)
    spy, off = BD.run_timing(run)
    assert (spy, off) == (12, 1)
    ie = keys["issue"].to_numpy(np.int64)
    toe = BD.t2_step(keys["time"].to_numpy(np.int64), lead, off).astype(float)
    tm, b1, b2 = _breaks(run, r, lead, keys, ie, toe)
    assert tm.s_steps == 0 and not b1.any() and not b2.any()
    np.testing.assert_array_equal(tm.t2_step(keys), toe.astype(np.int64))
    # one step later on either input refuses
    with pytest.raises(Exception, match="break the timing rules"):
        IX.check_tier_timing(tier, tm, keys, ie, toe + 1, np.ones(len(keys), bool), "review")
    with pytest.raises(Exception, match="break the timing rules"):
        IX.check_tier_timing(tier, tm, keys, ie + 1, toe, np.ones(len(keys), bool), "review")


def test_r01_ndvi_h1_reads_same_month_climate_by_the_runs_own_rule(runjson):
    """The task text says 'NDVI rain-lag uses only past rain/soil moisture'. It does not: at lead 0 the issue step is
    the target month (time - issue = 0 on the real test rows) and H1 reads x__V02 / x__V30 AT the issue step. That is
    legal only because the run's own R8 gives those columns steps 0 (our model reads them too): parity, not a leak.
    This pins the fact so the Part discloses it (ISSUE 9)."""
    run = runjson("ndvi")
    r8 = run.derived["R8"]["value"]
    for c in rival_of("ndvi", "bardl_h1")["t1_kind_columns"]:
        assert int(r8[c]["steps"]) == 0, c


def test_r01_ndvi_kraft_window_is_date_safe(runjson):
    """ndvi_kraft.py:253 / :272: window end e = issue - S, S = window_shift (max R8 steps of its driver kinds)."""
    run = runjson("ndvi")
    r = rival_of("ndvi", "kraft_lstm")
    S = KR.window_shift(run, r)
    keys = _grid_keys(np.arange(2003 * 12 + 1, 2023 * 12 + 13), 0)
    ie = keys["issue"].to_numpy(np.int64) - S
    tm, b1, b2 = _breaks(run, r, 0, keys, ie, np.full(len(keys), np.nan))
    assert S == tm.s_steps and not b1.any() and not b2.any()


# ------------------------------------------------------------------------------------------------ coral
def test_r01_coral_table_rules(runjson):
    """Table package: T1 boundary = issue + max_feature_end_minus_issue_day (-1 at every lead), T2 = issue - 1.
    crw_dhw d* = C - g - 1 = issue - 2 on day rows (g = sst_gap_days = 1 in the store build_manifest): passes as P/L.
    One day later (d* = issue - 1) still passes T1 (boundary issue - 1); d* = issue refuses. The Outlook (A) issued
    after our issue date breaks T1 as tier A must."""
    run = runjson("coral")
    assert run.plan["max_feature_end_minus_issue_day"] == {"0": -1, "183": -1, "365": -1}
    issue0 = 736330
    for lead, rid, tier in ((0, "crw_dhw", "P"), (183, "crw_dhw", "L"), (365, "crw_dhw", "L")):
        r = rival_of("coral", rid)
        t = issue0 + np.arange(50) + lead
        keys = pd.DataFrame({"unit": ["s|d"] * 50, "group": "g", "time": t, "issue": t - lead, "lead": lead})
        tm = IX.Timing(run, r, lead)
        ok = IX.check_tier_timing(tier, tm, keys, keys["issue"] - 2, np.full(50, np.nan), np.ones(50, bool), "r")
        assert ok["t1_breaks"] == 0
        with pytest.raises(Exception, match="break the timing rules"):
            IX.check_tier_timing(tier, tm, keys, keys["issue"].to_numpy(), np.full(50, np.nan), np.ones(50, bool), "r")
    r = rival_of("coral", "crw_outlook")
    t = issue0 + np.arange(50) + 183
    keys = pd.DataFrame({"unit": ["s|d"] * 50, "group": "g", "time": t, "issue": t - 183, "lead": 183})
    tm = IX.Timing(run, r, 183)
    rec = IX.check_tier_timing("A", tm, keys, keys["time"] - 140, np.full(50, np.nan), np.ones(50, bool), "r")
    assert rec["t1_breaks"] == 50
