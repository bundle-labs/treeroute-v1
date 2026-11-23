"""T-F06 x__fwi_pct, out of sample as of the lead's GUARD cut (SPEC_HUMAN_PARTB.txt 3.6; review R-3).

  R(u, t) = { x(u, t') : t' <= T_ref, same calendar month, t' != t, finite },  T_ref = run.cuts[L]["guard_cut"]
  p(u, t) = ( #{r < x} + 0.5 #{r == x} ) / |R|;  |R| < pct_min_reference (10) -> NaN;  x NaN -> NaN

- the mid-rank formula on a hand example (ties, above / below every reference value);
- a row with t <= T_ref is ranked WITHOUT its own month: its percentile equals a hand rank among the other years for
  every value of its own x (its own value moves it only through x, never through R);
- perturbing every FWI value with t' > T_ref other than the row's own leaves the percentile of every pick row (inner
  at lead 0, guard at lead 6), every row with t <= T_ref and every test row unchanged (facts' lead-0 and lead-6 cuts);
- |R| < 10 -> NaN for that row only;
- through build on the synthetic long products: x__fwi_pct is the guard-cut percentile (lead 0: 24192, lead 6: 24187)
  and differs from a fit-cut one; build refuses when T_ref >= the smallest test time, and when the newest reference
  info_end reaches the smallest pick-set issue (a fake guard cut one step later than the first inner issue; SEAS5:
  reference info_end = T_ref - 6).
"""

import numpy as np
import pandas as pd
import pytest

from tests_fire import fixtures_fire as FF


def _refusals(geff):
    return (geff.FireGeffRefusal,) + FF.tool_refusals()


def _pct(geff, unit, time, x, t_ref, min_ref=10):
    out = np.asarray(geff.fwi_percentile(np.asarray(unit), np.asarray(time, np.int64), np.asarray(x, np.float64),
                                         int(t_ref), 12, int(min_ref)))
    assert out.dtype == np.float64 and out.shape == (len(x),)
    return out


def _table(seed=FF.RANDOM_STATE, units=("u1", "u2", "u3"), first=FF.step(2003, 1), last=FF.step(2022, 12)):
    """A per-unit monthly table (unit, time, x) with distinct random values (no accidental ties)."""
    rng = np.random.default_rng(seed)
    rows = [(u, t) for u in units for t in range(first, last + 1)]
    f = pd.DataFrame(rows, columns=["unit", "time"])
    f["x"] = rng.permutation(len(f)).astype(np.float64) * 0.37 + rng.random(len(f)) * 1e-3 + 1.0
    return f


def test_f06_mid_rank_hand_example(geff):
    t_ref = FF.step(2015, 12)
    times = [FF.step(y, 1) for y in range(2003, 2015)] + [FF.step(2015, 1)]
    x = [float(v) for v in range(1, 13)] + [5.5]
    u = ["a"] * len(times)
    p = _pct(geff, u, times, x, t_ref)
    assert p[-1] == pytest.approx(5.0 / 12.0, abs=1e-15)                # R = the 12 other Januaries
    for v, want in ((5.0, 4.5 / 12.0), (0.5, 0.0), (99.0, 1.0), (12.0, 11.5 / 12.0), (1.0, 0.5 / 12.0)):
        q = _pct(geff, u, times, x[:-1] + [v], t_ref)
        assert q[-1] == pytest.approx(want, abs=1e-15), (v, q[-1], want)


def test_f06_rows_inside_the_reference_leave_their_own_month_out(geff):
    t_ref = FF.step(2015, 12)
    f = _table()
    p = _pct(geff, f["unit"], f["time"], f["x"], t_ref)
    hand = FF.pct_hand(f["unit"], f["time"], f["x"], t_ref, 10)
    np.testing.assert_allclose(p, hand, rtol=0, atol=1e-12)
    k = int(np.flatnonzero((f["unit"] == "u2") & (f["time"] == FF.step(2010, 7)))[0])
    for v in (-1.0, 0.0, float(f["x"].median()), 1e9):                # its own value moves it through x only
        g = f.copy()
        g.loc[k, "x"] = v
        q = _pct(geff, g["unit"], g["time"], g["x"], t_ref)
        ref = g[(g["unit"] == "u2") & (np.mod(g["time"] - 1, 12) == 6) & (g["time"] <= t_ref) & (g.index != k)]["x"]
        assert len(ref) == 12
        assert q[k] == pytest.approx(FF.mid_rank(v, ref.to_numpy()), abs=1e-15), v
    assert int(((f["time"] <= t_ref) & (f["unit"] == "u1")).sum()) == 13 * 12


@pytest.mark.parametrize("lead", [0, 6])
def test_f06_later_values_never_move_a_percentile(geff, lead):
    """Every FWI value with t' > T_ref other than the row's own is perturbed (two disjoint halves, so every row with
    t > T_ref keeps its own value in one of the two runs): no percentile moves."""
    cut = FF.FACT_CUTS[lead]
    t_ref = cut["guard_cut"]
    assert t_ref != cut["fit_cut"]
    f = _table()
    p = _pct(geff, f["unit"], f["time"], f["x"], t_ref)
    late = (f["time"] > t_ref).to_numpy()
    rng = np.random.default_rng(7)
    halves = np.zeros(len(f), dtype=bool)
    halves[np.flatnonzero(late)[::2]] = True
    for perturbed in (halves, late & ~halves):
        g = f.copy()
        g.loc[perturbed, "x"] = g.loc[perturbed, "x"] * rng.uniform(0.1, 10.0, int(perturbed.sum())) + 50.0
        q = _pct(geff, g["unit"], g["time"], g["x"], t_ref)
        kept = ~perturbed
        np.testing.assert_array_equal(q[kept], p[kept])
    pick = (f["time"] >= 24193) & (f["time"] <= cut["fit_cut"] - FF.OFFSET)     # inner (lead 0) / guard (lead 6)
    assert pick.sum() > 0 and np.isfinite(p[pick.to_numpy()]).all()
    test = (f["time"] >= FF.TEST_START).to_numpy()
    assert np.isfinite(p[test]).all()
    # a fit-cut reference would rank the pick rows against later FWI: a different percentile somewhere
    pf = _pct(geff, f["unit"], f["time"], f["x"], cut["fit_cut"])
    assert (pf[pick.to_numpy()] != p[pick.to_numpy()]).any()


def test_f06_too_small_reference_is_nan_for_that_row_only(geff):
    t_ref = FF.step(2015, 12)
    f = _table()
    short = (f["unit"] == "u3") & (np.mod(f["time"] - 1, 12) == 0) & (f["time"] < FF.step(2007, 1))
    f.loc[short, "x"] = np.nan                                         # u3 January: 2003-2006 missing
    f.loc[(f["unit"] == "u1") & (f["time"] == FF.step(2020, 5)), "x"] = np.nan
    p = _pct(geff, f["unit"], f["time"], f["x"], t_ref)
    hand = FF.pct_hand(f["unit"], f["time"], f["x"], t_ref, 10)
    np.testing.assert_array_equal(np.isnan(p), np.isnan(hand))
    np.testing.assert_allclose(p[np.isfinite(hand)], hand[np.isfinite(hand)], rtol=0, atol=1e-12)
    jan_u3 = ((f["unit"] == "u3") & (np.mod(f["time"] - 1, 12) == 0)).to_numpy()
    after = jan_u3 & (f["time"] > t_ref).to_numpy()
    assert np.isnan(p[after]).all()                                    # |R| = 9 < 10
    assert np.isfinite(p[((f["unit"] == "u3") & (np.mod(f["time"] - 1, 12) == 1)).to_numpy()]).all()
    assert np.isnan(p[((f["unit"] == "u1") & (f["time"] == FF.step(2020, 5))).to_numpy()]).all()   # x NaN


def _frame_pct(frame, t_ref, min_ref=10):
    f = frame.drop_duplicates(subset=["unit", "time"]).sort_values(["unit", "time"]).reset_index(drop=True)
    return f, FF.pct_hand(f["unit"], f["time"], f["x__fwi_mean"], t_ref, min_ref)


@pytest.mark.parametrize("kind", ["era5", "seas5"])
def test_f06_build_uses_the_guard_cut(geff, synth_products, tmp_path, kind):
    lead = 0 if kind == "era5" else 6
    toy = (FF.synth_era5_toy if kind == "era5" else FF.synth_seas5_toy)(tmp_path, synth_products)
    frame = geff.build(toy.ctx(), toy.rival, lead, "all")
    f, hand = _frame_pct(frame, FF.FACT_CUTS[lead]["guard_cut"])
    got = f["x__fwi_pct"].to_numpy(np.float64)
    assert np.isfinite(got).sum() > 0.8 * len(got)
    np.testing.assert_array_equal(np.isnan(got), np.isnan(hand))
    np.testing.assert_allclose(got[np.isfinite(hand)], hand[np.isfinite(hand)], rtol=0, atol=1e-12)
    _, fit_cut = _frame_pct(frame, FF.FACT_CUTS[lead]["fit_cut"])
    both = np.isfinite(fit_cut) & np.isfinite(got)
    assert (np.abs(fit_cut[both] - got[both]) > 1e-9).any()             # never the fit cut
    pick = frame[frame["time"].between(24193, FF.FACT_CUTS[lead]["fit_cut"] - FF.OFFSET)]
    assert len(pick) and np.isfinite(pick["x__fwi_pct"]).all()


def test_f06_build_refuses_a_reference_reaching_the_test_or_pick_rows(geff, synth_products, tmp_path):
    # ERA5 lead 0: a guard cut at the first test step
    cuts = {0: dict(FF.FACT_CUTS[0], guard_cut=FF.TEST_START)}
    toy = FF.synth_era5_toy(tmp_path / "a", synth_products)
    ctx = toy.ctx(run=FF.FakeRun(cuts=cuts))
    FF.refuses(geff.build, ctx, toy.rival, 0, "all", kinds=_refusals(geff))
    # ERA5 lead 0: a guard cut one step later than the first inner issue (24193): reference info_end 24194
    toy = FF.synth_era5_toy(tmp_path / "b", synth_products)
    first_inner = int(toy.ctx().keys("inner")["issue"].min())
    assert first_inner == 24193
    ctx = toy.ctx(run=FF.FakeRun(cuts={0: dict(FF.FACT_CUTS[0], guard_cut=first_inner + 1)}))
    FF.refuses(geff.build, ctx, toy.rival, 0, "all", kinds=_refusals(geff))
    # the facts' cut passes (reference info_end 24192 < 24193)
    geff.build(toy.ctx(), toy.rival, 0, "all")
    # SEAS5 lead 6: reference info_end = T_ref - 6 must stay below the first guard issue (24187)
    toy6 = FF.synth_seas5_toy(tmp_path / "c", synth_products)
    first_guard = int(toy6.ctx().keys("guard")["issue"].min())
    assert first_guard == 24187
    bad = dict(FF.FACT_CUTS)
    bad[6] = dict(FF.FACT_CUTS[6], guard_cut=first_guard + 6)          # T_ref - 6 = 24187: not below it
    FF.refuses(geff.build, toy6.ctx(run=FF.FakeRun(cuts=bad)), toy6.rival, 6, "all", kinds=_refusals(geff))
    geff.build(toy6.ctx(), toy6.rival, 6, "all")                         # 24187 - 6 = 24181 < 24187 passes
