"""POST HOC re-computation of the engine-v2 alarm replay, implementer A (engine path). Owner ruling AN2.

Spec: D:/treeroute/analysis/paper_posthoc/v2_replay/SPEC.md (sections 2-7, 10). Everything computed here is POST HOC
(the alarm was specified after the five v1 runs were locked, run and scored); on coral the replay is CIRCULAR (the rule
was designed from the same coral test window). Coral's 2016-2019 test window was set by hand. No locked number,
verdict or adoption changes.

Approach A: the engine-v2 code (hash 88f4db2c) and its two replay tools are used read-only, exactly where the original
2026-10-21 replay used them:
  A1  verify the engine-v2 hash, the tool and module file hashes, the LIVE hash (read-only);
  A2  re-run tools/alarm_replay.py then tools/alarm_with_without.py into ./tool_rerun (fresh folder);
  G0-G9  the reproduction gate (SPEC section 5); on any failure: write result_A.json with the failing item and stop;
  A3  the section-6 quantities Q1-Q12 with the engine's own functions (alarm.batch_keys, alarm.decide_alarm,
      metrics.score_table, alarm_pass.verdict_with); Q5 contributions by the spec's formula.
Writes ONLY inside D:/treeroute/analysis/paper_posthoc/v2_replay/A/.

Run:  py -3.9 -I -B D:/treeroute/analysis/paper_posthoc/v2_replay/A/replay_A.py
"""
import sys

sys.dont_write_bytecode = True

import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import platform  # noqa: E402
import subprocess  # noqa: E402
import time as _time  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = Path("D:/treeroute/analysis/paper_posthoc/v2_replay")
if HERE != ROOT.resolve() / "A":
    raise SystemExit("replay_A.py must live in %s" % (ROOT / "A"))
ENGINE_V2 = Path("D:/treeroute/engine_v2/engine")
TOOLS = ENGINE_V2 / "tools"
LIVE_TREEROUTE = Path("C:/Users/moh the ghost/Desktop/data set for reserch paper/engine/treeroute")
GATE = Path("D:/treeroute/engine_v2/replay_af2_20261021")
HIST = Path("D:/treeroute/engine_v2/replay")
TOOL_OUT = HERE / "tool_rerun"
INPUTS_LIST = ROOT / "INPUTS_SHA256.txt"
SPEC = ROOT / "SPEC.md"
EDGES = Path("D:/treeroute/runs/_headline_tables/coral/coral_report/magnitude_edges.csv")
RESULTS604 = Path("D:/treeroute/analysis/guidance/coral/results_coral.json")
RESULT_FILE = HERE / "result_A.json"

ENGINE_V2_HASH = "88f4db2ce7c0a48834243b8e9403a29d8a3dbcc88c00ed44620d9ced79b44b7d"
LIVE_HASH = "930d961cdfdd219c36b113174e6c865096f973068e30696850f13d5ec4a60814"

PACKAGES = ["pm25", "ndvi", "fire", "defo", "coral"]
RUN_IDS = {"pm25": "20261007_74e67609", "ndvi": "20261016_d1de3158", "fire": "20261017_869d1f38",
           "defo": "20261017_d71c61f4", "coral": "20261020_f3b8e3da"}
RUNS = {p: "D:/treeroute/runs/%s/headline/%s" % (p, RUN_IDS[p]) for p in PACKAGES}
LEADS = {"pm25": [6, 12], "ndvi": [6, 12], "fire": [6, 12], "defo": [1], "coral": [183, 365]}
ABS_EDGE = 50.0
THRESHOLDS = [1.5, 2.0, 2.5, 3.0]

# section 2's table (design; confirmed by the gate)
EXPECTED_STATUS = {"pm25/0": "inert_twin_not_simpler", "pm25/6": "inert_twin_not_simpler",
                   "pm25/12": "not_applicable_declined", "ndvi/0": "inert_twin_not_simpler",
                   "ndvi/6": "not_applicable_declined", "ndvi/12": "not_applicable_declined",
                   "fire/0": "inert_twin_not_eligible", "fire/6": "not_applicable_declined",
                   "fire/12": "not_applicable_declined", "defo/0": "active",
                   "defo/1": "not_replayable_twin_not_saved", "coral/0": "active",
                   "coral/183": "not_replayable_twin_not_saved", "coral/365": "not_applicable_declined"}
PLAIN_STATUS = {"active": "can switch",
                "inert_twin_not_simpler": "cannot switch: twin not simpler",
                "inert_twin_not_eligible": "cannot switch: twin fails its skill guard",
                "not_applicable_declined": "nothing to switch: declined",
                "not_replayable_twin_not_saved": "not replayable: twin not saved"}
OUTCOME_LABEL = "outcome-defined (selected on the test label)"

# ---------------------------------------------------------------------------------------------------------------------
# The spec's printed values (SPEC.md section 5), checked against the gate files and the recomputation.
SPEC_G1 = {
    "coral/0": {"status": "active", "twin_arm": "arcsine_corrector_unweighted", "twin_kind": "weighting",
                "twin_simpler": True, "twin_eligible": True, "reference_gap": 0.34056479282671, "reference_rows": 2046,
                "batches": 48, "batches_tested": 33, "batches_fired": 11,
                "fired_batches": "2016-01 2016-02 2016-03 2016-04 2016-05 2016-06 2016-08 2017-03 2017-12 2019-05 "
                                 "2019-06",
                "rows_switched": 737, "n": 2312, "max_ratio_tested": 29.105817502602708,
                "mae_without": 6.69798924506233, "mae_with": 6.119956002798195},
    "pm25/0": {"n": 91428, "mae_without": 3.588091134093021, "mae_with": 3.588091134093021},
    "pm25/6": {"status": "inert_twin_not_simpler", "mae_without": 3.846310424132128, "mae_with": 3.846310424132128},
    "pm25/12": {"status": "not_applicable_declined", "mae_without": 4.083558322865165,
                "mae_with": 4.083558322865165},
    "ndvi/0": {"status": "inert_twin_not_simpler", "mae_without": 0.03146059686292064,
               "mae_with": 0.03146059686292064},
    "ndvi/6": {"status": "not_applicable_declined", "mae_without": 0.03956835866470208,
               "mae_with": 0.03956835866470208},
    "ndvi/12": {"status": "not_applicable_declined", "mae_without": 0.039583272201769236,
                "mae_with": 0.039583272201769236},
    "fire/0": {"status": "inert_twin_not_eligible", "mae_without": 0.004385064558301006,
               "mae_with": 0.004385064558301006},
    "fire/6": {"status": "not_applicable_declined", "mae_without": 0.006312458723027394,
               "mae_with": 0.006312458723027394},
    "fire/12": {"status": "not_applicable_declined", "mae_without": 0.006310978468756987,
                "mae_with": 0.006310978468756987},
    "defo/0": {"status": "active", "twin_arm": "log_c_plain_unweighted", "twin_kind": "tool",
               "reference_gap": 0.00013719429872479928, "reference_rows": 276822, "batches": 4, "batches_tested": 4,
               "batches_fired": 0, "max_ratio_tested": 1.1659792695776747, "mae_without": 0.005415798421978487,
               "mae_with": 0.005415798421978487},
    "defo/1": {"status": "not_replayable_twin_not_saved", "mae_without": 0.005407746164567043, "batches": 4,
               "batches_ge30": 4},
    "coral/183": {"status": "not_replayable_twin_not_saved", "mae_without": 7.709698984777605, "batches": 49,
                  "batches_ge30": 32},
    "coral/365": {"status": "not_applicable_declined", "mae_without": 8.294498353993655,
                  "mae_with": 8.294498353993655},
}
SPEC_G1_SUBSETS = {  # (package/lead, subset id): (n or None, without, with or None)
    ("coral/0", "y_gt_0"): (1024, 13.370101628934457, 11.835788785619453),
    ("coral/0", "y_gt_q75"): (239, 41.05202467908258, 33.27844301061296),
    ("coral/0", "y_ge_50"): (140, 53.12512328455528, 40.9865068947793),
    ("coral/183", "y_gt_0"): (None, 15.883504733505497, None),
    ("coral/183", "y_gt_q75"): (255, 50.58073261784866, None),
    ("coral/183", "y_ge_50"): (None, 68.44966552627503, None),
    ("coral/365", "y_gt_0"): (None, 17.4696095648763, 17.4696095648763),
    ("coral/365", "y_gt_q75"): (251, 55.70945219123506, 55.70945219123506),
    ("coral/365", "y_ge_50"): (None, 73.64017261904762, 73.64017261904762),
}
SPEC_G2_ELIG = {"coral": (7.287182963109116, 9.74151323420556, True),
                "fire": (0.004386949584483835, 0.00436777286420139, False),
                "defo": (0.005808902179729096, 0.006102746693604387, True),
                "pm25": (3.3585540357961188, 3.5256518387286944, True),
                "ndvi": (0.029235256613920256, 0.03681265458390077, True)}
SPEC_G2_INERT_MAX = {"pm25": 1.753861864808271, "ndvi": 1.749949522314697, "fire": 1.847279910383901}
SPEC_G3 = {"2016": (873, 12.406328256098309, 10.681069664805374), "2017": (565, 3.5692507744181308, 3.6880301411805525),
           "2018": (443, 1.280418254929322, 1.280418254929322), "2019": (431, 4.805509495430039, 5.043624464950422)}
SPEC_G6 = {1.5: "6.109", 2.5: "6.100", 3.0: "6.100"}
SPEC_G7 = {"tag": "helps", "mean": 7.873171654763077, "low": 2.405477799042173, "high": 13.34086551048398,
           "n_groups": 37, "groups_better": 23, "pooled_contrast": 2.17454235119546,
           "bj_mean": 8.016229062074508, "bj_low": 2.3522839485988065, "bj_high": 13.68017417555021, "bj_n": 35,
           "bj_flag": False, "band": 0.9175581931137083, "without_tag": "helps", "without_mean": 5.206781299700313,
           "without_low": 1.9722236985140444, "without_high": 8.441338900886581}
SPEC_G8 = {"C": {"AGRRA": (1, 5.540752183604888), "FRRP": (190, 7.659652365514182),
                 "McClanahan": (189, 35.05979452499404), "Reef_Check": (1932, 3.829490304207522)},
           "T_pooled": 6.14748576299595, "T_FRRP": 7.736388261777524, "T_Reef_Check": 4.022595138987255,
           "M2_pooled": 6.393951387338696, "ratio": 4.2913410523963345}


# ---------------------------------------------------------------------------------------------------------------------
def sha256_file(path):
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def fnum(x):
    """A float for JSON (None for missing / not finite)."""
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def jsonable(o):
    import numpy as np
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return fnum(o)
    if o is None or isinstance(o, str):
        return o
    raise TypeError("not JSON-able: %r (%s)" % (o, type(o)))


def same_float(a, b):
    """Bit-equal floats (NaN == NaN; None == NaN)."""
    a = float("nan") if a is None else float(a)
    b = float("nan") if b is None else float(b)
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    import struct
    return struct.pack("<d", a) == struct.pack("<d", b)


def bits_equal(a, b):
    import numpy as np
    a = np.ascontiguousarray(np.asarray(a, dtype=np.float64))
    b = np.ascontiguousarray(np.asarray(b, dtype=np.float64))
    if a.shape != b.shape:
        return False
    na, nb = np.isnan(a), np.isnan(b)
    if not np.array_equal(na, nb):
        return False
    return bool(np.array_equal(a[~na].view(np.uint64), b[~nb].view(np.uint64)))


def year_key(v):
    v = float(v)
    return str(int(v)) if v.is_integer() else repr(v)


class GateFailure(Exception):
    pass


# ---------------------------------------------------------------------------------------------------------------------
def main():
    t0 = _time.time()
    out = {"implementer": "A", "script_sha256": sha256_file(Path(__file__)),
           "python_and_libraries": None, "inputs": {}, "engine_v2_hash": None, "read_engine_code": None,
           "gates": {}, "passes": {}, "batches": {}, "by_year": {}, "coral_programme": {},
           "coral_programme_year": {}, "contributions": {}, "forms": {}, "subsets": {}, "small_batches": {},
           "threshold_check": {}, "silence": {}, "regions": {}, "verdicts": {}, "summary_text": []}
    gates = out["gates"]

    def write_result():
        RESULT_FILE.write_text(json.dumps(jsonable(out), indent=1, sort_keys=False) + "\n", encoding="utf-8")

    def fail(item, details):
        gates[item] = {"pass": False, "details": details}
        out["summary_text"] = ["POST HOC: the reproduction gate FAILED at %s; nothing new was computed." % item]
        write_result()
        print("GATE FAILED:", item)
        print(json.dumps(jsonable(details), indent=1)[:4000])
        raise SystemExit(2)

    # ------------------------------------------------------------------ G0: inputs, engine and tool hashes (A1)
    listed = {}
    for line in INPUTS_LIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        h, p = line.split(" ", 1)
        listed[p.lstrip("*")] = h
    g0 = {"listed_files": len(listed), "mismatched": [], "missing": [],
          "spec_sha256": sha256_file(SPEC), "inputs_list_sha256": sha256_file(INPUTS_LIST)}
    for p, h in listed.items():
        if not Path(p).is_file():
            g0["missing"].append(p)
            continue
        got = sha256_file(p)
        out["inputs"][p] = got
        if got != h:
            g0["mismatched"].append({"file": p, "expected": h, "obtained": got})
    if g0["missing"] or g0["mismatched"]:
        fail("G0", g0)

    # import the engine-v2 code read-only (never the LIVE engine)
    for p in (str(TOOLS), str(ENGINE_V2)):
        if p in sys.path:
            sys.path.remove(p)
    sys.path.insert(0, str(TOOLS))
    sys.path.insert(0, str(ENGINE_V2))
    import numpy as np
    import pandas as pd
    import pyarrow
    import pyarrow.parquet as pq
    import treeroute
    from treeroute.runs import fingerprint as FP
    from treeroute.layer import alarm as LAL
    from treeroute.layer import arms as LA
    from treeroute.pipeline import alarm_pass as AP
    from treeroute.report import metrics as M
    from treeroute.route.kinds import GridPoint
    from treeroute import engine_constants as K
    import alarm_replay as AR
    import alarm_with_without as AWW

    out["python_and_libraries"] = {"python": sys.version, "executable": sys.executable,
                                   "platform": platform.platform(), "numpy": np.__version__,
                                   "pandas": pd.__version__, "pyarrow": pyarrow.__version__,
                                   "treeroute_imported_from": str(Path(treeroute.__file__).resolve().parent),
                                   "flags": {"isolated": bool(sys.flags.isolated),
                                             "dont_write_bytecode": bool(sys.dont_write_bytecode)}}
    if Path(treeroute.__file__).resolve().parent != (ENGINE_V2 / "treeroute").resolve():
        fail("G0", {"treeroute imported from the wrong folder": str(treeroute.__file__)})
    v2_hash = FP.engine_code_sha256()
    live_hash = FP.engine_code_sha256(LIVE_TREEROUTE)
    out["engine_v2_hash"] = v2_hash
    g0.update({"engine_v2_hash": v2_hash, "engine_v2_expected": ENGINE_V2_HASH, "live_hash": live_hash,
               "live_expected": LIVE_HASH,
               "constants": {"A8.alarm_ratio_threshold": float(K.ALARM_RATIO_THRESHOLD),
                             "A8.alarm_min_batch_rows": int(K.ALARM_MIN_BATCH_ROWS)},
               "tool_and_module_files_checked_in_list": [str(TOOLS / "alarm_replay.py").replace("\\", "/"),
                                                         str(TOOLS / "alarm_with_without.py").replace("\\", "/")]})
    if v2_hash != ENGINE_V2_HASH or live_hash != LIVE_HASH:
        fail("G0", g0)
    if float(K.ALARM_RATIO_THRESHOLD) != 2.0 or int(K.ALARM_MIN_BATCH_ROWS) != 30:
        fail("G0", g0)
    for mod, fname in ((AR, "alarm_replay.py"), (AWW, "alarm_with_without.py")):
        if Path(mod.__file__).resolve() != (TOOLS / fname).resolve():
            fail("G0", {"tool imported from the wrong file": str(mod.__file__)})
    gates["G0"] = {"pass": True, "details": g0}
    print("G0 pass (%d listed files, engine v2 %s, LIVE %s) %.0fs" % (len(listed), v2_hash[:8], live_hash[:8],
                                                                        _time.time() - t0))

    # ------------------------------------------------------------------ A2: re-run the original tools
    run_args = [RUNS[p] for p in PACKAGES]
    edge_arg = "coral=%s" % str(EDGES).replace("\\", "/")
    cmds = [[sys.executable, "-I", "-B", str(TOOLS / "alarm_replay.py")] + run_args + ["--out", str(TOOL_OUT)],
            [sys.executable, "-I", "-B", str(TOOLS / "alarm_with_without.py")] + run_args
            + ["--out", str(TOOL_OUT), "--magnitude-edges", edge_arg, "--abs-edge", "50"]]
    a2 = {"commands": [" ".join(c[1:]) for c in cmds], "runs": [], "skipped": "--skip-tools" in sys.argv}
    if a2["skipped"] and not (TOOL_OUT / "WITH_WITHOUT.csv").is_file():
        raise SystemExit("--skip-tools needs an earlier tool re-run in %s" % TOOL_OUT)
    for c in ([] if a2["skipped"] else cmds):
        r = subprocess.run(c, cwd=str(HERE), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        a2["runs"].append({"returncode": r.returncode, "stdout_sha256": hashlib.sha256(r.stdout).hexdigest(),
                           "stderr_tail": r.stderr.decode("utf-8", "replace")[-2000:]})
        if r.returncode != 0:
            fail("G1", {"step A2 tool run failed": a2})
    print("A2 tools re-run %.0fs" % (_time.time() - t0))

    # ------------------------------------------------------------------ in-process recomputation (engine functions)
    def rj(path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    edges_df = pd.read_csv(str(EDGES))
    coral_edges = {int(r.lead): float(r.q75_positive_donor_labels) for r in edges_df.itertuples()}
    BASE = ["unit", "group", "time", "year", "y", "normal", "legal_min", "legal_max"]

    def keep_cols(frame, extra, cols):
        k = [c for c in BASE] + [c for c in extra if c not in BASE] + list(cols)
        return list(dict.fromkeys(k))

    def pooled(frame, cols, S):
        t = M.score_table(frame[keep_cols(frame, (), cols)], (), S["tol"], S["floor"], S["kind"])
        res = {}
        for c in cols:
            sel = t[(t["line"] == M.LINE_POOLED) & (t["rows_basis"] == M.ROWS_BASIS_ALL) & (t["column"] == c)]
            if len(sel) != 1:
                raise RuntimeError("no single pooled line for %s" % c)
            res[c] = (float(sel["mae"].iloc[0]), int(sel["n"].iloc[0]))
        return res

    def pooled_mask(frame, mask, cols, S):
        return pooled(frame.loc[mask], cols, S)

    def keyed(frame, by, cols, S):
        t = M.score_table(frame[keep_cols(frame, by, cols)], tuple(by), S["tol"], S["floor"], S["kind"])
        sel = t[(t["line"] == M.LINE_KEY) & (t["rows_basis"] == M.ROWS_BASIS_ALL)]
        res = {}
        for c in cols:
            s = sel[sel["column"] == c]
            keys = list(zip(*[s[b].tolist() for b in by]))
            for k, mae_, n_ in zip(keys, s["mae"].tolist(), s["n"].tolist()):
                res.setdefault(k, {})[c] = (float(mae_), int(n_))
        return res

    states = {}
    for pkg in PACKAGES:
        folder = Path(RUNS[pkg])
        adoption, verdict = rj(folder / "adoption.json"), rj(folder / "verdict.json")
        record, derived = rj(folder / "run_record.json"), rj(folder / "derived.json")
        ladder = rj(folder / "ladder" / "ladder.json")
        weightings = (LA.Weighting.UNWEIGHTED,) if verdict["router_kind"] == "region" \
            else (LA.Weighting.UNWEIGHTED, LA.Weighting.GLS)
        cadence = AR._cadence(derived["R1"]["value"])
        declined = bool(adoption["declined"])
        if declined:
            raise RuntimeError("%s nowcast declined: not expected by the spec" % pkg)
        adopted_col = verdict.get("adopted_column") or (M.ARM_PREFIX + verdict["adopted"])
        reference_col = verdict["reference"]
        adopted = AR._arm(adoption["adopted"])
        point = GridPoint(float(adoption["penalty"]["level"]),
                          None if adoption["penalty"]["ratio"] is None else float(adoption["penalty"]["ratio"]))
        twin, tkind = LAL.twin_of(adopted, weightings)
        simpler = LAL.twin_is_simpler(adopted, twin)
        eligible, basis = LAL.twin_eligible_at_point(
            adoption["surface_mae"], twin, point, AP.decline_baseline_key(folder),
            in_eligible_list=LAL.twin_eligible_nowcast(twin, [AR._arm(a) for a in adoption.get("eligible") or []]))
        ref = AP.nowcast_reference(folder, adopted, twin, point)
        gap = ref["gap"]
        status = LAL.pass_status(declined, simpler, eligible, gap)
        names = set(pq.read_schema(str(folder / "test_preds.parquet")).names)
        twin_col, pre_tw = M.ARM_PREFIX + LA.arm_name(twin), M.PRE_PREFIX + LA.arm_name(twin)
        pre_ad = M.PRE_PREFIX + adopted_col[len(M.ARM_PREFIX):]
        want = ["unit", "group", "time", "year", "lead", "issue", "y", "normal", "legal_min", "legal_max",
                adopted_col, reference_col, twin_col, pre_tw]
        if pre_ad in names:
            want.append(pre_ad)
        if reference_col.startswith(M.ARM_PREFIX):
            pre_ref = M.PRE_PREFIX + reference_col[len(M.ARM_PREFIX):]
            if pre_ref in names:
                want.append(pre_ref)
        want = list(dict.fromkeys(want))
        t = pq.read_table(str(folder / "test_preds.parquet"), columns=want).to_pandas()
        prog = None
        if "programme" in names:
            pt = pq.read_table(str(folder / "test_preds.parquet"), columns=["unit", "time", "y", "programme"]
                               ).to_pandas()
            prog = pt
        a_v = t[adopted_col].to_numpy(dtype=np.float64)
        a_pre = t[pre_ad].to_numpy(dtype=np.float64) if pre_ad in t.columns else a_v
        tw = t[twin_col].to_numpy(dtype=np.float64)
        tw_pre = t[pre_tw].to_numpy(dtype=np.float64)
        batch = LAL.batch_keys(t["issue"].to_numpy(dtype=np.int64), cadence)
        rec = LAL.decide_alarm(status, a_v, a_pre, tw, tw_pre, batch, gap)
        frame = t.copy()
        frame[LAL.WITH_ALARM_COLUMN] = np.asarray(rec.with_alarm, dtype=np.float64)
        if pre_ad in t.columns:
            frame[LAL.PRE_WITH_ALARM_COLUMN] = np.asarray(rec.pre_with_alarm, dtype=np.float64)
        S = {"tol": float(verdict["hit_tolerance"]), "floor": verdict.get("measurement_error_floor"),
             "kind": record["kind"]}
        rule = M.REFERENCE_DONOR_ROW_MEDIAN if verdict.get("reference_rule") == M.REFERENCE_DONOR_ROW_MEDIAN \
            else M.REFERENCE_OWN_LINK_TREES_OFF
        blocks = {g: int(i) for g, i in derived["R14:overlap_blocks"]["value"]["block_of_group"].items()}
        vw = AP.verdict_with(frame, reference_col, adopted_col, float(verdict["band"]), declined, rule, S["tol"],
                             S["floor"], S["kind"], blocks)
        st = {"pkg": pkg, "lead": 0, "folder": folder, "adoption": adoption, "verdict": verdict, "record": record,
              "derived": derived, "ladder": ladder, "weightings": weightings, "cadence": cadence,
              "adopted_col": adopted_col, "reference_col": reference_col, "twin": twin, "twin_name": LA.arm_name(twin),
              "twin_col": twin_col, "tkind": tkind, "simpler": simpler, "eligible": eligible, "basis": basis,
              "ref": ref, "gap": gap, "status": status, "t": t, "prog": prog, "a_v": a_v, "a_pre": a_pre, "tw": tw,
              "tw_pre": tw_pre, "batch": batch, "rec": rec, "frame": frame, "S": S, "vw": vw, "replayable": True,
              "band": float(verdict["band"])}
        states["%s/0" % pkg] = st
        # leads
        lt = pd.read_csv(folder / "ladder" / "ladder_table.csv",
                         usecols=["lead", "ladder_rows", "adopted", "rows_basis", "column", "line", "mae"])
        SL = {"tol": float(ladder["hit_tolerance"]), "floor": ladder.get("measurement_error_floor"),
              "kind": record["kind"]}
        if sorted(int(x) for x in ladder["leads"]) != LEADS[pkg]:
            raise RuntimeError("%s leads %r" % (pkg, ladder["leads"]))
        for L in LEADS[pkg]:
            la = rj(folder / ("adoption_lead_%d.json" % L))
            pinned = AR._arm(la["pinned"])
            facts = AP.lead_twin(pinned, bool(la["guard_passed"]), weightings)
            sel = lt[(lt["lead"] == L) & (lt["adopted"] == True) & (lt["line"] == "pooled")  # noqa: E712
                     & (lt["rows_basis"] == "all") & (lt["ladder_rows"] == "all")]
            if len(sel) != 1:
                raise RuntimeError("%s lead %d: no single adopted pooled ladder line" % (pkg, L))
            lcol = str(sel["column"].iloc[0])
            tp = folder / "ladder" / ("lead_%d" % L) / "test_preds.parquet"
            lnames = set(pq.read_schema(str(tp)).names)
            lw = ["unit", "group", "time", "year", "issue", "y", "normal", "legal_min", "legal_max", lcol]
            lpre = "pre__" + lcol[len("arm__"):] if lcol.startswith("arm__") else None
            if lpre is not None and lpre in lnames:
                lw.append(lpre)
            ltwin_col = "arm__" + LA.arm_name(facts["twin"])
            lt_frame = pq.read_table(str(tp), columns=list(dict.fromkeys(lw))).to_pandas()
            la_v = lt_frame[lcol].to_numpy(dtype=np.float64)
            la_pre = lt_frame[lpre].to_numpy(dtype=np.float64) if (lpre is not None and lpre in lt_frame.columns) \
                else la_v
            lbatch = LAL.batch_keys(lt_frame["issue"].to_numpy(dtype=np.int64), cadence)
            lst = {"pkg": pkg, "lead": L, "folder": folder, "verdict": verdict, "ladder": ladder, "facts": facts,
                   "adopted_col": lcol, "twin_name": LA.arm_name(facts["twin"]), "tkind": facts["kind"],
                   "simpler": facts["simpler"], "t": lt_frame, "a_v": la_v, "batch": lbatch, "S": SL,
                   "ladder_mae": float(sel["mae"].iloc[0]), "band": float(verdict["band"]),
                   "twin_saved": ltwin_col in lnames}
            if AP.may_be_active(facts):
                if lst["twin_saved"]:
                    raise RuntimeError("%s lead %d: twin saved, not expected" % (pkg, L))
                lst.update(status="not_replayable_twin_not_saved", replayable=False, rec=None)
            else:
                lstatus = LAL.pass_status(facts["declined"], facts["simpler"], None, None)
                lrec = LAL.decide_alarm(lstatus, la_v, la_pre, None, None, lbatch, None)
                if lrec.rows_switched != 0 or not np.array_equal(lrec.with_alarm, la_v, equal_nan=True):
                    raise RuntimeError("%s lead %d: an inert pass switched rows" % (pkg, L))
                lf = lt_frame.copy()
                lf[LAL.WITH_ALARM_COLUMN] = np.asarray(lrec.with_alarm, dtype=np.float64)
                lst.update(status=lstatus, replayable=True, rec=lrec, frame=lf)
            states["%s/%d" % (pkg, L)] = lst
    print("in-process recomputation %.0fs" % (_time.time() - t0))

    PASS_ORDER = ["pm25/0", "pm25/6", "pm25/12", "ndvi/0", "ndvi/6", "ndvi/12", "fire/0", "fire/6", "fire/12",
                  "defo/0", "defo/1", "coral/0", "coral/183", "coral/365"]
    if sorted(PASS_ORDER) != sorted(states):
        raise RuntimeError("pass set")

    # gate-file style lines (subsets), per pass
    def subset_masks(y, edge):
        lab = np.isfinite(y)
        out_ = [("all", "all rows", lab.copy())]
        if edge is not None:
            out_.append(("y_gt_0", "positive label (y > 0)", lab & (y > 0)))
            out_.append(("y_gt_q75", "severe (y > %.6g: q75 of positive donor labels at the lead's fit cut)" % edge,
                         lab & (y > edge)))
            out_.append(("y_ge_50", "severe (y >= %.6g)" % ABS_EDGE, lab & (y >= ABS_EDGE)))
        return out_

    def gate_lines(key):
        st = states[key]
        edge = coral_edges[st["lead"]] if st["pkg"] == "coral" else None
        frame = st["frame"] if st["replayable"] else st["t"]
        cols = [st["adopted_col"]] + ([LAL.WITH_ALARM_COLUMN] if st["replayable"] else [])
        y = frame["y"].to_numpy(dtype=np.float64)
        res = []
        for sid, name, mask in subset_masks(y, edge):
            # the tool scores frame.loc[mask_of_all_rows]; 'all rows' is every saved row (unlabelled rows unscored)
            m = np.ones(y.size, dtype=bool) if sid == "all" else mask
            sc = pooled_mask(frame, m, cols, st["S"])
            res.append({"sid": sid, "subset": name, "n": sc[st["adopted_col"]][1],
                        "mae_without": sc[st["adopted_col"]][0],
                        "mae_with": sc[LAL.WITH_ALARM_COLUMN][0] if st["replayable"] else None})
        return res

    for key in PASS_ORDER:
        states[key]["lines"] = gate_lines(key)

    # ------------------------------------------------------------------ G1: pass facts
    g1 = {"tool_rerun_with_without_bytes_equal": None, "mismatches": [], "spec_mismatches": [], "step_A2": a2}
    gate_ww = GATE / "WITH_WITHOUT.csv"
    re_ww = TOOL_OUT / "WITH_WITHOUT.csv"
    g1["tool_rerun_with_without_sha256"] = sha256_file(re_ww)
    g1["tool_rerun_with_without_bytes_equal"] = re_ww.read_bytes() == gate_ww.read_bytes()
    gdf = pd.read_csv(str(gate_ww), dtype=str, keep_default_na=False)
    rdf = pd.read_csv(str(re_ww), dtype=str, keep_default_na=False)
    g1["gate_lines"] = int(len(gdf))
    if len(gdf) != 23 or not gdf.equals(rdf):
        g1["mismatches"].append("re-run WITH_WITHOUT.csv differs from the gate file as text cells")
    gnum = pd.read_csv(str(gate_ww), float_precision="round_trip")

    def sbool(s):
        return {"True": True, "False": False, "": None}[s]

    def sint(s):
        return None if s == "" else int(float(s))

    def sflt(s):
        return None if s == "" else float(s)

    li = 0
    for key in PASS_ORDER:
        st = states[key]
        for ln in st["lines"]:
            g = gdf.iloc[li]
            li += 1
            exp = {"package": st["pkg"], "lead": str(st["lead"]), "subset": ln["subset"], "status": st["status"],
                   "replayable": st["replayable"], "adopted_column": st["adopted_col"], "twin_arm": st["twin_name"],
                   "twin_kind": st["tkind"], "twin_simpler": st["simpler"]}
            got = {"package": g["package"], "lead": g["lead"], "subset": g["subset"], "status": g["status"],
                   "replayable": sbool(g["replayable"]), "adopted_column": g["adopted_column"],
                   "twin_arm": g["twin_arm"], "twin_kind": g["twin_kind"], "twin_simpler": sbool(g["twin_simpler"])}
            if st["lead"] == 0:
                rec = st["rec"]
                fired = [b.batch for b in rec.batches if b.fired]
                tr = [b.ratio for b in rec.batches if b.tested and b.ratio is not None]
                exp.update(twin_eligible=st["eligible"], reference_gap=st["gap"], batches=len(rec.batches),
                           batches_tested=rec.batches_tested, batches_fired=rec.batches_fired,
                           rows_switched=rec.rows_switched, fired_batches=" ".join(fired),
                           max_ratio_tested=max(tr) if tr else None)
            elif st["replayable"]:
                rec = st["rec"]
                exp.update(twin_eligible=None, reference_gap=None, batches=len(rec.batches),
                           batches_tested=rec.batches_tested, batches_fired=rec.batches_fired,
                           rows_switched=rec.rows_switched, fired_batches="", max_ratio_tested=None)
            else:
                nb = len(set(np.asarray(st["batch"], dtype=str).tolist()))
                exp.update(twin_eligible=None, reference_gap=None, batches=nb, batches_tested=None,
                           batches_fired=None, rows_switched=None, fired_batches="", max_ratio_tested=None)
            got.update(twin_eligible=sbool(g["twin_eligible"]), reference_gap=sflt(g["reference_gap"]),
                       batches=sint(g["batches"]), batches_tested=sint(g["batches_tested"]),
                       batches_fired=sint(g["batches_fired"]), rows_switched=sint(g["rows_switched"]),
                       fired_batches=g["fired_batches"], max_ratio_tested=sflt(g["max_ratio_tested"]))
            exp.update(n=ln["n"], mae_without=ln["mae_without"], mae_with=ln["mae_with"])
            got.update(n=sint(g["n"]), mae_without=sflt(g["mae_without"]), mae_with=sflt(g["mae_with"]))
            for k in exp:
                e, o = exp[k], got[k]
                ok = same_float(e, o) if isinstance(e, float) or isinstance(o, float) else (e == o)
                if not ok:
                    g1["mismatches"].append({"line": li, "pass": key, "field": k, "expected_recomputed": e,
                                             "gate": o})
            # gate float columns read round-trip must equal the text parse
            gn = gnum.iloc[li - 1]
            for k in ("mae_without", "mae_with", "reference_gap", "max_ratio_tested"):
                if not same_float(gn[k], got[k]):
                    g1["mismatches"].append({"line": li, "field": k, "round_trip_parse": float(gn[k]),
                                             "text_parse": got[k]})
            # the spec's printed values
            sp = SPEC_G1.get(key, {}) if ln["sid"] == "all" else {}
            sv = SPEC_G1_SUBSETS.get((key, ln["sid"]))
            if sv is not None:
                sp = {"mae_without": sv[1]}
                if sv[0] is not None:
                    sp["n"] = sv[0]
                if sv[2] is not None:
                    sp["mae_with"] = sv[2]
            for k, v in sp.items():
                if k == "reference_rows":
                    o = st["ref"]["rows"]
                elif k == "batches_ge30":
                    cnt = pd.Series(np.asarray(st["batch"], dtype=str)).value_counts()
                    o = int((cnt >= 30).sum())
                else:
                    o = exp[k]
                ok = same_float(v, o) if isinstance(v, float) else (v == o)
                if not ok:
                    g1["spec_mismatches"].append({"pass": key, "subset": ln["sid"], "field": k, "spec": v,
                                                  "recomputed": o})
    if li != len(gdf):
        g1["mismatches"].append("line count %d vs gate %d" % (li, len(gdf)))
    # spec: coral 183 has 49 batches, 32 of them >= 30 rows; defo 1: 4 of 4
    if g1["mismatches"] or g1["spec_mismatches"] or not g1["tool_rerun_with_without_bytes_equal"]:
        fail("G1", g1)
    gates["G1"] = {"pass": True, "details": g1}
    print("G1 pass")

    # ------------------------------------------------------------------ G2: batch records, eligibility, reference
    g2 = {"mismatches": [], "rerun_json_bytes_equal": {}, "inert_max_computed_ratio": {}}
    for pkg in PACKAGES:
        st = states["%s/0" % pkg]
        gpath = GATE / pkg / RUN_IDS[pkg] / "alarm_replay.json"
        rpath = TOOL_OUT / pkg / RUN_IDS[pkg] / "alarm_replay.json"
        g2["rerun_json_bytes_equal"][pkg] = rpath.read_bytes() == gpath.read_bytes()
        if not g2["rerun_json_bytes_equal"][pkg]:
            g2["mismatches"].append({"pkg": pkg, "item": "re-run alarm_replay.json bytes differ"})
        gd = rj(gpath)
        rec = st["rec"]
        mine = [{"batch": b.batch, "rows": b.rows, "gap": b.gap, "ratio": b.ratio, "tested": b.tested,
                 "fired": b.fired} for b in rec.batches]
        if len(mine) != len(gd["batches"]):
            g2["mismatches"].append({"pkg": pkg, "item": "batch count", "mine": len(mine),
                                     "gate": len(gd["batches"])})
        for m, g in zip(mine, gd["batches"]):
            for k in ("batch", "rows", "tested", "fired"):
                if m[k] != g[k]:
                    g2["mismatches"].append({"pkg": pkg, "batch": m["batch"], "field": k, "mine": m[k], "gate": g[k]})
            for k in ("gap", "ratio"):
                if not same_float(m[k], g[k]):
                    g2["mismatches"].append({"pkg": pkg, "batch": m["batch"], "field": k, "mine": m[k], "gate": g[k]})
        eb = gd["eligibility_basis"]
        for k in ("twin_mae", "baseline_mae"):
            if not same_float(st["basis"][k], eb[k]):
                g2["mismatches"].append({"pkg": pkg, "field": k, "mine": st["basis"][k], "gate": eb[k]})
        for k in ("baseline", "twin_key", "eligible"):
            if st["basis"][k] != eb[k]:
                g2["mismatches"].append({"pkg": pkg, "field": k, "mine": st["basis"][k], "gate": eb[k]})
        sp = SPEC_G2_ELIG[pkg]
        if not (same_float(sp[0], eb["twin_mae"]) and same_float(sp[1], eb["baseline_mae"]) and sp[2] == eb["eligible"]):
            g2["mismatches"].append({"pkg": pkg, "item": "spec eligibility values", "spec": sp,
                                     "gate": [eb["twin_mae"], eb["baseline_mae"], eb["eligible"]]})
        gr = gd["reference"]
        if gr["columns"] != st["ref"]["columns"] or gr["rows"] != st["ref"]["rows"] or \
                not same_float(gr["gap"], st["ref"]["gap"]):
            g2["mismatches"].append({"pkg": pkg, "item": "reference", "mine": [st["ref"]["columns"], st["ref"]["rows"],
                                                                             st["ref"]["gap"]], "gate": gr})
        if pkg in SPEC_G2_INERT_MAX:
            mx = max(b.ratio for b in rec.batches if b.ratio is not None)
            g2["inert_max_computed_ratio"][pkg] = {"max_ratio_computed": mx, "batches_tested": rec.batches_tested}
            if not same_float(mx, SPEC_G2_INERT_MAX[pkg]) or rec.batches_tested != 0:
                g2["mismatches"].append({"pkg": pkg, "item": "inert max ratio", "mine": mx,
                                         "spec": SPEC_G2_INERT_MAX[pkg]})
    if g2["mismatches"]:
        fail("G2", g2)
    gates["G2"] = {"pass": True, "details": g2}
    print("G2 pass")

    # ------------------------------------------------------------------ G3: scores csv lines
    g3 = {"mismatches": [], "rerun_scores_bytes_equal": {}}
    for pkg in PACKAGES:
        st = states["%s/0" % pkg]
        gpath = GATE / pkg / RUN_IDS[pkg] / "alarm_replay_scores.csv"
        rpath = TOOL_OUT / pkg / RUN_IDS[pkg] / "alarm_replay_scores.csv"
        g3["rerun_scores_bytes_equal"][pkg] = rpath.read_bytes() == gpath.read_bytes()
        if not g3["rerun_scores_bytes_equal"][pkg]:
            g3["mismatches"].append({"pkg": pkg, "item": "re-run scores csv bytes differ"})
        gs = pd.read_csv(str(gpath), float_precision="round_trip", keep_default_na=False, dtype={"key": str})
        cols = [st["adopted_col"], LAL.WITH_ALARM_COLUMN, st["reference_col"]]
        mine = {("pooled", ""): pooled(st["frame"], cols, st["S"])}
        for by in ("year", "group"):
            for k, v in keyed(st["frame"], (by,), cols, st["S"]).items():
                mine[(by, str(k[0]))] = v
        if len(mine) != len(gs):
            g3["mismatches"].append({"pkg": pkg, "item": "line count", "mine": len(mine), "gate": len(gs)})
        for _, r in gs.iterrows():
            m = mine.get((r["line"], r["key"]))
            if m is None:
                g3["mismatches"].append({"pkg": pkg, "missing line": [r["line"], r["key"]]})
                continue
            for c, f in ((st["adopted_col"], "mae_without"), (LAL.WITH_ALARM_COLUMN, "mae_with"),
                         (st["reference_col"], "mae_reference")):
                if not same_float(m[c][0], float(r[f])):
                    g3["mismatches"].append({"pkg": pkg, "line": [r["line"], r["key"]], "field": f, "mine": m[c][0],
                                             "gate": float(r[f])})
            if m[st["adopted_col"]][1] != int(r["n"]):
                g3["mismatches"].append({"pkg": pkg, "line": [r["line"], r["key"]], "field": "n"})
        if pkg == "coral":
            for yk, (n, wo, wi) in SPEC_G3.items():
                m = mine[("year", yk + ".0")]
                if not (m[st["adopted_col"]][1] == n and same_float(m[st["adopted_col"]][0], wo)
                        and same_float(m[LAL.WITH_ALARM_COLUMN][0], wi)):
                    g3["mismatches"].append({"item": "spec coral year", "year": yk, "spec": [n, wo, wi],
                                             "mine": [m[st["adopted_col"]][1], m[st["adopted_col"]][0],
                                                      m[LAL.WITH_ALARM_COLUMN][0]]})
    if g3["mismatches"]:
        fail("G3", g3)
    gates["G3"] = {"pass": True, "details": g3}
    print("G3 pass")

    # ------------------------------------------------------------------ G4: small batches
    g4 = {"by_nowcast": {}, "mismatches": []}
    for pkg in PACKAGES:
        rec = states["%s/0" % pkg]["rec"]
        small = [b for b in rec.batches if b.rows < int(K.ALARM_MIN_BATCH_ROWS)]
        g4["by_nowcast"][pkg] = {"count": len(small), "rows": int(sum(b.rows for b in small))}
        if pkg == "coral":
            b7 = [b for b in small if b.batch == "2016-07"]
            g4["coral_2016_07"] = {"rows": b7[0].rows, "ratio": b7[0].ratio} if b7 else None
            if len(small) != 15 or sum(b.rows for b in small) != 275 or not b7 or b7[0].rows != 16 or \
                    not same_float(b7[0].ratio, 25.529655201638473):
                g4["mismatches"].append("coral small batches")
        elif small:
            g4["mismatches"].append("%s has small batches" % pkg)
    if g4["mismatches"]:
        fail("G4", g4)
    gates["G4"] = {"pass": True, "details": g4}
    print("G4 pass")

    # ------------------------------------------------------------------ G5: row-level files
    g5 = {"files": {}, "mismatches": []}

    def rows_frame(st):
        t = st["t"]
        base = t[["unit", "group", "time", "year", "issue", "y"]]
        if st["lead"] == 0:
            rec = st["rec"]
            return base.assign(batch=np.asarray(rec.batch, dtype=str), adopted=st["a_v"], twin=st["tw"],
                               with_alarm=np.asarray(rec.with_alarm, dtype=np.float64),
                               fired=np.asarray(rec.fired, dtype=bool))
        if st["replayable"]:
            rec = st["rec"]
            return base.assign(batch=np.asarray(rec.batch, dtype=str), adopted=st["a_v"],
                               with_alarm=np.asarray(rec.with_alarm, dtype=np.float64),
                               fired=np.asarray(rec.fired, dtype=bool))
        return base.assign(batch=np.asarray(st["batch"], dtype=str), adopted=st["a_v"])

    for key in PASS_ORDER:
        st = states[key]
        name = "%s_%s_lead_%d.parquet" % (st["pkg"], RUN_IDS[st["pkg"]], st["lead"])
        gfile = pd.read_parquet(str(GATE / "rows" / name))
        rfile = pd.read_parquet(str(TOOL_OUT / "rows" / name))
        mine = rows_frame(st).reset_index(drop=True)
        rec_ = {"recomputed_equals_gate": bool(gfile.equals(mine)), "rerun_equals_gate": bool(gfile.equals(rfile)),
                "rerun_bytes_equal": (TOOL_OUT / "rows" / name).read_bytes() == (GATE / "rows" / name).read_bytes(),
                "columns": list(gfile.columns), "rows": int(len(gfile))}
        bit = True
        for c in gfile.columns:
            if gfile[c].dtype.kind == "f":
                bit = bit and bits_equal(gfile[c].to_numpy(), mine[c].to_numpy()) and \
                    bits_equal(gfile[c].to_numpy(), rfile[c].to_numpy())
        rec_["floats_bitwise"] = bit
        if list(gfile.columns) != list(mine.columns):
            rec_["recomputed_equals_gate"] = False
        g5["files"][name] = rec_
        if not (rec_["recomputed_equals_gate"] and rec_["rerun_equals_gate"] and bit):
            first = None
            if len(gfile) == len(mine):
                for c in gfile.columns:
                    if c in mine.columns:
                        a_, b_ = gfile[c].to_numpy(), mine[c].to_numpy()
                        diff = np.flatnonzero(~((a_ == b_) | (pd.isna(a_) & pd.isna(b_))))
                        if diff.size:
                            first = {"column": c, "rows": diff[:5].tolist()}
                            break
            g5["mismatches"].append({"file": name, "first_difference": first, "dtypes_gate": gfile.dtypes.astype(
                str).to_dict(), "dtypes_mine": mine.dtypes.astype(str).to_dict()})
    if len(g5["files"]) != 14:
        g5["mismatches"].append("not 14 files")
    if g5["mismatches"]:
        fail("G5", g5)
    gates["G5"] = {"pass": True, "details": g5}
    print("G5 pass")

    # ------------------------------------------------------------------ G6: threshold check (information only)
    thr_recs = {}
    for key in ("coral/0", "defo/0"):
        st = states[key]
        for thr in THRESHOLDS:
            r = LAL.decide_alarm(st["status"], st["a_v"], st["a_pre"], st["tw"], st["tw_pre"], st["batch"], st["gap"],
                                 threshold=thr)
            f = st["frame"][keep_cols(st["frame"], (), [st["adopted_col"]])].copy()
            f[LAL.WITH_ALARM_COLUMN] = np.asarray(r.with_alarm, dtype=np.float64)
            thr_recs[(key, thr)] = (r, f)
    g6 = {"coral": {}, "defo": {}, "mismatches": []}
    for thr in THRESHOLDS:
        r, f = thr_recs[("coral/0", thr)]
        m = pooled(f, [LAL.WITH_ALARM_COLUMN], states["coral/0"]["S"])[LAL.WITH_ALARM_COLUMN][0]
        g6["coral"][repr(thr)] = {"mae_with": m, "rounded_3": "%.3f" % m, "batches_switched": r.batches_fired,
                                  "rows_switched": r.rows_switched}
        if thr in SPEC_G6 and "%.3f" % m != SPEC_G6[thr]:
            g6["mismatches"].append({"threshold": thr, "spec": SPEC_G6[thr], "mine": "%.3f" % m})
        if thr == 2.0 and not same_float(m, 6.119956002798195):
            g6["mismatches"].append("coral 2.0 differs")
        r2, f2 = thr_recs[("defo/0", thr)]
        g6["defo"][repr(thr)] = {"batches_switched": r2.batches_fired, "rows_switched": r2.rows_switched}
        if r2.batches_fired != 0:
            g6["mismatches"].append("defo switched at %r" % thr)
    if g6["mismatches"]:
        fail("G6", g6)
    gates["G6"] = {"pass": True, "details": g6}
    print("G6 pass")

    # ------------------------------------------------------------------ G7: with-alarm verdicts
    g7 = {"mismatches": [], "by_package": {}}

    def verdict_view(vw):
        v = vw["verdict"]
        return {"pooled_mae_without": vw["pooled_mae_adopted"], "pooled_mae_with": vw["pooled_mae"],
                "pooled_mae_reference": vw["pooled_mae_reference"], "verdict_with": v,
                "blocked_jackknife_with": vw["blocked_jackknife"]}

    for pkg in PACKAGES:
        st = states["%s/0" % pkg]
        gd = rj(GATE / pkg / RUN_IDS[pkg] / "alarm_replay.json")["scores"]
        mine = json.loads(json.dumps(M._json_safe(verdict_view(st["vw"])), sort_keys=True))
        same = (mine["verdict_with"] == gd["verdict_with"] and mine["blocked_jackknife_with"] ==
                gd["blocked_jackknife_with"] and mine["pooled_mae_with"] == gd["pooled_mae_with"] and
                mine["pooled_mae_without"] == gd["pooled_mae_without"] and
                mine["pooled_mae_reference"] == gd["pooled_mae_reference"] and
                st["verdict"]["verdict"] == gd["verdict_without"] and float(st["verdict"]["band"]) == gd["band"])
        g7["by_package"][pkg] = {"equal_to_gate": same, "tag_with": mine["verdict_with"].get("tag"),
                                 "tag_without": gd["verdict_without"].get("tag")}
        if not same:
            g7["mismatches"].append({"pkg": pkg, "mine": mine, "gate": gd})
        if pkg != "coral" and mine["pooled_mae_with"] != mine["pooled_mae_without"]:
            g7["mismatches"].append({"pkg": pkg, "item": "with != without where nothing switched"})
    c = rj(GATE / "coral" / RUN_IDS["coral"] / "alarm_replay.json")["scores"]
    vwc, bj, vwo = c["verdict_with"], c["blocked_jackknife_with"], c["verdict_without"]
    chk = [(vwc["tag"], SPEC_G7["tag"]), (vwc["contrast"]["mean"], SPEC_G7["mean"]),
           (vwc["contrast"]["low"], SPEC_G7["low"]), (vwc["contrast"]["high"], SPEC_G7["high"]),
           (vwc["contrast"]["n_groups"], SPEC_G7["n_groups"]), (vwc["groups_better"], SPEC_G7["groups_better"]),
           (vwc["pooled_contrast"], SPEC_G7["pooled_contrast"]), (bj["mean"], SPEC_G7["bj_mean"]),
           (bj["low"], SPEC_G7["bj_low"]), (bj["high"], SPEC_G7["bj_high"]), (bj["n_blocks"], SPEC_G7["bj_n"]),
           (bj["flag"], SPEC_G7["bj_flag"]), (c["band"], SPEC_G7["band"]), (vwo["tag"], SPEC_G7["without_tag"]),
           (vwo["contrast"]["mean"], SPEC_G7["without_mean"]), (vwo["contrast"]["low"], SPEC_G7["without_low"]),
           (vwo["contrast"]["high"], SPEC_G7["without_high"])]
    for got, exp in chk:
        ok = same_float(got, exp) if isinstance(exp, float) else got == exp
        if not ok:
            g7["mismatches"].append({"item": "spec coral verdict value", "spec": exp, "gate": got})
    if g7["mismatches"]:
        fail("G7", g7)
    gates["G7"] = {"pass": True, "details": g7}
    print("G7 pass")

    # ------------------------------------------------------------------ G8: Part 604 cross-check (coral)
    cs = states["coral/0"]
    cf = cs["frame"].copy()
    prog = cs["prog"]
    if not (np.array_equal(prog["unit"].to_numpy(), cf["unit"].to_numpy()) and
            np.array_equal(prog["time"].to_numpy(), cf["time"].to_numpy()) and
            bits_equal(prog["y"].to_numpy(), cf["y"].to_numpy())):
        fail("G8", {"programme column not row-aligned with the replay rows": True})
    gate_rows0 = pd.read_parquet(str(GATE / "rows" / ("coral_%s_lead_0.parquet" % RUN_IDS["coral"])))
    if not (np.array_equal(prog["unit"].to_numpy(), gate_rows0["unit"].to_numpy()) and
            np.array_equal(prog["time"].to_numpy(), gate_rows0["time"].to_numpy()) and
            bits_equal(prog["y"].to_numpy(), gate_rows0["y"].to_numpy())):
        fail("G8", {"programme column not row-aligned with the gate replay rows": True})
    cf["programme"] = prog["programme"].to_numpy()
    a_c, t_c = cs["a_v"], cs["tw"]
    fired_c = np.asarray(cs["rec"].fired, dtype=bool)
    blend_all = 0.5 * a_c + 0.5 * t_c
    blend_batch = a_c.copy()
    blend_batch[fired_c] = blend_all[fired_c]
    cf["arm__blend_batch"] = blend_batch
    cf["arm__blend_all"] = blend_all
    F = {"F1": LAL.WITH_ALARM_COLUMN, "F2": "arm__blend_batch", "F3": cs["twin_col"], "F4": "arm__blend_all"}
    r604 = rj(RESULTS604)
    g8 = {"mismatches": [], "values": {}}
    pc = keyed(cf, ("programme",), [cs["adopted_col"], cs["twin_col"], "arm__blend_all"], cs["S"])
    for p_, (n, m) in SPEC_G8["C"].items():
        mine = pc[(p_,)][cs["adopted_col"]]
        r6 = r604["methods"]["C"]["per_programme"][p_]
        g8["values"]["C/" + p_] = {"n": mine[1], "mae": mine[0]}
        if not (mine[1] == n == r6["n"] and same_float(mine[0], m) and same_float(mine[0], r6["mae"])):
            g8["mismatches"].append({"item": "C " + p_, "mine": mine, "spec": [n, m], "part604": r6})
    for p_ in ("AGRRA", "FRRP", "McClanahan", "Reef_Check"):
        mine = pc[(p_,)][cs["twin_col"]]
        r6 = r604["methods"]["T"]["per_programme"][p_]
        g8["values"]["T/" + p_] = {"n": mine[1], "mae": mine[0]}
        if not (mine[1] == r6["n"] and same_float(mine[0], r6["mae"])):
            g8["mismatches"].append({"item": "T " + p_, "mine": mine, "part604": r6})
    for p_, k in (("FRRP", "T_FRRP"), ("Reef_Check", "T_Reef_Check")):
        if not same_float(pc[(p_,)][cs["twin_col"]][0], SPEC_G8[k]):
            g8["mismatches"].append({"item": "spec " + k})
    pt_ = pooled(cf, [cs["twin_col"], "arm__blend_all"], cs["S"])
    g8["values"]["T_pooled"] = pt_[cs["twin_col"]][0]
    g8["values"]["M2_pooled"] = pt_["arm__blend_all"][0]
    for name_, mine, exps in (("T=M1", pt_[cs["twin_col"]][0], [SPEC_G8["T_pooled"], r604["methods"]["T"]["mae"],
                                                                r604["methods"]["M1"]["mae"]]),
                              ("M2=M3", pt_["arm__blend_all"][0], [SPEC_G8["M2_pooled"], r604["methods"]["M2"]["mae"],
                                                                   r604["methods"]["M3"]["mae"]])):
        for e in exps:
            if not same_float(mine, e):
                g8["mismatches"].append({"item": name_, "mine": mine, "expected": e})
    whole_ratio = LAL.reference_gap(a_c, t_c) / cs["gap"]
    g8["values"]["whole_window_ratio"] = whole_ratio
    if not (same_float(whole_ratio, SPEC_G8["ratio"]) and
            same_float(whole_ratio, r604["sanity_part603"]["alarm_ratio"]["now"])):
        g8["mismatches"].append({"item": "whole-window ratio", "mine": whole_ratio, "spec": SPEC_G8["ratio"]})
    # information (not gating): per-year values of C, T, M2 against Part 604
    info = {}
    py_ = keyed(cf, ("year",), [cs["adopted_col"], cs["twin_col"], "arm__blend_all"], cs["S"])
    for meth, col in (("C", cs["adopted_col"]), ("T", cs["twin_col"]), ("M2", "arm__blend_all")):
        for yk, v in r604["methods"][meth]["per_year"].items():
            mine = py_[(float(yk),)][col][0]
            info["%s/%s" % (meth, yk)] = {"mine": mine, "part604": v, "bit_equal": same_float(mine, v)}
    g8["information_per_year"] = info
    if g8["mismatches"]:
        fail("G8", g8)
    gates["G8"] = {"pass": True, "details": g8}
    print("G8 pass")

    # ------------------------------------------------------------------ G9: history (information)
    h = pd.read_csv(str(HIST / "WITH_WITHOUT.csv"), dtype=str, keep_default_na=False)
    g = pd.read_csv(str(gate_ww), dtype=str, keep_default_na=False)
    cols_ = [c for c in g.columns if c != "note"]
    g9 = {"same_shape": h.shape == g.shape, "same_columns": list(h.columns) == list(g.columns)}
    g9["equal_except_note"] = bool(g9["same_shape"] and g9["same_columns"] and h[cols_].equals(g[cols_]))
    g9["note_differs_on_lines"] = int((h["note"] != g["note"]).sum()) if g9["same_shape"] else None
    gates["G9"] = {"pass": bool(g9["equal_except_note"]), "details": g9}
    if not g9["equal_except_note"]:
        fail("G9", g9)
    print("G9 pass; gate complete %.0fs" % (_time.time() - t0))

    # =================================================================================================================
    # Section 6 (POST HOC). Only reached when G0-G9 passed.
    # =================================================================================================================
    W = LAL.WITH_ALARM_COLUMN
    MINR = int(K.ALARM_MIN_BATCH_ROWS)
    THR = float(K.ALARM_RATIO_THRESHOLD)

    def flag(wo, wi):
        if same_float(wo, wi):
            return "same"
        return "better" if wi < wo else "worse"

    # ---------------- Q1 passes
    for key in PASS_ORDER:
        st = states[key]
        frame = st["frame"] if st["replayable"] else st["t"]
        y = frame["y"].to_numpy(dtype=np.float64)
        lab = np.isfinite(y)
        bk = np.asarray(st["batch"] if st["lead"] != 0 else st["rec"].batch, dtype=str)
        cnt = pd.Series(bk).value_counts()
        e = {"package": st["pkg"], "run": RUN_IDS[st["pkg"]], "lead": st["lead"],
             "pass": "nowcast" if st["lead"] == 0 else "lead %d" % st["lead"],
             "status": st["status"], "plain_status": PLAIN_STATUS[st["status"]],
             "adopted_column": st["adopted_col"], "twin_arm": st["twin_name"], "twin_kind": st["tkind"],
             "twin_simpler": st["simpler"], "replayable": st["replayable"],
             "saved_rows": int(y.size), "labelled_rows": int(lab.sum()), "batches": int(cnt.size),
             "batches_ge30": int((cnt >= MINR).sum()), "saved_rows_in_small_batches": int(cnt[cnt < MINR].sum()),
             "band": st["band"]}
        if e["status"] != EXPECTED_STATUS[key]:
            raise RuntimeError("status %s %s" % (key, e["status"]))
        if st["lead"] == 0:
            rec = st["rec"]
            fired = np.asarray(rec.fired, dtype=bool)
            e["twin_guard"] = bool(st["eligible"])
            e["twin_guard_basis"] = {"twin_key": st["basis"]["twin_key"], "twin_mae": st["basis"]["twin_mae"],
                                     "baseline": st["basis"]["baseline"],
                                     "baseline_mae": st["basis"]["baseline_mae"]}
            e["reference_gap"] = st["gap"]
            e["reference_rows"] = st["ref"]["rows"]
            e["batches_tested"] = rec.batches_tested
            e["batches_switched"] = rec.batches_fired
            e["saved_rows_switched"] = rec.rows_switched
            e["labelled_rows_switched"] = int((fired & lab).sum())
            e["rows_value_changed"] = int((fired & (st["tw"] != st["a_v"])).sum())
            tr = [b.ratio for b in rec.batches if b.tested and b.ratio is not None]
            g30 = [b.ratio for b in rec.batches if b.rows >= MINR and b.ratio is not None]
            e["max_ratio_tested"] = max(tr) if tr else None
            e["max_ratio_ge30"] = max(g30) if g30 else None
            e["max_ratio_ge30_note"] = ("the rule could act" if st["status"] == "active"
                                        else "information only: the rule could not act")
            e["switched_batches"] = [b.batch for b in rec.batches if b.fired]
            sc = pooled(frame, [st["adopted_col"], W], st["S"])
        else:
            e["twin_guard"] = "not saved" if not st["replayable"] else "not needed"
            e["twin_guard_basis"] = None
            e["reference_gap"] = None
            e["reference_rows"] = None
            e["max_ratio_tested"] = None
            e["max_ratio_ge30"] = None
            e["max_ratio_ge30_note"] = "no twin predictions at this lead: no ratio exists"
            e["switched_batches"] = [] if st["replayable"] else None
            if st["replayable"]:
                rec = st["rec"]
                e["batches_tested"] = rec.batches_tested
                e["batches_switched"] = rec.batches_fired
                e["saved_rows_switched"] = rec.rows_switched
                e["labelled_rows_switched"] = int((np.asarray(rec.fired) & lab).sum())
                e["rows_value_changed"] = 0
                sc = pooled(frame, [st["adopted_col"], W], st["S"])
            else:
                e["batches_tested"] = None
                e["batches_switched"] = None
                e["saved_rows_switched"] = None
                e["labelled_rows_switched"] = None
                e["rows_value_changed"] = None
                sc = pooled(frame, [st["adopted_col"]], st["S"])
        e["n_scored"] = sc[st["adopted_col"]][1]
        e["mae_without"] = sc[st["adopted_col"]][0]
        if st["replayable"]:
            e["mae_with"] = sc[W][0]
            e["change"] = e["mae_with"] - e["mae_without"]
            e["change_pct"] = 100.0 * e["change"] / e["mae_without"]
            e["change_in_band_units"] = e["change"] / st["band"]
            if st["lead"] != 0 or rec.rows_switched == 0:
                if not same_float(e["mae_with"], e["mae_without"]):
                    raise RuntimeError("%s: nothing switched but with != without" % key)
        else:
            e["mae_with"] = e["change"] = e["change_pct"] = e["change_in_band_units"] = None
            if not same_float(e["mae_without"], st["ladder_mae"]) and \
                    not math.isclose(e["mae_without"], st["ladder_mae"], rel_tol=1e-12):
                raise RuntimeError("%s ladder MAE" % key)
        e["post_hoc"] = True
        e["circular"] = st["pkg"] == "coral"
        out["passes"][key] = e
    print("Q1 done")

    # ---------------- Q2 / Q8 per-batch tables (nowcasts)
    for pkg in PACKAGES:
        key = "%s/0" % pkg
        st = states[key]
        rec = st["rec"]
        fr = st["frame"].copy()
        fr["batch"] = np.asarray(rec.batch, dtype=str)
        kb = keyed(fr, ("batch",), [st["adopted_col"], W], st["S"])
        idx_of = fr.groupby("batch").indices
        yarr = fr["year"].to_numpy()
        larr = np.isfinite(fr["y"].to_numpy(dtype=np.float64))
        yr = {b: sorted(set(yarr[np.asarray(ix)].tolist())) for b, ix in idx_of.items()}
        lab_n = {b: int(larr[np.asarray(ix)].sum()) for b, ix in idx_of.items()}
        for b in rec.batches:
            years = yr[b.batch]
            if len(years) != 1:
                raise RuntimeError("%s batch %s spans years %r" % (pkg, b.batch, years))
            if pkg == "coral" and int(years[0]) != int(b.batch[:4]):
                raise RuntimeError("coral batch %s year %r" % (b.batch, years))
            m = kb[(b.batch,)]
            out["batches"]["%s/%s" % (key, b.batch)] = {
                "package": pkg, "lead": 0, "batch": b.batch, "saved_rows": b.rows,
                "labelled_rows": int(lab_n[b.batch]), "year": year_key(years[0]), "gap": b.gap, "ratio": b.ratio,
                "tested": b.tested, "switched": b.fired, "small_batch": b.rows < MINR,
                "ratio_above_threshold": bool(b.ratio is not None and b.ratio > THR),
                "n_scored": m[st["adopted_col"]][1], "mae_without": m[st["adopted_col"]][0],
                "mae_with": m[W][0],
                "note": ("tested in the code's sense" if b.tested else
                         ("not tested: fewer than 30 saved rows" if b.rows < MINR and st["status"] == "active" else
                          "not tested: the rule cannot act at this pass (ratio is information only)"))}
        st["batch_years"] = {b: year_key(v[0]) for b, v in yr.items()}
    print("Q2 done")

    # ---------------- Q8 small batches
    for pkg in PACKAGES:
        key = "%s/0" % pkg
        st = states[key]
        rec = st["rec"]
        y = st["t"]["y"].to_numpy(dtype=np.float64)
        bk = np.asarray(rec.batch, dtype=str)
        small = [b for b in rec.batches if b.rows < MINR]
        items = []
        for b in small:
            items.append({"batch": b.batch, "saved_rows": b.rows,
                          "labelled_rows": int(np.isfinite(y[bk == b.batch]).sum()), "ratio": b.ratio,
                          "ratio_above_threshold": bool(b.ratio is not None and b.ratio > THR)})
        above = [b for b in small if b.ratio is not None and b.ratio > THR]
        e = {"pass_status": st["status"], "small_batches": items, "count": len(small),
             "saved_rows": int(sum(b.rows for b in small)),
             "largest_ratio": max([b.ratio for b in small if b.ratio is not None]) if small else None,
             "above_threshold_count": len(above), "above_threshold_saved_rows": int(sum(b.rows for b in above)),
             "information_only": True}
        if pkg == "coral":
            ab = set(b.batch for b in above)
            cfm = np.asarray(rec.fired, dtype=bool) | np.isin(bk, list(ab))
            col = st["a_v"].copy()
            col[cfm] = st["tw"][cfm]
            f = st["frame"][keep_cols(st["frame"], (), [st["adopted_col"]])].copy()
            f["arm__small_counterfactual"] = col
            m = pooled(f, ["arm__small_counterfactual"], st["S"])["arm__small_counterfactual"][0]
            e["counterfactual_info_only"] = {
                "label": "INFORMATION ONLY: pooled MAE if the small batches with ratio > 2.0 had also switched "
                         "(the 30-row floor stays fixed; this is not the rule)",
                "rows_switched": int(cfm.sum()), "batches_switched": rec.batches_fired + len(ab),
                "pooled_mae_with": m, "change_vs_without": m - out["passes"][key]["mae_without"],
                "change_vs_rule": m - out["passes"][key]["mae_with"]}
        out["small_batches"][key] = e
    for key in ("defo/1", "coral/183"):
        st = states[key]
        cnt = pd.Series(np.asarray(st["batch"], dtype=str)).value_counts()
        out["small_batches"][key] = {"pass_status": st["status"], "batches": int(cnt.size),
                                     "small_count": int((cnt < MINR).sum()),
                                     "small_saved_rows": int(cnt[cnt < MINR].sum()),
                                     "note": "not replayable: the twin was not saved, so no ratio exists"}
    print("Q8 done")

    # ---------------- Q3 by year (every replayable pass)
    worse_years = []
    for key in PASS_ORDER:
        st = states[key]
        if not st["replayable"]:
            continue
        frame = st["frame"]
        ky = keyed(frame, ("year",), [st["adopted_col"], W], st["S"])
        bk = np.asarray(st["rec"].batch, dtype=str)
        fired = np.asarray(st["rec"].fired, dtype=bool)
        yrs = frame["year"].to_numpy()
        bres = {b.batch: b for b in st["rec"].batches}
        for (yv,), m in sorted(ky.items(), key=lambda kv: float(kv[0][0])):
            ym = yrs == yv
            in_year = sorted(set(bk[ym].tolist()))
            wo, wi = m[st["adopted_col"]][0], m[W][0]
            fl = flag(wo, wi)
            e = {"n": m[st["adopted_col"]][1], "mae_without": wo, "mae_with": wi, "change": wi - wo, "flag": fl,
                 "batches": len(in_year), "batches_tested": sum(1 for b in in_year if bres[b].tested),
                 "batches_switched": sum(1 for b in in_year if bres[b].fired),
                 "rows_switched": int((fired & ym).sum()),
                 "batches_rule": ("lead 0: each batch lies in one year (asserted)" if st["lead"] == 0 else
                                  "batches with at least one row in this year (a lead's issue batch can span two "
                                  "target years)")}
            if st["lead"] == 0:
                spans = [b for b in in_year if st["batch_years"][b] != year_key(yv)]
                if spans:
                    raise RuntimeError("%s: batch outside its year" % key)
            if st["rec"].rows_switched == 0 and fl != "same":
                raise RuntimeError("%s %r: nothing switched but with != without" % (key, yv))
            out["by_year"]["%s/%s" % (key, year_key(yv))] = e
            if fl == "worse":
                worse_years.append("%s/%s" % (key, year_key(yv)))
    out["by_year_worse"] = worse_years
    print("Q3 done")

    # ---------------- Q4 coral programme and programme x year
    cfa = cf  # coral frame with programme, F2, F4 columns
    bkc = np.asarray(cs["rec"].batch, dtype=str)
    progs = cfa["programme"].to_numpy()
    yrs_c = cfa["year"].to_numpy()
    kp = keyed(cfa, ("programme",), [cs["adopted_col"], W], cs["S"])
    for (p_,), m in sorted(kp.items()):
        pm = progs == p_
        wo, wi = m[cs["adopted_col"]][0], m[W][0]
        e = {"n": m[cs["adopted_col"]][1], "mae_without": wo, "mae_with": wi, "change": wi - wo,
             "flag": flag(wo, wi), "rows_switched": int((fired_c & pm).sum()),
             "switched_batches_holding": len(set(bkc[fired_c & pm].tolist())),
             "note": "n = 1, not interpretable" if p_ == "AGRRA" else None,
             "post_hoc": True, "circular": True}
        out["coral_programme"][str(p_)] = e
    kpy = keyed(cfa, ("programme", "year"), [cs["adopted_col"], W], cs["S"])
    for (p_, yv), m in sorted(kpy.items(), key=lambda kv: (kv[0][0], float(kv[0][1]))):
        pm = (progs == p_) & (yrs_c == yv)
        wo, wi = m[cs["adopted_col"]][0], m[W][0]
        e = {"programme": p_, "year": year_key(yv), "n": m[cs["adopted_col"]][1], "mae_without": wo,
             "mae_with": wi, "change": wi - wo, "flag": flag(wo, wi), "rows_switched": int((fired_c & pm).sum()),
             "switched_batches_holding": len(set(bkc[fired_c & pm].tolist())),
             "note": "n = 1, not interpretable" if p_ == "AGRRA" else None}
        out["coral_programme_year"]["%s/%s" % (p_, year_key(yv))] = e
    print("Q4 done")

    # ---------------- Q5 contributions
    Pc = out["passes"]["coral/0"]
    N = Pc["n_scored"]
    dpool = Pc["mae_with"] - Pc["mae_without"]
    contrib = {"N": N, "pooled_mae_without": Pc["mae_without"], "pooled_mae_with": Pc["mae_with"],
               "pooled_change": dpool, "formula": "contrib = (n_cell / N) x (MAE_with(cell) - MAE_without(cell)); "
                                                  "share = contrib / pooled change",
               "by_programme": {}, "by_programme_year": {}}
    for label, src, dst in (("programme", out["coral_programme"], "by_programme"),
                            ("programme_year", out["coral_programme_year"], "by_programme_year")):
        s = 0.0
        for k, v in src.items():
            cval = (v["n"] / N) * (v["mae_with"] - v["mae_without"])
            s += cval
            contrib[dst][k] = {"n": v["n"], "change": v["mae_with"] - v["mae_without"], "contrib": cval,
                               "share": cval / dpool, "share_pct": 100.0 * cval / dpool}
        contrib["sum_" + label] = s
        contrib["residual_" + label] = s - dpool
    out["contributions"] = contrib
    print("Q5 done")

    # ---------------- Q7 subsets (coral nowcast and coral leads) and Q6 forms
    def subset_defs(y, edge):
        lab = np.isfinite(y)
        if (y[lab] < 0).any():
            raise RuntimeError("negative coral label")
        return [("all", "all labelled rows", None, lab),
                ("y_gt_0", "y > 0 (bleached)", 0.0, lab & (y > 0)),
                ("y_eq_0", "y == 0 (complement of y > 0)", 0.0, lab & (y == 0)),
                ("y_ge_50", "y >= 50", ABS_EDGE, lab & (y >= ABS_EDGE)),
                ("y_lt_50", "y < 50 (complement of y >= 50)", ABS_EDGE, lab & (y < ABS_EDGE)),
                ("y_gt_q75", "y > %r (the lead's q75 of positive donor labels)" % edge, edge, lab & (y > edge)),
                ("y_le_q75", "y <= %r (complement)" % edge, edge, lab & (y <= edge))]

    for key in ("coral/0", "coral/183", "coral/365"):
        st = states[key]
        frame = st["frame"] if st["replayable"] else st["t"]
        y = frame["y"].to_numpy(dtype=np.float64)
        defs = subset_defs(y, coral_edges[st["lead"]])
        lab_total = int(np.isfinite(y).sum())
        for a_, b_ in (("y_gt_0", "y_eq_0"), ("y_ge_50", "y_lt_50"), ("y_gt_q75", "y_le_q75")):
            na = int(dict((d[0], d[3]) for d in defs)[a_].sum())
            nb = int(dict((d[0], d[3]) for d in defs)[b_].sum())
            if na + nb != lab_total:
                raise RuntimeError("subset complement %s %s" % (a_, b_))
        fired = np.asarray(st["rec"].fired, dtype=bool) if st["replayable"] else None
        for sid, label, edge, mask in defs:
            cols = [st["adopted_col"]] + ([W] if st["replayable"] else [])
            sc = pooled_mask(frame, mask, cols, st["S"])
            e = {"label": label, "edge": edge, "n": sc[st["adopted_col"]][1],
                 "mae_without": sc[st["adopted_col"]][0],
                 "mae_with": sc[W][0] if st["replayable"] else None,
                 "rows_switched_in_subset": int((fired & mask).sum()) if fired is not None else None,
                 "outcome_defined": sid != "all",
                 "selection": OUTCOME_LABEL if sid != "all" else "all labelled rows",
                 "post_hoc": True, "circular": True}
            e["change"] = (e["mae_with"] - e["mae_without"]) if e["mae_with"] is not None else None
            out["subsets"]["%s/%s" % (key, sid)] = e
    print("Q7 done")

    yc = cfa["y"].to_numpy(dtype=np.float64)
    defs0 = subset_defs(yc, coral_edges[0])
    form_labels = {"F1": "per-batch switch: the fixed v2 rule (= the with-alarm column)",
                   "F2": "per-batch even blend on the same 11 switched batches (INFORMATION ONLY, not the rule)",
                   "F3": "whole-window switch, the twin on every row (Part 603/604 M1; cross-check only; not the "
                         "alarm's value (C6))",
                   "F4": "whole-window even blend on every row (Part 603 blend = Part 604 M2 = M3; cross-check only)"}
    allcols = [cs["adopted_col"]] + [F[k] for k in ("F1", "F2", "F3", "F4")]
    pool_all = pooled(cfa, allcols, cs["S"])
    by_y = keyed(cfa, ("year",), allcols, cs["S"])
    by_p = keyed(cfa, ("programme",), allcols, cs["S"])
    sub_sc = {sid: pooled_mask(cfa, mask, allcols, cs["S"]) for sid, _, _, mask in defs0}
    for fk in ("F1", "F2", "F3", "F4"):
        col = F[fk]
        vals = cfa[col].to_numpy(dtype=np.float64)
        e = {"label": form_labels[fk], "column": col,
             "pooled": {"n": pool_all[col][1], "mae": pool_all[col][0],
                        "change_vs_without": pool_all[col][0] - pool_all[cs["adopted_col"]][0]},
             "by_year": {year_key(k[0]): {"n": v[col][1], "mae": v[col][0],
                                          "change_vs_without": v[col][0] - v[cs["adopted_col"]][0],
                                          "flag": flag(v[cs["adopted_col"]][0], v[col][0])}
                         for k, v in sorted(by_y.items(), key=lambda kv: float(kv[0][0]))},
             "by_programme": {str(k[0]): {"n": v[col][1], "mae": v[col][0],
                                          "change_vs_without": v[col][0] - v[cs["adopted_col"]][0],
                                          "flag": flag(v[cs["adopted_col"]][0], v[col][0])}
                              for k, v in sorted(by_p.items())},
             "subsets": {sid: {"n": sub_sc[sid][col][1], "mae": sub_sc[sid][col][0],
                               "change_vs_without": sub_sc[sid][col][0] - sub_sc[sid][cs["adopted_col"]][0],
                               "selection": OUTCOME_LABEL if sid != "all" else "all labelled rows"}
                         for sid, _, _, _ in defs0},
             "rows_differing": int((vals != cs["a_v"]).sum()),
             "post_hoc": True, "circular": True}
        out["forms"][fk] = e
    # defo: nothing switched, so F1 = F2 = without (asserted); F3/F4 not computed for defo
    ds = states["defo/0"]
    d_f2 = ds["a_v"].copy()
    dfired = np.asarray(ds["rec"].fired, dtype=bool)
    d_f2[dfired] = (0.5 * ds["a_v"] + 0.5 * ds["tw"])[dfired]
    d_ok = bits_equal(ds["frame"][W].to_numpy(), ds["a_v"]) and bits_equal(d_f2, ds["a_v"])
    if not d_ok or dfired.any():
        raise RuntimeError("defo F1/F2 differ from without")
    out["forms"]["F1"]["defo_0_equals_without"] = True
    out["forms"]["F2"]["defo_0_equals_without"] = True
    # cross-checks of F3/F4 against Part 604 (gate G8 already passed)
    out["forms"]["F3"]["equals_part604_M1"] = same_float(pool_all[F["F3"]][0], r604["methods"]["M1"]["mae"])
    out["forms"]["F4"]["equals_part604_M2_M3"] = same_float(pool_all[F["F4"]][0], r604["methods"]["M2"]["mae"])
    if not same_float(pool_all[F["F1"]][0], Pc["mae_with"]):
        raise RuntimeError("F1 pooled differs from the with-alarm MAE")
    print("Q6 done")

    # ---------------- Q9 thresholds (information only)
    for key in ("coral/0", "defo/0"):
        st = states[key]
        for thr in THRESHOLDS:
            r, f = thr_recs[(key, thr)]
            m = pooled(f, [st["adopted_col"], W], st["S"])
            e = {"threshold": thr, "batches_switched": r.batches_fired, "rows_switched": r.rows_switched,
                 "switched_batches": [b.batch for b in r.batches if b.fired],
                 "mae_without": m[st["adopted_col"]][0], "mae_with": m[W][0],
                 "change": m[W][0] - m[st["adopted_col"]][0],
                 "information_only": thr != 2.0,
                 "note": "the fixed rule" if thr == 2.0 else "INFORMATION ONLY: the threshold 2.0 stays fixed"}
            if key == "coral/0":
                f2 = f.copy()
                ky = keyed(f2, ("year",), [st["adopted_col"], W], st["S"])
                e["by_year"] = {year_key(k[0]): {"n": v[W][1], "mae_without": v[st["adopted_col"]][0],
                                                 "mae_with": v[W][0],
                                                 "change": v[W][0] - v[st["adopted_col"]][0],
                                                 "flag": flag(v[st["adopted_col"]][0], v[W][0])}
                                for k, v in sorted(ky.items(), key=lambda kv: float(kv[0][0]))}
            if thr == 2.0 and not (r.batches_fired == st["rec"].batches_fired and
                                   same_float(m[W][0], out["passes"][key]["mae_with"])):
                raise RuntimeError("threshold 2.0 differs from the rule")
            out["threshold_check"]["%s/%r" % (key, thr)] = e
    print("Q9 done")

    # ---------------- Q10 silence and firing
    for pkg in PACKAGES:
        key = "%s/0" % pkg
        P = out["passes"][key]
        if P["batches_switched"]:
            why = "switched %d of %d tested batches (%d saved rows)" % (P["batches_switched"], P["batches_tested"],
                                                                        P["saved_rows_switched"])
            kind = "active, switched"
        elif P["status"] == "active":
            why = "can switch, but no tested batch's ratio exceeded 2.0"
            kind = "active, nothing switched"
        else:
            why = PLAIN_STATUS[P["status"]]
            kind = "inert (cannot act)"
        out["silence"][key] = {"switched_any": "yes" if P["batches_switched"] else "no", "class": kind, "why": why,
                               "status": P["status"], "batches_tested": P["batches_tested"],
                               "largest_ratio_tested": P["max_ratio_tested"],
                               "largest_ratio_ge30_information": P["max_ratio_ge30"]}
    print("Q10 done")

    # ---------------- Q11 regions (coral) and verdict blocks
    kg = keyed(cs["frame"], ("group",), [cs["adopted_col"], W], cs["S"])
    gate_sc = pd.read_csv(str(GATE / "coral" / RUN_IDS["coral"] / "alarm_replay_scores.csv"),
                          float_precision="round_trip", keep_default_na=False, dtype={"key": str})
    gate_groups = {r["key"]: r for _, r in gate_sc[gate_sc["line"] == "group"].iterrows()}
    lines, cnts = {}, {"better": 0, "same": 0, "worse": 0}
    for (g_,), m in sorted(kg.items()):
        wo, wi = m[cs["adopted_col"]][0], m[W][0]
        fl = flag(wo, wi)
        cnts[fl] += 1
        gr = gate_groups[str(g_)]
        eq = same_float(wo, float(gr["mae_without"])) and same_float(wi, float(gr["mae_with"])) and \
            m[cs["adopted_col"]][1] == int(gr["n"])
        if not eq:
            raise RuntimeError("region line differs from the gate scores: %s" % g_)
        lines[str(g_)] = {"n": m[cs["adopted_col"]][1], "mae_without": wo, "mae_with": wi, "change": wi - wo,
                          "flag": fl, "equals_gate_scores_line": eq}
    out["regions"]["coral/0"] = {"lines": lines, "regions": len(lines), **cnts, "post_hoc": True, "circular": True,
                                 "note": "S5 use is an owner item (O2)"}
    for pkg in PACKAGES:
        st = states["%s/0" % pkg]
        vw = json.loads(json.dumps(M._json_safe(verdict_view(st["vw"])), sort_keys=True))
        out["verdicts"]["%s/0" % pkg] = {
            "with": {"pooled_mae_with": vw["pooled_mae_with"], "pooled_mae_without": vw["pooled_mae_without"],
                     "pooled_mae_reference": vw["pooled_mae_reference"], "verdict": vw["verdict_with"],
                     "blocked_jackknife": vw["blocked_jackknife_with"]},
            "without_locked": {"verdict": st["verdict"]["verdict"],
                               "blocked_jackknife": st["verdict"].get("blocked_jackknife")},
            "band": st["band"], "post_hoc": True, "circular": pkg == "coral"}
    print("Q11 done")

    # ---------------- Q12 row-level outputs
    written = {}
    for key in PASS_ORDER:
        st = states[key]
        if not st["replayable"]:
            continue
        t = st["t"]
        rec = st["rec"]
        df = t[["unit", "group", "time", "year", "issue", "y"]].copy()
        df["batch"] = np.asarray(rec.batch, dtype=str)
        df["adopted"] = st["a_v"]
        df["twin"] = st["tw"] if st["lead"] == 0 else np.full(st["a_v"].size, np.nan)
        df["with_alarm"] = np.asarray(rec.with_alarm, dtype=np.float64)
        df["fired"] = np.asarray(rec.fired, dtype=bool)
        if key == "coral/0":
            df["programme"] = cfa["programme"].to_numpy()
            df["blend_batch"] = cfa["arm__blend_batch"].to_numpy()
            df["twin_all"] = cfa[cs["twin_col"]].to_numpy()
            df["blend_all"] = cfa["arm__blend_all"].to_numpy()
        name = "rows_%s_lead_%d.parquet" % (st["pkg"], st["lead"])
        path = HERE / name
        df.reset_index(drop=True).to_parquet(str(path), index=False)
        back = pd.read_parquet(str(path))
        if not back.equals(df.reset_index(drop=True)):
            raise RuntimeError("row file round trip %s" % name)
        written[name] = {"rows": int(len(df)), "columns": list(df.columns), "sha256": sha256_file(path)}
    out["row_files"] = written
    print("Q12 done")

    # ---------------- summary text (plain words, numbers only, every line POST HOC; coral also CIRCULAR)
    S_ = []
    P = out["passes"]
    C0 = P["coral/0"]
    S_.append("POST HOC: reproduction gate G0-G9 passed; engine v2 %s, LIVE %s unchanged; the re-run tools gave "
              "byte-identical WITH_WITHOUT.csv, alarm_replay.json and alarm_replay_scores.csv files and equal row "
              "files." % (v2_hash[:8], live_hash[:8]))
    S_.append("POST HOC, CIRCULAR: coral nowcast (test window 2016-2019, set by hand): status active; twin %s "
              "(weighting), simpler, passes its skill guard; reference gap %r on %d decision-surface rows."
              % (C0["twin_arm"], C0["reference_gap"], C0["reference_rows"]))
    S_.append("POST HOC, CIRCULAR: coral nowcast: %d month batches, %d with at least 30 visits and tested, %d "
              "switched (%s); %d of %d survey visits switched (%d changed value); largest tested ratio %r."
              % (C0["batches"], C0["batches_tested"], C0["batches_switched"], " ".join(C0["switched_batches"]),
                 C0["saved_rows_switched"], C0["saved_rows"], C0["rows_value_changed"], C0["max_ratio_tested"]))
    S_.append("POST HOC, CIRCULAR: coral nowcast MAE without %r, with %r (change %r, %r%% of without, %r band "
              "units)." % (C0["mae_without"], C0["mae_with"], C0["change"], C0["change_pct"],
                           C0["change_in_band_units"]))
    for yk in ("2016", "2017", "2018", "2019"):
        e = out["by_year"]["coral/0/%s" % yk]
        S_.append("POST HOC, CIRCULAR: coral nowcast %s (n %d): %r -> %r, %s; %d batches switched, %d visits."
                  % (yk, e["n"], e["mae_without"], e["mae_with"],
                     "unchanged" if e["flag"] == "same" else e["flag"], e["batches_switched"], e["rows_switched"]))
    S_.append("POST HOC: test years in which the alarm made a nowcast worse: %s." % (", ".join(worse_years) or "none"))
    for p_, e in out["coral_programme"].items():
        S_.append("POST HOC, CIRCULAR: coral nowcast programme %s (n %d%s): %r -> %r, %s; %d visits switched in %d "
                  "switched batches; contribution %r (share %r of the pooled change)."
                  % (p_, e["n"], ", not interpretable" if p_ == "AGRRA" else "", e["mae_without"], e["mae_with"],
                     e["flag"], e["rows_switched"], e["switched_batches_holding"],
                     contrib["by_programme"][p_]["contrib"], contrib["by_programme"][p_]["share"]))
    for sid in ("y_gt_0", "y_eq_0", "y_ge_50", "y_lt_50", "y_gt_q75", "y_le_q75"):
        e = out["subsets"]["coral/0/%s" % sid]
        S_.append("POST HOC, CIRCULAR, %s: coral nowcast %s (n %d): %r -> %r; %d visits switched in this subset."
                  % (OUTCOME_LABEL, e["label"], e["n"], e["mae_without"], e["mae_with"], e["rows_switched_in_subset"]))
    for fk in ("F1", "F2", "F3", "F4"):
        e = out["forms"][fk]
        S_.append("POST HOC, CIRCULAR: coral nowcast form %s (%s): pooled MAE %r; %d rows differ from the adopted arm."
                  % (fk, e["label"], e["pooled"]["mae"], e["rows_differing"]))
    sb = out["small_batches"]["coral/0"]
    S_.append("POST HOC, CIRCULAR: coral nowcast: %d batches had fewer than 30 visits (%d visits), not tested; %d of "
              "them had a ratio above 2.0 (%d visits); largest %r. INFORMATION ONLY: had those also switched, the "
              "pooled MAE would be %r." % (sb["count"], sb["saved_rows"], sb["above_threshold_count"],
                                           sb["above_threshold_saved_rows"], sb["largest_ratio"],
                                           sb["counterfactual_info_only"]["pooled_mae_with"]))
    for thr in THRESHOLDS:
        e = out["threshold_check"]["coral/0/%r" % thr]
        S_.append("POST HOC, CIRCULAR%s: coral nowcast at threshold %r: %d batches, %d visits switched, MAE with %r."
                  % ("" if thr == 2.0 else ", INFORMATION ONLY (2.0 stays fixed)", thr, e["batches_switched"],
                     e["rows_switched"], e["mae_with"]))
    D0 = P["defo/0"]
    S_.append("POST HOC: defo nowcast: status active; twin %s (answer type); reference gap %r on %d rows; %d yearly "
              "batches, %d tested, %d switched; largest ratio %r; MAE %r with and without."
              % (D0["twin_arm"], D0["reference_gap"], D0["reference_rows"], D0["batches"], D0["batches_tested"],
                 D0["batches_switched"], D0["max_ratio_tested"], D0["mae_without"]))
    for pkg in ("pm25", "ndvi", "fire"):
        e = P["%s/0" % pkg]
        S_.append("POST HOC: %s nowcast: %s; %d batches, ratios computed but 0 tested; largest computed ratio %r "
                  "(information only: the rule could not act); MAE %r with and without."
                  % (pkg, e["plain_status"], e["batches"], e["max_ratio_ge30"], e["mae_without"]))
    for key in ("pm25/6", "pm25/12", "ndvi/6", "ndvi/12", "fire/6", "fire/12", "defo/1", "coral/183", "coral/365"):
        e = P[key]
        tag = "POST HOC, CIRCULAR" if key.startswith("coral") else "POST HOC"
        if e["replayable"]:
            S_.append("%s: %s lead %d: %s; MAE %r with and without." % (tag, e["package"], e["lead"],
                                                                        e["plain_status"], e["mae_without"]))
        else:
            S_.append("%s: %s lead %d: %s; MAE without %r; %d batches, %d with at least 30 rows; MAE with not "
                      "computed." % (tag, e["package"], e["lead"], e["plain_status"], e["mae_without"], e["batches"],
                                     e["batches_ge30"]))
    rg = out["regions"]["coral/0"]
    S_.append("POST HOC, CIRCULAR: coral nowcast regions: %d better, %d same, %d worse with the alarm (of %d)."
              % (rg["better"], rg["same"], rg["worse"], rg["regions"]))
    vw = out["verdicts"]["coral/0"]["with"]["verdict"]
    S_.append("POST HOC, CIRCULAR: coral nowcast verdict with the alarm against the training median: %s, contrast "
              "mean %r [%r, %r], %d groups, %d better (locked verdict without: %s)."
              % (vw["tag"], vw["contrast"]["mean"], vw["contrast"]["low"], vw["contrast"]["high"],
                 vw["contrast"]["n_groups"], vw["groups_better"], out["verdicts"]["coral/0"]["without_locked"][
                     "verdict"]["tag"]))
    out["summary_text"] = S_
    out["elapsed_seconds"] = _time.time() - t0
    write_result()
    print("\n".join(S_))
    print("wrote", RESULT_FILE)


if __name__ == "__main__":
    main()
