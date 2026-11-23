"""The fire package's code on the REAL stores (READ-ONLY; each test is skipped when a store is not on this
machine). Tests may name problems, regions and drives (G-NONAMES scans engine code only).

  - the static table / key map of fire_draft (data/static, written by ingest/build_static.py);
  - the target reader on real files: a complete census, the n_valid rule, the unit-months absent from a file;
  - the fire-history recompute at the SHIPPED label lag 1 against D:/fire/history, value for value (two groups
    here; the build of 2026-09-29 checked all 40 groups, every cell the store holds, 252 months, 19 columns:
    identical): the check of the code the ruled store (label lag 2) is built with;
  - the OLD fire_draft's rebuilt history store (data/fire_history, label lag 2) against the recompute, value for
    value, and its manifest; its unit-keyed drivers copy against the D: source (values unchanged); both stores hold
    only the shipped 1,000-cell pick. UPDATED 2026-10-06 (agent C1): the draft was refreshed from the installed fire
    package (datasets/_tools/refresh_drafts.py), and the old draft, with these two stores, was moved aside, not
    deleted, to datasets/_moved_20261006/fire_draft/; these tests read it there. They FAIL LOUDLY when that folder
    is gone (2026-10-06 review: a skip would hide it), naming the folder: restore it, or retire these five archival
    tests with it (move their text to datasets/_moved_20261006/tests_before_draft_refresh/);
    the pick's 103 non-unit cells (finnish_lapland's 15 on 9 latitude rows no target file holds);
  - the ring radii over the 40 region grids (the disclosed own-value weight at grid edges, catalog.yaml);
  - G-HIST on real labels: no fire-history column equals a column of the engine's own-history block or a plain
    lag, on every row or wherever that lag is non-zero, except last_burn_size (a sparse own lag);
  - the overlap blocks from the static table's grid indices (R14, the 'grid_indices' link rule).
"""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

from conftest import ENGINE_DIR

DATASETS = ENGINE_DIR / "datasets"
FIRE_DIR = DATASETS / "fire"
DRAFT_DIR = DATASETS / "fire_draft"
STATIC = DRAFT_DIR / "data" / "static" / "part-0.parquet"
MANIFEST = DRAFT_DIR / "data" / "static" / "key_map_manifest.json"
TARGET = Path("D:/fire/target")
HISTORY = Path("D:/fire/history")
JOINED = Path("D:/fire/drivers/joined")
GEOM = Path("D:/fire/geom")
PANEL = Path("D:/monthly_panel")

needs_target = pytest.mark.skipif(not (TARGET.is_dir() and STATIC.is_file()),
                                  reason="D:/fire/target or fire_draft's static table is not on this machine")
needs_history = pytest.mark.skipif(not (TARGET.is_dir() and HISTORY.is_dir() and GEOM.is_dir()),
                                   reason="D:/fire/target, D:/fire/history or D:/fire/geom is not on this machine")


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def static():
    if not STATIC.is_file():
        pytest.skip("fire_draft's static table is not written")
    return pq.read_table(str(STATIC)).to_pandas()


def test_the_static_table_is_the_key_map_the_manifest_describes(static):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert list(static.columns) == ["cell_id", "region", "lat", "lon", "grid_ix", "grid_iy"]
    assert len(static) == manifest["units"] == 925737
    assert not static.cell_id.duplicated().any()
    counts = static.groupby("region").size().to_dict()
    assert counts == {g: v["units"] for g, v in manifest["groups"].items()}
    assert len(counts) == 40
    assert np.isfinite(static.lat).all() and np.isfinite(static.lon).all()
    ids = static.cell_id.astype(str) + ""
    rebuilt = static.region.astype(str) + "_" + static.grid_ix.astype(str) + "_" + static.grid_iy.astype(str)
    assert (ids == rebuilt).all()                                  # the id IS {group}_{ix}_{iy}
    # every group's units = target cells (union over years) that are panel cells
    for g, v in manifest["groups"].items():
        assert v["units"] + v["target_cells_without_panel_cell"] == v["target_cells"], g
        assert v["years"] == [2002, 2022], g
    if TARGET.is_dir():
        groups = sorted({p.stem.rpartition("_")[0] for p in TARGET.glob("*.parquet")})
        assert groups == sorted(counts)


def test_the_overlap_blocks_from_the_static_grid_indices(static):
    """R14 on the static table: with grid indices the 'grid_indices' rule runs (no diagonal tolerance);
    one linked pair, as expected_derived.json's provisional spacing-rule measurement found."""
    from treeroute import split as SP

    d = SP.derive_overlap_blocks(static.region.to_numpy(object), static.lat.to_numpy(), static.lon.to_numpy(),
                                 static.grid_ix.to_numpy(), static.grid_iy.to_numpy())
    assert d.inputs["link_rule"]["rule"] == "grid_indices"
    assert len(d.value.members) == 39
    assert tuple(d.value.linked_pairs) == (("angola_zambia_fire_belt", "miombo_woodland_zambia", 60),)
    pair, = d.inputs["linked_pairs"]
    assert pair["shared_position_units"] == [29, 29] and pair["only_touches"] is False


@needs_target
def test_the_target_reader_on_real_files_is_a_complete_census(static):
    tr = load_module(DRAFT_DIR / "ingest" / "target_reader.py", "fire_tr_real")
    for group, year in (("thar_desert", 2010), ("canadian_taiga", 2003)):
        path = TARGET / ("%s_%d.parquet" % (group, year))
        out = tr.read_target_file(path, {"group": group, "year": year})
        units = static[static.region == group].cell_id
        assert len(out) == len(units) * 12
        assert set(out.cell_id) == set(units)
        raw = pq.read_table(str(path), columns=["lat", "lon", "month", "n_valid", "burned_frac"]).to_pandas()
        km = tr.key_map(group, DRAFT_DIR)
        _, ok = km.lookup(tr.cell_key(raw.lat.to_numpy(), raw.lon.to_numpy()))
        raw = raw[ok]
        expected_nan = int((raw.n_valid <= 0).sum()) + (len(units) * 12 - len(raw))
        assert int(out.burned_frac.isna().sum()) == expected_nan
        valid = out.burned_frac.dropna()
        assert ((valid >= 0) & (valid <= 1)).all()
    # the store's gaps: some canadian_taiga units have no row in 2003, so their whole year is NaN
    assert int(out.groupby("cell_id").burned_frac.apply(lambda s: s.isna().all()).sum()) > 0


@needs_history
@pytest.mark.parametrize("group", ["thar_desert", "greece_mainland"])
def test_the_recompute_equals_the_history_store_value_for_value(group):
    """At the shipped label lag 1 the recompute IS D:/fire/history (the ruled store uses lag 2, same code)."""
    bh = load_module(DRAFT_DIR / "ingest" / "build_history.py", "fire_bh_real_%s" % group)
    th = load_module(DRAFT_DIR / "features" / "target_history.py", "fire_th_real_%s" % group)
    la, lo, grid, y0 = bh.group_grid(DRAFT_DIR, group)
    cols = th.history_columns(grid, la, newest_label_lag=th.SHIPPED_NEWEST_LABEL_LAG)
    assert tuple(cols) == th.SHIPPED_COLUMNS
    store = pd.read_parquet(HISTORY / ("%s.parquet" % group))
    i, j = th.grid_positions(la, lo, store.lat.to_numpy(), store.lon.to_numpy())
    k = th.month_index(store.year.to_numpy(), store.month.to_numpy(), y0)
    for c in th.SHIPPED_COLUMNS:
        assert np.array_equal(cols[c][i, j, k], store[c].to_numpy(dtype=np.float32)), c


# the old draft (shipped verdicts, 1,000-cell sidecar copies), moved aside on 2026-10-06 when the draft was refreshed
OLD_DRAFT_DIR = DATASETS / "_moved_20261006" / "fire_draft"
DRAFT_HISTORY = OLD_DRAFT_DIR / "data" / "fire_history"
DRAFT_DRIVERS = OLD_DRAFT_DIR / "data" / "fire_drivers"
PICK_ONLY_TEMPLATES = ("data/fire_history/{group}.parquet", "data/fire_drivers/{group}.parquet")


@pytest.fixture
def old_draft():
    """The old fire_draft kept aside: these archival tests depend on it, so its absence FAILS (never a quiet skip;
    2026-10-06 review). Only the D: stores' absence (another machine) skips, as everywhere in this file."""
    missing = [str(d) for d in (OLD_DRAFT_DIR, DRAFT_HISTORY, DRAFT_DRIVERS) if not d.is_dir()]
    if missing:
        pytest.fail("the old fire_draft is no longer kept aside (missing: %s). These archival tests read its 1,000-cell "
                    "stores and code there (moved aside, not deleted, on 2026-10-06). Restore the folder, or retire "
                    "these five tests with it (move their text to datasets/_moved_20261006/tests_before_draft_refresh/)"
                    % missing)
    return OLD_DRAFT_DIR


@pytest.mark.skipif(not (TARGET.is_dir() and GEOM.is_dir()), reason="D:/fire/target or D:/fire/geom is not on this machine")
@pytest.mark.parametrize("group", ["thar_desert", "northern_australia_monsoon"])
def test_the_draft_history_store_is_the_recompute_at_the_ruled_lag(static, old_draft, group):
    """data/fire_history = build_history.py's columns at label lag 2 on the drivers copy's units, value for
    value; its manifest names the lag, the columns, the unit rule and today's code."""
    bh = load_module(OLD_DRAFT_DIR / "ingest" / "build_history.py", "fire_bh_draft_%s" % group)
    th = load_module(OLD_DRAFT_DIR / "features" / "target_history.py", "fire_th_draft_%s" % group)
    units_from = "data/fire_drivers/{group}.parquet"
    manifest = json.loads((DRAFT_HISTORY / bh.MANIFEST).read_text(encoding="utf-8"))
    head = bh._manifest_head(OLD_DRAFT_DIR, units_from)
    assert {k: manifest[k] for k in head} == head
    assert sorted(manifest["groups"]) == sorted(static.region.unique())
    stored = pd.read_parquet(DRAFT_HISTORY / ("%s.parquet" % group))
    assert list(stored.columns) == ["cell_id", "year", "month"] + list(th.COLUMNS)
    assert not set(th.REFUSED_COLUMNS) & set(stored.columns)
    units = bh.units_of(OLD_DRAFT_DIR, units_from, group)
    assert sorted(stored.cell_id.unique()) == units
    assert manifest["groups"][group] == {"rows": len(stored), "units": len(units)}
    rebuilt = bh.unit_history(OLD_DRAFT_DIR, group, units=units)
    pd.testing.assert_frame_equal(stored, rebuilt, check_dtype=True)
    assert stored.tslf_months.min() >= th.NEWEST_LABEL_LAG == 2


@pytest.mark.skipif(not JOINED.is_dir(), reason="the drivers sidecar D:/fire/drivers/joined is not on this machine")
@pytest.mark.parametrize("group", ["thar_desert", "finnish_lapland"])
def test_the_drivers_copy_holds_the_source_values_unchanged(static, old_draft, group):
    tr = load_module(DRAFT_DIR / "ingest" / "target_reader.py", "fire_tr_copies_%s" % group)
    km = tr.key_map(group, DRAFT_DIR)
    src = pd.read_parquet(JOINED / ("%s.parquet" % group))
    copy = pd.read_parquet(DRAFT_DRIVERS / ("%s.parquet" % group))
    unit, ok = km.lookup(tr.cell_key(src.lat.to_numpy(), src.lon.to_numpy()))
    src = src[ok].assign(cell_id=km.ids[unit[ok]]).drop(columns=["lat", "lon"])
    src = src.sort_values(["cell_id", "year", "month"], kind="stable").reset_index(drop=True)
    assert list(copy.columns) == ["cell_id", "year", "month"] + [c for c in src.columns
                                                                  if c not in ("cell_id", "year", "month")]
    pd.testing.assert_frame_equal(copy, src[copy.columns], check_dtype=True)
    manifest = json.loads((OLD_DRAFT_DIR / "data" / "sidecar_rekey_manifest.json").read_text(encoding="utf-8"))
    assert sorted(manifest["dropped_cells"]) == ["data/fire_drivers/{group}.parquet"]
    dropped = manifest["dropped_cells"]["data/fire_drivers/{group}.parquet"].get(group, 0)
    assert dropped == (15 if group == "finnish_lapland" else 0)
    assert sum(manifest["dropped_cells"]["data/fire_drivers/{group}.parquet"].values()) == 103


@pytest.mark.skipif(not (JOINED.is_dir() and TARGET.is_dir()), reason="D:/fire is not on this machine")
def test_the_dropped_sidecar_cells_lie_on_rows_no_target_file_holds(static):
    """ingest/build_sidecars.py docstring: finnish_lapland's 15 non-unit cells of the shipped pick lie on 9
    latitude rows that no target file holds (so they have no label)."""
    side = pq.read_table(str(JOINED / "finnish_lapland.parquet"), columns=["lat", "lon"]).to_pandas().drop_duplicates()
    units = static[static.region == "finnish_lapland"]
    keys = set(zip(np.round(units.lat, 5), np.round(units.lon, 5)))
    dropped = [(a, b) for a, b in zip(np.round(side.lat, 5), np.round(side.lon, 5)) if (a, b) not in keys]
    rows = set()
    for path in sorted(TARGET.glob("finnish_lapland_*.parquet")):
        rows |= set(np.round(pq.read_table(str(path), columns=["lat"]).column("lat").to_numpy(), 5))
    assert len(dropped) == 15
    assert len({a for a, _ in dropped}) == 9 and not {a for a, _ in dropped} & rows


@pytest.mark.skipif(not GEOM.is_dir(), reason="D:/fire/geom is not on this machine")
def test_the_ring_radii_over_the_region_grids_are_the_disclosed_range():
    """catalog.yaml RING EDGES: over the 40 region grids the ring radius is 6-17 cells (25 km) and 19-52 (75 km),
    so a unit's own value weighs 25.5-28.6% of its ring mean at a grid corner and 0.5-3.6% on an edge
    (tests/test_fire_package.py::test_ring_edge_padding_puts_the_units_own_value_in_its_ring)."""
    th = load_module(DRAFT_DIR / "features" / "target_history.py", "fire_th_radii")
    radii = {km: [] for km in th.RINGS_KM}
    paths = sorted(GEOM.glob("*.npz"))
    assert len(paths) == 40
    for path in paths:
        la = np.load(str(path))["la"]
        for km in th.RINGS_KM:
            radii[km].append(th.ring_radius_cells(la, km))
    assert (min(radii[25.0]), max(radii[25.0])) == (6, 17)
    assert (min(radii[75.0]), max(radii[75.0])) == (19, 52)


def test_the_pick_only_stores_hold_the_shipped_pick_only(static, old_draft):
    """The premise of the old draft's coverage departure: each store holds at most 1,000 units per group, the same
    units in both, under 5% of all units (why neither can serve R18's stride over every unit)."""
    units = {}
    for template in PICK_ONLY_TEMPLATES:
        per = {}
        for g in sorted(static.region.unique()):
            path = OLD_DRAFT_DIR / template.format(group=g)
            per[g] = set(pq.read_table(str(path), columns=["cell_id"]).column("cell_id").to_pylist())
            assert len(per[g]) <= 1000, (template, g)
        units[template] = per
    a, b = units.values()
    assert a == b
    total = sum(len(v) for v in a.values())
    assert total / len(static) < 0.05


@needs_history
@pytest.mark.parametrize("lag", [1, 2])
def test_g_hist_on_real_labels_no_history_column_duplicates_the_engine_block(lag):
    """On a burning group's units (every tenth cell of the store), no column equals the engine's own-history
    block (from t-1 or t-2) or a plain lag y(t-1..t-12), on every row or wherever the reference is non-zero,
    except last_burn_size: it equals y(t-lag) on every row where y(t-lag) > 0 (G_HIST_SPARSE_LAG)."""
    import test_fire_package as T

    group = "northern_australia_monsoon"
    bh = load_module(DRAFT_DIR / "ingest" / "build_history.py", "fire_bh_ghist")
    th = load_module(DRAFT_DIR / "features" / "target_history.py", "fire_th_ghist")
    la, lo, grid, _ = bh.group_grid(DRAFT_DIR, group)
    store = pd.read_parquet(HISTORY / ("%s.parquet" % group))
    cells = store[["lat", "lon"]].drop_duplicates().iloc[::10]
    i, j = th.grid_positions(la, lo, cells.lat.to_numpy(), cells.lon.to_numpy())
    y = grid[i, j, :].astype(np.float64)                          # units x months, NaN = unobserved
    cols = th.history_columns(grid, la, newest_label_lag=lag)
    hits = T.g_hist_matches({c: v[i, j, :] for c, v in cols.items()}, y)
    assert sorted(hits) == sorted(T.G_HIST_SPARSE_LAG), hits
    assert "y(t-%d) (informative rows)" % lag in hits["last_burn_size"]
    burning = int((np.nan_to_num(y) > 0).any(axis=1).sum())
    assert burning > 50                                         # the check ran on cells that burn
