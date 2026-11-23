"""The ONE place where the human-rival tests call the tool (SPEC_HUMAN.txt sections 1 and 6).

Every call into rivals_human.* and the adapters goes through a function here, so a signature the builders settle
differently is fixed in one place. A hook the code does not have yet fails the test with `need()`, naming the item of
D:/treeroute/human_rivals_build/BUILD_NOTES_tests.txt that asks for it (fail loud, never a skip).

Also here: the toy setups (config, toy registry, toy products, the common board of the toy run), the full toy flow
(slim, adapt, check, init, tune, lock under the read spy, then the test side), and small file helpers.
"""

import contextlib
import importlib
import io
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pytest

TESTS_DIR = Path(__file__).resolve().parent
HUMAN_ROOT = TESTS_DIR.parents[1]                          # D:/treeroute/human_rivals_build/human
WRITE_ROOT = HUMAN_ROOT.parent                             # D:/treeroute/human_rivals_build
COMMON_ROOT = Path(os.environ.get("HUMAN_COMMON_ROOT", r"D:\treeroute\rivals_build"))
ENGINE_ROOT = Path(os.environ.get("RIVALS_ENGINE_ROOT",
                                  r"C:\Users\<user>\Desktop\data set for reserch paper\engine"))
NOTES = WRITE_ROOT / "BUILD_NOTES_tests.txt"
COMMON_SHA = "b6ea97b72b5a8f79f7f8257f1e4afd00d7783479fada03eea9101410fa509bf2"   # Part 608 fix (was 71457aa9, H:183-189)
OLD_COMMON_SHA = "71457aa902d30dde17a4a88e8d5c7f1de85515c70d2d7ac4745967066f243b97"   # coral + fire boards (ruling AG)
KEYS = ["unit", "group", "time", "issue", "lead"]

# which builder owns which module (SPEC_HUMAN.txt 6)
OWNER = {"config": "A", "common": "A", "slim": "A", "index": "A", "maps": "A", "methods": "A", "refs": "A",
         "board": "A", "lockfile": "A", "join": "A", "manifest": "A", "cli": "A",
         "coral_crw": "B", "coral_outlook": "B", "defo_vt0007": "B", "defo_prep": "B",
         "pm25_reanalysis": "C", "ndvi_bardl": "C", "ndvi_kraft": "C", "ndvi_kraft_prep": "C"}
ADAPTERS = ("coral_crw", "coral_outlook", "defo_vt0007", "defo_prep", "pm25_reanalysis", "ndvi_bardl", "ndvi_kraft",
            "ndvi_kraft_prep")


# ===================================================================================================== small helpers
def tool(name: str) -> Any:
    """rivals_human.<name> (shared tool) or the adapter module <name> (adapters/ at the build root, or
    rivals_human/adapters/); a missing module fails the test naming its builder."""
    sys.dont_write_bytecode = True
    if str(HUMAN_ROOT) not in sys.path:
        sys.path.insert(0, str(HUMAN_ROOT))
    cands = ["adapters." + name, "rivals_human.adapters." + name] if name in ADAPTERS else ["rivals_human." + name]
    errors = []
    for mod in cands:
        try:
            return importlib.import_module(mod)
        except ModuleNotFoundError as exc:
            missing = exc.name or ""
            if not (mod == missing or mod.startswith(missing + ".")):
                raise                                   # the module exists but imports something missing: loud
            errors.append(str(exc))
    pytest.fail("module %s is missing (builder %s, SPEC_HUMAN.txt 6): %s"
                % (" / ".join(cands), OWNER.get(name, "?"), "; ".join(errors)))


def need(module: Any, name: str, item: str) -> Any:
    """getattr, or fail the test naming the BUILD_NOTES_tests.txt item that asks for the hook."""
    if not hasattr(module, name):
        pytest.fail("%s.%s is missing: requested in %s item %s" % (module.__name__, name, NOTES, item))
    return getattr(module, name)


INTERFACE_ERRORS = (TypeError, AttributeError, NameError, ImportError, NotImplementedError, SyntaxError,
                    UnboundLocalError)


def refuses(words: Any, fn: Callable, *args: Any, **kwargs: Any) -> str:
    """fn must REFUSE (raise) with a message naming one of `words` (case-insensitive). An interface error (TypeError,
    AttributeError, ...) is not a refusal: it fails the test, so a broken call never passes as a refusal."""
    if isinstance(words, str):
        words = (words,)
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = fn(*args, **kwargs)
    except INTERFACE_ERRORS as exc:
        pytest.fail("expected a refusal naming %s; got an interface error %s: %s" % (words, type(exc).__name__, exc))
    except SystemExit as exc:
        text = "%s%s%s" % (exc, out.getvalue(), err.getvalue())
        assert exc.code not in (0, None), "expected a refusal naming %s, the command exited 0" % (words,)
    except Exception as exc:                            # the tool's refusal classes; the message decides
        text = "%s: %s\n%s%s" % (type(exc).__name__, exc, out.getvalue(), err.getvalue())
    else:
        pytest.fail("expected a refusal naming %s; the call returned %r\n%s%s" % (words, rc, out.getvalue(),
                                                                                   err.getvalue()))
    low = text.lower()
    assert any(str(w).lower() in low for w in words), "refused, but the message names none of %s:\n%s" % (words, text)
    return text


def sha256_file(path: Any) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Any) -> Any:
    with open(str(path), "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Any, obj: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return p


def read_parquet(path: Any, columns: Optional[Sequence[str]] = None) -> pd.DataFrame:
    import pyarrow.parquet as pq
    return pq.read_table(str(path), columns=list(columns) if columns is not None else None).to_pandas()


def write_parquet(path: Any, frame: pd.DataFrame) -> Path:
    import pyarrow as pa
    import pyarrow.parquet as pq
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), str(p))
    return p


def move_aside(path: Path, moved_root: Path) -> Path:
    """Never delete: a file or folder a test must take away is moved under moved_root/<utc stamp>/."""
    import datetime as _dt
    dest = Path(moved_root) / _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S%f") / Path(path).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(dest))
    return dest


def snapshot(root: Path, skip: Sequence[str] = ()) -> Dict[str, Tuple[int, int]]:
    """{path: (size, mtime_ns)} of every file under root (folders named in skip left out)."""
    out = {}
    for p in sorted(Path(root).rglob("*")):
        if any(s in p.parts for s in skip):
            continue
        if p.is_file():
            st = os.stat(p)
            out[str(p)] = (int(st.st_size), int(st.st_mtime_ns))
    return out


def find_values(obj: Any, key: str) -> List[Any]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                out.append(v)
            out.extend(find_values(v, key))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(find_values(v, key))
    return out


def replace_everywhere(obj: Any, old: Any, new: Any) -> Any:
    if isinstance(obj, dict):
        return {k: replace_everywhere(v, old, new) for k, v in obj.items()}
    if isinstance(obj, list):
        return [replace_everywhere(v, old, new) for v in obj]
    return new if obj == old else obj


# ===================================================================================================== toy setups
@dataclass
class HumanToy:
    """One toy run wired for the human tool. Every path sits under the toy's basetemp."""
    toy: Any                                   # rivals.tests.toy_runs.Toy
    exports: Dict[int, Path]
    base: Path
    config: Path
    roots: Dict[str, Path]
    registry: Dict[str, Any]
    products: Dict[str, Any] = field(default_factory=dict)
    common_board: Optional[Path] = None

    @property
    def run(self) -> Path:
        return self.toy.run

    @property
    def package(self) -> str:
        return self.toy.package_name

    @property
    def leads(self) -> Tuple[int, ...]:
        return tuple(self.toy.leads)

    def rival_ids(self, kind: Optional[str] = None) -> List[str]:
        return [r["id"] for r in self.registry["rivals"] if kind is None or r["kind"] == kind]

    def rival(self, rid: str) -> Dict[str, Any]:
        return next(r for r in self.registry["rivals"] if r["id"] == rid)

    def h_run(self):
        _, H = common_modules(self.config)
        return H.Run(self.run)


def harness_sha_now() -> str:
    """The common harness code sha recomputed with the common recipe (H:183-189), without importing it."""
    import hashlib
    parts = []
    for p in sorted((COMMON_ROOT / "rivals").glob("*.py")):
        parts.append([p.name, sha256_file(p)])
    text = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def write_config(path: Path, toy: Any, base: Path, *, registry_dir: Path, products_file: Path,
                 common_board_root: Path, common_sha: str = COMMON_SHA, out_name: str = "_hout",
                 slim_name: str = "_slim", index_name: str = "_index") -> Tuple[Path, Dict[str, Path]]:
    """human_rivals.yaml for a toy (SPEC_HUMAN.txt 1.1): the six common roots (the toy's export machine, whose
    registry protects the toy run and package) and the extra keys; every root under the toy's basetemp."""
    roots = {"engine_root": ENGINE_ROOT, "machine_file": Path(toy.machine_file), "export_root": Path(toy.export_root),
             "export_ckpt_root": Path(toy.export_ckpt_root), "out_root": base / out_name,
             "moved_root": base / "_hmoved", "common_build_root": COMMON_ROOT, "common_board_root": common_board_root,
             "slim_root": base / slim_name, "index_root": base / index_name, "products_root": base / "_products",
             "on_disk_products": products_file, "table_root": base / "_table", "registry_dir": registry_dir}
    lines = ["# toy human_rivals.yaml (tests only; SPEC_HUMAN.txt 1.1)"]
    for k, v in roots.items():
        lines.append("%s: '%s'" % (k, Path(v).as_posix()))
    lines.append("common_harness_sha256: '%s'" % common_sha)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, roots


def copy_schema(registry_dir: Path) -> None:
    """The toy registry folder gets the tool's own schema (registry/_schema.yaml, builder A), copied byte for byte."""
    src = HUMAN_ROOT / "registry" / "_schema.yaml"
    if not src.is_file():
        pytest.fail("registry/_schema.yaml is missing (builder A, SPEC_HUMAN.txt 1.7; item A0 of %s)" % NOTES)
    registry_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(src), str(registry_dir / "_schema.yaml"))


def write_registries(base: Path, name: str, package: str, registry: Mapping[str, Any],
                     products: Mapping[str, Mapping[str, Any]]) -> Tuple[Path, Path]:
    from rivals_human.tests import toy_products as TP
    rd = base / name
    copy_schema(rd)
    TP.write_yaml(rd / ("%s.yaml" % package), dict(registry))
    pf = TP.write_yaml(rd / "_products.yaml", TP.products_registry(products))
    return rd, pf


def common_modules(config: Any = None):
    """(layout, harness) through the tool's pinned import (rivals_human.common.load, spec 1.2)."""
    C = tool("common")
    return need(C, "load", "A2")(str(config) if config is not None else None)


def common_init(toy: Any, export0: Path, out_root: Path) -> Path:
    """The common board of a toy run (board.json only), through the signed harness, read-only use."""
    from rivals.tests import toy_runs as T
    return T.h_init(toy, export0, out_root, ())


def setup_grid(toy: Any, exports: Mapping[int, Path], variant: str = "main", name: str = "hgrid") -> HumanToy:
    from rivals_human.tests import toy_products as TP
    base = Path(toy.base)
    common_root = base / "_out_common"
    board = common_root / toy.package_name / toy.run.name / "board.json"
    if not board.is_file():
        common_init(toy, exports[0], common_root)
    fit0 = int(toy.cuts(0)["fit_cut"])
    prod = TP.grid_products(base / "_products", exports, fit0) if not (base / "_products" / "toy_grid").is_dir() \
        else {"folder": base / "_products" / "toy_grid" / "v1"}
    products = {"toy_grid": {"path": str(prod["folder"]), "manifest": str(prod["folder"] / "product_manifest.json"),
                             "licence": "toy", "source": "synthetic (tests)"}}
    reg = TP.grid_registry(toy.package_name, variant)
    rd, pf = write_registries(base, "_registry_%s" % name, toy.package_name, reg, products)
    cfg, roots = write_config(base / ("human_rivals_%s.yaml" % name), toy, base, registry_dir=rd, products_file=pf,
                              common_board_root=common_root, out_name="_hout_%s" % name)
    return HumanToy(toy=toy, exports=dict(exports), base=base, config=cfg, roots=roots, registry=reg,
                    products=dict(prod), common_board=board)


def setup_table(toy: Any, exports: Mapping[int, Path], name: str = "htable", scored_common: bool = True) -> HumanToy:
    """The table toy; scored_common: the common board is run in full (init, tune, lock, refit, score, board) under
    the toy's common config, as the joiner needs it."""
    from rivals.tests import toy_runs as T
    from rivals_human.tests import toy_products as TP
    base = Path(toy.base)
    common_root = base / "_out_common"
    board = common_root / toy.package_name / toy.run.name / "board.json"
    if not board.is_file():
        if scored_common:
            T.run_full_flow(toy, T.SpiedExport(dirs=dict(exports), spy=T.ReadSpy()), out_name="_out_common")
        else:
            common_init(toy, exports[0], common_root)
    prod = TP.table_products(base / "_products", exports) if not (base / "_products" / "toy_daily").is_dir() \
        else {"daily": base / "_products" / "toy_daily" / "v1", "outlook": base / "_products" / "toy_outlook" / "v1"}
    products = {pid: {"path": str(prod[k]), "manifest": str(prod[k] / "product_manifest.json"), "licence": "toy",
                      "source": "synthetic (tests)"} for pid, k in (("toy_daily", "daily"), ("toy_outlook", "outlook"))}
    reg = TP.table_registry(toy.package_name)
    rd, pf = write_registries(base, "_registry_%s" % name, toy.package_name, reg, products)
    cfg, roots = write_config(base / ("human_rivals_%s.yaml" % name), toy, base, registry_dir=rd, products_file=pf,
                              common_board_root=common_root, out_name="_hout_%s" % name)
    return HumanToy(toy=toy, exports=dict(exports), base=base, config=cfg, roots=roots, registry=reg,
                    products=dict(prod), common_board=board)


def variant_config(h: HumanToy, name: str, registry: Optional[Mapping[str, Any]] = None, **over: Any) -> HumanToy:
    """A second config on the same toy (same slim and index roots unless overridden; its own registry folder and out
    root). over: write_config keyword overrides (common_sha, slim_name, index_name, out_name)."""
    reg = dict(registry) if registry is not None else h.registry
    products = read_yaml(h.roots["on_disk_products"])["products"]
    rd, pf = write_registries(h.base, "_registry_%s" % name, h.package, reg, products)
    kw = {"out_name": "_hout_%s" % name}
    kw.update(over)
    cfg, roots = write_config(h.base / ("human_rivals_%s.yaml" % name), h.toy, h.base, registry_dir=rd,
                              products_file=pf, common_board_root=h.roots["common_board_root"], **kw)
    return HumanToy(toy=h.toy, exports=h.exports, base=h.base, config=cfg, roots=roots, registry=reg,
                    products=h.products, common_board=h.common_board)


def read_yaml(path: Any) -> Any:
    import yaml
    with open(str(path), "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def minimal_config(folder: Path, common_sha: str = COMMON_SHA, common_board_root: Optional[Path] = None) -> Path:
    """A human_rivals.yaml with every key, for unit tests that need no toy run: the test machine of the human build
    (its own heavy-job lock folder), every write root under `folder`."""
    folder = Path(folder)
    machine = HUMAN_ROOT / "_machine" / "machine.yaml"
    keys = {"engine_root": ENGINE_ROOT, "machine_file": machine, "export_root": folder / "_export",
            "export_ckpt_root": folder / "_export" / "_engine_run_root", "out_root": folder / "_hout",
            "moved_root": folder / "_hmoved", "common_build_root": COMMON_ROOT,
            "common_board_root": common_board_root or folder / "_out_common", "slim_root": folder / "_slim",
            "index_root": folder / "_index", "products_root": folder / "_products",
            "on_disk_products": folder / "_registry" / "_products.yaml", "table_root": folder / "_table",
            "registry_dir": folder / "_registry"}
    lines = ["%s: '%s'" % (k, Path(v).as_posix()) for k, v in keys.items()]
    lines.append("common_harness_sha256: '%s'" % common_sha)
    p = folder / "human_rivals_min.yaml"
    folder.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def adapter_ctx(h: HumanToy, rival_id: str, lead: int, stage: str = "all", token: Any = None, out: Any = None):
    """index.AdapterCtx for one rival and lead (the tool's own context class; spec 6), on the toy's slim copy."""
    C = tool("config")
    I = tool("index")
    S = tool("slim")
    common = tool("common")
    cfg = load_config(h)
    run = h.h_run()
    reg = need(C, "load_registry", "A1")(cfg, run.package)
    products = need(C, "load_products", "A1")(cfg)
    rival = next(r for r in reg["rivals"] if r["id"] == rival_id)
    sl = need(S, "open_slim", "A3")(cfg, run, lead)
    hctx = need(common, "HumanCtx", "A2")(cfg, Path(out or (h.base / "_adapter_ctx_out")), "test")
    return need(I, "AdapterCtx", "A4")(cfg, hctx, run, reg, products, rival, lead, stage, sl, token)


# ===================================================================================================== tool calls
# A1-A3: config, common, slim ----------------------------------------------------------------------------------------
def load_config(h_or_path: Any):
    p = h_or_path.config if isinstance(h_or_path, HumanToy) else h_or_path
    return need(tool("config"), "load_config", "A1")(str(p))


def slim(h: HumanToy, lead: int, export: Optional[Path] = None, config: Optional[Path] = None,
         run: Optional[Path] = None) -> Path:
    fn = need(tool("slim"), "slim", "A3")
    return Path(fn(str(run or h.run), str(export or h.exports[lead]), str(config or h.config)))


def slim_all(h: HumanToy) -> Dict[int, Path]:
    return {L: slim(h, L) for L in h.leads}


def slim_lead(h: HumanToy, folder: Path):
    S = tool("slim")
    return need(S, "SlimLead", "A3")(folder, h.h_run())


def read_set(sl: Any, name: str, lock: Any = None):
    """(keys, y or None, {link: normal}, history DataFrame, extras DataFrame) of a slim set."""
    s = sl.read_set(name, lock=lock)
    return s.keys, s.y, s.normal, s.history, s.extras


def slim_manifest(folder: Path) -> Dict[str, Any]:
    return read_json(Path(folder) / "slim_manifest.json")


# A4-A5: index, timing ------------------------------------------------------------------------------------------------
def adapt(h: HumanToy, rival: str, lead: Any = "all", stage: Optional[str] = None,
          config: Optional[Path] = None) -> List[Path]:
    fn = need(tool("index"), "adapt", "A4")
    return [Path(p) for p in fn(str(h.run), rival, lead, stage, str(config or h.config))]


def check(h: HumanToy, rival: str, config: Optional[Path] = None) -> Dict[str, Any]:
    return need(tool("index"), "check", "A4")(str(h.run), rival, str(config or h.config))


def timing(run: Any, rival: Mapping[str, Any], lead: int):
    """index.Timing(run, rival, lead) (A5)."""
    return need(tool("index"), "Timing", "A5")(run, rival, lead)


def check_tier_timing(tier: str, tm: Any, keys: pd.DataFrame, info_end: Any, target_obs_end: Any,
                      covered: Optional[np.ndarray] = None) -> Dict[str, int]:
    fn = need(tool("index"), "check_tier_timing", "A5")
    cov = np.ones(len(keys), dtype=bool) if covered is None else covered
    return fn(tier, tm, keys, info_end, target_obs_end, cov, "toy test")


def check_frame(frame: pd.DataFrame, expected_keys: pd.DataFrame, rival: Mapping[str, Any], tm: Any, tier: str,
                legal: Tuple[float, float], opened: Mapping[str, Mapping[str, str]],
                manifests: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    fn = need(tool("index"), "check_frame", "A4")
    return fn(frame, expected_keys, rival, tm, tier, legal, opened, manifests, "toy test")


def index_table(h: HumanToy, rival: str, lead: int, stage: str = "all") -> Path:
    I = tool("index")
    files = need(I, "index_files", "A4")(load_config(h), h.h_run(), rival, lead)
    return Path(files[stage])


# A6: maps --------------------------------------------------------------------------------------------------------------
def fit_map(family: str, x, y, z0, link, c, ub, units, keys):
    return need(tool("maps"), "fit", "A6")(family, x, y, z0, link, c, ub, units, keys)


def fit_map_l1(family: str, x, y, z0, link, c, ub, units, keys):
    return need(tool("maps"), "fit_l1", "A6")(family, x, y, z0, link, c, ub, units, keys)


def candidates(rival: Mapping[str, Any], links: Sequence[str]) -> List[Dict[str, Any]]:
    return need(tool("maps"), "candidates", "A6")(rival, list(links))


# A7: the pick ------------------------------------------------------------------------------------------------------------
def pick_of(records: Sequence[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    """records: trial records {candidate, order, status, pick_mae}; the lowest pick MAE, ties by the fixed order."""
    return need(tool("board"), "pick_of", "A7")(list(records))


# A10: the board commands -----------------------------------------------------------------------------------------------
def init(h: HumanToy, config: Optional[Path] = None, run: Optional[Path] = None) -> Path:
    return Path(need(tool("board"), "init", "A10")(str(run or h.run), str(config or h.config)))


def tune(h: HumanToy, out: Path, resume: bool = True, config: Optional[Path] = None) -> Any:
    return need(tool("board"), "tune", "A10")(str(out), resume=resume, config=str(config or h.config))


def lock(h: HumanToy, out: Path, config: Optional[Path] = None) -> Any:
    return need(tool("board"), "lock", "A10")(str(out), config=str(config or h.config))


def refit(h: HumanToy, out: Path, lead: int, resume: bool = True, config: Optional[Path] = None) -> Any:
    return need(tool("board"), "refit", "A10")(str(out), int(lead), resume=resume, config=str(config or h.config))


def refs(h: HumanToy, out: Path, lead: int, config: Optional[Path] = None) -> Any:
    return need(tool("refs"), "refs", "A11")(str(out), int(lead), config=str(config or h.config))


def score(h: HumanToy, out: Path, lead: int, config: Optional[Path] = None) -> Any:
    return need(tool("board"), "score", "A10")(str(out), int(lead), config=str(config or h.config))


def board(h: HumanToy, out: Path, config: Optional[Path] = None) -> Any:
    """human_board.md (board.board_md; the CLI command `board`)."""
    return need(tool("board"), "board_md", "A10")(str(out), config=str(config or h.config))


def status(h: HumanToy, out: Path) -> Any:
    return need(tool("board"), "status", "A10")(str(out))


def verify_lock(out: Path):
    return need(tool("lockfile"), "verify_lock", "A12")(str(out))


def ledger_path(out: Path, fingerprint: str) -> Path:
    return Path(need(tool("lockfile"), "ledger_path", "A12")(str(out), fingerprint))


def join(h: HumanToy, runs: Sequence[Path], config: Optional[Path] = None) -> Path:
    return Path(need(tool("join"), "join", "A13")([str(r) for r in runs], config=str(config or h.config)))


def manifest(h: HumanToy, product: str, config: Optional[Path] = None) -> Path:
    return Path(need(tool("manifest"), "manifest", "A14")(product, config=str(config or h.config)))


def cli_main(argv: Sequence[str]) -> int:
    return need(tool("cli"), "main", "A15")(list(argv))


# ===================================================================================================== board files
def lead_dir(out: Path, lead: int) -> Path:
    return Path(out) / ("lead_%d" % int(lead))


def preds(out: Path, lead: int, rival: str) -> pd.DataFrame:
    return read_parquet(lead_dir(out, lead) / ("preds_%s.parquet" % rival))


def guard_file(out: Path, lead: int, rival: str) -> pd.DataFrame:
    return read_parquet(lead_dir(out, lead) / ("guard_%s.parquet" % rival))


def board_lead(out: Path, lead: int) -> pd.DataFrame:
    return pd.read_csv(Path(out) / ("human_board_lead_%d.csv" % int(lead)), float_precision="round_trip")


def picks(out: Path) -> Dict[str, Any]:
    return read_json(Path(out) / "human_picks.json")


def saved_test(h: HumanToy, lead: int, columns: Optional[Sequence[str]] = None) -> pd.DataFrame:
    """The run's saved test rows of a lead (WITH y: tests read them only after the tool's own score)."""
    return read_parquet(h.toy.saved_test_preds(lead), columns)


# ===================================================================================================== the full flow
@dataclass
class Flow:
    h: HumanToy
    slim_dirs: Dict[int, Path]
    out: Path
    spy: Any = None                                  # ReadSpy over init / tune / lock
    pre_lock: Dict[str, str] = field(default_factory=dict)
    adapted: Dict[str, List[Path]] = field(default_factory=dict)
    checks: Dict[str, Any] = field(default_factory=dict)
    steps: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)     # "refit 0", "refs 6", "score 0", "board": the refusal

    def ok(self, *steps: str) -> None:
        """Fail the calling test with the recorded refusal when a flow step it needs did not finish."""
        bad = ["%s: %s" % (s, self.errors[s]) for s in steps if s in self.errors]
        if bad:
            pytest.fail("the toy flow step(s) this test reads did not finish:\n" + "\n".join(bad))


def _try(fn: Callable, *a: Any, **kw: Any) -> str:
    try:
        fn(*a, **kw)
    except INTERFACE_ERRORS as exc:
        return "INTERFACE ERROR: %s: %s" % (type(exc).__name__, exc)
    except BaseException as exc:                     # noqa: B902
        return "refused: %s: %s" % (type(exc).__name__, exc)
    return "RAN"


def index_rivals(h: HumanToy) -> List[Dict[str, Any]]:
    return [r for r in h.registry["rivals"] if r.get("adapter")]


def staged(r: Mapping[str, Any]) -> bool:
    return bool(r.get("reads_target_in_test_window"))


def run_flow(h: HumanToy, slim_dirs: Mapping[int, Path], out_name: str = "_hout_a",
             config: Optional[Path] = None) -> Flow:
    """adapt (train side) + check for every index rival, init, tune, the pre-lock refusals, lock (spied), then the
    test side: adapt stage test (staged rivals), refit, refs, score at every lead, board."""
    from rivals.tests import toy_runs as T
    cfg = config or h.config
    for r in index_rivals(h):
        h_stage = "train" if staged(r) else None
        flow_adapted = adapt(h, r["id"], "all", h_stage, cfg)
        assert flow_adapted, "adapt wrote no index table for %s" % r["id"]
    checks = {r["id"]: check(h, r["id"], cfg) for r in index_rivals(h)}
    with T.ReadSpy() as spy:
        out = init(h, cfg)
        tune(h, out, True, cfg)
        pre = {"refit": _try(refit, h, out, 0, True, cfg), "score": _try(score, h, out, 0, cfg),
               "refs": _try(refs, h, out, 0, cfg)}
        for r in index_rivals(h):
            if staged(r):
                pre["adapt_test_%s" % r["id"]] = _try(adapt, h, r["id"], "all", "test", cfg)
        lock(h, out, cfg)
    flow = Flow(h=h, slim_dirs=dict(slim_dirs), out=out, spy=spy, pre_lock=pre, checks=checks)
    for r in index_rivals(h):
        if staged(r):
            adapt(h, r["id"], "all", "test", cfg)
    # the test side: a refusal of one step is recorded (flow.errors) and the flow goes on, so one defect does not
    # hide every other result; a test that reads a step's output calls flow.ok("<step> <lead>") first
    def attempt(key: str, fn: Callable, *a: Any) -> None:
        res = _try(fn, *a)
        if res != "RAN":
            flow.errors[key] = res
    for L in h.leads:
        attempt("refit %d" % L, refit, h, out, L, True, cfg)
    for L in sorted(h.leads, reverse=True):          # leads >= 1 first: the parity proof precedes the nowcast rows
        attempt("refs %d" % L, refs, h, out, L, cfg)
    for L in h.leads:
        attempt("score %d" % L, score, h, out, L, cfg)
    attempt("board", board, h, out, cfg)
    flow.steps = ["adapt", "check", "init", "tune", "lock", "refit", "refs", "score", "board"]
    return flow


def run_tune_lock(h: HumanToy, config: Optional[Path] = None) -> Path:
    """init, tune, lock only (index tables must exist)."""
    cfg = config or h.config
    out = init(h, cfg)
    tune(h, out, True, cfg)
    lock(h, out, cfg)
    return out
