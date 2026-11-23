"""Toy runs, toy configs, the read spy and the ONE place where the tests call the rival code.

Every call into rivals.export / rivals.harness / rivals.models goes through an adapter here, so a signature the
builders settle differently is fixed in one place. Hooks the spec does not fix are requested in
D:/treeroute/rivals_build/BUILD_NOTES_tests.md; `need()` fails a test with the request number when one is missing.

Toy runs (SPEC_RIVALS.md 4.1): the engine's own toy builders, imported read-only from the engine's tests folder:
grid per-unit toy (tests/test_pipeline.py make_pipeline_package, kind smoke; variants ok, sparse, decline) and
the table toy (tests/table_toy.py build_toy_table_package; variants ok, donor_only_group). Each toy gets two
machine files: the RUN machine (the engine run writes its run folder) and the EXPORT machine, whose registry
protects the toy's run root and package, so any write of the rival code into a run or a package is refused by
the engine's own registry (runs/registry.py:195).
"""

import builtins
import contextlib
import datetime as _dt
import hashlib
import io
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pytest

TESTS_DIR = Path(__file__).resolve().parent
BUILD_ROOT = TESTS_DIR.parents[1]
ENGINE_ROOT = Path(os.environ.get("RIVALS_ENGINE_ROOT",
                                  r"C:\Users\<user>\Desktop\data set for reserch paper\engine"))
ENGINE_TESTS = ENGINE_ROOT / "tests"
NOTES = BUILD_ROOT / "BUILD_NOTES_tests.md"

FAKE_LAUNCH = {"test_only": True, "env_pins": {"OMP_NUM_THREADS": "4"},
               "backend": {"sklearn_patched": True, "onedal_threads": 4}}

ROLE_FLAGS = ("r_refit", "r_tune", "r_inner", "r_guardfit", "r_guard")
LEARNERS_ALL = ("ridge", "rf", "lgbm", "lgbm_tweedie", "hgb_l1")
CHECK_IDS_I = tuple("I%d" % i for i in range(1, 10))
CHECK_IDS_P = tuple("P%d" % i for i in range(1, 15))


# ------------------------------------------------------------------------------------------ small helpers
def need(module: Any, name: str, item: str) -> Any:
    """getattr, or fail the test naming the BUILD_NOTES_tests.md request that asks for the hook."""
    if not hasattr(module, name):
        pytest.fail("%s.%s is missing: requested in %s item %s" % (module.__name__, name, NOTES, item))
    return getattr(module, name)


def rivals_export():
    import rivals.export as X
    return X


def rivals_harness():
    import rivals.harness as H
    return H


def rivals_models():
    import rivals.models as M
    return M


def sha256_file(path: Any) -> str:
    h = hashlib.sha256()
    with io.open(str(path), "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Any) -> Any:
    with io.open(str(path), "r", encoding="utf-8") as fh:
        return json.load(fh)


def utc_stamp() -> str:
    return _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")


def move_aside(path: Path, moved_root: Path) -> Path:
    """Never delete: a file or folder the test must take away is moved under moved_root/<utc stamp>/."""
    dest = Path(moved_root) / utc_stamp() / Path(path).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(dest))
    return dest


def read_parquet(path: Any, columns: Optional[Sequence[str]] = None):
    import pyarrow.parquet as pq
    return pq.read_table(str(path), columns=list(columns) if columns is not None else None).to_pandas()


def parquet_columns(path: Any) -> List[str]:
    import pyarrow.parquet as pq
    return list(pq.read_schema(str(path)).names)


def check_id_in(text: str, check: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9])%s(?![0-9])" % re.escape(check), text) is not None


def expect_refusal(check: str, fn: Callable, *args: Any, **kwargs: Any) -> str:
    """fn must refuse naming `check` (e.g. 'I2', 'P6', 'heavy'): by raising (the message names it) or, for a
    main(argv) -> int, by a non-zero return with the message on stdout/stderr. Returns the message."""
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = fn(*args, **kwargs)
    except SystemExit as exc:                         # argparse-style exits count as a return code
        rc = exc.code
        text = out.getvalue() + err.getvalue() + str(exc)
    except BaseException as exc:                      # noqa: B902 - any refusal type counts; the message decides
        text = "%s: %s\n%s%s" % (type(exc).__name__, exc, out.getvalue(), err.getvalue())
        assert check_id_in(text, check) or check.lower() in text.lower(), (
            "refused, but the message does not name %r:\n%s" % (check, text))
        return text
    else:
        text = out.getvalue() + err.getvalue()
    assert rc not in (0, None), "expected a refusal naming %r, the call returned %r:\n%s" % (check, rc, text)
    assert check_id_in(text, check) or check.lower() in text.lower(), (
        "refused (rc %r), but the output does not name %r:\n%s" % (rc, check, text))
    return text


# ------------------------------------------------------------------------------------------ toy runs
@dataclass
class Toy:
    name: str
    kind: str                       # 'grid' or 'table'
    variant: str
    base: Path
    package: Path
    run: Path
    config: Path                    # the toy's rivals.yaml (export machine, export/out/moved roots under base)
    machine_file: Path
    temp_dir: Path
    export_root: Path
    export_ckpt_root: Path
    out_root: Path
    moved_root: Path
    leads: Tuple[int, ...]
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def run_name(self) -> str:
        return self.run.name

    @property
    def package_name(self) -> str:
        return read_json(self.run / "manifest.json")["config"]["package"]

    def derived(self) -> Dict[str, Any]:
        return read_json(self.run / "derived.json")

    def cuts(self, lead: int) -> Dict[str, int]:
        v = self.derived()["R11"]["value"][str(int(lead))]
        return {"fit_cut": int(v["fit_cut"]), "guard_cut": int(v["guard_cut"])}

    def links(self) -> List[str]:
        return list(self.derived()["R22"]["value"])

    def c(self, lead: int) -> Optional[float]:
        d = self.derived()
        key = "R23:lead=%d" % int(lead)
        return float(d[key]["value"]) if key in d and d[key]["value"] is not None else None

    def legal(self) -> Tuple[float, float]:
        t = read_parquet(self.run / "test_preds.parquet", ["legal_min", "legal_max"])
        return float(t["legal_min"].iloc[0]), float(t["legal_max"].iloc[0])

    def saved_test_preds(self, lead: int) -> Path:
        return self.run / "test_preds.parquet" if lead == 0 else \
            self.run / "ladder" / ("lead_%d" % lead) / "test_preds.parquet"


def engine_grid_toy():
    """The engine's grid toy module (tests/test_pipeline.py), imported read-only."""
    import importlib
    mod = importlib.import_module("conftest")
    if Path(getattr(mod, "__file__", "")).resolve().parent != ENGINE_TESTS.resolve():
        raise RuntimeError("the module 'conftest' in sys.modules is %s, not the engine's tests/conftest.py; "
                           "the engine toy builders need the engine's" % getattr(mod, "__file__", None))
    return importlib.import_module("test_pipeline")


def engine_table_toy():
    import importlib
    engine_grid_toy()                     # the same 'conftest' check
    return importlib.import_module("table_toy")


def write_registry(folder: Path, protected: Sequence[Path]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "protected_roots.txt").write_text(
        "# rival test registry\n" + "\n".join(Path(p).as_posix() for p in protected) + "\n", encoding="utf-8")
    return folder


def write_machine_yaml(path: Path, run_root: Path, temp_dir: Path, registry_dir: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("run_root: '%s'\ntemp_dir: '%s'\nregistry_dir: '%s'\n"
                    % (Path(run_root).as_posix(), Path(temp_dir).as_posix(), Path(registry_dir).as_posix()),
                    encoding="utf-8")
    return path


def write_rivals_yaml(path: Path, machine_file: Path, export_root: Path, export_ckpt_root: Path, out_root: Path,
                      moved_root: Path, engine_root: Path = ENGINE_ROOT) -> Path:
    """The six keys of SPEC_RIVALS.md 1.1, every path absolute."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["engine_root: '%s'" % Path(engine_root).as_posix(),
             "machine_file: '%s'" % Path(machine_file).as_posix(),
             "export_root: '%s'" % Path(export_root).as_posix(),
             "export_ckpt_root: '%s'" % Path(export_ckpt_root).as_posix(),
             "out_root: '%s'" % Path(out_root).as_posix(),
             "moved_root: '%s'" % Path(moved_root).as_posix()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _run_machine(base: Path):
    from types import SimpleNamespace
    shipped = base / "shipped_root"
    shipped.mkdir(parents=True, exist_ok=True)
    reg = write_registry(base / "registry_run", [shipped])
    (base / "temp").mkdir(exist_ok=True)
    return SimpleNamespace(run_root=str(base / "runs"), temp_dir=str(base / "temp"), registry_dir=str(reg))


def _finish(base: Path, kind: str, variant: str, pkg: Path, run: Path) -> Toy:
    """Write the export machine (registry protecting the run root and the package) and the toy's rivals.yaml."""
    reg = write_registry(base / "registry_export", [base / "shipped_root", base / "runs", pkg])
    machine = write_machine_yaml(base / "machine_export.yaml", base / "runs_export_unused", base / "temp", reg)
    export_root = base / "_export"
    ckpt = export_root / "_engine_run_root"
    out_root = base / "_out"
    moved = base / "_moved"
    cfg = write_rivals_yaml(base / "rivals.yaml", machine, export_root, ckpt, out_root, moved)
    derived = read_json(run / "derived.json")
    leads = tuple(sorted(int(k) for k in derived["R11"]["value"]))
    toy = Toy(name="%s_%s" % (kind, variant), kind=kind, variant=variant, base=base, package=pkg, run=run,
              config=cfg, machine_file=machine, temp_dir=base / "temp", export_root=export_root,
              export_ckpt_root=ckpt, out_root=out_root, moved_root=moved, leads=leads)
    toy.extra["snapshot"] = snapshot(toy)
    return toy


def snapshot(toy: Toy) -> Dict[str, Tuple[int, int]]:
    """{relative path: (size, mtime_ns)} of every file under the toy's run folder and package (no __pycache__)."""
    out = {}
    for root in (toy.run, toy.package):
        for p in sorted(Path(root).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                st = os.stat(p)
                out[str(p)] = (int(st.st_size), int(st.st_mtime_ns))
    return out


def build_grid_toy(base: Path, variant: str = "ok") -> Toy:
    """The engine's grid per-unit toy, kind smoke (variants: ok, sparse = R12 fallback units, decline = a declined
    nowcast and every lead's guard failing, made as the engine test makes it: n2_eligible stood in as False)."""
    G = engine_grid_toy()
    opts = {"ok": {}, "sparse": {"sparse": True}, "decline": {"decline": True}}[variant]
    pkg = G.make_pipeline_package(base / "pk", name="synth_%s" % variant, **opts)
    from treeroute.pipeline.run import run_pipeline
    with pytest.MonkeyPatch.context() as mp:
        if variant == "decline":
            from treeroute.layer import decide as LD
            mp.setattr(LD, "n2_eligible", lambda arm_mae, own_trees_off_mae: False)
        run = Path(run_pipeline(pkg, base / "runs", "smoke", machine=_run_machine(base), echo=lambda s: None,
                                launch_record=FAKE_LAUNCH))
    return _finish(base, "grid", variant, pkg, run)


def build_table_toy(base: Path, variant: str = "ok") -> Toy:
    TT = engine_table_toy()
    pkg = TT.build_toy_table_package(base / "pk", variant)
    from treeroute.pipeline.run import run_pipeline
    run = Path(run_pipeline(pkg, base / "runs", "smoke", machine=_run_machine(base), echo=lambda s: None,
                            launch_record=FAKE_LAUNCH))
    return _finish(base, "table", variant, pkg, run)


def copy_run(toy: Toy, case: str) -> Path:
    """A copy of the toy's run folder under base/run_copies/<case>/ with the same folder name (for the parity
    refusals that edit a run file; the original is never touched)."""
    dest = toy.base / "run_copies" / case / toy.run.name
    shutil.copytree(str(toy.run), str(dest))
    return dest


# ------------------------------------------------------------------------------------------ the read spy (T1)
class ReadSpy(object):
    """Records every read of a file through pyarrow / pandas / open while active: (how, path, columns, mode).

    Spied: pyarrow.parquet.read_table / read_pandas / ParquetFile (init and read) / read_schema,
    pyarrow.dataset.dataset, pandas.read_parquet / read_csv, builtins.open and io.open. A reader bound by
    `from x import y` before the spy starts is not seen (the rival code is asked to call through the module,
    BUILD_NOTES item B2). The engine's LabelView.open_test_labels is replaced by a recorder that refuses."""

    def __init__(self) -> None:
        self.calls: List[Tuple[str, str, Optional[Tuple[str, ...]], str]] = []
        self.test_label_opens: List[Tuple[Any, ...]] = []
        self._mp: Optional[pytest.MonkeyPatch] = None
        self._depth = 0

    @staticmethod
    def _path(source: Any) -> str:
        if isinstance(source, (str, os.PathLike)):
            return str(Path(source))
        return "<%s>" % type(source).__name__

    def _rec(self, how: str, source: Any, columns: Any = None, mode: str = "rb") -> None:
        if self._depth:                   # a reader called by another spied reader: the outer call is the record
            return
        cols = tuple(columns) if columns is not None else None
        self.calls.append((how, self._path(source), cols, mode))

    def _wrap(self, how: str, fn: Callable, columns_of: Callable, mode_of: Callable = lambda a, kw: "rb",
              path_only: bool = False) -> Callable:
        spy = self

        def wrapped(source, *a, **kw):
            if not (path_only and not isinstance(source, (str, os.PathLike))):
                spy._rec(how, source, columns_of(a, kw), mode_of(a, kw))
            spy._depth += 1
            try:
                return fn(source, *a, **kw)
            finally:
                spy._depth -= 1
        return wrapped

    def __enter__(self) -> "ReadSpy":
        import pandas as pd
        import pyarrow.dataset as pds
        import pyarrow.parquet as pq
        from treeroute.labels import vault

        mp = pytest.MonkeyPatch()
        self._mp = mp
        spy = self
        o_rt, o_rp, o_rs = pq.read_table, pq.read_pandas, pq.read_schema
        o_pf_init, o_pf_read = pq.ParquetFile.__init__, pq.ParquetFile.read
        o_ds, o_pd_rp, o_pd_csv = pds.dataset, pd.read_parquet, pd.read_csv
        o_open, o_io_open = builtins.open, io.open

        cols_kw = lambda a, kw: kw.get("columns", a[0] if a else None)          # noqa: E731
        read_table = spy._wrap("pq.read_table", o_rt, cols_kw)
        read_pandas = spy._wrap("pq.read_pandas", o_rp, cols_kw)
        read_schema = spy._wrap("pq.read_schema", o_rs, lambda a, kw: ())
        dataset = spy._wrap("pyarrow.dataset", o_ds, lambda a, kw: None)
        pd_read_parquet = spy._wrap("pd.read_parquet", o_pd_rp, lambda a, kw: kw.get("columns"))
        pd_read_csv = spy._wrap("pd.read_csv", o_pd_csv, lambda a, kw: kw.get("usecols"))
        mode_kw = lambda a, kw: kw.get("mode", a[0] if a else "r")                # noqa: E731
        spy_open = spy._wrap("open", o_open, lambda a, kw: None, mode_kw, path_only=True)
        spy_io_open = spy._wrap("io.open", o_io_open, lambda a, kw: None, mode_kw, path_only=True)

        def pf_init(self_, source, *a, **kw):
            self_._rivals_spy_source = spy._path(source)
            spy._depth += 1
            try:
                return o_pf_init(self_, source, *a, **kw)
            finally:
                spy._depth -= 1

        def pf_read(self_, *a, **kw):
            spy._rec("pq.ParquetFile.read", getattr(self_, "_rivals_spy_source", "<?>"),
                     kw.get("columns", a[0] if a else None))
            spy._depth += 1
            try:
                return o_pf_read(self_, *a, **kw)
            finally:
                spy._depth -= 1

        def no_test_labels(self_, *a, **kw):
            spy.test_label_opens.append(a)
            raise AssertionError("LabelView.open_test_labels was called (SPEC_RIVALS.md 2.6)")

        mp.setattr(pq, "read_table", read_table)
        mp.setattr(pq, "read_pandas", read_pandas)
        mp.setattr(pq, "read_schema", read_schema)
        mp.setattr(pq.ParquetFile, "__init__", pf_init)
        mp.setattr(pq.ParquetFile, "read", pf_read)
        mp.setattr(pds, "dataset", dataset)
        mp.setattr(pd, "read_parquet", pd_read_parquet)
        mp.setattr(pd, "read_csv", pd_read_csv)
        mp.setattr(builtins, "open", spy_open)
        mp.setattr(io, "open", spy_io_open)
        mp.setattr(vault.LabelView, "open_test_labels", no_test_labels)
        return self

    def __exit__(self, *exc: Any) -> bool:
        assert self._mp is not None
        self._mp.undo()
        return False

    # ---- verdicts
    @staticmethod
    def _is_read(mode: str) -> bool:
        return not any(ch in mode for ch in "wxa+")

    def test_file_reads(self, export_root: Path, decoded_only: bool) -> List[Tuple[Any, ...]]:
        """Reads of any file inside an export lead's test/ folder. decoded_only=True counts only parquet decodes
        (pyarrow / pandas), not raw byte opens (hashing a written file)."""
        root = os.path.normcase(os.path.abspath(str(export_root)))
        out = []
        for how, path, cols, mode in self.calls:
            if path.startswith("<"):
                continue
            p = os.path.normcase(os.path.abspath(path))
            if not p.startswith(root + os.sep):
                continue
            if "test" not in Path(os.path.relpath(p, root)).parts[:-1]:
                continue
            if how in ("open", "io.open"):
                if not self._is_read(mode) or decoded_only:
                    continue
            out.append((how, path, cols, mode))
        return out

    def test_y_requests(self) -> List[Tuple[Any, ...]]:
        """Reads of a saved test_preds.parquet that asked for y, asked for every column, or opened it raw."""
        out = []
        for how, path, cols, mode in self.calls:
            if Path(path).name != "test_preds.parquet":
                continue
            if how in ("open", "io.open"):
                if self._is_read(mode):
                    out.append((how, path, cols, mode))
                continue
            if how == "pq.read_schema":
                continue
            if cols is None or "y" in cols:
                out.append((how, path, cols, mode))
        return out


# ------------------------------------------------------------------------------------------ export adapters
def export_run(toy: Toy, leads: Sequence[int], roles: Optional[Sequence[str]] = None,
               run: Optional[Path] = None, package: Optional[Path] = None,
               config: Optional[Path] = None, resume: bool = False) -> List[Path]:
    """export.export_run(run, package, leads, roles, config) -> list[Path] (SPEC_RIVALS.md section 5); leads as a
    comma text (builder A reads 'all', one lead or a comma list)."""
    X = rivals_export()
    fn = need(X, "export_run", "A2")
    out = fn(Path(run or toy.run), Path(package or toy.package), ",".join(str(int(L)) for L in leads),
             list(roles) if roles is not None else None, Path(config or toy.config), resume=resume)
    return [Path(p) for p in out]


def export_main(toy: Toy, lead: str = "all", extra: Sequence[str] = (), run: Optional[Path] = None) -> int:
    X = rivals_export()
    fn = need(X, "main", "A2")
    argv = ["--run", str(run or toy.run), "--package", str(toy.package), "--lead", str(lead),
            "--config", str(toy.config), "--resume"] + list(extra)
    return fn(argv)


def export_lead_dir(toy: Toy, lead: int) -> Path:
    """<export_root>/<package>/<run_name>/lead_<L>/ (SPEC_RIVALS.md 1.2)."""
    return toy.export_root / toy.package_name / toy.run_name / ("lead_%d" % int(lead))


def export_all_via_main(toy: Toy) -> Dict[int, Path]:
    rc = export_main(toy, "all")
    assert rc == 0, "export.main returned %r" % rc
    dirs = {L: export_lead_dir(toy, L) for L in toy.leads}
    for L, d in dirs.items():
        assert (d / "export_manifest.json").is_file(), "no export_manifest.json in %s" % d
    return dirs


@dataclass
class SpiedExport:
    dirs: Dict[int, Path]
    spy: ReadSpy


def export_with_spy(toy: Toy) -> SpiedExport:
    with ReadSpy() as spy:
        dirs = export_run(toy, toy.leads, None)
    by_lead = {}
    for d in dirs:
        m = re.match(r"lead_(\d+)$", d.name)
        assert m, "export_run returned %s, not a lead_<L> folder" % d
        by_lead[int(m.group(1))] = d
    assert sorted(by_lead) == sorted(toy.leads), (sorted(by_lead), toy.leads)
    return SpiedExport(dirs=by_lead, spy=spy)


def export_checks(lead_dir: Path) -> Dict[str, str]:
    """{check id: result} of the P-checks from export_manifest.json. The spec (2.7) asks for 'every P-check with its
    numbers'; builder A records them under 'parity' as {id: {..., 'result': 'pass' | 'printed' | 'skipped: ...'}}
    ('checks' with 'status' is read too)."""
    man = read_json(Path(lead_dir) / "export_manifest.json")
    block = man.get("parity", man.get("checks"))
    if block is None:
        pytest.fail("export_manifest.json has no 'parity' block of P-check results (%s item A5)" % NOTES)
    out = {}
    items = block.items() if isinstance(block, dict) else [(v["id"], v) for v in block]
    for k, v in items:
        if isinstance(v, dict):
            out[str(k)] = str(v.get("result", v.get("status")))
        else:
            out[str(k)] = str(v)
    return out


def train_frames(lead_dir: Path):
    import pandas as pd
    files = sorted((Path(lead_dir) / "train").glob("*.parquet"))
    assert files, "no train/*.parquet in %s" % lead_dir
    return pd.concat([read_parquet(f) for f in files], ignore_index=True)


# ------------------------------------------------------------------------------------------ harness adapters
def h_init(toy: Toy, export_lead0: Path, out_root: Path, extra_learners: Sequence[str] = ()) -> Path:
    H = rivals_harness()
    fn = need(H, "init", "B1")
    out = fn(toy.run, Path(export_lead0), Path(out_root), extra_learners=tuple(extra_learners), config=toy.config)
    assert out is not None, "harness.init must return the out folder (BUILD_NOTES item B1)"
    return Path(out)


def h_tune(toy: Toy, out: Path, resume: bool = True) -> Any:
    return need(rivals_harness(), "tune", "B1")(Path(out), resume=resume, config=toy.config)


def h_lock(toy: Toy, out: Path) -> Any:
    return need(rivals_harness(), "lock", "B1")(Path(out), config=toy.config)


def h_refit(toy: Toy, out: Path, lead: int, resume: bool = True) -> Any:
    return need(rivals_harness(), "refit", "B1")(Path(out), int(lead), resume=resume, config=toy.config)


def h_score(toy: Toy, out: Path, lead: int) -> Any:
    return need(rivals_harness(), "score", "B1")(Path(out), int(lead), config=toy.config)


def h_board(toy: Toy, out: Path) -> Any:
    return need(rivals_harness(), "board", "B1")(Path(out), config=toy.config)


def h_open_test_labels(toy: Toy, out: Path, lead: int) -> Any:
    return need(rivals_harness(), "open_test_labels_rivals", "B1")(Path(out), int(lead), config=toy.config)


@contextlib.contextmanager
def counting_fit_predict(stop_after: Optional[int] = None, transform: Optional[Callable] = None):
    """Wrap models.fit_predict (the harness calls it through the module, item B2): count calls, optionally raise
    before call stop_after + 1 (a crash after trial k), optionally transform each result."""
    M = rivals_models()
    orig = need(M, "fit_predict", "B3")
    box = {"calls": 0}

    class Interrupted(RuntimeError):
        pass

    def wrapped(*a: Any, **kw: Any) -> Any:
        if stop_after is not None and box["calls"] >= stop_after:
            raise Interrupted("test interrupt after %d fits" % stop_after)
        box["calls"] += 1
        res = orig(*a, **kw)
        return transform(res) if transform is not None else res

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(M, "fit_predict", wrapped)
        box["Interrupted"] = Interrupted
        yield box


@dataclass
class Flow:
    toy: Toy
    export: SpiedExport
    out: Path
    spy_pre_lock: Optional[ReadSpy] = None
    spy_refit: Optional[ReadSpy] = None
    fit_calls_tune: int = 0
    pre_lock: Dict[str, str] = field(default_factory=dict)       # step -> 'refused: <msg>' or 'RAN'
    scored_leads: Tuple[int, ...] = ()


def _try(fn: Callable, *a: Any, **kw: Any) -> str:
    try:
        fn(*a, **kw)
    except BaseException as exc:                                 # noqa: B902
        return "refused: %s: %s" % (type(exc).__name__, exc)
    return "RAN"


def run_tune_lock_flow(toy: Toy, export: SpiedExport, out_name: str, extra_learners: Sequence[str] = ("hgb_l1",),
                       spy: bool = False) -> Flow:
    out_root = toy.base / out_name
    reader = ReadSpy() if spy else contextlib.nullcontext()
    with reader as s:
        with counting_fit_predict() as box:
            out = h_init(toy, export.dirs[0], out_root, extra_learners)
            h_tune(toy, out)
            calls = box["calls"]
        flow = Flow(toy=toy, export=export, out=out, spy_pre_lock=s if spy else None, fit_calls_tune=calls)
        flow.pre_lock["refit"] = _try(h_refit, toy, out, 0)
        flow.pre_lock["score"] = _try(h_score, toy, out, 0)
        flow.pre_lock["open_test_labels"] = _try(h_open_test_labels, toy, out, 0)
        h_lock(toy, out)
    return flow


def run_full_flow(toy: Toy, export: SpiedExport, out_name: str) -> Flow:
    flow = run_tune_lock_flow(toy, export, out_name, spy=True)
    with ReadSpy() as s:
        for L in toy.leads:
            h_refit(toy, flow.out, L)
    flow.spy_refit = s
    for L in toy.leads:
        h_score(toy, flow.out, L)
    h_board(toy, flow.out)
    flow.scored_leads = tuple(toy.leads)
    return flow


def learners_of(out: Path) -> List[str]:
    """The board's learner ids from board.json (item B5: key 'learners', a list of ids or of {'id': ...})."""
    board = read_json(Path(out) / "board.json")
    items = board.get("learners")
    if items is None:
        pytest.fail("board.json has no 'learners' (requested in %s item B5)" % NOTES)
    return [str(x["id"] if isinstance(x, dict) else x) for x in items]


def trial_pred_files(out: Path) -> List[Path]:
    return sorted((Path(out) / "trials").glob("*/*/inner_preds.parquet"))


# ------------------------------------------------------------------------------------------ models adapter
def fit_predict(learner: str, params: Dict[str, Any], X: np.ndarray, y: np.ndarray, z0: np.ndarray, link: str,
                c: Optional[float], ub: Optional[float], legal: Tuple[float, float],
                score: Dict[str, Tuple[np.ndarray, np.ndarray]], checkpoints: Sequence[Any],
                columns: Optional[Sequence[str]] = None) -> Dict[str, Dict[Any, Dict[str, np.ndarray]]]:
    """models.fit_predict(learner, params, fit_set, score_sets, checkpoints) with the fit-set shape requested in
    BUILD_NOTES item B3. score: {name: (X, z0)}. Returns {name: {checkpoint: {'pre': ..., 'pred': ...}}}."""
    M = rivals_models()
    fn = need(M, "fit_predict", "B3")
    cols = list(columns) if columns is not None else ["f%d" % i for i in range(X.shape[1])]
    fit_set = {"X": np.asarray(X, dtype=np.float32), "columns": cols, "y": np.asarray(y, dtype=np.float64),
               "z0": np.asarray(z0, dtype=np.float64), "link": link, "c": c, "ub": ub, "legal": tuple(legal)}
    score_sets = {k: {"X": np.asarray(v[0], dtype=np.float32), "columns": cols,
                      "z0": np.asarray(v[1], dtype=np.float64), "link": link, "c": c, "ub": ub,
                      "legal": tuple(legal)} for k, v in score.items()}
    return fn(learner, dict(params), fit_set, score_sets, list(checkpoints))
