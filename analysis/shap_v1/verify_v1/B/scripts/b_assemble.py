# Implementer B, round 14: assemble V\B\results.json from V\B\work\problems.json (items 1-8, b_compare.py) and
# V\B\work\b1.json (item 9, b_b1.py), with the one-line choices (the full entries are in V\B\choices.md).
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import pyarrow
import scipy
import b_lib as L

CHOICES = {
    "C01": "Flagged rows would enter every statistic; no row of any piece is flagged (resid_flag false everywhere).",
    "C02": "I = mean over regions of the within-region mean |phi| (each region weighs 1, its rows 1/n_r); on a draw each drawn copy of a region weighs 1.",
    "C03": "Signed mean S with the same region weighting as I, phi in place of |phi|.",
    "C04": "j in J when I_m(j) > 1e-12 * sum_k I_m(k) (region-weighted, full sample, strict) for some model; a zero-total model adds nothing.",
    "C05": "Some model = every model of per_lead.json models (cross-link and declined included); one J per problem and level for every statistic; B1 never enters it.",
    "C06": "A player without a column has phi 0 for that model (I, S, share 0; ranked with the zeros by name); structural zeros = union of all models' columns minus J.",
    "C07": "J, B1's pair J and the determined signs fixed at the full sample; top-k sets, their unions and the consensus found again on each draw.",
    "C08": "n_J has no interval (J fixed); n_nonzero, sign_n_determined and sign_n_agree get intervals (recomputed per draw).",
    "C09": "Nonzero = I_m(j) > 0 (phi != 0 on some row), counted over the model's own columns (outside J too); equals meta.json's counts.",
    "C10": "Ties = exact float64 equality of I; average ranks; ordered rankings: larger I first, ties by the player name (with x__/c__ prefix) in Python string order ascending.",
    "C11": "Spearman = Pearson correlation of average ranks; top-20 union: ranks taken again within the union of the two top-20 sets.",
    "C12": "Fewer than k players: the top-k set is all of J; top-20 Jaccard only when the full-sample J (B1: the pair's J) has 200 or more players.",
    "C13": "RBO = ((1-p)/p) sum_{d=1..k} (X_d/d) p^d + (X_k/k) p^k over the full tie-broken rankings of J (eq. 32 with s = l = k); self-RBO = 1.",
    "C14": "TV = 0.5 * sum |s_a - s_b| over J (shares over J); family TV = 0.5 * sum over the five family shares.",
    "C15": "Family attribution = row sum of all its variables' variable-level phi; importance = region-weighted mean |sum|; shares over the five families; empty family = 0; feature pairs reuse it.",
    "C16": "Precedence normal > hist_* > calendar/ctx:* > global-index rule > local drivers; one value per time step = exact equality at every test time step, missing counted as a value.",
    "C17": "Determined: percentile 95% interval of S excludes 0 strictly (fixed); agreement = n_agree / n_determined on the union of the two top-10 sets, null when n_determined = 0.",
    "C18": "Undefined (null/NaN): Spearman or tau-b with an all-tied side, sign agreement with nothing determined, W with fewer than two rankings, main-row rival numbers of fire, item 8 draws without such rows.",
    "C19": "W over the main set on the level's J with the tie correction 12S/(m^2(n^3-n) - m sum T); mean pairwise Spearman = mean of the main-set pairs' Spearman over J.",
    "C20": "Stability = mean over the finite draws of Spearman(full-sample I, draw I) over J; no interval (n_finite null).",
    "C21": "numpy.percentile linear interpolation at 2.5 and 97.5 over the finite draws only; an interval whenever at least one draw is finite.",
    "C22": "Median over rivals (even count: mean of the two middle values), recomputed per draw; the range as min and max, each with its own per-draw interval.",
    "C23": "The median of the rivals' own-history shares (per draw); a rival is named only when the count is odd and exactly one rival has the median value.",
    "C24": "Own-history share = the own-history family share of C15.",
    "C25": "Every arcsine-link model of every problem (coral 4, fire 1); its own rows with pre > 0; variable level over the level's J; regions with such rows weigh 1; intervals from the same draws.",
    "I01": "Region = rows.parquet column group (same row and group in every piece; G distinct groups = the draw matrix's columns).",
    "I02": "Row b = draw b, column k = k-th region drawn; value = index into sorted(distinct group); the matrix is reproduced by SHA-256('shap_v1|AW4|<p>|0|<b>|<k>')[:8] mod G.",
    "I03": "The SHA-256 covers every byte of the .npy file (header and data); it equals per_lead.json draws_sha256 on all five problems.",
    "I04": "The lead's test set = the rivals' export of the headline run, D:\\treeroute\\rival_export\\<p>\\<run>\\lead_0\\test\\*.parquet; read unit, time, issue and the candidate x__ columns.",
    "I05": "The registered sample = the sample= field of the problem's SAMPLE_REGISTER.txt line (leads include 0); every B1 meta.json matches it.",
    "I06": "A log line's time is its bracketed time; B1 lines from 2026-11-15 23:06:00; set-up line = first with 'background pairs', done line = first 'done in' after it.",
    "X01": "An arcsine model's nonzero rows use its own pre column.",
    "X02": "The families named by their columns take precedence over the global-index test (calendar stays context and calendar).",
    "X03": "The feature-level pairs' tv_family_shares equals the variable-level one (families come from variable-level phi).",
    "X04": "main_row.kendall_w is the variable-level W of item 5, computed again.",
    "X05": "A J player with zero importance on a draw keeps share 0 and ranks with the zeros by name.",
}


def main():
    problems = json.loads((L.VB / "work" / "problems.json").read_text(encoding="utf-8"))
    b1 = json.loads((L.VB / "work" / "b1.json").read_text(encoding="utf-8"))
    assert set(problems) == {"coral", "defo", "fire", "pm25", "ndvi"}
    res = {"schema_version": "round14_results_v1", "implementer": "B",
           "written_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "software": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                        "pyarrow": pyarrow.__version__, "scipy": scipy.__version__},
           "choices": CHOICES,
           "problems": {p: problems[p] for p in ["coral", "defo", "fire", "pm25", "ndvi"]},
           "b1": {p: b1[p] for p in ["coral", "defo", "fire", "pm25", "ndvi"]},
           "notes": ("Implementer B. Items 1-8: scripts\\b_compare.py (opens nothing under treeroute_B1). Item 9: "
                     "scripts\\b_b1.py (defo's identity check first: 0 at both levels with the same rows, players and "
                     "variables, so the fire, pm25 and ndvi B1 numbers follow). Global-index rule: scripts\\b_global_index.py. "
                     "Choices in choices.md.")}
    L.dump_json(res, L.VB / "results.json")
    print("results.json written:", os.path.getsize(L.VB / "results.json"), "bytes")


if __name__ == "__main__":
    main()
