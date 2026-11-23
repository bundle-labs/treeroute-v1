"""A synthetic TABLE package for the table-option tests (SPEC_TABLE_MODE.md 6.1). A builder, not a test file.

build_toy_table_package(root, variant="ok") writes a complete table package (dataset.yaml input: table) and its three
lead files under root/<name>: 5 groups (g_a ... g_e) of point sites clustered per group (clusters far apart, so each
group is its own overlap block; variant 'touching' puts two groups' sites together), dates in 12 calendar years
(2000-2011) from a fixed arithmetic rule (no random draw), about 60 rows per group (most sites one visit, 10 sites
2-3 visits), 6 tree features (one NaN on about 10% of rows; two carry a strong group offset, so a row's pool in
feature space fills with its own group first and does not span every group: some trees survive the drop set), 2 context columns (one NaN on 3 train rows of the
earliest years), one string stratum with 3 values, a target in [0, 100] with about 40% zeros, and lead files 0, 183 and
365 (key_feature_end = issue day - 1; lead 365 leaves out about 5% of the rows, train rows of the first years and test
rows only, never a guard-surface row). The marks follow the derived window (test years 2008-2011).

The refusal variants (one per contract check) change one thing each; REFUSAL_VARIANTS maps each to the check id the
refusal names. The package names no real problem (G-NONAMES applies to the engine, and this file keeps to it too).
"""

import datetime as _dt
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

GROUPS = {"g_a": (10.0, 10.0), "g_b": (10.0, 40.0), "g_c": (40.0, 10.0), "g_d": (40.0, 40.0), "g_e": (-30.0, 70.0)}
YEARS = tuple(range(2000, 2012))
TEST_YEARS = (2008, 2009, 2010, 2011)
SITES_PER_GROUP = 50
MULTI_SITES = 2                 # per group: sites with 2-3 visits (10 over the 5 groups)
LEADS = (0, 183, 365)
TREE_COLS = ("f1", "f2", "f3", "f4", "f5", "f6")
CONTEXT_COLS = ("c_season", "c_aux")
STRATUM = "source"
STRATA = ("lab", "field", "remote")
REFUSAL_VARIANTS = {
    "bad_issue": "T-ISSUE", "feature_end_late": "T-FEATEND", "reserved_stratum_name": "T-NAMES",
    "train_in_test": "T-MARK", "test_before_window": "T-MARK", "dup_row_id": "T-ROWID", "dup_unit_date": "T-UNITTIME",
    "unit_two_places": "T-UNIT", "unit_two_groups": "T-UNIT", "extra_column": "T-COLUMNS", "missing_role": "U1",
    "label_out_of_range": "T-RANGE", "inf_feature": "T-FINITE", "sentinel_feature": "T-FINITE",
    "missing_lead_file": "T-FILES", "extra_lead_file": "T-FILES", "lead_row_not_in_nowcast": "T-LEADSET",
    "label_differs_across_leads": "T-LEADSET", "one_site_group": "R14", "empty_group_at_cut": "R19",
    "reach_on_target": "R11", "grid_role_in_table": "U1", "guard_row_absent_at_lead": "H4",
}


def _day(year: int, k: int) -> int:
    """A fixed irregular day in a year (no draw): the k-th visit day of the year."""
    doy = 1 + (k * 37 + year * 11) % 360
    return _dt.date(year, 1, 1).toordinal() + doy - 1


def _rows() -> pd.DataFrame:
    """One row per visit: row id, site, group, lat, lon, target day, label, features at lead 0, stratum."""
    out: List[Dict[str, Any]] = []
    for gi, (g, (la, lo)) in enumerate(sorted(GROUPS.items())):
        for s in range(SITES_PER_GROUP):
            visits = 1 if s >= MULTI_SITES else 2 + (s % 2)
            lat = la + 0.25 * (s % 8) + 0.03 * gi
            lon = lo + 0.25 * (s // 8) + 0.02 * gi
            for v in range(visits):
                k = s * 3 + v
                year = YEARS[(s * 5 + gi * 3 + v * 4) % len(YEARS)]
                day = _day(year, k + gi)
                out.append({"site": "%s_s%02d" % (g, s), "region": g, "lat": lat, "lon": lon, "day": day,
                            "k": k, "gi": gi})
    frame = pd.DataFrame(out).sort_values(["region", "site", "day"], kind="stable").reset_index(drop=True)
    frame["row_id"] = ["r%04d" % i for i in range(len(frame))]
    return frame


def _features(frame: pd.DataFrame, lead: int) -> Dict[str, np.ndarray]:
    """Fixed-formula features at a lead (they move a little with the lead, as features ending earlier would)."""
    n = len(frame)
    i = np.arange(n, dtype=np.float64)
    gi = frame["gi"].to_numpy(dtype=np.float64)
    doy = np.asarray([_dt.date.fromordinal(int(d)).timetuple().tm_yday for d in frame["day"]], dtype=np.float64)
    shift = lead / 365.0
    f = {"f1": np.sin(0.37 * i + gi) + 0.1 * shift, "f2": np.cos(0.11 * i) * (1.0 + 0.2 * gi),
         "f3": ((i * 7) % 13) / 13.0 - shift * 0.05 + 4.0 * gi, "f4": np.sin(2 * np.pi * doy / 365.0) + 0.3 * gi,
         "f5": np.cos(0.05 * i * (1 + gi)) + 4.0 * gi, "f6": ((i * 3) % 17) / 17.0}
    f6 = f["f6"].copy()
    f6[(np.arange(n) % 10) == 3] = np.nan
    f["f6"] = f6
    c = {"c_season": np.cos(2 * np.pi * (doy - lead) / 365.0), "c_aux": 0.5 * gi + ((i * 5) % 7) / 7.0}
    return dict(f, **c)


def _label(frame: pd.DataFrame) -> np.ndarray:
    feats = _features(frame, 0)
    i = np.arange(len(frame))
    y = 50.0 + 18.0 * feats["f1"] - 12.0 * feats["f2"] + 8.0 * feats["c_season"] + 3.0 * np.sin(1.7 * i)
    y = np.clip(y, 0.0, 100.0)
    y[(i * 7) % 5 < 2] = 0.0
    return np.round(y, 6)


def _write_yaml_files(pkg: Path, variant: str) -> None:
    stratum = "year" if variant == "reserved_stratum_name" else STRATUM
    target_window = ("    window: {length: 1, unit: day, align: backward, reach_after_max: {value: 1, unit: day}}\n"
                     if variant == "reach_on_target" else "    window: {length: 1, unit: day, align: backward}\n")
    issue_role = "key_time, calendar_part: date" if variant == "grid_role_in_table" else "key_issue"
    lines = ["columns:",
             "  row_id: {role: key_row}" if variant != "missing_role" else "  row_id: {role: key_unit}",
             "  site: {role: key_unit}" if variant != "missing_role" else "  site: {role: support}",
             "  region: {role: key_group}", "  lat: {role: key_lat}", "  lon: {role: key_lon}",
             "  visit_date: {role: key_time, calendar_part: date}", "  issue_date: {role: %s}" % issue_role,
             "  feature_end: {role: key_feature_end}", "  mark: {role: key_mark}",
             "  y:", "    role: target", "    legal_range: [0, 100]",
             "    legal_range_source: a synthetic percent cover, 0 to 100", "    stamp: event_date"]
    text = "\n".join(lines) + "\n" + target_window
    for c in TREE_COLS:
        text += "  %s: {role: driver, co_measured_with_target: false, co_measured_evidence: Part 1}\n" % c
    for c in CONTEXT_COLS:
        text += "  %s: {role: router_context}\n" % c
    text += "  %s: {role: report_stratum}\n" % stratum
    if variant == "extra_column":
        pass                    # the extra column is in the files, not in the catalog
    (pkg / "catalog.yaml").write_text(text, encoding="utf-8")
    ban = "verdicts:\n  y: {verdict: ban, reason: label, evidence: Part 1}\n"
    if variant == "missing_role":
        ban += "  site: {verdict: keep, reason: a support column, evidence: Part 1}\n"
    for c in TREE_COLS + CONTEXT_COLS:
        ban += "  %s: {verdict: keep, reason: a synthetic driver, evidence: Part 1}\n" % c
    ban += "  %s: {verdict: keep, reason: a report stratum, evidence: Part 1}\n" % stratum
    (pkg / "ban.yaml").write_text(ban, encoding="utf-8")
    (pkg / "split.yaml").write_text("excluded: {}\n", encoding="utf-8")
    (pkg / "exceptions.yaml").write_text("", encoding="utf-8")
    (pkg / "AUDIT_CHECKLIST.md").write_text("# Audit checklist\n\n- [ ] U2 statement signed by: tester\n",
                                            encoding="utf-8")


def lead_frame(base: pd.DataFrame, lead: int, stratum: str = STRATUM) -> pd.DataFrame:
    """The lead file's frame of the base rows (every catalog column, in catalog order)."""
    feats = _features(base, lead)
    day = base["day"].to_numpy(dtype=np.int64)
    as_date = lambda days: pd.to_datetime([_dt.date.fromordinal(int(d)) for d in days]).date  # noqa: E731
    out = pd.DataFrame({"row_id": base["row_id"].to_numpy(dtype=object), "site": base["site"].to_numpy(dtype=object),
                        "region": base["region"].to_numpy(dtype=object),
                        "lat": base["lat"].to_numpy(dtype=np.float64), "lon": base["lon"].to_numpy(dtype=np.float64),
                        "visit_date": as_date(day), "issue_date": as_date(day - lead),
                        "feature_end": as_date(day - lead - 1),
                        "mark": base["mark"].to_numpy(dtype=object), "y": base["y"].to_numpy(dtype=np.float64)})
    for c in TREE_COLS + CONTEXT_COLS:
        out[c] = feats[c].astype(np.float64)
    out[stratum] = base[STRATUM].to_numpy(dtype=object)
    return out


def _write_parquet(frame: pd.DataFrame, path: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    fields = []
    for c in frame.columns:
        if c in ("visit_date", "issue_date", "feature_end"):
            fields.append(pa.field(c, pa.date32()))
        elif frame[c].dtype == object:
            fields.append(pa.field(c, pa.string()))
        else:
            fields.append(pa.field(c, pa.from_numpy_dtype(frame[c].dtype)))
    table = pa.Table.from_pandas(frame, schema=pa.schema(fields), preserve_index=False)
    pq.write_table(table, str(path))


def build_toy_table_package(root: Any, variant: str = "ok", name: str = "toy_table") -> Path:
    """Write the toy table package (module docstring) and return its folder."""
    if variant not in ("ok", "touching") and variant not in REFUSAL_VARIANTS:
        raise ValueError("unknown toy variant %r" % variant)
    root = Path(root)
    pkg = root / name
    (pkg / "data").mkdir(parents=True)
    base = _rows()
    if variant == "touching":
        sel = base["region"] == "g_b"
        base.loc[sel, "lat"] = base.loc[sel, "lat"] - 30.0 + 2.1        # g_b's sites beside g_a's
    if variant == "one_site_group":
        keep = (base["region"] != "g_e") | (base["site"] == "g_e_s05")
        base = base[keep].reset_index(drop=True)
    years = np.asarray([_dt.date.fromordinal(int(d)).year for d in base["day"]], dtype=np.int64)
    if variant == "empty_group_at_cut":
        # g_e holds no row at or before the guard cut (its first years moved into the inner-score window)
        sel = (base["region"] == "g_e").to_numpy() & (years <= 2004)
        base.loc[sel, "day"] = [_dt.date(2006, 1, 1).toordinal() + 3 * i for i in range(int(sel.sum()))]
        years = np.asarray([_dt.date.fromordinal(int(d)).year for d in base["day"]], dtype=np.int64)
    base["mark"] = np.where(np.isin(years, TEST_YEARS), "test", "train").astype(object)
    if variant == "train_in_test":
        base.loc[int(np.flatnonzero(np.isin(years, TEST_YEARS))[0]), "mark"] = "train"
    if variant == "test_before_window":
        base.loc[int(np.flatnonzero(years == 2003)[0]), "mark"] = "test"
    base["y"] = _label(base)
    base[STRATUM] = np.asarray([STRATA[i % 3] for i in range(len(base))], dtype=object)
    stratum = "year" if variant == "reserved_stratum_name" else STRATUM
    frames = {L: lead_frame(base, L, stratum) for L in LEADS}
    # c_aux missing on 3 train rows of the first years (owner ruling G1 leaves them out of the router fits)
    early = np.flatnonzero(years <= 2001)[:3]
    for L in LEADS:
        frames[L].loc[early, "c_aux"] = np.nan
    # lead 365 leaves out about 5% of the rows: train rows of 2000-2003 and test rows, never a guard-surface row
    out365 = np.flatnonzero(((years <= 2003) | np.isin(years, TEST_YEARS)) & (np.arange(len(base)) % 20 == 7))
    if variant == "guard_row_absent_at_lead":
        out365 = np.r_[out365, np.flatnonzero((years >= 2005) & (years <= 2006))[:2]]
    frames[365] = frames[365].drop(index=out365).reset_index(drop=True)
    if variant == "bad_issue":
        frames[183].loc[0, "issue_date"] = (pd.Timestamp(frames[183].loc[0, "issue_date"]) + pd.Timedelta(days=1)).date()
    if variant == "feature_end_late":
        frames[183].loc[1, "feature_end"] = frames[183].loc[1, "issue_date"]
    if variant == "dup_row_id":
        frames[0].loc[1, "row_id"] = frames[0].loc[0, "row_id"]
    if variant == "dup_unit_date":
        frames[0].loc[1, "site"] = frames[0].loc[0, "site"]
        frames[0].loc[1, "visit_date"] = frames[0].loc[0, "visit_date"]
        frames[0].loc[1, "issue_date"] = frames[0].loc[0, "issue_date"]
        frames[0].loc[1, "feature_end"] = frames[0].loc[0, "feature_end"]
        frames[0].loc[1, "lat"], frames[0].loc[1, "lon"] = frames[0].loc[0, "lat"], frames[0].loc[0, "lon"]
    if variant == "unit_two_places":
        frames[0].loc[0, "lat"] = frames[0].loc[0, "lat"] + 0.5
        frames[0].loc[1, "site"] = frames[0].loc[0, "site"]
        frames[0].loc[0, "lat"] = frames[0].loc[1, "lat"] + 0.5
    if variant == "unit_two_groups":
        frames[0].loc[0, "site"] = frames[0].loc[len(frames[0]) - 1, "site"]
    if variant == "extra_column":
        for L in LEADS:
            frames[L]["stray"] = 1.0
    if variant == "label_out_of_range":
        frames[0].loc[0, "y"] = 101.0
    if variant == "inf_feature":
        frames[0].loc[0, "f1"] = np.inf
    if variant == "sentinel_feature":
        frames[0].loc[0, "f2"] = 1e31
    if variant == "lead_row_not_in_nowcast":
        frames[183].loc[0, "row_id"] = "zz_not_in_lead_0"
    if variant == "label_differs_across_leads":
        frames[183].loc[0, "y"] = frames[183].loc[0, "y"] + 1.0 if frames[183].loc[0, "y"] < 99 else 1.0
    for L in LEADS:
        if variant == "missing_lead_file" and L == 365:
            continue
        _write_parquet(frames[L], pkg / "data" / ("lead_%d.parquet" % L))
    if variant == "extra_lead_file":
        _write_parquet(frames[183], pkg / "data" / "lead_90.parquet")
    (pkg / "dataset.yaml").write_text(
        "name: %s\nversion: '0.1.0'\nowner: tester\ndescription: a synthetic table package for the table tests\n"
        "input: table\nstores:\n  target: 'data/lead_{lead}.parquet'\nincludes: []\n" % name, encoding="utf-8")
    _write_yaml_files(pkg, variant)
    return pkg


__all__ = ["build_toy_table_package", "REFUSAL_VARIANTS", "GROUPS", "LEADS", "TEST_YEARS", "lead_frame", "FAKE_LAUNCH",
           "toy_machine", "run_toy", "set_test_labels", "patch_sklearn"]


# ---------------------------------------------------------------------------------------------------
# Run helpers for the table-option tests (a fake machine under the test's folder; the launcher's record faked as
# tests/test_pipeline.py fakes it)
FAKE_LAUNCH = {"test_only": True, "env_pins": {"OMP_NUM_THREADS": "4"},
               "backend": {"sklearn_patched": True, "onedal_threads": 4}}


def toy_machine(base: Any) -> Any:
    from types import SimpleNamespace

    from conftest import make_registry

    base = Path(base)
    protected = base / "shipped_root"
    protected.mkdir(parents=True, exist_ok=True)
    reg = make_registry(base, [protected])
    (base / "temp").mkdir(exist_ok=True)
    return SimpleNamespace(run_root=str(base / "runs"), temp_dir=str(base / "temp"), registry_dir=str(reg))


def run_toy(pkg: Any, base: Any, kind: str = "smoke", machine: Any = None, echo: Any = None) -> Path:
    from treeroute.pipeline.run import run_pipeline

    machine = machine or toy_machine(base)
    return Path(run_pipeline(pkg, Path(base) / "runs", kind, machine=machine,
                             echo=echo if echo is not None else (lambda s: None), launch_record=FAKE_LAUNCH))


def set_test_labels(pkg: Any, value: float) -> None:
    """The leak probe's edit: every test-marked row's label set to ``value`` in every lead file (in place)."""
    import pyarrow.parquet as pq

    for path in sorted((Path(pkg) / "data").glob("lead_*.parquet")):
        frame = pq.read_table(str(path)).to_pandas()
        frame.loc[frame["mark"] == "test", "y"] = float(value)
        _write_parquet(frame, path)


def patch_sklearn() -> Any:
    """Patch sklearn with sklearnex for the test (owner ruling C); returns the undo function (it also puts back the
    environment variables sklearnex sets)."""
    import os

    before = dict(os.environ)
    import sklearnex

    was = sklearnex.sklearn_is_patched()
    if not was:
        sklearnex.patch_sklearn(verbose=False)

    def undo():
        if not was:
            sklearnex.unpatch_sklearn()
        for name in set(os.environ) - set(before):
            del os.environ[name]
        for name, value in before.items():
            if os.environ.get(name) != value:
                os.environ[name] = value
    return undo
