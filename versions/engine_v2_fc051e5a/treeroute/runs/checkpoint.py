"""Crash-safe checkpoints inside the long steps (owner ruling P, section P of the owner rulings file).

WHY. A run saves its progress at phase ends (runs/resume.py), and a restart always derives again, because the
run fingerprint hashes derived.json. On the largest packages the derive alone is the census pass and R30's
per-test-year count, many hours, and a stop (a RAM or disk refusal, a crash, Ctrl+C, a power cut) threw all
of it away. A checkpoint saves the work INSIDE a long step, so a stop loses at most the unit in progress.
Plumbing only (ruling P2): a checkpoint stores integers, bits, hash states and the exact Python objects a
step computed; a step that loads one ends in the same bytes as a step that computed it (the gates compare).

THE STEPS (each with its own key; the step's module says what one record holds). Only these two: the later
phases already save at their ends (runs/resume.py).
  census     derive/census.py scan_target: the census after every chunk of target files, as a delta (the
             units first seen, the bit and histogram rows the chunk touched, the presence counts and the
             driver files read, the resumable SHA-256 states of R1's hashes), replayed in order;
  r30        pipeline/stream.py StreamedShareReader (the per-group path): per group, as soon as it is counted,
             the integer counts R30 sums over the groups and what the group's column reader leaves behind (its
             last-value record, its static report strata, its data manifest).

LOADS. A process loads only the records that were on disk when it first opened the step (an earlier, stopped
process's); a record this process wrote is never loaded back by it, so an uninterrupted run computes everything,
as the engine without checkpoints does.

KEY. A step's key is the SHA-256 of the canonical JSON of its parts: the package fingerprint, the engine code
(runs.fingerprint.engine_code_sha256: every engine file's bytes), the library versions and Python, every
input file the step reads (path, size, mtime_ns) and the derived settings it depends on. A restart reuses a
checkpoint ONLY under the same key; otherwise the step recomputes, and the log says which part changed
(against the newest earlier folder of the same step).

FILES. <run root>/<package>/_checkpoints/<step>-<first 16 hex of the key>/ holds key.json (the parts and the
key) and the records. A record is a data file <name>.dat and its sidecar <name>.json (the data file's
SHA-256 and size, and the record's meta), each written atomically (temp file, fsync, rename), the data file
first. A data file without its sidecar is a partial write: ignored. A data file whose SHA-256 is not its
sidecar's (truncated, overwritten) or an unreadable sidecar is CORRUPT: reported loudly, moved aside
(<file>.corrupt-<n>) and recomputed. Nothing is trusted silently.

CLEANUP. A finished run removes the checkpoint folders this process used (after DONE.json). Folders of other
keys stay (a plan's checkpoints serve the run that follows it); their size is reported, and the owner
removes stale ones by hand.

RESUMABLE SHA-256. R1's input hashes are SHA-256 digests fed row by row over the whole census pass. Python's
hashlib cannot save a digest's state, so the census hashes through OpenSSL's own SHA256_Init / _Update /
_Final (ctypes, the libcrypto that ships with Python), whose context is a plain C struct that is saved as
bytes and restored. It is checked against hashlib on first use (fresh, resumed and copied states); when the
library is missing or the check fails the census runs on hashlib and saves no chunk (the log says so).
"""

import ctypes
import ctypes.util
import datetime
import glob
import hashlib
import io
import json
import os
import pickle
import platform
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from treeroute.errors import RefusedError
from treeroute.runs.atomic import dumps, dumps_canonical, read_json, replace_bytes, replace_text

CHECKPOINT_DIR = "_checkpoints"
KEY_FILE = "key.json"
DATA_SUFFIX = ".dat"
SIDE_SUFFIX = ".json"
CORRUPT_MARK = ".corrupt-"
PICKLE_PROTOCOL = 4                # protocol 4: Python 3.4 and later read it; fixed so a record's bytes never vary
KEY_SHOW = 16                      # hex characters of a key in a folder name and in the log
_SHOW = 3
_NAME = re.compile(r"^[a-z0-9][a-z0-9_]*$")
_GIB = float(1 << 30)


class CheckpointRefusal(RefusedError):
    """A checkpoint could not be written or its folder is not what its name says (fail loudly)."""


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------------------------------
# Resumable SHA-256 (OpenSSL's context struct, saved as bytes)
# origin: OpenSSL's SHA256_CTX is h[8], Nl, Nh, data[16], num, md_len: 28 unsigned ints, 112 bytes (sha.h, the
# same in the 1.1 and 3 series). The buffer is larger and zeroed, so a wider struct could never write past it;
# the whole buffer is the saved state (the bytes the library never touches stay zero).
SHA_CTX_BYTES = 256
SHA_DIGEST_BYTES = 32


class _Crypto(object):
    lib = None
    checked = False
    why = None


def _find_libcrypto() -> List[str]:
    """Candidate libcrypto files: the ones beside Python's own _hashlib / _ssl modules first."""
    out: List[str] = []
    try:
        import _hashlib

        here = os.path.dirname(getattr(_hashlib, "__file__", "") or "")
        if here:
            out += sorted(glob.glob(os.path.join(here, "libcrypto*")))
    except ImportError:
        pass
    for folder in (os.path.join(sys.base_prefix, "DLLs"), os.path.join(sys.base_prefix, "lib")):
        out += sorted(glob.glob(os.path.join(folder, "libcrypto*")))
    found = ctypes.util.find_library("crypto")
    if found:
        out.append(found)
    seen = []
    for c in out:
        if c not in seen:
            seen.append(c)
    return seen


def _load_crypto():
    if _Crypto.checked:
        return _Crypto.lib
    _Crypto.checked = True
    for path in _find_libcrypto():
        try:
            lib = ctypes.CDLL(path)
            init, update, final = lib.SHA256_Init, lib.SHA256_Update, lib.SHA256_Final
        except (OSError, AttributeError) as exc:
            _Crypto.why = "%s: %s" % (path, exc)
            continue
        init.argtypes, init.restype = [ctypes.c_void_p], ctypes.c_int
        update.argtypes, update.restype = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t], ctypes.c_int
        final.argtypes, final.restype = [ctypes.c_void_p, ctypes.c_void_p], ctypes.c_int
        _Crypto.lib = lib
        try:
            _self_test()
        except Exception as exc:              # a wrong result or a crash in the check: never used
            _Crypto.lib = None
            _Crypto.why = "%s failed the check against hashlib: %s" % (path, exc)
            continue
        _Crypto.why = None
        return lib
    if _Crypto.why is None:
        _Crypto.why = "no libcrypto with SHA256_Init found"
    return None


class ResumableSha256(object):
    """SHA-256 whose state is bytes (state() / from_state()): update, copy, hexdigest as hashlib's."""

    def __init__(self, _state: Optional[bytes] = None) -> None:
        lib = _Crypto.lib if _Crypto.checked else _load_crypto()
        if lib is None:
            raise CheckpointRefusal("P1", "the resumable SHA-256 is not available (%s)" % _Crypto.why,
                                    fix="internal: the census runs on hashlib without chunk checkpoints")
        self._lib = lib
        self._ctx = ctypes.create_string_buffer(SHA_CTX_BYTES)
        if _state is None:
            if self._lib.SHA256_Init(self._ctx) != 1:
                raise CheckpointRefusal("P1", "SHA256_Init failed")
        else:
            if len(_state) != SHA_CTX_BYTES:
                raise CheckpointRefusal("P1", "a saved SHA-256 state holds %d bytes, not %d" % (len(_state),
                                                                                                  SHA_CTX_BYTES))
            ctypes.memmove(self._ctx, _state, SHA_CTX_BYTES)

    def update(self, data: Any) -> None:
        if not isinstance(data, bytes):
            data = bytes(data)
        if self._lib.SHA256_Update(self._ctx, data, len(data)) != 1:
            raise CheckpointRefusal("P1", "SHA256_Update failed")

    def copy(self) -> "ResumableSha256":
        return ResumableSha256(self.state())

    def state(self) -> bytes:
        return bytes(self._ctx.raw)

    @classmethod
    def from_state(cls, state: bytes) -> "ResumableSha256":
        return cls(bytes(state))

    def digest(self) -> bytes:
        ctx = ctypes.create_string_buffer(self.state(), SHA_CTX_BYTES)
        out = ctypes.create_string_buffer(SHA_DIGEST_BYTES)
        if self._lib.SHA256_Final(out, ctx) != 1:
            raise CheckpointRefusal("P1", "SHA256_Final failed")
        return bytes(out.raw)

    def hexdigest(self) -> str:
        return self.digest().hex()


def _self_test() -> None:
    """Fresh, resumed (state saved and restored mid-stream) and copied states against hashlib."""
    parts = [b"", b"a", b"x" * 63, b"y" * 64, b"z" * 65, bytes(range(256)) * 9, b"tail"]
    ref = hashlib.sha256()
    h = ResumableSha256()
    for i, p in enumerate(parts):
        ref.update(p)
        h.update(p)
        if i % 2:
            h = ResumableSha256.from_state(h.state())
        if ref.hexdigest() != h.copy().hexdigest():
            raise ValueError("digest differs after part %d" % i)
    if hashlib.sha256(b"abc").hexdigest() != _one(b"abc"):
        raise ValueError("digest of a short message differs")


def _one(data: bytes) -> str:
    h = ResumableSha256()
    h.update(data)
    return h.hexdigest()


def resumable_sha256_available() -> Tuple[bool, Optional[str]]:
    """(available, why not)."""
    lib = _load_crypto()
    return lib is not None, _Crypto.why


# ---------------------------------------------------------------------------------------------------
# Key parts
def file_stats(paths: Sequence[Any]) -> List[List[Any]]:
    """[path, size, mtime_ns] per file, in the order given (forward slashes; a missing file refuses)."""
    out = []
    for p in paths:
        st = os.stat(str(p))
        out.append([str(p).replace("\\", "/"), int(st.st_size), int(st.st_mtime_ns)])
    return out


_ENGINE = {}


def engine_parts() -> Dict[str, Any]:
    """The key parts every step shares: the engine code (file bytes), the library versions and Python."""
    if "parts" not in _ENGINE:
        from treeroute.runs.fingerprint import engine_code_sha256, library_versions

        _ENGINE["parts"] = {"engine_code_sha256": engine_code_sha256(), "libraries": library_versions(),
                            "python": platform.python_version()}
    return dict(_ENGINE["parts"])


def key_of(parts: Mapping[str, Any]) -> str:
    return sha256_hex(dumps_canonical(parts).encode("ascii"))


def _short(value: Any) -> str:
    text = value if isinstance(value, str) else dumps_canonical(value)
    return text if len(text) <= 24 else "%s..." % text[:KEY_SHOW]


def _file_part(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, list) and len(v) == 3 and isinstance(v[0], str)
                                           for v in value) and bool(value)


def explain_difference(old: Mapping[str, Any], new: Mapping[str, Any]) -> List[str]:
    """Which key parts differ, in words (a file list names its changed, added and removed files)."""
    out: List[str] = []
    for k in sorted(set(old) | set(new)):
        a, b = old.get(k), new.get(k)
        if dumps_canonical(a) == dumps_canonical(b):
            continue
        if _file_part(a) and _file_part(b):
            fa = {p: (s, m) for p, s, m in a}
            fb = {p: (s, m) for p, s, m in b}
            changed = [p for p in fb if p in fa and fa[p] != fb[p]]
            added = [p for p in fb if p not in fa]
            removed = [p for p in fa if p not in fb]
            bits = []
            for p in changed[:_SHOW]:
                (s0, m0), (s1, m1) = fa[p], fb[p]
                bits.append("%s (size %d -> %d, mtime_ns %d -> %d)" % (p, s0, s1, m0, m1))
            if changed:
                bits = ["%d changed: %s%s" % (len(changed), "; ".join(bits), " ..." if len(changed) > _SHOW else "")]
            if added:
                bits.append("%d added (%s%s)" % (len(added), ", ".join(added[:_SHOW]), " ..." if len(added) > _SHOW
                                                 else ""))
            if removed:
                bits.append("%d removed (%s%s)" % (len(removed), ", ".join(removed[:_SHOW]),
                                                   " ..." if len(removed) > _SHOW else ""))
            if not bits:
                bits.append("the file order changed")
            out.append("input files '%s': %s" % (k, "; ".join(bits)))
        elif k not in old:
            out.append("%s is new" % k)
        elif k not in new:
            out.append("%s is gone" % k)
        else:
            out.append("%s changed (%s -> %s)" % (k, _short(a), _short(b)))
    return out


# ---------------------------------------------------------------------------------------------------
class Checkpoints(object):
    """The checkpoint root of one package: <run root>/<package>/_checkpoints (module docstring). Every folder
    it creates is checked against the shipped registry first (runs.registry: never under a protected root)."""

    def __init__(self, run_root: Any, package_name: str, registry: Any, echo: Callable[[str], None]) -> None:
        self.registry = registry
        self.root = Path(registry.assert_writable(Path(run_root) / package_name / CHECKPOINT_DIR))
        self.echo = echo
        self.used: Dict[str, "CheckpointStep"] = {}
        self.loaded: Dict[str, int] = {}

    def step(self, name: str, parts: Mapping[str, Any]) -> "CheckpointStep":
        if not _NAME.match(name):
            raise ValueError("a checkpoint step name is lower-case letters, digits and '_', got %r" % (name,))
        full = dict(engine_parts(), step=name, **dict(parts))
        key = key_of(full)
        folder = self.root / ("%s-%s" % (name, key[:KEY_SHOW]))
        step = self.used.get(str(folder))
        if step is None:
            step = CheckpointStep(self, name, key, full, folder)
            self.used[str(folder)] = step
        return step

    def folders(self) -> List[Path]:
        if not self.root.is_dir():
            return []
        return sorted(p for p in self.root.iterdir() if p.is_dir())

    def footprint_bytes(self, folders: Optional[Sequence[Path]] = None) -> int:
        total = 0
        for f in (self.folders() if folders is None else folders):
            for p in Path(f).rglob("*"):
                if p.is_file():
                    total += p.stat().st_size
        return int(total)

    def report_stale(self) -> None:
        """Log the folders of other keys (left for the owner; never removed by the engine)."""
        mine = {str(Path(s.folder)) for s in self.used.values()}
        stale = [f for f in self.folders() if str(f) not in mine]
        if stale:
            self.echo("checkpoint: %d folder(s) of other keys under %s hold %.2f GiB (%s%s); a run never reuses "
                      "them; remove them by hand when no plan or run needs them"
                      % (len(stale), self.root, self.footprint_bytes(stale) / _GIB,
                         ", ".join(f.name for f in stale[:_SHOW]), " ..." if len(stale) > _SHOW else ""))

    def remove_used(self) -> None:
        """After the run finished: remove the folders this process used (its own checkpoints), loudly."""
        import gc

        gc.collect()
        removed, size = [], 0
        for step in list(self.used.values()):
            folder = Path(step.folder)
            if not folder.is_dir():
                continue
            self.registry.assert_writable(folder)
            size += self.footprint_bytes([folder])
            shutil.rmtree(str(folder))
            removed.append(folder.name)
        self.used = {}
        if removed:
            self.echo("checkpoint: the run finished; removed its %d checkpoint folder(s) (%.3f GiB): %s"
                      % (len(removed), size / _GIB, ", ".join(removed)))
        if self.root.is_dir() and not any(self.root.iterdir()):
            self.root.rmdir()
        else:
            self.report_stale()


class CheckpointStep(object):
    """One step's folder under one key (module docstring)."""

    def __init__(self, owner: Checkpoints, name: str, key: str, parts: Mapping[str, Any], folder: Path) -> None:
        self.owner, self.name, self.key, self.parts, self.folder = owner, name, key, dict(parts), Path(folder)
        self.echo = owner.echo
        self.corrupt: List[str] = []
        self.preexisting: set = set()          # records on disk at open (a stopped process's): the only ones loaded
        self._opened = False
        self._open()

    # ------------------------------------------------------------------ the folder and its key
    def _open(self) -> None:
        key_path = self.folder / KEY_FILE
        if self.folder.is_dir():
            try:
                held = read_json(key_path) if key_path.is_file() else None
            except Exception as exc:
                held = {"unreadable": str(exc)}
            if held is not None and held.get("key") == self.key:
                self.preexisting = set(self.records())
                n = len(self.preexisting)
                partial = self._partials()
                self.echo("checkpoint: %s key %s: %d saved record(s) in %s%s"
                          % (self.name, self.key[:KEY_SHOW], n, self.folder,
                             ("; ignored %d partial write(s) of a stopped process: %s"
                              % (len(partial), ", ".join(p.name for p in partial[:_SHOW]))) if partial else ""))
                self._opened = True
                return
            # the folder's name says this key but its key file does not (an unwritten or damaged key file, or a
            # 64-bit name collision): never trusted, moved aside whole
            aside = self._aside(self.folder)
            self.echo("CHECKPOINT CORRUPT: %s's folder %s holds no readable key file for key %s (%s); moved aside to "
                      "%s and recomputed" % (self.name, self.folder, self.key[:KEY_SHOW],
                                             "none" if held is None else _short(held), aside.name))
        self._explain_new()

    def _explain_new(self) -> None:
        siblings = []
        root = self.owner.root
        mine = {str(Path(s.folder)) for s in self.owner.used.values()}
        if root.is_dir():
            for d in root.iterdir():
                if d.is_dir() and d.name.startswith(self.name + "-") and (d / KEY_FILE).is_file()                         and str(d) not in mine:
                    siblings.append(d)
        if not siblings:
            self.echo("checkpoint: %s key %s: no earlier checkpoint of this step; computing" % (self.name,
                                                                                               self.key[:KEY_SHOW]))
            return
        newest = max(siblings, key=lambda d: ((d / KEY_FILE).stat().st_mtime_ns, d.name))
        try:
            old = read_json(newest / KEY_FILE).get("parts") or {}
            why = explain_difference(old, self.parts)
        except Exception as exc:
            why = ["its key file is unreadable (%s)" % exc]
        self.echo("checkpoint: %s NOT reused: the newest earlier checkpoint %s has another key (%s -> %s): %s; "
                  "recomputing" % (self.name, newest.name, newest.name.rsplit("-", 1)[-1], self.key[:KEY_SHOW],
                                   "; ".join(why) or "the parts are equal in canonical JSON but the key differs"))

    def _ensure_folder(self) -> None:
        if self._opened:
            return
        self.owner.registry.assert_writable(self.folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        replace_text(self.folder / KEY_FILE, dumps({"key": self.key, "step": self.name, "parts": self.parts,
                                                     "created_utc": _utc_now()}) + "\n")
        self._opened = True

    def _aside(self, path: Path) -> Path:
        n = 1
        while True:
            target = path.with_name("%s%s%d" % (path.name, CORRUPT_MARK, n))
            if not target.exists():
                os.replace(str(path), str(target))
                return target
            n += 1

    def _partials(self) -> List[Path]:
        if not self.folder.is_dir():
            return []
        return sorted(p for p in self.folder.iterdir() if ".tmp-" in p.name)

    # ------------------------------------------------------------------ records
    def records(self, prefix: str = "") -> List[str]:
        """Names of the records with a sidecar (complete writes; their data are checked when loaded)."""
        if not self.folder.is_dir():
            return []
        out = []
        for p in self.folder.iterdir():
            if p.suffix == SIDE_SUFFIX and p.name != KEY_FILE and p.name.startswith(prefix) and ".tmp-" not in p.name:
                out.append(p.name[:-len(SIDE_SUFFIX)])
        return sorted(out)

    def save(self, name: str, data: bytes, fmt: str, meta: Optional[Mapping[str, Any]] = None) -> None:
        """Write a record: the data file atomically, then its sidecar (SHA-256, size, meta) atomically."""
        if not _NAME.match(name):
            raise ValueError("a checkpoint record name is lower-case letters, digits and '_', got %r" % (name,))
        self._ensure_folder()
        side = {"record": name, "format": fmt, "sha256": sha256_hex(data), "bytes": len(data),
                "key": self.key, "meta": dict(meta or {}), "written_utc": _utc_now()}
        side_text = dumps(side) + "\n"             # serialised first: a bad meta never leaves a data file
        replace_bytes(self.folder / (name + DATA_SUFFIX), data)
        replace_text(self.folder / (name + SIDE_SUFFIX), side_text)

    def load(self, name: str) -> Optional[Tuple[Dict[str, Any], bytes]]:
        """(meta, data) of a complete record whose data match their SHA-256; None when absent or written by this
        process (LOADS in the module docstring). A corrupt record is reported loudly, moved aside and None returned
        (the caller recomputes it)."""
        if name not in self.preexisting:
            return None
        side_path = self.folder / (name + SIDE_SUFFIX)
        data_path = self.folder / (name + DATA_SUFFIX)
        if not side_path.is_file():
            return None
        problem = None
        side: Dict[str, Any] = {}
        try:
            side = read_json(side_path)
        except Exception as exc:
            problem = "its sidecar is unreadable (%s)" % exc
        if problem is None:
            if side.get("key") != self.key:
                problem = "its sidecar names key %s" % str(side.get("key"))[:KEY_SHOW]
            elif not data_path.is_file():
                problem = "its data file is missing"
            else:
                data = data_path.read_bytes()
                if len(data) != side.get("bytes") or sha256_hex(data) != side.get("sha256"):
                    problem = ("its data file holds %d bytes with SHA-256 %s; the sidecar says %s bytes, %s"
                               % (len(data), sha256_hex(data)[:KEY_SHOW], side.get("bytes"),
                                  str(side.get("sha256"))[:KEY_SHOW]))
        if problem is not None:
            self.quarantine(name, problem)
            return None
        return dict(side.get("meta") or {}), data

    def quarantine(self, name: str, problem: str) -> None:
        moved = []
        for suffix in (DATA_SUFFIX, SIDE_SUFFIX):
            p = self.folder / (name + suffix)
            if p.exists():
                moved.append(self._aside(p).name)
        self.corrupt.append(name)
        self.echo("CHECKPOINT CORRUPT: %s record %s in %s: %s; moved aside (%s); recomputing it"
                  % (self.name, name, self.folder, problem, ", ".join(moved) or "nothing to move"))

    # ------------------------------------------------------------------ typed records
    def save_arrays(self, name: str, arrays: Mapping[str, Any], meta: Optional[Mapping[str, Any]] = None) -> None:
        import numpy as np

        buf = io.BytesIO()
        np.savez(buf, **{k: np.ascontiguousarray(v) for k, v in arrays.items()})
        self.save(name, buf.getvalue(), "npz", meta)

    def load_arrays(self, name: str) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        import numpy as np

        got = self.load(name)
        if got is None:
            return None
        meta, data = got
        with np.load(io.BytesIO(data), allow_pickle=False) as z:
            arrays = {k: z[k] for k in z.files}
        return meta, arrays

    def save_object(self, name: str, obj: Any, meta: Optional[Mapping[str, Any]] = None) -> None:
        self.save(name, pickle.dumps(obj, protocol=PICKLE_PROTOCOL), "pickle", meta)

    def load_object(self, name: str) -> Optional[Tuple[Dict[str, Any], Any]]:
        """A pickled record. Only records this engine wrote under this key are read, after their SHA-256 matched
        the sidecar written with them."""
        got = self.load(name)
        if got is None:
            return None
        meta, data = got
        return meta, pickle.loads(data)

    def discard_from(self, names: Sequence[str], why: str) -> None:
        """Move aside records a replay cannot use (records after a corrupt or missing one)."""
        for name in names:
            self.quarantine(name, why)


def record_name(prefix: str, text: str) -> str:
    """A record name for any text (a group name may hold any character): the prefix and 20 hex of its SHA-256."""
    return "%s_%s" % (prefix, sha256_hex(str(text).encode("utf-8"))[:20])


def disk_check(checkpoints: Optional[Checkpoints], need_bytes: int, what: str, echo: Callable[[str], None]) -> None:
    """G-DISK go/refuse for checkpoint bytes still to be written under the checkpoint root (they never set a
    number; a refusal names the fix)."""
    from treeroute.errors import PreflightRefusal
    from treeroute.runs import preflight

    if checkpoints is None:
        return
    try:
        preflight.check_resources(checkpoints.root, int(need_bytes), 0)
    except PreflightRefusal as exc:
        raise CheckpointRefusal("G-DISK", "the checkpoints of %s need about %.2f GiB under %s: %s"
                                % (what, need_bytes / _GIB, checkpoints.root, exc),
                                fix="free disk on that drive (stale checkpoint folders of other keys may be "
                                    "removed by hand); the run size is never reduced") from exc
    echo("preflight: checkpoints of %s need about %.3f GiB under %s (%.2f GiB free; %.3f GiB held there now): go"
         % (what, need_bytes / _GIB, checkpoints.root, preflight.free_disk_bytes(checkpoints.root) / _GIB,
            checkpoints.footprint_bytes() / _GIB))


__all__ = ["Checkpoints", "CheckpointStep", "CheckpointRefusal", "ResumableSha256", "resumable_sha256_available",
           "file_stats", "engine_parts", "key_of", "explain_difference", "record_name", "disk_check",
           "CHECKPOINT_DIR"]
