"""Deforestation package: write the package's static table (plan 1.2 'Static table'; 6.2 step 2).

The static table holds one row per unit: the unit id, its group, its representative point (lat, lon;
the cell centre as the monthly panel stores it), its grid indices, and forest2000_px, the report stratum
(Q50: results by year-2000 forest-pixel quartiles). The engine reads it for the overlap blocks (R14:
'grid_indices' link rule when grid_ix / grid_iy exist) and for the per-stratum tables (R34: a static
stratum comes from the static table). forest2000_px is a Hansen co-product with a forced ban: it never
reaches the trees, only the report.

What it reads (read-only, in place):
  - the target store (dataset.yaml stores.target, one file per group): the unit ids of every group, and
    forest2000_px, which must be ONE value per cell across the years (the year-2000 forest mask);
  - the monthly panel (D:/monthly_panel, the source store dataset.yaml declares): cell_id, lat, lon of
    the group's first panel year (lat and lon are static columns, repeated on every row).
Grid indices come from the unit id itself, '{group}_{ix}_{iy}' (plan 1.2's id format), parsed from the
right because group names hold underscores.

What it writes: dataset.yaml's stores.static (D:/defo_features/static/part-0.parquet, beside the features
store), written ONCE: an existing file is refused, never replaced. Columns: cell_id, region, lat, lon,
grid_ix, grid_iy, forest2000_px.

    py -3.9 build_static.py <package folder> [--out=<file>]        (--out: a test copy elsewhere)
    py -3.9 build_static.py <package folder> --out=<file> --groups=a,b     (a partial test copy)

--groups needs --out: the canonical table is written once and must hold every group, so a partial
table never takes its path. A --groups name without a target file is refused.

Refuses (fail loudly): a target cell without lat/lon in the panel; a lat/lon that differs between two rows
of one cell; a forest2000_px that differs between two years of one cell; a unit id whose last two parts
are not integers; a repeated unit; an existing output file.

This is dataset code (it may name stores and drives); the engine never runs it (plan 1.1: ingest/ is
hashed, never executed by the engine).
"""
# Provenance: APP_PLAN.md 1.2 (static table: unit id, group id, lat, lon, optional grid_ix, grid_iy), R34 / Q50
# (forest2000_px quartiles as the report stratum; HEADLINE_QUESTIONS_AND_FIXES.md:51, 346-349);
# engine/datasets/pm25/ingest/build_static.py (the same table for the PM2.5 package); defo_ingest.py:9-16
# (forest2000_px = year-2000 forest pixels of the cell, one mask for every year).

import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

STATIC_COLUMNS = ("cell_id", "region", "lat", "lon", "grid_ix", "grid_iy", "forest2000_px")
PANEL_TEMPLATE = "D:/monthly_panel/{group}_monthly_{year}.parquet"


def _template_files(template):
    folder, name = os.path.split(template.replace("\\", "/"))
    pattern = re.escape(name).replace(re.escape("{group}"), "(?P<group>.+?)").replace(
        re.escape("{year}"), "(?P<year>[0-9]{4})")
    rx = re.compile("^" + pattern + "$")
    out = {}
    for entry in sorted(os.listdir(folder)):
        m = rx.match(entry)
        if m and os.path.isfile(os.path.join(folder, entry)):
            key = (m.group("group"),) + ((int(m.group("year")),) if "year" in m.groupdict() else ())
            out[key] = os.path.join(folder, entry)
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


def group_rows(target_path, panel_path, group):
    """The static rows of one group (sorted by unit id)."""
    t = pq.read_table(target_path, columns=["cell_id", "forest2000_px"]).to_pandas()
    t["cell_id"] = t["cell_id"].astype(str)
    per = t.groupby("cell_id", sort=True)["forest2000_px"].agg(["min", "max"])
    moving = per[per["min"] != per["max"]]
    if len(moving):
        raise SystemExit("%s: %d cells change forest2000_px between years, e.g. %s"
                         % (group, len(moving), moving.index[:3].tolist()))
    units = per.index.to_numpy(dtype=object)
    pts = pq.read_table(panel_path, columns=["cell_id", "lat", "lon"]).to_pandas()
    pts["cell_id"] = pts["cell_id"].astype(str)
    agg = pts.groupby("cell_id", sort=False).agg(lat_n=("lat", "nunique"), lon_n=("lon", "nunique"),
                                                 lat=("lat", "first"), lon=("lon", "first"))
    bad = agg[(agg.lat_n > 1) | (agg.lon_n > 1)]
    if len(bad):
        raise SystemExit("%s: %d cells change lat/lon between rows, e.g. %s" % (group, len(bad), bad.index[:3].tolist()))
    pos = agg.reindex(units)
    lost = pos.lat.isna() | pos.lon.isna()
    if lost.any():
        raise SystemExit("%s: %d target cells have no lat/lon in the panel, e.g. %s"
                         % (group, int(lost.sum()), list(units[lost.to_numpy()][:3])))
    ix, iy = _grid_indices(units.tolist(), group)
    return pd.DataFrame({"cell_id": units, "region": np.full(len(units), group, dtype=object),
                         "lat": pos.lat.to_numpy(dtype=np.float64), "lon": pos.lon.to_numpy(dtype=np.float64),
                         "grid_ix": ix, "grid_iy": iy,
                         "forest2000_px": per["min"].to_numpy(dtype=np.float64)})


def build(package, out=None, groups=None):
    if groups and out is None:
        raise SystemExit("--groups needs --out: the canonical static table (dataset.yaml stores.static) is written "
                         "once and must hold every group; write a partial table elsewhere")
    package = Path(package).resolve()
    ds = yaml.safe_load((package / "dataset.yaml").read_text(encoding="utf-8"))
    if PANEL_TEMPLATE not in ds["stores"]["drivers"]:
        raise SystemExit("dataset.yaml does not declare the monthly panel %s" % PANEL_TEMPLATE)
    out = Path(out if out is not None else ds["stores"]["static"])
    if not out.is_absolute():
        out = package / out
    if out.exists():
        raise SystemExit("%s exists; the static table is written once (delete it by hand to rebuild)" % out)
    target = _template_files(ds["stores"]["target"])
    panel = _template_files(PANEL_TEMPLATE)
    all_groups = sorted(k[0] for k in target)
    unknown = sorted(set(groups or ()) - set(all_groups))
    if unknown:
        raise SystemExit("--groups names groups without a target file: %s" % unknown)
    todo = all_groups if not groups else [g for g in all_groups if g in set(groups)]
    parts = []
    for g in todo:
        years = sorted(y for gg, y in panel if gg == g)
        if not years:
            raise SystemExit("%s: no monthly panel file" % g)
        rows = group_rows(target[(g,)], panel[(g, years[0])], g)
        parts.append(rows)
        print("%-40s %7d cells" % (g, len(rows)), flush=True)
    table = pd.concat(parts, ignore_index=True)
    if table.cell_id.duplicated().any():
        raise SystemExit("a unit id is listed twice: %s" % table.cell_id[table.cell_id.duplicated()].iloc[:3].tolist())
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp_%d" % os.getpid())
    pq.write_table(pa.Table.from_pandas(table[list(STATIC_COLUMNS)], preserve_index=False), str(tmp))
    os.rename(str(tmp), str(out))       # on Windows rename refuses an existing target: written once
    print("wrote %s: %d units in %d groups" % (out, len(table), len(todo)), flush=True)
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    if len(args) != 1 or set(opts) - {"out", "groups"}:
        raise SystemExit("usage: py -3.9 build_static.py <package folder> [--out=<file>] [--groups=a,b]")
    build(args[0], opts.get("out"), [g for g in opts.get("groups", "").split(",") if g] or None)
