"""The layer, vault, FitContext and GLS shapes and signatures against the approved contracts.

The approved shapes live in treeroute/_proposed/common.py, vault.py, fit_context.py and weights_gls.py,
the approved signatures in layer.py, vault.py, fit_context.py and weights_gls.py. Tests may not IMPORT
proposed code, so both are checked by PARSING their source (as tests/test_derive_shapes.py does):
  - every engine copy of an approved record has the approved field names in order, and every copied
    enum the approved member values;
  - every engine function or method with an approved signature takes the approved parameters, in
    order; the only additions are the flagged ones (keyword or defaulted, listed in ADDED below).
"""

import ast
import inspect
from dataclasses import fields
from enum import Enum

from conftest import TREEROUTE_DIR
from treeroute.fit import context as FC
from treeroute.fit import weights as FW
from treeroute.labels import vault as V
from treeroute.layer import arms as LA
from treeroute.layer import decide as LD
from treeroute.layer import links as LL

PROPOSED = TREEROUTE_DIR / "_proposed"

# approved source file -> {approved class name: engine copy}
RECORDS = {
    "common.py": {"ArmSpec": LA.ArmSpec, "PenaltyPick": LD.PenaltyPick, "Adoption": LD.Adoption,
                  "LeadAdoption": LD.LeadAdoption, "GuardResult": LD.GuardResult,
                  "FitCtxLogRow": FC.FitCtxLogRow},
    "vault.py": {"LabelSlice": V.LabelSlice, "TestLabels": V.TestLabels, "DonorLabels": V.DonorLabels},
    "fit_context.py": {"DonorRows": FC.DonorRows, "UnitHistory": FC.UnitHistory, "RouterRows": FC.RouterRows},
    "weights_gls.py": {"WeightModel": FW.WeightModel},
}
ENUMS = {"common.py": {"Tool": LA.Tool, "Weighting": LA.Weighting, "GuardStatus": LD.GuardStatus,
                       "FoldPurpose": FC.FoldPurpose}}

# approved function -> the engine function (module-level)
FUNCTIONS = {
    "layer.py": {"link_forward": LL.link_forward, "link_inverse": LL.link_inverse, "c_for_cut": LL.c_for_cut,
                 "candidate_arms": LA.candidate_arms, "penalty_search": LD.penalty_search,
                 "n2_eligible": LD.n2_eligible, "select_adoption": LD.select_adoption,
                 "clip_to_legal": LL.clip_to_legal, "lead_arms": LA.lead_arms,
                 "forecast_adoption": LD.forecast_adoption, "check_plumbing": LD.check_plumbing},
    "vault.py": {"lock_adoption": V.lock_adoption, "lock_lead_adoption": V.lock_lead_adoption},
    "weights_gls.py": {"cross_region_error": FW.cross_region_error, "fit_weight_model": FW.fit_weight_model,
                       "sigma_floor": FW.sigma_floor, "sigma_clip_bounds": FW.sigma_clip_bounds,
                       "row_weights": FW.row_weights, "weight_model_for_cut": FW.weight_model_for_cut},
}
METHODS = {"vault.py": ("LabelView", V.LabelView), "fit_context.py": ("FitContext", FC.FitContext)}

# flagged additions to approved signatures (each defaulted or keyword-only; see the module docstrings).
# select_adoption "baseline": owner ruling V1 (the owner rulings file, section V; layer/decide.py:386, :401-405).
# weight_model_for_cut "matrix_dir": owner ruling X1 (2026-10-20; the ruling-R RAM tactic, fit/weights.py:526).
# weight_model_for_cut "echo": the progress-print callback of the same RAM change (ruling Q1: the engine prints what it
# waits for); logging only, never a number. Listed with X1; shown to the owner on 2026-10-20 for confirmation.
ADDED = {"LabelView.__init__": ("cadence",), "LabelView.asof_rows": ("purpose",),
         "LabelView.donor_labels": ("picks",), "select_adoption": ("order", "baseline"),
         "cross_region_error": ("blocks",), "weight_model_for_cut": ("blocks", "matrix_dir", "echo")}


def test_every_addition_is_keyword_only():
    """The flagged additions never shift an approved positional parameter."""
    engine = {"LabelView.__init__": V.LabelView.__init__, "LabelView.asof_rows": V.LabelView.asof_rows,
              "LabelView.donor_labels": V.LabelView.donor_labels, "select_adoption": LD.select_adoption,
              "cross_region_error": FW.cross_region_error, "weight_model_for_cut": FW.weight_model_for_cut}
    for key, names in ADDED.items():
        params = inspect.signature(engine[key]).parameters
        for name in names:
            assert params[name].kind is inspect.Parameter.KEYWORD_ONLY, (key, name)


def _classes(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            names = [n.target.id for n in node.body
                     if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)]
            members = {n.targets[0].id: n.value.value for n in node.body
                       if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                       and isinstance(n.targets[0], ast.Name) and not n.targets[0].id.startswith("__")}
            methods = {m.name: [a.arg for a in m.args.args] for m in node.body if isinstance(m, ast.FunctionDef)}
            out[node.name] = (names, members, methods)
    return out


def _functions(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name: [a.arg for a in n.args.args] for n in tree.body if isinstance(n, ast.FunctionDef)}


def test_records_are_field_identical_to_the_approved_shapes():
    for source, copies in RECORDS.items():
        approved = _classes(PROPOSED / source)
        for name, cls in copies.items():
            assert [f.name for f in fields(cls)] == approved[name][0], name


def test_enums_have_the_approved_members():
    for source, copies in ENUMS.items():
        approved = _classes(PROPOSED / source)
        for name, cls in copies.items():
            assert issubclass(cls, Enum)
            assert {m.name: m.value for m in cls} == approved[name][1], name


def _check(name, engine_fn, approved_params, skip_self=False):
    sig = inspect.signature(engine_fn)
    params = list(sig.parameters.values())
    if skip_self:
        params = params[1:]
        approved_params = approved_params[1:]
    positional = [p.name for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    extra = [p for p in params if p.name not in approved_params]
    assert positional[:len(approved_params)] == approved_params, name
    for p in extra:
        assert p.name in ADDED.get(name, ()), (name, p.name)
        assert p.default is not p.empty or p.kind is p.KEYWORD_ONLY, (name, p.name)


def test_functions_take_the_approved_parameters():
    for source, fns in FUNCTIONS.items():
        approved = _functions(PROPOSED / source)
        for name, fn in fns.items():
            _check(name, fn, approved[name])


def test_methods_take_the_approved_parameters():
    for source, (cls_name, cls) in METHODS.items():
        approved = _classes(PROPOSED / source)[cls_name][2]
        for method, params in approved.items():
            engine = getattr(cls, method)
            key = "%s.%s" % (cls_name, method)
            _check(key if key in ADDED else method, engine, params, skip_self=True)


def test_layer_rule_homes_name_real_functions():
    import importlib

    from treeroute import layer

    for rule, where in layer.RULE_HOME.items():
        module, name = where.rsplit(".", 1)
        assert callable(getattr(importlib.import_module("treeroute." + module), name)), rule
    tree = ast.parse((PROPOSED / "derive_rules.py").read_text(encoding="utf-8"))
    approved = None
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else (
            node.targets[0] if isinstance(node, ast.Assign) else None)
        if getattr(target, "id", None) == "RULE_HOME":
            approved = ast.literal_eval(node.value)
    assert approved is not None
    for rule, where in layer.RULE_HOME.items():
        assert approved[rule] == "layer." + where.rsplit(".", 1)[1], rule
