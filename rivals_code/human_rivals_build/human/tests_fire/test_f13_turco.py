"""T-F13 the SPI-lag runner adapters/fire_turco.py (SPEC_HUMAN_PARTB.txt 4, 4.2, 4.3; OWNER DECISION OD-1), on a
synthetic toy (3 groups x 8 units, 2003-2022, the facts' cuts; y made from the normal by the form).

- T1 picks the generating SPI scale by SSE on the in-season training rows and recovers b; the fire season of a toy
  normal is the right 3 months (a Dec-Jan-Feb wrap included; a tie -> the earliest start month); outside the season
  pre = N; |SPI| > 3.5 is missing (dropped at fit, pre = N at predict, counted);
- T2 (all months, the fixed x__spi_03m) and T3 (in season, y - N = b1 N SPI_3 + b2 N SPI_12) recover their slopes;
- methods.run_predict passes with the run's R8 (spi steps 0: info_end = issue) and refuses the same rows on a run
  whose spi_03m has steps 1; target_obs_end = cut - offset passes T2, + 1 refuses; labels only inside fit.
Imports only `from adapters import fire_enso, fire_turco` (the `runners` fixture).
"""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from tests_fire import fixtures_fire as FF

SEASON = {"g1": [6, 7, 8], "g2": [12, 1, 2], "g3": [3, 4, 5]}
B = {"g1": 0.12, "g2": -0.08, "g3": 0.2}


@pytest.fixture(scope="module")
def T(runners):
    return runners[1]


def _months(t):
    return np.mod(np.asarray(t, np.int64) - 1, 12) + 1


def _groups_of(res):
    return res["groups"] if isinstance(res, dict) and "groups" in res else res


def _toy(gen="x__spi_06m", corrupt=True):
    f = FF.runner_frame(6)
    if corrupt:                                                   # corrupt SPI (precip sentinel) on a few rows
        f.loc[f.index[7::211], gen] = -9.9
        f.loc[f.index[11::223], "x__spi_01m"] = 12.0
    m = _months(f["time"])
    ins = np.array([mm in SEASON[g] for g, mm in zip(f["group"], m)])
    N = f["N"].to_numpy()
    s = f[gen].to_numpy(np.float64)
    ok = np.abs(s) <= 3.5
    b = f["group"].map(B).to_numpy(np.float64)
    y = np.where(ins & ok, N * (1.0 + b * np.where(ok, s, 0.0)), N * (1.0 + 0.3 * f["x__spi_24m"].to_numpy()))
    return f, m, ins, N, y


def _spi(f, sel):
    return f.loc[sel, FF.SPI_COLS].reset_index(drop=True)


def test_f13_module_surface(T):
    assert T.PARAMS_FORMAT == "human-fire-turco-params/1"
    for name in ("fit", "predict", "fire_season", "fit_ratio", "fit_groups", "predict_values"):
        assert callable(getattr(T, name, None)), name


def test_f13_fire_season(T):
    f = FF.runner_frame(6)
    seasons = T.fire_season(f["group"].to_numpy(), _months(f["time"]), f["N"].to_numpy(), 3)
    for g, w in SEASON.items():
        got = [int(v) for v in seasons[g]]
        assert sorted(got) == sorted(w), (g, got)
        assert all(got[i + 1] == got[i] % 12 + 1 for i in range(2)), got
    flat = T.fire_season(np.array(["z"] * 24), np.tile(np.arange(1, 13), 2), np.full(24, 0.25), 3)
    assert [int(v) for v in flat["z"]] == [1, 2, 3]                  # a tie: the earliest start month
    # December alone is larger: Oct-Nov-Dec, Nov-Dec-Jan and Dec-Jan-Feb tie -> the earliest start, October
    late = T.fire_season(np.array(["w"] * 12), np.arange(1, 13), np.r_[np.full(11, 0.25), 0.5], 3)   # exact sums
    assert [int(v) for v in late["w"]] == [10, 11, 12]


def test_f13_t1_picks_the_generating_scale_and_recovers_b(T):
    f, m, ins, N, y = _toy()
    fit_rows = f["r_refit"].to_numpy()
    res = T.fit_groups(f["group"].to_numpy()[fit_rows], m[fit_rows], y[fit_rows], N[fit_rows], _spi(f, fit_rows),
                       "T1", FF.TURCO_OPTIONS)
    for g, b in B.items():
        rec = _groups_of(res)[g]
        assert rec["scale"] == "x__spi_06m", (g, rec.get("scale"), rec.get("sse_by_scale"))
        assert rec["b"] == pytest.approx(b, rel=1e-9), g
        assert sorted(int(v) for v in rec["season"]) == sorted(SEASON[g])
        assert rec["fallback"] is False
        sse = rec["sse_by_scale"]
        assert set(sse) == set(FF.SPI_COLS) and min(sse, key=sse.get) == "x__spi_06m"
    test = f["is_test"].to_numpy()
    pre, counts = T.predict_values(f["group"].to_numpy()[test], m[test], N[test], _spi(f, test), res,
                                   FF.TURCO_OPTIONS)
    s6 = f["x__spi_06m"].to_numpy()[test]
    ok = np.abs(s6) <= 3.5
    bt = f["group"].map(B).to_numpy()[test]
    i_t = ins[test]
    np.testing.assert_array_equal(pre[~i_t], N[test][~i_t])          # outside the fire season: the normal
    np.testing.assert_allclose(pre[i_t & ok], (N[test] * (1.0 + bt * s6))[i_t & ok], rtol=1e-9, atol=1e-15)
    np.testing.assert_array_equal(pre[i_t & ~ok], N[test][i_t & ~ok])  # |SPI| > 3.5 -> missing -> the normal
    assert (i_t & ~ok & (N[test] > 0)).sum() > 0
    ints = set(int(v) for v in counts.values() if isinstance(v, (int, np.integer)))
    n_bad = int((~ok).sum())
    n_used = int((i_t & ~ok & (N[test] > 0)).sum())
    assert n_bad in ints or n_used in ints, counts


def test_f13_t1_tie_takes_the_first_scale_of_the_options(T):
    f, m, ins, N, y = _toy(gen="x__spi_03m", corrupt=False)
    f["x__spi_12m"] = f["x__spi_03m"]                               # 3 and 12 identical: SSE tie -> spi_03m first
    fit_rows = f["r_refit"].to_numpy()
    res = T.fit_groups(f["group"].to_numpy()[fit_rows], m[fit_rows], y[fit_rows], N[fit_rows], _spi(f, fit_rows),
                       "T1", FF.TURCO_OPTIONS)
    assert all(_groups_of(res)[g]["scale"] == "x__spi_03m" for g in B)
    opt = dict(FF.TURCO_OPTIONS, scales=["x__spi_12m", "x__spi_03m", "x__spi_01m", "x__spi_06m", "x__spi_24m"])
    res2 = T.fit_groups(f["group"].to_numpy()[fit_rows], m[fit_rows], y[fit_rows], N[fit_rows], _spi(f, fit_rows),
                        "T1", opt)
    assert all(_groups_of(res2)[g]["scale"] == "x__spi_12m" for g in B)


def test_f13_t2_and_t3(T):
    f = FF.runner_frame(6)
    m = _months(f["time"])
    N = f["N"].to_numpy()
    s3, s12 = f["x__spi_03m"].to_numpy(), f["x__spi_12m"].to_numpy()
    b = f["group"].map(B).to_numpy(np.float64)
    fit_rows, test = f["r_refit"].to_numpy(), f["is_test"].to_numpy()
    y2 = N * (1.0 + b * s3)
    r2 = T.fit_groups(f["group"].to_numpy()[fit_rows], m[fit_rows], y2[fit_rows], N[fit_rows], _spi(f, fit_rows),
                      "T2", FF.TURCO_OPTIONS)
    for g, bb in B.items():
        assert _groups_of(r2)[g]["b"] == pytest.approx(bb, rel=1e-9)
    p2, _ = T.predict_values(f["group"].to_numpy()[test], m[test], N[test], _spi(f, test), r2, FF.TURCO_OPTIONS)
    np.testing.assert_allclose(p2, y2[test], rtol=1e-9, atol=1e-15)            # every month (no season in T2)
    ins = np.array([mm in SEASON[g] for g, mm in zip(f["group"], m)])
    b2 = -0.5 * b
    y3 = np.where(ins, N * (1.0 + b * s3 + b2 * s12), N)
    r3 = T.fit_groups(f["group"].to_numpy()[fit_rows], m[fit_rows], y3[fit_rows], N[fit_rows], _spi(f, fit_rows),
                      "T3", FF.TURCO_OPTIONS)
    for g, bb in B.items():
        rec = _groups_of(r3)[g]
        assert rec["b1"] == pytest.approx(bb, rel=1e-9) and rec["b2"] == pytest.approx(-0.5 * bb, rel=1e-9)
    p3, _ = T.predict_values(f["group"].to_numpy()[test], m[test], N[test], _spi(f, test), r3, FF.TURCO_OPTIONS)
    np.testing.assert_allclose(p3, y3[test], rtol=1e-9, atol=1e-15)
    np.testing.assert_array_equal(p3[~ins[test]], N[test][~ins[test]])


def _ctx(tmp_path, f, y, lead=6, r8=None, form="T1"):
    rival = FF.turco_rival(form)
    sets = FF.runner_sets(f, y, FF.SPI_COLS)
    return FF.runner_ctx(tmp_path, rival, lead, sets, r8=r8), rival, sets


def test_f13_runner_fit_predict_and_labels(tmp_path, T):
    f, m, ins, N, y = _toy()
    ctx, rival, sets = _ctx(tmp_path, f, y)
    FF.refuses(T.fit, ctx, dict(rival), 6, "guardfit", kinds=FF.tool_refusals(), words=("outside",))
    params = FF.fit_in_scope(T, ctx, rival, 6, "guardfit")
    assert ctx.label_calls == ["guardfit"]
    assert params["format"] == T.PARAMS_FORMAT and params["fit_set"] == "guardfit" and params["form"] == "T1"
    for g, b in B.items():
        rec = _groups_of(params)[g]
        assert rec["scale"] == "x__spi_06m" and rec["b"] == pytest.approx(b, rel=1e-9)
    out = T.predict(ctx, dict(rival), 6, params, "guard")
    assert ctx.label_calls == ["guardfit"]
    assert np.isfinite(out["pre"].to_numpy(np.float64)).all()
    with ctx._fitting("tune"):
        FF.refuses(T.fit, ctx, dict(rival), 6, "tune")


@pytest.mark.parametrize("lead,tier", [(6, "P"), (12, "X")])
def test_f13_timing_through_methods_run_predict(tmp_path, T, lead, tier):
    from rivals_human import methods as ME
    f = FF.runner_frame(lead)
    m = _months(f["time"])
    b = f["group"].map(B).to_numpy(np.float64)
    y = f["N"].to_numpy() * (1.0 + b * f["x__spi_06m"].to_numpy())
    ctx, rival, sets = _ctx(tmp_path, f, y, lead=lead)
    for fit_set, score_set, cut in (("guardfit", "guard", "guard_cut"), ("refit", "test", "fit_cut")):
        params = FF.fit_in_scope(T, ctx, rival, lead, fit_set)
        keys = ctx.keys(score_set)
        frame, rec = ME.run_predict(T, ctx, rival, lead, params, score_set, keys, tier)
        assert rec["t1_breaks"] == 0 and rec["t2_breaks"] == 0 and rec["predicted"] == len(keys)
        np.testing.assert_array_equal(frame["info_end"].to_numpy(np.int64), keys["issue"].to_numpy(np.int64))
        np.testing.assert_array_equal(frame["target_obs_end"].to_numpy(np.float64),
                                      np.full(len(keys), FF.FACT_CUTS[lead][cut] - FF.OFFSET))
        out = T.predict(ctx, dict(rival), lead, params, score_set)
        ctx1 = FF.runner_ctx(tmp_path, rival, lead, sets, r8=FF.fact_r8(spi_03m=1))
        FF.refuses(ME.run_predict, SimpleNamespace(predict=lambda *a, **k: out.copy()), ctx1, rival, lead, params,
                   score_set, keys, tier, kinds=FF.tool_refusals(), words=("T1",))
        late = out.copy()
        late["target_obs_end"] = late["target_obs_end"] + 1.0
        FF.refuses(ME.run_predict, SimpleNamespace(predict=lambda *a, **k: late.copy()), ctx, rival, lead, params,
                   score_set, keys, tier, kinds=FF.tool_refusals(), words=("T2",))
