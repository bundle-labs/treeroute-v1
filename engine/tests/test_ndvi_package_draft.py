"""The DRAFT development package datasets/ndvi_draft/ (tests may name problems).

UPDATED 2026-10-06 (agent C1). ndvi_draft is now the NDVI package AS INSTALLED (owner ruling J's ban list, with
rulings K and L), stamped DRAFT by the one generator datasets/_tools/refresh_drafts.py; tests/test_pipeline_draft.py
checks all four drafts against it. This file keeps the NDVI-specific checks.

WHAT WAS RETIRED. Until 2026-10-06 this module generated ndvi_draft from the SHIPPED verdicts of its Q34 review sheet
(review/v2/ndvi_columns.csv) plus the owner's NDVI rulings, with a DRAFT co-measured floor (V20_burned_binary,
snow_cover_fraction, cloud_frequency_pct, cropland_fraction), one catalog row per feature-script lag, and a G-LAG
departure for the 13 unknown-window columns and their 65 lags, frozen at the pre-J package. Ruling J installed the
owner's ban list (which carries the co-measured answers as package facts and the lag rows in the catalog) and ruling
L1 (b) signed the 13 windows, so that generator and its departures describe a run nobody will make. The old draft
was moved aside, not deleted (datasets/_moved_20261006/ndvi_draft/), and this file's earlier text is in
datasets/_moved_20261006/tests_before_draft_refresh/test_ndvi_package_draft.py.
"""

import importlib.util

from conftest import ENGINE_DIR

DATASETS = ENGINE_DIR / "datasets"
NDVI_DIR = DATASETS / "ndvi"
DRAFT_DIR = DATASETS / "ndvi_draft"
KEY_ROLES = ("key_unit", "key_group", "key_time")


def _tool():
    path = DATASETS / "_tools" / "refresh_drafts.py"
    spec = importlib.util.spec_from_file_location("refresh_drafts_for_ndvi_test", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_ndvi_draft_is_the_installed_package_stamped():
    from treeroute.package.load import load_package
    from treeroute.pipeline.draft import draft_status

    R = _tool()
    assert R.differences("ndvi") == []
    draft, real = load_package(DRAFT_DIR), load_package(NDVI_DIR)
    st = draft_status(draft)
    assert st.is_draft and st.stamped_verdicts == len(draft.ban.verdicts) and st.stamp == R.DRAFT_STAMP
    assert {c: (v.verdict, v.reason) for c, v in draft.ban.verdicts.items()} == \
        {c: (v.verdict, v.reason) for c, v in real.ban.verdicts.items()}


def test_the_draft_reads_the_installed_co_measured_answers_and_rulings():
    """The draft's facts are the package's (catalog.yaml copied byte for byte): the co-measured answers ruled under
    J (cloud_frequency_pct, snow_cover_fraction, burn_frac true), the target twin V12_mean_evi and the classifiers
    banned as the package bans them; no DRAFT-only floor remains."""
    from treeroute.package.load import load_package

    draft, real = load_package(DRAFT_DIR), load_package(NDVI_DIR)
    assert (DRAFT_DIR / "catalog.yaml").read_bytes() == (NDVI_DIR / "catalog.yaml").read_bytes()
    for c in ("cloud_frequency_pct", "snow_cover_fraction", "burn_frac"):
        assert draft.catalog.columns[c].co_measured_with_target is True, c
    for c in ("V11_mean_ndvi", "V12_mean_evi", "clf_dry", "clf_wet"):
        assert draft.ban.verdicts[c].verdict == "ban" == real.ban.verdicts[c].verdict, c
    for c, f in draft.catalog.columns.items():
        assert "DRAFT" not in (f.co_measured_evidence or ""), c        # no draft-only facts


def test_the_draft_feature_script_and_static_table_are_the_packages():
    from treeroute.pipeline import data as D

    for rel in ("features/build.py", "ingest/build_static.py", "ingest/target_reader.py", "data/static/part-0.parquet"):
        assert (DRAFT_DIR / rel).read_bytes() == (NDVI_DIR / rel).read_bytes(), rel
    assert D.feature_outputs(D.load_hook(DRAFT_DIR, D.FEATURE_SCRIPT)) == \
        D.feature_outputs(D.load_hook(NDVI_DIR, D.FEATURE_SCRIPT))


def test_every_feature_output_has_a_catalog_row_and_a_verdict():
    """The engine has no verdict family expansion (plan 1.4 is not built), so every feature output needs its own
    catalog row and verdict (G-CLOSED) in the draft as in the package."""
    from treeroute.package.load import load_package
    from treeroute.pipeline import data as D

    pkg = load_package(DRAFT_DIR)
    outputs = D.feature_outputs(D.load_hook(DRAFT_DIR, D.FEATURE_SCRIPT))
    assert outputs
    missing = sorted(c for c in outputs if c not in pkg.catalog.columns or c not in pkg.ban.verdicts)
    assert missing == [], missing[:10]
    non_key = [c for c, f in pkg.catalog.columns.items() if f.role not in KEY_ROLES]
    assert sorted(pkg.ban.verdicts) == sorted(non_key)
