"""SPEEDPROOF COPY (2026-09-28) of pm25_adaptation.py -- NOT the shipped script. APP_PLAN.md 4.5.

Everything below is the shipped pm25_adaptation.py (sha256 cf2f2357...1f11057) with SIX plumbing
changes (a)-(f) and the copy-only records (g), and nothing else. None of them touches a formula, a row,
a seed or an order of operations:
  (a) SPEEDUP 2. columns() predicts the trees on TREE_WORKERS threads into the same row-block buffer;
      each thread owns a contiguous range of tree columns and runs exactly the shipped per-tree lines.
  (b) SPEEDUP 3. route_percell / route_sweep solve the per-cell routers on ROUTER_WORKERS threads with
      BLAS pinned to 1 thread (threadpoolctl) for the whole solve, at ANY worker count, so the bytes
      cannot depend on the worker count. Each cell's computation is the shipped one, moved into a
      function; the cell list, the fallback rule, the NVERIFY cells and the write-back order are fixed
      serially first, and results are written back in the shipped cell order.
  (c) --workers N (default 8) sets both counts; --tree-workers / --router-workers override one.
      --workers 1 runs both loops SERIALLY in the main thread (still with BLAS pinned to 1 in the router).
  (d) the project folder is put on sys.path (this file lives in engine/speedproof/), and the temp
      matrices + pool go to D:/treeroute/speedproof/tmp instead of D:/pm25 (the pre-flight checks both).
  (e) OFF unless --finite-once 1 (added after the first wide runs showed speedup (a) alone gives ~1.1x):
      sklearn's per-predict input finiteness scan (daal4py's, installed by patch_sklearn) holds the GIL
      and re-scans the whole block for every tree; with the flag it runs once per block in the main
      thread (same function, same allow_nan) and the trees predict under thread-local assume_finite.
  (f) TEST ONLY, --router-pin 0 (with --router-workers 1): the router runs the shipped serial loop in
      the shipped BLAS state, so the tree side alone can be compared byte for byte with the shipped script.
  (g) COPY-ONLY RECORDS, written beside the shipped outputs and never into them (added 2026-09-28 after
      review): this file's own sha256 goes into verdict.json["speedproof"] and the pre-flight log line,
      so every run folder names the code version that made it; the FLOAT64 inner surfaces go to
      speedproof_inner_f64.npz (inner_preds.npz stays float32, as shipped, so it remains comparable
      with the shipped outputs); and the tree-answer seconds are split into row-matrix build (Vm),
      prediction, and copy-into-memmap + flush.
Run:  py -3.9 -u pm25_adaptation_fast.py --smoke ... --run-dir D:/treeroute/speedproof/fast_w8 --workers 8

The type-2 adaptation architecture on PM2.5. Problem #5.

A STANDALONE ADAPTER, NOT AN EDIT TO adaptation.py. The machinery is IMPORTED -- derive_tier1,
fit_correctors, solve_local, build_bank, open_A, tree_columns_to all come from the existing modules
rather than being copied, because three versions of the NDVI remove-list is what copying produces.
What lives here is the PM2.5 contract: which rows, which split, which arms, and how it is scored.

THE TWO-TIER RULE, WHICH IS THE WHOLE CLAIM.
    base models   trained on DONOR regions only, <=2019. No base model ever sees a test region.
    router        calibrated on the TEST CELL'S OWN 2003-2019 history. 204 rows/cell (2002 is
                  dropped -- owner ruling A1, see pm25_architecture).
    arm decision  made on an INNER window (2003-2016 fit -> 2017-2019 score) inside the calibration
                  history. NO TEST-WINDOW NUMBER IS SEEN BEFORE THE LAYER PICKS.
    scoring       2020-2023, never touched until the arm is fixed. 100 strided cells per test region
                  (2,000 cells, every region weighted equally) is the FINAL evaluation (ruling A12).
An assertion enforces each boundary; if one fires the run is not what this docstring says it is.

*** SCIENCE CHANGE A6 (2026-09-24): THE INNER CLIMATOLOGY IS BUILT FROM THE INNER FIT ROWS ONLY. ***
The climatology is an UNPENALISED router input and the guess-normal baseline. It used to be averaged
over ALL calibration years (2002-2019) and reused inside the inner pass, so 3 of its 18 years were
the very years the inner pass scores -- a normal that already knew the answer, which rewards any
candidate that leans on it (heavy tree penalty). The inner pass now builds its own climatology from
<=2016 rows; the test pass still uses the full <=2019 history, which is legitimate there.
DISCLOSED, NOT FIXED (ruling A6): the donor trees are fitted on donor rows up to 2019, so on the
inner-score months (2017-2019) they have seen those months in OTHER regions -- and the global index
columns (ENSO, PDO, ...; one value per month everywhere) let a tree recognise the month. In 2020-2023
they cannot. The inner window is therefore somewhat easier for the TREES than the test window is.
The same holds for the CORRECTORS and their placebo (fit_correctors fits them on the donor trees' own-
region out-of-bag rows up to 2019), which can favour the corrector arms in the inner decision in
particular; and the donor-mean fallbacks (gmean/lgmean) include 2017-2019 donor targets, though they
reach only cells with <24 fit rows. None of this touches a test region or any 2020-2023 row.
Fire (adaptation.py:2185-2214) and defo share this; fixing it only here would make PM2.5 incomparable.
Fire also shares the climatology leak (adaptation.py:2322-2326) -- disclosed there, not fixed (G3).

*** SCIENCE CHANGE A8 (2026-09-24): THE log ARM ROUTES ON A LOG-SCALE CLIMATOLOGY. ***
The log arm fits the ridge on log1p(y). Its unpenalised climatology input used to stay on the RAW
ug/m3 scale -- a log-space model fed a raw-scale normal, which cannot express a multiplicative
seasonal cycle and blew up on peaks (smoke: bolivia MAE 9.71 vs base 6.32). It now gets `lclim`,
the per-cell per-month MEAN OF log1p(y) over the calibration rows -- the normal in the space the
ridge actually fits. mean(log) != log(mean) because the target is skewed, which is the whole reason
the arm exists. The tree columns stay raw-scale (no new bank). Scoring is unchanged: every arm is
scored in ug/m3 against the RAW climatology.
WHY a log arm at all: PM2.5 is strictly positive and right-skewed, and derive_tier1's link rule
(arcsine if bounded, else identity) cannot express a log link. The link is therefore OFFERED AS A
CANDIDATE ARM and adopted only if it wins on rows the layer may see. (An earlier version justified
it with "Taylor p ~ 2 = log-normal". That was WRONG and is withdrawn: derive_tier1's exponent reads
the target's distribution SHAPE -- any log-normal returns ~2.15, a true gamma law 1.24 -- and
defo/fire/coral all read ~2.)

CANDIDATES. base | log | corrector | log_corrector, each over the (level x ratio) penalty grid, plus
ONE TREES-OFF candidate per link. Trees-off turns out to be THE CLIMATOLOGY ITSELF: the per-cell
climatology is the cell x month mean over the very rows the ridge is fitted on, so its unpenalised
column takes coefficient 1 and the context block cannot add anything (the 2026-09-24 review showed
this; the crash test confirms treesoff MAE == guess-normal MAE). So `treesoff` = guess-normal and
`log_treesoff` = the GEOMETRIC normal expm1(mean log1p y), each one penalty-free candidate. If one
wins, the layer is DECLINING TO PREDICT the anomaly at all -- and the tree arms are then scored at the
best TREE-ROUTED candidate's penalty, never at a penalty nothing chose. Adoption is ARGMIN MAE over
every candidate on the inner window, BASE INCLUDED, so "the layer declines" is reportable.
NOTE FOR READERS OF MAE: on this right-skewed target the geometric normal sits nearer the median, and
MAE rewards the median -- so the log family can win on MAE partly WITHOUT routing skill. So (ruling
N2) an arm is ELIGIBLE for adoption only if it beats ITS OWN link-matched normal on the inner window
(identity arms the arithmetic normal, log arms the geometric one); if none is eligible the layer
declines and adopts DECLINE_TO. Every log arm is also reported against both normals.

TYPE 1, TWO WAYS (ruling A7). The test pass scores `base_inherited` -- fire's (ALPHA, A_CTX), no
adaptation at all -- AND `base` at the ADOPTED penalty. Their difference is what the penalty sweep
alone bought; the adopted arm minus `base` is what the tools bought.

THE PLACEBO IS A DIAGNOSTIC, NOT A GATE. Correctors are also fitted on cyclically-shifted residuals,
which have nothing to learn by construction. corrector - base says what the tool is WORTH; corrector
- placebo says whether it CORRECTS. On coral those were +0.0153 and +0.0020 -- worth adopting, and
not a corrector.

SCORING. anomaly-R2 (deployable) AND pattern-R2 (diagnostic), because this target has a train-to-test
LEVEL SHIFT of roughly half a test standard deviation whose SIGN VARIES BY REGION -- 82 of 127
regions fell over 2002-2023, 45 rose. That offset drives anomaly-R2 negative on its own, whether or
not the model reads the within-window pattern. Reporting only the first would call the architecture
broken; only the second would be dishonest. MAE and hit-rate alongside, always against guess-normal.
PATTERN-R2 DEMEANS PER REGION -- the shift's sign varies by region, so one pooled mean does not
remove it. HIT-RATE = share within +/-2 ug/m3 (ACAG's own error floor, ruling A11), for the model
AND for guess-normal; the old "right side of normal" survives as `dirhit`, a bonus. Everything is
also written PER REGION and PER YEAR. Confidence intervals: leave-one-REGION-out jackknife, the
shipped layer's own (adaptation.jack) -- no bootstrap, no seeds (ruling A10).

EVERY DECISION IS PERSISTED, NOT JUST PRINTED. RUN_DIR (D:/pm25_adapt/full or /smoke) receives:
run.log (the console, including pool/memory lines and any traceback), _adaptation.log
(adaptation.py's own lines -- previously they landed in FIRE's log because argv names --problem
fire), inner_candidates.csv (every candidate the layer ranked), inner_preds.npz (the row-level inner
surfaces, so the decision can be re-scored on another criterion), verdict.json (written right after
the inner decision, then completed: adopted arm + penalty, Tier-1 reading, config, features, phase
timings), predictions.parquet (row level, with cell_id and the adopted arm), per_region.csv,
per_year.csv. RUNNING exists only while a run is alive.

CRASH-SAFE: main() refuses to start while earlier tree-matrix/pool files sit on D:/pm25, refuses to
overwrite a previous run unless --force (which MOVES it to prev_<timestamp>/), checks the disk before
hours of bank building and before every matrix, and deletes the matrix and pool in a finally-block.

    py -3.9 -u pm25_adaptation.py --smoke        8 donors / 3 test, tiny -- ALWAYS RUN THIS FIRST
    py -3.9 -u pm25_adaptation.py --npd 100      the full split, 10,700 tree columns (100 = default)
    py -3.9 -u pm25_adaptation.py --npd 100 --force    same, moving the previous full run aside
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# SPEEDPROOF (d): this copy lives in <project>/engine/speedproof/, and every module it imports
# (adaptation, pm25_architecture, fire_architecture, ...) lives in <project>. Put <project> FIRST so the
# shipped modules are the ones imported; the originals are not edited.
_PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT)
sys.argv = [a for a in sys.argv]
_ARGV = list(sys.argv)


def _num(flag, default, cast):
    if flag in _ARGV:
        return cast(_ARGV[_ARGV.index(flag) + 1])
    return default


# SPEEDPROOF (c): worker counts. Plumbing only -- the gate is that outputs are byte-identical for any
# value. 1 = the serial loops in the main thread.
WORKERS = _num("--workers", 8, int)
TREE_WORKERS = _num("--tree-workers", WORKERS, int)
ROUTER_WORKERS = _num("--router-workers", WORKERS, int)
assert TREE_WORKERS >= 1 and ROUTER_WORKERS >= 1, (TREE_WORKERS, ROUTER_WORKERS)
# SPEEDPROOF (e), OFF by default: --finite-once 1. MEASURED 2026-09-28 (SPEEDPROOF_REPORT.md): 78% of
# every tree predict() is sklearn's input finiteness scan, which fire_architecture's patch_sklearn()
# replaces with daal4py's _assert_all_finite. It holds the GIL, so threads cannot overlap it, and it
# re-scans the WHOLE row block once per tree (3,200-10,700 times per block, same bytes each time).
# With the flag, the scan runs ONCE per block in the main thread -- the same function predict() would
# call, with the same allow_nan -- and the trees predict under sklearn's thread-local assume_finite.
# The per-tree lines are unchanged and no value can change: the scan only raises or returns.
FINITE_ONCE = _num("--finite-once", 0, int) == 1
# SPEEDPROOF (f), TEST ONLY: --router-pin 0 runs the router loop SERIALLY and WITHOUT the BLAS-1 pin, i.e.
# in the shipped script's BLAS state, so the tree-side changes (a)/(e) can be checked byte for byte
# against the unpatched script with nothing else moving (APP_PLAN 4.5, the speedup-2 gate). Parallel
# router workers are only allowed pinned.
ROUTER_PIN = _num("--router-pin", 1, int) == 1
assert ROUTER_PIN or ROUTER_WORKERS == 1, "--router-pin 0 requires --router-workers 1"
# SPEEDPROOF (d): temp matrices and the pool live here, inside the speedproof write scope.
TMP_DIR = "D:/treeroute/speedproof/tmp"
# SPEEDPROOF (g): the sha256 of THIS file as it is being run, recorded in every run folder. An earlier
# round credited runs to "the final file" that had in fact been made by earlier versions of it.
import hashlib  # noqa: E402
with open(os.path.abspath(__file__), "rb") as _fh:
    CODE_SHA256 = hashlib.sha256(_fh.read()).hexdigest()
del _fh
F64_NAME = "speedproof_inner_f64.npz"     # (g) float64 inner surfaces; copy-only, beside inner_preds.npz
from concurrent.futures import ThreadPoolExecutor  # noqa: E402


SMOKE = "--smoke" in _ARGV
FORCE = "--force" in _ARGV       # move a previous run's outputs aside instead of refusing to start
CELLS = _num("--cells", 40 if SMOKE else 100, int)       # test cells per test region
DCELLS = _num("--dcells", 40 if SMOKE else 100, int)     # donor cells per donor region
# default 100 for the full run: the documented headline is --npd 100 (10,700 columns), and a bare run
# used to get 50 while writing into the same output folder as the headline.
NPD = _num("--npd", 12 if SMOKE else 100, int)           # trees per donor region
# N3 (owner ruling 2026-09-24): no equivalence band for THIS run. The band is then DERIVED from the
# run itself -- the median jackknife SE of the arm contrasts, written to verdict.json as
# eq_band_derived -- and fixed here as EQ_UGM3 for every run after it. Not picked by hand.
# FIXED 2026-09-25 from Part 556, the first full run, exactly as N3 says: its derived band was
# 0.0395 ug/m3 (verdict.json eq_band_derived). Every run from here on reads contrasts against it.
EQ_UGM3 = 0.0395
# N2 guard settings -- owner rulings 2026-09-24 (QUESTIONS_ROUND5):
# Q2: a decline adopts the ARITHMETIC normal. Guess-normal has ONE definition across this project;
#     falling back to the geometric normal would let the median effect in through the guard's door.
# Q3: eligible arms are ranked by RAW MAE (what deploys); the gain is always DECOMPOSED instead
#     (normal effect vs routing effect, see the report). "saved" is kept only for diagnostics.
DECLINE_TO = "treesoff"
ADOPT_RANK = "mae"
MF = _num("--mf", 0.1, float)
TRAIN_END = 2019
INNER = 2016                       # inner fit <=2016, inner score 2017-2019
MIN_HIST = 24
HIT_TOL = 2.0                      # ug/m3 -- ACAG's own absolute error floor (ruling A11)
OUT = "D:/pm25_adapt"
# --run-dir: a NEW folder for a new configuration, so a later run never needs --force on `full`
# (which would move Part 556's shipped outputs aside). Default unchanged.
RUN_DIR = _num("--run-dir", os.path.join(OUT, "smoke" if SMOKE else "full"), str)
# *** SCIENCE CHANGE U2 (owner rulings 2026-09-25): ONE LINK SCHEMA, TWO LOG DEFINITIONS. ***
# The Type-2 layer is to use the same schema on every problem. log1p is not unit-free -- its "+1" is
# counted in the target's storage unit, so it bends ug/m3 strongly and a fraction hardly at all. The
# owner kept BOTH as candidate links and lets the layer pick:
#     log    = log1p(y)          back: expm1(p)        (Part 556's link, unchanged)
#     logc   = log(y + c)        back: exp(p) - c,  c = 1st percentile of the POSITIVE target values
#                                on the DONOR training rows (<= TRAIN_END), read once, logged
# Default is Part 556's set; the uniform-schema run passes --links identity,log,logc.
LINK_SET = _num("--links", "identity,log", str).split(",")
assert set(LINK_SET) <= {"identity", "log", "logc"} and "identity" in LINK_SET, LINK_SET
# --expect-from <inner_candidates.csv>: a REGRESSION GATE. Every arm this run shares with an earlier
# run is re-scored on the inner window at the same penalty; the MAEs must agree to EXPECT_TOL or the
# run stops before the (long) test pass. With the log1p arms this proves the bank, the frames and the
# router are Part 556's, so any logc difference is the link and nothing else.
EXPECT_FROM = _num("--expect-from", None, str)
EXPECT_TOL = 1e-4                  # ug/m3; thread-order noise in the ridge sits far below this
# THE PENALTY GRID. Levels span 0.1x to 100x the inherited ALPHA; ratios span the tree/context
# BALANCE. rho = A_CTX/ALPHA = 0.5 with mlt = 1.0 is exactly the inherited (0.5, 0.25), so the
# un-swept behaviour is a point inside the grid and can be asserted against. Sweeping the level
# alone would leave the balance a hand-set human constant -- the violation, not the fix.
# EDGE PICKS, AND WHAT THEY MEAN (corrected 2026-09-24, ruling A9). Two smoke runs picked mlt = 10,
# the top of the original grid, and the grid was extended to 100. The reason then given -- "fire's
# ALPHA is too weak, as reference_router_ridge_scaling predicts" -- was BACKWARDS: the smoke banks
# (96-320 trees) were NARROWER than fire's ~9,000, and that law predicts a SMALLER penalty for a
# narrower bank. A top-edge pick more plausibly means the trees add nothing and the router falls back
# to the climatology -- so TREES-OFF (= the climatology) is now an explicit candidate, and the RATIO
# axis, whose floor (0.25) the last smoke also hit, is extended DOWN to 0.0625.
LEVELS = [float(x) for x in _num("--levels", "0.1,0.3,1.0,3.0,10.0,30.0,100.0", str).split(",")]
RATIOS = [float(x) for x in _num("--ratios", "0.0625,0.125,0.25,0.5,1.0", str).split(",")]
GRID = [(m, r) for m in LEVELS for r in RATIOS]
SHIPPED_CELL = GRID.index((1.0, 0.5)) if (1.0, 0.5) in GRID else None

# BOTH imported modules parse sys.argv AT IMPORT TIME -- fire_architecture reads --npd/--alpha,
# and adaptation.py runs an argparse that REQUIRES --problem. Neither should see this script's
# flags, and adaptation is only used for derive_tier1 / fit_correctors / ETA, none of which
# depend on which problem was named. So the argv is replaced with a benign one before importing.
sys.argv = ["pm25_adaptation.py", "--problem", "fire"]

import panel_sentinel as _ps           # noqa: E402
import pm25_architecture as PA         # noqa: E402
import pm25_ban as BAN                 # noqa: E402
import pm25_split as SPLIT             # noqa: E402
import fire_architecture as FA         # noqa: E402
from coral_architecture import solve_local     # noqa: E402
from sklearn.tree import DecisionTreeRegressor  # noqa: E402
from threadpoolctl import threadpool_limits     # noqa: E402
import sklearn                                  # noqa: E402  (SPEEDPROOF (e): config_context)
import sklearn.utils.validation as _skval       # noqa: E402  (the PATCHED _assert_all_finite)

# SPEEDPROOF (d): the pool goes to TMP_DIR too. build_pool() and cleanup() read PA.POOL at call time.
PA.POOL = os.path.join(TMP_DIR, "pool_%d.f32" % os.getpid())

CTX = ["month", "lat"]
ALPHA, A_CTX = FA.ALPHA, FA.A_CTX
# The corrector blend weight in q = p + eta * c. adaptation.py has no module-level
# constant for it -- it is written inline as the shipped arm
#     adaptation.py:1395  for nm, cm, eta in [("base", None, 0.0), ("corrector", Cm, 1.0)]
# so 1.0 is taken from there rather than invented, and named here so a future sweep
# has something to sweep.
ETA = 1.0


def log(m):
    """Console AND RUN_DIR/run.log. The first full run's verdict existed only in a console window;
    when that window went, the decision went with it."""
    s = "[%s] %s" % (time.strftime("%H:%M:%S"), m)
    print(s, flush=True)
    os.makedirs(RUN_DIR, exist_ok=True)
    with open(os.path.join(RUN_DIR, "run.log"), "a", encoding="utf-8") as f:
        f.write(s + "\n")


_T0 = [time.time()]
TIMINGS = {}
COLS_SEC = [0.0]      # SPEEDPROOF: total seconds in columns() (tree answers), summed over matrices
ROUTER_SEC = [0.0]    # SPEEDPROOF: total seconds in route_sweep / route_percell, summed over arms
# SPEEDPROOF (g): COLS_SEC split three ways, summed over matrices: building the row matrix Vm
# (fillna / astype / vstack), predicting the trees, and copying each block into the memmap + flush().
VM_SEC, PRED_SEC, WRITE_SEC = [0.0], [0.0], [0.0]

# THE TREE-COLUMN MATRIX CACHE, module level so the crash handler in main() can always reach it.
# (frame pair, corrector tag) -> (memmap, path). run_arm keeps AT MOST ONE entry.
ACACHE = {}


def drop_cache():
    """Release the cached tree-column matrix and DELETE its file. At most ONE matrix is ever on disk
    (17.46 GB inner, 21.57 GB test at --npd 100) instead of two inner plus three test ones (~104 GB
    against ~41 GB free). Also called from main()'s finally-block, so a crash cleans up too.

    THE MAPPING MUST BE CLOSED BEFORE THE DELETE. On Windows a file with an open memory map
    cannot be removed. The previous version called os.remove while ACACHE still referenced
    every memmap, so each delete raised PermissionError, a bare `except: pass` swallowed it,
    and every "dropped" file stayed on disk (reproduced 2026-09-24). So: take the paths, drop
    every reference, collect, then delete -- and say so LOUDLY if a delete still fails. The disk
    pre-check before the next matrix then stops the run with the numbers rather than letting it
    die mid-write."""
    import gc
    paths = [path_ for _, path_ in ACACHE.values()]
    ACACHE.clear()
    gc.collect()
    for path_ in paths:
        try:
            os.remove(path_)
        except OSError as e:
            log("  !! WARNING: could not delete %s (%s) -- disk may run out" % (path_, e))


def phase_done(name):
    """Per-phase wall clock, logged AND persisted -- the handoff's '<40 min for inner base' rule could
    never be checked because no breakdown existed (bank vs column build vs routing)."""
    dt = (time.time() - _T0[0]) / 60.0
    TIMINGS[name] = round(dt, 2)
    log("  [timing] %-28s %7.1f min (%.1f s)" % (name, dt, dt * 60.0))
    _T0[0] = time.time()


# ---------------------------------------------------------------------------------- scoring
def _demean(v, g):
    """Subtract each group's own mean (per region). g=None -> one pooled mean."""
    if g is None:
        return v - v.mean()
    return v - pd.Series(v).groupby(g).transform("mean").values


def score(y, p, clim, groups=None):
    """anomaly-R2 (deployable), pattern-R2 (diagnostic), MAE, hit-rate -- IN ANOMALY SPACE.

    GUESS-NORMAL IS THE CLIMATOLOGY, NOT ZERO. The first version of this function scored against
    predicting 0 ug/m3 and reported anomaly-R2 +0.956 and hit-rate 0.998. Neither was skill: a
    model that merely reproduces the seasonal cycle beats "always predict zero" overwhelmingly,
    because the seasonal cycle is most of the variance. The project's own note says pooled R2 sits
    on a ~77% climatology floor for exactly this reason. So every number here is computed on
        anomaly = value - that cell's own month climatology, fitted on the calibration years ONLY
    and guess-normal is anomaly 0.

    pattern-R2 then removes the TEST-WINDOW MEAN from both truth and prediction. It USES TEST
    INFORMATION, so it is a diagnostic upper bound and never a deployable score -- it exists
    because this target's train-to-test level shift is ~half a test standard deviation with a sign
    that varies by region, which drives anomaly-R2 negative on its own.

    PATTERN-R2 DEMEANS PER GROUP (pass groups = region labels). The level shift this diagnostic exists
    to remove has a sign that VARIES BY REGION, so one pooled mean leaves most of it in (smoke: pooled
    +0.055 vs per-region +0.026). `pat_pooled` is kept only for comparison with older printouts.

    HIT-RATE = share of rows within +/-HIT_TOL ug/m3 of the truth, and `hit0` the same for
    guess-normal -- a hit-rate needs a do-nothing baseline to mean anything, and "right side of
    normal" has none (anomaly 0 has no sign). That older measure survives as `dirhit`, a bonus.
    """
    ok = np.isfinite(y) & np.isfinite(p) & np.isfinite(clim)
    y, p, c = y[ok], p[ok], clim[ok]
    g = None if groups is None else np.asarray(groups)[ok]
    if len(y) < 10:
        return dict(n=len(y))
    ay, ap = y - c, p - c                      # truth and prediction as ANOMALIES
    s0 = float(np.sum(ay ** 2))                # guess-normal predicts anomaly 0
    r2 = 1.0 - float(np.sum((ay - ap) ** 2)) / s0 if s0 > 0 else np.nan

    def _pat(gg):
        yd, pd_ = _demean(ay, gg), _demean(ap, gg)
        s0d = float(np.sum(yd ** 2))
        return 1.0 - float(np.sum((yd - pd_) ** 2)) / s0d if s0d > 0 else np.nan

    big = np.abs(ay) > np.nanpercentile(np.abs(ay), 50)
    return dict(n=len(y), r2=r2, pat=_pat(g), pat_pooled=_pat(None),
                mae=float(np.mean(np.abs(y - p))),          # raw ug/m3, comparable across arms
                mae0=float(np.mean(np.abs(ay))),            # what guess-normal costs
                hit=float(np.mean(np.abs(y - p) <= HIT_TOL)),
                hit0=float(np.mean(np.abs(ay) <= HIT_TOL)),
                dirhit=float(np.mean(np.sign(ap[big]) == np.sign(ay[big]))) if big.any() else np.nan)


def route_percell(hist, test, A, ntree, yh, gmean, cut, pen=(1.0, 0.5), ccol="clim",
                  trees_off=False):
    """One block-penalised ridge per test cell, fitted on THAT CELL'S OWN history up to `cut`.

    `ccol` names the climatology column the ridge gets as its unpenalised input: "clim" (raw ug/m3)
    for identity-link arms, "lclim" (mean of log1p y) for log arms -- science change A8.
    trees_off=True drops the tree block entirely (intercept + climatology + context); A is not read.

    hist and test are disjoint frames by construction, so this is already strict: no scored row
    ever calibrates another. The assertions below ARE the claim, not decoration.

    `cut` IS A PARAMETER AND NOT TRAIN_END, because this router is called twice with different
    boundaries and hard-coding one made the other fail. The INNER decision pass fits <=2016 and
    scores 2017-2019 -- both inside the calibration history -- while the TEST pass fits <=2019 and
    scores 2020-2023. A fixed 2019 boundary would have rejected the inner pass as "a training row
    entered the scored set", which is exactly what it did the first time this ran.
    """
    assert int(hist.year.max()) <= cut, "calibration history crossed its cut (%d)" % cut
    assert int(test.year.min()) > cut, "a calibration row entered the scored set (cut %d)" % cut
    out = np.full(len(test), np.nan)
    hc, tc = hist.cell.values, test.cell.values
    order = np.argsort(hc, kind="stable")
    hs = hc[order]
    Ch = np.column_stack([hist[c].values for c in CTX]).astype(np.float64)
    Ct = np.column_stack([test[c].values for c in CTX]).astype(np.float64)
    mu, sd = Ch.mean(0), Ch.std(0) + 1e-9
    Ch, Ct = (Ch - mu) / sd, (Ct - mu) / sd
    nh, nfit, nfall = len(hist), 0, 0
    # SPEEDPROOF (b): the cell list and the fallback rule are fixed SERIALLY, in the shipped order;
    # only the fitted cells' solves go to the workers. Column arrays are read once here so no worker
    # touches a pandas object.
    hM, tM = hist[ccol].values, test[ccol].values
    plan = []
    for cell in pd.unique(tc):
        lo, hi = np.searchsorted(hs, cell, "left"), np.searchsorted(hs, cell, "right")
        hidx = order[lo:hi]
        tsel = np.flatnonzero(tc == cell)
        if len(hidx) < MIN_HIST or not np.isfinite(yh[hidx]).all():
            out[tsel] = gmean
            nfall += len(tsel)
            continue
        plan.append((hidx, tsel))

    def _one_cell(item):
        # the shipped per-cell body, unchanged apart from reading hM / tM instead of the frames
        hidx, tsel = item
        M = hM[hidx]
        blk_h = [np.ones(len(hidx)), M - M.mean(), Ch[hidx]]
        blk_t = [np.ones(len(tsel)), tM[tsel] - M.mean(), Ct[tsel]]
        if not trees_off:
            blk_h.append(np.asarray(A[hidx], np.float64))
            blk_t.append(np.asarray(A[nh + tsel], np.float64))
        Xc, Xt = np.column_stack(blk_h), np.column_stack(blk_t)
        b = solve_local(Xc, yh[hidx], np.ones(len(hidx)), 0 if trees_off else ntree, len(CTX),
                        ALPHA * pen[0], ALPHA * pen[0] * pen[1])
        return Xt @ b

    for (hidx, tsel), v in zip(plan, _par_cells(_one_cell, plan)):
        out[tsel] = v
        nfit += 1
    return out, nfit, nfall


def route_sweep(hist, test, A, ntree, yh, gmean, cut, grid, ccol="clim", with_off=False):
    """route_percell over a PENALTY GRID, building each cell's design matrix ONCE.

    Returns (P, P0, nfit, nfall). P0 is the TREES-OFF prediction -- ONE column, because it is the
    climatology itself and no penalty changes it (see the with_off block) -- when with_off=True,
    else None.

    WHY A SWEEP AT ALL. ALPHA=0.5 and A_CTX=0.25 are imported from fire_architecture -- hand-set
    constants tuned on a different problem at a different bank width. adaptation.py calls the fixed
    tree/context RATIO "the last genuine Tier-2 violation in fire's adaptation layer", and
    reference_router_ridge_scaling records that ridge shrinkage is NOT scale-invariant in column
    count (it collapsed ~6.6x going 3k -> 15k). Running PM2.5 at 10,700 columns on fire's penalties
    would be an assumption; sweeping replaces it with a measurement.

    THE GRID IS (LEVEL x RATIO), reparameterised so the current behaviour is a POINT INSIDE it:
        a_tree = ALPHA * mlt          a_ctx  = ALPHA * mlt * rho
    At rho = A_CTX/ALPHA = 0.5 and mlt = 1.0 this is exactly (ALPHA, A_CTX), which is the contract
    check -- that cell MUST reproduce the un-swept route, and an assertion below enforces it.
    Sweeping the LEVEL alone would select a magnitude while leaving the BALANCE between the tree
    block and the context block a human constant, which is the violation, not the fix.

    COST. solve_local dispatches to the dual whenever n < p, which is always here (216 rows against
    10,703 columns), so each solve is O(n^2 p) on a 216x216 system rather than forming a 10,703^2
    Gram. The expensive per-cell work -- reading A from the memmap and upcasting to float64 -- is
    done ONCE and shared across the whole grid, so the grid multiplies only the solve.
    """
    assert int(hist.year.max()) <= cut, "calibration history crossed its cut (%d)" % cut
    assert int(test.year.min()) > cut, "a calibration row entered the scored set (cut %d)" % cut
    out = np.full((len(test), len(grid)), np.nan)
    out0 = np.full(len(test), np.nan) if with_off else None
    hc, tc = hist.cell.values, test.cell.values
    order = np.argsort(hc, kind="stable")
    hs = hc[order]
    Ch = np.column_stack([hist[c].values for c in CTX]).astype(np.float64)
    Ct = np.column_stack([test[c].values for c in CTX]).astype(np.float64)
    mu, sd = Ch.mean(0), Ch.std(0) + 1e-9
    Ch, Ct = (Ch - mu) / sd, (Ct - mu) / sd
    nh, nfit, nfall = len(hist), 0, 0
    o = 2 + len(CTX)                                  # intercept, climatology, context
    # SPEEDPROOF (b): cell list, fallback rule and the NVERIFY cells are fixed SERIALLY, in the
    # shipped order. The shipped loop checked `nfit < NVERIFY` with nfit = fitted cells so far, so
    # a cell is verified iff fewer than NVERIFY fitted cells precede it -- computed here, not by
    # whichever thread finishes first.
    hM, tM = hist[ccol].values, test[ccol].values
    plan = []
    for cell in pd.unique(tc):
        lo, hi = np.searchsorted(hs, cell, "left"), np.searchsorted(hs, cell, "right")
        hidx = order[lo:hi]
        tsel = np.flatnonzero(tc == cell)
        if len(hidx) < MIN_HIST or not np.isfinite(yh[hidx]).all():
            out[tsel, :] = gmean
            if with_off:
                out0[tsel] = gmean
            nfall += len(tsel)
            continue
        plan.append((cell, hidx, tsel, len(plan) < NVERIFY))

    def _one_cell(item):
        # the shipped per-cell body; results come back instead of being written into `out` here
        cell, hidx, tsel, verify = item
        M = hM[hidx]
        # BUILT ONCE, SOLVED len(grid) TIMES. This is the whole reason the sweep is affordable.
        Xc = np.column_stack([np.ones(len(hidx)), M - M.mean(), Ch[hidx],
                              np.asarray(A[hidx], np.float64)])
        Xt = np.column_stack([np.ones(len(tsel)), tM[tsel] - M.mean(), Ct[tsel],
                              np.asarray(A[nh + tsel], np.float64)])
        w = np.ones(len(hidx))
        if Xc.shape[0] < Xc.shape[1]:
            # THE DUAL REGIME -- the one solve_local itself uses whenever rows < columns, i.e.
            # always at full scale. _grid_dual solves ALL grid points from one pair of k x k
            # Grams instead of rebuilding them per point: same answer (checked below), ~20x faster
            # (measured by the 2026-09-24 review: 1.58 s -> 0.08 s per cell at 10,700 trees).
            Pk = _grid_dual(Xc, yh[hidx], Xt, ntree, len(CTX), grid)
            if verify:
                # FAIL LOUD if the shortcut ever disagrees with the reference solver.
                ref = np.column_stack([Xt @ solve_local(Xc, yh[hidx], w, ntree, len(CTX),
                                                        ALPHA * m_, ALPHA * m_ * r_)
                                       for m_, r_ in grid])
                err = float(np.abs(Pk - ref).max())
                assert err < 1e-8, ("shared-Gram grid solve disagrees with solve_local by %.3g "
                                    "on cell %s" % (err, cell))
        else:
            Pk = np.full((len(tsel), len(grid)), np.nan)
            for k, (mlt, rho) in enumerate(grid):
                b = solve_local(Xc, yh[hidx], w, ntree, len(CTX), ALPHA * mlt, ALPHA * mlt * rho)
                Pk[:, k] = Xt @ b
        p0 = None
        if with_off:
            # TREES-OFF IS THE CLIMATOLOGY ITSELF, so it is ONE column, not a grid. The per-cell
            # climatology is the cell x month mean over exactly these fit rows, so the unpenalised
            # climatology column takes coefficient 1, the residual has zero mean in every month
            # and is orthogonal to the month context, and lat is constant within a cell: the
            # context block cannot contribute at ANY penalty. Solved here rather than assumed.
            b0 = solve_local(Xc[:, :o], yh[hidx], w, 0, len(CTX), ALPHA, A_CTX)
            p0 = Xt[:, :o] @ b0
        return Pk, p0

    for (cell, hidx, tsel, verify), (Pk, p0) in zip(plan, _par_cells(_one_cell, plan)):
        out[tsel, :] = Pk
        if with_off:
            out0[tsel] = p0
        nfit += 1
    return out, out0, nfit, nfall


def _par_cells(fn, items):
    """SPEEDPROOF (b). fn(item) for every item; results in ITEM ORDER.

    BLAS is pinned to 1 thread for the whole call at ANY worker count, so each cell's arithmetic is
    the same whichever thread runs it and however many run at once. ROUTER_WORKERS == 1 runs the
    plain loop in the calling thread (the serial reference). A worker's exception (e.g. the NVERIFY
    assertion) is re-raised here, in the main thread, when its result is collected -- fail loud."""
    if not ROUTER_PIN:
        return [fn(it) for it in items]          # (f) test only: the shipped loop, shipped BLAS
    with threadpool_limits(limits=1, user_api="blas"):
        if ROUTER_WORKERS <= 1 or len(items) <= 1:
            return [fn(it) for it in items]
        ex = ThreadPoolExecutor(max_workers=ROUTER_WORKERS)
        try:
            return list(ex.map(fn, items))
        finally:
            ex.shutdown(wait=True, cancel_futures=True)


NVERIFY = 3        # cells per sweep on which the shared-Gram shortcut is checked against solve_local
ROW_BLOCK = 12288  # rows per tree-matrix write block: ~0.53 GB of RAM at 10,700 trees (ruling R2)


def _grid_dual(Xc, yc, Xt, ntree, nctx, grid):
    """solve_local's DUAL path (coral_architecture._solve_local_dual, unit weights) for EVERY
    (mlt, rho) grid point at once. The projection of the unpenalised block and the two block Grams
    (context, trees) do not depend on the penalty, so they are built ONCE; each grid point is then
    a k x k Cholesky plus an O(k p) back-substitution. The penalty traces are taken on the RAW
    blocks, exactly as the reference does (its docstring explains why that matters)."""
    from scipy.linalg import solve_triangular
    o = 2
    k = Xc.shape[0]
    U, P = Xc[:, :o], Xc[:, o:]
    Q, _ = np.linalg.qr(U)
    Py = yc - Q @ (Q.T @ yc)
    PP = P - Q @ (Q.T @ P)
    Pc, Pt = PP[:, :nctx], PP[:, nctx:]
    Gc, Gt = Pc @ Pc.T, Pt @ Pt.T
    sc0 = max(float((P[:, :nctx] ** 2).sum()) / max(nctx, 1), 1e-12)
    st0 = max(float((P[:, nctx:] ** 2).sum()) / max(ntree, 1), 1e-12)
    out = np.empty((Xt.shape[0], len(grid)))
    for j, (mlt, rho) in enumerate(grid):
        s2c, s2t = ALPHA * mlt * rho * sc0, ALPHA * mlt * st0
        G = Gc / s2c + Gt / s2t
        G.flat[:: k + 1] += 1.0
        try:
            L = np.linalg.cholesky(G)
            u = solve_triangular(L.T, solve_triangular(L, Py, lower=True), lower=False)
        except np.linalg.LinAlgError:
            u = np.linalg.lstsq(G, Py, rcond=None)[0]
        bP = np.r_[Pc.T @ u / s2c, Pt.T @ u / s2t]
        bU = np.linalg.lstsq(U, yc - P @ bP, rcond=None)[0]
        out[:, j] = Xt @ np.r_[bU, bP]
    return out


def _jsonable(o):
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


def _run():
    """The run itself. main() wraps it with the pre-flight checks and the guaranteed cleanup."""
    import json
    os.makedirs(RUN_DIR, exist_ok=True)
    import adaptation as AD
    # adaptation.py's own log() appends to os.path.join(AD.OUT, "_adaptation.log"), and AD.OUT was
    # derived from the benign argv above -- D:/adaptation/fire_full. So PM2.5's Tier-1 and corrector
    # lines were being written into FIRE's log. Point it at this run's folder instead.
    AD.OUT = RUN_DIR
    VERDICT = {"argv": _ARGV, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    log("=" * 92)
    log("RUN START %s | argv %s" % (VERDICT["started"], " ".join(_ARGV[1:])))

    donors = list(SPLIT.DONORS)
    tests = list(SPLIT.TEST)
    if SMOKE:
        donors, tests = donors[:8], tests[:3]
    log("PM2.5 | %d donors | %d test | %d test cells/reg | %d trees/donor"
        % (len(donors), len(tests), CELLS, NPD))

    # ---------------------------------------------------------------- pool
    PA.N_CELLS = max(CELLS, DCELLS)
    mm, nrows, feat, meta = PA.build_pool(n_cells=max(CELLS, DCELLS), regions=donors + tests)
    BAN.report(log)
    log("  %d features reach the model: %s" % (len(feat), ", ".join(feat)))
    phase_done("pool")
    # cell_id is a STRING like "alaska_interior_taiga_-4036_2275". The router sorts and binary-
    # searches on cells, so it needs an integer code -- factorised ONCE here, on the pool, so
    # donor/history/test frames cannot disagree about which code means which cell.
    meta["cell"] = pd.factorize(meta.cell_id.values)[0].astype(np.int64)

    def stride(reg, n):
        c = np.sort(meta.cell[meta.reg.values == reg].unique())
        return set(c[:: max(1, len(c) // n)][:n].tolist()) if len(c) > n else set(c.tolist())

    dsel = np.zeros(len(meta), bool)
    for r in donors:
        dsel |= (meta.reg.values == r) & meta.cell.isin(stride(r, DCELLS)).values
    i_don = np.flatnonzero(dsel & (meta.year.values <= TRAIN_END))
    hi_, ti_ = [], []
    for t in tests:
        sel = (meta.reg.values == t) & meta.cell.isin(stride(t, CELLS)).values
        hi_.append(np.flatnonzero(sel & (meta.year.values <= TRAIN_END)))
        ti_.append(np.flatnonzero(sel & (meta.year.values > TRAIN_END)))
    i_hist, i_test = np.concatenate(hi_), np.concatenate(ti_)

    # THE TWO-TIER BOUNDARY. If either fires, the run is not what the docstring claims.
    assert int(meta.iloc[i_don].year.max()) <= TRAIN_END, "donor window not closed"
    assert not (set(meta.iloc[i_don].reg.unique()) & set(tests)), \
        "a TEST region reached the donor block -- base models would see it"

    don = PA.gather(mm, feat, meta, i_don)
    hist = PA.gather(mm, feat, meta, i_hist)
    test = PA.gather(mm, feat, meta, i_test)
    del mm
    PA.cleanup()
    for f in (don, hist, test):
        f["ecoid"] = f.reg.map({r: i for i, r in enumerate(donors + tests)})
    # SORT BY CELL. MEASURED, not guessed: the pool is written year by year, so one cell's 216
    # monthly rows sit 264 apart. The router reads A[hidx] for one cell at a time, and on an 18.4 GB
    # memmap that cannot be cached in 15.8 GB of RAM every one of those 216 offsets is a seek on a
    # 7200 RPM platter -- timed at 10.9 s scattered against 1.75 s contiguous, and the first full
    # run spent 3 h 49 m on a single arm because of it. Sorting by cell makes each cell's block one
    # sequential read. The frames' ORDER is what A's row order inherits, so this must happen BEFORE
    # any tree column is written, and the year filters that build the inner window preserve relative
    # order so they stay contiguous too.
    don = don.sort_values(["cell", "t"]).reset_index(drop=True)
    hist = hist.sort_values(["cell", "t"]).reset_index(drop=True)
    test = test.sort_values(["cell", "t"]).reset_index(drop=True)

    gmean = float(don.y.mean())
    lgmean = float(np.log1p(don.y.values).mean())
    # U2: the logc offset, from DONOR rows only (i_don is <= TRAIN_END by the assertion above), so it
    # is one constant for the whole run -- identical on the inner and the test pass -- and no test
    # region and no 2020-2023 row can move it.
    ypos = don.y.values[np.isfinite(don.y.values) & (don.y.values > 0)]
    C_LOG = float(np.percentile(ypos, 1)) if len(ypos) else float("nan")
    lcgmean = float(np.log(don.y.values + C_LOG).mean()) if "logc" in LINK_SET else float("nan")
    if "logc" in LINK_SET:
        assert np.isfinite(C_LOG) and C_LOG > 0, "logc offset undefined (%s)" % C_LOG
        log("  U2 logc link: c = %.6g ug/m3 = 1st percentile of %s positive donor-row values "
            "(donor min %.6g, median %.6g)" % (C_LOG, format(len(ypos), ","), float(ypos.min()),
                                              float(np.median(ypos))))

    def add_clim(src, frames):
        """Write `clim` (per cell-month MEAN of y, ug/m3), `lclim` (per cell-month MEAN of
        log1p(y) -- science change A8) and, for the logc link, `lcclim` (per cell-month MEAN of
        log(y + c) -- the same rule A8 applies to log1p) into every frame, computed from `src` rows
        ONLY. Fallbacks: the cell's own mean, then the donor mean. Whatever `src` is, NO row outside
        it contributes -- that is the property A6 depends on."""
        s = src[["cell", "month", "y"]].assign(ly=np.log1p(src.y.values))
        cc, cm = s.groupby(["cell", "month"]).y.mean(), s.groupby("cell").y.mean()
        lc, lm = s.groupby(["cell", "month"]).ly.mean(), s.groupby("cell").ly.mean()
        if "logc" in LINK_SET:
            s = s.assign(lcy=np.log(src.y.values + C_LOG))
            lcc, lcm = s.groupby(["cell", "month"]).lcy.mean(), s.groupby("cell").lcy.mean()
        for f in frames:
            ix = f.set_index(["cell", "month"]).index
            v = pd.Series(ix.map(cc), index=f.index).astype(float)
            f["clim"] = v.fillna(f.cell.map(cm)).fillna(gmean).values
            lv = pd.Series(ix.map(lc), index=f.index).astype(float)
            f["lclim"] = lv.fillna(f.cell.map(lm)).fillna(lgmean).values
            if "logc" in LINK_SET:
                cv = pd.Series(ix.map(lcc), index=f.index).astype(float)
                f["lcclim"] = cv.fillna(f.cell.map(lcm)).fillna(lcgmean).values

    # TEST PASS climatology: the full calibration history (2003-2019) -- it must not see 2020-2023.
    add_clim(hist, [hist, test])
    y = test.y.values.astype(np.float64)
    yh = hist.y.values.astype(np.float64)
    log("  donor %s | history %s | SCORED %s rows"
        % (format(len(don), ","), format(len(hist), ","), format(len(y), ",")))

    # ---------------------------------------------------------------- TIER 1
    rpu = float(hist.groupby("cell").size().median())
    t1 = AD.derive_tier1(yh, rpu, "pm25")
    VERDICT["tier1"] = t1
    VERDICT["rows"] = {"donor": len(don), "history": len(hist), "scored": len(y)}
    VERDICT["features"] = list(feat)

    # ---------------------------------------------------------------- bank
    Vd = don[feat].fillna(0).values.astype(np.float32)
    yd = don.y.values.astype(np.float64)
    base_rows = np.arange(len(don))
    trees, inbag, home = [], [], []
    for e, g in don.groupby("ecoid"):
        gi = base_rows[don.ecoid.values == e]
        n = len(gi)
        # HALF THE REGION, NOT FIRE'S FIXED 800-ROW CAP. A PM2.5 donor region has ~8,640 rows at
        # smoke and ~21,600 at full scale, so an 800-row draw is 9% of it -- which is legitimate
        # bagging but leaves 91% out-of-bag, and fit_correctors asserts the held-out share sits in
        # [0.15, 0.80] because a share near 1.0 is the signature of a real bug (out-of-bag taken
        # against ALL regions instead of the tree's own). That bug is NOT present here; the band's
        # assumption is. Drawing k from n with replacement leaves exp(-k/n) out of bag, so k = n/2
        # gives 0.61 and k = 800 of 8,640 gives 0.91. Half the region is both in band and closer to
        # textbook bagging than a fixed row cap that was sized for a different problem's regions.
        take = max(30, int(0.5 * n))
        for j in range(NPD):
            # INHERITED SEED, LABELLED AS THE NO-SEEDS RULE REQUIRES (ruling A10). This is fire's
            # SHIPPED bank formula, RandomState(SEED*1000 + e*17 + j) with SEED = 7
            # (fire_evt_arch.py:74; adaptation.py:2348-2351), copied so the two banks are built the
            # same way. Constant, never varied, never swept: it fixes one bag per tree.
            rsj = np.random.RandomState(7 * 1000 + int(e) * 17 + j)
            idx = rsj.choice(n, size=take, replace=True)
            trees.append(DecisionTreeRegressor(max_depth=8, min_samples_leaf=5, max_features=MF,
                                               random_state=700 + j).fit(Vd[gi][idx], yd[gi][idx]))
            inbag.append(gi[np.unique(idx)])
            home.append(gi)
    log("  bank %d trees / %d donor regions" % (len(trees), don.ecoid.nunique()))
    corr = AD.fit_correctors(trees, inbag, home, Vd, yd, MF, placebo=False)
    plac = AD.fit_correctors(trees, inbag, home, Vd, yd, MF, placebo=True)
    phase_done("bank + correctors")

    # ---------------------------------------------------------------- tree columns
    ntree = len(trees)
    def columns(Vm, tag, use_corr):
        """Tree columns for ONE pair of frames, on disk.

        FLOAT32, NOT FIRE'S FLOAT16, AND THE REASON IS THE TARGET'S SCALE. fire's open_A stores
        float16 because its predictions are burned fractions and occurrence probabilities in
        [0, 1], where float16 resolves about 1e-3 -- well inside the measurement precision. PM2.5
        reaches 689 ug/m3, where float16's step is ~0.5, which is COARSER than the target's own
        resolution of ~0.01. Reusing that storage choice would quantise every tree column in the
        dirty regions, which are the ones that matter. Cost at --npd 100: ~17.5 GB (inner) and
        ~21.5 GB (test) per matrix instead of half that -- which is why only ONE may exist at a time.

        BUILT PER FRAME PAIR, not once. The router indexes A[hix] and A[nh + tsel], so the matrix
        must be laid out as exactly the rows it is asked about. The inner decision window passes
        DIFFERENT frames from the test pass, and sharing one matrix between them would silently
        mis-align every index.

        WRITTEN IN ROW BLOCKS, NEVER COLUMN BY COLUMN (ruling R2, handoff rule 2.1.2). The matrix
        is C-ordered, so column j of a 500k x 10,700 float32 array is strided by 42,800 bytes:
        writing one column touched ~500k scattered pages across ~22 GB, and that happened 10,700
        times per matrix -- the forbidden pattern at its worst on a 7200 RPM drive. Now every tree
        predicts one block of ROW_BLOCK rows into RAM, and the block is written as one contiguous
        slab and flushed. Tree prediction is row-wise, so the numbers are IDENTICAL.
        """
        # SPEEDPROOF (d): temp matrix in TMP_DIR, not D:/pm25.
        os.makedirs(TMP_DIR, exist_ok=True)
        path = os.path.join(TMP_DIR, "A_%s_%d.f32" % (tag, os.getpid()))
        n = len(Vm)
        A = np.memmap(path, np.float32, "w+", shape=(n, ntree))
        buf = np.empty((min(ROW_BLOCK, n), ntree), np.float32)
        # SPEEDPROOF (a): the trees of ONE row block are split into contiguous column ranges, one per
        # thread. Each thread runs exactly the shipped per-tree lines and writes only its own columns
        # of `buf`; a tree's answer depends only on the tree and the rows, so the bytes are the same
        # for any worker count. The block still goes to disk as one slab, as before.
        nw = max(1, min(TREE_WORKERS, ntree))
        cuts = [ntree * i // nw for i in range(nw + 1)]
        chunks = [(cuts[i], cuts[i + 1]) for i in range(nw) if cuts[i + 1] > cuts[i]]

        def _fill_body(V, m, lo, hi):
            for j in range(lo, hi):
                t = trees[j]
                p = t.predict(V).astype(np.float32)
                if use_corr is not None and use_corr[j] is not None:
                    p = p + ETA * use_corr[j].predict(V).astype(np.float32)
                buf[:m, j] = p

        def _fill(V, m, lo, hi):
            if FINITE_ONCE:
                # sklearn's config is THREAD-LOCAL: this affects only the thread running this chunk
                with sklearn.config_context(assume_finite=True):
                    _fill_body(V, m, lo, hi)
            else:
                _fill_body(V, m, lo, hi)

        ex = ThreadPoolExecutor(max_workers=nw) if nw > 1 else None
        try:
            for a0 in range(0, n, ROW_BLOCK):
                b0 = min(a0 + ROW_BLOCK, n)
                V = Vm[a0:b0]
                t_p = time.time()                          # (g) prediction seconds, incl. the scan
                if FINITE_ONCE:
                    # SPEEDPROOF (e): the scan every predict() would run, ONCE for this block, with the
                    # allow_nan the trees' own _validate_X_predict would pass. Fails loud, as before.
                    _skval._assert_all_finite(V, allow_nan=trees[0]._support_missing_values(V),
                                              input_name="X")
                if ex is None:
                    _fill(V, b0 - a0, 0, ntree)           # --workers 1: the serial loop
                else:
                    futs = [ex.submit(_fill, V, b0 - a0, lo, hi) for lo, hi in chunks]
                    for f_ in futs:
                        f_.result()                        # re-raises a worker's error here
                t_w = time.time()
                PRED_SEC[0] += t_w - t_p
                A[a0:b0, :] = buf[:b0 - a0]
                A.flush()      # hand the dirty pages back per block, or RSS grows to the whole file
                WRITE_SEC[0] += time.time() - t_w          # (g) copy into the memmap + flush() call
        finally:
            if ex is not None:
                ex.shutdown(wait=True, cancel_futures=True)
        del buf
        return A, path

    LINKS = {"identity": (lambda v: v, lambda v: v),
             # log1p, not log: the target's floor is 0.006 and log would blow up on it. log1p is
             # monotone, defined at zero, and ~log for the values that matter.
             "log": (np.log1p, np.expm1),
             # U2: unit-free log. c is read from donor rows above; the unpenalised intercept absorbs
             # a change of units, so the fitted predictions scale with the target.
             "logc": (lambda v: np.log(v + C_LOG), lambda v: np.exp(v) - C_LOG)}
    # The climatology each link routes on (A8 for log1p, the same rule for logc).
    CCOL = {"identity": "clim", "log": "lclim", "logc": "lcclim"}
    # Arm names per link -- identity keeps Part 556's names so every earlier table still reads.
    ARM = {"identity": ("base", "corrector", "placebo", "treesoff"),
           "log": ("log", "log_corrector", "log_placebo", "log_treesoff"),
           "logc": ("logc", "logc_corrector", "logc_placebo", "logc_treesoff")}

    def normal_values(link, frame):
        """What link L's trees-off arm must equal: its normal, back on the ug/m3 scale."""
        return {"identity": lambda: frame.clim.values,
                "log": lambda: np.expm1(frame.lclim.values),
                "logc": lambda: np.exp(frame.lcclim.values) - C_LOG}[link]()

    def run_arm(name, link, use_corr, frame_h, frame_t, yh_, y_, cut,
                sweep=None, pen=(1.0, 0.5), trees_off=False):
        """One arm end to end: link the target, build this frame pair's tree columns, route.

        THE LINK IS APPLIED TO THE TARGET AND UNDONE ON THE PREDICTION. The ridge is fitted on
        f(y) and the tree columns are left alone, which is the same shape fire uses for arcsine.
        finv(p) puts the prediction back on ug/m3 so every arm is scored on the SAME units -- an
        MAE compared across arms in different spaces would be meaningless.
        The climatology input follows the link: `lclim` for log arms, `clim` otherwise (A8).

        Returns (P, P0, nfit, nfall) with a sweep -- P0 the trees-off surface for arms without a
        corrector, else None -- and (p, nfit, nfall) at a single penalty.
        """
        f, finv = LINKS[link]
        ccol = CCOL[link]
        if trees_off:
            assert sweep is None, "trees-off sweeps come from route_sweep(with_off=True)"
            t_r = time.time()
            p, nfit, nfall = route_percell(frame_h, frame_t, None, ntree, f(yh_), float(f(gmean)),
                                           cut, pen, ccol=ccol, trees_off=True)
            _router_log(name, t_r, nfit)
            return finv(p), nfit, nfall
        # THE LINK CHANGES THE TARGET, NOT THE COLUMNS. base and log see identical tree columns,
        # and so do corrector and log_corrector -- so four arms need TWO matrices, not four. Each
        # build is 10,700 tree predictions over ~500k rows, so caching on (frame pair, corrector)
        # halves the most expensive step in the run.
        ck = (id(frame_h), id(frame_t), "corr" if use_corr is corr else
              ("plac" if use_corr is plac else "none"))
        if ck not in ACACHE:
            # ONE MATRIX ON DISK AT A TIME. A different matrix is needed now, so the cached one is
            # finished with -- callers order arms so that arms sharing a matrix are adjacent.
            if ACACHE:
                drop_cache()
            import shutil
            need = (len(frame_h) + len(frame_t)) * ntree * 4
            free = shutil.disk_usage("D:/").free
            if free < need * 1.05 + 1e9:
                raise SystemExit("pm25_adaptation: D: has %.1f GB free; the %s tree matrix needs "
                                 "%.1f GB. Stopping BEFORE writing it rather than dying mid-write."
                                 % (free / 1e9, name, need / 1e9))
            t0 = time.time()
            Vm = np.vstack([frame_h[feat].fillna(0).values.astype(np.float32),
                            frame_t[feat].fillna(0).values.astype(np.float32)])
            vm_s = time.time() - t0                        # (g) row-matrix build seconds
            VM_SEC[0] += vm_s
            p_before, w_before = PRED_SEC[0], WRITE_SEC[0]
            A, path = columns(Vm, name, use_corr)
            del Vm
            ACACHE[ck] = (A, path)
            COLS_SEC[0] += time.time() - t0
            log("    columns %-16s %s x %d written in %.1f min (%.2f s) [%d tree workers%s] "
                "(Vm build %.2f s | predict %.2f s | memmap copy+flush %.2f s)"
                % (name, format(A.shape[0], ","), A.shape[1], (time.time() - t0) / 60.0,
                   time.time() - t0, TREE_WORKERS, ", finite scan once per block" if FINITE_ONCE
                   else "", vm_s, PRED_SEC[0] - p_before, WRITE_SEC[0] - w_before))
        A, path = ACACHE[ck]
        t_r = time.time()
        if sweep is not None:
            P, P0, nfit, nfall = route_sweep(frame_h, frame_t, A, ntree, f(yh_), float(f(gmean)),
                                             cut, sweep, ccol=ccol, with_off=(use_corr is None))
            _router_log(name, t_r, nfit)
            return finv(P), (None if P0 is None else finv(P0)), nfit, nfall
        p, nfit, nfall = route_percell(frame_h, frame_t, A, ntree, f(yh_), float(f(gmean)),
                                       cut, pen, ccol=ccol)
        _router_log(name, t_r, nfit)
        return finv(p), nfit, nfall

    def _router_log(name, t_r, nfit):
        # SPEEDPROOF: router wall clock per arm, so speedup 3 can be read from run.log directly.
        dt = time.time() - t_r
        ROUTER_SEC[0] += dt
        log("    router  %-16s %d cells in %.2f s  [%d router workers, %s]"
            % (name, nfit, dt, ROUTER_WORKERS,
               "BLAS 1" if ROUTER_PIN else "UNPINNED: shipped BLAS state"))

    # ---------------------------------------------------------------- ARM DECISION, inner window
    # <=2016 fits, 2017-2019 scores. Both lie INSIDE the calibration history, so no test-window
    # number exists at the moment the layer chooses.
    ih = hist[hist.year <= INNER].reset_index(drop=True)
    it = hist[hist.year > INNER].reset_index(drop=True)
    assert int(ih.year.max()) <= INNER < int(it.year.min()), "inner window is not ordered"
    assert int(it.year.max()) <= TRAIN_END, "the inner score window crossed into the test years"
    # SCIENCE CHANGE A6: the inner pass gets a climatology built from ITS OWN FIT ROWS (<=2016).
    # The history-wide `clim` both frames inherited from `hist` averaged in 2017-2019 -- the very
    # rows scored here -- as an unpenalised input and as the guess-normal baseline.
    add_clim(ih, [ih, it])
    ihy, ity = ih.y.values.astype(np.float64), it.y.values.astype(np.float64)
    log("  INNER DECISION WINDOW: fit %s rows (%d-%d) -> score %s rows (%d-%d); "
        "climatology from the fit rows only"
        % (format(len(ih), ","), int(ih.year.min()), INNER, format(len(it), ","), INNER + 1,
           TRAIN_END))

    # THE LAYER CHOOSES ARM **AND** PENALTY, JOINTLY, ON ROWS IT IS ALLOWED TO SEE.
    # Choosing the arm first and then the penalty would fix the arm at the inherited penalty and
    # then tune around it -- which is not the same surface, and would hide an arm that only wins
    # at a different shrinkage. The candidate set is every (arm, penalty) pair.
    log("  PENALTY GRID: %d levels x %d ratios = %d points; the shipped (1.0, 0.5) is point %s; "
        "plus trees-off per link" % (len(LEVELS), len(RATIOS), len(GRID), SHIPPED_CELL))
    inner, cand = {}, {}

    def rank(name, P):
        """Score every grid column of one arm on the inner window; keep the arm's best."""
        best_k, best_s = None, None
        for k, (mlt, rho) in enumerate(GRID):
            s = score(ity, P[:, k], it.clim.values, groups=it.reg.values)
            cand[(name, mlt, rho)] = s
            if best_s is None or s["mae"] < best_s["mae"]:
                best_k, best_s = k, s
        inner[name] = dict(best_s, pen=GRID[best_k])
        shipped = cand[(name, 1.0, 0.5)] if SHIPPED_CELL is not None else None
        log("    inner %-14s best MAE %.4f at (mlt %.2g, rho %.3g) | shipped-penalty MAE %.4f"
            % (name, best_s["mae"], GRID[best_k][0], GRID[best_k][1],
               shipped["mae"] if shipped else float("nan")))

    def rank_single(name, p, normal):
        """A penalty-free candidate (trees-off). `normal` is what it should equal -- logged, not
        assumed, so the 'trees-off IS the climatology' statement is checked on every run."""
        s = score(ity, p, it.clim.values, groups=it.reg.values)
        cand[(name, None, None)] = s
        inner[name] = dict(s, pen=None)
        log("    inner %-14s MAE %.4f (penalty-free; max |pred - %s| = %.2e)"
            % (name, s["mae"], {"treesoff": "clim", "log_treesoff": "expm1(lclim)",
                                "logc_treesoff": "exp(lcclim)-c"}[name],
               float(np.nanmax(np.abs(p - normal)))))

    SURF = {}                     # inner row-level surfaces, saved below -- predictions, not scores
    # SPEEDPROOF (g): the same surfaces in FLOAT64, copy-only, saved to F64_NAME. The shipped SURF is
    # float32 by design, so inner_preds.npz cannot show a difference near 1e-13; this file can.
    SURF64 = {}
    # Arms sharing a tree matrix stay ADJACENT (all no-corrector links, then all corrector links),
    # so run_arm's one-matrix rule builds each matrix once. With the default LINK_SET this is
    # exactly Part 556's order: base, log, corrector, log_corrector.
    INNER_ARMS = ([(ARM[L][0], L, None) for L in LINK_SET]
                  + [(ARM[L][1], L, corr) for L in LINK_SET])
    for name, link, c in INNER_ARMS:
        P, P0, _, _ = run_arm("in_" + name, link, c, ih, it, ihy, ity, INNER, sweep=GRID)
        rank(name, P)
        SURF[name] = P.astype(np.float32)
        SURF64[name] = np.array(P, np.float64)                      # SPEEDPROOF (g)
        if P0 is not None:
            off = ARM[link][3]
            rank_single(off, P0, normal_values(link, it))
            SURF[off] = P0.astype(np.float32)
            SURF64[off] = np.array(P0, np.float64)                  # SPEEDPROOF (g)

        # CONTRACT CHECK. The (1.0, 0.5) point of the grid IS (ALPHA, A_CTX), so it must reproduce
        # the un-swept router exactly. If it does not, the sweep is not a superset of the shipped
        # path and nothing below can be compared with any earlier number.
        # Run right after BASE, while base's matrix is still cached -- the same computation as
        # before, moved up only so that matrix can be deleted before the corrector arms build theirs.
        if name == "base" and SHIPPED_CELL is not None:
            chk, _, _ = run_arm("chk", "identity", None, ih, it, ihy, ity, INNER, pen=(1.0, 0.5))
            SURF64["chk"] = np.array(chk, np.float64)               # SPEEDPROOF (g)
            ref = cand[("base", 1.0, 0.5)]["mae"]
            got = score(ity, chk, it.clim.values)["mae"]
            assert abs(got - ref) < 1e-9, (
                "the grid's (1.0, 0.5) point does not reproduce the un-swept route: %.10f vs %.10f. "
                "The sweep is then not a superset of the shipped path." % (got, ref))
            log("    contract: grid point (1.0, 0.5) reproduces the un-swept route (MAE %.6f)" % got)

    drop_cache()          # the inner frame pair is finished with
    phase_done("inner decision")

    # EVERY CANDIDATE THE LAYER RANKED, persisted -- the decision must be auditable after the fact.
    pd.DataFrame([dict(arm=a, mlt=m, rho=r,
                       a_tree=None if m is None else ALPHA * m,
                       a_ctx=None if m is None else ALPHA * m * r,
                       **{k: s.get(k) for k in ("n", "mae", "r2", "pat", "hit", "hit0", "mae0")})
                  for (a, m, r), s in cand.items()]).to_csv(
        os.path.join(RUN_DIR, "inner_candidates.csv"), index=False)
    # ...and the ROW-LEVEL inner surfaces, so the decision can be re-scored on another criterion
    # (e.g. corr2, as ruling G2 did for defo) without re-running the whole inner pass.
    np.savez_compressed(os.path.join(RUN_DIR, "inner_preds.npz"),
                        grid=np.array(GRID), y=ity, clim=it.clim.values, lclim=it.lclim.values,
                        reg=it.reg.values.astype(str), cell_id=it.cell_id.values.astype(str),
                        year=it.year.values, month=it.month.values,
                        **({"lcclim": it.lcclim.values, "c_log": np.array([C_LOG])}
                           if "logc" in LINK_SET else {}),
                        **{"P_" + k: v for k, v in SURF.items()})
    del SURF
    # SPEEDPROOF (g): copy-only float64 inner surfaces (+ the contract check's single-penalty route
    # "chk"), row-aligned with inner_preds.npz. Not read by anything in this script.
    np.savez_compressed(os.path.join(RUN_DIR, F64_NAME), code_sha256=np.array([CODE_SHA256]),
                        **{"P_" + k: v for k, v in SURF64.items()})
    del SURF64

    # REGRESSION GATE (U2). Every (arm, penalty) this run shares with the earlier run must score the
    # same inner MAE. It runs BEFORE the test pass, so a mismatch costs the inner pass, not the day.
    if EXPECT_FROM:
        ref_c = pd.read_csv(EXPECT_FROM)
        diffs = []
        for (a, m, r), s in cand.items():
            q = ref_c[(ref_c.arm == a) & (ref_c.mlt.isna() if m is None else
                                          np.isclose(ref_c.mlt, m) & np.isclose(ref_c.rho, r))]
            if len(q) == 1:
                diffs.append((a, m, r, float(q.mae.iloc[0]), s["mae"]))
        worst = max((abs(d[4] - d[3]) for d in diffs), default=float("nan"))
        for a, m, r, old, new in diffs:
            log("    regression %-16s (mlt %s, rho %s): earlier MAE %.6f, now %.6f, diff %.2e"
                % (a, m, r, old, new, new - old))
        VERDICT["regression_gate"] = dict(source=EXPECT_FROM, n_shared=len(diffs), worst=worst,
                                          tol=EXPECT_TOL)
        assert diffs, "regression gate: no (arm, penalty) shared with %s" % EXPECT_FROM
        assert worst <= EXPECT_TOL, (
            "regression gate FAILED: an arm shared with %s moved by %.3g ug/m3 (> %.0e). The bank, "
            "frames or router are not the earlier run's; stopping before the test pass."
            % (EXPECT_FROM, worst, EXPECT_TOL))
        log("  regression gate PASSED: %d shared (arm, penalty) points reproduce %s to %.2e ug/m3"
            % (len(diffs), EXPECT_FROM, worst))

    TREES_OFF = tuple(ARM[L][3] for L in LINK_SET)
    # N2 GUARD (owner ruling 2026-09-24). A tree arm may be adopted ONLY IF IT BEATS ITS OWN
    # LINK-MATCHED NORMAL on the inner window: identity arms the arithmetic normal (treesoff), log
    # arms the geometric normal (log_treesoff). MAE rewards the median, and on this skewed target the
    # geometric normal ALONE beats the arithmetic one -- so without the guard a log arm could be
    # adopted for being median-like rather than for routing skill. This removes that explanation by
    # construction. If no arm passes, the layer DECLINES TO PREDICT and adopts DECLINE_TO.
    NORMAL_OF = {}
    for L in LINK_SET:
        NORMAL_OF[ARM[L][0]] = ARM[L][3]
        NORMAL_OF[ARM[L][1]] = ARM[L][3]
    for k, nk in NORMAL_OF.items():
        inner[k]["own_normal"] = nk
        inner[k]["saved_vs_own_normal"] = inner[nk]["mae"] - inner[k]["mae"]
        inner[k]["beats_own_normal"] = bool(inner[k]["mae"] < inner[nk]["mae"])
        log("    guard %-14s MAE %.4f vs its %-12s %.4f -> %s"
            % (k, inner[k]["mae"], nk, inner[nk]["mae"],
               "ELIGIBLE" if inner[k]["beats_own_normal"] else "not eligible"))
    eligible = [k for k in NORMAL_OF if inner[k]["beats_own_normal"]]
    if ADOPT_RANK == "saved":
        rank_key = lambda k: -inner[k]["saved_vs_own_normal"]      # noqa: E731
    else:
        rank_key = lambda k: inner[k]["mae"]                       # noqa: E731
    pick = min(eligible, key=rank_key) if eligible else DECLINE_TO
    PEN = inner[pick]["pen"]                      # None when the layer declines (a normal)
    # THE TREE ARMS' PENALTY: the adopted arm's when a tree arm is adopted; otherwise the best
    # TREE-ROUTED candidate's -- never a penalty nothing chose, which would make every contrast
    # below an artefact.
    tree_pick = pick if pick in NORMAL_OF else min(NORMAL_OF, key=lambda k: inner[k]["mae"])
    PEN_TREE = inner[tree_pick]["pen"]
    log("  => LAYER ADOPTS: %s %s   [%d of %d tree arms beat their own normal; ranked by %s; "
        "%d candidates scored, base included]"
        % (pick, "at penalty (mlt %.2g, rho %.3g)" % PEN if PEN else "(penalty-free)",
           len(eligible), len(NORMAL_OF), "MAE" if ADOPT_RANK != "saved" else
           "MAE saved vs own normal", len(cand)))
    if pick == "base":
        log("     the layer DECLINED THE TOOLS -- no tool beat the untooled route on rows it may see")
    if pick in TREES_OFF:
        log("     the layer DECLINED TO PREDICT -- no tree arm beat its own link-matched normal on "
            "rows it may see; adopted the %s. Tree arms below are scored at the best tree-routed "
            "candidate's penalty: %s at (mlt %.2g, rho %.3g)"
            % ("arithmetic normal (guess-normal)" if pick == "treesoff" else "geometric normal",
               tree_pick, PEN_TREE[0], PEN_TREE[1]))
    if PEN_TREE != (1.0, 0.5):
        log("     tree arms MOVED OFF the inherited penalty: fire's (ALPHA %.3g, A_CTX %.3g) -> "
            "(%.3g, %.3g)" % (ALPHA, A_CTX, ALPHA * PEN_TREE[0], ALPHA * PEN_TREE[0] * PEN_TREE[1]))
    else:
        log("     tree arms KEPT the inherited penalty -- fire's constants survive the sweep here")
    # A ONE-POINT GRID IS A FROZEN PENALTY, NOT AN EDGE: the owner froze Part 556's (10, 0.0625)
    # (ruling 2026-09-25). Calling it TOP and BOTTOM at once would be noise; say what it is.
    FROZEN = len(LEVELS) == 1 and len(RATIOS) == 1
    if FROZEN:
        edge = {"level": "FROZEN", "ratio": "FROZEN"}
        log("  penalty FROZEN by the owner at (mlt %.3g, rho %.4g) -- a one-point grid; Part 556 "
            "picked it at the ratio axis's bottom edge, and that caveat carries over"
            % (LEVELS[0], RATIOS[0]))
    else:
        edge = {"level": ("TOP" if PEN_TREE[0] == max(LEVELS) else
                          "BOTTOM" if PEN_TREE[0] == min(LEVELS) else None),
                "ratio": ("TOP" if PEN_TREE[1] == max(RATIOS) else
                          "BOTTOM" if PEN_TREE[1] == min(RATIOS) else None)}
    if not FROZEN and (edge["level"] or edge["ratio"]):
        log("  !! EDGE PICK (tree arms): level %s, ratio %s -- a pick at a grid edge is the grid "
            "running out, not a selection" % (edge["level"], edge["ratio"]))
    VERDICT.update(status="inner decision done", adopted=pick,
                   penalty=None if PEN is None else list(PEN),
                   tree_pick=tree_pick, penalty_tree_arms=list(PEN_TREE),
                   a_tree=ALPHA * PEN_TREE[0], a_ctx=ALPHA * PEN_TREE[0] * PEN_TREE[1],
                   edge=edge, n_candidates=len(cand),
                   eligible=eligible, decline_to=DECLINE_TO, adopt_rank=ADOPT_RANK,
                   inner_best={k: dict(mae=v["mae"],
                                       pen=None if v["pen"] is None else list(v["pen"]),
                                       own_normal=v.get("own_normal"),
                                       saved_vs_own_normal=v.get("saved_vs_own_normal"),
                                       beats_own_normal=v.get("beats_own_normal"))
                               for k, v in inner.items()})
    # A PARTIAL verdict now, so a crash in the (long) test pass cannot lose the decision.
    with open(os.path.join(RUN_DIR, "verdict.json"), "w", encoding="utf-8") as fh:
        json.dump(_jsonable(VERDICT), fh, indent=1)

    # ---------------------------------------------------------------- TEST
    # EVERY TREE arm is scored at ONE penalty (PEN_TREE -- the adopted one, or the best tree-routed
    # one when trees-off is adopted), so the table compares arms at one shrinkage rather than each
    # at its own -- otherwise "corrector beats base" could just mean "the corrector got a better
    # lambda". The ONE exception is base_inherited (ruling A7): fire's (ALPHA, A_CTX), i.e. Type 1
    # with no adaptation at all. The trees-off arms are penalty-free (they ARE the two normals).
    # Arms sharing a tree matrix are adjacent, so run_arm's one-matrix rule never rebuilds one.
    # Built from LINK_SET in matrix order; with the default set it is exactly Part 556's list.
    TEST_ARMS = ([("base_inherited", "identity", None, (1.0, 0.5), False)]
                 + [(ARM[L][0], L, None, PEN_TREE, False) for L in LINK_SET]
                 + [(ARM[L][3], L, None, (1.0, 0.5), True) for L in LINK_SET]   # = the normals
                 + [(ARM[L][1], L, corr, PEN_TREE, False) for L in LINK_SET]
                 + [(ARM[L][2], L, plac, PEN_TREE, False) for L in LINK_SET])
    res, preds = {}, {}
    for name, link, c, pen, off in TEST_ARMS:
        p, nfit, nfall = run_arm("te_" + name, link, c, hist, test, yh, y, TRAIN_END,
                                 pen=pen, trees_off=off)
        res[name] = score(y, p, test.clim.values, groups=test.reg.values)
        preds[name] = p
        log("  TEST %-15s MAE %.4f  anomR2 %+.4f  patR2 %+.4f  hit %.3f  (%d cells, %d fell back)"
            % (name, res[name]["mae"], res[name]["r2"], res[name]["pat"], res[name]["hit"],
               nfit, nfall))
    drop_cache()
    phase_done("test pass")
    ARMS_OUT = [a[0] for a in TEST_ARMS]

    # SAVE ROW-LEVEL PREDICTIONS, never scores alone -- with the STRING cell_id (the integer `cell`
    # is a factorize code that means nothing outside this run) and the adopted arm.
    out = test[["reg", "cell_id", "cell", "year", "month", "y", "clim", "lclim"]
               + (["lcclim"] if "logc" in LINK_SET else [])].copy()
    for k, v in preds.items():
        out["p_" + k] = v
    out["adopted"] = pick
    out.to_parquet(os.path.join(RUN_DIR, "predictions.parquet"), index=False, compression="zstd")

    # ---------------------------------------------------------------- per region, per year
    def table(frame, key, groups_col):
        rows = []
        for kv, g in frame.groupby(key):
            d = {key: kv, "n": len(g)}
            for k in ARMS_OUT:
                s = score(g.y.values, g["p_" + k].values, g.clim.values,
                          groups=None if groups_col is None else g[groups_col].values)
                for m in ("mae", "r2", "pat", "hit", "dirhit"):
                    d["%s_%s" % (k, m)] = s.get(m)
            s0 = score(g.y.values, g.clim.values, g.clim.values)
            d["mae0"], d["hit0"] = s0.get("mae0"), s0.get("hit0")
            rows.append(d)
        return pd.DataFrame(rows)

    R = table(out, "reg", None)                      # one region: its own mean IS the group mean
    Yr = table(out, "year", "reg")                   # one year: demean per region within it
    R.to_csv(os.path.join(RUN_DIR, "per_region.csv"), index=False)
    Yr.to_csv(os.path.join(RUN_DIR, "per_year.csv"), index=False)

    log("")
    log("=" * 92)
    log("TYPE 1 (untooled base) vs TYPE 2 (the layer's pick: %s at penalty %s; tree arms at %s)"
        % (pick, PEN, PEN_TREE))
    log("=" * 92)
    log("  %-16s %10s %10s %10s %10s %10s" % ("arm", "MAE", "anomR2", "patR2", "hit+-2", "dirhit"))
    NOTE = {"base_inherited": "  <- TYPE 1, no adaptation", "treesoff": "  (= guess-normal)",
            "log_treesoff": "  (= geometric normal)", "logc_treesoff": "  (= log(y+c) normal)"}
    for k in ARMS_OUT:
        star = NOTE.get(k, "") + ("  <== ADOPTED" if k == pick else "")
        log("  %-16s %10.4f %+10.4f %+10.4f %10.3f %10.3f%s"
            % (k, res[k]["mae"], res[k]["r2"], res[k]["pat"], res[k]["hit"], res[k]["dirhit"],
               star))
    log("  %-16s %10.4f %10s %10s %10.3f" % ("guess-normal", res["base"]["mae0"], "0.0000",
                                             "0.0000", res["base"]["hit0"]))
    log("  (a log arm's MAE should also be read against log_treesoff, the geometric normal: MAE "
        "rewards the median, and on this skewed target that normal alone sits nearer it)")
    log("")

    # Q3 (owner ruling 2026-09-24): RAW MAE ADOPTS -- it is what deploys -- but the adopted arm's
    # gain is ALWAYS DECOMPOSED, so a reader sees how much came from which normal the arm sits on
    # and how much from routing:
    #     normal effect  = arithmetic-normal MAE - geometric-normal MAE
    #     routing effect = the arm's OWN link-matched normal MAE - the arm's MAE
    # A consistently positive normal effect is itself a finding: guess-normal (the arithmetic
    # climatology) would then be the wrong naive baseline for a right-skewed target.
    # U2: the normal effect is taken against the ADOPTED arm's own normal (for an identity pick it is
    # 0 by definition); log1p's is still printed when present, so Part 556's line stays comparable.
    def decompose(mae_of):
        own = NORMAL_OF.get(pick)
        d = {}
        if "log_treesoff" in mae_of:
            d["normal_effect"] = mae_of["treesoff"] - mae_of["log_treesoff"]
        if "logc_treesoff" in mae_of:
            d["normal_effect_logc"] = mae_of["treesoff"] - mae_of["logc_treesoff"]
        if own is not None:
            d.update(own_normal=own, own_normal_effect=mae_of["treesoff"] - mae_of[own],
                     routing_effect=mae_of[own] - mae_of[pick])
        return d
    DEC = {"inner": decompose({k: v["mae"] for k, v in inner.items()}),
           "test": decompose({k: res[k]["mae"] for k in ARMS_OUT})}
    for w in ("inner", "test"):
        d = DEC[w]
        parts = []
        if "normal_effect" in d:
            parts.append("normal effect %+.4f ug/m3 (arithmetic - log1p normal)" % d["normal_effect"])
        if "normal_effect_logc" in d:
            parts.append("logc normal effect %+.4f (arithmetic - log(y+c) normal)"
                         % d["normal_effect_logc"])
        if "routing_effect" in d:
            parts.append("routing effect %+.4f (%s - %s)" % (d["routing_effect"], d["own_normal"],
                                                            pick))
        log("  DECOMPOSITION (%s window): %s" % (w, " | ".join(parts)))
    VERDICT["decomposition"] = DEC
    log("")

    # REGION-LEVEL CONTRASTS: leave-one-region-out jackknife, the shipped layer's own interval
    # (adaptation.jack) -- no bootstrap, no seeds (ruling A10). Each tuple is (label, REFERENCE a,
    # ARM b); dv = MAE(a) - MAE(b), so POSITIVE = b, the arm printed first, has the LOWER MAE.
    contrasts = ([("penalty sweep", "base_inherited", "base"),
                  ("tool worth", "base", pick)]
                 + [("%s vs its placebo" % ARM[L][1], ARM[L][2], ARM[L][1]) for L in LINK_SET]
                 # U2: does the unit-free log differ from log1p on this target at all?
                 + ([("log(y+c) vs log1p", "log_corrector", "logc_corrector")]
                    if {"log", "logc"} <= set(LINK_SET) else []))
    VERDICT["contrasts"] = {}
    for label, a, b in contrasts:
        if a == b:
            continue
        dv = (R["%s_mae" % a] - R["%s_mae" % b]).dropna().to_numpy()   # MAE saved by b over a
        m_, lo, hi, se = AD.jack(dv)
        # FOUR outcomes, as the shipped layer's verdict() insists -- never merge "equivalent" or
        # "identical" into CANNOT TELL. IDENTICAL: e.g. the penalty sweep when the layer kept fire's
        # penalty, so base == base_inherited exactly. The equivalence band is in ug/m3 and is the
        # owner's to set (EQ_UGM3); fire's AD.DELTA is in fire's units and is NOT reused here.
        if len(dv) and np.allclose(dv, 0.0, atol=1e-12):
            tag = "IDENTICAL"
        elif not np.isfinite(lo):
            tag = "CANNOT TELL"
        elif lo > 0:
            tag = "HELPS"
        elif hi < 0:
            tag = "HURTS"
        elif EQ_UGM3 is not None and -EQ_UGM3 <= lo and hi <= EQ_UGM3:
            tag = "DOES NOT HELP (equivalent)"
        else:
            tag = "CANNOT TELL"
        log("  %-30s %-15s over %-15s MAE saved %+.4f  jackknife 95%% [%+.4f, %+.4f]  %s  "
            "(pooled %+.4f; %d/%d regions)"
            % (label, b, a, m_, lo, hi, tag, res[a]["mae"] - res[b]["mae"], int((dv > 0).sum()),
               len(dv)))
        VERDICT["contrasts"][label] = dict(arm=b, ref=a, mean=m_, lo=lo, hi=hi, se=se, verdict=tag)
    # N3: DERIVE the equivalence band from this run's own noise scale -- the median jackknife SE of
    # the (non-identical) arm contrasts -- and record it, to be fixed as EQ_UGM3 for later runs.
    ses = [c["se"] for c in VERDICT["contrasts"].values()
           if c["verdict"] != "IDENTICAL" and c["se"] is not None and np.isfinite(c["se"])]
    VERDICT["eq_band_derived"] = float(np.median(ses)) if ses else None
    log("  N3: equivalence band derived from this run (median jackknife SE of the contrasts): %s"
        " | band IN USE for the verdicts above: %s"
        % ("%.4f ug/m3" % VERDICT["eq_band_derived"] if ses else
           "not derivable (fewer than 3 regions)",
           "none" if EQ_UGM3 is None else "%.4f ug/m3 (fixed from Part 556)" % EQ_UGM3))
    log("")
    log("  per region: %d regions | base beats guess-normal in %d | %s beats it in %d"
        % (len(R), int((R.base_mae < R.mae0).sum()), pick,
           int((R["%s_mae" % pick] < R.mae0).sum())))
    # SPEEDPROOF: the plumbing settings of this copy, kept OUT of `config` so config stays comparable
    # with the shipped script's verdict.json.
    from threadpoolctl import threadpool_info
    VERDICT["speedproof"] = dict(code_sha256=CODE_SHA256, code_file=os.path.abspath(__file__),
                                 tree_workers=TREE_WORKERS, router_workers=ROUTER_WORKERS,
                                 router_blas_threads=1 if ROUTER_PIN else "unpinned",
                                 tmp_dir=TMP_DIR, finite_once=FINITE_ONCE,
                                 columns_sec=round(COLS_SEC[0], 2),
                                 columns_vm_sec=round(VM_SEC[0], 2),
                                 columns_predict_sec=round(PRED_SEC[0], 2),
                                 columns_memmap_write_sec=round(WRITE_SEC[0], 2),
                                 router_sec=round(ROUTER_SEC[0], 2),
                                 blas_outside_router=[(d.get("prefix"), d.get("num_threads"))
                                                      for d in threadpool_info()
                                                      if d.get("user_api") == "blas"])
    log("  SPEEDPROOF: tree answers %.1f s on %d tree workers (finite scan once per block: %s; "
        "Vm build %.1f s, predict %.1f s, memmap copy+flush %.1f s) | "
        "routers %.1f s on %d router workers (%s) | BLAS outside the router: %s | code sha256 %s"
        % (COLS_SEC[0], TREE_WORKERS, FINITE_ONCE, VM_SEC[0], PRED_SEC[0], WRITE_SEC[0],
           ROUTER_SEC[0], ROUTER_WORKERS, "BLAS 1" if ROUTER_PIN else "UNPINNED",
           VERDICT["speedproof"]["blas_outside_router"], CODE_SHA256))
    VERDICT.update(test={k: res[k] for k in ARMS_OUT}, timings=TIMINGS,
                   config=dict(SMOKE=SMOKE, CELLS=CELLS, DCELLS=DCELLS, NPD=NPD, MF=MF,
                               LEVELS=LEVELS, RATIOS=RATIOS, ALPHA=ALPHA, A_CTX=A_CTX,
                               HIT_TOL=HIT_TOL, INNER=INNER, TRAIN_END=TRAIN_END,
                               FIRST_YEAR=PA.FIRST_YEAR, USE_EDGAR=PA.USE_EDGAR,
                               DROP_CONDITIONAL=PA.DROP_CONDITIONAL, EQ_UGM3=EQ_UGM3,
                               DECLINE_TO=DECLINE_TO, ADOPT_RANK=ADOPT_RANK, NVERIFY=NVERIFY,
                               ROW_BLOCK=ROW_BLOCK, donors=donors, tests=tests,
                               LINK_SET=LINK_SET, C_LOG=C_LOG if "logc" in LINK_SET else None,
                               FROZEN_PENALTY=FROZEN, EXPECT_FROM=EXPECT_FROM,
                               RUN_DIR=RUN_DIR),
                   status="done", finished=time.strftime("%Y-%m-%d %H:%M:%S"))
    with open(os.path.join(RUN_DIR, "verdict.json"), "w", encoding="utf-8") as fh:
        json.dump(_jsonable(VERDICT), fh, indent=1)
    log("")
    log("  saved -> %s  (run.log, _adaptation.log, inner_candidates.csv, inner_preds.npz, "
        "verdict.json, predictions.parquet, per_region.csv, per_year.csv)" % RUN_DIR)
    return 0


_OUTPUTS = ("verdict.json", "predictions.parquet", "inner_candidates.csv", "inner_preds.npz",
            "per_region.csv", "per_year.csv", "run.log", "_adaptation.log", "RUNNING",
            F64_NAME)                      # SPEEDPROOF (g)


def main():
    """Pre-flight checks, then the run, with cleanup GUARANTEED.

    A crash used to leave an 18-22 GB tree matrix and the pool on D:, named by a PID no later run
    would reuse -- which is exactly how D:/pm25 accumulated its orphans. Now: refuse to start while
    any such file exists; refuse to overwrite a previous run's outputs unless --force (which MOVES
    them aside, never deletes); check the disk can hold one test matrix BEFORE hours of bank
    building; and delete the matrix and the pool in a finally-block whatever happens."""
    import glob
    import shutil
    import traceback
    # SPEEDPROOF (d): check the shipped temp folder AND this copy's own, so neither kind of orphan
    # (nor a live shipped run competing for the disk and the cores) goes unnoticed.
    stale = sorted(glob.glob("D:/pm25/A_*.f32") + glob.glob("D:/pm25/pool_*.f32")
                   + glob.glob(TMP_DIR + "/A_*.f32") + glob.glob(TMP_DIR + "/pool_*.f32"))
    if stale:
        raise SystemExit(
            "pm25_adaptation: refusing to start -- %d tree-matrix/pool file(s) from earlier runs are "
            "on D:/pm25 (%.1f GB). They are temp files of runs that are no longer alive; delete them "
            "first:\n  %s" % (len(stale), sum(os.path.getsize(f) for f in stale) / 1e9,
                              "\n  ".join(stale)))
    os.makedirs(RUN_DIR, exist_ok=True)
    olds = [f for f in _OUTPUTS if os.path.exists(os.path.join(RUN_DIR, f))]
    if olds and not FORCE:
        raise SystemExit("pm25_adaptation: %s already holds a run (%s). Re-run with --force to move "
                         "it to %s/prev_<timestamp>/ first." % (RUN_DIR, ", ".join(olds), RUN_DIR))
    if olds:
        prev = os.path.join(RUN_DIR, "prev_" + time.strftime("%Y%m%d_%H%M%S"))
        os.makedirs(prev)
        for f in olds:
            shutil.move(os.path.join(RUN_DIR, f), os.path.join(prev, f))
    # the disk budget: ONE test-pass matrix = test cells x (history + test months) x tree columns
    n_d = min(len(SPLIT.DONORS), 8) if SMOKE else len(SPLIT.DONORS)
    n_t = min(len(SPLIT.TEST), 3) if SMOKE else len(SPLIT.TEST)
    months = (TRAIN_END - PA.FIRST_YEAR + 1 + 2023 - TRAIN_END) * 12
    need = n_t * CELLS * months * n_d * NPD * 4
    free = shutil.disk_usage("D:/").free
    if free < need * 1.05 + 3e9:
        raise SystemExit("pm25_adaptation: D: has %.1f GB free; one test-pass tree matrix needs "
                         "%.1f GB plus ~3 GB headroom. Free space before starting."
                         % (free / 1e9, need / 1e9))
    # EVERY line of the run goes to run.log, including the pool and memory-wait lines printed by
    # pm25_architecture / fire_architecture (their log() is looked up at call time).
    PA.log = log
    FA.log = log
    with open(os.path.join(RUN_DIR, "RUNNING"), "w", encoding="utf-8") as fh:
        fh.write("pid %d | started %s | argv %s\n"
                 % (os.getpid(), time.strftime("%Y-%m-%d %H:%M:%S"), " ".join(_ARGV[1:])))
    log("  pre-flight: no stale matrices; D: %.1f GB free, one test matrix needs %.1f GB | "
        "SPEEDPROOF code sha256 %s" % (free / 1e9, need / 1e9, CODE_SHA256))
    try:
        rc = _run()
        os.remove(os.path.join(RUN_DIR, "RUNNING"))
        return rc
    except BaseException:
        log("!! RUN FAILED\n" + traceback.format_exc())
        raise
    finally:
        drop_cache()
        PA.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
