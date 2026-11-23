"""PROPOSED signatures: the name-seed bank recipe in treeroute/fit/ (plan 4.2, R19). SCIENCE: owner
signatures, agent bodies.

One recipe for every package: per donor group 100 trees (engine constant; smoke 12, R21); each tree
fits a bag of max(30, half the group's rows) drawn with replacement; depth 8, min leaf 5,
max_features 10%, squared error; float32. Three seeds per tree, each a fixed checksum of (donor NAME,
tree number, role): the bag draw, the tree's random_state, and its corrector's random_state (the
placebo corrector uses the same seed as the real one). Seeds are disclosed and never varied. Adding
or removing a donor never changes another donor's trees, correctors or placebo correctors.

Primitives take no storage, sampler, layout, seed-formula or artefact argument (signature test,
G-NOKNOB). The fit-one-tree primitive takes a random_state VALUE, so the legacy harness can pass the
legacy seeds as integers.
"""
# Provenance for the module: pm25_adaptation.py:636-648 (bank), :641-646 (legacy seeds
# 7000 + e*17 + j, 700 + j); adaptation.py:454-477 (correctors; placebo roll at :467; corrector seed j
# over the global tree list at :470; [0.15, 0.80] band at :474).
from __future__ import annotations

from typing import Mapping, Optional

import numpy as np

from .common import Bank, FittedTree, SeedRole
from .fit_context import DonorRows


# Provenance: plan 2.3 R19 ("a fixed checksum of (donor NAME, tree number, role)"); replaces
# 7000 + e*17 + j, 700 + j and j over the global list (pm25_adaptation.py:641-646; adaptation.py:470).
def name_seed(donor_name: str, tree_number: int, role: SeedRole) -> int:
    """The fixed seed of one tree role, from the donor's NAME and the tree number.

    Rule: R19.  Needed: Wed 30 Sep (bank primitives with name seeds).

    Contract (plan 2.3 R19, 1.7):
        A pure checksum of (donor name, tree number, role). It never depends on list position, so
        adding or removing a donor changes no other donor's seeds, and the old overlap between
        donors disappears. Disclosed in the manifest, never varied.
    Inputs:
        donor_name: the donor group's name.
        tree_number: 0-based tree number within the donor.
        role: BAG, TREE or CORRECTOR.
    Returns:
        an integer seed in [0, 2^32 - 1] (the range numpy RandomState accepts).
    Refuses:
        - an empty name or a negative tree number.
    OWNER DECISION: which checksum -- propose the first 4 bytes (big-endian) of SHA-256 of the UTF-8
        string "<donor_name>|<tree_number>|<role value>".
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_adaptation.py:636-648 (take = max(30, int(0.5 * n))).
def bag_size(n_group_rows: int) -> int:
    """Bag size of every tree of a donor group: max(30, half the group's rows).

    Rule: R19.  Needed: Wed 30 Sep (bank).

    Contract (plan 2.3 R19; source int(0.5 x n), i.e. half rounded down):
        max(30, floor(n / 2)).
    Inputs:
        n_group_rows: the donor group's training rows at the cut.
    Returns:
        the bag size.
    Refuses:
        - n_group_rows < 1.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_adaptation.py:641-643 (np.random.RandomState(seed).choice(n, size=take,
# replace=True)); plan 5 G-NODRAW (bank bags are an allowed draw, seeded by the disclosed formula).
def draw_bag(n_group_rows: int, seed: int) -> np.ndarray:
    """Draw one bag: bag_size(n) row positions from 0..n-1, with replacement.

    Rule: R19, G-NODRAW.  Needed: Wed 30 Sep (bank).

    Contract (plan 2.3 R19, 5 G-NODRAW):
        One of the draws G-NODRAW allows, and nothing else in the data path draws: bank bags, tree
        feature sampling and corrector fits (each seeded by the disclosed name-seed formula), and
        the GLS weight forest (its fixed engine-constant random_state). The seed is
        name_seed(..., BAG), or a legacy integer passed by the harness.
    Inputs:
        n_group_rows: rows in the donor group.
        seed: the bag seed value.
    Returns:
        int64 positions (length bag_size(n)).
    Refuses:
        - n_group_rows < 1.
    OWNER DECISION: generator -- propose numpy RandomState(seed).choice(n, size, replace=True), as
        the source, so the harness can reproduce legacy bags from seed values alone.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: pm25_adaptation.py:644-646 (DecisionTreeRegressor(max_depth=8, min_samples_leaf=5,
# max_features=0.1, random_state=...)); plan 1.7 last row, 4.4 (primitive with a random_state value).
def fit_one_tree(X: np.ndarray, y: np.ndarray, row_indices: np.ndarray, random_state: int) -> FittedTree:
    """PRIMITIVE: fit one bank tree on the given rows with the given random_state value.

    Rule: R19, G-NOKNOB (primitive signature).  Needed: Wed 30 Sep (bank primitives).

    Contract (plan 2.3 R19, 1.7, 4.4):
        Tree constants come from the engine constants (depth 8, min leaf 5, max_features 10%,
        squared error); X is float32. The random_state drives the tree's node feature sampling.
        There is no argument for storage, sampler, layout, seed formula, artefact or tree settings.
    Inputs:
        X: feature matrix (float32).
        y: labels (float64).
        row_indices: the bag (rows may repeat).
        random_state: an integer value (name_seed(..., TREE), or a legacy value from the harness).
    Returns:
        the fitted tree.
    Refuses:
        - empty row_indices, or non-finite y at those rows.
    OWNER DECISION: legacy variants that need OTHER tree settings (the optional track's
        max_features 0.15) build their trees inside the harness, since this primitive takes none.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: adaptation.py:454-477 (corrector DecisionTreeRegressor(max_depth=6, min_samples_leaf=10,
# max_features=mf, random_state=j)).
def fit_one_corrector(X: np.ndarray, residual: np.ndarray, row_indices: np.ndarray, random_state: int) -> FittedTree:
    """PRIMITIVE: fit one corrector tree (depth 6, leaf 10) on given rows and residuals.

    Rule: R19.  Needed: Wed 30 Sep (bank).

    Contract (plan 2.3 R19):
        Corrector constants from the engine constants: depth 6, min leaf 10, max_features 10% (the
        source used the bank's max_features). random_state is a value.
    Inputs:
        X: feature matrix (float32).
        residual: the residual target at every row of X (only row_indices are read).
        row_indices: the out-of-bag rows.
        random_state: name_seed(..., CORRECTOR), or a legacy value.
    Returns:
        the fitted corrector.
    Refuses:
        - empty row_indices.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: adaptation.py:456-458 (ob = home rows minus in-bag rows; asserted disjoint); adaptation.py:
# 98-102 (held-out rows WITHIN the tree's own region, never all donors).
def oob_rows(home_rows: np.ndarray, bag_rows: np.ndarray) -> np.ndarray:
    """The tree's out-of-bag rows: its own donor group's rows that are not in its bag.

    Rule: R19.  Needed: Wed 30 Sep (bank).

    Contract (plan 2.3 R19; source: provenance comment):
        Held out WITHIN the tree's own donor group, never against all donors (that bug gave a
        near-1.0 held-out share and a placebo that scored).
    Inputs:
        home_rows: row positions of the tree's donor group.
        bag_rows: the bag's positions (may repeat).
    Returns:
        sorted unique out-of-bag positions.
    Refuses:
        - (internal assert) any overlap with the bag.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.3 R19 ("the expected held-out share computed from the bag size (replaces the fixed
# [0.15, 0.80] band, adaptation.py:474)"); pm25_adaptation.py:630-635 comment (exp(-k/n)).
def expected_oob_share(n_group_rows: int, bag: int) -> float:
    """Expected out-of-bag share of a bag of size b drawn with replacement from n rows.

    Rule: R19.  Needed: Wed 30 Sep (bank).

    Contract (plan 2.3 R19):
        (1 - 1/n)^b. It replaces the fixed plausibility band on the observed held-out share.
    Inputs:
        n_group_rows: n.
        bag: b.
    Returns:
        the expected share in (0, 1).
    Refuses:
        - n < 1 or b < 1.
    OWNER DECISION: the exact form (1 - 1/n)^b versus the source comment's exp(-b/n); and the
        TOLERANCE for comparing observed with expected (the plan gives none) -- see check_oob_share.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: adaptation.py:474-477 (assert on the mean held-out share); plan 2.3 R19.
def check_oob_share(observed: Mapping[str, float], expected: Mapping[str, float]) -> None:
    """Refuse a bank whose observed held-out share per donor group is far from the expected share.

    Rule: R19.  Needed: Wed 30 Sep (bank).

    Contract (plan 2.3 R19):
        A share near 1.0 is the signature of out-of-bag taken against all groups instead of the
        tree's own; the expected share is computed from the bag size, per group.
    Inputs:
        observed: {donor group: mean observed held-out share over its trees}.
        expected: {donor group: expected_oob_share}.
    Returns:
        None.
    Refuses:
        - any group outside the tolerance.
    OWNER DECISION: the tolerance (not stated in the plan) -- a number is needed before this can run.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: adaptation.py:454-477 (r = y[ob] - t.predict(X[ob]); skip trees with < 50 out-of-bag rows,
# minrows=50).
def fit_corrector(tree: FittedTree, X: np.ndarray, y: np.ndarray, oob: np.ndarray, random_state: int) -> Optional[FittedTree]:
    """Fit a tree's corrector on its out-of-bag residuals.

    Rule: R19, R24.  Needed: Wed 30 Sep (bank).

    Contract (plan 2.3 R19; source: provenance comment):
        residual = y - tree(X) on the tree's out-of-bag rows; fit_one_corrector on them with the
        corrector seed. Same construction for every package.
    Inputs:
        tree: the bank tree.
        X, y: donor rows (DonorRows.X, DonorRows.y).
        oob: the tree's out-of-bag rows (oob_rows).
        random_state: name_seed(donor, j, CORRECTOR).
    Returns:
        the corrector, or None when the tree has too few out-of-bag rows.
    Refuses:
        - non-finite residuals.
    OWNER DECISION: the source skips a corrector with fewer than 50 out-of-bag rows; the plan does
        not mention it -- keep 50 (propose) or drop the minimum.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: adaptation.py:466-467 (placebo: r = np.roll(r, len(r) // 2)); plan 2.4 R24 (placebo =
# scrambled residual, never selectable).
def fit_placebo_corrector(tree: FittedTree, X: np.ndarray, y: np.ndarray, oob: np.ndarray,
                          random_state: int) -> Optional[FittedTree]:
    """Fit the placebo corrector: the same construction on a scrambled residual.

    Rule: R19, R24.  Needed: Wed 30 Sep (bank).

    Contract (plan 2.3 R19, 2.4 R24; source: provenance comment):
        The residual (as in fit_corrector) is rolled by half its length, which keeps its
        distribution and breaks its link to the rows. Same seed as the real corrector. Never
        selectable; it guards against false 'helps' claims.
    Inputs:
        tree, X, y, oob: as fit_corrector.
        random_state: the SAME value the real corrector used.
    Returns:
        the placebo corrector, or None when the real one was skipped.
    Refuses:
        - as fit_corrector.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")


# Provenance: plan 2.3 R19; plan 4.1 step 6; pm25_adaptation.py:621-650 (for e, g in groupby; bag per
# group; tree j per group); plan 5 G-DISJOINT (bank manifest).
def fit_donor_bank(donor_rows: DonorRows, trees_per_donor: int) -> Bank:
    """Fit the whole bank from DonorRows: per donor group, in sorted order, trees, correctors and
    placebo correctors with name seeds.

    Rule: R19, G-DISJOINT, G-FITCUT.  Needed: Wed 30 Sep (bank).

    Contract (plan 2.3 R19, 4.1 step 6):
        For each donor group (sorted) and tree number j < trees_per_donor: bag = draw_bag(n,
        name_seed(g, j, BAG)) over the group's own rows; tree = fit_one_tree(..., name_seed(g, j,
        TREE)); corrector and placebo with name_seed(g, j, CORRECTOR). The manifest records groups,
        units, label times and the cut (G-DISJOINT). Observed held-out shares are checked
        (check_oob_share).
    Inputs:
        donor_rows: from FitContext.donor_rows('bank') at this cut.
        trees_per_donor: the engine constant (100) or the smoke constant (12, R21); never from a
            package or a flag.
    Returns:
        Bank.
    Refuses:
        - anything the primitives or check_oob_share refuse.
    """
    raise NotImplementedError("PROPOSED signature -- awaiting owner approval")
