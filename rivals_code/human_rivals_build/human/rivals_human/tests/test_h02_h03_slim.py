"""T-H02 slim copy and T-H03 slim reader (SPEC_HUMAN.txt 1.3) on the grid toy's common export.

T-H02: every copied column equals the export byte for byte; the slim manifest's sha chain holds (each slim file's
sha256, the source export's content sha, the run fingerprint, the common harness sha); a registry naming an extra
column the export lacks refuses; an export with a stray file refuses; an export made under an accepted engine
difference refuses without its seal; the slim cut-rule check equals the harness's (H:778-812) on the toy and on edits.
T-H03: SlimLead.read_set equals ExportLead.read_set for every train set, guard-side substitution included.
"""

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from rivals_human.tests import hooks as HK
from rivals_human.tests import toy_products as TP


def _parts(d: Path, part: str):
    return sorted((Path(d) / part).glob("*.parquet"))


# ------------------------------------------------------------------------------------------ T-H02
def test_h02_copied_columns_equal_the_export_byte_for_byte(grid_human, grid_slim):
    for L, sdir in grid_slim.items():
        edir = grid_human.exports[L]
        for part in ("train", "guardside", "test"):
            sfiles = _parts(sdir, part)
            assert [p.name for p in sfiles] == [p.name for p in _parts(edir, part)], (L, part)
            for sp in sfiles:
                s = HK.read_parquet(sp)
                e = HK.read_parquet(edir / part / sp.name, list(s.columns))
                pd.testing.assert_frame_equal(s, e, check_exact=True)
                if part == "test":
                    assert "y" not in s.columns
                if part == "train":
                    for c in ("unit", "group", "time", "issue", "lead", "y", "r_refit", "nfit__identity"):
                        assert c in s.columns, (sp, c)
                    for c in TP.GRID_EXTRAS:
                        assert c in s.columns, "the registry's slim_extra_columns %s were not copied" % c
                    hist = ["x__" + h for h in grid_human.toy.derived()["R17"]["value"]["columns"]]
                    assert all(h in s.columns for h in hist)


def test_h02_slim_manifest_sha_chain(grid_human, grid_slim):
    LY, H = HK.common_modules(grid_human.config)
    run = grid_human.h_run()
    for L, sdir in grid_slim.items():
        m = HK.slim_manifest(sdir)
        assert m["format"] == "human-slim/1" and int(m["lead"]) == L
        assert m["run"]["fingerprint"] == run.fingerprint
        assert m["common_harness_sha256"] == HK.COMMON_SHA
        em = HK.read_json(grid_human.exports[L] / "export_manifest.json")
        assert m["source_export_content_sha256"] == H.export_content_sha(em)
        assert m["source_export_manifest_sha256"] == HK.sha256_file(grid_human.exports[L] / "export_manifest.json")
        for f in m["files"]:
            assert HK.sha256_file(sdir / f["path"]) == f["sha256"], f["path"]
            src = next(e for e in em["files"] if e["path"] == f["source_path"])
            assert f["source_sha256"] == src["sha256"]
        assert HK.sha256_file(sdir / m["units"]["path"]) == m["units"]["sha256"]


def test_h02_a_named_extra_column_missing_from_the_export_refuses(grid_human, grid_slim):
    from rivals_human.tests import toy_products as TP
    v = HK.variant_config(grid_human, "missing_extra", TP.grid_registry(grid_human.package, "missing_extra"))
    HK.refuses(("x__not_in_the_export", "holds no column"), HK.slim, v, 0, None, v.config)


def _copy_export_lead(h, lead: int, name: str) -> Path:
    src = h.exports[lead]
    dest = h.base / name / h.package / h.run.name / src.name
    shutil.copytree(str(src), str(dest))
    return dest


def test_h02_an_export_with_a_stray_file_refuses(grid_human, grid_slim):
    d = _copy_export_lead(grid_human, 0, "_export_stray")
    first = _parts(d, "train")[0]
    shutil.copyfile(str(first), str(d / "train" / "zz_stray.parquet"))
    HK.refuses(("not listed", "differ from the manifest"), HK.slim, grid_human, 0, d)


def test_h02_an_accepted_engine_difference_without_its_seal_refuses(grid_human, grid_slim):
    d = _copy_export_lead(grid_human, 0, "_export_seal")
    mp = d / "export_manifest.json"
    m = HK.read_json(mp)
    m.setdefault("engine", {})["accepted_difference"] = {"ruling": "Z1", "run_id": "toy", "ruling_source": "test"}
    HK.move_aside(mp, grid_human.base / "_moved_by_tests")
    mp.write_text(json.dumps(m, indent=1), encoding="utf-8")
    HK.refuses(("ACCEPTED_ALL_LEADS", "seal", "accepted", "identity"), HK.slim, grid_human, 0, d)


def test_h02_slim_cut_rules_equal_the_harness_rules(grid_human, grid_slim):
    """slim.check_rows (the slim reader's re-implementation) and ExportLead._check_rows (H:778-812) agree on the toy
    export's own keys (both pass) and on edited keys (both refuse)."""
    S = HK.tool("slim")
    check_rows = HK.need(S, "check_rows", "A3")
    LY, H = HK.common_modules(grid_human.config)
    run = grid_human.h_run()
    for L in grid_human.leads:
        ex = H.ExportLead(grid_human.exports[L], L, run)
        sets = ("refit", "tune", "inner") if L == 0 else ("refit", "guardfit", "guard")
        for s in sets:
            k, _, _, _ = ex.read_set(s)
            check_rows(run, L, s, k, "toy")
            ex._check_rows(s, k, "toy")
            bad = k.copy()
            if s == "refit":
                bad.loc[0, "time"] = run.cuts[L]["fit_cut"] + 1
                bad.loc[0, "issue"] = bad.loc[0, "time"] - L
            elif s in ("tune", "guardfit"):
                bad.loc[0, "time"] = run.cuts[L]["guard_cut"] + 1
                bad.loc[0, "issue"] = bad.loc[0, "time"] - L
            else:
                bad.loc[0, "time"] = run.cuts[0]["guard_cut"]
                bad.loc[0, "issue"] = bad.loc[0, "time"] - L
            HK.refuses(("cut", "break"), check_rows, run, L, s, bad, "toy")
            HK.refuses(("cut", "break"), ex._check_rows, s, bad, "toy")
            off = k.copy()
            off.loc[0, "issue"] = off.loc[0, "issue"] - 1
            HK.refuses("issue", check_rows, run, L, s, off, "toy")
            HK.refuses("issue", ex._check_rows, s, off, "toy")


# ------------------------------------------------------------------------------------------ T-H03
@pytest.mark.parametrize("lead", [0, 6])
def test_h03_slim_reader_equals_the_export_reader(grid_human, grid_slim, lead):
    LY, H = HK.common_modules(grid_human.config)
    run = grid_human.h_run()
    ex = H.ExportLead(grid_human.exports[lead], lead, run)
    sl = HK.slim_lead(grid_human, grid_slim[lead])
    sets = ("refit", "tune", "inner") if lead == 0 else ("refit", "guardfit", "guard")
    for s in sets:
        ek, ey, eX, en = ex.read_set(s)
        sk, sy, sn, shist, sext = HK.read_set(sl, s)
        for c in ("unit", "group"):
            assert ek[c].astype(str).tolist() == sk[c].astype(str).tolist(), (s, c)
        for c in ("time", "issue", "lead"):
            assert np.array_equal(ek[c].to_numpy(np.int64), sk[c].to_numpy(np.int64)), (s, c)
        assert np.asarray(ey, np.float64).tobytes() == np.asarray(sy, np.float64).tobytes(), s
        for l in run.links:
            assert np.asarray(en[l], np.float64).tobytes() == np.asarray(sn[l], np.float64).tobytes(), (s, l)
        for col in shist.columns:
            j = ex.features.index(col)
            assert eX[:, j].tobytes() == shist[col].to_numpy(np.float32).tobytes(), (s, col)


def test_h03_test_set_needs_a_lock(grid_human, grid_slim):
    sl = HK.slim_lead(grid_human, grid_slim[0])
    HK.refuses(("lock", "token"), sl.read_set, "test")
