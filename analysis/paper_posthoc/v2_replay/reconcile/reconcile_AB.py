"""Owner ruling AN2, part 3 of 3: reconcile implementers A and B of the POST HOC engine-v2 alarm replay.

Spec: D:/treeroute/analysis/paper_posthoc/v2_replay/SPEC.md, section 8.

What it does (read-only on every input; writes only reconcile_AB.json and reconcile_AB.log in this folder):
  1. Provenance: sha256 of SPEC.md, INPUTS_SHA256.txt, both scripts, both result files and all row files;
     checks the hashes A and B recorded for themselves, their inputs (against INPUTS_SHA256.txt) and their
     row files; re-hashes every file of INPUTS_SHA256.txt (streamed) to show the inputs are unchanged.
  2. Gates: G0-G9 'pass' in result_A.json and result_B.json.
  3. Leaf by leaf: result_A.json vs result_B.json. A and B used different key names for some fields; a
     fixed rename table (CANON below) maps B's names onto A's before the comparison. Exact for non-floats,
     floats bit-equal or |rel| <= 1e-12 (every non-bit-equal leaf listed). Free text (labels, notes) is
     compared but a difference there is classed as wording, not as a number. Leaves present on one side
     only are listed; for numbers among them the script looks for the same value in the same record of
     the other side, and step 5 recomputes most of them.
  4. Row-level: the 12 rows_<pkg>_lead_<L>.parquet of A and B, byte hashes and column by column bitwise
     (NaN-aware); also every column they share with the 14 gate row files of the 2026-10-21 replay.
  5. A third, independent recomputation (this script's own numpy code, no engine import) of the numbers
     from the row files (A's and B's are byte-identical) and, for the two not-replayable leads, from the
     gate row files, compared with A and with B.
No seed is involved. Run: py -3.9 -I -B reconcile_AB.py  (numpy 2.0.2 / pandas 2.3.3 / pyarrow 21.0.0, as A and B).
Every number here is POST HOC; coral numbers are also CIRCULAR (fact A8); coral's 2016-2019 window was set by hand.
"""
import sys
sys.dont_write_bytecode = True
import os, re, json, math, struct, hashlib, platform, time

import numpy as np
import pandas as pd
import pyarrow
import pyarrow.parquet as pq

T0 = time.time()
DEV = "--dev" in sys.argv[1:]          # development only: skip the input re-hash and write nothing
ROOT = "D:/treeroute/analysis/paper_posthoc/v2_replay"
OUTDIR = ROOT + "/reconcile"
GATE_ROWS = "D:/treeroute/engine_v2/replay_af2_20261021/rows"
EDGES_CSV = "D:/treeroute/runs/_headline_tables/coral/coral_report/magnitude_edges.csv"
RUNS = {"pm25": "20261007_74e67609", "ndvi": "20261016_d1de3158", "fire": "20261017_869d1f38",
        "defo": "20261017_d71c61f4", "coral": "20261020_f3b8e3da"}
REPLAYABLE = [("pm25", 0), ("pm25", 6), ("pm25", 12), ("ndvi", 0), ("ndvi", 6), ("ndvi", 12), ("fire", 0),
              ("fire", 6), ("fire", 12), ("defo", 0), ("coral", 0), ("coral", 365)]
NOT_REPLAYABLE = [("defo", 1), ("coral", 183)]
THRESHOLD, MIN_ROWS = 2.0, 30          # V1 / A8 constants (fixed); the threshold check uses exactly these four:
THRESHOLDS = [1.5, 2.0, 2.5, 3.0]
REL_TOL = 1e-12
RESIDUAL_ABS_TOL = 1e-14               # Q5 residuals are rounding only; their last bits depend on summation order
TEXT_KEYS = {"label", "note", "why", "why_not", "formula", "selection", "batches_rule", "max_ratio_ge30_note"}
LOG = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def out_path(name):
    p = os.path.abspath(os.path.join(OUTDIR, name)).replace("\\", "/")
    assert p.startswith(os.path.abspath(OUTDIR).replace("\\", "/") + "/"), p
    return p


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def jload(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def norm(p):
    return p.replace("\\", "/")


# ----------------------------------------------------------------------------------------------------- 1
say("POST HOC reconciliation of the engine-v2 alarm replay (ruling AN2, part 3); coral is also CIRCULAR.")
prov = {"python": sys.version, "executable": sys.executable, "platform": platform.platform(),
        "numpy": np.__version__, "pandas": pd.__version__, "pyarrow": pyarrow.__version__,
        "flags": {"isolated": bool(sys.flags.isolated), "dont_write_bytecode": bool(sys.dont_write_bytecode)}}
files = {"SPEC.md": ROOT + "/SPEC.md", "INPUTS_SHA256.txt": ROOT + "/INPUTS_SHA256.txt",
         "A/replay_A.py": ROOT + "/A/replay_A.py", "B/replay_B.py": ROOT + "/B/replay_B.py",
         "A/result_A.json": ROOT + "/A/result_A.json", "B/result_B.json": ROOT + "/B/result_B.json",
         "A/run1.log": ROOT + "/A/run1.log", "reconcile/reconcile_AB.py": os.path.abspath(__file__)}
for pkg, lead in REPLAYABLE:
    for side in "AB":
        files[f"{side}/rows_{pkg}_lead_{lead}.parquet"] = f"{ROOT}/{side}/rows_{pkg}_lead_{lead}.parquet"
for dp, _, fns in os.walk(ROOT + "/A/tool_rerun"):
    for fn in sorted(fns):
        full = norm(os.path.join(dp, fn))
        files["A/" + full.split("/A/", 1)[1]] = full
hashes = {k: sha256(v) for k, v in files.items()}
prov["file_sha256"] = hashes
A = jload(files["A/result_A.json"])
B = jload(files["B/result_B.json"])
checks = []          # (name, ok, detail)


def check(name, ok, detail=None):
    checks.append({"check": name, "ok": bool(ok), "detail": detail})
    if not ok:
        say("CHECK FAILED:", name, detail)


check("A script_sha256 equals replay_A.py on disk", A["script_sha256"] == hashes["A/replay_A.py"], A["script_sha256"])
check("B script_sha256 equals replay_B.py on disk", B["script_sha256"] == hashes["B/replay_B.py"], B["script_sha256"])
for fn, rec in A.get("row_files", {}).items():
    check(f"A row_files[{fn}].sha256 equals disk", rec["sha256"] == hashes["A/" + fn], rec["sha256"])
for key, rec in B["passes"].items():
    if rec.get("row_file"):
        fn = os.path.basename(rec["row_file"])
        check(f"B passes[{key}].row_file_sha256 equals disk", rec["row_file_sha256"] == hashes["B/" + fn], rec["row_file_sha256"])
for side, R_ in (("A", A), ("B", B)):
    for k in ("numpy", "pandas", "pyarrow"):
        check(f"{side} {k} version equals this script's", R_["python_and_libraries"][k] == prov[k], R_["python_and_libraries"][k])
    check(f"{side} python 3.9.13", R_["python_and_libraries"]["python"].startswith("3.9.13"), R_["python_and_libraries"]["python"])

listed = {}
with open(files["INPUTS_SHA256.txt"], "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        h, p = line.split(None, 1)
        listed[norm(p.lstrip("*"))] = h
inputs_report = {"listed": len(listed)}
for side, R_ in (("A", A), ("B", B)):
    ins = {norm(p): h for p, h in R_["inputs"].items()}
    in_list = [p for p in ins if p in listed]
    mism = [p for p in in_list if ins[p] != listed[p]]
    extra = {p: h for p, h in ins.items() if p not in listed}
    extra_ok = {}
    for p, h in extra.items():
        rel = p.split("/v2_replay/", 1)[1] if "/v2_replay/" in p else None
        extra_ok[p] = (rel in hashes and hashes[rel] == h) if rel else (sha256(p) == h)
    inputs_report[side] = {"recorded": len(ins), "in_list": len(in_list), "mismatch_vs_list": mism,
                           "not_in_list": extra, "not_in_list_match_disk": extra_ok,
                           "listed_not_recorded": sorted(set(listed) - set(ins))}
    check(f"{side} recorded input hashes equal INPUTS_SHA256.txt", not mism, mism)
    check(f"{side} recorded hashes of files outside the list equal disk", all(extra_ok.values()), extra_ok)
t = time.time()
rehash_bad = {} if DEV else {p: (h, sha256(p)) for p, h in listed.items()}
rehash_bad = {p: v for p, v in rehash_bad.items() if v[0] != v[1]}
inputs_report["rehash_now"] = {"files": len(listed), "mismatches": rehash_bad, "seconds": round(time.time() - t, 1)}
check("every INPUTS_SHA256.txt file re-hashed now matches", not rehash_bad, rehash_bad)
# A's step-A2 tool re-run against the gate targets of the 2026-10-21 replay (byte level)
GATE_DIR = "D:/treeroute/engine_v2/replay_af2_20261021"
tool_vs_gate = {}
for rel in sorted(h for h in hashes if h.startswith("A/tool_rerun/")):
    sub = rel[len("A/tool_rerun/"):]
    gp = f"{GATE_DIR}/{sub}"
    tool_vs_gate[sub] = {"tool_rerun_sha256": hashes[rel], "gate_sha256": sha256(gp) if os.path.exists(gp) else None}
    tool_vs_gate[sub]["byte_identical"] = tool_vs_gate[sub]["tool_rerun_sha256"] == tool_vs_gate[sub]["gate_sha256"]
check("A tool re-run files byte-identical to the gate targets (all of them)",
      all(v["byte_identical"] for v in tool_vs_gate.values()), {k: v["byte_identical"] for k, v in tool_vs_gate.items()})
prov["tool_rerun_vs_gate"] = tool_vs_gate
say(f"1 provenance: {len(hashes)} output files hashed; {0 if DEV else len(listed)} of {len(listed)} inputs re-hashed now, {len(rehash_bad)} mismatches")

# ----------------------------------------------------------------------------------------------------- 2
gates = {}
for g in [f"G{i}" for i in range(10)]:
    gates[g] = {"A": bool(A["gates"][g]["pass"]), "B": bool(B["gates"][g]["pass"])}
    check(f"gate {g} passed in A and B", gates[g]["A"] and gates[g]["B"], gates[g])
check("B read no engine code", B.get("read_engine_code") == [], B.get("read_engine_code"))
say("2 gates:", {g: (v["A"], v["B"]) for g, v in gates.items()})


# ----------------------------------------------------------------------------------------------------- 3
def flatten(o, path=()):
    out = {}
    if isinstance(o, dict):
        if not o:
            out[path] = "<empty dict>"
        for k, v in o.items():
            out.update(flatten(v, path + (str(k),)))
    elif isinstance(o, list):
        if not o:
            out[path] = "<empty list>"
        for i, v in enumerate(o):
            out.update(flatten(v, path + (f"[{i}]",)))
    else:
        out[path] = o
    return out


REN2 = {  # field renames at depth 2 (section, record, FIELD), B name -> A name
    "passes": {"batches_ge30_saved_rows": "batches_ge30", "saved_rows_in_batches_lt30": "saved_rows_in_small_batches",
               "twin_passes_skill_guard": "twin_guard", "reference_gap_rows": "reference_rows"},
    "batches": {"small_batch_lt30": "small_batch"},
    "by_year": {"saved_rows_switched": "rows_switched"},
    "coral_programme": {"saved_rows_switched": "rows_switched", "switched_batches_holding_visits": "switched_batches_holding"},
    "coral_programme_year": {"saved_rows_switched": "rows_switched", "switched_batches_holding_visits": "switched_batches_holding"},
    "threshold_check": {"pooled_mae_with": "mae_with", "pooled_mae_without": "mae_without", "saved_rows_switched": "rows_switched"},
    "silence": {"switched_any_batch": "switched_any", "kind": "class", "largest_ratio_computed_information": "largest_ratio_ge30_information"},
    "small_batches": {"batches_lt30": "small_batches", "count_ratio_above_2": "above_threshold_count",
                      "saved_rows_ratio_above_2": "above_threshold_saved_rows",
                      "counterfactual_if_small_batches_above_2_also_switched": "counterfactual_info_only",
                      "status": "pass_status", "count_lt30": "small_count", "saved_rows_lt30": "small_saved_rows"},
}
CANON_NOTES = [
    "B field names mapped onto A's (depth 2): " + json.dumps(REN2),
    "B contributions by_programme_residual / by_programme_year_residual -> residual_programme / residual_programme_year",
    "B forms .../change -> change_vs_without; rows_differing/saved_rows -> rows_differing; rows_differing/labelled_rows -> rows_differing_labelled",
    "B small_batches list items ratio_above_2 -> ratio_above_threshold; counterfactual saved_rows_switched -> rows_switched",
    "B regions counts/<flag> -> <flag>; n_regions -> regions",
    "B verdicts/<pkg>/{verdict_with, blocked_jackknife_with, verdict_without_locked, blocked_jackknife_without_locked, pooled_mae_*} -> "
    "A verdicts/<pkg>/0/{with/verdict, with/blocked_jackknife, without_locked/verdict, without_locked/blocked_jackknife, with/pooled_mae_*}; "
    "verdict_without_recomputed -> without_recomputed_B/verdict (B only; cross-checked against A without_locked)",
    "B python_and_libraries flags_isolated / dont_write_bytecode -> flags/isolated, flags/dont_write_bytecode",
    "values: a 'year' leaf held as int (B) is compared as its decimal text (A); B subsets 'edge' text ('y > 23.9575') is compared "
    "as its number (A holds the number); A silence switched_any 'yes'/'no' is compared as true/false (B)",
]


def canon(side, path, value):
    p = list(path)
    sec = p[0]
    if side == "B":
        if len(p) > 2 and sec in REN2 and p[2] in REN2[sec]:
            p[2] = REN2[sec][p[2]]
        if sec == "small_batches":
            if len(p) > 4 and p[2] == "small_batches" and p[4] == "ratio_above_2":
                p[4] = "ratio_above_threshold"
            if len(p) > 3 and p[2] == "counterfactual_info_only" and p[3] == "saved_rows_switched":
                p[3] = "rows_switched"
        if sec == "contributions" and len(p) > 1:
            p[1] = {"by_programme_residual": "residual_programme",
                    "by_programme_year_residual": "residual_programme_year"}.get(p[1], p[1])
        if sec == "forms":
            if p[-1] == "change":
                p[-1] = "change_vs_without"
            if len(p) == 4 and p[2] == "rows_differing":
                p = p[:3] if p[3] == "saved_rows" else p[:2] + ["rows_differing_labelled"]
        if sec == "regions" and len(p) > 2:
            if p[2] == "counts" and len(p) == 4:
                p = p[:2] + [p[3]]
            elif p[2] == "n_regions":
                p[2] = "regions"
        if sec == "verdicts" and len(p) > 2:
            pk = p[1] + "/0"
            f = p[2]
            mp = {"verdict_with": ["with", "verdict"], "blocked_jackknife_with": ["with", "blocked_jackknife"],
                  "verdict_without_locked": ["without_locked", "verdict"],
                  "blocked_jackknife_without_locked": ["without_locked", "blocked_jackknife"],
                  "verdict_without_recomputed": ["without_recomputed_B", "verdict"],
                  "blocked_jackknife_without_recomputed": ["without_recomputed_B", "blocked_jackknife"],
                  "pooled_mae_with": ["with", "pooled_mae_with"], "pooled_mae_without": ["with", "pooled_mae_without"],
                  "pooled_mae_reference": ["with", "pooled_mae_reference"]}
            p = ["verdicts", pk] + mp.get(f, [f]) + p[3:]
        if sec == "python_and_libraries" and len(p) == 2:
            if p[1] == "flags_isolated":
                p = [sec, "flags", "isolated"]
            elif p[1] == "dont_write_bytecode":
                p = [sec, "flags", "dont_write_bytecode"]
        if sec == "subsets" and p[-1] == "edge" and isinstance(value, str):
            m = re.search(r"(-?\d+(?:\.\d+)?)\s*$", value)
            value = float(m.group(1)) if m else value
    if side == "A" and sec == "silence" and p[-1] == "switched_any" and value in ("yes", "no"):
        value = value == "yes"
    if p[-1] == "year" and isinstance(value, int) and not isinstance(value, bool):
        value = str(value)
    return tuple(p), value


def cflat(side, R_):
    out = {}
    for path, v in flatten({k: v for k, v in R_.items()}).items():
        cp, cv = canon(side, path, v)
        assert cp not in out, (side, cp)
        out[cp] = cv
    return out


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def compare(a, b):
    """-> (status, absdiff, reldiff). status in bit_equal, equal, within_tol, differ."""
    if a is None or b is None:
        return ("equal" if a is None and b is None else "differ"), None, None
    if isinstance(a, bool) or isinstance(b, bool):
        return ("equal" if (type(a) is type(b) and a == b) else "differ"), None, None
    if is_num(a) and is_num(b):
        if isinstance(a, int) and isinstance(b, int):
            return ("equal" if a == b else "differ"), float(abs(a - b)), None
        fa, fb = float(a), float(b)
        if math.isnan(fa) and math.isnan(fb):
            return "bit_equal", 0.0, 0.0
        if struct.pack("<d", fa) == struct.pack("<d", fb):
            return ("bit_equal" if type(a) is type(b) else "equal"), 0.0, 0.0
        ad = abs(fa - fb)
        rd = ad / max(abs(fa), abs(fb)) if max(abs(fa), abs(fb)) > 0 else 0.0
        if ad == 0.0:
            return "equal", 0.0, 0.0       # 0.0 vs -0.0
        return ("within_tol" if rd <= REL_TOL else "differ"), ad, rd
    return ("equal" if a == b else "differ"), None, None


def ps(path):
    return "/".join(path)


SKIP_SECTIONS = {"implementer", "script_sha256", "engine_v2_hash", "read_engine_code", "summary_text", "inputs",
                 "gates", "elapsed_seconds", "row_files"}
FA = {k: v for k, v in cflat("A", A).items() if k[0] not in SKIP_SECTIONS}
FB = {k: v for k, v in cflat("B", B).items() if k[0] not in SKIP_SECTIONS}
leaf = {"matched": 0, "bit_equal_floats": 0, "equal_other": 0, "within_tol": [], "differ_numbers_or_codes": [],
        "differ_wording": [], "differ_expected_environment": [], "only_A": [], "only_B": [], "per_section": {}}
max_abs_matched = 0.0
for path in sorted(set(FA) | set(FB)):
    sec = path[0]
    st = leaf["per_section"].setdefault(sec, {"A_leaves": 0, "B_leaves": 0, "matched": 0, "same": 0, "differ": 0,
                                              "wording": 0, "only_A": 0, "only_B": 0})
    inA, inB = path in FA, path in FB
    st["A_leaves"] += inA
    st["B_leaves"] += inB
    if inA and inB:
        leaf["matched"] += 1
        st["matched"] += 1
        s, ad, rd = compare(FA[path], FB[path])
        if ad is not None:
            max_abs_matched = max(max_abs_matched, ad)
        if s == "bit_equal":
            leaf["bit_equal_floats" if isinstance(FA[path], float) else "equal_other"] += 1
            st["same"] += 1
        elif s == "equal":
            leaf["equal_other"] += 1
            st["same"] += 1
        elif s == "within_tol":
            leaf["within_tol"].append({"path": ps(path), "A": FA[path], "B": FB[path], "abs": ad, "rel": rd})
            st["same"] += 1
        elif path[-1] in TEXT_KEYS or (sec == "subsets" and path[-1] == "label") or (sec == "forms" and path[-1] == "label"):
            leaf["differ_wording"].append({"path": ps(path), "A": FA[path], "B": FB[path]})
            st["wording"] += 1
        elif sec == "python_and_libraries" and path[-1] in ("platform",):
            leaf["differ_expected_environment"].append({"path": ps(path), "A": FA[path], "B": FB[path]})
        else:
            leaf["differ_numbers_or_codes"].append({"path": ps(path), "A": FA[path], "B": FB[path], "abs": ad, "rel": rd})
            st["differ"] += 1
    elif inA:
        leaf["only_A"].append(path)
        st["only_A"] += 1
    else:
        leaf["only_B"].append(path)
        st["only_B"] += 1
leaf["max_abs_diff_matched_numeric"] = max_abs_matched

# explicit cross pairs (same quantity stored in different places by A and B)
cross = []
for pkg in RUNS:
    k = pkg + "/0"
    for sub in ("verdict", "blocked_jackknife"):
        pa = ("verdicts", k, "without_locked", sub)
        pb = ("verdicts", k, "without_recomputed_B", sub)
        for path in [q for q in FB if q[:4] == pb]:
            cross.append((pa + path[4:], path))
for sub, a_sub in (("verdict_with", "verdict"), ("blocked_jackknife_with", "blocked_jackknife")):
    for path in [q for q in FB if q[:3] == ("regions", "coral/0", sub)]:
        cross.append((("verdicts", "coral/0", "with", a_sub) + path[3:], path))
for F in ("F2", "F3", "F4"):
    for path in [q for q in FB if q[0] == "subsets" and q[1] == "coral/0" and q[-1] in (f"mae_{F}", f"change_{F}")]:
        sid = path[2]
        cross.append((("forms", F, "subsets", sid, "mae" if path[-1].startswith("mae") else "change_vs_without"), path))
DERIVED = {}   # A-side values derived from A's own leaves (B stores them as separate fields)
for k, rec in A["passes"].items():
    tb = rec.get("twin_guard_basis")
    if isinstance(tb, dict) and tb.get("twin_key"):
        mm = re.search(r"@level=([^,]+),ratio=(.+)$", tb["twin_key"])
        lv = None if mm.group(1) == "None" else float(mm.group(1))
        rt_ = None if mm.group(2) == "None" else float(mm.group(2))
        DERIVED[("passes", k, "twin_guard_basis", "point", "level")] = lv
        DERIVED[("passes", k, "twin_guard_basis", "point", "ratio")] = rt_
        DERIVED[("passes", k, "twin_guard_basis", "eligible")] = rec.get("twin_guard")
for path, v in DERIVED.items():
    FA[("derived_from_A",) + path] = v
    cross.append((("derived_from_A",) + path, path))
cross_res = {"pairs": 0, "same": 0, "differ": []}
for pa, pb in cross:
    if pa not in FA:
        cross_res["differ"].append({"A_path": ps(pa), "B_path": ps(pb), "why": "A path absent"})
        continue
    s, ad, rd = compare(FA[pa], FB[pb])
    cross_res["pairs"] += 1
    if s in ("bit_equal", "equal", "within_tol"):
        cross_res["same"] += 1
    else:
        cross_res["differ"].append({"A_path": ps(pa), "B_path": ps(pb), "A": FA[pa], "B": FB[pb]})
crossed_A = {pa for pa, _ in cross}
crossed_B = {pb for _, pb in cross}
say(f"3 leaves: matched {leaf['matched']}; differing numbers/codes {len(leaf['differ_numbers_or_codes'])}; "
    f"within 1e-12 {len(leaf['within_tol'])}; wording {len(leaf['differ_wording'])}; only A {len(leaf['only_A'])}; "
    f"only B {len(leaf['only_B'])}; cross pairs {cross_res['pairs']} ({len(cross_res['differ'])} differ)")

# ----------------------------------------------------------------------------------------------------- 4
rows_report = {}
row_max_abs = 0.0
for pkg, lead in REPLAYABLE:
    fn = f"rows_{pkg}_lead_{lead}.parquet"
    ta = pq.read_table(f"{ROOT}/A/{fn}")
    tb = pq.read_table(f"{ROOT}/B/{fn}")
    r = {"sha256_A": hashes["A/" + fn], "sha256_B": hashes["B/" + fn],
         "byte_identical": hashes["A/" + fn] == hashes["B/" + fn],
         "rows": [ta.num_rows, tb.num_rows], "schema_equal": ta.schema.equals(tb.schema), "columns": {}}
    for c in ta.column_names:
        if c not in tb.column_names:
            r["columns"][c] = "only in A"
            continue
        xa = ta.column(c).to_numpy(zero_copy_only=False)
        xb = tb.column(c).to_numpy(zero_copy_only=False)
        if xa.dtype.kind == "f":
            both_nan = np.isnan(xa) & np.isnan(xb)
            bit = (xa.view(np.uint64) == xb.view(np.uint64)) | both_nan
            fin = np.isfinite(xa) & np.isfinite(xb)
            mad = float(np.max(np.abs(xa[fin] - xb[fin]))) if fin.any() else 0.0
            row_max_abs = max(row_max_abs, mad)
            r["columns"][c] = {"bitwise_equal_rows": int(bit.sum()), "rows": int(len(xa)),
                               "nan_mismatch": int((np.isnan(xa) != np.isnan(xb)).sum()), "max_abs_diff": mad}
        else:
            eq = np.asarray(xa == xb)
            r["columns"][c] = {"equal_rows": int(eq.sum()), "rows": int(len(xa))}
    for c in tb.column_names:
        if c not in ta.column_names:
            r["columns"][c] = "only in B"
    ok = r["byte_identical"] and r["schema_equal"] and all(
        isinstance(v, dict) and v.get("bitwise_equal_rows", v.get("equal_rows")) == v["rows"] for v in r["columns"].values())
    r["all_columns_bitwise_equal"] = ok
    check(f"row file {fn}: A == B (bytes and every column bitwise)", ok, None if ok else r)
    # the gate row file of the 2026-10-21 replay: every shared column
    gp = f"{GATE_ROWS}/{pkg}_{RUNS[pkg]}_lead_{lead}.parquet"
    tg = pq.read_table(gp)
    gsh = {}
    for c in tg.column_names:
        if c not in ta.column_names:
            gsh[c] = "not in A/B file"
            continue
        xg = tg.column(c).to_numpy(zero_copy_only=False)
        xa = ta.column(c).to_numpy(zero_copy_only=False)
        if xg.dtype.kind == "f":
            gsh[c] = bool(np.all((xg.view(np.uint64) == xa.view(np.uint64)) | (np.isnan(xg) & np.isnan(xa))))
        else:
            gsh[c] = bool(np.all(np.asarray(xg == xa)))
    r["gate_file"] = {"path": gp, "rows": tg.num_rows, "shared_columns_bitwise_equal": gsh,
                      "columns_only_in_A_B_file": [c for c in ta.column_names if c not in tg.column_names]}
    check(f"row file {fn}: every column shared with the gate file bitwise equal",
          tg.num_rows == ta.num_rows and all(v is True for v in gsh.values() if v != "not in A/B file"), gsh)
    rows_report[fn] = r
say(f"4 row files: {sum(r['all_columns_bitwise_equal'] for r in rows_report.values())} of {len(rows_report)} identical; max abs diff {row_max_abs}")

# ----------------------------------------------------------------------------------------------------- 5
edges = pd.read_csv(EDGES_CSV).set_index("lead")["q75_positive_donor_labels"].to_dict()
RC = {}   # canonical path -> recomputed value


def mae(y, p, m):
    if not m.any():
        return None
    return float(np.mean(np.abs(y[m] - p[m])))


def flag(w, wo):
    if w is None or wo is None:
        return None
    return "better" if w < wo else ("worse" if w > wo else "same")


def border(keys):
    keys = list(keys)
    if keys and all(str(k).startswith("step:") for k in keys):
        return sorted(keys, key=lambda s: int(s.split(":", 1)[1]))
    return sorted(keys)


def put(path, v):
    RC[tuple(path)] = v


def put_list(path, lst):
    if not lst:
        put(path, "<empty list>")
    for i, v in enumerate(lst):
        put(tuple(path) + (f"[{i}]",), v)


def subset_masks(y, lab, q):
    return {"all": lab.copy(), "y_gt_0": lab & (y > 0), "y_eq_0": lab & (y == 0), "y_ge_50": lab & (y >= 50),
            "y_lt_50": lab & (y < 50), "y_gt_q75": lab & (y > q), "y_le_q75": lab & (y <= q)}


worse_years = []
for pkg, lead in REPLAYABLE:
    k = f"{pkg}/{lead}"
    d = pd.read_parquet(f"{ROOT}/A/rows_{pkg}_lead_{lead}.parquet")
    y = d["y"].to_numpy(float)
    ad = d["adopted"].to_numpy(float)
    tw = d["twin"].to_numpy(float)
    wa = d["with_alarm"].to_numpy(float)
    fired = d["fired"].to_numpy(bool)
    batch = d["batch"].to_numpy(object)
    year = d["year"].to_numpy()
    lab = np.isfinite(y)
    pa = A["passes"][k]
    Rg, status, band = pa["reference_gap"], pa["status"], pa["band"]
    twin_saved = bool(np.isfinite(tw).any())
    active = status == "active" and Rg is not None and math.isfinite(Rg) and Rg > 0
    put(("passes", k, "saved_rows"), int(len(d)))
    put(("passes", k, "labelled_rows"), int(lab.sum()))
    put(("passes", k, "n_scored"), int(lab.sum()))
    put(("passes", k, "twin_saved"), twin_saved)
    mwo, mwi = mae(y, ad, lab), mae(y, wa, lab)
    put(("passes", k, "mae_without"), mwo)
    put(("passes", k, "mae_with"), mwi)
    put(("passes", k, "change"), mwi - mwo)
    put(("passes", k, "change_pct"), (mwi - mwo) / mwo * 100.0)
    put(("passes", k, "change_in_band_units"), (mwi - mwo) / band)
    put(("passes", k, "saved_rows_switched"), int(fired.sum()))
    put(("passes", k, "labelled_rows_switched"), int((fired & lab).sum()))
    put(("passes", k, "rows_value_changed"), int((fired & (tw != ad)).sum()))
    bk = border(pd.unique(batch))
    idx = {b: np.flatnonzero(batch == b) for b in bk}
    size = {b: len(idx[b]) for b in bk}
    put(("passes", k, "batches"), len(bk))
    put(("passes", k, "batches_ge30"), sum(size[b] >= MIN_ROWS for b in bk))
    put(("passes", k, "saved_rows_in_small_batches"), int(sum(size[b] for b in bk if size[b] < MIN_ROWS)))
    ratio, tested, switched = {}, {}, {}
    for b in bk:
        I = idx[b]
        if twin_saved and Rg is not None:
            g = float(np.mean(np.abs(ad[I] - tw[I])))
            ratio[b] = g / Rg
        else:
            g = None
            ratio[b] = None
        tested[b] = bool(active and size[b] >= MIN_ROWS)
        switched[b] = bool(tested[b] and ratio[b] > THRESHOLD)
        check(f"{k} batch {b}: saved 'fired' equals the rule's decision", bool(np.all(fired[I] == switched[b])))
        if lead == 0:
            m = np.zeros(len(d), bool)
            m[I] = True
            yrs = sorted(set(year[I].tolist()))
            check(f"{k} batch {b} lies in one year", len(yrs) == 1, yrs)
            base = ("batches", f"{k}/{b}")
            put(base + ("saved_rows",), size[b])
            put(base + ("labelled_rows",), int((m & lab).sum()))
            put(base + ("n_scored",), int((m & lab).sum()))
            put(base + ("year",), str(yrs[0]))
            put(base + ("gap",), g)
            put(base + ("ratio",), ratio[b])
            put(base + ("tested",), tested[b])
            put(base + ("switched",), switched[b])
            put(base + ("small_batch",), size[b] < MIN_ROWS)
            put(base + ("ratio_above_threshold",), None if ratio[b] is None else bool(ratio[b] > THRESHOLD))
            bw, bwi = mae(y, ad, m & lab), mae(y, wa, m & lab)
            put(base + ("mae_without",), bw)
            put(base + ("mae_with",), bwi)
            put(base + ("change",), None if bw is None else bwi - bw)
            put(base + ("saved_rows_switched",), int((fired & m).sum()))
            put(base + ("labelled_rows_switched",), int((fired & m & lab).sum()))
            put(base + ("rows_value_changed",), int((fired & m & (tw != ad)).sum()))
    sw = [b for b in bk if switched[b]]
    put(("passes", k, "batches_tested"), sum(tested.values()))
    put(("passes", k, "batches_switched"), len(sw))
    put_list(("passes", k, "switched_batches"), sw)
    rt = [ratio[b] for b in bk if tested[b]]
    rg = [ratio[b] for b in bk if size[b] >= MIN_ROWS and ratio[b] is not None]
    put(("passes", k, "max_ratio_tested"), max(rt) if rt else None)
    put(("passes", k, "max_ratio_ge30"), max(rg) if rg else None)
    # by year
    for yr in sorted(set(year.tolist())):
        m = year == yr
        n = int((m & lab).sum())
        w0, w1 = mae(y, ad, m & lab), mae(y, wa, m & lab)
        base = ("by_year", f"{k}/{yr}")
        yb = [b for b in bk if np.any(m[idx[b]])]
        put(base + ("n",), n)
        put(base + ("saved_rows",), int(m.sum()))
        put(base + ("mae_without",), w0)
        put(base + ("mae_with",), w1)
        put(base + ("change",), w1 - w0)
        put(base + ("flag",), flag(w1, w0))
        put(base + ("batches",), len(yb))
        put(base + ("batches_spanning_two_years",), sum(len(set(year[idx[b]].tolist())) > 1 for b in yb))
        put(base + ("batches_tested",), sum(tested[b] for b in yb))
        put(base + ("batches_switched",), sum(switched[b] for b in yb))
        put(base + ("rows_switched",), int((fired & m).sum()))
        put(base + ("labelled_rows_switched",), int((fired & m & lab).sum()))
        if lead == 0 and flag(w1, w0) == "worse":
            worse_years.append(f"{k}/{yr}")
        if not fired.any():
            check(f"{k} {yr}: nothing switched, with == without bitwise", struct.pack("<d", w0) == struct.pack("<d", w1))
    # subsets (coral)
    if pkg == "coral":
        q = float(edges[lead])
        for sid, msk in subset_masks(y, lab, q).items():
            base = ("subsets", f"{k}/{sid}")
            w0, w1 = mae(y, ad, msk), mae(y, wa, msk)
            put(base + ("n",), int(msk.sum()))
            put(base + ("mae_without",), w0)
            put(base + ("mae_with",), w1)
            put(base + ("change",), w1 - w0)
            put(base + ("change_pct",), (w1 - w0) / w0 * 100.0)
            put(base + ("rows_switched_in_subset",), int((fired & msk).sum()))
            put(base + ("edge",), None if sid == "all" else (0.0 if sid in ("y_gt_0", "y_eq_0") else (50.0 if sid in ("y_ge_50", "y_lt_50") else q)))
            put(base + ("q75_edge",), q)
    # small batches, threshold check, silence: lead-0 passes
    if lead == 0:
        sb = [b for b in bk if size[b] < MIN_ROWS]
        base = ("small_batches", k)
        if twin_saved:
            put(base + ("count",), len(sb))
            put(base + ("saved_rows",), int(sum(size[b] for b in sb)))
            put(base + ("largest_ratio",), max(ratio[b] for b in sb) if sb else None)
            put(base + ("above_threshold_count",), sum(ratio[b] > THRESHOLD for b in sb))
            put(base + ("above_threshold_saved_rows",), int(sum(size[b] for b in sb if ratio[b] > THRESHOLD)))
            if not sb:
                put(base + ("small_batches",), "<empty list>")
            for i, b in enumerate(sb):
                m = np.zeros(len(d), bool)
                m[idx[b]] = True
                bb = base + ("small_batches", f"[{i}]")
                put(bb + ("batch",), b)
                put(bb + ("saved_rows",), size[b])
                put(bb + ("labelled_rows",), int((m & lab).sum()))
                put(bb + ("ratio",), ratio[b])
                put(bb + ("ratio_above_threshold",), bool(ratio[b] > THRESHOLD))
                put(bb + ("tested",), False)
            if pkg == "coral":
                add = [b for b in sb if ratio[b] > THRESHOLD]
                cf = set(sw) | set(add)
                mcf = np.isin(batch, list(cf))
                col = np.where(mcf, tw, ad)
                v = mae(y, col, lab)
                cb = base + ("counterfactual_info_only",)
                put(cb + ("rows_switched",), int(mcf.sum()))
                put(cb + ("batches_switched",), len(cf))
                put(cb + ("pooled_mae_with",), v)
                put(cb + ("change_vs_without",), v - mwo)
                put(cb + ("change_vs_rule",), v - mwi)
                put(cb + ("pooled_mae_without",), mwo)
                put(cb + ("pooled_mae_with_fixed_rule",), mwi)
                put_list(cb + ("batches_added",), add)
        if pkg in ("coral", "defo"):
            for t in THRESHOLDS:
                swt = [b for b in bk if tested[b] and ratio[b] > t]
                mt = np.isin(batch, swt)
                col = np.where(mt, tw, ad)
                v = mae(y, col, lab)
                base = ("threshold_check", f"{k}/{t}")
                put(base + ("threshold",), t)
                put(base + ("batches_tested",), sum(tested.values()))
                put(base + ("batches_switched",), len(swt))
                put_list(base + ("switched_batches",), swt)
                put(base + ("rows_switched",), int(mt.sum()))
                put(base + ("labelled_rows_switched",), int((mt & lab).sum()))
                put(base + ("mae_without",), mwo)
                put(base + ("mae_with",), v)
                put(base + ("change",), v - mwo)
                if t == THRESHOLD:
                    check(f"{k}: threshold 2.0 reproduces the with-alarm column", struct.pack("<d", v) == struct.pack("<d", mwi))
                if pkg == "coral":
                    for yr in sorted(set(year.tolist())):
                        m = (year == yr) & lab
                        w0, w1 = mae(y, ad, m), mae(y, col, m)
                        yb = base + ("by_year", str(yr))
                        put(yb + ("n",), int(m.sum()))
                        put(yb + ("mae_without",), w0)
                        put(yb + ("mae_with",), w1)
                        put(yb + ("change",), w1 - w0)
                        put(yb + ("flag",), flag(w1, w0))
        base = ("silence", f"{pkg}/0")
        put(base + ("switched_any",), bool(len(sw) > 0))
        put(base + ("batches_tested",), sum(tested.values()))
        put(base + ("batches_switched",), len(sw))
        put(base + ("largest_ratio_tested",), max(rt) if rt else None)
        put(base + ("largest_ratio_ge30_information",), max(rg) if rg else None)
    # coral nowcast: programme, programme x year, contributions, forms, regions
    if pkg == "coral" and lead == 0:
        prog = d["programme"].to_numpy(object)
        N = int(lab.sum())
        pch = mwi - mwo
        put(("contributions", "N"), N)
        put(("contributions", "pooled_mae_without"), mwo)
        put(("contributions", "pooled_mae_with"), mwi)
        put(("contributions", "pooled_change"), pch)
        sums = {}
        for level in ("programme", "programme_year"):
            cells = []
            for p_ in sorted(set(prog.tolist())):
                if level == "programme":
                    cells.append((p_, prog == p_))
                else:
                    for yr in sorted(set(year[prog == p_].tolist())):
                        cells.append((f"{p_}/{yr}", (prog == p_) & (year == yr)))
            tot = 0.0
            for name, mc in cells:
                m = mc & lab
                n = int(m.sum())
                w0, w1 = mae(y, ad, m), mae(y, wa, m)
                sec = "coral_programme" if level == "programme" else "coral_programme_year"
                base = (sec, name)
                put(base + ("n",), n)
                put(base + ("mae_without",), w0)
                put(base + ("mae_with",), w1)
                put(base + ("change",), w1 - w0)
                put(base + ("flag",), flag(w1, w0))
                put(base + ("rows_switched",), int((fired & mc).sum()))
                put(base + ("switched_batches_holding",), len(set(batch[fired & mc].tolist())))
                contrib = (n / N) * (w1 - w0)
                tot += contrib
                cb = ("contributions", "by_" + level, name)
                put(cb + ("n",), n)
                put(cb + ("change",), w1 - w0)
                put(cb + ("contrib",), contrib)
                put(cb + ("share",), contrib / pch)
                put(cb + ("share_pct",), contrib / pch * 100.0)
            sums[level] = tot
        put(("contributions", "sum_programme"), sums["programme"])
        put(("contributions", "sum_programme_year"), sums["programme_year"])
        put(("contributions", "residual_programme"), sums["programme"] - pch)
        put(("contributions", "residual_programme_year"), sums["programme_year"] - pch)
        forms = {"F1": "with_alarm", "F2": "blend_batch", "F3": "twin_all", "F4": "blend_all"}
        q = float(edges[0])
        masks = subset_masks(y, lab, q)
        for F, cname in forms.items():
            col = d[cname].to_numpy(float)
            fb = ("forms", F)
            v = mae(y, col, lab)
            put(fb + ("pooled", "n"), N)
            put(fb + ("pooled", "mae"), v)
            put(fb + ("pooled", "mae_without"), mwo)
            put(fb + ("pooled", "change_vs_without"), v - mwo)
            for yr in sorted(set(year.tolist())):
                m = (year == yr) & lab
                w0, w1 = mae(y, ad, m), mae(y, col, m)
                for kk, vv in (("n", int(m.sum())), ("mae", w1), ("mae_without", w0), ("change_vs_without", w1 - w0), ("flag", flag(w1, w0))):
                    put(fb + ("by_year", str(yr), kk), vv)
            for p_ in sorted(set(prog.tolist())):
                m = (prog == p_) & lab
                w0, w1 = mae(y, ad, m), mae(y, col, m)
                for kk, vv in (("n", int(m.sum())), ("mae", w1), ("mae_without", w0), ("change_vs_without", w1 - w0), ("flag", flag(w1, w0))):
                    put(fb + ("by_programme", p_, kk), vv)
            for sid, msk in masks.items():
                w0, w1 = mae(y, ad, msk), mae(y, col, msk)
                for kk, vv in (("n", int(msk.sum())), ("mae", w1), ("mae_without", w0), ("change_vs_without", w1 - w0)):
                    put(fb + ("subsets", sid, kk), vv)
                if F != "F1":
                    put(("subsets", f"coral/0/{sid}", f"mae_{F}"), w1)
                    put(("subsets", f"coral/0/{sid}", f"change_{F}"), w1 - w0)
            put(fb + ("rows_differing",), int((col != ad).sum()))
            put(fb + ("rows_differing_labelled",), int(((col != ad) & lab).sum()))
        grp = d["group"].to_numpy(object)
        # the verdict's reference column (verdict.json "reference": base__donor_median), from the run's test_preds,
        # row-aligned with the replay rows (asserted on unit, time and y)
        tp = pq.read_table(f"D:/treeroute/runs/coral/headline/{RUNS['coral']}/test_preds.parquet",
                           columns=["unit", "time", "y", "base__donor_median"]).to_pandas()
        check("coral test_preds row-aligned with the replay rows (unit, time, y)",
              bool((tp["unit"].to_numpy(object) == d["unit"].to_numpy(object)).all()
                   and (tp["time"].to_numpy() == d["time"].to_numpy()).all()
                   and np.array_equal(tp["y"].to_numpy(float), y, equal_nan=True)))
        refc = tp["base__donor_median"].to_numpy(float)
        put(("verdicts", "coral/0", "with", "pooled_mae_reference"), mae(y, refc, lab))
        cnt = {"better": 0, "same": 0, "worse": 0}
        for g_ in sorted(set(grp.tolist())):
            m = (grp == g_) & lab
            w0, w1 = mae(y, ad, m), mae(y, wa, m)
            lb = ("regions", "coral/0", "lines", g_)
            put(lb + ("mae_reference",), mae(y, refc, m))
            put(lb + ("n",), int(m.sum()))
            put(lb + ("mae_without",), w0)
            put(lb + ("mae_with",), w1)
            put(lb + ("change",), w1 - w0)
            put(lb + ("flag",), flag(w1, w0))
            put(lb + ("saved_rows_switched",), int((fired & (grp == g_)).sum()))
            cnt[flag(w1, w0)] += 1
        for kk, vv in cnt.items():
            put(("regions", "coral/0", kk), vv)
        put(("regions", "coral/0", "regions"), len(set(grp.tolist())))
put_list(("by_year_worse",), worse_years)   # A only (B gives the same through its by_year flags)

# not-replayable leads, from the gate row files (no twin saved)
for pkg, lead in NOT_REPLAYABLE:
    k = f"{pkg}/{lead}"
    d = pd.read_parquet(f"{GATE_ROWS}/{pkg}_{RUNS[pkg]}_lead_{lead}.parquet")
    y = d["y"].to_numpy(float)
    ad = d["adopted"].to_numpy(float)
    batch = d["batch"].to_numpy(object)
    lab = np.isfinite(y)
    bk = border(pd.unique(batch))
    size = {b: int((batch == b).sum()) for b in bk}
    put(("passes", k, "saved_rows"), int(len(d)))
    put(("passes", k, "labelled_rows"), int(lab.sum()))
    put(("passes", k, "n_scored"), int(lab.sum()))
    put(("passes", k, "mae_without"), mae(y, ad, lab))
    put(("passes", k, "batches"), len(bk))
    put(("passes", k, "batches_ge30"), sum(size[b] >= MIN_ROWS for b in bk))
    put(("passes", k, "saved_rows_in_small_batches"), int(sum(size[b] for b in bk if size[b] < MIN_ROWS)))
    for f_ in ("mae_with", "batches_tested", "batches_switched", "saved_rows_switched", "max_ratio_tested", "change"):
        put(("passes", k, f_), None)
    put(("passes", k, "twin_saved"), False)
    sb = [b for b in bk if size[b] < MIN_ROWS]
    put(("small_batches", k, "batches"), len(bk))
    put(("small_batches", k, "small_count"), len(sb))
    put(("small_batches", k, "small_saved_rows"), int(sum(size[b] for b in sb)))
    if not sb:
        put(("small_batches", k, "small_batches"), "<empty list>")
    for i, b in enumerate(sb):
        put(("small_batches", k, "small_batches", f"[{i}]", "batch"), b)
        put(("small_batches", k, "small_batches", f"[{i}]", "saved_rows"), size[b])
    if pkg == "coral":
        q = float(edges[lead])
        for sid, msk in subset_masks(y, lab, q).items():
            base = ("subsets", f"{k}/{sid}")
            put(base + ("n",), int(msk.sum()))
            put(base + ("mae_without",), mae(y, ad, msk))
            put(base + ("mae_with",), None)
            put(base + ("rows_switched_in_subset",), None)
            put(base + ("change",), None)
            put(base + ("change_pct",), None)
            put(base + ("q75_edge",), q)

# compare the recomputation with A and with B
rc = {"values": len(RC), "A": {"compared": 0, "bit_or_exact": 0, "within_tol": [], "differ": [], "absent": 0},
      "B": {"compared": 0, "bit_or_exact": 0, "within_tol": [], "differ": [], "absent": 0}, "in_neither": []}
max_abs_rc = 0.0
for path, v in RC.items():
    hit = False
    for side, F_ in (("A", FA), ("B", FB)):
        if path not in F_:
            rc[side]["absent"] += 1
            continue
        hit = True
        rc[side]["compared"] += 1
        s, ad_, rd = compare(v, F_[path])
        if ad_ is not None:
            max_abs_rc = max(max_abs_rc, ad_)
        if s in ("bit_equal", "equal"):
            rc[side]["bit_or_exact"] += 1
        elif s == "within_tol" or (path[-1].startswith("residual") and ad_ is not None and ad_ <= RESIDUAL_ABS_TOL):
            rc[side]["within_tol"].append({"path": ps(path), "recomputed": v, side: F_[path], "abs": ad_, "rel": rd})
        else:
            rc[side]["differ"].append({"path": ps(path), "recomputed": v, side: F_[path], "abs": ad_, "rel": rd})
    if not hit:
        rc["in_neither"].append(ps(path))
rc["max_abs_diff"] = max_abs_rc
say(f"5 recompute: {len(RC)} values; vs A {rc['A']['compared']} compared, {len(rc['A']['differ'])} differ, "
    f"{len(rc['A']['within_tol'])} within tol; vs B {rc['B']['compared']} compared, {len(rc['B']['differ'])} differ, "
    f"{len(rc['B']['within_tol'])} within tol")

# one-sided leaves: confirmed by the recomputation, by a cross pair, or by the same value in the same record
TRIVIAL = (None, True, False, 0, 0.0, "<empty list>", "<empty dict>")
IDENT_KEYS = {"package", "lead", "year", "subset", "batch", "threshold", "programme", "pass", "run", "row_file",
              "row_file_sha256", "column", "script_path", "executable", "treeroute_imported_from", "twin_key", "baseline"}
LABEL_FLAGS = {"post_hoc", "circular", "information_only", "outcome_defined", "equals_gate_scores_line",
               "defo_0_equals_without", "equals_part604_M1", "equals_part604_M2_M3", "in_adoption_eligible_list"}


def one_sided(paths, here, other, crossed):
    res = {"total": len(paths), "numeric_or_flag": 0, "confirmed_by_recompute": 0, "recompute_differs": [],
           "confirmed_by_cross_pair": 0, "same_value_in_same_record_other_side": 0, "identifiers": 0,
           "label_flags": 0, "text": 0, "null": 0, "unconfirmed": []}
    rec_index = {}
    for q, v in other.items():
        rec_index.setdefault(q[:2], []).append((q, v))
    for path in paths:
        v = here[path]
        if path in RC:
            res["numeric_or_flag"] += 1
            if compare(RC[path], v)[0] in ("bit_equal", "equal", "within_tol") or (
                    path[-1].startswith("residual") and abs(RC[path] - v) <= RESIDUAL_ABS_TOL):
                res["confirmed_by_recompute"] += 1
            else:
                res["recompute_differs"].append({"path": ps(path), "value": v, "recomputed": RC[path]})
            continue
        last = [x for x in path if not x.startswith("[")][-1]
        if last in IDENT_KEYS:
            res["identifiers"] += 1
            continue
        if last in LABEL_FLAGS:
            res["label_flags"] += 1
            continue
        if isinstance(v, str):
            res["text"] += 1
            continue
        if v is None:
            res["null"] += 1
            continue
        res["numeric_or_flag"] += 1
        if path in crossed:
            res["confirmed_by_cross_pair"] += 1
            continue
        found = None
        if v not in TRIVIAL or (isinstance(v, float) and v != 0.0):
            for q, w in rec_index.get(path[:2], []):
                if type(w) is type(v) and compare(v, w)[0] in ("bit_equal", "equal"):
                    found = q
                    break
        if found:
            res["same_value_in_same_record_other_side"] += 1
            continue
        res["unconfirmed"].append({"path": ps(path), "value": v})
    return res


osA = one_sided(leaf["only_A"], FA, FB, crossed_A)
osB = one_sided(leaf["only_B"], FB, FA, crossed_B)
leaf["only_A"] = [ps(p) for p in leaf["only_A"]]
leaf["only_B"] = [ps(p) for p in leaf["only_B"]]
say(f"one-sided leaves: A {osA['total']} ({len(osA['unconfirmed'])} numbers/flags unconfirmed); "
    f"B {osB['total']} ({len(osB['unconfirmed'])} unconfirmed)")

# ----------------------------------------------------------------------------------------------------- verdict
disagree = (leaf["differ_numbers_or_codes"] or cross_res["differ"] or rc["A"]["differ"] or rc["B"]["differ"]
            or osA["recompute_differs"] or osB["recompute_differs"]
            or not all(r["all_columns_bitwise_equal"] for r in rows_report.values())
            or any(not c["ok"] for c in checks))
verdict = "DISAGREE" if disagree else "AGREE"
headline = {}
for k in ("coral/0", "defo/0", "pm25/0", "ndvi/0", "fire/0"):
    headline[k] = {f: A["passes"][k][f] for f in ("status", "batches", "batches_tested", "batches_switched",
                                                     "saved_rows_switched", "mae_without", "mae_with", "max_ratio_tested", "max_ratio_ge30")}
result = {
    "what": "POST HOC reconciliation of A and B of the engine-v2 alarm replay (owner ruling AN2, part 3); coral numbers are also CIRCULAR (fact A8); coral's 2016-2019 window was set by hand",
    "verdict": verdict,
    "environment": prov,
    "inputs": inputs_report,
    "gates": gates,
    "checks": {"total": len(checks), "failed": [c for c in checks if not c["ok"]]},
    "leaf_comparison": {"canonicalisation": CANON_NOTES, "rel_tol": REL_TOL, **leaf,
                        "cross_pairs": cross_res, "only_A_summary": osA, "only_B_summary": osB},
    "row_files": rows_report,
    "row_files_max_abs_diff": row_max_abs,
    "recompute": rc,
    "headline_from_A": headline,
    "elapsed_seconds": round(time.time() - T0, 1),
}
say(f"VERDICT: {verdict}. checks {len(checks)} ({len(result['checks']['failed'])} failed); matched leaves max abs diff "
    f"{max_abs_matched}; row files max abs diff {row_max_abs}; recompute max abs diff {max_abs_rc}")
if DEV:
    with open(os.path.join(os.environ.get("RECONCILE_DEV_OUT", "."), "dev_result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, default=str)
    sys.exit(0)
with open(out_path("reconcile_AB.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, indent=1, sort_keys=False, default=str)
with open(out_path("reconcile_AB.log"), "w", encoding="utf-8") as f:
    f.write("\n".join(LOG) + "\n")
say("wrote", out_path("reconcile_AB.json"), "and", out_path("reconcile_AB.log"))
