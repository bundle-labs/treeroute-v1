"""T-F14 the runner contract through the tool (SPEC_HUMAN_PARTB.txt 1.3, 4; methods.py:40-91): methods.run_fit and
methods.run_predict on the stand-in ctx (the fit inside the label scope methods.run_fit opens for the real ctx), for
both runners, every form, leads 6 and 12, guard and test sets: one row per key in the set's order, the RUNNER_COLUMNS,
no +-inf, every pre finite (coverage all_rows), rows whose normal is 0 predict exactly 0 (a normal a float
residue below 0 predicts <= 0, i.e. 0 after the tool's clip), info_end int64.
"""

import numpy as np
import pytest

from tests_fire import fixtures_fire as FF


def _y(f, gen):
    N = f["N"].to_numpy()
    s = f[gen].to_numpy(np.float64)
    ok = np.isfinite(s) & (np.abs(s) <= 3.5)
    b = f["group"].map({"g1": 0.2, "g2": -0.1, "g3": 0.05}).to_numpy(np.float64)
    return np.where(ok, N * (1.0 + b * np.where(ok, s, 0.0)), N)


CASES = [("enso", "E1"), ("enso", "E2"), ("enso", "E3"), ("turco", "T1"), ("turco", "T2"), ("turco", "T3")]


@pytest.mark.parametrize("which,form", CASES)
@pytest.mark.parametrize("lead", [6, 12])
def test_f14_run_fit_and_run_predict(tmp_path, runners, which, form, lead):
    from rivals_human import config as C
    from rivals_human import methods as ME
    runner = runners[0] if which == "enso" else runners[1]
    f = FF.runner_frame(lead)
    iss = sorted(set(f["issue"]))
    f.loc[f["issue"].isin(iss[50::90]), "x__oni"] = np.nan             # missing predictors on some rows
    f.loc[f.index[3::157], "x__spi_03m"] = 99.0
    zero = f.index[f["N"].to_numpy() == 0.0]
    f.loc[zero[5::40], "N"] = -1e-17                                   # a float residue below 0: still no fire
    if which == "enso":
        rival, extras, y = FF.enso_rival(form), ["x__oni"], _y(f, "x__oni")
    else:
        rival, extras, y = FF.turco_rival(form), FF.SPI_COLS, _y(f, "x__spi_03m")
    sets = FF.runner_sets(f, y, extras)
    ctx = FF.runner_ctx(tmp_path, rival, lead, sets)
    tier = "P" if lead == 6 else "X"
    for fit_set, score_set in (("guardfit", "guard"), ("refit", "test")):
        with ctx._fitting(fit_set):
            params = ME.run_fit(runner, ctx, rival, lead, fit_set)
        keys = ctx.keys(score_set)
        frame, rec = ME.run_predict(runner, ctx, rival, lead, params, score_set, keys, tier)
        assert list(frame.columns) == list(C.RUNNER_COLUMNS)
        assert len(frame) == len(keys) and rec["rows"] == len(keys)
        for k in ("unit", "time", "issue"):
            np.testing.assert_array_equal(frame[k].astype(str).to_numpy(), keys[k].astype(str).to_numpy())
        pre = frame["pre"].to_numpy(np.float64)
        assert not np.isinf(pre).any()
        assert np.isfinite(pre).all(), "coverage all_rows: every score row gets a finite pre"
        assert rec["predicted"] == len(keys)
        N = sets[score_set]["normal"]["identity"]
        assert (N == 0).any() and (N < 0).any()
        assert (pre[N == 0] == 0.0).all()                              # a zero normal predicts exactly 0
        assert (pre[N < 0] <= 0.0).all()                               # below 0: 0 after the tool's clip
        assert frame["info_end"].dtype == np.int64
