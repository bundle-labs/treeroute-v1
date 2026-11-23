"""Owner ruling Z1: an accepted engine difference, kept as DATA in rivals.yaml per RUN ID (export.py
accepted_differences / acceptance_for / check_engine / check_identity_after_derive / check_banks).

The grid toy run (made under LIVE) is copied and made to look like a run of an OLDER engine: its manifest names a
fake engine (file sha A through a fake freeze lock) and another engine-constants hash, and its fingerprint is
rebuilt by the engine's own formula, as that engine would have written it. A fake lineage proves B -> LIVE; the
hop A -> B has no proof and only the acceptance can carry it. Then:
  - with the entry: the export passes, records the acceptance, and every parity check P1-P15 passes;
  - without it, for another run fingerprint, with a changed evidence file, for another LIVE: I4 / ACCEPT refuse;
  - one more config difference, or the accepted key at another value: I5 refuses;
  - a P15 failure (the run's recorded bank fingerprint edited) or a skipped check (a dry pass): refuses;
  - malformed config blocks refuse ACCEPT; the production entry for the pm25 headline validates and carries I4.
No refusal writes an export_manifest.json.
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml

from rivals.tests import toy_runs as T

A, B = "a" * 64, "b" * 64
STRIPPED_A = "5" * 64
OLD_CONSTANTS = "d" * 64
RULING = "Z1-test"
PRODUCTION = T.BUILD_ROOT / "rivals_production.yaml"
PM25_RUN = Path("D:/treeroute/runs/pm25/headline/20261007_74e67609")


def _live():
    from treeroute.runs.fingerprint import engine_code_sha256
    return engine_code_sha256()


def _constants_now():
    from treeroute import engine_constants as K
    return K.constants_hash()


def _fingerprint(man):
    """The engine's run fingerprint formula (runs/fingerprint.py run_fingerprint, as export.py I6 rebuilds it)."""
    from treeroute.runs.atomic import dumps_canonical
    return hashlib.sha256(dumps_canonical({"config": man["config"], "engine_code": man["engine_modules"],
                                           "versions": man["versions"], "python": man["python"]})
                          .encode("ascii")).hexdigest()


def _old_engine_copy(toy, case, edit_config=None):
    """A copy of the toy run as an older engine would have written it (see the module text)."""
    run = T.copy_run(toy, case)
    path = run / "manifest.json"
    man = T.read_json(path)
    assert _fingerprint(man) == man["fingerprint"], "the test's fingerprint formula is not the engine's"
    man["engine_modules"] = {"fake/module.py": "0" * 64}
    man["engine_code_hash"] = STRIPPED_A
    man["config"]["engine_constants_sha256"] = OLD_CONSTANTS
    if edit_config:
        edit_config(man["config"])
    man["fingerprint"] = _fingerprint(man)
    path.write_text(json.dumps(man, indent=1, sort_keys=True), encoding="utf-8")
    return run, man


def _proof(path, frm, to, package):
    lines = ["no-op proof (test fake)", "LIVE engine_code_sha256: %s" % frm, "BUILD engine_code_sha256: %s" % to,
             "=== COMPARE %s : old  vs  new" % package,
             "prediction and score files and derived.json byte-identical: 24",
             "MUST-MATCH FILES THAT DIFFER OR ARE MISSING (0):", "RESULT: PASS. test fake."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _entry(run_id, fingerprint, evidence, **over):
    e = {"run_id": run_id, "run_fingerprint": fingerprint, "ruling": RULING, "ruling_source": "test",
         "live_engine_file_sha": _live(), "requires_parity": "P1-P15",
         "I4_hops": [{"from": A, "to": B, "must_match_differences": ["a.json: test"],
                      "evidence": [{"path": Path(evidence).as_posix(), "sha256": T.sha256_file(evidence)}]}],
         "I5_config_keys": [{"key": "engine_constants_sha256", "run": OLD_CONSTANTS, "live": _constants_now()}]}
    e.update(over)
    return e


def _world(toy, case, entries):
    """A case folder: a registry with the toy's protected roots and one freeze lock (A, STRIPPED_A), a lineage
    proving B -> LIVE, and a rivals.yaml with the given accepted-difference entries (a list, or a function of the
    evidence file returning it)."""
    root = toy.base / "z1" / case
    root.mkdir(parents=True)
    reg_old = Path(yaml.safe_load(Path(toy.machine_file).read_text(encoding="utf-8"))["registry_dir"])
    reg = root / "registry"
    (reg / "freeze").mkdir(parents=True)
    shutil.copy(str(reg_old / "protected_roots.txt"), str(reg / "protected_roots.txt"))
    lock = {"engine": {"engine_code_sha256": A, "engine_code_hash_comment_stripped": STRIPPED_A}}
    (reg / "freeze" / "FREEZE_test.lock.json").write_text(json.dumps(lock), encoding="utf-8")
    machine = T.write_machine_yaml(root / "machine.yaml", toy.base / "runs_export_unused", toy.temp_dir, reg)
    X = T.rivals_export()
    hop = X.parse_proof(_proof(root / "proof_b_live.txt", B, _live(), toy.package_name))
    (root / "engine_lineage.json").write_text(json.dumps({"format": X.LINEAGE_FORMAT, "hops": [hop]}),
                                              encoding="utf-8")
    evidence = root / "evidence_a_b.txt"
    evidence.write_text("the owner's accepted hop A -> B (test)\n", encoding="utf-8")
    cfg = T.write_rivals_yaml(root / "rivals.yaml", machine, root / "_export", toy.export_ckpt_root, root / "_out",
                              root / "_moved")
    if callable(entries):
        entries = entries(evidence)
    extra = {"engine_lineage": (root / "engine_lineage.json").as_posix()}
    if entries is not None:
        extra["accepted_engine_differences"] = entries
    with open(cfg, "a", encoding="utf-8") as fh:
        fh.write(yaml.safe_dump(extra, sort_keys=False))
    return cfg, evidence


def _export(toy, run, cfg, leads=(0,), roles=None, p15=None):
    X = T.rivals_export()
    return X.export_run(run, toy.package, ",".join(str(L) for L in leads), roles, cfg, p15=p15)


def _no_manifest(cfg):
    assert not list((Path(cfg).parent / "_export").rglob("export_manifest.json")), \
        "a refused export wrote export_manifest.json"


# ------------------------------------------------------------------------------------------ the accepted path
def test_z1_the_accepted_run_exports_and_passes_p1_p15_at_every_lead(grid_toy):
    run, man = _old_engine_copy(grid_toy, "z1_ok")
    cfg, _ = _world(grid_toy, "z1_ok", lambda ev: [_entry(run.name, man["fingerprint"], ev)])
    dirs = _export(grid_toy, run, cfg, leads=grid_toy.leads)
    assert len(dirs) == len(grid_toy.leads)
    for d in dirs:
        m = T.read_json(d / "export_manifest.json")
        for cid in ["P%d" % i for i in range(1, 16)]:
            res = m["parity"][cid]["result"] if isinstance(m["parity"][cid], dict) else m["parity"][cid]
            assert str(res).startswith("pass"), (d.name, cid, res)
        assert set(m["parity"]["P15"]["banks"]) == ({"refit", "tune"} if m["lead"] == 0 else {"refit", "guardfit"})
        acc = m["engine"]["accepted_difference"]
        assert acc["ruling"] == RULING and acc["run_id"] == run.name and acc["requires_parity"] == "P1-P15"
        assert [(h["from"], h["to"]) for h in acc["I4_hops_accepted_on_the_chain"]] == [(A, B)]
        assert [c["key"] for c in acc["I5_config_keys_accepted"]] == ["engine_constants_sha256"]
        assert [(h["from"], h["to"], bool(h.get("accepted"))) for h in m["engine"]["hops"]] == \
            [(A, B, True), (B, _live(), False)]
        assert m["identity"]["I5"].startswith("pass with 1 key") and m["identity"]["I4"]["result"].startswith("pass")
    # Z check 1 c: the seal is written last and lists every lead's manifest sha256
    from rivals import layout
    seal_p = dirs[0].parent / layout.ACCEPT_SEAL
    seal = T.read_json(seal_p)
    assert seal["format"] == layout.FORMAT_ACCEPT_SEAL and seal["run_id"] == run.name
    assert sorted(int(k) for k in seal["leads"]) == sorted(grid_toy.leads)
    for d in dirs:
        lead = str(T.read_json(d / "export_manifest.json")["lead"])
        assert seal["leads"][lead]["manifest_sha256"] == T.sha256_file(d / "export_manifest.json")
    # Z check 1 d: the harness starts a board only with the seal, and refuses a lead whose manifest is not sealed
    H = T.rivals_harness()
    lead0 = [d for d in dirs if d.name == "lead_0"][0]
    H.init(run, lead0, Path(cfg).parent / "_out_ok", config=cfg)
    hidden = seal_p.with_name("seal_hidden.json")
    seal_p.rename(hidden)
    with pytest.raises(Exception, match="ACCEPTED_ALL_LEADS"):
        H.init(run, lead0, Path(cfg).parent / "_out_noseal", config=cfg)
    hidden.rename(seal_p)
    doc = T.read_json(seal_p)
    last = str(max(grid_toy.leads))
    doc["leads"][last]["manifest_sha256"] = "0" * 64
    seal_p.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(Exception, match="is not the one the seal"):
        H.init(run, lead0, Path(cfg).parent / "_out_badseal", config=cfg)
    del doc["leads"][last]
    seal_p.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(Exception, match="does not cover lead"):
        H.init(run, lead0, Path(cfg).parent / "_out_partseal", config=cfg)
    # every lead must carry the same accepted record (export_identity)
    assert H.export_identity(T.read_json(lead0 / "export_manifest.json"))["accepted_difference"] == acc
    # the board records it (harness board.json engine block -> board.md line)
    line = H._accepted_line({"engine": {"accepted_difference": acc}})
    assert "ACCEPTED ENGINE DIFFERENCE" in line and RULING in line and "engine_constants_sha256" in line
    assert "ACCEPTED" not in H._accepted_line({"engine": {}})


def test_z1_p15_on_a_live_run_with_the_flag(grid_toy):
    """--p15 on a run with no accepted difference: the bank fingerprints reproduce (no acceptance recorded)."""
    root = grid_toy.base / "z1" / "p15_live"
    cfg = T.write_rivals_yaml(root / "rivals.yaml", grid_toy.machine_file, root / "_export",
                              grid_toy.export_ckpt_root, root / "_out", root / "_moved")
    (d,) = _export(grid_toy, grid_toy.run, cfg, leads=(max(grid_toy.leads),), p15=True)
    m = T.read_json(d / "export_manifest.json")
    assert m["parity"]["P15"]["result"] == "pass" and m["engine"]["accepted_difference"] is None


# ------------------------------------------------------------------------------------------ I4 / ACCEPT refusals
def test_z1_without_the_entry_refuses_i4(grid_toy):
    run, _ = _old_engine_copy(grid_toy, "z1_none")
    cfg, _ = _world(grid_toy, "z1_none", None)
    T.expect_refusal("I4", _export, grid_toy, run, cfg)
    _no_manifest(cfg)


def test_z1_an_entry_for_another_fingerprint_refuses(grid_toy):
    run, _ = _old_engine_copy(grid_toy, "z1_fp")
    cfg, _ = _world(grid_toy, "z1_fp", lambda ev: [_entry(run.name, "e" * 64, ev)])
    T.expect_refusal("ACCEPT", _export, grid_toy, run, cfg)
    _no_manifest(cfg)


def test_z1_a_changed_evidence_file_refuses_i4(grid_toy):
    run, man = _old_engine_copy(grid_toy, "z1_ev")
    cfg, evidence = _world(grid_toy, "z1_ev", lambda ev: [_entry(run.name, man["fingerprint"], ev)])
    evidence.write_text(evidence.read_text(encoding="utf-8") + "edited\n", encoding="utf-8")
    text = T.expect_refusal("I4", _export, grid_toy, run, cfg)
    assert "changed since the ruling" in text
    _no_manifest(cfg)


def test_z1_another_live_engine_refuses_i4(grid_toy):
    run, man = _old_engine_copy(grid_toy, "z1_live")
    cfg, _ = _world(grid_toy, "z1_live",
                    lambda ev: [_entry(run.name, man["fingerprint"], ev, live_engine_file_sha="f" * 64)])
    T.expect_refusal("I4", _export, grid_toy, run, cfg)
    _no_manifest(cfg)


# ------------------------------------------------------------------------------------------ I5 refusals
def test_z1_another_config_difference_still_refuses_i5(grid_toy):
    run, man = _old_engine_copy(grid_toy, "z1_other",
                                edit_config=lambda c: c.__setitem__("static_files_sha256", "e" * 64))
    cfg, _ = _world(grid_toy, "z1_other", lambda ev: [_entry(run.name, man["fingerprint"], ev)])
    text = T.expect_refusal("I5", _export, grid_toy, run, cfg, grid_toy.leads)
    assert "in ['static_files_sha256']" in text, text[-600:]
    _no_manifest(cfg)


def test_z1_the_accepted_key_at_another_value_refuses_i5(grid_toy):
    run, man = _old_engine_copy(grid_toy, "z1_val")
    keys = [{"key": "engine_constants_sha256", "run": "c" * 64, "live": _constants_now()}]
    cfg, _ = _world(grid_toy, "z1_val", lambda ev: [_entry(run.name, man["fingerprint"], ev, I5_config_keys=keys)])
    text = T.expect_refusal("I5", _export, grid_toy, run, cfg, grid_toy.leads)
    assert "engine_constants_sha256" in text
    _no_manifest(cfg)


# ------------------------------------------------------------------------------------------ the P1-P15 condition
def test_z1_a_p15_failure_refuses(grid_toy):
    run, man = _old_engine_copy(grid_toy, "z1_p15")
    path = run / "tables.json"
    t = T.read_json(path)
    t["fit_cut_store"]["bank_fingerprint"] = "0" * 64
    path.write_text(json.dumps(t, indent=1, sort_keys=True), encoding="utf-8")
    cfg, _ = _world(grid_toy, "z1_p15", lambda ev: [_entry(run.name, man["fingerprint"], ev)])
    T.expect_refusal("P15", _export, grid_toy, run, cfg, grid_toy.leads)
    _no_manifest(cfg)


def test_z1_a_skipped_check_refuses_accept(grid_toy):
    """An export without the test role skips P6 and P9: under an accepted difference that refuses."""
    run, man = _old_engine_copy(grid_toy, "z1_dry")
    cfg, _ = _world(grid_toy, "z1_dry", lambda ev: [_entry(run.name, man["fingerprint"], ev)])
    text = T.expect_refusal("ACCEPT", _export, grid_toy, run, cfg, grid_toy.leads,
                            ["refit", "tune", "inner", "guardfit", "guard"])
    assert "P6" in text and "P9" in text
    _no_manifest(cfg)


def test_z1_p15_cannot_be_switched_off(grid_toy):
    run, man = _old_engine_copy(grid_toy, "z1_off")
    cfg, _ = _world(grid_toy, "z1_off", lambda ev: [_entry(run.name, man["fingerprint"], ev)])
    T.expect_refusal("ARGS", _export, grid_toy, run, cfg, (0,), None, False)
    _no_manifest(cfg)


# ------------------------------------------------------------------------------------------ the config block
@pytest.mark.parametrize("bad, why", [
    ({"package": "pm25"}, "unknown fields"),
    ({"run_fingerprint": "abc"}, "64-hex"),
    ({"requires_parity": "P1-P14"}, "requires_parity"),
    ({"ruling": ""}, "ruling"),
    ({"I4_hops": [], "I5_config_keys": []}, "non-empty"),
    ({"I4_hops": [{"from": A, "to": B, "must_match_differences": [], "evidence": []}]}, "evidence"),
    ({"I5_config_keys": [{"key": "k", "run": "x", "live": "x"}]}, "nothing to accept"),
])
def test_z1_a_malformed_block_refuses_accept(tmp_path, bad, why):
    from rivals import layout
    X = T.rivals_export()
    ev = tmp_path / "ev.txt"
    ev.write_text("x\n", encoding="utf-8")
    good = _entry("run_x", "1" * 64, ev)
    base = {k: str(tmp_path / k) for k in layout.ROOT_KEYS}
    roots = layout.roots_from_mapping(dict(base, accepted_engine_differences=[good]))
    assert len(X.accepted_differences(roots)) == 1
    entry = dict(good)
    entry.update(bad)
    roots = layout.roots_from_mapping(dict(base, accepted_engine_differences=[entry]))
    text = T.expect_refusal("ACCEPT", X.accepted_differences, roots)
    assert why in text, text
    roots = layout.roots_from_mapping(dict(base, accepted_engine_differences=[good, dict(good)]))
    T.expect_refusal("ACCEPT", X.accepted_differences, roots)


def test_z1_the_production_entry_validates_and_carries_the_pm25_headline_through_i4():
    """The production config's entry parses; its evidence files have their sha256; I4 on the pm25 headline
    manifest (files only: no lock, no derive, no test file) passes with exactly the three accepted hops."""
    from rivals import layout
    X = T.rivals_export()
    roots = layout.load_roots(PRODUCTION)
    entries = X.accepted_differences(roots)
    assert [e["run_id"] for e in entries] == ["20261007_74e67609"]
    e = entries[0]
    assert e["ruling"] == "Z1" and e["requires_parity"] == "P1-P15"
    assert [c["key"] for c in e["I5_config_keys"]] == ["engine_constants_sha256"]
    assert [(h["from"][:8], h["to"][:8]) for h in e["I4_hops"]] == [("7b508557", "1f257395"),
                                                                    ("1f257395", "7a0341ef"),
                                                                    ("7a0341ef", "65a177bc")]
    if not PM25_RUN.is_dir():
        pytest.skip("the pm25 headline run is absent on this machine")
    for h in e["I4_hops"]:
        for ev in h["evidence"]:
            assert T.sha256_file(ev["path"]) == ev["sha256"], ev["path"]
    man = T.read_json(PM25_RUN / "manifest.json")
    assert man["config"]["engine_constants_sha256"] == e["I5_config_keys"][0]["run"]
    assert e["I5_config_keys"][0]["live"] == _constants_now()
    acc = X.acceptance_for(roots, PM25_RUN, man)
    rec = X.check_engine(man, roots, "D:/treeroute/registry", str(man["config"]["package"]), acc)
    assert [bool(h.get("accepted")) for h in rec["hops"]] == [True, True, True, False, False]
    assert rec["hops"][-1]["to"] == _live()
    with pytest.raises(X.ExportRefusal) as exc:                    # and without the entry it refuses I4
        X.check_engine(man, roots, "D:/treeroute/registry", str(man["config"]["package"]), None)
    assert exc.value.check == "I4"


# ------------------------------------------------------------------------------------------ Z check (2026-10-21)
def _manifests(cfg):
    return sorted((Path(cfg).parent / "_export").rglob("export_manifest.json"))


def test_z1_a_subset_of_leads_refuses_args(grid_toy):
    """Z check 1 a: an accepted difference holds for the whole run, so its leads are exported in ONE call."""
    run, man = _old_engine_copy(grid_toy, "z1_subset")
    cfg, _ = _world(grid_toy, "z1_subset", lambda ev: [_entry(run.name, man["fingerprint"], ev)])
    text = T.expect_refusal("ARGS", _export, grid_toy, run, cfg, (0,))
    assert "every lead" in text
    _no_manifest(cfg)


def test_z1_a_failure_at_a_later_lead_leaves_no_usable_lead(grid_toy):
    """Z check 1 b (from the Z1 review): P15 fails at the LAST lead only. No lead of the run is left with an
    export_manifest.json (they are moved aside, never deleted), and there is no seal."""
    from rivals import layout
    run, man = _old_engine_copy(grid_toy, "z1_partial")
    last = max(grid_toy.leads)
    assert last > 0
    path = run / "ladder" / ("lead_%d" % last) / "lead.json"
    lj = T.read_json(path)
    lj["guard_fits"]["bank"]["fingerprint"] = "0" * 64
    path.write_text(json.dumps(lj, indent=1, sort_keys=True), encoding="utf-8")
    cfg, _ = _world(grid_toy, "z1_partial", lambda ev: [_entry(run.name, man["fingerprint"], ev)])
    T.expect_refusal("P15", _export, grid_toy, run, cfg, grid_toy.leads)
    assert _manifests(cfg) == []
    assert not list((Path(cfg).parent / "_export").rglob(layout.ACCEPT_SEAL))
    moved = sorted((Path(cfg).parent / "_moved").rglob("export_manifest.json"))
    assert len(moved) == len(grid_toy.leads) - 1, moved              # the earlier leads' manifests, kept aside


def test_z1_a_not_checkable_p9_link_refuses_accept(grid_toy):
    """Z check 2 (from the Z1 review): P9 marks a link whose trees-off column the run did not save as 'not
    checkable'; under an accepted difference a nested result that is not a pass refuses."""
    import pyarrow.parquet as pq
    run, man = _old_engine_copy(grid_toy, "z1_p9")
    tp = run / "test_preds.parquet"                       # the TOY's file (synthetic)
    tab = pq.read_table(tp)
    drop = [n for n in tab.column_names if n.startswith("pre__") and "trees_off" in n]
    assert drop, tab.column_names
    pq.write_table(tab.drop([drop[0]]), tp)
    cfg, _ = _world(grid_toy, "z1_p9", lambda ev: [_entry(run.name, man["fingerprint"], ev)])
    text = T.expect_refusal("ACCEPT", _export, grid_toy, run, cfg, grid_toy.leads)
    assert "P9" in text and "not checkable" in text
    assert _manifests(cfg) == []


def test_z1_an_entry_that_carries_nothing_refuses_accept(grid_toy):
    """Z check 3 (from the Z1 review): a run made under LIVE passes I4 and I5 on its own; an entry for its run id
    is stale data and refuses, never recorded as an accepted difference."""
    run = T.copy_run(grid_toy, "z1_unused")
    man = T.read_json(run / "manifest.json")
    ev = run.parent / "ev_unused.txt"
    ev.write_text("unused\n", encoding="utf-8")
    root = grid_toy.base / "z1" / "z1_unused"
    cfg = T.write_rivals_yaml(root / "rivals.yaml", grid_toy.machine_file, root / "_export",
                              grid_toy.export_ckpt_root, root / "_out", root / "_moved")
    entry = _entry(run.name, man["fingerprint"], ev,
                   I5_config_keys=[{"key": "engine_constants_sha256", "run": "d" * 64, "live": "e" * 64}])
    with open(cfg, "a", encoding="utf-8") as fh:
        fh.write(yaml.safe_dump({"accepted_engine_differences": [entry]}, sort_keys=False))
    text = T.expect_refusal("ACCEPT", _export, grid_toy, run, cfg, grid_toy.leads)
    assert "without it" in text
    assert _manifests(cfg) == []


def test_z1_parity_results_reads_every_level():
    X = T.rivals_export()
    rec = {"result": "pass", "links": {"a": {"result": "pass"}, "b": {"result": "not checkable: x"}}}
    assert list(X.parity_results(rec)) == ["pass", "pass", "not checkable: x"]
    assert list(X.parity_results("skipped: dry")) == ["skipped: dry"]
