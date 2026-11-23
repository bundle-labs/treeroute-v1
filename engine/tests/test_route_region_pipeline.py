"""The region router's ENGINE mode on the REAL tree-answer store (fit/tables.TreeAnswerStore), built by the
pipeline's own steps.

tests/test_route_region.py proves the region kernels on an in-memory FakeStore; the legacy gate
(legacy_harness/region_replay.py) proves the solver on the shipped defo banks in LEGACY mode (no normal,
the shipped row cap, no mask). Neither reads a table the engine built. Here the pipeline's own steps
(treeroute.pipeline.run.Pipeline up to the temp folder, then passes.RunState.build_pool and fit: the vault,
the pool, the inner-cut bank refit and its TreeAnswerStore, the own-block masks, the normals, the guard
tolerances) run on tests/test_pipeline.py's synthetic package (4 groups; grp_a and grp_b touch on the
grid and form ONE overlap block), and the region kernels read that store in engine mode:

  - the kernel's predictions at every level are the direct solve (region_gram / region_ridge /
    region_predict with the normal column) on the store's own answers at the mask's columns, byte for byte;
  - the own overlap block is dropped: for grp_a the store answers grp_b's trees, the router never reads
    them (and never grp_a's, which the store holds back);
  - trees-off equals the units' normals within the run's own guard tolerance (R16);
  - the whole-unit cap (a lowered budget) keeps split.region_cap_units' units, fits their rows only and
    still scores every scored unit;
  - one Gram shared across the run's links (L4) gives the same bytes as a fresh Gram per link, and is
    bound to the store's real bank fingerprint and table kind.

Every file goes under the test's temp folder (a fake machine file: run root, temp dir, registry); the
run folder and temp dir are released at the end. The pipeline's region WIRING is not built (pipeline/ is
outside the region module): this drives the kernels beside the pipeline, as the wiring will.
"""

from contextlib import contextmanager
from dataclasses import replace as _replace

import numpy as np
import pytest

from test_pipeline import FAKE_LAUNCH, _machine, make_pipeline_package, sklearnex_patched  # noqa: F401

from treeroute import engine_constants as K
from treeroute import split as SP
from treeroute.route import region as R
from treeroute.route.kinds import RouteRefusal


@contextmanager
def _pipeline_state(base):
    """The synthetic package run through Pipeline.run()'s own steps up to the temp folder, then
    RunState.build_pool() and fit() (the inner-cut bank and its store); released on exit."""
    from treeroute.pipeline import passes as P
    from treeroute.pipeline.run import Pipeline

    pkg = make_pipeline_package(base / "pk")
    pipe = Pipeline(pkg, base / "runs", "smoke", machine=_machine(base), echo=lambda s: None,
                    launch_record=FAKE_LAUNCH)
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
            yield state
    finally:
        pipe._release()


@pytest.fixture(scope="module")
def run_state(tmp_path_factory):
    with _pipeline_state(tmp_path_factory.mktemp("region_pipeline")) as state:
        yield state


def _region_rows(state, group, link):
    """RegionRows of one group in one link, from the pipeline's inner decision context (the guard cut):
    fit rows = the group's BANK units' valid rows at or before the cut (FitContext.router_rows, through
    stages.pass_rows), score rows = its scored units' steps after the cut up to the fit cut, normals =
    stages.unit_normals (R15). The inner store's plain and corrector tables are built over both."""
    from treeroute.pipeline import stages as ST

    ctx = state.ctx_inner
    fit_cut = int(state.cuts.fit_cut)
    cut = int(ctx.cut)
    bank = sorted(state.lists.bank[group])
    scored = sorted(state.lists.scored[group])
    n = int(state.vg.grid.n_steps)
    ids = ST.unit_positions(state.vg, bank, None, fit_cut)
    for kind in ("plain", "corrector"):
        state.store_inner.build(group, kind, ids, ST.zero_filled(state.inner_features))
    s_keys = ST.unit_positions(state.vg, scored, cut + 1, fit_cut)
    s_units = np.asarray(state.vg.grid.unit_ids, dtype=object)[s_keys // n]
    s_steps = (state.vg.first_step + s_keys % n).astype(np.int64)
    prows = ST.pass_rows(ctx, bank, s_units, s_steps, s_keys, "router_inner")
    normals = ST.unit_normals(ctx, bank, link, state.c, state.ub, state.donor_mean_inner[link], state.season)
    pr = ST.per_unit_rows(prows, link, state.c, state.ub, normals, state.season, state.unit_group)
    return R.RegionRows(cut=cut, group=group, fit_units=tuple(bank), scored_units=tuple(scored),
                        fit_unit=pr.fit_unit, fit_time=pr.fit_time, fit_y=pr.fit_y, fit_normal=pr.fit_normal,
                        fit_keys=pr.fit_keys, score_unit=pr.score_unit, score_time=pr.score_time,
                        score_normal=pr.score_normal, score_keys=pr.score_keys, score_rows=pr.score_rows)


def _direct(state, rows, kind, kept_units):
    """The engine-mode solve written out from the store's own answers: the rows of the kept units, the
    mask's columns, every region level. At the kernel's BLAS thread count: the float32 Gram's bytes
    depend on how OpenBLAS splits the accumulation over threads (the region gate's finding)."""
    from threadpoolctl import threadpool_limits

    with threadpool_limits(limits=int(K.BLAS_THREADS), user_api="blas"):
        return _direct_solve(state, rows, kind, kept_units)


def _direct_solve(state, rows, kind, kept_units):
    store, masks = state.store_inner, state.masks_inner
    fit_sel = np.isin(np.asarray(rows.fit_unit, dtype=object), np.asarray(kept_units, dtype=object))
    view = store.unit_view(np.concatenate([rows.fit_keys[fit_sel], rows.score_keys]), kind)
    want = np.asarray(masks.columns_by_group[rows.group], dtype=np.int64)
    pos = np.searchsorted(view.tree_index, want)
    assert np.array_equal(view.tree_index[pos], want)
    vals = np.asarray(view.values)[:, pos]
    nf = int(fit_sel.sum())
    gram = R.region_gram(vals[:nf])
    out = []
    for point in R.region_grid():
        fit = R.region_ridge(gram, rows.fit_y[fit_sel], R.region_lambda(point), rows.fit_normal[fit_sel])
        out.append(R.region_predict(fit, vals[nf:], rows.score_normal))
    return np.column_stack(out)


@pytest.mark.parametrize("group", ["grp_a", "grp_c"])
def test_engine_mode_on_the_real_store_is_the_direct_solve_and_drops_the_own_block(run_state, group):
    st = run_state
    L = st.links[0]
    rows = _region_rows(st, group, L)
    out = R._route_region_grid(rows, st.store_inner, "plain", st.masks_inner, st.tol[L])
    assert out.n_units_fitted == len(rows.fit_units)             # 12 units: far below the 60,000-row budget
    assert out.predictions.shape == (rows.score_keys.size, len(R.region_grid()))
    assert np.isfinite(out.predictions).all()
    assert out.predictions.tobytes() == _direct(st, rows, "plain", rows.fit_units).tobytes()
    # the own overlap block: the store answers every tree but the group's own; the router drops the block
    owners = np.asarray(st.bank_inner.tree_group, dtype=object)
    answered = set(owners[st.store_inner.unit_view(rows.fit_keys[:3], "plain").tree_index].tolist())
    used = set(owners[st.masks_inner.columns_by_group[group]].tolist())
    assert group not in answered
    if group == "grp_a":
        assert "grp_b" in answered and used == {"grp_c", "grp_d"}
    else:
        assert used == {"grp_a", "grp_b", "grp_d"} == answered
    # R16: trees-off is the units' normals, within the run's own guard tolerance
    assert np.max(np.abs(out.trees_off - rows.score_normal)) <= st.tol[L]
    # the level at the centre is the one-level route
    at = R._route_region_at(rows, st.store_inner, "plain", st.masks_inner, R.region_centre(), st.tol[L])
    k = list(R.region_grid()).index(R.region_centre())
    assert at.predictions[:, 0].tobytes() == out.predictions[:, k].tobytes()


def test_the_whole_unit_cap_on_the_real_store(run_state, monkeypatch):
    st = run_state
    L = st.links[0]
    rows = _region_rows(st, "grp_d", L)
    counts = {u: int(np.count_nonzero(rows.fit_unit == u)) for u in rows.fit_units}
    budget = int(0.4 * sum(counts.values()))
    kept = SP.region_cap_units(rows.fit_units, counts, budget)
    assert 1 < len(kept) < len(rows.fit_units)
    monkeypatch.setattr(K, "REGION_ROUTER_ROW_BUDGET", budget)
    out = R._route_region_grid(rows, st.store_inner, "plain", st.masks_inner, st.tol[L])
    assert out.n_units_fitted == len(kept)
    assert out.predictions.tobytes() == _direct(st, rows, "plain", kept).tobytes()
    # every scored unit is scored, also the ones outside the cap (with its own normal, R15)
    outside = sorted(set(rows.scored_units) - set(kept))
    assert outside and np.isin(rows.score_unit, np.asarray(outside, dtype=object)).any()
    assert np.isfinite(out.predictions).all()


def test_one_gram_shared_across_the_runs_links_gives_the_same_bytes(run_state):
    st = run_state
    assert len(st.links) >= 2, st.links
    group = "grp_b"
    by_link = {L: _region_rows(st, group, L) for L in st.links}
    first = by_link[st.links[0]]
    for L, rows in by_link.items():                              # the links share the fit rows (L4)
        assert np.array_equal(rows.fit_keys, first.fit_keys)
    gram = R.region_shared_gram(first, st.store_inner, "corrector", st.masks_inner)
    for L, rows in by_link.items():
        fresh = R._route_region_grid(rows, st.store_inner, "corrector", st.masks_inner, st.tol[L])
        shared = R._route_region_grid(rows, st.store_inner, "corrector", st.masks_inner, st.tol[L], gram=gram)
        assert shared.predictions.tobytes() == fresh.predictions.tobytes(), L
        assert shared.trees_off.tobytes() == fresh.trees_off.tobytes(), L
    with pytest.raises(RouteRefusal):                           # another table kind
        R._route_region_grid(first, st.store_inner, "plain", st.masks_inner, st.tol[st.links[0]], gram=gram)
    # the fingerprint is the real bank's: the same rows on a store claiming another bank are refused
    real = st.store_inner.bank_fingerprint
    assert real == st.bank_inner.manifest.bank_fingerprint and real
    try:
        st.store_inner.bank_fingerprint = real[::-1]
        with pytest.raises(RouteRefusal, match="shared Gram"):
            R._route_region_grid(first, st.store_inner, "corrector", st.masks_inner, st.tol[st.links[0]],
                                 gram=gram)
    finally:
        st.store_inner.bank_fingerprint = real


def test_a_score_row_at_the_cut_or_a_foreign_unit_is_refused_on_the_real_rows(run_state):
    st = run_state
    L = st.links[0]
    rows = _region_rows(st, "grp_c", L)
    early = _replace(rows, score_time=np.where(np.arange(rows.score_time.size) == 0, rows.cut, rows.score_time))
    with pytest.raises(RouteRefusal):
        R._route_region_grid(early, st.store_inner, "plain", st.masks_inner, st.tol[L])
    other = sorted(st.lists.bank["grp_d"])[0]
    stray = _replace(rows, fit_unit=np.where(np.arange(rows.fit_unit.size) == 0, other, rows.fit_unit))
    with pytest.raises(RouteRefusal):
        R._route_region_grid(stray, st.store_inner, "plain", st.masks_inner, st.tol[L])
