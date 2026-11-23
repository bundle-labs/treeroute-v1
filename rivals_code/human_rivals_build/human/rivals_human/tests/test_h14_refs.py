"""T-H14 reference rows (SPEC_HUMAN.txt 1.10; Q4, Q23): the tool's own persistence / damped persistence code
reproduces the run's saved lead >= 1 base__persistence and base__damped_persistence byte for byte (the parity
proof), and at the nowcast equals the hand recipe (oracles.persistence_parity, itself checked against the engine
in test_oracles.py); a perturbed phi refuses and no nowcast row is written; the table toy's last visit reproduces its
lead >= 1 base__persistence; reference rows exist only after the lock."""

import numpy as np
import pandas as pd
import pytest

from rivals_human.tests import hooks as HK
from rivals_human.tests import oracles as O

KEYS3 = ["unit", "time", "lead"]
PERS, DAMP, LAST = "base__human_persistence", "base__human_damped_persistence", "base__human_last_visit"


def _refs(out, lead):
    return HK.read_parquet(HK.lead_dir(out, lead) / "refs.parquet")


def _bytes(a):
    return np.asarray(a, dtype=np.float64).tobytes()


def _parity(out, lead):
    """lead_<L>/refs.json of a lead >= 1: the parity proof's record (refs writes no rows at L >= 1)."""
    return HK.read_json(HK.lead_dir(out, lead) / "refs.json")["parity"][str(lead)]


@pytest.mark.parametrize("lead", [6, 12])
def test_h14_grid_parity_at_leads_6_and_12(grid_flow, lead):
    grid_flow.ok("refs %d" % lead)
    rec = _parity(grid_flow.out, lead)
    assert rec["base__persistence"] == "equal" and rec["base__damped_persistence"] == "equal", rec
    assert not (HK.lead_dir(grid_flow.out, lead) / "refs.parquet").is_file()


def test_h14_grid_nowcast_rows_equal_the_hand_recipe(grid_flow):
    grid_flow.ok("refs 0")
    h = grid_flow.h
    d = h.toy.derived()
    offset = int(d["R17"]["value"]["start_offset_steps"])
    spy = int(d["R2"]["value"]["steps_per_year"])
    legal = h.toy.legal()
    labels = O.label_table(h.exports[0], HK.saved_test(h, 0, ["unit", "time", "y"]))
    want = O.persistence_parity(h.run, h.exports, 0, offset, spy, legal, h.toy.cuts(0)["fit_cut"], "lead0_refit",
                                labels=labels)
    r = _refs(grid_flow.out, 0)
    j = want.merge(r, on=KEYS3, how="left", validate="one_to_one")
    assert _bytes(j[PERS]) == _bytes(j["persistence"])
    assert _bytes(j[DAMP]) == _bytes(j["damped_persistence"])


def test_h14_reference_rows_are_scored_and_labelled(grid_flow):
    grid_flow.ok("refs 0", "score 0")
    b = HK.board_lead(grid_flow.out, 0)
    ref = b[b["rival_type"] == "reference"]
    assert {PERS, DAMP} <= set(ref["rival"])
    assert not ref["decides"].astype(str).str.lower().eq("true").any()
    r = ref[ref["rival"] == DAMP].iloc[0]
    assert "baseline to beat" in "%s %s" % (r.get("label", ""), r.get("flags", ""))


def test_h14_reference_rows_need_the_lock(grid_flow):
    assert grid_flow.pre_lock["refs"].startswith("refused:")


def test_h14_a_perturbed_phi_refuses_and_writes_no_nowcast_row(grid_flow, monkeypatch):
    from treeroute.report import metrics as MET
    v = HK.variant_config(grid_flow.h, "phi")
    out = HK.run_tune_lock(v)
    orig = MET.damped_persistence_phi

    def shifted(histories, lead_steps, same_season_key):
        return {u: min(1.0, p + 0.05) for u, p in orig(histories, lead_steps, same_season_key).items()}

    monkeypatch.setattr(MET, "damped_persistence_phi", shifted)
    HK.refuses(("parity", "byte"), HK.refs, v, out, 6)
    HK.refuses(("parity", "byte"), HK.refs, v, out, 0)
    assert not (HK.lead_dir(out, 0) / "refs.parquet").is_file()


@pytest.mark.parametrize("lead", [183, 365])
def test_h14_table_last_visit_parity(table_flow, lead):
    table_flow.ok("refs %d" % lead)
    assert _parity(table_flow.out, lead)["base__persistence"] == "equal"


def test_h14_table_nowcast_last_visit_equals_the_hand_recipe(table_flow):
    table_flow.ok("refs 0")
    from rivals_human.tests.test_oracles import table_site_of
    h = table_flow.h
    labels = pd.concat([O.read_export_part(h.exports[0], "train", ["unit", "time", "y"]),
                        HK.saved_test(h, 0, ["unit", "time", "y"])], ignore_index=True)
    saved = HK.saved_test(h, 0, KEYS3 + ["issue"])
    want = O.last_visit(labels, saved, h.toy.legal(), site_of=table_site_of(h.toy))
    r = _refs(table_flow.out, 0)
    j = saved.merge(r, on=KEYS3, how="left", validate="one_to_one")
    assert _bytes(j[LAST]) == _bytes(want)
