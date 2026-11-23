"""T-F07 the join to the slim keys and the frame (SPEC_HUMAN_PARTB.txt 3.7; SPEC_HUMAN 1.4; index.py:410-479).

One row per slim key (train + test, stage all), keys of no other lead; NaN where not covered (a month outside the
product); product_cell and src are text on every row ("" where uncovered); x__fwi_mean / x__fwi_pct float64, info_end
int64, target_obs_end float64 (NaN); the frame passes the tool's own index.check_frame with the shas the ctx opened
(every src file of a covered row opened through ctx.open_product with its manifest sha).
"""

import numpy as np
import pandas as pd
import pytest

from tests_fire import fixtures_fire as FF


def _check_frame(frame, ctx, rival, lead, tier="P"):
    from rivals_human import index as IX
    return IX.check_frame(frame, ctx.keys("all"), rival, IX.Timing(ctx.run, rival, lead), tier, (0.0, 1.0),
                          ctx.opened, FF.manifests_of(ctx), "toy %s lead %d" % (rival["id"], lead))


def _schema(geff, frame):
    from rivals_human import config as C
    assert sorted(frame.columns) == sorted(list(C.INDEX_FIXED_COLUMNS) + FF.STATS)
    for s in FF.STATS:
        assert frame[s].dtype == np.float64, s
    assert frame["info_end"].dtype == np.int64
    assert frame["target_obs_end"].dtype == np.float64 and frame["target_obs_end"].isna().all()
    for c in ("product_cell", "src"):
        assert all(isinstance(v, str) for v in frame[c].tolist()), c
    for c in ("time", "issue", "lead"):
        assert np.issubdtype(frame[c].dtype, np.integer), c


@pytest.mark.parametrize("kind", ["era5", "seas5"])
def test_f07_one_row_per_slim_key_and_check_frame(geff, raw_subsets, tmp_path, kind):
    toy = FF.era5_toy(tmp_path, raw_subsets) if kind == "era5" else FF.seas5_toy(tmp_path, raw_subsets)
    ctx = toy.ctx()
    frame = geff.build(ctx, toy.rival, toy.lead, "all")
    _schema(geff, frame)
    keys = ctx.keys("all")
    assert len(frame) == len(keys)
    a = frame[["unit", "time", "issue", "lead"]].astype({"unit": str}).sort_values(["unit", "time"]).reset_index(drop=True)
    b = keys[["unit", "time", "issue", "lead"]].sort_values(["unit", "time"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_dtype=False)
    assert not frame.duplicated(subset=["unit", "time", "issue"]).any()
    assert (frame["lead"] == toy.lead).all()
    rec = _check_frame(frame, ctx, toy.rival, toy.lead)
    assert rec["rows"] == len(keys) and rec["t1_breaks"] == 0 and rec["t2_breaks"] == 0
    covered = np.isfinite(frame[FF.STATS].to_numpy(np.float64)).any(axis=1)
    pid = FF.ERA5_PID if kind == "era5" else FF.SEAS5_PID
    names = set(ctx.opened[pid])
    assert set(frame.loc[covered, "src"]) <= names and (frame.loc[covered, "src"] != "").all()
    assert (frame.loc[covered, "product_cell"] != "").all()
    out_time = FF.step(2020, 1) if kind == "era5" else FF.step(2019, 8)
    out = frame[frame["time"] == out_time]
    assert len(out) == len(toy.units) and out[FF.STATS].isna().all().all()           # outside the product -> NaN
    assert set(out["src"]) <= {""} | names


def test_f07_check_frame_catches_a_src_not_opened(geff, raw_subsets, tmp_path):
    """The proof that the opened shas matter: a frame naming a file the ctx did not open is refused by the tool."""
    toy = FF.era5_toy(tmp_path, raw_subsets)
    ctx = toy.ctx()
    frame = geff.build(ctx, toy.rival, 0, "all")
    bad = frame.copy()
    covered = np.isfinite(bad[FF.STATS].to_numpy(np.float64)).any(axis=1)
    bad.loc[np.flatnonzero(covered)[0], "src"] = "hist_never_opened_2018-2019.nc"
    FF.refuses(_check_frame, bad, ctx, toy.rival, 0, kinds=FF.tool_refusals(), words=("src",))


def test_f07_duplicate_or_foreign_keys_refuse(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets)
    dup = pd.concat([toy.table, toy.table.iloc[:1]], ignore_index=True)
    FF.refuses(geff.build, toy.ctx(key_table=dup), toy.rival, 0, "all",
               kinds=(geff.FireGeffRefusal,) + FF.tool_refusals())
    other = toy.table.copy()
    other.loc[other.index[-1], "lead"] = 6
    other.loc[other.index[-1], "issue"] = other.loc[other.index[-1], "time"] - 6
    FF.refuses(geff.build, toy.ctx(key_table=other), toy.rival, 0, "all",
               kinds=(geff.FireGeffRefusal,) + FF.tool_refusals())


def test_f07_build_logs_counts(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets)
    ctx = toy.ctx()
    geff.build(ctx, toy.rival, 0, "all")
    assert ctx.log_lines, "the adapter logs its counts (3.7: rows, covered per stat, substituted, uncovered, ...)"
