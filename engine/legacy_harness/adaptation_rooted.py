"""THE ADAPTATION SCRIPT -- Tier 1 and Tier 2 for every problem, one engine, three adapters.

    py -3.9 -u adaptation.py --problem=defo   --smoke=1     <- ALWAYS SMOKE FIRST
    py -3.9 -u adaptation.py --problem=defo
    py -3.9 -u adaptation.py --problem=coral
    py -3.9 -u adaptation.py --problem=coral  --split=dbl
    py -3.9 -u adaptation.py --problem=fire

WHAT IT REPORTS, PER PROBLEM
    TYPE 1  BASE        bank + router, no tools.
    TYPE 2  ADAPTATION  picks among {base, corrector, evt, both} automatically. THIS SCRIPT.
    TYPE 3  MANUAL      NOT computed -- QUOTED. Its design is the thing that needs a person, so
                        computing it here would credit the automation with human work.

ADOPTION: ARGMIN MAE over the candidate set, no margin. BASE IS A CANDIDATE, so when base wins the
layer DECLINES -- that is how "no tool" happens. The choice is GLOBAL per problem. Per-region choice
was built exactly as specified, measured, and lost 4:1 (+0.0039 against always-on's +0.0156) because
each region decided on margins of 0.0002-0.0013. Fourth reproduction of IMPROVEMENT_ROADMAP.md:150.

WHOSE ROWS THE CHOICE IS MADE ON -- READ THIS BEFORE QUOTING ANY ADOPTION.
NO PROBLEM'S TOOL CHOICE HAS EVER BEEN MADE FROM DONOR REGIONS ALONE. Three different situations:
    defo   the TEST REGION's OWN rows: 2003-2016 fit -> 2017-2019 score. No test-window row, but
           not donor-blind either. Legitimate under the two-tier rule (base models never train on a
           test region; the ROUTER may calibrate on its pre-test rows) -- a weaker claim, not a leak.
           Weaker still: Part 507 found an inner-window selector pinning to a grid ENDPOINT 15/17.
    fire   the TEST CELLS' OWN history: <=2016 fit -> 2017-2018 score. Same shape, same caveat.
    coral  NOTHING. No pre-test window exists (test rows end 2019, median 1 row/site). Until
           2026-09-14 run_coral built the surface from the TEST TARGETS and the layer adopted the
           test-best arm on all three splits while this file printed "test window never touched".
           It now DECLINES TO ADOPT on coral. See the comment at run_coral's `dec = None`.
--decide is NOT IMPLEMENTED and now raises. No adapter reads it; KFOLD was dead. The donor-fold
surface exists only in decide_arms.py --build=1, defo only, and HAS NEVER BEEN RUN.

VERDICTS ARE REPORTED, NEVER USED TO ADOPT. HELPS / HURTS / DOES NOT HELP (equivalent) / CANNOT
TELL, each with a minimum detectable effect. They decide what the PAPER MAY CLAIM. Both can hold at
once: coral's corrector is worth adopting on MAE AND is statistically equivalent to a placebo.

THE PLACEBO IS A DIAGNOSTIC, NOT A GATE -- same rows, same trees, same eta, residual cyclically
shifted by n//2, so it has nothing to learn by construction. It cannot block adoption. It separates
    corrector - base      what the tool is WORTH       -> adoption
    corrector - placebo   whether it CORRECTS          -> what you may call it
MEASURED: coral +0.0153 vs +0.0020 (worth having, NOT a corrector -- 87% reproduced by scrambled
residuals). Defo +0.0126 vs +0.0152 (worth having AND correcting).

--------------------------------------------------------------------------------------------------
WHY THE ADAPTERS ARE HAND-WRITTEN, AND WHAT IS AUTOMATIC

AUTOMATIC: the tool decision on defo and fire -- nobody sees a TEST-WINDOW number before it is
made. NOT automatic on coral: there is no surface, so the layer declines and any coral arm quoted is
a human choice. "Demonstrated on three problems" is false; it is two.
CONFIGURED PER PROBLEM: the data contract -- calibration unit, link, hurdle, split, donor window.
These are FORCED by how each dataset is shaped and a reader can check the arithmetic, but this
script does not derive them; they are encoded from measured row counts:

    rows per calibration unit   NDVI 216 | FIRE 204 | DEFO 17 | CORAL 1  (median, MEASURED)

  DEFO   ANNUAL 2003-2023 | donors <=2019 | tests 2020-2023 | 17 rows/cell
         -> REGION-POOLED. Per-cell is UNCONSTRUCTABLE: a 30-row guard against a 17-row maximum.
         Corrector uses defo's explicit half-split (replace=False), so the base is halved --
         Part 506 item 7 measured that at +0.0001, CI[-0.0013,+0.0015], i.e. free.
  FIRE   MONTHLY 2002-2022 | tests split at TRAIN_END=2018 | 204 rows/cell
         -> PER-CELL. Bank draws replace=True, so out-of-bag rows are FREE.
         DONOR WINDOW CLOSED AT 2018 (user decision). Shipped fire draws donors across 2002-2022
         with NO year restriction, so donor rows from inside the 2019-2022 test window enter
         calibration -- the DONOR_MAX_YEAR shape flagged for NDVI. Closing it LOWERS Type 1 and
         Type 2 together; contrasts should survive, and fire's LEVELS become comparable with defo's
         for the first time.
  CORAL  SPATIAL, and not a path-and-years swap. MEASURED: median 1 row per site, 74.3% of test
         sites have ONE row EVER. There is no per-cell history at any threshold, which is why coral
         routes over the nearest k=50 NEIGHBOURS -- that pool IS the substitute for a history that
         does not exist. Its data also stops: test rows end 2019, only 34 donor rows lie beyond.
         THREE CALIBRATION ARMS on the doubly-blocked split (--calib), because the pool mask is
         the whole coral leak question and the three answers are different claims:
            full     donors + same-eco, every row strictly EARLIER than the target. Causal, but
                     test-era rows enter with their TRUE labels.
            strict   nothing after CUT enters the pool at all. No scored row ever calibrates
                     another, at the cost of the test era's own spatial information.
            rollout  test-era rows enter carrying the model's OWN PREDICTION, never truth. THE ONLY
                     ARM IN WHICH NO TEST-ERA LABEL REACHES THE MODEL. Simulates deploying at CUT
                     and running forward with no further survey. Runs in DATE ORDER; errors
                     compound across the horizon, so report MAE by year, not just pooled.
         REGISTERED BEFORE RUNNING: rollout should land BETWEEN strict and full, nearer strict --
         a neighbour's predicted value is a smoothed point on the model's own manifold, so it pulls
         the local ridge toward the base solution. It cannot collapse entirely, because each
         neighbour's prediction came from ITS OWN k=50 pool and so is not in the current cell's
         column span. If rollout ~ full, the test-era rows never needed their labels and coral's
         calibration is deployable. If rollout ~ strict, that part of full's lead WAS label
         information and full must not be the headline.
         TWO SPLITS, both reported:
            main  spatial (shipped)   15,698 tr / 3,042 te / 235 severe / 74 eco
            dbl   doubly blocked      10,148 tr / 1,046 te / 128 severe / 35 eco   (cut 2010)
         NOT temporal-only: at a 2014 cut, 43.6% of test rows sit on a reef ALSO in training.
         PRE-DECLARED: `dbl` is underpowered BY CONSTRUCTION (a third the rows, CIs ~1.7x wider).
         A CANNOT TELL there is NOT a refutation of `main`; only a sign flip with a CI excluding
         zero is. Its 128 severe rows are too thin for a tail claim, so EVT will be CANNOT TELL
         there almost regardless.
         SPLITS ARE NOT COMPARABLE: severe rate runs 4.6%-23.4%, so each prints its own predict-zero.

ROW CONTRACT -- two grains, no seed in any partition.
  CORRECTOR -> PER TREE, held-out rows WITHIN THAT TREE'S OWN REGION. Not optional: computing it
     against all donors gave a 97.2% held-out share instead of 44.9%, fitted every corrector on rows
     from regions its tree never saw, AND THE PLACEBO CAUGHT IT (scored +0.1575 and was adopted).
     An assertion now fails the run outside [0.15, 0.80].
  EVT -> PER REGION, K=5 donor folds held out of the bank. An out-of-bag row from a donor the bank
     has hundreds of other trees on is NOT out-of-model for the ROUTED prediction; fit there and the
     mean-excess is too small and the head under-fires.

EVT HEAD: peaks-over-threshold at ONE fixed quantile (0.90) for every problem, and RAISE-ONLY --
definitional, not a knob: a head answering "how much does the base fall SHORT" must never lower a
prediction. On coral, fitting over all rows instead of the tail made pred@severe fall 59.36 -> 46.71
and the arm HURT (-0.0301); POT + raise-only took it to +0.0002, an equivalence verdict.
OPEN: whether one fixed quantile serves all three is UNTESTED. If fire needs another value, the EVT
is TIER 3 by this project's own definition and the taxonomy must say so.

SEEDS: none in any partition this script creates. Fire's SHIPPED design uses a fixed
np.random.default_rng(7) for donor downsampling and test-cell choice; that is inherited, constant
across runs, and never swept. It is NOT a seed sweep and is disclosed rather than removed, because
removing it would change fire's scored set and break comparability with every earlier fire result.
"""
import os
os.environ.setdefault("JOBLIB_TEMP_FOLDER", "D:/joblib_tmp")

import gc
import re
import sys
import json
import time
import pickle
import argparse
import warnings

import textwrap

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

OUT_ROOT = os.environ.get("ADAPTATION_OUT_ROOT", "D:/treeroute/golden")
DELTA = 0.01
EVT_Q = 0.90
KFOLD = 5

# THE RIDGE-PENALTY GRID. Swept INSIDE the routing, because the expensive object is the routed
# column matrix and the penalty only changes the SOLVE on it: 13 penalties cost 13 solves, not 13
# routings. Defo evidence (D:/defo_overnight/_capacity_vs_lambda.csv, 4 regions at the shipped
# 6,250-column width) says the shipped value is the argmin NOWHERE and the per-region optimum spans
# 10..10,000 -- a 1000x spread -- so a single global value is capped at about 1% while varying it
# per region has a 12.5% ORACLE ceiling.
# Defo's penalty is an absolute lambda (S.ridge); coral and fire use a tree-block ALPHA in
# solve_local on a DIFFERENT scale (shipped 0.5), so the grid is applied MULTIPLICATIVELY there --
# the same 13 relative steps around each problem's own shipped value, never the same numbers.
LAMS = [1, 3, 10, 30, 50, 100, 200, 300, 500, 700, 1000, 1500, 2500, 3000, 10000]
LAMMULT = [L / 100.0 for L in LAMS]      # 0.01x .. 100x, centred on 1.0x = shipped
# 1 AND 3 WERE ADDED AFTER THE GRID WAS CAUGHT CENSORING THE ANSWER. Part 517: defo's first
# sweep had a floor of 10 and TWENTY OF TWENTY-FIVE donors picked exactly 10 -- the boundary.
# Extending to 1 and 3 moved four of the first six donors BELOW the old floor and left the two
# genuine interior optima BIT-IDENTICAL, which is what proved the floor was the problem and not
# the estimator. lambda_select.py was extended then; THIS list was missed and stayed at 13,
# so every coral/fire sweep run before 2026-09-15 swept 0.1x-100x, not 0.01x-100x.
# READ THE GRID FROM THE CACHE, NEVER FROM THIS LIST. Part 517's first bug was a report that
# zipped a NEW 15-value grid against an OLD 13-value cache; zip() stops at the shorter, so every
# cached number was relabelled two positions left and the table looked plausible and was fiction.
# fire_lambda.py loads `lam` from the npz and asserts the two surfaces agree, which is the fix.
BLK = 20000

ap = argparse.ArgumentParser()
ap.add_argument("--problem", required=True, choices=["defo", "coral", "fire"])
ap.add_argument("--split", default="main", choices=["main", "dbl", "time"])
ap.add_argument("--cut", type=int, default=2010)   # coral year cut for split=dbl / split=time
ap.add_argument("--decide", default="inner", choices=["inner", "folds"])
# `donor` IS THE COLD-START MODE: the router's pool is DONOR ROWS ONLY, never the test unit's own
# ecoregion, at any date. The other three modes all allow `same` into the pool -- `strict` admits
# the test ecoregion's pre-CUT rows, `full` and `rollout` admit every earlier row from it -- so all
# three require the test unit to HAVE a history. That requirement is the single biggest barrier to
# anyone deploying this: a newly monitored reef, or a region that has never been surveyed, has no
# history to calibrate on and the architecture simply cannot be run there.
# `donor` answers the question that blocks adoption: what does it cost to give that up entirely?
ap.add_argument("--calib", default="full", choices=["full", "strict", "rollout", "donor"])
ap.add_argument("--arms", default="all", choices=["all", "base"])   # `base` = no correctors/placebo
ap.add_argument("--fold", type=int, default=-1)    # coral DONOR-FOLD pass; -1 = off
ap.add_argument("--lamsweep", type=int, default=0) # sweep the ridge penalty, see LAMS below
ap.add_argument("--sweeparms", default="all")      # restrict the sweep to these arms (cost)
ap.add_argument("--folds", type=int, default=1)    # extra INNER folds for a pooled pick
ap.add_argument("--levels", default="")            # penalty LEVEL grid; blank = LAMMULT
ap.add_argument("--ratios", default="")            # A_CTX/ALPHA RATIO grid; blank = shipped only
ap.add_argument("--sweeponly", type=int, default=0)# route ONLY the swept arms
ap.add_argument("--evt", type=int, default=1)
ap.add_argument("--smoke", type=int, default=0)
# ---- THE FORECAST STUDY. 0 = the shipped NOWCAST, and every line below is then a no-op, so the
# cached nowcast results stay reachable by the code path that produced them. >0 replaces the TOOL
# axis with the forecast-arm axis; see forecast_arms.py for what each arm means and why the tool is
# pinned rather than crossed.
ap.add_argument("--lead", type=int, default=0)
ap.add_argument("--fcarms", default="nowref,lagtrain,lagroute,both")
# THE SELECTION SURFACE. Default `mae` is the historical behaviour and every earlier decision in
# this chapter reproduces under it. `level` and `corr2` are the scale-free readings Part 525
# measured; all three are always REPORTED, and this flag only decides which one ADOPTS.
ap.add_argument("--select", default="mae", choices=["mae", "level", "corr2"])
# CELL CAPS, OVERRIDABLE. defo scores 4,000 cells per region and fire 125 per test region by
# default -- caps chosen for wall time, not for the science. 0 keeps each adapter's own default.
ap.add_argument("--cells", type=int, default=0)
# THE TREE SPLIT CRITERION. Passed straight through to defo_corrector, which puts it in the BANK
# filename; declared here too so it lands in this run's OUT path. Without that, a poisson run would
# overwrite the squared_error results it is supposed to be compared against -- the same collision
# the calib arm and the lead already guard against.
ap.add_argument("--criterion", default="squared_error", choices=["squared_error", "poisson"])
# WHICH COLUMNS DEFINE THE ROUTER'S SIMILARITY SPACE. "all" is the shipped behaviour: every driver
# column, equally weighted. "shap<k>" keeps the k highest mean|SHAP| columns and weights them by
# that importance. "rand<k>" keeps k at random, equal weight, and exists to prove that any gain
# comes from WHICH columns rather than merely from HOW MANY.
ap.add_argument("--simfeat", default="all")
# EXCLUDE EVERY DONOR WITHIN THIS MANY KM OF THE TARGET. An ABLATION, not a feature: nobody would
# deploy it. Cold-start R2 falls monotonically with distance to the nearest donor (+0.2026 at a
# 388 km median, +0.0525 at 1,268 km, -0.6364 at 2,998 km) -- but that is CORRELATIONAL. Surveys
# that happen to have close donors may simply be easier surveys, in better-studied, less extreme
# places. Deleting the close donors from the surveys that HAVE them tests the counterfactual: if
# their error degrades toward the far-tercile level, distance is causal and "add nearby training
# rows" is sound advice. If it does not, those sites were merely easier and the advice is unfounded.
ap.add_argument("--mindist", type=float, default=0.0)
# DONOR CELLS POOLED PER TEST CELL under --calib=donor on fire. Fire's own router fits on one cell's
# ~204 rows against thousands of tree columns, so it is already heavily shrunk; pooling several
# donor cells gives the ridge MORE rows than the shipped path has, not fewer, which should if
# anything improve conditioning. 5 is ~1,000 rows.
ap.add_argument("--donorcells", type=int, default=5)
# DONOR REGIONS POOLED PER TEST REGION under --calib=donor on defo. 4 nearest at ~15,000 rows
# each fills the 60,000-row REGROWS budget the shipped router already uses for self-history.
ap.add_argument("--donorregs", type=int, default=4)
A_, _ = ap.parse_known_args()

if A_.decide == "folds":
    # KFOLD was defined and read by nothing; no adapter consults A_.decide. Running --decide=folds
    # silently computed the INNER surface while the log printed "on the folds surface".
    raise SystemExit("--decide=folds is NOT IMPLEMENTED in this script. No adapter reads --decide; "
                     "the donor-fold surface exists only in decide_arms.py --build=1 (defo only, "
                     "never run). Use --decide=inner and read the SURFACE line for whose rows it is.")

# the calib arm is part of the OUTPUT IDENTITY. Three arms differ only in the pool mask, so their
# predictions are the same shape and would overwrite each other silently -- the exact class of bug
# that let a 400-cell smoke load as a 4,000-cell full run (Part 512's cache-name lesson).
OUT = os.path.join(OUT_ROOT, A_.problem
                   + ("" if A_.split == "main" else "_%s%d" % (A_.split, A_.cut))
                   # defo AT THE DEFAULT CALIB KEEPS ITS BARE PATH, so the shipped results
                   # and every reader of them stay valid; a non-default calib gets a suffix
                   # because otherwise two different calibrations share one cache. Measured:
                   # --calib=strict returned the --calib=donor numbers in 7 seconds.
                   + ("" if (A_.problem == "defo" and A_.calib == "full")
                      else "_" + A_.calib)
                   + ("" if A_.fold < 0 else "_fold%d" % A_.fold)
                   + ("" if A_.lead == 0 else "_L%d" % A_.lead)
                   + ("" if not A_.cells else "_c%d" % A_.cells)
                   + ("" if A_.criterion == "squared_error" else "_" + A_.criterion[:4])
                   + ("" if A_.simfeat == "all" else "_sf" + A_.simfeat)
                   + ("" if A_.mindist <= 0 else "_md%d" % int(A_.mindist))
                   + ("_smoke" if A_.smoke else ""))
# THE LEAD IS PART OF THE OUTPUT IDENTITY for the same reason the calib arm is: a forecast run and
# a nowcast run produce predictions of the same shape for the same test rows, so without the suffix
# the forecast run's caches would overwrite the nowcast's silently and the comparison would be
# against itself. Lead 0 keeps the historical path exactly.
# CORAL/main NOW CARRIES ITS CALIB SUFFIX TOO. It previously wrote to the bare `coral` dir, which
# holds the HISTORICAL SHIPPED RESULT -- run under the original own_earlier mask, before --calib
# existed. Running --split=main --calib=full to measure the forward-reach leak would have silently
# overwritten the very baseline it was being compared against.
# A SMOKE RUN MUST NEVER OCCUPY A FULL RUN'S DIRECTORY. On 2026-09-14 a killed fire smoke wrote
# 19,181 rows into D:/adaptation/fire_rollout, where the full-scale arm has 59,892 -- and the
# runner's skip-if-done check would have SKIPPED that arm as "already computed", then aborted the
# comparison 2.5 h later on the row-count assertion. Same class as Part 512's cache filename that
# lacked the cell count and let a 400-cell smoke load as a 4,000-cell run. Separate the paths.
os.makedirs(OUT, exist_ok=True)


def log(m):
    s = "[%s] %s" % (time.strftime("%H:%M:%S"), m)
    print(s, flush=True)
    with open(os.path.join(OUT, "_adaptation.log"), "a", encoding="utf-8") as f:
        f.write(s + "\n")


def freegb():
    try:
        import psutil
        return psutil.virtual_memory().available / 2.0 ** 30
    except Exception:
        return 99.0


def guard(need, where):
    f = freegb()
    log("    [mem] %.1f GB free before %s (need ~%.1f)" % (f, where, need))
    if f < need:
        raise SystemExit("REFUSING: %.1f GB free, need %.1f for %s. Everything is cached; close "
                         "other apps and rerun." % (f, need, where))


TYPE3 = {
    "defo": dict(name="co_corr_gate", r2=+0.0703, src="Part 503/506, 17 regions"),
    "fire": dict(name="cascade @5%", r2=None,
                 src="Part 485 -- DISCLOSE: the 5% budget was swept ON THE TEST ROWS and the "
                     "criterion mean(pred)/mean(y) needs test labels"),
    "coral": dict(name=None, r2=None,
                  src="NONE EXISTS -- the gate needs a month-on-month surge label and 74.3% of "
                      "coral test sites have ONE row ever. Empty by CONSTRUCTION, not omission."),
}


# ==================================================================================================
# TIER 1 -- DERIVED FROM THE DATA, NOT CONFIGURED
#
# The dividing line between tiers is NOT "did a human set it". It is "can the decision be READ OFF
# A PROPERTY OF THE DATA". The arcsine link is used for proportions -- a script can check whether
# the target is bounded in [0,1] and apply it, with no understanding of the problem required. A gate
# is the opposite: nothing in the data tells you one should exist, what it should catch, or whether
# it should be soft. That needs a theory of the problem, which is why gates stay TIER 3.
#
# Four properties drive four choices:
#     median rows per unit   -> calibration unit   (>=100 per-cell; below that, pooled)
#     target range in [0,1]  -> link               (arcsine vs identity)
#     zero fraction          -> hurdle split
#     Taylor variance power  -> objective          (crit_select.py already automates this)
#
# WHERE A READING IS AMBIGUOUS, OFFER BOTH AND LET MAE DECIDE. coral_final_benchmark.py:169 already
# does exactly this for its own link -- it scores raw and arcsine and keeps the lower MAE. That works
# for the link and the hurdle. It does NOT work for a gate: there is no "gate or not" reading to take.
# ==================================================================================================

LINK_G = lambda v: np.arcsin(np.sqrt(np.clip(np.asarray(v, float), 0.0, 1.0)))
LINK_I = lambda p: np.sin(np.clip(np.asarray(p, float), 0.0, np.pi / 2)) ** 2


def derive_tier1(y, rows_per_unit, name=""):
    """Read Tier 1 off the data. Returns a dict AND logs the reading, so it is auditable."""
    y = np.asarray(y, float)
    y = y[np.isfinite(y)]
    lo, hi = float(y.min()), float(y.max())
    zf = float((y == 0).mean())
    # SCALE-AWARE BOUNDEDNESS. The old test was `hi <= 1.0`, which asks "is this a proportion on a
    # 0-1 scale" -- not "is this a bounded proportion". CORAL is percent bleaching on 0-100, so it
    # FAILED the test and derived link=identity for the one problem that actually SHIPS the arcsine
    # link, and ships it because it was measured at MAE 4.569 -> 4.059. A bounded quantity must not
    # be misread because of the units it is recorded in.
    # The upper bound is read off the data: the smallest of the conventional proportion scales that
    # contains every observation. A target that never exceeds 1 is a fraction; one that never
    # exceeds 100 but does exceed 1 is a percentage. Anything else is unbounded as far as this
    # derivation can tell, and gets the identity link.
    UB = None
    for cand in (1.0, 100.0):
        if lo >= 0.0 and hi <= cand:
            UB = cand
            break
    bounded = UB is not None
    unit = "per-cell" if rows_per_unit >= 100 else "pooled"
    # Taylor's power law: Var = phi * mu^p, estimated on binned means (crit_select's criterion).
    # BIN ON THE POSITIVE ROWS ONLY. On fire, 98.5% of rows are exactly zero, so 20 quantile bins
    # collapse to a handful of duplicated edges, fewer than 5 survive the (mu>0 & vr>0) filter, and
    # the whole objective choice returned NaN -- silently, with no answer at all. The power law is a
    # statement about the mean-variance relationship WHERE THERE IS A MEAN, so the zeros are not
    # informative for it and excluding them is the correct reading, not a workaround.
    pw, nb = float("nan"), 0
    try:
        pos = y[y > 0]
        if len(pos) >= 100:
            q = np.quantile(pos, np.linspace(0, 1, 21))
            b = np.unique(q)
            if len(b) >= 6:
                idx = np.clip(np.searchsorted(b, pos) - 1, 0, len(b) - 2)
                mu = np.array([pos[idx == k].mean() if (idx == k).any() else np.nan
                               for k in range(len(b) - 1)])
                vr = np.array([pos[idx == k].var() if (idx == k).sum() > 1 else np.nan
                               for k in range(len(b) - 1)])
                ok = np.isfinite(mu) & np.isfinite(vr) & (mu > 0) & (vr > 0)
                nb = int(ok.sum())
                if nb >= 5:
                    pw = float(np.polyfit(np.log(mu[ok]), np.log(vr[ok]), 1)[0])
    except Exception:
        pw = float("nan")
    d = dict(range=(lo, hi), bounded=bounded, zero_frac=zf, rows_per_unit=rows_per_unit,
             unit=unit, link="arcsine" if bounded else "identity",
             hurdle=zf >= 0.50, taylor_p=pw)
    log("  TIER 1 DERIVED%s: y in [%.4g, %.4g] | scale %s | zeros %.1f%% | rows/unit %s"
        % ((" " + name) if name else "", lo, hi,
           ("0-%g bounded" % UB) if bounded else "unbounded", 100 * zf, rows_per_unit))
    log("    Taylor p %s (from %d positive-row bins)%s"
        % (("%.2f" % pw) if np.isfinite(pw) else "UNDETERMINED", nb,
           "  <- too few bins; the objective choice has NO answer here" if not np.isfinite(pw) else ""))
    log("    -> calibration unit %s | link %s | hurdle %s"
        % (d["unit"], d["link"], "YES" if d["hurdle"] else "no"))
    return d


# WHAT EACH PROBLEM ACTUALLY RUNS, and where it KNOWINGLY differs from the derivation. A divergence
# is allowed -- three chapters of measurement outrank a two-line rule -- but it must be DECLARED
# here, so that a silent one becomes impossible.
TIER1_ACTUAL = {
    "defo":  dict(unit="pooled",   link="arcsine",
                  why_unit=None),
    "fire":  dict(unit="per-cell", link="arcsine",
                  why_unit=None),
    "coral": dict(unit="k=50 nbr", link="arcsine",
                  why_unit="derive_tier1's rule is BINARY (per-cell vs pooled) and cannot express a "
                           "NEIGHBOUR pool. Coral's median site has ONE row ever, so `pooled` is the "
                           "rule's answer and k=50 neighbours is the design that exists BECAUSE no "
                           "per-site history does. Offered, not derived -- the layer reports the "
                           "accuracy of each unit and the user chooses."),
}


def tier1_check(derived, problem):
    """Compare what the data SAYS to what the adapter DOES, and refuse a silent divergence.

    derive_tier1 has existed since this chapter began and was called exactly ONCE -- from run_defo,
    as a bare statement, with rows_per_unit hardcoded to 17 and the return value discarded. It
    logged a reading that nothing consumed. The portability claim ("point it at a new problem and
    the user edits nothing") rests entirely on those readings being right AND being in charge, and
    neither had ever been tested.
    tier1_audit.py now tests the first half: 7 of 9 readings reproduce the shipped configuration,
    link 3/3 and hurdle 3/3. This function is the second half. It does NOT force the derivation --
    a measured configuration outranks a rule -- it forces the divergence to be DECLARED.
    THE OBJECTIVE DIVERGENCE IS NOW A DECISION, NOT AN OVERSIGHT (user ruling, 2026-09-21).
    crit_select writes POISSON for defo into D:/crit_select.csv (R3, p_hat +1.916, 28.2 SE above
    the midpoint) and every bank in this project builds with sklearn's DEFAULT squared_error,
    because no builder passes criterion= at all. Fire and coral agree with their verdict only by
    coincidence.
    ASKED AND ANSWERED: defo SHIPS ON squared_error. The user was reminded that defo's reported
    loss to lgbm_tweedie might be a misconfiguration rather than an architectural limit, and chose
    to leave the objective as built rather than rebuild the bank. That is a legitimate call -- a
    measured configuration outranks a derived rule, which is this function's whole premise -- and
    the consequence is stated plainly rather than buried: DEFO'S NUMBERS ARE squared_error NUMBERS
    AND THE POISSON ALTERNATIVE WAS NEVER MEASURED AT FULL SCALE. Any claim that the architecture
    reaches its limit on defo is therefore a claim about the squared_error configuration only.
    """
    act = TIER1_ACTUAL.get(problem)
    if act is None:
        log("  TIER 1 CHECK: no declared configuration for %r -- derivation is ADVISORY only" % problem)
        return
    for k in ("unit", "link"):
        if derived[k] == act[k]:
            log("  TIER 1 %-5s DERIVED %-10s == RUNNING %-10s  agree" % (k, derived[k], act[k]))
            continue
        why = act.get("why_" + k)
        if not why:
            raise SystemExit(
                "TIER 1 UNDECLARED DIVERGENCE on %r/%s: the data derives %r, the adapter runs %r, "
                "and no reason is recorded in TIER1_ACTUAL. Either fix the adapter or declare the "
                "divergence with its measurement." % (problem, k, derived[k], act[k]))
        log("  TIER 1 %-5s DERIVED %-10s != RUNNING %-10s  DECLARED DIVERGENCE:" % (k, derived[k], act[k]))
        for line in textwrap.wrap(why, 92):
            log("      " + line)


# ==================================================================================================
# SHARED TOOL LAYER -- identical maths for every problem
# ==================================================================================================

def fit_correctors(trees, inbag, home, X, y, mf, depth=6, placebo=False, minrows=50):
    from sklearn.tree import DecisionTreeRegressor
    corr, nfit, nskip, shares = [], 0, 0, []
    for j, t in enumerate(trees):
        ob = np.setdiff1d(home[j], inbag[j], assume_unique=False)
        assert np.intersect1d(ob, inbag[j]).size == 0, "tool row leaked into the in-bag set"
        shares.append(len(ob) / max(len(home[j]), 1))
        if len(ob) < minrows:
            corr.append(None)
            nskip += 1
            continue
        r = y[ob] - t.predict(X[ob]).astype(np.float64)
        if placebo:
            r = np.roll(r, len(r) // 2)
        corr.append(DecisionTreeRegressor(max_depth=depth, min_samples_leaf=10, max_features=mf,
                                          random_state=j).fit(X[ob], r))
        nfit += 1
    sh = float(np.mean(shares)) if shares else 0.0
    log("    correctors %d fitted / %d skipped | own-region held-out share %.1f%%%s"
        % (nfit, nskip, 100 * sh, "  [PLACEBO]" if placebo else ""))
    assert 0.15 <= sh <= 0.80, (
        "held-out share %.3f outside the plausible band -- near 1.0 means it was taken against ALL "
        "regions instead of the tree's own, the bug the placebo caught on coral." % sh)
    return corr


class UndershootHead(object):
    """Peaks-over-threshold, RAISE-ONLY. Monotone, so the base ranking is preserved exactly."""

    def __init__(self, p, t, q=EVT_Q):
        from sklearn.isotonic import IsotonicRegression
        p, t = np.asarray(p, float), np.asarray(t, float)
        self.u = float(np.quantile(p, q))
        m = p > self.u
        self.n_exc = int(m.sum())
        self.ok = self.n_exc >= 50
        if self.ok:
            self.iso = IsotonicRegression(out_of_bounds="clip", increasing=True).fit(p[m], t[m])

    def predict(self, p):
        p = np.asarray(p, float)
        if not self.ok:
            return p
        out = p.copy()
        m = p > self.u
        if m.any():
            out[m] = np.maximum(p[m], self.iso.predict(p[m]))
        return out


# ==================================================================================================
# DECISION / VERDICT / REPORT
# ==================================================================================================

def r2(y, p, ref=None):
    """R2 against a REFERENCE mean. `ref` is the TRAIN mean when supplied.

    THE CONVENTION MATTERS AND COST ME TWO WRONG DIAGNOSES. Parts 503-512 centre the denominator on
    the TRAIN mean (defo_sharedrows.py:215 `gm = y[tr].mean(); den_r = sum((y[te]-gm)**2)`), this
    harness was centring on the TEST mean. Because
        sum((y_te - gm)^2) = sum((y_te - ybar_te)^2) + n*(ybar_te - gm)^2
    the train-centred denominator is ALWAYS >= the test-centred one, so the same predictions score
    HIGHER under the chapter's convention -- co_base +0.0416 there against +0.0120 here, with MAE
    identical to six decimals in all 17 regions. Nothing was ever wrong with the predictions; I
    "fixed" a clip and a row contract chasing a bug that did not exist.
    MAE is comparable across harnesses. R2 is NOT, unless the reference mean matches."""
    y, p = np.asarray(y, float), np.asarray(p, float)
    m = float(np.mean(y)) if ref is None else float(ref)
    ss = float(((y - m) ** 2).sum())
    return 1.0 - float(((y - p) ** 2).sum()) / ss if ss > 0 else float("nan")


def mae(y, p):
    return float(np.abs(np.asarray(y, float) - np.asarray(p, float)).mean())


def jack(v):
    v = np.asarray(v, float)
    n = len(v)
    if n < 3:
        return float(v.mean()), float("nan"), float("nan"), float("nan")
    jk = np.array([np.delete(v, i).mean() for i in range(n)])
    se = float(np.sqrt((n - 1) / n * ((jk - jk.mean()) ** 2).sum()))
    return float(v.mean()), v.mean() - 1.96 * se, v.mean() + 1.96 * se, se


def verdict(d, label):
    """FOUR cases. CANNOT TELL is NOT a failure verdict and must never be merged with equivalence --
    an earlier version did exactly that and printed 'does not beat its own placebo' on a run where
    it had beaten it by +0.0797."""
    m, lo, hi, se = jack(d)
    if not np.isfinite(lo):
        v = "CANNOT TELL"
    elif lo > 0:
        v = "HELPS"
    elif hi < 0:
        v = "HURTS"
    elif -DELTA <= lo and hi <= DELTA:
        v = "DOES NOT HELP (equivalent)"
    else:
        v = "CANNOT TELL"
    return dict(label=label, mean=m, lo=lo, hi=hi, se=se, mde=2.8 * se,
                wins=int((np.asarray(d) > 0).sum()), n=len(d), verdict=v)


CONTROLS = ("placebo",)          # scored and reported, NEVER selectable

# WHOSE ROWS EACH DECISION SURFACE IS BUILT FROM. Printed verbatim, because "test window never
# touched" was printed for a year while coral was deciding on test targets, and because even the two
# honest surfaces are NOT donor-blind -- they use the TEST UNIT'S OWN pre-test history. That is
# legitimate under the two-tier rule (base models never train on a test region; the router may
# calibrate on its pre-test rows) but it is a weaker claim than "configured from donors alone", and
# the difference has to be visible at the point the decision is printed.
SURFACE = {
    "defo": "TEST REGION's own rows, 2003-2016 fit -> 2017-2019 score (NOT donor-only)",
    "fire": "TEST CELLS' own history, <=2016 fit -> 2017-2018 score (NOT donor-only)",
    # CORAL'S ENTRY WAS STALE. It read "NONE -- no pre-test window exists", which described the
    # pipeline before the donor-fold pass existed and was still being printed as current provenance
    # after coral had acquired a decision surface at every lead. Coral genuinely has no pre-test
    # window -- test rows end 2019 and the median site has one row ever -- so it decides the only
    # other way the data allows, and that is DONOR-ONLY, which is a STRONGER claim than defo's and
    # fire's, not a weaker one.
    "coral": ("HELD-OUT DONOR ecoregions, K=5 folds, bank <=cut -> score the held-out donors' "
              "later rows (DONOR-ONLY: no test ecoregion is opened at any point)"),
}

# WHICH ARM EACH PLACEBO IS A CONTROL FOR. Declared, never inferred from the name: the old code
# matched the literal string "corrector", which only defo has, so the corrector-vs-placebo
# comparison silently never fired on coral or fire -- the two problems whose placebo finding
# motivated the control. Note fire's placebo is routed with use_link=False, so its counterpart is
# raw_corrector; pairing it with link_corrector would compare across DIFFERENT LINKS.
PLACEBO_OF = {"defo": "corrector", "coral": "link_corrector", "fire": "raw_corrector"}


def sim_weights(FC, Xtr, ytr, mode, log=print):
    """A weight per driver column for the router's similarity space. FITS ON DONOR ROWS ONLY.

    Returns a vector w with len(FC) entries. Z is multiplied by w before distances are taken, so a
    zero weight removes a column and a large weight stretches that axis.

    "all"      -> ones. The shipped behaviour, and the control the others are measured against.
    "shap<k>"  -> mean|SHAP| over the donor rows, top k kept and used AS the weights (normalised to
                  mean 1 so the overall distance scale is comparable to `all`), the rest zeroed.
    "rand<k>"  -> k columns at random, weight 1. THE PLACEBO for shap<k>.

    NO TEST ROW IS TOUCHED. The model whose SHAP values are read is fitted on Xtr/ytr, which the
    caller passes as the donor block only. That makes the similarity space data-driven and still
    leak-free -- the distinction the whole benchmark turns on.
    """
    import re as _re
    w = np.ones(len(FC))
    if mode == "all":
        return w, "all %d columns, weight 1 (shipped)" % len(FC)
    # rand<k>o<j> SHIFTS THE STRIDE. rand5 scored 9.958 -- the only positive R2 in the cold-start
    # family -- while rand10 from the same generator scored 14.909. One arbitrary subset landing
    # well is not evidence that k=5 is good; it may be evidence that THAT subset is. Offsetting the
    # stride gives other equally-arbitrary subsets at the same width, which is the only way to tell
    # a width effect from a lucky draw. Choosing rand5 because it won ON TEST would be the oracle
    # defect this project spent a day removing.
    m = _re.match(r"^(shap|rand)(\d+)(?:o(\d+))?$", mode)
    if not m:
        raise SystemExit("--simfeat must be all, shap<k>, rand<k> or rand<k>o<j>; got %r" % mode)
    kind, k = m.group(1), int(m.group(2))
    off = int(m.group(3) or 0)
    if k < 1 or k > len(FC):
        raise SystemExit("--simfeat=%s: k must be in 1..%d" % (mode, len(FC)))
    if kind == "rand":
        # SEEDLESS BY CONSTRUCTION. This project's standing rule is no seeds; a random draw that
        # varies run to run would make the placebo unreproducible. The draw is therefore a fixed
        # deterministic stride through the column order -- arbitrary with respect to importance,
        # which is all a placebo needs, and identical on every run.
        idx = (np.arange(0, len(FC), max(1, len(FC) // k)) + off) % len(FC)
        idx = np.unique(idx)[:k]
        w = np.zeros(len(FC))
        w[idx] = 1.0
        return w, ("%d columns by fixed stride offset %d, equal weight (PLACEBO for shap%d); "
                   "cols %s" % (len(idx), off, k, ",".join(str(i) for i in idx[:8])))
    cache = os.path.join(OUT_ROOT, "_coral_shap_%d.npz" % len(FC))
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        if list(z["cols"]) == list(FC) and int(z["n"][0]) == len(Xtr):
            imp = z["imp"]
        else:
            imp = None
    else:
        imp = None
    if imp is None:
        from sklearn.ensemble import HistGradientBoostingRegressor
        log("    computing SHAP on %s DONOR rows x %d cols (cached after)"
            % (format(len(Xtr), ","), len(FC)))
        mdl = HistGradientBoostingRegressor(early_stopping=False, random_state=0).fit(Xtr, ytr)
        try:
            import shap
            ex = shap.TreeExplainer(mdl)
            sv = ex.shap_values(Xtr)
            imp = np.abs(np.asarray(sv)).mean(0)
        except Exception as e:
            # PERMUTATION IMPORTANCE IS THE DECLARED FALLBACK, NOT A SILENT ONE. It answers the
            # same question -- how much does this column move the prediction -- by a different
            # route, and the log says which was used so the result is never ambiguous.
            log("    shap unavailable (%s); using PERMUTATION importance on donor rows instead"
                % str(e)[:60])
            from sklearn.inspection import permutation_importance
            r = permutation_importance(mdl, Xtr, ytr, n_repeats=3, random_state=0, n_jobs=4)
            imp = np.clip(r.importances_mean, 0, None)
        np.savez_compressed(cache, imp=imp, cols=np.array(FC), n=np.array([len(Xtr)]))
    ordr = np.argsort(-imp)[:k]
    w = np.zeros(len(FC))
    w[ordr] = imp[ordr]
    if w.sum() <= 0:
        raise SystemExit("--simfeat=%s: every selected column has zero importance" % mode)
    w = w / w[w > 0].mean()                  # mean weight 1, so distances stay comparable to `all`
    top = ", ".join("%s(%.3f)" % (FC[i], imp[i]) for i in ordr[:5])
    return w, "top %d by mean|SHAP| on donor rows, importance-weighted; leaders: %s" % (k, top)


def fold_decision(arms, lead=0):
    """CORAL'S DECISION, MADE ON HELD-OUT DONOR ECOREGIONS. Returns (pick, detail) or (None, why).

    LEAD SELECTS WHICH FOLD TABLE IS READ, and mixing them is the failure this argument prevents.
    The lead-0 table ranks the TOOL arms (base/raw/link_corrector/raw_corrector); a forecast table
    ranks lagtrain/lagroute/both. Handing forecast arm names to the lead-0 table matches exactly one
    of them -- `base` -- and an argmin over one candidate is not a decision.

    The donor-fold pass (--fold=0..4) scores every arm on held-out DONOR ecoregions run through the
    exact test-time protocol, and never opens a test ecoregion. Its POOLED argmin is coral's tool
    decision; this function loads it so the main run can APPLY that decision instead of declaring
    it has none. Per-fold picks are carried through too, because a 3-1-1 split is a weak decision
    and must be reported as one rather than laundered into a single confident name.
    """
    import glob as _g
    # EXCLUDE THE SMOKE RUNS. The glob "coral_dbl*_strict_fold*" also matches
    # coral_dbl2005_strict_fold0_smoke and its four siblings -- 800-row capped runs that were half
    # of the ten files this decision was pooling over. reference_smoke_deltas_lie records that a
    # smoke delta under ~0.01 carries no sign information, so they have no business in a shipping
    # decision. Measured: the pick is link_corrector on real-only (9.860 vs base 10.253), on
    # smoke-only and on the contaminated pool, so this changes the provenance, not the answer.
    pat = ("coral_dbl*_strict_fold*" if not lead else "coral_dbl*_fold*_L%d" % lead)
    fs = sorted(f for f in _g.glob(os.path.join(OUT_ROOT, pat, "_preds.npz"))
                if "_smoke" not in f)
    if not fs:
        return None, ("no donor-fold pass has been run for lead %d (adaptation.py --fold=0..4%s)"
                      % (lead, "" if not lead else " --lead=%d" % lead))
    tot, per = {}, []
    for f in fs:
        z = dict(np.load(f, allow_pickle=True))
        yy = z["y"].astype(np.float64)
        sc = {a: float(np.mean(np.abs(yy - z[a].astype(np.float64))))
              for a in arms if a in z and a not in CONTROLS}
        if not sc:
            continue
        per.append(min(sc, key=sc.get))
        for a, v in sc.items():
            tot.setdefault(a, []).append((v, len(yy)))
    if not tot:
        return None, "donor-fold results exist but share no arm with this run"
    # AN ARGMIN OVER ONE CANDIDATE IS NOT A DECISION. The fold pass scored the NOWCAST arms
    # (base/raw/link_corrector/raw_corrector). A forecast run's arms are base/lagtrain/lagroute/both,
    # so the overlap is the single name "base" -- and this function duly returned it as a 5/5
    # unanimous pick. At lead>0 `base` is the CEILING: the nowcast bank on NOWCAST features, which is
    # not a forecast at all. The caller would have shipped the ceiling as the chosen forecast model
    # and labelled it FINAL.
    # Require a real contest. One arm means the fold pass has nothing to say about this arm set.
    if len(tot) < 2:
        return None, ("donor-fold results share only %s with this run -- an argmin over one "
                      "candidate is not a decision" % sorted(tot))
    # pool by ROWS, not by fold -- folds differ 3.3x in size and a fold mean would over-weight
    # the small ones.
    pooled = {a: sum(v * n for v, n in L) / sum(n for _, n in L) for a, L in tot.items()}
    pick = min(pooled, key=pooled.get)
    agree = sum(1 for p in per if p == pick)
    # THE VOTE AND THE WIDTH CAVEAT TRAVEL WITH THE DECISION. A 2/5 pooled argmin is a real decision
    # on real held-out evidence and a 5/5 one is not the same thing; printing only the winner loses
    # the difference. The bank-width caveat is attached here too because it applies to EVERY fold
    # decision and to nothing else, so anywhere this note is shown, it belongs.
    return pick, ("%d folds, pooled argmin MAE; per-fold picks %s; %d/%d agree%s | bank built from "
                  "%d of %d donor groups, so the fold pass routes a NARROWER column space than the "
                  "test pass -- valid for RANKING arms, and its absolute numbers are never reported"
                  % (len(per), "/".join(per), agree, len(per),
                     "  <- SPLIT VOTE, a weak decision" if agree != len(per) else "",
                     KFOLD - 1, KFOLD))


def report(problem, P, y, per_unit, decide_mae):
    # THE PLACEBO IS A CONTROL, NOT A CANDIDATE. It was selectable until 2026-09-13 and was ADOPTED
    # on two of three coral splits -- not because the machinery broke, but because a scrambled-
    # residual arm is nearly identical to base and can win a near-tie on MAE. A control that can be
    # chosen is not a control.
    # decide_mae is None when the adapter HAS NO HONEST SURFACE. Coral is that case: it has no
    # pre-test inner window (test rows end 2019, median 1 row/site). Until 2026-09-14 run_coral built
    # the surface as mae(TEST y, TEST preds) and this function duly adopted the test-best arm on all
    # three splits, while the log printed "test window never touched" and a NOTE describing a
    # donor-side fit that the code never computed. No honest surface is better than a silent one:
    # the layer now DECLINES TO DECIDE and says so. The arm table below is unaffected and still
    # prints -- those are real test MAEs; what was invalid was SELECTING on them.
    if A_.lead:
        # THE TABLE BELOW MEANS SOMETHING DIFFERENT AT LEAD > 0 AND MUST SAY SO. `base` is not the
        # untooled arm here, it is the NOWCAST CEILING; the candidates are not tools, they are
        # answers to "what has to be retrained"; and the Type 1/2/3 block at the bottom is a
        # statement about tool tiers that this run did not vary. Printing the usual headings over
        # forecast arms would be the same class of mislabelling as Part 517's shifted grid: every
        # number correct, every label wrong.
        import forecast_arms as _F
        n_, u_, _h = _F.NATIVE[problem]
        log("-" * 100)
        log("FORECAST RUN -- lead %d x %d %s. READ THE TABLE AS FOLLOWS:" % (A_.lead, n_, u_))
        log("  base       = nowref, the NOWCAST REFERENCE re-scored on the rows the lag leaves.")
        log("               NOT A CEILING: a forecast arm can and does beat it, because nowref")
        log("               tracks the TRAIN SET and a longer cut changes the donor bank.")
        log("               It uses drivers a forecaster does not have. It is not a candidate.")
        log("  lagtrain   ARM A -- trees retrained on t-1 features")
        log("  lagroute   ARM B -- nowcast trees unchanged, fed t-1 features; router refit only")
        log("  both       ARM C -- A's and B's columns concatenated")
        log("  The TOOL was held fixed at `%s` and NOT varied, so the Type 1/2/3 block below is"
            % _F.FCTOOL[problem])
        log("  carried over from the nowcast run and describes the tool axis, not this one.")
    fold_note = None
    if decide_mae is None and problem == "coral" and A_.fold < 0 and not A_.lead:
        # coral has no inner window, but it DOES have a donor-fold surface. Use it.
        pick, fold_note = fold_decision(list(P.keys()))
        cand = None
    elif decide_mae is None and problem == "coral" and A_.lead and A_.fold < 0:
        # THE LEAD-0 FOLD TABLE IS ABOUT TOOLS AND IS STILL NOT CONSULTED HERE. It ranks
        # base/raw/link_corrector/raw_corrector; handed the forecast arm names it matches exactly
        # one -- `base` -- and would "adopt" it on a candidate set of one. A selector whose evidence
        # does not cover the candidates is not a selector; it is a default wearing a verdict's
        # clothes, the same defect Part 515 found in coral's original `dec`.
        # WHAT IS NEW is a table built AT THIS LEAD, by five donor-fold passes over the forecast
        # arms. fold_decision(lead=...) reads only those, so the evidence covers the candidates.
        # `base` is withheld: at a lead it is the nowcast CEILING, not a deployable forecast, and a
        # control that can be selected is not a control.
        cand = None
        pick, fold_note = fold_decision([k for k in P.keys() if k != "base"], lead=A_.lead)
        if pick is None:
            log("  NOTE: no donor-fold table exists at %s, so no arm is adopted. Build one with"
                % _F.lead_label(problem, A_.lead))
            log("  adaptation.py --fold=0..4 --lead=%d, then re-run without --fold." % A_.lead)
    elif A_.fold >= 0:
        # A FOLD RUN IS EVIDENCE, NOT A DECISION. It scores the arms on held-out donors so that a
        # LATER run, without --fold, can pool the folds and choose. If it fell through to the
        # decline-to-base branch below it would write "=> ADOPTED: base" into the fold's own log --
        # a verdict where none was reached, and a completion marker a runner would read as success.
        cand, pick = None, None
        log("  FOLD PASS %d/%d: this run produces EVIDENCE and adopts nothing. Pool the folds by"
            % (A_.fold + 1, KFOLD))
        log("  re-running without --fold; fold_decision reads them and returns the argmin.")
    elif decide_mae is None:
        # NO SURFACE AT ALL -> DECLINE TO BASE. "No adoption" is not an answer: the layer's whole
        # job is to return a configuration, and the conservative one is the untooled base. That is
        # a decision with a consequence, and it is scored like any other.
        cand, pick = None, "base"
    else:
        # THE _lvl_ AND _c2_ ENTRIES ARE SURFACES, NOT ARMS, and must never enter the candidate set.
        # They share a dict with the arms for caching convenience; without this filter the layer
        # would happily "adopt" an arm called `_c2_base`.
        cand = {k: v for k, v in decide_mae.items()
                if k not in CONTROLS and not k.startswith(("_lvl_", "_c2_"))}
        if A_.lead:
            # ON A FORECAST RUN `base` IS THE CEILING, NOT A CANDIDATE, AND IT CANNOT BE DEPLOYED.
            # base is aliased to nowref -- the nowcast bank on nowcast features -- so it answers the
            # question using drivers that do not exist at issue time. Leaving it selectable lets the
            # layer "adopt" it and print `TYPE 2 adaptation -> base` as though a forecasting system
            # had been chosen, when what was chosen is the thing the study is measuring AGAINST.
            # Same rule as the placebo: a control that can be selected is not a control.
            cand.pop("base", None)
        if not cand:
            raise SystemExit("no candidate arms left after removing controls")
        lvl = {k[5:]: v for k, v in decide_mae.items()
               if k.startswith("_lvl_") and k[5:] in cand}
        c2 = {k[4:]: v for k, v in decide_mae.items()
              if k.startswith("_c2_") and k[4:] in cand}
        SURF = {"mae": (cand, min, "raw inner MAE"),
                "level": (lvl, min, "inner MAE at MATCHED prediction level"),
                "corr2": (c2, max, "inner corr^2 (affine-invariant)")}
        use, agg, why = SURF.get(A_.select, SURF["mae"])
        if not use:
            log("  NOTE: --select=%s asked for a scale-free surface but this run did not compute"
                % A_.select)
            log("  one (older cache, or a single arm). Falling back to raw inner MAE.")
            use, agg, why = SURF["mae"]
        pick = agg(use, key=use.get)
        if lvl and c2:
            # PRINTING ALL THREE IS THE POINT. They disagree on exactly the problems where the
            # disagreement matters, and a single number would conceal which one was consulted.
            p_m, p_l, p_c = min(cand, key=cand.get), min(lvl, key=lvl.get), max(c2, key=c2.get)
            log("  THREE SELECTION SURFACES on the SAME inner rows (see reference_mae_ranks_timidity):")
            log("    %-28s -> %-14s %s" % ("raw inner MAE", p_m, "<- SELECTED" if A_.select == "mae" else ""))
            log("    %-28s -> %-14s %s" % ("inner MAE at matched level", p_l, "<- SELECTED" if A_.select == "level" else ""))
            log("    %-28s -> %-14s %s" % ("inner corr^2 (scale-free)", p_c, "<- SELECTED" if A_.select == "corr2" else ""))
            if len({p_m, p_l, p_c}) > 1:
                log("    THEY DISAGREE. Raw MAE ranks TIMIDITY on a mostly-zero target -- its optimum")
                log("    is the conditional median, which is 0 here -- so where these differ, the two")
                log("    scale-free readings are the ones with evidence behind them (Part 525).")
    log("-" * 100)
    log("%-14s %12s %10s" % ("arm", "MAE", "R2"))
    for nm, p in sorted(P.items(), key=lambda kv: mae(y, kv[1])):
        log("%-14s %12.6f %+10.4f" % (nm, mae(y, p), r2(y, p)))
    log("%-14s %12.6f   <- THIS split only; splits are not comparable to each other"
        % ("predict-zero", mae(y, np.zeros_like(y))))

    log("-" * 100)
    if decide_mae is None and fold_note is not None and pick is not None:
        log("THE DECISION -- argmin MAE on HELD-OUT DONOR ECOREGIONS (no test ecoregion opened)")
        log("   %s" % fold_note)
        log("   => ADOPTED: %s" % pick)
    elif decide_mae is None and fold_note is not None and pick is None:
        # fold_note IS NON-None ON REFUSAL TOO -- it carries the REASON. Testing it alone treated a
        # refusal as a verdict and printed "=> ADOPTED: None", which is both false and machine
        # readable: rivals_final.py matches `=> ADOPTED:\s*(\S+)` and would capture the literal
        # string "None" as an arm name. It would then fail the `pick not in arms` check and demote
        # the cell to NOT FINAL, so nothing was ever scored wrongly -- but a log that announces a
        # decision it did not make is exactly what this run's whole audit trail depends on not doing.
        log("THE DECISION -- NOT MADE. The donor-fold surface refused:")
        log("   %s" % fold_note)
        log("   => NO ARM ADOPTED. Build the missing folds, then re-run without --fold.")
    elif decide_mae is None and pick == "base" and fold_note is None and problem == "coral":
        log("THE DECISION -- DECLINED TO BASE. %s" % (fold_note or ""))
        log("   => ADOPTED: base (no honest surface exists, so the layer takes the untooled arm)")
    elif decide_mae is None:
        if A_.arms == "base":
            # fire HAS an honest surface; what it lacks here is the full candidate set.
            log("THE DECISION -- NOT MADE. The candidate set was truncated by --arms=base for cost,")
            log("   so an argmin over it is not the layer's choice. %s's surface is fine; rerun"
                % problem)
            log("   without --arms to get its real Type 2 decision.")
        else:
            log("THE DECISION -- NOT MADE. %s has no decision surface that excludes the test"
                " window." % problem)
            log("   The arm table above is valid; SELECTING on it would not be. Until a donor-side")
            log("   or held-out surface exists, the layer reports and does not adopt.")
        log("   => NO ADOPTION. Any arm quoted for %s here is a HUMAN choice, not a layer choice."
            % problem)
    else:
        surf = SURFACE[problem] if A_.fold < 0 else (
            "HELD-OUT DONOR ecoregions, fold %d of %d -- no test ecoregion is loaded"
            % (A_.fold + 1, KFOLD))
        log("THE DECISION -- %s on the %s surface" % (
            {"mae": "argmin raw MAE", "level": "argmin LEVEL-MATCHED MAE",
             "corr2": "argmax corr^2"}[A_.select if A_.select in ("mae", "level", "corr2") else "mae"],
            surf))
        if A_.fold >= 0:
            log("   ONE FOLD ONLY. The layer's actual choice pools all %d folds -- see"
                " run_calib.py's donor-fold table." % KFOLD)
        # PRINT THE SURFACE THAT WAS CONSULTED. This table used to print `cand` (raw inner MAE)
        # regardless of --select, under a heading naming the chosen surface -- so a corr^2 run
        # printed MAE values ordered by MAE beneath "argmax corr^2", and the CHOSEN row could sit
        # anywhere in that ordering with no explanation. `use` is whichever dict actually decided,
        # including after the fallback to MAE when no scale-free surface was computed.
        _hi = agg is max
        for k, v in sorted(use.items(), key=lambda kv: kv[1], reverse=_hi):
            tag = "   <- CHOSEN" if k == pick else ("   (CONTROL, not selectable)" if k in CONTROLS else "")
            log("   %-12s %12.6f%s" % (k, v, tag))
        log("   (values above are %s; %s is better)" % (why, "higher" if _hi else "lower"))
        log("   => %s" % ("THE LAYER DECLINED -- base won; no tool improved on it"
                          if pick == "base" else "ADOPTED: " + pick))

    log("-" * 100)
    if not per_unit:
        # --sweeponly routed one arm, so there is no `base` to difference against and no verdicts
        # to compute. Say so and return rather than raising: the sweep caches -- which are the
        # entire point of that mode -- are already written and complete by the time we get here.
        # This crashed twice on 2026-09-16, once in assemble() and once here, each time AFTER a
        # 68-minute run had finished its real work.
        log("VERDICTS: NONE. A single arm was routed (--sweeponly), so there is no reference to")
        log("  difference against. The arm table above and the sweep caches are valid and complete.")
        log("-" * 100)
        return
    log("VERDICTS vs base (REPORTED, never used to adopt) | R2 | DELTA %.3f" % DELTA)
    V = []
    for nm, d in per_unit.items():
        v = verdict(d, nm)
        V.append(v)
        log("  %-20s dR2 %+.4f  CI[%+.4f,%+.4f]  MDE %.4f  %2d/%d  -> %s"
            % (v["label"], v["mean"], v["lo"], v["hi"], v["mde"], v["wins"], v["n"], v["verdict"]))
    co = PLACEBO_OF[problem]
    cb = [v for v in V if v["label"] == co]
    pb = [v for v in V if v["label"] == "placebo"]
    if pb and not cb:
        raise SystemExit("placebo scored but its counterpart %r is absent from the per-unit verdicts "
                         "for %s. The old code matched the literal name 'corrector' and so skipped "
                         "this SILENTLY on coral and fire." % (co, problem))
    if cb and pb and cb[0]["mean"]:
        log("  the placebo reproduces %.0f%% of %s's gain over base  (placebo %+.4f vs %+.4f)"
            % (100.0 * pb[0]["mean"] / cb[0]["mean"], co, pb[0]["mean"], cb[0]["mean"]))

    t3 = TYPE3[problem]
    log("-" * 100)
    log("THE THREE TYPES -- %s%s" % (problem, ("/" + A_.split) if problem == "coral" else ""))
    log("  TYPE 1  base                       MAE %12.6f  R2 %+.4f" % (mae(y, P["base"]), r2(y, P["base"])))
    if pick is None:
        # No honest surface -> no Type 2 row. Printing the best arm here would be exactly the
        # oracle-pick-reported-as-automatic that Part 515 records.
        log("  TYPE 2  NOT AVAILABLE -- no decision surface excludes the test window on this")
        log("          problem, so there is no automatic choice to report. See the arm table.")
    else:
        log("  TYPE 2  adaptation -> %-11s  MAE %12.6f  R2 %+.4f"
            % (pick, mae(y, P[pick]), r2(y, P[pick])))
    if t3["name"]:
        log("  TYPE 3  %-26s R2 %s   QUOTED, not computed" % (
            t3["name"], ("%+.4f" % t3["r2"]) if t3["r2"] is not None else "  n/a"))
    else:
        log("  TYPE 3  NONE")
    log("          %s" % t3["src"])
    _vv = os.path.join(OUT, "_verdicts.csv")
    pd.DataFrame(V).to_csv(_vv + ".tmp", index=False)
    os.replace(_vv + ".tmp", _vv)
    # TMP-THEN-REPLACE. os.replace is atomic on Windows for same-volume paths, so a reader either
    # sees the previous complete file or the new complete file, never a partial one.
    _pp = os.path.join(OUT, "_preds.npz")
    np.savez_compressed(_pp + ".tmp.npz", y=y, **P)
    os.replace(_pp + ".tmp.npz", _pp)
    log("  wrote %s" % OUT)
    return pick


def assemble(rows, arms):
    """Per-unit results -> pooled predictions, per-unit R2 deltas, and the inner-window MAEs."""
    y = np.concatenate([r["y"] for r in rows])
    P = {a: np.concatenate([r[a] for r in rows]) for a in arms}
    per = {}
    ref = lambda r: (float(r["ref"][0]) if "ref" in r else None)
    for a in arms:
        if a != "base":
            per[a] = np.array([r2(r["y"], r[a], ref(r)) - r2(r["y"], r["base"], ref(r)) for r in rows])
    co = PLACEBO_OF[A_.problem]          # declared, not matched on the literal name "corrector"
    if co in arms and "placebo" in arms:
        per["corrector-placebo"] = np.array([r2(r["y"], r[co], ref(r))
                                             - r2(r["y"], r["placebo"], ref(r)) for r in rows])
    dec = {}
    if all(("inner_" + a) in rows[0] for a in arms):
        iy = np.concatenate([r["inner_y"] for r in rows])
        for a in arms:
            dec[a] = mae(iy, np.concatenate([r["inner_" + a] for r in rows]))
        # ---- THE SCALE-FREE SURFACES. See reference_mae_ranks_timidity and Part 525.
        # RAW MAE ON A MOSTLY-ZERO TARGET RANKS TIMIDITY, NOT ACCURACY. Its optimum is the
        # conditional median, which is 0 on all four problems here, so every arm sits on the bold
        # side of the minimum and the MAE gradient points at shrinkage for all of them. Measured
        # consequence on defo: read as raw MAE the inner surface landed at 61% of the
        # oracle-to-anti-oracle span, where 50% is random -- it was ANTI-informative, and it duly
        # rejected every forecast arm while the test ordering put `base` last.
        # The SAME ROWS recover the test ordering once the level confound is removed:
        #     within-region Kendall tau  +0.000 -> +0.294  jack95 [+0.064,+0.524]  p = 0.0371
        #     per-region argmin match      7/17 -> 11/17
        # WHY THE ARMS DRIFT APART AT ALL: their own prediction levels move between the inner and
        # test windows by DIFFERENT amounts (measured on defo: base -5.1%, lagtrain -8.8%,
        # both -10.6%, lagroute -11.8%), which re-orders them by timidity alone.
        # Two scale-free readings are computed, never one, because they can disagree and a single
        # number would hide that:
        #   mae_lvl  every arm's inner predictions rescaled to the REFERENCE arm's inner mean, then
        #            MAE. Keeps MAE's loss semantics, removes the level.
        #   corr2    squared correlation. AFFINE-invariant, so no rescaling of any kind can move it.
        # BOTH ARE ALWAYS REPORTED. --select decides which one ADOPTS; the default stays `mae` so
        # that every historical decision in this chapter reproduces exactly.
        base_a = "base" if "base" in arms else arms[0]
        ip = {a: np.concatenate([r["inner_" + a] for r in rows]) for a in arms}
        m0 = float(np.mean(ip[base_a]))
        for a in arms:
            mu = float(np.mean(ip[a]))
            q = ip[a] * (m0 / mu) if abs(mu) > 1e-12 else ip[a]
            dec["_lvl_" + a] = mae(iy, q)
            s = float(np.std(ip[a]))
            dec["_c2_" + a] = (float(np.corrcoef(iy, ip[a])[0, 1] ** 2) if s > 1e-14 else 0.0)
    return P, y, per, dec


# ==================================================================================================
# ADAPTER 1F -- DEFORESTATION, FORECAST.  One year ahead, four arms, one row set.
# ==================================================================================================

def run_defo_forecast():
    """Defo at lead LEAD years. Separate from run_defo on purpose: every conditional threaded
    through the nowcast path is a chance to change a cached number, and the nowcast results are
    the chapter's baseline. This function shares the donors, the tests, the cell cap, the row cap,
    the penalty and the inner window with run_defo, and differs ONLY in what the columns are built
    from.

    THE TOOL IS `link`, defo's adopted Tier-1 arm (MAE 0.005297 against base 0.008639). The
    forecast arms are compared at that tool, not crossed with the tool grid -- see forecast_arms.

    ROW SET. defo_lag drops each cell's first year, so 2003 leaves the TRAINING window and the
    router calibrates on ~6% fewer rows. THE TEST WINDOW IS UNTOUCHED (2020-2023 rows survive,
    carrying 2019-2022 drivers), but `nowref` is still re-scored on the surviving rows rather than
    read from the nowcast cache, because the calibration row set differs and Part 523 measured that
    defo's router is row-starved. All four arms see identical rows, identical calibration indices
    and identical targets.
    """
    import defo_train as T
    import defo_softgate as S
    import defo_corrector as C
    import defo_lag as DL
    import forecast_arms as F
    T.SUB, T.POOL = 150000, 1500000

    CELLS = 400 if A_.smoke else (A_.cells or 4000)
    REGROWS, LAM, INNER, LEAD = 60000, 100.0, 2016, A_.lead
    donors, tests = T.load_split()
    Cn = pd.read_csv("D:/run89full/forest_census.csv")
    forested = Cn[Cn.frac_tc30 >= 0.25].sort_values("cells").region.tolist()
    donors = [r for r in forested if r in donors][:C.NDON]
    tests = [r for r in forested if r in tests][C.FROM:C.FROM + C.NTEST]
    if A_.smoke:
        tests = tests[:2]
    cols = T.feature_cols(C.ARM)
    F.banner("defo", LEAD, log)
    log("  defo | %d donors | %d tests | cells %d | %d of %d columns shift, %d are already <=t-1"
        % (len(donors), len(tests), CELLS, len(DL.lag_columns(cols)), len(cols),
           len(cols) - len(DL.lag_columns(cols))))

    want = [a.strip() for a in A_.fcarms.split(",") if a.strip()]
    ARMS = [a for a in F.FCARMS if a in want]
    if not ARMS:
        raise SystemExit("--fcarms selected nothing. Pick from %s" % ",".join(F.FCARMS))
    if "nowref" not in ARMS:
        raise SystemExit("`nowref` is the reference every other arm is differenced against and "
                         "assemble() aliases `base` to it. It cannot be dropped.")
    p_now = [C.bpath("pair", d, lead=0) for d in donors]
    p_lag = [C.bpath("pair", d, lead=LEAD) for d in donors]
    need = list(p_now) + (list(p_lag) if set(ARMS) & {"lagtrain", "both"} else [])
    miss = [p for p in need if not os.path.exists(p)]
    if miss:
        raise SystemExit(
            "%d defo banks missing (e.g. %s)\n  nowcast banks: py -3.9 -u defo_corrector.py "
            "--build=1\n  LAG-%d banks:   py -3.9 -u defo_corrector.py --build=1 --lead=%d"
            % (len(miss), os.path.basename(miss[0]), LEAD, LEAD))

    def stack(paths, Xm, nrow):
        """Every donor tree's prediction as a column. `base` half of the pair only -- the link arm
        carries no corrector, so the corrector half is never read and never allocated."""
        tot = sum(len(pickle.load(open(p, "rb"))) for p in paths)
        M = np.zeros((nrow, tot), np.float16)
        j = 0
        for p in paths:
            o = pickle.load(open(p, "rb"))
            for t in o:
                if t[0] is not None:
                    for a in range(0, nrow, BLK):
                        b = min(a + BLK, nrow)
                        M[a:b, j] = t[0].predict(Xm[a:b]).astype(np.float16)
                j += 1
            del o
            gc.collect()
        return M

    # THE HEADROOM IS COMPUTED, NOT GUESSED, AND COUNTED ONCE. Two float16 stacks of NCOL columns
    # over ~21 rows per cell, plus the float64 Gram the solve holds -- (2*NCOL)^2 for `both`,
    # NCOL^2 otherwise. A flat 5.2 GB refused a 400-cell smoke that needs 0.6, which trains the
    # habit of overriding the guard, and a guard that gets overridden is worse than no guard.
    NCOL = sum(len(pickle.load(open(p, "rb"))) for p in p_now)
    WIDE = 2 * NCOL if "both" in ARMS else NCOL
    # THE PEAK IS THE MAX OVER PHASES, NOT THE SUM. The first version added every term and asked
    # for 5.3 GB on a machine that routinely shows 5.1 free, which would have refused the whole
    # defo stage over a peak that never happens: the single-block arms hold S.ridge's float32 fit
    # slice but only the narrow Gram, and `both` holds the wide Gram but ridge2's 20,000-row blocks
    # instead of a fit slice. They do not coexist.
    _st = CELLS * 21 * NCOL * 2 / 2.0 ** 30                     # ONE float16 stack
    _fit = REGROWS * NCOL * 4 / 2.0 ** 30                       # S.ridge's float32 fit slice
    _blk = 2 * 20000 * NCOL * 4 / 2.0 ** 30                     # ridge2's two row blocks
    _single = 2 * _st + NCOL ** 2 * 8 / 2.0 ** 30 + _fit        # lagtrain / lagroute
    _both = 2 * _st + WIDE ** 2 * 8 / 2.0 ** 30 + _blk          # arm C, if it is being routed
    NEED_GB = round(max(_single, _both if "both" in ARMS else 0.0) + 0.8, 1)
    log("  %d columns per bank | widest solve %d | headroom required %.1f GB"
        % (NCOL, WIDE, NEED_GB))

    NEED = ["y", "inner_y", "ref"] + ARMS + ["inner_" + a for a in ARMS]
    rows = []
    for i, reg in enumerate(tests, 1):
        f = os.path.join(OUT, "%s_c%d.npz" % (reg, CELLS))
        if os.path.exists(f):
            z = np.load(f)
            m_ = [k for k in NEED if k not in z.files]
            if m_:
                log("  [stale] %s is missing %s -- recomputing" % (reg, ",".join(m_[:3])))
            else:
                rows.append({k: z[k] for k in z.files if k != "region"})
                log("  [cached] %s" % reg)
                continue
        # THE HEADROOM IS COMPUTED, NOT GUESSED. Two float16 stacks of NCOL columns over ~21 rows
        # per cell, plus the float64 Gram the solve holds -- (2*NCOL)^2 for `both`, NCOL^2
        # otherwise. A flat 5.2 GB was refusing a 400-cell smoke that needs 0.6, which trains the
        # habit of ignoring the guard, and a guard that gets ignored is worse than no guard.
        guard(NEED_GB, "forecast scoring %s (%d cols/bank, widest solve %d)" % (reg, NCOL, WIDE))
        t0 = time.time()
        meta, X = T.load_region(reg, cols, cap=CELLS)
        m2, Xl, kept = DL.apply_lag(meta, X, cols, LEAD)
        Xn = X[kept]                      # nowcast features on EXACTLY the surviving rows
        del X
        gc.collect()
        if i == 1:
            log(DL.report(meta, m2, reg))
        n = len(m2)
        tr = m2.is_train.to_numpy() == 1
        y = m2.y.to_numpy(np.float64)
        yr = m2.year.to_numpy()
        ti = np.flatnonzero(tr & np.isfinite(y))
        te = np.flatnonzero((~tr) & np.isfinite(y))
        if len(ti) > REGROWS:
            ti = ti[np.linspace(0, len(ti) - 1, REGROWS).astype(np.int64)]
        i_fit, i_sc = ti[yr[ti] <= INNER], ti[yr[ti] > INNER]
        assert yr[ti].max() <= 2019 and yr[te].min() >= 2020, "the lag moved the train/test boundary"
        out = dict(y=y[te], inner_y=y[i_sc], ref=np.array([float(y[ti].mean())]))
        g = LINK_G(y)

        def emit(nm, Am, Bm=None):
            """One arm: fit the router on the calibration rows, and again on the inner fit window
            for the decision surface. Same rows, same penalty, same link -- only the columns move."""
            if Bm is None:
                p = LINK_I(S.apply(Am, S.ridge(Am, g, ti, LAM)))
                q = LINK_I(S.apply(Am, S.ridge(Am, g, i_fit, LAM)))
            else:
                p = LINK_I(F.apply2(Am, Bm, F.ridge2(Am, Bm, g, ti, LAM)))
                q = LINK_I(F.apply2(Am, Bm, F.ridge2(Am, Bm, g, i_fit, LAM)))
            out[nm] = np.clip(p, 0.0, 1.0)[te]
            out["inner_" + nm] = np.clip(q, 0.0, 1.0)[i_sc]

        # ORDER IS A MEMORY DECISION. nowref's columns are not needed by any later arm, so they are
        # built and released first; `both` is last because it is the only arm that needs two stacks
        # resident at once. Peak is two stacks (~2.1 GB at 4,000 cells) plus the solve.
        emit("nowref", stack(p_now, Xn, n))
        gc.collect()
        del Xn
        Al = Ar = None
        if set(ARMS) & {"lagtrain", "both"}:
            Al = stack(p_lag, Xl, n)
        if set(ARMS) & {"lagroute", "both"}:
            Ar = stack(p_now, Xl, n)
        if "lagtrain" in ARMS:
            emit("lagtrain", Al)
        if "lagroute" in ARMS:
            emit("lagroute", Ar)
        if "both" in ARMS:
            emit("both", Al, Ar)
        del Al, Ar, Xl, m2, meta
        gc.collect()
        np.savez_compressed(f + ".tmp.npz", **out)
        os.replace(f + ".tmp.npz", f)
        rows.append(out)
        log("  %2d/%d %-28s %.1f min | %s" % (i, len(tests), reg, (time.time() - t0) / 60,
            " ".join("%s %.6f" % (a, mae(out["y"], out[a])) for a in ARMS)))
    # `base` IS `nowref`, aliased rather than routed twice. assemble() differences every arm
    # against `base`, so this makes each per-unit delta read "forecast arm minus the nowcast
    # ceiling ON THE SAME ROWS" -- which is the quantity the study is about.
    for r in rows:
        r["base"], r["inner_base"] = r["nowref"], r["inner_nowref"]
    log("  `base` in the table below IS `nowref`: the nowcast REFERENCE re-scored on the surviving")
    log("  rows. A delta is the COST OF THE LEAD only where it is negative; nowref is not a bound")
    log("  and an arm that beats it has not done something impossible.")
    return assemble(rows, ["base"] + [a for a in ARMS if a != "nowref"])


# ==================================================================================================
# ADAPTER 1 -- DEFORESTATION   region-pooled calibration, 17 rows/cell
# ==================================================================================================

def run_defo():
    import defo_train as T
    import defo_softgate as S
    import defo_corrector as C
    T.SUB, T.POOL = 150000, 1500000          # pin AFTER imports -- defo_corrector mutates them

    CELLS = 400 if A_.smoke else (A_.cells or 4000)   # the OUT path already carries --cells
    REGROWS, LAM, INNER = 60000, 100.0, 2016
    donors, tests = T.load_split()
    Cn = pd.read_csv("D:/run89full/forest_census.csv")
    forested = Cn[Cn.frac_tc30 >= 0.25].sort_values("cells").region.tolist()
    donors = [r for r in forested if r in donors][:C.NDON]
    tests = [r for r in forested if r in tests][C.FROM:C.FROM + C.NTEST]
    if A_.smoke:
        tests = tests[:2]
    cols = T.feature_cols(C.ARM)
    log("  defo | %d donors | %d tests | cells %d | region-pooled (17 rows/cell)"
        % (len(donors), len(tests), CELLS))

    pair = [C.bpath("pair", d) for d in donors]
    plac = [os.path.join("D:/defo_tier2/banks", "plac_%s_n%d_mf%d_c%d_%s.pkl"
                         % (C.ARM, C.NT, C.MF, C.CDEPTH, d)) for d in donors]
    miss = [p for p in pair + plac if not os.path.exists(p)]
    if miss:
        raise SystemExit("%d defo banks missing (e.g. %s)\n  real:    py -3.9 -u defo_corrector.py "
                         "--build=1\n  placebo: py -3.9 -u defo_tier2.py --build=1"
                         % (len(miss), os.path.basename(miss[0])))

    def stack(paths, X, nrow, which):
        tot = sum(len(pickle.load(open(p, "rb"))) for p in paths)
        M = np.zeros((nrow, tot), np.float16)
        j = 0
        for p in paths:
            o = pickle.load(open(p, "rb"))
            for t in o:
                tree = t[0] if which == "base" else (t[1] if which == "corr" else t)
                if tree is not None:
                    for a in range(0, nrow, BLK):
                        b = min(a + BLK, nrow)
                        M[a:b, j] = tree.predict(X[a:b]).astype(np.float16)
                j += 1
            del o
            gc.collect()
        return M

    def form(Pm, Cm, eta, nrow):
        if Cm is None or eta == 0.0:
            return Pm.astype(np.float32)
        q = np.empty((nrow, Pm.shape[1]), np.float32)
        for i in range(0, nrow, BLK):
            j = min(i + BLK, nrow)
            np.multiply(Cm[i:j].astype(np.float32), np.float32(eta), out=q[i:j])
            q[i:j] += Pm[i:j].astype(np.float32)
        return q

    COLD = {}
    if A_.calib == "donor":
        # ONE DONOR BLOCK, BUILT ONCE AND REUSED. Loading donor regions per test region would
        # read the same parquet 17 times; the block is region-tagged so each test region can
        # still select its own nearest subset from it without another read.
        B = pd.read_csv("D:/run89full/forest_region_bbox.csv")
        _cen = {r: ((B[B.region == r].iloc[0]["lat_min"] + B[B.region == r].iloc[0]["lat_max"])
                    / 2.0,
                    (B[B.region == r].iloc[0]["lon_min"] + B[B.region == r].iloc[0]["lon_max"])
                    / 2.0)
                for r in set(donors) | set(tests) if (B.region == r).any()}
        _miss = [r for r in tests if r not in _cen]
        if _miss:
            raise SystemExit("no bbox for test region(s) %s -- cannot pick nearest donors"
                             % ", ".join(_miss))
        _per = max(1, REGROWS // max(1, A_.donorregs))
        log("  COLD START on defo: the ridge is fitted on the %d NEAREST DONOR REGIONS, never"
            % A_.donorregs)
        log("  on the test region's own rows. Donor block capped at %s rows (REGROWS), the same"
            % format(REGROWS, ","))
        log("  cap the shipped router applies to self-history, so both fit on equal rows.")
        # ONLY LOAD WHAT GETS USED. Each test region pools its 4 nearest donors, so across the
        # 17 test regions the union of those choices is much smaller than the 25 available.
        # Loading all of them cost ~220 MB of features for regions no ridge would ever see,
        # and the scoring guard refused the run over it. Centroids are enough to decide this
        # and cost nothing to read.
        from coral_glorys2_ab import haversine as _hv0
        _need = set()
        for _t in tests:
            _o = sorted(((float(_hv0(_cen[_t][0], _cen[_t][1], np.array([_cen[d][0]]),
                                     np.array([_cen[d][1]]))[0]), d)
                         for d in donors if d in _cen))
            _need.update(d for _, d in _o[:A_.donorregs])
        log("  %d of %d donor regions are the nearest-%d for some test region; loading only"
            % (len(_need), len(donors), A_.donorregs))
        log("  those: %s" % ", ".join(sorted(_need)))
        for d in donors:
            if d not in _cen or d not in _need:
                continue
            _m, _X = T.load_region(d, cols, cap=CELLS, train_only=True)
            _ok = np.flatnonzero((_m.is_train.to_numpy() == 1)
                                 & np.isfinite(_m.y.to_numpy(np.float64)))
            if len(_ok) > _per:
                _ok = _ok[np.linspace(0, len(_ok) - 1, _per).astype(np.int64)]
            assert int(_m.iloc[_ok].year.max()) <= 2019, "donor window not closed"
            COLD[d] = (_m.iloc[_ok].reset_index(drop=True), _X[_ok])
            del _m, _X
            gc.collect()
        log("  donor block: %d regions, %s rows total"
            % (len(COLD), format(sum(len(v[0]) for v in COLD.values()), ",")))

    ARMS = ["base", "link", "corrector", "placebo"]
    NEED = ["y", "inner_y"] + ARMS + ["inner_" + a for a in ARMS]

    rows = []
    for i, reg in enumerate(tests, 1):
        # THE CELL COUNT MUST BE IN THE FILENAME. Without it a --smoke=1 run (400 cells) and a
        # full run (4,000) share a cache path, and the full run silently loads smoke results and
        # reports them as final. It would not crash -- it would print plausible numbers.
        f = os.path.join(OUT, "%s_c%d.npz" % (reg, CELLS))
        if os.path.exists(f):
            z = np.load(f)
            miss = [k for k in NEED if k not in z.files]
            if miss:
                # A CACHE FILE FROM AN EARLIER ARM SET. Trusting the filename alone is how a stale
                # cache silently drops an arm -- exactly what defo_sharedrows' tag() guards against.
                log("  [stale] %s is missing %s -- recomputing" % (reg, ",".join(miss[:3])))
            else:
                rows.append({k: z[k] for k in z.files if k != "region"})
                log("  [cached] %s" % reg)
                continue
        guard(4.9, "scoring %s" % reg)
        t0 = time.time()
        meta, X = T.load_region(reg, cols, cap=CELLS)
        n = len(meta)
        tr = meta.is_train.to_numpy() == 1
        y = meta.y.to_numpy(np.float64)
        yr = meta.year.to_numpy()
        ti = np.flatnonzero(tr & np.isfinite(y))
        te = np.flatnonzero((~tr) & np.isfinite(y))
        if len(ti) > REGROWS:
            ti = ti[np.linspace(0, len(ti) - 1, REGROWS).astype(np.int64)]
        i_fit, i_sc = ti[yr[ti] <= INNER], ti[yr[ti] > INNER]
        if A_.calib == "donor":
            # THE FIT ROWS ARE SWAPPED, THE SCORED ROWS ARE NOT. `te` still indexes this
            # region's test-window rows and is untouched, so the scored set is identical to
            # the shipped run and the two are directly comparable.
            from coral_glorys2_ab import haversine as _hv
            _d = sorted(((float(_hv(_cen[reg][0], _cen[reg][1], np.array([_cen[d][0]]),
                                    np.array([_cen[d][1]]))[0]), d) for d in COLD))
            _use = [d for _, d in _d[:A_.donorregs]]
            _dm = pd.concat([COLD[d][0] for d in _use], ignore_index=True)
            _dX = np.vstack([COLD[d][1] for d in _use])
            log("    %s <- donors %s (centroid %s km; an UPPER BOUND, centroid-to-centroid)"
                % (reg, ", ".join(_use),
                   ", ".join("%.0f" % v for v, _ in _d[:A_.donorregs])))
            # The ridge needs the donor rows' tree columns, so X and y for the FIT come from
            # the donor block while everything applied below still comes from this region.
            _ny = len(_dm)
            X = np.vstack([_dX, X])
            y = np.r_[_dm.y.to_numpy(np.float64), y]
            yr = np.r_[_dm.year.to_numpy(), yr]
            n = len(y)
            ti = np.arange(_ny)
            te = te + _ny
            i_fit = ti[yr[ti] <= INNER]
            i_sc = ti[yr[ti] > INNER]
            assert not np.intersect1d(ti, te).size, "a donor row reached the scored set"
        out = dict(y=y[te], inner_y=y[i_sc], ref=np.array([float(y[ti].mean())]))

        if i == 1:
            # MEASURE THE BLOCK THE RIDGE IS FITTED ON. Under cold start `ti` indexes the
            # concatenated donor+region arrays and `meta` holds only the region, so
            # meta.iloc[ti] is out of bounds -- and would be the wrong rows even if it were
            # not, since derive_tier1's rows-per-unit decides per-cell vs pooled and must
            # describe the calibration block, which is now DONOR rows.
            _rpu_src = _dm if A_.calib == "donor" else meta.iloc[ti]
            rpu = float(_rpu_src.groupby("cell_id").size().median())
            tier1_check(derive_tier1(y[ti], rpu, "defo"), "defo")
            log("    NOTE the derived link is ARCSINE but shipped defo uses IDENTITY -- the only")
            log("    problem where nobody asked. Scored below as the `link` arm.")
        Pm = stack(pair, X, n, "base")
        Cm = stack(pair, X, n, "corr")
        # THE TIER-1 LINK ARM. Same columns, same rows, same lambda -- the ONLY change is that the
        # ridge is fitted on G(y) and inverted. Coral measured its link at MAE 4.569 -> 4.059,
        # "beating 5 driver additions combined"; defo has never been asked.
        q = form(Pm, None, 0.0, n)
        wbL = S.ridge(q, LINK_G(y), ti, LAM)
        out["link"] = np.clip(LINK_I(S.apply(q, wbL)), 0.0, 1.0)[te]
        w2L = S.ridge(q, LINK_G(y), i_fit, LAM)
        out["inner_link"] = np.clip(LINK_I(S.apply(q, w2L)), 0.0, 1.0)[i_sc]
        del q
        gc.collect()
        for nm, cm, eta in [("base", None, 0.0), ("corrector", Cm, 1.0)]:
            q = form(Pm, cm, eta, n)
            wb = S.ridge(q, y, ti, LAM)
            out[nm] = np.clip(S.apply(q, wb), 0.0, 1.0)[te]          # target is a FRACTION
            w2 = S.ridge(q, y, i_fit, LAM)
            out["inner_" + nm] = np.clip(S.apply(q, w2), 0.0, 1.0)[i_sc]
            del q
            gc.collect()
        del Cm
        gc.collect()
        Cp = stack(plac, X, n, "plac")
        q = form(Pm, Cp, 1.0, n)
        wb = S.ridge(q, y, ti, LAM)
        out["placebo"] = np.clip(S.apply(q, wb), 0.0, 1.0)[te]
        w2 = S.ridge(q, y, i_fit, LAM)
        out["inner_placebo"] = np.clip(S.apply(q, w2), 0.0, 1.0)[i_sc]
        del q, Cp, Pm, X, meta
        gc.collect()
        np.savez_compressed(f + ".tmp.npz", **out)     # atomic; a killed write must not
        os.replace(f + ".tmp.npz", f)                 # leave a file the resume trusts
        rows.append(out)
        log("  %2d/%d %-28s %.1f min" % (i, len(tests), reg, (time.time() - t0) / 60))
    return assemble(rows, ["base", "link", "corrector", "placebo"])


# ==================================================================================================
# ADAPTER 2 -- CORAL   neighbour-pool calibration, 1 row/site
# ==================================================================================================

def run_coral():
    import coral_poolaudit as PA
    from coral_glorys2_ab import haversine, solve_local, G
    from coral_smoke_regress import continuous_target
    from coral_confound_audit import source_map
    from coral_ghspop_ab import build as build_pop, SHAPE
    from sklearn.tree import DecisionTreeRegressor
    from sklearn.ensemble import RandomForestRegressor

    NPD = 60 if A_.smoke else 500
    MF, K, ALPHA, A_CTX, MINOK = 0.15, 50, 0.5, 0.25, 12
    CTXC = ["month", "doy_sin", "doy_cos", "abslat"]
    INV = lambda p: 100.0 * np.sin(np.clip(p, 0, np.pi / 2)) ** 2
    MODE = "own_earlier"

    X = pd.read_parquet("forecast_features_L0.parquet")
    sp = json.load(open("fullscale_split.json"))
    X["side"] = np.where(X.eco.isin(sp["donors"]), "donor", "test")
    X["y"] = X.sid.map(continuous_target())
    X = X.dropna(subset=["y"]).reset_index(drop=True)
    X = build_pop(X)
    allf = [c for c in X.columns if c not in ("sid", "eco", "side", "pos", "date", "y",
                                              "lat", "lon", "_side", "src")]
    ABS = [c for c in allf if re.match(r"^(mean|std)_\d+$", c)
           or c in ("abslat", "mmm", "mmm_n_years")]
    HOB = [c for c in allf if c.startswith("mhw_")]
    FC = [c for c in allf if c not in ABS + HOB] + HOB
    FC = [c for c in FC if c not in SHAPE] + SHAPE
    dm = X[X.side == "donor"]
    for c in FC:
        if X[c].isna().any():
            X[c] = X[c].fillna(dm[c].median())
    X["yr"] = pd.to_datetime(X.date).dt.year

    CUT = A_.cut
    if A_.fold >= 0:
        # ------------------------------------------------------------------------------------
        # THE DONOR-FOLD PASS. CORAL'S FIRST DECISION SURFACE THAT NEVER OPENS A TEST REGION.
        #
        # Coral has no pre-test inner window (test rows end 2019, median 1 row per site), which is
        # why run_coral had no honest surface at all and the layer declines (Part 515). This builds
        # one the only way the data allows: hold out DONOR ecoregions and treat each as a stand-in
        # for an unseen region, run through the EXACT test-time protocol.
        #
        #     trees   donor ecoregions NOT in this fold, year <= CUT
        #     scored  the HELD-OUT donors' rows, year > CUT
        #
        # Same shape as the real task (unseen ecoregion, later years), so ranking the arms here is a
        # legitimate basis for choosing one -- and no test ecoregion is touched at any point. The
        # held-out donors' post-CUT rows are needed and they exist: the dbl split DROPS donor rows
        # after CUT, so this pass reads them back from X deliberately.
        #
        # WIDTH IS NOT PRESERVED: 16 of 20 donors build the bank, so the fold pass routes a
        # narrower column space than the test pass. reference_width_screening_unsafe warns a width
        # change alone can flip a sign. Acceptable HERE and only here, for the reason decide_arms.py
        # gives: the fold pass RANKS arms against each other at one common width, and its absolute
        # numbers are never reported as results.
        dons = sorted(pd.unique(X[X.side == "donor"].eco.values).tolist())
        grp = [dons[i::KFOLD] for i in range(KFOLD)]
        held = set(grp[A_.fold % KFOLD])
        trn = X[(X.side == "donor") & (~X.eco.isin(held)) & (X.yr <= CUT)].reset_index(drop=True)
        tst = X[(X.side == "donor") & (X.eco.isin(held)) & (X.yr > CUT)].reset_index(drop=True)
        assert not (set(pd.unique(trn.eco.values)) & held), "held-out donor leaked into the bank"
        assert (tst.side == "donor").all(), "a TEST ecoregion entered the donor-fold pass"
        assert int(trn.yr.max()) <= CUT, "donor window not closed in the fold pass"
        log("  CORAL DONOR-FOLD %d/%d | bank from %d donors (<=%d) | scored on %d HELD-OUT donors"
            % (A_.fold + 1, KFOLD, trn.eco.nunique(), CUT, tst.eco.nunique()))
        log("  %s rows train / %s rows scored | NO TEST ECOREGION IS OPENED AT ANY POINT."
            % (format(len(trn), ","), format(len(tst), ",")))
        log("  held out: %s" % ", ".join(str(e) for e in sorted(held)))
    elif A_.split == "dbl":
        # BOTH axes: different regions AND a later window -- what defo/fire/NDVI all do.
        trn = X[(X.side == "donor") & (X.yr <= CUT)].reset_index(drop=True)
        tst = X[(X.side == "test") & (X.yr > CUT)].reset_index(drop=True)
        log("  CORAL DOUBLY BLOCKED (cut %d). UNDERPOWERED BY CONSTRUCTION -- a third the rows, CIs" % CUT)
        log("  ~1.7x wider. A CANNOT TELL here is NOT a refutation of the spatial result; only a")
        log("  sign flip with a CI excluding zero is.")
    elif A_.split == "time":
        # TIME ONLY: every cell regardless of region, split on the year.
        trn = X[X.yr <= CUT].reset_index(drop=True)
        tst = X[X.yr > CUT].reset_index(drop=True)
        ov = float(tst.lat.round(5).astype(str).add("_").add(tst.lon.round(5).astype(str))
                   .isin(trn.lat.round(5).astype(str).add("_").add(trn.lon.round(5).astype(str))).mean())
        log("  CORAL TEMPORAL ONLY (cut %d). MEASURED REEF OVERLAP: %.1f%% of test rows sit on a reef"
            % (CUT, 100 * ov))
        log("  that is ALSO in training -- the model has seen that exact site. A WEAKER block than it")
        log("  looks; at a 2014 cut this was 43.6%%. Report it beside the number, never without.")
    else:
        # SPACE ONLY: the shipped split. Every existing coral result uses this.
        trn = X[X.side == "donor"].reset_index(drop=True)
        tst = X[X.side == "test"].reset_index(drop=True)
    if A_.smoke:
        tst = tst.iloc[:800].reset_index(drop=True)
    log("  coral | %d cols | train %s / %d eco | TEST %s / %d eco | severe %d | neighbour pool k=%d"
        % (len(FC), format(len(trn), ","), trn.eco.nunique(), format(len(tst), ","),
           tst.eco.nunique(), int((tst.y >= 50).sum()), K))

    Vtr = trn[FC].fillna(0).values.astype(np.float32)
    Vte = tst[FC].fillna(0).values.astype(np.float32)
    ytr = trn.y.values.astype(np.float64)
    base_rows = np.arange(len(trn))
    guard(2.5, "coral bank")
    trees, inbag, home = [], [], []
    for e, g in trn.groupby("eco"):
        gi = base_rows[trn.eco.values == e]
        n = len(gi)
        for j in range(NPD):
            rs = np.random.RandomState(int(e) * 17 + j)
            idx = rs.choice(n, size=max(30, int(0.8 * n)), replace=True)
            trees.append(DecisionTreeRegressor(max_depth=8, min_samples_leaf=5, max_features=MF,
                                               random_state=j).fit(Vtr[gi][idx], ytr[gi][idx]))
            inbag.append(gi[np.unique(idx)])
            home.append(gi)
    log("    bank %d trees / %d donors" % (len(trees), trn.eco.nunique()))
    corr = fit_correctors(trees, inbag, home, Vtr, ytr, MF, placebo=False)
    plac = fit_correctors(trees, inbag, home, Vtr, ytr, MF, placebo=True)

    n_tr = len(trn)
    y_all = np.r_[trn.y.values, tst.y.values].astype(np.float64)
    t_all = G(y_all)
    C_ = np.vstack([trn[CTXC].values, tst[CTXC].values]).astype(np.float64)
    C_ = (C_ - C_[:n_tr].mean(0)) / (C_[:n_tr].std(0) + 1e-9)
    M_ = np.r_[trn.mmm.values, tst.mmm.values]
    Z = np.vstack([Vtr, Vte]).astype(np.float64)
    Z = (Z - Z[:n_tr].mean(0)) / (Z[:n_tr].std(0) + 1e-9)
    # THE SIMILARITY SPACE IS SCALED HERE AND NOWHERE ELSE. Standardise first, then weight, so a
    # column's weight means "how much this driver counts" rather than "what units it happens to be
    # in". Weights are fitted on the DONOR block only -- Z[:n_tr] -- which is the same block the
    # standardisation already uses.
    _w, _wnote = sim_weights(FC, Z[:n_tr], y_all[:n_tr], A_.simfeat, log)
    log("  SIMILARITY SPACE: --simfeat=%s -> %s" % (A_.simfeat, _wnote))
    if A_.simfeat != "all":
        Z = Z * _w
    lat = np.r_[trn.lat.values, tst.lat.values]
    lon = np.r_[trn.lon.values, tst.lon.values]
    eco = np.r_[trn.eco.values, tst.eco.values]
    dat = np.r_[trn.date.values, tst.date.values]
    yr_ = np.r_[trn.yr.values, tst.yr.values].astype(np.int64)
    ar = np.arange(len(t_all))
    isdon = ar < n_tr
    sg = RandomForestRegressor(300, max_depth=8, min_samples_leaf=5, n_jobs=4,
                               random_state=0).fit(Vtr, np.abs(ytr - ytr.mean()))
    s = np.clip(sg.predict(np.vstack([Vtr, Vte])), 1e-6, None)
    lo_, hi_ = np.percentile(s, [5, 95])
    W = 1.0 / np.clip(s, lo_, hi_) ** 2

    tag_sweep = ["arm"]

    def route(cc, eta, use_link=True, calib=None):
        """use_link=False fits the local ridge on RAW y instead of G(y). Coral's SHIPPED base is the
        LINKED one, so `raw` is the contrast arm here -- the mirror of defo, where the shipped base
        is raw and `link` is the new arm. Same four arms on every problem, same names."""
        """coral_poolaudit.route_masked's body with the column matrix INJECTED. Everything else --
        pool mask, weights, neighbour count, link, solver -- is untouched, so any difference between
        arms is the COLUMNS and nothing else."""
        calib = calib or A_.calib
        A = np.empty((len(t_all), len(trees)), np.float32)
        for j, t in enumerate(trees):
            A[:n_tr, j] = t.predict(Vtr)
            A[n_tr:, j] = t.predict(Vte)
            if cc is not None and cc[j] is not None:
                A[:n_tr, j] += eta * cc[j].predict(Vtr)
                A[n_tr:, j] += eta * cc[j].predict(Vte)
        # ---- THE CALIBRATION POOL. Three arms, and the difference between them is the whole
        # coral leak question. `full` is causal but uses TRUE test-era labels; `strict` refuses
        # test-era rows entirely; `rollout` admits them carrying the model's OWN PREDICTION.
        #
        # WHAT THE SHIPPED MASK DID WRONG. own_earlier was
        #     (isdon | (same & dat < dat_i)) & (ar != i)
        # -- the date filter applies ONLY to same-ecoregion rows, so a DONOR row of any date could
        # calibrate an earlier test cell. Under --split=dbl every donor row is <= CUT so that hole
        # is closed by the split here, but the clause itself is time-blind and is not reused.
        #
        # ROLLOUT IS THE ONLY ARM IN WHICH NO TEST-ERA LABEL EVER REACHES THE MODEL. It simulates
        # deploying at CUT and running forward with no further survey: after CUT, the model knows
        # only what it predicted. It must therefore run in DATE ORDER, and its errors compound.
        out = np.empty(len(tst))
        _lev_c = ([float(x) for x in A_.levels.split(",")] if A_.levels else list(LAMMULT))
        _rho_c = ([float(x) for x in A_.ratios.split(",")] if A_.ratios else [float(A_CTX) / float(ALPHA)])
        GRID_C = [(m_, r_) for m_ in _lev_c for r_ in _rho_c]
        SW = np.full((len(tst), len(GRID_C)), np.nan) if A_.lamsweep else None
        tgt = (t_all if use_link else y_all).copy()   # rollout mutates the test half; others don't
        HI = (np.pi / 2.0) if use_link else 100.0     # clip self-fed values to the legal range
        order = np.argsort(dat[n_tr:], kind="stable") if calib == "rollout" else np.arange(len(tst))
        nsub = 0
        for i in order:
            gi = n_tr + i
            same = eco == eco[gi]
            if calib == "donor":
                # COLD START. `same` is absent: no row from the target's own ecoregion may enter
                # the pool, whatever its date. The date bound stays because a donor row dated after
                # the target is still a future row, and the assertion below checks it.
                ok = np.where(isdon & (dat < dat[gi]) & (ar != gi))[0]
            elif calib == "strict":
                ok = np.where((isdon | same) & (yr_ <= CUT) & (ar != gi))[0]
            else:
                ok = np.where((isdon | same) & (dat < dat[gi]) & (ar != gi))[0]
            if len(ok) < MINOK:
                out[i] = (t_all if use_link else y_all)[:n_tr].mean()
                if calib == "rollout":
                    tgt[gi] = out[i]
                continue
            d = haversine(lat[gi], lon[gi], lat[ok], lon[ok])
            if A_.mindist > 0:
                # THE ABLATION BITES AFTER eligibility and BEFORE selection, so it removes
                # candidates rather than reordering them. A target whose pool drops below MINOK once
                # its neighbours are deleted falls back to the training mean -- exactly what would
                # happen if those donors had never been collected, which is what is being simulated.
                _keep = d >= A_.mindist
                ok, d = ok[_keep], d[_keep]
                if len(ok) < MINOK:
                    out[i] = (t_all if use_link else y_all)[:n_tr].mean()
                    if calib == "rollout":
                        tgt[gi] = out[i]
                    continue
            gg = ok[np.argsort(d)][:min(len(ok), 3 * K)]
            sel = gg[np.argsort(np.sqrt(((Z[gg] - Z[gi]) ** 2).sum(1)))][:K]
            # THE ASSERTION THAT MAKES THE BLOCK CHECKABLE: nothing in the pool may be dated at or
            # after the target, and under `strict` nothing may post-date CUT.
            assert (dat[sel] < dat[gi]).all() or calib == "strict", "future row in pool"
            # THE COLD-START CLAIM IS ASSERTED, NOT ANNOUNCED. If one row from the target's own
            # ecoregion reaches the pool the mode is not cold-start and the number is not the
            # number it is reported as.
            assert calib != "donor" or not same[sel].any(),                 "a same-ecoregion row entered a DONOR-ONLY pool"
            assert calib != "strict" or (yr_[sel] <= CUT).all(), "post-CUT row in a strict pool"
            if calib == "rollout":
                nsub += int((yr_[sel] > CUT).sum())
            Xc = np.column_stack([np.ones(len(sel)), M_[sel] - M_[sel].mean(), C_[sel], A[sel]])
            xg = np.r_[1.0, M_[gi] - M_[sel].mean(), C_[gi], A[gi]]
            if A_.lamsweep:
                # Same neighbourhood, same columns; SW[i, k] is this row's prediction at grid cell k.
                # The selection happens afterwards, never inside the loop.
                # REPARAMETERISED LIKE FIRE'S (Part 521): a_tree = ALPHA*mlt, a_ctx = ALPHA*mlt*rho,
                # so the RATIO between the tree and context blocks is selectable instead of pinned at
                # the hand-set A_CTX/ALPHA = 0.5. On fire that turned out to be worth 0.000000,
                # because its context block is 2 columns against 9,000. CORAL'S IS 4 AGAINST 9,500 --
                # a 2,375:1 ratio, the same regime -- so the expectation here is another null, and
                # measuring it is how that stops being an assumption.
                for k, (mlt, rho) in enumerate(GRID_C):
                    bb = solve_local(Xc, tgt[sel], W[sel], A.shape[1], len(CTXC),
                                     ALPHA * mlt, ALPHA * mlt * rho)
                    SW[i, k] = float(xg @ bb)
            b = solve_local(Xc, tgt[sel], W[sel], A.shape[1], len(CTXC), ALPHA, A_CTX)
            out[i] = float(xg @ b)
            if calib == "rollout":
                # this prediction becomes a POOL ROW for every later cell. clip, or a bad early
                # year can compound into a runaway over the 14-year horizon.
                tgt[gi] = float(np.clip(out[i], 0.0, HI))
        if calib == "rollout":
            log("      rollout: %d pool slots filled with PREDICTED values (%.1f%% of %d)"
                % (nsub, 100.0 * nsub / max(1, len(tst) * K), len(tst) * K))
        if A_.lamsweep and SW is not None:
            _sf = os.path.join(OUT, "_lamsweep_%s.npz" % tag_sweep[0])
            np.savez_compressed(_sf + ".tmp.npz",
                                y=tst.y.values.astype(np.float64), sw=SW,
                                lam=np.array([g_[0] for g_ in GRID_C], np.float64),
                                rho=np.array([g_[1] for g_ in GRID_C], np.float64),
                                eco=tst.eco.values.astype(str))
            os.replace(_sf + ".tmp.npz", _sf)
            log("      lamsweep: wrote %d rows x %d cells (%d levels x %d ratios)"
                % (SW.shape[0], SW.shape[1], len(_lev_c), len(_rho_c)))
        del A
        gc.collect()
        return out

    P = {}
    SPEC = [("link", None, True), ("raw", None, False),
            ("link_corrector", corr, True), ("raw_corrector", corr, False),
            ("placebo", plac, True)]
    for nm, cc, lk in SPEC:
        t0 = time.time()
        tag_sweep[0] = nm
        v = route(cc, 1.0, lk)
        P[nm] = np.clip(INV(v) if lk else v, 0.0, 100.0)
        log("    %-16s routed | %.1f min | MAE %.4f" % (nm, (time.time() - t0) / 60,
                                                        mae(tst.y.values, P[nm])))
    P["base"] = P["link"]          # coral SHIPS the linked arm -- base is an alias, not a 5th route
    ARMS = ["base", "raw", "link_corrector", "raw_corrector", "placebo"]   # `link` == `base` here
    y = tst.y.values.astype(np.float64)
    # TIER 1, MEASURED AND CHECKED. Coral's rows_per_unit is per SITE, and it is the reason the
    # derivation and the running configuration diverge -- see TIER1_ACTUAL["coral"].
    try:
        _rpu = float(tst.groupby("sid").size().median()) if "sid" in tst.columns else 1.0
    except Exception:
        _rpu = 1.0
    tier1_check(derive_tier1(y, _rpu, "coral"), "coral")
    # per-unit = per ECOREGION, the grain the deliverable holds out
    rows = []
    # R2 ON A TINY GROUP IS UNBOUNDED. At a 5-row floor coral produced dR2 +9.14 with MDE 21.80 --
    # arithmetic noise, not a result. A group needs enough rows AND enough target variance for the
    # denominator to mean anything.
    # A UNIT NEEDS ENOUGH VARIANCE, NOT JUST ENOUGH ROWS. R2 divides by the unit's own variance, so
    # an ecoregion with near-constant y gives an unbounded ratio: the smoke produced dR2 +17.4167
    # with MDE 48.8480 -- arithmetic noise reported as a verdict. Require a real share of the pooled
    # variance as well as a row count.
    MINGRP, VARFRAC = 50, 0.05
    vpool = float(np.var(y))
    for e in pd.unique(tst.eco.values):
        m = tst.eco.values == e
        if m.sum() < MINGRP or float(np.var(y[m])) < VARFRAC * vpool:
            continue
        rows.append(dict(y=y[m], **{k: P[k][m] for k in ARMS}))
    # THE GROUP FLOOR IS FOR THE PER-UNIT VERDICTS ONLY. It was briefly applied to the pooled table
    # too, and coral's headline MAE silently moved 5.669 -> 1.469 between two runs of the SAME
    # config, because the table was then computed over 5 of 22 ecoregions instead of the test set.
    _, _, per, _ = assemble(rows, ARMS)
    Pp = {k: P[k] for k in ARMS}                # ALL test rows
    yy = y
    # NO DECISION SURFACE. This line used to read `dec = {k: mae(y, P[k]) for k in ARMS}` -- the
    # TEST targets against the TEST predictions -- so the layer adopted the test-best arm on all
    # three splits while logging "test window never touched". The inline justification was "SAME
    # KEYS as Pp, or report() KeyErrors on the pick": a KeyError was silenced by handing the
    # selector the answer. Coral genuinely has no pre-test window (test rows end 2019, median 1 row
    # per site), so there is nothing honest to put here; report() now declines to adopt.
    if A_.fold >= 0:
        # THE FOLD PASS IS THE SURFACE. Its scored rows are HELD-OUT DONOR ecoregions -- no test
        # ecoregion is loaded at all -- so ranking the arms on them is exactly the evidence a
        # decision is allowed to use. This is the one coral configuration with an honest `dec`.
        # It is ONE fold; the layer's actual choice pools all KFOLD of them (run_calib.py).
        dec = {k: mae(y, P[k]) for k in ARMS}
    else:
        dec = None
    log("  per-unit verdicts use %d of %d ecoregions (>=%d rows AND >=%.0f%% of pooled variance);"
        % (len(rows), tst.eco.nunique(), MINGRP, 100 * VARFRAC))
    log("  is the FULL test set.")
    log("  NOTE: coral has no pre-test inner window (test rows end 2019, median 1 row/site). This")
    log("  line previously claimed the surface was a DONOR-side fit; no such object was ever")
    log("  computed here, and the surface in use was the TEST SET. There is now no surface at all.")
    if A_.mindist > 0:
        log("  ABLATION: every donor within %.0f km of the target is DELETED from its pool."
            % A_.mindist)
        log("  This simulates never having collected them. A causal test, not a setting.")
    if A_.calib in ("strict", "donor") and A_.split == "dbl":
        # TWO NAMES, ONE POOL. On the doubly-blocked split every donor row is <=CUT and
        # every test row is >CUT, so strict's `same` branch selects nothing and donor's
        # date filter is a no-op: both reduce to ALL DONORS. They produced byte-identical
        # predictions (md5 f202ff6174c29d74) across four days without anyone noticing,
        # because a duplicated mode looks exactly like an independent measurement.
        log("  NOTE --calib=strict and --calib=donor are THE SAME POOL on split=dbl.")
        log("  Both reduce to all donors: A holds no test-ecoregion row dated <=%d (the"
            % CUT)
        log("  split drops them), so strict's same-ecoregion branch is empty and donor's")
        log("  date filter is a no-op. THIS RUN IS NOT AN INDEPENDENT MEASUREMENT of the")
        log("  other; do not report them as two results.")
    log("  CALIBRATION POOL for this run: --calib=%s%s"
        % (A_.calib, "  <- COLD START: donor rows only, the test unit's own history is NEVER used"
           if A_.calib == "donor" else ""))
    return Pp, yy, per, dec


# ==================================================================================================
# ADAPTER 2F -- CORAL, FORECAST.  Lead 1 = every driver window re-cut at T-30 days.
# ==================================================================================================

def run_coral_forecast():
    """Coral at lead LEAD x 30 days, four arms, IDENTICAL ROWS.

    CORAL'S LAG IS NOT A ROW SHIFT AND THIS IS THE CLEANEST OF THE THREE PROBLEMS BECAUSE OF IT.
    Its features are window summaries -- dhw_30, hs_max_56, mean_180 and so on -- each ending at a
    cut date. coral_forecast.build(lead) recomputes every one of them with the cut moved back
    `lead` days, on the SAME survey rows with the SAME targets. So no row is lost, the test set is
    identical to the nowcast test set, and `nowref` here must reproduce the cached nowcast number
    rather than merely being comparable to it. That identity is a free end-to-end check on the
    whole forecast harness and is asserted below.

    11 of the 94 columns are unaffected by the cut (sid, eco, position, month, doy, abslat, the
    masks): they are static or seasonal, known arbitrarily far ahead. The other 83 move.

    WHAT DIFFERS BETWEEN ARMS BESIDES THE COLUMNS, STATED. Coral's router picks each target's
    calibration pool by driver similarity (`Z`), weights it by a fitted spread model (`W`) and
    centres on `mmm`. All three are built FROM THE DRIVERS, so a forecast arm must build them from
    the drivers it actually has -- using the nowcast Z to select neighbours for a forecast arm
    would leak T-0 information into the pool choice through the back door. Each arm therefore uses
    its own frame throughout. The consequence is that arms differ in pool MEMBERSHIP as well as in
    columns, which is honest for a forecast claim and is the opposite of the nowcast study's
    convention, where holding the pool fixed was what isolated the tool.
    """
    import forecast_arms as F
    from coral_glorys2_ab import haversine, solve_local, G
    from coral_smoke_regress import continuous_target
    from coral_ghspop_ab import build as build_pop, SHAPE
    from coral_forecast import feat_path
    from sklearn.tree import DecisionTreeRegressor
    from sklearn.ensemble import RandomForestRegressor

    NPD = 60 if A_.smoke else 500
    MF, K, ALPHA, A_CTX, MINOK = 0.15, 50, 0.5, 0.25, 12
    CTXC = ["month", "doy_sin", "doy_cos", "abslat"]
    INV = lambda p: 100.0 * np.sin(np.clip(p, 0, np.pi / 2)) ** 2
    LEAD, CUT = A_.lead, A_.cut
    DAYS = F.lead_days_coral(LEAD)        # MONTHS -> days, explicit ladder, 12 mo = 365 d not 360
    F.banner("coral", LEAD, log)
    log("  LEAD LADDER: --lead is MONTHS on coral and fire, YEARS on defo, so --lead=12 is one")
    log("  year on both coral and fire and the two curves share an axis. This run: %s."
        % F.lead_label("coral", LEAD))

    want = [a.strip() for a in A_.fcarms.split(",") if a.strip()]
    ARMS = [a for a in F.FCARMS if a in want]
    if "nowref" not in ARMS:
        raise SystemExit("`nowref` is the reference every other arm is differenced against.")

    def prep(path):
        """One feature frame through coral's exact loading contract: target join, population
        columns, donor-median imputation, column order. Run twice, once per lead."""
        if not os.path.exists(path):
            raise SystemExit("%s is missing. Build it first:  py -3.9 -u coral_forecast.py "
                             "--leads=%d" % (path, DAYS))
        Xf = pd.read_parquet(path)
        sp = json.load(open("fullscale_split.json"))
        Xf["side"] = np.where(Xf.eco.isin(sp["donors"]), "donor", "test")
        Xf["y"] = Xf.sid.map(continuous_target())
        Xf = Xf.dropna(subset=["y"]).reset_index(drop=True)
        Xf = build_pop(Xf)
        allf = [c for c in Xf.columns if c not in ("sid", "eco", "side", "pos", "date", "y",
                                                   "lat", "lon", "_side", "src")]
        ABS = [c for c in allf if re.match(r"^(mean|std)_\d+$", c)
               or c in ("abslat", "mmm", "mmm_n_years")]
        HOB = [c for c in allf if c.startswith("mhw_")]
        FCc = [c for c in allf if c not in ABS + HOB] + HOB
        FCc = [c for c in FCc if c not in SHAPE] + SHAPE
        dm = Xf[Xf.side == "donor"]
        for c in FCc:
            if Xf[c].isna().any():
                Xf[c] = Xf[c].fillna(dm[c].median())
        Xf["yr"] = pd.to_datetime(Xf.date).dt.year
        return Xf, FCc

    X0, FC0 = prep("forecast_features_L0.parquet")
    XL, FCL = prep(feat_path(DAYS))
    # THE TWO FRAMES MUST BE THE SAME SURVEYS IN THE SAME ORDER, or every arm-to-arm difference
    # below is a row misalignment wearing a lead's clothes.
    # A LONGER LEAD CAN LOSE EVENTS. coral_forecast's own curve restricts every lead to the common
    # sid set for exactly this reason: a site whose 10-year window no longer fits once the cut moves
    # back drops out, and comparing arms across a changing test set would partly measure the test
    # set. At 30 days nothing is lost (21,430 rows both sides, verified), so this is a no-op today
    # and a guard for L180/L365 tomorrow -- written now because a silent row-count difference is
    # precisely the failure that would not announce itself.
    assert FC0 == FCL, "the two leads carry different feature columns"
    if len(X0) != len(XL) or not (X0.sid.values == XL.sid.values).all():
        common = np.intersect1d(X0.sid.values, XL.sid.values)
        log("  lead %dd lost %d of %d surveys; both frames restricted to the %s common sids"
            % (DAYS, len(X0) - len(common), len(X0), format(len(common), ",")))
        X0 = X0[X0.sid.isin(common)].sort_values("sid").reset_index(drop=True)
        XL = XL[XL.sid.isin(common)].sort_values("sid").reset_index(drop=True)
    assert (X0.sid.values == XL.sid.values).all(), "sid alignment failed"
    assert (X0.date.values == XL.date.values).all(), "dates differ between leads"
    assert np.allclose(X0.y.values, XL.y.values), "TARGETS differ between leads"
    nmove = sum(1 for c in FC0 if not np.allclose(X0[c].fillna(-999), XL[c].fillna(-999)))
    log("  coral | %d cols, %d re-cut at T-%dd, %d unaffected (static/seasonal) | %s rows"
        % (len(FC0), nmove, DAYS, len(FC0) - nmove, format(len(X0), ",")))

    if A_.fold >= 0:
        # ------------------------------------------------------------------------------------
        # THE DONOR-FOLD PASS, AT A LEAD. The same construction run_coral() uses at lead 0, and it
        # has to exist separately because the dispatch sends --lead>0 here and this function used
        # to ignore --fold entirely -- scoring the ordinary test set while writing a directory
        # named as though it were a fold. Twenty such runs completed before identical dR2 across
        # all five folds gave it away.
        #
        #     trees   donor ecoregions NOT in this fold, year <= CUT
        #     scored  the HELD-OUT donors' rows, year > CUT, with the lead's re-cut features
        #
        # THE MASK IS BUILT ON X0 AND THAT IS CORRECT: X0 and XL are asserted sid-for-sid identical
        # above, and every arm indexes both frames through the same itr/ite, so one mask governs
        # both leads. Building it twice would invite them to diverge.
        #
        # WIDTH IS NOT PRESERVED here either -- 16 of 20 donors build the bank, the same caveat
        # run_coral() records. The fold pass RANKS arms at one common width and its absolute
        # numbers are never reported as results.
        dons = sorted(pd.unique(X0[X0.side == "donor"].eco.values).tolist())
        grp = [dons[i::KFOLD] for i in range(KFOLD)]
        held = set(grp[A_.fold % KFOLD])
        mtr = ((X0.side == "donor") & (~X0.eco.isin(held)) & (X0.yr <= CUT)).values
        mte = ((X0.side == "donor") & (X0.eco.isin(held)) & (X0.yr > CUT)).values
        assert not (set(pd.unique(X0.iloc[np.flatnonzero(mtr)].eco.values)) & held), \
            "held-out donor leaked into the bank"
        assert (X0.iloc[np.flatnonzero(mte)].side == "donor").all(), \
            "a TEST ecoregion entered the donor-fold pass"
        assert int(X0.iloc[np.flatnonzero(mtr)].yr.max()) <= CUT, \
            "donor window not closed in the fold pass"
        assert mte.sum() > 0, "this fold scored no rows -- the hold-out is empty"
        log("  CORAL DONOR-FOLD %d/%d AT LEAD %s | bank from %d donors (<=%d) | scored on %d "
            "HELD-OUT donors" % (A_.fold + 1, KFOLD, F.lead_label("coral", LEAD),
                                 X0.iloc[np.flatnonzero(mtr)].eco.nunique(), CUT,
                                 X0.iloc[np.flatnonzero(mte)].eco.nunique()))
        log("  %s rows train / %s rows scored | NO TEST ECOREGION IS OPENED AT ANY POINT."
            % (format(int(mtr.sum()), ","), format(int(mte.sum()), ",")))
        log("  held out: %s" % ", ".join(str(e) for e in sorted(held)))
    elif A_.split == "dbl":
        mtr = ((X0.side == "donor") & (X0.yr <= CUT)).values
        mte = ((X0.side == "test") & (X0.yr > CUT)).values
        log("  CORAL DOUBLY BLOCKED (cut %d), the same split the nowcast run used." % CUT)
    elif A_.split == "time":
        mtr, mte = (X0.yr <= CUT).values, (X0.yr > CUT).values
    else:
        mtr, mte = (X0.side == "donor").values, (X0.side == "test").values
    if A_.smoke:
        mte = mte & (np.cumsum(mte) <= 800)
    itr, ite = np.flatnonzero(mtr), np.flatnonzero(mte)
    trn, tst = X0.iloc[itr].reset_index(drop=True), X0.iloc[ite].reset_index(drop=True)
    n_tr = len(trn)
    y = tst.y.values.astype(np.float64)
    log("  train %s / %d eco | TEST %s / %d eco | severe %d | neighbour pool k=%d | calib %s"
        % (format(n_tr, ","), trn.eco.nunique(), format(len(tst), ","), tst.eco.nunique(),
           int((tst.y >= 50).sum()), K, A_.calib))

    def frame_parts(Xf):
        """Everything the router needs, built from ONE frame: columns, pool geometry, weights."""
        Vtr = Xf.iloc[itr][FC0].fillna(0).values.astype(np.float32)
        Vte = Xf.iloc[ite][FC0].fillna(0).values.astype(np.float32)
        Zz = np.vstack([Vtr, Vte]).astype(np.float64)
        Zz = (Zz - Zz[:n_tr].mean(0)) / (Zz[:n_tr].std(0) + 1e-9)
        Cz = np.vstack([Xf.iloc[itr][CTXC].values, Xf.iloc[ite][CTXC].values]).astype(np.float64)
        Cz = (Cz - Cz[:n_tr].mean(0)) / (Cz[:n_tr].std(0) + 1e-9)
        Mz = np.r_[Xf.iloc[itr].mmm.values, Xf.iloc[ite].mmm.values]
        sg = RandomForestRegressor(300, max_depth=8, min_samples_leaf=5, n_jobs=4,
                                   random_state=0).fit(Vtr, np.abs(ytr0 - ytr0.mean()))
        s = np.clip(sg.predict(np.vstack([Vtr, Vte])), 1e-6, None)
        lo_, hi_ = np.percentile(s, [5, 95])
        return dict(Vtr=Vtr, Vte=Vte, Z=Zz, C=Cz, M=Mz, W=1.0 / np.clip(s, lo_, hi_) ** 2)

    ytr0 = trn.y.values.astype(np.float64)
    guard(3.5, "coral forecast: two frames, two banks")
    PT = {"now": frame_parts(X0), "lag": frame_parts(XL)}

    def bank(Vtr):
        # ITERATE IN groupby ORDER, NOT APPEARANCE ORDER. run_coral builds its bank with
        # `for e, g in trn.groupby("eco")`, which visits ecoregions SORTED. pd.unique visits them in
        # first-appearance order. The trees are the same trees either way -- each is seeded from its
        # own ecoregion id -- but the COLUMN ORDER differs, and while a ridge is permutation
        # invariant in exact arithmetic, this function's whole claim is that `nowref` REPRODUCES the
        # cached nowcast to 1e-6. Do not spend that contract's credibility on a gratuitous
        # difference; match the original.
        trees = []
        base_rows = np.arange(n_tr)
        for e in sorted(pd.unique(trn.eco.values)):
            gi = base_rows[trn.eco.values == e]
            n = len(gi)
            for j in range(NPD):
                rs = np.random.RandomState(int(e) * 17 + j)
                idx = rs.choice(n, size=max(30, int(0.8 * n)), replace=True)
                trees.append(DecisionTreeRegressor(max_depth=8, min_samples_leaf=5,
                                                   max_features=MF, random_state=j)
                             .fit(Vtr[gi][idx], ytr0[gi][idx]))
        return trees

    BK = {"now": bank(PT["now"]["Vtr"])}
    log("    nowcast bank %d trees / %d donors" % (len(BK["now"]), trn.eco.nunique()))
    if set(ARMS) & {"lagtrain", "both"}:
        BK["lag"] = bank(PT["lag"]["Vtr"])
        log("    lag-%dd  bank %d trees / %d donors" % (DAYS, len(BK["lag"]), trn.eco.nunique()))

    t_all = G(np.r_[ytr0, y])
    lat = np.r_[trn.lat.values, tst.lat.values]
    lon = np.r_[trn.lon.values, tst.lon.values]
    eco = np.r_[trn.eco.values, tst.eco.values]
    dat = np.r_[trn.date.values, tst.date.values]
    yr_ = np.r_[trn.yr.values, tst.yr.values].astype(np.int64)
    ar = np.arange(len(t_all))
    isdon = ar < n_tr

    def columns(bk, fr):
        A = np.empty((len(t_all), len(BK[bk])), np.float32)
        for j, t in enumerate(BK[bk]):
            A[:n_tr, j] = t.predict(PT[fr]["Vtr"])
            A[n_tr:, j] = t.predict(PT[fr]["Vte"])
        return A

    def route(A, fr):
        """coral's shipped neighbour-pool router with the column matrix injected. The pool mask,
        the link, the weights and the solver are untouched; `fr` names which frame supplies the
        geometry, so a forecast arm never selects neighbours on drivers it would not have."""
        Z_, C_, M_, W = PT[fr]["Z"], PT[fr]["C"], PT[fr]["M"], PT[fr]["W"]
        out = np.empty(len(tst))
        # ---- THE THREE CALIBRATION POOLS, AND ROLLOUT IS NOT OPTIONAL HERE.
        # The first version of this adapter branched only on `strict` and let everything else fall
        # into the `full` clause -- so --calib=rollout produced FULL numbers in a directory named
        # rollout. Three planned stages would have been mislabelled duplicates of three others, and
        # nothing would have crashed or looked wrong. Rollout is the ONLY arm in which no test-era
        # LABEL ever reaches the model, so silently substituting `full` for it inverts the exact
        # property the arm exists to demonstrate.
        #   full     same-ecoregion rows dated before the target, carrying TRUE labels
        #   strict   no test-era row at all; the pool stops at CUT
        #   rollout  the same rows as `full`, carrying the model's OWN PREDICTIONS
        # ROLLOUT MUST RUN IN DATE ORDER and its errors compound, which is why it is slower and why
        # its predictions are clipped before being fed forward.
        roll = (A_.calib == "rollout")
        tgt = t_all.copy()                       # rollout mutates the test half; the others do not
        order = np.argsort(dat[n_tr:], kind="stable") if roll else np.arange(len(tst))
        nsub = 0
        for i in order:
            gi = n_tr + i
            same = eco == eco[gi]
            if A_.calib == "strict":
                ok = np.where((isdon | same) & (yr_ <= CUT) & (ar != gi))[0]
            else:
                ok = np.where((isdon | same) & (dat < dat[gi]) & (ar != gi))[0]
            if len(ok) < MINOK:
                out[i] = t_all[:n_tr].mean()
                if roll:
                    tgt[gi] = out[i]
                continue
            d = haversine(lat[gi], lon[gi], lat[ok], lon[ok])
            if A_.mindist > 0:
                # THE ABLATION BITES AFTER eligibility and BEFORE selection, so it removes
                # candidates rather than reordering them. A target whose pool drops below MINOK once
                # its neighbours are deleted falls back to the training mean -- exactly what would
                # happen if those donors had never been collected, which is what is being simulated.
                _keep = d >= A_.mindist
                ok, d = ok[_keep], d[_keep]
                if len(ok) < MINOK:
                    out[i] = (t_all if use_link else y_all)[:n_tr].mean()
                    if calib == "rollout":
                        tgt[gi] = out[i]
                    continue
            gg = ok[np.argsort(d)][:min(len(ok), 3 * K)]
            sel = gg[np.argsort(np.sqrt(((Z_[gg] - Z_[gi]) ** 2).sum(1)))][:K]
            assert A_.calib != "strict" or (yr_[sel] <= CUT).all(), "post-CUT row in a strict pool"
            assert A_.calib == "strict" or (dat[sel] < dat[gi]).all(), "future row in the pool"
            if roll:
                nsub += int((yr_[sel] > CUT).sum())
            Xc = np.column_stack([np.ones(len(sel)), M_[sel] - M_[sel].mean(), C_[sel], A[sel]])
            xg = np.r_[1.0, M_[gi] - M_[sel].mean(), C_[gi], A[gi]]
            b = solve_local(Xc, tgt[sel], W[sel], A.shape[1], len(CTXC), ALPHA, A_CTX)
            out[i] = float(xg @ b)
            if roll:
                # this prediction becomes a POOL ROW for every later cell. Clip, or one bad early
                # year compounds across the horizon.
                tgt[gi] = float(np.clip(out[i], 0.0, np.pi / 2.0))
        if roll:
            log("      rollout: %s pool slots filled with PREDICTED values (%.1f%% of %d)"
                % (format(nsub, ","), 100.0 * nsub / max(1, len(tst) * K), len(tst) * K))
        return np.clip(INV(out), 0.0, 100.0)

    SRC = {"nowref": ("now", "now"), "lagtrain": ("lag", "lag"), "lagroute": ("now", "lag")}
    P, keep = {}, {}
    for nm in ARMS:
        t0 = time.time()
        if nm == "both":
            # ARM C. The two column sets are concatenated into ONE tree block, so solve_local
            # trace-normalises across both halves -- the same treatment each half gets alone, since
            # both are tree predictions of the same target on the same scale. The WIDTH doubles and
            # that is a real confound (reference_router_ridge_scaling: a 6.6x shrinkage collapse
            # from 3k to 15k columns); it is reported, not normalised away.
            A = np.hstack([keep["lagtrain"], keep["lagroute"]])
            P[nm] = route(A, "lag")
            del A
        else:
            bk, fr = SRC[nm]
            A = columns(bk, fr)
            if nm in ("lagtrain", "lagroute") and "both" in ARMS:
                keep[nm] = A
            P[nm] = route(A, fr)
            if nm not in keep:
                del A
        gc.collect()
        log("    %-10s routed | %.1f min | MAE %.4f" % (nm, (time.time() - t0) / 60,
                                                        mae(y, P[nm])))
    keep.clear()
    gc.collect()
    P["base"] = P["nowref"]
    ARMS_R = ["base"] + [a for a in ARMS if a != "nowref"]
    log("  `base` IS `nowref` -- the nowcast REFERENCE on IDENTICAL rows. Each delta is the cost")
    log("  of the lead. CONTRACT: nowref should reproduce the cached nowcast MAE for this split.")
    cache = os.path.join(OUT_ROOT, "coral" + ("" if A_.split == "main" else "_%s%d"
                                              % (A_.split, A_.cut)) + "_" + A_.calib, "_preds.npz")
    # The nowcast run's TRAIN row count, recovered from its own log so the contract check can tell
    # "the harness is broken" from "this lead trains on a slightly different set".
    _NTRN_NOWCAST = len(trn)
    try:
        import re as _re
        _lg = os.path.join(os.path.dirname(cache), "_adaptation.log")
        _m = _re.findall(r"train ([\d,]+) /", io.open(_lg, encoding="utf-8").read())
        if _m:
            _NTRN_NOWCAST = int(_m[-1].replace(",", ""))
    except Exception:
        pass
    # A SKIPPED CHECK MUST SAY WHY IT SKIPPED. The first version printed nothing when the row
    # counts differed, so a smoke run -- where they differ by construction -- looked exactly like a
    # full run whose contract had passed. A check that is silent about not running is worse than no
    # check, because it buys confidence it did not earn.
    if not os.path.exists(cache):
        log("  CONTRACT SKIPPED: no cached nowcast at %s" % cache)
    else:
        z = np.load(cache)
        if "base" not in z.files:
            log("  CONTRACT SKIPPED: %s has no `base` arm" % cache)
        elif len(z["base"]) != len(y):
            why = (" (expected under --smoke)" if A_.smoke else
                   " (expected under --fold: the test set is HELD-OUT DONORS, not test ecoregions)"
                   if A_.fold >= 0 else " *** INVESTIGATE")
            log("  CONTRACT SKIPPED: cached nowcast has %s rows, this run has %s -- not the same "
                "test set%s" % (format(len(z["base"]), ","), format(len(y), ","), why))
        elif len(trn) != _NTRN_NOWCAST:
            # THE CHECK ONLY MEANS ANYTHING IF THE BANK IS THE SAME BANK, AND AT LEADS > 1 IT IS
            # NOT. A longer cut drops a few surveys, the common-sid restriction removes them from
            # BOTH frames, and the training set shrinks (5,978 -> 5,976 at 90 d, 5,975 at 180 and
            # 365 d) -- so the donor bank differs and nowref legitimately differs with it. The first
            # version compared against a nowcast built on all 5,978 rows and cried
            # "*** Every arm below is suspect" on three of four coral leads. It was wrong each time.
            # THE TELL, and it is decisive: L180 and L365 have the SAME train count and produced the
            # IDENTICAL nowref (5.948909). nowref tracks the TRAIN SET, not the lead.
            log("  CONTRACT NOT APPLICABLE: this lead trains on %s rows against the cached "
                "nowcast's %s" % (format(len(trn), ","), format(_NTRN_NOWCAST, ",")))
            log("  (the longer cut dropped surveys, so the donor bank is not the same bank). The")
            log("  test rows ARE identical, so the WITHIN-run arm comparison below is unaffected;")
            log("  only the cross-run tie to the cached nowcast is unavailable. nowref %.6f vs "
                "cached %.6f." % (mae(y, P["nowref"]), mae(y, z["base"])))
        else:
            d = abs(mae(y, z["base"]) - mae(y, P["nowref"]))
            log("  CONTRACT nowref vs cached nowcast `base`: %.6f vs %.6f  (|d| %.2e) %s"
                % (mae(y, z["base"]), mae(y, P["nowref"]), d, "OK" if d < 1e-6 else "*** DIFFERS"))
            if d >= 1e-6:
                log("  *** Same rows AND the same training set, yet the harness does not reproduce")
                log("  *** the nowcast. Every arm below is suspect. Investigate before reading it.")

    MINGRP, VARFRAC = 50, 0.05
    vpool = float(np.var(y))
    rows = []
    for e in pd.unique(tst.eco.values):
        m = tst.eco.values == e
        if m.sum() < MINGRP or float(np.var(y[m])) < VARFRAC * vpool:
            continue
        rows.append(dict(y=y[m], **{k: P[k][m] for k in ARMS_R}))
    _, _, per, _ = assemble(rows, ARMS_R)
    # THE SIDS ARE PERSISTED BECAUSE A LADDER NEEDS THEM. _preds.npz carries y and the arms but no
    # row identity, and a longer coral lead can drop surveys, so without this a cross-lead table
    # would silently compare different test sets -- the same class of error the nowref arm exists
    # to prevent WITHIN a run.
    _rr = os.path.join(OUT, "_rows.npz")
    np.savez_compressed(_rr + ".tmp.npz",
                        sid=tst.sid.values.astype(np.int64),
                        eco=tst.eco.values.astype(str),
                        date=tst.date.values.astype(str), lead_days=np.array([DAYS]))
    os.replace(_rr + ".tmp.npz", _rr)
    log("  per-unit verdicts use %d of %d ecoregions; the table is the FULL test set."
        % (len(rows), tst.eco.nunique()))
    log("  NO DECISION SURFACE: coral has no pre-test inner window, so the layer reports the")
    log("  forecast arms and does not adopt one. Same standing rule as its nowcast run.")
    return {k: P[k] for k in ARMS_R}, y, per, None


# ==================================================================================================
# ADAPTER 3 -- WILDFIRE   per-cell calibration, 204 rows/cell, donors CLOSED AT 2018
# ==================================================================================================

def run_fire():
    import fire_architecture as FA
    import fire_evt_arch as FE
    from fire_architecture import (build_pool, complete_regions, gather, open_A,
                                   tree_columns_to)
    from coral_architecture import solve_local      # FE.route_percell imports its own; the
                                                    # expanding-window path below needs it too
    from sklearn.tree import DecisionTreeRegressor

    NPD = 40 if A_.smoke else FE.NPD
    MF, SEED, TRAIN_END, MIN_HIST = FE.MFV, FE.SEED, FE.TRAIN_END, FE.MIN_HIST
    CELLS = 40 if A_.smoke else (A_.cells or FE.CELLS)
    FA.USE_HISTORY, FA.USE_DRIVERS = 1, 1
    FA.NPD, FA.MF = NPD, MF
    FA.N_CELLS = 1000          # --cells collides with fire_architecture's pool cap; see run_fire_forecast
    INNER = TRAIN_END - 2                     # inner fit <=2016, inner score 2017-2018
    # Size of the cold-start donor block, matched to the SHIPPED history block (~81k rows) so
    # the tree-column memmap stays the same order of magnitude: at full scale ntree is 9,000,
    # so 100k rows x 9,000 x 4 B = 3.6 GB, which the shipped path already allocates. Bigger
    # would be better conditioned and would not fit.
    DONOR_ROWS_TARGET = 100000

    regs = complete_regions()
    size = pd.read_csv("D:/fire/region_sizes.csv")
    size = size[size.region.isin(regs)].sort_values("panel_cells", ascending=False)
    donors = list(size.region.head(FE.N_DONORS))
    tests = [r for r in size.region if r not in donors]
    log("  fire | %d donors | %d tests | npd %d | per-cell (204 rows/cell) | TRAIN_END %d"
        % (len(donors), len(tests), NPD, TRAIN_END))
    # The pool build streams 40 regions and GROWS as it goes -- measured 7.2 -> 1.2 GB free on the
    # smoke run, which is the level this machine has hung at twice. A guard before the call is not
    # enough; FA.wait_mem is fire's own in-loop throttle and must be armed.
    guard(5.0, "fire pool build (it grows -- 5 GB headroom, not 3)")
    FA.wait_mem(2.5, "fire pool build", max_wait_min=30)
    mm, nrows, feat, meta = build_pool()
    codes = {r: i for i, r in enumerate(regs)}
    meta["ecoid"] = meta.reg.map(codes)
    meta["year"] = (meta.t - meta.month) // 12
    meta["cell"] = (np.round(meta.lat.values.astype(np.float64), 5) * 1e5).astype(np.int64) \
        * 100000000 + (np.round(meta.lon.values.astype(np.float64), 5) * 1e5).astype(np.int64)

    # ---- DONOR WINDOW CLOSED AT TRAIN_END (user decision). The shipped run has NO year filter
    # here, so donor rows from inside the 2019-2022 test window enter calibration.
    rs = np.random.default_rng(SEED)           # inherited from the shipped design; never swept
    i_don = np.flatnonzero(meta.reg.isin(donors).values & (meta.year <= TRAIN_END).values)
    sub = meta.iloc[i_don]
    pos, neg = i_don[(sub.y > 0).values], i_don[(sub.y == 0).values]
    npos = min(len(pos), max(1, FE.MAX_TR // (1 + FE.NEG_TR)))
    pk = rs.choice(pos, npos, replace=False) if npos < len(pos) else pos
    nk = rs.choice(neg, min(len(neg), FE.NEG_TR * len(pk)), replace=False)
    keep_don = np.sort(np.concatenate([pk, nk]))
    assert int(meta.iloc[keep_don].year.max()) <= TRAIN_END, "donor window not closed"
    log("    donor window CLOSED at %d: %s rows (%d fires), max year %d"
        % (TRAIN_END, format(len(keep_don), ","), int((meta.iloc[keep_don].y > 0).sum()),
           int(meta.iloc[keep_don].year.max())))

    if A_.calib == "donor":
        # WHOLE CELLS, DETERMINISTICALLY CHOSEN. A stride over the sorted cell list, never a
        # draw: the standing rule is no seeds, and the rs.choice above is inherited from the
        # original design rather than endorsed. WHOLE cells because the ridge needs a time
        # series per cell -- the shipped row-stratified block gives ~2 rows/cell, under
        # MIN_HIST, and Tier 1 refused the run because of it.
        from coral_glorys2_ab import haversine as _hv
        _dm = meta.reg.isin(donors).values & (meta.year <= TRAIN_END).values
        _dg = meta.iloc[np.flatnonzero(_dm)].groupby("cell")
        _dall = np.array(list(_dg.groups.keys()))
        _dla = _dg.lat.first().reindex(_dall).values
        _dlo = _dg.lon.first().reindex(_dall).values
        _want = max(200, int(DONOR_ROWS_TARGET // max(1, MIN_HIST * 8)))
        # NEAREST-FIRST, ROUND-ROBIN OVER TEST CELLS. Ranking every donor by its distance to
        # the single closest test cell would spend the whole budget on one dense test region;
        # taking one donor per test cell in turn spreads it so every test region gets local
        # coverage in proportion to how many cells it has.
        _tm = meta.reg.isin(tests).values
        _tg = meta.iloc[np.flatnonzero(_tm)].groupby("cell")
        _tall = np.array(list(_tg.groups.keys()))
        _tla = _tg.lat.first().reindex(_tall).values
        _tlo = _tg.lon.first().reindex(_tall).values
        _tstep = max(1, len(_tall) // 400)          # 400 probes is plenty to cover the regions
        _order = []
        for _ti in range(0, len(_tall), _tstep):
            _order.append(np.argsort(_hv(_tla[_ti], _tlo[_ti], _dla, _dlo)))
        # DEDUP INSIDE THE LOOP. Hundreds of test cells share a nearest donor, so appending one
        # per probe and deduping afterwards collapsed 520 requested cells to 58 -- and because
        # the donor block also builds the TREE BANK, that silently cut the bank from 1,200 trees
        # over 30 regions to 360 over 9. Counting only distinct cells makes each round advance
        # to every probe's next-nearest donor, which is what round-robin was meant to do.
        _pick, _r = [], 0
        _seen = set()
        while len(_pick) < _want and _r < len(_dall):
            for _o in _order:
                if len(_pick) >= _want:
                    break
                _c = _dall[_o[_r]]
                if _c in _seen:
                    continue
                _seen.add(_c)
                _pick.append(_c)
            _r += 1
        _pick = set(_pick)
        # keep_don IS LEFT ALONE. It builds the TREE BANK and the correctors, which need the
        # shipped 30-region spread; overwriting it with the proximity selection cut the bank
        # to 9 regions and tripped fit_correctors' own-region guard at 0.910. The cold-start
        # selection belongs to the CALIBRATION block, which is i_hist, set below.
        keep_cal = np.flatnonzero(meta.reg.isin(donors).values
                                  & (meta.year <= TRAIN_END).values
                                  & meta.cell.isin(_pick).values)
        assert int(meta.iloc[keep_cal].year.max()) <= TRAIN_END, "donor window not closed"
        _rpc = float(pd.Series(meta.iloc[keep_cal].cell.values).value_counts().median())
        log("    COLD-START DONOR BLOCK: %s whole cells -> %s rows, median %.0f rows/cell"
            % (format(len(_pick), ","), format(len(keep_cal), ","), _rpc))
        log("    (the shipped row-stratified block gives ~2 rows/cell, under MIN_HIST=%d)"
            % MIN_HIST)
        _dsel = meta.iloc[keep_cal].groupby("cell")
        _sla = _dsel.lat.first().values
        _slo = _dsel.lon.first().values
        _nd = np.array([float(_hv(_tla[i], _tlo[i], _sla, _slo).min())
                        for i in range(0, len(_tall), _tstep)])
        log("    donor cells chosen NEAREST-FIRST: test cell to nearest CHOSEN donor is "
            "median %.0f km, p25 %.0f, p75 %.0f" % (np.median(_nd),
                                                    np.percentile(_nd, 25),
                                                    np.percentile(_nd, 75)))

    hi_, ti_ = [], []
    for t in tests:
        rm = (meta.reg == t).values
        cells = pd.unique(meta.cell.values[rm])
        pick = set(rs.choice(cells, min(CELLS, len(cells)), replace=False).tolist())
        sel = rm & meta.cell.isin(pick).values
        hi_.append(np.flatnonzero(sel & (meta.year <= TRAIN_END).values))
        ti_.append(np.flatnonzero(sel & (meta.year > TRAIN_END).values))
    i_hist, i_test = np.concatenate(hi_), np.concatenate(ti_)
    if A_.calib == "donor":
        # THE CALIBRATION BLOCK IS SWAPPED HERE AND NOWHERE ELSE. i_hist indexed the TEST
        # cells' own <=2018 rows; it now indexes the chosen DONOR cells instead. Everything
        # downstream reads `hist` by name -- Vh, nh, yh, tgt, clim -- so this one line carries
        # through the tree columns and the solver untouched, and the bank is unaffected
        # because it is built from keep_don, which this does not touch.
        i_hist = keep_cal
    don = gather(mm, feat, meta, keep_don)
    hist = gather(mm, feat, meta, i_hist)
    test = gather(mm, feat, meta, i_test)
    del mm
    try:
        os.remove(FA.POOL)
    except Exception:
        pass
    for f in (don, hist, test):
        f["ecoid"] = f.reg.map(codes)
        f["cell"] = (np.round(f.lat.values.astype(np.float64), 5) * 1e5).astype(np.int64) \
            * 100000000 + (np.round(f.lon.values.astype(np.float64), 5) * 1e5).astype(np.int64)
        f["year"] = (f.t - f.month) // 12
    cc = hist.groupby(["cell", "month"]).y.mean()
    cm = hist.groupby("cell").y.mean()
    for f in (hist, test):
        v = pd.Series(f.set_index(["cell", "month"]).index.map(cc), index=f.index).astype(float)
        f["clim"] = v.fillna(f.cell.map(cm)).fillna(0.0).values
    y = test.y.values.astype(np.float64)
    yh = hist.y.values.astype(np.float64)
    gmean = float(don.y.mean())
    log("    donor %s | history %s | SCORED %s rows (%d fires, %.2f%%)"
        % (format(len(don), ","), format(len(hist), ","), format(len(y), ","),
           int((y > 0).sum()), 100 * (y > 0).mean()))

    # TIER 1, MEASURED AND CHECKED. rows_per_unit is the CALIBRATION history each cell actually
    # has -- the rows its own ridge is fitted on -- not the scoring window's length.
    tier1_check(derive_tier1(yh, float(hist.groupby("cell").size().median()), "fire"), "fire")

    Vd = don[feat].fillna(0).values.astype(np.float32)
    yd = don.y.values.astype(np.float64)
    base_rows = np.arange(len(don))
    trees, inbag, home = [], [], []
    guard(3.0, "fire bank")
    for e, g in don.groupby("ecoid"):
        gi = base_rows[don.ecoid.values == e]
        n = len(gi)
        take = max(30, min(int(0.8 * n), FA.TREE_SAMPLES))
        for j in range(NPD):
            rsj = np.random.RandomState(SEED * 1000 + int(e) * 17 + j)
            idx = rsj.choice(n, size=take, replace=True)
            trees.append(DecisionTreeRegressor(max_depth=8, min_samples_leaf=5, max_features=MF,
                                               random_state=SEED * 100 + j).fit(Vd[gi][idx],
                                                                                yd[gi][idx]))
            inbag.append(gi[np.unique(idx)])
            home.append(gi)
    log("    bank %d trees / %d donors" % (len(trees), don.ecoid.nunique()))
    corr = fit_correctors(trees, inbag, home, Vd, yd, MF, placebo=False)
    plac = fit_correctors(trees, inbag, home, Vd, yd, MF, placebo=True)

    nh = len(hist)
    hidx = np.flatnonzero((hist.year <= INNER).values)
    sidx = np.flatnonzero((hist.year > INNER).values)

    def _route_cold(don_, test_, A_m, ntree, tgt_d, gm):
        """COLD START: every test cell fitted on MATCHED DONOR cells, never on its own history.

        Two stages, the same rule coral's router uses and for the same reason: geography first
        because climate is spatially autocorrelated, drivers second because two places at the same
        latitude can still be nothing alike.
            1  haversine from the test cell to every donor CELL centroid -> nearest 3*ncell
            2  of those, the `ncell` nearest in WEIGHTED driver space (--simfeat applies here too)
            3  fit the block-penalised ridge on ALL rows of those donor cells

        THE ASSERTION IS THE CLAIM. If one row from a test region reaches a pool, this is not cold
        start and the number is not what it is reported as.
        """
        from coral_glorys2_ab import haversine
        ncell = max(1, A_.donorcells)
        dc, tc = don_.cell.values, test_.cell.values
        order = np.argsort(dc, kind="stable")
        ds = dc[order]
        Cd = np.column_stack([don_[c].values for c in FE.CTX]).astype(np.float64)
        Ct = np.column_stack([test_[c].values for c in FE.CTX]).astype(np.float64)
        mu, sd = Cd.mean(0), Cd.std(0) + 1e-9
        Cd, Ct = (Cd - mu) / sd, (Ct - mu) / sd
        nd = len(don_)
        # CELL-LEVEL GEOMETRY AND DRIVER MEANS, built once. Per-row would be 315,000 x 156 distance
        # evaluations per test cell; per-cell is ~1,000.
        dcell = pd.unique(dc)
        gd = don_.groupby("cell")
        dlat = gd.lat.first().reindex(dcell).values
        dlon = gd.lon.first().reindex(dcell).values
        Zd = gd[feat].mean().reindex(dcell).values.astype(np.float64)
        zmu, zsd = Zd.mean(0), Zd.std(0) + 1e-9
        Zd = (Zd - zmu) / zsd
        wsim, wnote = sim_weights(feat, Zd, gd.y.mean().reindex(dcell).values.astype(np.float64),
                                  A_.simfeat, log)
        if A_.simfeat != "all":
            Zd = Zd * wsim
        log("    cold-start pool: %s donor cells | %s" % (format(len(dcell), ","), wnote))
        gt = test_.groupby("cell")
        out = np.full(len(test_), np.nan)
        nfit = nfall = 0
        dists = []
        for cell in pd.unique(tc):
            tsel = np.flatnonzero(tc == cell)
            g = gt.get_group(cell)
            tlat, tlon = float(g.lat.iloc[0]), float(g.lon.iloc[0])
            dkm = haversine(tlat, tlon, dlat, dlon)
            if A_.mindist > 0:
                near = dkm >= A_.mindist
                if near.sum() < ncell:
                    out[tsel] = gm
                    nfall += len(tsel)
                    continue
            else:
                near = np.ones(len(dkm), bool)
            cand = np.flatnonzero(near)
            cand = cand[np.argsort(dkm[cand])][:min(near.sum(), 3 * ncell)]
            zt = (g[feat].mean().values.astype(np.float64) - zmu) / zsd
            if A_.simfeat != "all":
                zt = zt * wsim
            pick = cand[np.argsort(np.sqrt(((Zd[cand] - zt) ** 2).sum(1)))][:ncell]
            dists.append(float(np.median(dkm[pick])))
            rows = np.concatenate([order[np.searchsorted(ds, dcell[p], "left"):
                                         np.searchsorted(ds, dcell[p], "right")] for p in pick])
            if len(rows) < MIN_HIST or not np.isfinite(tgt_d[rows]).all():
                out[tsel] = gm
                nfall += len(tsel)
                continue
            assert not don_.reg.values[rows[0]] in set(test_.reg.values), \
                "a TEST region row entered a cold-start pool"
            M = don_.clim.values[rows]
            Xc = np.column_stack([np.ones(len(rows)), M - M.mean(), Cd[rows],
                                  np.asarray(A_m[rows], np.float64)])
            b = solve_local(Xc, tgt_d[rows], np.ones(len(rows)), ntree, len(FE.CTX),
                            FA.ALPHA, FA.A_CTX)
            Xt = np.column_stack([np.ones(len(tsel)), test_.clim.values[tsel] - M.mean(),
                                  Ct[tsel], np.asarray(A_m[nd + tsel], np.float64)])
            out[tsel] = Xt @ b
            nfit += 1
        if dists:
            log("    matched donor cells: median %.0f km, p25 %.0f, p75 %.0f | %d cells fitted, "
                "%d rows fell back" % (np.median(dists), np.percentile(dists, 25),
                                       np.percentile(dists, 75), nfit, nfall))
        return out, nfit, nfall

    def percell(hist_, test_, A_m, ntree, tgt_h, tgt_t_true, gm, calib):
        """THE THREE CALIBRATION ARMS FOR FIRE. They mean the OPPOSITE of what they mean on coral.

        Coral's shipped pool ADMITS test-era neighbours, so `strict` is a RESTRICTION there.
        Fire's shipped router fits each cell's ridge on that cell's <=TRAIN_END history ONLY --
        `hist` and `test` are disjoint frames by construction -- so fire is ALREADY strict, and
        `full` / `rollout` are an EXPANSION: they let a cell predicting 2021 also calibrate on its
        own 2019-2020 rows, which a deployed model WOULD have.

            strict   delegates to FE.route_percell UNCHANGED, so it is bit-identical to the
                     shipped path and to every earlier fire number.
            full     expanding window, refit per YEAR: rows <=TRAIN_END plus this cell's own test
                     rows from earlier years, carrying their TRUE labels.
            rollout  the same rows carrying the model's OWN PREDICTIONS. No test-era label ever
                     reaches the ridge.

        REFIT GRANULARITY IS YEARLY, NOT MONTHLY, AND THAT IS A COST DECISION: monthly would be 48
        refits per cell against 4, on a 9,000-column solve, and fire already costs ~6.6 min/arm.
        Yearly captures the expanding window at ~4.5x instead of ~48x. Stated because it is a
        deliberate approximation of the arm, not a property of it.
        """
        if calib == "donor":
            return _route_cold(hist_, test_, A_m, ntree, tgt_h, gm)
        if calib == "strict":
            return FE.route_percell(hist_, test_, A_m, ntree, tgt_h, gm, MIN_HIST)
        out = np.full(len(test_), np.nan)
        fed = np.zeros(len(test_))            # rollout: what we handed forward
        hc, tc, ty = hist_.cell.values, test_.cell.values, test_.year.values
        order = np.argsort(hc, kind="stable")
        hs = hc[order]
        Ch = np.column_stack([hist_[c].values for c in FE.CTX]).astype(np.float64)
        Ct = np.column_stack([test_[c].values for c in FE.CTX]).astype(np.float64)
        mu, sd = Ch.mean(0), Ch.std(0) + 1e-9
        Ch, Ct = (Ch - mu) / sd, (Ct - mu) / sd
        nh_ = len(hist_)
        nfit = nfall = nsub = 0
        for cell in pd.unique(tc):
            lo, hi = np.searchsorted(hs, cell, "left"), np.searchsorted(hs, cell, "right")
            hix = order[lo:hi]
            tsel = np.flatnonzero(tc == cell)
            if len(hix) < MIN_HIST or not np.isfinite(tgt_h[hix]).all():
                out[tsel] = gm
                nfall += len(tsel)
                continue
            for Y in sorted(np.unique(ty[tsel])):
                now = tsel[ty[tsel] == Y]
                ext = tsel[ty[tsel] < Y]          # this cell's OWN earlier test rows
                assert (ty[ext] < Y).all(), "future row entered an expanding window"
                add = tgt_t_true[ext] if calib == "full" else fed[ext]
                nsub += len(ext) if calib == "rollout" else 0
                M = np.r_[hist_.clim.values[hix], test_.clim.values[ext]]
                Xc = np.column_stack([np.ones(len(hix) + len(ext)), M - M.mean(),
                                      np.vstack([Ch[hix], Ct[ext]]),
                                      np.vstack([np.asarray(A_m[hix], np.float64),
                                                 np.asarray(A_m[nh_ + ext], np.float64)])])
                b = solve_local(Xc, np.r_[tgt_h[hix], add], np.ones(len(hix) + len(ext)),
                                ntree, len(FE.CTX), FA.ALPHA, FA.A_CTX)
                Xt = np.column_stack([np.ones(len(now)), test_.clim.values[now] - M.mean(),
                                      Ct[now], np.asarray(A_m[nh_ + now], np.float64)])
                out[now] = Xt @ b
                if calib == "rollout":
                    # this year's prediction becomes next year's calibration row. clip, or a bad
                    # early year compounds across the 4-year horizon.
                    fed[now] = np.clip(out[now], 0.0, (np.pi / 2.0) if USE_LINK[0] else 1.0)
            nfit += 1
        if calib == "rollout":
            log("      rollout: %s calibration rows fed from PREDICTIONS" % format(nsub, ","))
        return out, nfit, nfall

    def percell_sweep(hist_, test_, A_m, ntree, tgt_h, tag):
        """FIRE'S PENALTY SWEEP. One ridge per (cell, penalty) on that cell's OWN <=TRAIN_END
        history -- the same rows FE.route_percell uses, the same columns, only ALPHA varies.

        This duplicates route_percell's body rather than calling it, because route_percell takes no
        penalty argument and reads FA.ALPHA from module state. Mutating that global would change it
        for every later caller in the process, which is exactly the class of bug that makes a run
        depend on the order its arms happen to execute in. A local copy is the cheaper risk.
        """
        # THE GRID IS (LEVEL x RATIO), AND THE RATIO IS THE POINT OF THE HONEST RUN.
        # Fire's router carries TWO penalties -- ALPHA on the tree block, A_CTX on the context block.
        # Every sweep before 2026-09-16 scaled BOTH by one multiplier, so the LEVEL was selected and
        # the 2:1 BALANCE between the blocks stayed a hand-set human constant. That is the last
        # genuine Tier-2 violation in fire's adaptation layer (MIN_HIST is inert -- 1,249 of 1,249
        # cells fit -- and --calib is pinned to strict from the command line).
        # REPARAMETERISED so the old behaviour is a POINT INSIDE the new grid:
        #     a_tree = ALPHA * mlt          a_ctx = ALPHA * mlt * rho
        # At rho = A_CTX/ALPHA = 0.5 this is identical to A_CTX * mlt, which is what the previous
        # runs did. That identity is the contract check: the (1.0, 0.5) cell MUST reproduce the arm's
        # own cached MAE, and fire_honest.py asserts it before reading anything else.
        _lev = ([float(x) for x in A_.levels.split(",")] if A_.levels else list(LAMMULT))
        _rho = ([float(x) for x in A_.ratios.split(",")] if A_.ratios
                else [float(FA.A_CTX) / float(FA.ALPHA)])
        GRID = [(m_, r_) for m_ in _lev for r_ in _rho]
        SW = np.full((len(test_), len(GRID)), np.nan)
        hc, tc = hist_.cell.values, test_.cell.values
        order = np.argsort(hc, kind="stable")
        hs = hc[order]
        Ch = np.column_stack([hist_[c].values for c in FE.CTX]).astype(np.float64)
        Ct = np.column_stack([test_[c].values for c in FE.CTX]).astype(np.float64)
        mu, sd = Ch.mean(0), Ch.std(0) + 1e-9
        Ch, Ct = (Ch - mu) / sd, (Ct - mu) / sd
        nh_ = len(hist_)
        for cell in pd.unique(tc):
            lo, hi = np.searchsorted(hs, cell, "left"), np.searchsorted(hs, cell, "right")
            hix = order[lo:hi]
            tsel = np.flatnonzero(tc == cell)
            if len(hix) < MIN_HIST or not np.isfinite(tgt_h[hix]).all():
                continue
            M = hist_.clim.values[hix]
            Xc = np.column_stack([np.ones(len(hix)), M - M.mean(), Ch[hix],
                                  np.asarray(A_m[hix], np.float64)])
            Xt = np.column_stack([np.ones(len(tsel)), test_.clim.values[tsel] - M.mean(),
                                  Ct[tsel], np.asarray(A_m[nh_ + tsel], np.float64)])
            for k, (mlt, rho) in enumerate(GRID):
                b = solve_local(Xc, tgt_h[hix], np.ones(len(hix)), ntree, len(FE.CTX),
                                FA.ALPHA * mlt, FA.ALPHA * mlt * rho)
                SW[tsel, k] = Xt @ b
        _sf = os.path.join(OUT, "_lamsweep_%s.npz" % tag)
        np.savez_compressed(_sf + ".tmp.npz",
                            y=test_.y.values.astype(np.float64), sw=SW,
                            lam=np.array([g_[0] for g_ in GRID], np.float64),
                            rho=np.array([g_[1] for g_ in GRID], np.float64),
                            cell=test_.cell.values, reg=test_.reg.values.astype(str))
        os.replace(_sf + ".tmp.npz", _sf)
        log("      lamsweep: wrote %d rows x %d cells of grid (%d levels x %d ratios)"
            % (SW.shape[0], SW.shape[1], len(_lev), len(_rho)))

    USE_LINK = [False]

    def route(cc, eta, tag, use_link=False):
        """use_link=True fits the per-cell ridge on arcsin(sqrt(y)) and inverts. Fire's SHIPPED base
        is RAW (the arcsine appears only in the hurdle's magnitude part, which this Tier-2 harness
        does not run), so `link` is a NEW arm here, as it is on defo."""
        """Columns on a DISK MEMMAP -- 9,000 cols x ~315,000 rows is 11.3 GB in RAM."""
        A, Ap = open_A(nh + len(test), len(trees), "adapt_" + tag)
        Vh = hist[feat].fillna(0).values.astype(np.float32)
        Vt = test[feat].fillna(0).values.astype(np.float32)
        for j, t in enumerate(trees):
            ph, pt = t.predict(Vh), t.predict(Vt)
            if cc is not None and cc[j] is not None:
                ph = ph + eta * cc[j].predict(Vh)
                pt = pt + eta * cc[j].predict(Vt)
            A[:nh, j] = ph.astype(np.float32)
            A[nh:, j] = pt.astype(np.float32)
        A.flush()
        tgt = LINK_G(yh) if use_link else yh
        gm = float(LINK_G(np.array([gmean]))[0]) if use_link else gmean
        USE_LINK[0] = use_link
        tt = LINK_G(y) if use_link else y          # TRUE test labels -- used ONLY by calib=full
        # THE SWEEP IS RESTRICTED BY --sweeparms BECAUSE IT IS PER-ARM AND FIRE HAS FIVE.
        # Each swept arm costs 2 surfaces x 15 penalties of per-cell solves on top of its own route.
        # The lambda question is asked of the arm the layer ADOPTED, not of every candidate, so
        # sweeping all five is 2.5x the cost for four answers nobody asked for. Default "all"
        # preserves the previous behaviour exactly.
        _sw = A_.sweeparms == "all" or tag in [t.strip() for t in A_.sweeparms.split(",")]
        if A_.lamsweep and _sw:
            # INNER surfaces (each its own fit -> score pair) AND the test surface, so the selection
            # can be made on the first and the oracle read off the second.
            # EXTRA FOLDS EXIST TO TEST WHETHER FOLD 1's CURVE SHAPE IS A PROPERTY OF THE PROBLEM OR
            # OF THAT WINDOW. Fold 1 alone showed 9 of 10 regions strictly monotone, which would make
            # pooling a no-op -- but that is one window's evidence, and Part 517 found fold2 on defo
            # to be BETTER BEHAVED than fold1 (picks clustered at 30-100 where fold1 scattered over
            # 1-1500), so a second window is not a formality. Each fold steps the cut back 2 years and
            # scores the 2 years after it; fire has 204 monthly rows per cell over 2002-2018, so fold
            # 3 still fits on 132 rows against MIN_HIST=24 and drops no cell.
            for f_ in range(int(max(A_.folds, 1))):
                cut = INNER - 2 * f_
                fi = np.flatnonzero((hist.year <= cut).values)
                si = np.flatnonzero(((hist.year > cut) & (hist.year <= cut + 2)).values)
                if len(fi) < 200 or len(si) < 100:
                    log("      [fold %d] cut %d: too few rows (%d fit / %d score) -- skipped"
                        % (f_ + 1, cut, len(fi), len(si)))
                    continue
                nm_ = "_inner" if f_ == 0 else "_inner%d" % (f_ + 1)
                log("      [fold %d] fit <=%d (%s rows) -> score %d-%d (%s rows)"
                    % (f_ + 1, cut, format(len(fi), ","), cut + 1, cut + 2, format(len(si), ",")))
                percell_sweep(hist.iloc[fi].reset_index(drop=True),
                              hist.iloc[si].reset_index(drop=True),
                              np.vstack([np.asarray(A[:nh][fi]), np.asarray(A[:nh][si])]),
                              len(trees), tgt[fi], tag + nm_)
            percell_sweep(hist, test, A, len(trees), tgt, tag + "_test")
        q, nfit, nfall = percell(hist, test, A, len(trees), tgt, tt, gm, A_.calib)
        # THE INNER (ADOPTION) SURFACE IS ALWAYS STRICT, whatever --calib says. The calib arms
        # are a leak-sensitivity study, not adoption candidates; letting the decision surface
        # expand too would make the selector's evidence depend on the thing being studied.
        qi, _, _ = FE.route_percell(hist.iloc[hidx].reset_index(drop=True),
                                    hist.iloc[sidx].reset_index(drop=True),
                                    np.vstack([np.asarray(A[:nh][hidx]),
                                               np.asarray(A[:nh][sidx])]),
                                    len(trees), tgt[hidx], gm, MIN_HIST)
        if use_link:
            q, qi = LINK_I(q), LINK_I(qi)
        del A
        try:
            os.remove(Ap)
        except Exception:
            pass
        gc.collect()
        log("    %-10s %d cells fitted, %s fell back" % (tag, nfit, format(nfall, ",")))
        return np.clip(q, 0.0, 1.0), np.clip(qi, 0.0, 1.0)

    P, IN = {}, {}
    SPEC = [("raw", None, False), ("link", None, True),
            ("raw_corrector", corr, False), ("link_corrector", corr, True),
            ("placebo", plac, False)]
    if A_.arms == "base":
        # the calibration question is about the POOL, not the tools. Fire's expanding refit costs
        # ~4.5x per arm, so routing five of them to answer a pool question is waste.
        SPEC = [s_ for s_ in SPEC if s_[0] in ("raw", "link")]
        log("    --arms=base: routing %s only (calibration study, not a tool study)"
            % ", ".join(s_[0] for s_ in SPEC))
    if A_.sweeponly:
        # ROUTE ONLY THE SWEPT ARMS. The penalty study does not need the other three, and each costs
        # 10-67 min. ADOPTION IS SUPPRESSED below for exactly the reason --arms=base suppresses it:
        # an argmin over a candidate set truncated for cost is not the layer's decision.
        keep_ = [t.strip() for t in A_.sweeparms.split(",")]
        SPEC = [s_ for s_ in SPEC if s_[0] in keep_] or SPEC
        log("    --sweeponly: routing %s only (penalty study, ADOPTION SUPPRESSED)"
            % ", ".join(s_[0] for s_ in SPEC))
    for nm, cc, lk in SPEC:
        t0 = time.time()
        P[nm], IN[nm] = route(cc, 1.0, nm, lk)
        log("    %-16s %.1f min | MAE %.6f" % (nm, (time.time() - t0) / 60, mae(y, P[nm])))
    if "raw" in P:
        P["base"], IN["base"] = P["raw"], IN["raw"]   # fire SHIPS raw -- alias, not a 6th route

    ARMS = [a for a in ["base", "link", "raw_corrector", "link_corrector", "placebo"]
            if a in P]                      # `raw` == `base` here; --arms=base drops the rest
    rows = []
    for r in pd.unique(test.reg.values):
        m = (test.reg == r).values
        mi = (hist.iloc[sidx].reg == r).values
        if m.sum() < 50 or float(np.var(y[m])) < 0.05 * float(np.var(y)):
            continue
        d = dict(y=y[m], inner_y=yh[sidx][mi])
        for k in ARMS:
            d[k] = P[k][m]
            d["inner_" + k] = IN[k][mi]
        rows.append(d)
    if "base" not in P:
        # --sweeponly skipped the arm `base` aliases, so there is no reference to difference
        # against. assemble() would raise KeyError AFTER the whole run -- which it did once, at
        # 15:12 on 2026-09-16, costing the report block of a 68-minute run (the sweep files were
        # already on disk, so nothing else was lost). Return the predictions and skip the verdict
        # table: with a truncated candidate set there is no adoption to report anyway.
        log("    --sweeponly: no `base` arm routed, so the verdict table is SKIPPED (nothing to")
        log("    difference against). The sweep caches are written and complete.")
        return P, y, {}, None
    _, _, per, dec = assemble(rows, ARMS)
    if A_.arms == "base":
        # --arms=base drops the corrector and placebo arms FOR COST, to answer a calibration-pool
        # question. The layer would still happily argmin over what is left and print
        # "TYPE 2 adaptation -> link", and that number would look like fire's tool decision while
        # having been chosen from 2 candidates instead of 5. A decision over a candidate set that
        # was truncated for convenience is not the layer's decision. Same rule that makes the
        # placebo a CONTROL and coral's missing surface a NO ADOPTION: if the evidence is not the
        # real evidence, do not print a verdict.
        log("    --arms=base: ADOPTION SUPPRESSED. The candidate set was truncated for cost, so")
        log("    any argmin over it is not the adaptation layer's choice. Run without --arms to")
        log("    get fire's real Type 2 decision.")
        dec = None
    log("  per-unit verdicts use %d of %d regions; the table is the FULL test set."
        % (len(rows), len(pd.unique(test.reg.values))))
    return {k: P[k] for k in ARMS}, y, per, dec


# ==================================================================================================
# ADAPTER 3F -- WILDFIRE, FORECAST.  Lead 1 = one month ahead on the monthly panel.
# ==================================================================================================

def run_fire_forecast():
    """Fire at lead LEAD months, four arms, one row set.

    THE POOL IS BUILT ONCE, UNLAGGED, AND THE LAG IS AN INDEX REMAP. fire_architecture has its own
    --lag, which shifts the columns inside load() and drops the orphaned months. Using it would mean
    streaming all 40 regions TWICE -- the expensive half of the run -- and, worse, it would produce
    two pools with different row counts that then have to be re-aligned by key, which is the
    alignment problem this harness exists to avoid. Instead the pool is built once and complete, and
    each row's predecessor is located by (cell, t-LEAD). The lagged feature frame is then the SAME
    memmap gathered at the predecessor positions. Exact, one pass, and the alignment is an identity
    rather than a join.

    NOT EVERY COLUMN MOVES. fire_architecture.NOLAG_PREFIX names the blocks that are already <= t-1
    by construction -- time-since-last-fire, burn counts, burn rate, last burn, NBR -- and a
    forecaster issuing at the end of month t-1 has all of them. They are copied back from the target
    row, exactly as fire's own --lag does. So does `clim`, the cell-month burn climatology, which is
    built from <= TRAIN_END targets, and so does the context block (month, lat): both are known
    arbitrarily far ahead. THE CONSEQUENCE IS THAT THE ROUTER'S CONTEXT BLOCK IS IDENTICAL ACROSS
    ALL FOUR ARMS and the only thing that differs is the tree block, which is what makes the
    comparison a clean one.

    THE TOOL IS `link_corrector`, the arm fire's nowcast layer ADOPTED (MAE 0.003993 against base
    0.007027, Part 520).
    """
    import fire_architecture as FA
    import fire_evt_arch as FE
    import forecast_arms as F
    from fire_architecture import build_pool, complete_regions, gather, open_A
    from sklearn.tree import DecisionTreeRegressor

    NPD = 40 if A_.smoke else FE.NPD
    MF, SEED, TRAIN_END, MIN_HIST = FE.MFV, FE.SEED, FE.TRAIN_END, FE.MIN_HIST
    CELLS = 40 if A_.smoke else (A_.cells or FE.CELLS)
    FA.USE_HISTORY, FA.USE_DRIVERS = 1, 1
    FA.NPD, FA.MF = NPD, MF
    # --cells IS A NAME COLLISION AND IT IS SILENT. fire_architecture parses the SAME flag off
    # sys.argv for a DIFFERENT quantity: N_CELLS = _num("--cells", 1000) caps cells per region in
    # the POOL, while this adapter's --cells caps TEST cells per region. Passing --cells=300 would
    # therefore also shrink the pool from 1,000 to 300 cells per region -- a third of the donor
    # panel -- and nothing would report it. Pin it back after import.
    FA.N_CELLS = 1000
    INNER, LEAD = TRAIN_END - 2, A_.lead      # LEAD is in MONTHS; prev_index takes it directly
    if FA.USE_LAG:
        raise SystemExit("fire_architecture was imported with --lag=%d. The forecast adapter does "
                         "its own lagging on an UNLAGGED pool; a pre-lagged pool would be shifted "
                         "twice. Drop --lag from the command line." % FA.USE_LAG)
    F.banner("fire", LEAD, log)

    want = [a.strip() for a in A_.fcarms.split(",") if a.strip()]
    ARMS = [a for a in F.FCARMS if a in want]
    if "nowref" not in ARMS:
        raise SystemExit("`nowref` is the reference every other arm is differenced against.")

    regs = complete_regions()
    size = pd.read_csv("D:/fire/region_sizes.csv")
    size = size[size.region.isin(regs)].sort_values("panel_cells", ascending=False)
    donors = list(size.region.head(FE.N_DONORS))
    tests = [r for r in size.region if r not in donors]
    log("  fire | %d donors | %d tests | npd %d | per-cell | TRAIN_END %d" %
        (len(donors), len(tests), NPD, TRAIN_END))
    guard(5.0, "fire pool build (it grows -- 5 GB headroom, not 3)")
    FA.wait_mem(2.5, "fire pool build", max_wait_min=30)
    mm, nrows, feat, meta = build_pool()
    codes = {r: i for i, r in enumerate(regs)}
    meta["ecoid"] = meta.reg.map(codes)
    meta["year"] = (meta.t - meta.month) // 12
    meta["cell"] = (np.round(meta.lat.values.astype(np.float64), 5) * 1e5).astype(np.int64) \
        * 100000000 + (np.round(meta.lon.values.astype(np.float64), 5) * 1e5).astype(np.int64)

    pv = F.prev_index(meta.cell.values, meta.t.values, LEAD)
    # SAY WHICH CAUSE, DO NOT ASSERT ONE. A complete panel loses exactly LEAD rows per cell -- the
    # first month has no predecessor. Anything ABOVE that is a HOLE: a (cell, month) the panel does
    # not carry, so the month after it has no t-1 either. The first version of this line claimed
    # "one per cell, plus any panel hole" without measuring the split, and the fire panel turned out
    # to drop about 2.7x the per-cell floor. That does not bias the comparison -- every arm, nowref
    # included, is scored on the SAME surviving rows -- but it is a property of the data worth
    # knowing rather than a number worth glossing.
    # A DUPLICATE (cell, t) WOULD BE THE SERIOUS CASE AND IT IS CHECKED, NOT ASSUMED. The cell key
    # is built from rounded lat/lon, so if two regions overlap geographically the same key appears
    # twice at the same month. prev_index survives that safely -- the second row sees step 0, fails
    # the `step == lead` test and is dropped rather than mispaired -- but it would mean a cell's
    # history is being assembled across two regions, which is a region-blocking question and not a
    # row-count one. Fire's nowcast run never had to ask, because it never looked backwards.
    # Counted from a sort, not from a set of 9.9M python tuples -- the obvious
    # pd.unique(zip(...)) form allocates roughly a gigabyte of tuple objects on this pool, on a
    # machine that is already at its memory ceiling during the pool build.
    _o = np.lexsort((meta.t.values, meta.cell.values))
    _c, _t = meta.cell.values[_o], meta.t.values[_o]
    _dup = int(((_c[1:] == _c[:-1]) & (_t[1:] == _t[:-1])).sum())
    del _o, _c, _t
    if _dup:
        raise SystemExit(
            "%s duplicate (cell, t) rows in the fire pool. The cell key is rounded lat/lon, so "
            "this means two regions carry the same cell and its lagged history would be assembled "
            "across a region boundary. Resolve the overlap before running a forecast arm; the "
            "nowcast path never had to ask because it never looks backwards." % format(_dup, ","))
    _ncell = int(pd.unique(meta.cell.values).size)
    _drop = int((pv < 0).sum())
    _floor = _ncell * LEAD
    log("    predecessor map: %s of %s pool rows have a t-%d row in the same cell; %s dropped"
        % (format(int((pv >= 0).sum()), ","), format(len(meta), ","), LEAD, format(_drop, ",")))
    log("      %s cells x lead %d = %s unavoidable (each cell's first month); the remaining %s are"
        % (format(_ncell, ","), LEAD, format(_floor, ","), format(_drop - _floor, ",")))
    log("      PANEL HOLES -- months the panel does not carry, whose successor loses its t-1. %s"
        % ("none" if _drop == _floor else
           "%.2f%% of rows, %.2fx the floor." % (100.0 * (_drop - _floor) / len(meta),
                                                 _drop / max(_floor, 1))))
    log("      Every arm including nowref is scored on the SAME survivors, so this costs rows, not")
    log("      fairness.")

    # THE DONOR DRAW MUST CONSUME THE RNG EXACTLY AS run_fire DOES, OR THE TEST CELLS MOVE.
    # The first version filtered i_don by (pv >= 0) BEFORE the pos/neg draw. That changes the SIZE
    # of `pos` and `neg`, so rs.choice consumes a different amount of generator state, so the
    # rs.choice(cells, ...) in the test loop below lands on a DIFFERENT 1,250 cells -- and fire's
    # forecast run scored 59,917 rows against the nowcast run's 59,892, with 907 fires against 913
    # and a mean target 1.06% apart. Nothing inside the forecast run was wrong (all four arms shared
    # rows), but fire's nowcast and forecast numbers were not comparable to each other, which is
    # precisely the pairing the study exists to make.
    # THE FIX IS TO FILTER AFTER, NOT BEFORE: draw from the same population run_fire draws from, then
    # drop the drawn rows that have no predecessor. The rng is then in the same state at the test
    # loop, the test cells match, and the only difference is the handful of donor rows the lag
    # cannot serve. run_fire is NOT touched, so every cached nowcast number stays valid.
    rs = np.random.default_rng(SEED)
    i_don = np.flatnonzero(meta.reg.isin(donors).values & (meta.year <= TRAIN_END).values)
    sub = meta.iloc[i_don]
    pos, neg = i_don[(sub.y > 0).values], i_don[(sub.y == 0).values]
    npos = min(len(pos), max(1, FE.MAX_TR // (1 + FE.NEG_TR)))
    pk = rs.choice(pos, npos, replace=False) if npos < len(pos) else pos
    nk = rs.choice(neg, min(len(neg), FE.NEG_TR * len(pk)), replace=False)
    keep_don = np.sort(np.concatenate([pk, nk]))
    _nd0 = len(keep_don)
    keep_don = keep_don[pv[keep_don] >= 0]           # drop AFTER the draw, never before
    log("    donor rows the lag cannot serve: %s of %s (%.2f%%) dropped after the draw"
        % (format(_nd0 - len(keep_don), ","), format(_nd0, ","),
           100.0 * (_nd0 - len(keep_don)) / max(_nd0, 1)))
    assert int(meta.iloc[keep_don].year.max()) <= TRAIN_END, "donor window not closed"
    assert int(meta.iloc[pv[keep_don]].year.max()) <= TRAIN_END, "a PREDECESSOR reopened the window"
    log("    donor window CLOSED at %d: %s rows (%d fires)"
        % (TRAIN_END, format(len(keep_don), ","), int((meta.iloc[keep_don].y > 0).sum())))

    hi_, ti_ = [], []
    for t in tests:
        rm = (meta.reg == t).values
        cells = pd.unique(meta.cell.values[rm])
        pick = set(rs.choice(cells, min(CELLS, len(cells)), replace=False).tolist())
        sel = rm & meta.cell.isin(pick).values & (pv >= 0)
        hi_.append(np.flatnonzero(sel & (meta.year <= TRAIN_END).values))
        ti_.append(np.flatnonzero(sel & (meta.year > TRAIN_END).values))
    i_hist, i_test = np.concatenate(hi_), np.concatenate(ti_)

    def at(idx):
        """gather() at ARBITRARY positions, preserving the caller's order.

        gather sorts its index -- deliberately, because the pool is on a mechanical drive and a
        scattered read never finishes. That sort is invisible when the caller's index is already
        ascending, which every existing caller's is, and CATASTROPHIC here: the predecessor
        positions are not monotone in the target positions, so gathering them sorted would pair
        each target row with some other row's history. Sort, gather, then invert."""
        idx = np.asarray(idx)
        o = np.argsort(idx, kind="stable")
        Fr = gather(mm, feat, meta, idx[o])
        inv = np.empty(len(o), np.int64)
        inv[o] = np.arange(len(o))
        return Fr.iloc[inv].reset_index(drop=True)

    NOLAG = [c for c in feat if c.startswith(FA.NOLAG_PREFIX)]
    log("    %d of %d feature columns shift; %d are fire-history (%s)"
        % (len(feat) - len(NOLAG), len(feat), len(NOLAG), ", ".join(FA.NOLAG_PREFIX)))
    if LEAD == 1:
        log("    and are taken from the TARGET row -- at lead 1 that history is complete at issue")
        log("    time, which is exactly what fire_architecture's own --lag does")
    else:
        log("    and at LEAD %d they are taken from the PREDECESSOR row, NOT the target: the history"
            % LEAD)
        log("    as of month t depends on months t-%d..t-1 that a forecaster issuing at t-%d has not"
            % (LEAD - 1, LEAD))
        log("    seen. Copying it forward would be a leak.")

    def pair(idx):
        """(nowcast frame, lagged frame) for one row set, aligned row for row."""
        fn = at(idx)
        fl = at(pv[idx])
        # ---- THE NOLAG BLOCK IS ONLY SAFE TO TAKE FROM THE TARGET ROW AT LEAD 1. This is a LEAK at
        # every longer lead and it would have run on three of tonight's four fire stages.
        # tslf, n_burns, burn_rate, last_burn and nbr describe the fire HISTORY as of month t --
        # each is determined entirely by fires STRICTLY BEFORE t. At lead 1 the forecast is issued at
        # the end of t-1, so that history is complete and in hand: taking it from the target row is
        # correct, and it is exactly what fire_architecture's own --lag does (it excludes
        # NOLAG_PREFIX from the shift).
        # AT LEAD 3 THE FORECAST IS ISSUED AT THE END OF t-3, and `time since last fire at month t`
        # depends on whether anything burned in t-2 and t-1 -- months the forecaster has not seen.
        # Copying it forward hands the model a partial answer to its own question on a target whose
        # base rate is 1.5%. The fix is to leave the PREDECESSOR's own values in place, which are
        # the history as of t-LEAD: exactly what is known at issue time.
        if LEAD == 1:
            fl[NOLAG] = fn[NOLAG].values
        for c in ("reg", "lat", "lon", "t", "month", "y"):
            fl[c] = fn[c].values                          # keys and TARGET belong to the target row
        for f_ in (fn, fl):
            f_["ecoid"] = f_.reg.map(codes)
            f_["cell"] = (np.round(f_.lat.values.astype(np.float64), 5) * 1e5).astype(np.int64) \
                * 100000000 + (np.round(f_.lon.values.astype(np.float64), 5) * 1e5).astype(np.int64)
            f_["year"] = (f_.t - f_.month) // 12
        return fn, fl

    don_n, don_l = pair(keep_don)
    hist_n, hist_l = pair(i_hist)
    test_n, test_l = pair(i_test)
    del mm
    try:
        os.remove(FA.POOL)
    except Exception:
        pass
    gc.collect()
    # CONTRACT: a lagged row's drivers must be its own cell's previous month. Checked on the frames
    # that were actually built, not on the index that built them.
    _c = pd.Series(meta.t.values[pv[i_test]] - meta.t.values[i_test]).unique()
    assert list(_c) == [-LEAD], "the lagged test frame is not exactly %d month(s) behind" % LEAD

    cc = hist_n.groupby(["cell", "month"]).y.mean()
    cm = hist_n.groupby("cell").y.mean()
    for f_ in (hist_n, hist_l, test_n, test_l):
        v = pd.Series(f_.set_index(["cell", "month"]).index.map(cc), index=f_.index).astype(float)
        f_["clim"] = v.fillna(f_.cell.map(cm)).fillna(0.0).values
    y = test_n.y.values.astype(np.float64)
    yh = hist_n.y.values.astype(np.float64)
    gmean = float(don_n.y.mean())
    log("    donor %s | history %s | SCORED %s rows (%d fires, %.2f%%)"
        % (format(len(don_n), ","), format(len(hist_n), ","), format(len(y), ","),
           int((y > 0).sum()), 100 * (y > 0).mean()))

    def bank(dfr):
        V = dfr[feat].fillna(0).values.astype(np.float32)
        yd = dfr.y.values.astype(np.float64)
        base_rows = np.arange(len(dfr))
        trees, inbag, home = [], [], []
        for e in sorted(pd.unique(dfr.ecoid.values)):   # groupby order, as run_fire uses
            gi = base_rows[dfr.ecoid.values == e]
            n = len(gi)
            take = max(30, min(int(0.8 * n), FA.TREE_SAMPLES))
            for j in range(NPD):
                rsj = np.random.RandomState(SEED * 1000 + int(e) * 17 + j)
                idx = rsj.choice(n, size=take, replace=True)
                trees.append(DecisionTreeRegressor(max_depth=8, min_samples_leaf=5,
                                                   max_features=MF,
                                                   random_state=SEED * 100 + j)
                             .fit(V[gi][idx], yd[gi][idx]))
                inbag.append(gi[np.unique(idx)])
                home.append(gi)
        return trees, fit_correctors(trees, inbag, home, V, yd, MF, placebo=False)

    guard(3.0, "fire forecast banks")
    BK = {"now": bank(don_n)}
    log("    nowcast bank %d trees" % len(BK["now"][0]))
    if set(ARMS) & {"lagtrain", "both"}:
        BK["lag"] = bank(don_l)
        log("    lag-%dmo bank %d trees" % (LEAD, len(BK["lag"][0])))

    nh, nt = len(hist_n), len(test_n)
    hidx = np.flatnonzero((hist_n.year <= INNER).values)
    sidx = np.flatnonzero((hist_n.year > INNER).values)
    FRAME = {"now": (hist_n, test_n), "lag": (hist_l, test_l)}
    SRC = {"nowref": [("now", "now")], "lagtrain": [("lag", "lag")],
           "lagroute": [("now", "lag")], "both": [("lag", "lag"), ("now", "lag")]}

    def fill(A, off, bk, fr):
        """One bank's columns, written into A starting at column `off`. The tool is
        link_corrector: every tree's prediction carries its own OOB-fitted corrector."""
        trees, corr = BK[bk]
        hf, tf = FRAME[fr]
        Vh = hf[feat].fillna(0).values.astype(np.float32)
        Vt = tf[feat].fillna(0).values.astype(np.float32)
        for j, t in enumerate(trees):
            ph, pt = t.predict(Vh), t.predict(Vt)
            if corr[j] is not None:
                ph = ph + corr[j].predict(Vh)
                pt = pt + corr[j].predict(Vt)
            A[:nh, off + j] = ph.astype(np.float32)
            A[nh:, off + j] = pt.astype(np.float32)
        return len(trees)

    def percell_fc(hist_, test_, A_m, ntree, tgt_h, tgt_t_true, gm_, calib):
        """FIRE'S THREE CALIBRATION POOLS, FOR THE FORECAST ADAPTER.

        THIS EXISTED NOWHERE AND ITS ABSENCE WAS SILENT. run_fire_forecast called FE.route_percell
        unconditionally and never read A_.calib at all, so --calib=rollout produced STRICT numbers
        in a directory named rollout. Three planned stages would have been mislabelled duplicates of
        three others, with nothing crashing and nothing looking wrong. On fire `strict` is the
        SHIPPED behaviour and full/rollout are an EXPANSION -- the opposite of what the same flag
        means on coral -- which is precisely why it cannot be left to a default.

            strict   delegates to FE.route_percell UNCHANGED, so it stays bit-identical to the
                     shipped path and to every earlier fire number.
            full     expanding window, refit per YEAR: this cell's <=TRAIN_END rows plus its own
                     earlier test rows carrying their TRUE labels.
            rollout  the same rows carrying the model's OWN PREDICTIONS, so no test-era label ever
                     reaches the ridge.

        A FAITHFUL COPY of run_fire's percell rather than a call into it: that one is a closure over
        run_fire's locals, and hoisting it would touch the code path every cached fire nowcast number
        came from. Duplication is the cheaper risk here, and the two are checked against each other
        by the `strict` branch, which both delegate to.
        REFIT GRANULARITY IS YEARLY, a deliberate approximation -- monthly would be 48 refits per
        cell against 4 on a 9,000-column solve.
        """
        if calib == "strict":
            return FE.route_percell(hist_, test_, A_m, ntree, tgt_h, gm_, MIN_HIST)
        out_ = np.full(len(test_), np.nan)
        fed = np.zeros(len(test_))
        hc, tc, ty = hist_.cell.values, test_.cell.values, test_.year.values
        order = np.argsort(hc, kind="stable")
        hs = hc[order]
        Ch = np.column_stack([hist_[c].values for c in FE.CTX]).astype(np.float64)
        Ct = np.column_stack([test_[c].values for c in FE.CTX]).astype(np.float64)
        mu, sd = Ch.mean(0), Ch.std(0) + 1e-9
        Ch, Ct = (Ch - mu) / sd, (Ct - mu) / sd
        nh_ = len(hist_)
        nfit_ = nfall_ = nsub = 0
        for cell in pd.unique(tc):
            lo, hi = np.searchsorted(hs, cell, "left"), np.searchsorted(hs, cell, "right")
            hix = order[lo:hi]
            tsel = np.flatnonzero(tc == cell)
            if len(hix) < MIN_HIST or not np.isfinite(tgt_h[hix]).all():
                out_[tsel] = gm_
                nfall_ += len(tsel)
                continue
            for Y in sorted(np.unique(ty[tsel])):
                now = tsel[ty[tsel] == Y]
                ext = tsel[ty[tsel] < Y]          # this cell's OWN earlier test rows
                assert (ty[ext] < Y).all(), "future row entered an expanding window"
                add = tgt_t_true[ext] if calib == "full" else fed[ext]
                nsub += len(ext) if calib == "rollout" else 0
                M = np.r_[hist_.clim.values[hix], test_.clim.values[ext]]
                Xc = np.column_stack([np.ones(len(hix) + len(ext)), M - M.mean(),
                                      np.vstack([Ch[hix], Ct[ext]]),
                                      np.vstack([np.asarray(A_m[hix], np.float64),
                                                 np.asarray(A_m[nh_ + ext], np.float64)])])
                b = solve_local(Xc, np.r_[tgt_h[hix], add], np.ones(len(hix) + len(ext)),
                                ntree, len(FE.CTX), FA.ALPHA, FA.A_CTX)
                Xt = np.column_stack([np.ones(len(now)), test_.clim.values[now] - M.mean(),
                                      Ct[now], np.asarray(A_m[nh_ + now], np.float64)])
                out_[now] = Xt @ b
                if calib == "rollout":
                    # THE LINK IS ALWAYS ON in this adapter -- the pinned tool is link_corrector, so
                    # the ridge is fitted on arcsin(sqrt(y)) and the legal range is [0, pi/2]. Clip,
                    # or one bad early year compounds across the horizon.
                    fed[now] = np.clip(out_[now], 0.0, np.pi / 2.0)
            nfit_ += 1
        if calib == "rollout":
            log("      rollout: %s calibration rows fed from PREDICTIONS" % format(nsub, ","))
        return out_, nfit_, nfall_

    P, IN = {}, {}
    # ---- PER-ARM CHECKPOINTS. A fire stage costs ~70 min and used to have no intermediate state at
    # all, so a crash or a refused memory guard in the last arm discarded the pool build, both banks
    # and every completed route. Each arm is now written the moment it is routed, and reloaded on a
    # restart. The row count is stored with it: an arm cached from a run whose test set differed --
    # a different cell sample, a different lead -- must be REJECTED, not reused, which is the same
    # rule the per-region defo caches follow.
    def arm_path(nm_):
        return os.path.join(OUT, "_arm_%s.npz" % nm_)

    def arm_load(nm_):
        f_ = arm_path(nm_)
        if not os.path.exists(f_):
            return None
        try:
            z_ = np.load(f_)
            if len(z_["p"]) != len(y) or len(z_["i"]) != len(sidx):
                log("    [stale] %s cached on %d/%d rows, this run has %d/%d -- recomputing"
                    % (nm_, len(z_["p"]), len(z_["i"]), len(y), len(sidx)))
                return None
            return z_["p"], z_["i"]
        except Exception as e_:
            log("    [corrupt] %s (%s) -- recomputing" % (nm_, e_))
            return None

    def arm_save(nm_, p_, i_):
        f_ = arm_path(nm_)
        np.savez_compressed(f_ + ".tmp.npz", p=p_, i=i_)
        os.replace(f_ + ".tmp.npz", f_)

    tgt = LINK_G(yh)                       # fire's adopted arm fits the ridge on arcsin(sqrt(y))
    tt = LINK_G(y)                         # TRUE test labels -- read ONLY by calib=full
    gm = float(LINK_G(np.array([gmean]))[0])
    log("    CALIBRATION POOL: --calib=%s  (on fire, `strict` is the SHIPPED router; full and"
        % A_.calib)
    log("    rollout EXPAND it. The same flag RESTRICTS on coral -- opposite meanings.)")
    for nm in ARMS:
        t0 = time.time()
        _c = arm_load(nm)
        if _c is not None:
            P[nm], IN[nm] = _c
            log("    %-10s [cached] MAE %.6f" % (nm, mae(y, P[nm])))
            continue
        spec = SRC[nm]
        width = sum(len(BK[b][0]) for b, _ in spec)
        A, Ap = open_A(nh + nt, width, "fc_%s" % nm)
        off = 0
        for b, fr in spec:
            off += fill(A, off, b, fr)
        A.flush()
        # THE ROUTER'S CONTEXT AND HISTORY FRAMES ARE ALWAYS THE TARGET-ROW ONES. clim and CTX
        # (month, lat) are known at issue time, so using the nowcast frame for them is not a leak;
        # holding them fixed is what makes the tree block the only thing that varies between arms.
        q, nfit, nfall = percell_fc(hist_n, test_n, A, width, tgt, tt, gm, A_.calib)
        # THE INNER SURFACE GOES TO DISK TOO, IN BLOCKS. run_fire builds it as
        # np.vstack([np.asarray(A[:nh][hidx]), np.asarray(A[:nh][sidx])]) -- a fancy-index on a
        # memmap, which materialises the WHOLE history in RAM. At the nowcast width that is 255,000
        # x 9,000 float16 = 4.6 GB and it has survived; at arm C's doubled width it is 9.2 GB on a
        # machine with 15.8 GB total that this script has already taken down twice. The router only
        # ever touches these rows a cell at a time, so there is no reason for them to be resident:
        # copy in 20,000-row blocks into a second memmap and hand route_percell that.
        Ai, Aip = open_A(nh, width, "fc_%s_inner" % nm)
        o_ = np.concatenate([hidx, sidx])
        for a0 in range(0, len(o_), 20000):
            s_ = o_[a0:a0 + 20000]
            Ai[a0:a0 + len(s_)] = A[s_]
        Ai.flush()
        qi, _, _ = FE.route_percell(hist_n.iloc[hidx].reset_index(drop=True),
                                    hist_n.iloc[sidx].reset_index(drop=True),
                                    Ai, width, tgt[hidx], gm, MIN_HIST)
        del Ai
        try:
            os.remove(Aip)
        except Exception:
            pass
        P[nm] = np.clip(LINK_I(q), 0.0, 1.0)
        IN[nm] = np.clip(LINK_I(qi), 0.0, 1.0)
        arm_save(nm, P[nm], IN[nm])
        del A
        try:
            os.remove(Ap)
        except Exception:
            pass
        gc.collect()
        log("    %-10s %5d cols | %d cells fitted, %s fell back | %.1f min | MAE %.6f"
            % (nm, width, nfit, format(nfall, ","), (time.time() - t0) / 60, mae(y, P[nm])))
    P["base"], IN["base"] = P["nowref"], IN["nowref"]
    ARMS_R = ["base"] + [a for a in ARMS if a != "nowref"]
    log("  `base` IS `nowref` -- the nowcast REFERENCE on the rows the lag leaves. Each delta is")
    log("  the cost of the lead. The INNER surface (fit <=%d, score %d-%d) is the decision"
        % (INNER, INNER + 1, TRAIN_END))
    log("  surface, and it never opens a test-window row -- the same rule as fire's nowcast run.")

    rows = []
    for r in pd.unique(test_n.reg.values):
        m = (test_n.reg == r).values
        mi = (hist_n.iloc[sidx].reg == r).values
        if m.sum() < 50 or float(np.var(y[m])) < 0.05 * float(np.var(y)):
            continue
        d = dict(y=y[m], inner_y=yh[sidx][mi])
        for k in ARMS_R:
            d[k] = P[k][m]
            d["inner_" + k] = IN[k][mi]
        rows.append(d)
    _, _, per, dec = assemble(rows, ARMS_R)
    log("  per-unit verdicts use %d of %d regions; the table is the FULL test set."
        % (len(rows), len(pd.unique(test_n.reg.values))))
    return {k: P[k] for k in ARMS_R}, y, per, dec


def main():
    log("=" * 100)
    log("ADAPTATION | %s | split %s | decide %s | EVT %s%s"
        % (A_.problem, A_.split, A_.decide, "on" if A_.evt else "off", " | SMOKE" if A_.smoke else ""))
    log("  ADOPTION: argmin MAE over the candidate set. Base is a candidate, so it can DECLINE.")
    log("  The choice is GLOBAL and never sees a test-window row. Verdicts are reported, not used.")
    if A_.evt:
        log("  NOTE: the EVT arm needs a K=5 DONOR-FOLD table (a bank rebuild per fold). It is NOT")
        log("  wired in this version -- the candidate set is {base, corrector}. Run with --evt=0 to")
        log("  silence this. Building it on test rows would be selection on the evaluation window.")
    if A_.lead:
        # --fold IS NOW HONOURED ON CORAL'S FORECAST PATH and refused on the other two, which still
        # do not implement a hold-out. A flag that is ignored must fail rather than pass quietly:
        # before this check existed, `--fold=0..4 --lead=1` renamed the output directory and scored
        # the ordinary TEST set, producing five bit-identical "folds" per lead.
        if A_.fold >= 0 and A_.problem != "coral":
            raise SystemExit(
                "REFUSING: --fold=%d with --lead=%d on %s. The donor-fold hold-out is implemented "
                "for coral only; on this problem --fold would rename the output directory while "
                "scoring the ordinary TEST set, which is a silent no-op."
                % (A_.fold, A_.lead, A_.problem))
        fn = {"defo": run_defo_forecast, "coral": run_coral_forecast,
              "fire": run_fire_forecast}[A_.problem]
    else:
        fn = {"defo": run_defo, "coral": run_coral, "fire": run_fire}[A_.problem]
    P, y, per, dec = fn()
    report(A_.problem, P, y, per, dec)


if __name__ == "__main__":
    main()
