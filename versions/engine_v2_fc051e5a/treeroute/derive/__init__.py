"""treeroute.derive: the derive rules (plan Section 2), derive_all and derived.json. SCIENCE:
owner-approved signatures, agent bodies, under leave one region out (owner rulings D and E; rulings F
for the Tuesday-build follow-ups).

Modules:
  - rules.py         R1 cadence; R2 season key; R3 coverage end over the joined rows of every group (F2);
                     R4 first year with its kept-column guard; R5 test window with the short-record
                     ladder; R6 train end; R7 inner windows; R8 feature lags; R9 freeze epochs (and the
                     day form of the cuts it reads); R10 leads; R11 cuts; R22 links; the plan-time
                     records of R23 (c per lead cut, its one formula and the run's agreement check) and
                     R28 (clip bounds), whose approved home is layer/.
  - router_rules.py  R12 router kind (h over every group's candidate units), its valid-row counter
                     and the constant-history share; R13 decision surface under LORO; R14 router
                     design; R17 own-history spec.
  - unit_rules.py    R18 bank and scored counts (C16, the event floor); R19 bank plan (and the
                     inner-cut bank's plan, L6 b); R20 batching; R21 smoke plan under LORO; R30
                     missing-value flags.
  - orchestrate.py   derive_all, with its guards (R8 covers the kept columns; the G-EPOCH stand-in;
                     R23 against independently rebuilt donor rows) and the plan-time label reader that
                     stands in for the vault until labels/vault.py exists.
  - derived.py       the Derived helpers, borderline flags, hashes and the write-once writer.
  - shapes.py        field-identical copies of the approved shapes.

The unit LISTS, the groups and the overlap blocks are split's (treeroute/split.py); derive calls it.
Every rule is a pure function returning a Derived; nothing here reads split.yaml or writes a file
except write_derived_json, which the caller points at a run folder.
"""

# Import order matters: treeroute.split imports Derived, make_derived and sha256_of_array from this
# package, and unit_rules / orchestrate import split, so those three names are bound first.
from .derived import (DeriveRefusal, borderline_flags, derived_document, derived_entry, derived_sha256,
                      jsonable, make_derived, sha256_of_array, sha256_of_json, write_derived_json)
from .shapes import (Cadence, CadenceKind, CalendarPart, CutDays, CutKind, CutPair, Derived, DonorLabels,
                     GridPoint, HistorySpec, Lag, LeadPlan, LeadUnit, Link, LoroSurfaceKind,
                     MissingShares, RouterDesign, RouterKind, SeasonKeyKind, SeasonKeySpec, StepUnit,
                     TestWindowPlan, Windows)
from .rules import (c_from_donor_y, check_r08_covers_kept_columns, check_r23_matches_run,
                    count_valid_rows_per_group_year, cut_days, derive_r01_cadence,
                    derive_r02_season_key, derive_r03_coverage_end, derive_r04_first_year,
                    derive_r05_test_window, derive_r06_train_end, derive_r07_inner_windows,
                    derive_r08_feature_lags, derive_r09_freeze_epochs, derive_r10_leads,
                    derive_r11_cuts, derive_r22_links, derive_r23_c_for_cut, derive_r28_clip_bounds)
from .router_rules import (constant_history_share, count_valid_rows_per_unit, derive_r12_router_kind,
                           derive_r13_surface_loro, derive_r14_router_design, derive_r17_history_spec)
from .unit_rules import (EventRate, derive_r18_bank_count, derive_r18_scored_count, derive_r19_bank_plan,
                         derive_r19_inner_cut_bank_plan, derive_r20_batching, derive_r21_smoke_plan_loro,
                         derive_r30_missing_flags, donor_event_rate, scored_counts_at_event_rate)
from .orchestrate import derive_all

RULE_HOME = {
    "R1": "derive.rules.derive_r01_cadence",
    "R2": "derive.rules.derive_r02_season_key",
    "R3": "derive.rules.derive_r03_coverage_end",
    "R4": "derive.rules.derive_r04_first_year",
    "R5": "derive.rules.derive_r05_test_window",
    "R6": "derive.rules.derive_r06_train_end",
    "R7": "derive.rules.derive_r07_inner_windows",
    "R8": "derive.rules.derive_r08_feature_lags",
    "R9": "derive.rules.derive_r09_freeze_epochs",
    "R10": "derive.rules.derive_r10_leads",
    "R11": "derive.rules.derive_r11_cuts",
    "R12": "derive.router_rules.derive_r12_router_kind",
    "R13": "derive.router_rules.derive_r13_surface_loro",
    "R14": "derive.router_rules.derive_r14_router_design",
    "R17": "derive.router_rules.derive_r17_history_spec",
    "R18": "derive.unit_rules.derive_r18_scored_count",
    "R19": "derive.unit_rules.derive_r19_bank_plan",
    "R20": "derive.unit_rules.derive_r20_batching",
    "R21": "derive.unit_rules.derive_r21_smoke_plan_loro",
    "R22": "derive.rules.derive_r22_links",
    "R30": "derive.unit_rules.derive_r30_missing_flags",
}

# Rules whose approved home (the approved RULE_HOME) is layer/: derive writes only a plan-time record of
# the same value, so derived.json shows it before the run. {rule: (derive's record, the rule's home)}.
# R23: both sides compute c with c_from_donor_y and the run calls check_r23_matches_run. R28: both read
# the target's one cited legal range.
PLAN_TIME_RECORDS = {
    "R23": ("derive.rules.derive_r23_c_for_cut", "layer.c_for_cut"),
    "R28": ("derive.rules.derive_r28_clip_bounds", "layer.clip_to_legal"),
}

# The LORO additions supersede three approved derive_rules signatures (SIGNATURES_LORO_ADDENDUM.md,
# "Superseded signatures"): {approved name: the function(s) that replace it}. R18's bank count is the
# other half of the old unit count; RULE_HOME names the scored count, which returns both counts.
SUPERSEDED = {
    "derive_r13_decision_surface": ("derive_r13_surface_loro",),
    "derive_r18_unit_count": ("derive_r18_bank_count", "derive_r18_scored_count"),
    "derive_r21_smoke_plan": ("derive_r21_smoke_plan_loro",),
}

__all__ = [
    "DeriveRefusal", "borderline_flags", "derived_document", "derived_entry", "derived_sha256",
    "jsonable", "make_derived", "sha256_of_array", "sha256_of_json", "write_derived_json",
    "c_from_donor_y", "check_r08_covers_kept_columns", "check_r23_matches_run",
    "count_valid_rows_per_group_year", "cut_days", "derive_r01_cadence", "derive_r02_season_key",
    "derive_r03_coverage_end", "derive_r04_first_year", "derive_r05_test_window",
    "derive_r06_train_end", "derive_r07_inner_windows", "derive_r08_feature_lags",
    "derive_r09_freeze_epochs", "derive_r10_leads", "derive_r11_cuts", "derive_r22_links",
    "derive_r23_c_for_cut", "derive_r28_clip_bounds",
    "constant_history_share", "count_valid_rows_per_unit", "derive_r12_router_kind",
    "derive_r13_surface_loro", "derive_r14_router_design", "derive_r17_history_spec",
    "derive_r18_bank_count", "derive_r18_scored_count", "derive_r19_bank_plan",
    "derive_r19_inner_cut_bank_plan", "derive_r20_batching",
    "derive_r21_smoke_plan_loro", "derive_r30_missing_flags", "donor_event_rate", "EventRate",
    "scored_counts_at_event_rate", "derive_all",
    "Cadence", "CadenceKind", "CalendarPart", "CutDays", "CutKind", "CutPair", "Derived", "DonorLabels",
    "GridPoint", "HistorySpec", "Lag", "LeadPlan", "LeadUnit", "Link", "LoroSurfaceKind",
    "MissingShares", "RouterDesign", "RouterKind", "SeasonKeyKind", "SeasonKeySpec", "StepUnit",
    "TestWindowPlan", "Windows",
    "RULE_HOME", "PLAN_TIME_RECORDS", "SUPERSEDED",
]
