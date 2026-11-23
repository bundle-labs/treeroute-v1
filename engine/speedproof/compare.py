"""Re-runnable comparison for the speedproof runs (APP_PLAN.md 4.5, speedups 2 and 3).

Reads ONLY saved outputs of finished runs; writes nothing except the optional --json summary.

    py -3.9 compare.py                                   # the default trio in D:/treeroute/speedproof
    py -3.9 compare.py --golden D:/.../golden_smoke --w1 D:/.../fast_w1 --w8 D:/.../fast_w8
    py -3.9 compare.py --pair D:/a D:/b                  # any two run folders
    py -3.9 compare.py --json D:/treeroute/speedproof/compare_u2.json
    py -3.9 compare.py --gates [--json ...]              # the speedproof gate table (GATES below)

What is compared, per pair of run folders:
  predictions.parquet   file sha256; every column bit for bit; max |diff| per p_<arm> column
  inner_preds.npz       every array bit for bit, plus the file sha256 for information (the gate
                        is the arrays: zip metadata is not part of the result); max |diff| per P_<arm>.
                        NOTE: the shipped script stores these surfaces as FLOAT32 (SURF[name] =
                        P.astype(np.float32)), so this file cannot show a difference near 1e-13.
  speedproof_inner_f64.npz   (copy runs from 2026-09-28 13:30 on) the same inner surfaces in FLOAT64,
                        plus the contract check's single-penalty route P_chk. Compared, and part of
                        the IDENTICAL verdict, only when BOTH folders have it; else reported absent.
  inner_candidates.csv  file sha256; max |diff| and the number of differing rows of every numeric
                        column (these scores are computed from the FLOAT64 inner surfaces)
  per_region.csv, per_year.csv   the same
  code version          verdict.json["speedproof"]["code_sha256"] for copy runs (13:30 on), or
                        launcher.json["shipped_sha256"] for run_shipped_blas1.py runs
  verdict.json          canonical JSON after removing the keys that MUST differ between runs
                        (argv, started, finished, timings, config.RUN_DIR, speedproof); every
                        remaining leaf that differs is listed with both values
  decisions             adopted arm, penalties, eligible arms, contrast verdicts, and every test /
                        inner-best MAE rounded to 6 decimals
  timings               from run.log: the script's own [timing] phases, the per-matrix "columns"
                        lines and (copy only) the "router" lines; the shipped script logs minutes
                        at 0.1 precision, so seconds are ALSO derived from the [HH:MM:SS] stamps.

Verdict for a pair: IDENTICAL means every compared array, file and non-volatile verdict leaf is
bit-for-bit equal. Otherwise the numbers are printed so the size of the gap can be read.
"""
import argparse
import hashlib
import json
import os
import re
import sys

import numpy as np
import pandas as pd

ROOT = "D:/treeroute/speedproof"
VOLATILE = {("argv",), ("started",), ("finished",), ("timings",), ("config", "RUN_DIR"),
            ("speedproof",)}
CSVS = ("inner_candidates.csv", "per_region.csv", "per_year.csv")
F64 = "speedproof_inner_f64.npz"


def _r(n):
    return os.path.join(ROOT, n)


# The speedproof gate table (--gates): (label, run A, run B, expected). "IDENTICAL" must hold bit for
# bit on everything compared; "GAP" is reported with its size, and passes if the decisions are equal.
GATES = [
    ("G1 final file, default path (8 workers, pinned router) == copy serial reference",
     _r("wide_w1"), _r("wide_final_w8"), "IDENTICAL"),
    ("G2 final file + finite-once, 8 workers == copy serial reference",
     _r("wide_w1"), _r("wide_final_fo_w8"), "IDENTICAL"),
    ("G3 final file: 1 worker vs 8 workers, finite-once (incl. float64 inner surfaces)",
     _r("wide_final_fo_w1"), _r("wide_final_fo_w8"), "IDENTICAL"),
    ("G4 final file: finite-once off vs on, 8 workers (incl. float64 inner surfaces)",
     _r("wide_final_w8"), _r("wide_final_fo_w8"), "IDENTICAL"),
    ("G5 SPEEDUP 2 alone (8 tree threads, per-tree scan, shipped router) == shipped script",
     _r("wide_golden"), _r("wide_final_trees8_fo0"), "IDENTICAL"),
    ("G6 speedup 2 + finite-once (8 tree threads, shipped router) == shipped [earlier file version]",
     _r("wide_golden"), _r("wide_trees8_unpinned"), "IDENTICAL"),
    ("G7 SPEEDUP 3 PLAN GATE: shipped script at BLAS 1 == copy, 8 router workers at BLAS 1",
     _r("wide_golden_blas1"), _r("wide_final_w8"), "IDENTICAL"),
    ("G8 the gap is the BLAS thread count: shipped as launched vs shipped at BLAS 1",
     _r("wide_golden"), _r("wide_golden_blas1"), "GAP"),
    ("G9 final file, U2 smoke flags (primal path, Part 556 regression gate) == earlier copy",
     _r("fast_w1"), _r("final2_u2_w8"), "IDENTICAL"),
    ("G10 final file, U2 smoke flags == shipped script",
     _r("golden_smoke"), _r("final2_u2_w8"), "IDENTICAL"),
]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def bits_equal(a, b):
    """True iff two arrays have the same dtype, shape and bytes (NaN payloads included)."""
    a, b = np.asarray(a), np.asarray(b)
    if a.dtype != b.dtype or a.shape != b.shape:
        return False
    if a.dtype.kind == "O":
        return bool(np.all(a == b))
    return np.ascontiguousarray(a).tobytes() == np.ascontiguousarray(b).tobytes()


def maxabs(a, b):
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    if a.shape != b.shape:
        return float("nan")
    nan_a, nan_b = np.isnan(a), np.isnan(b)
    if not np.array_equal(nan_a, nan_b):
        return float("inf")                      # a NaN in one run and a number in the other
    ok = ~nan_a
    return float(np.max(np.abs(a[ok] - b[ok]))) if ok.any() else 0.0


def cmp_parquet(da, db):
    fa, fb = os.path.join(da, "predictions.parquet"), os.path.join(db, "predictions.parquet")
    A, B = pd.read_parquet(fa), pd.read_parquet(fb)
    out = dict(file_sha_equal=sha(fa) == sha(fb), rows=(len(A), len(B)),
               columns_equal=list(A.columns) == list(B.columns), col_bits_equal={},
               arm_maxabs={})
    for c in A.columns:
        if c not in B.columns:
            out["col_bits_equal"][c] = False
            continue
        out["col_bits_equal"][c] = bits_equal(A[c].to_numpy(), B[c].to_numpy())
        if c.startswith("p_"):
            out["arm_maxabs"][c[2:]] = maxabs(A[c].to_numpy(), B[c].to_numpy())
    out["all_bits_equal"] = (out["columns_equal"] and len(A) == len(B)
                             and all(out["col_bits_equal"].values()))
    return out


def cmp_npz(da, db):
    fa, fb = os.path.join(da, "inner_preds.npz"), os.path.join(db, "inner_preds.npz")
    out = dict(file_sha_equal=sha(fa) == sha(fb), arr_bits_equal={}, arm_maxabs={})
    with np.load(fa, allow_pickle=False) as A, np.load(fb, allow_pickle=False) as B:
        ka, kb = sorted(A.files), sorted(B.files)
        out["keys_equal"] = ka == kb
        for k in ka:
            if k not in kb:
                out["arr_bits_equal"][k] = False
                continue
            out["arr_bits_equal"][k] = bits_equal(A[k], B[k])
            if k.startswith("P_"):
                out["arm_maxabs"][k[2:]] = maxabs(A[k], B[k])
    out["all_bits_equal"] = out["keys_equal"] and all(out["arr_bits_equal"].values())
    return out


def cmp_csv(da, db, name):
    fa, fb = os.path.join(da, name), os.path.join(db, name)
    A, B = pd.read_csv(fa), pd.read_csv(fb)
    out = dict(file_sha_equal=sha(fa) == sha(fb), shape=(A.shape, B.shape), col_maxabs={},
               nonnum_equal=True)
    if A.shape != B.shape or list(A.columns) != list(B.columns):
        out["nonnum_equal"] = False
        return out
    out["col_nrows_diff"] = {}
    out["n_rows"] = int(len(A))
    for c in A.columns:
        if A[c].dtype.kind in "fiu" and B[c].dtype.kind in "fiu":
            a_, b_ = A[c].to_numpy(np.float64), B[c].to_numpy(np.float64)
            out["col_maxabs"][c] = maxabs(a_, b_)
            same = (a_ == b_) | (np.isnan(a_) & np.isnan(b_))
            out["col_nrows_diff"][c] = int((~same).sum())
        elif not A[c].fillna("<NA>").astype(str).equals(B[c].fillna("<NA>").astype(str)):
            out["nonnum_equal"] = False
    return out


def cmp_f64(da, db):
    """The copy-only float64 inner surfaces, compared only when BOTH runs have them."""
    fa, fb = os.path.join(da, F64), os.path.join(db, F64)
    ha, hb = os.path.exists(fa), os.path.exists(fb)
    out = dict(present=(ha, hb), arr_bits_equal={}, arm_maxabs={}, all_bits_equal=None)
    if not (ha and hb):
        return out
    with np.load(fa, allow_pickle=False) as A, np.load(fb, allow_pickle=False) as B:
        ka = sorted(k for k in A.files if k.startswith("P_"))
        kb = sorted(k for k in B.files if k.startswith("P_"))
        out["keys_equal"] = ka == kb
        for k in ka:
            if k not in kb:
                out["arr_bits_equal"][k] = False
                continue
            out["arr_bits_equal"][k] = bits_equal(A[k], B[k])
            out["arm_maxabs"][k[2:]] = maxabs(A[k], B[k])
    out["all_bits_equal"] = out["keys_equal"] and all(out["arr_bits_equal"].values())
    return out


def code_id(d):
    """Which code made a run folder: the copy's own sha256, or the shipped file's (launcher runs)."""
    try:
        with open(os.path.join(d, "verdict.json"), encoding="utf-8") as f:
            sp = json.load(f).get("speedproof")
    except (OSError, ValueError):
        sp = None
    if sp and sp.get("code_sha256"):
        return "copy, sha256 %s" % sp["code_sha256"]
    lj = os.path.join(d, "launcher.json")
    if os.path.exists(lj):
        with open(lj, encoding="utf-8") as f:
            L = json.load(f)
        return ("SHIPPED script, sha256 %s, via run_shipped_blas1.py (every BLAS at 1 thread at the "
                "end: %s)" % (L.get("shipped_sha256"), L.get("blas_all_one_thread_at_end")))
    if sp:
        return "copy, version NOT recorded (made before 2026-09-28 13:30)"
    return "shipped script (no speedproof block; version not recorded in the folder)"


def _strip(d, path=()):
    if isinstance(d, dict):
        return {k: _strip(v, path + (k,)) for k, v in d.items() if path + (k,) not in VOLATILE}
    return d


def _leaves(d, path=()):
    if isinstance(d, dict):
        for k, v in d.items():
            yield from _leaves(v, path + (str(k),))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            yield from _leaves(v, path + (str(i),))
    else:
        yield path, d


def cmp_verdict(da, db):
    with open(os.path.join(da, "verdict.json"), encoding="utf-8") as f:
        A = json.load(f)
    with open(os.path.join(db, "verdict.json"), encoding="utf-8") as f:
        B = json.load(f)
    sa, sb = _strip(A), _strip(B)
    la, lb = dict(_leaves(sa)), dict(_leaves(sb))
    diffs = []
    for k in sorted(set(la) | set(lb)):
        va, vb = la.get(k, "<absent>"), lb.get(k, "<absent>")
        if va != vb:
            d = None
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                d = abs(float(va) - float(vb))
            diffs.append(("/".join(k), va, vb, d))
    dec = decisions(A), decisions(B)
    return dict(canonical_equal=json.dumps(sa, sort_keys=True) == json.dumps(sb, sort_keys=True),
                n_leaf_diffs=len(diffs), leaf_diffs=diffs,
                max_numeric_leaf_diff=max([d[3] for d in diffs if d[3] is not None], default=0.0),
                decisions_a=dec[0], decisions_b=dec[1], decisions_equal=dec[0] == dec[1])


def decisions(V):
    """Everything a reader acts on, with MAEs rounded to 6 decimals."""
    r6 = lambda x: None if x is None else round(float(x), 6)       # noqa: E731
    return dict(adopted=V.get("adopted"), penalty=V.get("penalty"), tree_pick=V.get("tree_pick"),
                penalty_tree_arms=V.get("penalty_tree_arms"), eligible=V.get("eligible"),
                edge=V.get("edge"),
                contrast_verdicts={k: v.get("verdict") for k, v in V.get("contrasts", {}).items()},
                test_mae6={k: r6(v.get("mae")) for k, v in V.get("test", {}).items()},
                inner_best_mae6={k: r6(v.get("mae")) for k, v in V.get("inner_best", {}).items()},
                regression_gate_worst=(V.get("regression_gate") or {}).get("worst"))


_TS = re.compile(r"^\[(\d\d):(\d\d):(\d\d)\] (.*)$")
# copy runs from 13:30 on split each matrix's seconds (SPEEDPROOF (g))
_SPLIT = re.compile(r"Vm build ([\d.]+) s \| predict ([\d.]+) s \| memmap copy\+flush ([\d.]+) s")


def timings(d):
    """Phase and per-matrix timings from run.log (the LAST run in the file)."""
    lines = open(os.path.join(d, "run.log"), encoding="utf-8").read().splitlines()
    start = max(i for i, l in enumerate(lines) if "RUN START" in l)
    # the pre-flight line is logged just BEFORE "RUN START"; include it as the clock origin
    i0 = start - 1 if start > 0 and "pre-flight" in lines[start - 1] else start
    recs, prev_t, day = [], None, 0
    for l in lines[i0:]:
        m = _TS.match(l)
        if not m:
            continue
        t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + day
        if prev_t is not None and t < prev_t:
            day += 86400
            t += 86400
        recs.append((t, m.group(4)))
        prev_t = t
    t_first = recs[0][0]
    out = dict(phases={}, phases_stamp_sec={}, columns=[], router=[], wall_stamp_sec=None)
    last_phase_t = t_first
    for i, (t, msg) in enumerate(recs):
        m = re.search(r"\[timing\] (.+?)\s+([\d.]+) min(?: \(([\d.]+) s\))?", msg)
        if m:
            nm = m.group(1).strip()
            out["phases"][nm] = float(m.group(3)) if m.group(3) else float(m.group(2)) * 60.0
            out["phases_stamp_sec"][nm] = t - last_phase_t
            last_phase_t = t
            continue
        m = re.search(r"columns (\S+)\s+([\d,]+) x (\d+) written in ([\d.]+) min(?: \(([\d.]+) s\))?",
                      msg)
        if m:
            sec = float(m.group(5)) if m.group(5) else None
            sp = _SPLIT.search(msg)
            out["columns"].append(dict(matrix=m.group(1), rows=int(m.group(2).replace(",", "")),
                                       trees=int(m.group(3)), sec_logged=sec,
                                       sec_stamp=t - recs[i - 1][0] if i else None,
                                       vm=float(sp.group(1)) if sp else None,
                                       predict=float(sp.group(2)) if sp else None,
                                       write=float(sp.group(3)) if sp else None))
            continue
        m = re.search(r"router\s+(\S+)\s+(\d+) cells in ([\d.]+) s", msg)
        if m:
            out["router"].append(dict(arm=m.group(1), cells=int(m.group(2)),
                                      sec=float(m.group(3))))
        if msg.strip().startswith("saved ->"):
            out["wall_stamp_sec"] = t - t_first
    out["columns_total_sec_logged"] = (sum(c["sec_logged"] for c in out["columns"])
                                       if all(c["sec_logged"] is not None for c in out["columns"])
                                       else None)
    out["columns_total_sec_stamp"] = sum(c["sec_stamp"] or 0 for c in out["columns"])
    for k in ("vm", "predict", "write"):
        vals = [c[k] for c in out["columns"]]
        out["columns_total_" + k] = (sum(vals) if vals and all(v is not None for v in vals)
                                     else None)
    out["router_total_sec"] = sum(r["sec"] for r in out["router"]) if out["router"] else None
    return out


def compare_pair(da, db):
    res = dict(a=da, b=db, code_a=code_id(da), code_b=code_id(db),
               parquet=cmp_parquet(da, db), npz=cmp_npz(da, db),
               csv={n: cmp_csv(da, db, n) for n in CSVS}, verdict=cmp_verdict(da, db),
               f64=cmp_f64(da, db))
    res["identical"] = bool(
        res["parquet"]["all_bits_equal"] and res["npz"]["all_bits_equal"]
        and all(c["file_sha_equal"] for c in res["csv"].values())
        and res["verdict"]["canonical_equal"]
        and res["f64"]["all_bits_equal"] is not False)
    arms = sorted(set(res["parquet"]["arm_maxabs"]) | set(res["npz"]["arm_maxabs"])
                  | set(res["f64"]["arm_maxabs"]))
    res["arm_maxabs"] = {a: dict(test=res["parquet"]["arm_maxabs"].get(a),
                                 inner=res["npz"]["arm_maxabs"].get(a),
                                 inner64=res["f64"]["arm_maxabs"].get(a)) for a in arms}
    res["max_any_arm"] = max([v for d in res["arm_maxabs"].values() for v in d.values()
                              if v is not None], default=0.0)
    return res


def _fmt(v):
    return "-" if v is None else "%.3g" % v


def _fmt2(v):
    return "-" if v is None else "%.2f" % v


def show_pair(label, r):
    p = print
    p("=" * 100)
    p("%s\n  A = %s\n      [%s]\n  B = %s\n      [%s]"
      % (label, r["a"], r.get("code_a"), r["b"], r.get("code_b")))
    p("  RESULT: %s" % ("IDENTICAL (bit for bit on every compared array, file and verdict leaf)"
                        if r["identical"] else "NOT identical -- sizes below"))
    pq, nz = r["parquet"], r["npz"]
    p("  predictions.parquet  file sha256 equal: %s | all columns bit-equal: %s | rows %s"
      % (pq["file_sha_equal"], pq["all_bits_equal"], pq["rows"]))
    bad = [c for c, ok in pq["col_bits_equal"].items() if not ok]
    if bad:
        p("      columns that differ: %s" % ", ".join(bad))
    p("  inner_preds.npz      all arrays bit-equal: %s (file sha256 equal: %s)"
      % (nz["all_bits_equal"], nz["file_sha_equal"]))
    bad = [k for k, ok in nz["arr_bits_equal"].items() if not ok]
    if bad:
        p("      arrays that differ: %s" % ", ".join(bad))
    f6 = r.get("f64", {})
    if f6.get("all_bits_equal") is None:
        pa, pb = f6.get("present", ("?", "?"))
        p("  %s  not compared: present in A %s, B %s (copy runs from 13:30 on only)" % (F64, pa, pb))
    else:
        p("  %s  all float64 arrays bit-equal: %s" % (F64, f6["all_bits_equal"]))
        bad = [k for k, ok in f6["arr_bits_equal"].items() if not ok]
        if bad:
            p("      arrays that differ: %s" % ", ".join(bad))
    for n, c in r["csv"].items():
        mx = max([v for v in c["col_maxabs"].values()], default=0.0)
        nd = {k: v for k, v in c.get("col_nrows_diff", {}).items() if v}
        p("  %-20s file sha256 equal: %s | max |diff| over numeric columns %.3g%s"
          % (n, c["file_sha_equal"], mx,
             "" if not nd else " | rows differing (of %d): %s" % (c.get("n_rows", 0), nd)))
    v = r["verdict"]
    p("  verdict.json         non-volatile content equal: %s | %d leaf diffs | max numeric leaf "
      "diff %.3g" % (v["canonical_equal"], v["n_leaf_diffs"], v["max_numeric_leaf_diff"]))
    for path, va, vb, d in v["leaf_diffs"][:12]:
        p("      %-58s %s  vs  %s" % (path, va, vb))
    if v["n_leaf_diffs"] > 12:
        p("      ... %d more" % (v["n_leaf_diffs"] - 12))
    p("  decisions (adopted arm, penalties, eligible, contrast verdicts, MAE to 6 dp) equal: %s"
      % v["decisions_equal"])
    da = v["decisions_a"]
    p("      adopted %s | penalty %s | tree_pick %s at %s | eligible %s"
      % (da["adopted"], da["penalty"], da["tree_pick"], da["penalty_tree_arms"], da["eligible"]))
    p("      contrasts: %s" % da["contrast_verdicts"])
    p("  max |diff| per arm (test = predictions.parquet p_<arm>, float64; inner(f32) = "
      "inner_preds.npz P_<arm>, FLOAT32 as shipped; inner64 = %s, copy runs only):" % F64)
    for a, d in r["arm_maxabs"].items():
        p("      %-18s test %-10s inner(f32) %-10s inner64 %s"
          % (a, _fmt(d["test"]), _fmt(d["inner"]), _fmt(d.get("inner64"))))
    p("  largest |diff| on any arm: %.3g" % r["max_any_arm"])


def show_timings(runs):
    print("=" * 100)
    print("TIMINGS (seconds; 'logged' = the script's own clock, 'stamp' = from [HH:MM:SS], 1 s "
          "resolution)")
    T = {k: timings(d) for k, d in runs.items()}
    names = list(T)
    phases = []
    for t in T.values():
        for ph in t["phases"]:
            if ph not in phases:
                phases.append(ph)
    print("  %-30s" % "phase" + "".join("%22s" % n for n in names))
    for ph in phases:
        print("  %-30s" % ph + "".join(
            "%22s" % ("%.1f / %d" % (T[n]["phases"][ph], T[n]["phases_stamp_sec"][ph])
                      if ph in T[n]["phases"] else "-") for n in names))
    print("  %-30s" % "  (logged / stamp)")
    print("  %-30s" % "tree answers, all matrices" + "".join(
        "%22s" % (("%.2f" % T[n]["columns_total_sec_logged"])
                  if T[n]["columns_total_sec_logged"] is not None
                  else "~%d (stamp)" % T[n]["columns_total_sec_stamp"]) for n in names))
    for k, lab in (("vm", "  of which Vm build"), ("predict", "  of which predict"),
                   ("write", "  of which memmap copy+flush")):
        print("  %-30s" % lab + "".join(
            "%22s" % _fmt2(T[n]["columns_total_" + k]) for n in names))
    print("  %-30s" % "router solves, all arms" + "".join(
        "%22s" % ("%.2f" % T[n]["router_total_sec"] if T[n]["router_total_sec"] is not None
                  else "n/a (not logged)") for n in names))
    def _rs(t):
        ph = t["phases_stamp_sec"]
        tree = (t["columns_total_sec_logged"] if t["columns_total_sec_logged"] is not None
                else t["columns_total_sec_stamp"])
        if "inner decision" in ph and "test pass" in ph:
            return "%.0f" % (ph["inner decision"] + ph["test pass"] - tree)
        return "-"
    print("  %-30s" % "inner+test minus tree answers" + "".join("%22s" % _rs(T[n]) for n in names))
    print("  %-30s" % "  (= routers + scoring; every run)")
    print("  %-30s" % "wall, pre-flight to saved" + "".join(
        "%22s" % T[n]["wall_stamp_sec"] for n in names))
    print("  per matrix (logged s, else stamp s):")
    mats = [c["matrix"] for c in T[names[0]]["columns"]]
    for i, m in enumerate(mats):
        row = []
        for n in names:
            cs = T[n]["columns"]
            if i < len(cs):
                c = cs[i]
                row.append("%.2f" % c["sec_logged"] if c["sec_logged"] is not None
                           else "~%d" % c["sec_stamp"])
            else:
                row.append("-")
        print("    %-26s" % ("%s (%s x %d)" % (m, format(T[names[0]]["columns"][i]["rows"], ","),
                                              T[names[0]]["columns"][i]["trees"]))[:60]
              + "".join("%22s" % x for x in row))
    return T


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--golden", default=os.path.join(ROOT, "golden_smoke"))
    ap.add_argument("--w1", default=os.path.join(ROOT, "fast_w1"))
    ap.add_argument("--w8", default=os.path.join(ROOT, "fast_w8"))
    ap.add_argument("--shipped", default=None,
                    help="optional: a shipped run folder the golden should reproduce (read only)")
    ap.add_argument("--extra", nargs="*", default=[],
                    help="further runs of the COPY (other worker counts / flags); each must be "
                         "IDENTICAL to --w1, and is added to the timing table")
    ap.add_argument("--pair", nargs=2, default=None, help="compare just these two run folders")
    ap.add_argument("--gates", action="store_true",
                    help="run the speedproof gate table (GATES); a missing run folder is reported")
    ap.add_argument("--json", default=None, help="write the full comparison here as JSON")
    a = ap.parse_args()

    summary = {}
    if a.gates:
        rows = []
        for label, da, db, expect in GATES:
            if not (os.path.isdir(da) and os.path.isdir(db)):
                rows.append((label, expect, "MISSING RUN", None, None))
                print("=" * 100 + "\n%s\n  skipped: %s or %s does not exist" % (label, da, db))
                continue
            r = compare_pair(da, db)
            show_pair(label, r)
            summary[label] = r
            ok = r["identical"] if expect == "IDENTICAL" else r["verdict"]["decisions_equal"]
            rows.append((label, expect, "PASS" if ok else "FAIL", r["max_any_arm"],
                         r["verdict"]["decisions_equal"]))
        runs = {}
        for g in GATES:
            for d in (g[1], g[2]):
                if os.path.isdir(d):
                    runs[os.path.basename(d)] = d
        summary["timings"] = show_timings(runs)
        print("=" * 100)
        print("GATE TABLE")
        for label, expect, verdict, mx, dec in rows:
            gid = label.split()[0]
            print("  %-4s %-11s expected %-9s | largest |diff| on any arm %-9s | decisions equal %s"
                  % (gid, verdict, expect, _fmt(mx), dec))
            print("       %s" % label[len(gid) + 1:])
        summary["gate_table"] = rows
    elif a.pair:
        r = compare_pair(*a.pair)
        show_pair("PAIR", r)
        summary["pair"] = r
        summary["timings"] = show_timings({"A": a.pair[0], "B": a.pair[1]})
    else:
        r18 = compare_pair(a.w1, a.w8)
        show_pair("GATE: copy --workers 1  vs  copy --workers 8   (must be IDENTICAL)", r18)
        rg1 = compare_pair(a.golden, a.w1)
        show_pair("GAP: shipped script (numpy BLAS 16 / scipy BLAS 4 in the router)  vs  copy "
                  "--workers 1 (BLAS 1 in the router)", rg1)
        summary.update(w1_vs_w8=r18, golden_vs_w1=rg1)
        runs = {"golden": a.golden, "w1": a.w1, "w8": a.w8}
        if a.shipped:
            rs = compare_pair(a.shipped, a.golden)
            show_pair("REPRODUCTION: shipped run  vs  fresh golden (same script, same flags)", rs)
            summary["shipped_vs_golden"] = rs
        rx = {}
        for d in a.extra:
            rx[d] = compare_pair(a.w1, d)
            show_pair("GATE: copy --workers 1  vs  %s   (must be IDENTICAL)" % d, rx[d])
            runs[os.path.basename(os.path.normpath(d))] = d
        summary["w1_vs_extra"] = rx
        summary["timings"] = show_timings(runs)
        print("=" * 100)
        print("GATE speedups 2+3 (1 vs 8 workers byte-identical): %s"
              % ("PASS" if r18["identical"] else "FAIL"))
        for d, r in rx.items():
            print("GATE %s identical to --workers 1: %s" % (d, "PASS" if r["identical"] else "FAIL"))
        print("GAP to the shipped script: largest |diff| on any arm %.3g; decisions equal: %s"
              % (rg1["max_any_arm"], rg1["verdict"]["decisions_equal"]))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=1, default=str)
        print("written: %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
