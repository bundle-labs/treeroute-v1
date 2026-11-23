"""Fire package: a unit-keyed copy of the drivers sidecar store (plan 1.2 'Driver tables: Grid: unit id,
time, columns at the target's step'; 'id maps (fire's lat/lon to id) live in the ingest script').

WHY A COPY. The engine's driver reader joins every driver store on the catalog's key_unit column
(treeroute/pipeline/data.py, ColumnReader._read_drivers reads [cell_id, year, month] + the columns). The
fire drivers sidecar is keyed on lat + lon only, so the engine cannot read it in place. This script writes a
copy, keyed on the unit id through the package's key map (the static table, ingest/build_static.py), with every
value unchanged:

    D:/fire/drivers/joined/{group}.parquet  -> <package>/data/fire_drivers/{group}.parquet

The other sidecar, the fire-history store D:/fire/history, is NOT copied: it reads label t-1, a leak under
ruling R-D (b). ingest/build_history.py recomputes it from the target at the ruled lag instead (fire_draft:
data/fire_history, on the units of this copy, --units-from=data/fire_drivers/{group}.parquet).

Columns written: cell_id, year, month, then the store's value columns in the store's order (lat and lon are
dropped: they are the key). Rows sorted by cell_id, year, month. Each output file is written ONCE (an existing
file is refused, never replaced); a group whose outputs both exist is skipped, so the script resumes.

COVERAGE (owner item, see AUDIT_CHECKLIST.md): the drivers sidecar exists ONLY for the shipped 1,000-cell pick
per group (D:/fire/cells_1000.parquet), not for every unit. Under ruling C ('Fire cells: the R18 stride over
all cells') about 92% of bank units are outside that pick, so their lightning / VOD / biomass columns would be
missing and 0-filled; fire_draft therefore marks them conditional (tests/test_fire_package.py,
COVERAGE_REASON). They cannot be rebuilt for every unit without re-joining their raw products
(fire_join_drivers.py; D:/fire/drivers/raw).

    py -3.9 build_sidecars.py <package folder>

A sidecar cell that is not a unit (the target never holds it, so it has no label: finnish_lapland has 15 such
cells in the shipped pick, on 9 latitude rows no target file holds; 103 over the 40 groups; the shipped run
dropped them by its inner join with the target) is dropped; the count per group is written to
<package>/data/sidecar_rekey_manifest.json (outside the store folder) and printed.

Refuses (fail loudly): a repeated (unit, year, month); a missing static table.

Read-only on D:/fire. Dataset code; the engine never runs it (plan 1.1).
"""
# Provenance: fire_join_drivers.py (the drivers sidecar: lat, lon, year, month + its columns, the 1,000-cell
# pick); fire_architecture.py:241-243, 276-288 (the shipped left join of both sidecars on the lat/lon key);
# APP_PLAN.md 1.2; OWNER_RULINGS_2026-09-28.md B R-D (b) (why the history sidecar is recomputed, not copied).

import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

SIDECARS = (
    ("D:/fire/drivers/joined/{group}.parquet", "data/fire_drivers/{group}.parquet"),
)
KEYS = ("lat", "lon", "year", "month")
MANIFEST = "data/sidecar_rekey_manifest.json"


def _reader(package):
    """The package's own target reader module (its key map), loaded from its path."""
    path = Path(package) / "ingest" / "target_reader.py"
    spec = importlib.util.spec_from_file_location("fire_target_reader_for_sidecars", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rekey(source, group, km, cell_key):
    """One sidecar file keyed on the unit id (see the module docstring)."""
    table = pq.read_table(source).to_pandas()
    missing = [c for c in KEYS if c not in table.columns]
    if missing:
        raise SystemExit("%s has no key column %s" % (source, missing))
    values = [c for c in table.columns if c not in KEYS]
    keys = cell_key(table["lat"].to_numpy(), table["lon"].to_numpy())
    unit, ok = km.lookup(keys)
    dropped = sorted(set(np.unique(keys[~ok]).tolist()))
    table = table[ok]
    unit = unit[ok]
    out = pd.DataFrame({"cell_id": km.ids[unit],
                        "year": table["year"].to_numpy().astype(np.int64),
                        "month": table["month"].to_numpy().astype(np.int64)})
    for c in values:
        out[c] = table[c].to_numpy()
    if out.duplicated(["cell_id", "year", "month"]).any():
        raise SystemExit("%s repeats a (unit, year, month)" % source)
    return out.sort_values(["cell_id", "year", "month"], kind="stable").reset_index(drop=True), dropped


def build(package):
    package = Path(package).resolve()
    reader = _reader(package)
    groups = sorted(set.intersection(*[{p.stem for p in Path(os.path.dirname(src)).glob("*.parquet")}
                                       for src, _ in SIDECARS]))
    every = sorted(set.union(*[{p.stem for p in Path(os.path.dirname(src)).glob("*.parquet")}
                               for src, _ in SIDECARS]))
    if groups != every:
        raise SystemExit("the sidecars hold different groups: %s" % sorted(set(every) - set(groups)))
    manifest_path = package / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {
        "rule": "sidecar rows keyed on the unit id through the static table (the shipped lat/lon key); rows of "
                "cells that are not units are dropped (no target cell, so no label)",
        "sources": {dst: src for src, dst in SIDECARS}, "dropped_cells": {}}
    for g in groups:
        outs = [package / dst.format(group=g) for _, dst in SIDECARS]
        if all(o.exists() for o in outs):
            print("%-32s HAVE" % g, flush=True)
            continue
        km = reader.key_map(g, package)
        for (src, rel), dst in zip(SIDECARS, outs):
            if dst.exists():
                continue
            frame, dropped = rekey(src.format(group=g), g, km, reader.cell_key)
            dst.parent.mkdir(parents=True, exist_ok=True)
            tmp = dst.with_name(dst.name + ".tmp_%d" % os.getpid())
            pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), str(tmp))
            os.rename(str(tmp), str(dst))
            manifest["dropped_cells"].setdefault(rel, {})[g] = len(dropped)
            print("%-32s %-14s %8d rows, %5d units%s" % (g, dst.parent.name, len(frame), frame.cell_id.nunique(),
                  (" | %d cells that are not units dropped" % len(dropped)) if dropped else ""), flush=True)
        tmp = manifest_path.with_name(manifest_path.name + ".tmp_%d" % os.getpid())
        tmp.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(str(tmp), str(manifest_path))
    return package


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: py -3.9 build_sidecars.py <package folder>")
    build(sys.argv[1])
