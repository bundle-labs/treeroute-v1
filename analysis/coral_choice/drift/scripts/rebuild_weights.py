"""Rebuild the coral headline run's GLS weight models (test-pass model + 83 fold models) with the
engine's own pipeline objects, up to and including TableRunState.fit(need_inner=True), then dump
per-row sigma and weights. READ-ONLY on run/package/engine: run_root and temp_dir are redirected
under D:/treeroute/analysis/coral_choice/drift. Run with:  py -3.9 rebuild_weights.py
"""
import sys
from pathlib import Path

ENGINE = Path(r"C:\Users\<user>\Desktop\data set for reserch paper\engine")
sys.path.insert(0, str(ENGINE))
from treeroute import launch  # noqa: E402

launch.pin_threads()

import json  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from treeroute.fit import weights as W  # noqa: E402
from treeroute.package.schema import MachineFile  # noqa: E402
from treeroute.pipeline import stages as ST  # noqa: E402
from treeroute.pipeline.record import KIND_HEADLINE  # noqa: E402
from treeroute.pipeline.table_passes import TableRunState  # noqa: E402
from treeroute.pipeline.table_run import TablePipeline  # noqa: E402

OUT = Path(r"D:\treeroute\analysis\coral_choice\drift")
machine = MachineFile(run_root=str(OUT / "rebuild_root"), temp_dir=str(OUT / "rebuild_tmp"),
                      registry_dir="D:/treeroute/registry")
PKG = ENGINE / "datasets" / "coral"

# record the error target each forest is fitted on (wrapper only; the original runs unchanged)
CAPTURED = []
_orig_fit = W.fit_weight_model


def _wrapped(donor_rows, error_target):
    CAPTURED.append((np.asarray(donor_rows.grid_rows, dtype=np.int64).copy(),
                     np.asarray(error_target, dtype=np.float64).copy()))
    return _orig_fit(donor_rows, error_target)


W.fit_weight_model = _wrapped

p = TablePipeline(PKG, machine.run_root, KIND_HEADLINE, machine=machine, launch_record=launch.record())
dst = OUT / "out"
try:
    p._lock(); p._load(); p._groups(); p._preflight_target(); p._read(); p._derive(); p._open(); p._temp()
    print("FINGERPRINT", p.fingerprint)
    with TableRunState(p) as s:
        s.build_pool(need_inner=True)
        s.fit(need_inner=True)
        rows = np.asarray(p.table.row_ids, dtype=object)
        N = rows.size
        keys = np.arange(N, dtype=np.int64)
        X = ST.zero_filled(s.ctx_fit.features)(keys)
        wm = s.weights
        sig_T = wm.forest.sigma(keys, X)
        w_T = W.weights_for_rows(wm, keys, X)
        fitted_T = np.isin(keys, wm.forest.grid_rows)
        names = list(s.fold_weights.keys())
        sig_F = np.empty((len(names), N)); w_F = np.empty((len(names), N)); fit_F = np.zeros((len(names), N), bool)
        consts = {"test": {"cut": wm.cut, "floor": wm.sigma_floor, "lo": wm.clip_low, "hi": wm.clip_high,
                           "n": int(wm.forest.grid_rows.size)}}
        for i, g in enumerate(names):
            m = s.fold_weights[g]
            sig_F[i] = m.forest.sigma(keys, X)
            w_F[i] = W.weights_for_rows(m, keys, X)
            fit_F[i] = np.isin(keys, m.forest.grid_rows)
            consts[g] = {"cut": m.cut, "floor": m.sigma_floor, "lo": m.clip_low, "hi": m.clip_high,
                         "n": int(m.forest.grid_rows.size)}
        d = s.donor_fit
        donor = pd.DataFrame({"key": np.asarray(d.grid_rows, np.int64), "y": np.asarray(d.y, float),
                              "day": np.asarray(d.times, np.int64), "group": np.asarray(d.group_of_row, object)})
        tf = list(p.spec.tree_features)
        meta = pd.DataFrame({"row_id": rows, "group": np.asarray(p.table.groups, dtype=object),
                             "day": np.asarray(p.table.target_day, np.int64),
                             "is_test": np.asarray(p.table.is_test, bool)})
        for j, c in enumerate(tf):
            meta["f_" + c] = X[:, j]
        for c in p.spec.strata:
            meta["s_" + c] = np.asarray(p.table.strata[c], dtype=object)
        # error target (global, the same values per row in every model)
        err = np.full(N, np.nan)
        for gr, e in CAPTURED:
            prev = err[gr]
            if np.isfinite(prev).any() and not np.allclose(prev[np.isfinite(prev)], e[np.isfinite(prev)]):
                print("WARNING: error target differs between captures")
            err[gr] = e
        meta["err_target"] = err
        meta["sig_T"] = sig_T; meta["w_T"] = w_T; meta["fitted_T"] = fitted_T
        meta.to_parquet(dst / "rows.parquet")
        donor.to_parquet(dst / "donor_fit.parquet")
        np.save(dst / "sig_folds.npy", sig_F); np.save(dst / "w_folds.npy", w_F); np.save(dst / "fit_folds.npy", fit_F)
        (dst / "fold_names.json").write_text(json.dumps(names))
        (dst / "consts.json").write_text(json.dumps(consts, indent=1, default=float))
        print("captures", len(CAPTURED), "rows", N, "folds", len(names))
finally:
    p._release()
