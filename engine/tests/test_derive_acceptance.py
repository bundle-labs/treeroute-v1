"""Acceptance: derive/ on the four real packages against their expected_derived.json (plan 3.2, the M1
gate), under leave one region out (owner rulings D, E and F).

Fields checked: cadence, season key, Y0, Y_end, the windows, leads, links (plan 3.2's first rows) and the
LORO rows: the groups (their count and the exclusions from split.yaml), the valid rows per unit, the
router kind, the decision surface, the router design, the history block, the bank and scored unit
counts, the bank's trees, the router's tree columns in a one- and a two-group block, the region
router's fit budget (region packages; None elsewhere), and the R30 flags. The overlap blocks (plan 3.2
R14_overlap_blocks, and R14_tree_columns' groups_in_two_group_blocks) are listed as NOT CHECKED: the
packages declare no static table over their candidate units yet, and derive_all's approved signature
carries none (the plan command records split.derive_overlap_blocks beside derived.json).

THIS TEST DOES NOT EXERCISE derive_all past the facts checks. Since owner ruling J installed the ban lists
(2026-10-05), every non-key column has a verdict and the closed world (io.apply_verdicts) passes; on the
bare package derive_all then refuses at R8 when kept feature-script outputs have no store facts (the
pipeline adds their facts with pipeline.data.augment_package), which
test_derive_all_passes_the_closed_world_and_needs_only_the_feature_script_facts reports; and it needs the
whole target table and every candidate unit's labels in memory, which the largest stores exceed (hundreds
of millions of rows). So this test RE-ORCHESTRATES THE RULES ITSELF, streaming the stores group by group;
what it checks is each rule on the real data, not derive_all's orchestration (tests/test_derive_all.py
covers that on synthetic packages).

READ-ONLY: the packages are loaded with treeroute.package.load (which verifies the included store
catalogs' hashes) and the stores are read in place with treeroute.io.readers; nothing is written.
  - The groups: split.yaml holds only exclusions and seen_during_design; the groups are the target
    store's groups minus the exclusions (split.groups_under_loro), every one trained and tested.
  - Kept candidates: the columns that ENTER after the verdicts, exactly as derive_all takes them
    (orchestrate._Facts): io.apply_verdicts' tree features (driver, engineered) and router context.
    'ban' and 'conditional' leave every engine run (io.apply LEAVE), so a conditional column is not a
    candidate. UPDATED 2026-10-06 (agent C1, review fix): before, every column not BANNED was a candidate
    (the rule before ruling J installed the ban lists), so conditional columns entered R4 here and on
    PM2.5 set a Y0 the engine never derives. An entering ENGINEERED column counts when it has store
    facts (a store catalog declares it: e.g. a store of yearly aggregates and lag columns a package's
    store builder writes). None is dropped silently: a
    driver / router_context candidate without store facts makes R8 refuse as derive_all does (e.g.
    router context built by the feature script, which records its facts only when it runs), and a
    candidate without store facts or held by no declared driver store makes the F2 presence below
    incomplete, so Y_end and every field computed from it are PROVISIONAL. An engineered column WITHOUT
    store facts is one the feature script builds (its facts come from the script; the pipeline adds them
    with pipeline.data.augment_package): R8 / R4 here do not see it, and the Y0 note counts them.
    UPDATED 2026-10-06 (agent C1, review fix): engineered store columns were not candidates before, so on
    a package whose lag columns live in a store (e.g. year t-2 copies) R4 here could not see the lag that
    sets Y0, and a Y0 match was no evidence.
  - A driver store that holds kept candidates but has NO file for some LORO groups it does not declare
    absent is NOT BUILT for those groups (a run stops at the driver read there, G-MISSING): it is left out
    of the presence below (its columns count as held by no store, so the presence is incomplete and the
    fields from it PROVISIONAL), and R4's reader asks no store for its columns. The note names it.
  - R3 (owner ruling F2): per (group, year), the rows with a VALID label (finite y, D6) AND the kept
    drivers present, over EVERY group (C3 under LORO). Presence is measured here per (group, year), NOT
    per row: a driver store that holds a kept candidate must hold that group's rows for that year (from
    its file listing, or from its year column when one file holds every year), or declare the group
    absent (F8). The io join will give the per-row flag; the rule itself takes per-row flags.
  - R1: every unit of the first group (sorted), all years. A target store without the unit key (keyed
    by lat/lon until its ingest maps cell ids) uses '{group}_{lat}_{lon}' with the S1 decimals.
  - R8 columns: the kept candidates that have store facts; its report note says what R8 could lag.
  - R4 (owner ruling J5): the ENGINE's own R4 entry builder (orchestrate._r04_entry: the lag-operation
    look-back, the driver stores' first years, derive_r04_first_year) runs on one row per target (group,
    year), with a column reader that answers drivers_present from the stores' (group, year) presence
    listing (_PresenceReader, F2 / F8 as the pipeline's reader answers it), so a regression in the
    engine's J5 code shows here on the real data. Its refusals are R4 outcomes.
  - Candidates (R18) and h (R12): per unit, the valid rows per year, summed over the windows.
  - The event rate (R18's floor, D14): every valid label of every unit at or before the train end whose
    own label window has ended by the cut. Hundreds of millions of values do not fit a label-only donor
    view in memory, so the exact 90th percentile and the event count are STREAMED (two passes: a
    histogram of the float64 values, then the values of the bins that hold the two order statistics)
    and fed to derive.scored_counts_at_event_rate, the half of derive_r18_scored_count after the rate.
    On the smallest package the approved derive_r18_scored_count also runs on the full label-only view
    and must agree; a unit test checks the stream against donor_event_rate on synthetic arrays.
  - R19, R22, R23: the label-only donor view of every group's BANK units at the nowcast fit cut (and
    at each lead's fit cut for R23, and at the inner cut for the inner-cut bank's plan, L6 b), with the
    label-window rule (a label counts once its own window has ended by the cut). Each R23 entry is
    checked with check_r23_matches_run against the bank rows re-selected by timing.label_usable per
    step (not by the walk-back the views use).
  - The unit lists: the bank and scored lists are checked against the plan's formulas written here
    (the stride over the sorted candidates; positions floor(i x (N-1) / (m-1)) of the bank).
  - When R1 or R4 refuses, the rules downstream take the EXPECTED cadence or Y0, so the LORO rows are
    still exercised on the real data. A field computed from an expected value, or from incomplete
    driver presence, is PROVISIONAL: a match is reported as xfail ('not M1 evidence'), never as a
    pass, and a mismatch still fails.
  - A target value at or beyond the sentinel magnitude is refused (D30: the ingest writes NaN).

Outcomes: a field that matches passes. A field listed in KNOWN_DIFFERENCES is REPORTED as xfail with the
derived value (or the refusal) beside the expected one; it is strict, so a listed field that starts to
match fails until the list is updated. A KNOWN difference that waits for an owner choice also has its derived
value pinned in PENDING_OWNER_DERIVED: a different derived value fails. Any other mismatch or refusal FAILS.
Values are never patched in
engine code (plan 3.2); corrections belong in the package's expected_derived.json or its facts.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from conftest import ENGINE_DIR
from test_derive_shapes import DonorView
from treeroute import derive as D
from treeroute import engine_constants as K
from treeroute import split as SP
from treeroute import timing
from treeroute.derive import orchestrate as O
from treeroute.errors import RefusedError
from treeroute.io.apply import apply_verdicts
from treeroute.io.listing import list_store
from treeroute.io.readers import read_columns, read_footer
from treeroute.io.steps import step_bounds, step_index
from treeroute.package.load import load_package

PACKAGES = ("pm25", "fire", "defo", "ndvi")
FIELDS = ("cadence", "season_key", "y0", "y_end", "test_years", "train_end", "inner_fit",
          "inner_score", "leads", "links", "groups", "valid_rows_per_unit", "router_kind",
          "decision_surface", "router_design", "history", "bank_units", "scored_units", "bank_trees",
          "tree_columns", "overlap_blocks", "region_fit", "missing_flags")
# the upstream values each field is computed from that may have been replaced by the expected value
# ('cadence', 'y0') or measured incompletely ('presence': F2 over only the candidates a store holds)
_W = {"y0", "presence"}                     # the windows: Y0 (R4) and Y_end (R3, F2 presence)
# Y0 also depends on the presence: R4's first data year (J5) is read through the same presence listing
DEPENDS = {"cadence": set(), "season_key": {"cadence"}, "y0": {"cadence", "presence"}, "y_end": {"presence"},
           "test_years": _W, "train_end": _W, "inner_fit": _W, "inner_score": _W,
           "leads": {"cadence"}, "links": {"cadence"} | _W, "groups": set(),
           "valid_rows_per_unit": _W, "router_kind": _W, "decision_surface": _W,
           "router_design": _W, "history": {"cadence"} | _W, "bank_units": _W,
           "scored_units": {"cadence"} | _W, "bank_trees": set(), "tree_columns": set(),
           "overlap_blocks": set(), "region_fit": _W, "missing_flags": set()}

_R30_NOT_RUN = ("R30 is not run: its shares come from the io column reader (MissingShareReader, not "
                "built), measured after R8's lags, which R8 refuses on this package today")
_UNPENALISED = ("derive's R14 lists the intercept among the unpenalised blocks, as the router's own "
                "design does (route/kinds.py per_unit_router_design); expected_derived.json lists the "
                "normal only: correct the json, or the owner rules the reading")
_BLOCKS_NOT_CHECKED = ("NOT CHECKED: the overlap blocks need the static table over the candidate units "
                       "(split.derive_overlap_blocks); the package declares none yet (plan 1.2; fire's "
                       "cells_1000 covers its sidecar cells only) and derive_all's approved signature "
                       "carries none, so the plan command must record them beside derived.json")
_NO_FACTS_R8 = ("R8 cannot run on the kept candidates: some have no store facts (router context the "
                "feature script builds), which derive_all refuses before R8")
# (package, field): why it differs today. Reported (strict xfail), never patched in engine code.
_Y0_OVER_THE_REST = ("; R8 refuses none of the candidates with facts since ruling L1 (b) (2026-10-06) signed the index "
                     "windows (G-LAG refused them before); over the candidates R8 can lag (the columns that ENTER after "
                     "the verdicts, io.apply_verdicts), R4 gives Y0 2003, the expected value (measured 2026-10-06 "
                     "12:28-12:54)")
KNOWN_DIFFERENCES = {
    ("pm25", "y0"): _NO_FACTS_R8 + _Y0_OVER_THE_REST + "; before that day's review fix four 'conditional' columns "
                                                       "(V15_bare_ground_pct, V17_herb_cover_pct, phenology_sos_doy, "
                                                       "tree_cover_pct) still counted here and gave a Y0 of 2004 the "
                                                       "engine never derives",
    ("fire", "cadence"): "the fire target store is not a complete census: units of the first group "
                         "miss whole months (R1 sees irregular spacing; plan 1.2: the ingest writes a "
                         "NaN row for every missing unit x month)",
    ("fire", "y0"): "R1 refuses the fire target (not a complete census), so R8 and R4 cannot run; R8 "
                    "would also refuse its candidates without store facts",
    ("ndvi", "y0"): _NO_FACTS_R8 + _Y0_OVER_THE_REST,
    ("pm25", "missing_flags"): _R30_NOT_RUN, ("fire", "missing_flags"): _R30_NOT_RUN,
    ("defo", "missing_flags"): _R30_NOT_RUN, ("ndvi", "missing_flags"): _R30_NOT_RUN,
    ("pm25", "router_design"): _UNPENALISED, ("fire", "router_design"): _UNPENALISED,
    ("defo", "router_design"): _UNPENALISED, ("ndvi", "router_design"): _UNPENALISED,
    ("pm25", "overlap_blocks"): _BLOCKS_NOT_CHECKED, ("fire", "overlap_blocks"): _BLOCKS_NOT_CHECKED,
    ("defo", "overlap_blocks"): _BLOCKS_NOT_CHECKED, ("ndvi", "overlap_blocks"): _BLOCKS_NOT_CHECKED,
}
# 2026-10-06 (defo follow-ups of owner ruling N, OWNER_RULINGS_2026-10-06.md): S17 a took candidate (a), Y0 2004, and
# datasets/defo/expected_derived.json now holds the values the engine derives for it (Y0 2004, inner fit 2004-2016,
# 13 / 16 valid rows per unit, bank 4,615 with seven capped groups, scored 2,197 = 92,274 in all, region fit 4,615 /
# 3,750 units), so the defo Y0 KNOWN entries and their pinned derived values are gone: those fields now pass or fail.
# The derived value of a KNOWN difference that waits for an owner choice, pinned: the derivation must stay at the
# candidate the review file shows (a different derived value FAILS, so the xfail is never vacuous). None waits today.
PENDING_OWNER_DERIVED = {}
N_BINS = 1 << 16
_BIN_SHIFT = np.uint64(48)


@dataclass
class Outcome:
    value: Any = None
    refusal: Optional[str] = None
    note: str = ""
    provisional: Tuple[str, ...] = ()        # upstream values that came from the EXPECTED file


@dataclass
class GroupData:
    units: np.ndarray                         # sorted unit ids (object)
    years: Tuple[int, ...]                    # the columns of counts
    counts: np.ndarray                        # [unit, year] valid rows
    joined: Dict[int, int]                    # year -> joined valid rows (F2)


@dataclass
class Real:
    name: str
    expected: Dict[str, Any]
    outcomes: Dict[str, Outcome] = field(default_factory=dict)
    derived: Dict[str, Any] = field(default_factory=dict)
    replaced: Dict[str, str] = field(default_factory=dict)     # {upstream: how it was replaced}


# ---------------------------------------------------------------------------------------------------
# reading
def _floats(table, column):
    y = table.column(column).to_numpy(zero_copy_only=False).astype(np.float64)
    big = np.isfinite(y) & (np.abs(y) >= K.SENTINEL_MASK_ABS)
    assert not big.any(), "%d target values at the sentinel magnitude (D30)" % int(big.sum())
    return y


def _unit_index(table, group, unit_col):
    """(unit ids of the file, index of each row's unit): the unit key column, or
    '{group}_{lat}_{lon}' with the S1 decimals where the store is keyed by lat/lon."""
    if unit_col in table.column_names:
        column = table.column(unit_col)
        if not pa.types.is_dictionary(column.type):
            column = column.dictionary_encode()
        dicts, idxs, offset = [], [], 0
        for chunk in column.chunks:                  # each chunk carries its own dictionary
            d = chunk.dictionary.to_numpy(zero_copy_only=False)
            dicts.append(d)
            idxs.append(chunk.indices.to_numpy().astype(np.int64) + offset)
            offset += len(d)
        codes, uniq = pd.factorize(np.concatenate(dicts))
        return np.asarray(uniq, dtype=object), codes[np.concatenate(idxs)]
    lat = table.column("lat").to_numpy().astype(np.float32)
    lon = table.column("lon").to_numpy().astype(np.float32)
    key = (lat.view(np.uint32).astype(np.uint64) << np.uint64(32)) | lon.view(np.uint32).astype(np.uint64)
    uniq, inverse = np.unique(key, return_inverse=True)
    ulat = (uniq >> np.uint64(32)).astype(np.uint32).view(np.float32)
    ulon = (uniq & np.uint64(0xFFFFFFFF)).astype(np.uint32).view(np.float32)
    fmt = "%%s_%%.%df_%%.%df" % (K.UNIT_ID_LATLON_DECIMALS, K.UNIT_ID_LATLON_DECIMALS)
    ids = np.asarray([fmt % (group, a, b) for a, b in zip(ulat.tolist(), ulon.tolist())], dtype=object)
    assert len(set(ids.tolist())) == len(ids), "two lat/lon pairs of %s share one unit id" % group
    return ids, inverse.ravel()


def _bins(y):
    """The top 16 bits of each value's order-preserving float64 key (an ordered histogram bin)."""
    b = np.ascontiguousarray(y, dtype=np.float64).view(np.uint64)
    key = np.where((b >> np.uint64(63)).astype(bool), ~b, b | np.uint64(1 << 63))
    return (key >> _BIN_SHIFT).astype(np.int64)


def exact_event_rate(hist, n, values_in_bins):
    """(events, rows, q90) of the streamed rows, the numbers donor_event_rate gives on the whole array:
    the 90th percentile by numpy's linear rule (its virtual index and interpolation), then the rows
    strictly above it. values_in_bins(lo, hi) returns (sorted distinct values, counts) of the rows in
    histogram bins lo..hi."""
    virtual = (n - 1) * float(K.EVENT_QUANTILE)
    k = int(np.floor(virtual))
    gamma = virtual - k
    k2 = min(k + 1, n - 1)
    cum = np.cumsum(hist)
    lo, hi = int(np.searchsorted(cum, k + 1)), int(np.searchsorted(cum, k2 + 1))
    vals, counts = values_in_bins(lo, hi)
    below = int(cum[lo - 1]) if lo > 0 else 0
    ranks = below + np.cumsum(counts)                     # rank (1-based) of each value's last row
    x_k = float(vals[int(np.searchsorted(ranks, k + 1))])
    x_k2 = float(vals[int(np.searchsorted(ranks, k2 + 1))])
    q90 = float(np.quantile(np.array([x_k, x_k2]), gamma))
    events = int(hist[hi + 1:].sum()) + int(counts[vals > q90].sum())
    return events, int(n), q90


def _merge_values(parts):
    if not parts:
        return np.zeros(0), np.zeros(0, dtype=np.int64)
    vals = np.concatenate([p[0] for p in parts])
    counts = np.concatenate([p[1] for p in parts])
    u, inv = np.unique(vals, return_inverse=True)
    total = np.zeros(len(u), dtype=np.int64)
    np.add.at(total, inv, counts)
    return u, total


class _Ctx(object):
    """One package: its facts, its target files by group, driver presence (F2)."""

    def __init__(self, name):
        self.root = ENGINE_DIR / "datasets" / name
        self.pkg = load_package(self.root)
        cols = self.pkg.catalog.columns
        self.target = next(c for c, f in cols.items() if f.role == "target")
        self.unit_col = next(c for c, f in cols.items() if f.role == "key_unit")
        self.time_facts = {c: f.calendar_part for c, f in cols.items() if f.role == "key_time"}
        tf = cols[self.target]
        self.target_facts = SimpleNamespace(name=self.target, window=tf.window, stamp=tf.stamp,
                                            computed_from=tuple(tf.computed_from),
                                            fact_status=tf.fact_status)
        self.legal_range = tuple(tf.legal_range)
        self.listing = list_store(self.pkg.dataset.stores.target, base=self.pkg.root)
        if not self.listing.store_root_exists or not self.listing.files:
            pytest.skip("target store of %s is not reachable (%s)" % (name, self.listing.store_root))
        self.by_group: Dict[str, list] = {}
        for key, path in self.listing.files:
            self.by_group.setdefault(key[0], []).append((key, path))
        self.per_year_files = "year" in self.listing.key_names
        self.groups = SP.groups_under_loro(SP.loro_split_sets(self.pkg.split), tuple(sorted(self.by_group)))
        self.store_facts = {}
        for catalog in self.pkg.stores.values():
            for c, f in catalog.columns.items():
                self.store_facts.setdefault(c, f)
        # the kept candidates are the columns that ENTER after the verdicts, as derive_all takes them
        # (orchestrate._Facts): io.apply_verdicts' tree features and router context. 'ban' and 'conditional'
        # leave every engine run (io.apply LEAVE), so a conditional column is never a candidate here.
        non_key = tuple(c for c, f in cols.items() if f.role not in ("key_unit", "key_group", "key_time"))
        sets = apply_verdicts(non_key, dict(self.pkg.ban.verdicts), {c: cols[c].role for c in non_key})
        entering = set(sets.tree_features) | set(sets.router_context)
        self.candidates, self.no_facts, self.script_built = {}, [], []
        self.context = tuple(sets.router_context)
        for c, f in cols.items():
            if c not in entering:
                continue
            s = self.store_facts.get(c)
            if s is None and f.role == "engineered":
                self.script_built.append(c)          # built by the feature script: not seen here
                continue
            if s is None:
                self.no_facts.append(c)
                continue
            self.candidates[c] = SimpleNamespace(name=c, cadence=s.cadence, stamp=s.stamp, window=s.window,
                                                 fact_status=s.fact_status,
                                                 co_measured_with_target=f.co_measured_with_target)
        names = pq.ParquetFile(self.listing.files[0][1]).schema_arrow.names
        self.unit_cols = [self.unit_col] if self.unit_col in names else ["lat", "lon"]
        self.unbuilt: Dict[str, Tuple[Tuple[str, ...], Tuple[str, ...]]] = {}  # template: (missing, kept)
        self.presence = self._driver_presence()
        held = set(c for p in self.presence for c in p[1])
        unbuilt = set(c for _, kept in self.unbuilt.values() for c in kept)
        # facts, but no store holds them (the columns of a store not built for some groups are counted there)
        self.not_held = [c for c in self.candidates if c not in held and c not in unbuilt]

    def presence_gap(self):
        """How F2's presence is incomplete (None when every kept candidate is measured)."""
        parts = []
        if self.no_facts:
            parts.append("%d have no store facts (e.g. %s)" % (len(self.no_facts), self.no_facts[:3]))
        if self.not_held:
            parts.append("%d have facts but no declared driver store holds them (e.g. %s)"
                         % (len(self.not_held), self.not_held[:3]))
        for template, (missing, kept) in sorted(self.unbuilt.items()):
            parts.append("driver store %s is NOT BUILT for %d of the %d LORO groups (e.g. %s; a run there stops "
                         "at the driver read, G-MISSING): its %d kept columns are left out (e.g. %s)"
                         % (template, len(missing), len(self.groups), list(missing[:3]), len(kept),
                            list(kept[:3])))
        if not parts:
            return None
        return ("driver presence (F2) measured over only the %d kept candidates a driver store holds, of "
                "%d: %s" % (len(self.candidates) - len(self.not_held),
                            len(self.candidates) + len(self.no_facts), "; ".join(parts)))

    def _driver_presence(self):
        """[(store template, its kept columns, groups declared absent, {(group, year)} held or None)]"""
        out = []
        for template in self.pkg.dataset.stores.drivers:
            listing = list_store(template, base=self.pkg.root)
            assert listing.files, "driver store %s is not reachable" % template
            names = pq.ParquetFile(listing.files[0][1]).schema_arrow.names
            kept = [c for c in self.candidates if c in names]
            if not kept:
                continue
            absent = set.intersection(*[set(getattr(self.store_facts[c], "absent_groups", {}) or {})
                                        for c in kept])
            store_groups = {k[0] for k, _ in listing.files}
            missing = tuple(g for g in self.groups if g not in store_groups and g not in absent)
            if missing:                                      # not built there: left out, never read as absent
                self.unbuilt[template] = (missing, tuple(kept))
                continue
            held: Optional[Set[Tuple[str, int]]] = set()
            if "year" in listing.key_names:
                held = {(k[0], int(k[listing.key_names.index("year")])) for k, _ in listing.files}
            elif "year" in names:
                def years_of(item):
                    k, p = item
                    ys = np.unique(read_columns(p, ["year"]).column("year").to_numpy())
                    return {(k[0], int(y)) for y in ys}
                with ThreadPoolExecutor(8) as pool:
                    for part in pool.map(years_of, listing.files):
                        held |= part
            else:
                held = None                                  # one file per group, no time dimension
            out.append((template, tuple(kept), absent, held, store_groups))
        return out

    def present(self, group, year):
        for _, _, absent, held, groups in self.presence:
            if group in absent:
                continue
            if held is None:
                if group not in groups:
                    return False
            elif (group, year) not in held:
                return False
        return True

    def files_to(self, group, last_year):
        return [(k, p) for k, p in self.by_group[group]
                if not self.per_year_files or k[1] <= last_year]

    def read(self, path, columns, units=True):
        """The unit key (read as a dictionary: test-side speed), time and given columns of one file;
        pass B reads without the unit key. read_columns' own checks run on every file first read."""
        names = (self.unit_cols if units else []) + [c for c in self.time_facts] + list(columns)
        table = pq.read_table(path, columns=names, read_dictionary=[self.unit_col]
                              if units and self.unit_cols == [self.unit_col] else None)
        assert table.column_names == names, (path, table.column_names, names)
        return table


# ---------------------------------------------------------------------------------------------------
# pass A: per unit and year, the valid rows; per year, the joined valid rows (F2)
def _pass_a(ctx, g, check_counter=False):
    """Per unit and year, the valid rows; per year, the joined valid rows (F2: the valid rows of the
    years in which every kept-column store holds the group). With check_counter, the first file's
    joined count is also taken with the rule's own counter (count_valid_rows_per_group_year) on its
    rows, and must agree."""
    parts = []
    for n_file, (key, path) in enumerate(ctx.by_group[g]):
        if n_file == 0:
            read_columns(path, ctx.unit_cols + list(ctx.time_facts) + [ctx.target])   # the io checks
        tb = ctx.read(path, [ctx.target])
        y = _floats(tb, ctx.target)
        years = tb.column("year").to_numpy().astype(np.int64)
        ids, idx = _unit_index(tb, g, ctx.unit_col)
        valid = np.isfinite(y)
        uy, inv = np.unique(years, return_inverse=True)
        if check_counter and n_file == 0:
            present = np.array([ctx.present(g, int(v)) for v in uy], dtype=bool)[inv]
            by_rule = D.count_valid_rows_per_group_year(np.full(len(y), g, dtype=object), years, valid,
                                                        present, (g,))
            here = {(g, int(v)): int((valid & present & (inv == j)).sum()) for j, v in enumerate(uy)}
            assert by_rule == {k: n for k, n in here.items() if n}, (by_rule, here)
        for j, year in enumerate(uy.tolist()):
            m = valid & (inv == j)
            parts.append((ids, int(year), np.bincount(idx[m], minlength=len(ids))))
    units = np.sort(pd.unique(np.concatenate([p[0] for p in parts])))
    years = tuple(sorted({p[1] for p in parts}))
    counts = np.zeros((len(units), len(years)), dtype=np.int64)
    index = pd.Index(units)
    for ids, year, c in parts:
        counts[index.get_indexer(ids), years.index(year)] += c
    joined = {y: int(counts[:, j].sum()) for j, y in enumerate(years) if ctx.present(g, y)}
    return GroupData(units=units, years=years, counts=counts, joined={y: n for y, n in joined.items() if n})


def _window_sum(data, first, last):
    cols = [i for i, y in enumerate(data.years) if first <= y <= last]
    return data.counts[:, cols].sum(axis=1) if cols else np.zeros(len(data.units), dtype=np.int64)


# ---------------------------------------------------------------------------------------------------
# passes C: the streamed event rate and the bank units' donor rows
def _usable_rows(ctx, tb, cadence, last_usable):
    y = _floats(tb, ctx.target)
    steps = step_index({c: tb.column(c).to_numpy() for c in ctx.time_facts}, ctx.time_facts, cadence)
    return y, steps, np.isfinite(y) & (steps <= last_usable)


def _pass_c1(ctx, g, cadence, last_year, last_usable, bank_units):
    hist = np.zeros(N_BINS, dtype=np.int64)
    rows = []
    bank = set(bank_units)
    for _, path in ctx.files_to(g, last_year):
        tb = ctx.read(path, [ctx.target])
        y, steps, ok = _usable_rows(ctx, tb, cadence, last_usable)
        hist += np.bincount(_bins(y[ok]), minlength=N_BINS)
        ids, idx = _unit_index(tb, g, ctx.unit_col)
        in_bank = np.fromiter((u in bank for u in ids.tolist()), dtype=bool, count=len(ids))[idx] & ok
        rows.append((ids[idx[in_bank]], steps[in_bank], y[in_bank]))
    return hist, rows


def _pass_c2(ctx, g, cadence, last_year, last_usable, lo, hi):
    parts = []
    for _, path in ctx.files_to(g, last_year):
        tb = ctx.read(path, [ctx.target], units=False)
        y, _, ok = _usable_rows(ctx, tb, cadence, last_usable)
        v = y[ok]
        b = _bins(v)
        sel = v[(b >= lo) & (b <= hi)]
        if len(sel):
            parts.append(np.unique(sel, return_counts=True))
    return parts


def _last_usable_step(ctx, cut, cadence):
    """The newest step whose label window has ended by the cut's last day (timing's label rule)."""
    cut_day = int(step_bounds(np.array([cut], dtype=np.int64), cadence)[1][0])
    step = int(cut)
    while True:
        first, last = step_bounds(np.array([step], dtype=np.int64), cadence)
        if timing.target_content(ctx.target_facts, (int(first[0]), int(last[0])))[1] <= cut_day:
            return step
        step -= 1


def _donor_view(rows, groups, cut, lead, last_usable, scope="picked", cut_kind="fit"):
    units = np.concatenate([r[0] for r in rows]) if rows else np.zeros(0, dtype=object)
    steps = np.concatenate([r[1] for r in rows]).astype(np.int64) if rows else np.zeros(0, np.int64)
    y = np.concatenate([r[2] for r in rows]) if rows else np.zeros(0)
    group_of_row = (np.concatenate([np.full(len(r[0]), r[3], dtype=object) for r in rows]) if rows
                    else np.zeros(0, dtype=object))
    keep = steps <= last_usable
    units, steps, y, group_of_row = units[keep], steps[keep], y[keep], group_of_row[keep]
    codes = pd.factorize(units, sort=True)[0]            # code-point order of the unit ids
    order = np.lexsort((steps, codes))
    units, steps, y, group_of_row = units[order], steps[order], y[order], group_of_row[order]
    key_hash = D.sha256_of_json([D.sha256_of_array(units), D.sha256_of_array(steps)])
    return DonorView(groups=tuple(groups), cut=int(cut), cut_kind=cut_kind, lead=int(lead), unit_scope=scope,
                     unit_ids=units, times=steps, group_of_row=group_of_row, y=y, row_key_hash=key_hash)


def _rebuilt_rows(ctx, rows, cut, cadence):
    """(y, row-key hash) of the bank rows at a cut re-selected WITHOUT the walk-back the views use:
    per distinct step, timing.label_usable(its last day, its own label window's last day, the cut's
    last day); rows in (unit id, step) order."""
    units = np.concatenate([r[0] for r in rows]) if rows else np.zeros(0, dtype=object)
    steps = np.concatenate([r[1] for r in rows]).astype(np.int64) if rows else np.zeros(0, np.int64)
    y = np.concatenate([r[2] for r in rows]) if rows else np.zeros(0)
    distinct, where = np.unique(steps, return_inverse=True)
    first, last = step_bounds(distinct, cadence)
    cut_day = int(step_bounds(np.array([cut], dtype=np.int64), cadence)[1][0])
    usable = np.array([timing.label_usable(int(b), int(timing.target_content(ctx.target_facts,
                                                                            (int(a), int(b)))[1]), cut_day)
                       for a, b in zip(first.tolist(), last.tolist())], dtype=bool)[where]
    units, steps, y = units[usable], steps[usable], y[usable]
    _, codes = np.unique(units, return_inverse=True)
    order = np.lexsort((steps, codes))
    units, steps = units[order], steps[order]
    return y[order], D.sha256_of_json([D.sha256_of_array(units.astype(object)), D.sha256_of_array(steps)])


# ---------------------------------------------------------------------------------------------------
def _run(real, rule, call, *args):
    try:
        out = call(*args)
    except RefusedError as exc:
        real.derived[rule] = exc
        return None
    real.derived[rule] = out
    return out


def _r08_as_derive_all(ctx, cadence):
    """R8 over the kept candidates, refusing first, as derive_all does, when a candidate has no store
    facts (never dropped silently)."""
    if ctx.no_facts:
        raise D.DeriveRefusal("R8", "%d kept columns have no store facts, e.g. %s: R8 cannot lag them"
                              % (len(ctx.no_facts), ctx.no_facts[:5]),
                              fix="declare their facts in a store catalog, or build them with the "
                                  "feature script, which records its output facts (plan 1.5)")
    return D.derive_r08_feature_lags(ctx.candidates, ctx.target_facts, cadence)


def _expected_cadence(real):
    e = real.expected["R1_cadence"]
    return D.Cadence(D.CadenceKind(e["kind"]), length=e["length"], unit=D.StepUnit(e["unit"]))


def _build(name: str) -> Real:
    ctx = _Ctx(name)
    real = Real(name, json.loads((ctx.root / "expected_derived.json").read_text(encoding="utf-8")))
    groups = ctx.groups
    real.derived["groups"] = groups
    real.derived["excluded"] = dict(SP.loro_split_sets(ctx.pkg.split).excluded)

    # pass A over every group: R3's joined rows, the per-unit valid rows
    with ThreadPoolExecutor(8) as pool:
        data = dict(zip(groups, pool.map(lambda g: _pass_a(ctx, g, g == groups[0]), groups)))
    counts = {(g, y): n for g in groups for y, n in data[g].joined.items()}
    r3 = _run(real, "R3", D.derive_r03_coverage_end, counts, groups, False)
    gap = ctx.presence_gap()
    if gap:
        real.replaced["presence"] = gap

    # R1 / R2 on every unit of the first group
    first = ctx.by_group[groups[0]]
    names = pq.ParquetFile(first[0][1]).schema_arrow.names
    unit_cols = [ctx.unit_col] if ctx.unit_col in names else ["lat", "lon"]
    tb = pa.concat_tables([read_columns(p, unit_cols + list(ctx.time_facts)) for _, p in first])
    if unit_cols == [ctx.unit_col]:
        units = tb.column(ctx.unit_col).combine_chunks().dictionary_encode().indices.to_numpy()
    else:
        pairs = np.stack([tb.column("lat").to_numpy(), tb.column("lon").to_numpy()], axis=1)
        units = np.unique(pairs, axis=0, return_inverse=True)[1].ravel()
    r1 = _run(real, "R1", D.derive_r01_cadence, units,
              {c: tb.column(c).to_numpy() for c in ctx.time_facts}, ctx.time_facts)
    cadence = r1.value if r1 else _expected_cadence(real)
    if r1 is None:
        real.replaced["cadence"] = "the EXPECTED cadence"
    r2 = _run(real, "R2", D.derive_r02_season_key, cadence, getattr(cadence, "composites_per_year", None))

    # R8 / R4
    first_year = (min(k[1] for k, _ in ctx.listing.files) if ctx.per_year_files else
                  min(read_footer(p).column("year").min for _, p in ctx.listing.files))
    ctx.target_rows = _target_group_years(ctx, data)
    r8 = _run(real, "R8", _r08_as_derive_all, ctx, cadence) if r1 else None
    r4 = _run(real, "R4", _r04_as_derive_all, ctx, r8.value, first_year) if r8 else None
    lag_note = _lag_note(ctx, cadence, first_year) if r1 else ""

    # R5 - R7
    exp_w = real.expected["R3_R7_windows"]
    y0 = r4.value if r4 else exp_w["y0"]
    if r4 is None:
        real.replaced["y0"] = "the EXPECTED y0"
    windows = None
    if r3:
        r5 = _run(real, "R5", D.derive_r05_test_window, y0, r3.value)
        r6 = _run(real, "R6", D.derive_r06_train_end, r5.value.test_years) if r5 else None
        r7 = _run(real, "R7", D.derive_r07_inner_windows, y0, r3.value, r5.value, r6.value) if r6 else None
        windows = r7.value if r7 else None

    # R10 / R11
    r10 = _run(real, "R10", D.derive_r10_leads, r2.value, False) if r2 else None
    r11 = (_run(real, "R11", D.derive_r11_cuts, windows, r10.value, cadence)
           if windows is not None and r10 is not None else None)

    if windows is not None and r11 is not None:
        _loro_rows(real, ctx, data, cadence, windows, r2.value, r10.value, r11.value)
    _run(real, "R28", D.derive_r28_clip_bounds, ctx.legal_range)
    _outcomes(real, lag_note)
    return real


def _loro_rows(real, ctx, data, cadence, windows, season, lead_plan, cuts):
    """R12-R14, R17, R18, R19, R21, R22, R23 on the real data, under leave one region out."""
    groups = ctx.groups
    y0, train_end, inner_end = windows.y0, windows.train_end, windows.inner_fit[1]
    candidates, inner, test_cut = {}, {}, {}
    for g in groups:
        d = data[g]
        cand = _window_sum(d, min(d.years), train_end) > 0
        candidates[g] = tuple(d.units[cand].tolist())
        inner[g] = _window_sum(d, y0, inner_end)[cand]
        test_cut[g] = _window_sum(d, y0, train_end)[cand]
    # split.candidate_units on the first group's (unit, year) rows gives the same candidates
    d0 = data[groups[0]]
    rows = np.repeat(d0.units, len(d0.years))
    years = np.tile(np.array([timing.year_last_step(y, cadence) for y in d0.years]), len(d0.units))
    assert SP.candidate_units(rows, np.full(len(rows), groups[0], dtype=object), years,
                              d0.counts.ravel() > 0, groups[0],
                              timing.year_last_step(train_end, cadence)) == candidates[groups[0]]
    every = np.concatenate([inner[g] for g in groups])
    real.derived["valid_rows"] = {"inner_fit": float(np.median(every)),
                                  "test_cut": float(np.median(np.concatenate([test_cut[g] for g in groups])))}
    per_unit = {u: int(n) for g in groups for u, n in zip(candidates[g], inner[g].tolist())}
    r12 = _run(real, "R12", D.derive_r12_router_kind, per_unit)
    if r12 is None:
        return
    kind = r12.value
    _run(real, "R13", D.derive_r13_surface_loro, kind, groups)
    r14 = _run(real, "R14", D.derive_r14_router_design, kind, ctx.context)
    _run(real, "R17", D.derive_r17_history_spec, season, ctx.target_facts, cadence, kind, False)
    _run(real, "R21", D.derive_r21_smoke_plan_loro, groups)
    if r14 is None:
        return
    non_tree = sum(len(ctx.context) if b == "context" else (0 if b == "trees" else 1)
                   for b in r14.value.columns)
    available = {g: len(candidates[g]) for g in groups}
    pooled = {g: int(inner[g].sum()) for g in groups}
    bank_rule = _run(real, "R18:bank", D.derive_r18_bank_count, kind, season, float(np.median(every)),
                     available, pooled, non_tree)
    if bank_rule is None:
        return
    n, bank = bank_rule.value

    # the streamed event rate and the bank units' donor rows (bank units: the stride pick of R18 (1))
    fit_cut = int(cuts[0].fit_cut)
    last_usable = _last_usable_step(ctx, fit_cut, cadence)
    bank_units = {g: SP.stride_pick(candidates[g], bank[g]) for g in groups}
    with ThreadPoolExecutor(8) as pool:
        c1 = dict(zip(groups, pool.map(lambda g: _pass_c1(ctx, g, cadence, train_end, last_usable,
                                                          bank_units[g]), groups)))
    hist = sum(c1[g][0] for g in groups)
    total = int(hist.sum())

    def values_in_bins(lo, hi):
        with ThreadPoolExecutor(8) as pool:
            parts = [p for part in pool.map(lambda g: _pass_c2(ctx, g, cadence, train_end, last_usable,
                                                               lo, hi), groups) for p in part]
        return _merge_values(parts)

    events, rows, q90 = exact_event_rate(hist, total, values_in_bins)
    rate = D.EventRate(events=events, rows=rows, q90=q90, unit_scope="all_donor_units", cut=fit_cut,
                       cut_kind="fit", lead=0, groups=len(groups),
                       row_key_hash=D.sha256_of_json([D.sha256_of_array(hist), rows]),
                       source="streamed exact order statistics over every group's labels (acceptance test)")
    test_rows = int(season.steps_per_year) * len(windows.test_years)
    scored = _run(real, "R18", D.scored_counts_at_event_rate, kind, n, bank, available,
                  K.K_GROUP_EQUIVALENTS, rate, test_rows)
    if scored is None:
        return
    if rows <= 20_000_000:
        # the approved rule on the full label-only view must give the same counts
        all_rows = []
        for g in groups:
            for _, path in ctx.files_to(g, train_end):
                tb = ctx.read(path, [ctx.target])
                y, steps, ok = _usable_rows(ctx, tb, cadence, last_usable)
                ids, idx = _unit_index(tb, g, ctx.unit_col)
                all_rows.append((ids[idx[ok]], steps[ok], y[ok], g))
        view = _donor_view(all_rows, groups, fit_cut, 0, last_usable, scope="all_donor_units")
        assert D.donor_event_rate(view.y) == (events, rows, q90)
        full = D.derive_r18_scored_count(kind, n, bank, available, K.K_GROUP_EQUIVALENTS, view, test_rows)
        assert full.value == scored.value and full.flags == scored.flags
        real.derived["R18:full_view_checked"] = True
    if kind == D.RouterKind.REGION:
        # the region router's fit budget (R14, L2 rule 2): whole, evenly spaced bank units within it.
        # derive_all counts a router's fit rows with the label-window rule at each cut; the yearly
        # valid-row sums below equal those counts only when the cut step's own label is usable at the
        # cut (then every earlier one is), which is checked, not assumed
        for cut_year in (inner_end, train_end):
            cut_step = int(timing.year_last_step(cut_year, cadence))
            assert _last_usable_step(ctx, cut_step, cadence) == cut_step, (
                "the target's label window reaches past the %d cut: count the region fit rows per step "
                "with the label-window rule" % cut_year)
        fit = {"inner": [], "test": [], "capped": False}
        for g in groups:
            d = data[g]
            rows = dict(zip(d.units.tolist(), _window_sum(d, y0, inner_end).tolist()))
            rows_t = dict(zip(d.units.tolist(), _window_sum(d, y0, train_end).tolist()))
            kept = SP.region_cap_units(bank_units[g], {u: rows[u] for u in bank_units[g]},
                                       K.REGION_ROUTER_ROW_BUDGET)
            kept_t = SP.region_cap_units(bank_units[g], {u: rows_t[u] for u in bank_units[g]},
                                         K.REGION_ROUTER_ROW_BUDGET)
            fit["inner"].append(len(kept))
            fit["test"].append(len(kept_t))
            fit["capped"] = fit["capped"] or len(kept) < len(bank_units[g])
        real.derived["region_fit"] = {"inner_surface_units": int(np.median(fit["inner"])),
                                      "inner_capped": fit["capped"],
                                      "test_pass_units": int(np.median(fit["test"]))}
    lists = SP.pick_unit_lists(groups, candidates, scored.value)
    assert all(lists.bank[g] == bank_units[g] for g in groups if scored.value.bank_by_group[g] == bank[g])
    # the plan's formulas, written here (not split's code): bank = c[::max(1, len(c) // n)][:n] over the
    # sorted candidates (all when len(c) <= n); scored = positions floor(i x (N-1) / (m-1)) of the bank
    for g in groups:
        c, b = candidates[g], scored.value.bank_by_group[g]
        assert lists.bank[g] == (c if len(c) <= b else c[::max(1, len(c) // b)][:b]), g
        big_n, m = len(lists.bank[g]), scored.value.scored_by_group[g]
        want = (tuple(lists.bank[g][(i * (big_n - 1)) // (m - 1)] for i in range(m)) if m > 1
                else lists.bank[g][:1])
        assert lists.scored[g] == want, g
    real.derived["R18:units"] = lists
    real.derived["R18:units_checked"] = "the plan's stride and evenly spaced formulas, per group"

    # R19, R22, R23 on the bank units' rows (bank raised by the floor is re-read: none on these packages)
    assert scored.value.bank_by_group == bank, "the event floor raised a bank count; re-read its rows"
    bank_rows = [(r[0], r[1], r[2], g) for g in groups for r in c1[g][1]]
    donor = _donor_view(bank_rows, groups, fit_cut, 0, last_usable)
    _run(real, "R19", D.derive_r19_bank_plan, donor, False)
    inner_cut = int(cuts[0].guard_cut)                      # the inner-cut bank (L6 b)
    inner_view = _donor_view(bank_rows, groups, inner_cut, 0, _last_usable_step(ctx, inner_cut, cadence),
                             cut_kind="guard")
    _run(real, "R19:inner_cut", D.derive_r19_inner_cut_bank_plan, inner_view, False)
    r22 = _run(real, "R22", D.derive_r22_links, ctx.legal_range, donor)
    if r22 is not None and D.Link.LOG_C in r22.value:
        for lead in sorted(cuts):
            cut = int(cuts[lead].fit_cut)
            view = _donor_view(bank_rows, groups, cut, lead, _last_usable_step(ctx, cut, cadence))
            entry = _run(real, "R23:lead=%d" % lead, D.derive_r23_c_for_cut, view)
            if entry is not None:
                # the run's check against the rows re-selected independently of the view's walk-back
                y_rt, hash_rt = _rebuilt_rows(ctx, bank_rows, cut, cadence)
                D.check_r23_matches_run(entry, lead, cut, D.c_from_donor_y(y_rt)[0], hash_rt)


def _lag_note(ctx, cadence, first_year):
    """What R8 could and could not lag, and the Y0 over the columns it could (report text only)."""
    lags, refused = {}, {}
    for c, col in ctx.candidates.items():
        if getattr(col.cadence, "kind", None) in ("static", "epoch", "irregular"):   # R8 lists these
            continue
        try:
            lags[c] = timing.compute_lag(col, ctx.target_facts, cadence, "nowcast")
        except RefusedError as exc:
            refused.setdefault(exc.rule, []).append(c)
    text = "; R8 refuses %s of %d time-varying candidates (%s)" % (
        sum(len(v) for v in refused.values()), len(lags) + sum(len(v) for v in refused.values()),
        ", ".join("%s: %d, e.g. %s" % (r, len(v), v[:3]) for r, v in sorted(refused.items())))
    if ctx.no_facts:
        text += "; %d catalog columns have no store facts (e.g. %s)" % (len(ctx.no_facts), ctx.no_facts[:3])
    if ctx.script_built:
        text += ("; %d kept engineered columns the feature script builds are not seen here (their facts come from "
                 "the script, e.g. %s)" % (len(ctx.script_built), ctx.script_built[:3]))
    for template, (missing, kept) in sorted(ctx.unbuilt.items()):
        text += ("; driver store %s is not built for %d LORO groups: R4's reader asks no store for its %d kept "
                 "columns" % (template, len(missing), len(kept)))
    if lags:
        try:
            r4 = _r04_as_derive_all(ctx, lags, first_year)
        except RefusedError as exc:
            return text + "; over the %d it can lag, R4 refuses: %s" % (len(lags), exc)
        text += ("; over the %d it can lag, Y0 would be %d (first data year %d, J5: the driver stores', "
                 "target from %d; + %d, set by %s)"
                 % (len(lags), r4.value, r4.inputs["first_data_year"], first_year,
                    r4.inputs["largest_lag_years"], r4.inputs["set_by"][:4]))
    return text


def _target_group_years(ctx, data):
    """The target's (group, year) pairs over EVERY target group (derive_all reads every target row, the
    excluded groups too): pass A's years for the LORO groups; for the others, the year keys of
    per-year files, or each file's footer year range."""
    pairs = set()
    for g, files in ctx.by_group.items():
        if g in data:
            pairs.update((g, int(y)) for y in data[g].years)
        elif ctx.per_year_files:
            pairs.update((g, int(k[1])) for k, _ in files)
        else:
            for _, p in files:
                col = read_footer(p).column("year")
                pairs.update((g, y) for y in range(int(col.min), int(col.max) + 1))
    return sorted(pairs)


class _PresenceReader(object):
    """drivers_present over the stores' (group, year) presence listing (ctx.presence), answered as the
    pipeline's column reader answers it: a row is present when every driver store holding one of the
    asked columns has the group in that year (a store with no time dimension: the group has a file), and
    a group the store declares absent counts as present (F2, F8). A column no store holds asks no store."""

    def __init__(self, ctx):
        self.ctx = ctx

    def drivers_present(self, unit_ids, group_ids, time_columns, columns):
        groups = np.asarray(group_ids, dtype=object)
        years = np.asarray(time_columns["year"], dtype=np.int64)
        out = np.ones(len(groups), dtype=bool)
        wanted = set(columns)
        for _, kept, absent, held, store_groups in self.ctx.presence:
            if not wanted & set(kept):
                continue
            out &= np.array([g in absent or (g in store_groups if held is None else (g, int(y)) in held)
                             for g, y in zip(groups.tolist(), years.tolist())], dtype=bool)
        return out


def _r04_as_derive_all(ctx, lags, target_first_year):
    """R4 as derive_all builds it (orchestrate._r04_entry, owner ruling J5), on one row per target (group,
    year) (ctx.target_rows) with _PresenceReader; the facts are the store catalogs' (operation,
    derived_from, absent groups). Refuses whatever the engine refuses (R4)."""
    rows = ctx.target_rows
    groups = np.array([g for g, _ in rows], dtype=object)
    years = np.array([y for _, y in rows], dtype=np.int64)
    units = np.array(["%s|%d" % (g, y) for g, y in rows], dtype=object)
    facts = SimpleNamespace(store=ctx.store_facts,
                            absent_groups={c: dict(getattr(ctx.store_facts.get(c), "absent_groups", {}) or {})
                                           for c in lags})
    return O._r04_entry(ctx.pkg, facts, lags, _PresenceReader(ctx), units, groups, {"year": years}, years,
                        int(target_first_year))


def _outcomes(real, lag_note):
    upstream = {"R2": "R1", "R4": "R8", "R8": "R1", "R5": "R3", "R6": "R5", "R7": "R6", "R10": "R2",
                "R22": "R12", "R12": "R11", "R11": "R7", "R13": "R12", "R14": "R12", "R17": "R12",
                "R18:bank": "R14", "R18": "R18:bank", "R19": "R18"}

    def put(fieldname, rule, pick, note=""):
        got, chain = real.derived.get(rule), rule
        while got is None and chain in upstream:
            chain = upstream[chain]
            got = real.derived.get(chain)
        replaced = tuple(real.replaced[k] for k in sorted(DEPENDS[fieldname] & set(real.replaced)))
        if isinstance(got, RefusedError):
            where = "" if chain == rule else "%s did not run: " % rule
            real.outcomes[fieldname] = Outcome(refusal=where + str(got), note=note, provisional=replaced)
        elif got is None or chain != rule:
            real.outcomes[fieldname] = Outcome(refusal="%s did not run" % rule, note=note)
        else:
            real.outcomes[fieldname] = Outcome(value=pick(got.value), note=note, provisional=replaced)

    y0_note = " (Y0 %s)" % ("EXPECTED: R4 is refused" if "y0" in real.replaced else "derived")
    put("cadence", "R1", lambda c: {"kind": c.kind.value, "length": c.length,
                                    "unit": c.unit.value if c.unit else None})
    put("season_key", "R2", lambda s: {"kind": s.kind.value, "steps_per_year": s.steps_per_year})
    put("y0", "R4", lambda v: v, lag_note)
    put("y_end", "R3", lambda v: v)
    put("test_years", "R5", lambda p: list(p.test_years), y0_note)
    put("train_end", "R6", lambda v: v, y0_note)
    put("inner_fit", "R7", lambda w: list(w.inner_fit), y0_note)
    put("inner_score", "R7", lambda w: list(w.inner_score), y0_note)
    put("leads", "R10", lambda p: D.jsonable(p))
    put("links", "R22", lambda links: [link.value for link in links])
    real.outcomes["groups"] = Outcome(value={"n_groups": len(real.derived["groups"]),
                                             "excluded": sorted(real.derived["excluded"])})
    put("router_kind", "R12", lambda k: k.value)
    if "valid_rows" in real.derived and "router_kind" in real.outcomes:
        real.outcomes["valid_rows_per_unit"] = Outcome(value=real.derived["valid_rows"],
                                                       provisional=real.outcomes["router_kind"].provisional)
    else:
        put("valid_rows_per_unit", "R12", lambda k: None)
    put("decision_surface", "R13", lambda v: v[0].value)
    put("router_design", "R14", lambda d: {
        "kind": d.kind.value, "columns": list(d.columns), "unpenalised": list(d.unpenalised),
        "centre": list(d.centre), "grid_points": len(d.grid),
        "levels": len({p.level for p in d.grid}),
        "ratios": (len({p.ratio for p in d.grid}) if d.grid[0].ratio is not None else None),
        "fit_row_cap": d.fit_row_cap})
    put("history", "R17", lambda s: {"n_columns": len(s.columns), "last_values": s.last_values,
                                     "trailing_steps": list(s.trailing_steps),
                                     "all_history_mean": s.all_history_mean,
                                     "start_offset_steps": s.start_offset_steps})
    put("bank_units", "R18:bank", lambda v: {"bank": v[0], "capped": {g: b for g, b in v[1].items()
                                                                        if b < v[0]}})
    put("scored_units", "R18", lambda c: {
        "scored": int(pd.Series(list(c.scored_by_group.values())).mode().min()),
        "scored_total": sum(c.scored_by_group.values()), "n_groups": c.n_groups,
        "k_group_equivalents": c.k_group_equivalents})
    put("bank_trees", "R19", lambda v: v["bank_trees"])
    # the router drops its own block's trees: a one-group block loses its group's trees, a two-group
    # block both groups' (R14, L2 rule 4)
    put("tree_columns", "R19", lambda v: {"bank_trees": v["bank_trees"],
                                          "one_group_block": v["bank_trees"] - v["trees_per_group"],
                                          "two_group_block": v["bank_trees"] - 2 * v["trees_per_group"]})
    real.outcomes["overlap_blocks"] = Outcome(refusal=_BLOCKS_NOT_CHECKED)
    if "router_kind" in real.outcomes and real.outcomes["router_kind"].refusal is None:
        real.outcomes["region_fit"] = Outcome(value=real.derived.get("region_fit"),
                                              provisional=real.outcomes["router_kind"].provisional)
    else:
        put("region_fit", "R12", lambda k: None)
    real.outcomes["missing_flags"] = Outcome(refusal=_R30_NOT_RUN)


_CACHE: Dict[str, Real] = {}


def real_package(name: str) -> Real:
    if name not in _CACHE:
        _CACHE[name] = _build(name)
    return _CACHE[name]


def _expected(real: Real, fieldname: str):
    e = real.expected
    w = e["R3_R7_windows"]
    design = e["R14_router_design"]
    r18 = e["R18_units_per_group"]
    return {"cadence": {k: e["R1_cadence"][k] for k in ("kind", "length", "unit")},
            "season_key": e["R2_season_key"],
            "y0": w["y0"], "y_end": w["y_end"], "test_years": w["test_years"],
            "train_end": w["train_end"], "inner_fit": w["inner_fit"], "inner_score": w["inner_score"],
            "leads": {k: e["R10_leads"][k] for k in ("requested_months", "leads", "lead_unit", "merged",
                                                     "not_supplied", "contract_lead_zero")},
            "links": e["R22_links"]["value"],
            "groups": {"n_groups": e["LORO_groups"]["n_groups"], "excluded": e["LORO_groups"]["excluded"]},
            "valid_rows_per_unit": {k: float(e["R12_valid_rows_per_unit"][k]) for k in ("inner_fit",
                                                                                       "test_cut")},
            "router_kind": e["R12_router_kind"]["value"],
            "decision_surface": e["R13_decision_surface"]["value"],
            "router_design": {k: design[k] for k in ("kind", "columns", "unpenalised", "centre",
                                                     "grid_points", "levels", "ratios", "fit_row_cap")},
            "history": {k: e["R17_history"][k] for k in ("n_columns", "last_values", "trailing_steps",
                                                          "all_history_mean", "start_offset_steps")},
            "bank_units": {"bank": r18["bank"], "capped": r18.get("bank_small_groups", {})},
            "scored_units": {"scored": r18["scored"], "scored_total": r18["scored_total"],
                             "n_groups": r18["n_groups"], "k_group_equivalents": r18["k_group_equivalents"]},
            "bank_trees": e["R14_tree_columns"]["bank_trees"],
            "tree_columns": {k: e["R14_tree_columns"][k] for k in ("bank_trees", "one_group_block",
                                                                   "two_group_block")},
            "overlap_blocks": {"n_blocks": e["R14_overlap_blocks"]["n_blocks"],
                               "linked_pairs": e["R14_overlap_blocks"]["linked_pairs"],
                               "groups_in_two_group_blocks":
                                   e["R14_tree_columns"]["groups_in_two_group_blocks"]},
            "region_fit": ({"inner_surface_units": design["inner_surface_rows"]["units"],
                            "inner_capped": design["inner_surface_rows"]["capped"],
                            "test_pass_units": design["test_pass_rows"]["units_approx"]}
                           if "inner_surface_rows" in design else None),
            "missing_flags": e["R30_missing_flags"]["plan_3_2"]}[fieldname]


# ---------------------------------------------------------------------------------------------------
def test_the_streamed_event_rate_is_donor_event_rate():
    arrays = [np.arange(1000.0), np.r_[np.zeros(990), np.arange(1.0, 11.0)], np.r_[np.zeros(85), np.ones(15)],
              np.sin(np.arange(12345.0)) * 50, np.round(np.cos(np.arange(5000.0)) * 3, 1),
              np.r_[-np.arange(40.0), np.full(3, 7.25)], np.array([2.5]), np.linspace(0.0, 1.0, 7)]
    for y in arrays:
        hist = np.bincount(_bins(y), minlength=N_BINS)

        def values_in_bins(lo, hi, y=y):
            b = _bins(y)
            return np.unique(y[(b >= lo) & (b <= hi)], return_counts=True)

        assert exact_event_rate(hist, len(y), values_in_bins) == D.donor_event_rate(y)


@pytest.mark.parametrize("fieldname", FIELDS)
@pytest.mark.parametrize("name", PACKAGES)
def test_derived_field_matches_expected(name, fieldname):
    real = real_package(name)
    outcome = real.outcomes[fieldname]
    expected = _expected(real, fieldname)
    if outcome.refusal is None and outcome.value == expected:
        assert (name, fieldname) not in KNOWN_DIFFERENCES, (
            "%s %s now matches the expected value %r: remove it from KNOWN_DIFFERENCES"
            % (name, fieldname, expected))
        if outcome.provisional:
            pytest.xfail("PROVISIONAL, not M1 evidence -- %s %s matches %r only with %s%s"
                         % (name, fieldname, expected, " and ".join(outcome.provisional), outcome.note))
        return
    got = ("REFUSED: %s" % outcome.refusal) if outcome.refusal else ("derived %r" % (outcome.value,))
    marks = (" [computed with %s]" % " and ".join(outcome.provisional)
             if outcome.provisional else "")
    report = "%s %s: %s; expected %r%s%s" % (name, fieldname, got, expected, marks, outcome.note)
    if (name, fieldname) in KNOWN_DIFFERENCES:
        if (name, fieldname) in PENDING_OWNER_DERIVED:
            pinned = PENDING_OWNER_DERIVED[(name, fieldname)]
            assert outcome.refusal is None and outcome.value == pinned, (
                "%s %s waits for an owner choice with the derived value pinned at %r, but: %s"
                % (name, fieldname, pinned, report))
        pytest.xfail("KNOWN (%s) -- %s" % (KNOWN_DIFFERENCES[(name, fieldname)], report))
    pytest.fail("MISMATCH (report it; never patch engine code): " + report)


class _NotRead(object):
    """A target table and column reader derive_all must not reach: any attribute read fails."""

    def __getattr__(self, name):
        raise AssertionError("derive_all got past the closed world and read %r: feed it the real target "
                             "(a streaming vault view) and update this test" % name)


@pytest.mark.parametrize("name", PACKAGES)
def test_derive_all_passes_the_closed_world_and_needs_only_the_feature_script_facts(name):
    """derive_all itself on the real package, before it reads any target row.

    UPDATED 2026-10-06 (agent C1; was test_derive_all_stops_at_the_closed_world, which expected G-CLOSED): since owner
    ruling J installed the four ban lists (OWNER_RULINGS_2026-10-05.md section J, 2026-10-05), every non-key catalog
    column has a verdict, so the closed world passes. The kept columns the package's FEATURE SCRIPT builds (J2 a lag
    columns, L3 hold columns, PM2.5's burn_lag1, NDVI's driver lags, the router context it writes) have no store
    catalog: their facts come from the script itself (plan 1.5), which the pipeline adds with
    pipeline.data.augment_package before it calls derive (Pipeline._load). So:
      - on the bare package derive_all refuses at R8 ('kept columns have no store facts'), and the columns without
        facts are exactly kept feature-script outputs (no other kept column lacks store facts);
      - with the script's output facts added, as the pipeline does, it passes the closed world and every facts check
        and stops only where it reads the target (this test hands it none)."""
    from treeroute.pipeline import data as PD

    pkg = load_package(ENGINE_DIR / "datasets" / name)
    no_verdict = [c for c, f in pkg.catalog.columns.items()
                  if f.role not in ("key_unit", "key_group", "key_time") and c not in pkg.ban.verdicts]
    assert no_verdict == [], "closed world: %d columns of %s have no verdict" % (len(no_verdict), name)
    hook = PD.load_hook(pkg.root, PD.FEATURE_SCRIPT)
    outputs = PD.feature_outputs(hook) if hook is not None else {}
    non_key = tuple(c for c, f in pkg.catalog.columns.items() if f.role not in ("key_unit", "key_group", "key_time"))
    kept_sets = apply_verdicts(non_key, dict(pkg.ban.verdicts), {c: pkg.catalog.columns[c].role for c in non_key})
    kept = tuple(kept_sets.tree_features) + tuple(kept_sets.router_context)
    no_facts = {c for c in kept if c not in O._store_facts(pkg)}      # the kept columns without store facts
    assert no_facts <= set(outputs), sorted(no_facts - set(outputs))[:10]
    if no_facts:
        with pytest.raises(RefusedError) as info:
            D.derive_all(pkg, _NotRead(), _NotRead())
        assert info.value.rule == "R8" and "have no store facts" in str(info.value), info.value
    with pytest.raises(AssertionError, match="got past the closed world"):
        D.derive_all(PD.augment_package(pkg, outputs), _NotRead(), _NotRead())


@pytest.mark.parametrize("name", PACKAGES)
def test_cuts_c_unit_lists_and_clip_bounds_run_on_the_real_windows(name):
    real = real_package(name)
    r11 = real.derived.get("R11")
    assert r11 is not None and not isinstance(r11, RefusedError), r11
    assert sorted(r11.value) == [0] + list(real.derived["R10"].value.leads)
    r28 = real.derived["R28"]
    assert not isinstance(r28, RefusedError) and r28.value[0] < r28.value[1]
    r22 = real.derived["R22"]
    assert not isinstance(r22, RefusedError), r22
    if D.Link.LOG_C in r22.value:
        assert all(real.derived["R23:lead=%d" % lead].value > 0 for lead in r11.value)
    assert real.derived["R18:units_checked"]                        # checked in _loro_rows
    inner = real.derived["R19:inner_cut"]
    assert not isinstance(inner, RefusedError), inner
    assert inner.inputs["donor"]["cut"] == r11.value[0].guard_cut
    assert inner.value["bank_trees"] == real.derived["R19"].value["bank_trees"]
    r21 = real.derived["R21"]
    assert r21.value["groups"] == sorted(real.derived["groups"])[:4]
    doc = D.derived_document({rule: d for rule, d in real.derived.items()
                              if isinstance(d, D.Derived)})
    assert json.loads(json.dumps(doc)) == doc                        # every entry is strict JSON
