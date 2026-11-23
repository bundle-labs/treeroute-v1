"""The one runner the owner starts, per problem and scope (PROTOCOL.md 2; RUN_COMMANDS.md).

  py -3.9 -I -B D:/treeroute/analysis/shap_v1/scripts/run_shap.py --problem coral --scope i
        [--n 1000] [--arcsine-tolerance 0] [--recorded-path-map] [--defo-regions 0] [--with-pinned] [--skip-rf]
        [--dry-run]

Order per problem: the sample (all reported leads, registered once; a registered sample is never replaced, and the
runner refuses when --n or --defo-regions differ from it), then the treeroute rebuild of every tree lead in ONE
engine process (its input pre-check E3a runs before the target is read), then per lead in scope: the treeroute SHAP,
the rivals (load or rebuild, exactness, SHAP), the comparison. Every step is its own process (the engine and the
rival boards need different thread pins) started with a clean environment; every step skips the pieces it finished
before under the same identity (resume = start the same command again). A step that stops on a gate (exit 3) is
recorded and the runner goes on with the next independent step; nothing later reads a stopped model.
Refuses to start while another engine job holds D:/treeroute/tmp's heavy-job lock (one heavy job per machine).
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shapv1_common as C  # noqa: E402

CLEAN_PREFIXES = ("OMP_", "OPENBLAS_", "MKL_", "NUMEXPR_", "BLIS_", "VECLIB_", "GOTO", "KMP_", "SKLEARN", "SCIPY_",
                  "NPY_", "DAAL", "ONEDAL", "TBB_")


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", required=True, choices=sorted(C.PROBLEMS))
    ap.add_argument("--scope", required=True, choices=sorted(C.SCOPES))
    ap.add_argument("--n", type=int, default=C.DEFAULT_N)
    ap.add_argument("--arcsine-tolerance", type=float, default=0.0, help="owner decision D8 (default bit identity)")
    ap.add_argument("--recorded-path-map", action="store_true", help="owner decision D14 (b)")
    ap.add_argument("--ignore-ram-warning", action="store_true",
                    help="go on although the engine's RAM pre-flight warns that the run will be refused")
    ap.add_argument("--defo-regions", type=int, default=0)
    ap.add_argument("--with-pinned", action="store_true", help="D5 (b): explain the pinned arm at declined leads")
    ap.add_argument("--skip-rf", action="store_true", help="leave the RF rebuild for a later run")
    ap.add_argument("--draws", type=int, default=2000)
    ap.add_argument("--precheck", action="store_true",
                    help="only the sample (registered) and the rebuild's input pre-checks E0/E3a/E3m (minutes), then stop")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def clean_env():
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith(CLEAN_PREFIXES) and k.upper() != "PYTHONHASHSEED"}
    return env


def step(log, name, args, dry, summary):
    cmd = [sys.executable, "-I", "-B", os.path.join(HERE, args[0])] + [str(x) for x in args[1:]]
    log("STEP %s: %s" % (name, " ".join(cmd[3:])))
    if dry:
        summary.append({"step": name, "status": "dry-run"})
        return 0
    t0 = time.time()
    rc = subprocess.call(cmd, env=clean_env())
    rec = {"step": name, "exit": rc, "seconds": round(time.time() - t0, 1),
           "status": {0: "done", 3: "stopped at a gate (a stop rule)"}.get(rc, "failed")}
    summary.append(rec)
    log("STEP %s: %s in %.1f s" % (name, rec["status"], rec["seconds"]))
    return rc


def check_registered(a, log):
    """The registered sample must be the one this command asks for (N, defo regions): refuse otherwise."""
    root = C.sample_dir(a.problem)
    ident = C.sample_identity(a.problem, root)
    want_n, want_r = int(a.n), int(a.defo_regions or 0)
    got_n, got_r = int(ident.get("n_asked") or -1), int(ident.get("defo_regions") or 0)
    if got_n != want_n or got_r != want_r:
        raise SystemExit("REFUSED: the registered %s sample was made with --n %d --defo-regions %d, this command "
                         "asks for --n %d --defo-regions %d. A registered sample is never replaced: use its own "
                         "settings, or register a new sample under a new tag (owner decision)"
                         % (a.problem, got_n, got_r, want_n, want_r))
    log("sample: registered sample found (%s), N %d, defo regions %s" % (ident["sample_sha256"][:16], got_n,
                                                                         got_r or "all"))


def main():
    a = parse()
    log = C.Log("run_%s_scope_%s" % (a.problem, a.scope))
    lock = "D:/treeroute/tmp/treeroute_heavy_job.lock"
    if os.path.exists(lock):
        raise SystemExit("REFUSED: another engine job holds %s; run one heavy job at a time" % lock)
    leads = C.SCOPES[a.scope][a.problem]
    log("problem %s, scope (%s): leads %s; N %d; arcsine tolerance %g; recorded path map %s; with pinned %s"
        % (a.problem, a.scope, leads, a.n, a.arcsine_tolerance, a.recorded_path_map, a.with_pinned))
    summary = []
    sfile = os.path.join(C.sample_dir(a.problem), "sample.parquet")
    if os.path.isfile(sfile) and C.registered(a.problem, sfile):
        check_registered(a, log)
    else:
        rc = step(log, "sample", ["make_sample.py", "--problem", a.problem, "--n", a.n, "--defo-regions",
                                  a.defo_regions], a.dry_run, summary)
        if rc != 0 and not a.dry_run:
            raise SystemExit("the sample step failed; nothing else runs")
    tree_leads = [L for L in leads if L in C.KEPT_TREE_LEADS[a.problem] or a.with_pinned]
    if tree_leads:                                     # one engine process for every lead: census and derive once
        args = ["tr_rebuild.py", "--problem", a.problem, "--leads"] + list(tree_leads) + [
            "--arcsine-tolerance", a.arcsine_tolerance]
        if a.recorded_path_map:
            args.append("--recorded-path-map")
        if a.ignore_ram_warning:
            args.append("--ignore-ram-warning")
        if a.with_pinned:
            args.append("--explain-pinned")
        if a.precheck:
            args.append("--precheck-only")
        step(log, "treeroute rebuild leads %s%s" % (tree_leads, " (pre-check only)" if a.precheck else ""), args,
             a.dry_run, summary)
    if a.precheck:
        log("pre-check finished: %s" % json.dumps([(s["step"], s["status"]) for s in summary]))
        return
    for L in leads:
        if L in tree_leads:
            if a.dry_run or os.path.isfile(os.path.join(C.rebuild_dir(a.problem, L), "DONE.json")):
                step(log, "treeroute SHAP lead %d" % L, ["tr_shap.py", "--problem", a.problem, "--lead", L],
                     a.dry_run, summary)
            else:
                log("lead %d: no finished treeroute rebuild (a gate stopped it, or it declined): no treeroute SHAP" % L)
        else:
            log("lead %d: the kept prediction is a feature-free baseline: treeroute has no SHAP here (D5)" % L)
        learners = ["ridge", "lgbm", "lgbm_tweedie", "hgb_l1"] + ([] if a.skip_rf else ["rf"])
        step(log, "rivals lead %d" % L, ["rival_shap.py", "--problem", a.problem, "--lead", L, "--learners"] + learners,
             a.dry_run, summary)
        step(log, "compare lead %d" % L, ["compare_shap.py", "--problem", a.problem, "--lead", L, "--draws", a.draws],
             a.dry_run, summary)
    path = os.path.join(C.ROOT, "out", a.problem, "RUN_SUMMARY_scope_%s.json" % a.scope)
    if not a.dry_run:
        C.write_json(path, {"problem": a.problem, "scope": a.scope, "leads": leads, "steps": summary,
                            "finished": time.strftime("%Y-%m-%d %H:%M:%S")})
    log("runner finished: %s" % json.dumps([(s["step"], s["status"]) for s in summary]))


if __name__ == "__main__":
    main()
