"""treeroute_report.freeze: the freeze lock (plan 8.0, 8.1 M5) and 'verify'.

Every test builds its own world under tmp_path: a scratch registry (never the real one), a scratch run root, a
synthetic package with its store files (6 groups in the target store, grp_z excluded by split.yaml, so 5 groups
and R21's first 4 of them as the ruling-M2 smoke groups), a synthetic deep check report that follows the CHECK
REPORT CONTRACT and a small pre-registration draft. One test per refused precondition; one all-green test writes
and checks a lock; verify finds no drift right after it and names each planted drift.
"""

import json
import os
from pathlib import Path

import pytest

from conftest import make_package, make_registry
from treeroute import engine_constants as K
from treeroute.package.load import load_package
from treeroute_report import common as C
from treeroute_report import freeze as F

ENGINE_SHA = "ab" * 32
DRAFT = """# Pre-registration (test)
lock {{LOCK_SHA256}} at {{LOCK_FILE}}; engine {{ENGINE_CODE_SHA256}}; constants {{ENGINE_CONSTANTS_SHA256}}
tooling {{REPORT_TOOLING_SHA256}}; awaiting: {{CONSTANTS_AWAITING_OWNER}}
toy: {{PACKAGE_FINGERPRINT:toy_pkg}} check {{CHECK_REPORT_SHA256:toy_pkg}}
derived {{DERIVED_SHA256:toy_pkg}}
settings:
{{DERIVED_SETTINGS:toy_pkg}}
other: {{PACKAGE_FINGERPRINT:other_pkg}}
"""
GREEN_BAN = """verdicts:
  x1: {verdict: keep, reason: reviewed, evidence: Part 1}
  g1: {verdict: keep, reason: reviewed, evidence: Part 2}
"""
NOW = "2026-10-10T12:00:00+00:00"
_REAL_CONSTANTS = C.constants_with_origins
# the world's target store: grp_z is excluded by conftest's split.yaml, so 5 groups remain (ruling M2: R21 checks the
# first C13.smoke_groups of them in sorted order)
DATA_GROUPS = ("grp_a", "grp_b", "grp_c", "grp_d", "grp_e", "grp_z")
PACKAGE_GROUPS = DATA_GROUPS[:-1]
SMOKE_GROUPS = list(PACKAGE_GROUPS[:int(K.SMOKE_GROUPS)])
YEARS = (2020, 2021)


def m2_record(**over):
    """The checked_groups record a ruling-M2 deep report of the world's package carries."""
    rec = {"groups": list(SMOKE_GROUPS), "selection": "R21 smoke groups, ruling M2", "rule": "R21",
           "constants": {"C13.smoke_groups": K.SMOKE_GROUPS, "C15.min_groups": K.MIN_GROUPS},
           "package_groups": len(PACKAGE_GROUPS), "data_groups": len(DATA_GROUPS), "refused": None}
    rec.update(over)
    return rec


def _moment(text=NOW):
    import datetime

    return datetime.datetime.fromisoformat(text)


def _engine_sha():
    return ENGINE_SHA


def _fixed_constants():
    """The real constants with origins; any unset one gets a test value, so the all-green world does not
    depend on the live engine's open constants (the refusal is tested on its own)."""
    rows = _REAL_CONSTANTS()
    return [dict(r, value=1.0, status="cited") if r["status"] == "unset" else r for r in rows]


def _pins():
    return {"source": "test", "source_sha256": "0" * 64, "pins": {"x": "1"}, "installed": {"x": "1"}}


def write_check(run_root, pkg_root, **over):
    pkg = load_package(pkg_root)
    report = {"package": pkg.dataset.name, "package_fingerprint": pkg.fingerprint, "engine_code_sha256": ENGINE_SHA,
              "mode": "deep", "green": True,
              "guards": [{"id": "G-FACTS", "status": "pass", "message": "every kept fact signed", "columns": []},
                         {"id": "G-LAG", "status": "pass", "message": "ok", "columns": []},
                         {"id": "G-MISSING", "status": "flag", "message": "a flag is allowed", "columns": ["x1"]}],
              "started": "2026-10-10T10:00:00+00:00", "finished": "2026-10-10T10:05:00+00:00",
              "checked_groups": m2_record()}
    report.update(over)
    path = Path(run_root) / pkg.dataset.name / "check" / ("check_deep_%s.json" % pkg.fingerprint[:12])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report), encoding="utf-8")
    return path, report


@pytest.fixture
def world(tmp_path, monkeypatch):
    from treeroute.runs import fingerprint as FP

    monkeypatch.setattr(C, "constants_with_origins", _fixed_constants)
    monkeypatch.setattr(C, "version_pins", _pins)
    # the engine and tooling listings are read once: other work may edit the live tree while a test runs
    engine_files, stripped = C.engine_file_hashes(), FP.engine_code_hash()
    tooling = C.report_file_hashes()
    monkeypatch.setattr(C, "engine_file_hashes", lambda root=None: dict(engine_files))
    monkeypatch.setattr(C, "report_file_hashes", lambda root=None: dict(tooling))
    monkeypatch.setattr(FP, "engine_code_hash", lambda root=None: stripped)
    protected = tmp_path / "shipped"
    protected.mkdir()
    reg = make_registry(tmp_path, [protected])
    pkg = make_package(tmp_path / "pkgs")
    (pkg / "ban.yaml").write_text(GREEN_BAN, encoding="utf-8")
    files = []
    for kind in ("target", "drivers"):
        for g in DATA_GROUPS:
            for y in YEARS:
                p = pkg / "data" / kind / ("group=%s" % g) / ("year=%d" % y) / "part-0.parquet"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(("%s %s %d" % (kind, g, y)).encode("ascii"))
                files.append(p)
    n_target = len(DATA_GROUPS) * len(YEARS)
    static = pkg / "data" / "static" / "part-0.parquet"
    static.parent.mkdir(parents=True)
    static.write_bytes(b"static table")
    entries = []
    for p in files[:n_target]:                           # the target files are in inputs.json, the rest are not
        st = os.stat(p)
        entries.append({"path": p.as_posix(), "size": st.st_size, "mtime": int(st.st_mtime),
                        "sha256": C.sha256_file(p)})
    (reg / "inputs.json").write_text(json.dumps({"created": "test", "roots": [str(pkg / "data" / "target")],
                                                 "extra": [], "files": entries}), encoding="utf-8")
    runs = tmp_path / "runs"
    check_path, _ = write_check(runs, pkg)
    draft = tmp_path / "PREREG_DRAFT.md"
    draft.write_text(DRAFT, encoding="utf-8")
    return {"tmp": tmp_path, "registry": reg, "runs": runs, "pkg": pkg, "check": check_path, "draft": draft,
            "protected": protected, "target_files": files[:n_target], "static": static}


def _freeze(world, packages=None, now=NOW, **kw):
    return F.freeze([world["pkg"]] if packages is None else packages, world["runs"], world["registry"],
                    engine_code_sha256=kw.pop("engine", _engine_sha), prereg_draft=kw.pop("draft", world["draft"]),
                    echo=lambda *_: None, now=_moment(now))


def _refused(world, fid, match=None, **kw):
    with pytest.raises(F.FreezeRefusal) as info:
        _freeze(world, **kw)
    assert fid in info.value.ids(), str(info.value)
    if match:
        assert match in str(info.value), str(info.value)
    freeze_dir = world["registry"] / F.FREEZE_SUBDIR
    assert not freeze_dir.exists() or not any(freeze_dir.iterdir()), "a refused freeze wrote a file"
    return info.value


# ----------------------------------------------------------------------------------------- all green
def test_an_all_green_world_gets_a_correct_lock_and_a_filled_preregistration(world):
    res = _freeze(world)
    lock_path = res["lock"]
    assert lock_path.parent == (world["registry"] / F.FREEZE_SUBDIR).resolve()
    assert lock_path.name == "FREEZE_20261010T120000Z.lock.json"
    text = lock_path.read_text(encoding="utf-8")
    assert C.sha256_text(text) == res["lock_sha256"]
    lock = json.loads(text)
    pkg = load_package(world["pkg"])
    assert lock["lock_format"] == F.LOCK_FORMAT and lock["created_utc"] == NOW
    assert lock["engine"]["engine_code_sha256"] == ENGINE_SHA
    assert lock["engine"]["files"] == C.engine_file_hashes()
    assert "engine_constants.py" in lock["engine"]["files"] and not any("_proposed" in k for k in lock["engine"]["files"])
    # the report tooling is hashed on its own: the table builder, the freeze and the pre-registered lists
    tooling = lock["report_tooling"]["files"]
    assert {"table.py", "freeze.py", "continuity_groups.yaml", "history_bands.yaml", "report_rows.yaml"} <= set(tooling)
    assert tooling["continuity_groups.yaml"] == C.sha256_file(C.REPORT_DIR / "continuity_groups.yaml")
    assert lock["report_tooling"]["sha256"] == F.report_tooling_sha256(tooling)
    assert not any("__pycache__" in k for k in tooling)
    ids = [r["id"] for r in lock["engine_constants"]["constants"]]
    assert ids == [r["id"] for r in K.table()]
    assert all(r["origin"] for r in lock["engine_constants"]["constants"])
    assert lock["engine_constants"]["constants_hash"] == K.constants_hash()
    awaiting = [r["id"] for r in K.table() if r["status"] in F.CONSTANT_STATUSES_TO_CONFIRM]
    assert [r["id"] for r in lock["engine_constants"]["awaiting_owner"]] == awaiting
    assert {"F-DRAFT", "F-TOOLING", "F-STORES", "G-FACTS", "F-CHECK-GROUPS"} <= set(lock["preconditions"])
    (rec,) = lock["packages"]
    assert rec["draft"]["is_draft"] is False
    assert rec["fingerprint"] == pkg.fingerprint and rec["file_hashes"] == pkg.file_hashes
    assert rec["include_hashes"] == pkg.include_hashes
    assert rec["check_report"]["sha256"] == C.sha256_file(world["check"])
    assert rec["check_report"]["checked_groups"] == m2_record()          # ruling M2: the groups the check read
    assert rec["plan"] is None
    sources = {Path(p).name + ":" + v["source"] for p, v in lock["store_files"].items()}
    assert sum(1 for s in sources if s.endswith(":inputs.json")) >= 1
    by_source = {}
    for p, v in lock["store_files"].items():
        by_source.setdefault(v["source"], []).append(p)
        assert v["sha256"] == C.sha256_file(p)
    n_files = len(DATA_GROUPS) * len(YEARS)
    assert len(by_source["inputs.json"]) == n_files and len(by_source["freeze"]) == n_files + 1   # drivers + static
    roles = [s["role"] for s in rec["stores"]]
    assert roles == ["target", "static", "drivers"]
    assert lock["inputs"]["sha256"] == C.sha256_file(world["registry"] / "inputs.json")
    assert lock["python"]["libraries"]["numpy"]
    pins = lock["launch_pins"]["env_pins"]
    assert pins["OMP_NUM_THREADS"] == str(K.FOREST_THREADS) and pins["OPENBLAS_NUM_THREADS"] == str(K.BLAS_THREADS)
    assert lock["launch_pins"]["workers"]["router_workers"] == K.ROUTER_WORKERS
    assert "no-op rule" in lock["no_op_rule"]
    filled = res["prereg"].read_text(encoding="utf-8")
    assert res["lock_sha256"] in filled and pkg.fingerprint in filled and ENGINE_SHA in filled
    assert lock["report_tooling"]["sha256"] in filled
    if awaiting:
        assert "awaiting: %d: %s (" % (len(awaiting), awaiting[0]) in filled
    else:
        assert "awaiting: none" in filled
    assert "{{" not in filled
    assert "NOT FILLED: other_pkg is not in this freeze" in filled and "NOT FILLED: toy_pkg has no plan" in filled
    assert sorted(res["unfilled"]) == ["DERIVED_SETTINGS:toy_pkg", "DERIVED_SHA256:toy_pkg",
                                       "PACKAGE_FINGERPRINT:other_pkg"]


def test_the_lock_is_written_once(world):
    _freeze(world)
    with pytest.raises(Exception, match="refusing to overwrite"):
        _freeze(world)


def test_a_current_plan_is_recorded_and_fills_the_derived_settings(world):
    from treeroute.runs.fingerprint import engine_code_hash

    pkg = load_package(world["pkg"])
    folder = make_plan(world, pkg.fingerprint, engine_code_hash())
    res = _freeze(world)
    rec = json.loads(res["lock"].read_text(encoding="utf-8"))["packages"][0]["plan"]
    assert rec["folder"] == str(folder)
    assert rec["derived_json_sha256"] == C.sha256_file(folder / "derived.json")
    assert rec["plan_json_sha256"] == C.sha256_file(folder / "plan.json")
    filled = res["prereg"].read_text(encoding="utf-8")
    assert "router kind per_unit" in filled and "test years 2020, 2021" in filled
    assert rec["derived_json_sha256"] in filled


def make_plan(world, package_fingerprint, engine_hash, name="20261010_aaaaaaaa"):
    folder = world["runs"] / "toy_pkg" / "headline" / name
    (folder / "phases" / "plan").mkdir(parents=True)
    (folder / "phases" / "plan" / "DONE").write_text(json.dumps({"finished_utc": "2026-10-10T11:00:00+00:00"}),
                                                     encoding="utf-8")
    (folder / "run_record.json").write_text(json.dumps({"package_fingerprint": package_fingerprint,
                                                        "run_fingerprint": "c" * 64, "derived_sha256": "d" * 64}),
                                            encoding="utf-8")
    (folder / "manifest.json").write_text(json.dumps({"engine_code_hash": engine_hash}), encoding="utf-8")
    (folder / "derived.json").write_text(json.dumps({"R1": {"value": "monthly"}}), encoding="utf-8")
    plan = {"router_kind": "per_unit", "links": ["identity"], "windows": {"y0": 2003, "y_end": 2021,
            "test_years": [2020, 2021], "train_end": 2019, "inner_fit": [2003, 2016], "inner_score": [2017, 2019]},
            "groups": 2, "bank_units": {"grp_a": 3, "grp_b": 3}, "scored_units": {"grp_a": 2, "grp_b": 2},
            "trees_per_group": 100, "leads": [6, 12], "history_columns": ["hist_last_1"], "overlap_blocks": [],
            "tree_features": 2, "context": []}
    (folder / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    return folder


# ---------------------------------------------------------------------------- one test per refusal
def test_refuses_without_a_package(world):
    _refused(world, "F-NAMES", packages=[])


def test_refuses_a_package_named_twice(world):
    _refused(world, "F-NAMES", "named twice", packages=[world["pkg"], world["pkg"]])


def test_refuses_a_package_that_does_not_load(world):
    (world["pkg"] / "split.yaml").unlink()
    _refused(world, "F-PACKAGE")


def test_refuses_a_draft_package(world):
    from treeroute.pipeline.draft import DRAFT_MARKER, draft_status

    (world["pkg"] / "ban.yaml").write_text(GREEN_BAN.replace(
        "evidence: Part 2", "evidence: '%s shipped verdicts | Part 2'" % DRAFT_MARKER), encoding="utf-8")
    assert draft_status(load_package(world["pkg"])).is_draft
    write_check(world["runs"], world["pkg"])                     # a green deep report does not make it freezable
    _refused(world, "F-DRAFT", "is a DRAFT")


def test_refuses_while_the_contract_engine_hash_function_is_missing(world, monkeypatch):
    from treeroute.runs import fingerprint as FP

    monkeypatch.delattr(FP, C.CONTRACT_FUNCTION, raising=False)
    _refused(world, "F-ENGINE-HASH", "agent B adds it", engine=None)


def test_refuses_without_a_deep_check_report(world):
    world["check"].unlink()
    _refused(world, "F-CHECK-EXISTS", "no deep check report")


def test_refuses_a_deep_check_report_of_an_older_fingerprint(world):
    old = world["check"].with_name("check_deep_000000000000.json")
    world["check"].rename(old)
    _refused(world, "F-CHECK-EXISTS", "check_deep_000000000000.json")


def test_refuses_a_report_that_breaks_the_contract(world):
    path, report = write_check(world["runs"], world["pkg"])
    del report["started"]
    path.write_text(json.dumps(report), encoding="utf-8")
    _refused(world, "F-CHECK-CONTRACT", "missing keys")


def test_refuses_a_report_with_an_unknown_guard_status(world):
    write_check(world["runs"], world["pkg"], guards=[{"id": "G-FACTS", "status": "maybe", "message": "", "columns": []}])
    _refused(world, "F-CHECK-CONTRACT", "status 'maybe'")


def test_refuses_a_report_of_other_engine_code(world):
    write_check(world["runs"], world["pkg"], engine_code_sha256="cd" * 32)
    _refused(world, "F-CHECK-MATCH", "the engine changed since the check")


def test_refuses_a_quick_report_or_another_package(world):
    write_check(world["runs"], world["pkg"], mode="quick", package="someone_else")
    err = _refused(world, "F-CHECK-MATCH")
    assert "mode 'quick'" in str(err) and "someone_else" in str(err)


def test_refuses_a_report_that_is_not_green(world):
    write_check(world["runs"], world["pkg"], green=False)
    _refused(world, "F-CHECK-GREEN", "green=False")


def test_refuses_a_green_report_with_a_refusing_guard(world):
    path, report = write_check(world["runs"], world["pkg"])
    report["guards"].append({"id": "G-LAG2", "status": "refuse", "message": "x", "columns": []})
    path.write_text(json.dumps(report), encoding="utf-8")
    _refused(world, "F-CHECK-GREEN", "G-LAG2")


# ------------------------------------------------------------- ruling M2: the deep report's groups
def test_the_smoke_groups_the_freeze_recomputes_are_r21_of_the_package_groups(world):
    from treeroute.check import report as R
    from treeroute.derive.unit_rules import derive_r21_smoke_plan_loro

    pkg = load_package(world["pkg"])
    assert C.package_smoke_groups(pkg) == m2_record() == R.package_smoke_groups(pkg)
    assert SMOKE_GROUPS == list(derive_r21_smoke_plan_loro(PACKAGE_GROUPS).value["groups"])


def test_refuses_a_deep_report_on_every_group(world):
    # a full-size deep check is a side record under ruling M2, never the gate
    write_check(world["runs"], world["pkg"], checked_groups=m2_record(groups=list(PACKAGE_GROUPS)))
    err = _refused(world, "F-CHECK-GROUPS", "not the package's R21 smoke groups")
    assert "checked %d group(s)" % len(PACKAGE_GROUPS) in str(err) and ", ".join(SMOKE_GROUPS) in str(err)


@pytest.mark.parametrize("groups", [list(PACKAGE_GROUPS[1:]), ["grp_a", "grp_b"], ["grp_a", "grp_b", "grp_c", "grp_z"]])
def test_refuses_a_deep_report_on_another_subset(world, groups):
    write_check(world["runs"], world["pkg"], checked_groups=m2_record(
        groups=groups, selection="groups given by the caller (tests and gates only; not the ruling-M2 subset)",
        rule=None, constants={}))
    _refused(world, "F-CHECK-GROUPS", "not the package's R21 smoke groups")


def test_the_groups_decide_not_the_selection_words(world):
    # a caller-given subset that IS the R21 smoke groups checked the same data: accepted, its words recorded
    words = "groups given by the caller (tests and gates only; not the ruling-M2 subset)"
    write_check(world["runs"], world["pkg"], checked_groups=m2_record(selection=words, rule=None, constants={}))
    res = _freeze(world)
    rec = json.loads(res["lock"].read_text(encoding="utf-8"))["packages"][0]["check_report"]["checked_groups"]
    assert rec["groups"] == SMOKE_GROUPS and rec["selection"] == words


def test_refuses_a_deep_report_written_before_ruling_m2(world):
    path, report = write_check(world["runs"], world["pkg"])
    del report["checked_groups"]
    path.write_text(json.dumps(report), encoding="utf-8")
    _refused(world, "F-CHECK-CONTRACT", "missing keys ['checked_groups'] (a deep report names the groups")


@pytest.mark.parametrize("bad,match", [
    ({"groups": ["grp_b", "grp_a"]}, "not a sorted list"),
    ({"groups": "grp_a"}, "not a sorted list"),
    ({"package_groups": "5"}, "not a count"),
    ("R21", "not an object"),
])
def test_refuses_a_malformed_groups_record(world, bad, match):
    record = m2_record(**bad) if isinstance(bad, dict) else bad
    write_check(world["runs"], world["pkg"], checked_groups=record)
    _refused(world, "F-CHECK-CONTRACT", match)


def test_refuses_a_groups_record_with_other_keys(world):
    record = m2_record()
    del record["refused"]
    write_check(world["runs"], world["pkg"], checked_groups=record)
    _refused(world, "F-CHECK-CONTRACT", "checked_groups has the keys")


def test_refuses_a_deep_report_whose_group_choice_refused(world):
    write_check(world["runs"], world["pkg"], checked_groups=m2_record(groups=[], refused="[R21] too few groups"))
    _refused(world, "F-CHECK-GROUPS", "chose no group")


def test_refuses_when_the_package_group_count_changed_since_the_check(world):
    write_check(world["runs"], world["pkg"], checked_groups=m2_record(package_groups=len(PACKAGE_GROUPS) + 1))
    _refused(world, "F-CHECK-GROUPS", "when it was checked, %d now" % len(PACKAGE_GROUPS))


def test_refuses_when_a_new_group_changes_the_smoke_groups(world):
    p = world["pkg"] / "data" / "target" / "group=grp_0" / "year=2020" / "part-0.parquet"   # sorts first
    p.parent.mkdir(parents=True)
    p.write_bytes(b"a new group")
    err = _refused(world, "F-CHECK-GROUPS", "not the package's R21 smoke groups")
    assert "grp_0" in str(err)


def test_refuses_when_the_groups_cannot_be_listed(world):
    (world["pkg"] / "split.yaml").write_text("excluded: {grp_q: not in the data}\n", encoding="utf-8")
    write_check(world["runs"], world["pkg"])                     # the package changed: a fresh report
    _refused(world, "F-CHECK-GROUPS", "R21 smoke groups cannot be listed")


def test_refuses_unsigned_timing_facts_on_kept_columns(world):
    write_check(world["runs"], world["pkg"],
                guards=[{"id": "G-FACTS", "status": "flag", "message": "3 kept columns unsigned",
                         "columns": ["x1", "g1", "x9"]}])
    _refused(world, "G-FACTS", "x1, g1, x9")


def test_refuses_a_report_without_the_facts_guard(world):
    write_check(world["runs"], world["pkg"], guards=[{"id": "G-LAG", "status": "pass", "message": "", "columns": []}])
    _refused(world, "G-FACTS", "has no G-FACTS guard")


def test_refuses_a_keep_unreviewed_verdict(world):
    (world["pkg"] / "ban.yaml").write_text(GREEN_BAN.replace(
        "g1: {verdict: keep, reason: reviewed, evidence: Part 2}",
        'g1: {verdict: keep_unreviewed, reason: "facts signed, not reviewed"}'), encoding="utf-8")
    write_check(world["runs"], world["pkg"])                     # the package changed: a fresh green report
    _refused(world, "F-BAN-OPEN", "keep_unreviewed verdict(s): g1")


def test_refuses_an_open_owner_decision_written_in_the_ban_list(world):
    (world["pkg"] / "ban.yaml").write_text("# g1: OWNER DECISION pending (keep or ban)\n" + GREEN_BAN, encoding="utf-8")
    write_check(world["runs"], world["pkg"])
    _refused(world, "F-BAN-OPEN", "line 1")


@pytest.mark.parametrize("line", [
    "# The verdicts are the owner's, except three agent choices that await confirmation: x1 and g1",
    "#   whose windows await the owner's signature",
    "# g1: owner to decide between keep and ban",
    "# g1 kept pending the owner's review",
    "#   (owner decision open)",
    # the item labels the ban lists use (defo ban.yaml K3/K5, L3, L1 notes; the L3 reason-word note of the others)
    "#          in exceptions.yaml; OWNER item.",
    "#          feature-script output derived from a post_window_snapshot ban: OWNER item); kept through the six",
    "#       L1 (signatures): NOT written here; this file and the package's facts carry no reviewed_by (OWNER item).",
    "#          REASON WORD (owner check): L3 says the raw aglw_* are banned 'post_window_snapshot for 2022+'. They are",
])
def test_refuses_each_written_form_of_an_open_decision(world, line):
    (world["pkg"] / "ban.yaml").write_text(line + "\n" + GREEN_BAN, encoding="utf-8")
    write_check(world["runs"], world["pkg"])
    _refused(world, "F-BAN-OPEN", "line 1")


@pytest.mark.parametrize("line", [
    "#   rows read the 2022 layer (the data fix is an owner decision).",
    "# the 2023-vintage OWNER CHECK is moot",
    "# confirmed on NDVI; signed by the owner 2026-10-06",
    "#       L4 eddi_observed_mean/_min/_max: keep -> ban structural (closes J2 d's OWNER CHECK).",
    "#   sheet OWNER CHECK (PM2.5, fire and NDVI ban them; G-KEYS treats them as static-table columns)",
    "#   REASON WORD (owner check) is moot: the owner ruled 'incomplete'",
    "#   the OWNER item is closed by ruling M",
])
def test_settled_notes_are_not_open_decisions(line):
    assert not F.OPEN_DECISION.search(line)


def test_refuses_a_stale_plan(world):
    from treeroute.runs.fingerprint import engine_code_hash

    make_plan(world, "9" * 64, engine_code_hash())
    _refused(world, "F-PLAN", "plan again")


def test_refuses_a_plan_made_by_other_engine_code(world):
    pkg = load_package(world["pkg"])
    make_plan(world, pkg.fingerprint, "8" * 64)
    _refused(world, "F-PLAN", "other engine code")


def test_refuses_an_unset_engine_constant(world, monkeypatch):
    rows = _fixed_constants()
    rows[0] = dict(rows[0], value="UNSET", status="unset")
    monkeypatch.setattr(C, "constants_with_origins", lambda: rows)
    _refused(world, "F-CONSTANTS", rows[0]["id"])


def test_refuses_a_constant_without_an_origin(world, monkeypatch):
    rows = _fixed_constants()
    rows[1] = dict(rows[1], origin="")
    monkeypatch.setattr(C, "constants_with_origins", lambda: rows)
    _refused(world, "F-CONSTANTS", "without an origin comment: %s" % rows[1]["id"])


def test_refuses_library_versions_off_the_pins(world, monkeypatch):
    monkeypatch.setattr(C, "version_pins", lambda: dict(_pins(), installed={"x": "2"}))
    _refused(world, "F-PINS", "x pinned 1, installed 2")


def test_refuses_without_inputs_json(world):
    (world["registry"] / "inputs.json").unlink()
    _refused(world, "F-INPUTS")


def test_refuses_an_unknown_placeholder_in_the_draft(world):
    bad = world["tmp"] / "bad_draft.md"
    bad.write_text("{{LOCK_HASH}}\n", encoding="utf-8")
    _refused(world, "F-PREREG", "LOCK_HASH", draft=bad)


@pytest.mark.parametrize("marker", F.PENDING_MARKERS)
def test_refuses_a_draft_that_still_has_a_pending_item(world, marker):
    bad = world["tmp"] / "pending_draft.md"
    bad.write_text(DRAFT + "\n1. **%s: defo's first year.** Keep or drop.\n" % marker, encoding="utf-8")
    err = _refused(world, "F-PREREG", "1 open item(s)", draft=bad)
    assert "line %d" % (DRAFT.count("\n") + 2) in str(err)


def test_a_marker_named_in_prose_is_not_a_pending_item():
    text = ("Each open item starts with a bold marker, owner decision pending or open before freeze; the freeze "
            "refuses while one remains (the words OWNER DECISION PENDING alone, not bold, are prose).\n")
    assert F.pending_items(text) == []
    assert [m["marker"] for m in F.pending_items("- **OPEN BEFORE FREEZE: x**\n")] == ["OPEN BEFORE FREEZE"]


def test_the_older_fingerprint_list_leaves_out_the_details_sidecars(world):
    old = world["check"].with_name("check_deep_000000000000.json")
    world["check"].rename(old)
    old.with_name("check_deep_000000000000_details.json").write_text("{}", encoding="utf-8")
    err = _refused(world, "F-CHECK-EXISTS", "check_deep_000000000000.json")
    assert "_details.json" not in str(err)


def test_refuses_a_store_template_that_matches_no_file(world):
    import shutil

    shutil.rmtree(world["pkg"] / "data" / "drivers")
    _refused(world, "F-STORES", "matches no file")


def test_refuses_an_input_store_file_changed_since_inputs_json(world):
    world["target_files"][0].write_bytes(b"changed content, longer than before")
    _refused(world, "F-STORES", "changed since inputs.json")


def test_lists_every_failure_together(world):
    world["check"].unlink()
    (world["registry"] / "inputs.json").unlink()
    err = _refused(world, "F-CHECK-EXISTS")
    assert "F-INPUTS" in err.ids()


def test_a_changed_input_store_is_listed_with_the_other_round_one_failures(world):
    world["check"].unlink()
    world["target_files"][0].write_bytes(b"changed content, longer than before")
    err = _refused(world, "F-CHECK-EXISTS")
    assert "F-STORES" in err.ids(), str(err)


def test_refuses_a_store_file_that_changes_while_the_freeze_hashes_it(world, monkeypatch):
    real = C.sha256_file

    def hash_then_rewrite(path):
        out = real(path)
        if os.path.normcase(os.path.abspath(str(path))) == os.path.normcase(os.path.abspath(str(world["static"]))):
            Path(path).write_bytes(b"rewritten while the freeze read it")
        return out
    monkeypatch.setattr(C, "sha256_file", hash_then_rewrite)
    _refused(world, "F-STORES", "changed while the freeze read it")


def test_refuses_when_the_report_tooling_changes_while_the_freeze_runs(world, monkeypatch):
    first = C.report_file_hashes()
    calls = []

    def listing(root=None):
        calls.append(1)
        return dict(first) if len(calls) == 1 else dict(first, **{"table.py": "0" * 64})
    monkeypatch.setattr(C, "report_file_hashes", listing)
    _refused(world, "F-TOOLING", "table.py")


def test_constants_awaiting_the_owner_do_not_refuse_but_are_listed(world, monkeypatch):
    rows = _fixed_constants()
    rows = [dict(r, status="cited") for r in rows]
    rows[2] = dict(rows[2], status="proposed")
    monkeypatch.setattr(C, "constants_with_origins", lambda: rows)
    lines = []
    res = F.freeze([world["pkg"]], world["runs"], world["registry"], engine_code_sha256=_engine_sha,
                   prereg_draft=world["draft"], echo=lines.append, now=_moment())
    lock = json.loads(res["lock"].read_text(encoding="utf-8"))
    assert lock["engine_constants"]["awaiting_owner"] == [{"id": rows[2]["id"], "status": "proposed"}]
    assert any(ln.startswith("NOTE: 1 engine constant(s) await the owner's confirmation") for ln in lines)
    assert "awaiting: 1: %s (proposed)" % rows[2]["id"] in res["prereg"].read_text(encoding="utf-8")


# ------------------------------------------------------------------------------------ write guard
def test_the_write_guard_allows_only_the_freeze_folder_inside_the_registry(world):
    guard = C.WriteGuard(world["registry"], own_registry_subdirs=(F.FREEZE_SUBDIR,))
    assert guard.check(world["registry"] / "freeze" / "x.json").name == "x.json"
    with pytest.raises(C.ReportRefusal, match="inside the registry folder"):
        guard.check(world["registry"] / "inputs.json")
    with pytest.raises(C.ReportRefusal, match="protected"):
        guard.check(world["protected"] / "freeze" / "x.json")


# ----------------------------------------------------------------------------------------- verify
def test_verify_finds_no_drift_right_after_the_freeze(world):
    res = _freeze(world)
    out = F.verify(res["lock"], world["registry"], engine_code_sha256=_engine_sha, echo=lambda *_: None,
                   now=_moment("2026-10-11T00:00:00+00:00"))
    assert out["drift"] == [] and out["affected"] == []
    assert Path(out["report"]).name == "VERIFY_FREEZE_20261010T120000Z_20261011T000000Z.json"


def test_verify_names_package_and_store_drift(world):
    res = _freeze(world)
    with open(world["pkg"] / "exceptions.yaml", "a", encoding="utf-8") as fh:
        fh.write("# an edit after the freeze\n")
    world["static"].write_bytes(b"a rebuilt static table")
    out = F.verify(res["lock"], world["registry"], rehash_inputs=True, engine_code_sha256=_engine_sha,
                   echo=lambda *_: None, write_report=False)
    whats = {(d["what"], d["change"]) for d in out["drift"]}
    assert ("package fingerprint", "changed") in whats
    assert ("package file (toy_pkg)", "changed") in whats
    assert ("store file", "content changed") in whats
    assert out["affected"] == ["toy_pkg"], [d for d in out["drift"] if d["affects"] != "toy_pkg"]


def test_verify_names_a_change_of_the_smoke_groups(world):
    res = _freeze(world)
    p = world["pkg"] / "data" / "target" / "group=grp_0" / "year=2020" / "part-0.parquet"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"a new group")
    out = F.verify(res["lock"], world["registry"], engine_code_sha256=_engine_sha, echo=lambda *_: None,
                   write_report=False)
    moved = [d for d in out["drift"] if d["what"] == "R21 smoke groups (ruling M2)"]
    assert len(moved) == 1 and moved[0]["locked"] == SMOKE_GROUPS and moved[0]["now"][0] == "grp_0"
    assert out["affected"] == ["toy_pkg"]


def test_verify_names_a_changed_engine_file(world, monkeypatch):
    res = _freeze(world)
    files = dict(C.engine_file_hashes())
    files["engine_constants.py"] = "0" * 64
    monkeypatch.setattr(C, "engine_file_hashes", lambda root=None: files)
    out = F.verify(res["lock"], world["registry"], engine_code_sha256=_engine_sha, echo=lambda *_: None,
                   write_report=False)
    assert [(d["what"], d["item"], d["change"]) for d in out["drift"]] == [
        ("engine file", "engine_constants.py", "changed")]
    assert out["affected"] == ["all packages"]


def test_verify_names_a_changed_report_tooling_file(world, monkeypatch):
    res = _freeze(world)
    files = dict(C.report_file_hashes())
    files["continuity_groups.yaml"] = "0" * 64
    monkeypatch.setattr(C, "report_file_hashes", lambda root=None: files)
    out = F.verify(res["lock"], world["registry"], engine_code_sha256=_engine_sha, echo=lambda *_: None,
                   write_report=False)
    assert [(d["what"], d["item"], d["change"]) for d in out["drift"]] == [
        ("report tooling file (treeroute_report)", "continuity_groups.yaml", "changed")]
    assert out["affected"] == ["all packages"]


def test_verify_names_a_package_that_became_a_draft(world):
    from treeroute.pipeline.draft import DRAFT_MARKER

    res = _freeze(world)
    (world["pkg"] / "ban.yaml").write_text(GREEN_BAN.replace(
        "evidence: Part 2", "evidence: '%s shipped verdicts | Part 2'" % DRAFT_MARKER), encoding="utf-8")
    out = F.verify(res["lock"], world["registry"], engine_code_sha256=_engine_sha, echo=lambda *_: None,
                   write_report=False)
    assert ("package draft status", "changed") in {(d["what"], d["change"]) for d in out["drift"]}
    assert out["affected"] == ["toy_pkg"]


def test_verify_says_an_engine_change_affects_every_package(world):
    res = _freeze(world)
    out = F.verify(res["lock"], world["registry"], engine_code_sha256=lambda: "ef" * 32, echo=lambda *_: None,
                   write_report=False)
    assert any(d["what"] == "engine_code_sha256" for d in out["drift"])
    assert out["affected"] == ["all packages"]


def test_the_command_refuses_with_exit_4_and_writes_nothing(world):
    import subprocess
    import sys

    proc = subprocess.run([sys.executable, "-m", "treeroute_report.freeze", str(world["pkg"]), "--run-root",
                           str(world["runs"]), "--registry-dir", str(world["registry"]), "--prereg",
                           str(world["draft"])], cwd=str(C.ENGINE_DIR), capture_output=True, text=True, timeout=300)
    assert proc.returncode == F.EXIT_REFUSED, proc.stdout + proc.stderr
    assert "refused" in proc.stderr
    assert not (world["registry"] / F.FREEZE_SUBDIR).exists()


# --------------------------------------------------------------------- the contract and the real draft
def test_the_check_contract_matches_the_check_command(tmp_path):
    from treeroute.check import report as R
    from treeroute.runs import fingerprint as FP

    assert tuple(R.CONTRACT_KEYS) == F.CONTRACT_KEYS and tuple(R.GUARD_KEYS) == F.GUARD_KEYS
    assert tuple(R.DEEP_CONTRACT_KEYS) == F.DEEP_CONTRACT_KEYS and R.GROUPS_KEY == F.GROUPS_KEY
    assert tuple(R.GROUPS_RECORD_KEYS) == F.GROUPS_RECORD_KEYS and R.M2_SELECTION == F.M2_SELECTION
    assert C.SMOKE_GROUPS_MODULE == R.__name__ and callable(getattr(R, C.SMOKE_GROUPS_FUNCTION))
    assert set(R.STATUS_WORDS.values()) == set(F.GUARD_STATUSES)
    assert R.report_path(tmp_path, "p", "deep", "a" * 64) == F._check_report_path(tmp_path, "p", "a" * 64)
    assert C.contract_engine_code_sha256() == FP.engine_code_sha256()


def test_the_real_draft_uses_only_known_fields_and_names_the_four_packages():
    text = F.DEFAULT_PREREG.read_text(encoding="utf-8")
    fields = F.PLACEHOLDER.findall(text)
    for field, pkg in fields:
        assert field in (F.PACKAGE_FIELDS if pkg else F.GLOBAL_FIELDS), (field, pkg)
    per_package = {}
    for field, pkg in fields:
        if pkg:
            per_package.setdefault(pkg, set()).add(field)
    assert set(per_package) == {"pm25", "fire", "defo", "ndvi"}
    assert all(v == set(F.PACKAGE_FIELDS) for v in per_package.values()), per_package
    assert {"LOCK_SHA256", "ENGINE_CODE_SHA256", "ENGINE_CONSTANTS_SHA256", "REPORT_TOOLING_SHA256",
            "CONSTANTS_AWAITING_OWNER"} <= set(f for f, p in fields if not p)
    # ruling N settled every owner decision of the draft (S22 removed those markers); the items that wait on the
    # owner reading S8's 17 entries and on the deep-check run keep 'OPEN BEFORE FREEZE', so F-PREREG still refuses
    assert "**OPEN BEFORE FREEZE" in text and any(m in text for m in F.PENDING_MARKERS)
    assert "## Appendix A. The plan 3.3 flags as rows of their own" in text and "Not written yet" not in text

