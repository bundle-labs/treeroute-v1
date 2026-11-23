"""The CHECK REPORT CONTRACT (between the check command and treeroute_report). Boilerplate.

'py -3.9 -m treeroute check <package> [--deep]' writes
    <run_root>/<package name>/check/check_<quick|deep>_<package fingerprint, 12 hex>.json
A quick report has exactly the keys {package, package_fingerprint, engine_code_sha256, mode, green, guards,
started, finished} (CONTRACT_KEYS); a deep report has exactly those keys plus 'checked_groups' (DEEP_CONTRACT_KEYS).
guards is a list of {id, status, message, columns} with status pass | flag | refuse. green is True only when no
guard refuses (a flag is report only). engine_code_sha256 is runs.fingerprint.engine_code_sha256.
Each guard's details (full column lists, counts) go into a sidecar beside it,
check_<mode>_<fingerprint 12 hex>_details.json, so the contract's keys stay exactly as agreed. Both files are
replaced atomically when the same package fingerprint is checked again.

checked_groups (owner ruling M2: the freeze gate's 'check --deep' runs on each
package's R21 smoke groups, plus the quick checks on the whole package, and the deep report names the groups it
checked): {groups, selection, rule, constants, package_groups, data_groups, refused} (GROUPS_RECORD_KEYS), written
into the report and into its details sidecar. The command always checks the ruling-M2 subset: 'groups' is R21's
smoke plan over the package's groups (derive.unit_rules.derive_r21_smoke_plan_loro, the engine's own smoke rule:
the first C13.smoke_groups groups in sorted order, every group when there are fewer), 'selection' is M2_SELECTION,
'package_groups' counts the groups after split.yaml's exclusions (the list R21 picks from) and 'data_groups' the
groups the target store lists. A caller-given subset (tests and gates only, run_deep's 'groups') is recorded with
CALLER_SELECTION; when R21 refuses, 'groups' is empty and 'refused' holds the reason (the report is red then).
package_smoke_groups is the one function that lists a package's ruling-M2 groups: the freeze recomputes them with it
and accepts a deep report only on exactly those groups.
"""

import datetime as _dt
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from treeroute.layer.decide import GuardStatus

STATUS_WORDS = {GuardStatus.PASS: "pass", GuardStatus.FLAG: "flag", GuardStatus.BLOCK: "refuse"}
CONTRACT_KEYS = ("package", "package_fingerprint", "engine_code_sha256", "mode", "green", "guards", "started",
                 "finished")
GROUPS_KEY = "checked_groups"
DEEP_CONTRACT_KEYS = CONTRACT_KEYS + (GROUPS_KEY,)
GUARD_KEYS = ("id", "status", "message", "columns")
GROUPS_RECORD_KEYS = ("groups", "selection", "rule", "constants", "package_groups", "data_groups", "refused")
FINGERPRINT_HEX = 12
# Ruling M2: how the deep pass's groups were chosen (the text the freeze reads back).
M2_RULE = "R21"
M2_SELECTION = "R21 smoke groups, ruling M2"
CALLER_SELECTION = "groups given by the caller (tests and gates only; not the ruling-M2 subset)"
# The engine constants R21's group choice reads (recorded with their values in checked_groups.constants).
M2_CONSTANTS = ("C13.smoke_groups", "C15.min_groups")


def now_text() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def contract_keys(mode: str) -> Tuple[str, ...]:
    """The exact top-level keys of a report of this mode."""
    if mode not in ("quick", "deep"):
        raise ValueError("mode is quick or deep, got %r" % (mode,))
    return DEEP_CONTRACT_KEYS if mode == "deep" else CONTRACT_KEYS


# ============================================================================== ruling M2: the deep groups
def smoke_group_selection(groups: Sequence[str], data_groups: Sequence[str]) -> Dict[str, Any]:
    """Ruling M2's checked_groups record: R21's smoke groups of ``groups`` (the package's groups after split.yaml's
    exclusions) by the engine's own smoke rule (derive_r21_smoke_plan_loro), never a new number. ``data_groups``
    (the groups the target store lists) is only counted. Raises R21's refusal (DeriveRefusal: fewer than
    C15.min_groups groups, or names that are not distinct)."""
    from treeroute.derive.unit_rules import derive_r21_smoke_plan_loro

    plan = derive_r21_smoke_plan_loro(tuple(groups))
    used = dict(plan.inputs.get("constants") or {})
    return {"groups": [str(g) for g in plan.value["groups"]], "selection": M2_SELECTION, "rule": plan.rule_id,
            "constants": {cid: used[cid] for cid in M2_CONSTANTS if cid in used},
            "package_groups": len(tuple(groups)), "data_groups": len(tuple(data_groups)), "refused": None}


def refused_selection(groups: Sequence[str], data_groups: Sequence[str], reason: str) -> Dict[str, Any]:
    """The checked_groups record when the ruling-M2 groups cannot be chosen: no group checked, the reason kept."""
    return {"groups": [], "selection": M2_SELECTION, "rule": M2_RULE, "constants": {},
            "package_groups": len(tuple(groups)), "data_groups": len(tuple(data_groups)), "refused": str(reason)}


def caller_selection(chosen: Sequence[str], groups: Sequence[str], data_groups: Sequence[str]) -> Dict[str, Any]:
    """The checked_groups record of a caller-given subset (tests and gates only): never the ruling-M2 subset by
    construction, so the freeze compares its groups with R21's and refuses any other subset."""
    return {"groups": sorted(str(g) for g in chosen), "selection": CALLER_SELECTION, "rule": None, "constants": {},
            "package_groups": len(tuple(groups)), "data_groups": len(tuple(data_groups)), "refused": None}


def package_smoke_groups(loaded: Any) -> Dict[str, Any]:
    """Ruling M2's groups of a loaded package, listed as the smoke command lists them (pipeline.run: the target
    store's {group} values minus split.yaml's exclusions, split.groups_under_loro), then smoke_group_selection.
    The freeze recomputes with this function the groups a deep report must have checked. Raises RefusedError: the
    target store holds no file, its template has no {group} placeholder, split.yaml excludes a group the data does
    not hold, or R21 refuses."""
    from treeroute import split as SP
    from treeroute.pipeline import data as D

    if getattr(loaded.dataset, "input", "grid") == "table":
        # owner ruling U1 (SPEC_TABLE_MODE.md 3.1): a table package lists its groups from the lead-0 file's group column
        from treeroute.package import table as T

        data_groups = T.table_groups(loaded, T.table_spec(loaded))
        groups = SP.groups_under_loro(SP.loro_split_sets(loaded.split), tuple(data_groups))
        return smoke_group_selection(groups, data_groups)
    listing = D.list_target(loaded)
    data_groups = D.listed_groups(listing)
    if data_groups is None:
        raise D.DataRefusal(M2_RULE, "the target store template %s has no {group} placeholder, so the R21 smoke "
                            "groups cannot be listed" % (listing.path_template,),
                            fix="use a {group} placeholder in dataset.yaml stores.target")
    groups = SP.groups_under_loro(SP.loro_split_sets(loaded.split), tuple(data_groups))
    return smoke_group_selection(groups, data_groups)


def check_selection_record(record: Any) -> Dict[str, Any]:
    """A checked_groups record with exactly GROUPS_RECORD_KEYS and a sorted list of distinct group names; raises
    ValueError otherwise (a deep report never goes out without its groups)."""
    if not isinstance(record, dict) or set(record) != set(GROUPS_RECORD_KEYS):
        raise ValueError("a deep report needs checked_groups with exactly the keys %s, got %r"
                         % (list(GROUPS_RECORD_KEYS), sorted(record) if isinstance(record, dict) else record))
    names = record["groups"]
    if not isinstance(names, list) or any(not isinstance(g, str) or not g for g in names) \
            or names != sorted(set(names)):
        raise ValueError("checked_groups.groups must be a sorted list of distinct group names, got %r" % (names,))
    return record


def selection_text(record: Dict[str, Any]) -> str:
    """One line naming the deep pass's groups and how they were chosen (the printed header and the guard line)."""
    names = ", ".join(record["groups"]) or "none"
    counts = "of the package's %d groups after split.yaml's exclusions (%d in the target store)" % (
        record["package_groups"], record["data_groups"])
    if record["refused"]:
        return "the ruling-M2 subset (%s) cannot be chosen, %s: %s" % (record["selection"], counts, record["refused"])
    if record["selection"] == M2_SELECTION:
        n = record["constants"].get("C13.smoke_groups")
        return ("ruling-M2 subset (%s; the first %s groups in sorted order, C13.smoke_groups): %d %s: %s"
                % (record["selection"], n, len(record["groups"]), counts, names))
    return "%s: %d %s: %s" % (record["selection"], len(record["groups"]), counts, names)


def message_of(res: Any) -> str:
    """'[rule] reason Columns: ... Fix: ... (Part n)': a rule id, the columns, the fix and a Part number."""
    text = "[%s] %s" % (res.rule_id, res.reason)
    if res.columns:
        cols = list(res.columns)
        text += " Columns: %s%s." % (", ".join(cols[:20]), " ... (%d in all)" % len(cols) if len(cols) > 20 else "")
    if res.fix and res.status is not GuardStatus.PASS:
        text += " Fix: %s." % res.fix.rstrip(".")
    if res.part is not None:
        text += " (Part %d)" % int(res.part)
    return text


def guard_rows(results: Sequence[Tuple[str, Any]]) -> List[Dict[str, Any]]:
    return [{"id": label, "status": STATUS_WORDS[res.status], "message": message_of(res),
             "columns": list(res.columns)} for label, res in results]


def is_green(results: Sequence[Tuple[str, Any]]) -> bool:
    return all(res.status is not GuardStatus.BLOCK for _, res in results)


def report_path(run_root: Any, package_name: str, mode: str, fingerprint: str) -> Path:
    return Path(run_root) / package_name / "check" / ("check_%s_%s.json" % (mode, fingerprint[:FINGERPRINT_HEX]))


def write_report(run_root: Any, loaded: Any, mode: str, results: Sequence[Tuple[str, Any]], started: str,
                 finished: str, checked_groups: Optional[Dict[str, Any]] = None) -> Path:
    """Write the contract file and its details sidecar; returns the contract file's path. A deep report needs
    checked_groups (ruling M2; check_selection_record), a quick report takes none."""
    from treeroute.runs.atomic import replace_json, to_jsonable
    from treeroute.runs.fingerprint import engine_code_sha256

    keys = contract_keys(mode)
    if mode == "deep":
        check_selection_record(checked_groups)
    elif checked_groups is not None:
        raise ValueError("a quick report checks the whole package's facts and takes no checked_groups")
    path = report_path(run_root, loaded.dataset.name, mode, loaded.fingerprint)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"package": loaded.dataset.name, "package_fingerprint": loaded.fingerprint,
           "engine_code_sha256": engine_code_sha256(), "mode": mode, "green": is_green(results),
           "guards": guard_rows(results), "started": started, "finished": finished}
    details = {"package": loaded.dataset.name, "package_fingerprint": loaded.fingerprint, "mode": mode,
               "guards": [{"id": label, "rule": res.rule_id, "part": res.part, "fix": res.fix,
                           "details": _plain(res.details)} for label, res in results]}
    if mode == "deep":
        doc[GROUPS_KEY] = _plain(checked_groups)
        details[GROUPS_KEY] = _plain(checked_groups)
    if set(doc) != set(keys):
        raise ValueError("the %s report's keys %s differ from the contract's %s" % (mode, sorted(doc), list(keys)))
    replace_json(path, doc)
    replace_json(path.with_name(path.stem + "_details.json"), to_jsonable(_plain(details)))
    return path


def _plain(obj: Any) -> Any:
    """JSON-safe copy: sets become sorted lists, tuples lists, numpy scalars Python numbers, non-finite floats
    text (strict JSON)."""
    import math

    import numpy as np

    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (set, frozenset)):
        return [_plain(v) for v in sorted(obj, key=repr)]
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    if isinstance(obj, np.generic):
        obj = obj.item()
    if isinstance(obj, float) and not math.isfinite(obj):
        return repr(obj)
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


__all__ = ["write_report", "report_path", "guard_rows", "is_green", "message_of", "now_text", "CONTRACT_KEYS",
           "DEEP_CONTRACT_KEYS", "GROUPS_KEY", "GROUPS_RECORD_KEYS", "GUARD_KEYS", "STATUS_WORDS", "M2_SELECTION",
           "CALLER_SELECTION", "contract_keys", "smoke_group_selection", "refused_selection", "caller_selection",
           "package_smoke_groups", "check_selection_record", "selection_text"]
