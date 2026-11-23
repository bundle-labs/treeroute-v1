import json, numpy as np, pyarrow.parquet as pq
B = r"D:/treeroute/rivals/pm25/20261007_74e67609"
S = r"D:/treeroute/rivals_scratch/pm25/20261007_74e67609"
for L in (0, 6, 12):
    m = json.load(open(f"{B}/lead_{L}/model_ridge.json"))
    names = m["names"]; mean = np.array(m["mean"]); sd = np.array(m["sd"])
    coef = np.array(m["coef"]["1000.0"])
    idx = pq.read_table(f"{S}/lead_{L}_refit.index.parquet", columns=["time","y","n__log_c"]).to_pandas()
    y = idx["y"].to_numpy(); z0 = idx["n__log_c"].to_numpy()
    t = np.log(y + 1.5) - z0
    j = names.index("__normal__")
    print(f"lead {L}: n_fit {len(idx)} max time {idx.time.max()} | model intercept {m['intercept']:.9f} vs mean(log(y+c)-normal) on refit rows {t.mean():.9f} | normal mean in model {mean[j]:.9f} vs refit {z0.mean():.9f} | sd {sd[j]:.6f} vs {z0.std():.6f}")
    eff = coef * sd
    o = np.argsort(-np.abs(eff))[:12]
    print("   top standardized effects:", [(names[i], round(float(eff[i]), 4)) for i in o])
    print("   flags:", len(m["flags"]), m["flags"][:6], "dropped:", m["dropped"])
