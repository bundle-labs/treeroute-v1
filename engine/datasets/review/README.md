# Review sheets: ban list and column facts (the Q34 review)

Four spreadsheets, one per headline problem. Each row is one column a model could read. Each sheet comes pre-filled with two things: what the shipped run actually did, and the rulings you have already made. You fill in two columns, `owner_verdict` and `owner_timing_signed`. That is the whole job.

| File | Rows | What is in it |
|---|---|---|
| `pm25_columns.csv` | 178 | 166 panel columns, GFED burn (2 + a pixel count), EDGAR (5 + a flag), router context (month, lat), the target |
| `fire_columns.csv` | 200 | 166 panel columns, fire-history sidecar (19), fire-driver sidecar (8), router context, the target and its 4 count columns |
| `defo_columns.csv` | 178 | 166 panel columns (the annual mean/min/max columns are listed under their parent), the 8 `h_*` history columns, the target and its 3 pixel counts |
| `ndvi_columns.csv` | 202 | 166 panel columns (V11 is the target row), GFED burn (new, lag 1), 28 water-memory features, 6 router-context entries |

The keys `cell_id`, `region`, `year` and `month` have no row, because a key is never a feature. Deadline for the verdicts and the signed timing facts: **Tue 27 Oct** (the freeze; APP_PLAN.md 9.1 item 5).

## ATTENTION: read these first

1. **The index audit landed after these sheets were written, and it replaces some rows.** It is `../_stores/INDEX_WINDOW_AUDIT.md` and `index_facts.yaml`. For the rows below, sign against the audit, not against the sheet:

   | Column | Sheet says | Audit says (proposed, with sources) |
   |---|---|---|
   | nino12, nino3, nino4, nino34, soi, pdo, tna, tsa, iod, noi, ao, nao, pna, wp, epo, sam | window unknown | plain monthly value: lag 0 |
   | tni | window unknown | 5-month running mean, centred: lag 2. The centring comes from a data test only (audit open item 2) |
   | co2 | plain month: lag 0 | proposed as reaching about 1 month ahead: lag 1. This is an assumed fact and needs your choice (audit open item 1) |
   | V11, V12 used as drivers on a monthly target | lag 0 or 1, per the V11 audit | lag 1. V11 reaches up to 15 days into the next month |

2. **The two files write "the calendar month" in different ways.** These sheets use stamp `period_end` with a 1-month window looking back. The audit uses stamp `period_centre` with a 1-month centred window. Both mean exactly the calendar month, so nothing is wrong. But the M1 schema must pick one, and the import has to convert the other (open item for the build).

3. **Rows whose `notes` say "OWNER CHECK" or "FOOTER FINDING".** These are places where the shipped code, a ruling or two documents disagree. There are 1 on PM2.5, 7 on fire, 9 on defo and 12 on NDVI. Filter the `notes` column for them.

4. **Rows whose `missing_share_note` says "R30 FLAG".** These columns are more than 25% missing in donor rows, or they vanish in a test year. They need an explicit `keep` with evidence, or a `ban`. `keep_unreviewed` is not enough.

5. **Rows whose `co_measured_candidate` starts with "yes".** Each one needs your explicit true or false. Write it in `owner_timing_signed`, as shown below.

6. **There is no "lag" verdict in the engine.** A row marked `lagged` today becomes `keep`. The engine works out the delay itself, from the timing facts you sign.

## How to fill `owner_verdict`

Write one of these words:

| Write | Plain meaning |
|---|---|
| `keep` | Let the model read it. |
| `keep_unreviewed` | Keep it without a full review. Allowed only if its timing facts are signed, it does not reach ahead in time, and it has no lineage flag. It is listed in every report. |
| `freeze` | Let the model see one old photo of the column, taken before the test period, and nothing newer. |
| `ban:<reason>` | Lock it away. Reasons: `label`, `coproduct`, `target_derived`, `replaced_by_engine`, `post_event_state`, `lookahead_unfixable`, `trend_proxy`, `incomplete`, `structural`, `post_window_snapshot`. For example `ban:trend_proxy`. |
| `conditional` | Keep it out of every engine run and save it for a later side experiment. This is PM2.5's current treatment of its optical columns. |
| `watch` | Keep it, and list it in every report. |

- Put the evidence, a Part number, in `notes`, for example `Part 431`. Every verdict needs one.
- An empty cell means "not reviewed yet".
- The mean/min/max columns of one parent share one verdict, and so do the members of a sum group. That covers defo's aggregates and MOD44B's `V15 + V17 + tree_cover_pct = 100`.

## How to fill `owner_timing_signed`

The timing facts are the columns `cadence`, `stamp`, `window_length`, `window_align` and `units`, plus the legal range.

| Write | Meaning |
|---|---|
| `yes` | The facts on this row are right. |
| `assumed:<length> <unit>` | The window is unknown, but you sign a maximum, for example `assumed:5 month`. The engine then delays the column enough to cover that maximum. |
| `fix:<what>` | A fact is wrong. Say the right value, for example `fix: window 3 month centred`. |
| add `; co_measured=true` or `; co_measured=false` | Your answer for a co-measured candidate, for example `yes; co_measured=false`. |

Banned rows may stay empty, because timing facts only matter for kept columns. A kept column without signed timing facts cannot enter the headline run (G-FACTS).

## What the other columns mean

- **current_verdict / current_reason / source_locator**: what the shipped run did, with any ruling since then applied. Rulings are tagged, for example `[ruling Q2]` or `[ruling Q3 a]`. `source_locator` points at the exact file and line.
- **stamp and window**: think of a monthly total as a receipt for the whole month. It is stamped at the month's end (`period_end`) and looks back one month (`backward`). ONI is a 3-month average centred on its month, so it peeks one month ahead. The plan's allowed stamps are period_start, period_centre, period_end and event_date. "unknown" means nobody has confirmed it yet.
- **lag_note**: what the engine's lag rule (R8) would conclude from these facts. It is information only; you never type a lag.
- **co_measured_candidate**: "yes" if the column comes from the same product family or sensor as the target, in the same period, or if its lineage points back to the target. The reason is given after the colon.
- **missing_share_note**: read from each parquet file's footer (its table of contents), never from a full scan. It counts NaN only, over all cells rather than just the picked units. Fill codes such as -32768 are counted separately ("a fill code is the footer min or max"), and zeros are not counted as missing. Sidecars stored as one file per region give a whole-period share, not a per-year one.
- **notes**: surprises, then the cadence sample (5 small regions x 2010 and 2015), then the source notes, then "other problems: ..." with this column's verdict in the other three sheets.
- **fact_status**: always `unverified` in this seed.

## Surprises found while building these sheets

- **V20_burned_binary is monthly.** PM2.5 bans it as an "annual" look-ahead summary (pm25_ban.py:34), but the stored column changes month by month. `burn_month_count` and `burn_doy_mean` are the annual ones.
- **The burned-area columns switch sensor at the split.** FireCCI uses MODIS up to 2019 and OLCI from 2020 (ingest_firecci_fire.py:28, 37-40). Night lights switch from DMSP to VIIRS between 2013 and 2014.
- **conflict_\* are monthly counts, filled with zero.** They are not annual (AUDIT_REPORT.md item 5 got that wrong). In the defo matrix they are never NaN: they are constant zero in 25 of 42 groups, and `eddi_observed` is constant 1 in 23 of 42. So the missing-value rule, which counts NaN, would not actually flag them. Plan flag 7 still asks you to rule on them.
- **Some columns are held flat after a year.** `hdi` is held at its 2015 value, and `fert_n` / `fert_p` at 2013. For WorldPop population, the ingest says 2020 is held for 2021-23, while defo_ban.py says those years are extrapolated.
- **Five column families are stored as log1p, not raw units:** `gdp_pc`, `ntl`, `road_density`, `travel_time` and the `aglw_*` columns.
- **Fire's `lgt_missing` is exactly "year before 2013"**: a year key in disguise.
- **Defo feeds lat and lon to its trees.** The other three problems never do.
- **Some columns are kept by NDVI's run89 but banned by the other three problems:** co2, the food prices, scpdsi, eddi and eddi_observed.
- **The shipped fire run also fed columns that Q3 a now bans:** the FREEZE snapshots, the snow day-of-year columns, and AMO/SPEI. The AMO/SPEI ban carries an OWNER CHECK, because PM2.5's reason (empty in 2023) does not reach fire's 2003-2022 coverage.

## After you finish

Save as CSV (UTF-8) under the same file name. If Excel changes `ban:trend_proxy` or long numbers, open the file with Data > From Text/CSV and set every column to text. The generator (`../_tools/export_review_csv.py`) **never overwrites these files**. Run again, it refuses. For a fresh blank set, run it with `--out-dir <new folder>`.
