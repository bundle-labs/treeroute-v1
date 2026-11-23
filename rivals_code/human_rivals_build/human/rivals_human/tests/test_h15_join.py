"""T-H15 the joiner (SPEC_HUMAN.txt 1.12; PROT section 4): ONE table from the scored common board and the human board
of the table toy. Schema and row order; a lead without a human rival prints one "no human rival: <reason>" line; no
"best rival" line; a mismatched fingerprint, saved test_preds sha, band or "ours" all-row MAE each refuse."""

import json
import shutil

import pandas as pd
import pytest

from rivals_human.tests import hooks as HK

SCHEMA = ["problem", "lead", "rival", "rival_type", "kind", "tier", "label", "decides", "rows_basis", "rows",
          "rows_covered", "rows_total", "groups", "groups_total", "contrast", "verdict", "d_mean", "d_low", "d_high",
          "rival_mae", "ours_mae_same_rows", "ours_mae_all_rows", "normal_mae_same_rows", "anomaly_r2", "corr2", "hit",
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


def test_h15_common_rows_carry_anomaly_r2_and_the_normal_mae(table_flow, joined):
    """Review B issue 11: the common board's rows carry the anomaly R2 of their rival column (read from the common
    scores/lead_<L>_pooled.csv; empty where the engine leaves it empty, as on the table toy) and the guess-normal
    MAE (the board's rule: base__guess_normal, else the run's decline target); rows_covered is filled."""
    import numpy as np
    t = pd.read_csv(joined / "RIVALS_TABLE.csv", float_precision="round_trip")
    com = t[t["rival_type"] == "common"]
    assert len(com)
    h = table_flow.h
    pools = sorted((h.roots["common_board_root"] / h.package).glob("*/scores/lead_0_pooled.csv"))
    assert len(pools) == 1, pools
    pool = pd.read_csv(pools[0], float_precision="round_trip")
    sel = pool[(pool["line"] == "pooled") & (pool["rows_basis"] == "all")].set_index("column")
    run = h.h_run()
    ncol = "base__guess_normal" if "base__guess_normal" in sel.index else run.decline_target
    c0 = com[com["lead"] == 0]
    for _, r in c0.iterrows():
        want = sel.loc["arm__rival_" + str(r["rival"]), "anom_r2"]
        assert (np.isnan(want) and np.isnan(r["anomaly_r2"])) or want == r["anomaly_r2"], r["rival"]
        assert r["normal_mae_same_rows"] == sel.loc[ncol, "mae"]
    assert t[t["rival_type"].isin(["ours", "common"])]["normal_mae_same_rows"].notna().all()
    hum = t[(t["rival_type"] == "human") & t["contrast"].notna()]
    assert (hum["rows_covered"] <= hum["rows_total"]).all() and (hum["rows"] <= hum["rows_covered"]).all()


def test_h15_pending_run_gives_common_rows_and_one_pending_row_per_lead(table_flow, joined):
    """Review B issue 3: a run passed as pending (Part B) joins from its common board only."""
    from rivals_human import config as C
    from rivals_human import join as J
    h = table_flow.h
    out = J.join([], config=str(h.config), pending=[str(h.run)])
    t = pd.read_csv(out / "RIVALS_TABLE.csv", float_precision="round_trip")
    for L in h.leads:
        blk = t[t["lead"] == L]
        assert (blk["rival_type"] == "common").any()
        pend = blk[blk["rival_type"] == "human"]
        assert len(pend) == 1 and str(pend["flags"].iloc[0]) == C.PENDING_LINE


def test_h15_human_order_puts_print_beside_rows_after_their_parent():
    """Review B issue 5 (PLAN 3.14): an A row with print_beside follows its parity row; placebos after extensions."""
    from rivals_human import board as B
    reg = {"rivals": [
        {"id": "same", "leads": {0: "A"}, "print_beside": "lag"},
        {"id": "ext", "leads": {0: "X"}},
        {"id": "lag", "leads": {0: "P"}},
        {"id": "plc", "leads": {0: "X"}, "placebo_of": "lag"},
        {"id": "adv", "leads": {0: "A"}},
        {"id": "lag2", "leads": {0: "P"}}]}
    got = B.human_rival_order(reg, 0, ["same", "ext", "lag", "plc", "adv", "lag2"])
    assert got == ["lag", "same", "lag2", "ext", "plc", "adv"], got


def test_h15_joint_claim_is_not_decidable_when_a_form_has_no_row():
    """Review B issue 10 (Q14 a): YES only when ours beats every form; a form without a deciding row (or not
    calibratable) makes the claim NOT DECIDABLE, never silent."""
    from rivals_human import board as B
    none1 = {"tier": "none", "reason": "toy: no row"}
    reg = {"rivals": [{"id": "f1", "leads": {0: "P", 1: none1}}, {"id": "f2", "leads": {0: "P", 1: none1}}]}
    jc = {"name": "ours beats M", "rivals": ["f1", "f2"]}

    def t(rows):
        return pd.DataFrame(rows, columns=["rival", "contrast", "verdict"])
    both = t([("f1", "guarded_vs_headline", "BEATS"), ("f2", "guarded_vs_headline", "BEATS")])
    assert B.joint_claim_line(jc, both, reg, 0) == "ours beats M: YES"
    one = t([("f1", "guarded_vs_headline", "BEATS"), ("f2", "guarded_vs_headline", "LOSES")])
    assert B.joint_claim_line(jc, one, reg, 0).startswith("ours beats M: NO")
    miss = t([("f1", "guarded_vs_headline", "BEATS"), ("f1", "raw_vs_raw", "BEATS")])
    assert "NOT DECIDABLE (f2 has no row)" in B.joint_claim_line(jc, miss, reg, 0)
    nc = t([("f1", "guarded_vs_headline", "BEATS"), ("f2", "guarded_vs_headline", "NOT CALIBRATABLE")])
    assert "NOT DECIDABLE" in B.joint_claim_line(jc, nc, reg, 0)
    assert B.joint_claim_line(jc, both, reg, 1) is None


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
    # its own index root, so its own run ledger: the shared ledger of the main table flow (review issue 7) would
    # rightly refuse these other picks after the main flow opened test labels
    v = HK.variant_config(h, "no365", reg, index_name="_index_no365")
    for r in reg["rivals"]:
        if not r.get("runner"):
            HK.adapt(v, r["id"], "all", None)
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


@pytest.mark.parametrize("case,words", [
    ("hb_pin", ("human board ran under common harness",)),
    ("hb_common_harness", ("made against a common board of harness",)),
    ("hb_accepted_as", ("acceptance at init",)),
])
def test_h15_harness_records_mismatch_refuse(table_flow, joined, case, words):
    """Ruling AG5 (Part 613): the join refuses a human board not made under the pinned harness, one recorded against a
    common board of another harness, and one whose recorded older-harness acceptance differs from the join config's."""
    def edit(d):
        if case == "hb_pin":
            _edit_json(d / "human_board.json", lambda doc: doc.update(common_harness_sha256="e" * 64))
        elif case == "hb_common_harness":
            _edit_json(d / "human_board.json", lambda doc: doc["common_board"].update(harness_code_sha256="e" * 64))
        else:
            _edit_json(d / "human_board.json", lambda doc: doc["common_board"].update(harness_accepted_as="some reason"))
    v = _edited_copy(table_flow, "join_%s" % case, edit)
    HK.refuses(words, HK.join, v, [v.run])


def test_h15_init_records_no_acceptance_for_a_pinned_common_board(table_flow, joined):
    """The toy's common board is under the pin, so init records harness_accepted_as None and the joined table prints
    no older-harness section (ruling AG5)."""
    hb = HK.read_json(table_flow.out / "human_board.json")
    assert "harness_accepted_as" in hb["common_board"] and hb["common_board"]["harness_accepted_as"] is None
    assert "accepted older harness" not in (joined / "RIVALS_TABLE.md").read_text(encoding="utf-8").lower()
