import json, glob, os
import numpy as np, pandas as pd, pyarrow.parquet as pq
BASE = r"D:\treeroute\rival_export\pm25\20261007_74e67609"
C = 1.5
def month(t): return ((np.asarray(t) - 1) % 12) + 1
for L in (0, 6, 12):
    man = json.load(open(BASE + r"\lead_%d\export_manifest.json" % L))
    fc, gc_ = man["cuts"]["fit_cut"], man["cuts"]["guard_cut"]
    files = sorted(glob.glob(BASE + r"\lead_%d\train\*.parquet" % L))
    tot = dict(test=0, refit=0, h_ok=0, h_n=0, e_test_id=0.0, e_test_lc=0.0, e_ref=0.0, e_g=0.0, g_rows=0,
               tmax_refit=0, tmax_fitg=0, tmin_test=10**9, tmin_surf=10**9, tmax_surf=0, cross=0)
    gflag, sflag = ("r_tune", "r_inner") if L == 0 else ("r_guardfit", "r_guard")
    for f in files:
        g = os.path.basename(f)
        tr = pq.read_table(f, columns=["unit", "time", "y", "r_refit", gflag, sflag, "nfit__identity", "nfit__log_c", "x__hist_last_1"]).to_pandas()
        te = pq.read_table(BASE + r"\lead_%d\test\%s" % (L, g), columns=["unit", "time", "nfit__identity", "nfit__log_c"]).to_pandas()
        gs = pq.read_table(BASE + r"\lead_%d\guardside\%s" % (L, g), columns=["unit", "time", "ngd__identity"]).to_pandas()
        ref = tr[tr.r_refit]
        tot["tmax_refit"] = max(tot["tmax_refit"], int(ref.time.max()))
        tot["tmax_fitg"] = max(tot["tmax_fitg"], int(tr[tr[gflag]].time.max()))
        s = tr[tr[sflag]]
        if len(s):
            tot["tmin_surf"] = min(tot["tmin_surf"], int(s.time.min())); tot["tmax_surf"] = max(tot["tmax_surf"], int(s.time.max()))
        tot["tmin_test"] = min(tot["tmin_test"], int(te.time.min()))
        tot["cross"] += int((tr[gflag] & tr[sflag]).sum())
        tab = ref.assign(mo=month(ref.time)).groupby(["unit", "mo"])["y"].mean()
        tabl = ref.assign(mo=month(ref.time), z=np.log(ref.y + C)).groupby(["unit", "mo"])["z"].mean()
        k = pd.MultiIndex.from_arrays([te.unit, month(te.time)])
        tot["e_test_id"] = max(tot["e_test_id"], float(np.nanmax(np.abs(tab.reindex(k).to_numpy() - te.nfit__identity.to_numpy()))))
        tot["e_test_lc"] = max(tot["e_test_lc"], float(np.nanmax(np.abs(tabl.reindex(k).to_numpy() - te.nfit__log_c.to_numpy()))))
        k2 = pd.MultiIndex.from_arrays([ref.unit, month(ref.time)])
        tot["e_ref"] = max(tot["e_ref"], float(np.nanmax(np.abs(tab.reindex(k2).to_numpy() - ref.nfit__identity.to_numpy()))))
        gf = tr[tr[gflag]]
        tabg = gf.assign(mo=month(gf.time)).groupby(["unit", "mo"])["y"].mean()
        k3 = pd.MultiIndex.from_arrays([gs.unit, month(gs.time)])
        tot["e_g"] = max(tot["e_g"], float(np.nanmax(np.abs(tabg.reindex(k3).to_numpy() - gs.ngd__identity.to_numpy()))))
        tot["g_rows"] += len(gs)
        yl = ref.set_index(["unit", "time"])["y"]
        newest = ref.time - (1 if L == 0 else L)
        a = yl.reindex(pd.MultiIndex.from_arrays([ref.unit, newest])).to_numpy()
        ok = np.isfinite(a)
        tot["h_ok"] += int(np.isclose(ref.x__hist_last_1.to_numpy(np.float64)[ok], a[ok].astype(np.float32).astype(np.float64), atol=1e-6).sum())
        tot["h_n"] += int(ok.sum())
        tot["test"] += len(te); tot["refit"] += len(ref)
    print("lead %d (fit cut %d, guard cut %d, %d groups): %s" % (L, fc, gc_, len(files), json.dumps(tot)))
