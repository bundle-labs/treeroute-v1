"""The fire package's INSTALLED Q34 ban list (OWNER_RULINGS_2026-10-05.md section J) and its J2 (a) lag-12 columns.

Tests may name problems, columns and drives (G-NONAMES scans engine code only). Package files and synthetic frames
only: no D: store is read here (tests/test_fire_package_derive.py and test_fire_package_data.py read the stores).

What is pinned:
  - ban.yaml is the review's verdicts (engine/datasets/review/proposed/fire_ban_proposed.yaml, adopted by J1) word for
    word, except the rows the owner's later rules change: J3 AS AMENDED (livestock 'watch': the yearly series lagged
    one year by R8, never frozen), J2 (a) (six lag-12 columns kept, the raw parents still banned), J2 (b)
    (deeprec_twsa, phenology_sos_doy kept at their assumed store bounds), J2 (c) (snow_duration_days kept), J2 (d)
    (epo and snow_cover_fraction conditional until the pipeline runs the last-value fill; epo also waits for its
    window), and J4's note on the soil rows (nitrogen_gkg is stored in cg/kg);
  - the switchable conditionals: the 9 fire-history columns wait for the every-unit store, and each switches to the
    verdict its reason names (and the header lists); snow_cover_fraction and epo wait for the last-value fill, and
    either can be kept only once a pipeline module calls it;
  - the lag-12 columns: facts composed from the parents' store facts (R8 lag 0), values read from the SAME unit 12
    calendar steps earlier, never another row;
  - every kept column has store facts; the only R8 refusals are the unsigned windows the header names (G-LAG), so
    derive_all on the package refuses loudly at R8 until the owner signs them;
  - no timing fact is marked signed or verified on the owner's behalf; the disclosures of the kept defects.

REVISED 2026-10-06 for ruling L (OWNER_RULINGS_2026-10-05.md section L, the author's answer, not quoted): L1 signs the timing facts (the
13 index windows {3, month, centred}: R8 lag 1 month, so no kept column is refused any more; the J-assumed facts, the
aglw_* yearly facts, cloud_frequency_pct's co-measured answer and the lag-12 windows), written fact_status 'assumed' +
reviewed_by owner + date 2026-10-06 (the schema's spelling of a signed fact); L2 phenology_sos_doy conditional (Y0
2003); L3 the raw aglw_* banned and kept through <parent>_hold2021 (watch); L4 epo keep, wbal_roll24 banned. Each
L row's evidence starts with the ruling and ends with the review's evidence, as the J rows do.
"""

import re
from collections import Counter
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest
import yaml

from conftest import ENGINE_DIR

DATASETS = ENGINE_DIR / "datasets"
FIRE_DIR = DATASETS / "fire"
PROPOSED = DATASETS / "review" / "proposed" / "fire_ban_proposed.yaml"
J = "OWNER_RULINGS_2026-10-05.md"
KEY_ROLES = ("key_unit", "key_group", "key_time")
MONTH = NS(kind="regular", length=1, unit="month")

LIVESTOCK = ("aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats", "aglw_total_lsu")
LAG12_PARENTS = ("V06_spei_12m", "spei_01m", "spei_03m", "spei_06m", "spei_24m", "amo")
LAG12 = tuple("%s_lag12" % p for p in LAG12_PARENTS)
# the rows J2 / J3 change, with the verdict each rule gives (J2 d: conditional until the last-value fill runs)
RULED = {"deeprec_twsa": ("keep", "J2 (b)"), "phenology_sos_doy": ("keep", "J2 (b)"),
         "snow_duration_days": ("keep", "J2 (c)"), "epo": ("conditional", "J2 (d)"),
         "snow_cover_fraction": ("conditional", "J2 (d)")}
RULED.update({c: ("watch", "J3") for c in LIVESTOCK})            # J3 AMENDED 2026-10-05: watch, never freeze
# ruling L (2026-10-06) moves these rows again: {column: (verdict, rule)}; wbal_roll24 was a review keep
RULED.update({"phenology_sos_doy": ("conditional", "L2"), "epo": ("keep", "L4")})
RULED.update({c: ("ban", "L3") for c in LIVESTOCK})
L4_FROM_KEEP = {"wbal_roll24": ("ban", "L4")}
HOLD = tuple("%s_hold2021" % c for c in LIVESTOCK)               # L3: the real 2021 layer held for 2022-2023
SIGNATURE = ("assumed", "owner", "2026-10-06")
# the 13 index windows the owner signed {3, month, centred} (L1 b); on fire all 13 are kept (grace_lwe watch)
SIGNED_INDEX_WINDOWS = ("soi", "tna", "tsa", "iod", "noi", "ao", "nao", "pna", "wp", "sam", "pdo", "epo", "grace_lwe")
# J4: the review's soil reasons carry a stale range note ('nitrogen_gkg max 267 ... impossible'); each keeps the
# review's text word for word and gains this note
J4_NOTE = (" | J4 (OWNER_RULINGS_2026-10-05.md): nitrogen_gkg is stored in cg/kg, so its 267 is 26.7 g/kg, not an "
           "impossible value; units and legal range corrected in the store catalog (fact_status assumed)")
# lag-12 columns moved keep -> watch by the year-clock screen (ban.yaml header), as spi_12m and spi_24m
LAG12_WATCH = ("V06_spei_12m_lag12", "spei_24m_lag12")
# the 9 fire-history columns that wait for the every-unit store (J1, Q5), with the verdict after the switch
HISTORY_SWITCH = {"tslf_months": "watch", "tslf_censored": "watch", "n_burns_12mo": "keep", "n_burns_60mo": "watch",
                  "burn_rate_120mo": "keep", "nbr25km_12mo_lag3": "keep", "nbr75km_12mo_lag3": "keep",
                  "nbr25km_12mo_lag6": "keep", "nbr75km_12mo_lag6": "keep"}
HISTORY_CATALOG = "ingest/fire_history_store_catalog.yaml"
# owner ruling N S9 a (OWNER_RULINGS_2026-10-06.md N): the owner-built store (D:/fire_history_lag2) is declared; it does
# not build the four lag-1 rings (they read label t-1, ruling R-D b), so their review rows left the package
RINGS_LAG1 = ("nbr25km_lag1", "nbr25km_12mo_lag1", "nbr75km_lag1", "nbr75km_12mo_lag1")
# the store-catalog columns ruling N re-ruled on fire: S27 bans travel_time, S29 road_density (post_window_snapshot)
N_BANNED = ("travel_time", "road_density")
# kept columns whose store window is still unknown with no signed bound: none since ruling L1 (b), 2026-10-06 (the
# set could only shrink as windows were signed; it is empty now)
AWAITING_WINDOW_SIGNATURE = ()
PIPELINE_DIR = ENGINE_DIR / "treeroute" / "pipeline"


@pytest.fixture(scope="module")
def fire():
    from treeroute.package.load import load_package

    return load_package(FIRE_DIR)


@pytest.fixture(scope="module")
def proposed():
    return yaml.safe_load(PROPOSED.read_text(encoding="utf-8"))["verdicts"]


@pytest.fixture(scope="module")
def hook():
    from treeroute.pipeline import data as D

    return D.load_hook(FIRE_DIR, D.FEATURE_SCRIPT)


@pytest.fixture(scope="module")
def augmented(fire, hook):
    from treeroute.pipeline import data as D

    return D.augment_package(fire, D.feature_outputs(hook))


def _dump(v):
    return {"verdict": v.verdict, "reason": v.reason, "evidence": v.evidence}


def _store_facts(pkg):
    out = {}
    for cat in pkg.stores.values():
        out.update(cat.columns)
    return out


def _target(pkg):
    (name, tf), = [(c, f) for c, f in pkg.catalog.columns.items() if f.role == "target"]
    return NS(name=name, cadence=MONTH, stamp=tf.stamp, window=tf.window, computed_from=())


def _lags(augmented):
    """{kept column: Lag} from R8's compute_lag, and {kept column: refusal rule} for the refused ones."""
    from treeroute.derive.orchestrate import _Facts
    from treeroute.timing import TimingRefusal, compute_lag

    facts = _Facts(augmented)
    lags, refused = {}, {}
    for c in facts.kept:
        try:
            lags[c] = compute_lag(facts.kept_facts[c], facts.target, MONTH, "nowcast")
        except TimingRefusal as err:
            refused[c] = err.rule
    return facts, lags, refused


def _history_store_declared(pkg):
    """True when the package includes the generated catalog of the history store rebuilt at label lag 2."""
    cat = pkg.stores.get(HISTORY_CATALOG)
    if cat is None:
        return False
    return all(c in cat.columns and cat.columns[c].reads_target and cat.columns[c].window.length == 2
               for c in HISTORY_SWITCH)


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


# ------------------------------------------------------------------------------------------------
# ban.yaml against the review and the rulings
def test_the_installed_verdicts_are_the_review_with_the_j_rulings(fire, proposed):
    installed = fire.ban.verdicts
    assert set(installed) == (set(proposed) - set(RINGS_LAG1)) | set(LAG12) | set(HOLD)
    assert not set(RINGS_LAG1) & set(fire.catalog.columns)                   # ruling N S9 a: not built
    for c in N_BANNED:                                                         # ruling N S27, S29
        assert (installed[c].verdict, installed[c].reason) == ("ban", "post_window_snapshot"), c
        assert "ruling N" in installed[c].evidence, c
    j4 = {c for c, v in proposed.items() if "nitrogen_gkg max 267" in v["reason"]}
    assert len(j4) == 10 and "nitrogen_gkg" in j4
    for c in sorted(j4):                                                # J4: the review's text plus one note
        assert _dump(installed[c]) == dict(proposed[c], reason=proposed[c]["reason"] + J4_NOTE), c
    untouched = (set(proposed) - set(RULED) - set(LAG12_PARENTS) - set(HISTORY_SWITCH) - j4 - set(L4_FROM_KEEP)
                 - set(RINGS_LAG1) - set(N_BANNED))
    for c in sorted(untouched):
        assert _dump(installed[c]) == proposed[c], c                    # word for word
    for c in LAG12_PARENTS:                                             # J2 (a): the raw parent stays banned
        v = installed[c]
        assert (v.verdict, v.reason) == ("ban", "incomplete") == (proposed[c]["verdict"], proposed[c]["reason"])
        assert v.evidence.startswith("%s J2 (a)" % J) and v.evidence.endswith(proposed[c]["evidence"]), c
    for c in LAG12:
        v = installed[c]
        assert v.verdict == ("watch" if c in LAG12_WATCH else "keep"), c
        if c in LAG12_WATCH:                                           # the screen's count is in the reason
            assert "WATCH: it tracks the year in" in v.reason and "year-clock screen" in v.evidence, c
        assert "J2 (a)" in v.reason and v.evidence.startswith("%s J2 (a)" % J), c
    for c, (verdict, rule) in list(RULED.items()) + list(L4_FROM_KEEP.items()):
        v = installed[c]
        assert proposed[c]["verdict"] == ("keep" if c in L4_FROM_KEEP else "ban"), c   # the review's verdict
        assert v.verdict == verdict or (verdict == "conditional" and v.verdict == "keep"), (c, v.verdict)
        assert v.evidence.startswith("%s %s" % (J, rule)), c
        assert v.evidence.endswith("review: %s" % proposed[c]["evidence"]), c    # the review's evidence kept
    # the FireCCI trio keep the review's ban; their twin role (catalog.yaml) forces it
    for c in ("V20_burned_binary", "burn_month_count", "burn_doy_mean"):
        assert _dump(installed[c]) == proposed[c]
        assert fire.catalog.columns[c].role == "target_twin"
    # the amended J3 withdrew the only freeze: no fire column is frozen (the pipeline refuses 'freeze', R9)
    assert not [c for c, v in installed.items() if v.verdict == "freeze"]


def test_the_header_names_every_change_and_the_counts_are_current(fire):
    text = (FIRE_DIR / "ban.yaml").read_text(encoding="utf-8")
    header = text.split("\nverdicts:\n", 1)[0]
    assert "INSTALLED 2026-10-05" in header and "fire_ban_proposed.yaml" in header
    for c in list(RULED) + list(LAG12_PARENTS) + list(L4_FROM_KEEP):
        assert c in header, c
    assert "REVISED 2026-10-06 under ruling L" in header
    counts = Counter(v.verdict + (":" + v.reason if v.verdict == "ban" else "") for v in fire.ban.verdicts.values())
    expected = ", ".join("%s %d" % (k, n) for k, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    assert "# Counts: %s\n" % expected in header + "\n"
    assert "%d verdicts" % len(fire.ban.verdicts) in header


# ------------------------------------------------------------------------------------------------
# the switchable conditionals
def test_the_history_columns_wait_for_the_every_unit_store_and_name_their_switch(fire):
    text = (FIRE_DIR / "ban.yaml").read_text(encoding="utf-8")
    header = text.split("\nverdicts:\n", 1)[0]
    listed = dict(re.findall(r"^#   (\w+)\s+-> (keep|watch)$", header, flags=re.M))
    assert listed == HISTORY_SWITCH
    declared = _history_store_declared(fire)
    for c, after in HISTORY_SWITCH.items():
        v = fire.ban.verdicts[c]
        if v.verdict == "conditional":
            assert "After the store is built and included: %s." % after in v.reason, c
        else:
            assert declared, "%s is %s but no rebuilt history store is declared (R8 would refuse it)" % (c, v.verdict)
            assert v.verdict == after, c
    # the other target-derived rows stay banned: lag-1 rings (R-D b), single-month rings, a sparse own lag, a month key
    assert not set(RINGS_LAG1) & set(fire.ban.verdicts)                 # ruling N S9 a: not built, no row
    for c in ("nbr25km_lag3", "nbr75km_lag3", "nbr25km_lag6", "nbr75km_lag6", "last_burn_size"):
        assert (fire.ban.verdicts[c].verdict, fire.ban.verdicts[c].reason) == ("ban", "target_derived"), c
    assert (fire.ban.verdicts["last_burn_month"].verdict, fire.ban.verdicts["last_burn_month"].reason) == \
        ("ban", "structural")


def test_epo_and_snow_cover_enter_only_with_the_last_value_fill(fire, augmented):
    """J2 (d): the engine's last-value rule fills epo's December and snow cover's empty October 2022. Without the fill
    running, R30 zero-fills them (epo == 0 marks December). Ruling L4 keeps epo (the fill is wired and L1 b signed its
    window: lag 1 month); snow_cover_fraction stays 'conditional', its reason naming its switch."""
    _, lags, refused = _lags(augmented)
    runs = _last_value_fill_runs()
    for c in ("epo", "snow_cover_fraction"):
        v = fire.ban.verdicts[c]
        assert "J2 (d)" in v.reason or "J2 d" in v.reason, c
        if v.verdict in ("keep", "watch"):
            assert runs, "%s is kept but no pipeline module calls fill_last_value (J2 d): R30 would zero-fill" % c
    assert "SWITCH to keep" in fire.ban.verdicts["snow_cover_fraction"].reason
    epo = fire.ban.verdicts["epo"]
    assert epo.verdict == "keep" and "L4" in epo.reason and "epo" not in refused and lags["epo"].steps == 1
    # snow cover is co-measured (J2 d; MODIS, the target's sensor): R8 gives it at least one step once it enters
    from treeroute.timing import compute_lag

    pkg_col = fire.catalog.columns["snow_cover_fraction"]
    assert pkg_col.co_measured_with_target is True and "J2 (d)" in pkg_col.co_measured_evidence
    s = _store_facts(fire)["snow_cover_fraction"]
    view = NS(name="snow_cover_fraction", cadence=s.cadence, stamp=s.stamp, window=s.window,
              fact_status=s.fact_status, co_measured_with_target=True)
    assert compute_lag(view, _target(fire), MONTH, "nowcast").steps == 1


# ------------------------------------------------------------------------------------------------
# J3 and J2 (b), (c): the facts the verdicts rely on
def test_livestock_is_a_lagged_watch_column_never_frozen(fire, augmented, hook):
    """J3 AS AMENDED (2026-10-05) and ruling L3 (2026-10-06): the raw aglw_* are banned and the yearly AGLW series
    enters the trees through <parent>_hold2021 ('watch'), R8 lagging it one year on this monthly target; nothing is
    frozen (no R9), and fire never reads a post-2021 (rescaled) layer either way."""
    import json

    from treeroute.pipeline import data as D

    spec = D.package_spec(augmented)
    assert not spec.frozen
    assert not set(LIVESTOCK) & set(spec.tree_features) and set(HOLD) <= set(spec.tree_features)
    _, lags, refused = _lags(augmented)
    store = _store_facts(fire)
    outputs = D.feature_outputs(hook)
    y_end = json.loads((FIRE_DIR / "expected_derived.json").read_text(encoding="utf-8"))["R3_R7_windows"]["y_end"]
    for c, h in zip(LIVESTOCK, HOLD):
        assert (fire.ban.verdicts[c].verdict, fire.ban.verdicts[c].reason) == ("ban", "incomplete"), c
        assert "post_window_snapshot" in fire.ban.verdicts[c].evidence and h in fire.ban.verdicts[c].evidence, c
        assert fire.ban.verdicts[h].verdict == "watch" and fire.catalog.columns[h].role == "engineered", h
        assert h not in refused and (lags[h].steps, lags[h].column_cadence.unit) == (1, "year"), h
        f = store[c]
        assert (f.cadence.kind, f.cadence.length, f.cadence.unit) == ("regular", 1, "year"), c
        # the last real layer is 2021 (2022-23 are the 2021 layer rescaled): at a 1-year lag the latest row fire
        # reads (y_end 2022) sees the 2021 layer, and lead feature rows are earlier still
        assert f.observed_through == "2021" and y_end - lags[h].steps <= int(f.observed_through), c
        assert (f.fact_status, f.reviewed_by, f.date) == SIGNATURE, c                  # L1 c
        o = outputs[h]
        assert o.derived_from == [c] and o.operation == "hold_last_observed through_year=2021 unit=year", h
        assert (o.cadence, o.window, o.stamp, o.observed_through) == (f.cadence, f.window, f.stamp, "2021"), h
        # L3 builds the hold; ruling N S5 signed the feature-script outputs' facts
        assert (o.fact_status, o.reviewed_by, o.date) == SIGNATURE, h


def test_the_j2b_and_j2c_lags_come_from_the_store_facts(fire, augmented):
    from treeroute.derive.rules import derive_r04_first_year

    _, lags, refused = _lags(augmented)
    assert (lags["deeprec_twsa"].steps, lags["deeprec_twsa"].column_cadence.unit) == (3, "month")
    assert "phenology_sos_doy" not in lags                             # L2: out (conditional)
    assert (lags["snow_duration_days"].steps, lags["snow_duration_days"].column_cadence.unit) == (1, "year")
    store = _store_facts(fire)
    for c in ("deeprec_twsa", "phenology_sos_doy"):
        assert (store[c].fact_status, store[c].reviewed_by, store[c].date) == SIGNATURE, c     # L1 a, never verified
    # phenology_sos_doy's 2-year lag would set Y0 2004 alone (J5); ruling L2 holds it out, so Y0 is 2003
    v = fire.ban.verdicts["phenology_sos_doy"]
    assert v.verdict == "conditional" and "L2" in v.reason and "Y0 stays 2003" in v.reason
    assert derive_r04_first_year(2002, lags).value == 2003


# ------------------------------------------------------------------------------------------------
# the J2 (a) lag-12 columns
def test_the_lag12_facts_are_composed_from_the_parents(fire, hook, augmented):
    from treeroute.pipeline import data as D
    from treeroute.timing import compute_lag

    store = _store_facts(fire)
    outputs = D.feature_outputs(hook)
    assert tuple(hook.LAG12_COLUMNS) == LAG12 and tuple(hook.LAG12_BASES) == LAG12_PARENTS
    span = {}
    for parent, col in zip(LAG12_PARENTS, LAG12):
        f, p = outputs[col], store[parent]
        assert fire.catalog.columns[col].role == "engineered"
        assert list(f.derived_from) == [parent] and f.operation == "lag k=12 unit=month" and f.reads_target is False
        assert (f.dtype, f.units, f.scope, f.legal_range) == (p.dtype, p.units, p.scope, p.legal_range), col
        assert (f.stamp, f.window.align, f.window.unit, f.window.reach_after_max) == \
            ("period_end", "backward", "month", None), col
        assert (f.fact_status, f.reviewed_by, f.date) == SIGNATURE, col       # L1 c: the composed window, signed
        span[parent] = int(f.window.length)
        view = NS(name=col, cadence=f.cadence, stamp=f.stamp, window=f.window, fact_status=f.fact_status,
                  co_measured_with_target=fire.catalog.columns[col].co_measured_with_target)
        assert compute_lag(view, _target(fire), MONTH, "nowcast").steps == 0, col
    # the parent's own months plus 12 (trailing windows of 1, 3, 6, 12 and 24 months; amo a plain month)
    assert span == {"V06_spei_12m": 24, "spei_01m": 13, "spei_03m": 15, "spei_06m": 18, "spei_24m": 36, "amo": 13}
    # the parents are banned for a non-leak reason: the lineage check records them and does not refuse
    notes = D.check_feature_lineage(outputs, augmented)
    for parent, col in zip(LAG12_PARENTS, LAG12):
        assert notes[col] == ["%s: ban (incomplete)" % parent]


def _frame(rows):
    out = pd.DataFrame(rows, columns=["cell_id", "year", "month"])
    out["region"] = "g"
    out["_step"] = out["year"] * 12 + out["month"]
    out["lat"] = 10.0
    for c in LIVESTOCK:                       # the L3 hold sources (annual values: the year itself plus an offset)
        out[c] = out["year"] * 1.0 + LIVESTOCK.index(c) / 10.0
    return out


KEYS = {"unit": "cell_id", "group": "region", "step": "_step", "time": {"year": "year", "month": "month"}}


def test_the_lag12_build_reads_the_same_unit_12_calendar_steps_earlier(hook):
    rows = [("a", 2003 + (m - 1) // 12, (m - 1) % 12 + 1) for m in range(1, 31) if m != 15]   # a: 29 months
    rows += [("b", 2003 + (m - 1) // 12, (m - 1) % 12 + 1) for m in range(7, 25)]            # b: 18 months
    frame = _frame(rows)
    rng_free = np.arange(len(frame), dtype=np.float64)
    for i, parent in enumerate(LAG12_PARENTS):
        frame[parent] = rng_free * 10 + i
    frame.loc[3, "amo"] = np.nan                     # a missing value stays missing 12 months later
    out = hook.build(frame, KEYS)
    assert list(out.columns) == list(hook.OUTPUTS) and out.index.equals(frame.index)
    at = {(u, s): k for k, (u, s) in enumerate(zip(frame["cell_id"], frame["_step"]))}
    for k, (u, s) in enumerate(zip(frame["cell_id"], frame["_step"])):
        src = at.get((u, s - 12))
        for parent, col in zip(LAG12_PARENTS, LAG12):
            got = out[col].iloc[k]
            if src is None:
                assert np.isnan(got), (u, s, col)            # no row of the SAME unit 12 steps earlier
            else:
                want = frame[parent].iloc[src]
                assert (np.isnan(got) and np.isnan(want)) or got == np.float32(want), (u, s, col)
    # unit b's first rows never read unit a's rows, and the absent month of a (its 15th) gives NaN at its 27th
    assert out.loc[frame["cell_id"] == "b", "amo_lag12"].iloc[:12].isna().all()
    k27 = at[("a", 2003 * 12 + 27)]
    assert np.isnan(out["spei_01m_lag12"].iloc[k27])
    assert np.isnan(out["amo_lag12"].iloc[at[("a", int(frame["_step"].iloc[3]) + 12)]])


def test_the_lag12_build_refuses_a_bad_frame(hook):
    frame = _frame([("a", 2003, 1), ("a", 2003, 2)])
    for parent in LAG12_PARENTS:
        frame[parent] = 1.0
    with pytest.raises(hook.FeatureBuildError, match="not sorted"):
        hook.build(frame.iloc[::-1].reset_index(drop=True), KEYS)
    with pytest.raises(hook.FeatureBuildError, match="not sorted|repeats"):
        hook.build(pd.concat([frame.iloc[:1], frame.iloc[:1]], ignore_index=True), KEYS)
    bad = frame.copy()
    bad["month"] = [5, 6]
    with pytest.raises(hook.FeatureBuildError, match="calendar months"):
        hook.build(bad, KEYS)
    with pytest.raises(hook.FeatureBuildError, match="lacks the sources"):
        hook.build(frame.drop(columns=["amo"]), KEYS)


def test_the_l3_hold_build_keeps_the_2021_layer_for_later_years(hook):
    rows = [(u, y, m) for u in ("a", "b") for y in (2020, 2021, 2022) for m in range(1, 13)
            if not (u == "b" and (y, m) == (2021, 5))]
    frame = _frame(rows)
    for parent in LAG12_PARENTS:
        frame[parent] = 0.0
    out = hook.build(frame, KEYS)
    for i, (c, h) in enumerate(zip(LIVESTOCK, HOLD)):
        got = out[h].to_numpy(dtype=np.float64)
        for k, (u, y, m) in enumerate(rows):
            if y <= 2021:
                assert got[k] == y + i / 10.0, (h, u, y, m)                   # the column itself
            elif u == "b" and m == 5:
                assert np.isnan(got[k]), (h, u, y, m)                         # its 2021 May row is absent
            else:
                assert got[k] == 2021 + i / 10.0, (h, u, y, m)                # 2022: the 2021 layer, same unit


# ------------------------------------------------------------------------------------------------
# the package as derive sees it
def test_every_kept_column_has_store_facts_and_only_unsigned_windows_refuse(augmented):
    from treeroute.pipeline import data as D

    facts, lags, refused = _lags(augmented)              # _Facts: closed world, twins banned, every kept column has facts
    spec = D.package_spec(augmented)
    assert set(spec.context) == {"ctx:month", "ctx:lat"}
    g_lag = {c for c, rule in refused.items() if rule == "G-LAG"}
    assert g_lag <= set(AWAITING_WINDOW_SIGNATURE), sorted(g_lag - set(AWAITING_WINDOW_SIGNATURE))
    store = _store_facts(augmented)
    other = {c: rule for c, rule in refused.items() if rule != "G-LAG"}
    assert all(store[c].cadence.kind == "static" for c in other), other   # static columns take no lag
    assert not g_lag                                     # ruling L1 (b): every kept window is signed
    for c in SIGNED_INDEX_WINDOWS:                       # pdo: lag 2 by ruling N1 (the ERSSTv5 reach)
        assert augmented.ban.verdicts[c].verdict in ("keep", "watch") and lags[c].steps == (2 if c == "pdo" else 1), c


def test_derive_all_on_the_installed_package_refuses_loudly_at_r8(augmented):
    """A toy target table (one unit, 2002-2022): derive_all gets past the closed world and the store-facts guard and
    stops at R8 while any kept column's window is unsigned (G-LAG); the real stores are never read."""
    from treeroute.derive import derive_all
    from treeroute.errors import RefusedError

    _, _, refused = _lags(augmented)
    g_lag = sorted(c for c, rule in refused.items() if rule == "G-LAG")
    years = np.repeat(np.arange(2002, 2023), 12)
    months = np.tile(np.arange(1, 13), 21)
    n = len(years)
    target = NS(unit_ids=np.array(["g_1_1"] * n, dtype=object), group_ids=np.array(["g"] * n, dtype=object),
                time_columns={"year": years, "month": months}, y=np.zeros(n))
    with pytest.raises(RefusedError) as info:
        derive_all(augmented, target, None)
    if g_lag:
        assert info.value.rule == "G-LAG" and any(c in str(info.value) for c in g_lag), info.value
    else:
        assert info.value.rule not in ("G-CLOSED", "R8", "G-LAG"), info.value      # past R8: the reader is next


# ------------------------------------------------------------------------------------------------
# signing state and disclosures
def test_no_timing_fact_is_signed_on_the_owners_behalf(fire, hook):
    """Only the facts an owner ruling names carry the owner's signature (fact_status 'assumed' + reviewed_by owner +
    date 2026-10-06); nothing is 'verified'. UPDATED 2026-10-06 for ruling N (S1-S6, S9 a): every signed store fact and
    every signed feature-script output names ruling L1 or ruling N in its provenance."""
    from treeroute.pipeline import data as D

    for c, f in D.feature_outputs(hook).items():
        assert f.fact_status != "verified", c
        assert f.reviewed_by is None or ((f.fact_status, f.reviewed_by, f.date) == SIGNATURE
                                         and ("ruling N" in f.provenance or "L1" in f.provenance)), c
    for c, f in _store_facts(fire).items():
        assert f.fact_status != "verified", c
        assert f.reviewed_by is None or ((f.fact_status, f.reviewed_by, f.date) == SIGNATURE
                                         and ("ruling N" in f.provenance or "L1" in f.provenance)), c
    signed_package = {"cloud_frequency_pct"}                                   # L1 c: fire's co-measured answer
    for c, f in fire.catalog.columns.items():
        assert f.fact_status != "verified", c
        if c in signed_package:
            assert (f.fact_status, f.reviewed_by, f.date) == SIGNATURE, c
        else:
            assert f.reviewed_by is None, c
    assert fire.catalog.columns["burned_frac"].fact_status == "unverified"
    signed_store = set(SIGNED_INDEX_WINDOWS) | set(LIVESTOCK) | {"deeprec_twsa", "phenology_sos_doy"}
    for c in signed_store:
        f = _store_facts(fire)[c]
        assert (f.fact_status, f.reviewed_by, f.date) == SIGNATURE, c


def test_the_disclosures_of_kept_defects_are_present_and_unsigned(fire):
    entries = fire.exceptions.entries
    columns = {e.column for e in entries if e.column}
    assert {"ntl", "hdi", "fert_n", "fert_p", "luh2_urban", "grace_lwe"} <= columns
    for c in columns:
        assert fire.ban.verdicts[c].verdict in ("keep", "watch"), c
    # the amended J3: one provenance flag names the six livestock columns as watch; the freeze entry is withdrawn
    j3 = [e for e in entries if e.check and e.check.startswith("J3 amended (watch)")]
    assert len(j3) == 1 and j3[0].kind == "provenance_flag" and all(c in j3[0].check for c in LIVESTOCK)
    assert "INDIA" in j3[0].reason and "never reads" in j3[0].reason
    assert not any("freeze" in (e.check or "").lower() for e in entries)
    # ruling N S8 signed the entries that were already true; the others stay UNSIGNED
    assert all(e.owner.startswith(("UNSIGNED", "owner -- signed by the owner 2026-10-06 (ruling N,")) for e in entries)
