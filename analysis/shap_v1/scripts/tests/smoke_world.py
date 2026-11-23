"""End-to-end smoke of the gridded treeroute path on an engine smoke world (R21: 4 regions, 40 units, 12 trees),
with a given engine snapshot. Everything is written under smoke/world_<problem>/ (smoke only, never a result).

  py -3.9 -I -B smoke_world.py --problem pm25 [--engine-root DIR] [--lead 0] [--arm NAME] [--restricted]

1. the reference: the engine's own smoke run (Pipeline.run, the run's own decision and test pass) into
   smoke/world_<p>/engine_runs (skipped when finished);
2. a registered 12-row sample of 3 units (hash order) from the reference's saved test rows;
3. tr_rebuild.py --kind smoke against the reference (all units routed, or with --restricted only the sample's
   units, as the real runs; --arm routes another saved arm of the reference, e.g. the region kind with a log_c
   corrector arm), every saved row of the routed units checked;
4. a B2 background from the rebuild's router fit rows (registered), then tr_shap.py (every stop rule).
LIMIT: every smoke world builds its reference on TODAY's OS and libraries, so it cannot detect a difference between
the old and the new installation; only a real headline rebuild (the coral pilot) can.
"""
import argparse
import os
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
import shapv1_common as C  # noqa: E402


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", required=True)
    ap.add_argument("--engine-root", default=None)
    ap.add_argument("--lead", type=int, default=0)
    ap.add_argument("--step", default="all", choices=("all", "reference"))
    ap.add_argument("--arm", default=None, help="route this saved arm instead of the kept one (tr_rebuild --smoke-arm)")
    ap.add_argument("--restricted", action="store_true", help="route only the sample's units (as the real runs)")
    return ap.parse_args()


def main():
    a = parse()
    P = C.PROBLEMS[a.problem]
    eng = os.path.abspath(a.engine_root or P["engine"])
    w = C.makedirs(os.path.join(C.ROOT, "smoke", "world_%s" % a.problem))
    machine = os.path.join(w, "machine.yaml")
    C.write_text(machine, "run_root: %s\ntemp_dir: %s\nregistry_dir: D:/treeroute/registry\n"
                 % ((w + "/engine_runs").replace("\\", "/"), (w + "/engine_tmp").replace("\\", "/")))
    log = C.Log("smoke_world_%s" % a.problem, os.path.join(w, "logs"))
    if a.step == "reference":
        sys.path.insert(0, eng)
        from treeroute import launch
        launch.pin_threads()
        from treeroute.runs.machine import load_machine
        from treeroute.pipeline.run import Pipeline
        m = load_machine(machine)
        pipe = Pipeline(C.package_dir(a.problem), m.run_root, "smoke", machine=m, echo=lambda s: log("engine| " + s))
        folder = pipe.run()
        C.write_text(os.path.join(w, "reference.txt"), str(folder))
        log("reference smoke run finished: %s" % folder)
        return
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("OMP_", "OPENBLAS_", "MKL_", "NUMEXPR_",
                                                                             "BLIS_", "VECLIB_"))}
    py = [sys.executable, "-I", "-B"]
    ref_file = os.path.join(w, "reference.txt")
    if not os.path.isfile(ref_file):
        rc = subprocess.call(py + [os.path.abspath(__file__), "--problem", a.problem, "--engine-root", eng,
                                   "--step", "reference"], env=env)
        if rc != 0:
            raise SystemExit("reference smoke run failed (%d)" % rc)
    ref = open(ref_file, encoding="utf-8").read().strip()
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq
    tp = pq.read_table(os.path.join(ref, "test_preds.parquet") if a.lead == 0 else os.path.join(
        ref, "ladder", "lead_%d" % a.lead, "test_preds.parquet")).to_pandas()
    tp = tp[np.isfinite(tp["y"].to_numpy(np.float64))]
    units = C.hash_order("shap_v1|smoke|%s" % a.problem, sorted(tp["unit"].astype(str).unique()))[:3]
    rows = []
    for u in sorted(units):
        tu = tp[tp["unit"].astype(str) == u]
        for yv in sorted(tu["year"].unique()):
            cand = tu[tu["year"] == yv]
            pick = C.hash_order("shap_v1|smoke|row", ["%s|%d" % (u, t) for t in cand["time"]])[0]
            rows.append(cand[cand["time"] == int(pick.rsplit("|", 1)[1])].iloc[0][["unit", "group", "time", "year"]])
    S = pd.DataFrame(rows).reset_index(drop=True)
    S.insert(0, "row", np.arange(len(S)))
    tag = "smoke" + ("_" + a.arm if a.arm else "") + ("_restricted" if a.restricted else "")
    sroot = C.makedirs(os.path.join(w, "sample" if tag == "smoke" else "sample_" + tag))
    C.write_parquet(os.path.join(sroot, "sample.parquet"), S)
    reg = os.path.join(sroot, "SAMPLE_REGISTER.txt")
    ssha = C.sha256_file(os.path.join(sroot, "sample.parquet"))
    with open(C.assert_writable(reg), "w", encoding="utf-8") as fh:
        fh.write("smoke problem=%s tag=%s n=%d sample=%s\n" % (a.problem, tag, len(S), ssha))
    rb = os.path.join(w, "rebuild_lead_%d%s" % (a.lead, "" if tag == "smoke" else "_" + tag))
    machine2 = os.path.join(w, "machine_rebuild.yaml")          # the rebuild's own run root (as in real use)
    C.write_text(machine2, "run_root: %s\ntemp_dir: %s\nregistry_dir: D:/treeroute/registry\n"
                 % ((w + "/rebuild_engine_runs").replace("\\", "/"), (w + "/rebuild_engine_tmp").replace("\\", "/")))
    cmd = py + [os.path.join(SCRIPTS, "tr_rebuild.py"), "--problem", a.problem, "--lead", str(a.lead), "--kind",
                "smoke", "--reference", ref, "--engine-root", eng, "--machine", machine2, "--sample-root", sroot,
                "--register", reg, "--out-root", rb, "--arcsine-tolerance", "1e-12"]
    if not a.restricted:
        cmd.append("--all-units")
    if a.arm:
        cmd += ["--smoke-arm", a.arm]
    rc = subprocess.call(cmd, env=env)
    if rc != 0:
        raise SystemExit("tr_rebuild failed or stopped at a gate (%d)" % rc)
    R = pq.read_table(os.path.join(rb, "rows.parquet")).to_pandas()
    if not (R["role"] == "fit").any():                    # the region kind saves the units' rows in routers.npz
        Z = np.load(os.path.join(rb, "routers.npz"), allow_pickle=False)
        cut = int(C.read_json(os.path.join(P["export"], "lead_%d" % a.lead, "export_manifest.json"))["cuts"]["fit_cut"])
        R = pd.DataFrame({"unit": Z["all_units"].astype(str), "time": Z["all_time"].astype(np.int64)})
        R = R[R["time"] <= cut]
        R["role"] = "fit"
    spy = 12 if a.problem in ("pm25", "ndvi", "fire") else 1
    bg = []
    for r, u, t in zip(S["row"], S["unit"].astype(str), S["time"].astype(int)):
        f = R[(R["unit"] == u) & (R["role"] == "fit")]
        f = f[(f["time"] % spy) == (t % spy)] if spy > 1 else f
        bg += [(int(r), u, int(tt)) for tt in f["time"]]
    bname = "background_lead_%d.parquet" % a.lead
    C.write_parquet(os.path.join(sroot, bname), pd.DataFrame(bg, columns=["row", "unit", "time"]))
    with open(C.assert_writable(reg), "a", encoding="utf-8") as fh:   # the background joins the register
        fh.write("smoke problem=%s tag=%s n=%d sample=%s %s=%s\n" % (a.problem, tag, len(S), ssha, bname,
                                                                     C.sha256_file(os.path.join(sroot, bname))))
    rc = subprocess.call(py + [os.path.join(SCRIPTS, "tr_shap.py"), "--problem", a.problem, "--lead", str(a.lead),
                               "--rebuild", rb, "--sample-root", sroot, "--register", reg,
                               "--out-root", os.path.join(w, "out" if tag == "smoke" else "out_" + tag)], env=env)
    log("smoke world %s lead %d: tr_shap exit %d" % (a.problem, a.lead, rc))
    sys.exit(rc)


if __name__ == "__main__":
    main()
