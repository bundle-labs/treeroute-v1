"""C9, the guard tolerance constant k (R36, U-4; tests may name problems).

APP_PLAN.md R36 / 3.1 C9 / U-4: "k is set so PM2.5's identity gate stays 1e-6, and checked to be at least 10x the
measured arithmetic error". R36's tolerance of one link is k x s, s = the donor-row standard deviation of link(y) at
the cut (report.metrics.guard_tolerance; pipeline.stages.guard_tolerances). While k is UNSET a smoke uses the
stand-in k = C9.identity_gate / s(identity) per cut and a headline run refuses.

MEASURED 2026-10-06 by agent C1 (scratch D:/treeroute/c1_20261006/k_measure.py, read-only): the engine's own census
and streamed derive of datasets/pm25 at full size (127 groups x 100 bank units, labels before Y0 2003 withheld), stopped
where R30 asks for the column reader; its donor argument is the fit-cut lead-0 donor rows (the row-key hash equals
R23:lead=0's, which passes.py checks against its own FitContext.donor_rows('bank')). s computed with
report.metrics.guard_tolerance(k = 1) on those rows and on the lead-6 / lead-12 fit-cut subsets (row counts and
row-key hashes equal R23:lead=6 / lead=12).

DECISION (C1, not the owner's): k is NOT set. One k cannot hold PM2.5's identity gate at 1e-6 at every cut the engine
gates: the nowcast fit cut, the lead-6 and the lead-12 fit cuts have different donor rows, so different s; a k that
gives exactly 1e-6 at the nowcast gives the PM2.5_LEAD_GATES below at the two leads (the stand-in gives 1e-6 at all
three today), and it also changes every smoke's tolerance. The task's rule was "if k cannot be set without changing
a PM2.5 gate, do not set it". These tests pin the candidate for the owner and guard the constant: it stays UNSET, or
it is exactly the candidate (then the nowcast gate is exactly 1e-6 through the engine's own function).
"""

import math
from types import SimpleNamespace as NS

import pytest

from treeroute import engine_constants as K

# PM2.5 full-size fit-cut donor rows, identity link (np.std, ddof 0), lead 0 = the first shipped nowcast's fit cut
# (cut step 24240, 2,590,280 rows of 12,700 bank units, y float64, row-key hash 70f0ed7d..., = R23:lead=0's donor):
# 19.11763956287126 ug m-3 (log_c link, c = 1.5: 0.7755617561410368)
S_PM25_NOWCAST = float.fromhex("0x1.31e1da05b3f70p+4")
# the same at the lead-6 and lead-12 fit cuts (subsets of the same rows, times at or before each cut): cut 24235,
# 2,526,780 rows, 19.11575100807622; cut 24229, 2,450,597 rows, 19.140650318701773 (row counts and hashes = R23's)
S_PM25_LEADS = {6: float.fromhex("0x1.31da1dbaa2a99p+4"), 12: float.fromhex("0x1.32401a8c6ff00p+4")}
# the candidate: the float whose product with S_PM25_NOWCAST is exactly C9.identity_gate (1e-6): 5.230771281733543e-08;
# it gives 9.999012140181412e-07 at lead 6 and 1.0012036400076922e-06 at lead 12 (both above 10 x 9e-8)
K_CANDIDATE = float.fromhex("0x1.c151e07e7cf79p-25")
PM25_LEAD_GATES = {6: K_CANDIDATE * S_PM25_LEADS[6], 12: K_CANDIDATE * S_PM25_LEADS[12]}


def test_the_candidate_keeps_the_pm25_nowcast_identity_gate_exactly():
    assert K_CANDIDATE * S_PM25_NOWCAST == K.IDENTITY_GATE == 1e-6


def test_the_candidate_is_at_least_10x_the_measured_arithmetic_error():
    # the measured error (C9.measured_arith_error, 9e-8) is in PM2.5's y units: in R36's relative units it is
    # 9e-8 / s, so k >= 10 x 9e-8 / s, i.e. the identity tolerance k x s >= 9e-7, at every cut
    floor = K.K_MIN_MULTIPLE_OF_ARITH_ERROR * K.MEASURED_ARITH_ERROR
    assert K_CANDIDATE * S_PM25_NOWCAST >= floor
    assert K_CANDIDATE >= K.K_MIN_MULTIPLE_OF_ARITH_ERROR * K.MEASURED_ARITH_ERROR / S_PM25_NOWCAST
    for lead, gate in PM25_LEAD_GATES.items():
        assert gate >= floor, lead


def test_one_k_changes_the_pm25_lead_gates_so_k_stays_unset():
    """The reason k is not set: the lead gates move off 1e-6 (the stand-in keeps them there)."""
    for lead, gate in PM25_LEAD_GATES.items():
        assert gate != K.IDENTITY_GATE and math.isclose(gate, K.IDENTITY_GATE, rel_tol=0.1), (lead, gate)


def test_k_is_unset_or_exactly_the_measured_candidate():
    if K.GUARD_TOLERANCE_K is K.UNSET:
        with pytest.raises(Exception):
            K.get("C9.guard_tolerance_k")
        return
    assert float(K.get("C9.guard_tolerance_k")) == K_CANDIDATE


def test_the_engine_gives_exactly_1e6_at_the_measured_s_when_k_is_the_candidate(monkeypatch):
    """pipeline.stages.guard_tolerances (headline path, smoke False) with k = the candidate, on donor rows whose ddof-0
    standard deviation is exactly S_PM25_NOWCAST (two labels 0 and 2s: mean s, deviations +-s)."""
    from treeroute.derive.shapes import Link
    from treeroute.pipeline import stages as ST

    original = K.get
    monkeypatch.setattr(K, "GUARD_TOLERANCE_K", K_CANDIDATE)
    monkeypatch.setattr(K, "get", lambda cid: K_CANDIDATE if cid == "C9.guard_tolerance_k" else original(cid))
    donor = NS(y=[0.0, 2.0 * S_PM25_NOWCAST])
    tol, record = ST.guard_tolerances(donor, [Link.IDENTITY], None, None, smoke=False)
    assert record["s"]["identity"] == S_PM25_NOWCAST and record["standin"] is False
    assert tol[Link.IDENTITY] == K.IDENTITY_GATE
