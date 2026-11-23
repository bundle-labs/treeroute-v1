"""T-H20 plug and predict (SPEC_HUMAN.txt 1.7, 6; as SPECR T14): the engine's own G-NONAMES scanner over the tool
code rivals_human/ (tests excluded; adapters/ and registry/ are where problems are named) finds no problem name, year,
drive or unit; the scanner is not blind. Also a contract check of the parallel build: every ctx.<name> an adapter or
runner uses exists on the tool's AdapterCtx."""

import re
from pathlib import Path

import pytest

from rivals_human.tests import hooks as HK


def _scanner():
    import nonames_scan as S                       # the engine's scanner (engine tests folder), read-only
    return S


def test_h20_the_tool_code_names_no_problem_year_drive_or_unit():
    S = _scanner()
    root = HK.HUMAN_ROOT / "rivals_human"
    code = [p for p in root.rglob("*.py") if not set(p.relative_to(root).parts) & {"tests", "adapters"}]
    assert code, "no tool code yet (builder A)"
    names = S.registered_names(HK.ENGINE_ROOT / "datasets")
    assert {"coral", "fire", "ndvi", "defo", "pm25"} <= names
    found = S.scan_tree(root, names, excluded_dirs=("tests", "adapters", "__pycache__", "_proposed"))
    assert found == [], "\n".join("%s: %s" % f for f in found[:40])


def test_h20_the_scanner_is_not_blind(tmp_path):
    S = _scanner()
    (tmp_path / "bad.py").write_text("LABEL = 'coral'\nYEAR = 2019\nROOT = 'D:/x'\nm = 5 % 12\n", encoding="utf-8")
    found = S.scan_tree(tmp_path, S.registered_names(HK.ENGINE_ROOT / "datasets"))
    text = " ".join(p for _, p in found)
    for what in ("coral", "year", "drive", "12"):
        assert what in text, (what, found)


def _ctx_names_used(paths):
    used = {}
    for p in paths:
        for m in re.finditer(r"\bctx\.([A-Za-z_]\w*)", p.read_text(encoding="utf-8")):
            used.setdefault(m.group(1), set()).add(p.name)
    return used


def test_h20_every_ctx_call_of_an_adapter_exists_on_the_tool_context():
    """Adapters and runners are written in parallel against BUILD_NOTES_shared.txt; a ctx.<name> the tool's
    index.AdapterCtx does not have would fail only on real data. Names an adapter guards with getattr(ctx, ...)
    are optional and listed in OPTIONAL."""
    I = HK.tool("index")
    src = (HK.HUMAN_ROOT / "rivals_human" / "index.py").read_text(encoding="utf-8")
    cls = src[src.index("class AdapterCtx"):]
    cls = cls[:cls.index("\n# ====")] if "\n# ====" in cls else cls
    have = set(dir(I.AdapterCtx))
    for line in cls.splitlines():
        m = re.match(r"\s*((?:self\.\w+\s*,\s*)*self\.\w+)\s*=(?!=)", line)
        if m:
            have |= set(re.findall(r"self\.(\w+)", m.group(1)))
    adapters = sorted((HK.HUMAN_ROOT / "adapters").glob("*.py")) + \
        sorted((HK.HUMAN_ROOT / "rivals_human" / "adapters").glob("*.py"))
    used = _ctx_names_used(adapters)
    optional = set()
    for p in adapters:
        optional |= set(re.findall(r"getattr\(ctx,\s*[\"'](\w+)[\"']", p.read_text(encoding="utf-8")))
    missing = {n: sorted(f) for n, f in used.items() if n not in have and n not in optional}
    assert not missing, "adapters call ctx names the tool's AdapterCtx lacks: %s" % missing


REAL_RUNS = {"pm25": r"D:\treeroute\runs\pm25\headline\20261007_74e67609",
             "ndvi": r"D:\treeroute\runs\ndvi\headline\20261016_d1de3158",
             "defo": r"D:\treeroute\runs\defo\headline\20261017_d71c61f4",
             "coral": r"D:\treeroute\runs\coral\headline\20261020_f3b8e3da"}


def _real_cfg():
    C = HK.tool("config")
    keys = {k: "D:/treeroute/human_rivals_build/_unused" for k in C.ROOT_KEYS + C.PATH_EXTRA_KEYS}
    keys.update(registry_dir=str(HK.HUMAN_ROOT / "registry"), on_disk_products=str(HK.HUMAN_ROOT / "registry" /
                                                                                   "_products.yaml"),
                common_build_root=str(HK.COMMON_ROOT), common_harness_sha256=HK.COMMON_SHA)
    return C, C.load_config(keys)


@pytest.mark.parametrize("pkg", sorted(REAL_RUNS))
def test_h20_the_real_registries_validate_against_the_schema(pkg):
    """registry/<pkg>.yaml of builders B and C against builder A's registry/_schema.yaml and the 1.7 rules."""
    C, cfg = _real_cfg()
    reg = C.load_registry(cfg, pkg)
    assert reg["package"] == pkg and reg["rivals"]
    products = C.load_products(cfg)
    for r in reg["rivals"]:
        for pid in r.get("products") or []:
            assert pid in products, "rival %s names product %r, not in registry/_products.yaml" % (r["id"], pid)


@pytest.mark.realdata
@pytest.mark.parametrize("pkg", sorted(REAL_RUNS))
def test_h20_the_real_registries_fit_their_headline_runs(pkg):
    """Read-only (run JSON files only): every registry lead is a run lead, links and t1_kind_columns exist
    (board.check_registry_against_run). Owner command: HUMAN_REAL=1."""
    C, cfg = _real_cfg()
    LY, H = HK.common_modules(HK.minimal_config(HK.WRITE_ROOT / "pt" / "tests" / "_realdata_cfg"))
    B = HK.tool("board")
    run = H.Run(REAL_RUNS[pkg])
    HK.need(B, "check_registry_against_run", "A10")(C.load_registry(cfg, pkg), run)
