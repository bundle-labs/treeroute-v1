"""derive_all on the PM2.5 package with the ruling-J ban list, on the real stores (READ-ONLY; tests may name
problems, regions and drives). Heavy: skipped unless PM25_DERIVE_CHECK=1.

UPDATED 2026-10-06 (agent C1) for owner ruling L (OWNER_RULINGS_2026-10-05.md section L): L1 (b) signed the 13 index
windows {3, month, centred} in the shared panel store catalog, so the package AS INSTALLED passes R8 (no G-LAG
refusal) and the in-memory overlay below is retired (its windows would now replace the signed ones); L2 put
phenology_sos_doy out (conditional), so Y0 is 2003, inner fit 2003-2016 and h 168 (ruling F3's values, now in
expected_derived.json); L3 banned the raw aglw_* and keeps the six aglw_*_hold2021 columns (one year). Both derive_all
passes now run on the package as installed, and the L-state lags are compared with expected_derived.json's
R8_feature_lags.l_state_lags. The text below describes the check as it was written before ruling L.

Two derivations:
  1. the package EXACTLY as installed: derive_all must refuse at R8 (G-LAG) on the kept index columns whose store
     window is still unknown (their signatures are the owner's: review/proposed/BAN_REVIEW_SUMMARY.md 5 B,
     ruling J1's noi bound, and epo, kept by J2 d with no proposed window; none of them written yet);
  2. an IN-MEMORY overlay, never written to any file, that supplies those 12 windows (a plain month {1, month,
     centred} for soi, tna, tsa, iod, ao, nao, pna, wp, sam and, by analogy with its CPC siblings, epo; noi
     {3, month, centred} assumed, J1; pdo {1, month, centred} + reach_after_max {2, month}), so the derived
     values can be compared with
     datasets/pm25/expected_derived.json (whose Y0, inner fit and h are PROVISIONAL: they hold while the owner
     keeps phenology_sos_doy). Nothing else is supplied: under the amended J3 no column is frozen, so the
     pipeline's own ColumnReader runs unchanged, last-value rule included (J2 d: epo's Decembers).
The pipeline's own read steps run (the package's target reader, the column reader with the panel, GFED and the
feature script, then derive_all twice: on every label, then with the labels before Y0 withheld, as
treeroute.pipeline.run does).

Compared with expected_derived.json: R1, R2, Y0 (R4) and what sets it, Y_end, test years, train end, inner fit,
inner score (R3-R7), leads (R10), the router kind (R12) and its h = the valid rows per unit Y0..inner-fit end
(R12_valid_rows_per_unit.inner_fit), the decision surface (R13), the router design (R14: kind, columns, centre,
grid points, levels, ratios, fit-row cap; 'unpenalised' is a KNOWN difference, recorded not asserted: derive
lists intercept and normal, the json the normal only, tests/test_derive_acceptance.py _UNPENALISED), the history
block (R17), the links (R22), the bank count and trees per group (R18, R19), the index lags (R8) and the columns
ruling J changed, R9 (empty) and R30's flags. NOT derivable by derive_all and recorded as such: the overlap
blocks (they need the static table, split.derive_overlap_blocks), R12_valid_rows_per_unit.test_cut (no rule
outputs it), and region_fit (a region-router field; PM2.5's router is per unit).

ONE DEPARTURE, forced by the machine: the full census (about 2 million units x 264 months) does not fit in memory
(treeroute/pipeline/run.py LIMITS: a streaming vault and derive is an owner item), so each group keeps
UNITS_PER_GROUP units, a stride over its units with a valid label (split.stride_pick, the smoke's pick). The
windows, lags, router kind, history block and links do not depend on that pick; the bank count is 100 while a
group keeps at least 100 units; the scored count, group count and bank trees follow the number of groups read.

Environment: PM25_DERIVE_CHECK=1 to run; PM25_DERIVE_GROUPS = 'all' (default, 127 groups) or a number k (k groups
evenly spaced in sorted order; R18's scored count, the group count and the bank trees are then only reported).
The summary is printed and written as pm25_derive_summary.json under the test's tmp folder BEFORE the
assertions. The quick check (4 groups, about 2 minutes):
    set PM25_DERIVE_CHECK=1 & set PM25_DERIVE_GROUPS=4 & py -3.9 -m pytest tests/test_packages_pm25_derive.py -s -q
All 127 groups read about 2,800 target, 2,800 panel and 2,800 GFED files: roughly 25 minutes and 6 to 8 GB of
RAM. Close other heavy jobs first and give it a basetemp of its own:
    set PM25_DERIVE_CHECK=1 & set PM25_DERIVE_GROUPS=all & py -3.9 -m pytest tests/test_packages_pm25_derive.py -s -q --basetemp=D:/treeroute/pm25_package/pytest_tmp
"""

import datetime as dt
import json
import os
import time
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from conftest import ENGINE_DIR

PM25 = ENGINE_DIR / "datasets" / "pm25"
EXPECTED = PM25 / "expected_derived.json"
PANEL = "../_stores/monthly_panel_v170_schema_catalog.yaml"
UNITS_PER_GROUP = 100
AGLW = ("aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats", "aglw_total_lsu")
LAG12 = ("spei_01m_lag12", "spei_03m_lag12", "spei_06m_lag12", "V06_spei_12m_lag12", "spei_24m_lag12", "amo_lag12")

pytestmark = pytest.mark.skipif(os.environ.get("PM25_DERIVE_CHECK") != "1",
                                reason="heavy real-data check: set PM25_DERIVE_CHECK=1 to run it")


def _v(x):
    return getattr(x, "value", x)


def test_derive_all_on_pm25_as_installed(tmp_path):
    from treeroute import split as SP
    from treeroute import timing
    from treeroute.derive import derive_all
    from treeroute.derive.rules import derive_r01_cadence
    from treeroute.errors import RefusedError
    from treeroute.io.steps import step_index
    from treeroute.package.load import load_package
    from treeroute.pipeline import data as D

    if not os.path.isdir("D:/pm25_acag") or not os.path.isdir("D:/monthly_panel"):
        pytest.skip("D:/pm25_acag or D:/monthly_panel is not on this machine")
    t0 = time.time()

    def echo(msg):
        print("[%6.1fs] %s" % (time.time() - t0, msg), flush=True)

    package = load_package(PM25)
    target_hook = D.load_hook(package.root, D.TARGET_READER)
    feature_hook = D.load_hook(package.root, D.FEATURE_SCRIPT)
    pkg = D.augment_package(package, D.feature_outputs(feature_hook))
    pkg_o = pkg                                  # ruling L1 (b): no overlay; the package as installed
    spec = D.package_spec(pkg_o)
    assert spec.frozen == ()
    listing = D.list_target(pkg_o)
    all_groups = SP.groups_under_loro(SP.loro_split_sets(pkg_o.split), D.listed_groups(listing))
    choice = os.environ.get("PM25_DERIVE_GROUPS", "all")
    if choice == "all":
        groups = tuple(all_groups)
    else:
        k = int(choice)
        groups = tuple(all_groups[i] for i in
                       sorted({int(round(i * (len(all_groups) - 1) / max(k - 1, 1))) for i in range(k)}))
    full = len(groups) == len(all_groups)
    files_of = {}
    gi = listing.key_names.index(D.GROUP_PLACEHOLDER)
    for key, path in listing.files:
        files_of.setdefault(key[gi], []).append((key, path))
    picked = {}
    for g in groups:
        valid = set()
        for key, path in files_of[g]:
            part = target_hook.read_target_file(path, dict(zip(listing.key_names, key)))
            y = part[spec.target_col].to_numpy(dtype=np.float64)
            valid.update(pd.unique(part[spec.unit_col].to_numpy()[np.isfinite(y)]).tolist())
        picked[g] = frozenset(SP.stride_pick(tuple(sorted(valid)), UNITS_PER_GROUP))
    echo("unit pick: %d groups x %d units" % (len(groups), UNITS_PER_GROUP))

    class PickedUnits(object):
        @staticmethod
        def read_target_file(path, key):
            part = target_hook.read_target_file(path, key)
            return part[part[spec.unit_col].isin(picked[key["group"]])].reset_index(drop=True)

    frame = D.read_target(pkg_o, spec, PickedUnits(), listing, groups, None, echo)
    target = D.target_table(frame, spec)
    cadence = derive_r01_cadence(target.unit_ids, target.time_columns, spec.time_facts).value
    reader = D.ColumnReader(pkg_o, spec, frame, cadence, feature_hook, echo)

    # 1. the package as installed, on every label (ruling L1 b: R8 refuses nothing)
    try:
        first = dict(derive_all(pkg_o, target, reader))
        as_installed = {"refused": None}
    except RefusedError as exc:
        as_installed = {"refused": exc.rule, "message": str(exc)}
        raise
    echo("as installed: %s" % as_installed)

    # 2. the second pass, labels before Y0 withheld
    y0 = int(first["R4"].value)
    steps = step_index(target.time_columns, spec.time_facts, cadence)
    y0_first = int(timing.year_last_step(y0 - 1, cadence)) + 1
    model_target = SimpleNamespace(unit_ids=target.unit_ids, group_ids=target.group_ids,
                                   time_columns=target.time_columns, y=np.where(steps < y0_first, np.nan, target.y))
    derived = dict(derive_all(pkg_o, model_target, reader))
    w = derived["R7"].value
    lists = derived["R18:units"].value
    hist = derived["R17"].value
    design = derived["R14"].value
    r19 = derived["R19"].value
    r8 = {str(k): int(v.steps) for k, v in sorted(derived["R8"].value.items())}
    r9 = {c: {int(lead): {str(_v(k)): dt.date.fromordinal(int(d)).isoformat() for k, d in per.items()}
              for lead, per in leads.items()} for c, leads in derived["R9"].value.items()}
    lv = reader.last_value_record(derived["R8"].value)
    last_value = {c: {"missing": int(lv.missing[c]), "filled": int(lv.filled[c]), "tail": int(lv.tail[c]),
                      "head": int(lv.head[c]), "gap_longer": int(lv.gap_longer[c])}
                  for c in lv.columns if int(lv.missing[c])}
    summary = {
        "groups_read": len(groups), "units_per_group_read": UNITS_PER_GROUP, "target_rows": int(len(frame)),
        "as_installed": as_installed,
        "R1": [_v(derived["R1"].value.kind), derived["R1"].value.length, _v(derived["R1"].value.unit)],
        "R2_steps_per_year": int(derived["R2"].value.steps_per_year), "R4_y0": y0,
        "R4_set_by": derived["R4"].inputs["set_by"], "R3_y_end": int(derived["R3"].value),
        "R5_test_years": list(w.test_years), "R6_train_end": int(derived["R6"].value),
        "R7_inner_fit": list(w.inner_fit), "R7_inner_score": list(w.inner_score),
        "R10_leads": list(derived["R10"].value.leads), "R9": r9,
        "R12": _v(derived["R12"].value), "R12_h": float(derived["R12"].inputs["h"]),
        "R13": _v(derived["R13"].value[0]),
        "R14": {"kind": _v(design.kind), "columns": list(design.columns), "unpenalised": list(design.unpenalised),
                "centre": list(design.centre), "grid_points": len(design.grid),
                "levels": len({g.level for g in design.grid}),
                "ratios": len({g.ratio for g in design.grid if g.ratio is not None}),
                "fit_row_cap": design.fit_row_cap},
        "R14_region_fit": "R14:region_fit" in derived,
        "R18_groups": len(derived["R18:groups"].value),
        "R18_bank": sorted({len(v) for v in lists.bank.values()}),
        "R18_scored": sorted({len(v) for v in lists.scored.values()}),
        "R19_trees_per_group": int(r19["trees_per_group"]), "R19_bank_trees": int(r19["bank_trees"]),
        "R17": {"columns": list(hist.columns), "last_values": int(hist.last_values),
                "trailing_steps": list(hist.trailing_steps), "all_history_mean": bool(hist.all_history_mean),
                "start_offset_steps": int(hist.start_offset_steps)},
        "R22": [_v(x) for x in derived["R22"].value],
        "R8": r8, "R30_flags": list(derived["R30"].flags), "last_value": last_value,
        "not_derivable_here": ["R14_overlap_blocks (static table; split.derive_overlap_blocks)",
                               "R12_valid_rows_per_unit.test_cut (no rule outputs it)",
                               "region_fit (region router only)"],
        "seconds": round(time.time() - t0, 1)}
    print("SUMMARY %s" % json.dumps(summary, default=str), flush=True)
    out = tmp_path / "pm25_derive_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")

    exp = json.loads(EXPECTED.read_text(encoding="utf-8"))
    assert as_installed["refused"] is None
    assert summary["R1"] == ["regular", 1, "month"] and summary["R2_steps_per_year"] == 12
    ew = exp["R3_R7_windows"]
    assert (y0, summary["R3_y_end"]) == (ew["y0"], ew["y_end"]) == (2003, 2023)          # ruling L2 (F3's value)
    assert "phenology_sos_doy" not in summary["R4_set_by"]
    assert summary["R5_test_years"] == ew["test_years"] and summary["R6_train_end"] == ew["train_end"]
    assert summary["R7_inner_fit"] == ew["inner_fit"] and summary["R7_inner_score"] == ew["inner_score"]
    assert summary["R10_leads"] == exp["R10_leads"]["leads"] == [6, 12]
    assert summary["R12"] == exp["R12_router_kind"]["value"]
    assert summary["R12_h"] == exp["R12_valid_rows_per_unit"]["inner_fit"] == 168
    assert summary["R13"] == exp["R13_decision_surface"]["value"]
    ed = exp["R14_router_design"]
    for field in ("kind", "columns", "centre", "grid_points", "levels", "ratios", "fit_row_cap"):
        assert summary["R14"][field] == ed[field], field
    assert summary["R14"]["unpenalised"] == ["intercept", "normal"] and ed["unpenalised"] == ["normal"]  # KNOWN
    assert summary["R14_region_fit"] is False and "inner_surface_rows" not in ed
    eh = exp["R17_history"]
    assert len(summary["R17"]["columns"]) == eh["n_columns"]
    for field in ("last_values", "trailing_steps", "all_history_mean", "start_offset_steps"):
        assert summary["R17"][field] == eh[field], field
    assert summary["R22"] == exp["R22_links"]["value"]
    assert summary["R18_bank"] == [exp["R18_units_per_group"]["bank"]]
    tc = exp["R14_tree_columns"]
    assert summary["R19_trees_per_group"] == tc["bank_trees"] // exp["LORO_groups"]["n_groups"]
    assert summary["R19_bank_trees"] == summary["R19_trees_per_group"] * summary["R18_groups"]
    if full:
        assert summary["R18_groups"] == exp["LORO_groups"]["n_groups"]
        assert summary["R18_scored"] == [exp["R18_units_per_group"]["scored"]]
        assert summary["R19_bank_trees"] == tc["bank_trees"]
    lags = exp["R8_feature_lags"]["index_lags_steps"]
    assert {c: r8[c] for c in lags if c in r8} == {c: s for c, s in lags.items() if c in r8}
    # the columns rulings J and L changed: expected_derived.json's l_state_lags, every one
    state = exp["R8_feature_lags"]["l_state_lags"]
    assert {c: r8.get(c) for c in state["steps"]} == state["steps"]
    assert not set(state["not_kept"]) & set(r8)
    assert r8["deeprec_twsa"] == 3 and r8["burn_frac"] == 1 and r8["burn_lag1"] == 0
    assert r8["snow_duration_days"] == 1 and r8["noi"] == 1 and r8["pdo"] == 1                 # L1 (b)
    assert "phenology_sos_doy" not in r8 and r8["epo"] == r8["nao"] == 1                          # L2, L1 (b)
    # J2 d: epo's Decembers are filled from November. Since L1 (b) epo is read at lag 1 month, so the units' last
    # December (2023, the record's tail) is read by no row of the table: no tail is left to R30 (2026-10-06)
    e = last_value["epo"]
    assert e["filled"] > 0 and e["tail"] == 0 and e["gap_longer"] == 0
    assert e["missing"] == e["filled"] + e["tail"] + e["head"]
    assert {c: r8[c] for c in LAG12} == {c: 0 for c in LAG12}
    assert not set(AGLW) & set(r8)                                   # L3: the raw aglw_* are banned
    holds = tuple(c + "_hold2021" for c in AGLW)
    assert {c: r8[c] for c in holds} == {c: 1 for c in holds}       # L3: the held 2021 layer, lagged one year
    assert r9 == {}
    assert not {f.split(":")[-1] for f in summary["R30_flags"]} & (set(LAG12) | set(holds))
