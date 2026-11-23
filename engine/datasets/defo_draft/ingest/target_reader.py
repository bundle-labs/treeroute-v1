"""Deforestation package: the package's own reader of its target store (plan 1.2 'Target table', 6.2 step 2).

The engine lists the target store with dataset.yaml's template (stores.target,
'D:/defo_target/{group}.parquet') and hands this reader one file at a time, with the key the listing
read back from the path. The reader returns the target table rows of that file exactly as the package
catalog names them:

    cell_id    key_unit   ({group}_{ix}_{iy}, as written by defo_ingest.py; plan 1.2 unit id format)
    region     key_group  (the files do not hold it: it is the {group} placeholder of the path)
    year       key_time   (calendar part year)
    loss_frac  target     (Hansen GFC forest-loss fraction; invalid labels as NaN, owner ruling D30)

What the store holds (parquet footer, 2026-09-28): cell_id, year, loss_px, forest2000_px, land_px,
loss_frac, one row per cell and year 2001-2025 (a complete census). loss_frac = loss_px / forest2000_px,
the pixels lost in the year over the year-2000 forest pixels (defo_ingest.py:6-16).

INVALID LABELS (D30). A cell with no year-2000 forest (forest2000_px == 0) has no defined loss fraction:
the store already writes NaN there (the shipped matrix dropped those rows, defo_matrix.py:317); this
reader enforces it (NaN wherever forest2000_px <= 0) and counts what it had to change. A finite value
outside the legal range [0, 1] is refused, never clipped or guessed.

CHECK AGAINST THE PIXEL COUNTS. On every row with year-2000 forest, loss_frac must equal
loss_px / forest2000_px within FRACTION_TOLERANCE (the store holds loss_frac as float32); a row that does
not is refused. Nothing else is read: loss_px, forest2000_px and land_px never leave this reader (they
are Hansen co-products with forced bans; forest2000_px reaches the report as a stratum only through the
static table, ingest/build_static.py).

Contract with the engine (treeroute/pipeline/data.py, 'target reader hook'):
    read_target_file(path, key) -> pandas.DataFrame
        path  one file of the target store, as the listing found it
        key   {placeholder: value} read back from the path, here {'group': <region>}
    Every row of the file is returned (a complete census; plan 1.2), with the four columns above.
    Nothing is written.

Read-only: the store is read in place (plan 1.2), never copied. Dataset code: it may name its store and
its product; the engine may not (G-NONAMES).
"""
# Provenance: defo_ingest.py:1-16 (the ingest that wrote D:/defo_target: loss_frac = loss_px / forest2000_px
# over the year-2000 forest mask); defo_matrix.py:282-283, 317 (the shipped matrix copied loss_frac as y and
# kept forest2000_px > 0 only); engine/datasets/defo/dataset.yaml (the store template and the {group}
# placeholder); OWNER_RULINGS_2026-09-28.md C 'Defo store' (the target comes from D:/defo_target, never from
# D:/defo_matrix's copy).

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

UNIT_COLUMN = "cell_id"
GROUP_COLUMN = "region"
YEAR_COLUMN = "year"
TARGET_COLUMN = "loss_frac"
COLUMNS = (UNIT_COLUMN, GROUP_COLUMN, YEAR_COLUMN, TARGET_COLUMN)
STORED_COLUMNS = (UNIT_COLUMN, YEAR_COLUMN, "loss_px", "forest2000_px", TARGET_COLUMN)
LEGAL_RANGE = (0.0, 1.0)
# loss_frac is stored as float32: a float32 quotient differs from the float64 one by at most half a float32
# ulp of a value in [0, 1] (6e-8); 1e-6 leaves room and still catches any real mismatch
FRACTION_TOLERANCE = 1e-6


class TargetReadError(Exception):
    """The target file is not what the reader expects (fail loudly; nothing is guessed)."""


def read_target_file(path, key):
    """One Hansen target file as target-table rows (see the module docstring)."""
    group = key.get("group") if isinstance(key, dict) else None
    if not isinstance(group, str) or not group:
        raise TargetReadError("%s: the key carries no group (%r); the store template has {group}" % (path, key))
    with pq.ParquetFile(str(path)) as pf:
        names = pf.schema_arrow.names
        missing = [c for c in STORED_COLUMNS if c not in names]
        if missing:
            raise TargetReadError("%s has no column %s (it holds %s)" % (path, missing, names))
        table = pf.read(columns=list(STORED_COLUMNS))
    frame = table.to_pandas()
    units = frame[UNIT_COLUMN].astype(object).to_numpy()
    wrong = [u for u in pd.unique(units) if not str(u).startswith(group + "_")]
    if wrong:
        raise TargetReadError("%s: unit ids %s do not carry the group %r of the path" % (path, wrong[:5], group))
    years = frame[YEAR_COLUMN].to_numpy().astype(np.int64)
    if pd.DataFrame({"u": units, "t": years}).duplicated().any():
        raise TargetReadError("%s: a (cell, year) row is repeated" % path)
    y = frame[TARGET_COLUMN].to_numpy().astype(np.float64)
    forest = frame["forest2000_px"].to_numpy().astype(np.float64)
    loss = frame["loss_px"].to_numpy().astype(np.float64)
    y[~np.isfinite(y)] = np.nan
    no_forest = ~(forest > 0)
    changed = int(np.count_nonzero(no_forest & np.isfinite(y)))
    if changed:
        print("target reader: %s: %d labels on cells without year-2000 forest set to NaN (D30)" % (path, changed))
    y[no_forest] = np.nan
    ok = np.isfinite(y)
    out_of_range = ok & ((y < LEGAL_RANGE[0]) | (y > LEGAL_RANGE[1]))
    if out_of_range.any():
        raise TargetReadError("%s: %d loss fractions outside [0, 1], e.g. %s"
                              % (path, int(out_of_range.sum()), y[out_of_range][:3].tolist()))
    with np.errstate(divide="ignore", invalid="ignore"):
        recomputed = loss / forest
    gap = np.abs(y[ok] - recomputed[ok])
    if gap.size and not np.all(gap <= FRACTION_TOLERANCE):
        raise TargetReadError("%s: %d loss fractions differ from loss_px / forest2000_px by more than %g "
                              "(max %g)" % (path, int(np.count_nonzero(~(gap <= FRACTION_TOLERANCE))),
                                            FRACTION_TOLERANCE, float(np.nanmax(gap))))
    return pd.DataFrame({UNIT_COLUMN: units,
                         GROUP_COLUMN: np.full(len(frame), group, dtype=object),
                         YEAR_COLUMN: years,
                         TARGET_COLUMN: y})
