"""The lean common-rival learners: one fit, staged predictions on the score sets (SPEC_RIVALS 3.2-3.4).

Plug and predict: nothing here names a problem. A learner sees a fit set (raw feature matrix, labels,
the link-space normals) and score sets, and returns PRE-CLIP predictions in y units at each
checkpoint. The harness clips with the engine's own clip and scores with the engine's own metrics.

Rules kept here (spec section 3.3):
  - tree learners (rf, lgbm, lgbm_tweedie, hgb_l1): NaN -> 0.0 (the engine's R30 0-fill);
  - ridge: NaN -> the fit rows' column mean, one 0/1 missing flag per column with any NaN in the
    fit rows, then standardised on the fit rows (sd 0 -> column dropped, recorded);
  - the normal of the trial's link is BOTH a fixed offset and the last feature column (Q16 a);
  - lgbm, rf, ridge, hgb_l1: target link(y) - normal, prediction normal + f(X) (for lgbm the
    same fit as label link(y) with init_score = the normal; see _fit_lgbm); lgbm_tweedie: label y,
    init_score = log(max(identity normal, c)), prediction exp(init + raw);
  - link forward and inverse are the engine's layer.links functions (no smearing);
  - random_state / seed 0 and 8 threads everywhere, never varied;
  - rf runs out of core (ruling Z2): all fit rows, each tree its own drawn sample, the fit file read in
    row blocks, RAM within RF_RAM_BUDGET (section "Random forest, out of core");
  - lgbm and lgbm_tweedie TUNING trials (ruling AA2) stop early on the score set the caller names (the
    harness names the inner window) after PATIENCE_ROUNDS rounds without a strictly lower metric, inside the cap;
    every LightGBM fit, tuning and final, bins into LGBM_MAX_BIN (255, LightGBM's default) bins (ruling AC1, which
    withdrew the 63-bin tuning of AA3); a final fit runs a fixed round count with no early stopping.
"""
# Provenance: SPEC_RIVALS.md 3.2-3.4 (D:/treeroute/rivals_build); RIVALS_PLAN_COMMON.md 2a, rule 5,
# rule 9, rule 10; OWNER_RULINGS_2026-10-06.md Y1-Y3, Z2 (RF out of core; the R5 max_samples rule is moot:
# every tree is fitted with bootstrap off on its own drawn sample).

import itertools
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

# ---------------------------------------------------------------------------------------------------
# Fixed board constants (recorded in board.json by the harness).
THREADS = 8
RANDOM_STATE = 0
LEARNING_RATE = 0.1
BASE_ROUNDS = (100, 200, 400, 800)
EXTENSION_ROUNDS = (1200, 1600)
EDGE_ROUNDS = BASE_ROUNDS[-1]            # the 800 cap (Y2 extension: a staged best here; AC2: an early-stopped trial run to it)
LAST_ROUNDS = EXTENSION_ROUNDS[-1]       # a pick here is flagged, never extended
RIDGE_ALPHAS = (0.1, 1.0, 10.0, 100.0, 1e3, 1e4, 1e5, 1e6)
RF_TREES = 300
RF_ROWS_PER_TREE = 200000
# Random forest out of core (ruling Z2, replaces the bank-unit stride of Q9 b): every RF fit sees ALL fit-set
# rows; each tree draws its own sample of min(RF_ROWS_PER_TREE, n_fit) rows (with replacement, a bootstrap)
# from ONE np.random.default_rng(RANDOM_STATE); the fit set stays on disk as the row-major float32 memmap and
# is read in sequential row blocks; the RF's RAM stays within RF_RAM_BUDGET (see _rf_budget).
RF_METHOD = "out_of_core/1"
RF_RAM_BUDGET = 4.5 * (1 << 30)
RF_FIT_FACTOR = 1.5                      # one oneDAL tree fit adds ~1.3-1.4 x its sample's bytes (measured)
RF_READ_BLOCK_BYTES = 64 << 20           # one sequential read of the fit file
RF_PRED_BLOCK_ROWS = 65536               # score rows per predict call
RF_SLACK_BYTES = 512 << 20               # one fitted tree, predict temporaries, small arrays
RF_CKPT_EVERY = 10                       # trees between two checkpoints (when the caller gives a store)
RF_SEED_HIGH = 2 ** 31 - 1               # each tree's random_state is drawn in [0, RF_SEED_HIGH)
# The in-RAM peak factor of hgb_l1 (it still fits one in-RAM matrix; harness ram_check).
RF_PEAK_FACTOR = 2.6
TWEEDIE_POWERS = (1.2, 1.5)
GIB = float(1 << 30)
# LightGBM tuning rules (owner rulings AA2, AC1, AC2; pre-registered):
#   - early stopping (AA2): a TUNING trial of lgbm / lgbm_tweedie scores the inner window after every round (the
#     engine's MAE of the clipped prediction, given by the harness) and stops once PATIENCE_ROUNDS rounds in a row
#     bring no strictly lower MAE, inside its cap (800; 1600 when extended). Its pick is its best round (ties: the
#     earlier).
#   - extension (AC2, amends Y2/Z3 b and AA2): only a trial that ran to the 800 cap WITHOUT a patience stop is
#     extended (its best round then lies in the last stage before the cap, (400, 800]; with patience 150 in fact in
#     (650, 800]); a trial stopped by patience is never extended (its extension would repeat it unchanged). See
#     ran_to_cap.
#   - bins (AC1, replaces AA3): every LightGBM fit, the tuning trials and every final fit (the refit at the fit cut
#     and every guard fit), uses LightGBM's default LGBM_MAX_BIN (255) histogram bins. The 63-bin tuning of AA3 is
#     withdrawn (its code is in _moved/20261021_preAC_code): a round count picked at 63 bins did not carry to a
#     255-bin refit.
EARLY_STOP_LEARNERS = ("lgbm", "lgbm_tweedie")
PATIENCE_ROUNDS = 150                    # owner ruling AD (2026-10-21; was 50 under AA2)
LGBM_MAX_BIN = 255                       # LightGBM's default max_bin; tuning and final fits alike (AC1)
LAST_STAGE_FROM = BASE_ROUNDS[-2]        # the last stage before the 800 cap, (400, 800]
LAST_EXT_STAGE_FROM = EXTENSION_ROUNDS[-2]   # a best round in (1200, 1600] is flagged edge_rounds_1600

LEARNERS = ("ridge", "rf", "lgbm", "lgbm_tweedie", "hgb_l1")
CORE_LEARNERS = ("ridge", "rf", "lgbm")
STAGED_LEARNERS = ("lgbm", "lgbm_tweedie", "hgb_l1")
LOSS = {"ridge": "squared_error", "rf": "squared_error", "lgbm": "squared_error",
        "lgbm_tweedie": "tweedie", "hgb_l1": "absolute_error"}

LGBM_FIXED = {
    "learning_rate": LEARNING_RATE,
    "feature_fraction": 0.5,
    "bagging_fraction": 1.0,
    "bagging_freq": 0,
    "deterministic": True,
    "force_row_wise": True,
    "feature_pre_filter": False,
    "num_threads": THREADS,
    "seed": RANDOM_STATE,
    "verbose": -1,
}
# Dataset (binning) parameters: the same for every trial that reuses a binned fit set.
LGBM_DATASET_PARAMS = {
    "feature_pre_filter": False,
    "verbose": -1,
    "num_threads": THREADS,
    "seed": RANDOM_STATE,
    "deterministic": True,
}
SEQUENCE_BATCH_ROWS = 65536
RIDGE_BLOCK_ROWS = 65536


class ModelRefusal(RuntimeError):
    """A learner refused its inputs. Nothing catches it (fail loud)."""


# ---------------------------------------------------------------------------------------------------
# Grids (spec 3.4), in the fixed grid order used for tie breaks.
def grid(learner: str) -> List[Dict[str, Any]]:
    """The settings of one learner in grid order (the link loop is the harness's)."""
    if learner == "ridge":
        return [{}]
    if learner == "rf":
        return [{"max_features": mf, "min_samples_leaf": msl}
                for mf, msl in itertools.product((0.2, 0.5), (5, 50))]
    if learner == "lgbm":
        return [{"num_leaves": nl, "min_child_samples": mcs}
                for nl, mcs in itertools.product((31, 127), (20, 200))]
    if learner == "lgbm_tweedie":
        return [dict(s, tweedie_variance_power=p)
                for s, p in itertools.product(grid("lgbm"), TWEEDIE_POWERS)]
    if learner == "hgb_l1":
        return [{"max_leaf_nodes": ml, "min_samples_leaf": msl}
                for ml, msl in itertools.product((31, 127), (20, 200))]
    raise ModelRefusal("unknown learner %r (known: %s)" % (learner, ", ".join(LEARNERS)))


def checkpoints(learner: str, extended: bool = False) -> Tuple[Any, ...]:
    """The checkpoints of one fit: alphas for ridge, tree count for rf, rounds for the boosters."""
    if learner == "ridge":
        return RIDGE_ALPHAS
    if learner == "rf":
        return (RF_TREES,)
    if learner in STAGED_LEARNERS:
        return BASE_ROUNDS + (EXTENSION_ROUNDS if extended else ())
    raise ModelRefusal("unknown learner %r" % (learner,))


def uses_links(learner: str) -> bool:
    """lgbm_tweedie has its own log link (no link loop); every other learner loops over R22 links."""
    return learner != "lgbm_tweedie"


def fixed_params(learner: str) -> Dict[str, Any]:
    """The fixed (non-grid) parameters, for board.json."""
    if learner == "ridge":
        return {"solver": "float64 X'X, chunked, numpy cholesky", "alphas": list(RIDGE_ALPHAS),
                "imputation": "fit-row mean + missing flags", "scaling": "fit-row mean and sd",
                "intercept": "unpenalised"}
    if learner == "rf":
        return {"library": "sklearnex", "method": RF_METHOD, "trees": RF_TREES,
                "tree": "RandomForestRegressor(n_estimators=1, bootstrap=False, criterion='squared_error', "
                        "n_jobs=%d) per tree, fitted on that tree's own sample" % THREADS,
                "rows_per_tree": "min(%d, n_fit), drawn with replacement" % RF_ROWS_PER_TREE,
                "draws": "one np.random.default_rng(%d); per tree in order: rows = integers(0, n_fit, "
                         "rows_per_tree) sorted, then random_state = integers(0, %d)" % (RANDOM_STATE, RF_SEED_HIGH),
                "prediction": "sum of the trees' predictions in tree order / trees (float64)",
                "ram_budget_bytes": RF_RAM_BUDGET, "fit_factor": RF_FIT_FACTOR,
                "read_block_bytes": RF_READ_BLOCK_BYTES}
    if learner == "lgbm":
        return dict(LGBM_FIXED, objective="regression", rounds=list(BASE_ROUNDS),
                    extension=list(EXTENSION_ROUNDS), tuning=tuning_options(learner),
                    final_fit=final_fit_options(learner))
    if learner == "lgbm_tweedie":
        return dict(LGBM_FIXED, objective="tweedie", rounds=list(BASE_ROUNDS),
                    extension=list(EXTENSION_ROUNDS), tuning=tuning_options(learner),
                    final_fit=final_fit_options(learner))
    if learner == "hgb_l1":
        return {"loss": "absolute_error", "learning_rate": LEARNING_RATE,
                "max_iter": "the largest checkpoint", "early_stopping": False,
                "random_state": RANDOM_STATE, "rounds": list(BASE_ROUNDS),
                "extension": list(EXTENSION_ROUNDS)}
    raise ModelRefusal("unknown learner %r" % (learner,))


def tuning_options(learner: str, extended: bool = False) -> Optional[Dict[str, Any]]:
    """The tuning-only options of a learner (early stopping, its extension rule and the bins), None for a learner
    without any. Part of every trial's config hash and of board.json."""
    if learner not in EARLY_STOP_LEARNERS:
        return None
    return {"early_stopping": "inner-window MAE of the clipped prediction after every round; stop after %d "
                              "rounds in a row without a strictly lower MAE" % PATIENCE_ROUNDS,
            "patience_rounds": PATIENCE_ROUNDS,
            "cap_rounds": int(EXTENSION_ROUNDS[-1] if extended else BASE_ROUNDS[-1]),
            "pick": "the trial's best round (ties: the earlier round)",
            "extension": "AC2: only a trial that ran to the %d cap without a patience stop (its best round then in "
                         "(%d, %d]) is refit from scratch with cap %d; a trial stopped by patience is never extended"
                         % (EDGE_ROUNDS, LAST_STAGE_FROM, EDGE_ROUNDS, LAST_ROUNDS),
            "max_bin": LGBM_MAX_BIN}


def final_fit_options(learner: str) -> Optional[Dict[str, Any]]:
    """The options of every final fit of a learner (the refit and the guard fits), None for a learner without
    tuning-only options. For lgbm / lgbm_tweedie the bins equal the tuning's (AC1); a final fit only drops the early
    stopping and runs the picked round count, so the tuning trial at that round IS the final model fitted on the
    tune rows (the lead-0 guard model)."""
    if learner not in EARLY_STOP_LEARNERS:
        return None
    return {"max_bin": LGBM_MAX_BIN, "rounds": "the picked round count", "early_stopping": None}


def ran_to_cap(early_stopping: Mapping[str, Any]) -> bool:
    """AC2: whether an early-stopped tuning trial ran to its cap without a patience stop (only such a trial is
    extended). early_stopping: the trial's early-stopping record (info['early_stopping'] of _fit_lgbm, saved in
    trial.json). Fails loud on a record that is missing a field or contradicts itself (not stopped by patience but
    fewer training iterations than the cap)."""
    if not isinstance(early_stopping, Mapping):
        raise ModelRefusal("ran_to_cap: no early-stopping record (%r)" % (early_stopping,))
    for k in ("stopped_by_patience", "iterations_run", "cap_rounds"):
        if k not in early_stopping:
            raise ModelRefusal("ran_to_cap: the early-stopping record has no %r" % k)
    if bool(early_stopping["stopped_by_patience"]):
        return False
    if int(early_stopping["iterations_run"]) != int(early_stopping["cap_rounds"]):
        raise ModelRefusal("ran_to_cap: not stopped by patience, yet %s iterations ran against a cap of %s"
                           % (early_stopping["iterations_run"], early_stopping["cap_rounds"]))
    return True


def in_last_stage(ck: Any, extended: bool = False) -> bool:
    """A round count in the last stage before the cap: (400, 800], or (1200, 1600] for an extended trial."""
    lo, hi = (LAST_EXT_STAGE_FROM, LAST_ROUNDS) if extended else (LAST_STAGE_FROM, EDGE_ROUNDS)
    return float(lo) < float(ck) <= float(hi)


# ---------------------------------------------------------------------------------------------------
# RF rows per tree (ruling Z2; the bank-unit stride of Q9 b is gone, its code is in _moved)
def rf_rows_per_tree(n_fit: int) -> int:
    """The sample size of every tree: min(RF_ROWS_PER_TREE, n_fit) rows, drawn with replacement."""
    if n_fit <= 0:
        raise ModelRefusal("an RF fit needs at least one row")
    return int(min(int(RF_ROWS_PER_TREE), int(n_fit)))


# ---------------------------------------------------------------------------------------------------
# Data containers
@dataclass
class FitData:
    """One fit set. X: rows x p float32 RAW features (NaN kept; a memmap is fine), in column order;
    y: float64 labels; normal: {link value: float64 link-space normal per row} (must hold
    'identity'); rows: optional increasing row positions to use, None = every row (the harness
    always passes None; the RF draws its own rows per tree)."""
    name: str
    X: Any
    columns: Tuple[str, ...]
    y: np.ndarray
    normal: Mapping[str, np.ndarray]
    rows: Optional[np.ndarray] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoreData:
    """One score set: X rows x p float32 RAW (same columns as the fit set); normal as FitData."""
    name: str
    X: Any
    normal: Mapping[str, np.ndarray]


def _check_set(s: Any, p: int, what: str) -> int:
    X = s.X
    if getattr(X, "ndim", None) != 2 or X.shape[1] != p:
        raise ModelRefusal("%s: X must be rows x %d, got shape %s" % (what, p, getattr(X, "shape", None)))
    n = int(X.shape[0])
    for link, v in s.normal.items():
        v = np.asarray(v)
        if v.shape != (n,):
            raise ModelRefusal("%s: the %s normal has shape %s for %d rows" % (what, link, v.shape, n))
        if not np.isfinite(v).all():
            raise ModelRefusal("%s: the %s normal holds %d non-finite values; a normal exists on every "
                               "row a rival fits or scores" % (what, link, int((~np.isfinite(v)).sum())))
    return n


def _link_enum(link: str):
    from treeroute.derive.shapes import Link
    return Link(link)


def link_forward(y: np.ndarray, link: str, c: Optional[float], ub: Optional[float]) -> np.ndarray:
    """The engine's R22 forward link (layer/links.py:84)."""
    from treeroute.layer import links as L
    return L.link_forward(np.asarray(y, dtype=np.float64), _link_enum(link), c, ub)


def link_inverse(z: np.ndarray, link: str, c: Optional[float], ub: Optional[float]) -> np.ndarray:
    """The engine's R22 inverse link (layer/links.py:118); no smearing."""
    from treeroute.layer import links as L
    return L.link_inverse(np.asarray(z, dtype=np.float64), _link_enum(link), c, ub)


def _zero_fill(block: np.ndarray) -> np.ndarray:
    """R30 0-fill of one float block (a copy). Infinite values are refused (the export asserts none)."""
    out = np.array(block, dtype=np.float32, copy=True)
    if np.isinf(out).any():
        raise ModelRefusal("a feature block holds %d infinite values" % int(np.isinf(out).sum()))
    out[np.isnan(out)] = 0.0
    return out


def _tree_matrix(X: Any, rows: Optional[np.ndarray], normal_col: np.ndarray) -> np.ndarray:
    """In-RAM 0-filled float32 matrix [X | normal column] of the rows given (None = all)."""
    n = int(X.shape[0]) if rows is None else int(rows.size)
    p = int(X.shape[1])
    out = np.empty((n, p + 1), dtype=np.float32)
    step = RIDGE_BLOCK_ROWS
    for a in range(0, n, step):
        b = min(n, a + step)
        src = X[a:b] if rows is None else X[rows[a:b]]
        out[a:b, :p] = _zero_fill(src)
    nc = np.asarray(normal_col, dtype=np.float64)
    out[:, p] = (nc if rows is None else nc[rows]).astype(np.float32)
    return out


# ---------------------------------------------------------------------------------------------------
# What a trial predicts in link space and how it returns to y units
def _target_and_offset(learner: str, params: Mapping[str, Any], s: Any, y: Optional[np.ndarray]):
    """(column normal, offset z0, label for the fit or None) for one set under one trial."""
    c, ub = params.get("c"), params.get("ub")
    if learner == "lgbm_tweedie":
        nid = np.asarray(s.normal["identity"], dtype=np.float64)
        cc = float(c) if c is not None else float("nan")
        if not (math.isfinite(cc) and cc > 0):
            raise ModelRefusal("lgbm_tweedie needs the run's c > 0 (R23), got %r" % (c,))
        z0 = np.log(np.maximum(nid, cc))
        label = None
        if y is not None:
            label = np.asarray(y, dtype=np.float64)
            if (label < 0).any():
                raise ModelRefusal("lgbm_tweedie needs labels >= 0; %d are below 0" % int((label < 0).sum()))
        return nid, z0, label
    link = params["link"]
    if link not in s.normal:
        raise ModelRefusal("%s: no %s normal on set %s" % (learner, link, s.name))
    z0 = np.asarray(s.normal[link], dtype=np.float64)
    label = None
    if y is not None:
        label = link_forward(y, link, c, ub) - z0
    return z0, z0, label


def _to_y(learner: str, params: Mapping[str, Any], z0: np.ndarray, f: np.ndarray) -> np.ndarray:
    """Pre-clip y-unit prediction from the offset and the learner's raw output."""
    z = np.asarray(z0, dtype=np.float64) + np.asarray(f, dtype=np.float64)
    if learner == "lgbm_tweedie":
        with np.errstate(over="raise"):
            try:
                return np.exp(z)
            except FloatingPointError:
                raise ModelRefusal("lgbm_tweedie: exp overflowed on %d rows" % int((z > 700).sum()))
    return link_inverse(z, params["link"], params.get("c"), params.get("ub"))


# ---------------------------------------------------------------------------------------------------
# LightGBM
class _ZeroFillSequence(object):
    """lgb.Sequence over a raw float32 matrix (memmap): 0-fill, the normal column appended,
    float64 batches (LightGBM's sample reader wants double)."""

    def __init__(self, X: Any, normal_col: np.ndarray, rows: Optional[np.ndarray]):
        self.X = X
        self.normal_col = np.asarray(normal_col, dtype=np.float64)
        self.rows = rows
        self.batch_size = SEQUENCE_BATCH_ROWS

    def __len__(self):
        return int(self.X.shape[0]) if self.rows is None else int(self.rows.size)

    def __getitem__(self, idx):
        if isinstance(idx, (int, np.integer)):
            r = int(idx) if self.rows is None else int(self.rows[int(idx)])
            out = np.empty(self.X.shape[1] + 1, dtype=np.float64)
            v = np.array(self.X[r], dtype=np.float64)
            if np.isinf(v).any():
                raise ModelRefusal("row %d holds an infinite value" % r)
            v[np.isnan(v)] = 0.0
            out[:-1] = v
            out[-1] = self.normal_col[r]
            return out
        if isinstance(idx, slice):
            pos = np.arange(len(self))[idx]
        else:
            pos = np.asarray(idx)
        src = pos if self.rows is None else self.rows[pos]
        if src.size and np.all(np.diff(src) == 1):
            block = self.X[int(src[0]):int(src[-1]) + 1]
        else:
            block = self.X[src]
        out = np.empty((src.size, self.X.shape[1] + 1), dtype=np.float64)
        out[:, :-1] = _zero_fill(block)
        out[:, -1] = self.normal_col[src]
        return out


def _make_sequence(X, normal_col, rows):
    import lightgbm as lgb

    class _Seq(_ZeroFillSequence, lgb.Sequence):
        pass

    return _Seq(X, normal_col, rows)


def lgbm_dataset(fit_set: FitData, column_link: str, cache: Optional[Dict[Any, Any]] = None,
                 max_bin: int = LGBM_MAX_BIN):
    """The binned Dataset of one fit set with the normal of column_link as its last column, built
    once (bins from the fit set's own rows, max_bin histogram bins) and reused across settings with set_label /
    set_init_score."""
    import lightgbm as lgb
    key = ("lgbm_dataset", fit_set.name, id(fit_set), column_link, int(max_bin))
    if cache is not None and key in cache:
        return cache[key]
    if cache is not None:
        # keep one binned set at a time (RAM): drop the other links' Datasets of any fit set
        for k in [k for k in cache if isinstance(k, tuple) and k and k[0] == "lgbm_dataset"]:
            del cache[k]
    seq = _make_sequence(fit_set.X, fit_set.normal[column_link], fit_set.rows)
    n = len(seq)
    ds = lgb.Dataset([seq], label=np.zeros(n), init_score=np.zeros(n),
                     params=dict(LGBM_DATASET_PARAMS, max_bin=int(max_bin)), free_raw_data=False)
    ds.construct()
    if cache is not None:
        cache[key] = ds
    return ds


@dataclass
class EarlyStop:
    """Early stopping of one TUNING trial (lgbm, lgbm_tweedie; ruling AA2). score_set: the name of the score set
    whose metric decides (the harness passes the inner window, never a test set); metric(pre) -> float: the
    metric of the pre-clip y-unit prediction, lower is better (the harness clips and takes the engine's MAE);
    patience: rounds in a row without a strictly lower value before the trial stops; also_save: extra round
    counts whose predictions are kept (an extended trial keeps its base trial's rounds for the prefix check)."""
    score_set: str
    metric: Any
    patience: int = PATIENCE_ROUNDS
    also_save: Tuple[int, ...] = ()


_ZERO_THRESHOLD = 1e-35                  # LightGBM's kZeroThreshold (a value with |v| <= it is "zero")


def _tree_output(tree: Mapping[str, Any], X: np.ndarray) -> np.ndarray:
    """One LightGBM tree's raw output on the rows of X (float32 [features | normal], 0-filled), from the tree's
    dump_model record: numerical splits only, value <= threshold goes left (LightGBM's NumericalDecision, the
    value taken as double; a missing-type 'Zero' or 'NaN' row follows default_left). The same leaf values the
    library's own predict adds (checked bit for bit by _fit_lgbm at every kept round)."""
    root = tree["tree_structure"]
    n = int(X.shape[0])
    if "leaf_value" in root and "split_feature" not in root:
        return np.full(n, float(root["leaf_value"]), dtype=np.float64)
    nodes, leaves = {}, {}
    stack = [root]
    while stack:
        nd = stack.pop()
        if "split_feature" not in nd:
            leaves[int(nd.get("leaf_index", 0))] = float(nd["leaf_value"])
            continue
        if nd.get("decision_type") != "<=":
            raise ModelRefusal("early stopping: a split of decision type %r (numerical '<=' only)"
                               % (nd.get("decision_type"),))
        kids = []
        for side in ("left_child", "right_child"):
            ch = nd[side]
            kids.append(int(ch["split_index"]) if "split_feature" in ch else ~int(ch.get("leaf_index", 0)))
            stack.append(ch)
        nodes[int(nd["split_index"])] = (int(nd["split_feature"]), float(nd["threshold"]), kids[0], kids[1],
                                         bool(nd["default_left"]), str(nd.get("missing_type", "None")))
    m = max(nodes) + 1
    feat = np.zeros(m, dtype=np.int64)
    thr = np.zeros(m, dtype=np.float64)
    left = np.zeros(m, dtype=np.int64)
    right = np.zeros(m, dtype=np.int64)
    dleft = np.zeros(m, dtype=bool)
    mzero = np.zeros(m, dtype=bool)
    mnan = np.zeros(m, dtype=bool)
    for k, (f, t, a, b, dl, mt) in nodes.items():
        feat[k], thr[k], left[k], right[k], dleft[k] = f, t, a, b, dl
        mzero[k], mnan[k] = mt == "Zero", mt == "NaN"
    lv = np.zeros(max(leaves) + 1, dtype=np.float64)
    for k, v in leaves.items():
        lv[k] = v
    out = np.empty(n, dtype=np.float64)
    active = np.arange(n, dtype=np.int64)
    node = np.zeros(n, dtype=np.int64)
    while active.size:
        nd = node[active]
        v = np.asarray(X[active, feat[nd]], dtype=np.float64)
        isnan = np.isnan(v)
        v = np.where(isnan & ~mnan[nd], 0.0, v)
        special = (mzero[nd] & (np.abs(v) <= _ZERO_THRESHOLD)) | (mnan[nd] & isnan)
        go_left = np.where(special, dleft[nd], v <= thr[nd])
        child = np.where(go_left, left[nd], right[nd])
        leaf = child < 0
        out[active[leaf]] = lv[~child[leaf]]
        node[active[~leaf]] = child[~leaf]
        active = active[~leaf]
    return out


class _RoundScorer(object):
    """lgb.train callback: after round r, adds tree r's raw output on the early-stop set to a float64 sum (the
    same additions, in the same order, as booster.predict(num_iteration=r) makes), scores it and raises
    EarlyStopException once `patience` rounds in a row bring no strictly lower metric. The tree's output is read
    from its dump_model record (_tree_output): calling the library's predict between two training rounds slows
    every later round about a hundredfold on this machine (measured), so it is not used here."""
    order = 30
    before_iteration = False

    def __init__(self, learner, params, Xe, z0e, metric, patience):
        self.learner, self.params, self.Xe, self.z0e = learner, params, Xe, z0e
        self.metric, self.patience = metric, int(patience)
        self.acc = np.zeros(int(Xe.shape[0]), dtype=np.float64)
        self.trace: List[float] = []        # the metric after round 1, 2, ... (a round = one tree of the model)
        self.best_round = 0
        self.best_value = float("inf")
        self.since_best = 0                  # training iterations since the last strictly lower metric
        self.iterations = 0                  # training iterations run
        self.stopped_by_patience = False

    def __call__(self, env):
        import lightgbm as lgb
        self.iterations = int(env.iteration) + 1
        n_now = int(env.model.current_iteration())
        if n_now < len(self.trace) or n_now > len(self.trace) + 1:
            raise ModelRefusal("early stopping: the model holds %d rounds after %d were scored"
                               % (n_now, len(self.trace)))
        improved = False
        if n_now == len(self.trace) + 1:
            # LightGBM adds no tree in an iteration where no split meets the requirements (the model then keeps
            # its rounds); a round here is a tree of the model, as booster.predict(num_iteration=r) counts them
            dump = env.model.dump_model(num_iteration=1, start_iteration=n_now - 1)
            trees = dump.get("tree_info") or []
            if len(trees) != 1:
                raise ModelRefusal("early stopping: round %d holds %d trees (one expected)" % (n_now, len(trees)))
            self.acc += _tree_output(trees[0], self.Xe)
            v = float(self.metric(_to_y(self.learner, self.params, self.z0e, self.acc)))
            if not math.isfinite(v):
                raise ModelRefusal("early stopping: the metric after round %d is %r" % (n_now, v))
            self.trace.append(v)
            if v < self.best_value:
                self.best_value, self.best_round = v, n_now
                improved = True
        self.since_best = 0 if improved else self.since_best + 1
        if self.since_best >= self.patience:
            self.stopped_by_patience = True
            # named as the model's last round (not the best one): lgb.train then keeps EVERY round when it reloads
            # the model from its text (model_to_string keeps best_iteration rounds), as a fit without early stopping
            raise lgb.callback.EarlyStopException(n_now - 1, [])


def _sel(v: np.ndarray, rows: Optional[np.ndarray]) -> np.ndarray:
    v = np.asarray(v)
    return v if rows is None else v[rows]


def _fit_lgbm(learner, params, fit_set, score_sets, cks, cache, max_bin=LGBM_MAX_BIN, early_stop=None):
    import lightgbm as lgb
    col_link = "identity" if learner == "lgbm_tweedie" else params["link"]
    rows = fit_set.rows
    _, z0, label = _target_and_offset(learner, params, fit_set, fit_set.y)
    ds = lgbm_dataset(fit_set, col_link, cache, max_bin=max_bin)
    ds.set_label(_sel(label, rows))
    # lgbm: the offset enters through the residual label (link(y) - z0) with a zero init_score: the same
    # squared-error fit as label link(y) with init_score z0, but LightGBM keeps labels in float32, and
    # the residual form keeps f exactly 0 when link(y) equals the normal. A given init_score (even 0)
    # also turns boost_from_average off. lgbm_tweedie: label y, init_score log(max(normal, c)).
    init = z0 if learner == "lgbm_tweedie" else np.zeros_like(z0)
    ds.set_init_score(_sel(init, rows))
    p = dict(LGBM_FIXED)
    p["objective"] = "tweedie" if learner == "lgbm_tweedie" else "regression"
    p["num_leaves"] = int(params["num_leaves"])
    p["min_child_samples"] = int(params["min_child_samples"])
    # the Dataset's bin count, named in the training parameters too (LightGBM would otherwise rebuild the Dataset
    # when the booster's default max_bin differs from the Dataset's)
    p["max_bin"] = int(max_bin)
    if learner == "lgbm_tweedie":
        p["tweedie_variance_power"] = float(params["tweedie_variance_power"])
    rounds = int(max(cks))
    scorer = None
    if early_stop is not None:
        if rounds < 1:
            raise ModelRefusal("early stopping needs a cap of at least one round")
        es = [s for s in score_sets if s.name == early_stop.score_set]
        if len(es) != 1:
            raise ModelRefusal("early stopping names score set %r, which is not one of %s"
                               % (early_stop.score_set, [s.name for s in score_sets]))
        ecn, ez0, _ = _target_and_offset(learner, params, es[0], None)
        scorer = _RoundScorer(learner, params, _tree_matrix(es[0].X, None, ecn), ez0, early_stop.metric,
                              early_stop.patience)
    # 0 rounds (a test of the offset, R16 analogue): no tree, the prediction is the offset itself
    if rounds > 0:
        booster = lgb.train(p, ds, num_boost_round=rounds, callbacks=[scorer] if scorer is not None else None)
    else:
        booster = None
    trained = int(booster.current_iteration()) if booster is not None else 0
    es_info = None
    if scorer is not None:
        del scorer.Xe
        if trained != len(scorer.trace) or scorer.best_round < 1:
            raise ModelRefusal("early stopping: %d rounds trained, %d scored, best round %d"
                               % (trained, len(scorer.trace), scorer.best_round))
        keep = {int(k) for k in cks if int(k) <= trained} | {scorer.best_round}
        keep |= {int(k) for k in early_stop.also_save if 0 < int(k) <= trained}
        cks = tuple(sorted(keep))
        es_info = {"patience_rounds": int(early_stop.patience), "cap_rounds": rounds,
                   "best_round": scorer.best_round, "best_metric": scorer.best_value, "stopped_at": trained,
                   "iterations_run": scorer.iterations, "stopped_by_patience": bool(scorer.stopped_by_patience),
                   "saved_rounds": list(cks), "trace": list(scorer.trace)}
    pred = {}
    for s in score_sets:
        cn, sz0, _ = _target_and_offset(learner, params, s, None)
        Xs = _tree_matrix(s.X, None, cn)
        pred[s.name] = {}
        for k in cks:
            if int(k) == 0:
                raw = np.zeros(Xs.shape[0])
            else:
                raw = booster.predict(Xs, num_iteration=int(k), raw_score=True)
            pred[s.name][k] = _to_y(learner, params, sz0, raw)
        del Xs
    if scorer is not None:
        # the per-round metric must reproduce from the finished model's own predictions, bit for bit
        for k in cks:
            v = float(early_stop.metric(pred[early_stop.score_set][k]))
            if v != scorer.trace[int(k) - 1]:
                raise ModelRefusal("early stopping: the metric at round %d is %r from the finished model and %r "
                                   "from the per-round sum" % (int(k), v, scorer.trace[int(k) - 1]))
    info = {"rounds_trained": trained,
            "train_params": p, "max_bin": int(max_bin),
            "n_fit": int(len(label) if rows is None else rows.size)}
    if es_info is not None:
        info["early_stopping"] = es_info
    return pred, booster, info


# ---------------------------------------------------------------------------------------------------
# Random forest, out of core (ruling Z2)
#
# What one RF fit does, in plain words:
#   1. Draws, from ONE generator np.random.default_rng(RANDOM_STATE), for tree 0, 1, ... in order: the tree's
#      rows (rows_per_tree positions in [0, n_fit), with replacement, then sorted) and the tree's own
#      random_state. The draws never depend on the RAM budget, the batch sizes or a resume.
#   2. Takes trees in order into a batch while the UNION of the batch's rows fits in the budget.
#   3. Reads the fit file ONCE per batch, front to back in contiguous row blocks, keeping only the union's
#      rows (0-filled, the normal column appended): the batch's "parent" in RAM.
#   4. Fits each tree of the batch on ITS OWN sample, gathered from the parent (the exact bytes of
#      [X | normal][rows of the tree]), with sklearnex RandomForestRegressor(n_estimators=1, bootstrap=False):
#      the oneDAL tree learner of the old in-RAM RF, at the same settings.
#   5. Predicts every score set with that tree in row blocks, adds it to a float64 sum (tree order), drops
#      the tree. The forest prediction is the sum / trees.
# So the trees equal the trees of an in-RAM fit on the same per-tree samples (tests/test_rf_out_of_core.py).
class RFStore(object):
    """Where an RF fit keeps its checkpoint (the trees done and the running prediction sums). The harness gives
    one that writes through the engine's registry; None = no checkpoint. load() -> bytes or None; save(bytes)."""

    def load(self) -> Optional[bytes]:
        raise NotImplementedError

    def save(self, data: bytes):
        raise NotImplementedError


def _rf_draws(n_eff: int, m: int, n_trees: int):
    """(tree, sorted positions int64, random_state) for every tree in order, from ONE generator."""
    rng = np.random.default_rng(RANDOM_STATE)
    for t in range(int(n_trees)):
        idx = rng.integers(0, n_eff, size=m, dtype=np.int64)
        seed = int(rng.integers(0, RF_SEED_HIGH))
        idx.sort(kind="stable")
        yield t, idx, seed


def _rf_tree(sample: np.ndarray, target: np.ndarray, params: Mapping[str, Any], seed: int):
    """One oneDAL tree on its own sample (all of it: bootstrap off, the draw is ours)."""
    from sklearnex.ensemble import RandomForestRegressor
    return RandomForestRegressor(n_estimators=1, bootstrap=False, max_features=float(params["max_features"]),
                                 min_samples_leaf=int(params["min_samples_leaf"]), criterion="squared_error",
                                 random_state=int(seed), n_jobs=THREADS).fit(sample, target)


def _rf_predict_into(tree, Xs: np.ndarray, acc: np.ndarray):
    """acc += the tree's prediction of Xs, RF_PRED_BLOCK_ROWS rows per call."""
    m = int(Xs.shape[0])
    for a in range(0, m, RF_PRED_BLOCK_ROWS):
        b = min(m, a + RF_PRED_BLOCK_ROWS)
        acc[a:b] += np.asarray(tree.predict(Xs[a:b]), dtype=np.float64)


class _RowReader(object):
    """Contiguous row blocks [a, b) of a row-major float32 matrix. An np.memmap opened on a file (not a view
    of one) is read with plain sequential file reads of its own bytes; anything else is sliced."""

    def __init__(self, X: Any, block_rows: int):
        import mmap
        self.X = X
        self.p = int(X.shape[1])
        self.n = int(X.shape[0])
        self.block_rows = int(block_rows)
        self.buf = np.empty((self.block_rows, self.p), dtype=np.float32)
        self.fh = None
        self.bytes_read = 0
        if (isinstance(X, np.memmap) and isinstance(getattr(X, "base", None), mmap.mmap)
                and getattr(X, "filename", None) and X.dtype == np.float32 and X.flags.c_contiguous):
            self.fh = open(X.filename, "rb", buffering=0)
            self.offset = int(X.offset)

    def read(self, a: int, b: int) -> np.ndarray:
        k = int(b - a)
        out = self.buf[:k]
        if self.fh is None:
            out[...] = self.X[a:b]
        else:
            mv = memoryview(out).cast("B")
            self.fh.seek(self.offset + int(a) * self.p * 4)
            got = 0
            while got < len(mv):
                r = self.fh.readinto(mv[got:])
                if not r:
                    raise ModelRefusal("the fit file %s ended at byte %d (rows %d-%d asked)"
                                       % (self.X.filename, self.offset + int(a) * self.p * 4 + got, a, b))
                got += r
        self.bytes_read += k * self.p * 4
        return out

    def close(self):
        if self.fh is not None:
            self.fh.close()
            self.fh = None


def _rf_fill_parent(reader: _RowReader, u: np.ndarray, normal_col: np.ndarray, parent: np.ndarray):
    """parent[i] = [0-filled X[u[i]] | float32(normal[u[i]])] for the sorted unique file rows u, read front to
    back in contiguous blocks that start at the next needed row (rows between two blocks are skipped)."""
    p = reader.p
    U = int(u.size)
    i = 0
    while i < U:
        a = int(u[i])
        b = min(reader.n, a + reader.block_rows)
        j = int(np.searchsorted(u, b, side="left"))
        blk = reader.read(a, b)
        sel = blk[u[i:j] - a]                      # a copy
        if np.isinf(sel).any():
            raise ModelRefusal("a feature block holds %d infinite values" % int(np.isinf(sel).sum()))
        sel[np.isnan(sel)] = 0.0
        parent[i:j, :p] = sel
        i = j
    parent[:, p] = np.asarray(normal_col, dtype=np.float64)[u].astype(np.float32)


def _rf_budget(n_file: int, p: int, m: int, score_rows: int, budget: float) -> Dict[str, int]:
    """The RF's RAM plan: what is fixed, and what is left for the batch's parent rows. Refuses when one tree's
    sample cannot fit."""
    row_bytes = (p + 1) * 4
    sample = m * row_bytes
    block_rows = max(1, int(RF_READ_BLOCK_BYTES // max(1, p * 4)))
    fixed = {
        "sample_and_fit": int(sample * (1.0 + RF_FIT_FACTOR)),
        "score_sets": int(score_rows * (row_bytes + 8)),
        "read_blocks": int(2 * block_rows * p * 4),
        "per_row_arrays": int(n_file * (1 + 8 + 8)),         # union mask, target, positions
        "slack": int(RF_SLACK_BYTES),
    }
    left = int(budget) - sum(fixed.values())
    if left < m * (row_bytes + 8):
        raise ModelRefusal("the RF needs about %.2f GiB for one tree of %d rows x %d columns plus %.2f GiB fixed; "
                           "its budget is %.2f GiB" % (m * (row_bytes + 8) / GIB, m, p + 1,
                                                       sum(fixed.values()) / GIB, budget / GIB))
    return dict(fixed, parent_budget=left, row_bytes=row_bytes, block_rows=block_rows)


def rf_ram_need(n_file: int, p: int, score_rows: int = 0, n_trees: Optional[int] = None,
                budget: Optional[float] = None) -> int:
    """The most RAM an RF fit plans to use (bytes): the fixed parts plus a parent of at most every row (all
    trees' row lists included), never above the budget. The harness's go / refuse check uses it."""
    B = float(RF_RAM_BUDGET if budget is None else budget)
    T = int(RF_TREES if n_trees is None else n_trees)
    m = rf_rows_per_tree(n_file)
    plan = _rf_budget(n_file, p, m, score_rows, B)
    fixed = int(B) - plan["parent_budget"]
    return int(min(B, fixed + n_file * plan["row_bytes"] + T * m * 8))


def rf_batch_plan(n_file: int, p: int, score_rows: int = 0, n_trees: Optional[int] = None,
                  budget: Optional[float] = None) -> Dict[str, Any]:
    """The batches an RF fit of this shape will make (the same draws and the same greedy rule as rf_forest,
    without reading any data): trees per batch and parent rows per batch. For planning and the time estimate."""
    B = float(RF_RAM_BUDGET if budget is None else budget)
    T = int(RF_TREES if n_trees is None else n_trees)
    m = rf_rows_per_tree(n_file)
    plan = _rf_budget(n_file, p, m, score_rows, B)
    mask = np.zeros(n_file, dtype=bool)
    per_batch, parent_rows = [], []
    k, U = 0, 0
    for t, idx, seed in _rf_draws(n_file, m, T):
        uniq = idx[np.concatenate(([True], idx[1:] != idx[:-1]))]
        new = int(np.count_nonzero(~mask[uniq]))
        if k and (U + new) * plan["row_bytes"] + (k + 1) * m * 8 > plan["parent_budget"]:
            per_batch.append(k)
            parent_rows.append(U)
            mask[:] = False
            k, U = 0, 0
            new = int(uniq.size)
        mask[uniq] = True
        U += new
        k += 1
    per_batch.append(k)
    parent_rows.append(U)
    return {"rows_per_tree": m, "trees": T, "batches": len(per_batch), "trees_per_batch": per_batch,
            "parent_rows_per_batch": parent_rows, "parent_budget_bytes": plan["parent_budget"],
            "rows_read_per_batch": "every block from the batch's first to its last parent row"}


def _rf_key(params, n_eff, p, m, n_trees, target, score_mats, caller_key) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update(repr((RF_METHOD, RANDOM_STATE, RF_SEED_HIGH, float(params["max_features"]),
                   int(params["min_samples_leaf"]), int(n_eff), int(p), int(m), int(n_trees),
                   str(caller_key))).encode("ascii"))
    h.update(np.ascontiguousarray(target, dtype=np.float64).tobytes())
    for name, Xs in score_mats:
        h.update(repr((name, Xs.shape)).encode("ascii"))
        h.update(np.ascontiguousarray(Xs[:, -1]).tobytes())
    return h.hexdigest()


def _rf_load(store, key, names, sizes):
    if store is None:
        return 0, None
    raw = store.load()
    if not raw:
        return 0, None
    import io as _io
    z = np.load(_io.BytesIO(raw), allow_pickle=False)
    if str(z["key"]) != key:
        return 0, None                             # another fit's checkpoint: start from tree 0
    acc = [np.array(z["acc_%d" % i], dtype=np.float64) for i in range(len(names))]
    if [a.size for a in acc] != list(sizes):
        raise ModelRefusal("an RF checkpoint with this fit's key holds the wrong row counts")
    return int(z["trees_done"]), acc


def _rf_save(store, key, trees_done, accs):
    if store is None:
        return
    import io as _io
    bio = _io.BytesIO()
    np.savez(bio, key=np.array(key), trees_done=np.array(int(trees_done)),
             **{"acc_%d" % i: a for i, a in enumerate(accs)})
    store.save(bio.getvalue())


def rf_forest(X: Any, rows: Optional[np.ndarray], normal_col: np.ndarray, target: np.ndarray,
              params: Mapping[str, Any], score_mats: Sequence[Tuple[str, np.ndarray]],
              n_trees: Optional[int] = None, budget: Optional[float] = None,
              store: Optional[RFStore] = None, caller_key: str = "",
              on_tree: Optional[Any] = None) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
    """The out-of-core forest (steps 1-5 above). X: the raw fit matrix (memmap or array, n_file x p);
    rows: None or increasing file rows forming the fit set; normal_col, target: per FILE row (float64);
    score_mats: [(name, 0-filled [X | normal] float32)]. Returns ({name: f = mean tree prediction}, info).
    on_tree(t): called after tree t is added to the sums (tests use it to stop a fit between trees)."""
    import hashlib
    T = int(RF_TREES if n_trees is None else n_trees)
    B = float(RF_RAM_BUDGET if budget is None else budget)
    if T < 1:
        raise ModelRefusal("an RF needs at least one tree")
    n_file, p = int(X.shape[0]), int(X.shape[1])
    file_rows = None if rows is None else np.asarray(rows, dtype=np.int64)
    n_eff = n_file if file_rows is None else int(file_rows.size)
    m = rf_rows_per_tree(n_eff)
    target = np.asarray(target, dtype=np.float64)
    names = [nm for nm, _ in score_mats]
    sizes = [int(Xs.shape[0]) for _, Xs in score_mats]
    plan = _rf_budget(n_file, p, m, sum(sizes), B)
    key = _rf_key(params, n_eff, p, m, T, target, score_mats, caller_key)
    start, accs = _rf_load(store, key, names, sizes)
    if accs is None:
        accs = [np.zeros(sz, dtype=np.float64) for sz in sizes]
    reader = _RowReader(X, plan["block_rows"])
    mask = np.zeros(n_file, dtype=bool)
    draws = _rf_draws(n_eff, m, T)
    sha = hashlib.sha256()
    pending = None
    batches, union_rows = [], []
    t_read = t_fit = t_pred = 0.0
    done = start
    try:
        while True:
            # the next batch: trees in order while the union of their rows fits the parent budget
            batch, U = [], 0
            while True:
                if pending is None:
                    nxt = next(draws, None)
                    if nxt is None:
                        break
                    t, idx, seed = nxt
                    sha.update(idx.tobytes())
                    sha.update(np.int64(seed).tobytes())
                    if t < start:
                        continue                   # finished before a resume: drawn again, not refitted
                    fr = idx if file_rows is None else file_rows[idx]
                    pending = (t, fr, seed)
                t, fr, seed = pending
                uniq = fr[np.concatenate(([True], fr[1:] != fr[:-1]))]
                new = int(np.count_nonzero(~mask[uniq]))
                need = (U + new) * plan["row_bytes"] + (len(batch) + 1) * m * 8
                if batch and need > plan["parent_budget"]:
                    break
                mask[uniq] = True
                U += new
                batch.append(pending)
                pending = None
            if not batch:
                break
            t0 = time.time()
            u = np.flatnonzero(mask)
            parent = np.empty((u.size, p + 1), dtype=np.float32)
            _rf_fill_parent(reader, u, normal_col, parent)
            mask[:] = False
            t_read += time.time() - t0
            batches.append(len(batch))
            union_rows.append(int(u.size))
            for t, fr, seed in batch:
                t0 = time.time()
                pos = np.searchsorted(u, fr)
                sample = parent[pos]
                tree = _rf_tree(sample, target[fr], params, seed)
                del sample, pos
                t_fit += time.time() - t0
                t0 = time.time()
                for (nm, Xs), acc in zip(score_mats, accs):
                    _rf_predict_into(tree, Xs, acc)
                del tree
                t_pred += time.time() - t0
                done = t + 1
                if on_tree is not None:
                    on_tree(t)
                if done % RF_CKPT_EVERY == 0 and done < T:
                    _rf_save(store, key, done, accs)
            del parent, u
            batch = []
            gc_collect()
    finally:
        reader.close()
    if done != T:
        raise ModelRefusal("the RF stopped at tree %d of %d" % (done, T))
    _rf_save(store, key, done, accs)
    f = {nm: acc / float(T) for nm, acc in zip(names, accs)}
    info = {"method": RF_METHOD, "n_fit": n_eff, "rows_per_tree": m, "trees": T, "resumed_from_tree": start,
            "batches": len(batches), "trees_per_batch": batches, "parent_rows_per_batch": union_rows,
            "samples_sha256": sha.hexdigest(), "budget_bytes": B,
            "ram_plan_bytes": {k: v for k, v in plan.items() if k not in ("row_bytes", "block_rows")},
            "read_gib": reader.bytes_read / GIB, "read_seconds": t_read, "fit_seconds": t_fit,
            "predict_seconds": t_pred}
    return f, info


def gc_collect():
    import gc
    gc.collect()


def _fit_rf(learner, params, fit_set, score_sets, cks, rf_store=None, rf_key="", n_trees=None):
    cn, _, target = _target_and_offset(learner, params, fit_set, fit_set.y)
    mats, offsets = [], {}
    for s in score_sets:
        scn, sz0, _ = _target_and_offset(learner, params, s, None)
        mats.append((s.name, _tree_matrix(s.X, None, scn)))
        offsets[s.name] = sz0
    f, info = rf_forest(fit_set.X, fit_set.rows, cn, target, params, mats, n_trees=n_trees,
                        store=rf_store, caller_key=rf_key)
    del mats
    pred = {name: {k: _to_y(learner, params, offsets[name], f[name]) for k in cks} for name in offsets}
    model = {"method": RF_METHOD, "trees": info["trees"], "rows_per_tree": info["rows_per_tree"],
             "note": "each tree is dropped after predicting; the predictions are kept (plan 5c)"}
    return pred, model, info


def rf_probe(fit_set: FitData, params: Mapping[str, Any], n_trees: int) -> Dict[str, Any]:
    """A short RF fit (n_trees trees, no score set) at the real fit shape: the probe's time and RAM check."""
    cn, _, target = _target_and_offset("rf", params, fit_set, fit_set.y)
    _, info = rf_forest(fit_set.X, fit_set.rows, cn, target, params, [], n_trees=n_trees)
    return info


# ---------------------------------------------------------------------------------------------------
# HistGradientBoosting, absolute error (labelled timid-prone)
def _fit_hgb(learner, params, fit_set, score_sets, cks):
    from sklearn.ensemble import HistGradientBoostingRegressor
    rows = fit_set.rows
    cn, _, target = _target_and_offset(learner, params, fit_set, fit_set.y)
    Xf = _tree_matrix(fit_set.X, rows, cn)
    t = _sel(target, rows)
    max_iter = int(max(cks))
    model = HistGradientBoostingRegressor(loss="absolute_error", learning_rate=LEARNING_RATE,
                                          max_iter=max_iter, early_stopping=False,
                                          max_leaf_nodes=int(params["max_leaf_nodes"]),
                                          min_samples_leaf=int(params["min_samples_leaf"]),
                                          random_state=RANDOM_STATE)
    model.fit(Xf, t)
    del Xf
    want = {int(k) for k in cks}
    pred = {}
    for s in score_sets:
        scn, sz0, _ = _target_and_offset(learner, params, s, None)
        Xs = _tree_matrix(s.X, None, scn)
        got = {}
        for i, f in enumerate(model.staged_predict(Xs), start=1):
            if i in want:
                got[i] = _to_y(learner, params, sz0, f)
        missing = sorted(want - set(got))
        if missing:
            raise ModelRefusal("hgb_l1 stopped at %d iterations; checkpoints %s were never reached"
                               % (int(model.n_iter_), missing))
        pred[s.name] = {k: got[int(k)] for k in cks}
        del Xs
    info = {"n_fit": int(t.size), "n_iter": int(model.n_iter_)}
    return pred, model, info


# ---------------------------------------------------------------------------------------------------
# Ridge: chunked float64 X'X, mean imputation + missing flags, standardised, cholesky
def _ridge_stats(X, rows, normal_col):
    """Pass 1: per-column non-NaN count, sum, min and max of [X | normal column]."""
    n = int(X.shape[0]) if rows is None else int(rows.size)
    p = int(X.shape[1]) + 1
    cnt = np.zeros(p, dtype=np.int64)
    tot = np.zeros(p, dtype=np.float64)
    lo = np.full(p, np.inf)
    hi = np.full(p, -np.inf)
    nc = np.asarray(normal_col, dtype=np.float64)
    for a in range(0, n, RIDGE_BLOCK_ROWS):
        b = min(n, a + RIDGE_BLOCK_ROWS)
        src = X[a:b] if rows is None else X[rows[a:b]]
        blk = np.empty((b - a, p), dtype=np.float64)
        blk[:, :-1] = src
        blk[:, -1] = nc[a:b] if rows is None else nc[rows[a:b]]
        if np.isinf(blk).any():
            raise ModelRefusal("ridge: the fit rows hold %d infinite values" % int(np.isinf(blk).sum()))
        ok = ~np.isnan(blk)
        cnt += ok.sum(axis=0)
        tot += np.where(ok, blk, 0.0).sum(axis=0)
        lo = np.minimum(lo, np.where(ok, blk, np.inf).min(axis=0))
        hi = np.maximum(hi, np.where(ok, blk, -np.inf).max(axis=0))
    return n, cnt, tot, lo, hi


class RidgeDesign(object):
    """The design of one fit set: which value columns are kept, which flags exist, means and sds."""

    def __init__(self, X, rows, normal_col, columns):
        n, cnt, tot, lo, hi = _ridge_stats(X, rows, normal_col)
        if n == 0:
            raise ModelRefusal("ridge: no fit row")
        names = list(columns) + ["__normal__"]
        nan_cnt = n - cnt
        with np.errstate(invalid="ignore", divide="ignore"):
            mean = np.where(cnt > 0, tot / np.maximum(cnt, 1), 0.0)
        constant = (cnt == 0) | (lo == hi)
        self.p_raw = len(names)
        self.mean_impute = mean                                   # per raw column
        self.keep_value = np.flatnonzero(~constant)               # raw value columns kept
        self.flag_cols = np.flatnonzero((nan_cnt > 0) & (nan_cnt < n))
        self.dropped = [names[i] for i in np.flatnonzero(constant)]
        self.flag_names = ["missing__" + names[i] for i in self.flag_cols]
        self.names = [names[i] for i in self.keep_value] + self.flag_names
        self.n = n
        self._nan_share = nan_cnt / float(n)

    def means(self) -> np.ndarray:
        """The design columns' means over the fit rows."""
        return np.concatenate([self.mean_impute[self.keep_value], self._nan_share[self.flag_cols]])

    def block(self, src: np.ndarray, normal_part: np.ndarray) -> np.ndarray:
        """The imputed design block [kept values | flags] (float64), before centring."""
        raw = np.empty((src.shape[0], self.p_raw), dtype=np.float64)
        raw[:, :-1] = src
        raw[:, -1] = normal_part
        nan = np.isnan(raw)
        flags = nan[:, self.flag_cols].astype(np.float64)
        if nan.any():
            raw = np.where(nan, self.mean_impute[None, :], raw)
        return np.concatenate([raw[:, self.keep_value], flags], axis=1)


def _fit_ridge(learner, params, fit_set, score_sets, cks):
    rows = fit_set.rows
    cn, _, target = _target_and_offset(learner, params, fit_set, fit_set.y)
    t = _sel(target, rows).astype(np.float64)
    design = RidgeDesign(fit_set.X, rows, cn, fit_set.columns)
    n = design.n
    q = len(design.names)
    if q == 0:
        raise ModelRefusal("ridge: every column is constant on the fit rows")
    # design means from pass 1: an imputed value column keeps its non-NaN mean; a flag's mean is
    # its NaN share
    mu = design.means()
    ncs = np.asarray(cn, dtype=np.float64)
    tbar = float(t.mean())
    # pass 2: centred cross products
    C = np.zeros((q, q), dtype=np.float64)
    g = np.zeros(q, dtype=np.float64)
    for a in range(0, n, RIDGE_BLOCK_ROWS):
        b = min(n, a + RIDGE_BLOCK_ROWS)
        src = fit_set.X[a:b] if rows is None else fit_set.X[rows[a:b]]
        npart = ncs[a:b] if rows is None else ncs[rows[a:b]]
        Z = design.block(src, npart) - mu[None, :]
        C += Z.T @ Z
        g += Z.T @ (t[a:b] - tbar)
    sd = np.sqrt(np.diag(C) / n)
    zero_sd = ~(sd > 0)
    if zero_sd.any():
        raise ModelRefusal("ridge: %d design columns have sd 0 after the constant check (%s)"
                           % (int(zero_sd.sum()), [design.names[i] for i in np.flatnonzero(zero_sd)][:5]))
    A = C / np.outer(sd, sd)
    bvec = g / sd
    coefs = {}
    for alpha in cks:
        M = A + float(alpha) * np.eye(q)
        Lc = np.linalg.cholesky(M)
        w = np.linalg.solve(Lc.T, np.linalg.solve(Lc, bvec))
        coefs[alpha] = w / sd                      # on the centred, unscaled design
    pred = {}
    for s in score_sets:
        scn, sz0, _ = _target_and_offset(learner, params, s, None)
        m = int(s.X.shape[0])
        out = {alpha: np.empty(m, dtype=np.float64) for alpha in cks}
        scn = np.asarray(scn, dtype=np.float64)
        for a in range(0, m, RIDGE_BLOCK_ROWS):
            b = min(m, a + RIDGE_BLOCK_ROWS)
            Z = design.block(np.asarray(s.X[a:b]), scn[a:b]) - mu[None, :]
            for alpha in cks:
                out[alpha][a:b] = tbar + Z @ coefs[alpha]
        pred[s.name] = {alpha: _to_y(learner, params, sz0, out[alpha]) for alpha in cks}
    model = {"names": design.names, "dropped": design.dropped, "flags": design.flag_names,
             "mean": mu.tolist(), "sd": sd.tolist(), "intercept": tbar,
             "coef": {repr(float(a)): coefs[a].tolist() for a in cks}}
    info = {"n_fit": n, "design_columns": q, "dropped_columns": design.dropped,
            "flag_columns": len(design.flag_names)}
    return pred, model, info


# ---------------------------------------------------------------------------------------------------
class FitResult(dict):
    """{score set name: {checkpoint: {'pre': pre-clip y-unit predictions, 'pred': clipped (only when
    a legal range was given)}}}, with the fitted object in .model and plain facts in .info."""

    def __init__(self, data, model=None, info=None):
        super().__init__(data)
        self.model = model
        self.info = dict(info or {})


def _as_fit(fit_set: Any) -> Tuple[FitData, Dict[str, Any]]:
    """A FitData, or the plain mapping {X, columns, y, z0, link, c, ub, legal} (z0 = the link-space
    normal of 'link'; with link 'identity' it is also the identity normal)."""
    if isinstance(fit_set, FitData):
        return fit_set, {}
    if not isinstance(fit_set, Mapping):
        raise ModelRefusal("the fit set must be a FitData or a mapping, got %s" % type(fit_set).__name__)
    link = fit_set.get("link")
    if not link:
        raise ModelRefusal("a mapping fit set names its link")
    X = np.asarray(fit_set["X"], dtype=np.float32)
    cols = tuple(fit_set.get("columns") or ["f%d" % i for i in range(X.shape[1])])
    fd = FitData(name=str(fit_set.get("name", "fit")), X=X, columns=cols,
                 y=np.asarray(fit_set["y"], dtype=np.float64),
                 normal={link: np.asarray(fit_set["z0"], dtype=np.float64)},
                 rows=fit_set.get("rows"))
    extra = {k: fit_set[k] for k in ("link", "c", "ub", "legal") if k in fit_set}
    return fd, extra


def _as_scores(score_sets: Any) -> List[ScoreData]:
    if isinstance(score_sets, Mapping):
        out = []
        for name, v in score_sets.items():
            if isinstance(v, ScoreData):
                out.append(ScoreData(name=str(name), X=v.X, normal=v.normal))
                continue
            link = v.get("link")
            if not link:
                raise ModelRefusal("score set %s names no link" % name)
            out.append(ScoreData(name=str(name), X=np.asarray(v["X"], dtype=np.float32),
                                 normal={link: np.asarray(v["z0"], dtype=np.float64)}))
        return out
    return list(score_sets)


def fit_predict(learner: str, params: Mapping[str, Any], fit_set: Any, score_sets: Any,
                checkpoints: Iterable[Any], cache: Optional[Dict[Any, Any]] = None,
                rf_store: Optional[RFStore] = None, rf_key: str = "",
                early_stop: Optional[EarlyStop] = None, max_bin: Optional[int] = None) -> FitResult:
    """Fit one trial on fit_set and predict every score set at every checkpoint.

    params: the setting (grid values) plus 'link' (R22 value; not for lgbm_tweedie), 'c' (the
    lead's R23 c, A3), 'ub' (the legal maximum when finite, else None) and optionally 'legal'
    (min, max): then each prediction is also clipped with the engine's clip_to_legal ('pred').
    A mapping fit set may carry link, c, ub and legal instead (params win).
    fit_set: FitData or a mapping (see _as_fit); score_sets: a list of ScoreData or a mapping
    {name: ScoreData or {X, z0, link}}.
    checkpoints: alphas (ridge), the tree count (rf: any one value, one fit), or rounds (boosters;
    the fit runs to the largest).
    rf_store, rf_key (rf only): where the out-of-core forest keeps its checkpoint, and the caller's key of the
    fit (a stored checkpoint is used only when its key equals this fit's key).
    early_stop (lgbm, lgbm_tweedie only; tuning): an EarlyStop; the largest checkpoint is then the cap, and the
    result holds the checkpoints reached, the best round and early_stop.also_save (info['early_stopping'] has
    the best round, the stop and the per-round metric).
    max_bin (lgbm, lgbm_tweedie only): histogram bins; None = LGBM_MAX_BIN (LightGBM's default 255). The harness
    passes LGBM_MAX_BIN to every LightGBM fit, tuning and final (ruling AC1); another value is for the tests only.
    Returns a FitResult {score set name: {checkpoint: {'pre': ..., 'pred': ...}}} with .model (the
    booster, the estimator, or the ridge coefficients) and .info.
    """
    fit_set, extra = _as_fit(fit_set)
    params = dict(extra, **dict(params))
    score_sets = _as_scores(score_sets)
    cks = tuple(checkpoints)
    if not cks:
        raise ModelRefusal("no checkpoint asked")
    if learner not in LEARNERS:
        raise ModelRefusal("unknown learner %r (known: %s)" % (learner, ", ".join(LEARNERS)))
    if uses_links(learner) and not params.get("link"):
        raise ModelRefusal("%s needs a link" % learner)
    if learner == "lgbm_tweedie" and "identity" not in fit_set.normal:
        raise ModelRefusal("lgbm_tweedie needs the identity normal (its offset is log(max(normal, c)))")
    p = len(fit_set.columns)
    n = _check_set(fit_set, p, "fit set %s" % fit_set.name)
    y = np.asarray(fit_set.y, dtype=np.float64)
    if y.shape != (n,) or not np.isfinite(y).all():
        raise ModelRefusal("fit set %s: y must be %d finite labels" % (fit_set.name, n))
    if fit_set.rows is not None:
        r = np.asarray(fit_set.rows)
        if r.ndim != 1 or r.size == 0 or r.min() < 0 or r.max() >= n or np.any(np.diff(r) <= 0):
            raise ModelRefusal("fit set %s: rows must be increasing positions inside the set" % fit_set.name)
    for s in score_sets:
        _check_set(s, p, "score set %s" % s.name)
    if (early_stop is not None or max_bin is not None) and learner not in EARLY_STOP_LEARNERS:
        raise ModelRefusal("%s takes no early stopping and no max_bin (only %s do)"
                           % (learner, ", ".join(EARLY_STOP_LEARNERS)))
    if max_bin is not None and (int(max_bin) != max_bin or not 2 <= int(max_bin) <= 255):
        raise ModelRefusal("max_bin must be an integer in [2, 255], got %r" % (max_bin,))
    if learner == "lgbm" or learner == "lgbm_tweedie":
        pred, model, info = _fit_lgbm(learner, params, fit_set, score_sets, cks, cache,
                                      max_bin=LGBM_MAX_BIN if max_bin is None else int(max_bin),
                                      early_stop=early_stop)
    elif learner == "rf":
        pred, model, info = _fit_rf(learner, params, fit_set, score_sets, cks, rf_store=rf_store, rf_key=rf_key)
    elif learner == "hgb_l1":
        pred, model, info = _fit_hgb(learner, params, fit_set, score_sets, cks)
    else:
        pred, model, info = _fit_ridge(learner, params, fit_set, score_sets, cks)
    legal = params.get("legal")
    out = {}
    for name, by_ck in pred.items():
        out[name] = {}
        for k, v in by_ck.items():
            rec = {"pre": v}
            if legal is not None:
                from treeroute.layer.links import clip_to_legal
                rec["pred"] = clip_to_legal(v, tuple(legal), False)[0]
            out[name][k] = rec
    return FitResult(out, model=model, info=info)


__all__ = ["THREADS", "RANDOM_STATE", "BASE_ROUNDS", "EXTENSION_ROUNDS", "EDGE_ROUNDS", "LAST_ROUNDS",
           "RIDGE_ALPHAS", "RF_TREES", "LEARNERS", "CORE_LEARNERS", "STAGED_LEARNERS", "LOSS",
           "ModelRefusal", "grid", "checkpoints", "uses_links", "fixed_params", "rf_rows_per_tree",
           "FitData", "ScoreData", "FitResult", "link_forward", "link_inverse", "RFStore", "rf_forest",
           "rf_probe", "lgbm_dataset", "fit_predict", "RF_RAM_BUDGET", "RF_METHOD", "EarlyStop",
           "EARLY_STOP_LEARNERS", "PATIENCE_ROUNDS", "LGBM_MAX_BIN", "tuning_options",
           "final_fit_options", "in_last_stage", "ran_to_cap"]
