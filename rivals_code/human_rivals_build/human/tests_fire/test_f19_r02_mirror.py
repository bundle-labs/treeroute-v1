"""T-F19 the R02 mirror for the fire files (SPEC_HUMAN_PARTB.txt 3.9, 4; review R-7, R-8): B3's own early run of the
static scan of review_tests/test_r02_runner_label_scope.py:71-88, which the ONE suite runs over every adapters/*.py and
which may not be edited. An AST scan of adapters/fire_*.py finds no attribute named slim, _hctx, read_set or _token
(any object, module paths such as rivals_human.slim.open_slim included), and every `.fit_labels(...)` call has exactly
one positional argument, the bare Name fit_set, no keyword, and sits inside fit() or a helper whose parameter is named
fit_set. Both runners read labels (at least one such call each, in the runner or its shared helper module).
"""

import ast

import pytest

from tests_fire import fixtures_fire as FF

FORBIDDEN_ATTRS = ("slim", "_hctx", "read_set", "_token")


def _files():
    files = sorted((FF.HUMAN_ROOT / "adapters").glob("fire_*.py"))
    names = set(p.name for p in files)
    need = {"fire_geff.py", "fire_refs_prep.py", "fire_enso.py", "fire_turco.py"}
    assert need <= names, "adapters/fire_*.py missing: %s" % sorted(need - names)
    return files


def _parents(tree):
    par = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            par[child] = node
    return par


def _enclosing_function(node, par):
    while node in par:
        node = par[node]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    return None


def test_f19_no_forbidden_attribute_in_the_fire_files():
    for p in _files():
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRS:
                pytest.fail("%s:%d touches .%s (R02 fails the ONE suite on it)" % (p.name, node.lineno, node.attr))


def test_f19_fit_labels_calls_are_literal():
    calls = {}
    for p in _files():
        tree = ast.parse(p.read_text(encoding="utf-8"))
        par = _parents(tree)
        calls[p.name] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "fit_labels":
                where = "%s:%d" % (p.name, node.lineno)
                assert [ast.dump(a) for a in node.args] == [ast.dump(ast.Name(id="fit_set", ctx=ast.Load()))], where
                assert not node.keywords, "%s: a keyword argument in fit_labels" % where
                fn = _enclosing_function(node, par)
                assert fn is not None, "%s: fit_labels outside any function" % where
                params = [a.arg for a in fn.args.args + fn.args.kwonlyargs]
                assert fn.name == "fit" or "fit_set" in params, "%s: inside %s(%s)" % (where, fn.name, params)
                calls[p.name].append(where)
    assert not calls["fire_geff.py"] and not calls["fire_refs_prep.py"]          # the index path reads no label
    shared = sum(len(v) for k, v in calls.items() if k not in ("fire_geff.py", "fire_refs_prep.py"))
    assert shared >= 1, "no runner reads its labels through ctx.fit_labels(fit_set)"


def test_f19_the_mirror_is_not_blind(tmp_path):
    bad = tmp_path / "fire_bad.py"
    bad.write_text("def predict(ctx, fs):\n    ctx.fit_labels(fs)\n    return ctx.slim.read_set('inner')\n",
                   encoding="utf-8")
    tree = ast.parse(bad.read_text(encoding="utf-8"))
    attrs = [n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)]
    assert "slim" in attrs and "read_set" in attrs
    call = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "fit_labels"][0]
    assert [ast.dump(a) for a in call.args] != [ast.dump(ast.Name(id="fit_set", ctx=ast.Load()))]
