"""The four headline dataset packages in declarative form (APP_PLAN.md 1.1-1.2).

Each package must load through the engine's own loader (closed folder, schema, sha256 includes,
fingerprint).

Splits under leave-one-region-out (owner ruling D; owner rulings E, L7 b): split.yaml holds only the
exclusions and seen_during_design, and every group in the data that is not excluded is trained and
tested. The shipped hard splits moved, exactly, to legacy_harness/shipped_splits.yaml (the harness
replays) and their test groups to treeroute_report/continuity_groups.yaml (the continuity row). Those
lists are still checked as SETS, never by count alone: every donor and test set is compared with the set
rebuilt from its shipped source (pm25_split.py; D:/run89full/ndvi_split.txt; the fire and defo
selections re-run read-only from their D: inputs). Counts are printed beside, as a second check.

The D: sources are read-only here. A test that needs one is skipped when it is missing, and fails
loudly when it is present but has changed (its sha256 no longer matches the one the shipped lists
cite), because then the transcription must be re-verified. D:/defo_matrix (2.9 GB) is not hashed: its
column list is pinned instead (parquet schemas only), plus one group's y/is_train values.

Driver columns are checked against the stores dataset.yaml DECLARES, not against every included
catalog: for pm25, fire and ndvi through the catalog that describes each declared driver store; for
defo, whose only driver store (D:/defo_matrix) has no store catalog, against the matrix's own columns.

Tests may name problems, regions and drives (G-NONAMES scans engine code only).
"""

import ast
import csv
import hashlib
import json
import re
from pathlib import Path

import pytest
import yaml

from conftest import ENGINE_DIR, REPO_PARENT
from treeroute import engine_constants as K
from treeroute import split as SP
from treeroute.io.listing import list_store
from treeroute.package.load import load_dataset_file, load_package, validate_file
from treeroute.package.schema import SplitFile

DATASETS = ENGINE_DIR / "datasets"
PACKAGES = ("pm25", "fire", "defo", "ndvi")
TARGETS = {"pm25": "pm25_ugm3", "fire": "burned_frac", "defo": "loss_frac", "ndvi": "V11_mean_ndvi"}
MONTHLY = ("pm25", "fire", "ndvi")
SHIPPED_SPLITS = ENGINE_DIR / "legacy_harness" / "shipped_splits.yaml"
CONTINUITY = ENGINE_DIR / "treeroute_report" / "continuity_groups.yaml"

PM25_SPLIT = REPO_PARENT / "pm25_split.py"
NDVI_SPLIT = Path("D:/run89full/ndvi_split.txt")
FOREST_CENSUS = Path("D:/run89full/forest_census.csv")
FIRE_SIZES = Path("D:/fire/region_sizes.csv")
FIRE_TARGET = Path("D:/fire/target")
RUN89_HELPERS = Path("D:/run89/helpers")

# sha256 of each split source as cited in the shipped lists' provenance (2026-09-28).
SOURCE_SHA256 = {
    PM25_SPLIT: "5507ff59ca7a9083e5bf1004879ec452f93661e68e916eb223d12f5f5e41e18a",
    NDVI_SPLIT: "7c1495b29e08acc6e4a5ffa66ccdbe88edcb17e1f237ef10a49be47af165637b",
    FOREST_CENSUS: "ca79ffe48f9438828ef3aae54013bc54d297ca3c7f573af7f9f5432d32a0eeb1",
    FIRE_SIZES: "5997f2c50e1b8080633c75ee1a92697d5ce2806f1fb0a2b23de0d60a16626031",
}

# (donors, tests) of the OLD hard splits as SET sizes: a side check only; every one is also compared as a
# set below. Under LORO every one of these groups is trained and tested.
COUNTS = {"pm25": (107, 20), "fire": (30, 10), "defo": (25, 17), "ndvi": (89, 44)}
GROUPS_UNDER_LORO = {p: d + t for p, (d, t) in COUNTS.items()}      # 127 / 40 / 42 / 133


class _Packages(dict):
    """The four packages, each loaded on first use and kept: a package that refuses to load (for example a stale
    include sha256) fails every case that reads it, loudly, and no case that does not."""

    def __missing__(self, name):
        if name not in PACKAGES:
            raise KeyError(name)
        self[name] = load_package(DATASETS / name)
        return self[name]


@pytest.fixture(scope="module")
def pkgs():
    return _Packages()


@pytest.fixture(scope="module")
def splits():
    """split.yaml of each package through the schema alone (no include hashes, so these tests do not
    depend on the shared store catalogs)."""
    return {p: validate_file(DATASETS / p / "split.yaml", SplitFile) for p in PACKAGES}


@pytest.fixture(scope="module")
def shipped():
    return yaml.safe_load(SHIPPED_SPLITS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def continuity():
    return yaml.safe_load(CONTINUITY.read_text(encoding="utf-8"))


def need(path):
    """Skip when a D: source is missing; fail loudly when it changed since the transcription."""
    if not path.exists():
        pytest.skip("source %s is not on this machine" % path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == SOURCE_SHA256[path], (
        "%s changed since the split was transcribed (sha256 %s, cited %s): re-verify "
        "legacy_harness/shipped_splits.yaml" % (path, digest, SOURCE_SHA256[path]))
    return path


def donors(shipped, name):
    """The OLD donor groups of a package (legacy_harness/shipped_splits.yaml)."""
    return set(shipped[name]["donor_groups"])


def tgroups(shipped, name):
    """The OLD test groups of a package (legacy_harness/shipped_splits.yaml)."""
    return set(shipped[name]["test_groups"])


def read_split_txt(path):
    """{'donors': {line: group}, 'tests': {line: group}} with 1-based line numbers."""
    out, section = {"donors": {}, "tests": {}}, None
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        if line in out:
            section = line
            continue
        assert section is not None, "group before a section header at line %d" % n
        out[section][n] = line
    return out


# ------------------------------------------------------------------------------------------------
# loading
@pytest.mark.parametrize("name", PACKAGES)
def test_package_loads_through_the_engine_loader(pkgs, name):
    pkg = pkgs[name]
    assert pkg.dataset.name == name
    assert len(pkg.fingerprint) == 64
    assert pkg.stores, "every package includes at least one shared store catalog"
    for path in pkg.stores:
        if name == "defo" and path in (DEFO_FEATURES_CATALOG, DEFO_K_CATALOG):
            # defo's generated features store catalog (owner ruling C 'Defo store') and, since owner ruling K
            # (OWNER_RULINGS_2026-10-05.md section K, 2026-10-06), its generated K store catalog, both in the package
            continue
        if name == "fire" and path == "ingest/fire_history_store_catalog.yaml":
            # owner ruling N S9 a (OWNER_RULINGS_2026-10-06.md N): the owner-built fire history store is declared
            continue
        # otherwise only the shared catalogs in the engine schema; the older seeds do not load (review/v2/README.md)
        assert path.startswith("../_stores/") and path.endswith("_schema_catalog.yaml"), path
    assert "../_stores/monthly_panel_v170_schema_catalog.yaml" in pkg.stores
    assert pkg.split == validate_file(DATASETS / name / "split.yaml", SplitFile)


# ------------------------------------------------------------------------------------------------
# split.yaml under leave-one-region-out (no D: needed)
@pytest.mark.parametrize("name", PACKAGES)
def test_split_yaml_holds_only_exclusions_and_seen_during_design(splits, name):
    split = splits[name]
    raw = yaml.safe_load((DATASETS / name / "split.yaml").read_text(encoding="utf-8"))
    assert set(raw) <= {"excluded", "seen_during_design"}, sorted(raw)
    assert split.excluded == {}, "%s: nothing is excluded (every group in the data is used)" % name
    assert len(split.seen_during_design) == len(set(split.seen_during_design))
    text = (DATASETS / name / "split.yaml").read_text(encoding="utf-8")
    assert "legacy_harness/shipped_splits.yaml" in text and "treeroute_report/continuity_groups.yaml" in text


def test_ndvi_seen_during_design_is_the_q49_pair(splits, shipped):
    assert set(splits["ndvi"].seen_during_design) == {"thar_desert", "greece_mainland"}
    for name in ("pm25", "fire", "defo"):
        assert splits[name].seen_during_design == []
    # both were test groups of the old split, so they are also in the continuity row
    assert set(splits["ndvi"].seen_during_design) <= tgroups(shipped, "ndvi")


# ------------------------------------------------------------------------------------------------
# the moved lists: legacy_harness/shipped_splits.yaml and treeroute_report/continuity_groups.yaml
@pytest.mark.parametrize("name", PACKAGES)
def test_shipped_lists_are_sorted_sets_and_disjoint(shipped, name):
    block = shipped[name]
    d, t = block["donor_groups"], block["test_groups"]
    for label, groups in (("donor_groups", d), ("test_groups", t)):
        assert groups == sorted(set(groups)), "%s: %s is not a sorted set" % (name, label)
    assert not set(d) & set(t), "%s: donor and test groups overlap" % name
    assert (len(d), len(t)) == COUNTS[name] == (block["n_donor_groups"], block["n_test_groups"])
    assert block["excluded"] == {}
    cited = {Path(k).name if "/" in k else k.split(" ")[0]: v for k, v in block["source_sha256"].items()}
    for path, digest in SOURCE_SHA256.items():
        if path.name in cited:
            assert cited[path.name] == digest, (name, path.name)
    assert block["source"]


def test_shipped_seen_during_design_matches_the_package(shipped, splits):
    for name in PACKAGES:
        assert (shipped[name]["seen_during_design"] or []) == sorted(splits[name].seen_during_design)


@pytest.mark.parametrize("name", PACKAGES)
def test_continuity_groups_are_the_old_test_groups(shipped, continuity, name):
    row = continuity[name]
    assert row["continuity_groups"] == shipped[name]["test_groups"]
    assert row["n_groups"] == COUNTS[name][1]
    assert row["label"] == "continuity, not a replication"
    exp = json.loads((DATASETS / name / "expected_derived.json").read_text(encoding="utf-8"))
    assert exp["R34_continuity_row"]["groups"] == row["n_groups"]
    assert exp["R18_units_per_group"]["old_test_units"] == row["old_test_units"]


def test_the_engine_reads_neither_moved_list():
    """The old lists live outside the engine (G-IMPORT, G-NONAMES): no engine file names them."""
    for path in (ENGINE_DIR / "treeroute").rglob("*.py"):
        if "_proposed" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert "shipped_splits" not in text and "continuity_groups.yaml" not in text, path


def test_group_universes_nest_inside_the_panel_groups(pkgs, shipped):
    panel = donors(shipped, "ndvi") | tgroups(shipped, "ndvi")
    assert len(panel) == 133
    for name in ("pm25", "fire", "defo"):
        groups = donors(shipped, name) | tgroups(shipped, name)
        assert groups <= panel, "%s groups outside the panel: %s" % (name, sorted(groups - panel))
    # defo = the forested groups of the NDVI split, roles kept (adaptation.py:1215-1219)
    assert donors(shipped, "defo") <= donors(shipped, "ndvi")
    assert tgroups(shipped, "defo") <= tgroups(shipped, "ndvi")
    # the 6 panel groups without an ACAG file are exactly the GFED-absent groups
    no_pm25 = panel - donors(shipped, "pm25") - tgroups(shipped, "pm25")
    gfed = pkgs["ndvi"].stores["../_stores/gfed_burn_schema_catalog.yaml"]
    assert no_pm25 == set(gfed.columns["burn_frac"].absent_groups)


# ------------------------------------------------------------------------------------------------
# the groups under LORO: every group of the target data (read-only store listing)
@pytest.mark.parametrize("name", PACKAGES)
def test_every_group_in_the_target_data_is_trained_and_tested(splits, shipped, name):
    dataset = load_dataset_file(DATASETS / name)
    listing = list_store(dataset.stores.target, base=DATASETS / name)
    if not listing.store_root_exists or not listing.files:
        pytest.skip("target store of %s is not reachable (%s)" % (name, listing.store_root))
    data_groups = tuple(sorted({key[0] for key, _ in listing.files}))
    sets = SP.loro_split_sets(splits[name])
    assert SP.loro_split_differences(sets, data_groups) == SP.LoroSplitDiff((), (), ())
    groups = SP.groups_under_loro(sets, data_groups)
    assert len(groups) == GROUPS_UNDER_LORO[name]
    assert set(groups) == donors(shipped, name) | tgroups(shipped, name)   # nothing new, nothing lost
    exp = json.loads((DATASETS / name / "expected_derived.json").read_text(encoding="utf-8"))
    assert exp["LORO_groups"]["n_groups"] == len(groups)
    report = SP.report_groupings(groups, sets)
    assert report["all"] == groups
    if name == "ndvi":
        assert len(report["without_seen_during_design"]) == 131
    else:
        assert set(report) == {"all"}


# ------------------------------------------------------------------------------------------------
# the old lists: set equality with the shipped sources
def test_pm25_split_equals_the_frozen_module(shipped):
    tree = ast.parse(need(PM25_SPLIT).read_text(encoding="utf-8"))
    found = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("TEST", "DONORS")):
            found[node.targets[0].id] = (set(ast.literal_eval(node.value)), node.lineno, node.end_lineno)
    # the line ranges cited in the shipped lists' provenance
    assert found["TEST"][1:] == (55, 76)
    assert found["DONORS"][1:] == (78, 186)
    assert tgroups(shipped, "pm25") == found["TEST"][0]
    assert donors(shipped, "pm25") == found["DONORS"][0]


def test_ndvi_split_equals_ndvi_split_txt(shipped):
    sections = read_split_txt(need(NDVI_SPLIT))
    # the line ranges cited in the shipped lists' provenance
    assert sorted(sections["donors"]) == list(range(2, 91))
    assert sorted(sections["tests"]) == list(range(92, 136))
    assert donors(shipped, "ndvi") == set(sections["donors"].values())
    assert tgroups(shipped, "ndvi") == set(sections["tests"].values())


def test_fire_split_equals_the_shipped_selection(shipped):
    """fire_evt_arch.py:157-161: complete groups (every year 2002-2022 in D:/fire/target), sorted by
    panel_cells descending, the first 30 are donors, the rest tests."""
    sizes = need(FIRE_SIZES)
    if not FIRE_TARGET.is_dir():
        pytest.skip("D:/fire/target is not on this machine")
    years = {}
    for f in FIRE_TARGET.glob("*.parquet"):
        stem, _, year = f.stem.rpartition("_")
        if year.isdigit() and len(year) == 4:
            years.setdefault(stem, set()).add(int(year))
    complete = {g for g, ys in years.items() if set(range(2002, 2023)) <= ys}
    with open(sizes, encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["region"] in complete]
    rows.sort(key=lambda r: -int(r["panel_cells"]))
    cells = [int(r["panel_cells"]) for r in rows]
    # no tie at the donor boundary, so the sort algorithm cannot change the sets
    assert cells[29] > cells[30]
    assert donors(shipped, "fire") == {r["region"] for r in rows[:30]}
    assert tgroups(shipped, "fire") == {r["region"] for r in rows[30:]}


def test_defo_split_equals_the_shipped_selection(shipped):
    """adaptation.py:1215-1219: forest_census frac_tc30 >= 0.25 (sorted by cells) x ndvi_split; the
    first NDON = 25 forested donors, tests [FROM:FROM + NTEST] = [0:17]."""
    sections = read_split_txt(need(NDVI_SPLIT))
    with open(need(FOREST_CENSUS), encoding="utf-8", newline="") as fh:
        census = list(csv.DictReader(fh))
    forested = [r["region"] for r in sorted((r for r in census if float(r["frac_tc30"]) >= 0.25),
                                            key=lambda r: int(r["cells"]))]
    fd = [g for g in forested if g in set(sections["donors"].values())]
    ft = [g for g in forested if g in set(sections["tests"].values())]
    # both slices take every forested group, so the sort order cannot change the sets
    assert (len(fd), len(ft)) == (25, 17)
    assert donors(shipped, "defo") == set(fd[:25])
    assert tgroups(shipped, "defo") == set(ft[0:17])

# ------------------------------------------------------------------------------------------------
# catalog facts
@pytest.mark.parametrize("name", PACKAGES)
def test_one_target_and_the_key_roles(pkgs, name):
    cols = pkgs[name].catalog.columns
    targets = [c for c, f in cols.items() if f.role == "target"]
    assert targets == [TARGETS[name]]
    assert [c for c, f in cols.items() if f.role == "key_unit"] == ["cell_id"]
    assert [c for c, f in cols.items() if f.role == "key_group"] == ["region"]
    parts = sorted(f.calendar_part for f in cols.values() if f.role == "key_time")
    assert parts == (["month", "year"] if name in MONTHLY else ["year"])
    t = cols[TARGETS[name]]
    assert t.window is not None and t.stamp is not None
    assert t.fact_status == "unverified"


def test_target_legal_ranges_and_error_floors(pkgs):
    cols = {p: pkgs[p].catalog.columns[TARGETS[p]] for p in PACKAGES}
    assert cols["pm25"].legal_range == (0.0, float("inf"))
    assert cols["fire"].legal_range == (0.0, 1.0)
    assert cols["defo"].legal_range == (0.0, 1.0)
    assert cols["ndvi"].legal_range == (-0.2, 1.0)
    for p in ("fire", "defo", "ndvi"):
        assert cols[p].legal_range_source
    # ruled floors only: PM2.5 +-2 ug/m3 (pm25_adaptation.py:144), NDVI +-0.02 (rule R1)
    assert cols["pm25"].measurement_error_floor == 2.0
    assert cols["ndvi"].measurement_error_floor == 0.02
    assert cols["fire"].measurement_error_floor is None
    assert cols["defo"].measurement_error_floor is None


def declared_store_catalogs(pkg):
    """{declared store path template: [include paths of the store catalogs that describe it]}.

    Nothing in the schema links a store path in dataset.yaml to the catalog that describes it (the
    catalog carries only a store name), so this uses the path template each catalog's description
    names. A test heuristic, not an engine rule."""
    s = pkg.dataset.stores
    paths = [s.target, s.static] + list(s.drivers)
    return {p: [inc for inc, cat in pkg.stores.items() if p in (cat.description or "")] for p in paths}


def driver_like(pkg):
    return {c for c, f in pkg.catalog.columns.items() if f.role in ("driver", "target_twin")}


@pytest.mark.parametrize("name", ("pm25", "fire", "ndvi"))
def test_driver_columns_exist_in_the_declared_driver_stores(pkgs, name):
    """Each driver (and twin) is a column of a store catalog that describes a DECLARED driver store,
    not merely of some included catalog; and every include describes a declared store."""
    pkg = pkgs[name]
    by_path = declared_store_catalogs(pkg)
    for path in pkg.dataset.stores.drivers:
        assert len(by_path[path]) == 1, "%s: driver store %s is described by %s" % (name, path, by_path[path])
    stored = set().union(*(set(pkg.stores[by_path[p][0]].columns) for p in pkg.dataset.stores.drivers))
    drivers = driver_like(pkg)
    assert drivers, name
    assert drivers <= stored, sorted(drivers - stored)
    described = {inc for incs in by_path.values() for inc in incs}
    assert described == set(pkg.stores), "includes that describe no declared store: %s" % sorted(
        set(pkg.stores) - described)


# D:/defo_matrix, measured read-only on 2026-09-28 (all 42 files: one schema, 328 columns).
DEFO_MATRIX = Path("D:/defo_matrix")
DEFO_MATRIX_TEMPLATE = "D:/defo_matrix/{group}.parquet"
DEFO_TARGET = Path("D:/defo_target")
PANEL_CATALOG = "../_stores/monthly_panel_v170_schema_catalog.yaml"
# the approved declaration (OWNER_RULINGS_2026-09-28.md C 'Defo store', option b; dataset.yaml 0.2.0)
DEFO_FEATURES_TEMPLATE = "D:/defo_features/{group}_{year}.parquet"
DEFO_STATIC = "D:/defo_features/static/part-0.parquet"
DEFO_TARGET_TEMPLATE = "D:/defo_target/{group}.parquet"
PANEL_TEMPLATE = "D:/monthly_panel/{group}_monthly_{year}.parquet"
DEFO_FEATURES_CATALOG = "features/defo_features_store_catalog.yaml"
# owner ruling K (OWNER_RULINGS_2026-10-05.md section K, 2026-10-06): the small K supplementary store, the SECOND driver
# store (features/build_store_k.py; K2 epo, K3 deeprec_twsa, K5 MOD44B lag 2, K6 the 11 index families after L1 b)
DEFO_K_TEMPLATE = "D:/defo_features_k/{group}_{year}.parquet"
DEFO_K_CATALOG = "features/defo_features_k_store_catalog.yaml"
AGG = ("_mean", "_min", "_max")
# catalog drivers present in the matrix only as lag1_* forms: defo_ban.py's LAG list (:124-137)
DEFO_LAG_ONLY = {
    "V11_mean_ndvi", "V12_mean_evi", "V13_mean_lst_C", "nighttime_lst_C", "V14_mean_albedo", "gpp_kgC_m2",
    "V20_burned_binary", "burn_month_count", "burn_doy_mean", "esacci_sm", "snow_cover_fraction",
    "cloud_frequency_pct", "ntl"}
# catalog drivers absent from the matrix: dropped at build by defo_ban.py's BAN (24) and FREEZE (14)
# lists (defo_matrix.py:305-308)
DEFO_DROPPED_AT_BUILD = {
    "tree_cover_pct", "V15_bare_ground_pct", "V17_herb_cover_pct", "modis_landcover_class",
    "modis_landcover_annual", "cropland_fraction", "shrub_cover_pct_global", "phenology_sos_doy",
    "luh2_cropland", "luh2_pasture", "luh2_range", "luh2_urban", "luh2_forest", "luh2_secondary",
    "deeprec_twsa", "clf_dry", "clf_wet", "co2", "food_price_index", "food_meat", "food_dairy",
    "food_cereals", "food_oils", "food_sugar",
    "dist_pa", "dist_powerplant", "dist_thermal", "dist_coal_mine", "dist_dam", "dist_reservoir",
    "dist_oilgas_well", "built_surface_fraction", "aglw_cattle", "aglw_buffalo", "aglw_horse",
    "aglw_sheep", "aglw_goats", "aglw_total_lsu"}


def test_defo_declares_the_features_store_first_then_the_monthly_panel(pkgs):
    """Owner ruling C 'Defo store' (option b): defo's yearly columns are rebuilt from the monthly panel by the
    package's feature script. The FEATURES store D:/defo_features is the first driver store (the reader takes
    each kept column from the first store that holds it) and the features output; the monthly panel, its
    source, is the second driver store; the static table is the features store's. Each driver store is
    described by exactly one included catalog: the generated features store catalog and the panel catalog.
    D:/defo_matrix is not declared any more (nothing reads it). UPDATED 2026-10-06 (agent C1) for owner ruling K: the
    K supplementary store D:/defo_features_k is the SECOND driver store, described by its generated catalog."""
    pkg = pkgs["defo"]
    s = pkg.dataset.stores
    assert list(s.drivers) == [DEFO_FEATURES_TEMPLATE, DEFO_K_TEMPLATE, PANEL_TEMPLATE]
    assert s.features == DEFO_FEATURES_TEMPLATE
    assert (s.target, s.static) == (DEFO_TARGET_TEMPLATE, DEFO_STATIC)
    assert DEFO_MATRIX_TEMPLATE not in [s.target, s.static, s.features] + list(s.drivers)
    assert set(pkg.stores) == {PANEL_CATALOG, DEFO_FEATURES_CATALOG, DEFO_K_CATALOG}
    by_path = declared_store_catalogs(pkg)
    assert by_path == {DEFO_TARGET_TEMPLATE: [], DEFO_STATIC: [], DEFO_FEATURES_TEMPLATE: [DEFO_FEATURES_CATALOG],
                       DEFO_K_TEMPLATE: [DEFO_K_CATALOG], PANEL_TEMPLATE: [PANEL_CATALOG]}, by_path


def test_defo_catalog_against_the_matrix_columns(pkgs, shipped):
    pq = pytest.importorskip("pyarrow.parquet")
    if not DEFO_MATRIX.is_dir():
        pytest.skip("D:/defo_matrix is not on this machine")
    pkg = pkgs["defo"]
    files = sorted(DEFO_MATRIX.glob("*.parquet"))
    assert {f.stem for f in files} == donors(shipped, "defo") | tgroups(shipped, "defo")
    schemas = {tuple(pq.read_schema(str(f)).names) for f in files}
    assert len(schemas) == 1, "the 42 matrix files no longer share one schema"
    names = set(schemas.pop())
    assert len(names) == 328
    cols = pkg.catalog.columns

    def declared(c):
        return c in cols or any(c.endswith(s) and c[:-len(s)] in cols for s in AGG)

    # owner ruling J4 (OWNER_RULINGS_2026-10-05.md) removed the 33 pre-lagged lag1_* rows (never read, ruling C)
    # and the 101 monthly parents (declared through their aggregates): every OTHER matrix column is declared
    lag1 = {c for c in names if c.startswith("lag1_")}
    assert len(lag1) == 33
    assert sorted(c for c in names if not declared(c)) == sorted(lag1)
    assert not lag1 & set(cols)

    def lag_parent(c):
        rest = c[len("lag1_"):]
        if rest in DEFO_LAG_ONLY:          # single-column parents (burn_doy_mean ends in _mean itself)
            return rest
        return next((rest[:-len(s)] for s in AGG if rest.endswith(s)), rest)

    assert {lag_parent(c) for c in lag1} == DEFO_LAG_ONLY
    assert cols["y"].role == "target_twin"
    assert cols["land_px"].role == "support"
    for c, reason in (("y", "label"), ("forest2000_px", "coproduct"), ("land_px", "coproduct"),
                      ("is_train", "structural")):
        assert c in names
        v = pkg.ban.verdicts[c]
        assert (v.verdict, v.reason) == ("ban", reason), c
    # the catalog drivers the matrix does not hold (the matrix is not read any more, ruling C): pinned as SETS.
    # Since J4 the monthly parents are not catalog rows, so only the annual and static drivers of both lists remain
    def present(c):
        return c in names or any(c + s in names for s in AGG)

    absent = {c for c in driver_like(pkg) if not present(c)}
    lag_only = {c for c in absent if ("lag1_" + c) in names or any("lag1_" + c + s in names for s in AGG)}
    assert lag_only == DEFO_LAG_ONLY & set(cols) == {"burn_doy_mean", "burn_month_count", "ntl"}
    assert absent - lag_only == DEFO_DROPPED_AT_BUILD & set(cols)
    assert DEFO_DROPPED_AT_BUILD - set(cols) == {"deeprec_twsa", "co2", "food_price_index", "food_meat", "food_dairy",
                                                 "food_cereals", "food_oils", "food_sugar"}   # monthly parents
    assert len(absent) == 33


def test_defo_matrix_y_is_an_exact_copy_of_the_target(pkgs):
    """Checked on one group here (costa_rica); the 2026-09-28 measurement covered all 42 groups
    (max |y - loss_frac| = 0.0 over 12,182,814 rows) and found is_train == (year <= 2019)."""
    pd = pytest.importorskip("pandas")
    m, t = DEFO_MATRIX / "costa_rica.parquet", DEFO_TARGET / "costa_rica.parquet"
    if not (m.exists() and t.exists()):
        pytest.skip("D:/defo_matrix or D:/defo_target is not on this machine")
    M = pd.read_parquet(m, columns=["cell_id", "year", "y", "land_px", "is_train"])
    T = pd.read_parquet(t, columns=["cell_id", "year", "loss_frac", "land_px"])
    J = M.merge(T, on=["cell_id", "year"], how="left", suffixes=("", "_t"), validate="one_to_one")
    assert len(J) == len(M) > 0 and J.loss_frac.notna().all()
    assert (J.y.astype("float64") - J.loss_frac.astype("float32").astype("float64")).abs().max() == 0.0
    assert (J.land_px.astype("int64") == J.land_px_t.astype("int64")).all()
    assert ((M.year <= 2019).astype("int8") == M.is_train.astype("int8")).all()


@pytest.mark.parametrize("name", PACKAGES)
def test_every_target_twin_has_a_forced_ban(pkgs, name):
    pkg = pkgs[name]
    for col, facts in pkg.catalog.columns.items():
        if facts.role == "target_twin":
            v = pkg.ban.verdicts.get(col)
            assert v is not None and v.verdict == "ban", "%s: twin %s has no forced ban (plan 1.4)" % (name, col)


# Review-sheet rows (engine/datasets/review/v2/<problem>_columns.csv) that catalog.yaml leaves out,
# as SETS; each is disclosed in the catalog header.
SHEET_ROWS_OMITTED = {
    "pm25": set(),
    "fire": {"n_burned", "n_valid", "n_unmapped", "unmapped_frac",                      # target store
             "ndvi_lag1_anom", "ndvi_cure", "ndvi_ratio_1_3", "ndvi_ratio_1_12",        # fire_ndvi_lags
             "evi_lag1_anom", "evi_cure", "evi_ratio_1_3", "evi_ratio_1_12",
             "mdc", "kbdi", "nesterov", "angstrom_neg", "ffwi", "rh_pct",               # fire_danger
             # owner ruling N S9 a: the declared history store does not build the lag-1 rings (they read label t-1)
             "nbr25km_lag1", "nbr25km_12mo_lag1", "nbr75km_lag1", "nbr75km_12mo_lag1"},
    "defo": {"loss_px"},                                                                 # target store
    "ndvi": {"ctx:climatology"},      # owner ruling N S11: the empty row is removed (the engine builds the normal)
}
# catalog columns that are not review-sheet rows (besides the keys)
# PM2.5's six lag-12 engineered columns (owner ruling J2 a, OWNER_RULINGS_2026-10-05.md): built by the package's
# feature script from parents banned 'incomplete'; they are not review-sheet rows
PM25_LAG12_COLUMNS = {"spei_01m_lag12", "spei_03m_lag12", "spei_06m_lag12", "V06_spei_12m_lag12", "spei_24m_lag12",
                      "amo_lag12"}
# owner ruling L3 (OWNER_RULINGS_2026-10-05.md section L): each monthly package keeps the yearly livestock columns
# through an engineered hold of the real 2021 layer (features/build.py HOLD_PARENTS); not sheet rows
L3_HOLD_COLUMNS = {"%s_hold2021" % p for p in ("aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep",
                                               "aglw_goats", "aglw_total_lsu")}
# fire's J2 (a) lag-12 columns carry the same six names as PM2.5's; NDVI's feature-script lag rows (345 driver lags
# + the 6 lag-12 columns, <base>_lag<k> of a sheet base) are checked by pattern below
CATALOG_NOT_ON_SHEET = {"pm25": PM25_LAG12_COLUMNS | L3_HOLD_COLUMNS, "fire": PM25_LAG12_COLUMNS | L3_HOLD_COLUMNS,
                        "ndvi": set(L3_HOLD_COLUMNS),
                        "defo": {"y", "is_train"}}   # plus the 33 lag1_* columns (checked by prefix)
# defo's yearly columns rebuilt from the monthly panel by aggregate_time (OWNER_RULINGS_2026-09-28.md C
# 'Defo store', option b): declared at the end of defo's catalog.yaml (role engineered), with their store
# facts in this shared catalog. They are aggregates of reviewed parents, so they are not sheet rows.
DEFO_ANNUAL_FEATURES = DATASETS / "_stores" / "defo_annual_features_schema_catalog.yaml"
# owner ruling J2 (a) on defo: one engineered lag column per SPEI/AMO aggregate (features/build.py)
DEFO_J2A_LAG_COLUMNS = {"%s_%s_lag1" % (b, s) for b in ("V06_spei_12m", "spei_01m", "spei_03m", "spei_06m",
                                                         "spei_24m", "amo") for s in ("mean", "min", "max")}
# owner ruling K: the K store's new names (K3 deeprec_twsa_k3_<stat>, K5 <MOD44B parent>_lag2) and ruling L3's six
# aglw_*_hold2021 columns are engineered catalog rows, not review-sheet rows (K2's epo_<stat> and K6's index
# aggregates are rebuilt yearly columns of reviewed parents, already in the seed catalog)
DEFO_K_NEW_NAMES = ({"deeprec_twsa_k3_%s" % s for s in ("mean", "min", "max")}
                    | {"%s_lag2" % p for p in ("V15_bare_ground_pct", "V17_herb_cover_pct", "tree_cover_pct")})


@pytest.mark.parametrize("name", PACKAGES)
def test_catalog_covers_the_review_sheet(pkgs, name):
    path = DATASETS / "review" / "v2" / ("%s_columns.csv" % name)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        sheet = [r["column"] for r in csv.DictReader(fh)]
    assert len(sheet) == len(set(sheet))
    cols = pkgs[name].catalog.columns
    keys = {c for c, f in cols.items() if f.role.startswith("key_")}
    omitted, not_on_sheet = set(SHEET_ROWS_OMITTED[name]), set(CATALOG_NOT_ON_SHEET[name])
    annual = set()
    if name == "defo":
        from treeroute.package.schema import StoreCatalog
        seed = validate_file(DEFO_ANNUAL_FEATURES, StoreCatalog)
        annual = set(seed.columns)
        # owner ruling J4: the 101 monthly parents are reviewed per family on the sheet but declared through
        # their aggregates, not as rows; J2 (a): the engineered lag columns the feature script builds
        parents = {f.derived_from[0] for f in seed.columns.values()}
        assert len(parents) == 101 and parents <= set(sheet)
        omitted |= parents
        not_on_sheet |= DEFO_J2A_LAG_COLUMNS | DEFO_K_NEW_NAMES | L3_HOLD_COLUMNS
    assert set(sheet) - set(cols) == omitted
    extra = set(cols) - set(sheet) - keys
    lag1 = {c for c in extra if c.startswith("lag1_")}
    if name == "defo":
        assert annual and annual <= extra, "every rebuilt yearly column is declared in catalog.yaml"
        assert {cols[c].role for c in annual} == {"engineered"}
        assert not annual & set(sheet) and not annual & lag1
    if name == "ndvi":
        import re
        lag_rows = {c for c in extra if re.fullmatch(r"(.+)_lag(\d+)", c)
                    and re.fullmatch(r"(.+)_lag(\d+)", c).group(1) in sheet}
        assert len(lag_rows) == 351, len(lag_rows)     # 345 driver lags + 6 lag-12 columns (J2 a, J4)
        extra = extra - lag_rows
    assert extra - lag1 - annual == not_on_sheet
    assert len(lag1) == 0                  # defo's 33 lag1_* rows were removed by owner ruling J4


@pytest.mark.parametrize("name", PACKAGES)
def test_co_measured_answers_carry_evidence(pkgs, name):
    for col, facts in pkgs[name].catalog.columns.items():
        if facts.co_measured_with_target is not None:
            assert facts.co_measured_evidence, "%s.%s: co-measured answer without evidence" % (name, col)


def test_owner_ruled_co_measured_facts(pkgs):
    assert pkgs["fire"].catalog.columns["cloud_frequency_pct"].co_measured_with_target is True   # Q3 a
    assert pkgs["ndvi"].catalog.columns["burn_frac"].co_measured_with_target is True             # Q38 b


def test_ndvi_top5_context_is_declared_data_selected_and_test_exposed(pkgs, shipped):
    ndvi = pkgs["ndvi"]
    selected = {c: f.data_selected for c, f in ndvi.catalog.columns.items() if f.data_selected is not None}
    assert len(selected) == 5
    assert all(ndvi.catalog.columns[c].role == "router_context" for c in selected)
    groups = {tuple(ds.groups) for ds in selected.values()}
    assert len(groups) == 1, "the five entries name the same 89 helper groups"
    helpers = set(groups.pop())
    assert len(helpers) == 89
    assert len(helpers & tgroups(shipped, "ndvi")) == 19   # F15: the OLD test groups among the helpers
    # under leave one region out every group is tested, so every helper group is a tested group
    assert helpers <= donors(shipped, "ndvi") | tgroups(shipped, "ndvi")
    exp = json.loads((DATASETS / "ndvi" / "expected_derived.json").read_text(encoding="utf-8"))
    assert set(exp["data_selected_exposure"]["old_test_groups_in_selection"]) == helpers & tgroups(shipped, "ndvi")
    loro_groups = (donors(shipped, "ndvi") | tgroups(shipped, "ndvi")) - set(ndvi.split.excluded)
    assert exp["data_selected_exposure"]["tested_groups_in_selection"] == len(helpers & loro_groups) == 89
    if RUN89_HELPERS.is_dir():
        on_disk = {p.name[len("hmod_"):-len(".npz")] for p in RUN89_HELPERS.glob("hmod_*.npz")}
        assert helpers == on_disk


# ------------------------------------------------------------------------------------------------
# ban.yaml placeholder and exceptions.yaml disclosures
@pytest.mark.parametrize("name", PACKAGES)
def test_ban_file_names_only_catalog_columns_and_bans_the_target(pkgs, name):
    pkg = pkgs[name]
    assert set(pkg.ban.verdicts) <= set(pkg.catalog.columns)
    v = pkg.ban.verdicts[TARGETS[name]]
    assert (v.verdict, v.reason) == ("ban", "label")


@pytest.mark.parametrize("name", PACKAGES)
def test_exception_columns_are_catalog_columns(pkgs, name):
    pkg = pkgs[name]
    for e in pkg.exceptions.entries:
        if e.column is not None:
            assert e.column in pkg.catalog.columns, e.column


def test_the_disclosures_the_plan_names_are_present(pkgs):
    def exposed(name):
        return {(e.kind, e.column or e.check) for e in pkgs[name].exceptions.entries}

    # PM2.5's GFED burn block (Q25 b; plan 7.2)
    assert {("test_exposure", "burn_frac"), ("test_exposure", "burn_lag1")} <= exposed("pm25")
    # fire's <= 2018 cut (Q10 a; plan 7.2): a disclosure about R6, never a timing value
    fire = [e for e in pkgs["fire"].exceptions.entries if e.kind == "test_exposure"]
    assert any(e.check and e.check.startswith("R6") for e in fire)
    # NDVI's top-5 context list: one test_exposure entry per data_selected column, and no other
    ndvi = pkgs["ndvi"]
    selected = {c for c, f in ndvi.catalog.columns.items() if f.data_selected is not None}
    assert {e.column for e in ndvi.exceptions.entries if e.kind == "test_exposure"} == selected
    # defo_matrix's derived sentinels (plan 1.2 example; HEADLINE_RUN_PLAN.md:144)
    assert any(e.kind == "disclosed_defect" and "G-SENTINEL" in (e.check or "")
               for e in pkgs["defo"].exceptions.entries)


OLD_TOP5_CLAIM = "19 of which are NDVI test groups"     # the pre-LORO wording of the group exposure


def test_ndvi_top5_disclosures_name_both_exposures(pkgs, shipped):
    """Plan 1.3 refuses a data_selected list that read rows after the earliest fit cut unless
    exceptions.yaml discloses it (under LORO every group is tested, so the time cut is the test; before,
    reading test groups was refused too). The top-5 list read both the late rows and tested groups, so
    each disclosure names both exposures, and none cites a 3.3 flag as the owner's authority.

    Under leave one region out every group is tested, so the tested groups among run89's 89 helpers
    are every helper that is a package group: all 89 (70 old donors and 19 old test groups; read-only
    check of D:/run89/trained on 2026-09-28). The disclosure must state that count ("89 ... tested
    groups" in one sentence) and must no longer claim only the 19. The 19 old test groups (F15) stay as
    a side check: each one is still named.

    exceptions.yaml is outside the loro build's write scope and still states the pre-LORO 19. While it
    does, this reports xfail (a known understatement, never a pass); any other wording is checked in
    full and fails loudly.
    """
    ndvi = pkgs["ndvi"]
    groups = (donors(shipped, "ndvi") | tgroups(shipped, "ndvi")) - set(ndvi.split.excluded)
    stale = []
    for e in ndvi.exceptions.entries:
        if e.kind != "test_exposure":
            continue
        ds = ndvi.catalog.columns[e.column].data_selected
        # the second exposure and the owner field
        assert ds.latest_date in e.reason and "earliest fit cut" in e.reason
        assert "flag" not in e.owner and "F15" in e.owner
        # side check: the 19 old test groups among the helpers (F15) are each named
        old = sorted(set(ds.groups) & tgroups(shipped, "ndvi"))
        assert len(old) == 19
        missing = [g for g in old if not re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % g, e.reason)]
        assert not missing, "%s: old test groups not named: %s" % (e.column, missing)
        # the LORO count: every helper that is a package group is tested
        tested = len(set(ds.groups) & groups)
        assert tested == 89
        states_loro = re.search(r"\b%d\b[^.]*\btested groups\b" % tested, e.reason) is not None
        if not states_loro and OLD_TOP5_CLAIM in e.reason:
            stale.append(e.column)
            continue
        assert states_loro, "%s: the disclosure must state that all %d helper groups are tested" % (
            e.column, tested)
        assert OLD_TOP5_CLAIM not in e.reason, "%s: still claims only 19 test groups" % e.column
    if stale:
        pytest.xfail("KNOWN (datasets/ndvi/exceptions.yaml, outside the loro build's write scope): %d "
                     "top-5 disclosures still say %r; under leave one region out all 89 helper groups "
                     "are tested groups (19 of them the old test groups). Restate them, e.g. 'all 89 are "
                     "tested groups under leave one region out, 19 of which were NDVI's old test groups'"
                     % (len(stale), OLD_TOP5_CLAIM))


@pytest.mark.parametrize("name", PACKAGES)
def test_drafted_owner_fields_are_marked_unsigned(pkgs, name):
    """The agent drafted these files. An owner field says UNSIGNED unless the owner signed it. UPDATED 2026-10-06:
    owner ruling N S8 (OWNER_RULINGS_2026-10-06.md N) signed the 28 entries that were already true; each of those
    names the ruling. Every other entry stays UNSIGNED (the 17 refreshed ones wait on the owner)."""
    pkg = pkgs[name]
    assert pkg.dataset.owner.startswith("UNSIGNED")
    for e in pkg.exceptions.entries:
        signed_by_n = e.owner.startswith("owner -- signed by the owner 2026-10-06 (ruling N, OWNER_RULINGS_2026-10-06.md,"
                                         " FREEZE_SIGNOFF_SHEET.md S8); basis: ")
        assert signed_by_n or e.owner.startswith("UNSIGNED -- basis: "), "%s: %r reads as a signature" % (name, e.owner)


# ------------------------------------------------------------------------------------------------
# expected_derived.json (plan 3.2; tests only) and AUDIT_CHECKLIST.md
@pytest.mark.parametrize("name", PACKAGES)
def test_expected_derived_windows_are_self_consistent(name):
    exp = json.loads((DATASETS / name / "expected_derived.json").read_text(encoding="utf-8"))
    w = exp["R3_R7_windows"]
    spy = exp["R2_season_key"]["steps_per_year"]
    assert w["test_years"] == list(range(w["y_end"] - 3, w["y_end"] + 1))
    assert w["train_end"] == w["test_years"][0] - 1
    assert w["inner_score"] == list(range(w["train_end"] - 2, w["train_end"] + 1))
    assert w["inner_fit"] == [w["y0"], w["inner_score"][0] - 1]
    rows = exp["R12_valid_rows_per_unit"]
    assert rows["inner_fit"] == spy * (w["inner_fit"][1] - w["inner_fit"][0] + 1)
    assert rows["test_cut"] == spy * (w["train_end"] - w["y0"] + 1)
    assert exp["R10_leads"]["contract_lead_zero"] is True
    assert exp["R12_router_kind"]["value"] == exp["R14_router_design"]["kind"]
    # leave one region out: every group trained and tested; the C16 budget reproduces the scored count
    g = exp["LORO_groups"]
    assert g["all_trained_and_tested"] is True and g["excluded"] == []
    assert g["n_groups"] == GROUPS_UNDER_LORO[name] == g["old_split"]["donor"] + g["old_split"]["test"]
    units = exp["R18_units_per_group"]
    assert units["k_group_equivalents"] == K.K_GROUP_EQUIVALENTS
    assert units["n_groups"] == g["n_groups"]
    banks = {"g%03d" % i: units["bank"] for i in range(g["n_groups"])}
    counts, flags = SP.scored_count_budget(units["bank"], banks, K.K_GROUP_EQUIVALENTS)
    assert set(counts.values()) == {units["scored"]} and flags == ()
    assert units["scored_total"] == units["scored"] * g["n_groups"]
    assert units["scored"] <= units["bank"]
    assert units["ratio_to_old"] == round(units["scored_total"] / units["old_test_units"], 2)
    # overlap blocks: every group in one block; linked pairs sorted; tree columns follow the bank size
    blocks = exp["R14_overlap_blocks"]
    pairs = blocks["linked_pairs"]
    assert blocks["n_blocks"] == g["n_groups"] - len(pairs)     # every measured pair is its own block
    assert all(a < b for a, b, _ in pairs) and pairs == sorted(pairs)
    assert set(blocks["shared_cells"]) == {"%s+%s" % (a, b) for a, b, _ in pairs}
    assert blocks["pairs_that_only_touch"] == [] and "provisional" in blocks["status"]
    cols = exp["R14_tree_columns"]
    assert cols["bank_trees"] == g["n_groups"] * K.TREES_PER_GROUP
    assert cols["one_group_block"] == cols["bank_trees"] - K.TREES_PER_GROUP
    assert cols["two_group_block"] == cols["bank_trees"] - 2 * K.TREES_PER_GROUP
    assert cols["groups_in_two_group_blocks"] == 2 * len(pairs)
    cont = exp["R34_continuity_row"]
    assert cont["groups"] == g["old_split"]["test"]
    assert cont["scored_units"] == cont["groups"] * units["scored"]
    assert exp["R35_band"]["groups"] == g["n_groups"]


def test_expected_derived_values_the_plan_names():
    exp = {p: json.loads((DATASETS / p / "expected_derived.json").read_text(encoding="utf-8"))
           for p in PACKAGES}
    assert {p: exp[p]["R12_router_kind"]["value"] for p in PACKAGES} == {
        "pm25": "per_unit", "fire": "per_unit", "defo": "region", "ndvi": "per_unit"}
    assert {p: tuple(exp[p]["R22_links"]["value"]) for p in PACKAGES} == {
        "pm25": ("identity", "log_c"), "fire": ("identity", "log_c", "arcsine"),
        "defo": ("identity", "log_c", "arcsine"), "ndvi": ("identity",)}
    assert exp["defo"]["R10_leads"]["leads"] == [1]
    # owner ruling I1: 6 and 12 months for every package (annual defo: one merged 1-year lead), as R10 derives
    # them from each package's own season key
    from treeroute.derive import rules as DR
    from treeroute.derive import shapes as DS

    for p in PACKAGES:
        r10 = exp[p]["R10_leads"]
        spy = exp[p]["R2_season_key"]["steps_per_year"]
        kind = DS.SeasonKeyKind.CONSTANT if spy == 1 else DS.SeasonKeyKind.MONTH_OF_YEAR
        plan = DR.derive_r10_leads(DS.SeasonKeySpec(kind, spy), False).value
        assert r10["requested_months"] == [6, 12] == list(plan.requested_months)
        assert r10["leads"] == list(plan.leads) == ([1] if p == "defo" else [6, 12])
        assert r10["merged"] == {str(k): list(v) for k, v in plan.merged.items()}
        assert r10["not_supplied"] == list(plan.not_supplied) == []
        assert not {1, 3} & set(r10["leads"]) or p == "defo"
    assert exp["defo"]["R10_leads"]["merged"] == {"1": [6, 12]}
    assert exp["defo"]["R17_history"]["n_columns"] == 5
    assert exp["ndvi"]["R17_history"]["start_offset_steps"] == 1
    assert exp["fire"]["R3_R7_windows"]["y0"] == 2003
    # leave one region out (plan 3.2): groups, bank and scored units at K = 20, continuity rows
    assert {p: exp[p]["LORO_groups"]["n_groups"] for p in PACKAGES} == {
        "pm25": 127, "fire": 40, "defo": 42, "ndvi": 133}
    assert {p: (exp[p]["R18_units_per_group"]["bank"], exp[p]["R18_units_per_group"]["scored"])
            for p in PACKAGES} == {"pm25": (100, 15), "fire": (100, 50), "defo": (4285, 2040), "ndvi": (100, 15)}
    assert exp["defo"]["R18_units_per_group"]["bank"] == K.REGION_ROUTER_ROW_BUDGET // 14
    assert {p: exp[p]["R18_units_per_group"]["scored_total"] for p in PACKAGES} == {
        "pm25": 1905, "fire": 2000, "defo": 85680, "ndvi": 1995}
    assert {p: exp[p]["R18_units_per_group"]["old_test_units"] for p in PACKAGES} == {
        "pm25": 2000, "fire": 1000, "defo": 70487, "ndvi": 4400}
    assert {p: exp[p]["R34_continuity_row"]["scored_units"] for p in PACKAGES} == {
        "pm25": 300, "fire": 500, "defo": 34680, "ndvi": 660}
    assert {p: exp[p]["R14_tree_columns"]["one_group_block"] for p in PACKAGES} == {
        "pm25": 12600, "fire": 3900, "defo": 4100, "ndvi": 13200}
    # overlap blocks measured on the stores' units (plan 3.2: PM2.5 8 pairs, fire 1, defo 2, NDVI 8 / 125)
    assert {p: (len(exp[p]["R14_overlap_blocks"]["linked_pairs"]), exp[p]["R14_overlap_blocks"]["n_blocks"])
            for p in PACKAGES} == {"pm25": (8, 119), "fire": (1, 39), "defo": (2, 40), "ndvi": (8, 125)}
    assert exp["ndvi"]["R14_overlap_blocks"]["shared_cells"]["australian_mulga+brigalow_belt"] == 8251
    assert exp["fire"]["R14_overlap_blocks"]["link_rule"] == "spacing"
    # fire's history block starts one step earlier (ruling R-D b; the reach-after fact is now declared,
    # unsigned, and R17 is not built yet, so it stays provisional)
    assert exp["fire"]["R17_history"]["start_offset_steps"] == 1
    assert "provisional" in exp["fire"]["R17_history"]["status"]
    # the ruled index lags (rulings R-A a, R-B, R-C a; F4): merged into the store catalog and recomputed
    # below; provisional while the facts are unsigned and derive's R8 waits on M1
    for p in MONTHLY:
        r8 = exp[p]["R8_feature_lags"]
        assert (r8["oni_steps"], r8["tni_steps"], r8["nino_steps"], r8["sst_anom_steps"], r8["co2_steps"]) == (3, 3, 2, 2, 1)
        lags = r8["index_lags_steps"]
        assert len(lags) == 15 and lags["oni"] == 3 and lags["tni"] == 3 and lags["co2"] == 1
        assert {v for c, v in lags.items() if c.startswith(("nino", "sst_anom_"))} == {2}
        assert "provisional" in r8["status"] and "pending" not in r8
    assert exp["pm25"]["R8_feature_lags"]["oni_steps"] == 3                      # plan 3.2: oni 3 months
    # defo: every index column and the two composites lag 1 year on the annual target, as a set
    lag_year = set(exp["defo"]["R8_feature_lags"]["lag_1_year"])
    assert {"V11_mean_ndvi", "V12_mean_evi", "oni", "tni", "co2"} <= lag_year and len(lag_year) == 17
    assert "provisional" in exp["defo"]["R8_feature_lags"]["status"]


# The acceptance values above are the ones the RULES must reproduce (plan 3.2). Where a rule is already
# built (timing.compute_lag for R8's per-column lag; timing.target_reach_offset_steps for R17's offset),
# recompute the value from the package's own facts: the package catalog for the target, the included store
# catalog for each driver (the store-catalog sha256 in dataset.yaml is checked by load_package first).
PANEL_INCLUDE = "../_stores/monthly_panel_v170_schema_catalog.yaml"
TARGET_STEP = {"pm25": "month", "fire": "month", "defo": "year", "ndvi": "month"}


def _step(unit):
    from types import SimpleNamespace as NS
    return NS(kind="regular", length=1, unit=unit)


def _target_view(pkg, unit):
    from types import SimpleNamespace as NS
    (name, facts), = [(c, f) for c, f in pkg.catalog.columns.items() if f.role == "target"]
    return NS(name=name, cadence=_step(unit), stamp=facts.stamp, window=facts.window,
              computed_from=tuple(facts.computed_from), fact_status=facts.fact_status)


@pytest.mark.parametrize("name", MONTHLY)
def test_expected_index_lags_come_out_of_the_timing_rules(pkgs, name):
    from types import SimpleNamespace as NS
    from treeroute.timing import compute_lag

    pkg = pkgs[name]
    exp = json.loads((DATASETS / name / "expected_derived.json").read_text(encoding="utf-8"))
    panel = pkg.stores[PANEL_INCLUDE]
    tgt = _target_view(pkg, TARGET_STEP[name])
    got = {}
    for col in exp["R8_feature_lags"]["index_lags_steps"]:
        facts, pfacts = panel.columns[col], pkg.catalog.columns[col]
        assert pfacts.role == "driver", (name, col)
        view = NS(name=col, cadence=facts.cadence, stamp=facts.stamp, window=facts.window,
                  fact_status=facts.fact_status, co_measured_with_target=pfacts.co_measured_with_target)
        got[col] = compute_lag(view, tgt, tgt.cadence, "nowcast").steps
    assert got == exp["R8_feature_lags"]["index_lags_steps"]


@pytest.mark.parametrize("name", MONTHLY)
def test_expected_l_state_lags_come_out_of_the_timing_rules(pkgs, name):
    """expected_derived.json R8_feature_lags.l_state_lags (added 2026-10-06, rulings J2 and L): every listed KEPT
    column's lag recomputed by timing.compute_lag from the package's facts, the feature script's output facts added
    as the pipeline does (pipeline.data.augment_package); every column listed as not kept is not kept."""
    from types import SimpleNamespace as NS
    from treeroute.pipeline import data as D
    from treeroute.timing import compute_lag

    pkg = pkgs[name]
    exp = json.loads((DATASETS / name / "expected_derived.json").read_text(encoding="utf-8"))
    block = exp["R8_feature_lags"]["l_state_lags"]
    assert "L1 (b)" in block["rulings"] and "L3" in block["rulings"]
    spec = D.package_spec(D.augment_package(pkg, D.feature_outputs(D.load_hook(pkg.root, D.FEATURE_SCRIPT))))
    kept = set(spec.tree_features) | set(spec.context)
    tgt = _target_view(pkg, TARGET_STEP[name])
    got = {}
    for col in block["steps"]:
        assert col in kept, (name, col)
        f = spec.store_facts[col]
        view = NS(name=col, cadence=f.cadence, stamp=f.stamp, window=f.window, fact_status=f.fact_status,
                  co_measured_with_target=pkg.catalog.columns[col].co_measured_with_target)
        got[col] = compute_lag(view, tgt, tgt.cadence, "nowcast").steps
    assert got == block["steps"]
    assert not set(block["not_kept"]) & kept
    # the L1 (b) index windows give one month wherever kept (pdo two: ruling N1, the ERSSTv5 reach); the hold columns
    # one year (L3); lag-12 columns 0 (J2 a)
    assert {got[c] for c in got if c in ("soi", "tna", "tsa", "iod", "ao", "nao", "pna", "wp", "sam", "noi",
                                         "epo", "grace_lwe")} == {1}
    assert got.get("pdo", 2) == 2
    assert {got[c] for c in got if c.endswith("_hold2021")} == {1} and {got[c] for c in got if c.endswith("_lag12")} == {0}


@pytest.mark.parametrize("name", PACKAGES)
def test_expected_history_offset_comes_out_of_the_target_window(pkgs, name):
    from treeroute.timing import target_reach_offset_steps

    exp = json.loads((DATASETS / name / "expected_derived.json").read_text(encoding="utf-8"))
    tgt = _target_view(pkgs[name], TARGET_STEP[name])
    assert target_reach_offset_steps(tgt, tgt.cadence) == exp["R17_history"]["start_offset_steps"]


@pytest.mark.parametrize("name", PACKAGES)
def test_audit_checklist_lists_the_plan_checks(name):
    text = (DATASETS / name / "AUDIT_CHECKLIST.md").read_text(encoding="utf-8")
    for phrase in ("Target lineage and co-products", "Fill codes", "Compositing-window dating",
                   "Product vintages", "Split design", "The unit definition (as delivered)",
                   "not chosen from target values after the donor train end", "Signed:"):
        assert phrase in text, "%s: %r missing" % (name, phrase)
