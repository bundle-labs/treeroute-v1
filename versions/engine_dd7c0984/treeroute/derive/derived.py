"""derived.json: the Derived record's helpers, borderline flags, input hashes and the writer.

Every rule returns a Derived: its value, the inputs it read (a JSON-able summary of each, with a SHA-256
per input) and its margin to every threshold it compared against. A value within 20% of a threshold is
flagged 'borderline:<threshold name>' (plan Section 2 preamble; C10). The flag is reported, never a
choice.

JSON form (derived_entry): enums become their value strings, dataclasses become objects of their
fields, tuples become lists, integer mapping keys become their decimal text (JSON keys are strings),
numpy values become plain numbers, and an infinite float becomes the string 'inf' or '-inf' (strict
JSON has no infinity; a legal range may be open above). NaN anywhere is refused: a derived value is
never 'not a number'.

The writer (write_derived_json) writes the file once and never replaces it (runs.atomic.write_json_once)
and returns the SHA-256 of the canonical JSON, which the run compares with the one plan showed (plan 4.1
step 2). The rules themselves write nothing.
"""

import hashlib
import json
import math
from dataclasses import fields, is_dataclass
from enum import Enum
from fractions import Fraction
from numbers import Integral, Real
from typing import Any, Dict, Mapping, Optional, Tuple

import numpy as np

from treeroute import engine_constants as K
from treeroute.errors import RefusedError
from treeroute.runs.atomic import dumps_canonical, write_json_once

from .shapes import Derived

INF_TEXT = "inf"
NEG_INF_TEXT = "-inf"
BORDERLINE_PREFIX = "borderline:"
WRITER_RULE = "derived.json"


class DeriveRefusal(RefusedError):
    """A derive rule refused (R1-R28). Nothing catches it to carry on (fail loudly)."""


# ---------------------------------------------------------------------------------------------------
# JSON form
def jsonable(obj: Any, where: str = "value") -> Any:
    """``obj`` as plain JSON types (see the module docstring). Unknown types and NaN are refused."""
    if obj is None or isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, Enum):
        return jsonable(obj.value, where)
    if isinstance(obj, (Integral, np.integer)):
        return int(obj)
    if isinstance(obj, (Real, np.floating)):
        value = float(obj)
        if math.isnan(value):
            raise DeriveRefusal(WRITER_RULE, "%s is NaN; a derived value or input is never 'not a "
                                "number'" % where, fix="the rule must refuse or record None")
        if math.isinf(value):
            return INF_TEXT if value > 0 else NEG_INF_TEXT
        return value
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: jsonable(getattr(obj, f.name), "%s.%s" % (where, f.name))
                for f in fields(obj)}
    if isinstance(obj, Mapping):
        out: Dict[str, Any] = {}
        for key, value in obj.items():
            text = _key_text(key, where)
            if text in out:
                raise DeriveRefusal(WRITER_RULE, "%s has two keys that both read %r" % (where, text),
                                    fix="keys must stay distinct as text")
            out[text] = jsonable(value, "%s[%s]" % (where, text))
        return out
    if isinstance(obj, np.ndarray):
        return [jsonable(v, where) for v in obj.tolist()]
    if isinstance(obj, (list, tuple)):
        return [jsonable(v, "%s[%d]" % (where, i)) for i, v in enumerate(obj)]
    if isinstance(obj, (set, frozenset)):
        return sorted((jsonable(v, where) for v in obj), key=lambda v: json.dumps(v, sort_keys=True))
    raise DeriveRefusal(WRITER_RULE, "%s has a type derived.json cannot hold: %s"
                        % (where, type(obj).__name__), fix="record a plain summary instead")


def _key_text(key: Any, where: str) -> str:
    if isinstance(key, Enum):
        key = key.value
    if isinstance(key, str):
        return key
    if isinstance(key, (Integral, np.integer)) and not isinstance(key, (bool, np.bool_)):
        return str(int(key))
    raise DeriveRefusal(WRITER_RULE, "%s has a key of type %s; derived.json keys are text or whole "
                        "numbers" % (where, type(key).__name__), fix="use text or integer keys")


def sha256_of_json(obj: Any) -> str:
    """SHA-256 of the canonical JSON of ``obj`` (in its jsonable form)."""
    return hashlib.sha256(dumps_canonical(jsonable(obj)).encode("ascii")).hexdigest()


def sha256_of_array(values: Any) -> str:
    """SHA-256 of an array's dtype, shape and values. Numbers and dates hash their raw bytes; text and
    other objects hash the JSON list of their text, so two arrays hash equal only if they are equal."""
    arr = np.asarray(values)
    h = hashlib.sha256()
    h.update(("%s|%s|" % (arr.dtype.str, arr.shape)).encode("ascii"))
    if arr.dtype.kind in "biufcmM":
        h.update(np.ascontiguousarray(arr).tobytes())
    else:
        h.update(json.dumps([v if isinstance(v, str) else repr(v) for v in arr.ravel().tolist()],
                            ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return h.hexdigest()


def constants_used(*ids: str) -> Dict[str, Any]:
    """{constant id: value} for the engine constants a rule read (recorded in its inputs)."""
    return {cid: K.get(cid) for cid in ids}


# ---------------------------------------------------------------------------------------------------
def _exact(number: Any, what: str) -> Fraction:
    """An exact fraction of a finite number (a float is read as its shortest decimal text)."""
    if isinstance(number, (bool, np.bool_)) or not isinstance(number, (Real, np.number)):
        raise DeriveRefusal("Section 2", "%s must be a number, got %r" % (what, number),
                            fix="pass the number the rule compared")
    value = float(number)
    if not math.isfinite(value):
        raise DeriveRefusal("Section 2", "%s is not finite (%r)" % (what, number),
                            fix="a rule compares finite numbers only")
    if isinstance(number, (Integral, np.integer)):
        return Fraction(int(number))
    return Fraction(repr(value))


# Provenance: plan Section 2 preamble ("A value within 20% of a threshold is flagged 'borderline'");
# D1 (accepted): relative to the threshold, a zero threshold uses the absolute margin only.
def borderline_flags(value: float, thresholds: Mapping[str, float]) -> Tuple[Mapping[str, float], Tuple[str, ...]]:
    """Margin of a derived value to each of its thresholds, and a 'borderline' flag within 20%.

    Rule: Section 2 (all rules). margin = value - threshold (signed). Flag 'borderline:<name>' when
    |value - threshold| <= 0.2 x |threshold| (C10), compared exactly on the numbers' decimal text, so
    a value exactly 20% away is flagged. For a zero threshold the same formula leaves only the
    absolute margin: the flag is then raised only for a value equal to the threshold (D1).
    Returns ({name: margin}, flags) in the order the thresholds are given.
    Refuses: a non-finite value; a non-finite threshold; a threshold name that is not text.
    """
    v = _exact(value, "the compared value")
    share = _exact(K.BORDERLINE_SHARE, "C10.borderline_share")
    margins: Dict[str, float] = {}
    flags = []
    for name, threshold in thresholds.items():
        if not isinstance(name, str) or not name:
            raise DeriveRefusal("Section 2", "threshold names are non-empty text, got %r" % (name,),
                                fix="name each threshold by its constant or rule")
        t = _exact(threshold, "threshold %s" % name)
        margins[name] = float(v - t)
        if abs(v - t) <= share * abs(t):
            flags.append(BORDERLINE_PREFIX + name)
    return margins, tuple(flags)


# ---------------------------------------------------------------------------------------------------
def make_derived(rule_id: str, value: Any, inputs: Mapping[str, Any],
                 array_hashes: Optional[Mapping[str, str]] = None,
                 margins: Optional[Mapping[str, float]] = None,
                 flags: Tuple[str, ...] = ()) -> Derived:
    """Build one Derived. input_hashes holds the SHA-256 of every recorded input (its canonical JSON)
    plus the hashes of the raw arrays the rule read (``array_hashes``, named by the caller).

    Refuses: an array-hash name that repeats an input name; inputs, value or margins that derived.json
    cannot hold (checked here, so a bad value never reaches the writer).
    """
    inputs = dict(inputs)
    hashes: Dict[str, str] = {name: sha256_of_json(item) for name, item in inputs.items()}
    for name, digest in (array_hashes or {}).items():
        if name in hashes:
            raise DeriveRefusal(rule_id, "input hash %r is named twice" % name,
                                fix="name raw-array hashes apart from the recorded inputs")
        hashes[name] = digest
    out = Derived(rule_id=rule_id, value=value, inputs=inputs, input_hashes=hashes,
                  margins=dict(margins or {}), flags=tuple(flags))
    derived_entry(out)          # every part must be writable
    return out


def derived_entry(d: Derived) -> Dict[str, Any]:
    """One Derived in its derived.json form."""
    where = "rule %s" % d.rule_id
    return {"rule_id": d.rule_id,
            "value": jsonable(d.value, where + " value"),
            "inputs": jsonable(d.inputs, where + " inputs"),
            "input_hashes": jsonable(d.input_hashes, where + " input_hashes"),
            "margins": jsonable(d.margins, where + " margins"),
            "flags": jsonable(list(d.flags), where + " flags")}


def derived_document(entries: Mapping[str, Derived]) -> Dict[str, Any]:
    """The derived.json content: {entry name: entry}. An entry's name is its rule id, or its rule id
    followed by ':' and a qualifier when one rule has several entries (one c per cut).

    Refuses: an entry that is not a Derived; a name that does not start with its entry's rule id; no
    entry at all.
    """
    if not entries:
        raise DeriveRefusal(WRITER_RULE, "no derived entry to write", fix="run the rules first")
    out: Dict[str, Any] = {}
    for name, d in entries.items():
        if not isinstance(d, Derived):
            raise DeriveRefusal(WRITER_RULE, "entry %r is a %s, not a Derived"
                                % (name, type(d).__name__), fix="pass the rules' outputs")
        if not isinstance(name, str) or not (name == d.rule_id or name.startswith(d.rule_id + ":")):
            raise DeriveRefusal(WRITER_RULE, "entry %r holds rule %s; an entry is named by its rule id "
                                "(or '<rule id>:<qualifier>')" % (name, d.rule_id),
                                fix="name the entry after its rule")
        out[name] = derived_entry(d)
    return out


def derived_sha256(entries: Mapping[str, Derived]) -> str:
    """SHA-256 of the canonical JSON of the derived.json content (what plan shows and the run checks)."""
    return hashlib.sha256(dumps_canonical(derived_document(entries)).encode("ascii")).hexdigest()


def write_derived_json(path: Any, entries: Mapping[str, Derived]) -> str:
    """Write derived.json once (never replaced; an existing file is refused) and return its
    derived_sha256."""
    document = derived_document(entries)
    write_json_once(path, document)
    return hashlib.sha256(dumps_canonical(document).encode("ascii")).hexdigest()
