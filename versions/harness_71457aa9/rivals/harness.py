"""The rival harness: init, probe, tune, lock, refit, score, board (SPEC_RIVALS section 3).

Plug and predict: the harness reads a finished run folder and the export of that run; it names no
problem. Every fact (links, c, cuts, legal range, router kind, decline target, band, tolerance,
strata, overlap blocks) is read from the run; every data column from the export.

The test-label rule: no function here opens a test feature file or a test label before the picks
are locked. test/*.parquet is read first by refit (after the lock); the run's saved test labels are
read ONLY by open_test_labels_rivals (score), which refuses without a valid lock.
"""
# Provenance: SPEC_RIVALS.md section 3 (D:/treeroute/rivals_build); RIVALS_PLAN_COMMON.md section 3
# rules 1-18; OWNER_RULINGS_2026-10-06.md Y1-Y4. Engine functions used (LIVE, read-only):
# layer/links.py:84 link_forward, :118 link_inverse, :261 clip_to_legal; layer/decide.py:290
# n2_eligible; report/metrics.py:336 baseline_predict_zero, :569 mae, :604 corr2, :623
# calibration_ratio, :743 stratum_bins, :846 score_table, :999 metric_by_key, :1058 blocked_jackknife,
# :1097 contrast_tag, :1123 _paired_contrast; runs/preflight.py:168 HeavyJobLock; runs/registry.py:195
# assert_writable; runs/atomic.py write_json_once / replace_json / replace_bytes / dumps_canonical.

import datetime as _dt
import gc
import glob
import hashlib
import io
import json
import math
import os
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from rivals import layout as LY
from rivals import models as M

BOARD_FORMAT = "rivals-board/1"
PICKS_FORMAT = "rivals-picks/1"

# ---- the config file (spec 1.1): paths only; read by layout.load_roots ------------------------------
CONFIG_KEYS = LY.ROOT_KEYS

# ---- the export folder of one run and lead (spec 1.2; names from rivals/layout.py) ------------------
EXPORT_MANIFEST = LY.EXPORT_MANIFEST
TRAIN_DIR, GUARD_DIR, TEST_DIR = LY.TRAIN_DIR, LY.GUARDSIDE_DIR, LY.TEST_DIR
UNITS_FILE = LY.UNITS_FILE
KEYS = LY.KEY_COLUMNS
FLAG_REFIT, FLAG_TUNE, FLAG_INNER, FLAG_GUARDFIT, FLAG_GUARD = (
    LY.ROLE_FLAG[LY.ROLE_REFIT], LY.ROLE_FLAG[LY.ROLE_TUNE], LY.ROLE_FLAG[LY.ROLE_INNER],
    LY.ROLE_FLAG[LY.ROLE_GUARDFIT], LY.ROLE_FLAG[LY.ROLE_GUARD])
FLAGS = LY.FLAG_COLUMNS
X_PREFIX, C_PREFIX, H_PREFIX = LY.X_PREFIX, LY.C_PREFIX, LY.H_PREFIX
NFIT_PREFIX, NGD_PREFIX = LY.NFIT_PREFIX, LY.NGD_PREFIX
ZERO_SHARE_KEY = "zero_share_refit_y"      # export manifest key read when the export holds no refit row

# The sets a lead holds: (flag, side). side 'fit' = fit-cut features and normal (train/ or test/);
# 'guard' = guard-cut history (guardside/ h__) and guard-cut normal (ngd__).
SETS = {
    "tune": (FLAG_TUNE, "guard"),
    "inner": (FLAG_INNER, "guard"),
    "refit": (FLAG_REFIT, "fit"),
    "guardfit": (FLAG_GUARDFIT, "guard"),
    "guard": (FLAG_GUARD, "guard"),
    "test": (None, "fit"),
}

# ---- the harness output folder (spec 1.3) ----------------------------------------------------------
BOARD_FILE = LY.BOARD_FILE
PICKS_FILE = LY.PICKS_FILE
PICKS_LOCK = LY.PICKS_LOCK
TRIALS_DIR = LY.TRIALS_DIR
TRIALS_CSV = LY.TRIALS_CSV
LOG_FILE = LY.RIVALS_LOG
STATUS_FILE = "status.json"
MATERIALIZED_DIR = LY.MATERIALIZED_DIR
SCORES_DIR = LY.SCORES_DIR
TEST_LABELS_OPENED = LY.TEST_LABELS_OPENED
BOARD_LEAD_CSV = LY.BOARD_LEAD_CSV
BOARD_MD = LY.BOARD_MD
PROBE_FILE = "probe.json"

# ---- run facts -------------------------------------------------------------------------------------
DEFAULT_DECLINE_TARGET = "arm__identity_trees_off_unweighted"
TREES_OFF_SUFFIX = "_trees_off_unweighted"
TWEEDIE_ZERO_SHARE = 0.20
WATCHDOG_LIMIT_GIB = 12
WATCHDOG_LIMIT_BYTES = WATCHDOG_LIMIT_GIB << 30
WATCHDOG_POLL_S = 2.0
LGBM_RAM_EXTRA = 2 * (1 << 30)
RIDGE_RAM = 1 << 30
LIBRARIES = ("lightgbm", "scikit-learn", "scikit-learn-intelex", "numpy", "pandas", "pyarrow",
             "threadpoolctl")
PROBE_ROUNDS, PROBE_TREES = 20, 10
WATCHDOG_EXIT = 70
LOG_HEADER = ("utc | command | stage | learner | trial | seconds | peak private GiB so far | message"
              "   (private = memory the process owns; file pages read through a memmap are not counted)")
LEDGER_DIR = "_ledger"                     # <out root>/_ledger/<run fingerprint>.jsonl: locks and label openings
EXPORT_COPY_DIR = "exports"                # <board>/exports/lead_L/: the manifest and units.parquet kept
SCRATCH_KEY = "scratch_root"               # rivals.yaml (optional): where the fit-set copies go
DISK_SLACK = 3 << 30                       # a fit-set copy needs its size + 3 GiB free
# contrast_tag's tags read as "ours vs the rival" (d = MAE rival - MAE ours; HELPS = ours better)
VERDICT_WORDS = {"helps": "BEATS", "hurts": "LOSES", "does_not_help_equivalent": "EQUIVALENT",
                 "cannot_tell": "CANNOT TELL", "identical": "IDENTICAL", "declined": "DECLINED"}


class HarnessRefusal(RuntimeError):
    """A harness rule refused. Nothing catches it (fail loud)."""


def _refuse(message: str, fix: Optional[str] = None):
    raise HarnessRefusal(message + ("" if not fix else "  FIX: " + fix))


# ===================================================================================================
# Small helpers
def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Any, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def read_json(path: Any) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _clean(obj: Any) -> Any:
    """JSON-safe copy: NaN / inf -> None, numpy scalars -> Python numbers, tuples -> lists."""
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, Path):
        return str(obj)
    return obj


def dumps_canonical(obj: Any) -> str:
    return json.dumps(_clean(obj), sort_keys=True, separators=(",", ":"), allow_nan=False,
                      ensure_ascii=True)


def dumps_pretty(obj: Any) -> str:
    return json.dumps(_clean(obj), sort_keys=True, indent=1, allow_nan=False, ensure_ascii=False) + "\n"


def ck_label(ck: Any) -> str:
    """A checkpoint's label: rounds and tree counts as integers, alphas as repr(float)."""
    if isinstance(ck, (int, np.integer)) and not isinstance(ck, bool):
        return str(int(ck))
    return repr(float(ck))


def harness_code_sha(root: Optional[Path] = None) -> str:
    """sha256 over the sorted (name, sha256) of rivals/*.py (tests excluded)."""
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    parts = []
    for p in sorted(root.glob("*.py")):
        parts.append([p.name, sha256_file(p)])
    return sha256_bytes(dumps_canonical(parts).encode("ascii"))


def library_versions() -> Dict[str, Optional[str]]:
    from importlib import metadata
    out = {}
    for dist in LIBRARIES:
        try:
            out[dist] = metadata.version(dist)
        except metadata.PackageNotFoundError:
            out[dist] = None
    return out


def _find_value(obj: Any, value: Any) -> bool:
    """True if value occurs anywhere inside a JSON document."""
    if obj == value:
        return True
    if isinstance(obj, dict):
        return any(_find_value(v, value) for v in obj.values())
    if isinstance(obj, list):
        return any(_find_value(v, value) for v in obj)
    return False


def _find_key(obj: Any, key: str) -> List[Any]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                out.append(v)
            out.extend(_find_key(v, key))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_find_key(v, key))
    return out


# ===================================================================================================
# Config, engine, registry, moved-aside folder
def load_config(path: Any = None) -> Dict[str, str]:
    """The rivals.yaml roots (layout.load_roots: paths only, every one absolute) as plain strings,
    with the LIVE engine imported read-only from engine_root (layout.import_engine)."""
    roots = LY.as_roots(path)
    out = {k: Path(getattr(roots, k)).as_posix() for k in CONFIG_KEYS}
    sr = roots.extra.get(SCRATCH_KEY)
    if sr is not None and not Path(str(sr)).is_absolute():
        _refuse("rivals.yaml %s must be an absolute path, got %r" % (SCRATCH_KEY, sr))
    out[SCRATCH_KEY] = None if sr is None else Path(str(sr)).as_posix()
    out["_file"] = roots.source
    LY.import_engine(roots.engine_root)
    return out


class Engine(object):
    """The LIVE engine's functions, imported read-only."""

    def __init__(self, cfg: Mapping[str, str]):
        LY.import_engine(cfg["engine_root"])
        from treeroute.report import metrics
        from treeroute.layer import links, decide
        from treeroute.runs import preflight, registry, machine, atomic
        self.metrics, self.links, self.decide = metrics, links, decide
        self.preflight, self.atomic = preflight, atomic
        self.machine = machine.load_machine(cfg["machine_file"])
        self.registry = registry.Registry(self.machine.registry_dir)

    def writable(self, path: Any) -> Path:
        self.registry.assert_writable(str(path))
        return Path(path)


class Ctx(object):
    """One command's context: config, engine, out folder, log."""

    def __init__(self, cfg, eng, out: Path, command: str):
        self.cfg, self.eng, self.out, self.command = cfg, eng, Path(out), command
        self.peak_rss = 0
        self.peak_resident = 0
        self.moved_stamp = None
        self.progress = ""

    # --- writes -----------------------------------------------------------------------------------
    def mkdir(self, path: Path) -> Path:
        self.eng.writable(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_once_json(self, path: Path, obj: Any):
        """Write-once: refuses when the file exists (the heavy-job lock rules out a second writer)."""
        if os.path.lexists(path):
            _refuse("refusing to overwrite %s (written once)" % path)
        self.replace_json(path, obj)

    def replace_json(self, path: Path, obj: Any):
        LY.atomic_write_bytes(path, dumps_pretty(obj).encode("utf-8"), self.eng.registry)

    def replace_bytes(self, path: Path, data: bytes):
        LY.atomic_write_bytes(path, data, self.eng.registry)

    def write_parquet(self, path: Path, frame: pd.DataFrame):
        """Deterministic parquet bytes, written atomically (temp file, fsync, rename)."""
        self.replace_bytes(path, parquet_bytes(frame))

    def move_aside(self, path: Path):
        """Never delete: move a file or folder under moved_root/<utc stamp>/ (keeping its name)."""
        path = Path(path)
        if not os.path.lexists(path):
            return
        if self.moved_stamp is None:
            self.moved_stamp = utc_stamp()
        dest = LY.move_aside(path, self.cfg["moved_root"], self.eng.registry, stamp=self.moved_stamp,
                             relative_to=self.out.parent)
        self.log("moved", message="%s -> %s" % (path, dest))

    # --- log and status --------------------------------------------------------------------------
    def rss(self) -> int:
        """The process tree's PRIVATE memory (Windows: private bytes; elsewhere: uss), never the resident set:
        pages read from a memmapped data file count in the resident set but are not memory the process owns
        (robustness review 4). The resident set is kept as a second number (peak_resident)."""
        total, resident = process_tree_memory()
        self.peak_resident = max(getattr(self, "peak_resident", 0), resident)
        self.peak_rss = max(self.peak_rss, total)
        return total

    def log(self, stage: str, learner: str = "", trial: str = "", seconds: Optional[float] = None,
            message: str = "", echo: bool = True):
        self.rss()
        line = "%s | %s | %s | %s | %s | %s | %.2f GiB | %s" % (
            utc_now(), self.command, stage, learner or "-", trial or "-",
            "-" if seconds is None else "%.1f s" % seconds, self.peak_rss / M.GIB, message)
        if self.out.is_dir():
            lp = self.out / LOG_FILE
            if not lp.is_file():
                LY.append_line(lp, LOG_HEADER, self.eng.registry)
            LY.append_line(lp, line, self.eng.registry)
            self.status(stage, learner, trial)
        if echo:
            print(line, flush=True)

    def status(self, stage: str, learner: str = "", trial: str = ""):
        rec = {"command": self.command, "stage": stage, "learner": learner, "trial": trial,
               "utc": utc_now(), "pid": os.getpid(), "peak_rss_bytes": self.peak_rss}
        self.replace_json(self.out / STATUS_FILE, rec)


def process_memory(proc: Any) -> Tuple[int, int]:
    """(private bytes, resident bytes) of one process. Windows: memory_info().private; elsewhere uss."""
    import psutil
    mi = proc.memory_info()
    private = getattr(mi, "private", None)
    if private is None:
        try:
            private = proc.memory_full_info().uss
        except (psutil.Error, AttributeError):
            private = mi.rss
    return int(private), int(mi.rss)


def process_tree_memory() -> Tuple[int, int]:
    """(private, resident) summed over this process and its children."""
    import psutil
    proc = psutil.Process(os.getpid())
    private, resident = process_memory(proc)
    for ch in proc.children(recursive=True):
        try:
            p, r = process_memory(ch)
        except psutil.Error:
            continue
        private += p
        resident += r
    return private, resident


def read_columns(path: Any, columns: Sequence[str]) -> pd.DataFrame:
    """Read only the named columns of one parquet file (ParquetFile.read: no dataset scan of the whole
    file). Every read of a run's saved test rows before scoring goes through here, never asking y."""
    if "y" in columns:
        _refuse("internal: a column read asked for y (%s)" % path)
    with pq.ParquetFile(str(path)) as pf:
        return pf.read(columns=list(columns)).to_pandas()


def parquet_bytes(frame: pd.DataFrame) -> bytes:
    table = pa.Table.from_pandas(frame, preserve_index=False)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    return buf.getvalue()


class Watchdog(threading.Thread):
    """Polls the process tree's private memory every 2 s; at the limit it logs a failure line, releases the
    heavy-job lock and stops the process (the trial in flight is redone on resume)."""

    def __init__(self, ctx: Ctx, lock: Any, limit: int = WATCHDOG_LIMIT_BYTES):
        super().__init__(daemon=True)
        self.ctx, self.lock, self.limit = ctx, lock, limit
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.wait(WATCHDOG_POLL_S):
            rss = self.ctx.rss()
            if rss >= self.limit:
                try:
                    self.ctx.log("FAILED", message="RAM watchdog: process tree private memory %.2f GiB reached "
                                 "the %.2f GiB limit; stopping (resume redoes the trial in flight)"
                                 % (rss / M.GIB, self.limit / M.GIB))
                    if self.lock is not None:
                        self.lock.release()
                finally:
                    os._exit(WATCHDOG_EXIT)

    def stop(self):
        self._stop_event.set()


def thread_state() -> List[List[Any]]:
    """The thread pools of the learners' libraries, after loading them and limiting to 8."""
    import threadpoolctl
    import lightgbm  # noqa: F401  (loads its OpenMP pool)
    import sklearn.ensemble  # noqa: F401
    import sklearnex.ensemble  # noqa: F401
    threadpoolctl.threadpool_limits(M.THREADS)
    info = threadpoolctl.threadpool_info()
    rows = sorted([str(i.get("user_api")), str(i.get("internal_api")), str(i.get("prefix")),
                   int(i.get("num_threads"))] for i in info)
    return rows


class _Command(object):
    """Context manager for one command: config, engine, the engine's heavy-job lock, the watchdog."""

    def __init__(self, name: str, out: Any, config: Any = None, need_out: bool = True):
        self.name, self.out_arg, self.config, self.need_out = name, out, config, need_out

    def __enter__(self) -> Ctx:
        cfg = load_config(self.config)
        eng = Engine(cfg)
        self.ctx = Ctx(cfg, eng, Path(self.out_arg), self.name)
        if self.need_out and not (self.ctx.out / BOARD_FILE).is_file():
            _refuse("%s holds no %s" % (self.ctx.out, BOARD_FILE), fix="run init first")
        self.lock = eng.preflight.HeavyJobLock(eng.machine.temp_dir)
        self.lock.acquire()
        self.dog = Watchdog(self.ctx, self.lock)
        self.dog.start()
        self.t0 = time.time()
        return self.ctx

    def __exit__(self, exc_type, exc, tb):
        self.dog.stop()
        try:
            if exc is not None and self.ctx.out.is_dir():
                self.ctx.log("FAILED", message="%s: %s" % (type(exc).__name__, exc))
            elif exc is None and self.ctx.out.is_dir():
                self.ctx.log("done", seconds=time.time() - self.t0)
        finally:
            self.lock.release()
        return False


# ===================================================================================================
# Run facts (all read from the run folder)
class Run(object):
    """The finished run: every fact the rivals need, read from its own files."""

    def __init__(self, folder: Any):
        self.folder = Path(folder)
        for name in ("DONE.json", "manifest.json", "derived.json", "plan.json", "verdict.json",
                     "decision_checks.json", "inner_preds.parquet", "test_preds.parquet"):
            if not (self.folder / name).is_file():
                _refuse("run folder %s has no %s" % (self.folder, name))
        self.manifest = read_json(self.folder / "manifest.json")
        self.derived = read_json(self.folder / "derived.json")
        self.plan = read_json(self.folder / "plan.json")
        self.verdict = read_json(self.folder / "verdict.json")
        self.checks = read_json(self.folder / "decision_checks.json")
        self.name = self.folder.name
        self.fingerprint = self.manifest["fingerprint"]
        self.package = self.manifest["config"]["package"]
        self.kind = self.manifest["config"]["kind"]
        self.links = list(self.plan["links"])
        r22 = self._derived_value("R22")
        if list(r22) != self.links:
            _refuse("plan.json links %s differ from derived R22 %s" % (self.links, r22))
        if "identity" not in self.links:
            _refuse("the run's R22 links %s hold no identity link; the rivals need the identity "
                    "normal (Tweedie offset, N2 comparator)" % self.links)
        self.router_kind = self.plan["router_kind"]
        r11 = self._derived_value("R11")
        self.cuts = {int(k): {"fit_cut": int(v["fit_cut"]), "guard_cut": int(v["guard_cut"])}
                     for k, v in r11.items()}
        self.leads = sorted(self.cuts)
        legal = self._derived_value("R28")
        self.legal = (float(legal[0]), float(legal[1]))
        self.ub = self.legal[1] if math.isfinite(self.legal[1]) else None
        self.band = float(self.verdict["band"])
        self.tol = float(self.verdict["hit_tolerance"])
        floor = self.verdict.get("measurement_error_floor")
        self.floor = None if floor is None else float(floor)
        db = self.checks.get("decline_baseline")
        self.v1 = isinstance(db, dict) and bool(db.get("key"))
        self.decline_target = db["key"] if self.v1 else DEFAULT_DECLINE_TARGET
        vt = self.verdict.get("decline_target")
        if vt is not None and vt != self.decline_target:
            _refuse("verdict.json decline_target %r differs from decision_checks %r" % (vt, self.decline_target))
        ob = self.derived.get("R14:overlap_blocks")
        self.block_of_group = (ob or {}).get("value", {}).get("block_of_group") if ob else None

    def _derived_value(self, key: str) -> Any:
        if key not in self.derived or "value" not in self.derived[key]:
            _refuse("derived.json has no %s value" % key)
        return self.derived[key]["value"]

    def c(self, lead: int) -> Optional[float]:
        """The lead's R23 c (the fit-cut c serves every row of the lead, A3); None without log_c."""
        key = "R23:lead=%d" % lead
        if key in self.derived:
            return float(self.derived[key]["value"])
        if "log_c" in self.links:
            _refuse("the run offers log_c but derived.json has no %s" % key)
        return None

    def test_preds_path(self, lead: int) -> Path:
        if lead == 0:
            return self.folder / "test_preds.parquet"
        return self.folder / "ladder" / ("lead_%d" % lead) / "test_preds.parquet"

    def guard_preds_path(self, lead: int) -> Path:
        return self.folder / "ladder" / ("lead_%d" % lead) / "guard_preds.parquet"

    def lead_json(self, lead: int) -> Dict[str, Any]:
        return read_json(self.folder / "ladder" / ("lead_%d" % lead) / "lead.json")

    def inner_candidates(self) -> int:
        p = self.folder / "inner_candidates.csv"
        if not p.is_file():
            return 0
        return int(len(pd.read_csv(p)))

    def decline_target_at(self, lead: int) -> str:
        """The decline target column of a lead's saved test rows (the run's own safety net)."""
        if lead != 0:
            lt = self.lead_json(lead).get("test", {}).get("decline_target")
            if lt is not None and lt != self.decline_target:
                _refuse("lead %d decline_target %r differs from the run's %r" % (lead, lt, self.decline_target))
        return self.decline_target

    def comparator_inner(self, learner: str, link: Optional[str]) -> str:
        """The N2 comparator column on the inner rows (inner_preds.parquet)."""
        if self.v1:
            return self.decline_target
        own = "identity" if learner == "lgbm_tweedie" else link
        return own + TREES_OFF_SUFFIX

    def ours(self, lead: int) -> Tuple[str, str]:
        """(our headline column, our pinned arm raw column) on the lead's saved test rows."""
        if lead == 0:
            declined = bool(self.verdict.get("declined"))
            headline = self.decline_target if declined else "arm__" + self.verdict["adopted"]
            ac = self.verdict.get("adopted_column")
            if ac is not None and ac != headline:
                _refuse("verdict adopted_column %r differs from the headline column %r" % (ac, headline))
            # the pinned arm: the adopted arm, or (declined nowcast) the best tree arm the leads pin
            arm = self.verdict.get("best_tree_arm") if declined else self.verdict["adopted"]
            if not arm:
                _refuse("verdict.json names no arm to print raw beside the headline")
            return headline, "arm__" + arm
        lj = self.lead_json(lead)
        pinned = lj.get("pinned")
        if not pinned:
            _refuse("lead %d lead.json names no pinned arm" % lead)
        return lj["test"]["adopted_column"], "arm__" + pinned


def check_run_identity(run: Run, board: Mapping[str, Any]):
    if run.fingerprint != board["run"]["fingerprint"]:
        _refuse("the run fingerprint %s differs from board.json %s" % (run.fingerprint, board["run"]["fingerprint"]))


# ===================================================================================================
# The export of one lead (read-only)
# Files read from an export are checked against the sha256 the export manifest lists for them (once per
# process per file; a changed size or modification time re-checks). Review fixes (rivals review): leak-fairness 3/4,
# parity 1/2/10, robustness 6.
_VERIFIED: Dict[str, Tuple[int, int, str]] = {}
UNITS_PART = "units"


def export_identity(manifest: Mapping[str, Any]) -> Dict[str, Any]:
    """The facts every lead of one board's export must share (parity review 1)."""
    try:
        return {"run_fingerprint": manifest["run"]["fingerprint"],
                "package_fingerprint": manifest["package"]["fingerprint"],
                "engine_live_file_sha": manifest["engine"]["live_file_sha"],
                "export_code_sha256": manifest["export_code_sha256"],
                "derived_sha256": manifest["derived_sha256"],
                "router_kind": manifest.get("router_kind"),
                "links": list(manifest["links"]),
                "ub": manifest.get("ub"),
                "legal_range_text": list(manifest["legal_range_text"]),
                # an owner-accepted engine difference: every lead must carry the same record (Z check 1 d)
                "accepted_difference": (manifest.get("engine") or {}).get("accepted_difference")}
    except (KeyError, TypeError) as exc:
        _refuse("the export manifest lacks an identity field (%s)" % exc)


def check_accept_seal(ex: "ExportLead", run: "Run") -> Optional[Dict[str, Any]]:
    """Z check 1 d: an export made under an owner-accepted engine difference is usable only when its run's seal
    (export.py write_accept_seal, written last) exists, covers EVERY lead of the run, and lists the sha256 of
    each lead's export_manifest.json as it is now. Returns the seal (None for a run with no accepted difference)."""
    acc = (ex.manifest.get("engine") or {}).get("accepted_difference")
    if not acc:
        return None
    root = ex.dir.parent
    sp = root / LY.ACCEPT_SEAL
    fix = "export every lead of the run again in one call (export --lead all --resume); if it refuses, ask the owner"
    if not sp.is_file():
        _refuse("lead %d export %s was made under the accepted engine difference of ruling %s, but %s is missing: "
                "not every lead passed P1-P15 in one call" % (ex.lead, ex.dir, acc.get("ruling"), sp), fix=fix)
    seal = read_json(sp)
    leads = seal.get("leads") or {}
    if (seal.get("format") != LY.FORMAT_ACCEPT_SEAL or seal.get("run_id") != acc.get("run_id")
            or seal.get("run_fingerprint") != run.fingerprint or seal.get("ruling") != acc.get("ruling")):
        _refuse("the seal %s does not belong to run id %s (fingerprint %s, ruling %s)"
                % (sp, acc.get("run_id"), run.fingerprint[:16], acc.get("ruling")), fix=fix)
    missing = [L for L in run.leads if str(int(L)) not in leads]
    if missing:
        _refuse("the seal %s does not cover lead(s) %s of the run" % (sp, missing), fix=fix)
    for L in run.leads:
        mp = root / ("lead_%d" % int(L)) / EXPORT_MANIFEST
        got = sha256_file(mp) if mp.is_file() else None
        if got != leads[str(int(L))].get("manifest_sha256"):
            _refuse("lead %d's export manifest %s is not the one the seal %s lists (sha %s vs %s)"
                    % (int(L), mp, sp, str(got)[:16], str(leads[str(int(L))].get("manifest_sha256"))[:16]), fix=fix)
    return seal


def export_content_sha(manifest: Mapping[str, Any]) -> str:
    """A hash of the export's CONTENT: every listed file (path, sha256, rows, part, group), the columns, counts,
    row-key hashes, lead, cuts, c and the identity. Timings, stamps, peak RAM and resume counters are left out,
    so a rebuilt export with the same bytes has the same content hash (robustness review 6)."""
    files = sorted([str(f["path"]), str(f["sha256"]), int(f["rows"]), str(f["part"]), str(f["group"])]
                   for f in manifest.get("files") or [])
    rec = {"files": files, "columns": manifest.get("columns"), "counts": manifest.get("counts"),
           "row_key_hashes": manifest.get("row_key_hashes"), "lead": manifest.get("lead"),
           "roles": manifest.get("roles"), "cuts": manifest.get("cuts"), "c": manifest.get("c"),
           "identity": export_identity(manifest)}
    return sha256_bytes(dumps_canonical(rec).encode("ascii"))


def _legal_of_manifest(manifest: Mapping[str, Any]) -> Tuple[float, float]:
    txt = manifest.get("legal_range_text")
    if not txt or len(txt) != 2:
        _refuse("the export manifest has no legal_range_text")
    return float(txt[0]), float(txt[1])


class ExportLead(object):
    """One lead folder of the export: its groups, its columns, its sets."""

    def __init__(self, folder: Any, lead: int, run: Run):
        self.dir = Path(folder)
        self.lead = int(lead)
        self.run = run
        mpath = self.dir / EXPORT_MANIFEST
        if not mpath.is_file():
            _refuse("export %s has no %s (the export writes it LAST, after every parity check)"
                    % (self.dir, EXPORT_MANIFEST), fix="finish the export of this lead first")
        self.manifest_bytes = mpath.read_bytes()
        self.manifest_sha = sha256_bytes(self.manifest_bytes)
        self.manifest = json.loads(self.manifest_bytes.decode("utf-8"))
        if not _find_value(self.manifest, run.fingerprint):
            _refuse("export manifest %s does not name the run fingerprint %s" % (mpath, run.fingerprint))
        if int(self.manifest.get("lead", -1)) != self.lead:
            _refuse("export %s is lead %r, not lead %d" % (self.dir, self.manifest.get("lead"), self.lead))
        self.content_sha = export_content_sha(self.manifest)
        # the cuts: the manifest's must equal the run's own (derived R11)
        if self.lead not in run.cuts or 0 not in run.cuts:
            _refuse("the run has no cuts for lead %d (derived R11 leads %s)" % (self.lead, run.leads))
        mc = self.manifest.get("cuts") or {}
        for k in ("fit_cut", "guard_cut"):
            if k not in mc or int(mc[k]) != int(run.cuts[self.lead][k]):
                _refuse("export %s %s %r differs from the run's derived R11 %r"
                        % (self.dir, k, mc.get(k), run.cuts[self.lead][k]))
        # the files: groups come from the manifest's list, never from a folder listing; a stray or missing
        # file refuses (leak-fairness review 4, parity review 2)
        listed = self.manifest.get("files") or []
        if not listed:
            _refuse("export manifest %s lists no file" % mpath)
        self._entry: Dict[str, Dict[str, Mapping[str, Any]]] = {}
        for f in listed:
            part = str(f["part"])
            stem = Path(str(f["path"])).stem
            if stem in self._entry.setdefault(part, {}):
                _refuse("export manifest %s lists %s/%s twice" % (mpath, part, stem))
            self._entry[part][stem] = f
        for part in (TRAIN_DIR, GUARD_DIR, TEST_DIR):
            want = sorted(str(e["path"]) for e in self._entry.get(part, {}).values())
            pdir = self.dir / part
            have = sorted(p.relative_to(self.dir).as_posix() for p in pdir.glob("*.parquet")) if pdir.is_dir() else []
            if want != have:
                extra = sorted(set(have) - set(want))
                gone = sorted(set(want) - set(have))
                _refuse("export %s: the %s files on disk differ from the manifest's list (not listed: %s; missing: "
                        "%s)" % (self.dir, part, extra[:5], gone[:5]),
                        fix="re-export this lead with --resume; never add or edit an export file by hand")
        units = [e for e in self._entry.get(UNITS_PART, {}).values()]
        if len(units) != 1 or Path(str(units[0]["path"])).name != UNITS_FILE:
            _refuse("export manifest %s does not list one %s" % (mpath, UNITS_FILE))
        self.groups = sorted(self._entry.get(TRAIN_DIR, {}))
        if not self.groups:
            _refuse("export %s holds no %s/*.parquet" % (self.dir, TRAIN_DIR))
        names = None
        for g in self.groups:
            s = pq.read_schema(self.path(TRAIN_DIR, g, verify=False)).names
            if names is None:
                names = s
            elif s != names:
                _refuse("export group files hold different columns (%s vs the first group)" % g)
        self.train_columns = list(names)
        missing = [k for k in KEYS + FLAGS + ("y",) if k not in names]
        if missing:
            _refuse("export train files lack the columns %s" % missing)
        self.x_cols = [n for n in names if n.startswith(X_PREFIX)]
        self.c_cols = [n for n in names if n.startswith(C_PREFIX)]
        self.features = self.x_cols + self.c_cols
        for link in run.links:
            if NFIT_PREFIX + link not in names:
                _refuse("export train files lack %s%s (one normal per R22 link)" % (NFIT_PREFIX, link))
        self.h_cols: List[str] = []
        gstems = sorted(self._entry.get(GUARD_DIR, {}))
        if gstems:
            gnames = pq.read_schema(self.path(GUARD_DIR, gstems[0], verify=False)).names
            self.h_cols = [n for n in gnames if n.startswith(H_PREFIX)]
            for h in self.h_cols:
                if X_PREFIX + h[len(H_PREFIX):] not in self.x_cols:
                    _refuse("guardside column %s has no matching %s column" % (h, X_PREFIX + h[len(H_PREFIX):]))
            for link in run.links:
                if NGD_PREFIX + link not in gnames:
                    _refuse("export guardside files lack %s%s" % (NGD_PREFIX, link))
        hist = sorted(run.plan.get("history_columns") or [])
        if gstems and sorted(h[len(H_PREFIX):] for h in self.h_cols) != hist:
            _refuse("guardside history columns %s differ from plan.json history_columns %s" % (self.h_cols, hist))
        if not self.features:
            _refuse("export %s holds no feature column (%s* or %s*)" % (self.dir, X_PREFIX, C_PREFIX))
        self.guard_flags = (FLAG_TUNE, FLAG_INNER) if self.lead == 0 else (FLAG_GUARDFIT, FLAG_GUARD)

    # --- verified file access ----------------------------------------------------------------------
    def path(self, part: str, stem: str, verify: bool = True) -> Path:
        """The path of a listed export file. verify: its sha256 equals the manifest's (checked once per process
        per file; a changed size or modification time checks again). Refuses an unlisted file."""
        e = self._entry.get(part, {}).get(stem)
        if e is None:
            _refuse("export %s: %s/%s is not listed in the manifest" % (self.dir, part, stem))
        p = self.dir / str(e["path"])
        if not p.is_file():
            _refuse("export %s: the listed file %s is missing" % (self.dir, p))
        if verify:
            st = os.stat(str(p))
            key = os.path.normcase(str(p.resolve()))
            hit = _VERIFIED.get(key)
            if hit is None or hit != (int(st.st_size), int(st.st_mtime_ns), str(e["sha256"])):
                sha = sha256_file(p)
                if sha != str(e["sha256"]):
                    _refuse("export file %s has sha256 %s; the manifest lists %s (an edited or partly rewritten "
                            "export file)" % (p, sha[:16], str(e["sha256"])[:16]),
                            fix="re-export this lead with --resume")
                _VERIFIED[key] = (int(st.st_size), int(st.st_mtime_ns), sha)
        return p

    def files_sha(self, part: Optional[str] = None) -> str:
        """sha256 of the sorted (path, sha256) list of the manifest's files (of one part, or all)."""
        rows = sorted([str(e["path"]), str(e["sha256"])] for p, d in self._entry.items() for e in d.values()
                      if part is None or p == part)
        return sha256_bytes(dumps_canonical(rows).encode("ascii"))

    def read_table(self, part: str, stem: str, columns: Optional[Sequence[str]] = None) -> pd.DataFrame:
        with pq.ParquetFile(str(self.path(part, stem))) as pf:
            return pf.read(columns=None if columns is None else list(columns)).to_pandas()

    # --- units ------------------------------------------------------------------------------------
    def units(self) -> pd.DataFrame:
        u = self.read_table(UNITS_PART, Path(UNITS_FILE).stem)
        for c in ("unit", "group"):
            if c not in u.columns:
                _refuse("%s lacks the column %s" % (self.dir / UNITS_FILE, c))
        return u

    # --- the cut rules, re-checked on every row read (leak-fairness review 3) ---------------------
    def _check_rows(self, set_name: str, keys: pd.DataFrame, where: Any):
        """Refuse any row read into a set that breaks its cut: refit <= fit cut; tune / guard-fit <= the lead's
        guard cut; inner / guard after the nowcast guard cut and <= the lead's fit cut; test after the fit cut;
        and issue = time - lead on every row."""
        if not len(keys):
            return
        t = keys["time"].to_numpy(np.int64)
        fit_cut = int(self.run.cuts[self.lead]["fit_cut"])
        guard_cut = int(self.run.cuts[self.lead]["guard_cut"])
        guard0 = int(self.run.cuts[0]["guard_cut"])
        if set_name == "refit":
            bad = t > fit_cut
            rule = "at or before the fit cut %d" % fit_cut
        elif set_name in ("tune", "guardfit"):
            bad = t > guard_cut
            rule = "at or before the guard cut %d" % guard_cut
        elif set_name in ("inner", "guard"):
            bad = (t <= guard0) | (t > fit_cut)
            rule = "after the nowcast guard cut %d and at or before the fit cut %d" % (guard0, fit_cut)
        elif set_name == "test":
            bad = t <= fit_cut
            rule = "after the fit cut %d" % fit_cut
        else:
            _refuse("internal: unknown set %s" % set_name)
        if bad.any():
            _refuse("export %s, %s: %d %s row(s) break the cut rule (%s); first time %d"
                    % (self.dir, where, int(bad.sum()), set_name, rule, int(t[bad][0])),
                    fix="the export is wrong; re-export it and report the defect")
        if "issue" in keys.columns and "lead" in keys.columns:
            iss = keys["issue"].to_numpy(np.int64)
            ld = keys["lead"].to_numpy(np.int64)
            if not np.array_equal(iss, t - ld):
                _refuse("export %s, %s: %s rows where issue != time - lead" % (self.dir, where, set_name))
            if (ld != self.lead).any():
                _refuse("export %s, %s: %s rows of another lead" % (self.dir, where, set_name))

    def _check_disjoint(self, t: pd.DataFrame, where: Any):
        """No (unit, time, issue) of a fit set is also a row of its score set (tune vs inner; guard-fit vs
        guard), in one group file."""
        fit_flag, score_flag = self.guard_flags
        a = t.loc[t[fit_flag].to_numpy(bool), ["unit", "time", "issue"]]
        b = t.loc[t[score_flag].to_numpy(bool), ["unit", "time", "issue"]]
        if len(a) and len(b):
            ka = set(zip(a["unit"].astype(str), a["time"].astype(np.int64), a["issue"].astype(np.int64)))
            kb = set(zip(b["unit"].astype(str), b["time"].astype(np.int64), b["issue"].astype(np.int64)))
            both = ka & kb
            if both:
                _refuse("export %s, %s: %d row key(s) are both %s and %s rows" % (self.dir, where, len(both),
                                                                                  fit_flag, score_flag))

    # --- one group of one set ---------------------------------------------------------------------
    def _group_block(self, g: str, set_name: str):
        flag, side = SETS[set_name]
        if set_name == "test":
            if g not in self._entry.get(TEST_DIR, {}):
                return None
            path = self.path(TEST_DIR, g)
            schema = pq.read_schema(path).names
            if "y" in schema:
                _refuse("export test file %s holds a y column; test labels never leave the vault" % path)
            cols = list(KEYS) + self.features + [NFIT_PREFIX + l for l in self.run.links]
            t = pq.read_table(path, columns=cols).to_pandas()
            self._check_rows("test", t[list(KEYS)], path.name)
            normal = {l: t[NFIT_PREFIX + l].to_numpy(np.float64) for l in self.run.links}
            return t[list(KEYS)], None, t[self.features].to_numpy(np.float32), normal
        if flag not in self.guard_flags and side == "guard":
            _refuse("set %s is not a guard-side set at lead %d" % (set_name, self.lead))
        cols = list(KEYS) + list(FLAGS) + ["y"] + self.features
        if side == "fit":
            cols += [NFIT_PREFIX + l for l in self.run.links]
        t = self.read_table(TRAIN_DIR, g, cols)
        mask = t[flag].to_numpy(bool)
        if not mask.any():
            return None
        X = t.loc[mask, self.features].to_numpy(np.float32)
        keys = t.loc[mask, list(KEYS)].reset_index(drop=True)
        self._check_rows(set_name, keys, "train/%s" % g)
        y = t.loc[mask, "y"].to_numpy(np.float64)
        if side == "fit":
            normal = {l: t.loc[mask, NFIT_PREFIX + l].to_numpy(np.float64) for l in self.run.links}
            return keys, y, X, normal
        self._check_disjoint(t, "train/%s" % g)
        union = np.zeros(len(t), dtype=bool)
        for f in self.guard_flags:
            union |= t[f].to_numpy(bool)
        gcols = list(KEYS) + self.h_cols + [NGD_PREFIX + l for l in self.run.links]
        gt = self.read_table(GUARD_DIR, g, gcols)
        gpath = self.dir / GUARD_DIR / (g + ".parquet")
        if len(gt) != int(union.sum()):
            _refuse("guardside %s holds %d rows; train flags %s mark %d" % (gpath, len(gt), self.guard_flags, int(union.sum())))
        pos = (np.cumsum(union) - 1)[mask]
        gsel = gt.iloc[pos].reset_index(drop=True)
        for k in ("unit", "time", "issue"):
            if not np.array_equal(gsel[k].to_numpy(), keys[k].to_numpy()):
                _refuse("guardside %s rows are not in train order (key %s)" % (gpath, k))
        for h in self.h_cols:
            j = self.features.index(X_PREFIX + h[len(H_PREFIX):])
            X[:, j] = gsel[h].to_numpy(np.float32)
        normal = {l: gsel[NGD_PREFIX + l].to_numpy(np.float64) for l in self.run.links}
        return keys, y, X, normal

    def count(self, set_name: str) -> int:
        flag, _ = SETS[set_name]
        if flag is None:
            _refuse("count() is for train-side sets")
        n = 0
        for g in self.groups:
            t = self.read_table(TRAIN_DIR, g, [flag])
            n += int(np.asarray(t[flag].to_numpy(), dtype=bool).sum())
        return n

    def read_set(self, set_name: str, into: Any = None):
        """(keys DataFrame, y or None, X float32 rows x features, {link: normal}) in group order.
        into: an open writable memmap with the right shape (rows are written into it)."""
        keys, ys, Xs, normals = [], [], [], {l: [] for l in self.run.links}
        at = 0
        groups = self.groups
        if set_name == "test":
            groups = sorted(self._entry.get(TEST_DIR, {}))
            if not groups:
                _refuse("export %s has no %s files" % (self.dir, TEST_DIR))
        for g in groups:
            blk = self._group_block(g, set_name)
            if blk is None:
                continue
            k, y, X, nm = blk
            keys.append(k)
            if y is not None:
                ys.append(y)
            if into is not None:
                into[at:at + X.shape[0]] = X
            else:
                Xs.append(X)
            at += X.shape[0]
            for l in self.run.links:
                normals[l].append(nm[l])
        if at == 0:
            _refuse("export %s holds no %s row at lead %d" % (self.dir, set_name, self.lead))
        K = pd.concat(keys, ignore_index=True)
        y = np.concatenate(ys) if ys else None
        X = None if into is not None else np.concatenate(Xs, axis=0)
        nm = {l: np.concatenate(v) for l, v in normals.items()}
        if y is not None and not np.isfinite(y).all():
            _refuse("export set %s holds %d missing labels" % (set_name, int((~np.isfinite(y)).sum())))
        dup = K.duplicated(subset=["unit", "time", "issue"])
        if dup.any():
            _refuse("export set %s names a (unit, time, issue) twice (%d rows)" % (set_name, int(dup.sum())))
        return K, y, X, nm


def _lead_export_dir(board: Mapping[str, Any], lead: int) -> Path:
    base = Path(board["export"]["lead_0"]["dir"])
    return base if lead == 0 else base.parent / ("lead_%d" % lead)


def export_lead(board: Mapping[str, Any], run: Run, lead: int) -> ExportLead:
    """The lead's export, checked against the board: the same identity as lead 0 (run, package, engine,
    export code, derived, links, legal range), the run's c for the lead, and (lead 0) the content hash taken
    at init. A rebuilt export with the same content passes (parity review 1 and 10; robustness review 6)."""
    ex = ExportLead(_lead_export_dir(board, lead), lead, run)
    check_accept_seal(ex, run)
    want = board["export"]["identity"]
    got = export_identity(ex.manifest)
    diff = sorted(k for k in set(want) | set(got) if _clean(want.get(k)) != _clean(got.get(k)))
    if diff:
        _refuse("lead %d export %s differs from the board's lead-0 export in %s (%s vs %s)"
                % (lead, ex.dir, diff, [got.get(k) for k in diff], [want.get(k) for k in diff]),
                fix="export every lead of a board with the same engine, package and export code")
    c_run = board["run"]["c"].get(str(lead))
    c_man = ex.manifest.get("c")
    if (c_run is None) != (c_man is None) or (c_run is not None and float(c_run) != float(c_man)):
        _refuse("lead %d export c %r differs from the run's derived R23 %r" % (lead, c_man, c_run))
    legal = tuple(float(v) for v in board["run"]["legal"])
    if _legal_of_manifest(ex.manifest) != legal:
        _refuse("lead %d export legal range %s differs from the run's R28 %s"
                % (lead, _legal_of_manifest(ex.manifest), legal))
    if lead == 0 and ex.content_sha != board["export"]["lead_0"]["content_sha256"]:
        _refuse("the lead-0 export content changed since init (content sha %s vs %s)"
                % (ex.content_sha[:16], board["export"]["lead_0"]["content_sha256"][:16]),
                fix="the board is bound to its lead-0 export's content; restore it or init a new board")
    return ex


# ===================================================================================================
# Fit sets: materialized float32 memmaps (spec 3.10)
def materialized_dir(ctx: Ctx) -> Path:
    """Where the fit-set copies go: <scratch_root>/<package>/<run>/ when rivals.yaml names a scratch_root,
    else <board>/materialized/. They are rebuildable caches (their sha256 stays in the kept json)."""
    sr = ctx.cfg.get(SCRATCH_KEY)
    if sr:
        return Path(sr) / ctx.out.parent.name / ctx.out.name
    return ctx.out / MATERIALIZED_DIR


def materialize(ctx: Ctx, ex: ExportLead, set_name: str) -> M.FitData:
    """The fit set as a float32 C-ordered memmap (written once with its sha) + its index parquet.
    Refuses before writing when the drive lacks the copy's size + 3 GiB (robustness review 3); a temp file
    left by a killed copy is moved aside first (robustness review 7)."""
    mdir = ctx.mkdir(materialized_dir(ctx))
    stem = "lead_%d_%s" % (ex.lead, set_name)
    f32, idx, meta_p = mdir / (stem + ".f32"), mdir / (stem + ".index.parquet"), mdir / (stem + ".json")
    for old in sorted(mdir.glob(stem + ".f32.tmp_*")) + sorted(mdir.glob(stem + ".index.parquet.tmp_*")):
        ctx.log("materialized", message="a temp file of a killed copy (%.2f GiB) is moved aside: %s"
                % (os.path.getsize(old) / M.GIB, old))
        ctx.move_aside(old)
    want = {"set": set_name, "lead": ex.lead, "export_content_sha256": ex.content_sha,
            "export_files_sha256": ex.files_sha(), "columns": ex.features}
    if meta_p.is_file():
        meta = read_json(meta_p)
        ok = all(meta.get(k) == v for k, v in want.items()) and f32.is_file() and idx.is_file()
        if ok and os.path.getsize(f32) == int(meta["rows"]) * len(ex.features) * 4                 and sha256_file(f32) == meta["sha256"] and sha256_file(idx) == meta["index_sha256"]:
            ctx.log("materialized", message="reused %s (%d rows)" % (f32.name, meta["rows"]))
            return _open_fit(ex, set_name, f32, idx, int(meta["rows"]))
        for p in (meta_p, f32, idx):
            if p.is_file() and p.suffix == ".f32":
                ctx.log("materialized", message="a stale copy (%.2f GiB) is moved aside; the owner may delete it "
                        "after the board is done: %s" % (os.path.getsize(p) / M.GIB, p))
            ctx.move_aside(p)
    else:
        for p in (f32, idx):
            ctx.move_aside(p)
    n = ex.count(set_name)
    if n == 0:
        _refuse("export %s holds no %s row" % (ex.dir, set_name))
    p = len(ex.features)
    need = n * max(p, 1) * 4 + DISK_SLACK
    free = shutil.disk_usage(str(mdir)).free
    if free < need:
        _refuse("the fit-set copy of %s needs %.2f GiB + 3 GiB on %s; %.2f GiB is free"
                % (stem, (need - DISK_SLACK) / M.GIB, mdir, free / M.GIB),
                fix="free disk (old fit-set copies listed in rivals.log as 'may delete' are safe to delete), "
                    "then resume")
    t0 = time.time()
    tmp = Path(str(f32) + ".tmp_%d" % os.getpid())
    ctx.eng.writable(tmp)
    mm = np.memmap(str(tmp), dtype=np.float32, mode="w+", shape=(n, max(p, 1)))
    K, y, _, nm = ex.read_set(set_name, into=mm)
    if len(K) != n:
        _refuse("set %s: %d rows written, %d counted" % (set_name, len(K), n))
    mm.flush()
    del mm
    gc.collect()
    os.replace(str(tmp), str(f32))
    frame = K.copy()
    frame["y"] = y
    for l, v in nm.items():
        frame["n__" + l] = v
    ctx.write_parquet(idx, frame)
    meta = dict(want, rows=n, sha256=sha256_file(f32), index_sha256=sha256_file(idx))
    ctx.replace_json(meta_p, meta)
    ctx.log("materialized", seconds=time.time() - t0, message="%s: %d rows x %d columns (%.2f GiB)"
            % (f32.name, n, p, os.path.getsize(f32) / M.GIB))
    return _open_fit(ex, set_name, f32, idx, n)


def _open_fit(ex: ExportLead, set_name: str, f32: Path, idx: Path, n: int) -> M.FitData:
    X = np.memmap(str(f32), dtype=np.float32, mode="r", shape=(n, len(ex.features)))
    frame = pq.read_table(idx).to_pandas()
    normal = {l: frame["n__" + l].to_numpy(np.float64) for l in ex.run.links}
    fd = M.FitData(name="lead_%d_%s" % (ex.lead, set_name), X=X, columns=tuple(ex.features),
                   y=frame["y"].to_numpy(np.float64), normal=normal)
    fd.meta["keys"] = frame[list(KEYS)]
    return fd


def score_set(ex: ExportLead, set_name: str):
    """(ScoreData, keys, y or None) of a score set, in RAM."""
    K, y, X, nm = ex.read_set(set_name)
    return M.ScoreData(name=set_name, X=X, normal=nm), K, y


def board_rf_method() -> Dict[str, Any]:
    """The board's RF record (ruling Z2, replaces the bank-unit stride of Q9 b): every RF fit (tune, guard-fit,
    refit) sees ALL its fit-set rows, out of core, each tree on its own drawn sample."""
    return {"method": M.RF_METHOD, "rows_per_tree": "min(%d, fit rows)" % M.RF_ROWS_PER_TREE,
            "trees": M.RF_TREES, "budget_bytes": M.RF_RAM_BUDGET, "fit_factor": M.RF_FIT_FACTOR,
            "read_block_bytes": M.RF_READ_BLOCK_BYTES, "checkpoint_every_trees": M.RF_CKPT_EVERY}


RF_CKPT_DIR = "rf_checkpoints"


class RFCheckpoint(M.RFStore):
    """An RF fit's checkpoint file <fit-set copies folder>/rf_checkpoints/<key>.npz, written atomically through
    the engine's registry. It holds the trees done and the running prediction sums (no tree, no label)."""

    def __init__(self, ctx: "Ctx", key: str):
        self.ctx = ctx
        self.key = key
        self.path = materialized_dir(ctx) / RF_CKPT_DIR / ("%s.npz" % key[:32])

    def load(self) -> Optional[bytes]:
        return self.path.read_bytes() if self.path.is_file() else None

    def save(self, data: bytes):
        self.ctx.mkdir(self.path.parent)
        self.ctx.replace_bytes(self.path, data)

    def finish(self):
        """After the fit's results are written: the checkpoint is moved aside (never deleted)."""
        if self.path.is_file():
            self.ctx.move_aside(self.path)


def rf_checkpoint(ctx: "Ctx", learner: str, *parts: Any) -> Optional[RFCheckpoint]:
    """The checkpoint store of one RF fit (None for the other learners); the key names the fit."""
    if learner != "rf":
        return None
    return RFCheckpoint(ctx, sha256_bytes(dumps_canonical([str(x) for x in parts]).encode("ascii")))


def ram_check(learner: str, rows: int, cols: int, score_rows: int = 0):
    """Go / refuse before a fit (spec 3.10). score_rows: the rows the fit predicts (the RF's plan holds a
    0-filled copy and a float64 sum per score row; Z2 check 3)."""
    import psutil
    if learner in ("lgbm", "lgbm_tweedie"):
        need = rows * cols * 1 + LGBM_RAM_EXTRA
    elif learner == "rf":
        need = M.rf_ram_need(rows, cols - 1, int(score_rows))   # out of core (Z2): its own plan, within budget
    elif learner == "hgb_l1":
        need = int(M.RF_PEAK_FACTOR * rows * cols * 4)
    else:
        need = RIDGE_RAM
    avail = psutil.virtual_memory().available
    if need > min(avail, WATCHDOG_LIMIT_BYTES):
        _refuse("%s needs about %.2f GiB for %d x %d; %.2f GiB is available (watchdog %.0f GiB)"
                % (learner, need / M.GIB, rows, cols, avail / M.GIB, WATCHDOG_LIMIT_BYTES / M.GIB),
                fix="close other apps and resume")


# ===================================================================================================
# The board's learners and trials
def learners_for(legal_min: float, zero_share: Optional[float], links: Sequence[str],
                 extra: Sequence[str] = ()) -> List[str]:
    """The lean board (Y1) from data rules only: ridge, rf, lgbm always; lgbm_tweedie when
    legal_min == 0 AND the zero share of the lead-0 refit labels >= 0.20 (it then needs the run's c,
    so log_c must be an R22 link, else REFUSE); hgb_l1 only when asked (--extra-learners)."""
    out = list(M.CORE_LEARNERS)
    if zero_share is None:
        _refuse("the zero share of the lead-0 refit labels is unknown")
    if float(legal_min) == 0.0 and float(zero_share) >= TWEEDIE_ZERO_SHARE:
        if "log_c" not in links:
            _refuse("lgbm_tweedie is switched on (legal_min 0, zero share %.3f >= %.2f) but log_c is not "
                    "an R22 link, so the run has no c for its offset" % (zero_share, TWEEDIE_ZERO_SHARE),
                    fix="OWNER ITEM: rule how the Tweedie offset is built without c")
        out.append("lgbm_tweedie")
    for e in extra:
        if e != "hgb_l1":
            _refuse("--extra-learners takes only hgb_l1, got %r" % e)
        if e not in out:
            out.append(e)
    return out


def board_learners(legal_min: float, zero_share: Optional[float], links: Sequence[str],
                   extra_learners: Sequence[str] = ()) -> Tuple[str, ...]:
    """The data rules of the lean board (spec 3.2) as a tuple of learner ids (see learners_for)."""
    return tuple(learners_for(legal_min, zero_share, links, extra_learners))


def setting_slug(setting: Mapping[str, Any]) -> str:
    if not setting:
        return "alphas"
    return "_".join("%s%s" % (k, v) for k, v in setting.items())


def trial_list(board: Mapping[str, Any], learner: str) -> List[Dict[str, Any]]:
    """The base trials of one learner in the fixed tie-break order (R22 link order, grid order)."""
    out = []
    links = board["run"]["links"] if M.uses_links(learner) else [None]
    for li, link in enumerate(links):
        for gi, st in enumerate(M.grid(learner)):
            tid = "%s__%s__%s" % (learner, link or "own_log", setting_slug(st))
            out.append({"trial_id": tid, "learner": learner, "link": link, "setting": dict(st),
                        "link_order": li, "grid_order": gi, "extended": False})
    return out


def trial_params(board: Mapping[str, Any], trial: Mapping[str, Any], lead: int) -> Dict[str, Any]:
    c = board["run"]["c"].get(str(lead))
    return dict(trial["setting"], link=trial["link"], c=c, ub=board["run"]["ub"])


def trial_hash(board: Mapping[str, Any], trial: Mapping[str, Any], cks: Sequence[Any]) -> str:
    rec = {"learner": trial["learner"], "setting": trial["setting"], "link": trial["link"],
           "checkpoints": [ck_label(k) for k in cks], "fit_set": "lead_0_tune",
           "export_content_sha256": board["export"]["lead_0"]["content_sha256"],
           "rf_method": board["rf"]["method"] if trial["learner"] == "rf" else None,
           "harness_code_sha256": board["harness_code_sha256"], "c": board["run"]["c"].get("0"),
           "ub": board["run"]["ub"], "extended": bool(trial.get("extended")),
           # early stopping, its extension rule and the bins of the tuning (AA2, AC1, AC2); None for a learner
           # without them
           "tuning": M.tuning_options(trial["learner"], bool(trial.get("extended")))}
    return sha256_bytes(dumps_canonical(rec).encode("ascii"))


# ---- pick and extension rules (pure; spec 3.5) -----------------------------------------------------
# A "row" is one trial at one checkpoint: {trial_id, link_order, grid_order, checkpoint, inner_mae}.
def _ck_num(ck: Any) -> float:
    return float(ck)


def _row_key(r: Mapping[str, Any]) -> Tuple[int, int, float]:
    return (int(r["link_order"]), int(r["grid_order"]), _ck_num(r["checkpoint"]))


def pick_learner(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """The pick over setting x link x checkpoint: the lowest inner MAE; ties broken by the fixed order
    (R22 link order, then grid order, then the smaller checkpoint)."""
    best = None
    for r in sorted(rows, key=_row_key):
        v = float(r["inner_mae"])
        if not math.isfinite(v):
            _refuse("trial %s checkpoint %s has a non-finite inner MAE" % (r["trial_id"], r["checkpoint"]))
        if best is None or v < best["inner_mae"]:
            best = {"trial_id": r["trial_id"], "checkpoint": r["checkpoint"], "inner_mae": v,
                    "link_order": int(r["link_order"]), "grid_order": int(r["grid_order"])}
    if best is None:
        _refuse("no trial result to pick from")
    return best


def own_best(rows: Sequence[Mapping[str, Any]], trial_id: str, max_checkpoint: Optional[float] = None):
    """(checkpoint, MAE) of one trial's own best (ties -> the smaller checkpoint)."""
    sub = [r for r in rows if r["trial_id"] == trial_id
           and (max_checkpoint is None or _ck_num(r["checkpoint"]) <= max_checkpoint)]
    if not sub:
        _refuse("no row for trial %s" % trial_id)
    p = pick_learner(sub)
    return p["checkpoint"], p["inner_mae"]


def trials_to_extend(rows: Sequence[Mapping[str, Any]], pick: Optional[Mapping[str, Any]] = None,
                     ran_to_cap: Optional[Mapping[str, bool]] = None) -> List[str]:
    """Y2, reading R-Y2 b (rivals review, leak-fairness 1), with AA2 and AC2: EVERY trial whose OWN best over its
    base rounds (up to 800) lies in the last stage before the cap, (400, 800], is refit from scratch with cap 1600
    and re-picked, whatever the learner's pick is, EXCEPT (AC2) an early-stopped trial that stopped by patience.
    A staged learner (hgb_l1) is scored at 100, 200, 400, 800 only, so for it this is "own best at 800" (ran_to_cap
    None). An early-stopped learner (lgbm, lgbm_tweedie) passes ran_to_cap {trial_id: models.ran_to_cap(its
    early-stopping record)} for every trial: only a trial that ran to the 800 cap without a patience stop is
    extended (its best round then lies in (650, 800] with patience 150, ruling AD); one stopped by patience would only repeat
    itself. A trial whose rows already hold a round above 800 is never extended again; a pick in (1200, 1600] is
    flagged. Ridge alphas and the RF tree count are never asked (the caller passes boosting learners only).
    `pick` is kept for the old call shape and is not used."""
    edge = float(M.EDGE_ROUNDS)
    seen: List[str] = []
    extended = set()
    for r in sorted(rows, key=_row_key):
        if r["trial_id"] not in seen:
            seen.append(r["trial_id"])
        if _ck_num(r["checkpoint"]) > edge:
            extended.add(r["trial_id"])
    if ran_to_cap is not None:
        missing = [tid for tid in seen if tid not in ran_to_cap]
        if missing:
            _refuse("the extension rule (AC2) has no cap record for trials %s" % missing)
    out = []
    for tid in seen:
        if tid in extended:
            continue
        if ran_to_cap is not None and not bool(ran_to_cap[tid]):
            continue                    # AC2: stopped by patience inside the 800 cap -> never extended
        ck, _ = own_best(rows, tid, edge)
        if M.in_last_stage(ck):
            out.append(tid)
    return out


def check_extension_prefix(base_pre: Mapping[Any, np.ndarray], ext_pre: Mapping[Any, np.ndarray],
                           trial_id: str = ""):
    """The extended refit's predictions at every round the base trial kept (100-800 for a staged learner; the
    stages reached and the best round for an early-stopped one) must equal the base trial's byte for byte (keys
    are checkpoints as numbers or labels)."""
    b = {ck_label(int(float(k))): v for k, v in base_pre.items()}
    e = {ck_label(int(float(k))): v for k, v in ext_pre.items()}
    if not b:
        _refuse("determinism check: the base trial %s kept no round" % trial_id)
    for lab in sorted(b, key=lambda x: int(x)):
        if lab not in b or lab not in e:
            _refuse("determinism check: checkpoint %s is missing for trial %s" % (lab, trial_id))
        x, y = np.asarray(b[lab], dtype=np.float64), np.asarray(e[lab], dtype=np.float64)
        if x.shape != y.shape or x.tobytes() != y.tobytes():
            _refuse("determinism check failed: trial %s refit to %d rounds does not reproduce its "
                    "checkpoint %s byte for byte" % (trial_id, M.LAST_ROUNDS, lab))


def pick_flags(learner: str, pick: Mapping[str, Any]) -> List[str]:
    """Edge flags, printed only, never extended: edge_rounds_1600 (a booster picked in the last stage before the
    1600 cap, (1200, 1600]; for the staged hgb_l1 that is 1600); the lower edge: edge_rounds_100 for a booster scored
    at stages only (hgb_l1: a pick at the first stage, 100), edge_round_1 for an early-stopped booster (a pick at
    round 1, the lowest round it can pick; any other round is an interior best, AA2 review item 4);
    edge_alpha_1e6 and edge_alpha_0.1 (ridge at either end of its alpha grid). Rivals review, leak-fairness 5."""
    flags = []
    ck = _ck_num(pick["checkpoint"])
    if learner in M.STAGED_LEARNERS:
        if M.in_last_stage(ck, extended=True):
            flags.append("edge_rounds_1600")
        if learner in M.EARLY_STOP_LEARNERS:
            if ck <= 1.0:
                flags.append("edge_round_1")
        elif ck <= float(M.BASE_ROUNDS[0]):
            flags.append("edge_rounds_100")
    if learner == "ridge":
        if ck == float(M.RIDGE_ALPHAS[-1]):
            flags.append("edge_alpha_1e6")
        if ck == float(M.RIDGE_ALPHAS[0]):
            flags.append("edge_alpha_0.1")
    return flags


# ===================================================================================================
# Scoring helpers (engine functions)
def clip(eng: Engine, pre: np.ndarray, legal: Tuple[float, float]) -> np.ndarray:
    return eng.links.clip_to_legal(np.asarray(pre, dtype=np.float64), legal, False)[0]


def inner_metrics(eng: Engine, y: np.ndarray, pred: np.ndarray, legal) -> Dict[str, float]:
    m = eng.metrics
    zero = m.baseline_predict_zero(int(y.size), legal)
    return {"mae": m.mae(y, pred), "corr2": m.corr2(y, pred),
            "calibration_ratio": m.calibration_ratio(y, pred), "predict_zero_mae": m.mae(y, zero)}


# ===================================================================================================
# init
RUN_FILES = ("manifest.json", "derived.json", "plan.json", "verdict.json", "decision_checks.json",
             "inner_preds.parquet", "score_by_group.csv", "score_pooled.csv")
LEAD_RUN_FILES = ("lead.json", "guard_preds.parquet")


def run_file_shas(run: Run) -> Dict[str, str]:
    """sha256 of the run files the board reads before the lock (never a test_preds file: those are hashed when
    the test labels are opened). Parity review 10."""
    out = {}
    for name in RUN_FILES:
        p = run.folder / name
        if p.is_file():
            out[name] = sha256_file(p)
    for L in run.leads:
        if L == 0:
            continue
        for name in LEAD_RUN_FILES:
            p = run.folder / "ladder" / ("lead_%d" % L) / name
            if p.is_file():
                out["ladder/lead_%d/%s" % (L, name)] = sha256_file(p)
    return out


def engine_file_sha() -> str:
    """The LIVE engine's file sha now (treeroute.runs.fingerprint.engine_code_sha256)."""
    from treeroute.runs.fingerprint import engine_code_sha256
    return engine_code_sha256()


# ---- the run's ledger: kept OUTSIDE the board folder (leak-fairness review 2) ---------------------
def ledger_path(out: Path, fingerprint: str) -> Path:
    return Path(out).parent.parent / LEDGER_DIR / ("%s.jsonl" % fingerprint)


def ledger_read(out: Path, fingerprint: str) -> List[Dict[str, Any]]:
    p = ledger_path(out, fingerprint)
    if not p.is_file():
        return []
    rows = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                _refuse("the ledger %s line %d is not JSON" % (p, i + 1), fix="the ledger is append-only; restore it")
    return rows


def ledger_append(ctx: Ctx, fingerprint: str, rec: Mapping[str, Any]):
    p = ledger_path(ctx.out, fingerprint)
    ctx.eng.writable(p)
    LY.append_line(p, dumps_canonical(dict(rec, utc=utc_now(), board=str(ctx.out))), ctx.eng.registry)


def picks_content_sha(picks: Mapping[str, Any]) -> str:
    """The hash of WHAT was picked (learner -> trial, extension, link, setting, checkpoint), independent of the
    board folder and code hash, so a reproduced tuning has the same content hash."""
    rec = {L: {k: p.get(k) for k in ("trial_id", "extended", "link", "setting", "checkpoint")}
           for L, p in sorted(picks.items())}
    return sha256_bytes(dumps_canonical(rec).encode("ascii"))


def ledger_openings(out: Path, fingerprint: Optional[str]) -> List[Dict[str, Any]]:
    if not fingerprint:
        return []
    return [r for r in ledger_read(out, fingerprint) if r.get("event") == "test_labels_opened"]


def test_side_files(out: Path) -> List[Path]:
    """Any trace of a test row in the board folder: a test-label record, or a lead's predictions."""
    out = Path(out)
    found = sorted(out.glob("test_labels_opened_rivals_lead_*.json"))
    found += sorted(out.glob("lead_*/preds_*.parquet"))
    return found


def init(run: Any, export: Any, out_root: Any, extra_learners: Sequence[str] = (), config: Any = None) -> Path:
    """Write board.json once (spec 3.1). Returns the board folder <out_root>/<package>/<run name>."""
    cfg = load_config(config)
    eng = Engine(cfg)
    r = Run(run)
    out = Path(out_root) / r.package / r.name
    ctx = Ctx(cfg, eng, out, "init")
    lock = eng.preflight.HeavyJobLock(eng.machine.temp_dir)
    lock.acquire()
    try:
        ex = ExportLead(export, 0, r)
        check_accept_seal(ex, r)
        ident = export_identity(ex.manifest)
        live = engine_file_sha()
        if ident["engine_live_file_sha"] != live:
            _refuse("the lead-0 export was made under engine %s; LIVE is now %s"
                    % (ident["engine_live_file_sha"][:8], live[:8]), fix="re-export under the LIVE engine")
        zero_share, rule_src = _zero_share(ex)
        learners = learners_for(r.legal[0], zero_share, r.links, extra_learners)
        threads = thread_state()
        board = {
            "format": BOARD_FORMAT,
            "run": {"folder": str(r.folder), "name": r.name, "fingerprint": r.fingerprint,
                    "package": r.package, "kind": r.kind, "router_kind": r.router_kind,
                    "links": r.links, "leads": r.leads, "cuts": {str(k): v for k, v in r.cuts.items()},
                    "c": {str(L): r.c(L) for L in r.leads}, "legal": list(r.legal), "ub": r.ub,
                    "band": r.band, "hit_tolerance": r.tol, "measurement_error_floor": r.floor,
                    "decline_target": r.decline_target, "v1_donor_median_guard": r.v1,
                    "file_sha256": run_file_shas(r)},
            "export": {"lead_0": {"dir": str(Path(export)), "manifest_sha256": ex.manifest_sha,
                                  "content_sha256": ex.content_sha, "files_sha256": ex.files_sha(),
                                  "features": len(ex.features), "history_columns": ex.h_cols,
                                  "context_columns": ex.c_cols},
                       "identity": ident},
            "engine": {"live_file_sha": ident["engine_live_file_sha"],
                       "live_stripped_now": (ex.manifest.get("engine") or {}).get("live_stripped_now"),
                       "export_code_sha256": ident["export_code_sha256"],
                       # an owner-accepted engine difference of this run (export.py acceptance_record), or None
                       "accepted_difference": (ex.manifest.get("engine") or {}).get("accepted_difference")},
            "rf": board_rf_method(),
            "data_rules": {"legal_min": r.legal[0], "refit_y_zero_share": zero_share,
                           "zero_share_source": rule_src, "tweedie_zero_share": TWEEDIE_ZERO_SHARE,
                           "log_c_in_links": "log_c" in r.links, "extra_learners": list(extra_learners)},
            "learners": [{"id": L, "loss": M.LOSS[L], "fixed": M.fixed_params(L),
                          "grid": M.grid(L), "uses_links": M.uses_links(L),
                          "trials": len(trial_list({"run": {"links": r.links}}, L)),
                          "checkpoints": [ck_label(k) for k in M.checkpoints(L)],
                          "labels": (["timid-prone"] if L == "hgb_l1" else [])} for L in learners],
            "rules": {"pick": "lowest inner MAE of the clipped prediction over setting x link x "
                              "checkpoint (lgbm, lgbm_tweedie: x every round up to the early stop); ties: R22 "
                              "link order, grid order, smaller checkpoint",
                      "extension": "Y2 reading R-Y2 b with AC2: hgb_l1 (scored at 100, 200, 400, 800 only): every "
                                   "trial whose own best is 800; lgbm and lgbm_tweedie: only a trial that ran to the "
                                   "800 cap without a patience stop (its best round then in the last stage before "
                                   "the cap, (400, 800]); a trial stopped by patience is never extended (AC2). An "
                                   "extended trial is refit from scratch with cap 1600 and the learner is re-picked "
                                   "over all its trials; a pick in (1200, 1600] is flagged, never extended",
                      "early_stopping": "AA2: lgbm and lgbm_tweedie tuning trials score the inner window after "
                                        "every round and stop after %d rounds in a row without a strictly lower "
                                        "inner MAE, inside the cap (800, or 1600 extended); the trial's pick is its "
                                        "best round, chosen from every round on the same inner rows the lead-0 "
                                        "guard later uses (a small tilt in the rival's favour, disclosed); test rows "
                                        "are never read" % M.PATIENCE_ROUNDS,
                      "bins": "AC1 (replaces AA3): lgbm and lgbm_tweedie tune AND refit at LightGBM's default "
                              "%d histogram bins; a final fit differs from its tuning trial only by running the "
                              "picked round count with no early stopping, so the tuning trial at the pick is the "
                              "reported model's lead-0 guard model" % M.LGBM_MAX_BIN,
                      "edge_flags": "edge_rounds_100 (hgb_l1: a pick at 100 iterations), edge_round_1 (lgbm, "
                                    "lgbm_tweedie: a pick at round 1), edge_rounds_1600 (a pick in (1200, 1600]), "
                                    "edge_alpha_0.1, edge_alpha_1e6: printed only",
                      "offset": "the link normal is a fixed offset AND the last column (Q16 a)",
                      "missing": "trees 0-fill (R30); ridge fit-row mean + missing flags (Q7 a)",
                      "rf": "out of core (Z2): every RF fit sees all its fit-set rows; %d trees, each fitted "
                            "on its own sample of min(%d, rows) rows drawn with replacement from one "
                            "random_state-%d generator; the fit file is read in row blocks; RAM within "
                            "%.3g bytes" % (M.RF_TREES, M.RF_ROWS_PER_TREE, M.RANDOM_STATE, M.RF_RAM_BUDGET),
                      "guard": "N2 against the rival's own-link trees-off (V1 runs: the donor-row "
                               "median); fallback = the run's decline target; guarded decides; the guard model is "
                               "fitted with the final-fit options",
                      "tuning": "lead 0 only, inner window only; picks pinned at every lead",
                      "lock": "picks locked before any test file; tune / lock refuse once any test trace "
                              "exists; the run's ledger (outside the board) refuses a lock whose picks differ "
                              "from picks under which test labels were opened"},
            "our_inner_candidates": r.inner_candidates(),
            "threads": M.THREADS, "threadpool_info": threads,
            "harness_code_sha256": harness_code_sha(), "versions": library_versions(),
            "config": {k: cfg[k] for k in CONFIG_KEYS + (SCRATCH_KEY,)},
        }
        text = dumps_pretty(board)
        bp = out / BOARD_FILE
        if bp.is_file():
            if bp.read_text(encoding="utf-8") != text:
                _refuse("%s exists and differs from this init" % bp,
                        fix="init writes board.json once; use a new out root or move the old board aside")
            ctx.log("init", message="board.json exists and is identical; nothing written")
            return out
        ctx.mkdir(out)
        ctx.write_once_json(bp, board)
        keep_export_files(ctx, ex)
        n_trials = sum(b["trials"] for b in board["learners"])
        ctx.log("init", message="board: %s; %d base trials; our layer scored %d inner candidates; RF %s"
                % (", ".join(learners), n_trials, board["our_inner_candidates"], board["rf"]["method"]))
        opened = ledger_openings(out, r.fingerprint)
        if opened:
            ctx.log("init", message="NOTE: the run's ledger shows test labels opened before (%d time(s)); this "
                    "board's lock refuses unless its picks equal those picks" % len(opened))
        return out
    finally:
        lock.release()


def keep_export_files(ctx: Ctx, ex: ExportLead) -> Path:
    """Copy the lead's export_manifest.json and units.parquet into <board>/exports/lead_L/ (checked bytes), so a
    scored lead never needs its export again (robustness review 6). A rebuilt export with the same content keeps
    the first copy."""
    d = ctx.mkdir(ctx.out / EXPORT_COPY_DIR / ("lead_%d" % ex.lead))
    mp, up = d / EXPORT_MANIFEST, d / UNITS_FILE
    ubytes = ex.path(UNITS_PART, Path(UNITS_FILE).stem).read_bytes()
    if mp.is_file():
        kept = json.loads(mp.read_bytes().decode("utf-8"))
        if export_content_sha(kept) != ex.content_sha:
            _refuse("%s holds another export's manifest (content %s vs %s)"
                    % (mp, export_content_sha(kept)[:16], ex.content_sha[:16]),
                    fix="the lead was refit from another export; move %s aside to start the lead again" % d)
    else:
        ctx.replace_bytes(mp, ex.manifest_bytes)
    if up.is_file():
        if sha256_file(up) != sha256_bytes(ubytes):
            _refuse("%s differs from the export's units.parquet" % up)
    else:
        ctx.replace_bytes(up, ubytes)
    return d


def kept_units(out: Path, lead: int) -> pd.DataFrame:
    """The lead's units.parquet as kept in the board at refit, checked against the kept manifest's sha."""
    d = Path(out) / EXPORT_COPY_DIR / ("lead_%d" % int(lead))
    mp, up = d / EXPORT_MANIFEST, d / UNITS_FILE
    if not mp.is_file() or not up.is_file():
        _refuse("the board keeps no export files of lead %d (%s)" % (lead, d), fix="refit --lead %d first" % lead)
    man = read_json(mp)
    want = [f["sha256"] for f in man.get("files") or [] if str(f.get("part")) == UNITS_PART]
    if len(want) != 1 or sha256_file(up) != want[0]:
        _refuse("the kept %s does not match its kept manifest" % up)
    u = pq.read_table(up).to_pandas()
    for c in ("unit", "group"):
        if c not in u.columns:
            _refuse("%s lacks the column %s" % (up, c))
    return u


def _zero_share(ex: ExportLead) -> Tuple[float, str]:
    """Zero share of the lead-0 refit labels: from the refit rows, or the export manifest key
    when the export holds no refit row (a dry pass)."""
    vals = _find_key(ex.manifest, ZERO_SHARE_KEY)
    n_refit = ex.count("refit")
    if n_refit:
        ys = []
        for g in ex.groups:
            t = ex.read_table(TRAIN_DIR, g, [FLAG_REFIT, "y"])
            ys.append(t.loc[t[FLAG_REFIT].to_numpy(bool), "y"].to_numpy(np.float64))
        y = np.concatenate(ys)
        share = float(np.mean(y == 0.0))
        for v in vals:
            if v is not None and abs(float(v) - share) > 1e-12:
                _refuse("export manifest %s %r differs from the refit rows' %r" % (ZERO_SHARE_KEY, v, share))
        return share, "refit rows (%d)" % y.size
    if len(vals) != 1 or vals[0] is None:
        _refuse("the export holds no refit row and its manifest has no single %s" % ZERO_SHARE_KEY,
                fix="the export writes %s into export_manifest.json" % ZERO_SHARE_KEY)
    return float(vals[0]), "export manifest %s" % ZERO_SHARE_KEY


# ===================================================================================================
# Board checks run by every later command
def load_board(ctx: Ctx) -> Tuple[Dict[str, Any], Run]:
    bp = ctx.out / BOARD_FILE
    board = read_json(bp)
    if board.get("format") != BOARD_FORMAT:
        _refuse("%s is not a %s file" % (bp, BOARD_FORMAT))
    run = Run(board["run"]["folder"])
    check_run_identity(run, board)
    sha = harness_code_sha()
    if sha != board["harness_code_sha256"]:
        _refuse("the harness code changed since init (%s vs %s)" % (sha, board["harness_code_sha256"]),
                fix="a board runs under one harness code; init a new board")
    if library_versions() != board["versions"]:
        _refuse("library versions changed since init: %s vs %s" % (library_versions(), board["versions"]))
    th = thread_state()
    if th != board["threadpool_info"]:
        _refuse("the thread pools differ from init (%s vs %s); threads never change mid-board"
                % (th, board["threadpool_info"]))
    for k in CONFIG_KEYS + (SCRATCH_KEY,):
        if board["config"].get(k) != ctx.cfg.get(k):
            _refuse("config %s differs from board.json (%s vs %s)" % (k, ctx.cfg.get(k), board["config"].get(k)))
    live = engine_file_sha()
    if live != board["engine"]["live_file_sha"]:
        _refuse("the LIVE engine changed since init (file sha %s vs the board's %s)"
                % (live[:8], board["engine"]["live_file_sha"][:8]),
                fix="a board runs under one engine; re-export and init a new board (parity review 1)")
    now = run_file_shas(run)
    if now != board["run"]["file_sha256"]:
        diff = sorted(k for k in set(now) | set(board["run"]["file_sha256"])
                      if now.get(k) != board["run"]["file_sha256"].get(k))
        _refuse("run files changed since init: %s" % diff, fix="the run folder is read-only; restore it")
    return board, run


def learner_ids(board: Mapping[str, Any]) -> List[str]:
    """The board's learner ids in board order (board.json 'learners')."""
    return [b["id"] for b in board["learners"]]


# ===================================================================================================
# tune
def _trial_dir(ctx: Ctx, trial: Mapping[str, Any]) -> Path:
    tid = trial["trial_id"] + ("__ext" if trial.get("extended") else "")
    return ctx.out / TRIALS_DIR / trial["learner"] / tid


def _load_result(ctx: Ctx, board, trial) -> Optional[Dict[str, Any]]:
    """The finished trial.json when its config hash matches; a partial or stale folder is moved aside."""
    d = _trial_dir(ctx, trial)
    cks = M.checkpoints(trial["learner"], extended=bool(trial.get("extended")))
    h = trial_hash(board, trial, cks)
    tj = d / "trial.json"
    if tj.is_file():
        rec = read_json(tj)
        if rec.get("config_hash") == h and (d / "inner_preds.parquet").is_file() \
                and sha256_file(d / "inner_preds.parquet") == rec.get("inner_preds_sha256"):
            return rec
    if d.exists():
        ctx.move_aside(d)
    return None


def _run_trial(ctx: Ctx, board, run: Run, trial, fit: M.FitData, inner: M.ScoreData,
               inner_keys: pd.DataFrame, inner_y: np.ndarray, ex: ExportLead, cache: Dict) -> Dict[str, Any]:
    learner = trial["learner"]
    extended = bool(trial.get("extended"))
    cks = M.checkpoints(learner, extended=extended)
    h = trial_hash(board, trial, cks)
    d = _trial_dir(ctx, trial)
    legal = tuple(board["run"]["legal"])
    t0 = time.time()
    ram_check(learner, int(fit.X.shape[0]), len(fit.columns) + 1, int(inner.X.shape[0]))
    params = trial_params(board, trial, 0)
    store = rf_checkpoint(ctx, learner, "tune", h)
    es, base_rec = None, None
    extra = {}
    if learner in M.EARLY_STOP_LEARNERS:
        # AA2: early stopping on the inner window ONLY (the score set handed to the fit is the inner set; its
        # labels are the export's inner labels); AC1: the same 255 bins as every final fit
        if extended:
            base_rec = _read_done(ctx, board, dict(trial, extended=False))
            if base_rec is None:
                _refuse("the extension of %s needs its finished base trial" % trial["trial_id"])
        es = M.EarlyStop(score_set=inner.name, patience=M.PATIENCE_ROUNDS,
                         metric=lambda pre: float(ctx.eng.metrics.mae(inner_y, clip(ctx.eng, pre, legal))),
                         also_save=tuple(int(x) for x in (base_rec or {}).get("checkpoints", ())))
        extra = {"early_stop": es, "max_bin": M.LGBM_MAX_BIN}
    res = M.fit_predict(learner, params, fit, [inner], cks, cache=cache, rf_store=store,
                        rf_key=store.key if store else "", **extra)
    if set(res) != {inner.name}:
        _refuse("internal: a tuning fit scored %s, not only the inner set" % sorted(res))
    pre = {k: v["pre"] for k, v in res[inner.name].items()}
    kept = sorted(pre, key=float) if es is not None else list(cks)
    es_info = (getattr(res, "info", {}) or {}).get("early_stopping") if es is not None else None
    frame = inner_keys[["unit", "group", "time"]].copy()
    ck_mae, ck_rec = {}, {}
    for k in kept:
        lab = ck_label(k)
        p_clip = clip(ctx.eng, pre[k], legal)
        frame["pre__" + lab] = pre[k]
        frame["pred__" + lab] = p_clip
        met = inner_metrics(ctx.eng, inner_y, p_clip, legal)
        ck_mae[lab] = met["mae"]
        ck_rec[lab] = met
        if es_info is not None and met["mae"] != es_info["trace"][int(k) - 1]:
            _refuse("trial %s: the inner MAE at round %s (%r) is not the early-stopping trace's (%r)"
                    % (trial["trial_id"], lab, met["mae"], es_info["trace"][int(k) - 1]))
    if extended:
        base_d = _trial_dir(ctx, dict(trial, extended=False))
        base_labs = list(base_rec["checkpoints"]) if base_rec is not None else [ck_label(k) for k in M.BASE_ROUNDS]
        bt = pq.read_table(base_d / "inner_preds.parquet", columns=["pre__" + lab for lab in base_labs]).to_pandas()
        missing = [lab for lab in base_labs if int(lab) not in pre]
        if missing:
            _refuse("determinism check failed: trial %s extended does not reach the base trial's rounds %s"
                    % (trial["trial_id"], missing))
        check_extension_prefix({lab: bt["pre__" + lab].to_numpy() for lab in base_labs},
                               {lab: pre[int(lab)] for lab in base_labs}, trial["trial_id"])
        if base_rec is not None and es_info is not None:
            bt_trace = (base_rec.get("early_stopping") or {}).get("trace") or []
            if [float(x) for x in es_info["trace"][:len(bt_trace)]] != [float(x) for x in bt_trace]:
                _refuse("determinism check failed: trial %s extended does not reproduce its base trial's per-round "
                        "inner MAE" % trial["trial_id"])
    ctx.mkdir(d)
    ctx.write_parquet(d / "inner_preds.parquet", frame)
    info = dict(getattr(res, "info", {}) or {})
    info.pop("early_stopping", None)
    rec = {"trial_id": trial["trial_id"], "learner": learner, "link": trial["link"],
           "setting": trial["setting"], "link_order": trial["link_order"],
           "grid_order": trial["grid_order"], "extended": extended,
           "checkpoints": [ck_label(k) for k in kept], "config_hash": h, "metrics": ck_rec,
           "ck_mae": ck_mae, "n_inner": int(inner_y.size), "fit_info": _clean_info(info),
           "inner_preds_sha256": sha256_file(d / "inner_preds.parquet"),
           "seconds": time.time() - t0, "utc": utc_now()}
    if es_info is not None:
        # AA2: the patience, the cap, the best round, where it stopped, and the inner MAE after every round
        rec["early_stopping"] = _clean(es_info)
        rec["tuning"] = M.tuning_options(learner, extended)
    best, best_mae = own_best(trial_rows(rec), rec["trial_id"])
    rec["best_checkpoint"], rec["best_mae"] = ck_label(best), best_mae
    ctx.write_once_json(d / "trial.json", rec)
    if store is not None:
        store.finish()
    ctx.log("trial", learner, d.name, time.time() - t0, "%sbest inner MAE %s at %s"
            % (("[%s] " % ctx.progress) if getattr(ctx, "progress", "") else "", repr(best_mae), ck_label(best)))
    return rec


def _clean_info(info: Mapping[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in info.items():
        if k == "train_params":
            out[k] = {kk: vv for kk, vv in v.items()}
        else:
            out[k] = v
    return _clean(out)


def _ck_value(learner: str, label: str) -> Any:
    """A checkpoint label back to its value (alphas float, rounds and trees int)."""
    return float(label) if learner == "ridge" else int(label)


def trial_rows(rec: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """The flat pick rows of one trial record (one per checkpoint)."""
    return [{"trial_id": rec["trial_id"], "link_order": rec["link_order"], "grid_order": rec["grid_order"],
             "checkpoint": _ck_value(rec["learner"], lab), "inner_mae": float(rec["ck_mae"][lab])}
            for lab in rec["checkpoints"]]


def _read_done(ctx: Ctx, board, trial) -> Optional[Dict[str, Any]]:
    d = _trial_dir(ctx, trial)
    tj = d / "trial.json"
    if not tj.is_file():
        return None
    rec = read_json(tj)
    cks = M.checkpoints(trial["learner"], extended=bool(trial.get("extended")))
    if rec.get("config_hash") != trial_hash(board, trial, cks):
        return None
    if not (d / "inner_preds.parquet").is_file() or \
            sha256_file(d / "inner_preds.parquet") != rec.get("inner_preds_sha256"):
        return None
    return rec


def tune(out: Any, resume: bool = False, config: Any = None, hook: Any = None) -> Path:
    """Tune every learner on the lead-0 tune rows, scored on the inner rows (spec 3.5).
    hook: test-only callable(trial record) run after each finished trial."""
    with _Command("tune", out, config) as ctx:
        board, run = load_board(ctx)
        if (ctx.out / PICKS_LOCK).is_file():
            _refuse("the picks are locked; tuning never runs again after the lock")
        # any TEST_LABELS_OPENED record (test_labels_opened_rivals_lead_*.json) or lead_*/preds_* file refuses,
        # whether or not the lock file is still there (leak-fairness review 2)
        traces = test_side_files(ctx.out)
        if traces:
            _refuse("this board already holds test-side files (%s); tuning never runs after a test row was "
                    "touched" % [str(p) for p in traces[:3]])
        tdir = ctx.out / TRIALS_DIR
        if tdir.is_dir() and any(tdir.iterdir()) and not resume:
            _refuse("%s already holds trials" % tdir, fix="pass --resume")
        ex = export_lead(board, run, 0)
        fit = None
        inner = inner_keys = inner_y = None
        cache: Dict[Any, Any] = {}
        for learner in learner_ids(board):
            recs = []
            tl = trial_list(board, learner)
            for k, t in enumerate(tl):
                ctx.progress = "%d/%d" % (k + 1, len(tl))
                rec = _load_result(ctx, board, t)
                if rec is None:
                    if fit is None:
                        fit = materialize(ctx, ex, "tune")
                        inner, inner_keys, inner_y = score_set(ex, "inner")
                    rec = _run_trial(ctx, board, run, t, fit, inner, inner_keys, inner_y, ex, cache)
                    if hook is not None:
                        hook(rec)
                else:
                    ctx.log("trial", learner, t["trial_id"], message="skipped (finished, same config hash)", echo=False)
                recs.append(rec)
            ext_ids = _extension_ids(learner, recs)
            ext_list = [t for t in trial_list(board, learner) if t["trial_id"] in ext_ids]
            for k, t in enumerate(ext_list):
                ctx.progress = "extension %d/%d" % (k + 1, len(ext_list))
                te = dict(t, extended=True)
                rec = _load_result(ctx, board, te)
                if rec is None:
                    if fit is None:
                        fit = materialize(ctx, ex, "tune")
                        inner, inner_keys, inner_y = score_set(ex, "inner")
                    rec = _run_trial(ctx, board, run, te, fit, inner, inner_keys, inner_y, ex, cache)
                    if hook is not None:
                        hook(rec)
            ctx.progress = ""
            ctx.log("learner", learner, message="base grid done (%d trials); extended (%s): %s"
                    % (len(recs), "ran to the 800 cap without a patience stop, AC2"
                       if learner in M.EARLY_STOP_LEARNERS else "own best at 800", ext_ids or "none"))
        cache.clear()
        write_trials_csv(ctx, board)
        return ctx.out


def collect(ctx: Ctx, board, learner: str, strict: bool = True):
    """(base records, extended records by base id, extension ids) of a learner; strict refuses gaps."""
    base = []
    for t in trial_list(board, learner):
        rec = _read_done(ctx, board, t)
        if rec is None:
            if strict:
                _refuse("learner %s: trial %s is not finished" % (learner, t["trial_id"]), fix="tune --resume")
            continue
        base.append(rec)
    ext_ids = _extension_ids(learner, base) if base else []
    ext = {}
    for t in trial_list(board, learner):
        if t["trial_id"] in ext_ids:
            rec = _read_done(ctx, board, dict(t, extended=True))
            if rec is None:
                if strict:
                    _refuse("learner %s: extension of %s is not finished" % (learner, t["trial_id"]),
                            fix="tune --resume")
                continue
            ext[t["trial_id"]] = rec
    return base, ext, ext_ids


def _extension_ids(learner: str, base_recs: Sequence[Mapping[str, Any]]) -> List[str]:
    """Y2 on the base grid of one boosting learner (ridge and RF never extend); AC2 for the early-stopped learners:
    each base trial's own early-stopping record says whether it ran to the 800 cap (models.ran_to_cap); a trial
    record without one refuses."""
    if learner not in M.STAGED_LEARNERS:
        return []
    rows = [r for rec in base_recs for r in trial_rows(rec)]
    cap = None
    if learner in M.EARLY_STOP_LEARNERS:
        cap = {}
        for rec in base_recs:
            if not rec.get("early_stopping"):
                _refuse("trial %s of %s has no early-stopping record (the AC2 extension rule needs it)"
                        % (rec.get("trial_id"), learner))
            cap[rec["trial_id"]] = bool(M.ran_to_cap(rec["early_stopping"]))
    return trials_to_extend(rows, pick_learner(rows), ran_to_cap=cap)


def learner_pick(learner: str, base, ext) -> Dict[str, Any]:
    """The learner's pick over its base trials, an extended trial replacing its base trial."""
    rows = []
    for r in base:
        rows.extend(trial_rows(ext.get(r["trial_id"], r)))
    pick = pick_learner(rows)
    rec = next(r for r in base if r["trial_id"] == pick["trial_id"])
    pick["extended"] = pick["trial_id"] in ext
    pick["link"] = rec["link"]
    pick["setting"] = rec["setting"]
    pick["checkpoint_label"] = ck_label(pick["checkpoint"])
    pick["mae"] = pick["inner_mae"]
    pick["flags"] = pick_flags(learner, pick)
    return pick


def write_trials_csv(ctx: Ctx, board):
    rows = []
    for learner in learner_ids(board):
        base, ext, _ = collect(ctx, board, learner, strict=False)
        for r in base + [ext[k] for k in sorted(ext)]:
            for lab in r["checkpoints"]:
                m = r["metrics"][lab]
                rows.append({"learner": learner, "trial_id": r["trial_id"], "extended": r["extended"],
                             "link": r["link"] or "", "setting": dumps_canonical(r["setting"]),
                             "checkpoint": lab, "n_inner": r["n_inner"], "mae": m["mae"],
                             "corr2": m["corr2"], "calibration_ratio": m["calibration_ratio"],
                             "predict_zero_mae": m["predict_zero_mae"]})
    frame = pd.DataFrame(rows)
    ctx.replace_bytes(ctx.out / TRIALS_CSV, frame.to_csv(index=False,
                                                         lineterminator="\n").encode("utf-8"))


# ===================================================================================================
# lock
def _inner_comparator(ctx: Ctx, run: Run, learner: str, link: Optional[str], keys: pd.DataFrame,
                      y: np.ndarray) -> Tuple[str, np.ndarray]:
    """The N2 comparator on the inner rows: the run's saved column, key-joined by (unit, time)."""
    col = run.comparator_inner(learner, link)
    t = pq.read_table(run.folder / "inner_preds.parquet", columns=["unit", "time", "y", col]).to_pandas()
    j = _join(keys[["unit", "time"]], t, ["unit", "time"], "inner_preds.parquet")
    ys = j["y"].to_numpy(np.float64)
    if ys.tobytes() != np.asarray(y, dtype=np.float64).tobytes():
        _refuse("the export's inner labels differ from inner_preds.parquet (parity P4)")
    return col, j[col].to_numpy(np.float64)


def _join(left_keys: pd.DataFrame, right: pd.DataFrame, on: List[str], what: str) -> pd.DataFrame:
    """Left keys joined one to one, in the left order; refuses a missing or duplicated key."""
    if right.duplicated(subset=on).any():
        _refuse("%s names a key %s twice" % (what, on))
    lk = left_keys[on].copy()
    for k in on:
        if k == "unit" or k == "group":
            lk[k] = lk[k].astype(str)
    r = right.copy()
    for k in on:
        if k == "unit" or k == "group":
            r[k] = r[k].astype(str)
    j = lk.merge(r, on=on, how="left", indicator=True, validate="one_to_one")
    miss = int((j["_merge"] != "both").sum())
    if miss:
        _refuse("%d rows have no match in %s on %s" % (miss, what, on))
    return j.drop(columns="_merge")


def picks_sha(ctx: Ctx) -> str:
    return sha256_file(ctx.out / PICKS_FILE)


def verify_lock(out: Path) -> Dict[str, Any]:
    """The lock is valid: picks.json.lock.json exists and its sha matches picks.json; every test-label record of
    the board names THIS picks sha; and the run's ledger shows no test label opened under other picks
    (leak-fairness review 2)."""
    out = Path(out)
    lp, pp = out / PICKS_LOCK, out / PICKS_FILE
    if not lp.is_file() or not pp.is_file():
        _refuse("the picks are not locked (%s missing)" % (lp if not lp.is_file() else pp), fix="run lock")
    lk = read_json(lp)
    sha = sha256_file(pp)
    if lk.get("sha256") != sha:
        _refuse("picks.json changed after the lock (sha %s vs locked %s)" % (sha, lk.get("sha256")))
    for rp in sorted(out.glob("test_labels_opened_rivals_lead_*.json")):
        rec = read_json(rp)
        named = [rec.get("picks_sha256")] + [h.get("picks_sha256") for h in rec.get("history") or []]
        other = sorted(set(str(x) for x in named if x != sha))
        if other:
            _refuse("%s shows test labels opened under picks %s, not the locked picks %s; picks are never "
                    "re-locked after a test label was opened" % (rp.name, [o[:16] for o in other], sha[:16]))
    doc = read_json(pp)
    picks = doc.get("picks")
    if isinstance(picks, dict) and doc.get("run_fingerprint"):
        mine = picks_content_sha(picks)
        for r in ledger_openings(out, doc["run_fingerprint"]):
            if r.get("picks_content_sha256") != mine:
                _refuse("the run ledger %s shows test labels opened at %s under other picks (content %s, "
                        "board %s); these picks (content %s) are refused"
                        % (ledger_path(out, doc["run_fingerprint"]), r.get("utc"),
                           str(r.get("picks_content_sha256"))[:16], r.get("board"), mine[:16]))
    return doc


def lock(out: Any, config: Any = None) -> Path:
    """Lock the picks (rule 17): picks.json then its hashed lock. No test file is opened."""
    with _Command("lock", out, config) as ctx:
        board, run = load_board(ctx)
        traces = test_side_files(ctx.out)
        if traces:
            _refuse("this board already holds test-side files (%s); picks are never locked after a test row was "
                    "touched" % [str(p) for p in traces[:3]])
        if (ctx.out / PICKS_LOCK).is_file():
            _refuse("the picks are already locked; picks are written once")
        if (ctx.out / PICKS_FILE).is_file():
            # killed between picks.json and its lock: nothing was read in between, so redo (robustness 10)
            ctx.log("lock", message="picks.json without its lock (a killed lock): moved aside, locking again")
            ctx.move_aside(ctx.out / PICKS_FILE)
        ex = export_lead(board, run, 0)
        write_trials_csv(ctx, board)
        legal = tuple(board["run"]["legal"])
        picks = {}
        for learner in learner_ids(board):
            base, ext, ext_ids = collect(ctx, board, learner, strict=True)
            pick = learner_pick(learner, base, ext)
            rec = ext.get(pick["trial_id"]) or next(r for r in base if r["trial_id"] == pick["trial_id"])
            d = _trial_dir(ctx, {"trial_id": pick["trial_id"], "learner": learner, "extended": pick["extended"]})
            ip = pq.read_table(d / "inner_preds.parquet").to_pandas()
            pred = ip["pred__" + pick["checkpoint_label"]].to_numpy(np.float64)
            _, inner_keys, inner_y = score_set_keys(ex, "inner")
            if not (ip["unit"].astype(str).to_numpy() == inner_keys["unit"].astype(str).to_numpy()).all():
                _refuse("trial %s inner rows are not the export's inner rows" % pick["trial_id"])
            comp_name, comp = _inner_comparator(ctx, run, learner, pick["link"], inner_keys, inner_y)
            m = ctx.eng.metrics
            rival_mae = m.mae(inner_y, pred)
            if rival_mae != rec["ck_mae"][pick["checkpoint_label"]]:
                _refuse("trial %s: the saved inner MAE does not reproduce" % pick["trial_id"])
            comp_mae = m.mae(inner_y, comp)
            eligible = bool(ctx.eng.decide.n2_eligible(rival_mae, comp_mae))
            # whose numbers these are (AA3 review item 3; AC1): every learner's final fit uses its tuning options
            # (lgbm / lgbm_tweedie: the same 255 bins; the final fit only drops the early stopping at the picked
            # round), so the tuning model at the pick is the reported model's lead-0 guard model
            numbers_from = "the tuning model, which is the reported model's lead-0 guard model"
            picks[learner] = {"trial_id": pick["trial_id"], "extended": pick["extended"],
                              "link": pick["link"], "setting": pick["setting"],
                              "checkpoint": pick["checkpoint_label"], "inner_mae": rival_mae,
                              "inner_mae_and_n2_are_of": numbers_from,
                              "flags": pick["flags"], "extension_trials": ext_ids,
                              "n2_lead_0": {"comparator": comp_name, "comparator_mae": comp_mae,
                                            "rival_mae": rival_mae, "eligible": eligible}}
            ctx.log("pick", learner, pick["trial_id"],
                    message="link %s at %s, inner MAE %r (%s); N2 vs %s %r: %s; flags: %s; extended trials: %d"
                    % (pick["link"] or "own log link", pick["checkpoint_label"], rival_mae,
                       "tuning model = the lead-0 guard model", comp_name, comp_mae,
                       "eligible" if eligible else "NOT eligible", ", ".join(pick["flags"]) or "none",
                       len(ext_ids)))
        doc = {"format": PICKS_FORMAT, "run_fingerprint": run.fingerprint, "picks": picks,
               "trials_csv_sha256": sha256_file(ctx.out / TRIALS_CSV),
               "board_json_sha256": sha256_file(ctx.out / BOARD_FILE),
               "export_content_sha256": {"0": board["export"]["lead_0"]["content_sha256"]},
               "harness_code_sha256": board["harness_code_sha256"]}
        content = picks_content_sha(picks)
        for r in ledger_openings(ctx.out, run.fingerprint):
            if r.get("picks_content_sha256") != content:
                _refuse("the run ledger shows test labels opened at %s under other picks (content %s, board %s); "
                        "these picks (content %s) are NOT locked: re-tuning after a test label never changes a pick"
                        % (r.get("utc"), str(r.get("picks_content_sha256"))[:16], r.get("board"), content[:16]),
                        fix="OWNER ITEM: nothing is locked; report this")
        ctx.write_once_json(ctx.out / PICKS_FILE, doc)
        lk = {"file": PICKS_FILE, "sha256": sha256_file(ctx.out / PICKS_FILE), "utc": utc_now(),
              "harness_code_sha256": board["harness_code_sha256"],
              "rule": "rule 17: every rival's inner pick is locked before any test file or test label "
                      "is read; a changed picks.json is refused by every later command"}
        ctx.write_once_json(ctx.out / PICKS_LOCK, lk)
        ledger_append(ctx, run.fingerprint, {"event": "locked", "picks_sha256": lk["sha256"],
                                             "picks_content_sha256": content})
        ctx.log("locked", message="picks.json sha %s (picks content %s)" % (lk["sha256"], content[:16]))
        return ctx.out


def score_set_keys(ex: ExportLead, set_name: str):
    """Keys and labels of a train-side set without its features."""
    flag, _ = SETS[set_name]
    keys, ys = [], []
    for g in ex.groups:
        t = ex.read_table(TRAIN_DIR, g, list(KEYS) + [flag, "y"])
        m = t[flag].to_numpy(bool)
        if m.any():
            ex._check_rows(set_name, t.loc[m, list(KEYS)], "train/%s" % g)
            keys.append(t.loc[m, list(KEYS)])
            ys.append(t.loc[m, "y"].to_numpy(np.float64))
    if not keys:
        _refuse("export %s holds no %s row" % (ex.dir, set_name))
    return None, pd.concat(keys, ignore_index=True), np.concatenate(ys)


# ===================================================================================================
# probe
def probe(out: Any, lead: int = 0, config: Any = None) -> Dict[str, Any]:
    """20-round LightGBM and 10-tree RF at the real tune shape: time and peak RAM; no inner score."""
    with _Command("probe", out, config) as ctx:
        board, run = load_board(ctx)
        if lead != 0:
            _refuse("probe runs at lead 0 (the tuning shape)")
        ex = export_lead(board, run, 0)
        fit = materialize(ctx, ex, "tune")
        link = board["run"]["links"][0]
        rec: Dict[str, Any] = {"rows": int(fit.X.shape[0]), "columns": len(fit.columns) + 1}
        for learner, cks in (("lgbm", (PROBE_ROUNDS,)), ("rf", None)):
            st = M.grid(learner)[-1]
            ctx.peak_rss = 0
            t0 = time.time()
            params = dict(st, link=link, c=board["run"]["c"].get("0"), ub=board["run"]["ub"])
            if learner == "rf":
                rec["rf_info"] = _clean_info(M.rf_probe(fit, params, PROBE_TREES))
            else:
                M.fit_predict(learner, params, fit, [], cks, cache={}, max_bin=M.LGBM_MAX_BIN)   # the tuning shape
            rec[learner] = {"setting": st, "seconds": time.time() - t0, "peak_rss_bytes": ctx.rss()}
            ctx.log("probe", learner, seconds=time.time() - t0,
                    message="peak %.2f GiB" % (ctx.peak_rss / M.GIB))
        ctx.replace_json(ctx.out / PROBE_FILE, rec)
        return rec


# ===================================================================================================
# refit
def _lead_dir(ctx: Ctx, lead: int) -> Path:
    return ctx.out / ("lead_%d" % lead)


def _pick_trial(learner: str, pick: Mapping[str, Any]) -> Dict[str, Any]:
    return {"learner": learner, "link": pick["link"], "setting": dict(pick["setting"]),
            "trial_id": pick["trial_id"]}


def _pinned(learner: str, pick: Mapping[str, Any]) -> Any:
    return float(pick["checkpoint"]) if learner == "ridge" else int(pick["checkpoint"])


def saved_test_keys(run: Run, lead: int) -> Tuple[str, pd.DataFrame]:
    """The lead's saved test rows in the saved order: keys and the run's decline target column only
    (prediction columns, never y)."""
    col = run.decline_target_at(lead)
    cols = ["unit", "group", "time", "issue", "lead", col]
    t = read_columns(run.test_preds_path(lead), cols)
    v = t[col].to_numpy(np.float64)
    if not np.isfinite(v).all():
        _refuse("the decline target %s is missing on %d saved test rows" % (col, int((~np.isfinite(v)).sum())))
    if t.duplicated(subset=["unit", "time", "lead"]).any():
        _refuse("the saved test rows name a (unit, time, lead) twice")
    return col, t


def to_saved_order(saved: pd.DataFrame, keys: pd.DataFrame, what: str) -> np.ndarray:
    """Positions into the export's test rows that put them in the saved order; refuses a missing or
    extra key (F65: every rival column is scored on exactly the saved rows)."""
    on = ["unit", "time", "lead"]
    k = keys[on].reset_index(drop=True).copy()
    k["_pos"] = np.arange(len(k))
    j = _join(saved[on], k, on, what)
    if len(k) != len(saved):
        _refuse("%s: %d export test rows for %d saved test rows" % (what, len(k), len(saved)))
    return j["_pos"].to_numpy(np.int64)


def apply_guard(guard_pred: np.ndarray, comparator: np.ndarray, y: np.ndarray, raw: np.ndarray,
                fallback: np.ndarray, eng: Optional[Engine] = None) -> Tuple[np.ndarray, bool]:
    """Our N2 safety net applied to a rival (spec 3.7): passed iff MAE(rival) < MAE(comparator)
    strictly on the guard rows (layer.decide.n2_eligible); guarded = raw if passed, else fallback."""
    if eng is not None:
        mae, n2 = eng.metrics.mae, eng.decide.n2_eligible
    else:
        from treeroute.report.metrics import mae
        from treeroute.layer.decide import n2_eligible as n2
    passed = bool(n2(mae(y, guard_pred), mae(y, comparator)))
    raw, fallback = np.asarray(raw, dtype=np.float64), np.asarray(fallback, dtype=np.float64)
    if raw.shape != fallback.shape:
        _refuse("the raw and fallback test columns differ in length (%s vs %s)" % (raw.shape, fallback.shape))
    return (raw if passed else fallback), passed


def refit(out: Any, lead: int, resume: bool = False, config: Any = None) -> Path:
    """Guard (N2), refit at the pick, predict the test rows raw and guarded (spec 3.7)."""
    with _Command("refit", out, config) as ctx:
        board, run = load_board(ctx)
        picks_doc = verify_lock(ctx.out)
        lead = int(lead)
        if lead not in run.leads:
            _refuse("lead %d is not a lead of the run (%s)" % (lead, run.leads))
        ex = export_lead(board, run, lead)
        ldir = ctx.mkdir(_lead_dir(ctx, lead))
        exp_rec = {"lead": lead, "export_dir": str(ex.dir), "export_content_sha256": ex.content_sha,
                   "export_files_sha256": ex.files_sha(), "picks_sha256": picks_sha(ctx)}
        ep = ldir / "export.json"
        if ep.is_file():
            old = read_json(ep)
            if old != _clean(exp_rec):
                _refuse("lead %d was refit from another export or picks (%s)" % (lead, ep),
                        fix="move %s aside to start the lead again" % ldir)
        else:
            ctx.write_once_json(ep, exp_rec)
        keep_export_files(ctx, ex)
        legal = tuple(board["run"]["legal"])
        cache: Dict[Any, Any] = {}
        sets: Dict[str, Any] = {}

        def fitset(name):
            if name not in sets:
                sets[name] = materialize(ctx, ex, name)
            return sets[name]

        def scoreset(name):
            key = "score:" + name
            if key not in sets:
                sets[key] = score_set(ex, name)
            return sets[key]

        for learner in learner_ids(board):
            pick = picks_doc["picks"][learner]
            trial = _pick_trial(learner, pick)
            pinned = _pinned(learner, pick)
            done_p = ldir / ("done_%s.json" % learner)
            h = sha256_bytes(dumps_canonical({"lead": lead, "pick": pick, "export": ex.content_sha,
                                              "harness": board["harness_code_sha256"],
                                              "rf": board["rf"]["method"],
                                              "final_fit": M.final_fit_options(learner)}).encode("ascii"))
            if done_p.is_file():
                rec = read_json(done_p)
                if rec.get("hash") == h and resume:
                    ctx.log("refit", learner, message="skipped (finished, same hash)")
                    continue
                if rec.get("hash") == h and not resume:
                    _refuse("lead %d %s is already refit" % (lead, learner), fix="pass --resume")
                ctx.move_aside(done_p)
            for name in ("preds_%s.parquet", "guard_%s.parquet", "model_%s.txt", "model_%s.json",
                         "model_%s.pkl"):
                ctx.move_aside(ldir / (name % learner))
            t0 = time.time()
            params = trial_params(board, trial, lead)
            # the final-fit options (AC1: LightGBM's default 255 bins, the same as its tuning, at the picked round
            # count with no early stopping); {} for the other learners
            fin = {"max_bin": M.LGBM_MAX_BIN} if learner in M.EARLY_STOP_LEARNERS else {}
            # 1. guard (N2 applied to the rival)
            g_store = None
            if lead == 0:
                # every learner (AC1 for lgbm / lgbm_tweedie): the tuning trial at the pick IS the final model fitted
                # on the tune rows, so its saved inner predictions are the lead-0 guard (no second fit)
                guard_source = "the tuning trial's inner predictions at the pick"
                d = _trial_dir(ctx, {"trial_id": pick["trial_id"], "learner": learner,
                                     "extended": pick["extended"]})
                if fin:
                    tbin = (read_json(d / "trial.json").get("fit_info") or {}).get("max_bin")
                    if tbin != fin["max_bin"]:
                        _refuse("lead 0 %s: the tuning trial %s was binned with %r bins, not the final fit's %r; its "
                                "predictions are not the final model's" % (learner, pick["trial_id"], tbin,
                                                                          fin["max_bin"]))
                ip = pq.read_table(d / "inner_preds.parquet").to_pandas()
                _, gkeys, gy = score_set_keys(ex, "inner")
                g_pre = ip["pre__" + pick["checkpoint"]].to_numpy(np.float64)
                g_pred = ip["pred__" + pick["checkpoint"]].to_numpy(np.float64)
                comp_name, comp = _inner_comparator(ctx, run, learner, pick["link"], gkeys, gy)
            else:
                guard_source = "a fit on the guard-fit rows%s, scored on the guard rows" % (
                    (" with the final-fit options %s" % fin) if fin else "")
                gfit = fitset("guardfit")
                gsc, gkeys, gy = scoreset("guard")
                ram_check(learner, int(gfit.X.shape[0]), len(gfit.columns) + 1, int(gsc.X.shape[0]))
                g_store = rf_checkpoint(ctx, learner, "guardfit", h)
                gres = M.fit_predict(learner, params, gfit, [gsc], (pinned,), cache=cache, rf_store=g_store,
                                     rf_key=g_store.key if g_store else "", **fin)
                g_pre = np.asarray(gres["guard"][pinned]["pre"], dtype=np.float64)
                del gres                           # the guard-fit model is not kept in RAM (robustness 5)
                gc.collect()
                g_pred = clip(ctx.eng, g_pre, legal)
                comp_name, comp = _guard_comparator(ctx, run, lead, learner, pick["link"], gsc, gkeys, gy, params)
            m = ctx.eng.metrics
            g_mae, c_mae = m.mae(gy, g_pred), m.mae(gy, comp)
            gframe = gkeys.reset_index(drop=True).copy()
            gframe["y"] = gy
            gframe["pre__rival_" + learner] = g_pre
            gframe["arm__rival_" + learner] = g_pred
            gframe["comparator"] = comp
            gframe["guard_passed"] = bool(ctx.eng.decide.n2_eligible(g_mae, c_mae))
            ctx.write_parquet(ldir / ("guard_%s.parquet" % learner), gframe)
            ctx.log("guard", learner, seconds=time.time() - t0,
                    message="rival %r vs %s %r: %s" % (g_mae, comp_name, c_mae,
                                                       "PASSED" if g_mae < c_mae else "failed"))
            # 2. refit at the fit cut, pinned rounds / alpha
            t1 = time.time()
            rfit = fitset("refit")
            # 3. the test rows: first read of any test file (after the lock); the RAM check counts them (Z2 check 3)
            tsc, tkeys, _ = scoreset("test")
            ram_check(learner, int(rfit.X.shape[0]), len(rfit.columns) + 1, int(tsc.X.shape[0]))
            if "saved" not in sets:
                sets["saved"] = saved_test_keys(run, lead)
                sets["saved_pos"] = to_saved_order(sets["saved"][1], tkeys, "the saved test rows")
            fb_name, saved = sets["saved"]
            pos = sets["saved_pos"]
            r_store = rf_checkpoint(ctx, learner, "refit", h)
            res = M.fit_predict(learner, params, rfit, [tsc], (pinned,), cache=cache, rf_store=r_store,
                                rf_key=r_store.key if r_store else "", **fin)
            t_pre = np.asarray(res["test"][pinned]["pre"], dtype=np.float64)[pos]
            t_raw = clip(ctx.eng, t_pre, legal)
            fb = saved[fb_name].to_numpy(np.float64)
            guarded, passed = apply_guard(g_pred, comp, gy, t_raw, fb, ctx.eng)
            pframe = saved[["unit", "group", "time", "issue", "lead"]].reset_index(drop=True).copy()
            pframe["pre__rival_" + learner] = t_pre
            pframe["arm__rival_%s_raw" % learner] = t_raw
            pframe["arm__rival_" + learner] = guarded
            pframe["guard_passed"] = passed
            ctx.write_parquet(ldir / ("preds_%s.parquet" % learner), pframe)
            model_file = _save_model(ctx, ldir, learner, getattr(res, "model", None))
            fit_info = _clean_info(getattr(res, "info", {}))
            del res                                # the refit model is not kept into the next learner
            gc.collect()
            done = {"hash": h, "lead": lead, "learner": learner, "pick": pick, "pinned": ck_label(pinned),
                    "guard": {"rows": int(gy.size), "rival_mae": g_mae, "comparator": comp_name,
                              "comparator_mae": c_mae, "passed": passed, "source": guard_source},
                    "final_fit": M.final_fit_options(learner),
                    "fallback": fb_name, "test_rows": int(len(tkeys)),
                    "fit_info": fit_info, "model_file": model_file, "comparator_source": comp_name,
                    "preds_sha256": sha256_file(ldir / ("preds_%s.parquet" % learner)),
                    "seconds": time.time() - t0, "utc": utc_now()}
            ctx.write_once_json(done_p, done)
            for st_ in (r_store, g_store):
                if st_ is not None:
                    st_.finish()
            ctx.log("refit", learner, seconds=time.time() - t1,
                    message="test rows %d; guard %s; guarded = %s"
                    % (len(tkeys), "passed" if passed else "failed", "raw" if passed else fb_name))
        cache.clear()
        return ctx.out


def _guard_comparator(ctx: Ctx, run: Run, lead: int, learner: str, link: Optional[str],
                      gsc: M.ScoreData, gkeys: pd.DataFrame, gy: np.ndarray, params) -> Tuple[str, np.ndarray]:
    """Lead >= 1: V1 runs the saved guard_preds donor median; otherwise the run's own saved
    arm__<own link>_trees_off_unweighted on the guard rows, key-joined (y checked byte for byte), as the lead-0
    comparator reads inner_preds (parity review 5). Only when the run saved no such column: rebuilt as
    clip(link_inverse(guard-cut normal)) of the rival's own link (Tweedie: identity, R-TW); the name says which."""
    legal = run.legal
    gp = run.guard_preds_path(lead)
    names = pq.read_schema(gp).names if gp.is_file() else []
    if run.v1:
        col = run.decline_target
    else:
        own = "identity" if learner == "lgbm_tweedie" else link
        col = "arm__" + own + TREES_OFF_SUFFIX
    if col in names:
        t = pq.read_table(gp, columns=["unit", "time", "issue", "y", col]).to_pandas()
        j = _join(gkeys[["unit", "time", "issue"]], t, ["unit", "time", "issue"], "guard_preds.parquet")
        if j["y"].to_numpy(np.float64).tobytes() != np.asarray(gy, np.float64).tobytes():
            _refuse("the export's guard labels differ from guard_preds.parquet (parity P5)")
        return col + " (saved guard_preds)", j[col].to_numpy(np.float64)
    if run.v1:
        _refuse("lead %d guard_preds.parquet has no %s" % (lead, col))
    z = gsc.normal[own]
    pre = M.link_inverse(z, own, params.get("c"), params.get("ub"))
    return own + TREES_OFF_SUFFIX + " (rebuilt from the guard-cut normal: the run saved no %s)" % col, \
        clip(ctx.eng, pre, legal)


def _save_model(ctx: Ctx, ldir: Path, learner: str, model: Any) -> Optional[str]:
    """GBM and ridge models are saved; RF models are not (plan 5c), their predictions are."""
    if learner in ("lgbm", "lgbm_tweedie"):
        if model is None:
            return None
        p = ldir / ("model_%s.txt" % learner)
        ctx.replace_bytes(p, model.model_to_string().encode("utf-8"))
        return p.name
    if learner == "ridge":
        p = ldir / ("model_%s.json" % learner)
        ctx.replace_json(p, model)
        return p.name
    if learner == "hgb_l1":
        import pickle
        p = ldir / ("model_%s.pkl" % learner)
        ctx.replace_bytes(p, pickle.dumps(model, protocol=4))
        return p.name
    return None


# ===================================================================================================
# score (the only reader of test labels)
def open_test_labels_rivals(out: Any, lead: int, run: Optional[Run] = None, ctx: Optional[Ctx] = None,
                            learners: Optional[Sequence[str]] = None, config: Any = None) -> pd.DataFrame:
    """The ONE reader of test y. Refuses unless the picks lock is valid and every learner's
    preds_<learner>.parquet of the lead exists; then reads the lead's saved test rows WITH y and
    writes test_labels_opened_rivals_lead_<L>.json."""
    out = Path(out)
    picks_doc = verify_lock(out)
    board = read_json(out / BOARD_FILE)
    if ctx is None:
        cfg = load_config(config)
        ctx = Ctx(cfg, Engine(cfg), out, "open_test_labels")
    if run is None:
        run = Run(board["run"]["folder"])
    learners = list(learners) if learners is not None else learner_ids(board)
    ldir = out / ("lead_%d" % int(lead))
    missing = [L for L in learners if not (ldir / ("preds_%s.parquet" % L)).is_file()
               or not (ldir / ("done_%s.json" % L)).is_file()]
    if missing:
        _refuse("lead %d: no finished predictions for %s" % (lead, missing), fix="refit --lead %d" % lead)
    if set(learners) != set(picks_doc["picks"]):
        _refuse("the learners %s differ from the locked picks %s" % (learners, sorted(picks_doc["picks"])))
    path = run.test_preds_path(int(lead))
    psha = sha256_file(out / PICKS_FILE)
    content = picks_content_sha(picks_doc["picks"])
    ledger_append(ctx, board["run"]["fingerprint"], {"event": "test_labels_opened", "lead": int(lead),
                                                     "picks_sha256": psha, "picks_content_sha256": content})
    frame = pq.read_table(path).to_pandas()
    rec = {"utc": utc_now(), "picks_sha256": psha, "picks_content_sha256": content, "rows": int(len(frame)),
           "file": str(path), "lead": int(lead), "test_preds_sha256": sha256_file(path)}
    rp = out / (TEST_LABELS_OPENED % int(lead))
    history = read_json(rp).get("history", []) if rp.is_file() else []
    doc = dict(rec, history=history + [rec])          # the latest opening on top, every opening listed
    ctx.replace_json(rp, doc)
    return frame


def _frame_for_scoring(ctx: Ctx, board, run: Run, lead: int, saved: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    keep = [c for c in ("unit", "group", "time", "year", "lead", "issue", "y", "normal", "legal_min",
                        "legal_max") if c in saved.columns]
    frame = saved[keep].copy()
    for c in saved.columns:
        if c.startswith("base__"):
            frame[c] = saved[c]
    headline, raw = run.ours(lead)
    for name, col in (("ours", headline), ("ours_raw", raw)):
        if col not in saved.columns:
            _refuse("lead %d: our column %s is not in the saved test rows" % (lead, col))
        frame["arm__" + name] = saved[col].to_numpy(np.float64)
        pre = "pre__" + col[len("arm__"):] if col.startswith("arm__") else None
        if pre and pre in saved.columns:
            frame["pre__" + name] = saved[pre].to_numpy(np.float64)
    ldir = _lead_dir(ctx, lead)
    learners = learner_ids(board)
    for L in learners:
        p = pq.read_table(ldir / ("preds_%s.parquet" % L)).to_pandas()
        if len(p) != len(saved):
            _refuse("lead %d %s: %d rival rows for %d saved rows" % (lead, L, len(p), len(saved)))
        j = _join(saved[["unit", "time", "lead"]], p, ["unit", "time", "lead"], "preds_%s.parquet" % L)
        frame["arm__rival_" + L] = j["arm__rival_" + L].to_numpy(np.float64)
        frame["arm__rival_%s_raw" % L] = j["arm__rival_%s_raw" % L].to_numpy(np.float64)
        frame["pre__rival_%s_raw" % L] = j["pre__rival_" + L].to_numpy(np.float64)
    return frame, learners


def _strata_tables(ctx: Ctx, board, run: Run, units: pd.DataFrame, frame: pd.DataFrame, tol, floor, kind):
    """Per-stratum tables with the run's own edges (per_stratum.csv) and the export's unit values."""
    out = {}
    strata = run.verdict.get("strata") or {}
    if not strata:
        return out
    units = units.copy()
    units["unit"] = units["unit"].astype(str)
    ps_path = run.folder / "per_stratum.csv"
    ps = pd.read_csv(ps_path) if ps_path.is_file() else None
    for name, info in sorted(strata.items()):
        if name not in units.columns:
            _refuse("units.parquet lacks the report stratum column %s" % name)
        vals = frame[["unit"]].astype(str).merge(units[["unit", name]], on="unit", how="left")[name]
        if vals.isna().any():
            _refuse("stratum %s has no value for %d test rows" % (name, int(vals.isna().sum())))
        edges = info.get("edges") if isinstance(info, dict) else None
        if edges is not None:
            if ps is not None and "edge_q25" in ps.columns:
                sub = ps[ps["stratum_column"] == name]
                pe = [float(sub["edge_q25"].iloc[0]), float(sub["edge_q50"].iloc[0]), float(sub["edge_q75"].iloc[0])]
                if pe != [float(e) for e in edges]:
                    _refuse("stratum %s edges differ: per_stratum.csv %s vs verdict %s" % (name, pe, edges))
            bins = ctx.eng.metrics.stratum_bins(vals.to_numpy(np.float64), tuple(edges))
            f = frame.assign(stratum=bins.astype(np.float64))
        else:
            f = frame.assign(stratum=vals.astype(str).to_numpy())
        t = ctx.eng.metrics.score_table(f, ("stratum",), tol, floor, kind)
        t.insert(0, "stratum_column", name)
        out["stratum_" + name] = t
    return out


def check_ours_against_run(run: Run, lead: int, group_table: pd.DataFrame, pooled_table: pd.DataFrame
                           ) -> Dict[str, Any]:
    """Tie the board's "ours" to the run's own record (parity review 6). Lead 0: the pooled MAE of our headline
    column equals the run's score_pooled.csv, and its per-group MAE equals score_by_group.csv (fail loud). A
    lead >= 1: the run keeps no score file for the lead, so this is recorded as not checkable (our lead columns
    are read straight from the lead's saved test_preds)."""
    headline, _ = run.ours(lead)
    if lead != 0:
        return {"lead": lead, "result": "not checkable: the run keeps no score file at lead %d; our columns are "
                                        "the saved %s columns" % (lead, run.test_preds_path(lead).name)}
    out: Dict[str, Any] = {"lead": 0, "column": headline}
    sp, sg = run.folder / "score_pooled.csv", run.folder / "score_by_group.csv"
    if not sp.is_file() or not sg.is_file():
        out["result"] = "not checkable: the run has no score_pooled.csv / score_by_group.csv"
        return out
    rp = pd.read_csv(sp)
    rp = rp[(rp["column"] == headline) & (rp["line"] == "pooled") & (rp["rows_basis"] == "all")]
    if len(rp) != 1:
        _refuse("score_pooled.csv has %d pooled lines for our headline column %s" % (len(rp), headline))
    ours = _pooled(pooled_table, "arm__ours")["mae"]
    theirs = float(rp["mae"].iloc[0])
    if not np.isclose(ours, theirs, rtol=1e-12, atol=0.0):
        _refuse("our headline pooled MAE %r differs from the run's score_pooled.csv %r (%s)" % (ours, theirs, headline))
    rg = pd.read_csv(sg)
    rg = rg[(rg["column"] == headline) & (rg["line"] == "key") & (rg["rows_basis"] == "all")]
    mine = group_table[(group_table["column"] == "arm__ours") & (group_table["line"] == "key")
                       & (group_table["rows_basis"] == "all")]
    a = dict(zip(rg["group"].astype(str), rg["mae"].astype(float)))
    b = dict(zip(mine["group"].astype(str), mine["mae"].astype(float)))
    if set(a) != set(b) or any(not np.isclose(a[g], b[g], rtol=1e-12, atol=0.0) for g in a):
        bad = sorted(g for g in set(a) | set(b) if g not in a or g not in b or not np.isclose(a[g], b[g], rtol=1e-12))
        _refuse("our per-group MAE differs from the run's score_by_group.csv in %d group(s) (first %s)"
                % (len(bad), bad[:3]))
    out.update(pooled_mae=ours, run_pooled_mae=theirs, groups=len(a),
               result="pass (pooled and %d groups equal the run's own scores)" % len(a))
    return out


def score(out: Any, lead: int, config: Any = None) -> Path:
    """Score every rival on the lead's saved test rows with the engine's own functions (spec 3.8)."""
    with _Command("score", out, config) as ctx:
        board, run = load_board(ctx)
        lead = int(lead)
        units = kept_units(ctx.out, lead)            # the export itself is no longer needed (robustness 6)
        saved = open_test_labels_rivals(ctx.out, lead, run=run, ctx=ctx)
        frame, learners = _frame_for_scoring(ctx, board, run, lead, saved)
        m = ctx.eng.metrics
        tol, floor, kind = run.tol, run.floor, run.kind
        tables = {"group": m.score_table(frame, ("group",), tol, floor, kind),
                  "year": m.score_table(frame, ("year",), tol, floor, kind),
                  "pooled": m.score_table(frame, (), tol, floor, kind)}
        ours_check = check_ours_against_run(run, lead, tables["group"], tables["pooled"])
        ctx.log("ours", message="our columns vs the run's own scores: %s" % ours_check["result"])
        tables.update(_strata_tables(ctx, board, run, units, frame, tol, floor, kind))
        if "seen_during_design" in units.columns and units["seen_during_design"].astype(bool).any():
            seen = set(units.loc[units["seen_during_design"].astype(bool), "unit"].astype(str))
            f2 = frame[~frame["unit"].astype(str).isin(seen)].reset_index(drop=True)
            if len(f2):
                tables["group_unseen"] = m.score_table(f2, ("group",), tol, floor, kind)
                tables["pooled_unseen"] = m.score_table(f2, (), tol, floor, kind)
            else:   # every scored unit was seen during design (e.g. a split whose seen list holds every group):
                    # no unseen rows, so no unseen table (the engine refuses an empty table, R34). Fix logged in
                    # the Part after 598; it changes no pick and no score.
                ctx.log("unseen", message="every scored unit was seen during design: no unseen tables written")
        sdir = ctx.mkdir(ctx.out / SCORES_DIR)
        for name, t in tables.items():
            ctx.replace_bytes(sdir / ("lead_%d_%s.csv" % (lead, name)),
                              t.to_csv(index=False, lineterminator="\n").encode("utf-8"))
        rows = []
        gt, pt = tables["group"], tables["pooled"]
        for L in learners:
            for kind_name, rcol, ocol in (("guarded_vs_headline", "arm__rival_" + L, "arm__ours"),
                                          ("raw_vs_raw", "arm__rival_%s_raw" % L, "arm__ours_raw")):
                rmap = m.metric_by_key(gt, rcol, "mae", "group")
                omap = m.metric_by_key(gt, ocol, "mae", "group")
                groups, d = m._paired_contrast(rmap, omap, "%s %s" % (L, kind_name))
                tag, jk = m.contrast_tag(d, run.band)
                word = VERDICT_WORDS[tag.value]
                bj = None
                if run.block_of_group:
                    bj = m.blocked_jackknife(dict(zip(groups, d.tolist())), run.block_of_group)
                pr = _pooled(pt, rcol)
                po = _pooled(pt, ocol)
                timid = bool(pr["mae"] < po["mae"] and (
                    (math.isfinite(pr["calibration_ratio"]) and pr["calibration_ratio"] < 0.5)
                    or (math.isfinite(pr["corr2"]) and math.isfinite(po["corr2"]) and pr["corr2"] < 0.5 * po["corr2"])))
                rows.append({"lead": lead, "learner": L, "contrast": kind_name, "rival_column": rcol,
                             "ours_column": ocol, "ours_beats_rival": word, "tag": tag.value,
                             "decides": kind_name == "guarded_vs_headline", "band": run.band,
                             "d_mean": jk.mean, "d_se": jk.se, "d_low": jk.low, "d_high": jk.high,
                             "n_groups": jk.n_groups,
                             "blocked_mean": None if bj is None else bj.mean,
                             "blocked_se": None if bj is None else bj.se,
                             "rival_mae": pr["mae"], "ours_mae": po["mae"],
                             "rival_corr2": pr["corr2"], "ours_corr2": po["corr2"],
                             "rival_calibration_ratio": pr["calibration_ratio"],
                             "rival_hit": pr["hit"], "ours_hit": po["hit"],
                             "timid_win": timid,
                             "guard_passed": read_json(_lead_dir(ctx, lead) / ("done_%s.json" % L))["guard"]["passed"]})
        bl = pd.DataFrame(rows)
        ctx.replace_bytes(ctx.out / (BOARD_LEAD_CSV % lead),
                          bl.to_csv(index=False, lineterminator="\n").encode("utf-8"))
        ctx.replace_json(ctx.out / SCORES_DIR / ("lead_%d_ours_check.json" % lead), ours_check)
        for r in rows:
            if r["decides"]:
                ctx.log("verdict", r["learner"], message="ours vs rival (guarded): %s; d = %.6g [%.6g, %.6g]%s"
                        % (r["ours_beats_rival"], r["d_mean"], r["d_low"], r["d_high"],
                           "; TIMID rival win" if r["timid_win"] else ""))
        mdir = materialized_dir(ctx)
        copies = sorted(mdir.glob("lead_%d_*.f32" % lead)) if mdir.is_dir() else []
        for p in copies:
            ctx.log("may delete", message="lead %d is scored: the fit-set copy %s (%.2f GiB) is a rebuildable cache "
                    "(its sha256 is kept in %s); the owner may delete it and its .index.parquet"
                    % (lead, p, os.path.getsize(p) / M.GIB, p.with_suffix(".json").name))
        return ctx.out


def _pooled(table: pd.DataFrame, column: str) -> Dict[str, float]:
    sel = table[(table["line"] == "pooled") & (table["column"] == column) & (table["rows_basis"] == "all")]
    if len(sel) != 1:
        _refuse("the pooled table has %d lines for %s" % (len(sel), column))
    r = sel.iloc[0]
    return {k: float(r[k]) for k in ("mae", "corr2", "calibration_ratio", "hit")}


# ===================================================================================================
# board
def _accepted_line(bd: Mapping[str, Any]) -> str:
    """board.md's line on an owner-accepted engine difference of the run (from board.json, from the export)."""
    acc = (bd.get("engine") or {}).get("accepted_difference")
    if not acc:
        return "Engine: the export's identity checks I1-I9 all passed with no accepted difference."
    hops = ["%s->%s" % (str(h.get("from"))[:8], str(h.get("to"))[:8])
            for h in acc.get("I4_hops_accepted_on_the_chain") or []]
    keys = [str(c.get("key")) for c in acc.get("I5_config_keys_accepted") or []]
    return ("ACCEPTED ENGINE DIFFERENCE (owner ruling %s, %s): run id %s; engine hops without a parsable no-op proof "
            "%s; run-config keys %s; accepted on the condition that every parity check %s passed (it did, at "
            "every exported lead)." % (acc.get("ruling"), acc.get("ruling_source"), acc.get("run_id"), hops or "none",
                                      keys or "none", acc.get("requires_parity")))


def board(out: Any, config: Any = None) -> Path:
    """board.md from every board_lead_<L>.csv (plain table)."""
    with _Command("board", out, config) as ctx:
        bd, run = load_board(ctx)
        files = sorted(ctx.out.glob("board_lead_*.csv"), key=lambda p: int(p.stem.split("_")[-1]))
        if not files:
            _refuse("no board_lead_<L>.csv yet", fix="score a lead first")
        lines = ["# Common rivals board", "",
                 "Run: %s (fingerprint %s). Band %s (the nowcast band at every lead)."
                 % (run.name, run.fingerprint[:8], repr(run.band)),
                 _accepted_line(bd),
                 "Guarded vs our headline decides; raw vs raw is printed beside. BEATS = ours beats the rival.",
                 "'our MAE' on a guarded_vs_headline row is OUR HEADLINE ANSWER (the normal output at a lead where "
                 "our own guard failed); on a raw_vs_raw row it is OUR PINNED MODEL (= HEADLINE_MODEL_TABLE "
                 "'Model MAE'). d = rival MAE - our MAE per group; d > 0 means ours is better.",
                 "", "| lead | rival | contrast | ours vs rival | d mean | d low | d high | rival MAE | our MAE "
                 "(column) | guard | timid |",
                 "|---|---|---|---|---|---|---|---|---|---|---|"]
        for p in files:
            t = pd.read_csv(p)
            for _, r in t.iterrows():
                ours_label = "headline answer" if r["contrast"] == "guarded_vs_headline" else "pinned model"
                lines.append("| %d | %s | %s | %s | %.6g | %.6g | %.6g | %.6g | %.6g (%s) | %s | %s |" % (
                    int(r["lead"]), r["learner"], r["contrast"], r["ours_beats_rival"], r["d_mean"],
                    r["d_low"], r["d_high"], r["rival_mae"], r["ours_mae"], ours_label,
                    "passed" if bool(r["guard_passed"]) else "failed", "yes" if bool(r["timid_win"]) else ""))
        ctx.replace_bytes(ctx.out / BOARD_MD, ("\n".join(lines) + "\n").encode("utf-8"))
        ctx.log("board", message="%d lead table(s)" % len(files))
        return ctx.out


# ===================================================================================================
# unlock and status (owner helpers; robustness review 1)
def unlock(config: Any = None) -> str:
    """Move a STALE heavy-job lock aside (never delete): only when the process that wrote it is dead
    (the engine's own proc.is_alive check of pid and start time). A live holder refuses."""
    cfg = load_config(config)
    eng = Engine(cfg)
    from treeroute.runs import proc
    lockp = Path(eng.machine.temp_dir) / eng.preflight.HEAVY_LOCK_FILE
    if not lockp.is_file():
        return "no heavy-job lock at %s; nothing to do" % lockp
    try:
        owner = read_json(lockp)
    except Exception as exc:                    # an unreadable lock is never guessed about
        _refuse("the heavy-job lock %s is unreadable (%s)" % (lockp, exc),
                fix="check in Task Manager that no python job runs, then move the file aside by hand")
    pid, created = owner.get("pid"), owner.get("pid_created_ms")
    if proc.is_alive(pid, created):
        _refuse("the heavy-job lock %s is held by a LIVE process (pid %s)" % (lockp, pid),
                fix="wait for that job to finish; never unlock a live job")
    dest = LY.move_aside(lockp, cfg["moved_root"], eng.registry, stamp="stale_lock_" + utc_stamp())
    return "stale lock from dead pid %s moved aside: %s -> %s" % (pid, lockp, dest)


def status(out: Any) -> str:
    """Plain progress of a board (read-only, takes no lock): status.json, whether its process is alive, the
    finished trials and leads, and the last log lines."""
    import psutil
    out = Path(out)
    lines = ["board: %s" % out]
    sp = out / STATUS_FILE
    if sp.is_file():
        st = read_json(sp)
        alive = False
        try:
            alive = psutil.pid_exists(int(st.get("pid")))
        except (TypeError, ValueError):
            pass
        lines.append("last status: %s %s %s %s at %s (pid %s: %s)"
                     % (st.get("command"), st.get("stage"), st.get("learner") or "", st.get("trial") or "",
                        st.get("utc"), st.get("pid"), "RUNNING" if alive else "not running"))
        if not alive and st.get("stage") not in ("done", "locked", "board"):
            lines.append("the last command did not finish (killed, crashed or a power cut): rerun the same "
                         "command with --resume; if it says 'stale heavy-job lock', run unlock first")
    td = out / TRIALS_DIR
    if td.is_dir():
        lines.append("finished trials: %d" % len(list(td.glob("*/*/trial.json"))))
    lines.append("picks locked: %s" % ("yes" if (out / PICKS_LOCK).is_file() else "no"))
    for ld in sorted(out.glob("lead_*")):
        lines.append("%s: refit done for %s; scored: %s" % (
            ld.name, sorted(p.stem[len("done_"):] for p in ld.glob("done_*.json")) or "none",
            "yes" if (out / (BOARD_LEAD_CSV % int(ld.name.split("_")[1]))).is_file() else "no"))
    lp = out / LOG_FILE
    if lp.is_file():
        tail = lp.read_text(encoding="utf-8").splitlines()[-5:]
        lines.append("last log lines:")
        lines.extend("  " + t for t in tail)
    return "\n".join(lines)


__all__ = ["HarnessRefusal", "apply_guard", "load_config", "Run", "ExportLead", "learners_for", "board_learners",
           "trial_list", "pick_learner", "trials_to_extend", "check_extension_prefix", "pick_flags",
           "own_best", "init", "probe", "tune", "lock", "refit", "score", "board",
           "open_test_labels_rivals", "verify_lock", "harness_code_sha", "unlock", "status",
           "export_content_sha", "export_identity"]
