"""Train the leakage-free ANNUAL (per cell-year) REGIME on EVERY region (89 train + 44 test = 133) and SAVE the
regime features (clf_dry = P_dry, clf_wet = P_wet) into the MAIN monthly panel. Same proven construction as
test_cb89_bundle.py: per-cell tertile of annual NDVI (cell-RELATIVE anomaly), OOF GroupKFold-on-cell for
2002-2019, and a classifier fit on <=2019 features PREDICTS the 2020-2023 regime (never uses test-year NDVI) ->
leakage-free vs the canonical train/test window. Logistic regime classifier (CatBoost MultiClass hangs on GPU).

TWO PHASES, both crash-safe + progress-visible, all regions test+train:
  Phase 1 (COMPUTE, read-only on the panel): streamed 2000-cell chunks -> annual regime -> sidecar
    D:\panel_regime\{region}.parquet [cell_id, year, clf_dry, clf_wet]. Skips a region whose sidecar exists;
    REUSES D:\cb89_test_regime\{region}.parquet when present (identical full-cell regime the cb89 test built).
  Phase 2 (INJECT into the panel): merge clf_dry/clf_wet into each {region}_monthly_{year}.parquet IN PLACE via
    atomic temp + os.replace; idempotent (year-files that already carry the two cols are skipped; a re-run
    drops+re-adds); reversible (just drop the 2 cols). Retries os.replace on a Windows file-lock.

RUN (YOUR terminal, resumable):
  py -3.9 presplit_cc/save_regime_to_panel.py --sidecar-only   # PHASE 1 only -- no panel touched (do this first)
  py -3.9 presplit_cc/save_regime_to_panel.py                  # compute-or-reuse + INJECT into the panel
  [--force  recompute sidecars / rewrite all year-files] [region ...  limit to named regions]
NOTE: run the injection (no --sidecar-only) only when test_cb89_bundle.py is NOT reading the panel -- a concurrent
open handle makes the Windows atomic replace fail (it retries, then leaves the original intact to redo next run).
"""
import gc
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import monthly_loader as ML  # noqa: E402
from experiment_regime_stream import build_feats, load, CAT  # noqa: E402
from train_small_bundle_regime_thar import (cellyear_regime, _ann, rfiles, region_cells,  # noqa: E402
                                            BATCH_CELLS, SEED, TARGET)
import train_small_bundle_regime_thar as REG  # noqa: E402

import warnings  # noqa: E402
from sklearn.exceptions import ConvergenceWarning  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402
warnings.filterwarnings("ignore", category=ConvergenceWarning)          # collinear climate feats -> lbfgs cap; harmless
REG.USE_GPU = False
REG._clf = lambda X, y: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(X, y)

PANEL = ML.PANEL_DIR
SIDE = r"D:\panel_regime"                                                # the leakage-free regime sidecars
CB89 = r"D:\cb89_test_regime"                                            # identical full-cell regimes cb89 already built
os.makedirs(SIDE, exist_ok=True)


def compute_regime(region, rt):
    """Return [cell_id, year, clf_dry, clf_wet]; cache to the sidecar. Reuse cb89's if present."""
    side = os.path.join(SIDE, f"{region}.parquet")
    if os.path.exists(side):
        return pd.read_parquet(side)
    files = rfiles(region)
    cells = region_cells(files)
    cb = os.path.join(CB89, f"{region}.parquet")
    if os.path.exists(cb):
        reg = pd.read_parquet(cb)[["cell_id", "year", "clf_dry", "clf_wet"]]
        if reg.cell_id.nunique() >= len(cells):                                     # FULL coverage -> safe to reuse
            tmp = side + ".tmp"; reg.to_parquet(tmp, index=False); os.replace(tmp, side)
            print(f"    {region}: regime reused from cb89_test_regime ({len(reg):,} cell-years)", flush=True)
            return reg
        print(f"    {region}: cb89 regime covers {reg.cell_id.nunique():,}/{len(cells):,} cells (capped) "
              f"-> recompute fresh", flush=True)
    cl = cells.copy(); np.random.RandomState(SEED).shuffle(cl)
    chunks = [cl[i:i + BATCH_CELLS].tolist() for i in range(0, len(cells), BATCH_CELLS)]
    print(f"    {region}: computing regime over {len(cells):,} cells -> {len(chunks)} chunks", flush=True)
    anns = []
    for k, ch in enumerate(chunks):
        d = load(files, ["cell_id", "year", TARGET] + REG.FEATS0, ch)
        d = d[d[TARGET].notna()]
        anns.append(_ann(d))
        if (k + 1) % 8 == 0 or (k + 1) == len(chunks):
            print(f"      regime chunk {k+1}/{len(chunks)} ({time.time()-rt:.0f}s)", flush=True)
    reg = cellyear_regime(pd.concat(anns, ignore_index=True), test_region=True)     # OOF <=2019 + predicted 2020-2023
    reg = reg[["cell_id", "year", "clf_dry", "clf_wet"]]
    tmp = side + ".tmp"; reg.to_parquet(tmp, index=False); os.replace(tmp, side)
    del anns; gc.collect()
    return reg


def _schema_names(f):
    try:
        import pyarrow.parquet as pq
        return set(pq.ParquetFile(f).schema.names)                                  # metadata only, no data read
    except Exception:
        return set(pd.read_parquet(f).columns)


def _atomic_replace(tmp, f, tries=5):
    for a in range(tries):
        try:
            os.replace(tmp, f); return True
        except PermissionError:                                                     # panel file open elsewhere (Windows lock)
            time.sleep(2.0 * (a + 1))
    try:
        os.remove(tmp)                                                              # give up cleanly -> original intact, redo next run
    except OSError:
        pass
    return False


def inject(region, reg, force):
    """Merge clf_dry/clf_wet into each panel year-file IN PLACE (atomic). Returns (written, skipped, locked)."""
    by_year = {int(y): g[["cell_id", "clf_dry", "clf_wet"]] for y, g in reg.groupby("year")}
    written = skipped = locked = 0
    for f in rfiles(region):
        if {"clf_dry", "clf_wet"} <= _schema_names(f) and not force:
            skipped += 1; continue
        year = int(os.path.basename(f).rsplit("_", 1)[1].split(".")[0])
        df = pd.read_parquet(f).drop(columns=["clf_dry", "clf_wet"], errors="ignore")
        rr = by_year.get(year, pd.DataFrame({"cell_id": [], "clf_dry": [], "clf_wet": []}))
        df = df.merge(rr, on="cell_id", how="left")
        tmp = f + ".regime.tmp"
        df.to_parquet(tmp, index=False)
        if _atomic_replace(tmp, f):
            written += 1
        else:
            locked += 1
            print(f"      {os.path.basename(f)}: LOCKED (open elsewhere) -> left original, will redo", flush=True)
        del df; gc.collect()
    return written, skipped, locked


def main():
    t0 = time.time()
    sidecar_only = "--sidecar-only" in sys.argv
    force = "--force" in sys.argv
    named = [a for a in sys.argv[1:] if not a.startswith("--")]

    tf = rfiles("thar_desert")
    tsamp = load(tf, None, region_cells(tf)[:200].tolist())
    _, feats_wm, _ = build_feats(tsamp, None)
    REG.FEATS0 = [c for c in feats_wm if c != CAT and "_lag" not in c and "_roll" not in c and "_wytd" not in c
                  and c not in ("api_precip", "api_soilmoist", "consec_dry_months", "months_since_sig_rain")]
    del tsamp

    donors, test = ML.split_regions()
    regions = named or (list(donors) + list(test))
    mode = "PHASE 1 (compute sidecars only -- panel untouched)" if sidecar_only else "compute/reuse + INJECT into panel"
    print(f"REGIME -> PANEL | {len(regions)} regions (test+train) | {len(REG.FEATS0)} regime feats | {mode}"
          f"{' | --force' if force else ''}\n", flush=True)

    t_all, n = time.time(), 0
    tot_w = tot_s = tot_l = 0
    for i, region in enumerate(regions, 1):
        rt = time.time()
        if not rfiles(region):
            print(f"[{i}/{len(regions)}] {region}: no panel -> skip", flush=True); continue
        side_exists = os.path.exists(os.path.join(SIDE, f"{region}.parquet"))
        if sidecar_only and side_exists and not force:
            print(f"[{i}/{len(regions)}] {region}: sidecar done -> skip", flush=True); continue
        print(f"[{i}/{len(regions)}] {region}: START", flush=True)

        reg = compute_regime(region, rt)
        if sidecar_only:
            print(f"[{i}/{len(regions)}] {region}: sidecar saved ({len(reg):,} cell-years, {time.time()-rt:.0f}s)\n", flush=True)
            n += 1; continue

        w, s, lk = inject(region, reg, force)
        tot_w += w; tot_s += s; tot_l += lk; n += 1
        el = time.time() - t_all; eta = (el / n) * (len(regions) - i)
        print(f"[{i}/{len(regions)}] {region}: DONE | {w} year-files written, {s} already-had, {lk} locked "
              f"({time.time()-rt:.0f}s) | {n} this run, {el/60:.0f}m elapsed, ~{eta/3600:.1f}h ETA\n", flush=True)
        gc.collect()

    if sidecar_only:
        print(f"\nPHASE 1 DONE. {n} regime sidecars in {SIDE}. Next: inject with the no-flag run "
              f"(when test_cb89 is not reading the panel).")
    else:
        print(f"\nALL DONE. injected {tot_w} year-files, {tot_s} already-had, {tot_l} left-locked (rerun to finish). "
              f"clf_dry/clf_wet now in the panel + sidecars in {SIDE}. ({time.time()-t0:.0f}s)")
    print("SAVE_REGIME_DONE")


if __name__ == "__main__":
    main()
