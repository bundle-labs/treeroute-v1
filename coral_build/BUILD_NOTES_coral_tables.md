# BUILD NOTES: coral tables + package draft (builder key `coral_tables`)

Written 2026-10-19. Scope: `coral_tables\`, `coral_data\`, `engine\datasets\coral_draft\`. No engine code was touched.
Spec followed: `SPEC_CORAL_TABLES.md`. Results and the owner command: `coral_tables\README.md`.

## What was built

- `coral_tables\build_tables.py` (stage 2, new). Ports coral_forecast.py:105-175 and coral_extra_drivers.py:70-122
  with C (and the gap g) in place of the event date; imports coral_mhw_features and coral_extra_drivers; copies
  mmm_from verbatim (build_tables.py:137). Writes the 3 lead files, manifest, audit, drops, log, tiny package;
  `--publish full`.
- `coral_tables\check_tables.py` (new). Independent contract and look-ahead checker, with a negative control.
- `coral_tables\columns.py`: `feature_end` added (role `key_feature_end`); 85 columns. `make_draft.py`: the role added
  to KEY_ROLES; rerun (catalog 85 columns, ban 76 verdicts).
- `coral_draft\exceptions.yaml`: the five SPEC section 6 items added (17 entries); the CoralTemp entry now says g = 1.
  `AUDIT_CHECKLIST.md`: statement 6 (feature_end), g = 1, checker evidence. `ingest\README.md`: keys, commands, counts.
- `coral_tables\README.md` (new): tiny results, time and RAM, the full-build PowerShell command.

## Deviations from SPEC_CORAL_TABLES.md (smallest possible; reason each)

1. **Resume is all-or-nothing, not per lead** (SPEC 4.3). One pass over the sites computes all three leads from one
   SST slice (SPEC 4.4), so a partial rebuild would cost the same pass. A rerun with the same inputs, code and
   parameters skips; otherwise all three files are rebuilt and the old ones move to `coral_data\_moved\`.
2. **Canary sample** (SPEC 3.4 item 3): every 50th row of the sorted candidate sample (build_tables.py:504), the same
   rows at every lead, not every 50th row of each lead file. Tiny mode: every row (as specified).
3. **Replay copy uses the raw Sample_ID lat/lon** from events_dated (build_tables.py:599), not the 4-decimal site
   coordinates written to the table. The legacy files were computed from raw coordinates, so this is the only way
   the cyclone distances and abslat can match at 1e-9. The written rows use the site coordinates (SPEC 1.2).
4. **cyc_days_since_close is measured from C** (not C - g), over the window [C - g - 3650, C - g), capped at 3650
   (build_tables.py:368). With g = 0 it equals the legacy value; columns.py already said "C minus the day".
5. **mhw_thr_gap** returns NaN without calling nanmedian on an all-NaN array (build_tables.py:334). Same value as the
   legacy line, no warning.
6. **feature_end includes the dmi months** although dmi_lag* are `conditional`: the columns are written, so their
   windows count. It changes nothing today (the dmi bound equals the nino34a bound: the last day of the month before
   C's month).
7. **`--publish` does not edit dataset.yaml.** It prints the target line and the protected-root line for the owner
   (build_tables.py:772). Reason: the draft's store pointer is an owner-visible change after the proof.
8. **Stage-2 drop reasons**: a lead-L row is dropped as `stage1_short_history_L<L>` from the stage-1 flag
   (build_tables.py:563), or as `stage2_short_history` / `stage2_mmm_rule` when the cut C - g leaves too little
   history or no MMM month. None occurred in the tiny groups.

## A bug found and fixed during the tiny build (worth knowing)

The first tiny run failed the replay check: cyc_mindist differed from the legacy files by 5e-5 relative. Cause:
numpy 2.0.2 (NEP 50). A plain Python float latitude with the float32 track arrays makes `hav` run in float32. The
legacy loop passed `ev.lat.values[i]`, an np.float64. Fix: cyc_features casts lat/lon to np.float64
(build_tables.py:343). After the fix the replay is exact (0 difference) on 579 x 68 and 579 x 65 cells.
The legacy hav still evaluates cos(lat2) in float32 (a float32 array times a Python float), so the independent
checker allows 1e-6 relative on cyc_mindist only (check_tables.py:56); measured 3e-8.

## Tests run (from D:\treeroute\coral_build\engine unless noted)

| Test | Result |
|---|---|
| `build_tables.py --build tiny` (coral_tables) | pass: 897 rows per lead; asserts, canary (2,691 row-leads) and replay (exact) all pass; 173 s, peak 0.45 GB |
| `check_tables.py --build tiny` (coral_tables) | PASS, 52 checks (contract T-FILES..T-NAMES; look-ahead recompute 2,691 x 53, 0 cells differ) |
| `check_tables.py --build tiny --negative-control` | PASS: a cut one day later gives 23,354 differing cells |
| rerun `build_tables.py --build tiny` | skips (manifest match) and refreshes the tiny package, 2 s |
| `load_package` on coral_draft and on coral_data\tiny\package | both load (17 exception entries) |
| `table_spec` + `read_tables` (build copy, in progress) on the tiny package | pass: 63 tree, 5 context, stratum programme |
| `pytest tests/test_nonames.py` | 42 passed, 1 failed: 4-digit year '2026' at line 1 of derive/table.py, labels/rows.py, package/table.py, pipeline/table_passes.py, pipeline/table_router.py. **Not my files** (other builders' docstrings); see the request below |

## Requests for files I do not own

- **Engine table builders**: `tests/test_nonames.py::test_engine_tree_has_no_names_years_drives_units_or_month_arithmetic`
  fails on the 4-digit year '2026' in line 1 of derive/table.py, labels/rows.py, package/table.py,
  pipeline/table_passes.py and pipeline/table_router.py. Remove the year from those docstrings.

## Open items (owner)

- P1: the 2016-2019 window departs from R3 (Q6 c); sign before any full coral smoke or run.
- The full build is not run (U6). Command: coral_tables\README.md. About 26-30 minutes, about 1 GB.
- After `--publish full`: repoint coral_draft dataset.yaml to `coral_store/<stamp>/` and protect `coral_store`.
- P14: the DMI anomaly base period is not stated in dmi.txt (recorded in the manifest); dmi_lag* stay conditional.
- P17: g = 1 is the default; the CoralTemp analysis reach itself is still unverified.
- P13: ERSST V6 reach +2 months is assumed from R-A (written for ERSSTv5).
- All other P items of SPEC_CORAL_TABLES.md section 7 stand as drafted.
