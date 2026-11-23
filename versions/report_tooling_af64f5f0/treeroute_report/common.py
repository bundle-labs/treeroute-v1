"""Shared helpers of treeroute_report (outside the engine hash; plan 7.1).

Nothing here changes a fit, a pick or a decision. Every refusal names its rule and its fix (fail loudly).
"""

import ast
import datetime
import hashlib
import io
import json
import os
import tokenize
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from treeroute.errors import RefusedError

REPORT_DIR = Path(__file__).resolve().parent
ENGINE_DIR = REPORT_DIR.parent
TREEROUTE_DIR = ENGINE_DIR / "treeroute"
CONSTANTS_FILE = TREEROUTE_DIR / "engine_constants.py"

# The CHECK REPORT CONTRACT (between agent B's 'treeroute check' and this tool): engine_code_sha256 is the
# SHA-256 over the sorted (relative path, file SHA-256) list of every .py file under treeroute/ except
# _proposed/ and __pycache__/. Agent B owns the function, in treeroute/runs/fingerprint.py; this tool imports
# it and never re-implements it, so the value it compares is byte for byte the one the check report wrote.
CONTRACT_MODULE = "treeroute.runs.fingerprint"
CONTRACT_FUNCTION = "engine_code_sha256"
# Owner ruling M2 (OWNER_RULINGS_2026-10-06.md): the freeze gate's deep check runs on each package's R21 smoke groups.
# The groups a deep report must have checked come from the check's own function (it lists the groups as the smoke
# command does and calls the engine's smoke rule); this tool imports it and never re-implements the rule.
SMOKE_GROUPS_MODULE = "treeroute.check.report"
SMOKE_GROUPS_FUNCTION = "package_smoke_groups"

GIB = float(1 << 30)


class ReportRefusal(RefusedError):
    """treeroute_report refused (fail loudly; the message names the rule and the fix)."""


# ------------------------------------------------------------------------------------------- time
def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def utc_stamp(moment: datetime.datetime) -> str:
    """'20261010T120000Z': the UTC timestamp used in file names."""
    return moment.astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso(moment: datetime.datetime) -> str:
    return moment.astimezone(datetime.timezone.utc).isoformat(timespec="seconds")


# ----------------------------------------------------------------------------------------- hashes
def sha256_file(path: Any) -> str:
    from treeroute.runs.fingerprint import sha256_file as _sha

    return _sha(path)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def gib(n_bytes: float) -> str:
    """A size in GiB (2^30 bytes), printed as GiB."""
    return "%.3f GiB" % (float(n_bytes) / GIB)


def engine_file_hashes(root: Optional[Path] = None) -> Dict[str, str]:
    """{relative posix path: file SHA-256} of every engine .py file (the listing behind the contract hash;
    _proposed/ and __pycache__/ excluded by fingerprint.engine_module_files)."""
    from treeroute.runs.fingerprint import engine_module_files

    root = Path(root) if root is not None else TREEROUTE_DIR
    return {p.relative_to(root).as_posix(): sha256_file(p) for p in engine_module_files(root)}


REPORT_TOOLING_SUFFIXES = (".py", ".yaml", ".yml")


def report_file_hashes(root: Optional[Path] = None) -> Dict[str, str]:
    """{relative posix path: file SHA-256} of every .py and .yaml file of this tool (treeroute_report/:
    the table builder, the freeze, and the pre-registered lists continuity_groups.yaml, history_bands.yaml and
    report_rows.yaml). They are outside the engine hash, so the freeze lock records them on their own."""
    root = Path(root) if root is not None else REPORT_DIR
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in REPORT_TOOLING_SUFFIXES and "__pycache__" not in p.parts:
            out[p.relative_to(root).as_posix()] = sha256_file(p)
    if not out:
        raise ReportRefusal("F-TOOLING", "no .py or .yaml file found under %s" % root)
    return out


def contract_engine_code_sha256() -> str:
    """engine_code_sha256 of the live engine, from agent B's contract function. Refuses while it is absent:
    a value computed here could differ in its serialisation from the one the check report wrote."""
    import importlib

    module = importlib.import_module(CONTRACT_MODULE)
    fn = getattr(module, CONTRACT_FUNCTION, None)
    if fn is None:
        raise ReportRefusal("CHECK-CONTRACT", "%s.%s is missing: the CHECK REPORT CONTRACT puts the engine code "
                            "hash there (agent B adds it), and the freeze compares the check report against it"
                            % (CONTRACT_MODULE, CONTRACT_FUNCTION),
                            fix="add the contract function (agent B's scope), then run the freeze again")
    value = fn()
    if not (isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)):
        raise ReportRefusal("CHECK-CONTRACT", "%s.%s() returned %r, not 64 lower-case hex characters"
                            % (CONTRACT_MODULE, CONTRACT_FUNCTION, value))
    return value


def package_smoke_groups(package: Any, rule: str = "F-CHECK-GROUPS") -> Dict[str, Any]:
    """Ruling M2's checked_groups record of a loaded package ({groups, selection, rule, constants, package_groups,
    data_groups, refused}), from the check's own function (SMOKE_GROUPS_MODULE.SMOKE_GROUPS_FUNCTION). Refuses
    (ReportRefusal under ``rule``) when that function is missing or when listing the groups or R21 refuses."""
    import importlib

    module = importlib.import_module(SMOKE_GROUPS_MODULE)
    fn = getattr(module, SMOKE_GROUPS_FUNCTION, None)
    if fn is None:
        raise ReportRefusal(rule, "%s.%s is missing: ruling M2 needs the check's own list of a package's R21 smoke "
                            "groups" % (SMOKE_GROUPS_MODULE, SMOKE_GROUPS_FUNCTION),
                            fix="restore the function in treeroute/check/report.py")
    try:
        return fn(package)
    except RefusedError as exc:
        raise ReportRefusal(rule, "the package's R21 smoke groups cannot be listed: %s" % exc,
                            fix=getattr(exc, "fix", None) or "fix the target store or split.yaml") from exc


# ------------------------------------------------------------------------------ engine constants
def _comment_text(line: str) -> str:
    text = line.strip()
    if text.startswith("#"):
        text = text[1:].strip()
    return text


def constant_origins(path: Optional[Path] = None) -> Dict[str, str]:
    """{constant id: its origin comment} read from engine_constants.py.

    A constant's origin is the comment block nearest above its _c(...) statement (walking up over the
    statements of the same block, stopping at a blank line), plus any trailing comment on its own lines.
    Lines of only dashes are dropped. The engine keeps origins in comments, never in strings (G-NONAMES),
    so this is the only place they can be read from."""
    path = Path(path) if path is not None else CONSTANTS_FILE
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    trailing: Dict[int, List[str]] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            row, col = tok.start
            if lines[row - 1][:col].strip():          # code before it on the same line: a trailing comment
                trailing.setdefault(row, []).append(_comment_text(tok.string))
    tree = ast.parse(source)
    code_lines = set()
    calls = []
    for node in tree.body:
        code_lines.update(range(node.lineno, node.end_lineno + 1))
        value = getattr(node, "value", None)
        if isinstance(node, (ast.Assign, ast.Expr)) and isinstance(value, ast.Call) \
                and isinstance(value.func, ast.Name) and value.func.id == "_c":
            first = value.args[0] if value.args else None
            if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
                raise ReportRefusal("F-CONSTANTS", "%s:%d: a _c(...) call whose first argument is not a literal id"
                                    % (path.name, node.lineno))
            calls.append((node.lineno, node.end_lineno, first.value))
    out: Dict[str, str] = {}
    for start, end, cid in calls:
        row = start - 1
        while row >= 1 and row in code_lines:          # other statements of the same block
            row -= 1
        block: List[str] = []
        while row >= 1 and lines[row - 1].strip().startswith("#"):
            block.append(_comment_text(lines[row - 1]))
            row -= 1
        block.reverse()
        own = [t for r in range(start, end + 1) for t in trailing.get(r, [])]
        parts = [t for t in block + own if t and set(t) != {"-"}]
        if cid in out:
            raise ReportRefusal("F-CONSTANTS", "engine constant id %r is registered twice in %s" % (cid, path.name))
        out[cid] = " ".join(parts)
    return out


def constants_with_origins() -> List[Dict[str, Any]]:
    """Every engine constant: id, value, test-exposed flag, status (engine_constants.table()) and origin."""
    from treeroute import engine_constants as K

    origins = constant_origins()
    rows = []
    for row in K.table():
        if row["id"] not in origins:
            raise ReportRefusal("F-CONSTANTS", "engine constant %s has no _c(...) statement the origin reader "
                                "found in %s" % (row["id"], CONSTANTS_FILE.name))
        rows.append(dict(row, origin=origins[row["id"]]))
    extra = sorted(set(origins) - set(r["id"] for r in rows))
    if extra:
        raise ReportRefusal("F-CONSTANTS", "_c(...) statements without a registered constant: %s" % extra)
    return rows


# ------------------------------------------------------------------------------------ version pins
VERSION_PINS_FILE = ENGINE_DIR / "tests" / "test_fit_tables_guard.py"
VERSION_PINS_NAME = "PINNED"


def version_pins(path: Optional[Path] = None) -> Dict[str, Any]:
    """The library version pins of owner ruling C ('add version pins and a guard test'). They live in the
    guard test, not the engine (G-NONAMES refuses the version string there). Returns the source, its hash,
    the pins and the installed versions."""
    from importlib import metadata

    path = Path(path) if path is not None else VERSION_PINS_FILE
    if not path.is_file():
        raise ReportRefusal("F-PINS", "the version-pin file %s is missing" % path)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    pins = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == VERSION_PINS_NAME
                                                for t in node.targets):
            pins = ast.literal_eval(node.value)
    if not isinstance(pins, dict) or not pins:
        raise ReportRefusal("F-PINS", "%s holds no %s dict of version pins" % (path, VERSION_PINS_NAME))
    installed = {}
    for dist in sorted(pins):
        try:
            installed[dist] = metadata.version(dist)
        except metadata.PackageNotFoundError:
            installed[dist] = None
    return {"source": str(path), "source_sha256": sha256_file(path), "pins": dict(sorted(pins.items())),
            "installed": installed}


# --------------------------------------------------------------------------------- protected paths
def _norm(path: Any) -> str:
    from treeroute.runs.registry import normalize

    return normalize(path)


def _within(path_n: str, root_n: str) -> bool:
    try:
        return os.path.commonpath([path_n, root_n]) == root_n
    except ValueError:
        return False


def _identity(path: str):
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (st.st_dev, st.st_ino) if st.st_ino else None


class WriteGuard(object):
    """Refuse a write of this tool under a protected root, onto a registered shipped file or a hard-linked
    file, or inside the registry folder outside the sub-folders this tool owns there.

    The roots come from the registry the engine reads (protected_roots.txt plus shipped.json's roots and
    files; treeroute.runs.registry.Registry refuses a missing or empty registry). Paths are compared by
    spelling (resolved, case folded) and by file identity of every existing ancestor, as the engine does.
    The engine's own Registry refuses every write inside the registry folder; the freeze lock is the one
    file the plan puts there (registry/freeze/), so this guard allows exactly the sub-folders named."""

    def __init__(self, registry_dir: Any, own_registry_subdirs: Sequence[str] = ()):
        from treeroute.runs.registry import Registry

        self.registry = Registry(registry_dir)
        self.registry_dir = Path(registry_dir)
        self._roots_n = sorted(set(_norm(r) for r in self.registry.roots))
        self._root_ids = {}
        for root_n in self._roots_n:
            ident = _identity(root_n)
            if ident is not None:
                self._root_ids[ident] = root_n
        shipped = self.registry_dir / "shipped.json"
        self._files_n = set()
        if shipped.is_file():
            data = json.loads(shipped.read_text(encoding="utf-8"))
            self._files_n = set(_norm(e["path"]) for e in data.get("files", []))
        self._registry_n = _norm(self.registry_dir)
        self._own_n = [_norm(self.registry_dir / d) for d in own_registry_subdirs]

    def check(self, path: Any) -> Path:
        """The resolved path to create; refuses a protected location."""
        from treeroute.runs.registry import canonical

        canon = canonical(path)
        path_n = os.path.normcase(canon)
        for root_n in self._roots_n:
            if _within(path_n, root_n):
                raise ReportRefusal("G-NOOVERWRITE", "%s is under the protected (shipped) root %s" % (path, root_n),
                                    fix="write outside every root in protected_roots.txt")
        current = Path(canon)
        for ancestor in [current] + list(current.parents):
            if os.path.lexists(str(ancestor)):
                ident = _identity(str(ancestor))
                if ident is not None and ident in self._root_ids:
                    raise ReportRefusal("G-NOOVERWRITE", "%s resolves into the protected root %s through %s"
                                        % (path, self._root_ids[ident], ancestor))
        if path_n in self._files_n:
            raise ReportRefusal("G-NOOVERWRITE", "%s is a registered shipped file" % path)
        if _within(path_n, self._registry_n) and not any(_within(path_n, own) for own in self._own_n):
            raise ReportRefusal("G-NOOVERWRITE", "%s is inside the registry folder %s outside this tool's own "
                                "sub-folders (%s)" % (path, self._registry_n, ", ".join(self._own_n) or "none"))
        if os.path.isfile(canon) and os.stat(canon).st_nlink > 1:
            raise ReportRefusal("G-NOOVERWRITE", "%s has more than one hard link" % path)
        return Path(canon)


def machine_defaults() -> Dict[str, str]:
    """run_root and registry_dir from config/machine.yaml (the engine's machine file)."""
    from treeroute.runs.machine import load_machine

    machine = load_machine()
    return {"run_root": machine.run_root, "registry_dir": machine.registry_dir}


__all__ = ["REPORT_DIR", "ENGINE_DIR", "TREEROUTE_DIR", "ReportRefusal", "utc_now", "utc_stamp", "utc_iso",
           "sha256_file", "sha256_text", "gib", "engine_file_hashes", "report_file_hashes",
           "contract_engine_code_sha256",
           "constant_origins", "constants_with_origins", "version_pins", "WriteGuard", "machine_defaults"]
