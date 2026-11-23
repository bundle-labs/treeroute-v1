"""The streaming target census (treeroute.derive.census): derive_all_streamed gives derived.json
byte-identical to derive_all on the same table, however the table is cut into files; the label rows it
reads again are the picked units' only (a planted label in an unpicked unit cannot reach them); the
streamed hashes, the percentile replica and the exact radix select (with forced refinement passes)
match numpy and derive's own helpers; labels that are mostly zero, with both signs of zero, give numpy's
event count; a read from a calendar coordinate on returns exactly the rows from there, in file order,
with every label dropped, and skips the files that end before it.

The package and the synthetic reader are test_derive_all's (conftest.make_package); group names are
generic.
"""

import numpy as np
import pytest

from test_derive_all import Reader, package, target_table
from treeroute import derive as D
from treeroute.derive import census as C
from treeroute.derive.derived import sha256_of_array
from treeroute.runs.atomic import dumps_canonical


def _doc(out):
    return dumps_canonical(D.derived_document(out))


def _streamed(pkg, target, reader, rows_per_file, withhold=None):
    census = C.scan_target(C.TableSource(target, rows_per_file), {"step_year": "year", "step_month": "month"},
                           C.ReaderPresence(reader))
    return census, C.derive_all_streamed(pkg, census, reader, withhold_before_step=withhold)


def _big_target(n_big=130):
    """test_derive_all's table with one group holding more candidates than its bank count (100): the
    picked units are then a strict subset of the units."""
    import test_derive_all as T

    saved = dict(T.UNITS)
    try:
        T.UNITS["g_c"] = n_big
        return T.target_table()
    finally:
        T.UNITS.clear()
        T.UNITS.update(saved)


@pytest.fixture(scope="module")
def pkg(tmp_path_factory):
    return package(tmp_path_factory.mktemp("census"))


@pytest.mark.parametrize("rows_per_file", [997, 12 * 13 * 7])
def test_streamed_derive_is_byte_identical_to_derive_all(pkg, rows_per_file):
    target = target_table()
    expected = D.derive_all(pkg, target, Reader())
    census, got = _streamed(pkg, target, Reader(), rows_per_file)
    assert list(got) == list(expected)
    assert _doc(got) == _doc(expected)
    assert census.rows == len(target.unit_ids)


def test_identical_when_the_picked_units_are_a_subset(pkg):
    target = _big_target()
    expected = D.derive_all(pkg, target, Reader())
    census, got = _streamed(pkg, target, Reader(), 5000)
    assert _doc(got) == _doc(expected)
    lists = got["R18:units"].value
    assert len(lists.bank["g_c"]) == 100 < 130
    picked = census._picked[0]                       # the only label rows read again: the bank units'
    assert set(picked) == {u for g in lists.bank for u in lists.bank[g]}
    assert not any(u.startswith("g_z") for u in picked)


def test_identical_with_the_labels_before_y0_withheld(pkg):
    target = target_table()
    years = np.asarray(target.time_columns["step_year"])
    y0 = 2001
    withheld = target.__class__(**vars(target))
    withheld.y = np.where(years < y0, np.nan, target.y)
    expected = D.derive_all(pkg, withheld, Reader())
    census, _ = _streamed(pkg, target, Reader(), 3000)
    first = (y0 * 12 + 0)                            # month steps: the census's view computes the real one
    cadence = D.derive_all(pkg, target, Reader())["R1"].value
    from treeroute import timing
    first = int(timing.year_last_step(y0 - 1, cadence)) + 1
    got = C.derive_all_streamed(pkg, census, Reader(), withhold_before_step=first)
    assert _doc(got) == _doc(expected)
    rows, valid = C.withheld_counts(census, cadence, D.orchestrate._Facts(pkg).target, first)
    before = years < y0
    assert rows == int(before.sum()) and valid == int(np.isfinite(target.y[before]).sum())


def test_a_planted_label_in_an_unpicked_unit_never_reaches_the_picked_rows(pkg):
    target = _big_target()
    units = np.asarray(target.unit_ids)
    years = np.asarray(target.time_columns["step_year"])
    planted = 987.654
    clean = D.derive_all(pkg, target, Reader())
    bank = {u for g, v in clean["R18:units"].value.bank.items() for u in v}
    victim = sorted(set(units[(target.group_ids == "g_c")]) - bank)[0]
    y = target.y.copy()
    y[(units == victim) & (years == 2010)] = planted        # after the train end (2007)
    target.y = y
    census, got = _streamed(pkg, target, Reader(), 4000)
    assert _doc(got) == _doc(D.derive_all(pkg, target, Reader()))
    rows = census.read_units(census._picked[0])
    assert victim not in set(rows.unit_ids.tolist()) and not np.any(rows.y == planted)


def test_streamed_hashes_equal_sha256_of_array():
    rng = np.random.default_rng(3)
    text = np.array(["u%dé" % i for i in rng.integers(0, 50, 1000)], dtype=object)
    ints = rng.integers(-10 ** 9, 10 ** 9, 1000).astype(np.int64)
    for kind, arr in (("text", text), ("int64", ints)):
        h = C._ArrayHash(len(arr), kind)
        for a in range(0, len(arr), 137):
            h.update(arr[a:a + 137])
        assert h.hexdigest() == sha256_of_array(arr)
    empty = C._ArrayHash(0, "text")
    assert empty.hexdigest() == sha256_of_array(np.zeros(0, dtype=object))


@pytest.mark.parametrize("n", [1, 2, 3, 10, 11, 1001, 4096])
def test_the_percentile_replica_matches_numpy(n):
    rng = np.random.default_rng(n)
    for values in (rng.normal(size=n), rng.integers(0, 4, n).astype(np.float64), np.round(rng.random(n), 2)):
        s = np.sort(values)
        kp, kn = C.percentile_ranks(n, 90.00000000000001)
        assert C._linear_percentile(s[kp], s[kn], n, 90.00000000000001) == float(np.percentile(values, 90.00000000000001))
        kp, kn = C.percentile_ranks(n, 90.0)
        assert C._linear_percentile(s[kp], s[kn], n, 90.0) == float(np.percentile(values, 90.0))


def test_sortable_keys_order_the_values():
    v = np.array([-np.inf, -3.5, -1e-300, -0.0, 0.0, 1e-300, 2.0, 7.25, np.inf])
    k = C.sortable_keys(v)
    assert (np.diff(k.astype(object)) > 0).all()


def test_the_radix_select_refines_and_stays_exact(pkg, monkeypatch):
    target = _big_target()
    expected = D.derive_all(pkg, target, Reader())
    monkeypatch.setattr(C, "COLLECT_CAP", 7)          # every bin is 'too large': refinement passes run
    _, got = _streamed(pkg, target, Reader(), 2500)
    assert _doc(got) == _doc(expected)
    assert got["R18"].inputs == expected["R18"].inputs


def test_a_repeated_unit_time_is_refused_across_files(pkg):
    target = target_table()
    for name in ("unit_ids", "group_ids", "y"):
        setattr(target, name, np.concatenate([getattr(target, name), getattr(target, name)[:3]]))
    target.time_columns = {c: np.concatenate([v, v[:3]]) for c, v in target.time_columns.items()}
    with pytest.raises(D.DeriveRefusal, match="repeat a \\(unit, time\\)"):
        _streamed(pkg, target, Reader(), 1000)


def test_a_day_calendar_is_refused_by_the_streamed_census():
    class T(object):
        unit_ids = np.array(["a", "a"], dtype=object)
        group_ids = np.array(["g", "g"], dtype=object)
        time_columns = {"d": np.array([730000, 730016])}
        y = np.array([1.0, 2.0])
    with pytest.raises(D.DeriveRefusal, match="day time line"):
        C.scan_target(C.TableSource(T, 10), {"d": "date"}, None)


def test_the_census_ram_estimate_counts_the_bits_and_one_file():
    small = C.census_ram_bytes(1000, 288, 10_000, 100_000, 2)
    big = C.census_ram_bytes(2_000_000, 288, 330_000, 7_100_000, 2)
    assert big > small > 10_000 * 120
    assert big < 3 * (1 << 30)              # a 2 M-unit monthly census stays within a few GB


def test_identical_across_many_unit_blocks(pkg, monkeypatch):
    target = _big_target()
    expected = D.derive_all(pkg, target, Reader())
    monkeypatch.setattr(C, "UNIT_BLOCK", 16)          # every bit read crosses many unit blocks
    _, got = _streamed(pkg, target, Reader(), 3333)
    assert _doc(got) == _doc(expected)


@pytest.mark.parametrize("share_neg, share_pos, share_val", [(0.91, 0.03, 0.06), (0.45, 0.47, 0.08),
                                                             (0.03, 0.91, 0.06), (0.95, 0.0, 0.05),
                                                             (0.0, 0.94, 0.06)])
def test_mixed_signed_zero_labels_count_events_as_numpy(pkg, share_neg, share_pos, share_val):
    """Mostly-zero labels (the 90th percentile is a zero): the event count, the rows and the R18 lists
    equal derive_all's (numpy's); with zeros of one sign derived.json is byte-identical (q90's sign
    included); with both signs q90 is zero (its sign is the residual of event_rate's docstring). Before
    zeros were keyed as +0.0, a 90th percentile in the -0.0 bin missed the +0.0 bin's labels."""
    target = target_table()
    rng = np.random.default_rng(int(share_neg * 100) + int(share_pos * 10))
    u = rng.random(len(target.y))
    y = np.where(u < share_neg, -0.0, np.where(u < share_neg + share_pos, 0.0, 0.5 + rng.random(len(u))))
    target.y = np.where(np.isfinite(target.y), y, np.nan)
    expected = D.derive_all(pkg, target, Reader())
    _, got = _streamed(pkg, target, Reader(), 1777)
    e, g = expected["R18"].inputs["event_rate"], got["R18"].inputs["event_rate"]
    assert (g["events"], g["rows"], g["rate"]) == (e["events"], e["rows"], e["rate"])
    assert g["q90"] == 0.0 == e["q90"]
    assert got["R18"].value == expected["R18"].value
    if not (share_neg and share_pos):
        assert _doc(got) == _doc(expected)


def test_the_event_rate_matches_numpy_on_random_labels_with_signed_zeros():
    """census.event_rate against np.percentile and its strict count on 3000 small random label sets drawn
    from a few values with both signs of zero: the event count and q90's value always; q90's sign whenever
    the zeros hold one sign."""
    from types import SimpleNamespace

    from treeroute import engine_constants as K

    pct = float(K.EVENT_QUANTILE) * 100.0
    rng = np.random.default_rng(11)
    pool = np.array([-2.0, -0.5, -0.0, 0.0, 0.0, -0.0, 0.25, 1.0, 3.0])
    for trial in range(3000):
        n = int(rng.integers(1, 40))
        y = pool[rng.integers(0, len(pool), n)]
        table = SimpleNamespace(unit_ids=np.array(["u%d" % i for i in range(n)], dtype=object),
                                group_ids=np.array(["g"] * n, dtype=object),
                                time_columns={"yr": np.full(n, 2000, dtype=np.int64)}, y=y)
        census = C.scan_target(C.TableSource(table, int(rng.integers(1, n + 1))), {"yr": "year"}, None)
        view = SimpleNamespace(keep=np.ones(1, bool), steps=np.array([2000]), window_end=np.zeros(1, np.int64))
        got = census.event_rate(view, ("g",), 2000, 10 ** 9, pct)
        q = np.percentile(y, pct)
        assert got.events == int((y > q).sum()) and got.rows == n, (trial, y.tolist())
        assert got.q90 == q, (trial, y.tolist())
        zeros = y[y == 0]
        if zeros.size == 0 or np.signbit(zeros).all() or not np.signbit(zeros).any():
            assert np.signbit(got.q90) == np.signbit(q), (trial, y.tolist())


def test_read_units_from_a_coordinate_drops_labels_and_earlier_rows(pkg):
    import test_derive_all as T

    target = T.target_table()
    years = np.asarray(target.time_columns["step_year"])
    order = np.lexsort((np.asarray(target.time_columns["step_month"]), years))     # files hold whole years
    for name in ("unit_ids", "group_ids", "y"):
        setattr(target, name, np.asarray(getattr(target, name))[order])
    target.time_columns = {c: np.asarray(v)[order] for c, v in target.time_columns.items()}
    per_year = int((np.asarray(target.time_columns["step_year"]) == 2005).sum())
    census = C.scan_target(C.TableSource(target, per_year), {"step_year": "year", "step_month": "month"},
                           C.ReaderPresence(Reader()))
    units = sorted(set(np.asarray(target.unit_ids)[:40].tolist()))
    first = 2008 * 12
    whole = census.read_units(units, cache=False)
    part = census.read_units(units, cache=False, min_coord=first, labels=False)
    coord = whole.time_columns["step_year"] * 12 + whole.time_columns["step_month"] - 1
    keep = coord >= first
    assert np.array_equal(part.unit_ids, whole.unit_ids[keep])
    for c in whole.time_columns:
        assert np.array_equal(part.time_columns[c], whole.time_columns[c][keep])
    assert np.isnan(part.y).all() and np.isfinite(whole.y[keep]).any()
    assert census.last_read_files < len(census.source.files)        # the files before 2008 were not read
    assert int(census.rows_from(np.array([census._code_of[u] for u in units]), first).sum()) == int(keep.sum())
    with pytest.raises(D.DeriveRefusal, match="only the picked units' whole rows are cached"):
        census.read_units(units, min_coord=first)
