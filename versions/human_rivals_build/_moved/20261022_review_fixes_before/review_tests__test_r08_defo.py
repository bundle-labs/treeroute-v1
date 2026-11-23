"""R08: defo VT0007 - loss only before the issue year, the staged prep, and the coverage rule.

Loss before the issue year: every issue year t counts HRP loss years t-10 .. t-1 and the distance map at the end of
t-1 (defo_prep.py:401-412, defo_vt0007.py:301-307); lossyear values above the stage's ymax are zeroed before any
read (defo_prep.py:191-197). Stage train reads loss <= the fit cut only (defo_prep.py:581-586).
ISSUE 8 (low): the registry coverage rule {issue_min: 2010} (registry/defo.yaml:40) is written for lead 1
(issue = t - 1) and its comment claims lead 0 too; at lead 0 (issue = t) it marks t = 2010 covered while the adapter
writes NaN there (t_min = 2011, defo_vt0007.py:268, :312-313). Harmless today (only test rows 2020-2023 are masked,
board.py:730-747) but the rule is not the adapter's coverage at every lead.
"""
import numpy as np
import pandas as pd
import pytest

from adapters import defo_prep as DP
from rivals_human import board as B
from review_tests.conftest import rival_of


def test_r08_lossyear_guard_zeroes_every_later_year():
    ly = np.arange(0, 26, dtype=np.uint8)                     # 2000 + v; 0 = never lost
    out = DP.lossyear_guard(ly, 2018)
    assert out.max() == 18 and (out[19:] == 0).all() and (out[:19] == ly[:19]).all()


@pytest.mark.parametrize("t", [2011, 2016, 2019, 2020, 2023])
def test_r08_stage_plan_reads_only_loss_before_the_issue_year(t):
    plan = DP.stage_plan([t], 10, t - 1)
    assert sorted(plan) == [t - 11, t - 1]
    assert plan[t - 11] == list(range(t - 10, t)) and max(plan[t - 11]) == t - 1
    assert plan[t - 1] == []                                 # the distance map at end t-1 needs forest counts only
    with pytest.raises(Exception, match="past this stage's ymax"):
        DP.stage_plan([t], 10, t - 2)                        # one year short: refuses instead of reading ahead


def test_r08_stage_train_issue_years_need_no_test_window_loss():
    """Stage train (before the lock) plans issue years 2011..2019 (+ the frozen form's 2020) and reads loss <= 2019
    = the fit cut (labels <= 2019 are train labels; R11 fit cut 2019)."""
    r = rival_of("defo", "vt0007_shipped")
    years = DP.issue_years(r, "train", 2019, None)
    assert years[0] == 2011 and years[-1] == 2020
    plan = DP.stage_plan(years, 10, 2019)
    assert max(max(v) if v else T for T, v in plan.items()) <= 2019


def _cov(rule, lead, years):
    t = np.asarray(years)
    keys = pd.DataFrame({"unit": "c1", "group": "g", "time": t, "issue": t - lead, "lead": lead})
    units = pd.DataFrame({"unit": ["c1"], "is_scored": [True]})
    return B.coverage_rule_mask(rule, keys, units, "review")


def test_r08_coverage_rule_covers_every_test_row():
    for rid in ("vt0007_shipped", "vt0007_cal", "vt0007_frozen2019"):
        rule = rival_of("defo", rid)["coverage"]
        for lead in (0, 1):
            assert _cov(rule, lead, range(2020, 2024)).all()


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="ISSUE 8: coverage {issue_min: 2010} marks issue year 2010 covered at lead 0, where the "
                          "adapter writes NaN (t_min 2011)")
def test_r08_coverage_rule_equals_adapter_coverage_at_every_lead():
    rule = rival_of("defo", "vt0007_shipped")["coverage"]
    opts = rival_of("defo", "vt0007_shipped")["options"]
    t_min = int(opts["first_loss_year"]) + int(opts["hrp_years"])
    years = np.arange(2001, 2024)
    for lead in (0, 1):
        np.testing.assert_array_equal(_cov(rule, lead, years), years >= t_min, err_msg="lead %d" % lead)
