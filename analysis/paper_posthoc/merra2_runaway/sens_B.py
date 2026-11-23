"""sens_B.py -- POST-HOC sensitivity of the PM2.5 published rival merra2_lag1 (implementer B).

Run:  py -3.9 -I "D:/treeroute/analysis/paper_posthoc/merra2_runaway/sens_B.py"

What it does (all numbers are post hoc; the board's verdict is not changed):
  0. Reproduces the board's deciding contrast (guarded_vs_headline, lead 0) from the saved row-level files:
     same rows (covered rows of groups with >= 10 covered rows; scored where y and the forecast are finite),
     same per-group MAEs, d = rival MAE - our MAE per group, the same leave-one-group-out jackknife at 1.96,
     the same band and tag rule. Refuses (fail loud) unless the board's numbers are reproduced.
  1. Finds the largest rival forecast (the "runaway") and reports where and when it is.
  2. Recomputes the contrast with that one row removed from BOTH sides.
  3. Recomputes the contrast with the rival forecast clipped to the largest label of the rival's own
     training rows (the refit rows of the board's slim lead-0 set, the rows its map was fitted on).
  4. Counts rival forecasts above 1,000 ug/m3.

Reads only (column-selected): the board's preds/guard/scores/csv/json files, the headline run's saved test rows
(labels the board already opened), its verdict.json and derived.json, the rivals table, the merra2_lag1 index
(a few rows), the slim refit-row labels, the engine's unit-centre table, and the engine's metrics module (as a
cross-check of the jackknife and tag). Writes ONLY sens_B.json beside this script.
"""
import sys

sys.dont_write_bytecode = True          # the engine import below must leave no .pyc behind

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
import pyarrow.parquet as pq

# ------------------------------------------------------------------------------------------------ inputs
BOARD = Path(r"D:/treeroute/rivals_human/pm25/20261007_74e67609")
RUN = Path(r"D:/treeroute/runs/pm25/headline/20261007_74e67609")
TABLE = Path(r"D:/treeroute/rivals_table/20261025T162302876402Z/RIVALS_TABLE.csv")
INDEX = Path(r"D:/treeroute/human_index/pm25/20261007_74e67609/merra2_lag1/lead_0.parquet")
STATIC = Path(r"C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/datasets/pm25/data/static/part-0.parquet")
ENGINE = Path(r"C:/Users/moh the ghost/Desktop/data set for reserch paper/engine")
OUT = Path(__file__).resolve().parent / "sens_B.json"

RIVAL = "merra2_lag1"
LEAD = 0
CONTRAST = "guarded_vs_headline"
MIN_GROUP_TEST_ROWS = 10        # board constants.min_group_test_rows
Z = 1.96                        # engine JACKKNIFE_Z (checked against the engine below)
IDENTICAL_ATOL = 1e-12          # engine metrics.IDENTICAL_ATOL (checked below)
THRESH = 1000.0                 # ug/m3, task item 4
REPRO_TOL = 1e-9                # largest |difference| accepted when reproducing the board (CSV round trip)
VERDICT_WORDS = {"helps": "BEATS", "hurts": "LOSES", "does_not_help_equivalent": "EQUIVALENT",
                 "cannot_tell": "CANNOT TELL", "identical": "IDENTICAL"}


def refuse(msg):
    raise SystemExit("REFUSED: " + msg)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def year_month(step):
    """Engine D28: monthly step = year x 12 + month (1 not subtracted)."""
    s = int(step)
    return (s - 1) // 12, (s - 1) % 12 + 1


# ------------------------------------------------------------------------------------------------ the rule
def per_group_mae(frame, col):
    """{group: (MAE, n)} -- score_table's key lines on rows basis 'all': rows where y and the column are finite,
    the group's rows in saved order, MAE = mean |y - p| (metrics.mae)."""
    y = frame["y"].to_numpy(np.float64)
    p = frame[col].to_numpy(np.float64)
    if np.isinf(y).any() or np.isinf(p).any():
        refuse("an infinite value in y or %s" % col)
    out = {}
    for g, idx in sorted(frame.groupby("group", sort=True).indices.items(), key=lambda kv: str(kv[0])):
        idx = np.asarray(idx)
        rows = idx[np.isfinite(y[idx]) & np.isfinite(p[idx])]
        if not rows.size:
            refuse("group %s has no scored row for %s" % (g, col))
        if (np.isfinite(y[idx]) & ~np.isfinite(p[idx])).any():
            refuse("arm %s is missing on a labelled row of group %s" % (col, g))
        out[str(g)] = (float(np.mean(np.abs(y[rows] - p[rows]))), int(rows.size))
    return out


def pooled_mae(frame, col):
    y = frame["y"].to_numpy(np.float64)
    p = frame[col].to_numpy(np.float64)
    ok = np.isfinite(y) & np.isfinite(p)
    return float(np.mean(np.abs(y[ok] - p[ok]))), int(ok.sum())


def jackknife(v):
    """metrics.group_jackknife: mean of the per-group values; leave-one-out means; SE = sqrt((n-1)/n x sum of
    squared deviations of the LOO means from their mean); mean +/- 1.96 SE."""
    v = np.asarray(v, dtype=np.float64)
    n = int(v.size)
    jk = np.array([np.delete(v, i).mean() for i in range(n)])
    se = float(np.sqrt((n - 1) / n * ((jk - jk.mean()) ** 2).sum()))
    mean = float(v.mean())
    return {"mean": mean, "se": se, "low": float(mean - Z * se), "high": float(mean + Z * se), "n_groups": n}


def tag_of(dv, jk, band):
    """metrics.contrast_tag (R5 rule, D74/F42)."""
    if np.all(np.abs(dv) <= IDENTICAL_ATOL):
        return "identical"
    if not (math.isfinite(jk["low"]) and math.isfinite(jk["high"])):
        return "cannot_tell"
    if -band <= jk["low"] and jk["high"] <= band:
        return "does_not_help_equivalent"
    if jk["low"] > 0 and jk["mean"] >= band:
        return "helps"
    if jk["high"] < 0 and jk["mean"] <= -band:
        return "hurts"
    return "cannot_tell"


def contrast(frame, rcol, ocol, band, block_of_group):
    rmap, omap = per_group_mae(frame, rcol), per_group_mae(frame, ocol)
    if set(rmap) != set(omap):
        refuse("the two MAE maps hold different groups")
    groups = sorted(rmap)
    dv = np.array([rmap[g][0] - omap[g][0] for g in groups])
    jk = jackknife(dv)
    tag = tag_of(dv, jk, band)
    members = {}
    for g, d in zip(groups, dv.tolist()):                  # report-only blocked jackknife (R14 overlap blocks)
        members.setdefault(int(block_of_group[g]), []).append(float(d))
    bj = jackknife(np.array([float(np.mean(members[b])) for b in sorted(members)]))
    pr, nr = pooled_mae(frame, rcol)
    po, no = pooled_mae(frame, ocol)
    if nr != no:
        refuse("pooled rows differ between arms")
    return {"verdict": VERDICT_WORDS[tag], "tag": tag, "d_mean": jk["mean"], "d_se": jk["se"],
            "d_low": jk["low"], "d_high": jk["high"], "n_groups": jk["n_groups"],
            "blocked_mean_report_only": bj["mean"], "blocked_se_report_only": bj["se"], "n_blocks": bj["n_groups"],
            "rival_mae_pooled": pr, "ours_mae_pooled_same_rows": po, "scored_rows": nr,
            "groups_rival_worse": int((dv > 0).sum()), "groups_rival_better": int((dv < 0).sum()),
            "_dv": dv, "_groups": groups, "_rmap": rmap, "_omap": omap}


def public(res):
    return {k: v for k, v in res.items() if not k.startswith("_")}


# ------------------------------------------------------------------------------------------------ main
def main():
    report = {"what": "POST-HOC sensitivity of the PM2.5 published rival merra2_lag1 (human rival, tier P), deciding "
                      "contrast guarded_vs_headline at lead 0; implementer B. Post hoc: the board's verdict "
                      "(CANNOT TELL) stands; these numbers are sensitivities, not verdicts.",
              "inputs": {}}

    # --- run facts: headline column, band, legal range, overlap blocks
    verdict = read_json(RUN / "verdict.json")
    derived = read_json(RUN / "derived.json")
    band = float(verdict["band"])
    if verdict.get("declined"):
        refuse("the headline run declined; this script reads the adopted arm only")
    headline = "arm__" + verdict["adopted"]
    if verdict.get("adopted_column") not in (None, headline):
        refuse("verdict adopted_column differs from the headline column")
    legal = derived["R28"]["value"]
    block_of_group = derived["R14:overlap_blocks"]["value"]["block_of_group"]

    # --- the board's own records, and file integrity
    done = read_json(BOARD / "lead_0" / ("done_%s.json" % RIVAL))
    opened = read_json(BOARD / ("test_labels_opened_human_lead_%d.json" % LEAD))
    picks = read_json(BOARD / "human_picks.json")["picks"][RIVAL]
    preds_p = BOARD / "lead_0" / ("preds_%s.parquet" % RIVAL)
    test_p = Path(opened["file"])
    if sha256(preds_p) != done["preds_sha256"]:
        refuse("%s changed after the board's refit" % preds_p)
    if sha256(test_p) != opened["test_preds_sha256"]:
        refuse("%s differs from the file the board opened" % test_p)
    if done["status"] != "ok" or not done["guard"]["passed"]:
        refuse("the board's refit record is not ok/guard-passed; guarded would be the fallback")
    report["inputs"] = {
        "board_run": str(BOARD), "preds_file": str(preds_p), "preds_sha256": done["preds_sha256"],
        "test_rows_file": str(test_p), "test_rows_sha256": opened["test_preds_sha256"],
        "rivals_table": str(TABLE), "headline_column": headline, "band": band, "legal_range": legal,
        "pick": {k: picks[k] for k in ("candidate", "family", "link", "stat", "form")},
        "guard": done["guard"]}

    # --- the board's frame: saved test rows + the rival's guarded forecast, joined one to one in saved order
    t = pq.read_table(str(test_p), columns=["unit", "group", "time", "year", "lead", "issue", "y", "normal",
                                            headline]).to_pandas()
    t["unit"] = t["unit"].astype(str)
    t["group"] = t["group"].astype(str)
    pf = pq.read_table(str(preds_p)).to_pandas()
    pf["unit"] = pf["unit"].astype(str)
    if pf.duplicated(subset=["unit", "time", "lead"]).any():
        refuse("the preds file names a key twice")
    j = t[["unit", "time", "lead"]].merge(pf.drop(columns=["group"]), on=["unit", "time", "lead"], how="left",
                                          indicator=True, validate="one_to_one")
    if (j["_merge"] != "both").any():
        refuse("%d saved test rows have no rival row" % int((j["_merge"] != "both").sum()))
    f = t.copy()
    f["arm__ours"] = t[headline].to_numpy(np.float64)
    f["arm__rival"] = j["guarded"].to_numpy(np.float64)
    f["rival_pre"] = j["pre"].to_numpy(np.float64)
    f["x"] = j["x"].to_numpy(np.float64)
    f["product_cell"] = j["product_cell"].astype(str).to_numpy()
    cov = j["covered"].to_numpy(bool)
    fc = f.loc[cov].reset_index(drop=True)
    gcount = fc.groupby("group").size()
    dec_groups = sorted(gcount.index[gcount >= MIN_GROUP_TEST_ROWS].astype(str).tolist())
    fd = fc[fc["group"].isin(dec_groups)].reset_index(drop=True)
    labelled = np.isfinite(fd["y"].to_numpy(np.float64))

    population = {"test_rows": int(len(f)), "covered_rows": int(cov.sum()), "deciding_rows": int(len(fd)),
                  "deciding_rows_labelled_scored": int(labelled.sum()),
                  "deciding_rows_unlabelled_not_scored": int((~labelled).sum()),
                  "groups": len(dec_groups), "units": int(fd["unit"].nunique()),
                  "months": "%d-%02d .. %d-%02d" % (year_month(fd["time"].min()) + year_month(fd["time"].max()))}

    # --- step 0: reproduce the board EXACTLY
    base = contrast(fd, "arm__rival", "arm__ours", band, block_of_group)
    bl = pd.read_csv(BOARD / ("human_board_lead_%d.csv" % LEAD), float_precision="round_trip")
    brow = bl[(bl["rival"] == RIVAL) & (bl["contrast"] == CONTRAST)]
    tb = pd.read_csv(TABLE, float_precision="round_trip")
    trow = tb[(tb["problem"] == "pm25") & (tb["lead"] == LEAD) & (tb["rival"] == RIVAL) & (tb["contrast"] == CONTRAST)]
    if len(brow) != 1 or len(trow) != 1:
        refuse("the board csv / rivals table does not hold exactly one %s %s row" % (RIVAL, CONTRAST))
    brow, trow = brow.iloc[0], trow.iloc[0]
    checks = {}
    pairs = [("d_mean", "d_mean"), ("d_se", "d_se"), ("d_low", "d_low"), ("d_high", "d_high"),
             ("rival_mae_pooled", "rival_mae"), ("ours_mae_pooled_same_rows", "ours_mae_same_rows"),
             ("blocked_mean_report_only", "blocked_mean"), ("blocked_se_report_only", "blocked_se")]
    for mine, theirs in pairs:
        checks["board_csv." + theirs] = {"ours": base[mine], "board": float(brow[theirs]),
                                         "abs_diff": abs(base[mine] - float(brow[theirs])),
                                         "bit_exact": base[mine] == float(brow[theirs])}
    for mine, theirs in [pq_ for pq_ in pairs[:6] if pq_[1] != "d_se"]:     # the table prints no d_se
        checks["rivals_table." + theirs] = {"ours": base[mine], "table": float(trow[theirs]),
                                            "abs_diff": abs(base[mine] - float(trow[theirs])),
                                            "bit_exact": base[mine] == float(trow[theirs])}
    checks["verdict"] = {"ours": base["verdict"], "board": brow["verdict"], "table": trow["verdict"]}
    checks["n_groups"] = {"ours": base["n_groups"], "board": int(brow["n_groups"]), "table": int(trow["groups"])}
    checks["deciding_rows"] = {"ours": int(len(fd)), "board": int(brow["rows"]), "table": int(trow["rows"])}
    checks["band"] = {"ours": band, "board": float(brow["band"])}
    # per-group MAEs against the board's saved group table
    gt = pd.read_csv(BOARD / "scores" / ("lead_%d_%s_group.csv" % (LEAD, RIVAL)), float_precision="round_trip")
    worst = 0.0
    exact = True
    for col, mp in (("arm__rival", base["_rmap"]), ("arm__ours", base["_omap"])):
        sel = gt[(gt["line"] == "key") & (gt["column"] == col) & (gt["rows_basis"] == "all")]
        saved = {str(g): (float(m), int(n)) for g, m, n in zip(sel["group"], sel["mae"], sel["n"])}
        if set(saved) != set(mp):
            refuse("the saved group table holds other groups for %s" % col)
        for g in mp:
            if saved[g][1] != mp[g][1]:
                refuse("group %s row count %d differs from the board's %d (%s)" % (g, mp[g][1], saved[g][1], col))
            worst = max(worst, abs(saved[g][0] - mp[g][0]))
            exact = exact and saved[g][0] == mp[g][0]
    checks["per_group_mae_vs_saved_group_table"] = {"groups": len(base["_groups"]), "columns": 2,
                                                    "max_abs_diff": worst, "all_bit_exact": bool(exact)}
    # engine cross-check of the jackknife and tag on the same per-group vector
    sys.path.insert(0, str(ENGINE))
    from treeroute import engine_constants as K           # noqa: E402  (read-only import, no bytecode written)
    from treeroute.report import metrics as M              # noqa: E402
    if float(K.JACKKNIFE_Z) != Z or float(M.IDENTICAL_ATOL) != IDENTICAL_ATOL:
        refuse("the engine's jackknife z or identical tolerance differs from this script's")

    def engine_check(res):
        etag, ejk = M.contrast_tag(res["_dv"], band)
        return {"engine_tag": etag.value, "engine_mean": ejk.mean, "engine_low": ejk.low, "engine_high": ejk.high,
                "agrees_bit_exact": bool(etag.value == res["tag"] and ejk.mean == res["d_mean"]
                                         and ejk.low == res["d_low"] and ejk.high == res["d_high"])}

    checks["engine_contrast_tag"] = engine_check(base)
    bad = [k for k, v in checks.items() if isinstance(v, dict) and "abs_diff" in v and v["abs_diff"] > REPRO_TOL]
    if bad or worst > REPRO_TOL or base["verdict"] != brow["verdict"] or base["n_groups"] != int(brow["n_groups"]) \
            or len(fd) != int(brow["rows"]) or not checks["engine_contrast_tag"]["agrees_bit_exact"]:
        refuse("the board's deciding contrast is NOT reproduced: %s" % (bad or "verdict/groups/rows/engine"))
    report["population"] = population
    report["step0_reproduction"] = {"result": "REPRODUCED", "contrast": public(base), "checks": checks}

    # --- step 1: the runaway forecast
    rv = fd["arm__rival"].to_numpy(np.float64)
    i = int(np.nanargmax(rv))
    row = fd.iloc[i]
    yr, mo = year_month(row["time"])
    order = np.argsort(-np.where(np.isfinite(rv), rv, -np.inf))
    ix = ds.dataset(str(INDEX), format="parquet").to_table(
        columns=["unit", "time", "issue", "info_end", "target_obs_end", "product_cell", "src", "x__pm25"],
        filter=(ds.field("unit") == row["unit"])).to_pandas()
    ixr = ix[ix["time"] == int(row["time"])]
    if len(ixr) != 1 or float(ixr["x__pm25"].iloc[0]) != float(row["x"]):
        refuse("the index row of the runaway does not hold the board's x")
    xs_yr, xs_mo = year_month(int(ixr["info_end"].iloc[0]))
    st = ds.dataset(str(STATIC), format="parquet").to_table(
        columns=["cell_id", "lat", "lon"], filter=(ds.field("cell_id") == row["unit"])).to_pandas()
    g = str(row["group"])
    rmap, omap = base["_rmap"], base["_omap"]
    yv = fd["y"].to_numpy(np.float64)
    rival_abs = np.abs(yv - rv)
    tot_rival_err = float(np.nansum(np.where(labelled, rival_abs, np.nan)))
    report["step1_runaway"] = {
        "confirmed": bool(abs(float(row["arm__rival"]) - 418000.0) < 1000.0),
        "rival_forecast_ug_m3": float(row["arm__rival"]),
        "rival_pre_clip_ug_m3": float(row["rival_pre"]),
        "observed_label_y_ug_m3": float(row["y"]),
        "our_headline_forecast_ug_m3": float(row["arm__ours"]),
        "normal_ug_m3": float(row["normal"]),
        "rival_abs_error": float(abs(row["y"] - row["arm__rival"])),
        "our_abs_error": float(abs(row["y"] - row["arm__ours"])),
        "unit": str(row["unit"]), "region_group": g,
        "unit_centre_lat_lon": [float(st["lat"].iloc[0]), float(st["lon"].iloc[0])] if len(st) == 1 else None,
        "merra2_product_cell": str(row["product_cell"]),
        "target_month": "%d-%02d" % (yr, mo), "time_step": int(row["time"]), "issue_step": int(row["issue"]),
        "input_x_merra2_pm25_ug_m3": float(row["x"]),
        "input_x_month": "%d-%02d" % (xs_yr, xs_mo), "input_x_source_file": str(ixr["src"].iloc[0]),
        "second_largest_rival_forecast": {
            "value": float(rv[order[1]]), "unit": str(fd["unit"].iloc[order[1]]),
            "region_group": str(fd["group"].iloc[order[1]]),
            "target_month": "%d-%02d" % year_month(fd["time"].iloc[order[1]])},
        "share_of_all_rival_absolute_error_pct": 100.0 * float(rival_abs[i]) / tot_rival_err,
        "region_rows_scored": rmap[g][1],
        "region_rival_mae": rmap[g][0], "region_our_mae": omap[g][0], "region_d": rmap[g][0] - omap[g][0],
        "region_d_share_of_d_mean": (rmap[g][0] - omap[g][0]) / len(base["_groups"]),
        "region_rival_mae_without_row": None}

    # --- step 2: the runaway row removed from BOTH sides
    fd_drop = fd.drop(index=i).reset_index(drop=True)
    s1 = contrast(fd_drop, "arm__rival", "arm__ours", band, block_of_group)
    s1c = engine_check(s1)
    report["step1_runaway"]["region_rival_mae_without_row"] = s1["_rmap"][g][0]
    report["step2_drop_runaway_row"] = dict(
        public(s1), engine_check=s1c, post_hoc=True,
        population={"deciding_rows": int(len(fd_drop)), "scored_rows": s1["scored_rows"], "groups": s1["n_groups"],
                    "removed": "1 row (%s, %d-%02d) from both rival and ours" % (row["unit"], yr, mo),
                    "region_rows_after": s1["_rmap"][g][1]},
        region_d_after=s1["_rmap"][g][0] - s1["_omap"][g][0],
        drafting_agent_claim={"d_mean": 0.284, "d_low": 0.146, "d_high": 0.422,
                              "matches_to_3_decimals": bool(round(s1["d_mean"], 3) == 0.284
                                                            and round(s1["d_low"], 3) == 0.146
                                                            and round(s1["d_high"], 3) == 0.422)})

    # --- step 3: the rival clipped to the largest label of its own training rows
    tr = ds.dataset(str(BOARD / "slim" / "lead_0" / "train"), format="parquet").to_table(
        columns=["unit", "time", "r_refit", "y"], filter=(ds.field("r_refit") == True)).to_pandas()  # noqa: E712
    if tr["y"].isna().any():
        refuse("a refit row has no label")
    ymax_i = int(tr["y"].to_numpy(np.float64).argmax())
    ymax = float(tr["y"].iloc[ymax_i])
    yu, yt = str(tr["unit"].iloc[ymax_i]), int(tr["time"].iloc[ymax_i])
    n_at_max = int((tr["y"].to_numpy(np.float64) == ymax).sum())
    ixm = ds.dataset(str(INDEX), format="parquet").to_table(
        columns=["unit", "time", "x__pm25"], filter=(ds.field("unit") == yu) & (ds.field("time") == yt)).to_pandas()
    if len(ixm) != 1 or not np.isfinite(ixm["x__pm25"].iloc[0]):
        refuse("the largest refit label's row has no finite rival input; it would not be among the map's fit rows")
    rmap_info = read_json(BOARD / "lead_0" / ("map_%s.json" % RIVAL))["refit"]["info"]
    fdc = fd.copy()
    fdc["arm__rival"] = np.minimum(fd["arm__rival"].to_numpy(np.float64), ymax)
    clipped = (fd["arm__rival"].to_numpy(np.float64) > ymax)
    s2 = contrast(fdc, "arm__rival", "arm__ours", band, block_of_group)
    report["step3_clip_to_max_training_label"] = dict(
        public(s2), engine_check=engine_check(s2), post_hoc=True,
        clip_value_ug_m3=ymax,
        clip_source=("largest label y over the rival's refit rows (board slim lead_0 train set, flag r_refit; "
                     "%d rows, steps %d-%02d .. %d-%02d); the map was fitted on %d of them (rows with a finite "
                     "MERRA-2 input), and the row holding this label is one of them (its x is finite)"
                     % (len(tr), *year_month(tr["time"].min()), *year_month(tr["time"].max()), rmap_info["rows"])),
        clip_label_row={"unit": yu, "target_month": "%d-%02d" % year_month(yt), "rows_at_this_value": n_at_max,
                        "x_merra2": float(ixm["x__pm25"].iloc[0])},
        rows_clipped=int(clipped.sum()),
        rows_clipped_list=[{"unit": str(fd["unit"].iloc[k]), "group": str(fd["group"].iloc[k]),
                            "target_month": "%d-%02d" % year_month(fd["time"].iloc[k]),
                            "rival": float(fd["arm__rival"].iloc[k]), "y": float(fd["y"].iloc[k]),
                            "ours": float(fd["arm__ours"].iloc[k])} for k in np.flatnonzero(clipped)],
        population={"deciding_rows": int(len(fdc)), "scored_rows": s2["scored_rows"], "groups": s2["n_groups"],
                    "note": "every deciding row kept; only the rival forecast is clipped (ours unchanged)"})

    # --- step 4: rival forecasts above 1,000 ug/m3
    allrv = f["arm__rival"].to_numpy(np.float64)
    big = np.flatnonzero(allrv > THRESH)
    gp = pq.read_table(str(BOARD / "lead_0" / ("guard_%s.parquet" % RIVAL)), columns=["pred", "y"]).to_pandas()
    report["step4_forecasts_above_1000"] = {
        "threshold_ug_m3": THRESH,
        "test_rows_count": int(big.size), "test_rows_population": int(len(f)),
        "deciding_labelled_rows_count": int(((rv > THRESH) & labelled).sum()),
        "deciding_labelled_rows_population": int(labelled.sum()),
        "rows": [{"unit": str(f["unit"].iloc[k]), "group": str(f["group"].iloc[k]),
                  "target_month": "%d-%02d" % year_month(f["time"].iloc[k]), "rival": float(allrv[k]),
                  "x_merra2_lag1": float(f["x"].iloc[k]), "y": float(f["y"].iloc[k]),
                  "ours": float(f["arm__ours"].iloc[k])} for k in big[np.argsort(-allrv[big])]],
        "test_rows_above_max_training_label": int((allrv > ymax).sum()),
        "context_inner_guard_rows_count": int((gp["pred"].to_numpy(np.float64) > THRESH).sum()),
        "context_inner_guard_rows_population": int(len(gp)),
        "context_inner_guard_max_pred": float(gp["pred"].max())}

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1, sort_keys=False, allow_nan=True)
    print(json.dumps({"step0": report["step0_reproduction"]["result"],
                      "base": {k: base[k] for k in ("verdict", "d_mean", "d_low", "d_high", "n_groups", "scored_rows")},
                      "drop": {k: s1[k] for k in ("verdict", "d_mean", "d_low", "d_high", "n_groups", "scored_rows")},
                      "clip": {k: s2[k] for k in ("verdict", "d_mean", "d_low", "d_high", "n_groups", "scored_rows")},
                      "clip_value": ymax, "above_1000": int(big.size)}, indent=1))


if __name__ == "__main__":
    main()
