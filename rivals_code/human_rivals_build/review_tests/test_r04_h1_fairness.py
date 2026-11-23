"""R04: NDVI H1 (adapters/ndvi_bardl.py) - leakage and "best fair shot".

Leakage: predict() is row-wise (a score row's prediction uses only its own features plus fit-set parameters), never
asks for labels, and the climate means it subtracts come from the FIT set.
Fairness (ISSUE 4): with `standardize: false` (registry/ndvi.yaml:44, the current setting) the prediction depends on
the UNITS the climate columns happen to be stored in, because BayesianRidge puts one shared prior precision on every
coefficient (ndvi_bardl.py:284-291). A method whose answer changes when precipitation is written in metres instead of
millimetres is not getting its best fair shot; standardize: true is unit-free.
Toy data: the builder's own synthetic ARDL (tests_builder_c/test_pm25_ndvi_adapters.py:326-381), imported read-only.
"""
import numpy as np
import pandas as pd
import pytest

from adapters import ndvi_bardl as BD
from tests_builder_c import test_pm25_ndvi_adapters as TC

PRECIP = ["x__V02_total_precip_mm", "x__V02_total_precip_mm_lag1", "x__V02_total_precip_mm_lag2"]


def _rival(standardize):
    return dict(TC.H1_RIVAL, options=dict(TC.H1_RIVAL["options"], standardize=standardize))


def _rescaled_ctx(factor):
    ctx, series = TC.ndvi_ctx()
    for name in ("tune", "inner"):
        k, y, z, h, e = ctx.sets[name]
        e = e.copy()
        for c in PRECIP:
            e[c] = e[c] * factor
        ctx.sets[name] = (k, y, z, h, e)
    return ctx


def _fit_predict(ctx, standardize):
    p = BD.fit(ctx, _rival(standardize), 0, "tune")
    out = BD.predict(ctx, _rival(standardize), 0, p, "inner")
    return out["pre"].to_numpy(np.float64), p


def _inner_mae(ctx, pre):
    k, y, z, h, e = ctx.sets["inner"]
    ok = np.isfinite(pre)
    return float(np.mean(np.abs(pre[ok] - y[ok])))


def test_r04_h1_unscaled_answer_depends_on_storage_units():
    """Precipitation in mm vs in 1/1000 of the same unit: the unscaled fit changes its predictions (ISSUE 4), the
    standardized fit does not."""
    a, pa = _fit_predict(_rescaled_ctx(1.0), False)
    b, pb = _fit_predict(_rescaled_ctx(1e-3), False)
    ok = np.isfinite(a)
    diff_unscaled = float(np.max(np.abs(a[ok] - b[ok])))
    sa, _ = _fit_predict(_rescaled_ctx(1.0), True)
    sb, _ = _fit_predict(_rescaled_ctx(1e-3), True)
    diff_std = float(np.max(np.abs(sa[ok] - sb[ok])))
    assert diff_std < 1e-9, diff_std
    assert diff_unscaled > 1e-4, "unscaled H1 was unit-free here (%g); ISSUE 4 would not apply" % diff_unscaled
    # the NDVI lag-1 AR coefficient is the term the shared prior shrinks: it moves with the precipitation unit
    lag1 = lambda p: np.mean([p["units"][u]["coef"][0] for u in ("u0", "u1", "u2")])   # noqa: E731
    assert abs(lag1(pa) - lag1(pb)) > 1e-3, (lag1(pa), lag1(pb))


def test_r04_h1_scale_choice_moves_inner_mae():
    """Printed evidence for the owner decision (not a verdict): inner MAE of the two settings on the toy ARDL, and
    of the unscaled fit with precipitation stored in metres. Both settings are fitted on tune rows only."""
    ctx = _rescaled_ctx(1.0)
    pre_u, _ = _fit_predict(ctx, False)
    pre_s, _ = _fit_predict(ctx, True)
    ctx_m = _rescaled_ctx(1e-3)
    pre_m, _ = _fit_predict(ctx_m, False)
    maes = {"unscaled_mm": _inner_mae(ctx, pre_u), "standardized": _inner_mae(ctx, pre_s),
            "unscaled_metres": _inner_mae(ctx_m, pre_m)}
    print("H1 inner MAE on the toy ARDL: %s" % maes)
    assert all(np.isfinite(v) for v in maes.values())
    assert maes["unscaled_mm"] != maes["unscaled_metres"]


def test_r04_h1_predict_is_row_wise_and_label_free():
    """Change one inner row's climate values and its label: only that row's prediction moves (no transductive use of
    the score set), and no label is asked for."""
    ctx, _ = TC.ndvi_ctx()
    p = BD.fit(ctx, TC.H1_RIVAL, 0, "tune")
    base = BD.predict(ctx, TC.H1_RIVAL, 0, p, "inner")["pre"].to_numpy(np.float64)
    k, y, z, h, e = ctx.sets["inner"]
    row = int(np.flatnonzero((k["unit"] == "u0").to_numpy())[5])
    e2 = e.copy()
    e2.loc[row, PRECIP[0]] = e2.loc[row, PRECIP[0]] + 500.0
    y2 = y.copy()
    y2[:] = 99.0                                        # poisoned labels of the score set: must not matter
    ctx.sets["inner"] = (k, y2, z, h, e2)
    calls = list(ctx.label_calls)
    moved = BD.predict(ctx, TC.H1_RIVAL, 0, p, "inner")["pre"].to_numpy(np.float64)
    assert ctx.label_calls == calls
    d = np.abs(np.nan_to_num(moved) - np.nan_to_num(base)) > 0
    assert d[row] and d.sum() == 1, np.flatnonzero(d)[:5]


def test_r04_h1_climate_means_come_from_the_fit_set_only():
    """The unit x month climate means saved in the params equal the fit (tune) rows' means; shifting every inner
    climate value by a constant shifts no mean (the score set never feeds them)."""
    ctx, _ = TC.ndvi_ctx()
    p = BD.fit(ctx, TC.H1_RIVAL, 0, "tune")
    k, y, z, h, e = ctx.sets["tune"]
    m = pd.DataFrame({"u": k["unit"].astype(str), "k": BD.season_key(k["issue"].to_numpy(), 12),
                      "v": e[PRECIP[0]].to_numpy()})
    m = m[m["u"].isin(["u0", "u1", "u2", "u3"])].groupby(["u", "k"])["v"].mean()
    for (u, kk), v in m.items():
        assert abs(p["climate_means"]["precip"]["%s|%d" % (u, kk)] - v) < 1e-12
