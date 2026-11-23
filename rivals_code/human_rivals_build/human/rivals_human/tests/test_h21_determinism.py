"""T-H21 determinism and resume (SPEC_HUMAN.txt 1.6, 1.13; no seeds varied): two independent tunes give byte-equal
trials and picks; a tune killed after candidate k and resumed gives byte-equal outputs; a lead-0 pick refit on the
tune rows reproduces its tuning predictions (the refit checks it)."""

import json

import pytest

from rivals_human.tests import hooks as HK


def _trial_bytes(out):
    d = out / "trials"
    return {str(p.relative_to(d)): p.read_bytes() for p in sorted(d.rglob("*"))
            if p.is_file() and not p.name.endswith(".json")} | \
        {str(p.relative_to(d)): _strip_json(p) for p in sorted(d.rglob("*.json"))}


def _strip_json(p):
    """A trial record without its wall-clock fields (seconds)."""
    doc = HK.read_json(p)
    if isinstance(doc, dict):
        doc.pop("seconds", None)
    return json.dumps(doc, sort_keys=True).encode("utf-8")


def _picks_content(out):
    doc = HK.picks(out)
    return json.dumps({r: {k: v for k, v in p.items() if k != "leads"} for r, p in doc["picks"].items()},
                      sort_keys=True)


def test_h21_two_tunes_are_byte_equal(grid_flow):
    v1 = HK.variant_config(grid_flow.h, "det_a")
    v2 = HK.variant_config(grid_flow.h, "det_b")
    o1, o2 = HK.run_tune_lock(v1), HK.run_tune_lock(v2)
    assert _trial_bytes(o1) == _trial_bytes(o2)
    assert (o1 / "trials.csv").read_bytes() == (o2 / "trials.csv").read_bytes()
    assert _picks_content(o1) == _picks_content(o2) == _picks_content(grid_flow.out)


def test_h21_a_killed_tune_resumes_to_the_same_outputs(grid_flow, monkeypatch):
    M = HK.tool("maps")
    v = HK.variant_config(grid_flow.h, "resume")
    out = HK.init(v)
    calls = {"n": 0}
    orig = M.fit

    class Killed(RuntimeError):
        pass

    def killing_fit(*a, **kw):
        calls["n"] += 1
        if calls["n"] > 7:
            raise Killed("test kill after 7 candidate fits")
        return orig(*a, **kw)

    monkeypatch.setattr(M, "fit", killing_fit)
    with pytest.raises(Killed):
        HK.tune(v, out)
    assert calls["n"] == 8, "tune did not fit through maps.fit (BUILD_NOTES_tests.txt item A16)"
    monkeypatch.setattr(M, "fit", orig)
    HK.tune(v, out, resume=True)
    HK.lock(v, out)
    ref = HK.variant_config(grid_flow.h, "resume_ref")
    o_ref = HK.run_tune_lock(ref)
    assert _trial_bytes(out) == _trial_bytes(o_ref)
    assert _picks_content(out) == _picks_content(o_ref)
