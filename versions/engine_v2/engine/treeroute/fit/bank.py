"""The bank recipe (plan 2.3 R19): three name seeds per tree, the fit-one-tree primitive, and the
whole bank with its correctors, placebo correctors and per-tree group ownership.

SCIENCE bodies for the owner-approved signatures in treeroute/_proposed/bank_recipe.py (approved in
the owner rulings file, part A: every proposed default accepted; D51 ruled). Where the rulings file
differs from a docstring there, the rulings file wins.

One recipe for every package, all numbers from the engine constants (C13):
  - per group, TREES_PER_DONOR trees (the smoke run uses SMOKE_TREES_PER_DONOR, R21);
  - each tree fits a bag of max(BAG_MIN_ROWS, floor(BAG_FRACTION x n)) of the group's own n rows,
    drawn with replacement; depth TREE_MAX_DEPTH, min leaf TREE_MIN_LEAF, max_features
    TREE_MAX_FEATURES, criterion TREE_CRITERION, features in TREE_DTYPE;
  - three seeds per tree, each the first 4 bytes (big-endian) of SHA-256 of the UTF-8 string
    '<group name>|<tree number>|<role>' (D47): the bag draw, the tree's random_state, and its
    corrector's random_state (the placebo corrector uses the same seed as the real one).
Seeds depend on the group's NAME and the tree number only, never on list position. So adding or
removing a group changes no other group's trees, correctors or placebo correctors.

Leave one group out (owner rulings, part D): every group in the donor rows trains its own specialist
trees. The bank records which group owns each tree (Bank.tree_group). columns_without_own_group is
the FAIL-CLOSED column set a unit's router may use: every tree except its own group's, refusing a
group name that owns no tree in the bank. (group_tree_columns and columns_excluding_group are plain
column arithmetic, not a leak guard; see their docstrings.)

Row order: a group's bags index that group's rows in the order the donor rows hold them, so the bank
refuses donor rows that are not in ascending grid_rows order (the pool's grid order). Tree features
must be finite (0-filled, R30): the bank refuses a missing value rather than let the trees route it.

The primitives take no storage, sampler, layout, seed-formula or artefact argument (G-NOKNOB). The
fit-one-tree primitive takes a random_state VALUE, so the legacy harness can pass legacy seeds as
integers; no legacy seed formula lives in the engine.

The shared shapes (SeedRole, BankManifest, Bank) are FIELD-IDENTICAL copies of the approved shapes in
the proposed common module, which engine code may not import (G-IMPORT). DonorRows (the approved
container of the proposed fit_context module) is read by attribute until fit/context.py exists.
"""
# Provenance for the module: pm25_adaptation.py:619-651 (bank loop, bag take = max(30, int(0.5 * n)),
# DecisionTreeRegressor(max_depth=8, min_samples_leaf=5, max_features=MF, random_state=700 + j),
# legacy bag seed RandomState(7000 + e*17 + j)); adaptation.py:454-477 (correctors, placebo roll at
# :467, corrector seed j over the global tree list at :470, the old [0.15, 0.80] band at :474).

import hashlib
import math
from dataclasses import dataclass
from enum import Enum
from numbers import Integral, Real
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np

from treeroute.engine_constants import (BAG_FRACTION, BAG_MIN_ROWS, BAG_WITH_REPLACEMENT,
                                        SMOKE_TREES_PER_DONOR, TREE_CRITERION, TREE_DTYPE,
                                        TREE_MAX_DEPTH, TREE_MAX_FEATURES, TREE_MIN_LEAF,
                                        TREES_PER_DONOR)
from treeroute.errors import RefusedError

# The seed range numpy RandomState and scikit-learn's random_state accept: [0, 2^32 - 1].
SEED_MAX = (1 << 32) - 1

# D51 (owner rulings, part A): |observed - expected| <= 5 x sqrt(p (1 - p) / n), p the expected
# held-out share for the bag size and n the home group's row count.
# OWNER CONFIRMS: this number is not yet in engine_constants.py (outside this module's write scope);
# it belongs beside the C13 bank constants.
OOB_SHARE_TOLERANCE_SIGMAS = 5.0


class BankRefusal(RefusedError):
    """A bank rule refused (R19, G-FITCUT, G-DISJOINT). Nothing catches it to carry on."""


# ---------------------------------------------------------------------------------------------------
# Shapes (field-identical to the approved shared shapes)
class SeedRole(Enum):
    """R19: the three seeds of each tree."""
    BAG = "bag"
    TREE = "tree"
    CORRECTOR = "corrector"


@dataclass(frozen=True)
class BankManifest:
    """What every bank (fold banks included) carries for G-DISJOINT: the groups, units and label
    times it saw, and the cut it was fitted at."""
    bank_fingerprint: str
    groups: Tuple[str, ...]
    unit_ids_hash: str
    n_units: int
    min_label_time: int
    max_label_time: int
    cut: int
    cut_kind: Any                      # CutKind (FIT or GUARD), as the donor rows carry it
    lead: int
    held_out_fold: Tuple[str, ...]     # empty unless a fold bank


@dataclass(frozen=True)
class Bank:
    """A fitted bank. trees[i] belongs to group tree_group[i] with tree number tree_number[i];
    correctors[i] and placebo_correctors[i] are None when the tree had too few out-of-bag rows."""
    trees: Tuple[Any, ...]
    correctors: Tuple[Optional[Any], ...]
    placebo_correctors: Tuple[Optional[Any], ...]
    tree_group: Tuple[str, ...]
    tree_number: Tuple[int, ...]
    oob_share: Mapping[str, float]
    manifest: BankManifest


# ---------------------------------------------------------------------------------------------------
# Input checks shared by the primitives (every refusal names the rule and the fix)
def as_int_value(value: Any, what: str, low: int, high: Optional[int] = None) -> int:
    """An integer VALUE in [low, high]; a bool, a float or a callable is refused."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (Integral, np.integer)):
        raise BankRefusal("R19", "%s must be an integer value, got %s %r"
                          % (what, type(value).__name__, value),
                          fix="pass a plain integer (seed formulas never enter the engine)")
    out = int(value)
    if out < low or (high is not None and out > high):
        raise BankRefusal("R19", "%s = %d is outside [%d, %s]"
                          % (what, out, low, "inf" if high is None else high))
    return out


def check_features(X: Any) -> np.ndarray:
    """X must be a 2-D numpy array in the bank's feature dtype (float32, C13)."""
    if not isinstance(X, np.ndarray) or X.ndim != 2:
        raise BankRefusal("R19", "X must be a 2-D numpy array, got %s"
                          % (type(X).__name__ if not isinstance(X, np.ndarray) else
                             "%d-D" % X.ndim))
    if X.dtype != np.dtype(TREE_DTYPE):
        raise BankRefusal("R19", "X must be %s, got %s" % (TREE_DTYPE, X.dtype),
                          fix="cast the feature matrix once, where it is built (DonorRows.X)")
    return X


def check_target(y: Any, n_rows: int, what: str) -> np.ndarray:
    """A 1-D float64 array with one value per row of X."""
    if not isinstance(y, np.ndarray) or y.ndim != 1:
        raise BankRefusal("R19", "%s must be a 1-D numpy array" % what)
    if y.dtype != np.float64:
        raise BankRefusal("R19", "%s must be float64, got %s" % (what, y.dtype))
    if len(y) != n_rows:
        raise BankRefusal("R19", "%s has %d values for %d rows of X" % (what, len(y), n_rows))
    return y


def check_rows(row_indices: Any, n_rows: int, what: str) -> np.ndarray:
    """Non-empty 1-D integer row positions inside [0, n_rows), as int64 (values unchanged)."""
    rows = np.asarray(row_indices)
    if rows.ndim != 1:
        raise BankRefusal("R19", "%s must be 1-D, got %d-D" % (what, rows.ndim))
    if rows.size == 0:
        raise BankRefusal("R19", "%s is empty" % what)
    if rows.dtype == np.bool_ or not np.issubdtype(rows.dtype, np.integer):
        raise BankRefusal("R19", "%s must hold integer row positions, got %s" % (what, rows.dtype))
    low, high = int(rows.min()), int(rows.max())
    if low < 0 or high >= n_rows:
        raise BankRefusal("R19", "%s reaches row %d, outside [0, %d)"
                          % (what, low if low < 0 else high, n_rows))
    return rows.astype(np.int64, copy=False)


def _tree_class():
    # Imported at the first fit, so it loads after the launcher's pins (and under whatever patch
    # the launcher applied; scikit-learn-intelex does not replace this estimator).
    from sklearn.tree import DecisionTreeRegressor
    return DecisionTreeRegressor


# ---------------------------------------------------------------------------------------------------
# Provenance: plan 2.3 R19 ("a fixed checksum of (donor NAME, tree number, role)"); D47 (owner
# rulings, part A); replaces 7000 + e*17 + j, 700 + j and j over the global list
# (pm25_adaptation.py:641-646; adaptation.py:470).
def name_seed(donor_name: str, tree_number: int, role: SeedRole) -> int:
    """The fixed seed of one tree role, from the group's NAME and the tree number.

    Rule: R19, D47. The first 4 bytes, read big-endian, of SHA-256 of the UTF-8 string
    '<donor_name>|<tree_number>|<role value>' (tree number in decimal, role value 'bag', 'tree' or
    'corrector'). A pure checksum: it never depends on list position. Disclosed, never varied.

    Returns an integer in [0, 2^32 - 1]. Refuses an empty name, a negative tree number, or a role
    that is not BAG, TREE or CORRECTOR (a SeedRole member or its value string).
    """
    if not isinstance(donor_name, str) or donor_name == "":
        raise BankRefusal("R19", "a seed needs a non-empty group name, got %r" % (donor_name,))
    j = as_int_value(tree_number, "tree_number", 0)
    if isinstance(role, SeedRole):
        role_value = role.value
    elif isinstance(role, str) and role in {r.value for r in SeedRole}:
        role_value = role
    else:
        raise BankRefusal("R19", "seed role must be one of %s, got %r"
                          % ([r.value for r in SeedRole], role))
    digest = hashlib.sha256(("%s|%d|%s" % (donor_name, j, role_value)).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


# Provenance: pm25_adaptation.py:636 (take = max(30, int(0.5 * n))).
def bag_size(n_group_rows: int) -> int:
    """Bag size of every tree of a group: max(30, floor(n / 2)) (C13 BAG_MIN_ROWS, BAG_FRACTION).

    Rule: R19. Computed as max(BAG_MIN_ROWS, int(BAG_FRACTION x n)), the source's own expression.
    Refuses n_group_rows < 1.
    """
    n = as_int_value(n_group_rows, "n_group_rows", 1)
    return max(int(BAG_MIN_ROWS), int(BAG_FRACTION * n))


# Provenance: pm25_adaptation.py:642-643 (np.random.RandomState(seed).choice(n, size=take,
# replace=True)); D48 (owner rulings, part A); plan 5 G-NODRAW (bank bags are an allowed draw).
def draw_bag(n_group_rows: int, seed: int) -> np.ndarray:
    """Draw one bag: bag_size(n) row positions from 0..n-1, with replacement.

    Rule: R19, G-NODRAW, D48. numpy RandomState(seed).choice(n, bag_size(n), replace=True), the
    source's generator, so the harness reproduces legacy bags from seed values alone. The seed is
    name_seed(..., BAG), or a legacy integer passed by the harness.

    Returns int64 positions into the group's own rows. Refuses n_group_rows < 1 or a seed outside
    [0, 2^32 - 1].
    """
    n = as_int_value(n_group_rows, "n_group_rows", 1)
    s = as_int_value(seed, "seed", 0, SEED_MAX)
    if BAG_WITH_REPLACEMENT is not True:
        raise BankRefusal("R19", "engine constant C13.bag_with_replacement must be True")
    return np.random.RandomState(s).choice(n, size=bag_size(n), replace=True).astype(np.int64,
                                                                                    copy=False)


# Provenance: pm25_adaptation.py:644-646 (DecisionTreeRegressor(max_depth=8, min_samples_leaf=5,
# max_features=0.1, random_state=...).fit(Vd[gi][idx], yd[gi][idx])); plan 1.7, 4.4.
def fit_one_tree(X: np.ndarray, y: np.ndarray, row_indices: np.ndarray, random_state: int) -> Any:
    """PRIMITIVE: fit one bank tree on the given rows with the given random_state value.

    Rule: R19, G-NOKNOB. Tree settings come from the engine constants only (depth, min leaf,
    max_features, criterion); X is float32 and y float64. The tree is fitted on X[row_indices],
    y[row_indices] in the order given (rows may repeat). The random_state drives the tree's node
    feature sampling. No argument for storage, sampler, layout, seed formula, artefact or settings.

    Returns the fitted tree. Refuses empty row_indices, rows outside X, non-finite y at those rows,
    a random_state that is not an integer value in [0, 2^32 - 1], or X/y of the wrong type.
    """
    X = check_features(X)
    y = check_target(y, X.shape[0], "y")
    rows = check_rows(row_indices, X.shape[0], "row_indices")
    rs = as_int_value(random_state, "random_state", 0, SEED_MAX)
    yb = y[rows]
    if not np.all(np.isfinite(yb)):
        raise BankRefusal("R19", "%d of the %d bag rows have a non-finite label"
                          % (int(np.sum(~np.isfinite(yb))), len(yb)),
                          fix="bank rows come from DonorRows, which holds valid labels only")
    tree = _tree_class()(criterion=TREE_CRITERION, max_depth=TREE_MAX_DEPTH,
                         min_samples_leaf=TREE_MIN_LEAF, max_features=TREE_MAX_FEATURES,
                         random_state=rs)
    return tree.fit(X[rows], yb)


# Provenance: adaptation.py:456-458 (ob = setdiff1d(home, inbag), asserted disjoint);
# adaptation.py:98-102 (held-out rows WITHIN the tree's own group, never all groups).
def oob_rows(home_rows: np.ndarray, bag_rows: np.ndarray) -> np.ndarray:
    """The tree's out-of-bag rows: its own group's rows that are not in its bag.

    Rule: R19. Held out WITHIN the tree's own group, never against all groups (that bug gave a
    near-1.0 held-out share and a placebo that scored).

    Returns sorted unique positions. Refuses (internal asserts, raised even under python -O) any
    overlap with the bag, and any bag row that is not one of the home rows (a tree fitted on
    another group's row).
    """
    home = np.asarray(home_rows)
    bag = np.asarray(bag_rows)
    if home.ndim != 1 or bag.ndim != 1:
        raise BankRefusal("R19", "home rows and bag rows must be 1-D")
    if not np.all(np.isin(bag, home)):
        raise BankRefusal("R19", "%d bag rows are not rows of the tree's own group"
                          % int(np.sum(~np.isin(bag, home))),
                          fix="draw the bag over the group's own rows only")
    ob = np.setdiff1d(home, bag, assume_unique=False)
    if np.intersect1d(ob, bag).size != 0:
        raise BankRefusal("R19", "an out-of-bag row leaked into the bag")
    return ob.astype(np.int64, copy=False)


# Provenance: plan 2.3 R19 (the expected held-out share from the bag size replaces the fixed
# [0.15, 0.80] band, adaptation.py:474); D50 (owner rulings, part A: the exact form).
def expected_oob_share(n_group_rows: int, bag: int) -> float:
    """Expected out-of-bag share of a bag of size b drawn with replacement from n rows: (1 - 1/n)^b.

    Rule: R19, D50. A one-row group gives 0.0 (its only row is always drawn).
    Refuses n < 1 or b < 1.
    """
    n = as_int_value(n_group_rows, "n_group_rows", 1)
    b = as_int_value(bag, "bag", 1)
    return float((1.0 - 1.0 / n) ** b)


def oob_share_tolerance(expected: float, n_group_rows: int) -> float:
    """D51: 5 x sqrt(p (1 - p) / n), p the expected held-out share, n the home group's rows."""
    n = as_int_value(n_group_rows, "n_group_rows", 1)
    p = float(expected)
    if not (0.0 <= p <= 1.0):
        raise BankRefusal("R19", "expected held-out share %r is outside [0, 1]" % (expected,))
    return OOB_SHARE_TOLERANCE_SIGMAS * math.sqrt(p * (1.0 - p) / n)


# Provenance: adaptation.py:474-477 (assert on the mean held-out share); plan 2.3 R19; D51.
def check_oob_share(observed: Mapping[str, float], expected: Mapping[str, float],
                    n_group_rows: Mapping[str, int]) -> None:
    """Refuse a bank whose observed held-out share per group is far from the expected share.

    Rule: R19, D51. For each group: |observed - expected| <= 5 x sqrt(p (1 - p) / n), with p the
    expected share for the bag size and n the home group's row count. A share near 1.0 is the
    signature of out-of-bag taken against all groups instead of the tree's own.

    SIGNATURE NOTE: the approved signature took (observed, expected) only. D51's bound needs each
    group's row count, so n_group_rows is a third argument (the rulings file wins).

    Inputs: observed {group: mean held-out share over its trees}; expected {group:
    expected_oob_share}; n_group_rows {group: rows}. Refuses different group sets, a non-finite
    observed share, and any group outside the tolerance (all such groups are named).
    """
    keys = set(observed)
    if keys != set(expected) or keys != set(n_group_rows):
        raise BankRefusal("R19", "held-out share check got different groups: observed %s, expected "
                          "%s, rows %s" % (sorted(observed), sorted(expected), sorted(n_group_rows)))
    bad = []
    for g in sorted(keys):
        obs = observed[g]
        if isinstance(obs, bool) or not isinstance(obs, (Real, np.floating)) or not math.isfinite(obs):
            raise BankRefusal("R19", "group %r: observed held-out share %r is not a finite number"
                              % (g, obs))
        p = float(expected[g])
        tol = oob_share_tolerance(p, n_group_rows[g])
        if abs(float(obs) - p) > tol:
            bad.append("%s: observed %.4f, expected %.4f, tolerance %.4f (n = %d)"
                       % (g, float(obs), p, tol, int(n_group_rows[g])))
    if bad:
        raise BankRefusal("R19", "held-out share outside the expected band in %d group(s): %s"
                          % (len(bad), "; ".join(bad)),
                          fix="out-of-bag rows must be taken within the tree's own group; a share "
                              "near 1.0 means they were taken against all groups")


# ---------------------------------------------------------------------------------------------------
# Fingerprints (bank manifest, tree-answer store keys)
_TREE_ARRAYS = ("children_left", "children_right", "feature", "threshold", "value", "impurity",
                "n_node_samples", "weighted_n_node_samples", "missing_go_to_left")


def tree_fingerprint(tree: Any) -> str:
    """SHA-256 of a fitted tree's node arrays (structure, thresholds, leaf values) and its input
    width. Two trees with the same fingerprint answer every row with the same bytes. None (a
    skipped corrector) gives one fixed marker fingerprint."""
    h = hashlib.sha256()
    if tree is None:
        h.update(b"none")
        return h.hexdigest()
    h.update(("n_features_in=%d;" % int(tree.n_features_in_)).encode("ascii"))
    t = tree.tree_
    for name in _TREE_ARRAYS:
        if not hasattr(t, name):
            continue
        a = np.ascontiguousarray(getattr(t, name))
        h.update(("%s:%s:%s;" % (name, a.dtype.str, a.shape)).encode("ascii"))
        h.update(a.tobytes())
    return h.hexdigest()


def _bank_fingerprint(trees, correctors, placebos, tree_group, tree_number) -> str:
    h = hashlib.sha256()
    for i in range(len(trees)):
        h.update(("%s|%d|%s|%s|%s\n" % (tree_group[i], tree_number[i], tree_fingerprint(trees[i]),
                                        tree_fingerprint(correctors[i]),
                                        tree_fingerprint(placebos[i]))).encode("utf-8"))
    return h.hexdigest()


def _hash_strings(values: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------------------
# Ownership (owner rulings, part D: a unit's router never uses its own group's trees)
def _group_name_arg(group: Any) -> str:
    """A group name must be a non-empty str: bytes, an int or None never match a tree's group, so
    they would silently drop nothing."""
    if not isinstance(group, str) or group == "":
        raise BankRefusal("G-DISJOINT", "a group must be a non-empty name string, got %s %r"
                          % (type(group).__name__, group),
                          fix="pass the group name exactly as the bank's tree_group holds it")
    return group


def _owners(tree_group: Sequence[str]) -> np.ndarray:
    owners = np.asarray(tuple(tree_group), dtype=object)
    if owners.ndim != 1 or owners.size == 0:
        raise BankRefusal("G-DISJOINT", "tree_group must be a non-empty 1-D sequence of group names")
    bad = sorted(repr(g) for g in set(owners.tolist()) if not isinstance(g, str) or g == "")
    if bad:
        raise BankRefusal("G-DISJOINT", "tree_group holds entries that are not group names: %s"
                          % ", ".join(bad))
    return owners


def _near_misses(owners: np.ndarray, group: str) -> Tuple[str, ...]:
    """Owners that equal ``group`` up to letter case and surrounding spaces, other than itself."""
    key = group.strip().casefold()
    return tuple(sorted(g for g in set(owners.tolist()) if g != group and g.strip().casefold() == key))


def _refuse_near_miss(owners: np.ndarray, group: str, n_own: int) -> None:
    if n_own == 0:
        near = _near_misses(owners, group)
        if near:
            raise BankRefusal("G-DISJOINT", "group %r owns no tree, but %s does (a different case or "
                              "spacing of the same name)" % (group, " and ".join(repr(g) for g in near)),
                              fix="pass the group name exactly as the bank's tree_group holds it")


def group_tree_columns(tree_group: Sequence[str], group: str) -> np.ndarray:
    """Tree columns (positions in the bank's tree order) owned by ``group``, ascending.

    Column arithmetic only. Refuses a group that is not a non-empty string, and a group that owns no
    tree while a different case or spacing of its name does. Any other group that owns no tree gets
    no column (an empty array); the router guard is columns_without_own_group."""
    owners = _owners(tree_group)
    group = _group_name_arg(group)
    own = np.flatnonzero(owners == group).astype(np.int64)
    _refuse_near_miss(owners, group, len(own))
    return own


def columns_excluding_group(tree_group: Sequence[str], group: str) -> np.ndarray:
    """Every tree column NOT owned by ``group``, ascending.

    Column arithmetic only, NOT the leak guard: a group that owns no tree gets every column. It is
    kept with that behaviour because the tree-answer store's tests compare its own column mask with
    this one, a group outside the bank included. Refuses a group that is not a non-empty string, and
    a group that owns no tree while a different case or spacing of its name does. A router takes its
    columns from columns_without_own_group, which refuses any group that owns no tree."""
    owners = _owners(tree_group)
    group = _group_name_arg(group)
    keep = np.flatnonzero(owners != group).astype(np.int64)
    _refuse_near_miss(owners, group, len(owners) - len(keep))
    return keep


# Provenance: owner rulings part D ("a unit's router never sees its own group's trees, which are
# dropped as columns"); plan 2.2 R14 (the drop is a column mask, and every router fit asserts it).
def columns_without_own_group(bank: Bank, group: str) -> np.ndarray:
    """The tree columns a router serving a unit of ``group`` may use: every tree of the bank except
    that group's own, ascending. FAIL-CLOSED.

    Rule: owner rulings part D (leave one group out), R14, G-DISJOINT. Under leave-one-group-out
    every group trains its own trees, so a group that owns no tree in the bank is a wrong name (a
    typo, another case, a unit id), and the mask would drop nothing. It is refused, unless the
    bank's manifest names the group as held out (held_out_fold; always empty for the banks
    fit_donor_bank builds, which fits no fold bank).

    Returns int64 column positions. Refuses a group that is not a non-empty string; a group that owns
    no tree and is not named held out (near-miss names are listed in the message); an empty result
    (a bank of that group alone). Asserts (raised even under python -O) that no returned column
    belongs to ``group``.
    """
    for name in ("tree_group", "manifest"):
        if not hasattr(bank, name):
            raise BankRefusal("G-DISJOINT", "columns_without_own_group needs the Bank, which has "
                              "tree_group and manifest; got %s" % type(bank).__name__,
                              fix="pass the Bank that fit_donor_bank returned")
    owners = _owners(bank.tree_group)
    group = _group_name_arg(group)
    own = owners == group
    held_out = tuple(getattr(bank.manifest, "held_out_fold", ()) or ())
    if not own.any() and group not in held_out:
        near = _near_misses(owners, group)
        raise BankRefusal("G-DISJOINT", "group %r owns no tree in this bank%s; under leave one group "
                          "out every group trains its own trees, so its router would drop nothing"
                          % (group, (" (did you mean %s?)" % " or ".join(repr(g) for g in near))
                                    if near else ""),
                          fix="pass the unit's group name exactly as the bank's tree_group holds it")
    keep = np.flatnonzero(~own).astype(np.int64)
    if keep.size == 0:
        raise BankRefusal("G-DISJOINT", "every tree of the bank belongs to group %r, so its router "
                          "would have no tree column" % group,
                          fix="leave one group out needs trees from at least one other group")
    if any(owners[c] == group for c in keep.tolist()):
        raise BankRefusal("G-DISJOINT", "internal: an own-group column of %r survived the mask" % group)
    return keep


def seed_table(tree_group: Sequence[str], tree_number: Sequence[int]) -> Tuple[Dict[str, Any], ...]:
    """The disclosed seeds of every tree, for the manifest: group, tree number, bag, tree and
    corrector seeds (the placebo corrector uses the corrector seed)."""
    if len(tree_group) != len(tree_number):
        raise BankRefusal("R19", "tree_group and tree_number differ in length")
    return tuple({"group": g, "tree_number": int(j),
                  "bag_seed": name_seed(g, j, SeedRole.BAG),
                  "tree_seed": name_seed(g, j, SeedRole.TREE),
                  "corrector_seed": name_seed(g, j, SeedRole.CORRECTOR)}
                 for g, j in zip(tree_group, tree_number))


# ---------------------------------------------------------------------------------------------------
_DONOR_FIELDS = ("groups", "cut", "cut_kind", "lead", "fold", "unit_ids", "times", "group_of_row",
                 "grid_rows", "y", "X", "row_key_hash")


def _field(donor_rows: Any, name: str) -> Any:
    try:
        return getattr(donor_rows, name)
    except AttributeError:
        raise BankRefusal("G-DONOR", "the donor rows have no %r field" % name,
                          fix="pass the DonorRows that FitContext.donor_rows hands out") from None


def _check_grid_order(grid_rows: Any, n_rows: int) -> None:
    """The donor rows must come in strictly ascending grid_rows (the pool's grid order: unit by unit,
    then step). A group's bags are positions into its rows in that order, so any other order (or a
    repeated row) would change its trees with no other sign."""
    g = np.asarray(grid_rows)
    if g.ndim != 1 or len(g) != n_rows:
        raise BankRefusal("G-DONOR", "donor grid_rows has shape %s for %d rows" % (g.shape, n_rows))
    if g.dtype == np.bool_ or not np.issubdtype(g.dtype, np.integer):
        raise BankRefusal("G-DONOR", "donor grid_rows must hold integer grid positions, got %s" % g.dtype)
    if n_rows and int(g.min()) < 0:
        raise BankRefusal("G-DONOR", "donor grid_rows holds a negative position (%d)" % int(g.min()))
    if n_rows > 1:
        up = g[1:] > g[:-1]
        if not bool(up.all()):
            breaks = np.flatnonzero(~up)
            raise BankRefusal("R19", "the donor rows are not in ascending grid order: %d place(s) where "
                              "grid_rows does not increase, first after row %d (%d then %d)"
                              % (len(breaks), int(breaks[0]), int(g[breaks[0]]), int(g[breaks[0] + 1])),
                              fix="hand the rows over in the pool's grid order (ascending grid_rows, "
                                  "unit by unit then step, no repeats), as FitContext.donor_rows does")


# Values scanned per block by the finiteness check (about 16 MB of float32), so the check never
# allocates a mask the size of the donor matrix.
_FINITE_SCAN_VALUES = 1 << 22


def _check_finite_features(X: np.ndarray) -> None:
    """Refuse any missing or infinite tree feature: DonorRows.X is 0-filled (R30). The fitted trees
    would otherwise route missing values themselves and differ from the 0-filled trees."""
    n = X.shape[0]
    step = max(1, _FINITE_SCAN_VALUES // max(1, X.shape[1]))
    bad_rows, first = 0, -1
    for start in range(0, n, step):
        ok_rows = np.isfinite(X[start:start + step]).all(axis=1)
        if not bool(ok_rows.all()):
            where = np.flatnonzero(~ok_rows)
            bad_rows += len(where)
            if first < 0:
                first = start + int(where[0])
    if bad_rows:
        raise BankRefusal("R30", "%d donor rows hold a missing or infinite tree feature (first: row %d)"
                          % (bad_rows, first),
                          fix="tree features are 0-filled before the bank (R30); DonorRows.X holds "
                              "finite values only")


def _check_trees_per_donor(trees_per_donor: Any) -> int:
    t = as_int_value(trees_per_donor, "trees_per_donor", 1)
    allowed = (int(TREES_PER_DONOR), int(SMOKE_TREES_PER_DONOR))
    if t not in allowed:
        raise BankRefusal("R19", "trees_per_donor = %d; the bank takes only the engine constant "
                          "(C13.trees_per_donor = %d) or the smoke constant "
                          "(C13.smoke_trees_per_donor = %d)" % (t, allowed[0], allowed[1]),
                          fix="the tree count is never set by a package or a flag (plan 1.7)")
    return t


# Provenance: plan 2.3 R19; plan 4.1 step 6; pm25_adaptation.py:621-651 (for e, g in groupby; bag per
# group; tree j per group); adaptation.py:454-477; plan 5 G-DISJOINT (bank manifest); owner rulings
# part D (every group trains its own specialist).
def fit_donor_bank(donor_rows: Any, trees_per_donor: int) -> Bank:
    """Fit the whole bank from DonorRows: per group, in sorted order, trees, correctors and placebo
    correctors with name seeds.

    Rule: R19, G-DISJOINT, G-FITCUT. For each group g (sorted by name) with n rows (its row
    positions gi, ascending, which is grid order because the rows must come in ascending grid_rows)
    and each tree number j < trees_per_donor:
        bag       = draw_bag(n, name_seed(g, j, BAG))              positions into gi
        tree      = fit_one_tree(X, y, gi[bag], name_seed(g, j, TREE))
        oob       = oob_rows(gi, gi[bag])                           within g only
        corrector = fit_corrector(tree, X, y, oob, name_seed(g, j, CORRECTOR))
        placebo   = fit_placebo_corrector(..., the same seed)
    Each group's mean observed held-out share is checked against expected_oob_share(n, bag_size(n))
    (check_oob_share, D51). Every group in the donor rows trains its own trees; tree_group records
    the owner of each tree (leave one group out: columns_without_own_group).

    Inputs: donor_rows, read by attribute (groups, cut, cut_kind, lead, fold, unit_ids, times,
    group_of_row, grid_rows, y, X, row_key_hash); trees_per_donor, the engine constant or the smoke
    constant only.

    Returns Bank, trees in (sorted group, tree number) order. Refuses anything a primitive or
    check_oob_share refuses; a tree count other than the two constants; a row labelled after the
    cut (G-FITCUT); a row whose group is not listed, or a listed group without rows; a non-finite
    label; a missing or infinite tree feature (R30); rows not in strictly ascending grid_rows order
    (the pool's grid order); donor rows of a fold context (G-DISJOINT: under leave one group out no
    fold bank is fitted; one bank serves every fold by dropping that fold's tree columns, plan R13).
    OWNER DECISION pending on the fold path: keep it refused, or add the held-out groups to the
    DonorRows contract (the approved DonorRows has no field for them).
    """
    return fit_donor_bank_saved(donor_rows, trees_per_donor, None)


def fit_donor_bank_saved(donor_rows: Any, trees_per_donor: int, group_store: Any) -> Bank:
    """fit_donor_bank with a per-group save seam (owner request of ruling S2's engine change, 'save every progress'; PLUMBING ONLY,
    no number changes). group_store None is fit_donor_bank exactly. Otherwise, per group in the same sorted order:
    group_store.load(group) returns that group's (trees, correctors, placebo correctors, held-out shares) saved by
    an earlier, stopped process under the same key, or None; a loaded group is not refitted (its rows are not
    read). A fitted group is handed to group_store.save(group, trees, correctors, placebos, shares) as soon as it
    is fitted. The store verifies a loaded group's trees by tree_fingerprint (every node array: the same
    fingerprint answers every row with the same bytes), so the bank, its fingerprint and every tree answer equal
    a fresh fit's. Every other check (the donor rows, D51's held-out shares, the manifest) runs as before."""
    from treeroute.fit.correctors import fit_corrector_and_placebo  # one direction: no cycle

    for name in _DONOR_FIELDS:
        _field(donor_rows, name)
    t_per = _check_trees_per_donor(trees_per_donor)
    if donor_rows.fold is not None:
        raise BankRefusal("G-DISJOINT", "these donor rows belong to fold %r; under leave one group out "
                          "no fold bank is fitted: one bank serves every fold by dropping that fold's "
                          "tree columns (plan R13)" % (donor_rows.fold,),
                          fix="fit the bank on the donor rows of the whole context at the cut. OWNER "
                              "DECISION pending: keep fold banks refused, or add the held-out groups "
                              "to the DonorRows contract")
    # plan R20's per-group batching: a lazy X (fit.context.LazyDonorFeatures) is read one group's rows at a time;
    # each group's trees see exactly the rows (and bytes) they see in the whole matrix
    lazy = bool(getattr(donor_rows.X, "lazy_rows", False))
    if lazy:
        X = donor_rows.X
        if len(X.shape) != 2 or X.dtype != np.dtype(TREE_DTYPE):
            raise BankRefusal("R19", "X must be a 2-D %s matrix, got shape %s dtype %s"
                              % (TREE_DTYPE, X.shape, X.dtype))
    else:
        X = check_features(donor_rows.X)
    n_rows = X.shape[0]
    y = check_target(donor_rows.y, n_rows, "donor y")
    if not np.all(np.isfinite(y)):
        raise BankRefusal("G-DONOR", "%d donor labels are not finite" % int(np.sum(~np.isfinite(y))),
                          fix="DonorRows holds valid labels only")
    group_of_row = np.asarray(donor_rows.group_of_row)
    unit_ids = np.asarray(donor_rows.unit_ids)
    times = np.asarray(donor_rows.times)
    for what, arr in (("group_of_row", group_of_row), ("unit_ids", unit_ids), ("times", times)):
        if arr.ndim != 1 or len(arr) != n_rows:
            raise BankRefusal("G-DONOR", "donor %s has shape %s for %d rows"
                              % (what, arr.shape, n_rows))
    if n_rows == 0:
        raise BankRefusal("G-DONOR", "the donor rows are empty")
    _check_grid_order(donor_rows.grid_rows, n_rows)
    if not lazy:
        _check_finite_features(X)
    if not np.issubdtype(times.dtype, np.integer):
        raise BankRefusal("G-FITCUT", "donor times must be integer steps or days, got %s" % times.dtype)
    cut = as_int_value(donor_rows.cut, "cut", -(1 << 62))
    lead = as_int_value(donor_rows.lead, "lead", 0)
    if int(times.max()) > cut:
        raise BankRefusal("G-FITCUT", "%d donor rows are labelled after the cut %d (latest %d)"
                          % (int(np.sum(times > cut)), cut, int(times.max())),
                          fix="bank rows come from FitContext.donor_rows at this cut")
    listed = tuple(donor_rows.groups)
    if not all(isinstance(g, str) and g for g in listed):
        raise BankRefusal("G-DONOR", "donor group names must be non-empty strings: %r" % (listed,))
    groups = tuple(sorted(set(listed)))
    if len(groups) != len(listed):
        raise BankRefusal("G-DONOR", "the donor groups list repeats a name: %r" % (listed,))
    if group_of_row.dtype.kind not in "OU":
        raise BankRefusal("G-DONOR", "group_of_row must hold group names, got %s" % group_of_row.dtype)
    # group codes without a per-row string copy (the full donor pool has millions of rows)
    names, codes = np.unique(group_of_row.astype(object), return_inverse=True)
    present = set(str(g) for g in names)
    if present - set(groups):
        raise BankRefusal("G-DISJOINT", "rows of groups outside the donor groups: %s"
                          % sorted(present - set(groups)))
    if set(groups) - present:
        raise BankRefusal("G-DONOR", "donor groups without any row at the cut: %s"
                          % sorted(set(groups) - present))
    code_of = {str(g): k for k, g in enumerate(names)}
    trees, correctors, placebos, tree_group, tree_number = [], [], [], [], []
    observed, expected, n_by_group = {}, {}, {}
    for g in groups:
        gi = np.flatnonzero(codes == code_of[g]).astype(np.int64)     # ascending = grid order
        n = len(gi)
        saved = group_store.load(g) if group_store is not None else None
        if saved is not None:          # a stopped process's fit of this group, verified by the store
            g_trees, g_corr, g_plac, shares = saved
            if not (len(g_trees) == len(g_corr) == len(g_plac) == len(shares) == t_per):
                raise BankRefusal("R19", "internal: the saved fit of group %r holds %d trees, not %d"
                                  % (g, len(g_trees), t_per))
            trees.extend(g_trees)
            correctors.extend(g_corr)
            placebos.extend(g_plac)
            tree_group.extend([g] * t_per)
            tree_number.extend(range(t_per))
            observed[g] = float(np.mean([float(s) for s in shares]))
            expected[g] = expected_oob_share(n, bag_size(n))
            n_by_group[g] = n
            continue
        shares = []
        first_tree = len(trees)
        if lazy:                       # the group's rows alone, positions into them (the same rows, in order)
            Xg = check_features(X[gi])
            _check_finite_features(Xg)
            yg, home = y[gi], np.arange(n, dtype=np.int64)
        else:
            Xg, yg, home = X, y, gi
        for j in range(t_per):
            bag = draw_bag(n, name_seed(g, j, SeedRole.BAG))
            rows = home[bag]
            tree = fit_one_tree(Xg, yg, rows, name_seed(g, j, SeedRole.TREE))
            ob = oob_rows(home, rows)
            shares.append(len(ob) / float(n))
            corr, plac = fit_corrector_and_placebo(tree, Xg, yg, ob,
                                                   name_seed(g, j, SeedRole.CORRECTOR))
            trees.append(tree)
            correctors.append(corr)
            placebos.append(plac)
            tree_group.append(g)
            tree_number.append(j)
        observed[g] = float(np.mean(shares))
        expected[g] = expected_oob_share(n, bag_size(n))
        n_by_group[g] = n
        if group_store is not None:
            group_store.save(g, tuple(trees[first_tree:]), tuple(correctors[first_tree:]),
                             tuple(placebos[first_tree:]), tuple(float(s) for s in shares))
    check_oob_share(observed, expected, n_by_group)

    unique_units = sorted(set(str(u) for u in unit_ids.tolist()))
    manifest = BankManifest(
        bank_fingerprint=_bank_fingerprint(trees, correctors, placebos, tree_group, tree_number),
        groups=groups, unit_ids_hash=_hash_strings(unique_units), n_units=len(unique_units),
        min_label_time=int(times.min()), max_label_time=int(times.max()), cut=cut,
        cut_kind=donor_rows.cut_kind, lead=lead, held_out_fold=())      # no fold bank (see above)
    return Bank(trees=tuple(trees), correctors=tuple(correctors), placebo_correctors=tuple(placebos),
                tree_group=tuple(tree_group), tree_number=tuple(tree_number),
                oob_share=dict(observed), manifest=manifest)
