"""Run records, the run log and the headline-table builder (plan 7.1; boilerplate).

run_record.json (written once when a run folder is opened) says what the run is and whether it may ever
enter a headline table: its kind, the package and its fingerprint, the DRAFT stamp (pipeline.draft), the
reasons it is not headline-eligible (the build's departures from the approved design among them), and the
build's known limits. The headline-table builder reads it and refuses:
  - a run of a DRAFT package (G-DRAFT): its verdicts are not the owner's review;
  - a smoke run (plumbing only) and a run stamped legacy (G-LEGACY);
  - a run with any not-headline reason (a stand-in constant, or a departure the owner has not ruled);
  - an unfinished run;
  - a run whose saved rows do not score exactly the derived scored units (G-SPLIT, outputs); a unit the run's
    nowcast test pass left with no scored row under owner ruling S1 (run_record.json SCORE_CONTEXT_KEY, its
    units_unscored) is not expected in the saved rows, and the record discloses it.
Owner ruling S1 adds ONE key to run_record.json after the folder is opened, and only when a pass leaves a scored row
out (add_pass_record: the per-pass counts per unit); a resumed run keeps that key (pipeline.run).
"""

import datetime
import hashlib
import io
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from treeroute.errors import RefusedError
from treeroute.runs.atomic import dumps, read_json, replace_json, write_json_once, write_text_once

RUN_RECORD = "run_record.json"
RUN_LOG = "run.log"
VERDICT_FILE = "verdict.json"
TEST_PREDS = "test_preds.parquet"
INNER_PREDS = "inner_preds.parquet"
INNER_CANDIDATES = "inner_candidates.csv"
DERIVED_FILE = "derived.json"
PLAN_FILE = "plan.json"
KIND_HEADLINE = "headline"
KIND_SMOKE = "smoke"
KIND_LEGACY = "legacy"
SCORE_CONTEXT_KEY = "score_context_left_out"   # owner ruling S1: run_record.json's per-pass counts (only when > 0)
S1_TEST_PASS = "test pass"                     # the nowcast test pass's name (its unscored units leave G-SPLIT)


class TableRefusal(RefusedError):
    """The headline-table builder refused a run (G-DRAFT, G-LEGACY, G-SPLIT)."""


class RunLog(object):
    """Echo lines to the console and append them to the run folder's run.log (once a folder exists)."""

    def __init__(self, echo=print):
        self._echo = echo
        self._path: Optional[Path] = None
        self._buffer: List[str] = []

    def attach(self, folder: Any) -> None:
        self._path = Path(folder) / RUN_LOG
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write("".join(line + "\n" for line in self._buffer))
        self._buffer = []

    def __call__(self, line: str) -> None:
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        text = "[%s] %s" % (stamp, line)
        self._echo(text)
        self._keep(text)

    def file_only(self, line: str) -> None:
        """A line for run.log only (already on the console)."""
        self._keep("[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), line))

    def _keep(self, text: str) -> None:
        if self._path is None:
            self._buffer.append(text)
        else:
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(text + "\n")


def write_once_or_same(path: Any, obj: Any) -> None:
    """Write a JSON record once; on a resumed run an existing record must be identical."""
    path = Path(path)
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != json.loads(dumps(obj)):
            raise RefusedError("G-FINGERPRINT", "%s exists with other content; a resumed run never changes a "
                               "record" % path, fix="start a new run")
        return
    write_json_once(path, obj)


def write_text_once_or_same(path: Any, text: str) -> None:
    path = Path(path)
    if path.exists():
        if path.read_bytes() != text.encode("utf-8"):
            raise RefusedError("G-FINGERPRINT", "%s exists with other content" % path, fix="start a new run")
        return
    write_text_once(path, text)


def add_pass_record(folder: Any, what: str, summary: Mapping[str, Any], rule: str) -> None:
    """Owner ruling S1: one pass's left-out scored rows (counts per unit, the unscored units, the rows file) under
    run_record.json's SCORE_CONTEXT_KEY, by pass name. A resumed pass that records the same summary changes
    nothing; a different summary for a pass already recorded refuses (a resumed pass never changes a record)."""
    path = Path(folder) / RUN_RECORD
    doc = read_json(path)
    want = json.loads(dumps(dict(summary)))
    block = doc.get(SCORE_CONTEXT_KEY) or {"rule": rule, "by_pass": {}}
    held = block["by_pass"].get(what)
    if held is not None:
        if held != want:
            raise RefusedError("G-FINGERPRINT", "%s: the S1 record of pass %r exists with other content; a resumed "
                               "run never changes a record" % (path, what), fix="start a new run")
        return
    block["by_pass"][what] = want
    doc[SCORE_CONTEXT_KEY] = block
    replace_json(path, doc)


def csv_text(table: Any) -> str:
    """A table as CSV text with LF line ends on every platform (byte-stable records)."""
    return table.to_csv(index=False, lineterminator="\n")


def run_record(kind: str, package: Any, fingerprint: str, draft: Any, not_headline: Sequence[str],
               limits: Sequence[str], extra: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    rec = {"kind": kind, "package": package.dataset.name, "package_version": package.dataset.version,
           "package_fingerprint": package.fingerprint, "run_fingerprint": fingerprint,
           "draft": draft.record(), "headline_eligible": kind == KIND_HEADLINE and not draft.is_draft
           and not not_headline, "not_headline_reasons": list(not_headline), "limits": list(limits)}
    if draft.is_draft:
        rec["DRAFT"] = "DRAFT: %s -- this run can never enter a headline table" % (draft.stamp or "draft package")
    rec.update(dict(extra or {}))
    return rec


# ---------------------------------------------------------------------------------------------------
# The headline-table builder
def _refuse_run(folder: Path, rule: str, why: str) -> None:
    raise TableRefusal(rule, "run %s: %s" % (folder, why),
                       fix="build the headline table from finished headline runs of signed packages only")


def check_headline_run(folder: Any) -> Dict[str, Any]:
    """The checks the table builder runs on one run folder; returns its run record and verdict."""
    folder = Path(folder)
    rec_path = folder / RUN_RECORD
    if not rec_path.is_file():
        _refuse_run(folder, "G-LEGACY", "no %s: not a pipeline run" % RUN_RECORD)
    rec = read_json(rec_path)
    draft = rec.get("draft") or {}
    if draft.get("is_draft") or rec.get("DRAFT"):
        _refuse_run(folder, "G-DRAFT", "a DRAFT run (%s); a draft package never enters a headline table"
                    % (draft.get("stamp") or "draft package"))
    if rec.get("kind") == KIND_LEGACY or rec.get("legacy"):
        _refuse_run(folder, "G-LEGACY", "a legacy (harness) run")
    if rec.get("kind") != KIND_HEADLINE:
        _refuse_run(folder, "G-LEGACY", "a %s run, not a headline run" % rec.get("kind"))
    if rec.get("not_headline_reasons"):
        _refuse_run(folder, "plan 7.1", "not headline-eligible: %s" % "; ".join(rec["not_headline_reasons"]))
    if not rec.get("headline_eligible"):
        _refuse_run(folder, "plan 7.1", "the run record does not mark it headline-eligible")
    if not (folder / "DONE.json").is_file():
        _refuse_run(folder, "G-LEGACY", "the run has not finished")
    verdict = read_json(folder / VERDICT_FILE)
    return {"record": rec, "verdict": verdict}


def s1_unscored_units(folder: Any) -> Tuple[str, ...]:
    """Owner ruling S1: the units the run's nowcast test pass left with no scored row (run_record.json
    SCORE_CONTEXT_KEY, pass S1_TEST_PASS); () when none."""
    path = Path(folder) / RUN_RECORD
    if not path.is_file():
        return ()
    by_pass = (read_json(path).get(SCORE_CONTEXT_KEY) or {}).get("by_pass") or {}
    return tuple(sorted(str(u) for u in ((by_pass.get(S1_TEST_PASS) or {}).get("units_unscored") or ())))


def check_scored_units(folder: Any) -> Tuple[str, ...]:
    """G-SPLIT on the outputs: the saved rows score exactly each group's derived scored units, less the units the
    nowcast test pass left with no scored row under owner ruling S1 (s1_unscored_units; a group whose every scored
    unit is among them is not expected either). Returns those units (disclosed by the callers)."""
    import pandas as pd

    from treeroute import split as SP

    folder = Path(folder)
    derived = read_json(folder / DERIVED_FILE)
    lists = derived["R18:units"]["value"]
    gone = set(s1_unscored_units(folder))
    scored = {g: tuple(u for u in v if u not in gone) for g, v in lists["scored"].items()}
    dropped = {g for g in lists["scored"] if lists["scored"][g] and not scored[g]}    # every unit unscored by S1
    unit_lists = SP.UnitLists(bank={g: tuple(v) for g, v in lists["bank"].items() if g not in dropped},
                              scored={g: scored[g] for g in lists["scored"] if g not in dropped})
    rows = pd.read_parquet(folder / TEST_PREDS, columns=["unit", "group"])
    got = {g: tuple(sorted(set(sub["unit"].tolist()))) for g, sub in rows.groupby("group")}
    SP.check_scored_units_loro(got, unit_lists)
    return tuple(sorted(gone))


def build_headline_table(folders: Iterable[Any]):
    """The headline table from finished, headline-eligible runs only (one line per run). Refuses the
    whole table if any run is refused: a DRAFT, smoke or legacy run never enters it."""
    import pandas as pd

    lines = []
    for folder in folders:
        checked = check_headline_run(folder)
        check_scored_units(folder)
        rec, v = checked["record"], checked["verdict"]
        lines.append({"package": rec["package"], "package_fingerprint": rec["package_fingerprint"],
                      "run_fingerprint": rec["run_fingerprint"], "adopted": v.get("adopted"),
                      "declined": v.get("declined"), "verdict": (v.get("verdict") or {}).get("tag"),
                      "pooled_mae_adopted": v.get("pooled_mae_adopted"),
                      "pooled_mae_reference": v.get("pooled_mae_reference"),
                      "band": v.get("band"), "n_groups": v.get("n_groups"), "run_folder": str(folder)})
    if not lines:
        raise TableRefusal("G-LEGACY", "no finished headline run to tabulate")
    return pd.DataFrame(lines)


def write_headline_table(table: Any, out_dir: Any) -> Path:
    """Write the table once under a name keyed by its content (an identical table is kept, not
    rewritten)."""
    text = csv_text(table)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    path = Path(out_dir) / ("headline_table_%s.csv" % sha)
    write_text_once_or_same(path, text)
    return path


def finished_runs(run_root: Any, package_name: str, kind: str) -> List[Path]:
    kind_dir = Path(run_root) / package_name / kind
    if not kind_dir.is_dir():
        return []
    return sorted(p for p in kind_dir.iterdir() if p.is_dir() and (p / "DONE.json").is_file())


__all__ = ["RUN_RECORD", "RUN_LOG", "VERDICT_FILE", "TEST_PREDS", "INNER_PREDS", "INNER_CANDIDATES",
           "DERIVED_FILE", "PLAN_FILE", "KIND_HEADLINE", "KIND_SMOKE", "TableRefusal", "RunLog",
           "write_once_or_same", "write_text_once_or_same", "csv_text", "run_record", "check_headline_run",
           "SCORE_CONTEXT_KEY", "S1_TEST_PASS", "add_pass_record", "s1_unscored_units",
           "check_scored_units", "build_headline_table", "write_headline_table", "finished_runs"]
