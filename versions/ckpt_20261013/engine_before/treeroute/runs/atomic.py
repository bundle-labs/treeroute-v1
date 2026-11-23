"""Atomic JSON writes (temp file, fsync, rename) and canonical JSON for hashing.

Two write modes:
  write_json_once  the file must not exist; it is written once and never replaced (manifest,
                   derived.json, DONE markers, adoption.json). An existing file is refused.
  replace_json     atomically replaces the file (status.json heartbeat only).

An interrupted write leaves at most a ``<name>.tmp-<pid>-<start ms>-<n>`` file beside the target;
the target is either absent or complete, never truncated. The temp name carries the process start
time and a per-process counter, so it can never collide with a temp file left by a dead process
whose pid was reused. Non-finite floats are refused (strict JSON): a caller that means "no value"
converts it to None itself.

Windows sharing: a rename over a file fails with PermissionError while any other process holds
that file open (a reader such as ``treeroute status``, an indexer, an antivirus scan; opening with
delete sharing does not help, measured on this machine). The rename is retried ``RENAME_ATTEMPTS``
times, ``RENAME_WAIT_S`` apart (about 1 s in all, far longer than a reader needs to read a small
JSON file), then fails loudly naming the file. These waits are plumbing: they cannot change any
number.
"""

import itertools
import json
import os
import time

from treeroute.errors import TreerouteError

RENAME_ATTEMPTS = 20
RENAME_WAIT_S = 0.05

_TEMP_COUNTER = itertools.count(1)
_IDENTITY = {}


class AtomicWriteError(TreerouteError):
    """An atomic write was refused or failed."""


def to_jsonable(obj):
    """Convert common engine values to plain JSON types. Unknown types raise TypeError."""
    if obj is None or isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, int):
        return int(obj)
    if isinstance(obj, float):
        return float(obj)
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings, got %r" % (key,))
            out[key] = to_jsonable(value)
        return out
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted(to_jsonable(v) for v in obj)
    if isinstance(obj, os.PathLike):
        return os.fspath(obj)
    # numpy scalars and 0-d arrays expose .item(); checked by duck type so numpy is not imported
    item = getattr(obj, "item", None)
    if callable(item) and getattr(obj, "shape", None) == ():
        return to_jsonable(item())
    tolist = getattr(obj, "tolist", None)
    if callable(tolist):
        return to_jsonable(tolist())
    raise TypeError("cannot convert %s to JSON" % type(obj).__name__)


def dumps(obj, indent=1):
    """Readable strict JSON (sorted keys, NaN refused)."""
    return json.dumps(to_jsonable(obj), indent=indent, sort_keys=True, allow_nan=False,
                      ensure_ascii=False)


def dumps_canonical(obj):
    """Canonical strict JSON for hashing: sorted keys, no whitespace, ASCII only, NaN refused."""
    return json.dumps(to_jsonable(obj), sort_keys=True, separators=(",", ":"), allow_nan=False,
                      ensure_ascii=True)


def _process_tag():
    """'<pid>-<start ms>' of this process (cached per pid, so a forked child gets its own)."""
    pid = os.getpid()
    if _IDENTITY.get("pid") != pid:
        from treeroute.runs import proc

        _, created = proc.own_identity()
        _IDENTITY["pid"] = pid
        _IDENTITY["tag"] = "%d-%s" % (pid, created)
    return _IDENTITY["tag"]


def temp_name(path):
    """The temp file name for one write of ``path`` (unique per process and per write)."""
    return "%s.tmp-%s-%d" % (os.fspath(path), _process_tag(), next(_TEMP_COUNTER))


def _write_temp(path, text):
    tmp = temp_name(path)
    # 'x' refuses to clobber any existing file, even though the name cannot repeat
    with open(tmp, "x", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    return tmp


def _retry_sharing(action, what, path):
    """Run ``action``; on PermissionError retry, then fail loudly naming ``path``."""
    last = None
    for attempt in range(RENAME_ATTEMPTS):
        try:
            return action()
        except PermissionError as exc:
            last = exc
            if attempt + 1 < RENAME_ATTEMPTS:
                time.sleep(RENAME_WAIT_S)
    raise AtomicWriteError(
        "%s %s failed %d times over %.1f s: another process holds the file open without delete "
        "sharing, or the folder is not writable (%s). Close whatever reads it and run again "
        "(a resume continues from the last finished phase)."
        % (what, path, RENAME_ATTEMPTS, RENAME_ATTEMPTS * RENAME_WAIT_S, last)) from last


def _remove_own_temp(tmp):
    if os.path.exists(tmp):
        _retry_sharing(lambda: os.remove(tmp), "removing the temp file", tmp)


def write_text_once(path, text):
    """Write ``text`` to a NEW file atomically. Refuses if ``path`` exists (never overwrites)."""
    path = os.fspath(path)
    if os.path.lexists(path):
        raise AtomicWriteError("refusing to overwrite %s (written once)" % path)
    tmp = _write_temp(path, text)

    def _publish():
        if os.name == "nt":
            os.rename(tmp, path)  # on Windows rename fails if the target exists: atomic write-once
        else:
            os.link(tmp, path)  # fails if the target exists
            os.remove(tmp)

    try:
        _retry_sharing(_publish, "publishing the write-once file", path)
    except FileExistsError as exc:
        _remove_own_temp(tmp)
        raise AtomicWriteError("refusing to overwrite %s (appeared during the write)" % path) from exc
    except BaseException:
        _remove_own_temp(tmp)
        raise


def replace_text(path, text):
    """Atomically replace ``path`` with ``text`` (creates it if absent)."""
    path = os.fspath(path)
    tmp = _write_temp(path, text)
    try:
        _retry_sharing(lambda: os.replace(tmp, path), "replacing", path)
    except BaseException:
        _remove_own_temp(tmp)
        raise


def write_json_once(path, obj):
    """Serialise first (so a bad value never leaves a partial file), then write once atomically."""
    write_text_once(path, dumps(obj) + "\n")


def replace_json(path, obj):
    replace_text(path, dumps(obj) + "\n")


def _parse(fh, path):
    try:
        return json.load(fh)
    except json.JSONDecodeError as exc:
        raise AtomicWriteError("unreadable JSON in %s (%s)" % (path, exc)) from exc


def read_json(path):
    """Read a JSON file; an unreadable file stops with its path named."""
    path = os.fspath(path)
    with open(path, encoding="utf-8") as fh:
        return _parse(fh, path)
