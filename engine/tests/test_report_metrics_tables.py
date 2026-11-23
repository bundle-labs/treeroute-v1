"""treeroute.report.metrics: saved rows (assemble_rows), the score tables (R34: per year, per group,
per stratum; pooled and macro lines; D67 row selection), metric_by_key and the write-once writers.
Synthetic data; every branch. Files go only under pytest's tmp_path (tests/_pytest_tmp).
"""

import json
import math
import os

import numpy as np
import pandas as pd
import pytest

from treeroute.errors import RefusedError
from treeroute.report import metrics as M
from treeroute.runs.atomic import AtomicWriteError

INF = float("inf")
LEGAL = (0.0, INF)


def refused(fn, *args, match=None, **kwargs):
    with pytest.raises(RefusedError) as info:
        fn(*args, **kwargs)
    if match:
        assert match in str(info.value), str(info.value)
    return info.value


def _rows(n_groups=4, units_per_group=3, years=(10, 11), seed=5):
    """A synthetic saved-row set: monthly rows (steps year x 12 + month) of a few groups."""
    rng = np.random.RandomState(seed)
    unit, group, time, year = [], [], [], []
    for g in range(n_groups):
        for u in range(units_per_group):
            for yr in years:
                for m in range(1, 13):
                    unit.append("g%d_u%d" % (g, u))
                    group.append("g%d" % g)
                    time.append(yr * 12 + m)
                    year.append(yr)
    n = len(unit)
    normal = 5.0 + 2.0 * np.sin(np.array(time) / 2.0)
    y = np.maximum(normal + rng.normal(0, 1.5, n), 0.0)
    pre_a = y + rng.normal(0, 1.0, n) - 0.3
    pre_b = normal + 0.5 * (y - normal) + rng.normal(0, 0.8, n)
    pre_pa = pre_a + rng.normal(0, 0.5, n)
    keys = {"unit": np.array(unit), "group": np.array(group), "time": np.array(time), "year": np.array(year)}
    arms = {"a": np.clip(pre_a, *LEGAL), "b": np.clip(pre_b, *LEGAL)}
    placebos = {"pa": np.clip(pre_pa, *LEGAL)}
    pre = {"a": pre_a, "b": pre_b, "pa": pre_pa}
    persist = np.clip(np.r_[np.nan, y[:-1]], *LEGAL)
    persist[np.array(time) % 12 == 1] = np.nan          # no issue label at the first month of a year
    baselines = {"guess_normal": M.baseline_guess_normal(normal, LEGAL),
                 "predict_zero": M.baseline_predict_zero(n, LEGAL), "persistence": persist}
    return keys, y, normal, arms, placebos, pre, baselines


def _args(**over):
    keys, y, normal, arms, placebos, pre, baselines = _rows()
    args = dict(keys=keys, lead=0, issue=keys["time"], y=y, normal=normal, arms=arms, placebos=placebos,
                pre_clip=pre, baselines=baselines, legal_range=LEGAL)
    args.update(over)
    return args


def _frame(**over):
    return M.assemble_rows(**_args(**over))


# ---------------------------------------------------------------------------------------------------
# assemble_rows
def test_assemble_rows_saves_every_row_and_column():
    f = _frame()
    keys, y, normal, arms, placebos, pre, baselines = _rows()
    assert len(f) == len(y)
    for c in ("unit", "group", "time", "year", "lead", "issue", "y", "normal", "legal_min", "legal_max",
              "arm__a", "pre__a", "arm__b", "pre__b", "placebo__pa", "pre__pa", "base__guess_normal",
              "base__predict_zero", "base__persistence"):
        assert c in f.columns, c
    assert "arm__pa" not in f.columns                    # a placebo is never saved under the arm prefix
    assert np.array_equal(f["pre__a"].to_numpy(), pre["a"])
    assert np.array_equal(f["placebo__pa"].to_numpy(), placebos["pa"])
    assert f["lead"].unique().tolist() == [0] and f["legal_max"].unique().tolist() == [INF]
    none = M.assemble_rows(**_args(placebos={}, pre_clip={"a": pre["a"], "b": pre["b"]}))
    assert not [c for c in none.columns if c.startswith("placebo__")]   # a lead without a placebo


def test_assemble_rows_accepts_missing_labels_and_no_normal():
    keys, y, normal, arms, placebos, pre, baselines = _rows()
    y2 = y.copy()
    y2[:3] = np.nan
    f = M.assemble_rows(keys, 1, keys["time"] - 1, y2, np.full(y.size, np.nan), arms, placebos, pre,
                        baselines, LEGAL)
    assert f["y"].isna().sum() == 3 and f["normal"].isna().all()


def test_assemble_rows_compares_with_the_layers_clip():
    keys, y, normal, arms, placebos, pre, baselines = _rows()
    legal = (0.5, 6.0)                                   # clips on both sides
    pre2 = {k: v.copy() for k, v in pre.items()}
    pre2["a"][:2] = (-3.0, 40.0)
    from treeroute.layer.links import clip_to_legal

    clipped = {k: clip_to_legal(v, legal, False)[0] for k, v in pre2.items()}
    base = {k: np.clip(np.nan_to_num(v, nan=1.0), *legal) for k, v in baselines.items()}
    f = M.assemble_rows(keys, 0, keys["time"], y, normal, {"a": clipped["a"], "b": clipped["b"]},
                        {"pa": clipped["pa"]}, pre2, base, legal)
    assert f["arm__a"].iloc[0] == 0.5 and f["arm__a"].iloc[1] == 6.0 and f["pre__a"].iloc[1] == 40.0


def test_assemble_rows_refusals():
    keys, y, normal, arms, placebos, pre, baselines = _rows()
    n = y.size
    base = _args()

    def bad(match, **over):
        refused(M.assemble_rows, **dict(base, **over), match=match)

    bad("whole number", lead=-1)
    bad("whole number", lead=True)
    bad("map key names", keys=[1, 2])
    bad("key columns", keys={k: v for k, v in keys.items() if k != "year"})
    bad("infinite", y=np.r_[y[:-1], INF])
    bad("collides", keys=dict(keys, lead=keys["time"]))
    bad("collides", keys=dict(keys, arm__x=keys["time"]))
    bad("shape", keys=dict(keys, stratum=np.ones(3)))
    bad("missing on", keys=dict(keys, stratum=np.r_[np.ones(n - 1), np.nan]))
    dup = dict(keys, time=np.r_[keys["time"][:1], keys["time"][:-1]])
    bad("repeat", keys=dup)
    bad("issue values", issue=keys["time"][:5])
    bad("normal values", normal=normal[:5])
    bad("everywhere or nowhere", normal=np.r_[np.nan, normal[1:]])
    bad("at least one arm", arms={}, placebos={}, pre_clip={})
    bad("placebos must map", placebos=[1])
    bad("both as an arm and as a placebo", placebos={"a": arms["a"]})
    bad("pre-clip values and nothing else", pre_clip={"a": pre["a"], "b": pre["b"]})
    bad("pre-clip values and nothing else", pre_clip=[1])
    bad("map names", baselines=[1])
    bad("non-empty strings", arms={"": arms["a"]}, placebos={}, pre_clip={"": pre["a"]})
    bad("values for", arms={"a": arms["a"][:5]}, placebos={}, pre_clip={"a": pre["a"][:5]})
    bad("not finite", arms={"a": arms["a"]}, placebos={}, pre_clip={"a": np.r_[np.nan, pre["a"][1:]]})
    bad("arm 'a': 1", arms={"a": np.r_[arms["a"][0] + 1e-3, arms["a"][1:]]}, placebos={},
        pre_clip={"a": pre["a"]})
    bad("placebo 'pa'", placebos={"pa": np.r_[np.nan, placebos["pa"][1:]]})
    bad("placebo 'pa': 1 predictions are not their pre-clip value clipped",
        placebos={"pa": np.r_[placebos["pa"][0] + 1e-3, placebos["pa"][1:]]})
    bad("values for", baselines={"x": np.ones(5)})
    bad("infinite", baselines={"x": np.r_[INF, np.ones(n - 1)]})
    bad("outside the legal range", baselines={"x": np.r_[-1.0, np.ones(n - 1)]})


# ---------------------------------------------------------------------------------------------------
# score_table
def test_score_table_per_group_reproduces_the_scores_on_each_groups_rows():
    f = _frame()
    t = M.score_table(f, ("group",), 1.0, 0.5, M.RunKind.HEADLINE)
    assert t.attrs["by"] == ("group",) and set(t["run_kind"]) == {"headline"}
    key = t[(t.line == "key") & (t.column == "arm__a") & (t.rows_basis == "all")]
    assert key["group"].tolist() == ["g0", "g1", "g2", "g3"]
    g1 = f[f.group == "g1"]
    row = key[key.group == "g1"].iloc[0]
    assert row["mae"] == M.mae(g1.y, g1.arm__a)
    assert row["anom_r2"] == M.anomaly_r2(g1.y, g1.arm__a, g1.normal)
    assert row["corr2"] == M.corr2(g1.y, g1.arm__a)
    assert row["hit"] == M.hit_rate(g1.y, g1.arm__a, 1.0)
    assert row["hit_floor"] == M.hit_rate(g1.y, g1.arm__a, 0.5)
    assert row["calibration_ratio"] == M.calibration_ratio(g1.y, g1.arm__a)
    assert row["preclip_rate"] == M.preclip_rate(g1.pre__a, LEGAL) and row["preclip_n"] == len(g1)
    det = M.top10_detection(g1.y.to_numpy(), g1.arm__a.to_numpy())
    assert row["detection_events"] == det.n_events and row["n_units"] == 3 and row["n"] == len(g1)
    pooled = t[(t.line == "pooled") & (t.column == "arm__a") & (t.rows_basis == "all")].iloc[0]
    assert pooled["mae"] == M.mae(f.y, f.arm__a)
    assert pooled["detection"] == M.top10_detection(f.y.to_numpy(), f.arm__a.to_numpy()).score
    macro = t[(t.line == "macro") & (t.column == "arm__a") & (t.rows_basis == "all")].iloc[0]
    assert macro["mae"] == pytest.approx(key["mae"].mean()) and macro["mae_keys"] == 4
    assert macro["n"] == pooled["n"]
    zero = t[(t.line == "key") & (t.column == "base__guess_normal") & (t.rows_basis == "all")]
    assert (zero["anom_r2"] == 0.0).all()           # guess-normal scores 0 by construction
    assert zero["column_kind"].unique().tolist() == ["baseline"]
    assert np.isnan(zero["preclip_rate"]).all() and (zero["preclip_n"] == 0).all()


def test_score_table_d67_partial_baseline_scored_on_its_rows_with_arms_beside():
    f = _frame()
    t = M.score_table(f, ("year",), 1.0, None, "smoke")
    bases = t["rows_basis"].unique().tolist()
    assert bases == ["all", "base__persistence"]
    have = f["base__persistence"].notna() & f["y"].notna()
    p_all = t[(t.line == "pooled") & (t.column == "base__persistence") & (t.rows_basis == "all")].iloc[0]
    assert p_all["n"] == int(have.sum()) and p_all["rows_missing"] == int((~have).sum())
    beside = t[(t.line == "pooled") & (t.column == "arm__a") & (t.rows_basis == "base__persistence")].iloc[0]
    assert beside["n"] == int(have.sum())
    assert beside["mae"] == M.mae(f.y[have], f.arm__a[have])
    assert np.isnan(t["hit_floor"]).all()               # no declared floor


def test_score_table_pooled_only_multi_key_and_stratum_tables():
    f = _frame()
    only = M.score_table(f, (), 1.0, None, M.RunKind.LEGACY)
    assert set(only["line"]) == {"pooled"}
    multi = M.score_table(f, ("group", "year"), 1.0, None, M.RunKind.LEGACY)
    keys = multi[(multi.line == "key") & (multi.column == "arm__a") & (multi.rows_basis == "all")]
    assert len(keys) == 8 and set(keys["year"]) == {10, 11}
    edges = (4.0, 5.0, 6.0)
    f2 = f.assign(stratum=M.stratum_bins(f["normal"].to_numpy(), edges))
    per = M.score_table(f2, ("stratum",), 1.0, None, M.RunKind.HEADLINE)
    strata = per[(per.line == "key") & (per.column == "arm__b") & (per.rows_basis == "all")]
    assert strata["stratum"].tolist() == sorted(set(f2["stratum"]))


def test_score_table_without_a_normal_and_with_an_empty_key_under_a_basis():
    f = _frame()
    f["normal"] = np.nan                                  # neighbour kind: no normal on any row
    f["base__recent"] = np.where(f["group"] == "g0", np.nan, f["y"] * 0 + 5.0)
    t = M.score_table(f, ("group",), 1.0, None, M.RunKind.HEADLINE)
    assert np.isnan(t["anom_r2"]).all() and (t["anom_r2_n"] == 0).all()
    empty = t[(t.line == "key") & (t.column == "arm__a") & (t.rows_basis == "base__recent") & (t.group == "g0")]
    assert len(empty) == 1 and empty.iloc[0]["n"] == 0 and np.isnan(empty.iloc[0]["mae"])
    macro = t[(t.line == "macro") & (t.column == "arm__a") & (t.rows_basis == "base__recent")].iloc[0]
    assert macro["mae_keys"] == 3


def test_score_table_skips_unlabelled_rows_and_prints_their_count():
    f = _frame()
    f.loc[f.index[:10], "y"] = np.nan                     # the first 10 rows are all group g0
    t = M.score_table(f, (), 1.0, None, M.RunKind.HEADLINE)
    row = t[(t.column == "arm__a") & (t.rows_basis == "all")].iloc[0]
    assert row["n"] == len(f) - 10 and row["n_unlabelled"] == 10
    assert (t["n_unlabelled"] == 10).all()                # on every line of a pooled-only table
    g = M.score_table(f, ("group",), 1.0, None, M.RunKind.HEADLINE)
    key = g[(g.line == "key") & (g.column == "arm__a") & (g.rows_basis == "all")].set_index("group")
    assert key["n_unlabelled"].to_dict() == {"g0": 10, "g1": 0, "g2": 0, "g3": 0}
    assert (key["n"] + key["n_unlabelled"]).tolist() == f.groupby("group").size().tolist()
    assert (g[g.line != "key"]["n_unlabelled"] == 10).all()   # pooled and macro lines


def test_score_table_marks_placebos_and_scores_their_pre_clip():
    f = _frame()
    t = M.score_table(f, ("group",), 1.0, None, M.RunKind.HEADLINE)
    kinds = t.drop_duplicates("column").set_index("column")["column_kind"].to_dict()
    assert kinds["placebo__pa"] == "placebo" and kinds["arm__a"] == "arm"
    assert kinds["base__guess_normal"] == "baseline"
    assert not [c for c, k in kinds.items() if k == "arm" and not c.startswith("arm__")]
    pooled = t[(t.line == "pooled") & (t.column == "placebo__pa") & (t.rows_basis == "all")].iloc[0]
    assert pooled["mae"] == M.mae(f.y, f.placebo__pa)
    assert pooled["preclip_rate"] == M.preclip_rate(f.pre__pa, LEGAL) and pooled["preclip_n"] == len(f)


@pytest.mark.parametrize("column", ["arm__a", "placebo__pa"])
def test_score_table_refuses_an_arm_or_placebo_missing_on_labelled_rows(column):
    f = _frame()
    v = f[column].to_numpy().copy()
    v[[4, 9]] = np.nan
    info = refused(M.score_table, f.assign(**{column: v}), ("group",), 1.0, None, "smoke",
                   match="missing on 2 labelled rows")
    assert info.rule == "R28"
    y = f["y"].to_numpy().copy()
    y[[4, 9]] = np.nan                                    # missing only where there is no label: fine
    t = M.score_table(f.assign(**{column: v, "y": y}), ("group",), 1.0, None, "smoke")
    assert t["rows_basis"].unique().tolist() == ["all", "base__persistence"]


def test_score_table_refusals():
    f = _frame()
    refused(M.score_table, f.to_dict(), ("group",), 1.0, None, M.RunKind.HEADLINE, match="DataFrame")
    refused(M.score_table, f, "group", 1.0, None, M.RunKind.HEADLINE, match="tuple")
    refused(M.score_table, f, ("group", ""), 1.0, None, M.RunKind.HEADLINE, match="tuple")
    refused(M.score_table, f, ("group", "group"), 1.0, None, M.RunKind.HEADLINE, match="twice")
    refused(M.score_table, f, ("group",), 0.0, None, M.RunKind.HEADLINE, match="above 0")
    refused(M.score_table, f, ("group",), 1.0, -1.0, M.RunKind.HEADLINE, match="above 0")
    refused(M.score_table, f, ("group",), 1.0, None, "final", match="run_kind")
    refused(M.score_table, f.drop(columns=["normal"]), ("group",), 1.0, None, "smoke", match="normal")
    refused(M.score_table, f, ("stratum",), 1.0, None, "smoke", match="stratum")
    scored = [c for c in f.columns if c.startswith(("arm__", "placebo__", "base__"))]
    refused(M.score_table, f.drop(columns=scored), ("group",), 1.0, None, "smoke", match="no scored column")
    refused(M.score_table, f.assign(arm__=1.0), ("group",), 1.0, None, "smoke", match="names no arm")
    refused(M.score_table, f.assign(placebo__=1.0), ("group",), 1.0, None, "smoke", match="names no arm")
    refused(M.score_table, f.assign(pre__zz=1.0), ("group",), 1.0, None, "smoke",
            match="no arm or placebo column")
    refused(M.score_table, f.assign(placebo__a=f["arm__a"]), ("group",), 1.0, None, "smoke",
            match="belongs to both")
    y_inf = f["y"].to_numpy().copy()
    y_inf[3] = INF
    refused(M.score_table, f.assign(y=y_inf), ("group",), 1.0, None, "smoke", match="infinite values")
    b_inf = f["base__persistence"].to_numpy().copy()
    b_inf[5] = INF
    refused(M.score_table, f.assign(base__persistence=b_inf), ("group",), 1.0, None, "smoke",
            match="baseline 'base__persistence' holds 1 infinite")
    refused(M.score_table, f.drop(columns=["legal_max"]), ("group",), 1.0, None, "smoke",
            match="legal range columns")
    lm = f["legal_max"].to_numpy().copy()
    lm[0] = 5.0
    refused(M.score_table, f.assign(legal_max=lm), ("group",), 1.0, None, "smoke", match="one value per run")
    g = f["group"].to_numpy().astype(object)
    g[0] = None
    refused(M.score_table, f.assign(group=g), ("group",), 1.0, None, "smoke", match="missing on")
    nn = f["normal"].to_numpy().copy()
    nn[0] = np.nan
    refused(M.score_table, f.assign(normal=nn), ("group",), 1.0, None, "smoke", match="everywhere or nowhere")
    pre_nan = f["pre__a"].to_numpy().copy()
    pre_nan[0] = np.nan
    refused(M.score_table, f.assign(pre__a=pre_nan), ("group",), 1.0, None, "smoke", match="missing values")


def test_score_table_serves_legacy_rows_without_pre_clip_or_legal_range():
    f = _frame().drop(columns=["pre__a", "pre__b", "pre__pa", "legal_min", "legal_max", "lead", "issue"])
    t = M.score_table(f, ("group",), 1.0, None, M.RunKind.LEGACY)
    assert np.isnan(t["preclip_rate"]).all() and set(t["run_kind"]) == {"legacy"}


def test_metric_by_key():
    t = M.score_table(_frame(), ("group",), 1.0, None, M.RunKind.HEADLINE)
    got = M.metric_by_key(t, "arm__a", "mae", "group")
    assert sorted(got) == ["g0", "g1", "g2", "g3"]
    refused(M.metric_by_key, t, "arm__a", "nope", "group", match="no column 'nope'")
    refused(M.metric_by_key, t, "arm__zz", "mae", "group", match="no key line")
    multi = M.score_table(_frame(), ("group", "year"), 1.0, None, M.RunKind.HEADLINE)
    refused(M.metric_by_key, multi, "arm__a", "mae", "group", match="twice")
    refused(M.metric_by_key, t.drop(columns=["rows_missing"]), "arm__a", "mae", "group",
            match="no column 'rows_missing'")


def test_metric_by_key_never_hands_out_maes_over_different_rows():
    """A baseline missing on some rows is refused on the 'all' basis (its per-group MAE there is
    over fewer rows than an arm's, so a contrast would not be paired); on its own basis every column
    is over the same rows and the contrast is paired."""
    f = _frame()
    t = M.score_table(f, ("group",), 1.0, None, M.RunKind.HEADLINE)
    info = refused(M.metric_by_key, t, "base__persistence", "mae", "group", match="fewer rows")
    assert "rows_basis='base__persistence'" in info.fix
    own = M.metric_by_key(t, "base__persistence", "mae", "group", rows_basis="base__persistence")
    arm = M.metric_by_key(t, "arm__a", "mae", "group", rows_basis="base__persistence")
    have = f["base__persistence"].notna() & f["y"].notna()
    for g in own:
        rows = f[have & (f.group == g)]
        assert own[g] == M.mae(rows.y, rows.base__persistence) and arm[g] == M.mae(rows.y, rows.arm__a)
    band, records = M.band_from_pairs({"p": own, "a": arm}, [("p", "a")])
    assert records[0]["n_groups"] == 4 and np.isfinite(band)


# ---------------------------------------------------------------------------------------------------
# writers
def test_rows_round_trip_write_once(tmp_path):
    f = _frame()
    path = tmp_path / "test_preds.parquet"
    assert M.write_rows_once(f, path) == os.fspath(path)
    back = M.read_rows(path)
    pd.testing.assert_frame_equal(back, f)
    with pytest.raises(AtomicWriteError, match="refusing to overwrite"):
        M.write_rows_once(f, path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["test_preds.parquet"]


def test_write_rows_refuses_frames_assemble_rows_did_not_build(tmp_path):
    f = _frame()
    refused(M.write_rows_once, f.to_dict(), tmp_path / "x.parquet", match="DataFrame")
    refused(M.write_rows_once, f.drop(columns=["issue"]), tmp_path / "x.parquet", match="lack the columns")
    arms = [c for c in f.columns if c.startswith(("arm__", "pre__"))]
    refused(M.write_rows_once, f.drop(columns=arms), tmp_path / "x.parquet", match="no arm")
    refused(M.write_rows_once, f.drop(columns=["pre__b"]), tmp_path / "x.parquet", match="pre-clip column")
    refused(M.write_rows_once, f.drop(columns=["pre__pa"]), tmp_path / "x.parquet", match="pre-clip column")
    refused(M.write_rows_once, f.iloc[:0], tmp_path / "x.parquet", match="no row")
    twice = pd.concat([f, f[["y"]]], axis=1)
    refused(M.write_rows_once, twice, tmp_path / "x.parquet", match="column twice")
    assert list(tmp_path.iterdir()) == []


def _with(f, column, rows, value):
    v = f[column].to_numpy().copy()
    v[rows] = value
    return f.assign(**{column: v})


def test_write_rows_reruns_every_assemble_rows_check(tmp_path):
    """The docstring's promise: a frame assemble_rows would refuse to build is refused, whatever its
    column names say (finiteness, clip equality, legal range, keys, duplicates, the lead)."""
    f = _frame()
    out = tmp_path / "x.parquet"

    def bad(frame, match):
        refused(M.write_rows_once, frame, out, match=match)

    bad(_with(f, "arm__a", [3], np.nan), "arm 'a': 1 predictions are not their pre-clip value clipped")
    bad(_with(f, "arm__a", [3], f["arm__a"].iloc[3] + 0.5), "arm 'a': 1 predictions")
    bad(_with(f, "placebo__pa", [0, 1], np.nan), "placebo 'pa': 2 predictions")
    bad(_with(f, "pre__b", [2], np.inf), "pre-clip values are not finite")
    bad(_with(f, "base__guess_normal", [0], -1.0), "outside the legal range")
    bad(_with(f, "base__persistence", [1], np.inf), "infinite")
    bad(_with(f, "y", [0], np.inf), "infinite")
    bad(_with(f, "legal_max", [0], 50.0), "legal_max is not one value")
    bad(_with(f, "normal", [0], np.nan), "everywhere or nowhere")
    bad(_with(f.assign(issue=f["issue"].astype(float)), "issue", [0], 1.5), "whole numbers")
    bad(f.assign(time=f["time"].iloc[0]), "repeat a (unit, time) key")
    g = f["group"].to_numpy().astype(object)
    g[0] = None
    bad(f.assign(group=g), "key 'group' is missing")
    bad(_with(f.assign(lead=f["lead"].astype(float)), "lead", [0], np.nan), "lead is missing")
    bad(f.assign(lead=-1), "whole number at or above 0")
    assert list(tmp_path.iterdir()) == []


def test_write_rows_accepts_several_leads_checked_one_by_one(tmp_path):
    f0 = _frame()
    f1 = _frame(lead=1, issue=_frame()["time"].to_numpy() - 1)
    both = pd.concat([f0, f1], ignore_index=True)       # (unit, time) repeats across leads only
    path = M.write_rows_once(both, tmp_path / "all_leads.parquet")
    pd.testing.assert_frame_equal(M.read_rows(path), both)
    lm = both["legal_max"].to_numpy().copy()
    lm[len(f0):] = 50.0                                  # one legal range per LEAD is enough
    scored = [c for c in both.columns if c.startswith(("arm__", "placebo__", "pre__", "base__"))]
    assert float(both[scored].max().max()) < 50.0        # so no value needs a new clip
    M.write_rows_once(both.assign(legal_max=lm), tmp_path / "per_lead_range.parquet")
    bad = both.copy()
    bad.loc[len(f0), "arm__a"] = bad.loc[len(f0), "arm__a"] + 1.0
    refused(M.write_rows_once, bad, tmp_path / "x.parquet", match="arm 'a': 1 predictions")


def test_write_rows_fsyncs_the_temp_file_before_publishing(tmp_path, monkeypatch):
    path = tmp_path / "test_preds.parquet"
    seen = []
    real_fsync = os.fsync

    def spy(fd):
        seen.append((fd, path.exists(), [p.name for p in tmp_path.iterdir()]))
        real_fsync(fd)

    monkeypatch.setattr(M.os, "fsync", spy)
    M.write_rows_once(_frame(), path)
    assert len(seen) == 1
    fd, published, names = seen[0]
    assert not published and len(names) == 1 and names[0].startswith("test_preds.parquet.tmp-")
    assert path.is_file() and [p.name for p in tmp_path.iterdir()] == ["test_preds.parquet"]


def test_write_rows_cleans_its_temp_file_when_the_write_fails(tmp_path, monkeypatch):
    def boom(self, fh, **kwargs):
        fh.write(b"partial")
        raise OSError("disk full")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", boom)
    with pytest.raises(OSError, match="disk full"):
        M.write_rows_once(_frame(), tmp_path / "x.parquet")
    assert list(tmp_path.iterdir()) == []


def test_write_rows_cleans_its_temp_file_when_fsync_fails(tmp_path, monkeypatch):
    def broken(fd):
        raise OSError("fsync failed")

    monkeypatch.setattr(M.os, "fsync", broken)
    with pytest.raises(OSError, match="fsync failed"):
        M.write_rows_once(_frame(), tmp_path / "x.parquet")
    assert list(tmp_path.iterdir()) == []


def test_publish_once_refuses_an_existing_target_and_retries_sharing(tmp_path, monkeypatch):
    target = tmp_path / "t.bin"
    target.write_bytes(b"old")
    tmp = tmp_path / "t.bin.tmp"
    tmp.write_bytes(b"new")
    with pytest.raises(AtomicWriteError, match="appeared during the write"):
        M._publish_once(os.fspath(tmp), os.fspath(target))
    assert target.read_bytes() == b"old" and not tmp.exists()
    # a reader holding the target open: every attempt gets PermissionError, then a loud failure
    tmp.write_bytes(b"new")
    monkeypatch.setattr(M.atomic, "RENAME_ATTEMPTS", 3)
    monkeypatch.setattr(M.atomic, "RENAME_WAIT_S", 0.0)

    def locked(src, dst):
        raise PermissionError("held open")

    monkeypatch.setattr(M.os, "rename", locked)
    monkeypatch.setattr(M.os, "link", locked)
    with pytest.raises(AtomicWriteError, match="failed 3 times"):
        M._publish_once(os.fspath(tmp), os.fspath(tmp_path / "fresh.bin"))
    assert not tmp.exists()


def test_publish_once_link_branch(tmp_path, monkeypatch):
    tmp = tmp_path / "a.tmp"
    tmp.write_bytes(b"x")
    monkeypatch.setattr(M.os, "name", "posix")
    try:
        M._publish_once(os.fspath(tmp), os.fspath(tmp_path / "a.bin"))
    finally:
        monkeypatch.undo()
    assert (tmp_path / "a.bin").read_bytes() == b"x" and not tmp.exists()


def test_write_table_and_json_records(tmp_path):
    t = M.score_table(_frame(), ("group",), 1.0, None, M.RunKind.HEADLINE)
    p = M.write_table_once(t, tmp_path / "per_group.csv")
    back = pd.read_csv(p)
    assert len(back) == len(t) and back["mae"].tolist() == pytest.approx(t["mae"].tolist(), nan_ok=True)
    with pytest.raises(AtomicWriteError):
        M.write_table_once(t, tmp_path / "per_group.csv")
    refused(M.write_table_once, {"a": 1}, tmp_path / "x.csv", match="DataFrame")
    ref = {"a": 2.0, "b": 2.5}
    adopted = {"a": 1.5, "b": 2.4}
    v = M.single_verdict(ref, adopted, 2.25, 1.95, 0.05, False, M.REFERENCE_OWN_LINK_TREES_OFF)
    rec = M.verdict_record(v)
    assert rec["tag"] == "cannot_tell" and rec["contrast"]["se"] is None and rec["contrast"]["n_groups"] == 2
    assert rec["sign_flip_groups"] == [] and rec["groups_better"] == 2
    path = M.write_json_once({"verdict": rec, "band": 0.05, "flag": np.bool_(True), "n": np.int64(3),
                              "x": np.float32(float("nan")), "tag": M.VerdictTag.HELPS,
                              "det": M.DetectionScore(float("nan"), 3, 0.1)}, tmp_path / "verdict.json")
    data = json.loads(open(path, encoding="utf-8").read())
    assert data["verdict"]["tag"] == "cannot_tell" and data["flag"] is True and data["x"] is None
    assert data["tag"] == "helps" and data["det"] == {"score": None, "n_events": 3, "event_share": 0.1}
    refused(M.verdict_record, {"tag": "x"}, match="VerdictResult")
    refused(M.write_json_once, [1], tmp_path / "y.json", match="mapping")
