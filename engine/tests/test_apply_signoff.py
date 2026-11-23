"""datasets/_tools/apply_signoff.py, the tool that writes the owner's freeze sign-off answers (FREEZE_SIGNOFF_SHEET.md)
into the packages: refusals before anything is read, the text edits (flow rows, blocks, values over several lines),
the settled ban.yaml notes, the engine constants, the move-aside writing, and one end-to-end pass on the planted clean
package with blockers put back in (G-FACTS and G-CLOSED refuse before, pass after; a second run plans nothing).
"""

import importlib.util
import textwrap
from pathlib import Path

import pytest
import yaml

from conftest import ENGINE_DIR
from planted import build as B

TOOL = ENGINE_DIR / "datasets" / "_tools" / "apply_signoff.py"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("apply_signoff_under_test", str(TOOL))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RULING = "ruling: {id: 'T', file: 'TEST_RULINGS.md', date: '2026-10-06'}\n"


def write_answers(path, body, ruling=RULING):
    path.write_text(ruling + textwrap.dedent(body), encoding="utf-8")
    return path


# ------------------------------------------------------------------------------------------- refusals
@pytest.mark.parametrize("body, needle", [
    ("answers:\n  S99: {answer: yes}\n", "unknown IDs"),
    ("answers:\n  S1: {answer: maybe}\n", "is not one of"),
    ("answers:\n  S1: {answer: yes, colour: red}\n", "unknown keys"),
    ("answers:\n  S10: {answer: yes, options: {yes: {delete_files: [x]}}}\n", "unknown keys"),
    ("answers:\n  S14: {answer: keep, options: {sometimes: {}}}\n", "options for unknown answer"),
    ("answers:\n  S14: {answer: confirm_watch, options: {confirm_watch: {notes: [{package: p}]}}}\n", "a note needs"),
    ("families: {soil: S9}\nanswers: {}\n", "maps to"),
    ("bogus: 1\nanswers: {}\n", "unknown top-level keys"),
    ("answers:\n  S17: {answer: b}\n  S28: {answer: a}\n", "answer S28 b"),
    ("answers:\n  S29: {answer: a, options: {a: {store_facts: {p: {road: {units: x}}}}}}\n", "may be recorded"),
    ("answers:\n  S6: {answer: recommended, reason_maybe: x}\n", "unknown keys"),
])
def test_bad_answers_are_refused_before_any_package_is_read(tool, tmp_path, body, needle, capsys):
    path = write_answers(tmp_path / "a.yaml", body)
    assert tool.main([str(path), "--engine", str(tmp_path / "no_engine"), "--packages", "nothing"]) == 4
    assert needle in capsys.readouterr().out


def test_an_answer_without_the_owner_ruling_is_refused(tool, tmp_path, capsys):
    path = write_answers(tmp_path / "a.yaml", "answers:\n  S1: {answer: yes}\n", ruling="ruling: {id: '', file: '', date: ''}\n")
    assert tool.main([str(path), "--engine", str(tmp_path), "--packages", "p"]) == 4
    assert "ruling.id is empty" in capsys.readouterr().out


def test_yes_and_no_read_as_words(tool, tmp_path):
    path = write_answers(tmp_path / "a.yaml", "answers:\n  S1: {answer: yes}\n  S5: {answer: no}\n"
                                              "  S11: {answer: yes, options: {yes: {remove_rows: {p: [c]}}}}\n")
    ans = tool.load_answers(path)
    assert ans.answers["S1"]["answer"] == "yes" and ans.answers["S5"]["answer"] == "no"
    assert "yes" in ans.answers["S11"]["options"]


# ------------------------------------------------------------------------------------------- text edits
STORE_TEXT = """\
store: s
columns:
  a:
    dtype: float32
    units: '1'
    cadence: {kind: static}
    scope: unit
    stamp: period_end
    fact_status: unverified
    provenance: 'a long text that runs on
      over a second line'
  b: {dtype: float32, units: '1', cadence: {kind: static}, scope: unit, stamp: period_end}  # a flow row
"""


def test_set_fields_signs_a_block_and_a_flow_row_and_keeps_everything_else(tool):
    lines = STORE_TEXT.split("\n")
    for col in ("a", "b"):
        lines = tool.set_fields(lines, col, 2, "columns", {"fact_status": "assumed", "reviewed_by": "owner",
                                                          "date": "2026-10-06"}, append_to={"provenance": "signed"})
    text = "\n".join(lines)
    old, new = yaml.safe_load(STORE_TEXT), yaml.safe_load(text)
    assert new["columns"]["a"]["provenance"] == "a long text that runs on over a second line; signed"
    assert new["columns"]["b"]["provenance"] == "signed" and "# a flow row" in text
    for col in ("a", "b"):
        assert new["columns"][col]["reviewed_by"] == "owner" and new["columns"][col]["date"] == "2026-10-06"
    changed = tool.ydiff(old, new)
    assert all(p[0] == "columns" and p[2] in ("fact_status", "reviewed_by", "date", "provenance") for p in changed)


def test_a_flow_verdict_becomes_a_block_and_comments_survive(tool):
    text = "verdicts:\n  x: {verdict: keep, reason: r, evidence: Part 1}\n  y:\n    # kept comment\n    verdict: ban\n" \
           "    reason: label\n    evidence: Part 1\n"
    lines = tool.replace_verdict(text.split("\n"), "x", "conditional", "out: a test", "owner ruling T")
    lines = tool.replace_verdict(lines, "y", "ban", "structural", "owner ruling T")
    doc = yaml.safe_load("\n".join(lines))
    assert doc["verdicts"]["x"] == {"verdict": "conditional", "reason": "out: a test", "evidence": "owner ruling T"}
    assert doc["verdicts"]["y"]["reason"] == "structural" and "# kept comment" in "\n".join(lines)


def test_settle_line_closes_every_open_phrase_the_freeze_scan_reads(tool):
    from treeroute_report.freeze import OPEN_DECISION

    for line in ("#   DECISION pending: keep or ban", "# windows await the owner's signature, while",
                 "# three agent choices that await confirmation: a, b", "#  REASON WORD (owner check): L3 says",
                 "    evidence: 'fixable, so OWNER item: one or the other'", "  x (owner decision open)'",
                 "# OWNER DECISION OPEN, (a) keep"):
        assert OPEN_DECISION.search(line)
        out = tool.settle_line(line, "ruling T, 2026-10-06 -- settled", OPEN_DECISION)
        assert not OPEN_DECISION.search(out) and "ruling T" in out


def test_engine_constants_c9_and_the_awaiting_statuses(tool, tmp_path):
    eng = tmp_path / "eng"
    (eng / "treeroute").mkdir(parents=True)
    src = (ENGINE_DIR / "treeroute" / "engine_constants.py").read_text(encoding="utf-8")
    (eng / "treeroute" / "engine_constants.py").write_text(src, encoding="utf-8")
    ans = tool.load_answers(write_answers(tmp_path / "a.yaml", "answers:\n  S12: {answer: a}\n  S20: {answer: b}\n"))
    plan = tool.Plan(eng, ans, [])
    tool.plan_constants(plan)
    tool.validate(plan)                                   # executes the edited module in its own namespace
    fe = plan.files[(eng / "treeroute" / "engine_constants.py").resolve()]
    ns = {"__name__": "check"}
    exec(compile(fe.text(), "engine_constants.py", "exec"), ns)
    reg = ns["_REGISTRY"]
    if '"C9.guard_tolerance_k", UNSET' in src:
        assert reg["C9.guard_tolerance_k"].value == tool.C9_CANDIDATE and reg["C9.guard_tolerance_k"].status == "cited"
    assert not [c for c in reg.values() if c.status in ("proposed", "extra")]
    assert "origin: owner ruling T" in fe.text() or '"C9.guard_tolerance_k", UNSET' not in src


def test_add_rows_and_remove_rows_edit_catalog_and_ban_together(tool, tmp_path):
    from types import SimpleNamespace

    pkg = tmp_path / "engine" / "datasets" / "p"
    pkg.mkdir(parents=True)
    (pkg / "catalog.yaml").write_text("columns:\n  y: {role: target}\n  old: {role: driver}\n", encoding="utf-8")
    (pkg / "ban.yaml").write_text("verdicts:\n  y: {verdict: ban, reason: label, evidence: Part 1}\n"
                                  "  old:\n    verdict: ban\n    reason: structural\n    evidence: Part 1\n",
                                  encoding="utf-8")
    ans = tool.load_answers(write_answers(tmp_path / "a.yaml", """\
        answers:
          S10:
            answer: yes
            options:
              yes:
                remove_rows: {p: [old]}
                add_rows: {p: {month: {role: support, verdict: ban, reason: structural, evidence: annual target}}}
        """))
    plan = tool.Plan((tmp_path / "engine").resolve(), ans, ["p"])
    ctxs = {"p": SimpleNamespace(facts=SimpleNamespace(loaded=SimpleNamespace(root=str(pkg))))}
    tool.plan_options(plan, ctxs)
    tool.validate(plan)
    cat = yaml.safe_load(plan.files[(pkg / "catalog.yaml").resolve()].text())
    ban = yaml.safe_load(plan.files[(pkg / "ban.yaml").resolve()].text())
    assert set(cat["columns"]) == {"y", "month"} and cat["columns"]["month"]["role"] == "support"
    assert set(ban["verdicts"]) == {"y", "month"} and ban["verdicts"]["month"]["verdict"] == "ban"
    assert "S10" in ban["verdicts"]["month"]["evidence"]


# ------------------------------------------------------------------------------------------- end to end
def _package_with_blockers(engine):
    pkg = B.make_clean_package(engine / "datasets")
    for _ in range(4):                                    # x1, g1, x2, s1 lose their signature; frac keeps it
        B.edit_store(pkg, "fact_status: verified", "fact_status: unverified")
    B.edit(pkg, "features/build.py", '"reads_target": False, "fact_status": "verified"}',
           '"reads_target": False, "fact_status": "unverified"}')
    B.edit(pkg, "catalog.yaml", "  x1: {role: driver, co_measured_with_target: false, co_measured_evidence: Part 1}",
           "  x1: {role: driver}")
    B.edit(pkg, "catalog.yaml", "    legal_range_source: synthetic product guide, valid range table\n", "")
    B.edit(pkg, "catalog.yaml", "  x1_lag1:", "  ghost: {role: driver}\n  x1_lag1:")
    B.edit(pkg, "ban.yaml", "verdicts:\n", "# the x2 disclosure: OWNER item, still waiting\nverdicts:\n"
                                           "  ghost: {verdict: ban, reason: structural, evidence: Part 1}\n")
    (pkg / "exceptions.yaml").write_text(
        "entries:\n  - kind: provenance_flag\n    column: x2\n    decision: disclose\n    reason: a test disclosure\n"
        "    owner: 'UNSIGNED -- basis: a test'\n    date: '2026-10-06'\n", encoding="utf-8")
    (engine / "config").mkdir(parents=True)
    (engine / "registry").mkdir()
    (engine / "registry" / "protected_roots.txt").write_text(str(engine / "protected") + "\n", encoding="utf-8")
    (engine / "config" / "machine.yaml").write_text("registry_dir: %s\n" % (engine / "registry").as_posix(),
                                                    encoding="utf-8")
    return pkg


ANSWERS = """\
packages: [planted_pkg]
families: {'(none)': S1}
answers:
  S1: {answer: yes}
  S5: {answer: yes}
  S6: {answer: recommended, true_for: {planted_pkg: []}}
  S7: {answer: yes, source: {planted_pkg: 'synthetic product guide, valid range table'}}
  S8: {answer: yes}
  S11:
    answer: yes
    options: {yes: {remove_rows: {planted_pkg: [ghost]}}}
  S14:
    answer: confirm_watch
    options: {confirm_watch: {notes: [{package: planted_pkg, contains: 'OWNER item, still waiting', text: closed}]}}
"""


def _guards(pkg):
    from treeroute.check.quick import run_quick

    ctx = run_quick(pkg, echo=lambda s: None)
    return {label: r.status.value for label, r in ctx.results}


def _snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(Path(root).rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts}


def test_end_to_end_dry_run_apply_and_a_second_run(tool, tmp_path, capsys):
    from treeroute_report.freeze import OPEN_DECISION

    engine = tmp_path / "engine"
    pkg = _package_with_blockers(engine)
    before = _guards(pkg)
    assert before["G-FACTS"] == "block" and before["G-CLOSED"] == "block", before
    answers = write_answers(tmp_path / "answers.yaml", ANSWERS)
    snap0 = _snapshot(engine / "datasets")

    assert tool.main([str(answers), "--engine", str(engine)]) == 0          # dry run
    out = capsys.readouterr().out
    assert "Nothing was written (dry run)" in out and "S5" in out and "S6_false" in out
    assert _snapshot(engine / "datasets") == snap0

    aside = tmp_path / "aside"
    assert tool.main([str(answers), "--engine", str(engine), "--apply", "--aside-root", str(aside)]) == 0
    out = capsys.readouterr().out
    assert "written:" in out
    after = _guards(pkg)
    assert after["G-FACTS"] == "pass" and after["G-CLOSED"] == "pass", after
    snap1 = _snapshot(engine / "datasets")
    assert set(snap1) == set(snap0)                                         # no file deleted or added
    everything = _snapshot(aside)
    moved = {k: v for k, v in everything.items() if not k.startswith("_staged/")}
    staged = {k[len("_staged/"):]: v for k, v in everything.items() if k.startswith("_staged/")}
    assert moved and set(staged) == set(moved), "every edited file's old copy and its staged new text are aside"
    for relpath, data in moved.items():
        assert snap0[relpath[len("datasets/"):]] == data                    # the old bytes, unchanged
        assert snap1[relpath[len("datasets/"):]] != data
        assert snap1[relpath[len("datasets/"):]] == staged[relpath]          # the staged text is what was written
    ban = (pkg / "ban.yaml").read_text(encoding="utf-8")
    assert not OPEN_DECISION.search(ban) and "ghost" not in ban
    store = yaml.safe_load((engine / "datasets" / "_stores" / "planted_store.yaml").read_text(encoding="utf-8"))
    assert store["columns"]["x1"]["reviewed_by"] == "owner" and store["columns"]["x1"]["fact_status"] == "assumed"
    assert "SIGNOFF BLOCK" in (pkg / "features" / "build.py").read_text(encoding="utf-8")
    exc = yaml.safe_load((pkg / "exceptions.yaml").read_text(encoding="utf-8"))
    assert exc["entries"][0]["owner"].startswith("owner -- signed by the owner 2026-10-06 (ruling T")

    assert tool.main([str(answers), "--engine", str(engine)]) == 0          # idempotent
    assert "files to write: 0" in capsys.readouterr().out


def test_writing_under_a_protected_root_is_refused_and_moves_nothing(tool, tmp_path, capsys):
    engine = tmp_path / "engine"
    pkg = _package_with_blockers(engine)
    answers = write_answers(tmp_path / "answers.yaml", ANSWERS)
    snap0 = _snapshot(engine / "datasets")
    assert tool.main([str(answers), "--engine", str(engine), "--apply", "--aside-root",
                      str(engine / "protected" / "aside")]) == 4
    assert "protected root" in capsys.readouterr().out
    assert _snapshot(engine / "datasets") == snap0 and not (engine / "protected").exists()
    assert pkg.is_dir()


def test_a_failure_half_way_puts_every_file_back_and_deletes_nothing(tool, tmp_path, capsys, monkeypatch):
    engine = tmp_path / "engine"
    _package_with_blockers(engine)
    answers = write_answers(tmp_path / "answers.yaml", ANSWERS)
    snap0 = _snapshot(engine / "datasets")
    real_replace, calls = tool.os.replace, []

    def locked_on_the_third(src, dst):                    # the third file swap fails, as a locked file would
        if str(src).endswith(".signoff_tmp"):
            calls.append(dst)
            if len(calls) == 3:
                raise OSError("locked by another program (test)")
        return real_replace(src, dst)

    monkeypatch.setattr(tool.os, "replace", locked_on_the_third)
    aside = tmp_path / "aside"
    assert tool.main([str(answers), "--engine", str(engine), "--apply", "--aside-root", str(aside)]) == 4
    out = capsys.readouterr().out
    assert "refused half way" in out and "were put back as they were" in out and "NOT restored" in out
    monkeypatch.setattr(tool.os, "replace", real_replace)
    snap1 = _snapshot(engine / "datasets")
    leftovers = [k for k in snap1 if k.endswith(".signoff_tmp")]
    assert len(leftovers) == 1                            # named in the message, never deleted
    assert {k: v for k, v in snap1.items() if k not in leftovers} == snap0
    assert _snapshot(aside / "_rolled_back") and _snapshot(aside / "_staged")


def test_a_file_changed_after_the_plan_read_it_is_refused_before_anything_moves(tool, tmp_path):
    engine = tmp_path / "engine"
    pkg = _package_with_blockers(engine)
    ans = tool.load_answers(write_answers(tmp_path / "a.yaml", "answers: {}\n"))
    plan = tool.Plan(engine.resolve(), ans, ["planted_pkg"])
    fe = plan.file(pkg / "ban.yaml", "ban")
    fe.lines = fe.lines + ["# an edit"]
    (pkg / "ban.yaml").write_text((pkg / "ban.yaml").read_text(encoding="utf-8") + "# another task\n",
                                  encoding="utf-8")
    before = (pkg / "ban.yaml").read_bytes()
    with pytest.raises(tool.SignoffRefusal, match="changed on disk since this run read them"):
        tool.write_all(plan, tmp_path / "aside")
    assert (pkg / "ban.yaml").read_bytes() == before and not (tmp_path / "aside" / "datasets").exists()


# ------------------------------------------------------------------------------------------- S8, S6, S29, pins
def test_s8_refuses_entries_that_still_read_open_or_call_a_banned_column_kept(tool):
    verdicts = {"raw": {"verdict": "ban", "reason": "incomplete"}, "hold": {"verdict": "watch", "reason": "r"},
                "x": {"verdict": "keep", "reason": "r"}}
    entry = {"kind": "disclosed_defect", "column": "x", "decision": "disclose", "reason": "fine",
             "owner": "UNSIGNED -- basis: a"}
    assert tool.stale_entry_reason(entry, verdicts) == ""
    assert "open decision" in tool.stale_entry_reason(dict(entry, decision="disclose; the fix is an OWNER DECISION"),
                                                      verdicts)
    assert "open decision" in tool.stale_entry_reason(dict(entry, reason="G-LAG refuses it until the owner signs one"),
                                                      verdicts)
    assert "open decision" in tool.stale_entry_reason(dict(entry, owner="UNSIGNED; the choice (a)/(b) is the owner's"),
                                                      verdicts)
    assert "bans raw" in tool.stale_entry_reason(dict(entry, column="raw", decision="disclose; kept as watch"), verdicts)
    both = {"kind": "provenance_flag", "check": "L3 (raw; held as hold)", "decision": "raw banned, hold kept as watch",
            "reason": "r", "owner": "UNSIGNED -- basis: L3"}
    assert tool.stale_entry_reason(both, verdicts) == ""                     # a kept column is named too
    only_raw = dict(both, check="J3 amended (watch): raw", decision="disclose (watch)")
    assert "bans raw" in tool.stale_entry_reason(only_raw, verdicts)


def test_s8_yes_is_refused_while_a_stale_entry_remains_and_names_it(tool, tmp_path, capsys):
    engine = tmp_path / "engine"
    pkg = _package_with_blockers(engine)
    B.edit(pkg, "exceptions.yaml", "decision: disclose", "decision: 'disclose; the data fix is an OWNER DECISION'")
    answers = write_answers(tmp_path / "answers.yaml", ANSWERS)
    snap0 = _snapshot(engine / "datasets")
    assert tool.main([str(answers), "--engine", str(engine), "--apply", "--aside-root", str(tmp_path / "x")]) == 4
    out = capsys.readouterr().out
    assert "not true as written" in out and "planted_pkg entry 0 (x2)" in out and "OWNER DECISION" in out
    assert _snapshot(engine / "datasets") == snap0


def _fake_ctx(pkg, entering, target="y"):
    from types import SimpleNamespace as NS

    facts = NS(loaded=NS(root=str(pkg)), target=NS(name=target), columns=entering, keys=())
    return NS(facts=facts, lags={}, cadence=None, entering=entering)


def test_s6_reasons_a_lag_of_a_coproduct_parent_and_the_owners_own_reason(tool, tmp_path):
    from types import SimpleNamespace as NS

    pkg = tmp_path / "engine" / "datasets" / "p"
    pkg.mkdir(parents=True)
    (pkg / "catalog.yaml").write_text("columns:\n  y: {role: target}\n  tc_lag2: {role: engineered}\n"
                                      "  tc: {role: driver}\n  pop: {role: driver}\n  t2m: {role: driver}\n"
                                      "  y_nbr: {role: engineered}\n", encoding="utf-8")
    (pkg / "ban.yaml").write_text("verdicts:\n  y: {verdict: ban, reason: label, evidence: P}\n"
                                  "  tc: {verdict: ban, reason: coproduct, evidence: P}\n", encoding="utf-8")
    yearly = NS(kind="regular", length=1, unit="year")
    entering = {"tc_lag2": NS(cadence=yearly, co_measured_with_target=None, derived_from=["tc"]),
                "pop": NS(cadence=yearly, co_measured_with_target=None, derived_from=[]),
                "t2m": NS(cadence=yearly, co_measured_with_target=None, derived_from=[]),
                "y_nbr": NS(cadence=yearly, co_measured_with_target=None, derived_from=["y"])}
    ans = tool.load_answers(write_answers(tmp_path / "a.yaml", """\
        answers:
          S6:
            answer: recommended
            true_for: {p: []}
            reason_false: plain no
            reason_false_for: {p: {pop: the owner's own reason}}
            reason_derived: derived no
            reason_coproduct: coproduct-parent no
        """))
    plan = tool.Plan((tmp_path / "engine").resolve(), ans, ["p"])
    tool.plan_co_measured(plan, {"p": _fake_ctx(pkg, entering)}, {"p": entering})
    cat = yaml.safe_load(plan.files[(pkg / "catalog.yaml").resolve()].text())["columns"]
    assert cat["tc_lag2"]["co_measured_evidence"].endswith("coproduct-parent no")
    assert cat["pop"]["co_measured_evidence"].endswith("the owners own reason")
    assert cat["t2m"]["co_measured_evidence"].endswith("plain no")
    assert cat["y_nbr"]["co_measured_evidence"].endswith("derived no")          # the target's own history
    assert all(cat[c]["co_measured_with_target"] is False for c in entering)


def test_s29_store_facts_record_an_epoch_on_the_store_row(tool, tmp_path):
    from treeroute.check.quick import run_quick

    engine = tmp_path / "engine"
    pkg = _package_with_blockers(engine)
    ctx = run_quick(pkg, echo=lambda s: None)
    ans = tool.load_answers(write_answers(tmp_path / "a.yaml", "answers:\n  S29: {answer: a}\n"))
    plan = tool.Plan(engine.resolve(), ans, ["planted_pkg"])
    tool.plan_store_facts(plan, {"planted_pkg": ctx}, "S29", "planted_pkg",
                          {"s1": {"content_epoch": "2018", "evidence": "a test map compiled about 2018"}})
    tool.validate(plan)                                   # schema, planned fields only, the epoch written
    store = (engine / "datasets" / "_stores" / "planted_store.yaml").resolve()
    col = yaml.safe_load(plan.files[store].text())["columns"]["s1"]
    assert col["content_epoch"] == "2018" and "S29" in col["provenance"] and "about 2018" in col["provenance"]


def test_a_shared_catalog_edit_with_an_unlisted_real_package_is_refused(tool, tmp_path):
    from types import SimpleNamespace as NS

    datasets = tmp_path / "engine" / "datasets"
    (datasets / "_stores").mkdir(parents=True)
    store = datasets / "_stores" / "s.yaml"
    store.write_text("columns:\n  a: {dtype: float32}\n", encoding="utf-8")
    for name in ("p", "q", "p_draft"):
        (datasets / name).mkdir()
        (datasets / name / "dataset.yaml").write_text("includes:\n  - {path: ../_stores/s.yaml, sha256: %s}\n"
                                                       % ("0" * 64), encoding="utf-8")
    ans = tool.load_answers(write_answers(tmp_path / "a.yaml", "answers: {}\n"))
    plan = tool.Plan((tmp_path / "engine").resolve(), ans, ["p"])
    fe = plan.file(store, "store")
    fe.lines = ["# edited"] + fe.lines
    ctxs = {"p": NS(facts=NS(loaded=NS(root=str(datasets / "p"))))}
    with pytest.raises(tool.SignoffRefusal, match="datasets/q/dataset.yaml includes"):
        tool.plan_repins(plan, ctxs)
    ctxs["q"] = NS(facts=NS(loaded=NS(root=str(datasets / "q"))))
    plan.files = {k: v for k, v in plan.files.items() if v.kind == "store"}
    tool.plan_repins(plan, ctxs)                          # both real packages listed: re-pinned; the draft listed
    assert any("p_draft" in w for w in plan.warnings)


def test_the_report_lists_the_tests_that_read_an_edited_file(tool, tmp_path):
    engine = tmp_path / "engine"
    (engine / "tests").mkdir(parents=True)
    (engine / "tests" / "test_reads_it.py").write_text("P = DATASETS / 'p' / 'ban.yaml'\n", encoding="utf-8")
    (engine / "tests" / "test_other.py").write_text("P = DATASETS / 'q' / 'ban.yaml'\n", encoding="utf-8")
    pkg = engine / "datasets" / "p"
    pkg.mkdir(parents=True)
    (pkg / "ban.yaml").write_text("verdicts: {}\n", encoding="utf-8")
    ans = tool.load_answers(write_answers(tmp_path / "a.yaml", "answers: {}\n"))
    plan = tool.Plan(engine.resolve(), ans, ["p"])
    fe = plan.file(pkg / "ban.yaml", "ban")
    fe.lines = ["# edited"] + fe.lines
    listed = dict(tool.affected_tests(plan))
    assert "tests/test_reads_it.py" in listed and "tests/test_other.py" not in listed
    assert all(path in listed for path, _, _ in tool.MEASURED_TEST_IMPACT)


def test_s8_sign_only_signs_the_listed_entries_and_leaves_the_rest(tool, tmp_path, capsys):
    """Ruling N S8: the owner signs part of the list. Only the listed entries are checked and signed; a stale entry
    left off the list does not block them and stays unsigned; a label that no longer matches its entry is refused."""
    engine = tmp_path / "engine"
    pkg = _package_with_blockers(engine)
    with (pkg / "exceptions.yaml").open("a", encoding="utf-8") as fh:
        fh.write("  - kind: provenance_flag\n    column: x1\n    decision: 'disclose; the data fix is an OWNER DECISION'\n"
                 "    reason: a stale test disclosure\n    owner: 'UNSIGNED -- basis: a test'\n    date: '2026-10-06'\n")
    wrong = write_answers(tmp_path / "wrong.yaml", ANSWERS.replace(
        "  S8: {answer: yes}", "  S8: {answer: yes, sign_only: {planted_pkg: {0: x1}}}"))
    assert tool.main([str(wrong), "--engine", str(engine)]) == 4
    assert "entry 0 is 'x2', not 'x1'" in capsys.readouterr().out
    answers = write_answers(tmp_path / "answers.yaml", ANSWERS.replace(
        "  S8: {answer: yes}", "  S8: {answer: yes, sign_only: {planted_pkg: {0: x2}}}"))
    assert tool.main([str(answers), "--engine", str(engine), "--apply", "--aside-root", str(tmp_path / "x")]) == 0
    out = capsys.readouterr().out
    assert "1 unsigned exceptions.yaml entries are left unsigned" in out and "planted_pkg 1 (x1)" in out
    entries = yaml.safe_load((pkg / "exceptions.yaml").read_text(encoding="utf-8"))["entries"]
    assert entries[0]["owner"].startswith("owner -- ") and entries[1]["owner"].startswith("UNSIGNED")
    assert tool.main([str(answers), "--engine", str(engine)]) == 0          # idempotent: nothing more to sign
    assert "sign entry" not in capsys.readouterr().out
