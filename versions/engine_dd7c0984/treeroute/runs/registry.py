"""The shipped-results registry: refuse any write under a protected path (G-NOOVERWRITE).

The registry folder (its location comes from config/machine.yaml, never from engine code) holds:
  protected_roots.txt  one shipped root per line ('#' starts a comment)
  shipped.json         {"roots": [...], "files": [{"path": ...}, ...]} written by M0
  anything else        hash-verified backups and other bookkeeping (for example backup_* folders)

A path is refused if:
  - it is not a plain local drive path after resolution (UNC paths, admin shares, device and volume
    paths cannot be compared with the registry reliably, so they are refused outright);
  - it is, or lies under, a protected root from either file, by spelling OR by file identity (the
    volume serial and file index of every existing ancestor, which catches junctions, subst drives
    and other aliases that a string comparison misses);
  - it is a listed shipped file;
  - it lies inside the registry folder itself, except the files the engine writes there
    (``ENGINE_WRITTEN_REGISTRY_FILES``, plan 7.1);
  - it is an existing file with more than one hard link (it may be a shipped file under another
    name).

Spellings are resolved before any comparison: the extended-length prefix is stripped, '..' is
collapsed, trailing dots and spaces of each component are dropped (Win32 does the same when it opens
a path), symlinks and junctions are followed, and letter case is folded. ``assert_writable`` returns
the resolved path; callers create exactly that path, never their raw spelling.

A missing or empty registry refuses everything: without it no write can be checked. There is no
--force.
"""

import os
import re
from pathlib import Path

from treeroute.errors import RegistryError, RegistryRefusal
from treeroute.runs.atomic import read_json

PROTECTED_ROOTS_FILE = "protected_roots.txt"
SHIPPED_FILE = "shipped.json"
# Files inside the registry folder that the engine itself writes (plan 7.1). Everything else in the
# registry folder is protected.
ENGINE_WRITTEN_REGISTRY_FILES = ("index.csv", "bands.csv")

_IS_WINDOWS = os.name == "nt"
_BS = "\\"
_EXTENDED_UNC = _BS * 2 + "?" + _BS + "UNC" + _BS
_LOCAL_PREFIXES = (_BS * 2 + "?" + _BS, _BS * 2 + "." + _BS)
_DRIVE_ABSOLUTE = re.compile(r"^[A-Za-z]:\\")


class _Unresolvable(Exception):
    """A path spelling that cannot be resolved to a plain local path."""


def _strip_prefix(text):
    """Drop a Windows extended-length or device prefix; turn the extended UNC form into '\\\\'."""
    if not _IS_WINDOWS:
        return text
    if text[:8].upper() == _EXTENDED_UNC.upper():
        return _BS * 2 + text[8:]
    for prefix in _LOCAL_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix):]
    return text


def _drop_trailing_dots_and_spaces(text):
    """Win32 ignores trailing dots and spaces of each component; so does the comparison."""
    if not _IS_WINDOWS:
        return text
    drive, rest = os.path.splitdrive(text)
    parts = rest.split(_BS)
    out = []
    for part in parts:
        if part == "":
            out.append(part)
            continue
        fixed = part.rstrip(". ")
        if fixed == "":
            raise _Unresolvable("the component %r is only dots and spaces" % part)
        out.append(fixed)
    return drive + _BS.join(out)


def canonical(path):
    """Absolute, prefix-free, symlink-resolved path with its real letter case kept.

    This is the path the engine creates. Raises _Unresolvable for a spelling that does not resolve
    to a plain local path.
    """
    try:
        text = os.path.abspath(os.fspath(path))  # collapses '..' (even under the long prefix)
        text = _strip_prefix(text)
        text = os.path.abspath(text)
        text = _drop_trailing_dots_and_spaces(text)
        text = os.path.realpath(text)
    except (OSError, ValueError) as exc:
        raise _Unresolvable("%s: %s" % (type(exc).__name__, exc)) from exc
    text = _strip_prefix(text)
    if _IS_WINDOWS:
        if not _DRIVE_ABSOLUTE.match(text):
            raise _Unresolvable(
                "it is not a plain local drive path (UNC path, admin share, device or volume path)")
        text = _drop_trailing_dots_and_spaces(text)
    elif not text.startswith("/"):
        raise _Unresolvable("it is not an absolute path")
    return text


def normalize(path):
    """Canonical path with case folded: the string used for every comparison."""
    return os.path.normcase(canonical(path))


def _is_within(path_n, root_n):
    try:
        return os.path.commonpath([path_n, root_n]) == root_n
    except ValueError:  # different drives
        return False


def _identity(path):
    """(volume serial, file index) of an existing path, or None if it cannot be read."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    if not st.st_ino:  # the file system gives no stable file index
        return None
    return (st.st_dev, st.st_ino)


def _existing_ancestors(canon):
    path = Path(canon)
    for candidate in [path] + list(path.parents):
        if os.path.lexists(str(candidate)):
            yield candidate


class Registry(object):
    def __init__(self, registry_dir):
        self.registry_dir = Path(registry_dir)
        roots_file = self.registry_dir / PROTECTED_ROOTS_FILE
        if not roots_file.is_file():
            raise RegistryError("registry file %s is missing: no write can be checked, so every "
                                "write is refused" % roots_file)
        roots = []
        with open(roots_file, encoding="utf-8") as fh:
            for line in fh:
                text = line.split("#", 1)[0].strip()
                if text:
                    roots.append(text)
        shipped_files = []
        shipped_path = self.registry_dir / SHIPPED_FILE
        if shipped_path.is_file():
            shipped = read_json(shipped_path)
            if not isinstance(shipped, dict):
                raise RegistryError("%s is not a JSON object" % shipped_path)
            roots.extend(str(r) for r in shipped.get("roots", []))
            for entry in shipped.get("files", []):
                if not isinstance(entry, dict) or "path" not in entry:
                    raise RegistryError("%s has a file entry without a path: %r"
                                        % (shipped_path, entry))
                shipped_files.append(str(entry["path"]))
        if not roots:
            raise RegistryError("registry %s lists no protected roots: every write is refused"
                                % roots_file)
        self.roots = sorted(set(roots))
        self._roots_n = sorted(set(self._normalize_listed(r) for r in roots))
        self._root_ids = {}
        for root_n in self._roots_n:
            ident = _identity(root_n)
            if ident is not None:
                self._root_ids[ident] = root_n
        self._files_n = set(self._normalize_listed(f) for f in shipped_files)
        self._registry_n = self._normalize_listed(self.registry_dir)
        self._registry_id = _identity(self._registry_n)
        self._engine_files_n = set(os.path.normcase(os.path.join(self._registry_n, name))
                                   for name in ENGINE_WRITTEN_REGISTRY_FILES)
        self.n_shipped_files = len(shipped_files)

    def _normalize_listed(self, path):
        try:
            return normalize(path)
        except _Unresolvable as exc:
            raise RegistryError("the registry lists %r, which does not resolve to a plain local "
                                "path (%s)" % (path, exc)) from exc

    def is_protected(self, path):
        """True if ``assert_writable`` would refuse ``path``."""
        try:
            self.assert_writable(path)
        except RegistryRefusal:
            return True
        return False

    def assert_writable(self, path):
        """Return the resolved path to create, or raise RegistryRefusal for a protected location."""
        try:
            canon = canonical(path)
        except _Unresolvable as exc:
            raise RegistryRefusal(
                "G-NOOVERWRITE", "%s cannot be checked against the shipped registry: %s." % (path, exc),
                fix="use a plain local drive path such as the machine file's run root") from None
        path_n = os.path.normcase(canon)
        for root_n in self._roots_n:
            if _is_within(path_n, root_n):
                raise RegistryRefusal(
                    "G-NOOVERWRITE", "%s is under the protected (shipped) root %s." % (path, root_n),
                    fix="choose a run root outside every root in %s" % PROTECTED_ROOTS_FILE)
        ancestors = [(a, _identity(str(a))) for a in _existing_ancestors(canon)]
        for ancestor, ident in ancestors:
            if ident is not None and ident in self._root_ids:
                raise RegistryRefusal(
                    "G-NOOVERWRITE", "%s resolves into the protected (shipped) root %s through %s "
                    "(same volume and file index)." % (path, self._root_ids[ident], ancestor),
                    fix="choose a run root outside every root in %s" % PROTECTED_ROOTS_FILE)
        if path_n in self._files_n:
            raise RegistryRefusal("G-NOOVERWRITE", "%s is a registered shipped file." % path,
                                  fix="write a new file elsewhere")
        if path_n not in self._engine_files_n:
            in_registry = _is_within(path_n, self._registry_n)
            if not in_registry and self._registry_id is not None:
                in_registry = any(ident == self._registry_id for _, ident in ancestors)
            if in_registry:
                raise RegistryRefusal(
                    "G-NOOVERWRITE", "%s is inside the registry folder %s, which holds the shipped "
                    "list and its backups; the engine writes only %s there."
                    % (path, self._registry_n, ", ".join(ENGINE_WRITTEN_REGISTRY_FILES)),
                    fix="choose a run root outside the registry folder")
        if os.path.isfile(canon):
            try:
                links = os.stat(canon).st_nlink
            except OSError:
                links = 1
            if links > 1:
                raise RegistryRefusal(
                    "G-NOOVERWRITE", "%s has %d hard links; it may be a shipped file under another "
                    "name." % (path, links), fix="write a new file elsewhere")
        return Path(canon)
