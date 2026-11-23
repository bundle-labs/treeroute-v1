"""G-NONAMES: engine code names no dataset, year, drive letter or unit, and does no month
arithmetic with 12 ('% 12', '* 12.0', divmod(x, 12), np.mod(x, 12), ...).

The scan covers every file under treeroute/ except _proposed/ (proposed signatures, not engine
code; they are scanned when they move into the engine) and __pycache__.
"""

import pytest

from conftest import ENGINE_DIR, TREEROUTE_DIR
from nonames_scan import registered_names, scan_python_source, scan_tree

NAMES = registered_names(ENGINE_DIR / "datasets")


def test_engine_tree_has_no_names_years_drives_units_or_month_arithmetic():
    problems = scan_tree(TREEROUTE_DIR, NAMES)
    assert not problems, "\n".join("%s: %s" % p for p in problems)


# ---- planted faults: the scanner itself must catch each pattern and spare comments ----
PLANTED = [
    ("x = 'the pm2.5 target'", "pm2"),
    ("pm25_rows = 3", "pm25"),
    ("fire_rate = 1", "fire"),
    ("def f():\n    '''uses NDVI'''\n", "ndvi"),
    ("name = 'coral'", "coral"),
    ("TRAIN_END = 2019", "year"),
    ("T_DEC2019 = 5", "year"),
    ("msg = 'test years 2020-23'", "year"),
    ("OUT = 'D:/somewhere'", "drive"),
    ("OUT = r'C:\\\\data'", "drive"),
    ("HIT_TOL_UGM3 = 2.0", "unit"),
    ("label = 'ug/m3'", "u\\s*g"),
    ("m = t % 12", "month arithmetic"),
    ("n = years * 12", "month arithmetic"),
    ("n = 12 * years", "month arithmetic"),
    ("k = t / 12", "month arithmetic"),
    ("n = years * 12.0", "month arithmetic"),
    ("m = t % 12.", "month arithmetic"),
    ("k = 12 / steps", "month arithmetic"),
    ("k = 12.0 // steps", "month arithmetic"),
    ("q, r = divmod(t, 12)", "month arithmetic"),
    ("r = np.mod(t, 12)", "month arithmetic"),
    ("r = math.fmod(t, 12.0)", "month arithmetic"),
    ("n = np.multiply(years, 12)", "month arithmetic"),
    ("free = shutil.disk_usage('D:')", "drive"),
    ("root = Path(\"e:\")", "drive"),
]


@pytest.mark.parametrize("source,needle", PLANTED)
def test_scanner_catches_planted_fault(source, needle):
    problems = scan_python_source(source + "\n", NAMES, "planted")
    assert problems, source
    assert any(needle in problem for _, problem in problems), problems


CLEAN = [
    "x = 1  # origin: pm25_adaptation.py:143 (fire_architecture.py:102), 2019, D:/x, % 12",
    "MONTHS_PER_YEAR = 12",
    "SMOKE_TREES = 12",
    "levels = (0.1, 0.3, 1.0)",
    "fmt = '%Y%m%d'",
    "firing = 1  # not a whole-word name",
    "GIB = float(1 << 30)",
    "rows = 1200",
    "url = 'https://example.org/a'",
    "MONTHS = 12.0",
    "q, r = divmod(t, 7)",
    "x = 12.5 * y",
    "msg = '%s: %s' % (a, b)",
    "tag = 'key: value'",
    "sep = ':'",
]


@pytest.mark.parametrize("source", CLEAN)
def test_scanner_spares_comments_and_generic_code(source):
    assert scan_python_source(source + "\n", NAMES, "clean") == []


def test_registered_names_include_the_five_problems():
    for name in ("pm25", "fire", "defo", "ndvi", "coral"):
        assert name in NAMES
