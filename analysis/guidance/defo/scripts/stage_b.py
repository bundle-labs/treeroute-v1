"""Label-free guidance of the tool choice -- DEFO, STAGE B (scoring only).

Protocol: D:/treeroute/analysis/guidance/PROTOCOL.txt (sha256 c51fc39a...), sections 3 (G2, G4), 6, 7.
Verifies stageA.sha256.txt FIRST, then opens test y for the first time, only to score. Writes results_defo.json.
"""
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROTOCOL = Path("D:/treeroute/analysis/guidance/PROTOCOL.txt")
PROTOCOL_SHA = "c51fc39ad390204de8894fd3b50cd4f9cf0fc70a92eddf99214497fb6201eef4"
RUN = Path("D:/treeroute/runs/defo/headline/20261017_d71c61f4")
OUT = Path("D:/treeroute/analysis/guidance/defo")
CHOSEN = "log_c_corrector_unweighted"
REL = 1e-9
METHODS = ["T_twin", "M1", "M2", "M3", "M4", "M5", "M5raw", "M5_placebo_ungated", "M5_placebo_gated",
           "M6", "M6s", "M6_ungated", "M6s_ungated", "M6_placebo_ungated", "M6s_placebo_ungated",
           "M6_placebo_gated", "M6s_placebo_gated"]


def main():
    t0 = time.time()
    assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() == PROTOCOL_SHA
    for line in (OUT / "stageA.sha256.txt").read_text().split("\n"):
        if line.strip():
            h, name = line.split("  ")
            p = OUT / name if (OUT / name).exists() else OUT / "scripts" / name
            assert hashlib.sha256(p.read_bytes()).hexdigest() == h, "stage A hash mismatch: %s" % name
    print("stage A hashes verified")
    verdict = json.load(open(RUN / "verdict.json"))
    band = float(verdict["band"])
    orig = float(verdict["pooled_mae_adopted"])
    MP = pd.read_parquet(OUT / "method_preds_defo.parquet")
    T = pd.read_parquet(RUN / "test_preds.parquet", columns=["unit", "time", "year", "y", "arm__" + CHOSEN])
    assert (MP["unit"].to_numpy() == T["unit"].to_numpy()).all() and (MP["time"].to_numpy() == T["time"].to_numpy()).all()
    y = T["y"].to_numpy(np.float64)
    C = MP["C_chosen"].to_numpy()
    assert np.array_equal(C, T["arm__" + CHOSEN].to_numpy(np.float64))
    sc = np.isfinite(y) & np.isfinite(C)
    mae_c = float(np.mean(np.abs(y[sc] - C[sc])))
    g2 = {"scored_rows": int(sc.sum()), "test_rows": len(T), "chosen_test_mae": mae_c,
          "verdict_pooled_mae_adopted": orig, "rel": abs(mae_c - orig) / orig}
    g2["pass"] = g2["rel"] <= REL
    print("G2 %s: %.15f vs %.15f (rel %.1e), scored %d" % ("PASS" if g2["pass"] else "FAIL", mae_c, orig,
                                                           g2["rel"], sc.sum()))
    assert g2["pass"]
    yr = T["year"].to_numpy()[sc]
    ys, Cs = y[sc], C[sc]
    years = sorted(np.unique(yr))
    res = {"original": {"arm": CHOSEN, "test_mae": mae_c, "band": band, "quarter_band": 0.25 * band,
                        "per_year": {int(v): float(np.mean(np.abs(ys[yr == v] - Cs[yr == v]))) for v in years}},
           "G2": g2, "methods": {}}
    for m in METHODS:
        P = MP[m].to_numpy()[sc]
        assert np.isfinite(P).all(), m
        mae = float(np.mean(np.abs(ys - P)))
        d = mae - mae_c
        same = bool(np.array_equal(P, Cs))
        tag = "SAME" if same else ("HELPS" if d < 0 else ("HURTS" if d > 0 else "EQUAL-MAE"))
        res["methods"][m] = {"test_mae": mae, "delta": d, "delta_over_band": d / band, "tag": tag,
                             "rows_differing_from_C": int(np.sum(P != Cs)),
                             "S2_no_harm_defo": bool(d <= 0.25 * band),
                             "per_year": {int(v): float(np.mean(np.abs(ys[yr == v] - P[yr == v]))) for v in years}}
        print("%-22s MAE %.9f  delta %+.3e  /band %+.4f  %-6s differs %d" % (m, mae, d, d / band, tag,
                                                                            np.sum(P != Cs)))
    res["seconds"] = time.time() - t0
    json.dump(res, open(OUT / "results_defo.json", "w"), indent=1)


if __name__ == "__main__":
    main()
