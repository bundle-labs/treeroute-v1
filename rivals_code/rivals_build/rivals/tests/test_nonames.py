"""T14 (plug and predict): the engine's own G-NONAMES scanner (engine tests/nonames_scan.py) over the rival code.

Scanned: every file under rivals/ except rivals/tests (tests may name problems and paths, as in the engine) and
__pycache__. Registered names = the scanner's base list + every engine dataset package (folder and name).
The data-rule half of T14 is in test_tuning_rules.py.
"""

from rivals.tests import toy_runs as T


def test_t14_the_rival_code_names_no_problem_year_drive_or_unit():
    import nonames_scan as S                       # the engine's scanner, imported read-only

    root = T.BUILD_ROOT / "rivals"
    code = [p for p in root.rglob("*.py") if "tests" not in p.relative_to(root).parts]
    assert code, "no rival code yet (builders A and B)"
    names = S.registered_names(T.ENGINE_ROOT / "datasets")
    assert {"coral", "fire", "ndvi", "defo", "pm25"} <= names
    found = S.scan_tree(root, names, excluded_dirs=("tests", "__pycache__", "_proposed"))
    assert found == [], "\n".join("%s: %s" % f for f in found[:40])


def test_t14_the_scanner_is_not_blind(tmp_path):
    """A planted file with a problem name, a year and a drive letter is found (the scan works on this machine)."""
    import nonames_scan as S

    (tmp_path / "bad.py").write_text("LABEL = 'coral'\nYEAR = 2019\nROOT = 'D:/x'\nm = 5 % 12\n", encoding="utf-8")
    found = S.scan_tree(tmp_path, S.registered_names(T.ENGINE_ROOT / "datasets"))
    text = " ".join(p for _, p in found)
    for what in ("coral", "year", "drive", "12"):
        assert what in text, (what, found)
