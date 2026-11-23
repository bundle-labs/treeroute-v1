"""NDVI package: the package's own reader of its target store (plan 1.2 'Target table', 6.2 step 2).

The target is the monthly panel's column V11_mean_ndvi (MOD13C2.061 CMG 0.05 deg monthly NDVI, scale 1e-4,
aggregated to the 4 km panel cells; ruling Q1 a). The engine lists the target store with dataset.yaml's
template (stores.target, 'D:/monthly_panel/{group}_monthly_{year}.parquet', the same files as the first
driver store) and hands this reader one file at a time, with the key the listing read back from the path.
The reader returns that file's target-table rows with the columns the package catalog names:

    cell_id        key_unit   ({group}_{ix}_{iy}, as the panel writes it; plan 1.2 unit id format)
    region         key_group  (the panel's region column; it must equal the path's {group})
    year           key_time   (calendar part year; every row must be the path's {year})
    month          key_time   (calendar part month, 1..12)
    V11_mean_ndvi  target     (invalid labels as NaN, owner ruling D30)

THE FILLS. The ingest gated MOD13C2's raw values to the documented valid range -2000..10000 before scaling
(presplit_cc/ingest_modis_cmg_local.py:59, raw_min/raw_max), so an invalid pixel reached the panel as NaN.
This reader masks again, at read, every fill code it knows, and counts and prints each kind it masked:
  - the panel-wide integer fill codes the panel's store catalog declares (-32768, -32767, -2^31, -2^31+1;
    monthly_panel_v170_schema_catalog.yaml, V11_mean_ndvi fill_values) and any value at or above 2^30 in
    magnitude (the engine's near-sentinel flag). The codes are WRITTEN HERE (PANEL_FILLS; the reader does not
    open the store catalog) and tests/test_ndvi_package.py pins them to the store catalog's fill_values
    (test_the_target_reader_fill_codes_are_the_store_catalogs);
  - MOD13C2's own NDVI fill, raw -3000, which is -0.3 after the 1e-4 scale (PRODUCT_FILL; PAPER_REFERENCE.md
    2.2 [Part 390]: fill -3000, excluded by the gate). Every value within PRODUCT_FILL_TOL (1e-6) of -0.3 is
    masked: that covers the ingest's float32 arithmetic (float32(-3000) x float32(1e-4) = -0.29999998), the
    float32 -0.3 (-0.30000001) and the float64 -0.3. The legal minimum is -0.2, so the mask never touches a
    legal label;
  - an infinite value (+/-inf).
So a re-ingest that forgot the gate cannot slip a DECLARED fill code (the panel's or the product's) into the
labels. It CAN slip in a raw value outside the valid range that is no fill code (raw below -2000 other than
-3000, or above 10000): such a value is finite and is NOT masked here. It is counted and printed as outside
the legal range [-0.2, 1] (MOD13 User Guide V6.1 Table 19), and the engine's range check decides (D95: refuse
above 0.1% of the non-missing values; at or below that share it flags and prints the count, and the values
STAY in the labels). The panel holds none today (PAPER_REFERENCE.md 2.2: observed range exactly
[-0.2000, 0.9988], no mass at -0.30).

Refuses (fail loudly, TargetReadError): a key without a group or without a year (the store template has
both); a missing column; a row of another region than the path's group; ANY unit id (every distinct id of
the file) that does not start with '<group>_'; a row of another year than the path's; a month outside 1..12.

Contract with the engine (treeroute/pipeline/data.py, 'target reader hook'):
    read_target_file(path, key) -> pandas.DataFrame
        path  one file of the target store, as the listing found it
        key   {placeholder: value} read back from the path, here {'group': <region>, 'year': <year>}
    Every row of the file is returned (a complete census; plan 1.2), with the five columns above.
    Nothing else is read, and nothing is written.

Read-only: the store is read in place (plan 1.2), never copied. Dataset code: it may name its store and its
product; the engine may not (G-NONAMES).
"""
# Provenance: presplit_cc/ingest_modis_cmg_local.py:55-60 (the MOD13C2 NDVI field, scale 0.0001, raw_min -2000,
# raw_max 10000); PAPER_REFERENCE.md 2.2 [Part 390] (MOD13C2's NDVI fill -3000);
# presplit_cc/monthly_loader.py:28-29 (TARGET = V11_mean_ndvi; ID_KEYS cell_id, region, year,
# month); engine/datasets/_stores/monthly_panel_v170_schema_catalog.yaml (V11_mean_ndvi: float32, fill_values);
# engine/datasets/ndvi/catalog.yaml (the key roles and the target's legal range).

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

UNIT_COLUMN = "cell_id"
GROUP_COLUMN = "region"
YEAR_COLUMN = "year"
MONTH_COLUMN = "month"
TARGET_COLUMN = "V11_mean_ndvi"
COLUMNS = (UNIT_COLUMN, GROUP_COLUMN, YEAR_COLUMN, MONTH_COLUMN, TARGET_COLUMN)

# origin: monthly_panel_v170_schema_catalog.yaml, V11_mean_ndvi fill_values (the panel-wide integer fill codes;
# APP_PLAN.md 1.3: confirmed by the panel's author, panel_sentinel.py:20-23)
PANEL_FILLS = (-32768.0, -32767.0, -2147483648.0, -2147483647.0)
# origin: MOD13C2's NDVI fill, raw -3000 x scale 1e-4 (PAPER_REFERENCE.md 2.2 [Part 390]: 'Fill -3000, excluded by
# the gate'; the valid range -2000..10000 is presplit_cc/ingest_modis_cmg_local.py:59). Masked within the
# tolerance: the ingest multiplies in float32 (-0.29999998), and float32(-0.3) is -0.30000001; no legal label
# (minimum -0.2) lies within 0.1 of it
PRODUCT_FILL = -0.3
PRODUCT_FILL_TOL = 1e-6
# origin: the engine's near-sentinel flag (APP_PLAN.md 1.3 'fill_values, near_sentinel_optout': 2^30); an NDVI
# never comes near it, so anything this large is a fill code or arithmetic on one
NEAR_SENTINEL = 2.0 ** 30
# origin: catalog.yaml V11_mean_ndvi legal_range (MOD13 User Guide V6.1 Table 19: valid_range -2000..10000,
# scale 0.0001); counted and printed only, never masked here
LEGAL_RANGE = (-0.2, 1.0)


class TargetReadError(Exception):
    """The target file is not what the reader expects (fail loudly; nothing is guessed)."""


def read_target_file(path, key):
    """One monthly-panel file as NDVI target-table rows (see the module docstring)."""
    group = key.get("group") if isinstance(key, dict) else None
    year = key.get("year") if isinstance(key, dict) else None
    if not isinstance(group, str) or not group:
        raise TargetReadError("%s: the key carries no group (%r); the store template has {group}" % (path, key))
    if year is None or str(year).strip() == "":
        raise TargetReadError("%s: the key carries no year (%r); the store template has {year}" % (path, key))
    try:
        year = int(year)
    except (TypeError, ValueError):
        raise TargetReadError("%s: the key's year %r is not an integer" % (path, year))
    with pq.ParquetFile(str(path)) as pf:
        names = pf.schema_arrow.names
    missing = [c for c in COLUMNS if c not in names]
    if missing:
        raise TargetReadError("%s has no column %s" % (path, missing))
    # the id columns are read dictionary-encoded, so every row of one cell points at ONE str object (a
    # census file repeats each id 12 times; the largest groups hold 20+ million rows over their years)
    table = pq.read_table(str(path), columns=list(COLUMNS), read_dictionary=[UNIT_COLUMN, GROUP_COLUMN])
    frame = table.to_pandas()
    regions = frame[GROUP_COLUMN].astype(str).unique()
    wrong_region = sorted(r for r in regions if r != group)
    if wrong_region:
        raise TargetReadError("%s: rows of the regions %s in the file of group %r" % (path, wrong_region[:5], group))
    units = np.asarray(frame[UNIT_COLUMN], dtype=object)
    prefix = group + "_"
    # every distinct id of the file (the ids point at few str objects, so this is one pass over the uniques)
    wrong = [u for u in pd.unique(units) if not (isinstance(u, str) and u.startswith(prefix))]
    if wrong:
        raise TargetReadError("%s: %d unit ids do not carry the group %r of the path, e.g. %s"
                              % (path, len(wrong), group, wrong[:5]))
    years = frame[YEAR_COLUMN].to_numpy().astype(np.int64)
    if not (years == year).all():
        raise TargetReadError("%s: rows of years %s in the file of year %s"
                              % (path, sorted(set(years.tolist()))[:5], year))
    months = frame[MONTH_COLUMN].to_numpy().astype(np.int64)
    if len(months) and (months.min() < 1 or months.max() > 12):
        raise TargetReadError("%s: months outside 1..12 (%d..%d)" % (path, months.min(), months.max()))
    y = frame[TARGET_COLUMN].to_numpy().astype(np.float64)
    infinite = np.isinf(y)
    n_inf = int(infinite.sum())
    if n_inf:
        print("target reader: %s: %d infinite values masked to NaN" % (path, n_inf))
    y[infinite] = np.nan
    finite = np.isfinite(y)
    fill = finite & (np.isin(y, PANEL_FILLS) | (np.abs(y) >= NEAR_SENTINEL))
    n_fill = int(fill.sum())
    if n_fill:
        print("target reader: %s: %d values at a panel fill code or the 2^30 magnitude masked to NaN" % (path, n_fill))
    y[fill] = np.nan
    product = np.isfinite(y) & (np.abs(y - PRODUCT_FILL) <= PRODUCT_FILL_TOL)
    n_product = int(product.sum())
    if n_product:
        print("target reader: %s: %d values at MOD13C2's fill (raw -3000, %g) masked to NaN"
              % (path, n_product, PRODUCT_FILL))
    y[product] = np.nan
    ok = np.isfinite(y)
    outside = int((ok & ((y < LEGAL_RANGE[0]) | (y > LEGAL_RANGE[1]))).sum())
    if outside:
        print("target reader: %s: %d of %d valid labels outside the legal range [%g, %g] (not masked; the "
              "engine's range check decides, D95)" % (path, outside, int(ok.sum()), LEGAL_RANGE[0], LEGAL_RANGE[1]))
    return pd.DataFrame({UNIT_COLUMN: units,
                         GROUP_COLUMN: np.full(len(frame), group, dtype=object),
                         YEAR_COLUMN: years,
                         MONTH_COLUMN: months,
                         TARGET_COLUMN: y})
