"""G-IMPORT: importing treeroute imports no dataset code, no harness and no legacy script, reads no
argv, changes no environment variable and patches nothing. The light entry modules also must not
load numpy, or the launcher's thread pins would come too late.

Each check runs in a fresh interpreter. The research folder that holds the legacy scripts is put on
sys.path first, so an accidental import of a legacy module would succeed and be caught.
"""

import ast
import json

import pytest

from conftest import REPO_PARENT, run_python

FORBIDDEN_PREFIXES = ("adaptation", "pm25_", "fire_", "coral_", "defo_", "ndvi_", "legacy_harness",
                      "desertflow", "cross_region", "type3")

SPY = """
import json, os, sys
sys.path.insert(0, %r)

class ArgvSpy(list):
    touched = []
    def _t(self, what):
        ArgvSpy.touched.append(what)
    def __getitem__(self, i):
        self._t('getitem'); return list.__getitem__(self, i)
    def __iter__(self):
        self._t('iter'); return list.__iter__(self)
    def __len__(self):
        self._t('len'); return list.__len__(self)
    def __contains__(self, x):
        self._t('contains'); return list.__contains__(self, x)
    def copy(self):
        self._t('copy'); return list.copy(self)

sys.argv = ArgvSpy(['prog', '--cells', '5', '--smoke'])
env_before = dict(os.environ)
before = set(sys.modules)
""" % str(REPO_PARENT)


def _run(body):
    proc = run_python(SPY + body)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")][-1]
    return json.loads(line[len("RESULT "):])


def test_light_entry_modules_do_not_load_numpy_or_touch_argv_or_env():
    res = _run("""
import treeroute, treeroute.launch, treeroute.engine_constants, treeroute.errors
import treeroute.__main__
new = sorted(set(sys.modules) - before)
print('RESULT ' + json.dumps({
    'numeric': [m for m in ('numpy', 'scipy', 'sklearn', 'sklearnex', 'daal4py', 'pandas')
                if m in sys.modules],
    'argv_touched': ArgvSpy.touched,
    'env_changed': sorted(k for k in set(os.environ) | set(env_before)
                          if os.environ.get(k) != env_before.get(k)),
    'new': new}))
""")
    assert res["numeric"] == [], res["numeric"]
    assert res["argv_touched"] == []
    assert res["env_changed"] == []


def test_importing_every_engine_module_stays_clean():
    res = _run("""
import importlib, pathlib
import treeroute
root = pathlib.Path(treeroute.__file__).resolve().parent
names = []
# walk the files ourselves: pkgutil.walk_packages would import treeroute._proposed to descend into it
for path in sorted(root.rglob('*.py')):
    rel = path.relative_to(root)
    if '_proposed' in rel.parts or '__pycache__' in rel.parts:
        continue
    parts = ['treeroute'] + list(rel.with_suffix('').parts)
    if parts[-1] == '__init__':
        parts = parts[:-1]
    name = '.'.join(parts)
    importlib.import_module(name)
    names.append(name)
new = sorted(set(sys.modules) - before)
env_changed = sorted(k for k in set(os.environ) | set(env_before)
                     if os.environ.get(k) != env_before.get(k))
# only asked if an engine import loaded sklearnex; the test never imports it itself
patched = bool(sys.modules['sklearnex'].sklearn_is_patched()) if 'sklearnex' in new else False
print('RESULT ' + json.dumps({
    'imported': names, 'new': new, 'argv_touched': ArgvSpy.touched,
    'env_changed': env_changed, 'sklearn_patched': patched,
    'numeric': [m for m in ('numpy', 'scipy', 'sklearn', 'sklearnex') if m in new]}))
""")
    assert "treeroute.cli" in res["imported"] and "treeroute.runs.tempmem" in res["imported"]
    bad = [m for m in res["new"] if m.split(".")[0].startswith(FORBIDDEN_PREFIXES)]
    assert bad == [], bad
    proposed = [m for m in res["new"] if m.startswith("treeroute._proposed")]
    assert proposed == [], proposed
    assert res["argv_touched"] == [], res["argv_touched"]
    assert res["env_changed"] == [], res["env_changed"]
    assert res["sklearn_patched"] is False


PROPOSED = "_proposed"
IMPORT_CALLS = {"import_module", "__import__", "find_spec", "spec_from_file_location",
                "run_path", "run_module", "load_source"}


def _imported_modules(tree, rel):
    """Absolute names imported by a module at ``rel`` (a treeroute-relative posix path), with
    relative imports resolved against its package."""
    package = ["treeroute"] + list(rel.parts[:-1])  # also right for a package's __init__.py
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[:len(package) - (node.level - 1)] if node.level > 1 else package
                prefix = ".".join(base)
                module = prefix + ("." + node.module if node.module else "")
            else:
                module = node.module or ""
            out.append(module)
            out.extend("%s.%s" % (module, a.name) for a in node.names)
    return out


def _import_calls_naming(tree, needle):
    """Calls like importlib.import_module('treeroute._proposed.x') whose string args name needle."""
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else (
            func.attr if isinstance(func, ast.Attribute) else None)
        if name not in IMPORT_CALLS:
            continue
        for arg in list(node.args) + [k.value for k in node.keywords]:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and needle in arg.value:
                hits.append("%s(%r)" % (name, arg.value))
    return hits


def test_engine_code_has_no_import_of_legacy_or_dataset_modules():
    from conftest import TREEROUTE_DIR

    offenders = []
    for path in sorted(TREEROUTE_DIR.rglob("*.py")):
        rel = path.relative_to(TREEROUTE_DIR)
        if PROPOSED in rel.parts or "__pycache__" in rel.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for mod in _imported_modules(tree, rel):
            if mod.split(".")[0].startswith(FORBIDDEN_PREFIXES):
                offenders.append("%s: import %s" % (rel.as_posix(), mod))
            if PROPOSED in mod.split("."):
                offenders.append("%s: import %s (proposed, unhashed code)" % (rel.as_posix(), mod))
        for call in _import_calls_naming(tree, PROPOSED):
            offenders.append("%s: %s (proposed, unhashed code)" % (rel.as_posix(), call))
    assert offenders == [], offenders


@pytest.mark.parametrize("source,rel", [
    ("import treeroute._proposed.split", "fit/bank.py"),
    ("from treeroute._proposed import split", "fit/bank.py"),
    ("from treeroute import _proposed", "fit/bank.py"),
    ("from .._proposed import split", "fit/bank.py"),
    ("from . import _proposed", "cli.py"),
    ("from ._proposed.split import x", "cli.py"),
])
def test_proposed_import_detector_catches_every_spelling(source, rel):
    from pathlib import PurePosixPath

    mods = _imported_modules(ast.parse(source), PurePosixPath(rel))
    assert any(PROPOSED in m.split(".") for m in mods), mods


def test_proposed_import_call_detector():
    tree = ast.parse("import importlib\nm = importlib.import_module('treeroute._proposed.x')\n")
    assert _import_calls_naming(tree, PROPOSED)
    assert not _import_calls_naming(ast.parse("EXCLUDED = ('_proposed',)\n"), PROPOSED)
