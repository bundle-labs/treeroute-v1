"""The last-value rule (owner ruling J2 d, io.lastvalue.fill_last_value) wired into the column reader:
ColumnReader.lagged fills each kept TREE feature's short inner gaps right after the kept columns are
selected and before caching (router context is never filled), so R30's shares count what is still missing;
the record is kept per lag map, adds up per column when the frame is built in column chunks, and enters
the run record.

The synthetic package is test_pipeline's: x1's stored sentinel (-32768, about 0.5% of rows) is masked at
read, which leaves single-month gaps inside x1's record, the rule's own case.
"""

import numpy as np
import pandas as pd
import pytest

from test_pipeline import make_pipeline_package


def _reader(tmp_path, group="grp_c"):
    from treeroute.derive.rules import derive_r01_cadence
    from treeroute.package.load import load_package
    from treeroute.pipeline import data as D

    package = load_package(make_pipeline_package(tmp_path / "pk"))
    hook = D.load_hook(package.root, D.FEATURE_SCRIPT)
    pkg = D.augment_package(package, D.feature_outputs(hook))
    spec = D.package_spec(pkg)
    frame = D.read_target(pkg, spec, None, D.list_target(pkg), (group,), None, lambda s: None)
    t = D.target_table(frame, spec)
    cad = derive_r01_cadence(t.unit_ids, t.time_columns, spec.time_facts).value
    return D.ColumnReader(pkg, spec, frame, cad, hook, lambda s: None), cad


def _lags(cad):
    from treeroute.derive.shapes import Cadence, CadenceKind, StepUnit
    from treeroute.timing.shapes import Lag

    year = Cadence(kind=CadenceKind.REGULAR, length=1, unit=StepUnit.YEAR)
    return {"x1": Lag("x1", 1, cad, None), "g1": Lag("g1", 0, cad, None), "x2": Lag("x2", 1, year, None),
            "s1": Lag("s1", 0, cad, None), "ctx:m": Lag("ctx:m", 0, cad, None)}


def _expected_fill(values, codes, steps, max_steps):
    """An independent per-unit loop of the rule: a NaN between two values of the same unit whose gap is at
    most max_steps steps takes the earlier value."""
    out = values.copy()
    filled = 0
    for u in np.unique(codes):
        idx = np.flatnonzero(codes == u)
        idx = idx[np.argsort(steps[idx], kind="stable")]
        have = [i for i in idx if np.isfinite(values[i])]
        for a, b in zip(have[:-1], have[1:]):
            gap = int(steps[b] - steps[a] - 1)
            if 0 < gap <= max_steps:
                inner = [i for i in idx if steps[a] < steps[i] < steps[b]]
                for i in inner:
                    out[i] = values[a]
                    filled += 1
    return out, filled


def test_lagged_fills_short_inner_gaps_of_tree_features_from_the_earlier_value(tmp_path):
    from treeroute.io.lastvalue import last_value_max_steps
    from treeroute.io.apply import apply_lags

    reader, cad = _reader(tmp_path)
    lags = _lags(cad)
    raw_x1 = apply_lags(reader.raw[["x1"]], reader.codes, reader.steps, {"x1": lags["x1"]}, cad)["x1"]
    raw_x1 = raw_x1.to_numpy(dtype=np.float64)
    assert np.isnan(raw_x1).sum() > 0                                  # the masked sentinels, lagged
    lagged = reader.lagged(lags)
    want, n_filled = _expected_fill(raw_x1, reader.codes, reader.steps, last_value_max_steps(cad))
    got = lagged["x1"].to_numpy(dtype=np.float64)
    assert np.array_equal(np.isnan(got), np.isnan(want)) and np.allclose(got[~np.isnan(got)], want[~np.isnan(want)])
    assert n_filled > 0
    record = reader.last_value_record(lags)
    assert record.filled["x1"] == n_filled
    assert record.columns == tuple(c for c in reader.kept if c in reader.spec.tree_features)
    assert "ctx:m" not in record.columns                               # router context is never filled
    assert record.missing["x1"] == int(np.isnan(raw_x1).sum())
    assert record.left_to_r30("x1") == int(np.isnan(got).sum())
    assert reader.lagged(lags) is lagged                               # filled once, then served from the cache


def test_r30_counts_what_is_still_missing_after_the_fill(tmp_path):
    from types import SimpleNamespace

    reader, cad = _reader(tmp_path)
    lags = _lags(cad)
    lagged = reader.lagged(lags)
    donor = SimpleNamespace(unit_ids=reader.units, times=reader.steps, row_key_hash="h", unit_scope="picked")
    shares = reader.measure(donor, lags, (2010,))
    assert shares.donor_training_missing_share["x1"] == float(np.isnan(lagged["x1"].to_numpy()).mean())
    record = reader.last_value_record(lags)
    assert shares.donor_training_missing_share["x1"] == record.left_to_r30("x1") / float(len(reader.units))


def test_the_record_of_a_frame_built_in_column_chunks_equals_the_whole_frames(tmp_path):
    from treeroute.pipeline import data as D

    reader, cad = _reader(tmp_path)
    lags = _lags(cad)
    whole = reader.lagged(lags)
    full = reader.last_value_record(lags)
    kept = reader.kept
    reader._lagged.clear()
    reader._last_value.clear()
    parts = []
    try:
        for i in range(0, len(kept), 2):
            reader.kept = tuple(kept[i:i + 2])
            reader._lagged.clear()
            parts.append(D.ColumnReader.lagged(reader, lags))
    finally:
        reader.kept = kept
    pd.testing.assert_frame_equal(pd.concat(parts, axis=1)[list(kept)], whole)
    assert reader.last_value_record(lags).as_dict() == full.as_dict()


def test_the_record_is_refused_before_the_lagged_frame_exists(tmp_path):
    from treeroute.pipeline import data as D

    reader, cad = _reader(tmp_path)
    with pytest.raises(D.DataRefusal, match="last-value record"):
        reader.last_value_record(_lags(cad))
