"""T-F15 Part A non-regression (SPEC_HUMAN_PARTB.txt ATTENTION B2 / B3, 2.7, 4.4; hard rule "Part A must not
change").

(a) the recipe of common.tool_code_sha (common.py:115-126) over config.code_files() minus adapters/fire_*.py, with the
    bytes of rivals_human/maps.py REPLACED by the baseline copy _moved/<utc>_partB_baseline/rivals_human/maps.py (sha
    f38d7ce7...), equals cd956f1d... (the NDVI human board's tool hash): no other tool file changed;
(b) coral / defo / pm25 / ndvi.yaml and _schema.yaml keep the shas of the spec's facts list;
(c) every Part A product entry of the new _products.yaml equals (parsed) the baseline copy
    _moved/<utc>_partB_baseline/registry/_products.yaml (sha 4e479759...);
(d) realdata: `join --runs CORAL DEFO PM NDVI --pending FIRE` with a config whose table_root is under the basetemp
    (production keys otherwise, incl. common_harness_accepted_boards) writes a RIVALS_TABLE.csv byte-equal to the Part
    619 table (the same --part value, read from that csv's part column). Skipped by the ONE suite; run by the
    separate light realdata command of spec section 5;
(e) the new maps.py differs from the baseline only in the module docstring, Iso.fit, the F6PctRatio class and new
    module constants named F6_*; no Part A registry lists F6 in any families list.
"""

import ast
import hashlib
import json
from pathlib import Path

import pytest

from tests_fire import fixtures_fire as FF

TOOL_SHA_PART_A_NDVI = "cd956f1dbd0f9b0f2ada37c1a27f8212768d94fc6242cab0686bf7c71608a273"
BASELINE_MAPS_SHA = "f38d7ce78ede1b101b5fba89fb4aa89559171e63e1532e60d58bd030acb91a59"
BASELINE_PRODUCTS_SHA = "4e4797597c0a7c76815159d7ce5fa3cf723d2b996d1e3b67a05968136bcb5d1f"
REGISTRY_SHAS = {   # spec facts list (2026-10-25); full values read from SHAS_FOR_PART_A_20261025.txt and the files
    "_schema.yaml": "0d4dbcb7d81e32b901c35395df3fc4f78619493a9d18bb52711f3c6daf7b8ced",
    "coral.yaml": "7e356d61d048f6f81c7d5e16a9ca8541552f268ad4b5cd3b691a824b0787d7c7",
    "defo.yaml": "fe11acf4a39e9500fda82df15364cf819d3e29734fb9e573c71722b1782baedc",
    "pm25.yaml": "5fe8e221190674e5b2d8c972b46acfca819678795d8e48c6600eaf67a3322e2f",
    "ndvi.yaml": "b69537fc7e360da16b5dc60ae827e9a25f509678527695224fa193c20ce5424d",
}
PART_A = ("coral", "defo", "pm25", "ndvi")
PART619_TABLE = Path(r"D:\treeroute\rivals_table\20261025T162302876402Z\RIVALS_TABLE.csv")
RUNS = {"coral": r"D:\treeroute\runs\coral\headline\20261020_f3b8e3da",
        "defo": r"D:\treeroute\runs\defo\headline\20261017_d71c61f4",
        "pm25": r"D:\treeroute\runs\pm25\headline\20261007_74e67609",
        "ndvi": r"D:\treeroute\runs\ndvi\headline\20261016_d1de3158",
        "fire": str(FF.RUN_DIR)}


def _recipe(parts):
    text = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def test_f15a_tool_hash_with_the_baseline_maps_is_the_part_a_hash():
    from rivals_human import common
    from rivals_human import config as C
    files = C.code_files()
    now = [["%s/%s" % (p.parent.name, p.name), FF.sha256_file(p)] for p in files]
    assert _recipe(now) == common.tool_code_sha()                       # the recipe is the tool's own
    base = FF.baseline_file("rivals_human/maps.py", BASELINE_MAPS_SHA)
    parts = []
    for p in files:
        if p.parent.name == "adapters" and p.name.startswith("fire_"):
            continue
        b = base.read_bytes() if (p.parent.name == "rivals_human" and p.name == "maps.py") else p.read_bytes()
        parts.append(["%s/%s" % (p.parent.name, p.name), hashlib.sha256(b).hexdigest()])
    assert _recipe(parts) == TOOL_SHA_PART_A_NDVI, "a tool file other than maps.py / adapters/fire_*.py changed"


def test_f15b_part_a_registries_and_schema_unchanged():
    for name, sha in REGISTRY_SHAS.items():
        assert FF.sha256_file(FF.HUMAN_ROOT / "registry" / name) == sha, name


def test_f15c_part_a_product_entries_unchanged():
    import yaml
    base = FF.baseline_file("registry/_products.yaml", BASELINE_PRODUCTS_SHA)
    old = yaml.safe_load(base.read_text(encoding="utf-8"))["products"]
    new = yaml.safe_load((FF.HUMAN_ROOT / "registry" / "_products.yaml").read_text(encoding="utf-8"))["products"]
    for pid, rec in old.items():
        assert pid in new, pid
        assert new[pid] == rec, pid
    added = set(new) - set(old)
    assert added == {FF.ERA5_PID, FF.SEAS5_PID, FF.STATIC_PID, FF.TARGET_PID, FF.STORE_PID}, sorted(added)   # 2.7


def _top_nodes(tree):
    return list(tree.body)


def _is_docstring(node):
    return isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) and \
        isinstance(node.value.value, str)


def _is_f6_constant(node):
    targets = []
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]
    return bool(targets) and all(isinstance(t, ast.Name) and t.id.startswith("F6_") for t in targets)


def _class(nodes, name):
    hits = [n for n in nodes if isinstance(n, ast.ClassDef) and n.name == name]
    assert len(hits) == 1, name
    return hits[0]


def test_f15e_maps_py_differs_only_where_section_4_4_allows():
    base = ast.parse(FF.baseline_file("rivals_human/maps.py", BASELINE_MAPS_SHA).read_text(encoding="utf-8"))
    new = ast.parse((FF.HUMAN_ROOT / "rivals_human" / "maps.py").read_text(encoding="utf-8"))
    assert not any(_is_f6_constant(n) for n in base.body)

    def rest(tree):
        out = []
        for i, n in enumerate(_top_nodes(tree)):
            if i == 0 and _is_docstring(n):
                continue
            if _is_f6_constant(n):
                continue
            if isinstance(n, ast.ClassDef) and n.name in ("F6PctRatio", "Iso"):
                out.append(("class", n.name))
                continue
            out.append(ast.dump(n))
        return out
    assert rest(new) == rest(base), "a top-level node other than the docstring, Iso, F6PctRatio and F6_* changed"
    bi, ni = _class(base.body, "Iso"), _class(new.body, "Iso")
    assert [ast.dump(b) for b in bi.bases] == [ast.dump(b) for b in ni.bases]
    assert [ast.dump(d) for d in bi.decorator_list] == [ast.dump(d) for d in ni.decorator_list]

    def iso_rest(cls):
        return [ast.dump(n) for n in cls.body if not (isinstance(n, ast.FunctionDef) and n.name == "fit")]
    assert iso_rest(ni) == iso_rest(bi), "an Iso method other than fit changed"
    fit = [n for n in ni.body if isinstance(n, ast.FunctionDef) and n.name == "fit"][0]
    args = [a.arg for a in fit.args.args]
    assert args[:5] == ["cls", "x", "t", "increasing", "rho"] and "weights" in args
    defaults = dict(zip(args[-len(fit.args.defaults):], fit.args.defaults)) if fit.args.defaults else {}
    assert isinstance(defaults.get("weights"), ast.Constant) and defaults["weights"].value is None
    consts = [n.targets[0].id for n in new.body if isinstance(n, ast.Assign) and _is_f6_constant(n)]
    assert sorted(consts) == ["F6_MAX_INCOMPLETE_SHARE", "F6_NORMAL_TOL"]


def test_f15e_no_part_a_registry_lists_f6():
    import yaml
    for pkg in PART_A:
        reg = yaml.safe_load((FF.HUMAN_ROOT / "registry" / ("%s.yaml" % pkg)).read_text(encoding="utf-8"))
        for r in reg["rivals"]:
            assert "F6" not in (r.get("families") or []), (pkg, r["id"])


@pytest.mark.realdata
def test_f15d_join_still_accepts_the_part_a_boards(tmp_path):
    """The re-join under the new tool hash: same table bytes as Part 619 (finished boards and their CSV / JSON only;
    no test_preds, no label)."""
    import pandas as pd
    import yaml
    from rivals_human import join as J
    if not PART619_TABLE.is_file():
        pytest.fail("the Part 619 table %s is missing" % PART619_TABLE)
    cfg = yaml.safe_load(FF.PRODUCTION_CONFIG.read_text(encoding="utf-8"))
    cfg["table_root"] = str(tmp_path / "_table").replace("\\", "/")
    parts = pd.read_csv(str(PART619_TABLE), dtype=str, keep_default_na=False)["part"]
    assert parts.nunique() == 1
    out = J.join([RUNS[p] for p in ("coral", "defo", "pm25", "ndvi")], config=cfg, part=str(parts.iloc[0]),
                 pending=[RUNS["fire"]])
    got = (Path(out) / "RIVALS_TABLE.csv").read_bytes()
    want = PART619_TABLE.read_bytes()
    assert got == want, "the re-join differs from the Part 619 table (%d vs %d bytes)" % (len(got), len(want))
    print("T-F15 d: re-join byte-equal to %s (sha256 %s)" % (PART619_TABLE, FF.sha256_bytes(got)))
