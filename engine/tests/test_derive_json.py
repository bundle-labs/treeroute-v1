"""derived.json: the JSON form of Derived values, input hashes and the write-once writer."""

import hashlib
import json
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pytest

from treeroute import derive as D
from treeroute.errors import RefusedError
from treeroute.runs.atomic import AtomicWriteError, dumps_canonical


class Colour(Enum):
    RED = "red"


@dataclass(frozen=True)
class Pair:
    a: int
    b: Colour


def test_jsonable_converts_engine_values():
    value = {1: (Pair(1, Colour.RED), np.int64(3), np.float32(0.5)), "k": [float("inf"), -float("inf")],
             Colour.RED: {np.int32(2): np.bool_(True)}, "arr": np.array([1, 2])}
    assert D.jsonable(value) == {"1": [{"a": 1, "b": "red"}, 3, 0.5], "k": ["inf", "-inf"],
                                 "red": {"2": True}, "arr": [1, 2]}


@pytest.mark.parametrize("bad", [float("nan"), {"x": np.float64("nan")}, object(), {(1, 2): 3},
                                 {1: "a", "1": "b"}, {True: 1}])
def test_jsonable_refuses_nan_unknown_types_and_bad_keys(bad):
    with pytest.raises(RefusedError):
        D.jsonable(bad)


def test_array_hash_sees_dtype_shape_and_values():
    a = np.arange(5, dtype=np.int64)
    assert D.sha256_of_array(a) == D.sha256_of_array(a.copy())
    assert D.sha256_of_array(a) != D.sha256_of_array(a.astype(np.int32))
    assert D.sha256_of_array(a) != D.sha256_of_array(a[::-1])
    s = np.array(["u1", "u2"], dtype=object)
    assert D.sha256_of_array(s) == D.sha256_of_array(np.array(["u1", "u2"]).astype(object))
    assert D.sha256_of_array(s) != D.sha256_of_array(np.array(["u1", "u3"], dtype=object))


def test_make_derived_hashes_every_input_and_the_raw_arrays():
    d = D.make_derived("R6", 2018, {"test_years": [2019, 2020]}, {"raw": "f" * 64},
                       {"m": 1.0}, ("flag",))
    assert d.input_hashes["test_years"] == D.sha256_of_json([2019, 2020])
    assert d.input_hashes["raw"] == "f" * 64 and d.margins == {"m": 1.0} and d.flags == ("flag",)
    with pytest.raises(RefusedError):
        D.make_derived("R6", 1, {"x": 1}, {"x": "0" * 64})               # hash name repeats an input
    with pytest.raises(RefusedError):
        D.make_derived("R6", float("nan"), {})                            # unwritable value


def test_document_names_entries_by_rule():
    r5 = D.derive_r05_test_window(2003, 2023)
    r6 = D.derive_r06_train_end(r5.value.test_years)
    doc = D.derived_document({"R5": r5, "R6": r6})
    assert doc["R5"]["value"] == {"test_years": [2020, 2021, 2022, 2023], "inner_score_years": 3,
                                  "ladder_steps": []}
    assert set(doc["R6"]) == {"rule_id", "value", "inputs", "input_hashes", "margins", "flags"}
    c = D.make_derived("R23", 0.5, {"lead": 3})
    assert D.derived_document({"R23:lead=3": c})["R23:lead=3"]["value"] == 0.5
    for bad in [{}, {"R7": r6}, {"R6x": r6}, {"R6": "not a derived"}]:
        with pytest.raises(RefusedError):
            D.derived_document(bad)


def test_writer_writes_once_and_returns_the_canonical_hash(tmp_path):
    entries = {"R28": D.derive_r28_clip_bounds((0.0, float("inf"))),
               "R6": D.derive_r06_train_end((2020, 2021, 2022, 2023))}
    path = tmp_path / "derived.json"
    digest = D.write_derived_json(path, entries)
    assert digest == D.derived_sha256(entries)
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["R28"]["value"] == [0.0, "inf"] and on_disk["R6"]["value"] == 2019
    assert hashlib.sha256(dumps_canonical(on_disk).encode("ascii")).hexdigest() == digest
    with pytest.raises(AtomicWriteError):
        D.write_derived_json(path, entries)                                # never replaced
