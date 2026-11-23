"""Label-free guidance, FIRE, STAGE B: open the test labels ONLY to score stage A's frozen predictions.

Protocol: D:/treeroute/analysis/guidance/PROTOCOL.txt section 6-7. Checks stageA.sha256.txt first.
"""
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

T0 = time.time()
OUT = Path("D:/treeroute/analysis/guidance/fire")
RUN = Path("D:/treeroute/runs/fire/headline/20261017_869d1f38")


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


for line in open(OUT / "stageA.sha256.txt"):
    h, name = line.split()
    assert sha_file(OUT / name) == h, f"stage A file changed: {name}"
A = json.load(open(OUT / "stageA_fire.json"))
P = pq.read_table(OUT / "method_preds_fire.parquet").to_pandas()
Y = pq.read_table(RUN / "test_preds.parquet", columns=["unit", "time", "y"]).to_pandas()
assert (Y["unit"].astype(str).to_numpy() == P["unit"].to_numpy()).all() and (Y["time"] == P["time"]).all()
verdict = json.load(open(RUN / "verdict.json"))
band = float(verdict["band"])
orig = float(verdict["pooled_mae_adopted"])
y = Y["y"].to_numpy(np.float64)
C = P["C"].to_numpy()
scored = np.isfinite(y) & np.isfinite(C)
c_mae = float(np.mean(np.abs(y[scored] - C[scored])))
G2 = abs(c_mae - orig) <= 1e-9 * abs(orig)
years = P["year"].to_numpy()

METHODS = ["M1", "M2", "M3", "M4", "M5", "M5raw", "M5_placebo_ungated", "M5_placebo_gated",
           "M6", "M6s", "M6raw", "M6sraw", "M6_placebo_ungated", "M6s_placebo_ungated",
           "M6_placebo_gated", "M6s_placebo_gated", "T"]
res = {"G2": {"recomputed": c_mae, "verdict": orig, "ok": bool(G2)}, "scored_rows": int(scored.sum()),
       "band": band, "quarter_band": 0.25 * band, "original": {"arm": A["chosen"], "test_mae": c_mae,
       "per_year": {int(yr): float(np.mean(np.abs(y[scored & (years == yr)] - C[scored & (years == yr)])))
                    for yr in sorted(set(years))}}, "methods": {}}
for m in METHODS:
    v = P[m].to_numpy()
    ok = scored & np.isfinite(v)
    assert ok.sum() == scored.sum(), (m, int(ok.sum()))
    mae = float(np.mean(np.abs(y[scored] - v[scored])))
    d = mae - c_mae
    same = bool(np.array_equal(v[scored], C[scored]))
    tag = "SAME" if same else ("HELPS" if d < 0 else ("HURTS" if d > 0 else "SAME-MAE"))
    res["methods"][m] = {
        "test_mae": mae, "delta": d, "delta_over_band": d / band, "tag": tag,
        "rows_differing_from_C": int(np.sum(v[scored] != C[scored])),
        "S2_no_harm(delta<=0.25band)": bool(d <= 0.25 * band),
        "per_year": {int(yr): float(np.mean(np.abs(y[scored & (years == yr)] - v[scored & (years == yr)])))
                     for yr in sorted(set(years))},
    }
# Part 603 sanity (fire: alarm 0.90, M3 0.004409)
res["sanity_part603"] = {"alarm_ratio": A["alarm"]["ratio"], "expected_alarm": 0.90,
                         "M3": res["methods"]["M3"]["test_mae"], "expected_M3": 0.004409}
# surface-only diagnostic of the M6 ties (labels of the SURFACE only)
S = pq.read_table(RUN / "inner_preds.parquet",
                  columns=["y", "arcsine_corrector_gls@level=100.0,ratio=1.0",
                           "arcsine_corrector_unweighted@level=100.0,ratio=1.0"]).to_pandas()
cs, ts = S.iloc[:, 1].to_numpy(), S.iloc[:, 2].to_numpy()
res["surface_tie_diagnostic"] = {"rows": len(S), "C_equals_T": int(np.sum(cs == ts)),
                                 "y_zero": int(np.sum(S["y"].to_numpy() == 0)),
                                 "ties_with_C_equals_T": int(np.sum((cs == ts)))}
res["seconds"] = time.time() - T0
json.dump(res, open(OUT / "results_fire.json", "w"), indent=1)
print(json.dumps({"G2": res["G2"], "orig": c_mae, "band": band, "sanity": res["sanity_part603"],
                  "ties": res["surface_tie_diagnostic"]}, indent=1))
for m, r in res["methods"].items():
    print(f"{m:22s} {r['test_mae']:.9f} d={r['delta']:+.3e} d/band={r['delta_over_band']:+.4f} {r['tag']:8s} "
          f"diff_rows={r['rows_differing_from_C']} S2={r['S2_no_harm(delta<=0.25band)']}")
