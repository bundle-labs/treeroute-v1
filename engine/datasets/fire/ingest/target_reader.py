"""Fire package: the package's own reader of its target store (plan 1.2 'Target table', 6.2 step 2).

The engine lists the target store with dataset.yaml's template (stores.target,
'D:/fire/target/{group}_{year}.parquet') and hands this reader one file at a time, with the key the
listing read back from the path. The reader returns that file's target-table rows exactly as the package
catalog names them:

    cell_id      key_unit   (the panel cell id {group}_{ix}_{iy}, through the key map below)
    region       key_group  (the files do not hold it: it is the {group} placeholder of the path)
    year         key_time   (calendar part year)
    month        key_time   (calendar part month)
    burned_frac  target     (invalid labels as NaN, owner ruling D30)

THE KEY MAP (plan 1.2: "id maps (fire's lat/lon to id) live in the ingest script"). The store is keyed on
lat + lon. The map is the package's static table (dataset.yaml stores.static, written once by
ingest/build_static.py): a row's (lat, lon), rounded to 5 decimals with the shipped key
(fire_architecture.py:241-243), is looked up among the group's units. A target cell that is not a unit (it
has no panel cell) is dropped and counted; build_static.py's manifest lists those cells per group.

THE VALIDITY RULE (fire_architecture.py:273-274: X = X[X.n_valid > 0]; y = burned_frac). A label is valid
only where n_valid > 0 (some land pixels of the cell were mapped that month); otherwise it is NaN. The shipped
run then filled a NaN burned_frac with 0 (fillna(0.0)); no such row exists in the store (NaN burned_frac
occurs exactly where n_valid <= 0, READ-ONLY scan of all 840 files, 2026-09-29), so a finite n_valid with a
NaN burned_frac is REFUSED here rather than guessed. A burned_frac outside [0, 1] is refused (the target's
legal range, fraction by construction).

THE COMPLETE CENSUS (plan 1.2, R1). The store drops some cells from some years' files (e.g. 1,169 of
canadian_taiga's 72,154 cells are absent from at least one year; READ-ONLY scan 2026-09-29): the shipped run
never saw those months (an inner join). This reader returns EVERY unit of the group for EVERY month of the
file's year, with a NaN label where the file has no row, so the engine's dense grid is a complete census and
R1 sees a regular monthly step. The NaN counts per file are printed.

Contract with the engine (treeroute/pipeline/data.py, 'target reader hook'):
    read_target_file(path, key) -> pandas.DataFrame
        path  one file of the target store, as the listing found it
        key   {placeholder: value} read back from the path, here {'group': <region>, 'year': <year>}
    The rows are the group's units x the 12 months of the year (sorted by unit, then month), with the five
    columns above. Nothing else is read (the key map once per package), and nothing is written.

Read-only: the store is read in place (plan 1.2), never copied. Dataset code: it may name its store and its
product; the engine may not (G-NONAMES).
"""
# Provenance: fire_architecture.py:241-243 (the key), :250-275 (the shipped load: key join, n_valid > 0,
# fillna(0.0)); fire_fetch_target.py:8, 339 (burned_frac = burned pixels / valid land pixels, in [0, 1]);
# APP_PLAN.md 1.2 (target table; complete census; id maps and validity rules in the ingest); OWNER_RULINGS
# D30 (invalid labels as NaN).

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml

UNIT_COLUMN = "cell_id"
GROUP_COLUMN = "region"
YEAR_COLUMN = "year"
MONTH_COLUMN = "month"
TARGET_COLUMN = "burned_frac"
COLUMNS = (UNIT_COLUMN, GROUP_COLUMN, YEAR_COLUMN, MONTH_COLUMN, TARGET_COLUMN)
STORED_COLUMNS = ("lat", "lon", YEAR_COLUMN, MONTH_COLUMN, "n_valid", TARGET_COLUMN)
MONTHS = 12
LEGAL_RANGE = (0.0, 1.0)

# the package root: this file is <package>/ingest/target_reader.py
PACKAGE_ROOT = Path(__file__).resolve().parent.parent


class TargetReadError(Exception):
    """The target file is not what the reader expects (fail loudly; nothing is guessed)."""


def cell_key(lat, lon):
    """The shipped lat/lon key (fire_architecture.py:241-243), exactly: round to 5 decimals, scale, truncate."""
    return ((np.round(np.asarray(lat).astype(np.float64), 5) * 100000).astype(np.int64) * 100000000
            + (np.round(np.asarray(lon).astype(np.float64), 5) * 100000).astype(np.int64))


def static_table_path(package_root=PACKAGE_ROOT):
    """The static table named by the package's dataset.yaml (stores.static), resolved from the package."""
    ds = yaml.safe_load((Path(package_root) / "dataset.yaml").read_text(encoding="utf-8"))
    rel = ds["stores"]["static"]
    return Path(rel) if os.path.isabs(rel) else (Path(package_root) / rel)


class KeyMap(object):
    """One group's units: sorted keys, the unit (index into ids) of each key, and the ids as ONE str object
    per unit (every census row of a unit points at the same object)."""

    def __init__(self, group, ids, lat, lon):
        self.group = group
        self.ids = np.array([str(u) for u in ids], dtype=object)
        keys = cell_key(lat, lon)
        order = np.argsort(keys, kind="stable")
        self.keys = keys[order]
        self.unit_of_key = order.astype(np.int64)
        if (np.diff(self.keys) == 0).any():
            raise TargetReadError("the static table holds two units of %s on one lat/lon key" % group)

    def lookup(self, keys):
        """(unit index per key, matched mask)."""
        pos = np.searchsorted(self.keys, keys)
        pos = np.minimum(pos, max(len(self.keys) - 1, 0))
        ok = (self.keys[pos] == keys) if len(self.keys) else np.zeros(len(keys), dtype=bool)
        return np.where(ok, self.unit_of_key[pos], -1), ok


_CACHE = {}


def key_map(group, package_root=PACKAGE_ROOT):
    """The group's key map from the static table (read once per table file state)."""
    path = static_table_path(package_root)
    if not path.is_file():
        raise TargetReadError("the key map %s does not exist: run ingest/build_static.py on the package first"
                              % path)
    st = path.stat()
    state = (str(path), st.st_size, st.st_mtime_ns)
    entry = _CACHE.get("table")
    if entry is None or entry[0] != state:
        table = pq.read_table(str(path), columns=[UNIT_COLUMN, GROUP_COLUMN, "lat", "lon"]).to_pandas()
        entry = (state, table, {})
        _CACHE["table"] = entry
    _, table, maps = entry
    if group not in maps:
        rows = table[table[GROUP_COLUMN].astype(str) == group]
        if not len(rows):
            raise TargetReadError("the key map %s holds no unit of the group %r" % (path, group))
        maps[group] = KeyMap(group, rows[UNIT_COLUMN].to_numpy(), rows["lat"].to_numpy(), rows["lon"].to_numpy())
    return maps[group]


def valid_labels(burned_frac, n_valid, what):
    """The validity rule (fire_architecture.py:273-274): the label where n_valid > 0, else NaN. Refuses a
    NaN label on a valid row (the shipped fillna(0.0) is not guessed) and a label outside [0, 1]."""
    y = np.asarray(burned_frac, dtype=np.float64).copy()
    nv = np.asarray(n_valid)
    ok = nv > 0
    bad = ok & ~np.isfinite(y)
    if bad.any():
        raise TargetReadError("%s: %d rows have n_valid > 0 but no burned_frac (the shipped run filled 0; "
                              "refused, not guessed)" % (what, int(bad.sum())))
    y[~ok] = np.nan
    out = np.isfinite(y) & ((y < LEGAL_RANGE[0]) | (y > LEGAL_RANGE[1]))
    if out.any():
        raise TargetReadError("%s: %d labels outside [0, 1]" % (what, int(out.sum())))
    return y


def read_target_file(path, key):
    """One fire target file as target-table rows: every unit of the group x the 12 months of the year."""
    group = key.get("group") if isinstance(key, dict) else None
    year = key.get("year") if isinstance(key, dict) else None
    if not isinstance(group, str) or not group:
        raise TargetReadError("%s: the key carries no group (%r); the store template has {group}" % (path, key))
    if year is None:
        raise TargetReadError("%s: the key carries no year (%r); the store template has {year}" % (path, key))
    year = int(year)
    with pq.ParquetFile(str(path)) as pf:
        names = pf.schema_arrow.names
        missing = [c for c in STORED_COLUMNS if c not in names]
        if missing:
            raise TargetReadError("%s has no column %s (it holds %s)" % (path, missing, names))
        table = pf.read(columns=list(STORED_COLUMNS))
    years = table.column(YEAR_COLUMN).to_numpy().astype(np.int64)
    if not (years == year).all():
        raise TargetReadError("%s: rows of years %s in the file of year %d"
                              % (path, sorted(set(years.tolist()))[:5], year))
    months = table.column(MONTH_COLUMN).to_numpy().astype(np.int64)
    if len(months) and (months.min() < 1 or months.max() > MONTHS):
        raise TargetReadError("%s: months outside 1..12" % path)
    y = valid_labels(table.column(TARGET_COLUMN).to_numpy(zero_copy_only=False),
                     table.column("n_valid").to_numpy(zero_copy_only=False), path)
    km = key_map(group)
    unit, ok = km.lookup(cell_key(table.column("lat").to_numpy(), table.column("lon").to_numpy()))
    n_units = len(km.ids)
    slot = unit[ok] * MONTHS + (months[ok] - 1)
    if len(slot) != len(np.unique(slot)):
        raise TargetReadError("%s repeats a (unit, month) row" % path)
    census = np.full(n_units * MONTHS, np.nan)
    census[slot] = y[ok]
    present = np.zeros(n_units * MONTHS, dtype=bool)
    present[slot] = True
    n_absent = int((~present).sum())
    n_dropped = int((~ok).sum())
    if n_absent or n_dropped:
        print("target reader: %s: %d unit-months absent from the file (NaN labels); %d rows of cells that "
              "are not units (no panel cell) dropped" % (os.path.basename(str(path)), n_absent, n_dropped))
    unit_rows = np.repeat(np.arange(n_units, dtype=np.int64), MONTHS)
    return pd.DataFrame({UNIT_COLUMN: km.ids[unit_rows],
                         GROUP_COLUMN: np.full(n_units * MONTHS, group, dtype=object),
                         YEAR_COLUMN: np.full(n_units * MONTHS, year, dtype=np.int64),
                         MONTH_COLUMN: np.tile(np.arange(1, MONTHS + 1, dtype=np.int64), n_units),
                         TARGET_COLUMN: census})
