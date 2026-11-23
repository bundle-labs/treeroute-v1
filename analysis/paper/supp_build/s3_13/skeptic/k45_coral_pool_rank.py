# Skeptic (version 5 check, item 2, V5-2): "a pool of earlier nearby survey visits". The engine's rule
# (engine\treeroute\route\neighbour.py L16-27, L365-374, read only; 02_method.md L53): the eligible candidates are the
# pass's router rows dated strictly before the row's issue day, other than the row; the pool is the 50 most similar
# in standardised tree inputs among the 150 nearest of them by haversine angle. A falsification test on the data at
# hand: the union of all 1,000 saved pools (SHAP\out\coral\lead_0\treeroute\background_keys.parquet) is a subset of
# the candidates, so for each sample row at most 149 eligible visits of that union may lie strictly nearer than the
# row's farthest pool visit (with a relative margin of 1e-9 on the angle, since the site keys round the coordinates
# to 4 decimals). Prints the largest such count and how many rows exceed 149. Read-only; prints only.
import math, sys
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
base = SHAP + r"\out\coral\lead_0\treeroute"
B = pd.read_parquet(base + r"\background_keys.parquet")
R = pd.read_parquet(base + r"\rows.parquet", columns=["row", "unit", "time"])
site = lambda u: str(u).split("|")[0]
ll = lambda u: (float(site(u).split("_")[-2]), float(site(u).split("_")[-1]))
U = B.drop_duplicates("unit")[["unit", "time"]].reset_index(drop=True)
clat = np.array([ll(u)[0] for u in U.unit])
clon = np.array([ll(u)[1] for u in U.unit])
cday = U.time.to_numpy()
cunit = U.unit.to_numpy()
p = math.pi / 180
ccos = np.cos(clat * p)
pos = {u: k for k, u in enumerate(cunit)}
counts, elig, pool_rank_max = [], [], []
for r, g in B.groupby("row"):
    x = R[R.row == r].iloc[0]
    lat, lon = ll(x.unit)
    a = np.sin((clat - lat) * p / 2) ** 2 + math.cos(lat * p) * ccos * np.sin((clon - lon) * p / 2) ** 2
    ang = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    ok = (cday < int(x.time)) & (cunit != x.unit)
    idx = np.array([pos[u] for u in g.unit])
    assert ok[idx].all()
    amax = ang[idx].max()
    nearer = int(((ang < amax * (1 - 1e-9)) & ok).sum())
    counts.append(nearer)
    elig.append(int(ok.sum()))
counts = np.array(counts)
print("union of the pools: %d distinct visits; eligible per sample row (from this union): min %d, median %d, max %d" % (
    len(U), min(elig), int(np.median(elig)), max(elig)))
print("eligible union visits strictly nearer than the row's farthest pool visit: min %d, median %d, max %d; rows above 149: %d of %d" % (
    counts.min(), int(np.median(counts)), counts.max(), int((counts > 149).sum()), len(counts)))
