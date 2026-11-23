"""T-H15 the joiner (SPEC_HUMAN.txt 1.12; PROT section 4): ONE table from the scored common board and the human board
of the table toy. Schema and row order; a lead without a human rival prints one "no human rival: <reason>" line; no
"best rival" line; a mismatched fingerprint, saved test_preds sha, band or "ours" all-row MAE each refuse."""

import json
import shutil

import pandas as pd
import pytest

from rivals_human.tests import hooks as HK

SCHEMA = ["problem", "lead", "rival", "rival_type", "kind", "tier", "decides", "rows_basis", "rows", "rows_total",
          "groups", "groups_total", "contrast", "verdict", "d_mean", "d_low", "d_high", "rival_mae",
          "ours_mae_same_rows", "ours_mae_all_rows", "normal_mae_same_rows", "anomaly_r2", "corr2", "hit",
          "calibration_ratio", "timid_win", "guard_passed", "flags", "part"]


@pytest.fixture(scope="module")
def joined(table_flow):
    table_flow.ok(*["score %d" % L for L in table_flow.h.leads])
    return HK.join(table_flow.h, [table_flow.h.run])


def test_h15_outputs_and_schema(joined):
    for name in ("RIVALS_TABLE.md", "RIVALS_TABLE.csv", "inputs_sha256.txt"):
        assert (joined / name).is_file(), name
    t = pd.read_csv(joined / "RIVALS_TABLE.csv", float_precision="round_trip")
    assert list(t.columns) == SCHEMA
    for line in (joined / "inputs_sha256.txt").read_text(encoding="utf-8").splitlines():
        sha, path = line.split("  ", 1)
        assert HK.sha256_file(path) == sha, path


def _rank(row) -> int:
    rt, tier = str(row["rival_type"]), str(row["tier"])
    if rt == "ours":
        return 0
    if rt == "common":
        return 1
    if rt == "human":
        return {"P": 2, "L": 2, "X": 3, "A": 4}.get(tier, 2)
    return {"own_history": 5, "reference": 6}[rt]


def test_h15_row_order_in_each_problem_lead_block(joined):
    t = pd.read_csv(joined / "RIVALS_TABLE.csv", float_precision="round_trip")
    for (prob, lead), blk in t.groupby(["problem", "lead"], sort=False):
        ranks = [_rank(r) for _, r in blk.iterrows()]
        assert ranks == sorted(ranks), (prob, lead, list(zip(blk["rival"], blk["rival_type"], blk["tier"])))
        assert ranks[0] == 0, "the block does not start with our headline"
        assert 1 in ranks, "no common rival row in the block"


def test_h15_no_best_rival_line(joined):
    text = (joined / "RIVALS_TABLE.md").read_text(encoding="utf-8").lower()
    assert "best rival" not in text
    assert "reading rules" in text


def test_h15_a_lead_without_a_human_rival_prints_one_line(table_flow):
    """A variant registry with no human rival at lead 365 (registry no_rival_leads) on the same toy: the joined
    table holds one 'no human rival: <reason>' row at 365."""
    from rivals_human.tests import toy_products as TP
    h = table_flow.h
    reg = TP.table_registry(h.package)
    reason = "toy: no forecast product with a public archive reaches 365 days"
    for r in reg["rivals"]:
        r["leads"][365] = {"tier": "none", "reason": reason}
        r["score_without_net"] = []
    reg["no_rival_leads"] = {365: reason}
    v = HK.variant_config(h, "no365", reg)
    out = HK.run_tune_lock(v)
    for L in v.leads:
        HK.refit(v, out, L)
    for L in sorted(v.leads, reverse=True):
        HK.refs(v, out, L)
    for L in v.leads:
        HK.score(v, out, L)
    t = pd.read_csv(HK.join(v, [v.run]) / "RIVALS_TABLE.csv", float_precision="round_trip")
    at = t[(t["lead"] == 365) & (t["rival_type"] == "human")]
    assert len(at) == 1 and str(at["rival"].iloc[0]) == "no human rival"
    assert reason in str(at["flags"].iloc[0])


def _edited_copy(table_flow, name, edit):
    """The human board tree copied under a new out root, edited by edit(board_dir); returns a config naming it."""
    h = table_flow.h
    v = HK.variant_config(h, name)
    src = table_flow.out
    dest = v.roots["out_root"] / h.package / h.run.name
    shutil.copytree(str(src), str(dest))
    edit(dest)
    return v


def _edit_json(path, fn):
    doc = HK.read_json(path)
    fn(doc)
    HK.move_aside(path, path.parent.parent / "_moved_by_tests")
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")


@pytest.mark.parametrize("case,words", [
    ("fingerprint", ("fingerprint",)),
    ("test_preds", ("different saved test rows", "sha")),
    ("band", ("band",)),
    ("ours_mae", ("pooled mae", "ours")),
])
def test_h15_mismatches_refuse(table_flow, joined, case, words):
    def edit(d):
        if case == "fingerprint":
            _edit_json(d / "human_board.json", lambda doc: doc["run"].update(fingerprint="0" * 64))
        elif case == "test_preds":
            _edit_json(d / "test_labels_opened_human_lead_0.json", lambda doc: doc.update(test_preds_sha256="0" * 64))
        elif case == "band":
            _edit_json(d / "human_board.json", lambda doc: doc["run"].update(band=float(doc["run"]["band"]) * 2 + 1))
        else:
            p = d / "scores" / "lead_0_all_pooled.csv"
            t = pd.read_csv(p, float_precision="round_trip")
            sel = (t["line"] == "pooled") & (t["column"] == "arm__ours") & (t["rows_basis"] == "all")
            t.loc[sel, "mae"] = t.loc[sel, "mae"] * 1.5 + 1.0
            HK.move_aside(p, d / "_moved_by_tests")
            p.write_text(t.to_csv(index=False, lineterminator="\n"), encoding="utf-8")
    v = _edited_copy(table_flow, "join_%s" % case, edit)
    HK.refuses(words, HK.join, v, [v.run])
