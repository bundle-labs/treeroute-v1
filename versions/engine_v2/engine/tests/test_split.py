"""treeroute.split under leave-one-region-out: sorted sets, the groups, R18's two unit lists, the C16
budget, the region fit cap, overlap blocks, rival folds, and the set / disjointness checks.

Synthetic data throughout, plus one read-only check on a real store (defo's target unit ids; skipped when
D: is not on the machine). Tests may name problems and regions (G-NONAMES scans engine code only).
"""

from pathlib import Path

import numpy as np
import pytest

from treeroute import engine_constants as K
from treeroute import split as SP
from treeroute.derive import Derived, derived_entry
from treeroute.errors import RefusedError
from treeroute.fit.bank import BankManifest, _hash_strings
from treeroute.package import schema as S


def refused(fn, *args, match=None, **kwargs):
    with pytest.raises(SP.SplitRefusal) as info:
        fn(*args, **kwargs)
    assert isinstance(info.value, RefusedError)
    if match:
        assert match in str(info.value), str(info.value)
    return info.value


# ---------------------------------------------------------------------------------------------------
# sorted sets, split sets, groups
def test_as_sorted_set_sorts_by_code_point_and_refuses_repeats():
    assert SP.as_sorted_set(["b", "a", "C", "a_b", "a-b"], "x") == ("C", "a", "a-b", "a_b", "b")
    assert SP.as_sorted_set((), "x") == ()
    refused(SP.as_sorted_set, ["a", "b", "a"], "groups", match="more than once")
    refused(SP.as_sorted_set, ["a", ""], "groups")
    refused(SP.as_sorted_set, ["a", 3], "groups")
    refused(SP.as_sorted_set, "abc", "groups", match="single string")


def test_loro_split_sets_from_the_package_model():
    model = S.SplitFile.model_validate({"excluded": {"z": "no coverage"}, "seen_during_design": ["b", "a"]})
    sets = SP.loro_split_sets(model)
    assert sets == SP.LoroSplitSets(excluded={"z": "no coverage"}, seen_during_design=("a", "b"),
                                    continuity_groups=())
    refused(SP.loro_split_sets, object(), match="no 'excluded' field")


def test_loro_split_differences_lists_every_problem_and_nothing_else():
    ok = SP.LoroSplitSets(excluded={"z": "r"}, seen_during_design=("a",), continuity_groups=("b",))
    assert SP.loro_split_differences(ok, ("a", "b", "c", "z")) == SP.LoroSplitDiff((), (), ())
    bad = SP.LoroSplitSets(excluded={"z": "r", "gone": "r", "a": "r"}, seen_during_design=("a", "a", "q"),
                           continuity_groups=("b", "b"))
    diff = SP.loro_split_differences(bad, ("a", "b", "z", "z"))
    assert diff.listed_not_in_data == ("gone", "q")
    assert diff.reported_and_excluded == ("a",)
    assert diff.duplicates == ("a", "b", "z")


def test_groups_under_loro_are_the_data_minus_the_exclusions_sorted():
    sets = SP.LoroSplitSets(excluded={"g2": "r"}, seen_during_design=(), continuity_groups=())
    assert SP.groups_under_loro(sets, ("g3", "g1", "g2")) == ("g1", "g3")
    refused(SP.groups_under_loro, SP.LoroSplitSets({"nope": "r"}, (), ()), ("g1",), match="not in the data")
    refused(SP.groups_under_loro, SP.LoroSplitSets({"g1": "r"}, (), ()), ("g1",), match="every group")
    refused(SP.groups_under_loro, SP.LoroSplitSets({}, (), ()), ("g1", "g1"), match="more than once")


def test_report_groupings():
    groups = ("a", "b", "c", "d")
    none = SP.LoroSplitSets({}, (), ())
    assert SP.report_groupings(groups, none) == {"all": groups}
    both = SP.LoroSplitSets({}, ("c", "a"), ("d", "b"))
    out = SP.report_groupings(groups, both)
    assert out == {"all": groups, "without_seen_during_design": ("b", "d"), "continuity": ("b", "d")}
    refused(SP.report_groupings, groups, SP.LoroSplitSets({}, ("x",), ()), match="not among the groups")


# ---------------------------------------------------------------------------------------------------
# R18: candidates, stride, evenly spaced subset
def test_candidate_units_read_validity_at_or_before_the_train_end_only():
    unit = np.array(["g_1", "g_1", "g_2", "g_3", "g_4", "h_1"], dtype=object)
    group = np.array(["g", "g", "g", "g", "g", "h"], dtype=object)
    step = np.array([5, 11, 10, 11, 3, 1])
    valid = np.array([False, True, True, True, False, True])
    # g_1 is valid only after the cut, g_3 only after it, g_4 never; h_1 is another group
    assert SP.candidate_units(unit, group, step, valid, "g", 10) == ("g_2",)
    assert SP.candidate_units(unit, group, step, valid, "g", 11) == ("g_1", "g_2", "g_3")
    refused(SP.candidate_units, unit, group, step, valid, "g", 4, match="no unit with a valid label")
    refused(SP.candidate_units, unit, group, step, valid.astype(int), "g", 10, match="boolean")
    refused(SP.candidate_units, unit, group, step.astype(float), valid, "g", 10, match="integer")
    refused(SP.candidate_units, unit, group[:3], step, valid, "g", 10)


def shipped_cells_for(ids, n):
    """pm25_architecture.py:101-108 as shipped: c = sorted ids; all if len(c) <= n; else
    c[::max(1, len(c) // n)][:n]."""
    c = sorted(ids)
    return c if len(c) <= n else c[::max(1, len(c) // n)][:n]


@pytest.mark.parametrize("n_units,count", [(1, 100), (100, 100), (101, 100), (199, 100), (250, 100),
                                           (19600, 100), (15051, 100), (4285, 4285), (9999, 4285)])
def test_stride_pick_is_the_shipped_formula(n_units, count):
    ids = tuple(sorted("grp_%d_%d" % (i % 97, i) for i in range(n_units)))
    got = SP.stride_pick(ids, count)
    assert list(got) == shipped_cells_for(ids, count)
    assert len(got) == min(n_units, count) and list(got) == sorted(got)


def test_stride_pick_refusals():
    refused(SP.stride_pick, ("b", "a"), 1, match="not sorted")
    refused(SP.stride_pick, ("a", "a"), 1, match="repeats")
    refused(SP.stride_pick, ("a",), 0)
    refused(SP.stride_pick, ("a",), True)
    refused(SP.stride_pick, ("a",), 1.0)


@pytest.mark.parametrize("n,m", [(100, 15), (100, 50), (100, 1), (100, 2), (100, 99), (100, 100),
                                 (4285, 2040), (2543, 2040), (7, 3), (5, 9)])
def test_evenly_spaced_subset_positions(n, m):
    units = tuple("u%05d" % i for i in range(n))
    got = SP.evenly_spaced_subset(units, m)
    if m >= n:
        assert got == units
    elif m == 1:
        assert got == (units[0],)
    else:
        want = [units[(i * (n - 1)) // (m - 1)] for i in range(m)]
        assert list(got) == want
        assert got[0] == units[0] and got[-1] == units[-1]      # spans the whole list
        assert len(set(got)) == m
    assert list(got) == sorted(got)


def test_evenly_spaced_reaches_the_tail_where_the_stride_does_not():
    units = tuple("u%03d" % i for i in range(100))
    assert SP.evenly_spaced_subset(units, 15)[-1] == "u099"
    assert SP.stride_pick(units, 15)[-1] == "u084"         # s = 100 // 15 = 6: stops at 84


def test_evenly_spaced_subset_refusals():
    refused(SP.evenly_spaced_subset, (), 1, match="no unit")
    refused(SP.evenly_spaced_subset, ("b", "a"), 1)
    refused(SP.evenly_spaced_subset, ("a",), 0)


# ---------------------------------------------------------------------------------------------------
# C16 budget and the two lists
@pytest.mark.parametrize("n,groups,per_group,total", [(100, 127, 15, 1905), (100, 40, 50, 2000),
                                                      (4285, 42, 2040, 85680), (100, 133, 15, 1995)])
def test_scored_count_budget_at_k_20_gives_the_ruled_counts(n, groups, per_group, total):
    banks = {"g%03d" % i: n for i in range(groups)}
    counts, flags = SP.scored_count_budget(n, banks, K.K_GROUP_EQUIVALENTS)
    assert set(counts.values()) == {per_group}
    assert sum(counts.values()) == total
    assert flags == ()


def test_scored_count_budget_caps_at_the_bank_and_flags_the_minimum():
    # defo's four small groups keep all their cells as bank units but are still above 2,040
    banks = {"g%02d" % i: 4285 for i in range(38)}
    banks.update({"costa_rica": 2543, "pearl_river_delta": 2734, "tongass_alaska": 3938,
                  "tasmania_western": 4016})
    counts, flags = SP.scored_count_budget(4285, banks, 20)
    assert set(counts.values()) == {2040} and flags == ()
    capped, flags = SP.scored_count_budget(100, {"a": 100, "b": 7}, 1)     # max(10, 100 // 2) = 50
    assert capped == {"a": 50, "b": 7} and flags == ("scored_capped:b",)
    small, flags = SP.scored_count_budget(100, {"g%03d" % i: 100 for i in range(300)}, 20)
    assert set(small.values()) == {10}                     # floor(2,000 / 300) = 6 < 10
    assert len(flags) == 300 and all(f.startswith("minimum:") for f in flags)
    refused(SP.scored_count_budget, 100, {}, 20)
    refused(SP.scored_count_budget, 0, {"a": 1}, 20)
    refused(SP.scored_count_budget, 100, {"a": 1}, 0)
    refused(SP.scored_count_budget, 100, {"a": 0}, 20)


def unit_ids(group, n):
    return tuple(sorted("%s_%d_%d" % (group, i, -i) for i in range(n)))


def test_pick_unit_lists_bank_by_stride_scored_as_a_subset():
    cands = {"a": unit_ids("a", 250), "b": unit_ids("b", 80), "c": unit_ids("c", 100)}
    counts = SP.UnitCounts(rule_value=100, k_group_equivalents=20, n_groups=3,
                           bank_by_group={"a": 100, "b": 80, "c": 100},
                           scored_by_group={"a": 15, "b": 15, "c": 100})
    lists = SP.pick_unit_lists(("c", "a", "b"), cands, counts)
    assert list(lists.bank) == ["a", "b", "c"]
    assert lists.bank["a"] == SP.stride_pick(cands["a"], 100)
    assert lists.bank["b"] == cands["b"]
    for g in "abc":
        assert set(lists.scored[g]) <= set(lists.bank[g])
        assert lists.scored[g] == SP.evenly_spaced_subset(lists.bank[g], counts.scored_by_group[g])
    assert lists.scored["c"] == lists.bank["c"]
    SP.check_scored_units_loro(dict(lists.scored), lists)


def test_pick_unit_lists_refusals():
    cands = {"a": unit_ids("a", 50), "b": unit_ids("b", 50)}

    def counts(bank, scored):
        return SP.UnitCounts(100, 20, 2, bank, scored)

    refused(SP.pick_unit_lists, ("a", "b"), cands, counts({"a": 50}, {"a": 5, "b": 5}), match="no entry")
    refused(SP.pick_unit_lists, ("a",), cands, counts({"a": 50, "b": 50}, {"a": 5}), match="not listed")
    refused(SP.pick_unit_lists, ("a", "b"), cands, counts({"a": 51, "b": 50}, {"a": 5, "b": 5}),
            match="above its 50 candidates")
    refused(SP.pick_unit_lists, ("a", "b"), cands, counts({"a": 20, "b": 50}, {"a": 21, "b": 5}),
            match="above its bank count")
    refused(SP.pick_unit_lists, ("a",), {}, counts({"a": 1}, {"a": 1}), match="no entry")
    shared = {"a": ("x_1",), "b": ("x_1",)}
    err = refused(SP.pick_unit_lists, ("a", "b"), shared, counts({"a": 1, "b": 1}, {"a": 1, "b": 1}))
    assert err.rule == "G-DISJOINT"


def test_check_scored_units_loro_refuses_every_difference():
    lists = SP.UnitLists(bank={"a": ("a1", "a2", "a3"), "b": ("b1", "b2")},
                         scored={"a": ("a1", "a3"), "b": ("b2",)})
    SP.check_scored_units_loro({"a": ("a3", "a1"), "b": ("b2",)}, lists)
    refused(SP.check_scored_units_loro, {"a": ("a1", "a3")}, lists, match="no scored unit of 'b'")
    refused(SP.check_scored_units_loro, {"a": ("a1", "a3"), "b": ("b2",), "c": ("c1",)}, lists,
            match="outside the unit lists")
    refused(SP.check_scored_units_loro, {"a": ("a1", "a2"), "b": ("b2",)}, lists, match="missing 'a3'")
    outside = SP.UnitLists(bank={"a": ("a1",)}, scored={"a": ("a1", "a9")})
    refused(SP.check_scored_units_loro, {"a": ("a1", "a9")}, outside, match="outside its bank list")


# ---------------------------------------------------------------------------------------------------
# group manifests (G-DISJOINT)
def manifest(group, units, cut=100, max_t=100, groups=None, held=()):
    distinct = sorted(set(units))
    return BankManifest(bank_fingerprint="f", groups=groups or (group,), unit_ids_hash=_hash_strings(distinct),
                        n_units=len(distinct), min_label_time=0, max_label_time=max_t, cut=cut,
                        cut_kind="fit", lead=0, held_out_fold=held)


def test_unit_ids_hash_is_the_bank_manifest_formula():
    units = ("b_2", "a_1", "a_1", "c_3")
    assert SP.unit_ids_hash(units) == _hash_strings(sorted(set(units)))


def test_assert_group_manifests():
    lists = SP.UnitLists(bank={"a": ("a1", "a2"), "b": ("b1",)}, scored={"a": ("a1",), "b": ("b1",)})
    good = {"a": manifest("a", ("a2", "a1")), "b": manifest("b", ("b1",))}
    SP.assert_group_manifests(good, lists, 100)
    refused(SP.assert_group_manifests, {"a": good["a"]}, lists, 100, match="no tree manifest")
    refused(SP.assert_group_manifests, dict(good, c=manifest("c", ("c1",))), lists, 100, match="outside")
    refused(SP.assert_group_manifests, dict(good, a=manifest("a", ("a1", "a2"), groups=("a", "b"))),
            lists, 100, match="saw groups")
    refused(SP.assert_group_manifests, dict(good, a=manifest("a", ("a1", "a3"))), lists, 100,
            match="not its 2 bank units")
    refused(SP.assert_group_manifests, dict(good, a=manifest("a", ("a1", "a2"), max_t=101)), lists, 100,
            match="after the cut")
    refused(SP.assert_group_manifests, good, lists, 99, match="records cut 100")
    refused(SP.assert_group_manifests, dict(good, a=manifest("a", ("a1", "a2"), held=("b",))), lists, 100,
            match="fold bank")
    refused(SP.assert_group_manifests, {"a": object(), "b": good["b"]}, lists, 100, match="has no")


# ---------------------------------------------------------------------------------------------------
# the region router's fit cap (R14)
def test_region_cap_keeps_every_unit_when_they_fit():
    units = tuple("u%04d" % i for i in range(4285))
    rows = {u: 14 for u in units}                         # 59,990 rows: the inner surface, no cap
    assert SP.region_cap_units(units, rows, K.REGION_ROUTER_ROW_BUDGET) == units


def test_region_cap_keeps_evenly_spaced_whole_units_under_the_budget():
    units = tuple("u%04d" % i for i in range(4285))
    rows = {u: 17 for u in units}                         # the test pass: about 3,529 units
    kept = SP.region_cap_units(units, rows, K.REGION_ROUTER_ROW_BUDGET)
    assert len(kept) == 60000 // 17 == 3529
    assert sum(rows[u] for u in kept) <= 60000
    assert kept == SP.evenly_spaced_subset(units, 3529)
    assert kept[0] == units[0] and kept[-1] == units[-1]


def test_region_cap_takes_the_largest_feasible_m_even_when_not_monotone():
    units = ("a", "b", "c", "d", "e")
    # m = 4 keeps positions 0, 1, 2, 4 (rows 1 + 1 + 1 + 9 = 12); m = 3 keeps 0, 2, 4 (11); m = 2 keeps
    # 0, 4 (10); the budget 12 admits m = 4
    rows = {"a": 1, "b": 1, "c": 1, "d": 1, "e": 9}
    assert SP.region_cap_units(units, rows, 12) == ("a", "b", "c", "e")
    assert SP.region_cap_units(units, rows, 10) == ("a", "e")
    assert SP.region_cap_units(("a", "b", "c"), {"a": 5, "b": 5, "c": 5}, 5) == ("a",)   # m = 1: position 0


def test_region_cap_refusals():
    refused(SP.region_cap_units, ("a", "b"), {"a": 1}, 10, match="no fit-row count")
    refused(SP.region_cap_units, ("a",), {"a": 11}, 10, match="more fit rows than the whole budget")
    refused(SP.region_cap_units, ("b", "a"), {"a": 1, "b": 1}, 10)
    refused(SP.region_cap_units, ("a",), {"a": -1}, 10)
    refused(SP.region_cap_units, ("a",), {"a": 1}, 0)
    refused(SP.region_cap_units, (), {}, 10, match="no unit")


# ---------------------------------------------------------------------------------------------------
# overlap blocks (R14; L2 rule 4)
def grid_units():
    """Five groups on an integer grid. A and B share one cell; C touches B diagonally only; D and E are
    far apart; F touches nothing but sits two cells from E (not a neighbour)."""
    rows = []
    for x in range(3):
        for y in range(3):
            rows.append(("A", x, y))
    rows += [("B", 2, 2), ("B", 3, 3), ("B", 4, 4)]          # (2, 2) is also A's
    rows += [("C", 5, 5), ("C", 6, 6)]                       # (5, 5) touches B's (4, 4) diagonally
    rows += [("D", 20, 20), ("D", 21, 20)]
    rows += [("E", 40, 40)]
    rows += [("F", 42, 40), ("F", 43, 40)]
    g = np.array([r[0] for r in rows], dtype=object)
    ix = np.array([r[1] for r in rows], dtype=np.int64)
    iy = np.array([r[2] for r in rows], dtype=np.int64)
    lat = iy * 0.1
    lon = ix * 0.1
    return g, lat, lon, ix, iy


def test_overlap_blocks_on_grid_indices():
    g, lat, lon, ix, iy = grid_units()
    d = SP.derive_overlap_blocks(g, lat, lon, ix, iy)
    assert isinstance(d, Derived) and d.rule_id == "R14"
    blocks = d.value
    assert blocks.link_rule == SP.GRID_INDICES
    assert blocks.members == (("A", "B", "C"), ("D",), ("E",), ("F",))
    assert blocks.block_of_group == {"A": 0, "B": 0, "C": 0, "D": 1, "E": 2, "F": 3}
    # (group, group, units of the smaller group linked): A-B: B (3 units) is smaller; its (2, 2) and
    # (3, 3) touch A (2, 2 shared; 3, 3 is the diagonal neighbour of A's 2, 2). B-C: C (2 units) is
    # smaller; only (5, 5) touches B.
    assert blocks.linked_pairs == (("A", "B", 2), ("B", "C", 1))
    assert d.flags == ("overlap:A+B:2", "overlap:B+C:1")
    rec = {tuple(r["groups"]): r for r in d.inputs["linked_pairs"]}
    assert rec[("A", "B")]["shared_position_units"] == [1, 1] and not rec[("A", "B")]["only_touches"]
    assert rec[("B", "C")]["shared_position_units"] == [0, 0] and rec[("B", "C")]["only_touches"]
    assert d.inputs["n_blocks"] == 4 and d.inputs["units_by_group"]["A"] == 9
    assert {"grid_ix", "grid_iy", "unit_group"} <= set(d.input_hashes)
    derived_entry(d)                                          # writable to derived.json
    assert SP.block_of_group(blocks, "C") == ("A", "B", "C")
    assert SP.block_of_group(blocks, "D") == ("D",)
    refused(SP.block_of_group, blocks, "Z", match="in no overlap block")


def test_overlap_blocks_do_not_depend_on_row_order():
    g, lat, lon, ix, iy = grid_units()
    order = np.random.RandomState(3).permutation(len(g))      # test-side shuffle only
    a = SP.derive_overlap_blocks(g, lat, lon, ix, iy).value
    b = SP.derive_overlap_blocks(g[order], lat[order], lon[order], ix[order], iy[order]).value
    assert a == b
    SP.assert_blocks_equal(a, b)


def test_overlap_blocks_chain_into_one_component():
    g = np.array(["p", "q", "r", "s"], dtype=object)
    ix = np.array([0, 1, 2, 10])
    iy = np.array([0, 1, 2, 10])
    d = SP.derive_overlap_blocks(g, np.zeros(4), np.zeros(4), ix, iy)
    assert d.value.members == (("p", "q", "r"), ("s",))      # p-q and q-r link p to r through q


def test_overlap_blocks_spacing_rule_without_grid_indices():
    # a regular lattice near the equator, 0.1 degree apart; X and Y interleave along one row edge, W is
    # far away, V touches Y only diagonally (distance sqrt(2) x spacing)
    pts = []
    for i in range(5):
        for j in range(5):
            pts.append(("X", 0.1 * i, 0.1 * j))
    for i in range(5, 8):
        for j in range(5):
            pts.append(("Y", 0.1 * i, 0.1 * j))
    pts += [("W", 30.0 + 0.1 * i, 30.0) for i in range(4)]
    g = np.array([p[0] for p in pts], dtype=object)
    lat = np.array([p[1] for p in pts])
    lon = np.array([p[2] for p in pts])
    d = SP.derive_overlap_blocks(g, lat, lon, None, None)
    assert d.value.link_rule == SP.SPACING
    assert d.value.members == (("W",), ("X", "Y"))
    assert set(d.inputs["spacing_radians"]) == {"W", "X", "Y"}
    assert all(v > 0 for v in d.inputs["spacing_radians"].values())
    rec = d.inputs["linked_pairs"][0]
    assert rec["groups"] == ["X", "Y"] and rec["only_touches"]
    # a shared location links whatever the spacing
    g2 = np.concatenate([g, np.array(["W"], dtype=object)])
    lat2 = np.concatenate([lat, [0.0]])
    lon2 = np.concatenate([lon, [0.0]])
    d2 = SP.derive_overlap_blocks(g2, lat2, lon2, None, None)
    assert d2.value.members == (("W", "X", "Y"),)


def test_overlap_block_refusals():
    g, lat, lon, ix, iy = grid_units()
    refused(SP.derive_overlap_blocks, g[:3], lat, lon, ix, iy, match="shape")
    refused(SP.derive_overlap_blocks, g, lat, lon, ix, None, match="both or neither")
    refused(SP.derive_overlap_blocks, g, lat, lon, ix.astype(float), iy, match="integer grid indices")
    refused(SP.derive_overlap_blocks, g, np.where(lat > 0, 91.0, lat), lon, ix, iy, match="[-90, 90]")
    refused(SP.derive_overlap_blocks, g, lat * np.nan, lon, ix, iy, match="not finite")
    refused(SP.derive_overlap_blocks, np.array([], dtype=object), [], [], None, None, match="non-empty")
    bad = g.copy()
    bad[0] = ""
    refused(SP.derive_overlap_blocks, bad, lat, lon, ix, iy, match="not group names")
    # the spacing rule needs two units per group
    refused(SP.derive_overlap_blocks, g, lat, lon, None, None, match="group 'E' has 1 unit")


def test_assert_blocks_equal_refuses_a_changed_static_table():
    g, lat, lon, ix, iy = grid_units()
    a = SP.derive_overlap_blocks(g, lat, lon, ix, iy).value
    moved = ix.copy()
    moved[g == "C"] += 5                                      # C no longer touches B
    b = SP.derive_overlap_blocks(g, lat, lon, moved, iy).value
    err = refused(SP.assert_blocks_equal, a, b, match="differ from derived.json")
    assert err.rule == "G-DISJOINT" and "'C'" in str(err)


# ---------------------------------------------------------------------------------------------------
# rival folds (C17)
def blocks_of(*members):
    members = tuple(tuple(sorted(m)) for m in members)
    members = tuple(sorted(members))
    return SP.OverlapBlocks(block_of_group={g: i for i, m in enumerate(members) for g in m},
                            members=members, linked_pairs=(), link_rule=SP.GRID_INDICES)


def test_rival_folds_are_round_robin_over_sorted_blocks():
    names = ["g%02d" % i for i in range(23)]
    blocks = blocks_of(*[(n,) for n in names if n not in ("g03", "g04")], ("g03", "g04"))
    folds = SP.rival_fold_of_group(blocks, K.RIVAL_FOLDS)
    assert folds["g03"] == folds["g04"] == 3                   # a block stays in one fold
    assert folds["g05"] == 4                                   # the next block takes the next fold
    assert folds["g00"] == 0 and folds["g10"] == 9 and folds["g11"] == 0
    assert sorted(set(folds.values())) == list(range(10))
    train = SP.rival_fold_training_groups(folds, 3)
    assert "g03" not in train and "g04" not in train and len(train) == 23 - 3   # g03, g04, g13 in fold 3
    refused(SP.rival_fold_training_groups, folds, 10, match="not one of the folds")
    refused(SP.rival_fold_of_group, blocks, 1)
    refused(SP.rival_fold_of_group, blocks_of(("a",), ("b",)), 10, match="[2, 2]")
    refused(SP.rival_fold_training_groups, {"a": 0}, 0, match="holds every group")


def test_one_group_blocks_give_round_robin_over_names():
    names = ["b", "a", "d", "c"]
    folds = SP.rival_fold_of_group(blocks_of(*[(n,) for n in names]), 2)
    assert folds == {"a": 0, "b": 1, "c": 0, "d": 1}


def test_assert_rival_source():
    folds = {"a": 0, "b": 1, "c": 0}
    SP.assert_rival_source(np.array(["a", "b", "c", "a"], dtype=object), np.array([0, 1, 0, 0]), folds)
    refused(SP.assert_rival_source, np.array(["a", "b"], dtype=object), np.array([0, 0]), folds,
            match="1 rows came from another fold's model")
    refused(SP.assert_rival_source, np.array(["z"], dtype=object), np.array([0]), folds, match="without a rival fold")
    refused(SP.assert_rival_source, np.array(["a"], dtype=object), np.array([0, 1]), folds)
    refused(SP.assert_rival_source, np.array(["a"], dtype=object), np.array([0.0]), folds, match="integer")


# ---------------------------------------------------------------------------------------------------
# one real store, read-only (defo's target unit ids '{group}_{ix}_{iy}', plan 1.2)
DEFO_TARGET = Path("D:/defo_target")


def test_defo_overlap_blocks_on_the_real_unit_ids():
    """The LORO review predicted 2 linked pairs among defo's groups by name. The engine rule, run on
    every unit id of D:/defo_target (grid indices parsed from the ids test-side; the package's static
    table with grid_ix / grid_iy is not built yet), finds exactly those two, each sharing cells."""
    pq = pytest.importorskip("pyarrow.parquet")
    files = sorted(DEFO_TARGET.glob("*.parquet")) if DEFO_TARGET.is_dir() else []
    if len(files) != 42:
        pytest.skip("D:/defo_target is not on this machine")
    groups, ix, iy = [], [], []
    for f in files:
        ids = np.unique(pq.read_table(str(f), columns=["cell_id"]).column("cell_id").to_numpy(zero_copy_only=False))
        for u in ids.tolist():
            a, b = u[len(f.stem) + 1:].split("_")
            groups.append(f.stem)
            ix.append(int(a))
            iy.append(int(b))
    n = len(groups)
    d = SP.derive_overlap_blocks(np.array(groups, dtype=object), np.zeros(n), np.zeros(n),
                                 np.array(ix), np.array(iy))
    multi = [m for m in d.value.members if len(m) > 1]
    assert multi == [("andes_puna", "bolivia_beni_savanna"), ("angola_zambia_fire_belt", "miombo_woodland_zambia")]
    assert len(d.value.members) == 40
    shared = {tuple(r["groups"]): r["shared_position_units"][0] for r in d.inputs["linked_pairs"]}
    assert shared == {("andes_puna", "bolivia_beni_savanna"): 1, ("angola_zambia_fire_belt", "miombo_woodland_zambia"): 29}
