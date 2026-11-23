"""R19 name seeds (D47), bag size and the bag draw (D48): pinned values, ranges and refusals."""

import hashlib

import numpy as np
import pytest

from treeroute import engine_constants as K
from treeroute.fit import bank as B
from treeroute.fit.bank import BankRefusal, SeedRole


def _reference(text):
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:4], "big")


# Pinned: a change of checksum, byte order, separator or role spelling changes these numbers.
PINNED = [
    ("grp_a", 0, SeedRole.BAG, 1274061588),
    ("grp_a", 0, SeedRole.TREE, 1451802336),
    ("grp_a", 0, SeedRole.CORRECTOR, 3013793711),
    ("grp_b", 11, SeedRole.TREE, 1988021371),
    ("x", 99, SeedRole.BAG, 2909670175),
]


@pytest.mark.parametrize("name,j,role,value", PINNED)
def test_name_seed_pinned_values(name, j, role, value):
    assert B.name_seed(name, j, role) == value
    assert B.name_seed(name, j, role) == _reference("%s|%d|%s" % (name, j, role.value))


def test_name_seed_is_d47_first_four_bytes_big_endian_and_in_range():
    for name in ("alpha", "beta_region", "grp with spaces", "été"):
        for j in (0, 1, 7, 99, 12345):
            for role in SeedRole:
                s = B.name_seed(name, j, role)
                digest = hashlib.sha256(("%s|%d|%s" % (name, j, role.value)).encode("utf-8")).digest()
                assert s == int.from_bytes(digest[:4], "big")
                assert 0 <= s <= B.SEED_MAX == 2 ** 32 - 1
                assert isinstance(s, int)


def test_name_seed_accepts_the_role_value_string_and_numpy_ints():
    assert B.name_seed("g", 3, "tree") == B.name_seed("g", 3, SeedRole.TREE)
    assert B.name_seed("g", np.int64(3), SeedRole.BAG) == B.name_seed("g", 3, SeedRole.BAG)


def test_name_seed_depends_on_name_and_number_only_and_roles_differ():
    seeds = {(g, j, r): B.name_seed(g, j, r) for g in ("a", "b", "c") for j in range(12)
             for r in SeedRole}
    assert len(set(seeds.values())) == len(seeds)  # no overlap between groups, trees or roles
    # position in any list plays no part: the same call gives the same number
    assert B.name_seed("b", 5, SeedRole.TREE) == seeds[("b", 5, SeedRole.TREE)]


@pytest.mark.parametrize("args", [
    ("", 0, SeedRole.BAG),
    (None, 0, SeedRole.BAG),
    ("g", -1, SeedRole.BAG),
    ("g", 1.0, SeedRole.BAG),
    ("g", True, SeedRole.BAG),
    ("g", 0, "placebo"),
    ("g", 0, 1),
])
def test_name_seed_refusals(args):
    with pytest.raises(BankRefusal) as info:
        B.name_seed(*args)
    assert "[R19]" in str(info.value)


def test_seed_role_members_are_the_three_approved_roles():
    assert {r.name: r.value for r in SeedRole} == {"BAG": "bag", "TREE": "tree",
                                                   "CORRECTOR": "corrector"}


# ---------------------------------------------------------------------------------------------------
def test_bag_size_is_max_min_rows_and_half_rounded_down():
    assert (K.BAG_MIN_ROWS, K.BAG_FRACTION) == (30, 0.5)
    for n, want in [(1, 30), (2, 30), (59, 30), (60, 30), (61, 30), (62, 31), (63, 31), (1001, 500),
                    (8640, 4320), (21601, 10800)]:
        assert B.bag_size(n) == want == max(30, n // 2)


@pytest.mark.parametrize("n", [0, -3, 2.5, True])
def test_bag_size_refuses(n):
    with pytest.raises(BankRefusal):
        B.bag_size(n)


def test_draw_bag_is_the_source_generator_with_replacement():
    for n, seed in [(1, 0), (10, 5), (61, 123), (500, B.SEED_MAX), (8640, 7000 + 3 * 17 + 4)]:
        got = B.draw_bag(n, seed)
        want = np.random.RandomState(seed).choice(n, size=B.bag_size(n), replace=True)
        assert got.dtype == np.int64 and got.shape == (B.bag_size(n),)
        assert np.array_equal(got, want)
        assert got.min() >= 0 and got.max() < n
    assert len(np.unique(B.draw_bag(500, 1))) < B.bag_size(500)  # with replacement: repeats occur


def test_draw_bag_same_seed_same_bytes():
    assert B.draw_bag(777, 42).tobytes() == B.draw_bag(777, 42).tobytes()
    assert B.draw_bag(777, 42).tobytes() != B.draw_bag(777, 43).tobytes()


@pytest.mark.parametrize("n,seed", [(0, 1), (10, -1), (10, 2 ** 32), (10, 1.5), (10, None),
                                    (10, lambda: 3)])
def test_draw_bag_refuses(n, seed):
    with pytest.raises(BankRefusal):
        B.draw_bag(n, seed)


def test_seed_table_discloses_every_tree():
    rows = B.seed_table(("a", "a", "b"), (0, 1, 0))
    assert [r["group"] for r in rows] == ["a", "a", "b"]
    assert rows[1] == {"group": "a", "tree_number": 1,
                       "bag_seed": B.name_seed("a", 1, SeedRole.BAG),
                       "tree_seed": B.name_seed("a", 1, SeedRole.TREE),
                       "corrector_seed": B.name_seed("a", 1, SeedRole.CORRECTOR)}
    with pytest.raises(BankRefusal):
        B.seed_table(("a",), (0, 1))
