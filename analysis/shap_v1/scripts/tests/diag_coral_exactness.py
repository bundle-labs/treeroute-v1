"""Diagnosis of the coral rebuild's last-bit differences (smoke only; writes under smoke/).

(a) the kept GLS arm routed twice in one process: run-to-run identity;
(b) the unweighted corrector arm and the plain arms against their saved columns: do weights cause the difference?
(c) one group's 100 bank trees refitted in this process against the tree fingerprints the earlier process saved
    with its checkpoint: is the bank deterministic across processes on this machine?
"""
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import shapv1_common as C  # noqa: E402

ENG = C.PROBLEMS["coral"]["engine"]
sys.path.insert(0, ENG)
from treeroute import launch  # noqa: E402

launch.pin_threads()
import json  # noqa: E402
import time  # noqa: E402
import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from treeroute.runs.machine import load_machine  # noqa: E402
from treeroute.pipeline.table_run import TablePipeline  # noqa: E402
from treeroute.pipeline.table_passes import TableRunState  # noqa: E402
from treeroute.pipeline.table_router import NeighbourPass, PassPart  # noqa: E402
from treeroute.pipeline import passes as PS  # noqa: E402
from treeroute.pipeline import stages as ST  # noqa: E402
from treeroute.pipeline import record as REC  # noqa: E402
from treeroute.layer import arms as LA  # noqa: E402
from treeroute.layer.links import clip_to_legal  # noqa: E402
from treeroute.fit import bank as B  # noqa: E402

log = C.Log("diag_coral_exactness", os.path.join(C.ROOT, "smoke", "logs"))
REF = C.PROBLEMS["coral"]["run"]
machine = load_machine(os.path.join(C.ROOT, "smoke", "machine_shap_smoke.yaml"))
pipe = TablePipeline(C.package_dir("coral"), machine.run_root, "headline", machine=machine, echo=lambda m: None)
report = {}
try:
    for step in ("_lock", "_load", "_groups", "_preflight_target", "_read", "_derive", "_open", "_temp"):
        getattr(pipe, step)()
    with TableRunState(pipe) as s:
        s.build_pool(need_inner=False)
        s.fit(need_inner=False)
        saved = pq.read_table(os.path.join(REF, "test_preds.parquet")).to_pandas()
        rows_id = np.asarray(s.data.row_ids, dtype=object).astype(str)
        pos = {r: i for i, r in enumerate(rows_id.tolist())}
        keys = np.asarray([pos[u] for u in saved["unit"].astype(str)], np.int64)
        doc = C.read_json(os.path.join(REF, "adoption.json"))
        point = PS._point_doc(doc["penalty"])

        def route(arm):
            part = PassPart(name="all", score_index=np.arange(keys.size), c=s.c, model=s.weights,
                            fallback_donor=s.donor_fit)
            npass = NeighbourPass(s, REC.S1_TEST_PASS, s.ctx_fit, s.store_fit, s.bank_fit.tree_group, 0,
                                  s.data.leads[0], keys, [part], s.tol)
            r = npass.route([arm], point)
            pre = ST.inverse(r.predictions[LA.arm_name(arm)][:, 0], arm.link, s.c, s.ub)
            return np.asarray(pre, np.float64)
        arms = {}
        for tool in (LA.Tool.CORRECTOR, LA.Tool.PLAIN):
            for w in (LA.Weighting.GLS, LA.Weighting.UNWEIGHTED):
                for link in s.links:
                    arms[LA.arm_name(LA.ArmSpec(link, tool, w, True))] = LA.ArmSpec(link, tool, w, True)
        t0 = time.time()
        first = None
        for name in ["arcsine_corrector_gls", "arcsine_corrector_unweighted", "arcsine_plain_unweighted",
                     "identity_plain_unweighted", "identity_corrector_gls", "log_c_plain_unweighted"]:
            pre = route(arms[name])
            ref = saved["pre__" + name].to_numpy(np.float64)
            report[name] = {"bit_equal": int((pre == ref).sum()), "rows": int(ref.size),
                            "max_abs": float(np.abs(pre - ref).max())}
            log("%s: %d of %d bit-equal, max |diff| %.3g" % (name, report[name]["bit_equal"], ref.size,
                                                             report[name]["max_abs"]))
            if first is None:
                first = pre
        again = route(arms["arcsine_corrector_gls"])
        report["gls_twice_identical"] = bool(np.array_equal(first, again))
        log("GLS arm routed twice in one process: identical %s (%.1f s for all routes)"
            % (report["gls_twice_identical"], time.time() - t0))
        # (c) one group's trees refitted here against the checkpoint's saved fingerprints
        ck = [d for d in os.listdir(os.path.join(machine.run_root, "coral", "_checkpoints")) if d.startswith("bank-")]
        folder = os.path.join(machine.run_root, "coral", "_checkpoints", sorted(ck)[0])
        sides = sorted(f for f in os.listdir(folder) if f.endswith(".json"))
        meta = C.read_json(os.path.join(folder, sides[0]))
        g = meta["meta"]["group"]
        idx = [i for i, gg in enumerate(s.bank_fit.tree_group) if gg == g]
        prints_now = [[B.tree_fingerprint(s.bank_fit.trees[i]), B.tree_fingerprint(s.bank_fit.correctors[i]),
                       B.tree_fingerprint(s.bank_fit.placebo_correctors[i])] for i in idx]
        report["checkpoint_vs_loaded_group"] = prints_now == meta["meta"]["tree_fingerprints"]
        d = s.donor_fit
        rows_g = np.flatnonzero(np.asarray(d.groups_of_rows if hasattr(d, "groups_of_rows") else
                                           [s.unit_group[str(u)] for u in d.unit_ids], dtype=object) == g)
        X = np.asarray(d.X)[rows_g]
        y = np.asarray(d.y, np.float64)[rows_g]
        refit = []
        for j in range(len(idx)):
            bag = B.draw_bag(rows_g.size, B.name_seed(g, j, B.SeedRole.BAG))
            t = B.fit_one_tree(X, y, bag, B.name_seed(g, j, B.SeedRole.TREE))
            refit.append(B.tree_fingerprint(t))
        same = sum(int(a == b[0]) for a, b in zip(refit, meta["meta"]["tree_fingerprints"]))
        report["group"] = g
        report["refit_trees_equal_to_checkpoint"] = [same, len(refit)]
        log("group %s: %d of %d trees refitted in this process equal the earlier process's fingerprints"
            % (g, same, len(refit)))
finally:
    pipe._release()
C.write_json(os.path.join(C.ROOT, "smoke", "diag_coral_exactness.json"), report)
