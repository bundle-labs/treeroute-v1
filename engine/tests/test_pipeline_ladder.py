"""The forecast ladder (plan 4.1 step 11; R10, R11, R17, R29, R31, R34, R35; D86; F45; F57), the router-kind
dispatch (R12: per-unit with the region fallback, region) and the GLS arms, end to end on the pipeline's
synthetic package (tests/test_pipeline.py: 4 groups, 12 years, monthly target; R10 gives leads 6 and 12, owner
ruling I1), with owner rulings H2 (a guard-cut bank per lead), H4 (a test row whose issue row is absent is left
out of scoring, saved flagged and counted) and H5 (each lead searches its own fallback level on its guard).

Every run writes only under the test's temp folder (the fake machine file's run root and temp dir).
"""

import hashlib
import json
from contextlib import contextmanager
from dataclasses import replace as _replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from test_pipeline import (FAKE_LAUNCH, GROUPS, LEADS, SPARSE_GROUP, SPARSE_UNITS, _machine, _run,  # noqa: F401
                           make_pipeline_package, sklearnex_patched)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ladder_run(tmp_path_factory):
    base = tmp_path_factory.mktemp("ladder_smoke")
    pkg = make_pipeline_package(base / "pk")
    return base, pkg, Path(_run(pkg, base))


def _cuts(folder):
    return {int(k): v for k, v in _json(folder / "derived.json")["R11"]["value"].items()}


# ------------------------------------------------------------------------------------------ the lock
def test_every_lead_is_locked_before_its_test_labels_open_and_pinned_to_the_nowcast(ladder_run):
    _, _, folder = ladder_run
    nowcast_sha = _json(folder / "adoption.json.lock.json")["sha256"]
    adoption = _json(folder / "adoption.json")
    pinned = adoption["adopted"] if not adoption["declined"] else adoption["best_tree_arm"]
    penalty = adoption["penalty"] if not adoption["declined"] else adoption["best_tree_penalty"]
    for lead in LEADS:
        name = "adoption_lead_%d.json" % lead
        lock = _json(folder / (name + ".lock.json"))
        opened = _json(folder / ("test_labels_opened_lead_%d.json" % lead))
        assert lock["lead"] == lead and lock["sha256"] == _sha(folder / name) == opened["adoption_sha256"]
        assert lock["locked_at_epoch"] <= (folder / ("test_labels_opened_lead_%d.json" % lead)).stat().st_mtime + 1e-3
        doc = _json(folder / name)
        assert doc["nowcast_sha256"] == nowcast_sha                       # the lead names the locked nowcast
        assert doc["pinned"] == pinned and doc["penalty"] == penalty      # R29's pin
        assert doc["placebo_built"] is (lead == max(LEADS))               # F45: the longest lead only
        # the guard rows were saved before the lock
        assert (folder / "ladder" / ("lead_%d" % lead) / "guard_preds.parquet").stat().st_mtime <= \
            lock["locked_at_epoch"] + 1e-3


def test_the_lead_zero_contract_reproduces_the_nowcast_exactly(ladder_run):
    _, _, folder = ladder_run
    c = _json(folder / "ladder" / "contract_lead_0.json")
    assert c["pool_identical"] and c["pinned_pre_clip_identical"] and c["trees_off_identical"]
    assert c["g_plumb"]["lead0_equals_nowcast"]["pass"] and c["g_plumb"]["lead0_equals_nowcast"]["max_abs"] == 0.0
    assert c["pool_rows_compared"] == len(GROUPS) * 12 * 11 * 12          # every grid row (Y0 on)
    cuts = _cuts(folder)
    assert c["cuts"] == {"fit_cut": cuts[0]["fit_cut"], "guard_cut": cuts[0]["guard_cut"]}
    # the lead path itself ran at lead 0: its fits and its assembled columns equal the nowcast's
    assert c["fits_identical"] == {"c": True, "donor_link_means": True, "tolerances": True}
    assert set(c["bank_inputs"]["identical"]) == {"row_key_hash", "cut", "groups", "grid_rows", "unit_ids",
                                                  "times", "y", "X"}
    pinned = c["pinned"]
    assert {"unit", "group", "time", "year", "lead", "issue", "y", "normal", "arm__" + pinned,
            "arm__identity_trees_off_unweighted", "base__predict_zero", "base__guess_normal",
            "base__last5_normal"} <= set(c["columns_identical"])
    assert "pre__" + pinned in c["columns_identical"]
    assert c["covers"] and "N2 guard" in c["not_covered"] and "persistence" in c["not_covered"]
    assert "guard-cut bank" in c["not_covered"]                         # the contract runs no guard (H2)
    assert c["fallback_levels"].startswith("the nowcast decision surface's")   # H5 applies at leads >= 1
    log = pd.read_parquet(folder / "fitctx_log.parquet")
    part = log[log["part"] == "ladder_contract"]
    assert "ctx_fit_lead_0" in set(part["context"])                     # the lead path's own context
    assert "ctx_guard_lead_0" not in set(part["context"])               # no guard bank at the contract
    assert (part.loc[part["context"] == "ctx_fit_lead_0", "cut"] == cuts[0]["fit_cut"]).all()


def test_each_lead_refits_its_bank_at_its_own_cut(ladder_run):
    _, _, folder = ladder_run
    cuts = _cuts(folder)
    prints = set()
    for lead in LEADS:
        rec = _json(folder / "ladder" / ("lead_%d" % lead) / "lead.json")
        bank = rec["fits"]["bank"]
        assert rec["cuts"] == {"fit_cut": cuts[lead]["fit_cut"], "guard_cut": cuts[lead]["guard_cut"]}
        assert bank["cut"] == cuts[lead]["fit_cut"] and bank["max_label_time"] <= cuts[lead]["fit_cut"]
        prints.add(bank["fingerprint"])
        # owner ruling H2: a second bank, refit at the lead's GUARD cut, with its own guard history block
        g = rec["guard_fits"]
        assert g["refit"] is True and g["rule"].startswith("owner ruling H2")
        assert g["bank"]["cut"] == cuts[lead]["guard_cut"] and g["bank"]["max_label_time"] <= cuts[lead]["guard_cut"]
        assert g["bank"]["trees"] == bank["trees"] and g["bank"]["donor_rows"] < bank["donor_rows"]
        assert g["history"]["cut"] == cuts[lead]["guard_cut"]
        prints.add(g["bank"]["fingerprint"])
        # R11: the fit cut is the train end moved back by L - 1 steps (never later)
        assert cuts[lead]["fit_cut"] == min(cuts[0]["fit_cut"], cuts[0]["fit_cut"] - (lead - 1))
        assert cuts[lead]["guard_cut"] == min(cuts[0]["guard_cut"], cuts[0]["guard_cut"] - (lead - 1))
        assert rec["fits"]["gls_weight_model"].startswith("not refit")    # the nowcast adopted an unweighted arm
        assert rec["fits"]["issue_row_absent"]["test_rows"] == 0          # the pre-Y0 year is a lag source
    assert len(prints) == 2 * len(LEADS)                                  # two new banks per lead (H2)


def test_the_fitctx_log_holds_every_lead_within_its_cuts(ladder_run):
    _, _, folder = ladder_run
    cuts = _cuts(folder)
    log = pd.read_parquet(folder / "fitctx_log.parquet")
    for lead in LEADS:
        part = log[log["part"] == "ladder_lead_%d" % lead]
        fit = part[part["context"] == "ctx_fit_lead_%d" % lead]
        guard = part[part["context"] == "ctx_guard_lead_%d" % lead]
        assert len(fit) and len(guard)
        assert (fit["cut"] == cuts[lead]["fit_cut"]).all() and (fit["lead"] == lead).all()
        assert (guard["cut"] == cuts[lead]["guard_cut"]).all()
        for frame in (fit, guard):
            ok = frame["max_label_time"] >= 0
            assert (frame.loc[ok, "max_label_time"] <= frame.loc[ok, "cut"]).all()     # G-FITCUT
        assert {"bank", "bank_guard", "history_fill", "router_lead_guard", "router_lead_test",
                "damped_persistence_phi"} <= set(part["purpose"])
        # H2: the guard's bank rows and router rows are handed out at the GUARD cut, the test pass's at the fit cut
        assert set(guard.loc[guard["object_kind"] == "donor_rows", "purpose"]) == {"bank_guard"}
        assert "router_lead_guard" in set(guard["purpose"]) and "router_lead_guard" not in set(fit["purpose"])
        hist = part[part["context"] == "ctx_guard_history_lead_%d" % lead]
        assert (hist["cut"] == cuts[lead]["guard_cut"]).all() and "history_fill" in set(hist["purpose"])


def test_the_guard_surface_stands_at_the_lead_cuts(ladder_run):
    _, _, folder = ladder_run
    cuts = _cuts(folder)
    for lead in LEADS:
        g = pd.read_parquet(folder / "ladder" / ("lead_%d" % lead) / "guard_preds.parquet")
        rec = _json(folder / "ladder" / ("lead_%d" % lead) / "lead.json")["guard"]
        assert len(g) == rec["surface_rows"] > 0 and np.isfinite(g["y"]).all()
        assert g["time"].max() <= cuts[lead]["fit_cut"] and g["time"].min() > cuts[0]["guard_cut"]
        assert (g["issue"] == g["time"] - lead).all() and g["issue"].min() >= cuts[lead]["guard_cut"]
        pinned = [c for c in g.columns if c.startswith("arm__") and "trees_off" not in c]
        assert len(pinned) == 1
        mae = float(np.abs(g[pinned[0]] - g["y"]).mean())
        assert mae == pytest.approx(rec["pinned_mae"], abs=1e-12)
        link = pinned[0][len("arm__"):].split("_plain")[0].split("_corrector")[0]
        off = float(np.abs(g["arm__%s_trees_off_unweighted" % link] - g["y"]).mean())
        assert off == pytest.approx(rec["own_trees_off_mae"], abs=1e-12)
        assert rec["passed"] is (mae < off)                              # N2 (R27) at the lead
        # owner ruling H2: the guard bank stands at the lead's guard cut, so no guard row is inside its label
        # window (asserted by the run, recorded here)
        assert rec["bank_cut"] == cuts[lead]["guard_cut"] and rec["bank_max_label_time"] <= cuts[lead]["guard_cut"]
        assert rec["guard_rows_in_bank_label_window"] == 0 and g["time"].min() > rec["bank_max_label_time"]
        assert rec["h2_check"].startswith("asserted")
        # the nowcast's banks were released before the first lead: the guard runs with the lead's two banks
        assert rec["nowcast_banks_held"] == [] and rec["banks_in_memory"] == 2
        # owner ruling H5: the guard searched its own fallback level on this surface
        assert rec["fallback_levels"]["rule"].startswith("owner ruling H5")
        assert rec["fallback_levels"]["levels"] and rec["router"]["fallback_levels"] == rec["fallback_levels"]["levels"]
        doc = _json(folder / ("adoption_lead_%d.json" % lead))
        assert doc["guard_passed"] is rec["passed"]
        assert (doc["adopted"] is None) is (not rec["passed"])           # D86: a failed guard declines


def test_each_lead_saves_every_row_with_its_issue_step_persistence_and_placebo(ladder_run):
    from treeroute.report import metrics as M

    _, _, folder = ladder_run
    now = M.read_rows(folder / "test_preds.parquet")
    y_of = {(u, int(t)): v for u, t, v in zip(now["unit"], now["time"], now["y"])}
    for lead in LEADS:
        rows = M.read_rows(folder / "ladder" / ("lead_%d" % lead) / "test_preds.parquet")
        assert list(rows["unit"]) == list(now["unit"]) and list(rows["time"]) == list(now["time"])
        assert (rows["lead"] == lead).all() and (rows["issue"] == rows["time"] - lead).all()
        # H4: every issue row exists here (the pre-Y0 year is a lag source), so no test row is left out
        h4 = _json(folder / "ladder" / ("lead_%d" % lead) / "lead.json")["issue_features_missing"]
        assert h4["rows_left_out"] == 0 and h4["rows_file"] is None and h4["by_unit"] == {}
        assert not (folder / "ladder" / ("lead_%d" % lead) / "issue_missing_rows.parquet").exists()
        assert np.array_equal(rows["y"].to_numpy(), now["y"].to_numpy(), equal_nan=True)
        assert {"base__persistence", "base__damped_persistence", "base__guess_normal", "base__last5_normal",
                "base__predict_zero"} <= set(rows.columns)
        # persistence = the label at the issue step; checked where the issue step is in the test window
        issue = rows["issue"].to_numpy()
        inside = issue >= now["time"].min()
        want = np.array([y_of.get((u, int(t)), np.nan) for u, t in zip(rows["unit"][inside], issue[inside])])
        got = rows["base__persistence"].to_numpy()[inside]
        assert np.array_equal(got, np.maximum(want, 0.0), equal_nan=True)
        placebos = [c for c in rows.columns if c.startswith("placebo__")]
        assert bool(placebos) is (lead == max(LEADS))                    # the pinned placebo at 12 only
        for c in [c for c in rows.columns if c.startswith(("arm__", "placebo__"))]:
            assert np.isfinite(rows[c]).all()
        assert "arm__identity_trees_off_unweighted" in rows.columns       # the decline target, always built
        rec = _json(folder / "ladder" / ("lead_%d" % lead) / "lead.json")["test"]
        assert rec["same_season_key"] is (lead % 12 == 0)                 # U-2: lead 12 shares the month
        assert rec["persistence_label"]["start_offset_steps"] == 0 and rec["persistence_label"]["gap_steps"] == lead
        assert 0.0 <= rec["phi"]["min"] <= rec["phi"]["max"] <= 1.0


def test_the_ladder_table_scores_common_rows_under_the_nowcast_band(ladder_run):
    _, _, folder = ladder_run
    lad = _json(folder / "ladder" / "ladder.json")
    verdict = _json(folder / "verdict.json")
    assert lad["band"] == verdict["band"] and lad["leads"] == list(LEADS)
    assert set(lad["verdicts"]) == {"0"} | {str(L) for L in LEADS}
    table = pd.read_csv(folder / "ladder" / "ladder_table.csv")
    assert set(table["lead"]) == {0} | set(LEADS) and set(table["ladder_rows"]) == {"common", "all"}
    common = table[(table["ladder_rows"] == "common") & table["adopted"]]
    assert set(common["lead"]) == {0} | set(LEADS) and (common["n"] == lad["common_rows"]).all()
    pinned = table[(table["ladder_rows"] == "common") & (table["column"] == "arm__" + lad["pinned"])]
    assert set(pinned["lead"]) == {0} | set(LEADS)                     # the pinned arm at every lead
    for lead, v in lad["verdicts"].items():
        assert v["common_rows"] == lad["common_rows"]
        if v["adopted"] == v["reference"]:
            assert v["tag"] in ("declined", "identical")
    assert lad["verdicts"]["0"]["adopted"] == "arm__" + verdict["adopted"]
    assert set(lad["rulings"]) == {"H2", "H3", "H4", "H5", "I1"}
    assert {"guard_gls_answers", "issue_missing_scope", "guard_issue_rows"} <= set(lad["readings"])
    assert not {"guard_bank", "context", "missing_issue_rows", "fallback_level", "guard_c_tolerances"}         & set(lad["readings"])
    assert "D63 a" in lad["rulings"]["H2"]          # the guard's fit-cut c is ruled (D63 a), not a reading
    # H4's reading: test rows whose issue row exists but holds a non-finite feature are counted per lead,
    # lead 0 (the nowcast's own rows) included, and nothing is left out for them
    n_test = int(_json(folder / "ladder" / ("lead_%d" % LEADS[0]) / "lead.json")["test"]["test_rows"])
    partly = lad["issue_features_partly_missing"]["by_lead"]
    assert set(partly) == {"0"} | {str(L) for L in LEADS}
    for v in partly.values():
        assert v["test_rows_with_issue_row"] == n_test and v["rows_with_a_nonfinite_context_value"] == 0
        assert 0 <= v["rows_with_a_nonfinite_tree_feature"] <= n_test
    assert lad["issue_rows_left_out"]["by_lead"] == {str(L): {"rows_left_out": 0, "by_unit": {}, "rows_file": None}
                                                     for L in LEADS}
    assert {k: v["guard_rows_in_bank_label_window"] for k, v in lad["guard_bank_label_window"]["by_lead"].items()} \
        == {str(L): 0 for L in LEADS}


# ------------------------------------------------------------------------------------------ features at the issue step
@contextmanager
def _state_after_decision(base, pkg=None, per_group=True):
    """The package (default: the synthetic one) run through Pipeline.run()'s own steps up to the decision
    (adoption locked). per_group=False: the gates' whole-frame path (one column reader of every picked unit)."""
    from treeroute.pipeline import passes as P
    from treeroute.pipeline.run import Pipeline

    pkg = make_pipeline_package(base / "pk") if pkg is None else pkg
    pipe = Pipeline(pkg, base / "runs", "smoke", machine=_machine(base), echo=lambda s: None,
                    launch_record=FAKE_LAUNCH, per_group=per_group)
    try:
        pipe._lock()
        pipe._load()
        pipe._groups()
        pipe._preflight_target()
        pipe._read()
        pipe._derive()
        pipe._smoke_bank_plans(pipe._vault(None))
        pipe._open()
        pipe._temp()
        with P.RunState(pipe) as state:
            state.build_pool(need_inner=True)
            state.fit(need_inner=True)
            state.decision()
            yield pipe, state
    finally:
        pipe._release()


def test_the_lead_features_are_the_issue_step_rows_and_the_history_ends_there(tmp_path):
    """On the whole path's reader (Ladder._moved); the per-group lead pool is checked against it below."""
    from treeroute.pipeline.ladder import Ladder

    with _state_after_decision(tmp_path, per_group=False) as (pipe, state):
        lad = Ladder(state)
        lead = 6
        tree_v, ctx_v, absent = lad._moved(lead)
        reader = pipe.reader
        lagged = reader.lagged(state.derived["R8"].value)
        tcols = list(pipe.spec.tree_features)
        X = lagged[tcols].to_numpy(dtype=np.float32)
        units, steps = state.vg.unit_ids, state.vg.steps
        src = reader.base_rows(units, steps - lead)                     # every issue row exists here
        assert not absent.any()
        assert np.array_equal(tree_v, X[src], equal_nan=True)            # the whole row, from t - L
        C = lagged[list(pipe.spec.context)].to_numpy(dtype=np.float32)
        assert np.array_equal(ctx_v, C[src], equal_nan=True)            # router context moves too (plan 1.5)
        assert not np.array_equal(tree_v, X[reader.base_rows(units, steps)], equal_nan=True)
        # lead 0 gives the nowcast's rows exactly
        t0, c0, _ = lad._moved(0)
        assert np.array_equal(t0, X[reader.base_rows(units, steps)], equal_nan=True)
        # the history block at lead L: hist_last_1 of row t is the label at the issue step t - L
        from treeroute.derive.shapes import CutKind
        from treeroute.fit.context import FitContext

        ctx = FitContext(state.derived, pipe.split_sets, state.vg.grid, state.labels, state.pool, state.lists,
                         lead, CutKind.FIT)
        hist, filled, _ = lad._history(ctx, lead)
        cols = list(state.derived["R17"].value.columns)
        n = int(state.vg.grid.n_steps)
        rows = np.arange(units.size)
        y_issue = state.labels.asof_rows(rows // n, steps - lead, 0, purpose="test")
        ok = np.isfinite(y_issue)
        assert ok.sum() > 0.9 * units.size
        assert np.array_equal(hist[ok, cols.index("hist_last_1")], y_issue[ok].astype(np.float32))
        assert 0.0 < filled["hist_last_1"] < 0.2


def test_the_per_group_lead_pool_is_the_whole_paths(tmp_path):
    """Plan R20: a lead pool filled group by group (RunState.fill_pool_by_group on per-group column readers) holds the
    whole path's Ladder._moved rows byte for byte, with the same 'issue row absent' flags, at lead 0 and every lead."""
    from contextlib import ExitStack

    from treeroute.fit.pool import open_pool
    from treeroute.pipeline import stages as ST
    from treeroute.pipeline import stream as STR
    from treeroute.pipeline.ladder import Ladder

    with _state_after_decision(tmp_path, per_group=False) as (pipe, state):
        lad = Ladder(state)
        whole = pipe.reader
        readers = STR.GroupReaders(pipe.pkg, pipe.spec, pipe.target, pipe.cadence, pipe.feature_hook, lambda s: None,
                                   lambda n: None)
        assert len(readers.groups) > 1
        tree_cols, ctx_cols = lad._tree_columns()
        rows = np.arange(len(state.vg.grid.unit_ids) * lad.n, dtype=np.int64)
        hist = np.full((rows.size, len(tree_cols) - len(pipe.spec.tree_features)), 0.5, dtype=np.float32)
        for L in (0,) + tuple(LEADS):
            tree_v, ctx_v, absent = lad._moved(L)
            with ExitStack() as stack:
                a = stack.enter_context(open_pool(pipe.temp_dir, "pool_w_%d" % L, rows, tree_cols, ctx_cols))
                ST.fill_pool(a, state.vg, lambda r: tree_v[r], lambda r: ctx_v[r], hist, lambda s: None)
                b = stack.enter_context(open_pool(pipe.temp_dir, "pool_g_%d" % L, rows, tree_cols, ctx_cols))
                pipe.reader = readers
                try:
                    flags = state.fill_pool_by_group(b, hist, L)
                finally:
                    pipe.reader = whole
                assert np.array_equal(flags, absent), L
                assert a.tree_features(rows).tobytes() == b.tree_features(rows).tobytes(), L
                assert a.context(rows).tobytes() == b.context(rows).tobytes(), L
        assert readers.builds == len(readers.groups) * (1 + len(LEADS))


# ------------------------------------------------------------------------------------------ the gates, planted
def test_unit_gls_weights_give_the_unweighted_bytes_in_the_test_pass(tmp_path):
    """The weighted-kernel gate through the whole test pass: with every R25 weight 1 each GLS arm and its
    placebo (the weighted solve of route.solve, per unit, at the pinned penalty) are byte for byte the
    unweighted twins, before and after the legal clip."""
    from treeroute.report import metrics as M

    with _state_after_decision(tmp_path) as (pipe, state):
        state.weights_fn = lambda model, features: (lambda keys: np.ones(np.asarray(keys).size))
        state.test_pass()
        rows = M.read_rows(pipe.folder / "test_preds.parquet")
    gls = [c for c in rows.columns if c.endswith("_gls")]
    assert len(gls) == 2 * 3 * 2                        # 2 links x (plain, corrector, placebo) x (saved, pre-clip)
    for c in gls:
        twin = c[:-len("_gls")] + "_unweighted"
        assert np.array_equal(rows[c].to_numpy(), rows[twin].to_numpy()), c


def test_the_lead_zero_contract_refuses_a_planted_fault(tmp_path, monkeypatch):
    """The lead-0 contract is a check, not a record: a lead-0 pool that is not the nowcast's, and a pinned
    route that is not the nowcast's (another penalty), are each refused (G-PLUMB) and leave no contract
    file; the unplanted ladder then holds the contract."""
    from treeroute.pipeline import ladder as LAD
    from treeroute.route import kinds as RK

    with _state_after_decision(tmp_path) as (pipe, state):
        state.test_pass()
        real_move = LAD.features_at_issue_step

        def moved_wrong(X, codes, steps, lead):
            out = real_move(X, codes, steps, lead)
            return out + np.float32(1.0) if lead == 0 else out          # NaN stays NaN; every value moves
        monkeypatch.setattr(LAD, "features_at_issue_step", moved_wrong)
        with pytest.raises(LAD.LadderRefusal, match="lead-0 pool differs from the nowcast pool"):
            LAD.Ladder(state).contract()
        monkeypatch.setattr(LAD, "features_at_issue_step", real_move)
        lad = LAD.Ladder(state)
        grid = RK.per_unit_grid(lad.pin_point.ratio is not None)
        lad.pin_point = next(p for p in grid if p != lad.pin_point)
        with pytest.raises(LAD.LadderRefusal, match="lead-0 contract FAILED"):
            lad.contract()
        assert not (pipe.folder / "ladder" / LAD.CONTRACT_FILE).exists()
        rec = LAD.Ladder(state).contract()
        assert rec["pool_identical"] and rec["pinned_pre_clip_identical"] and rec["trees_off_identical"]
        assert (pipe.folder / "ladder" / LAD.CONTRACT_FILE).is_file()


# ------------------------------------------------------------------------------------------ resume inside a lead
def test_a_crash_inside_a_lead_resumes_from_its_locked_lead_adoption(tmp_path, monkeypatch):
    from treeroute.report import metrics as M

    pkg = make_pipeline_package(tmp_path / "pk")
    real = M.assemble_rows

    def crash(keys, lead, *args, **kwargs):
        if lead == 12:
            raise RuntimeError("simulated power cut inside lead 12, after its test labels opened")
        return real(keys, lead, *args, **kwargs)
    monkeypatch.setattr(M, "assemble_rows", crash)
    with pytest.raises(RuntimeError, match="simulated power cut"):
        _run(pkg, tmp_path)
    folder = next((tmp_path / "runs" / "synth_pkg" / "smoke").iterdir())
    assert (folder / "adoption_lead_12.json.lock.json").is_file()
    assert (folder / "test_labels_opened_lead_12.json").is_file()
    assert (folder / "phases" / "ladder_lead_6" / "DONE").is_file()
    assert not (folder / "phases" / "ladder_lead_12" / "DONE").exists() and not (folder / "DONE.json").exists()
    assert list((tmp_path / "temp").iterdir()) == []                   # every temp file released on the crash
    sha = _sha(folder / "adoption_lead_12.json")
    lead6 = _sha(folder / "ladder" / "lead_6" / "test_preds.parquet")
    monkeypatch.undo()
    again = Path(_run(pkg, tmp_path))
    assert again == folder and (folder / "DONE.json").is_file()
    assert _sha(folder / "adoption_lead_12.json") == sha               # never re-decided (its guard bank refit, H2)
    assert _sha(folder / "ladder" / "lead_6" / "test_preds.parquet") == lead6   # a done lead is not redone
    assert "resumed from the locked adoption_lead_12.json" in (folder / "run.log").read_text(encoding="utf-8")
    assert (folder / "ladder" / "lead_12" / "test_preds.parquet").is_file()


# ------------------------------------------------------------------------------------------ a weighted pin
def test_a_gls_adoption_pins_a_weighted_arm_and_refits_the_weights_at_every_lead(tmp_path, monkeypatch):
    """The layer is stood in to prefer an eligible GLS arm (layer.decide.select_adoption's result moved to
    that arm and its own pick), so the ladder pins a weighted arm: R25's weight model is refit at each
    lead's cut, and the weighted route runs at the guard and the test pass of every lead."""
    from treeroute.layer import arms as LA
    from treeroute.layer import decide as LD

    real = LD.select_adoption

    def prefer_gls(picks, trees_off_mae, beside, order=None):
        ad = real(picks, trees_off_mae, beside, order=order)
        gls = [p for p in picks if p.arm.weighting is LA.Weighting.GLS and p.arm in ad.eligible]
        if ad.declined or not gls:
            return ad
        best = min(gls, key=lambda p: p.mae)
        return _replace(ad, adopted=best.arm, penalty=best.point, best_tree_arm=best.arm, best_tree_penalty=best.point)
    monkeypatch.setattr(LD, "select_adoption", prefer_gls)
    pkg = make_pipeline_package(tmp_path / "pk")
    folder = Path(_run(pkg, tmp_path))
    adoption = _json(folder / "adoption.json")
    assert adoption["adopted"]["weighting"] == "gls"
    lad = _json(folder / "ladder" / "ladder.json")
    assert lad["pinned"].endswith("_gls")
    for lead in LEADS:
        d = folder / "ladder" / ("lead_%d" % lead)
        assert (d / "gls_weight_model.json").is_file()
        rec = _json(d / "lead.json")
        assert rec["fits"]["gls_weight_model"].startswith("refit")
        wm = _json(d / "gls_weight_model.json")
        assert wm["inputs"]["lead"] == lead and wm["inputs"]["cut"] == _cuts(folder)[lead]["guard_cut"]
    contract = _json(folder / "ladder" / "contract_lead_0.json")
    assert contract["pinned_pre_clip_identical"] is True
    assert contract["fits_identical"]["gls_weight_model"] is True       # the lead path's GLS refit at lead 0


# ------------------------------------------------------------------------------------------ R12: the fallback, the region kind
def test_short_history_units_take_their_groups_region_fallback(tmp_path):
    from treeroute.report import metrics as M

    pkg = make_pipeline_package(tmp_path / "pk", name="synth_sparse", sparse=True)
    folder = Path(_run(pkg, tmp_path))
    short = sorted("%s_%d_%d" % (SPARSE_GROUP, GROUPS[SPARSE_GROUP][0] + i % 4, GROUPS[SPARSE_GROUP][1] + i // 4)
                   for i in SPARSE_UNITS)
    checks = _json(folder / "decision_checks.json")
    assert checks["router_kind"] == "per_unit"
    fb = checks["fallback"]
    for key in ("identity|plain", "identity|corrector", "log_c|plain", "log_c|corrector"):
        assert fb[key]["short_units"] == short and fb[key]["groups"] == {SPARSE_GROUP: short}
        lv = checks["fallback_levels"][key]
        assert lv["used_centre"] is True and lv["fallback_units_scored"] == len(short)   # C15: under 10 units
    assert checks["fallback_gls_note"]
    rows = M.read_rows(folder / "test_preds.parquet")
    sub = rows[rows["unit"].isin(short)]
    assert len(sub) == len(short) * 48
    for c in [c for c in rows.columns if c.startswith(("arm__", "placebo__"))]:
        assert np.isfinite(rows[c]).all(), c
    guard = _json(folder / "guard_report.json")["ran"]["R12"]
    assert guard["router_kind"] == "per_unit" and guard["fallback_decision_surface"]
    assert (folder / "DONE.json").is_file() and (folder / "ladder" / "ladder.json").is_file()


def test_a_region_package_routes_by_group_without_gls_and_runs_the_ladder(tmp_path, monkeypatch):
    """R12 stood in to the REGION outcome (C5's per-unit threshold raised above every unit's history), so
    the region kernels of route/region.py route every pass: one pooled ridge per group on its capped bank
    units, the tree-block Gram shared across the links (L4); no weighted solve exists, so the GLS arms are
    absent under the declared reason and no weight model is fitted."""
    from treeroute import engine_constants as K
    from treeroute.report import metrics as M

    monkeypatch.setattr(K, "PER_UNIT_MIN_VALID_ROWS", 10000)
    pkg = make_pipeline_package(tmp_path / "pk", name="synth_region")
    folder = Path(_run(pkg, tmp_path))
    derived = _json(folder / "derived.json")
    assert derived["R12"]["value"] == "region"
    checks = _json(folder / "decision_checks.json")
    assert checks["router_kind"] == "region" and checks["gls"]["routed"] is False
    assert checks["region"]["capped_units_fitted_by_group"] == {g: 12 for g in GROUPS}
    for link in ("identity", "log_c"):
        assert checks["g_plumb"][link]["trees_off_equals_normal"]["pass"]
        assert checks["g_plumb"][link]["base_point_reproduces_unswept"]["pass"]
    adoption = _json(folder / "adoption.json")
    assert adoption["decision"]["missing_arms"] == ["identity_plain_gls", "identity_corrector_gls",
                                                    "log_c_plain_gls", "log_c_corrector_gls"]
    assert adoption["decision"]["gls_absent_reason"].startswith("the region router kind has no weighted solve")
    point = adoption["penalty"] or adoption["best_tree_penalty"]
    assert point["ratio"] is None                                       # the region grid: levels only
    assert _json(folder / "gls_weight_model.json")["fitted"] is False
    rows = M.read_rows(folder / "test_preds.parquet")
    assert not [c for c in rows.columns if c.endswith("_gls")]
    for c in [c for c in rows.columns if c.startswith(("arm__", "placebo__"))]:
        assert np.isfinite(rows[c]).all(), c
    assert len(_json(folder / "verdict.json")["band_pairs"]) == 6
    lad = _json(folder / "ladder" / "ladder.json")
    assert set(lad["verdicts"]) == {"0"} | {str(L) for L in LEADS}
    assert _json(folder / "ladder" / "contract_lead_0.json")["pinned_pre_clip_identical"] is True


def test_the_neighbour_kind_is_refused_before_any_fit(tmp_path, monkeypatch):
    from treeroute import engine_constants as K

    monkeypatch.setattr(K, "PER_UNIT_MIN_VALID_ROWS", 10000)
    monkeypatch.setattr(K, "REGION_MIN_VALID_ROWS", 5000)
    pkg = make_pipeline_package(tmp_path / "pk", name="synth_nb")
    with pytest.raises(NotImplementedError, match="neighbour router kind"):
        _run(pkg, tmp_path)
    folder = next((tmp_path / "runs" / "synth_nb" / "smoke").iterdir())
    assert not (folder / "adoption.json").exists() and not (folder / "gls_weight_model.json").exists()
    assert list((tmp_path / "temp").iterdir()) == []


def test_the_lead_zero_contract_checks_the_lead_paths_own_bank_inputs_fits_and_columns(tmp_path, monkeypatch):
    """The contract runs the lead path's own per-lead code at lead 0, so a fault there is refused too (not
    only a fault in the feature move): the lead bank's donor rows asked at another cut, a tolerance that is
    not the nowcast's, and an assembled baseline column that is not the nowcast's are each refused (G-PLUMB)
    and leave no contract file."""
    from treeroute.derive.shapes import CutKind
    from treeroute.fit.context import FitContext
    from treeroute.pipeline import ladder as LAD

    with _state_after_decision(tmp_path) as (pipe, state):
        state.test_pass()
        # the hand-out the run uses: donor_rows_lazy per group (plan R20), donor_rows on the whole path
        name = "donor_rows_lazy" if state.per_group else "donor_rows"
        real_donor = getattr(FitContext, name)

        def donor_at_lead_6(self, purpose, unit_ids=None):
            if purpose == "bank" and self.lead == 0 and self.features is not state.pool:
                return real_donor(self.for_lead(6, CutKind.FIT), purpose, unit_ids)
            return real_donor(self, purpose, unit_ids)
        monkeypatch.setattr(FitContext, name, donor_at_lead_6)
        with pytest.raises(LAD.LadderRefusal, match="donor rows differ from the nowcast bank's"):
            LAD.Ladder(state).contract()
        monkeypatch.setattr(FitContext, name, real_donor)

        real_tol = LAD.ST.guard_tolerances

        def tol_doubled(*args, **kwargs):
            tol, rec = real_tol(*args, **kwargs)
            return {L: 2.0 * v for L, v in tol.items()}, rec
        monkeypatch.setattr(LAD.ST, "guard_tolerances", tol_doubled)
        with pytest.raises(LAD.LadderRefusal, match=r"\['tolerances'\] differ"):
            LAD.Ladder(state).contract()
        monkeypatch.setattr(LAD.ST, "guard_tolerances", real_tol)

        real_base = LAD.Ladder._common_baselines

        def last5_moved(self, *args):
            return {k: (v + 1e-3 if k == "last5_normal" else v) for k, v in real_base(self, *args).items()}
        monkeypatch.setattr(LAD.Ladder, "_common_baselines", last5_moved)
        with pytest.raises(LAD.LadderRefusal, match=r"lead-0 contract FAILED.*\['base__last5_normal'\] differ"):
            LAD.Ladder(state).contract()
        monkeypatch.setattr(LAD.Ladder, "_common_baselines", real_base)
        assert not (pipe.folder / "ladder" / LAD.CONTRACT_FILE).exists()
        rec = LAD.Ladder(state).contract()
        assert rec["pool_identical"] and rec["fits_identical"]["tolerances"]


# ------------------------------------------------------------------------------------------ R12: an all-short pass
def test_an_all_short_pass_is_routed_whole_by_the_fallback_region_routers(tmp_path, monkeypatch):
    """R12 at a long lead: when EVERY scored unit of a pass is short, pipeline/router.py does not call the
    per-unit kernels (which still refuse a pass with no unit to fit): every row starts NaN and the groups'
    fallback region routers fill them all, a trees-off-only link included."""
    from treeroute import engine_constants as K
    from treeroute.derive.shapes import Link
    from treeroute.layer import arms as LA
    from treeroute.layer import decide as LD
    from treeroute.pipeline import router as PR
    from treeroute.pipeline import stages as ST
    from treeroute.route import kinds as RK

    with _state_after_decision(tmp_path) as (pipe, state):
        pinned, point = LD.pin_of(state.adoption)
        kind = LA.table_kind(pinned)
        state._build_tables(state.store_fit, state.pool, (kind,), None, "test")
        keys = ST.unit_positions(state.vg, state.scored_units, state.vg.test_first, None)
        units, steps = state.vg.unit_ids[keys], state.vg.steps[keys]
        other = Link.LOG_C if pinned.link == Link.IDENTITY else Link.IDENTITY
        monkeypatch.setattr(K, "PER_UNIT_MIN_VALID_ROWS", 10 ** 6)
        inp = PR.PassInput("all short", state.ctx_fit, state.store_fit, state.masks_fit, state.pool, units, steps,
                           keys, state.tol, state.donor_mean_fit, "router_all_short", state.c)
        wfn = state.weights_fn(state.weights, state.pool) if pinned.weighting is LA.Weighting.GLS else None
        router = PR.PassRouter(state, inp, state.kind, weights=wfn, fallback_levels=state.decided_levels())
        routed = router.route([pinned], point, extra_trees_off=(other,))
        n_units = len(state.scored_units)
        assert routed.records["all_short"] == {pinned.link.value: n_units, other.value: n_units}
        fb = routed.records["fallback"]["%s|%s" % (pinned.link.value, kind)]
        assert fb["short_units"] == sorted(state.scored_units)
        assert np.isfinite(routed.predictions[LA.arm_name(pinned)]).all()
        for L in (pinned.link, other):
            gap = np.abs(routed.trees_off[L] - routed.score_normal[L])
            assert np.isfinite(gap).all() and gap.max() <= state.tol[L]     # R16 from the fallback routers
        with pytest.raises(RK.RouteRefusal, match="all short.*pipeline/router.py"):
            RK._route_per_unit_at(router._per_unit_rows(pinned.link), state.store_fit, kind, state.masks_fit,
                                  point, state.tol[pinned.link])


# ------------------------------------------------------------------------------------------ R17's start offset at the leads
REACH_OLD = "    window: {length: 1, unit: month, align: backward}\n    stamp: period_end\n"
REACH_NEW = ("    window: {length: 1, unit: month, align: backward, reach_after_max: {value: 5, unit: day}}\n"
             "    stamp: period_end\n")


def make_reach_package(root, name="synth_reach"):
    """The synthetic package with a target window reaching 5 days past its month, so R17's start offset is 1
    (as for a target whose label window closes after its step): a label is not known at its own step's end."""
    pkg = make_pipeline_package(root, name=name)
    cat = pkg / "catalog.yaml"
    text = cat.read_text(encoding="utf-8")
    assert text.count(REACH_OLD) == 1
    cat.write_text(text.replace(REACH_OLD, REACH_NEW), encoding="utf-8")
    return pkg


def test_persistence_reads_the_history_blocks_newest_label_when_the_target_reaches_past_its_step(tmp_path):
    """R17 / R31: with start offset 1 the newest readable label at lead L is t - L - 1, the history block's
    hist_last_1, never the issue step's own label t - L (its window has not closed at the issue step);
    damped persistence pairs labels L + 1 apart and applies the season-key rule to that gap."""
    from types import SimpleNamespace

    from treeroute.derive.shapes import CutKind
    from treeroute.fit.context import FitContext
    from treeroute.pipeline.ladder import Ladder

    pkg = make_reach_package(tmp_path / "pk")
    with _state_after_decision(tmp_path, pkg) as (pipe, state):
        spec17 = state.derived["R17"].value
        assert spec17.start_offset_steps == 1
        lad = Ladder(state)
        t_keys, t_units, t_steps = lad._test_rows()
        cols = list(spec17.columns)
        n = int(state.vg.grid.n_steps)
        for lead in LEADS:
            ctx = FitContext(state.derived, pipe.split_sets, state.vg.grid, state.labels, state.pool, state.lists,
                             lead, CutKind.FIT)
            hist, _, _ = lad._history(ctx, lead)
            pers = lad._persistence_inputs(SimpleNamespace(lead=lead, ctx_fit=ctx), t_keys, t_units, t_steps)
            assert pers["gap"] == lead + 1 and pers["start_offset_steps"] == 1
            assert np.array_equal(pers["label_step"], t_steps - lead - 1)
            assert pers["same_season_key"] is ((lead + 1) % 12 == 0)
            y = pers["y_issue"]
            ok = np.isfinite(y)
            assert ok.sum() > 0.9 * t_keys.size
            assert np.array_equal(y[ok].astype(np.float32), hist[t_keys, cols.index("hist_last_1")][ok])
            own = state.labels.asof_rows(t_keys // n, t_steps - lead, 0, purpose="test")
            both = ok & np.isfinite(own)
            assert not np.array_equal(own[both], y[both])                  # the old (look-ahead) read differs


def test_a_reaching_target_saves_offset_persistence_at_every_lead(tmp_path):
    """End to end on the offset-1 package: every lead saves persistence as the label L + 1 steps back (its
    issue step stays t - L), records the gap, and the run finishes."""
    from treeroute.report import metrics as M

    pkg = make_reach_package(tmp_path / "pk")
    folder = Path(_run(pkg, tmp_path))
    assert _json(folder / "derived.json")["R17"]["value"]["start_offset_steps"] == 1
    now = M.read_rows(folder / "test_preds.parquet")
    y_of = {(u, int(t)): v for u, t, v in zip(now["unit"], now["time"], now["y"])}
    for lead in LEADS:
        rows = M.read_rows(folder / "ladder" / ("lead_%d" % lead) / "test_preds.parquet")
        assert (rows["issue"] == rows["time"] - lead).all()
        label = rows["time"].to_numpy() - lead - 1
        inside = label >= now["time"].min()
        assert inside.sum() > 0.5 * len(rows)
        want = np.array([y_of.get((u, int(t)), np.nan) for u, t in zip(rows["unit"][inside], label[inside])])
        assert np.array_equal(rows["base__persistence"].to_numpy()[inside], np.maximum(want, 0.0), equal_nan=True)
        rec = _json(folder / "ladder" / ("lead_%d" % lead) / "lead.json")["test"]
        assert rec["persistence_label"]["start_offset_steps"] == 1
        assert rec["persistence_label"]["gap_steps"] == lead + 1
        assert rec["same_season_key"] is ((lead + 1) % 12 == 0)
    assert (folder / "DONE.json").is_file()


# ------------------------------------------------------------------------------------------ owner ruling I1: the lead set
def test_the_leads_are_6_and_12_months_and_leads_1_and_3_never_run(ladder_run):
    """Owner ruling I1: the engine's lead constant (R10) is 6 and 12 months, plus lead 0 (the contract); on this
    monthly package R10 gives leads 6 and 12, the cuts exist for 0, 6 and 12 only, and nothing of a lead 1 or 3
    is written anywhere (no lock, no opened labels, no lead folder, no phase)."""
    from treeroute import engine_constants as K

    _, _, folder = ladder_run
    assert K.LEAD_MONTHS == (6, 12) and K.get("C6.lead_months") == (6, 12)
    r10 = _json(folder / "derived.json")["R10"]["value"]
    assert r10["requested_months"] == [6, 12] and r10["leads"] == [6, 12] == list(LEADS)
    assert r10["merged"] == {} and r10["not_supplied"] == [] and r10["contract_lead_zero"] is True
    assert sorted(_cuts(folder)) == [0, 6, 12]
    assert sorted(p.name for p in (folder / "ladder").iterdir() if p.is_dir()) == ["lead_12", "lead_6"]
    phases = sorted(p.name for p in (folder / "phases").iterdir() if p.name.startswith("ladder_lead_"))
    assert phases == ["ladder_lead_12", "ladder_lead_6"]
    for lead in (1, 3):
        for name in ("adoption_lead_%d.json" % lead, "adoption_lead_%d.json.lock.json" % lead,
                     "test_labels_opened_lead_%d.json" % lead, "ladder/lead_%d" % lead, "phases/ladder_lead_%d" % lead):
            assert not (folder / name).exists(), name
    assert _json(folder / "ladder" / "ladder.json")["longest_lead"] == 12      # the pinned placebo's lead


# ------------------------------------------------------------------------------------------ owner ruling H4, planted
def _plant_absent_issue_rows(monkeypatch, pick):
    """Stand in an absent issue row (the case H4 rules; the dense census never gives one on a test row here): at
    every lead L >= 1 the rows pick(ladder, L) get absent=True and NaN moved features and context, exactly what
    io.apply.features_at_issue_step gives a row without a predecessor. Returns {lead: planted grid rows}."""
    from treeroute.pipeline import ladder as LAD

    real = LAD.Ladder._moved
    real_group = LAD.Ladder._moved_group
    planted = {}

    def moved(self, L):                                   # the whole path's seam
        tree_v, ctx_v, absent = real(self, L)
        if L > 0:
            rows = np.asarray(pick(self, L), dtype=np.int64)
            absent = absent.copy()
            absent[rows] = True
            tree_v = tree_v.copy()
            tree_v[rows] = np.nan
            if ctx_v is not None:
                ctx_v = ctx_v.copy()
                ctx_v[rows] = np.nan
            planted[L] = rows
        return tree_v, ctx_v, absent

    def moved_group(self, L, rows, tree_v, ctx_v, absent):      # the per-group path's seam (plan R20)
        tree_v, ctx_v, absent = real_group(self, L, rows, tree_v, ctx_v, absent)
        if L > 0:
            hit = np.isin(rows, np.asarray(pick(self, L), dtype=np.int64))
            if hit.any():
                absent = absent.copy()
                absent[hit] = True
                tree_v = tree_v.copy()
                tree_v[hit] = np.nan
                if ctx_v is not None:
                    ctx_v = ctx_v.copy()
                    ctx_v[hit] = np.nan
                planted[L] = np.sort(np.concatenate([planted.get(L, np.zeros(0, dtype=np.int64)), rows[hit]]))
        return tree_v, ctx_v, absent
    monkeypatch.setattr(LAD.Ladder, "_moved", moved)
    monkeypatch.setattr(LAD.Ladder, "_moved_group", moved_group)
    return planted


def test_a_test_row_whose_issue_row_is_absent_is_left_out_of_scoring_saved_flagged_and_counted(tmp_path, monkeypatch):
    """Owner ruling H4 end to end: five test rows (three of the first scored unit, two of the last) lose their
    issue row at every lead. Each lead leaves them out of scoring (they are not in its test_preds, so no score or
    common row holds them, and their NaN context never reaches G1's scored-row refusal), saves them in
    issue_missing_rows.parquet with the flag, and counts them per unit and lead; lead 0 (the contract) is
    untouched and still equals the nowcast byte for byte."""
    from treeroute.report import metrics as M

    def pick(lad, L):
        keys = lad._test_rows()[0]
        return keys[[0, 1, 2, -2, -1]]
    planted = _plant_absent_issue_rows(monkeypatch, pick)
    pkg = make_pipeline_package(tmp_path / "pk")
    folder = Path(_run(pkg, tmp_path))
    assert (folder / "DONE.json").is_file()
    assert _json(folder / "ladder" / "contract_lead_0.json")["pinned_pre_clip_identical"] is True
    now = M.read_rows(folder / "test_preds.parquet")
    key = lambda f: list(zip(f["unit"].tolist(), f["time"].astype(int).tolist()))     # noqa: E731
    all_keys = key(now)
    lost = [all_keys[i] for i in (0, 1, 2, len(all_keys) - 2, len(all_keys) - 1)]
    y_now = dict(zip(all_keys, now["y"].tolist()))
    lad = _json(folder / "ladder" / "ladder.json")
    for lead in LEADS:
        assert planted[lead].size == 5
        d = folder / "ladder" / ("lead_%d" % lead)
        rows = M.read_rows(d / "test_preds.parquet")
        assert key(rows) == [k for k in all_keys if k not in lost]            # absent from the scored rows
        saved = pd.read_parquet(d / "issue_missing_rows.parquet")
        assert key(saved) == lost and saved["issue_features_missing"].all()   # present in the saved rows, flagged
        assert (saved["reason"] == "issue_row_absent").all() and (saved["lead"] == lead).all()
        assert (saved["issue"] == saved["time"] - lead).all()
        assert np.array_equal(saved["y"].to_numpy(), np.array([y_now[k] for k in lost]), equal_nan=True)
        rec = _json(d / "lead.json")
        h4 = rec["issue_features_missing"]
        assert h4 == rec["test"]["issue_features_missing"] and h4["rule"].startswith("owner ruling H4")
        assert h4["rows_left_out"] == 5 and h4["units_with_rows_left_out"] == 2          # counted per unit and lead
        assert h4["by_unit"] == {lost[0][0]: 3, lost[-1][0]: 2}
        assert h4["rows_file"] == "ladder/lead_%d/issue_missing_rows.parquet" % lead
        assert rec["fits"]["issue_row_absent"]["test_rows"] == 5
        assert rec["test"]["rows"] == len(all_keys) - 5 and rec["test"]["test_rows"] == len(all_keys)
        assert lad["issue_rows_left_out"]["by_lead"][str(lead)]["rows_left_out"] == 5
        # no score holds them: every lead's 'all rows' line counts only its scored labelled rows
        table = pd.read_csv(folder / "ladder" / "ladder_table.csv")
        line = table[(table["lead"] == lead) & (table["ladder_rows"] == "all") & table["adopted"]]
        assert int(line["n"].iloc[0]) == int(np.isfinite(rows["y"]).sum())
    labelled = {k for k, v in y_now.items() if np.isfinite(v)}
    assert lad["common_rows"] == len(labelled - set(lost))                    # absent from the common rows
    log = (folder / "run.log").read_text(encoding="utf-8")
    assert "lead 12 test pass: H4 left 5 test row(s) of 2 unit(s) out of scoring" in log


def test_a_guard_row_without_its_issue_row_refuses_and_the_h2_check_is_live(tmp_path, monkeypatch):
    """H4 names test rows: a GUARD-surface row whose issue row is absent refuses loudly (never scored on NaN
    features, never left out without a ruling). The H2 check is live: a guard handed the lead's FIT-cut bank as
    if it were refit at the guard cut refuses, because its guard rows lie inside that bank's label window. The
    router refuses a pass that both searches its own fallback level and reads another surface's."""
    from treeroute.layer import decide as LD
    from treeroute.pipeline import ladder as LAD
    from treeroute.pipeline import router as PR

    with _state_after_decision(tmp_path) as (pipe, state):
        state.test_pass()
        guard_first = int(state.cuts.guard_cut) + 1
        lead = min(LEADS)

        def guard_rows(lad, L):
            u0 = state.scored_units[0]
            row = list(state.vg.grid.unit_ids).index(u0)
            steps = np.arange(guard_first, int(lad.cuts[L].fit_cut) + 1, dtype=np.int64)
            return row * lad.n + (steps - int(state.vg.first_step))
        with monkeypatch.context() as mp:
            _plant_absent_issue_rows(mp, guard_rows)
            with pytest.raises(LAD.LadderRefusal, match=r"\[H4\] lead %d: \d+ guard-surface row" % lead):
                LAD.Ladder(state).run_lead(lead)
        assert not (pipe.folder / ("adoption_lead_%d.json" % lead)).exists()        # refused before the lock
        real_go = LAD.Ladder._guard_objects

        def fit_bank_as_guard(self, o, stack):
            g = real_go(self, o, stack)
            return _replace(g, bank=o.bank, store=o.store, masks=o.masks)     # still claims the H2 refit
        with monkeypatch.context() as mp:
            mp.setattr(LAD.Ladder, "_guard_objects", fit_bank_as_guard)
            with pytest.raises(LAD.LadderRefusal, match=r"\[H2\] lead %d: \d+ guard row\(s\) are dated at or before"
                                                        % lead):
                LAD.Ladder(state).run_lead(lead)
        assert not (pipe.folder / ("adoption_lead_%d.json" % lead)).exists()
        pinned, point = LD.pin_of(state.adoption)
        keys = np.zeros(0, dtype=np.int64)
        inp = PR.PassInput("probe", state.ctx_fit, state.store_fit, state.masks_fit, state.pool,
                           np.zeros(0, dtype=object), keys, keys, state.tol, state.donor_mean_fit, "probe", state.c)
        with pytest.raises(PR.RouterRefusal, match=r"\[R12\] probe: a pass that searches its own fallback level"):
            PR.PassRouter(state, inp, state.kind, fallback_levels=state.decided_levels() or {"x": {}},
                          search_levels=True)
        with pytest.raises(PR.RouterRefusal, match=r"level_tables are searched only by a pass with search_levels"):
            PR.PassRouter(state, inp, state.kind).route([pinned], point, level_tables=((pinned.link, "corrector"),))
    assert list((tmp_path / "temp").iterdir()) == []                          # every temp file released


# ------------------------------------------------------------------------------------------ owner ruling H5
def test_each_lead_searches_its_own_fallback_level_on_its_guard_surface(tmp_path, monkeypatch):
    """Owner ruling H5 on the sparse package (two grp_c units are short-history at every guard and test pass),
    with C15's search threshold stood in at 1 fallback unit so the search, not the lambda centre, decides: each
    lead's guard routes the pinned arm at the pinned penalty and searches the fallback level on its OWN surface
    (the level is the argmin of that surface's pooled fallback MAE, recorded with every level's MAE); the lead's
    test pass fills its short units at that level; at the longest lead the corrector table's level is searched
    too (the placebo takes its corrector's level). The surface MAEs are the lead's, not the nowcast's."""
    from treeroute import engine_constants as K

    monkeypatch.setattr(K, "FALLBACK_MIN_UNITS_FOR_SEARCH", 1)
    pkg = make_pipeline_package(tmp_path / "pk", name="synth_sparse_h5", sparse=True)
    folder = Path(_run(pkg, tmp_path))
    short = sorted("%s_%d_%d" % (SPARSE_GROUP, GROUPS[SPARSE_GROUP][0] + i % 4, GROUPS[SPARSE_GROUP][1] + i // 4)
                   for i in SPARSE_UNITS)
    adoption = _json(folder / "adoption.json")
    pinned = adoption["adopted"] if not adoption["declined"] else adoption["best_tree_arm"]
    key = "%s|%s" % (pinned["link"], pinned["tool"])
    nowcast = _json(folder / "decision_checks.json")["fallback_levels"]
    for lead in LEADS:
        rec = _json(folder / "ladder" / ("lead_%d" % lead) / "lead.json")
        levels = rec["guard"]["fallback_levels"]["levels"]
        assert rec["fallback_levels"]["levels"] == levels and rec["fallback_levels"]["source"] == \
            "the lead's own guard surface"
        lv = levels[key]
        assert lv["used_centre"] is False and lv["fallback_units_scored"] == len(short)
        mae = {float(k): v for k, v in lv["surface_mae_by_level"].items()}
        assert len(mae) == 7 and lv["level"] == min(mae, key=lambda k: (mae[k], sorted(mae).index(k)))
        assert lv["surface_mae_by_level"] != nowcast[key]["surface_mae_by_level"]    # its own surface
        assert rec["guard"]["router"]["fallback"][key]["short_units"] == short
        test_fb = rec["test"]["router"]["fallback"][key]
        assert test_fb["short_units"] == short and test_fb["level"] == lv["level"]  # the test pass reads it
        corrector_key = "%s|corrector" % pinned["link"]
        assert (corrector_key in levels) is (lead == max(LEADS) or pinned["tool"] == "corrector")
        if lead == max(LEADS):
            placebo_key = "%s|placebo_corrector" % pinned["link"]
            assert rec["test"]["router"]["fallback"][placebo_key]["level"] == levels[corrector_key]["level"]
    assert (folder / "DONE.json").is_file()


# ------------------------------------------------------------------------------------------ H4's reading, counted
def test_issue_rows_with_a_nonfinite_feature_are_counted_per_lead_and_kept(tmp_path, monkeypatch):
    """READINGS issue_missing_scope: a test row whose issue row EXISTS but holds a non-finite moved tree feature
    is not left out (the trees read it 0-filled, R30, as the nowcast's own rows), and it is counted per lead in
    lead.json fits.issue_features_partly_missing, by column. Planted: one tree column NaN on four test rows at
    lead 6 (their issue rows stay present)."""
    from treeroute.pipeline import ladder as LAD

    real_group = LAD.Ladder._moved_group
    planted = {"rows": np.zeros(0, dtype=np.int64), "before": {}}

    def moved_group(self, L, rows, tree_v, ctx_v, absent):      # the per-group path's seam (plan R20)
        tree_v, ctx_v, absent = real_group(self, L, rows, tree_v, ctx_v, absent)
        if L == min(LEADS):
            keys = self._test_rows()[0]
            at = np.flatnonzero(np.isin(rows, keys))
            for r, i in zip(rows[at].tolist(), at.tolist()):
                planted["before"][r] = tree_v[i].copy()
            room = 4 - planted["rows"].size
            ok = at[np.isfinite(tree_v[at]).all(axis=1)][:max(room, 0)]
            if ok.size:
                tree_v = tree_v.copy()
                tree_v[ok, 0] = np.nan
                planted["rows"] = np.concatenate([planted["rows"], rows[ok]])
        return tree_v, ctx_v, absent
    monkeypatch.setattr(LAD.Ladder, "_moved_group", moved_group)
    from contextlib import ExitStack

    with _state_after_decision(tmp_path) as (pipe, state):
        lad = LAD.Ladder(state)
        col = list(pipe.spec.tree_features)[0]
        keys = lad._test_rows()[0]
        with ExitStack() as stack:
            o = lad._objects(min(LEADS), stack)
            rec = o.record["issue_features_partly_missing"]
            assert planted["rows"].size == 4
            assert not np.asarray(o.issue_absent)[planted["rows"]].any()     # kept: H4 leaves out absent rows only
            before = np.stack([planted["before"][int(k)] for k in keys])
            want_rows = int((~np.isfinite(before)).any(axis=1).sum()) + 4
            assert rec["tree_features"]["rows"] == want_rows
            assert rec["tree_features"]["by_column"][col] == int((~np.isfinite(before[:, 0])).sum()) + 4
            assert rec["test_rows_with_issue_row"] == keys.size and rec["context"]["rows"] == 0
            assert rec["reading"] == LAD.PARTLY_MISSING_NOTE
    assert list((tmp_path / "temp").iterdir()) == []
    assert "issue_features_partly_missing" in LAD.READINGS["issue_missing_scope"]


# ------------------------------------------------------------------------------------------ the nowcast banks, released
def test_the_nowcast_banks_are_released_before_the_leads_run(tmp_path, monkeypatch):
    """RunState.release_bank: the inner-cut bank and the fit-cut bank leave the state (bank, store and masks),
    their stores are closed and no reference to their trees or stores survives (weak references die), a second
    release is a no-op, an unknown name refuses; Ladder.run releases both before the first lead (the run log
    orders the releases before the lead-6 lagtrain bank)."""
    import gc
    import weakref

    from treeroute.pipeline import passes as P

    with _state_after_decision(tmp_path) as (pipe, state):
        state.test_pass()
        assert state.banks_held() == [P.BANK_FIT, P.BANK_INNER]
        refs = {w: (weakref.ref(getattr(state, a[0]).trees[0]), weakref.ref(getattr(state, a[1])))
                for w, a in P.BANK_ATTRS.items()}
        fit_store = weakref.ref(state.store_fit)
        rec = state.release_bank(P.BANK_INNER, "test")
        gc.collect()
        assert rec["bank"] == P.BANK_INNER and rec["alias_of_fit_cut_bank"] is False and rec["trees"] > 0
        assert refs[P.BANK_INNER][0]() is None and refs[P.BANK_INNER][1]() is None
        assert not hasattr(state, "bank_inner") and not hasattr(state, "store_inner")
        assert state.banks_held() == [P.BANK_FIT] and fit_store() is not None and not state.store_fit._closed
        assert state.release_bank(P.BANK_INNER, "again") is None                 # a second release: no-op
        state.release_bank(P.BANK_FIT, "test")
        gc.collect()
        assert refs[P.BANK_FIT][0]() is None and refs[P.BANK_FIT][1]() is None and state.banks_held() == []
        with pytest.raises(P.PassRefusal, match="no nowcast bank named"):
            state.release_bank("guard", "test")
    assert list((tmp_path / "temp").iterdir()) == []                          # every temp file released


def test_the_ladder_releases_the_nowcast_banks_before_its_first_lead(ladder_run):
    """Ladder.run: the inner-cut bank is released before the lead-0 contract, the fit-cut bank after it and
    before the first lead's lagtrain bank (run.log order); every guard then holds two banks (lead.json)."""
    _, _, folder = ladder_run
    log = (folder / "run.log").read_text(encoding="utf-8")
    inner = log.index("released the nowcast's inner-cut bank")
    contract = log.index("lead-0 contract holds")
    fit = log.index("released the nowcast's fit-cut bank")
    lead = log.index("lead %d: lagtrain bank" % min(LEADS))
    assert inner < contract < fit < lead
    assert log.count("released the nowcast's") == 2


def test_with_the_inner_refit_off_releasing_the_inner_bank_drops_only_its_alias(tmp_path, monkeypatch):
    """A7.inner_cut_bank_refit off (L6 a): the inner names alias the fit-cut bank, so releasing BANK_INNER drops
    the alias and leaves the fit-cut bank and its open store in place."""
    from treeroute import engine_constants as K
    from treeroute.pipeline import passes as P

    monkeypatch.setattr(K, "INNER_CUT_BANK_REFIT", False)
    with _state_after_decision(tmp_path) as (pipe, state):
        assert state.bank_inner is state.bank_fit
        rec = state.release_bank(P.BANK_INNER, "test")
        assert rec["alias_of_fit_cut_bank"] is True
        assert state.banks_held() == [P.BANK_FIT] and not state.store_fit._closed
        assert not hasattr(state, "store_inner")
