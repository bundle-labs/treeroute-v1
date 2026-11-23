"""T-F11 registry/fire.yaml (SPEC_HUMAN_PARTB.txt 1.1, 2.1-2.4, 2.7; review R-16).

Toy-level (always runs): fire.yaml validates through config.load_registry against the real _schema.yaml (a config
mapping as test_h20_nonames.py:76-83); every product id is in registry/_products.yaml; runners hold no stats,
families or adapter; families in the order F0..F6; the structural contract of section 2 (geff_era5 picked at the
nowcast, geff_seas5 a separate rival picked on its lead-6 guard rows, the runners without a lead-0 row and with a
label-free coverage); the adapter options equal the ones the toy tests run with (fixtures_fire, spec 2.2 / 2.3),
and the refs label store names a product of _products.yaml.

Real data (@realdata, run JSON and parquet SCHEMAS only, no label): board.check_registry_against_run with the fire
run; slim.check_extra_columns; every column of slim.extra_columns(registry) (the union over ALL rivals, which slim
copies at EVERY lead) and every plan history column is in the EXP lead_0, lead_6 AND lead_12 train AND test parquet
schemas; the geff t1 columns and oni / spi are R8 keys with the steps of the facts.
"""

import json

import pytest

from tests_fire import fixtures_fire as FF


@pytest.fixture(scope="module")
def reg():
    C, cfg = FF.real_registry_cfg()
    return C, cfg, C.load_registry(cfg, "fire")


def _rival(registry, rid):
    hits = [r for r in registry["rivals"] if r["id"] == rid]
    assert len(hits) == 1, "registry/fire.yaml names rival %s %d times" % (rid, len(hits))
    return hits[0]


def test_f11_fire_registry_validates_and_names_known_products(reg):
    C, cfg, registry = reg
    assert registry["package"] == "fire"
    assert str(registry.get("run", "")).replace("\\", "/").rstrip("/").endswith("20261017_869d1f38")
    products = C.load_products(cfg)
    ids = [r["id"] for r in registry["rivals"]]
    assert {"geff_era5", "geff_seas5", "enso_lag", "turco_spi"} <= set(ids)
    for r in registry["rivals"]:
        for pid in r.get("products") or []:
            assert pid in products, "rival %s names product %r, not in registry/_products.yaml" % (r["id"], pid)
        tiers = C.lead_tiers(r)
        assert sorted(tiers) == [0, 6, 12], (r["id"], sorted(tiers))
        if r.get("runner"):
            assert r["kind"] == "M"
            assert not r.get("stats") and not r.get("families") and not r.get("adapter"), r["id"]
        else:
            fams = list(r.get("families") or [])
            assert fams == sorted(fams, key=C.FAMILY_ORDER.index), (r["id"], fams)
    store = registry.get("refs_label_store")
    assert isinstance(store, dict) and store.get("product") in products
    for k in ("file_pattern", "unit_column", "year_column", "month_column", "label_column", "dtype"):
        assert k in store, k


def test_f11_rival_structure(reg):
    C, cfg, registry = reg
    era5, seas5 = _rival(registry, "geff_era5"), _rival(registry, "geff_seas5")
    enso, turco = _rival(registry, "enso_lag"), _rival(registry, "turco_spi")
    t = {r["id"]: C.lead_tiers(r) for r in (era5, seas5, enso, turco)}
    assert t["geff_era5"][0]["tier"] == "P" and (era5.get("pick") or C.PICK_NOWCAST) == C.PICK_NOWCAST
    assert t["geff_era5"][12]["tier"] == "none"
    assert t["geff_seas5"][0]["tier"] == "none" and t["geff_seas5"][12]["tier"] == "none"
    assert t["geff_seas5"][6]["tier"] in ("P", "L") and seas5["pick"] == C.PICK_LOWEST_LEAD
    for r in (era5, seas5):
        assert r["kind"] == "I" and list(r["stats"]) == FF.STATS
        assert r["adapter"] == "adapters.fire_geff:build" and r["availability"] == "adapters.fire_geff:availability"
        assert r.get("reads_target_in_test_window") is False and (r.get("coverage") or C.COVERAGE_X) == C.COVERAGE_X
        assert list(r["t1_kind_columns"]) == FF.FWI_T1
        assert "F6" in r["families"]
    assert era5.get("prep") == "adapters.fire_refs_prep:run_prep"
    assert {FF.ERA5_PID, FF.STATIC_PID}.issubset(era5["products"]) and FF.SEAS5_PID not in era5["products"]
    assert {FF.SEAS5_PID, FF.STATIC_PID}.issubset(seas5["products"]) and FF.ERA5_PID not in seas5["products"]
    assert enso["runner"] == "adapters.fire_enso" and turco["runner"] == "adapters.fire_turco"
    for r in (enso, turco):
        assert t[r["id"]][0]["tier"] == "none"
        assert r["pick"] == C.PICK_LOWEST_LEAD and r["coverage"] == C.COVERAGE_ALL
        assert r.get("optional") is True and r.get("products") in ([], None)
    assert list(enso["slim_extra_columns"]) == ["x__oni"] and list(enso["t1_kind_columns"]) == ["oni"]
    assert list(turco["slim_extra_columns"]) == FF.SPI_COLS and list(turco["t1_kind_columns"]) == FF.SPI_T1


def _without_reader(opt):
    o = json.loads(json.dumps(opt))
    o.get("refs_store", {}).pop("target_reader", None)
    return o


def test_f11_toy_options_are_the_registry_options(reg):
    """The adapter tests run with the registry's own option values (spec 2.2 / 2.3; the reader path aside)."""
    C, cfg, registry = reg
    assert _without_reader(_rival(registry, "geff_era5")["options"]) == _without_reader(FF.era5_options())
    assert _rival(registry, "geff_seas5")["options"] == FF.seas5_options()
    reader = _rival(registry, "geff_era5")["options"]["refs_store"]["target_reader"]
    assert FF.Path(reader).resolve() == FF.TARGET_READER.resolve()
    for rid, toy in (("enso_lag", FF.ENSO_OPTIONS), ("turco_spi", FF.TURCO_OPTIONS)):
        opt = _rival(registry, rid)["options"]
        assert set(toy) <= set(opt), (rid, sorted(set(toy) - set(opt)))
        for k, v in toy.items():
            if k != "form":
                assert opt[k] == v, (rid, k, opt[k], v)


# ------------------------------------------------------------------------------------------ real data (schemas)
@pytest.fixture(scope="module")
def real_run(tmp_path_factory):
    from rivals_human.tests import hooks as HK
    LY, H = HK.common_modules(HK.minimal_config(tmp_path_factory.mktemp("f11_cfg")))
    return H.Run(str(FF.RUN_DIR))


@pytest.mark.realdata
def test_f11_registry_fits_the_fire_run(reg, real_run):
    from rivals_human import board as B
    from rivals_human import slim as S
    C, cfg, registry = reg
    B.check_registry_against_run(registry, real_run)
    S.check_extra_columns(registry, real_run)
    assert sorted(real_run.leads) == [0, 6, 12]
    r8 = real_run.derived["R8"]["value"]
    for c in FF.FWI_T1 + FF.SPI_T1:
        assert int(r8[c]["steps"]) == 0, c
    assert int(r8["oni"]["steps"]) == 3


@pytest.mark.realdata
@pytest.mark.parametrize("lead", [0, 6, 12])
def test_f11_extras_and_history_columns_are_in_every_export_schema(reg, real_run, lead):
    import pyarrow.parquet as pq
    from rivals_human import slim as S
    C, cfg, registry = reg
    need = list(S.extra_columns(registry)) + list(S.history_columns(real_run))
    assert "x__oni" in need and "x__spi_03m" in need and "x__hist_last_1" in need
    ld = FF.EXPORT_DIR / ("lead_%d" % lead)
    if not ld.is_dir():
        pytest.fail("the fire export %s is gone (ATTENTION B1: it must stay until the fire slim)" % ld)
    for part in ("train", "test"):
        files = sorted((ld / part).glob("*.parquet"))
        assert len(files) == 40, (lead, part, len(files))
        for p in files:
            names = set(pq.read_schema(str(p)).names)
            missing = [c for c in need if c not in names]
            assert not missing, (lead, part, p.name, missing)
            if part == "test":
                assert "y" not in names
