"""V6 b (PLAN_V6B.md T3, T4): a table group with no test-marked row is a DONOR-ONLY group. One smoke of the toy's
'donor_only_group' variant (g_a has train rows only): g_a scores nothing (test_preds, per_group.csv, the jackknife,
verdict.json); its trees are in the fit-cut, inner-cut and every lead bank; its row ids sit in the saved pools (never
a test row); it is a decision-surface fold with its own median; the run record and plan list it; the watermarked
report discloses it; overwriting every test label moves no prediction. And pipeline.record.check_scored_units on
small fake run folders: a listed donor-only group passes; an empty scored list with no 'R18:donor_only' still refuses
(the grid behaviour); a donor-only group with a saved row refuses; 'R18:donor_only' naming a group with scored units
refuses."""

import json

import numpy as np
import pandas as pd
import pytest

from table_toy import build_toy_table_package, patch_sklearn, run_toy, set_test_labels


@pytest.fixture(scope="module", autouse=True)
def sklearnex_patched():
    undo = patch_sklearn()
    yield
    undo()


@pytest.fixture(scope="module")
def donor_run(tmp_path_factory):
    base = tmp_path_factory.mktemp("donor_only")
    pkg = build_toy_table_package(base / "pk", "donor_only_group")
    return base, pkg, run_toy(pkg, base)


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_donor_only_group_scores_nothing(donor_run):
    _, _, folder = donor_run
    derived = _json(folder / "derived.json")
    assert derived["R18:donor_only"]["value"] == ["g_a"]
    assert derived["R18:units"]["value"]["scored"]["g_a"] == []
    preds = pd.read_parquet(folder / "test_preds.parquet")
    assert "g_a" not in set(preds["group"]) and set(preds["group"]) == {"g_b", "g_c", "g_d"}
    for L in (183, 365):
        lp = pd.read_parquet(folder / "ladder" / ("lead_%d" % L) / "test_preds.parquet")
        assert "g_a" not in set(lp["group"])
    pg = pd.read_csv(folder / "per_group.csv")
    assert sorted(pg["group"]) == ["g_b", "g_c", "g_d"]
    jk = pd.read_csv(folder / "jackknife.csv")
    assert set(jk.loc[jk["kind"] != "band_pair", "n_groups"].astype(int)) == {3}
    v = _json(folder / "verdict.json")
    assert v["n_groups"] == 3 and v["groups_trained"] == 4
    d = v["donor_only_groups"]
    assert d["groups"] == ["g_a"] and d["count"] == 1 and d["train_rows"] > 0 and d["surface_rows"] > 0
    from treeroute.pipeline import record as REC

    assert REC.check_scored_units(folder) == ()


def test_the_donor_only_group_lends_trees_and_pool_rows(donor_run):
    _, pkg, folder = donor_run
    import pyarrow.parquet as pq

    zero = pq.read_table(str(pkg / "data" / "lead_0.parquet")).to_pandas()
    g_a = set(zero.loc[zero["region"] == "g_a", "row_id"])
    test_rows = set(zero.loc[zero["mark"] == "test", "row_id"])
    assert g_a and not (g_a & test_rows)
    pools = ["pools_decision_surface.parquet", "pools_test_pass.parquet"]
    for L in (183, 365):
        pools += ["ladder/lead_%d/pools_guard.parquet" % L, "ladder/lead_%d/pools_test_pass.parquet" % L]
    for f in pools:
        frame = pd.read_parquet(folder / f)
        ids = set()
        for pool in frame["pool_row_ids"]:
            ids |= set(json.loads(pool))
        assert ids & g_a, f                       # g_a's rows serve the pools
        assert not (ids & test_rows), f           # never a test row
    # g_a's trees: the fit-cut and inner-cut answer stores hold a build of g_a's trees; every bank (fit-cut,
    # inner-cut, each lead's lagtrain and guard banks) has trees of all 4 run groups (corrector coverage counts the
    # groups of the bank's trees)
    tables = _json(folder / "tables.json")
    for store in ("fit_cut_store", "inner_cut_store"):
        assert "g_a" in {b["group"] for b in tables[store]["builds"]}, store
    checks = _json(folder / "decision_checks.json")
    covs = [checks["corrector_coverage"]["fit-cut"], checks["corrector_coverage"]["inner-cut"]]
    for L in (183, 365):
        lead = _json(folder / "ladder" / ("lead_%d" % L) / "lead.json")
        covs += [lead["fits"]["corrector_coverage"], lead["guard"]["corrector_coverage"]]
    assert len(covs) == 6 and all(cov["groups"] == 4 for cov in covs), covs
    assert "g_a" in checks["decline_baseline"]["per_fold_median"]
    assert "g_a" in checks["fold_c"]


def test_the_records_and_the_report_disclose_the_donor_only_group(donor_run, tmp_path, monkeypatch):
    from treeroute_report import table as RT

    _, _, folder = donor_run
    rec = _json(folder / "run_record.json")
    assert rec["donor_only_groups"]["groups"] == ["g_a"] and rec["donor_only_groups"]["count"] == 1
    assert not any(("donor_only" in str(r) or "donor-only" in str(r)) for r in rec.get("departures") or [])  # C3 (i)
    plan = _json(folder / "plan.json")
    assert plan["donor_only_groups"] == ["g_a"] and plan["scored_rows"]["g_a"] == 0
    cont = tmp_path / "continuity_groups.yaml"
    cont.write_text(RT.CONTINUITY_FILE.read_text(encoding="utf-8")
                    + "\ntoy_table:\n  label: none\n  continuity_groups: []\n", encoding="utf-8")
    monkeypatch.setattr(RT, "CONTINUITY_FILE", cont)
    built = RT.build([folder], watermark=True)
    disc = built["frames"]["disclosures"]
    rows = disc[disc["kind"] == "donor_only_groups"]
    assert len(rows) == 1 and "g_a" in rows["text"].iloc[0] and "nothing is scored" in rows["text"].iloc[0]
    assert "g_a" not in set(built["frames"]["per_group"]["group"])


def test_the_plain_record_has_no_disclosure_row():
    from treeroute_report import table as RT

    assert RT._donor_only_disclosure({}) == ""
    assert RT._donor_only_disclosure({"donor_only_groups": {"groups": [], "count": 0, "train_rows": 0}}) == ""
    assert "1 groups" in RT._donor_only_disclosure({"donor_only_groups": {"groups": ["x"], "count": 1,
                                                                          "train_rows": 4}})


def test_overwriting_the_test_labels_moves_no_prediction_with_a_donor_only_group(donor_run, tmp_path_factory):
    _, _, a = donor_run
    base = tmp_path_factory.mktemp("donor_only_probe")
    pkg = build_toy_table_package(base / "pk", "donor_only_group")
    set_test_labels(pkg, 100.0)
    b = run_toy(pkg, base)
    keep = lambda f: f[["unit", "time"] + [c for c in f.columns if c.startswith(("arm__", "placebo__", "pre__"))]  # noqa
                       + [c for c in ("base__donor_median", "base__predict_zero") if c in f.columns]].reset_index(drop=True)
    for f in ["test_preds.parquet"] + ["ladder/lead_%d/test_preds.parquet" % L for L in (183, 365)]:
        assert keep(pd.read_parquet(a / f)).equals(keep(pd.read_parquet(b / f))), f
    for f in ("pools_decision_surface.parquet", "pools_test_pass.parquet", "inner_preds.parquet"):
        assert pd.read_parquet(a / f).equals(pd.read_parquet(b / f)), f
    assert (a / "adoption.json").read_bytes() == (b / "adoption.json").read_bytes()


def test_the_additions_name_nothing():
    import inspect
    import textwrap

    from conftest import ENGINE_DIR
    from nonames_scan import registered_names, scan_python_source
    from treeroute_report import table as RT

    names = registered_names(ENGINE_DIR / "datasets")
    problems = scan_python_source(textwrap.dedent(inspect.getsource(RT._donor_only_disclosure)), names, "disclosure")
    assert not problems, problems


# ------------------------------------------------------------------ T4: check_scored_units on fake run folders
def _fake_run(folder, bank, scored, saved, donor_only=None):
    folder.mkdir(parents=True)
    derived = {"R18:units": {"value": {"bank": bank, "scored": scored}}}
    if donor_only is not None:
        derived["R18:donor_only"] = {"value": list(donor_only)}
    (folder / "derived.json").write_text(json.dumps(derived), encoding="utf-8")
    pd.DataFrame({"unit": [u for u, _ in saved], "group": [g for _, g in saved]}).to_parquet(
        folder / "test_preds.parquet")
    return folder


BANK = {"a": ["a1", "a2"], "b": ["b1", "b2"], "c": ["c1", "c2"]}


def test_check_scored_units_passes_a_listed_donor_only_group(tmp_path):
    from treeroute.pipeline import record as REC

    f = _fake_run(tmp_path / "r", BANK, {"a": [], "b": ["b2"], "c": ["c2"]}, [("b2", "b"), ("c2", "c")], ["a"])
    assert REC.check_scored_units(f) == ()


def test_check_scored_units_refuses_an_unlisted_empty_group(tmp_path):
    from treeroute.errors import RefusedError
    from treeroute.pipeline import record as REC

    f = _fake_run(tmp_path / "r", BANK, {"a": [], "b": ["b2"], "c": ["c2"]}, [("b2", "b"), ("c2", "c")])
    with pytest.raises(RefusedError, match="no scored unit"):
        REC.check_scored_units(f)
    g = _fake_run(tmp_path / "s", BANK, {"a": [], "b": ["b2"], "c": ["c2"]}, [("b2", "b"), ("c2", "c")], [])
    with pytest.raises(RefusedError, match="no scored unit"):
        REC.check_scored_units(g)


def test_check_scored_units_refuses_a_saved_row_of_a_donor_only_group(tmp_path):
    from treeroute.errors import RefusedError
    from treeroute.pipeline import record as REC

    f = _fake_run(tmp_path / "r", BANK, {"a": [], "b": ["b2"], "c": ["c2"]},
                  [("a1", "a"), ("b2", "b"), ("c2", "c")], ["a"])
    with pytest.raises(RefusedError, match="outside the unit lists"):
        REC.check_scored_units(f)


def test_check_scored_units_refuses_a_donor_only_entry_with_scored_units(tmp_path):
    from treeroute.errors import RefusedError
    from treeroute.pipeline import record as REC

    f = _fake_run(tmp_path / "r", BANK, {"a": ["a2"], "b": ["b2"], "c": ["c2"]},
                  [("b2", "b"), ("c2", "c")], ["a"])
    with pytest.raises(RefusedError, match="R18:donor_only"):
        REC.check_scored_units(f)
    g = _fake_run(tmp_path / "s", BANK, {"a": [], "b": ["b2"], "c": ["c2"]}, [("b2", "b"), ("c2", "c")], ["zz"])
    with pytest.raises(RefusedError, match="R18:donor_only"):
        REC.check_scored_units(g)


# ------------------------------------------------------------------ V6 b review fixes (issues 2, 3, 8)
def test_check_g_split_line_says_trained_and_counts_the_donor_only_groups(donor_run, tmp_path):
    """Review issue 2: a table package's G-SPLIT line no longer says 'every one trained and tested'."""
    from treeroute.check import guards as G
    from treeroute.check.table import run_table_quick

    _, pkg, _ = donor_run
    lines = dict(run_table_quick(pkg, echo=lambda s: None).results)
    res = lines["G-SPLIT"]
    assert res.status == G.PASS and "trained and tested" not in res.reason
    assert "1 donor-only" in res.reason and res.details["donor_only_groups"] == 1
    plain = build_toy_table_package(tmp_path / "pk", "ok")
    res0 = dict(run_table_quick(plain, echo=lambda s: None).results)["G-SPLIT"]
    assert res0.status == G.PASS and "0 donor-only" in res0.reason


def test_donor_only_counts_use_valid_labels():
    """Review issue 3: the disclosed train and surface rows count rows with a valid label only."""
    from treeroute.derive.table import donor_only_entry

    groups = ("a", "b", "c", "d")
    g = np.array(["a"] * 4 + ["b", "c", "d"], dtype=object)
    test = np.array([False, False, False, True, True, True, True])
    days = np.array([10, 11, 20, 30, 30, 30, 30])
    valid = np.array([True, False, True, True, True, True, True])
    scored = {"a": (), "b": ("y",), "c": ("z",), "d": ("w",)}
    e = donor_only_entry(groups, scored, g, test, days, 10, 20, valid=valid)
    assert e.inputs["train_rows"] == {"a": 2} and e.inputs["surface_rows"] == {"a": 1}
    assert "valid label" in e.inputs["count_rule"]
    e_any = donor_only_entry(groups, scored, g, test, days, 10, 20)
    assert e_any.inputs["train_rows"] == {"a": 3} and e_any.inputs["count_rule"] == "rows, any label"


def test_touching_variant_puts_g_b_in_g_a_block(tmp_path):
    """Review issue 8: the toy's 'touching' variant now makes {g_a, g_b} one overlap block (derive only)."""
    from treeroute.derive.table import derive_all_table
    from treeroute.package import table as T
    from treeroute.package.load import load_package

    pkg = build_toy_table_package(tmp_path / "pk", "touching")
    loaded = load_package(pkg)
    spec = T.table_spec(loaded)
    data = T.read_tables(loaded, spec, T.table_leads(), tuple(sorted(loaded.split.excluded)))
    derived = derive_all_table(loaded, spec, data, T.table_leads())
    members = [list(m) for m in derived["R14:overlap_blocks"].value.members]
    assert ["g_a", "g_b"] in members and tuple(derived["R18:donor_only"].value) == ()


@pytest.fixture(scope="module")
def touching_donor_run(tmp_path_factory):
    base = tmp_path_factory.mktemp("touching_donor_only")
    pkg = build_toy_table_package(base / "pk", "touching_donor_only")
    return base, pkg, run_toy(pkg, base)


def test_a_donor_only_block_partner_scores_nothing_and_its_block_counts_once(touching_donor_run):
    """Review issue 8: g_b is donor-only AND in the scored g_a's overlap block. g_b scores nothing; the block counts
    once in the blocked jackknife; every drop set holds whole blocks; no pool holds a test row; g_b lends rows."""
    import pyarrow.parquet as pq

    _, pkg, folder = touching_donor_run
    d = _json(folder / "derived.json")
    assert d["R18:donor_only"]["value"] == ["g_b"]
    assert ["g_a", "g_b"] in d["R14:overlap_blocks"]["value"]["members"]
    assert set(pd.read_parquet(folder / "test_preds.parquet", columns=["group"])["group"]) == {"g_a", "g_c", "g_d"}
    for L in (183, 365):
        lp = pd.read_parquet(folder / "ladder" / ("lead_%d" % L) / "test_preds.parquet", columns=["group"])
        assert "g_b" not in set(lp["group"])
    v = _json(folder / "verdict.json")
    assert v["n_groups"] == 3 and v["groups_trained"] == 4 and v["blocked_jackknife"]["n_blocks"] == 3
    zero = pq.read_table(str(pkg / "data" / "lead_0.parquet")).to_pandas()
    grp = dict(zip(zero["row_id"], zero["region"]))
    test_rows = set(zero.loc[zero["mark"] == "test", "row_id"])
    block = {"g_a": {"g_a", "g_b"}, "g_b": {"g_a", "g_b"}, "g_c": {"g_c"}, "g_d": {"g_d"}}
    lent = 0
    for f in ("pools_test_pass.parquet", "pools_decision_surface.parquet"):
        fr = pd.read_parquet(folder / f)
        for rid, pool, drops in zip(fr["row_id"], fr["pool_row_ids"], fr["drop_groups"]):
            pool = set(json.loads(pool))
            drop = set(json.loads(drops)) if isinstance(drops, str) else set(drops)
            assert not (pool & test_rows), (f, rid)
            assert set(block[grp[rid]]) | {x for r in pool for x in block[grp[r]]} <= drop, (f, rid)
            lent += int(grp[rid] in ("g_c", "g_d") and any(grp[r] == "g_b" for r in pool))
    assert lent > 0
