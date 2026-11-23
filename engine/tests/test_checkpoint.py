"""Crash-safe checkpoints inside the long steps (owner ruling P; treeroute/runs/checkpoint.py). The lean set
(owner, 2026-10-13: few, small tests; the byte-identity and kill-and-resume gates run on the real PM2.5 smoke):

  - a changed input file time or a changed package fingerprint gives another key: nothing is reused, and the
    log says which part changed;
  - a truncated record is detected (its SHA-256), reported, moved aside and recomputed: the census resumed
    past it equals the census read whole.
"""

import os

import numpy as np

from treeroute.runs import checkpoint as CK


def _registry(tmp_path):
    from conftest import make_registry
    from treeroute.runs.registry import Registry

    protected = tmp_path / "shipped_root"
    protected.mkdir(exist_ok=True)
    return Registry(make_registry(tmp_path, [protected]))


def _step(tmp_path, reg, msgs, name, parts):
    """The step as a NEW process opens it (a process loads only the records on disk when it opened the step)."""
    return CK.Checkpoints(tmp_path / "runs", "pkg", reg, msgs.append).step(name, parts)


def test_a_changed_mtime_or_a_changed_package_invalidates(tmp_path):
    msgs = []
    reg = _registry(tmp_path)
    f = tmp_path / "in.parquet"
    f.write_bytes(b"12345")

    def parts(fingerprint):
        return {"package_fingerprint": fingerprint, "target_files": CK.file_stats([f])}

    first = _step(tmp_path, reg, msgs, "census", parts("a" * 64))
    first.save_object("rec", {"n": 1})
    same = _step(tmp_path, reg, msgs, "census", parts("a" * 64))
    assert same.key == first.key and same.load_object("rec")[1] == {"n": 1}
    st = f.stat()
    os.utime(str(f), ns=(st.st_atime_ns, st.st_mtime_ns + 10 ** 9))
    touched = _step(tmp_path, reg, msgs, "census", parts("a" * 64))
    assert touched.key != first.key and touched.load_object("rec") is None
    said = [m for m in msgs if "NOT reused" in m][-1]
    assert "in.parquet" in said and "mtime_ns" in said
    other_pkg = _step(tmp_path, reg, msgs, "census", parts("b" * 64))
    assert other_pkg.key not in (first.key, touched.key) and other_pkg.load_object("rec") is None
    assert "package_fingerprint changed" in [m for m in msgs if "NOT reused" in m][-1]


def _table(n_units=37, years=(2001, 2002, 2003)):
    from types import SimpleNamespace

    rng = np.random.default_rng(5)               # test data only
    units, groups, yrs, months, y = [], [], [], [], []
    for u in range(n_units):
        g = "g%d" % (u % 3)
        for yr in years:
            for m in range(1, 13):
                if rng.random() < 0.05:
                    continue                      # an absent row
                units.append("%s_u%d" % (g, u))
                groups.append(g)
                yrs.append(yr)
                months.append(m)
                y.append(float("nan") if rng.random() < 0.1 else float(rng.normal()))
    order = np.lexsort((np.asarray(months), np.asarray(yrs), np.asarray(groups)))
    return SimpleNamespace(unit_ids=np.asarray(units, dtype=object)[order],
                           group_ids=np.asarray(groups, dtype=object)[order],
                           time_columns={"yr": np.asarray(yrs, dtype=np.int64)[order],
                                         "mo": np.asarray(months, dtype=np.int64)[order]},
                           y=np.asarray(y, dtype=np.float64)[order])


def _census_state(c):
    return {"names": list(c.unit_names), "groups": list(c.unit_group), "rows": c.unit_rows.tolist(),
            "coords": c.coords.tolist(), "exist": c.exist_bits.tobytes(), "valid": c.valid_bits.tobytes(),
            "hist": {k: v.tobytes() for k, v in c.hist.items()}, "mv": dict(c.mask_valid), "mr": dict(c.mask_rows),
            "mf": dict(c.mask_first_year), "n": c.rows, "r1": dict(c.r1_hashes), "spans": list(c.file_coords),
            "line": c.line}


def test_a_truncated_record_is_detected_reported_and_recomputed(tmp_path):
    from treeroute.derive import census as CEN

    table = _table()
    facts = {"yr": "year", "mo": "month"}
    whole = CEN.scan_target(CEN.TableSource(table, 97), facts)
    msgs = []
    reg = _registry(tmp_path)
    CEN.scan_target(CEN.TableSource(table, 97), facts, checkpoint=_step(tmp_path, reg, msgs, "census", {"t": 1}),
                    echo=msgs.append)
    step = _step(tmp_path, reg, msgs, "census", {"t": 1})
    n = len(step.records("chunk_"))
    assert n > 4                                                   # one chunk a file at this size
    k = n // 2
    victim = step.folder / ("chunk_%06d%s" % (k, CK.DATA_SUFFIX))
    victim.write_bytes(victim.read_bytes()[: victim.stat().st_size // 2])
    resumed = CEN.scan_target(CEN.TableSource(table, 97), facts, checkpoint=step, echo=msgs.append)
    assert any("CHECKPOINT CORRUPT" in m and "chunk_%06d" % k in m for m in msgs)
    assert any("census resumed at file %d of %d" % (k, n) in m for m in msgs)
    assert _census_state(resumed) == _census_state(whole)
    assert len(step.records("chunk_")) == n                         # the chunks from the corrupt one written again
    assert list(step.folder.glob("chunk_%06d%s%s*" % (k, CK.DATA_SUFFIX, CK.CORRUPT_MARK)))
