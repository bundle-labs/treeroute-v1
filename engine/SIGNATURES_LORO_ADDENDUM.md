# LORO addendum to the proposed science signatures

Written on the night of Mon 28 Sep, after owner ruling D (engine/OWNER_RULINGS_2026-09-28.md section D: leave-one-region-out, same total test cells). Revised the same night after a review of the LORO update (25 items; every high and medium item is applied here or put to the owner below). Read it with SIGNATURES_FOR_REVIEW.md and APP_PLAN.md (1.2, 1.6, R12-R14, R18-R21, R25, R34, R35, C16, C17, 4.5, 4.6, 7.2, 9.1 item 6).

- **What:** 27 new or changed science functions and 6 shapes in `engine/treeroute/_proposed/loro_additions.py`. Each body is one line, `raise NotImplementedError("PROPOSED signature -- awaiting owner approval")`, as in the other `_proposed` files. Nothing runs, and no test imports `_proposed/`.
- **Precedence:** where this addendum and an older docstring in `_proposed/` disagree, this addendum wins until that docstring is fixed. OWNER_RULINGS_2026-09-28.md wins over both.
- **ATTENTION: nothing in engine code, schema, packages or tests was changed tonight.** The Tuesday build workflow is running. The files that must follow are listed in the last section. They change only after that workflow finishes and after L1, L2 and L7 are decided.
- **ATTENTION: K = 20 does not meet ruling D's "same total".** It gives about the old total on PM2.5 only. Fire doubles, NDVI falls to 0.45x and defo rises 1.22x. No single engine constant can give every package its old total. L1 sets out the choice. No default is proposed.

## New owner decisions (7)

| # | Needed | Decision | Options | Where |
|---|---|---|---|---|
| **L1** | Tue 29 Sep | The scored-unit budget. Ruling D asks for "the same TOTAL as the old hard split". | See the table below. **No default: the owner chooses.** | `derive_r18_scored_count`; plan R18, C16, 9.1 item 6a |
| **L2** | Tue 29 Sep | The five companion rules, plus the subset formula | (1) Each group's trees and the region router keep the old R18 count (100; 4,285 region). (2) The region router's fit keeps its 60,000-row whole-unit budget, decoupled from the scored units. (3) A per-unit package's fallback region router pools the group's 100 bank units, **and the tree-answer tables also hold those bank units' rows at or before the cut, for every group that has a fallback unit** (R20; plan lists the groups and prices the rows). (4) **Overlap blocks (new):** groups that share or touch a unit location form one block, by a rule on the static table (below). A router drops the trees of every group in its block, not only its own. Rival folds keep a block together. G-DISJOINT checks physical keys. plan prints the blocks. A blocked jackknife is printed beside the ruled one (report only). (5) **Masked Type-3 services (new):** every FitContext tree service (fit_bank answers, donor_fold_predict) answers through the same mask, so a plug-in never sees a row's own block's trees. The scored units are the evenly spaced subset floor(i x (N-1)/(m-1)) of the bank units, R14's formula, not stride_pick's N // m, which never reaches the tail of the list. | `derive_r18_bank_count`, `evenly_spaced_subset`, `derive_overlap_blocks`, `router_tree_columns`, `own_block_masked_answers`, `route_per_unit_loro`, `route_region_loro`; plan 9.1 item 6b |
| **L3** | M8 | Donor-only rivals: folds, tuning, and Board B | The ruling fixes 10 folds. Proposed: round-robin over overlap blocks sorted by their first name (fold = sorted block position mod 10, C17); a block stays in one fold. Hyperparameters are tuned once, on the old board's rule moved to all blocks: every 4th block, fitted up to the inner-fit end and scored on the inner-score years (pm25_rivals.py:317-319). Each fold model then refits the pick up to the train end. Disclosed: the tuning reads pre-cut rows of groups a fold model later "never saw". Quirk, harmless: block positions 0, 4, 8, ... mod 10 fall only in even folds. **Board B (the per-unit MOS) needs a choice**, because it used to pick its rival trial jointly with the MOS by inner MAE, and under LORO a trial's z is in-sample for about 3/4 of groups: (a) Board B takes Board A's pick and z comes only from the fold models (a disclosed change from the old board); (b) every trial runs on all 10 folds (about 10x the tuning cost, roughly +15 h on PM2.5). Either way `assert_rival_source` also checks every z row. | `rival_fold_of_group`, `rival_tuning_holdout`, `assert_rival_source`; plan 4.6, 9.1 item 6c |
| **L4** | Tue 6 Oct (optional) | Share each region group's tree-block Gram across its 3 links | Yes, as boilerplate behind a byte-identity gate. The tree block and its trace normalisation do not change between links, so its Gram (T'T), almost all of the work, is computed once per group. **The per-unit link-matched normal column (U-1) does change with the link,** so its border with the tree block is recomputed per link. bench_region_gram.py timed T'T alone, so the saving (306 to about 125 min on defo; total about 39.5 h instead of 42.5 under L1 (a)) roughly holds. A Gram assembled in blocks may not be byte-identical to a one-shot Gram; if the gate fails, the change is dropped. | route/solve.py (boilerplate); plan 4.5, 9.1 item 6d |
| **L5** | Sat 3 Oct (the GLS tool) | The weight model, c and s under LORO | The GLS weight forest (R25) is now fitted on every group's bank-unit rows up to the inner-fit end, and the scored units are among them. So the sigma weight on a scored unit's own router-fit row is an in-bag forest prediction from a model that saw that row and its y. Before LORO it never saw a test group. c (R23) and s (R36) now also include the scored units' own inner-score labels (scalars over about 2.1M rows). Not a test-window leak. The neighbour folds already leave group g out; per-unit and region do not. Options, one rule for all kinds: (a) disclose only (7.2); no cost. (b) Fit the weight model on the 10 C17 folds, so each group's weights come from a model that never saw it. The donor-row tree pass is shared; the 10 forest fits cost about +10.6 h per cut over the four nowcasts (+1.2 h on PM2.5; from the cost model's unmeasured forest assumption A3, mostly NDVI's and defo's wide tables). (c) Serve the forest's out-of-bag sigma on each group's own rows: about no cost, but the trees that answer a row still saw the same group's other rows. For c and s: accept them (disclosed) or cut them at the inner-fit end on the decision surface. **No default.** | plan R25, 7.2, 9.1 item 6e |
| **L6** | Tue 29 Sep (with plan 9.1 item 4) | A7 under LORO | LORO strengthens the A7 bias. The decision bank is cut at the donor train end, so neighbouring and overlapping groups' trees are trained on the inner-score years (2017-19) and already know the same regional anomalies; the 2020-23 test window gets no such help. Before, the nearest PM2.5 donor was a median 337 km away edge to edge. Options: (a) keep one bank at the donor train end, disclosed as strengthened; (b) one extra bank refit at the inner cut: about +5.0 h measured (+6.6 conservative) over the four nowcasts, +0.65-1 h on PM2.5; +0.9-2.4 h more if the inner surface's GLS target also uses that bank. Either way the report shows the decision by nearest-donor distance band. **No default.** | plan 7.2, 9.1 item 4, 9.2 A7 |
| **L7** | Tue 29 Sep | Where the continuity list lives | Ruling D says split.yaml "keeps only exclusions and seen_during_design". The plan had added a third key, continuity_groups. (a) Keep continuity_groups in split.yaml, reporting only, with the owner's explicit OK. (b) Keep the old donor and test lists in legacy_harness/ and treeroute_report/ (both may name problems): split.yaml then holds exactly what the ruling says, the harness holds the exact shipped lists instead of inferring the donors, and treeroute_report computes the continuity row from saved rows. Checked: in all four packages every non-test group was a donor and nothing was excluded, so (a) can rebuild the old splits today. **L1 (b) needs L7 (a).** | plan 1.2, 4.4, 9.1 item 6g |

**L1 options** (hours: all headline runs, measured / conservative, from a scratch copy of loro_cost_model.py):

| Option | Scored per group: PM2.5 / fire / defo / NDVI | Totals (old: 2,000 / 1,000 / 70,487 / 4,400) | Plug and predict | Hours |
|---|---|---|---|---|
| (a) one K = 20 (C16) | 15 / 50 / 2,040 / 15 | 1,905 / 2,000 / 85,680 / 1,995: x0.95 / x2.0 / x1.22 / x0.45 | kept; departs from "same total" on fire, defo and NDVI | 42.5 / 54.8 |
| (b) each package's old total: K_p = its continuity-group count (20 / 10 / 17 / 44) | 15 / 25 / 1,734 / 33 | 1,905 / 1,000 / 72,828 / 4,389 | broken: a reporting list sets a count; a new problem has no list and still needs K | 47.4 / 63.3 (NDVI 22.1 / 29.7: its tables grow to 58.8 GB per kind, so both are rebuilt per group) |
| (c) one K = 44 (NDVI's old count), so every package gets about its old total or more (NDVI 4,389 against 4,400) | 34 / 100 (bank cap) / every bank unit / 33 | 4,318 / 4,000 / 176,061 / 4,389 | kept | about 59 / 80; PM2.5, defo and NDVI tables no longer fit on D: |

Under every option the old totals are printed beside the new ones (7.2). Two other rules were measured and are not offered: a total of T units per package (defo would drop to 2.8% of its old test rows), and a total of test rows per package (it counts rows where the ruling says cells).

**The overlap-block rule (L2 rule 4).** Two groups are linked when a unit of one lies at the same grid position as, or in the 8-neighbourhood of, a unit of the other: grid indices differing by at most 1 when the static table has them, otherwise a great-circle distance of at most sqrt(2) x the larger of the two groups' median nearest-unit spacing. Blocks are the connected components. Every candidate unit counts, not only the picks. No list and no number is hand-set. Measured read-only on D:/monthly_panel (NDVI's 133 groups): 8 linked pairs, 125 blocks, and no pair that only touches. brigalow_belt shares 8,251 cells with australian_mulga (48.8% of brigalow's cells, 16.5% of mulga's). california_central_valley shares 1,032 with california_chaparral (12.1%). Smaller: thar_desert / indian_acacia_babool 60, pampas / uruguay 42, cape_floristic_region / karoo 32, angola_zambia_fire_belt / miombo_woodland_zambia 29, andes_puna / bolivia_beni_savanna 1, north_china_plain / ordos_plateau 1. By name, all 8 pairs are among PM2.5's groups, 1 among fire's and 2 among defo's; M1 re-measures each package on its own grid. The old splits already had this (NDVI: brigalow test, mulga donor; PM2.5: california_central_valley test, chaparral donor), so the continuity row inherits it.

**Neighbour pool (coral track, M6b): now a fail-safe default, not an open question.** Every pool row from group h was trained on by h's trees, and about 39% of those trees had it in their bag. So by default the neighbour router drops the trees of every group present in the pool, and of their blocks. Relaxing that needs an owner signature. The fold-g pool on the decision surface follows the same rule as the test-pass pool.

## New signatures (loro_additions.py)

| Needed | Function or shape | One-line contract | Rule | Decision |
|---|---|---|---|---|
| Tue 29 Sep | `LoroSplitSets`, `LoroSplitDiff` | split.yaml as exclusions, seen_during_design and (under L7 a) continuity_groups; its differences with the data | plan 1.2, G-SPLIT | L7 |
| Tue 29 Sep | `loro_split_differences` | Every listed group exists in the data; no reported group is excluded | G-SPLIT | - |
| Tue 29 Sep | `groups_under_loro` | The groups = data minus exclusions, sorted; every one trained and tested | plan 1.2, R18, R19 | - |
| Tue 29 Sep | `check_g_split_loro` | G-SPLIT under LORO (BLOCK on any difference) | G-SPLIT | - |
| Tue 29 Sep | `check_g_support_loro` | G-SUPPORT counted in groups: refuse under 3, flag under 14 | G-SUPPORT, C15 | - (D44 restated) |
| Tue 29 Sep | `UnitCounts`, `UnitLists` | Two counts and two lists per group: bank and scored | R18 | - |
| Tue 29 Sep | `derive_r18_bank_count` | The pre-LORO count, no event floor; same rule value for every group, capped | R18 (1), C7 | L2 |
| Tue 29 Sep | `derive_r18_scored_count` | max(10, floor(K x n / G)), capped at the bank count; event floor on top (D13, D14) | R18 (2), C16 | **L1** |
| Tue 29 Sep | `evenly_spaced_subset` | Scored units = evenly spaced subset of the sorted bank units | R18, R14 | L2 |
| Tue 29 Sep | `pick_unit_lists` | Bank by stride (D40), scored as the subset; scored inside bank asserted | R18 | - |
| Tue 29 Sep | `OverlapBlocks`, `derive_overlap_blocks` | Groups that share or touch a unit location, as connected components, from the static table | R14, G-DISJOINT, C17, R34 | **L2** |
| Tue 29 Sep | `LoroSurfaceKind`, `derive_r13_surface_loro` | Inner window, or one leave-one-group-out fold per group from one inner-cut bank (fold g drops g's block and the pool groups) | R13, C8 | - |
| Tue 29 Sep | `derive_r21_smoke_plan_loro` | First 4 groups, all trained and tested, 40 units all scored, 12 trees | R21 | - |
| Wed 30 Sep | `assert_group_manifests` | Each group's trees saw only its own bank units, at or before the cut | G-DISJOINT, R19 | - |
| Fri 2 Oct | `router_tree_columns` | A router's tree columns = every tree outside its overlap block (neighbour: outside the row's and the pool's blocks) | R14, R20 | L2 |
| Fri 2 Oct | `assert_no_own_group_column` | Refuse any router fit or service answer holding an own-block column; blocks re-derived from physical keys at run start | G-DISJOINT | - |
| Fri 2 Oct | `route_per_unit_loro` | Per-unit router with the own-block drop; fallback pooled over bank units, whose rows the tables hold | R12, R14-R16, R20 | L2 |
| Tue 6 Oct | `route_region_loro` | Region router: fit on capped bank units, score the scored units, own block dropped | R14-R16, U-1 | L2 |
| Sun 4 Oct | `check_scored_units_loro` | Saved units = derived scored lists, inside the bank lists, for every group | G-SPLIT (outputs) | - |
| Sun 4 Oct | `report_groupings` | all / without seen_during_design / continuity; band from 'all' only; blocked jackknife on 'all' | R34, R35, Q49 | L7 |
| Sun 4 Oct | `nearest_other_group_distance` | Great-circle km from each scored unit to the nearest other group's bank unit; 0 km or own-block nearest flagged | R34, Section 10 | - |
| Sun 4 Oct | `distance_band_edges` | Distance bands at the quartiles of the per-unit distances (no hand-set edge) | R34, Section 10 | - |
| M4 | `own_block_masked_answers` | The one gateway for Type-3 tree answers (fit_bank, donor_fold_predict): each row's block dropped; no raw per-tree access | plan 1.6, G-DISJOINT | **L2** |
| M8 | `neighbour_pool_loro` | Strict pool from any group; returns the drop set (row's block + pool groups' blocks) | R14, C11 | - |
| M8 | `route_neighbour_loro` | Neighbour router with the per-row drop set | R14, R16, R23 | - |
| M8 | `rival_fold_of_group` | Round-robin over sorted overlap blocks, 10 folds | plan 4.6, C17 | **L3** |
| M8 | `rival_fold_training_groups` | A fold model is fitted on every group outside the fold | plan 4.6 | - |
| M8 | `rival_tuning_holdout` | Every 4th block in sorted order, once; carries the Board B choice | plan 4.6 | **L3** |
| M8 | `assert_rival_source` | Each donor-only prediction and each Board B z row came from its own group's fold model | G-DISJOINT, plan 4.6 | L3 |

## Superseded signatures

| Old (`_proposed/`) | Replaced by | What changes | Needed |
|---|---|---|---|
| `common.SplitSets` (donor_groups, test_groups, excluded, seen_during_design) | `LoroSplitSets` | No donor or test list; adds continuity_groups (reporting only; L7) | Tue 29 Sep |
| `common.SurfaceKind.DONOR_FOLDS` | `LoroSurfaceKind.LEAVE_ONE_GROUP_OUT` | Neighbour folds are one group each, from one inner-cut bank | Tue 29 Sep |
| `split.split_differences` (D38, D39) | `loro_split_differences` | D38 (the split's groups = donor + test + excluded) and D39 (seen_during_design inside the test groups) lapse: the groups are the data minus exclusions, and a reported group only has to exist and not be excluded | Tue 29 Sep |
| `split.pick_units` | `pick_unit_lists` | Two lists per group instead of one count for donor and test | Tue 29 Sep |
| `split.check_scored_units(scored, derived)` | `check_scored_units_loro(scored_in_outputs, lists: UnitLists)` | Needs the bank lists to check "scored inside bank"; runs for every group | Sun 4 Oct |
| `split.make_donor_folds` | `derive_r13_surface_loro` (neighbour); `rival_fold_of_group` (rivals) | The neighbour surface drops one block's columns per fold. Type-3 needs no folds (`own_block_masked_answers`) | Tue 29 Sep |
| `split.assert_bank_disjoint` | `assert_group_manifests` + `assert_no_own_group_column` | No test groups to be disjoint from. Each group's trees stay inside their group, and no router uses its own block's trees | Wed 30 Sep |
| `validators.check_g_split` | `check_g_split_loro` | As above | Tue 29 Sep |
| `validators.check_g_support` (D44, D45) | `check_g_support_loro` | n_test_groups and n_donor_groups become n_groups. The signed 3/2 refuse and 14/5 flag read 3 and 14 groups. D45 unchanged | Tue 29 Sep |
| `vault.LabelView.donor_labels(split: SplitSets, ...)` (vault.py:130) | `donor_labels(split: LoroSplitSets, cut, cut_kind, lead, unit_ids, purpose)` | Donor groups = groups_under_loro (every group). unit_ids = the bank units (scope 'picked') or None (every candidate unit, scope 'all_donor_units', for the R18 event rate). The refusal "a unit that belongs to a test group" becomes "a unit that is not a bank unit" | Tue 29 Sep |
| `derive_rules.derive_r13_decision_surface` | `derive_r13_surface_loro` | Neighbour: leave-one-group-out, not K = min(5, donors) fold banks | Tue 29 Sep |
| `derive_rules.derive_r18_unit_count` (D13, D14, D15) | `derive_r18_bank_count` + `derive_r18_scored_count` | The event floor (D13 formula, D14 rate) moves to the scored count. The rate reads every group's labelled rows at or before the train end. D15 (thin = non-tree columns) stays with the bank count | Tue 29 Sep |
| `derive_rules.derive_r21_smoke_plan` | `derive_r21_smoke_plan_loro` | 4 groups, all trained and tested, instead of 2 donor + 2 test | Tue 29 Sep |
| `route_kinds.route_per_unit` | `route_per_unit_loro` | Own-block tree columns dropped; the fallback region router pools bank units | Fri 2 Oct |
| `route_kinds.route_region` (D81 unchanged) | `route_region_loro` | Separate fit units (bank, capped) and scored units; own-block tree columns dropped | Tue 6 Oct |
| `FitContext.fit_bank(target_transform) -> Bank` (fit_context.py:274-290) | the same call, returning a service that answers only through `own_block_masked_answers` | A plug-in never holds a raw Bank: every answer drops the row's own block, on donor rows and scored rows alike. Planted fault | M4 |
| `route_kinds.neighbour_pool(..., test_groups)` (route_kinds.py:378-381) | `neighbour_pool_loro(..., blocks)` | No test_groups argument (no group is held back); returns the pool AND the drop set (the row's block plus the pool groups' blocks) | M8 |
| `route_kinds.route_neighbour` (route_kinds.py:408) | `route_neighbour_loro(..., tree_group, blocks, ...)` | Its signature had no tree-column argument, although R14 drops trees per row | M8 |

## Same signature, changed contract (docstring edits once approved)

- `split.candidate_units`, `split.stride_pick` (D40): run for every group. The stride now picks the BANK units. The M1 check that it reproduces the shipped cells still applies.
- `split.as_sorted_set` (D37): unchanged; it sorts the exclusion, seen and continuity lists.
- `derive_rules.derive_r03_coverage_end`: "half the test groups" becomes "half the groups" (the argument is renamed; see the last section).
- `derive_rules.derive_r12_router_kind` (D9): h is taken over all candidate units of EVERY group.
- `FitContext.donor_rows` (D16): donor rows are every group's BANK units at or before the cut. D16's "picked donor units" reads "bank units of every group".
- `FitContext.__init__`: `picks` becomes a `UnitLists`. `FitContext.router_rows` accepts the bank units of one group (region fit, fallback) or scored units.
- `FitContext.for_fold`: the DECISION_SURFACE purpose uses the one inner-cut bank with a column drop (R13). The TYPE3 purpose is no longer needed.
- `FitContext.donor_fold_predict` (D98): answers each donor row from the trees outside the row's overlap block, through `own_block_masked_answers`, so no fold bank is fitted. D98's open return type is unchanged.
- `common.Bank`: gains `group_manifests: Mapping[str, BankManifest]` (one per group), checked by `assert_group_manifests`.
- `bank_recipe.fit_donor_bank`: loops over every group, each on its own bank units' rows. The name seeds are unchanged.
- `weights_gls.cross_region_error` (D55, D56): **the target is unchanged; the fit is not.** "The mean of the trees from the OTHER groups" already excludes each row's own group (and, with blocks, its block), as the router does. But the forest is now fitted on rows that include the scored units' own fit rows, so their weights are in-bag (L5). The donor-row pass covers every group's bank units: 2,133,600 rows x 12,700 trees on PM2.5 (about 4.4 times a LORO test table), against about 1.8M x 10,700 before.
- `metrics.group_jackknife`, `metrics.single_verdict`: run over all groups for the headline, and again on the `report_groupings` subsets. The band from 'all' judges every subset. `group_jackknife` also runs on per-block values for the report-only blocked jackknife (R34); if its SE of the verdict contrast is more than 20% above the group SE (C10's borderline share), the report flags it for the owner. The ruled group jackknife (Q19 a) still decides.
- `metrics.equivalence_band` (D75): the registry key becomes target + unit-list fingerprint + engine version.
- `route_kinds.search_fallback_level` (D82): unchanged. The fallback router it serves now fits on bank units.

## Signed decisions that LORO restates, not reopens

D9, D13, D14, D15, D16, D40, D44, D45, D55, D56, D75, D81, D82 and D98 keep their rulings, with the wording above. D38 and D39 lapse, because the lists they governed no longer exist.

## Files that must follow after the Tuesday build workflow (NOT touched tonight)

- `treeroute/package/schema.py`: `SplitFile` (lines 452-459) drops donor_groups and test_groups, and adds continuity_groups only under L7 (a). The G-NOKNOB message at lines 144-145 refuses a donor or test list with "derived: every group is trained and tested".
- `treeroute/cli.py:97`: prints donor and test counts. It should print the groups, the bank and scored counts and the overlap blocks instead.
- `treeroute/derive/rules.py:381-401` (being written tonight by the Tuesday build): `derive_r03_coverage_end`'s argument `test_groups` is renamed `groups`. Its docstring is already generic.
- `treeroute/engine_constants.py`:
  - C8 `DONOR_FOLDS_MAX` goes.
  - C13 `TREES_PER_DONOR` (line 180) and `SMOKE_TREES_PER_DONOR` (line 206) become `TREES_PER_GROUP` and `SMOKE_TREES_PER_GROUP`. `SMOKE_DONOR_GROUPS` and `SMOKE_TEST_GROUPS` become one smoke-groups constant (4).
  - C15's four group thresholds become MIN_GROUPS 3 and FLAG_GROUPS_BELOW 14.
  - New C16: the scored-unit budget as the owner decides under L1, status "proposed" until then.
  - New C17: 10 rival folds, round-robin over sorted overlap blocks.
- `datasets/{pm25,fire,defo,ndvi}/split.yaml`: drop donor_groups. Under L7 (a) move test_groups to continuity_groups; under L7 (b) move both old lists to legacy_harness/ and treeroute_report/. Keep the shipped provenance comments.
- `datasets/*/expected_derived.json`: add the LORO rows of plan 3.2 (groups; overlap blocks; bank and scored units; tree columns per router; continuity).
- The tests that pin the above: schema, constants, packages_declarative and noknob.
