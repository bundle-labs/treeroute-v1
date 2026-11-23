"""Smoke of the BARDL loader scripts/bardl_shap.py (the NDVI published rival; scope (i)). Writes only
smoke/bardl_<label>/: its own sample and register, outputs, logs and smoke_report.json. It never writes the analysis'
SAMPLE_REGISTER.txt, sample/, out/, rebuild/ or logs/ (every bardl_shap.py run gets --log-dir, and the compare and
ridge children log under the smoke folder).

  py -3.9 -I -B smoke_bardl.py [--label smoke] [--step all|synthetic|exact|real|compare] [--fresh] [--no-ridge]

  synthetic  no real data (< 300 MB, < 1 min): bardl_shap's own functions (the same path as the owner's run, through
             shap_pipeline) on a synthetic world written as a small slim copy, through the adapter's own design() and
             predict(); checks (a)-(o) below
  exact      bardl_shap.py --exactness-only: every lead-0 test row of the NDVI human board (reads the board's files)
  real       its own sample: the rows of the first 3 groups of smoke/sample_ndvi_v3 and every row with a missing unit x
             month climate mean, renumbered, under its own register; bardl_shap.py on it, again (resume), with --rows
             10, and on doctored copies (the refusals, a stale piece); brute force on up to 10 real rows at both levels;
             the owner's run's own S-SAMPLE and S-BG functions (bardl_shap.background_rows and prediction_design) on
             every key of the full smoke sample (no SHAP value computed); the slim copy against the common export on
             every row of the groups: the values of the 9 players and the normal bit for bit, the keys issue and lead,
             the refit flag of the train part, and every background key a refit row of the export
  compare    compare_shap.py (a child with 1 thread, logging under the smoke) on the smoke's models root, holding BARDL,
             a copy of it marked declined by its guard and, unless --no-ridge, a ridge rival made by rival_shap.py on the
             same sample (a child with the board's 8 threads, logging under the smoke); then bardl_shap.py once more on
             that models root: skipped, with no REMINDER (compare_shap.py's own done record covers the BARDL piece)

Each step refuses when its own output folders exist, unless --fresh, which removes only those folders. Each step that
reads real data re-checks the heavy-job guard first (no lock file D:/treeroute/tmp/treeroute_heavy_job.lock, no SHAP
process of the owner, at least 6 GiB of free RAM) and stops before reading anything when it fails (exit 4). Exit 1
when a check fails.

Synthetic checks:
  (a) feature-level phi against brute-force Shapley values (shapv1_treeshap.brute_force over all 2^10 coalitions;
      f = the adapter's design() on [the unit's test rows + the hybrid rows], then predict's arithmetic) on 7 explained
      rows with 5-9 background rows: all finite; a missing climate value on x only; on one b only; a missing unit x
      month climate mean; a NaN hist_last on one b; players equal on every b; a fallback unit;
  (b) the grouped game (4 variables) likewise;
  (c) additivity at both levels;
  (d) S-ZERO: phi exactly 0 wherever the mask holds; nonzero for every player of the all-finite row; the
      missing-mean row's affected single term and mean term exactly 0; the fallback row all 0;
  (e) the per-lag linear split differs from the exact value on the one-sided-NaN rows and agrees on the all-finite row;
  (f) design() on background rows alone sets NDVI lags to 0 (the hazard); the mixed call adds only the missing ones;
  (g) our evaluator against the adapter's predict() on explained and background rows;
  (h) background_design() stops S-BG on a background normal moved by +1e-9 (the adapter's refusal) and by +1e-13 and
      -1e-13 (the bitwise check); read_background() stops S-BG on a key that is not a refit row and on a duplicated key;
      background_rows() stops S-BG on a background row whose issue is of another calendar month and on one of another
      lead; prediction_design() stops S-SAMPLE on a sample row of a unit without BARDL parameters;
  (i) exactness() reproduces a synthetic board (with clipped rows) bit for bit; a one-ulp coefficient fails exactly
      when it changes a prediction; a changed coefficient stops S-EXACT with exactness.json and FAILED.json;
  (j) S-ENV passes on the installed versions and stops on a doctored version and on a board without versions;
  (k) the writer stops S-EVAL on a background value moved by 1e-6 and writes the three files otherwise;
  (l) a recompute start and a stop remove the folder's done record, so compare's discovery rule skips the folder;
  (m) a slim file whose bytes are not its manifest's is refused (InputMismatch);
  (n) unequal normals (outside B2): the offset goes to 'normal' exactly and additivity holds;
  (o) bardl_shap.main() itself, end to end, on synthetic board trees: exit 0 with the pipeline's own values and every
      check; a second run skipped; a skip beside a comparison that does not list BARDL, or that was made from other
      rows, logs a REMINDER, and beside a comparison made from its rows does not; --exactness-only writes
      exactness.json only; an unregistered sample stops S-SAMPLE (its detail without a repeated 'STOP S-SAMPLE'
      prefix); a wrong preds record, a wrong registry record, registry bytes that no longer parse (checked
      before any parse) and a wrong provenance stop S-EXACT (exactness.json and FAILED.json), a wrong library version
      stops S-ENV, and no stop leaves a done record (a finished piece of an earlier run included).
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
import shapv1_common as C  # noqa: E402   (standard library only at import: numpy loads inside the steps)

THIS = os.path.abspath(__file__)
BARDL = os.path.join(SCRIPTS, "bardl_shap.py")
ADAPTER = "D:/treeroute/human_rivals_build/human/adapters/ndvi_bardl.py"
SOURCE_SAMPLE = os.path.join(C.ROOT, "smoke", "sample_ndvi_v3")
LOCK = "D:/treeroute/tmp/treeroute_heavy_job.lock"
OWNER_RX = re.compile(r"run_shap|tr_rebuild|tr_shap|rival_shap|compare_shap|make_sample")
MIN_FREE_GIB = 6.0
STEPS = ("synthetic", "exact", "real", "compare")
STEP_DIRS = {"synthetic": ["synthetic"], "exact": ["exact"], "real": ["sample", "out", "out_rows10", "refusals"],
             "compare": [os.path.join("out", "rival_bardl_h1_declined"), os.path.join("out", "rival_ridge"),
                         os.path.join("out", "compare")]}
WATCH_LOGS = ("bardl_shap", "compare_ndvi", "rival_shap_ndvi", "smoke_bardl")
REPORT = {}
FAIL = []


class GuardStop(Exception):
    pass


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="smoke")
    ap.add_argument("--step", default="all", choices=("all",) + STEPS + ("compare-child", "ridge-child"))
    ap.add_argument("--fresh", action="store_true", help="remove the step's own folders first")
    ap.add_argument("--no-ridge", action="store_true", help="compare step: no ridge rival (the declined copy only)")
    a = ap.parse_args()
    if not re.match(r"^[A-Za-z0-9_-]{1,40}$", a.label):
        raise SystemExit("REFUSED: --label must be letters, digits, _ or -")
    return a


def check(name, ok, value):
    REPORT[name] = {"pass": bool(ok), "value": value}
    print("%-78s %s  %s" % (name, "PASS" if ok else "FAIL", value), flush=True)
    if not ok:
        FAIL.append(name)


def guard():
    """(ok, record): no heavy-job lock, no SHAP process of the owner, enough free RAM. This smoke's own processes run
    bardl_shap.py and smoke_bardl.py, which the pattern does not match."""
    import psutil
    lock = os.path.exists(LOCK)
    own = 0
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cl = " ".join(p.info.get("cmdline") or [])
        except Exception:
            continue
        if OWNER_RX.search(cl):
            own += 1
    free = psutil.virtual_memory().available / 2 ** 30
    ok = (not lock) and own == 0 and free >= MIN_FREE_GIB
    return ok, {"lock_file": lock, "shap_processes": own, "available_gib": round(free, 2)}


def need_guard(what, log):
    ok, g = guard()
    log("heavy-job guard before %s: %s" % (what, g))
    if not ok:
        REPORT.setdefault("_guard_stops", []).append({"before": what, "guard": g})
        raise GuardStop("the heavy-job guard failed before %s: %s" % (what, g))


def py_cmd():
    return [sys.executable, "-I", "-B"]


def clean_env():
    """The environment without thread pins (each child sets its own before numpy loads)."""
    return {k: v for k, v in os.environ.items() if not k.upper().startswith(("OMP_", "OPENBLAS_", "MKL_", "NUMEXPR_",
                                                                              "BLIS_", "VECLIB_"))}


def run_child(cmd, log, what):
    t0 = time.time()
    rc = subprocess.call(cmd, env=clean_env())
    log("%s: exit %d in %.1f s" % (what, rc, time.time() - t0))
    return rc


def bardl_cmd(W, *extra):
    return py_cmd() + [BARDL, "--problem", "ndvi", "--lead", "0", "--log-dir", os.path.join(W, "logs")] + list(extra)


def logs_state():
    """Size and time of the analysis' log files this smoke could touch (they must not change)."""
    out = {}
    if os.path.isdir(C.LOGS):
        for f in sorted(os.listdir(C.LOGS)):
            if f.startswith(WATCH_LOGS):
                st = os.stat(os.path.join(C.LOGS, f))
                out[f] = [st.st_size, st.st_mtime_ns]
    return out


def prepare(W, step, fresh, log):
    ex = [os.path.join(W, d) for d in STEP_DIRS[step] if os.path.exists(os.path.join(W, d))]
    if ex and not fresh:
        raise SystemExit("REFUSED: %s exists from an earlier smoke; pass --fresh to remove the step's own folders" % ex)
    for d in ex:
        shutil.rmtree(C.assert_writable(d))
        log("--fresh: removed %s" % d)


def expect_stop(fn, folder, gate):
    """Run fn, which must stop with exit 3 and a FAILED.json in folder naming gate (a gate field, or a failed check
    of the writer). Returns (ok, record)."""
    try:
        fn()
        return False, "no stop"
    except SystemExit as exc:
        f = os.path.join(folder, "FAILED.json")
        rec = C.read_json(f) if os.path.isfile(f) else {}
        got = rec.get("gate") or [k for k, v in (rec.get("checks_passed") or {}).items() if not v]
        ok = exc.code == 3 and (got == gate or (isinstance(got, list) and gate in got))
        return bool(ok), {"exit": exc.code, "gate": got, "detail": str(rec.get("detail"))[:200]}


# ---------------------------------------------------------------------------------------------------------------
# the synthetic world (no real data)
def synth_world(BS, AD, np, pd, root):
    """Three units (two scored, one fallback) of two groups: train 2010-2019 (2010 rows are not refit rows), test
    2020-2023, written as a small slim copy (test and train files, a manifest with SHA-256); seven explained rows
    with their B2 keys; a JSON round-tripped params map (one unit x month climate mean removed)."""
    rng = np.random.default_rng(20261113)
    spy, off = 12, 1
    hist = ["x__hist_last_1", "x__hist_last_2", "x__hist_last_3", "x__hist_mean_12"]
    extras = ["x__V02_total_precip_mm", "x__V02_total_precip_mm_lag1", "x__V02_total_precip_mm_lag2",
              "x__V30_soil_moisture_pct", "x__V30_soil_moisture_pct_lag1", "x__V30_soil_moisture_pct_lag2"]
    rival = {"id": "bardl_h1", "kind": "M", "runner": "adapters.ndvi_bardl",
             "options": {"history": ["hist_last_1", "hist_last_2", "hist_last_3"],
                         "climate": {"precip": ["V02_total_precip_mm", "V02_total_precip_mm_lag1",
                                                "V02_total_precip_mm_lag2"],
                                     "soil_moisture": ["V30_soil_moisture_pct", "V30_soil_moisture_pct_lag1",
                                                       "V30_soil_moisture_pct_lag2"]},
                         "min_fit_rows": 36, "standardize": True}}
    opt = AD._options(rival)

    def normal(level, t):
        m = (np.asarray(t, np.int64) - 1) % 12 + 1
        return np.round(level + 0.1 * np.sin(m * 0.5236), 6)
    frames = []
    for u, g, lev in (("ua", "g1", 0.30), ("ub", "g1", 0.45), ("ufb", "g2", 0.20)):
        t = np.arange(24241 - 120, 24289, dtype=np.int64)
        n = t.size
        f = pd.DataFrame({"unit": u, "group": g, "time": t, "issue": t, "lead": np.zeros(n, np.int64)})
        f["nfit__identity"] = normal(lev, t)
        for k in (1, 2, 3):
            f["x__hist_last_%d" % k] = normal(lev, t - 1 - k) + rng.normal(0, 0.05, n)
        f["x__hist_mean_12"] = rng.normal(lev, 0.02, n)
        for col, mu_, sd_ in (("x__V02_total_precip_mm", 60.0, 25.0), ("x__V30_soil_moisture_pct", 30.0, 6.0)):
            v = rng.normal(mu_, sd_, n)
            f[col] = v
            f[col + "_lag1"] = np.r_[rng.normal(mu_, sd_, 1), v[:-1]]
            f[col + "_lag2"] = np.r_[rng.normal(mu_, sd_, 2), v[:-2]]
        f["r_refit"] = (t >= 24241 - 108) & (t <= 24240)
        frames.append(f)
    A = pd.concat(frames, ignore_index=True)

    def tm(month, year):
        return 24241 + (year - 2020) * 12 + (month - 1)
    # (case, unit, month, year, background rows)
    cases = [("all finite", "ua", 3, 2021, 5), ("a missing climate value on x only", "ua", 10, 2022, 6),
             ("a missing climate value on one b only", "ub", 4, 2020, 7),
             ("a missing unit x month climate mean", "ua", 5, 2023, 8), ("a NaN hist_last on one b", "ub", 8, 2021, 9),
             ("players equal on every b", "ub", 11, 2022, 5), ("a fallback unit", "ufb", 2, 2020, 6)]
    S_rows, B_rows = [], []
    for i, (name, u, m, y, nb) in enumerate(cases):
        tx = tm(m, y)
        S_rows.append({"row": i, "unit": u, "group": "g2" if u == "ufb" else "g1", "time": tx, "year": y})
        tbs = sorted(tm(m, yb) for yb in range(2019, 2019 - nb, -1))
        B_rows += [{"row": i, "unit": u, "time": tb} for tb in tbs]
        at = lambda uu, tt: (A["unit"] == uu) & (A["time"] == tt)  # noqa: E731
        if i == 1:
            A.loc[at(u, tx), "x__V02_total_precip_mm_lag1"] = np.nan
        if i == 2:
            A.loc[at(u, tbs[0]), "x__V30_soil_moisture_pct"] = np.nan
        if i == 4:
            A.loc[at(u, tbs[1]), "x__hist_last_2"] = np.nan
        if i == 5:
            for col in ("x__V30_soil_moisture_pct_lag1", "x__hist_last_1"):
                A.loc[(A["unit"] == u) & A["time"].isin(tbs), col] = float(A.loc[at(u, tx), col].iloc[0])
    S = pd.DataFrame(S_rows)
    B = pd.DataFrame(B_rows)
    R = A[A["r_refit"]].reset_index(drop=True)
    cm = AD.climate_means(R["unit"].astype(str).to_numpy(), R["issue"].to_numpy(np.int64),
                          R[extras].reset_index(drop=True), opt, spy)
    del cm["precip"]["ua|5"]
    names = AD.feature_names(opt)
    scale = np.array([0.05] * 3 + [25.0] * 3 + [6.0] * 3 + [20.0, 5.0])
    U = {}
    for u in ("ua", "ub"):
        coef = rng.normal(0, 0.05, 11)
        coef = np.where(np.abs(coef) < 0.01, 0.01, coef)
        U[u] = {"fallback": False, "n": 100, "coef": coef.tolist(), "intercept": float(rng.normal(0, 0.01)),
                "mu": (rng.normal(0, 0.1, 11) * scale).tolist(), "sd": (scale * rng.uniform(0.8, 1.2, 11)).tolist(),
                "alpha": 1.0, "lambda": 1.0}
    U["ufb"] = {"fallback": True, "n": 10}
    params = json.loads(json.dumps({"format": BS.FORMAT, "adapter": AD.ADAPTER_FORMAT, "rival": "bardl_h1", "lead": 0,
                                    "fit_set": "refit", "features": names, "min_fit_rows": 36, "steps_per_year": spy,
                                    "start_offset_steps": off, "standardize": True, "climate_means": cm, "units": U,
                                    "counts": {}, "estimator": "synthetic"}))
    keys = list(AD.KEYS)
    files = []
    slim_dir = C.makedirs(os.path.join(root, "slim"))
    for g in ("g1", "g2"):
        for part, cols in (("test", keys + ["nfit__identity"] + hist + extras),
                           ("train", keys + ["r_refit", "nfit__identity"] + hist + extras)):
            sel = (A["group"] == g) & ((A["time"] > 24240) if part == "test" else (A["time"] <= 24240))
            fr = A.loc[sel, cols].sort_values(["unit", "time"]).reset_index(drop=True)
            p = C.write_parquet(os.path.join(slim_dir, part, g + ".parquet"), fr)
            files.append({"part": part, "stem": g, "group": g, "path": "%s/%s.parquet" % (part, g),
                          "sha256": C.sha256_file(p), "rows": len(fr)})
    manifest = {"format": "human-slim/1", "lead": 0, "files": files, "columns": {"history": hist, "extras": extras}}
    run_ns = BS.SimpleNamespace(derived={"R17": {"inputs": {"steps_per_year": spy},
                                                 "value": {"start_offset_steps": off}}})
    export_x = hist + extras
    return BS.SimpleNamespace(rival=rival, opt=opt, params=params, S=S, B=B, A=A, slim_dir=slim_dir,
                              manifest=manifest, run=run_ns, export_x=export_x, spy=spy, off=off, cases=cases,
                              hist=hist, extras=extras)


def synth_board(BS, root, name, w, preds, legal, change=None):
    """A synthetic board tree for bardl_shap.main() itself (no real data): a human board with its picks, lead_0
    records (done, preds, coverage, map), the slim copy (the synthetic world's files), a registry with a copy of the
    adapter next to it, a run folder with derived.json, an export lead manifest and a common board.json; every record
    hash-consistent unless change(name, record) alters one. Returns the PROBLEMS entry to patch in."""
    base = os.path.join(root, "e2e", name)
    if os.path.isdir(base):
        shutil.rmtree(C.assert_writable(base))
    change = change or (lambda what, rec: rec)
    human = C.makedirs(os.path.join(base, "human_board"))
    ad_dir = C.makedirs(os.path.join(base, "human", "adapters"))
    shutil.copyfile(ADAPTER, C.assert_writable(os.path.join(ad_dir, "ndvi_bardl.py")))
    reg = C.write_text(os.path.join(base, "human", "registry", "ndvi.yaml"),
                       json.dumps({"package": "ndvi", "rivals": [w.rival]}, indent=1))     # JSON is YAML
    run_dir = C.makedirs(os.path.join(base, "run"))
    C.write_json(os.path.join(run_dir, "derived.json"), {"R17": {"inputs": {"steps_per_year": w.spy},
                                                                 "value": {"start_offset_steps": w.off}}})
    exman = {"files": [{"part": f["part"], "group": f["group"], "path": f["path"],
                        "sha256": "source-%s-%s" % (f["part"], f["group"])} for f in w.manifest["files"]],
             "columns": {"x": w.export_x}}
    exman = change("export_manifest", exman)
    ex_p = C.write_json(os.path.join(base, "export", "lead_0", "export_manifest.json"), exman)
    slim_dir = C.makedirs(os.path.join(human, "slim", "lead_0"))
    files = []
    for f in w.manifest["files"]:
        dst = os.path.join(slim_dir, *f["path"].split("/"))
        C.makedirs(os.path.dirname(dst))
        shutil.copyfile(os.path.join(w.slim_dir, *f["path"].split("/")), C.assert_writable(dst))
        files.append(dict(f, source_sha256="source-%s-%s" % (f["part"], f["group"])))
    kept = C.write_json(os.path.join(slim_dir, "export_manifest.json"), exman)
    season = {"kind": "month_of_year", "steps_per_year": w.spy}
    sm = {"format": "human-slim/1", "lead": 0, "run": {"fingerprint": "synthetic"}, "links": ["identity"],
          "legal": list(legal), "c": None, "cuts": {"fit_cut": 24240, "guard_cut": 24204}, "season": season,
          "offset_steps": w.off, "source_export_manifest_sha256": C.sha256_file(ex_p),
          "export_manifest": {"path": "export_manifest.json", "sha256": C.sha256_file(kept)}, "files": files,
          "columns": w.manifest["columns"]}
    sm_p = C.write_json(os.path.join(slim_dir, "slim_manifest.json"), change("slim_manifest", sm))
    cb_p = C.write_json(os.path.join(base, "board", "board.json"), {"run": {
        "fingerprint": "synthetic", "c": {"0": None}, "ub": 1.0, "links": ["identity"], "legal": list(legal)}})
    ldir = C.makedirs(os.path.join(human, "lead_0"))
    p_p = C.write_parquet(os.path.join(ldir, "preds_bardl_h1.parquet"), preds)
    c_p = C.write_parquet(os.path.join(ldir, "coverage_bardl_h1.parquet"),
                          preds[["unit", "group", "time", "issue", "lead", "covered"]])
    C.write_json(os.path.join(ldir, "map_bardl_h1.json"), {"method": "adapters.ndvi_bardl", "params": w.params,
                                                          "guard_params": None})
    C.write_json(os.path.join(ldir, "done_bardl_h1.json"), change("done", {
        "status": "ok", "lead": 0, "rival": "bardl_h1", "info": {"params_file": "map_bardl_h1.json"},
        "preds_sha256": C.sha256_file(p_p), "test_rows": int(len(preds)),
        "guard": {"passed": True, "rows": 1, "comparator": "synthetic"}}))
    have = C.versions()
    hb = {"format": "human-board/1", "dry": False,
          "run": {"fingerprint": "synthetic", "links": ["identity"], "legal": list(legal), "c": {"0": None}, "ub": 1.0,
                  "cuts": {"0": {"fit_cut": 24240, "guard_cut": 24204}}, "season": season, "offset_steps": w.off,
                  "file_sha256": {"derived.json": C.sha256_file(os.path.join(run_dir, "derived.json"))}},
          "registry": {"file": reg, "registry": C.sha256_file(reg)},
          "slim": {"0": {"manifest_sha256": C.sha256_file(sm_p)}}, "common_board": {"sha256": C.sha256_file(cb_p)},
          "versions": {k: have[k] for k in ("lightgbm", "numpy", "pandas", "pyarrow", "scikit-learn",
                                            "scikit-learn-intelex", "threadpoolctl")},
          "constants": {"threads": 8}, "tool_code_sha256": "synthetic"}
    hb_p = C.write_json(os.path.join(human, "human_board.json"), change("human_board", hb))
    C.write_json(os.path.join(human, "human_picks.json"), change("picks", {
        "board_json_sha256": C.sha256_file(hb_p), "run_fingerprint": "synthetic",
        "picks": {"bardl_h1": {"status": "ok", "leads": {"0": {"tier": "P", "coverage": {
            "sha256": C.sha256_file(c_p)}}}}}, "slim": {"0": {"manifest_sha256": C.sha256_file(sm_p)}}}))
    return {"run": run_dir, "board": os.path.join(base, "board"), "export": os.path.join(base, "export"),
            "human": human}


def run_main(BS, argv, patch):
    """bardl_shap.main(argv) in this process with the ndvi PROBLEMS entry patched (restored after); the exit code."""
    keep = C.PROBLEMS["ndvi"]
    C.PROBLEMS["ndvi"] = dict(keep, **patch)
    try:
        try:
            rc = BS.main(argv)
        except SystemExit as exc:
            rc = exc.code if isinstance(exc.code, int) else 1
    finally:
        C.PROBLEMS["ndvi"] = keep
    return rc


def adapter_f(BS, AD, np, pd, opt, params, T_unit, b_rows, players9, hist, extras, spy, off, lead, link):
    """f for brute force: hybrid raw players (rows of Z, one per background row) and the normal, designed with the
    unit's test rows by the adapter's own design(), then predict's arithmetic (:336-349)."""
    unit = str(b_rows["unit"].iloc[0])
    m = params["units"][unit]
    nT = len(T_unit)
    base_frame = b_rows.reset_index(drop=True)
    tu = T_unit.reset_index(drop=True)[list(base_frame.columns)]

    def f(Z):
        Z = np.asarray(Z, np.float64)
        hyb = base_frame.copy()
        for j, c in enumerate(players9):
            hyb[c] = Z[:, j]
        hyb["nfit__" + link] = Z[:, len(players9)]
        fr = pd.concat([tu, hyb], ignore_index=True)
        s = BS.slim_set(fr, hist, extras, link, AD.KEYS)
        X, _, _ = AD.design(s.keys, s.normal[link], s.history, s.extras, params["climate_means"], opt, lead, spy, off)
        X = np.where(np.isfinite(X), X, 0.0)[nT:]
        z0 = Z[:, len(players9)]
        if m["fallback"]:
            return z0
        Xu = (X - np.asarray(m["mu"], np.float64)) / np.asarray(m["sd"], np.float64)
        return z0 + (float(m["intercept"]) + Xu @ np.asarray(m["coef"], np.float64))
    return f


def brute_rows(BS, AD, TS, np, pd, opt, params, T, Kb, epos, bg_lists, rows, ns, hist, extras, spy, off, link):
    """Brute force at both levels on the given explained rows; returns (max |phi - bf|, max |phiv - bf|, per row)."""
    players9 = ns.players[:-1]
    worst_f = worst_v = 0.0
    per = {}
    for i in rows:
        u = str(T["unit"].iloc[epos[i]])
        T_unit = T[T["unit"].astype(str) == u]
        b_rows = Kb.iloc[bg_lists[i]]
        x = np.r_[T.iloc[epos[i]][players9].to_numpy(np.float64), float(T["nfit__" + link].iloc[epos[i]])]
        BG = np.c_[b_rows[players9].to_numpy(np.float64), b_rows["nfit__" + link].to_numpy(np.float64)]
        w = np.full(len(b_rows), 1.0 / len(b_rows))
        f = adapter_f(BS, AD, np, pd, opt, params, T_unit, b_rows, players9, hist, extras, spy, off, 0, link)
        bf = TS.brute_force(f, x, BG, w, np.arange(len(ns.players)), len(ns.players))
        bfv = TS.brute_force(f, x, BG, w, np.asarray(ns.pvar), len(ns.variables))
        df, dv = float(np.abs(bf - ns.phi[i]).max()), float(np.abs(bfv - ns.phiv[i]).max())
        worst_f, worst_v = max(worst_f, df), max(worst_v, dv)
        per[int(i)] = [df, dv]
    return worst_f, worst_v, per


def step_synthetic(W, log, a):
    import bardl_shap as BS                       # the board's pins (8) before numpy loads
    import numpy as np
    import pandas as pd
    import shapv1_rows as RW
    import shapv1_treeshap as TS
    root = C.makedirs(os.path.join(W, "synthetic"))
    data, _ = BS.read_bytes(ADAPTER)
    AD = BS.load_adapter(ADAPTER, data)
    w = synth_world(BS, AD, np, pd, root)
    link, opt, params, rival = "identity", w.opt, w.params, w.rival
    slim = BS.Slim(w.slim_dir, w.manifest)
    cols = BS.uniq(list(AD.KEYS) + ["nfit__" + link] + slim.history + slim.extras)
    T = BS.read_test(slim, cols)
    # (i) a synthetic board: the adapter's own predict() is the saved pre; raw is numpy's clip to a narrow range
    ctx = BS.MiniCtx(w.run, {"test": BS.slim_set(T, slim.history, slim.extras, link, AD.KEYS)})
    pre0 = AD.predict(ctx, rival, 0, params, "test")["pre"].to_numpy(np.float64)
    legal = [0.30, 0.45]
    preds = T[list(AD.KEYS)].copy()
    preds["covered"] = True
    preds["pre"] = pre0
    preds["raw"] = np.clip(pre0, legal[0], legal[1])
    clipped = int((preds["raw"].to_numpy() != pre0).sum())
    ex, saved_T = BS.exactness(AD, rival, params, w.run, T, preds, legal, 0, slim.history, slim.extras, link)
    check("(i) exactness(): synthetic board reproduced bit for bit (pre; raw with %d clipped rows)" % clipped,
          ex["pass"] and ex["raw"]["pass"] and ex["rows_checked"] == len(T) and clipped > 0,
          {"rows": ex["rows_checked"], "pre": ex["bit_equal_rows"], "raw": ex["raw"]["bit_equal_rows"]})
    p1 = json.loads(json.dumps(params))
    c0 = p1["units"]["ua"]["coef"][0]
    p1["units"]["ua"]["coef"][0] = float(np.nextafter(c0, np.inf))
    pre1 = AD.predict(BS.MiniCtx(w.run, {"test": BS.slim_set(T, slim.history, slim.extras, link, AD.KEYS)}), rival, 0,
                      p1, "test")["pre"].to_numpy(np.float64)
    changed = int((pre1.view(np.int64) != pre0.view(np.int64)).sum())
    ex1, _ = BS.exactness(AD, rival, p1, w.run, T, preds, legal, 0, slim.history, slim.extras, link)
    check("(i) one-ulp coefficient: exactness fails exactly when a prediction changes",
          ex1["pass"] == (changed == 0), {"rows_changed": changed, "pass": ex1["pass"]})
    p2 = json.loads(json.dumps(params))
    p2["units"]["ua"]["coef"][0] = float(c0 * (1 + 1e-12))
    ex2, _ = BS.exactness(AD, rival, p2, w.run, T, preds, legal, 0, slim.history, slim.extras, link)
    gi = C.makedirs(os.path.join(root, "gates", "i_exact", "rival_bardl_h1"))
    st_i = BS.Stopper(gi, "rival_bardl_h1", "ndvi", 0, log)
    ok, info = expect_stop(lambda: BS.write_exactness(st_i, dict(ex2, stage="bits")), gi, "S-EXACT")
    xj = C.read_json(os.path.join(gi, "exactness.json")) if os.path.isfile(os.path.join(gi, "exactness.json")) else {}
    check("(i) a changed coefficient: S-EXACT stop, exactness.json (pass false) and FAILED.json",
          ok and xj.get("pass") is False and not ex2["pass"], dict(info, bit_equal=ex2["bit_equal_rows"]))
    # the pipeline of the owner's run (bardl_shap.shap_pipeline) on the synthetic sample
    st = BS.Stopper(C.makedirs(os.path.join(root, "main", "rival_bardl_h1")), "rival_bardl_h1", "ndvi", 0, log)
    ns = BS.shap_pipeline(AD, opt, params, w.run, rival, 0, w.spy, w.off, T, saved_T, w.S, w.B, slim, cols, link,
                          w.export_x, st, log)
    want_players = ["x__hist_last_1", "x__hist_last_2", "x__hist_last_3", "x__V02_total_precip_mm",
                    "x__V02_total_precip_mm_lag1", "x__V02_total_precip_mm_lag2", "x__V30_soil_moisture_pct",
                    "x__V30_soil_moisture_pct_lag1", "x__V30_soil_moisture_pct_lag2", "normal"]
    check("players by the adapter's rule (9 export columns + normal), variables by the name rule",
          ns.players == want_players and ns.variables == ["hist_last", "normal", "soil_moisture_pct",
                                                          "total_precip_mm"], [ns.players, ns.variables])
    n = len(w.S)
    rows = list(range(n))
    wf, wv, per = brute_rows(BS, AD, TS, np, pd, opt, params, T, ns.Kb, ns.epos, ns.bg_lists, rows, ns, w.hist,
                             w.extras, w.spy, w.off, link)
    check("(a) feature level == brute force over 2^10 coalitions (7 rows, 5-9 b each)", wf <= 1e-12, wf)
    check("(b) variable level == brute force of the grouped game (4 variables)", wv <= 1e-12, wv)
    add = np.abs(ns.base + ns.phi.sum(1) - ns.eta).max()
    addv = np.abs(ns.base + ns.phiv.sum(1) - ns.eta).max()
    check("(c) additivity at both levels <= 1e-12", add <= 1e-12 and addv <= 1e-12, [float(add), float(addv)])
    viol = int((ns.const & (ns.phi != 0)).sum() + (ns.constv & (ns.phiv != 0)).sum())
    check("(d) S-ZERO: phi exactly 0 wherever the mask holds (both levels)", viol == 0 and int(ns.const.sum()) > n,
          {"violations": viol, "masked_cells": int(ns.const.sum() + ns.constv.sum())})
    P = {p: j for j, p in enumerate(ns.players)}
    names = AD.feature_names(opt)
    d_lag0, d_mean = names.index("precip_anom_l0"), names.index("precip_anom_mean3")
    check("(d) all-finite row: every player nonzero, normal exactly 0",
          bool((ns.phi[0, :9] != 0).all() and ns.phi[0, P["normal"]] == 0), ns.phi[0].tolist())
    check("(d) missing-mean row: the lag-0 player, its single term and the precip mean term exactly 0",
          bool(ns.phi[3, P["x__V02_total_precip_mm"]] == 0 and ns.terms[3, d_lag0] == 0 and ns.terms[3, d_mean] == 0
               and ns.phi[3, P["x__V02_total_precip_mm_lag1"]] != 0),
          [float(ns.phi[3, P["x__V02_total_precip_mm"]]), float(ns.terms[3, d_lag0]), float(ns.terms[3, d_mean])])
    check("(d) equal-on-every-b players masked and exactly 0; fallback row all 0",
          bool(ns.const[5, P["x__V30_soil_moisture_pct_lag1"]] and ns.const[5, P["x__hist_last_1"]]
               and ns.phi[5, P["x__V30_soil_moisture_pct_lag1"]] == 0 and ns.phi[5, P["x__hist_last_1"]] == 0
               and (ns.phi[6] == 0).all() and (ns.phiv[6] == 0).all()), ns.phi[6].tolist())
    check("(e) per-lag linear split: off by > 1e-6 on one-sided-NaN rows, <= 1e-12 on the all-finite row",
          bool(ns.lin_gap[1] > 1e-6 and ns.lin_gap[2] > 1e-6 and ns.lin_gap[0] <= 1e-12), ns.lin_gap.tolist())
    br = ns.bgrec
    check("(f) design() on background rows alone zeroes NDVI lags; the mixed call adds only the missing ones",
          br["lag_values_set_to_0_if_designed_alone (the hazard, not used)"] > 0
          and br["lag_values_set_to_0_added_by_the_background_rows"]
          == br["hist_last_values_missing_on_the_background_rows"] == 1,
          {k: br[k] for k in ("lag_values_set_to_0_if_designed_alone (the hazard, not used)",
                              "lag_values_set_to_0_added_by_the_background_rows",
                              "hist_last_values_missing_on_the_background_rows")})
    ge = float(np.abs(ns.eta - ns.saved_e).max())
    gb = float(np.abs(ns.f_b - ns.eta_bg_model).max())
    check("(g) evaluator vs the adapter's predict(): explained and background rows <= 1e-12", ge <= 1e-12 and gb <= 1e-12,
          [ge, gb])
    # (h) background stops
    for case, dz, word in (("h_plus_1e-9", 1e-9, "refused"), ("h_plus_1e-13", 1e-13, "own normal"),
                           ("h_minus_1e-13", -1e-13, "own normal")):
        Kb2 = ns.Kb.copy()
        Kb2.loc[0, "nfit__" + link] = float(Kb2.loc[0, "nfit__" + link]) + dz
        o = C.makedirs(os.path.join(root, "gates", case, "rival_bardl_h1"))
        s2 = BS.Stopper(o, "rival_bardl_h1", "ndvi", 0, log)
        ok, info = expect_stop(lambda: BS.background_design(AD, opt, params, w.run, rival, 0, w.spy, w.off, T,
                                                            ns.X_test, ns.kidx, ns.epos, ns.tpart, Kb2, slim.history,
                                                            slim.extras, link, saved_T, s2), o, "S-BG")
        check("(h) background normal %+g: S-BG (%s)" % (dz, word), ok and word in info.get("detail", ""), info)
    B3 = w.B.copy()
    t0_ = int(B3.loc[0, "time"])
    B3.loc[0, "time"] = 24241 - 120 + (t0_ - 1) % 12            # the same month in 2010: a train row, not a refit row
    o = C.makedirs(os.path.join(root, "gates", "h_not_refit", "rival_bardl_h1"))
    ok, info = expect_stop(lambda: BS.read_background(slim, w.S, B3, cols, BS.Stopper(o, "rival_bardl_h1", "ndvi", 0,
                                                                                      log)), o, "S-BG")
    check("(h) a key that is not a refit row: S-BG", ok and "not refit rows" in info.get("detail", ""), info)
    dup_dir = C.makedirs(os.path.join(root, "slim_dup"))
    tr = slim.read(slim.files["train"]["g1"], cols + ["r_refit"])
    tr = pd.concat([tr, tr.iloc[[int(np.flatnonzero(tr["r_refit"].to_numpy())[0])]]], ignore_index=True)
    pd_ = C.write_parquet(os.path.join(dup_dir, "train", "g1.parquet"), tr)
    man_dup = {"files": [{"part": "train", "stem": "g1", "group": "g1", "path": "train/g1.parquet",
                          "sha256": C.sha256_file(pd_)}], "columns": w.manifest["columns"]}
    sl_dup = BS.Slim(dup_dir, man_dup)
    first = tr.iloc[int(np.flatnonzero(tr["r_refit"].to_numpy())[0])]
    S4 = w.S.iloc[[0]].copy()
    S4["unit"], S4["group"] = first["unit"], "g1"
    B4 = pd.DataFrame({"row": [0], "unit": [first["unit"]], "time": [int(first["time"])]})
    o = C.makedirs(os.path.join(root, "gates", "h_duplicate", "rival_bardl_h1"))
    ok, info = expect_stop(lambda: BS.read_background(sl_dup, S4, B4, cols, BS.Stopper(o, "rival_bardl_h1", "ndvi", 0,
                                                                                         log)), o, "S-BG")
    check("(h) a key found twice among the refit rows: S-BG", ok and "more than once" in info.get("detail", ""), info)
    # (h) the checks after the read (background_rows) and the design's S-SAMPLE check (prediction_design): the
    # functions the owner's run and the real step's pre-flight share
    S5 = w.S[w.S["group"] == "g1"].reset_index(drop=True)
    B5 = w.B[w.B["row"].isin(S5["row"])].reset_index(drop=True)
    tr5 = slim.read(slim.files["train"]["g1"], cols + ["r_refit"])
    k5 = ((tr5["unit"].astype(str) == str(B5.loc[0, "unit"])).to_numpy()
          & (tr5["time"].to_numpy(np.int64) == int(B5.loc[0, "time"])))
    for case, col, word in (("h_issue_month", "issue", "another calendar month"), ("h_lead", "lead", "another lead")):
        t5 = tr5.copy()
        t5.loc[k5, col] = t5.loc[k5, col].to_numpy(np.int64) + 1
        d5 = C.makedirs(os.path.join(root, "slim_" + case))
        p5 = C.write_parquet(os.path.join(d5, "train", "g1.parquet"), t5)
        sl5 = BS.Slim(d5, {"files": [{"part": "train", "stem": "g1", "group": "g1", "path": "train/g1.parquet",
                                      "sha256": C.sha256_file(p5)}], "columns": w.manifest["columns"]})
        o = C.makedirs(os.path.join(root, "gates", case, "rival_bardl_h1"))
        ok, info = expect_stop(lambda: BS.background_rows(AD, S5, B5, T, saved_T, sl5, cols, w.spy, 0,
                                                          BS.Stopper(o, "rival_bardl_h1", "ndvi", 0, log)), o, "S-BG")
        check("(h) a background row's %s moved by one step: S-BG (%s)" % (col, word),
              ok and int(k5.sum()) == 1 and word in info.get("detail", ""), info)
    p6 = json.loads(json.dumps(params))
    del p6["units"]["ua"]
    o = C.makedirs(os.path.join(root, "gates", "h_unit_without_params", "rival_bardl_h1"))
    ok, info = expect_stop(lambda: BS.prediction_design(AD, opt, p6, w.run, rival, 0, w.spy, w.off, T, saved_T, ns.epos,
                                                        ns.Kb, slim, link, BS.Stopper(o, "rival_bardl_h1", "ndvi", 0,
                                                                                      log)), o, "S-SAMPLE")
    check("(h) a sample row of a unit without BARDL parameters: S-SAMPLE",
          ok and "without BARDL parameters" in info.get("detail", ""), info)
    # (j) S-ENV
    have = C.versions()
    hb_ok = {"versions": {k: have[k] for k in ("lightgbm", "numpy", "pandas", "pyarrow", "scikit-learn",
                                               "scikit-learn-intelex", "threadpoolctl")}, "constants": {"threads": 8}}
    o = C.makedirs(os.path.join(root, "gates", "j_env_ok", "rival_bardl_h1"))
    try:
        BS.s_env(BS.Stopper(o, "rival_bardl_h1", "ndvi", 0, log), hb_ok, log)
        env_ok = not os.path.isfile(os.path.join(o, "FAILED.json"))
    except SystemExit:
        env_ok = False
    check("(j) S-ENV passes on the installed versions and 8 pins", env_ok, hb_ok["versions"])
    for case, hb in (("j_env_version", dict(hb_ok, versions=dict(hb_ok["versions"], numpy="0.0.0"))),
                     ("j_env_no_versions", {"constants": {"threads": 8}})):
        o = C.makedirs(os.path.join(root, "gates", case, "rival_bardl_h1"))
        ok, info = expect_stop(lambda: BS.s_env(BS.Stopper(o, "rival_bardl_h1", "ndvi", 0, log), hb, log), o, "S-ENV")
        check("(j) %s: S-ENV stop" % case, ok, info)
    # (k) the writer
    meta = {"model": "rival_bardl_h1", "problem": "ndvi", "lead": 0, "link": "identity", "c": None, "ub": 1.0,
            "guard": {"passed": True}, "sample_sha256": "synthetic", "variable_map": ns.vmap}
    ok_k = C.makedirs(os.path.join(root, "gates", "k_writer", "rival_bardl_h1"))
    ok, info = expect_stop(lambda: RW.write(ok_k, w.S, ns.players, ns.phi, ns.variables, ns.phiv, ns.base, ns.eta,
                                            ns.saved_e, ns.saved_e, None, meta, log, w.B, const=ns.const,
                                            constv=ns.constv, eta_bg=ns.f_b, eta_bg_model=ns.eta_bg_model + 1e-6),
                           ok_k, "S-EVAL")
    check("(k) background evaluator off by 1e-6: S-EVAL stop", ok, info)
    rec = RW.write(ok_k, w.S, ns.players, ns.phi, ns.variables, ns.phiv, ns.base, ns.eta, ns.saved_e, ns.saved_e, None,
                   meta, log, w.B, const=ns.const, constv=ns.constv, eta_bg=ns.f_b, eta_bg_model=ns.eta_bg_model)
    files = [f for f in ("rows.parquet", "background_keys.parquet", "meta.json") if os.path.isfile(os.path.join(ok_k, f))]
    check("(k) the correct call writes rows.parquet, background_keys.parquet, meta.json (FAILED.json removed)",
          len(files) == 3 and rec["pass"] and not os.path.isfile(os.path.join(ok_k, "FAILED.json")), files)
    # (l) done records
    dl = C.makedirs(os.path.join(root, "gates", "l_done", "rival_bardl_h1"))
    rows_p = os.path.join(dl, "rows.parquet")
    shutil.copyfile(os.path.join(ok_k, "rows.parquet"), C.assert_writable(rows_p))
    C.mark_done(rows_p, {"other": "inputs"})
    s_l = BS.Stopper(dl, "rival_bardl_h1", "ndvi", 0, log)
    skipped = C.piece_done(rows_p, {"this": "run"})
    removed = s_l.drop_done("a recompute starts")
    found = os.path.isfile(rows_p) and os.path.isfile(rows_p + ".done.json")     # compare_shap.py:86-89
    C.mark_done(rows_p, {"other": "inputs"})
    ok, info = expect_stop(lambda: s_l.stop("S-SAMPLE", "smoke"), dl, "S-SAMPLE")
    check("(l) recompute start and a stop remove the done record (compare skips the folder)",
          (not skipped) and removed and not found and ok and not os.path.isfile(rows_p + ".done.json"),
          {"skipped": skipped, "removed": removed, "discovered": found, "stop": info})
    # (m) a slim file whose bytes are not its manifest's
    man_bad = json.loads(json.dumps(w.manifest))
    man_bad["files"][0]["sha256"] = "0" * 64
    try:
        BS.read_test(BS.Slim(w.slim_dir, man_bad), cols)
        mm = False
    except BS.InputMismatch:
        mm = True
    check("(m) a slim file whose SHA-256 is not its manifest's is refused", mm, mm)
    # (n) outside B2: unequal normals
    delta = np.linspace(-0.01, 0.01, len(ns.Kb))
    z0b2 = ns.z0b + delta
    phi2, phiv2, base2, eta2, _, _, _, _ = BS.bardl_shap(ns.De, ns.Db, ns.z0e, z0b2, ns.Ue, ns.Ub, ns.px, ns.pb, ns.pw,
                                                         ns.single, ns.means, len(ns.players), ns.pvar,
                                                         len(ns.variables), ns.normal_p, ns.normal_v)
    ref = np.bincount(ns.px, weights=(ns.z0e[ns.px] - z0b2[ns.pb]) * ns.pw, minlength=n)
    a2 = float(max(np.abs(base2 + phi2.sum(1) - eta2).max(), np.abs(base2 + phiv2.sum(1) - eta2).max()))
    check("(n) unequal normals: the offset goes to normal exactly; additivity holds; other players unchanged",
          bool(np.array_equal(phi2[:, ns.normal_p], ref) and a2 <= 1e-12 and np.array_equal(phi2[:, :9], ns.phi[:, :9])),
          a2)
    REPORT["_synthetic_rows"] = {str(i): c[0] for i, c in enumerate(w.cases)}
    REPORT["_brute_force_per_row"] = per
    # (o) end to end: bardl_shap.main() itself on synthetic board trees (no real data)
    import pyarrow.parquet as pq
    logdir = os.path.join(W, "logs")
    sroot = os.path.join(root, "e2e", "sample")
    reg, ssha, _ = write_sample(sroot, w.S, w.B, "bardl_synthetic", len(w.S))
    good = synth_board(BS, root, "board", w, preds, legal)
    argv = ["--problem", "ndvi", "--lead", "0", "--n", str(len(w.S)), "--sample-root", sroot, "--register", reg,
            "--log-dir", logdir]
    out = os.path.join(root, "e2e", "out")
    md = os.path.join(out, "rival_bardl_h1")
    rc = run_main(BS, argv + ["--out-root", out], good)
    ok = rc == 0 and os.path.isfile(os.path.join(md, "rows.parquet.done.json"))
    meta, same = {}, False
    if ok:
        R = pq.read_table(os.path.join(md, "rows.parquet")).to_pandas()
        meta = C.read_json(os.path.join(md, "meta.json"))
        same = bool(np.array_equal(R[["phi__" + p for p in ns.players]].to_numpy(np.float64), ns.phi)
                    and np.array_equal(R[["phiv__" + v for v in ns.variables]].to_numpy(np.float64), ns.phiv))
    check("(o) main() end to end on a synthetic board: exit 0, the pipeline's own values, every check",
          ok and same and all((meta.get("checks_passed") or {}).values()) and (meta.get("exactness") or {}).get(
              "inputs_pass") is True and meta.get("link_key") == "identity|c=-|ub=1" == meta.get("link_key_common_board"),
          {"exit": rc, "same_values": same, "checks": meta.get("checks_passed"), "link_key": meta.get("link_key")})
    rows_sha = C.sha256_file(os.path.join(md, "rows.parquet")) if ok else None
    cmp_dir = os.path.join(out, "compare")

    def since_last_run():
        with open(os.path.join(logdir, "bardl_shap_ndvi_lead0.log"), encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        return lines[max(i for i, ln in enumerate(lines) if "BARDL SHAP ndvi lead 0" in ln):]
    C.write_json(os.path.join(cmp_dir, "per_lead.json"), {"models": ["rival_other", "treeroute"], "draws": 7,
                                                          "sample_sha256": ssha})
    rc2 = run_main(BS, argv + ["--out-root", out], good)
    lines2 = since_last_run()
    check("(o) main() again: skipped, rows.parquet unchanged; beside a comparison that does not list BARDL: REMINDER",
          rc2 == 0 and ok and rows_sha == C.sha256_file(os.path.join(md, "rows.parquet"))
          and any("skipped" in ln for ln in lines2)
          and any("REMINDER" in ln and "does not list rival_bardl_h1" in ln for ln in lines2), [rc2] + lines2[-2:])
    per_cur = {"models": ["rival_bardl_h1"], "draws": 7, "sample_sha256": ssha}
    C.write_json(os.path.join(cmp_dir, "per_lead.json"), per_cur)
    h_cur = C.inputs_hash({"models": per_cur["models"], "draws": 7, "sample": ssha,      # compare_shap.py:336-339
                           "rows": {"rival_bardl_h1": C.sha256_file(os.path.join(md, "rows.parquet")) if ok else ""}})
    rem = {}
    for what, h in (("made from its rows", h_cur), ("made from other rows", "0" * 64)):
        C.write_json(os.path.join(cmp_dir, "pairs.parquet.done.json"), {"inputs": h})
        rcr = run_main(BS, argv + ["--out-root", out], good)
        lr = since_last_run()
        rem[what] = [rcr, any("skipped" in ln for ln in lr), any("REMINDER" in ln for ln in lr)]
    check("(o) a skip beside a comparison made from its rows: no REMINDER; made from other rows: REMINDER",
          rem["made from its rows"] == [0, True, False] and rem["made from other rows"] == [0, True, True], rem)
    out_x = os.path.join(root, "e2e", "out_exactness_only")
    rc3 = run_main(BS, ["--problem", "ndvi", "--lead", "0", "--exactness-only", "--out-root", out_x, "--log-dir",
                        logdir], good)
    got = sorted(os.listdir(os.path.join(out_x, "rival_bardl_h1"))) if os.path.isdir(out_x) else []
    check("(o) --exactness-only: exit 0, exactness.json and nothing else", rc3 == 0 and got == ["exactness.json"], got)
    reg_empty = C.write_text(os.path.join(root, "e2e", "register_empty", "SAMPLE_REGISTER.txt"), "")
    out_u = os.path.join(root, "e2e", "out_unregistered")
    if ok:                                               # a finished piece of an earlier run sits in the folder
        dst = C.makedirs(os.path.join(out_u, "rival_bardl_h1"))
        for f in ("rows.parquet", "rows.parquet.done.json", "background_keys.parquet", "meta.json"):
            shutil.copyfile(os.path.join(md, f), C.assert_writable(os.path.join(dst, f)))
    rc_u = run_main(BS, ["--problem", "ndvi", "--lead", "0", "--n", str(len(w.S)), "--sample-root", sroot, "--register",
                         reg_empty, "--log-dir", logdir, "--out-root", out_u], good)
    fu_p = os.path.join(out_u, "rival_bardl_h1", "FAILED.json")
    fu = C.read_json(fu_p) if os.path.isfile(fu_p) else {}
    du = str(fu.get("detail"))
    check("(o) an unregistered sample: exit 3, FAILED.json S-SAMPLE (detail without a repeated prefix), no done record",
          rc_u == 3 and ok and fu.get("gate") == "S-SAMPLE" and "is not in the sample register" in du
          and "STOP" not in du and not os.path.isfile(os.path.join(out_u, "rival_bardl_h1", "rows.parquet.done.json")),
          {"exit": rc_u, "gate": fu.get("gate"), "detail": du[-60:]})

    def ch(target, fn):
        return lambda what, rec: fn(rec) if what == target else rec

    def bad_yaml(case):                              # the registry's bytes no longer parse; the board's record is kept
        C.write_text(os.path.join(root, "e2e", case, "human", "registry", "ndvi.yaml"),
                     "rivals: [ {id: bardl_h1, runner: adapters.ndvi_bardl\n")
    for case, change, gate, stale, word, post in (
            ("bad_preds_record", ch("done", lambda r: dict(r, preds_sha256="0" * 64)), "S-EXACT", False,
             "preds_bardl_h1.parquet", None),
            ("bad_registry_record", ch("human_board", lambda r: dict(r, registry=dict(r["registry"],
                                                                                     registry="0" * 64))),
             "S-EXACT", False, "registry", None),
            ("unparseable_registry", None, "S-EXACT", True, "registry", bad_yaml),
            ("bad_provenance", ch("export_manifest", lambda r: dict(r, files=[
                dict(f, sha256="other") if f["part"] == "train" else f for f in r["files"]])), "S-EXACT", False,
             "provenance", None),
            ("bad_versions", ch("human_board", lambda r: dict(r, versions=dict(r["versions"], numpy="0.0.0"))),
             "S-ENV", True, "versions", None)):
        board_v = synth_board(BS, root, case, w, preds, legal, change)
        if post is not None:
            post(case)
        out_v = os.path.join(root, "e2e", "out_" + case)
        if stale and ok:                                 # a finished piece of an earlier run sits in the folder
            dst = C.makedirs(os.path.join(out_v, "rival_bardl_h1"))
            for f in ("rows.parquet", "rows.parquet.done.json", "background_keys.parquet", "meta.json"):
                shutil.copyfile(os.path.join(md, f), C.assert_writable(os.path.join(dst, f)))
        rc4 = run_main(BS, argv + ["--out-root", out_v], board_v)
        fj = os.path.join(out_v, "rival_bardl_h1", "FAILED.json")
        fr = C.read_json(fj) if os.path.isfile(fj) else {}
        xj = os.path.join(out_v, "rival_bardl_h1", "exactness.json")
        xr = C.read_json(xj) if os.path.isfile(xj) else {}
        named = word in json.dumps(xr.get("inputs_failed") or fr.get("detail") or "")
        nodone = not os.path.isfile(os.path.join(out_v, "rival_bardl_h1", "rows.parquet.done.json"))
        check("(o) main() on a board with %s: exit 3, FAILED.json %s%s, no done record left" % (
            case.replace("_", " "), gate, " (with exactness.json)" if gate == "S-EXACT" else ""),
            rc4 == 3 and fr.get("gate") == gate and named and nodone and (gate != "S-EXACT" or xr.get("pass") is False),
            {"exit": rc4, "gate": fr.get("gate"), "named": named, "no_done": nodone,
             "inputs_failed": xr.get("inputs_failed")})


# ---------------------------------------------------------------------------------------------------------------
def step_exact(W, log, a):
    need_guard("the exactness run", log)
    out = os.path.join(W, "exact")
    rc = run_child(bardl_cmd(W, "--exactness-only", "--out-root", out), log, "bardl_shap.py --exactness-only")
    md = os.path.join(out, "rival_bardl_h1")
    check("exact: exit 0", rc == 0, rc)
    f = os.path.join(md, "exactness.json")
    if not os.path.isfile(f):
        check("exact: exactness.json written", False, f)
        return
    e = C.read_json(f)
    done = C.read_json(os.path.join(C.PROBLEMS["ndvi"]["human"], "lead_0", "done_bardl_h1.json"))
    nrows = int(done.get("test_rows") or 0)
    check("exact: pre bit-equal on every test row (%d)" % nrows,
          e.get("pass") and e.get("rows") == nrows == e.get("bit_equal_rows") and e.get("max_abs_diff") == 0.0
          and e.get("same_nan") and e.get("inf_equal") and e.get("keys_only_saved") == 0
          and e.get("keys_only_rebuilt") == 0, {k: e.get(k) for k in ("rows", "bit_equal_rows", "max_abs_diff")})
    r = e.get("raw") or {}
    check("exact: raw (the legal clip) bit-equal on every test row", r.get("pass") and r.get("bit_equal_rows") == nrows,
          {k: r.get(k) for k in ("rows", "bit_equal_rows", "max_abs_diff")})
    bad = sorted(k for k, v in (e.get("inputs") or {}).items() if not v.get("equal"))
    prov = [v for k, v in (e.get("inputs") or {}).items() if k.startswith("provenance")]
    check("exact: every board record check equal (provenance included)", e.get("inputs_pass") and not bad and prov
          and prov[0].get("files_equal") == 266 and prov[0].get("files_different") == 0, {"failed": bad, "provenance":
                                                                                           prov})
    msg = None
    logf = os.path.join(C.PROBLEMS["ndvi"]["human"], "human_rivals.log")
    with open(logf, encoding="utf-8") as fh:
        for ln in fh:
            if "| refit | adapter | bardl_h1 | lead 0 |" in ln:
                msg = ln.rstrip("\n").split(" | ")[-1]
    check("exact: the adapter's message equals the board's own log line", msg is not None and e.get("adapter_message")
          == msg, e.get("adapter_message"))
    bc = e.get("board_code_reproduced") or {}            # information only, never a pass condition (never a gate)
    REPORT["_board_code_reproduced (informational)"] = {k: bc.get(k) for k in ("files", "equal")}
    nt = e.get("normal_table") or {}
    check("exact: every test row's normal equals its unit x month table",
          nt.get("rows_whose_normal_equals_the_table") == nt.get("test_rows") == nrows, nt)
    check("exact: no FAILED.json, no rows.parquet (exactness only)", not os.path.isfile(os.path.join(md, "FAILED.json"))
          and not os.path.isfile(os.path.join(md, "rows.parquet")), sorted(os.listdir(md)))


# ---------------------------------------------------------------------------------------------------------------
def write_sample(sroot, S, B, tag, n, register=True, extra=None):
    """A sample root: sample.parquet, background_lead_0.parquet, sample_manifest.json and its own register."""
    C.makedirs(sroot)
    C.write_parquet(os.path.join(sroot, "sample.parquet"), S[["row", "unit", "group", "time", "year"]])
    C.write_parquet(os.path.join(sroot, "background_lead_0.parquet"), B[["row", "unit", "time"]])
    ssha = C.sha256_file(os.path.join(sroot, "sample.parquet"))
    bsha = C.sha256_file(os.path.join(sroot, "background_lead_0.parquet"))
    man = {"n": int(n), "n_asked": int(n), "tag": tag, "problem": "ndvi", "leads": [0],
           "sha256": {"sample.parquet": ssha, "background_lead_0.parquet": bsha}}
    man.update(extra or {})
    C.write_json(os.path.join(sroot, "sample_manifest.json"), man)
    reg = os.path.join(sroot, "SAMPLE_REGISTER.txt")
    with open(C.assert_writable(reg), "w", encoding="utf-8") as fh:
        if register:
            fh.write("%s problem=ndvi tag=%s leads=0 n=%d defo_regions=0 sample=%s background_lead_0.parquet=%s\n"
                     % (datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), tag, int(n), ssha, bsha))
    return reg, ssha, bsha


def step_real(W, log, a):
    need_guard("the real smoke", log)
    import bardl_shap as BS                       # the board's pins (8) before numpy loads
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq
    import shapv1_treeshap as TS
    tag = "bardl_%s" % a.label
    src_reg = os.path.join(SOURCE_SAMPLE, "SAMPLE_REGISTER.txt")
    sid = C.sample_identity("ndvi", SOURCE_SAMPLE, src_reg, lead=0)
    check("real: the source smoke sample is registered in its own register", bool(sid.get("background_sha256")),
          sid["sample_sha256"][:16])
    S0 = pq.read_table(os.path.join(SOURCE_SAMPLE, "sample.parquet")).to_pandas()
    B0 = pq.read_table(os.path.join(SOURCE_SAMPLE, "background_lead_0.parquet")).to_pandas()
    bd = BS.board("ndvi", 0, None, log)
    params = bd.map["params"]
    CM = params["climate_means"]
    spy, off = int(params["steps_per_year"]), int(params["start_offset_steps"])
    sk = lambda t: (int(t) - 1) % spy + 1  # noqa: E731
    miss = [int(r) for r, u, t in zip(S0["row"], S0["unit"].astype(str), S0["time"])
            if any(("%s|%d" % (u, sk(int(t) - l))) not in CM[v] for v in CM for l in (0, 1, 2))]
    groups3 = sorted(S0["group"].astype(str).unique())[:3]
    pick = sorted(set(miss) | set(S0.loc[S0["group"].astype(str).isin(groups3), "row"].astype(int).tolist()))
    check("real: sample rows with a missing unit x month climate mean (from the map)", len(miss) > 0, miss)
    S = S0[S0["row"].isin(pick)].sort_values("row").reset_index(drop=True)
    newrow = {int(r): i for i, r in enumerate(S["row"])}
    S["row"] = np.arange(len(S), dtype=np.int64)
    B = B0[B0["row"].isin(pick)].copy()
    B["row"] = B["row"].map(newrow).astype(np.int64)
    B = B.sort_values("row", kind="stable").reset_index(drop=True)
    K = len(S)
    sroot = os.path.join(W, "sample")
    reg, ssha, _ = write_sample(sroot, S, B, tag, K, extra={
        "rule": "a subset of smoke/sample_ndvi_v3: the rows of its first 3 groups and every row with a missing unit x "
                "month climate mean, renumbered 0..K-1 (plumbing only)", "source_sample_sha256": sid["sample_sha256"],
        "source_rows": pick, "groups": sorted(S["group"].astype(str).unique())})
    log("smoke sample: %d rows (%d with a missing climate mean) in %d groups, %d background keys"
        % (K, len(miss), S["group"].nunique(), len(B)))
    logs0 = logs_state()
    out = os.path.join(W, "out")
    md = os.path.join(out, "rival_bardl_h1")
    main_cmd = bardl_cmd(W, "--n", str(K), "--sample-root", sroot, "--register", reg, "--out-root", out)
    need_guard("the main run", log)
    rc = run_child(main_cmd, log, "bardl_shap.py on the smoke sample")
    check("real: main run exit 0", rc == 0, rc)
    if rc != 0:
        return
    rows_sha = C.sha256_file(os.path.join(md, "rows.parquet"))
    done1 = C.read_json(os.path.join(md, "rows.parquet.done.json"))
    rc = run_child(main_cmd, log, "bardl_shap.py again (resume)")
    with open(os.path.join(W, "logs", "bardl_shap_ndvi_lead0.log"), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    last = max(i for i, ln in enumerate(lines) if "BARDL SHAP ndvi lead 0" in ln)
    skipped = any("skipped" in ln for ln in lines[last:])
    check("real: resume exit 0, skipped, rows.parquet and its done record unchanged",
          rc == 0 and skipped and C.sha256_file(os.path.join(md, "rows.parquet")) == rows_sha
          and C.read_json(os.path.join(md, "rows.parquet.done.json")) == done1, [rc, skipped])
    out10 = os.path.join(W, "out_rows10")
    rc = run_child(bardl_cmd(W, "--n", str(K), "--sample-root", sroot, "--register", reg, "--out-root", out10,
                             "--rows", "10"), log, "bardl_shap.py --rows 10")
    ok10 = False
    if rc == 0:
        r10 = pq.read_table(os.path.join(out10, "rival_bardl_h1", "rows.parquet")).to_pandas()
        k10 = pq.read_table(os.path.join(out10, "rival_bardl_h1", "background_keys.parquet")).to_pandas()
        want = B[B["row"] < 10][["row", "unit", "time"]].astype(str).sort_values(["row", "unit", "time"])
        ok10 = (len(r10) == 10 and r10["row"].tolist() == list(range(10))
                and k10.astype(str).sort_values(["row", "unit", "time"]).reset_index(drop=True).equals(
                    want.reset_index(drop=True)))
    check("real: --rows 10 explains 10 rows with only their keys", rc == 0 and ok10, rc)
    # refusals (each a copy under refusals/<case>/ with its own register) and a stale piece
    u_other = [u for u in S["unit"].astype(str).unique() if u != str(S.loc[0, "unit"])][0]

    def other_unit(Sc, Bc):
        Bc.loc[Bc.index[Bc["row"] == 0][0], "unit"] = u_other

    def test_time(Sc, Bc):
        Bc.loc[Bc.index[Bc["row"] == 0][0], "time"] = int(Sc.loc[0, "time"])
    for case, mod, register, nn, gate, stale in (("unregistered", None, False, K, "S-SAMPLE", False),
                                                 ("n_plus_1", None, True, K + 1, "S-SAMPLE", False),
                                                 ("other_unit", other_unit, True, K, "S-BG", False),
                                                 ("test_time_key", test_time, True, K, "S-BG", False),
                                                 ("stale_piece", None, True, K + 1, "S-SAMPLE", True)):
        cdir = os.path.join(W, "refusals", case)
        Sc, Bc = S.copy(), B.copy()
        if mod is not None:
            mod(Sc, Bc)
        creg, _, _ = write_sample(os.path.join(cdir, "sample"), Sc, Bc, tag + "_" + case, K, register=register)
        cout = os.path.join(cdir, "out")
        if stale:                                  # a finished piece from an earlier run sits in the folder
            dst = C.makedirs(os.path.join(cout, "rival_bardl_h1"))
            for f in ("rows.parquet", "rows.parquet.done.json", "background_keys.parquet", "meta.json"):
                shutil.copyfile(os.path.join(md, f), C.assert_writable(os.path.join(dst, f)))
        rc = run_child(bardl_cmd(W, "--n", str(nn), "--sample-root", os.path.join(cdir, "sample"), "--register", creg,
                                 "--out-root", cout), log, "refusal %s" % case)
        fj = os.path.join(cout, "rival_bardl_h1", "FAILED.json")
        got = C.read_json(fj).get("gate") if os.path.isfile(fj) else None
        nodone = not os.path.isfile(os.path.join(cout, "rival_bardl_h1", "rows.parquet.done.json"))
        check("real refusal %s: exit 3, FAILED.json gate %s, no done record left" % (case, gate),
              rc == 3 and got == gate and nodone, [rc, got, nodone])
    # the main run's outputs
    meta = C.read_json(os.path.join(md, "meta.json"))
    ex = meta.get("exactness") or {}
    check("real: exactness pre and raw bit-equal on every test row", ex.get("pass") and ex.get("bit_equal_rows")
          == ex.get("rows") and (ex.get("raw") or {}).get("bit_equal_rows") == ex.get("rows"),
          [ex.get("rows"), ex.get("bit_equal_rows"), (ex.get("raw") or {}).get("bit_equal_rows")])
    check("real: meta checks_passed all true", all((meta.get("checks_passed") or {}).values()),
          meta.get("checks_passed"))
    check("real: additivity <= 1e-12 at both levels", max(meta["max_abs_additivity_error"],
                                                          meta["max_abs_additivity_error_variable"]) <= 1e-12,
          [meta["max_abs_additivity_error"], meta["max_abs_additivity_error_variable"]])
    check("real: evaluator vs saved pre and vs predict() on background rows <= 1e-12",
          meta["max_abs_evaluator_minus_model"] <= 1e-12 and meta["max_abs_background_evaluator_minus_model"] <= 1e-12,
          [meta["max_abs_evaluator_minus_model"], meta["max_abs_background_evaluator_minus_model"]])
    check("real: S-ZERO violations 0; 10 players (<= 9 nonzero), 4 variables (<= 3 nonzero)",
          meta["structural_zero_violations"] == 0 and len(meta["players"]) == 10 and len(meta["variables"]) == 4
          and meta["players_nonzero"] <= 9 and meta["variables_nonzero"] <= 3,
          [meta["players_nonzero"], meta["variables_nonzero"]])
    R = pq.read_table(os.path.join(md, "rows.parquet")).to_pandas()
    check("real: phi__normal and phiv__normal exactly 0 on every row", bool((R["phi__normal"] == 0).all()
                                                                         and (R["phiv__normal"] == 0).all()),
          int((R["phi__normal"] != 0).sum()))
    check("real: link key identity|c=-|ub=1, equal to the common board's; guard passed",
          meta.get("link_key") == "identity|c=-|ub=1" == meta.get("link_key_common_board")
          and (meta.get("guard") or {}).get("passed") is True, [meta.get("link_key"), meta.get("guard")])
    bk = pq.read_table(os.path.join(md, "background_keys.parquet")).to_pandas().astype(str)
    reg_keys = B[["row", "unit", "time"]].astype(str)
    check("real: background_keys.parquet = the registered keys",
          bk.sort_values(["row", "unit", "time"]).reset_index(drop=True).equals(
              reg_keys.sort_values(["row", "unit", "time"]).reset_index(drop=True)), [len(bk), len(reg_keys)])
    bg = meta.get("background_design") or {}
    check("real: background normals bit-equal; lag zeros = missing hist_last",
          bg.get("background_rows_normal_bit_equal") == bg.get("background_rows")
          and bg.get("explained_rows_normal_bit_equal") == bg.get("explained_rows")
          and bg.get("lag_values_set_to_0_added_by_the_background_rows")
          == bg.get("hist_last_values_missing_on_the_background_rows"),
          {k: bg.get(k) for k in ("background_rows", "background_rows_normal_bit_equal", "explained_rows",
                                  "explained_rows_normal_bit_equal",
                                  "lag_values_set_to_0_added_by_the_background_rows",
                                  "hist_last_values_missing_on_the_background_rows",
                                  "lag_values_set_to_0_if_designed_alone (the hazard, not used)")})
    # brute force on up to 10 real rows (every missing-mean row first)
    need_guard("the brute force", log)
    rival = BS.registry_rival(bd, log)
    ad_path, ad_bytes, _ = BS.adapter_file(bd, rival, log)
    AD = BS.load_adapter(ad_path, ad_bytes)
    opt = AD._options(rival)
    slim = BS.Slim(bd.slim_dir, bd.slim_manifest)
    link = AD.LINK
    cols = BS.uniq(list(AD.KEYS) + ["nfit__" + link] + slim.history + slim.extras)
    mrows = [newrow[r] for r in miss]
    chosen = (mrows + [i for i in range(K) if i not in mrows])[:10]
    groups = sorted(set(S.loc[chosen, "group"].astype(str)))
    tg = {str(e["group"]): e for e in slim.entries("test")}
    trg = {str(e["group"]): e for e in slim.entries("train")}
    Tg = pd.concat([slim.read(tg[g], cols) for g in groups], ignore_index=True)
    Kg = pd.concat([slim.read(trg[g], cols + ["r_refit"]) for g in groups], ignore_index=True)
    Kg = Kg[Kg["r_refit"].to_numpy(bool)][cols].reset_index(drop=True)
    ns = BS.SimpleNamespace(players=meta["players"], variables=meta["variables"],
                            pvar=[meta["variables"].index(meta["variable_map"][p]) for p in meta["players"]])
    tpos = {(str(u), int(t)): i for i, (u, t) in enumerate(zip(Tg["unit"].astype(str), Tg["time"]))}
    kpos = {(str(u), int(t)): i for i, (u, t) in enumerate(zip(Kg["unit"].astype(str), Kg["time"]))}
    epos = np.array([tpos[(str(S.loc[i, "unit"]), int(S.loc[i, "time"]))] for i in chosen])
    bgl = {}
    for r, u, t in zip(B["row"], B["unit"].astype(str), B["time"]):
        if int(r) in chosen:
            bgl.setdefault(int(r), []).append(kpos[(u, int(t))])
    Rr = R.set_index("row")
    ns.phi = np.vstack([Rr.loc[i, ["phi__" + p for p in ns.players]].to_numpy(np.float64) for i in chosen])
    ns.phiv = np.vstack([Rr.loc[i, ["phiv__" + v for v in ns.variables]].to_numpy(np.float64) for i in chosen])
    t0 = time.time()
    wf, wv, per = brute_rows(BS, AD, TS, np, pd, opt, params, Tg, Kg, list(epos), [bgl[i] for i in chosen],
                             list(range(len(chosen))), ns, slim.history, slim.extras, spy, off, link)
    check("real: brute force (2^10 coalitions, and the grouped game) on %d rows (%d with a missing climate mean)"
          % (len(chosen), len(mrows)), wf <= 1e-12 and wv <= 1e-12,
          {"feature": wf, "variable": wv, "seconds": round(time.time() - t0, 1)})
    REPORT["_brute_force_rows"] = {str(chosen[k]): v for k, v in per.items()}
    # pre-flight on EVERY key of the full smoke sample (expected to be the sample the owner registers): the owner's
    # run's own S-SAMPLE and S-BG functions (background_rows, prediction_design), with no SHAP value computed
    need_guard("the S-SAMPLE and S-BG pre-flight on the full smoke sample", log)
    t0 = time.time()
    T_all = BS.read_test(slim, cols)
    pv = pd.DataFrame(pq.read_table(BS.pa.BufferReader(bd.preds_bytes)).to_pandas())
    jj = T_all[["unit", "time", "issue"]].assign(unit=T_all["unit"].astype(str)).merge(
        pv[["unit", "time", "issue", "pre"]].assign(unit=pv["unit"].astype(str)), on=["unit", "time", "issue"],
        how="left", validate="one_to_one")
    saved_all = jj["pre"].to_numpy(np.float64)
    pdir = C.makedirs(os.path.join(W, "refusals", "preflight_full_sample", "rival_bardl_h1"))
    stp = BS.Stopper(pdir, "rival_bardl_h1", "ndvi", 0, log)
    run_ns = BS.SimpleNamespace(derived={"R17": bd.derived["R17"]})
    try:
        ep, _, Kb_all, _ = BS.background_rows(AD, S0, B0, T_all, saved_all, slim, cols, spy, 0, stp)
        pre_rec = BS.prediction_design(AD, opt, params, run_ns, rival, 0, spy, off, T_all, saved_all, ep, Kb_all, slim,
                                       link, stp, log)[-1]
        stopped = None
    except SystemExit as exc:
        pre_rec = {}
        fj = os.path.join(pdir, "FAILED.json")
        stopped = C.read_json(fj) if os.path.isfile(fj) else {"exit": exc.code}
    check("real: the owner's S-SAMPLE and S-BG checks pass on all %d keys of the full smoke sample (no SHAP value)"
          % len(B0),
          stopped is None and pre_rec.get("background_rows_normal_bit_equal") == pre_rec.get("background_rows")
          and pre_rec.get("explained_rows_normal_bit_equal") == pre_rec.get("explained_rows") == len(S0),
          {"stop": stopped, "seconds": round(time.time() - t0, 1), "record": {k: pre_rec.get(k) for k in (
              "background_rows", "background_rows_normal_bit_equal", "explained_rows",
              "explained_rows_normal_bit_equal", "test_part_design_unchanged", "normal_table_unchanged",
              "lag_values_set_to_0_added_by_the_background_rows", "hist_last_values_missing_on_the_background_rows",
              "max_abs_test_part_predict_minus_saved_pre (informational)")}})
    # the slim copy against the common export (every row of the smoke's groups): the values of the 9 players and the
    # normal bit for bit; the keys issue and lead, and on the train part the refit flag; every background key of the
    # smoke sample a refit row of the export (BARDL's background rows are the rows the common rivals read)
    need_guard("the export comparison", log)
    vals = meta["players"][:-1] + ["nfit__" + link]
    ef_test, ef_train = C.export_files("ndvi", 0, "test"), C.export_files("ndvi", 0, "train")
    nrow, nbad, kbad, nmiss, missing_cols = 0, 0, 0, 0, []
    refit_keys = set()
    for g in sorted(S["group"].astype(str).unique()):
        for part, ef, ent in (("test", ef_test, tg), ("train", ef_train, trg)):
            kc = ["issue", "lead"] + (["r_refit"] if part == "train" else [])
            sl = slim.read(ent[g], ["unit", "time"] + kc + vals)
            sl["unit"] = sl["unit"].astype(str)
            have = set(pq.read_schema(ef[g]).names)
            if not set(kc + vals) <= have:
                missing_cols += sorted(set(kc + vals) - have)
                continue
            exf = pq.read_table(ef[g], columns=["unit", "time"] + kc + vals).to_pandas()
            exf["unit"] = exf["unit"].astype(str)
            j = sl.merge(exf, on=["unit", "time"], how="outer", suffixes=("", "_x"), validate="one_to_one",
                         indicator=True)
            nmiss += int((j["_merge"] != "both").sum())
            j = j[j["_merge"] == "both"]
            nrow += len(j)
            for c in vals:
                if not BS.same_bits(j[c].to_numpy(np.float64), j[c + "_x"].to_numpy(np.float64)):
                    nbad += 1
            for c in kc:
                if not np.array_equal(j[c].to_numpy(), j[c + "_x"].to_numpy()):
                    kbad += 1
            if part == "train":
                fl = exf["r_refit"].to_numpy(bool)
                refit_keys |= set(zip(exf.loc[fl, "unit"], exf.loc[fl, "time"].to_numpy(np.int64).tolist()))
    check("real: slim values of the 9 players and the normal = the export's, bit for bit (every row of the groups)",
          nbad == 0 and nrow > 0 and nmiss == 0 and not missing_cols,
          {"rows": nrow, "columns_differing": nbad, "rows_in_one_side_only": nmiss, "columns_missing": missing_cols})
    bkeys = set(zip(B["unit"].astype(str), B["time"].to_numpy(np.int64).tolist()))
    check("real: issue and lead (and the train part's r_refit) = the export's; every background key a refit row of the "
          "export", kbad == 0 and nrow > 0 and len(bkeys) > 0 and bkeys <= refit_keys,
          {"key_columns_differing": kbad, "background_keys": len(bkeys),
           "background_keys_not_refit_rows_of_the_export": len(bkeys - refit_keys)})
    check("real: no analysis log written or changed", logs_state() == logs0, sorted(logs_state()))


# ---------------------------------------------------------------------------------------------------------------
def smoke_log_class(W):
    Base = C.Log

    class SmokeLog(Base):
        def __init__(self, name, folder=None):
            Base.__init__(self, name, os.path.join(W, "logs"))
    return SmokeLog


def child_ridge(W, a):
    """A ridge rival on the smoke's sample by rival_shap.py itself (the board's pins), logging under the smoke."""
    C.Log = smoke_log_class(W)
    sroot = os.path.join(W, "sample")
    sys.argv = ["rival_shap.py", "--problem", "ndvi", "--lead", "0", "--learners", "ridge", "--sample-root", sroot,
                "--register", os.path.join(sroot, "SAMPLE_REGISTER.txt"), "--out-root", os.path.join(W, "out")]
    import rival_shap
    rival_shap.main()


def child_compare(W, a):
    """compare_shap.py itself (1 thread), logging under the smoke."""
    C.Log = smoke_log_class(W)
    sroot = os.path.join(W, "sample")
    sys.argv = ["compare_shap.py", "--problem", "ndvi", "--lead", "0", "--models-root", os.path.join(W, "out"),
                "--sample-root", sroot, "--register", os.path.join(sroot, "SAMPLE_REGISTER.txt"), "--draws", "200",
                "--out", os.path.join(W, "out", "compare")]
    import compare_shap
    compare_shap.main()


def step_compare(W, log, a):
    need_guard("the comparison", log)
    out = os.path.join(W, "out")
    md = os.path.join(out, "rival_bardl_h1")
    if not os.path.isfile(os.path.join(md, "rows.parquet.done.json")):
        check("compare: the real step's finished BARDL piece exists", False, md)
        return
    dst = C.makedirs(os.path.join(out, "rival_bardl_h1_declined"))
    for f in ("rows.parquet", "rows.parquet.done.json", "background_keys.parquet"):
        shutil.copyfile(os.path.join(md, f), C.assert_writable(os.path.join(dst, f)))
    meta = C.read_json(os.path.join(md, "meta.json"))
    meta["guard"] = dict(meta.get("guard") or {}, passed=False)
    meta["model"] = "rival_bardl_h1_declined"
    C.write_json(os.path.join(dst, "meta.json"), meta)
    logs0 = logs_state()
    ridge = False
    if not a.no_ridge:
        need_guard("the ridge rival", log)
        rc = run_child(py_cmd() + [THIS, "--step", "ridge-child", "--label", a.label], log,
                       "rival_shap.py --learners ridge on the smoke sample (child)")
        ridge = rc == 0 and os.path.isfile(os.path.join(out, "rival_ridge", "rows.parquet.done.json"))
        check("compare: smoke ridge rival made by rival_shap.py (exit 0, finished piece)", ridge, rc)
    need_guard("compare_shap.py", log)
    rc = run_child(py_cmd() + [THIS, "--step", "compare-child", "--label", a.label], log, "compare_shap.py (child)")
    check("compare: compare_shap.py exit 0", rc == 0, rc)
    pl = os.path.join(out, "compare", "per_lead.json")
    if rc != 0 or not os.path.isfile(pl):
        return
    per = C.read_json(pl)
    want = ["rival_bardl_h1", "rival_bardl_h1_declined"] + (["rival_ridge"] if ridge else [])
    check("compare: models found by their folder names", per.get("models") == want, per.get("models"))
    lk = per.get("links") or {}
    check("compare: BARDL's link key identity|c=-|ub=1", lk.get("rival_bardl_h1") == "identity|c=-|ub=1", lk)
    check("compare: the declined copy is labelled declined by its guard",
          per.get("declined_by_guard") == ["rival_bardl_h1_declined"], per.get("declined_by_guard"))
    exp_main = ["rival_bardl_h1"] + (["rival_ridge"] if ridge and lk.get("rival_ridge") == lk.get("rival_bardl_h1")
                                     else [])
    check("compare: main set = BARDL and its same-link, guard-passing rivals", per.get("main_set") == exp_main,
          per.get("main_set"))
    with open(os.path.join(out, "compare", "AW3_table.md"), encoding="utf-8") as fh:
        aw3 = fh.read()
    check("compare: AW3 table labels the pair 'raw model, declined by its guard'",
          "raw model, declined by its guard: rival_bardl_h1_declined" in aw3, aw3.count("declined by its guard"))
    import bardl_shap  # noqa: F401  (the board's pins before numpy, for reading the parquet results)
    import pandas as pd
    import pyarrow.parquet as pq
    fam = pq.read_table(os.path.join(out, "compare", "families.parquet")).to_pandas()
    fb = fam[fam["model"] == "rival_bardl_h1"].set_index("family")["share"]
    check("compare: BARDL's families: own history + local drivers = 100%, seasonal normal 0",
          abs(float(fb.get("own history", 0)) + float(fb.get("local drivers", 0)) - 1.0) <= 1e-12
          and float(fb.get("seasonal normal", 0)) == 0.0, fb.to_dict())
    imp = pq.read_table(os.path.join(out, "compare", "importance.parquet")).to_pandas()
    mi = imp[(imp["model"] == "rival_bardl_h1")]
    feat = set(mi.loc[mi["level"] == "feature", "player"])
    var = set(mi.loc[mi["level"] == "variable", "player"])
    check("compare: importance.parquet holds BARDL's 10 players and 4 variables",
          set(meta["players"]) <= feat and set(meta["variables"]) <= var, [len(feat), len(var)])
    # bardl_shap.py once more on the same models root: skipped, and no REMINDER (compare_shap.py's own done record
    # covers the finished BARDL piece)
    need_guard("bardl_shap.py after the comparison", log)
    sroot = os.path.join(W, "sample")
    K = int(C.read_json(os.path.join(sroot, "sample_manifest.json"))["n_asked"])
    rc = run_child(bardl_cmd(W, "--n", str(K), "--sample-root", sroot, "--register",
                             os.path.join(sroot, "SAMPLE_REGISTER.txt"), "--out-root", out), log,
                   "bardl_shap.py after the comparison")
    with open(os.path.join(W, "logs", "bardl_shap_ndvi_lead0.log"), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    lines = lines[max(i for i, ln in enumerate(lines) if "BARDL SHAP ndvi lead 0" in ln):]
    check("compare: bardl_shap.py afterwards: skipped, no REMINDER (the comparison covers its piece)",
          rc == 0 and any("skipped" in ln for ln in lines) and not any("REMINDER" in ln for ln in lines),
          [rc] + lines[-2:])
    check("compare: no analysis log written or changed", logs_state() == logs0, sorted(logs_state()))
    REPORT["_compare"] = {"models": per.get("models"), "links": lk, "main_set": per.get("main_set"),
                          "families_bardl": fb.to_dict()}


# ---------------------------------------------------------------------------------------------------------------
def main():
    a = parse()
    W = os.path.join(C.ROOT, "smoke", "bardl_%s" % a.label)
    if a.step == "ridge-child":
        return child_ridge(W, a)
    if a.step == "compare-child":
        return child_compare(W, a)
    C.makedirs(W)
    log = C.Log("smoke_bardl", os.path.join(W, "logs"))
    steps = list(STEPS) if a.step == "all" else [a.step]
    for s in steps:
        prepare(W, s, a.fresh, log)
    path = os.path.join(W, "smoke_report.json")
    report = C.read_json(path) if os.path.isfile(path) else {}
    code = 0
    for s in steps:
        REPORT.clear()
        del FAIL[:]
        t0 = time.time()
        log("smoke step %s (label %s)" % (s, a.label))
        guard_stop = None
        try:
            {"synthetic": step_synthetic, "exact": step_exact, "real": step_real, "compare": step_compare}[s](W, log, a)
        except GuardStop as exc:
            guard_stop = str(exc)
            log("STOPPED: %s" % exc)
        report[s] = {"checks": dict(REPORT), "failed": list(FAIL), "guard_stop": guard_stop,
                     "seconds": round(time.time() - t0, 1), "finished": datetime.datetime.now().isoformat(
                         timespec="seconds"), "peak_rss_gb": C.rss_gb()}
        C.write_json(path, report)
        n = len([k for k in REPORT if not k.startswith("_")])
        log("smoke step %s: %d checks, %d failed%s, %.1f s" % (s, n, len(FAIL), "; guard stop" if guard_stop else "",
                                                                time.time() - t0))
        if guard_stop:
            code = 4
            break
        if FAIL:
            code = 1
    sys.exit(code)


if __name__ == "__main__":
    main()
