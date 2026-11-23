"""R06 (ISSUE 6): a lead listed in `score_without_net` loses its row when the GUARD fit is not calibratable.

Ruling Q12 b: coral Outlook at 365 d is scored WITHOUT the safety net because its guard-fit rows are too few
(38 rows / 11 groups, research_coral.md:136-138). But board._refit_one fits the guard map first and, on
NotCalibratable, marks the whole lead "not_calibratable" and returns (board.py:878-883, :893, :934-938): no refit,
no test row, although the refit rows (targets 2011-11-14 .. 2015-01-01) may well be enough. The table toy never
exercises this (its I rival is below the floor everywhere and its Outlook is an M runner, toy_products.py:540-547).

Here: the grid toy's index rival toy_idx with score_without_net [12], and the guard fit at lead 12 forced to be
NotCalibratable (a wrapper around board.fit_candidate that raises on that one call, the refit call untouched).
"""
import pytest

from rivals_human import board as B
from rivals_human import config as C
from rivals_human import maps as MP
from rivals_human.tests import hooks as HK
from rivals_human.tests import toy_products as TP

pytestmark = pytest.mark.flow


@pytest.fixture(scope="module")
def no_net_board(grid_human, grid_slim):
    reg = TP.grid_registry(grid_human.package)
    idx = dict(next(r for r in reg["rivals"] if r["id"] == "toy_idx"))
    idx["score_without_net"] = [12]
    v = HK.variant_config(grid_human, "rv_nonet", dict(reg, rivals=[idx]), index_name="_index_rv_nonet")
    HK.adapt(v, "toy_idx", "all", None)
    out = HK.run_tune_lock(v)
    return v, out


def _refit_with_guard_forced_uncalibratable(v, out, lead, monkeypatch):
    real = B.fit_candidate
    seen = {"calls": 0}

    def wrapper(cand, sd, run, L, l1=False):
        if int(L) == int(lead) and not l1:
            seen["calls"] += 1
            if seen["calls"] == 1:                     # the guard fit (board.py:879) comes before the refit (:888)
                raise MP.NotCalibratable("forced in review: 38 guard-fit rows in 11 groups")
        return real(cand, sd, run, L, l1)
    monkeypatch.setattr(B, "fit_candidate", wrapper)
    HK.refit(v, out, lead, True)
    return HK.read_json(out / (C.LEAD_DIR % lead) / (C.DONE_FILE % "toy_idx")), seen


def test_r06_setup_lead12_is_a_no_net_lead(no_net_board):
    v, out = no_net_board
    p = HK.picks(out)["picks"]["toy_idx"]
    assert p["status"] == "ok" and p["leads"]["12"]["score_without_net"] is True
    assert p["leads"]["12"]["tier"] == "L"


# FIXED 2026-10-22 (was xfail strict): "ISSUE 6: a score_without_net lead whose guard fit is not calibratable gets NO row "
#   "(ruling Q12 b wants it scored raw, flagged 'no safety net')"
def test_r06_no_net_lead_is_scored_raw_when_the_guard_cannot_fit(no_net_board, monkeypatch):
    v, out = no_net_board
    done, seen = _refit_with_guard_forced_uncalibratable(v, out, 12, monkeypatch)
    assert seen["calls"] >= 1
    assert done["status"] == "ok", "lead 12 (score_without_net) ended %s: %s" % (done["status"], done.get("info"))
