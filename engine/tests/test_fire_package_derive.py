"""derive_all on the DRAFT fire package, on the real stores (READ-ONLY): the heavy check of the fire package
build (2026-09-29). Tests may name problems, regions and drives.

It runs the pipeline's own read and derive steps (treeroute.pipeline.data: the package's target reader hook,
the column reader with the panel and the feature script; then derive_all twice, as treeroute.pipeline.run does:
once on every label, once with the labels before Y0 withheld) and checks the derived settings the plan names for
fire (expected_derived.json): the monthly cadence and season key, Y0 2003 and Y_end 2022, the test window
2019-22, train end 2018, the inner windows, the per-unit router, 40 groups each trained and tested, 100 bank and
50 scored units per group, the history block (6 columns from t-2: start offset 1, ruling R-D b), the same-month
cloud lag 1 (Q3 a) and the ruled index lags (R-A a, R-B, R-C a), and the links.

THE PICK RUNS OVER ALL UNITS (ruling C). Each group keeps UNITS_PER_GROUP (120) units, an evenly spaced stride
(split.stride_pick, the smoke's own pick), applied file by file, over ALL its units that have a valid label, as a
headline run's R18 stride would. The earlier version of this check picked only units with a sidecar row, which
hid what a full-unit run meets: only 7.6% of stride units have one, and 0 in great_plains and mongolian_steppe.
It no longer has to: the draft keeps no column of a pick-only store (tests/test_fire_package.py, the coverage
departure), so F2 (R3's joined rows) never waits on a sidecar row and nothing is 0-filled. This check asserts
that directly: the column reader reads no pick-only store, and every driver store it reads holds a row for at
least 99% of the target rows (the missing shares of the kept columns' stores).

ONE DEPARTURE from a headline derive, forced by the machine: the full census (925,737 units x 252 months =
233 million rows, plus about 100 driver columns per row) does not fit in memory; the pipeline's own preflight
refuses such a run ("a streaming vault and derive" is an open owner item, treeroute/pipeline/run.py). So only the
unit lists are a subset (bank units are then a stride over these). The windows, the router kind, the unit counts,
the history block, the lags and the links do not depend on which 120 units a group keeps unless a group had
fewer than 100.

The summary (every derived value checked, R8 lags, R30 flags, the store shares) is printed and written BEFORE the
last assertions, so a failure still leaves it. Skipped unless FIRE_DRAFT_DERIVE_CHECK=1 is set. It reads the 840
target files twice and 840 panel files: about 15 minutes alone and 3 to 4 GB of RAM at most. Check that no other
heavy job runs first, and pass a basetemp of its own (tests/_pytest_tmp is shared by every pytest session and a
new session clears it; that stopped the run of 2026-09-29 at its last line):
    set FIRE_DRAFT_DERIVE_CHECK=1 & py -3.9 -m pytest tests/test_fire_package_derive.py -s -q --basetemp=D:/treeroute/fire_package/pytest_tmp
"""

import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from conftest import ENGINE_DIR

DRAFT_DIR = ENGINE_DIR / "datasets" / "fire_draft"
EXPECTED = ENGINE_DIR / "datasets" / "fire" / "expected_derived.json"
UNITS_PER_GROUP = 120
MIN_PRESENT_SHARE = 0.99

pytestmark = pytest.mark.skipif(os.environ.get("FIRE_DRAFT_DERIVE_CHECK") != "1",
                                reason="heavy real-data check: set FIRE_DRAFT_DERIVE_CHECK=1 to run it")


def _v(x):
    return getattr(x, "value", x)


# the stores that hold only the shipped 1,000-cell pick per group: the fire package's D: drivers sidecar and the old
# draft's two data/ copies (moved aside 2026-10-06 when the draft was refreshed from the installed package)
PICK_ONLY_STORES = ("D:/fire/drivers/joined/{group}.parquet", "data/fire_history/{group}.parquet",
                    "data/fire_drivers/{group}.parquet")
PICK_ONLY_CATALOG = "../_stores/fire_drivers_schema_catalog.yaml"


def test_derive_all_runs_on_fire_draft(tmp_path):
    from treeroute import split as SP
    from treeroute import timing
    from treeroute.derive import derive_all
    from treeroute.derive.rules import derive_r01_cadence
    from treeroute.io.steps import step_index
    from treeroute.package.load import load_package
    from treeroute.pipeline import data as D
    from treeroute.pipeline.draft import draft_status

    if not Path("D:/fire/target").is_dir() or not (DRAFT_DIR / "data" / "static" / "part-0.parquet").is_file():
        pytest.skip("D:/fire/target or fire_draft's data is not on this machine")
    log = []
    t0 = time.time()

    def echo(msg):
        log.append("[%6.1fs] %s" % (time.time() - t0, msg))
        print(log[-1], flush=True)

    package = load_package(DRAFT_DIR)
    assert draft_status(package).is_draft
    target_hook = D.load_hook(package.root, D.TARGET_READER)
    feature_hook = D.load_hook(package.root, D.FEATURE_SCRIPT)
    outputs = D.feature_outputs(feature_hook)
    pkg = D.augment_package(package, outputs)
    spec = D.package_spec(pkg)
    echo("kept: %d tree features, context %s" % (len(spec.tree_features), list(spec.context)))
    # UPDATED 2026-10-06 (agent C1): the draft is the installed fire package (datasets/_tools/refresh_drafts.py); its
    # pick-only columns are the drivers sidecar's, none kept by the installed ban list
    partial = set(package.stores[PICK_ONLY_CATALOG].columns) if PICK_ONLY_CATALOG in package.stores else set()
    assert not set(partial) & (set(spec.tree_features) | set(spec.context))
    listing = D.list_target(pkg)
    groups = SP.groups_under_loro(SP.loro_split_sets(pkg.split), D.listed_groups(listing))
    assert len(groups) == 40

    # the unit pick, per group: a stride over ALL its units with a valid label (the smoke's pick), found in a
    # first pass over the group's files; the engine's read_target then reads through a hook that keeps only the
    # picked units' rows of each file (a whole group's census is never held: yakutia_larch alone is 21 million
    # rows)
    files_of = {}
    gi = listing.key_names.index(D.GROUP_PLACEHOLDER)
    for key, path in listing.files:
        files_of.setdefault(key[gi], []).append((key, path))
    picked = {}
    for g in groups:
        valid = set()
        for key, path in files_of[g]:
            part = target_hook.read_target_file(path, dict(zip(listing.key_names, key)))
            y = part[spec.target_col].to_numpy(dtype=np.float64)
            valid.update(pd.unique(part[spec.unit_col].to_numpy()[np.isfinite(y)]).tolist())
        picked[g] = frozenset(SP.stride_pick(tuple(sorted(valid)), UNITS_PER_GROUP))
    echo("unit pick: %d units per group (stride over all units with a valid label)" % UNITS_PER_GROUP)

    class PickedUnits(object):
        """The package's target reader, keeping the picked units' rows of each file."""

        @staticmethod
        def read_target_file(path, key):
            part = target_hook.read_target_file(path, key)
            return part[part[spec.unit_col].isin(picked[key["group"]])].reset_index(drop=True)

    frame = D.read_target(pkg, spec, PickedUnits(), listing, groups, None, echo)
    target = D.target_table(frame, spec)
    cadence = derive_r01_cadence(target.unit_ids, target.time_columns, spec.time_facts).value
    reader = D.ColumnReader(pkg, spec, frame, cadence, feature_hook, echo)
    echo("column reader built")
    shares = {s.template: float(np.mean(s.present)) for s in reader.stores}
    first = dict(derive_all(pkg, target, reader))
    y0 = int(first["R4"].value)
    y0_first = int(timing.year_last_step(y0 - 1, cadence)) + 1
    steps = step_index(target.time_columns, spec.time_facts, cadence)
    before = steps < y0_first
    y_model = np.where(before, np.nan, target.y)
    model_target = SimpleNamespace(unit_ids=target.unit_ids, group_ids=target.group_ids,
                                   time_columns=target.time_columns, y=y_model)
    derived = dict(derive_all(pkg, model_target, reader))
    echo("derive_all: %d entries (second pass, labels before %d withheld: %d rows)"
         % (len(derived), y0, int(before.sum())))

    exp = json.loads(EXPECTED.read_text(encoding="utf-8"))
    cad = derived["R1"].value
    w = derived["R7"].value
    lists = derived["R18:units"].value
    hist = derived["R17"].value
    links = [_v(x) for x in derived["R22"].value]
    r8 = {str(k): int(v.steps) for k, v in sorted(derived["R8"].value.items())}
    summary = {
        "units_per_group_read": UNITS_PER_GROUP, "target_rows": int(len(frame)),
        "cadence": [_v(cad.kind), cad.length, _v(cad.unit)], "y0": y0, "y_end": int(derived["R3"].value),
        "test_years": list(w.test_years), "train_end": int(derived["R6"].value),
        "inner_fit": list(w.inner_fit), "inner_score": list(w.inner_score),
        "router": _v(derived["R12"].value), "groups": len(derived["R18:groups"].value),
        "bank": sorted({len(v) for v in lists.bank.values()}),
        "scored": sorted({len(v) for v in lists.scored.values()}),
        "history_columns": list(hist.columns), "history_start_offset_steps": int(hist.start_offset_steps),
        "links": links, "R8_lags": r8, "R30_flags": list(derived["R30"].flags),
        "driver_store_present_share": shares, "entries": sorted(derived),
        "seconds": round(time.time() - t0, 1)}
    print("SUMMARY %s" % json.dumps(summary, default=str), flush=True)
    # tests/_pytest_tmp is shared by every pytest session on the machine and a new session clears it, so a
    # suite started while this check runs can remove tmp_path under it (2026-09-29): recreate it
    out = tmp_path / "fire_draft_derive_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")

    # the missing shares of the kept columns' stores: no pick-only store is read, every store read is (almost)
    # complete on the target rows, and no R30 flag names a pick-only column
    assert not set(shares) & set(PICK_ONLY_STORES), shares
    assert all(v >= MIN_PRESENT_SHARE for v in shares.values()), shares
    assert not {f.split(":")[-1] for f in derived["R30"].flags} & set(partial)
    # the derived settings
    assert (_v(cad.kind), cad.length, _v(cad.unit)) == ("regular", 1, "month")
    assert derived["R2"].value.steps_per_year == 12
    ew = exp["R3_R7_windows"]
    assert int(derived["R4"].value) == ew["y0"] == 2003
    assert int(derived["R3"].value) == ew["y_end"] == 2022
    assert list(w.test_years) == ew["test_years"] == [2019, 2020, 2021, 2022]
    assert int(derived["R6"].value) == ew["train_end"] == 2018
    assert tuple(w.inner_fit) == tuple(ew["inner_fit"]) and list(w.inner_score) == ew["inner_score"]
    assert _v(derived["R12"].value) == exp["R12_router_kind"]["value"] == "per_unit"
    assert len(derived["R18:groups"].value) == 40
    assert {len(v) for v in lists.bank.values()} == {exp["R18_units_per_group"]["bank"]} == {100}
    assert {len(v) for v in lists.scored.values()} == {exp["R18_units_per_group"]["scored"]} == {50}
    eh = exp["R17_history"]
    assert len(hist.columns) == eh["n_columns"] == 6
    assert int(hist.start_offset_steps) == eh["start_offset_steps"] == 1            # ruling R-D (b): from t-2
    el = exp["R8_feature_lags"]
    assert r8["cloud_frequency_pct"] == el["cloud_frequency_pct_steps"] == 1        # co-measured, Q3 a
    ruled = {c: s for c, s in el["index_lags_steps"].items() if c in r8}
    assert ruled, "no ruled index column is kept"
    assert {c: r8[c] for c in ruled} == ruled
    assert links == exp["R22_links"]["value"] == ["identity", "log_c", "arcsine"]
