"""Propagate the 12 columns that were built for thar_desert alone to ALL 133 REGIONS: 157 -> 169 columns.

WHAT AND WHY (user's instruction, 2026-07-31). On 2026-07-30 thar was given 7 standardised drought indices and 5
raw water-balance columns, which broke the uniform schema, so `revert_thar_panel.py` removed them again. The
right fix is the other direction: give every region the same 12 columns. A UNIFORM SCHEMA IS A STRUCTURAL
PREREQUISITE -- a donor-trained tree cannot be applied to a target whose column set differs -- and
[[reference_feature_value_is_regional]] measured these very columns as −0.006 on thar and +0.024 on
australian_mulga. Present-everywhere + flagged-per-region is the design that lets each region's router use what
helps it; DROPPING a column because one region does not want it is what makes the schema region-specific.

  scpdsi, spi_01m, spi_03m, spi_06m, spi_12m, spi_24m, eddi     sampled rasters, from D:\\env_noauth sidecars
  wbal_mm      = V02_total_precip_mm - V07_total_ref_ET_mm      derived here, no download
  wbal_roll3/6/12/24 = trailing sums of wbal_mm                 derived here, no download

The wbal family is leak-free by construction (no distribution fit, no reference period, no provider calibration)
and complete through 2023 because TerraClimate is. The drought family is whole-record calibrated -- disclosed,
unchanged by this script.

NEVER REBUILD, ALWAYS JOIN ([[reference_panel_rebuild_hazard]]). `assemble_monthly_panel.py` emits only 115 of
the 157 columns, so running it would silently revert 49 downstream columns. This script only ADDS columns to
existing year-files.

NO 35 GB BACKUP, BY DESIGN. The operation is a pure column ADD, so it is exactly reversible: `--revert` drops the
same 12 names. A full copy of the 35 GB panel would leave only 34 GB free on D:. Crash safety instead comes from
writing each year-file to `.tmp` and `os.replace`-ing it, which is atomic -- a kill mid-run leaves every file
either fully old or fully new, never truncated.

ROLLING SUMS ARE COMPUTED ACROSS YEAR BOUNDARIES. The panel is one file per year but `wbal_roll24` needs the
whole 264-month series, so each region is loaded as a dense (ncell, 264) grid, rolled by cumsum, and scattered
back. min_periods == window, so the head of record is NaN (8.71% for roll24) -- expected, all inside the
training window, handled by the existing <=2019 median imputer.

  py -3.9 presplit_cc/add_drought_wbal_all_regions.py --check    # column count per region, no writes
  py -3.9 presplit_cc/add_drought_wbal_all_regions.py --dry      # full dry run: validate, report, no writes
  py -3.9 presplit_cc/add_drought_wbal_all_regions.py            # apply (resumable: 169-col regions skipped)
  py -3.9 presplit_cc/add_drought_wbal_all_regions.py --fixwbal  # repair the wbal sentinel escape in place
  py -3.9 presplit_cc/add_drought_wbal_all_regions.py --addobs   # add eddi_observed (169 -> 170)
  py -3.9 presplit_cc/add_drought_wbal_all_regions.py --revert   # undo everywhere
"""
import glob
import os
import sys
import time

import numpy as np
import pandas as pd

PANEL = r"D:\monthly_panel"
DROUGHT_DIR = r"D:\env_noauth"
DR = ["scpdsi", "spi_01m", "spi_03m", "spi_06m", "spi_12m", "spi_24m", "eddi"]
WB = ["wbal_mm", "wbal_roll3", "wbal_roll6", "wbal_roll12", "wbal_roll24"]
NEW = DR + WB
OBS = ["eddi_observed"]          # see --addobs; 1.0 where eddi was measured, 0.0 where NOAA withheld it
ROLLS = [("wbal_roll3", 3), ("wbal_roll6", 6), ("wbal_roll12", 12), ("wbal_roll24", 24)]
P_COL, ET_COL = "V02_total_precip_mm", "V07_total_ref_ET_mm"
Y0, Y1 = 2002, 2023
NMON = (Y1 - Y0 + 1) * 12
NCOL_BEFORE, NCOL_AFTER, NCOL_OBS = 157, 169, 170


COVERAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit", "DROUGHT_WBAL_COVERAGE.csv")


def _arg(f, d=None):
    return sys.argv[sys.argv.index(f) + 1] if f in sys.argv else d


def _report(r, ncell, rows, nan, dry):
    """Append this region's per-column NaN fraction. Coverage is NOT uniform and the run must say so: the CRU
    0.5deg scPDSI land mask leaves namib_desert 93.8% NaN because the Namib is a narrow coastal strip, and
    other coastal/high-latitude regions will do the same. A column that is ~all-NaN in a region is exactly what
    the per-region dead-feature flagger (`tree_route_ideas.py --flagdead`) exists to handle -- but only if it
    is on record rather than discovered mid-experiment."""
    if dry:
        return
    os.makedirs(os.path.dirname(COVERAGE), exist_ok=True)
    new = not os.path.exists(COVERAGE)
    with open(COVERAGE, "a", encoding="utf-8") as fh:
        if new:
            fh.write("region,cells,rows," + ",".join(f"nan_{c}" for c in NEW) + "\n")
        fh.write(f"{r},{ncell},{rows}," + ",".join(f"{nan[c]:.6f}" for c in NEW) + "\n")


def regions():
    rs = {os.path.basename(p).split("_monthly_")[0] for p in glob.glob(os.path.join(PANEL, "*_monthly_*.parquet"))}
    want = _arg("--regions")
    return sorted(rs & set(want.split(","))) if want else sorted(rs)


def files(r):
    return sorted(glob.glob(os.path.join(PANEL, f"{r}_monthly_*.parquet")))


def ncols(r):
    return len(pd.read_parquet(files(r)[0]).columns)


def _sentinel(a):
    """The panel's two NoData sentinels ([[reference_panel_nodata_sentinel]]): int32 -2**31 in
    V02_total_precip_mm, int16 -32768 across the whole TerraClimate tier incl. V07_total_ref_ET_mm."""
    return (np.abs(a) >= 2 ** 31) | (a == -32768.0)


def _diff(p, et):
    """P - PET with the sentinels masked FIRST.

    WHY THIS IS NOT JUST `p - et`. Subtracting the raw columns produces
        -2147483648 - (-32768) = -2147450880
    which is 32,768 BELOW `leak_audit.impute_masked`'s `abs(col) >= 2**31` guard and is not -32768 either, so
    it escapes BOTH arms of that guard and survives into the feature matrix as -2.1e9. Measured on the
    2010 year-files: 7,080 such values in 47 of 133 regions, 0 caught, 6,018 of them on rows with a finite
    NDVI target. Masking at the source is the fix; widening the guard in leak_audit.py is the backstop.

    The four roll columns inherit the NaN (min_periods == window), which is correct -- a window containing an
    unknown month has an unknown sum. They were never safe by themselves: a 3-month sum of sentinels only
    clears 2**31 by accident."""
    out = p - et
    out[_sentinel(p) | _sentinel(et)] = np.nan
    return out


def _roll(g, w):
    """Trailing sum over `w` months, NaN unless all `w` values are present -- i.e. pandas
    .rolling(w).sum() with the default min_periods=w, but vectorised over every cell at once.

    Cumsum in float64: a 24-month precip sum reaches a few thousand mm and a float32 cumsum over 264 terms
    accumulates visible error. Only the cumsum is float64; the result is stored float32 like the panel."""
    ok = np.isfinite(g)
    cw = np.concatenate([np.zeros((g.shape[0], 1)), np.cumsum(np.where(ok, g, 0.0), axis=1, dtype=np.float64)],
                        axis=1)
    cv = np.concatenate([np.zeros((g.shape[0], 1), np.int32), np.cumsum(ok, axis=1, dtype=np.int32)], axis=1)
    out = np.full(g.shape, np.nan, np.float32)
    s = cw[:, w:] - cw[:, :-w]
    v = cv[:, w:] - cv[:, :-w]
    out[:, w - 1:] = np.where(v == w, s, np.nan).astype(np.float32)
    return out


def _sidecars(r):
    """The per-column drought sidecars `{region}__{col}.parquet`, or None if any of the 7 is absent.

    READ THE SIDECARS, NOT `{region}_drought.parquet`. The 2026-07-15 ingest sampled all 7 columns for all 133
    regions but died during its final merge loop, so only 22 merged files exist while all 931 sidecars do.
    Reading sidecars directly skips that merge entirely -- no intermediate 604M-row x 7-col file to write."""
    ps = [os.path.join(DROUGHT_DIR, f"{r}__{c}.parquet") for c in DR]
    return ps if all(os.path.exists(p) for p in ps) else None


def _cellkey(path):
    """A sidecar's cell_id column as an Arrow array -- compared at the Arrow level so 22M rows never become
    22M Python str objects (that alone is ~1.3 GB for yakutia_larch)."""
    import pyarrow.parquet as pq
    return pq.read_table(path, columns=["cell_id"]).column(0).combine_chunks()


def build(r, fs, cat):
    """Return {colname: (ncell, 264) float32 grid} for all 12 new columns, or None if the drought source is
    missing. Grids are filled a year-file at a time and the drought sidecars a column at a time, so the peak
    is the 12 grids themselves (~1.1 GB for the largest region, yakutia_larch) rather than a 22M-row concat."""
    side = _sidecars(r)
    if side is None:
        return None
    ncell = len(cat)
    out = {c: np.full((ncell, NMON), np.nan, np.float32) for c in ["wbal_mm"] + DR}

    # ---- wbal_mm: scatter P - PET year-file by year-file ----
    for f in fs:
        w = pd.read_parquet(f, columns=["cell_id", "year", "month", P_COL, ET_COL])
        code = cat.get_indexer(w.cell_id.to_numpy())
        assert (code >= 0).all(), f"{r}: a panel cell_id is absent from the region cell list"
        ti = (w.year.to_numpy() - Y0) * 12 + (w.month.to_numpy() - 1)
        assert ti.min() >= 0 and ti.max() < NMON, f"{r}: panel months outside {Y0}-{Y1}"
        assert len(np.unique(code.astype(np.int64) * NMON + ti)) == len(w), \
            f"{r}: duplicate (cell_id, year, month) in {os.path.basename(f)}"
        out["wbal_mm"][code, ti] = _diff(w[P_COL].to_numpy(np.float32), w[ET_COL].to_numpy(np.float32))
        del w
    for name, win in ROLLS:
        out[name] = _roll(out["wbal_mm"], win)

    # ---- drought: same grid, aligned by the same cell code; one sidecar column at a time ----
    d = pd.read_parquet(side[0], columns=["cell_id", "year", "month"])
    dc = cat.get_indexer(d.cell_id.to_numpy())
    dt = (d.year.to_numpy() - Y0) * 12 + (d.month.to_numpy() - 1)
    nsrc = len(d)
    del d
    keep = (dc >= 0) & (dt >= 0) & (dt < NMON)
    dck, dtk = dc[keep].astype(np.int64), dt[keep]
    assert len(np.unique(dck * NMON + dtk)) == len(dck), f"{r}: drought source has duplicate (cell, month) rows"
    k0 = _cellkey(side[0])
    for c, p in zip(DR, side):
        if p != side[0]:
            # the 7 sidecars were written by SEPARATE invocations, so their row order is asserted, not assumed
            s = pd.read_parquet(p, columns=["year", "month"])
            assert len(s) == nsrc, f"{r}: {c} sidecar has {len(s):,} rows vs {nsrc:,} in {DR[0]}"
            assert np.array_equal((s.year.to_numpy() - Y0) * 12 + (s.month.to_numpy() - 1), dt), \
                f"{r}: {c} sidecar month order differs from {DR[0]}"
            del s
            assert _cellkey(p).equals(k0), f"{r}: {c} sidecar cell_id order differs from {DR[0]}"
        v = pd.read_parquet(p, columns=[c])[c].to_numpy(np.float32)
        out[c][dck, dtk] = v[keep]
        del v
    return out


def main():
    t0 = time.time()
    dry, chk, rev = "--dry" in sys.argv, "--check" in sys.argv, "--revert" in sys.argv
    regs = regions()
    print(f"  {len(regs)} regions in {PANEL}", flush=True)

    if chk:
        tally = {}
        for r in regs:
            tally.setdefault(ncols(r), []).append(r)
        for n in sorted(tally):
            print(f"  {n:>4} columns: {len(tally[n]):>4} regions   e.g. {', '.join(tally[n][:3])}")
        miss = [r for r in regs if _sidecars(r) is None]
        print(f"  drought sidecars complete for {len(regs)-len(miss)}/{len(regs)} regions; "
              f"{len(miss)} missing" + (f" (e.g. {', '.join(miss[:4])})" if miss else ""))
        return 0

    if rev:
        n = 0
        for r in regs:
            for f in files(r):
                p = pd.read_parquet(f)
                drop = [c for c in NEW + OBS if c in p.columns]   # eddi_observed is derived FROM eddi, so it
                #                                                  must come out with it, never survive alone
                if not drop:
                    continue
                rows = len(p)
                p = p.drop(columns=drop)
                assert len(p) == rows, f"row count changed on {f}"
                tmp = f + ".tmp"
                p.to_parquet(tmp, index=False)
                os.replace(tmp, f)
                n += 1
            print(f"  reverted {r} -> {ncols(r)} columns", flush=True)
        print(f"  REVERT done: {n} files ({time.time()-t0:.0f}s)")
        return 0

    if "--addobs" in sys.argv:
        # ---- eddi_observed: make the MASK an honest declared feature (Part 342) --------------------------
        # WHY. eddi's missingness is MNAR on snow and purely SEASONAL (Mar-Sep 0.0% NaN everywhere, Oct-Feb
        # carries all of it). After LA.build's pooled <=2019 median fill, every winter row in 19 high-latitude
        # regions carries ONE constant that is arithmetically a SUMMER median -- so "eddi == that value" means
        # BOTH "evaporative demand is near normal" AND "evaporative demand is undefined because the ground is
        # under snow", and no tree can tell those apart. This column separates them. The information is real
        # (holding October fixed, eddi drops out where swe = 25.8 mm and survives at 6.2 mm), so the choice is
        # not whether the model sees it -- it already does, laundered through a drought value -- but whether it
        # is DECLARED.
        #
        # WHY THERE IS NO scpdsi_observed. The scpdsi mask is STATIC and SPATIAL: a cell is either 0% or 100%
        # NaN for all 264 months (measured in all 133 regions). So scpdsi_observed would be a per-cell
        # CONSTANT -- collinear with the per-cell router's intercept, hence exactly zero use there, and for the
        # trees a hard-coded map of which cells are masked, i.e. the cell-identity split we are trying to
        # PREVENT. Declaring a temporal mask adds information; declaring a spatial one adds a cheat sheet.
        nfix = 0
        for k, r in enumerate(regions(), 1):
            fs = files(r)
            n0 = ncols(r)
            if n0 == NCOL_OBS:
                continue
            if n0 != NCOL_AFTER:
                print(f"  !! {r}: {n0} columns, expected {NCOL_AFTER} -- SKIPPED")
                continue
            frac, rows = 0.0, 0
            for f in fs:
                p = pd.read_parquet(f)
                n = len(p)
                assert OBS[0] not in p.columns, f"{f} already carries {OBS[0]}"
                obs = np.isfinite(p["eddi"].to_numpy(np.float32))
                p[OBS[0]] = obs.astype(np.float32)
                assert len(p) == n and len(p.columns) == NCOL_OBS, f"{f}: bad shape after add"
                if not dry:
                    tmp = f + ".tmp"
                    p.to_parquet(tmp, index=False)
                    os.replace(tmp, f)
                frac += float(obs.sum())
                rows += n
                del p
            print(f"  [{k}/133] {'DRY ' if dry else ''}{r}: eddi observed on {frac/rows:6.2%} of "
                  f"{rows:,} rows -> {NCOL_OBS} cols ({time.time()-t0:.0f}s)", flush=True)
            nfix += 1
        print(f"\n  {'DRY RUN' if dry else 'APPLIED'}: {nfix} regions gained {OBS[0]} ({time.time()-t0:.0f}s)")
        return 0

    if "--fixwbal" in sys.argv:
        # Recompute ONLY the 5 wbal columns with the sentinel mask applied. Touches no other column and does
        # not change the column count, so it is a far cheaper repair than reverting and re-joining all 133.
        nfix = 0
        for k, r in enumerate(regions(), 1):
            fs = files(r)
            if ncols(r) != NCOL_AFTER:
                print(f"  !! {r}: {ncols(r)} columns -- not joined yet, SKIPPED")
                continue
            bad = 0
            for f in fs:
                v = pd.read_parquet(f, columns=["wbal_mm"]).wbal_mm.to_numpy(np.float32)
                bad += int((_sentinel(v) | (np.abs(v) >= 2 ** 30)).sum())
            if not bad:
                continue
            cat = pd.Index(pd.unique(pd.concat(
                [pd.read_parquet(f, columns=["cell_id"]).cell_id for f in fs], ignore_index=True)))
            ncell = len(cat)
            g = {"wbal_mm": np.full((ncell, NMON), np.nan, np.float32)}
            for f in fs:
                w = pd.read_parquet(f, columns=["cell_id", "year", "month", P_COL, ET_COL])
                code = cat.get_indexer(w.cell_id.to_numpy())
                ti = (w.year.to_numpy() - Y0) * 12 + (w.month.to_numpy() - 1)
                g["wbal_mm"][code, ti] = _diff(w[P_COL].to_numpy(np.float32), w[ET_COL].to_numpy(np.float32))
                del w
            for name, win in ROLLS:
                g[name] = _roll(g["wbal_mm"], win)
            for f in fs:
                p = pd.read_parquet(f)
                n = len(p)
                cols0 = list(p.columns)
                code = cat.get_indexer(p.cell_id.to_numpy())
                ti = (p.year.to_numpy() - Y0) * 12 + (p.month.to_numpy() - 1)
                for c in WB:
                    p[c] = g[c][code, ti].astype(np.float32)
                assert len(p) == n and list(p.columns) == cols0, f"{f}: shape or column order changed"
                if not dry:
                    tmp = f + ".tmp"
                    p.to_parquet(tmp, index=False)
                    os.replace(tmp, f)
                del p
            after = sum(int(_sentinel(pd.read_parquet(f, columns=["wbal_mm"]).wbal_mm.to_numpy(np.float32)).sum())
                        for f in fs) if not dry else -1
            print(f"  [{k}] {'DRY ' if dry else ''}{r}: {bad:,} poisoned wbal_mm values -> "
                  f"{'(dry run)' if dry else f'{after} remaining'} ({time.time()-t0:.0f}s)", flush=True)
            nfix += 1
        print(f"\n  {'DRY RUN' if dry else 'APPLIED'}: {nfix} regions repaired ({time.time()-t0:.0f}s)")
        return 0

    done = skipped = 0
    nomissing = []
    for k, r in enumerate(regs, 1):
        fs = files(r)
        n0 = ncols(r)
        if n0 == NCOL_AFTER:
            skipped += 1
            continue
        if n0 != NCOL_BEFORE:
            print(f"  !! {r}: {n0} columns, expected {NCOL_BEFORE} -- SKIPPED, inspect before proceeding")
            continue
        cat = pd.Index(pd.unique(pd.concat(
            [pd.read_parquet(f, columns=["cell_id"]).cell_id for f in fs], ignore_index=True)))
        g = build(r, fs, cat)
        if g is None:
            nomissing.append(r)
            print(f"  !! {r}: incomplete drought sidecars -- run ingest_drought_indices.py first, SKIPPED")
            continue
        rows = 0
        for f in fs:
            p = pd.read_parquet(f)
            n = len(p)
            clash = [c for c in NEW if c in p.columns]
            assert not clash, f"{f} already carries {clash}"
            code = cat.get_indexer(p.cell_id.to_numpy())
            assert (code >= 0).all(), f"{f}: unknown cell_id"
            ti = (p.year.to_numpy() - Y0) * 12 + (p.month.to_numpy() - 1)
            for c in NEW:
                p[c] = g[c][code, ti].astype(np.float32)
            assert len(p) == n, f"row count changed on {f}"
            assert len(p.columns) == NCOL_AFTER, f"{f}: {len(p.columns)} columns, expected {NCOL_AFTER}"
            if not dry:
                tmp = f + ".tmp"
                p.to_parquet(tmp, index=False)
                os.replace(tmp, f)
            rows += n
            del p
        nan = {c: float(np.isnan(g[c]).mean()) for c in NEW}
        _report(r, len(cat), rows, nan, dry)
        print(f"  [{k}/{len(regs)}] {'DRY ' if dry else ''}{r}: {len(cat):,} cells / {rows:,} rows "
              f"-> {NCOL_AFTER} cols | NaN roll24 {nan['wbal_roll24']:.1%} scpdsi {nan['scpdsi']:.1%} "
              f"eddi {nan['eddi']:.1%} ({time.time()-t0:.0f}s)", flush=True)
        del g
        done += 1

    print(f"\n  {'DRY RUN -- nothing written' if dry else 'APPLIED'}: {done} regions joined, "
          f"{skipped} already at {NCOL_AFTER}, {len(nomissing)} missing drought source ({time.time()-t0:.0f}s)")
    if nomissing:
        print("  MISSING DROUGHT SOURCE (%d): %s" % (len(nomissing), ",".join(nomissing)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
