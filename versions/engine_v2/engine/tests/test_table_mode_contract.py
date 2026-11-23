"""The table option's package contract (SPEC_TABLE_MODE.md 1, 2.1, 5.1-5.2): the dataset.yaml input field, the six
table key roles, the cross-file rule, every grid package unchanged, and each contract check refusing with its id."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from conftest import ENGINE_DIR
from table_toy import REFUSAL_VARIANTS, build_toy_table_package

LIVE_ENGINE = Path(r"C:\Users\moh the ghost\Desktop\data set for reserch paper\engine")


def _dataset(text):
    from treeroute.package import schema as S

    import yaml
    return S.DatasetFile.model_validate(yaml.safe_load(textwrap.dedent(text)))


def test_input_defaults_to_grid_and_a_grid_needs_its_static_table():
    d = _dataset("""
        name: p
        version: '1'
        owner: o
        description: d
        stores: {target: 'a/{group}.parquet', static: 's.parquet'}
        """)
    assert d.input == "grid"
    with pytest.raises(Exception, match="static"):
        _dataset("""
            name: p
            version: '1'
            owner: o
            description: d
            stores: {target: 'a/{group}.parquet'}
            """)
    with pytest.raises(Exception, match="table package"):
        _dataset("""
            name: p
            version: '1'
            owner: o
            description: d
            stores: {target: 'a/lead_{lead}.parquet', static: 's.parquet'}
            """)


@pytest.mark.parametrize("stores, why", [
    ("{target: 'a/lead_{lead}_{group}.parquet'}", "exactly one placeholder"),
    ("{target: 'a/lead.parquet'}", "exactly one placeholder"),
    ("{target: 'a/lead_{lead}.parquet', static: 's.parquet'}", "takes no static"),
    ("{target: 'a/lead_{lead}.parquet', drivers: ['d.parquet']}", "takes no drivers"),
])
def test_a_table_dataset_names_one_lead_template_and_no_store(stores, why):
    with pytest.raises(Exception, match=why):
        _dataset("""
            name: p
            version: '1'
            owner: o
            description: d
            input: table
            stores: %s
            """ % stores)
    ok = _dataset("""
        name: p
        version: '1'
        owner: o
        description: d
        input: table
        stores: {target: 'a/lead_{lead}.parquet'}
        """)
    assert ok.input == "table" and ok.stores.static is None


def test_the_ok_toy_loads_and_its_contract_holds(tmp_path):
    from treeroute.package import table as T
    from treeroute.package.load import load_package

    pkg = build_toy_table_package(tmp_path)
    loaded = load_package(pkg)
    spec = T.table_spec(loaded)
    assert spec.tree_features == ("f1", "f2", "f3", "f4", "f5", "f6")
    assert spec.context == ("c_season", "c_aux") and spec.strata == ("source",)
    data = T.read_tables(loaded, spec, T.table_leads())
    assert T.table_leads() == (0, 183, 365)
    assert list(data.row_ids) == sorted(data.row_ids.tolist())
    assert tuple(data.grid.unit_ids) == tuple(data.row_ids.tolist()) and int(data.grid.n_steps) == 1
    assert data.leads[0].present.all() and not data.leads[365].present.all()
    for L, lt in data.leads.items():
        assert lt.max_feature_end_gap == -1
        p = lt.present
        assert (lt.issue_day[p] == data.target_day[p] - L).all()


def test_the_nine_key_columns_never_reach_apply_verdicts(tmp_path, monkeypatch):
    from treeroute.io import apply as A
    from treeroute.package import table as T
    from treeroute.package.load import load_package

    seen = []
    real = A.apply_verdicts

    def spy(columns, verdicts, roles):
        seen.append(tuple(columns))
        return real(columns, verdicts, roles)
    monkeypatch.setattr(A, "apply_verdicts", spy)
    spec = T.table_spec(load_package(build_toy_table_package(tmp_path)))
    keys = {spec.row_col, spec.package_unit_col, spec.group_col, spec.lat_col, spec.lon_col, spec.time_col,
            spec.issue_col, spec.feature_end_col, spec.mark_col}
    assert seen and not (set(seen[0]) & keys)


CONTRACT_VARIANTS = sorted(v for v, c in REFUSAL_VARIANTS.items()
                           if c.startswith("T-") and c != "T-MARK" or v in ("missing_role", "reach_on_target",
                                                                             "grid_role_in_table"))


@pytest.mark.parametrize("variant", CONTRACT_VARIANTS)
def test_each_contract_variant_refuses_with_its_check(tmp_path, variant):
    from treeroute.errors import PackageError, RefusedError
    from treeroute.package import table as T
    from treeroute.package.load import load_package

    pkg = build_toy_table_package(tmp_path, variant)
    want = REFUSAL_VARIANTS[variant]
    with pytest.raises((RefusedError, PackageError)) as info:
        loaded = load_package(pkg)
        spec = T.table_spec(loaded)
        T.read_tables(loaded, spec, T.table_leads())
    text = str(info.value)
    assert want in text or (want == "U1" and ("table key role" in text or "U1" in text)), text


@pytest.mark.parametrize("variant", ["train_in_test", "test_before_window", "one_site_group", "empty_group_at_cut"])
def test_each_derive_variant_refuses_with_its_rule(tmp_path, variant):
    from treeroute.derive.table import derive_all_table
    from treeroute.errors import RefusedError
    from treeroute.package import table as T
    from treeroute.package.load import load_package

    loaded = load_package(build_toy_table_package(tmp_path, variant))
    spec = T.table_spec(loaded)
    data = T.read_tables(loaded, spec, T.table_leads())
    with pytest.raises(RefusedError) as info:
        derive_all_table(loaded, spec, data, T.table_leads())
    want = REFUSAL_VARIANTS[variant]
    assert want in str(info.value) or (want == "T-MARK" and "R5" in str(info.value)), str(info.value)


def test_a_grid_package_may_not_declare_a_table_key_role(tmp_path):
    from treeroute.errors import PackageError
    from treeroute.package.load import load_package

    pkg = build_toy_table_package(tmp_path)
    text = (pkg / "dataset.yaml").read_text(encoding="utf-8").replace("input: table\n", "")
    text = text.replace("'data/lead_{lead}.parquet'", "'data/lead_0.parquet'\n  static: 'data/lead_0.parquet'")
    (pkg / "dataset.yaml").write_text(text, encoding="utf-8")
    with pytest.raises(PackageError, match="table key role"):
        load_package(pkg)


_FINGERPRINTS = """
import json, sys
from pathlib import Path
from treeroute.package.load import load_package
out = {}
for d in sorted(Path(sys.argv[1]).iterdir()):
    if not (d / 'dataset.yaml').is_file():
        continue
    try:
        p = load_package(d)
        dump = p.dataset.model_dump()
        dump.pop('input', None)
        if dump.get('stores', {}).get('static') is None:
            dump.get('stores', {}).pop('static', None)
        out[d.name] = [p.fingerprint, json.dumps(dump, sort_keys=True, default=str),
                       json.dumps(p.catalog.model_dump(), sort_keys=True, default=str)]
    except Exception as exc:
        out[d.name] = ['refused', type(exc).__name__]
print(json.dumps(out))
"""


def test_every_grid_package_loads_as_it_does_in_live():
    """5.1 / 5.2: every package in the build copy's datasets/ gives the same fingerprint and the same dataset and
    catalog fields under the build engine as under LIVE's engine (LIVE is only imported, with -B: no bytecode is
    written there)."""
    if not LIVE_ENGINE.is_dir():
        pytest.skip("the LIVE engine is not on this machine")

    def run(cwd):
        r = subprocess.run([sys.executable, "-B", "-c", _FINGERPRINTS, str(ENGINE_DIR / "datasets")], cwd=str(cwd),
                           capture_output=True, text=True, timeout=600, env=dict(__import__("os").environ,
                                                                                 PYTHONDONTWRITEBYTECODE="1"))
        assert r.returncode == 0, r.stderr[-2000:]
        return json.loads(r.stdout.strip().splitlines()[-1])
    build = run(ENGINE_DIR)
    live = run(LIVE_ENGINE)
    shared = sorted(set(build) & set(live))
    assert shared
    for name in shared:
        if live[name][0] == "refused":
            continue                                    # a package LIVE refuses (a table draft) is not a grid package
        assert build[name] == live[name], name
