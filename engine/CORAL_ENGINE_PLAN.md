# Coral in the engine: the build plan

Written 2026-10-19. Revised the same day after three skeptic reviews (REVIEW LOG at the end). Read-only design. Nothing here has been built or run.
Paths are relative to the project root `C:\Users\<user>\Desktop\data set for reserch paper\` unless they start with `D:/`.
"engine/..." means a file under the engine folder. Owner rulings override plans.

**ATTENTION, read first:**
- **BLOCKER 1 (G-DERIVED).** The deep check rebuilds every engineered column from its declared operation and BLOCKs an operation it does not know (engine/treeroute/check/guards.py:1263-1285). The known operations take exactly one source column (engine/treeroute/check/recompute.py:230-241). Coral's DHW, hs_max, n_above_mmm (SST against an expanding-window MMM), the Hobday mhw_* columns and the cyc_* columns cannot be declared that way. The freeze needs a green deep check (engine/treeroute_report/freeze.py:12; ruling M2). Route to choose: Q16.
- **BLOCKER 2 (empty groups).** The bank fit refuses a group with no rows (engine/treeroute/fit/bank.py:200-206). Some ecoregions have no visit at the inner-fit end or the train end (measured, section 3C2). Rule to choose: Q18.
- Coral cannot start today. The engine refuses an events table at the streamed census (engine/treeroute/derive/census.py:254-261) and at about 30 later places (section 2).
- Engine hashes: fire, NDVI and defo ran under engine 65a177bc (engine/PENDING_PARTS.md:248, 267, 291). PM2.5 ran under 7b508557 (engine/PENDING_PARTS.md:156) and is covered by the R1/S2 no-op chain (engine/OWNER_RULINGS_2026-10-06.md:68, 77). Any engine edit moves `engine_code_sha256` (engine/treeroute/runs/fingerprint.py:138). The new engine must prove the same bytes on the four grid smokes (section 3B).
- Conflicts with signed rulings that need an owner answer before coral's pre-registration: pool mode vs C2 c and G5 (Q2), the guard and decline objects (Q4, Q17), which sites are scored vs ruling L1 / R18 (Q5), the test window end (Q6), GLS per fold vs ruling L5 (Q12), the ruled coral rivals C11 c / C12 (Q19).
- No shipped coral number can be compared with an engine coral number (section 5).

---

## 1. SUMMARY

- "Adding coral" means teaching the generic engine two new things: an **events** time line (irregular survey dates, counted in days) and the **neighbour** router (each survey borrows from nearby, earlier labelled surveys). Then we write one coral dataset package. No engine file may name coral (engine/tests/test_nonames.py).
- Ruling H1 fixes the shape: neighbour router, events, leave-one-ecoregion-out, built after the four grid runs, with its own pre-registration Part (engine/OWNER_RULINGS_2026-09-28.md:94). Ruling I1 fixes the leads: nowcast, 183 days, 365 days (engine/OWNER_RULINGS_2026-09-28.md:104).
- Main pieces: (A) engine events path plus neighbour router, (B) proof the grid smokes do not move, (C) the coral package, (D) gates, pre-registration, freeze, run, (E) the coral report table.
- Rough total: about 22-25 agent days for the engine (A), about 28-33 agent days for the whole build. Machine time: about 1 hour for feature tables and 2-10 hours for the headline run (estimate, unverified). This is far above APP_PLAN's M6b figure (2.5-3.5 d, APP_PLAN.md:800) and its M8 figure (APP_PLAN.md:802).

Analogy: the engine today is a train timetable. Every unit has a seat at every station (a dense grid). Coral is a taxi service: trips happen at odd times, most passengers ride once, and you predict a trip by looking at similar trips nearby that already happened.

---

## 2. WHAT EXISTS AND WHAT IS MISSING

### 2a. Engine

| Piece | Status | Where |
|---|---|---|
| R1 detects events; R2 season key = month of event | built | engine/treeroute/derive/rules.py:322, 463-464 |
| R3 for events = last year with any joined row (F2) | built | rules.py:569-583, 620-622 |
| R10 leads 183 / 365 days; R11 day cuts (one fit cut and one guard cut per lead) | built | rules.py:1009-1061; engine/treeroute/timing/cuts.py:62-89, 202-215 |
| R12 router kind = neighbour when h < 2 | built | engine/treeroute/derive/router_rules.py:149-196 |
| R13 leave-one-group-out folds; R14 neighbour design (150 / 50 / 12) | built (rules only) | router_rules.py:213-237, 296-300; engine/treeroute/engine_constants.py:149-187 |
| Day ordinals, one-day periods | built | engine/treeroute/io/steps.py:206-236; engine/treeroute/timing/calendar.py:193-194 |
| Donor-row median baseline; "no normal" scoring | built | engine/treeroute/report/metrics.py:131, 558-565, 665, 909-913 |
| Overlap blocks with a no-grid spacing rule | built, but refuses 1-site groups | engine/treeroute/split.py:732-735, 774-878 |
| Streamed census on a day line | **missing** (refuses) | census.py:254-261, 300-305; engine/treeroute/pipeline/stream.py:75-82 |
| derive_all for events | **missing** (M8 raise) | engine/treeroute/derive/orchestrate.py:432-434; census.py:1207-1209 |
| `is_events` passed to R3/R10/R17/R20 | **missing** (hard-coded False) | orchestrate.py:467, 475, 511, 558; census.py:1237-1340 |
| R17 for events reaches the neighbour "empty" spec | **missing** (raises first) | router_rules.py:338-346 |
| As-of driver join at the issue date | **missing** (stub) | engine/treeroute/io/joins.py:347-352 |
| Feature hook with the issue date | **missing**; today `build(frame, keys)` is called once | engine/treeroute/pipeline/data.py:17, 669; APP_PLAN.md:117, 179 |
| G-DERIVED recompute of multi-source columns | **missing** (one source per operation) | check/recompute.py:230-241; check/guards.py:1263-1285 |
| Event label vault (as-of view, locks) | **missing** (refuses grid=None) | engine/treeroute/labels/vault.py:180-182 |
| Row ids not tied to grid position | **missing** (FitContext refuses a non-DenseGrid) | engine/treeroute/pipeline/stages.py:106-130; fit/context.py:380-389; fit/bank.py:515-535 |
| Bank fit for a group with no rows at a cut | **missing** (refuses) | fit/bank.py:200-206 |
| Neighbour router (pool, route, trees-off) | **missing** (stubs, approved signatures) | engine/treeroute/route/kinds.py:1233-1258; pipeline/router.py:102-112 |
| Fold contexts for the decision surface | **missing** (M8 raise) | engine/treeroute/fit/context.py:742-750; fit/bank.py:599-602 |
| Ladder in day leads | **missing** (M8 raise) | engine/treeroute/pipeline/ladder.py:333-353 |
| Plumbing check for a kind with no normal | **missing** | engine/treeroute/layer/decide.py:577-604 |
| Verdict reference for neighbour | built path reused: own-link trees-off (Q17); donor-row median printed beside | pipeline/passes.py:1102-1103; ladder.py:1164-1165 |
| Report roles for neighbour | **missing** (needs guess_normal, last5) | engine/treeroute_report/table.py:82-83, 211 |
| Per-event report stratum (programme) | **missing** (static strata only) | engine/treeroute/pipeline/data.py:24-30, 878-892 |
| Deep check on events | **missing** (refuses) | engine/treeroute/check/deep.py:585-592, 714-750 |
| LIMITS text in plan.json / run_record.json | says neighbour, day leads and day time lines are refused | engine/treeroute/pipeline/run.py:139-150, 1144, 1306 |
| `_proposed/` neighbour code | contracts only, all raise | engine/treeroute/_proposed/loro_additions.py:28, 760-789 |

### 2b. Package and data

| Piece | Status | Where |
|---|---|---|
| Target y per survey | recipe exists, not stored | coral_smoke_regress.py:56-77 (GCBD SQLite) |
| Events keys (lat, lon, eco, yr, mo, dy) | on disk, 23,258 rows, 1986-2020 | D:/coral/target/events_dated.parquet |
| `date` column | defect: day clamped at 28 (1,324 events) | CORAL_STATE.md:148-151 |
| Survey day | defect: unknown day filled with the 15th (Donner 100%, Safaie 86%) | CORAL_DATA_AUDIT.md:65-69 |
| `gcbd_bleaching_joined.parquet` | unusable (no site, no date) | D:/coral/target/README.md |
| Daily SST per site | on disk: per-site series that end at each site's last survey year; uncompressed npz, so a memory map needs manual byte offsets (np.load ignores mmap_mode for .npz) | D:/coral/drivers/sst_compact_all.npz (889 MB); completeness review measurement |
| ENSO, DMI, IBTrACS, CRW mask, GHS-POP | on disk | D:/coral/drivers/climate, static, ghspop |
| ENSO anomaly used by the grid packages | shared ERSSTv5 store | engine/datasets/_stores/index_facts.yaml; engine/datasets/pm25/ban.yaml:395-398 |
| Lead-183 feature table | **missing** (only L0/30/90/180/365) | project root forecast_features_L*.parquet |
| A coral package folder | **missing** | engine/datasets/coral/ (not created) |
| Coral ban review (Q34) | **not done** | HEADLINE_QUESTIONS_AND_FIXES.md:86 |
| D:/coral protected | **no** | D:/treeroute/registry/protected_roots.txt (D:/adaptation is) |
| Coral pre-registration Part | **not written** | engine/PREREGISTRATION_DRAFT.md:55-56 leaves coral out |

---

## 3. BUILD LIST (in order)

Rule for every engine item: new code runs only when the data says `cadence.kind == irregular` (from R1) or the derived router kind is `neighbour` (from R12). Grid packages never reach it. No problem name, year or drive letter in engine code. An events package whose R12 gives h >= 2 (per-unit or region kind) still refuses at R17 (router_rules.py:338-341, M8); this is written as a LIMITS line.

Size key: S = under half a day, M = about 1 day, L = 2 or more days (agent time).

### A. Generic engine additions

| # | Item | Files to touch | What it does | How it stays generic | Tests | Size | Can it move grid outputs? |
|---|---|---|---|---|---|---|---|
| A1 | Events time line | io/steps.py:336-340; pipeline/stream.py:72-82; derive/census.py:254-305; pipeline/data.py:351, 521-628 | Day ordinals as the time index. Year windows become first/last day of a year. Census reads `year + day_of_year` keys. (unit, day) keyed rows. Day coordinates are offset to be at least 0 before the `unit << 20 | coordinate` driver key is packed, or the run refuses loudly (stream.py:72; steps.py:204-206; pre-1970 days would be negative, unverified whether any coral store has them) | Branch on R1's events flag | Six toy event packages (APP_PLAN.md:802), incl. irregular repeat visits and a presence-only refusal | M | No, if the step path is untouched. Census record layout for grids must stay the same |
| A2 | derive_all for events | derive/orchestrate.py:176-327, 422-558; derive/census.py:1207-1340 | Pass R1's events flag to R3, R10, R17, R20. Label reads on day ordinals | Flag comes from R1 | test_derive_all.py:336-345 rewritten; expected_derived toy | M | derived.json of grids must stay identical (passing a computed False is value-neutral) |
| A3 | R17 for neighbour | derive/router_rules.py:338-346 | Return the empty history spec for neighbour before the events raise. Per-unit and region events still raise | Reads derived kind | test_derive_loro_rules.py:255-260 | S | No |
| A4 | As-of driver join and as-of feature build | io/joins.py:347-352; pipeline/data.py:669 | Join each driver at the row's issue date. Refuse any value whose content ends after the issue date. On the events path only, pass the issue date through the keys dict (`keys['issue']`). The grid call stays `build(ordered, keys)` byte for byte. The engine checks each output against its declared window and stamp at the issue date | Reads store window/reach facts (R8) | 1:1 join test; look-ahead refusal test; **look-ahead canary**: re-run build with all source data after the issue date removed, outputs must be equal | M | No (new path only) |
| A5 | Event label vault | labels/vault.py:180-182; pipeline/stages.py:77-103 | One row per visit keyed (unit, day): validity, donor labels, as-of view ("k-th previous visit before the issue date"), locks, open test labels | grid=None means events | test_vault.py:37-41 rewritten | L | No |
| A6 | Event row index | pipeline/stages.py:106-130; fit/context.py:380-389, 631; fit/bank.py:515-535; fit/pool.py; fit/weights.py:98-141 | Event rows get a row index and a row-to-group map. R20 key = unit + event date + issue date (unit_rules.py:459). The event row index is a separate object. Grid code is untouched | Cadence-gated | Byte check on grid bank order | L | **Yes, high risk** if grid code is touched. It must not be |
| A7 | Neighbour pool (strict) | route/kinds.py:1244 `neighbour_pool_loro`; fit/tables.py:936-959 | **Pool = labelled rows with `label_usable(day, window_end, cut)` true (cuts.py:92-102).** Cut = the lead's R11 fit cut (`test_first_day - L`; the train-end last day at lead 0) on the test pass, and the R11 guard cut on every decision or guard surface (cuts.py:62-89). Never a per-row issue date (that is Q2 d). The caller filters the candidates, as the approved contract says (loro_additions.py:760-786). 150 nearest by great-circle distance, then 50 nearest in tree-feature space. The standardisation, the 50-nearest similarity and the donor-row-median fallback all use the same cut. Similarity uses the lead-L features for both the scored row and the pool rows (adaptation.py:1790-1799). Under 12 rows → `None`, caller uses the donor-row median and counts it in `n_rows_pool_fallback` (kinds.py:182). Returns the drop list: the row's block and every pool group's block (R14 default) | Constants C11 (150/50/12) already shared. No signature change | Assert no pool label after the R11 cut; assert no pool label on the scored row's own event day; pool-fallback count test; drop-list test | L | No (stub today) |
| A8 | Neighbour router and trees-off | route/kinds.py:1233, 1255; pipeline/router.py:102-112, 642-702; uses route/solve.py:61-330 | Per row: intercept (unpenalised) + context + remaining trees, block ridge on the 35-point grid (C12). Trees-off = intercept + context fit on the same pool. Its identity version is the decline target (R16). `trees_off_neighbour`, `neighbour_pool_loro` and `route_neighbour_loro` keep their approved parameters (test_route_kinds.py:316-330). The superseded `neighbour_pool` and `route_neighbour` keep raising | Reads R14 design | test_route_kinds.py:292-307: only the M8-raise test changes; toy pool solve | L | Only if route/solve.py is edited. **Call it, do not change it** |
| A9 | Pool tables across groups | pipeline/router.py GroupTables; passes.py:522-550; run.py:628-670 | Pools need other groups' rows. Keep all tree answers in reach for neighbour runs (about 15k rows). The all-answers build calls `_refuse_ram(wait=True)` with an estimate (run.py:494; ruling Q1) | Kind-gated schedule | tables.json for grids unchanged | M | tables.json of grids, if the schedule is shared. Gate it |
| A10 | Leave-one-group-out decision surface (R13) | pipeline/passes.py:731-798; layer/decide.py:820-823; fit/context.py:742-750 `for_fold`; fit/bank.py:599-602 | One bank cut at the inner-fit end. Fold g drops g's block and its pool groups' trees (with correctors and placebos), no refit. c and GLS per Q12. `decide()` takes the stacked fold surface. Folds with no inner-score rows give nothing (about 34 non-empty folds) | Folds from R13 | Fold-drop test; "no fold row sees its own block" test | L | No |
| A11 | Overlap blocks for point sites | split.py:732-735 | A one-site group needs a spacing. Option in Q8 | Rule reads the static table | 1-site and 2-site toy groups | S | No (grids have grid indices) |
| A12 | Census, R30, checkpoints, RAM wait, LIMITS for events | pipeline/stream.py:427-476; io/lastvalue.py:132-150; pipeline/run.py:131-160, 494, 628-720, 1023-1045, 1223-1253; runs/checkpoint.py | Count missing shares on event rows. Skip the last-value fill for events (not defined, see risks). Checkpoint keys and RAM plan in rows, not steps. The fold surface saves one checkpoint record per fold (P1 machinery, key = engine + package + fold). Every in-run RAM check waits (ruling Q1). **LIMITS:** edit the 4 lines that say neighbour, day leads, day time lines and time-varying strata are refused (run.py:139-140, 145, 147-150); add lines for the neighbour kind's departures (for example A9's all-tables schedule) and for "events with h >= 2 refuse (R17)" | Cadence-gated | Interrupt during the fold surface, then resume: result equals an uninterrupted run (the P2 pattern) | M | The `limits` field of plan.json and run_record.json changes for grids too. This is an expected, disclosed difference in B3 |
| A13 | Ladder in days | pipeline/ladder.py:333-353, 420-494, 660-672; passes.py:436-510 | Leads 183 and 365. Features as of the issue day. Lead 0 join must equal the nowcast join byte for byte. **Each lead L >= 183 fits its test bank, correctors and placebos at the fit cut (`test_first_day - L`), and its guard bank at the guard cut (`inner_score_first_day - L`) (H2).** Lead 0 reuses the nowcast bank (train end) and the inner-cut bank. Total 6 bank cuts. The pinned placebo is built at 365 days (R29) | R10 gives the leads | test_pipeline_ladder.py:522-529 rewritten | M | No |
| A14 | Plumbing and verdict for neighbour | layer/decide.py:577-604; passes.py:1102-1103; ladder.py:1164-1165; passes.py:980-995 | Neighbour G-PLUMB: trees-off equals a reference least-squares fit of the same pool (route/solve.py reference); the base point reproduces the un-swept route. **Verdict reference stays the own-link trees-off** (as grids). The donor-row median is printed beside it, and is the reference for the R32 hit tolerance and MAE skill only (HEADLINE_QUESTIONS_AND_FIXES.md:168-171, Q15 a there). Q17 if the owner wants otherwise | Kind-gated | decision_checks toy | S-M | decision_checks.json for grids only if shared code changes. Gate it |
| A15 | Report metrics for events | report/metrics.py:415-470; engine/treeroute_report/table.py:82-83, 211; pipeline/data.py:24-30; tests/test_nonames.py:16-17 | No cell x month normal, so **anomaly R2 is replaced by**: MAE, skill against the donor-row median and against predict-zero, R2 about the donor-row median, hit rate against R32's tolerance, and corr2. Persistence and damped persistence (on (visit, previous visit) pairs, R31) only on rows with an earlier visit. A per-event report stratum (from the catalog's `report_stratum` role) for reporting only. Every report threshold is derived from donor rows. No programme name in treeroute or treeroute_report code. Add treeroute_report to the G-NONAMES scan | Kind-aware roles | test_report_metrics.py additions; nonames scan on treeroute_report | M | The score files of grids if shared code changes. Covered by B3 |
| A16 | Deep check for events | check/deep.py:585-592, 714-750, 803-814, 1220-1233; check/quick.py:358 | Event versions of G-DERIVED, G-HIST, G-CALENDAR, G-LINEAGE, G-SUPPORT (presence-only refusal then runs) | Cadence-gated | test_check_guards.py | M | No (off the run path) |
| A17 | R18 for the events cadence | derive/unit_rules.py:220-250 | Q5 a: every test-window visit of every group is scored. A candidate unit is any unit with a dated event row (reads existence only, never labels). Needs an owner ruling that supersedes L1 / R18(2) for the events cadence | Cadence-gated | toy: scored rows = all test-window visits | S | No |
| A18 | R3 event branch (only if Q6 a) | derive/rules.py:620-622 | The last year must hold at least half the median yearly joined count. Reuses C3's "half" share (`COVERAGE_GROUP_SHARE`); no new constant | Cadence-gated | toy with a near-empty last year | S | No |
| A19 | Groups with no rows at a bank cut (only if Q18 a) | fit/bank.py:200-206; fit/tables.py | A group with 0 rows at a cut trains no trees at that cut, still lends and receives pool rows; counted and flagged | Cadence-gated | toy group with 0 rows before the inner-fit end | M | No |
| A20 | Route for the SST-relative, Hobday and cyclone columns (Q16) | Q16 a: package ingest + A4 join; Q16 b: check/recompute.py | Makes G-DERIVED pass on coral's columns | Q16 a: no engine change; Q16 b: generic multi-source operations | deep check green on a toy and on the R21 smoke groups | M | Q16 b only, if shared recompute code changes. No-op gated |
| A21 | Coral rivals (only if Q19 a) | rival code for events (path unverified; rival_data.py:53, 309 is legacy) | Lagged NOAA DHW (row-paired), CRW 4-month Outlook (leak-free), hgb_l1, damped persistence on repeat-visit rows (C11 c, C12, F67) | Rivals read the package's own stores | rival-row toy | L | No |

**Guard and decline objects (Q4).** Today a forecast lead whose pinned arm fails the guard falls back to the identity trees-off, while the guard compared it with its own-link trees-off (engine/treeroute/layer/decide.py:527-550; ladder.py:857, 905; seen on fire, engine/PENDING_PARTS.md:274-276). The same mismatch exists at the nowcast: R27 checks each arm against its own-link trees-off, but a decline adopts the identity trees-off (APP_PLAN.md:241, 262). The decline target is defined in layer/arms.py:227-255. A kind-gated fix (Q4 b) touches layer/arms.py, pipeline/ladder.py:857, 905 and the D86 docstrings in decide.py:520-576; `forecast_adoption` has no kind argument (decide.py:527).

Estimated engine total: about 22-25 agent days (10 M + 5 L + 5 S-ish, plus A21 if Q19 a; estimate).

### B. The no-op proof (grid runs must not move)

1. Before any edit, save the four grid smoke outputs from the live engine 65a177bc as the "old" set.
2. After the build, run the same four smokes on the new engine.
3. Gate (ruling R1 wording, engine/OWNER_RULINGS_2026-10-06.md:68): byte-identical on every prediction and score file (score_by_group.csv, score_pooled.csv, per_group.csv, per_year.csv, jackknife.csv, verdict.json, adoption*.json, ladder/*), derived.json, tables.json, decision_checks.json, and every JSON record that carries no hash, time or path. Only hash-bearing fields may differ, plus the disclosed `limits` field of plan.json and run_record.json (A12). Also: re-running `treeroute report` on the four headline folders must give byte-identical D:/treeroute/runs/_headline_tables/*.
4. Add one full-width probe on one group per grid package, or a code proof that the new branches never run on them (APP_PLAN.md:21, 802).
5. If all pass, the four finished headline runs keep their numbers. fire, NDVI and defo keep 65a177bc; PM2.5 keeps 7b508557 under the R1/S2 chain. Disclose it as rulings R1 and P2 did (engine/OWNER_RULINGS_2026-10-06.md:54, 68).
6. If any byte differs, stop. Either fix the leak into the grid path, or the affected packages re-run (engine/treeroute_report/freeze.py:75-78).
7. `freeze verify` will report drift on the grid locks because `engine_code_sha256` and the report-tooling hashes changed (treeroute_report is outside the engine hash, fingerprint.py:22, but inside the lock, freeze.py:65-66, 78). The disclosure note says why that is expected.

Size: S-M (about 1 agent day; four smokes on this machine).

### C. The coral package (engine/datasets/coral/)

**C1. Files**

| File | Content |
|---|---|
| dataset.yaml | name, version, owner, description, stores (target `{group}` template, static, drivers), includes with sha256 (engine/treeroute/package/schema.py:246-262) |
| ingest/build_target.py | Builds the target store from the GCBD SQLite with the legacy recipe (coral_smoke_regress.py:56-77): Reef_Check Population rows, mean of S1-S4; AGRRA/FRRP/McClanahan/Donner Percent_Bleached; drop Kumagai, Safaie; drop y outside [0, 100]. Date rebuilt from yr/mo/dy. Writes `date_precision` (day / month; month when the day was imputed as 15, CORAL_DATA_AUDIT.md:65-69). One parquet per ecoregion in a new store (for example D:/coral_target/{group}.parquet). Also writes a (site, date)-keyed programme store, declared with role `report_stratum`. Duplicate (site, date) rule from Q7 |
| ingest/build_static.py | One row per site: unit id, group id, lat, lon (EPSG:4326). Unit id = `{group}_{lat}_{lon}` at 4 decimals (APP_PLAN.md:115). Group id form from Q21. Drop the 3 rows with no ecoregion |
| ingest/target_reader.py | Returns only the key columns and y (engine/treeroute/check/quick.py:79). No `pos`, `side`, `dy` |
| ingest/build_drivers.py | Writes dated per-site driver stores: daily SST per site (reads sst_compact_all.npz one site at a time by byte-offset memory map), ENSO anomaly and DMI as monthly series, IBTrACS track points, CRW mask (static), GHS-POP epochs. Under Q16 a, also the SST-relative, Hobday and cyclone columns as dated stores with their own facts |
| features/build.py | `OUTPUTS` and `build(frame, keys)`; on the events path the issue date arrives in `keys['issue']` (A4). Every column computed from data dated strictly before the issue date (C4). Missing values are written as NaN |
| catalog.yaml | Keys (site, ecoregion, year, day_of_year). Target: legal_range [0, 100] with source; window 1 day (whole month for `date_precision = month`, Q20); stamp event_date. Programme as report stratum. MMM and abslat as router context. Every column with explicit `co_measured_with_target` |
| store catalogs | Per column: units, cadence, window and reach (`reach_after_max` for CoralTemp and the DMI window, signed, Q22). Caps, not fill values: `days_since_dhw4` and `cyc_days_since_close` capped at 3,650; `cyc_mindist` capped at a declared km bound ("none within cap" = cap). The codes 99999 and 9999 are **not** declared as fill values, because G-SENTINEL masking plus R30's 0-fill would flip their meaning (APP_PLAN.md:265, 606). GHS-POP R2023A: a per-epoch content date from GHSL_Data_Package_2023.pdf and the input metadata xlsx (ruling N2, engine/OWNER_RULINGS_2026-10-06.md:37) |
| ban.yaml | One verdict per non-key column (C3). No `keep_unreviewed` at freeze (freeze.py:41-45) |
| split.yaml | `excluded` (Q8 / Q18 result). `seen_during_design` = every ecoregion that was a pilot, donor or test group in Parts 417-558: the 10 pilot ecoregions (CORAL_STATE.md:59), fullscale_split.json donors and test groups, the 74-ecoregion main split, the dbl2005 board; listed from the saved prediction files. `continuity_groups` = the old 74 main-split held-out ecoregions (ruling D, engine/OWNER_RULINGS_2026-09-28.md:51; APP_PLAN.md:93, 122) |
| exceptions.yaml | disclosed_defect: date clamp; sid 10321889 latitude sign (CORAL_STATE.md:148-159); Donner/Safaie day imputed as 15 (CORAL_DATA_AUDIT.md:65). provenance_flag: programme confound (CORAL_STATE.md:30-34). Departure: MMM (an absolute temperature) in router context |
| AUDIT_CHECKLIST.md | Signed: lineage per source, fill codes and caps, label grain, the four harmonisation choices (D:/coral/target/README.md), unit definition, unit set not chosen from labels. GEBCO and SRTM15+ bathymetry: banned, lookahead (optical inversion of the reef after the survey; CORAL_STATE.md:111-114). Survey-recorded depth only, if ever used |
| expected_derived.json | R1 irregular, R2 event_month, R3 Y_end, R4 Y0, R5 test years, R7 inner windows, R10 183/365 days, R12 neighbour, R22 links, LORO group count, groups with test-window rows, groups with inner-score rows, scored-group count |

**C2. Split.** Groups = ecoregions, leave-one-ecoregion-out (H1). There is no donor/test list: split.yaml cannot hold one (schema.py:477-490). Group count is derived (97 ecoregions have labels; 94 have SST features). Test window comes from R3/R5 (Q6). Measured by the completeness review on the GCBD recipe, before the SST filter: groups with test-window (2016-19) rows: **42 of 97** (2,616 visits); groups with inner-score (2013-15) rows: **34**. Groups with 0 visits at the inner-fit end: 4; at the end of 2015: 3. A quick cross-check today on events_dated.parquet (all 112 eco codes, before any y filter) gives the same picture: 47 groups with 2016-19 rows, 37 with 2013-15 rows, 3 groups with no row by 2012 and 2 by 2015. So "every group is tested" (ruling D) does not hold for coral: the jackknife, R33 and the R18 floor run on the scored groups only.

**C3. Column verdicts** (science-rules review; sources: CORAL_EXPERIMENTS.md:57, 1751-1755; coral_forecast.py:121-210; coral_ghspop_ab.py:63-115). Every verdict below is signed by the owner (Q9, Q10, Q22).

| Columns | n | Verdict | Why |
|---|---:|---|---|
| dhw, hs_max, n_above_mmm, n_above_mmm1, cool at 30/56/84/90/180/365 days | 30 | keep | Relative to the leak-free MMM; windows end before the cut. G-DERIVED route: Q16 |
| days_since_max_hs, slope_90 | 2 | keep | Short window; a slope is not a level |
| Hobday mhw_* (9 columns) | 9 | keep | The one confirmed driver win. Declare the 365 cap on mhw_since_end |
| mhw_thr_gap | 1 | watch (Q22) | Quasi-static site climate |
| lifetime_dhw, n_dhw_ge4_before, max_dhw_before | 3 | ban trend_proxy or watch (Q10) | Running totals since 1985 grow with the year (pooled r with year 0.83-0.93) |
| n_dhw_ge8_before | 1 | watch | Same family, weaker |
| days_since_dhw4 | 1 | keep, fixed cap 3,650; watch (Q22) | 99999 on 38% of rows (coral_forecast.py:147). A fixed declared cap, no data dependence. Watch: its observable maximum grows with record length (a partial clock) |
| nino34_lag0/3/6 | 3 | **ban structural** (Q22) | Absolute ERSST V6 Niño-3.4 (nina34.txt header; CORAL_STATE.md:152-154): an absolute temperature that carries the season key (calendar month alone R² 0.186). Replace with the shared ERSSTv5 anomaly at the R-A lag 2 (engine/datasets/_stores/index_facts.yaml; engine/OWNER_RULINGS_2026-09-28.md:24) |
| dmi_lag0/3/6 | 3 | keep after a signed window bound (Q22) | HadISST anomaly; window unknown, and R8 refuses an unknown window at lag 0 (APP_PLAN.md:228). Precedent: R-B signed tni's bound |
| cyc_* (16 columns) | 16 | keep | Dated tracks, windows before the cut. Fixed caps (C1), no fill codes. G-DERIVED route: Q16 |
| mask_is_water, mask_land_frac_7x7 | 2 | ban, or keep with a written exception and content date (Q22) | Static geography as a main effect (CORAL_STATE.md:106-109); `mask_for_sst_clim_mmm` is a data-product mask, not a physical map under N2 (coral_extra_drivers.py:128) |
| month, doy_sin, doy_cos | 3 | ban as tree columns (G-KEYS), keep as router context | APP_PLAN.md:609; pm25/ban.yaml:807-810 precedent. Read date: Q11 |
| pop_ratio_5_50, pop_grad_5_25, pop_growth_20y | 3 | keep, freeze cadence, after the content-date check (Q22) | Rebuild from the last epoch at or before the issue year, no interpolation (guards.py:439-445). R2023A files (dated 2023) may carry later content; G-EPOCH checks the epoch content dates against every fit cut (N2) |
| pop level columns (3) | 3 | ban structural | Location fingerprints; the 77-vs-80 defect (Q9) |
| mean_*, std_* (12), lat, lon | 14 | ban structural | Absolute-temperature and location ban (Part 415) |
| abslat, mmm | 2 | ban as tree columns; keep as penalised router context | APP_PLAN.md:74, 356. MMM in context is a disclosed departure from the absolute-temperature ban; legacy context did not include it (coral_forecast.py:228) |
| mmm_n_years | 1 | ban trend_proxy | r with year 1.000 |
| pos, side, box, byr, S1-S4, sev, prev | - | ban label / not read | Label twins and the old split |

Result: about 66-73 tree columns (depends on Q9, Q10 and Q22), plus context (season, abslat, MMM).

**C4. Feature script, date safe at each lead.** For each row and lead, the issue day = event day minus the lead (0, 183 or 365). Every SST window, the MMM (expanding window, at least 10 years, epoch 1988.2857; coral_dhw_model.py:64-93), Hobday, cyclones and ENSO/DMI read only data dated before the issue day. POP reads the last epoch at or before the issue year. The engine verifies this with A4's stamp check and look-ahead canary; the script is not trusted on its own. The package writes NaN for rows with too little SST history (under 1,825 days before the issue day, coral_forecast.py:110-112); the engine then applies rulings H4 and S1 (left out, saved with a flag, counted per unit and lead; engine/OWNER_RULINGS_2026-09-28.md:97; engine/OWNER_RULINGS_2026-10-06.md:76). The 576 no-SST sites are disclosed with counts. The static `.fit` scan passes `np.polyfit`, because only fit / fit_transform / fit_predict / partial_fit calls are flagged (check/guards.py:62, 1316-1330). The G-DERIVED recompute is the real gate (BLOCKER 1, Q16). Legacy build time: about 9-10 minutes per lead plus about 5 minutes to load (CORAL_FORECAST.log). Peak RAM if loaded whole about 2.5-3 GB; reading per site by memory map keeps it far lower.

**C5. Target facts.** Bounds 0 to 100, cited from the survey protocol. Zeros kept (43.7% zeros). Because y is bounded, R22 offers identity, log(y+c) and arcsine links (APP_PLAN.md:151, 257; derive/rules.py:1273-1302). Arcsine is offered, not forced. MAE selects (Q37 a).

Package size: L (about 3-4 agent days, plus about 45 minutes of machine time for three leads; more under Q16 a).

### D. Gates and run

1. Owner runs the ingest scripts by hand, for example `py -3.9 datasets/coral/ingest/build_target.py datasets/coral`.
2. Owner then adds D:/coral and the new target store root to D:/treeroute/registry/protected_roots.txt.
3. Quick check: `py -3.9 -m treeroute check datasets/coral` (engine/treeroute/cli.py:103-149). R1 at check time reads only the first target file (check/quick.py:70-76), so it sees one ecoregion. Verify R1 on the real store before freeze.
4. Smoke: `py -3.9 -m treeroute smoke datasets/coral`. R21: first 4 groups in sorted order, 40 units each, 12 trees (engine/treeroute/derive/unit_rules.py:471-501). With numeric ids these are '1', '10', '100', '101', with 8, 0, 0 and 0 test-window visits (completeness review measurement). Q21 decides the id form; the 4 picked groups and their test counts are listed before freeze.
5. Full-width probe on 3 groups (ruling M1: the group with the most target rows plus the first 2 in sorted order). If the R21 groups hold fewer than about 40 test visits, this probe is the one that exercises scoring.
6. Deep check on the R21 smoke groups only (ruling M2, engine/OWNER_RULINGS_2026-10-06.md:10): `py -3.9 -m treeroute check datasets/coral --deep`.
7. Sign-off sheet for coral (copy of datasets/_tools/signoff_answers_TEMPLATE.yaml), then `apply_signoff.py --apply`, then repeat steps 3 and 6.
8. Write `engine/PREREGISTRATION_DRAFT_coral.md`: engine and constants hashes, package fingerprint, derived.json hash, lock file, the 7.2 test-exposure table (it states: "column set, link set and pool design were chosen with labels of the engine test window visible"; the 2016-19 rows of 24 ecoregions were scored before, APP_PLAN.md:310), the A7 disclosure with GLS and neighbour asymmetries, each item-13 flag as its own row, the LORO design (groups, blocks, units, distances) (APP_PLAN.md:731), per lead the guard reference, the decline object and their MAEs side by side, plus every Q answer in section 4.
9. Freeze coral alone: `py -3.9 -m treeroute_report.freeze datasets/coral --prereg PREREGISTRATION_DRAFT_coral.md`, then `py -3.9 -m treeroute_report.freeze verify` (freeze.py:3-7, 75-79).
10. Headline run, owner's own PowerShell, other programs closed:

```
cd "C:\Users\<user>\Desktop\data set for reserch paper\engine"
py -3.9 -u -m treeroute run datasets/coral
```
It resumes after a crash and refuses a finished run (cli.py:206-218).
11. Report: `py -3.9 -m treeroute report datasets/coral`. Log the result as a new Part in engine/PENDING_PARTS.md.

**Expected cost on this machine (estimate, unverified):**

| Item | Estimate | Why |
|---|---|---|
| Rows | about 14-15k visits after Q7 a, about 2.6k test-window visits, both before the SST filter | completeness review measurement |
| Banks | 6 bank cuts: 3 test-cut (train end, 183, 365) + 2 guard-cut (183, 365) + 1 inner-cut; up to about 97 groups x 100 trees, small trees | R11, R19, H2, A13 |
| Router | about 2.6k scored rows x 3 leads x 35 grid points x arms; each solve is a 50-row dual system | R14 |
| Time | 2-10 hours (M6b said 6-10 h, APP_PLAN.md:800) | fold surface (about 34 non-empty folds) is the biggest part |
| RAM | about 0.6-0.75 GB per table kind per bank cut; about 2.3 GB for plain + corrector + placebo (fit/tables.py:91); up to about 3-4 GB with every corrector link held (unverified); peak under about 6 GB | 15k rows x about 9,700 trees as float32 |
| Disk | under 3 GB on D: | answers, checkpoints, predictions |

Size: M (about 1-2 agent days, plus the owner's time to sign).

### E. The coral report table

No threshold or programme name below is hard-coded in code: strata and their values come from the catalog's `report_stratum` column, and thresholds come from donor rows (A15).

| Block | Rows | Notes |
|---|---|---|
| Primary: per programme | Reef_Check, McClanahan, FRRP. Donner and AGRRA shown with n only (test window: Reef_Check 2,646, McClanahan 218, FRRP 193, AGRRA 2, Donner 0; completeness review measurement) | Pooled numbers second, labelled as mixing programmes (F66, HEADLINE_QUESTIONS_AND_FIXES.md:430) |
| Verdict | printed per programme (jackknife over the groups holding that programme); the pooled verdict is labelled secondary | Pooled severe-tail skill is a source statistic (CORAL_STATE.md:29-34) |
| Each row shows | adopted arm, predict-zero, donor-row median, neighbour trees-off; MAE, R2 about the donor-row median, hit rate, corr2, skill vs predict-zero; n, zero share | Report bundle rule (MAE + R2 + hit rate) |
| R33 top-10% detection | within programme only, or labelled "source statistic, not severe-tail skill" | CORAL_STATE.md:29-34 |
| By magnitude | per programme value, ordered from the data | Labelled a target-defined diagnostic, not a headline |
| Flattening guard | mean prediction vs observed mean on rows at or above the donor-row upper quartile, for every arm | Part 443 undershot 52 vs 77 |
| Continuity | the old 74 main-split held-out ecoregions, alone, from the same run | ruling D |
| Rivals (Q19) | lagged DHW (row-paired), CRW Outlook (leak-free), hgb_l1, damped persistence on repeat-visit rows | C11 c, C12, F67 |
| Year-blocked control | not an engine row. Reason: every engine fit and pool ends at the R11 cut, so no label from a test year enters any fitted object; the legacy failure was donors sharing test years (CORAL_STATE.md:96-101). A harness-only year-blocked row may be added later, report-only | |
| DONORS-ONLY pool | harness-only, report-only, never selectable | CORAL_EXPERIMENTS.md:3790-3793 |
| Pool fallback | pool-fallback count per lead | A7 |
| Uncertainty | ecoregion jackknife at 1.96 (R34) over the scored groups. No event-clustered bootstrap in the engine (G-NODRAW; bootstrap over regions only) | |
| Leads | nowcast, 183, 365 on common survey ids only | 365 days worded as risk stratification |
| Per ecoregion | n, zero share, programme mix; never ranked by MAE | CORAL_EVALUATION_AUDIT.md:102 |
| Legacy side rows (Q2 b) | only in legacy_harness output, never in the engine report or table, labelled "uses post-cut labels" | |
| Wording | "given a survey on this date"; predict-zero wins on Reef_Check if it does; arcsine described as a trade | |

---

## 4. OWNER DECISION SHEET

| # | Question | Options | RECOMMENDED | Reason |
|---|---|---|---|---|
| Q1 | Run coral under the item-13 flags (APP_PLAN.md:350-359)? | a) accept all as a bundle; b) one by one; c) keep legacy settings (500 trees, 0.15, full pool) | **a**, with each flag as its own pre-reg row | They are the generic engine rules; legacy settings were chosen on test rows |
| Q2 | Pool mode. Ruling C2 c said full and rollout side by side (QUESTIONS_ROUND3_HANDOFF.md:246-264); G5 approved both pools with full limited to rows at or before each row's issue date (QUESTIONS_ROUND3_HANDOFF.md:513-515) | a) strict only (departs from C2 c and G5); b) strict headline (pool at the R11 cut per lead); full (G5: at or before the issue date) and rollout as legacy-harness side rows only, labelled "uses post-cut labels"; c) keep C2 c; d) per-row issue-date pool in the engine (G5's full, analogue of D54 a; needs a new ruling, because R11 lists router rows and G-FITCUT forbids labels after the cut) | **b** | The engine pool must respect the R11 cut. Side rows keep C2/G5 visible. The G5 legacy re-runs are approved but not run (CLAIMS_LEDGER.md:264); machine time unverified |
| Q3 | Close Q28-Q32's pool items (HEADLINE_QUESTIONS_AND_FIXES.md:238-256) | a) close by the strict design: Q29 folds use the strict pool; Q30 moot; Q31 own-group earlier rows are already allowed; Q32 moot in the engine (the pool uses the R11 cut per lead); b) keep them open for the harness | **a** | The strict pool plus day cuts answers them |
| Q4 | Guard and decline objects (decide.py:527-550; PENDING_PARTS.md:274-276). The mismatch is at the nowcast (R27 vs R16 decline) and at forecast leads (D86) | a) keep identical behaviour, disclose both; b) fix for the neighbour kind only: on a failed guard or a decline, fall back to the same object the guard compared with (own-link trees-off), at the nowcast and at every lead; c) fix for every kind now | **b**, and fix all kinds in the next engine version | Kind-gated, read from the data, so grid bytes stay identical. Files: layer/arms.py, pipeline/ladder.py:857, 905, decide.py:520-576 docstrings. c re-runs PM2.5 lead 12, NDVI and fire leads 6 and 12. Needs a signature because it departs from the 2026-09-24 decline ruling |
| Q5 | Which coral rows are scored (R18; most sites have one visit) | a) every test-window visit of every group (departs from ruling L1 / R18(2) for the events cadence; R18 candidates become any unit with a dated event row, existence only; A17; needs an owner signature); b) R18 as written (about 10 units per group by stride over units with a label at or before the train end); c) only sites with an earlier visit | **a**, with the revisited-only share disclosed | R18's unit pick leaves most picked sites with no test-window visit; option c would keep about 67% of test visits (measured before the SST filter); the neighbour router does not need a site's own history |
| Q6 | Test window end. R3's event branch (rules.py:620-622) takes the last year with any joined row (F2), so if the 45 rows of 2020 keep their SST it ends at 2020 and the window is 2017-2020 | a) new generic rule (A18): the last year must hold at least half (C3's share) the median yearly joined count (gives 2016-19); b) R3 as built (2017-2020); c) package drops 2020 rows | **a**, with disclosure | A rule read from the data; b scores a nearly empty year; c is a hand knob. The pre-registration must say the rule was written after seeing the yearly counts and that it decides whether 2016 (the largest year, 1,159 events) is a test year. The other window is printed as a pre-registered sensitivity row |
| Q7 | Repeat surveys at one site and date (3,089 pairs; 1,283 disagree) | a) average y per (site, date) as one visit; b) make the unit site + depth or reef id; c) keep the first | **a**, disclosed | Legacy already averaged per survey; a visit is the label grain. b is unverified to resolve them |
| Q8 | One-site ecoregions (8) in overlap blocks | a) generic rule: a one-unit group uses the median nearest-site spacing of all units; b) exclude them in split.yaml; c) merge with neighbours | **a** | Generic, keeps data, no hand list |
| Q9 | Column set: 77 or 80 (Q28) | a) 77 frame: 3 POP shape columns, levels banned; b) 80 (levels kept); c) both, 80 as a side arm | **a** | Levels are location fingerprints and "did nothing" (Part 452); the 80 was a coding defect |
| Q10 | Heat totals that track the year (lifetime_dhw, n_dhw_ge4_before, max_dhw_before, n_dhw_ge8_before) | a) all watch; b) ban the three strong ones as trend_proxy, watch n_dhw_ge8_before; c) ban all four | **b** | Same rule the grid packages used for year clocks; they are running totals since 1985 |
| Q11 | Season columns at a lead (ruling H3 puts context at the issue step) | a) follow H3 for coral; b) for the events cadence, read key-derived calendar context at the event date; c) drop season context | **a** | Follows H3. Each lead is a separate pass with a fixed L, so the issue-day season is a fixed shift of the event season; b gains little and would be a departure |
| Q12 | GLS weights and c for the neighbour folds | a) L5: out-of-bag sigma on all groups' bank rows; b) R13 / R25: a weight forest fitted per fold on rows outside the fold's block; c) both: out-of-bag sigma computed inside each fold; d) no GLS arms for neighbour | **c** | Keeps L5's object (engine/OWNER_RULINGS_2026-09-28.md:63) and R13's fold honesty (APP_PLAN.md:238) |
| Q13 | Corrector arms on coral (record says none; adaptation adopted link_corrector) | a) engine offers them as for grids; b) none for neighbour | **a** | Plug and predict; the selection decides, the pre-reg says so |
| Q14 | Headline form | a) per-programme table and verdict primary, pooled second; b) engine pooled default | **a** (needs A15's per-event report stratum) | Drivers identify the programme; pooled margins are banned in the coral record |
| Q15 | Legacy harness replay of D:/adaptation/coral_full/_preds.npz | a) before the native build, as M6b's gate; b) after the coral headline run; c) skip, cite legacy numbers only | **b** | It does not gate the native run; it only links old and new numbers. Writes go outside D:/adaptation |
| Q16 | G-DERIVED route for the SST-relative, Hobday and cyclone columns (BLOCKER 1) | a) ingest writes them as dated per-site driver stores with their own facts; the engine joins them as-of at each issue date (A4; APP_PLAN.md:117); b) add generic multi-source operations to check/recompute.py (engine change, no-op gated); c) an owner-signed G-DERIVED exception route | **a**, if a size check passes; else b | No engine change to the recompute; the as-of join is needed anyway. The store size (daily values per site) is unverified and must be measured first |
| Q17 | Verdict reference for neighbour | a) the own-link trees-off, as for grids; donor-row median printed beside and used for hit tolerance and MAE skill; b) the donor-row median as the verdict reference; then the decline target and the guard baseline must be the same object | **a** | One rule for all kinds; "the trees help" stays the claim. b makes HELPS easier (beats a constant) |
| Q18 | Groups with no or few rows at a bank cut (BLOCKER 2) | a) generic rule (A19): a group with 0 rows at a cut trains no trees there, still lends and receives pool rows, counted and flagged; b) exclude such groups in split.yaml, disclosed; c) merge them with neighbours | **a** | Generic, keeps data. Groups with 1-29 rows already work (bag of 30 with replacement, bank.py:198-206) |
| Q19 | Coral rivals (C11 c and C12 are ruled, QUESTIONS_ROUND3_HANDOFF.md:472-473; F67) | a) build them (A21) before the coral pre-registration; b) report-only side Part after the run | **a** | Without test-era labels coral corr² was 0.097 vs DHW 0.421 (CLAIMS_LEDGER.md:75); the strict pool may lose to DHW |
| Q20 | Survey days imputed as the 15th (Donner, Safaie) | a) `date_precision = month`: the label window is the whole month, so features end before the month starts (exact R8 handling unverified); b) drop them; c) ignore, disclose | **a** | Keeps the rows; a true survey can be up to 14 days earlier, so a 1-day window can include post-survey heat |
| Q21 | Group id form | a) ecoregion names from Ecoregion_Name_LUT, with the 4 R21 smoke groups and their test counts listed before freeze; b) numbers | **a** | Numeric ids pick '1', '10', '100', '101', which hold almost no test visits |
| Q22 | Sign C3's remaining verdicts | a) as C3: nino34 banned and replaced by the shared ERSSTv5 anomaly at lag 2; dmi window bound `{3, month, centred}` (as R-B); mask_* banned; mhw_thr_gap and days_since_dhw4 watch; GHS-POP kept only if its epoch content dates are at or before each fit cut (else ban or a disclosed exception); CoralTemp `reach_after_max` declared and signed; MMM in context disclosed; b) one by one | **a** | Each item follows an existing ruling or precedent (R-A, R-B, N2, item 8 of section B) |

---

## 5. RISKS

**Could make coral not runnable**
- BLOCKER 1 (G-DERIVED recompute) and BLOCKER 2 (empty groups at a bank cut): Q16, Q18.
- A6 (row index) sits beside code every grid run uses. A slip breaks byte identity and forces grid re-runs.
- Pools across groups (A9) break the "one group's tables at a time" RAM plan. Coral is small, so keeping all answers should fit, but it is untested.
- The feature script re-reads daily SST for each lead. If done whole-table it needs 2.5-3 GB and the PC froze before on the pilot table (coral_safe.py:1-25). Never load D:/coral/drivers/sst_full_merged.parquet.
- R1's day-line rule may refuse if every multi-visit site looks regular (rules.py:291-312). At check time it sees one ecoregion only (quick.py:70-76); a one-site file may refuse or mislead. Unverified on coral.
- 576 sites have no SST (1,343 labelled surveys). Their rows are left out by the engine (H4/S1) and some small ecoregions may vanish.
- The last-value fill and the trend flag are defined in steps (engine_constants.py:287-293; report/metrics.py:1295-1305). Events need a rule or a skip; neither is ruled.
- Tooling names the four packages (datasets/_tools/refresh_drafts.py:50, 143-144); the coral draft needs a hand copy.
- With McClanahan only in 2016 and Donner absent from 2016-19, the test window mostly scores Reef_Check. Results may look like "predict-zero wins" for structural reasons.
- CoralTemp's content reach after its stamp is unverified; "strictly before the issue day" is safe only with a declared `reach_after_max` (Q22).

**Could make coral not comparable**
- Strict pool: on the dbl2005 split strict scored MAE 12.37 vs predict-zero 9.14 (CLAIMS_LEDGER.md:75). The engine result may lose to predict-zero. That is an honest result, not a bug.
- Merging MERMAID later would move the coverage end and the test window.
- Q4 b makes coral's engine path differ from the grid path in one disclosed place.

**Shipped coral numbers that will NOT be comparable to the engine run**
- Parts 443-457 (5.503, 5.167, 7.784, the per-programme tables, McClanahan 18.664): time-blind pool with other held-out labels (coral_glorys2_ab.py:93), 20/74 split, 3-7 seed means, 30/180/365 leads, and an 80-column model labelled 77.
- adaptation.py runs (5.668, 5.780 / 5.725, dbl2005 full/rollout/strict, all `_L*` forecasts): target-date pool cut (adaptation.py:2020, 2042), POP read at the true year at leads (adaptation.py:1836).
- Part 458: pilot split, 5 test ecoregions.
- What differs in the engine: LORO split and the R3/Q6 window, strict pool at the R11 cut, 100 trees at 0.10, MMM penalised, pool groups' trees dropped, donor-median fallback, ENSO anomaly at lag 2, frozen POP epochs, season as context at the issue day, one name-seeded bank, verdict against the own-link trees-off.
- Test exposure: nearly every labelled ecoregion and the 2016-19 rows of 24 ecoregions were seen during design (CORAL_EXPERIMENTS.md:2463-2465; APP_PLAN.md:310). The pre-registration says so.
- The harness replay (Q15) is the only like-for-like link to old numbers. The continuity row shows the old 74 groups inside the new run; it compares groups, not methods.

---

## 6. SOURCES

- Owner rulings: engine/OWNER_RULINGS_2026-09-28.md (D :48-55, L1 :61, L5 :63, H1 :94, H2-H5 :95-98, I1 :104, R-A :24, R-B :25); engine/OWNER_RULINGS_2026-10-06.md (M1-M3 :9-11, N2 :37, P1-P2 :53-54, Q1 :61, R1 :68, S1-S2 :76-77).
- Plans: APP_PLAN.md (:9-21, 74, 93, 115-124, 151, 176-180, 221-275, 310-359, 604-617, 731, 800-802); HEADLINE_QUESTIONS_AND_FIXES.md (:86, 166-171, 238-256, 430-431); QUESTIONS_ROUND3_HANDOFF.md (:246-264, 330-337, 460-475, 513-515); CLAIMS_LEDGER.md (:10, 75, 264, 382, 431); engine/SIGNATURES_LORO_ADDENDUM.md; engine/PREREGISTRATION_DRAFT.md (:55-56); engine/PENDING_PARTS.md (:156, 248, 267, 274-277, 291).
- Engine code: route/kinds.py:1228-1258; _proposed/loro_additions.py:755-792; derive/router_rules.py:149-346; derive/rules.py:569-625; derive/unit_rules.py:220-250, 471-501; derive/orchestrate.py; derive/census.py; io/steps.py:200-236; io/joins.py; labels/vault.py; pipeline/{stream,data,stages,router,passes,ladder,run}.py; fit/{context,bank,tables,pool,weights}.py; layer/arms.py:225-256; layer/decide.py:520-605; timing/cuts.py:55-102, 200-216; report/metrics.py; check/{deep,quick,guards,recompute}.py; split.py:732-878; runs/fingerprint.py:22, 138; engine/treeroute_report/{freeze,table}.py; tests/test_nonames.py:16-17; tests/test_route_kinds.py:300-335.
- Legacy coral: coral_glorys2_ab.py, coral_architecture.py, coral_forecast.py, coral_extra_drivers.py, coral_ghspop_ab.py, coral_smoke_regress.py, coral_dhw_model.py, coral_safe.py, adaptation.py.
- Coral docs: CORAL_EXPERIMENTS.md, CORAL_STATE.md, CORAL_DATA_AUDIT.md, CORAL_EVALUATION_AUDIT.md, CORAL_LABEL_AUDIT.md, CORAL_DESIGN_RECOMMENDATION.md, JOINT_CLAIM_NDVI_CORAL.md.
- Data (metadata and small reads only): D:/coral/target/events_dated.parquet (read today: yearly counts 2015 928, 2016 1,159, 2019 595, 2020 45; 6,434 rows on day 15); D:/coral/drivers/climate/nina34.txt header (absolute values); D:/coral/drivers/ghspop/GHS_POP_E2015.zip listing (R2023A, 2023-04-29); D:/treeroute/registry/freeze/FREEZE_20261017T105545Z.lock.json; D:/treeroute/registry/protected_roots.txt.
- Counts marked "completeness review measurement" come from that review's GCBD SQLite join and were not re-measured; today's events_dated.parquet cross-check agrees in direction.

---

## REVIEW LOG

Architecture review (A-n), leakage review (L-n), completeness review (C-n).

| Issue | Result | Reason |
|---|---|---|
| A-1 | fixed | Confirmed: recompute takes one source per operation (recompute.py:230-241); added BLOCKER 1, Q16, A20 |
| A-2 | fixed | Confirmed: R11 gives one cut per lead (cuts.py:62-89); A7 and Q3 rewritten |
| A-3 | fixed | A14 keeps own-link trees-off as verdict reference; Q17 added |
| A-4 | fixed | B3 uses ruling R1 wording plus report-table byte check; B7 names report-tooling hashes |
| A-5 | fixed | Confirmed LIMITS lines (run.py:139-150); A12 edits them, B3 lists the disclosed difference |
| A-6 | fixed | Confirmed scan covers treeroute/ only (test_nonames.py:16-17); E and A15 derive thresholds, no names, scan added |
| A-7 | fixed | A4 passes `keys['issue']` on the events path; look-ahead canary added |
| A-8 | fixed | A17 (R18) and A18 (R3) added; Q5 states the L1 departure |
| A-9 | fixed | Q4 and the guard note name arms.py, ladder.py:857, 905, decide.py docstrings |
| A-10 | fixed | A9 RAM wait; A12 per-fold checkpoint and interrupt test |
| A-11 | fixed | A8: no signature change; superseded stubs keep raising |
| A-12 | fixed | Rule line and A3/A12: events with h >= 2 still refuse (LIMITS line) |
| A-13 | fixed | A14 plumbing uses the route/solve.py reference fit |
| A-14 | fixed | A6 wording: separate event row index, grid untouched |
| A-15 | fixed | Confirmed PM2.5 ran under 7b508557 (PENDING_PARTS.md:156); ATTENTION and B5 corrected |
| A-16 | fixed | RAM row re-priced per table kind (tables.py:91) |
| A-17 | fixed | build_target writes a (site, date) report_stratum store |
| A-18 | fixed | D1 and D2 swapped |
| A-19 | fixed | Confirmed quick.py:70-76 reads one file; note in D3 and risks |
| A-20 | fixed | Event-clustered bootstrap dropped from the engine table (G-NODRAW) |
| A-21 | fixed | A1 offsets day coordinates or refuses (pre-1970 presence unverified) |
| L-1 | fixed | A7 uses label_usable at the R11 fit/guard cut; same cut for fallback, scaling, similarity; two new tests; Q2 d covers the as-of option |
| L-2 | fixed | A13 fits test banks at each lead's fit cut; 6 bank cuts; cost re-priced |
| L-3 | fixed | Same fix as A-3 |
| L-4 | fixed | Q4 covers the nowcast decline too; pre-reg prints both objects per lead |
| L-5 | fixed | seen_during_design widened; pre-reg 7.2 statement added |
| L-6 | fixed | Q6 requires the disclosure and a sensitivity row |
| L-7 | fixed | Q5 a needs the R18 candidate amendment (A17) |
| L-8 | fixed | Confirmed absolute values in nina34.txt; nino34 banned, shared anomaly at lag 2 (Q22) |
| L-9 | fixed | Codes not declared as fills; fixed caps; days_since_dhw4 watch |
| L-10 | fixed | Confirmed R2023A files dated 2023; content-date fact and G-EPOCH check (Q22) |
| L-11 | fixed | E: per-programme verdict; R33 within programme or labelled |
| L-12 | fixed | Year-blocked control justified in writing; DONORS-ONLY marked harness-only |
| L-13 | fixed | Q12 options relabelled; recommendation is the both-ways option c |
| L-14 | fixed | Q11 now recommends a (follow H3) |
| L-15 | fixed | mask_* ban or exception (Q22); MMM-in-context disclosed |
| L-16 | fixed | CoralTemp and DMI reach/window signed before freeze (Q22, C1) |
| L-17 | fixed | Side rows only in legacy_harness output, labelled |
| L-18 | fixed | Bathymetry ban in AUDIT_CHECKLIST |
| C-1 | fixed | Confirmed bank.py:200-206 refuses 0 rows; BLOCKER 2, Q18, A19 |
| C-2 | fixed | Confirmed the size sum (8 M + 5 L + 3 S >= 19.5 d); totals re-stated with new items |
| C-3 | fixed | C2 and cost table give scored and fold group counts; cross-checked today |
| C-4 | fixed | Q5 reworded: L1 departure, 67% share, floor sentence removed |
| C-5 | fixed | Confirmed C11 c and C12 rulings; Q19, A21, E rivals row; Q13 rival line removed |
| C-6 | fixed (part) | G5 and option d added to Q2; the "new signature" part rejected: the caller pre-cuts candidates (loro_additions.py:760-786), so no date input is needed |
| C-7 | fixed | Confirmed 6,434 rows on day 15; date_precision, exception, Q20 |
| C-8 | fixed | Same fix as L-5 |
| C-9 | fixed | continuity_groups in split.yaml; continuity row in E; section 5 wording |
| C-10 | fixed | Q21 added; D5 states the M1 pick rule |
| C-11 | fixed | Confirmed R3 event branch (rules.py:620-622); Q6 reason rewritten |
| C-12 | fixed | Same as L-2 plus RAM and time re-priced (2-10 h) |
| C-13 | fixed | Row counts updated |
| C-14 | fixed | C4: package writes NaN; engine applies H4/S1 |
| C-15 | fixed | A13 pinned placebo at 365; A15 damped persistence |
| C-16 | fixed | Confirmed FIT_CALLS (guards.py:62); polyfit risk removed, recompute gate kept |
| C-17 | fixed | Q22 added |
| C-18 | fixed | E primary programmes limited to Reef_Check, McClanahan, FRRP |
| C-19 | fixed | expected_derived.json list extended |
| C-20 | fixed | 2b SST row reworded |
| C-21 | fixed | Column count 66-73 |

Count: 60 issues. 59 fixed in full, 1 fixed in part (C-6, signature point rejected). No issue rejected in full.
