"""T-F05 timing of the FWI index rows (SPEC_HUMAN_PARTB.txt 3.5; PLAN 3.3; index.py:43-126): the frames the adapter
writes pass the tool's own T1 / T2 rule as tier P, and a shifted copy does not.

- geff_era5 lead 0: info_end = the target month = the issue; passes with the run's R8 (FWI inputs at steps 0) and
  refuses on a copy whose R8 gives V01_mean_temp_C steps 1 (the PLAN 3.3 toy: target-month FWI is parity only
  because our own nowcast reads target-month weather);
- geff_seas5 lead 6: info_end = the issue (start = the end of the issue month) passes; a "start M-4" variant
  (info_end = issue + 1) refuses as tier P; target_obs_end is NaN on every row (FWI observes no burned area).
"""

import numpy as np
import pytest

from tests_fire import fixtures_fire as FF


def _check(frame, run, rival, lead, tier="P"):
    from rivals_human import index as IX
    timing = IX.Timing(run, rival, lead)
    X = frame[FF.STATS].to_numpy(np.float64)
    covered = np.isfinite(X).any(axis=1)
    assert covered.any()
    return IX.check_tier_timing(tier, timing, frame[FF.KEYS], frame["info_end"].to_numpy(np.int64),
                                frame["target_obs_end"].to_numpy(np.float64), covered, "toy %s lead %d"
                                % (rival["id"], lead))


def test_f05_era5_lead0_parity_needs_target_month_weather(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets)
    frame = geff.build(toy.ctx(), toy.rival, 0, "all")
    np.testing.assert_array_equal(frame["info_end"].to_numpy(np.int64), frame["time"].to_numpy(np.int64))
    assert frame["info_end"].dtype == np.int64
    assert frame["target_obs_end"].isna().all()
    rec = _check(frame, FF.FakeRun(cuts=FF.RAW_ERA5_CUTS), toy.rival, 0)
    assert rec["t1_breaks"] == 0 and rec["t2_breaks"] == 0
    late = FF.FakeRun(cuts=FF.RAW_ERA5_CUTS, r8=FF.fact_r8(V01_mean_temp_C=1))
    FF.refuses(_check, frame, late, toy.rival, 0, kinds=FF.tool_refusals(), words=("T1",))


def test_f05_seas5_lead6_issue_boundary(geff, raw_subsets, tmp_path):
    toy = FF.seas5_toy(tmp_path, raw_subsets)
    frame = geff.build(toy.ctx(), toy.rival, 6, "all")
    np.testing.assert_array_equal(frame["info_end"].to_numpy(np.int64), frame["issue"].to_numpy(np.int64))
    np.testing.assert_array_equal(frame["issue"].to_numpy(np.int64), frame["time"].to_numpy(np.int64) - 6)
    assert frame["target_obs_end"].isna().all()
    rec = _check(frame, toy.run, toy.rival, 6)
    assert rec["t1_breaks"] == 0
    m4 = frame.copy()
    m4["info_end"] = m4["info_end"].to_numpy(np.int64) + 1          # a start at M-4: the first day after the issue
    FF.refuses(_check, m4, toy.run, toy.rival, 6, kinds=FF.tool_refusals(), words=("T1",))


def test_f05_synthetic_products_at_the_facts_cuts(geff, synth_products, tmp_path):
    """The same rules on the long synthetic products with the run's own cuts and R8 (spec facts)."""
    t0 = FF.synth_era5_toy(tmp_path / "e", synth_products)
    f0 = geff.build(t0.ctx(), t0.rival, 0, "all")
    _check(f0, FF.FakeRun(), t0.rival, 0)
    t6 = FF.synth_seas5_toy(tmp_path / "s", synth_products)
    f6 = geff.build(t6.ctx(), t6.rival, 6, "all")
    _check(f6, FF.FakeRun(), t6.rival, 6)
    np.testing.assert_array_equal(f6["info_end"].to_numpy(np.int64), f6["time"].to_numpy(np.int64) - 6)
