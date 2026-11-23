"""Fire package: write the package's static table, which is also the target's lat/lon -> unit id KEY MAP
(plan 1.2 'Static table'; 'id maps (fire's lat/lon to id) live in the ingest script'; M4 'fire's key map').

The fire target store (D:/fire/target/{group}_{year}.parquet) and the two sidecar stores are keyed on
lat + lon, not on a unit id. The unit is the monthly panel's 4 km cell ({group}_{ix}_{iy}, plan 1.2's id
format, as PM2.5): the shipped fire run joined target, panel and sidecars on the SAME key, lat and lon
rounded to 5 decimals (fire_architecture.py:241-243, used at :253-266 and :285), and this script keeps that
key exactly.

The unit set (one row per unit), per group:
    the union over ALL target years of the target's cells (a cell missing from some years' files is still a
    unit: its missing months become NaN labels in the target reader, so the grid is a complete census),
    INTERSECTED with the panel's cells (the union over the same years of the panel's cell_id, lat, lon).
  - A target cell with no panel cell is NOT a unit: it has no unit id in the plan's format and none of the
    panel's drivers. It is counted per group in the manifest (the shipped 1,000-cell pick was drawn from the
    same panel x target intersection, fire_select_cells.py). It still counts as a NEIGHBOUR in the fire-history
    rings (features/target_history.py reads the target product's whole grid, as fire_build_history.py did).
  - A panel cell with no target cell is not a unit (no label); counted too.

Columns written: cell_id, region, lat, lon (the panel's cell centre, EPSG:4326, float64 of the stored
float32), grid_ix, grid_iy (the two integers of the id, parsed from the right because group names hold
underscores). The engine reads them for the overlap blocks (R14: the 'grid_indices' link rule) and the router
context; the target reader reads cell_id, region, lat, lon as the key map.

What it reads (read-only, in place): every target file of every group (lat, lon only) and every panel file
of the same group-years (cell_id, lat, lon only). What it writes, ONCE (an existing file is refused, never
replaced):
    <package>/data/static/part-0.parquet          (dataset.yaml stores.static)
    <package>/data/static/key_map_manifest.json   (per-group counts and the key rule; not read by the engine)

    py -3.9 build_static.py <package folder>

Refuses (fail loudly): a panel cell whose lat/lon changes between years; two panel cells on one key; a unit
id that does not read as '{group}_<int>_<int>'; a group with no target or no panel file for a target year;
a unit listed twice; an existing output file.

Dataset code (it may name stores and drives); the engine never runs it (plan 1.1: ingest/ is hashed, never
executed by the engine; the target reader is the one ingest file the engine runs).
"""
# Provenance: APP_PLAN.md 1.2 (static table; unit id format; 'id maps (fire's lat/lon to id) live in the
# ingest script'); fire_architecture.py:241-243 (the key), :250-266 (panel x target x cells_1000 on the key);
# fire_select_cells.py (the shipped pick drawn from the panel/target grid intersection); OWNER_RULINGS_2026-09-28.md
# C 'Fire cells' (R18's stride runs over ALL cells, so the unit set is every intersecting cell, not cells_1000).

import json
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
MANIFEST = "key_map_manifest.json"
KEY_RULE = ("key = int(round(lat, 5) * 1e5) * 1e8 + int(round(lon, 5) * 1e5) on float64 of the stored float32 "
            "(fire_architecture.py:241-243)")


def cell_key(lat, lon):
    """The shipped lat/lon key (fire_architecture.py:241-243), exactly: round to 5 decimals, scale, truncate."""
    return ((np.round(np.asarray(lat).astype(np.float64), 5) * 100000).astype(np.int64) * 100000000
            + (np.round(np.asarray(lon).astype(np.float64), 5) * 100000).astype(np.int64))


def template_files(template, package):
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


def grid_indices(units, group):
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


def target_keys(files):
    """Union over the files of the target's cell keys."""
    keys = []
    for path in files:
        t = pq.read_table(path, columns=["lat", "lon"])
        keys.append(np.unique(cell_key(t.column("lat").to_numpy(), t.column("lon").to_numpy())))
    return np.unique(np.concatenate(keys))


def panel_cells(files, group):
    """Union over the files of the panel's cells: DataFrame(key, cell_id, lat, lon), one row per cell."""
    parts = []
    for path in files:
        p = pq.read_table(path, columns=["cell_id", "lat", "lon"]).to_pandas()
        p = p.drop_duplicates(["cell_id", "lat", "lon"])
        parts.append(p)
    p = pd.concat(parts, ignore_index=True).drop_duplicates(["cell_id", "lat", "lon"])
    p["cell_id"] = p["cell_id"].astype(object).map(str)
    moving = p[p.cell_id.duplicated(keep=False)]
    if len(moving):
        raise SystemExit("%s: %d panel cells change lat/lon between years, e.g. %s"
                         % (group, moving.cell_id.nunique(), moving.cell_id.iloc[:3].tolist()))
    p["key"] = cell_key(p.lat.to_numpy(), p.lon.to_numpy())
    twice = p[p.key.duplicated(keep=False)]
    if len(twice):
        raise SystemExit("%s: %d panel cells share a lat/lon key, e.g. %s"
                         % (group, len(twice), twice.cell_id.iloc[:4].tolist()))
    return p


def build(package):
    package = Path(package).resolve()
    ds = yaml.safe_load((package / "dataset.yaml").read_text(encoding="utf-8"))
    out = package / ds["stores"]["static"]
    manifest_path = out.parent / MANIFEST
    for path in (out, manifest_path):
        if path.exists():
            raise SystemExit("%s exists; the static table is written once (delete it by hand to rebuild)" % path)
    target = template_files(ds["stores"]["target"], package)
    panel = template_files(ds["stores"]["drivers"][0], package)
    groups = sorted({g for g, _ in target})
    parts, manifest = [], {}
    for g in groups:
        years = sorted(y for gg, y in target if gg == g)
        lost = [y for y in years if (g, y) not in panel]
        if lost:
            raise SystemExit("%s: no panel file for the target years %s" % (g, lost))
        tkeys = target_keys([target[(g, y)] for y in years])
        pcells = panel_cells([panel[(g, y)] for y in years], g)
        units = pcells[pcells.key.isin(tkeys)].sort_values("cell_id", kind="stable")
        ids = units.cell_id.to_numpy(dtype=object)
        ix, iy = grid_indices(ids.tolist(), g)
        parts.append(pd.DataFrame({"cell_id": ids, "region": np.full(len(ids), g, dtype=object),
                                   "lat": units.lat.to_numpy().astype(np.float64),
                                   "lon": units.lon.to_numpy().astype(np.float64),
                                   "grid_ix": ix, "grid_iy": iy}))
        n_target_only = int(len(tkeys) - len(units))
        manifest[g] = {"years": [years[0], years[-1]], "target_cells": int(len(tkeys)),
                       "panel_cells": int(len(pcells)), "units": int(len(units)),
                       "target_cells_without_panel_cell": n_target_only,
                       "panel_cells_without_target_cell": int(len(pcells) - len(units))}
        print("%-32s %7d units | %6d target cells without a panel cell | %6d panel cells without a target cell"
              % (g, len(units), n_target_only, len(pcells) - len(units)), flush=True)
    table = pd.concat(parts, ignore_index=True)
    if table.cell_id.duplicated().any():
        raise SystemExit("a unit id is listed twice: %s" % table.cell_id[table.cell_id.duplicated()].iloc[:3].tolist())
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp_%d" % os.getpid())
    pq.write_table(pa.Table.from_pandas(table[list(STATIC_COLUMNS)], preserve_index=False), str(tmp))
    os.rename(str(tmp), str(out))       # on Windows rename refuses an existing target: written once
    doc = {"key_rule": KEY_RULE,
           "unit_set": "per group: the union over all target years of the target's cells, intersected with the "
                       "union over the same years of the panel's cells; the unit id is the panel's cell_id",
           "target_store": ds["stores"]["target"], "panel_store": ds["stores"]["drivers"][0],
           "units": int(len(table)), "groups": manifest}
    tmp = manifest_path.with_name(manifest_path.name + ".tmp_%d" % os.getpid())
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=True), encoding="utf-8")
    os.rename(str(tmp), str(manifest_path))
    print("wrote %s: %d units in %d groups (manifest %s)" % (out, len(table), len(groups), manifest_path.name),
          flush=True)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: py -3.9 build_static.py <package folder>")
    build(sys.argv[1])
