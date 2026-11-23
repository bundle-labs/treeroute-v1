"""The shared contract of the rivals export and harness (SPEC_RIVALS.md section 1).

Paths, file names, column names and small file helpers only. No science, no problem name, no number that
changes a result. Both builders code to this module; neither redefines a name kept here.

Roots (1.1) come from ONE YAML file (rivals.yaml): every root path absolute. Every write path is checked
with the engine's runs.registry.Registry(registry_dir).assert_writable(path) before the first byte
(assert_writable below takes the registry object). Nothing is ever deleted: a replaced or partial file is
moved under moved_root/<utc stamp>/ (move_aside).

This module imports no numeric library, so the export can read its config before the engine's thread
pins (treeroute.launch.pin_threads refuses once numpy is loaded).
"""

import datetime
import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

# ---------------------------------------------------------------------------------------------------
# 1.1 Roots
ROOT_KEYS = ("engine_root", "machine_file", "export_root", "export_ckpt_root", "out_root", "moved_root")
CONFIG_NAME = "rivals.yaml"
# the build folder holds rivals/ (this package) and rivals.yaml beside it
BUILD_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = BUILD_ROOT / CONFIG_NAME
LINEAGE_NAME = "engine_lineage.json"


class LayoutRefusal(Exception):
    """A layout rule refused (fail loudly): a bad config, a write outside the allowed roots."""

    def __init__(self, check: str, message: str, fix: Optional[str] = None) -> None:
        self.check = check
        self.fix = fix
        text = "refused [%s]: %s" % (check, message)
        if fix:
            text += " (fix: %s)" % fix
        super().__init__(text)


@dataclass(frozen=True)
class Roots:
    """The six roots of rivals.yaml (absolute paths) and any other keys the file holds (extra)."""
    engine_root: Path
    machine_file: Path
    export_root: Path
    export_ckpt_root: Path
    out_root: Path
    moved_root: Path
    source: str = "<mapping>"
    extra: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        out = {k: str(getattr(self, k)).replace("\\", "/") for k in ROOT_KEYS}
        out["source"] = self.source
        out["extra"] = json.loads(json.dumps(dict(self.extra), default=str))
        return out


def roots_from_mapping(data: Mapping[str, Any], source: str = "<mapping>") -> Roots:
    """Roots from a mapping (the parsed rivals.yaml). Refuses a missing key and a relative path."""
    if not isinstance(data, Mapping):
        raise LayoutRefusal("CONFIG", "%s is not a mapping of root names to paths" % source)
    missing = [k for k in ROOT_KEYS if not data.get(k)]
    if missing:
        raise LayoutRefusal("CONFIG", "%s has no %s" % (source, ", ".join(missing)),
                            fix="give every root of SPEC_RIVALS.md 1.1 as an absolute path")
    paths = {}
    for k in ROOT_KEYS:
        p = Path(str(data[k]))
        if not p.is_absolute():
            raise LayoutRefusal("CONFIG", "%s: %s must be an absolute path, got %r" % (source, k, str(data[k])))
        paths[k] = p
    extra = {k: v for k, v in data.items() if k not in ROOT_KEYS}
    return Roots(source=source, extra=extra, **paths)


def load_roots(path: Any = None) -> Roots:
    """Read rivals.yaml (default: the build folder's) and return its Roots."""
    import yaml

    p = Path(path) if path is not None else DEFAULT_CONFIG
    if not p.is_file():
        raise LayoutRefusal("CONFIG", "the config file %s is missing" % p,
                            fix="write rivals.yaml with the roots of SPEC_RIVALS.md 1.1")
    with open(p, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return roots_from_mapping(data, str(p))


def as_roots(config: Any) -> Roots:
    """A Roots from a Roots, a mapping, a path to rivals.yaml, or None (the default file)."""
    if isinstance(config, Roots):
        return config
    if isinstance(config, Mapping):
        return roots_from_mapping(config)
    return load_roots(config)


def lineage_file(roots: Roots) -> Path:
    """The engine lineage file (SPEC_RIVALS.md 2.2 I4): rivals.yaml's 'engine_lineage', else engine_lineage.json
    beside the config file (the build folder for a mapping)."""
    given = roots.extra.get("engine_lineage")
    if given:
        return Path(str(given))
    if roots.source and roots.source != "<mapping>":
        return Path(roots.source).resolve().parent / LINEAGE_NAME
    return BUILD_ROOT / LINEAGE_NAME


def import_engine(engine_root: Any) -> Any:
    """Put the LIVE engine first on sys.path and import treeroute from it (read-only). Refuses a treeroute
    already imported from another folder."""
    root = Path(engine_root).resolve()
    if not (root / "treeroute" / "__init__.py").is_file():
        raise LayoutRefusal("ENGINE", "%s holds no treeroute package" % root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import treeroute

    got = Path(treeroute.__file__).resolve().parents[1]
    if os.path.normcase(str(got)) != os.path.normcase(str(root)):
        raise LayoutRefusal("ENGINE", "treeroute is imported from %s, not from the engine root %s" % (got, root))
    return treeroute


# ---------------------------------------------------------------------------------------------------
# 1.2 The export folder of one run and lead
FORMAT_EXPORT = "rivals-export/1"
TRAIN_DIR = "train"
GUARDSIDE_DIR = "guardside"
TEST_DIR = "test"
PARTS = (TRAIN_DIR, GUARDSIDE_DIR, TEST_DIR)
UNITS_FILE = "units.parquet"
PROGRESS_DIR = "_progress"
EXPORT_MANIFEST = "export_manifest.json"
# a run exported under an owner-accepted engine difference: written LAST, once every lead passed P1-P15 in one
# call (Z check 1 c); it lists each lead's manifest sha256, and the harness refuses such a run without it
ACCEPT_SEAL = "ACCEPTED_ALL_LEADS.json"
FORMAT_ACCEPT_SEAL = "rivals-accept-seal/1"
EXPORT_LOG = "export.log"
STATUS_FILE = "status.json"
ENGINE_FOLDER = "_engine_folder"          # the export's empty engine host folder (one per run export)

# keys
COL_UNIT = "unit"
COL_GROUP = "group"
COL_TIME = "time"                         # the LABEL step (grids) or the target day (tables)
COL_ISSUE = "issue"                       # time - lead
COL_LEAD = "lead"
KEY_COLUMNS = (COL_UNIT, COL_GROUP, COL_TIME, COL_ISSUE, COL_LEAD)
COL_Y = "y"
COL_SAVED_ROW = "saved_row"               # test files: the row's index in the run's saved test_preds of the lead

# roles
ROLE_REFIT = "refit"
ROLE_TUNE = "tune"
ROLE_INNER = "inner"
ROLE_GUARDFIT = "guardfit"
ROLE_GUARD = "guard"
ROLE_TEST = "test"
ROLES = (ROLE_REFIT, ROLE_TUNE, ROLE_INNER, ROLE_GUARDFIT, ROLE_GUARD, ROLE_TEST)
ROLES_LEAD0 = (ROLE_REFIT, ROLE_TUNE, ROLE_INNER, ROLE_TEST)
ROLES_LEADL = (ROLE_REFIT, ROLE_GUARDFIT, ROLE_GUARD, ROLE_TEST)
TRAIN_ROLES = (ROLE_REFIT, ROLE_TUNE, ROLE_INNER, ROLE_GUARDFIT, ROLE_GUARD)
GUARDSIDE_ROLES_LEAD0 = (ROLE_TUNE, ROLE_INNER)
GUARDSIDE_ROLES_LEADL = (ROLE_GUARDFIT, ROLE_GUARD)
ROLE_FLAG = {r: "r_" + r for r in TRAIN_ROLES}
FLAG_COLUMNS = tuple(ROLE_FLAG[r] for r in TRAIN_ROLES)

# column prefixes
X_PREFIX = "x__"                          # tree columns (kept tree features, then the FIT-cut history block)
C_PREFIX = "c__"                          # router context
H_PREFIX = "h__"                          # guardside: the history block at the guard cut
NFIT_PREFIX = "nfit__"                    # the FIT-cut normal in link space, per R22 link
NGD_PREFIX = "ngd__"                      # guardside: the GUARD-cut normal in link space, per R22 link


def x_col(name: str) -> str:
    return X_PREFIX + str(name)


def c_col(name: str) -> str:
    return C_PREFIX + str(name)


def h_col(name: str) -> str:
    return H_PREFIX + str(name)


def nfit_col(link: str) -> str:
    return NFIT_PREFIX + str(link)


def ngd_col(link: str) -> str:
    return NGD_PREFIX + str(link)


def roles_of_lead(lead: int) -> Tuple[str, ...]:
    return ROLES_LEAD0 if int(lead) == 0 else ROLES_LEADL


def guardside_roles(lead: int) -> Tuple[str, ...]:
    return GUARDSIDE_ROLES_LEAD0 if int(lead) == 0 else GUARDSIDE_ROLES_LEADL


_SAFE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-.")


def group_file_stem(group: str) -> str:
    """A group's file name stem: the group name with every character outside [A-Za-z0-9 _-.] written as %XX
    (its UTF-8 bytes), so any group name gives one plain file name and group_of_stem reads it back."""
    out = []
    for ch in str(group):
        if ch in _SAFE and ch != "%":
            out.append(ch)
        else:
            out.extend("%%%02X" % b for b in ch.encode("utf-8"))
    stem = "".join(out)
    if stem in ("", ".", "..") or stem.endswith((".", " ")):
        stem = "".join("%%%02X" % b for b in str(group).encode("utf-8"))
    return stem


def group_of_stem(stem: str) -> str:
    """The inverse of group_file_stem."""
    raw = bytearray()
    i = 0
    s = str(stem)
    while i < len(s):
        if s[i] == "%":
            raw.append(int(s[i + 1:i + 3], 16))
            i += 3
        else:
            raw.extend(s[i].encode("utf-8"))
            i += 1
    return raw.decode("utf-8")


def export_run_dir(roots: Roots, package_name: str, run_name: str) -> Path:
    return Path(roots.export_root) / str(package_name) / str(run_name)


def accept_seal_file(roots: Roots, package_name: str, run_name: str) -> Path:
    return export_run_dir(roots, package_name, run_name) / ACCEPT_SEAL


def export_lead_dir(roots: Roots, package_name: str, run_name: str, lead: int) -> Path:
    return export_run_dir(roots, package_name, run_name) / ("lead_%d" % int(lead))


def group_file(lead_dir: Any, part: str, group: str) -> Path:
    if part not in PARTS:
        raise LayoutRefusal("LAYOUT", "unknown part %r (parts %s)" % (part, PARTS))
    return Path(lead_dir) / part / (group_file_stem(group) + ".parquet")


def progress_file(lead_dir: Any, part: str, group: str) -> Path:
    return Path(lead_dir) / PROGRESS_DIR / part / (group_file_stem(group) + ".json")


# ---------------------------------------------------------------------------------------------------
# 1.3 The harness output folder
BOARD_FILE = "board.json"
TRIALS_DIR = "trials"
TRIALS_CSV = "trials.csv"
PICKS_FILE = "picks.json"
PICKS_LOCK = "picks.json.lock.json"
TEST_LABELS_OPENED = "test_labels_opened_rivals_lead_%d.json"
SCORES_DIR = "scores"
BOARD_LEAD_CSV = "board_lead_%d.csv"
BOARD_MD = "board.md"
RIVALS_LOG = "rivals.log"
MATERIALIZED_DIR = "materialized"


def out_run_dir(roots: Roots, package_name: str, run_name: str) -> Path:
    return Path(roots.out_root) / str(package_name) / str(run_name)


def out_lead_dir(out_dir: Any, lead: int) -> Path:
    return Path(out_dir) / ("lead_%d" % int(lead))


# ---------------------------------------------------------------------------------------------------
# small file helpers
def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def utc_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Any, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def canonical_json(obj: Any) -> str:
    """Sorted keys, no spaces, ASCII: the text a hash is taken of."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False, default=str)


def sha256_json(obj: Any) -> str:
    return sha256_bytes(canonical_json(obj).encode("ascii"))


def code_sha(paths: Iterable[Any]) -> str:
    """SHA-256 of the canonical JSON of [[file name, sha256 of its bytes], ...] in the order given."""
    return sha256_json([[Path(p).name, sha256_file(p)] for p in paths])


def assert_writable(registry: Any, path: Any) -> Path:
    """The engine's Registry.assert_writable (runs/registry.py), before the first byte of any write."""
    if registry is None:
        raise LayoutRefusal("G-NOOVERWRITE", "internal: a write to %s was asked without the registry" % path)
    return Path(registry.assert_writable(Path(path)))


def atomic_write_bytes(path: Any, data: bytes, registry: Any) -> Path:
    """Write <name>.tmp_<pid> with open(..., 'xb'), flush, fsync, then os.replace onto the name (1.2)."""
    path = Path(path)
    assert_writable(registry, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp_%d" % os.getpid())
    assert_writable(registry, tmp)
    with open(tmp, "xb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(str(tmp), str(path))
    return path


def write_json_atomic(path: Any, obj: Any, registry: Any) -> Path:
    text = json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=True, allow_nan=False, default=str) + "\n"
    return atomic_write_bytes(path, text.encode("ascii"), registry)


def append_line(path: Any, line: str, registry: Any) -> None:
    """Append one line (UTC stamped by the caller) to a log file."""
    path = Path(path)
    assert_writable(registry, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line.rstrip("\n") + "\n")


def move_aside(path: Any, moved_root: Any, registry: Any, stamp: Optional[str] = None,
               relative_to: Any = None) -> Path:
    """Move a file or folder under moved_root/<stamp>/ (never delete). The relative path below relative_to
    (default: the path's drive anchor) is kept, so two moved files never collide. Returns the new path."""
    src = Path(path)
    if not src.exists():
        raise LayoutRefusal("MOVE", "nothing to move aside at %s" % src)
    base = Path(relative_to) if relative_to is not None else Path(src.anchor)
    try:
        rel = src.resolve().relative_to(base.resolve())
    except ValueError:
        rel = Path(src.name)
    dest = Path(moved_root) / (stamp or utc_stamp()) / rel
    assert_writable(registry, dest)
    if dest.exists():
        raise LayoutRefusal("MOVE", "%s already exists; a moved file is never overwritten" % dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    return dest


__all__ = [n for n in dir() if not n.startswith("_") and n not in (
    "annotations", "datetime", "hashlib", "json", "os", "shutil", "sys", "dataclass", "field", "Path", "Any",
    "Dict", "Iterable", "Mapping", "Optional", "Tuple")]
