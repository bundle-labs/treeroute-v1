"""derive_all_table: the plan-time rules of the table option, in dependency order (SPEC_TABLE_MODE.md 3.5).

Owner ruling U1 (the owner rulings file, section U): a table package supplies ready rows, one table per lead;
the engine skips the grid-only steps and keeps the simple date checks. So this orchestration runs the SAME rules
as derive_all (derive/orchestrate.py) where a table has their inputs, through the same functions, and replaces
the grid-only ones by what the table declares:
  - R1 is the irregular cadence by declaration (U1; owner item O2: R1's cadence detection is not run);
  - R8 is an empty lag map (U1: the package's features already end before the issue date; no lag is computed),
    R4 the first year of any valid row with no lag source;
  - R3 counts the valid rows per group and year (is_events True: the last year with any valid row);
  - R18's unit lists are every row of a group (bank) and its TEST-marked rows (scored), U1 (the package marks
    train and test; R18 (2)'s stride pick is not used: TABLE_LIMITS);
  - R19 is planned at all six bank cuts (lead 0's fit and guard cuts and each lead's two), each from the lead's
    own rows (labels.rows.RowLabelView.for_lead); a group with no row at any of them refuses (owner item O13);
  - R23 is planned per lead fit cut and per decision-surface fold (signed R13: fold g's c comes from the lead-0
    guard-cut donor rows outside g's overlap block).
Every label read goes through a RowLabelView built with run_folder None (validity and donor views only). The
kind R12 picks must be the neighbour kind: the table option builds that kind only (U3; owner item O16).
"""
# Provenance for the module: SPEC_TABLE_MODE.md 3.5 (the entry table) and 2.1 (T-MARK); derive/orchestrate.py
# derive_all (the order and the guards it copies); OWNER_RULINGS_2026-10-06.md U1, U3, I1; APP_PLAN.md R13
# (fold c "from the rows outside g's block at or before the inner-fit end").

import datetime as _dt
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np

from treeroute import engine_constants as K
from treeroute import split as _split
from treeroute.package.table import MARK_TEST, MARK_TRAIN, U2_VOUCHED

from . import router_rules as RR
from . import rules as R
from . import unit_rules as UR
from .derived import DeriveRefusal, make_derived, sha256_of_array, sha256_of_json
from .shapes import Cadence, CadenceKind, CutKind, Link, MissingShares, RouterKind

U1_RULE = ("owner ruling U1: the table option; the package supplies one row per sample in one table per lead, the "
           "engine computes no lag and runs no package code, and checks the dates it can check")
R1_TABLE = "declared by the table option (ruling U1): a table's rows are events (irregular dates per unit)"
R8_TABLE = ("ruling U1: no lag is computed for a table; each lead's file holds features that already end before "
            "the row's issue date (vouched by the package owner, U2)")
R18_TABLE = "U1: the package marks train and test (bank = every row of the group, scored = its test-marked rows)"
_SHOW = 5


def _year(day: int) -> int:
    return _dt.date.fromordinal(int(day)).year


def _years(days: np.ndarray) -> np.ndarray:
    distinct, inverse = np.unique(np.asarray(days, dtype=np.int64), return_inverse=True)
    years = np.array([_year(d) for d in distinct.tolist()], dtype=np.int64)
    return years[np.asarray(inverse).reshape(-1)]


def _first_day(year: int) -> int:
    return _dt.date(int(year), 1, 1).toordinal()


def _last_day(year: int) -> int:
    return _dt.date(int(year), 12, 31).toordinal()


def check_marks(data: Any, windows: Any) -> Dict[str, Any]:
    """T-MARK (R5, R6; owner item O1): a train row's target date is at or before 31 December of the train end
    year; a test row's target date lies inside the test years; the marks equal the derived window exactly."""
    days = np.asarray(data.target_day, dtype=np.int64)
    test = np.asarray(data.is_test, dtype=bool)
    lo, hi = _first_day(min(windows.test_years)), _last_day(max(windows.test_years))
    in_window = (days >= lo) & (days <= hi)
    after = days > hi
    rows = np.asarray(data.row_ids, dtype=object)
    bad_train = ~test & ~(days <= _last_day(windows.train_end))
    bad_test = test & ~in_window
    if bad_train.any() or bad_test.any() or after.any():
        raise DeriveRefusal("R5", "T-MARK: the package's marks differ from the derived window (train end %d, test "
                            "years %s): %d train row(s) dated after the train end (e.g. %s), %d test row(s) outside "
                            "the test years (e.g. %s), %d row(s) after the last test year"
                            % (windows.train_end, list(windows.test_years), int(bad_train.sum()),
                               rows[bad_train][:_SHOW].tolist(), int(bad_test.sum()), rows[bad_test][:_SHOW].tolist(),
                               int(after.sum())),
                            fix="owner item O1: set the marks from the derived window (R3 events, R5)")
    return {"train_rows": int((~test).sum()), "test_rows": int(test.sum()), "train_end": int(windows.train_end),
            "test_years": list(windows.test_years), "rule": "T-MARK: marks equal the derived window (O1)"}


def derive_all_table(package: Any, spec: Any, data: Any, leads: Sequence[int]) -> Dict[str, Any]:
    """Every plan-time rule of a table run (module docstring; SPEC_TABLE_MODE.md 3.5). data: package/table.TableData
    (the run's rows: a smoke's rows for a smoke, as the grid smoke derives on its own rows). Returns
    {entry name: Derived}. Refuses: the first rule that refuses (fail loudly); T-MARK; a kind other than neighbour;
    a group with no row at a bank cut (O13)."""
    from treeroute.labels.rows import build_row_vault

    out: Dict[str, Any] = {}
    rows = np.asarray(data.row_ids, dtype=object)
    groups_of_row = np.asarray(data.groups, dtype=object)
    units = np.asarray(data.units, dtype=object)
    days = np.asarray(data.target_day, dtype=np.int64)
    n = rows.size
    leads = tuple(sorted(int(L) for L in leads))
    out["U1:table"] = make_derived("U1", {
        "rows_per_lead": {str(L): int(data.leads[L].present.sum()) for L in leads},
        "rows_absent_per_lead": {str(L): {"train": int((~data.leads[L].present & ~data.is_test).sum()),
                                           "test": int((~data.leads[L].present & data.is_test).sum())} for L in leads},
        "max_feature_end_minus_issue_day": {str(L): data.leads[L].max_feature_end_gap for L in leads}},
        {"rule": U1_RULE, "files": data.data_manifest["files"], "row_grid_hash": sha256_of_array(rows),
         "run_rows": int(n), "excluded_groups": list(data.dropped_groups)})
    out["U2:vouched"] = make_derived("U2", list(U2_VOUCHED), {"rule": "owner ruling U2"})

    # R1, R2 (events), R8 (no lags), R4
    repeat = int(np.sum(np.unique(units.astype(str), return_counts=True)[1] > 1))
    cadence = Cadence(kind=CadenceKind.IRREGULAR)
    out["R1"] = make_derived("R1", cadence, {"rule": R1_TABLE, "rows": int(n),
                                             "package_units": int(len(set(units.tolist()))),
                                             "repeat_visit_units": repeat})
    out["R2"] = R.derive_r02_season_key(cadence, None)
    season = out["R2"].value
    out["R8"] = make_derived("R8", {}, {"rule": R8_TABLE})
    valid = np.isfinite(np.asarray(data.y, dtype=np.float64))
    if not valid.any():
        raise DeriveRefusal("R4", "the table holds no valid label", fix="check the target column")
    years = _years(days)
    out["R4"] = R.derive_r04_first_year(int(years[valid].min()), {})

    # the groups (leave one region out), R3 events
    split_sets = _split.loro_split_sets(package.split)
    data_groups = tuple(sorted(set(groups_of_row.tolist())))
    diff = _split.loro_split_differences(split_sets, data_groups)
    if diff.listed_not_in_data or diff.reported_and_excluded or diff.duplicates:
        raise DeriveRefusal("G-SPLIT", "split.yaml differs from the data: %s" % (diff,),
                            fix="list only groups the data holds; a reported group is never excluded")
    groups = _split.groups_under_loro(split_sets, data_groups)
    out["R18:groups"] = make_derived("R18", groups, {
        "data_groups": len(data_groups), "excluded": dict(split_sets.excluded),
        "seen_during_design": list(split_sets.seen_during_design),
        "design": "leave one region out: every group trains its own trees and is tested"})
    probe = build_row_vault(data, int(days.max()) + 1, None)          # validity only before R5 fixes the window
    _, _, v_valid = probe.validity(int(days.min()), int(days.max()))
    counts = R.count_valid_rows_per_group_year(groups_of_row, years, v_valid, np.ones(n, dtype=bool), groups)
    out["R3"] = R.derive_r03_coverage_end(counts, groups, True)

    # R5 - R7, T-MARK, R10, R11, R9
    y0, y_end = int(out["R4"].value), int(out["R3"].value)
    out["R5"] = R.derive_r05_test_window(y0, y_end)
    out["R6"] = R.derive_r06_train_end(out["R5"].value.test_years)
    out["R7"] = R.derive_r07_inner_windows(y0, y_end, out["R5"].value, out["R6"].value)
    windows = out["R7"].value
    out["R5:marks"] = make_derived("R5", check_marks(data, windows), {"rule": "T-MARK (SPEC_TABLE_MODE.md 2.1)"})
    out["R10"] = R.derive_r10_leads(season, True)
    if (0,) + tuple(out["R10"].value.leads) != leads:
        raise DeriveRefusal("R10", "the table's lead files %s are not lead 0 and R10's leads %s"
                            % (list(leads), list(out["R10"].value.leads)))
    out["R11"] = R.derive_r11_cuts(windows, out["R10"].value, cadence)
    cuts = out["R11"].value
    out["R9"] = R.derive_r09_freeze_epochs({}, R.cut_days(cuts, cadence))

    test_first = _first_day(min(windows.test_years))
    vault = build_row_vault(data, test_first, None)
    fit0, guard0 = int(cuts[0].fit_cut), int(cuts[0].guard_cut)
    y0_day = _first_day(y0)
    inner_end = _last_day(windows.inner_fit[1])

    # candidates (package units, per group), R12 on package units (validity only)
    v_units, v_days, v_valid = vault.validity(int(days.min()), fit0)
    pos_of = {str(r): i for i, r in enumerate(rows.tolist())}
    v_idx = np.asarray([pos_of[str(u)] for u in v_units.tolist()], dtype=np.int64)
    v_pu = units[v_idx]
    v_groups = groups_of_row[v_idx]
    candidates = {g: _split.candidate_units(v_pu, v_groups, v_days, v_valid, g, fit0) for g in groups}
    every = sorted({u for g in groups for u in candidates[g]})
    w_units, w_days, w_valid = vault.validity(y0_day, inner_end)
    w_pu = units[np.asarray([pos_of[str(u)] for u in w_units.tolist()], dtype=np.int64)]
    inner_counts = {u: 0 for u in every}
    for u, ok in zip(w_pu.tolist(), w_valid.tolist()):
        if ok and u in inner_counts:
            inner_counts[u] += 1
    out["R12"] = RR.derive_r12_router_kind(inner_counts)
    kind = out["R12"].value
    if getattr(kind, "value", kind) != RouterKind.NEIGHBOUR.value:
        raise DeriveRefusal("R12", "R12 picks the %s kind for this table (h = %s); the table option builds the "
                            "neighbour kind only (U3)" % (getattr(kind, "value", kind), out["R12"].inputs.get("h")),
                            fix="owner item O16: build table versions of the per-unit and region kinds")

    # R13, R14 (and the overlap blocks over the package units), R17
    out["R13"] = RR.derive_r13_surface_loro(kind, groups)
    out["R14"] = RR.derive_r14_router_design(kind, tuple(spec.context))
    first_of_unit: Dict[str, int] = {}
    for i, u in enumerate(units.tolist()):
        first_of_unit.setdefault(str(u), i)
    order = sorted(first_of_unit)
    idx = np.asarray([first_of_unit[u] for u in order], dtype=np.int64)
    out["R14:overlap_blocks"] = _split.derive_overlap_blocks(groups_of_row[idx], np.asarray(data.lat)[idx],
                                                             np.asarray(data.lon)[idx], None, None)
    blocks = out["R14:overlap_blocks"].value
    out["R17"] = RR.derive_r17_history_spec(season, None, cadence, kind, True)

    # R18: every row of a group is a bank unit; its test rows are the scored units (U1)
    bank = {g: tuple(rows[groups_of_row == g].tolist()) for g in groups}
    test = np.asarray(data.is_test, dtype=bool)
    scored = {g: tuple(rows[(groups_of_row == g) & test].tolist()) for g in groups}
    lists = _split.UnitLists(bank=bank, scored=scored)
    out["R18:units"] = make_derived("R18", lists, {
        "bank_units_hash": {g: _split.unit_ids_hash(bank[g]) for g in groups},
        "scored_units_hash": {g: _split.unit_ids_hash(scored[g]) for g in groups},
        "rule": R18_TABLE})
    bank_rows = tuple(u for g in groups for u in bank[g])

    # R19 at lead 0's two cuts (the approved rules) and at each lead's two cuts (O13)
    donor = vault.donor_labels(split_sets, fit0, CutKind.FIT, 0, bank_rows, "bank_plan", picks=lists)
    out["R19"] = UR.derive_r19_bank_plan(donor, False)
    inner = vault.donor_labels(split_sets, guard0, CutKind.GUARD, 0, bank_rows, "bank_plan_inner_cut", picks=lists)
    out["R19:inner_cut"] = UR.derive_r19_inner_cut_bank_plan(inner, False)
    lead_views = {0: vault}
    for L in leads:
        if L == 0:
            continue
        view = vault.for_lead(data.leads[L].present, L)
        lead_views[L] = view
        for name, cut, ck in (("fit", int(cuts[L].fit_cut), CutKind.FIT), ("guard", int(cuts[L].guard_cut), CutKind.GUARD)):
            d = view.donor_labels(split_sets, cut, ck, L, bank_rows, "bank_plan_lead_%d_%s" % (L, name), picks=lists)
            out["R19:lead=%d:%s" % (L, name)] = _lead_bank_rows(d, groups, L, name)
    out["R20"] = UR.derive_r20_batching(True, groups)
    out["R21"] = UR.derive_r21_smoke_plan_loro(groups)

    # R22, R23 per lead fit cut and per fold, R28
    out["R22"] = R.derive_r22_links(tuple(spec.legal_range), donor)
    if Link.LOG_C in out["R22"].value:
        for L in leads:
            cut = int(cuts[L].fit_cut)
            view = lead_views[L].donor_labels(split_sets, cut, CutKind.FIT, L, bank_rows, "links", picks=lists)
            out["R23:lead=%d" % L] = R.derive_r23_c_for_cut(view)
        for fold, (g,) in enumerate(out["R13"].value[1]):
            left = _split.block_of_group(blocks, g)
            keep = tuple(u for h in groups if h not in left for u in bank[h])
            view = vault.donor_labels(split_sets, guard0, CutKind.GUARD, 0, keep, "links_fold", picks=lists)
            out["R23:fold=%s" % g] = fold_c_entry(view, fold, g, left)
    out["R28"] = R.derive_r28_clip_bounds(tuple(spec.legal_range))

    # R30 over the R19 donor rows (train rows at the lead-0 fit cut) and the test years' rows (lead 0)
    pos = np.asarray([pos_of[str(u)] for u in donor.unit_ids.tolist()], dtype=np.int64)
    X0 = data.leads[0].tree
    miss, zero, by_year = {}, {}, {}
    for j, c in enumerate(spec.tree_features):
        d = X0[pos, j].astype(np.float64)
        miss[c] = float(np.isnan(d).mean()) if d.size else 0.0
        zero[c] = float((d == 0).mean()) if d.size else 0.0
        for yr in windows.test_years:
            sel = years == int(yr)
            if sel.any():
                by_year[(c, int(yr))] = float(np.isnan(X0[sel, j]).mean())
    shares = MissingShares(donor_row_key_hash=donor.row_key_hash, donor_unit_scope=donor.unit_scope,
                           donor_training_missing_share=miss, donor_training_zero_share=zero,
                           test_year_missing_share=by_year)
    out["R30"] = UR.derive_r30_missing_flags(shares, {})
    return out


def _lead_bank_rows(donor: Any, groups: Tuple[str, ...], lead: int, which: str) -> Any:
    """The rows per group of one lead's bank cut (R19's count, applied at every bank cut: owner item O13). A group
    with no row refuses with R19's own message (derive/unit_rules.py _bank_plan)."""
    g = np.asarray(donor.group_of_row, dtype=object)
    names, counts = np.unique(g, return_counts=True)
    rows = {str(a): int(b) for a, b in zip(names.tolist(), counts.tolist())}
    empty = [x for x in groups if rows.get(x, 0) == 0]
    if empty:
        raise DeriveRefusal("R19", "%d groups have no donor row at the cut, e.g. %s: a group with no row cannot train "
                            "its trees (lead %d, %s cut %d; owner item O13)"
                            % (len(empty), empty[:_SHOW], lead, which, int(donor.cut)),
                            fix="exclude the group in split.yaml, with its reason, or check its units")
    return make_derived("R19", {"rows_per_group": {x: rows[x] for x in groups}, "lead": int(lead), "cut": int(donor.cut),
                                "cut_kind": which},
                        {"rule": "R19's rows per group at this lead's %s cut, from the lead's own rows (O13)" % which},
                        {"donor_row_key_hash": str(donor.row_key_hash)})


def fold_c_entry(view: Any, fold: int, group: str, left_out: Tuple[str, ...]) -> Any:
    """R23 for one decision-surface fold (signed R13: fold g's c from the lead-0 guard-cut donor rows outside g's
    overlap block): c_from_donor_y, the one R23 formula, on the view's labels; recorded with the lead, cut and cut
    kind check_r23_matches_run reads, the fold and its left-out block, and the view's row-key hash."""
    c, positive = R.c_from_donor_y(np.asarray(view.y))
    donor = {"unit_scope": getattr(view.unit_scope, "value", view.unit_scope), "cut": int(view.cut),
             "cut_kind": getattr(view.cut_kind, "value", view.cut_kind), "lead": int(view.lead),
             "groups": list(view.groups), "rows": int(np.asarray(view.y).size), "fold": int(fold),
             "fold_group": str(group), "left_out_block": list(left_out)}
    return make_derived("R23", c, {"donor": donor, "positive_rows": positive,
                                   "percentile_method": "linear (numpy default, D62)",
                                   "rule": "signed R13: fold g's c from the guard-cut donor rows outside g's block"},
                        {"donor_row_key_hash": str(view.row_key_hash)})


__all__ = ["derive_all_table", "check_marks", "fold_c_entry", "U1_RULE", "R8_TABLE", "R18_TABLE"]
