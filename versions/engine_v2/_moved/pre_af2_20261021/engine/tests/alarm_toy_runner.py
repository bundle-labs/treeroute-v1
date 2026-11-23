"""Runs ONE toy package through a GIVEN engine copy in a fresh interpreter (a helper of tests/test_pipeline_alarm.py
and tests/test_table_mode_alarm.py, not a test). Used to compare the engine v2 run of a toy with the frozen engine v1
copy's run of the same toy, byte for byte (owner ruling AE: when the alarm never switches, every v1 output stays the
same), in identical child processes.

It imports NOTHING from tests/ (tests/conftest.py would put the v2 engine first on sys.path): the engine folder given
is put first on sys.path, sklearn is patched (owner ruling C, as the tests do), and run_pipeline runs with a fake
launch record. It prints one JSON line: the run folder, the engine file it imported and its engine_code_sha256.

Modes (the same code for both engines, so a forced v1 run and a forced v2 run differ only by the engine):
  normal   the run as it is;
  forced   decide()'s select_adoption is wrapped so the nowcast adopts the best GLS-weighted corrector (its twin, the
           unweighted corrector, stays in the eligible list; when no GLS corrector passes N2, every reference MAE is
           raised first so every arm is eligible), and every lead's guard passes (forecast_adoption sees a
           trees-off MAE above the pinned arm's); with --alarm-switch-all (an engine that has the alarm) the A8
           threshold is 0 and the minimum batch 1, and a lead's twin is always eligible, so every batch with a gap
           takes the twin.
--spy FILE (an engine with the alarm): records, at each open_test_labels call, whether that pass's alarm lock existed.
"""

import argparse
import json
import os
import sys
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--registry", required=True)
    ap.add_argument("--mode", default="normal", choices=("normal", "forced"))
    ap.add_argument("--alarm-switch-all", action="store_true")
    ap.add_argument("--spy", default=None)
    ns = ap.parse_args()
    sys.path.insert(0, ns.engine)
    import sklearnex

    sklearnex.patch_sklearn(verbose=False)
    import treeroute
    from treeroute.runs.fingerprint import engine_code_sha256

    if not os.path.abspath(treeroute.__file__).startswith(os.path.abspath(ns.engine)):
        raise SystemExit("imported %s, not the engine at %s" % (treeroute.__file__, ns.engine))
    if ns.mode == "forced":
        _force(ns.alarm_switch_all)
    if ns.spy:
        _spy(ns.spy)
    from types import SimpleNamespace

    from treeroute.pipeline.run import run_pipeline

    base = os.path.abspath(ns.base)
    os.makedirs(os.path.join(base, "temp"), exist_ok=True)
    machine = SimpleNamespace(run_root=os.path.join(base, "runs"), temp_dir=os.path.join(base, "temp"),
                              registry_dir=ns.registry)
    launch = {"test_only": True, "env_pins": {"OMP_NUM_THREADS": "4"},
              "backend": {"sklearn_patched": True, "onedal_threads": 4}}
    folder = run_pipeline(ns.pkg, os.path.join(base, "runs"), "smoke", machine=machine, echo=lambda s: None,
                          launch_record=launch)
    print("RESULT " + json.dumps({"folder": str(folder), "treeroute": treeroute.__file__,
                                  "engine_code_sha256": engine_code_sha256()}))


def _force(switch_all):
    import dataclasses

    from treeroute.layer import arms as LA
    from treeroute.layer import decide as LD

    orig = LD.select_adoption

    def forced(picks, trees_off_mae, beside, **kw):
        full = orig(picks, trees_off_mae, beside, **kw)
        if not any(p.arm.tool is LA.Tool.CORRECTOR and p.arm.weighting is LA.Weighting.GLS and p.arm in full.eligible
                   for p in picks):
            # a toy whose GLS corrector fails N2: every reference is raised so every arm is eligible (forced toy only)
            trees_off_mae = {k: 1e30 for k in trees_off_mae}
            if kw.get("baseline") is not None:
                kw = dict(kw, baseline=(kw["baseline"][0], 1e30))
            full = orig(picks, trees_off_mae, beside, **kw)
        gls = tuple(p for p in picks if p.arm.tool is LA.Tool.CORRECTOR and p.arm.weighting is LA.Weighting.GLS
                    and p.arm in full.eligible)
        if not gls:
            raise SystemExit("forced mode: no eligible GLS corrector to adopt")
        best = orig(gls, trees_off_mae, beside, **kw)
        return dataclasses.replace(full, adopted=best.adopted, penalty=best.penalty, declined=False,
                                   best_tree_arm=best.adopted, best_tree_penalty=best.penalty)
    LD.select_adoption = forced
    orig_fa = LD.forecast_adoption

    def passes(nowcast, lead, pinned_mae, off_mae, longest):
        return orig_fa(nowcast, lead, pinned_mae, max(float(off_mae), float(pinned_mae) + 1.0), longest)
    LD.forecast_adoption = passes
    if switch_all:
        from treeroute import engine_constants as K
        from treeroute.layer import alarm as LAL

        K.ALARM_RATIO_THRESHOLD = 0.0
        K.ALARM_MIN_BATCH_ROWS = 1
        LAL.twin_eligible_lead = lambda twin_mae, base_mae: True


def _spy(path):
    from treeroute.labels import vault as V

    orig = V.LabelView.open_test_labels
    events = []

    def spied(self, adoption_sha256, lead, *, alarm_sha256):
        folder = self.run_folder
        lock = folder / ((V.ALARM_FILE % int(lead)) + V.ALARM_LOCK_SUFFIX)
        preds = None
        if lock.is_file():
            doc = json.loads((folder / (V.ALARM_FILE % int(lead))).read_text(encoding="utf-8"))
            preds = doc.get("alarm_preds_file")
        events.append({"lead": int(lead), "at": time.time(), "alarm_lock_exists": lock.is_file(),
                       "alarm_preds_exists": bool(preds) and (folder / preds).is_file(),
                       "marker_existed": (folder / (V.OPENED_FILE % int(lead))).is_file()})
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(events, fh)
        return orig(self, adoption_sha256, lead, alarm_sha256=alarm_sha256)
    V.LabelView.open_test_labels = spied


if __name__ == "__main__":
    main()
