"""Builds D:/treeroute/analysis/paper_posthoc/SPEC.json (the computation spec for the AK3/AK4 post-hoc Part).
Reads only _probe/inputs_sha256.txt (hashes taken 2026-10-26) and writes SPEC.json. No engine, run or paper file is touched."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "SPEC.json")

SHA = {}
with open(os.path.join(HERE, "inputs_sha256.txt"), encoding="utf-8") as fh:
    for line in fh:
        h, p = line.strip().split(" ", 1)
        SHA[p.lstrip("*")] = h

RUN = {
    "pm25": "D:/treeroute/runs/pm25/headline/20261007_74e67609",
    "ndvi": "D:/treeroute/runs/ndvi/headline/20261016_d1de3158",
    "fire": "D:/treeroute/runs/fire/headline/20261017_869d1f38",
    "defo": "D:/treeroute/runs/defo/headline/20261017_d71c61f4",
    "coral": "D:/treeroute/runs/coral/headline/20261020_f3b8e3da",
}
HT = "D:/treeroute/runs/_headline_tables"
HEAD = {"pm25": HT + "/headline_93b64854d1f9.csv", "ndvi": HT + "/ndvi/headline_9e5590eab94b.csv",
        "fire": HT + "/fire/headline_85a9134089e4.csv", "defo": HT + "/defo/headline_1571da960aa6.csv",
        "coral": HT + "/coral/headline_344838cf7de1.csv"}
VERD = {"pm25": HT + "/verdicts_9abcea419ce2.csv", "ndvi": HT + "/ndvi/verdicts_c4cd7e7c2610.csv",
        "fire": HT + "/fire/verdicts_7ee7167afe8d.csv", "defo": HT + "/defo/verdicts_bf99c6741bce.csv",
        "coral": HT + "/coral/verdicts_a9d948cbf26b.csv"}
BOARD = {"pm25": "D:/treeroute/rivals/pm25/20261007_74e67609", "ndvi": "D:/treeroute/rivals/ndvi/20261016_d1de3158",
         "fire": "D:/treeroute/rivals/fire/20261017_869d1f38", "defo": "D:/treeroute/rivals/defo/20261017_d71c61f4",
         "coral": "D:/treeroute/rivals/coral/20261020_f3b8e3da"}
HBOARD = {"pm25": "D:/treeroute/rivals_human/pm25/20261007_74e67609",
          "ndvi": "D:/treeroute/rivals_human/ndvi/20261016_d1de3158",
          "defo": "D:/treeroute/rivals_human/defo/20261017_d71c61f4",
          "coral": "D:/treeroute/rivals_human/coral/20261020_f3b8e3da"}
LEADS = {"pm25": [0, 6, 12], "ndvi": [0, 6, 12], "fire": [0, 6, 12], "defo": [0, 1], "coral": [0, 183, 365]}
RIVALS_TABLE = "D:/treeroute/rivals_table/20261025T162302876402Z/RIVALS_TABLE.csv"
MAG_EDGES = HT + "/coral/coral_report/magnitude_edges.csv"
MAG_BINS = HT + "/coral/coral_report/magnitude_bins.csv"
ENG = "C:/Users/<user>/Desktop/data set for reserch paper/engine"


def inp(path, cols=None):
    h = SHA.get(path)
    if h is None:
        raise SystemExit("no hash recorded for " + path)
    s = "%s [sha256 %s]" % (path, h[:16])
    if cols:
        s += " columns: " + ", ".join(cols)
    return s


TP = "test_preds.parquet"
PKGS = ["pm25", "ndvi", "fire", "defo", "coral"]

common = {
    "status": "SPEC for the ONE post-hoc Part ruled by AK3/AK4 (engine/OWNER_RULINGS_2026-10-06.md section AK). "
              "Every number it defines is POST HOC: computed after each run's test labels were opened (P17). "
              "None of them changes a locked verdict (wording per AK2: 'locked before test labels were opened', "
              "not 'pre-registered').",
    "written": "2026-10-26",
    "write_scope": "Only D:/treeroute/analysis/paper_posthoc (this file, _probe/, and later the script and its out/). "
                   "Engine files, run outputs, boards, rival tables, the paper folder and memory are read-only. "
                   "Nothing is deleted.",
    "compute": "py -3.9 -I -B (Python 3.9.13); numpy 2.0.2, pandas 2.3.3, pyarrow 21.0.0, scipy 1.13.1 (scipy only for "
               "the t and normal quantiles / p-values in P29). Read only the listed columns (pq.read_table(columns=...)). "
               "Largest table: defo test_preds 369,096 rows. No heavy job, no re-fit, no re-routing, no engine import "
               "(importing would write __pycache__ into the read-only engine folder); the formulas below are "
               "re-implemented and PROVEN equal to the engine by the equality checks.",
    "rows": "Every run's test_preds.parquet holds lead 0 only (asserted: lead == 0 on every row). 'Labelled rows' = rows "
            "with finite y. pm25 91,440 saved / 91,428 labelled / 1,905 units / 127 groups / years 2020-2023; ndvi "
            "95,184 / 94,527 / 1,983 / 133 / 2020-2023; fire 96,000 / 94,702 / 2,000 / 40 / 2019-2022; defo 369,096 / "
            "369,096 / 92,274 / 42 / 2020-2023; coral 2,312 / 2,312 / 2,312 visits / 37 scored groups / 2016-2019.",
    "definitions": {
        "MAE": "mean |y - p| over the rows where y and p are both finite (engine report/metrics.py mae(), score_table()). "
               "arm__* and placebo__* columns are the post-clip predictions that the engine scores; pre__* columns are "
               "pre-clip and are never scored.",
        "per_group_MAE": "the same MAE over one group's labelled rows; groups in sorted order (score_table by=('group',)).",
        "paired_contrast": "d_g = MAE_reference(g) - MAE_arm(g) for our own contrasts (positive = arm better; "
                           "metrics._paired_contrast, single_verdict); for rivals d_g = MAE_rival(g) - MAE_ours(g) "
                           "(positive = ours better; rivals_build/rivals/harness.py score() lines 2494-2513).",
        "group_jackknife": "region (group) jackknife, metrics.group_jackknife: mean = mean_g d_g; leave-one-group-out "
                           "means m_i; SE = sqrt((G-1)/G * sum_i (m_i - mean(m))^2); CI = mean +- 1.96*SE with "
                           "JACKKNIFE_Z = 1.96 exactly (engine_constants.py S2.jackknife_z). G < 3: SE and CI NaN.",
        "tag_rule": "metrics.contrast_tag (D74): IDENTICAL if every |d_g| <= 1e-12 (IDENTICAL_ATOL); CANNOT TELL if the "
                    "CI is undefined; EQUIVALENT if -band <= low and high <= band; HELPS if low > 0 and mean >= band; "
                    "HURTS if high < 0 and mean <= -band; otherwise CANNOT TELL. Engine strings: helps, hurts, "
                    "does_not_help_equivalent, cannot_tell, identical, declined. Boards read HELPS/HURTS as BEATS/LOSES.",
        "band": "each run's nowcast band = verdict.json 'band' (R35/D75: median jackknife SE of the run's own non-identical "
                "D75 pairs; metrics.band_from_pairs/equivalence_band): pm25 0.04621194666, ndvi 0.0005974707756, "
                "fire 1.356697052e-05, defo 0.0001104494048, coral 0.9175581931. Used unchanged for every "
                "report-only tag below.",
        "guess_normal": "base__guess_normal = clip(normal, legal range) (metrics.baseline_guess_normal); predict-zero = "
                        "base__predict_zero (metrics.baseline_predict_zero); coral's normal-free reference = "
                        "base__donor_median (metrics.baseline_donor_median).",
        "blocked_jackknife": "report-only: metrics.blocked_jackknife on the overlap blocks of per_group.csv "
                             "'overlap_block' (one block per distinct value).",
        "join_rival_rows": "rival rows join our saved rows on (unit, time, lead), one-to-one, exactly as "
                           "harness._frame_for_scoring (lines 2363-2388); 'ours' = the run's headline column at lead 0 "
                           "(the adopted arm); 'rival' = arm__rival_<L> (guarded, the deciding column; equal to "
                           "arm__rival_<L>_raw where guard_passed is True). Row count after the join must equal the "
                           "saved row count.",
        "anomaly_r2": "1 - sum((y-n)-(p-n))^2 / sum((y-n)^2) with n = the saved 'normal' column (metrics.anomaly_r2; "
                      "NaN without a normal, i.e. coral).",
        "hit_rate": "share of rows with |y - p| <= tol, tol = verdict.json hit_tolerance (metrics.hit_rate; R32); "
                    "hit_floor uses verdict.json measurement_error_floor where it is not null (pm25 2.0, ndvi 0.02).",
    },
    "check_protocol": [
        "Hash every input at start; each sha256 must start with the 16-hex prefix recorded in this spec, else stop.",
        "Every recomputed quantity that the engine or a harness also wrote is asserted equal with "
        "numpy.isclose(rtol=1e-12, atol=0) (the tolerance of harness.check_ours_against_run, lines 2424-2459): "
        "pooled lines against score_pooled.csv (rows_basis 'all', line 'pooled'), per-group lines against "
        "score_by_group.csv (rows_basis 'all', line 'key'), contrasts against jackknife.csv / verdicts CSVs / board "
        "CSVs, coral bins against coral_report/magnitude_bins.csv. Any mismatch stops the script (fail loud).",
        "Where this spec quotes a probe value, the script's value must match it to the printed digits; a difference is "
        "reported, never silently replaced.",
        "No seed, no bootstrap: the only uncertainty is the region (group) jackknife; blocked jackknife report-only.",
        "Every output row carries: item ID, population (rows, groups, leads, years), source files with sha256 prefix, "
        "formula id, and the label 'post hoc'.",
    ],
    "engine_code_identity": "Code paths cite the project engine copy " + ENG + "/treeroute. Its comment-stripped code "
                            "hashes (treeroute/runs/fingerprint.py module_code_hash, computed 2026-10-26) equal the run "
                            "manifests: report/metrics.py 6c9234a6 (all five runs), route/region.py f4fd6751 (defo, coral "
                            "manifests), route/neighbour.py 3e2745b6 (coral), route/kinds.py 3741a0a2 (coral). PM2.5, "
                            "NDVI, fire and defo ran route/kinds.py ab16d168; a copy with that hash is "
                            "D:/treeroute/install_20261015/engine_old/treeroute/route/kinds.py, and its point_penalties "
                            "has the same formula.",
    "probe": "Light probes during spec writing (read-only; scripts in _probe/probe_defs.py, probe2.py, probe3.py) "
             "fixed the ambiguous definitions. Probe values are quoted per item; the checked script is authoritative.",
    "key_findings_for_the_owner": [
        "Most 'provisional' pooled numbers (M34, R12 pooled, R13 pooled, R15, R3b fire cell) are ALREADY written by the "
        "engine in each run's frozen score_pooled.csv / score_by_group.csv. The Part can cite those files as the "
        "source; the script's recomputation from test_preds.parquet is the check.",
        "RC12's provisional wording 'L1 wins on every bleached stratum' is NOT reproduced: on the engine's own coral "
        "magnitude bins ours has the lower MAE in B1-B3 and hgb_l1 wins only B4 (> 23.96%) and the severe y >= 50 "
        "stratum (38.66 vs 53.13). The Part must replace that wording.",
        "M34 lists PM2.5, NDVI and defo but fire also has an identity link (trees-off 0.006258758 vs guess-normal "
        "0.006258758); trees-off and guess-normal are equal to ~1e-10 in pooled MAE, not bit-identical (max row "
        "difference 8.1e-07 on fire, inside the run's 9e-07 identity tolerance).",
        "A1's top 1% is y >= numpy.quantile(y of all 94,702 labelled fire rows, 0.99) = 0.102941, giving 949 rows in "
        "31 regions (a strict '>' gives 938). The threshold is taken from TEST labels (outcome-defined).",
        "P29 is reproduced: of 79 deciding verdict rows (14 ours + 65 rival), only fire nowcast and coral CRW 183 d "
        "change under t(G-1).",
    ],
    "dependents": "N6, N20, N21 and N25 rest on R12, R13, R15 and P29; they change only if those numbers change.",
    "planned_outputs": "D:/treeroute/analysis/paper_posthoc/posthoc_facts.py (one script) writing "
                       "D:/treeroute/analysis/paper_posthoc/out/<ID>.csv, out/RESULT.json, out/inputs_sha256.txt and "
                       "out/run.log; logged as ONE post-hoc Part (the next free number in engine/PENDING_PARTS.md; "
                       "the last on 2026-10-26 is Part 621 with addenda).",
}

items = []

# ------------------------------------------------------------------ M34
items.append({
    "id": "M34",
    "what": "Climatology identity on the saved test rows: for every run with an identity link, the pooled test MAE "
            "of the identity-link trees-off arm against the guess-normal baseline, their exact difference, the largest "
            "per-row difference, and the trees-off anomaly R2.",
    "population": "Lead 0 (nowcast), labelled rows: pm25 91,428 rows / 1,905 units / 127 groups / 2020-2023; ndvi "
                  "94,527 / 1,983 / 133 / 2020-2023; fire 94,702 / 2,000 / 40 / 2019-2022; defo 369,096 / 92,274 / "
                  "42 / 2020-2023. The per-row maximum is over every saved row (pm25 91,440, ndvi 95,184, fire 96,000, "
                  "defo 369,096). Coral is excluded (neighbour kind: no normal, no guess-normal).",
    "inputs": [inp(RUN[p] + "/" + TP, ["y", "normal", "legal_min", "legal_max", "arm__identity_trees_off_unweighted",
                                         "base__guess_normal"]) for p in PKGS[:4]]
              + [inp(RUN[p] + "/score_pooled.csv") for p in PKGS[:4]]
              + [inp(RUN[p] + "/verdict.json", ["tolerances"]) for p in PKGS[:4]]
              + [inp(HEAD["ndvi"])],
    "formula": "TO = arm__identity_trees_off_unweighted, GN = base__guess_normal. MAE_TO = mean|y - TO| and MAE_GN = "
               "mean|y - GN| over labelled rows; diff = MAE_TO - MAE_GN; rel = diff / MAE_GN; maxdev = max over all "
               "saved rows of |TO - GN|; assert GN == clip(normal, legal_min, legal_max) exactly; anomaly R2 of TO = "
               "1 - sum((y-normal)-(TO-normal))^2 / sum((y-normal)^2). Compare maxdev with the run's identity "
               "tolerance verdict.json tolerances.tolerance.identity (pm25 1e-06, ndvi/fire/defo 9e-07; ruling O4: "
               "max(k*s, 9e-07), k = 5.230771281733543e-08). Check MAE_TO, MAE_GN and anomaly R2 against "
               "score_pooled.csv (rtol 1e-12). Print MAEs to 6 significant digits AND the exact diff.",
    "fact_sheet_values": "M34 (provisional): identity-link trees-off MAE equals guess-normal MAE 'to every printed "
                         "digit': PM2.5 4.03161, NDVI 0.0394141, defo 0.00840486; NDVI trees-off anomaly R2 1.45e-09. "
                         "Engine score_pooled.csv (frozen) already holds: pm25 TO 4.031610558456933 vs GN "
                         "4.031610558674801; ndvi 0.039414114188559106 vs 0.03941411443328163; fire "
                         "0.006258758011328549 vs 0.006258757880478231; defo 0.008404857347564031 vs "
                         "0.008404857347226244; TO anomaly R2 5.16e-11 / 1.45e-09 / 5.52e-09 / 2.02e-10. Probe: maxdev "
                         "4.1e-09 / 1.76e-07 / 8.09e-07 / 4.76e-09; GN == clip(normal) exactly in all four. Fire is "
                         "missing from M34 and should be added; wording should say 'equal within 1e-8 relative', not "
                         "identical.",
    "engine_definition_source": ENG + "/treeroute/report/metrics.py: mae() line 569, anomaly_r2() 580, "
                                "baseline_guess_normal() 348, score_table() 846; route/kinds.py _trees_off_checked() "
                                "605-625 (R16: trees-off must stay within the R36 tolerance of the normal on every "
                                "score row, link space); pipeline/passes.py report() 1049-1065 writes score_pooled.csv; "
                                "verdict.json 'tolerances' (ruling O4); APP_PLAN.md R16, R36.",
})

# ------------------------------------------------------------------ R12
fire_cols = ["y", "group", "arm__log_c_trees_off_unweighted", "base__predict_zero", "arm__log_c_plain_unweighted",
             "arm__log_c_plain_gls", "arm__log_c_corrector_unweighted", "arm__log_c_corrector_gls",
             "arm__arcsine_corrector_gls", "arm__arcsine_trees_off_unweighted", "arm__identity_trees_off_unweighted",
             "base__guess_normal"]
items.append({
    "id": "R12",
    "what": "The pooled-MAE part of R12: on fire at the nowcast, the ordering of the geometric normal (log trees-off), "
            "predict-zero, the four log tree arms, the adopted arcsine corrector GLS, the arcsine trees-off and the "
            "identity normal (decline target). Beside it (new, report-only): the per-region paired contrast of the "
            "adopted arm against the log trees-off and against predict-zero.",
    "population": "Fire, lead 0, labelled rows: 94,702 cell-months (1,298 unlabelled saved rows excluded), 2,000 "
                  "units, 40 groups, test years 2019-2022. Contrasts over the 40 groups.",
    "inputs": [inp(RUN["fire"] + "/" + TP, fire_cols), inp(RUN["fire"] + "/score_pooled.csv"),
               inp(RUN["fire"] + "/score_by_group.csv"), inp(RUN["fire"] + "/jackknife.csv"),
               inp(RUN["fire"] + "/verdict.json", ["band"]), inp(RUN["fire"] + "/adoption.json")],
    "formula": "Pooled MAE of each listed column over the labelled rows, sorted ascending (check vs score_pooled.csv, "
               "rtol 1e-12). Report-only contrasts: d_g = MAE_ref(g) - MAE_adopted(g) with ref = "
               "arm__log_c_trees_off_unweighted and, separately, ref = base__predict_zero (positive = adopted better); "
               "per-group MAE recomputed and checked against score_by_group.csv; group jackknife (1.96); tag with the "
               "fire band 1.356697052e-05. The final part of R12 (adoption.json surface MAEs, jackknife.csv band-pair "
               "tags of the log arms) is re-read, not recomputed, and the jackknife.csv log-arm rows are re-derived "
               "from score_by_group.csv as a check.",
    "fact_sheet_values": "R12 provisional: log trees-off 0.004281 < predict-zero 0.004284 < log tree arms "
                         "0.004296-0.004322 < adopted 0.004385 < arcsine trees-off 0.004428 < identity normal 0.006259. "
                         "Frozen score_pooled.csv already holds: log TO 0.004281302312816825; PZ 0.004284114619241937; "
                         "log corrector GLS 0.0042957948726572255, log plain GLS 0.004296987722157366, log corrector "
                         "unweighted 0.004320857403502066, log plain unweighted 0.004322425347543649; adopted "
                         "0.004385064558301006; arcsine TO 0.00442826356638935; identity TO 0.006258758011328549 "
                         "(GN 0.006258757880478231). Final part (jackknife.csv): log plain/corrector unweighted HURT "
                         "-4.19e-05 [-6.88e-05, -1.50e-05] / -4.03e-05 [-6.66e-05, -1.40e-05]; GLS CANNOT TELL. The two "
                         "new report-only contrasts are not in the fact sheet yet.",
    "engine_definition_source": ENG + "/treeroute/report/metrics.py score_table() 846, metric_by_key() 999, "
                                "_paired_contrast() 1123, group_jackknife() 1032, contrast_tag() 1097; "
                                "pipeline/passes.py report() 1080-1131 (D75 pairs, single verdict, jackknife.csv); "
                                "layer/decide.py (guard and adoption; M43-M45).",
})

# ------------------------------------------------------------------ R13
r13_cols = {"pm25": "log_c / unweighted (adopted corrector)", "ndvi": "identity / unweighted (adopted arm is plain)",
            "fire": "arcsine / gls (adopted)", "defo": "log_c / unweighted (adopted)", "coral": "arcsine / gls (adopted)"}
items.append({
    "id": "R13",
    "what": "The pooled-MAE table of R13: for the adopted link and weighting of each run, the pooled test MAE of the "
            "corrector arm, its placebo and the plain arm; beside it every other link x weighting triple. Also "
            "re-derive the final placebo band-pair contrasts and tags of jackknife.csv from score_by_group.csv.",
    "population": "Lead 0 labelled rows of each run (pm25 91,428 / 127 groups; ndvi 94,527 / 133; fire 94,702 / 40; "
                  "defo 369,096 / 42; coral 2,312 / 37). Triples used: " + "; ".join("%s %s" % (k, v) for k, v in r13_cols.items()) + ".",
    "inputs": [inp(RUN[p] + "/" + TP, ["y", "group", "arm__<link>_corrector_<w>", "placebo__<link>_placebo_corrector_<w>",
                                         "arm__<link>_plain_<w>"]) for p in PKGS]
              + [inp(RUN[p] + "/score_pooled.csv") for p in PKGS]
              + [inp(RUN[p] + "/score_by_group.csv") for p in PKGS]
              + [inp(RUN[p] + "/jackknife.csv") for p in PKGS],
    "formula": "Pooled MAE per column over labelled rows (check vs score_pooled.csv). For every placebo__ row of "
               "jackknife.csv (kind band_pair): d_g = MAE_placebo(g) - MAE_corrector(g) from score_by_group.csv, group "
               "jackknife (1.96), tag with the run's band; assert mean, se, low, high and tag equal jackknife.csv "
               "(rtol 1e-12). Report corrector - placebo and corrector - plain pooled differences.",
    "fact_sheet_values": "R13 supplementary (provisional): fire corrector 0.004385 / placebo 0.004383 / plain 0.004386; "
                         "defo 0.0054158 / 0.0054195 / 0.0054164; PM2.5 3.58809 / 3.59157 / 3.59645; NDVI 0.0314975 / "
                         "0.0316536 / 0.0314606 (adopted plain); coral (GLS) 6.698 / 6.732 / 6.736. Frozen "
                         "score_pooled.csv agrees: fire 0.004385064558 / 0.004383043171 / 0.004385670290; defo "
                         "0.005415798422 / 0.005419502142 / 0.005416406367; pm25 3.588091134 / 3.591572881 / "
                         "3.596454184; ndvi 0.03149747357 / 0.03165363992 / 0.03146059686; coral 6.697989245 / "
                         "6.731545728 / 6.735936796. Final part (jackknife.csv): every corrector-vs-placebo pair "
                         "does_not_help_equivalent except defo identity unweighted (cannot_tell) and fire's two identity "
                         "pairs (hurts).",
    "engine_definition_source": ENG + "/treeroute/pipeline/passes.py report() 1087-1101 (D75 pairs: each tree arm vs "
                                "its trees-off, each corrector vs its placebo) and pipeline/table_passes.py 574-642 "
                                "(coral, table option); report/metrics.py band_from_pairs() 1195, group_jackknife() "
                                "1032, contrast_tag() 1097; layer/arms.py (placebo never selectable, R24).",
})

# ------------------------------------------------------------------ R14
items.append({
    "id": "R14",
    "what": "Implied absolute penalties of each run's adopted grid point (the same point is pinned at every kept lead, "
            "M47): (a_tree, a_ctx) for the per-unit and neighbour kinds, lambda for the region kind.",
    "population": "One adopted point per run at lead 0: pm25 level 30 ratio 1.0 (per_unit); ndvi level 1 ratio 0.0625 "
                  "(per_unit); fire level 100 ratio 1.0 (per_unit); defo level 0.1 ratio null (region); coral level "
                  "100 ratio 1.0 (neighbour). No rows.",
    "inputs": [inp(RUN[p] + "/adoption.json", ["penalty", "best_tree_penalty", "adopted", "declined"]) for p in PKGS]
              + [inp(RUN[p] + "/derived.json", ["R14.kind", "R14.centre", "R14.grid"]) for p in PKGS],
    "formula": "Read kind and centre from derived.json R14 and (level, ratio) from adoption.json 'penalty'; assert "
               "penalty == best_tree_penalty, declined is false, and the point is in derived R14 'grid'. per_unit: "
               "a_tree = centre[0] * level; a_ctx = a_tree * ratio (0.0 when ratio is null). neighbour: the same with "
               "the neighbour centre (derived centre[0]). region: lambda = centre[0] * level. Note: the context centre "
               "(derived centre[1] = 0.25) is NOT used by point_penalties; a_ctx scales a_tree by the ratio.",
    "fact_sheet_values": "R14 (provisional): PM2.5 a_tree 15 / a_ctx 15; NDVI 0.5 / 0.03125; fire 50 / 50; defo lambda "
                         "10; coral 50 / 50. derived.json centres: per_unit [0.5, 0.25] (pm25, ndvi, fire), region "
                         "[100.0] (defo), neighbour [0.5, 0.25] (coral); so the expected values are 0.5*30 = 15, "
                         "15*1.0 = 15; 0.5*1 = 0.5, 0.5*0.0625 = 0.03125; 0.5*100 = 50, 50; 100*0.1 = 10; 0.5*100 = 50, "
                         "50.",
    "engine_definition_source": ENG + "/treeroute/route/kinds.py point_penalties() 365-375 (frozen ab16d168 copy "
                                "D:/treeroute/install_20261015/engine_old/treeroute/route/kinds.py has the same "
                                "formula); route/region.py region_lambda() 168-175; route/neighbour.py "
                                "neighbour_point_penalties() 235-246; engine_constants.py C12 lines 182-190 "
                                "(PER_UNIT_TREES_CENTRE 0.5, PER_UNIT_CONTEXT_CENTRE 0.25, NEIGHBOUR_TREES_CENTRE 0.5, "
                                "REGION_LAMBDA_CENTRE 100); layer/decide.py penalty_search() 235.",
})

# ------------------------------------------------------------------ R15
items.append({
    "id": "R15",
    "what": "AK4(a) cheap ablation table: every saved column at the nowcast (all arm__ arms including each link's "
            "trees-off, all placebo__ columns, all base__ baselines) with pooled MAE, anomaly R2, corr2 and hit rate, "
            "and the adopted arm's regret. Beside it (report-only) the per-region paired contrast of the adopted arm "
            "against every other selectable arm, and factor summaries (link, tool, weighting). NOT a test of the "
            "per-unit axis (M56); AK4(b) is the real ablation.",
    "population": "Lead 0 labelled rows: pm25 91,428 rows / 127 groups (17 columns: 10 arms, 4 placebos, 3 baselines; "
                  "8 selectable tree arms); ndvi 94,527 / 133 (10: 5, 2, 3; 4 selectable); fire 94,702 / 40 (24: 15, "
                  "6, 3; 12 selectable); defo 369,096 / 42 (15: 9, 3, 3; 6 selectable); coral 2,312 / 37 (23: 15, 6, "
                  "2; 12 selectable).",
    "inputs": [inp(RUN[p] + "/" + TP, ["y", "normal", "group", "unit", "legal_min", "legal_max", "every arm__, placebo__, "
                                         "base__ column"]) for p in PKGS]
              + [inp(RUN[p] + "/score_pooled.csv") for p in PKGS]
              + [inp(RUN[p] + "/score_by_group.csv") for p in PKGS]
              + [inp(RUN[p] + "/verdict.json", ["adopted", "band", "hit_tolerance", "measurement_error_floor"]) for p in PKGS]
              + [inp(RUN[p] + "/adoption.json", ["adopted", "eligible", "penalty"]) for p in PKGS],
    "formula": "Per column: pooled MAE, anomaly R2 (saved normal; NaN on coral), corr2, hit at verdict.json "
               "hit_tolerance (and hit_floor where the floor is declared), each checked against score_pooled.csv "
               "(rtol 1e-12). Selectable tree arms = arm__ columns whose name does not contain 'trees_off' (placebos "
               "and baselines are never selectable, R24). best = the selectable arm with the lowest pooled MAE; "
               "regret_abs = MAE(adopted) - MAE(best); regret_rel = regret_abs / MAE(best). Also print the lowest "
               "column overall (any kind) and mark eligible arms from adoption.json. Report-only: for each "
               "selectable arm a != adopted, d_g = MAE_a(g) - MAE_adopted(g) (positive = adopted better) from "
               "score_by_group.csv, group jackknife 1.96, tag with the run band, labelled post hoc. Factor summaries: "
               "weighting effect = MAE(link, tool, unweighted) - MAE(link, tool, gls); tool effect = MAE(plain) - "
               "MAE(corrector); link effect = best arm per link.",
    "fact_sheet_values": "R15 (provisional): PM2.5 best log corrector GLS 3.5875 vs adopted log corrector unweighted "
                         "3.5881 (regret 0.0006); plain vs corrector 3.5965 vs 3.5881 (unweighted); identity arms "
                         "3.724-3.778; log trees-off 3.853. NDVI adopted identity plain unweighted 0.03146 is best "
                         "(regret 0); others 0.03148-0.03151. Fire best tree arm log corrector GLS 0.004296 vs adopted "
                         "0.004385 (+2.1%); all four log arms 0.004296-0.004322 beat the adopted; log trees-off "
                         "0.004281 beats them all; identity arms 0.00648-0.00669 > identity normal 0.006259. Defo "
                         "adopted 0.0054158 = log plain 0.0054164 (regret 0); arcsine arms 0.00573; identity arms "
                         "0.00791-0.00797 (> PZ 0.00612). Coral every unweighted arcsine/log arm 6.147-6.376 beats the "
                         "adopted 6.698; best arcsine corrector unweighted 6.147 (regret 0.55, +9.0%). score_pooled.csv "
                         "values agree (e.g. pm25 3.5874804069 vs 3.5880911341 -> 0.00061; fire 0.0042957949 vs "
                         "0.0043850646 -> +2.08%; coral 6.1474857630 vs 6.6979892451 -> 0.5505, +8.95%).",
    "engine_definition_source": ENG + "/treeroute/report/metrics.py score_table() 846 (pooled, macro and key lines), "
                                "hit_rate() 688, corr2() 604, anomaly_r2() 580, group_jackknife() 1032, contrast_tag() "
                                "1097; layer/arms.py (arm set, R24); layer/decide.py (eligibility guard, adoption; "
                                "M43-M44); pipeline/passes.py report() 1049-1065.",
})

# ------------------------------------------------------------------ P29
p29_inputs = [inp(VERD[p]) for p in PKGS] + [inp(HEAD[p], ["lead", "rows", "line", "mae_reference", "reference"]) for p in PKGS]
for p in PKGS:
    for L in LEADS[p]:
        p29_inputs.append(inp("%s/board_lead_%d.csv" % (BOARD[p], L),
                              ["lead", "learner", "contrast", "decides", "band", "d_mean", "d_se", "d_low", "d_high",
                               "n_groups", "tag"]))
for p in ["pm25", "ndvi", "defo", "coral"]:
    for L in LEADS[p]:
        p29_inputs.append(inp("%s/human_board_lead_%d.csv" % (HBOARD[p], L),
                              ["lead", "rival", "decides", "band", "d_mean", "d_se", "d_low", "d_high", "n_groups", "tag"]))
p29_inputs += [inp(RIVALS_TABLE, ["problem", "lead", "rival", "decides", "groups", "d_mean", "d_low", "d_high", "verdict"]),
               inp(RUN["fire"] + "/jackknife.csv")]
items.append({
    "id": "P29",
    "what": "Sensitivity of every deciding verdict to the interval method: t(G-1) instead of z = 1.96, two-sided "
            "p-values (z and t), the re-applied tag, Holm across the five nowcast verdicts, the band as a share of the "
            "deciding reference MAE, and the count of deciding verdicts. Report-only, post hoc.",
    "population": "79 deciding verdict rows: 14 of ours (pm25 leads 0/6/12, ndvi 0/6/12, fire 0/6/12, defo 0/1, coral "
                  "0/183/365; lead 0 = verdicts CSV rows 'all' (source verdict.json), leads > 0 = rows 'common' "
                  "(source ladder.json); 6 are declined) + 65 RIVALS_TABLE rows with decides == True (53 common, 12 "
                  "human; 12 of them IDENTICAL). G = the row's n_groups: pm25 127, ndvi 133, fire 40, defo 42, coral 37 "
                  "(32 on the coral human CRW rows). Holm: the 5 lead-0 own verdicts.",
    "inputs": p29_inputs,
    "formula": "For each row take mean and SE from its source (own: contrast_mean, contrast_se; common: board d_mean, "
               "d_se; human: human board d_mean, d_se) and check SE == (high - low)/(2*1.96) and the recorded CI == "
               "mean +- 1.96*SE (rtol 1e-9; RIVALS_TABLE d_low/d_high cross-checked too). t CI = mean +- "
               "t_{0.975, G-1}*SE (scipy.stats.t.ppf). p_z = 2*(1 - Phi(|mean/SE|)); p_t = 2*(1 - T_{G-1}(|mean/SE|)). "
               "tag_t = the D74 rule with the t CI and the row's own band; rows tagged declined or identical keep their "
               "tag (no interval). Holm step-down at alpha 0.05 over the 5 lead-0 own verdicts, separately with p_z and "
               "p_t (adjusted p_(i) = max_{j<=i} min(1, (m-j+1) p_(j)), m = 5). Band share = 100 * band / "
               "mae_reference of the lead-0 'all' pooled headline row (own-link trees-off; coral donor median). Fire's "
               "blocked-jackknife CI is read from jackknife.csv (report-only row). Count rows = 79.",
    "fact_sheet_values": "P29 (provisional): fire nowcast t39 = 2.023, lower bound -1.2e-06, p_t 0.056 (z: +1.46e-07, "
                         "p 0.049) -> HELPS becomes CANNOT TELL; coral CRW (tier L) 183 d, 32 groups, t31 CI [-0.073, "
                         "3.773] -> BEATS becomes CANNOT TELL; every other deciding verdict unchanged. Holm with z: all "
                         "five nowcasts survive (fire last, p 0.049 vs 0.05); with t fire fails (0.056). Band share: "
                         "PM2.5 1.20%, NDVI 1.52%, fire 0.31%, defo 1.93%, coral 11.06%. 'About 80 verdicts'. Probe: "
                         "79 rows, exactly those 2 change; p_z / p_t fire 0.04921 / 0.05635, CRW 183 0.04976 / 0.05879; "
                         "band shares 1.1993 / 1.5159 / 0.3064 / 1.9328 / 11.0623 %. Fire blocked jackknife (final, "
                         "jackknife.csv): mean 4.078e-05, se 2.187e-05, CI [-2.08e-06, 8.37e-05], 39 blocks.",
    "engine_definition_source": ENG + "/treeroute/report/metrics.py group_jackknife() 1032, contrast_tag() 1097, "
                                "single_verdict() 1141, blocked_jackknife() 1058, equivalence_band() 1175; "
                                "engine_constants.py JACKKNIFE_Z (S2.jackknife_z = 1.96, line 323); rival harness "
                                "D:/treeroute/rivals_build/rivals/harness.py score() 2494-2513 (contrast_tag with the "
                                "run band); human tool D:/treeroute/human_rivals_build/human/rivals_human/board.py "
                                "1152-1155; engine/PREREGISTRATION_DRAFT.md sections 7-8 (z = 1.96, no multiplicity "
                                "correction).",
})

# ------------------------------------------------------------------ R3b
r3b_inputs = [inp(RUN[p] + "/score_pooled.csv") for p in PKGS] + [inp(HEAD[p]) for p in PKGS] + \
             [inp(RUN[p] + "/" + TP, ["y", "adopted arm column", "base__* columns", "arm__*_trees_off_unweighted"]) for p in PKGS]
items.append({
    "id": "R3b",
    "what": "Model against the best naive baseline at the nowcast, for all five problems (only the fire cell is "
            "provisional; the other four rows are recomputed as a check).",
    "population": "Lead 0 labelled rows: pm25 91,428 / 127 groups; ndvi 94,527 / 133; fire 94,702 / 40; defo 369,096 "
                  "/ 42; coral 2,312 / 37.",
    "inputs": r3b_inputs,
    "formula": "Model = the adopted arm column (verdict.json 'adopted'). Candidate baselines: base__guess_normal, "
               "base__last5_normal, base__predict_zero and arm__<link>_trees_off_unweighted for every link of the run "
               "(the geometric normal on log links); coral: base__donor_median and base__predict_zero only (its "
               "trees-off is a neighbour-pool regression, not a naive baseline, R3b note). best = the candidate with "
               "the lowest pooled MAE over labelled rows; change% = 100*(MAE_model - MAE_best)/MAE_best; for fire also "
               "change% vs base__predict_zero. MAEs checked against score_pooled.csv.",
    "fact_sheet_values": "R3b: fire 0.004385 vs log trees-off 0.004281 (provisional), then PZ 0.004284: +2.4% "
                         "(worse); +2.4% vs PZ. Final rows: PM2.5 3.588 vs log trees-off 3.853 (-6.9%); NDVI 0.03146 vs "
                         "L5 0.03934 (-20.0%); defo 0.005416 vs log trees-off 0.005715 (-5.2%); coral 6.698 vs PZ 8.100 "
                         "(-17.3%). Expected from score_pooled.csv: fire +2.424% vs log TO (0.0043850646 vs "
                         "0.0042813023), +2.356% vs PZ (0.0042841146); pm25 -6.88%; ndvi -20.02%; defo -5.23%; coral "
                         "-17.31%.",
    "engine_definition_source": ENG + "/treeroute/report/metrics.py baseline_guess_normal() 348, "
                                "baseline_last5_normal() 402, baseline_predict_zero() 336, baseline_donor_median() "
                                "558, mae() 569; route/kinds.py trees-off (R16); route/neighbour.py trees_off_neighbour "
                                "(why coral trees-off is excluded).",
})

# ------------------------------------------------------------------ RC12
LRN = ["ridge", "rf", "lgbm", "lgbm_tweedie", "hgb_l1"]
rc12_inputs = [inp(RUN["coral"] + "/" + TP, ["unit", "group", "time", "lead", "year", "programme", "y",
                                             "arm__arcsine_corrector_gls", "base__donor_median", "base__predict_zero"])] + \
              [inp("%s/lead_0/preds_%s.parquet" % (BOARD["coral"], L),
                   ["unit", "time", "lead", "arm__rival_%s" % L, "arm__rival_%s_raw" % L, "guard_passed"]) for L in LRN] + \
              [inp(BOARD["coral"] + "/board_lead_0.csv"), inp(MAG_EDGES), inp(MAG_BINS),
               inp(RUN["coral"] + "/verdict.json", ["band"])]
items.append({
    "id": "RC12",
    "what": "Coral nowcast by target magnitude: ours (adopted arcsine corrector GLS) against every common rival, "
            "with hgb_l1 (the L1 booster that beats us pooled) in focus, plus predict-zero and the donor median. "
            "Outcome-defined strata: report-only, post hoc, shown together.",
    "population": "Coral lead 0, all 2,312 test visits (37 scored groups, 2016-2019). Strata: (a) the engine report's "
                  "own magnitude bins with the lead-0 edges of positive donor labels (pos_q25 1.91619047625, pos_q50 "
                  "7.255, pos_q75 23.9575; 11,338 donor rows): B0 y = 0 (1,288 visits, 26 groups), B1 (0, q25] (278, "
                  "23), B2 (q25, q50] (262), B3 (q50, q75] (245), B4 > q75 (239); (b) severe y >= 50 (140 visits; "
                  "the D54/Part 605 stratum). y > 0 as a whole is item A2.",
    "inputs": rc12_inputs,
    "formula": "Join each rival's preds_<L>.parquet on (unit, time, lead) one-to-one (2,312 rows). Bin: B0 if y == 0, "
               "else searchsorted([q25, q50, q75], y, side='left') -> B1..B4 (right-closed), exactly coral_report.py "
               "magnitude_bin. Per stratum and column (ours, arm__rival_<L> for the 5 learners, base__predict_zero, "
               "base__donor_median): n, n_groups, mean y, mean prediction, MAE. Check ours per bin against "
               "magnitude_bins.csv (lead 0, stratum_value ALL, column arm__arcsine_corrector_gls; rtol 1e-12). "
               "Report-only per-group contrast in each stratum: d_g = MAE_rival(g) - MAE_ours(g) over the groups with "
               "at least one row in the stratum, group jackknife 1.96, tag with the coral band 0.9175581931 (G < 3 -> "
               "cannot tell).",
    "fact_sheet_values": "RC12 provisional (engine/PAPER_NOTES_RIVALS.md, 2026-10-21): 'the loss comes from "
                         "under-predicting big events: ours wins on 0% surveys (1.39 vs 2.12), and L1 wins on every "
                         "bleached stratum (severe 38.7 vs 53.1)'. Probe (light, this spec): B0 ours 1.393 vs hgb_l1 "
                         "2.116; B1 2.248 vs 2.489; B2 4.571 vs 5.769; B3 8.396 vs 9.469 (ours lower in B1-B3); B4 "
                         "41.052 vs 31.151; y >= 50 53.125 vs 38.660 (hgb_l1 lower). 'Every bleached stratum' is NOT "
                         "reproduced on the engine bins nor on the cuts (0,10]/(10,50]/(50,inf) (ours lower on (0,10]: "
                         "3.71 vs 4.41). The final part of RC12 (Part 600: 6.356 vs 6.698, d -2.30 [-4.21, -0.39]; by "
                         "programme) is unchanged.",
    "engine_definition_source": "D:/treeroute/coral_build/report_scripts/coral_report.py magnitude_edges() 498-529 "
                                "and magnitude_bin() 531-541 (the B0-B4 bins of the frozen coral report); " + ENG +
                                "/treeroute/report/metrics.py mae() 569, group_jackknife() 1032, contrast_tag() 1097; "
                                "rival harness D:/treeroute/rivals_build/rivals/harness.py _frame_for_scoring() "
                                "2363-2388 (join, guarded/raw columns) and score() 2494-2513 (d = rival - ours).",
})

# ------------------------------------------------------------------ A1
LRNF = ["ridge", "rf", "lgbm", "lgbm_tweedie"]
a1_inputs = [inp(RUN["fire"] + "/" + TP, ["unit", "group", "time", "lead", "y", "arm__arcsine_corrector_gls",
                                          "base__predict_zero", "base__guess_normal"])] + \
            [inp("%s/lead_0/preds_%s.parquet" % (BOARD["fire"], L),
                 ["unit", "time", "lead", "arm__rival_%s" % L, "arm__rival_%s_raw" % L, "guard_passed"]) for L in LRNF] + \
            [inp(BOARD["fire"] + "/board_lead_0.csv"), inp(RUN["fire"] + "/verdict.json", ["band"])]
items.append({
    "id": "A1",
    "what": "Fire active cells, stratified (owner MUST-INCLUDE; outcome-conditional, post hoc): ours vs "
            "LightGBM-Tweedie (the pooled-MAE winner), other common rivals and predict-zero beside, on the zero rows, "
            "the active rows (y > 0; final in the Part 606 addendum, recomputed as a check), the top 1% and the "
            "active rows below the top 1%. The provisional pieces are the top-1% numbers and the zero-row complement.",
    "population": "Fire lead 0 labelled rows 94,702 (40 groups, 2019-2022). Strata: y == 0: 92,943 rows (98.14%); "
                  "y > 0: 1,759 rows in 33 groups; top 1%: y >= q99 where q99 = numpy.quantile(y over the 94,702 "
                  "labelled rows, 0.99, default linear) = 0.102941 (to 6 d.p.): 949 rows in 31 groups; 0 < y < q99: "
                  "810 rows. The q99 threshold comes from TEST labels.",
    "inputs": a1_inputs,
    "formula": "Join each rival on (unit, time, lead). Per stratum: n, n_groups, mean y, mean prediction (ours, "
               "Tweedie, each rival), MAE (ours = arm__arcsine_corrector_gls; rivals = arm__rival_<L>, the deciding "
               "column; Tweedie's guard passed so guarded = raw; Ridge's guard failed so its guarded column is the "
               "normal and its raw column is shown beside), predict-zero MAE. Per-group contrast d_g = MAE_Tweedie(g) "
               "- MAE_ours(g) over the stratum's groups, group jackknife 1.96, groups where ours is better, tag with "
               "the fire band 1.356697052e-05 (report-only). Check: the all-rows pooled MAEs equal board_lead_0.csv "
               "rival_mae / ours_mae (rtol 1e-12).",
    "fact_sheet_values": "A1 final (Part 606 addendum): y > 0, 1,759 cell-months, 33 regions: ours 0.191 vs Tweedie "
                         "0.201, d +0.0047 [+0.0024, +0.0071], ours better in 25 of 33. Provisional "
                         "(PAPER_NOTES_RIVALS.md line 10): top 1%, 949 cell-months: ours 0.308 vs Tweedie 0.335; mean "
                         "predictions 0.098 / 0.062 vs truth 0.391. Complement (line 14): on the 98.1% zero rows ours "
                         "predicts a mean 0.00085, Tweedie 0.00032. Probe reproduces all: y > 0 0.191107 vs 0.200700, "
                         "d 0.0047162 [0.0023708, 0.0070615], 25/33; top 1% (>=) 949 rows / 31 groups, MAE 0.3082 vs "
                         "0.3350, mean pred 0.0980 vs 0.0618, mean y 0.3913 (strict > gives 938 rows); zero rows 92,943 "
                         "(98.14%), mean pred 0.000851 vs 0.000321.",
    "engine_definition_source": "Rival harness D:/treeroute/rivals_build/rivals/harness.py _frame_for_scoring() "
                                "2363-2388 and score() 2494-2522 (metric_by_key per group, _paired_contrast(rival, "
                                "ours), contrast_tag with the run band, timid rule); " + ENG + "/treeroute/report/"
                                "metrics.py group_jackknife() 1032, contrast_tag() 1097, top10_detection() 700 (the "
                                "engine's own outcome-defined event rule, NOT used here: the top 1% is a different, "
                                "post-hoc cut).",
})

# ------------------------------------------------------------------ A2
items.append({
    "id": "A2",
    "what": "Coral active (bleached, y > 0) surveys at the nowcast: ours against each of the five common rivals, "
            "pooled MAE and per-region paired contrasts (outcome-conditional, post hoc). The engine-v2 alarm numbers "
            "in PAPER_NOTES_RIVALS.md are out of scope (engine v2 replay, not v1 saved predictions).",
    "population": "Coral lead 0 visits with y > 0: 1,024 of 2,312 (36 of the 37 scored groups), 2016-2019.",
    "inputs": [inp(RUN["coral"] + "/" + TP, ["unit", "group", "time", "lead", "y", "arm__arcsine_corrector_gls",
                                              "base__donor_median", "base__predict_zero"])]
              + [inp("%s/lead_0/preds_%s.parquet" % (BOARD["coral"], L),
                     ["unit", "time", "lead", "arm__rival_%s" % L, "arm__rival_%s_raw" % L, "guard_passed"]) for L in LRN]
              + [inp(BOARD["coral"] + "/board_lead_0.csv"), inp(RUN["coral"] + "/verdict.json", ["band"])],
    "formula": "Join on (unit, time, lead); keep y > 0. Pooled MAE for ours, each arm__rival_<L> (all five passed their "
               "lead-0 guard, so guarded = raw; assert), predict-zero and donor median; mean y and mean predictions. "
               "Per rival: d_g = MAE_rival(g) - MAE_ours(g) over the 36 groups, group jackknife 1.96, groups where ours "
               "is better, tag with the coral band 0.9175581931 (report-only). Check: the all-rows pooled MAEs equal "
               "board_lead_0.csv rival_mae / ours_mae (rtol 1e-12).",
    "fact_sheet_values": "A2 (provisional, PAPER_NOTES_RIVALS.md, 2026-10-21): 1,024 surveys, 36 regions; ours 13.37 "
                         "mid-pack (L1 11.69, LightGBM 12.70, RF 12.87 better; Tweedie 13.62, Ridge 14.48 worse); every "
                         "per-region contrast CANNOT TELL (vs L1 -1.90 [-4.76, +0.97]). Probe reproduces: ours 13.370; "
                         "Ridge 14.478 d +1.808 [-1.805, +5.420], 23/36 groups ours better; RF 12.867 -0.781 [-3.156, "
                         "+1.595], 19/36; LightGBM 12.704 -0.745 [-3.298, +1.808], 18/36; Tweedie 13.617 +0.337 [-1.232, "
                         "+1.906], 17/36; hgb_l1 11.688 -1.896 [-4.758, +0.967], 17/36.",
    "engine_definition_source": "Rival harness D:/treeroute/rivals_build/rivals/harness.py _frame_for_scoring() "
                                "2363-2388, score() 2494-2522; " + ENG + "/treeroute/report/metrics.py mae() 569, "
                                "group_jackknife() 1032, contrast_tag() 1097.",
})

spec = {"spec": common, "items": items}
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(spec, fh, indent=1, ensure_ascii=True)
    fh.write("\n")
print("wrote", OUT, len(items), "items")
