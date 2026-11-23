"""A small synthetic world for the vault, FitContext, layer and GLS tests: a keys-only monthly grid, a
target table (some labels invalid), a label-free feature source, derived.json entries (R2, R11, R18
unit lists, R22 links with the legal range) and LORO split sets. Other test files import make_world,
make_context and the decision helpers (surface_keys, make_surface, surface_arms, decide_world) from
here; the tests below check the world itself.

Layout: groups g_a, g_b, g_c (4 units each; g_z holds 2 units and is excluded by split.yaml), monthly
steps over 10 years, test window the last 2 years, train end the year before, inner fit ending 3 years
before that. Leads 0, 1 and 3. Every group's 4 units are bank units; the first 2 are scored. R22's
links are identity and log_c on the legal range [0, inf).
"""

from types import SimpleNamespace

import numpy as np

from treeroute import timing
from treeroute.derive.derived import make_derived
from treeroute.derive.shapes import CutKind, Link, SeasonKeyKind, SeasonKeySpec
from treeroute.io.steps import DenseGrid, build_dense_grid, step_bounds
from treeroute.labels.vault import LabelView
from treeroute.split import LoroSplitSets, UnitLists
from treeroute.timing.shapes import CutPair

MONTHS = 12
Y_FIRST, Y_LAST = 2001, 2010
TEST_FIRST_YEAR = 2009
TRAIN_END_YEAR = 2008
INNER_FIT_END_YEAR = 2005
GROUPS = ("g_a", "g_b", "g_c")
EXCLUDED = "g_z"
UNITS_PER_GROUP = 4
CADENCE = SimpleNamespace(kind="regular", length=1, unit="month")
IN_MONTH = SimpleNamespace(name="y", stamp="period_start", computed_from=(),
                           window=SimpleNamespace(length=1, unit="month", align="forward",
                                                  max_length=None, fact_status="verified"))
PAST_STEP = SimpleNamespace(name="y", stamp="period_start", computed_from=(),
                            window=SimpleNamespace(length=45, unit="day", align="forward",
                                                   max_length=None, fact_status="verified"))


def step_of(year, month):
    return year * MONTHS + month


FIRST_STEP = step_of(Y_FIRST, 1)
LAST_STEP = step_of(Y_LAST, MONTHS)
TEST_FIRST = step_of(TEST_FIRST_YEAR, 1)
FIT_CUT_0 = step_of(TRAIN_END_YEAR, MONTHS)
GUARD_CUT_0 = step_of(INNER_FIT_END_YEAR, MONTHS)
LINKS = (Link.IDENTITY, Link.LOG_C)
LEGAL = (0.0, float("inf"))


class ToyFeatures(object):
    """A label-free FeatureSource over every grid position: 3 tree columns (a few NaN), 1 context."""
    tree_columns = ("f0", "f1", "f2")
    context_columns = ("c0",)

    def __init__(self, n_positions, steps):
        k = np.arange(n_positions, dtype=np.float64)
        self._tree = np.column_stack([np.sin(k * 0.37), np.cos(k * 0.11), (steps % 7) / 7.0]).astype(np.float32)
        self._tree[::17, 1] = np.nan                    # missing tree features: 0-filled by FitContext
        self._ctx = ((steps % MONTHS) / float(MONTHS)).astype(np.float32)[:, None]
        self._ctx[::23, 0] = np.nan                     # router context keeps NaN
        self.calls = []

    def tree_features(self, grid_rows):
        rows = np.asarray(grid_rows, dtype=np.int64)
        self.calls.append(("tree", rows.size))
        return self._tree[rows].copy()

    def context(self, grid_rows):
        rows = np.asarray(grid_rows, dtype=np.int64)
        self.calls.append(("context", rows.size))
        return self._ctx[rows].copy()


def census():
    """(unit ids, group ids, steps, y) of the whole target table, one row per unit x step."""
    units, groups, steps, y = [], [], [], []
    for gi, g in enumerate(GROUPS + (EXCLUDED,)):
        n_units = 2 if g == EXCLUDED else UNITS_PER_GROUP
        for ui in range(n_units):
            u = "%s_u%d" % (g, ui)
            for s in range(FIRST_STEP, LAST_STEP + 1):
                month = (s - 1) % MONTHS + 1
                units.append(u)
                groups.append(g)
                steps.append(s)
                y.append(10.0 * (gi + 1) + ui + 3.0 * np.sin(month) + 0.01 * (s - FIRST_STEP))
    y = np.asarray(y)
    steps = np.asarray(steps, dtype=np.int64)
    y[::29] = np.nan                                    # invalid labels (NaN), never handed out
    return np.asarray(units, dtype=object), np.asarray(groups, dtype=object), steps, y


def window_last_days(steps, target_facts):
    first, last = step_bounds(np.unique(steps), CADENCE)
    ends = {int(s): timing.target_content(target_facts, (int(a), int(b)))[1]
            for s, a, b in zip(np.unique(steps).tolist(), first.tolist(), last.tolist())}
    return np.asarray([ends[int(s)] for s in steps.tolist()], dtype=np.int64)


def cuts(leads=(0, 1, 3)):
    return {lead: CutPair(lead=lead, lead_unit="steps", fit_cut=min(FIT_CUT_0, FIT_CUT_0 - (lead - 1)),
                          guard_cut=min(GUARD_CUT_0, GUARD_CUT_0 - (lead - 1))) for lead in leads}


def unit_lists():
    bank = {g: tuple("%s_u%d" % (g, i) for i in range(UNITS_PER_GROUP)) for g in GROUPS}
    scored = {g: bank[g][:2] for g in GROUPS}
    return UnitLists(bank=bank, scored=scored)


def make_world(run_folder=None, target_facts=IN_MONTH, with_units_entry=True):
    units, groups, steps, y = census()
    grid = build_dense_grid(units, groups, steps, (FIRST_STEP, LAST_STEP))
    target = SimpleNamespace(unit_ids=units, group_ids=groups, time_columns={}, y=y)
    labels = LabelView(grid, target, steps, TEST_FIRST, window_last_days(steps, target_facts), run_folder,
                       cadence=CADENCE)
    n_pos = len(grid.unit_ids) * grid.n_steps
    pos_steps = np.tile(np.arange(FIRST_STEP, LAST_STEP + 1, dtype=np.int64), len(grid.unit_ids))
    features = ToyFeatures(n_pos, pos_steps)
    derived = {"R11": make_derived("R11", cuts(), {"source": "test world"}),
               "R2": make_derived("R2", SeasonKeySpec(kind=SeasonKeyKind.MONTH_OF_YEAR, steps_per_year=MONTHS),
                                  {"source": "test world"}),
               "R22": make_derived("R22", LINKS, {"legal_range": list(LEGAL), "source": "test world"})}
    picks = unit_lists()
    if with_units_entry:
        derived["R18:units"] = make_derived("R18", picks, {"source": "test world"})
    split = LoroSplitSets(excluded={EXCLUDED: "no coverage"}, seen_during_design=(), continuity_groups=())
    return SimpleNamespace(units=units, groups=groups, steps=steps, y=y, grid=grid, target=target,
                           labels=labels, features=features, derived=derived, picks=picks, split=split,
                           target_facts=target_facts)


def make_context(world, lead=0, cut_kind=CutKind.FIT):
    from treeroute.fit.context import FitContext

    return FitContext(world.derived, world.split, world.grid, world.labels, world.features, world.picks,
                      lead, cut_kind)


# ------------------------------------------------------------------------------------------ decisions
def surface_keys(world, cut=FIT_CUT_0, after=GUARD_CUT_0):
    """The inner score rows: every scored unit's valid labelled steps in (after, cut], unit by unit."""
    s = world.labels.asof(cut)
    scored = {u for g in GROUPS for u in world.picks.scored[g]}
    keep = [(u, t) for u, t in zip(s.unit_ids.tolist(), s.times.tolist()) if u in scored and t > after]
    return (np.asarray([u for u, _ in keep], dtype=object), np.asarray([t for _, t in keep], dtype=np.int64))


def make_surface(world, cut=FIT_CUT_0, after=GUARD_CUT_0):
    units, times = surface_keys(world, cut, after)
    return world.labels.decision_surface(units, times, cut)


def surface_arms(y, seed=5, links=LINKS, gls=True, shift=0.0, off_noise=3.0):
    """Synthetic pre-clip surfaces for every arm of candidate_arms(links) without placebos (GLS arms
    left out when gls is False): tree arms y + shift + noise shrinking along the grid, trees-off
    y + noise(off_noise)."""
    from treeroute.layer.arms import ArmSpec, Tool, Weighting, trees_off_of
    from treeroute.layer.decide import SurfaceArm
    from treeroute.route.kinds import per_unit_grid

    grid = per_unit_grid(True)
    rng = np.random.RandomState(seed)
    y = np.asarray(y, dtype=np.float64)
    out = []
    for link in links:
        for tool in (Tool.PLAIN, Tool.CORRECTOR):
            for weighting in ((Weighting.UNWEIGHTED, Weighting.GLS) if gls else (Weighting.UNWEIGHTED,)):
                noise = rng.normal(0.0, 1.0, size=(y.size, len(grid))) * np.linspace(4.0, 1.0, len(grid))
                out.append(SurfaceArm(ArmSpec(link, tool, weighting, True), y[:, None] + noise + shift))
    for link in links:
        out.append(SurfaceArm(trees_off_of(link), y + rng.normal(0.0, 1.0, size=y.size) * off_noise))
    return out


def decide_world(world, declined=False, seed=5, gls=True, **kw):
    """decide() on the world's inner score rows: adopts a tree arm, or (declined) declines, because
    every trees-off then predicts y exactly. Returns the DecisionRecord (registered with the vault)."""
    from treeroute.layer.decide import decide
    from treeroute.route.kinds import per_unit_grid

    s = make_surface(world)
    arms = surface_arms(s.y, seed=seed, gls=gls, off_noise=0.0 if declined else 3.0)
    return decide(s, arms, per_unit_grid(True), LEGAL, make_context(world, 0, CutKind.GUARD), **kw)


# ------------------------------------------------------------------------------------------ the world
def test_world_grid_is_dense_and_sorted():
    w = make_world()
    assert isinstance(w.grid, DenseGrid)
    assert list(w.grid.unit_ids) == sorted(w.grid.unit_ids)
    assert w.grid.n_steps == LAST_STEP - FIRST_STEP + 1
    assert w.labels.test_first_time == TEST_FIRST


def test_world_decision_helpers_adopt_and_decline_as_designed():
    w = make_world()
    units, times = surface_keys(w)
    assert units.size == times.size > 100 and times.min() > GUARD_CUT_0 and times.max() <= FIT_CUT_0
    scored = {u for g in GROUPS for u in w.picks.scored[g]}
    assert set(units.tolist()) == scored
    assert not decide_world(w).adoption.declined
    assert decide_world(w, declined=True).adoption.declined


def test_world_windows_reach_past_the_step_only_in_the_past_step_variant():
    units, groups, steps, y = census()
    inside = window_last_days(steps[:MONTHS], IN_MONTH)
    past = window_last_days(steps[:MONTHS], PAST_STEP)
    last = step_bounds(steps[:MONTHS], CADENCE)[1]
    assert np.array_equal(inside, last)
    assert (past > last).all()
