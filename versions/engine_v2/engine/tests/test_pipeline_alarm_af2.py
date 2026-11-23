"""Owner ruling AF2 end to end: the grid toy of tests/test_pipeline.py run through this engine (tests/alarm_toy_runner.py,
forced adoption of the GLS corrector, the A8 threshold 0 and the batch floor 1, so an ELIGIBLE twin takes every batch
with a gap), with the adopted link's trees-off MAE handed to select_adoption set so that:
  F5 SPLIT: the twin (the unweighted corrector) beats it at its OWN best point (it is in adoption.json's eligible list)
     but NOT at the adopted point (equal there; N2 is strict): the nowcast alarm is inert_twin_not_eligible, no batch
     switches although every batch's ratio is above the (zero) threshold, and with = without bit for bit;
  F6 REVERSE: the twin beats it at the adopted point too: the nowcast alarm is active and switches.
Both records name the rulings (AF1, AF2) and the eligibility basis, and pass verify_alarm.
"""

import json
from pathlib import Path

import pytest

from alarm_toy_compare import run_child
from conftest import make_registry
from test_pipeline import make_pipeline_package, sklearnex_patched  # noqa: F401  (the module's autouse fixture)


@pytest.fixture(scope="module")
def af2_toys(tmp_path_factory):
    from conftest import ENGINE_DIR

    base = tmp_path_factory.mktemp("alarm_af2")
    pkg = make_pipeline_package(base / "pk")
    (base / "shipped").mkdir()
    reg = make_registry(base, [base / "shipped"])
    return {kind: run_child(ENGINE_DIR, pkg, base / kind, reg, mode="forced", switch_all=True, af2=kind)
            for kind in ("split", "reverse")}


def _doc(folder, name):
    return json.loads((Path(folder) / name).read_text(encoding="utf-8"))


def _common(folder):
    from treeroute.pipeline import alarm_pass as AP

    doc, alarm = AP.verify_alarm(folder, 0)
    adoption = _doc(folder, "adoption.json")
    assert doc["adopted_arm"].endswith("_corrector_gls") and doc["twin_arm"].endswith("_corrector_unweighted")
    assert doc["constants"] == {"A8.alarm_ratio_threshold": 0.0, "A8.alarm_min_batch_rows": 1}
    assert {"AF1", "AF2"} <= set(doc["rulings"])
    # the twin IS in the eligible list (its own best point beats the reference) in both toys
    assert doc["twin_arm"] in ["%s_%s_%s" % (a["link"], a["tool"], a["weighting"]) for a in adoption["eligible"]]
    basis = doc["eligibility_basis"]
    assert basis["ruling"] == "AF2" and basis["in_adoption_eligible_list"] is True
    assert basis["point"] == adoption["penalty"]
    assert basis["twin_mae"] == adoption["surface_mae"][basis["twin_key"]]
    assert basis["baseline_mae"] == adoption["surface_mae"][basis["baseline"]]
    assert basis["baseline"].endswith("_trees_off_unweighted")
    # the twin's own best point is below the reference
    twin_best = min(v for k, v in adoption["surface_mae"].items() if k.startswith(doc["twin_arm"] + "@"))
    assert twin_best < basis["baseline_mae"]
    return doc, alarm, basis


def test_f5_eligible_at_its_own_best_point_but_not_at_the_adopted_point_never_switches(af2_toys):
    folder = af2_toys["split"]["folder"]
    doc, alarm, basis = _common(folder)
    assert basis["twin_mae"] == basis["baseline_mae"]               # equal at the adopted point: not strictly below
    assert doc["twin_eligible"] is False and doc["status"] == "inert_twin_not_eligible"
    ratios = [b["ratio"] for b in doc["batches"]]
    assert ratios and all(r is not None and r > 0.0 for r in ratios)   # every batch above the zero threshold ...
    assert doc["batches_tested"] == 0 and doc["batches_fired"] == 0 and doc["rows_switched"] == 0   # ... none switched
    assert not alarm["fired"].any() and (alarm["with_alarm"].to_numpy() == alarm["adopted"].to_numpy()).all()
    rec = _doc(folder, "alarm_verdict.json")
    assert rec["with"]["pooled_mae"] == rec["without"]["pooled_mae_adopted"]


def test_f6_eligible_at_the_adopted_point_switches(af2_toys):
    folder = af2_toys["reverse"]["folder"]
    doc, alarm, basis = _common(folder)
    assert basis["twin_mae"] < basis["baseline_mae"]
    assert doc["twin_eligible"] is True and doc["status"] == "active"
    assert doc["batches_fired"] > 0 and doc["rows_switched"] == int(alarm["fired"].sum()) > 0
    rec = _doc(folder, "alarm_verdict.json")
    assert rec["with"]["pooled_mae"] != rec["without"]["pooled_mae_adopted"]
