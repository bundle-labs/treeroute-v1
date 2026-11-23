# Round 14, implementer A: assemble V\A\results.json from V\A\work\items_<p>.json and V\A\work\b1.json.
import datetime
import json
import os
import platform
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pyarrow
import pandas
import scipy

import a_lib as L

CHOICES = {
    "C01": "Every row enters every statistic; no row of any piece (B1 included) has resid_flag true, so this changes no number.",
    "C02": "Rows of a region are averaged, then regions averaged with weight 1 each; on a draw a region drawn k times weighs k (cluster bootstrap).",
    "C03": "The signed mean uses the same region weights as I_m(j), on signed phi.",
    "C04": "j is in J iff some model has I_m(j) > 1e-12 x (sum of I_m over all its players), I the region-weighted mean |phi|; strict '>'; a zero total adds nothing.",
    "C05": "'Some model' = every model of per_lead.json models (cross-link and declined included); one J per level for every statistic of the problem.",
    "C06": "A name with no column in a model's file is 0 on every row for that model (ranked as 0, ties by name); structural zeros = union of names minus J.",
    "C07": "J (and its 200-player test) and B1's pair J fixed at the full sample; top-k sets and their unions found again on each draw; determined signs fixed from the full bootstrap.",
    "C08": "Counts recomputed per draw get intervals (n_nonzero, n_nonzero_before_merge, sign_n_determined, sign_n_agree); n_J has none (J fixed).",
    "C09": "Nonzero = I_m(j) > 0 exactly (some row nonzero), counted over the model's own columns; per draw on that draw's I.",
    "C10": "Ties = exact float64 equality of I_m; name = result name (x__/c__ kept) in ascending Python order; one strict order (I desc, name asc) for top-k, RBO, top-10/top-3.",
    "C11": "Spearman = Pearson of average ranks; over the top-20 union the two I vectors are re-ranked within the union.",
    "C12": "A top-k set has min(k,|J|) names; the top-20 Jaccard only when the full-sample J (B1: pair J) has >= 200 players, else null.",
    "C13": "RBO = (1-p) sum_{d=1..n} p^(d-1) A_d + p^n A_n over the two full strict rankings of J (eq. 32 with s = l = n); self-RBO = 1.",
    "C14": "TV = half the sum of absolute differences of the shares over J; family TV the same over the families present.",
    "C15": "Family row attribution = sum of all its variables' phiv; family share = region-weighted mean |sum| over the five families' total; variable level only; absent family null.",
    "C16": "Named families first (hist_*, normal, calendar/ctx:*), then the rule (every column one exact value per time across all test-set units), else local drivers.",
    "C17": "Determined iff ci_low > 0 or ci_high < 0 (strict); sign agreement = n_agree / n_determined on the top-10 union, undefined when n_determined = 0.",
    "C18": "Undefined (null on the full sample, NaN on a draw): all-tied rankings, no determined player, zero totals, fewer than 2 main models, no rival (fire), no hist_* variable (coral).",
    "C19": "W over J with average ranks and T = sum(t^3 - t) per rater; mean pairwise Spearman = mean of the main set's Spearman over J, computed directly.",
    "C20": "Stability = mean over finite draws of Spearman over J between full-sample I and the draw's I; no interval (counts and percentiles in extra).",
    "C21": "numpy percentile 2.5/97.5 (linear interpolation) of the finite replicates; non-finite dropped and counted; interval whenever n_finite >= 1.",
    "C22": "Rivals = main set minus treeroute; median by numpy (even count: mean of the middle two), CI from per-draw medians; range = min and max, each with per-draw CI.",
    "C23": "Median of the rivals' own-history shares, recomputed per draw; median_rival_name only for an odd count.",
    "C24": "Own-history share = the own-history family share (sum of hist_* phiv per row), not the sum of hist_* shares.",
    "C25": "All arcsine-link models of all problems (coral 4, fire treeroute); their pre > 0 rows; I, share, S, sign, n_nonzero, ranking, top-10 over the variable J; regions without such rows drop out.",
    "I01": "Region = rows.parquet column `group` (identical in every piece; 37/42/40/127/133 distinct = draw-matrix columns).",
    "I02": "Draw matrix (2000, G) int64, reproduced exactly as entry(b,k) = first 8 bytes (big-endian) of SHA-256('shap_v1|AW4|<p>|0|<b>|<k>') mod G: row b = draw b, G picks with replacement, indexing the regions in sorted() order (= first-appearance order).",
    "I03": "draws_sha256 = SHA-256 of every byte of the .npy file (header and data); it matches for all five problems; the data bytes alone do not match.",
    "I04": "Test set = the lead-0 test export named by SHAP\\logs\\rival_shap_<p>_lead0.log ('test set:' line): D:\\treeroute\\rival_export\\<p>\\<run>\\lead_0\\test\\<region>.parquet; columns unit, time and the players' feature columns.",
    "I05": "SHAP\\SAMPLE_REGISTER.txt: the one line with problem=<p> (its leads include 0), field sample=; every B1 piece's sample_sha256 equals it.",
    "I06": "A log line's time is its leading [YYYY-MM-DD HH:MM:SS]; B1 lines are from 2026-11-15 23:06; set-up = first with 'background pairs', done = the 'done in' line.",
    "X01": "Same-link iff the two per_lead.json links strings are equal (each holds link, c and ub).",
    "X02": "Per-draw aggregates (median/min/max over rivals, consensus, mean pairwise Spearman) are non-finite when any input is (did not occur).",
    "X03": "The consensus is the plain mean of the rivals' shares over the variable J; its ranking uses the same strict order (share desc, name asc).",
}


def main():
    res = {"schema_version": "round14_results_v1", "implementer": "A",
           "written_at": datetime.datetime.now().astimezone().replace(microsecond=0).isoformat(),
           "software": {"python": platform.python_version(), "numpy": np.__version__, "pyarrow": pyarrow.__version__,
                        "pandas": pandas.__version__, "scipy": scipy.__version__},
           "choices": CHOICES}
    probs = {}
    for p in L.PROBLEMS:
        with open(os.path.join(L.V_A, "work", "items_%s.json" % p), "r", encoding="utf-8") as fh:
            probs[p] = json.load(fh)
    res["problems"] = probs
    with open(os.path.join(L.V_A, "work", "b1.json"), "r", encoding="utf-8") as fh:
        res["b1"] = json.load(fh)
    res["notes"] = ("Implementer A, round 14. Items 1-8: a10_items1_8.py (reads no treeroute_B1 file); item 9: "
                    "a20_b1.py (defo identity first: exactly 0 with the same rows, players and variables, then fire, "
                    "pm25 and ndvi). pandas is used only by the inspection and spot-check scripts, scipy only by the "
                    "self-test and spot checks. Per-draw values: V\\A\\draws\\<p>.npz and b1_<p>.npz.")
    path = os.path.join(L.V_A, "results.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, allow_nan=False, indent=1)
    print("wrote", path, os.path.getsize(path), "bytes")


if __name__ == "__main__":
    main()
