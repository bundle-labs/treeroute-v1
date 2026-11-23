"""Light probe (read-only) to pin down ambiguous definitions for SPEC.json.
Not the post-hoc script. Reads only the needed columns of saved predictions."""
import sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

RUN = {
    "fire": "D:/treeroute/runs/fire/headline/20261017_869d1f38",
    "coral": "D:/treeroute/runs/coral/headline/20261020_f3b8e3da",
}
BOARD = {
    "fire": "D:/treeroute/rivals/fire/20261017_869d1f38",
    "coral": "D:/treeroute/rivals/coral/20261020_f3b8e3da",
}


def jk(v):
    v = np.asarray(v, float)
    n = v.size
    loo = np.array([np.delete(v, i).mean() for i in range(n)])
    se = np.sqrt((n - 1) / n * ((loo - loo.mean()) ** 2).sum())
    return v.mean(), se, v.mean() - 1.96 * se, v.mean() + 1.96 * se, n


def load(pkg, ours_col, learners):
    t = pq.read_table(RUN[pkg] + "/test_preds.parquet",
                      columns=["unit", "group", "time", "lead", "y", ours_col]).to_pandas()
    for L in learners:
        p = pq.read_table(BOARD[pkg] + "/lead_0/preds_%s.parquet" % L,
                          columns=["unit", "time", "lead", "arm__rival_" + L, "arm__rival_%s_raw" % L]).to_pandas()
        t = t.merge(p, on=["unit", "time", "lead"], how="left", validate="one_to_one")
    return t


def per_group_contrast(sub, rcol, ocol):
    g = sub.assign(er=(sub["y"] - sub[rcol]).abs(), eo=(sub["y"] - sub[ocol]).abs()).groupby("group")[["er", "eo"]].mean()
    d = (g["er"] - g["eo"]).sort_index()
    return d


# ---------------- fire
f = load("fire", "arm__arcsine_corrector_gls", ["lgbm_tweedie"])
f = f[np.isfinite(f["y"])]
print("fire labelled rows", len(f), "groups", f.group.nunique())
o, r = "arm__arcsine_corrector_gls", "arm__rival_lgbm_tweedie"
act = f[f.y > 0]
print("active rows", len(act), "groups", act.group.nunique(),
      "mae ours %.6f tweedie %.6f" % ((act.y - act[o]).abs().mean(), (act.y - act[r]).abs().mean()))
d = per_group_contrast(act, r, o)
print("active jk", jk(d.values), "ours better", int((d > 0).sum()))
z = f[f.y == 0]
print("zero rows", len(z), "share %.4f" % (len(z) / len(f)), "mean pred ours %.6f tw %.6f" % (z[o].mean(), z[r].mean()))
for name, thr_fn in (("q99_all_ge", lambda y: y >= np.quantile(y, 0.99)),
                     ("q99_all_gt", lambda y: y > np.quantile(y, 0.99)),
                     ("q99_pos_ge", None)):
    if thr_fn is None:
        continue
    m = thr_fn(f.y.values)
    s = f[m]
    print(name, "thr %.6f" % np.quantile(f.y.values, 0.99), "n", int(m.sum()),
          "mean y %.4f ours %.4f tw %.4f mae ours %.4f tw %.4f groups %d" % (
              s.y.mean(), s[o].mean(), s[r].mean(), (s.y - s[o]).abs().mean(), (s.y - s[r]).abs().mean(), s.group.nunique()))
# top 1% of the active rows
qa = np.quantile(act.y.values, 0.99)
print("q99 of active", qa, int((act.y >= qa).sum()))
# top-k by rank
srt = f.sort_values("y", ascending=False)
for k in (947, 949):
    s = srt.head(k)
    print("top-%d by rank: min y %.6f mae ours %.4f tw %.4f" % (k, s.y.min(), (s.y - s[o]).abs().mean(), (s.y - s[r]).abs().mean()))

# ---------------- coral
learners = ["ridge", "rf", "lgbm", "lgbm_tweedie", "hgb_l1"]
c = load("coral", "arm__arcsine_corrector_gls", learners)
c = c[np.isfinite(c["y"])]
o = "arm__arcsine_corrector_gls"
act = c[c.y > 0]
print("coral active", len(act), "groups", act.group.nunique(), "ours %.3f" % (act.y - act[o]).abs().mean())
for L in learners:
    rc = "arm__rival_" + L
    d = per_group_contrast(act, rc, o)
    print("  ", L, "mae %.3f" % (act.y - act[rc]).abs().mean(), "jk", tuple(round(x, 3) for x in jk(d.values)[:4]),
          "ours better groups", int((d > 0).sum()), "of", d.size)
edges = [1.91619047625, 7.255, 23.9575]
yv = c.y.values
idx = np.searchsorted(np.asarray(edges), yv, side="left")
names = np.array(["B1", "B2", "B3", "B4"])
binv = np.where(yv == 0, "B0", names[np.minimum(idx, 3)])
c = c.assign(bin=binv)
for b in ["B0", "B1", "B2", "B3", "B4"]:
    s = c[c.bin == b]
    print("bin", b, len(s), "ours %.3f hgb_l1 %.3f" % ((s.y - s[o]).abs().mean(), (s.y - s["arm__rival_hgb_l1"]).abs().mean()))
for lo, hi, nm in ((0, 0, "zero"), (0, 10, "(0,10)"), (10, 50, "[10,50)"), (50, 1e9, ">=50")):
    if nm == "zero":
        s = c[c.y == 0]
    elif nm == "(0,10)":
        s = c[(c.y > 0) & (c.y < 10)]
    elif nm == "[10,50)":
        s = c[(c.y >= 10) & (c.y < 50)]
    else:
        s = c[c.y >= 50]
    print("cut", nm, len(s), "ours %.3f hgb_l1 %.3f" % ((s.y - s[o]).abs().mean(), (s.y - s["arm__rival_hgb_l1"]).abs().mean()))
