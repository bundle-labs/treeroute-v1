"""The one pipeline of plan 4.1: the NOWCAST (lead 0) and the forecast ladder (step 11).

    1  load and fingerprint the package; the DRAFT stamp; the package's code hooks; the feature
       script's lineage (a stand-in for G-LINEAGE: the quick checks themselves are not built)
    2  derive_all -> derived.json (plus the overlap blocks from the static table, R14); a headline run
       refuses when derived.json differs from the one the package's latest plan showed
    3  the dense grid and the label vault; the feature pool (sentinels masked, 1:1 joins, computed lags
       and verdicts applied, the feature script's outputs attached)
    4  the own-history block (R17), written into the pool; a second block at the INNER cut for the
       inner decision (its fallbacks read labels within the guard cut only)
    5  the unit lists (R18: bank units and the scored subset, from derived.json)
    6  FitContext fits: the bank at the fit cut and the bank refit at the inner cut (L6 b), their
       correctors and placebo correctors (R19), the GLS weight model (R25)
    7  tree-answer tables per group, built once per row, own-group trees never computed, own-block
       columns dropped by the router's mask (R14, R20)
    8  the decision surface: every link x arm (unweighted and, for the per-unit kind, GLS-weighted) x grid
       point + trees-off, routed by the run's router kind (pipeline/router.py: per-unit with the region
       fallback for short-history units, or region), the N2 guard, MAE adoption (decide), adoption.json
       locked and its hash put in a write-once manifest addendum before any test label opens (G-LOCK)
    9  the test pass: every arm saved (placebo table built once, after the lock), the legal clip, the
       baselines
   12  metrics: score tables by group / year / stratum / pooled, the single verdict with its band (D74,
       D75), the blocked jackknife beside, the pre-clip table, the guard report
   11  the forecast ladder (pipeline/ladder.py), after the nowcast's report: the lead-0 contract, then per
       derived lead (6 and 12 months, owner ruling I1) the lead's cuts, the features moved to the issue step
       (H3), lagtrain pinned to the nowcast adoption, a second bank refit at the lead's guard cut for its
       N2 guard (H2: L6 b at every lead; decline per D86) with the lead's own R12 fallback level (H5),
       persistence and damped persistence, the pinned placebo at the longest lead, every scored row saved
       and the test rows whose issue row is absent left out of scoring, saved flagged and counted (H4); then
       the ladder table on the common rows under the nowcast band
Step 10 (Type 3) is not built.

Run folder: <run root>/<package>/<headline or smoke>/<yyyymmdd>_<fp8>/ (runs.resume.open_run), with
run.json, run_record.json (DRAFT stamp, headline eligibility, departures, limits), manifest.json,
manifest_adoption.json (the adoption hash, written once before the test labels open), derived.json,
plan.json, plan_check.json (a headline run: the plan folder its derived.json was checked against, or
that no plan preceded it), status.json (heartbeat), run.log, phases/<name>/DONE and
phases/<name>/fitctx_log.parquet, inner_candidates.csv, inner_preds.parquet, adoption.json (+ lock),
test_preds.parquet (every row, every arm), fitctx_log.parquet, score_by_group.csv, per_year.csv,
per_stratum.csv (declared strata only), score_pooled.csv, per_group.csv, jackknife.csv, preclip.csv,
guard_report.json, verdict.json and DONE.json. The fingerprint covers the package, derived.json, the
data read (target, static and driver files by size and time), the engine code and the library versions;
the same fingerprint resumes (phases already DONE are not redone: derived.json is re-derived and must be
identical; a locked adoption is read back, never re-decided), a finished one is refused.

Headline eligibility: a run is headline-eligible only with no not-headline reason. Besides the DRAFT
stamp, the smoke kind and the R36 stand-in, every departure of this build from the approved design is a
reason until it is built or the owner rules it acceptable (DEPARTURES, build_departures). Owner ruling S21
accept (the owner rulings file, section N) ruled the build's departures acceptable (ACCEPTED_DEPARTURES);
only split_view (a probe's excluded groups) is still a reason.

Streaming (owner item, G-DISK): the target is never held whole. Step 1 reads it file by file into a
census (derive/census.py: validity bits, presence counts, label histograms, R1's hashes); derive_all runs over
the census (derive_all_streamed: the same rules, the same bytes); the full label rows of the PICKED units (the
bank units, which hold every scored unit) are read again after the picks, and only they reach the plan-time
label reader, the column reader (pool, ladder) and the vault. A smoke's pick (R21) gathers each group's units
with a valid label file by file too. R30's per-test-year missing share (over every target row of a test year)
is counted once for both derive passes, in unit blocks that read only the rows from the test years' window
on (pipeline/stream.py: the files that end before it are skipped, every label is dropped as it is read, and
each block's picked units are checked against the picked reader's whole histories). The RAM go/refuse checks
the census pass before the first file and the picked units' working set before ANY of their rows are read
(census.row_guard). The data manifest the fingerprint hashes reports every target row read
(stream.census_data_manifest), as the whole-table reader reports it. Pipeline(streamed=False) keeps the
in-memory path (the whole table, derive_all) for the byte-identity gates only.

Per-group batching (plan R20, made real): every command processes ONE GROUP AT A
TIME wherever the math is per group or per unit, so a full-size run fits the machine. The picked units'
column reader is built per group (pipeline/stream.py GroupReaders: that group's picked rows, joined, lagged,
last-value filled, used and freed before the next group) for R30's shares (integer counts summed over the
groups and divided once), the last-value record (counts summed), the static strata and the pools (filled
group by group, the forecast ladder's lead pools too); the feature script must be group-separable, which
check_group_separable checks in every run on the smoke-shaped sample (refused otherwise). Every router pass
walks the groups with one group's tree-answer tables on disk at a time (pipeline/router.py GroupTables); the
GLS weight model drops each group's donor-row table once read. The RAM pre-flight counts the largest group's
reader (and the picked label rows), the disk pre-flight the pools plus the largest group's tables of any
pass (_preflight_disk); the GLS weight model (a fit over every group's donor rows, R25) refuses before its
donor matrix is built when its peak does not fit (fit.weights.gls_ram_bytes, at the nowcast fit and at each
weighted lead). Pipeline(per_group=False) keeps the whole-frame path (one reader of every picked
unit, every group's tables kept) for the byte-identity gates only; the in-memory path is whole-frame.
per_group_schedule.json records the separability check, the reader builds and each pass's table peak.

Last value (owner ruling J2 d): the column reader's lagged frame fills each kept tree feature's short inner
gaps (io.lastvalue.fill_last_value) before R30 and the pool read it; the counts per column go into
run_record.json ('last_value', over the column reader's rows, beside the run's target rows: streamed at full
size those are the picked units' rows, fewer than every target row) and run.log.

Smoke (R21): the first C13.smoke_groups groups in sorted order, C13.smoke_units_per_group units per
group (a stride over each group's sorted unit ids with at least one valid label: validity only, never a
value), C13.smoke_trees_per_group trees per group. derive_all runs on the smoke's own target rows, so
every group is trained and tested and every unit is a bank and a scored unit; the R21 plan over the
package's full group list is recorded beside ('R21:smoke_selection'), and R19 is re-derived with the
smoke tree count ('R19:smoke', 'R19:inner_cut_smoke'). Plumbing only: smoke deltas carry no sign
information.
"""

import gc
import hashlib
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from treeroute import engine_constants as _K
from treeroute.errors import PreflightRefusal, RefusedError

PHASE_PLAN = "plan"
PHASE_DECISION = "decision"
PHASE_TEST = "test_pass"
PHASE_REPORT = "report"
PLAN_CHECK_FILE = "plan_check.json"
PER_GROUP_PLAN_FILE = "per_group_plan.json"            # plan R20's per-group schedule (per-group path only)
PER_GROUP_SCHEDULE_FILE = "per_group_schedule.json"
TEMP_PREFIX = "treeroute_run_"
GIB = float(1 << 30)
# Go/refuse estimates only (G-DISK): they never set a number. A target row held by pandas (unit and group
# object pointers, time parts, y, index) and one float64 feature value per row and column; each scored row
# goes into up to five tables (inner-cut plain and corrector, fit-cut plain, corrector and placebo).
TARGET_ROW_BYTES = 120
FRAME_VALUE_BYTES = 16
TABLES_PER_ROW = 5
TABLES_PER_LEAD = 2          # the lead's fit-cut store: the pinned tool, and the placebo at the longest lead
GUARD_TABLES_PER_LEAD = 1    # the lead's guard-cut store (owner ruling H2): the pinned tool
# plan R20's per-group schedule (disk_plan): the table kinds of one group that coexist in a pass (counts of the
# tools a pass reads, not numbers that set anything): engine constants P3.nowcast_table_kinds (plain, corrector and
# placebo in the nowcast's test pass) and P3.lead_table_kinds (a lead's guard: the pinned kind and the corrector's
# fallback level; its test pass: the pinned kind and the placebo)
NOWCAST_TABLE_KINDS = _K.NOWCAST_TABLE_KINDS
LEAD_TABLE_KINDS = _K.LEAD_TABLE_KINDS
LIMITS = (
    "Type 3 (plan 4.1 step 10) is not built",
    "the quick and deep checks (plan 4.1 step 1, treeroute/check) are not built and not run; the feature "
    "script's lineage is checked against the verdicts only",
    "the GLS-weighted per-unit solve is a new formula awaiting the owner's review; a region package routes no "
    "GLS arm (route/region.py has no weighted solve) and fits no weight model",
    "the per-unit and region routers are called through route.kinds' and route.region's private kernels "
    "(route_per_unit_loro and route_region_loro are not built)",
    "the neighbour router kind (R12) is refused (milestone M8)",
    "the forecast ladder runs grid leads in steps only; leads in days (events) are refused (milestone M8)",
    "the continuity row (continuity.csv), nearest-donor distances and distance bands, report.html and "
    "part_draft.md are not built (treeroute_report)",
    "the band is derived from this run's own contrasts; registry/bands.csv and registry/index.csv are not "
    "written",
    "'freeze' verdicts are refused: per-cut frozen pools are not built",
    "per_stratum.csv covers static report strata only; a time-varying stratum is refused",
    "the target is read as a streaming census (derive/census.py; full rows only for the picked units): a "
    "date or day_of_year calendar (a day time line) is refused by it, and so is a driver store whose template "
    "has no {group} placeholder; R30's per-test-year missing share is counted once over every census row of "
    "the test years, in unit blocks that read the target and driver files from the test years' window on (the "
    "window rests on the feature script's declared backward windows, checked against the picked units' whole "
    "histories)",
    "the picked units' column reader is built one group at a time (plan R20) and rebuilt by every stage that "
    "reads it (each derive pass's R30, the nowcast pool, the lead-0 contract's and each lead's pool): driver "
    "files are read once per build; the per-group path rests on the feature script's group-separability, "
    "checked on the smoke-shaped sample only",
    "the per-group table schedule drops every table once its group is routed: the test pass recomputes the "
    "scored units' rows the GLS weight model built, and the lead-0 contract recomputes its pinned table and, "
    "for a weighted pin, the lead-0 weight model's donor rows (the same bytes, more tree predictions)",
)
# Departures of this build from the approved design. Each one is a not-headline reason until it is built
# or the owner rules it acceptable in the rulings file (then it leaves this list).
# Owner ruling S21 accept (OWNER_RULINGS_2026-10-06.md section N; FREEZE_SIGNOFF_SHEET.md S21, follow-up corrected
# per SIGNOFF_REVIEW.md S21): the freeze runs the checks and locks the hashes, the band is the first headline's own,
# report rows come from saved predictions, the weighted GLS solve is brute-force tested
# (tests/test_route_weighted.py), and the pre-Y0 label reading is accepted. Every build departure moved to
# ACCEPTED_DEPARTURES (kept as the record the paper discloses); none is a not-headline reason any more.
DEPARTURES = ()
ACCEPTED_DEPARTURES = (
    ("quick_checks", "the quick and deep checks are not run (treeroute/check is not built: G-LINEAGE, "
                     "G-DERIVED, G-KEYS, G-HIST scan, G-NODRAW, G-CADENCE, G-FACTS ...; plan 4.1 step 1)"),
    ("gls_kernel", "R24's GLS-weighted per-unit arms are routed by a NEW weighted solve (route.solve "
                   "solve_grid_weighted / solve_point_weighted: the weighted primal is solve_local with the weights, "
                   "the weighted shared-Gram solve is grid_dual on rows scaled by sqrt(w)) awaiting the owner's "
                   "review; a region package's GLS arms are absent under a declared reason; a GLS arm's "
                   "short-history rows take the unweighted fallback region router"),
    ("private_router", "the per-unit and region routers run through route.kinds' and route.region's private "
                       "kernels (pipeline/router.py), not the approved route_per_unit_loro / route_region_loro"),
    ("band_source", "the R35 band is this run's own, not the package's first-headline band from "
                    "registry/bands.csv"),
    ("report_rows", "R34's continuity row, nearest-donor distances and distance bands are not built"),
    # owner rulings H2-H5 (2026-10-05) replaced the departures ladder_guard_bank and ladder_readings; the readings
    # this build made of them await the owner (ladder.json readings). The guard's fit-cut c is not a reading:
    # ruling D63 a puts it there (ladder.GUARD_FIT_CUT_RULE)
    ("ladder_h_readings", "the forecast ladder's readings of owner rulings H2 and H4 await the owner (ladder.json "
                          "readings): a weighted pin's guard GLS weight model reads its tree answers from the lead's "
                          "fit-cut bank, as the nowcast's does (L6_ANSWERS_DISCLOSURE); H4 is read as a test row "
                          "whose issue row is absent (test rows whose issue row exists but holds a non-finite "
                          "feature are counted per lead, not left out); a guard-surface row whose issue row is "
                          "absent refuses"),
)
SPLIT_VIEW_DEPARTURE = ("split_view", "the excluded groups' target rows are not read, so derive_all's R1, R2 and "
                                      "R4 (the cadence and the first data year) count the run's groups only; the "
                                      "approved derive_all takes the whole target table (the owner has not ruled "
                                      "this reading)")
# S21 accept (ruling N): the pre-Y0 label reading is ruled acceptable, so a run that withholds labels no longer
# carries it as a not-headline reason (the paper discloses ACCEPTED_DEPARTURES).
MODEL_LABELS_DEPARTURE = ("model_labels", "labels before Y0 are withheld from derive_all's label views by a "
                                          "second derive_all pass, and the pre-Y0 year is not on the grid "
                                          "for R17 (ruled acceptable: S21 accept, owner rulings section N)")
ACCEPTED_DEPARTURES = ACCEPTED_DEPARTURES + (MODEL_LABELS_DEPARTURE,)


class PipelineRefusal(RefusedError):
    """The pipeline refused (fail loudly)."""


def _sha_json(obj: Any) -> str:
    from treeroute.runs.atomic import dumps_canonical

    return hashlib.sha256(dumps_canonical(obj).encode("ascii")).hexdigest()


def _file_list_sha(paths: Sequence[str]) -> str:
    items = []
    for p in sorted(set(str(x) for x in paths)):
        st = os.stat(p)
        items.append([p.replace("\\", "/"), int(st.st_size), int(st.st_mtime_ns)])
    return _sha_json(items)


def build_departures(pipe: Any) -> List[str]:
    """The not-headline reasons of this build's departures (DEPARTURES, plus the split view when excluded
    groups were left unread). The pre-Y0 label reading is ruled acceptable (S21 accept, ruling N): it is in
    ACCEPTED_DEPARTURES and is no reason."""
    items = list(DEPARTURES)
    if getattr(pipe, "split_view_dropped", None):
        items.append(SPLIT_VIEW_DEPARTURE)
    return ["departure %s: %s" % (key, text) for key, text in items]


# ---------------------------------------------------------------------------------------------------
class Pipeline(object):
    """One run of the pipeline. run() does everything; plan() stops after derived.json and plan.json."""

    def __init__(self, package_path: Any, run_root: Any, kind: str, machine: Any = None,
                 echo: Callable[[str], None] = print, launch_record: Optional[Mapping[str, Any]] = None,
                 streamed: bool = True, per_group: bool = True) -> None:
        from treeroute.pipeline.record import KIND_HEADLINE, KIND_SMOKE, RunLog
        from treeroute.runs.machine import load_machine
        from treeroute.runs.registry import Registry

        if kind not in (KIND_HEADLINE, KIND_SMOKE):
            raise PipelineRefusal("plan 7.1", "run kind %r is neither headline nor smoke" % kind)
        self.kind = kind
        self.smoke = kind == KIND_SMOKE
        self.machine = machine if machine is not None else load_machine()
        self.registry = Registry(self.machine.registry_dir)
        self.run_root = self.registry.assert_writable(Path(run_root))
        self.package_path = Path(package_path)
        # TEST ONLY: a process started by pytest cannot pass through the launcher (numpy is loaded first),
        # so the tests hand the manifest a launch record; the CLI never does (None = the launcher's).
        self.launch_record = launch_record
        self.log = RunLog(echo)
        self.temp_dir: Optional[Path] = None
        self._planning = False
        self._cleanup: List[Callable[[], None]] = []
        self.model_labels_withheld = False
        self.split_view_dropped: List[str] = []
        self.plan_check: Dict[str, Any] = {}
        # GATE ONLY: streamed=False reads the whole target table and runs derive_all (the byte-identity gates
        # compare the two paths); every command runs the streamed census
        self.streamed = bool(streamed)
        # GATE ONLY: per_group=False keeps the whole-frame path (one column reader of every picked unit, every
        # group's tables kept on disk); every command runs per group (plan R20). The in-memory path is whole.
        self.per_group = bool(per_group) and self.streamed
        self.separability: Optional[Dict[str, Any]] = None
        self.census = None

    # ------------------------------------------------------------------ the heavy-job lock (first)
    def _lock(self) -> None:
        """One heavy job per machine (G-DISK), taken before anything is read: the machine temp root
        (created here if absent, and removed again when this run leaves it empty), orphan files refused,
        the lock acquired."""
        from treeroute.runs import preflight

        root = self.registry.assert_writable(Path(self.machine.temp_dir))
        created = []
        probe = root
        while not probe.exists():
            created.append(probe)
            probe = probe.parent
        root.mkdir(parents=True, exist_ok=True)
        self.temp_root = root

        def remove_created():
            for d in created:                          # leaf first; only folders this run made, only empty
                if d.is_dir() and not any(d.iterdir()):
                    d.rmdir()
        if created:
            self._cleanup.append(remove_created)
        preflight.refuse_orphans(root)
        for sub in root.iterdir():
            if sub.is_dir() and sub.name.startswith(TEMP_PREFIX):
                preflight.refuse_orphans(sub)
        self.lock = preflight.HeavyJobLock(root)
        self.lock.acquire()
        self._cleanup.append(self.lock.release)

    def _release(self) -> None:
        errors = []
        for fn in reversed(self._cleanup):
            try:
                fn()
            except Exception as exc:          # every cleanup runs; the first failure is re-raised
                errors.append(exc)
        self._cleanup = []
        if errors:
            raise errors[0]

    # ------------------------------------------------------------------ step 1-2: load and derive
    def _load(self) -> None:
        from treeroute.package.load import load_package
        from treeroute.pipeline import data as D
        from treeroute.pipeline.draft import draft_status

        self.package = load_package(self.package_path)
        self.draft = draft_status(self.package)
        self.target_hook = D.load_hook(self.package.root, D.TARGET_READER)
        self.feature_hook = D.load_hook(self.package.root, D.FEATURE_SCRIPT)
        outputs = D.feature_outputs(self.feature_hook) if self.feature_hook is not None else {}
        self.pkg = D.augment_package(self.package, outputs)
        self.spec = D.package_spec(self.pkg)
        self.feature_lineage = D.check_feature_lineage(outputs, self.pkg)
        self.log("package %s version %s, fingerprint %s%s" % (
            self.package.dataset.name, self.package.dataset.version, self.package.fingerprint[:16],
            (" | DRAFT: %s" % self.draft.stamp) if self.draft.is_draft else ""))
        for column, notes in sorted(self.feature_lineage.items()):
            self.log("feature lineage: %s is derived from %s" % (column, "; ".join(notes)))
        if self.spec.listed_in_reports:
            self.log("listed in every report (keep_unreviewed / watch): %s" % ", ".join(self.spec.listed_in_reports))
        if self.spec.frozen:
            raise PipelineRefusal("R9", "columns %s have a 'freeze' verdict; the pipeline's per-cut frozen "
                                  "pools are not built" % list(self.spec.frozen)[:5],
                                  fix="owner item: build per-cut pools, or rule the columns")
        self.not_headline = []
        if self.draft.is_draft:
            self.not_headline.append("DRAFT package: %s" % self.draft.stamp)
        if self.smoke:
            self.not_headline.append("smoke run: plumbing only (R21), smoke deltas carry no sign information")
        from treeroute import engine_constants as K
        if K.GUARD_TOLERANCE_K is K.UNSET:
            if self.smoke:
                self.not_headline.append("R36 stand-in tolerance (C9.guard_tolerance_k unset)")
            elif self._planning:
                # plan computes no tolerance; the headline run that resumes this folder refuses until k is set
                self.not_headline.append("C9.guard_tolerance_k unset: the headline run refuses until the owner "
                                         "sets k")
            else:
                K.get("C9.guard_tolerance_k")      # a headline run refuses until the owner sets k (C9)

    def _groups(self) -> None:
        from treeroute import engine_constants as K
        from treeroute import split as SP
        from treeroute.derive.unit_rules import derive_r21_smoke_plan_loro
        from treeroute.pipeline import data as D

        self.listing = D.list_target(self.pkg)
        self.split_sets = SP.loro_split_sets(self.pkg.split)
        data_groups = D.listed_groups(self.listing)
        if data_groups is None:
            raise PipelineRefusal("R18", "the target store template has no {group} placeholder, so the groups "
                                  "cannot be listed before the target is read",
                                  fix="use a {group} placeholder in dataset.yaml stores.target")
        diff = SP.loro_split_differences(self.split_sets, data_groups)
        if diff.listed_not_in_data or diff.reported_and_excluded or diff.duplicates:
            raise PipelineRefusal("G-SPLIT", "split.yaml differs from the data: %s" % (diff,))
        self.all_groups = SP.groups_under_loro(self.split_sets, data_groups)
        self.smoke_plan = None
        if self.smoke:
            self.smoke_plan = derive_r21_smoke_plan_loro(self.all_groups)
            self.run_groups = tuple(self.smoke_plan.value["groups"])
            self.trees_per_group = int(self.smoke_plan.value["trees_per_group"])
        else:
            self.run_groups = tuple(self.all_groups)
            self.trees_per_group = int(K.TREES_PER_GROUP)
        self.log("groups: %d in the data, %d after exclusions; this run: %d (%s)"
                 % (len(data_groups), len(self.all_groups), len(self.run_groups), self.kind))

    def _preflight_target(self) -> None:
        """RAM go/refuse before the target is read (G-DISK: it never shrinks a run). Streamed (every
        command): the census pass (one file, the bit matrices and counters of the units, estimated from the
        biggest file of each group), and for a smoke the pick before it (the biggest group's rows, read
        whole as read_target reads them). In-memory (gates only): every file of the run, or the biggest
        group's files for a smoke."""
        if self.streamed:
            return self._preflight_census()
        import pyarrow.parquet as pq

        from treeroute.pipeline import data as D
        from treeroute.runs import preflight

        files = D._files_of(self.listing, self.run_groups)
        per_file = {p: pq.ParquetFile(p).metadata.num_rows for _, p in files}
        rows = sum(per_file.values())
        held = rows
        if self.smoke:
            i = self.listing.key_names.index(D.GROUP_PLACEHOLDER)
            held = max(sum(per_file[p] for k, p in files if k[i] == g) for g in self.run_groups)
        need = held * TARGET_ROW_BYTES
        self.data_files = [p for _, p in files]
        try:
            preflight.check_resources(self.machine.temp_dir, 0, int(need))
        except PreflightRefusal as exc:
            raise PipelineRefusal("G-DISK", "the in-memory path (gates only) holds the target census of this run "
                                  "(%d rows in %d files, %d held at once) whole: about %.2f GiB of RAM before any "
                                  "compute (%s)" % (rows, len(files), held, need / GIB, exc),
                                  fix="run the streamed census (Pipeline(streamed=True), every command's path); "
                                      "nothing is computed and no run folder is opened") from exc
        self.log("preflight: %d target rows in %d files, %d held at once; RAM estimate %.2f GiB: go"
                 % (rows, len(files), held, need / GIB))

    def _preflight_census(self) -> None:
        import numpy as np
        import pyarrow.parquet as pq

        from treeroute.derive.census import census_ram_bytes
        from treeroute.pipeline import data as D
        from treeroute.pipeline import stream as STR

        files = D._files_of(self.listing, self.run_groups)
        per_file = {p: pq.ParquetFile(p).metadata.num_rows for _, p in files}
        rows = sum(per_file.values())
        self.data_files = [p for _, p in files]
        biggest = max(per_file.values()) if per_file else 0
        self._biggest_file_rows = int(biggest)
        # a smoke's pick reads one file at a time too (its units with a valid label, gathered file by file)
        self.source = STR.TargetFileSource(self.pkg, self.spec, self.target_hook, self.listing, self.run_groups,
                                           self._smoke_pick(), self.log)
        units = coords = group_rows = 0
        big_group = None
        per_group_units = []
        for g in self.source.groups:
            mine = [h for h in self.source.files if h[0] == g]
            big = max(mine, key=lambda h: per_file[h[2]])
            sample = self.source.read(big)
            per_group_units.append(int(len(set(sample.unit_ids.tolist()))))
            units += per_group_units[-1]
            coords = max(coords, len(mine) * int(len(np.unique(STR._coord(sample.time_columns, self.spec.time_facts)))))
            if sum(per_file[h[2]] for h in mine) > group_rows:
                big_group = g
            group_rows = max(group_rows, sum(per_file[h[2]] for h in mine))
        presence_plan = STR.PresenceReader(self.pkg, self.spec, self.feature_hook, self.run_groups)
        stores = len(presence_plan.stores)
        need = census_ram_bytes(units, coords, biggest, group_rows, stores)
        self.census_estimate = int(need)
        self._refuse_ram(need, "the target census of this run (%d rows in %d files; about %d units x %d calendar "
                               "steps, estimated from the biggest file of each group; one file of %d rows held at "
                               "once)" % (rows, len(files), units, coords, biggest))
        self.log("preflight: %d target rows in %d files, streamed (one file of at most %d rows at once, ~%d units x "
                 "%d steps of counters); census RAM estimate %.2f GiB: go"
                 % (rows, len(files), biggest, units, coords, need / GIB))
        # report only, never a refusal: R12 picks the router kind after the census, and the region and
        # neighbour kinds' bank counts are not bounded by the per-unit kind's (R18 (1)); the picked units'
        # column reader at the per-unit kind's C7 bank count, on whole histories of the estimated steps
        from treeroute import engine_constants as K
        from treeroute.runs import preflight

        bank = sum(min(int(K.BANK_UNITS_PER_GROUP), n) for n in per_group_units)
        free = preflight.available_ram_bytes()
        if self.per_group:
            # plan R20: the picked label rows are held whole; the column reader is one group's at a time
            largest = max(min(int(K.BANK_UNITS_PER_GROUP), n) for n in per_group_units) if per_group_units else 0
            labels = bank * coords * TARGET_ROW_BYTES
            # one driver file in flight: the biggest file of each store among the biggest group's (footers only)
            file_bytes = 0
            for plan in presence_plan.plan:
                paths = [p for _, p in D._files_of(plan.listing, [big_group])] if big_group is not None else []
                rows_f = max([int(pq.ParquetFile(p).metadata.num_rows) for p in paths] or [0])
                file_bytes = max(file_bytes, preflight.driver_file_bytes(rows_f, 1 + len(plan.parts) + len(plan.columns)))
            reader = preflight.column_reader_peak_bytes(largest * coords, self._frame_columns()) + file_bytes
            after = need + labels + reader
            self.log("preflight (report only): after the census, at the per-unit kind (C7: %d bank units per group), "
                     "the picked units' label rows (about %d units x %d steps: %.2f GiB) and ONE group's column reader "
                     "at its peak (plan R20: the largest group, about %d units x %d steps, %d frame columns, beside the "
                     "biggest driver file of the biggest group in flight: %.2f GiB) "
                     "beside the census (%.2f GiB): %.2f GiB in all, %.2f GiB available now%s (R12 decides the kind "
                     "after the census; each group's reader is refused before it is built when it does not fit)"
                     % (int(K.BANK_UNITS_PER_GROUP), bank, coords, labels / GIB, largest, coords,
                        self._frame_columns(), reader / GIB, need / GIB, after / GIB, free / GIB,
                        "; WARNING: at the per-unit kind this run will be refused after the census" if after > free
                        else ""))
            return
        picked = preflight.column_reader_peak_bytes(bank * coords, self._frame_columns())
        self.log("preflight (report only): after the census the picked units' column reader must fit as well: "
                 "at the per-unit kind (C7: %d bank units per group) about %d units x %d steps, %d frame columns: "
                 "%.2f GiB at its peak, %.2f GiB available now%s (R12 decides the kind after the census; the run "
                 "refuses before reading the picked rows when they do not fit)"
                 % (int(K.BANK_UNITS_PER_GROUP), bank, coords, self._frame_columns(), picked / GIB, free / GIB,
                    "; WARNING: at the per-unit kind this run will be refused after the census" if picked > free
                    else ""))

    def _refuse_ram(self, need: int, what: str) -> None:
        from treeroute.runs import preflight

        try:
            preflight.check_resources(self.machine.temp_dir, 0, int(need))
        except PreflightRefusal as exc:
            raise PipelineRefusal("G-DISK", "%s needs about %.2f GiB of RAM (%s)" % (what, need / GIB, exc),
                                  fix="free RAM (close other programs); the run size is never reduced; nothing "
                                      "is computed and no run folder is opened") from exc

    def _frame_columns(self) -> int:
        return len(self.spec.tree_features) + len(self.spec.context) + len(self.spec.feature_outputs) + 4

    def _check_picked_rows(self, n_rows: int) -> None:
        """RAM go/refuse before target rows are read again and joined (the streamed working set: a column
        reader of those rows at its peak, runs.preflight.column_reader_peak_bytes): the picked units' rows,
        and each unit block of R30's test-year count."""
        from treeroute.runs import preflight

        need = preflight.column_reader_peak_bytes(n_rows, self._frame_columns())
        self._refuse_ram(need, "the picked units' working set (%d target rows, %d frame columns, a column reader "
                         "at its peak)" % (n_rows, self._frame_columns()))

    def _check_label_rows(self, n_rows: int) -> None:
        """Per-group path (plan R20): RAM go/refuse before target rows are read again WITHOUT a column reader of
        them (the picked units' label rows; an R30 block's rows, whose reader has its own check first): a target
        row held (TARGET_ROW_BYTES) and one target file in flight (runs.preflight.CENSUS_FILE_ROW_BYTES a row of
        the biggest file). The column readers are checked one group at a time (_check_group_reader_rows)."""
        from treeroute.runs import preflight

        biggest = int(getattr(self, "_biggest_file_rows", 0))
        need = int(n_rows) * TARGET_ROW_BYTES + biggest * preflight.CENSUS_FILE_ROW_BYTES
        self._refuse_ram(need, "the picked units' working set (%d target rows read again for their labels, one file "
                         "of %d rows in flight; the column readers are built one group at a time)" % (n_rows, biggest))

    def _driver_file_bytes(self) -> int:
        """One driver file in flight inside a column reader (runs.preflight.driver_file_bytes): the biggest file of
        any driver store of the run (its rows from the census pass, its read columns from the store plan)."""
        from treeroute.pipeline import data as D
        from treeroute.runs import preflight

        pres = getattr(self, "presence", None)
        if pres is None:
            return 0
        out = 0
        for plan in pres.plan:
            rows = max([int(pres.file_rows.get(str(path), 0)) for _, path in D._files_of(plan.listing, self.run_groups)]
                       or [0])
            out = max(out, preflight.driver_file_bytes(rows, 1 + len(plan.parts) + len(plan.columns)))
        return out

    def group_reader_bytes(self, n_rows: int) -> int:
        """A per-group column reader at its peak: its rows (runs.preflight.column_reader_peak_bytes) and the biggest
        driver file in flight while it reads (_driver_file_bytes)."""
        from treeroute.runs import preflight

        return preflight.column_reader_peak_bytes(n_rows, self._frame_columns()) + self._driver_file_bytes()

    def _check_group_reader_rows(self, n_rows: int) -> None:
        """Per-group path (plan R20): RAM go/refuse before one group's picked-unit column reader is built (that
        group's rows, a column reader at its peak, and one driver file in flight: group_reader_bytes)."""
        self._refuse_ram(self.group_reader_bytes(n_rows),
                         "one group's picked-unit column reader (%d target rows, %d frame columns, a column reader at "
                         "its peak, beside one driver file of %.2f GiB in flight; plan R20: one group's reader at a "
                         "time)" % (n_rows, self._frame_columns(), self._driver_file_bytes() / GIB))

    def _check_sample_reader_rows(self, n_rows: int) -> None:
        """Per-group path: RAM go/refuse before the separability check's sample reader is built (the smoke-shaped
        sample of a few groups, together; stream.check_group_separable)."""
        self._refuse_ram(self.group_reader_bytes(n_rows),
                         "the separability check's sample column reader (%d target rows, %d frame columns, a column "
                         "reader at its peak, beside one driver file in flight)" % (n_rows, self._frame_columns()))

    def _block_row_budget(self) -> int:
        """The most target rows one unit block of R30's streamed test-year count holds: half the RAM
        available now over a column reader's peak bytes per row (asked again for every group)."""
        from treeroute.runs import preflight

        per_row = preflight.column_reader_peak_bytes(1, self._frame_columns())
        return max(1, int(preflight.available_ram_bytes() // 2 // per_row))

    def _smoke_pick(self):
        """R21's pick (group, the group's units with a valid label) -> its units: a stride over the sorted
        unit ids (validity only, never a value). None for a run that is not a smoke."""
        from treeroute import split as SP

        if not self.smoke:
            return None
        count = int(self.smoke_plan.value["units_per_group"])

        def pick(group, valid_units):
            units = tuple(sorted(set(str(u) for u in valid_units)))
            if not units:
                raise PipelineRefusal("R21", "smoke group %s has no unit with a valid label" % group)
            return SP.stride_pick(units, count)
        return pick

    def _smoke_keep(self):
        """read_target's keep_units(group, frame) for the in-memory path: the same pick on the group's frame."""
        import numpy as np

        pick = self._smoke_pick()
        if pick is None:
            return None
        spec = self.spec

        def keep(group, frame):
            valid = frame[np.isfinite(frame[spec.target_col].to_numpy(dtype=np.float64))]
            return pick(group, valid[spec.unit_col].astype(str).tolist())
        return keep

    def _preflight_frame(self) -> None:
        """RAM go/refuse for the joined feature frame, from the rows actually read."""
        from treeroute.runs import preflight

        n_cols = len(self.spec.tree_features) + len(self.spec.context) + len(self.reader.outputs) + 4
        need = len(self.target_df) * (TARGET_ROW_BYTES + FRAME_VALUE_BYTES * n_cols)
        preflight.check_resources(self.machine.temp_dir, 0, int(need))

    def _reader_peak_gib(self, n_rows: int) -> float:
        return self.group_reader_bytes(n_rows) / GIB

    def disk_plan(self) -> Dict[str, Any]:
        """Plan R20's per-group schedule: the temp disk that coexists at its peak, in bytes, by part (go/refuse
        only; it never sets a number). The pools stay open for the whole run: the nowcast pool (every bank unit x
        every vault step x the tree, history and context columns, float32) and the inner-cut history block; one
        forecast lead at a time adds its lead pool and its guard-cut history block. Tree-answer tables: ONE
        group's at a time (router.GroupTables, fit.tables.DropAfterRead), each table over at most the group's
        bank units' rows (every vault step; scored units are bank units, so a table over the scored rows and,
        for a fallback group or the region kind, the bank rows never exceeds it; any group may fall back at a
        lead, so the bound is counted for every group) x the bank's trees less the group's own (float32): the
        nowcast test pass holds 3 kinds (plain, corrector, placebo), the decision 2, the GLS weight model 1; a
        lead's guard 2 (the pinned kind and the corrector's fallback level), its test pass 2 (the pinned kind
        and the placebo). The peak is the largest group's."""
        from treeroute import timing

        w = self.derived["R7"].value
        steps = (int(timing.year_last_step(int(w.y_end), self.cadence))
                 - int(timing.year_last_step(int(w.y0) - 1, self.cadence)))
        lists = self.derived["R18:units"].value
        groups = sorted(lists.bank)
        bank = sum(len(v) for v in lists.bank.values())
        trees = len(groups) * self.trees_per_group
        cols = max(trees - self.trees_per_group, 0)
        n_hist = len(self.derived["R17"].value.columns)
        n_tree, n_ctx = len(self.spec.tree_features), len(self.spec.context)
        import numpy as np

        from treeroute import engine_constants as K
        from treeroute.fit.pool import POOL_DTYPE

        pitem, titem = np.dtype(POOL_DTYPE).itemsize, np.dtype(K.TREE_DTYPE).itemsize
        pool = bank * steps * (n_tree + n_hist + n_ctx) * pitem
        hist = bank * steps * n_hist * pitem
        per_kind = {g: len(lists.bank[g]) * steps * cols * titem for g in groups}
        big = max(groups, key=lambda g: (per_kind[g], g)) if groups else None
        table = per_kind[big] if big is not None else 0
        nowcast_tables = NOWCAST_TABLE_KINDS * table          # the weight model's one kind is fewer
        lead_tables = LEAD_TABLE_KINDS * table
        peak = pool + hist + max(nowcast_tables, pool + hist + lead_tables)
        return {"total": int(peak), "pool": int(pool), "history_block": int(hist), "lead_pool": int(pool),
                "lead_guard_history_block": int(hist), "largest_group": big, "largest_group_bank_units":
                len(lists.bank[big]) if big is not None else 0, "table_one_kind_largest_group": int(table),
                "nowcast_tables_at_peak": int(nowcast_tables), "lead_tables_at_peak": int(lead_tables),
                "steps": int(steps), "table_columns": int(cols), "groups": len(groups)}

    def _preflight_disk(self) -> None:
        """Disk go/refuse in the temp dir for the pool and the tree-answer tables (plan 4.5: which tables
        stay between passes changes hours, never a number). Per group (plan R20): what coexists under the
        schedule (disk_plan: the pools and the largest group's tables), refused when even that does not fit."""
        from treeroute import timing
        from treeroute.runs import preflight

        if self.per_group:
            parts = self.disk_plan()
            self.disk_parts = parts
            try:
                preflight.check_resources(self.temp_dir, parts["total"], 0)
            except PreflightRefusal as exc:
                raise PipelineRefusal("G-DISK", "the per-group schedule's temp disk at its peak (the pools %.2f GiB, "
                                      "one lead's pools %.2f GiB, and ONE group's tables: the largest group %s, %.2f "
                                      "GiB a kind, %d kinds in the nowcast, %d at a lead) does not fit: %s"
                                      % ((parts["pool"] + parts["history_block"]) / GIB,
                                         (parts["lead_pool"] + parts["lead_guard_history_block"]) / GIB,
                                         parts["largest_group"], parts["table_one_kind_largest_group"] / GIB,
                                         NOWCAST_TABLE_KINDS, LEAD_TABLE_KINDS, exc),
                                      fix="free disk on the temp drive; the run size is never reduced") from exc
            self.log("preflight: temp disk under the per-group schedule %.2f GiB at its peak (pools %.2f GiB; one "
                     "lead's pools %.2f GiB; the largest group %s's tables %.2f GiB a kind: %.2f GiB in the nowcast, "
                     "%.2f GiB at a lead): go"
                     % (parts["total"] / GIB, (parts["pool"] + parts["history_block"]) / GIB,
                        (parts["lead_pool"] + parts["lead_guard_history_block"]) / GIB, parts["largest_group"],
                        parts["table_one_kind_largest_group"] / GIB, parts["nowcast_tables_at_peak"] / GIB,
                        parts["lead_tables_at_peak"] / GIB))
            return

        w = self.derived["R7"].value
        steps = (int(timing.year_last_step(int(w.y_end), self.cadence))
                 - int(timing.year_last_step(int(w.y0) - 1, self.cadence)))
        lists = self.derived["R18:units"].value
        bank = sum(len(v) for v in lists.bank.values())
        scored = sum(len(v) for v in lists.scored.values())
        trees = len(lists.bank) * self.trees_per_group
        n_hist = len(self.derived["R17"].value.columns)
        n_cols = len(self.spec.tree_features) + len(self.spec.context) + n_hist
        pool = bank * steps * (n_cols + n_hist) * 4          # + the inner-cut history block
        tables = scored * steps * trees * 4 * TABLES_PER_ROW + bank * steps * trees * 4
        # the forecast ladder holds one lead at a time: its pool and its tables (pinned tool, placebo at the
        # longest lead, the bank rows of the region kind or of a fallback group) beside the nowcast's, and while
        # its guard runs the guard-cut history block and the guard-cut bank's tables (owner ruling H2)
        lead = bank * steps * n_cols * 4 + scored * steps * trees * 4 * TABLES_PER_LEAD + bank * steps * trees * 4
        lead += bank * steps * n_hist * 4 + scored * steps * trees * 4 * GUARD_TABLES_PER_LEAD \
            + bank * steps * trees * 4
        preflight.check_resources(self.temp_dir, pool + tables + lead, 0)
        self.log("preflight: temp disk for the pool, the tables and one forecast lead %.2f GiB: go"
                 % ((pool + tables + lead) / GIB))

    def _read(self) -> None:
        from treeroute.derive.rules import derive_r01_cadence
        from treeroute.pipeline import data as D

        if self.streamed:
            return self._read_census()
        keep = self._smoke_keep()
        self.target_df = D.read_target(self.pkg, self.spec, self.target_hook, self.listing, self.run_groups,
                                       keep, self.log)
        self.target = D.target_table(self.target_df, self.spec)
        self.cadence = derive_r01_cadence(self.target.unit_ids, self.target.time_columns,
                                          self.spec.time_facts).value
        self.reader = D.ColumnReader(self.pkg, self.spec, self.target_df, self.cadence, self.feature_hook, self.log)
        self._preflight_frame()

    def _read_census(self) -> None:
        """Step 1, streamed: one pass over the target files into the census (with the drivers' row presence
        per file); R1's cadence from it. No target row is kept."""
        from treeroute.derive.census import scan_target
        from treeroute.pipeline import stream as STR

        t0 = time.time()
        self.presence = STR.PresenceReader(self.pkg, self.spec, self.feature_hook, self.run_groups)
        self.census = scan_target(self.source, self.spec.time_facts, self.presence,
                                  expected_rows=self.source.expected_rows(), echo=self.log)
        # RAM go/refuse before ANY picked rows are read again (plan_labels, the column reader, R30's blocks); per
        # group (plan R20) the label rows are checked as target rows, each group's reader at its own build
        self.census.row_guard = self._check_label_rows if self.per_group else self._check_picked_rows
        self.cadence = self.census.r01().value
        self.log("census: %d rows, %d units in %.1f s (driver key files read %d)"
                 % (self.census.rows, self.census.n_units(), time.time() - t0, len(self.presence.files_read)))

    def _derive(self) -> None:
        if self.census is not None:
            return self._derive_streamed()
        return self._derive_in_memory()

    def _derive_streamed(self) -> None:
        """Step 2, streamed: derive_all_streamed over the census (twice when labels before Y0 are withheld,
        as the in-memory path runs derive_all twice); then the picked units' full rows for the vault and the
        column reader (the bank units of the final derivation)."""
        from types import SimpleNamespace as NS

        from treeroute import timing
        from treeroute.derive import derived_sha256
        from treeroute.derive.census import derive_all_streamed, withheld_counts
        from treeroute.derive.derived import make_derived
        from treeroute.derive.orchestrate import _Facts
        from treeroute.pipeline import stream as STR

        t0 = time.time()
        derive_pkg, split_view = self._split_view()
        share = STR.StreamedShareReader(self.pkg, self.spec, self.census, self.cadence, self.feature_hook, self.log,
                                        self._check_picked_rows, self._block_row_budget, group_readers=self.per_group,
                                        reader_rows=self._check_group_reader_rows,
                                        sample_rows=self._check_sample_reader_rows)
        first = dict(derive_all_streamed(derive_pkg, self.census, share))
        if first["R1"].value != self.cadence:
            raise PipelineRefusal("R1", "derive_all's cadence differs from the reader's")
        y0 = int(first["R4"].value)
        y0_first = int(timing.year_last_step(y0 - 1, self.cadence)) + 1
        target_facts = _Facts(derive_pkg).target
        n_before, valid_before = withheld_counts(self.census, self.cadence, target_facts, y0_first)
        self.derived = first
        if n_before:
            self.derived = dict(derive_all_streamed(derive_pkg, self.census, share, withhold_before_step=y0_first))
            if int(self.derived["R4"].value) != y0 or self.derived["R7"].value.y0 != y0:
                raise PipelineRefusal("R4", "Y0 moved when the lag-source labels were withheld (%s -> %s)"
                                      % (y0, self.derived["R4"].value))
            self.derived["R4:model_labels"] = make_derived("R4", {"first_model_step": y0_first}, {
                "rule": "labels before Y0 are withheld from derive's label views (C4: the years before Y0 are "
                        "lag sources only); the run's vault holds [Y0, Y_end]",
                "withheld_rows": int(n_before),
                "withheld_valid_labels": int(valid_before),
                "first_pass_sha256": derived_sha256(first)})
            self.model_labels_withheld = True
        lists = self.derived["R18:units"].value
        picked = tuple(u for g in sorted(lists.bank) for u in lists.bank[g]) + \
            tuple(u for g in sorted(lists.scored) for u in lists.scored[g])
        if self.per_group:
            # plan R20: the column readers of the final picks, one group at a time (R30's last measure built
            # them over the picked rows read for its labels: the same rows)
            self.reader = share.group_readers
            self.reader_builds_replaced = int(share.reader_builds_replaced)
            if self.reader is None or self.census._picked is None or \
                    tuple(self.census._picked[0]) != tuple(sorted(set(picked))):
                raise PipelineRefusal("R20", "internal: the per-group column readers are not the final picks' "
                                      "(R30 measured on other picked units)")
            self.separability = share.separability
            g, n = self.reader.largest()
            self.log("per-group column readers: %d groups, the largest %s with %d picked rows (%.2f GiB at its "
                     "reader's peak); feature script: %s" % (len(self.reader.groups), g, n,
                                                             self._reader_peak_gib(n),
                                                             (self.separability or {}).get("result")
                                                             or (self.separability or {}).get("reason")))
        else:
            self.reader = share.reader_for(sorted(set(picked)))
        rows = self.census.read_units(sorted(set(picked)))
        self.target = NS(unit_ids=rows.unit_ids, group_ids=rows.group_ids, time_columns=rows.time_columns, y=rows.y)
        self.data_manifest = STR.census_data_manifest(self.reader, self.census, self.presence)
        self.driver_files = list(self.presence.files_read)        # every run group's, read by the census pass
        self.log("picked units' rows read again: %d rows of %d units (of %d census rows); R30 test-year shares: %s%s"
                 % (len(rows.unit_ids), len(set(picked)), self.census.rows, share.test_year_source,
                    (" %s" % (share.test_year_stats,)) if share.test_year_stats else ""))
        self._derive_finish(t0, split_view)

    def _derive_in_memory(self) -> None:
        import numpy as np

        from treeroute import split as SP
        from treeroute import timing
        from treeroute.derive import derive_all, derived_sha256
        from treeroute.derive.derived import make_derived
        from treeroute.io.steps import step_index
        from treeroute.pipeline import data as D

        t0 = time.time()
        derive_pkg, split_view = self._split_view()
        first = dict(derive_all(derive_pkg, self.target, self.reader))
        if first["R1"].value != self.cadence:
            raise PipelineRefusal("R1", "derive_all's cadence differs from the reader's")
        # C4 / R4: the data years before Y0 are read ONLY as lag sources. derive_all's label views read every
        # valid label at or before a cut from the target's first step, so a second pass withholds (NaN) the
        # labels before Y0: its donor views (R18's event rate, R19, R23, R30) then hold the model rows the
        # run's vault holds, [Y0, Y_end], and the run's own checks (R23) compare like with like. This reading
        # is ruled acceptable (S21 accept, OWNER_RULINGS_2026-10-06.md N; MODEL_LABELS_DEPARTURE).
        y0 = int(first["R4"].value)
        y0_first = int(timing.year_last_step(y0 - 1, self.cadence)) + 1
        steps = step_index(self.target.time_columns, self.spec.time_facts, self.cadence)
        before = steps < y0_first
        self.derived = first
        if before.any():
            y_model = np.where(before, np.nan, self.target.y)
            model_target = SimpleNamespace(unit_ids=self.target.unit_ids, group_ids=self.target.group_ids,
                                           time_columns=self.target.time_columns, y=y_model)
            self.derived = dict(derive_all(derive_pkg, model_target, self.reader))
            if int(self.derived["R4"].value) != y0 or self.derived["R7"].value.y0 != y0:
                raise PipelineRefusal("R4", "Y0 moved when the lag-source labels were withheld (%s -> %s)"
                                      % (y0, self.derived["R4"].value))
            self.derived["R4:model_labels"] = make_derived("R4", {"first_model_step": y0_first}, {
                "rule": "labels before Y0 are withheld from derive's label views (C4: the years before Y0 are "
                        "lag sources only); the run's vault holds [Y0, Y_end]",
                "withheld_rows": int(before.sum()),
                "withheld_valid_labels": int(np.isfinite(self.target.y[before]).sum()),
                "first_pass_sha256": derived_sha256(first)})
            self.model_labels_withheld = True
        self.data_manifest = self.reader.data_manifest()
        self.driver_files = list(self.reader.files_read)
        self._derive_finish(t0, split_view)

    def _derive_finish(self, t0: float, split_view: Any) -> None:
        import numpy as np

        from treeroute import split as SP
        from treeroute.pipeline import data as D

        if split_view is not None:
            self.derived["R18:split_view"] = split_view
        if self.smoke_plan is not None:
            self.derived["R21:smoke_selection"] = self.smoke_plan
        self.static = D.read_static(self.pkg, self.spec, self.run_groups, extra=self.reader.strata_unread)
        grid_cols = [c for c in D.STATIC_GRID if c in self.static.columns]
        blocks = SP.derive_overlap_blocks(
            self.static[self.spec.group_col].to_numpy(dtype=object),
            self.static[D.STATIC_LAT].to_numpy(dtype=np.float64),
            self.static[D.STATIC_LON].to_numpy(dtype=np.float64),
            self.static["grid_ix"].to_numpy() if grid_cols else None,
            self.static["grid_iy"].to_numpy() if grid_cols else None)
        self.derived["R14:overlap_blocks"] = blocks
        self.blocks = blocks.value
        missing = sorted(set(self.derived["R18:groups"].value) - set(self.blocks.block_of_group))
        if missing:
            raise PipelineRefusal("R14", "groups %s have no unit in the static table" % missing[:5])
        self.strata = D.stratum_values(self.spec, self.reader, self.static)
        # J2 d: the last-value rule ran inside the column reader's lagged frame (R30 measured after it); its
        # counts go into the run record and the log
        self.last_value = self.reader.last_value_record(self.derived["R8"].value)
        self.log(self.last_value.summary_line())
        self.log("derive_all: %d entries in %.1f s; router %s; overlap blocks %d for %d groups%s"
                 % (len(self.derived), time.time() - t0, self.derived["R12"].value.value,
                    len(self.blocks.members), len(self.blocks.block_of_group),
                    ("; report strata %s" % ", ".join(self.strata)) if self.strata else ""))

    def _release_census(self) -> None:
        """Per-group path, 'run' only: nothing after derive reads the census (the picked rows, the vault, the data
        manifest and the per-group readers hold what the run reads), so its bit matrices and unit table and the
        presence reader's key cache are released before the fits (RAM only; its counts stay in census_counts)."""
        import gc

        if self.census is None:
            return
        self.census_counts = {"rows": int(self.census.rows), "units": int(self.census.n_units())}
        self.census = None
        if getattr(self, "presence", None) is not None:
            self.presence._cache.clear()
        gc.collect()
        self.log("census released after derive (%d rows, %d units): the per-group run reads the picked rows only"
                 % (self.census_counts["rows"], self.census_counts["units"]))

    def _split_view(self):
        """derive_all reads split.yaml against the target rows it is handed and refuses a group the split
        names that those rows do not hold. The pipeline reads the rows of the run's groups only: never an
        excluded group's (so a group excluded for missing drivers cannot stop the read), and a smoke reads
        its own groups only. derive_all is therefore handed the package with a split VIEW that names only
        the read groups (the run's groups are the same: the data's groups minus the exclusions). What the
        view leaves out is recorded ('R18:split_view'), and the run's split sets become the view's.
        Returns (package for derive, entry or None)."""
        from treeroute import split as SP
        from treeroute.derive.derived import make_derived
        from treeroute.package.schema import SplitFile

        read = set(self.run_groups)
        split = self.pkg.split
        excluded = dict(split.excluded)
        seen = list(split.seen_during_design)
        dropped_ex = {g: r for g, r in sorted(excluded.items()) if g not in read}
        dropped_seen = sorted(g for g in seen if g not in read)
        if not dropped_ex and not dropped_seen:
            return self.pkg, None
        self.split_view_dropped = sorted(dropped_ex)
        view = SplitFile(excluded={g: r for g, r in excluded.items() if g in read},
                         seen_during_design=[g for g in seen if g in read])
        # every later reader of the split (the vault's donor views, FitContext, the report) reads the same
        # view as derive_all: the groups of the run are the same, and no view names a group left unread
        self.split_sets = SP.loro_split_sets(view)
        entry = make_derived("R18", {"excluded_not_read": dropped_ex, "seen_during_design_not_read": dropped_seen},
                             {"rule": "derive_all is handed the target rows of the run's groups only; its split "
                                      "view names only those groups (the excluded groups' rows are never read, a "
                                      "smoke reads its own groups); the run's groups are unchanged",
                              "read_groups": len(read)})
        self.log("split view for derive_all: excluded groups not read %s; seen_during_design groups not read %s"
                 % (sorted(dropped_ex), dropped_seen))
        return self.pkg._replace(split=view), entry

    # ------------------------------------------------------------------ the vault (step 3)
    def _vault(self, run_folder: Optional[Path]):
        import numpy as np

        from treeroute import timing
        from treeroute.io.steps import step_index
        from treeroute.pipeline import stages as ST

        w = self.derived["R7"].value
        first = int(timing.year_last_step(int(w.y0) - 1, self.cadence)) + 1
        last = int(timing.year_last_step(int(w.y_end), self.cadence))
        test_first = int(timing.year_last_step(min(w.test_years) - 1, self.cadence)) + 1
        lists = self.derived["R18:units"].value
        bank = sorted(u for g in lists.bank for u in lists.bank[g])
        t = self.target
        keep = np.isin(t.unit_ids, np.asarray(bank, dtype=object))
        steps = step_index(t.time_columns, self.spec.time_facts, self.cadence)
        tf = self.pkg.catalog.columns[self.spec.target_col]
        target_facts = SimpleNamespace(name=self.spec.target_col, window=tf.window, stamp=tf.stamp,
                                       computed_from=tuple(tf.computed_from), fact_status=tf.fact_status)
        return ST.build_vault(t.unit_ids[keep], t.group_ids[keep], steps[keep], t.y[keep], (first, last),
                              test_first, self.cadence, target_facts, run_folder)

    def _smoke_bank_plans(self, vg: Any) -> None:
        """R19 re-derived with the smoke tree count from the vault's donor views (same rows as plan's)."""
        from treeroute.derive.shapes import CutKind
        from treeroute.derive.unit_rules import derive_r19_bank_plan, derive_r19_inner_cut_bank_plan

        lists = self.derived["R18:units"].value
        bank = tuple(u for g in sorted(lists.bank) for u in lists.bank[g])
        cuts = self.derived["R11"].value[0]
        for name, cut, kind, rule, base in (("R19:smoke", cuts.fit_cut, CutKind.FIT, derive_r19_bank_plan, "R19"),
                                            ("R19:inner_cut_smoke", cuts.guard_cut, CutKind.GUARD,
                                             derive_r19_inner_cut_bank_plan, "R19:inner_cut")):
            if base not in self.derived:
                continue
            view = vg.labels.donor_labels(self.split_sets, int(cut), kind, 0, bank, "bank_plan_smoke",
                                          picks=lists)
            entry = rule(view, True)
            planned = self.derived[base].input_hashes.get("donor_row_key_hash")
            if entry.input_hashes.get("donor_row_key_hash") != planned:
                raise PipelineRefusal("R19", "the smoke bank plan's donor rows (row-key hash %s) are not the rows "
                                      "derive_all's %s read (%s)" % (entry.input_hashes.get("donor_row_key_hash"),
                                                                    base, planned))
            self.derived[name] = entry

    # ------------------------------------------------------------------ the run folder
    def _unit_list_hashes(self) -> Dict[str, Any]:
        """Plan 7.1: the bank and scored unit-list hashes per group, and the overlap blocks."""
        lists = self.derived["R18:units"].value
        return {"bank": {g: _sha_json(list(lists.bank[g])) for g in sorted(lists.bank)},
                "scored": {g: _sha_json(list(lists.scored.get(g, ()))) for g in sorted(lists.bank)},
                "bank_all": self.derived["R18:units"].inputs["bank_units_hash"],
                "scored_all": self.derived["R18:units"].inputs["scored_units_hash"],
                "overlap_blocks": _sha_json([list(b) for b in self.blocks.members])}

    def _plan_check(self) -> None:
        """Plan 4.1 step 2: a headline run refuses when derived.json differs from the one the package's
        latest plan showed (the headline folder whose plan phase finished last, finished or not). With no
        plan folder the run derives its own and records that."""
        from treeroute.runs.atomic import read_json
        from treeroute.runs.resume import PHASE_DONE, PHASES_DIR

        kind_dir = self.run_root / self.package.dataset.name / self.kind
        plans = []
        if kind_dir.is_dir():
            for folder in kind_dir.iterdir():
                marker = folder / PHASES_DIR / PHASE_PLAN / PHASE_DONE
                if folder.is_dir() and marker.is_file():
                    info = read_json(marker)
                    plans.append((str(info.get("finished_utc")), marker.stat().st_mtime_ns, folder.name, folder, info))
        if not plans:
            self.plan_check = {"plan_folder": None, "derived_sha256": self.derived_sha,
                               "note": "no plan folder of this package: 'run' does not require a prior plan; "
                                       "the run derived its own derived.json (owner: rule whether a headline "
                                       "run must follow a plan)"}
            self.log("plan check: no plan folder of this package; this run's derived.json is its own")
            return
        _, _, _, folder, info = max(plans, key=lambda p: p[:3])
        shown = (info.get("summary") or {}).get("derived_sha256")
        if shown != self.derived_sha:
            raise PipelineRefusal("G-FINGERPRINT", "derived.json differs from the one the latest plan showed (%s: "
                                  "SHA-256 %s; this run derives %s): the data, the package or the engine changed "
                                  "since" % (folder, str(shown)[:16], self.derived_sha[:16]),
                                  fix="run 'treeroute plan' again and read plan.json before 'treeroute run'")
        self.plan_check = {"plan_folder": str(folder), "derived_sha256": shown,
                           "plan_finished_utc": info.get("finished_utc"),
                           "plan_fingerprint": info.get("fingerprint"),
                           "same_fingerprint": info.get("fingerprint") == self.fingerprint}
        self.log("plan check: derived.json equals the latest plan's (%s)" % folder.name)

    def _open(self) -> None:
        from treeroute import engine_constants as K
        from treeroute.derive import derived_sha256
        from treeroute.pipeline import data as D
        from treeroute.pipeline import record as REC
        from treeroute.runs.fingerprint import run_fingerprint
        from treeroute.runs.resume import Phases, open_run
        from treeroute.runs.status import StatusWriter

        self.derived_sha = derived_sha256(self.derived)
        self.not_headline = list(self.not_headline) + build_departures(self)
        self.config = {"kind": self.kind, "package": self.package.dataset.name,
                       "package_fingerprint": self.package.fingerprint, "derived_sha256": self.derived_sha,
                       "draft": self.draft.record(), "groups": list(self.run_groups),
                       "trees_per_group": self.trees_per_group,
                       "data": self.data_manifest, "target_files_sha256": _file_list_sha(self.data_files),
                       "static_files_sha256": _file_list_sha(D.static_files(self.pkg)),
                       "driver_files_sha256": _file_list_sha(self.driver_files),
                       "engine_constants_sha256": K.constants_hash(),
                       "feature_list": list(self.spec.tree_features) + list(self.derived["R17"].value.columns),
                       "context_list": list(self.spec.context), "strata": list(self.spec.strata)}
        self.fingerprint = run_fingerprint(self.config)
        if self.kind == REC.KIND_HEADLINE and not self._planning:
            self._plan_check()
        handle = open_run(self.run_root, self.package.dataset.name, self.kind, self.fingerprint, self.registry)
        self.folder = Path(handle.path)
        self.log.attach(self.folder)
        self.log("run folder %s (%s)" % (self.folder, handle.state))
        self.phases = Phases(self.folder, self.fingerprint)
        self.status = StatusWriter(self.folder, self.fingerprint)
        self.status.beat(PHASE_PLAN, "derived.json")
        rec = REC.run_record(self.kind, self.package, self.fingerprint, self.draft, self.not_headline, LIMITS,
                             {"derived_sha256": self.derived_sha, "groups": list(self.run_groups),
                              "departures": build_departures(self),
                              "listed_in_reports": list(self.spec.listed_in_reports),
                              "strata": list(self.spec.strata), "feature_lineage": self.feature_lineage,
                              "last_value": dict(self.last_value.as_dict(),
                                                 rows_scope="the column reader's rows: every row of each unit it "
                                                            "holds (the pool and R30's donor shares read these); "
                                                            "run_target_rows and run_units are every target row "
                                                            "and unit the run read",
                                                 run_target_rows=int(self.data_manifest["target_rows"]),
                                                 run_units=int(self.data_manifest["units"]))})
        REC.write_once_or_same(self.folder / REC.RUN_RECORD, rec)
        derived_path = self.folder / REC.DERIVED_FILE
        if derived_path.exists():
            from treeroute.derive import derived_document
            from treeroute.runs.atomic import dumps

            # internal: the fingerprint hashes derived.json, so a resumed folder's copy is identical
            now = json.loads(dumps(derived_document(self.derived)))
            if json.loads(derived_path.read_text(encoding="utf-8")) != now:
                raise PipelineRefusal("G-FINGERPRINT", "derived.json in %s differs from the one derived now"
                                      % self.folder, fix="plan again: the data or the package changed")
        else:
            from treeroute.derive import write_derived_json

            write_derived_json(derived_path, self.derived)
        REC.write_once_or_same(self.folder / REC.PLAN_FILE, self._plan_document())
        if self.plan_check:
            path = self.folder / PLAN_CHECK_FILE
            if path.exists():
                # a resumed run: the first process's check is the record (the check itself ran again above)
                self.log("plan check (resumed run): %s" % json.dumps(self.plan_check, default=str))
            else:
                REC.write_once_or_same(path, self.plan_check)
        manifest_path = self.folder / "manifest.json"
        if not manifest_path.exists():
            from treeroute.runs.machine import machine_record
            from treeroute.runs.manifest import build_manifest, write_manifest

            write_manifest(self.folder, build_manifest(
                self.fingerprint, self.package.fingerprint, machine_record(self.machine), config=self.config,
                launch_record=self.launch_record,
                feature_list=self.config["feature_list"],
                unit_list_hashes=self._unit_list_hashes(),
                table_schedule={"kinds": ["plain", "corrector", "placebo_corrector"],
                                "built": "per group; plain and corrector over the scored units' rows, the placebo "
                                         "after the adoption lock; per-group batching (plan R20) drops a group's "
                                         "tables once it is routed, so a row a later pass needs is built again "
                                         "(tables.json 'schedule')"}))
        if self.per_group:
            REC.write_once_or_same(self.folder / PER_GROUP_PLAN_FILE, self._per_group_plan())
        if not self.phases.done(PHASE_PLAN):
            self.phases.mark_done(PHASE_PLAN, {"derived_sha256": self.derived_sha})

    def _per_group_plan(self) -> Dict[str, Any]:
        """per_group_plan.json (plan R20's per-group schedule; deterministic): the separability check, the
        groups' picked rows and the largest group's reader at its peak, and the run's temp disk at its peak
        (disk_plan), in bytes and GiB."""
        g, n = self.reader.largest()
        disk = self.disk_plan()
        return {"rule": "plan R20 per-group batching (pipeline/run.py docstring)",
                "separability": self.separability,
                "readers": {"groups": len(self.reader.groups), "largest_group": g, "largest_group_rows": int(n),
                            "picked_rows": int(sum(self.reader.rows_of(x) for x in self.reader.groups)),
                            "frame_columns": self._frame_columns(),
                            "largest_reader_peak_bytes": int(round(self._reader_peak_gib(n) * GIB)),
                            "largest_reader_peak_gib": round(self._reader_peak_gib(n), 3),
                            "label_rows_bytes": int(sum(self.reader.rows_of(x) for x in self.reader.groups))
                            * TARGET_ROW_BYTES},
                "temp_disk": dict(disk, total_gib=round(disk["total"] / GIB, 3)),
                "ram": self.ram_plan()}

    def ram_plan(self) -> Dict[str, Any]:
        """Plan R20's per-group schedule: RAM that coexists at the run's peaks, by part, in bytes (report only; each
        part has its own go/refuse where it is built: the census, the label rows and each group's reader in derive
        and the pool fills (Pipeline._refuse_ram), the GLS weight model's peak in fit.weights.weight_model_for_cut
        before its donor matrix is built (G-DISK), the tree-answer stores' row blocks in fit.tables). Derive: the
        census (resident until the picks are read; its pre-flight estimate), the picked units' label rows, ONE
        group's column reader at its peak (the largest group's, beside one driver file in flight). Run: the census
        is released after derive; a pool fill holds one group's reader; the GLS weight model (per-unit kind only,
        fit.weights.gls_ram_bytes) holds its donor rows' features whole, a fit over every group by design (R25):
        every bank unit's rows up to the guard cut x the tree and history columns, float32 (an upper bound: only
        valid labels are rows), at its peak while the matrix is built (in row blocks into one float32 array: the
        matrix beside one block's read and mask), beside the largest group's answer read of the donor-row pass
        (the store's read of that group's rows x the bank's trees less its own: its float32 output beside the
        table's gathered rows and its row-index arrays while in flight, then that output held whole beside one row
        block's column copy and float64 copy), or beside the forest's fit. Not counted: the banks' trees and the
        router's per-unit loads (no estimate exists; the go/refuse at each GLS fit reads the RAM available then,
        after the banks are fitted)."""
        from treeroute import timing
        from treeroute.fit.weights import gls_ram_bytes
        from treeroute.pipeline import router as PR

        g, n = self.reader.largest()
        labels = int(sum(self.reader.rows_of(x) for x in self.reader.groups)) * TARGET_ROW_BYTES
        reader = self.group_reader_bytes(n)
        w = self.derived["R7"].value
        first = int(timing.year_last_step(int(w.y0) - 1, self.cadence)) + 1
        guard = int(self.derived["R11"].value[0].guard_cut)
        lists = self.derived["R18:units"].value
        cols = len(self.spec.tree_features) + len(self.derived["R17"].value.columns)
        kind = self.derived["R12"].value
        per_unit = getattr(kind, "value", kind) == PR.KIND_PER_UNIT       # (the neighbour kind is refused at the fits)
        gls: Dict[str, Any] = {"peak": 0, "matrix": 0, "build": 0, "answer_read": 0, "forest": 0,
                               "answer_read_group": None, "build_block_rows": 0, "answer_block_rows": 0}
        if per_unit:
            steps = max(guard - first + 1, 0)
            trees = len(lists.bank) * int(self.trees_per_group)
            gls = gls_ram_bytes({x: len(v) * steps for x, v in lists.bank.items()}, cols,
                                {x: trees - int(self.trees_per_group) for x in lists.bank})
        census = int(getattr(self, "census_estimate", 0))
        run_peak = labels + max(reader, int(gls["peak"]))
        return {"derive_peak": census + labels + reader, "census_estimate": census, "label_rows": labels,
                "largest_group_reader": reader, "largest_group": g, "run_gls_donor_matrix": int(gls["matrix"]),
                "run_gls_matrix_build": int(gls["build"]), "run_gls_answer_read": int(gls["answer_read"]),
                "run_gls_answer_read_group": gls["answer_read_group"], "run_gls_forest": int(gls["forest"]),
                "run_gls_build_block_rows": int(gls["build_block_rows"]),
                "run_gls_answer_block_rows": int(gls["answer_block_rows"]),
                "run_gls_peak": int(gls["peak"]), "run_peak_listed": run_peak,
                "not_counted": "the banks' trees, the router's per-unit loads",
                "derive_peak_gib": round((census + labels + reader) / GIB, 3),
                "run_gls_peak_gib": round(int(gls["peak"]) / GIB, 3),
                "run_peak_listed_gib": round(run_peak / GIB, 3)}

    def _report_disk_plan(self) -> None:
        """plan (report only, never a refusal): the run's temp disk under the per-group schedule against the free
        space of the machine's temp root now."""
        from treeroute.runs import preflight

        parts = self.disk_plan()
        free = preflight.free_disk_bytes(self.temp_root)
        self.log("preflight (report only): 'run' will need %.2f GiB of temp disk at its peak under the per-group "
                 "schedule (pools %.2f GiB, one lead's pools %.2f GiB, the largest group %s's tables %.2f GiB a kind); "
                 "%.2f GiB free at %s now%s" % (parts["total"] / GIB, (parts["pool"] + parts["history_block"]) / GIB,
                                                (parts["lead_pool"] + parts["lead_guard_history_block"]) / GIB,
                                                parts["largest_group"], parts["table_one_kind_largest_group"] / GIB,
                                                free / GIB, self.temp_root,
                                                "; WARNING: 'run' will refuse at its disk check" if parts["total"] > free
                                                else ""))
        ram = self.ram_plan()
        self.log("preflight (report only): RAM under the per-group schedule: derive %.2f GiB (census %.2f, label rows "
                 "%.2f, the largest group %s's reader %.2f); run: the census released, the GLS weight model at its "
                 "peak %.2f GiB (donor matrix %.2f GiB, a fit over every group, R25: %.2f while it is built, %.2f "
                 "beside group %s's answer read, %.2f beside the forest; refused before the matrix is built when it "
                 "does not fit) beside the label rows; not counted: %s"
                 % (ram["derive_peak"] / GIB, ram["census_estimate"] / GIB, ram["label_rows"] / GIB,
                    ram["largest_group"], ram["largest_group_reader"] / GIB, ram["run_gls_peak"] / GIB,
                    ram["run_gls_donor_matrix"] / GIB, ram["run_gls_matrix_build"] / GIB,
                    ram["run_gls_answer_read"] / GIB, ram["run_gls_answer_read_group"], ram["run_gls_forest"] / GIB,
                    ram["not_counted"]))

    def _plan_document(self) -> Dict[str, Any]:
        w = self.derived["R7"].value
        lists = self.derived["R18:units"].value
        return {"kind": self.kind, "package": self.package.dataset.name, "draft": self.draft.record(),
                "not_headline_reasons": list(self.not_headline), "limits": list(LIMITS),
                "router_kind": self.derived["R12"].value.value, "links": [l.value for l in self.derived["R22"].value],
                "windows": {"y0": w.y0, "y_end": w.y_end, "test_years": list(w.test_years),
                            "train_end": w.train_end, "inner_fit": list(w.inner_fit),
                            "inner_score": list(w.inner_score)},
                "groups": len(lists.bank), "bank_units": {g: len(v) for g, v in lists.bank.items()},
                "scored_units": {g: len(v) for g, v in lists.scored.items()},
                "trees_per_group": self.trees_per_group,
                "overlap_blocks": [list(b) for b in self.blocks.members if len(b) > 1],
                "history_columns": list(self.derived["R17"].value.columns),
                "tree_features": len(self.spec.tree_features), "context": list(self.spec.context),
                "listed_in_reports": list(self.spec.listed_in_reports), "strata": list(self.spec.strata),
                "feature_lineage": self.feature_lineage,
                "leads": list(self.derived["R10"].value.leads),
                "phases": [PHASE_PLAN, PHASE_DECISION, PHASE_TEST, PHASE_REPORT] + self._ladder_phases()}

    def _ladder_phases(self) -> List[str]:
        from treeroute.pipeline import ladder as LAD

        try:
            return LAD.phase_names(self.derived)
        except NotImplementedError:
            return []

    # ------------------------------------------------------------------ the run's temp folder
    def _temp(self) -> None:
        self.temp_dir = self.registry.assert_writable(
            self.temp_root / ("%s%s_%d" % (TEMP_PREFIX, self.fingerprint[:8], os.getpid())))
        self.temp_dir.mkdir(exist_ok=False)

        def remove_temp():
            gc.collect()
            left = sorted(p.name for p in self.temp_dir.iterdir())
            if left:
                raise PipelineRefusal("G-DISK", "temp files left in %s: %s" % (self.temp_dir, left[:5]))
            self.temp_dir.rmdir()
        self._cleanup.append(remove_temp)
        self._preflight_disk()

    # ------------------------------------------------------------------ public entry points
    def plan(self) -> Path:
        """Steps 1-2 only: derived.json and plan.json in the run folder (no fit). Holds the heavy-job lock:
        it reads the whole target."""
        self._planning = True
        try:
            self._lock()
            self._load()
            self._groups()
            self._preflight_target()
            self._read()
            self._derive()
            if self.smoke:
                self._smoke_bank_plans(self._vault(None))
            self._open()
            if self.per_group:
                self._report_disk_plan()
            self.log("plan written: %s" % (self.folder / "plan.json"))
            return self.folder
        finally:
            self._release()

    def run(self) -> Path:
        try:
            self._lock()
            self._load()
            self._groups()
            self._preflight_target()
            self._read()
            self._derive()
            if self.smoke:
                self._smoke_bank_plans(self._vault(None))
            self._open()
            if self.per_group:
                self._release_census()
            self._temp()
            try:
                self._compute()
            except BaseException as exc:
                self.status.fail(getattr(self, "_phase", "run"), "%s: %s" % (type(exc).__name__, str(exc)[:300]))
                raise
            return self.folder
        finally:
            self._release()

    # ------------------------------------------------------------------ steps 3-12
    def _compute(self) -> None:
        from treeroute.pipeline import ladder as LAD
        from treeroute.pipeline import passes as P
        from treeroute.runs.atomic import read_json
        from treeroute.runs.resume import PHASE_DONE, PHASES_DIR, mark_run_finished

        done_decision = self.phases.done(PHASE_DECISION) or (self.folder / "adoption.json.lock.json").exists()
        done_test = self.phases.done(PHASE_TEST)
        done_report = self.phases.done(PHASE_REPORT)
        ladder_phases = LAD.phase_names(self.derived)
        done_ladder = all(self.phases.done(ph) for ph in ladder_phases)
        if done_report and done_ladder:
            mark_run_finished(self.folder, self.fingerprint, {"resumed": True})
            return
        with P.RunState(self) as state:
            self._phase = "pool"
            state.build_pool(need_inner=not done_decision)
            self._phase = "fits"
            state.fit(need_inner=not done_decision)
            if not done_decision:
                self._phase = PHASE_DECISION
                state.decision()
                self.phases.mark_done(PHASE_DECISION, {"adoption_sha256": state.adoption_sha})
            else:
                state.read_adoption()
                self.log("decision: resumed from the locked adoption.json (SHA-256 %s)" % state.adoption_sha[:16])
                if not self.phases.done(PHASE_DECISION):
                    # the process that locked the adoption stopped before its marker: the lock is the record
                    self.phases.mark_done(PHASE_DECISION, {"adoption_sha256": state.adoption_sha,
                                                           "marked_on_resume": True})
            if not done_test:
                self._phase = PHASE_TEST
                state.test_pass()
                self.phases.mark_done(PHASE_TEST, {"rows": state.n_test_rows})
            if not done_report:
                self._phase = PHASE_REPORT
                summary = state.report()
                state.write_log_part("report")
                self.phases.mark_done(PHASE_REPORT, summary)
            else:
                summary = dict(read_json(self.folder / PHASES_DIR / PHASE_REPORT / PHASE_DONE).get("summary") or {})
            # step 11: the forecast ladder (its own phases, each marked done after its records)
            ladder = LAD.Ladder(state)
            out = ladder.run(self.phases)
            if not out:
                out = dict(read_json(self.folder / PHASES_DIR / LAD.PHASE_TABLE / PHASE_DONE).get("summary") or {})
            summary = dict(summary, ladder=out)
            state.write_fitctx_log(LAD.log_parts(self.derived))
            if self.per_group and not (self.folder / PER_GROUP_SCHEDULE_FILE).exists():
                # this process's schedule (a resumed run keeps the first process's file)
                from treeroute.pipeline import record as REC

                sep = self.separability or {}
                earlier = int(self.reader_builds_replaced)
                REC.write_once_or_same(self.folder / PER_GROUP_SCHEDULE_FILE, {
                    "rule": "plan R20 per-group batching: each pass's largest group's tables (bytes held right before "
                            "the group's tables were dropped) and the picked-unit reader builds of this process (each "
                            "build reads the group's driver files)",
                    "reader_builds": earlier + int(self.reader.builds),
                    "reader_builds_by_object": {
                        "derive_replaced_readers": earlier,
                        "final_readers": int(self.reader.builds),
                        "reading": "derive's R30 measure builds a new set of group readers each time it runs (once per "
                                   "derive pass; two passes when the labels before Y0 are withheld); the final set "
                                   "serves the last derive pass and every pool fill (the nowcast pool, then each "
                                   "forecast lead's)"},
                    "separability_sample_readers": (1 + len(sep.get("groups") or ())) if sep.get("checked") else 0,
                    "passes": list(state.schedule_record["passes"]),
                    "temp_disk_plan": getattr(self, "disk_parts", None)})
        self.status.finish("finished", "verdict %s; ladder %s" % (summary.get("verdict"), out.get("verdicts")))
        mark_run_finished(self.folder, self.fingerprint, summary)
        self.log("finished: %s" % json.dumps(summary, default=str))


def run_pipeline(package_path: Any, run_root: Any, kind: str, machine: Any = None,
                 echo: Callable[[str], None] = print, launch_record: Optional[Mapping[str, Any]] = None) -> Path:
    """Run the whole pipeline (nowcast and forecast ladder); returns the run folder."""
    return Pipeline(package_path, run_root, kind, machine, echo, launch_record).run()


def plan_pipeline(package_path: Any, run_root: Any, machine: Any = None,
                  echo: Callable[[str], None] = print, launch_record: Optional[Mapping[str, Any]] = None) -> Path:
    """derived.json and plan.json of a headline run (its run folder, which 'run' then resumes)."""
    from treeroute.pipeline.record import KIND_HEADLINE

    return Pipeline(package_path, run_root, KIND_HEADLINE, machine, echo, launch_record).plan()


def report_runs(package_path: Any, run_root: Any, machine: Any = None,
                echo: Callable[[str], None] = print) -> Optional[Path]:
    """Print every finished run's verdict and build the headline table from finished headline runs
    (the builder refuses DRAFT, smoke and legacy runs and every run with a not-headline reason).
    Returns the table's path, or None when there is no headline run."""
    from treeroute.package.load import load_dataset_file
    from treeroute.pipeline import record as REC
    from treeroute.runs.atomic import read_json
    from treeroute.runs.machine import load_machine
    from treeroute.runs.registry import Registry

    machine = machine if machine is not None else load_machine()
    root = Registry(machine.registry_dir).assert_writable(Path(run_root))
    name = load_dataset_file(package_path).name
    for kind in (REC.KIND_SMOKE, REC.KIND_HEADLINE):
        for folder in REC.finished_runs(root, name, kind):
            v = read_json(folder / REC.VERDICT_FILE) if (folder / REC.VERDICT_FILE).is_file() else {}
            rec = read_json(folder / REC.RUN_RECORD) if (folder / REC.RUN_RECORD).is_file() else {}
            echo("%s/%s: %s%s | adopted %s | verdict %s | pooled MAE adopted %s vs reference %s"
                 % (kind, folder.name, "DRAFT | " if (rec.get("draft") or {}).get("is_draft") else "",
                    "headline-eligible" if rec.get("headline_eligible") else "not headline-eligible",
                    v.get("adopted"), (v.get("verdict") or {}).get("tag"), v.get("pooled_mae_adopted"),
                    v.get("pooled_mae_reference")))
    headline = REC.finished_runs(root, name, REC.KIND_HEADLINE)
    if not headline:
        echo("no finished headline run of %s: no headline table" % name)
        return None
    table = REC.build_headline_table(headline)
    path = REC.write_headline_table(table, root / name)
    echo("headline table: %s (%d runs)" % (path, len(table)))
    return path


__all__ = ["Pipeline", "PipelineRefusal", "run_pipeline", "plan_pipeline", "report_runs", "LIMITS",
           "DEPARTURES", "build_departures"]
