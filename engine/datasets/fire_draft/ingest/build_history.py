"""Fire package: the fire-history store, recomputed from the target at the ruled label lag, and its store catalog
(owner command; plan 1.5 target-derived columns; OWNER_RULINGS_2026-09-28.md B R-D (b) and C 'Fire cells').

WHY A REBUILD. The shipped fire-history store D:/fire/history reads label t-1 (Part 492), which ruling R-D (b)
makes a leak (month t-1's label uses observations from month t; the engine's own history block starts at t-2),
and it holds the shipped 1,000-cell pick per group only (ruling C runs R18's stride over ALL units). This script
writes the columns of features/target_history.py at its NEWEST_LABEL_LAG (2: every column at month t reads labels
of months <= t-2; the four lag-1 rings cannot be built, so 15 columns, not the shipped 19):

    <out>/{group}.parquet        cell_id, year, month + the columns (float32); rows sorted by cell_id, year,
                                 month; every month of every target year for each unit (the grid is complete)
    <out>/history_manifest.json  the label lag, the columns, the unit rule, the sha256 of this file and of
                                 features/target_history.py, rows and units per group

    py -3.9 build_history.py <package folder> <out folder> [--units-from=<template>] [group ...]

The units: every unit of the package's static table, or (--units-from) the units a unit-keyed store holds per
group (a template relative to the package or absolute, with {group}; fire_draft builds its data/fire_history
copy from the units of data/fire_drivers/{group}.parquet, the shipped pick). Each group file is written ONCE; a
group whose file exists is skipped, so the command resumes after a stop. A folder whose manifest was written with
another label lag, other columns, another unit rule or other code is REFUSED (a resumed build never mixes two
versions): pass a new folder.

Size and time (measured 2026-09-29): every unit (925,737) takes about 2 GB and about 10 minutes (the largest
group, yakutia_larch, about 2.5 GB of RAM). Write it to the data disk (D:), never inside a package on C: (refused
without --units-from). The shipped pick (about 39,900 units) takes about 90 MB.

THE STORE CATALOG. The included shared catalog (../_stores/fire_history_schema_catalog.yaml) describes the
shipped store (lag 1, 19 columns, keyed on lat/lon). The rebuilt store needs its own:

    py -3.9 build_history.py catalog <package folder> <store template> (--every-unit | --units-from=<template>)

writes <package>/ingest/fire_history_store_catalog.yaml (generated; never edited by hand) and prints the include
line for dataset.yaml (path + sha256). Each column keeps the shipped facts (derived_from burned_frac, reads_target
true, dtype, units, cadence, stamp period_start) except: the window is NEWEST_LABEL_LAG months backward from the
start of the row's month (the newest label month t-L plus the target's detection reach into t-L+1 ... t-1, the
'wider window that ends at the content's end' convention of the shared catalogs; R8 reads only the forward edge,
so the lag is unchanged), the operation and provenance name the lag, and tslf_months's legal range starts at L.

What it reads (read-only, in place): the target files of each group (lat, lon, year, month, n_valid,
burned_frac) through the package's own validity rule (ingest/target_reader.py valid_labels); the target
product's region grid axes, D:/fire/geom/{group}.npz (la, lo), as fire_build_history.py:66-69 did; the static
table (the units and their lat/lon). The rings read every cell of that grid, unit or not; a grid cell the target
never holds (finnish_lapland has two such rows at its northern edge) is unobserved (0 in the rings).

Dataset code; the engine never runs it (plan 1.1).
"""
# Provenance: fire_build_history.py (the shipped builder: D:/fire/geom grid axes, the target, the 1,000-cell
# subset at the end); features/target_history.py; ingest/target_reader.py; OWNER_RULINGS_2026-09-28.md B R-D (b),
# C; engine/datasets/defo/features/build_store.py (the package-local generated store catalog, included by sha256).

import hashlib
import importlib.util
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

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
# the target product's region grid (fire_fetch_target.py writes it; fire_build_history.py:66-69 reads la, lo)
GEOM_TEMPLATE = "D:/fire/geom/{group}.npz"
MANIFEST = "history_manifest.json"
SHIPPED_CATALOG = "../_stores/fire_history_schema_catalog.yaml"     # relative to the package folder
STORE_CATALOG = "ingest/fire_history_store_catalog.yaml"            # relative to the package folder
STORE_NAME = "fire_history_rebuilt"
EVERY_UNIT = "every unit of the static table"


def _module(package, rel, name):
    path = Path(package) / rel
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _resolve(package, template):
    return template if os.path.isabs(template) else str(Path(package) / template)


def target_files(package, group):
    """{year: path} of the group's target files (dataset.yaml stores.target)."""
    ds = yaml.safe_load((Path(package) / "dataset.yaml").read_text(encoding="utf-8"))
    path = _resolve(package, ds["stores"]["target"])
    folder, name = os.path.split(path.replace("\\", "/"))
    rx = re.compile("^" + re.escape(name).replace(re.escape("{group}"), re.escape(group)).replace(
        re.escape("{year}"), "(?P<year>[0-9]+)") + "$")
    out = {}
    for entry in sorted(os.listdir(folder)):
        m = rx.match(entry)
        if m:
            out[int(m.group("year"))] = os.path.join(folder, entry)
    if not out:
        raise SystemExit("no target file for the group %s under %s" % (group, folder))
    return out


def grid_axes_of(group):
    """The region grid axes (la, lo) of the target product, rounded to 5 decimals (fire_build_history.py:66-69)."""
    path = GEOM_TEMPLATE.format(group=group)
    if not os.path.isfile(path):
        raise SystemExit("the region grid %s does not exist" % path)
    with np.load(path, allow_pickle=False) as z:
        la = np.round(np.asarray(z["la"], np.float64), 5)
        lo = np.round(np.asarray(z["lo"], np.float64), 5)
    if (np.diff(la) <= 0).any() or (np.diff(lo) <= 0).any():
        raise SystemExit("%s: the grid axes are not strictly increasing" % path)
    return la, lo


def group_grid(package, group):
    """(lat axis, lon axis, burned-fraction grid [i, j, month] with NaN = unobserved, first year): every target
    cell of every year of the group on the product's region grid, the validity rule applied. Refuses a target
    cell off the grid."""
    reader = _module(package, "ingest/target_reader.py", "fire_target_reader_for_history")
    th = _module(package, "features/target_history.py", "fire_target_history_for_history")
    files = target_files(package, group)
    years = sorted(files)
    if years != list(range(years[0], years[-1] + 1)):
        raise SystemExit("%s: the target years are not contiguous: %s" % (group, years))
    frames = []
    for y in years:
        t = pq.read_table(files[y], columns=["lat", "lon", "year", "month", "n_valid", "burned_frac"]).to_pandas()
        if not (t["year"].to_numpy() == y).all():
            raise SystemExit("%s: rows of another year in the file of %d" % (files[y], y))
        t["y"] = reader.valid_labels(t["burned_frac"].to_numpy(), t["n_valid"].to_numpy(), files[y])
        frames.append(t[["lat", "lon", "year", "month", "y"]])
    t = pd.concat(frames, ignore_index=True)
    la, lo = grid_axes_of(group)
    i, j = th.grid_positions(la, lo, t["lat"].to_numpy(), t["lon"].to_numpy())
    k = th.month_index(t["year"].to_numpy(), t["month"].to_numpy(), years[0])
    grid = np.full((len(la), len(lo), len(years) * th.MONTHS_PER_YEAR), np.nan, np.float32)
    flat = (i * len(lo) + j) * grid.shape[2] + k
    if len(np.unique(flat)) != len(flat):
        raise SystemExit("%s: the target repeats a (cell, month)" % group)
    grid[i, j, k] = t["y"].to_numpy(dtype=np.float32)
    return la, lo, grid, years[0]


def units_of(package, template, group):
    """The unit ids a unit-keyed store holds for the group (its cell_id column), sorted."""
    path = _resolve(package, template).format(group=group)
    if not os.path.isfile(path):
        raise SystemExit("the unit store %s does not exist" % path)
    ids = pq.read_table(path, columns=["cell_id"]).column("cell_id").to_pylist()
    return sorted(set(str(x) for x in ids))


def unit_history(package, group, newest_label_lag=None, units=None):
    """The columns for the group's units (DataFrame: cell_id, year, month, columns): every unit of the static
    table, or only the ids in ``units`` (each must be a unit of the group)."""
    th = _module(package, "features/target_history.py", "fire_target_history_for_history")
    reader = _module(package, "ingest/target_reader.py", "fire_target_reader_for_history")
    lag = th.NEWEST_LABEL_LAG if newest_label_lag is None else int(newest_label_lag)
    la, lo, grid, first_year = group_grid(package, group)
    cols = th.history_columns(grid, la, newest_label_lag=lag)
    names = list(cols)
    static = pq.read_table(str(reader.static_table_path(package)), columns=["cell_id", "region", "lat", "lon"]).to_pandas()
    groups = static["region"].astype(str)
    all_units = static[groups == group]
    if not len(all_units):
        raise SystemExit("the static table holds no unit of %s" % group)
    if units is not None:
        wanted = set(str(u) for u in units)
        unknown = sorted(wanted - set(all_units["cell_id"].astype(str)))
        if unknown:
            raise SystemExit("%s: %d requested ids are not units of the group, e.g. %s"
                             % (group, len(unknown), unknown[:3]))
        all_units = all_units[all_units["cell_id"].astype(str).isin(wanted)]
    units_frame = all_units.assign(cell_id=all_units["cell_id"].astype(str)).sort_values("cell_id", kind="stable")
    ui, uj = th.grid_positions(la, lo, units_frame["lat"].to_numpy(), units_frame["lon"].to_numpy())
    nmon = grid.shape[2]
    n = len(units_frame)
    out = pd.DataFrame({"cell_id": np.repeat(units_frame["cell_id"].to_numpy(dtype=object), nmon),
                        "year": np.tile(first_year + np.arange(nmon) // th.MONTHS_PER_YEAR, n).astype(np.int64),
                        "month": np.tile(np.arange(nmon) % th.MONTHS_PER_YEAR + 1, n).astype(np.int64)})
    for c in names:
        out[c] = cols[c][ui, uj, :].ravel()
    return out


def _manifest_head(package, units_from):
    th = _module(package, "features/target_history.py", "fire_target_history_for_history")
    return {"newest_label_lag": int(th.NEWEST_LABEL_LAG), "columns": list(th.COLUMNS),
            "units": EVERY_UNIT if units_from is None else "the units of %s" % units_from,
            "code_sha256": {"features/target_history.py": _sha256(Path(package) / "features" / "target_history.py"),
                            "ingest/build_history.py": _sha256(Path(package) / "ingest" / "build_history.py")}}


def build(package, out_dir, groups=None, units_from=None):
    package = Path(package).resolve()
    out_dir = Path(out_dir) if os.path.isabs(str(out_dir)) else Path.cwd() / out_dir
    inside = package in out_dir.resolve().parents or out_dir.resolve() == package
    if inside and units_from is None:
        raise SystemExit("write the history of every unit (about 2 GB) outside the package, on D: (%s)" % out_dir)
    reader = _module(package, "ingest/target_reader.py", "fire_target_reader_for_history")
    static = pq.read_table(str(reader.static_table_path(package)), columns=["region"]).to_pandas()
    every = sorted(static["region"].astype(str).unique())
    todo = every if not groups else list(groups)
    unknown = sorted(set(todo) - set(every))
    if unknown:
        raise SystemExit("groups %s are not in the static table" % unknown)
    head = _manifest_head(package, units_from)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / MANIFEST
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        differs = sorted(k for k in head if manifest.get(k) != head[k])
        if differs:
            raise SystemExit("%s was written with another %s: a resumed build would mix two versions; pass a new "
                             "folder" % (manifest_path, ", ".join(differs)))
    else:
        present = sorted(p.name for p in out_dir.glob("*.parquet"))
        if present:
            raise SystemExit("%s holds %d parquet files but no %s: they cannot be traced; pass a new folder"
                             % (out_dir, len(present), MANIFEST))
        manifest = dict(head, groups={})
    for g in todo:
        dst = out_dir / ("%s.parquet" % g)
        if dst.exists():
            if g not in manifest["groups"]:
                raise SystemExit("%s exists but the manifest does not list it" % dst)
            print("%-32s HAVE" % g, flush=True)
            continue
        units = None if units_from is None else units_of(package, units_from, g)
        frame = unit_history(package, g, units=units)
        tmp = dst.with_name(dst.name + ".tmp_%d" % os.getpid())
        pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), str(tmp))
        os.replace(str(tmp), str(dst))
        manifest["groups"][g] = {"rows": int(len(frame)), "units": int(frame["cell_id"].nunique())}
        tmp = manifest_path.with_name(manifest_path.name + ".tmp_%d" % os.getpid())
        tmp.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(str(tmp), str(manifest_path))
        print("%-32s %9d rows, %6d units" % (g, len(frame), manifest["groups"][g]["units"]), flush=True)
    return out_dir


# ------------------------------------------------------------------------------------------------ store catalog
def store_catalog(package, template, units_from=None):
    """The store catalog of a rebuilt store at ``template`` (a dict in the engine's StoreCatalog shape)."""
    th = _module(package, "features/target_history.py", "fire_target_history_for_history")
    shipped = yaml.safe_load((Path(package) / SHIPPED_CATALOG).read_text(encoding="utf-8"))
    L = int(th.NEWEST_LABEL_LAG)
    coverage = EVERY_UNIT if units_from is None else "the units of %s only" % units_from
    columns = {}
    for c in th.COLUMNS:
        f = dict(shipped["columns"][c])
        f["window"] = {"length": L, "unit": "month", "align": "backward"}
        f["operation"] = "%s; reads labels of months <= t-%d only (NEWEST_LABEL_LAG, ruling R-D b)" % (
            f["operation"], L)
        f["provenance"] = ("features/target_history.py (NEWEST_LABEL_LAG %d) written by ingest/build_history.py; "
                           "shipped definition %s" % (L, f["provenance"]))
        if c == "tslf_months":
            f["legal_range"] = [float(L), float(th.CAP)]
        f["fact_status"] = "unverified"
        columns[c] = f
    description = (
        "Fire-history features recomputed from the fire TARGET (MCD64A1 burned fraction) at newest label lag %d: "
        "every column at month t reads labels of months <= t-%d only (ruling R-D b; the shipped store "
        "D:/fire/history reads t-1). One parquet per fire group: %s; keys cell_id, year, month; units: %s. "
        "Written by ingest/build_history.py (features/target_history.py); the shipped lag-1 rings %s are not "
        "built. Every fact unverified." % (L, L, template, coverage, ", ".join(th.REFUSED_COLUMNS)))
    return {"store": STORE_NAME, "description": description, "columns": columns}


def store_catalog_text(package, template, units_from=None):
    header = ("# fire_history_store_catalog.yaml -- GENERATED by ingest/build_history.py catalog; never edit by hand.\n"
              "# The store catalog (treeroute.package.schema.StoreCatalog) of the fire-history store rebuilt at the\n"
              "# ruled label lag (ingest/build_history.py docstring, THE STORE CATALOG). Facts copied from\n"
              "# %s except the window, operation, provenance and tslf_months's legal range.\n" % SHIPPED_CATALOG)
    body = yaml.safe_dump(store_catalog(package, template, units_from), sort_keys=False, width=100,
                          allow_unicode=False, default_flow_style=False)
    return header + body


def write_store_catalog(package, template, units_from=None):
    """Writes <package>/ingest/fire_history_store_catalog.yaml; returns (include path, sha256)."""
    text = store_catalog_text(package, template, units_from)
    path = Path(package) / STORE_CATALOG
    tmp = path.with_name(path.name + ".tmp_%d" % os.getpid())
    tmp.write_bytes(text.encode("ascii"))
    os.replace(str(tmp), str(path))
    return STORE_CATALOG, _sha256(path)


def _option(args, name):
    hits = [a for a in args if a.startswith(name + "=")]
    if len(hits) > 1:
        raise SystemExit("%s given twice" % name)
    return (hits[0].split("=", 1)[1] if hits else None), [a for a in args if not a.startswith(name + "=")]


if __name__ == "__main__":
    argv = sys.argv[1:]
    usage = ("usage: py -3.9 build_history.py <package folder> <out folder> [--units-from=<template>] [group ...]\n"
             "       py -3.9 build_history.py catalog <package folder> <store template> "
             "(--every-unit | --units-from=<template>)")
    if argv[:1] == ["catalog"]:
        units_from, rest = _option(argv[1:], "--units-from")
        every = "--every-unit" in rest
        rest = [a for a in rest if a != "--every-unit"]
        if len(rest) != 2 or every == (units_from is not None):
            raise SystemExit(usage)
        inc, sha = write_store_catalog(Path(rest[0]).resolve(), rest[1], units_from)
        print("wrote %s\ndataset.yaml includes: - {path: %s, sha256: %s}" % (Path(rest[0]) / inc, inc, sha))
    else:
        units_from, rest = _option(argv, "--units-from")
        if len(rest) < 2:
            raise SystemExit(usage)
        build(rest[0], rest[1], rest[2:], units_from)
