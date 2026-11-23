"""T6: the engine-lineage logic of check I4 (SPEC_RIVALS.md ATTENTION A1, 2.2 I4) on fake chains.

Drives builder A's export.check_engine(manifest, roots, registry_dir, package_name) with a fake registry (one
freeze lock naming the run's file sha), a fake lineage file and fake proof files written in the format of the real
D:/treeroute/coral_build/noop/noop_summary.txt ('LIVE engine_code_sha256:' = the hop's from-engine, 'BUILD
engine_code_sha256:' = its to-engine, one '=== COMPARE <package> :' block per package with its
'MUST-MATCH FILES THAT DIFFER OR ARE MISSING (n):' line, and the closing 'RESULT: PASS' line).
"""

import json

import pytest

from rivals.tests import toy_runs as T

A, B = "a" * 64, "b" * 64
STRIPPED_A = "5" * 64


def _live():
    from treeroute.runs.fingerprint import engine_code_sha256
    return engine_code_sha256()


def _proof(path, frm, to, packages, must_match=0, passed=True):
    lines = ["no-op proof (test fake)", "LIVE engine_code_sha256: %s" % frm, "BUILD engine_code_sha256: %s" % to]
    for pkg in packages:
        lines += ["=== COMPARE %s : old  vs  new" % pkg,
                  "prediction and score files and derived.json byte-identical: 24",
                  "MUST-MATCH FILES THAT DIFFER OR ARE MISSING (%d):" % must_match]
        lines += ["  test_preds.parquet: differs"] * must_match
        lines += ["other files that differ (review; engine hash, fingerprint or times expected) (1):", "  run.log: differs"]
    if passed:
        lines.append("RESULT: PASS. test fake.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class World(object):
    """A fake registry with one freeze lock (run file sha A, stripped STRIPPED_A) and a config whose lineage file
    lists the given proofs."""

    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.registry = tmp_path / "registry"
        (self.registry / "freeze").mkdir(parents=True)
        lock = {"engine": {"engine_code_sha256": A, "engine_code_hash_comment_stripped": STRIPPED_A}}
        (self.registry / "freeze" / "FREEZE_test.lock.json").write_text(json.dumps(lock), encoding="utf-8")
        T.write_registry(self.registry, [tmp_path / "shipped_root"])
        self.machine = T.write_machine_yaml(tmp_path / "machine.yaml", tmp_path / "runs", tmp_path / "temp",
                                            self.registry)
        self.config = T.write_rivals_yaml(tmp_path / "rivals.yaml", self.machine, tmp_path / "_export",
                                          tmp_path / "_export" / "_engine_run_root", tmp_path / "_out",
                                          tmp_path / "_moved")
        self.manifest = {"engine_code_hash": STRIPPED_A, "engine_modules": {"fake/module.py": "0" * 64}}

    def roots(self):
        from rivals import layout
        return layout.load_roots(self.config)

    def lineage(self, proofs):
        X = T.rivals_export()
        hops = [X.parse_proof(p) for p in proofs]
        doc = {"format": X.LINEAGE_FORMAT, "hops": hops}
        (self.tmp / "engine_lineage.json").write_text(json.dumps(doc), encoding="utf-8")

    def check(self, package="toy_pkg"):
        fn = T.need(T.rivals_export(), "check_engine", "A6")
        return fn(self.manifest, self.roots(), self.registry, package)


def test_t6_a_complete_chain_passes(tmp_path):
    w = World(tmp_path)
    live = _live()
    w.lineage([_proof(tmp_path / "p1.txt", A, B, ["other_pkg", "toy_pkg"]),
               _proof(tmp_path / "p2.txt", B, live, ["toy_pkg"])])
    rec = w.check()
    assert [(h["from"], h["to"]) for h in rec["hops"]] == [(A, B), (B, live)]
    assert rec["run_file_sha"] == A


def test_t6_the_same_engine_needs_no_hop(tmp_path, grid_toy):
    from rivals import layout
    man = T.read_json(grid_toy.run / "manifest.json")             # a toy run made under LIVE
    rec = T.rivals_export().check_engine(man, layout.load_roots(grid_toy.config), tmp_path, "synth_ok")
    assert rec["hops"] == []


def test_t6_a_missing_hop_refuses(tmp_path):
    w = World(tmp_path)
    w.lineage([_proof(tmp_path / "p1.txt", A, B, ["toy_pkg"])])     # B -> LIVE is missing
    T.expect_refusal("I4", w.check)


def test_t6_no_lineage_file_refuses(tmp_path):
    w = World(tmp_path)
    T.expect_refusal("I4", w.check)


def test_t6_the_proof_must_name_the_package(tmp_path):
    w = World(tmp_path)
    w.lineage([_proof(tmp_path / "p1.txt", A, B, ["toy_pkg"]),
               _proof(tmp_path / "p2.txt", B, _live(), ["other_pkg"])])
    T.expect_refusal("I4", w.check)


def test_t6_a_package_name_inside_another_name_does_not_count(tmp_path):
    w = World(tmp_path)
    w.lineage([_proof(tmp_path / "p1.txt", A, _live(), ["toy_pkg"])])
    T.expect_refusal("I4", w.check, "toy")


def test_t6_a_proof_with_differing_must_match_files_refuses(tmp_path):
    w = World(tmp_path)
    w.lineage([_proof(tmp_path / "p1.txt", A, _live(), ["toy_pkg"], must_match=2)])
    T.expect_refusal("I4", w.check)


def test_t6_a_proof_without_the_pass_line_refuses(tmp_path):
    w = World(tmp_path)
    w.lineage([_proof(tmp_path / "p1.txt", A, _live(), ["toy_pkg"], passed=False)])
    T.expect_refusal("I4", w.check)


def test_t6_a_changed_proof_file_refuses(tmp_path):
    w = World(tmp_path)
    p1 = _proof(tmp_path / "p1.txt", A, _live(), ["toy_pkg"])
    w.lineage([p1])
    p1.write_text(p1.read_text(encoding="utf-8") + "edited\n", encoding="utf-8")
    T.expect_refusal("I4", w.check)


def test_t6_a_missing_proof_file_refuses(tmp_path):
    w = World(tmp_path)
    p1 = _proof(tmp_path / "p1.txt", A, _live(), ["toy_pkg"])
    w.lineage([p1])
    T.move_aside(p1, tmp_path / "_moved")
    T.expect_refusal("I4", w.check)


def test_t6_the_real_proofs_parse_as_hops():
    """The two recorded proof files (A1) parse: from/to shas, package sections with must-match 0, the PASS line."""
    from pathlib import Path

    X = T.rivals_export()
    for p, frm, to in (("D:/treeroute/coral_build/noop/noop_summary.txt", "65a177bc", "dd7c0984"),
                       ("D:/treeroute/coral_build_v6b/noop/noop_summary.txt", "dd7c0984", "930d961c")):
        if not Path(p).is_file():
            pytest.skip("%s is absent on this machine" % p)
        h = X.parse_proof(p)
        assert h["from"].startswith(frm) and h["to"].startswith(to) and h["result_pass"]
        assert h["packages_must_match"] and all(v == 0 for v in h["packages_must_match"].values()), h
