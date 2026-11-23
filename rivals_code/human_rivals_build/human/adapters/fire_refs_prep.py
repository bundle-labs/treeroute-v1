"""Fire refs label store (owner prep): the 2018 TRAINING labels, keyed on cell_id, through the package's own reader.

SPEC_HUMAN_PARTB.txt 3.9 and 1.4 (ATTENTION B4; the Part 618 precedent of NDVI). Owner command F3:
    py -3.9 -B -m rivals_human.cli prep --run <fire run> --rival geff_era5 --stage train
then `manifest --product fire_refs_label_store` and the EARLY byte check T-F18 (a realdata test outside adapters/).

Why: with R17 start offset 1 the export's training rows stop at Nov 2018 (step 24227), yet the engine's nowcast
persistence reads the label AT the lead-0 fit cut (Dec 2018, step 24228). refs.store_labels (refs.py:245-298) reads
those labels from the registry's refs_label_store (files "{group}_labels_{year}.parquet" with cell_id / year / month /
burned_frac) and byte-checks every overlapping label against the held slim labels itself. The fire target store
D:/fire/target/{group}_{year}.parquet is keyed on lat/lon (float32) with n_valid, NOT on cell_id, so refs cannot read it
directly: this prep writes a cell_id-keyed copy, made by the PACKAGE'S OWN reader (engine/datasets/fire/ingest/
target_reader.py read_target_file: its 5-decimal lat/lon key map, its n_valid > 0 validity rule and its complete
census), so the labels are exactly the ones the engine read.

What it writes: ctx.work_dir()/<out_dir>/<group>_labels_<year>.parquet per group of the bank units and per year of
options.refs_store.years ([2018]): columns cell_id (str), year (int64), month (int64), burned_frac (float64, NaN kept),
the group's bank units only (all of them, scored or not), sorted by cell_id then month. Deterministic bytes; a file that
already exists must hold the same bytes (else refuse: move it aside first), so a re-run never changes a hashed store.

Rules (3.9): a year after the last training year ((lead-0 fit cut - 1) // 12 = 2018) refuses: never a test-year label.
The reader is imported by file path with sys.dont_write_bytecode set (no __pycache__ in the engine), and its
static_table_path() must be the same file as the sha-checked product fire_static_cells part-0.parquet. NO label
self-check here and no slim access at all (review test R02 scans every adapters/*.py; the byte check is refs' own and
T-F18's, made early by the owner before any init).

The AdapterCtx calls used here: ctx.run (.cuts[0]["fit_cut"], .derived), ctx.units(), ctx.open_product(pid, name),
ctx.product_files(pid), ctx.work_dir(), ctx.write_bytes(path, data), ctx.log(message); ctx.package (the registry, read
only to compare its refs_label_store with these options when the ctx carries it).
"""
# Provenance: SPEC_HUMAN_PARTB.txt 1.4, 2.1 (refs_label_store), 2.2 (options.refs_store), 3.9; engine/datasets/fire/
# ingest/target_reader.py:151-200 (read_target_file), :88-93 (static_table_path); rivals_human/refs.py:245-298
# (store_labels: file_pattern, unit/year/month/label columns, dtype); adapters/ndvi_kraft_prep.py (prep style).

import hashlib
import io
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import numpy as np
import pandas as pd

PREP_FORMAT = "human-fire-refs-store/1"
MONTHS_PER_YEAR = 12
STORE_COLUMNS = ("cell_id", "year", "month", "burned_frac")       # the reader's own names (target_reader.py:52-57)
STATIC_FILE = "part-0.parquet"
READER_MODULE = "_fire_package_target_reader"


class FireRefsPrepRefusal(RuntimeError):
    """A fire refs-store prep rule refused (fail loud)."""


def _refuse(message: str, fix: Optional[str] = None):
    raise FireRefsPrepRefusal(message + ("" if not fix else "  FIX: " + fix))


def prep_options(rival: Mapping[str, Any]) -> Dict[str, Any]:
    """options.refs_store of the rival that hosts the prep (registry/fire.yaml geff_era5)."""
    rs = dict((rival.get("options") or {}).get("refs_store") or {})
    for k in ("target_product", "static_product", "years", "out_dir", "file_pattern", "target_file_pattern",
              "target_reader"):
        if k not in rs:
            _refuse("rival %s: options.refs_store lacks %r" % (rival.get("id"), k))
    rs["years"] = sorted(int(y) for y in rs["years"])
    if not rs["years"] or len(set(rs["years"])) != len(rs["years"]):
        _refuse("rival %s: options.refs_store.years must be a non-empty list of distinct years" % rival.get("id"))
    for k in ("target_product", "static_product"):
        if rs[k] not in (rival.get("products") or []):
            _refuse("rival %s: refs_store %s %r is not in its products list" % (rival.get("id"), k, rs[k]))
    if Path(str(rs["out_dir"])).is_absolute() or ".." in Path(str(rs["out_dir"])).parts:
        _refuse("rival %s: refs_store.out_dir must be a folder name under the rival's work folder" % rival.get("id"))
    return rs


def last_training_year(run: Any) -> int:
    """(lead-0 fit cut - 1) // 12: the year of the newest label step the lead-0 refit may hold (2018 for fire)."""
    d = getattr(run, "derived", None) or {}
    spy = ((d.get("R2") or {}).get("value") or {}).get("steps_per_year") if isinstance(d, Mapping) else None
    if spy is not None and int(spy) != MONTHS_PER_YEAR:
        _refuse("the run has %s steps per year; the store's year x month rule needs a monthly run" % spy)
    return (int(run.cuts[0]["fit_cut"]) - 1) // MONTHS_PER_YEAR


def load_target_reader(path: Any):
    """The package's own target reader, imported by file path (no __pycache__ written into the engine)."""
    import importlib.util

    p = Path(str(path))
    if not p.is_file():
        _refuse("the package target reader %s does not exist" % p)
    before = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location(READER_MODULE, str(p))
        if spec is None or spec.loader is None:
            _refuse("cannot import the package target reader %s" % p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = before
    for name in ("read_target_file", "static_table_path"):
        if not callable(getattr(mod, name, None)):
            _refuse("the package target reader %s has no %s()" % (p, name))
    return mod


def _same_file(a: Path, b: Path) -> bool:
    import os
    try:
        return os.path.samefile(str(a), str(b))
    except OSError:
        return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))


def _check_registry_store(ctx: Any, rs: Mapping[str, Any]) -> None:
    """The package's refs_label_store must read what this prep writes (file pattern, columns, float64)."""
    reg = getattr(ctx, "package", None)
    store = reg.get("refs_label_store") if isinstance(reg, Mapping) else None
    if not isinstance(store, Mapping):
        return
    want = {"file_pattern": rs["file_pattern"], "unit_column": STORE_COLUMNS[0], "year_column": STORE_COLUMNS[1],
            "month_column": STORE_COLUMNS[2], "label_column": STORE_COLUMNS[3], "dtype": "float64"}
    bad = {k: (store.get(k), v) for k, v in want.items() if str(store.get(k)) != str(v)}
    if bad:
        _refuse("the registry's refs_label_store does not read what the prep writes: %s (registry, prep)" % bad)


def parquet_bytes(frame: pd.DataFrame) -> bytes:
    """Deterministic parquet bytes (no pandas index, fixed types and compression)."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    schema = pa.schema([(STORE_COLUMNS[0], pa.string()), (STORE_COLUMNS[1], pa.int64()), (STORE_COLUMNS[2], pa.int64()),
                        (STORE_COLUMNS[3], pa.float64())])
    tab = pa.Table.from_pandas(frame[list(STORE_COLUMNS)], schema=schema, preserve_index=False)
    buf = io.BytesIO()
    pq.write_table(tab, buf, compression="zstd")
    return buf.getvalue()


def group_store(frame: pd.DataFrame, group: str, year: int, bank_units: List[str], what: str) -> pd.DataFrame:
    """The reader's rows of one group-year cut to the group's bank units: cell_id / year / month / burned_frac."""
    missing = [c for c in STORE_COLUMNS if c not in frame.columns]
    if missing:
        _refuse("%s: the package reader returned no column %s (it returned %s)" % (what, missing, list(frame.columns)))
    t = pd.DataFrame({STORE_COLUMNS[0]: frame[STORE_COLUMNS[0]].astype(str).to_numpy(),
                      STORE_COLUMNS[1]: frame[STORE_COLUMNS[1]].to_numpy(np.int64),
                      STORE_COLUMNS[2]: frame[STORE_COLUMNS[2]].to_numpy(np.int64),
                      STORE_COLUMNS[3]: frame[STORE_COLUMNS[3]].to_numpy(np.float64)})
    if (t[STORE_COLUMNS[1]] != int(year)).any():
        _refuse("%s: the reader returned rows of other years" % what)
    if ((t[STORE_COLUMNS[2]] < 1) | (t[STORE_COLUMNS[2]] > MONTHS_PER_YEAR)).any():
        _refuse("%s: months outside 1..12" % what)
    t = t[t[STORE_COLUMNS[0]].isin(set(bank_units))]
    if t.duplicated(subset=[STORE_COLUMNS[0], STORE_COLUMNS[2]]).any():
        _refuse("%s: the reader returned a (cell, month) twice" % what)
    absent = sorted(set(bank_units) - set(t[STORE_COLUMNS[0]]))
    if absent:
        _refuse("%s: %d bank unit(s) of group %s are not in the reader's census (first %s)"
                % (what, len(absent), group, absent[:3]))
    return t.sort_values([STORE_COLUMNS[0], STORE_COLUMNS[2]], kind="mergesort").reset_index(drop=True)


def run_prep(ctx: Any, rival: Mapping[str, Any]) -> Dict[str, Any]:
    """Owner command F3 (prep --rival geff_era5 --stage train): write the cell_id-keyed refs label store."""
    rs = prep_options(rival)
    last = last_training_year(ctx.run)
    late = [y for y in rs["years"] if y > last]
    if late:
        _refuse("refs_store years %s lie after the last training year %d (lead-0 fit cut %d): never a test-year label"
                % (late, last, int(ctx.run.cuts[0]["fit_cut"])))
    _check_registry_store(ctx, rs)
    reader = load_target_reader(rs["target_reader"])
    static = Path(str(ctx.open_product(str(rs["static_product"]), STATIC_FILE)))          # sha-checked
    own = Path(str(reader.static_table_path()))
    if not own.is_file() or not _same_file(own, static):
        _refuse("the package reader's static table %s is not the product %s file %s"
                % (own, rs["static_product"], static), fix="the reader must key on the same static table")
    u = ctx.units()
    units = pd.DataFrame({"unit": u["unit"].astype(str).to_numpy(), "group": u["group"].astype(str).to_numpy()})
    if units["unit"].duplicated().any():
        _refuse("the slim units table names a unit twice")
    listed = set(str(n) for n in ctx.product_files(str(rs["target_product"])))
    out = Path(str(ctx.work_dir())) / str(rs["out_dir"])
    written: Dict[str, Any] = {}
    tot = {"rows": 0, "finite": 0, "dec_rows": 0, "dec_finite": 0, "files": 0, "unchanged": 0}
    for group in sorted(set(units["group"])):
        bank = sorted(units.loc[units["group"] == group, "unit"].tolist())
        for year in rs["years"]:
            name = str(rs["target_file_pattern"]).format(group=group, year=year)
            if name not in listed:
                _refuse("product %s lists no %s" % (rs["target_product"], name))
            path = ctx.open_product(str(rs["target_product"]), name)                      # sha-checked
            what = "%s %s" % (rs["target_product"], name)
            frame = reader.read_target_file(path, {"group": group, "year": int(year)})
            t = group_store(frame, group, int(year), bank, what)
            data = parquet_bytes(t)
            target = out / str(rs["file_pattern"]).format(group=group, year=year)
            same = False
            if target.exists():
                with open(str(target), "rb") as fh:
                    old = fh.read()
                if old != data:
                    _refuse("refs store file %s exists with other bytes (written from other inputs?)" % target,
                            fix="move it aside (never delete), then rerun the prep; re-hash the product afterwards")
                same = True
            else:
                ctx.write_bytes(target, data)
            y = t[STORE_COLUMNS[3]].to_numpy(np.float64)
            dec = t[STORE_COLUMNS[2]].to_numpy(np.int64) == MONTHS_PER_YEAR
            rec = {"file": target.name, "rows": int(len(t)), "units": int(len(bank)),
                   "finite": int(np.isfinite(y).sum()), "dec_rows": int(dec.sum()),
                   "dec_finite": int((dec & np.isfinite(y)).sum()),
                   "sha256": hashlib.sha256(data).hexdigest(), "unchanged": same}
            written.setdefault(group, {})[str(year)] = rec
            for k in ("rows", "finite", "dec_rows", "dec_finite"):
                tot[k] += rec[k]
            tot["files"] += 1
            tot["unchanged"] += int(same)
            ctx.log("refs store %s: %d rows (%d bank units), %d finite labels; Dec %d: %d rows, %d finite%s"
                    % (target.name, rec["rows"], rec["units"], rec["finite"], int(year), rec["dec_rows"],
                       rec["dec_finite"], " (already written, same bytes)" if same else ""))
    ctx.log("refs store: %d files, %d rows, %d finite labels, Dec rows %d (%d finite) in %s; next: manifest --product "
            "fire_refs_label_store, then the early byte check T-F18 (no label self-check here)"
            % (tot["files"], tot["rows"], tot["finite"], tot["dec_rows"], tot["dec_finite"], out))
    return {"format": PREP_FORMAT, "years": list(rs["years"]), "last_training_year": last, "out_dir": str(out),
            "reader": str(Path(str(rs["target_reader"]))), "static_table": str(static), "groups": written,
            "totals": tot}


__all__ = ["PREP_FORMAT", "STORE_COLUMNS", "FireRefsPrepRefusal", "prep_options", "last_training_year",
           "load_target_reader", "group_store", "parquet_bytes", "run_prep"]
