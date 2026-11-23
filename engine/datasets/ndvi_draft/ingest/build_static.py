"""NDVI package: write the package's static table (plan 1.2 'Static table'; 6.2 step 2).

The static table holds one row per unit: the unit id, its group, its representative point (lat, lon;
EPSG:4326, the cell centre) and its grid indices. The engine reads it for the overlap blocks (R14: the
'grid_indices' link rule when grid_ix / grid_iy exist; NDVI's groups share cells, e.g. australian_mulga and
brigalow_belt, expected_derived.json R14_overlap_blocks) and the router context.

What it reads (read-only, in place): the target store (dataset.yaml stores.target), which for NDVI IS the
monthly panel: cell_id, lat, lon of the FIRST year's file of each group (lat and lon are static columns of
the panel, repeated on every row), and the cell ids of EVERY other year's file of the group (the census
check below: each year must hold exactly the first year's cell set).
Grid indices come from the unit id itself, '{group}_{ix}_{iy}' (plan 1.2's id format), parsed from the
right because group names hold underscores.

What it writes: <package>/data/static/part-0.parquet (dataset.yaml stores.static), written ONCE: an existing
file is refused, never replaced. Columns: cell_id, region, lat, lon, grid_ix, grid_iy.

    py -3.9 build_static.py <package folder>

Refuses (fail loudly): a lat/lon that differs between two rows of one cell; ANY row of the first year's file
whose lat or lon is missing, non-finite or outside [-90, 90] / [-180, 180] (checked row by row BEFORE the
per-cell reduction, whose nunique and first skip NaN; the range catches the panel's integer fill codes, which
are finite); a row with no cell id; a unit id whose last two parts are not integers or that does not start with its
group; a group any of whose years holds another cell set than its first year (every year is checked, not
only the two ends); a unit listed twice; an existing output file.

static_table(package) builds and checks the table without writing anything (a read-only re-check of a
written table compares against it); build(package) refuses an existing output first, then writes it.

This is dataset code (it may name stores and drives); the engine never runs it (plan 1.1: ingest/ is hashed,
never executed by the engine).
"""
# Provenance: APP_PLAN.md 1.2 (static table: unit id, group id, lat, lon, optional grid_ix, grid_iy);
# engine/datasets/pm25/ingest/build_static.py (the same builder for the PM2.5 target, whose cells are the
# panel's); engine/datasets/ndvi/dataset.yaml (the store templates).

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
    """{(group, year): path} of a '{group}...{year}' template (a plain listing of its folder)."""
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


def _cell_set(path):
    """The distinct cell ids of one target file (arrow's hash unique over the one column)."""
    return set(pq.read_table(str(path), columns=["cell_id"]).column("cell_id").unique().to_pylist())


def group_rows(files, group):
    """The static rows of one group (sorted by unit id) from its target files, in year order: lat and lon
    from the first file, and every file must hold exactly the first file's cell set (one census)."""
    files = list(files)
    if not files:
        raise SystemExit("%s: no target file" % group)
    first_file = files[0]
    pts = pq.read_table(str(first_file), columns=["cell_id", "lat", "lon"]).to_pandas()
    if pts["cell_id"].isna().any():
        raise SystemExit("%s: %d rows of %s have no cell id" % (group, int(pts["cell_id"].isna().sum()), first_file))
    pts["cell_id"] = pts["cell_id"].astype(object)
    lat = pts["lat"].to_numpy(dtype=np.float64)
    lon = pts["lon"].to_numpy(dtype=np.float64)
    with np.errstate(invalid="ignore"):
        bad_row = ~(np.isfinite(lat) & np.isfinite(lon) & (np.abs(lat) <= 90.0) & (np.abs(lon) <= 180.0))
    if bad_row.any():
        raise SystemExit("%s: %d rows of %s have a cell id but a missing, non-finite or out-of-range lat/lon, "
                         "e.g. cells %s" % (group, int(bad_row.sum()), first_file,
                                            sorted(set(str(u) for u in pts["cell_id"][bad_row]))[:3]))
    per_cell = pts.groupby("cell_id", sort=True).agg(lat_n=("lat", "nunique"), lon_n=("lon", "nunique"),
                                                     lat=("lat", "first"), lon=("lon", "first"))
    moving = per_cell[(per_cell.lat_n > 1) | (per_cell.lon_n > 1)]
    if len(moving):
        raise SystemExit("%s: %d cells change lat/lon between rows, e.g. %s"
                         % (group, len(moving), moving.index[:3].tolist()))
    census = set(per_cell.index)
    for other in files[1:]:
        cells = _cell_set(other)
        if cells != census:
            raise SystemExit("%s: the first year's file holds %d cells and %s holds %d (%d differ); the target is "
                             "not one census" % (group, len(census), other, len(cells), len(cells ^ census)))
    units = np.asarray([str(u) for u in per_cell.index], dtype=object)
    order = np.argsort(units, kind="stable")
    units = units[order]
    ix, iy = _grid_indices(units.tolist(), group)
    return pd.DataFrame({"cell_id": units, "region": np.full(len(units), group, dtype=object),
                         "lat": per_cell.lat.to_numpy(dtype=np.float64)[order],
                         "lon": per_cell.lon.to_numpy(dtype=np.float64)[order],
                         "grid_ix": ix, "grid_iy": iy})


def _output_path(package, ds):
    return package / ds["stores"]["static"]


def static_table(package):
    """The checked static table of a package (every group, every year's census); writes nothing."""
    package = Path(package).resolve()
    ds = yaml.safe_load((package / "dataset.yaml").read_text(encoding="utf-8"))
    target = _template_files(ds["stores"]["target"], package)
    groups = sorted({g for g, _ in target})
    if not groups:
        raise SystemExit("the target store %s holds no file" % ds["stores"]["target"])
    parts = []
    for g in groups:
        years = sorted(y for gg, y in target if gg == g)
        parts.append(group_rows([target[(g, y)] for y in years], g))
        print("%-40s %7d cells, %d years" % (g, len(parts[-1]), len(years)), flush=True)
    table = pd.concat(parts, ignore_index=True)
    if table.cell_id.duplicated().any():
        raise SystemExit("a unit id is listed twice: %s" % table.cell_id[table.cell_id.duplicated()].iloc[:3].tolist())
    return table[list(STATIC_COLUMNS)]


def build(package):
    package = Path(package).resolve()
    ds = yaml.safe_load((package / "dataset.yaml").read_text(encoding="utf-8"))
    out = _output_path(package, ds)
    if out.exists():
        raise SystemExit("%s exists; the static table is written once (delete it by hand to rebuild)" % out)
    table = static_table(package)
    groups = table["region"].nunique()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp_%d" % os.getpid())
    pq.write_table(pa.Table.from_pandas(table[list(STATIC_COLUMNS)], preserve_index=False), str(tmp))
    os.rename(str(tmp), str(out))       # on Windows rename refuses an existing target: written once
    print("wrote %s: %d units in %d groups" % (out, len(table), groups), flush=True)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: py -3.9 build_static.py <package folder>")
    build(sys.argv[1])
