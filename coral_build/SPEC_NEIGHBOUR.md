# SPEC: the engine's neighbour router kind (ported, strict pool)

Written 2026-10-19 under owner ruling U (engine/OWNER_RULINGS_2026-10-06.md:84-95). Revised the same day after three
skeptic reviews; the REVIEW LOG is at the end. Design only. Nothing is built.
It details section 4 of SPEC_TABLE_MODE.md (the NEIGHBOUR INTERFACE) and fixes the science of each step.
SPEC_TABLE_MODE.md 4.0 is the one reconciled text; this spec follows it point by point.
Engine paths are under `D:\treeroute\coral_build\engine\` (today equal to LIVE, hash 65a177bc...).
Legacy paths are under `C:\Users\<user>\Desktop\data set for reserch paper\` (read only).
Signed rules win over this text. Where none covers a choice, the default is listed in section 9.

**ATTENTION (read first)**
- **The two specs now agree.** Distance (haversine), scalers (the pass's candidates), trees-off (`solve_point` with
  one unpenalised column), the every-tree-dropped row (its trees-off), GLS (built) and the weighted solvers (keyword
  on all ten) are one text: SPEC_TABLE_MODE.md 4.0.
- **The pool horizon is the pass's own bank cut** (signed R14, APP_PLAN.md:239: "a pool of labelled rows at or before
  the lead's cut"). At lead L the test pass uses lead L's fit cut and the guard surface lead L's guard cut. U4's
  per-row filter "target day before the issue day" applies on top.
- **The strict pool changes the legacy result.** The legacy default pool (`--calib full`, adaptation.py:179)
  took test rows of the row's own group with true labels (adaptation.py:1620; Part 458), and at leads it
  compared dates with the TARGET date, not the issue date (adaptation.py:2020; coral_forecast.py:14-17).
  The engine takes neither. Expect a different (probably lower) skill than the legacy numbers.
- **The default drop rule removes the nearest groups' trees.** Every group present in a row's pool loses
  its trees for that row (SIGNATURES_LORO_ADDENDUM.md:34). The pool is the 150 nearest sites, so the
  dropped trees are the geographically closest ones. The legacy kept them. The share dropped is recorded
  per row. Relaxing the rule needs an owner signature (N7).
- **Legacy MMM was unpenalised; the engine has only the intercept unpenalised.** The legacy design was
  [1, MMM centred on the pool, context, trees] with two free columns (adaptation.py:1651;
  coral_architecture.py:199, 231). Signed R14 lists the intercept alone (derive/router_rules.py:300-303).
  The package may declare MMM as router context; it is then penalised (N8).

---

## 0. Words used here

- **scored row**: a row the pass predicts (a surface row or a test row).
- **candidate**: a row that may enter a scored row's pool before the distance steps.
- **pool**: the at most 50 rows the local ridge is fitted on.
- **issue day** of a row at lead L: its target day minus L, read from the table's `key_issue` column
  (SPEC_TABLE_MODE.md 0, 1.3). Nowcast: its own day.
- **horizon** of a pass: the pass's own bank cut, the last target day a candidate may have (SPEC_TABLE_MODE.md 2.4).
- **drop set**: the groups whose trees the row's router may not use (whole overlap blocks).
- **kind** (of an answer table): plain, corrector or placebo corrector (fit/tables.py).
- Z: the standardised tree features used for the feature-space step.

---

## 1. POOL

### 1.1 Legacy (what is ported)

| Step | Legacy | Where |
|---|---|---|
| Constants | K = 50, MINOK = 12, 3K = 150 | adaptation.py:1434, 1639 |
| Eligible rows | `(isdon or same) and dat < dat_i and ar != i` (default `full`) | adaptation.py:1620; default calib adaptation.py:179 |
| Too few | under 12 eligible: the training mean of link(y) | adaptation.py:1621-1622 |
| Map distance | haversine in km, R = 6371 | adaptation.py:1626; coral_architecture.py:73, 143-147 |
| 150 nearest | `ok[np.argsort(d)][:min(len(ok), 3K)]` | adaptation.py:1639 |
| 50 most similar | Euclidean in Z, `np.argsort(...)[:K]` | adaptation.py:1640 |
| Z | every tree feature (FC), NaN filled with the donor median of ALL donor rows, then 0, standardised on the training rows (mean, sd + 1e-9) | adaptation.py:1446-1455, 1521, 1547-1548 |
| Z weights | none by default (`--simfeat all`) | adaptation.py:212, 1553-1556 |
| Future-row assert | `dat[sel] < dat[gi]` | adaptation.py:1643 |
| Leads | Z from the lead's own frame | adaptation.py:1795-1799, 1930-1935 |

### 1.2 Engine rule (route/neighbour.py `neighbour_pool_loro`, SPEC_TABLE_MODE.md 4.1)

For each scored row r of a pass, in this order:

1. **Candidates** (once per pass): `ctx.router_rows(every train row id present at the lead, "neighbour_pool:<pass>")`
   on the pass's own context (fit/context.py:680-713). They are TRAIN-marked rows with a valid label and target day
   at or before the pass's bank cut. Test rows are never handed out: the row vault refuses any read at or after the
   first test day (labels/vault.py:324-331). Then owner ruling G1 (OWNER_RULINGS_2026-09-28.md:88): candidates with a
   missing context value leave through `ST.drop_missing_context`, logged by `log_g1_kept` and saved by
   `save_context_missing_rows`, as the grid passes do. The kept rows are a `ContextKeptRows` (stages.py:286-298).
2. **Eligible** (per row): candidates with `target day < issue day of r` and `row id != r`.
   - Nowcast: issue day = r's own day. On the test pass and the decision surface every candidate is already
     dated before r (the cut is before r's day), so this filter binds only as an assert.
   - Lead L: issue day = r's day minus L, from `key_issue`. The candidates are at or before the lead's cut, which is
     at or before every scored issue day. The filter binds on rows issued after the cut: a test row of March 2016 at
     lead 365 sees train rows dated at or before the lead's fit cut (2015-01-01) and before March 2015. On the
     earliest test rows (issue day = the cut) it removes the candidates dated on the cut day (O27 of SPEC_TABLE_MODE).
   - "Dated strictly before" means the label's LAST content day is before the issue day (O4 of
     SPEC_TABLE_MODE). Such a label is complete before the features of r end (SPEC_TABLE_MODE.md 1.7).
3. **Minimum**: fewer than `C11.neighbour_pool_min_rows` (12) eligible rows: return `(None, own block)`.
   The caller writes the fallback (section 3.7) and counts the row in `n_rows_pool_fallback`
   (route/kinds.py:172-182). The count is taken on eligible rows, before any distance step, as the legacy
   (adaptation.py:1621).
4. **Map distance**: the haversine central angle, the legacy formula without the Earth radius:
   `a = sin((lat2-lat1)p/2)^2 + cos(lat1 p) cos(lat2 p) sin((lon2-lon1)p/2)^2`, `angle = 2 arcsin(sqrt(clip(a,0,1)))`,
   `p = pi/180` (coral_architecture.py:143-147). Same ranking as the legacy km. The approved text accepts
   great-circle distance (_proposed/route_kinds.py:399; loro_additions.py:672-673). No new engine constant.
5. **150 nearest**: stable sort of the angle (`np.argsort(kind="stable")`), keep the first
   `C11.neighbour_pool_distance` (150), or all eligible rows when fewer.
6. **50 most similar**: Euclidean distance in Z between r and those rows,
   `sqrt(((Z[gg] - Z[r])**2).sum(1))` (the legacy expression, adaptation.py:1640); stable sort; keep the first
   `C11.neighbour_pool_feature` (50), or all when fewer. A pool may hold 12 to 50 rows.
7. **Ties**: the stable sort keeps candidate order, which is row-position order (sorted row id,
   SPEC_TABLE_MODE.md 1.3). So a tie goes to the earlier row position, at both steps. Ties are common at
   step 5: repeat visits to one site share a distance. The legacy used numpy's default unstable sort.
8. **Asserts** (`RouteGuardError`, kept under python -O): a pool row that is not train-marked, dated after
   the pass's cut, dated on or after r's issue day, or equal to r (G-FITCUT; SPEC_TABLE_MODE.md 2.3).
9. **Returns**: pool row positions (store row keys, `candidates.row_positions`) in pool order, and the
   drop set (section 2).

### 1.3 Z: which features, standardised on which rows

- Columns: the tree features of the lead's table, exactly the columns the bank trees see (verdict-kept
  `driver` / `engineered`). The legacy FC also held `month`, `doy_sin` and `doy_cos` (adaptation.py:1443-1447),
  so its feature step preferred neighbours of the same season; here season is router context only (owner item
  N17).
- Missing values: 0-filled, as the trees see them (R30; SPEC_TABLE_MODE.md 1.3). The legacy first filled
  with a donor median over all dates (adaptation.py:1452-1455); that read later rows and is not ported.
- Constants: mean and population sd (+ `RK.CONTEXT_SD_OFFSET` = 1e-9, route/kinds.py:105) of each column
  over the pass's CANDIDATES (step 1). Candidates are train rows at or before the pass's own bank cut, so no test
  row, and no row dated after the cut, enters the constants. The cut is at or before every scored issue day, at
  every lead (test pass: cut = first test day minus L; guard surface: `check_inner_score_rows`, fit/context.py:715-731).
  These are the pass's bank DonorRows less G1 drops, which is the approved proposal "donor rows at or before the cut"
  (_proposed/route_kinds.py:400) and the legacy rule (training rows, adaptation.py:1548) restricted to the cut.
- Constant columns (fix phase, FIX_REPORT.md): a column with one value on every candidate is set to 0 in both Z
  matrices (route/neighbour.py `pool_feature_z`). It adds the same term to every candidate's distance, so this keeps
  the true ranking. With the 1e-9 offset alone, a score row off the constant got |Z| up to 3.5e10, and the feature
  step became map order. The pass records the count (`z_constant_columns`).
- No weights (legacy default `--simfeat all`).
- Leads: each lead's Z comes from that lead's table, for the scored row and the candidates alike
  (adaptation.py:1795-1799).

### 1.4 Determinism of the pool

Per scored row, the distance is computed on the full candidate vector in candidate order, never on a
variable-sized block. Elementwise numpy results then do not depend on how rows are batched. Pools depend on
the lead's Z, the candidates and the issue day only, not on the link, the kind, the weighting or the penalty. So one
pool per row serves every arm of the pass, as in the legacy ("pool mask ... untouched, so any difference between
arms is the COLUMNS", adaptation.py:1576-1578). Pools are computed once per pass, kept (int32, 50 per row) and saved
as `pools_<pass>.parquet` (SPEC_TABLE_MODE.md 3.8 step 9) for the pool audit.

---

## 2. TREE DROP

- **Own block** (R13/R14; router_rules.py:211-240, 255-315): the row's group's overlap block always drops
  (APP_PLAN.md:239 "Tree columns, every kind").
- **Pool blocks** (default, SIGNATURES_LORO_ADDENDUM.md:34; loro_additions.py:760-789): the block of every
  group present in the pool drops too. Reason: every pool row of group h was trained on by h's trees,
  about 39% in bag.
- Drop set = sorted union of those blocks. Columns = `RK.router_tree_columns(tree_group, drop_set)`
  (route/kinds.py:719-749), cached per distinct drop set. `RK.assert_no_own_group_column` runs on every fit
  (route/kinds.py:751-766; G-DISJOINT). The same columns serve plain, corrector and placebo tables.
- The legacy kept pool groups' trees and had no own-group trees only because test groups trained none
  (adaptation.py:1530-1537 builds the bank from `trn` only).
- **Almost all trees dropped**: the ridge still runs on the remaining columns. The tree penalty is
  trace-normalised per column (route/solve.py:79-81, 104-105), so a small block gets the same per-column
  shrinkage. Recorded per row: kept trees, kept share, groups dropped. The report prints their quantiles and
  the share of rows with fewer than 10% of the bank kept (report only, never a choice).
- **Every tree dropped**: `router_tree_columns` refuses an empty result (route/kinds.py:743-745), so it is not
  called. The row's every tree arm takes that row's trees-off value (section 4) on its pool: the limit of the
  ridge as the tree penalty grows. Counted apart as `n_rows_no_tree` (O8 of SPEC_TABLE_MODE, the one owner item).

---

## 3. LOCAL FIT

### 3.1 Design (R14, derive/router_rules.py:300-303)

- Columns: `[intercept, standardised context, tree answers]`; only the intercept is unpenalised.
  Without declared context: `[intercept, trees]`.
- Context: the package's `router_context` columns, standardised with `RK.router_standardisation` over the
  pass's candidates (route/kinds.py:456-480) and applied to pool and scored rows (route/kinds.py:482-494).
  Legacy: four context columns standardised on the training rows (adaptation.py:1435, 1544-1545).
- Trees: the kept columns of the pass's answer table, float32 upcast to float64 (route/kinds.py:427-436).
- Built with `RK.build_column_block` on a `RouterDesign` of kind neighbour (no normal block).
- y: `link_forward(y, link, c, ub)` on the pool rows (layer/links.py:84-115), with the pass's c (per fold on
  the decision surface, R13, R23).

### 3.2 Penalties and grid (R14, R26; engine_constants.py:179-197)

- `a_tree = C12.neighbour_trees_centre (0.5) x level`, `a_ctx = a_tree x ratio`.
- Grid: `C12.penalty_levels` (0.1 ... 100) x `C12.penalty_ratios` (0.0625 ... 1), level-major, 35 points;
  7 levels without context (`derived["R14"].value.grid`, router_rules.py:243-251).
- Base point: level 1, ratio 0.25 / 0.5 = 0.5, i.e. (0.5, 0.25), the legacy shipped pair
  (adaptation.py:1434, 1666). It must be on the grid (router_rules.py:308-310).
- Legacy reparameterisation is the same (`a_tree = ALPHA x mlt, a_ctx = ALPHA x mlt x rho`,
  adaptation.py:1601-1603, 1662-1665). The legacy swept 15 levels at the shipped ratio
  (adaptation.py:154); the engine follows signed R14 (35 points).
- Each block's penalty is `a x (sum of squared RAW block entries / columns)`, weighted by GLS weights when
  present (route/solve.py:72-81). The trace is on the raw block, not the projected one
  (coral_architecture.py:221-227).

### 3.3 Solve (the exact k-space dual)

- Pools have k <= 50 rows and p = 1 + context + trees columns, so k < p whenever more than about 50 trees
  remain. `solve_local` then dispatches to the dual (route/solve.py:67-68), as the legacy did with
  `USE_DUAL = True` (coral_architecture.py:176, 193-194). The switch is gone in the engine; the dual runs on
  shape alone (route/solve.py:8-10).
- Needed change (SPEC_TABLE_MODE.md 5.5): a keyword `n_unpenalised=UNPENALISED_COLUMNS` (default 2) on
  `solve_local`, `solve_local_dual`, `grid_dual`, `reference_grid`, `solve_grid`, `solve_point`,
  `grid_dual_weighted`, `reference_grid_weighted`, `solve_grid_weighted` and `solve_point_weighted`
  (route/solve.py:61-325). `o = n_unpenalised`, forwarded on every internal call. Grid callers never pass it. The
  neighbour kind passes 1.
- **Why the dual equals the primal.** The problem is
  `min |W^1/2 (y - U b_U - P b_P)|^2 + sum_j lambda_j b_Pj^2`, U the intercept, P the penalised columns.
  (1) b_U is free, so project it out: Q = orthonormal basis of W^1/2 U; Py = (I - QQ')W^1/2 y;
  PP = (I - QQ')W^1/2 P (route/solve.py:101-104). (2) Substitute c = Lambda^1/2 b_P, Zs = PP Lambda^-1/2:
  a ridge with unit penalty. (3) The push-through identity `(Zs'Zs + I)^-1 Zs' = Zs'(ZsZs' + I)^-1` gives
  `c = Zs' u`, `u = (ZsZs' + I)^-1 Py`: a k x k system (route/solve.py:111-119). (4) b_U is the
  least-squares fit of the remaining residual (route/solve.py:120). Every step is exact algebra. The only
  numeric gap is the primal's 1e-8 jitter on every diagonal element (route/solve.py:83;
  coral_architecture.py:208). The legacy measured agreement to 9.1e-10 (coral_architecture.py:189-191).
- Decision surface (every grid point): `grid_dual(..., n_unpenalised=1)` (or `grid_dual_weighted`) with
  `solve_grid`'s reference check on the first `solve.NVERIFY` (3) routed rows of each pass (route/solve.py:171-196).
- Test and guard passes (one point): `solve_point(..., n_unpenalised=1)` (or `solve_point_weighted`)
  (route/solve.py:199-204, 319-325).
- Small pools with k >= p (few trees left) take the primal path; the code is the same function.

### 3.4 Links (R22; layer/links.py:84-138)

- identity, log_c (`log(y + c)`, c from R23 per lead cut; per fold on the surface), arcsine
  (`arcsin(sqrt(y / UB))`), as R22 offers them for the target's legal range.
- Inverse: identity z; log_c `exp(z) - c`; arcsine `UB sin(clip(z, 0, pi/2))^2` (layer/links.py:118-138).
  Legacy arcsine inverse is the same line (adaptation.py:1436).
- Every arm is solved in link space; the pass returns link-space predictions (`RoutedPass`), and the layer
  inverts and clips (SPEC_TABLE_MODE.md 3.7).

### 3.5 Tools: plain, corrector, placebo

- The tools change the answer table only (fit/tables.py). Each kind is routed with the SAME pools and drop
  sets. Legacy: the corrector added `eta x corrector` to each tree column (adaptation.py:1583-1586).
- Arms: `candidate_arms(R22 links)` (layer/arms.py:152-171), each unweighted and GLS-weighted (R24); placebos only
  on the test pass (R24).

### 3.6 GLS weights (signed R24, R25, R13, L5)

- Signed rules cover the neighbour kind: R24 builds every arm "unweighted and GLS-weighted" (APP_PLAN.md:259); R25
  fits the weight model "per held-out group for neighbour, R13" (APP_PLAN.md:260); R13 builds fold g's GLS model
  "from the rows outside g's block at or before the inner-fit end" (APP_PLAN.md:238); L5 serves out-of-bag sigma
  (OWNER_RULINGS_2026-09-28.md:63). The approved `route_neighbour_loro` takes `weights` (loro_additions.py:794-797, :818).
- Test pass, lead 0: the cut's model from `weight_model_for_cut` (fit/weights.py:525), exactly as grids
  (pipeline/passes.py:575-583). Lead L: refit at the lead's cut only when the pinned arm is weighted (R29).
- Decision surface: one model per fold g from `weight_models_for_folds` (SPEC_TABLE_MODE.md 5.12): the guard-cut
  donor rows and their cross-region error target are built once (the arithmetic of `weight_model_for_cut`, with the
  fit-cut bank's answers as grids, L6_ANSWERS_DISCLOSURE); then one forest per fold on the rows outside g's block,
  handed out by the additive `FitContext.donor_rows_outside` (SPEC_TABLE_MODE.md 5.11). `fit/context.py:375-380` and
  `:742-748` keep refusing fold contexts; `for_fold` stays unbuilt.
- A row's weight is a property of the row, so the pool reads `w[pool]` (`weights_for_rows`, fit/weights.py:648-654),
  as the legacy (`W[sel]`, adaptation.py:1666).
- Solves: the weighted functions of route/solve.py with `n_unpenalised=1`. Trees-off stays unweighted
  (route/kinds.py:53, 1083).
- Legacy weights came from an in-sample spread forest on the training rows, clipped at percentiles over
  train AND test rows (adaptation.py:1564-1568). Not ported; R25 replaces it.
- Cost on coral: 83 fold forests (120 trees, depth 8) on about 9k rows each, plus one donor-row pass; roughly
  10-20 minutes (estimate; SPEC_TABLE_MODE.md 8.1).

### 3.7 Fallback and clip

- Pool None (under 12 eligible rows): every grid column of every arm and the trees-off take
  `link_forward(donor-row median of y)` (U3; `M.baseline_donor_median`, report/metrics.py:558-566).
  Donor rows (one per pass, each at or before the pass's bank cut, asserted):
  - nowcast and lead test passes: the lead's FIT-bank DonorRows;
  - lead-L guard surface: lead L's GUARD-bank DonorRows (the fit-cut rows would hold every guard row's own label);
  - decision surface: fold g's guard-cut DonorRows outside g's block (N5).
  After the inverse link the value equals the median within 1e-12. The legacy used the training mean of link(y)
  (adaptation.py:1622).
- Clip: R28 to the legal range after the inverse (`clip_with_counts` in decide; the pre-clip rate is kept).
  Legacy: `np.clip(INV(v), 0, 100)` (adaptation.py:1697).
- A row with no finite answer is never written: the kernel refuses a NaN in a kept tree column (G-PLUMB).

---

## 4. TREES-OFF and the donor-row median reference

- Trees-off (R16; _proposed/route_kinds.py:186-200): per row, `[intercept, standardised context]` fitted on
  the row's own pool, intercept unpenalised, context penalised at the R14 base point
  (`a_ctx = 0.5 x 1 x 0.5 = 0.25`) (O9 of SPEC_TABLE_MODE). Unweighted. Solved with
  `solve_point(Xc, y_link, Xt, 0, nctx, 0.0, a_ctx, n_unpenalised=1)`, the call shape the per-unit trees-off uses
  (route/kinds.py:586-593). Without context: the same call with nctx = 0, i.e. the jittered pool mean. This is the
  one text of SPEC_TABLE_MODE.md 4.0 and 4.2.
- It is the neighbour analogue of the other kinds' trees-off: the same router with the tree block removed.
  Per-unit and region drop the trees and keep intercept + normal (route/kinds.py:377-381); the neighbour kind
  has no normal (R15), so it keeps intercept + context.
- Per link. Each link's trees-off is reported beside the adopted column. Owner ruling V1 (2026-10-19,
  OWNER_RULINGS_2026-10-06.md:103) replaced the old rule for this kind: the decline target and every guard or
  decline baseline is the donor-row median (R34, base__donor_median), not the identity trees-off
  (pipeline/table_passes.py, pipeline/table_ladder.py; RULING_V_REPORT.md). The old text named the identity
  trees-off as the decline target and each link's trees-off as its guard reference (route/kinds.py:633-649).
- Pool None: trees-off = the fallback of 3.7.
- No identity assert (there is no normal). G-PLUMB pair 1 compares trees-off with an independent closed-form
  ridge on the same rows (O10 of SPEC_TABLE_MODE), with a `neighbour` note beside the pair's grid name.
- **The verdict reference is the donor-row median** (signed R34 and G-DECIDE, APP_PLAN.md:274, :319, :619; the
  approved trees_off_neighbour text, _proposed/route_kinds.py:192-193; `M.REFERENCE_DONOR_ROW_MEDIAN`,
  report/metrics.py:131). Neighbour trees-off is printed beside it. The donor-row median is also a baseline on every
  pass (R31) and the pool fallback. It is never an arm.

---

## 5. DECISION SURFACE (R13)

- Bank: the inner-cut bank at lead 0's guard cut (31 December of the inner-fit end year; L6 b). Every group's
  trees, each trained on that group's rows at or before the cut.
- Folds: one per group, sorted (router_rules.py:228-235). Fold g scores group g's TRAIN rows with a valid
  label and target day in (guard cut, fit cut] (SPEC_TABLE_MODE.md 2.4; APP_PLAN.md:238 "never after the
  donor train end"). Test rows are never scored here.
- Pool of each surface row: section 1 with horizon = the guard cut (signed R14 and R13: "the fold-g pool follows
  the same rule as the test-pass pool"). Candidates = train rows dated at or before the guard cut. So every pool row
  is before the row's issue day, and no inner-score label (after the guard cut) enters any pool. Group g's own rows
  at or before the guard cut may enter; its trees are dropped (own block).
- Drop set: g's block plus the pool groups' blocks (router_rules.py:216-219).
- Per fold: c from rows outside g's block at the guard cut (signed R13; checked against `R23:fold=<g>`); the GLS
  model per fold (3.6, signed R13/R25); the fallback median from the same rows (N5). Scalers (context and Z) from all
  candidates at the guard cut, the mirror of the test pass (N12).
- Every scored row is solved at all 35 grid points, for every selectable arm (unweighted and weighted) and each
  link's trees-off.
- The penalty pick: `LD.decide` (layer/decide.py:897-988) pools all folds' rows. `penalty_search` scores each
  grid point by MAE in y units after the inverse link and the clip; a tie goes to the first grid point; an
  edge pick is flagged, never extended (layer/decide.py:229-241). Then the R27 adoption. Test labels are
  never read: the vault issues the surface (`decision_surface`, SPEC_TABLE_MODE.md 3.4) and refuses test
  rows (layer/decide.py:772-806).
- The legacy fold pass held out 5 donor folds and scored their rows after CUT, with pools that took the
  held-out group's later rows (adaptation.py:1459-1489, 1620). The engine uses one fold per group and the
  strict pool.

---

## 6. LEADS

- Each lead L in (0, 183, 365) has its own table (SPEC_TABLE_MODE.md 1.2). A lead's pass reads only it:
  tree features, context, Z, issue days and the tree answers of pool and scored rows.
- Issue day = target day minus L, read from `key_issue` and asserted. The eligible filter (1.2 step 2) moves with it.
- Bank: the lead's fit-cut bank (test pass) and guard-cut bank (guard surface), SPEC_TABLE_MODE.md 3.9.
  Candidates: train rows present at L with target day at or before the pass's own cut (lead L's fit cut on the test
  pass; lead L's guard cut on the guard surface), and strictly before each row's issue day. The hand-outs are logged
  with lead L.
- Constants per pass (scalers, Z, fallback median) come from rows at or before that same cut (1.3, 3.7).
- Rows absent from a lead's table are not candidates at that lead (O15 of SPEC_TABLE_MODE).
- c: the lead's fit-cut c (D63 a). GLS: the lead's model, only when the pinned arm is weighted (R29).
- Guard and test passes run at the pinned point only (`LD.pin_of`), arms from `LA.lead_arms`
  (layer/arms.py:180).
- Lead 0 run through the lead path equals the nowcast pass byte for byte (SPEC_TABLE_MODE.md 3.9 step 8).
- Legacy at leads: Z and weights from the lead's frame (adaptation.py:1930-1945), but the pool date was the
  target date (adaptation.py:2020; coral_forecast.py:14-17). Fixed by U4.

---

## 7. DETERMINISM, RAM and TIME

**Determinism**
- No random draw anywhere in the kind. The only seeded objects nearby are the R25 weight forests
  (random_state 0, fit/weights.py:13-15), outside the router.
- Stable sorts with row-position ties (1.2 step 7). Pools fixed per pass before any solve (1.4).
- Rows are solved in score order. Workers: `C14.router_workers` (8) with BLAS at
  `C14.router_worker_blas_threads` (1) for the whole loop, checked on entry and exit, results written back
  in row order (the per-unit discipline, route/kinds.py:39-43, 901-950). So the bytes do not depend on the
  worker count. The `--jobs` hazard (memory: reference_jobs_changes_results) is closed the same way.
- The design is float64 from float32 answers; no dtype changes on the grid path.

**RAM** (machine 15.8 GB; coral: 83 groups x 100 trees = 8,300 trees, 13,650 rows at lead 0)
- Answer matrix per kind: rows of the lead table x bank trees x 4 bytes: 13,650 x 8,300 x 4 B = about 453 MB.
- One kind in RAM at a time (O20 of SPEC_TABLE_MODE); a RAM wait before it (ruling Q1). After the maximum wait the
  pass refuses, as today. There is no second, slower read path.
- Per row: the pool design 50 x 8,300 x 8 bytes = about 3.3 MB per worker; 8 workers about 27 MB.
  The 50 x 50 Grams are small.
- Pools: int32, 50 per row (about 3 MB for 13,650 rows); distances computed per row (13,650 x 8 bytes).
- GLS: the donor matrix of about 9,300 guard-cut rows x 63 features is small; the donor-row pass reads one group's
  answers at a time (fit/weights.py:611-624).
- Scored rows run in blocks for progress lines only. Nothing inside a pass is checkpointed; a resumed run recomputes
  the pass (SPEC_TABLE_MODE.md 3.10).

**Time** (estimates; the tiny smoke replaces them with measured numbers)
- Per row: about trees x 50 x 50 flops for the Gram (8,300 trees: about 21 M) plus 35 small Choleskys.
- Decision surface: 2,046 rows (SPEC_CORAL_TABLES.md 2.2) x 2 tools x 2 weightings x up to 3 links, plus trees-off:
  roughly 10-30 minutes with 8 workers. Test passes: one point, a few minutes each.
- Whole coral run (6 banks, GLS, passes, 2 leads): likely 1-3 hours, an owner command. Tiny smoke: a few minutes.

---

## 8. TESTS

Lean testing while building; the full suite once in the Fix phase.

| File | Test |
|---|---|
| tests/test_neighbour_pool.py | (1) date rule: no pool row on or after the issue day, at L = 0, 183, 365 on the toy; (2) never a test row and never after the pass's own cut, also when the toy plants a near test row with a huge label; (3) never the row itself; (4) 150 then 50 equals a brute-force reference over all candidates (haversine); (5) ties: two candidates at one site, the earlier row position wins; (6) under 12 eligible returns None, at exactly 11 and 12; (7) drop set = own block plus pool blocks, sorted, whole blocks; (8) the assert fires on a planted future candidate; (9) a ContextKeptRows is accepted |
| tests/test_neighbour_route.py | (1) dual equals a brute-force primal (`np.linalg.solve` on the full normal equations, intercept unpenalised, no jitter) within 1e-9, k = 50, p = 60 to 400, weighted and not; (2) `grid_dual` equals `reference_grid` at all 35 points, weighted and not; (3) trees-off equals a closed-form ridge of [1, context]; without context it equals the pool mean within 1e-9; (4) every tree dropped gives the trees-off and counts `n_rows_no_tree`; (5) G-DISJOINT fires on a planted own-block column; (6) fallback rows equal the donor median in y after the inverse link (1e-12) for identity, log_c and arcsine; (7) same bytes with 1 and 8 workers |
| tests/test_solve_unpenalised.py | the solve.py keyword omitted gives the old bytes on random designs, all ten solvers (grid no-op proof); `n_unpenalised=1` forwarded through the primal, the dual, `solve_grid(verify=True)`, `solve_point` and the weighted twins equals a brute-force primal; `n_unpenalised=2` equals no keyword |
| tests/test_fold_gls.py | SPEC_TABLE_MODE.md 5.11-5.12 |
| tests/test_table_pipeline.py | the pool audit and the leak probe of SPEC_TABLE_MODE.md 6.3 (pools, records, derived.json and every test prediction column at every lead unchanged when every test label is overwritten) |

**Comparison with the legacy code** (engine/legacy_harness/neighbour_replay.py; that folder may name problems).
- It runs ONLY on the synthetic toy table (tests/table_toy.py). It refuses any package that is not a toy build (the
  toy builder writes a marker file the harness checks), so no real test label is ever read outside the vault.
- It copies the legacy lines verbatim with provenance: haversine (coral_architecture.py:143-147),
  `solve_local` / `_solve_local_dual` with `o` as a parameter (coral_architecture.py:179-254), and the pool
  and fit loop (adaptation.py:1610-1666). Importing adaptation.py is avoided (it parses arguments on import).
- It feeds the legacy lines the float32-cast feature and context values the engine uses (SPEC_TABLE_MODE.md 3.3),
  so near-ties rank the same.
- Tiny case: the toy table at lead 0 and 365, 12 trees per group.
- Step 1, aligned: legacy mask `strict` with the train set = engine candidates of the same pass, W = 1, no MMM column
  (o = 1), the same tree columns as the engine's drop set, the median fallback, stable sorts. Expected: same pools,
  predictions within 1e-9.
- Step 2, each difference turned on alone, with counts of rows that change:
  (a) legacy default mask `full` (test rows and later rows enter; Part 458);
  (b) target date instead of issue date at lead 365;
  (c) pool groups' trees kept;
  (d) training mean fallback;
  (e) unstable sort (ties);
  (f) donor-median NaN fill in Z;
  (g) MMM unpenalised;
  (h) legacy GLS weights.
- The harness writes a CSV of these counts and MAE deltas on the toy. It is a check, never a selector.

---

## 9. OWNER ITEMS (no signed rule, or a departure; the default chosen)

Items shared with SPEC_TABLE_MODE.md section 7 are named there, not repeated: O4 (dated strictly before), O5 (Z,
scalers, distance, ties), O7 (fallback rows), O8 (every tree dropped), O9 (trees-off point), O10 (G-PLUMB pair 1),
O19 (signatures), O20 (one kind in RAM), O27 (event cut day). N1, N2, N4, N6, N9, N10, N11 and N13 left this list
(REVIEW LOG).

| # | Behaviour | Default (built) | Alternative |
|---|---|---|---|
| N3 | Z columns and fill (detail of O5) | the tree features, 0-filled, unweighted | donor-median fill (legacy, reads later rows); learned weights (`--simfeat`) |
| N5 | Fallback donor rows on the decision surface (detail of O7) | fold g's guard-cut rows outside g's block (as R13 does for c) | one median of all guard-cut rows for every fold |
| N7 | Pool groups' trees | dropped (signed default, SIGNATURES_LORO_ADDENDUM.md:34; U4 keeps it) | own block only (legacy-like; needs a signature) |
| N8 | Legacy unpenalised MMM | not ported; R14 intercept only; a declared MMM context column is penalised | a second unpenalised slot (changes signed R14) |
| N12 | Surface scalers | all candidates at the guard cut (mirror of the test pass) | per fold, rows outside g's block |
| N14 | Low-tree rows | recorded and printed (kept share under 10%) | a minimum kept share, else trees-off |
| N15 | Legacy comparison | harness check on the toy with counts, never a selector | none |
| N16 | Error target of the fold GLS models | built once from the fit-cut bank's answers on the guard-cut donor rows, as grids (L6_ANSWERS_DISCLOSURE) | per-fold answers from the inner-cut bank |
| N17 | Season in Z (fix phase) | Z holds the tree features only; season reaches the router as context (H3, G-KEYS). Smoke pools still hold 36% of rows within +-1 month of the issue month (uniform 25%) | append the standardised router context to Z, as the legacy FC held month, doy_sin, doy_cos (adaptation.py:1443-1447) |
| N18 | Legacy replay harness (fix phase) | BUILT by owner ruling V7 (2026-10-19), outside the engine: D:/treeroute/coral_build/replay/run_replay.py; result in replay/REPLAY_REPORT.md (PASS, P0-P5). Before V7: not built | (done) |

---

## REVIEW LOG (2026-10-19)

GS = grid-safety review, LK = leakage review, FS = feasibility review.

| Issue | Outcome | Where / reason |
|---|---|---|
| GS1 verdict reference | fixed | section 4 states the donor-row median is the verdict reference |
| GS2 lead pool horizon (lead 0's cuts) | fixed | ATTENTION, 0, 1.2, 1.3, 6: the pass's own bank cut; logs carry lead L |
| GS3 GLS per fold not buildable | fixed | 3.6 uses the additive fold entries of SPEC_TABLE_MODE.md 5.11-5.12 |
| GS4 six contradictions | fixed | ATTENTION; this spec follows SPEC_TABLE_MODE.md 4.0. The old "three departures" block is gone |
| GS7 G1 on candidates | fixed | 1.2 step 1 |
| GS14 keyword forwarding tests | fixed | 8 test_solve_unpenalised |
| GS16 memmap fallback, 512-row checkpoints | fixed | 7: both deleted; a failed RAM wait refuses (Q1) |
| LK1 scalers fitted on rows after the issue date | fixed | 1.3 (constants on candidates at or before the pass's own cut); 3.7 |
| LK3 probe of test pass | fixed | 8 refers to SPEC_TABLE_MODE.md 6.3 |
| LK5 guard-surface fallback donor rows | fixed | 3.7 names the guard-bank DonorRows |
| LK10 harness reads test labels | fixed | 8: toy only, refuses any other package |
| FS1, FS2 GLS and fold context | fixed | 3.6 |
| FS3 disagreements | fixed | ATTENTION; 1.2 step 4, 1.3, 2, 4 |
| FS6 mis-wired pool | fixed | 0 and 1.2 (issue days from `key_issue`); 1.4 pools saved; 8 audit |
| FS9 N13 and N5 signed | fixed in part | N13 deleted (signed R14/R13). N5 kept: R13 signs c and the GLS model per fold, not the fallback median |
| FS12 sizes for 83 groups, wall time | fixed | 7 |
| FS13 checkpoints / memmap | fixed | same as GS16 |
| FS14 float32 vs float64 in the harness | fixed | 8 |
| N1, N2, N4, N6, N9, N10, N11 | merged | now one text in SPEC_TABLE_MODE.md 4.0 and items O5, O8, O9, O19 there; N9 is signed |

Counts for this file: 18 issues fixed (one in part: FS9, where N5 stays an owner item because no signed rule covers
the fallback median), 0 rejected. The shared issues are also counted in SPEC_TABLE_MODE.md.
