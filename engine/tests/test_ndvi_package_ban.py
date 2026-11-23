"""The NDVI package's ban list as installed under owner rulings J (OWNER_RULINGS_2026-10-05.md section J, owner:
the author's answer, not quoted); tests may name problems.

What is checked (every check reads the package files and the engine's own checks; nothing is signed here):
  - the closed world through the engine: load_package, the feature outputs added (augment_package),
    package_spec (io.apply_verdicts) and the lineage stand-in (check_feature_lineage) all pass; one verdict per
    non-key catalog column (the 206 review-sheet columns and the feature script's 351 lag rows); no DRAFT stamp;
  - J1: every review-sheet column carries the verdict and reason of the base proposal
    (review/proposed/ndvi_ban_proposed.yaml) except exactly the J-changed columns (J_CHANGED);
  - J2 (a) the SPEI block and AMO stay banned (incomplete) and enter through one engineered lag-12 column each;
    J2 (b) deeprec_twsa is kept (with its lags) at its lag-3 bound, a store fact (assumed): R8 gives it lag 3 and
    the bound flows into its lags (the keep is refused if the store ever gives less); phenology_sos_doy stays
    banned as a co-product;
    J2 (c) snow_duration_days is kept at a one-year lag; J2 (d) epo and snow_cover_fraction are kept (the latter
    co-measured at lag 1) and their last-value gaps are disclosed; a kept epo or snow_cover_fraction enters only
    with the last-value rule wired into the pipeline (or while R8 refuses it);
  - J3 AS AMENDED (2026-10-05): livestock (aglw_*) is the yearly series, 'watch', kept and lagged one year by R8 on
    this monthly target, never frozen, its post-2021 rescaling disclosed; it feeds no feature output;
  - J4: features/build.py lags no banned base, and drops exactly the bases ban.yaml bans;
  - plan 1.4 family: every driver lag takes its base's verdict;
  - the timing facts are NOT signed: no catalog fact is 'verified', every disclosure is UNSIGNED, and the kept
    columns R8 refuses are exactly the 13 unsigned windows and their lags (a pin: when the owner signs a window,
    this test fails and names it, so the pin and ban.yaml's 'STILL TO SIGN' list are updated together);
  - ban.yaml's header counts are the file's.
proposed_fact_copy() builds, for tests/test_ndvi_package_derive.py, a temporary copy of the package whose store
catalog carries the PROPOSED (unsigned) timing facts of BAN_REVIEW_SUMMARY.md section 5 as 'assumed', so derive_all
can be exercised past R8 before the owner signs; the copy lives under the test's temp folder only.

REVISED 2026-10-06 for ruling L (OWNER_RULINGS_2026-10-05.md section L, the author's answer, not quoted): L1 signs the timing facts
(the 13 index windows {3, month, centred}: R8 lag 1 month, so R8 refuses no kept column any more; the J-assumed
facts; the aglw_* yearly facts; the co-measured answers of cloud_frequency_pct, snow_cover_fraction and burn_frac;
the six J2 a lag-12 windows), written fact_status 'assumed' + reviewed_by owner + date 2026-10-06 (the schema's
spelling of a signed fact); L3 bans the raw aglw_* and keeps each through <parent>_hold2021 (watch: the real 2021
layer held for 2022-2023); L2 and L4 leave NDVI's verdicts as they were (phenology banned, epo kept).
"""

import collections
import functools
import hashlib
import re
import shutil
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
import yaml

from conftest import ENGINE_DIR

NDVI = ENGINE_DIR / "datasets" / "ndvi"
DRAFT = ENGINE_DIR / "datasets" / "ndvi_draft"
PROPOSED = ENGINE_DIR / "datasets" / "review" / "proposed" / "ndvi_ban_proposed.yaml"
SHEET = ENGINE_DIR / "datasets" / "review" / "v2" / "ndvi_columns.csv"
PANEL_INCLUDE = "../_stores/monthly_panel_v170_schema_catalog.yaml"
MONTH = NS(kind="regular", length=1, unit="month")
RULINGS = "OWNER_RULINGS_2026-10-05.md"
KEY_ROLES = ("key_unit", "key_group", "key_time")

LIVESTOCK = ("aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats", "aglw_total_lsu")
LAG12_PARENTS = ("V06_spei_12m", "spei_01m", "spei_03m", "spei_06m", "spei_24m", "amo")
# the J changes against the J1 base: column -> (verdict, reason word or None for a non-ban)
J_CHANGED = {"snow_cover_fraction": ("watch", None),          # J2 (d); base: ban incomplete
             "epo": ("keep", None),                           # J2 (d); base: ban structural
             "deeprec_twsa": ("keep", None),                  # J2 (b); base: ban lookahead_unfixable
             "snow_duration_days": ("keep", None)}            # J2 (c); base: ban lookahead_unfixable
# ruling L3 (2026-10-06): the raw livestock columns banned again (base: ban post_window_snapshot; written
# 'incomplete' so the engine's lineage stand-in lets the hold columns through), kept through <parent>_hold2021
L_CHANGED = {c: ("ban", "incomplete") for c in LIVESTOCK}
HOLD = tuple("%s_hold2021" % c for c in LIVESTOCK)
SIGNATURE = ("assumed", "owner", "2026-10-06")
# owner ruling N (OWNER_RULINGS_2026-10-06.md N): S11 removes the sheet row ctx:climatology; S29 bans road_density;
# N1 gives pdo nino34's form {1, month, centred} + the ERSSTv5 reach of +2 months (lag 2; its lag-k columns 2 - k)
N_REMOVED = ("ctx:climatology",)
N_CHANGED = {"road_density": ("ban", "post_window_snapshot")}
N_SIGNED = "owner -- signed by the owner 2026-10-06 (ruling N,"
# the windows the owner signed {3, month, centred} (ruling L1 b); R8 refused them (G-LAG) before
SIGNED_WINDOWS = ("ao", "epo", "grace_lwe", "iod", "nao", "noi", "pdo", "pna", "sam", "soi", "tna", "tsa", "wp")
CONTEXT = ("ctx:sin1", "ctx:cos1", "ctx:sin2", "ctx:cos2", "ctx:top5:sph_kgkg_lag6", "ctx:top5:era5l_slhf_lag1",
           "ctx:top5:V07_total_ref_ET_mm_lag1", "ctx:top5:era5l_d2m", "ctx:top5:V01_mean_temp_C")

# The PROPOSED timing facts of BAN_REVIEW_SUMMARY.md section 5 (B: index windows; D: grace_lwe), NOT SIGNED: used only
# by proposed_fact_copy() for a temporary test copy, written there as fact_status 'assumed'.
_CENTRED = {"length": 1, "unit": "month", "align": "centred"}
PROPOSED_WINDOWS = {c: (dict(_CENTRED), "period_centre") for c in
                    ("soi", "tna", "tsa", "iod", "ao", "nao", "pna", "wp", "sam", "epo")}
PROPOSED_WINDOWS["noi"] = ({"length": 3, "unit": "month", "align": "centred"}, "period_centre")
PROPOSED_WINDOWS["pdo"] = (dict(_CENTRED, reach_after_max={"value": 2, "unit": "month"}), "period_centre")
PROPOSED_WINDOWS["grace_lwe"] = (dict(_CENTRED, reach_after_max={"value": 15, "unit": "day"},
                                      reach_before_max={"value": 15, "unit": "day"}), "period_centre")
# R8's lag of each on NDVI's target with those facts (timing.compute_lag)
PROPOSED_LAGS = {"soi": 0, "tna": 0, "tsa": 0, "iod": 0, "ao": 0, "nao": 0, "pna": 0, "wp": 0, "sam": 0, "epo": 0,
                 "noi": 1, "pdo": 2, "grace_lwe": 1}
# the J2 (b) bound the shared store catalog carries for deeprec_twsa (merged 2026-10-05, fact_status assumed)
DEEPREC_BOUND = {"value": 3.0, "unit": "month"}


def _v(x):
    return getattr(x, "value", x)


@functools.lru_cache(maxsize=None)
def _pkg():
    from treeroute.package.load import load_package

    return load_package(NDVI)


@functools.lru_cache(maxsize=None)
def _script():
    from treeroute.pipeline.data import load_hook

    return load_hook(NDVI, "features/build.py")


@functools.lru_cache(maxsize=None)
def _outputs():
    from treeroute.pipeline.data import feature_outputs

    return feature_outputs(_script())


@functools.lru_cache(maxsize=None)
def _aug():
    from treeroute.pipeline.data import augment_package

    return augment_package(_pkg(), _outputs())


@functools.lru_cache(maxsize=None)
def _proposed():
    return yaml.safe_load(PROPOSED.read_text(encoding="utf-8"))["verdicts"]


def _verdicts():
    return _pkg().ban.verdicts


def _target():
    t = _pkg().catalog.columns["V11_mean_ndvi"]
    return NS(name="V11_mean_ndvi", cadence=MONTH, stamp=t.stamp, window=t.window, computed_from=())


def _facts():
    out = {}
    for cat in _aug().stores.values():
        out.update(cat.columns)
    return out


def _lag(name, facts, co_measured=None):
    """(steps, floor reason) of R8's lag on NDVI's target, or the refusing rule."""
    from treeroute.timing import TimingRefusal, compute_lag

    view = NS(name=name, cadence=facts.cadence, stamp=facts.stamp, window=facts.window,
              fact_status=facts.fact_status, co_measured_with_target=co_measured)
    try:
        lag = compute_lag(view, _target(), MONTH, "nowcast")
        return lag.steps, lag.floor_reason
    except TimingRefusal as err:
        return err.rule


def _lag_rows():
    """{lag column: (base, k)} of the driver lags and {lag-12 column: parent} of the J2 (a) columns."""
    s = _script()
    family = {s.lag_column(b, k): (b, k) for k in s.LAG_ORDERS for b in s.LAG_BASES}
    lag12 = {s.lag_column(b, s.LAG12_ORDER): b for b in s.LAG12_BASES}
    return family, lag12


# ------------------------------------------------------------------------------------------------
def test_the_package_closes_the_world_through_the_engine():
    from treeroute.pipeline.data import check_feature_lineage, package_spec
    from treeroute.pipeline.draft import draft_status

    pkg = _pkg()
    assert not draft_status(pkg).is_draft and pkg.dataset.name == "ndvi"
    non_key = [c for c, f in pkg.catalog.columns.items() if f.role not in KEY_ROLES]
    assert sorted(_verdicts()) == sorted(non_key)
    family, lag12 = _lag_rows()
    sheet = list(_proposed())
    assert len(sheet) == 206
    assert set(non_key) == (set(sheet) - set(N_REMOVED)) | set(family) | set(lag12) | set(HOLD)
    assert len(family) == 345 and len(lag12) == 6
    spec = package_spec(_aug())                                     # io.apply_verdicts: the closed world
    notes = check_feature_lineage(_outputs(), _aug())               # no output built from a leak-banned source
    assert spec.context == CONTEXT
    assert len(spec.tree_features) == 492 and len(spec.listed_in_reports) == 37      # 493 before S29 (road_density)
    assert set(spec.feature_outputs) == set(_outputs())
    # the only recorded lineage notes: the J2 (a) columns and the L3 hold columns, built from their incomplete
    # (banned) parents
    want = dict({c: [b] for c, b in lag12.items()}, **{h: [c] for c, h in zip(LIVESTOCK, HOLD)})
    assert {c: [n.split(":")[0] for n in v] for c, v in notes.items()} == want


def test_every_sheet_column_keeps_the_j1_base_verdict_except_the_j_changes():
    import pandas as pd

    sheet = list(pd.read_csv(SHEET)["column"])
    assert sorted(sheet) == sorted(_proposed())
    differs = {}
    for c, base in _proposed().items():
        if c in N_REMOVED:
            assert c not in _verdicts(), c
            continue
        v = _verdicts()[c]
        # the verdict everywhere, and the reason WORD of a ban (a non-ban's reason is plain text: the J build
        # cites the ruling in some, e.g. the top-5 context columns' 'disclosed (ruling J1)')
        if _v(v.verdict) != base["verdict"] or (base["verdict"] == "ban" and v.reason != base["reason"]):
            differs[c] = (_v(v.verdict), v.reason)
    assert sorted(differs) == sorted(set(J_CHANGED) | set(L_CHANGED) | set(N_CHANGED))
    for c, (verdict, reason) in N_CHANGED.items():
        v = _verdicts()[c]
        assert (_v(v.verdict), v.reason) == (verdict, reason) and "ruling N" in v.evidence, c
    for c, (verdict, reason) in L_CHANGED.items():
        v = _verdicts()[c]
        assert _v(v.verdict) == verdict and v.reason == reason, (c, v)
        assert "ruling L3" in v.evidence and "post_window_snapshot" in v.evidence, c
    for c, (verdict, reason) in J_CHANGED.items():
        v = _verdicts()[c]
        assert _proposed()[c]["verdict"] == "ban", c                    # every J change reopens or relabels a ban
        assert _v(v.verdict) == verdict and (reason is None or v.reason == reason), (c, v)
        assert "OWNER RULING J" in v.evidence and RULINGS in v.evidence, c


def test_j2a_the_incomplete_parents_enter_through_one_lag12_column():
    s, facts = _script(), _facts()
    assert tuple(s.LAG12_BASES) == LAG12_PARENTS and s.LAG12_ORDER == 12
    for b in LAG12_PARENTS:
        v = _verdicts()[b]
        assert (_v(v.verdict), v.reason) == ("ban", "incomplete") and "J2 (a)" in v.evidence, b
        col = s.lag_column(b, 12)
        out = _outputs()[col]
        assert out.derived_from == (b,) or list(out.derived_from) == [b], col
        assert out.operation == "lag k=12 unit=month" and _lag(col, out) == (0, None), col
        assert _v(_verdicts()[col].verdict) == "keep" and "J2 (a)" in _verdicts()[col].evidence, col
        assert _pkg().catalog.columns[col].role == "engineered", col
        for k in (1, 2, 3, 6):                                       # the lags that read 2023 months are not built
            assert s.lag_column(b, k) not in _outputs() and s.lag_column(b, k) not in _pkg().catalog.columns
        # complete in every test year: a 2023 row reads the same month of 2022, inside the parent's record
        assert facts[b].observed_through is not None and str(facts[b].observed_through) >= "2022-12", b
    # AMO is detrended over its whole record: disclosed like a base period (INDEX_WINDOW_AUDIT.md row 9, Q43 a)
    e = {(x.kind, x.column): x for x in _pkg().exceptions.entries}[("provenance_flag", "amo_lag12")]
    assert "INDEX_WINDOW_AUDIT.md row 9" in e.reason and "S10" in e.reason
    assert e.owner.startswith(("UNSIGNED -- basis: ", N_SIGNED))             # ruling N S8 signs the true entries


def test_j2b_deeprec_is_kept_at_its_lag3_bound():
    """J2 (b) rules a cautious lag-3 bound. R8 reads windows from the store catalogs only; the shared store catalog
    carries reach_after_max {3, month} (assumed, unsigned), so the column and its lags are kept. If the store ever
    gave it less than lag 3, this keep would feed later DeepRec values than the ruling allows: refused here."""
    s, facts = _script(), _facts()
    lags = [s.lag_column("deeprec_twsa", k) for k in s.LAG_ORDERS]
    for c in ["deeprec_twsa"] + lags:
        assert _v(_verdicts()[c].verdict) == "keep", c
    assert "J2 (b)" in _verdicts()["deeprec_twsa"].evidence and "deeprec_twsa" in s.LAG_BASES
    f = facts["deeprec_twsa"]
    assert f.window.reach_after_max is not None
    assert {"value": float(f.window.reach_after_max.value), "unit": _v(f.window.reach_after_max.unit)} == DEEPREC_BOUND
    assert _v(f.fact_status) == "assumed"                              # a ruled bound: assumed, never verified
    assert _lag("deeprec_twsa", f) == (3, None), "the store fact no longer gives the J2 (b) lag 3"
    # the composed lags keep what is left of the bound (never less than 3 months in all)
    assert [_lag(c, facts[c])[0] for c in lags] == [2, 1, 0, 0, 0]
    v = _verdicts()["phenology_sos_doy"]
    assert (_v(v.verdict), v.reason) == ("ban", "coproduct") and "J2 (b)" in v.evidence


def test_j2c_snow_duration_days_is_kept_at_a_one_year_lag():
    f = _facts()["snow_duration_days"]
    assert _v(_verdicts()["snow_duration_days"].verdict) == "keep"
    assert (_v(f.cadence.unit), f.cadence.length) == ("year", 1)
    assert _lag("snow_duration_days", f) == (1, None)                # one step of its own (annual) cadence


def test_j2d_the_last_value_columns_are_kept_and_disclosed():
    s, facts, cols = _script(), _facts(), _pkg().catalog.columns
    # epo: kept with its lags; its window is signed (L1 b, {3, month, centred}): R8 lag 1 month
    assert _v(_verdicts()["epo"].verdict) == "keep" and "epo" in s.LAG_BASES
    assert all(_v(_verdicts()[s.lag_column("epo", k)].verdict) == "keep" for k in s.LAG_ORDERS)
    assert _lag("epo", facts["epo"]) == (1, None)
    # snow_cover_fraction: watch, same-sensor co-measured at lag 1
    assert _v(_verdicts()["snow_cover_fraction"].verdict) == "watch"
    assert cols["snow_cover_fraction"].co_measured_with_target is True
    assert "J2 (d)" in cols["snow_cover_fraction"].co_measured_evidence
    assert _lag("snow_cover_fraction", facts["snow_cover_fraction"], True) == (1, "co_measured")
    assert "snow_cover_fraction" not in s.LAG_BASES
    entries = {(e.kind, e.column): e for e in _pkg().exceptions.entries}
    for c in ("snow_cover_fraction", "epo"):
        e = entries[("disclosed_defect", c)]
        assert "J2 (d)" in e.owner and e.owner.startswith("UNSIGNED -- basis: "), c
    snow = entries[("disclosed_defect", "snow_cover_fraction")]
    assert "October 2022" in snow.reason and "OWNER DECISION OPEN" in snow.decision
    # the polar-night gaps longer than the last-value maximum fall to R30 (measured 2026-10-05): named, not hidden
    for g in ("taimyr_peninsula", "finnish_lapland", "alaska_north_slope", "yamal_peninsula", "canadian_arctic_nunavut"):
        assert g in snow.reason and g in _verdicts()["snow_cover_fraction"].evidence, g
    assert "PRESENCE" in snow.reason and "PRESENCE" in entries[("disclosed_defect", "epo")].reason
    assert "December" in entries[("disclosed_defect", "epo")].reason


PIPELINE_DIR = ENGINE_DIR / "treeroute" / "pipeline"


def _last_value_fill_runs():
    """True when a pipeline module CALLS fill_last_value (an ast Call node, not a docstring or a comment): the J2 d
    rule is wired into a run. Whether the call sits before R30 is the wiring task's own test."""
    import ast

    for path in PIPELINE_DIR.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                f = node.func
                name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
                if name == "fill_last_value":
                    return True
    return False


def test_epo_and_snow_cover_enter_only_with_the_last_value_fill():
    """J2 (d): the engine's last-value rule fills epo's December and snow cover's empty October 2022. Without the
    fill running, R30 zero-fills them (epo == 0 marks December; a November 2022 row reads 'no snow'). So a kept or
    watched epo / snow_cover_fraction (or any of epo's lags) needs either the fill wired into the pipeline or R8's
    refusal (G-LAG) of its window."""
    from treeroute.pipeline.data import package_spec

    s, facts, cols = _script(), _facts(), _pkg().catalog.columns
    spec = package_spec(_aug())
    runs = _last_value_fill_runs()
    for c in ["snow_cover_fraction", "epo"] + [s.lag_column("epo", k) for k in s.LAG_ORDERS]:
        if _v(_verdicts()[c].verdict) not in ("keep", "watch"):
            continue
        assert c in spec.tree_features, c                          # the fill acts on tree features only
        refused = not isinstance(_lag(c, facts[c], cols[c].co_measured_with_target), tuple)
        assert runs or refused, ("%s enters the trees but no pipeline module calls fill_last_value (J2 d): R30 "
                                 "would zero-fill its gaps" % c)


def test_j3_livestock_is_a_lagged_watch_column_never_frozen():
    """J3 AS AMENDED by the owner (2026-10-05) and ruling L3 (2026-10-06): the yearly AGLW series is kept LAGGED,
    verdict watch, through <parent>_hold2021 (the real 2021 layer held for 2022-2023); the raw columns are banned. On
    this monthly target R8 lags the hold one year, so a row carries only last year's mask; nothing is frozen (no R9);
    the store's post-2021 rows (the 2021 layer rescaled) stay disclosed."""
    from treeroute.pipeline.data import package_spec

    spec, facts = package_spec(_aug()), _facts()
    assert not spec.frozen
    entries = {(e.kind, e.column): e for e in _pkg().exceptions.entries}
    for c, h in zip(LIVESTOCK, HOLD):
        v = _verdicts()[c]
        assert (_v(v.verdict), v.reason) == ("ban", "incomplete") and "ruling L3" in v.evidence, c
        assert c not in spec.tree_features, c
        w = _verdicts()[h]
        assert _v(w.verdict) == "watch" and "L3" in w.reason + w.evidence, h
        assert h in spec.tree_features and h in spec.listed_in_reports and h not in spec.context, h
        assert _pkg().catalog.columns[h].role == "engineered", h
        f = facts[c]
        assert (_v(f.cadence.kind), f.cadence.length, _v(f.cadence.unit)) == ("regular", 1, "year"), c
        assert (_v(f.fact_status), f.reviewed_by, f.date) == SIGNATURE, c                      # L1 c
        o = facts[h]
        assert list(o.derived_from) == [c] and o.operation == "hold_last_observed through_year=2021 unit=year", h
        assert (_v(o.fact_status), o.reviewed_by, o.date) == SIGNATURE, h       # ruling N S5 signed the output
        assert _lag(h, o) == (1, None), h                                                       # year - 1
        assert _pkg().catalog.columns[c].role == "driver", c
        assert str(f.observed_through) == "2021", c                  # 2022-23 are the 2021 layer rescaled
        e = entries[("disclosed_defect", c)]
        assert e.owner.startswith("UNSIGNED -- basis: ") and "J3 as amended" in e.owner, c
        assert "INDIA" in e.reason and "EVERY region" in e.reason and "2023" in e.reason, c
        assert "fetch_livestock_extend.py:49-50" in e.reason and ":96-97" in e.reason, c
    assert not set(LIVESTOCK) & set(_script().LAG_BASES)
    assert sorted(o for o, f in _outputs().items() if set(f.derived_from) & set(LIVESTOCK)) == sorted(HOLD)


def test_j4_the_lag_bases_hold_no_banned_base():
    s = _script()
    banned = {b for b in s.RUN89_LAG_BASES if _v(_verdicts()[b].verdict) == "ban"}
    assert set(s.DROPPED_LAG_BASES) == banned and len(banned) == 18
    assert s.LAG_BASES == tuple(b for b in s.RUN89_LAG_BASES if b not in banned)
    for o, f in _outputs().items():
        for src in f.derived_from:
            v = _verdicts().get(src)
            if v is not None and _v(v.verdict) == "ban":
                assert (o in _lag_rows()[1] or o in HOLD) and v.reason == "incomplete", (o, src)   # J2 a, L3


def test_every_driver_lag_takes_its_base_verdict():
    family, _ = _lag_rows()
    for col, (base, k) in family.items():
        v, b = _verdicts()[col], _verdicts()[base]
        assert _v(v.verdict) == _v(b.verdict), col
        assert ("family of %s" % base) in v.evidence and ("lag k=%d unit=month" % k) in v.evidence, col
        assert _pkg().catalog.columns[col].role == "engineered", col
        # k >= 1 steps back already: ruling N S6 answered 'false' on every derived column (with its evidence)
        assert _pkg().catalog.columns[col].co_measured_with_target is False, col
        assert "ruling N" in _pkg().catalog.columns[col].co_measured_evidence, col


def test_cloud_frequency_is_co_measured_at_lag_one():
    f = _pkg().catalog.columns["cloud_frequency_pct"]
    assert f.co_measured_with_target is True and "Q3 a" in f.co_measured_evidence
    assert _lag("cloud_frequency_pct", _facts()["cloud_frequency_pct"], True) == (1, "co_measured")
    assert _v(_verdicts()["cloud_frequency_pct"].verdict) == "keep"
    assert _pkg().catalog.columns["burn_frac"].co_measured_with_target is True        # Q38 b, unchanged


def test_r8_refuses_no_kept_column_after_the_l1_signatures():
    """Ruling L1 (b), 2026-10-06: the 13 windows R8 refused (G-LAG) are signed {3, month, centred}: R8 now lags every
    kept column (each index column 1 month; its lags what is left of that reach)."""
    from treeroute.pipeline.data import package_spec

    spec, facts, cols = package_spec(_aug()), _facts(), _pkg().catalog.columns
    refused = {}
    for c in spec.tree_features + spec.context:
        f = facts[c]
        if _v(f.cadence.kind) in ("static", "epoch"):
            continue
        got = _lag(c, f, cols[c].co_measured_with_target)
        if not isinstance(got, tuple):
            refused[c] = got
    s = _script()
    assert refused == {}
    for b in SIGNED_WINDOWS:
        f = facts[b]
        n1 = b == "pdo"                                              # ruling N1: nino34's form, lag 2
        assert (f.window.length, _v(f.window.unit), _v(f.window.align)) == (1 if n1 else 3, "month", "centred"), b
        assert (_v(f.fact_status), f.reviewed_by, f.date) == SIGNATURE, b
        assert _lag(b, f, cols[b].co_measured_with_target) == (2 if n1 else 1, None), b
        want = [max(0, (2 if n1 else 1) - k) for k in s.LAG_ORDERS]
        assert [_lag(s.lag_column(b, k), facts[s.lag_column(b, k)])[0] for k in s.LAG_ORDERS] == want, b
    header = (NDVI / "ban.yaml").read_text(encoding="utf-8").split("\nverdicts:\n", 1)[0]
    assert "REVISED 2026-10-06 under ruling L" in header


def test_only_the_owners_l1_signatures_are_marked_signed():
    """Nothing is 'verified'. The only signed facts are ruling L1's (fact_status 'assumed' + reviewed_by owner + date
    2026-10-06): the package catalog's three co-measured answers, and in the store facts the index windows, the
    J-assumed facts, the aglw_* yearly facts, burn_frac's reach and the six lag-12 windows. The L3 hold columns copy
    their parent's fact_status but not its signature (L1 does not list them). Every disclosure stays UNSIGNED."""
    pkg = _pkg()
    assert pkg.dataset.owner.startswith("UNSIGNED")
    signed_package = {"cloud_frequency_pct", "snow_cover_fraction", "burn_frac"}
    for c, f in pkg.catalog.columns.items():
        assert _v(f.fact_status) in ("unverified", "assumed"), c
        if c in signed_package:
            assert (_v(f.fact_status), f.reviewed_by, f.date) == SIGNATURE, c
        else:
            assert f.reviewed_by is None, c
    for e in pkg.exceptions.entries:                     # ruling N S8 signed the entries that were already true
        assert e.owner.startswith(("UNSIGNED -- basis: ", N_SIGNED)), (e.kind, e.column)
    s = _script()
    signed_store = (set(SIGNED_WINDOWS) | set(LIVESTOCK)
                    | {"deeprec_twsa", "nitrogen_gkg", "V30_soil_moisture_pct", "tni", "burn_frac", "phenology_sos_doy"}
                    | {s.lag_column(b, s.LAG12_ORDER) for b in s.LAG12_BASES})
    # UPDATED 2026-10-06: ruling N (S1-S6) signed further store facts and every feature-script output; each signed
    # fact names ruling L1 or ruling N
    for c, f in _facts().items():
        assert _v(f.fact_status) != "verified", c
        if c in signed_store:
            assert (_v(f.fact_status), f.reviewed_by, f.date) == SIGNATURE, c
        assert f.reviewed_by is None or ((_v(f.fact_status), f.reviewed_by, f.date) == SIGNATURE
                                         and ("ruling N" in f.provenance or "L1" in f.provenance)), c
    # tni's R-B window: signed by L1 (a); its verdicts say so
    assert (_v(_facts()["tni"].fact_status), _facts()["tni"].reviewed_by) == ("assumed", "owner")
    assert all("signed by the owner 2026-10-06 (ruling L1 a)" in _verdicts()[c].reason
               for c in ["tni"] + [_script().lag_column("tni", k) for k in _script().LAG_ORDERS])


def test_the_header_counts_are_the_files():
    text = (NDVI / "ban.yaml").read_text(encoding="utf-8")

    def counts(vs):
        out = collections.Counter(_v(v.verdict) if _v(v.verdict) != "ban" else "ban:" + v.reason for v in vs)
        return dict(out)

    def parsed(line):
        return {k: int(n) for k, n in re.findall(r"([a-z_:]+) (\d+)", line)}

    sheet_line = re.search(r"^# Verdict counts \(206 sheet columns\): (.*)$", text, re.M).group(1)
    all_line = re.search(r"^# Verdict counts \(all (\d+) entries\): (.*)$", text, re.M)
    assert parsed(sheet_line) == counts(_verdicts()[c] for c in _proposed() if c not in N_REMOVED)
    assert int(all_line.group(1)) == len(_verdicts()) == 562          # 557 + the 6 L3 hold columns - S11's row
    assert parsed(all_line.group(2)) == counts(_verdicts().values())


def test_the_proposed_facts_give_the_proposed_lags():
    """The PROPOSED (unsigned) facts that proposed_fact_copy() writes into the test copy give the lags the
    proposal states (BAN_REVIEW_SUMMARY.md section 5; deeprec_twsa: J2 b)."""
    from treeroute.package.schema import StoreColumn

    facts = _facts()
    for c, (window, stamp) in PROPOSED_WINDOWS.items():
        f = StoreColumn.model_validate(dict(facts[c].model_dump(exclude_none=True), window=window, stamp=stamp,
                                            fact_status="assumed"))
        assert _lag(c, f, _pkg().catalog.columns[c].co_measured_with_target) == (PROPOSED_LAGS[c], None), c


# ------------------------------------------------------------------------------------------------
# a temporary copy with the PROPOSED timing facts (for tests/test_ndvi_package_derive.py)
PACKAGE_FILES = ("dataset.yaml", "catalog.yaml", "ban.yaml", "split.yaml", "exceptions.yaml", "AUDIT_CHECKLIST.md",
                 "expected_derived.json", "features/build.py", "ingest/target_reader.py", "ingest/build_static.py")


def proposed_fact_copy(dest):
    """A copy of datasets/ndvi under `dest`/datasets/ndvi whose shared store catalog copy carries the PROPOSED timing
    facts (PROPOSED_WINDOWS, fact_status 'assumed'; NOT signed), with dataset.yaml's include sha256 values set to the
    copies (the other included catalogs are copied unchanged), and the draft's static table (written by the
    byte-identical builder) as its data/static table. Returns the copy's package root. Read-only on everything
    outside `dest`."""
    from treeroute.package import load as L

    dest = Path(dest)
    root = dest / "datasets" / "ndvi"
    stores = dest / "datasets" / "_stores"
    for rel in PACKAGE_FILES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(NDVI / rel), str(root / rel))
    static = DRAFT / "data" / "static" / "part-0.parquet"
    if static.is_file():
        (root / "data" / "static").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(static), str(root / "data" / "static" / "part-0.parquet"))
    stores.mkdir(parents=True, exist_ok=True)
    dataset_text = (root / "dataset.yaml").read_text(encoding="utf-8")
    from treeroute.package.load import load_dataset_file

    for inc in load_dataset_file(NDVI).includes:
        src = (NDVI / inc.path).resolve()
        name = Path(inc.path).name
        if inc.path != PANEL_INCLUDE:
            shutil.copyfile(str(src), str(stores / name))
            new_sha = hashlib.sha256((stores / name).read_bytes()).hexdigest()
            assert dataset_text.count(inc.sha256) == 1
            dataset_text = dataset_text.replace(inc.sha256, new_sha)
            continue
        cat = yaml.load(src.read_text(encoding="utf-8"), Loader=L._UniqueKeyLoader)
        for c, (window, stamp) in PROPOSED_WINDOWS.items():
            cat["columns"][c]["window"] = window
            cat["columns"][c]["stamp"] = stamp
            cat["columns"][c]["fact_status"] = "assumed"
        text = ("# TEST COPY (tests/test_ndvi_package_ban.py::proposed_fact_copy): the shared store catalog with the "
                "PROPOSED, UNSIGNED timing facts of BAN_REVIEW_SUMMARY.md section 5 as 'assumed'.\n"
                + yaml.safe_dump(cat, sort_keys=False, width=120, allow_unicode=False))
        (stores / name).write_text(text, encoding="utf-8")
        new_sha = hashlib.sha256((stores / name).read_bytes()).hexdigest()
        assert dataset_text.count(inc.sha256) == 1
        dataset_text = dataset_text.replace(inc.sha256, new_sha)
    (root / "dataset.yaml").write_text(dataset_text, encoding="utf-8")
    return root


def test_the_proposed_fact_copy_loads_and_r8_lags_every_kept_column(tmp_path):
    from treeroute.package.load import load_package
    from treeroute.pipeline.data import augment_package, feature_outputs, load_hook, package_spec
    from treeroute.timing import compute_lag

    root = proposed_fact_copy(tmp_path)
    pkg = load_package(root)
    hook = load_hook(root, "features/build.py")
    aug = augment_package(pkg, feature_outputs(hook))
    spec = package_spec(aug)
    facts = {}
    for cat in aug.stores.values():
        facts.update(cat.columns)
    t = pkg.catalog.columns["V11_mean_ndvi"]
    tgt = NS(name="V11_mean_ndvi", cadence=MONTH, stamp=t.stamp, window=t.window, computed_from=())
    lags = {}
    for c in spec.tree_features + spec.context:
        f = facts[c]
        if _v(f.cadence.kind) in ("static", "epoch"):
            continue
        view = NS(name=c, cadence=f.cadence, stamp=f.stamp, window=f.window, fact_status=f.fact_status,
                  co_measured_with_target=pkg.catalog.columns[c].co_measured_with_target)
        lags[c] = compute_lag(view, tgt, MONTH, "nowcast").steps        # no refusal left
    assert {c: lags[c] for c in PROPOSED_LAGS} == PROPOSED_LAGS and lags["deeprec_twsa"] == 3
    assert len(spec.tree_features) == 492                               # the same kept set as the package
    assert all(lags[c] == 1 for c in HOLD)                              # L3 holds: one step of a year
    assert (root / "ban.yaml").read_bytes() == (NDVI / "ban.yaml").read_bytes()
