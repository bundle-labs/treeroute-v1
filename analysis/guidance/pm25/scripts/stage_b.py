"""STAGE B -- pm25 -- scores the stage-A method predictions on the test labels (PROTOCOL.txt section 6).
Runs only after stageA.sha256.txt exists; verifies those hashes first. Test y is opened here, only to score.
"""
import hashlib
import json
import os
import time

import numpy as np
import pandas as pd
import psutil
import pyarrow.parquet as pq

T0 = time.time()
PKG = "pm25"
RUN = "D:/treeroute/runs/pm25/headline/20261007_74e67609"
OUT = "D:/treeroute/analysis/guidance/pm25"
CHOSEN = "log_c_corrector_unweighted"


def file_sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# verify stage A was frozen before this script opens y
for line in open(os.path.join(OUT, "stageA.sha256.txt")):
    if line.startswith("written"):
        print(line.strip())
        continue
    h, p = line.strip().split("  ", 1)
    assert file_sha256(p) == h, "stage A file changed: %s" % p
stage = json.load(open(os.path.join(OUT, "stageA_%s.json" % PKG)))
verdict = json.load(open(os.path.join(RUN, "verdict.json")))
assert verdict["adopted"] == CHOSEN
BAND = float(verdict["band"])
ORIG = float(verdict["pooled_mae_adopted"])

mp = pd.read_parquet(os.path.join(OUT, "method_preds_%s.parquet" % PKG))
tp = pq.read_table(os.path.join(RUN, "test_preds.parquet"),
                   columns=["unit", "time", "year", "y", "arm__" + CHOSEN]).to_pandas()
assert (tp["unit"].to_numpy() == mp["unit"].to_numpy()).all() and (tp["time"].to_numpy() == mp["time"].to_numpy()).all()
y = tp["y"].to_numpy(np.float64)
C = tp["arm__" + CHOSEN].to_numpy(np.float64)
assert np.array_equal(C, mp["C_chosen"].to_numpy(), equal_nan=True)
scored = np.isfinite(y) & np.isfinite(C)
orig = float(np.mean(np.abs(y[scored] - C[scored])))
g2 = {"orig_recomputed": orig, "verdict": ORIG, "rel": abs(orig - ORIG) / ORIG, "scored_rows": int(scored.sum())}
g2["PASS"] = g2["rel"] <= 1e-9
print("G2", g2)
assert g2["PASS"]
years = tp["year"].to_numpy()

methods = [c for c in mp.columns if c not in ("unit", "time", "C_chosen")]
res = {}
for m in methods:
    p = mp[m].to_numpy(np.float64)
    nonfinite = int((~np.isfinite(p[scored])).sum())
    ok = scored & np.isfinite(p)
    mae = float(np.mean(np.abs(y[ok] - p[ok])))
    d = mae - orig
    same = bool(np.array_equal(p[scored], C[scored]))
    status = "SAME" if same else ("HELPS" if d < 0 else ("HURTS" if d > 0 else "SAME-MAE"))
    per_year = {int(yr): float(np.mean(np.abs(y[ok & (years == yr)] - p[ok & (years == yr)]))) for yr in np.unique(years)}
    res[m] = {"mae": mae, "delta": d, "delta_over_band": d / BAND, "status": status,
              "S2_no_harm(delta<=0.25band)": bool(d <= 0.25 * BAND), "nonfinite_on_scored": nonfinite,
              "share_scored_rows_differing_from_C": float(np.mean(p[scored] != C[scored])), "per_year": per_year}
orig_year = {int(yr): float(np.mean(np.abs(y[scored & (years == yr)] - C[scored & (years == yr)]))) for yr in np.unique(years)}

sanity = {"alarm_ratio": stage["alarm"]["ratio"], "alarm_ratio_part603": 1.00,
          "M3_mae": res["M3"]["mae"], "M3_part603": 3.584,
          "M3_matches_rounding": abs(round(res["M3"]["mae"], 3) - 3.584) < 1e-9,
          "alarm_matches_rounding": abs(round(stage["alarm"]["ratio"], 2) - 1.00) < 1e-9}
out = {"package": PKG, "original": {"arm": CHOSEN, "test_mae": orig, "band": BAND, "per_year": orig_year},
       "twin_test_mae": res["T_twin"]["mae"], "G2": g2, "methods": res, "sanity_part603": sanity,
       "seconds_stage_b": time.time() - T0,
       "peak_ram_gb_stage_b": round(getattr(psutil.Process().memory_info(), "peak_wset", 0) / 1e9, 3)}
json.dump(out, open(os.path.join(OUT, "results_%s.json" % PKG), "w"), indent=1)
print("original %s test MAE %.6f band %.6f (0.25 band %.6f)" % (CHOSEN, orig, BAND, 0.25 * BAND))
for m in methods:
    r = res[m]
    print("%-20s MAE %.6f  delta %+.6f  /band %+.4f  %-6s  differs %.4f  nonfinite %d" % (
        m, r["mae"], r["delta"], r["delta_over_band"], r["status"], r["share_scored_rows_differing_from_C"],
        r["nonfinite_on_scored"]))
print("sanity", sanity)
