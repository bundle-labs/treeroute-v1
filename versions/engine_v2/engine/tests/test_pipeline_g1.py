"""Owner ruling G1 (OWNER_RULINGS_2026-09-28.md section G, 2026-10-05): at each lead, a router FIT row whose
context (read at the lead's issue step) is missing or non-finite leaves that lead's router fit, exactly as a row
with a missing label does (R30); the count is printed per unit and lead and flagged above 5% of a unit's fit
rows; nothing is filled; a SCORED row with missing context still refuses; route.kinds' R20 refusal stays as
the last guard.

The synthetic package of tests/test_pipeline.py gets a second router-context column, ctx:e (the calendar month
again), which is missing in the first two months of the pre-Y0 year YEARS[0]. Y0 is YEARS[1], so only at lead
12 do fit rows read their context there: the first two Y0 months of every unit lose it. At leads 0 and 6 (the
leads are 6 and 12, owner ruling I1) every context value is present, so those leads must be byte for byte what
they were before G1 (the same package
run with the G1 filter switched off, which refuses at lead 12 exactly as the NDVI smoke did). That switched-off
run is the current engine with drop_missing_context made a no-op, not the engine as it stood before G1; the
true before/after proof is the NDVI draft smoke compared file by file with its run from before G1
(SMOKES_REPORT.md section 5).

Every run writes only under the test's temp folder (the fake machine file's run root and temp dir).
"""

import hashlib
import json
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from test_pipeline import (FEATURES, LEADS, YEARS, _run, make_pipeline_package,  # noqa: F401
                           sklearnex_patched)
from test_pipeline_ladder import _state_after_decision

G1_COLUMN = "ctx:e"
LOST_YEAR = YEARS[0]          # the pre-Y0 lag year: the issue year of Y0's rows at lead 12
LOST_MONTHS = (1, 2)
Y0 = YEARS[1]
EARLY_LEADS = tuple(L for L in LEADS if L < 12)

FEATURES_G1 = FEATURES.replace(
    '''              "fact_status": "verified"},
}''',
    '''              "fact_status": "verified"},
    "ctx:e": {"dtype": "float32", "units": "1",
              "cadence": {"kind": "regular", "length": 1, "unit": "month"},
              "scope": "global", "stamp": "period_end",
              "window": {"length": 1, "unit": "month", "align": "backward"},
              "legal_range": [1.0, 12.0], "derived_from": ["step_year", "step_month"], "reads_target": False,
              "fact_status": "verified"},
}''').replace(
    '''    return pd.DataFrame({"ctx:m": frame[month].astype("float32")}, index=frame.index)''',
    '''    year = [c for c, part in keys["time"].items() if part == "year"][0]
    m = frame[month].astype("float32")
    lost = (frame[year] == %d) & (frame[month] <= %d)
    return pd.DataFrame({"ctx:m": m, "ctx:e": m.where(~lost)}, index=frame.index)''' % (LOST_YEAR, max(LOST_MONTHS)))


def make_g1_package(root, name="synth_g1"):
    """The synthetic package with the second context column ctx:e (module docstring)."""
    assert FEATURES_G1.count('"ctx:e"') == 2 and "m.where(~lost)" in FEATURES_G1
    pkg = make_pipeline_package(root, name=name)
    (pkg / "features" / "build.py").write_text(FEATURES_G1, encoding="utf-8")
    cat = pkg / "catalog.yaml"
    text = cat.read_text(encoding="utf-8")
    assert text.count("  'ctx:m': {role: router_context}\n") == 1
    cat.write_text(text + "  '%s': {role: router_context}\n" % G1_COLUMN, encoding="utf-8")
    ban = pkg / "ban.yaml"
    ban.write_text(ban.read_text(encoding="utf-8")
                   + "  '%s': {verdict: keep, reason: reviewed, evidence: 'Part 1'}\n" % G1_COLUMN, encoding="utf-8")
    return pkg


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _step(year, month):
    """A monthly step id (the engine's month count; checked against derived.json's lead-0 fit cut below)."""
    return int(year) * 12 + int(month)


def _labels_lost(pkg):
    """{unit: valid labels in the lost Y0 months}: the fit rows G1 must leave out at lead 12 (every unit is
    scored at smoke size; a row without a label is no fit row in the first place, R30)."""
    frames = [pd.read_parquet(p) for p in sorted((pkg / "data" / "target").glob("group=*/year=%d/part-0.parquet" % Y0))]
    t = pd.concat(frames, ignore_index=True)
    t = t[t["step_month"].isin(LOST_MONTHS) & t["y"].notna()]
    return {str(u): int(n) for u, n in t.groupby("unit_id").size().items()}


# ------------------------------------------------------------------------------------------ the filter itself
def _fit_rows(units, times, context):
    return SimpleNamespace(cut=999, cut_kind="fit", lead=12, unit_ids=np.asarray(units, dtype=object),
                           times=np.asarray(times, dtype=np.int64),
                           row_positions=np.arange(len(units), dtype=np.int64) * 7 + 3,
                           y=np.linspace(0.1, 0.9, len(units)), context=np.asarray(context, dtype=np.float32))


def test_g1_leaves_out_fit_rows_without_context_counts_them_and_fills_nothing():
    """Unit a loses 1 of 20 rows (5.0%: not flagged, the flag is ABOVE 5%), unit b 2 of 20 (10%: flagged, one
    NaN and one infinite value), unit c none of 10. The kept rows are the others, in order, with the same
    bytes; the raw rows still refuse in route.kinds (R20, the last guard), the kept rows pass."""
    from treeroute.pipeline import stages as ST
    from treeroute.route import kinds as RK

    units = ["a"] * 20 + ["b"] * 20 + ["c"] * 10
    times = list(range(100, 120)) * 2 + list(range(100, 110))
    ctx = np.column_stack([np.arange(50, dtype=np.float32) + 1, np.ones(50, dtype=np.float32)])
    ctx[0, 0] = np.nan                       # a, step 100
    ctx[20, 1] = np.nan                      # b, step 100
    ctx[21, 0] = np.inf                      # b, step 101
    fit = _fit_rows(units, times, ctx)
    out, rec, left = ST.drop_missing_context(fit, ("c1", "c2"))
    keep = np.setdiff1d(np.arange(50), [0, 20, 21])
    assert isinstance(out, ST.ContextKeptRows) and out.cut == 999 and out.lead == 12
    assert np.array_equal(out.unit_ids, fit.unit_ids[keep]) and np.array_equal(out.times, fit.times[keep])
    assert np.array_equal(out.row_positions, fit.row_positions[keep]) and np.array_equal(out.y, fit.y[keep])
    assert out.context.dtype == np.float32 and out.context.tobytes() == fit.context[keep].tobytes()   # nothing filled
    assert np.isfinite(out.context).all()
    assert rec["rows_left_out"] == 3 and rec["fit_rows"] == 50 and rec["units_in_fit"] == 3
    assert rec["by_unit"] == {"a": {"left_out": 1, "fit_rows": 20, "share": 0.05, "flagged": False},
                              "b": {"left_out": 2, "fit_rows": 20, "share": 0.1, "flagged": True}}
    from treeroute import engine_constants as K

    assert rec["flagged_units"] == ["b"] and rec["flag_share"] == K.CONTEXT_MISSING_FLAG_SHARE == 0.05
    assert rec["flag_share_constant"] == "C10.context_missing_flag_share"
    assert rec["by_column"] == {"c1": 2, "c2": 1} and rec["by_step"] == {"100": 2, "101": 1}
    assert rec["units_with_rows_left_out"] == 2 and rec["context_columns"] == 2
    # every row left out is listed: unit, step, grid position and which context columns were missing
    assert isinstance(left, ST.ContextMissingRows) and left.columns == ("c1", "c2")
    assert left.unit_ids.tolist() == ["a", "b", "b"] and left.times.tolist() == [100, 100, 101]
    assert np.array_equal(left.row_positions, fit.row_positions[[0, 20, 21]])
    assert left.missing.tolist() == [[True, False], [False, True], [True, False]]
    frame = left.frame("lead 12 guard", "router_lead_guard")
    assert list(frame.columns) == ["pass", "purpose", "lead", "cut_kind", "cut", "unit", "time", "issue",
                                   "row_position", "missing__c1", "missing__c2"]
    assert frame["issue"].tolist() == [88, 88, 89] and (frame["lead"] == 12).all() and (frame["cut"] == 999).all()
    assert frame["missing__c1"].tolist() == [True, False, True] and frame["pass"].unique().tolist() == ["lead 12 guard"]
    with pytest.raises(RK.RouteRefusal, match=r"\[R20\] the context on fit rows holds 3 missing or infinite"):
        RK.router_standardisation(fit, fit.context)
    mean, sd = RK.router_standardisation(out, out.context)
    assert np.isfinite(mean).all() and np.isfinite(sd).all()


def test_g1_hands_back_the_same_rows_when_every_context_is_present():
    from treeroute.pipeline import stages as ST

    fit = _fit_rows(["a"] * 5 + ["b"] * 5, list(range(10)), np.ones((10, 2)))
    out, rec, left = ST.drop_missing_context(fit, ("c1", "c2"))
    assert out is fit and left is None                 # the pass is byte for byte what it was before G1
    assert rec["rows_left_out"] == 0 and rec["by_unit"] == {} and rec["flagged_units"] == []
    assert rec["by_column"] == {} and rec["by_step"] == {} and rec["units_in_fit"] == 2


def test_g1_refuses_a_pass_whose_every_fit_row_lost_its_context_and_any_scored_row_without_context():
    from treeroute.pipeline import stages as ST

    ctx = np.ones((4, 2))
    ctx[:, 1] = np.nan
    with pytest.raises(ST.StageRefusal, match=r"\[G1\] every one of the 4 router fit rows"):
        ST.drop_missing_context(_fit_rows(["a", "a", "b", "b"], [1, 2, 1, 2], ctx), ("c1", "c2"))
    score = np.ones((3, 2))
    ST.check_score_context(score, np.array(["a", "b", "b"], dtype=object), np.array([5, 5, 6]), ("c1", "c2"), "p")
    score[2, 0] = np.nan
    with pytest.raises(ST.StageRefusal, match=r"\[G1\] p: 1 scored row\(s\) of 1 unit\(s\).*\['c1'\].*b@6"):
        ST.check_score_context(score, np.array(["a", "b", "b"], dtype=object), np.array([5, 5, 6]), ("c1", "c2"),
                               "p")


# ------------------------------------------------------------------------------------------ one lead, pass by pass
def test_at_a_lead_whose_issue_steps_lack_context_the_fit_rows_leave_and_scored_rows_refuse(tmp_path):
    """On the G1 package at lead 12: the per-unit pass's fit rows are FitContext's router rows less exactly the
    rows whose moved context is missing (every scored unit's labelled rows in the first two Y0 months), with
    the same bytes otherwise; the raw rows still refuse in route.kinds (R20); a pass that SCORES rows without
    context refuses (G1) before any kernel; at lead 6 no row is left out and the rows are FitContext's own."""
    from treeroute.fit.context import RouterRows
    from treeroute.labels.vault import row_key_hash
    from treeroute.layer import decide as LD
    from treeroute.pipeline import router as PR
    from treeroute.pipeline import stages as ST
    from treeroute.pipeline.ladder import Ladder
    from treeroute.route import kinds as RK

    pkg = make_g1_package(tmp_path / "pk")
    with _state_after_decision(tmp_path, pkg) as (pipe, state):
        assert tuple(state.pool.context_columns) == ("ctx:m", G1_COLUMN)
        lad = Ladder(state)
        t_keys, t_units, t_steps = lad._test_rows()
        first = int(state.vg.first_step)
        assert first == _step(Y0, 1)
        with ExitStack() as stack:
            o = lad._objects(12, stack)
            raw = o.ctx_fit.router_rows(tuple(state.scored_units), "g1_test")
            bad = ~np.isfinite(np.asarray(raw.context, dtype=np.float64)).all(axis=1)
            assert bad.any()
            assert set(np.asarray(raw.times)[bad].tolist()) == {first, first + 1}            # the first two Y0 months
            assert np.isfinite(np.asarray(raw.context)[:, 0]).all()                         # ctx:m never lost
            lost = _labels_lost(pkg)
            got = pd.Series(np.asarray(raw.unit_ids, dtype=object)[bad]).value_counts().to_dict()
            assert {str(u): int(n) for u, n in got.items()} == {u: n for u, n in lost.items() if n}
            rows = ST.pass_rows(o.ctx_fit, state.scored_units, t_units, t_steps, t_keys, "g1_test")
            fit = rows.fit
            assert isinstance(fit, ST.ContextKeptRows)
            # G-FITCUT: the router rows' hand-out is logged as FitContext wrote it, and its twin records the rows
            # actually fitted (count, newest label step, row-key hash), right after it
            log = o.ctx_fit.log()
            src = log[-1]
            assert (src.object_kind, src.purpose, src.n_rows) == ("router_rows", "g1_test", int(bad.size))
            (at, twin), = rows.fit_log
            assert at == len(log) and twin.purpose == "g1_test" + ST.G1_KEPT_SUFFIX
            assert twin.n_rows == int((~bad).sum()) and twin.max_label_time == int(np.asarray(fit.times).max())
            assert twin.row_key_hash == row_key_hash(fit.unit_ids, fit.times) != src.row_key_hash
            assert (twin.object_kind, twin.lead, twin.cut_kind, twin.cut, twin.groups_hash, twin.fold) == \
                (src.object_kind, src.lead, src.cut_kind, src.cut, src.groups_hash, src.fold)
            left = rows.left_out
            assert np.array_equal(left.row_positions, np.asarray(raw.row_positions)[bad])
            assert left.columns == ("ctx:m", G1_COLUMN) and left.missing[:, 1].all() and not left.missing[:, 0].any()
            assert np.array_equal(fit.row_positions, np.asarray(raw.row_positions)[~bad])
            assert np.array_equal(fit.unit_ids, np.asarray(raw.unit_ids, dtype=object)[~bad])
            assert np.array_equal(fit.times, np.asarray(raw.times)[~bad])
            assert np.asarray(fit.y).tobytes() == np.asarray(raw.y)[~bad].tobytes()
            assert np.asarray(fit.context).tobytes() == np.asarray(raw.context)[~bad].tobytes()  # nothing filled
            rec = rows.context_missing
            assert rec["rows_left_out"] == int(bad.sum()) and rec["fit_rows"] == int(bad.size)
            assert rec["by_column"] == {G1_COLUMN: int(bad.sum())}
            assert rec["by_step"] == {str(t): int(((np.asarray(raw.times) == t) & bad).sum()) for t in (first, first + 1)
                                      if ((np.asarray(raw.times) == t) & bad).any()}
            for u, d in rec["by_unit"].items():
                assert d["left_out"] == lost[u] and d["flagged"] is (d["share"] > 0.05)
            assert rec["normal"] == ST.G1_NORMAL
            # R15 on the fit rows: a unit that lost rows takes its normal from its kept fit rows only, so the
            # router's trees-off still equals its normal (R16; the lead's whole route below runs under that guard)
            n_log = len(o.ctx_fit.log())
            hist, twins = ST.context_kept_histories(o.ctx_fit, state.scored_units, rows)
            new = o.ctx_fit.log()[n_log:]
            # one logged 'normal' hand-out per scored unit (as before G1), and a twin for each unit that lost rows,
            # made right after that unit's hand-out
            assert [(r.object_kind, r.purpose) for r in new] == [("unit_history", "normal")] * len(state.scored_units)
            assert len(twins) == len(rec["by_unit"]) > 0
            for at, twin in twins:
                src = o.ctx_fit.log()[at - 1]
                assert (src.object_kind, src.purpose, twin.purpose) == ("unit_history", "normal", "normal:g1_kept")
                assert 0 < twin.n_rows < src.n_rows and twin.groups_hash == src.groups_hash
                assert twin.max_label_time <= twin.cut == src.cut
            for u in sorted(state.scored_units):
                full = o.ctx_fit.unit_history(u, "g1_test")
                if u in rec["by_unit"]:
                    keep_u = np.asarray(full.times) > first + 1
                    assert np.array_equal(hist[u].times, np.asarray(full.times)[keep_u])
                    assert np.asarray(hist[u].y).tobytes() == np.asarray(full.y)[keep_u].tobytes()
                    assert np.array_equal(hist[u].season_keys, np.asarray(full.season_keys)[keep_u])
                    kept_hash = row_key_hash(np.full(int(keep_u.sum()), u, dtype=object), np.asarray(full.times)[keep_u])
                    assert sum(1 for _, t in twins if t.row_key_hash == kept_hash) == 1    # its twin logs these rows
                    assert rec["by_unit"][u]["fit_rows"] == np.asarray(full.times).size
                else:
                    assert np.array_equal(hist[u].times, full.times)        # a unit that lost nothing: unchanged
            with pytest.raises(RK.RouteRefusal, match=r"\[R20\] the context on fit rows"):
                RK.router_standardisation(raw, raw.context)                                 # the last guard stands
            # scored rows without context refuse loudly (G1), before any kernel or table
            pinned, point = LD.pin_of(state.adoption)
            s_keys = np.asarray(raw.row_positions, dtype=np.int64)[bad]
            inp = PR.PassInput("g1 scored rows", o.ctx_fit, o.store, o.masks, o.pool,
                               np.asarray(raw.unit_ids, dtype=object)[bad], np.asarray(raw.times)[bad], s_keys,
                               o.tol, o.donor_mean_fit, "router_g1_scored", o.c)
            with pytest.raises(ST.StageRefusal, match=r"\[G1\] router_g1_scored: %d scored row\(s\)" % int(bad.sum())):
                PR.PassRouter(state, inp, state.kind, fallback_levels=state.decided_levels()).route([pinned], point)
        with ExitStack() as stack:
            o6 = lad._objects(6, stack)
            rows6 = ST.pass_rows(o6.ctx_fit, state.scored_units, t_units, t_steps, t_keys, "g1_test")
            assert isinstance(rows6.fit, RouterRows)                                       # FitContext's own rows
            assert rows6.context_missing["rows_left_out"] == 0 and rows6.context_missing["by_unit"] == {}
            assert rows6.left_out is None and rows6.fit_log == ()
            assert ST.context_kept_histories(o6.ctx_fit, state.scored_units, rows6) == (None, ())


# ------------------------------------------------------------------------------------------ end to end
@pytest.fixture(scope="module")
def g1_runs(tmp_path_factory):
    """The G1 package run twice from the same package folder, each under its own run root: (off) with the G1
    filter switched off (drop_missing_context a no-op: the current engine, which stands for the pipeline before
    G1 only where no row is left out; module docstring), which must refuse at lead 12 with route.kinds' R20
    exactly as the NDVI smoke did; (on) with G1, which must finish."""
    from treeroute.errors import RefusedError
    from treeroute.pipeline import stages as ST

    base = tmp_path_factory.mktemp("g1_runs")
    pkg = make_g1_package(base / "pk")
    (base / "off").mkdir()
    (base / "on").mkdir()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ST, "drop_missing_context", lambda fit, cols: (fit, None, None))
        with pytest.raises(RefusedError, match=r"\[R20\] the context on fit rows holds \d+ missing or infinite") as info:
            _run(pkg, base / "off")
    off = next((base / "off" / "runs" / "synth_g1" / "smoke").iterdir())
    on = Path(_run(pkg, base / "on"))
    return pkg, off, on, str(info.value)


def test_before_g1_the_package_refused_at_lead_12_after_leads_0_to_6_saved(g1_runs):
    _, off, _, message = g1_runs
    status = _json(off / "status.json")
    assert status["state"] == "failed" and status["phase"] == "ladder_lead_12", status
    assert not (off / "DONE.json").exists() and not (off / "adoption_lead_12.json").exists()
    for lead in EARLY_LEADS:
        assert (off / "phases" / ("ladder_lead_%d" % lead) / "DONE").is_file()
    assert "leave rows with a missing label out of the fit rows (R30)" in message


def test_with_g1_lead_12_runs_and_leaves_out_only_the_early_fit_rows_counted_per_unit(g1_runs):
    pkg, _, on, _ = g1_runs
    assert (on / "DONE.json").is_file() and (on / "ladder" / "ladder.json").is_file()
    derived = _json(on / "derived.json")
    fit_cut0 = int(derived["R11"]["value"]["0"]["fit_cut"])
    assert fit_cut0 % 12 == 0                                                 # _step's month count is the engine's
    lost = {u: n for u, n in _labels_lost(pkg).items() if n}
    rec = _json(on / "ladder" / "lead_12" / "lead.json")
    for pass_name in ("guard", "test"):
        full = rec[pass_name]["router"]["context_missing"]
        summary = rec["context_missing"][pass_name]
        assert full["rows_left_out"] == summary["rows_left_out"] == sum(lost.values()) > 0
        assert {u: d["left_out"] for u, d in full["by_unit"].items()} == lost
        assert set(full["by_step"]) == {str(_step(Y0, m)) for m in LOST_MONTHS}     # the early fit months only
        assert full["by_column"] == {G1_COLUMN: sum(lost.values())}
        for u, d in full["by_unit"].items():
            assert d["share"] == pytest.approx(d["left_out"] / d["fit_rows"], abs=0.0)
            assert d["flagged"] is (d["share"] > 0.05)
        assert summary["flagged_units"] == sorted(u for u, d in full["by_unit"].items() if d["flagged"])
    # the guard's fit rows end at the lead's guard cut (37 Y0-on months here), the test pass's at its fit cut
    # (73): 2 rows left out of a unit are 5.4% (flagged) at the guard and 2.7% (not flagged) at the test pass
    assert rec["context_missing"]["guard"]["flagged_units"]
    assert rec["context_missing"]["test"]["flagged_units"] == []
    for lead in EARLY_LEADS:
        lr = _json(on / "ladder" / ("lead_%d" % lead) / "lead.json")
        for pass_name in ("guard", "test"):
            assert lr["context_missing"][pass_name]["rows_left_out"] == 0
            assert lr[pass_name]["router"]["context_missing"]["by_unit"] == {}
    lad = _json(on / "ladder" / "ladder.json")
    assert lad["context_rows_left_out"]["by_lead"]["12"] == {"guard": sum(lost.values()), "test": sum(lost.values())}
    assert all(v == {"guard": 0, "test": 0} for k, v in lad["context_rows_left_out"]["by_lead"].items() if k != "12")
    assert _json(on / "decision_checks.json")["context_missing"]["rows_left_out"] == 0      # the nowcast
    log = (on / "run.log").read_text(encoding="utf-8")
    assert "lead 12 test pass: G1 left %d of" % sum(lost.values()) in log
    assert log.count("lead 12 guard: G1 unit ") == len(lost)                          # every unit's count printed
    # nothing changed for the scored rows: every lead-12 test row is predicted
    rows = pd.read_parquet(on / "ladder" / "lead_12" / "test_preds.parquet")
    for c in [c for c in rows.columns if c.startswith(("arm__", "placebo__"))]:
        assert np.isfinite(rows[c]).all(), c


def test_lead_0_and_every_lead_without_missing_context_are_byte_identical_to_before_g1(g1_runs):
    """Same package, same engine, G1 switched off (before) and on: the nowcast and lead 6 saved the same bytes
    (decision rows, test rows, guard rows, adoptions)."""
    _, off, on, _ = g1_runs
    names = ["inner_preds.parquet", "test_preds.parquet", "adoption.json", "inner_candidates.csv"]
    names += ["phases/%s/fitctx_log.parquet" % part for part in ("setup_with_inner", "decision", "test_pass",
                                                                  "ladder_contract")]
    for lead in EARLY_LEADS:
        names += ["adoption_lead_%d.json" % lead, "ladder/lead_%d/test_preds.parquet" % lead,
                  "ladder/lead_%d/guard_preds.parquet" % lead, "phases/ladder_lead_%d/fitctx_log.parquet" % lead]
    for name in names:
        assert _sha(off / name) == _sha(on / name), name
    c_off, c_on = _json(off / "ladder" / "contract_lead_0.json"), _json(on / "ladder" / "contract_lead_0.json")
    assert c_on["pool_identical"] and c_on["pinned_pre_clip_identical"] and c_on["trees_off_identical"]
    assert c_on["router"]["context_missing"]["rows_left_out"] == 0 and "context_missing" not in c_off["router"]
    assert {k: v for k, v in c_on.items() if k != "router"} == {k: v for k, v in c_off.items() if k != "router"}


def test_the_lead_12_log_records_every_normal_and_the_rows_g1_kept(g1_runs):
    """G-FITCUT after G1: at lead 12 each pass's context logs one 'normal' hand-out per scored unit and routed
    link (as at every other lead), each trimmed hand-out is followed by its ':g1_kept' twin (the router rows,
    and the normal history of every unit that lost rows) holding the rows actually fitted, and no twin
    appears at a lead or pass that left nothing out."""
    from treeroute.pipeline import stages as ST

    pkg, _, on, _ = g1_runs
    lost = {u: n for u, n in _labels_lost(pkg).items() if n}
    rec = _json(on / "ladder" / "lead_12" / "lead.json")
    log = pd.read_parquet(on / "fitctx_log.parquet")
    n_scored = int(pd.read_parquet(on / "ladder" / "lead_12" / "test_preds.parquet")["unit"].nunique())
    part = log[log["part"] == "ladder_lead_12"].reset_index(drop=True)
    for context, pass_name, purpose in (("ctx_guard_lead_12", "guard", "router_lead_guard"),
                                        ("ctx_fit_lead_12", "test", "router_lead_test")):
        full = rec[pass_name]["router"]["context_missing"]
        frame = part[part["context"] == context].reset_index(drop=True)
        assert (frame.loc[frame["max_label_time"] >= 0, "max_label_time"] <= frame["cut"].iloc[0]).all()
        # the router rows: FitContext's hand-out, then its twin with the kept rows
        i = frame.index[(frame["object_kind"] == "router_rows") & (frame["purpose"] == purpose)].tolist()
        assert len(i) == 1 and frame.loc[i[0], "n_rows"] == full["fit_rows"]
        twin = frame.loc[i[0] + 1]
        assert twin["purpose"] == purpose + ST.G1_KEPT_SUFFIX and twin["object_kind"] == "router_rows"
        assert twin["n_rows"] == full["fit_rows"] - full["rows_left_out"]
        assert twin["groups_hash"] == frame.loc[i[0], "groups_hash"]
        # the normals: one hand-out per scored unit and link, each trimmed one followed by its twin
        normal = frame[(frame["object_kind"] == "unit_history") & (frame["purpose"] == "normal")]
        kept = frame[frame["purpose"] == "normal" + ST.G1_KEPT_SUFFIX]
        units = len(full["by_unit"])
        assert units == len(lost) == n_scored and len(normal) and len(normal) % units == 0
        assert len(kept) == len(normal)                 # every scored unit lost rows here
        assert (frame.loc[kept.index - 1, "purpose"] == "normal").all()
        want = sorted(d["fit_rows"] - d["left_out"] for d in full["by_unit"].values()) * (len(normal) // units)
        assert sorted(kept["n_rows"].tolist()) == sorted(want)
        assert sorted(frame.loc[kept.index - 1, "n_rows"].tolist()) == sorted(
            [d["fit_rows"] for d in full["by_unit"].values()] * (len(normal) // units))
    others = log[log["part"] != "ladder_lead_12"]
    assert not others["purpose"].str.endswith(ST.G1_KEPT_SUFFIX).any()


def test_every_fit_row_g1_left_out_is_saved_with_its_missing_columns(g1_runs):
    pkg, off, on, _ = g1_runs
    lost = {u: n for u, n in _labels_lost(pkg).items() if n}
    rec = _json(on / "ladder" / "lead_12" / "lead.json")
    saved = sorted(p.name for p in (on / "context_missing").iterdir())
    assert saved == ["lead_12_guard.parquet", "lead_12_test_pass.parquet"]     # only the passes that left rows out
    assert not (off / "context_missing").exists()
    for pass_name, name, purpose in (("guard", "lead_12_guard.parquet", "router_lead_guard"),
                                     ("test", "lead_12_test_pass.parquet", "router_lead_test")):
        assert rec[pass_name]["router"]["context_missing"]["rows_file"] == "context_missing/" + name
        assert rec["context_missing"][pass_name]["rows_file"] == "context_missing/" + name
        rows = pd.read_parquet(on / "context_missing" / name)
        assert len(rows) == rec["context_missing"][pass_name]["rows_left_out"] == sum(lost.values())
        assert rows.groupby("unit").size().to_dict() == lost
        assert set(rows["time"]) == {_step(Y0, m) for m in LOST_MONTHS}
        assert (rows["issue"] == rows["time"] - 12).all() and (rows["lead"] == 12).all()
        assert (rows["purpose"] == purpose).all() and rows["row_position"].is_unique
        assert rows["missing__" + G1_COLUMN].all() and not rows["missing__ctx:m"].any()
        cut = rec["cuts"]["guard_cut" if pass_name == "guard" else "fit_cut"]
        assert (rows["cut"] == cut).all() and (rows["time"] <= cut).all()

