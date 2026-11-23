"""Build, extend and verify the legacy-harness golden registry (plan 4.4).

THE REGISTRY IS A WRITE-ONCE SERIES. goldens.json is version 1; later versions are goldens_v2.json,
goldens_v3.json, ... Every file is written once and never changed. A new version supersedes the
previous one and records what changed (`supersedes`, `changes`). Every reader (verify, and
`rooted_copy.py check`) uses the NEWEST version.

    py -3.9 goldens.py build                              # version 1 only; refuses, goldens.json exists
    py -3.9 goldens.py next --note "why"                  # next version: fire block and launcher record
                                                          #   regenerated, the other goldens carried over
    py -3.9 goldens.py next --fire-run DIR --note "why"   # ... and FOLD a captured fire run into it
    py -3.9 goldens.py verify                             # read-only: re-hash every registered file
    py -3.9 goldens.py verify --fire-run DIR              # check the fire run in DIR (unfolded registry)
    py -3.9 goldens.py verify --deep                      # also re-hash the defo bank files (~3.7 GB)
    py -3.9 goldens.py verify --registry FILE             # verify an older version instead

WHERE THE FIRE GOLDEN'S HASHES LIVE IS AN OWNER DECISION (README.md "Registry versions"):
  A. fold them into the next registry version (`next --fire-run DIR`); verify then re-hashes them
     from the registry, like every other golden;
  B. keep the run's own never-overwritten launcher.json as the registry of that run-captured
     golden; verify re-hashes the outputs listed there (default folder D:/treeroute/golden/
     fire_smoke, or --fire-run DIR after a retry).
Both are implemented; neither happens by itself.

Nothing here runs a model or writes outside this folder.
Outside the product: the engine never imports this module (G-IMPORT). The harness may name problems.
"""
import glob
import hashlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
REGISTRY = os.path.join(HERE, "goldens.json")            # version 1
SHIPPED_JSON = "D:/treeroute/registry/shipped.json"
BACKUP = "D:/treeroute/registry/backup_20260928"
SPEEDPROOF = "D:/treeroute/speedproof"
GOLDEN = "D:/treeroute/golden"

# ---- the fire smoke golden: configuration and commands (the harness may name problems)
FIRE_OUT = GOLDEN + "/fire_smoke"                        # the DEFAULT (first-attempt) run folder
FIRE_ARGV = ["--problem=fire", "--calib=strict", "--smoke=1"]
FIRE_PREFIXES = ["D:/fire/pool_features_", "D:/fire/lead1_pool_", "D:/fire/A_"]
FIRE_WATCH = ["D:/fire", "D:/joblib_tmp"]
FIRE_EXPECTED_REL = ["fire_strict_smoke/_adaptation.log", "fire_strict_smoke/_preds.npz",
                     "fire_strict_smoke/_verdicts.csv", "console.txt"]
FIRE_CAUTION_GB = 8.5          # the agent's caution choice (NOT a measured requirement)
FIRE_SHIPPED_GUARD_GB = 5.0    # the shipped guard before the pool build (adaptation.py run_fire)

FIRE_RAM_EVIDENCE = [
    "FOR A LOWER THRESHOLD: the run that produced the registered reference fire_strict/_preds.npz "
    "(D:/adaptation/fire_strict/_adaptation.log, block starting 00:27:51; file time 2026-09-22 "
    "01:34; full width, npd 300, all five arms) logged 5.7 GB free before the pool build and 5.1 GB "
    "before the bank, and finished (link_corrector MAE 0.003993, ADOPTED).",
    "FOR A LOWER THRESHOLD: the 14:04:08 block of the same log (npd 300, --sweeponly) logged 6.2 GB "
    "before the pool build and 3.8 GB before the bank, and finished its routing.",
    "FOR A LOWER THRESHOLD: the shipped guards ask for 5.0 GB before the pool build and 3.0 GB before "
    "the bank (adaptation.py guard(5.0) / guard(3.0) in run_fire). The throttle FA.wait_mem then "
    "waits, instead of dying, before the pool build while under 2.5 GB (adaptation.py) and between "
    "regions while under 1.2 GB (fire_architecture.build_pool).",
    "FOR CAUTION: the 02:51:23 SMOKE block of the same log logged 7.2 GB before the pool build and "
    "never logged again (the next line is a new run at 03:13:34); the adaptation.py comment at the "
    "pool build records 'measured 7.2 -> 1.2 GB free on the smoke run, which is the level this "
    "machine has hung at twice'.",
    "LIMIT OF THE EVIDENCE: fire_architecture's PAUSED/RESUMED messages print to the console only, "
    "so _adaptation.log cannot show whether a run paused. The 00:27 pool build took 18 min, inside "
    "the 11.5-20 min range of the other blocks. The smoke builds the same 40-region pool as the "
    "full run (npd changes only the bank), so its pool-build memory is the same.",
    "The shipped fire_strict_smoke (22:47, D:/adaptation/fire_strict_smoke/_adaptation.log) went "
    "from 8.7 GB before the pool build to 4.9 GB before the bank.",
]


def fire_command(out_dir=FIRE_OUT, min_gb=FIRE_CAUTION_GB, scratch=None, check_only=False):
    """The fire golden command. A retry uses a NEW out_dir (it is also ADAPTATION_OUT_ROOT)."""
    return ('cd "%s"\n' % HERE
            + "py -3.9 -u launch_pinned.py --script adaptation_rooted.py --copy-of ../../adaptation.py "
            "--out-dir %s --env ADAPTATION_OUT_ROOT=%s%s %s %s --min-avail-gb %.1f%s -- %s"
            % (out_dir, out_dir, "" if not scratch else " --scratch " + scratch,
               " ".join("--redirect-prefix " + p for p in FIRE_PREFIXES),
               " ".join("--watch " + w for w in FIRE_WATCH), min_gb,
               " --check-only" if check_only else "", " ".join(FIRE_ARGV)))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fwd(p):
    return p.replace("\\", "/")


def absfwd(p):
    return fwd(os.path.abspath(p)).rstrip("/")


def entry(path, shipped=None, role=None):
    """{path, size, sha256, sha256_from[, matches_shipped_json][, role]} -- hashed now."""
    path = fwd(path)
    e = {"path": path, "size": os.path.getsize(path), "sha256": sha256_file(path),
         "sha256_from": "hashed by goldens.py"}
    if shipped is not None and path in shipped:
        e["matches_shipped_json"] = (shipped[path]["sha256"] == e["sha256"]
                                     and shipped[path]["size"] == e["size"])
    if role:
        e["role"] = role
    return e


def registry_entry(path, shipped, role=None):
    """An entry copied from shipped.json WITHOUT re-hashing (large bank files); verify --deep re-hashes."""
    s = shipped[path]
    e = {"path": path, "size": s["size"], "sha256": s["sha256"], "sha256_from": SHIPPED_JSON}
    if role:
        e["role"] = role
    return e


def folder(path):
    return sorted(fwd(os.path.join(dp, f)) for dp, _d, fn in os.walk(path) for f in fn)


def load_shipped():
    with open(SHIPPED_JSON, encoding="utf-8") as f:
        d = json.load(f)
    return {x["path"]: x for x in d["files"]}, d.get("created")


def _verdict(path):
    with open(path, encoding="utf-8") as f:
        v = json.load(f)
    cfg = v.get("config", {})
    return {"adopted": v.get("adopted"), "regression_gate": v.get("regression_gate"),
            "argv": v.get("argv"), "npd": cfg.get("NPD"), "levels": cfg.get("LEVELS"),
            "ratios": cfg.get("RATIOS"), "started": v.get("started"), "finished": v.get("finished")}


# ------------------------------------------------------------------------------ registry versions

def registry_versions(here=HERE):
    """[(n, path)] of every registry version on disk, oldest first (goldens.json is version 1).
    Fails loudly on a gap in the numbering (a version must never go missing)."""
    out = []
    v1 = os.path.join(here, "goldens.json")
    if os.path.exists(v1):
        out.append((1, fwd(v1)))
    for p in glob.glob(os.path.join(here, "goldens_v*.json")):
        m = re.fullmatch(r"goldens_v(\d+)\.json", os.path.basename(p))
        if m and int(m.group(1)) >= 2:
            out.append((int(m.group(1)), fwd(p)))
    out.sort()
    if [n for n, _ in out] != list(range(1, len(out) + 1)):
        raise SystemExit("goldens.py: the registry versions in %s are not 1..N without gaps: %s"
                         % (here, [n for n, _ in out]))
    return out


def latest_registry(here=HERE):
    v = registry_versions(here)
    if not v:
        raise SystemExit("goldens.py: no registry in %s (run `goldens.py build`)" % here)
    return v[-1]


# ------------------------------------------------------------------------------------------ build

def build_pm25(shipped):
    s_path = os.path.join(PROJECT, "pm25_adaptation.py")
    s_now = sha256_file(s_path)
    with open(SPEEDPROOF + "/wide_golden_blas1/launcher.json", encoding="utf-8") as f:
        lj = json.load(f)
    common = {
        "problem": "pm25",
        "produced_by_script": fwd(s_path),
        "produced_by_script_sha256": lj["shipped_sha256"],
        "script_sha256_now": s_now,
        "script_unchanged_since": s_now == lj["shipped_sha256"],
        "rerun": "no (task rule: register, do not re-run)",
        "evidence": [SPEEDPROOF + "/compare_gates_final.txt", SPEEDPROOF + "/compare_gates_final.json",
                     SPEEDPROOF + "/fix_round_status.txt",
                     fwd(os.path.join(PROJECT, "engine", "speedproof", "SPEEDPROOF_REPORT.md"))],
    }
    u2 = dict(common)
    u2.update({
        "what": "PM2.5 U2 smoke of the shipped pm25_adaptation.py: 8 donors, 3 test regions, 40 cells, "
                "12 trees/donor, one-point grid (10, 0.0625), links identity/log/logc. The primal "
                "router path (Part 556 configuration).",
        "command": 'cd "C:\\Users\\moh the ghost\\Desktop\\data set for reserch paper"\n'
                   "py -3.9 -u pm25_adaptation.py --smoke --links identity,log,logc --levels 10 "
                   "--ratios 0.0625 --run-dir D:/treeroute/speedproof/golden_smoke "
                   "--expect-from D:/pm25_adapt/smoke/inner_candidates.csv",
        "run_at": "2026-09-28 11:55-11:59 (speed proof round 1)",
        "threads": "NOT pinned by a launcher: the shipped script as launched from a shell with no "
                   "thread variables, i.e. numpy OpenBLAS 16, scipy OpenBLAS 4, OpenMP 4 "
                   "(SPEEDPROOF_REPORT.md finding 3). At this width the router solves are too small "
                   "for OpenBLAS to use more than one thread (finding 4), and gate G10 shows it "
                   "bit-identical to the copy run with every BLAS at 1 thread (final2_u2_w8).",
        "facts": ["bit-identical to the shipped D:/pm25_adapt/u2_smoke (speed proof round 1)",
                  "Part 556 regression gate inside the run: worst 8.88e-16 against "
                  "D:/pm25_adapt/smoke/inner_candidates.csv (tolerance 1e-4)"],
        "summary": _verdict(SPEEDPROOF + "/golden_smoke/verdict.json"),
        "gates": ["plan 4.4: PM2.5 replay equals the golden smoke (target 1e-9, hard stop 1e-4) -- "
                  "U2 flags, primal path",
                  "plan 4.5 speedups 1 and 2: byte-identical smoke against the current code "
                  "(G10 passed on the speed-proof copy)"],
        "files": [entry(p) for p in folder(SPEEDPROOF + "/golden_smoke")]
                 + [entry(SPEEDPROOF + "/golden_smoke.console.txt", role="console")],
    })
    wide = dict(common)
    wide.update({
        "what": "PM2.5 WIDE smoke of the shipped pm25_adaptation.py with every BLAS pinned to 1 "
                "thread: 8 donors, 3 test regions, 400 trees/donor (3,200 trees), the default "
                "35-point grid, links identity/log/logc. Reaches the dual solve, NVERIFY and the "
                "(1.0, 0.5) contract check.",
        "command": 'cd "C:\\Users\\moh the ghost\\Desktop\\data set for reserch paper\\engine\\speedproof"\n'
                   "py -3.9 -u run_shipped_blas1.py --smoke --npd 400 --links identity,log,logc "
                   "--run-dir D:/treeroute/speedproof/wide_golden_blas1",
        "run_at": "%s to %s (speed proof round 2)" % (lj["started"], lj["finished"]),
        "launcher": lj["launcher"], "launcher_sha256": lj["launcher_sha256"],
        "threads": "pinned: numpy and scipy OpenBLAS at 1 thread for the whole process "
                   "(threadpoolctl, after both loaded); OpenMP 4 (the shipped cap_threads). "
                   "Recorded in launcher.json: blas_all_one_thread_at_end=%s."
                   % lj.get("blas_all_one_thread_at_end"),
        "facts": ["G7 (speedup-3 plan gate): bit-identical to the speed-proof copy on 8 router "
                  "workers at BLAS 1 (wide_final_w8)",
                  "G8: the shipped script as launched (wide_golden, BLAS numpy 16 / scipy 4) differs "
                  "by at most 3.55e-13 ug/m3 on test predictions; every decision equal",
                  "temp files were redirected by name to D:/treeroute/speedproof/tmp; nothing was "
                  "written to D:/pm25"],
        "summary": _verdict(SPEEDPROOF + "/wide_golden_blas1/verdict.json"),
        "gates": ["plan 4.4: PM2.5 replay equals the golden captured under the pins (target 1e-9, "
                  "hard stop 1e-4) -- the pinned golden, and the only one wide enough to exercise "
                  "the dual solve, NVERIFY and the contract check",
                  "plan 4.5 speedup 3: byte-identical across router worker counts at BLAS 1 (G7 passed)"],
        "files": [entry(p) for p in folder(SPEEDPROOF + "/wide_golden_blas1")]
                 + [entry(SPEEDPROOF + "/wide_golden_blas1.console.txt", role="console")],
    })
    return u2, wide


def build_fire(shipped):
    """The fire_smoke block, always PENDING here; `next --fire-run` folds a captured run into it."""
    src = os.path.join(PROJECT, "adaptation.py")
    copy = os.path.join(HERE, "adaptation_rooted.py")
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import rooted_copy
    chk = rooted_copy.check(src, copy)
    refs = [p for p in sorted(shipped) if p.startswith(("D:/adaptation/fire_strict/_preds.npz",
                                                          "D:/adaptation/fire_strict/_verdicts.csv",
                                                          "D:/adaptation/fire_strict/_adaptation.log",
                                                          "D:/adaptation/fire_strict_smoke/"))]
    return {
        "problem": "fire",
        "status": "PENDING -- not run yet",
        "why_pending": (
            "not run on 2026-09-28. The launcher refused at 5.70 GB available because the agent had "
            "chosen --min-avail-gb %.1f. %.1f GB is a CAUTION CHOICE, NOT a measured requirement: "
            "the run that produced the registered reference fire_strict/_preds.npz started with "
            "5.7 GB free and finished, while a smoke started at 7.2 GB fell to 1.2 GB and died "
            "(evidence in ram_threshold). The OWNER picks the threshold: close the browser (it held "
            "about 5 GB) and run at %.1f, or run at a lower --min-avail-gb such as %.1f (the "
            "shipped guard). 5.77 GB was available at the fix-round check."
            % (FIRE_CAUTION_GB, FIRE_CAUTION_GB, FIRE_CAUTION_GB, FIRE_SHIPPED_GUARD_GB)),
        "ram_threshold": {
            "caution_gb": FIRE_CAUTION_GB, "shipped_guard_gb": FIRE_SHIPPED_GUARD_GB,
            "decided_by": "owner (not decided yet)", "evidence": FIRE_RAM_EVIDENCE},
        "what": "Fire smoke of the shipped adaptation.py nowcast in its shipped configuration: "
                "--problem=fire --calib=strict --smoke=1, every arm (raw=base, link, raw_corrector, "
                "link_corrector, placebo): 30 donors, 10 test regions, 40 trees/donor, 40 test "
                "cells/region (fire_evt_arch default_rng(7) picks), TRAIN_END 2018, inner 2017-18.",
        "argv": FIRE_ARGV,
        "commands": {"caution_%.1f_gb" % FIRE_CAUTION_GB: fire_command(min_gb=FIRE_CAUTION_GB),
                     "shipped_guard_%.1f_gb" % FIRE_SHIPPED_GUARD_GB:
                         fire_command(min_gb=FIRE_SHIPPED_GUARD_GB),
                     "preflight_only": fire_command(check_only=True)},
        "default_run_dir": FIRE_OUT,
        "retry": "a failed attempt keeps its folder and its launcher.json (never overwritten). A retry "
                 "needs a NEW folder for BOTH --out-dir and ADAPTATION_OUT_ROOT (the launcher refuses "
                 "an --env path outside --out-dir, and an --out-dir that holds files), and a scratch "
                 "folder with no files: the owner clears D:/treeroute/golden/_scratch by hand (a "
                 "failed run can leave a multi-GB pool file there) or passes --scratch <new folder>. "
                 "Then `goldens.py verify --fire-run <new folder>`.",
        "script": fwd(copy), "script_sha256": chk["copy_sha256"],
        "source": fwd(src), "source_sha256": chk["source_sha256"],
        "rooted_copy_check": {k: chk[k] for k in ("ok", "problems", "changed_lines", "unified_diff")},
        "outputs_expected_relative": FIRE_EXPECTED_REL + ["launcher.json"],
        "hashes_live_in": "OWNER DECISION, not made yet: (A) folded into the next registry version by "
                          "`goldens.py next --fire-run DIR`, or (B) the run's own launcher.json "
                          "('outputs': path, size, sha256 of every file, written once by "
                          "launch_pinned.py), read by `goldens.py verify [--fire-run DIR]`",
        "threads": "pinned by launch_pinned.py: OPENBLAS/MKL/BLIS/VECLIB = 1 and OMP/NUMEXPR = 4 set "
                   "before numpy loads, then numpy + scipy.linalg imported and threadpoolctl BLAS = 1 "
                   "for the process. Fire routes per cell (router units), which A8 runs at BLAS 1; "
                   "the whole-process BLAS 1 is the harness task's wording, not literally A8 (owner "
                   "question). The shipped fire runs used numpy BLAS 16 / scipy 4, so this golden may "
                   "differ from them at the 1e-13 rounding level (as PM2.5's G8 did).",
        "scratch": "fire_architecture writes its pool and tree matrices to D:/fire/pool_features_<pid>"
                   ".f32 and D:/fire/A_<tag>_<pid>.f16 (not protected, but outside the harness write "
                   "scope); the launcher redirects those names to the scratch folder, and the "
                   "stale-file sweep (_sweep_stale_pools) then looks only there. Nothing is EXPECTED "
                   "in D:/fire or D:/joblib_tmp (a trace of run_fire; adaptation.py only setdefaults "
                   "JOBLIB_TEMP_FOLDER, which the launcher sets first); the --watch D:/fire --watch "
                   "D:/joblib_tmp diff checks it (exit 5 on any change). No run has shown it yet.",
        "shipped_references": {
            "note": "NOT the golden. fire_strict_smoke was run 2026-09-21 23:08 with --arms=base "
                    "(raw, link only; base MAE 0.007763, link 0.004247, 19,181 scored rows), BEFORE "
                    "fire_architecture.py's sentinel fix (file time 2026-09-22 00:27), at BLAS "
                    "16/4. fire_strict/_preds.npz is the full shipped nowcast whose link_corrector "
                    "test MAE is 0.003993 (59,892 rows) -- the reference the plan's fire replay gate "
                    "cites for full width. fire_strict/_preds.npz.bak (picked up by the prefix "
                    "match) holds the pre-sentinel-fix predictions.",
            "files": [entry(p, shipped) for p in refs],
        },
        "gates": ["plan 4.4: fire replay equals its golden (shipped test MAE 0.003993 at full width); "
                  "this smoke is the pinned, byte-level golden for the harness replay (cap800 rows, "
                  "default_rng(7) cells, float16 matrices, seeds SEED*1000+e*17+j / SEED*100+j)",
                  "M4 gate 'Fire replay = golden'"],
        "files": [],
    }


def build_defo(shipped):
    arrays = sorted(p for p in shipped if p.startswith("D:/adaptation/defo/")
                    and p.endswith("_c4000.npz"))
    import numpy as np
    files, rows = [], {}
    for p in arrays:
        z = np.load(p, allow_pickle=False)
        has = "link_corrector" in z.files and "inner_link_corrector" in z.files
        role = "link_corrector cache" if has else "rival cache (no link_corrector key; matched by the glob only)"
        e = entry(p, shipped, role=role)
        b = BACKUP + "/defo/" + os.path.basename(p)
        e["backup"] = entry(b) if os.path.exists(b) else None
        if e["backup"]:
            e["backup"]["matches_original"] = e["backup"]["sha256"] == e["sha256"]
        if has:
            rows[os.path.basename(p)[:-len("_c4000.npz")]] = {
                "test_rows": int(z["y"].shape[0]), "inner_rows": int(z["inner_y"].shape[0]),
                "keys": list(z.files)}
        files.append(e)
    plac = sorted(p for p in shipped if p.startswith("D:/defo_tier2/banks/plac_hist_n250_mf15_c12_"))
    donors = [os.path.basename(p)[len("plac_hist_n250_mf15_c12_"):-len(".pkl")] for p in plac]
    pair = ["D:/defo_corrector/banks/pair_hist_n250_mf15_c12_%s.pkl" % d for d in donors]
    missing = [p for p in pair if p not in shipped]
    return {
        "problem": "defo",
        "what": "The cached link_corrector arrays of the shipped defo nowcast: one npz per test "
                "region (4,000 cells, annual, test 2020-23, inner score 2017-19), keys "
                "link_corrector / inner_link_corrector next to y, inner_y and the other arms.",
        "produced_by": ["adaptation.py run_defo (base, link, corrector, placebo; the shipped file's "
                        "sha256 now is %s)" % sha256_file(os.path.join(PROJECT, "adaptation.py")),
                        "add_linkcorr.py (added link_corrector, inner_link_corrector and link_gate "
                        "IN PLACE; D:/adaptation/defo/_addarm.log; its sha256 now is %s)"
                        % sha256_file(os.path.join(PROJECT, "add_linkcorr.py"))],
        "rerun": "NEVER: run_defo deletes and rebuilds caches (task rule; plan G-NOOVERWRITE)",
        "rows_per_region": rows,
        "backup_folder": BACKUP + "/defo",
        "banks": {
            "note": "the 25 lead-0 donor banks the replay needs (plan 4.4: 'defo's shipped artefact "
                    "banks by sha256'). Donors = the 25 placebo-bank names. sha256 copied from "
                    "shipped.json, not re-hashed by build; `verify --deep` re-hashes them. "
                    "add_linkcorr.py's link_gate also reads D:/defo_overnight/banks (not protected, "
                    "not needed for link_corrector).",
            "donors": donors,
            "missing_from_shipped_json": missing,
            "files": [registry_entry(p, shipped, "pair bank (base + corrector trees)") for p in pair
                      if p in shipped]
                     + [registry_entry(p, shipped, "placebo bank") for p in plac],
        },
        "gates": ["plan 4.4: the engine's region solver on defo's shipped banks equals the cached "
                  "link_corrector arrays, with matching row counts",
                  "M3 gate 'Defo replay = cached link_corrector arrays with matching row counts' "
                  "(part of the Tue 13 Oct kill switch)"],
        "files": files,
    }


def launcher_block():
    """The current launcher and the self-test records made WITH THIS launcher (exit 0, pins held,
    no leak)."""
    lp = os.path.join(HERE, "launch_pinned.py")
    sha = sha256_file(lp)
    recs = []
    for p in sorted(glob.glob(GOLDEN + "/_launcher_selftest*/launcher.json")):
        with open(p, encoding="utf-8") as f:
            lj = json.load(f)
        leak = any(any((lj.get(k) or {}).values()) for k in
                   ("protected_roots_changed", "redirect_sources_changed", "watched_changed"))
        if lj.get("launcher_sha256") == sha and lj.get("exit_code") == 0 \
                and lj.get("pins_ok_at_end") and not leak:
            recs.append({"path": fwd(p), "sha256": sha256_file(p)})
    return {"path": fwd(lp), "sha256": sha,
            "rooted_copy_sha256": sha256_file(os.path.join(HERE, "rooted_copy.py")),
            "selftest_records": recs,
            "selftest_record": recs[-1]["path"] if recs else None,
            "selftest_record_sha256": recs[-1]["sha256"] if recs else None}


def build():
    if os.path.exists(REGISTRY):
        raise SystemExit("goldens.py: %s exists; it is never overwritten (use `next`)." % REGISTRY)
    shipped, shipped_created = load_shipped()
    u2, wide = build_pm25(shipped)
    fire = build_fire(shipped)
    defo = build_defo(shipped)
    reg = {
        "version": 1,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "written_by": fwd(os.path.abspath(__file__)),
        "written_by_sha256": sha256_file(os.path.abspath(__file__)),
        "plan": "APP_PLAN.md 4.4 (legacy harness) and the Day-1 corrections box",
        "shipped_registry": {"path": SHIPPED_JSON, "created": shipped_created,
                             "sha256": sha256_file(SHIPPED_JSON)},
        "launcher": launcher_block(),
        "rules": RULES,
        "goldens": {"pm25_u2_smoke": u2, "pm25_wide_smoke_blas1": wide, "fire_smoke": fire,
                    "defo_link_corrector": defo},
    }
    with open(REGISTRY, "x", encoding="utf-8") as f:
        json.dump(reg, f, indent=1)
    print("wrote %s" % REGISTRY)
    return reg


RULES = ["goldens are read-only references; nothing here is ever re-run into its own folder",
         "new harness outputs go only under %s/" % GOLDEN,
         "a replay passes only against these hashes/arrays at the plan's tolerances",
         "the registry is a write-once series (goldens.json, goldens_v2.json, ...); readers use the "
         "newest version"]


# ------------------------------------------------------------------------------ fire run records

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_fire_record(lj, fire, run_dir):
    """Problems with a fire run's launcher.json (an empty list = a valid golden record), including a
    re-hash of every output it lists."""
    run_dir = absfwd(run_dir)
    problems = []
    if lj.get("exit_code") != 0:
        problems.append("exit code %s" % lj.get("exit_code"))
    if not lj.get("pins_ok_at_end"):
        problems.append("thread pools not at their pins at the end: %s" % lj.get("bad_pools_at_end"))
    for key in ("protected_roots_changed", "redirect_sources_changed", "watched_changed"):
        if any((lj.get(key) or {}).values()):
            problems.append("leak (%s): %s" % (key, lj[key]))
    if "watched_changed" not in lj:
        problems.append("no watched-folder diff (the run used a launcher without --watch)")
    low = [w.lower() for w in lj.get("watch", [])]
    miss_w = [w for w in FIRE_WATCH if w.lower() not in low]
    if miss_w:
        problems.append("not watched: %s" % miss_w)
    lowp = [p.lower() for p in lj.get("redirect_prefixes", [])]
    miss_p = [p for p in FIRE_PREFIXES if p.lower() not in lowp]
    if miss_p:
        problems.append("not redirected: %s" % miss_p)
    if lj.get("argv") != fire.get("argv", FIRE_ARGV):
        problems.append("script arguments %s, expected %s" % (lj.get("argv"), fire.get("argv", FIRE_ARGV)))
    root = (lj.get("env_script") or {}).get("ADAPTATION_OUT_ROOT")
    if not root or absfwd(root).lower() != run_dir.lower():
        problems.append("ADAPTATION_OUT_ROOT %s is not the run folder %s" % (root, run_dir))
    if lj.get("script_sha256") != fire["script_sha256"]:
        problems.append("the run used a different adaptation_rooted.py")
    cp = lj.get("copy_of") or {}
    if cp.get("source_sha256") != fire["source_sha256"]:
        problems.append("the run's adaptation.py sha256 differs from the registered source")
    if not cp.get("ok"):
        problems.append("the run's --copy-of check was not ok")
    if lj.get("scratch_left"):
        problems.append("scratch files were left behind: %s" % lj["scratch_left"])
    outs = {absfwd(o["path"]).lower() for o in lj.get("outputs", [])}
    rel = [r for r in fire.get("outputs_expected_relative", FIRE_EXPECTED_REL) if r != "launcher.json"]
    missing = [r for r in rel if (run_dir + "/" + r).lower() not in outs]
    if missing:
        problems.append("expected outputs missing: %s" % missing)
    stray = [o["path"] for o in lj.get("outputs", []) if not absfwd(o["path"]).lower()
             .startswith(run_dir.lower() + "/")]
    if stray:
        problems.append("outputs outside the run folder: %s" % stray)
    res = []
    _check_files(lj.get("outputs", []), True, res)
    changed = [p for s, p in res if s != "OK"]
    if changed:
        problems.append("outputs changed since the run: %s" % changed)
    return problems


def fire_attempts(golden=GOLDEN):
    """[(folder, record)] of every launcher.json directly under golden/*/ made by a fire run."""
    out = []
    for p in sorted(glob.glob(golden + "/*/launcher.json")):
        try:
            lj = load_json(p)
        except Exception as exc:                     # a broken record is shown, not hidden
            out.append((fwd(os.path.dirname(p)), {"unreadable": repr(exc)}))
            continue
        if os.path.basename(str(lj.get("script", ""))) == "adaptation_rooted.py":
            out.append((fwd(os.path.dirname(p)), lj))
    return out


def _run_dir_arg(d):
    n = absfwd(d)
    if not n.lower().startswith(GOLDEN.lower() + "/"):
        raise SystemExit("goldens.py: --fire-run %s must be a folder under %s/" % (n, GOLDEN))
    return n


# ------------------------------------------------------------------------------------------ next

def build_next(note, fire_run=None, here=HERE):
    """Write the next registry version (write-once). The fire block and the launcher record are
    regenerated; the other goldens are carried over verbatim (verify re-hashes them)."""
    if not note or not note.strip():
        raise SystemExit("goldens.py next: --note is required (say why this version exists)")
    n, prev_path = latest_registry(here)
    dst = os.path.join(here, "goldens_v%d.json" % (n + 1))
    if os.path.exists(dst):
        raise SystemExit("goldens.py: %s exists; it is never overwritten." % dst)
    prev = load_json(prev_path)
    shipped, shipped_created = load_shipped()
    fire = build_fire(shipped)
    changes = [note.strip()]
    if fire_run:
        run_dir = absfwd(fire_run)
        lj_path = run_dir + "/launcher.json"
        if not os.path.exists(lj_path):
            raise SystemExit("goldens.py next: %s does not exist" % lj_path)
        lj = load_json(lj_path)
        problems = check_fire_record(lj, fire, run_dir)
        if problems:
            raise SystemExit("goldens.py next: the fire run %s cannot be folded in:\n  %s"
                             % (run_dir, "\n  ".join(problems)))
        fire.update({
            "status": "CAPTURED -- folded into this registry version",
            "why_pending": None,
            "run_dir": run_dir,
            "launcher_record": entry(lj_path, role="launcher record"),
            "captured": {k: lj.get(k) for k in ("started", "finished", "avail_ram_gb_at_start",
                                                "min_avail_gb", "launcher_sha256", "versions")},
            "hashes_live_in": "this registry version ('files'), option A",
            "files": [entry(o["path"], role="run output") for o in lj["outputs"]]
                     + [entry(lj_path, role="launcher record")],
        })
        fire["ram_threshold"]["decided_by"] = "owner: --min-avail-gb %s used" % lj.get("min_avail_gb")
        changes.append("fire_smoke: run %s folded in (%d files)" % (run_dir, len(fire["files"])))
    pf = prev["goldens"].get("fire_smoke", {})
    diff_keys = sorted(k for k in set(pf) | set(fire) if pf.get(k) != fire.get(k))
    changes.append("fire_smoke regenerated by build_fire; fields that differ from version %d: %s"
                   % (n, diff_keys))
    lb = launcher_block()
    if (prev.get("launcher") or {}).get("sha256") != lb["sha256"]:
        changes.append("launch_pinned.py sha256 %s -> %s; self-test record(s) with the new "
                       "launcher: %s" % ((prev.get("launcher") or {}).get("sha256"), lb["sha256"],
                                         [r["path"] for r in lb["selftest_records"]] or "NONE"))
    me = sha256_file(os.path.abspath(__file__))
    if prev.get("written_by_sha256") != me:
        changes.append("goldens.py sha256 %s -> %s" % (prev.get("written_by_sha256"), me))
    sj = {"path": SHIPPED_JSON, "created": shipped_created, "sha256": sha256_file(SHIPPED_JSON)}
    if (prev.get("shipped_registry") or {}).get("sha256") != sj["sha256"]:
        changes.append("!! shipped.json sha256 changed since version %d" % n)
    carried = [g for g in prev["goldens"] if g != "fire_smoke"]
    reg = {
        "version": n + 1,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "written_by": fwd(os.path.abspath(__file__)),
        "written_by_sha256": me,
        "supersedes": {"version": n, "path": prev_path, "sha256": sha256_file(prev_path)},
        "changes": changes,
        "carried_over": {g: "verbatim from version %d (%s)" % (n, os.path.basename(prev_path))
                         for g in carried},
        "plan": prev.get("plan"),
        "shipped_registry": sj,
        "launcher": lb,
        "rules": RULES,
        "goldens": {g: (fire if g == "fire_smoke" else prev["goldens"][g]) for g in prev["goldens"]},
    }
    with open(dst, "x", encoding="utf-8") as f:
        json.dump(reg, f, indent=1)
    print("wrote %s (version %d)" % (fwd(dst), n + 1))
    for c in changes:
        print("  change: %s" % c)
    return fwd(dst)


# ----------------------------------------------------------------------------------------- verify

def _check_files(files, deep, out):
    for e in files:
        p = e["path"]
        if e.get("sha256_from") == SHIPPED_JSON and not deep:
            ok = os.path.exists(p) and os.path.getsize(p) == e["size"]
            out.append(("SIZE-OK" if ok else "CHANGED/MISSING", p))
            continue
        if not os.path.exists(p):
            out.append(("MISSING", p))
            continue
        ok = sha256_file(p) == e["sha256"] and os.path.getsize(p) == e["size"]
        out.append(("OK" if ok else "CHANGED", p))
        if e.get("backup"):
            _check_files([e["backup"]], deep, out)


def verify(deep=False, registry=None, fire_run=None, here=HERE, golden=GOLDEN):
    if registry is None:
        n, registry = latest_registry(here)
    else:
        n = "given"
    reg = load_json(registry)
    print("registry %s (version %s)" % (fwd(registry), reg.get("version", n)))
    bad = 0
    for gid, g in reg["goldens"].items():
        res = []
        _check_files(g.get("files", []), deep, res)
        _check_files(g.get("shipped_references", {}).get("files", []), deep, res)
        _check_files(g.get("banks", {}).get("files", []), deep, res)
        n_bad = sum(1 for s, _ in res if s not in ("OK", "SIZE-OK"))
        bad += n_bad
        print("%-24s %4d files checked, %d problem(s)%s"
              % (gid, len(res), n_bad, "" if deep or not g.get("banks") else
                 " (bank files size-checked only; --deep re-hashes them)"))
        for s, p in res:
            if s not in ("OK", "SIZE-OK"):
                print("    %s %s" % (s, p))
    fire = reg["goldens"]["fire_smoke"]
    if str(fire.get("status", "")).startswith("CAPTURED"):
        # option A: the outputs were re-hashed above from the registry; re-check the run record too
        if fire_run:
            raise SystemExit("goldens.py verify: this registry already folds in the fire run %s; "
                             "--fire-run applies only to a registry whose fire_smoke is PENDING"
                             % fire["run_dir"])
        problems = check_fire_record(load_json(fire["launcher_record"]["path"]), fire,
                                     fire["run_dir"])
        bad += len(problems)
        print("fire_smoke               FOLDED from %s: %s" % (
            fire["run_dir"], "record OK" if not problems else "PROBLEMS: " + "; ".join(problems)))
        checked = fire["run_dir"]
    else:
        # option B (or not folded yet): the run's own launcher.json holds the hashes
        checked = absfwd(fire_run) if fire_run else FIRE_OUT
        lj_path = checked + "/launcher.json"
        if not os.path.exists(lj_path):
            if fire_run:
                print("fire_smoke               --fire-run %s has no launcher.json" % checked)
                bad += 1
            else:
                print("fire_smoke               PENDING: %s does not exist yet. The RAM threshold "
                      "is the owner's choice (README.md 'RAM threshold'). Commands:\n"
                      "  caution (%.1f GB):\n%s\n  shipped guard (%.1f GB):\n%s"
                      % (lj_path, FIRE_CAUTION_GB, fire_command(min_gb=FIRE_CAUTION_GB),
                         FIRE_SHIPPED_GUARD_GB, fire_command(min_gb=FIRE_SHIPPED_GUARD_GB)))
        else:
            lj = load_json(lj_path)
            problems = check_fire_record(lj, fire, checked)
            bad += len(problems)
            print("fire_smoke               RUN %s (not folded; hashes from its launcher.json), "
                  "finished %s, %d outputs: %s"
                  % (checked, lj.get("finished"), len(lj.get("outputs", [])),
                     "record OK" if not problems else "PROBLEMS: " + "; ".join(problems)))
    others = [(d, lj) for d, lj in fire_attempts(golden) if d.lower() != checked.lower()]
    for d, lj in others:
        print("    other fire attempt (not checked; pass --fire-run to check it): %s exit %s, "
              "finished %s" % (d, lj.get("exit_code"), lj.get("finished")))
    print("VERIFY %s" % ("OK" if not bad else "FAILED (%d problem(s))" % bad))
    return 0 if not bad else 1


def _opts(argv, flags, valued):
    """A tiny exact parser: returns {name: value or True}; refuses anything else."""
    out, i = {}, 0
    while i < len(argv):
        k = argv[i]
        if k in flags:
            out[k] = True
            i += 1
        elif k in valued and i + 1 < len(argv):
            out[k] = argv[i + 1]
            i += 2
        else:
            raise SystemExit(USAGE)
    return out


USAGE = ("usage: py -3.9 goldens.py build\n"
         "       py -3.9 goldens.py next --note TEXT [--fire-run DIR]\n"
         "       py -3.9 goldens.py verify [--deep] [--registry FILE] [--fire-run DIR]")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["build"]:
        build()
        return verify()
    if argv[:1] == ["next"]:
        o = _opts(argv[1:], (), ("--note", "--fire-run"))
        run = _run_dir_arg(o["--fire-run"]) if "--fire-run" in o else None
        build_next(o.get("--note"), fire_run=run)
        return verify()
    if argv[:1] == ["verify"]:
        o = _opts(argv[1:], ("--deep",), ("--registry", "--fire-run"))
        run = _run_dir_arg(o["--fire-run"]) if "--fire-run" in o else None
        return verify(deep=o.get("--deep", False), registry=o.get("--registry"), fire_run=run)
    raise SystemExit(USAGE)


if __name__ == "__main__":
    sys.exit(main())
