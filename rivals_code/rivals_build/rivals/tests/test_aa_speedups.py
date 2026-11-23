"""Owner rulings AA (2026-10-21, the author's answer, not quoted) and AC (2026-10-21, the author's answer, not quoted
): the rival speed-ups and their corrections (SPEC_RIVALS.md 3.4a, 3.5, 2.10).

AA2  LightGBM / LightGBM-Tweedie tuning trials stop early on the inner window (patience models.PATIENCE_ROUNDS), the
     pick is the best round; test rows are never read.
AC2  (amends Y2/Z3 b and AA2) the 1600-round extension applies only to a trial that ran to the 800 cap without a
     patience stop (models.ran_to_cap); a trial stopped by patience is never extended.
AC1  (replaces AA3) tuning trials and every final fit use models.LGBM_MAX_BIN (255) bins; the 63-bin tuning is gone,
     and the tuning trial at the pick is the lead-0 guard model (its predictions equal a fresh final fit's).
AA4  the lean export takes two engine guard steps from the run's record; its exported files are byte-identical to
     the full export's and P1-P14 (P15 on the real smoke) pass. The defo smoke timing (full vs lean) is a real-data
     test (RIVALS_REAL=1) and writes evidence/aa4/defo_smoke_timing.json.

Synthetic data here is test data only (fixed generators), never a model seed.
"""

import json
import time
from pathlib import Path

import numpy as np
import pytest

from rivals.tests import toy_runs as T

GIB = 2 ** 30


def _M():
    return T.rivals_models()


def _H():
    return T.rivals_harness()


def _X():
    return T.rivals_export()


# ------------------------------------------------------------------------------------------ synthetic sets
def _smooth(seed, n):
    """A noise-free smooth target: boosting keeps improving on held-out rows for hundreds of rounds."""
    rng = np.random.default_rng(seed)                  # test data only
    X = rng.uniform(-2, 2, (n, 4)).astype(np.float32)
    y = 10 + 3 * np.sin(2 * X[:, 0]) + 2 * X[:, 1] * X[:, 2] + np.cos(3 * X[:, 3]) + 0.5 * X[:, 0] ** 2
    return X, y.astype(np.float64)


def _noisy(seed, n):
    """A noisy target: the inner MAE bottoms out early, so the trial stops by patience well inside the cap."""
    rng = np.random.default_rng(seed)                  # test data only
    X = rng.standard_normal((n, 6)).astype(np.float32)
    X[rng.random((n, 6)) < 0.1] = np.nan
    y = np.maximum(0.0, 5 + 3 * np.nan_to_num(X[:, 0]) + 2 * rng.standard_normal(n))
    return X, y


def _sets(maker, n_fit=3000, n_inner=600):
    M = _M()
    X, y = maker(1, n_fit)
    Xi, yi = maker(2, n_inner)
    cols = tuple("f%d" % i for i in range(X.shape[1]))
    fit = M.FitData("fit", X, cols, y, {"identity": np.full(y.size, 5.0)})
    inner = M.ScoreData("inner", Xi, {"identity": np.full(yi.size, 5.0)})
    return fit, inner, yi


def _metric(yi):
    from treeroute.layer.links import clip_to_legal
    from treeroute.report.metrics import mae
    return lambda pre: float(mae(yi, clip_to_legal(np.asarray(pre, dtype=np.float64), (0.0, np.inf), False)[0]))


PARAMS = {"num_leaves": 31, "min_child_samples": 20, "link": "identity", "c": None, "ub": None}


def _model_text(booster):
    """The model text without the [num_iterations: ...] parameter line (the cap, not the trees)."""
    return "\n".join(l for l in booster.model_to_string().splitlines() if not l.startswith("[num_iterations:"))


# ------------------------------------------------------------------------------------------ AA2: models
def test_aa2_early_stopping_picks_the_best_round_and_stops_after_the_patience():
    M = _M()
    fit, inner, yi = _sets(_noisy)
    metric = _metric(yi)
    es = M.EarlyStop(score_set="inner", metric=metric)
    assert es.patience == M.PATIENCE_ROUNDS == 150
    res = M.fit_predict("lgbm", PARAMS, fit, [inner], M.BASE_ROUNDS, cache={}, early_stop=es,
                        max_bin=M.LGBM_MAX_BIN)
    e = res.info["early_stopping"]
    assert e["stopped_by_patience"] and e["stopped_at"] < 800, e["stopped_at"]
    trace = e["trace"]
    assert len(trace) == e["stopped_at"] == res.info["rounds_trained"]
    best = int(np.argmin(trace)) + 1                       # argmin: the FIRST lowest value (ties -> earlier)
    assert e["best_round"] == best and e["best_metric"] == trace[best - 1]
    assert e["iterations_run"] == best + M.PATIENCE_ROUNDS  # exactly PATIENCE_ROUNDS rounds in a row without a lower MAE
    assert all(v >= trace[best - 1] for v in trace[best:])
    assert best in res["inner"] and set(res["inner"]) == {k for k in M.BASE_ROUNDS if k <= e["stopped_at"]} | {best}
    # every round's MAE is the MAE of the library's own prediction at that round (a plain fit, no early stop)
    plain = M.fit_predict("lgbm", PARAMS, fit, [inner], tuple(range(1, e["stopped_at"] + 1)), cache={},
                          max_bin=M.LGBM_MAX_BIN)
    assert [metric(plain["inner"][k]["pre"]) for k in range(1, e["stopped_at"] + 1)] == trace
    for k in res["inner"]:
        assert res["inner"][k]["pre"].tobytes() == plain["inner"][k]["pre"].tobytes(), k
    # the early-stopped model holds the same trees as the plain fit of the same length
    assert _model_text(res.model) == _model_text(plain.model)


def test_aa2_tweedie_stops_early_too():
    M = _M()
    fit, inner, yi = _sets(_noisy)
    p = dict(PARAMS, link=None, c=0.5, tweedie_variance_power=1.5)
    res = M.fit_predict("lgbm_tweedie", p, fit, [inner], M.BASE_ROUNDS, cache={},
                        early_stop=M.EarlyStop("inner", _metric(yi)), max_bin=M.LGBM_MAX_BIN)
    e = res.info["early_stopping"]
    assert e["stopped_by_patience"] and e["best_round"] in res["inner"]
    assert e["best_round"] == int(np.argmin(e["trace"])) + 1


def test_aa2_early_stopping_scores_only_the_named_set_and_refuses_misuse():
    M = _M()
    fit, inner, yi = _sets(_noisy, 800, 200)
    seen = []

    def metric(pre):
        seen.append(np.asarray(pre).shape)
        return _metric(yi)(pre)

    other = M.ScoreData("other", inner.X[:50], {"identity": inner.normal["identity"][:50]})
    M.fit_predict("lgbm", PARAMS, fit, [inner, other], (100,), cache={}, early_stop=M.EarlyStop("inner", metric))
    assert seen and set(seen) == {(yi.size,)}               # only the inner rows are ever scored
    with pytest.raises(M.ModelRefusal):                     # a set the fit does not hold
        M.fit_predict("lgbm", PARAMS, fit, [inner], (100,), cache={}, early_stop=M.EarlyStop("test", metric))
    with pytest.raises(M.ModelRefusal):                     # early stopping is for the LightGBM learners only
        M.fit_predict("hgb_l1", {"max_leaf_nodes": 31, "min_samples_leaf": 20, "link": "identity"}, fit, [inner],
                      (100,), early_stop=M.EarlyStop("inner", metric))
    with pytest.raises(M.ModelRefusal):
        M.fit_predict("ridge", {"link": "identity"}, fit, [inner], (1.0,), max_bin=63)


def test_aa2_the_extension_still_triggers_and_reproduces_its_base_trial():
    """A noise-free target keeps improving: the base trial runs to the 800 cap without a patience stop (AC2), its
    best round lies in (400, 800], so the trial is extended; the extended refit (cap 1600) reproduces every kept
    round of the base trial byte for byte and its per-round inner MAE, and goes on past 800."""
    M = _M()
    fit, inner, yi = _sets(_smooth, 2500, 600)
    metric = _metric(yi)
    base = M.fit_predict("lgbm", PARAMS, fit, [inner], M.checkpoints("lgbm"), cache={},
                         early_stop=M.EarlyStop("inner", metric), max_bin=M.LGBM_MAX_BIN)
    eb = base.info["early_stopping"]
    assert M.in_last_stage(eb["best_round"]), eb["best_round"]
    assert not eb["stopped_by_patience"] and eb["iterations_run"] == 800 and M.ran_to_cap(eb)
    rows = [{"trial_id": "t", "link_order": 0, "grid_order": 0, "checkpoint": k, "inner_mae": metric(v["pre"])}
            for k, v in base["inner"].items()]
    assert _H().trials_to_extend(rows) == ["t"]
    assert _H().trials_to_extend(rows, ran_to_cap={"t": M.ran_to_cap(eb)}) == ["t"]
    ext = M.fit_predict("lgbm", PARAMS, fit, [inner], M.checkpoints("lgbm", extended=True), cache={},
                        early_stop=M.EarlyStop("inner", metric, also_save=tuple(base["inner"])),
                        max_bin=M.LGBM_MAX_BIN)
    ee = ext.info["early_stopping"]
    assert ee["cap_rounds"] == 1600 and ee["iterations_run"] > 800
    assert ee["trace"][:len(eb["trace"])] == eb["trace"]
    _H().check_extension_prefix({k: v["pre"] for k, v in base["inner"].items()},
                                {k: v["pre"] for k, v in ext["inner"].items()}, "t")


def test_aa2_rules_on_early_stopped_rows():
    H = _H()

    def rows(best_of):
        out = []
        for gi, (tid, kept) in enumerate(best_of.items()):
            for ck, mae in kept.items():
                out.append({"trial_id": tid, "link_order": 0, "grid_order": gi, "checkpoint": ck, "inner_mae": mae})
        return out

    r = rows({"a": {100: 3.0, 200: 2.5, 400: 2.2, 437: 2.0},       # best 437: in (400, 800] -> extended
              "b": {100: 3.0, 200: 2.5, 400: 2.1},                 # best exactly 400 -> not extended
              "c": {52: 2.4, 100: 2.6},                            # best 52 -> not extended
              "d": {100: 3.0, 200: 2.9, 400: 2.8, 800: 2.7}})      # best 800 (cap reached) -> extended
    assert H.trials_to_extend(r) == ["a", "d"]                       # staged reading (no cap records)
    # AC2: with the early-stopping records, a trial stopped by patience is never extended, whatever its best round
    assert H.trials_to_extend(r, ran_to_cap={"a": False, "b": False, "c": False, "d": True}) == ["d"]
    assert H.trials_to_extend(r, ran_to_cap={"a": False, "b": False, "c": False, "d": False}) == []
    with pytest.raises(Exception):                                   # a trial without a cap record refuses
        H.trials_to_extend(r, ran_to_cap={"a": False, "b": False, "d": True})
    # the lower edge of an early-stopped booster is round 1; round 52 is an interior best (AA review item 4)
    assert H.pick_flags("lgbm", {"checkpoint": 52}) == []
    assert H.pick_flags("lgbm_tweedie", {"checkpoint": 1}) == ["edge_round_1"]
    assert "edge_rounds_100" not in H.pick_flags("lgbm", {"checkpoint": 100})
    assert "edge_rounds_100" in H.pick_flags("hgb_l1", {"checkpoint": 100})
    assert "edge_rounds_100" not in H.pick_flags("hgb_l1", {"checkpoint": 200})
    assert "edge_rounds_1600" in H.pick_flags("lgbm", {"checkpoint": 1250})
    assert "edge_rounds_1600" not in H.pick_flags("lgbm", {"checkpoint": 1200})


# ------------------------------------------------------------------------------------------ AC2: models
def test_ac2_ran_to_cap_reads_the_early_stopping_record_and_fails_loud():
    M = _M()
    assert M.ran_to_cap({"stopped_by_patience": True, "iterations_run": 500, "cap_rounds": 800}) is False
    assert M.ran_to_cap({"stopped_by_patience": True, "iterations_run": 800, "cap_rounds": 800}) is False
    assert M.ran_to_cap({"stopped_by_patience": False, "iterations_run": 800, "cap_rounds": 800}) is True
    with pytest.raises(M.ModelRefusal):                     # not stopped, yet short of the cap: contradictory
        M.ran_to_cap({"stopped_by_patience": False, "iterations_run": 700, "cap_rounds": 800})
    with pytest.raises(M.ModelRefusal):                     # a missing field
        M.ran_to_cap({"stopped_by_patience": False, "cap_rounds": 800})
    with pytest.raises(M.ModelRefusal):                     # no record at all
        M.ran_to_cap(None)
    # on a real early-stopped fit: a noisy target stops by patience -> not extended
    fit, inner, yi = _sets(_noisy)
    e = M.fit_predict("lgbm", PARAMS, fit, [inner], M.BASE_ROUNDS, cache={}, max_bin=M.LGBM_MAX_BIN,
                      early_stop=M.EarlyStop("inner", _metric(yi))).info["early_stopping"]
    assert e["stopped_by_patience"] and M.ran_to_cap(e) is False
    assert "patience stop" in M.tuning_options("lgbm")["extension"]


# ------------------------------------------------------------------------------------------ AC1: models
def test_ac1_tuning_and_final_fits_both_use_255_bins():
    M = _M()
    assert M.LGBM_MAX_BIN == 255
    assert not hasattr(M, "TUNE_MAX_BIN") and not hasattr(M, "REFIT_MAX_BIN")      # the 63-bin path is gone
    assert M.tuning_options("lgbm")["max_bin"] == 255 and M.tuning_options("lgbm_tweedie")["max_bin"] == 255
    assert M.final_fit_options("lgbm") == {"max_bin": 255, "rounds": "the picked round count", "early_stopping": None}
    fit, inner, yi = _sets(_noisy)
    cache = {}
    tuned = M.fit_predict("lgbm", PARAMS, fit, [inner], (100,), cache=cache, max_bin=M.LGBM_MAX_BIN,
                          early_stop=M.EarlyStop("inner", _metric(yi)))
    ds = [v for k, v in cache.items() if k[0] == "lgbm_dataset"]
    assert len(ds) == 1 and max(ds[0].feature_num_bin(i) for i in range(ds[0].num_feature())) > 63
    assert tuned.info["max_bin"] == 255 and tuned.info["train_params"]["max_bin"] == 255
    assert "[max_bin: 255]" in tuned.model.model_to_string()
    cache = {}
    final = M.fit_predict("lgbm", PARAMS, fit, [inner], (100,), cache=cache)        # the default: final fits
    ds = [v for k, v in cache.items() if k[0] == "lgbm_dataset"]
    assert max(ds[0].feature_num_bin(i) for i in range(ds[0].num_feature())) > 63
    assert final.info["max_bin"] == 255 and "[max_bin: 255]" in final.model.model_to_string()


@pytest.mark.parametrize("learner", ["lgbm", "lgbm_tweedie"])
def test_ac1_the_tuning_trial_at_its_best_round_is_the_final_fit_at_that_round(learner):
    """The lead-0 guard reuses the tuning trial's inner predictions at the pick (harness refit, lead 0). That is
    sound only if a fresh final fit (255 bins, the picked round count, no early stopping) on the same rows gives the
    same predictions and the same trees: checked byte for byte at the trial's best round."""
    M = _M()
    fit, inner, yi = _sets(_noisy)
    p = PARAMS if learner == "lgbm" else dict(PARAMS, link=None, c=0.5, tweedie_variance_power=1.5)
    tuned = M.fit_predict(learner, p, fit, [inner], M.BASE_ROUNDS, cache={}, max_bin=M.LGBM_MAX_BIN,
                          early_stop=M.EarlyStop("inner", _metric(yi)))
    best = tuned.info["early_stopping"]["best_round"]
    final = M.fit_predict(learner, p, fit, [inner], (best,), cache={}, max_bin=M.LGBM_MAX_BIN)
    assert final.info["rounds_trained"] == best
    assert tuned["inner"][best]["pre"].tobytes() == final["inner"][best]["pre"].tobytes()

    def trees(booster):                                     # the tree records of the first `best` rounds
        return booster.model_to_string(num_iteration=best).split("Tree=0", 1)[1].split("end of trees", 1)[0]

    assert trees(tuned.model) == trees(final.model)


# ------------------------------------------------------------------------------------------ AA2/AA3: the harness
@pytest.fixture(scope="module")
def aa_tune(table_toy, table_export):
    """A fresh init / tune / lock on the table toy's export with (1) the read spy, (2) a recorder of every fit's
    score sets and early-stop set, and (3) the extension rule forced for every base trial (the last-stage test AND
    the AC2 ran-to-cap test), so the harness's extension path (also_save, prefix and trace checks) runs on
    early-stopped trials. The unforced AC2 path is tested on flow A (test_ac2_...)."""
    M = _M()
    calls = []
    orig_fit = M.fit_predict
    orig_stage = M.in_last_stage

    def recorder(learner, params, fit_set, score_sets, cks, **kw):
        es = kw.get("early_stop")
        calls.append({"learner": learner, "fit": getattr(fit_set, "name", None),
                      "scores": [getattr(s, "name", None) for s in score_sets],
                      "early_stop": None if es is None else es.score_set, "max_bin": kw.get("max_bin")})
        return orig_fit(learner, params, fit_set, score_sets, cks, **kw)

    out_root = table_toy.base / "_out_aa"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(M, "fit_predict", recorder)
        mp.setattr(M, "in_last_stage", lambda ck, extended=False: True if not extended else orig_stage(ck, True))
        mp.setattr(M, "ran_to_cap", lambda e: True)
        with T.ReadSpy() as spy:
            out = T.h_init(table_toy, table_export.dirs[0], out_root, ("hgb_l1",))
            T.h_tune(table_toy, out)
            T.h_lock(table_toy, out)
    return {"out": out, "calls": calls, "spy": spy}


def test_aa2_tuning_scores_the_inner_rows_only_and_never_reads_a_test_row(aa_tune, table_toy):
    M = _M()
    calls, spy = aa_tune["calls"], aa_tune["spy"]
    lg = [c for c in calls if c["learner"] in ("lgbm", "lgbm_tweedie")]
    assert lg and all(str(c["fit"]).endswith("_tune") and c["scores"] == ["inner"] and c["early_stop"] == "inner"
                      and c["max_bin"] == M.LGBM_MAX_BIN == 255 for c in lg), lg
    assert all(c["scores"] == ["inner"] for c in calls)
    assert spy.test_label_opens == [] and spy.test_y_requests() == []
    assert spy.test_file_reads(table_toy.export_root, decoded_only=False) == []


def test_aa2_trials_record_the_patience_the_best_round_and_the_trace(aa_tune):
    out = Path(aa_tune["out"])
    board = T.read_json(out / "board.json")
    lg = {b["id"]: b for b in board["learners"]}
    assert lg["lgbm"]["fixed"]["tuning"]["patience_rounds"] == 150
    assert lg["lgbm"]["fixed"]["tuning"]["max_bin"] == 255 and lg["lgbm"]["fixed"]["final_fit"]["max_bin"] == 255
    assert "AC1" in board["rules"]["bins"] and "AC2" in board["rules"]["extension"]
    assert "early_stopping" in board["rules"] and "bins" in board["rules"]
    n = 0
    for tj in sorted((out / "trials").glob("lgbm*/*/trial.json")):
        rec = T.read_json(tj)
        e = rec["early_stopping"]
        assert e["patience_rounds"] == 150 and rec["tuning"]["max_bin"] == 255
        assert rec["fit_info"]["max_bin"] == 255
        assert len(e["trace"]) == e["stopped_at"]
        assert rec["best_checkpoint"] == str(e["best_round"]) == str(int(np.argmin(e["trace"])) + 1)
        assert rec["ck_mae"][str(e["best_round"])] == e["trace"][e["best_round"] - 1]
        n += 1
    assert n >= 12


def test_aa2_the_harness_extension_path_runs_on_early_stopped_trials(aa_tune):
    out = Path(aa_tune["out"])
    for learner in ("lgbm", "lgbm_tweedie"):
        exts = sorted((out / "trials" / learner).glob("*__ext/trial.json"))
        bases = [p for p in (out / "trials" / learner).glob("*/trial.json") if not p.parent.name.endswith("__ext")]
        assert exts and len(exts) == len(bases), (learner, len(exts), len(bases))
        for p in exts:
            rec = T.read_json(p)
            base = T.read_json(p.parent.parent / p.parent.name[:-len("__ext")] / "trial.json")
            assert rec["extended"] and rec["early_stopping"]["cap_rounds"] == 1600
            assert set(base["checkpoints"]) <= set(rec["checkpoints"])
            assert rec["early_stopping"]["trace"][:len(base["early_stopping"]["trace"])] == \
                base["early_stopping"]["trace"]
    picks = T.read_json(out / "picks.json")["picks"]
    assert picks["lgbm"]["extension_trials"]                    # the lock saw the extensions


def test_ac2_patience_stopped_trials_are_not_extended_on_flow_a(table_flow):
    """Flow A, the rule NOT forced: every lgbm / lgbm_tweedie base trial that stopped by patience has no extended
    trial; a trial is extended exactly when it ran to the 800 cap without a patience stop; picks.json's
    extension_trials lists exactly those."""
    M = _M()
    out = Path(table_flow.out)
    picks = T.read_json(out / "picks.json")["picks"]
    for learner in ("lgbm", "lgbm_tweedie"):
        tdir = out / "trials" / learner
        bases = {p.parent.name: T.read_json(p) for p in tdir.glob("*/trial.json")
                 if not p.parent.name.endswith("__ext")}
        exts = {p.parent.name[:-len("__ext")] for p in tdir.glob("*__ext/trial.json")}
        assert bases
        should = {tid for tid, rec in bases.items() if M.ran_to_cap(rec["early_stopping"])}
        assert exts == should, (learner, sorted(exts), sorted(should))
        assert set(picks[learner]["extension_trials"]) == should
        for tid, rec in bases.items():
            if rec["early_stopping"]["stopped_by_patience"]:
                assert tid not in exts


def test_ac1_refit_and_guard_fits_use_255_bins_and_the_lead0_guard_is_the_tuning_trial(table_flow):
    out = Path(table_flow.out)
    for tj in sorted((out / "trials").glob("lgbm*/*/trial.json")):
        assert T.read_json(tj)["fit_info"]["train_params"]["max_bin"] == 255, tj
    picks = T.read_json(out / "picks.json")["picks"]
    for L in table_flow.scored_leads:
        for learner in ("lgbm", "lgbm_tweedie"):
            done = T.read_json(out / ("lead_%d" % L) / ("done_%s.json" % learner))
            assert done["fit_info"]["max_bin"] == 255 and done["fit_info"]["train_params"]["max_bin"] == 255
            assert done["final_fit"]["max_bin"] == 255
            if L == 0:
                # AC1: the tuning trial at the pick is the final model on the tune rows -> the same inner MAE as
                # picks.json records (no second 255-bin fit, no second number)
                assert done["guard"]["source"] == "the tuning trial's inner predictions at the pick"
                assert done["guard"]["rival_mae"] == picks[learner]["inner_mae"]
                assert picks[learner]["inner_mae_and_n2_are_of"] == \
                    "the tuning model, which is the reported model's lead-0 guard model"
            else:
                assert "final-fit options" in done["guard"]["source"], done["guard"]["source"]
            text = (out / ("lead_%d" % L) / ("model_%s.txt" % learner)).read_text(encoding="utf-8")
            assert "[max_bin: 255]" in text
            assert int(done["pinned"]) == int(done["pick"]["checkpoint"])
        done = T.read_json(out / ("lead_%d" % L) / "done_ridge.json")
        assert done["final_fit"] is None


# ------------------------------------------------------------------------------------------ AA4: the lean export
def _second_config(toy, tag):
    base = toy.base / ("_aa4_" + tag)
    cfg = T.write_rivals_yaml(base / "rivals.yaml", toy.machine_file, base / "_export", base / "_export" /
                              "_engine_run_root", base / "_out", base / "_moved")
    return cfg, base / "_export"


def _export(toy, cfg, lean, p15=None):
    X = _X()
    t0 = time.time()
    dirs = X.export_run(toy.run, toy.package, ",".join(str(L) for L in toy.leads), None, cfg, lean=lean, p15=p15)
    return [Path(d) for d in dirs], time.time() - t0


def _exported_files(d):
    man = T.read_json(Path(d) / "export_manifest.json")
    files = sorted((f["path"], f["sha256"], int(f["rows"])) for f in man["files"])
    for path, sha, _ in files:                                  # the listed bytes are the bytes on disk
        assert T.sha256_file(Path(d) / path) == sha, path
    return man, files


def _compare(full_dirs, lean_dirs, p_ids):
    H = _H()
    assert [d.name for d in full_dirs] == [d.name for d in lean_dirs]
    out = []
    for fd, ld in zip(full_dirs, lean_dirs):
        fm, ff = _exported_files(fd)
        lm, lf = _exported_files(ld)
        assert ff == lf, "lead %s: the lean export's files differ from the full export's" % fd.name
        assert H.export_content_sha(fm) == H.export_content_sha(lm)
        for k in ("columns", "counts", "row_key_hashes", "cuts", "c", "derived_sha256", "records"):
            assert fm[k] == lm[k], (fd.name, k)
        for man in (fm, lm):
            st = {k: str(v.get("result")) for k, v in man["parity"].items()}
            for cid in p_ids:
                assert st[cid].lower().startswith(("pass", "printed")), (fd.name, cid, st[cid])
        assert fm["lean_export"]["on"] is False and lm["lean_export"]["on"] is True
        out.append((fm, lm, len(ff)))
    return out


def test_aa4_lean_export_is_byte_identical_on_the_grid_toy(grid_toy):
    """The grid toy runs the per-group path (its separability check runs in a full export); every census row is a
    picked row, so R30's test-year count is not needed there (the count skip is tested below on the engine class)."""
    cfg_f, _ = _second_config(grid_toy, "full")
    cfg_l, _ = _second_config(grid_toy, "lean")
    full_dirs, _ = _export(grid_toy, cfg_f, lean=False)
    with T.ReadSpy() as spy:
        lean_dirs, _ = _export(grid_toy, cfg_l, lean=True)
    assert spy.test_label_opens == [] and spy.test_y_requests() == []
    res = _compare(full_dirs, lean_dirs, T.CHECK_IDS_P)
    fm, lm, n = res[0]
    assert n > 0
    assert lm["lean_export"]["separability_check"]["skipped"] >= 1
    assert lm["lean_export"]["r30_test_year_count"]["skipped"] == 0
    assert lm["lean_export"]["r30_test_year_count"]["not_needed"] >= 1


def test_aa4_the_r30_count_is_taken_from_the_run_only_when_it_would_run(tmp_path):
    """LeanEngine on the engine's own StreamedShareReader.measure (stood in by a recorder): when not every census
    row is picked, the run's shares are put in the reader's count cache in the engine's order before the engine's
    measure runs (so its count never starts); when every census row is picked nothing is put there; the class and
    the module are restored on exit."""
    from types import SimpleNamespace as NS

    from treeroute.pipeline import stream as STR

    X = _X()
    run = tmp_path / "run"
    run.mkdir()
    shares = {"b": {"2021": 0.5, "2020": 0.25}, "a": {"2020": 0.0, "2021": 1.0}}
    (run / "derived.json").write_text(json.dumps({"R30": {"inputs": {"test_year_missing_share": shares}}}),
                                      encoding="utf-8")
    (run / "per_group_plan.json").write_text(json.dumps({"separability": {"checked": True,
                                                                          "result": "group-separable on the sample"}}),
                                             encoding="utf-8")
    seen = []

    def engine_measure(self_, donor, lags, test_years):
        key = (STR._lag_key(lags), tuple(int(y) for y in test_years))
        seen.append(dict(self_._test_year_cache.get(key, {})))
        return "shares"

    orig_measure, orig_sep = STR.StreamedShareReader.measure, STR.check_group_separable
    lines = []
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(STR.StreamedShareReader, "measure", engine_measure)
        with X.LeanEngine(run, lines.append) as le:
            spec = NS(tree_features=("a", "b"))
            part = NS(spec=spec, _test_year_cache={},
                      census=NS(rows=10, _picked=(("u1",), NS(unit_ids=np.array(["u1"] * 4, dtype=object)))))
            assert STR.StreamedShareReader.measure(part, None, {}, [2020, 2021]) == "shares"
            whole = NS(spec=spec, _test_year_cache={},
                       census=NS(rows=4, _picked=(("u1",), NS(unit_ids=np.array(["u1"] * 4, dtype=object)))))
            STR.StreamedShareReader.measure(whole, None, {}, [2020, 2021])
            rec = STR.check_group_separable("anything")
        assert STR.StreamedShareReader.measure is engine_measure
    assert STR.StreamedShareReader.measure is orig_measure and STR.check_group_separable is orig_sep
    assert list(seen[0].items()) == [(("a", 2020), 0.0), (("a", 2021), 1.0), (("b", 2020), 0.25), (("b", 2021), 0.5)]
    assert seen[1] == {}
    assert le.rec["r30_test_year_count"] == {"skipped": 1, "not_needed": 1, "run_record": True}
    assert rec["result"] == "group-separable on the sample" and le.rec["separability_check"]["skipped"] == 1
    assert any("LEAN" in x for x in lines)


def test_aa4_cli_has_the_full_engine_checks_switch():
    import inspect
    X = _X()
    assert "lean" in inspect.signature(X.export_run).parameters
    assert inspect.signature(X.export_run).parameters["lean"].default is True
    assert "--full-engine-checks" in inspect.getsource(X.main)


# ------------------------------------------------------------------------------------------ AA4 on the defo smoke
@pytest.mark.realdata
def test_aa4_defo_smoke_lean_equals_full_and_its_time(tmp_path_factory):
    """The defo smoke run (region kind, 4 groups x 40 units, leads 0 and 1): full and lean exports into fresh roots
    (no engine checkpoint carried over), twice each in the order full, lean, full, lean; P15 on. Files byte-equal,
    P1-P15 pass, and the times go to evidence/aa4/defo_smoke_timing.json."""
    import psutil

    from rivals.tests.test_realdata import DEFO_SMOKE, SMOKE_CFG, _no_real_heavy_job, _real

    _no_real_heavy_job()
    if psutil.virtual_memory().available <= 3 * GIB:
        pytest.skip("available RAM %.1f GiB <= 3 GiB" % (psutil.virtual_memory().available / GIB))
    base = tmp_path_factory.mktemp("aa4_defo")
    toy = _real(DEFO_SMOKE, "defo", SMOKE_CFG, base / "_out")
    toy.base = base
    times = {"full": [], "lean": []}
    dirs = {}
    manifests = {}
    for i, mode in enumerate(("full", "lean", "full", "lean")):
        cfg, _ = _second_config(toy, "%s%d" % (mode, i))
        text = Path(cfg).read_text(encoding="utf-8") + "engine_lineage: '%s'\n" % (T.BUILD_ROOT / "engine_lineage.json"
                                                                                  ).as_posix()
        Path(cfg).write_text(text, encoding="utf-8")
        with T.ReadSpy() as spy:
            d, sec = _export(toy, cfg, lean=(mode == "lean"), p15=True)
        assert spy.test_label_opens == [] and spy.test_y_requests() == []
        times[mode].append(sec)
        dirs.setdefault(mode, d)
        manifests["%s%d" % (mode, i)] = {x.name: T.read_json(x / "export_manifest.json")["timings_seconds"] for x in d}
    res = _compare(dirs["full"], dirs["lean"], tuple("P%d" % i for i in range(1, 16)))
    lean_rec = res[0][1]["lean_export"]
    ev = T.BUILD_ROOT / "evidence" / "aa4"
    ev.mkdir(parents=True, exist_ok=True)
    doc = {"run": str(DEFO_SMOKE), "order": ["full", "lean", "full", "lean"], "wall_seconds": times,
           "manifest_timings_seconds": manifests, "lean_record": lean_rec,
           "files_per_lead": {fm["lead"]: n for fm, _, n in res},
           "byte_identical": True, "parity": "P1-P15 pass in every export (p15 on)",
           "full_mean_seconds": sum(times["full"]) / 2.0, "lean_mean_seconds": sum(times["lean"]) / 2.0,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    text = json.dumps(doc, indent=1, sort_keys=True)
    (ev / "defo_smoke_timing.json").write_text(text, encoding="utf-8")          # the latest run
    # every run also keeps its own time-stamped copy, so a later run never overwrites cited evidence
    (ev / ("defo_smoke_timing_%s.json" % doc["utc"].replace(":", "").replace("-", ""))).write_text(
        text, encoding="utf-8")
    print("AA4 defo smoke: full %s s, lean %s s" % (times["full"], times["lean"]))
    assert lean_rec["separability_check"]["skipped"] >= 1
    # the check of AA4: the lean export saves time on this run (both repeats)
    assert max(times["lean"]) < min(times["full"]), times
