"""T-F16 plug and predict with the fire files present (SPEC_HUMAN_PARTB.txt 4.4 (4), 5; hard rule "plug and
predict"): the existing scans run unchanged (no new code; they are called here so B3's own run sees them early, and
run again in the ONE suite from their own folders):
- rivals_human/tests/test_h20_nonames.py: the engine's G-NONAMES scanner finds no problem name, year, drive or unit in
  rivals_human/ (the edited maps.py included) and is not blind; every ctx.<name> of adapters/*.py (the fire ones
  included) exists on the tool's AdapterCtx;
- review_tests/test_r02_runner_label_scope.py: the static scan of every adapters/*.py (no .slim / ._hctx / .read_set
  / ._token; fit_labels only with the bare name fit_set).
"""

from tests_fire import fixtures_fire as FF

FIRE_FILES = ("fire_geff.py", "fire_refs_prep.py", "fire_enso.py", "fire_turco.py")


def test_f16_h20_scans_pass_with_the_fire_files(tmp_path):
    from rivals_human.tests import test_h20_nonames as H20
    have = set(p.name for p in (FF.HUMAN_ROOT / "adapters").glob("fire_*.py"))
    assert set(FIRE_FILES) <= have, "adapters/fire_*.py missing: %s" % sorted(set(FIRE_FILES) - have)
    H20.test_h20_the_tool_code_names_no_problem_year_drive_or_unit()
    H20.test_h20_the_scanner_is_not_blind(tmp_path)
    H20.test_h20_every_ctx_call_of_an_adapter_exists_on_the_tool_context()


def test_f16_r02_static_scan_passes_with_the_fire_files():
    path = FF.WRITE_ROOT / "review_tests" / "test_r02_runner_label_scope.py"
    mod = FF.load_module_from(path, "tests_fire_review_r02")
    mod.test_r02_shipped_adapters_use_only_their_own_fit_set()
