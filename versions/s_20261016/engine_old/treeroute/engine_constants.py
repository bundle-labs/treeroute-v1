"""Engine constants: every fixed number the rules use, each with an id, a value and a test-exposed flag.

Frozen and hashed with the engine (runs/fingerprint.py hashes this file like every engine module).
Changing any value is an engine version change: every package re-runs.

Where a value came from is written in a COMMENT next to it, never in a string, so the G-NONAMES scan
(tests/test_nonames.py) can check that no string, identifier or literal names a problem.

Status of each constant:
  cited     the plan or an owner ruling cites the value's origin (plan Section 3.1 table, C1-C14,
            C16, C17, C18 (the last-value maximum, owner ruling J2 d), and C15's two group
            thresholds, which restate the signed D44; OWNER_RULINGS_*.md)
  proposed  a threshold without a cited origin; the owner signs it (plan 3.1 C15, 9.1 item 2f)
  extra     a number named in a plan Section 1, 2 or 5 rule but missing from the 3.1 table; the
            owner confirms it belongs here
  unset     the value is not fixed yet; reading it raises UnsetConstantError

Access: the module-level names (for example ``TREES_PER_GROUP``) hold the values; ``get(cid)`` reads
by id and refuses unset constants; ``table()`` gives the rows the run manifest records.

Leave one region out (owner rulings D and E): there is no donor or test set. Every group trains its own
trees and is tested, so the constants that counted donor or test groups are restated per group (C8,
C13 smoke, C15), and C16 (the scored-unit budget) and C17 (the rival region folds) are new. Two old
module-level names stay as ALIASES of the renamed constants (TREES_PER_DONOR, SMOKE_TREES_PER_DONOR),
because fit/bank.py and the legacy harness still import them; they are not registered twice.
"""

import hashlib
import json
from typing import Any, Dict, List, NamedTuple, Tuple

from treeroute.errors import UnsetConstantError

STATUSES = ("cited", "proposed", "extra", "unset")


class _Unset(object):
    """Marker for a constant whose value is not fixed yet. Any use of it fails loudly."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "UNSET"

    def _refuse(self, *args, **kwargs):
        raise UnsetConstantError("an engine constant whose value is not fixed yet was used")

    # Comparisons and hashing refuse too: 'tol == 0' must not quietly give False.
    __bool__ = __float__ = __int__ = __index__ = __complex__ = __round__ = _refuse
    __add__ = __radd__ = __sub__ = __rsub__ = __mul__ = __rmul__ = _refuse
    __truediv__ = __rtruediv__ = __floordiv__ = __rfloordiv__ = __mod__ = __rmod__ = _refuse
    __pow__ = __rpow__ = __neg__ = __pos__ = __abs__ = _refuse
    __lt__ = __le__ = __gt__ = __ge__ = __eq__ = __ne__ = __hash__ = _refuse


UNSET = _Unset()


class Constant(NamedTuple):
    id: str
    value: Any
    test_exposed: bool
    status: str


_REGISTRY: Dict[str, Constant] = {}
_IMMUTABLE = (int, float, str, bool, type(None), _Unset)


def _frozen(value):
    if isinstance(value, tuple):
        return all(_frozen(v) for v in value)
    return isinstance(value, _IMMUTABLE)


def _c(cid, value, test_exposed=False, status="cited"):
    """Register one constant and return its value (for the module-level name)."""
    if cid in _REGISTRY:
        raise ValueError("duplicate engine constant id %r" % cid)
    if status not in STATUSES:
        raise ValueError("constant %r: unknown status %r" % (cid, status))
    if (value is UNSET) != (status == "unset"):
        raise ValueError("constant %r: status 'unset' and the UNSET value go together" % cid)
    if not _frozen(value):
        raise ValueError("constant %r: value must be immutable (number, string, bool, tuple)" % cid)
    _REGISTRY[cid] = Constant(cid, value, bool(test_exposed), status)
    return value


# ---------------------------------------------------------------------------------------------------
# C1 Test window (R5)
# origin: the last 4 years of coverage, as the shipped runs use (plan 3.1 C1; fire per Q10 a;
# NDVI per Q40 a)
TEST_YEARS = _c("C1.test_years", 4)
TEST_YEARS_SHORT_RECORD = _c("C1.test_years_short_record", 3)  # R5 short-record ladder

# C2 Inner score window (R7); inner fit length floor (R5)
# origin: pm25_adaptation.py:141-142 (INNER = 2016 -> score 2017-19); adaptation.py:1214
INNER_SCORE_YEARS = _c("C2.inner_score_years", 3)
INNER_SCORE_YEARS_SHORT_RECORD = _c("C2.inner_score_years_short_record", 2)  # R5 ladder
INNER_FIT_MIN_YEARS = _c("C2.inner_fit_min_years", 1)  # R5: "4 test + 3 inner score + 1 inner fit"

# C3 Coverage end (R3)
# origin: plan 3.1 C3, "robust to a few late groups"; under LORO the share is of ALL groups (every group
# is tested; owner ruling D)
COVERAGE_GROUP_SHARE = _c("C3.coverage_group_share", 0.5)
COVERAGE_ROW_SHARE = _c("C3.coverage_row_share", 0.90)

# C4 First year (R4): set by computed lags only; no number. Recorded as a flag so the manifest
# carries the convention.
# origin: pm25_architecture.py:64-72 (the first data year read only as a lag source)
FIRST_YEAR_FROM_LAG_SOURCES_ONLY = _c("C4.first_year_from_lag_sources_only", True)

# C5 Router thresholds (R12)
# origin: MIN_HIST = 24, pm25_adaptation.py:143; "under 2 = most units seen at most once"
PER_UNIT_MIN_VALID_ROWS = _c("C5.per_unit_min_valid_rows", 24)
REGION_MIN_VALID_ROWS = _c("C5.region_min_valid_rows", 2)

# C6 Leads (R10)
# origin: owner ruling I1 (OWNER_RULINGS_2026-09-28.md section I, 2026-10-05: "only the nowcast, 6 lead, 12
# lead -- three leads only"): 6 and 12 months for every package, plus lead 0 (the contract, C6 below). It
# replaces 1/3/6/12 (Q41 a). Grids: steps = months x steps per year / 12; events: days = months x 365.25 / 12
# (183 and 365); rounded half up, merged when equal (annual data: both round to 1 year and merge)
LEAD_MONTHS = _c("C6.lead_months", (6, 12))
MONTHS_PER_YEAR = _c("C6.months_per_year", 12)
DAYS_PER_YEAR = _c("C6.days_per_year", 365.25)
LEAD_ROUNDING = _c("C6.lead_rounding", "half_up")
LEAD_ZERO_CONTRACT = _c("C6.lead_zero_contract", True)  # R10: lead 0 always runs as the contract

# C7 Bank units per group (R18 (1): trees, region-router fit, fallback router) and the region row
# budget (R14)
# origin: 100 units per group, Q39 a; pm25_adaptation.py:122-123. Under LORO this is the BANK count
# (owner rulings E, L2 rule 1); the scored count is C16.
BANK_UNITS_PER_GROUP = _c("C7.bank_units_per_group", 100)
# origin: R18, keeps the rows per group-year of 100 units at a monthly step
SUBMONTHLY_ROWS_PER_GROUP_YEAR = _c("C7.submonthly_rows_per_group_year", 1200)
EVENT_FLOOR_PER_GROUP = _c("C7.event_floor_per_group", 10)  # R18 10-event floor, on the SCORED count
EVENT_QUANTILE = _c("C7.event_quantile", 0.90)  # R18: event = y strictly above the donor q90
# origin: REGROWS = 60000, adaptation.py:1213 (defo's shipped region router budget); exposure
# unknown (plan 7.2), so flagged test-exposed. Under LORO the fit keeps this budget of whole, evenly
# spaced BANK units, decoupled from the scored units (owner rulings E, L2 rule 2; split.region_cap_units)
REGION_ROUTER_ROW_BUDGET = _c("C7.region_router_row_budget", 60000, test_exposed=True)

# C8 Neighbour decision folds (R13): leave one group out. Every group is held out once, by dropping its
# overlap block's trees (and, by default, the pool groups' trees) from one bank cut at the inner-fit
# end, so there is no fold count. Recorded as a flag so the manifest carries the convention.
# origin: owner ruling D (every group tested; a router never sees its own group's trees); plan 3.1 C8.
# It replaces K = min(5, donor groups) (coral's shipped decision used 5 folds).
NEIGHBOUR_FOLDS_LEAVE_ONE_GROUP_OUT = _c("C8.neighbour_folds_leave_one_group_out", True)

# C9 Guard tolerance constant k (R36)
# k is fixed once so that the identity gate of the first shipped nowcast stays at 1e-6 (U-4), and
# checked to be at least 10x the measured arithmetic error. The value needs that measurement.
GUARD_TOLERANCE_K = _c("C9.guard_tolerance_k", 5.230771281733543e-08, status="cited")  # origin: owner ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S12 a): the measured candidate, PM2.5 nowcast identity gate exactly C9.identity_gate (tests/test_c9_guard_tolerance.py)
IDENTITY_GATE = _c("C9.identity_gate", 1e-6)  # origin: U-4, the shipped identity gate
K_MIN_MULTIPLE_OF_ARITH_ERROR = _c("C9.k_min_multiple_of_arith_error", 10)
MEASURED_ARITH_ERROR = _c("C9.measured_arith_error", 9e-8)  # origin: plan R36, measured

# C10 Flags (report only, never a choice)
FALLBACK_FLAG_SHARE = _c("C10.fallback_flag_share", 0.05)  # R12: fallback over 5% of units
BORDERLINE_SHARE = _c("C10.borderline_share", 0.20)  # plan 2: within 20% of a threshold
THIN_GROUP_ROWS_PER_ROUTER_COLUMN = _c("C10.thin_group_rows_per_router_column", 20)  # R18
# origin: owner ruling G1 (OWNER_RULINGS_2026-09-28.md section G, 2026-10-05): the router fit rows a pass
# leaves out for missing context are "flagged above 5% of a unit's fit rows" (report only, never a choice).
# Moved here from pipeline/stages.py (SMOKES_REPORT.md section 5, ATTENTION G1-b).
CONTEXT_MISSING_FLAG_SHARE = _c("C10.context_missing_flag_share", 0.05)

# C11 Neighbour pool (R14)
# origin: adaptation.py:1434 (MINOK = 12), 1638-1640 (150 by distance, then 50 in feature space)
NEIGHBOUR_POOL_DISTANCE = _c("C11.neighbour_pool_distance", 150)
NEIGHBOUR_POOL_FEATURE = _c("C11.neighbour_pool_feature", 50)
NEIGHBOUR_POOL_MIN_ROWS = _c("C11.neighbour_pool_min_rows", 12)

# C12 Penalty centres and grid (R14, R26)
# origin: fire_architecture.py:102-103 (ALPHA 0.5, A_CTX 0.25); adaptation.py:1434 for the
# neighbour kind. Listed in the plan 7.2 test-exposure table, so flagged test-exposed.
PER_UNIT_TREES_CENTRE = _c("C12.per_unit_trees_centre", 0.5, test_exposed=True)
PER_UNIT_CONTEXT_CENTRE = _c("C12.per_unit_context_centre", 0.25, test_exposed=True)
# origin: adaptation.py:1434 (the neighbour grid: 35 points around 0.5 / 0.25, R14); plan 7.2 lists
# the per-unit AND neighbour centre, so both kinds get their own ids, flagged test-exposed
NEIGHBOUR_TREES_CENTRE = _c("C12.neighbour_trees_centre", 0.5, test_exposed=True)
NEIGHBOUR_CONTEXT_CENTRE = _c("C12.neighbour_context_centre", 0.25, test_exposed=True)
# origin: LAM = 100.0, adaptation.py:1214; coincides with defo's pooled test-window argmax
# (CLAIMS_LEDGER.md:610), plan 7.2
REGION_LAMBDA_CENTRE = _c("C12.region_lambda_centre", 100.0, test_exposed=True)
# origin: pm25_adaptation.py:176 (LEVELS) and :177 (RATIOS); 7 x 5 = 35 points
PENALTY_LEVELS = _c("C12.penalty_levels", (0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0))
PENALTY_RATIOS = _c("C12.penalty_ratios", (0.0625, 0.125, 0.25, 0.5, 1.0))
# The plan gives the region grid as "7 levels 0.1-100x around lambda 100". No shipped 7-value
# region list exists (adaptation.py:153 swept 15 levels 0.01-100x; defo_softgate.py:75 swept six
# values 10-3000), so the per-unit level list above is reused. OWNER CONFIRMS.
REGION_PENALTY_LEVELS = _c("C12.region_penalty_levels", (0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0))

# C13 Bank (R19), correctors (R19), GLS weight model (R25), smoke (R21)
# origin: pm25_adaptation.py:636-648 (bags max(30, half the rows) with replacement; depth 8, leaf 5,
# max_features 0.1, squared error); 100 trees per donor (uniformity ruling 2026-09-28). Under LORO every
# group trains its own 100 trees (plan R19), so the constant is per GROUP.
TREES_PER_GROUP = _c("C13.trees_per_group", 100)
TREES_PER_DONOR = TREES_PER_GROUP  # alias (not registered): fit/bank.py still imports this name
BAG_MIN_ROWS = _c("C13.bag_min_rows", 30)
BAG_FRACTION = _c("C13.bag_fraction", 0.5)
BAG_WITH_REPLACEMENT = _c("C13.bag_with_replacement", True)
TREE_MAX_DEPTH = _c("C13.tree_max_depth", 8)
TREE_MIN_LEAF = _c("C13.tree_min_leaf", 5)
TREE_MAX_FEATURES = _c("C13.tree_max_features", 0.10)
TREE_CRITERION = _c("C13.tree_criterion", "squared_error")
TREE_DTYPE = _c("C13.tree_dtype", "float32")
# origin: D51 (owner rulings, part A): |observed - expected| <= 5 x sqrt(p (1 - p) / n), p the expected
# held-out share for the bag size and n the home group's rows; moved here by owner rulings E ("the
# constants D51 5 sigma, D52 50 rows and the block size 12,288 move into engine_constants.py"). fit/bank.py
# holds the same value as OOB_SHARE_TOLERANCE_SIGMAS until it reads this one.
OOB_SHARE_TOLERANCE_SIGMAS = _c("C13.oob_share_tolerance_sigmas", 5.0)
# origin: adaptation.py:454-477 (out-of-bag correctors, depth 6, leaf 10)
CORRECTOR_MAX_DEPTH = _c("C13.corrector_max_depth", 6)
CORRECTOR_MIN_LEAF = _c("C13.corrector_min_leaf", 10)
# origin: adaptation.py:454 (minrows=50); D52 accepted (owner rulings, part A): a tree with fewer
# out-of-bag rows gets no corrector and no placebo corrector; moved here by owner rulings E.
# fit/correctors.py holds the same value as CORRECTOR_MIN_OOB_ROWS until it reads this one.
CORRECTOR_MIN_OOB_ROWS = _c("C13.corrector_min_oob_rows", 50)
# origin: coral_architecture.py:304 (RandomForestRegressor(120, depth 8, leaf 20, all features,
# bootstrap, random_state 0)); pinned to 4 threads here instead of n_jobs=-1
GLS_TREES = _c("C13.gls_trees", 120)
GLS_MAX_DEPTH = _c("C13.gls_max_depth", 8)
GLS_MIN_LEAF = _c("C13.gls_min_leaf", 20)
GLS_MAX_FEATURES = _c("C13.gls_max_features", 1.0)
GLS_BOOTSTRAP = _c("C13.gls_bootstrap", True)
GLS_RANDOM_STATE = _c("C13.gls_random_state", 0)  # fixed, disclosed, never varied
GLS_THREADS = _c("C13.gls_threads", 4)
GLS_SIGMA_FLOOR_SHARE = _c("C13.gls_sigma_floor_share", 0.01)  # R25: 1% of the donor spread
GLS_CLIP_QUANTILES = _c("C13.gls_clip_quantiles", (0.05, 0.95))  # R25, on donor rows only
GLS_WEIGHT_RATIO_CAP = _c("C13.gls_weight_ratio_cap", 100.0)  # R25: max/min weight ratio
# origin: pm25_adaptation.py:122-126 (40 cells, 12 trees per donor at smoke size). Under LORO (plan R21):
# the first 4 groups in sorted order, every one trained and tested, all 40 units scored, 12 trees per
# group; it replaces the first 2 donor + first 2 test groups (there is no test set).
SMOKE_UNITS_PER_GROUP = _c("C13.smoke_units_per_group", 40)
SMOKE_TREES_PER_GROUP = _c("C13.smoke_trees_per_group", 12)
SMOKE_TREES_PER_DONOR = SMOKE_TREES_PER_GROUP  # alias (not registered): fit/bank.py still imports it
SMOKE_GROUPS = _c("C13.smoke_groups", 4)  # R21: the first 4 groups in sorted order

# C14 Threads and backend (A8, plan 4.5)
# origin: A8 machine profile; bench_tree_threads.py and bench_router_threads.py (2026-09-28)
FOREST_THREADS = _c("C14.forest_threads", 4)
BLAS_THREADS = _c("C14.blas_threads", 4)  # any BLAS outside router units
TREE_PREDICT_WORKERS = _c("C14.tree_predict_workers", 8)  # cannot change a number (plan 4.5)
ROUTER_WORKERS = _c("C14.router_workers", 8)
ROUTER_WORKER_BLAS_THREADS = _c("C14.router_worker_blas_threads", 1)
SKLEARNEX_REQUIRED = _c("C14.sklearnex_required", True)
# origin: pm25_adaptation.py:448 (ROW_BLOCK = 12288, ruling R2: about 0.53 GB of block buffer at 10,700
# trees); moved here by owner rulings E. The block size cannot change a number (a tree answers each row
# on its own; plan 4.5), so it sits with the runtime constants. fit/tables.py holds the same value as
# ROW_BLOCK_ROWS until it reads this one.
TABLE_ROW_BLOCK_ROWS = _c("C14.table_row_block_rows", 12288)

# C15 Thresholds without a cited origin: proposed defaults, the owner signs them (plan 9.1 item 2f).
# The two group thresholds are cited: they restate the signed D44.
MISSING_FLAG_SHARE = _c("C15.missing_flag_share", 0.25, status="cited")  # R30  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was proposed
# origin: D44 (signed as "3 test or 2 donor refuse; 14 test or 5 donor flag": owner rulings A accepted its
# proposed default), restated for LORO, not reopened (SIGNATURES_LORO_ADDENDUM.md, "Signed decisions that
# LORO restates"; plan 3.1 C15; owner ruling D): every group is tested and each router sees the trees of
# G-1 groups, so the thresholds count GROUPS. The five-donor flag belonged to the old donor folds and goes.
MIN_GROUPS = _c("C15.min_groups", 3, status="cited")  # G-SUPPORT refuse under 3 groups
FLAG_GROUPS_BELOW = _c("C15.flag_groups_below", 14, status="cited")  # G-SUPPORT flag under 14
FALLBACK_MIN_UNITS_FOR_SEARCH = _c("C15.fallback_min_units_for_search", 10, status="cited")  # R12  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was proposed

# C16 LORO scored-unit budget (R18 (2))
# origin: owner rulings E, L1 (one engine constant K = 20: scored units per group = max(10, floor(20 x
# R18 count / G)), capped at the units available). K = 20 is the old PM2.5 test-group count and the
# geometric mean (19.5) of the four old counts (20, 10, 16.45 capped, 44): it comes from the size of the
# old hand splits, not from results (disclosed, plan 7.2). It gives 15 / 50 / 2,040 / 15 per group on
# PM2.5 / fire / defo / NDVI; the departure from ruling D's "same total" (fire x2, NDVI x0.45, defo
# x1.22) is disclosed and the old totals are printed beside.
K_GROUP_EQUIVALENTS = _c("C16.k_group_equivalents", 20)
# origin: plan 3.1 C16 and R18 ("max(10, ...)"; the 10 is flagged when it binds); owner rulings E, L1
SCORED_UNITS_MIN = _c("C16.scored_units_min", 10)

# C17 Rival region folds (plan 4.6)
# origin: owner ruling D ("donor-only rivals are trained on region folds (10)"); plan 3.1 C17: round-robin
# over overlap blocks sorted by their first group name (block at sorted position j -> fold j mod 10), as
# C8 did over names before LORO. L3 (the tuning rule, Board B) is deferred to M8.
RIVAL_FOLDS = _c("C17.rival_folds", 10)

# C18 Last value (owner rule J2 d): the longest gap the last-value rule bridges, in months
# origin: owner ruling J2(d) (OWNER_RULINGS_2026-10-05.md section J, 2026-10-05): "a tree feature missing in
# a month INSIDE its record takes the most recent EARLIER value of the same unit, at most 2 months back
# (engine constant), never a later value; every fill is counted per column; longer gaps fall back to R30".
# Steps = floor(months x steps per year / 12) (io/lastvalue.py): 2 on a monthly target, 0 on an annual one
# (no last-value fill on annual data), 7 on 46 composites a year.
LAST_VALUE_MAX_MONTHS = _c("C18.last_value_max_months", 2)

# A7 design flag (plan 7.2, 9.1 item 4): decision-window parity under leave one region out
# origin: owner rulings E, L6 option (b): for the inner decision the bank AND the correctors are refit at
# the INNER cut, so the trees behind the inner decision hold no rows after the inner-fit end (about
# +5-6.6 h over the four nowcasts). It replaces option (a), pm25_adaptation.py's one bank at the donor
# train end serving both the inner decision and the test pass. It stays test-exposed (the 7.2 row
# stays): the ruling names the bank and the correctors only, not whether the inner GLS error target
# (R25) also uses the inner-cut bank (plan 9.1 item 4, +0.9-2.4 h), and the weight model's in-sample
# rows (L5) are disclosed beside it.
INNER_CUT_BANK_REFIT = _c("A7.inner_cut_bank_refit", True, test_exposed=True)

# ---------------------------------------------------------------------------------------------------
# Numbers named in plan Section 1 / 2 / 5 rules but missing from the 3.1 table. OWNER CONFIRMS each.
# origin: R17 (last 3 values, trailing 1-year and 5-year means, all-history mean)
HISTORY_LAST_VALUES = _c("S2.history_last_values", 3, status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra
HISTORY_TRAILING_YEARS = _c("S2.history_trailing_years", (1, 5), status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra
# origin: R23, pm25_adaptation.py:575-576 (c = 1st percentile of positive donor-row y)
LOG_C_QUANTILE = _c("S2.log_c_quantile", 0.01, status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra
# origin: R22 (a log or arcsine link needs MORE THAN this many distinct donor values: > 2)
LINK_DISTINCT_VALUES_ABOVE = _c("S2.link_distinct_values_above", 2, status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra
# origin: R31 (guess-normal and the last-5-years normal, Q26)
RECENT_NORMAL_YEARS = _c("S2.recent_normal_years", 5, status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra
# origin: R32 (half the donor rows' mean absolute deviation from their own normal)
HIT_TOLERANCE_DEVIATION_SHARE = _c("S2.hit_tolerance_deviation_share", 0.5, status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra
# origin: R33, forecast_report.py:57-77 (top 10%; NaN under 10 events or over 50% events)
DETECTION_TOP_SHARE = _c("S2.detection_top_share", 0.10, status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra
DETECTION_MIN_EVENTS = _c("S2.detection_min_events", 10, status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra
DETECTION_MAX_EVENT_SHARE = _c("S2.detection_max_event_share", 0.50, status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra
# origin: R34, Q19 a (group jackknife at 1.96)
JACKKNIFE_Z = _c("S2.jackknife_z", 1.96, status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra
# origin: G-SENTINEL (plan 5): abs >= 1e30 masked; abs >= 2^30 flagged unless opted out
SENTINEL_MASK_ABS = _c("S5.sentinel_mask_abs", 1e30, status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra
SENTINEL_FLAG_ABS = _c("S5.sentinel_flag_abs", float(2 ** 30), status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra
# origin: G-CADENCE (plan 5): annual joins after a constancy assert at 0.1%
# (pm25_architecture.py:139-160)
CADENCE_CONSTANCY_TOLERANCE = _c("S5.cadence_constancy_tolerance", 0.001, status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra
# origin: G-SUPPORT (plan 5): donor y has AT LEAST this many distinct values (>= 2); a different
# test from R22's "more than 2" above
SUPPORT_MIN_DISTINCT_VALUES = _c("S5.support_min_distinct_values", 2, status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra
# origin: plan 1.2 unit id format: '{group}_{lat}_{lon}' with 4 decimals when no grid indices exist
UNIT_ID_LATLON_DECIMALS = _c("S1.unit_id_latlon_decimals", 4, status="cited")  # owner confirmed: ruling N (2026-10-06, FREEZE_SIGNOFF_SHEET.md S20 b), was extra


# ---------------------------------------------------------------------------------------------------
def get(cid):
    """Value of the constant ``cid``. Raises KeyError for an unknown id, UnsetConstantError if unset."""
    const = _REGISTRY[cid]
    if const.status == "unset":
        raise UnsetConstantError("engine constant %s is not fixed yet" % cid)
    return const.value


def constants():
    """All registered constants, in declaration order."""
    return tuple(_REGISTRY.values())


def _json_value(value):
    if value is UNSET:
        return "UNSET"
    if isinstance(value, tuple):
        return [_json_value(v) for v in value]
    return value


def table():
    """Rows for the manifest: id, value, test_exposed, status. No names, only ids (G-NONAMES)."""
    rows: List[Dict[str, Any]] = []
    for const in _REGISTRY.values():
        rows.append({"id": const.id, "value": _json_value(const.value),
                     "test_exposed": const.test_exposed, "status": const.status})
    return rows


def constants_hash():
    """SHA-256 of the canonical JSON of ``table()``."""
    payload = json.dumps(table(), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def groups():
    """Group prefixes present (C1..C18, A7, S1, S2, S5)."""
    seen: List[str] = []
    for cid in _REGISTRY:
        prefix = cid.split(".", 1)[0]
        if prefix not in seen:
            seen.append(prefix)
    return tuple(seen)


def by_group(prefix) -> Tuple[Constant, ...]:
    return tuple(c for c in _REGISTRY.values() if c.id.split(".", 1)[0] == prefix)


# ---------------------------------------------------------------------------------------------------
# V  The validators of treeroute/check/ (plan 5 guards; plan 8.1 M1 quick checks, M4 deep validators).
# Added by the check build (agent B, 2026-10-06) in this separate block at the end of the file. Every value
# below is an owner-ruled decision (OWNER_RULINGS_2026-09-28.md, ruling A); none is a modelling number.
# origin: owner ruling A, D79 and D92 ("a stride sample of 1,000 rows (all rows if fewer)"): the rows the
# G-DERIVED recompute (check_g_derived) and the G-HIST sample match (check_g_hist_sample) read.
CHECK_SAMPLE_ROWS = _c("V1.check_sample_rows", 1000)
# origin: owner ruling A, D79 and D92 ("with a relative tolerance of 1e-9"): the match tolerance of the
# G-DERIVED recompute, the G-HIST sample match and the G-LINEAGE sum-group reconstruction test.
CHECK_SAMPLE_REL_TOLERANCE = _c("V1.check_sample_rel_tolerance", 1e-9)
# origin: owner ruling A, D95 ("refuse if more than 0.1% of a column's non-missing values fall outside its legal
# range; otherwise flag and print the count"): G-RANGE (check_g_range).
RANGE_REFUSE_SHARE = _c("V2.range_refuse_share", 0.001)
# origin: owner ruling A, D94 (the proposed default: "the common integer and float fill values, each with its
# origin comment"): the codes G-SENTINEL's deep scan (check_g_sentinel_deep) looks for in RAW values of a
# column that does not declare them. Report only (FLAG); the read-time mask (io/sentinel.py) masks only
# DECLARED codes and abs >= 1e30. Origins, in order:
#   -9999.0                 the GDAL / ESRI raster NoData convention
#   -999.0                  the common station and gridded-product missing code
#   -32768.0                the int16 minimum (HDF integer fill; the toy store catalog's declared fill)
#   -32767.0                netCDF's default fill for a short (NC_FILL_SHORT)
#   32767.0                 the int16 maximum, used as a fill by satellite integer products
#   65535.0                 netCDF's default fill for an unsigned short (NC_FILL_USHORT)
#   -2147483648.0           the int32 minimum: the panel's -2^31 NoData poison (plan 5 G-SENTINEL, 47/133 regions)
#   -2147483647.0           netCDF's default fill for an int (NC_FILL_INT)
#   2147483647.0            the int32 maximum
#   -2147450880.0           the derived near-sentinel panel_sentinel.py:15-20 missed (plan 5 G-SENTINEL)
#   1e20                    the CF / CMIP missing_value convention
#   9.969209968386869e36    netCDF's default float and double fill (NC_FILL_FLOAT; the target product's fill)
#   -3.4028234663852886e38  the float32 minimum (GDAL float NoData)
#   3.4028234663852886e38   the float32 maximum
KNOWN_FILL_CODES = _c("V3.known_fill_codes", (
    -9999.0, -999.0, -32768.0, -32767.0, 32767.0, 65535.0, -2147483648.0, -2147483647.0, 2147483647.0,
    -2147450880.0, 1e20, 9.969209968386869e36, -3.4028234663852886e38, 3.4028234663852886e38))
# origin: owner ruling A (the proposed default of check_g_hist_sample: "lags 0 to 3 and the R17 trailing
# windows"): the own-target look-backs G-HIST's sample match tests (the trailing windows are R17's,
# S2.history_trailing_years).
HIST_SAMPLE_LAGS = _c("V4.hist_sample_lags", (0, 1, 2, 3))
# origin: the machine profile (16 cores; 15.8 GB RAM, 5-11 GB free while other work runs): 'check --deep' pass 1 reads
# each group in its own worker process (one group's target keys and labels plus one 32-column block of one store file
# per worker). The smoke-size gate (2026-10-06) peaked at 6.7-8.2 GiB for the whole process tree with 3 workers, so 2.
# Plumbing: pass 1's results are integer counts and sets merged per group, so this value cannot change a number
# (tests/test_check_deep.py checks 1 worker against 2); it changes hours only.
CHECK_DEEP_WORKERS = _c("V5.check_deep_workers", 2)


# ---------------------------------------------------------------------------------------------------
# P  Pre-flight byte sizes and plumbing of plan R20's per-group schedule (added by the per-group build, agent A,
# 2026-10-06) in this separate block at the end of the file. Each P1-P3 value is the size of a go/refuse ESTIMATE
# (plan 1.7: disk and RAM decide only go or refuse; they never set a unit count or any other number), and P4 is a
# write block: none of them can change a number of a run; P1-P3 change only whether a run is refused on a machine.
# P5 (added by agent G, 2026-10-06) is a row block of the donor feature matrix and the GLS target: it bounds RAM only.
# origin: counted from pipeline/data.py ColumnReader._read_drivers, which reads a whole driver file's needed columns
# before it keeps its units' rows: 8 bytes a read value (float64, the widest stored dtype; runs/preflight.py
# driver_file_bytes).
READER_FILE_VALUE_BYTES = _c("P1.reader_file_value_bytes", 8)
# origin: counted from the same read, per file row: the unit id column as read and its string cast for the unit
# filter (2 x (a 4-byte offset + up to 60 characters) = 128 bytes), the time-key columns (up to 2 x 8) and the filter
# mask, rounded up to 160. Checked on two full-size measurements of pm25_draft's largest group (yakutia_larch, 44 driver
# files, 2026-10-06): D:/treeroute/A_pergroup_20261006/measure_pm25/measure.json (102 frame columns: the reader rose
# 0.60 GiB working set, 0.38 GiB private; estimate 0.995 GiB, of which this file term 0.87 GiB) and
# D:/treeroute/skepticA_20261006/measure_pm25_full/measure.json (139 columns: rose 0.66 / 0.66 GiB; estimate 1.21 GiB).
READER_FILE_ROW_BYTES = _c("P1.reader_file_row_bytes", 160)
# origin: counted from fit/context.py FitContext._tree_feature_matrix (the GLS weight model's donor matrix,
# fit/weights.py gls_ram_bytes), which writes ONE row block (P5.donor_block_values values) at a time into the
# preallocated float32 matrix (4 bytes a value, counted apart): per value of the block in flight, an upper bound of the
# feature source's read and its own copies (FeaturePool's ascending gather and its reordered copy, 2 x 4 bytes a pool
# value, and the gather's two row-index arrays, 16 bytes a row: at most 9 bytes a tree value while the pool's context
# columns are at most 1/8 of its tree columns less 2: ndvi_draft 9 of 499, pm25_draft and fire_draft 2 of 124,
# defo_draft none; HistoryOverride's read and its copy, 2 x 4) and, after the read returns, the read (4) beside one
# boolean mask at a time (isinf, then isnan: 1). Measured 2026-10-06 at the ndvi_draft smoke's GLS shape (25,558 donor
# rows x 499 tree columns and 9 context columns, blocks of 8,405 rows; tracemalloc around _tree_feature_matrix alone
# over a real FeaturePool, D:/treeroute/G2_20261006/probe/fr_live.json): 8.18 bytes a block value above the matrix
# (85.3 MB for a 51.0 MB matrix; the count above gives 8 x 508/499 + 16/499 = 8.18), so this bound's headroom is about
# 10% (tests/test_fit_weights_blocks.py checks it over a real FeaturePool). The smoke's own GLS hand-out peaked at the
# same 85.3 MB (D:/treeroute/G_20261006/gates_final/ndvi_draft/pergroup/gate.json). Before the row blocks (agent G,
# 2026-10-06) the same 9 bytes were held for EVERY value at once (104.3 MB, D:/treeroute/G2_20261006/probe/fr_old.json).
GLS_MATRIX_BUILD_BYTES_PER_VALUE = _c("P2.gls_matrix_build_bytes_per_value", 9)
# origin: counted from fit/tables.py TreeAnswerStore._read, the ONE store read of a group's rows in fit/weights.py
# weight_model_for_cut's donor-row pass (the per-group store view, fit/tables.py DropAfterRead, drops the group's table
# after that read), beside the matrix, per cell of the read (the group's rows x the bank's trees less the group's own)
# while it is in flight: the read's float32 output (4 bytes a cell) beside the gathered rows of the table's one segment
# (4; the GLS pass builds a group's table in one build, so one segment, and a fancy index of its memmap reads a copy).
# Measured 2026-10-06 (D:/treeroute/G2_20261006/probe/store_read.json from store_read_probe.py: a real TreeAnswerStore
# read through DropAfterRead, tracemalloc, 4,500 rows x 40, 120, 300 and 800 columns): 8 bytes a cell plus 57-59 bytes
# a row (the row-index arrays, P2.gls_answer_read_bytes_per_row). After the read only its float32 output is held
# (4 bytes a cell) while the target is computed beside ONE row block's copies (P2.gls_answer_block_bytes_per_cell);
# fit/weights.py gls_ram_bytes takes the larger of the two. Until 2026-10-06 (agent G) this constant was 16 for the
# whole moment: the output (4) plus the column copy (4) and the float64 copy (8) of the whole group, which are now one
# row block's (the in-flight 8 sat below the 16).
GLS_ANSWER_READ_BYTES_PER_CELL = _c("P2.gls_answer_read_bytes_per_cell", 8)
# origin: counted from the same read (fit/tables.py TreeAnswerStore.unit_view and _read), per row of the read while it
# is in flight: the read's own copy of the row ids, each row's segment and position (_locate), the segment's selection,
# its rows, their order and the two reordered copies (the gather's rows and the output's positions): at most 8 int64
# arrays, 64 bytes a row. Measured beside the cells above (D:/treeroute/G2_20261006/probe/store_read.json): 57-59 bytes
# a row at 40-800 columns. Under 0.01 byte a cell at full-size NDVI's 13,200 read columns, but about 1/6 of the read at
# 40 columns; it was not counted before 2026-10-06 (agent G, second round).
GLS_ANSWER_READ_BYTES_PER_ROW = _c("P2.gls_answer_read_bytes_per_row", 64)
# origin: counted from fit/weights.py _blocked_group_error, per cell of ONE row block of the read (P5.donor_block_values
# values, rows x the read's columns): the copy of the columns outside the rows' overlap block (4 bytes) and the float64
# copy whose row mean is the GLS target (8); the finite check's boolean mask (1) is freed before the float64 copy.
GLS_ANSWER_BLOCK_BYTES_PER_CELL = _c("P2.gls_answer_block_bytes_per_cell", 12)
# origin: counted from fit/weights.py fit_weight_model: the finite check's boolean mask over the donor matrix
# (1 byte a value) before the forest's fit, which rose at most 0.25 bytes a value above X and y at 36M values or
# more in the measurement below (it does not coexist with the mask).
GLS_FOREST_BYTES_PER_VALUE = _c("P2.gls_forest_bytes_per_value", 1)
# re-measured 2026-10-15 (install review, D:/treeroute/install_20261015/gls_probe/forest.jsonl, gls_forest_probe.py;
# the C13 forest after the launcher's pins, float32 X of 200,000-800,000 rows x 60-240 columns, 48M-80M values): the
# fit's own peak-commit rise above X and y is 5.045 bytes a value + 218.6 a row + 4.8 MB (least squares over 4 shapes,
# residuals under 0.5 MB), the same with X on a temp memmap (334.6 vs 334.0 MB at 48M values): the fit copies its input
# (4 bytes a value: the matrix term of the forest moment, which _file_backed keeps for that copy) and adds 1.05 bytes
# a value, so this constant stays 1 (it is not far below). The per-row part is above P2.gls_forest_bytes_per_row: an
# owner's item (go/refuse only). The earlier 7.2 bytes a value (12M values or fewer) held the row and fixed parts.
# origin: measured 2026-10-06 (D:/treeroute/A_pergroup_20261006/gls_ram/forest.jsonl, measure_gls_forest.py): the
# C13 GLS forest (sklearnex, 4 threads, oob_score on) on synthetic float32 matrices of 100,000-600,000 rows x 40-120
# columns rose 6.0-10.8 MB of private bytes above X and y (12.2 MB working set at most): 85 bytes a row at 100,000
# rows, 19 at 600,000 (the out-of-bag arrays and a fixed part). 64 bytes a row with the 1 byte a value above covers
# every measured shape.
GLS_FOREST_BYTES_PER_ROW = _c("P2.gls_forest_bytes_per_row", 64)
# origin: the passes' code (pipeline/run.py disk_plan): the tree-answer table kinds of ONE group that coexist on disk
# in a pass. The nowcast's test pass reads plain, corrector and placebo (pipeline/passes.py test_pass).
NOWCAST_TABLE_KINDS = _c("P3.nowcast_table_kinds", 3)
# origin: as above: a lead's guard reads the pinned kind and the corrector's fallback level, its test pass the pinned
# kind and the placebo (pipeline/ladder.py).
LEAD_TABLE_KINDS = _c("P3.lead_table_kinds", 2)
# origin: plumbing (pipeline/passes.py fill_pool_by_group): the rows of one pool write in a per-group pool fill, the
# block stages.fill_pool writes. The values written are the same at any block size (the pool is a float32 memmap
# written row for row; tests/test_pipeline_ladder.py checks the per-group fill byte for byte against the whole fill);
# it bounds RAM only.
POOL_FILL_ROWS = _c("P4.pool_fill_rows", 50000)
# origin: plumbing (agent G, 2026-10-06): the values (rows x columns) of ONE row block wherever the donor rows' tree
# features are built whole (fit/context.py FitContext._tree_feature_matrix: the eager DonorRows.X, the GLS weight
# model's donor matrix among them) and wherever the GLS donor-row pass turns one group's answer read into its target
# (fit/weights.py _blocked_group_error). 2^22 values is 16 MiB a float32 copy: one block's temporaries (P2: 9 bytes a
# value at the build, 12 a cell at the target) are 36-48 MiB, under 1% of full-size NDVI's 4.69 GiB donor matrix (the
# estimate of 2026-10-06), while the ndvi_draft smoke's 25,558 x 499 matrix (measured 2026-10-06) is still built in 4
# blocks, so the smokes run the blocked build (pm25_draft's and fire_draft's GLS matrices fit in one block; defo_draft
# fits no GLS model). The values are the same at any block size (each feature row is read on its own; the target's
# blocks keep the whole group's column-wise float64 sum, see fit/weights.py _row_blocks;
# tests/test_fit_weights_blocks.py checks one block against many, byte for byte); it bounds RAM only.
DONOR_BLOCK_VALUES = _c("P5.donor_block_values", 4194304)

# ---------------------------------------------------------------------------------------------------
# V (continued)  Two float-comparison tolerances of treeroute/check/guards.py that were bare numbers (the check
# fix round, agent B, 2026-10-06), added in this separate block at the end of the file. Neither is a modelling
# number: each only absorbs floating-point rounding in a comparison whose operands differ by far more when they
# really differ.
# origin: float rounding of a step length in days (C6: a month is 365.25 / 12 days, so a monthly and a target's
# monthly step can differ in the last bits): list_co_measured_candidates' "no coarser than the target's cadence"
# compares step lengths with this relative slack. Real cadences differ by at least a factor 28/31 (day vs month
# lengths), so the value only decides equal lengths.
CADENCE_COMPARE_REL_TOLERANCE = _c("V6.cadence_compare_rel_tolerance", 1e-9)
# origin: the float32 rounding of a large fill code (relative spacing 2^-24, about 6e-8): G-SENTINEL's deep scan
# (sentinel_counts) counts a raw value at or above the 1e30 mask as the known code V3.known_fill_codes names when
# it lies within this relative distance of it. The large codes (1e20 below the mask; 9.97e36 and 3.40e38 above it)
# differ by orders of magnitude, so the value only absorbs a code stored as float32 and read as float64.
LARGE_FILL_CODE_REL_TOLERANCE = _c("V7.large_fill_code_rel_tolerance", 1e-6)

# ---------------------------------------------------------------------------------------------------
# P6  Crash-safe checkpoints inside the long steps (owner ruling P, OWNER_RULINGS_2026-10-06.md section P, 2026-10-13;
# runs/checkpoint.py), added in this separate block at the end of the file. None of them can change a number of a run
# (ruling P2: a step that loads a checkpoint ends in the same bytes as one that computed it; the gates compare): the
# chunk sizes decide how much work a stop loses, the byte sizes only the G-DISK go/refuse of the checkpoints.
# origin: owner ruling P1 ("checkpoint every chunk of files"): the census pass saves a chunk after every 1/100 of the
# target files, so a stop loses at most about 1% of the pass (full-size NDVI, 2,926 files in 1,998 s on 2026-10-12:
# 30 files, about 20 s; a smoke's few files: one file a chunk). A chunk is a delta of the counters the files touched
# (derive/census.py checkpoint_delta), a few MB at full size, so 100 of them cost seconds.
CENSUS_CHECKPOINT_CHUNKS = _c("P6.census_checkpoint_chunks", 100)
# origin: owner ruling P1: a chunk also closes after this many seconds, so a store of few slow files still saves at
# least once a minute (a stop loses at most this plus the file being read).
CENSUS_CHECKPOINT_SECONDS = _c("P6.census_checkpoint_seconds", 60)
# origin: counted from derive/census.py checkpoint_delta, per census unit over all chunks: its id as JSON text (up to
# about 60 bytes with quotes and comma), its group index (8) and its row count (8, written again by each chunk whose
# code range holds it: at most twice for a unit whose group spans a chunk edge), rounded up to 128 for the npz headers.
# G-DISK go/refuse only.
CHECKPOINT_CENSUS_UNIT_BYTES = _c("P6.checkpoint_census_unit_bytes", 128)
# origin: counted from the same delta: the existence and validity bits of every (calendar step, unit) are written by
# the chunk that holds the unit's file of that step; a chunk whose code range spans two groups writes the touched steps
# over both groups' codes, so at most twice. G-DISK go/refuse only.
CHECKPOINT_CENSUS_BIT_COPIES = _c("P6.checkpoint_census_bit_copies", 2)
# origin: counted from pipeline/stream.py StreamedShareReader._measure_by_group's group record (pickled): the group's
# column-reader leftovers (its data manifest, its static report strata over its picked units, its last-value record)
# and the fixed parts of the counts, bounded at 256 KiB a group; the per-feature part below is counted apart. G-DISK
# go/refuse only.
CHECKPOINT_R30_GROUP_BYTES = _c("P6.checkpoint_r30_group_bytes", 262144)
# origin: counted from the same record, per tree feature: its donor missing and zero counts, its last-value counts
# (five) and its test-year counts (one per test year, twice: the donor rows' and the streamed count's), each a pickled
# int beside its key (the column name is pickled once and referenced), bounded at 256 bytes a feature. G-DISK go/refuse
# only.
CHECKPOINT_R30_FEATURE_BYTES = _c("P6.checkpoint_r30_feature_bytes", 256)

# ---------------------------------------------------------------------------------------------------
# P7  Room to work (owner ruling Q, OWNER_RULINGS_2026-10-06.md section Q, 2026-10-15; runs/room.py) and the RAM
# savings that cannot change a number (D:/treeroute/engine_next/RAM_TACTICS.md), added in this separate block at the
# end of the file. None of them can change a number of a run: the room values decide only WHEN a step starts (a
# step computes the same bytes whenever it starts), and the batch size only how many driver rows are decoded at once
# (the rows kept are the same at any batch size; tests/test_ram_tactics.py).
# origin: owner ruling Q1 ("re-checks every engine-constant interval"): one check is a psutil read, a gc pass and the
# working-set trim (well under a second), so 30 s notices a closed program within half a minute at no real cost.
ROOM_POLL_SECONDS = _c("P7.room_poll_seconds", 30)
# origin: owner ruling Q1 ("prints what it needs and the biggest programs using memory"): one note in the run log every
# 10 minutes while a check waits (the first note at once), so a night's wait writes about 70 lines, not 1,400.
ROOM_NOTE_SECONDS = _c("P7.room_note_seconds", 600)
# origin: owner ruling Q1 ("after an engine-constant maximum wait it refuses, as today"): 12 hours, one night away from
# the machine; a longer wait would hold the heavy-job lock and the run's temp files for a run nobody is freeing RAM for.
ROOM_MAX_WAIT_SECONDS = _c("P7.room_max_wait_seconds", 43200)
# origin: owner ruling Q1 ("the biggest programs using memory"): the five largest working sets name the programs to
# close on a 15.8 GB machine; a longer list adds lines, not decisions.
ROOM_TOP_PROGRAMS = _c("P7.room_top_programs", 5)
# origin: plumbing (RAM tactic 5): a driver file's needed columns are decoded this many rows at a time and only the
# reader's units' rows of each batch are kept (pipeline/data.py ColumnReader._read_drivers), instead of decoding the
# whole file first. The kept rows, their order, the schema and the values are the same at any batch size
# (tests/test_ram_tactics.py compares with the whole-file read); it bounds RAM only: 65,536 rows x 170 columns x 8 bytes
# is at most 89 MB a batch, against 0.5-1.1 GB for a full-size driver file of about a million rows.
READER_BATCH_ROWS = _c("P7.reader_batch_rows", 65536)
