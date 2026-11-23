"""The GLS row-weight model (plan 4.2 fit/ row, R25). SCIENCE bodies for the owner-approved signatures of
treeroute/_proposed/weights_gls.py (owner rulings A-F).

GLS weights are a Type-2 TOOL: they change the router's row weights, never the tree answers, so
weighted arms read the same tree-answer tables. One weight model per lead cut serves that lead's
decision and test pass.

The rules, as ruled:
  - Target (D55, D56; owner rulings E, L2 rule 4): the cross-region error, |y - mean of the PLAIN
    answers of the trees outside the row's own OVERLAP BLOCK| per donor row (the same rule as the
    router's column mask). The blocks are required: a group alone in its block is a one-group block
    passed explicitly, never a default.
  - Model (R25, C13): a random forest with the shipped weight model's settings as engine constants: 120 trees,
    depth 8, min leaf 20, max_features 1.0, bootstrap on, random_state 0 (fixed, disclosed, never
    varied), 4 threads. It is fitted on the donor rows at or before the inner-fit end of its cut, which
    is the lead's GUARD cut (D57): guard_ctx.donor_rows('gls').
  - Out-of-bag sigma (owner rulings E, L5 option c): the sigma served on a row the forest was fitted
    on is its OUT-OF-BAG prediction (the forest's trees whose bootstrap sample left the row out);
    other rows get the whole forest's prediction. The forest's own oob_prediction_ is used, because
    under sklearnex the bootstrap is drawn inside oneDAL (estimators_samples_ does not reproduce it);
    a fit in which some row has no out-of-bag tree is refused (sklearn would silently answer 0).
  - Floor (D58): 1% of R36's s for the IDENTITY link, the donor-row standard deviation of y (ddof 0)
    on the same donor rows, computed by the one R36 function (report.metrics.guard_tolerance with
    k = 1).
  - Clip bounds (D59): the 5th and 95th percentiles (numpy linear) of the floored out-of-bag sigma on
    the donor rows the model was fitted on; donor rows only, never the frame being weighted.
  - Weights (D60): floor, then clip, then 1/sigma^2, then the max/min ratio capped at 100 by raising
    the smallest weights to (largest / 100). With equal sigma every weight is equal, so the weighted
    arm equals the unweighted arm (the router's penalty is trace-normalised on the weighted Gram, so a
    common factor cancels; G-PLUMB checks it within the R36 tolerance).

The forest is fitted only with sklearn patched by sklearnex (owner ruling C: patched globally at start
up), so a run's weights are always the oneDAL forest's; the implementation is recorded, and so is every
warning the fit raised other than the out-of-bag one (each is re-emitted, never dropped).

Answers bank (flagged for the owner, L6): the approved contract takes the tree answers from the bank
of fit_ctx's cut, so at lead 0 the decision surface's GLS target is built from the FIT-cut bank, not
the L6 b inner-cut bank (the "+0.9-2.4 h" variant of the LORO addendum). The R25 record names the
answers' bank cut and this disclosure until the owner rules.

Signature note (flagged for the owner): cross_region_error and weight_model_for_cut take the overlap
blocks as a REQUIRED keyword (blocks=..., derive_overlap_blocks' value). The approved signatures carry
none, but the LORO addendum says the GLS target leaves out a row's whole block, and a default would let
a caller silently drop only the row's own group.
"""
# Provenance for the module: coral_architecture.py:304-313 (the shipped weight model, corrected:
# RandomForestRegressor(120, max_depth=8, min_samples_leaf=20, n_jobs=-1, random_state=0) fitted on
# |y - oof| in-sample residuals, clip bounds from whatever frame it weighted, :311); plan 2.4 R25; plan
# 9.1 item 2b; owner rulings A (D55-D60), E (L5 c: out-of-bag sigma).

import math
import traceback
import warnings
from contextlib import ExitStack
from dataclasses import dataclass
from numbers import Real
from typing import Any, Dict, Optional, Tuple

import numpy as np

from treeroute import engine_constants as K
from treeroute import split as _split
from treeroute.derive.derived import make_derived, sha256_of_json
from treeroute.derive.shapes import CutKind, Link
from treeroute.errors import RefusedError
from treeroute.report import metrics as _metrics

from .context import DonorRows, FitContext, feature_block_rows


class WeightsRefusal(RefusedError):
    """A GLS weight rule refused (R25, G-DONOR, G-FITCUT, G-NODRAW, C14)."""


@dataclass(frozen=True)
class WeightModel:
    """One cut's weight model and its donor-only constants (all written to derived.json). cut is the
    cut of the donor rows the forest was fitted on (the lead's guard cut); fold is -1 outside a fold
    context (no fold contexts exist under LORO)."""
    forest: Any
    cut: int
    lead: int
    sigma_floor: float
    clip_low: float
    clip_high: float
    fold: int


# The R25 record's disclosure of the answers' bank (owner ruling pending, L6)
L6_ANSWERS_DISCLOSURE = (
    "the tree answers of the GLS target come from the bank of fit_ctx's cut (approved contract); at lead 0 "
    "the decision surface's GLS target therefore reads the FIT-cut bank, not the L6 b inner-cut bank "
    "(owner ruling pending)")


class OobSigmaForest(object):
    """The fitted sigma forest (a FittedTree: predict(X)) with its out-of-bag sigma on the donor rows
    it was fitted on (L5 c). sigma(grid_rows, X) serves the out-of-bag value on those rows and the
    whole forest's prediction elsewhere. It also carries the fit's other warnings, and (set by
    weight_model_for_cut) the overlap blocks and the answers' bank cut the target used."""

    def __init__(self, forest: Any, grid_rows: np.ndarray, oob_sigma: np.ndarray, cut: int,
                 row_key_hash: str, implementation: str, fit_warnings: Tuple[str, ...] = ()) -> None:
        self._forest = forest
        self._rows = np.array(grid_rows, dtype=np.int64, copy=True)
        self._rows.setflags(write=False)
        self._oob = np.array(oob_sigma, dtype=np.float64, copy=True)
        self._oob.setflags(write=False)
        self.cut = int(cut)
        self.row_key_hash = str(row_key_hash)
        self.implementation = str(implementation)
        self.fit_warnings = tuple(str(w) for w in fit_warnings)
        self.blocks_members: Optional[Tuple[Tuple[str, ...], ...]] = None
        self.answers_cut: Optional[int] = None

    @property
    def grid_rows(self) -> np.ndarray:
        return self._rows

    @property
    def oob_sigma(self) -> np.ndarray:
        """The out-of-bag sigma on the fitted donor rows, in their order (before the floor)."""
        return self._oob

    @property
    def n_trees(self) -> int:
        return len(self._forest.estimators_)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """The whole forest's sigma for rows it was not fitted on (float64)."""
        return np.asarray(self._forest.predict(_features(X, "X")), dtype=np.float64)

    def sigma(self, grid_rows: np.ndarray, X: np.ndarray) -> np.ndarray:
        """Sigma per row (before the floor): the out-of-bag value on a fitted donor row (matched by
        grid position), the whole forest's prediction on any other row."""
        rows = np.asarray(grid_rows)
        if rows.ndim != 1 or rows.dtype.kind not in "iu":
            raise WeightsRefusal("R25", "grid_rows must be 1-D integer grid positions")
        Xv = _features(X, "X")
        if Xv.shape[0] != rows.size:
            raise WeightsRefusal("R25", "X has %d rows for %d grid rows" % (Xv.shape[0], rows.size))
        out = np.empty(rows.size, dtype=np.float64)
        fitted = np.zeros(rows.size, dtype=bool)
        pos_c = np.zeros(rows.size, dtype=np.int64)
        if self._rows.size:
            pos_c = np.minimum(np.searchsorted(self._rows, rows), self._rows.size - 1)
            fitted = self._rows[pos_c] == rows
        out[fitted] = self._oob[pos_c[fitted]]
        other = ~fitted
        if other.any():
            out[other] = self.predict(Xv[other])
        return out


# ---------------------------------------------------------------------------------------------------
def _all_finite(arr: np.ndarray) -> bool:
    """np.isfinite(arr).all() of a 2-D array, in row blocks of P5.donor_block_values values: the same answer (a value
    is finite or not on its own), with one block's boolean mask at a time instead of the whole array's (RAM tactic
    7: the donor matrix's mask was 1 byte a value right before the forest's fit)."""
    step = max(int(K.DONOR_BLOCK_VALUES) // max(int(arr.shape[1]), 1), 1)
    for a0 in range(0, int(arr.shape[0]), step):
        if not np.isfinite(arr[a0:a0 + step]).all():
            return False
    return True


def _features(X: Any, what: str) -> np.ndarray:
    arr = np.asarray(X)
    if arr.ndim != 2 or arr.dtype.kind != "f":
        raise WeightsRefusal("R25", "%s must be a 2-D float array, got %s %s" % (what, arr.dtype, arr.shape))
    if not _all_finite(arr):
        raise WeightsRefusal("R30", "%s holds missing or infinite values; tree features are 0-filled "
                             "(R30)" % what)
    return np.asarray(arr, dtype=np.float32)


def _donor_rows(donor_rows: Any, what: str) -> DonorRows:
    if not isinstance(donor_rows, DonorRows):
        raise WeightsRefusal("G-DONOR", "%s accepts only DonorRows (FitContext.donor_rows), got %s"
                             % (what, type(donor_rows).__name__))
    t = np.asarray(donor_rows.times)
    if t.size and int(t.max()) > int(donor_rows.cut):
        raise WeightsRefusal("G-FITCUT", "%d donor rows are after their cut %d"
                             % (int(np.count_nonzero(t > donor_rows.cut)), int(donor_rows.cut)))
    return donor_rows


def _require_blocks(blocks: Any, groups: Any, what: str) -> Any:
    """The overlap blocks, required (LORO L2 rule 4): derive_overlap_blocks' value, with every group
    that owns a tree or a row in a block (split.block_of_group refuses otherwise)."""
    if blocks is None:
        raise WeightsRefusal("R25", "%s needs the overlap blocks: under LORO the GLS target leaves out the "
                             "row's whole overlap block (owner rulings E, L2 rule 4); a group alone in "
                             "its block is passed as a one-group block, never assumed" % what,
                             fix="pass blocks=derive_overlap_blocks(...).value")
    for g in sorted({str(x) for x in groups}):
        _split.block_of_group(blocks, g)
    return blocks


def _block(group: str, blocks: Any) -> Tuple[str, ...]:
    return tuple(_split.block_of_group(blocks, group))


def _allowed_columns(tree_group: np.ndarray, group: str, blocks: Any) -> np.ndarray:
    block = _block(group, blocks)
    keep = np.flatnonzero(~np.isin(tree_group, np.asarray(block, dtype=object))).astype(np.int64)
    if keep.size == 0:
        raise WeightsRefusal("R25", "the rows of group %s have no tree from another group (block %s): a "
                             "single-group bank has no cross-region error" % (group, block))
    return keep


def _group_error(y: np.ndarray, answers: np.ndarray) -> np.ndarray:
    """|y - the float64 mean of the given tree answers| per row (the one formula)."""
    if not np.isfinite(answers).all():
        raise WeightsRefusal("R25", "a tree answer used by the cross-region error is missing or infinite")
    return np.abs(y - answers.astype(np.float64).mean(axis=1))


def _row_blocks(n_rows: int, n_columns: int) -> Tuple[Tuple[int, int], ...]:
    """Row blocks [a, b) over n_rows rows of a read with n_columns columns: P5.donor_block_values values a block, and
    never a block of ONE row unless n_rows is 1 (a trailing single row joins the block before it).

    Why no single row: the target's column selection values[:, where] (a fancy index on the columns) is F-ordered, so
    numpy's float64 mean over a row is a column-wise sum (column 0, then + column 1, + column 2, ...), the same order
    whatever the number of rows (2 or more). A selection of ONE row is C- and F-ordered at once and numpy sums it
    pairwise instead, which can differ in the last bit. With at least 2 rows a block keeps the whole group's order, so
    _blocked_group_error gives the whole group's bytes (tests/test_fit_weights_blocks.py, on values where the order
    shows; the 1-row block is planted there and differs)."""
    n = int(n_rows)
    step = max(int(K.DONOR_BLOCK_VALUES) // max(int(n_columns), 1), 2)
    cuts = list(range(0, n, step)) + [n]
    if len(cuts) > 2 and cuts[-1] - cuts[-2] == 1:
        del cuts[-2]
    return tuple(zip(cuts[:-1], cuts[1:]))


# Provenance: the GLS weight model's RAM (agent A's estimate, 2026-10-06: the donor matrix beside one group's whole
# 16-bytes-a-cell answer read, about 8.0 GiB at full-size NDVI); plan 1.7 (RAM decides go or refuse, never a number).
def _blocked_group_error(y: np.ndarray, values: np.ndarray, where: np.ndarray) -> np.ndarray:
    """_group_error(y, values[:, where]) in row blocks (_row_blocks over values' rows and columns): the same function on
    each block's rows, so the column copy and the float64 copy exist for one block at a time, never for the group.
    Every operation, dtype and reduction order is the whole group's (_row_blocks), so the bytes are the same; a
    missing or infinite answer is refused by the block that holds it, with _group_error's message."""
    out = np.empty(int(values.shape[0]), dtype=np.float64)
    for a0, b0 in _row_blocks(int(values.shape[0]), int(values.shape[1])):
        out[a0:b0] = _group_error(y[a0:b0], values[a0:b0][:, where])
    return out


# Provenance: plan 2.4 R25 ("the absolute gap between y and the mean of the trees from the OTHER donor
# groups"); coral_architecture.py:305-307 fitted in-sample residuals instead; D55, D56 (plain answers).
def cross_region_error(donor_rows: DonorRows, tree_answers: np.ndarray, tree_group: Tuple[str, ...], *,
                       blocks: Any) -> np.ndarray:
    """The weight model's target: |y - mean PLAIN answer of the trees outside the row's overlap
    block|, per donor row.

    Rule: R25 (D55, D56; LORO L2 rule 4). For a donor row of group g, average the answers of every tree
    whose group is not in g's overlap block (blocks, required keyword: derive_overlap_blocks' value),
    in float64, and take the absolute gap to y. Columns of g's own block are never read (they may hold
    NaN: the tree-answer store never computes a group's own trees).
    Returns float64 error per donor row (donor_rows order).
    Refuses: anything but DonorRows; no blocks, or a group of the rows or the bank in no block; a group
    whose rows have no tree outside its block (a single-block bank); shape mismatches; a missing or
    infinite answer in a column that is read.
    """
    donor = _donor_rows(donor_rows, "cross_region_error")
    y = np.asarray(donor.y, dtype=np.float64)
    A = np.asarray(tree_answers)
    groups = np.asarray(tuple(tree_group), dtype=object)
    if A.ndim != 2 or A.shape != (y.size, groups.size) or A.dtype.kind != "f":
        raise WeightsRefusal("R25", "tree answers have shape %s %s; the donor rows are %d and the bank %d "
                             "trees" % (A.shape, A.dtype, y.size, groups.size))
    row_group = np.asarray(donor.group_of_row, dtype=object)
    _require_blocks(blocks, set(row_group.tolist()) | set(groups.tolist()), "cross_region_error")
    out = np.empty(y.size, dtype=np.float64)
    for g in sorted(set(row_group.tolist())):
        idx = np.flatnonzero(row_group == g)
        cols = _allowed_columns(groups, g, blocks)
        out[idx] = _group_error(y[idx], A[idx][:, cols])
    return out


def _require_patched() -> None:
    try:
        import sklearnex
    except Exception as exc:
        raise WeightsRefusal("C14", "sklearnex could not be imported: %s" % exc,
                             fix="install the pinned scikit-learn-intelex") from exc
    if not sklearnex.sklearn_is_patched():
        raise WeightsRefusal("C14", "sklearn is not patched by sklearnex; the GLS forest is fitted only "
                             "in the state the launcher sets (owner ruling C)",
                             fix="start the engine through its launcher (py -3.9 -m treeroute)")


# Provenance: plan 2.4 R25, C13 (120 trees, depth 8, min leaf 20, max_features 1.0, bootstrap on,
# random_state 0, 4 pinned threads); coral_architecture.py:304; owner rulings E, L5 (c).
def fit_weight_model(donor_rows: DonorRows, error_target: np.ndarray) -> OobSigmaForest:
    """Fit the sigma model: a random forest from the kept tree features to the cross-region error.

    Rule: R25, G-DONOR, G-NODRAW (D57, L5 c). Engine constants only (C13 GLS_*); inputs are the donor
    rows' kept tree features (0-filled, R30), at or before the inner-fit end of the cut (the caller's
    guard context). The forest keeps its out-of-bag predictions on these rows (L5 c).
    Returns the fitted forest with its out-of-bag sigma (OobSigmaForest).
    Refuses: anything but DonorRows; rows after the cut; a length mismatch; a non-finite or negative
    target; sklearn not patched by sklearnex (C14); a fit in which a row has no out-of-bag tree.
    """
    donor = _donor_rows(donor_rows, "fit_weight_model")
    X = _features(donor.X, "the donor tree features")
    e = np.asarray(error_target, dtype=np.float64)
    if e.ndim != 1 or e.size != X.shape[0]:
        raise WeightsRefusal("R25", "the error target has %s values for %d donor rows" % (e.shape, X.shape[0]))
    if e.size == 0:
        raise WeightsRefusal("R25", "no donor row to fit the weight model on")
    if not np.isfinite(e).all() or (e < 0).any():
        raise WeightsRefusal("R25", "the error target must be finite and non-negative (an absolute gap)")
    _require_patched()
    from sklearn.ensemble import RandomForestRegressor

    forest = RandomForestRegressor(n_estimators=K.GLS_TREES, max_depth=K.GLS_MAX_DEPTH,
                                   min_samples_leaf=K.GLS_MIN_LEAF, max_features=K.GLS_MAX_FEATURES,
                                   bootstrap=K.GLS_BOOTSTRAP, random_state=K.GLS_RANDOM_STATE,
                                   n_jobs=K.GLS_THREADS, oob_score=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        forest.fit(X, e)
    oob_warnings = [str(w.message) for w in caught if "OOB" in str(w.message) or "oob" in str(w.message)]
    other = [w for w in caught if not ("OOB" in str(w.message) or "oob" in str(w.message))]
    for w in other:                               # never dropped: re-emitted, and recorded on the model
        warnings.warn_explicit(w.message, w.category, w.filename, w.lineno)
    if oob_warnings:
        raise WeightsRefusal("R25", "some donor rows have no out-of-bag tree (%s); L5 serves out-of-bag "
                             "sigma on every fitted row" % oob_warnings[0][:160],
                             fix="the weight model needs more donor rows per tree")
    oob = np.asarray(getattr(forest, "oob_prediction_", None), dtype=np.float64)
    if oob.shape != (e.size,) or not np.isfinite(oob).all():
        raise WeightsRefusal("R25", "the forest's out-of-bag predictions are missing or not finite")
    return OobSigmaForest(forest, donor.grid_rows, oob, donor.cut, donor.row_key_hash,
                          "%s.%s" % (type(forest).__module__, type(forest).__name__),
                          tuple("%s: %s" % (w.category.__name__, w.message) for w in other))


def _positive(x: Any, what: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (Real, np.floating, np.integer)) or \
            not math.isfinite(float(x)) or not float(x) > 0:
        raise WeightsRefusal("R25", "%s must be a finite positive number, got %r" % (what, x))
    return float(x)


# Provenance: plan 2.4 R25 ("sigma is floored at 1% of the donor spread (R36's s)"); D58 (identity-link s).
def sigma_floor(identity_link_s: float) -> float:
    """The floor on predicted sigma: 1% (C13 GLS_SIGMA_FLOOR_SHARE) of R36's identity-link s.

    Rule: R25, R36 (D58). Refuses: s <= 0 or non-finite (G-SUPPORT refuses a constant target
    earlier)."""
    return float(K.GLS_SIGMA_FLOOR_SHARE) * _positive(identity_link_s, "the identity-link donor spread s")


# Provenance: plan 2.4 R25 ("The clip bounds are the 5th and 95th percentiles of sigma on those donor
# rows, written to derived.json"); coral_architecture.py:311 took them from test rows (the defect); D59.
def sigma_clip_bounds(sigma_on_donor_rows: np.ndarray) -> Tuple[float, float]:
    """The clip bounds of sigma: its 5th and 95th percentiles (numpy linear, D59) on the donor rows the
    model was fitted on (after the floor).

    Rule: R25, G-DONOR. Donor rows only; never the frame being weighted.
    Returns (low, high). Refuses: fewer than 2 finite values; a non-positive bound.
    """
    s = np.asarray(sigma_on_donor_rows, dtype=np.float64)
    fin = s[np.isfinite(s)] if s.ndim == 1 else np.array([])
    if s.ndim != 1 or fin.size < 2:
        raise WeightsRefusal("R25", "the clip bounds need at least 2 finite sigma values on donor rows")
    q = [100.0 * float(v) for v in K.GLS_CLIP_QUANTILES]
    lo, hi = (float(v) for v in np.percentile(fin, q))
    if not (0 < lo <= hi):
        raise WeightsRefusal("R25", "the clip bounds (%r, %r) are not positive and ordered" % (lo, hi))
    return lo, hi


# Provenance: plan 2.4 R25 ("Weight = 1/sigma^2, with the max/min ratio capped at 100");
# coral_architecture.py:308-313; D60 (floor, then clip, then 1/sigma^2, then the cap).
def row_weights(sigma: np.ndarray, floor: float, clip_low: float, clip_high: float) -> np.ndarray:
    """Router row weights from predicted sigma: floor, clip, 1/sigma^2, max/min ratio capped at 100.

    Rule: R25 (D60). sigma is floored, clipped to the donor bounds and turned into weight = 1/sigma^2;
    the smallest weights are then raised to (largest / C13 GLS_WEIGHT_RATIO_CAP). Weights apply to
    router fit rows only. With equal sigma every weight is equal.
    Returns float64 weights. Refuses: non-finite sigma; no sigma; a floor or bound that is not finite
    and positive; clip_low > clip_high.
    """
    s = np.asarray(sigma, dtype=np.float64)
    if s.ndim != 1 or s.size == 0:
        raise WeightsRefusal("R25", "sigma must be a non-empty 1-D array")
    if not np.isfinite(s).all():
        raise WeightsRefusal("R25", "%d sigma values are missing or infinite"
                             % int(s.size - np.count_nonzero(np.isfinite(s))))
    f = _positive(floor, "the sigma floor")
    lo = _positive(clip_low, "the lower clip bound")
    hi = _positive(clip_high, "the upper clip bound")
    if lo > hi:
        raise WeightsRefusal("R25", "the clip bounds are reversed (%r > %r)" % (lo, hi))
    s = np.clip(np.maximum(s, f), lo, hi)
    w = 1.0 / s ** 2
    return np.maximum(w, w.max() / float(K.GLS_WEIGHT_RATIO_CAP))


# Provenance: plan 1.7 (disk and RAM decide only go or refuse; they never set a number); the per-group task's
# verified gap (2026-10-06): the GLS donor matrix, the donor-row pass's answer reads and the forest had no go/refuse.
def gls_ram_bytes(rows_of_group: Dict[str, int], n_columns: int, read_columns_of_group: Dict[str, int]) -> Dict[str, Any]:
    """The GLS weight model's RAM at its peaks (go/refuse only), in bytes, by part. rows_of_group: the donor rows of
    each group; n_columns: the tree columns of the donor matrix; read_columns_of_group: the answer columns the
    donor-row pass reads for each group's rows (the bank's trees less the group's own).
      matrix       the donor rows' tree features held whole (a fit over every group, R25), float32
      build        while the matrix is built in row blocks (fit.context FitContext._tree_feature_matrix): the matrix
                   beside ONE block's read and mask (build_block_rows = feature_block_rows rows x the columns x
                   P2.gls_matrix_build_bytes_per_value)
      answer_read  the matrix beside ONE group's answer read of the donor-row pass, the largest group's: the larger
                   of the store's read in flight (fit.tables TreeAnswerStore._read: its float32 output beside the
                   table's gathered rows, P2.gls_answer_read_bytes_per_cell a row x read column, and its row-index
                   arrays, P2.gls_answer_read_bytes_per_row a row) and, once it returns, that float32 output held
                   whole (4 bytes a cell) beside ONE row block's column copy and float64 copy (answer_block_rows =
                   the largest of that group's _row_blocks x its read columns x P2.gls_answer_block_bytes_per_cell)
      forest       the matrix beside the forest's fit (P2.gls_forest_bytes_per_value a value and
                   P2.gls_forest_bytes_per_row a row, measured)
      peak         the largest of build, answer_read and forest (they never coexist)
    The store's own row blocks while it builds a group's table are checked by the store (fit.tables). Not counted
    in build and answer_read: the donor rows' keys, labels, groups and target (8-byte values a row), and the
    row-key hash's text of the unit ids while the hand-out is made, once the matrix is built (about 135 bytes a
    row above the matrix, measured on the smokes). The build's bytes a value (P2.gls_matrix_build_bytes_per_value)
    assume a feature source that holds at most two float32 copies of its tree and context columns (and two row-index
    arrays) while it reads, with the context at most 1/8 of the tree columns less 2 (the constant's origin); a wider
    source's extra is at most one block's."""
    rows = int(sum(int(v) for v in rows_of_group.values()))
    n_cols = int(n_columns)
    values = rows * n_cols
    matrix = values * np.dtype(np.float32).itemsize
    held = np.dtype(np.float32).itemsize                  # the store's answers are float32 (its read's output)
    read_group, read, read_block = None, 0, 0
    for g in sorted(rows_of_group):
        r, c = int(rows_of_group[g]), int(read_columns_of_group[g])
        block = max([b - a for a, b in _row_blocks(r, c)] or [0])
        cells = max(r * c * int(K.GLS_ANSWER_READ_BYTES_PER_CELL)                    # the store's read in flight:
                    + r * int(K.GLS_ANSWER_READ_BYTES_PER_ROW),                      # cells and row-index arrays
                    r * c * held + block * c * int(K.GLS_ANSWER_BLOCK_BYTES_PER_CELL))  # its output + one block
        if cells > read:
            read_group, read, read_block = g, cells, block
    build_block = min(rows, feature_block_rows(n_cols))
    build = matrix + build_block * n_cols * int(K.GLS_MATRIX_BUILD_BYTES_PER_VALUE)
    forest = matrix + values * int(K.GLS_FOREST_BYTES_PER_VALUE) + rows * int(K.GLS_FOREST_BYTES_PER_ROW)
    return {"rows": rows, "columns": n_cols, "matrix": int(matrix), "build": int(build),
            "build_block_rows": int(build_block), "answer_read": int(matrix + read), "answer_read_group": read_group,
            "answer_block_rows": int(read_block), "forest": int(forest),
            "peak": int(max(build, matrix + read, forest))}


def _read_columns(tree_group: np.ndarray, groups: Any) -> Dict[str, int]:
    """The answer columns a group's table holds: every tree of the bank except the group's own."""
    return {str(g): int(np.count_nonzero(tree_group != g)) for g in groups}


def _file_backed(parts: Dict[str, Any]) -> Dict[str, Any]:
    """gls_ram_bytes' parts when the donor matrix is a temp memmap on the temp disk (RAM tactic 6): the matrix's own
    pages are file-backed (the system can drop them and read them back), so the build holds only its block and the
    answer read only its read in RAM; the forest's moment keeps the matrix's bytes, because the forest's fit copies
    its input into its own memory (measured: the fit's commit rise is the same with a memmap as with the matrix in
    RAM). matrix_file: the temp disk the file takes."""
    out = dict(parts)
    m = int(parts["matrix"])
    out["build"] = int(parts["build"]) - m
    out["answer_read"] = int(parts["answer_read"]) - m
    out["peak"] = int(max(out["build"], out["answer_read"], int(parts["forest"])))
    out["matrix_file"] = m
    return out


def _refuse_gls_ram(parts: Dict[str, Any], matrix_dir: Any = None) -> None:
    """The GLS weight model's go/refuse: the matrix file's temp disk (with matrix_dir), then the RAM peak. A refusal
    is marked as a shortage (runs.preflight.mark_shortage), so the in-run check may wait for room (runs.room)."""
    from treeroute.runs import preflight

    gib = float(1 << 30)
    if matrix_dir is not None:
        free_disk = preflight.free_disk_bytes(matrix_dir)
        if parts["matrix_file"] > free_disk:
            exc = WeightsRefusal("G-DISK", "the GLS weight model's (R25) donor matrix file of %d rows x %d tree columns "
                                 "needs %.2f GiB of temp disk at %s, %.2f GiB free: free %.2f GiB"
                                 % (parts["rows"], parts["columns"], parts["matrix_file"] / gib, matrix_dir,
                                    free_disk / gib, (parts["matrix_file"] - free_disk) / gib),
                                 fix="free disk on the temp drive; the run size is never reduced; the donor matrix "
                                     "was not built")
            raise preflight.mark_shortage(exc, need_disk=parts["matrix_file"], disk_path=matrix_dir)
    free = preflight.available_ram_bytes()
    if parts["peak"] > free:
        exc = WeightsRefusal("G-DISK", "the GLS weight model (R25) needs about %.2f GiB of RAM at its peak, %.2f GiB "
                             "available: the donor matrix of %d rows x %d tree columns (%.2f GiB, a fit over every "
                             "group) %.2f GiB while it is built, %.2f GiB beside group %s's answer read, %.2f GiB "
                             "beside the forest's fit; free %.2f GiB"
                             % (parts["peak"] / gib, free / gib, parts["rows"], parts["columns"],
                                parts["matrix"] / gib, parts["build"] / gib, parts["answer_read"] / gib,
                                parts["answer_read_group"], parts["forest"] / gib, (parts["peak"] - free) / gib)
                             + (" (the donor matrix itself is a file on the temp disk, outside these RAM figures "
                                "except the forest's own copy)" if matrix_dir is not None else ""),
                             fix="free RAM (close other programs); the run size is never reduced; the donor matrix "
                                 "was not built")
        raise preflight.mark_shortage(exc, need_ram=parts["peak"])


def _check_store(answers: Any, tree_group: np.ndarray) -> None:
    for name in ("build", "unit_view", "own_columns"):
        if not callable(getattr(answers, name, None)):
            raise WeightsRefusal("R25", "answers must be the tree-answer store (no %s())" % name)
    n = getattr(answers, "n_trees", None)
    if n != tree_group.size:
        raise WeightsRefusal("G-DISJOINT", "the store's bank holds %r trees, tree_group names %d"
                             % (n, tree_group.size))
    for g in sorted(set(tree_group.tolist())):
        if not np.array_equal(np.asarray(answers.own_columns(g), dtype=np.int64),
                              np.flatnonzero(tree_group == g)):
            raise WeightsRefusal("G-DISJOINT", "tree_group disagrees with the store's own trees for "
                                 "group %s (physical keys)" % g)


# Provenance: plan 2.4 R25 (per cut; per fold for neighbour; refit per lead only if the pinned arm is
# weighted); plan 4.5 (donor-row pass through the parallel writer); D57 (the lead's guard cut).
def weight_model_for_cut(fit_ctx: FitContext, guard_ctx: FitContext, answers: Any,
                         tree_group: Tuple[str, ...], *, blocks: Any, matrix_dir: Any = None,
                         echo: Any = None) -> WeightModel:
    """Build one cut's weight model end to end: donor rows, the donor-row pass, the error target, the
    forest, the floor and the clip bounds.

    Rule: R25, G-FITCUT, G-DONOR (D55-D60, L5 c; LORO L2 rule 4). The donor rows are
    guard_ctx.donor_rows('gls') (the lead's guard cut: the inner-fit end at lead 0). The donor-row pass
    builds each group's rows in the tree-answer store (plain table; the store computes every tree
    except the group's own, in parallel row blocks) and reads them back; answers come from the bank of
    fit_ctx's cut (the caller passes that store; L6_ANSWERS_DISCLOSURE is recorded). The target is
    cross_region_error's formula per group over the trees outside the row's overlap block (blocks,
    required keyword); the floor is sigma_floor of the donor rows' identity-link s (R36's
    guard_tolerance with k = 1: the standard deviation, ddof 0); the clip bounds come from the floored
    out-of-bag sigma on the same rows. Called at a forecast lead only when the pinned arm is weighted.
    Returns WeightModel (record it with weight_model_record).
    Refuses: contexts of different leads or folds; fit_ctx not a FIT context; guard_ctx not a GUARD
    context; no blocks, or a group in no block; a store whose trees disagree with tree_group; RAM: the
    model's peak (gls_ram_bytes: the donor matrix while it is built, beside the largest group's answer
    read, beside the forest) above the RAM available, once the donor rows are known and before their
    matrix is built (G-DISK; FitContext.donor_rows_checked, the same rows as donor_rows('gls')); anything
    its parts refuse.
    RAM: the donor matrix is built in row blocks into one float32 array (FitContext._tree_feature_matrix) and
    each group's target is computed in row blocks of its one store read (_blocked_group_error), the same bytes
    as in one piece; gls_ram_bytes counts these moments.
    RAM tactics (the RAM_TACTICS.md note of this engine change; none changes a byte): right before the donor matrix is
    built, memory is given back (runs.room.release_memory: gc and the working-set trim) and the RAM check waits for
    room (owner ruling Q1, runs.room.wait_for_room) instead of refusing at once. matrix_dir (the run's temp folder;
    None keeps the matrix in RAM): the donor matrix is a C-ordered float32 temp memmap there (runs.tempmem), written
    by the same row blocks; the forest's fit on it is byte-identical to the fit on the same values in RAM
    (tests/test_ram_tactics.py), and the file is deleted (loudly) before this returns or raises. echo: where the
    notes go (None: print).
    """
    say = print if echo is None else echo
    for what, ctx in (("fit_ctx", fit_ctx), ("guard_ctx", guard_ctx)):
        if not isinstance(ctx, FitContext):
            raise WeightsRefusal("R25", "%s must be a FitContext, got %s" % (what, type(ctx).__name__))
    if fit_ctx.lead != guard_ctx.lead:
        raise WeightsRefusal("R25", "fit_ctx is at lead %d, guard_ctx at lead %d" % (fit_ctx.lead, guard_ctx.lead))
    if fit_ctx.cut_kind is not CutKind.FIT or guard_ctx.cut_kind is not CutKind.GUARD:
        raise WeightsRefusal("R25", "fit_ctx must be the lead's FIT context and guard_ctx its GUARD context")
    groups_arr = np.asarray(tuple(tree_group), dtype=object)
    _check_store(answers, groups_arr)
    _require_blocks(blocks, set(groups_arr.tolist()) | set(guard_ctx.groups), "weight_model_for_cut")

    def ram_check(group_of_row: np.ndarray, n_columns: int) -> None:
        # RAM go/refuse once the donor rows are known, before their feature matrix is built (gls_ram_bytes); with
        # matrix_dir the matrix's own pages are file-backed (_file_backed) and its file needs the temp disk
        from treeroute.runs.room import release_memory, wait_for_room

        g_names, g_rows = np.unique(np.asarray(group_of_row, dtype=object).astype(str), return_counts=True)
        rows_of = {str(g): int(n) for g, n in zip(g_names.tolist(), g_rows.tolist())}
        parts = gls_ram_bytes(rows_of, n_columns, _read_columns(groups_arr, rows_of))
        if matrix_dir is not None:
            parts = _file_backed(parts)
        released = release_memory()                  # RAM tactics 2 and 3: right before the big step
        say("GLS weight model (R25): memory given back before the donor matrix (gc: %d objects; working-set trim "
            "%s); the matrix %s" % (released["gc_collected"], "ran" if released["trimmed"] else "did not run",
                                    "is a temp file at %s" % (matrix_dir,) if matrix_dir is not None else "is in RAM"))
        # the wait notes go to the run's echo (None: runs.room.stamped_print), each starting "[waiting]"
        wait_for_room(lambda: _refuse_gls_ram(parts, matrix_dir), "the GLS weight model's donor matrix (R25)", echo,
                      retry_on=(WeightsRefusal,))

    with ExitStack() as stack:
        alloc = None
        if matrix_dir is not None:
            from treeroute.runs.tempmem import temp_memmap

            tag = "gls_donor_l%d_c%d" % (int(guard_ctx.lead), int(guard_ctx.cut))

            def alloc(shape, dtype):
                return stack.enter_context(temp_memmap(matrix_dir, tag, shape, dtype)).array
        donor = X = features = None
        try:
            donor = guard_ctx.donor_rows_checked("gls", ram_check) if alloc is None else \
                guard_ctx.donor_rows_checked("gls", ram_check, alloc)
            y = np.asarray(donor.y, dtype=np.float64)
            row_group = np.asarray(donor.group_of_row, dtype=object)
            keys_all = np.asarray(donor.grid_rows, dtype=np.int64)
            X = donor.X

            def features(ids):
                pos = np.searchsorted(keys_all, np.asarray(ids, dtype=np.int64))
                return np.ascontiguousarray(X[pos])

            error = np.empty(y.size, dtype=np.float64)
            for g in sorted(set(row_group.tolist())):
                idx = np.flatnonzero(row_group == g)
                keys = keys_all[idx]
                answers.build(g, "plain", keys, features)
                view = answers.unit_view(keys, "plain")
                index = np.asarray(view.tree_index, dtype=np.int64)
                cols = _allowed_columns(groups_arr, g, blocks)
                where = np.searchsorted(index, cols)
                where_c = np.minimum(where, max(index.size - 1, 0))
                if index.size == 0 or not np.array_equal(index[where_c], cols):
                    raise WeightsRefusal("G-DISJOINT", "the store does not answer every tree outside group %s's "
                                         "block for its rows" % g)
                values = np.asarray(view.values)
                error[idx] = _blocked_group_error(y[idx], values, where_c)
                del view, values
            from treeroute.runs.room import release_memory

            released = release_memory()              # RAM tactics 2 and 3: before the forest copies its input
            say("GLS weight model (R25): memory given back before the forest's fit (gc: %d objects; working-set trim "
                "%s)" % (released["gc_collected"], "ran" if released["trimmed"] else "did not run"))
            forest = fit_weight_model(donor, error)
            forest.blocks_members = tuple(tuple(_block(g, blocks)) for g in sorted(set(row_group.tolist())))
            forest.answers_cut = int(fit_ctx.cut)
            floor = sigma_floor(_metrics.guard_tolerance(donor, Link.IDENTITY, None, None, 1.0))
            lo, hi = sigma_clip_bounds(np.maximum(forest.oob_sigma, floor))
            donor_cut = int(donor.cut)
        except BaseException as exc:
            # drop this frame's aliases of a temp memmap and the finished frames' locals in the traceback, so the
            # file's loud release (runs.tempmem) can delete it and this exception is the one that propagates
            donor = X = features = None
            traceback.clear_frames(exc.__traceback__)
            raise
        donor = X = features = None                  # the memmap's last aliases go before its release
    return WeightModel(forest=forest, cut=donor_cut, lead=int(fit_ctx.lead), sigma_floor=floor,
                       clip_low=lo, clip_high=hi, fold=-1)


def weights_for_rows(model: WeightModel, grid_rows: np.ndarray, X: np.ndarray) -> np.ndarray:
    """The GLS weights of a router's fit rows: the model's sigma on those rows (out-of-bag on the rows
    it was fitted on, L5 c), then row_weights with the model's floor and clip bounds."""
    if not isinstance(model, WeightModel) or not isinstance(model.forest, OobSigmaForest):
        raise WeightsRefusal("R25", "weights come from a WeightModel built by weight_model_for_cut")
    return row_weights(model.forest.sigma(grid_rows, X), model.sigma_floor, model.clip_low,
                       model.clip_high)


def weight_model_record(model: WeightModel) -> Any:
    """The derived.json entry of a weight model ('R25:lead=<lead>'): its cut, lead, floor, clip bounds,
    the donor rows' count and row-key hash, the overlap block of each donor group, the answers' bank
    cut with L6_ANSWERS_DISCLOSURE, the fit's other warnings, the forest's implementation and the
    engine constants. Refuses a model weight_model_for_cut did not build."""
    if not isinstance(model, WeightModel) or not isinstance(model.forest, OobSigmaForest) \
            or model.forest.blocks_members is None or model.forest.answers_cut is None:
        raise WeightsRefusal("R25", "weight_model_record takes weight_model_for_cut's WeightModel")
    f = model.forest
    inputs: Dict[str, Any] = {
        "cut": model.cut, "lead": model.lead, "fold": model.fold, "donor_rows": int(f.grid_rows.size),
        "sigma_floor": model.sigma_floor, "clip_low": model.clip_low, "clip_high": model.clip_high,
        "sigma_served": "out-of-bag on the fitted donor rows, the whole forest elsewhere (L5 c)",
        "implementation": f.implementation, "trees": f.n_trees,
        "blocks": [list(b) for b in f.blocks_members],
        "blocks_sha256": sha256_of_json([list(b) for b in f.blocks_members]),
        "answers_bank_cut": f.answers_cut, "answers_bank": L6_ANSWERS_DISCLOSURE,
        "fit_warnings": list(f.fit_warnings),
        "constants": {cid: K.get(cid) for cid in (
            "C13.gls_trees", "C13.gls_max_depth", "C13.gls_min_leaf", "C13.gls_max_features",
            "C13.gls_bootstrap", "C13.gls_random_state", "C13.gls_threads",
            "C13.gls_sigma_floor_share", "C13.gls_clip_quantiles", "C13.gls_weight_ratio_cap")}}
    return make_derived("R25", {"sigma_floor": model.sigma_floor, "clip_low": model.clip_low,
                                "clip_high": model.clip_high}, inputs,
                        {"donor_row_key_hash": f.row_key_hash})


__all__ = ["WeightsRefusal", "WeightModel", "OobSigmaForest", "L6_ANSWERS_DISCLOSURE", "cross_region_error",
           "fit_weight_model", "sigma_floor", "sigma_clip_bounds", "row_weights", "weight_model_for_cut",
           "weights_for_rows", "weight_model_record", "gls_ram_bytes"]
