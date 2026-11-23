"""Load a dataset package: closed folder, YAML files through the schema, sha256 includes, fingerprint.

What load does (boilerplate only):
  - refuses any top-level entry the package format does not name (G-NOKNOB, closed folder);
  - reads each YAML file with a loader that refuses duplicate keys (PyYAML keeps the last one
    silently), and validates it against its model in package/schema.py;
  - verifies every included shared store catalog against its declared sha256, then validates it;
  - computes the package fingerprint.

What load does NOT do: any science check (G-CLOSED, G-LAG, G-SPLIT, G-SUPPORT, G-FACTS, ...), any
data read, running any code in ingest/, features/ or type3/.

Package fingerprint = SHA-256 of the canonical JSON of {relative path: sha256} for every file in
the package except data/ (the data are covered by the data manifest, a later item), __pycache__
folders and expected_derived.json (acceptance values for tests; never read by a run), plus
{include path: sha256} of every included store catalog.
"""

import re
from pathlib import Path
from typing import Any, Dict, NamedTuple

import yaml
from pydantic import ValidationError

from treeroute.errors import PackageError
from treeroute.package import schema as S
from treeroute.runs.atomic import dumps_canonical
from treeroute.runs.fingerprint import sha256_bytes, sha256_file

# Plan 1.1 marks only features/, type3/ and tables/ optional; AUDIT_CHECKLIST.md (the signed human
# checks) is part of every package. Its content and signatures are checked by a validator later;
# here only its presence. expected_derived.json holds acceptance values for tests and is optional.
REQUIRED_FILES = ("dataset.yaml", "catalog.yaml", "ban.yaml", "split.yaml", "exceptions.yaml",
                  "AUDIT_CHECKLIST.md")
YAML_FILES = ("dataset.yaml", "catalog.yaml", "ban.yaml", "split.yaml", "exceptions.yaml")
OPTIONAL_FILES = ("expected_derived.json",)
OPTIONAL_DIRS = ("ingest", "features", "type3", "tables", "data")
TABLE_FILES = tuple("%s.parquet" % name for name in S.RESERVED_TABLES)
NOT_FINGERPRINTED_DIRS = ("data", "__pycache__")
NOT_FINGERPRINTED_FILES = ("expected_derived.json",)
EMPTY_ALLOWED = ("exceptions.yaml",)


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys instead of keeping the last one.

    More changes from SafeLoader (YAML 1.1), so values reach the schema as written:
      - dates stay strings (SafeLoader turns an unquoted date into a date object);
      - only true/false are booleans (SafeLoader also reads yes/no/on/off as booleans, so a group
        or column named 'no' would silently become False);
      - integers are plain decimals only: the YAML 1.1 octal ('010' -> 8), hexadecimal
        ('0x1F' -> 31), binary, sexagesimal ('12:30' -> 750) and underscore forms stay strings, and
        the schema then refuses them where a number is expected;
      - floats are plain decimals with an optional exponent ('1e5' and '1.5e-3' are floats; PyYAML
        needs a dot and a signed exponent), plus .inf and .nan; the sexagesimal form stays a string.
    """


# Standard YAML tags, built from PyYAML's own scalar tag (its prefix is the YAML tag namespace).
_TAG_PREFIX = yaml.resolver.BaseResolver.DEFAULT_SCALAR_TAG.rsplit(":", 1)[0] + ":"
_BOOL_TAG = _TAG_PREFIX + "bool"
_TIMESTAMP_TAG = _TAG_PREFIX + "timestamp"
_INT_TAG = _TAG_PREFIX + "int"
_FLOAT_TAG = _TAG_PREFIX + "float"
_REPLACED_TAGS = (_BOOL_TAG, _TIMESTAMP_TAG, _INT_TAG, _FLOAT_TAG)
_UniqueKeyLoader.yaml_implicit_resolvers = {
    first: [(tag, rx) for tag, rx in resolvers if tag not in _REPLACED_TAGS]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_UniqueKeyLoader.add_implicit_resolver(
    _BOOL_TAG, re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF"))
_UniqueKeyLoader.add_implicit_resolver(
    _INT_TAG, re.compile(r"^[-+]?(?:0|[1-9][0-9]*)$"), list("-+0123456789"))
_UniqueKeyLoader.add_implicit_resolver(
    _FLOAT_TAG, re.compile(r"""^(?:[-+]?(?:[0-9]+\.[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?
                              |[-+]?[0-9]+[eE][-+]?[0-9]+
                              |[-+]?\.(?:inf|Inf|INF)
                              |\.(?:nan|NaN|NAN))$""", re.X),
    list("-+0123456789."))


def _plain_number_error(node, kind):
    return yaml.constructor.ConstructorError(
        None, None, "%r is not a plain decimal %s (write it as a plain decimal, or quote it to "
        "keep it a string)" % (node.value, kind), node.start_mark)


def _construct_plain_int(loader, node):
    text = loader.construct_scalar(node)
    if not re.match(r"^[-+]?(?:0|[1-9][0-9]*)$", text):  # an explicit int tag on another form
        raise _plain_number_error(node, "integer")
    return int(text)


def _construct_plain_float(loader, node):
    text = loader.construct_scalar(node).lower()
    if text.endswith(".inf"):
        return float("-inf") if text.startswith("-") else float("inf")
    if text == ".nan":
        return float("nan")
    try:
        return float(text)
    except ValueError:
        raise _plain_number_error(node, "float") from None


_UniqueKeyLoader.add_constructor(_INT_TAG, _construct_plain_int)
_UniqueKeyLoader.add_constructor(_FLOAT_TAG, _construct_plain_float)


def _construct_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in seen
        except TypeError:
            raise yaml.constructor.ConstructorError(
                None, None, "unhashable key %r" % (key,), key_node.start_mark)
        if duplicate:
            raise yaml.constructor.ConstructorError(
                None, None, "duplicate key %r" % (key,), key_node.start_mark)
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def load_yaml(path):
    """Parse a UTF-8 YAML file, refusing duplicate keys. An empty file gives None."""
    path = Path(path)
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PackageError("%s is not UTF-8 text: %s" % (path, exc)) from exc
    try:
        return yaml.load(text, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise PackageError("%s is not valid YAML: %s" % (path, exc)) from exc


def validate_file(path, model, empty_allowed=False):
    """Load one YAML file and validate it against ``model``."""
    data = load_yaml(path)
    if data is None:
        if not empty_allowed:
            raise PackageError("%s is empty" % path)
        data = {}
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise PackageError("%s is invalid:\n%s" % (path, exc)) from exc


class LoadedPackage(NamedTuple):
    root: Path
    dataset: S.DatasetFile
    catalog: S.PackageCatalog
    ban: S.BanFile
    split: S.SplitFile
    exceptions: S.ExceptionsFile
    stores: Dict[str, S.StoreCatalog]
    file_hashes: Dict[str, str]
    include_hashes: Dict[str, str]
    fingerprint: str


def check_closed_folder(root):
    """Refuse any top-level entry, or tables/ file, that the package format does not name."""
    root = Path(root)
    problems = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        name = entry.name
        if name == "__pycache__":
            continue
        if entry.is_dir():
            if name not in OPTIONAL_DIRS:
                problems.append("unknown folder %s/" % name)
        elif name not in REQUIRED_FILES and name not in OPTIONAL_FILES:
            problems.append("unknown file %s" % name)
    for name in REQUIRED_FILES:
        if not (root / name).is_file():
            problems.append("missing required file %s" % name)
    tables = root / "tables"
    if tables.is_dir():
        for entry in sorted(tables.iterdir(), key=lambda p: p.name):
            if entry.name not in TABLE_FILES:
                problems.append("unknown table tables/%s (allowed: %s)"
                                % (entry.name, ", ".join(TABLE_FILES)))
    if problems:
        raise PackageError("package %s is not a closed package folder (G-NOKNOB): %s"
                           % (root, "; ".join(problems)))


def package_file_hashes(root):
    """{relative posix path: sha256} for every fingerprinted file of the package, sorted."""
    root = Path(root)
    out = {}
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if rel.parts[0] in NOT_FINGERPRINTED_DIRS or "__pycache__" in rel.parts:
            continue
        if rel.as_posix() in NOT_FINGERPRINTED_FILES:
            continue
        out[rel.as_posix()] = sha256_file(path)
    return out


def package_fingerprint(file_hashes, include_hashes):
    payload = {"files": file_hashes, "includes": include_hashes}
    return sha256_bytes(dumps_canonical(payload).encode("ascii"))


def load_includes(root, dataset):
    """Verify each included store catalog's sha256, then validate it. Returns (stores, hashes)."""
    stores = {}
    hashes = {}
    for inc in dataset.includes:
        path = (Path(root) / inc.path).resolve()
        if not path.is_file():
            raise PackageError("included store catalog %s (%s) is missing" % (inc.path, path))
        actual = sha256_file(path)
        if actual != inc.sha256:
            raise PackageError(
                "included store catalog %s has sha256 %s, but dataset.yaml declares %s. The shared "
                "catalog changed: review the change, then update the declared hash."
                % (inc.path, actual, inc.sha256))
        if inc.path in stores:
            raise PackageError("store catalog %s is included twice" % inc.path)
        stores[inc.path] = validate_file(path, S.StoreCatalog)
        hashes[inc.path] = actual
    return stores, hashes


def load_package(path):
    """Load and fingerprint a package. Raises PackageError on the first structural problem."""
    root = Path(path).resolve()
    if not root.is_dir():
        raise PackageError("package folder %s does not exist" % root)
    check_closed_folder(root)
    parsed: Dict[str, Any] = {}
    for name, model in S.PACKAGE_FILE_MODELS.items():
        parsed[name] = validate_file(root / name, model, empty_allowed=name in EMPTY_ALLOWED)
    if set(S.PACKAGE_FILE_MODELS) != set(YAML_FILES):
        raise PackageError("internal: the YAML file list and the schema models disagree")
    dataset = parsed["dataset.yaml"]
    stores, include_hashes = load_includes(root, dataset)
    file_hashes = package_file_hashes(root)
    return LoadedPackage(
        root=root,
        dataset=dataset,
        catalog=parsed["catalog.yaml"],
        ban=parsed["ban.yaml"],
        split=parsed["split.yaml"],
        exceptions=parsed["exceptions.yaml"],
        stores=stores,
        file_hashes=file_hashes,
        include_hashes=include_hashes,
        fingerprint=package_fingerprint(file_hashes, include_hashes),
    )


def load_dataset_file(path):
    """Only dataset.yaml (enough for ``status``, which needs the package name)."""
    root = Path(path).resolve()
    return validate_file(root / "dataset.yaml", S.DatasetFile)
