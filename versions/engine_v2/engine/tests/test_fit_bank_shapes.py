"""The bank against the APPROVED contracts: shapes (proposed common.py), the DonorRows container
(proposed fit_context.py) and the signatures (proposed bank_recipe.py).

The engine may not import the proposed modules (G-IMPORT) and the pytest process may not load them
(a loaded proposed module makes the manifest refuse), so the sources are parsed with ast here, and
the one run with the real proposed DonorRows happens in a fresh interpreter.
"""

import ast
import inspect
import json
from dataclasses import fields

from conftest import TREEROUTE_DIR, run_python
from treeroute.fit import bank as B
from treeroute.fit import correctors as C

PROPOSED = TREEROUTE_DIR / "_proposed"


def _classes(path):
    """{class name: (annotated field names in order, {member: constant value})}."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            names = [n.target.id for n in node.body
                     if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)]
            members = {n.targets[0].id: n.value.value for n in node.body
                       if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                       and isinstance(n.targets[0], ast.Name)}
            out[node.name] = (names, members)
    return out


def _functions(path):
    """{function name: [parameter names]} for the module's top-level functions."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name: [a.arg for a in n.args.args] for n in tree.body if isinstance(n, ast.FunctionDef)}


def test_bank_shapes_mirror_the_approved_common_shapes():
    approved = _classes(PROPOSED / "common.py")
    assert [f.name for f in fields(B.Bank)] == approved["Bank"][0]
    assert [f.name for f in fields(B.BankManifest)] == approved["BankManifest"][0]
    assert {m.name: m.value for m in B.SeedRole} == approved["SeedRole"][1]


def test_donor_rows_fields_read_are_the_approved_container():
    approved = _classes(PROPOSED / "fit_context.py")
    assert list(B._DONOR_FIELDS) == approved["DonorRows"][0]


def test_signatures_match_the_approved_bank_recipe():
    approved = _functions(PROPOSED / "bank_recipe.py")
    engine = {name: getattr(B, name, None) or getattr(C, name, None) for name in approved}
    assert all(fn is not None for fn in engine.values()), sorted(n for n, f in engine.items() if not f)
    for name, params in approved.items():
        got = list(inspect.signature(engine[name]).parameters)
        if name == "check_oob_share":
            # D51 (owner rulings, part A) needs each home group's row count: one added argument
            assert got == params + ["n_group_rows"], got
        else:
            assert got == params, (name, got, params)
    # the corrector functions live in correctors.py, the rest in bank.py
    assert {n for n in approved if hasattr(C, n) and not hasattr(B, n)} == {
        "fit_one_corrector", "fit_corrector", "fit_placebo_corrector"}


CODE = r"""
import json
import numpy as np
from treeroute._proposed import common as PC
from treeroute._proposed.fit_context import DonorRows
from treeroute.fit import bank as B

rng = np.random.RandomState(0)
n_per = {"g_one": 120, "g_two": 90}
X = rng.normal(size=(210, 12)).astype(np.float32)
y = (X[:, 0] + 0.1 * rng.normal(size=210)).astype(np.float64)
gor = np.array(["g_one"] * 120 + ["g_two"] * 90, dtype=object)
rows = DonorRows(groups=("g_two", "g_one"), cut=50, cut_kind=PC.CutKind.FIT, lead=0, fold=None,
                 unit_ids=np.array(["u%d" % (i // 30) for i in range(210)], dtype=object),
                 times=np.tile(np.arange(30, dtype=np.int64), 7), group_of_row=gor,
                 grid_rows=np.arange(210), y=y, X=X, row_key_hash="h")
bank = B.fit_donor_bank(rows, 12)
print("RESULT " + json.dumps({
    "groups": list(bank.manifest.groups), "cut_kind": bank.manifest.cut_kind.value,
    "n_trees": len(bank.trees), "n_units": bank.manifest.n_units,
    "first_seed": bank.trees[0].get_params()["random_state"],
    "want_seed": B.name_seed("g_one", 0, B.SeedRole.TREE)}))
"""


def test_fit_donor_bank_accepts_the_approved_donor_rows():
    proc = run_python(CODE)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")][-1]
    res = json.loads(line[len("RESULT "):])
    assert res["groups"] == ["g_one", "g_two"] and res["cut_kind"] == "fit"
    assert res["n_trees"] == 24 and res["n_units"] == 7
    assert res["first_seed"] == res["want_seed"]
