"""labels/vault.py: the adoption locks and the test-label release (plan 2.4 R27, R29; 4.1 steps 8-11;
5 G-LOCK).

  - lock_adoption writes the adoption document decide() registered (the adoption, every candidate and
    the decision section) once, hashes it and records the lock with the pre-lock test-window reads;
    test labels of a pass open only against that pass's recorded hash, after the lock;
  - planted faults: test labels asked for before any lock (an unlocked adoption), with a wrong hash,
    after adoption.json was changed on disk, for a lead whose nowcast was never locked; a lock after
    the labels opened; a second, different adoption; a placebo (or trees-off) arm adopted; an adoption
    no decide() made on a surface of this vault; a harness link without a legacy declaration; a lead
    pin that is not R29's; a vault without (or with another) run folder;
  - a resumed run re-reads its locks and markers, and refuses a folder whose opened marker names
    another adoption.
"""

import json
import os

import numpy as np
import pytest

from test_vault_world import LAST_STEP, LEGAL, TEST_FIRST, decide_world, make_context, make_surface, make_world
from treeroute.derive.shapes import CutKind, Link
from treeroute.labels.vault import (ADOPTION_FILE, LEAD_ADOPTION_FILE, LOCK_SUFFIX, OPENED_FILE,
                                    TestLabels, VaultRefusal, lock_adoption,
                                    lock_lead_adoption)
from treeroute.layer.arms import (ArmSpec, LayerRefusal, LegacyCandidates, Tool, Weighting,
                                  trees_off_of)
from treeroute.layer.decide import (Adoption, LeadAdoption, PenaltyPick, SurfaceArm, decide,
                                    forecast_adoption, select_adoption)
from treeroute.route.kinds import GridPoint, per_unit_grid

P1 = GridPoint(1.0, 0.5)
GRID = per_unit_grid(True)


def adoption(world, declined=False):
    """decide() on the world's inner surface (registered with its vault); its Adoption."""
    return decide_world(world, declined=declined).adoption


@pytest.fixture
def world(tmp_path):
    folder = tmp_path / "run"
    folder.mkdir()
    return make_world(run_folder=folder)


def _sha(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------ the nowcast pass
def test_lock_then_open_releases_the_test_window(world, capsys):
    folder = world.labels.run_folder
    rec = decide_world(world)
    a = rec.adoption
    world.labels.asof_rows(np.array([0, 1]), np.array([TEST_FIRST + 3, TEST_FIRST - 5]), 1)   # D54 (a)
    sha = lock_adoption(a, world.labels, folder)
    assert sha == _sha(folder / ADOPTION_FILE)
    lock = json.loads((folder / (ADOPTION_FILE + LOCK_SUFFIX)).read_text(encoding="utf-8"))
    assert lock["sha256"] == sha and lock["lead"] == 0
    assert lock["pre_lock_test_window_reads"]["rows"] == 1                  # one read reached the test window
    assert lock["pre_lock_test_window_reads"]["rows_before_any_lock"] == 1
    assert "pre-lock test-window reads" in capsys.readouterr().out
    doc = json.loads((folder / ADOPTION_FILE).read_text(encoding="utf-8"))
    assert doc["declined"] is False and doc["adopted"]["tool"] in ("plain", "corrector")
    # the locked document holds every candidate and the decision section
    assert len(doc["surface_mae"]) == len(rec.candidates)
    assert doc["decision"]["surface_sha256"] == rec.surface_sha256
    assert doc["decision"]["candidate_table_sha256"] == rec.candidate_table_sha256
    assert doc["decision"]["missing_arms"] == [] and doc["decision"]["legacy"] is None
    test = world.labels.open_test_labels(sha, 0)
    assert isinstance(test, TestLabels) and test.lead == 0 and test.adoption_sha256 == sha
    assert test.times.min() == TEST_FIRST and test.times.max() == LAST_STEP
    lookup = {(u, t): v for u, t, v in zip(world.units.tolist(), world.steps.tolist(), world.y.tolist())}
    for u, t, v in zip(test.unit_ids.tolist()[:500], test.times.tolist()[:500], test.y.tolist()[:500]):
        w = lookup[(u, t)]
        assert (np.isnan(w) and np.isnan(v)) or w == v
    marker = json.loads((folder / (OPENED_FILE % 0)).read_text(encoding="utf-8"))
    assert marker["adoption_sha256"] == sha
    assert world.labels.opened_passes() == {0: sha}
    # re-opening the same pass with the same hash is allowed (a resumed scoring pass)
    again = world.labels.open_test_labels(sha, 0)
    assert np.array_equal(again.times, test.times)


def test_planted_open_before_any_lock_is_refused(world):
    """Planted fault: an unlocked adoption. No test label opens before the adoption is hashed."""
    decide_world(world)
    with pytest.raises(VaultRefusal, match="no locked adoption"):
        world.labels.open_test_labels("0" * 64, 0)
    assert world.labels.opened_passes() == {}


def test_planted_open_with_a_wrong_hash_is_refused(world):
    sha = lock_adoption(adoption(world), world.labels, world.labels.run_folder)
    wrong = ("1" if sha[0] != "1" else "2") + sha[1:]
    with pytest.raises(VaultRefusal, match="hash mismatch"):
        world.labels.open_test_labels(wrong, 0)
    with pytest.raises(VaultRefusal, match="SHA-256 hex"):
        world.labels.open_test_labels("not a hash", 0)


def test_planted_changed_adoption_file_is_refused(world):
    folder = world.labels.run_folder
    sha = lock_adoption(adoption(world), world.labels, folder)
    path = folder / ADOPTION_FILE
    text = path.read_text(encoding="utf-8").replace('"declined": false', '"declined": true')
    os.chmod(str(path), 0o666)
    path.write_text(text, encoding="utf-8")                        # tampered after the lock
    with pytest.raises(VaultRefusal, match="hash mismatch"):
        world.labels.open_test_labels(sha, 0)
    with pytest.raises(VaultRefusal, match="differs from its lock record"):
        make_world(run_folder=folder)                              # a resumed run refuses the folder


def test_planted_lock_after_the_labels_opened_is_refused(world):
    folder = world.labels.run_folder
    sha = lock_adoption(adoption(world), world.labels, folder)
    world.labels.open_test_labels(sha, 0)
    with pytest.raises(VaultRefusal, match="open already"):
        lock_adoption(adoption(world), world.labels, folder)
    with pytest.raises(VaultRefusal, match="open already"):
        lock_adoption(adoption(world, declined=True), world.labels, folder)


def test_a_second_different_adoption_is_refused_and_the_same_one_confirms(world):
    folder = world.labels.run_folder
    first = adoption(world)
    sha = lock_adoption(first, world.labels, folder)
    assert lock_adoption(adoption(world), world.labels, folder) == sha      # decide() again: same document
    with pytest.raises(VaultRefusal, match="different content"):
        lock_adoption(adoption(world, declined=True), world.labels, folder)


def test_planted_placebo_or_trees_off_adoption_is_refused(world):
    """Planted fault: a placebo selected. Neither the layer nor the lock accepts it."""
    good = adoption(world)
    placebo = ArmSpec(link=Link.IDENTITY, tool=Tool.PLACEBO_CORRECTOR, weighting=Weighting.UNWEIGHTED,
                      selectable=False)
    bad = Adoption(adopted=placebo, penalty=P1, declined=False, best_tree_arm=placebo,
                   best_tree_penalty=P1, eligible=(placebo,), surface_mae=good.surface_mae, beside={})
    with pytest.raises(LayerRefusal, match="never selectable"):
        lock_adoption(bad, world.labels, world.labels.run_folder)
    off = trees_off_of(Link.IDENTITY)
    bad2 = Adoption(adopted=off, penalty=P1, declined=False, best_tree_arm=off, best_tree_penalty=P1,
                    eligible=(off,), surface_mae=good.surface_mae, beside={})
    with pytest.raises(LayerRefusal, match="never selectable"):
        lock_adoption(bad2, world.labels, world.labels.run_folder)
    # a placebo that claims to be selectable is refused as a malformed arm
    liar = ArmSpec(link=Link.IDENTITY, tool=Tool.PLACEBO_CORRECTOR, weighting=Weighting.UNWEIGHTED,
                   selectable=True)
    bad3 = Adoption(adopted=liar, penalty=P1, declined=False, best_tree_arm=liar, best_tree_penalty=P1,
                    eligible=(liar,), surface_mae=good.surface_mae, beside={})
    with pytest.raises(LayerRefusal, match="selectable"):
        lock_adoption(bad3, world.labels, world.labels.run_folder)
    assert not (world.labels.run_folder / ADOPTION_FILE).exists()


def test_planted_an_adoption_decide_did_not_make_is_refused(world):
    """Planted fault: an adoption built with select_adoption alone (no vault-issued surface)."""
    a = ArmSpec(Link.IDENTITY, Tool.PLAIN, Weighting.UNWEIGHTED, True)
    hand = select_adoption((PenaltyPick(a, P1, 1.0, {P1: 1.0}, False),), {Link.IDENTITY: 2.0}, {})
    with pytest.raises(VaultRefusal, match="not made by decide"):
        lock_adoption(hand, world.labels, world.labels.run_folder)
    # an adoption decided on another vault's surface is not this vault's
    other = make_world()
    elsewhere = decide_world(other).adoption
    with pytest.raises(VaultRefusal, match="not made by decide"):
        lock_adoption(elsewhere, world.labels, world.labels.run_folder)
    assert not (world.labels.run_folder / ADOPTION_FILE).exists()


class _Legacy(object):
    import enum

    class Key(enum.Enum):
        LOG1P = "log1p"


def test_a_harness_link_is_locked_only_under_its_legacy_declaration(world):
    key = _Legacy.Key.LOG1P
    arms_order = [ArmSpec(link, tool, Weighting.UNWEIGHTED, True)
                  for link in (Link.IDENTITY, key) for tool in (Tool.PLAIN, Tool.CORRECTOR)]
    legacy = LegacyCandidates(arms=tuple(arms_order) + (trees_off_of(Link.IDENTITY), trees_off_of(key)),
                              reason="replay of a shipped link R22 does not have")
    s = make_surface(world)
    good = np.tile(s.y[:, None], (1, len(GRID)))
    surf = [SurfaceArm(a, good + (0.5 if a.link is Link.IDENTITY else 0.1)) for a in arms_order]
    surf += [SurfaceArm(trees_off_of(Link.IDENTITY), s.y + 3.0), SurfaceArm(trees_off_of(key), s.y + 3.0)]
    rec = decide(s, surf, GRID, LEGAL, make_context(world, 0, CutKind.GUARD), legacy=legacy)
    assert rec.adoption.adopted.link is key
    # planted: the registered document loses its legacy declaration -> the lock refuses the key
    saved = [dict(d) for d in world.labels._decisions]
    for d in world.labels._decisions:
        d["decision"] = dict(d["decision"], legacy=None)
    with pytest.raises(VaultRefusal, match="R22 does not have"):
        lock_adoption(rec.adoption, world.labels, world.labels.run_folder)
    world.labels._decisions[:] = saved
    sha = lock_adoption(rec.adoption, world.labels, world.labels.run_folder)
    doc = json.loads((world.labels.run_folder / ADOPTION_FILE).read_text(encoding="utf-8"))
    assert doc["decision"]["legacy"]["link_keys"] == ["identity", "log1p"] and len(sha) == 64


def test_a_vault_without_or_with_another_run_folder_cannot_lock_or_open(world, tmp_path):
    bare = make_world()
    a = adoption(bare)
    with pytest.raises(VaultRefusal, match="run folder"):
        lock_adoption(a, bare.labels, world.labels.run_folder)
    with pytest.raises(VaultRefusal, match="run folder"):
        bare.labels.open_test_labels("0" * 64, 0)
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(VaultRefusal, match="run folder"):
        lock_adoption(adoption(world), world.labels, other)


# ------------------------------------------------------------------------------------ lead passes
def test_lead_lock_and_open(world):
    folder = world.labels.run_folder
    now = adoption(world)
    pinned_mae = 0.5
    with pytest.raises(VaultRefusal, match="not the one lock_adoption recorded"):
        lock_lead_adoption(forecast_adoption(now, 3, pinned_mae, 2.5, 3), now, "0" * 64, world.labels, folder)
    with pytest.raises(VaultRefusal, match="nowcast adoption was never locked"):
        world.labels.open_test_labels("0" * 64, 3)
    sha0 = lock_adoption(now, world.labels, folder)
    lead = forecast_adoption(now, 3, pinned_mae, 2.5, 3)
    assert lead.guard_passed and lead.placebo_built and lead.adopted == now.adopted
    with pytest.raises(VaultRefusal, match="no locked adoption"):
        world.labels.open_test_labels(sha0, 3)                     # the lead's own lock is needed
    sha3 = lock_lead_adoption(lead, now, sha0, world.labels, folder)
    assert sha3 == _sha(folder / (LEAD_ADOPTION_FILE % 3))
    doc = json.loads((folder / (LEAD_ADOPTION_FILE % 3)).read_text(encoding="utf-8"))
    assert doc["nowcast_sha256"] == sha0 and doc["lead"] == 3 and doc["placebo_built"] is True
    with pytest.raises(VaultRefusal, match="hash mismatch"):
        world.labels.open_test_labels(sha0, 3)
    test = world.labels.open_test_labels(sha3, 3)
    assert test.lead == 3
    with pytest.raises(VaultRefusal, match="open already"):
        lock_lead_adoption(lead, now, sha0, world.labels, folder)


def test_lead_lock_refuses_a_wrong_pin_lead_zero_and_another_nowcast(world):
    folder = world.labels.run_folder
    now = adoption(world)
    sha0 = lock_adoption(now, world.labels, folder)
    wrong_arm = ArmSpec(Link.LOG_C, Tool.PLAIN, Weighting.GLS, True)
    if wrong_arm == now.adopted:
        wrong_arm = ArmSpec(Link.IDENTITY, Tool.PLAIN, Weighting.UNWEIGHTED, True)
    bad = LeadAdoption(lead=1, pinned=wrong_arm, penalty=P1, guard_passed=True, adopted=wrong_arm,
                       placebo_built=False)
    with pytest.raises(VaultRefusal, match="R29's pin"):
        lock_lead_adoption(bad, now, sha0, world.labels, folder)
    zero = LeadAdoption(lead=0, pinned=now.adopted, penalty=now.penalty, guard_passed=True,
                        adopted=now.adopted, placebo_built=False)
    with pytest.raises(VaultRefusal, match="nowcast pass is locked by lock_adoption"):
        lock_lead_adoption(zero, now, sha0, world.labels, folder)
    other = adoption(world, declined=True)
    with pytest.raises(VaultRefusal, match="not the locked one"):
        lock_lead_adoption(forecast_adoption(other, 1, 2.0, 2.5, 3), other, sha0, world.labels, folder)
    # the locked file changed on disk: refused before any pin check
    path = folder / ADOPTION_FILE
    os.chmod(str(path), 0o666)
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(VaultRefusal, match="differs from its lock"):
        lock_lead_adoption(forecast_adoption(now, 1, 0.1, 2.5, 3), now, sha0, world.labels, folder)


def test_a_declined_nowcast_pins_its_best_tree_arm(world):
    folder = world.labels.run_folder
    now = adoption(world, declined=True)
    assert now.declined and now.adopted is None
    sha0 = lock_adoption(now, world.labels, folder)
    lead = forecast_adoption(now, 1, 5.0, 4.0, 3)                  # the pinned arm fails the guard
    assert lead.pinned == now.best_tree_arm and not lead.guard_passed and lead.adopted is None
    assert not lead.placebo_built
    sha1 = lock_lead_adoption(lead, now, sha0, world.labels, folder)
    assert world.labels.locked_passes() == {0: sha0, 1: sha1}


# ------------------------------------------------------------------------------------ resume
def test_a_resumed_vault_reads_its_locks_and_markers(world):
    folder = world.labels.run_folder
    sha = lock_adoption(adoption(world), world.labels, folder)
    world.labels.open_test_labels(sha, 0)
    again = make_world(run_folder=folder)
    assert again.labels.locked_passes() == {0: sha}
    assert again.labels.opened_passes() == {0: sha}
    assert again.labels.open_test_labels(sha, 0).lead == 0
    with pytest.raises(VaultRefusal, match="open already"):
        lock_adoption(adoption(again), again.labels, folder)


def test_a_resumed_run_that_decides_again_confirms_its_lock(world):
    folder = world.labels.run_folder
    sha = lock_adoption(adoption(world), world.labels, folder)
    again = make_world(run_folder=folder)                          # a new process: decide() runs again
    assert lock_adoption(adoption(again), again.labels, folder) == sha


def test_a_folder_whose_marker_names_another_adoption_is_refused(world):
    folder = world.labels.run_folder
    sha = lock_adoption(adoption(world), world.labels, folder)
    marker = folder / (OPENED_FILE % 0)
    marker.write_text(json.dumps({"lead": 0, "adoption_sha256": "f" * 64}), encoding="utf-8")
    with pytest.raises(VaultRefusal, match="opened against adoption"):
        make_world(run_folder=folder)
    marker.unlink()
    (folder / (OPENED_FILE % 3)).write_text(json.dumps({"lead": 3, "adoption_sha256": sha}), encoding="utf-8")
    with pytest.raises(VaultRefusal, match="opened against adoption"):
        make_world(run_folder=folder)                              # lead 3 was never locked
