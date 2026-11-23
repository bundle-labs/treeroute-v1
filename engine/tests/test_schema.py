"""Package schema: unknown keys forbidden, G-NOKNOB refusals, structural shapes."""

import pytest
from pydantic import ValidationError

from treeroute.package import schema as S

DATASET = {
    "name": "toy_pkg", "version": "1", "owner": "tester", "description": "one line",
    "stores": {"target": "t/{group}.parquet", "static": "s.parquet"},
}
STORE_COLUMN = {
    "dtype": "float32", "units": "1", "cadence": {"kind": "regular", "length": 1, "unit": "month"},
    "scope": "unit", "stamp": "period_end",
}
# leave one region out (owner rulings D, E L7 b): exclusions and seen_during_design only
SPLIT = {"excluded": {"z": "no coverage"}, "seen_during_design": ["a"]}
BAN = {"verdicts": {"x": {"verdict": "keep", "reason": "r", "evidence": "Part 1"}}}
CATALOG = {"columns": {"y": {"role": "target"}}}
EXCEPTIONS = {"entries": [{"kind": "test_exposure", "column": "x", "decision": "disclose",
                           "reason": "chosen with test data", "owner": "o", "date": "d"}]}

VALID = {
    S.DatasetFile: DATASET,
    S.SplitFile: SPLIT,
    S.BanFile: BAN,
    S.PackageCatalog: CATALOG,
    S.ExceptionsFile: EXCEPTIONS,
    S.StoreCatalog: {"store": "s", "columns": {"x": STORE_COLUMN}},
    S.MachineFile: {"run_root": "/r", "temp_dir": "/t", "registry_dir": "/g"},
}


@pytest.mark.parametrize("model", list(VALID), ids=lambda m: m.__name__)
def test_valid_examples_pass(model):
    model.model_validate(VALID[model])


@pytest.mark.parametrize("model", list(VALID), ids=lambda m: m.__name__)
def test_unknown_key_is_forbidden(model):
    data = dict(VALID[model])
    data["zz_unknown_key"] = 1
    with pytest.raises(ValidationError) as info:
        model.model_validate(data)
    assert "zz_unknown_key" in str(info.value)


DERIVED_KEYS = sorted(set(S.DERIVED_SETTING_TOKENS) | set(S.DERIVED_SETTING_PHRASES))


@pytest.mark.parametrize("model", list(VALID), ids=lambda m: m.__name__)
@pytest.mark.parametrize("key", DERIVED_KEYS)
def test_every_derived_setting_key_is_refused_with_the_rule(model, key):
    data = dict(VALID[model])
    if key in model.model_fields:
        pytest.skip("%r is a declared field of %s" % (key, model.__name__))
    data[key] = 1
    with pytest.raises(ValidationError) as info:
        model.model_validate(data)
    text = str(info.value)
    assert "derived: see derived.json, rule" in text, text
    assert "G-NOKNOB" in text


@pytest.mark.parametrize("key,rule", [
    ("n_trees", "R19"), ("treesPerDonor", "R19"), ("max_features", "R19"), ("maxFeatures", "R19"),
    ("test_years", "R5"), ("train_end", "R6"), ("lead_months", "R10"), ("log_c", "R23"),
    ("router_kind", "R12"), ("hit_tol", "R32/R36"), ("n_jobs", "C14"), ("random_state", "R19"),
    ("cells_per_region", "R18"), ("y0", "R4"),
    # the old command-line knobs of plan 1.7
    ("cells", "R18"), ("dcells", "R18"), ("npd", "R19"), ("mf", "R19"), ("links", "R22"),
    ("levels", "R14"), ("ratios", "R14"), ("alpha", "R14"), ("actx", "R14"), ("calib", "R3-R7"),
    # the plan 1.7 package-file list
    ("router", "R12"), ("penalty", "R14"), ("c", "R23"), ("normal", "R15"), ("windows", "R3-R7"),
    ("inner", "R7"), ("leads", "R10"), ("units", "R18"), ("trees", "R19"), ("depth", "R19"),
    ("sampler", "R19"), ("storage", "plan 1.7 / 4.5"), ("tolerance", "R32/R36"), ("band", "R35"),
    ("selection", "R27"), ("criterion", "R19"), ("weights", "R25"), ("baselines", "R31"),
    ("threads", "C14"), ("seed", "R19"), ("order", "plan 1.7"), ("mode", "plan 1.7"),
    # spellings the first review found without a rule
    ("window", "R3-R7"), ("min_samples_leaf", "R19"), ("leaf", "R19"), ("level", "R14"),
    ("minSamplesLeaf", "R19"), ("ntrees", "R19"), ("maxfeatures", "R19"),
])
def test_knob_spellings_map_to_their_rule(key, rule):
    assert S.derived_setting_rule(key) == rule


@pytest.mark.parametrize("key", ["donors", "tests", "from", "n_donors", "nTests"])
def test_split_count_keys_are_refused_every_group_is_tested(key):
    assert S.derived_setting_rule(key) is None and S.split_set_key(key)
    for model in (S.SplitFile, S.DatasetFile):
        data = dict(VALID[model])
        data[key] = 5
        with pytest.raises(ValidationError) as info:
            model.model_validate(data)
        assert "derived: every group is tested" in str(info.value)
        assert "G-NOKNOB" in str(info.value)


# ---- leave one region out: split.yaml holds exclusions and seen_during_design only (owner rulings D, E) ----
@pytest.mark.parametrize("key", ["donor_groups", "test_groups", "testGroups", "test_set", "donor_set",
                                 "test", "donor", "n_test_groups", "held_out_tests"])
def test_a_donor_or_test_list_is_refused_with_derived_every_group_is_tested(key):
    assert S.split_set_key(key)
    for model in (S.SplitFile, S.DatasetFile, S.ExceptionsFile):
        data = dict(VALID[model])
        data[key] = ["a", "b"]
        with pytest.raises(ValidationError) as info:
            model.model_validate(data)
        text = str(info.value)
        assert "derived: every group is tested" in text, text
        assert "G-NOKNOB" in text and "rules R18-R20" in text
        assert "excluded and seen_during_design" in text


def test_the_old_split_file_is_refused():
    with pytest.raises(ValidationError) as info:
        S.SplitFile.model_validate({"donor_groups": ["a", "b"], "test_groups": ["c"], "excluded": {}})
    assert "derived: every group is tested" in str(info.value)


@pytest.mark.parametrize("key", ["continuity_groups", "continuity", "continuityGroups"])
def test_a_continuity_list_is_refused_with_a_pointer_to_where_it_lives(key):
    assert S.continuity_key(key) and not S.split_set_key(key)
    with pytest.raises(ValidationError) as info:
        S.SplitFile.model_validate(dict(SPLIT, **{key: ["a"]}))
    text = str(info.value)
    assert "legacy_harness/ and treeroute_report/" in text and "G-NOKNOB" in text


def test_split_file_holds_exactly_excluded_and_seen_during_design():
    assert set(S.SplitFile.model_fields) == {"excluded", "seen_during_design"}
    empty = S.SplitFile.model_validate({})
    assert empty.excluded == {} and empty.seen_during_design == []
    full = S.SplitFile.model_validate(SPLIT)
    assert full.excluded == {"z": "no coverage"} and full.seen_during_design == ["a"]
    for bad in ({"excluded": {"z": ""}}, {"seen_during_design": [""]}, {"seen_during_design": "a"},
                {"excluded": ["z"]}):
        with pytest.raises(ValidationError):
            S.SplitFile.model_validate(bad)


def test_split_keys_do_not_catch_ordinary_words():
    for key in ("latest_date", "contest", "attest", "protest_units", "derived_from", "computed_from",
                "test_exposure_kind"):
        assert S.split_set_key(key) == (key == "test_exposure_kind"), key
    assert not S.continuity_key("discontinuity") and not S.continuity_key("continuous")


def test_declared_derived_from_is_not_mistaken_for_the_from_knob():
    S.StoreColumn.model_validate(dict(STORE_COLUMN, derived_from=["x"], operation="lag 1"))
    assert not S.split_set_key("derived_from") and not S.split_set_key("computed_from")


# ---- strict numbers: a string never becomes a number, a float never becomes an int ----
@pytest.mark.parametrize("model,data", [
    (S.StoreColumn, dict(STORE_COLUMN, legal_range=["0", "1"])),
    (S.StoreColumn, dict(STORE_COLUMN, fill_values=["-32768"])),
    (S.StoreColumn, dict(STORE_COLUMN, fill_values=[True])),
    (S.StoreColumn, dict(STORE_COLUMN, legal_range=[1, 0])),
    (S.StoreColumn, dict(STORE_COLUMN, legal_range=[float("nan"), 1])),
    (S.PackageColumn, {"role": "target", "legal_range": [1.0, 0.0]}),
    (S.PackageColumn, {"role": "target", "calibration_through": "2019"}),
    (S.PackageColumn, {"role": "target", "calibration_through": 2019.0}),
    (S.PackageColumn, {"role": "target", "calibration_through": True}),
    (S.PackageColumn, {"role": "target", "measurement_error_floor": "2"}),
    (S.PackageColumn, {"role": "target", "measurement_error_floor": float("inf")}),
    (S.Cadence, {"kind": "regular", "length": "8", "unit": "day"}),
    (S.Cadence, {"kind": "regular", "length": 8.0, "unit": "day"}),
    (S.Window, {"align": "backward", "length": "16", "unit": "day"}),
    (S.Window, {"align": "backward", "length": float("nan"), "unit": "day"}),
    (S.Window, {"align": "unknown", "max_length": float("inf"), "unit": "month"}),
])
def test_numbers_are_strict(model, data):
    with pytest.raises(ValidationError):
        model.model_validate(data)


def test_strict_numbers_still_take_yaml_integers_and_infinity():
    col = S.StoreColumn.model_validate(dict(STORE_COLUMN, legal_range=[0, float("inf")],
                                            fill_values=[-32768, -32767.0],
                                            window={"length": 16, "unit": "day",
                                                    "align": "backward"}))
    assert col.legal_range == (0.0, float("inf"))
    assert col.fill_values == [-32768.0, -32767.0]
    assert col.window.length == 16.0
    assert S.PackageColumn.model_validate(
        {"role": "target", "calibration_through": 2019, "legal_range": [-0.2, 1],
         "measurement_error_floor": 0}).calibration_through == 2019
    assert S.Cadence.model_validate({"kind": "composite_of_year", "length": 8,
                                     "unit": "day"}).length == 8


def test_declared_field_is_not_a_knob_but_the_same_key_elsewhere_is():
    # 'units' is a declared physical fact of a store column ...
    S.StoreColumn.model_validate(STORE_COLUMN)
    # ... but at the top of dataset.yaml it names the unit count, a derived setting
    data = dict(DATASET, units=4285)
    with pytest.raises(ValidationError) as info:
        S.DatasetFile.model_validate(data)
    assert "rule R18" in str(info.value)


def test_nested_knob_is_refused_too():
    data = dict(DATASET, stores={"target": "t", "static": "s", "threads": 8})
    with pytest.raises(ValidationError) as info:
        S.DatasetFile.model_validate(data)
    assert "rule C14" in str(info.value)


def test_misplaced_facts_get_a_pointed_message():
    with pytest.raises(ValidationError) as info:
        S.StoreColumn.model_validate(dict(STORE_COLUMN, role="driver"))
    assert "package fact" in str(info.value)
    with pytest.raises(ValidationError) as info:
        S.PackageCatalog.model_validate({"columns": {"y": {"role": "target", "units": "1"}}})
    assert "store fact" in str(info.value)


def test_ban_reasons_and_evidence():
    ok = {"verdict": "ban", "reason": "trend_proxy", "evidence": "Part 9"}
    S.Verdict.model_validate(ok)
    with pytest.raises(ValidationError):
        S.Verdict.model_validate(dict(ok, reason="looks bad"))
    with pytest.raises(ValidationError):
        S.Verdict.model_validate({"verdict": "lag", "reason": "x", "evidence": "Part 1"})
    with pytest.raises(ValidationError):
        S.Verdict.model_validate({"verdict": "keep", "reason": "x"})  # evidence missing
    S.Verdict.model_validate({"verdict": "keep_unreviewed", "reason": "facts signed"})
    with pytest.raises(ValidationError) as info:
        S.Verdict.model_validate({"verdict": "keep", "reason": "x", "evidence": "P", "lag": 1})
    assert "rule R8" in str(info.value)


def test_cadence_and_window_shapes():
    S.Cadence.model_validate({"kind": "composite_of_year", "length": 8, "unit": "day"})
    S.Cadence.model_validate({"kind": "irregular"})
    for bad in ({"kind": "regular", "unit": "month"},
                {"kind": "composite_of_year", "length": 16, "unit": "month"},
                {"kind": "static", "length": 1, "unit": "year"}):
        with pytest.raises(ValidationError):
            S.Cadence.model_validate(bad)
    S.Window.model_validate({"align": "unknown", "max_length": 3, "unit": "month"})
    S.Window.model_validate({"align": "centred", "length": 3, "unit": "month"})
    for bad in ({"align": "centred"}, {"align": "unknown", "length": 3, "unit": "month"},
                {"align": "backward", "length": 1, "unit": "month", "max_length": 2}):
        with pytest.raises(ValidationError):
            S.Window.model_validate(bad)


def test_key_time_needs_its_calendar_part():
    with pytest.raises(ValidationError):
        S.PackageColumn.model_validate({"role": "key_time"})
    with pytest.raises(ValidationError):
        S.PackageColumn.model_validate({"role": "driver", "calendar_part": "month"})
    S.PackageColumn.model_validate({"role": "key_time", "calendar_part": "day_of_year"})


def test_types_are_not_coerced_silently():
    with pytest.raises(ValidationError):
        S.SplitFile.model_validate({"seen_during_design": [1, 2]})
    with pytest.raises(ValidationError):
        S.StoreColumn.model_validate(dict(STORE_COLUMN, near_sentinel_optout=1))
    with pytest.raises(ValidationError):
        S.SplitFile.model_validate({"excluded": {7: "x"}})


def test_exception_entry_must_name_a_check_or_column_and_cannot_hold_timing():
    entry = dict(EXCEPTIONS["entries"][0])
    entry.pop("column")
    with pytest.raises(ValidationError):
        S.ExceptionsFile.model_validate({"entries": [entry]})
    with pytest.raises(ValidationError):
        S.ExceptionsFile.model_validate({"entries": [dict(EXCEPTIONS["entries"][0], lag=1)]})


def test_description_is_one_line_and_name_is_folder_safe():
    with pytest.raises(ValidationError):
        S.DatasetFile.model_validate(dict(DATASET, description="two\nlines"))
    with pytest.raises(ValidationError):
        S.DatasetFile.model_validate(dict(DATASET, name="../escape"))


def test_models_are_frozen():
    split = S.SplitFile.model_validate(SPLIT)
    with pytest.raises(ValidationError):
        split.seen_during_design = ["z"]
    with pytest.raises(ValidationError):
        split.excluded = {}


def test_json_schema_export_covers_every_file():
    schemas = S.json_schemas()
    assert set(schemas) == set(S.PACKAGE_FILE_MODELS) | {"store_catalog", "machine.yaml"}
    for schema in schemas.values():
        assert schema.get("additionalProperties") is False
