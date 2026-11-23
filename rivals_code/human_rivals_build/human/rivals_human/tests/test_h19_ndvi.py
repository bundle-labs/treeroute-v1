"""T-H19 NDVI H1 (SPEC_HUMAN.txt section 5; adapters/ndvi_bardl.py): the per-unit BayesianRidge runner recovers a
synthetic ARDL; a unit with < 36 complete fit rows predicts its normal (counted); a missing lag is anomaly 0
(counted); labels come only from ctx.fit_labels on the fit set (never on the score set, never through features);
two runs are byte-identical. Kraft (optional): a 2-unit, 20-step toy fit on CPU with seed 0 is deterministic.

The context here is a small fake with the runner contract of BUILD_NOTES_shared.txt (features, fit_labels, units,
run, t2_step, log); the real AdapterCtx is exercised by the toy flows (toy_m) and checked against every adapter's
calls in test_h20.
"""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from rivals_human.tests import hooks as HK

SPY, OFFSET = 12, 1
HIST = ["hist_last_1", "hist_last_2", "hist_last_3"]
CLIM = {"precip": ["x__V02_total_precip_mm", "x__V02_total_precip_mm_lag1", "x__V02_total_precip_mm_lag2"],
        "soil": ["x__V30_soil_moisture_pct", "x__V30_soil_moisture_pct_lag1", "x__V30_soil_moisture_pct_lag2"]}
RIVAL = {"id": "bardl_h1", "kind": "M", "options": {"history": HIST, "climate": CLIM}}


class FakeCtx(object):
    """Sets 'tune' (fit) and 'inner' (score) of one lead; records every label request."""

    def __init__(self, sets, labels, units):
        self.sets, self.labels, self._units = sets, labels, units
        self.label_calls, self.feature_calls = [], []
        self.run = SimpleNamespace(derived={"R17": {"inputs": {"steps_per_year": SPY},
                                                    "value": {"start_offset_steps": OFFSET}}})
        self.lines = []

    def units(self):
        return self._units

    def features(self, name):
        self.feature_calls.append(name)
        s = self.sets[name]
        return SimpleNamespace(keys=s["keys"], normal={"identity": s["z0"]}, history=s["history"], extras=s["extras"],
                               y=None)

    def fit_labels(self, name):
        self.label_calls.append(name)
        if name not in ("tune", "refit", "guardfit"):
            raise RuntimeError("fit_labels of a score set")
        s = self.sets[name]
        return s["keys"], self.labels[name], {"identity": s["z0"]}

    def t2_step(self, keys):
        t = keys["time"].to_numpy(np.int64)
        return t - 1 - OFFSET

    def log(self, message):
        self.lines.append(message)


def _toy(n_units=3, steps=150, short_unit_rows=30, seed=21):
    """a(t) = 0.6 a(T2 step) + 0.3 precip anomaly(issue) + small noise, per unit; one extra unit has only
    short_unit_rows rows (the < 36 fallback)."""
    rng = np.random.default_rng(seed)
    rows = []
    for u in range(n_units + 1):
        name = "u%d" % u
        n = steps if u < n_units else short_unit_rows
        t0 = 24000
        a = np.zeros(n + 4)
        p = rng.normal(0, 1, size=n + 4)
        for k in range(4, n + 4):
            a[k] = 0.6 * a[k - 2] + 0.3 * p[k - 1] + rng.normal(0, 0.05)  # T2 step = t - 2 (lead 0, offset 1)
        for k in range(4, n + 4):
            t = t0 + k
            rows.append({"unit": name, "group": "g%d" % (u % 3), "time": t, "issue": t, "lead": 0,
                         "z0": 0.3, "a": a[k], "h1": a[k - 2] + 0.3, "h2": a[k - 3] + 0.3, "h3": a[k - 4] + 0.3,
                         "p0": p[k - 1] * 1.0 + 0.0, "p1": p[k - 2], "p2": p[k - 3]})
    f = pd.DataFrame(rows)
    # the precip column read at the issue step must be the anomaly driver: the unit x month mean is ~0 here
    keys = f[["unit", "group", "time", "issue", "lead"]].reset_index(drop=True)
    hist = pd.DataFrame({"x__" + HIST[0]: f["h1"], "x__" + HIST[1]: f["h2"], "x__" + HIST[2]: f["h3"]})
    ext = pd.DataFrame({CLIM["precip"][0]: f["p0"], CLIM["precip"][1]: f["p1"], CLIM["precip"][2]: f["p2"],
                        CLIM["soil"][0]: 0.0, CLIM["soil"][1]: 0.0, CLIM["soil"][2]: 0.0})
    y = (f["z0"] + f["a"]).to_numpy(np.float64)
    z0 = f["z0"].to_numpy(np.float64)
    units = pd.DataFrame({"unit": ["u%d" % u for u in range(n_units + 1)], "group": "g0", "is_scored": True})
    fit_mask = f["time"].to_numpy() < 24000 + 4 + 110
    def take(m):
        return {"keys": keys[m].reset_index(drop=True), "z0": z0[m], "history": hist[m].reset_index(drop=True),
                "extras": ext[m].reset_index(drop=True)}
    sets = {"tune": take(fit_mask), "inner": take(~fit_mask)}
    labels = {"tune": y[fit_mask]}
    return FakeCtx(sets, labels, units), y[~fit_mask], f.loc[~fit_mask, "a"].to_numpy()


def _nd():
    return HK.tool("ndvi_bardl")


def test_h19_recovers_a_synthetic_ardl_and_reads_only_fit_labels():
    ND = _nd()
    ctx, y_score, a_score = _toy()
    params = HK.need(ND, "fit", "C2")(ctx, RIVAL, 0, "tune")
    assert ctx.label_calls == ["tune"]
    out = HK.need(ND, "predict", "C2")(ctx, RIVAL, 0, params, "inner")
    assert ctx.label_calls == ["tune"], "predict asked for labels"
    a_hat = out["pre"].to_numpy() - 0.3
    full = out["unit"].isin(["u0", "u1", "u2"]).to_numpy()
    r2 = 1 - np.sum((a_score[full] - a_hat[full]) ** 2) / np.sum((a_score[full] - a_score[full].mean()) ** 2)
    assert r2 > 0.6, r2
    lag1 = [params["units"]["u%d" % u]["coef"][0] for u in range(3)]
    assert all(0.3 < c < 0.8 for c in lag1), lag1                  # the true AR term is 0.6 (shrunk by the prior)
    assert (out["target_obs_end"].to_numpy() == (out["time"].to_numpy() - 1 - OFFSET)).all()
    assert (out["info_end"].to_numpy() == out["issue"].to_numpy()).all()


def test_h19_fewer_than_36_rows_predict_the_normal_and_are_counted():
    ND = _nd()
    ctx, _, _ = _toy(short_unit_rows=30)
    params = ND.fit(ctx, RIVAL, 0, "tune")
    assert params["units"]["u3"]["fallback"] is True
    assert params["counts"]["units_fallback_normal"] == 1
    out = ND.predict(ctx, RIVAL, 0, params, "inner")
    short = out["unit"] == "u3"
    if short.any():
        assert np.allclose(out.loc[short, "pre"].to_numpy(), 0.3)


def test_h19_a_missing_lag_is_anomaly_0_and_counted():
    ND = _nd()
    ctx, _, _ = _toy()
    s = ctx.sets["inner"]
    s["history"].loc[0, "x__hist_last_2"] = np.nan
    params = ND.fit(ctx, RIVAL, 0, "tune")
    X, ok, counts = HK.need(ND, "design", "C2")(s["keys"], s["z0"], s["history"], s["extras"],
                                                params["climate_means"], ND._options(RIVAL), 0, SPY, OFFSET)
    assert counts["ndvi_lag_values_missing_set_to_0"] == 1
    assert X[0, 1] == 0.0


def test_h19_deterministic_twice():
    ND = _nd()
    ctx1, _, _ = _toy()
    ctx2, _, _ = _toy()
    p1, p2 = ND.fit(ctx1, RIVAL, 0, "tune"), ND.fit(ctx2, RIVAL, 0, "tune")
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)
    o1, o2 = ND.predict(ctx1, RIVAL, 0, p1, "inner"), ND.predict(ctx2, RIVAL, 0, p2, "inner")
    assert o1["pre"].to_numpy().tobytes() == o2["pre"].to_numpy().tobytes()


@pytest.mark.slow_ok
def test_kraft_toy_fit_is_deterministic_on_cpu():
    """Kraft LSTM (optional, Q10): the adapter's own network on a 2-unit, 20-step toy, built and trained twice for a
    few steps with seed 0 on CPU (the adapter's _torch_setup: 8 threads, deterministic algorithms), gives equal
    predictions byte for byte."""
    KR = HK.tool("ndvi_kraft")
    opt = {"seed": 0, "threads": 8, "hidden": 8, "head": 4, "drivers": ["a", "b"], "statics": ["s"]}
    net_fn = HK.need(KR, "_net", "C3")
    setup = HK.need(KR, "_torch_setup", "C3")
    w = np.linspace(0, 1, 2 * 20 * 2, dtype=np.float32).reshape(2, 20, 2)
    st = np.array([[0.5], [1.5]], dtype=np.float32)
    target = np.array([0.2, 0.7], dtype=np.float32)

    def once():
        torch = setup(opt)
        net = net_fn(opt)
        sgd = torch.optim.SGD(net.parameters(), lr=0.05)
        W, S, T = torch.tensor(w), torch.tensor(st), torch.tensor(target)
        for _ in range(5):
            sgd.zero_grad()
            loss = ((net(W, S) - T) ** 2).mean()
            loss.backward()
            sgd.step()
        with torch.no_grad():
            return net(W, S).numpy().copy()
    a, b = once(), once()
    assert a.tobytes() == b.tobytes()
