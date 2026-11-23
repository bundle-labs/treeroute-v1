"""R19 whole-bank recipe: per-group specialists with name seeds, ownership for leave-one-group-out
routers (owner rulings part D), the held-out share check (D51), determinism and donor-order
invariance, the manifest (G-DISJOINT) and the refusals (G-FITCUT, G-DONOR)."""

import os
from dataclasses import dataclass, replace
from typing import Any, Optional, Tuple

import numpy as np
import pytest

from treeroute import engine_constants as K
from treeroute.fit import bank as B
from treeroute.fit import correctors as C
from treeroute.fit.bank import BankRefusal, SeedRole

T = K.SMOKE_TREES_PER_DONOR   # 12; the bank takes only the engine or the smoke constant


@pytest.fixture(scope="module", autouse=True)
def _keep_environment():
    """scikit-learn sets KMP_* variables when it is first imported (sklearn/__init__.py). Later tests
    start the launcher in a fresh interpreter, which refuses them, so this module puts the
    environment back as it found it."""
    before = dict(os.environ)
    yield
    for key in set(os.environ) - set(before):
        del os.environ[key]
    for key, value in before.items():
        if os.environ.get(key) != value:
            os.environ[key] = value


@dataclass(frozen=True)
class Rows:
    """A test double with the approved DonorRows fields (FitContext does not exist yet)."""
    groups: Tuple[str, ...]
    cut: int
    cut_kind: Any
    lead: int
    fold: Optional[int]
    unit_ids: np.ndarray
    times: np.ndarray
    group_of_row: np.ndarray
    grid_rows: np.ndarray
    y: np.ndarray
    X: np.ndarray
    row_key_hash: str


@dataclass(frozen=True)
class FoldRows(Rows):
    held_out_groups: Tuple[str, ...] = ()


SIZES = {"grp_b": 160, "grp_a": 220, "grp_c": 140, "grp_small": 60}
P = 15


def _group_block(name, n):
    """Deterministic synthetic rows for one group: 5 units x (n / 5) steps."""
    seed = sum(ord(c) for c in name)          # synthetic data only
    rng = np.random.RandomState(seed)
    X = rng.normal(size=(n, P)).astype(np.float32)
    y = (X[:, 0] * 3.0 + X[:, 1] ** 2 + 0.2 * rng.normal(size=n) + len(name)).astype(np.float64)
    per = n // 5
    units = np.array(["%s_u%d" % (name, i // per) for i in range(n)], dtype=object)
    times = np.tile(np.arange(per, dtype=np.int64), 5)
    return X, y, units, times


def make_rows(order=("grp_a", "grp_b", "grp_c", "grp_small"), groups=None, cls=Rows, **extra):
    blocks = [(g,) + _group_block(g, SIZES[g]) for g in order]
    X = np.vstack([b[1] for b in blocks])
    y = np.concatenate([b[2] for b in blocks])
    units = np.concatenate([b[3] for b in blocks])
    times = np.concatenate([b[4] for b in blocks])
    gor = np.concatenate([np.array([b[0]] * len(b[1]), dtype=object) for b in blocks])
    listed = tuple(order) if groups is None else groups
    return cls(groups=listed, cut=100, cut_kind="fit", lead=0, fold=extra.pop("fold", None),
               unit_ids=units, times=times, group_of_row=gor, grid_rows=np.arange(len(y)),
               y=y, X=X, row_key_hash="synthetic", **extra)


@pytest.fixture(scope="module")
def bank():
    return B.fit_donor_bank(make_rows(), T)


def _per_group_fingerprints(bank):
    out = {}
    for i, g in enumerate(bank.tree_group):
        out.setdefault(g, []).append((bank.tree_number[i], B.tree_fingerprint(bank.trees[i]),
                                      B.tree_fingerprint(bank.correctors[i]),
                                      B.tree_fingerprint(bank.placebo_correctors[i])))
    return out


# ---------------------------------------------------------------------------------------------------
def test_every_group_trains_its_own_trees_in_sorted_order(bank):
    groups = sorted(SIZES)
    assert bank.tree_group == tuple(g for g in groups for _ in range(T))
    assert bank.tree_number == tuple(j for _ in groups for j in range(T))
    assert len(bank.trees) == len(bank.correctors) == len(bank.placebo_correctors) == 4 * T
    assert bank.manifest.groups == tuple(groups)


def test_each_tree_is_the_primitive_on_its_group_rows_with_name_seeds():
    rows = make_rows()
    bank = B.fit_donor_bank(rows, T)
    gstr = rows.group_of_row.astype(str)
    for i in (0, 5, T + 3, 3 * T + 11):
        g, j = bank.tree_group[i], bank.tree_number[i]
        gi = np.flatnonzero(gstr == g)
        bag = B.draw_bag(len(gi), B.name_seed(g, j, SeedRole.BAG))
        tree = B.fit_one_tree(rows.X, rows.y, gi[bag], B.name_seed(g, j, SeedRole.TREE))
        assert B.tree_fingerprint(tree) == B.tree_fingerprint(bank.trees[i])
        ob = B.oob_rows(gi, gi[bag])
        corr = C.fit_corrector(tree, rows.X, rows.y, ob, B.name_seed(g, j, SeedRole.CORRECTOR))
        plac = C.fit_placebo_corrector(tree, rows.X, rows.y, ob,
                                       B.name_seed(g, j, SeedRole.CORRECTOR))
        assert B.tree_fingerprint(corr) == B.tree_fingerprint(bank.correctors[i])
        assert B.tree_fingerprint(plac) == B.tree_fingerprint(bank.placebo_correctors[i])
        assert bank.trees[i].get_params()["random_state"] == B.name_seed(g, j, SeedRole.TREE)


def test_small_group_trees_skip_correctors_d52(bank):
    # 60 rows -> bag 30 -> about 36 out-of-bag rows, under the 50-row minimum
    small = [i for i, g in enumerate(bank.tree_group) if g == "grp_small"]
    assert all(bank.correctors[i] is None and bank.placebo_correctors[i] is None for i in small)
    big = [i for i, g in enumerate(bank.tree_group) if g == "grp_a"]
    assert all(bank.correctors[i] is not None and bank.placebo_correctors[i] is not None
               for i in big)


def test_ownership_lets_a_router_drop_its_own_group(bank):
    for g in sorted(SIZES):
        own = B.group_tree_columns(bank.tree_group, g)
        keep = B.columns_without_own_group(bank, g)
        assert len(own) == T and all(bank.tree_group[i] == g for i in own)
        assert all(bank.tree_group[i] != g for i in keep)
        assert sorted(np.concatenate([own, keep]).tolist()) == list(range(len(bank.trees)))
        assert np.all(np.diff(keep) > 0) and keep.dtype == np.int64
        assert np.array_equal(keep, B.columns_excluding_group(bank.tree_group, g))


@pytest.mark.parametrize("wrong", ["GRP_A", "grp_a ", " Grp_A", "grp_aa", "gpr_a", "grp_elsewhere",
                                   "grp_a_u0", b"grp_a", 3, None, ""])
def test_the_router_mask_refuses_a_group_that_owns_no_tree(bank, wrong):
    """Fail-closed: a misspelled, re-cased, wrong-typed or unknown group would drop nothing."""
    with pytest.raises(BankRefusal) as info:
        B.columns_without_own_group(bank, wrong)
    assert "[G-DISJOINT]" in str(info.value)


def test_the_router_mask_names_the_near_miss():
    rows = make_rows(order=("grp_a", "grp_c"))
    bank = B.fit_donor_bank(rows, T)
    with pytest.raises(BankRefusal) as info:
        B.columns_without_own_group(bank, "GRP_A")
    assert "did you mean 'grp_a'" in str(info.value)


def test_the_router_mask_allows_only_a_group_the_manifest_names_held_out(bank):
    held = replace(bank, manifest=replace(bank.manifest, held_out_fold=("grp_elsewhere",)))
    assert np.array_equal(B.columns_without_own_group(held, "grp_elsewhere"),
                          np.arange(len(bank.trees)))
    with pytest.raises(BankRefusal):
        B.columns_without_own_group(held, "grp_elsewher")               # still a typo
    with pytest.raises(BankRefusal):
        B.columns_without_own_group(bank.tree_group, "grp_a")            # not a Bank: no manifest


def test_the_router_mask_refuses_an_empty_result():
    one = B.fit_donor_bank(make_rows(order=("grp_a",)), T)
    with pytest.raises(BankRefusal) as info:
        B.columns_without_own_group(one, "grp_a")
    assert "no tree column" in str(info.value)


def test_column_arithmetic_refuses_wrong_types_and_case_variants(bank):
    """group_tree_columns / columns_excluding_group are arithmetic (the store's tests mirror them): an
    unknown group gets no own column / every column, but a wrong type or a case or spacing variant
    of an owner's name is refused."""
    assert len(B.columns_excluding_group(bank.tree_group, "grp_elsewhere")) == len(bank.trees)
    assert len(B.group_tree_columns(bank.tree_group, "grp_elsewhere")) == 0
    for fn in (B.columns_excluding_group, B.group_tree_columns):
        for wrong in ("GRP_A", "grp_a ", b"grp_a", 3, None, ""):
            with pytest.raises(BankRefusal):
                fn(bank.tree_group, wrong)
        with pytest.raises(BankRefusal):
            fn((), "grp_a")
        with pytest.raises(BankRefusal):
            fn(("grp_a", b"grp_b"), "grp_a")


def test_oob_shares_are_per_group_and_near_the_expected_share(bank):
    assert set(bank.oob_share) == set(SIZES)
    for g, n in SIZES.items():
        exp = B.expected_oob_share(n, B.bag_size(n))
        assert abs(bank.oob_share[g] - exp) <= B.oob_share_tolerance(exp, n)


def test_oob_taken_against_all_groups_is_caught(monkeypatch):
    """Planted fault: the old bug (out-of-bag rows over ALL groups) must be refused by D51."""
    real = B.oob_rows
    all_rows = np.arange(sum(SIZES.values()))

    def all_groups_oob(home_rows, bag_rows):
        return real(all_rows, bag_rows)

    monkeypatch.setattr(B, "oob_rows", all_groups_oob)
    with pytest.raises(BankRefusal) as info:
        B.fit_donor_bank(make_rows(), T)
    assert "held-out share outside the expected band" in str(info.value)


# ---------------------------------------------------------------------------------------------------
def test_same_inputs_give_the_same_bytes(bank):
    again = B.fit_donor_bank(make_rows(), T)
    assert again.manifest.bank_fingerprint == bank.manifest.bank_fingerprint
    X = make_rows().X
    for a, b in zip(bank.trees + tuple(c for c in bank.correctors if c is not None),
                    again.trees + tuple(c for c in again.correctors if c is not None)):
        assert a.predict(X).tobytes() == b.predict(X).tobytes()
    assert again.oob_share == bank.oob_share


def test_donor_order_does_not_change_any_groups_trees(bank):
    # other groups' blocks sit elsewhere in the grid and the groups are listed in another order; each
    # group's own rows keep their grid order
    shuffled = make_rows(order=("grp_small", "grp_c", "grp_a", "grp_b"),
                         groups=("grp_c", "grp_b", "grp_small", "grp_a"))
    other = B.fit_donor_bank(shuffled, T)
    assert other.tree_group == bank.tree_group            # sorted by name, whatever the input order
    assert _per_group_fingerprints(other) == _per_group_fingerprints(bank)
    assert other.manifest.bank_fingerprint == bank.manifest.bank_fingerprint


def test_adding_or_removing_a_group_changes_no_other_groups_trees(bank):
    fewer = B.fit_donor_bank(make_rows(order=("grp_c", "grp_a")), T)
    ref = _per_group_fingerprints(bank)
    got = _per_group_fingerprints(fewer)
    assert set(got) == {"grp_a", "grp_c"}
    for g in got:
        assert got[g] == ref[g]
    assert fewer.oob_share["grp_a"] == bank.oob_share["grp_a"]


# ---------------------------------------------------------------------------------------------------
def test_manifest_records_groups_units_label_times_and_cut(bank):
    m = bank.manifest
    rows = make_rows()
    assert m.n_units == 4 * 5
    assert m.min_label_time == 0 and m.max_label_time == max(n // 5 for n in SIZES.values()) - 1
    assert (m.cut, m.cut_kind, m.lead, m.held_out_fold) == (100, "fit", 0, ())
    assert len(m.unit_ids_hash) == 64 and len(m.bank_fingerprint) == 64
    assert m.unit_ids_hash == B._hash_strings(sorted(set(rows.unit_ids.tolist())))


def test_fold_donor_rows_are_refused_no_fold_bank():
    """Leave one group out fits no fold bank (plan R13); a field outside the approved DonorRows is
    never read, so held_out_groups does not unlock it either."""
    with pytest.raises(BankRefusal) as info:
        B.fit_donor_bank(make_rows(order=("grp_a", "grp_c"), fold=1), T)
    assert "[G-DISJOINT]" in str(info.value) and "no fold bank" in str(info.value)
    assert "OWNER DECISION" in str(info.value)
    with pytest.raises(BankRefusal):
        B.fit_donor_bank(make_rows(order=("grp_a", "grp_c"), cls=FoldRows, fold=1,
                                   held_out_groups=("grp_b",)), T)
    with pytest.raises(BankRefusal):
        B.fit_donor_bank(make_rows(order=("grp_a", "grp_c"), fold=0), T)
    ok = B.fit_donor_bank(make_rows(order=("grp_a", "grp_c"), cls=FoldRows,
                                    held_out_groups=("grp_b",)), T)
    assert ok.manifest.held_out_fold == ()


# ---------------------------------------------------------------------------------------------------
def _time_major_inside(rows, group):
    """The same rows and values, with one group's rows reordered time-major (step, then unit) and
    their grid_rows carried along, as a FitContext bug would hand them over."""
    gi = np.flatnonzero(rows.group_of_row.astype(str) == group)
    inner = np.lexsort((rows.unit_ids[gi].astype(str), rows.times[gi]))
    order = np.arange(len(rows.y))
    order[gi] = gi[inner]
    return replace(rows, unit_ids=rows.unit_ids[order], times=rows.times[order],
                   group_of_row=rows.group_of_row[order], grid_rows=rows.grid_rows[order],
                   y=rows.y[order], X=rows.X[order])


def test_rows_inside_a_group_must_come_in_grid_order(bank):
    rows = make_rows()
    moved = _time_major_inside(rows, "grp_b")
    assert not np.array_equal(moved.X, rows.X)
    assert sorted(moved.grid_rows.tolist()) == rows.grid_rows.tolist()   # same rows, other order
    with pytest.raises(BankRefusal) as info:
        B.fit_donor_bank(moved, T)
    assert "[R19]" in str(info.value) and "ascending grid order" in str(info.value)
    # back in grid order, the bank is the same bank
    back = np.argsort(moved.grid_rows, kind="stable")
    again = B.fit_donor_bank(replace(moved, unit_ids=moved.unit_ids[back], times=moved.times[back],
                                     group_of_row=moved.group_of_row[back],
                                     grid_rows=moved.grid_rows[back], y=moved.y[back],
                                     X=moved.X[back]), T)
    assert again.manifest.bank_fingerprint == bank.manifest.bank_fingerprint


def test_grid_rows_must_be_strictly_ascending_integer_positions():
    rows = make_rows(order=("grp_a", "grp_c"))
    repeated = rows.grid_rows.copy()
    repeated[10] = repeated[9]                                           # a repeated grid row
    for bad in (repeated, rows.grid_rows[::-1].copy(), rows.grid_rows.astype(np.float64),
                rows.grid_rows[:-1], rows.grid_rows - 1, rows.grid_rows.astype(bool)):
        with pytest.raises(BankRefusal):
            B.fit_donor_bank(replace(rows, grid_rows=bad), T)
    gaps = replace(rows, grid_rows=rows.grid_rows * 7 + 3)               # gaps are fine
    assert (B.fit_donor_bank(gaps, T).manifest.bank_fingerprint
            == B.fit_donor_bank(rows, T).manifest.bank_fingerprint)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_missing_or_infinite_features_are_refused_naming_r30(value):
    rows = make_rows(order=("grp_a", "grp_c"))
    X = rows.X.copy()
    X[37, 4] = value
    X[300, 0] = value
    with pytest.raises(BankRefusal) as info:
        B.fit_donor_bank(replace(rows, X=X), T)
    msg = str(info.value)
    assert "[R30]" in msg and "2 donor rows" in msg and "row 37" in msg


def test_the_finiteness_scan_covers_every_block(monkeypatch):
    rows = make_rows(order=("grp_a", "grp_c"))
    X = rows.X.copy()
    X[-1, -1] = np.nan                                                   # the last value of the last block
    monkeypatch.setattr(B, "_FINITE_SCAN_VALUES", 7 * P)                 # 7-row blocks
    with pytest.raises(BankRefusal) as info:
        B.fit_donor_bank(replace(rows, X=X), T)
    assert "row %d" % (len(X) - 1) in str(info.value)


@pytest.mark.parametrize("count", [1, 5, 50, 99, 101, 300])
def test_only_the_engine_or_smoke_tree_count_is_accepted(count):
    with pytest.raises(BankRefusal) as info:
        B.fit_donor_bank(make_rows(order=("grp_a",)), count)
    assert "trees_per_donor" in str(info.value)


def test_refusals_on_the_donor_rows():
    rows = make_rows(order=("grp_a", "grp_c"))
    late = rows.times.copy()
    late[7] = 101
    with pytest.raises(BankRefusal) as info:
        B.fit_donor_bank(replace(rows, times=late), T)
    assert "[G-FITCUT]" in str(info.value)
    with pytest.raises(BankRefusal) as info:
        B.fit_donor_bank(replace(rows, groups=("grp_a",)), T)            # a row of an unlisted group
    assert "[G-DISJOINT]" in str(info.value)
    with pytest.raises(BankRefusal):
        B.fit_donor_bank(replace(rows, groups=("grp_a", "grp_c", "grp_z")), T)  # group without rows
    with pytest.raises(BankRefusal):
        B.fit_donor_bank(replace(rows, groups=("grp_a", "grp_a", "grp_c")), T)
    y_bad = rows.y.copy()
    y_bad[0] = np.nan
    with pytest.raises(BankRefusal):
        B.fit_donor_bank(replace(rows, y=y_bad), T)
    with pytest.raises(BankRefusal):
        B.fit_donor_bank(replace(rows, X=rows.X.astype(np.float64)), T)
    with pytest.raises(BankRefusal):
        B.fit_donor_bank(replace(rows, times=rows.times.astype(np.float64)), T)
    with pytest.raises(BankRefusal):
        B.fit_donor_bank(object(), T)                                    # not DonorRows at all


def test_bank_seeds_are_disclosed_by_the_seed_table(bank):
    table = B.seed_table(bank.tree_group, bank.tree_number)
    assert len(table) == len(bank.trees)
    for row, tree in zip(table, bank.trees):
        assert tree.get_params()["random_state"] == row["tree_seed"]
