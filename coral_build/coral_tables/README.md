# coral_tables: the builder of the coral lead tables (package side, not engine code)

Written 2026-10-19. Design: `D:\treeroute\coral_build\SPEC_CORAL_TABLES.md`. Table contract:
`D:\treeroute\coral_build\SPEC_TABLE_MODE.md` section 1. Nothing here is engine code; the engine only reads the
lead files.

**ATTENTION**
- **Run the full build only after the engine's table option is installed** (ruling U6; SPEC_CORAL_TABLES.md
  ATTENTION). P1 (the 2016-2019 window) is signed: owner ruling V3 (OWNER_RULINGS_2026-10-06.md:105), disclosed in
  coral_draft/exceptions.yaml (check R3).
- **The full build takes about 26-30 minutes** (extrapolated from the tiny build, below). It is an owner command.
- An interrupted full build starts again from the beginning: the three lead files are written together at the end.

## Files

| File | What it does |
|---|---|
| `build_visits.py` | Stage 1 (7 seconds): visits, marks, census -> `coral_data/visits.parquet`, `visits_census.json`, `month_precision_rows.csv` |
| `build_tables.py` | Stage 2: one feature table per lead (0, 183, 365) -> `coral_data/<build>/lead_<L>.parquet`, plus `build_manifest.json` (inputs, code hashes, parameters, counts, proof, timing), `rows_audit.parquet`, `dropped_rows.csv`, `build.log`. `--build tiny` also writes the smoke package `coral_data/tiny/package/`. `--publish full` copies a finished full build to `coral_store/<stamp>/` |
| `check_tables.py` | Independent checker: the table contract (T-FILES ... T-MARK) and a look-ahead test that recomputes the MMM, SST heat, cyclone, nino34a and season columns from data cut at C - g / C with its own code. `--negative-control` moves the cut one day later and must find differences |
| `columns.py` | The one column list (85 columns: 9 keys, target, stratum, 5 context, 69 tree columns) |
| `make_draft.py` | Writes `catalog.yaml` and `ban.yaml` of `engine\datasets\coral_draft` from columns.py |
| `npz_map.py` | Read-only memory map of a STORED .npz member (the SST compact is never loaded whole) |

## The tiny build (run 2026-10-19 on the build copy)

Groups (the SPEC default, P19): **Andaman Sea, Maldive Islands, Moreton Bay (eastern Australia), North and central
Red Sea.** Each has train rows at all six bank cuts and test-window rows (63, 81, 75 and 49 test rows).

```
cd D:\treeroute\coral_build\coral_tables
py -3.9 -u build_tables.py --build tiny
py -3.9 -u check_tables.py --build tiny
py -3.9 -u check_tables.py --build tiny --negative-control
```

| | lead 0 | lead 183 | lead 365 |
|---|---:|---:|---:|
| rows (train / test) | 897 (629 / 268) | 897 (629 / 268) | 897 (629 / 268) |
| groups / sites | 4 / 384 | 4 / 384 | 4 / 384 |

Visits not written: 99 with no SST series, 1 after the test window (`coral_data/tiny/dropped_rows.csv`). No stage-2
drop (MMM rule) in the tiny groups.

Proof (`coral_data/tiny/build_manifest.json`):
- asserts passed on all 2,691 row-leads. Largest "source day minus issue day": SST -2, cyclones -2, index months -1,
  feature_end -1 (every lead; g = 1).
- look-ahead canary: every row-lead (2,691) rebuilt from sources truncated at the cut: 0 mismatches.
- replay against the legacy `forecast_features_L0/_L365.parquet`: 579 visits x 68 columns (lead 0) and 579 x 65
  (lead 365): largest relative difference 0 (exact).

Checker (`coral_data/tiny/check_report.json`): 52 checks, all passed. The look-ahead recompute matched on 2,691
row-leads x 53 columns (largest relative difference 3e-8, in cyc_mindist; MMM within 2.3e-6 C). Negative control:
with the cut one day later, 23,354 cells differ, so the checker can see a one-day look-ahead.

The build copy's table reader (`treeroute.package.table.read_tables`, in progress) loads the tiny package:
63 tree columns, 5 context columns, stratum `programme`.

### Time and RAM

| | tiny (measured) | full (extrapolated) |
|---|---:|---:|
| row-leads written | 2,691 | 41,066 (13,694 + 13,686 + 13,686) |
| canary row-leads | 2,691 (every row) | about 820 (every 50th row) |
| replay rows (g = 0 copy, leads 0 and 365) | 1,158 | up to 17,106 (8,553 eligible visits) |
| row computations | 6,540 | about 59,000 |
| feature time | 2.8 min (26 ms per computation) | about 25 min |
| total wall time | 2.9 min (173 s) | **about 26-30 min** (+ cold HDD reads of 8,157 site slices and an 889 MB hash) |
| peak working set | 0.45 GB | about 1 GB (rows kept in RAM until the end: 41k x 74 values, plus the replay copy) |
| checker | 23 s | about 6 min |

## The full build (OWNER COMMAND; do not run before the engine install)

Close large programs first (guard() stops the build cleanly below 2.5 GB free RAM). In PowerShell:

```powershell
Set-Location D:\treeroute\coral_build\coral_tables
py -3.9 -u build_tables.py --build full *>&1 | Tee-Object -FilePath D:\treeroute\coral_build\coral_data\full_build_console.log
py -3.9 -u check_tables.py --build full *>&1 | Tee-Object -FilePath D:\treeroute\coral_build\coral_data\full_check_console.log
py -3.9 -u build_tables.py --publish full
```

Then (owner): set `stores.target` in `engine\datasets\coral_draft\dataset.yaml` to the line `--publish` prints
(`D:/treeroute/coral_build/coral_store/<stamp>/lead_{lead}.parquet`) and add `D:/treeroute/coral_build/coral_store`
to `D:\treeroute\registry\protected_roots.txt`.

A rerun with the same inputs, code and parameters does nothing. A changed input, code file or parameter rebuilds
all three leads; the old files move to `coral_data\_moved\<stamp>\<build>\` (nothing is deleted).

## Options

- `--sst-gap-days g` (default 1): SST and cyclone windows end before C - g (UTC source days vs local survey dates,
  P17). g = 0 is the legacy setting.
- `--groups "<a>;<b>"` (tiny only): other groups, separated by semicolons (names hold commas).
- The test window 2016-2019 is signed (V3). The 2017-2020 sensitivity row must NOT be built by rerunning
  `build_visits.py --test-years 2017-2020` with the default `--out`: that overwrites coral_data/visits.parquet (no
  move-aside, build_visits.py:294). Use its own `--out` folder; stage 2 then needs a `--visits-dir` option that is
  not built yet. Steps: coral_draft/ingest/README.md, section "The 2017-2020 sensitivity row".
- split.yaml (V5/V6): `py -3.9 -u make_split.py --check` recomputes the left-out groups from visits.parquet;
  `--write` rewrites coral_draft/split.yaml (old file moved to _moved/v_split_<stamp>/); `--lead-dir <build>` reads
  a built folder instead (rerun after the full build).
