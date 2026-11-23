"""The row vault (labels/rows.py, SPEC_TABLE_MODE.md 3.4) and derive_all_table (derive/table.py, 3.5) on the toy."""

import datetime as _dt

import numpy as np
import pytest

from table_toy import build_toy_table_package


@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    from treeroute.package import table as T
    from treeroute.package.load import load_package

    pkg = build_toy_table_package(tmp_path_factory.mktemp("toy"))
    loaded = load_package(pkg)
    spec = T.table_spec(loaded)
    data = T.read_tables(loaded, spec, T.table_leads())
    return loaded, spec, data


def _first(year):
    return _dt.date(year, 1, 1).toordinal()


def test_as_of_reads_are_in_days_and_never_reach_the_test_window(toy, tmp_path):
    from treeroute.derive.shapes import CutKind
    from treeroute.labels.rows import build_row_vault
    from treeroute.labels.vault import VaultRefusal
    from treeroute import split as SP

    _, _, data = toy
    v = build_row_vault(data, _first(2008), None)
    cut = _dt.date(2004, 12, 31).toordinal()
    sl = v.asof(cut)
    assert sl.times.size and int(sl.times.max()) <= cut
    assert set(sl.times.tolist()) <= set(data.target_day[np.isfinite(data.y)].tolist())
    with pytest.raises(VaultRefusal, match="test window"):
        v.asof(_first(2008))
    from treeroute.package.schema import SplitFile

    d = v.donor_labels(SP.loro_split_sets(SplitFile()), cut, CutKind.FIT, 0, tuple(data.row_ids.tolist()), "probe")
    assert int(d.times.max()) <= cut and d.y.size == sl.y.size


def test_the_decision_surface_takes_each_row_at_its_own_day(toy):
    from treeroute.labels.rows import build_row_vault
    from treeroute.labels.vault import VaultRefusal

    _, _, data = toy
    v = build_row_vault(data, _first(2008), None)
    days = data.target_day
    sel = np.flatnonzero((days > _dt.date(2004, 12, 31).toordinal()) & (days <= _dt.date(2007, 12, 31).toordinal())
                         & np.isfinite(data.y))
    surf = v.decision_surface(data.row_ids[sel], days[sel], _dt.date(2007, 12, 31).toordinal())
    assert np.array_equal(surf.y, data.y[sel])
    with pytest.raises(VaultRefusal, match="target day"):
        v.decision_surface(data.row_ids[sel], days[sel] + 1, _dt.date(2007, 12, 31).toordinal())
    with pytest.raises(VaultRefusal, match="own-history"):
        v.asof_rows(np.zeros(1, np.int64), np.zeros(1, np.int64), 0)


def test_test_labels_open_only_after_a_lock(toy, tmp_path):
    from treeroute.labels.rows import build_row_vault
    from treeroute.labels.vault import VaultRefusal

    _, _, data = toy
    folder = tmp_path / "run"
    folder.mkdir()
    v = build_row_vault(data, _first(2008), folder)
    with pytest.raises(VaultRefusal, match="no locked adoption"):
        v.open_test_labels("0" * 64, 0, alarm_sha256="0" * 64)


def test_for_lead_masks_absent_rows_and_last_label_before_is_strict(toy, tmp_path):
    from treeroute.labels.rows import build_row_vault

    _, _, data = toy
    v = build_row_vault(data, _first(2008), None)
    lt = data.leads[365]
    v365 = v.for_lead(lt.present, 365)
    _, _, ok = v365.validity(int(data.target_day.min()), int(data.target_day.max()))
    absent = ~lt.present
    assert absent.any() and not ok[absent].any()
    # persistence: the same unit's newest label strictly before the issue day
    units = np.asarray(data.units, dtype=object)
    multi = [u for u in set(units.tolist()) if (units == u).sum() > 1]
    rows = np.flatnonzero(np.isin(units, multi))
    issue = data.target_day[rows]
    got = v.last_label_before(units[rows], issue, "probe")
    for i, r in enumerate(rows.tolist()):
        same = np.flatnonzero((units == units[r]) & (data.target_day < issue[i]) & np.isfinite(data.y))
        if same.size == 0:
            assert np.isnan(got[i])
        else:
            j = same[np.argmax(data.target_day[same])]
            assert got[i] == data.y[j]
    log = [r for r in v.read_log() if r["method"] == "last_label_before"]
    assert len(log) == 1
    served_test = 0
    for i, r in enumerate(rows.tolist()):
        same = np.flatnonzero((units == units[r]) & (data.target_day < issue[i]) & np.isfinite(data.y))
        if same.size:
            served_test += int(data.target_day[same].max() >= _first(2008))
    assert log[0]["test_window_rows"] == served_test
    assert v.test_window_reads()["rows"] == served_test
    # with_days (FIX_REPORT.md leakage item 3): the same labels plus the day of each, from one logged read
    v2 = build_row_vault(data, _first(2008), None)
    got2, days2 = v2.last_label_before(units[rows], issue, "probe", with_days=True)
    assert np.array_equal(got2, got, equal_nan=True)
    for i, r in enumerate(rows.tolist()):
        same = np.flatnonzero((units == units[r]) & (data.target_day < issue[i]) & np.isfinite(data.y))
        assert days2[i] == (int(data.target_day[same].max()) if same.size else -1)
    assert len([r for r in v2.read_log() if r["method"] == "last_label_before"]) == 1


def test_derive_all_table_writes_the_expected_entries(toy):
    from treeroute.derive import derived_document
    from treeroute.derive.table import derive_all_table
    from treeroute.package import table as T

    loaded, spec, data = toy
    d = derive_all_table(loaded, spec, data, T.table_leads())
    assert getattr(d["R1"].value.kind, "value", None) == "irregular"
    assert getattr(d["R2"].value.kind, "value", None) == "event_month"
    assert d["R4"].value == 2000 and d["R3"].value == 2011
    w = d["R7"].value
    assert w.test_years == (2008, 2009, 2010, 2011) and w.train_end == 2007 and w.inner_fit == (2000, 2004)
    assert tuple(d["R10"].value.leads) == (183, 365)
    cuts = d["R11"].value
    assert cuts[0].fit_cut == _dt.date(2007, 12, 31).toordinal()
    assert cuts[183].fit_cut == _first(2008) - 183 and cuts[365].guard_cut == _first(2005) - 365
    assert d["R12"].value.value == "neighbour"
    assert len(d["R13"].value[1]) == 5
    assert d["R17"].value.columns == ()
    lists = d["R18:units"].value
    assert sum(len(v) for v in lists.bank.values()) == len(data.row_ids)
    assert sum(len(v) for v in lists.scored.values()) == int(data.is_test.sum())
    assert "bank_units_hash" in d["R18:units"].inputs and "donor_row_key_hash" in d["R19"].input_hashes
    for L in (183, 365):
        for which in ("fit", "guard"):
            assert "R19:lead=%d:%s" % (L, which) in d
    assert [l.value for l in d["R22"].value] == ["identity", "log_c", "arcsine"]
    for L in (0, 183, 365):
        assert "R23:lead=%d" % L in d
    for g in sorted(lists.bank):
        assert "R23:fold=%s" % g in d
    assert "R30" in d and "U1:table" in d and "U2:vouched" in d
    derived_document(d)                                   # every entry serialises (derived.json)


# ------------------------------------------------------------------ V6 b: donor-only groups (PLAN_V6B.md T2, T5)
def _derive(tmp_path, variant):
    from treeroute.derive.table import derive_all_table
    from treeroute.package import table as T
    from treeroute.package.load import load_package

    loaded = load_package(build_toy_table_package(tmp_path, variant))
    spec = T.table_spec(loaded)
    data = T.read_tables(loaded, spec, T.table_leads())
    return data, derive_all_table(loaded, spec, data, T.table_leads())


def test_the_plain_toy_has_no_donor_only_group(toy):
    from treeroute.derive.table import derive_all_table
    from treeroute.package import table as T

    loaded, spec, data = toy
    d = derive_all_table(loaded, spec, data, T.table_leads())
    assert d["R18:donor_only"].value == ()
    assert d["R18:donor_only"].inputs["scored_groups"] == 5 and d["R18:donor_only"].inputs["train_rows"] == {}


def test_a_group_with_no_test_row_is_donor_only_and_still_trains_and_lends(tmp_path):
    data, d = _derive(tmp_path, "donor_only_group")
    groups = np.asarray(data.groups, dtype=object)
    assert d["R18:donor_only"].value == ("g_a",)
    lists = d["R18:units"].value
    assert lists.scored["g_a"] == () and all(lists.scored[g] for g in ("g_b", "g_c", "g_d", "g_e"))
    assert set(lists.bank["g_a"]) == set(np.asarray(data.row_ids, dtype=object)[groups == "g_a"].tolist())
    inp = d["R18:donor_only"].inputs
    assert inp["train_rows"]["g_a"] == int((groups == "g_a").sum()) and inp["surface_rows"]["g_a"] > 0
    assert inp["scored_groups"] == 4 and inp["donor_only_groups"] == 1
    folds = [g for (g,) in d["R13"].value[1]]
    assert len(folds) == 5 and "g_a" in folds
    assert "R23:fold=g_a" in d
    assert d["R19"].value["rows_per_group"]["g_a"] > 0 and d["R19:inner_cut"].value["rows_per_group"]["g_a"] > 0
    for L in (183, 365):
        for which in ("fit", "guard"):
            assert d["R19:lead=%d:%s" % (L, which)].value["rows_per_group"]["g_a"] > 0


def test_too_few_groups_with_a_test_row_refuse_at_derive_and_in_check(tmp_path):
    from treeroute.check.quick import run_quick
    from treeroute.check.report import is_green
    from treeroute.check.table import DONOR_ONLY_LABEL
    from treeroute.errors import RefusedError

    with pytest.raises(RefusedError, match="G-SUPPORT"):
        _derive(tmp_path / "a", "too_few_scored")
    ctx = run_quick(build_toy_table_package(tmp_path / "b", "too_few_scored"), echo=lambda s: None)
    line = dict(ctx.results)[DONOR_ONLY_LABEL]
    assert line.rule_id == "G-SUPPORT" and getattr(line.status, "value", line.status) == "block"
    assert not is_green(ctx.results)
    ok = run_quick(build_toy_table_package(tmp_path / "c", "donor_only_group"), echo=lambda s: None)
    line = dict(ok.results)[DONOR_ONLY_LABEL]
    assert getattr(line.status, "value", line.status) == "pass" and "g_a" in line.reason
    assert is_green(ok.results), ok.results
