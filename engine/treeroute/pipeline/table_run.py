"""The table option's pipeline: TablePipeline, the one pipeline of plan 4.1 run on a table package.

Owner ruling U (the owner rulings file, section U, U1-U6); design in SPEC_TABLE_MODE.md 3.1-3.6, 3.10. A table
package (dataset.yaml input: table) supplies ready rows, one table per lead (package/table.py). Each sample row is
the engine's unit: the rows form a keys-only DenseGrid with one step and the row vault (labels/rows.py) holds their
labels, so FitContext, the bank and its checkpoints, the tree-answer store, decide(), the locks, the records and the
metrics run unchanged. TablePipeline subclasses pipeline/run.Pipeline and inherits its heavy-job lock, cleanup, RAM
and disk waits (owner ruling Q1), split view, plan check, temp folder, unit-list hashes, smoke bank plans, plan() and
run(). It replaces the grid-only steps:
  - _load: table_spec in place of package_spec (no target reader, no feature script: U1); feature lineage is
    vouched by the package owner (U2);
  - _groups: the lead-0 file's group column; _preflight_target: the table RAM pre-flight; _read: the contract read
    (package/table.read_tables: T-FILES ... T-FINITE, T-LEADSET); _derive: derive/table.derive_all_table;
  - _vault: the row vault (VaultRows); _preflight_disk: one pool per lead and the banks' tables;
  - _plan_document, _open: the grid records with the table's config, TABLE_LIMITS and TABLE_DEPARTURES (empty since
    owner ruling V4; the accepted ones are recorded as accepted_departures);
  - _compute: the same phases with TableRunState (pipeline/table_passes.py) and TableLadder (pipeline/table_ladder.py).
The grid's LIMITS and DEPARTURES (pipeline/run.py) are not edited: a table run carries its own lists. The streamed and
per_group flags of the base class are GATE ONLY flags on grids; a table run has no census and no per-group batching,
so this subclass sets both off itself (their grid meaning is unchanged). census_step carries the SHA-256 of the
table data manifest, so the inherited bank checkpoints are keyed by every input file's content (owner ruling P1).
"""
# Provenance for the module: SPEC_TABLE_MODE.md 3.1-3.6, 3.10; pipeline/run.py (the grid bodies copied where a line
# reads the census, the static table or grid steps); OWNER_RULINGS_2026-10-06.md U1-U6, Q1, P1.

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Mapping, Optional

import numpy as np

from .run import (GIB, PHASE_DECISION, PHASE_PLAN, PHASE_REPORT, PHASE_TEST, PLAN_CHECK_FILE, Pipeline,
                  PipelineRefusal, _file_list_sha, _sha_json)

INPUT_TABLE = "table"
TABLE_LIMITS = (
    "Type 3 (plan 4.1 step 10) is not built",
    "table features are vouched by the package owner (owner ruling U2): the engine recomputes none of them and "
    "checks only the declared feature-end day (T-FEATEND); the G-DERIVED recompute and the look-ahead canary are "
    "not run on tables",
    "the table option builds the neighbour router kind only (U3); per-unit and region tables are refused (O16)",
    "the scored rows are the package's test marks (U1), not R18 (2)'s stride pick",
    "the continuity row (continuity.csv), nearest-donor distances and distance bands, report.html and part_draft.md "
    "are not built (treeroute_report)",
    "the band is derived from this run's own contrasts; registry/bands.csv and registry/index.csv are not written",
    "'freeze' verdicts are refused: per-cut frozen pools are not built",
    "a time-varying report stratum is reported per row (a string stratum per value, a numeric one by quartiles)",
)
# Owner ruling V4 (OWNER_RULINGS_2026-10-06.md section V, 2026-10-19: "yes to all"): the table departures are
# accepted at the freeze, as ruling S21 accepted the grid departures (pipeline/run.py ACCEPTED_DEPARTURES). Every
# table departure moved to TABLE_ACCEPTED_DEPARTURES (kept as the record the paper discloses, and written into the
# run record); none is a not-headline reason any more.
TABLE_DEPARTURES = ()
TABLE_ACCEPTED_DEPARTURES = (
    ("neighbour_private_kernel", "the neighbour router runs through route.neighbour's private kernels "
                                 "(_route_neighbour_grid / _route_neighbour_at), not the approved route_neighbour_loro"),
    ("neighbour_pool_signature", "neighbour_pool_loro takes the keyword row_issue_day (U4 needs each row's issue day) "
                                 "and route.solve's solvers take the keyword n_unpenalised (the neighbour design's "
                                 "intercept alone is unpenalised); both await an owner signature"),
    ("fold_gls_entry", "the decision surface's per-fold c and GLS weight models are handed out by "
                       "FitContext.donor_rows_outside and fit.weights.weight_models_for_folds (new entries; for_fold "
                       "stays unbuilt)"),
    ("table_absent_rows", "a non-test row absent from a lead file leaves that lead's banks, c, tolerances, donor-row "
                          "median, GLS rows and pools; this departs from the accepted grid reading (ladder_h_readings), "
                          "where such a row stays in the bank with 0-filled features: a table has no feature row at "
                          "that lead to fill. A guard-surface row absent at its lead refuses, as on grids"),
    ("table_readings", "the owner items of SPEC_TABLE_MODE.md section 7 (O1-O27) are built at their listed defaults "
                       "and await the owner"),
)


def table_departures() -> List[str]:
    return ["departure %s: %s" % (key, text) for key, text in TABLE_DEPARTURES]


def table_accepted_departures() -> List[str]:
    """The accepted table departures (owner ruling V4), in the same text form; disclosed, never a reason."""
    return ["departure %s: %s" % (key, text) for key, text in TABLE_ACCEPTED_DEPARTURES]


@dataclass
class VaultRows:
    """The row vault of a table run and the per-position keys the passes read (no step bounds are carried)."""
    grid: Any
    labels: Any
    unit_ids: np.ndarray            # per row position: the row id
    steps: np.ndarray               # per row position: the target day
    window_end: np.ndarray          # per row position: the target day (1-day labels, section 1.5)
    test_first: int                 # the first day of the first test year
    package_units: np.ndarray


class TablePipeline(Pipeline):
    """One run of the pipeline on a table package (module docstring)."""

    def __init__(self, package_path: Any, run_root: Any, kind: str, machine: Any = None,
                 echo: Callable[[str], None] = print, launch_record: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(package_path, run_root, kind, machine, echo, launch_record)
        # the base class's streamed / per_group are GATE ONLY flags on grids (pipeline/run.py: they select the
        # byte-identity gates' paths there); a table run has no census and no per-group batching
        self.streamed = False
        self.per_group = False
        self.input = INPUT_TABLE
        self.table = None
        self.last_value = None

    # ------------------------------------------------------------------ step 1: load
    def _load(self) -> None:
        from treeroute import engine_constants as K
        from treeroute.package.load import load_package
        from treeroute.package.table import table_leads, table_spec
        from treeroute.pipeline.draft import draft_status

        self.package = load_package(self.package_path)
        self.draft = draft_status(self.package)
        self.target_hook = self.feature_hook = None
        self.pkg = self.package
        self.spec = table_spec(self.package)
        self.leads = table_leads()
        self.feature_lineage = {}
        self.log("package %s version %s, fingerprint %s%s (input: table)" % (
            self.package.dataset.name, self.package.dataset.version, self.package.fingerprint[:16],
            (" | DRAFT: %s" % self.draft.stamp) if self.draft.is_draft else ""))
        self.log("feature lineage: vouched by the package owner (U2)")
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
        if K.GUARD_TOLERANCE_K is K.UNSET:
            if self.smoke:
                self.not_headline.append("R36 stand-in tolerance (C9.guard_tolerance_k unset)")
            elif self._planning:
                self.not_headline.append("C9.guard_tolerance_k unset: the headline run refuses until the owner "
                                         "sets k")
            else:
                K.get("C9.guard_tolerance_k")

    def _groups(self) -> None:
        from treeroute import engine_constants as K
        from treeroute import split as SP
        from treeroute.derive.unit_rules import derive_r21_smoke_plan_loro
        from treeroute.package.table import table_groups

        self.split_sets = SP.loro_split_sets(self.pkg.split)
        data_groups = table_groups(self.package, self.spec)
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
        """The table RAM pre-flight (SPEC_TABLE_MODE.md 3.3): rows x columns x 8 bytes over the lead files, before any
        file is read whole (wait=False: plan-time, refuses at once)."""
        from treeroute.package.table import table_ram_bytes

        need, rows = table_ram_bytes(self.package, self.spec, self.leads)
        self._refuse_ram(need, "the table read (%s rows per lead, %d columns)" % (rows, len(self.spec.columns)))
        self.log("preflight: table rows per lead %s, %d columns; RAM estimate %.3f GiB: go"
                 % (rows, len(self.spec.columns), need / GIB))

    def _read(self) -> None:
        from treeroute import engine_constants as K
        from treeroute.derive.shapes import Cadence, CadenceKind
        from treeroute.package.table import read_tables

        t0 = time.time()
        self.table = read_tables(self.package, self.spec, self.leads, tuple(sorted(self.pkg.split.excluded)),
                                 keep_groups=self.run_groups,
                                 smoke_units_per_group=int(K.SMOKE_UNITS_PER_GROUP) if self.smoke else None)
        self.data_manifest = self.table.data_manifest
        self.data_files = [f["path"] for f in self.data_manifest["files"]]
        self.driver_files = []
        self.cadence = Cadence(kind=CadenceKind.IRREGULAR)
        key = hashlib.sha256(json.dumps([[f["path"], f["sha256"]] for f in self.data_manifest["files"]]).encode("utf-8")
                             ).hexdigest()
        # owner ruling P1: the inherited bank checkpoints put this key in theirs (passes.RunState.fit_bank)
        self.census_step = SimpleNamespace(key=key, folder=None)
        self.log("table read: %d rows of %d package units in %d lead files (%s) in %.1f s"
                 % (len(self.table.row_ids), int(self.data_manifest["run_units"]), len(self.data_files),
                    ", ".join("lead %d: %d rows" % (L, int(t.present.sum())) for L, t in sorted(self.table.leads.items())),
                    time.time() - t0))

    def _derive(self) -> None:
        from treeroute.derive.table import derive_all_table

        t0 = time.time()
        derive_pkg, split_view = self._split_view()
        self.derived = derive_all_table(derive_pkg, self.spec, self.table, self.leads)
        if split_view is not None:
            self.derived["R18:split_view"] = split_view
        if self.smoke_plan is not None:
            self.derived["R21:smoke_selection"] = self.smoke_plan
        self.blocks = self.derived["R14:overlap_blocks"].value
        self.strata = {c: np.asarray(self.table.strata[c]) for c in self.spec.strata}
        self.log("derive_all_table: %d entries in %.1f s; router %s; overlap blocks %d for %d groups; leads %s days"
                 % (len(self.derived), time.time() - t0, getattr(self.derived["R12"].value, "value", ""),
                    len(self.blocks.members), len(self.blocks.block_of_group), list(self.leads[1:])))

    def _vault(self, run_folder: Optional[Path]) -> VaultRows:
        import datetime as _dt

        from treeroute.labels.rows import build_row_vault

        w = self.derived["R7"].value
        test_first = _dt.date(int(min(w.test_years)), 1, 1).toordinal()
        labels = build_row_vault(self.table, test_first, run_folder)
        days = np.asarray(self.table.target_day, dtype=np.int64)
        return VaultRows(grid=self.table.grid, labels=labels, unit_ids=np.asarray(self.table.row_ids, dtype=object),
                         steps=days, window_end=days.copy(), test_first=int(test_first),
                         package_units=np.asarray(self.table.units, dtype=object))

    # ------------------------------------------------------------------ disk (Q1)
    def disk_plan(self) -> Dict[str, Any]:
        """Temp disk at the peak (go/refuse only): one pool per lead (rows x (tree + context) columns x 4 bytes) beside
        the nowcast's, and per live bank its tables of every row (rows x bank trees x 4 bytes x 3 kinds), two banks at
        a time."""
        rows = len(self.table.row_ids)
        cols = len(self.spec.tree_features) + len(self.spec.context)
        trees = len(self.run_groups) * int(self.trees_per_group)
        pool = rows * cols * 4
        tables = rows * trees * 4 * 3
        total = 2 * pool + 2 * tables
        return {"total": int(total), "pool": int(pool), "tables_one_bank": int(tables), "rows": int(rows),
                "trees": int(trees)}

    def _preflight_disk(self) -> None:
        from treeroute.errors import PreflightRefusal
        from treeroute.runs import preflight
        from treeroute.runs.room import wait_for_room

        parts = self.disk_plan()
        self.disk_parts = parts
        try:
            wait_for_room(lambda: preflight.check_resources(self.temp_dir, parts["total"], 0),
                          "the table run's temp disk", self.log)
        except PreflightRefusal as exc:
            raise PipelineRefusal("G-DISK", "the table run's temp disk at its peak (%.3f GiB) does not fit: %s"
                                  % (parts["total"] / GIB, exc),
                                  fix="free disk on the temp drive; the run size is never reduced") from exc
        self.log("preflight: temp disk for the table run %.3f GiB at its peak (two pools, two banks' tables): go"
                 % (parts["total"] / GIB))

    # ------------------------------------------------------------------ records
    def _ladder_phases(self) -> List[str]:
        from treeroute.pipeline.table_ladder import table_phase_names

        return table_phase_names(self.derived)

    def _plan_document(self) -> Dict[str, Any]:
        from treeroute.package.table import U2_VOUCHED
        from treeroute.pipeline.table_passes import donor_only_record

        w = self.derived["R7"].value
        lists = self.derived["R18:units"].value
        return {"kind": self.kind, "package": self.package.dataset.name, "input": INPUT_TABLE,
                "draft": self.draft.record(), "not_headline_reasons": list(self.not_headline),
                "limits": list(TABLE_LIMITS), "u2_vouched": list(U2_VOUCHED),
                "router_kind": getattr(self.derived["R12"].value, "value", self.derived["R12"].value),
                "links": [l.value for l in self.derived["R22"].value],
                "windows": {"y0": w.y0, "y_end": w.y_end, "test_years": list(w.test_years),
                            "train_end": w.train_end, "inner_fit": list(w.inner_fit),
                            "inner_score": list(w.inner_score)},
                "groups": len(lists.bank), "bank_rows": {g: len(v) for g, v in lists.bank.items()},
                "scored_rows": {g: len(v) for g, v in lists.scored.items()},
                "donor_only_groups": list(donor_only_record(self.derived)["groups"]),
                "trees_per_group": self.trees_per_group,
                "overlap_blocks": [list(b) for b in self.blocks.members if len(b) > 1],
                "tree_features": len(self.spec.tree_features), "context": list(self.spec.context),
                "listed_in_reports": list(self.spec.listed_in_reports), "strata": list(self.spec.strata),
                "feature_lineage": {}, "feature_lineage_note": "vouched by the package owner (U2)",
                "max_feature_end_minus_issue_day": {str(L): t.max_feature_end_gap
                                                    for L, t in sorted(self.table.leads.items())},
                "leads": list(self.derived["R10"].value.leads), "lead_unit": "days",
                "phases": [PHASE_PLAN, PHASE_DECISION, PHASE_TEST, PHASE_REPORT] + self._ladder_phases()}

    def _open(self) -> None:
        from treeroute import engine_constants as K
        from treeroute.derive import derived_sha256
        from treeroute.package.table import U2_VOUCHED
        from treeroute.pipeline import record as REC
        from treeroute.pipeline.table_passes import DONOR_ONLY_KEY, donor_only_record
        from treeroute.runs.fingerprint import run_fingerprint
        from treeroute.runs.resume import Phases, open_run
        from treeroute.runs.status import StatusWriter

        self.derived_sha = derived_sha256(self.derived)
        self.not_headline = list(self.not_headline) + table_departures()
        self.config = {"kind": self.kind, "package": self.package.dataset.name,
                       "package_fingerprint": self.package.fingerprint, "derived_sha256": self.derived_sha,
                       "draft": self.draft.record(), "groups": list(self.run_groups),
                       "trees_per_group": self.trees_per_group, "input": INPUT_TABLE,
                       "data": self.data_manifest, "target_files_sha256": _file_list_sha(self.data_files),
                       "static_files_sha256": _file_list_sha([]), "driver_files_sha256": _file_list_sha([]),
                       "engine_constants_sha256": K.constants_hash(),
                       "feature_list": list(self.spec.tree_features), "context_list": list(self.spec.context),
                       "strata": list(self.spec.strata)}
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
        rec = REC.run_record(self.kind, self.package, self.fingerprint, self.draft, self.not_headline, TABLE_LIMITS,
                             {"derived_sha256": self.derived_sha, "groups": list(self.run_groups), "input": INPUT_TABLE,
                              "departures": table_departures(),
                              "accepted_departures": table_accepted_departures(), "u2_vouched": list(U2_VOUCHED),
                              "listed_in_reports": list(self.spec.listed_in_reports),
                              "strata": list(self.spec.strata), "feature_lineage": {},
                              "max_feature_end_minus_issue_day": {str(L): t.max_feature_end_gap
                                                                  for L, t in sorted(self.table.leads.items())},
                              "table_rows": int(len(self.table.row_ids)),
                              DONOR_ONLY_KEY: {k: v for k, v in donor_only_record(self.derived).items()
                                               if k in ("groups", "count", "train_rows")}})
        held = self.folder / REC.RUN_RECORD
        if held.is_file():
            prior = json.loads(held.read_text(encoding="utf-8")).get(REC.SCORE_CONTEXT_KEY)
            if prior is not None:
                rec[REC.SCORE_CONTEXT_KEY] = prior
        REC.write_once_or_same(held, rec)
        derived_path = self.folder / REC.DERIVED_FILE
        if derived_path.exists():
            from treeroute.derive import derived_document
            from treeroute.runs.atomic import dumps

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
                self.log("plan check (resumed run): %s" % json.dumps(self.plan_check, default=str))
            else:
                REC.write_once_or_same(path, self.plan_check)
        manifest_path = self.folder / "manifest.json"
        if not manifest_path.exists():
            from treeroute.runs.machine import machine_record
            from treeroute.runs.manifest import build_manifest, write_manifest

            write_manifest(self.folder, build_manifest(
                self.fingerprint, self.package.fingerprint, machine_record(self.machine), config=self.config,
                launch_record=self.launch_record, feature_list=self.config["feature_list"],
                unit_list_hashes=self._unit_list_hashes(),
                table_schedule={"kinds": ["plain", "corrector", "placebo_corrector"],
                                "built": "per neighbour pass: every candidate and scored row of the pass, one table "
                                         "kind's dense answer matrix at a time (owner item O20)"}))
        if not self.phases.done(PHASE_PLAN):
            self.phases.mark_done(PHASE_PLAN, {"derived_sha256": self.derived_sha})

    # ------------------------------------------------------------------ steps 3-12
    def _compute(self) -> None:
        from treeroute.pipeline import table_ladder as TL
        from treeroute.pipeline.table_passes import TableRunState
        from treeroute.runs.atomic import read_json
        from treeroute.runs.resume import PHASE_DONE, PHASES_DIR, mark_run_finished

        done_decision = self.phases.done(PHASE_DECISION) or (self.folder / "adoption.json.lock.json").exists()
        done_test = self.phases.done(PHASE_TEST)
        done_report = self.phases.done(PHASE_REPORT)
        ladder_phases = TL.table_phase_names(self.derived)
        done_ladder = all(self.phases.done(ph) for ph in ladder_phases)
        if done_report and done_ladder:
            mark_run_finished(self.folder, self.fingerprint, {"resumed": True})
            self._remove_checkpoints()
            return
        with TableRunState(self) as state:
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
            ladder = TL.TableLadder(state)
            out = ladder.run(self.phases)
            if not out:
                out = dict(read_json(self.folder / PHASES_DIR / TL.PHASE_TABLE / PHASE_DONE).get("summary") or {})
            summary = dict(summary, ladder=out)
            state.write_fitctx_log(ladder_phases)
        self.status.finish("finished", "verdict %s; ladder %s" % (summary.get("verdict"), out.get("verdicts")))
        mark_run_finished(self.folder, self.fingerprint, summary)
        self.log("finished: %s" % json.dumps(summary, default=str))
        self._remove_checkpoints()


__all__ = ["TablePipeline", "TABLE_LIMITS", "TABLE_DEPARTURES", "TABLE_ACCEPTED_DEPARTURES",
           "table_departures", "table_accepted_departures", "VaultRows", "INPUT_TABLE"]
