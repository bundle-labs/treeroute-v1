"""POST HOC sensitivity (implementer A) of the PM2.5 published rival merra2_lag1, lead 0, deciding contrast
guarded_vs_headline (board run 20261007_74e67609).

Run:  py -3.9 -I D:/treeroute/analysis/paper_posthoc/merra2_runaway/sens_A.py
Reads only (light, column-selected): the run's test_preds.parquet + verdict.json, the board's preds file, done file,
group score table, lead-0 board CSV, the RIVALS_TABLE.csv row, and y/r_refit/group/time of the slim train files.
Writes only sens_A.json next to this script. Imports the engine's own metrics functions read-only
(sys.dont_write_bytecode is set first, so no __pycache__ is written).

Steps
 0. Reproduce the board's deciding contrast EXACTLY with the tool's code path (board._contrast): frame as
    board._ours_frame, join as harness._join (left order, one-to-one), covered rows, groups with >= 10 covered rows,
    engine score_table by group -> metric_by_key('mae') -> _paired_contrast(rival, ours) -> contrast_tag(d, band).
    Checked against the board's group table, the board CSV and RIVALS_TABLE.csv (exact equality reported).
 1. Locate the largest rival forecast (value, unit, region, month, product cell, inputs).
 2. Drop that ONE row from both sides (same rows for rival and ours) and recompute.
 3. Clip the rival forecast to the largest label in the rival's training rows (the slim lead-0 refit set, the rows
    the rival's map is refit on before predicting test) and recompute; per-region clip given beside.
 4. Count rival forecasts above 1,000 ug/m3.
"""
import sys

sys.dont_write_bytecode = True

import glob                                              # noqa: E402
import hashlib                                           # noqa: E402
import json                                              # noqa: E402
import math                                              # noqa: E402
import os                                                # noqa: E402

import numpy as np                                       # noqa: E402
import pandas as pd                                      # noqa: E402
import pyarrow.parquet as pq                             # noqa: E402

ENGINE_ROOT = r"C:\Users\moh the ghost\Desktop\data set for reserch paper\engine"
sys.path.insert(0, ENGINE_ROOT)
from treeroute.report import metrics as M               # noqa: E402

RUN = r"D:\treeroute\runs\pm25\headline\20261007_74e67609"
BOARD = r"D:\treeroute\rivals_human\pm25\20261007_74e67609"
RIVALS_TABLE = r"D:\treeroute\rivals_table\20261025T162302876402Z\RIVALS_TABLE.csv"
RIVAL = "merra2_lag1"
LEAD = 0
MIN_GROUP_TEST_ROWS = 10           # rivals_human/config.py:133
THRESH = 1000.0
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sens_A.json")
KEYS = ["unit", "time", "lead"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def join(left_keys, right, on, what):
    """harness._join: left keys joined one to one in the left order; refuses a missing or duplicated key."""
    if right.duplicated(subset=on).any():
        raise SystemExit("%s names a key twice" % what)
    lk = left_keys[on].copy()
    r = right.copy()
    for k in on:
        if k in ("unit", "group"):
            lk[k] = lk[k].astype(str)
            r[k] = r[k].astype(str)
    j = lk.merge(r, on=on, how="left", indicator=True, validate="one_to_one")
    if int((j["_merge"] != "both").sum()):
        raise SystemExit("unmatched rows in %s" % what)
    return j.drop(columns="_merge")


def month_of(time, year):
    m = int(time) - 12 * int(year)          # the run's time = 12*year + month (1..12); checked below
    return "%04d-%02d" % (int(year), m)


def contrast(fd, rcol, ocol, tol, floor, kind, band, what):
    """board._contrast's verdict path on the deciding rows fd (rows_basis 'all')."""
    gt = M.score_table(fd[["unit", "group", "time", "year", "y", "normal", rcol, ocol]], ("group",), tol, floor, kind)
    pt = M.score_table(fd[["unit", "group", "time", "year", "y", "normal", rcol, ocol]], (), tol, floor, kind)
    rmap = M.metric_by_key(gt, rcol, "mae", "group", rows_basis="all")
    omap = M.metric_by_key(gt, ocol, "mae", "group", rows_basis="all")
    groups, d = M._paired_contrast(rmap, omap, what)
    tag, jk = M.contrast_tag(d, band)

    def pooled(col):
        s = pt[(pt["line"] == "pooled") & (pt["column"] == col) & (pt["rows_basis"] == "all")]
        assert len(s) == 1
        return s.iloc[0]

    pr, po = pooled(rcol), pooled(ocol)
    # independent numpy re-computation of the jackknife (same formula as metrics.group_jackknife)
    n = d.size
    loo = np.array([np.delete(d, i).mean() for i in range(n)])
    se_np = float(np.sqrt((n - 1) / n * ((loo - loo.mean()) ** 2).sum()))
    order = np.argsort(-d)
    return {
        "verdict": {"helps": "BEATS", "hurts": "LOSES", "does_not_help_equivalent": "EQUIVALENT",
                    "cannot_tell": "CANNOT TELL", "identical": "IDENTICAL",
                    "declined": "DECLINED"}[tag.value],          # harness.VERDICT_WORDS
        "tag": tag.value,
        "d_mean": jk.mean, "d_se": jk.se, "d_low": jk.low, "d_high": jk.high, "n_groups": jk.n_groups,
        "d_se_numpy_check": se_np,
        "rows_scored": int(pr["n"]), "rival_mae_pooled": float(pr["mae"]), "ours_mae_pooled": float(po["mae"]),
        "groups_with_d_gt_0": int((d > 0).sum()), "groups_with_d_lt_0": int((d < 0).sum()),
        "top5_groups_by_d": [{"group": groups[i], "d": float(d[i])} for i in order[:5]],
        "_per_group": dict(zip(groups, d.tolist())), "_rmap": rmap, "_omap": omap,
    }


def strip(res):
    return {k: v for k, v in res.items() if not k.startswith("_")}


def main():
    out = {"label": "POST HOC sensitivity (implementer A); not part of the frozen protocol",
           "rival": RIVAL, "problem": "pm25", "lead": LEAD, "contrast": "guarded_vs_headline",
           "units": "ug/m3"}

    # ---------------------------------------------------------------- inputs + hashes
    verdict = json.load(open(os.path.join(RUN, "verdict.json"), encoding="utf-8"))
    band, tol = float(verdict["band"]), float(verdict["hit_tolerance"])
    floor = verdict.get("measurement_error_floor")
    floor = None if floor is None else float(floor)
    kind = verdict["kind"]
    headline = "arm__" + verdict["adopted"]
    assert not verdict.get("declined")
    tp_path = os.path.join(RUN, "test_preds.parquet")
    pp_path = os.path.join(BOARD, "lead_0", "preds_%s.parquet" % RIVAL)
    done = json.load(open(os.path.join(BOARD, "lead_0", "done_%s.json" % RIVAL), encoding="utf-8"))
    opened = json.load(open(os.path.join(BOARD, "test_labels_opened_human_lead_0.json"), encoding="utf-8"))
    tp_sha, pp_sha = sha256(tp_path), sha256(pp_path)
    out["inputs"] = {
        "test_preds": tp_path, "test_preds_sha256": tp_sha,
        "test_preds_sha256_matches_board_record": tp_sha == opened["test_preds_sha256"],
        "rival_preds": pp_path, "rival_preds_sha256": pp_sha,
        "rival_preds_sha256_matches_done_file": pp_sha == done["preds_sha256"],
        "headline_column": headline, "band": band, "hit_tolerance": tol, "floor": floor, "run_kind": kind,
        "guard_passed": done["guard"]["passed"],
    }

    # ---------------------------------------------------------------- frame (board._ours_frame + score())
    cols = ["unit", "group", "time", "year", "lead", "issue", "y", "normal", "legal_min", "legal_max", headline,
            "base__guess_normal"]
    saved = pq.read_table(tp_path, columns=cols).to_pandas()
    frame = saved[["unit", "group", "time", "year", "lead", "issue", "y", "normal", "legal_min", "legal_max"]].copy()
    frame["arm__ours"] = saved[headline].to_numpy(np.float64)
    frame["base__guess_normal"] = saved["base__guess_normal"].to_numpy(np.float64)
    pf = pq.read_table(pp_path).to_pandas()
    j = join(saved[KEYS], pf, KEYS, os.path.basename(pp_path))
    cov = j["covered"].to_numpy(bool)
    f = frame.copy()
    f["arm__rival"] = j["guarded"].to_numpy(np.float64)
    f["x"] = j["x"].to_numpy(np.float64)
    f["pre"] = j["pre"].to_numpy(np.float64)
    f["raw"] = j["raw"].to_numpy(np.float64)
    f["product_cell"] = j["product_cell"].astype(str).to_numpy()
    fc = f.loc[cov].reset_index(drop=True)
    gcount = fc.groupby("group").size()
    dec_groups = sorted(gcount.index[gcount >= MIN_GROUP_TEST_ROWS].astype(str).tolist())
    fd = fc[fc["group"].astype(str).isin(dec_groups)].reset_index(drop=True)
    tm = (fd["time"] - 12 * fd["year"]).to_numpy()
    assert tm.min() >= 1 and tm.max() <= 12, "time is not 12*year + month"
    labelled = np.isfinite(fd["y"].to_numpy(np.float64))
    out["population_board"] = {
        "rows_total": int(cov.size), "rows_covered": int(cov.sum()), "rows_deciding": int(len(fd)),
        "rows_labelled_scored": int(labelled.sum()), "rows_unlabelled": int((~labelled).sum()),
        "groups_deciding": len(dec_groups), "years": sorted(set(fd["year"].astype(int).tolist())),
        "legal_range": [float(fd["legal_min"].iloc[0]), float(fd["legal_max"].iloc[0])],
        "rival_guarded_equals_raw_equals_pre": bool(np.array_equal(fd["arm__rival"], fd["raw"])
                                                    and np.array_equal(fd["raw"], fd["pre"])),
    }

    # ---------------------------------------------------------------- 0. reproduce
    base = contrast(fd, "arm__rival", "arm__ours", tol, floor, kind, band, "%s guarded_vs_headline" % RIVAL)
    gtab = pd.read_csv(os.path.join(BOARD, "scores", "lead_0_%s_group.csv" % RIVAL), float_precision="round_trip")
    key = gtab[(gtab["line"] == "key") & (gtab["rows_basis"] == "all")]
    diffs = {}
    for col, mp in (("arm__rival", base["_rmap"]), ("arm__ours", base["_omap"])):
        s = key[key["column"] == col].set_index("group")["mae"]
        assert set(s.index.astype(str)) == set(mp)
        diffs[col] = float(max(abs(float(s[g]) - mp[g]) for g in mp))
    bl = pd.read_csv(os.path.join(BOARD, "human_board_lead_0.csv"), float_precision="round_trip")
    brow = bl[(bl["rival"] == RIVAL) & (bl["contrast"] == "guarded_vs_headline")].iloc[0]
    rt = pd.read_csv(RIVALS_TABLE, float_precision="round_trip")
    rrow = rt[(rt["problem"] == "pm25") & (rt["lead"] == LEAD) & (rt["rival"] == RIVAL)
              & (rt["contrast"] == "guarded_vs_headline")].iloc[0]
    out["reproduction"] = dict(strip(base), **{
        "board_d_mean": float(brow["d_mean"]), "board_d_se": float(brow["d_se"]),
        "board_d_low": float(brow["d_low"]), "board_d_high": float(brow["d_high"]),
        "board_verdict": brow["verdict"], "board_rival_mae": float(brow["rival_mae"]),
        "board_ours_mae": float(brow["ours_mae_same_rows"]),
        "rivals_table_d": [float(rrow["d_mean"]), float(rrow["d_low"]), float(rrow["d_high"])],
        "rivals_table_verdict": rrow["verdict"], "rivals_table_groups": float(rrow["groups"]),
        "max_abs_diff_group_mae_vs_board_table": diffs,
        "exact_match_d_mean": base["d_mean"] == float(brow["d_mean"]),
        "exact_match_d_se": base["d_se"] == float(brow["d_se"]),
        "exact_match_d_low": base["d_low"] == float(brow["d_low"]),
        "exact_match_d_high": base["d_high"] == float(brow["d_high"]),
        "max_abs_diff_vs_rivals_table": float(max(abs(base["d_mean"] - float(rrow["d_mean"])),
                                                  abs(base["d_low"] - float(rrow["d_low"])),
                                                  abs(base["d_high"] - float(rrow["d_high"])))),
    })

    # ---------------------------------------------------------------- 1. the runaway forecast
    i = int(np.nanargmax(fd["arm__rival"].to_numpy(np.float64)))
    r = fd.iloc[i]
    g = str(r["group"])
    gmask = (fd["group"].astype(str) == g).to_numpy()
    out["runaway"] = {
        "rival_forecast": float(r["arm__rival"]), "unit": str(r["unit"]), "region": g,
        "time": int(r["time"]), "month": month_of(r["time"], r["year"]), "issue": int(r["issue"]),
        "product_cell": str(r["product_cell"]), "rival_input_x_merra2_lag1": float(r["x"]),
        "observed_y": float(r["y"]), "ours_forecast": float(r["arm__ours"]), "normal": float(r["normal"]),
        "rival_abs_error": float(abs(r["arm__rival"] - r["y"])), "ours_abs_error": float(abs(r["arm__ours"] - r["y"])),
        "clipped": False,
        "region_d_with_it": float(base["_per_group"][g]),
        "region_rows": int(gmask.sum()), "region_labelled_rows": int((gmask & labelled).sum()),
        "second_largest_rival_forecast": float(np.sort(fd["arm__rival"].to_numpy(np.float64))[-2]),
    }

    # ---------------------------------------------------------------- 2. drop that one row from both sides
    fd1 = fd.drop(index=i).reset_index(drop=True)
    s1 = contrast(fd1, "arm__rival", "arm__ours", tol, floor, kind, band, "drop one row")
    out["sens1_drop_one_row"] = dict(strip(s1), **{
        "population": "deciding rows minus the one runaway row (removed from rival AND ours); %d labelled rows, "
                      "%d regions" % (s1["rows_scored"], s1["n_groups"]),
        "region_d_without_it": float(s1["_per_group"][g]),
        "drafting_agent_claim": {"d": 0.284, "low": 0.146, "high": 0.422},
    })

    # ---------------------------------------------------------------- 3. clip to the largest training label
    trs = sorted(glob.glob(os.path.join(BOARD, "slim", "lead_0", "train", "*.parquet")))
    parts = [pq.read_table(p, columns=["group", "time", "r_refit", "y"]).to_pandas() for p in trs]
    tr = pd.concat(parts, ignore_index=True)
    refit = tr[tr["r_refit"].to_numpy(bool)]
    yr = refit["y"].to_numpy(np.float64)
    ok = np.isfinite(yr)
    k = int(np.nanargmax(yr))
    ymax = float(yr[k])
    per_region_max = refit.groupby(refit["group"].astype(str))["y"].max()
    yall = tr["y"].to_numpy(np.float64)
    out["training_label_max"] = {
        "set": "slim lead-0 refit rows (r_refit; the rows the rival's map is refit on before its test predictions)",
        "refit_rows": int(len(refit)), "refit_rows_labelled": int(ok.sum()),
        "refit_time_range": [int(refit["time"].min()), int(refit["time"].max())],
        "refit_month_range": [month_of(refit["time"].min(), (refit["time"].min() - 1) // 12),
                              month_of(refit["time"].max(), (refit["time"].max() - 1) // 12)],
        "max_y": ymax, "max_y_region": str(refit["group"].iloc[k]), "max_y_time": int(refit["time"].iloc[k]),
        "max_y_month": month_of(refit["time"].iloc[k], (refit["time"].iloc[k] - 1) // 12),
        "max_y_all_train_file_rows": float(np.nanmax(yall)),
        "runaway_region_refit_max": float(per_region_max[g]),
        "max_test_label_for_reference": float(np.nanmax(fd["y"].to_numpy(np.float64))),
    }
    p = fd["arm__rival"].to_numpy(np.float64)
    fd2 = fd.copy()
    fd2["arm__rival_clip"] = np.minimum(p, ymax)
    s2 = contrast(fd2, "arm__rival_clip", "arm__ours", tol, floor, kind, band, "clip global")
    out["sens2_clip_to_training_max"] = dict(strip(s2), **{
        "clip_at": ymax, "rows_clipped": int((p > ymax).sum()),
        "rows_clipped_labelled": int(((p > ymax) & labelled).sum()),
        "population": "all deciding rows (%d labelled, %d regions); rival forecast min(p, %.6g)"
                      % (s2["rows_scored"], s2["n_groups"], ymax),
        "region_d_after_clip": float(s2["_per_group"][g]),
    })
    cap = fd["group"].astype(str).map(per_region_max).to_numpy(np.float64)
    fd3 = fd.copy()
    fd3["arm__rival_clipr"] = np.minimum(p, cap)
    s3 = contrast(fd3, "arm__rival_clipr", "arm__ours", tol, floor, kind, band, "clip per region")
    out["sens2b_clip_to_own_region_training_max"] = dict(strip(s3), **{
        "rows_clipped": int((p > cap).sum()), "rows_clipped_labelled": int(((p > cap) & labelled).sum()),
        "population": "all deciding rows (%d labelled, %d regions); rival forecast min(p, its region's refit max)"
                      % (s3["rows_scored"], s3["n_groups"]),
    })

    # ---------------------------------------------------------------- 4. forecasts above 1,000 ug/m3
    big = fd[p > THRESH].sort_values("arm__rival", ascending=False)
    out["count_rival_forecasts_gt_1000"] = {
        "threshold": THRESH, "population": "%d deciding rows (all covered test rows, lead 0, 2020-2023)" % len(fd),
        "count": int(len(big)), "count_labelled": int(np.isfinite(big["y"].to_numpy(np.float64)).sum()),
        "count_all_rows_of_preds_file": int((pf["guarded"].to_numpy(np.float64) > THRESH).sum()),
        "count_gt_training_max": int((p > ymax).sum()),
        "rows": [{"rival_forecast": float(b["arm__rival"]), "unit": str(b["unit"]), "region": str(b["group"]),
                  "month": month_of(b["time"], b["year"]), "x": float(b["x"]), "y": float(b["y"]),
                  "ours": float(b["arm__ours"])} for _, b in big.iterrows()],
    }

    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating, float)):
            return float(o) if math.isfinite(float(o)) else str(float(o))
        return o

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(clean(out), fh, indent=1, sort_keys=False)
    print(json.dumps(clean(out), indent=1))


if __name__ == "__main__":
    main()
