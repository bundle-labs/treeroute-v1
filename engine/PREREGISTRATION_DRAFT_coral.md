# Pre-registration Part: the coral bleaching headline run (the coral freeze alone)

> **This copy is for the coral freeze alone** (owner ruling H1 b, OWNER_RULINGS_2026-09-28.md:94: coral gets "its OWN
> pre-registration Part before its run"; ruling U6, OWNER_RULINGS_2026-10-06.md:95: "Then the coral tables, the coral
> pre-registration Part, the freeze and the headline run"). Written 2026-10-19 in the build copy
> (D:\treeroute\coral_build) in the structure of PREREGISTRATION_DRAFT_defo.md. The four grid problems (PM2.5, fire,
> NDVI, defo) are **not in this freeze**: every line about them is context only. The freeze command for this copy,
> from the LIVE engine folder after the install (section 12):
> `py -3.9 -m treeroute_report.freeze datasets/coral --prereg D:\treeroute\coral_build\PREREGISTRATION_DRAFT_coral.md`.
>
> **Coral in short.** Target: percent of coral bleached per reef survey visit (GCBD), 0-100. One row per visit
> (site + date). Groups are marine ecoregions. Input: the engine's TABLE option (ruling U1): the package hands in
> ready rows, one file per lead, with features that already end before each issue date; the owner is to vouch for
> their timing (U2; the statement in section 13 is not signed yet). Router: the neighbour kind (U3), with the strict
> pool (U4). Leave one ecoregion out. Leads: nowcast, 183 and 365 days (I1). Test window 2016-2019 (V3), with a
> declared 2017-2020 sensitivity row. Train end 2015, inner-score years 2013-2015, first year 1994. Decline object:
> the donor-row median (V1). Ruling V answered the 12 build questions of BUILD_REPORT.md section 3 on 2026-10-19
> (every recommended answer accepted); it did not answer the CORAL_ENGINE_PLAN.md question sheet (section 12 item 7). **V6 is decided:**
> on 2026-10-20 the owner amended V6 to option (b) (ruling W, OWNER_RULINGS_2026-10-06.md:116-121, the owner confirming option
> (b)). Groups with train rows but no test row are train-only DONOR groups. They train trees and lend rows; nothing is
> scored for them. Scored: 37 ecoregions (section 3.9).
>
> **Question numbers.** "coral Q" = the sheet in CORAL_ENGINE_PLAN.md section 4 (:244-267). "grid Q" = the grid
> question sheet that PREREGISTRATION_DRAFT.md cites (for example its Q19 a, Q21 a, Q22 b, Q37). The two sheets
> reuse numbers for different items.

> **Status: DRAFT for the owner to sign.** Written 2026-10-19 by an agent. Nothing here is signed. Sources: the owner
> rulings files (engine/OWNER_RULINGS_2026-09-28.md, _2026-10-05.md, _2026-10-06.md sections U, V and W), the build
> reports in D:\treeroute\coral_build (BUILD_REPORT.md, RULING_V_REPORT.md, CHECK_REPORT_V.md, SPEC_TABLE_MODE.md,
> SPEC_NEIGHBOUR.md, SPEC_CORAL_TABLES.md, PLAN_RULING_V.md, replay\REPLAY_REPORT.md) and the package draft
> engine\datasets\coral_draft. Where this text and a ruling differ, the ruling wins.
>
> **How it is filled.** Fields in double braces are filled by the freeze tool (treeroute_report/freeze.py:784-825;
> the known fields are listed at :749-750 and :763). The freeze writes the lock file, then a copy of this draft with
> every field filled, next to the lock: `<registry>/freeze/PREREGISTRATION_<UTC time>.md`. The owner signs THAT copy.
> Its SHA-256 goes into the Part log with the lock's SHA-256. A field the freeze cannot fill is printed as
> "NOT FILLED" in bold. The package fields name the package `coral`, the name the package must carry in its
> dataset.yaml at the freeze (section 12, item 3). A different name prints NOT FILLED for those fields.
>
> **Open items.** Every item still open starts with a bold marker: "owner decision pending" or "open before freeze",
> in bold capitals. The freeze refuses while either marker is in this file (F-PREREG, freeze.py:144-145, :599-604).
> The V6 choice field of earlier drafts is removed: ruling W wrote the choice (2026-10-20). No placeholder other than
> the freeze's own fields is left in this file (an unknown one would refuse, freeze.py:774-781).
> Some owner signatures are NOT seen by the freeze (the U2 statement, AUDIT_CHECKLIST.md:54, the ban verdicts' header
> at ban.yaml:2-4). Section 12 lists them as "by hand".
>
> **Scope.** This Part covers the coral nowcast-and-ladder headline run. It leaves out, on purpose:
> - the rivals (lagged DHW, the CRW Outlook, hgb_l1; coral Q19, CORAL_ENGINE_PLAN.md:264): deferred to M8 by owner
>   ruling E, L3, as for the grid problems. They get their own Part before any rival number. Coral Q19 recommended
>   building them before this Part; it is not ruled, so the signed rule (E, L3) is followed (U6; section 12 item 7);
> - the legacy harness rows and the year-blocked control (CORAL_ENGINE_PLAN.md:231, :237): report-only side rows,
>   never in the engine report;
> - the 2017-2020 sensitivity row's numbers: declared here (section 4.2); built and run only after the headline run,
>   under its own short Part (section 4.2).

## 1. The frozen state

- Lock file: {{LOCK_FILE}}
- Lock SHA-256: {{LOCK_SHA256}}
- Lock written (UTC): {{LOCK_CREATED_UTC}}
- Engine code (file hashes, the check contract): {{ENGINE_CODE_SHA256}}
- Engine code (comments stripped, as in the run manifests): {{ENGINE_CODE_HASH_STRIPPED}}
- Engine constants: {{ENGINE_CONSTANTS_SHA256}}
- Python: {{PYTHON_VERSION}}
- Report tooling (treeroute_report, hashed on its own): {{REPORT_TOOLING_SHA256}}
- Engine constants awaiting the owner, filled from the lock: {{CONSTANTS_AWAITING_OWNER}}
- **Installed engine (V6 (b), ruling W, with V4).** LIVE engine_code_sha256 since 2026-10-20 06:44 is
  `930d961cdfdd219c36b113174e6c865096f973068e30696850f13d5ec4a60814` (Part 595, engine\PENDING_PARTS.md). Installed
  by explicit list from D:/treeroute/coral_build_v6b: 9 changed files and 1 new file (tests/test_table_donor_only.py);
  old files in engine\_moved_coral_20261020_064437 (INSTALL_MANIFEST.json there: live_hash_before dd7c0984...,
  live_hash_after 930d961c...). The `check --deep` report of 2026-10-20 06:45 prints this hash (section 4.4).
  The field above is the one that counts.
  - History: dd7c0984 (V4 built, V6 (a)) was LIVE from 01:41 to 06:44 (Part 593; engine\_moved_coral_20261020_014111).
- **Report tooling moves too.** Both installs changed treeroute_report/table.py (the (b) install added the donor-only
  disclosure row, treeroute_report/table.py:542-545, :578), so the report-tooling hash moved (INTEGRATE_REPORT.md:89;
  INSTALL_MANIFEST.json). Adding the coral entry to treeroute_report/continuity_groups.yaml (section 12 item 3) moves
  it again. The no-op proof covers grid smokes only, not the grid report tables (run_noop_proof.ps1); that the grid
  tables are unchanged rests on an argument, not a run (CHECK_REPORT_V.md:104, :124).
- **The four grid headline runs keep their engine hash (ruling U5, OWNER_RULINGS_2026-10-06.md:94; ruling W2, :121).**
  None of the four is re-run. The grid no-op proof of 930d961c against dd7c0984 passed before the install (pm25 24,
  fire 24, defo 22, ndvi 26 files byte-identical; 0 must-match files differ; "RESULT: PASS",
  D:\treeroute\coral_build_v6b\noop\noop_summary.txt:73). The earlier proof of dd7c0984 also passed
  (D:\treeroute\coral_build\noop\noop_summary.txt). W2: the owner asked that the four finished problems not be retrained
  only to check that nothing had changed, since the change was to the code alone. No further grid re-run is made.
- **Disclosed: `freeze verify` on the four grid locks now reports drift.** It will list engine drift (their locks
  hold their own engine hashes, LIVE is 930d961c) and report-tooling drift (table.py; later continuity_groups.yaml).
  This is expected under U5 and W2 and covered by the no-op proof above; it is not a change to any grid result.
- After the freeze, `py -3.9 -m treeroute_report.freeze verify` re-hashes all of it and lists any drift.

## 2. The problem and its package

| Problem | Package | Target | Groups | Package fingerprint | Deep check report |
|---|---|---|---|---|---|
| Coral bleaching | datasets/coral | percent bleached per survey visit (GCBD), bounds 0-100 | 83 kept ecoregions: 37 scored + 46 donor-only (ruling W; section 3.9) | {{PACKAGE_FINGERPRINT:coral}} | {{CHECK_REPORT_SHA256:coral}} |

- **Target.** pct_bleached in [0, 100], legal range from the survey protocols (percentages); rows outside are dropped,
  never clipped (0 today). Recipe (coral_smoke_regress.py:56-77, reused unchanged): Reef Check Population rows, mean
  of S1-S4; AGRRA, FRRP, McClanahan and Donner Percent_Bleached; Kumagai and Safaie left out (ordinal only). Mean per
  sample, then mean per visit (SPEC_CORAL_TABLES.md 1.1-1.2).
- **Row.** One survey visit = (site, date). Site = ecoregion id + site key at 4 decimals (about 11 m). Group =
  ecoregion name (GCBD Ecoregion_Name_LUT). Report stratum = programme (Reef_Check, FRRP, McClanahan, AGRRA, Donner,
  mixed).
- **Data and sources** (all read from D:/coral, read only; AUDIT_CHECKLIST.md A4 for the vintages):

| Source | What it gives | Vintage |
|---|---|---|
| Global Coral Bleaching Database (GCBD) SQLite | labels, sites, dates, ecoregions, programmes | 11_24_21 |
| NOAA Coral Reef Watch CoralTemp daily SST (compact sst_compact_all.npz) | 30 SST heat, 7 heat history, 10 marine-heatwave columns; MMM (context) | 5,139 daily files |
| IBTrACS v04r01 best tracks | 16 cyclone columns | to 2026-08-20 |
| PSL nina34.txt (ERSST V6, absolute) | Nino-3.4 anomaly at lags 3, 6, 9 months (built in the package, base 1951-1980) | to Jul 2026 |
| PSL dmi.txt (HadISST1.1) | DMI at lags 2, 5, 8 months: conditional, out of the run (V9) | to May 2026 |
| calendar and site key | router context: month, day-of-year sin/cos at the feature cut, abs(latitude) | - |

- **Columns.** 85 per lead file: 9 keys (incl. feature_end), the target, the programme stratum, 5 router context
  columns, 69 tree columns. Drafted verdicts (ban.yaml, UNSIGNED, ban.yaml:2-4; signed before the freeze, section 12
  item 3): keep 65 (60 tree + 5 context), watch 3, conditional 3 (DMI), ban 5. If signed as drafted,
  **63 tree columns enter the trees** (60 keep + 3 watch); DMI stays out (V9; schema: 'conditional' leaves the
  run, pipeline/data.py:229). Not written: GHS-POP shape columns (content dated 2018-2022, ruling N2), the CRW mask
  pair, absolute Nino-3.4 and every lag-0 index column (SPEC_CORAL_TABLES.md 3.3).
- **Store.** One parquet file per lead (`lead_{lead}.parquet`, leads 0, 183, 365), written by the package-side
  builder (coral_tables/build_tables.py), published once to a protected folder (coral_store/<build stamp>/). The
  engine reads them in place. The engine recomputes no feature (U2).
  - **Published 2026-10-20 (write-once):** `D:/treeroute/coral_build/coral_store/20261020_014201/` (lead_0, lead_183,
    lead_365 and build_manifest.json). The root `D:/treeroute/coral_build/coral_store` is in
    D:/treeroute/registry/protected_roots.txt. The package store line reads
    `D:/treeroute/coral_build/coral_store/20261020_014201/lead_{lead}.parquet`.
  - **Full build (2026-10-20, 26.4 min, peak 1.39 GB; manifest coral_data\full\build_manifest.json):** lead 0
    13,694 rows (11,347 train, 2,347 test, 94 groups, 8,157 sites); leads 183 and 365 13,686 rows each. 41,066
    per-row asserts passed; look-ahead canary 822 row-leads, 0 mismatches; replay against the legacy feature files, max
    relative difference 0. Independent checker: RESULT PASS 52/52; the look-ahead recompute on all 41,066 row-leads x
    53 columns found 0 differing cells (coral_data\full_build_console.log, full_check_console.log).
  - **Package draft in LIVE:** engine\datasets\coral_draft (still DRAFT, unsigned), with the (b) split.yaml,
    exceptions.yaml, ingest\README.md and AUDIT_CHECKLIST.md since 2026-10-20 06:44 (old copies in
    D:\treeroute\coral_build\_moved\live_coral_draft_pre_v6b_20261020_064456). Fingerprint
    `04b9aab0fb5aa616d8544c8babff0d373800aea9c1c8d088d3911444082d7045` (check_deep_04b9aab0fb5a.json; the (a)
    fingerprint dfa07650... is superseded). The signed package `coral` made from it (section 12 item 3) will have its
    own fingerprint; the freeze fills that one below.
- The only hand-set input of the run is its package. Every modelling setting is derived by a written rule and printed
  by `treeroute plan` before any compute.

## 3. The design

### 3.1 The table option (ruling U1)

- The package supplies ready rows. Each row: row id, unit (site), group (ecoregion), lat, lon, target date, issue
  date, feature end, a train or test mark, the label, the programme, context and tree features.
- The engine skips the grid-only steps: the grid census, computed lags and grid pools (U1).
- It still checks dates on every file (SPEC_TABLE_MODE.md 2.1; package/table.py): T-ISSUE (issue = target minus
  lead), T-FEATEND (feature end before the issue date on every row), T-LEADSET (same row id = same visit and label in
  every file), T-UNITTIME, T-RANGE, T-FINITE, and T-MARK (train rows on or before the train end; test rows inside the
  test years; marks equal the derived window).
- Windows and cuts come from the dates: R3 (events) applied to lead files from which the package removed 2020 (V3, a
  hand cut, coral Q6 c), then the signed R4-R7 and R11 (events). The six bank cuts: lead 0
  fit 2015-12-31 and inner 2012-12-31; lead 183 fit 2015-07-02 and guard 2012-07-02; lead 365 fit 2015-01-01 and
  guard 2012-01-02 (make_split.py --check output, 2026-10-19).
- No test label reaches a fit, a selection, a guard or a pool: the row vault refuses any cut on or after 1 January of
  the first test year, and test labels open only after the pass's adoption lock (SPEC_TABLE_MODE.md 2.3).
- **Scored rows are the package's test marks (U1)**: every test-marked visit, not R18 (2)'s stride pick. Most test
  sites have no label before the train end, so they would never be R18 candidates (783 of 1,262 kept test sites;
  exceptions.yaml:103-108).

### 3.2 Feature timing vouched by the owner (ruling U2)

The engine cannot recompute hand-built features (U2, OWNER_RULINGS_2026-10-06.md:91). The owner vouches for their
timing. The statement is copied from AUDIT_CHECKLIST.md section B (:22-52) and is to be signed in section 13 (not
signed yet; AUDIT_CHECKLIST.md:54 is blank too, and the freeze does not read that file's content,
AUDIT_CHECKLIST.md:56):

1. Every feature and context value of a lead-L row uses only data dated strictly before its issue date (target date
   minus L). The builder uses the stricter cut C = anchor minus L (anchor = the target date, or the month's first day
   for a month-precision visit). SST and cyclone windows end before C minus 1 day (UTC days).
2. No feature reads the row's own label, a label of any test row, or any label dated on or after the issue date. No
   column of these files is computed from any label.
3. The issue date equals target date minus L (the engine checks it: T-ISSUE).
4. The same row id means the same visit, with the same label, in every file (the engine checks it: T-LEADSET).
5. The target date is the label's last content day.
6. feature_end is the last content day any feature window of the row may read at that lead, and it is before the issue
   date (the engine checks the second part: T-FEATEND).

The evidence the builder leaves: per-row asserts, the largest "source day minus issue day" per family (always below
0), a look-ahead canary (rows rebuilt from sources cut at C, compared byte for byte), a replay against the legacy
feature files, and an independent checker (check_tables.py) with a negative control (SPEC_CORAL_TABLES.md 3.4).
AUDIT_CHECKLIST.md:43 cites only the tiny build (2026-10-19). The evidence for the full tables the owner vouches for:
full build 2026-10-20, D:\treeroute\coral_build\coral_data\full\build_manifest.json proof (asserts 41,066 row-leads;
canary 822 row-leads, 0 mismatches; max source day minus issue day sst -2, cyclone -2, index -1, feature_end -1 at
every lead; replay max relative difference 0), coral_data\full\check_report.json and full_check_console.log
(RESULT: PASS, 52 checks ok). Settled 2026-10-20 (ruling X5): make_signed_coral.py added this full-build line to
AUDIT_CHECKLIST.md section B of the signed package `coral` (approved in its dry run). The
engine writes the U2 list into plan.json and run_record.json (derived entry U2:vouched). Open timing facts the owner
accepts by signing: CoralTemp reach after its day stamp unverified; ERSST V6 reach +2 months assumed; DMI bound only
proposed (DMI stays out); IBTrACS best tracks are post-season products (section 10).

### 3.3 Leave one ecoregion out

- No hand-made donor/test list (rulings D, E, H1). Every kept group trains its own trees and every group with a test
  row is tested. A kept group with no test-marked row is DONOR-ONLY (ruling W1): read from the marks, never from a
  list or a name; its trees and train rows are used, nothing is scored or reported for it (section 3.9).
- **Per-group banks.** 100 trees per group (C13.trees_per_group, engine_constants.py:203), max_features 0.10
  (C13.tree_max_features, :210), bags of half the group's rows with replacement, at least 30 rows (C13; derived R19).
  Seeds come from the group's name and the tree number (R19). No seed is varied.
- **Own-block masking.** Groups whose sites touch form one overlap block (R14). A row's router never sees the trees of
  its own block (G-DISJOINT). Under V6 (b) (83 groups after V5) the build engine finds 78 blocks; 5 hold two groups
  (SPEC_CORAL_TABLES.md 2.2). The count for the run is printed from plan.json (section 4.3).
- **Decision-surface folds.** Leave one group out (C8.neighbour_folds_leave_one_group_out). Each fold gets its own
  c, fallback median and GLS weight model from rows outside the fold's block (signed R13, R25). A fold whose group
  has no surface row is skipped; its trees still serve the others (BUILD_NOTES_table.md item 9). Donor-only groups'
  rows before the cut form their own folds (ruling W1, C1 (i)): 2,046 surface rows in 33 groups (section 3.9).

### 3.4 The neighbour router (ruling U3)

- R12 picks the kind from the data: the median valid rows per candidate site is h = 1.0, so the neighbour kind
  (SPEC_CORAL_TABLES.md 2.1; derived R12). U3 and H1 stand.
- Per scored row: take the **150 nearest earlier training rows by map distance** (haversine), then the **50 most
  similar in feature space** (C11.neighbour_pool_distance 150, C11.neighbour_pool_feature 50;
  engine_constants.py:173-177; origin adaptation.py:1434, 1638-1640).
- Feature space: the tree features only, 0-filled and standardised on the pass's candidates (V8; SPEC_TABLE_MODE.md
  O5). Season reaches the router as context only (H3).
- A local ridge on the pool: the kept trees' answers plus the 5 penalised context columns, the intercept alone
  unpenalised. Penalty grid 7 levels (0.1-100) x 5 ratios (0.0625-1) around the centres 0.5 / 0.25
  (C12.neighbour_trees_centre, C12.neighbour_context_centre; engine_constants.py:186-187; test-exposed).
- **With under 12 valid pool rows, the row falls back to the donor-row median** (C11.neighbour_pool_min_rows 12).
  The median is taken over the pass's bank donor rows (decision surface: outside the fold's block; lead guard: the
  guard bank) (SPEC_TABLE_MODE.md O7, SPEC_NEIGHBOUR.md N5).
- **Pool tree drop (V2).** The signed default stays: the trees of every group present in a row's pool, and of
  those groups' overlap blocks, are dropped, on top of the row's own block (SIGNATURES_LORO_ADDENDUM.md:34; U4;
  route/neighbour.py:29, :180). A row left with no tree takes its trees-off on its pool, counted as
  n_rows_no_tree (SPEC_TABLE_MODE.md O8; route/neighbour.py:914).
- The ported router equals the legacy lines on a toy when both get the same pool (replay harness, ruling V7:
  RESULT PASS P0-P5; replay\REPLAY_REPORT.md). The toy says nothing about coral.

### 3.5 The strict pool (ruling U4)

- The pool takes only TRAINING rows dated strictly before the row's issue date. At a lead the issue date is the
  target date minus the lead; at the nowcast it is the row's own date. It never takes a test row (U4,
  OWNER_RULINGS_2026-10-06.md:93).
- The pool horizon is also the pass's own bank cut, then "before the issue day" per row (SPEC_TABLE_MODE.md O3,
  signed R14).
- A per-row assert refuses any pool row that is not train-marked, is after the pass's cut, or is not strictly before
  the issue day (G-FITCUT). Every pass saves its pools (pools_<pass>.parquet) and logs the largest "pool day minus
  issue day" (always below 0).
- This fixes the legacy pool leak (Part 458; section 10).

### 3.6 The adaptation layer (R22-R28)

- **Links** (R22, derived from the donor rows): identity, log(y + c) and arcsine (the target has a finite upper bound,
  100; R28 legal range [0, 100]). The tiny smoke derived all three; the full plan prints its own list.
- **Arms:** for each link, plain and corrector, each unweighted and GLS-weighted (12 arms); each link's trees-off; a
  placebo per corrector that is never selectable. The pinned arm's placebo is built at the longest lead (365 days).
- **Selection by MAE on the decision surface** (grid Q37): the inner-score rows 2013-2015 of every fold, scored by the
  inner-cut bank (ruling E, L6 b). Every arm and every grid point is scored; the lowest MAE wins. Picks at the grid
  edge are flagged, never extended. Predict-zero and corr2 are printed beside. The adoption is locked and hashed
  before any test label is opened (G-LOCK).
- **Correctors** are fitted on out-of-bag rows (at least 50, C13.corrector_min_oob_rows). Where no tree has 50
  out-of-bag rows, a corrector arm equals its plain arm on the surface; the run records this per bank (BUILD_REPORT.md
  section 3 item 11, A4).

### 3.7 The guard and the decline object (ruling V1)

- **For the neighbour kind, every decline (nowcast and every lead) falls back to the donor-row median (R34), and
  every guard or decline comparison uses that same median as its baseline** (V1, OWNER_RULINGS_2026-10-06.md:103).
  The check and the fallback are one object.
- Nowcast: the decision's N2 check compares every arm with each surface row's fold median. If no arm passes, the
  nowcast adopts `base__donor_median` (layer/decide.py, gated on the router kind read from the data, R12; never a
  package name).
- Each lead (H2): the guard bank is refit at the lead's guard cut. The pinned arm is scored on the guard surface
  against the guard bank's donor-row median. Pass: the pinned arm is the lead's answer. Fail: the lead's answer is
  `base__donor_median` (lead.json guard.baseline_*; decision_checks.json).
- The grid kinds are unchanged (their guard/fallback fix waits for the next engine version, V1).

### 3.8 Other rules carried over

- **Missing router context (ruling S1).** A scored row whose context is missing or non-finite at its issue step is
  left out of scoring, saved with a flag and counted. Never filled.
- **Missing tree features (R30).** Written as NaN by the builder (no imputation); the engine 0-fills tree NaN and
  counts the filled share per column, flagged above 25% (C15.missing_flag_share). On the published tables the
  0-filled share and the marine-heatwave NaN rows are 0: no NaN cell in any of the 74 numeric columns at any lead
  (T-FINITE, coral_data\full_check_console.log:12, :27, :42).
- **Rows absent from a lead file** (8 train visits of 1994 at leads 183 and 365, V6 (b)): out of that lead's banks,
  c, tolerances, median, GLS rows and pools, counted (departure table_absent_rows, section 10).
- **Every row-level prediction is saved** (test_preds.parquet: every arm, every baseline, the pre-clip value; the
  pools; the guard rows). Every table is built from these saved rows.

### 3.9 The split, the exclusions and V6 (b) (ruling W)

**V6 is decided: option (b), ruling W, 2026-10-20** (OWNER_RULINGS_2026-10-06.md:116-121; the owner confirmed option
(b)). It replaces the signed V6 text ("Left out in split.yaml, disclosed", :108). Built defaults, taken as
ruled (W1): **C1 (i)** donor-only rows join the decision surface as their own folds (the "b1" of earlier drafts);
**C2 (i)** the R21 smoke groups are unchanged (the first 4 kept groups in sorted order, even one with no test row);
**C3 (i)** a record key plus one report disclosure row, signed by ruling W itself (no TABLE_DEPARTURES entry);
**C4** the run refuses when fewer than 3 groups have a test row (the same C15 constant). No further grid re-run (W2).

Counts from `make_split.py --check` ((b) version, D:/treeroute/coral_build_v6b/coral_tables/make_split.py) on the
published tables (D:/treeroute/coral_build/coral_store/20261020_014201): CHECK PASS (Part 595). The same counts
came from stage 1 (coral_data/visits.parquet) and the full build; stage 2 dropped no counted row. The check report
agrees: 94 groups in the data, 11 excluded, 83 kept, 46 donor-only, 37 scored (check_deep_04b9aab0fb5a.json, guards
G-SPLIT and "R18 donor-only groups").

- **Written:** 13,694 visits at lead 0 in 94 ecoregions (13,686 at leads 183 and 365), first year 1994. The 38 visits
  of 2020 are not written (V3).
- **V5 (signed): 11 groups the engine defaults refuse are left out in split.yaml** (OWNER_RULINGS_2026-10-06.md:107).
  They hold 35 test and 9 train visits. Four have 0 train rows at a bank cut (O13): Gulf of Guinea to Sierra Leone
  (18 test), Kimberley Coast (10 test), North-west Arabian Sea (1 test; also one site), Birds Head Peninsula (6 test,
  1 train). Eight have one site (O14): Ashmore Reef, Gulf of California, Houtman Abrolhos Islands, Line Islands,
  North-west Arabian Sea, Pompey and Swain Reefs, South China Sea, Southern Seychelles. split.yaml excludes only these
  11 (W1).
- **V6 (b), ruling W: 46 donor-only groups.** These kept groups have train rows but no test row in the lead files.
  The engine reads this from the marks, never from a list or a name (W1). They hold 1,874 train visits on 1,066
  sites, 1994-2015 (Reef_Check 1,416, Donner 311, AGRRA 147), which is 16.5% of the kept train visits; 111 of them
  are 2013-2015 decision-surface rows. Gulf of Thailand is one: its 10 test-window visits have no lead-0 SST history,
  so none is written. Their trees enter every bank. Their train rows enter every pool, c, median, tolerance and GLS
  model, and their rows before the cut form their own decision-surface folds (R13). Nothing is scored or reported
  for them. They are counted and disclosed: derived.json R18:donor_only, the run records (run_record
  donor_only_groups, pipeline/table_run.py:286), the check report and one report disclosure row
  (treeroute_report/table.py:542-545).

| Kept split, V6 (b) | Count |
|---|---|
| Groups in the data after V5 | 83 (37 scored + 46 donor-only) |
| Groups scored (test rows) | 37 |
| Train visits, lead 0 | 11,338 (7,348 sites) |
| Train visits, leads 183 / 365 | 11,330 / 11,330 |
| Test visits, every lead | 2,312 (1,262 sites) |
| Train by programme, lead 0 | Reef_Check 6,381, FRRP 2,185, Donner 2,116, AGRRA 651, mixed 5 |
| Decision-surface rows (2013-2015) | 2,046 in 33 groups (C1 (i)) |
| Bank trees at a cut | 83 x 100 |
| Overlap blocks | 78, 5 of them pairs (all 5 stay under (b)) |
| Rows absent at leads 183 / 365 (section 3.8) | 8 |
| Verdict reference (donor-row median of the train visits, lead 0, train rows only, no test row read) | 1.0 |
| R21 smoke and deep-check groups (section 4.4) | Andaman Islands, Andaman Sea, Austral Islands (donor-only, 0 test visits), Bahamas and Florida Keys |
| Engine | 930d961c (V4 + (b)), installed in LIVE 2026-10-20 06:44 (section 1) |
| Package files | the (b) split.yaml, exceptions.yaml, ingest/README.md, AUDIT_CHECKLIST.md in LIVE coral_draft since 06:44 (section 2). Their V6 texts still say "DRAFT option ... not signed" or "awaiting the owner"; they are reworded to cite ruling W in the signed package (section 12 item 3) |

**Disclosed about V6 (b).**
- **It departs from "every group is tested"** (ruling D, OWNER_RULINGS_2026-09-28.md:48), for table packages only
  (W1): 46 groups in the data are never tested. Their train rows still shape every fitted object behind the scored
  rows.
- **Why (b) was raised:** the legacy coral record calls more donors (5 to 20) "the FIRST significant improvement" of
  the coral programme (CORAL_EXPERIMENTS.md:2582, :2604, Part 444). It was not the only one: Part 425 (the arcsine
  link) and Part 458 (the strict mask) also improved scores. Part 444 compared donor sets on held-out TEST regions
  (:2586-2600), with the legacy split and the leaky pool. So the reason for raising (b) comes from a legacy test-row
  comparison; this is test exposure, disclosed in Appendix B. It is not a measurement of (a) against (b).
- **How it was chosen.** No test score of this package was used to compare (a) and (b). The sheet put to the owner
  listed both options with no recommendation and no score. Before the choice, real-data smokes had opened test labels
  (the tiny smoke 2026-10-19; the full-data smoke under (a) 2026-10-20), and an agent had seen the (a) smoke log's
  test line (section 4.4). These exposures are disclosed; none was used for the choice.
- **What changes with (b).** Both options scored the same 2,312 test visits in the same 37 groups. (b) changes the
  donor rows behind every fitted object (banks, pools, c, the donor-row median, tolerances, the GLS model), so its
  numbers differ from what (a) would give. The verdict reference is 1.0 (computed from coral_data/visits.parquet
  train rows only; the run's medians are per pass and cut). (a) is not run.

## 4. Leads, windows and test years

### 4.1 The headline windows

- **Leads (owner ruling I1, OWNER_RULINGS_2026-09-28.md:104):** the nowcast (lead 0), 183 days and 365 days (R10 on
  an events cadence: 6 and 12 months of 365.25 days, rounded half up).
- At every lead, every fitted object is cut at the lead's cut. Each lead refits its guard bank at its guard cut
  (rulings H2-H5). The lead-0 contract must reproduce the nowcast (G-PLUMB "lead 0 = nowcast").

| Package | Test years | Donor train end | Inner score years | First year (Y0) | Inner fit |
|---|---|---|---|---|---|
| coral | 2016-2019 (V3) | 2015 | 2013-2015 | 1994 | 1994-2012 |

- **The V3 window (OWNER_RULINGS_2026-10-06.md:105).** 2016-2019, by leaving out the 38 visits of 2020. This departs
  from R3: on all the data R3 gives 2017-2020. V3 is a hand cut (coral Q6 c, "a hand knob", CORAL_ENGINE_PLAN.md:251;
  SPEC_CORAL_TABLES.md:20), not a rule read from the data. **The cut came after the yearly counts were seen** (SPEC_CORAL_TABLES.md
  :19-21; exceptions.yaml:116-121). Test visits per year after V5: 2016 873, 2017 565, 2018 443, 2019 431.
- The settings the package's plan derived (filled from plan.json):
  - coral (derived.json {{DERIVED_SHA256:coral}}, plan.json {{PLAN_SHA256:coral}}):
{{DERIVED_SETTINGS:coral}}

### 4.2 The declared 2017-2020 sensitivity row

- **Declared now, never the headline.** It is reported beside the headline after the headline run, one heavy job at
  a time. It cannot change the verdict, the adoption or any choice.
- **Its own short Part.** Steps 2 and 5 below add a builder option and a new package after this freeze; section 11
  says such changes need a new Part. So the sensitivity row gets its own short Part and lock before its run (builder
  hash, package fingerprint, engine hash). This is the only carve-out from section 11, and it covers only the steps
  listed here.
- **Its not-headline mark.** Since V4 the engine marks a table run not-headline only for a DRAFT package
  (table_run.py:136-137), a smoke (:138-139) or an unset C9.guard_tolerance_k (:140-147); a table departure is no
  longer a reason (V4: the departures are accepted). A sensitivity run with k set carries none of these. A DRAFT
  stamp would make the freeze tool refuse (F-DRAFT, freeze.py:624-627). The sensitivity Part must therefore name how
  the mark is made: a DRAFT stamp with a lock written outside the freeze tool, or a named not-headline reason (an
  engine change, needing its own no-op proof). It is decided in that Part, never from a result.
- How it is produced (ingest/README.md:107-126):
  1. Stage 1 into its own folder (never over coral_data\visits.parquet):
     `py -3.9 -u build_visits.py --test-years 2017-2020 --out D:\treeroute\coral_build\coral_data\sens_2017_2020`.
     The 2020 visits are then written as test rows.
  2. A small builder option `--visits-dir DIR` for stage 2 and the checker (they read the visit table at a fixed path,
     build_tables.py:78, check_tables.py:52, :332). This builder change is not made yet. It changes the builder's code
     hash, never the engine or the headline tables (the headline store is published and protected).
  3. `build_tables.py --build full --visits-dir <sens folder>` and `check_tables.py --build full --visits-dir <sens folder>`.
  4. `make_split.py --visits <sens folder>\visits.parquet --split <sens package>\split.yaml --write`: the V5/V6 lists
     are recomputed for that window (they will differ from the headline lists), under V6 (b) (ruling W), with the (b)
     make_split.py in D:/treeroute/coral_build_v6b/coral_tables (SHA-256 a69e1c8c...; the file in
     D:/treeroute/coral_build/coral_tables is a different, pre-(b) version, SHA-256 c38d76b1...; section 3.9).
  5. A package copy `coral_sens_2017_2020` with its own name, store line and split.yaml, its header saying "declared
     sensitivity row (V3); never the headline". R3 gives 2020, R5 2017-2020; every cut moves one year later.
  6. From LIVE: check, smoke, run, at the same engine hash as the headline run.

### 4.3 Read from plan.json at the freeze

The DERIVED_SETTINGS field above prints the derived values. Expected, from SPEC_CORAL_TABLES.md 6 and the tiny smoke:
R1 irregular (declared by U1), R2 event month, R3 2019, R4 1994 (no lag sources), R5 2016-2019, R7 inner fit
1994-2012 and score 2013-2015, R10 183/365, R12 neighbour, R17 empty (no own-history block for the neighbour kind),
R22 identity / log_c / arcsine, R28 [0, 100]. Any difference from these is read before signing.

### 4.4 The R21 smoke and deep-check groups (coral Q21 a)

The first 4 kept groups in sorted order (R21; ruling M2 runs the deep check on them; F-CHECK-GROUPS depends on
them). The R21 rule is unchanged (ruling W, C2 (i)). Under (b) the first 4 kept groups now include the donor-only
Austral Islands in place of Banda Sea and Molucca Islands (the (a) set, Part 594), so one of them has no test row. Train /
test visits at lead 0, from coral_data/visits.parquet and split.yaml (the full-build counts are identical, section
3.9):

| R21 group, V6 (b) | train / test |
|---|---|
| Andaman Islands | 2 / 8 |
| Andaman Sea | 136 / 63 |
| Austral Islands, French Polynesia (donor-only) | 5 / 0 |
| Bahamas and Florida Keys | 2,922 / 206 |

So the smoke four has exactly 3 scored groups, the minimum (C15.min_groups 3; C4 refuses under 3). The deep check
under (b) did not refuse (checked_groups.refused null, check_deep_04b9aab0fb5a.json). From 2026-10-20 on, under the
read rule (section 12 item 4), no smoke score is read before the freeze. The earlier exposures are listed below.

**Checks from LIVE on coral_draft under (b) (fingerprint 04b9aab0fb5a..., engine 930d961c), 2026-10-20 06:45:**
- check --deep GREEN on the 4 groups above: D:\treeroute\runs\coral_draft\check\check_deep_04b9aab0fb5a.json.
  Full package fingerprint `04b9aab0fb5aa616d8544c8babff0d373800aea9c1c8d088d3911444082d7045`; engine_code_sha256
  930d961c...; G-CLOSED pass (63 tree features, 5 context columns, 1 strata); G-SPLIT pass (94 groups, 11 excluded,
  83 kept, 46 donor-only); U1 pass (13,650 rows; largest feature-end minus issue day -1 at every lead); "R18
  donor-only groups" pass (46 of 83); derive pass (router neighbour, test years 2016-2019); **G-FACTS flag** (target
  facts unsigned; must be signed before a headline run).
- check quick has not been run under (b). The (a) quick and deep reports (check_quick_dfa07650a6ed.json,
  check_deep_dfa07650a6ed.json, fingerprint dfa07650..., engine dd7c0984) are superseded.
- These cover the draft package only. The freeze needs both checks again on the signed package `coral` (its own
  fingerprint) at the engine it locks (F-CHECK-MATCH). The freeze fills the hashes; none is written here.

**Full-data smoke from LIVE under (b)** (run root D:/treeroute/coral_build_v6b/runs_live_smoke, folder
coral_draft\smoke\20261020_d28c38d5; 0.3 min, exit 0, every phase DONE; it started after ruling W, 06:44). Plumbing
only. From plan.json (counts only): lead-0 bank_rows 10 / 101 / 5 / 41 (157; all rows of the sites picked for the
bank, train and test marks together, so Andaman Islands' 10 are 2 train + 8 test visits; test labels are refused at
the cut) and scored rows 8 / 33 / 0 / 1 (42 in 3 groups) for Andaman Islands / Andaman Sea / Austral Islands / Bahamas and Florida Keys; donor_only_groups = Austral
Islands. Pool facts (from the pool records, no test score): every pool held exactly 50 rows, 0 pool fallbacks. Rows
left with no tree after the V2 drop: 0 of 24 on the surface, 2 of 18 on the lead-183 guard, 0 of 14 on the lead-365
guard. run_record donor_only_groups lists Austral Islands (5 train rows). With 4 groups only, these shares say
nothing about the full run. Its run.log and console log (D:\treeroute\coral_build_v6b\live_smoke.log) were not opened;
no test_preds, score, per-group, verdict or ladder file was opened.

**Earlier full-data smoke, under (a), superseded** (run root D:/treeroute/coral_build/runs_live_smoke, folder
coral_draft\smoke\20261020_4ba5d8fb; engine dd7c0984; 0.4 min, exit 0). 217 lead-0 bank rows, 79 scored rows, every
pool 50 rows, 0 fallbacks; no tree left on 5 of 26 surface rows, 2 of 19 and 7 of 14 guard rows. Kept here only for
the disclosures below.

**Disclosed about the smokes:**
- The tiny smoke and the (a) full-data smoke ran before V6 was decided. They used (a), the signed default at the
  time (U6). The (a) smoke opened the test labels of its 4 groups (79 rows); the (b) smoke opened those of its 3
  scored groups (42 rows).
- **The tiny smoke (2026-10-19, real data) also ran before V6, and its test MAE was read and used for a choice.**
  Run runs\coral_draft_tiny\smoke\20261019_6a40c185: 4 ecoregions (Andaman Sea, Maldive Islands, Moreton Bay, North
  and central Red Sea), 96 test rows of this test window. BUILD_REPORT.md:71-77 prints its pooled test MAE per lead
  and arm, and Part 593 copies it. The V1 recommendation cited those numbers (BUILD_REPORT.md:17-19, :89-91; section
  10 V1). Andaman Sea is also a scored group and an R21 smoke group.
- After the (a) smoke, an agent's review pass read plan.json, the test_labels_opened row counts,
  decision_checks.json and lead.json row counts; lead.json also showed test-pass no-tree counts (counts, not scores).
- A morning sheet drafted at 02:22, after the (a) smoke log's test line (next item, live_smoke.log 02:16) had been
  seen, recommended V6 (b) on the ground that "more donor regions helped in Part 444". That recommendation was
  withdrawn on review; the sheet then listed both options with no recommendation, and the owner chose (b) (ruling W).
  It is disclosed here.
- The (a) smoke's console log (D:\treeroute\coral_build\live_smoke.log) and its run.log end with a "finished" line
  that prints the smoke's test verdict and pooled test MAE (79 rows). An agent saw that line on 2026-10-20 while
  checking the log; the numbers are not copied anywhere. No test_preds, score or ladder file was opened. Under the
  read rule (section 12 item 4) this line is test exposure of 79 smoke rows, disclosed. No choice in this Part (V6
  included) used it.

## 5. Scored rows

- **Every test-marked visit is scored** (U1; exceptions.yaml:103-108): 2,312 visits in 37 ecoregions at every lead,
  under V6 (b) (ruling W; section 3.9). The 46 donor-only groups have no test row, so nothing is scored for them.
- By programme (exceptions.yaml:41-46): Reef_Check 1,932, FRRP 190, McClanahan 189, AGRRA 1, Donner 0. Pooled scores
  mostly measure Reef_Check.
- The saved rows must score exactly the derived rows (G-SPLIT on the outputs). The ladder is scored on the rows
  common to all leads (keys: row id and target date), with all rows beside.
- Test rows absent at a lead are handled by H4; a scored row with missing context by S1 (left out, counted).

## 6. Headline metrics and the reporting plan

### 6.1 The metrics

- **MAE** is the headline score. It is also the selection score.
- Printed with it, always together: **corr2** and the **hit rate**. The neighbour kind has no per-unit normal, so
  anomaly R2 against a normal is not defined (printed NaN with n 0; metrics.py:906-913), and the guess-normal and
  last-5-years columns are absent (shown NaN; SPEC_TABLE_MODE.md 3.11). R2 is never reported alone.
- **Predict-zero and the donor-row median are printed beside every MAE**, in every table and every stratum. At leads,
  persistence (the site's last label before the issue date, on the rows that have one) and damped persistence (its
  normal from the baseline-only chain of SPEC_TABLE_MODE.md O17) are printed with their row counts.
- Hit rate: the share of rows within the R32 tolerance, half the donor rows' mean absolute deviation from the
  donor-row median (metrics.py:665-686). No measurement floor is declared.
- Also printed: the calibration ratio, the pre-clip rate and the strict top-10% detection score (R33) with its event
  count. R33 is printed within programme only, or labelled "source statistic, not severe-tail skill"
  (CORAL_ENGINE_PLAN.md:226).
- The neighbour own-link trees-off of the adopted arm is printed beside the verdict reference (verdict.json beside).
- Per lead: the guard reference and the decline object (one object under V1, the guard bank's donor-row median),
  with the pinned arm's guard-surface MAE and the median's guard-surface MAE side by side (CORAL_ENGINE_PLAN.md:193,
  plan step 8; lead.json guard.baseline_*).
- **R2 about the donor-row median** (planned at CORAL_ENGINE_PLAN.md:224) is **not built** in the engine or the
  report tool, and is not reported. This is a declared departure from that plan line. No R2 of any kind is reported
  for coral (anomaly R2 is NaN, above).
- **Per test year and macro.** Departing from the grid Part's order (PREREGISTRATION_DRAFT.md:136-137: pooled is the
  headline, macro printed beside, grid Q20 a; scores per test year and per group), coral puts pooled second
  (section 6.2, item 4). The macro value (unweighted mean over the 37 ecoregions) is printed beside the pooled value,
  and MAE with its baselines is printed per test year (2016-2019), both report only, from the saved rows.

### 6.2 The order of the report (CORAL_ENGINE_PLAN.md section E, :217-238)

1. **Per programme first.** Reef_Check, FRRP and McClanahan rows with every metric and every baseline; AGRRA (1 test
   visit) and Donner (0) shown with n only. From per_stratum.csv (the engine scores the string stratum per value,
   SPEC_TABLE_MODE.md O18). Per-programme verdict lines (the same D74 rule, jackknife over the groups holding that
   programme) are report only.
2. **By magnitude, per programme.** Bins of the observed label: 0, then the donor rows' quartiles of the positive
   labels, right-closed (the R34 quartile convention), edges taken from train rows at the lead's fit cut, never from
   test rows. Labelled "a target-defined diagnostic, not a headline". Computed from the saved rows.
3. **Flattening guard.** For every arm and every baseline: the mean prediction against the observed mean on test rows
   whose label is at or above the donor rows' upper quartile (edge from train rows at the fit cut). A compressing link
   can win MAE by flattening the tail (CORAL_STATE.md:102-104). Report only, never a choice. Computed from the saved
   rows.
4. **Pooled second**, labelled "mixes programmes" (a declared departure from the grid order, section 6.1).
   **No claim is made from a pooled margin**, following coral Q14's reason text (CORAL_ENGINE_PLAN.md:259; not
   ruled, section 12 item 7) and the coral record; this sets the report order only. The registered verdict is still
   D74 (section 7), which is per ecoregion; it is labelled as mixing programmes. The macro value and the per-year
   rows (section 6.1) are printed here.
5. **Per ecoregion:** n, zero share, programme mix; never ranked by MAE.
6. **Counts printed for every pass and lead:**
   - the share of rows left with no tree after the pool tree drop (V2; n_rows_no_tree, per arm, in
     test_pass_router.json and each lead's records), on the decision surface, the test pass and each guard surface;
   - pool-fallback counts (rows with under 12 valid pool rows; n_rows_pool_fallback);
   - R30-style missing counts: the 0-filled share of every tree column (R30 filled_share; flag above 25%), and the
     marine-heatwave NaN rows (under 60 thresholded days). On the published tables both are 0 (T-FINITE: 0 NaN cells
     in all 74 numeric columns at every lead, coral_data\full_check_console.log); still printed;
   - S1 rows left out for missing context, and units left unscored at a lead;
   - pools holding a month-precision row (disclosure exceptions.yaml:91-96; counted by the report script from the
     saved pools, not by the engine);
   - picks at the penalty grid edge;
   - the donor-only groups (ruling W1, C3 (i)): their names and total train rows, in one report disclosure row
     (kind donor_only_groups, treeroute_report/table.py:542-545, :578-586), from the run record.
7. **Leads:** nowcast, 183 and 365 on the common survey ids. The 365-day row is worded as risk stratification.
8. **Wording:** "given a survey on this date" (every forecast is conditional on a survey happening,
   exceptions.yaml:85-90). If predict-zero wins on Reef_Check, the report says so.

Items 2 and 3, and the per-year and macro rows if the report tool does not print them, are not built in the engine
or the report tool (searched 2026-10-19). They are report-only scripts over the saved rows. They must be written and
their SHA-256 recorded in THIS Part before the freeze, or placed under treeroute_report/ so that
REPORT_TOOLING_SHA256 covers them (section 12 item 8). They can never change a choice or the verdict.
- **Report-only scripts and their SHA-256 (section 12 item 8).** Written 2026-10-20 and fixed after a skeptic review
  the same day; tested on synthetic toy runs only (version 1.2.0: 62 passed, 1 skipped; no real-data run was read). One script does
  all three:
  - magnitude bins (item 2): path D:\treeroute\coral_build\report_scripts\coral_report.py SHA-256
    063be40279a1b4ae0937a21eaec73af98fc4fb379349e34cbdb9c67cf2bacf88
  - flattening guard (item 3): path D:\treeroute\coral_build\report_scripts\coral_report.py SHA-256
    063be40279a1b4ae0937a21eaec73af98fc4fb379349e34cbdb9c67cf2bacf88
  - per-year and macro rows (section 6.1): path D:\treeroute\coral_build\report_scripts\coral_report.py SHA-256
    063be40279a1b4ae0937a21eaec73af98fc4fb379349e34cbdb9c67cf2bacf88
  - beside it, not used by the headline report: test_coral_report.py 6fe435626bdd8c6e6f47cde35a76832d05b2f40c1431d58ef289116874eadc22,
    build_toy_runs.py 83377f9f81855df618f43e62c173ec88f34bcd061d91f849d03913d5de39ff38, README.md
    ffda3308780a8a7b72fe19886ca3df2684f99f9cc7a62f8b8536fbce44fbf690 (same folder).
  - The script refuses any run that is not a headline-eligible headline run (read rule, section 12 item 4); `--toy` admits
    only the synthetic package toy_table. It refuses when its ALL verdict line differs from the engine's record.
  - Since version 1.2.0 (2026-10-20) the script also prints: the per-lead guard reference with the pinned arm's
    guard-surface MAE beside it (guard_reference.csv, from lead.json guard.baseline_*); the R30 0-filled share and the
    marine-heatwave NaN rows (r30_missing.csv; lead 0 from the saved R30, leads 183 and 365 counted from the lead
    tables and labelled so); pools holding a month-precision row (pools_month_precision.csv, counted from the saved
    pools_<pass>.parquet and the builder's pinned list); picks at the penalty grid edge (penalty_edge_picks.csv);
    the blocked jackknife per programme (programme_blocked_jackknife.csv). The engine itself does not save the R30
    share at leads 183/365, marine-heatwave NaN counts, month-precision pool counts or a per-programme jackknife;
    these are report-only counts from saved files. The engine's report tool prints the donor-only row, the overall
    blocked jackknife and its flag, and the pre-clip rate.
- **Flattening-guard edge: decided by owner ruling X4 (2026-10-20): (b).** The primary "severe" edge is q75 of the
  POSITIVE donor-row labels (coral_report.py EDGE_DEFAULT = EDGE_POSITIVE); q75 of ALL donor-row labels is printed
  beside it. The script was changed and re-hashed (lines above) before the freeze; toy tests 62 passed, 1 skipped.

## 7. The single verdict (rule D74)

- One contrast decides: the adopted arm against the **donor-row median** (R34: "the own link-matched trees-off, or the
  donor-row median without a normal"; metrics.py:131, :1141-1166; table_passes.py:584; at each lead
  table_ladder.py:638). Per group: MAE(donor-row median) minus MAE(adopted). Positive means the adopted arm is better.
  Verdict reference = donor-row median by signed R34 + V1; coral Q17 (which recommended the own-link trees-off) is
  not ruled (section 12 item 7).
- The tests run in this order, and the first one that holds gives the tag (metrics.py contrast_tag, :1097):
  1. If the layer declined, the tag is "declined" (the answer is then the donor-row median itself).
  2. **IDENTICAL:** every contrast is 0.
  3. **CANNOT TELL:** the CI cannot be computed (fewer than 3 groups).
  4. **EQUIVALENT:** the whole CI lies inside +-band. Tested before HELPS and HURTS (F42).
  5. **HELPS:** the CI low end is above 0 AND the point estimate is at or above +band.
  6. **HURTS:** the CI high end is below 0 AND the point estimate is at or below -band.
  7. **CANNOT TELL:** everything else.
- **The band (grid Q22 b, R35):** derived from this run's own contrasts, as this is coral's first headline run: the median
  jackknife SE of each tree arm against its own trees-off and each corrector against its placebo, identical contrasts
  left out. registry/bands.csv is not written for tables (TABLE_LIMITS, table_run.py:39-51). The nowcast band
  decides at every lead.
- **If R35 refuses** (no contrast SE is finite, report/metrics.py:1190-1191; it happened on a toy where every arm
  equalled its trees-off, O29, BUILD_NOTES_table.md:80-84; on the tiny data 69 of 71 guard rows had no tree): no
  verdict is given; it is reported as "no band (R35)". No outside band is borrowed, and there is no re-run with a
  changed pool drop.
- Predict-zero is printed beside the verdict. Sign flips between groups are flagged.

**What would count as each verdict, in words:**

- **HELPS:** across the 37 ecoregions, the adopted model's MAE is lower than the donor-row median's, the jackknife CI
  excludes 0 and the point gain is at least one band. Claim allowed: "on these surveys the model beats one constant
  guess shared by all ecoregions (the median of the pass's training visits)". Not allowed: a claim per programme, per magnitude or pooled unless that row says so on its own.
- **EQUIVALENT:** the CI sits inside +-band. Claim: no difference from the constant guess at this precision.
- **HURTS:** the CI lies below 0 and the point loss is at least one band. Reported as a loss to a constant guess.
- **CANNOT TELL:** any other result. No direction is claimed.
- **DECLINED:** the N2 check (nowcast) or the lead guard failed, and the answer is the donor-row median. Reported as
  "declined"; the pinned arm's saved score is shown beside, never as the answer.
- At each lead the same rule runs on that lead's rows under the nowcast band. A failed lead guard makes that lead
  "declined".
- Not a verdict: the sensitivity row, the per-programme and magnitude rows, the flattening guard, the tiny smoke,
  any legacy number.

## 8. Uncertainty: the jackknife over groups

- Leave-one-group-out jackknife at 1.96 (grid Q19 a), over the 37 scored ecoregions. The 46 donor-only groups
  (ruling W) have no contrast and are not jackknife units.
- No multiplicity correction (grid Q21 a), across leads, rows or strata.
- Report only: the blocked jackknife (overlap blocks as the unit). If its SE is more than 20% above the group SE, the
  report flags "group jackknife may be too narrow". The group jackknife still decides.
- No event-clustered bootstrap (G-NODRAW).

## 9. The continuity row

- **None for coral.** The table option does not build the continuity row (TABLE_LIMITS, table_run.py:46-47). The
  legacy hard split (20 donors / 74 tested) used the leaky pool, so a continuity row could not link to its numbers
  anyway (section 10).

## 10. Disclosures

**Signed by ruling V (OWNER_RULINGS_2026-10-06.md:97-114), disclosed here:**

- **V1 decline object.** The donor-row median (R34). Disclosed: the recommendation behind V1 (BUILD_REPORT.md
  section 3 item 1) cited the tiny smoke's pooled TEST MAE (identity trees-off against donor median; 96 test rows of
  4 ecoregions, runs\coral_draft_tiny\smoke\20261019_6a40c185; numbers in BUILD_REPORT.md:75-77 and Part 593). V1 was
  therefore chosen with test rows of this window visible. Andaman Sea is also a scored group and an R21 smoke group.
- **V2 pool tree drop.** The signed default drops the trees of every group in a row's pool and of those groups'
  blocks, on top of the row's own block (SIGNATURES_LORO_ADDENDUM.md:34; route/neighbour.py:29, :180). On the tiny data almost no
  tree was left on the guard rows (69 of 71 at lead 183, 44 of 60 at lead 365; CHECK_REPORT_V.md section 2; plumbing
  only), so a lead guard may be mostly a trees-off test. The full run reports the share (section 6.2).
- **V3 test window** 2016-2019 by leaving out the 38 visits of 2020 (a hand cut, coral Q6 c); a departure from R3;
  chosen after the yearly counts were seen; 2017-2020 is the declared sensitivity row (section 4).
- **V4 table departures, accepted at the freeze** (as S21 did for the grid departures). **V4 is built and installed
  (engine dd7c0984, carried into the installed 930d961c).** The departures moved to TABLE_ACCEPTED_DEPARTURES
  (pipeline/table_run.py:58-73) and are written into the run record as accepted_departures (:331); TABLE_DEPARTURES is empty (:57), so table_departures() returns
  nothing and no table departure is a not-headline reason. Two of the accepted texts still say "await an owner
  signature" and "await the owner" (:63, :72). They are left as written: rewording them would move the engine hash
  and need a new no-op proof. Signing this Part accepts them. The accepted departures
  (TABLE_ACCEPTED_DEPARTURES):
  - neighbour_private_kernel: the router runs through route.neighbour's private kernels, not the approved
    route_neighbour_loro;
  - neighbour_pool_signature: neighbour_pool_loro takes the keyword row_issue_day (U4 needs each row's issue day) and
    route.solve's solvers take n_unpenalised (the intercept alone is unpenalised);
  - fold_gls_entry: the decision surface's per-fold c and GLS models come from FitContext.donor_rows_outside and
    weight_models_for_folds (new entries; for_fold stays unbuilt);
  - table_absent_rows: a non-test row absent from a lead file leaves that lead's banks, c, tolerances, median, GLS
    rows and pools (the grid reading keeps it with 0-filled features); a guard-surface row absent at its lead refuses;
  - table_readings: the owner items O1-O27 of SPEC_TABLE_MODE.md section 7 are built at their listed defaults.
  Also listed as limits (TABLE_LIMITS, table_run.py:39-51): Type 3 not built; features vouched (U2), the G-DERIVED
  recompute and the look-ahead canary are not run on tables; only the neighbour kind is built for tables; scored rows
  are the test marks; no continuity row, nearest-donor distances, report.html or part_draft.md; the band from this
  run; 'freeze' verdicts refused; a time-varying string stratum scored per value.
- **Other drafted defaults, not a ruling-V item.** BUILD_REPORT.md:121-122 lists N3-N16 (SPEC_NEIGHBOUR.md:416-424)
  and P2-P26 (SPEC_CORAL_TABLES.md:369-394) as standing as written. Ruling V answered only the 12 questions of
  BUILD_REPORT.md section 3, so these are unsigned. They are built at their drafted defaults. Signing this Part
  accepts them as built, unless the owner names one to change before the freeze (a change is a new Part, section 11).
- **V5** exclusions (section 3.9): 11 groups.

**Signed by ruling W (OWNER_RULINGS_2026-10-06.md:116-121, 2026-10-20, the owner confirmed option (b)), disclosed here:**

- **W1 V6 (b) donor-only groups** (section 3.9). It replaces V6. 46 kept groups with no test row train trees and
  lend rows; nothing is scored for them. Built defaults C1 (i), C2 (i), C3 (i), C4. **This departs from "every group
  is trained and tested" (ruling D, OWNER_RULINGS_2026-09-28.md:48) for table packages only:** 46 groups in the data
  are never tested. It is disclosed in the run record (donor_only_groups), derived.json (R18:donor_only), the check
  report and one report disclosure row (C3 (i); no TABLE_DEPARTURES entry, so it is not a not-headline reason).
- **W2 no grid re-runs.** The (b) engine's grid no-op proof and full suite ran before the install (section 1); no
  further grid re-run is made.
- **V7** the toy-only replay ran before the full run (PASS). It never reads the coral package.
- **V8** season only as router context, not in the feature-space step.
- **V9 data timing**, kept and disclosed:
  - **the 1-day SST and cyclone gap:** SST and cyclone windows end before C minus 1 day, because source days are UTC
    and survey dates are local. The gap covers the UTC day stamp, not an unknown analysis reach of CoralTemp
    (exceptions.yaml:65-70, :97-102);
  - **ERSST timing:** the Nino-3.4 anomaly is built in the package from the absolute ERSST V6 series with a fixed
    1951-1980 base; the +2-month reach is assumed from ruling R-A, which was written for ERSSTv5 (exceptions.yaml:53-58);
  - **DMI conditional:** dmi_lag2/5/8 stay out of every run until a window bound is signed; the anomaly base period of
    dmi.txt is not stated (exceptions.yaml:59-64).
- **V10 checker coverage:** check_tables.py recomputes 53 of the 74 checked columns. The other 21 rest on the
  builder's look-ahead canary, which rebuilds rows from truncated sources.
- **V11** the r36 test asserts r36_tolerance(1.0) == max(K.GUARD_TOLERANCE_K, r36_floor()). Known package-data test
  failures stay listed: test_catalog_timing_facts.py (3), the defo package tests (6), 7 launcher tests that fail only
  in a subset order.
- **V12** only trees_off_neighbour is wired in route/kinds.py; the other approved neighbour names keep raising.

**Data and design disclosures (exceptions.yaml; owner fields still 'UNSIGNED' unless they name ruling V):**

- **Imputed survey days.** The day of every Donner sample (and most Safaie, which has no label) was filled with the
  15th. 2,128 visits (all train, 1994-2011, none in 2013-2015) get month precision: target date = the month's last
  day, features before the month's first day. Their season context takes only 12 values (exceptions.yaml:10-15,
  :91-96).
- **Repeated-survey averaging.** Several surveys at one site and date are averaged into one visit: 3,080 visits merge
  more than one sample (5,405 absorbed), 1,282 disagree on the label, 5 merge two programmes (exceptions.yaml:22-27).
- **Date clamp not used.** Dates are rebuilt from GCBD Date_Year/Month/Day; the legacy dated file clamped the day at
  28 (exceptions.yaml:16-21).
- **Two mislocated sites** (wrong ocean, both train) are not patched (exceptions.yaml:28-33).
- **Visits without SST** (1,006 on 576 sites, 259 test) or too little SST history (101 more) are not samples
  (exceptions.yaml:34-39).
- **Programme confound.** The drivers identify the survey programme out of sample (AUC 0.948, CORAL_STATE.md:32-34),
  because programmes surveyed different epochs. Hence per-programme first (section 6.2).
- **Survey-triggered sampling.** Surveys are often made because bleaching is seen. Every forecast is conditional on a
  survey happening (exceptions.yaml:85-90).
- **IBTrACS best tracks** are revised after each season; a real-time forecaster had advisories (exceptions.yaml:47-52).
- **MMM in the router context:** an absolute temperature, banned from the trees, kept as penalised context
  (exceptions.yaml:71-76).
- **The one-day gap at the event cut (O27):** at leads 183 and 365 the earliest test rows are issued on the fit cut
  day, and signed R11 keeps labels dated on the cut, so a lead bank, c, tolerance and median may hold a label dated on
  a scored row's issue day. The pool itself is strict (exceptions.yaml:109-114).
- **Verdict reference.** The donor-row median is a constant per pass. HELPS against it is an easier bar than against
  the trees-off (CORAL_ENGINE_PLAN.md:262 Q17 recommended the own-link trees-off; signed R34 names the donor-row
  median for a kind without a normal, and V1 made it the decline object). The own-link trees-off contrast is printed
  beside, and each tree arm against its trees-off feeds the band. The constant is shared by all ecoregions, and its
  rows include the 46 donor-only groups' train rows (1.0 on the lead-0 train visits under V6 (b); section 3.9).
- **Legacy grid narrower in levels.** The legacy coral router searched 15 levels at ratio 0.5; the engine grid is
  7 levels x 5 ratios (every engine level is a legacy level; REPLAY_REPORT.md ATTENTION 4).

**The legacy record:**

- **The legacy pool leak (Part 458, CORAL_EXPERIMENTS.md:3734).** The shipped neighbour pool spanned train AND test
  rows, so other test rows' labels entered the local fit, and its date clause bound only within an ecoregion, so rows
  dated later than the target entered from other ecoregions (coral_glorys2_ab.py:93). The strict pool (U4) fixes it.
- **No legacy number is comparable.** Parts 417-558 used that pool, a 20/74 hard split, 3-7 seed means, other leads,
  the clamped dates, an 80-column model labelled 77 with GHS-POP columns that are not written here, and imputation
  medians over all dates (CORAL_ENGINE_PLAN.md:291; SPEC_CORAL_TABLES.md 3.4). No legacy number is printed beside a
  headline number, and none is used for a choice, except that Part 444 is why V6 (b) was raised as an option
  (Appendix B). No score was put to the owner when V6 was chosen (section 3.9).
- **Test exposure.** Every kept group was a donor or a test ecoregion of the legacy runs, and the 2016-2019 rows of 24
  ecoregions were scored before. The column set, the link set and the pool design (150 / 50 / 12, the 0.5 / 0.25
  centres) were chosen with labels of this test window visible (exceptions.yaml:78-83; split.yaml:14-16).
- **V6 (b) was raised from a legacy test-row comparison** (Part 444, CORAL_EXPERIMENTS.md:2582-2604: donor sets
  compared on held-out test regions, legacy split, leaky pool). The owner chose (b) by ruling W (Appendix B).

**Engine and process:**

- **The four grid runs keep their old engine hash (U5, W2).** The coral engine adds the table option, the neighbour
  kind and the donor-only rule; the grid smokes are byte-identical under it (no-op proof, section 1). Grid runs are
  not re-run.
- **One old failing test:** test_layer_shapes.py::test_functions_take_the_approved_parameters fails on
  weight_model_for_cut's matrix_dir parameter (fit/weights.py:526). The parameter came with the ruling-R RAM tactics;
  it is not in the approved parameters. LIVE fails it too (CHECK_REPORT_V.md ATTENTION 2). Owner item (section 12
  item 2).
- **Full suite of the installed engine 930d961c** (run on the (b) build before the install, 2026-10-20): 3,500
  passed, 33 failed, 28 skipped, 62 xfailed (D:\treeroute\coral_build_v6b\fullsuite.log, last line). The 33 failures
  are exactly the 33 old LIVE failures: stale package/draft tests, CRLF, pdo lag 2 and matrix_dir (Part 594, Part
  595). Earlier: the pre-install V4 build copy 704c8aea (installed V4 engine: dd7c0984) gave 3,483 passed and the
  same 33 (D:\treeroute\coral_build\fullsuite2.log; Part 593).
- **No multiplicity correction** across leads, rows or strata (grid Q21 a).
- **The A7 bias.** The decision surface uses the inner-cut bank (ruling E, L6 b), refit at every lead's guard cut (H2).
- **GLS weights, c and s (ruling E, L5).** The sigma on a row the forest was fitted on is its out-of-bag prediction;
  c and the guard scale include history labels up to the cut. Not a test-window leak.
- Every run's own limits, departures and listed columns are printed in its report.

## 11. What counts as a bug fix after the freeze

- From the freeze on, only bug fixes are allowed (plan 8.1 M5).
- A bug fix is a code change that makes the engine or the builder do what an approved signature, an owner ruling or a
  written rule already says. Examples: a crash, a wrong index, a guard that refuses a valid input, a record written
  wrongly.
- These are NOT bug fixes: a new or changed constant, rule, threshold, ban verdict, column, feature window, gap g,
  link, arm, lead, test year, exclusion, V6 option, scored-row set, metric, report bin or verdict rule; a new package
  file; anything chosen after seeing a result. Such a change needs a new pre-registration Part before any affected run.
- The one carve-out: the declared 2017-2020 sensitivity row (section 4.2). Its builder option and package copy are
  made after this freeze under their own short Part and lock, before its run. It never touches the headline.
- Every bug fix is logged as its own Part, with the output of `py -3.9 -m treeroute_report.freeze verify`.
- An engine bug fix re-runs coral unless the no-op rule holds (derived.json and smoke outputs byte-identical, and
  either a one-group probe stays byte-identical or the changed functions never run on coral). The four grid runs are
  covered by the same no-op rule (U5).

## 12. Items still open (each must be settled before the freeze)

Each open item starts with its marker; the freeze refuses while any marker remains (F-PREREG). "Freeze also checks"
names the precondition that refuses by itself. "By hand" means the freeze sees only the marker.

1. Settled: **V6 (b), ruling W (2026-10-20, OWNER_RULINGS_2026-10-06.md:116-121; the owner confirmed option (b))**, at the built
   defaults C1 (i), C2 (i), C3 (i) and C4 (section 3.9). Written before `plan` and the freeze; the (b) check --deep and
   the (b) smoke ran after it (06:45). Real-data smokes ran before it (tiny smoke 2026-10-19; full-data smoke
   2026-10-20 under (a); section 4.4). The package texts that still call (b) a draft option are item 3.
2. Settled: **matrix_dir, owner ruling X1 (2026-10-20): approved.** Added to ADDED["weight_model_for_cut"] in
   engine/tests/test_layer_shapes.py (with the logging-only keyword echo of the same RAM change, shown to the owner);
   the test passes (6 passed); the engine hash is unchanged (930d961c). Background, done on 2026-10-20: V4 built (section 10); the (b) engine 930d961c passed its
   grid no-op proof against dd7c0984 and its full suite (3,500 passed; only the 33 known failures), was installed
   into LIVE at 06:44 by explicit list (Part 595), and the check report of 06:45 prints 930d961c (section 1). Still
   open: the owner's decision on matrix_dir in the approved parameters of weight_model_for_cut (the old failing shape
   test, section 10). Recommended: approve (it came with the ruling-R RAM tactics). Approving means adding
   matrix_dir to ADDED["weight_model_for_cut"] in engine/tests/test_layer_shapes.py:57 (or to the matching file in
   treeroute/_proposed/). Neither is inside the engine code hash (fingerprint.py:138-145 hashes treeroute/*.py and
   leaves out _proposed/), so the engine hash and the check reports are unchanged. By hand. Freeze also checks:
   F-CHECK-MATCH (the check report's engine code must equal today's).
3. Settled: **the signed package, owner ruling X5 (2026-10-20, signed as drafted).** `datasets/coral` was written by
   make_signed_coral.py --apply (package fingerprint 5b9383f0446df0f12e460cccb2bcd2e58d09fbf22b234cf2943a07aac14644c9;
   record D:/treeroute/coral_build/tools/signoff_records/coral_signoff_record_20261020_130714.json): texts reworded, DRAFT stamps and name replaced,
   signatures written, stale-text scan clean. The continuity_groups.yaml coral entry (empty, X2) was added and the
   protected root confirmed (X3). The checks and `plan` on `datasets/coral` follow. History, done on 2026-10-20: the full stage-2 build, check_tables.py (PASS 52/52),
   the publish to coral_store/20261020_014201, the store root in protected_roots.txt, coral_draft copied into LIVE
   with that store line (section 2); then the (b) package files (split.yaml, exceptions.yaml, ingest/README.md,
   AUDIT_CHECKLIST.md) copied into LIVE coral_draft, `make_split.py --check` ((b) version) on the published tables
   PASS, check --deep GREEN (section 4.4). Still open (line numbers are those of LIVE coral_draft today). The
   package `datasets/coral` is made from coral_draft by D:\treeroute\coral_build\tools\make_signed_coral.py
   (MAKE_SIGNED_CORAL.md), from ONE answers file the owner fills (coral_signoff_answers_TEMPLATE.yaml). Its dry run
   prints every change, including the reworded texts below, and predicts the new fingerprint; `--apply` writes only
   that plan (`--expect-fingerprint`). So the rewording and the signatures happen in one step, and the owner never
   signs a text that still says DRAFT (its stale-text scan refuses one). It edits:
   - the texts that still call (b) a draft option or are stale since the install (text edits; ids in brackets):
     split.yaml:1-2 (it names the pre-(b) coral_tables/make_split.py; [S3]: the (b) file
     D:/treeroute/coral_build_v6b/coral_tables/make_split.py, SHA-256 a69e1c8c..., wrote it from
     coral_data/visits.parquet on 2026-10-19 and checked it on the published lead tables on 2026-10-20) and :5 [S2];
     exceptions.yaml:3-6 (the header lists V6 as signed by ruling V; [X2] adds W1), :125 [X3; X5 aligns its "listed
     in the plan, run record, verdict.json" list with W1's list] and :126 (the owner field) [X4];
     AUDIT_CHECKLIST.md:3 ("**UNSIGNED.** Drafted by the agent") [A2] and :15 [A3]; ingest/README.md:1 "(DRAFT)" [R1],
     :5 "Unsigned. Development and smoke only" [R2], :8-9 "LIVE (hash 65a177bc...) refuses it ... (in progress)" [R3],
     :28 [R4], :29 [R5], :62 (the heading names ruling V only) [R9], :82 (cites TABLE_DEPARTURES at table_run.py:52-70;
     the code now has TABLE_DEPARTURES empty at :57 and TABLE_ACCEPTED_DEPARTURES at :58-73) [R10], :86 [R7], :126
     "From LIVE after the install" [R11];
   - ingest/README.md:35-44, the command block [R8]: :43-44 run make_split.py from D:\treeroute\coral_build\coral_tables,
     the pre-(b) file (SHA-256 c38d76b1...), which checks V6 (a). The (b) file in coral_build_v6b (a69e1c8c...) is the
     one that wrote and checked the (b) split.yaml; the edit points both lines at it. It also says make_draft.py is
     never run on the signed package;
   - AUDIT_CHECKLIST.md section B: the full-build evidence line added next to the tiny-build line at :43 (section 3.2);
   - dataset.yaml (line numbers of LIVE coral_draft/dataset.yaml): name `coral` (:17); version '0.1.0-draft' (:18) set
     to a non-draft value; owner 'UNSIGNED -- DRAFT ...' (:19) and the description's 'DRAFT --' prefix and "nothing
     signed" text (:20; the engine reads the DRAFT stamp from the description) replaced; the header comment (:1-4,
     "DRAFT ... UNSIGNED ... never a headline run") rewritten [D1]; the published store line kept (:23-24); the stale
     comment at :11-12 ("The owner adds the store root ... before the freeze") updated [D2]: the root was added on
     2026-10-20 by the session, and **the owner confirms the protected root** (D:/treeroute/coral_build/coral_store,
     D:/treeroute/registry/protected_roots.txt:8);
   - ban.yaml: the 76 drafted verdicts signed, the header text at ban.yaml:1-4 ("UNSIGNED ... The owner signs them
     before the coral freeze") replaced [B1], coral Q9, Q10 and Q22 answered (CORAL_ENGINE_PLAN.md:254-255, :267), and
     ban.yaml:40's "(owner item)" note settled. The freeze's F-BAN-OPEN does not match the header text (OPEN_DECISION,
     freeze.py:127-134), so only this marker guards it. An answer to Q9, Q10 or Q22 other than "confirm" needs the
     verdict changes written, or the owner's explicit acknowledgement that the drafted verdicts stand;
   - the owner fields of the exceptions.yaml entries still marked UNSIGNED filled (exceptions.yaml:14, :20, :26, :32,
     :38, :45, :51, :69, :75, :82, :89, :95, :107, :113); AUDIT_CHECKLIST.md sections A (rows 1-10, :11-20) and B
     ticked, with the signature at AUDIT_CHECKLIST.md:54 (the freeze does not read its content, :56);
   - the catalog's target facts (catalog.yaml:41-52, pct_bleached: no fact_status line, so 'unverified', :10-11). The
     tool signs them in catalog.yaml itself and rewrites the comments at :1-2 and :10-11 [C1, C2]. Hazard: catalog.yaml:2
     says "edit columns.py, not this file", and make_draft.py rewrites BOTH catalog.yaml and ban.yaml from columns.py
     (ingest/README.md:42). make_draft.py must never run after signing, or the ban and catalog signatures are lost. The
     tool is the only route planned: signing in coral_tables/columns.py instead would need make_draft.py to run FIRST,
     before any ban.yaml signature, would change coral_draft (a new deep check), and the tool refuses a target that
     already has a fact_status (make_signed_coral.py edit_catalog).
   Not edited by the tool (by hand, before the freeze; it is outside the package fingerprint):
   - the package's entry in treeroute_report/continuity_groups.yaml. The report table refuses a package with no
     entry (treeroute_report/table.py:497-499, fix text "continuity_groups: [] when the package has no old hard
     split"). Recommended: `continuity_groups: []`, because no legacy coral number is comparable (Part 458 pool leak;
     section 10). Editing that file moves the report-tooling hash, so it is done before the freeze; it adds
     report-tooling drift to the four grid locks; disclosed (section 1).
   Freeze also checks: F-PACKAGE, F-DRAFT (a DRAFT stamp refuses, freeze.py:624-627), F-BAN-OPEN (ban.yaml:40 refuses
   while its note stays, freeze.py:127-134), F-STORES, G-FACTS (must be 'pass'; today's check flags the unsigned
   target facts, freeze.py:39-40).
   **Order:** (a) the owner reads the tool's dry run (every reworded text, the full-build line, the verdicts); (b) the
   owner fills and signs the answers (morning sheet C1-C4: target facts, ban verdicts with Q9/Q10/Q22, exception
   owner fields, audit checklist and U2); (c) `--apply` writes `datasets/coral` with the texts reworded, the DRAFT
   stamps and name replaced and the signatures written, all at once; (d) continuity_groups.yaml (above) and matrix_dir
   (item 2); (e) check quick, check --deep and `plan` on `datasets/coral`. Every package edit changes the fingerprint,
   so (e) comes after the last one; any later package edit invalidates F-CHECK-MATCH and F-PLAN.
4. Checked by the freeze itself (no marker): the quick check on the whole package and the deep check on the R21 smoke
   groups (ruling M2; section 4.4), at the package fingerprint and engine code this freeze locks (F-CHECK-EXISTS,
   F-CHECK-CONTRACT, F-CHECK-MATCH, F-CHECK-GROUPS, F-CHECK-GREEN, G-FACTS); a current plan from the same fingerprint
   and engine (F-PLAN; run `py -3.9 -m treeroute plan datasets/coral` alone, heavy); every engine constant set
   (F-CONSTANTS). Today's GREEN deep check under (b) is on coral_draft (04b9aab0..., section 4.4); no quick check has
   run under (b); the signed package needs both. The full-data smokes (RULING_V_REPORT.md command 6) score test rows
   of the smoke groups (section 4.4), so they open real test labels. Read rule: only plan.json counts and the
   surface, pool and guard records are read (n_rows_no_tree on surface and guard rows, pool sizes and fallbacks,
   lead.json guard.baseline_*, decision_checks.json, run_record donor_only_groups). No smoke test_preds, score,
   per-group, verdict, ladder or run.log file, and no smoke console log, is opened before the freeze. V1, V2 and V6
   are not reopened from a smoke. Plumbing only; no choice is made from them. The report-only script enforces this
   for itself: it refuses any run that is not a headline-eligible headline run (section 6.2).
5. Settled: **the U2 statement, signed by the owner 2026-10-20 (ruling X5)** (section 13; AUDIT_CHECKLIST.md section B
   of `coral`). The freeze does not see the signature.
6. Settled: ruling U (2026-10-19): U1 table option, U2 (the ruling; its statement is item 5), U3 neighbour router, U4
   strict pool, U5 grid hashes kept, U6 order. Ruling V (2026-10-19, every recommended answer accepted): V1-V5 and V7-V12 (V4 built and
   installed). Ruling W (2026-10-20, the owner confirmed option (b)): W1 replaces V6 (V6 (b), built and installed, engine
   930d961c); W2 no grid re-runs.
7. Settled: **the coral question sheet, every reading below confirmed by the owner 2026-10-20 (ruling X5; Q1-Q22
   "confirm" in the sign-off record)** (CORAL_ENGINE_PLAN.md section 4, :244-267). Ruling V answered
   BUILD_REPORT section 3, not this sheet. Plan step 8 (CORAL_ENGINE_PLAN.md:193) asks for every Q answer here. U6
   (:95) says questions that would change signed rules are asked in short form before the freeze, and until then the
   signed rules apply. The status below is the agent's reading; the owner confirms it, or answers, and this marker is
   then removed. Verdict reference = donor-row median by signed R34 + V1; coral Q17 not ruled.

   | coral Q | Topic | Status | What this Part follows |
   |---|---|---|---|
   | Q1 | item-13 flags | not ruled as a bundle; the pool part overtaken by U3 | built engine values, one row each (Appendix A) |
   | Q2 | pool mode | engine pool overtaken by U4; the C2 c / G5 full and rollout side rows not ruled | strict pool only; side rows out of scope (Scope) |
   | Q3 | close Q28-Q32 pool items | not ruled | strict pool (U4) |
   | Q4 | guard and decline objects | overtaken by V1 (donor-row median, not Q4 b's own-link trees-off) | V1 (section 3.7) |
   | Q5 | scored rows | overtaken by U1 (test marks) | U1 (section 5) |
   | Q6 | test window end | overtaken by V3 (option c, a hand cut) | V3 (section 4.1) |
   | Q7 | repeat surveys | not ruled | averaged, disclosed (exceptions.yaml:22-27; owner field, item 3) |
   | Q8 | one-site groups | overtaken by V5 (option b, not the recommended a) | V5 (section 3.9) |
   | Q9 | column set 77 / 80 | not ruled | drafted ban.yaml; signed in item 3 |
   | Q10 | heat totals | not ruled | drafted ban.yaml (as Q10 b); signed in item 3 |
   | Q11 | season at a lead | overtaken by H3 and V8 | H3 (section 3.4) |
   | Q12 | GLS and c for folds | not ruled | signed R13, R25 (section 3.3); disclosed as departure fold_gls_entry (V4) |
   | Q13 | corrector arms | not ruled | the engine's arms as for grids (section 3.6) |
   | Q14 | headline form | not ruled | signed D74 decides (section 7); per-programme verdict lines report only. A per-programme deciding verdict would be a new rule and needs its own ruling before the freeze |
   | Q15 | legacy harness replay | not ruled; V7 built a toy-only replay instead | toy replay only; the legacy replay is out of scope |
   | Q16 | G-DERIVED route | overtaken by U2 (vouched, no recompute) | U2 (section 3.2) |
   | Q17 | verdict reference | not ruled (it recommended the own-link trees-off) | donor-row median by signed R34 + V1; trees-off printed beside |
   | Q18 | groups with no rows at a cut | overtaken by V5 (option b) | V5 (section 3.9) |
   | Q19 | rivals | not ruled (it recommended building them before this Part) | deferred by signed ruling E, L3 (Scope) |
   | Q20 | imputed day 15 | not ruled | month precision (exceptions.yaml:10-15; owner field, item 3) |
   | Q21 | group id form | not ruled | ecoregion names; smoke groups listed (section 4.4) |
   | Q22 | C3's remaining verdicts | not ruled; partly overtaken by V9 (ERSST V6 timing, DMI conditional) | drafted ban.yaml; signed in item 3 |

8. Settled: **the report-only scripts, final 2026-10-20** (section 6.2: magnitude bins, flattening guard, and the
   per-year and macro rows). Owner ruling X4 chose edge (b); the script was re-hashed (063be402...). Done on 2026-10-20: written as D:\treeroute\coral_build\report_scripts\coral_report.py, fixed
   after a skeptic review, tested on synthetic toy runs only, and its SHA-256 recorded in section 6.2. Still open:
   the owner names the flattening-guard primary edge (section 6.2); if it changes, the script is re-hashed and the
   section 6.2 lines rewritten. The marker is removed by hand once the hash in section 6.2 is final.

## Appendix A. The coral flags as rows of their own

Plan 3.3 flag 13 (APP_PLAN.md, copied in PREREGISTRATION_DRAFT_defo.md Appendix A row 13), one row per part, with
the ruling that settled it.

| # | Flag (plan 3.3 item 13) | Now |
|---|---|---|
| 13a | a 2016-19 test window | ruling V3: 2016-2019 by leaving out the 38 visits of 2020; 2017-2020 declared sensitivity row |
| 13b | leads of 183 and 365 days | ruling I1 (events: 183 and 365 days) |
| 13c | LORO folds from one bank cut at the inner-fit end | C8.neighbour_folds_leave_one_group_out; inner-cut bank (ruling E, L6 b) |
| 13d | a strict pool with no labels after the cut | ruling U4: train rows dated strictly before the issue date, never a test row, within the pass's cut |
| 13e | a pool under 12 rows falls back to the donor-row median | ruling U3; C11.neighbour_pool_min_rows 12; V1 makes the same median the decline object |
| 13f | MMM as penalised context | drafted, UNSIGNED: ctx_mmm penalised router context, disclosed departure (exceptions.yaml:71-76, owner field :75 UNSIGNED); owner item (ban.yaml:40 "(owner item)"; coral Q22 not ruled; section 12 item 3) |
| 13g | max_features 0.15 to 0.10, and 500 to 100 trees per group | C13.tree_max_features 0.10, C13.trees_per_group 100 |
| U1 | the table option | built; the grid-only steps are skipped; date checks kept |
| U2 | feature timing vouched by the owner | section 3.2; the statement is to be signed in section 13 (section 12 item 5) |
| V1 | decline object = donor-row median (neighbour kind) | built, gated on the router kind; grid kinds unchanged |
| W1 | groups with no test row are train-only donors (V6 b) | built and installed (engine 930d961c); read from the marks; C1 (i), C2 (i), C3 (i), C4 |

## Appendix B. Test-exposed constants and disclosures (coral)

| Item | Kind | Origin | Exposure | Since the plan |
|---|---|---|---|---|
| Neighbour centres 0.5 / 0.25 (C12.neighbour_trees_centre, C12.neighbour_context_centre) | engine constant, test-exposed | adaptation.py:1434 | legacy coral router; chosen with test-window labels visible | unchanged (engine_constants.py:186-187) |
| Pool sizes 150 / 50 / 12 (C11) | engine constant | adaptation.py:1434, 1638-1640 | legacy pool design, chosen with test-window labels visible (exceptions.yaml:78-83) | kept by ruling U3. Mismatch: the engine does not flag C11 as test-exposed (engine_constants.py:175-177), so the lock prints False for it; this table is the disclosure |
| 100 trees, max_features 0.10 (C13) | engine constant | plan 3.3 flag 13 | the legacy 500 / 0.15 were chosen on test rows (coral Q1, CORAL_ENGINE_PLAN.md:246) | generic engine values |
| Coral's legacy route penalty | package disclosure | coral_architecture.py:383-397 | sweep scored on test rows | not used: the engine's 35-point grid runs instead |
| The test window | package choice | ruling V3 | hand cut (coral Q6 c) written after the yearly counts were seen | disclosed (exceptions.yaml:116-121) |
| Column and link sets | package choice | CORAL_ENGINE_PLAN.md C3 | chosen with test-window labels visible | disclosed (exceptions.yaml:78-83) |
| One bank at the inner cut (A7) | engine design flag | ruling E, L6 b | neighbouring groups' trees know the inner-score years | refit at the inner cut and at every lead's guard cut |
| Weight model, c and s over the scored groups' fit rows | engine design flag | ruling E, L5 c | out-of-bag sigma on fitted rows | not a test-window leak |
| V1 decline object | ruling choice | BUILD_REPORT A1 (section 3 item 1) | tiny-smoke test MAE seen (96 test rows, 4 ecoregions; BUILD_REPORT.md:75-77) | disclosed (section 10 V1, section 4.4) |
| V6 (b), chosen by ruling W | package choice | Part 444 (CORAL_EXPERIMENTS.md:2582-2604) | V6(b) raised from a legacy test-row comparison (Part 444), legacy split and leaky pool; chosen 2026-10-20 after real-data smokes had opened test labels and an agent had seen the (a) smoke's test line; no score was put to the owner | disclosed (sections 3.9, 4.4) |
| Group jackknife over neighbouring groups | report design flag | grid Q19 a, R34 | band may be too narrow | blocked jackknife printed beside |

## 13. Signature

- **U2 statement (section 3.2).** I vouch for the feature timing of every row of every lead file of the coral package,
  as stated in section 3.2 and AUDIT_CHECKLIST.md section B, including the open timing facts listed there.
  Signed by: the project owner (owner ruling X5; in chat, 2026-10-20: all items accepted, option (b) chosen, signed as drafted)   Date: 2026-10-20
- **V6 option:** (b), by owner ruling W, 2026-10-20 (OWNER_RULINGS_2026-10-06.md:116-121; section 3.9). Decided by
  the ruling itself; no further entry here. Real-data smokes ran before it (tiny smoke 2026-10-19, full-data smoke
  2026-10-20 under (a); section 4.4).
- **Signed outside this file, before the freeze: DONE 2026-10-20 (owner ruling X; sign-off record
  D:/treeroute/coral_build/tools/signoff_records/coral_signoff_record_20261020_130714.json)** (the freeze does not see these signatures): the 76 ban verdicts
  and the ban.yaml:1-4 header (section 12 item 3); AUDIT_CHECKLIST.md:54 (sections A and B); the exceptions.yaml
  owner fields and the catalog's target facts (these four through one answers file and
  D:\treeroute\coral_build\tools\make_signed_coral.py, section 12 item 3); the coral question sheet answers (section 12 item 7);
  the matrix_dir decision (section 12 item 2); the continuity_groups.yaml entry and the confirmation of the protected
  root D:/treeroute/coral_build/coral_store (section 12 item 3).
- **This Part.**
  - Signed by: ____________________ (owner)
  - Date: ____________________
  - SHA-256 of this filled file: written into the Part log by the owner after signing.
  - Part number: assigned when the Part is logged.
- This draft is not the signed Part: the owner signs the filled copy the freeze writes (rulings O3, X6).

## REVIEW LOG

2026-10-20, agent, after a skeptic review of the 2026-10-19 draft (22 issues; all checked against their sources and
applied). Plumbing checks only; no test score was read in that review pass (earlier and later test exposures are
listed in section 4.4). Train-row facts recomputed from coral_data/visits.parquet and
split.yaml (train rows only): donor-row median 1.75 (a) / 1.0 (b); R21 groups and their counts (section 4.4).

- 1 V4 not built (table_run.py:294; record.py:158-161): section 1 hash line, section 10 V4, section 12 item 2.
- 2 V6 written before any real-data run; smoke read rule; smoke scores 4 groups' test rows: items 1 and 4, 4.4.
- 3 ban.yaml unsigned (:2-4; Q9, Q10, Q22): section 2 "drafted verdicts", item 3.
- 4 U2 statement not signed: 3.2, items 5 and 6, Appendix A; AUDIT_CHECKLIST.md:54 and dataset.yaml:22 in item 3.
- 5 coral Q1-Q22 status table: item 7 (marked open; U6).
- 6 "one constant shared by all ecoregions": section 7; median per option in 3.9 and section 10.
- 7 "V6 as signed (a) / V6 amended (b)"; (a) is the default; ruling D departure for (b): 3.9, header, section 10.
- 8 Part 444 quote corrected; Parts 425 and 458 noted; test-exposure row in Appendix B and section 10.
- 9 make_split.py has no (b) mode; hand edits listed: 3.9 table, 4.2 step 4.
- 10 sensitivity row gets its own Part and lock; not-headline mark to be named there: 4.2, section 11 carve-out.
- 11 report-only scripts hashed before the freeze: 6.2, item 8.
- 12 pooled-second, macro and per-year rows, R2 not built: 6.1, 6.2 item 4.
- 13 R35 refusal rule: section 7.
- 14 Q14 cited as reason text, not ruled: 6.2 item 4.
- 15 R21 groups for both options: new 4.4.
- 16 report-tooling hash drift and no-op scope: section 1.
- 17 N3-N16 and P2-P26 drafted defaults: section 10.
- 18 C11 test-exposure flag mismatch: Appendix B.
- 19 option-dependent sections: 3.3, 3.8, 3.9 list.
- 20 pool drop includes the groups' blocks and the row's own block: 3.4, section 10 V2.
- 21 V3 is a hand cut (coral Q6 c): 3.1, 4.1, section 10, Appendix B.
- 22 "coral Q" / "grid Q" prefixes: header note and every Q citation.

Still DRAFT. No line marks the owner as having signed anything.

## CHANGE NOTE 2026-10-20 (morning update, agent)

Facts from Part 593 (engine\PENDING_PARTS.md; it covers the work up to the install and the (b) copy only) and the
files cited (the full build and everything after it); nothing signed; no test score used for a choice in this update
(the test exposures are in section 4.4).
- Section 1: LIVE engine dd7c0984 (V4 built, installed 01:41); (b) engine 930d961c... named; grid no-op PASS on
  dd7c0984; expected `freeze verify` engine and report-tooling drift on the four grid locks, disclosed.
- Section 2: published store 20261020_014201, protected root, full-build counts and proofs, coral_draft fingerprint
  dfa07650... (the signed package gets its own; the freeze fills it).
- Section 3.9: counts refreshed on the full build (identical to stage 1). V6 stays OPEN with both columns; (b)'s
  engine row updated.
- Section 4.4: check quick and deep GREEN (report paths); full-data smoke pool facts only; disclosed that the smoke
  ran before V6 was written, and that its log's last line prints the smoke's test verdict and MAE (seen, not used).
- Section 10: V4 built; the two "await the owner" texts left as written; full-suite result; matrix_dir origin.
- Section 12: items 2 and 3 cut to what is still open (matrix_dir; (b) install; signed package; continuity_groups
  entry, recommended `[]`); item 4 and item 6 updated. Section 13: continuity_groups entry added to the by-hand list.

## CHANGE NOTE 2026-10-20 (second skeptic review, agent)

19 issues checked against their sources and applied; nothing signed; still DRAFT.
- V1 chosen with the tiny smoke's test MAE in view: section 10 V1 line, Appendix B row, section 4.4 (tiny smoke),
  REVIEW LOG wording narrowed to that pass.
- The morning sheet's (b) recommendation (written after the smoke log's test line was seen, resting on Part 444)
  withdrawn; disclosed in 4.4; section 10 legacy sentence names Part 444 as why (b) was raised.
- Section 12 item 1 and section 13: V6 before `plan`, any (b) check and the freeze; real-data smokes already ran.
- C3 and C4 of PLAN_V6B.md section 9 added (3.9 table, item 1).
- (b) package files: prepared in coral_build_v6b (four files differ from LIVE only in their (b) text); not its
  dataset.yaml; split.yaml regenerated there from the published store (write guard, make_split.py:188-190); 4.2 step 4.
- Item 3: LIVE coral_draft/dataset.yaml line numbers (:1-4, :11-12, :17-20, :23-24), no ATTENTION lines; protected root
  confirmed by the owner; AUDIT_CHECKLIST B full-build line; package-edit order; G-FACTS must pass.
- 4.4: 217 lead-0 bank rows and 79 scored rows (plan.json); Bahamas scores 1 row under (a); review reads listed.
- 4.2: not-headline reasons since V4 (table_run.py:136-147).
- Appendix A 13f: drafted, UNSIGNED.
- 3.2: full-build U2 evidence; section 2: "822 row-leads".
- Section 10: suite log fullsuite2.log, 28 skipped.
- 3.8 and 6.2 item 6: T-FINITE, 0 NaN cells on the published tables.
- Part 593 (engine\PENDING_PARTS.md) is stale after the install (title "FINAL RE-PROOF PENDING"; no entry for the full
  build, the publish, the protected root, the coral_draft copy, the LIVE checks, the full-data smoke or the smoke-log
  exposure). It is outside this file; it is to be updated by the main session (or a Part 594 logged).

## CHANGE NOTE 2026-10-20 (V6 (b) decided, agent)

Owner ruling W (OWNER_RULINGS_2026-10-06.md:116-121, 2026-10-20 06:44, the owner confirmed option (b)). Facts from Part 595
(engine\PENDING_PARTS.md), the install manifest, the (b) check report and the (b) smoke's plan.json counts and pool
records. Nothing signed; still DRAFT. No test score was read in this update.
- Header and section 3.9: the open V6 question, the V6_CHOICE field, both of its "owner decision pending" markers and
  the (a)/(b) comparison table removed. V6 (b) written as decided, with ruling W, its date and the built defaults
  C1 (i), C2 (i), C3 (i), C4. Only the (b) counts are kept: 83 kept groups (37 scored + 46 donor-only), 11,338 train
  and 2,312 test visits at lead 0, 2,046 surface rows in 33 groups, 78 blocks, 8 absent rows, verdict reference 1.0.
- Section 1: LIVE engine 930d961c (installed 06:44; 9 changed + 1 new file; engine\_moved_coral_20261020_064437);
  its grid no-op proof vs dd7c0984 (RESULT: PASS) and full suite (3,500 passed, the same 33 failures); W2 no grid
  re-runs; report tooling moved again (treeroute_report/table.py).
- Section 2: package fingerprint 04b9aab0... (the (b) package files in LIVE coral_draft).
- Section 4.4: R21 groups under (b) only; check --deep GREEN report check_deep_04b9aab0fb5a.json with its full
  fingerprint; no quick check yet under (b); (b) smoke plumbing (bank rows 157, scored rows 42 in 3 groups, pools 50,
  0 fallbacks, no-tree 0/24, 2/18, 0/14, donor_only_groups Austral Islands); (a) smoke kept as superseded history.
- Sections 5, 6.2 (donor-only disclosure row; report-script SLOT marked OPEN BEFORE FREEZE), 8, 10 (ruling W block:
  the departure from ruling D for table packages; full suite; :331), Appendix A (W1 row), Appendix B (V6 row).
- Section 12: item 1 settled (ruling W); item 2 cut to matrix_dir; item 3 adds the package texts that still call (b)
  a draft option (split.yaml:5, exceptions.yaml:125-126, AUDIT_CHECKLIST.md:15, ingest/README.md:28-29, :86) and the
  exact owner-field lines; item 4 read rule widened to plan.json counts and run_record donor_only_groups; item 6 adds
  ruling W. Still open: matrix_dir, continuity_groups, the protected-root confirmation, the package signatures, the
  U2 statement, the coral question sheet and the report-only scripts' hashes.
- Section 13: the V6 blank replaced by the ruling; protected-root confirmation added to the by-hand list.

## CHANGE NOTE 2026-10-20 (report scripts, signing tool and skeptic review, agent)

Two skeptic reviews (report scripts with the signing tool; this draft with the morning sheet). Their valid issues
are applied. Nothing signed; still DRAFT. No real-data test score was read: the report scripts were run on
synthetic toy runs only.
- Section 4.4: "Smoke scores are never read before the freeze" replaced (it contradicted the exposures listed below
  it): from 2026-10-20 on, under the read rule, no smoke score is read; earlier exposures listed. The R21 rule is
  unchanged, but under (b) Austral Islands (donor-only) replaces Banda Sea and Molucca Islands among the first 4
  kept groups. plan.json bank_rows explained (all rows of the bank sites, train and test marks together).
- Section 6.2: the report-script slot filled (coral_report.py, SHA-256 7fb3a477..., one script for all three lines;
  the tests, toy builder and README hashed beside); a new OPEN BEFORE FREEZE marker for the flattening-guard edge;
  the items printed by neither tool listed. Section 12 items 4 and 8 updated to match.
- Section 10: 704c8aea named as the pre-install V4 build copy (installed V4 engine: dd7c0984).
- Section 12 item 2: how matrix_dir is approved, outside the engine code hash. Item 3 rewritten around
  make_signed_coral.py (one answers file; dry run, then `--apply --expect-fingerprint`): the full list of stale
  package texts with their text-edit ids (split.yaml:1-2 and :5; exceptions.yaml:3-6, :125, :126;
  AUDIT_CHECKLIST.md:3, :15; ingest/README.md:1, :5, :8-9, :28, :29, :35-44, :62, :82, :86, :126); the make_split.py
  that wrote and checked the (b) split (coral_build_v6b, a69e1c8c..., not the pre-(b) c38d76b1...); the make_draft.py
  hazard for the catalog and ban signatures; and the order (dry run read, answers signed, one `--apply`, then
  continuity_groups and matrix_dir, then the checks and `plan`). Section 13: the four package signatures go through
  the tool.
- Correction to the second skeptic review's note above ("split.yaml regenerated there from the published store"):
  split.yaml's own header says it was written on 2026-10-19 from coral_data/visits.parquet by the (b) copy of
  make_split.py; on 2026-10-20 that file (a69e1c8c...) checked it on the published lead tables (PASS, Part 595).
- Not done here: engine\PENDING_PARTS.md Part 595 still lacks two facts (the (b) smoke opened 42 test labels in 3
  groups, no score read; G-FACTS is still flagged). That file is the main session's to update.

## CHANGE NOTE 2026-10-20 (report script 1.2.0, agent)

A second skeptic review of the report scripts. Its valid issues are applied. Nothing signed; still DRAFT. No
real-data run was opened: tests ran on the synthetic toy runs only (62 passed, 1 skipped; the skip is the
donor-only test on the ok toy, as expected).
- Section 6.2, the hash slots only: coral_report.py 1.2.0 is 4ce7e69e... (all three lines); test_coral_report.py
  a08a2908..., README.md d33bb9f9...; build_toy_runs.py unchanged (83377f9f...). The 1.0 files (7fb3a477...) are kept
  in report_scripts\_moved\before_saved_records_20261020. The 1.1.0 files (93feabc1..., never recorded here) were
  edited in place and not kept.
- Promised outputs (sections 6.1 and 6.2 item 6) now printed by coral_report.py:
  - the guard reference per lead with the pinned arm's guard-surface MAE and its own trees-off MAE beside
    (guard_reference.csv; lead.json guard.*; at the nowcast decision_checks.json decline_baseline and adoption.json
    surface_mae);
  - the R30 0-filled share (r30_missing.csv): as saved at lead 0 (derived.json R30), and at leads 0, 183 and 365 on
    the donor rows and the scored rows, counted from the lead tables; at lead 0 the counted donor-row shares must
    equal R30, or the script refuses;
  - the marine-heatwave NaN rows (r30_missing.csv): rows with a NaN in any mhw_* column, and apart the rows with a
    NaN in mhw_days_365 (under 60 thresholded days), per lead, counted from the lead tables;
  - pools holding a month-precision row (pools_month_precision.csv), counted from the saved pools and the builder's
    list coral_data\month_precision_rows.csv, pinned by SHA-256 cfa18268... (read without a flag for a non-toy run);
  - picks at the penalty grid edge (penalty_edge_picks.csv), from adoption.json, adoption_lead_<L>.json and the
    engine's printed run.log lines, each checked against adoption.json;
  - the blocked jackknife per programme (programme_blocked_jackknife.csv), checked against the engine's own
    functions in a test.
- Facts the engine does not save (so the script counts them and labels them "counted from the lead table (not an
  engine record)" or "not an engine record"): the R30 share at leads 183 and 365; any marine-heatwave NaN-row count;
  any month-precision flag or pool count (no "precision" in the engine code outside _proposed); the blocked jackknife
  per programme and at the leads; one nowcast reference value and its donor-row count (one median per fold is
  saved).
- The flattening-guard edges: both printed; (a) q75 of all donor-row labels is still the DEFAULT; (b) q75 of the
  positive donor-row labels is labelled as the owner's option. The labels now follow EDGE_DEFAULT.
- Fail loud: a missing or disagreeing guard field, decline baseline, run.log block or line, R30 share or
  month-precision list is a refusal (exit 2), not a blank.
- By hand, for the owner (not changed here; outside the hash slots): section 6.2 line "34 passed, 1 skipped" should
  read "62 passed, 1 skipped"; the "Printed by neither tool" sentence is out of date (each item above is now
  printed by coral_report.py); exceptions.yaml:94 says the run counts month-precision pools, which no engine code
  does, so that text or the citation "exceptions.yaml:91-96" needs a correction; the OPEN BEFORE FREEZE marker's
  "swap EDGE_PRIMARY and EDGE_POSITIVE in flattening_table" should read "set EDGE_DEFAULT = EDGE_POSITIVE".


### Change note 2026-10-20 (main session, after owner ruling X)
- Owner ruling X (OWNER_RULINGS_2026-10-06.md section X): matrix_dir approved (X1); continuity_groups empty (X2);
  the coral_store protected root confirmed (X3); flattening edge (b) (X4); every drafted signature item signed as
  drafted through make_signed_coral.py (X5). The pre-registration itself is signed on the filled copy the freeze
  writes (X6).
- coral_report.py re-hashed for X4: 063be402...; test file 6fe43562...; README ffda3308....


### Change note 2026-10-20 13:1x (main session)
- Every OPEN BEFORE FREEZE marker settled by owner ruling X (X1 matrix_dir, X2 continuity [], X3 protected root,
  X4 edge (b), X5 signatures as drafted): the signed package `datasets/coral` (fingerprint 5b9383f0...) exists.
- U2 statement signed (section 13). This Part itself is signed on the filled copy the freeze writes (X6).
