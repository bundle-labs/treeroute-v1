"""treeroute.report.metrics: scores (R34), hit tolerance (R32), detection (R33), strata, baselines (R31)
and the private checks behind them. Synthetic data; every branch.

The saved-row tables, the jackknife, the verdict, the band and the writers are in
test_report_metrics_tables.py and test_report_metrics_verdict.py; the Part 558 gate is in
test_report_metrics_gate.py.
"""

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
import pytest

from treeroute import engine_constants as K
from treeroute.derive.shapes import Link, RouterKind
from treeroute.errors import RefusedError
from treeroute.report import metrics as M

INF = float("inf")
LEGAL = (0.0, INF)


def refused(fn, *args, match=None, **kwargs):
    with pytest.raises(RefusedError) as info:
        fn(*args, **kwargs)
    if match:
        assert match in str(info.value), str(info.value)
    return info.value


@dataclass(frozen=True)
class Donor:
    """The approved DonorRows fields the metrics read (y), plus the rest for realism."""
    y: np.ndarray
    unit_ids: Optional[np.ndarray] = None
    times: Optional[np.ndarray] = None


@dataclass(frozen=True)
class History:
    """The approved UnitHistory fields."""
    unit_id: str
    times: np.ndarray
    season_keys: np.ndarray
    y: np.ndarray
    cut: int
    group: str = "g"


# ---------------------------------------------------------------------------------------------------
# private checks
def test_vector_refuses_non_numeric_boolean_and_matrices():
    refused(M._vector, np.array(["a", "b"]), "x", match="numeric")
    refused(M._vector, np.array([True, False]), "x", match="numeric")
    refused(M._vector, np.zeros((2, 2)), "x", match="one-dimensional")
    assert M._vector([1, 2], "x").dtype == np.float64


def test_finite_scalar_branches():
    refused(M._finite_scalar, "1", "x", "R34", match="finite number")
    refused(M._finite_scalar, True, "x", "R34", match="finite number")
    refused(M._finite_scalar, float("nan"), "x", "R34", match="finite number")
    refused(M._finite_scalar, 0.0, "x", "R34", positive=True, match="above 0")
    assert M._finite_scalar(np.float32(2.5), "x", "R34") == 2.5


def test_pair_refuses_shape_empty_and_non_finite_pairs_d67():
    refused(M.mae, [1.0, 2.0], [1.0], match="rows")
    refused(M.mae, [], [], match="no rows")
    refused(M.mae, [1.0, np.nan], [1.0, 2.0], match="D67")
    refused(M.mae, [1.0, 2.0], [np.inf, 2.0], match="D67")


def test_legal_range_is_read_by_the_layers_one_reader():
    refused(M._legal, 5.0, match="(min, max)")
    refused(M._legal, (0.0, 1.0, 2.0), match="(min, max)")
    refused(M._legal, (float("nan"), 1.0), match="min < max")
    refused(M._legal, ("0", 1.0), match="must be a number")
    refused(M._legal, (1.0, 1.0), match="min < max")
    refused(M._legal, (0.0, -INF), match="min < max")
    assert M._legal((0, INF)) == (0.0, INF)
    assert M._legal((-INF, 0.0)) == (-INF, 0.0)


def test_clip_is_the_layers_clip_and_refuses_inf_and_nan_unless_baseline():
    from treeroute.layer.links import clip_to_legal

    refused(M._clip, [1.0, INF], LEGAL, False, match="infinite")
    refused(M._clip, [1.0, -INF], LEGAL, True, match="infinite")
    refused(M._clip, [1.0, np.nan], LEGAL, False, match="missing")
    refused(M._clip, np.ones((2, 2)), LEGAL, False, match="one-dimensional")
    values = np.array([-1.0, np.nan, 3.0, 1.5])
    out = M._clip(values, (0.0, 2.0), True)
    assert out[0] == 0.0 and np.isnan(out[1]) and out[2] == 2.0 and out[3] == 1.5
    assert np.array_equal(out, clip_to_legal(values, (0.0, 2.0), True)[0], equal_nan=True)


def test_value_of_accepts_every_enum_copy_and_strings():
    assert M._value_of(RouterKind.PER_UNIT, M.KIND_VALUES, "kind", "R31") == "per_unit"
    assert M._value_of("region", M.KIND_VALUES, "kind", "R31") == "region"
    refused(M._value_of, "pooled", M.KIND_VALUES, "kind", "R31", match="one of")
    refused(M._value_of, 3, M.KIND_VALUES, "kind", "R31", match="one of")


def test_donor_y_checks():
    refused(M._donor_y, object(), "the donor rows", match="not a DonorRows")
    refused(M._donor_y, Donor(y=np.array([])), "the donor rows", match="no row")
    refused(M._donor_y, Donor(y=np.array([1.0, np.nan])), "the donor rows", match="valid labels only")


def test_history_checks():
    good = History("u", np.array([1, 2]), np.array([1, 2]), np.array([1.0, 2.0]), cut=2)
    assert M._history(good, "h")[0] == "u"
    refused(M._history, object(), "h", match="not a UnitHistory")
    refused(M._history, History("u", np.array([1, 2]), np.array([1]), np.array([1.0, 2.0]), 2), "h",
            match="one per label")
    refused(M._history, History("u", np.array([1, 2]), np.array([1, 2]), np.array([1.0, np.nan]), 2),
            "h", match="valid labels only")
    refused(M._history, History("u", np.array([1, 2]), np.array([1, 2]), np.array([1.0, 2.0]), 2.0),
            "h", match="integer")
    refused(M._history, History("u", np.array([1, 3]), np.array([1, 3]), np.array([1.0, 2.0]), 2), "h",
            match="after its cut")
    refused(M._history, History("u", np.array([1, 1]), np.array([1, 1]), np.array([1.0, 2.0]), 2), "h",
            match="twice")
    refused(M._history, History("u", np.array([1.5, 2]), np.array([1, 2]), np.array([1.0, 2.0]), 2), "h")


def test_guard_tolerance_reads_link_y_through_the_layer_and_inherits_its_refusals():
    y = Donor(y=np.array([0.0, 0.25, 1.0]))
    refused(M.guard_tolerance, y, Link.LOG_C, None, None, 1.0, match="c > 0")
    refused(M.guard_tolerance, y, Link.LOG_C, 0.0, None, 1.0, match="c > 0")
    refused(M.guard_tolerance, Donor(y=np.array([-2.0, 1.0])), Link.LOG_C, 1.0, None, 1.0, match="domain")
    refused(M.guard_tolerance, y, Link.ARCSINE, None, None, 1.0, match="upper bound")
    refused(M.guard_tolerance, Donor(y=np.array([2.0, 0.5])), Link.ARCSINE, None, 1.0, 1.0, match="domain")
    refused(M.guard_tolerance, y, "log_c", 0.5, None, 1.0, match="R22's links")


# ---------------------------------------------------------------------------------------------------
# scores
def test_mae_is_the_plain_mean_absolute_error():
    assert M.mae([1.0, 2.0, 4.0], [2.0, 2.0, 1.0]) == pytest.approx(4.0 / 3.0)


def test_anomaly_r2_against_the_normal():
    rng = np.random.RandomState(0)  # fixed synthetic data, not a varied seed
    y = rng.gamma(2.0, 3.0, 50)
    normal = np.full(50, y.mean()) + rng.normal(0, 0.1, 50)
    p = y * 0.8 + normal * 0.2
    want = 1.0 - np.sum((y - p) ** 2) / np.sum((y - normal) ** 2)
    assert M.anomaly_r2(y, p, normal) == pytest.approx(want, rel=1e-12)
    assert M.anomaly_r2(y, normal, normal) == 0.0          # guess-normal scores 0 by construction
    assert math.isnan(M.anomaly_r2(y[:9], p[:9], normal[:9]))  # D69: under 10 rows
    assert math.isnan(M.anomaly_r2(normal[:12], p[:12], normal[:12]))  # SSE(normal) = 0
    refused(M.anomaly_r2, y, p, normal[:5], match="rows")
    bad = normal.copy()
    bad[3] = np.nan
    refused(M.anomaly_r2, y, p, bad, match="non-finite")


def test_corr2_and_constant_sides():
    y = np.array([1.0, 2.0, 3.0, 5.0])
    p = np.array([1.5, 1.0, 4.0, 4.5])
    assert M.corr2(y, p) == pytest.approx(np.corrcoef(y, p)[0, 1] ** 2, rel=1e-12)
    assert math.isnan(M.corr2(y, np.full(4, 0.1)))
    assert math.isnan(M.corr2(np.full(4, 0.3), p))
    assert math.isnan(M.corr2([1.0], [2.0]))
    assert math.isnan(M.corr2([0.0, 1e-200], [1.0, 2.0]))   # not constant, but its spread underflows to 0


def test_calibration_ratio_and_flag():
    assert M.calibration_ratio([1.0, 3.0], [2.0, 4.0]) == pytest.approx(1.5)
    assert math.isnan(M.calibration_ratio([-1.0, 1.0], [2.0, 4.0]))
    assert not M.calibration_flagged(1.0)
    assert M.calibration_flagged(0.49) and M.calibration_flagged(2.01)
    assert not M.calibration_flagged(0.5) and not M.calibration_flagged(2.0)
    assert not M.calibration_flagged(float("nan"))


def test_preclip_rate_is_the_layers_one_implementation():
    from treeroute.layer.links import clip_with_counts

    values = np.array([-1.0, 0.0, 0.5, 2.0, 1.5])
    assert M.preclip_rate(values, (0.0, 1.0)) == 3 / 5
    assert M.preclip_rate(values, (0.0, 1.0)) == clip_with_counts(values, (0.0, 1.0), False)[1].preclip_rate
    assert M.preclip_rate([0.0, 1.0], (0.0, 1.0)) == 0.0          # the bounds themselves are legal
    refused(M.preclip_rate, [np.nan, 1.0], (0.0, 1.0), match="missing")
    refused(M.preclip_rate, [], (0.0, 1.0), match="no pre-clip")
    refused(M.preclip_rate, [1.0], (1.0, 0.0), match="min < max")
    refused(M.preclip_rate, [0.5, INF], (0.0, 1.0), match="infinite")   # never clipped, never rated


def test_hit_tolerance_is_half_the_mean_absolute_deviation_d71():
    donor = Donor(y=np.array([1.0, 2.0, 5.0, 0.0]))
    ref = np.array([1.0, 1.0, 1.0, 1.0])
    assert M.hit_tolerance(donor, ref) == pytest.approx(K.HIT_TOLERANCE_DEVIATION_SHARE * 6.0 / 4.0)
    refused(M.hit_tolerance, donor, ref[:3], match="values for")
    refused(M.hit_tolerance, donor, np.array([1.0, np.nan, 1.0, 1.0]), match="non-finite")
    refused(M.hit_tolerance, donor, donor.y.copy(), match="is 0")


def test_hit_rate_is_inclusive():
    assert M.hit_rate([1.0, 2.0, 3.0], [1.5, 2.6, 3.0], 0.5) == pytest.approx(2 / 3)
    refused(M.hit_rate, [1.0], [1.0], 0.0, match="above 0")
    refused(M.hit_rate, [1.0], [1.0], float("nan"), match="finite")


def _source_detection(y, p, q=0.90):
    """forecast_report.py:57-77, verbatim logic (tests may cite the source)."""
    t = np.quantile(y, q)
    m = y > t
    if m.sum() < 10 or m.mean() > 0.5:
        return float("nan")
    return float((p[m] > np.quantile(p, q)).mean())


def test_top10_detection_matches_the_strict_source_and_returns_counts():
    rng = np.random.RandomState(1)
    y = rng.gamma(2.0, 2.0, 400)
    p = y + rng.normal(0, 1.0, 400)
    det = M.top10_detection(y, p)
    assert det.score == pytest.approx(_source_detection(y, p))
    assert det.n_events == int((y > np.quantile(y, 0.9)).sum())
    assert det.event_share == pytest.approx(det.n_events / 400)


def test_top10_detection_nan_cases():
    few = M.top10_detection(np.arange(50.0), np.arange(50.0))       # 5 events < 10
    assert math.isnan(few.score) and few.n_events == 5
    yesno = np.r_[np.zeros(80), np.ones(20)]                          # q90 = max: no event
    d = M.top10_detection(yesno, np.linspace(0, 1, 100))
    assert math.isnan(d.score) and d.n_events == 0 and d.event_share == 0.0
    heavy = np.r_[np.zeros(30), np.arange(1.0, 71.0)]                 # strictness: ties at q90 are not events
    d2 = M.top10_detection(heavy, heavy)
    assert d2.n_events == int((heavy > np.quantile(heavy, 0.9)).sum())
    many = np.r_[np.zeros(4), np.ones(96)]                            # q90 = 1: no event
    assert M.top10_detection(many, many).n_events == 0
    tied = np.r_[np.full(95, 0.0), np.arange(1.0, 6.0)]               # q90 on a tie at 0: 5 events
    assert M.top10_detection(tied, tied).n_events == 5
    y = np.r_[np.full(40, 0.0), np.arange(1.0, 61.0)]                 # q90 = 50.1: exactly 10 events
    det = M.top10_detection(y, y)
    assert det.n_events == 10 and det.score == 1.0
    refused(M.top10_detection, [1.0, 2.0], [1.0], match="rows")
    refused(M.top10_detection, [1.0, np.nan], [1.0, 2.0], match="D67")


def test_top10_detection_event_share_above_half_is_nan(monkeypatch):
    # with numpy's linear q90, over half the rows above it needs a planted quantile: patch the share cap
    monkeypatch.setattr(K, "DETECTION_MAX_EVENT_SHARE", 0.05)
    rng = np.random.RandomState(2)
    y = rng.gamma(2.0, 2.0, 200)
    det = M.top10_detection(y, y)
    assert det.event_share > 0.05 and math.isnan(det.score)


def test_stratum_edges_and_right_closed_bins_d73():
    donor = Donor(y=np.zeros(8))
    v = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
    edges = M.stratum_edges(donor, v)
    assert edges == tuple(np.quantile(v, [0.25, 0.5, 0.75]))
    bins = M.stratum_bins(np.array([edges[0], edges[0] + 1e-9, edges[1], edges[2], 100.0, -5.0]), edges)
    assert bins.tolist() == [1, 2, 2, 3, 4, 1]
    refused(M.stratum_edges, donor, v[:3], match="for 8 donor rows")
    refused(M.stratum_edges, donor, np.r_[v[:7], np.nan], match="non-finite")
    refused(M.stratum_edges, donor, np.array([1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 3.0, 3.0]), match="distinct")
    refused(M.stratum_bins, v, (1.0, 2.0), match="three finite")
    refused(M.stratum_bins, v, (3.0, 2.0, 4.0), match="non-decreasing")
    refused(M.stratum_bins, v, ("a", 2.0, 4.0), match="three numbers")
    refused(M.stratum_bins, np.array([1.0, np.nan]), edges, match="non-finite")


# ---------------------------------------------------------------------------------------------------
# baselines (R31)
def test_predict_zero_is_clipped():
    assert M.baseline_predict_zero(3, LEGAL).tolist() == [0.0, 0.0, 0.0]
    assert M.baseline_predict_zero(2, (0.5, 1.0)).tolist() == [0.5, 0.5]   # legal minimum lifts it
    assert M.baseline_predict_zero(0, LEGAL).size == 0
    refused(M.baseline_predict_zero, -1, LEGAL, match="whole number")
    refused(M.baseline_predict_zero, True, LEGAL, match="whole number")
    refused(M.baseline_predict_zero, 2.0, LEGAL, match="whole number")


def test_guess_normal_is_the_clipped_arithmetic_normal():
    assert M.baseline_guess_normal(np.array([-1.0, 2.0]), LEGAL).tolist() == [0.0, 2.0]
    refused(M.baseline_guess_normal, np.array([1.0, np.nan]), LEGAL, match="normal exists")


def _monthly(year, month):
    return year * 12 + month


def test_last5_normal_monthly_window_fallbacks_and_clip():
    # unit rows over 8 years (2010-2017), cut at the end of 2017: the window is 2013-2017
    times, keys, y = [], [], []
    for year in range(2010, 2018):
        for month in (1, 2, 7):
            times.append(_monthly(year, month))
            keys.append(month)
            y.append(float(year - 2000) + (100.0 if year < 2013 else 0.0) + month)
    h = History("u", np.array(times), np.array(keys), np.array(y), cut=_monthly(2017, 12))
    out = M.baseline_last5_normal(h, RouterKind.PER_UNIT, np.array([1, 2, 7, 5]), 2017, LEGAL)
    win = [(t, k, v) for t, k, v in zip(times, keys, y) if 2013 <= (t - 1) // 12 <= 2017]
    jan = np.mean([v for _, k, v in win if k == 1])
    allm = np.mean([v for _, _, v in win])
    assert out[0] == pytest.approx(jan)
    assert out[3] == pytest.approx(allm)          # May: no row in the window -> unit all-season mean
    clipped = M.baseline_last5_normal(h, "region", np.array([1]), 2017, (0.0, 5.0))
    assert clipped.tolist() == [5.0]


def test_last5_normal_unit_without_recent_rows_stays_nan():
    h = History("u", np.array([_monthly(2005, 3)]), np.array([3]), np.array([4.0]), cut=_monthly(2017, 12))
    out = M.baseline_last5_normal(h, RouterKind.PER_UNIT, np.array([3, 4]), 2017, LEGAL)
    assert np.isnan(out).all()


def test_last5_normal_annual_and_event_forms():
    ann = History("u", np.array([2008, 2012, 2013, 2017]), np.array([1, 1, 1, 1]),
                  np.array([10.0, 20.0, 30.0, 40.0]), cut=2017)
    assert M.baseline_last5_normal(ann, RouterKind.REGION, np.array([1]), 2017, LEGAL).tolist() == [35.0]
    import datetime as dt
    days = [dt.date(2011, 3, 5), dt.date(2014, 3, 9), dt.date(2016, 8, 1)]
    ev = History("u", np.array([d.toordinal() for d in days]), np.array([d.month for d in days]),
                 np.array([1.0, 3.0, 5.0]), cut=dt.date(2016, 12, 31).toordinal())
    out = M.baseline_last5_normal(ev, RouterKind.PER_UNIT, np.array([3, 8, 1]), 2016, LEGAL)
    assert out.tolist() == [3.0, 5.0, 4.0]


def test_last5_normal_refusals():
    h = History("u", np.array([_monthly(2016, 1)]), np.array([1]), np.array([1.0]), cut=_monthly(2016, 12))
    refused(M.baseline_last5_normal, h, RouterKind.NEIGHBOUR, np.array([1]), 2016, LEGAL, match="no normal")
    refused(M.baseline_last5_normal, h, "pooled", np.array([1]), 2016, LEGAL, match="one of")
    refused(M.baseline_last5_normal, h, RouterKind.PER_UNIT, np.array([1]), 0, LEGAL, match="positive")
    refused(M.baseline_last5_normal, h, RouterKind.PER_UNIT, np.array([1]), 2015, LEGAL,
            match="not a step of the year")
    bad_keys = History("u", np.array([_monthly(2016, 1)]), np.array([2]), np.array([1.0]),
                       cut=_monthly(2016, 12))
    refused(M.baseline_last5_normal, bad_keys, RouterKind.PER_UNIT, np.array([1]), 2016, LEGAL,
            match="position in its year")
    ann = History("u", np.array([2015, 2016]), np.array([1, 2]), np.array([1.0, 2.0]), cut=2016)
    refused(M.baseline_last5_normal, ann, RouterKind.PER_UNIT, np.array([1]), 2016, LEGAL, match="one)")
    import datetime as dt
    cut_day = dt.date(2016, 12, 31).toordinal()
    ev_bad = History("u", np.array([dt.date(2016, 3, 1).toordinal()]), np.array([4]), np.array([1.0]),
                     cut=cut_day)
    refused(M.baseline_last5_normal, ev_bad, RouterKind.PER_UNIT, np.array([3]), 2016, LEGAL,
            match="month of the event date")
    ev_off = History("u", np.array([0]), np.array([1]), np.array([1.0]), cut=cut_day)
    refused(M.baseline_last5_normal, ev_off, RouterKind.PER_UNIT, np.array([1]), 2016, LEGAL,
            match="not")
    # a tiny calendar year cannot pin the steps per year (10 to 14 fit the cut): refused, never guessed
    tiny = History("u", np.array([30]), np.array([6]), np.array([1.0]), cut=30)
    refused(M.baseline_last5_normal, tiny, RouterKind.PER_UNIT, np.array([6]), 2, LEGAL,
            match="cannot be read off")


def test_persistence_keeps_nan_and_clips():
    out = M.baseline_persistence(np.array([-1.0, np.nan, 3.0]), (0.0, 2.0))
    assert out[0] == 0.0 and np.isnan(out[1]) and out[2] == 2.0
    refused(M.baseline_persistence, np.array([INF]), LEGAL, match="infinite")


def test_shares_season_key_u2():
    assert M.shares_season_key(12, 12) and M.shares_season_key(24, 12)
    assert not M.shares_season_key(3, 12)
    assert M.shares_season_key(1, 1) and M.shares_season_key(3, 1)     # annual: every lead
    refused(M.shares_season_key, 0, 12, match="at or above 1")
    refused(M.shares_season_key, 1, True, match="at or above 1")


def _source_phi(times, keys, y, lead, shared):
    """pm25_forecast.py:503-522 on one unit (tests may cite the source): leave-out means, both pair
    members out of a shared mean when the lead is a multiple of the year, phi through the origin."""
    df = pd.DataFrame({"t": times, "k": keys, "y": y})
    S = df.groupby("k").y.transform("sum")
    C = df.groupby("k").y.transform("count")
    pos = {t: i for i, t in enumerate(times)}
    a, ap = [], []
    for i, t in enumerate(times):
        j = pos.get(t - lead)
        if j is None:
            continue
        yi, yp = y[i], y[j]
        if shared:
            if C[i] <= 2:
                continue
            m = (S[i] - yi - yp) / max(C[i] - 2, 1)
            a.append(yi - m)
            ap.append(yp - m)
        else:
            a.append(yi - (S[i] - yi) / max(C[i] - 1, 1))
            ap.append(yp - (S[j] - yp) / max(C[j] - 1, 1))
    a, ap = np.array(a), np.array(ap)
    den = (ap ** 2).sum()
    return float(np.clip((a * ap).sum() / den, 0.0, 1.0)) if den > 0 else 0.0


def _unit_series(n_years, seed):
    rng = np.random.RandomState(seed)
    times = np.array([_monthly(2000 + i // 12, i % 12 + 1) for i in range(n_years * 12)])
    keys = (times - 1) % 12 + 1
    season = 5.0 + 3.0 * np.sin(keys / 12.0 * 2 * np.pi)
    a = np.zeros(times.size)
    for i in range(1, times.size):
        a[i] = 0.6 * a[i - 1] + rng.normal(0, 1.0)
    return times, keys, season + a


def test_damped_phi_matches_the_source_where_counts_suffice():
    times, keys, y = _unit_series(10, 3)
    cut = int(times.max())
    h = {"u": History("u", times, keys, y, cut)}
    for lead, shared in ((1, False), (3, False), (12, True)):
        got = M.damped_persistence_phi(h, lead, shared)["u"]
        assert got == pytest.approx(_source_phi(times.tolist(), keys.tolist(), y.tolist(), lead, shared),
                                    rel=1e-12, abs=1e-15)
        assert 0.0 <= got <= 1.0


def test_damped_phi_minimum_counts_d88_and_undefined_phi():
    # separate keys: a unit-season with one label cannot give a leave-out mean -> its pairs drop
    h = {"u": History("u", np.array([1, 2]), np.array([1, 2]), np.array([1.0, 2.0]), cut=2)}
    assert M.damped_persistence_phi(h, 1, False) == {"u": 0.0}
    # shared keys: two labels in the shared mean are too few (more than 2 needed)
    h2 = {"u": History("u", np.array([1, 13]), np.array([1, 1]), np.array([1.0, 2.0]), cut=13)}
    assert M.damped_persistence_phi(h2, 12, True) == {"u": 0.0}
    # no pair at all
    h3 = {"u": History("u", np.array([1, 5]), np.array([1, 5]), np.array([1.0, 2.0]), cut=5)}
    assert M.damped_persistence_phi(h3, 1, False) == {"u": 0.0}


def test_damped_phi_is_clipped_to_the_unit_interval():
    # anti-persistent anomalies give a negative slope -> clipped to 0; a steep positive one -> 1
    t = np.arange(1, 9)
    k = np.array([1, 2, 1, 2, 1, 2, 1, 2])
    anti = np.array([0.0, 10.0, 10.0, 0.0, 0.0, 10.0, 10.0, 0.0])
    phi = M.damped_persistence_phi({"u": History("u", t, k, anti, 8)}, 1, False)["u"]
    assert phi == 0.0
    # annual data (one season class, every lead shares it): raw phi 37/35 > 1 -> clipped to 1
    t2 = np.arange(1, 5)
    k2 = np.ones(4, dtype=np.int64)
    y2 = np.array([1.0, 0.0, 1.0, 4.0])
    phi2 = M.damped_persistence_phi({"u": History("u", t2, k2, y2, 4)}, 1, True)["u"]
    assert phi2 == 1.0
    assert _source_phi(t2.tolist(), k2.tolist(), y2.tolist(), 1, True) == 1.0


def test_damped_phi_refusals():
    good = History("u", np.array([1, 2, 3]), np.array([1, 2, 3]), np.array([1.0, 2.0, 3.0]), 3)
    refused(M.damped_persistence_phi, {"u": good}, 0, False, match="at or above 1")
    refused(M.damped_persistence_phi, {"u": good}, 1, "no", match="True or False")
    refused(M.damped_persistence_phi, {}, 1, False, match="at least one")
    refused(M.damped_persistence_phi, {"v": good}, 1, False, match="belongs to unit")
    other_cut = History("w", np.array([1, 2]), np.array([1, 2]), np.array([1.0, 2.0]), 5)
    refused(M.damped_persistence_phi, {"u": good, "w": other_cut}, 1, False, match="different cuts")
    refused(M.damped_persistence_phi, {"u": good}, 1, True, match="contradicts")
    same = History("u", np.array([1, 13]), np.array([1, 1]), np.array([1.0, 2.0]), 13)
    refused(M.damped_persistence_phi, {"u": same}, 12, False, match="contradicts")


def test_damped_persistence_formula_and_refusals():
    out = M.baseline_damped_persistence(np.array([5.0, 5.0, 1.0]), np.array([4.0, 4.0, 1.0]),
                                        np.array([6.0, np.nan, -9.0]), np.array([0.5, 0.5, 1.0]), LEGAL)
    assert out[0] == 6.0 and np.isnan(out[1]) and out[2] == 0.0
    refused(M.baseline_damped_persistence, np.ones(2), np.ones(3), np.ones(3), np.ones(3), LEGAL,
            match="one value per row")
    refused(M.baseline_damped_persistence, np.array([np.nan]), np.ones(1), np.ones(1), np.ones(1), LEGAL,
            match="normals must be finite")
    refused(M.baseline_damped_persistence, np.ones(1), np.ones(1), np.ones(1), np.array([1.5]), LEGAL,
            match="phi must lie")
    refused(M.baseline_damped_persistence, np.ones(1), np.ones(1), np.ones(1), np.array([np.nan]), LEGAL,
            match="phi must lie")


def test_donor_median():
    assert M.baseline_donor_median(Donor(y=np.array([3.0, 1.0, 2.0, 10.0]))) == 2.5
    refused(M.baseline_donor_median, Donor(y=np.array([np.nan, 1.0])), match="valid labels only")
