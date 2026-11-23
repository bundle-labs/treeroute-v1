"""Kraft LSTM (optional NDVI rival) input store: per unit and month, the climate drivers and soil statics.

SPEC_HUMAN.txt section 5 (Kraft) and section 8 O15 (owner command, heavy: a panel pass over D:/monthly_panel,
1-2 h; NEVER run by a builder). Opt-in only: nothing here runs unless the registry lists kraft_lstm and the owner
runs the prep.

What it writes: one parquet per panel region, columns unit, step (year x 12 + month, the engine's step index),
the registry's `drivers` and `statics` (float32), sorted by (unit, step); one row per (unit, month) found in the
panel. The folder is then hashed by the tool's `manifest` command (SPEC_HUMAN 1.8) and read by ndvi_kraft.py
through ctx.open_product (sha checked). Land cover is never read (banned proxy, R-NDV:61). The target column
(V11_mean_ndvi) is never read either: the column list is checked against `forbidden_columns`.

Reads: the panel files <region>_monthly_<year>.parquet of the product `panel_product` (D:/monthly_panel, hashed by
the tool's `manifest` command, SPEC_HUMAN 1.8 "monthly panel if Kraft runs"), each opened through ctx.open_product
(sha checked), column-pruned and filtered to the units of that region; the unit -> region map from the engine's static cell table, opened as a product (registry option
`unit_centres`: product, file, id, region; sha checked by ctx.open_product).
Writes: ctx.write_bytes(path, parquet bytes) under the folder the caller gives (default ctx.work_dir()/"store";
builder A's write path, engine registry check), then a progress record <store>_progress/<region>.json (sha256 of
the region file, rows, units, the inputs it was made from). RESUME (review B issue 12): a region whose file AND
record exist, with the same inputs and the recorded sha, is skipped; any mismatch (or a file without its record: a
pass killed mid-region) refuses, never overwrites. The progress folder sits beside the store, outside the product.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

PREP_FORMAT = "human-kraft-store/1"
PANEL_PATTERN = "{region}_monthly_{year:04d}.parquet"
MONTHS_PER_YEAR = 12


class KraftPrepRefusal(RuntimeError):
    """A Kraft prep rule refused (fail loud)."""


def _refuse(message: str, fix: Optional[str] = None):
    raise KraftPrepRefusal(message + ("" if not fix else "  FIX: " + fix))


def prep_options(rival: Mapping[str, Any]) -> Dict[str, Any]:
    opt = dict(rival.get("options") or {})
    for k in ("drivers", "statics", "panel_product", "unit_centres", "years", "forbidden_columns"):
        if k not in opt:
            _refuse("rival %s: registry options lack %r" % (rival.get("id"), k))
    cols = list(opt["drivers"]) + list(opt["statics"])
    bad = sorted(set(cols) & set(opt["forbidden_columns"]))
    if bad:
        _refuse("rival %s reads forbidden column(s) %s (target or banned proxy)" % (rival.get("id"), bad))
    if len(set(cols)) != len(cols):
        _refuse("rival %s names a driver or static twice" % rival.get("id"))
    y0, y1 = int(opt["years"][0]), int(opt["years"][1])
    if y1 < y0:
        _refuse("rival %s: years %s are not (first, last)" % (rival.get("id"), opt["years"]))
    opt["years"] = (y0, y1)
    return opt


def unit_regions(static_path: Any, unit_centres: Mapping[str, Any], units: Sequence[str]) -> pd.DataFrame:
    """unit -> panel region from the engine's static table (every unit must match exactly one cell)."""
    import pyarrow.dataset as ds

    path = Path(str(static_path))
    idc, regc = str(unit_centres["id"]), str(unit_centres.get("region", "region"))
    want = sorted(set(str(u) for u in units))
    tab = ds.dataset(str(path), format="parquet").to_table(columns=[idc, regc],
                                                          filter=ds.field(idc).isin(want)).to_pandas()
    if tab[idc].duplicated().any():
        _refuse("static table %s names a cell twice" % path)
    missing = sorted(set(want) - set(tab[idc].astype(str)))
    if missing:
        _refuse("%d unit(s) match no %s in %s (first %s)" % (len(missing), idc, path, missing[:3]))
    return tab.rename(columns={idc: "unit", regc: "region"})[["unit", "region"]].sort_values("unit").reset_index(drop=True)


def region_frame(open_file: Any, region: str, units: Sequence[str], years: Sequence[int],
                 drivers: Sequence[str], statics: Sequence[str]) -> pd.DataFrame:
    """One region's rows for the given units: unit, step, drivers, statics (float32). open_file(name) -> the path of
    a panel file, or None when the panel has no such file (that year is skipped; the window rule then marks those
    months missing)."""
    import pyarrow.dataset as ds

    if not callable(open_file):
        folder = Path(str(open_file))
        open_file = lambda name: (folder / name) if (folder / name).is_file() else None   # noqa: E731
    cols = ["cell_id", "year", "month"] + list(drivers) + list(statics)
    want = sorted(set(str(u) for u in units))
    parts = []
    for y in range(int(years[0]), int(years[1]) + 1):
        p = open_file(PANEL_PATTERN.format(region=region, year=y))
        if p is None:
            continue
        d = ds.dataset(str(p), format="parquet")
        missing = [c for c in cols if c not in d.schema.names]
        if missing:
            _refuse("panel file %s lacks the columns %s" % (p, missing))
        parts.append(d.to_table(columns=cols, filter=ds.field("cell_id").isin(want)).to_pandas())
    if not parts:
        return pd.DataFrame(columns=["unit", "step"] + list(drivers) + list(statics))
    t = pd.concat(parts, ignore_index=True)
    out = pd.DataFrame({"unit": t["cell_id"].astype(str),
                        "step": t["year"].astype(np.int64) * MONTHS_PER_YEAR + t["month"].astype(np.int64)})
    for c in list(drivers) + list(statics):
        out[c] = t[c].astype(np.float32)
    if out.duplicated(subset=["unit", "step"]).any():
        _refuse("panel region %s names a (cell, month) twice" % region)
    return out.sort_values(["unit", "step"], kind="mergesort").reset_index(drop=True)


def parquet_bytes(frame: pd.DataFrame) -> bytes:
    """Deterministic parquet bytes (no pandas index, fixed compression)."""
    import io

    import pyarrow as pa
    import pyarrow.parquet as pq

    buf = io.BytesIO()
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), buf, compression="zstd")
    return buf.getvalue()


def run_prep(ctx: Any, rival: Mapping[str, Any], out_dir: Any = None) -> Dict[str, Any]:
    """Owner command (SPEC_HUMAN 8 O15): write the store for every unit of units.parquet (the bank units).
    ctx: .units(), .open_product(pid, name), .work_dir(), .write_bytes(path, data), .log(message)."""
    opt = prep_options(rival)
    out = Path(str(out_dir)) if out_dir is not None else Path(str(ctx.work_dir())) / "store"
    u = ctx.units() if callable(ctx.units) else ctx.units
    units = u["unit"].astype(str).tolist()
    uc = opt["unit_centres"]
    reg = unit_regions(ctx.open_product(str(uc["product"]), str(uc["file"])), uc, units)
    panel = str(opt["panel_product"])
    listed = set(str(n) for n in ctx.product_files(panel))

    def open_file(name: str):
        return ctx.open_product(panel, name) if name in listed else None

    prog = out.parent / (out.name + PROGRESS_SUFFIX)
    written: Dict[str, Any] = {}
    skipped = 0
    for region, g in reg.groupby("region", sort=True):
        path = out / ("%s.parquet" % region)
        rp = prog / ("%s.json" % region)
        want = region_input_record(opt, str(region), g["unit"].tolist(), listed)
        if path.exists() or rp.exists():
            done = _read_progress(rp)
            if done is None or not path.exists():
                _refuse("Kraft store %s: the region file and its progress record %s do not both exist (a pass killed "
                        "mid-region?)" % (path, rp), fix="move the region file aside, then rerun the prep (resume)")
            if done.get("inputs") != want:
                _refuse("Kraft store %s was written from other inputs (options, units or panel files differ)" % path,
                        fix="move the store and its progress folder aside and run the prep again")
            if _sha_file(path) != done.get("sha256"):
                _refuse("Kraft store file %s changed after it was written (sha differs from %s)" % (path, rp),
                        fix="move it and its progress record aside, then rerun the prep")
            written[str(region)] = {"rows": done["rows"], "units": done["units"], "resumed": True}
            skipped += 1
            continue
        f = region_frame(open_file, str(region), g["unit"].tolist(), opt["years"], opt["drivers"],
                         opt["statics"])
        ctx.write_bytes(path, parquet_bytes(f))
        rec = {"format": PREP_FORMAT, "region": str(region), "rows": int(len(f)),
               "units": int(f["unit"].nunique()) if len(f) else 0, "sha256": _sha_file(path), "inputs": want}
        ctx.write_bytes(rp, (json.dumps(rec, sort_keys=True, indent=1) + "\n").encode("utf-8"))
        written[str(region)] = {"rows": rec["rows"], "units": rec["units"]}
        ctx.log("Kraft store %s: %d rows, %d units" % (region, len(f), written[str(region)]["units"]))
    if skipped:
        ctx.log("Kraft store: %d region(s) already written with the same inputs and sha (resumed, skipped)" % skipped)
    return {"format": PREP_FORMAT, "regions": written, "drivers": list(opt["drivers"]),
            "statics": list(opt["statics"]), "years": list(opt["years"]), "resumed_regions": skipped}


PROGRESS_SUFFIX = "_progress"


def _sha_file(path: Any) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for block in iter(lambda: fh.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def _read_progress(rp: Path) -> Optional[Dict[str, Any]]:
    if not rp.exists():
        return None
    try:
        rec = json.loads(rp.read_text(encoding="utf-8"))
    except ValueError:
        _refuse("the Kraft progress record %s is not JSON" % rp, fix="move it and its region file aside, then rerun")
    if rec.get("format") != PREP_FORMAT:
        _refuse("the Kraft progress record %s is not a %s record" % (rp, PREP_FORMAT))
    return rec


def region_input_record(opt: Mapping[str, Any], region: str, units: Sequence[str], listed: Any) -> Dict[str, Any]:
    """What a region file is made from (resume key): drivers, statics, years, the region's sorted units and the panel
    file names of that region the product lists (the panel product's manifest pins each file's sha)."""
    names = sorted(PANEL_PATTERN.format(region=region, year=y) for y in range(int(opt["years"][0]),
                                                                              int(opt["years"][1]) + 1)
                   if PANEL_PATTERN.format(region=region, year=y) in listed)
    return {"drivers": list(opt["drivers"]), "statics": list(opt["statics"]), "years": list(opt["years"]),
            "units": sorted(str(u) for u in units), "panel_files": names}


__all__ = ["PREP_FORMAT", "PANEL_PATTERN", "KraftPrepRefusal", "prep_options", "unit_regions", "region_frame",
           "parquet_bytes", "run_prep"]
