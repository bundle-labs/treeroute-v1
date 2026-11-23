"""Monthly-panel data loader for modeling.

* TRAIN/TEST = the EXISTING Desertflow region split (NOT re-derived): 89 train regions
  (config data.master_dir = master_final_e14_e26) vs 44 held-out test regions
  (config forecast.regions_dir = master_final_e14_TEST_REGIONS_e26). 0 overlap.
* TARGET = V11_mean_ndvi (monthly NDVI level).
* Rows with a NaN target are DROPPED (can't train on a missing target) -- this removes the
  snow/cloud-masked Arctic-winter months (~5% of rows in far-north regions, ~0% elsewhere).
* IDs/keys (cell_id, region, year, month) are KEPT in the frame but EXCLUDED from features
  (use feature_cols()). Nothing is physically removed from the panel files.
* MEMORY-SAFE: load ONE region at a time (the full panel is ~27GB; all 89 train regions at once
  would OOM a 16GB box). Use iter_split() to stream, or load_region() for one region.

The forecasting PAIR construction (features at month t -> NDVI at month t+k, i.e. the 'month_diff'
horizon that adapts Desertflow's annual year_diff) is intentionally NOT baked in here -- that's the
model-design step. Decide the horizon set + whether the target is a level or a delta, then we add
make_pairs() on top of this loader.
"""
import glob
import os

import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
PANEL_DIR = r"D:\monthly_panel"
TARGET = "V11_mean_ndvi"
ID_KEYS = ["cell_id", "region", "year", "month"]                 # kept in frame, NEVER features


def _regions(d):
    return sorted(os.path.basename(p).split("_master_")[0]
                  for p in glob.glob(os.path.join(d, "*_master_*.parquet")) if ".bak." not in p)


def split_regions():
    """-> (train_regions, test_regions) from the existing Desertflow master directories."""
    return _regions(cfg["data"]["master_dir"]), _regions(cfg["forecast"]["regions_dir"])


def split_of(region):
    """-> 'train' or 'test' for a region (None if unknown)."""
    tr, te = split_regions()
    return "train" if region in tr else "test" if region in te else None


def feature_cols(df, extra_exclude=()):
    """Feature columns = all columns except the ID/keys, the target, and any extra_exclude.
    Pass extra_exclude=[...] to also hold back cols you don't want in THIS model (kept in the data)."""
    excl = set(ID_KEYS) | {TARGET} | set(extra_exclude)
    return [c for c in df.columns if c not in excl]


def load_region(region, drop_nan_target=True, columns=None):
    """One region's monthly panel (its 22 year-files concatenated). Drops NaN-target rows by default.
    `columns` (optional) limits which columns are read (faster/lighter); include TARGET if you filter on it."""
    fs = sorted(glob.glob(os.path.join(PANEL_DIR, f"{region}_monthly_*.parquet")))
    if not fs:
        return None
    cols = None if columns is None else sorted(set(columns) | {TARGET, "cell_id", "year", "month"})
    df = pd.concat([pd.read_parquet(f, columns=cols) for f in fs], ignore_index=True)
    if drop_nan_target and TARGET in df.columns:
        df = df[df[TARGET].notna()].reset_index(drop=True)
    return df


def iter_split(split="train", drop_nan_target=True, columns=None):
    """Yield (region, DataFrame) for each region in `split` ('train' | 'test' | 'all').
    Memory-safe -- one region in RAM at a time. e.g.:
        for region, df in iter_split('train'):
            X, y = df[feature_cols(df)], df[TARGET]
            model.partial_fit(X, y)   # or accumulate / train per region
    """
    tr, te = split_regions()
    regs = {"train": tr, "test": te, "all": tr + te}[split]
    for r in regs:
        df = load_region(r, drop_nan_target=drop_nan_target, columns=columns)
        if df is not None:
            yield r, df


if __name__ == "__main__":
    tr, te = split_regions()
    print(f"split: {len(tr)} train + {len(te)} test = {len(tr) + len(te)} regions (overlap {len(set(tr) & set(te))})")
    df = load_region("thar_desert")
    feats = feature_cols(df)
    print(f"thar_desert: {len(df)} rows after NaN-target drop, {len(feats)} feature cols, target='{TARGET}'")
    print(f"  target NaN after drop (must be 0): {df[TARGET].isna().sum()}")
    print(f"  held-back (non-feature) cols: {ID_KEYS + [TARGET]}")
    print(f"  first 8 features: {feats[:8]}")
