"""Label-free guidance of the tool choice, NDVI, STAGE B (PROTOCOL.txt sha256 c51fc39a...).
Verifies the stage-A hashes, then opens test y ONLY to score. Writes ndvi/results_ndvi.json.
"""
import hashlib, json, time
import numpy as np, pandas as pd, pyarrow.parquet as pq, psutil

T0 = time.time()
PROTO_SHA = "c51fc39ad390204de8894fd3b50cd4f9cf0fc70a92eddf99214497fb6201eef4"
assert hashlib.sha256(open("D:/treeroute/analysis/guidance/PROTOCOL.txt", "rb").read()).hexdigest() == PROTO_SHA
RUN = "D:/treeroute/runs/ndvi/headline/20261016_d1de3158"
OUT = "D:/treeroute/analysis/guidance/ndvi"
for line in open(f"{OUT}/stageA.sha256.txt"):
    h, name = line.split()
    assert hashlib.sha256(open(f"{OUT}/{name}", "rb").read()).hexdigest() == h, "stage A file changed: " + name
V = json.load(open(f"{RUN}/verdict.json"))
ORIG_MAE = float(V["pooled_mae_adopted"]); BAND = float(V["band"])   # verdict.json:175, :4
assert V["adopted"] == "identity_plain_unweighted"
A = json.load(open(f"{OUT}/stageA_ndvi.json"))
MP = pd.read_parquet(f"{OUT}/method_preds_ndvi.parquet")
Y = pq.read_table(f"{RUN}/test_preds.parquet", columns=["unit", "time", "y"]).to_pandas()
assert (Y["unit"].to_numpy() == MP["unit"].to_numpy()).all() and (Y["time"].to_numpy() == MP["time"].to_numpy()).all()
y = Y["y"].to_numpy(float); C = MP["C"].to_numpy(float)
sc = np.isfinite(y) & np.isfinite(C)
mae_c = float(np.mean(np.abs(y[sc] - C[sc])))
G2 = {"scored_rows": int(sc.sum()), "chosen_test_mae": mae_c, "verdict": ORIG_MAE,
      "rel_diff": abs(mae_c - ORIG_MAE) / ORIG_MAE}
G2["pass"] = G2["rel_diff"] <= 1e-9
print("G2", G2, flush=True)
assert G2["pass"]
yr = MP["year"].to_numpy()
methods = [c for c in MP.columns if c not in ("unit", "time", "year", "C")]
res = {}
for mth in methods:
    p = MP[mth].to_numpy(float)
    nonfin = int((~np.isfinite(p[sc])).sum())
    mae = float(np.mean(np.abs(y[sc] - p[sc])))
    d = mae - ORIG_MAE
    same = bool(np.array_equal(p[sc], C[sc]))
    tag = "SAME" if same else ("HELPS" if d < 0 else ("HURTS" if d > 0 else "SAME-MAE"))
    per_year = {int(k): float(np.mean(np.abs(y[sc & (yr == k)] - p[sc & (yr == k)]))) for k in sorted(np.unique(yr[sc]))}
    res[mth] = {"test_mae": mae, "delta": d, "delta_over_band": d / BAND, "tag": tag,
                "rows_differ_from_C": int((p[sc] != C[sc]).sum()), "nonfinite_on_scored": nonfin,
                "per_year": per_year, "s2_no_harm_ok": bool(d <= 0.25 * BAND)}
orig_year = {int(k): float(np.mean(np.abs(y[sc & (yr == k)] - C[sc & (yr == k)]))) for k in sorted(np.unique(yr[sc]))}
sanity = {"alarm_ratio": A["alarm"]["ratio"], "alarm_ratio_part603": 1.19,
          "M3_mae": res["M3"]["test_mae"], "M3_part603": 0.0314608}
out = {"protocol_sha256": PROTO_SHA, "G2": G2, "orig": {"arm": V["adopted"], "test_mae": ORIG_MAE, "band": BAND,
       "quarter_band": 0.25 * BAND, "per_year": orig_year}, "methods": res, "sanity_part603": sanity,
       "runtime_s": round(time.time() - T0, 1),
       "peak_wset_GiB": round(getattr(psutil.Process().memory_info(), "peak_wset", 0) / 2 ** 30, 3)}
json.dump(out, open(f"{OUT}/results_ndvi.json", "w"), indent=1)
print("orig %.7f band %.6g" % (ORIG_MAE, BAND))
for k, v in res.items():
    print("%-20s %.7f  d=%+.3e  d/band=%+.4f  %-8s differ=%d" % (k, v["test_mae"], v["delta"], v["delta_over_band"], v["tag"], v["rows_differ_from_C"]))
print("sanity", sanity, "runtime %.1fs" % (time.time() - T0))
