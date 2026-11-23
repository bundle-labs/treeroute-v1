"""Label-free guidance -- CORAL, STAGE B (scoring). Opens test labels only after stage A's hashes check out.

Protocol: D:/treeroute/analysis/guidance/PROTOCOL.txt sections 6-7. Writes only under guidance/coral/.
"""
import hashlib
import json
import os
import sys
import time as _time

import numpy as np
import pandas as pd
import psutil

T0 = _time.time()
OUT = "D:/treeroute/analysis/guidance/coral"
RUN = "D:/treeroute/runs/coral/headline/20261020_f3b8e3da"
PROTOCOL = "D:/treeroute/analysis/guidance/PROTOCOL.txt"
PROTOCOL_SHA = "c51fc39ad390204de8894fd3b50cd4f9cf0fc70a92eddf99214497fb6201eef4"
CHOSEN = "arcsine_corrector_gls"
LOG = []


def log(msg):
    line = "[%7.1fs] %s" % (_time.time() - T0, msg)
    print(line, flush=True)
    LOG.append(line)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


if sha256_file(PROTOCOL) != PROTOCOL_SHA:
    sys.exit("protocol hash mismatch")
for line in open(os.path.join(OUT, "stageA.sha256.txt")):
    h, name = line.split()
    if sha256_file(os.path.join(OUT, name.lstrip("*"))) != h:
        sys.exit("stage A file changed: %s" % name)
log("protocol + stage A hashes OK")

verdict = json.load(open(os.path.join(RUN, "verdict.json"), encoding="utf-8"))
ORIG_MAE = float(verdict["pooled_mae_adopted"])
BAND = float(verdict["band"])
stage = json.load(open(os.path.join(OUT, "stageA_coral.json"), encoding="utf-8"))
preds = pd.read_parquet(os.path.join(OUT, "method_preds_coral.parquet"))
lab = pd.read_parquet(os.path.join(RUN, "test_preds.parquet"),
                      columns=["unit", "time", "y", "programme", "arm__%s" % CHOSEN])
assert (lab["unit"].to_numpy() == preds["unit"].to_numpy()).all()
assert (lab["time"].to_numpy() == preds["time"].to_numpy()).all()
assert np.array_equal(lab["arm__%s" % CHOSEN].to_numpy(), preds["C"].to_numpy(), equal_nan=True)
y = lab["y"].to_numpy(float)
C = preds["C"].to_numpy(float)
scored = np.isfinite(y) & np.isfinite(C)
y, C = y[scored], C[scored]
year = preds["year"].to_numpy(int)[scored]
prog = lab["programme"].astype(str).to_numpy()[scored]
orig = float(np.mean(np.abs(y - C)))
G2 = {"mae": orig, "verdict": ORIG_MAE, "rel": abs(orig - ORIG_MAE) / ORIG_MAE, "n_scored": int(scored.sum())}
G2["pass"] = G2["rel"] <= 1e-9
log("G2 %s" % G2)
if not G2["pass"]:
    sys.exit("G2 failed -> coral not scored")

bleached = y > 0
severe = y > 50                         # analyse_drift.py:107 bin (50, 101]


def mae(p, m=None):
    m = np.ones(len(y), bool) if m is None else m
    return float(np.mean(np.abs(y[m] - p[m])))


def score(name):
    p = preds[name].to_numpy(float)[scored]
    assert np.isfinite(p).all(), name
    d = mae(p) - orig
    same = bool(np.array_equal(p, C))
    res = {"mae": mae(p), "delta": d, "delta_over_band": d / BAND,
           "call": "SAME" if same else ("HELPS" if d < 0 else ("HURTS" if d > 0 else "TIE")),
           "rows_differing_from_chosen": int(np.sum(p != C)),
           "bleached_mae": mae(p, bleached), "severe_mae": mae(p, severe),
           "per_year": {int(Y): mae(p, year == Y) for Y in sorted(set(year))},
           "per_programme": {g: {"n": int(np.sum(prog == g)), "mae": mae(p, prog == g)} for g in sorted(set(prog))}}
    return res


NAMES = ["C", "T", "M1", "M2", "M3", "M4", "M5", "M5raw", "M5_placebo", "M5_placebo_gated",
         "M6", "M6s", "M6raw", "M6sraw", "M6_placebo", "M6s_placebo", "M6_placebo_gated", "M6s_placebo_gated"]
res = {n: score(n) for n in NAMES}
subsets = {"all": int(len(y)), "bleached_y_gt_0": int(bleached.sum()), "severe_y_gt_50": int(severe.sum()),
           "original_bleached_mae": mae(C, bleached), "original_severe_mae": mae(C, severe)}
for n in NAMES:
    r = res[n]
    log("%-18s MAE %.5f delta %+.5f (%+.3f band) %-5s | bleached %.4f severe %.4f | %s" % (
        n, r["mae"], r["delta"], r["delta_over_band"], r["call"], r["bleached_mae"], r["severe_mae"],
        {k: round(v, 3) for k, v in r["per_year"].items()}))

# success items S1, S3, S4 (S2 needs the other four problems)
succ = {}
for m, plac in [("M1", None), ("M2", None), ("M3", None), ("M4", None), ("M5", "M5_placebo"),
                ("M6", "M6_placebo"), ("M6s", "M6s_placebo")]:
    r = res[m]
    s = {"S1_coral_improves": r["delta"] < 0,
         "S3_beats_placebo": (res[plac]["delta"] > r["delta"]) if plac else "N/A",
         "S4_not_noop": r["rows_differing_from_chosen"] > 0,
         "S2_no_harm_elsewhere": "PENDING (pm25, ndvi, fire, defo)"}
    failed = [k for k, v in s.items() if v is False]
    s["coral_items_verdict"] = ("FAILS " + ", ".join(failed)) if failed else "coral items PASS (S2 pending)"
    if m in ("M1", "M2", "M3") and not failed:
        s["coral_items_verdict"] += "; CIRCULAR-ON-CORAL"
    succ[m] = s

sanity = {"alarm_ratio": {"now": stage["alarm"]["ratio"], "part603": 4.29},
          "M3_mae": {"now": res["M3"]["mae"], "part603": 6.394},
          "M1_mae": {"now": res["M1"]["mae"], "part603": 6.147}}
sanity["match"] = (abs(sanity["alarm_ratio"]["now"] - 4.29) < 0.005 and abs(res["M3"]["mae"] - 6.394) < 0.0005
                   and abs(res["M1"]["mae"] - 6.147) < 0.0005)
log("sanity vs Part 603: %s" % sanity)

out = {"protocol_sha256": PROTOCOL_SHA, "problem": "coral", "original": {"arm": CHOSEN, "mae": orig, "band": BAND},
       "gates": {"G2": G2}, "subsets": subsets, "methods": res, "success_items": succ, "sanity_part603": sanity,
       "stage_b_seconds": round(_time.time() - T0, 2),
       "stage_b_peak_ram_mb": round(psutil.Process().memory_info().peak_wset / 2 ** 20, 1)}
with open(os.path.join(OUT, "results_coral.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, default=float)
with open(os.path.join(OUT, "stage_b.log"), "w", encoding="utf-8") as f:
    f.write("\n".join(LOG) + "\n")
log("results_coral.json written (%.1f s, peak RAM %.0f MB)" % (out["stage_b_seconds"], out["stage_b_peak_ram_mb"]))
