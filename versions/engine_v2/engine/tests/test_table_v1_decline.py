"""Owner ruling V1 (OWNER_RULINGS_2026-10-06.md:103): for the neighbour kind, every decline (nowcast and every lead)
falls back to the donor-row median (R34), and every guard or decline comparison uses that same median as its
baseline. Grid kinds are unchanged.

  - layer/decide.py with a DeclineBaseline: an arm that beats its own trees-off but not the baseline declines; an
    arm that beats the baseline but not its trees-off is adopted; a tie with the baseline is not eligible (strict);
    the record, the candidate table, the predictions and the locked decision section carry the baseline;
  - refusals: with a legacy list, a wrong length, a non-finite value, a key that is an arm's or a candidate's;
  - decline_baseline=None (every grid caller): the adoption document and the printed lines are the old ones, byte
    for byte, and the old decline text names the identity trees-off;
  - the toy table run: the nowcast N2 and every lead's guard compare with the donor-row median (each surface row its
    fold's median; each guard the guard pass's own fallback median); the saved columns hold it;
  - a forced decline (every N2 comparison fails): the declined nowcast and every declined lead adopt
    base__donor_median; the ladder tags DECLINED; the report table reads the adopted column;
  - the gate is the router kind (R12), never a package name; the grid callers pass no decline baseline;
  - a fallback donor row (the median's rows) that is test-marked is refused (G-FITCUT), by mark and not only by date.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from table_toy import build_toy_table_package, patch_sklearn, run_toy
from test_vault_world import LEGAL, make_context, make_surface, make_world, surface_arms
from treeroute.derive.shapes import CutKind, Link
from treeroute.layer.arms import (ArmSpec, LayerRefusal, LegacyCandidates, Tool, Weighting, arm_name,
                                  trees_off_of)
from treeroute.layer import decide as LD
from treeroute.layer.decide import (DeclineBaseline, PenaltyPick, adoption_document, candidate_key, check_adoption,
                                    decide, decision_lines, forecast_adoption, select_adoption)
from treeroute.route.kinds import per_unit_grid

U = Weighting.UNWEIGHTED
GRID = per_unit_grid(True)
KEY = "base__donor_median"
RULE = "owner ruling V1 (test)"
LEADS = (183, 365)
DECLINED = "declined"            # report.metrics.VerdictTag.DECLINED.value


def arm(link, tool, weighting=U):
    return ArmSpec(link, tool, weighting, tool in (Tool.PLAIN, Tool.CORRECTOR))


def pick(a, point, mae):
    return PenaltyPick(arm=a, point=point, mae=mae, mae_by_point={point: mae}, edge=False)


# ------------------------------------------------------------------------------------ select_adoption
def test_the_baseline_replaces_each_arms_own_trees_off_in_n2():
    a1, b1 = arm(Link.IDENTITY, Tool.PLAIN), arm(Link.LOG_C, Tool.PLAIN)
    picks = (pick(a1, GRID[3], 3.0), pick(b1, GRID[5], 2.1))
    off = {Link.IDENTITY: 3.5, Link.LOG_C: 2.0}
    # old rule: a1 beats its own trees-off (3.0 < 3.5) and is adopted; b1 does not (2.1 > 2.0)
    assert select_adoption(picks, off, {}).adopted == a1
    # V1, baseline 2.5: b1 beats the baseline (and not its trees-off) and is adopted; a1 does not
    ad = select_adoption(picks, off, {}, baseline=(KEY, 2.5))
    assert ad.adopted == b1 and ad.eligible == (b1,) and not ad.declined
    assert ad.surface_mae[KEY] == 2.5
    assert ad.surface_mae[candidate_key(trees_off_of(Link.IDENTITY), None)] == 3.5    # still printed
    check_adoption(ad)
    # V1, baseline 2.0: a1 beats its own trees-off but not the baseline: the layer declines
    ad = select_adoption(picks, off, {}, baseline=(KEY, 2.0))
    assert ad.declined and ad.adopted is None and ad.best_tree_arm == b1
    # a tie with the baseline is not eligible (strict, D64)
    ad = select_adoption(picks, off, {}, baseline=(KEY, 2.1))
    assert ad.declined


def test_select_adoption_baseline_refusals():
    a1 = arm(Link.IDENTITY, Tool.PLAIN)
    picks = (pick(a1, GRID[3], 3.0),)
    off = {Link.IDENTITY: 3.5}
    legacy = LegacyCandidates(arms=(a1, trees_off_of(Link.IDENTITY)), reason="a replay")
    with pytest.raises(LayerRefusal, match="legacy"):
        select_adoption(picks, off, {}, order=legacy, baseline=(KEY, 2.0))
    with pytest.raises(LayerRefusal, match="candidate's key"):
        select_adoption(picks, off, {}, baseline=(candidate_key(a1, GRID[3]), 2.0))
    with pytest.raises(LayerRefusal, match="candidate's key"):
        select_adoption(picks, off, {}, baseline=("identity_trees_off_unweighted", 2.0))
    with pytest.raises(LayerRefusal, match="finite"):
        select_adoption(picks, off, {}, baseline=(KEY, float("nan")))
    with pytest.raises(LayerRefusal, match="key, MAE"):
        select_adoption(picks, off, {}, baseline=KEY)


def test_forecast_adoption_with_the_baseline_mae_declines_a_lead_that_does_not_beat_it():
    a1 = arm(Link.IDENTITY, Tool.PLAIN)
    now = select_adoption((pick(a1, GRID[3], 3.0),), {Link.IDENTITY: 3.5}, {}, baseline=(KEY, 3.2))
    assert forecast_adoption(now, 183, 2.9, 3.0, 365).guard_passed
    la = forecast_adoption(now, 183, 3.0, 3.0, 365)
    assert not la.guard_passed and la.adopted is None


# ------------------------------------------------------------------------------------ decide()
def _setup():
    w = make_world()
    return w, make_surface(w), make_context(w, 0, CutKind.GUARD)


def test_decide_with_a_decline_baseline_records_and_scores_it():
    w, s, guard = _setup()
    arms = surface_arms(s.y, seed=5)
    pre = np.full(s.y.size, -1.0)                       # below the legal range: decide clips it (R28)
    pre[::2] = float(np.median(s.y))
    rec = decide(s, arms, GRID, LEGAL, guard, decline_baseline=DeclineBaseline(KEY, RULE, pre))
    clipped = np.maximum(pre, 0.0)
    base_mae = float(np.mean(np.abs(s.y - clipped)))
    assert rec.decline_baseline == {"key": KEY, "rule": RULE, "mae": base_mae}
    assert rec.predictions[KEY].tobytes() == clipped.tobytes() and not rec.predictions[KEY].flags.writeable
    assert rec.clip[KEY].n_below == int((pre < 0).sum())
    assert rec.candidates[-1].arm == KEY and rec.candidates[-1].level is None and rec.candidates[-1].mae == base_mae
    assert rec.adoption.surface_mae[KEY] == base_mae
    best = {arm_name(p.arm): p.mae for p in rec.picks}
    assert [arm_name(a) for a in rec.adoption.eligible] == [n for n, m in best.items() if m < base_mae]
    doc = adoption_document(rec.adoption, rec)
    assert doc["decision"]["decline_baseline"] == {"key": KEY, "rule": RULE, "mae": base_mae}
    assert doc["decision"]["n_candidates"] == len(rec.candidates)
    registered = w.labels.decision_documents()
    assert json.dumps(registered[-1], sort_keys=True) == json.dumps(json.loads(json.dumps(doc)), sort_keys=True)
    assert any("decline baseline %s" % KEY in line for line in decision_lines(rec))


def test_decide_declines_to_the_baseline_when_no_arm_beats_it():
    w, s, guard = _setup()
    arms = surface_arms(s.y, seed=5)                    # every tree arm beats its noisy trees-off at some point
    old = decide(s, arms, GRID, LEGAL, guard)
    assert not old.adoption.declined
    rec = decide(s, arms, GRID, LEGAL, guard, decline_baseline=DeclineBaseline(KEY, RULE, np.asarray(s.y)))
    assert rec.adoption.declined and rec.decline_baseline["mae"] == 0.0
    lines = decision_lines(rec)
    assert any("no tree arm beat the decline baseline; the decline target is %s" % KEY in ln for ln in lines)
    assert not any("identity-link trees-off" in ln for ln in lines)


def test_decide_decline_baseline_refusals():
    w, s, guard = _setup()
    arms = surface_arms(s.y, seed=5)
    n = s.y.size
    legacy = LegacyCandidates(arms=tuple(sa.arm for sa in arms if sa.arm.weighting is not Weighting.GLS),
                              reason="a replay")
    with pytest.raises(LayerRefusal, match="legacy"):
        decide(s, arms, GRID, LEGAL, guard, legacy=legacy, decline_baseline=DeclineBaseline(KEY, RULE, np.zeros(n)))
    with pytest.raises(LayerRefusal, match="rows"):
        decide(s, arms, GRID, LEGAL, guard, decline_baseline=DeclineBaseline(KEY, RULE, np.zeros(n - 1)))
    bad = np.zeros(n)
    bad[3] = np.nan
    with pytest.raises(LayerRefusal, match="missing or infinite"):
        decide(s, arms, GRID, LEGAL, guard, decline_baseline=DeclineBaseline(KEY, RULE, bad))
    with pytest.raises(LayerRefusal, match="no arm has"):
        decide(s, arms, GRID, LEGAL, guard,
               decline_baseline=DeclineBaseline("identity_plain_unweighted", RULE, np.zeros(n)))
    with pytest.raises(LayerRefusal, match="rule"):
        decide(s, arms, GRID, LEGAL, guard, decline_baseline=DeclineBaseline(KEY, " ", np.zeros(n)))
    with pytest.raises(LayerRefusal, match="DeclineBaseline"):
        decide(s, arms, GRID, LEGAL, guard, decline_baseline=(KEY, np.zeros(n)))


def test_without_a_baseline_the_grid_decision_is_byte_identical():
    """Every grid caller passes no decline baseline: the document, the candidate table and the printed lines are the
    ones a call without the keyword gives, and the decline text still names the identity trees-off."""
    from treeroute.runs.atomic import dumps

    w, s, guard = _setup()
    for off_noise in (3.0, 0.0):                        # adopts, then declines (trees-off exact)
        arms = surface_arms(s.y, seed=5, off_noise=off_noise)
        a = decide(s, arms, GRID, LEGAL, guard)
        b = decide(s, arms, GRID, LEGAL, guard, decline_baseline=None)
        da, db = adoption_document(a.adoption, a), adoption_document(b.adoption, b)
        assert dumps(da) == dumps(db) and "decline_baseline" not in da["decision"]
        assert KEY not in da["surface_mae"] and a.decline_baseline is None
        assert a.candidates == b.candidates and decision_lines(a) == decision_lines(b)
        assert set(a.predictions) == {arm_name(sa.arm) for sa in arms}
        if off_noise == 0.0:
            assert a.adoption.declined
            assert any("the decline target is the identity-link trees-off" in ln for ln in decision_lines(a))


def test_the_grid_callers_pass_no_decline_baseline():
    """pipeline/passes.py and pipeline/ladder.py (the grid run and ladder) never name the V1 objects."""
    import treeroute.pipeline.ladder as GLAD
    import treeroute.pipeline.passes as GP

    for mod in (GP, GLAD):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "decline_baseline" not in src and "DeclineBaseline" not in src and "decline_to_donor_median" not in src


def test_the_gate_is_the_router_kind():
    from treeroute.pipeline import router as PR
    from treeroute.pipeline.table_passes import TableRunState

    st = TableRunState.__new__(TableRunState)
    assert not st.decline_to_donor_median()                   # no kind read yet
    st.kind = PR.KIND_NEIGHBOUR
    assert st.decline_to_donor_median()
    st.kind = "per_unit"
    assert not st.decline_to_donor_median()


# ------------------------------------------------------------------------------------ the toy table run
@pytest.fixture(scope="module", autouse=True)
def sklearnex_patched():
    undo = patch_sklearn()
    yield
    undo()


@pytest.fixture(scope="module")
def toy_run(tmp_path_factory):
    base = tmp_path_factory.mktemp("v1_toy")
    pkg = build_toy_table_package(base / "pk")
    return base, pkg, run_toy(pkg, base)


@pytest.fixture(scope="module")
def declined_run(tmp_path_factory):
    """Every N2 comparison fails (layer.decide.n2_eligible patched to False): the nowcast and every lead decline."""
    base = tmp_path_factory.mktemp("v1_declined")
    pkg = build_toy_table_package(base / "pk")
    mp = pytest.MonkeyPatch()
    mp.setattr(LD, "n2_eligible", lambda a, b: False)
    try:
        folder = run_toy(pkg, base)
    finally:
        mp.undo()
    return base, pkg, folder


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _arm_name_of(doc):
    return arm_name(ArmSpec(Link(doc["link"]), Tool(doc["tool"]), Weighting(doc["weighting"]), doc["selectable"]))


def test_the_toy_nowcast_n2_compares_with_the_fold_medians(toy_run):
    _, _, folder = toy_run
    doc = _json(folder / "adoption.json")
    base = doc["decision"]["decline_baseline"]
    assert base["key"] == KEY and "V1" in base["rule"] and doc["surface_mae"][KEY] == base["mae"]
    # eligible = the tree arms whose best surface MAE is below the baseline's (strict)
    best = {}
    for k, v in doc["surface_mae"].items():
        if "@" in k:
            name = k.split("@")[0]
            best[name] = min(best.get(name, np.inf), v)
    assert sorted(_arm_name_of(a) for a in doc["eligible"]) == sorted(n for n, m in best.items() if m < base["mae"])
    assert doc["declined"] == (not doc["eligible"])
    # each surface row's baseline is its own fold's median (the U3 fallback of that fold, N5), clipped
    checks = _json(folder / "decision_checks.json")
    fold_median = checks["decline_baseline"]["per_fold_median"]
    inner = pd.read_parquet(folder / "inner_preds.parquet")
    want = np.clip(inner["group"].map(fold_median).to_numpy(dtype=np.float64), 0.0, 100.0)
    assert np.array_equal(inner[KEY].to_numpy(dtype=np.float64), want)
    y = inner["y"].to_numpy(dtype=np.float64)
    assert float(np.mean(np.abs(y - want))) == base["mae"]
    v = _json(folder / "verdict.json")
    assert v["decline_target"] == KEY and "V1" in v["decline_rule"]
    assert v["adopted_column"] == (KEY if v["declined"] else "arm__" + v["adopted"])


def test_the_toy_lead_guards_compare_with_the_guard_banks_donor_median(toy_run):
    _, _, folder = toy_run
    for L in LEADS:
        lead = folder / "ladder" / ("lead_%d" % L)
        rec = _json(lead / "lead.json")
        g = rec["guard"]
        assert g["baseline_column"] == KEY and "V1" in g["baseline_rule"]
        assert g["passed"] == (g["pinned_mae"] < g["baseline_mae"])
        assert g["baseline_value"] == g["router"]["neighbour"]["constants"]["parts"]["all"]["median"]
        assert g["baseline_donor_rows"] == g["router"]["neighbour"]["constants"]["parts"]["all"]["fallback_rows"]
        gp = pd.read_parquet(lead / "guard_preds.parquet")
        base = gp[KEY].to_numpy(dtype=np.float64)
        assert np.all(base == min(max(g["baseline_value"], 0.0), 100.0))
        assert float(np.mean(np.abs(gp["y"].to_numpy(dtype=np.float64) - base))) == g["baseline_mae"]
        t = rec["test"]
        assert t["decline_target"] == KEY
        assert t["adopted_column"] == ("arm__" + rec["pinned"] if g["passed"] else KEY)


def test_a_declined_nowcast_and_declined_leads_adopt_the_donor_median(declined_run):
    _, _, folder = declined_run
    doc = _json(folder / "adoption.json")
    assert doc["declined"] and doc["adopted"] is None
    v = _json(folder / "verdict.json")
    assert v["declined"] and v["adopted"] == "donor_median" and v["adopted_column"] == KEY
    assert v["verdict"]["tag"] == DECLINED
    assert v["pooled_mae_adopted"] == v["pooled_mae_reference"]
    lad = _json(folder / "ladder" / "ladder.json")
    pinned_link = Link(doc["best_tree_arm"]["link"])
    for L in LEADS:
        rec = _json(folder / "ladder" / ("lead_%d" % L) / "lead.json")
        assert rec["pinned"] == _arm_name_of(doc["best_tree_arm"])
        assert rec["declined_at_lead"] and rec["adopted"] is None and not rec["guard"]["passed"]
        assert rec["test"]["adopted_column"] == KEY and rec["test"]["decline_target"] == KEY
        assert rec["test"]["own_trees_off_column"] == "arm__" + arm_name(trees_off_of(pinned_link))   # beside
        assert lad["verdicts"][str(L)]["adopted"] == KEY and lad["verdicts"][str(L)]["tag"] == DECLINED
    assert lad["verdicts"]["0"]["adopted"] == KEY and lad["verdicts"]["0"]["tag"] == DECLINED
    table = pd.read_csv(folder / "ladder" / "ladder_table.csv")
    assert set(table.loc[table["adopted"], "column"]) == {KEY}


def test_the_report_table_reads_the_adopted_column(declined_run, tmp_path, monkeypatch):
    from treeroute_report import table as RT

    _, _, folder = declined_run
    cont = tmp_path / "continuity_groups.yaml"
    cont.write_text(RT.CONTINUITY_FILE.read_text(encoding="utf-8")
                    + "\ntoy_table:\n  label: none\n  continuity_groups: []\n", encoding="utf-8")
    monkeypatch.setattr(RT, "CONTINUITY_FILE", cont)       # report tooling may name packages; the toy is not listed
    run = RT.Run(folder, watermark=True)
    assert run.info[0]["adopted"] == KEY and all(run.info[L]["adopted"] == KEY for L in LEADS)
    built = RT.build([folder], watermark=True)
    md = RT.render_markdown(built, {}, True)
    assert "SMOKE - NOT HEADLINE" in md                 # build() recomputed every verdict on the adopted columns


class _MarkedTable(object):
    """The run's table with one extra row marked test (every other attribute is the real table's)."""

    def __init__(self, table, is_test):
        self._table = table
        self.is_test = is_test

    def __getattr__(self, name):
        return getattr(self._table, name)


def test_a_test_marked_fallback_donor_row_is_refused(tmp_path):
    """REVIEW v1 item 2: the donor-row median's rows are checked by mark (pipeline/table_router.py). One fallback
    donor row of the first pass is marked test in the table the pass reads; the pass refuses before any solve."""
    from treeroute.pipeline import table_router as TR

    pkg = build_toy_table_package(tmp_path / "pk")
    real = TR.NeighbourPass._prepare
    seen = []

    def planted(self):
        mark = np.asarray(self.data.is_test, dtype=bool).copy()
        row = int(np.asarray(self.parts[0].fallback_donor.grid_rows, dtype=np.int64)[0])
        mark[row] = True
        self.data = _MarkedTable(self.data, mark)
        seen.append(row)
        return real(self)

    mp = pytest.MonkeyPatch()
    mp.setattr(TR.NeighbourPass, "_prepare", planted)
    try:
        with pytest.raises(Exception, match="fallback donor row"):
            run_toy(pkg, tmp_path)
    finally:
        mp.undo()
    assert len(seen) == 1
