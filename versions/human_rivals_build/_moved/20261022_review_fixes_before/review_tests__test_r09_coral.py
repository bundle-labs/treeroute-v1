"""R09: coral NOAA CRW rule (adapters/coral_crw.py) - date-safe at the issue date (d* = issue - 2 on day rows, every
index month before the cut, nothing after d* read) and no label read.

Store parameters copied from the real store build_manifest (read 2026-10-22): sst_gap_days 1, enso lags 3/6/9
reach 2, dmi lags 2/5/8 reach 1.
"""
import datetime as dt

import numpy as np
import pandas as pd
import pytest

from adapters import coral_crw as CR

BM = {"params": {"sst_gap_days": 1, "enso": {"lags": [3, 6, 9], "reach_months": 2, "base": [1951, 1980]},
                 "dmi": {"lags": [2, 5, 8], "reach_months": 1}}}


def _day_rows(lead, n=800):
    g, idx = CR.store_window_params(BM)
    start = dt.date(2013, 1, 1).toordinal()
    target = start + np.arange(n)
    issue = target - lead
    fe = np.array([CR.feature_end_of(int(c), g, idx) for c in issue])
    return target, issue, fe, g, idx


@pytest.mark.parametrize("lead", [0, 183, 365])
def test_r09_dstar_is_issue_minus_two_on_day_rows(lead):
    target, issue, fe, g, idx = _day_rows(lead)
    C, d_star, kinds = CR.derive_dstar(target, issue, fe, lead, g, idx)
    assert kinds["day"] == len(target)
    np.testing.assert_array_equal(d_star, issue - 2)
    assert (fe <= issue - 1).all()                               # every index month ends before the issue day


@pytest.mark.parametrize("lead", [0, 183])
def test_r09_a_store_feature_end_one_day_late_refuses(lead):
    target, issue, fe, g, idx = _day_rows(lead, n=40)
    bad = fe.copy()
    bad[7] += 1
    with pytest.raises(CR.CoralAdapterRefusal):
        CR.derive_dstar(target, issue, bad, lead, g, idx)


def test_r09_heat_stats_never_read_after_dstar():
    """A spike on d*+1 .. d*+30 changes neither DHW nor BAA7d; the same spike on d* does."""
    days = np.arange(15000, 15400, dtype=np.int64)
    sst = np.full(days.size, 29.2, dtype=np.float32)
    d_star = 15300
    base = CR.heat_stats(days, sst, 28.0, d_star)
    late = sst.copy()
    late[(days > d_star) & (days <= d_star + 30)] = 40.0
    assert CR.heat_stats(days, late, 28.0, d_star) == base
    now = sst.copy()
    now[days == d_star] = 40.0
    assert CR.heat_stats(days, now, 28.0, d_star) != base


def test_r09_store_reader_refuses_the_label_column(tmp_path):
    p = tmp_path / "store.parquet"
    pd.DataFrame({"unit_id": ["a"], "pct_bleached": [10.0]}).to_parquet(str(p))
    with pytest.raises(CR.CoralAdapterRefusal, match="label column"):
        CR.read_store(p, "pct_bleached", ["unit_id", "pct_bleached"])
    assert "pct_bleached" not in CR.STORE_KEY_COLUMNS
