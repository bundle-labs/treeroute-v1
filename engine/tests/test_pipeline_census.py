"""The pipeline on the streaming census (the default) against its in-memory path (Pipeline(streamed=
False), gates only), on test_pipeline's synthetic package read from its files: the same run folder
(fingerprint), byte-identical derived.json and plan.json, the same run record when every census unit is
picked (the last-value rule's counts included), the same vault rows and hashes, the same saved predictions
and scores; R30's streamed per-test-year shares, counted in unit blocks, equal the whole-table reader's;
the census RAM pre-flight refuses when the census would not fit, and the picked-unit working set is
refused before any picked row is read.

With fewer picked units than census units (the full-size shape): a planted label after the cut in a unit
that is in the census but not picked never reaches the picked rows read again or the vault; R30's
test-year count reads that unit's file again, but only from the test years' window on and with every
label dropped as the file is read, so the planted value never leaves census.read_units; the count runs
once for both derive passes; a window too short for the lags is refused by the check against the picked
units' whole histories; the window follows R8's lags and the declared windows of feature outputs, and
none is drawn for an output without a bounded window; a driver store without a {group} placeholder is
refused before the census; the streamed data manifest (what the fingerprint hashes) equals the
whole-table reader's.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from test_pipeline import FAKE_LAUNCH, _machine, make_pipeline_package, sklearnex_patched  # noqa: F401
from treeroute.errors import RefusedError

SAME_FILES = ("derived.json", "plan.json", "adoption.json", "inner_candidates.csv", "score_by_group.csv",
              "score_pooled.csv", "per_year.csv", "per_group.csv", "jackknife.csv", "preclip.csv")
SAME_JSON_BUT_TIMES = ("guard_report.json", "verdict.json", "tables.json", "test_pass_router.json",
                       "decision_checks.json", "run_record.json")
TIME_KEYS = ("_at", "_utc", "time", "seconds", "elapsed", "temp_dir")       # times and machine paths


def _no_times(obj):
    if isinstance(obj, dict):
        return {k: _no_times(v) for k, v in obj.items() if not any(k.endswith(t) for t in TIME_KEYS)}
    if isinstance(obj, list):
        return [_no_times(v) for v in obj]
    return obj


def _same_json(a, b):
    import json

    return _no_times(json.loads(a.read_text(encoding="utf-8"))) == _no_times(json.loads(b.read_text(encoding="utf-8")))
SAME_FRAMES = ("test_preds.parquet", "inner_preds.parquet")


def _pipe(pkg, base, streamed, kind="smoke"):
    from treeroute.pipeline.run import Pipeline

    return Pipeline(pkg, base / "runs", kind, machine=_machine(base), echo=lambda s: None,
                    launch_record=FAKE_LAUNCH, streamed=streamed)


@pytest.fixture(scope="module")
def both(tmp_path_factory):
    base = tmp_path_factory.mktemp("census_pipe")
    pkg = make_pipeline_package(base / "pk", sparse=True)
    out = {}
    for streamed in (True, False):
        b = base / ("streamed" if streamed else "in_memory")
        b.mkdir()
        out[streamed] = Path(_pipe(pkg, b, streamed).run())
    return pkg, base, out


def _same_tables_but_schedule(per_group, whole):
    """tables.json of the per-group path (plan R20: every table dropped once its group is routed) against the whole
    path's: the same stores (bank, trees, writer, backend); the inner-cut store built the same rows in the same
    builds, and its dropped tables are the whole path's held tables; the fit-cut store's final tables hold the
    same rows (the GLS weight model's donor-row tables were dropped, so the test pass computed those rows again);
    only the per-group record carries the schedule."""
    import json

    a = _no_times(json.loads(per_group.read_text(encoding="utf-8")))
    b = _no_times(json.loads(whole.read_text(encoding="utf-8")))
    assert "schedule" in a and "schedule" not in b
    for store in ("inner_cut_store", "fit_cut_store"):
        sa, sb = a[store], b[store]
        assert "dropped_tables" not in sb and sa["tables"] == []
        for key in ("bank_fingerprint", "trees", "features", "writer", "backend", "closed"):
            assert sa[key] == sb[key], (store, key)
        dropped = [{k: v for k, v in d.items() if k != "dropped_after_builds"} for d in sa["dropped_tables"]]
        if store == "inner_cut_store":
            assert sorted(dropped, key=lambda d: (d["group"], d["kind"])) == sb["tables"]
            assert sa["builds"] == sb["builds"]
        else:
            last = {}
            for d in dropped:
                last[(d["group"], d["kind"])] = d
            assert {k: d["rows"] for k, d in last.items()} == {(d["group"], d["kind"]): d["rows"] for d in sb["tables"]}


def test_the_streamed_smoke_writes_the_same_run_folder_and_outputs(both):
    _, _, out = both
    s, m = out[True], out[False]
    assert s.name == m.name                               # the same fingerprint
    for name in SAME_FILES:
        assert (s / name).read_bytes() == (m / name).read_bytes(), name
    for name in SAME_JSON_BUT_TIMES:
        if name == "tables.json":
            _same_tables_but_schedule(s / name, m / name)
        elif (m / name).exists():
            assert _same_json(s / name, m / name), name
    assert (s / "per_group_plan.json").is_file() and not (m / "per_group_plan.json").exists()
    assert (s / "per_group_schedule.json").is_file() and not (m / "per_group_schedule.json").exists()
    for name in SAME_FRAMES:
        pd.testing.assert_frame_equal(pd.read_parquet(s / name), pd.read_parquet(m / name))
    ladder_s = sorted(p.relative_to(s) for p in (s / "ladder").rglob("*") if p.is_file())
    ladder_m = sorted(p.relative_to(m) for p in (m / "ladder").rglob("*") if p.is_file())
    assert ladder_s == ladder_m
    for rel in ladder_s:
        if rel.suffix == ".csv":
            assert (s / rel).read_bytes() == (m / rel).read_bytes(), rel
        elif rel.suffix == ".json" and "lock" not in rel.name:
            assert _same_json(s / rel, m / rel), rel
        elif rel.suffix == ".parquet":
            pd.testing.assert_frame_equal(pd.read_parquet(s / rel), pd.read_parquet(m / rel))


def _through_vault(pkg, base, streamed):
    p = _pipe(pkg, base, streamed)
    p._lock()
    try:
        p._load()
        p._groups()
        p._preflight_target()
        p._read()
        p._derive()
        vg = p._vault(None)
        return p, vg
    finally:
        p._release()


def test_the_vault_holds_the_same_rows_and_hashes(both, tmp_path):
    from treeroute.derive.shapes import CutKind

    pkg, _, _ = both
    (tmp_path / "s").mkdir()
    (tmp_path / "m").mkdir()
    ps, vs = _through_vault(pkg, tmp_path / "s", True)
    pm, vm = _through_vault(pkg, tmp_path / "m", False)
    assert ps.census is not None and pm.census is None
    assert tuple(vs.grid.unit_ids) == tuple(vm.grid.unit_ids)
    for field in ("unit_ids", "steps", "window_end"):
        assert np.array_equal(getattr(vs, field), getattr(vm, field))
    lists = ps.derived["R18:units"].value
    bank = tuple(u for g in sorted(lists.bank) for u in lists.bank[g])
    cut = int(ps.derived["R11"].value[0].fit_cut)
    a = vs.labels.donor_labels(ps.split_sets, cut, CutKind.FIT, 0, bank, "test", picks=lists)
    b = vm.labels.donor_labels(pm.split_sets, cut, CutKind.FIT, 0, bank, "test", picks=lists)
    assert a.row_key_hash == b.row_key_hash and np.array_equal(a.y, b.y)
    # the streamed vault was built from the bank units' rows read again, nothing else
    assert set(ps.target.unit_ids.tolist()) == set(bank)


def test_streamed_test_year_shares_equal_the_whole_table_reader(both, tmp_path):
    """R30's per-test-year missing share counted group by group in blocks of a few units (the picked
    rows are then NOT every census row) equals ColumnReader.measure over the whole table."""
    from treeroute.pipeline import stream as STR

    pkg, _, _ = both
    (tmp_path / "m").mkdir()
    (tmp_path / "s").mkdir()
    pm, _ = _through_vault(pkg, tmp_path / "m", False)
    ps, _ = _through_vault(pkg, tmp_path / "s", True)
    lags = pm.derived["R8"].value
    years = tuple(pm.derived["R7"].value.test_years)
    whole = pm.reader.measure(_any_donor(pm), lags, years).test_year_missing_share
    share = STR.StreamedShareReader(ps.pkg, ps.spec, ps.census, ps.cadence, ps.feature_hook, lambda s: None,
                                    lambda n: None, lambda: 3 * 12 * 8)      # about three units a block
    got = share._test_year_shares(lags, years)
    assert list(got) == list(whole) and got == whole


def _any_donor(p):
    from types import SimpleNamespace

    units = np.asarray(p.reader.units, dtype=object)[:5]
    steps = np.asarray(p.reader.steps)[:5]
    return SimpleNamespace(unit_ids=units, times=steps, row_key_hash="h", unit_scope="picked")


def test_the_census_preflight_refuses_when_the_census_would_not_fit(both, tmp_path, monkeypatch):
    from treeroute.runs import preflight

    pkg, _, _ = both
    p = _pipe(pkg, tmp_path, True)
    p._lock()
    try:
        p._load()
        p._groups()
        monkeypatch.setattr(preflight, "available_ram_bytes", lambda: 1000)
        with pytest.raises(RefusedError, match="G-DISK"):
            p._preflight_target()
    finally:
        p._release()


def test_the_run_record_carries_the_last_value_counts(both):
    import json

    _, _, out = both
    rec = json.loads((out[True] / "run_record.json").read_text(encoding="utf-8"))
    lv = rec["last_value"]
    assert lv["rule"] == "J2d" and lv["constant"] == {"C18.last_value_max_months": 2} and lv["max_steps"] == 2
    assert lv["filled_rows"] > 0 and lv["columns"]["x1"]["filled"] > 0          # x1's masked sentinels
    assert "ctx:m" not in lv["columns"]
    log = (out[True] / "run.log").read_text(encoding="utf-8")
    assert "last value (J2d" in log


def test_the_column_reader_estimate_covers_its_measured_peaks():
    """The picked units' working set and R30's unit blocks are go/refused on a column reader's peak bytes
    a row: measured on full-size monthly stores at 4,235 B (102 frame columns) and 24,401 B (964 columns);
    the estimate keeps at least 15% over both (the earlier 120 + 16 x columns gave 1,752 B at 102)."""
    from treeroute.runs import preflight

    assert preflight.column_reader_peak_bytes(1, 102) >= 1.15 * 4235
    assert preflight.column_reader_peak_bytes(1, 964) >= 1.15 * 24401
    assert preflight.column_reader_peak_bytes(1000, 102) == 1000 * preflight.column_reader_peak_bytes(1, 102)


@pytest.mark.parametrize("per_group", [True, False])
def test_the_picked_working_set_is_refused_before_any_picked_row_is_read(both, tmp_path, monkeypatch, per_group):
    """Per group (plan R20, every command): the picked units' label rows are go/refused as target rows (one group's
    column reader is checked at its own build); the gates' whole path checks one reader of every picked unit."""
    from treeroute.pipeline.run import Pipeline
    from treeroute.runs import preflight

    pkg, _, _ = both
    p = Pipeline(pkg, tmp_path / "runs", "smoke", machine=_machine(tmp_path), echo=lambda s: None,
                 launch_record=FAKE_LAUNCH, streamed=True, per_group=per_group)
    p._lock()
    try:
        p._load()
        p._groups()
        p._preflight_target()
        p._read()                                        # the census pass fits
        from treeroute import engine_constants as K

        monkeypatch.setattr(K, "ROOM_MAX_WAIT_SECONDS", 0)      # owner ruling Q1: no wait, so it refuses as before
        monkeypatch.setattr(preflight, "available_ram_bytes", lambda: 1000)
        with pytest.raises(RefusedError, match="picked units' working set") as info:
            p._derive()
        assert "G-DISK" in str(info.value) or getattr(info.value, "rule", "") == "G-DISK"
        if per_group:
            assert "read again for their labels" in str(info.value) and "GiB" in str(info.value)
        else:
            assert "a column reader at its peak" in str(info.value)
        assert p.census._picked is None                  # refused before the picked rows were read
    finally:
        p._release()


def test_one_groups_reader_is_refused_before_it_is_built(both, tmp_path, monkeypatch):
    """Per group: with the label rows fitting, a group's column reader that does not fit is refused before it is
    built (the largest group's reader is the per-group path's RAM peak)."""
    from treeroute.runs import preflight

    pkg, _, _ = both
    p = _pipe(pkg, tmp_path, True)
    p._lock()
    try:
        p._load()
        p._groups()
        p._preflight_target()
        p._read()
        total = int(p.census.rows)                       # the smoke picks every census unit
        # the separability check's sample (every smoke group together: every row) fits; one group's reader does not
        from treeroute import engine_constants as K

        monkeypatch.setattr(K, "ROOM_MAX_WAIT_SECONDS", 0)      # owner ruling Q1: no wait, so it refuses as before
        monkeypatch.setattr(preflight, "column_reader_peak_bytes", lambda rows, cols: 10 ** 18 if rows < total else 0)
        with pytest.raises(RefusedError, match="one group's picked-unit column reader") as info:
            p._derive()
        assert "plan R20" in str(info.value)
        assert p.census._picked is not None              # the label rows were read; no group reader was built
    finally:
        p._release()


VICTIM_GROUP, VICTIM_INDEX, PLANTED = "grp_d", 5, 987.654
NO_LABEL_THROUGH, PLANT_YEAR, PLANT_MONTH = 2008, 2010, 6


def _plant(pkg_dir):
    """The victim unit gets no valid label through NO_LABEL_THROUGH (after the train end: it is no candidate,
    so never a bank unit) and the planted label at PLANT_YEAR-PLANT_MONTH, after the cut. Returns its id."""
    from test_pipeline import _units

    victim = _units(VICTIM_GROUP)[VICTIM_INDEX]
    for path in sorted((Path(pkg_dir) / "data" / "target" / ("group=%s" % VICTIM_GROUP)).rglob("*.parquet")):
        frame = pd.read_parquet(path)
        mine = frame["unit_id"] == victim
        frame.loc[mine & (frame["step_year"] <= NO_LABEL_THROUGH), "y"] = np.nan
        frame.loc[mine & (frame["step_year"] == PLANT_YEAR) & (frame["step_month"] == PLANT_MONTH), "y"] = PLANTED
        frame.to_parquet(path, index=False)
    return victim


@pytest.fixture(scope="module")
def planted(tmp_path_factory):
    """Both paths through the vault on the planted package; the streamed run's census.read_units calls
    and test-year counts are recorded (spy)."""
    from treeroute.derive import census as CEN
    from treeroute.pipeline import stream as STR

    base = tmp_path_factory.mktemp("census_planted")
    pkg = make_pipeline_package(base / "pk")
    victim = _plant(pkg)
    spy = {"reads": [], "counts": []}
    real_read, real_count = CEN.TargetCensus.read_units, STR.StreamedShareReader._count_finish

    def read_units(self, units, cache=True, min_coord=None, labels=True):
        rows = real_read(self, units, cache, min_coord, labels)
        y = np.asarray(rows.y, dtype=np.float64)
        coord = self._calendar_coord(rows.time_columns)
        spy["reads"].append({"cache": cache, "min_coord": min_coord, "labels": labels,
                             "victim": bool(np.any(np.asarray(rows.unit_ids, dtype=object) == victim)),
                             "planted": bool(np.any(y == PLANTED)), "finite": int(np.isfinite(y).sum()),
                             "first_coord": int(coord.min()), "files": int(getattr(self, "last_read_files", -1))})
        return rows

    def count(self, st):                         # the end of a test-year count (whole or per-group path)
        out = real_count(self, st)
        spy["counts"].append({"share": self, "stats": dict(self.test_year_stats)})
        return out
    CEN.TargetCensus.read_units, STR.StreamedShareReader._count_finish = read_units, count
    try:
        out = {}
        for streamed in (True, False):
            b = base / ("streamed" if streamed else "in_memory")
            b.mkdir()
            out[streamed] = _through_vault(pkg, b, streamed)
    finally:
        CEN.TargetCensus.read_units, STR.StreamedShareReader._count_finish = real_read, real_count
    return victim, out, spy


def test_a_planted_label_in_an_unpicked_unit_never_reaches_the_vault(planted):
    from treeroute import derive as DV
    from treeroute.runs.atomic import dumps_canonical

    victim, out, _ = planted
    (ps, vs), (pm, vm) = out[True], out[False]
    assert dumps_canonical(DV.derived_document(ps.derived)) == dumps_canonical(DV.derived_document(pm.derived))
    lists = ps.derived["R18:units"].value
    bank = {u for g in lists.bank for u in lists.bank[g]}
    assert victim in set(ps.census.unit_names.tolist()) and victim not in bank
    # the plant is real: the in-memory path holds it in its whole target table
    assert np.any(pm.target.y[pm.target.unit_ids == victim] == PLANTED)
    # the picked rows read again do not hold the victim; neither vault holds it
    assert victim not in set(ps.target.unit_ids.tolist()) and not np.any(ps.target.y == PLANTED)
    for vg in (vs, vm):
        assert victim not in set(vg.grid.unit_ids) and not np.any(vg.labels._y == PLANTED)
    assert tuple(vs.grid.unit_ids) == tuple(vm.grid.unit_ids)
    assert vs.labels._y.tobytes() == vm.labels._y.tobytes()
    assert vs.labels._window_end.tobytes() == vm.labels._window_end.tobytes()


def test_the_test_year_count_runs_once_from_the_window_and_drops_every_label(planted):
    """Two derive passes, one test-year count (cached per lag map and test years); its blocks read only the
    rows from the window on (skipping the files that end before it), every label dropped inside
    read_units: the victim's file is read again there, the planted value never comes out."""
    victim, out, spy = planted
    ps = out[True][0]
    assert ps.model_labels_withheld                               # two derive passes ...
    assert len(spy["counts"]) == 1                                # ... one test-year count
    share, stats = spy["counts"][0]["share"], spy["counts"][0]["stats"]
    assert share.test_year_source.startswith("the count already made")       # the second pass's source
    assert stats["min_coord"] is not None and stats["checked_rows"] > 0
    blocks = [r for r in spy["reads"] if not r["cache"]]
    assert len(blocks) == stats["blocks"] > 0
    assert all(r["min_coord"] == stats["min_coord"] and r["first_coord"] >= stats["min_coord"] for r in blocks)
    assert all(not r["labels"] and r["finite"] == 0 and not r["planted"] for r in blocks)
    assert any(r["victim"] for r in blocks)
    per_group = len(ps.source.files) // len(ps.source.groups)
    assert all(0 < r["files"] < per_group for r in blocks)        # the files before the window are skipped
    assert stats["target_files_read"] == sum(r["files"] for r in blocks)
    # every read with labels is a picked read of whole histories
    assert all(r["cache"] and r["min_coord"] is None and not r["victim"] for r in spy["reads"] if r["labels"])


def test_a_window_too_short_for_the_lags_is_refused(planted, monkeypatch):
    """The window's check: a window cut at the first test year changes the annual column x2 (lag 1: the
    year before) at the picked units' test-year rows, against the picked reader's whole histories:
    refused (R30)."""
    from treeroute.pipeline import data as D
    from treeroute.pipeline import stream as STR

    _, out, _ = planted
    ps = out[True][0]
    lags = ps.derived["R8"].value
    years = tuple(ps.derived["R7"].value.test_years)
    share = STR.StreamedShareReader(ps.pkg, ps.spec, ps.census, ps.cadence, ps.feature_hook, lambda s: None,
                                    lambda n: None, lambda: 10 ** 6)
    whole = D.ColumnReader(ps.pkg, ps.spec, STR.rows_frame(ps.target, ps.spec), ps.cadence, ps.feature_hook,
                           lambda s: None)
    share._readers = {("picked",): whole}                         # the picked units' whole histories
    monkeypatch.setattr(STR, "window_of_test_years", lambda *a, **k: (min(years), {"forced": True}))
    with pytest.raises(D.DataRefusal, match="the test-year window changes tree feature"):
        share._test_year_shares(lags, years)


def test_the_test_year_window_follows_the_lags_and_the_declared_windows(planted):
    from types import SimpleNamespace as NS

    from treeroute.pipeline import stream as STR
    from treeroute.timing.shapes import Lag

    _, out, _ = planted
    ps = out[True][0]
    lags = dict(ps.derived["R8"].value)
    years = tuple(ps.derived["R7"].value.test_years)
    first = min(years)
    coarse = [c for p in ps.presence.plan if not p.by_step for c in p.columns]
    assert coarse == []                                           # x2 is a year column of a monthly store
    # x2 (a year column, lag 1): the year before the one holding s_fill (the first test step - 2 - 1)
    year, info = STR.window_of_test_years(ps.spec, {}, coarse, lags, ps.cadence, years)
    assert year == first - 2 and info["binding"] == ["x2"]
    # a same-step lag of 30 months reaches further back
    long = dict(lags, x1=Lag("x1", 30, lags["x1"].column_cadence, None))
    year, info = STR.window_of_test_years(ps.spec, {}, coarse, long, ps.cadence, years)
    assert info["binding"] == ["x1"] and info["first_step"] == info["s_fill"] - 30 and year == first - 3
    # x1 as a feature output declared over 24 months: its reach (24 steps and one) is added to the lag
    facts = ps.spec.store_facts["x1"]
    out24 = {"x1": NS(derived_from=("g1",))}
    base = dict(tree_features=ps.spec.tree_features, time_facts=ps.spec.time_facts, unit_col=ps.spec.unit_col,
                group_col=ps.spec.group_col)
    spec24 = NS(store_facts=dict(ps.spec.store_facts, x1=facts.model_copy(
        update={"window": facts.window.model_copy(update={"length": 24})})), **base)
    year, info = STR.window_of_test_years(spec24, out24, coarse, lags, ps.cadence, years)
    assert info["binding"] == ["x1"] and info["first_step"] == info["s_fill"] - 25 and year == first - 3
    # an output without a bounded declared window: no window (every row is read)
    spec_none = NS(store_facts=dict(ps.spec.store_facts, x1=facts.model_copy(update={"window": None})), **base)
    year, info = STR.window_of_test_years(spec_none, out24, coarse, lags, ps.cadence, years)
    assert year is None and info["unbounded"] == "x1"


def test_the_test_year_window_on_an_annual_target():
    """An annual target: the last-value maximum is 0 steps (no fill), so s_fill is the year before the
    first test year; a lag of 2 years reaches two years further back; a static column needs only s_fill."""
    from types import SimpleNamespace as NS

    from treeroute import timing
    from treeroute.derive.shapes import Cadence, CadenceKind, StepUnit
    from treeroute.pipeline import stream as STR
    from treeroute.timing.shapes import Lag

    year = Cadence(kind=CadenceKind.REGULAR, length=1, unit=StepUnit.YEAR)
    spec = NS(tree_features=("a", "s"), time_facts={"yr": "year"}, unit_col="u", group_col="g",
              store_facts={"a": NS(cadence=NS(kind="regular"), window=None), "s": NS(cadence=NS(kind="static"))})
    first, info = STR.window_of_test_years(spec, {}, (), {"a": Lag("a", 2, year, None)}, year, (2019, 2020))
    assert info["first_test_step"] == int(timing.year_last_step(2018, year)) + 1
    assert info["s_fill"] == info["first_test_step"] - 1 and info["first_step"] == info["s_fill"] - 2
    assert first == 2016 and info["binding"] == ["a"]
    first, info = STR.window_of_test_years(spec, {}, (), {"a": Lag("a", 0, year, None)}, year, (2019, 2020))
    assert first == 2018 and info["binding"] == ["a", "s"]


def test_a_driver_store_without_a_group_placeholder_is_refused_before_the_census(planted, monkeypatch):
    from treeroute.pipeline import data as D
    from treeroute.pipeline import stream as STR

    _, out, _ = planted
    ps = out[True][0]
    monkeypatch.setattr(D, "listed_groups", lambda listing: None)
    with pytest.raises(D.DataRefusal, match=r"no \{group\} placeholder") as info:
        STR.PresenceReader(ps.pkg, ps.spec, ps.feature_hook, ps.run_groups)
    assert "G-DISK" in str(info.value) or getattr(info.value, "rule", "") == "G-DISK"


def test_the_streamed_data_manifest_equals_the_whole_table_readers(planted):
    _, out, _ = planted
    (ps, _), (pm, _) = out[True], out[False]
    picked_rows = sum(ps.reader.rows_of(g) for g in ps.reader.groups)
    assert picked_rows == len(ps.target.unit_ids) < ps.census.rows    # the picked readers hold fewer rows ...
    assert ps.data_manifest == pm.data_manifest                # ... and the manifest reports every row read
    assert pm.data_manifest == pm.reader.data_manifest()
