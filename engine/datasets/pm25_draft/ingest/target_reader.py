"""PM2.5 package: the package's own reader of its target store (plan 1.2 'Target table', 6.2 step 2).

The engine lists the target store with dataset.yaml's template (stores.target,
'D:/pm25_acag/{group}_pm25_{year}.parquet') and hands this reader one file at a time, with the key the
listing read back from the path. The reader returns the target table rows of that file exactly as the
package catalog names them:

    cell_id    key_unit   ({group}_{ix}_{iy}, as written by the ingest; plan 1.2 unit id format)
    region     key_group  (the files do not hold it: it is the {group} placeholder of the path)
    year       key_time   (calendar part year)
    month      key_time   (calendar part month)
    pm25_ugm3  target     (invalid labels as NaN, owner ruling D30)

THE FILL. ACAG V5.GL.06 writes 9.96921e36 for no data, read from the file header
(acag_pm25_ingest.py:17-21, 71). That value is POSITIVE and FINITE, so neither an isfinite nor a < 0
guard sees it. The ingest that made D:/pm25_acag masked every value at or above 1e30 before any
arithmetic (acag_pm25_ingest.py:74-76, 171-173), so the store should hold none; this reader applies the
same rule again at read, counts what it masked and prints the count, so a later re-ingest that forgot
the mask cannot slip a fill value into the labels. The engine refuses any target value at the sentinel
magnitude (D30), so an unmasked fill would stop the run, never enter it.

Contract with the engine (treeroute/pipeline/data.py, 'target reader hook'):
    read_target_file(path, key) -> pandas.DataFrame
        path  one file of the target store, as the listing found it
        key   {placeholder: value} read back from the path, here {'group': <region>, 'year': <year>}
    Every row of the file is returned (a complete census; plan 1.2), with the five columns above.
    Nothing else is read, and nothing is written.

Read-only: the store is read in place (plan 1.2), never copied. Dataset code: it may name its store and
its product; the engine may not (G-NONAMES).
"""
# Provenance: acag_pm25_ingest.py (the ingest that wrote D:/pm25_acag: FILL 9.96921e36 read from the file
# header, FILL_FLOOR 1e30 masked at read); engine/datasets/pm25/dataset.yaml (the store template and the
# {group} placeholder); APP_PLAN.md 3.2 row 'Dataset-side code' ("ACAG ingest (9.96921e36 fill to NaN)").

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

UNIT_COLUMN = "cell_id"
GROUP_COLUMN = "region"
YEAR_COLUMN = "year"
MONTH_COLUMN = "month"
TARGET_COLUMN = "pm25_ugm3"
COLUMNS = (UNIT_COLUMN, GROUP_COLUMN, YEAR_COLUMN, MONTH_COLUMN, TARGET_COLUMN)

# origin: acag_pm25_ingest.py:71 (FILL = 9.96921e36, read from the ACAG file header)
ACAG_FILL = 9.96921e36
# origin: acag_pm25_ingest.py:74-76 (anything at or above this is the fill value or arithmetic on it; a
# plain equality test would miss a value that went through a float32 -> float64 conversion)
FILL_FLOOR = 1e30

STORED_COLUMNS = (UNIT_COLUMN, YEAR_COLUMN, MONTH_COLUMN, TARGET_COLUMN)


class TargetReadError(Exception):
    """The target file is not what the reader expects (fail loudly; nothing is guessed)."""


def read_target_file(path, key):
    """One ACAG target file as target-table rows (see the module docstring)."""
    group = key.get("group") if isinstance(key, dict) else None
    year = key.get("year") if isinstance(key, dict) else None
    if not isinstance(group, str) or not group:
        raise TargetReadError("%s: the key carries no group (%r); the store template has {group}"
                              % (path, key))
    with pq.ParquetFile(str(path)) as pf:
        names = pf.schema_arrow.names
        missing = [c for c in STORED_COLUMNS if c not in names]
        if missing:
            raise TargetReadError("%s has no column %s (it holds %s)" % (path, missing, names))
        table = pf.read(columns=list(STORED_COLUMNS))
    frame = table.to_pandas()
    units = frame[UNIT_COLUMN].astype(object).to_numpy()
    wrong = [u for u in pd.unique(units)[:50] if not str(u).startswith(group + "_")]
    if wrong:
        raise TargetReadError("%s: unit ids %s do not carry the group %r of the path"
                              % (path, wrong[:5], group))
    years = frame[YEAR_COLUMN].to_numpy().astype(np.int64)
    if year is not None and not (years == int(year)).all():
        raise TargetReadError("%s: rows of years %s in the file of year %s"
                              % (path, sorted(set(years.tolist()))[:5], year))
    y = frame[TARGET_COLUMN].to_numpy().astype(np.float64)
    fill = np.isfinite(y) & (np.abs(y) >= FILL_FLOOR)
    n_fill = int(fill.sum())
    if n_fill:
        print("target reader: %s: %d values at the fill magnitude (the ACAG fill %g) masked to NaN"
              % (path, n_fill, ACAG_FILL))
    y[fill] = np.nan
    y[~np.isfinite(y)] = np.nan
    return pd.DataFrame({UNIT_COLUMN: units,
                         GROUP_COLUMN: np.full(len(frame), group, dtype=object),
                         YEAR_COLUMN: years,
                         MONTH_COLUMN: frame[MONTH_COLUMN].to_numpy().astype(np.int64),
                         TARGET_COLUMN: y})
