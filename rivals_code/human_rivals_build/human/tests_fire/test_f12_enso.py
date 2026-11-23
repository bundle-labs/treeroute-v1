"""T-F12 the ENSO-lag runner adapters/fire_enso.py (SPEC_HUMAN_PARTB.txt 4, 4.1, 4.3; OWNER DECISION OD-2), on a
synthetic toy (3 groups x 8 units, 2003-2022, lead 6 and 12, the facts' cuts; y made from the normal by the form).

- E1 y = N (1 + b_g ONI) recovers b_g; a group with < 100 usable rows falls back to b = 0 (pre = N, flagged);
- a NaN or |ONI| > 5 is dropped at fit and predicts the normal (counted);
- E2: the fire season is the 3 consecutive months of largest summed normal (a Dec-Jan-Feb wrap included), b from the
  in-season rows only, pre = N outside it; E3: one slope per group x month, a month with < 100 rows on the group slope;
- labels only through ctx.fit_labels(fit_set) inside fit (the stand-in ctx refuses outside a fit scope; predict
  asks for none); fit on "tune" refuses; params survive a JSON round trip; two fits are byte-equal;
- methods.run_predict (tier P, lead 6) passes on a run whose R8 gives oni steps 3 and refuses the same rows on a
  run with steps 4 (info_end = issue - 3 > issue - 4); target_obs_end = cut - offset passes T2, + 1 refuses; tier X
  at lead 12 passes the same checks.
Imports only `from adapters import fire_enso, fire_turco` (the `runners` fixture).
"""

import json
from types import SimpleNamespace

import numpy as np
import pytest

from tests_fire import fixtures_fire as FF

B = {"g1": 0.3, "g2": -0.2, "g3": 0.15}


@pytest.fixture(scope="module")
def E(runners):
    return runners[0]


def _frame(lead=6, bad_oni=True, small_group=True):
    groups = ("g1", "g2", "g3", "g4") if small_group else ("g1", "g2", "g3")
    f = FF.runner_frame(lead, groups=groups, peak={"g1": 7, "g2": 1, "g3": 4, "g4": 7})
    if small_group:                                           # g4: one unit, 60 months -> < 100 usable rows
        keep = (f["group"] != "g4") | ((f["unit"] == "g4_u00") & (f["time"] < FF.step(2008, 1)))
        f = f[keep].reset_index(drop=True)
    if bad_oni:
        iss = sorted(set(f["issue"]))
        nan_iss, big_iss = iss[30::97], iss[61::97]           # a few issue months with a missing / corrupt ONI
        f.loc[f["issue"].isin(nan_iss), "x__oni"] = np.nan
        f.loc[f["issue"].isin(big_iss), "x__oni"] = 6.5
    return f


def _y_e1(f, b=B):
    s = f["x__oni"].to_numpy(np.float64)
    bg = f["group"].map(lambda g: b.get(g, 0.25)).to_numpy(np.float64)
    ok = np.isfinite(s) & (np.abs(s) <= 5.0)
    return np.where(ok, f["N"].to_numpy() * (1.0 + bg * np.where(ok, s, 0.0)), f["N"].to_numpy())


def _ctx(tmp_path, f, y, form="E1", lead=6, r8=None):
    rival = FF.enso_rival(form)
    sets = FF.runner_sets(f, y, ["x__oni"])
    return FF.runner_ctx(tmp_path, rival, lead, sets, r8=r8), rival, sets


def _months(t):
    return np.mod(np.asarray(t, np.int64) - 1, 12) + 1


def _groups_of(res):
    return res["groups"] if isinstance(res, dict) and "groups" in res else res


def test_f12_module_surface(E):
    assert E.PARAMS_FORMAT == "human-fire-enso-params/1"
    for name in ("fit", "predict", "fire_season", "fit_ratio", "fit_groups", "predict_values"):
        assert callable(getattr(E, name, None)), name


def test_f12_fit_ratio_through_the_origin(E):
    rng = np.random.default_rng(1)
    N = rng.uniform(0.001, 0.05, 300)
    s = rng.normal(0, 1, 300)
    y = N * (1.0 + 0.37 * s)
    b, n, fb = E.fit_ratio(N, s, y, 100)
    assert b == pytest.approx(0.37, rel=1e-12) and n == 300 and fb is False
    want = float(np.dot(N * s, y - N) / np.dot(N * s, N * s))
    y2 = y + rng.normal(0, 0.001, 300)
    assert E.fit_ratio(N, s, y2, 100)[0] == pytest.approx(float(np.dot(N * s, y2 - N) / np.dot(N * s, N * s)),
                                                          rel=1e-12)
    assert want == pytest.approx(0.37, rel=1e-12)
    b, n, fb = E.fit_ratio(N[:99], s[:99], y[:99], 100)
    assert (b, fb) == (0.0, True) and n == 99
    b, n, fb = E.fit_ratio(N, np.zeros(300), y, 100)                  # sum((N s)^2) == 0 -> the normal
    assert (b, fb) == (0.0, True)
    Nz = N.copy()
    Nz[:250] = 0.0                                                    # N > 0 rows only: 50 usable
    assert E.fit_ratio(Nz, s, y, 100)[1:] == (50, True)


def test_f12_e1_recovers_the_slopes_and_falls_back(tmp_path, E):
    f = _frame()
    y = _y_e1(f)
    ctx, rival, sets = _ctx(tmp_path, f, y)
    params = FF.fit_in_scope(E, ctx, rival, 6, "guardfit")
    assert ctx.label_calls == ["guardfit"]
    assert params["format"] == E.PARAMS_FORMAT and params["fit_set"] == "guardfit" and params["form"] == "E1"
    g = _groups_of(params)
    for grp, b in B.items():
        assert g[grp]["b"] == pytest.approx(b, rel=1e-9), grp
        assert g[grp]["fallback"] is False and g[grp]["n"] >= 100
    assert g["g4"]["fallback"] is True and g["g4"]["b"] == 0.0 and g["g4"]["n"] < 100
    out = E.predict(ctx, rival, 6, params, "guard")
    assert ctx.label_calls == ["guardfit"]                            # predict asks for no label
    k = sets["guard"]["keys"]
    assert list(out[FF.KEYS].astype(str).values.tolist()) == list(k[FF.KEYS].astype(str).values.tolist())
    pre = out["pre"].to_numpy(np.float64)
    N = sets["guard"]["normal"]["identity"]
    s = sets["guard"]["extras"]["x__oni"].to_numpy(np.float64)
    bg = k["group"].map(lambda gg: B.get(gg, 0.0)).to_numpy(np.float64)
    ok = np.isfinite(s) & (np.abs(s) <= 5.0)
    np.testing.assert_allclose(pre[ok], (N * (1.0 + bg * s))[ok], rtol=1e-9, atol=1e-15)
    np.testing.assert_array_equal(pre[~ok], N[~ok])                   # missing / corrupt ONI -> the normal
    assert np.isfinite(pre).all()
    assert (~ok).sum() > 0


def test_f12_invalid_oni_is_dropped_and_counted(E):
    f = _frame(small_group=False)
    y = _y_e1(f)
    fit_rows = f["r_refit"].to_numpy()
    s = f["x__oni"].to_numpy(np.float64)
    res = E.fit_groups(f["group"].to_numpy()[fit_rows], _months(f["time"])[fit_rows], y[fit_rows],
                       f["N"].to_numpy()[fit_rows], s[fit_rows], "E1", FF.ENSO_OPTIONS)
    for grp, b in B.items():
        assert _groups_of(res)[grp]["b"] == pytest.approx(b, rel=1e-9)
    # a corrupt ONI used at fit would bend the slope: y of those rows made with the corrupt value
    y_bad = y.copy()
    big = (s == 6.5)
    y_bad[big] = f["N"].to_numpy()[big] * (1.0 + 0.9 * 6.5)
    res2 = E.fit_groups(f["group"].to_numpy()[fit_rows], _months(f["time"])[fit_rows], y_bad[fit_rows],
                        f["N"].to_numpy()[fit_rows], s[fit_rows], "E1", FF.ENSO_OPTIONS)
    assert _groups_of(res2)["g1"]["b"] == pytest.approx(B["g1"], rel=1e-9)        # the |ONI| > 5 rows were dropped
    test = f["is_test"].to_numpy()
    N = f["N"].to_numpy()[test]
    pre, counts = E.predict_values(f["group"].to_numpy()[test], _months(f["time"])[test], N, s[test], res,
                                   FF.ENSO_OPTIONS)
    bad = ~(np.isfinite(s[test]) & (np.abs(s[test]) <= 5.0))
    np.testing.assert_array_equal(pre[bad], N[bad])
    assert isinstance(counts, dict)
    ints = set(int(v) for v in counts.values() if isinstance(v, (int, np.integer)))
    n_nan, n_big = int((~np.isfinite(s[test])).sum()), int((np.abs(s[test]) > 5.0).sum())
    n_used = int((bad & (N > 0)).sum())
    assert n_nan + n_big > 0
    assert (n_nan in ints and n_big in ints) or (n_nan + n_big) in ints or n_used in ints, counts


def test_f12_e2_fire_season_and_outside_rows(E):
    f = _frame(bad_oni=False, small_group=False)
    seasons = E.fire_season(f["group"].to_numpy(), _months(f["time"]), f["N"].to_numpy(), 3)
    want = {"g1": [6, 7, 8], "g2": [12, 1, 2], "g3": [3, 4, 5]}
    for g, w in want.items():
        got = [int(m) for m in seasons[g]]
        assert sorted(got) == sorted(w), (g, got)
        assert all(got[i + 1] == got[i] % 12 + 1 for i in range(2)), got           # consecutive, cyclic
    s = f["x__oni"].to_numpy(np.float64)
    m = _months(f["time"])
    ins = np.array([mm in want[g] for g, mm in zip(f["group"], m)])
    N = f["N"].to_numpy()
    b_in = f["group"].map(B).to_numpy(np.float64)
    y = np.where(ins, N * (1.0 + b_in * s), N * (1.0 - 0.5 * s))   # outside: another relation, never fitted
    fit_rows = f["r_refit"].to_numpy()
    res = E.fit_groups(f["group"].to_numpy()[fit_rows], m[fit_rows], y[fit_rows], N[fit_rows], s[fit_rows], "E2",
                       FF.ENSO_OPTIONS)
    for g, b in B.items():
        rec = _groups_of(res)[g]
        assert rec["b"] == pytest.approx(b, rel=1e-9), g
        assert sorted(int(v) for v in rec["season"]) == sorted(want[g])
    test = f["is_test"].to_numpy()
    pre, _ = E.predict_values(f["group"].to_numpy()[test], m[test], N[test], s[test], res, FF.ENSO_OPTIONS)
    out = ~ins[test]
    np.testing.assert_array_equal(pre[out], N[test][out])
    np.testing.assert_allclose(pre[~out], (N * (1.0 + b_in * s))[test][~out], rtol=1e-9, atol=1e-15)


def test_f12_e3_monthly_slopes(E):
    f = _frame(bad_oni=False, small_group=False)
    m = _months(f["time"])
    s = f["x__oni"].to_numpy(np.float64)
    N = f["N"].to_numpy()
    bm = 0.02 * m - 0.1 + 0.4 * (m == 7)                            # July's own slope 0.44, far from the rest
    y = N * (1.0 + bm * s)
    fit_rows = f["r_refit"].to_numpy()
    g1_jul = (f["group"].to_numpy() == "g1") & (m == 7)
    thin = fit_rows & ~(g1_jul & (f["time"].to_numpy() > FF.step(2009, 12)))     # g1 July: 7 years x 8 = 56 rows
    assert 0 < (thin & g1_jul).sum() < 100
    args = (f["group"].to_numpy()[thin], m[thin], y[thin], N[thin], s[thin])
    res = E.fit_groups(*args, "E3", FF.ENSO_OPTIONS)
    e1 = E.fit_groups(*args, "E1", FF.ENSO_OPTIONS)
    test = f["is_test"].to_numpy()
    pre, _ = E.predict_values(f["group"].to_numpy()[test], m[test], N[test], s[test], res, FF.ENSO_OPTIONS)
    gt, mt = f["group"].to_numpy()[test], m[test]
    want = (N * (1.0 + bm * s))[test]
    regular = (N[test] > 0) & ~((gt == "g1") & (mt == 7))
    np.testing.assert_allclose(pre[regular], want[regular], rtol=1e-9, atol=1e-15)
    on_group = (gt == "g1") & (mt == 7)
    b_g1 = _groups_of(e1)["g1"]["b"]
    np.testing.assert_allclose(pre[on_group], (N[test] * (1.0 + b_g1 * s[test]))[on_group], rtol=1e-12, atol=1e-15)
    assert abs(b_g1 - 0.44) > 0.05                                   # the group slope is not July's own


def test_f12_labels_only_inside_fit(tmp_path, E):
    f = _frame()
    ctx, rival, sets = _ctx(tmp_path, f, _y_e1(f))
    FF.refuses(E.fit, ctx, dict(rival), 6, "guardfit", kinds=FF.tool_refusals(), words=("outside",))
    assert ctx.label_calls == []
    params = FF.fit_in_scope(E, ctx, rival, 6, "guardfit")
    calls = list(ctx.label_calls)
    E.predict(ctx, dict(rival), 6, params, "guard")
    assert ctx.label_calls == calls
    with ctx._fitting("tune"):
        FF.refuses(E.fit, ctx, dict(rival), 6, "tune")
    with ctx._fitting("refit"):
        p2 = E.fit(ctx, dict(rival), 6, "refit")
    FF.refuses(E.predict, ctx, dict(rival), 6, p2, "guard")         # refit params score the test set only


def test_f12_params_json_round_trip_and_determinism(tmp_path, E):
    from rivals_human import methods as ME
    f = _frame()
    ctx, rival, sets = _ctx(tmp_path, f, _y_e1(f))
    p1 = FF.fit_in_scope(E, ctx, rival, 6, "guardfit")
    p2 = FF.fit_in_scope(E, ctx, rival, 6, "guardfit")
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)
    rt = json.loads(json.dumps(p1, sort_keys=True))
    assert rt == p1
    with ctx._fitting("guardfit"):
        p3 = ME.run_fit(E, ctx, rival, 6, "guardfit")
    assert p3 == rt
    a = E.predict(ctx, dict(rival), 6, p1, "guard")
    b = E.predict(ctx, dict(rival), 6, rt, "guard")
    np.testing.assert_array_equal(a["pre"].to_numpy(), b["pre"].to_numpy())


@pytest.mark.parametrize("lead,tier", [(6, "P"), (12, "X")])
def test_f12_timing_through_methods_run_predict(tmp_path, E, lead, tier):
    from rivals_human import methods as ME
    f = _frame(lead=lead)
    ctx, rival, sets = _ctx(tmp_path, f, _y_e1(f), lead=lead)
    for fit_set, score_set, cut in (("guardfit", "guard", "guard_cut"), ("refit", "test", "fit_cut")):
        params = FF.fit_in_scope(E, ctx, rival, lead, fit_set)
        keys = ctx.keys(score_set)
        frame, rec = ME.run_predict(E, ctx, rival, lead, params, score_set, keys, tier)
        assert rec["t1_breaks"] == 0 and rec["t2_breaks"] == 0 and rec["predicted"] == len(keys)
        np.testing.assert_array_equal(frame["info_end"].to_numpy(np.int64), keys["issue"].to_numpy(np.int64) - 3)
        want_toe = FF.FACT_CUTS[lead][cut] - FF.OFFSET
        np.testing.assert_array_equal(frame["target_obs_end"].to_numpy(np.float64), np.full(len(keys), want_toe))
        out = E.predict(ctx, dict(rival), lead, params, score_set)
        ctx4 = FF.runner_ctx(tmp_path, rival, lead, sets, r8=FF.fact_r8(oni=4))
        FF.refuses(ME.run_predict, SimpleNamespace(predict=lambda *a, **k: out.copy()), ctx4, rival, lead, params,
                   score_set, keys, tier, kinds=FF.tool_refusals(), words=("T1",))
        late = out.copy()
        late["target_obs_end"] = late["target_obs_end"] + 1.0
        FF.refuses(ME.run_predict, SimpleNamespace(predict=lambda *a, **k: late.copy()), ctx, rival, lead, params,
                   score_set, keys, tier, kinds=FF.tool_refusals(), words=("T2",))
