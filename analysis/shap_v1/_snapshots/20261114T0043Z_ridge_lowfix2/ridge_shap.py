"""Ridge loader (fire, PM2.5, defo, NDVI): the board's own scoring of the whole test set, checked bit for bit, then
rival_shap.py's exact linear SHAP of ridge on the registered sample (PROTOCOL.md sections 4.2, 5, 9; scope (i), ruling
AY1). A script of its own: rival_shap.py, run_shap.py, compare_shap.py and the shared helpers are unchanged, so every
finished piece keeps its resume identity. One process per problem and lead, the boards' pins (8 threads).

Why. rival_shap.py copies every design block into one array stored row by row, then multiplies; the board multiplied
each block as it was made. When the model has missing flags, the board's block is stored column by column, numpy then
calls another BLAS routine, which adds the same terms in another order, and the last bit can differ (fire lead 0:
95,711 of 96,000 saved test predictions bit-equal with the row-by-row copy, 96,000 of 96,000 with the board's own
blocks). Memory alignment does not matter. Coral's model has no flags, so its blocks are stored row by row too:
rival_shap.py passed there, and its piece is kept.

  py -3.9 -I -B ridge_shap.py --problem fire --lead 0 [--n N] [--sample-root DIR] [--register FILE] [--rows K]
        [--out-root DIR] [--log-dir DIR] [--exactness-only]

  --n N             the registered sample size; by default the registered N is used, and a given N must equal it
  --out-root        the MODELS root: outputs go to <out-root>/rival_ridge/ (default out/<problem>/lead_<L>/)
  --log-dir         default logs/ (a smoke passes a folder of its own)
  --rows K          smoke only: explain the first K sample rows; refused without --out-root (a K-row piece in out/
                    would make compare_shap.py refuse the whole comparison)
  --exactness-only  S-ENV and S-EXACT only, no sample needed: writes ridge_shap_exactness.json and nothing else

Outputs <models root>/rival_ridge/: ridge_shap_exactness.json, rows.parquet, background_keys.parquet, meta.json and
rows.parquet.done.json (its 'script' field names this script), the format of every other rival: compare_shap.py finds
the folder by its name and labels fire's ridge 'raw model, declined by its guard' from meta.guard (D6). FAILED.json
names the gate after a stop. exactness.json in the same folder is rival_shap.py's own check (outside coral, its failed
one): this script never writes, moves or removes it, and copies its counts into its own record as information.
Log: <log dir>/ridge_shap_<problem>_lead<L>.log.

Refusals before anything is read (exit 1, nothing written): another heavy job is running, shown by a heavy-job lock
(D:/treeroute/tmp/ or the analysis' engine_tmp/) or by a Python process whose command line names run_shap, tr_rebuild,
tr_shap, rival_shap, compare_shap, make_sample, bardl_shap or ridge_shap (other than this process and the ones that
started it; run_shap.py's later steps hold no lock, and psutil must be importable for this check); the board has no
ridge pick or lacks a ridge record; the source of a copied rival_shap.py function changed (the drift guard). A folder
that holds another script's finished piece (coral: rival_shap.py's) is never written: when that piece is current
under rival_shap.py's own identity (rival_shap.py:539-544) the run ends with 'nothing to do' (exit 0), otherwise it
refuses (exit 1); --exactness-only refuses there (exit 1).

Gates (exit 3, logged as 'STOP <gate>'):
  S-ENV     before any data is read: the library versions and thread pins equal the board's (rival_shap.py's
            env_gate), and numpy's BLAS pool (blas, openblas, libscipy_openblas) runs the board's thread count (8)
            and board.json threadpool_info lists it with that count. Another count changes a few link-space rows at
            the ends of the threads' shares in some blocks (measured on synthetic blocks of the real shapes: the last
            blocks of PM2.5, NDVI and defo, in either memory order; no full block, and not fire's or coral's), and in
            y units fewer or none: this gate, not S-EXACT, guards the thread count (for fire it is stricter than
            needed);
  S-SAMPLE  the sample and its background file are registered and unchanged during the run, --n (when given) equals
            the registered N, every sample row is a test row (rival_shap.py's load_context);
  S-EXACT   inputs: the board's records agree with each other and with the export (done_ridge.json, model_ridge.json,
            picks.json, the SHA-256 of preds_ridge.parquet, board.json, lead_<L>/export.json, the export's content and
            files hashes); bits: the board's own scoring of the whole test set (below) reproduces pre__rival_ridge and
            its legal clip arm__rival_ridge_raw bit for bit on every row, with the same keys (rival_shap.py's
            bit_check: equal values, NaN and +-inf in the same places; the rows whose float64 bit patterns are equal
            are counted too, as information). The saved ridge values are always finite (the board's inverse link and
            clip refuse NaN and +-inf): a non-finite value on this side is a refusal of the engine, recorded as an
            S-EXACT stop. reread: the test set rival_shap.py's load_context reads for the SHAP values is the one
            checked, bit for bit; repeat: a second scoring of the whole test set equals the first bit for bit.
            ridge_shap_exactness.json is written at every S-EXACT;
  S-BG      every background key is a refit row (rival_shap.py's load_context);
  S-EVAL    the evaluator's design values at the explained rows equal the board's design blocks there, bit for bit;
            then, in shapv1_rows.write, our evaluator against the model's own value within 1e-9 at every explained row
            (the link value of the board's whole-test-set scoring; its back-transform equals the saved pre bit for
            bit) and at every background row (the board's scoring code run on those rows: the board never scored
            them);
  S-ADD, S-ZERO, S-RESID  in shapv1_rows.write (whose stops name the failed checks in FAILED.json's checks_passed).
S-ENV, and S-SAMPLE on the sample's identity or --n, write nothing and leave a finished piece as it is: they come
before the piece's identity is known, and a mistyped option or path does not disprove the piece (compare_shap.py
checks the sample itself). The other stops (S-SAMPLE in load_context, S-EXACT, S-BG, S-EVAL) remove this script's own
done record (never another script's), write FAILED.json naming the gate and exit 3; in a folder holding another
script's finished piece no stop writes anything. A passing S-EXACT removes this script's FAILED.json of an earlier
S-EXACT stop at stage inputs or bits (the checks it has just repeated) and no other FAILED.json; the shared writer
removes FAILED.json when a full run passes.
Exit codes: 0 done, skipped, or another script's current piece; 3 a gate; 1 a crash or a refusal (above; also a done
record that cannot be read, a write outside the analysis folder, an internal check); 2 argparse. After a finished or
skipped piece, a comparison of the same models root that does not cover it is logged as a REMINDER (logging only).

The board's scoring (rivals/models.py _fit_ridge, score loop 1135-1146; harness.py refit 2234-2245 and clip
1298-1299): X and the normals of ExportLead.read_set('test') (the export's sorted group order, as the board's
scoreset('test')); for every 65,536-row block, a fresh design block RidgeDesign.block minus the saved means, times the
saved coefficients of the pinned alpha, plus the intercept, with numpy's BLAS at 8 threads; then the inverse link (pre)
and the engine's clip_to_legal of pre (raw). The block is used as it was made: never copied, never preallocated, never
another block size, never a subset or another row order, never other threads.

SHAP: rival_shap.py's ridge arithmetic. Called, not copied: rival_shap.py env_gate, load_context (S-ENV, the sample,
the test set, the background rows, the players with merged exact copies, the variable map), score_data, ridge_design
(the evaluator's explained and background designs), bit_check, finish (the offset to 'normal', base, eta, pre, meta;
then shapv1_rows.write), model_files, HELPERS. Copied, with file:line:
  rival_shap.py 312-321   design_of: the design namespace RidgeDesign.block reads (adapted in 2 lines: features for
                          c.ex.features, SimpleNamespace for types.SimpleNamespace; S-EXACT proves it)
  rival_shap.py 355-386   the SHAP part of run_ridge, verbatim. Its names are bound as run_ridge binds them
                          (331-341): learner = 'ridge'; params = H.trial_params(board, H._pick_trial('ridge', pick),
                          lead); mj = model_ridge.json; coef = mj['coef'][H.ck_label(pinned)]; tbar = mj['intercept'];
                          names = mj['names'] (what ridge_design returns at 341); score_data and ridge_design are
                          rival_shap.py's own
  rival_shap.py 94-100    open_export (H.Run, H.ExportLead) and the read of the test set in s_exact
                          (read_set('test')), adapted
  rival_shap.py 181-184   saved_columns (the key join of the saved predictions), adapted: both columns, key counts
  rival_shap.py 539-544   rs_identity, rebuilt from the records with rival_shap.py's own functions
  bardl_shap.py 201-206 (link_key, from compare_shap.py 75-79), 209-216 (blas_pools, extended), 221-245 (Stopper,
  adapted), 1082-1109 (compare_reminder); rivals/models.py 1141-1145 (board_scores' loop, one checkpoint);
  rivals/harness.py 183-189 (board_code's recipe).
Drift guard: the script refuses to start (exit 1) when the SHA-256 of the source of rival_shap.run_ridge or
rival_shap.ridge_design differs from COPIED_SOURCES, so the copied lines are always rival_shap.py's.
Resume identity: rival_shap.py's (problem, lead, learner, rows, the sample and background files, model files, board,
export manifest) plus the SHA-256 of this script and of every rival_shap.py helper, the boards' scoring code
(rivals/*.py, harness_code_sha) and the LIVE engine's code (engine_file_sha).
"""
import argparse
import datetime
import glob
import hashlib
import inspect
import json
import os
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shapv1_common as C  # noqa: E402
import rival_shap as RS  # noqa: E402  (sets the boards' 8-thread pins before numpy loads; imports the LIVE engine)

np, pd, pq, M, H, RW, TS = RS.np, RS.pd, RS.pq, RS.M, RS.H, RS.RW, RS.TS
import pyarrow as pa  # noqa: E402
from treeroute.layer.arms import LayerRefusal  # noqa: E402  (the LIVE engine, imported read-only by rival_shap)
from treeroute.layer.links import clip_to_legal  # noqa: E402

SCRIPT = "ridge_shap.py"
MODEL = "rival_ridge"
LEARNER = "ridge"
EXACT_FILE = "ridge_shap_exactness.json"
EXIT_GATE = 3
KEY = list(RS.KEY)
HELPERS = (SCRIPT,) + tuple(RS.HELPERS)
NUMPY_POOL = ("blas", "openblas", "libscipy_openblas")       # numpy 2.0.2's bundled OpenBLAS (threadpoolctl names)
# SHA-256 of inspect.getsource() of the rival_shap.py functions whose lines are copied here (measured 2026-11-13 on
# rival_shap.py a3e836a5: run_ridge is lines 330-389, ridge_design 311-327)
COPIED_SOURCES = {"run_ridge": "e4739ec46bbbb9b368b3b657950273eaf7055361d3df47f9b2c0c7288f79f5da",
                  "ridge_design": "0dd33e29b52d54cdc78006945d6679cea32677b29e59587e5b1bb2d56110dc33"}
LOCKS = ("D:/treeroute/tmp/treeroute_heavy_job.lock", os.path.join(C.ROOT, "engine_tmp", "treeroute_heavy_job.lock"))
# another SHAP step at work: a Python process whose command line names one of these scripts (the lock covers only the
# engine's jobs; run_shap.py's later steps, tr_shap, rival_shap and compare, hold none)
BUSY_RX = re.compile(r"run_shap|tr_rebuild|tr_shap|rival_shap|compare_shap|make_sample|bardl_shap|ridge_shap")
PY_NAME_RX = re.compile(r"^(py|pyw|python[0-9.]*|pythonw[0-9.]*)(\.exe)?$", re.IGNORECASE)
KEPT_HARNESS_GLOB = "D:/treeroute/rivals_build/_moved/**/harness.py"     # information only (board_code)
SWITCH_PREFIXES = ("OPENBLAS_", "GOTO", "OMP_", "NPY_")          # thread and kernel switches: names and values
CLEARED_PREFIXES = ("OMP_", "OPENBLAS_", "MKL_", "NUMEXPR_", "BLIS_", "VECLIB_", "GOTO", "KMP_", "SKLEARN", "SCIPY_",
                    "NPY_", "DAAL", "ONEDAL", "TBB_")              # run_shap.py's CLEAN_PREFIXES (names only)
METHOD = ("the board's own scoring (rivals/models.py _fit_ridge, score loop 1135-1146) on the whole test set in the "
          "export's read order: per 65,536-row block a fresh design block (RidgeDesign.block) minus the saved means, "
          "times the saved coefficients of the pinned alpha, plus the intercept, with numpy's BLAS at the board's 8 "
          "threads; then the inverse link (pre) and the engine's legal clip (raw). Every row must match the saved "
          "pre__rival_ridge and arm__rival_ridge_raw bit for bit")


def parse(argv=None):
    ap = argparse.ArgumentParser(description="ridge loader: the board's own scoring checked bit for bit, then exact "
                                             "linear SHAP (PROTOCOL.md 4.2, 5, 9)")
    ap.add_argument("--problem", required=True, choices=sorted(C.PROBLEMS))
    ap.add_argument("--lead", type=int, required=True)
    ap.add_argument("--n", type=int, default=None, help="the registered sample size; default: the registered N "
                                                         "(a given N is checked: S-SAMPLE)")
    ap.add_argument("--sample-root", default=None)
    ap.add_argument("--register", default=None)
    ap.add_argument("--rows", type=int, default=0, help="smoke only: explain the first K sample rows (with --out-root)")
    ap.add_argument("--out-root", default=None, help="the models root; outputs go to <out-root>/rival_ridge/")
    ap.add_argument("--log-dir", default=None, help="default logs/; a smoke passes a folder of its own")
    ap.add_argument("--exactness-only", action="store_true", help="S-ENV and S-EXACT only (no sample needed)")
    a = ap.parse_args(argv)
    if a.rows < 0:
        ap.error("--rows must be 0 or more")
    if a.rows and not a.out_root:
        ap.error("--rows is for a smoke and needs --out-root: a piece of K rows in out/ would make compare_shap.py "
                 "refuse the whole comparison")
    return a


# ---------------------------------------------------------------------------------------------------------------
# small helpers
def read_bytes(path):
    with open(path, "rb") as fh:
        data = fh.read()
    return data, C.sha256_bytes(data)


def refuse(log, msg):
    """A structural refusal (exit 1): logged, then raised."""
    log("REFUSED: %s" % msg)
    raise SystemExit("REFUSED: %s" % C.redact(msg))


def same_bits(a, b):
    """Two arrays equal bit for bit (same shape and dtype; floats compared as their bit patterns, so NaN equals NaN)."""
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape or a.dtype != b.dtype:
        return False
    if a.dtype.kind != "f":
        return bool(np.array_equal(a, b))
    u = {2: np.uint16, 4: np.uint32, 8: np.uint64}[a.dtype.itemsize]
    return bool(np.array_equal(a.view(u), b.view(u)))


def pattern_equal_rows(a, b):
    """The number of rows whose float64 bit patterns are equal (information beside bit_check, which compares values:
    there -0.0 equals +0.0)."""
    a = np.ascontiguousarray(a, np.float64)
    b = np.ascontiguousarray(b, np.float64)
    return int(np.count_nonzero(a.view(np.uint64) == b.view(np.uint64)))


def link_key(meta):
    """compare_shap.py:75-79 (copied through bardl_shap.py:201-206: compare pins 1 thread and cannot be imported
    here), a self-check of the label compare_shap.py gives this piece."""
    c = meta.get("c")
    ub = meta.get("ub")
    return "%s|c=%s|ub=%s" % (meta.get("link"), "-" if c is None else "%.12g" % float(c),
                              "-" if ub is None else "%.12g" % float(ub))


def blas_pools():
    """The live thread pools (bardl_shap.py:209-216, extended): rows in board.json's threadpool_info format
    [user_api, internal_api, prefix, num_threads], sorted, and per pool its version, architecture and threading
    layer. Never a file path."""
    try:
        import threadpoolctl
        info = threadpoolctl.threadpool_info()
    except Exception as exc:                          # the S-ENV gate then fails (no pool found)
        return [], [{"error": type(exc).__name__}]
    rows = sorted([str(i.get("user_api")), str(i.get("internal_api")), str(i.get("prefix")), int(i.get("num_threads"))]
                  for i in info)
    keys = ("user_api", "internal_api", "prefix", "version", "architecture", "threading_layer", "num_threads")
    details = sorted(({k: i.get(k) for k in keys} for i in info), key=lambda d: (str(d["user_api"]), str(d["prefix"])))
    return rows, details


def switches():
    """The thread and kernel switches of this process: names and values of OPENBLAS_*, GOTO*, OMP_* and NPY_*
    variables, and only the names of the other variables run_shap.py clears."""
    env = os.environ
    vals = {k: env[k] for k in sorted(env) if k.upper().startswith(SWITCH_PREFIXES)}
    names = sorted(k for k in env if k.upper().startswith(CLEARED_PREFIXES) and k not in vals)
    return {"values": vals, "other_names": names, "OPENBLAS_CORETYPE": env.get("OPENBLAS_CORETYPE")}


def read_done(path):
    """(state, record) of a done record: 'none' (no file), 'unreadable', or 'own' / 'foreign' by its 'script'."""
    if not os.path.isfile(path):
        return "none", None
    try:
        rec = C.read_json(path)
    except (OSError, ValueError):
        return "unreadable", None
    if not isinstance(rec, dict):
        return "unreadable", None
    return ("own" if rec.get("script") == SCRIPT else "foreign"), rec


# ---------------------------------------------------------------------------------------------------------------
# gate stops
class Stopper(object):
    """Gate stops of the rival_ridge folder (bardl_shap.py:221-245, adapted). A stop that disproves the piece or
    follows the start of a recompute removes this script's own done record (never another script's), writes
    FAILED.json naming the gate and exits 3. A stop with write=False (S-ENV; S-SAMPLE on the sample's identity or
    --n, before the piece's identity is known) and every stop in a folder holding another script's finished piece
    write nothing: they log (with why) and exit 3."""

    def __init__(self, out, problem, lead, log):
        self.out, self.problem, self.lead, self.log = out, problem, int(lead), log
        self.foreign = False

    def drop_done(self, why):
        if self.foreign:
            return False
        path = os.path.join(self.out, "rows.parquet.done.json")
        state, _ = read_done(path)
        if state != "own":                            # never another script's record
            return False
        os.remove(C.assert_writable(path))
        self.log("%s: removed this script's old done record (%s)" % (MODEL, why))
        return True

    def stop(self, gate, detail, extra=None, write=True, why=None):
        if self.foreign or not write:
            self.log("STOP %s: %s: %s (nothing written: %s)" % (
                gate, MODEL, detail, "the folder holds another script's finished piece" if self.foreign
                else (why or "this stop comes before any data is read")))
            raise SystemExit(EXIT_GATE)
        C.makedirs(self.out)
        self.drop_done("a stop at %s leaves no finished piece" % gate)
        rec = {"model": MODEL, "problem": self.problem, "lead": self.lead, "gate": gate, "detail": detail,
               "pass": False, "script": SCRIPT, "finished": datetime.datetime.now().isoformat(timespec="seconds")}
        if extra:
            rec.update(extra)
        C.write_json(os.path.join(self.out, "FAILED.json"), rec)
        self.log("STOP %s: %s: %s" % (gate, MODEL, detail))
        raise SystemExit(EXIT_GATE)

    def clear_failed(self):
        """After S-EXACT passed: remove this script's own FAILED.json of an earlier S-EXACT stop at stage inputs or
        bits, the checks just repeated. Every other FAILED.json stays: another script's, and this script's records
        of S-SAMPLE, S-BG, S-EVAL, the shared writer's checks (no gate field) and S-EXACT's reread and repeat stages,
        which this check does not repeat (the shared writer removes FAILED.json when a full run passes)."""
        path = os.path.join(self.out, "FAILED.json")
        if self.foreign or not os.path.isfile(path):
            return False
        try:
            rec = C.read_json(path)
        except (OSError, ValueError):
            return False
        ex = rec.get("exactness") if isinstance(rec, dict) else None
        stage = ex.get("stage") if isinstance(ex, dict) else None
        if not (isinstance(rec, dict) and rec.get("script") == SCRIPT and rec.get("gate") == "S-EXACT"
                and stage in ("inputs", "bits")):
            return False
        os.remove(C.assert_writable(path))
        self.log("%s: removed this script's FAILED.json of an earlier S-EXACT stop (stage %s): S-EXACT passed now"
                 % (MODEL, stage))
        return True


def live_processes():
    """(pid, name, command line) of every process this account can see, or None when psutil cannot be imported."""
    try:
        import psutil
    except ImportError:
        return None
    out = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            info = p.info
            out.append((int(info.get("pid") or -1), str(info.get("name") or ""), " ".join(info.get("cmdline") or [])))
        except Exception:                             # a process that ended or hides its command line
            continue
    return out


def own_lineage():
    """This process and the ones that started it (the py launcher, the shell): never counted as another job. The
    direct parent also comes from os.getppid(), so the py launcher is skipped even if psutil's walk fails."""
    ids = {os.getpid(), os.getppid()}
    try:
        import psutil
        ids.update(p.pid for p in psutil.Process().parents())
    except Exception:
        pass
    return ids


def busy_processes(procs=None, skip=None):
    """[(script, pid)] of the other SHAP steps at work: a Python process (by its executable name) whose command line
    names one of BUSY_RX's scripts, other than this process and its parents. Only the script name and the process id
    are returned (a command line holds paths). None when psutil cannot be imported."""
    procs = live_processes() if procs is None else procs
    if procs is None:
        return None
    skip = own_lineage() if skip is None else set(skip)
    hits = []
    for pid, name, cl in procs:
        if pid in skip or not PY_NAME_RX.match(os.path.basename(str(name or ""))):
            continue
        m = BUSY_RX.search(str(cl or ""))
        if m:
            hits.append((m.group(0) + ".py", int(pid)))
    return sorted(hits)


def heavy_job_gate(log):
    """One heavy job at a time: refuse (exit 1, nothing read or written) while a heavy-job lock exists or another
    SHAP step runs (run_shap.py's later steps hold no lock)."""
    held = [p for p in LOCKS if os.path.exists(p)]
    if held:
        refuse(log, "a heavy job holds %s: run this command again when that job has finished (nothing was read or "
                    "written)" % ", ".join(held))
    busy = busy_processes()
    if busy is None:
        refuse(log, "psutil cannot be imported, so other SHAP steps at work cannot be seen: nothing was read or "
                    "written")
    if busy:
        refuse(log, "another SHAP step is running (%s): run this command again when it has finished; run_shap.py's "
                    "later steps hold no lock (nothing was read or written)"
               % ", ".join("%s pid %d" % b for b in busy))


def env_gates(st, bd, log):
    """S-ENV before any data is read: rival_shap.py's env_gate (library versions, thread pins, board threads 8),
    then numpy's BLAS pool at the board's thread count, recorded in board.json's threadpool_info. Writes nothing."""
    try:
        RS.env_gate(bd.board, log)
    except SystemExit as exc:                         # its message starts with 'STOP S-ENV: '
        st.stop("S-ENV", str(exc.code).replace("STOP S-ENV: ", "", 1), write=False)
    rows, details = blas_pools()
    want = bd.board.get("threads")
    try:
        want_i = int(want)
    except (TypeError, ValueError):
        want_i = None
    have = [r for r in rows if tuple(r[:3]) == NUMPY_POOL]
    listed = [list(r) for r in (bd.board.get("threadpool_info") or []) if list(r[:3]) == list(NUMPY_POOL)]
    ok_run = bool(have) and want_i is not None and all(r[3] == want_i for r in have)
    ok_board = want_i is not None and any(len(r) == 4 and r[3] == want_i for r in listed)
    env = {"pins": {v: os.environ.get(v) for v in C.PIN_VARS}, "board_threads": want, "numpy_blas_pool": have,
           "board_numpy_blas_pool": listed, "blas_pools": rows, "blas_details": details, "switches": switches(),
           "pass": bool(ok_run and ok_board)}
    if not env["pass"]:
        st.stop("S-ENV", "numpy's BLAS pool %s must run the board's %s threads and board.json threadpool_info must "
                         "list it with that count (this process: %s; board.json: %s)" % (list(NUMPY_POOL), want, have,
                                                                                         listed), write=False)
    nb = [d for d in details if (d.get("user_api"), d.get("internal_api"), d.get("prefix")) == NUMPY_POOL]
    log("S-ENV: numpy's BLAS %s runs %d threads, the board's count (OpenBLAS %s, %s, %s)"
        % (NUMPY_POOL[2], want_i, nb[0].get("version") if nb else None, nb[0].get("architecture") if nb else None,
           nb[0].get("threading_layer") if nb else None))
    return env


def drift_guard(log):
    """The copied lines are rival_shap.py's: the SHA-256 of the source of RS.run_ridge and RS.ridge_design must be
    the values recorded in COPIED_SOURCES. Refuses (exit 1) otherwise, before any data is read."""
    rec = {}
    for name in sorted(COPIED_SOURCES):
        lines, first = inspect.getsourcelines(getattr(RS, name))
        sha = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
        rec[name] = {"lines": [first, first + len(lines) - 1], "sha256": sha, "recorded": COPIED_SOURCES[name],
                     "equal": sha == COPIED_SOURCES[name]}
    bad = sorted(k for k, v in rec.items() if not v["equal"])
    if bad:
        refuse(log, "the source of rival_shap.py %s changed after this script copied its lines (now %s): compare the "
                    "copy in ridge_shap.py with rival_shap.py, then record the new SHA-256 in COPIED_SOURCES"
                    % (bad, {k: rec[k]["sha256"][:16] for k in bad}))
    log("drift guard: the copied rival_shap.py lines are current (run_ridge %d-%d, ridge_design %d-%d)"
        % tuple(rec["run_ridge"]["lines"] + rec["ridge_design"]["lines"]))
    return rec


# ---------------------------------------------------------------------------------------------------------------
# the board's records (no data file)
def board_records(a, log):
    """The board's records of ridge at the lead, parsed from the bytes whose SHA-256 is kept (records only; refuses
    a missing record or pick, exit 1)."""
    P = C.PROBLEMS[a.problem]
    L = int(a.lead)
    bd = SimpleNamespace(P=P, lead=L, ldir=os.path.join(P["board"], "lead_%d" % L), sha={}, path={}, engine_now=None)

    def rec(name, path, as_json=True):
        if not os.path.isfile(path):
            refuse(log, "%s does not exist" % path)
        data, sha = read_bytes(path)
        bd.sha[name], bd.path[name] = sha, path
        return json.loads(data.decode("utf-8")) if as_json else data
    bd.board = rec("board.json", os.path.join(P["board"], "board.json"))
    picks = (rec("picks.json", os.path.join(P["board"], "picks.json")).get("picks")) or {}
    if LEARNER not in picks:
        refuse(log, "the board %s has no ridge pick" % P["board"])
    bd.pick = picks[LEARNER]
    bd.done = rec("done", os.path.join(bd.ldir, "done_ridge.json"))
    bd.mj = rec("model", os.path.join(bd.ldir, "model_ridge.json"))
    bd.preds_bytes = rec("preds", os.path.join(bd.ldir, "preds_ridge.parquet"), as_json=False)
    bd.lead_export = rec("export.json", os.path.join(bd.ldir, "export.json"))
    bd.params = H.trial_params(bd.board, H._pick_trial(LEARNER, bd.pick), L)
    bd.pinned = H._pinned(LEARNER, bd.pick)
    bd.label = H.ck_label(bd.pinned)
    if bd.label not in (bd.mj.get("coef") or {}):
        refuse(log, "model_ridge.json holds no coefficients at the pinned alpha %s" % bd.label)
    bd.legal = H.board_legal(bd.board)
    bd.threads = bd.board.get("threads")
    bd.em_path = os.path.join(str(H._lead_export_dir(bd.board, L)), "export_manifest.json")
    log("board records: ridge pick %s (link %s, alpha %s%s), %s test rows, guard %s"
        % (bd.pick.get("trial_id"), bd.params.get("link"), bd.label,
           (", flags %s" % bd.pick.get("flags")) if bd.pick.get("flags") else "", bd.done.get("test_rows"),
           "passed" if (bd.done.get("guard") or {}).get("passed") else "declined (D6)"))
    return bd


def engine_now(bd):
    if bd.engine_now is None:
        bd.engine_now = H.engine_file_sha()
    return bd.engine_now


def bad_names(names, features):
    """Model names that are neither an export column, the missing flag of one, nor __normal__."""
    raw = set(str(f) for f in features) | {"__normal__"}
    return [n for n in names if (n[len("missing__"):] if n.startswith("missing__") else n) not in raw]


def records_check(bd, ex, n_test):
    """S-EXACT (inputs): the board's records agree with each other and with the export. Returns (ok, {check:
    {value, expected, equal}})."""
    R = {}

    def eq(name, value, expected):
        R[name] = {"value": value, "expected": expected, "equal": bool(value == expected)}
    done, mj = bd.done, bd.mj
    fi = done.get("fit_info") or {}
    names = list(mj.get("names") or [])
    flags = [n for n in names if n.startswith("missing__")]
    coef = (mj.get("coef") or {}).get(bd.label) or []
    eq("done.learner", done.get("learner"), LEARNER)
    eq("done.lead", done.get("lead"), bd.lead)
    eq("done.pinned = the pick's checkpoint label", done.get("pinned"), bd.label)
    eq("done.model_file", done.get("model_file"), "model_ridge.json")
    eq("done.pick = picks.json's ridge pick", C.canonical(done.get("pick")), C.canonical(bd.pick))
    eq("done.preds_sha256 = the SHA-256 of preds_ridge.parquet", done.get("preds_sha256"), bd.sha["preds"])
    eq("done.test_rows = the export's test rows", done.get("test_rows"), int(n_test))
    eq("done.fit_info.design_columns = the model's names", fi.get("design_columns"), len(names))
    eq("done.fit_info.flag_columns = the model's missing flags", fi.get("flag_columns"), len(flags))
    eq("done.fit_info.dropped_columns = the model's dropped", fi.get("dropped_columns"), mj.get("dropped"))
    eq("model.flags = its missing__ names", list(mj.get("flags") or []), flags)
    eq("model: mean, sd and the pinned coef have one value per name",
       [len(mj.get("mean") or []), len(mj.get("sd") or []), len(coef)], [len(names)] * 3)
    eq("model: every name is an export column, its missing flag, or __normal__", bad_names(names, ex.features), [])
    eq("board.json unchanged since it was read", C.sha256_file(bd.path["board.json"]), bd.sha["board.json"])
    le, tag = bd.lead_export, "lead_%d/export.json" % bd.lead
    eq(tag + " lead", le.get("lead"), bd.lead)
    eq(tag + " export_content_sha256 = the export's content hash", le.get("export_content_sha256"), ex.content_sha)
    eq(tag + " export_files_sha256 = the export's files hash", le.get("export_files_sha256"), ex.files_sha())
    if bd.lead == 0:
        l0 = (bd.board.get("export") or {}).get("lead_0") or {}
        eq("board.json export.lead_0.content_sha256 = the export's content hash", l0.get("content_sha256"),
           ex.content_sha)
        eq("board.json export.lead_0.files_sha256 = the export's files hash", l0.get("files_sha256"), ex.files_sha())
        eq("board.json export.lead_0.manifest_sha256 = the export manifest's SHA-256", l0.get("manifest_sha256"),
           ex.manifest_sha)
    return all(v["equal"] for v in R.values()), R


def board_code(board):
    """Information, never a gate: the rivals code-hash recipe (rivals/harness.py:183-189) over today's rivals/*.py
    and, when it differs from the board's harness_code_sha256, with harness.py taken from each kept copy under
    rivals_build/_moved/ in turn; reproduced_with names the copy that gives the board's hash. models.py holds the
    whole ridge scoring path."""
    try:
        root = Path(H.__file__).resolve().parent
        files = sorted(root.glob("*.py"))

        def recipe(sub=None):
            parts = [[p.name, H.sha256_file(sub if (sub is not None and p.name == "harness.py") else p)]
                     for p in files]
            return H.sha256_bytes(H.dumps_canonical(parts).encode("ascii"))
        today = H.harness_code_sha()
        recorded = board.get("harness_code_sha256")
        out = {"recipe": "rivals/harness.py:183-189 (harness_code_sha)", "today": today,
               "recipe_self_check": recipe() == today, "recorded": recorded, "equal_today": today == recorded,
               "reproduced_with": "today's rivals/*.py" if today == recorded else None, "kept_copies_tried": 0,
               "models_py_sha256": H.sha256_file(root / "models.py"), "gate": False}
        if today != recorded:
            kept = sorted(glob.glob(KEPT_HARNESS_GLOB, recursive=True))
            out["kept_copies_tried"] = len(kept)
            for k in kept:
                if recipe(Path(k)) == recorded:
                    try:
                        rel = os.path.relpath(k, C.TREEROUTE).replace("\\", "/")
                    except ValueError:
                        rel = C.redact(k).replace("\\", "/")
                    out["reproduced_with"] = "today's rivals/*.py with harness.py from %s" % rel
                    break
        return out
    except OSError as exc:
        return {"error": "%s: %s" % (type(exc).__name__, exc), "gate": False}


def rival_shap_record(out):
    """rival_shap.py's own exactness.json in this folder (read only), or None."""
    path = os.path.join(out, "exactness.json")
    if not os.path.isfile(path):
        return None
    try:
        r = C.read_json(path)
    except (OSError, ValueError):
        return {"unreadable": True}
    rec = {k: r.get(k) for k in ("rows", "rows_finite", "bit_equal_rows", "max_abs_diff", "pass")}
    rec["file"] = "exactness.json (rival_shap.py's own check of its row-by-row copy; kept, never changed here)"
    return rec


def log_rival_shap_record(out, log):
    r = rival_shap_record(out)
    if r and not r.get("unreadable"):
        log("rival_shap.py's own check in this folder (exactness.json, kept): %s of %s test rows bit-equal: %s"
            % (r.get("bit_equal_rows"), r.get("rows_finite"), "PASS" if r.get("pass") else "FAIL"))


# ---------------------------------------------------------------------------------------------------------------
# identities and the sample
def sample_ident(a, st):
    """The registered sample's identity (S-SAMPLE) and a given --n against its registered N (by default the
    registered N is used). A stop here comes before the piece's identity is known: it writes nothing and leaves a
    finished piece as it is (a mistyped --n, --register or --sample-root does not disprove it, and compare_shap.py
    checks the sample against the register itself)."""
    why = "this stop comes before the piece's identity is known; a finished piece here stays as it is"
    sroot = a.sample_root or C.sample_dir(a.problem)
    try:
        ident = C.sample_identity(a.problem, sroot, a.register, lead=a.lead)
    except SystemExit as exc:                         # its message starts with 'STOP S-SAMPLE: '
        st.stop("S-SAMPLE", str(exc.code).replace("STOP S-SAMPLE: ", "", 1), write=False, why=why)
    nreg = ident.get("n_asked") if ident.get("n_asked") is not None else ident.get("n")
    if a.n is not None and (nreg is None or int(nreg) != int(a.n)):
        st.stop("S-SAMPLE", "--n %d differs from the registered N %s (leave --n out to use the registered N)"
                % (a.n, nreg), write=False, why=why)
    st.log("sample: registered (tag %s, N %s%s)" % (ident.get("tag"), nreg, "" if a.n is None else ", --n equal"))
    return sroot, ident


def rs_identity(a, bd, ident):
    """rival_shap.py:539-544 rebuilt from the records with rival_shap.py's own functions: the identity rival_shap.py
    gives its ridge piece (coral's finished piece is recognised by it)."""
    return {"problem": a.problem, "lead": a.lead, "learner": LEARNER, "rows": a.rows,
            "sample": ident["sample_sha256"], "background_file": ident["background_sha256"],
            "model_files": RS.model_files(SimpleNamespace(ldir=bd.ldir), LEARNER),
            "board": C.sha256_file(os.path.join(bd.P["board"], "board.json")),
            "export_manifest": C.sha256_file(bd.em_path) if os.path.isfile(bd.em_path) else None,
            "scripts": {f: C.sha256_file(os.path.join(RS.HERE, f)) for f in RS.HELPERS}}


def identity(a, bd, ident):
    """This script's resume identity: rival_shap.py's, plus this script, the boards' scoring code and the LIVE
    engine's code."""
    inputs = rs_identity(a, bd, ident)
    inputs.update({"loader": SCRIPT, "scripts": {f: C.sha256_file(os.path.join(HERE, f)) for f in HELPERS},
                   "rivals_code": H.harness_code_sha(), "engine_code": engine_now(bd)})
    return inputs


def foreign_piece(a, bd, st, log):
    """A folder holding another script's finished piece (coral: rival_shap.py's): nothing is written. Current under
    rival_shap.py's own identity: 'nothing to do' (exit 0); otherwise a refusal (exit 1)."""
    _, ident = sample_ident(a, st)                    # st.foreign: a stop here writes nothing
    if C.piece_done(os.path.join(st.out, "rows.parquet"), rs_identity(a, bd, ident)):
        log("%s: rival_shap.py's own ridge piece is finished here and current: nothing to do (this script writes "
            "nothing into another script's folder)" % MODEL)
        log_rival_shap_record(st.out, log)
        compare_reminder(st.out, MODEL, a.problem, a.lead, log)
        return 0
    refuse(log, "%s holds another script's finished ridge piece that is not current under rival_shap.py's own "
                "identity (rival_shap.py:539-544): this script never removes another script's files; run "
                "rival_shap.py for this problem-lead again, or move the folder aside by hand" % st.out)


# ---------------------------------------------------------------------------------------------------------------
# S-EXACT: the board's own scoring, on the whole test set, bit for bit
def design_of(features, mj):
    """rival_shap.py:312-321, adapted in 2 lines (features for c.ex.features, SimpleNamespace for
    types.SimpleNamespace): the design namespace RidgeDesign.block reads, the means and the names."""
    names = mj["names"]
    raw_names = list(features) + ["__normal__"]
    values = [n for n in names if not n.startswith("missing__")]
    flags = [n for n in names if n.startswith("missing__")]
    mu = np.asarray(mj["mean"], np.float64)
    imp = np.zeros(len(raw_names))
    keep = np.array([raw_names.index(n) for n in values], np.int64)
    imp[keep] = mu[:len(values)]
    d = SimpleNamespace(p_raw=len(raw_names), mean_impute=imp, keep_value=keep,
                        flag_cols=np.array([raw_names.index(n[len("missing__"):]) for n in flags], np.int64))
    return d, mu, names


def board_scores(d, mu, tbar, coef, X, scn, also_c=False, keep_pos=None):
    """The board's score loop (rivals/models.py:1141-1145, one checkpoint): per 65,536-row block of X, in X's own row
    order, a fresh design block (RidgeDesign.block) minus the means, times the coefficients, plus the intercept. The
    block is used exactly as it was made (never copied, never preallocated): its memory order decides numpy's BLAS
    routine and so the order in which the terms are added. Returns (out, out_c, blocks, kept): out_c (information,
    also_c) multiplies a row-by-row copy of each block, which is rival_shap.py's arithmetic; kept holds the blocks'
    design rows at keep_pos (in keep_pos order)."""
    m = int(X.shape[0])
    out = np.empty(m, dtype=np.float64)
    out_c = np.empty(m, dtype=np.float64) if also_c else None
    keep_pos = None if keep_pos is None else np.asarray(keep_pos, np.int64)
    kept = None
    blocks = []
    for a in range(0, m, M.RIDGE_BLOCK_ROWS):
        b = min(m, a + M.RIDGE_BLOCK_ROWS)
        Z = M.RidgeDesign.block(d, np.asarray(X[a:b]), scn[a:b]) - mu[None, :]
        out[a:b] = tbar + Z @ coef
        blocks.append({"rows": [int(a), int(b)], "C": bool(Z.flags["C_CONTIGUOUS"]),
                       "F": bool(Z.flags["F_CONTIGUOUS"]), "strides": [int(s) for s in Z.strides]})
        if also_c:
            out_c[a:b] = tbar + np.ascontiguousarray(Z) @ coef
        if keep_pos is not None:
            if kept is None:
                kept = np.empty((keep_pos.size, Z.shape[1]), dtype=np.float64)
            sel = np.flatnonzero((keep_pos >= a) & (keep_pos < b))
            if sel.size:
                kept[sel] = Z[keep_pos[sel] - a]
        del Z
    return out, out_c, blocks, kept


def saved_columns(K, preds):
    """pre__rival_ridge and arm__rival_ridge_raw in the test set's order, joined by key (rival_shap.py:181-184,
    adapted: both columns, an outer join and its key counts; the board saved its rows in the run's saved order).
    Returns (pre, raw, keys_only_saved, keys_only_test, duplicate_keys_saved, duplicate_keys_test)."""
    p = preds[KEY + ["pre__rival_ridge", "arm__rival_ridge_raw"]].copy()
    k = K[KEY].reset_index(drop=True).copy()
    for f in (p, k):
        f["unit"] = f["unit"].astype(str)
        f["time"] = f["time"].to_numpy(np.int64)
        f["issue"] = f["issue"].to_numpy(np.int64)
    dup_saved, dup_test = int(p.duplicated(KEY).sum()), int(k.duplicated(KEY).sum())
    k["_t"] = np.arange(len(k), dtype=np.int64)
    j = k.merge(p, on=KEY, how="outer", indicator=True)
    only_test = int((j["_merge"] == "left_only").sum())
    only_saved = int((j["_merge"] == "right_only").sum())
    jb = j[j["_merge"] == "both"]
    t = jb["_t"].to_numpy(np.float64).astype(np.int64)
    pre = np.full(len(k), np.nan)
    raw = np.full(len(k), np.nan)
    pre[t] = jb["pre__rival_ridge"].to_numpy(np.float64)
    raw[t] = jb["arm__rival_ridge_raw"].to_numpy(np.float64)
    return pre, raw, only_saved, only_test, dup_saved, dup_test


def where_rows_differ(v, ref, blocks, threads, limit=20):
    """Information on a FAIL: where the differing rows sit. Per block its differing rows; the first ones as (block,
    offset, offset mod 4, rows to the end of their thread share). The share rule (consecutive shares of ceil(rows /
    threads) rows per BLAS call) is an inference from the observed positions, not read from the OpenBLAS source."""
    v, ref = np.asarray(v, np.float64), np.asarray(ref, np.float64)
    bad = np.flatnonzero(~((v == ref) | (np.isnan(v) & np.isnan(ref))))
    T = max(1, int(threads or 1))
    per, first = [], []
    for k, blk in enumerate(blocks):
        a, b = blk["rows"]
        sel = bad[(bad >= a) & (bad < b)]
        per.append({"block": k, "rows": [a, b], "rows_differing": int(sel.size)})
        n = b - a
        s = -(-n // T)
        for p in sel[:max(0, limit - len(first))]:
            o = int(p - a)
            end = min(n, (o // s + 1) * s) - 1
            first.append({"block": k, "offset": o, "offset_mod_4": o % 4, "rows_to_share_end": end - o})
    return {"rows_differing": int(bad.size), "per_block": per, "first": first, "threads": T,
            "share_rule": "inferred: shares of ceil(rows / threads) consecutive rows of each block (not read from the "
                          "OpenBLAS source)"}


def exactness(mj, params, label, legal, threads, features, K, X, nm, preds, also_c=True):
    """S-EXACT (bits): the board's own scoring of the whole test set (board_scores), its inverse link and the engine's
    legal clip, against the saved pre__rival_ridge and arm__rival_ridge_raw (key-joined), bit for bit on every row;
    the key sets must be equal. K, X, nm must be the whole test set in the export's read order (read_set('test')):
    a row's last bit can depend on the block it sits in and on its place in the threads' shares of that block, so a
    subset, another order or another block size is never a bit-exact check. Pure apart from numpy's BLAS. Returns
    (record, arrays or None)."""
    t0 = time.time()
    d, mu, names = design_of(features, mj)
    coef = np.asarray(mj["coef"][label], np.float64)
    tbar = float(mj["intercept"])
    rec = {"rows_test_set": int(len(K)), "design_columns": len(names),
           "flags": len([n for n in names if n.startswith("missing__")]), "dropped": mj.get("dropped"),
           "legal": [None if abs(x) == float("inf") else x for x in legal]}
    try:
        s = M.ScoreData(name="test", X=X, normal=nm)
        scn, sz0, _ = M._target_and_offset(LEARNER, params, s, None)
        scn = np.asarray(scn, np.float64)
        out, out_c, blocks, _ = board_scores(d, mu, tbar, coef, X, scn, also_c=also_c)
        pre = np.asarray(M._to_y(LEARNER, params, sz0, out), np.float64)
        raw = clip_to_legal(np.asarray(pre, np.float64), legal, False)[0]
    except (LayerRefusal, M.ModelRefusal, H.HarnessRefusal) as exc:
        rec.update({"stage": "bits", "pass": False, "refusal": "%s: %s" % (type(exc).__name__, exc),
                    "detail": "the engine refused the board's scoring output (%s): no SHAP value" % exc,
                    "seconds": round(time.time() - t0, 1)})
        return rec, None
    sv_pre, sv_raw, only_saved, only_test, dup_saved, dup_test = saved_columns(K, preds)
    bc = RS.bit_check(pre, sv_pre)
    rc = RS.bit_check(raw, sv_raw)
    rec.update(bc)
    rec.update({"stage": "bits", "raw": rc, "keys_only_saved": only_saved, "keys_only_test": only_test,
                "duplicate_keys_saved": dup_saved, "duplicate_keys_test": dup_test, "blocks": blocks,
                "block_rows": int(M.RIDGE_BLOCK_ROWS), "rows_clipped": int(np.count_nonzero(raw != pre)),
                "link_space_sha256": C.sha256_bytes(np.ascontiguousarray(out).tobytes()),
                "bit_patterns_equal_rows": {
                    "what": "information: rows whose float64 bit patterns equal the saved ones (the gate compares "
                            "values, so -0.0 and +0.0 count as equal there)",
                    "pre": pattern_equal_rows(pre, sv_pre), "raw": pattern_equal_rows(raw, sv_raw)}})
    if also_c:
        cc = RS.bit_check(np.asarray(M._to_y(LEARNER, params, sz0, out_c), np.float64), sv_pre)
        rec["row_by_row_copy"] = {
            "what": "information: the same blocks copied row by row before the product (rival_shap.py's arithmetic)",
            "bit_equal_rows": cc["bit_equal_rows"], "rows_finite": cc["rows_finite"], "pass": cc["pass"],
            "link_space_rows_differing_from_the_board_way": int(np.count_nonzero(out_c != out))}
    rec["pass"] = bool(bc["pass"] and rc["pass"] and only_saved == 0 and only_test == 0 and dup_saved == 0
                       and dup_test == 0)
    if not rec["pass"]:
        rec["detail"] = ("ridge does not reproduce its saved predictions with the board's own scoring (pre bit-equal "
                         "%d of %d, raw %d of %d, keys only saved %d, only in the test set %d): no SHAP value"
                         % (bc["bit_equal_rows"], bc["rows_finite"], rc["bit_equal_rows"], rc["rows_finite"],
                            only_saved, only_test))
        rec["where_rows_differ"] = where_rows_differ(pre, sv_pre, blocks, threads)
    rec["seconds"] = round(time.time() - t0, 1)
    ar = SimpleNamespace(d=d, mu=mu, names=names, coef=coef, tbar=tbar, scn=scn, sz0=np.asarray(sz0, np.float64),
                         out=out, pre=pre, sv_pre=sv_pre, params=params, blocks=blocks)
    return rec, ar


def write_exactness(st, rec):
    """ridge_shap_exactness.json is always written at S-EXACT; a failed record stops (FAILED.json, exit 3)."""
    C.write_json(os.path.join(st.out, EXACT_FILE), rec)
    if not rec.get("pass"):
        keys = ("stage", "rows", "rows_finite", "bit_equal_rows", "max_abs_diff", "same_nan", "inf_equal",
                "keys_only_saved", "keys_only_test", "refusal", "inputs_pass", "inputs_failed")
        summary = {k: rec[k] for k in keys if k in rec}
        if isinstance(rec.get("raw"), dict):
            summary["raw"] = {k: rec["raw"].get(k) for k in ("bit_equal_rows", "rows_finite", "max_abs_diff", "pass")}
        st.stop("S-EXACT", rec.get("detail") or "ridge does not reproduce its saved predictions: no SHAP value",
                {"exactness": summary, "exactness_file": EXACT_FILE})


def open_export(bd):
    """rival_shap.py:94-95: the run and the lead's export (H.Run, H.ExportLead: the manifest and the files' schemas;
    the files' bytes are hash-checked when they are read)."""
    run = H.Run(bd.P["run"])
    ex = H.ExportLead(H._lead_export_dir(bd.board, bd.lead), bd.lead, run)
    return run, ex


def s_exact(bd, env, drift, st, log):
    """S-EXACT on the whole test set: the export (refusals recorded), the test set (rival_shap.py:98), the records,
    then the bits. Returns (arrays, the test set, the record)."""
    t0 = time.time()
    base = {"script": SCRIPT, "method": METHOD, "model_file": "model_ridge.json", "alpha": bd.label,
            "pick_flags": bd.pick.get("flags") or [], "env": env, "drift_guard": drift,
            "board_code_reproduced": board_code(bd.board),
            "engine_code": {"now": engine_now(bd), "board": (bd.board.get("engine") or {}).get("live_file_sha"),
                            "equal": engine_now(bd) == (bd.board.get("engine") or {}).get("live_file_sha"),
                            "gate": False},
            "rival_shap_exactness_json": rival_shap_record(st.out)}
    try:
        _, ex = open_export(bd)
        K, _, X, nm = ex.read_set("test")
    except H.HarnessRefusal as exc:
        write_exactness(st, dict(base, stage="inputs", refusal=str(exc), detail="the export refused: %s" % exc,
                                 **{"pass": False}))
    log("test set: %d rows x %d features (%s), read and hash-checked in %.1f s" % (len(K), X.shape[1], ex.dir,
                                                                                    time.time() - t0))
    ok_rec, R = records_check(bd, ex, len(K))
    base.update({"inputs_pass": ok_rec, "inputs": R})
    if not ok_rec:
        bad = sorted(k for k, v in R.items() if not v["equal"])
        write_exactness(st, dict(base, stage="inputs", inputs_failed=bad,
                                 detail="the board's records disagree: %s" % bad, **{"pass": False}))
    preds = pq.read_table(pa.BufferReader(bd.preds_bytes)).to_pandas()
    rec, ar = exactness(bd.mj, bd.params, bd.label, bd.legal, bd.threads, ex.features, K, X, nm, preds, also_c=True)
    rec = dict(base, **rec)
    rec["peak_rss_gb"] = C.rss_gb()
    rr = rec.get("raw") or {}
    if rec.get("refusal"):
        log("S-EXACT: %d record checks %s; the engine refused the board's scoring of %d test rows (%s): FAIL"
            % (len(R), "all equal" if ok_rec else "NOT all equal", len(K), rec["refusal"]))
    else:
        lay = sorted(set("F" if b["F"] and not b["C"] else ("C" if b["C"] else "other") for b in rec["blocks"]))
        bp = rec.get("bit_patterns_equal_rows") or {}
        log("S-EXACT: %d record checks %s; the board's scoring of %d test rows in %d block%s (stored %s): pre "
            "bit-equal %s of %s (max |diff| %s), raw %s of %s (equal bit patterns: pre %s, raw %s); row-by-row copy "
            "(rival_shap.py's way) %s: %s"
            % (len(R), "all equal" if ok_rec else "NOT all equal", len(K), len(rec["blocks"]),
               "" if len(rec["blocks"]) == 1 else "s", "/".join(lay),
               rec.get("bit_equal_rows"), rec.get("rows_finite"), rec.get("max_abs_diff"), rr.get("bit_equal_rows"),
               rr.get("rows_finite"), bp.get("pre"), bp.get("raw"),
               (rec.get("row_by_row_copy") or {}).get("bit_equal_rows"), "PASS" if rec["pass"] else "FAIL"))
    write_exactness(st, rec)
    return ar, SimpleNamespace(K=K, X=X, nm=nm), rec


# ---------------------------------------------------------------------------------------------------------------
# the context and the SHAP values
def load_full(a, log, st):
    """rival_shap.py's load_context (the context of its own ridge piece), its stops mapped to gates."""
    try:
        return RS.load_context(a, log)
    except SystemExit as exc:
        msg = str(exc.code)
        for prefix, gate in (("STOP S-ENV: ", "S-ENV"), ("STOP S-SAMPLE: ", "S-SAMPLE"), ("STOP S-BG: ", "S-BG")):
            if msg.startswith(prefix):
                st.stop(gate, msg[len(prefix):], write=gate != "S-ENV")
        if msg.startswith("REFUSED: ") and "sample rows are not test rows" in msg:
            st.stop("S-SAMPLE", msg[len("REFUSED: "):])
        raise


def check_context(c, ident, T, exact, st, log):
    """The SHAP context holds the sample whose identity was read, the very test set S-EXACT checked (bit for bit),
    and explained-row positions that point at the sample's own keys."""
    if (c.ident.get("sample_sha256") != ident.get("sample_sha256")
            or c.ident.get("background_sha256") != ident.get("background_sha256")):
        st.stop("S-SAMPLE", "the sample or its background file changed after its registered identity was read")
    same = (len(c.K) == len(T.K) and c.K.reset_index(drop=True).equals(T.K.reset_index(drop=True))
            and same_bits(c.X, T.X) and sorted(c.nm) == sorted(T.nm)
            and all(same_bits(np.asarray(c.nm[k]), np.asarray(T.nm[k])) for k in T.nm))
    if not same:
        write_exactness(st, dict(exact, stage="reread", detail="the test set read for the SHAP values (rival_shap.py's "
                                 "load_context) differs from the one S-EXACT checked: no SHAP value",
                                 **{"pass": False}))
    ke = c.K.iloc[np.asarray(c.epos, np.int64)]
    if not (np.array_equal(ke["unit"].astype(str).to_numpy(), c.S["unit"].astype(str).to_numpy())
            and np.array_equal(ke["time"].to_numpy(np.int64), c.S["time"].to_numpy(np.int64))):
        refuse(log, "internal: the explained rows' test-set positions do not point at the sample's (unit, time) keys")
    log("context: the test set is the one S-EXACT checked (bit for bit); %d explained rows at their own keys"
        % len(c.epos))


def shap_rows(c, a, bd, ar, exact, st, log, out):
    """The model's own value (the board's whole-test-set scoring at the explained rows, and the board's scoring code
    on the background rows), rival_shap.py's ridge SHAP arithmetic (355-386, copied word for word), the design-value
    check, then rival_shap.py's finish (offset, base, eta, pre, meta) and the shared writer."""
    t0 = time.time()
    out2, _, _, kept = board_scores(ar.d, ar.mu, ar.tbar, ar.coef, c.X, ar.scn, keep_pos=c.epos)
    if not same_bits(out2, ar.out):
        write_exactness(st, dict(exact, stage="repeat", detail="a second scoring of the whole test set differs from "
                                 "the first: no SHAP value", **{"pass": False}))
    raw_model_e = out2[np.asarray(c.epos, np.int64)]
    if not same_bits(np.asarray(M._to_y(LEARNER, ar.params, ar.sz0[c.epos], raw_model_e), np.float64),
                     ar.sv_pre[c.epos]):
        raise RuntimeError("internal: the board's scoring at the explained rows does not give their saved pre")
    # ---- the names of rival_shap.py:331-341 (run_ridge), bound for the copied lines below
    learner = LEARNER
    params, mj, coef, tbar = ar.params, bd.mj, ar.coef, ar.tbar
    names = mj["names"]                                # what ridge_design returns at rival_shap.py:341
    score_data, ridge_design = RS.score_data, RS.ridge_design
    # ---- rival_shap.py:355-386, word for word
    se = score_data(c, c.X[c.epos], {l: v[c.epos] for l, v in c.nm.items()}, "explained")
    sb = score_data(c, c.Xb, c.nmb, "background")
    cne, z0e, _ = M._target_and_offset(learner, params, se, None)
    cnb, z0b, _ = M._target_and_offset(learner, params, sb, None)
    Ze, _ = ridge_design(c, mj, se.X, cne)
    Zb, _ = ridge_design(c, mj, sb.X, cnb)
    raw_e = tbar + Ze @ coef
    raw_b = tbar + Zb @ coef
    feats = [str(f) for f in c.ex.features]
    pcol = []                                          # design column -> player (a missing flag -> its column)
    for nme in names:
        bse = nme[len("missing__"):] if nme.startswith("missing__") else nme
        pcol.append(len(c.players) - 1 if bse == "__normal__" else int(c.poc[feats.index(bse)]))
    pcol = np.asarray(pcol, np.int64)
    vcol = np.asarray([c.variables.index(c.vmap[c.players[p]]) for p in pcol], np.int64)
    px, pb, pw = TS.pairs_for(c.bg_lists)
    phi = np.zeros((Ze.shape[0], len(c.players)))
    phiv = np.zeros((Ze.shape[0], len(c.variables)))
    for i, lst in enumerate(c.bg_lists):
        contrib = coef * (Ze[i][None, :] - Zb[lst]).mean(0)       # per-pair differences first: equal -> exactly 0
        np.add.at(phi[i], pcol, contrib)
        np.add.at(phiv[i], vcol, contrib)
    # S-ZERO masks on the design columns (a player is constant when all its design columns are)
    const = np.ones((Ze.shape[0], len(c.players)), bool)
    constv = np.ones((Ze.shape[0], len(c.variables)), bool)
    for i, lst in enumerate(c.bg_lists):
        diff_cols = np.flatnonzero((Zb[lst] != Ze[i][None, :]).any(0))
        const[i, np.unique(pcol[diff_cols])] = False
        constv[i, np.unique(vcol[diff_cols])] = False
        if (np.asarray(z0b)[lst] != z0e[i]).any():
            const[i, len(c.players) - 1] = False
            constv[i, c.variables.index("normal")] = False
    # ---- end of the copy
    if kept is None or not same_bits(np.asarray(Ze, np.float64), kept):
        st.stop("S-EVAL", "the evaluator's design values at the explained rows differ from the board's design blocks "
                          "there: no SHAP value")
    raw_model_b = board_scores(ar.d, ar.mu, ar.tbar, ar.coef, sb.X, np.asarray(cnb, np.float64))[0]
    q = int(Ze.shape[1])
    g = q * np.finfo(np.float64).eps / max(1e-300, 1.0 - q * np.finfo(np.float64).eps)
    bound = float((g * (np.abs(Ze * coef[None, :]).sum(1) + abs(tbar))).max()) if Ze.size else 0.0
    extra = {"guard": bd.done.get("guard"), "method": "exact linear SHAP; a missing flag folds into its column",
             "script": SCRIPT,
             "loader": "ridge_shap.py: S-EXACT by the board's own scoring of the whole test set; the SHAP values by "
                       "rival_shap.py's ridge arithmetic",
             "model_value": "the link value of the board's own scoring of the whole test set at the explained rows; "
                            "its back-transform equals the saved pre__rival_ridge bit for bit",
             "model_value_background": "the board's scoring code (the same 65,536-row blocks) run on the background "
                                       "rows (the board never scored them)",
             "explained_design_equal_board_blocks": True, "evaluator_rounding_bound": bound,
             "exactness_file": EXACT_FILE, "link_key": link_key({"link": params.get("link"), "c": params.get("c"),
                                                                 "ub": params.get("ub")}),
             "seconds": round(time.time() - t0, 1)}
    log("ridge: exact linear SHAP on %d rows (%d players, %d variables, %d pairs); the model's value is the board's "
        "own scoring (explained) and its scoring code (background)" % (Ze.shape[0], len(c.players),
                                                                       len(c.variables), px.size))
    return RS.finish(c, a, learner, params, phi, phiv, raw_e, raw_b, z0e, z0b, raw_model_e, raw_model_b, exact, extra,
                     log, out, const, constv)


def compare_reminder(out, model, problem, lead, log):
    """bardl_shap.py:1082-1109 (copied). Logging only (a forgotten comparison): when compare/ of this models root
    holds a comparison that does not cover this finished piece (per_lead.json does not list it, or the comparison's
    done record was made from other rows: the inputs of compare_shap.py:336-339 recomputed), log a REMINDER to run
    compare_shap.py again. Never stops and never changes the exit code."""
    root = os.path.dirname(out)
    cdir = os.path.join(root, "compare")
    per_path = os.path.join(cdir, "per_lead.json")
    if not os.path.isfile(per_path):
        return None
    why = None
    try:
        per = C.read_json(per_path)
        models = [str(m) for m in (per.get("models") or [])]
        if model not in models:
            why = "it does not list %s" % model
        else:
            done = C.read_json(os.path.join(cdir, "pairs.parquet.done.json"))
            want = C.inputs_hash({"models": models, "draws": per.get("draws"), "sample": per.get("sample_sha256"),
                                  "rows": {m: C.sha256_file(os.path.join(root, m, "rows.parquet")) for m in models}})
            if done.get("inputs") != want:
                why = "it was made from other rows than the finished pieces now in its models root"
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        why = "it cannot be checked (%s)" % type(exc).__name__
    if why:
        log("REMINDER: the comparison in %s does not cover this %s piece (%s): run compare_shap.py --problem %s "
            "--lead %d again on this models root, so that it includes it" % (cdir, model, why, problem, int(lead)))
    return why


# ---------------------------------------------------------------------------------------------------------------
def main(argv=None):
    a = parse(argv)
    log = C.Log("ridge_shap_%s_lead%d" % (a.problem, a.lead), a.log_dir or C.LOGS)
    try:
        return run(a, log)
    except SystemExit:
        raise
    except Exception as exc:
        log("CRASH: %s: %s" % (type(exc).__name__, exc))
        raise


def run(a, log):
    t_start = time.time()
    log("ridge SHAP %s lead %d%s; versions %s" % (a.problem, a.lead, " (exactness only)" if a.exactness_only else "",
                                                C.versions()))
    heavy_job_gate(log)
    bd = board_records(a, log)
    out = os.path.join(a.out_root or C.out_dir(a.problem, a.lead), MODEL)
    C.assert_writable(out)
    rows_path = os.path.join(out, "rows.parquet")
    st = Stopper(out, a.problem, a.lead, log)
    state, rec = read_done(rows_path + ".done.json")
    if state == "unreadable":
        refuse(log, "%s holds a done record that cannot be read: nothing is touched; move it aside by hand" % out)
    st.foreign = state == "foreign"
    if st.foreign and a.exactness_only:
        refuse(log, "%s holds another script's finished piece (its done record names no script, or %s): "
                    "--exactness-only never writes into it; for a cross-check pass both --out-root and --log-dir "
                    "under smoke/" % (out, rec.get("script")))
    env = env_gates(st, bd, log)
    drift = drift_guard(log)
    if st.foreign:
        return foreign_piece(a, bd, st, log)
    ident = inputs = None
    if not a.exactness_only:
        _, ident = sample_ident(a, st)
        inputs = identity(a, bd, ident)
        if C.piece_done(rows_path, inputs):
            log("%s: finished piece found with matching hashes: skipped" % MODEL)
            log_rival_shap_record(out, log)
            compare_reminder(out, MODEL, a.problem, a.lead, log)
            return 0
        st.drop_done("a recompute starts")
    # ---- S-EXACT, before the background is read (minutes for NDVI and defo)
    ar, T, exact = s_exact(bd, env, drift, st, log)
    st.clear_failed()                                 # only this script's record of an S-EXACT inputs or bits stop
    if a.exactness_only:
        log_rival_shap_record(out, log)
        log("%s: exactness only: %s written (%.1f s, peak RSS %s GB)" % (MODEL, EXACT_FILE, time.time() - t_start,
                                                                         C.rss_gb()))
        return 0
    # ---- the context, the sample, the background, the SHAP values
    c = load_full(a, log, st)
    check_context(c, ident, T, exact, st, log)
    T = None
    rec = shap_rows(c, a, bd, ar, exact, st, log, out)
    C.mark_done(rows_path, inputs, {"seconds": round(time.time() - t_start, 1), "sample_sha256": ident["sample_sha256"],
                                    "background_keys_sha256": rec["background_keys_sha256"], "script": SCRIPT})
    log("%s done: %d rows; players nonzero %d of %d, variables nonzero %d of %d; additivity max %.2e / %.2e; "
        "evaluator max %.2e (background %.2e); link key %s; guard %s; %.1f s; peak RSS %s GB"
        % (MODEL, rec["rows"], rec["players_nonzero"], len(rec["players"]), rec["variables_nonzero"],
           len(rec["variables"]), rec["max_abs_additivity_error"], rec["max_abs_additivity_error_variable"],
           rec["max_abs_evaluator_minus_model"], rec["max_abs_background_evaluator_minus_model"], rec["link_key"],
           "passed" if (rec.get("guard") or {}).get("passed") else "declined (D6)", time.time() - t_start,
           C.rss_gb()))
    compare_reminder(out, MODEL, a.problem, a.lead, log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
