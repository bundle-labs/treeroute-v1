"""treeroute.route.kinds: the per-unit building blocks (R12, R14-R16, R20, R26, R36) and the kinds
that are not built yet (region: Tue 6 Oct; neighbour: M8)."""

import math
from types import SimpleNamespace

import numpy as np
import pytest

from treeroute import engine_constants as K
from treeroute.errors import UnsetConstantError
from treeroute.route import kinds as R


# ------------------------------------------------------------------------------ grid (R14, R26)
def test_the_grid_is_seven_levels_by_five_ratios_level_major():
    grid = R.per_unit_grid(True)
    assert len(grid) == 35
    assert [(p.level, p.ratio) for p in grid] == [(m, r) for m in K.PENALTY_LEVELS
                                                  for r in K.PENALTY_RATIOS]
    free = R.per_unit_grid(False)
    assert [(p.level, p.ratio) for p in free] == [(m, None) for m in K.PENALTY_LEVELS]


def test_penalties_are_formed_as_the_source_forms_them():
    alpha = K.PER_UNIT_TREES_CENTRE
    for p in R.per_unit_grid(True):
        a_tree, a_ctx = R.point_penalties(p, True)
        assert a_tree == alpha * p.level and a_ctx == alpha * p.level * p.ratio   # same floats
    for p in R.per_unit_grid(False):
        assert R.point_penalties(p, False) == (alpha * p.level, 0.0)


def test_the_centre_point_is_the_pair_of_engine_constant_centres():
    centre = R.per_unit_centre(True)
    assert centre == R.GridPoint(1.0, 0.5)
    assert R.point_penalties(centre, True) == (K.PER_UNIT_TREES_CENTRE, K.PER_UNIT_CONTEXT_CENTRE)
    assert R.per_unit_centre(False) == R.GridPoint(1.0, None)


def test_a_point_off_the_grid_is_refused():
    for bad in (R.GridPoint(2.0, 0.5), R.GridPoint(1.0, 0.3), R.GridPoint(1.0, None), (1.0, 0.5)):
        with pytest.raises(R.RouteRefusal, match="R26"):
            R.point_penalties(bad, True)
    with pytest.raises(R.RouteRefusal, match="R26"):
        R.point_penalties(R.GridPoint(1.0, 0.5), False)


def test_the_per_unit_design_names_its_blocks():
    d = R.per_unit_router_design(True)
    assert d.kind is R.RouterKind.PER_UNIT
    assert d.columns == ("intercept", "normal", "context", "trees")
    assert d.unpenalised == ("intercept", "normal") and d.fit_row_cap is None
    assert d.grid == R.per_unit_grid(True)
    assert R.per_unit_router_design(False).columns == ("intercept", "normal", "trees")
    assert R.trees_off_router_design().columns == ("intercept", "normal")


# ------------------------------------------------------------------------------ columns (R14)
def test_build_column_block_layout_and_centring():
    n = 6
    normal = np.linspace(1.0, 2.0, n)
    ctx = np.arange(12, dtype=float).reshape(n, 2)
    trees = np.arange(18, dtype=np.float32).reshape(n, 3)
    dm = R.build_column_block(R.per_unit_router_design(True), normal, ctx, trees, 1.25)
    assert dm.blocks == ("intercept", "normal", "context", "context", "trees", "trees", "trees")
    assert dm.X.dtype == np.float64 and dm.X.flags["C_CONTIGUOUS"]
    want = np.column_stack([np.ones(n), normal - 1.25, ctx, trees.astype(np.float64)])
    assert dm.X.tobytes() == want.tobytes()


def test_build_column_block_refuses_missing_or_extra_blocks_and_bad_values():
    n = 4
    normal, ctx, trees = np.ones(n), np.zeros((n, 1)), np.ones((n, 2))
    d = R.per_unit_router_design(True)
    with pytest.raises(R.RouteRefusal, match="none was given"):
        R.build_column_block(d, normal, None, trees, 0.0)
    with pytest.raises(R.RouteRefusal, match="the design lists"):
        R.build_column_block(R.per_unit_router_design(False), normal, ctx, trees, 0.0)
    with pytest.raises(R.RouteRefusal, match="rows"):
        R.build_column_block(d, normal, ctx, np.ones((n + 1, 2)), 0.0)
    with pytest.raises(R.RouteRefusal, match="missing or infinite"):
        R.build_column_block(d, normal, ctx, np.array([[1.0, np.inf]] * n), 0.0)
    with pytest.raises(R.RouteRefusal, match="centre"):
        R.build_column_block(d, normal, ctx, trees, float("nan"))


# ------------------------------------------------------------------------------ standardisation (R20)
def test_standardisation_is_mean_and_sd_plus_offset_over_all_fit_rows():
    C = np.column_stack([np.tile(np.arange(1, 13), 3), np.full(36, 12.5)]).astype(np.float64)
    rows = SimpleNamespace(cut=10, times=np.arange(36) % 11)
    mu, sd = R.router_standardisation(rows, C)
    assert mu.tobytes() == C.mean(0).tobytes()
    assert sd.tobytes() == (C.std(0) + 1e-9).tobytes()
    Z = R.standardise_context(C, mu, sd)
    assert np.all(Z[:, 1] == 0.0)                       # a constant column standardises to 0
    assert R.CONTEXT_SD_OFFSET == 1e-9


def test_standardisation_refuses_rows_after_the_cut_and_bad_context():
    C = np.ones((5, 2))
    with pytest.raises(R.RouteRefusal, match="G-FITCUT"):
        R.router_standardisation(SimpleNamespace(cut=3, times=np.arange(5)), C)
    with pytest.raises(R.RouteRefusal, match="R20"):
        R.router_standardisation(SimpleNamespace(cut=9, times=np.arange(5)), np.ones((4, 2)))
    with pytest.raises(R.RouteRefusal, match="R20"):
        R.router_standardisation(SimpleNamespace(cut=9, times=np.arange(5)),
                                 np.array([[1.0, np.nan]] * 5))
    with pytest.raises(R.RouteRefusal, match="R20"):
        R.router_standardisation(SimpleNamespace(times=np.arange(5)), C)


# ------------------------------------------------------------------------------ normal (R15)
def test_season_normal_means_and_fallbacks():
    keys = np.array([1, 1, 2, 2, 2, 4])
    y = np.array([1.0, 3.0, 2.0, 4.0, 6.0, 10.0])
    t = np.arange(6)
    table = R.season_normal("u1", "identity", 5, None, t, keys, y, np.array([1, 2, 3, 4]), -7.0)
    assert table.by_season == {1: 2.0, 2: 4.0, 3: float(y.mean()), 4: 10.0}
    assert table.n_season_from_unit_mean == 1 and not table.used_donor_mean
    assert table.cut == 5 and table.unit_all_season_mean == float(y.mean())
    assert R.normal_values(table, np.array([4, 1, 3])).tolist() == [10.0, 2.0, float(y.mean())]
    empty = R.season_normal("u2", "identity", 5, None, np.array([], int), np.array([], int),
                            np.array([]), np.array([1, 2]), -7.0)
    assert empty.used_donor_mean and empty.by_season == {1: -7.0, 2: -7.0}


def test_season_normal_refusals():
    t, k, y = np.arange(3), np.array([1, 1, 2]), np.array([1.0, 2.0, 3.0])
    with pytest.raises(R.RouteRefusal, match="G-FITCUT"):
        R.season_normal("u", "identity", 1, None, t, k, y, np.array([1]), 0.0)
    with pytest.raises(R.RouteRefusal, match="R30"):
        R.season_normal("u", "identity", 5, None, t, k, np.array([1.0, np.nan, 3.0]), np.array([1]), 0.0)
    with pytest.raises(R.RouteRefusal, match="R15"):
        R.season_normal("u", "identity", 5, None, t, k, y, np.array([1]), float("inf"))
    table = R.season_normal("u", "identity", 5, None, t, k, y, np.array([1]), 0.0)
    with pytest.raises(R.RouteRefusal, match="season key"):
        R.normal_values(table, np.array([3]))


# ------------------------------------------------------------------------------ trees-off (R16, R36)
def _season_panel(seed=0, n=48):
    rs = np.random.RandomState(seed)
    keys = np.tile(np.arange(1, 13), n // 12)
    y = 2.0 + np.sin(keys) + rs.normal(0.0, 0.5, n)
    table = R.season_normal("u", "identity", 100, None, np.arange(n), keys, y, np.arange(1, 13), 0.0)
    fit_normal = R.normal_values(table, keys)
    score_normal = R.normal_values(table, np.arange(1, 13))
    return fit_normal, y, score_normal


def test_trees_off_is_intercept_plus_normal_and_equals_the_normal():
    fn, y, sn = _season_panel()
    p = R._trees_off_checked(fn, y, sn, 1e-6)
    assert float(np.max(np.abs(p - sn))) < 1e-8


def test_trees_off_refuses_a_normal_that_it_cannot_reproduce():
    fn, y, sn = _season_panel(seed=1)
    wrong = fn + np.cos(np.arange(fn.size))            # not the season mean of these fit rows
    with pytest.raises(R.RouteGuardError, match="R16: unit u7"):
        R._trees_off_checked(wrong, y, sn, 1e-6, "unit u7")
    for bad in (-1.0, 0.0, float("nan"), None):
        with pytest.raises(R.RouteRefusal, match="R36"):
            R._trees_off_checked(fn, y, sn, bad)
    with pytest.raises(TypeError):
        R._trees_off_checked(fn, y, sn)                # no silent default tolerance


def test_the_approved_trees_off_signature_has_no_tolerance_so_it_raises_naming_the_gap():
    fn, y, sn = _season_panel()
    with pytest.raises(NotImplementedError, match="R36 tolerance.*owner decision pending"):
        R.trees_off_with_normal(fn, y, sn)


def test_the_r36_tolerance_refuses_until_k_is_set():
    with pytest.raises(UnsetConstantError):
        R.r36_tolerance(1.0)


def test_reference_predictions():
    from enum import Enum

    class Link(Enum):
        IDENTITY = "identity"
        LOG_C = "log_c"

    ident, logc = Link.IDENTITY, Link.LOG_C
    refs, target = R.reference_predictions({ident: [1.0, 2.0], logc: [0.9, 1.8]})
    assert target.tolist() == [1.0, 2.0] and refs[logc].tolist() == [0.9, 1.8]
    with pytest.raises(R.RouteRefusal, match="identity"):
        R.reference_predictions({logc: [1.0]})


# ------------------------------------------------------------------------------ short history (R12)
def test_fallback_units_threshold_share_and_flag():
    counts = {"u%d" % i: 30 for i in range(19)}
    counts["u_short"] = K.PER_UNIT_MIN_VALID_ROWS - 1
    counts["u_edge"] = K.PER_UNIT_MIN_VALID_ROWS
    ids, share = R.fallback_units(counts)
    assert ids == ("u_short",) and share == pytest.approx(1 / 21.0)
    assert not R.fallback_share_flagged(share)
    assert R.fallback_share_flagged(2 / 21.0)
    with pytest.raises(R.RouteRefusal, match="R12"):
        R.fallback_units({})
    with pytest.raises(R.RouteRefusal, match="R12"):
        R.fallback_units({"u": -1})


# ------------------------------------------------------------------------------ own-block columns
def test_router_tree_columns_drops_every_group_of_the_block():
    tg = ["a"] * 3 + ["b"] * 2 + ["c"] * 4
    assert R.router_tree_columns(tg, ("a",)).tolist() == list(range(3, 9))
    assert R.router_tree_columns(tg, ("a", "b")).tolist() == list(range(5, 9))
    assert R.router_tree_columns(tg, ("a", "b")).dtype == np.int64
    with pytest.raises(R.RouteRefusal, match="every tree"):
        R.router_tree_columns(tg, ("a", "b", "c"))
    with pytest.raises(R.RouteRefusal, match="own groups"):
        R.router_tree_columns(tg, ())
    with pytest.raises(R.RouteRefusal, match="owns no tree"):
        R.router_tree_columns(tg, ("z",))


def test_own_block_tree_columns_builds_every_group_from_the_blocks():
    tg = ["a"] * 3 + ["b"] * 2 + ["c"] * 4
    cols = R.own_block_tree_columns(tg, {"a": ("b", "a"), "b": ("a", "b"), "c": ("c",)})
    assert cols.router_groups == {"a": ("a", "b"), "b": ("a", "b"), "c": ("c",)}
    assert cols.blocks == (("a", "b"), ("c",))
    assert cols.columns_by_group["c"].tolist() == [0, 1, 2, 3, 4]
    assert cols.columns_by_group["b"].tolist() == [5, 6, 7, 8]
    with pytest.raises(R.RouteRefusal, match="in no overlap block"):     # c's block is not given
        R.own_block_tree_columns(tg, {"a": ("a", "b"), "b": ("a", "b")})
    with pytest.raises(R.RouteRefusal, match="split"):
        R.own_block_tree_columns(tg, {"a": ("a", "b"), "b": ("b",), "c": ("c",)})


BLOCKS_AB_C = (("a", "b"), ("c",))


def _cols(tg, columns, router_groups, blocks=BLOCKS_AB_C):
    return R.RouterTreeColumns(tree_group=tg, blocks=blocks, columns_by_group=columns,
                               router_groups=router_groups)


def test_router_tree_columns_shape_checks():
    tg = ("a", "a", "b", "c")
    with pytest.raises(R.RouteRefusal, match="ascending"):
        _cols(tg, {"c": np.array([1, 0, 2])}, {"c": ("c",)})
    with pytest.raises(R.RouteRefusal, match="no router groups"):
        _cols(tg, {"c": np.array([0, 1, 2])}, {})
    with pytest.raises(R.RouteRefusal, match="not among its own"):
        _cols(tg, {"b": np.array([3])}, {"b": ("c",)})


def test_a_direct_mask_must_hold_whole_blocks_and_drop_nothing_else():
    tg = ("a", "a", "b", "c")
    given = {"a": np.array([3]), "c": np.array([0, 1, 2])}
    ok = _cols(tg, given, {"a": ("a", "b"), "c": ("c",)})
    assert ok.columns_by_group["a"].tolist() == [3]
    # a checked mask is frozen: read-only copies, so it cannot change after the checks
    given["a"][0] = 2
    assert ok.columns_by_group["a"].tolist() == [3]
    with pytest.raises(TypeError):
        ok.columns_by_group["a"] = np.array([2, 3])
    with pytest.raises(TypeError):
        ok.router_groups["a"] = ("a",)
    with pytest.raises(ValueError):
        ok.columns_by_group["c"][0] = 2
    # router groups (a,) split the block (a, b): b's trees would be used by a's routers
    with pytest.raises(R.RouteRefusal, match="split an overlap block.*'b'"):
        _cols(tg, {"a": np.array([2, 3])}, {"a": ("a",)})
    # a column of an own-block tree (b's tree 2 for group a)
    with pytest.raises(R.RouteGuardError, match="G-DISJOINT"):
        _cols(tg, {"a": np.array([2, 3])}, {"a": ("a", "b")})
    # a mask that drops a tree outside the block (c's routers lose b's tree)
    with pytest.raises(R.RouteRefusal, match="nothing else"):
        _cols(tg, {"c": np.array([0, 1])}, {"c": ("c",)})
    # blocks that are not a partition, a tree group without a block, a router group without a block
    with pytest.raises(R.RouteRefusal, match="two blocks"):
        _cols(tg, {"c": np.array([0, 1, 2])}, {"c": ("c",)}, blocks=(("a", "b"), ("b", "c")))
    with pytest.raises(R.RouteRefusal, match="not sorted"):
        _cols(tg, {"c": np.array([0, 1, 2])}, {"c": ("c",)}, blocks=(("b", "a"), ("c",)))
    with pytest.raises(R.RouteRefusal, match="in no overlap block"):
        _cols(tg, {"c": np.array([0, 1, 2])}, {"c": ("c",)}, blocks=(("a", "b"),))
    with pytest.raises(R.RouteRefusal, match="in no overlap block"):
        _cols(tg, {"c": np.array([0, 1, 2])}, {"c": ("c", "z")})
    with pytest.raises(R.RouteRefusal, match="tuple of groups"):
        _cols(tg, {"c": np.array([0, 1, 2])}, {"c": ("c",)}, blocks=("ab", ("c",)))


# ------------------------------------------------------------------------------ not built yet
REGION = [("region_cap_units", 3), ("route_region", 11), ("route_region_loro", 13),
          ("search_fallback_level", 3)]
NEIGHBOUR = [("trees_off_neighbour", 4), ("neighbour_pool", 11), ("neighbour_pool_loro", 11),
             ("route_neighbour", 9), ("route_neighbour_loro", 11)]


@pytest.mark.parametrize("name,nargs", REGION)
def test_region_kind_raises_naming_its_milestone(name, nargs):
    with pytest.raises(NotImplementedError, match="Tue 6 Oct"):
        getattr(R, name)(*([None] * nargs))


@pytest.mark.parametrize("name,nargs", NEIGHBOUR)
def test_neighbour_kind_raises_naming_its_milestone(name, nargs):
    with pytest.raises(NotImplementedError, match="M8"):
        getattr(R, name)(*([None] * nargs))


def test_fitcontext_level_wrappers_raise_naming_what_they_need():
    with pytest.raises(NotImplementedError, match="FitContext"):
        R.route_per_unit_loro(*([None] * 12))
    with pytest.raises(NotImplementedError, match="Sat 3 Oct"):
        R.unit_season_normal(*([None] * 7))
    with pytest.raises(NotImplementedError, match="Sat 3 Oct"):
        R.donor_link_mean(*([None] * 4))


# The approved contracts, read as TEXT (engine code may not import _proposed; G-IMPORT). Every
# approved router function must exist in route/kinds.py with EXACTLY the approved parameter list.
APPROVED_FILES = ("route_kinds.py", "loro_additions.py")
ROUTE_KINDS_APPROVED = (
    "unit_season_normal", "donor_link_mean", "build_column_block", "router_standardisation",
    "trees_off_with_normal", "trees_off_neighbour", "reference_predictions", "region_cap_units",
    "route_region", "fallback_units", "search_fallback_level", "neighbour_pool", "route_neighbour",
    "router_tree_columns", "assert_no_own_group_column", "route_per_unit_loro", "route_region_loro",
    "neighbour_pool_loro", "route_neighbour_loro")


def _approved_parameters():
    import ast
    from pathlib import Path

    folder = Path(R.__file__).resolve().parents[1] / "_proposed"
    out = {}
    for name in APPROVED_FILES:
        for node in ast.parse((folder / name).read_text(encoding="utf-8")).body:
            if isinstance(node, ast.FunctionDef):
                a = node.args
                out[node.name] = ([x.arg for x in a.posonlyargs] + [x.arg for x in a.args]
                                  + ([a.vararg.arg] if a.vararg else []) + [x.arg for x in a.kwonlyargs]
                                  + ([a.kwarg.arg] if a.kwarg else []))
    return out


def test_the_approved_signatures_are_kept_exactly():
    import inspect

    approved = _approved_parameters()
    for name in ROUTE_KINDS_APPROVED:
        assert name in approved, name
        assert list(inspect.signature(getattr(R, name)).parameters) == approved[name], name
    # every public function of route/kinds.py that shares a name with an approved one keeps its list
    for name in R.__all__:
        obj = getattr(R, name)
        if callable(obj) and name in approved and not isinstance(obj, type):
            assert list(inspect.signature(obj).parameters) == approved[name], name
    assert approved["trees_off_with_normal"] == ["fit_normal", "fit_y_link", "score_normal"]
    assert math.isclose(K.PER_UNIT_CONTEXT_CENTRE / K.PER_UNIT_TREES_CENTRE, 0.5)


def test_the_unapproved_router_kernels_are_private():
    # proposed public entry points await the owner; until then only the approved names are public
    for name in ("route_per_unit_grid", "route_per_unit_at"):
        assert not hasattr(R, name) and name not in R.__all__
    assert callable(R._route_per_unit_grid) and callable(R._route_per_unit_at)
    assert "_trees_off_checked" not in R.__all__
