"""T-H22 the heavy-job lock (SPEC_HUMAN.txt 1.13; PROT:321): while another holder keeps the engine's heavy-job lock of
the machine named by the config (the toy's own temp folder, never D:/treeroute/tmp), every heavy command refuses."""

import pytest

from rivals_human.tests import hooks as HK


@pytest.fixture()
def held_lock(grid_flow):
    """The engine HeavyJobLock in the toy machine's temp_dir, held by this process (a live holder)."""
    LY, H = HK.common_modules(grid_flow.h.config)
    cfg = H.load_config(HK.load_config(grid_flow.h).roots_mapping())
    eng = H.Engine(cfg)
    lock = eng.preflight.HeavyJobLock(eng.machine.temp_dir)
    lock.acquire()
    yield lock
    lock.release()


def test_h22_every_heavy_command_refuses_while_another_job_holds_the_lock(grid_flow, held_lock):
    h, out = grid_flow.h, grid_flow.out
    words = ("heavy", "holds")
    HK.refuses(words, HK.slim, h, 0)
    HK.refuses(words, HK.adapt, h, "toy_idx", 0)
    HK.refuses(words, HK.init, h)
    HK.refuses(words, HK.tune, h, out)
    HK.refuses(words, HK.lock, h, out)
    HK.refuses(words, HK.refit, h, out, 0)
    HK.refuses(words, HK.refs, h, out, 0)
    HK.refuses(words, HK.score, h, out, 0)
    HK.refuses(words, HK.board, h, out)


def test_h22_status_is_read_only_and_takes_no_lock(grid_flow, held_lock):
    text = HK.status(grid_flow.h, grid_flow.out)
    assert "human board" in str(text)
