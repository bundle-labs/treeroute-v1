"""PM2.5 package: write the package's static table (plan 1.2 'Static table'; 6.2 step 2).

The static table holds one row per unit: the unit id, its group, its representative point (lat, lon;
EPSG:4326, the cell centre) and its grid indices. The engine reads it for the overlap blocks (R14:
'grid_indices' link rule when grid_ix / grid_iy exist) and the router context; the package's feature
script reads lat from the monthly panel itself.

What it reads (read-only, in place):
  - the target store (dataset.yaml stores.target): the unit ids of every group, from the FIRST year's
    file of each group (a complete census: every year holds the same cells; the check below compares
    the last year's count);
  - the monthly panel (the first driver store of dataset.yaml): cell_id, lat, lon of the same
    group-year (lat and lon are static columns of the panel, repeated on every row).
Grid indices come from the unit id itself, '{group}_{ix}_{iy}' (plan 1.2's id format; the ingest wrote
the ACAG cells on the panel's grid), parsed from the right because group names hold underscores.

What it writes: <package>/data/static/part-0.parquet (dataset.yaml stores.static), written ONCE: an
existing file is refused, never replaced. Columns: cell_id, region, lat, lon, grid_ix, grid_iy.

    py -3.9 build_static.py <package folder>

Refuses (fail loudly): a unit of the target without lat/lon in the panel; a lat/lon that differs
between two rows of one cell; a unit id whose last two parts are not integers; a group whose last
year holds a different number of cells than its first year; an existing output file.

This is dataset code (it may name stores and drives); the engine never runs it (plan 1.1: ingest/ is
hashed, never executed by the engine).
"""
# Provenance: APP_PLAN.md 1.2 (static table: unit id, group id, lat, lon, optional grid_ix, grid_iy);
# engine/datasets/pm25/dataset.yaml (store templates; 'static: NOT WRITTEN YET'); acag_pm25_ingest.py
# (the ACAG cells are the panel's cells; region_grids reads the panel's cell_id, lat, lon).

import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

STATIC_COLUMNS = ("cell_id", "region", "lat", "lon", "grid_ix", "grid_iy")


def _template_files(template, package):
    """{(group, year): path} of a '{group}...{year}' template (a plain glob over its folder)."""
    path = template if os.path.isabs(template) else str(Path(package) / template)
    folder, name = os.path.split(path.replace("\\", "/"))
    pattern = re.escape(name).replace(re.escape("{group}"), "(?P<group>.+)").replace(
        re.escape("{year}"), "(?P<year>[0-9]+)")
    rx = re.compile("^" + pattern + "$")
    out = {}
    for entry in sorted(os.listdir(folder)):
        m = rx.match(entry)
        if m and os.path.isfile(os.path.join(folder, entry)):
            out[(m.group("group"), int(m.group("year")))] = os.path.join(folder, entry)
    return out


def _grid_indices(units, group):
    ix, iy = [], []
    for u in units:
        head, _, tail_y = u.rpartition("_")
        head2, _, tail_x = head.rpartition("_")
        if head2 != group:
            raise SystemExit("unit %r does not read as '%s_<ix>_<iy>'" % (u, group))
        try:
            ix.append(int(tail_x))
            iy.append(int(tail_y))
        except ValueError:
            raise SystemExit("unit %r: the grid indices are not integers" % u)
    return np.asarray(ix, dtype=np.int64), np.asarray(iy, dtype=np.int64)


def build(package):
    package = Path(package).resolve()
    ds = yaml.safe_load((package / "dataset.yaml").read_text(encoding="utf-8"))
    out = package / ds["stores"]["static"]
    if out.exists():
        raise SystemExit("%s exists; the static table is written once (delete it by hand to rebuild)" % out)
    target = _template_files(ds["stores"]["target"], package)
    panel = _template_files(ds["stores"]["drivers"][0], package)
    groups = sorted({g for g, _ in target})
    parts = []
    for g in groups:
        years = sorted(y for gg, y in target if gg == g)
        first, last = years[0], years[-1]
        units = pq.read_table(target[(g, first)], columns=["cell_id"]).column("cell_id").to_pandas()
        units = pd.unique(units.astype(object))
        n_last = len(pd.unique(pq.read_table(target[(g, last)], columns=["cell_id"])
                               .column("cell_id").to_pandas().astype(object)))
        if n_last != len(units):
            raise SystemExit("%s: %d cells in %d but %d in %d; the target is not one census"
                             % (g, len(units), first, n_last, last))
        if (g, first) not in panel:
            raise SystemExit("%s: no panel file for %d" % (g, first))
        pts = pq.read_table(panel[(g, first)], columns=["cell_id", "lat", "lon"]).to_pandas()
        pts["cell_id"] = pts["cell_id"].astype(object)
        per_cell = pts.groupby("cell_id", sort=False).agg(lat_n=("lat", "nunique"), lon_n=("lon", "nunique"),
                                                          lat=("lat", "first"), lon=("lon", "first"))
        moving = per_cell[(per_cell.lat_n > 1) | (per_cell.lon_n > 1)]
        if len(moving):
            raise SystemExit("%s: %d cells change lat/lon between rows, e.g. %s"
                             % (g, len(moving), moving.index[:3].tolist()))
        pos = per_cell.reindex(units)
        lost = pos.lat.isna() | pos.lon.isna()
        if lost.any():
            raise SystemExit("%s: %d target cells have no lat/lon in the panel, e.g. %s"
                             % (g, int(lost.sum()), list(np.asarray(units)[lost.to_numpy()][:3])))
        order = np.argsort(np.asarray(units, dtype=object).astype(str), kind="stable")
        units = np.asarray(units, dtype=object)[order]
        ix, iy = _grid_indices(units.tolist(), g)
        parts.append(pd.DataFrame({"cell_id": units, "region": np.full(len(units), g, dtype=object),
                                   "lat": pos.lat.to_numpy(dtype=np.float64)[order],
                                   "lon": pos.lon.to_numpy(dtype=np.float64)[order],
                                   "grid_ix": ix, "grid_iy": iy}))
        print("%-40s %7d cells" % (g, len(units)), flush=True)
    table = pd.concat(parts, ignore_index=True)
    if table.cell_id.duplicated().any():
        raise SystemExit("a unit id is listed twice: %s" % table.cell_id[table.cell_id.duplicated()].iloc[:3].tolist())
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp_%d" % os.getpid())
    pq.write_table(pa.Table.from_pandas(table[list(STATIC_COLUMNS)], preserve_index=False), str(tmp))
    os.rename(str(tmp), str(out))       # on Windows rename refuses an existing target: written once
    print("wrote %s: %d units in %d groups" % (out, len(table), len(groups)), flush=True)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: py -3.9 build_static.py <package folder>")
    build(sys.argv[1])
