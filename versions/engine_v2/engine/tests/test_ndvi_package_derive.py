"""derive_all on the NDVI packages on the real stores, READ-ONLY: the DRAFT package (datasets/ndvi_draft) and,
since the owner's J ban list (OWNER_RULINGS_2026-10-05.md section J), the NDVI package itself (datasets/ndvi).
Tests may name problems, regions and drives.

UPDATED 2026-10-06 (agent C1): ndvi_draft is now the NDVI package AS INSTALLED, stamped DRAFT
(datasets/_tools/refresh_drafts.py; the shipped-verdict draft with its co-measured floor was moved aside to
datasets/_moved_20261006/ndvi_draft/). The two draft checks below therefore assert the installed package's settings
(_check_settings_j with the signed windows), not the old draft's shipped-verdict lags and co-measured floor.

THE NDVI PACKAGE (J ban list). derive_all refuses it at R8 (G-LAG) until the owner signs the windows of the 13
kept columns its store catalog declares unknown (tests/test_ndvi_package_ban.py pins the set):
test_derive_all_on_the_ndvi_package_stops_at_the_unsigned_windows checks that refusal on 3 small groups. So that
the J list is exercised past R8 before the signature, test_derive_all_on_the_ndvi_package_with_the_proposed_facts
runs it on a TEMPORARY COPY (tests/test_ndvi_package_ban.py::proposed_fact_copy) whose store catalog copy carries
the PROPOSED, UNSIGNED windows of BAN_REVIEW_SUMMARY.md section 5 as 'assumed' (nothing in the package or the shared
catalogs changes), on the same 3 small groups x 5 units: the settings expected_derived.json names for the KEPT
columns (co2 and sst_anom_mediterranean are banned by J1, so R8 no longer lists them), deeprec_twsa at its J2 (b)
lag 3, the J2 (a) lag-12 columns at lag 0 reading the parent 12 months back (complete in 2023 where the parent is
empty), cloud_frequency_pct and snow_cover_fraction at lag 1 by the co-measured fact, burn_frac at lag 1.
test_derive_all_on_every_group_of_the_ndvi_package (gated: NDVI_DERIVE_CHECK=1; the draft check's size, about an
hour and 6.5 GB) runs the same copy on every group x 15 units:
    set NDVI_DERIVE_CHECK=1 & py -3.9 -m pytest tests/test_ndvi_package_derive.py -s -q -k every_group_of_the_ndvi

Both checks go through the pipeline's own steps (treeroute.pipeline.run.Pipeline: _load, _groups, the target
read with a unit pick (split.stride_pick, as the smoke's, but over the units with a valid label in a year up to
the train end 2019 only; the engine's smoke pick also looks at the 2020-23 test years, an owner item), the
column reader with the panel, GFED and the feature script, then _derive, which runs derive_all twice as a run
does). Nothing is written; the settings checked are the ones the plan names for NDVI
(datasets/ndvi/expected_derived.json).

test_derive_all_on_three_small_groups (whenever D:/monthly_panel is present; about half a minute to a minute,
  well under 1 GB): 3 small groups x 5 units. The group-independent settings (monthly cadence, the windows, the per-unit
  router, the identity link only, the history block starting one step back (R17 start_offset_steps 1: t-2 at
  the nowcast, ruling R-D), R8's ruled index lags, GFED burn at lag 1 by the co-measured fact, and the DRAFT
  co-measured floor: V20_burned_binary, snow_cover_fraction, cloud_frequency_pct at lag 1 by the same fact),
  and on the reader's lagged table: every driver lag and top-5 context column equals
  its base column at t - k - lag(output) of the same unit (never a later month), every water-memory column and
  harmonic sits at lag 0, the feature script never sees the target, the harmonics are the row's month, and the
  column-chunked lagged() of the full check serves the same table bit for bit.

test_derive_all_on_every_group (gated: NDVI_DRAFT_DERIVE_CHECK=1): every group (133) x 15 units by the same
  train-end pick: 133 groups each trained and tested, 15 bank and 15 scored units per group (R18's 15 scored
  units at the full census, floor(20 x 100 / 133); the bank is capped at the 15 units read), 125 overlap blocks,
  the history block one step back (t-2 at the nowcast), the ruled index lags and the DRAFT co-measured floor.
  Last run 2026-10-04 on the CURRENT draft (catalog.yaml and ban.yaml of 2026-09-29 18:43, with the floor), by
  this function unchanged except for a private machine root (the machine's shared heavy-job lock was stale, a
  dead job's): passed; 30 derived entries, 526,680 target rows, 1,995 units, 479 tree features + 9 context,
  472 feature outputs, R8 lags {0: 419, 1: 33, 2: 14, 3: 2}, R30 flags esacci_sm and its 5 lags, 125 blocks;
  23 minutes for the target, 34 for the reader, 39 seconds for derive (57 minutes in all, beside another
  job for part of it); peak working set 6.46 GB. (The run of 2026-09-29 was on the draft BEFORE the floor:
  R8 {0: 422, 1: 30, 2: 14, 3: 2}.)
  MEMORY GUARDS: skipped below MIN_FREE (6.5 GB, the measured peak) of free RAM; a watchdog thread stops the
  process (after releasing the heavy-job lock) if free RAM falls below WATCHDOG_FREE (0.5 GB).
  ONE DEPARTURE, forced by the machine (a finding for the owner, engine code): ColumnReader.lagged copies the
  whole kept width several times at once (apply_lags on every same-step column, then a per-column frame, then
  the kept-order copy), about 20 KB per row at NDVI's ~490 kept columns; the unchanged reader reached 10.2 GB
  RSS on this census and the run was stopped at 1 GB of free RAM. The check therefore serves lagged() through
  the reader's own lagged() applied to chunks of CHUNK columns, written in the kept order into one
  preallocated array (the same io calls per column; the small test proves the tables are identical). Check
  that no other heavy job runs first:
      set NDVI_DRAFT_DERIVE_CHECK=1 & py -3.9 -m pytest tests/test_ndvi_package_derive.py -s -q
"""

import collections
import json
import os
import re
import time

import numpy as np
import pandas as pd
import pytest

from conftest import ENGINE_DIR, make_registry

DRAFT_DIR = ENGINE_DIR / "datasets" / "ndvi_draft"
EXPECTED = ENGINE_DIR / "datasets" / "ndvi" / "expected_derived.json"
PANEL_DIR = "D:/monthly_panel"
SMALL_GROUPS = ("falkland_islands", "namib_desert", "okavango_delta")
SMALL_UNITS = 5
FULL_UNITS = 15
CHUNK = 24
# the heavy check's memory guards (see test_derive_all_on_every_group): it is skipped below MIN_FREE of free RAM,
# and a watchdog stops it (releasing the machine's heavy-job lock first) if free RAM falls below WATCHDOG_FREE
MIN_FREE = 6.5 * 2 ** 30     # the measured peak working set of 2026-10-04 (6.46 GB)
WATCHDOG_FREE = 0.5 * 2 ** 30

needs_panel = pytest.mark.skipif(not os.path.isdir(PANEL_DIR) or
                                 not (DRAFT_DIR / "data" / "static" / "part-0.parquet").is_file(),
                                 reason="D:/monthly_panel or ndvi_draft's static table is not on this machine")


def _v(x):
    return getattr(x, "value", x)


def _expected():
    return json.loads(EXPECTED.read_text(encoding="utf-8"))


def _fake_machine(tmp_path):
    from types import SimpleNamespace

    protected = tmp_path / "shipped_root"
    protected.mkdir(exist_ok=True)
    reg = make_registry(tmp_path, [protected])
    (tmp_path / "temp").mkdir(exist_ok=True)
    return SimpleNamespace(run_root=str(tmp_path / "runs"), temp_dir=str(tmp_path / "temp"),
                           registry_dir=str(reg))


def _chunked_lagged(reader, lags, chunk=CHUNK):
    """The reader's own lagged() applied to chunks of `chunk` kept columns, written side by side in the kept
    order into ONE preallocated float64 array (column-major, pandas' own block layout, so the frame wraps it
    without a copy: the kept width is held once, not twice as a dict of columns consolidated into a frame).
    Same io calls per column; see the module docstring. The reader's cache is set aside while the chunks are
    computed (a cached full table would otherwise be served to every chunk) and restored after."""
    from treeroute.pipeline import data as D

    kept, saved = reader.kept, dict(reader._lagged)
    values = np.empty((len(reader.raw.index), len(kept)), dtype=np.float64, order="F")
    try:
        for i in range(0, len(kept), chunk):
            reader.kept = tuple(kept[i:i + chunk])
            reader._lagged.clear()
            part = D.ColumnReader.lagged(reader, lags)
            if list(part.columns) != list(reader.kept):
                raise AssertionError("a chunk came back with other columns")
            for j, c in enumerate(part.columns):
                values[:, i + j] = part[c].to_numpy(dtype=np.float64)
            del part
    finally:
        reader.kept = kept
        reader._lagged.clear()
        reader._lagged.update(saved)
    return pd.DataFrame(values, index=reader.raw.index, columns=list(kept), copy=False)


def _watchdog(release, limit=WATCHDOG_FREE, period=2.0):
    """Stop the whole process if the machine's free RAM falls below `limit` while the heavy check runs (the
    owner's machine has 15.8 GB shared with other jobs; a stopped check can be re-run, a machine paging to a
    halt cannot). `release` (the pipeline's _release: the heavy-job lock, the temp root it made) runs first,
    so no stale lock is left; then os._exit, because a numpy call holding the main thread would delay an
    exception. Returns the event that ends the watch."""
    import threading

    import psutil

    stop = threading.Event()

    def watch():
        while not stop.wait(period):
            free = psutil.virtual_memory().available
            if free < limit:
                print("WATCHDOG: %.2f GB of RAM free (below %.2f GB): releasing the lock and stopping the check"
                      % (free / 2 ** 30, limit / 2 ** 30), flush=True)
                try:
                    release()
                finally:
                    os._exit(3)
    threading.Thread(target=watch, name="ndvi-derive-watchdog", daemon=True).start()
    return stop


def _serve_chunked(reader):
    """Make derive_all's reader.lagged the chunked one (cached per lag map, like the reader's own)."""
    cache = {}

    def lagged(lags):
        key = tuple(sorted((c, int(l.steps)) for c, l in lags.items()))
        if key not in cache:
            cache[key] = _chunked_lagged(reader, lags)
        return cache[key]
    reader.lagged = lagged


def _read(p, groups, units, log=print):
    """The pipeline's target read and column reader for `groups`, keeping `units` units per group by the
    smoke's stride pick over the units with a valid label UP TO THE TRAIN END (expected_derived.json R7
    train_end, 2019; _check_settings asserts that R7 derives the same year), so no label of a test year
    takes part in the pick. The engine's own smoke pick (treeroute/pipeline/run.py Pipeline._read) looks at
    every year, the 2020-23 test years included: an owner item outside this package. Group by group (the
    engine's read_target holds every file of the groups it is given before the pick, which at 133 groups is
    the whole census)."""
    from treeroute import split as SP
    from treeroute.derive.rules import derive_r01_cadence
    from treeroute.pipeline import data as D

    spec = p.spec
    train_end = int(_expected()["R3_R7_windows"]["train_end"])
    (year_col,) = [c for c, part in spec.time_facts.items() if part == "year"]

    def keep(group, frame):
        valid = (np.isfinite(frame[spec.target_col].to_numpy(dtype=np.float64))
                 & (frame[year_col].to_numpy(dtype=np.int64) <= train_end))
        found = tuple(sorted(str(u) for u in pd.unique(frame[spec.unit_col].to_numpy()[valid])))
        return SP.stride_pick(found, units)

    parts = [D.read_target(p.pkg, spec, p.target_hook, p.listing, (g,), keep, log) for g in groups]
    p.target_df = pd.concat(parts, ignore_index=True)
    del parts
    p.target_df[spec.unit_col] = D.shared_str_ids(p.target_df[spec.unit_col], "unit id")
    p.target_df[spec.group_col] = D.shared_str_ids(p.target_df[spec.group_col], "group id")
    p.target = D.target_table(p.target_df, spec)
    p.cadence = derive_r01_cadence(p.target.unit_ids, p.target.time_columns, spec.time_facts).value


@needs_panel
def test_derive_all_on_three_small_groups(tmp_path, monkeypatch):
    from treeroute.pipeline import data as D
    from treeroute.pipeline.record import KIND_HEADLINE
    from treeroute.pipeline.run import Pipeline

    p = Pipeline(DRAFT_DIR, tmp_path / "runs", KIND_HEADLINE, machine=_fake_machine(tmp_path),
                 echo=lambda s: None)
    p._planning = True
    p._load()
    assert p.draft.is_draft
    p._groups()
    assert len(p.all_groups) == 133
    if not set(SMALL_GROUPS) <= set(p.all_groups):
        pytest.skip("the small groups are not in this panel")
    p.run_groups = SMALL_GROUPS
    spec, hook = p.spec, p.feature_hook
    seen = []
    build = hook.build

    def spy(frame, keys):
        seen.append(list(frame.columns))
        return build(frame, keys)
    monkeypatch.setattr(hook, "build", spy)
    _read(p, SMALL_GROUPS, SMALL_UNITS, log=lambda s: None)
    p.reader = D.ColumnReader(p.pkg, spec, p.target_df, p.cadence, hook, lambda s: None)
    p._derive()
    d = p.derived

    _check_settings_j(d, _expected(), proposed=False)       # the draft is the installed package (2026-10-06)
    units = d["R18:units"].value
    assert sorted(d["R18:groups"].value) == sorted(SMALL_GROUPS)
    assert {len(v) for v in units.bank.values()} == {len(v) for v in units.scored.values()} == {SMALL_UNITS}
    assert len(seen) == 1 and spec.target_col not in seen[0]           # the feature script never sees the target
    assert spec.target_col not in p.reader.raw.columns

    lags = d["R8"].value
    lagged = p.reader.lagged(lags)
    raw = p.reader.raw
    uid = np.asarray(p.target.unit_ids, dtype=object)
    steps = p.reader.steps
    row_of = pd.Series(np.arange(len(uid)), index=pd.MultiIndex.from_arrays([uid, steps]))

    def base_at(base, back):
        idx = row_of.reindex(pd.MultiIndex.from_arrays([uid, steps - back])).to_numpy()
        ok = np.isfinite(idx)
        out = np.full(len(uid), np.nan)
        out[ok] = raw[base].to_numpy(dtype=np.float64)[idx[ok].astype(np.int64)]
        return out

    pairs = [(hook.lag_column(b, k), b, k) for k in hook.LAG_ORDERS for b in hook.LAG_BASES] + list(hook.TOP5)
    wants = {}
    for column, base, k in pairs:
        if column not in lagged.columns:
            continue
        L = int(lags[column].steps)
        if base in lags:                                              # never later than the base itself
            assert L + k >= int(lags[base].steps), (column, L, base, lags[base].steps)
        wants[column] = base_at(base, k + L)
    # J2 (d): lagged() runs the engine's last-value rule on the kept TREE features (pipeline/data.py, wired
    # 2026-10-05): the expected values go through the same rule (same rows, units and steps), so a short gap
    # reads the same unit's earlier value in both; a value the raw lag holds is never changed by it
    from treeroute.io.lastvalue import fill_last_value

    want_df = pd.DataFrame(wants, index=lagged.index)
    trees = tuple(c for c in want_df.columns if c in spec.tree_features)
    filled, _ = fill_last_value(want_df, p.reader.codes, steps, trees, p.cadence)
    checked = 0
    for column, raw_want in wants.items():
        want = filled[column].to_numpy(dtype=np.float64)
        got = lagged[column].to_numpy(dtype=np.float64)
        assert np.array_equal(np.isnan(got), np.isnan(want)), column
        assert np.allclose(got[~np.isnan(got)], want[~np.isnan(want)], rtol=1e-6, atol=0), column
        held = ~np.isnan(raw_want)
        assert np.allclose(got[held], raw_want[held], rtol=1e-6, atol=0), column
        checked += 1
    assert checked >= 300, checked                                    # 340 on 2026-09-29
    water = [c for c, f in hook.OUTPUTS.items() if f["operation"].split()[0] in
             ("trailing_mean", "cumulative", "years_since")]
    harmonics = [c for c, _, _ in hook.HARMONICS]
    for c in water + harmonics:
        if c in lagged.columns:
            assert int(lags[c].steps) == 0, (c, lags[c].steps)
            assert np.array_equal(lagged[c].to_numpy(dtype=np.float64), raw[c].to_numpy(dtype=np.float64),
                                  equal_nan=True), c
    for c in harmonics:
        assert c in spec.context
    month = p.target.time_columns["month"]
    assert np.allclose(lagged["ctx:sin1"].to_numpy(), np.sin(2 * np.pi * (month - 0.5) / 12))
    assert np.allclose(lagged["ctx:cos2"].to_numpy(), np.cos(4 * np.pi * (month - 0.5) / 12))
    assert "ctx:climatology" not in spec.context                     # the engine's normal replaces it

    chunked = _chunked_lagged(p.reader, lags, chunk=7)
    assert list(chunked.columns) == list(lagged.columns)
    for c in lagged.columns:
        assert np.array_equal(chunked[c].to_numpy(), lagged[c].to_numpy(dtype=np.float64), equal_nan=True), c
    assert p.reader.lagged(lags) is lagged                           # the reader's own cache is untouched


def test_the_watchdog_releases_first_then_stops_the_process(tmp_path):
    """The heavy check's memory watchdog: below its limit it runs the release (the heavy-job lock) and then
    ends the process with code 3; above it, it stays quiet until told to stop."""
    import subprocess
    import sys

    pytest.importorskip("psutil")
    marker = tmp_path / "released.txt"
    code = "; ".join(["import sys, time", "sys.path.insert(0, %r)" % str(ENGINE_DIR),
                      "sys.path.insert(0, %r)" % str(ENGINE_DIR / "tests"),
                      "import test_ndvi_package_derive as T",
                      "T._watchdog(lambda: open(%r, 'w').write('released'), limit=2 ** 62, period=0.05)"
                      % str(marker),
                      "time.sleep(30)"])
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert done.returncode == 3, (done.returncode, done.stdout, done.stderr)
    assert "WATCHDOG" in done.stdout and marker.read_text() == "released"
    calls = []
    stop = _watchdog(lambda: calls.append(1), limit=-1, period=0.01)
    time.sleep(0.1)
    stop.set()
    assert calls == []


@needs_panel
@pytest.mark.skipif(os.environ.get("NDVI_DRAFT_DERIVE_CHECK") != "1",
                    reason="heavy real-data check (about an hour, 6.5 GB peak): set NDVI_DRAFT_DERIVE_CHECK=1 to run it")
def test_derive_all_on_every_group(tmp_path):
    import psutil

    from treeroute.pipeline import data as D
    from treeroute.pipeline.record import KIND_HEADLINE
    from treeroute.pipeline.run import Pipeline
    from treeroute.runs.machine import load_machine

    if psutil.virtual_memory().available < MIN_FREE:
        pytest.skip("less than %.1f GB of RAM free: close other jobs first" % (MIN_FREE / 2 ** 30))
    t0 = time.time()
    machine = load_machine()
    p = Pipeline(DRAFT_DIR, machine.run_root, KIND_HEADLINE, machine=machine)
    p._planning = True
    p._lock()                         # the machine's heavy-job lock: refuses beside another pipeline job
    watch = _watchdog(p._release)
    try:
        p._load()
        p._groups()
        _read(p, p.run_groups, FULL_UNITS)
        t_read = time.time()
        p.reader = D.ColumnReader(p.pkg, p.spec, p.target_df, p.cadence, p.feature_hook, p.log)
        _serve_chunked(p.reader)
        t_reader = time.time()
        p._derive()
        d = p.derived
        exp = _expected()
        _check_settings_j(d, exp, proposed=False)            # the draft is the installed package (2026-10-06)
        units = d["R18:units"].value
        assert len(d["R18:groups"].value) == exp["LORO_groups"]["n_groups"] == 133
        assert {len(v) for v in units.scored.values()} == {exp["R18_units_per_group"]["scored"]} == {FULL_UNITS}
        assert {len(v) for v in units.bank.values()} == {FULL_UNITS}   # the bank is capped at the units read
        assert len(p.blocks.members) == exp["R14_overlap_blocks"]["n_blocks"] == 125
        lags = d["R8"].value
        flagged = sorted(d["R30"].value) if "R30" in d else []
        day1 = set(exp["R30_missing_flags"]["day1_review_csv"])
        assert all(c.rsplit("_lag", 1)[0] in day1 or c in day1 for c in flagged), flagged
        summary = {
            "units_per_group_read": FULL_UNITS, "target_rows": int(len(p.target_df)),
            "units": int(p.target_df[p.spec.unit_col].nunique()), "entries": len(d),
            "tree_features": len(p.spec.tree_features), "context": list(p.spec.context),
            "feature_outputs": len(p.reader.outputs),
            "R8_by_lag": dict(sorted(collections.Counter(int(l.steps) for l in lags.values()).items())),
            "R30_flagged": flagged, "blocks": len(p.blocks.members),
            "seconds": {"target": round(t_read - t0), "reader": round(t_reader - t_read),
                        "derive": round(time.time() - t_reader)},
            "peak_working_set_gb": round(getattr(psutil.Process().memory_info(), "peak_wset", 0) / 2 ** 30, 2)}
        (tmp_path / "ndvi_draft_derive_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
        print("SUMMARY %s" % json.dumps(summary), flush=True)
    finally:
        watch.set()
        p._release()


# ------------------------------------------------------------------------------------------------
# the NDVI package itself (the J ban list)
NDVI_DIR = ENGINE_DIR / "datasets" / "ndvi"
# J1 bans these two index columns (trend_proxy), so derive's R8 no longer lags them on this package
J_BANNED_INDEX = ("co2", "sst_anom_mediterranean")


def _check_settings_j(d, exp, proposed=True):
    """The group-independent settings of the NDVI package under the J ban list (plan 3.2 / expected_derived.json,
    for the kept columns). proposed: the run used proposed_fact_copy's PROPOSED index windows; else the package as
    installed, with the windows the owner signed under ruling L1 (b) ({3, month, centred}: lag 1 month)."""
    from test_ndvi_package_ban import HOLD, LIVESTOCK, PROPOSED_LAGS, SIGNED_WINDOWS

    cad = d["R1"].value
    assert (_v(cad.kind), cad.length, _v(cad.unit)) == ("regular", 1, "month")
    assert d["R2"].value.steps_per_year == 12
    w, ew = d["R7"].value, exp["R3_R7_windows"]
    assert int(d["R4"].value) == ew["y0"] == 2003
    assert (w.y0, w.y_end, list(w.test_years), w.train_end) == (ew["y0"], ew["y_end"], ew["test_years"],
                                                                 ew["train_end"])
    assert tuple(w.inner_fit) == tuple(ew["inner_fit"]) and list(w.inner_score) == ew["inner_score"]
    assert list(d["R10"].value.leads) == exp["R10_leads"]["leads"] == [6, 12]
    assert _v(d["R12"].value) == exp["R12_router_kind"]["value"] == "per_unit"
    assert [_v(x) for x in d["R22"].value] == exp["R22_links"]["value"] == ["identity"]
    h, eh = d["R17"].value, exp["R17_history"]
    assert h.start_offset_steps == eh["start_offset_steps"] == 1
    assert (len(h.columns), h.last_values, list(h.trailing_steps), h.all_history_mean) == (
        eh["n_columns"], eh["last_values"], eh["trailing_steps"], eh["all_history_mean"])
    lags = d["R8"].value
    for c, k in exp["R8_feature_lags"]["index_lags_steps"].items():
        if c in J_BANNED_INDEX:
            assert c not in lags, c
            continue
        assert c in lags and int(lags[c].steps) == k, (c, lags.get(c))
    assert int(lags["burn_frac"].steps) == exp["R8_feature_lags"]["burn_frac_steps"] == 1
    for c in ("cloud_frequency_pct", "snow_cover_fraction"):            # J1 / Q3 a and J2 (d): co-measured
        assert (int(lags[c].steps), lags[c].floor_reason) == (1, "co_measured"), (c, lags[c])
    for c in ("snow_duration_days", "luh2_urban", "ntl") + HOLD:          # annual columns at year -1 (J2 c; the L3
        assert int(lags[c].steps) == exp["R8_feature_lags"]["annual_columns_steps"] == 1, c    # livestock holds)
        assert _v(lags[c].column_cadence.unit) == "year", c
    assert not set(LIVESTOCK) & set(lags)                                  # L3: the raw aglw_* are banned
    assert int(lags["deeprec_twsa"].steps) == 3                            # J2 (b)
    assert [int(lags["deeprec_twsa_lag%d" % k].steps) for k in (1, 2, 3, 6, 12)] == [2, 1, 0, 0, 0]
    for b in ("V06_spei_12m", "spei_01m", "spei_03m", "spei_06m", "spei_24m", "amo"):   # J2 (a)
        assert b not in lags and int(lags[b + "_lag12"].steps) == 0, b
    if proposed:
        assert {c: int(lags[c].steps) for c in PROPOSED_LAGS} == PROPOSED_LAGS
    else:
        # pdo: lag 2 by ruling N1 (OWNER_RULINGS_2026-10-06.md N, the ERSSTv5 reach); the others lag 1 (L1 b)
        assert {c: int(lags[c].steps) for c in SIGNED_WINDOWS} == {c: 2 if c == "pdo" else 1 for c in SIGNED_WINDOWS}


@needs_panel
def test_derive_all_on_the_ndvi_package_passes_r8_with_the_signed_windows(tmp_path):
    """The NDVI package as installed, after ruling L1 (b) (2026-10-06): the 13 windows R8 refused are signed, so
    derive_all runs through (no G-LAG refusal) and gives the plan's settings with every signed index column at lag 1."""
    from treeroute.pipeline import data as D
    from treeroute.pipeline.record import KIND_HEADLINE
    from treeroute.pipeline.run import Pipeline

    p = Pipeline(NDVI_DIR, tmp_path / "runs", KIND_HEADLINE, machine=_fake_machine(tmp_path), echo=lambda s: None)
    p._planning = True
    p._load()
    assert not p.draft.is_draft
    p._groups()
    assert len(p.all_groups) == 133
    if not set(SMALL_GROUPS) <= set(p.all_groups):
        pytest.skip("the small groups are not in this panel")
    p.run_groups = SMALL_GROUPS
    _read(p, SMALL_GROUPS, SMALL_UNITS, log=lambda s: None)
    p.reader = D.ColumnReader(p.pkg, p.spec, p.target_df, p.cadence, p.feature_hook, lambda s: None)
    p._derive()
    _check_settings_j(p.derived, _expected(), proposed=False)
    assert len(p.spec.tree_features) == 492 and len(p.spec.context) == 9    # 493 before ruling N S29 (road_density)


@needs_panel
def test_derive_all_on_the_ndvi_package_with_the_proposed_facts(tmp_path):
    from test_ndvi_package_ban import proposed_fact_copy
    from treeroute.pipeline import data as D
    from treeroute.pipeline.record import KIND_HEADLINE
    from treeroute.pipeline.run import Pipeline

    root = proposed_fact_copy(tmp_path / "copy")
    p = Pipeline(root, tmp_path / "runs", KIND_HEADLINE, machine=_fake_machine(tmp_path), echo=lambda s: None)
    p._planning = True
    p._load()
    assert not p.draft.is_draft
    p._groups()
    if not set(SMALL_GROUPS) <= set(p.all_groups):
        pytest.skip("the small groups are not in this panel")
    p.run_groups = SMALL_GROUPS
    _read(p, SMALL_GROUPS, SMALL_UNITS, log=lambda s: None)
    p.reader = D.ColumnReader(p.pkg, p.spec, p.target_df, p.cadence, p.feature_hook, lambda s: None)
    p._derive()
    d = p.derived
    _check_settings_j(d, _expected())
    assert sorted(d["R18:groups"].value) == sorted(SMALL_GROUPS)
    assert len(p.spec.tree_features) == 492 and len(p.spec.context) == 9    # 493 before ruling N S29 (road_density)
    assert p.spec.target_col not in p.reader.raw.columns
    # J2 (a) on the data: each lag-12 column is its parent 12 calendar months earlier (same unit), and is complete in
    # 2023 where the raw parent is empty (amo keeps only January 2023)
    lags = d["R8"].value
    lagged = p.reader.lagged(lags)
    raw = p.reader.raw
    uid = np.asarray(p.target.unit_ids, dtype=object)
    steps = p.reader.steps
    row_of = pd.Series(np.arange(len(uid)), index=pd.MultiIndex.from_arrays([uid, steps]))
    idx = row_of.reindex(pd.MultiIndex.from_arrays([uid, steps - 12])).to_numpy()
    ok = np.isfinite(idx)
    year = p.target.time_columns["year"]
    for b in ("V06_spei_12m", "spei_01m", "spei_03m", "spei_06m", "spei_24m", "amo"):
        want = np.full(len(uid), np.nan)
        want[ok] = raw[b].to_numpy(dtype=np.float64)[idx[ok].astype(np.int64)]
        got = lagged[b + "_lag12"].to_numpy(dtype=np.float64)
        assert np.array_equal(np.isnan(got), np.isnan(want)), b
        assert np.allclose(got[~np.isnan(got)], want[~np.isnan(want)], rtol=1e-6, atol=0), b
        assert np.isfinite(raw[b].to_numpy(dtype=np.float64)[year == 2023]).mean() <= 1.0 / 12, b
        assert np.isfinite(got[year == 2023]).all(), b
        assert b not in lagged.columns, b                                  # the raw parent never enters


@needs_panel
@pytest.mark.skipif(os.environ.get("NDVI_DERIVE_CHECK") != "1",
                    reason="heavy real-data check (about an hour, 6.5 GB peak): set NDVI_DERIVE_CHECK=1 to run it")
def test_derive_all_on_every_group_of_the_ndvi_package(tmp_path):
    """Every group (133) x 15 units of the NDVI package under the J ban list, on the proposed-facts copy (the module
    docstring): 133 groups each trained and tested, 15 bank and 15 scored units per group, 125 overlap blocks, and
    the settings of _check_settings_j. Same memory guards and chunked lagged() as the draft's full check."""
    import psutil

    from test_ndvi_package_ban import proposed_fact_copy
    from treeroute.pipeline import data as D
    from treeroute.pipeline.record import KIND_HEADLINE
    from treeroute.pipeline.run import Pipeline
    from treeroute.runs.machine import load_machine

    if psutil.virtual_memory().available < MIN_FREE:
        pytest.skip("less than %.1f GB of RAM free: close other jobs first" % (MIN_FREE / 2 ** 30))
    t0 = time.time()
    root = proposed_fact_copy(tmp_path / "copy")
    machine = load_machine()
    p = Pipeline(root, machine.run_root, KIND_HEADLINE, machine=machine)
    p._planning = True
    p._lock()
    watch = _watchdog(p._release)
    try:
        p._load()
        p._groups()
        _read(p, p.run_groups, FULL_UNITS)
        t_read = time.time()
        p.reader = D.ColumnReader(p.pkg, p.spec, p.target_df, p.cadence, p.feature_hook, p.log)
        _serve_chunked(p.reader)
        t_reader = time.time()
        p._derive()
        d = p.derived
        exp = _expected()
        _check_settings_j(d, exp)
        units = d["R18:units"].value
        assert len(d["R18:groups"].value) == exp["LORO_groups"]["n_groups"] == 133
        assert {len(v) for v in units.scored.values()} == {exp["R18_units_per_group"]["scored"]} == {FULL_UNITS}
        assert {len(v) for v in units.bank.values()} == {FULL_UNITS}
        assert len(p.blocks.members) == exp["R14_overlap_blocks"]["n_blocks"] == 125
        lags = d["R8"].value
        flagged = sorted(d["R30"].value) if "R30" in d else []
        summary = {
            "units_per_group_read": FULL_UNITS, "target_rows": int(len(p.target_df)),
            "units": int(p.target_df[p.spec.unit_col].nunique()), "entries": len(d),
            "tree_features": len(p.spec.tree_features), "context": list(p.spec.context),
            "feature_outputs": len(p.reader.outputs),
            "R8_by_lag": dict(sorted(collections.Counter(int(l.steps) for l in lags.values()).items())),
            "R30_flagged": flagged, "R30_day1_review_csv": exp["R30_missing_flags"]["day1_review_csv"],
            "blocks": len(p.blocks.members),
            "seconds": {"target": round(t_read - t0), "reader": round(t_reader - t_read),
                        "derive": round(time.time() - t_reader)},
            "peak_working_set_gb": round(getattr(psutil.Process().memory_info(), "peak_wset", 0) / 2 ** 30, 2)}
        (tmp_path / "ndvi_derive_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
        print("SUMMARY %s" % json.dumps(summary), flush=True)
    finally:
        watch.set()
        p._release()
