"""Fingerprints: file hashes, engine code hashes and the run fingerprint.

run fingerprint = SHA-256 of the canonical JSON of
    {resolved config, ordered engine module code hashes, library versions, Python version}.

Engine module code is hashed with comments stripped (tokenize drops COMMENT and NL tokens), so an
origin comment can change without moving a fingerprint while any code change does. Every ``.py``
file under treeroute/ is hashed in sorted order, except ``_proposed/`` (proposed signatures, not
engine code) and ``__pycache__``. The machine file (config/machine.yaml) is outside the engine and
is not hashed here; its paths go into the manifest.
"""

import hashlib
import io
import platform
import sys
import tokenize
from pathlib import Path

from treeroute.runs.atomic import dumps_canonical

ENGINE_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = ("_proposed", "__pycache__")

# Distribution names whose versions enter the fingerprint (read from metadata, never imported).
VERSIONED_DISTRIBUTIONS = (
    "numpy", "scipy", "scikit-learn", "scikit-learn-intelex", "daal", "tbb", "pandas", "pyarrow",
    "threadpoolctl", "pydantic", "pydantic-core", "typer", "click", "PyYAML", "psutil",
)
# tbb is oneDAL's threading layer, so its version is part of what a forest computes.

# Proposed signatures live in treeroute/_proposed/ until the owner signs them. They are not engine
# code: not hashed, not scanned. A run must never execute them.
PROPOSED_PACKAGE = "treeroute._proposed"

_SKIP_TOKENS = (tokenize.COMMENT, tokenize.NL, tokenize.ENCODING)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def code_hash(source_bytes):
    """SHA-256 of Python source with comments and blank lines stripped (token stream)."""
    tokens = []
    for tok in tokenize.tokenize(io.BytesIO(source_bytes).readline):
        if tok.type in _SKIP_TOKENS:
            continue
        tokens.append([tokenize.tok_name[tok.type], tok.string])
    return sha256_bytes(dumps_canonical(tokens).encode("ascii"))


def module_code_hash(path):
    with open(path, "rb") as fh:
        return code_hash(fh.read())


def engine_module_files(root=None):
    """Every engine ``.py`` file, sorted by its path relative to treeroute/."""
    root = Path(root) if root is not None else ENGINE_ROOT
    files = []
    for path in root.rglob("*.py"):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def engine_code_hashes(root=None):
    """{relative posix path: comment-stripped code hash}, in sorted order."""
    root = Path(root) if root is not None else ENGINE_ROOT
    return {p.relative_to(root).as_posix(): module_code_hash(p) for p in engine_module_files(root)}


def engine_code_hash(root=None):
    return sha256_bytes(dumps_canonical(engine_code_hashes(root)).encode("ascii"))


def loaded_engine_modules():
    """Sorted names of the treeroute modules loaded in this process (for the manifest)."""
    return sorted(name for name in sys.modules if name == "treeroute" or name.startswith("treeroute."))


def loaded_proposed_modules():
    """Loaded modules from treeroute/_proposed/ (unhashed, unscanned code)."""
    return sorted(name for name in sys.modules
                  if name == PROPOSED_PACKAGE or name.startswith(PROPOSED_PACKAGE + "."))


def assert_no_proposed_code_loaded():
    """Refuse a fingerprinted run while any proposed (unsigned, unhashed) module is loaded."""
    loaded = loaded_proposed_modules()
    if loaded:
        from treeroute.errors import RefusedError

        raise RefusedError("G-FINGERPRINT", "proposed modules are loaded in this process: %s. They "
                           "are not engine code, so no fingerprint covers them."
                           % ", ".join(loaded),
                           fix="move a signed module into the engine before a run uses it")


def library_versions():
    """Installed versions of the numeric and plumbing libraries (from metadata; nothing imported)."""
    from importlib import metadata

    out = {}
    for dist in VERSIONED_DISTRIBUTIONS:
        try:
            out[dist] = metadata.version(dist)
        except metadata.PackageNotFoundError:
            out[dist] = None
    return out


def run_fingerprint(config, root=None):
    """SHA-256 of the resolved config plus the ordered engine code, library versions and Python."""
    payload = {
        "config": config,
        "engine_code": engine_code_hashes(root),
        "versions": library_versions(),
        "python": platform.python_version(),
    }
    return sha256_bytes(dumps_canonical(payload).encode("ascii"))


def engine_code_sha256(root=None):
    """SHA-256 of the engine's code as FILES (the check report contract, shared by treeroute/check and
    treeroute_report): the canonical JSON of the sorted [relative posix path, sha256 of the file's bytes] list
    of every ``.py`` file under treeroute/, except ``_proposed/`` and ``__pycache__`` (engine_module_files).
    Unlike engine_code_hash, comments count: any byte change in an engine file moves it."""
    root = Path(root) if root is not None else ENGINE_ROOT
    pairs = [[p.relative_to(root).as_posix(), sha256_file(p)] for p in engine_module_files(root)]
    return sha256_bytes(dumps_canonical(pairs).encode("ascii"))
