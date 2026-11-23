"""GATE: the engine metrics reproduce Part 558's logged scores and verdict tags from its SAVED rows.

Part 558 (the PM2.5 uniform-schema run, D:/pm25_adapt/u2) saved every test row with 13 arms
(predictions.parquet), its per-region and per-year tables, verdict.json and run.log. Everything here is
READ-ONLY: the files are opened for reading and nothing is written anywhere.

What must hold:
  - pooled MAE / anomaly R2 / hit (+-2, the old absolute tolerance, now the declared measurement
    floor) of all 13 arms equal verdict.json exactly and the run.log print to its 4 / 4 / 3 decimals
    (e.g. log_corrector 4.1002 / +0.0901 / 0.496); guess-normal's mae0 / hit0 likewise;
  - every region's and every year's MAE / anomaly R2 / hit equal per_region.csv and per_year.csv;
  - each logged contrast's jackknife (mean, interval, SE), pooled contrast and region count equal the
    log, and the N3 band derived from those SEs equals eq_band_derived;
  - the headline verdict (log_corrector vs log_treesoff) and the D75 band are pinned to 1e-12, with
    the tag of every D75 contrast at the old band and at the D75 band (what widening the band does);
  - the verdict tags: the engine's ONE tag rule is the R5 rule the owner ruled (D74) with the band
    checked first (F42). Five of the six logged tags come out the same. The sixth, 'log(y+c) vs
    log1p', was HURTS under the shipped four-outcome rule; its interval [-0.0060, -0.0019] lies
    wholly inside +-0.0395 and its point estimate (-0.0040) is inside the band, so R5 reads it
    EQUIVALENT ("certain but negligible", the case pm25_forecast.py:327-329 names). The test proves
    the interval is identical and that the shipped rule applied to it still says HURTS, so the only
    difference is the ruled rule.
Skipped when the saved run is not on this machine.
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from treeroute import engine_constants as K
from treeroute.report import metrics as M

RUN = Path("D:/pm25_adapt/u2")
FILES = ("predictions.parquet", "per_region.csv", "per_year.csv", "verdict.json", "run.log")
TOL = 2.0                     # pm25_adaptation.py:144 HIT_TOL, the old absolute tolerance (a floor now)
BAND = 0.0395                 # pm25_adaptation.py:132 EQ_UGM3, the band in use in Part 558
LEGAL = (0.0, float("inf"))
ARMS = ("base_inherited", "base", "log", "logc", "treesoff", "log_treesoff", "logc_treesoff",
        "corrector", "log_corrector", "logc_corrector", "placebo", "log_placebo", "logc_placebo")
PLACEBOS = ("placebo", "log_placebo", "logc_placebo")      # saved under the placebo prefix (R24)
EXACT = 1e-12


def col(arm):
    """The saved-row column of a Part 558 arm."""
    return ("placebo__" if arm in PLACEBOS else "arm__") + arm

pytestmark = pytest.mark.skipif(not all((RUN / f).is_file() for f in FILES),
                                reason="Part 558's saved run (D:/pm25_adapt/u2) is not on this machine")


@pytest.fixture(scope="module")
def saved():
    preds = pd.read_parquet(RUN / "predictions.parquet")
    region = pd.read_csv(RUN / "per_region.csv")
    year = pd.read_csv(RUN / "per_year.csv")
    with open(RUN / "verdict.json", encoding="utf-8") as fh:
        verdict = json.load(fh)
    log = (RUN / "run.log").read_text(encoding="utf-8")
    return {"preds": preds, "region": region, "year": year, "verdict": verdict, "log": log}


@pytest.fixture(scope="module")
def frame(saved):
    """Part 558's rows in the engine's saved-row schema (legacy: no pre-clip values were saved)."""
    d = saved["preds"]
    f = pd.DataFrame({"unit": d.cell_id.to_numpy(), "group": d.reg.to_numpy(),
                      "time": (d.year * 12 + d.month).to_numpy(), "year": d.year.to_numpy(),
                      "y": d.y.to_numpy(), "normal": d.clim.to_numpy()})
    for arm in ARMS:
        f[col(arm)] = d["p_" + arm].to_numpy()
    f["base__guess_normal"] = M.baseline_guess_normal(d.clim.to_numpy(), LEGAL)
    return f


@pytest.fixture(scope="module")
def tables(frame):
    return {by: M.score_table(frame, by, TOL, TOL, M.RunKind.LEGACY) for by in ((), ("group",), ("year",))}


def _pooled(table, column):
    sel = table[(table.line == "pooled") & (table.column == column) & (table.rows_basis == "all")]
    assert len(sel) == 1
    return sel.iloc[0]


def test_saved_rows_are_what_the_gate_assumes(saved, frame):
    d = saved["preds"]
    assert len(d) == saved["verdict"]["rows"]["scored"] == 95856
    assert set(d.adopted) == {"log_corrector"} and d.reg.nunique() == 20
    assert not frame.isna().any().any()
    assert not frame.duplicated(["unit", "time"]).any()


def test_pooled_scores_equal_verdict_json_exactly(saved, tables):
    test = saved["verdict"]["test"]
    for arm in ARMS:
        row = _pooled(tables[()], col(arm))
        assert row["n"] == test[arm]["n"]
        assert abs(row["mae"] - test[arm]["mae"]) <= EXACT, arm
        assert abs(row["anom_r2"] - test[arm]["r2"]) <= EXACT, arm
        assert abs(row["hit_floor"] - test[arm]["hit"]) <= EXACT, arm
    kinds = tables[()].drop_duplicates("column").set_index("column")["column_kind"]
    assert sorted(kinds[kinds == "placebo"].index) == sorted("placebo__" + a for a in PLACEBOS)
    assert len(kinds[kinds == "arm"]) == len(ARMS) - len(PLACEBOS)
    gn = _pooled(tables[()], "base__guess_normal")
    assert abs(gn["mae"] - test["base"]["mae0"]) <= EXACT
    assert abs(gn["hit_floor"] - test["base"]["hit0"]) <= EXACT
    assert gn["anom_r2"] == 0.0


def test_pooled_scores_print_as_the_run_log(saved, tables):
    pat = re.compile(r"TEST (\S+)\s+MAE ([\d.]+)\s+anomR2 ([+-][\d.]+)\s+patR2 \S+\s+hit ([\d.]+)")
    logged = {m.group(1): m.groups()[1:] for m in pat.finditer(saved["log"])}
    assert sorted(logged) == sorted(ARMS)
    for arm, (mae_s, r2_s, hit_s) in logged.items():
        row = _pooled(tables[()], col(arm))
        assert "%.4f" % row["mae"] == mae_s, arm
        assert "%+.4f" % row["anom_r2"] == r2_s, arm
        assert "%.3f" % row["hit_floor"] == hit_s, arm
    head = _pooled(tables[()], "arm__log_corrector")
    assert ("%.4f" % head["mae"], "%+.4f" % head["anom_r2"], "%.3f" % head["hit_floor"]) == \
        ("4.1002", "+0.0901", "0.496")


@pytest.mark.parametrize("by,csv,key", [(("group",), "region", "reg"), (("year",), "year", "year")])
def test_every_region_and_year_equals_the_saved_tables(saved, tables, by, csv, key):
    ref = saved[csv].set_index(key)
    t = tables[by]
    for arm in ARMS:
        lines = t[(t.line == "key") & (t.column == col(arm)) & (t.rows_basis == "all")].set_index(by[0])
        assert sorted(lines.index.tolist()) == sorted(ref.index.tolist())
        for k in ref.index:
            assert lines.loc[k, "n"] == ref.loc[k, "n"]
            assert abs(lines.loc[k, "mae"] - ref.loc[k, arm + "_mae"]) <= EXACT, (arm, k)
            assert abs(lines.loc[k, "anom_r2"] - ref.loc[k, arm + "_r2"]) <= EXACT, (arm, k)
            assert abs(lines.loc[k, "hit_floor"] - ref.loc[k, arm + "_hit"]) <= EXACT, (arm, k)
    gn = t[(t.line == "key") & (t.column == "base__guess_normal") & (t.rows_basis == "all")].set_index(by[0])
    for k in ref.index:
        assert abs(gn.loc[k, "mae"] - ref.loc[k, "mae0"]) <= EXACT
        assert abs(gn.loc[k, "hit_floor"] - ref.loc[k, "hit0"]) <= EXACT


def _four_outcome_tag(dv, lo, hi):
    """The SHIPPED four-outcome rule (pm25_adaptation.py:1104-1115), kept here only to show that the
    one tag that changed changed by the ruled rule, not by the numbers."""
    if len(dv) and np.allclose(dv, 0.0, atol=1e-12):
        return "IDENTICAL"
    if not np.isfinite(lo):
        return "CANNOT TELL"
    if lo > 0:
        return "HELPS"
    if hi < 0:
        return "HURTS"
    if -BAND <= lo and hi <= BAND:
        return "DOES NOT HELP (equivalent)"
    return "CANNOT TELL"


ENGINE_TAG = {"HELPS": M.VerdictTag.HELPS, "HURTS": M.VerdictTag.HURTS,
              "CANNOT TELL": M.VerdictTag.CANNOT_TELL, "IDENTICAL": M.VerdictTag.IDENTICAL,
              "DOES NOT HELP (equivalent)": M.VerdictTag.EQUIVALENT}
RULED_CHANGE = {"log(y+c) vs log1p": M.VerdictTag.EQUIVALENT}   # shipped HURTS; R5 (D74) with the band first


def test_contrasts_their_jackknife_and_the_verdict_tags(saved, tables):
    per_group = tables[("group",)]
    contrasts = saved["verdict"]["contrasts"]
    assert len(contrasts) == 6
    line = re.compile(r"^\[[\d:]+\][ \t]+(\S.*?)[ \t]{2,}\S+[ \t]+over \S+[ \t]+MAE saved [+-][\d.]+[ \t]+"
                      r"jackknife 95% \[[+-][\d.]+, [+-][\d.]+\][ \t]+.+?[ \t]+\(pooled ([+-][\d.]+); "
                      r"(\d+)/(\d+) regions\)", re.M)
    logged = {m.group(1).strip(): m.groups()[1:] for m in line.finditer(saved["log"])}
    assert sorted(logged) == sorted(contrasts)
    ses = []
    for label, c in contrasts.items():
        ref = M.metric_by_key(per_group, col(c["ref"]), "mae", "group")
        arm = M.metric_by_key(per_group, col(c["arm"]), "mae", "group")
        dv = np.array([ref[g] - arm[g] for g in sorted(ref)])
        tag, jk = M.contrast_tag(dv, BAND)
        assert abs(jk.mean - c["mean"]) <= EXACT and abs(jk.se - c["se"]) <= EXACT, label
        assert abs(jk.low - c["lo"]) <= EXACT and abs(jk.high - c["hi"]) <= EXACT, label
        pooled = _pooled(tables[()], col(c["ref"]))["mae"] - _pooled(tables[()], col(c["arm"]))["mae"]
        pooled_s, better_s, n_s = logged[label]
        assert "%+.4f" % pooled == pooled_s and int((dv > 0).sum()) == int(better_s) and jk.n_groups == int(n_s)
        assert _four_outcome_tag(dv, jk.low, jk.high) == c["verdict"], label   # same numbers, shipped rule
        want = RULED_CHANGE.get(label, ENGINE_TAG[c["verdict"]])
        assert tag is want, (label, tag, c["verdict"])
        ses.append(jk.se)
    # N3 (pm25_adaptation.py:1121-1125): the median jackknife SE of the non-identical contrasts
    assert abs(M.equivalence_band(ses) - saved["verdict"]["eq_band_derived"]) <= EXACT


# The headline verdict and the D75 band on Part 558's rows, pinned (new numbers: no logged counterpart).
HEADLINE = {"mean": 0.2704855514994937, "low": 0.11995897614316137, "high": 0.42101212685582606,
            "se": 0.07679927314098589}
HEADLINE_FLIPS = ("atlantic_forest_brazil", "kazakh_steppe", "western_ghats")
D75_BAND = 0.07586159074213324
# D75's set: each tree arm vs its own trees-off, each corrector vs its placebo (reference, arm)
D75_PAIRS = ([("treesoff", "base"), ("log_treesoff", "log"), ("logc_treesoff", "logc"),
              ("treesoff", "corrector"), ("log_treesoff", "log_corrector"), ("logc_treesoff", "logc_corrector")]
             + [("placebo", "corrector"), ("log_placebo", "log_corrector"), ("logc_placebo", "logc_corrector")])
T = M.VerdictTag
# the tag of each D75 contrast at the band in use (0.0395) and at the D75 band (0.0759)
D75_TAGS = {("treesoff", "base"): (T.HELPS, T.HELPS),
            ("log_treesoff", "log"): (T.HELPS, T.HELPS),
            ("logc_treesoff", "logc"): (T.HELPS, T.HELPS),
            ("treesoff", "corrector"): (T.CANNOT_TELL, T.CANNOT_TELL),
            ("log_treesoff", "log_corrector"): (T.HELPS, T.HELPS),
            ("logc_treesoff", "logc_corrector"): (T.HELPS, T.HELPS),
            ("placebo", "corrector"): (T.CANNOT_TELL, T.EQUIVALENT),
            ("log_placebo", "log_corrector"): (T.EQUIVALENT, T.EQUIVALENT),
            ("logc_placebo", "logc_corrector"): (T.EQUIVALENT, T.EQUIVALENT)}


@pytest.fixture(scope="module")
def per_group_mae(tables):
    return {arm: M.metric_by_key(tables[("group",)], col(arm), "mae", "group") for arm in ARMS}


def test_headline_verdict_decomposition_and_region_counts(saved, tables, per_group_mae):
    """The ONE verdict of the adopted arm against its own link-matched trees-off (F47), pinned, with the
    logged decomposition and region counts."""
    mae = per_group_mae
    pooled = {arm: _pooled(tables[()], col(arm))["mae"] for arm in ARMS}
    dec = saved["verdict"]["decomposition"]["test"]
    assert abs((pooled["treesoff"] - pooled["log_treesoff"]) - dec["normal_effect"]) <= EXACT
    assert abs((pooled["log_treesoff"] - pooled["log_corrector"]) - dec["routing_effect"]) <= EXACT
    for band in (BAND, D75_BAND):
        v = M.single_verdict(mae["log_treesoff"], mae["log_corrector"], pooled["log_treesoff"],
                             pooled["log_corrector"], band, False, M.REFERENCE_OWN_LINK_TREES_OFF)
        assert v.tag is T.HELPS and v.band == band
        for field, want in HEADLINE.items():
            assert abs(getattr(v.contrast, field) - want) <= EXACT, field
        assert v.contrast.n_groups == 20 and v.groups_better == 17
        assert v.sign_flip_groups == HEADLINE_FLIPS
        assert v.pooled_contrast == pooled["log_treesoff"] - pooled["log_corrector"]
        assert abs(v.pooled_contrast - dec["routing_effect"]) <= EXACT
    gn = M.metric_by_key(tables[("group",)], "base__guess_normal", "mae", "group")
    assert sum(mae["base"][g] < gn[g] for g in gn) == 13          # run.log: base beats guess-normal in 13
    assert sum(mae["log_corrector"][g] < gn[g] for g in gn) == 17  # ... log_corrector beats it in 17


def test_d75_band_and_what_widening_the_band_does(per_group_mae):
    """The D75 band is 0.0759 (vs 0.0395 in use). What it changes on these rows: no HELPS or HURTS
    tag; EQUIVALENT becomes unreachable for every tree-arm-vs-trees-off contrast (1.96 x SE exceeds
    the band), and 'corrector vs its placebo' moves from CANNOT TELL to EQUIVALENT. The band can bind
    HELPS only where 1.96 x SE is below it: the placebo contrasts (SE about 0.013), none of which is
    positive here."""
    band, records = M.band_from_pairs(per_group_mae, D75_PAIRS)
    assert abs(band - D75_BAND) <= EXACT and len(records) == 9
    assert not any(r["identical"] for r in records)
    assert abs(band - float(np.median([r["se"] for r in records]))) <= EXACT
    for (ref, arm), rec in zip(D75_PAIRS, records):
        assert (rec["reference"], rec["arm"]) == (ref, arm)
        dv = np.array([per_group_mae[ref][g] - per_group_mae[arm][g] for g in sorted(per_group_mae[ref])])
        tags = (M.contrast_tag(dv, BAND)[0], M.contrast_tag(dv, band)[0])
        assert tags == D75_TAGS[(ref, arm)], (ref, arm, tags)
        if ref.endswith("treesoff"):
            assert K.JACKKNIFE_Z * rec["se"] > band        # EQUIVALENT out of reach
        else:
            assert K.JACKKNIFE_Z * rec["se"] < band        # the band could bind HELPS here
            assert rec["mean"] < 0                                   # ... but no corrector beats its placebo
