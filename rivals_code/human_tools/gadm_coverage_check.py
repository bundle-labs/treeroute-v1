"""Check the D4 GADM download against the defo regions (read-only on every input).

Proves the hand-assigned country list in fetch_products.py (D4_REGION_COUNTRIES) is complete and says which
fetched countries no cell touches. Reads downloaded files, so run it isolated with the folder as an argument:

    py -3.9 -I D:\\treeroute\\human_tools\\gadm_coverage_check.py D:\\treeroute\\human_products\\gadm\\3.6_gpkg_defo42
        D:\\treeroute\\human_tools\\reports\\gadm_coverage.json

Per region: the 4 km cells (lat/lon from D:/monthly_panel/<region>_monthly_2010.parquet, as defo_ingest.py:99-104;
footprint = centre +- half the median spacing, defo_ingest.py:130-131). A cell is COVERED when its centre lies in a
fetched country's level-0 polygon. Uncovered cells are split into "coastal" (footprint touches a fetched country)
and "orphan" (touches none: a missing country or open sea). Per country: regions whose cell footprints touch it,
level-2 present or not and its unit count. Every file's SHA-256 is checked against product_manifest.json first.
"""
import glob
import hashlib
import json
import os
import sys
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely

DEFO_TARGET = r"D:\defo_target"
PANEL = r"D:\monthly_panel"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def region_cells(reg):
    d = pd.read_parquet(os.path.join(PANEL, "%s_monthly_2010.parquet" % reg),
                        columns=["cell_id", "lon", "lat"]).drop_duplicates("cell_id")
    d["lon"] = pd.to_numeric(d.lon, errors="coerce").astype("float64")
    d["lat"] = pd.to_numeric(d.lat, errors="coerce").astype("float64")
    d = d[np.isfinite(d.lon) & np.isfinite(d.lat)].reset_index(drop=True)
    ulon, ulat = np.sort(d.lon.unique()), np.sort(d.lat.unique())
    hx = float(np.median(np.diff(ulon))) / 2 if len(ulon) > 1 else 0.02
    hy = float(np.median(np.diff(ulat))) / 2 if len(ulat) > 1 else 0.02
    return d, hx, hy


def main(folder, out_json):
    man = json.load(open(os.path.join(folder, "product_manifest.json"), encoding="utf-8"))
    files = man["files"]
    countries = {}
    for fn, rec in sorted(files.items()):
        p = os.path.join(folder, fn)
        if sha256_file(p) != rec["sha256"]:
            raise SystemExit("hash mismatch: %s" % p)
        iso = fn.split("_")[1]
        with zipfile.ZipFile(p) as z:
            inner = [n for n in z.namelist() if n.lower().endswith(".gpkg")]
        if len(inner) != 1:
            raise SystemExit("%s: expected one .gpkg inside, found %s" % (fn, inner))
        vsi = "/vsizip/%s/%s" % (p.replace("\\", "/"), inner[0])
        layers = [l[0] for l in pyogrio.list_layers(vsi)]
        l0 = "gadm36_%s_0" % iso
        l2 = "gadm36_%s_2" % iso
        g0 = gpd.read_file(vsi, layer=l0, engine="pyogrio")[["geometry"]]
        n2 = int(pyogrio.read_info(vsi, layer=l2)["features"]) if l2 in layers else 0
        countries[iso] = {"file": fn, "layers": layers, "level2_present": l2 in layers, "level2_units": n2,
                          "geom": shapely.union_all(g0.geometry.values)}
        print("%s layers=%s level2_units=%d" % (iso, ",".join(layers), n2), flush=True)
    # Prepared geometries + vectorised tests: sjoin against huge coastlines (CAN, RUS, IDN) is far too slow.
    for c in countries.values():
        shapely.prepare(c["geom"])
        c["bounds"] = c["geom"].bounds
    regions = sorted(os.path.basename(f)[:-8] for f in glob.glob(os.path.join(DEFO_TARGET, "*.parquet")))
    rep = {"folder": folder, "regions": {}, "countries": {}}
    touched = {k: set() for k in countries}
    for reg in regions:
        d, hx, hy = region_cells(reg)
        x, y = d.lon.values, d.lat.values
        x0, x1, y0, y1 = x.min() - hx, x.max() + hx, y.min() - hy, y.max() + hy
        boxes = shapely.box(x - hx, y - hy, x + hx, y + hy)
        centre_iso = np.array([None] * len(d), dtype=object)
        fp_any = np.zeros(len(d), bool)
        tl = []
        for iso, c in countries.items():
            bx0, by0, bx1, by1 = c["bounds"]
            if bx0 > x1 or bx1 < x0 or by0 > y1 or by1 < y0:
                continue
            inside = shapely.contains_xy(c["geom"], x, y)
            centre_iso[inside & (centre_iso == None)] = iso
            hit = shapely.intersects(c["geom"], boxes)
            if hit.any():
                touched[iso].add(reg)
                tl.append(iso)
            fp_any |= hit
        unc = centre_iso == None
        by = pd.Series(centre_iso[~unc]).value_counts().to_dict()
        coastal = int((unc & fp_any).sum())
        orph = d.loc[unc & ~fp_any, ["lat", "lon"]]
        rep["regions"][reg] = {
            "cells": int(len(d)), "covered_by_centre": {k: int(v) for k, v in by.items()},
            "uncovered": int(unc.sum()), "uncovered_coastal": coastal, "orphans": int(len(orph)),
            "orphan_examples": orph.head(5).round(4).values.tolist(),
            "countries_touched": sorted(tl),
        }
        print("%-30s cells=%6d uncovered=%5d coastal=%5d orphans=%5d touched=%s"
              % (reg, len(d), unc.sum(), coastal, len(orph), ",".join(sorted(tl))), flush=True)
    for iso, c in countries.items():
        rep["countries"][iso] = {"file": c["file"], "level2_present": c["level2_present"],
                                 "level2_units": c["level2_units"], "layers": c["layers"],
                                 "regions_touching": sorted(touched[iso])}
    rep["not_touched"] = sorted(k for k in countries if not touched[k])
    rep["no_level2"] = sorted(k for k, c in countries.items() if not c["level2_present"])
    rep["total_orphans"] = int(sum(r["orphans"] for r in rep["regions"].values()))
    rep["verdict"] = "COMPLETE" if rep["total_orphans"] == 0 else "CHECK ORPHANS"
    tmp = out_json + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    os.replace(tmp, out_json)
    print("not touched: %s" % rep["not_touched"])
    print("no level 2: %s" % rep["no_level2"])
    print("orphans: %d -> %s" % (rep["total_orphans"], rep["verdict"]))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
