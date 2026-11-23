"""BARDL, the published NDVI rival (human board), at the nowcast: load its kept per-unit map, check every saved test
prediction bit for bit, then exact SHAP on the registered sample (PROTOCOL.md sections 4.2, 5, 9; scope (i), ruling
AY1). A script of its own: rival_shap.py, run_shap.py, compare_shap.py and the shared helpers are unchanged, so every
finished piece keeps its resume identity. One process per problem and lead, the board's pins (8 threads).

  py -3.9 -I -B bardl_shap.py --problem ndvi --lead 0 [--rival bardl_h1] [--n 1000] [--sample-root DIR]
        [--register FILE] [--rows K] [--out-root DIR] [--log-dir DIR] [--exactness-only]

  --out-root        the MODELS root: outputs go to <out-root>/rival_<id>/ (default out/<problem>/lead_<L>/)
  --log-dir         default logs/ (a smoke passes a folder of its own)
  --exactness-only  S-ENV and S-EXACT only, no sample needed: on success it writes exactness.json and nothing else

Outputs <models root>/rival_<id>/: exactness.json, rows.parquet, background_keys.parquet, meta.json and
rows.parquet.done.json, the format of every other rival (compare_shap.py finds the folder by its name); FAILED.json
names the gate after a stop. Log: <log dir>/bardl_shap_<problem>_lead<L>.log.

Inputs, read only (bytecode off): the human board (human_board.json, human_picks.json, lead_<L>/done_<id>.json,
preds_<id>.parquet, coverage_<id>.parquet, map_<id>.json); its slim copy slim/lead_<L> (slim_manifest.json and the
test and train files, every file hash-checked against the manifest as the tool's own reader does); the human tool's
registry and the adapter adapters/<module>.py, executed from the very bytes whose SHA-256 is recorded; the run's
derived.json; the common export's lead manifest; the common board.json.

Gates. Every stop removes this folder's own done record first (a stopped run never leaves a finished-looking piece for
the comparison), writes FAILED.json naming the gate and exits with code 3:
  S-ENV     before any data table is parsed: the library versions and thread pins equal the human board's (versions,
            constants.threads = 8);
  S-SAMPLE  the sample and its background file are registered; --n equals the registered N; every sample row is one
            test row of its group with a finite saved prediction;
  S-EXACT   the board's records agree (hashes, formats, run fingerprint, cuts, the slim copy's recorded provenance, the
            common board's link fields; the registry's SHA-256 before its bytes are parsed); every slim file has its
            manifest's SHA-256; the adapter's own predict() on every test row reproduces the saved pre and its legal
            clip raw bit for bit (exactness.json always written). It always predicts the whole slim test set, in the
            tool's own per-unit blocks, never a subset of rows: a row's BLAS dot can depend on the block it sits in
            (a last-bit difference);
  S-BG      every registered background key is a refit row of the slim copy, found once, of the explained row's unit
            and calendar month, with an issue of that month and the lead; the background rows are designed together
            with their unit's test set (the prediction-time normal table): the test rows' design must not change, the
            table must not change, the background and explained rows' own normals must equal the table bit for bit,
            and the NDVI lag values set to 0 must be exactly the missing ones. The adapter's predict() on that mixed
            set is S-EVAL's reference at the background rows; its test part may differ from the saved pre by about
            1e-16 (the same block effect), recorded as information only;
  S-ADD, S-EVAL, S-ZERO, S-RESID  in shapv1_rows.write (S-EVAL: our evaluator against the saved pre on every
            explained row and against the adapter's own predict() on every background row, 1e-9). These stops name
            the failed checks in FAILED.json's checks_passed (no gate field).
Exit codes: 0 done or skipped; 3 a gate; 1 a crash or a structural refusal (no human board, no or several BARDL
rivals, a player that is not an export column, a write outside the analysis folder); 2 argparse. After a finished or
skipped piece, a comparison of the same models root (compare/per_lead.json) that does not cover this piece (it does not
list it, or its done record was made from other rows) is logged as a REMINDER to run compare_shap.py again (logging
only).

SHAP, link space (identity: NDVI units). For row r of unit u (the adapter's predict, :336-349):
    f(r) = z0(r) + c_u + sum_j beta_uj Z_j(r),   Z_j = (F(D_j(r)) - mu_uj) / sd_uj,   F(v) = v if finite, else 0,
with D the 11 predictors of design() (NaN kept in the climate anomalies and the two 3-month means). Players: the nine
export columns the adapter reads (its own _col rule) plus 'normal' (the offset z0). Under B2 an explained row and its
background rows share the unit and the calendar month, so the NDVI-lag normals, the climate means and the coefficients
are the same for both and every term depends on its players only:
  - nine predictors depend on one player each: exact linear terms, the per-pair difference taken first;
  - each 3-month mean depends on its three lag players: its exact 3-player Shapley value per (x, b) pair, enumerated
    over the 8 coalitions under the adapter's missing-value rule (np.mean of the three, then F);
  - the offset goes to 'normal'; the intercept c_u to the base.
Variable level (the exact grouped game): each term goes whole to its variable.

Copied, never imported (file:line): rival_shap.py 28-34 (header and pins), 71-81 (env gate, adapted), 103-106 (--rows),
107-126 (explained and background joins, adapted), 187-200 (bit_check, verbatim), 218-229 (masks, adapted), 232-253
(finish: offset to normal, base, meta), 538-569 (identity, skip, done record, adapted); compare_shap.py 75-79
(link_key, a self-check); the human tool's slim.py 347, 352-368, 418-432 (read order and hash check, re-done without
importing the tool, which needs its production config and lock token); the engine's treeroute/layer/links.py 248-255
(the clip rule); rivals_human/tests/test_h19_ndvi.py 27-58 (the minimal context).
"""
import argparse
import datetime
import glob
import hashlib
import importlib.util
import json
import os
import sys
import time
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shapv1_common as C  # noqa: E402

PINS = 8
C.pin_threads(PINS)                            # the human board's constants.threads (8), before numpy loads
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

import shapv1_rows as RW  # noqa: E402
import shapv1_treeshap as TS  # noqa: E402

HELPERS = ("bardl_shap.py", "shapv1_rows.py", "shapv1_common.py", "shapv1_treeshap.py")
FORMAT = "human-bardl-params/1"
BOARD_FORMAT = "human-board/1"
SLIM_FORMAT = "human-slim/1"
KEY = ["unit", "time", "issue"]
OMEGA = (1.0 / 3.0, 1.0 / 6.0, 1.0 / 3.0)      # 3-player Shapley weights |S|! (2 - |S|)! / 3! by coalition size
EXIT_GATE = 3

# Informational evidence, never a gate: the human tool's code hash recipe (rivals_human/common.py:115-125,
# config.py:467-472) over today's files gives the board's tool_code_sha256 when the one file changed after the board is
# taken from its kept copy and the five adapters created after the board are left out (both lists from file dates).
BOARD_CODE_SUBSTITUTED = {"rivals_human/maps.py": "_moved/20261025T194657Z_partB_baseline/rivals_human/maps.py"}
BOARD_CODE_EXCLUDED = ("adapters/fire_enso.py", "adapters/fire_geff.py", "adapters/fire_lag_common.py",
                       "adapters/fire_refs_prep.py", "adapters/fire_turco.py")


def parse(argv=None):
    ap = argparse.ArgumentParser(description="BARDL loader: exactness and exact SHAP (PROTOCOL.md 4.2, 5, 9)")
    ap.add_argument("--problem", required=True, choices=sorted(C.PROBLEMS))
    ap.add_argument("--lead", type=int, required=True)
    ap.add_argument("--rival", default=None, help="the rival id (default: the single pick with BARDL params)")
    ap.add_argument("--n", type=int, default=C.DEFAULT_N, help="the registered sample size (checked: S-SAMPLE)")
    ap.add_argument("--sample-root", default=None)
    ap.add_argument("--register", default=None)
    ap.add_argument("--rows", type=int, default=0, help="smoke: explain only the first K sample rows")
    ap.add_argument("--out-root", default=None, help="the models root; outputs go to <out-root>/rival_<id>/")
    ap.add_argument("--log-dir", default=None, help="default logs/; a smoke passes a folder of its own")
    ap.add_argument("--exactness-only", action="store_true", help="S-ENV and S-EXACT only (no sample needed)")
    return ap.parse_args(argv)


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


def uniq(cols):
    out = []
    for c in cols:
        if c not in out:
            out.append(c)
    return out


def F(v):
    """The adapter's missing-value rule at prediction (:336-338): a non-finite design value is 0."""
    v = np.asarray(v, np.float64)
    return np.where(np.isfinite(v), v, 0.0)


def same_bits(a, b):
    """Two arrays equal bit for bit, NaN equal to NaN."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    if a.shape != b.shape:
        return False
    na, nb = np.isnan(a), np.isnan(b)
    return bool(np.array_equal(na, nb) and np.array_equal(a[~na].view(np.int64), b[~nb].view(np.int64)))


def bit_equal_rows(a, b):
    """Per element: both finite and bit-equal."""
    a = np.ascontiguousarray(a, np.float64)
    b = np.ascontiguousarray(b, np.float64)
    return np.isfinite(a) & np.isfinite(b) & (a.view(np.int64) == b.view(np.int64))


def bit_check(pre, ref):
    """Bit identity on every row: NaN in the same places, +-inf in the same places with the same sign, every
    finite value equal."""
    pre, ref = np.asarray(pre, np.float64), np.asarray(ref, np.float64)
    same_nan = bool(np.array_equal(np.isnan(pre), np.isnan(ref)))
    inf_ok = bool(np.array_equal(np.isinf(ref), np.isinf(pre)) and np.array_equal(pre[np.isinf(ref)],
                                                                                    ref[np.isinf(ref)]))
    fin = np.isfinite(ref) & np.isfinite(pre)
    d = np.abs(pre[fin] - ref[fin])
    return {"rows": int(ref.size), "rows_finite": int(fin.sum()), "same_nan": same_nan, "inf_equal": inf_ok,
            "rows_inf": int(np.isinf(ref).sum()), "bit_equal_rows": int((pre[fin] == ref[fin]).sum()),
            "max_abs_diff": float(d.max()) if d.size else 0.0,
            "pass": bool(same_nan and inf_ok and np.array_equal(pre[fin], ref[fin])
                         and np.array_equal(np.isfinite(ref), np.isfinite(pre)))}


def legal_clip(pre, legal):
    """The engine's legal-range clip (treeroute/layer/links.py:248-255): a finite value below the minimum becomes the
    minimum, above the maximum the maximum, everything else is unchanged (an open bound is +-inf)."""
    low = -np.inf if legal[0] is None else float(legal[0])
    high = np.inf if legal[1] is None else float(legal[1])
    v = np.array(pre, dtype=np.float64, copy=True)
    finite = ~np.isnan(v)
    below = finite & (v < low)
    above = finite & (v > high)
    v[below] = low
    v[above] = high
    return v


def link_key(meta):
    """compare_shap.py:75-79 (copied: compare pins 1 thread and cannot be imported here), a self-check."""
    c = meta.get("c")
    ub = meta.get("ub")
    return "%s|c=%s|ub=%s" % (meta.get("link"), "-" if c is None else "%.12g" % float(c),
                              "-" if ub is None else "%.12g" % float(ub))


def blas_threads():
    """The live thread pools (informational): only the API, the library prefix and the thread count (no path)."""
    try:
        import threadpoolctl
        return [{"internal_api": d.get("internal_api"), "prefix": d.get("prefix"), "num_threads": d.get("num_threads")}
                for d in threadpoolctl.threadpool_info()]
    except Exception as exc:                          # informational only
        return [{"error": type(exc).__name__}]


# ---------------------------------------------------------------------------------------------------------------
# gate stops
class Stopper(object):
    """Gate stops of one model folder: the folder's own done record is removed first, then FAILED.json names the
    gate; exit 3."""

    def __init__(self, out, model, problem, lead, log):
        self.out, self.model, self.problem, self.lead, self.log = out, model, problem, int(lead), log

    def drop_done(self, why):
        done = os.path.join(self.out, "rows.parquet.done.json")
        if os.path.isfile(done):
            os.remove(C.assert_writable(done))
            self.log("%s: removed this folder's old done record (%s)" % (self.model, why))
            return True
        return False

    def stop(self, gate, detail, extra=None):
        C.makedirs(self.out)
        self.drop_done("a stop at %s leaves no finished piece" % gate)
        rec = {"model": self.model, "problem": self.problem, "lead": self.lead, "gate": gate, "detail": detail,
               "pass": False, "finished": datetime.datetime.now().isoformat(timespec="seconds")}
        if extra:
            rec.update(extra)
        C.write_json(os.path.join(self.out, "FAILED.json"), rec)
        self.log("STOP %s: %s: %s" % (gate, self.model, detail))
        raise SystemExit(EXIT_GATE)


def env_gate(hb):
    """S-ENV (rival_shap.py:71-81, adapted): the human board's library versions (an empty list fails) and its thread
    count (constants.threads, which must be 8) against the installed versions and the pins. Returns (ok, record)."""
    have = C.versions()
    want = hb.get("versions") or {}
    diff = {k: [v, have.get(k)] for k, v in want.items() if have.get(k) != v}
    threads = (hb.get("constants") or {}).get("threads")
    pins = {v: os.environ.get(v) for v in C.PIN_VARS[:4]}
    bad_pins = {k: v for k, v in pins.items() if v != str(threads)}
    try:
        tint = int(threads)
    except (TypeError, ValueError):
        tint = None
    ok = bool(want) and not diff and not bad_pins and tint == PINS
    return ok, {"versions_diff": diff, "versions_missing": not bool(want), "pins": pins, "board_threads": threads,
                "pins_required": PINS, "pass": bool(ok)}


def s_env(st, hb, log):
    ok, rec = env_gate(hb)
    if not ok:
        st.stop("S-ENV", "the environment is not the human board's (versions %s%s; pins %s; board threads %s)"
                % (rec["versions_diff"], " (the board lists no versions)" if rec["versions_missing"] else "",
                   rec["pins"], rec["board_threads"]), {"env": rec})
    log("S-ENV: library versions and thread pins equal the human board's (%d threads)" % PINS)
    return rec


def write_exactness(st, rec):
    """exactness.json is always written at S-EXACT; a failed record stops (FAILED.json, exit 3), no SHAP value."""
    C.write_json(os.path.join(st.out, "exactness.json"), rec)
    if not rec.get("pass"):
        keys = ("stage", "rows", "rows_finite", "bit_equal_rows", "max_abs_diff", "same_nan", "inf_equal",
                "keys_only_saved", "keys_only_rebuilt", "refusal", "inputs_pass", "slim_file", "inputs_failed")
        summary = {k: rec[k] for k in keys if k in rec}
        if isinstance(rec.get("raw"), dict):
            summary["raw"] = {k: rec["raw"].get(k) for k in ("bit_equal_rows", "rows_finite", "max_abs_diff", "pass")}
        st.stop("S-EXACT", rec.get("detail") or "BARDL does not reproduce its saved predictions: no SHAP value",
                {"exactness": summary})


# ---------------------------------------------------------------------------------------------------------------
# the board's records (no data file)
def board(problem, lead, rival_id, log):
    """Paths, parsed records and SHA-256 of the human board's files (records only; refuses a missing board or rival)."""
    P = C.PROBLEMS[problem]
    human = P.get("human")
    if not human:
        refuse(log, "problem %s has no published-rival (human) board" % problem)
    L = int(lead)
    bd = SimpleNamespace(P=P, human=human, lead=L, ldir=os.path.join(human, "lead_%d" % L), sha={}, path={},
                         slim_dir=os.path.join(human, "slim", "lead_%d" % L))

    def rec(name, path, as_json=True):
        if not os.path.isfile(path):
            refuse(log, "%s does not exist" % path)
        data, sha = read_bytes(path)
        bd.sha[name], bd.path[name] = sha, path
        return json.loads(data.decode("utf-8")) if as_json else data
    bd.hb = rec("human_board.json", os.path.join(human, "human_board.json"))
    bd.picks = rec("human_picks.json", os.path.join(human, "human_picks.json"))
    found = {}
    for rid in sorted(bd.picks.get("picks") or {}):
        if rival_id is not None and rid != rival_id:
            continue
        mp = os.path.join(bd.ldir, "map_%s.json" % rid)
        if not os.path.isfile(mp):
            continue
        data, sha = read_bytes(mp)
        m = json.loads(data.decode("utf-8"))
        if (m.get("params") or {}).get("format") == FORMAT:
            found[rid] = (m, sha, mp)
    if len(found) != 1:
        refuse(log, "%s pick with %s params at lead %d in %s (%s)" % ("no" if not found else "more than one", FORMAT,
                                                                       L, bd.ldir, sorted(found) or rival_id))
    bd.rid = sorted(found)[0]
    bd.map, bd.sha["map"], bd.path["map"] = found[bd.rid]
    bd.done = rec("done", os.path.join(bd.ldir, "done_%s.json" % bd.rid))
    bd.preds_bytes = rec("preds", os.path.join(bd.ldir, "preds_%s.parquet" % bd.rid), as_json=False)
    bd.coverage_bytes = rec("coverage", os.path.join(bd.ldir, "coverage_%s.parquet" % bd.rid), as_json=False)
    bd.registry_bytes = rec("registry", str((bd.hb.get("registry") or {}).get("file") or "<no registry file>"),
                            as_json=False)
    bd.slim_bytes = rec("slim_manifest.json", os.path.join(bd.slim_dir, "slim_manifest.json"), as_json=False)
    bd.slim_manifest = json.loads(bd.slim_bytes.decode("utf-8"))
    rec("slim export_manifest.json", os.path.join(bd.slim_dir, "export_manifest.json"), as_json=False)
    bd.derived = rec("derived.json", os.path.join(P["run"], "derived.json"))
    bd.export_manifest = rec("export_manifest.json", os.path.join(P["export"], "lead_%d" % L, "export_manifest.json"))
    bd.cb = rec("board.json", os.path.join(P["board"], "board.json"))
    return bd


def registry_rival(bd, log):
    """The registry's entry of the rival (yaml.safe_load of plain data). Called only after the bytes' SHA-256 equals
    the human board's record (run(): checked before any parse, before the adapter it names is read)."""
    import yaml
    reg = yaml.safe_load(bd.registry_bytes.decode("utf-8")) or {}
    hits = [r for r in (reg.get("rivals") or []) if str(r.get("id")) == bd.rid]
    if len(hits) != 1:
        refuse(log, "the registry %s holds %d entries for %s" % (bd.path["registry"], len(hits), bd.rid))
    return hits[0]


def adapter_file(bd, rival, log):
    """(path, bytes, SHA-256) of the rival's runner adapters.<module> next to the registry folder."""
    runner = str(rival.get("runner") or "")
    parts = runner.split(".")
    if len(parts) != 2 or parts[0] != "adapters":
        refuse(log, "rival %s: runner %r is not adapters.<module>" % (bd.rid, runner))
    path = os.path.normpath(os.path.join(os.path.dirname(bd.path["registry"]), os.pardir, "adapters",
                                         parts[1] + ".py"))
    if not os.path.isfile(path):
        refuse(log, "the adapter %s does not exist" % path)
    data, sha = read_bytes(path)
    return path, data, sha


def load_adapter(path, data):
    """The adapter module, executed from the bytes whose SHA-256 was recorded (no package lookup, so nothing can
    shadow it; no bytecode is written)."""
    spec = importlib.util.spec_from_loader("shapv1_bardl_adapter", loader=None, origin=path)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = path
    exec(compile(data, path, "exec"), mod.__dict__)
    return mod


def board_code_reproduced(adapter_path, recorded):
    """Informational (never a gate): the human tool's own code hash recipe over today's files, with the one file
    changed after the board taken from its kept copy and the adapters created after the board left out. Equal to the
    board's tool_code_sha256: the adapter's bytes are the board's."""
    try:
        human = os.path.dirname(os.path.dirname(os.path.abspath(adapter_path)))
        build = os.path.dirname(human)
        files = sorted(glob.glob(os.path.join(human, "rivals_human", "*.py")))
        files += sorted(glob.glob(os.path.join(human, "adapters", "*.py")))
        parts = []
        for p in files:
            rel = "%s/%s" % (os.path.basename(os.path.dirname(p)), os.path.basename(p))
            if rel in BOARD_CODE_EXCLUDED:
                continue
            src = os.path.join(build, *BOARD_CODE_SUBSTITUTED[rel].split("/")) if rel in BOARD_CODE_SUBSTITUTED else p
            parts.append([rel, C.sha256_file(src)])
        text = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        sha = hashlib.sha256(text.encode("ascii")).hexdigest()
        return {"recipe": "rivals_human tool_code_sha (common.py:115-125, config.py:467-472)", "files": len(parts),
                "substituted": dict(BOARD_CODE_SUBSTITUTED), "excluded": list(BOARD_CODE_EXCLUDED), "sha256": sha,
                "recorded": recorded, "equal": bool(sha == recorded), "gate": False}
    except OSError as exc:
        return {"error": "%s: %s" % (type(exc).__name__, exc), "equal": False, "gate": False}


def check_records(bd, AD, rival, params, spy, offset, preds, cov):
    """S-EXACT (inputs): every record check of the board, the slim copy, the run, the export and the common board.
    Returns (ok, {check: record}); a hash record is {sha256, recorded, equal}, any other {value, expected, equal}."""
    hb, picks, done, sm = bd.hb, bd.picks, bd.done, bd.slim_manifest
    L = bd.lead
    R = {}

    def eq(name, value, expected):
        R[name] = {"value": value, "expected": expected, "equal": bool(value == expected)}

    def sha(name, value, recorded):
        R[name] = {"sha256": value, "recorded": recorded, "equal": bool(recorded is not None and value == recorded)}
    run = hb.get("run") or {}
    pk = (picks.get("picks") or {}).get(bd.rid) or {}
    plead = (pk.get("leads") or {}).get(str(L)) or {}
    sha("human_board.json", bd.sha["human_board.json"], picks.get("board_json_sha256"))
    eq("human_board.format", hb.get("format"), BOARD_FORMAT)
    eq("human_board.dry", hb.get("dry"), False)
    eq("human_picks.run_fingerprint", picks.get("run_fingerprint"), run.get("fingerprint"))
    eq("pick.status", pk.get("status"), "ok")
    R["pick.tier"] = {"value": plead.get("tier"), "expected": "a tier other than none",
                      "equal": plead.get("tier") not in (None, "none")}
    eq("done.status", done.get("status"), "ok")
    eq("done.lead", done.get("lead"), L)
    eq("done.rival", done.get("rival"), bd.rid)
    eq("done.params_file", (done.get("info") or {}).get("params_file"), "map_%s.json" % bd.rid)
    sha("preds_%s.parquet" % bd.rid, bd.sha["preds"], done.get("preds_sha256"))
    sha("coverage_%s.parquet" % bd.rid, bd.sha["coverage"], (plead.get("coverage") or {}).get("sha256"))
    same = len(cov) == len(preds)
    if same:
        for k in ("unit", "group"):
            same = same and np.array_equal(cov[k].astype(str).to_numpy(), preds[k].astype(str).to_numpy())
        for k in ("time", "issue", "lead"):
            same = same and np.array_equal(cov[k].to_numpy(np.int64), preds[k].to_numpy(np.int64))
        same = same and np.array_equal(cov["covered"].to_numpy(bool), preds["covered"].to_numpy(bool))
    eq("coverage mask = the preds' keys and covered column", bool(same), True)
    eq("map.method", bd.map.get("method"), rival.get("runner"))
    eq("map.params.format", params.get("format"), FORMAT)
    eq("adapter.PARAMS_FORMAT", AD.PARAMS_FORMAT, FORMAT)
    eq("map.params.adapter", params.get("adapter"), AD.ADAPTER_FORMAT)
    eq("map.params.rival", params.get("rival"), bd.rid)
    eq("map.params.lead", params.get("lead"), L)
    eq("map.params.fit_set", params.get("fit_set"), "refit")
    eq("map.params.steps_per_year (derived R17)", params.get("steps_per_year"), spy)
    eq("map.params.start_offset_steps (derived R17)", params.get("start_offset_steps"), offset)
    R["map_%s.json" % bd.rid] = {"sha256": bd.sha["map"], "recorded": None, "equal": True,
                                 "note": "not on the board; S-EXACT on every test row is its proof"}
    R["adapter"] = {"sha256": bd.sha["adapter"], "recorded": None, "equal": True,
                    "note": "in the board's tool code hash (board_code_reproduced, informational)"}
    sha("registry", bd.sha["registry"], (hb.get("registry") or {}).get("registry"))
    slim_rec = (hb.get("slim") or {}).get(str(L)) or {}
    sha("slim_manifest.json", bd.sha["slim_manifest.json"], slim_rec.get("manifest_sha256"))
    eq("slim_manifest.json SHA-256 in the picks", ((picks.get("slim") or {}).get(str(L)) or {}).get("manifest_sha256"),
       slim_rec.get("manifest_sha256"))
    eq("slim.format", sm.get("format"), SLIM_FORMAT)
    eq("slim.run_fingerprint", (sm.get("run") or {}).get("fingerprint"), run.get("fingerprint"))
    eq("slim.lead", sm.get("lead"), L)
    eq("slim.links", list(sm.get("links") or []), list(run.get("links") or []))
    eq("slim.legal", list(sm.get("legal") or []), list(run.get("legal") or []))
    eq("slim.fit_cut", (sm.get("cuts") or {}).get("fit_cut"), ((run.get("cuts") or {}).get(str(L)) or {}).get("fit_cut"))
    eq("slim.season", sm.get("season"), run.get("season"))
    eq("slim.offset_steps", sm.get("offset_steps"), run.get("offset_steps"))
    sha("derived.json", bd.sha["derived.json"], (run.get("file_sha256") or {}).get("derived.json"))
    sha("export_manifest.json (the common export's lead manifest)", bd.sha["export_manifest.json"],
        sm.get("source_export_manifest_sha256"))
    sha("export_manifest.json (the slim copy's kept copy)", bd.sha["slim export_manifest.json"],
        (sm.get("export_manifest") or {}).get("sha256"))
    ex = {(str(f.get("part")), str(f.get("group"))): str(f.get("sha256"))
          for f in (bd.export_manifest.get("files") or []) if "group" in f}
    n_eq = n_ne = n_miss = 0
    for f in sm.get("files") or []:
        if f.get("part") not in ("test", "train"):
            continue
        k = (str(f["part"]), str(f.get("group")))
        if k not in ex:
            n_miss += 1
        elif ex[k] == str(f.get("source_sha256")):
            n_eq += 1
        else:
            n_ne += 1
    R["provenance: recorded source SHA-256 of the slim test and train files = the export's"] = {
        "files_equal": n_eq, "files_different": n_ne, "files_missing": n_miss,
        "equal": bool(n_eq > 0 and n_ne == 0 and n_miss == 0)}
    cbr = bd.cb.get("run") or {}
    sha("board.json (the common board)", bd.sha["board.json"], (hb.get("common_board") or {}).get("sha256"))
    eq("common_board.run.fingerprint", cbr.get("fingerprint"), run.get("fingerprint"))
    eq("common_board.run.c", (cbr.get("c") or {}).get(str(L)), (run.get("c") or {}).get(str(L)))
    eq("common_board.run.ub", cbr.get("ub"), run.get("ub"))
    eq("common_board.run.links", list(cbr.get("links") or []), list(run.get("links") or []))
    eq("common_board.run.legal", list(cbr.get("legal") or []), list(run.get("legal") or []))
    eq("adapter.LINK is a link of the run", AD.LINK in list(run.get("links") or []), True)
    return all(v["equal"] for v in R.values()), R


# ---------------------------------------------------------------------------------------------------------------
# the slim copy (the tool's read order and hash check, re-done)
class InputMismatch(Exception):
    """A slim file whose bytes are not its manifest's (stop rule S-EXACT, inputs)."""


class Slim(object):
    """The slim copy of one lead: manifest entries by part and stem; every read hash-checks the file's bytes against
    its manifest entry first, then parses those same bytes (slim.py:347, 352-368, 418-432)."""

    def __init__(self, folder, manifest):
        self.dir = folder
        self.manifest = manifest
        self.files = {}
        for f in manifest["files"]:
            self.files.setdefault(str(f["part"]), {})[str(f["stem"])] = f
        cols = manifest["columns"]
        self.history = list(cols["history"])
        self.extras = list(cols["extras"])
        self.files_read = 0
        self.bytes_read = 0

    def entries(self, part):
        return [self.files[part][s] for s in sorted(self.files.get(part, {}))]

    def read(self, entry, columns):
        p = os.path.join(self.dir, *str(entry["path"]).split("/"))
        data, sha = read_bytes(p)
        if sha != str(entry["sha256"]):
            raise InputMismatch("slim file %s has SHA-256 %s; its manifest lists %s" % (entry["path"], sha[:16],
                                                                                         str(entry["sha256"])[:16]))
        self.files_read += 1
        self.bytes_read += len(data)
        return pq.read_table(pa.BufferReader(data), columns=list(columns)).to_pandas()


def read_test(slim, cols):
    """Every slim test file, sorted by stem, rows in file order (the tool's read_set('test'))."""
    return pd.concat([slim.read(e, cols) for e in slim.entries("test")], ignore_index=True)


def slim_set(frame, hist_cols, extra_cols, link, keys_cols):
    """The SlimSet the tool hands a runner (keys, normal {link: nfit__<link>}, history, extras; never y)."""
    fr = frame.reset_index(drop=True)
    return SimpleNamespace(keys=fr[list(keys_cols)].reset_index(drop=True),
                           normal={link: fr["nfit__" + link].to_numpy(np.float64)},
                           history=fr[list(hist_cols)].reset_index(drop=True),
                           extras=fr[list(extra_cols)].reset_index(drop=True), y=None)


class MiniCtx(object):
    """The minimal runner context of the tool's own test (rivals_human/tests/test_h19_ndvi.py:27-58): run.derived (R17),
    features(set) and log. No fit_labels (predict never asks for labels) and no t2_step (predict skips that optional
    cross-check, adapter :170-173)."""

    def __init__(self, run, sets, log=None):
        self.run, self.sets, self.lines, self._log = run, sets, [], log

    def features(self, name):
        return self.sets[name]

    def log(self, message):
        self.lines.append(str(message))
        if self._log is not None:
            self._log("adapter| %s" % message)


# ---------------------------------------------------------------------------------------------------------------
# S-EXACT (bits)
def exactness(AD, rival, params, run, T, preds, legal, lead, hist_cols, extra_cols, link, log=None):
    """The adapter's own predict() on every test row T, masked by the locked coverage (board.py:944) and clipped by
    the engine's legal rule (board.py:1050-1051), against the saved pre and raw, bit for bit on every row; the key
    sets must be equal. T must be the whole slim test set in the tool's read order (read_test): predict() sums each
    unit's rows by one BLAS dot, and a row's result can differ in the last bit when its block differs, so a subset is
    never a bit-exact check. Pure apart from the log. Returns (record, the saved pre in T's order or None)."""
    t0 = time.time()
    ctx = MiniCtx(run, {"test": slim_set(T, hist_cols, extra_cols, link, AD.KEYS)}, log)
    rec = {"rows_test_set": int(len(T))}
    try:
        out = AD.predict(ctx, dict(rival), int(lead), params, "test")
    except AD.BardlRefusal as exc:
        rec.update({"pass": False, "refusal": str(exc), "detail": "the adapter's predict() refused: %s" % exc,
                    "seconds": round(time.time() - t0, 1)})
        return rec, None
    new = pd.DataFrame({"unit": out["unit"].astype(str).to_numpy(), "time": out["time"].to_numpy(np.int64),
                        "issue": out["issue"].to_numpy(np.int64), "group_new": out["group"].astype(str).to_numpy(),
                        "pre_new": out["pre"].to_numpy(np.float64), "_t": np.arange(len(out), dtype=np.int64)})
    sv = pd.DataFrame({"unit": preds["unit"].astype(str).to_numpy(), "time": preds["time"].to_numpy(np.int64),
                       "issue": preds["issue"].to_numpy(np.int64), "group_saved": preds["group"].astype(str).to_numpy(),
                       "lead_saved": preds["lead"].to_numpy(np.int64), "covered": preds["covered"].to_numpy(bool),
                       "pre": preds["pre"].to_numpy(np.float64), "raw": preds["raw"].to_numpy(np.float64)})
    dup_new, dup_saved = int(new.duplicated(KEY).sum()), int(sv.duplicated(KEY).sum())
    if dup_new or dup_saved:
        rec.update({"pass": False, "duplicate_keys_rebuilt": dup_new, "duplicate_keys_saved": dup_saved,
                    "detail": "a (unit, time, issue) key appears twice", "seconds": round(time.time() - t0, 1)})
        return rec, None
    j = sv.merge(new, on=KEY, how="outer", indicator=True)
    only_saved = int((j["_merge"] == "left_only").sum())
    only_new = int((j["_merge"] == "right_only").sum())
    jb = j[j["_merge"] == "both"].reset_index(drop=True)
    cov = jb["covered"].to_numpy(bool)
    pre_new = np.where(cov, jb["pre_new"].to_numpy(np.float64), np.nan)
    raw_new = np.full(len(jb), np.nan)
    raw_new[cov] = legal_clip(pre_new[cov], legal)
    bc = bit_check(pre_new, jb["pre"].to_numpy(np.float64))
    rc = bit_check(raw_new, jb["raw"].to_numpy(np.float64))
    groups_equal = bool((jb["group_new"].to_numpy() == jb["group_saved"].to_numpy()).all())
    lead_equal = bool((jb["lead_saved"].to_numpy(np.int64) == int(lead)).all())
    rec.update(bc)
    rec.update({"raw": rc, "rows_checked": int(len(jb)), "keys_only_saved": only_saved, "keys_only_rebuilt": only_new,
                "covered_rows": int(cov.sum()), "groups_equal": groups_equal, "lead_equal": lead_equal,
                "units": int(jb["unit"].nunique()), "legal": list(legal),
                "adapter_message": ctx.lines[-1] if ctx.lines else None, "seconds": round(time.time() - t0, 1)})
    rec["pass"] = bool(bc["pass"] and rc["pass"] and only_saved == 0 and only_new == 0 and groups_equal and lead_equal)
    if not rec["pass"]:
        rec["detail"] = ("BARDL does not reproduce its saved predictions (pre bit-equal %d of %d, raw %d of %d, keys "
                         "only saved %d, only rebuilt %d): no SHAP value" % (bc["bit_equal_rows"], bc["rows_finite"],
                                                                            rc["bit_equal_rows"], rc["rows_finite"],
                                                                            only_saved, only_new))
    saved_T = np.full(len(T), np.nan)
    saved_T[jb["_t"].to_numpy(np.float64).astype(np.int64)] = jb["pre"].to_numpy(np.float64)
    return rec, saved_T


def normal_table_stat(AD, T, link, spy):
    """Informational: test rows whose own normal equals their unit's prediction-time table at their calendar month."""
    u = T["unit"].astype(str).to_numpy()
    k = AD.season_key(T["time"].to_numpy(np.int64), spy)
    z = T["nfit__" + link].to_numpy(np.float64)
    try:
        nt = AD.unit_normals(u, k, z)
    except AD.BardlRefusal as exc:                    # informational only (predict() checked its own rows)
        return {"test_rows": int(len(T)), "error": str(exc)}
    tab = np.array([nt.get((uu, int(kk)), np.nan) for uu, kk in zip(u, k)], np.float64)
    return {"test_rows": int(len(T)), "rows_whose_normal_equals_the_table": int(bit_equal_rows(z, tab).sum())}


# ---------------------------------------------------------------------------------------------------------------
# players and terms (by the adapter's own rules: no hand list)
def term_layout(AD, opt, params, hist_cols, extra_cols, export_x, log):
    """(players, single, means). players: for each registry option column in design()'s order (history, then each
    climate variable's three columns), the slim column the adapter's _col() reads (:120-126: the first of name,
    x__name, h__name), which must be an export x__ column; then 'normal'. single: (design column, player) of the
    one-player predictors; means: (design column, its three lag design columns, their players) (:222-246)."""
    names = AD.feature_names(opt)
    if list(params.get("features") or []) != list(names):
        refuse(log, "the map's features %s are not the adapter's %s" % (params.get("features"), names))

    def col_of(cols, name):
        for c in (name, "x__" + name, "h__" + name):
            if c in cols:
                return c
        refuse(log, "the slim copy has no column for %s" % name)
    players, single, means = [], [], []
    d = 0
    for k in range(AD.N_LAGS):
        if names[d] != "ndvi_anom_lag%d" % (k + 1):
            refuse(log, "design column %d is %s, not ndvi_anom_lag%d" % (d, names[d], k + 1))
        players.append(col_of(hist_cols, opt["history"][k]))
        single.append((d, len(players) - 1))
        d += 1
    lags = {}
    for var, cols in opt["climate"].items():
        lags[var] = []
        for l, name in zip(AD.CLIMATE_LAGS, cols):
            if names[d] != "%s_anom_l%d" % (var, l):
                refuse(log, "design column %d is %s, not %s_anom_l%d" % (d, names[d], var, l))
            players.append(col_of(extra_cols, name))
            single.append((d, len(players) - 1))
            lags[var].append((d, len(players) - 1))
            d += 1
    for var in opt["climate"]:
        if names[d] != "%s_anom_mean3" % var or len(lags[var]) != 3:
            refuse(log, "design column %d is %s, not %s_anom_mean3" % (d, names[d], var))
        means.append((d, [c for c, _ in lags[var]], [q for _, q in lags[var]]))
        d += 1
    if d != len(names) or len(set(players)) != len(players):
        refuse(log, "the design's %d columns do not map onto %d distinct players" % (len(names), len(players)))
    bad = [p for p in players if p not in set(export_x)]
    if bad:
        refuse(log, "players %s are not x__ columns of the common export" % bad)
    return players + ["normal"], single, means


def unit_arrays(params, units, nfeat):
    """Per row: the unit's coefficients, standardisation and intercept; a fallback unit (fewer than min_fit_rows
    complete rows) predicts its normal: coef 0, mu 0, sd 1, intercept 0 (f = z0)."""
    U = params["units"]
    n = len(units)
    out = {"coef": np.zeros((n, nfeat)), "mu": np.zeros((n, nfeat)), "sd": np.ones((n, nfeat)), "icpt": np.zeros(n),
           "fallback": np.zeros(n, bool)}
    cache = {}
    for i, u in enumerate(units):
        u = str(u)
        if u not in cache:
            m = U.get(u)
            if m is None:
                raise KeyError("unit %s has no BARDL parameters" % u)
            cache[u] = None if m.get("fallback") else (
                np.asarray(m["coef"], np.float64), np.asarray(m["mu"], np.float64), np.asarray(m["sd"], np.float64),
                float(m["intercept"]))
        e = cache[u]
        if e is None:
            out["fallback"][i] = True
            continue
        out["coef"][i], out["mu"][i], out["sd"][i], out["icpt"][i] = e
    return out


def evaluate(D, z0, U):
    """Our evaluator: f = z0 + (c + sum_j coef_j Z_j), Z_j = (F(D_j) - mu_j) / sd_j, summed in j order (the adapter
    sums the same terms by a BLAS dot, so S-EVAL compares within 1e-9)."""
    D = np.asarray(D, np.float64)
    Z = (F(D) - U["mu"]) / U["sd"]
    a = U["icpt"].copy()
    for j in range(D.shape[1]):
        a = a + U["coef"][:, j] * Z[:, j]
    return np.asarray(z0, np.float64) + a


# ---------------------------------------------------------------------------------------------------------------
# background (S-BG)
def explained_positions(S, T, saved_T, st):
    """S-SAMPLE: every sample row is exactly one test row of its group with a finite saved prediction."""
    if T.duplicated(["unit", "time"]).any():
        st.stop("S-SAMPLE", "the slim test set holds a (unit, time) key twice")
    pos = pd.DataFrame({"unit": T["unit"].astype(str).to_numpy(), "time": T["time"].to_numpy(np.int64),
                        "p": np.arange(len(T)), "g": T["group"].astype(str).to_numpy()})
    j = pd.DataFrame({"unit": S["unit"].astype(str).to_numpy(), "time": S["time"].to_numpy(np.int64),
                      "group": S["group"].astype(str).to_numpy()}).merge(pos, on=["unit", "time"], how="left",
                                                                         validate="many_to_one")
    miss = int(j["p"].isna().sum())
    if miss:
        st.stop("S-SAMPLE", "%d sample rows are not test rows of the slim copy" % miss)
    epos = j["p"].to_numpy(np.float64).astype(np.int64)
    bad_g = int((j["group"].to_numpy() != j["g"].to_numpy()).sum())
    if bad_g:
        st.stop("S-SAMPLE", "%d sample rows name another group than their test row" % bad_g)
    nonfin = int((~np.isfinite(saved_T[epos])).sum())
    if nonfin:
        st.stop("S-SAMPLE", "%d sample rows have no finite saved BARDL prediction" % nonfin)
    return epos


def background_keys(S, B, T, epos, spy, AD, st):
    """S-BG invariants of the registered keys before any file is read: each key names an explained row, is of that
    row's unit and calendar month, and no explained row is without background. Returns the explained row of each key."""
    srow = {int(r): i for i, r in enumerate(S["row"].to_numpy(np.int64))}
    bi = np.array([srow.get(int(r), -1) for r in B["row"].to_numpy(np.int64)], np.int64)
    if (bi < 0).any():
        st.stop("S-BG", "%d background keys name no explained row" % int((bi < 0).sum()))
    cnt = np.bincount(bi, minlength=len(S))
    if (cnt == 0).any():
        st.stop("S-BG", "%d explained rows have no background key" % int((cnt == 0).sum()))
    ue = T["unit"].astype(str).to_numpy()[epos][bi]
    if (ue != B["unit"].astype(str).to_numpy()).any():
        st.stop("S-BG", "%d background keys are of another unit than their explained row"
                % int((ue != B["unit"].astype(str).to_numpy()).sum()))
    te = T["time"].to_numpy(np.int64)[epos][bi]
    bad = AD.season_key(te, spy) != AD.season_key(B["time"].to_numpy(np.int64), spy)
    if bad.any():
        st.stop("S-BG", "%d background keys are of another calendar month than their explained row" % int(bad.sum()))
    return bi


def read_background(slim, S, B, cols, st):
    """The registered keys' rows: the refit rows (r_refit) of the slim train files of the sample's groups, each file
    hash-checked; every key found exactly once (S-BG otherwise). Returns (Kb: the distinct rows, q: Kb row of each
    registered key, in B's order)."""
    by_group = {}
    for e in slim.entries("train"):
        by_group.setdefault(str(e["group"]), []).append(e)
    want = set(zip(B["unit"].astype(str), B["time"].to_numpy(np.int64).tolist()))
    parts = []
    for g in sorted(set(S["group"].astype(str))):
        ents = by_group.get(g) or []
        if len(ents) != 1:
            st.stop("S-BG", "group %s has %d slim train files (one expected)" % (g, len(ents)))
        t = slim.read(ents[0], list(cols) + ["r_refit"])
        flag = t["r_refit"].to_numpy(bool)
        hit = np.fromiter(((u, int(tt)) in want for u, tt in zip(t["unit"].astype(str), t["time"].to_numpy(np.int64))),
                          bool, len(t)) & flag
        if hit.any():
            parts.append(t.loc[hit, list(cols)].reset_index(drop=True))
    Kb = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=list(cols))
    dup = int(Kb.duplicated(["unit", "time"]).sum()) if len(Kb) else 0
    if dup:
        st.stop("S-BG", "%d background keys appear more than once among the refit rows of the slim copy" % dup,
                {"duplicate_keys": dup})
    bpos = pd.DataFrame({"unit": Kb["unit"].astype(str).to_numpy(), "time": Kb["time"].to_numpy(np.int64),
                         "q": np.arange(len(Kb))})
    jb = pd.DataFrame({"row": B["row"].to_numpy(np.int64), "unit": B["unit"].astype(str).to_numpy(),
                       "time": B["time"].to_numpy(np.int64)}).merge(bpos, on=["unit", "time"], how="left",
                                                                    validate="many_to_one")
    miss = int(jb["q"].isna().sum())
    if miss:
        st.stop("S-BG", "%d registered background keys are not refit rows of the slim copy" % miss,
                {"keys_not_found": miss})
    return Kb, jb["q"].to_numpy(np.float64).astype(np.int64)


def background_design(AD, opt, params, run, rival, lead, spy, offset, T, X_test, kidx, epos, tpart, Kb, hist_cols,
                      extra_cols, link, saved_T, st, log=None):
    """The background rows as the model evaluates a scored row: design() on [the sampled units' whole test sets + the
    background rows] (design() builds its NDVI-lag normal table from the rows it is given; on background rows alone
    every lag anomaly would silently become 0). S-BG unless: the test rows' design is unchanged; the normal table is
    unchanged; every background and explained row's own normal equals the table bit for bit; the NDVI lag values set to
    0 are exactly the background rows' missing hist_last values. Returns (Db, the adapter's own predict() at every
    background row, record). The record's test-part difference against the saved pre is information only: in the
    mixed call each unit's block is longer, so it can be about 1e-16 rather than 0 (S-EXACT is the bit-exact check)."""
    t0 = time.time()
    cols = list(T.columns)
    Tp = T.iloc[tpart].reset_index(drop=True)
    nT = len(Tp)
    mix = pd.concat([Tp, Kb[cols]], ignore_index=True)
    ms = slim_set(mix, hist_cols, extra_cols, link, AD.KEYS)
    ts = slim_set(Tp, hist_cols, extra_cols, link, AD.KEYS)
    bs = slim_set(Kb[cols], hist_cols, extra_cols, link, AD.KEYS)
    cm = params["climate_means"]
    try:
        X_mix, _, cnt_mix = AD.design(ms.keys, ms.normal[link], ms.history, ms.extras, cm, opt, lead, spy, offset)
        _, _, cnt_tp = AD.design(ts.keys, ts.normal[link], ts.history, ts.extras, cm, opt, lead, spy, offset)
        _, _, cnt_alone = AD.design(bs.keys, bs.normal[link], bs.history, bs.extras, cm, opt, lead, spy, offset)
        sk = lambda t: AD.season_key(np.asarray(t, np.int64), spy)  # noqa: E731
        nt = AD.unit_normals(Tp["unit"].astype(str).to_numpy(), sk(Tp["time"]), Tp["nfit__" + link].to_numpy(np.float64))
        nm = AD.unit_normals(mix["unit"].astype(str).to_numpy(), sk(mix["time"]),
                             mix["nfit__" + link].to_numpy(np.float64))
    except AD.BardlRefusal as exc:
        st.stop("S-BG", "design() of the sampled units' test rows with their background rows refused: %s" % exc)
    same_test = same_bits(X_mix[:nT], X_test[kidx[tpart]])
    table_equal = bool(sorted(nt) == sorted(nm) and all(
        np.array([nt[k]], np.float64).view(np.int64)[0] == np.array([nm[k]], np.float64).view(np.int64)[0]
        for k in nt))

    def lookup(frame):
        return np.array([nt.get((u, int(k)), np.nan) for u, k in zip(frame["unit"].astype(str).to_numpy(),
                                                                       sk(frame["time"]))], np.float64)
    ok_b = bit_equal_rows(Kb["nfit__" + link].to_numpy(np.float64), lookup(Kb))
    Te = T.iloc[epos]
    ok_e = bit_equal_rows(Te["nfit__" + link].to_numpy(np.float64), lookup(Te))
    ok_t = bit_equal_rows(Tp["nfit__" + link].to_numpy(np.float64), lookup(Tp))
    hist_missing = 0
    for k in range(AD.N_LAGS):
        hist_missing += int((~np.isfinite(AD._col(bs.history, opt["history"][k]))).sum())
    lag_added = int(cnt_mix["ndvi_lag_values_missing_set_to_0"]) - int(cnt_tp["ndvi_lag_values_missing_set_to_0"])
    rec = {"test_rows_of_the_sampled_units": nT, "background_rows": int(len(Kb)), "test_part_design_unchanged": same_test,
           "normal_table_unchanged": table_equal, "background_rows_normal_bit_equal": int(ok_b.sum()),
           "explained_rows_normal_bit_equal": int(ok_e.sum()), "explained_rows": int(len(epos)),
           "test_part_rows_normal_bit_equal": int(ok_t.sum()),
           "lag_values_set_to_0_added_by_the_background_rows": lag_added,
           "hist_last_values_missing_on_the_background_rows": hist_missing,
           "lag_values_set_to_0_if_designed_alone (the hazard, not used)":
               int(cnt_alone["ndvi_lag_values_missing_set_to_0"])}
    problems = []
    if not same_test:
        problems.append("the test rows' design changed when the background rows were added")
    if not table_equal:
        problems.append("the unit normal table changed when the background rows were added")
    if not ok_b.all():
        problems.append("%d background rows' own normal is not their unit's prediction-time normal bit for bit"
                        % int((~ok_b).sum()))
    if not ok_e.all():
        problems.append("%d explained rows' own normal is not their unit's prediction-time normal bit for bit"
                        % int((~ok_e).sum()))
    if lag_added != hist_missing:
        problems.append("NDVI lag values set to 0 on the background rows: %d; missing hist_last values there: %d"
                        % (lag_added, hist_missing))
    if problems:
        st.stop("S-BG", "; ".join(problems), {"background_design": rec})
    try:
        pm = AD.predict(MiniCtx(run, {"test": ms}, None), dict(rival), int(lead), params, "test")
    except AD.BardlRefusal as exc:
        st.stop("S-BG", "predict() on the sampled units' test rows with their background rows refused: %s" % exc,
                {"background_design": rec})
    pre_mix = pm["pre"].to_numpy(np.float64)
    d = np.abs(pre_mix[:nT] - saved_T[tpart])
    rec["max_abs_test_part_predict_minus_saved_pre (informational)"] = float(np.nanmax(d)) if d.size else 0.0
    rec["seconds"] = round(time.time() - t0, 1)
    if log is not None:
        log("S-BG: %d background rows designed with %d test rows of their units: test design unchanged, normal table "
            "unchanged, normals bit-equal (background %d of %d, explained %d of %d), lag zeros %d = missing hist_last "
            "%d (designed alone: %d)" % (len(Kb), nT, int(ok_b.sum()), len(Kb), int(ok_e.sum()), len(epos), lag_added,
                                         hist_missing, rec["lag_values_set_to_0_if_designed_alone (the hazard, not "
                                                           "used)"]))
    return X_mix[nT:], pre_mix[nT:], rec


# ---------------------------------------------------------------------------------------------------------------
# the SHAP values (pure numpy)
def bardl_shap(De, Db, z0e, z0b, Ue, Ub, px, pb, pw, single, means, nplay, pvar, nvar, normal_p, normal_v):
    """Exact interventional SHAP of BARDL with per-row backgrounds (pairs px, pb, weights pw = 1/|B_i|), at the
    feature and the variable level. Each pair uses its explained row's unit arrays (the background row's unit is the
    same, S-BG). Returns (phi, phiv, base, eta, f at every background row, per-term variable-level contributions
    (n, 11), the per-row maximum |exact - per-lag linear split| of the mean terms, stats)."""
    De = np.asarray(De, np.float64)
    Db = np.asarray(Db, np.float64)
    z0e = np.asarray(z0e, np.float64)
    z0b = np.asarray(z0b, np.float64)
    n = De.shape[0]
    phi = np.zeros((n, nplay))
    phiv = np.zeros((n, nvar))
    terms = np.zeros((n, De.shape[1]))
    lin_gap = np.zeros(n)
    coef, mu, sd = Ue["coef"][px], Ue["mu"][px], Ue["sd"][px]

    def acc(v):
        return np.bincount(px, weights=v * pw, minlength=n)
    for d, p in single:                                   # one-player terms: per-pair difference first
        zx = (F(De[px, d]) - mu[:, d]) / sd[:, d]
        zb = (F(Db[pb, d]) - mu[:, d]) / sd[:, d]
        s = acc(coef[:, d] * (zx - zb))
        phi[:, p] += s
        phiv[:, pvar[p]] += s
        terms[:, d] += s
    stats = {}
    for d, lag_cols, qs in means:                         # three-player terms: 8 coalitions per pair
        if len(set(pvar[q] for q in qs)) != 1:
            raise RuntimeError("internal: the lag players of design column %d are in more than one variable" % d)
        hx = [De[px, c] for c in lag_cols]
        hb = [Db[pb, c] for c in lag_cols]
        v = []
        for S in range(8):
            M = np.mean(np.vstack([hx[l] if (S >> l) & 1 else hb[l] for l in range(3)]), axis=0)   # adapter :245
            if (S == 7 and not same_bits(M, De[px, d])) or (S == 0 and not same_bits(M, Db[pb, d])):
                raise RuntimeError("internal: design column %d is not the mean of its lag columns" % d)
            v.append(coef[:, d] * ((F(M) - mu[:, d]) / sd[:, d]))
        gap = 0.0
        for l in range(3):
            c = np.zeros(px.size)
            for S in range(8):
                if (S >> l) & 1:
                    continue
                c = c + OMEGA[bin(S).count("1")] * (v[S | (1 << l)] - v[S])
            s = acc(c)
            phi[:, qs[l]] += s
            lin = acc(coef[:, d] / (3.0 * sd[:, d]) * (F(hx[l]) - F(hb[l])))    # the per-lag linear split
            g = np.abs(s - lin)
            lin_gap = np.maximum(lin_gap, g)
            gap = max(gap, float(g.max()) if g.size else 0.0)
        s = acc(v[7] - v[0])
        phiv[:, pvar[qs[0]]] += s
        terms[:, d] += s
        miss = ~(np.isfinite(np.vstack(hx)).all(0) & np.isfinite(np.vstack(hb)).all(0))
        stats[int(d)] = {"pairs_with_a_missing_anomaly": int(miss.sum()),
                         "max_abs_exact_minus_per_lag_linear_split": gap}
    s = acc(z0e[px] - z0b[pb])                            # the offset: to 'normal' (rival_shap.py:237-239)
    phi[:, normal_p] += s
    phiv[:, normal_v] += s
    eta = evaluate(De, z0e, Ue)
    f_b = evaluate(Db, z0b, Ub)
    base = np.bincount(px, weights=f_b[pb] * pw, minlength=n)
    return phi, phiv, base, eta, f_b, terms, lin_gap, stats


def masks(Re, Rb, z0e, z0b, px, pb, poc, nplay, pocv, nvar, normal_p, normal_v):
    """S-ZERO masks (rival_shap.py:218-229, adapted) on the raw player values (NaN equal to NaN) at both levels;
    'normal' is constant where z0 is equal on every background row."""
    const = RW.constant_mask(Re, Rb, px, pb, poc, nplay)
    constv = RW.constant_mask(Re, Rb, px, pb, pocv, nvar)
    off_const = np.ones(Re.shape[0], bool)
    neq = np.asarray(z0e, np.float64)[px] != np.asarray(z0b, np.float64)[pb]
    off_const[np.unique(px[neq])] = False
    const[:, normal_p] &= off_const
    constv[:, normal_v] &= off_const
    return const, constv


# ---------------------------------------------------------------------------------------------------------------
def background_rows(AD, S, B, T, saved_T, slim, cols, spy, lead, st):
    """The explained rows and their background rows, one path for the owner's run and the smoke's pre-flight:
    S-SAMPLE (explained_positions); the registered keys' S-BG invariants (background_keys); the keys' refit rows of
    the slim copy (read_background: S-BG; a slim file whose bytes are not its manifest's stops S-EXACT); every
    background row's issue of its explained row's calendar month and of the lead (S-BG). Returns (epos, bi, Kb, q)."""
    epos = explained_positions(S, T, saved_T, st)
    bi = background_keys(S, B, T, epos, spy, AD, st)
    try:
        Kb, q = read_background(slim, S, B, cols, st)
    except InputMismatch as exc:
        st.stop("S-EXACT", "inputs: %s" % exc, {"slim_file": str(exc)})
    bad = AD.season_key(Kb["issue"].to_numpy(np.int64)[q], spy) != AD.season_key(
        T["issue"].to_numpy(np.int64)[epos][bi], spy)
    if bad.any():
        st.stop("S-BG", "%d background rows' issue is of another calendar month than their explained row's"
                % int(bad.sum()))
    if (Kb["lead"].to_numpy(np.int64) != int(lead)).any():
        st.stop("S-BG", "%d background rows are of another lead than %d"
                % (int((Kb["lead"].to_numpy(np.int64) != int(lead)).sum()), int(lead)))
    return epos, bi, Kb, q


def prediction_design(AD, opt, params, run_ns, rival, lead, spy, offset, T, saved_T, epos, Kb, slim, link, st,
                      log=None):
    """The prediction-time design, one path for the owner's run and the smoke's pre-flight: every sample row must be
    of a unit with BARDL parameters (S-SAMPLE); design() on the test rows of those units (the call predict() makes);
    then background_design() on the sampled units' whole test sets with the background rows (S-BG). Returns (X_test,
    kidx: the X_test row of each test row or -1, tpart, Db, eta_bg_model, record)."""
    keep = T["unit"].astype(str).isin(set(params["units"])).to_numpy()
    kidx = np.full(len(T), -1, np.int64)
    kidx[keep] = np.arange(int(keep.sum()))
    if (kidx[epos] < 0).any():
        st.stop("S-SAMPLE", "%d sample rows are of units without BARDL parameters" % int((kidx[epos] < 0).sum()))
    tk = slim_set(T[keep], slim.history, slim.extras, link, AD.KEYS)
    X_test, _, _ = AD.design(tk.keys, tk.normal[link], tk.history, tk.extras, params["climate_means"], opt, lead, spy,
                             offset)
    units_e = T["unit"].astype(str).to_numpy()[epos]
    tpart = np.flatnonzero(T["unit"].astype(str).isin(set(units_e)).to_numpy())
    Db, eta_bg_model, rec = background_design(AD, opt, params, run_ns, rival, lead, spy, offset, T, X_test, kidx, epos,
                                              tpart, Kb, slim.history, slim.extras, link, saved_T, st, log)
    return X_test, kidx, tpart, Db, eta_bg_model, rec


def shap_pipeline(AD, opt, params, run_ns, rival, lead, spy, offset, T, saved_T, S, B, slim, cols, link, export_x, st,
                  log):
    """Everything between S-EXACT and the writer, one path for the owner's run and the smoke: the players and terms,
    the explained rows and background rows (background_rows: S-SAMPLE, S-BG), the prediction-time design of both
    (prediction_design: S-SAMPLE, S-BG), the SHAP values and the S-ZERO masks. Returns a namespace (every array the
    writer needs, and the pieces the smoke checks)."""
    ns = SimpleNamespace(secs={})
    t0 = time.time()
    ns.players, ns.single, ns.means = term_layout(AD, opt, params, slim.history, slim.extras, export_x, log)
    ns.vmap, ns.variables = C.variable_map(ns.players)
    ns.pvar = [ns.variables.index(ns.vmap[p]) for p in ns.players]
    ns.normal_p, ns.normal_v = ns.players.index("normal"), ns.variables.index("normal")
    ns.epos, _, Kb, q = background_rows(AD, S, B, T, saved_T, slim, cols, spy, lead, st)
    epos = ns.epos
    rowpos = {int(r): i for i, r in enumerate(S["row"].to_numpy(np.int64))}
    ns.bg_lists = [[] for _ in range(len(S))]
    for r, qq in zip(B["row"].to_numpy(np.int64), q):
        ns.bg_lists[rowpos[int(r)]].append(int(qq))
    ns.px, ns.pb, ns.pw = TS.pairs_for(ns.bg_lists)
    ns.Kb = Kb
    sizes = list(map(len, ns.bg_lists))
    log("sample: %d explained rows, %d distinct background rows (per row: min %d, median %.0f, max %d), %d pairs; "
        "%d slim files read (%.1f MB)" % (len(S), len(Kb), min(sizes), float(np.median(sizes)), max(sizes),
                                          ns.px.size, slim.files_read, slim.bytes_read / 2 ** 20))
    ns.secs["sample_and_background_rows"] = round(time.time() - t0, 1)
    t0 = time.time()                                      # the prediction-time design (S-SAMPLE, S-BG)
    (ns.X_test, ns.kidx, ns.tpart, ns.Db, ns.eta_bg_model,
     ns.bgrec) = prediction_design(AD, opt, params, run_ns, rival, lead, spy, offset, T, saved_T, epos, Kb, slim, link,
                                   st, log)
    ns.De = ns.X_test[ns.kidx[epos]]
    units_e = T["unit"].astype(str).to_numpy()[epos]
    ns.secs["background_design"] = round(time.time() - t0, 1)
    t0 = time.time()                                      # the SHAP values
    nfeat = len(AD.feature_names(opt))
    ns.Ue = unit_arrays(params, units_e, nfeat)
    ns.Ub = unit_arrays(params, Kb["unit"].astype(str).to_numpy(), nfeat)
    ns.z0e = T["nfit__" + link].to_numpy(np.float64)[epos]
    ns.z0b = Kb["nfit__" + link].to_numpy(np.float64)
    (ns.phi, ns.phiv, ns.base, ns.eta, ns.f_b, ns.terms, ns.lin_gap,
     ns.kstats) = bardl_shap(ns.De, ns.Db, ns.z0e, ns.z0b, ns.Ue, ns.Ub, ns.px, ns.pb, ns.pw, ns.single, ns.means,
                             len(ns.players), ns.pvar, len(ns.variables), ns.normal_p, ns.normal_v)
    raw_cols = ns.players[:-1]
    ns.Re = T.iloc[epos][raw_cols].to_numpy(np.float64)
    ns.Rb = Kb[raw_cols].to_numpy(np.float64)
    ns.const, ns.constv = masks(ns.Re, ns.Rb, ns.z0e, ns.z0b, ns.px, ns.pb, np.arange(len(raw_cols)), len(ns.players),
                                np.asarray(ns.pvar[:-1], np.int64), len(ns.variables), ns.normal_p, ns.normal_v)
    ns.saved_e = saved_T[epos]
    ns.secs["shap"] = round(time.time() - t0, 1)
    return ns


def identity(a, bd, ident):
    """The resume identity (rival_shap.py:538-544, adapted): every file the piece depends on."""
    return {"problem": a.problem, "lead": int(a.lead), "learner": bd.rid, "rows": int(a.rows),
            "sample": ident["sample_sha256"], "background_file": ident["background_sha256"],
            "model_files": {"done_%s.json" % bd.rid: bd.sha["done"], "preds_%s.parquet" % bd.rid: bd.sha["preds"],
                            "map_%s.json" % bd.rid: bd.sha["map"], "coverage_%s.parquet" % bd.rid: bd.sha["coverage"]},
            "board": {k: bd.sha[k] for k in ("human_board.json", "human_picks.json", "registry", "slim_manifest.json",
                                             "derived.json", "export_manifest.json", "board.json")},
            "adapter": bd.sha["adapter"],
            "scripts": {f: C.sha256_file(os.path.join(HERE, f)) for f in HELPERS}}


def read_sample(sroot, ident, lead, rows, st):
    """The registered sample and background keys, parsed from the bytes whose SHA-256 the register names; --rows K
    keeps the first K rows and only their keys (rival_shap.py:103-106)."""
    sb, ssha = read_bytes(os.path.join(sroot, "sample.parquet"))
    bb, bsha = read_bytes(os.path.join(sroot, "background_lead_%d.parquet" % int(lead)))
    if ssha != ident["sample_sha256"] or bsha != ident.get("background_sha256"):
        st.stop("S-SAMPLE", "the sample or its background file changed after its registered identity was read")
    S = pq.read_table(pa.BufferReader(sb)).to_pandas()
    B = pq.read_table(pa.BufferReader(bb)).to_pandas()
    if rows:
        S = S.iloc[:rows].copy()
        B = B[B["row"].isin(S["row"])].copy()
    return S.reset_index(drop=True), B.reset_index(drop=True)


def compare_reminder(out, model, problem, lead, log):
    """Logging only (design risk 6, a forgotten comparison): when compare/ of this models root holds a comparison
    that does not cover this finished piece (per_lead.json does not list it, or the comparison's done record was made
    from other rows: the inputs of compare_shap.py:336-339 recomputed), log a REMINDER to run compare_shap.py again.
    Never stops and never changes the exit code."""
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


def main(argv=None):
    a = parse(argv)
    log = C.Log("bardl_shap_%s_lead%d" % (a.problem, a.lead), a.log_dir or C.LOGS)
    try:
        return run(a, log)
    except SystemExit:
        raise
    except Exception as exc:
        log("CRASH: %s: %s" % (type(exc).__name__, exc))
        raise


def run(a, log):
    t_start = time.time()
    secs = {}
    log("BARDL SHAP %s lead %d%s; versions %s" % (a.problem, a.lead, " (exactness only)" if a.exactness_only else "",
                                                C.versions()))
    bd = board(a.problem, a.lead, a.rival, log)
    model = "rival_%s" % bd.rid
    out = C.makedirs(os.path.join(a.out_root or C.out_dir(a.problem, a.lead), model))
    st = Stopper(out, model, a.problem, a.lead, log)
    s_env(st, bd.hb, log)
    reg_rec = (bd.hb.get("registry") or {}).get("registry")
    if bd.sha["registry"] != reg_rec:                     # before its bytes are parsed or its adapter is read
        write_exactness(st, {"pass": False, "stage": "inputs", "inputs_pass": False, "inputs_failed": ["registry"],
                             "inputs": {"registry": {"sha256": bd.sha["registry"], "recorded": reg_rec,
                                                     "equal": False}},
                             "detail": "the registry differs from the human board's record"})
    rival = registry_rival(bd, log)
    ad_path, ad_bytes, bd.sha["adapter"] = adapter_file(bd, rival, log)
    AD = load_adapter(ad_path, ad_bytes)
    params = bd.map.get("params") or {}
    try:
        opt = AD._options(rival)
        run_ns = SimpleNamespace(derived={"R17": bd.derived["R17"]})
        spy, offset = AD.run_timing(run_ns)
    except (AD.BardlRefusal, KeyError) as exc:
        write_exactness(st, {"pass": False, "stage": "inputs", "inputs_pass": False,
                             "detail": "the registry options or the run timing are not usable: %s" % exc})
    link = AD.LINK
    ident, inputs = None, None
    rows_path = os.path.join(out, "rows.parquet")
    if not a.exactness_only:
        sroot = a.sample_root or C.sample_dir(a.problem)
        try:
            ident = C.sample_identity(a.problem, sroot, a.register, lead=a.lead)
        except SystemExit as exc:                         # its message starts with 'STOP S-SAMPLE: '
            st.stop("S-SAMPLE", str(exc.code).replace("STOP S-SAMPLE: ", "", 1))
        nreg = ident.get("n_asked") if ident.get("n_asked") is not None else ident.get("n")
        if nreg is None or int(nreg) != int(a.n):
            st.stop("S-SAMPLE", "--n %d differs from the registered N %s" % (a.n, nreg), {"registered_n": nreg})
        inputs = identity(a, bd, ident)
        if C.piece_done(rows_path, inputs):
            log("%s: finished piece found with matching hashes: skipped" % model)
            compare_reminder(out, model, a.problem, a.lead, log)
            return 0
        st.drop_done("a recompute starts")
    # ---- S-EXACT
    t0 = time.time()
    preds = pq.read_table(pa.BufferReader(bd.preds_bytes)).to_pandas()
    cov = pq.read_table(pa.BufferReader(bd.coverage_bytes)).to_pandas()
    ok_rec, R = check_records(bd, AD, rival, params, spy, offset, preds, cov)
    base_rec = {"model_file": "map_%s.json" % bd.rid, "map_sha256": bd.sha["map"], "adapter_sha256": bd.sha["adapter"],
                "inputs_pass": ok_rec, "inputs": R,
                "board_code_reproduced": board_code_reproduced(ad_path, bd.hb.get("tool_code_sha256")),
                "threads": blas_threads()}
    if not ok_rec:
        bad = sorted(k for k, v in R.items() if not v.get("equal"))
        write_exactness(st, dict(base_rec, stage="inputs", inputs_failed=bad, detail="the board's records disagree: %s"
                                 % bad, **{"pass": False}))
    slim = Slim(bd.slim_dir, bd.slim_manifest)
    cols = uniq(list(AD.KEYS) + ["nfit__" + link] + slim.history + slim.extras)
    try:
        T = read_test(slim, cols)
    except InputMismatch as exc:
        write_exactness(st, dict(base_rec, stage="inputs", slim_file=str(exc), detail=str(exc), **{"pass": False}))
    exact, saved_T = exactness(AD, rival, params, run_ns, T, preds, (bd.hb.get("run") or {}).get("legal"), a.lead,
                               slim.history, slim.extras, link, log)
    exact.update(base_rec)
    exact["stage"] = "bits"
    exact["pass"] = bool(exact["pass"] and ok_rec)
    if saved_T is not None:
        exact["normal_table"] = normal_table_stat(AD, T, link, spy)
    log("S-EXACT: %d board record checks %s; predict() on %d test rows: pre bit-equal %s of %s (max |diff| %s), raw "
        "%s of %s: %s; board code reproduced: %s" % (
            len(R), "all equal" if ok_rec else "NOT all equal", len(T), exact.get("bit_equal_rows"),
            exact.get("rows_finite"), exact.get("max_abs_diff"), (exact.get("raw") or {}).get("bit_equal_rows"),
            (exact.get("raw") or {}).get("rows_finite"), "PASS" if exact["pass"] else "FAIL",
            exact["board_code_reproduced"].get("equal")))
    write_exactness(st, exact)
    secs["exactness"] = round(time.time() - t0, 1)
    if a.exactness_only:
        log("%s: exactness only: exactness.json written (%.1f s, peak RSS %s GB)" % (model, time.time() - t_start,
                                                                                     C.rss_gb()))
        return 0
    # ---- the sample, the background, the SHAP values (one path for the owner's run and the smoke)
    S, B = read_sample(sroot, ident, a.lead, a.rows, st)
    ns = shap_pipeline(AD, opt, params, run_ns, rival, a.lead, spy, offset, T, saved_T, S, B, slim, cols, link,
                       (bd.export_manifest.get("columns") or {}).get("x") or [], st, log)
    secs.update(ns.secs)
    names = AD.feature_names(opt)
    try:
        board_rel = os.path.relpath(bd.human, C.TREEROUTE).replace("\\", "/")
    except ValueError:                                    # a board on another drive than D:/treeroute
        board_rel = C.redact(bd.human).replace("\\", "/")
    meta = {"model": model, "problem": a.problem, "lead": int(a.lead), "link": link,
            "c": ((bd.hb.get("run") or {}).get("c") or {}).get(str(a.lead)), "ub": (bd.hb.get("run") or {}).get("ub"),
            "background": "B2 (PROTOCOL.md 5)", "exactness": exact, "guard": bd.done.get("guard"),
            "value_function": "interventional, per-row background", "duplicates_merged": {}, "variable_map": ns.vmap,
            "sample_sha256": ident["sample_sha256"],
            "method": "exact linear SHAP per unit (standardised BayesianRidge, the adapter's predict rule); each "
                      "3-month mean split exactly over its three lag players (its 3-player Shapley value over 8 "
                      "coalitions per pair, under the adapter's missing-value rule); the offset to 'normal'",
            "published": True, "board": board_rel,
            "adapter_sha256": bd.sha["adapter"], "map_sha256": bd.sha["map"],
            "normal_table": "the unit's prediction-time table (its test set); the background and explained rows' own "
                            "normals equal it bit for bit (S-BG)",
            "background_design": ns.bgrec,
            "mean_terms": {names[d]: v for d, v in ns.kstats.items()},
            "terms": {"single": {names[d]: ns.players[p] for d, p in ns.single},
                      "mean": {names[d]: [ns.players[x] for x in qs] for d, _, qs in ns.means}},
            "fallback_rows": {"explained": int(ns.Ue["fallback"].sum()), "background": int(ns.Ub["fallback"].sum())},
            "pairs": int(ns.px.size), "seconds": secs, "board_code_reproduced": exact.get("board_code_reproduced")}
    meta["link_key"] = link_key(meta)
    cbr = bd.cb.get("run") or {}
    meta["link_key_common_board"] = link_key({"link": link, "c": (cbr.get("c") or {}).get(str(a.lead)),
                                              "ub": cbr.get("ub")})
    meta["peak_rss_gb"] = C.rss_gb()
    rec = RW.write(out, S, ns.players, ns.phi, ns.variables, ns.phiv, ns.base, ns.eta, ns.saved_e, ns.saved_e, None,
                   meta, log, B, const=ns.const, constv=ns.constv, eta_bg=ns.f_b, eta_bg_model=ns.eta_bg_model)
    C.mark_done(rows_path, inputs, {"seconds": round(time.time() - t_start, 1), "sample_sha256": ident["sample_sha256"],
                                    "background_keys_sha256": rec["background_keys_sha256"]})
    log("%s done: %d rows, %d pairs; players nonzero %d of %d, variables nonzero %d of %d; additivity max %.2e / %.2e; "
        "evaluator max %.2e (background %.2e); link key %s; %.1f s; peak RSS %s GB"
        % (model, rec["rows"], ns.px.size, rec["players_nonzero"], len(ns.players), rec["variables_nonzero"],
           len(ns.variables), rec["max_abs_additivity_error"], rec["max_abs_additivity_error_variable"],
           rec["max_abs_evaluator_minus_model"], rec["max_abs_background_evaluator_minus_model"], meta["link_key"],
           time.time() - t_start, C.rss_gb()))
    compare_reminder(out, model, a.problem, a.lead, log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
