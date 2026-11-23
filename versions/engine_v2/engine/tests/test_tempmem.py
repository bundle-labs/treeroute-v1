"""Windows-safe temp memmap: refs dropped and gc run before a LOUD delete; nothing swallowed."""

import gc
import os

import numpy as np
import pytest

from treeroute.errors import TempMatrixError
from treeroute.runs import tempmem
from treeroute.runs.preflight import find_orphan_temp_files
from treeroute.runs.tempmem import temp_matrix_path, temp_memmap


def test_normal_lifecycle_deletes_the_file(tmp_path):
    with temp_memmap(tmp_path, "tbl", (6, 3), "float32") as tm:
        assert tm.path.exists() and tm.path.parent == tmp_path
        tm.write_rows(0, np.ones((2, 3), dtype=np.float32))
        tm.write_rows(2, np.full((4, 3), 2.0, dtype=np.float32))
        block = tm.read_rows(1, 3)
        path = tm.path
    assert not path.exists()
    assert tm.closed
    assert block.tolist() == [[1.0, 1.0, 1.0], [2.0, 2.0, 2.0]]  # read_rows returned a copy
    with pytest.raises(TempMatrixError):
        tm.array


def test_alias_dropped_inside_the_block_is_fine(tmp_path):
    with temp_memmap(tmp_path, "alias_ok", (4, 2), "float32") as tm:
        a = tm.array
        a[0] = 5.0
        view = a[1:3]
        del a, view  # the documented rule: drop every alias before the block ends
        path = tm.path
    assert not path.exists()


def test_leaked_alias_fails_loudly_and_leaves_the_file(tmp_path):
    keep = []
    with pytest.raises(TempMatrixError) as info:
        with temp_memmap(tmp_path, "leak", (4, 2), "float32") as tm:
            keep.append(tm.array[1:3])  # a container still holds a view of the memmap
            path = tm.path
    assert "still referenced" in str(info.value)
    assert path.exists()
    # the leftover is visible as a temp file of a LIVE process (not an orphan yet)
    assert find_orphan_temp_files(tmp_path) == []
    keep.clear()
    gc.collect()
    os.remove(str(path))  # the test cleans up its own file


def test_body_exception_propagates_and_file_is_deleted(tmp_path):
    with pytest.raises(RuntimeError):
        with temp_memmap(tmp_path, "boom", (3, 3), "float32") as tm:
            path = tm.path
            raise RuntimeError("body failed")
    assert not path.exists()


def test_delete_failure_is_not_swallowed(tmp_path, monkeypatch):
    def refuse(path):
        raise PermissionError(32, "The process cannot access the file", path)

    with pytest.raises(TempMatrixError) as info:
        with temp_memmap(tmp_path, "nodelete", (2, 2), "float32") as tm:
            path = tm.path
            monkeypatch.setattr(tempmem.os, "remove", refuse)
    monkeypatch.undo()
    assert "could not delete" in str(info.value)
    assert path.exists()
    os.remove(str(path))


def test_existing_file_is_never_overwritten(tmp_path):
    path = temp_matrix_path(tmp_path, "taken")
    path.write_bytes(b"someone's data")
    with pytest.raises(TempMatrixError) as info:
        with temp_memmap(tmp_path, "taken", (2, 2), "float32"):
            pass
    assert "refusing to overwrite" in str(info.value)
    assert path.read_bytes() == b"someone's data"


def test_row_block_writes_are_bounds_checked(tmp_path):
    with temp_memmap(tmp_path, "bounds", (3, 2), "float32") as tm:
        with pytest.raises(IndexError):
            tm.write_rows(2, np.zeros((2, 2), dtype=np.float32))


def test_bad_tag_and_missing_dir_are_refused(tmp_path):
    with pytest.raises(ValueError):
        temp_matrix_path(tmp_path, "../x")
    with pytest.raises(TempMatrixError):
        with temp_memmap(tmp_path / "missing", "t", (1, 1), "float32"):
            pass
