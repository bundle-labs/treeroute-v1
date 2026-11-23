"""The PM2.5 ban list installed under owner ruling J (OWNER_RULINGS_2026-10-05.md; tests may name problems).

Source: datasets/review/proposed/pm25_ban_proposed.yaml (the Q34 review with the defaults of its 10 questions,
ruling J1), with the owner's rules applied:
  J2 (a) spei_01m, spei_03m, spei_06m, V06_spei_12m, spei_24m and amo stay banned 'incomplete'; each is kept through
         an engineered <parent>_lag12 column built by the package feature script, its facts composed from the
         parent's (observed_through moved 12 months);
  J2 (b) deeprec_twsa kept (watch) at an ASSUMED lag-3 store bound; phenology_sos_doy kept (watch) at the assumed
         one-extra-year bound: lag 2 years, so R4 (J5) moves Y0 from 2003 to 2004;
  J2 (c) snow_duration_days kept (lag 1 year);
  J2 (d) epo kept: the engine's last-value rule is wired (treeroute/pipeline calls fill_last_value), so each
         December takes the same unit's November value; its store window is still unknown, so R8 refuses it
         (G-LAG) with the other unsigned index windows; December 2023 is a tail left to R30 (disclosed);
  J3     AMENDED: the six aglw_* columns are 'watch', a lagged annual driver (R8: year-1), not 'freeze'; their
         store facts are the seed's again (unverified, no content_epoch); the 2022-23 layers (the 2021 layer
         times INDIA's FAOSTAT ratios, every region) are disclosed with the exact test rows that read them;
  J4     nitrogen_gkg in cg/kg with legal range [0, 5000]; V30_soil_moisture_pct legal minimum -1e-12;
  J1     burn_frac lag 1 (the GFED store reach, assumed); burn_lag1's facts are composed from burn_frac's.
The owner signs timing facts separately: every store fact this change wrote is 'assumed', never 'verified', and
each such column's provenance names the facts the status covers. The index windows that still await a
signature make R8 refuse (G-LAG); that list is pinned here, so signing them must update this file. Reads only
the package, the store catalogs and engine source (no D: needed, except the skip-guarded read-only checks of
the livestock layers).

REVISED 2026-10-06 for ruling L (OWNER_RULINGS_2026-10-05.md section L, the author's answer, not quoted):
  L1     the timing facts are SIGNED (fact_status 'assumed' + reviewed_by owner + date 2026-10-06: the schema's spelling;
         it has no 'signed' value): the 13 index windows are {3, month, centred} (R8 lag 1 month, nothing refused at
         R8 any more); the J-assumed facts and the aglw_* yearly facts carry the signature; the six lag-12 outputs
         carry it on their composed window (L1 c);
  L2     phenology_sos_doy is 'conditional' (out), so Y0 stays 2003;
  L3     the raw aglw_* are banned (written 'incomplete'; the ruling's word post_window_snapshot would make the
         engine's lineage stand-in refuse the hold columns) and each is kept through <parent>_hold2021, watch: the
         real 2021 layer held for 2022-2023, so no row reads a 2022-23 layer any more;
  L4     epo stays keep (now lag 1 from its signed window); wbal_roll24 stays banned.
"""

import datetime as dt
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
PM25 = DATASETS / "pm25"
PROPOSED = DATASETS / "review" / "proposed" / "pm25_ban_proposed.yaml"
PANEL = "../_stores/monthly_panel_v170_schema_catalog.yaml"
GFED = "../_stores/gfed_burn_schema_catalog.yaml"
LAG12_PARENTS = ("spei_01m", "spei_03m", "spei_06m", "V06_spei_12m", "spei_24m", "amo")
LAG12 = tuple("%s_lag12" % p for p in LAG12_PARENTS)
AGLW = ("aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats", "aglw_total_lsu")
HOLD = tuple("%s_hold2021" % c for c in AGLW)                # ruling L3: the real 2021 layer held for 2022-2023
# the columns ruling J changed against the proposal: {column: the installed verdict}
J_CHANGED = {"deeprec_twsa": "watch", "epo": "keep"}
# the columns ruling L changed (L2 phenology out; L3 the raw livestock columns banned): {column: (verdict, reason)}
L_CHANGED = dict({"phenology_sos_doy": ("conditional", None)}, **{c: ("ban", "incomplete") for c in AGLW})
# the kept index columns whose windows the owner signed {3, month, centred} (ruling L1 b): R8 lag 1 month each
# (grace_lwe, the 13th, is banned on PM2.5)
SIGNED_INDEX_WINDOWS = ("ao", "epo", "iod", "nao", "noi", "pdo", "pna", "sam", "soi", "tna", "tsa", "wp")
# owner ruling N1 (OWNER_RULINGS_2026-10-06.md N): pdo takes nino34's form {1, month, centred} + the ERSSTv5 reach of
# +2 months: R8 lag 2; the other 11 keep L1 b's window and lag 1
N1_LAG = {"pdo": 2}
# the columns ruling N changed (S29 road_density banned on all four; S24 burn_lag1 out): {column: (verdict, reason)}
N_CHANGED = {"road_density": ("ban", "post_window_snapshot"), "burn_lag1": ("conditional", None)}
SIGNATURE = ("assumed", "owner", "2026-10-06")                   # plan 1.3's spelling of a signed fact
MONTHLY = NS(kind="regular", length=1, unit="month")
ANNUAL = NS(kind="regular", length=1, unit="year")
# D:/ndvi_drivers/livestock_aglw/india_faostat_ratios.csv, as disclosed (species, 2022 ratio, 2023 ratio)
INDIA_RATIOS = {"aglw_cattle": ("cattl", 1.0039, 1.0057), "aglw_buffalo": ("buff", 1.0027, 1.0055),
                "aglw_horse": ("hors", 0.7657, 0.6376), "aglw_sheep": ("sheep", 1.0596, 1.1597),
                "aglw_goats": ("goat", 1.1081, 1.2141)}


@pytest.fixture(scope="module")
def pkg():
    from treeroute.package.load import load_package

    return load_package(PM25)


@pytest.fixture(scope="module")
def hook(pkg):
    from treeroute.pipeline.data import load_hook

    return load_hook(pkg.root, "features/build.py")


@pytest.fixture(scope="module")
def augmented(pkg, hook):
    from treeroute.pipeline.data import augment_package, feature_outputs

    return augment_package(pkg, feature_outputs(hook))


@pytest.fixture(scope="module")
def proposal():
    return yaml.safe_load(PROPOSED.read_text(encoding="utf-8"))["verdicts"]


def _facts(pkg, column):
    for cat in pkg.stores.values():
        if column in cat.columns:
            return cat.columns[column]
    raise KeyError(column)


def _target(pkg, cadence=MONTHLY):
    tf = pkg.catalog.columns["pm25_ugm3"]
    return NS(name="pm25_ugm3", cadence=cadence, stamp=tf.stamp, window=tf.window, computed_from=())


def _annual_target():
    window = NS(length=1, unit="year", align="backward", reach_after_max=None, reach_before_max=None, max_length=None)
    return NS(name="annual_target", cadence=ANNUAL, stamp="period_end", window=window, computed_from=())


def _view(name, s, co_measured=None):
    return NS(name=name, cadence=s.cadence, stamp=s.stamp, window=s.window, fact_status=s.fact_status,
              co_measured_with_target=co_measured)


def _lag(pkg, column, target=None):
    from treeroute.timing import compute_lag

    s = _facts(pkg, column)
    co = pkg.catalog.columns[column].co_measured_with_target if column in pkg.catalog.columns else None
    target = target or _target(pkg)
    return compute_lag(_view(column, s, co), target, target.cadence, "nowcast").steps


def _kept_lags(pkg, augmented):
    """(refused, lags) over every kept tree feature and context column with a time axis (R8's input)."""
    from treeroute.pipeline.data import package_spec
    from treeroute.timing import Lag, TimingRefusal, lag_trace

    spec = package_spec(augmented)
    refused, lags = [], {}
    tgt = _target(pkg)
    for c in spec.tree_features + spec.context:
        s = spec.store_facts[c]
        if s.cadence.kind == "static":
            continue
        try:
            tr = lag_trace(_view(c, s, augmented.catalog.columns[c].co_measured_with_target), tgt, MONTHLY)
        except TimingRefusal as err:
            assert err.rule == "G-LAG", (c, err)
            refused.append(c)
            continue
        lags[c] = Lag(column=c, steps=tr.steps, column_cadence=s.cadence, floor_reason=tr.floor_reason)
    return refused, lags


# ------------------------------------------------------------------------------------------------
def test_the_package_loads_and_its_closed_world_holds(pkg, augmented):
    from treeroute.pipeline.data import package_spec

    non_key = [c for c, f in pkg.catalog.columns.items() if f.role not in ("key_unit", "key_group", "key_time")]
    assert sorted(pkg.ban.verdicts) == sorted(non_key) and len(non_key) == 190      # 184 + the 6 L3 hold columns
    counts = Counter(v.verdict for v in pkg.ban.verdicts.values())
    # ruling N: S29 bans road_density (keep -> ban post_window_snapshot), S24 puts burn_lag1 out (watch -> conditional)
    assert dict(counts) == {"keep": 101, "watch": 17, "conditional": 24, "ban": 48}
    assert dict(Counter(v.reason for v in pkg.ban.verdicts.values() if v.verdict == "ban")) == {
        "label": 1, "structural": 9, "post_window_snapshot": 9, "incomplete": 19, "trend_proxy": 10}
    spec = package_spec(augmented)
    assert len(spec.tree_features) == 116 and spec.context == ("ctx:month", "ctx:lat")
    assert spec.frozen == ()                                          # amended J3: nothing is frozen, no R9
    assert not set(AGLW) & set(spec.tree_features) and set(HOLD) <= set(spec.tree_features)      # L3
    assert "phenology_sos_doy" not in spec.tree_features                                         # L2
    assert "epo" in spec.tree_features                                 # J2 (d): kept through the last-value rule
    assert (pkg.ban.verdicts["pm25_ugm3"].verdict, pkg.ban.verdicts["pm25_ugm3"].reason) == ("ban", "label")


def test_the_install_is_the_proposal_except_where_ruling_j_changes_it(pkg, proposal):
    installed = pkg.ban.verdicts
    assert set(installed) == set(proposal) | set(LAG12) | set(HOLD)
    for col, p in proposal.items():
        v = installed[col]
        if col in N_CHANGED:
            verdict, reason = N_CHANGED[col]
            assert v.verdict == verdict and (reason is None or v.reason == reason), col
            assert "ruling N" in v.reason + v.evidence, col
            continue
        if col in L_CHANGED:
            verdict, reason = L_CHANGED[col]
            assert v.verdict == verdict and (reason is None or v.reason == reason), col
            assert "ruling L" in v.reason + v.evidence or "L2" in v.reason + v.evidence, col
            continue
        if col in J_CHANGED:
            assert v.verdict == J_CHANGED[col] != p["verdict"], col
            assert "J2" in v.reason + v.evidence or "J3" in v.reason + v.evidence, col
            continue
        assert (v.verdict, v.reason) == (p["verdict"], p["reason"]), col
        assert v.evidence.startswith(p["evidence"]), col          # J notes are appended, never replace evidence
    assert [c for c in installed if c in LAG12] == list(LAG12)
    order = list(installed)
    assert order.index(LAG12[0]) == order.index("burn_lag1") + 1     # catalog order
    assert not [c for c, v in installed.items() if v.verdict == "freeze"]


def test_j2a_parents_stay_banned_and_their_lag12_children_enter(pkg, augmented):
    from treeroute.pipeline.data import check_feature_lineage

    v = pkg.ban.verdicts
    for parent, child in zip(LAG12_PARENTS, LAG12):
        assert (v[parent].verdict, v[parent].reason) == ("ban", "incomplete"), parent
        assert "%s_lag12" % parent in v[parent].evidence
        assert v[child].verdict == ("watch" if parent == "spei_24m" else "keep"), child
        assert pkg.catalog.columns[child].role == "engineered"
    notes = check_feature_lineage(augmented.stores["features/build.py"].columns, augmented)
    assert {c: notes[c] for c in LAG12} == {c: ["%s: ban (incomplete)" % p] for p, c in zip(LAG12_PARENTS, LAG12)}


def test_j2a_lag12_facts_are_composed_from_the_parent(pkg, hook):
    from treeroute.pipeline.data import feature_outputs
    from treeroute.timing import compute_lag

    outputs = feature_outputs(hook)
    assert sorted(outputs) == sorted(("burn_lag1", "ctx:lat", "ctx:month") + LAG12 + HOLD)
    moved = {"2022-12": "2023-12", "2023-01": "2024-01"}
    for parent, child in zip(LAG12_PARENTS, LAG12):
        o, p = outputs[child], _facts(pkg, parent)
        assert o.derived_from == [parent] and o.operation == "lag k=12 unit=month" and o.reads_target is False
        assert (o.stamp, o.window.align, o.window.unit) == ("period_end", "backward", "month")
        assert o.window.length == p.window.length + 12 and o.window.reach_after_max is None
        assert o.legal_range == p.legal_range and o.units == p.units and o.dtype == p.dtype
        assert o.scope == p.scope
        assert (o.fact_status, o.reviewed_by, o.date) == SIGNATURE, child        # L1 c: the composed window, signed
        # the row of month m holds the parent's month m-12: real content runs 12 months past the parent's
        assert o.observed_through == moved[p.observed_through], child
    # the lag-12 column already holds month t-12: R8 gives it no further lag
    tgt = _target(pkg)
    for child in LAG12:
        assert compute_lag(_view(child, outputs[child]), tgt, MONTHLY, "nowcast").steps == 0, child


def test_the_observed_through_shift_refuses_a_form_it_cannot_move(hook):
    assert hook._shift_observed("x", "2022-12", 12) == "2023-12"
    assert hook._shift_observed("x", "2023-01", 1) == "2023-02"
    for bad in ("2021", "2022-13", "2022-12-31"):
        with pytest.raises(hook.FeatureBuildError):
            hook._shift_observed("x", bad, 12)


def test_j2a_build_reads_the_same_unit_twelve_calendar_months_back(hook):
    # unit a: 30 consecutive months; unit b: the same months but month 13 (step 24013) absent
    steps_a = np.arange(24001, 24031)
    steps_b = np.array([s for s in steps_a if s != 24013])
    n_a, n_b = len(steps_a), len(steps_b)
    frame = pd.DataFrame({
        "cell_id": ["a_0_0"] * n_a + ["b_0_1"] * n_b, "region": ["a"] * n_a + ["b"] * n_b,
        "year": 2000, "month": 1, "_step": np.concatenate([steps_a, steps_b]),
        "lat": [10.0] * n_a + [-5.0] * n_b, "burn_frac": 0.5})
    for i, p in enumerate(LAG12_PARENTS):
        frame[p] = frame["_step"].astype(float) + 1000.0 * i + np.where(frame["cell_id"] == "b_0_1", 0.5, 0.0)
    for p in AGLW:
        frame[p] = 1.0
    keys = {"unit": "cell_id", "group": "region", "step": "_step", "time": {"year": "year", "month": "month"}}
    out = hook.build(frame, keys)
    assert sorted(out.columns) == sorted(("burn_lag1", "ctx:lat", "ctx:month") + LAG12 + HOLD)
    for i, (p, c) in enumerate(zip(LAG12_PARENTS, LAG12)):
        got = out[c].to_numpy(dtype=np.float64)
        steps, unit = frame["_step"].to_numpy(), frame["cell_id"].to_numpy()
        for row in range(len(frame)):
            want_step = steps[row] - 12
            present = ((unit == unit[row]) & (steps == want_step)).any()
            if not present:
                assert np.isnan(got[row]), (c, row)              # no predecessor: missing, never a neighbour
            else:
                want = want_step + 1000.0 * i + (0.5 if unit[row] == "b_0_1" else 0.0)
                assert got[row] == pytest.approx(want, abs=0.01), (c, row)
    # unit b at step 24025 reads its absent step 24013: NaN, not unit a's value
    b25 = np.flatnonzero((frame["cell_id"] == "b_0_1").to_numpy() & (frame["_step"] == 24025).to_numpy())
    assert np.isnan(out["spei_01m_lag12"].to_numpy(dtype=np.float64)[b25]).all()


def test_j2b_deeprec_twsa_kept_at_an_assumed_lag_3_bound(pkg):
    s = _facts(pkg, "deeprec_twsa")
    assert s.fact_status == "assumed" and "covers window.reach_after_max only" in s.provenance
    assert (s.window.reach_after_max.value, s.window.reach_after_max.unit) == (3, "month")
    assert _lag(pkg, "deeprec_twsa") == 3
    assert pkg.ban.verdicts["deeprec_twsa"].verdict == "watch"


def test_l2_phenology_is_out_so_y0_stays_2003(pkg, augmented):
    """J2 (b) gave phenology_sos_doy a 2-year lag (its signed window, L1 a); ruling L2 holds it out (conditional),
    so R4 gives Y0 2003 (ruling F3)."""
    from treeroute.derive import rules as R

    s = _facts(pkg, "phenology_sos_doy")
    assert (s.fact_status, s.reviewed_by, s.date) == SIGNATURE
    assert s.window.align == "centred" and s.window.length == 1
    assert (s.window.reach_after_max.value, s.window.reach_after_max.unit) == (1, "year")
    assert "covers the window only" in s.provenance
    assert _lag(pkg, "phenology_sos_doy") == 2                        # years, on this monthly target
    assert _lag(pkg, "phenology_sos_doy", _annual_target()) == 1      # on an annual target
    v = pkg.ban.verdicts["phenology_sos_doy"]
    assert v.verdict == "conditional" and "L2" in v.reason and "Y0 stays 2003" in v.reason
    # the A2 list (8 MODIS land-cover columns) does not hold it out; those 8 stay conditional
    for c in ("tree_cover_pct", "V15_bare_ground_pct", "V17_herb_cover_pct", "modis_landcover_class",
              "modis_landcover_annual", "cropland_fraction", "shrub_cover_pct_global", "snow_cover_fraction"):
        assert pkg.ban.verdicts[c].verdict == "conditional", c
    _, lags = _kept_lags(pkg, augmented)
    assert "phenology_sos_doy" not in lags
    r4 = R.derive_r04_first_year(2002, lags)
    assert r4.value == 2003 and "phenology_sos_doy" not in r4.inputs["set_by"]
    from treeroute.timing import Lag
    with_it = dict(lags, phenology_sos_doy=Lag(column="phenology_sos_doy", steps=2, column_cadence=s.cadence,
                                               floor_reason=None))
    assert R.derive_r04_first_year(2002, with_it).value == 2004          # what keeping it would have given


def test_j2c_snow_duration_days_kept_and_lagged_one_year(pkg):
    assert pkg.ban.verdicts["snow_duration_days"].verdict == "keep"
    assert _lag(pkg, "snow_duration_days") == 1 and _facts(pkg, "snow_duration_days").cadence.unit == "year"


def test_j2d_epo_is_kept_because_the_last_value_rule_is_wired(pkg, augmented):
    """Ruling J2 (d): epo is kept because the pipeline runs the last-value rule (each December, which CPC never
    issues, takes the same unit's November value). If no pipeline module called fill_last_value any more, R30
    would 0-fill every December (a month key), so this test also checks the caller. Its store window is still
    unknown until ruling L1 (b), 2026-10-06: the owner signed {3, month, centred}, so R8 gives it lag 1 month."""
    from treeroute.io.lastvalue import fill_last_value

    v = pkg.ban.verdicts["epo"]
    assert v.verdict == "keep" and "J2 (d)" in v.reason and "pipeline/data.py" in v.evidence
    callers = []
    for path in sorted((ENGINE_DIR / "treeroute").rglob("*.py")):
        if path.name == "lastvalue.py":
            continue
        if re.search(r"\bfill_last_value\s*\(", path.read_text(encoding="utf-8")):
            callers.append(path.relative_to(ENGINE_DIR).as_posix())
    assert "treeroute/pipeline/data.py" in callers, callers
    s = _facts(pkg, "epo")
    assert (s.window.length, s.window.unit, s.window.align) == (3, "month", "centred")      # L1 b, signed
    assert (s.fact_status, s.reviewed_by, s.date) == SIGNATURE
    refused, lags = _kept_lags(pkg, augmented)
    assert "epo" not in refused and lags["epo"].steps == 1
    # the rule on epo's shape: two units, January 2022 to December 2023, every December missing; each interior
    # December takes the same unit's November value, December 2023 is a tail left to R30
    # (the rule on the UNLAGGED series; with R8's lag 1 month the 2023-12 row reads November 2023, so no row reads
    # that tail; exceptions.yaml's provenance_flag still describes the lag-0 tail, an open owner-file item)
    steps = np.arange(2022 * 12, 2024 * 12)
    months = steps % 12 + 1
    codes = np.repeat(np.array([0, 1]), len(steps))
    allsteps = np.concatenate([steps, steps])
    vals = np.concatenate([steps * 1.0, steps * 1.0 + 0.5])
    vals[np.concatenate([months, months]) == 12] = np.nan
    out, record = fill_last_value(pd.DataFrame({"epo": vals}), codes, allsteps, ("epo",), MONTHLY)
    got = out["epo"].to_numpy(dtype=np.float64)
    for u, off in ((0, 0.0), (1, 0.5)):
        rows = np.flatnonzero(codes == u)
        dec22, dec23 = rows[steps == 2022 * 12 + 11][0], rows[steps == 2023 * 12 + 11][0]
        assert got[dec22] == 2022 * 12 + 10 + off                      # December 2022 <- November 2022
        assert np.isnan(got[dec23])                                    # tail: R30's 0-fill on 2023-12 rows
    assert (record.missing["epo"], record.filled["epo"], record.tail["epo"]) == (4, 2, 2)
    ex = [e for e in pkg.exceptions.entries if e.kind == "provenance_flag" and e.column == "epo"]
    assert len(ex) == 1 and "tail" in ex[0].reason and "PRESENT" in ex[0].reason
    assert "once kept" not in ex[0].decision


def test_l3_livestock_is_kept_through_the_2021_hold_and_the_raw_columns_are_banned(pkg, augmented, hook):
    from treeroute.derive import rules as R
    from treeroute.derive import shapes as DS
    from treeroute.pipeline.data import check_feature_lineage, feature_outputs

    refused, lags = _kept_lags(pkg, augmented)
    outputs = feature_outputs(hook)
    for c, h in zip(AGLW, HOLD):
        v = pkg.ban.verdicts[c]
        assert (v.verdict, v.reason) == ("ban", "incomplete"), c
        assert "ruling L3" in v.evidence and "post_window_snapshot" in v.evidence and h in v.evidence, c
        w = pkg.ban.verdicts[h]
        assert w.verdict == "watch" and "L3" in w.reason + w.evidence and "disclosed" in w.reason, h
        assert pkg.catalog.columns[h].role == "engineered", h
        s = _facts(pkg, c)
        assert (s.cadence.kind, s.cadence.length, s.cadence.unit) == ("regular", 1, "year"), c
        assert s.observed_through == "2021", c
        assert "INDIA" in s.provenance and "No content_epoch" in s.provenance, c
        assert s.content_epoch is None and (s.fact_status, s.reviewed_by, s.date) == SIGNATURE, c    # L1 c
        o = outputs[h]
        assert o.derived_from == [c] and o.reads_target is False, h
        assert o.operation == "hold_last_observed through_year=2021 unit=year", h
        assert (o.cadence, o.stamp, o.window, o.units, o.dtype, o.legal_range, o.observed_through) == (
            s.cadence, s.stamp, s.window, s.units, s.dtype, s.legal_range, s.observed_through), h
        # L3 builds the hold; ruling N S5 signed the feature-script outputs' facts (OWNER_RULINGS_2026-10-06.md N)
        assert (o.fact_status, o.reviewed_by, o.date) == SIGNATURE and o.fill_values == [], h
        assert c not in lags and lags[h].steps == 1 and lags[h].column_cadence.unit == "year", h
    notes = check_feature_lineage(outputs, augmented)          # 'incomplete' is not a leak reason: no refusal
    assert {h: notes[h] for h in HOLD} == {h: ["%s: ban (incomplete)" % c] for c, h in zip(AGLW, HOLD)}
    # the test rows that WOULD read a rescaled 2022-23 layer through the raw column (a row's features are read at
    # its issue step, label step less the lead, lagged one year): these rows now read the hold, which holds 2021
    leads = (0,) + tuple(R.derive_r10_leads(DS.SeasonKeySpec(DS.SeasonKeyKind.MONTH_OF_YEAR, 12), False).value.leads)
    assert leads == (0, 6, 12)
    exposed = {}
    for lead in leads:
        for year in (2020, 2021, 2022, 2023):
            for month in range(1, 13):
                issue = year * 12 + month - 1 - lead
                if issue // 12 - lags["aglw_total_lsu_hold2021"].steps >= 2022:
                    exposed.setdefault(lead, []).append((year, month))
    assert exposed == {0: [(2023, m) for m in range(1, 13)], 6: [(2023, m) for m in range(7, 13)]}


def test_l3_hold_build_holds_the_2021_layer_backward_only(hook):
    # unit a: every month of 2020-2023; unit b: the same months but March 2021 absent; annual values y*10 (+ offset)
    rows = []
    for unit in ("a_0_0", "b_0_1"):
        for year in (2020, 2021, 2022, 2023):
            for month in range(1, 13):
                if unit == "b_0_1" and (year, month) == (2021, 3):
                    continue
                rows.append((unit, unit[0], year, month, year * 12 + month))
    frame = pd.DataFrame(rows, columns=["cell_id", "region", "year", "month", "_step"])
    frame["lat"], frame["burn_frac"] = 1.0, 0.0
    for p in LAG12_PARENTS:
        frame[p] = 0.0
    for i, p in enumerate(AGLW):
        frame[p] = frame["year"] * 10.0 + i + np.where(frame["cell_id"] == "b_0_1", 0.5, 0.0)
    keys = {"unit": "cell_id", "group": "region", "step": "_step", "time": {"year": "year", "month": "month"}}
    out = hook.build(frame, keys)
    for i, (p, h) in enumerate(zip(AGLW, HOLD)):
        got = out[h].to_numpy(dtype=np.float64)
        for r, row in frame.iterrows():
            off = 0.5 if row.cell_id == "b_0_1" else 0.0
            if row.year <= 2021:
                assert got[r] == row[p], (h, r)                              # up to 2021: the column itself
            elif row.cell_id == "b_0_1" and row.month == 3:
                assert np.isnan(got[r]), (h, r)                              # its 2021 March row is absent: NaN
            else:
                assert got[r] == 2021 * 10.0 + i + off, (h, r)               # 2022, 2023: the 2021 layer
    # never a later row: changing the 2022-2023 source values changes no hold value
    frame2 = frame.copy()
    for p in AGLW:
        frame2.loc[frame2["year"] >= 2022, p] = -999.0
    out2 = hook.build(frame2, keys)
    for h in HOLD:
        a, b = out[h].to_numpy(dtype=np.float64), out2[h].to_numpy(dtype=np.float64)
        assert np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)]), h


def test_l3_hold_refuses_a_parent_whose_observed_through_moved(pkg, hook):
    s = _facts(pkg, "aglw_cattle")
    with pytest.raises(hook.FeatureBuildError):
        hook._hold_facts("aglw_cattle", s.model_copy(update={"observed_through": "2022"}))


LIVESTOCK_LAYERS = Path("D:/ndvi_drivers/livestock_aglw")


@pytest.mark.skipif(not LIVESTOCK_LAYERS.is_dir(), reason="the livestock layers are not on this machine")
def test_j3_the_extended_livestock_years_were_written_after_the_real_ones():
    """Read-only: 2002-2021 came from the provider archive; 2022-2023 were written later by the extension."""
    def stamp(sp, y):
        return (LIVESTOCK_LAYERS / ("%s_%d.tif" % (sp, y))).stat().st_mtime

    for sp in ("Cattl", "Buffa", "Horse", "Sheep", "Goats"):
        real = [stamp(sp, y) for y in range(2002, 2022)]
        extended = [stamp(sp, y) for y in (2022, 2023)]
        assert min(extended) > max(real), sp


@pytest.mark.skipif(not (LIVESTOCK_LAYERS / "india_faostat_ratios.csv").is_file(),
                    reason="the livestock ratios are not on this machine")
def test_j3_the_extension_used_india_ratios_for_every_region(pkg):
    """Read-only: the disclosed ratios are the CSV's, and the extension script filters India alone."""
    ratios = pd.read_csv(LIVESTOCK_LAYERS / "india_faostat_ratios.csv")
    got = {r.species: (round(float(r.ratio_2022), 4), round(float(r.ratio_2023), 4)) for r in ratios.itertuples()}
    assert {sp: (a, b) for sp, a, b in INDIA_RATIOS.values()} == got
    script = (ENGINE_DIR.parent / "presplit_cc" / "fetch_livestock_extend.py").read_text(encoding="utf-8")
    assert '(chunk["Area"] == "India")' in script and "arr = data * r[ic][key]" in script
    by_col = {e.column: e for e in pkg.exceptions.entries if e.kind == "disclosed_defect"}
    for col, (_, r22, _) in INDIA_RATIOS.items():
        assert ("x%.4f for 2022" % r22) in by_col[col].reason, col


def test_j4_store_fact_fixes(pkg):
    n = _facts(pkg, "nitrogen_gkg")
    assert (n.units, tuple(n.legal_range), n.fact_status) == ("cg kg-1", (0.0, 5000.0), "assumed")
    assert "covers units and legal_range only" in n.provenance
    w = _facts(pkg, "V30_soil_moisture_pct")
    assert (tuple(w.legal_range), w.fact_status) == ((-1e-12, 100.0), "assumed")
    assert "covers the legal_range minimum only" in w.provenance


def test_j1_burn_frac_lag_1_and_burn_lag1_is_composed_from_it(pkg, hook):
    from treeroute.package import schema as S
    from treeroute.pipeline.data import feature_outputs
    from treeroute.timing import compute_lag

    s = _facts(pkg, "burn_frac")
    assert s.fact_status == "assumed" and (s.window.reach_after_max.value, s.window.reach_after_max.unit) == (1, "month")
    assert "covers window.reach_after_max only" in s.provenance
    assert _lag(pkg, "burn_frac") == 1
    o = feature_outputs(hook)["burn_lag1"]
    assert o.derived_from == ["burn_frac"] and o.operation == "lag k=1 unit=month"
    assert (o.window.length, o.window.unit, o.window.align, o.window.reach_after_max) == (2, "month", "backward", None)
    assert (o.product_family, o.legal_range, dict(o.absent_groups)) == (s.product_family, s.legal_range,
                                                                       dict(s.absent_groups))
    assert compute_lag(_view("burn_lag1", o), _target(pkg), MONTHLY, "nowcast").steps == 0
    # the window follows the store reach: with a two-month reach, burn_lag1 would reach one month past t
    wider = s.model_copy(update={"window": S.Window.model_validate(
        {"length": 1, "unit": "month", "align": "backward", "reach_after_max": {"value": 2, "unit": "month"}})})
    composed = hook._lag_facts("burn_frac", wider, 1, "test")
    assert composed["window"] == {"length": 2, "unit": "month", "align": "backward",
                                  "reach_after_max": {"value": 1, "unit": "month"}}
    assert pkg.ban.verdicts["burn_frac"].verdict == "watch" and "OWNER QUESTION" in pkg.ban.verdicts["burn_lag1"].evidence


def test_r8_refuses_no_kept_column_after_the_l1_signatures_and_y0_is_2003(pkg, augmented):
    """Ruling L1 (b): the 12 kept index windows are signed {3, month, centred}: R8 lags each one month and refuses
    nothing (G-LAG passes). With phenology_sos_doy out (L2), R4 gives Y0 2003 (ruling F3's value)."""
    from treeroute.derive import rules as R

    refused, lags = _kept_lags(pkg, augmented)
    assert refused == []
    assert {c: lags[c].steps for c in SIGNED_INDEX_WINDOWS} == {c: N1_LAG.get(c, 1) for c in SIGNED_INDEX_WINDOWS}
    assert {c: l.steps for c, l in lags.items() if c in LAG12} == {c: 0 for c in LAG12}
    assert {c: lags[c].steps for c in HOLD} == {c: 1 for c in HOLD}
    assert R.derive_r04_first_year(2002, lags).value == 2003


def test_the_owner_signed_facts_carry_the_signature_and_nothing_is_verified(pkg, hook):
    """Ruling L1: the J facts (a), the 13 index windows (b) and the aglw_* yearly facts (c) are signed, written
    fact_status 'assumed' + reviewed_by owner + date 2026-10-06. co2 (R-C a) is not in the ruling's list: unsigned.
    Nothing is 'verified' (no fact was checked against a source by the signature). Of the feature-script outputs only
    the six lag-12 windows are signed (L1 c, as BAN_INSTALL_REPORT.md section 8 C listed them): burn_lag1, the L3
    hold columns and the context columns are not."""
    from treeroute.pipeline.data import feature_outputs

    # UPDATED 2026-10-06: ruling N S5 signed the context and hold outputs too; burn_lag1 (out by S24) stays unsigned
    for c, f in feature_outputs(hook).items():
        assert f.fact_status != "verified", c
        assert (f.reviewed_by is not None) == (c != "burn_lag1"), c
    assert (feature_outputs(hook)["burn_lag1"].fact_status, _facts(pkg, "burn_frac").fact_status) == ("assumed",) * 2
    signed = ("nitrogen_gkg", "V30_soil_moisture_pct", "deeprec_twsa", "phenology_sos_doy", "burn_frac", "tni") \
        + SIGNED_INDEX_WINDOWS + ("grace_lwe",) + AGLW
    assert {c: (_facts(pkg, c).fact_status, _facts(pkg, c).reviewed_by, _facts(pkg, c).date) for c in signed} == {
        c: SIGNATURE for c in signed}
    assert all("SIGNED by the owner 2026-10-06 (ruling L1" in _facts(pkg, c).provenance for c in signed)
    assert all(" covers " in _facts(pkg, c).provenance for c in ("nitrogen_gkg", "V30_soil_moisture_pct",
                                                                   "deeprec_twsa", "phenology_sos_doy", "burn_frac"))
    assert (_facts(pkg, "co2").fact_status, _facts(pkg, "co2").reviewed_by) == ("assumed", None)
    for c in SIGNED_INDEX_WINDOWS + ("grace_lwe",):
        w = _facts(pkg, c).window
        reach = None if w.reach_after_max is None else (w.reach_after_max.value, w.reach_after_max.unit)
        want = (1, "month", "centred", None, (2, "month")) if c in N1_LAG else (3, "month", "centred", None, None)
        assert (w.length, w.unit, w.align, w.max_length, reach) == want, c
        assert _facts(pkg, c).stamp == "period_centre", c
    for path in (PANEL, GFED):
        verified = [c for c, f in pkg.stores[path].columns.items() if f.fact_status == "verified"]
        assert verified == [], (path, verified)
        for c, f in pkg.stores[path].columns.items():
            assert (f.reviewed_by is None) == (f.date is None), (path, c)
            assert f.reviewed_by in (None, "owner"), (path, c)


def test_the_j_disclosures_are_present_and_unsigned(pkg):
    entries = pkg.exceptions.entries
    by = {(e.kind, e.column or e.check) for e in entries}
    assert ("provenance_flag", "deeprec_twsa") in by and ("provenance_flag", "epo") in by
    assert {("disclosed_defect", c) for c in AGLW} <= by
    lag12 = [e for e in entries if e.check and e.check.startswith("J2 a:")]
    assert len(lag12) == 1 and "standardised over its whole record" in lag12[0].reason
    assert "detrended over its whole record" in lag12[0].reason
    for e in entries:
        # ruling N S8 signed the entries that were already true; the others stay UNSIGNED
        assert e.owner.startswith(("UNSIGNED -- basis: ", "owner -- signed by the owner 2026-10-06 (ruling N,")), e.owner
        if e.kind == "disclosed_defect" and e.column in AGLW:
            assert "IS read" in e.reason and "INDIA" in e.reason and "never read at any cut" not in e.reason
