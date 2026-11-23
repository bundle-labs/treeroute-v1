# Rival board: the owner's commands

Written 2026-10-20; updated 2026-10-21 for ruling Z (pm25 not re-run; Random Forest out of core), for ruling AA
(no phase 2; LightGBM tuning with early stopping; the lean export) and for ruling AC (LightGBM tunes and refits at
255 bins; only a trial that ran to the 800 cap is extended; the out-of-core Random Forest kept). Every command below
is for YOU to run in PowerShell. Nothing here runs by itself. Times marked (x) are estimates; only coral is measured.
The LightGBM times assume trials stop near round 350 (the "middle" case of AA_CHECK_REPORT.md section 4, re-priced
for 255 bins in AC_REPORT.md); the fire probe gives the first real figure. The Random Forest times come from the bench with a real (unbuffered) disk read rate of 118.9 MB/s
(`_bench\z2_rf_bench_results.json`, "estimate").

## 0. Before anything

1. **Sign the rival Part first:** `D:\treeroute\rivals_build\PREREGISTRATION_DRAFT_rivals_common.md`. No rival test
   score may exist before it is signed (rulings Y4, Z4, AA5, AC4).
   **No phase 2 (ruling AA1):** the donor-only 10-fold folds and Board B are dropped. This file never had commands
   or times for them, so nothing below changes; the plan's 21-61 h and 4-12 h phase-2 rows are simply not run.
2. **Before EACH session (every evening you start a step):**
   - **close every app you can: games, game launchers, browsers, chat apps.** With apps open this PC often has only
     about 4.5 GB free, and several steps need more. Check the free RAM before you start:
     `[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,1)` (GiB free). Coral needs
     about 2.5, the fits about 5-6, the fire export about 8.3;
   - the PC must not sleep (Settings > Power: Never);
   - The Random Forest needs about **4.5 GiB free** RAM on its own for NDVI
     and defo (the whole NDVI job about 5.2-5.8 GiB). It checks before each fit and refuses if the RAM is not free
     ("REFUSED: rf needs about X GiB"): then close apps and resume. The watchdog stops any job at 12 GiB;
   - no engine run may be running (the rival commands take the engine's own heavy-job lock and refuse if it is held);
   - check free disk: `Get-PSDrive D` (27 GB free today).
3. **Open PowerShell and set these once per window** (copy all lines):

```powershell
cd D:\treeroute\rivals_build
$CFG = "D:\treeroute\rivals_build\rivals_production.yaml"
$ENG = "C:\Users\<user>\Desktop\data set for reserch paper\engine"
function rivcli { py -3.9 -B -m rivals.cli @args --config $CFG }   # not R or RV: those are PowerShell built-in aliases (Invoke-History, Remove-Variable)
```

`rivcli` is a short name for `py -3.9 -B -m rivals.cli ... --config <production config>`. Every command needs the
config; without it the command refuses. There are no new command flags in ruling Z. Ruling AA adds ONE export flag,
`--full-engine-checks` (it runs the two engine guard steps the lean export skips). **Do not add it** unless I ask:
the default lean export writes the same files. **Never use it on NDVI** (the step it adds back is estimated at 7-23 h
there). The commands below do not use it.

## 1. How to watch, resume and fix

- **Progress of a board:** `py -3.9 -B -m rivals.cli status --out $OUT` (safe while a job runs; shows the last step,
  whether its process is alive, finished trials, refit and scored leads, and the last log lines).
- **Live log of a board:** `Get-Content $OUT\rivals.log -Tail 15 -Wait` (Ctrl+C stops the watching, not the job).
- **Live log of an export:** `Get-Content D:\treeroute\rival_export\<package>\<run>\lead_<L>\export.log -Tail 15 -Wait`.
- **Resume after a crash, a power cut or a kill:** run the SAME command again with `--resume` (export, tune, refit).
  Finished pieces are skipped by hash; at most one fit is redone (a Random Forest fit resumes from its last
  checkpoint, every 10 trees). `lock`, `score` and `board` are short: just rerun.
- **"REFUSED: ... stale heavy-job lock ... from dead pid ..."** (the last job died): run `rivcli unlock`, then your
  command again with `--resume`. `unlock` refuses if the lock's process is still alive.
- **"REFUSED: ... needs about X GiB ..."** (RAM or disk): close apps or free disk, then resume.
- Any other REFUSED line: stop and send it to me. Never edit a file in an export or a board by hand.

## 2. Coral (first, end to end; about 15 minutes, under 2.5 GiB RAM)

Close apps first (section 0.2).

```powershell
$RUN = "D:\treeroute\runs\coral\headline\20261020_f3b8e3da"
$OUT = "D:\treeroute\rivals\coral\20261020_f3b8e3da"
rivcli export --run $RUN --package "$ENG\datasets\coral" --lead all --resume      # 1-2 min, ~2.4 GiB; test keys only, no test label
rivcli init --run $RUN --export D:\treeroute\rival_export\coral\20261020_f3b8e3da\lead_0 --out D:\treeroute\rivals --extra-learners hgb_l1
rivcli tune --out $OUT --resume                                                   # ~4 min (measured 227-230 s on the AC dry passes; RF ~90 s, hgb_l1 ~115 s of it)
rivcli lock --out $OUT                                                            # seconds
py -3.9 -B -c "import json,sys; sys.path.insert(0,'.'); from rivals import harness as H; print(H.picks_content_sha(json.load(open(r'$OUT\picks.json'))['picks']))"
```

- **Check:** the last line must print `5ad9502f975c771ecbc7406d98a57eaba5b308d3920fbd5d77f8269e2567639b` (the dry
  picks under ruling AD; the older values 3b5a33f1..., 2a3e224e... and 14b18f11... are no longer right). If it prints anything else: STOP and send it to me (do not refit or score).
- Then, lead by lead:

```powershell
foreach ($L in 0, 183, 365) { rivcli refit --out $OUT --lead $L --resume }       # ~1 min each (x; lead 0's guard re-uses the tuning trial, no extra fit)
foreach ($L in 0, 183, 365) { rivcli score --out $OUT --lead $L }                # seconds each; opens the test labels
rivcli board --out $OUT                                                           # writes $OUT\board.md
```

## 3. Fire (second; export ~1.3 h (x), fitting ~2.4-3.7 h (x), up to +2.4 h if trials extend)

The export runs the engine's own derive: about **8.3 GiB RAM**. Close everything (check the free RAM, section 0.2).

```powershell
$RUN = "D:\treeroute\runs\fire\headline\20261017_869d1f38"
$OUT = "D:\treeroute\rivals\fire\20261017_869d1f38"
rivcli export --run $RUN --package "$ENG\datasets\fire" --lead all --resume      # ~1.3 h (x; lean, was 2.6 h), 8.3 GiB; disk ~1.4 GB
rivcli init --run $RUN --export D:\treeroute\rival_export\fire\20261017_869d1f38\lead_0 --out D:\treeroute\rivals
rivcli probe --out $OUT --lead 0                                                  # a few minutes; send me probe.json
```

- **Stop here and send me** `$OUT\probe.json`, the export's total time (last lines of its export.log) and the
  output of this line (the lean export's first real check, ruling AA4):
  `(Get-Content D:\treeroute\rival_export\fire\20261017_869d1f38\lead_0\export_manifest.json | ConvertFrom-Json).timings_seconds`
  Its `derive` should be about 1,700 s (the headline's derive took 5,841 s with the count the lean export skips).
  I re-price the plan from them before the long fits.
- Then:

```powershell
rivcli tune --out $OUT --resume                                                   # ~2-2.8 h (x; RF ~1.6 h of it), ~2-3 GB RAM
rivcli lock --out $OUT
foreach ($L in 0, 6, 12) { rivcli refit --out $OUT --lead $L --resume }          # ~15-30 min each (x; RF 5-14 min)
foreach ($L in 0, 6, 12) { rivcli score --out $OUT --lead $L }
rivcli board --out $OUT
```

## 4. PM2.5 (third; the EXISTING headline, not re-run: ruling Z1)

The pm25 headline of 2026-10-07 is used as it is. Its export would refuse on two engine-identity checks (I4, I5);
ruling Z1 accepts them for this run only, as data in the production config. The export then MUST pass every parity
check P1-P15 at every lead. P15 runs by itself (it refits the run's 6 tree banks, about 21-25 min each, and compares
their fingerprints with the run's). **Any refusal means: stop and send it to me (I ask you); do not retry with other
options.** Export all leads in ONE call (`--lead all`; one lead alone is refused). If it refuses part way, every lead
manifest it wrote is moved aside, so no half export can be used. Export ~2 h (lean, was 5 h) + ~2.5 h for P15 (x);
fitting ~1.9-3.5 h (x; RF 1.4-2.2 h), up to +3.2 h; RAM ~4.3 GB for the fits (P15's peak RAM is logged in export.log
and in each lead's manifest; not yet measured at full size).

**Optional, your choice:** the lean export copies pm25's R30 test-year shares from the 2026-10-07 run, so it cannot
show whether today's engine would count them differently (the exported values are not affected; P15 checks them).
If you want that audit, add `--full-engine-checks` to the export line below: about +2.7 h. Default: without it.

```powershell
$RUN = "D:\treeroute\runs\pm25\headline\20261007_74e67609"
$OUT = "D:\treeroute\rivals\pm25\20261007_74e67609"
rivcli export --run $RUN --package "$ENG\datasets\pm25" --lead all --resume      # ~4.5 h (x) with P15
rivcli init --run $RUN --export D:\treeroute\rival_export\pm25\20261007_74e67609\lead_0 --out D:\treeroute\rivals
rivcli tune --out $OUT --resume
rivcli lock --out $OUT
foreach ($L in 0, 6, 12) { rivcli refit --out $OUT --lead $L --resume }
foreach ($L in 0, 6, 12) { rivcli score --out $OUT --lead $L }
rivcli board --out $OUT
```

- **Check after the export:** `D:\treeroute\rival_export\pm25\20261007_74e67609\ACCEPTED_ALL_LEADS.json` must exist
  (it is written last, only when every lead passed). Without it, `init` refuses.
- board.md shows an "ACCEPTED ENGINE DIFFERENCE" line for pm25: that is expected (disclosed in the rival Part).

## 5. Defo (fourth; export ~3.3 h (x), fitting ~8-14 h (x), up to +19 h if many trials extend)

Disk: the export is about 8.5 GB and each lead's fit-set copies about 6.7 GB. Free space first (section 7).
RAM about 4.7 GiB (the RF uses up to its 4.5 GiB budget; close everything).

```powershell
$RUN = "D:\treeroute\runs\defo\headline\20261017_d71c61f4"
$OUT = "D:\treeroute\rivals\defo\20261017_d71c61f4"
rivcli export --run $RUN --package "$ENG\datasets\defo" --lead all --resume      # ~3.3 h (x)
rivcli init --run $RUN --export D:\treeroute\rival_export\defo\20261017_d71c61f4\lead_0 --out D:\treeroute\rivals
rivcli probe --out $OUT --lead 0
rivcli tune --out $OUT --resume                                                   # the longest step (RF ~4.7 h of it): split over nights; --resume continues
rivcli lock --out $OUT
rivcli refit --out $OUT --lead 0 --resume                                         # RF ~0.3-0.7 h (x)
rivcli score --out $OUT --lead 0
#   delete the lead-0 fit-set copies now (section 7), then:
rivcli refit --out $OUT --lead 1 --resume                                         # RF ~0.5-1.4 h (x, guard fit + refit)
rivcli score --out $OUT --lead 1
rivcli board --out $OUT
```

## 6. NDVI (last; ONE LEAD AT A TIME; export 2-14 h (x) in all, fitting ~8.7-15.5 h (x), up to +8.4 h)

**Never add `--full-engine-checks` to an NDVI export.** The step it adds back (R30's count over about 604M rows and
256k files) was never timed for NDVI and is estimated at 7-23 h per export call.

Disk per lead: export ~5.7 GB + the engine's temp pools while exporting (~6-7 GB, freed after) + fit-set copies
~10 GB. Delete the defo export and copies first (section 7). Export RAM about 6.1 GiB; fitting about 5.2-5.8 GiB
(the RF reads its fit file 25-30 times per fit: about 15-23 min of disk reads per fit).

**6a. A smoke check first (recommended, about 20-40 min (x)):** an NDVI smoke run (4 groups) under LIVE, its export
at every lead, and the bank-fingerprint proof (P15). It catches a fault in the NDVI export path before hours of work.

```powershell
py -3.9 -B pt\integ\smoke_run.py "$ENG\datasets\ndvi"                       # prints SMOKE DONE <folder>
$SM = "<that folder>"                                                         # D:\treeroute\rivals_build\runs\ndvi\smoke\<name>
py -3.9 -B -m rivals.cli export --run $SM --package "$ENG\datasets\ndvi" --lead all --resume --config pt\integ\integ_smoke.yaml
py -3.9 -B pt\integ\parity_p15.py $SM "pt\integ\_export_smoke\ndvi\$(Split-Path $SM -Leaf)" pt\integ\parity_p15_ndvi_smoke.json
```

The last line must print `P15 pass`. If not, stop and send it to me.

**6b. The board:**

```powershell
$RUN = "D:\treeroute\runs\ndvi\headline\20261016_d1de3158"
$OUT = "D:\treeroute\rivals\ndvi\20261016_d1de3158"
rivcli export --run $RUN --package "$ENG\datasets\ndvi" --lead 0 --resume
rivcli init --run $RUN --export D:\treeroute\rival_export\ndvi\20261016_d1de3158\lead_0 --out D:\treeroute\rivals
rivcli probe --out $OUT --lead 0
rivcli tune --out $OUT --resume                                                   # RF ~4 h of it (x): split over nights; --resume continues
rivcli lock --out $OUT
rivcli refit --out $OUT --lead 0 --resume                                         # RF ~0.7-1.6 h (x)
rivcli score --out $OUT --lead 0
#   delete the lead-0 fit-set copies AND the lead-0 export folder now (section 7; the board keeps what it needs)
rivcli export --run $RUN --package "$ENG\datasets\ndvi" --lead 6 --resume
rivcli refit --out $OUT --lead 6 --resume                                         # RF ~1.3-3 h (x, guard fit + refit)
rivcli score --out $OUT --lead 6
#   delete the lead-6 copies and the lead-6 export folder
rivcli export --run $RUN --package "$ENG\datasets\ndvi" --lead 12 --resume
rivcli refit --out $OUT --lead 12 --resume                                        # RF ~1.2-3 h (x)
rivcli score --out $OUT --lead 12
rivcli board --out $OUT
```

## 7. Freeing disk (only you delete; the code never deletes)

- After a lead is scored, `rivals.log` prints `may delete` lines: each names a fit-set copy in
  `D:\treeroute\rivals_scratch\<package>\<run>\` and its size. They are rebuildable caches; their hashes stay in the
  board (ruling Z3: you delete them by hand). To delete one lead's copies (example: defo lead 0):
  `Remove-Item D:\treeroute\rivals_scratch\defo\20261017_d71c61f4\lead_0_*`
- An export folder may be deleted once its lead is SCORED (the board keeps the lead's manifest and units file):
  `Remove-Item -Recurse D:\treeroute\rival_export\<package>\<run>\lead_<L>`
  Keep lead 0's export until `lock` is done. A deleted export can be rebuilt with the same export command; the
  board accepts it if its content is the same. **Not for pm25:** keep all its lead folders and
  `ACCEPTED_ALL_LEADS.json` until its board is done (the harness checks the seal against every lead's manifest).
- Test files you may delete (synthetic, rebuildable): `D:\treeroute\rivals_build\review_tests_z\_pt\heavy1` and
  `D:\treeroute\rivals_build\pt\zfin\heavy1` (about 1 GB each).
- Never delete anything under `D:\treeroute\rivals\` (the boards) or `D:\treeroute\runs\`.

## 8. Time and RAM summary (x = estimate)

| Step | Time | Peak RAM | Disk added |
|---|---|---|---|
| coral, all | ~15 min (tune measured ~4 min) | ~2.4 GiB | <0.1 GB |
| fire export / fits | ~1.3 h / 2.4-3.7 h (+2.4 h) (x) | 8.3 GiB / ~2-3 GB | ~1.4 GB + copies ~1 GB |
| pm25 export (+P15) / fits | ~2 h + ~2.5 h / 1.9-3.5 h (+3.2 h) (x); no headline re-run | P15 not yet measured / ~4.3 GB | ~4 GB + copies ~3 GB |
| defo export / fits | ~3.3 h / 8.0-13.9 h (+19 h) (x) | ~4.7 GiB | ~8.5 GB + ~6.7 GB per lead |
| ndvi smoke check | 20-40 min (x) | under 6 GiB (x) | ~1 GB |
| ndvi export / fits | 2-14 h / 8.7-15.5 h (+8.4 h) (x) | 6.1 GiB / ~5.2-5.8 GiB | per lead ~5.7 GB + ~10 GB |
| **All** | **about 33-62 h of machine time over about 7-12 overnight sessions** (+33 h if every LightGBM trial runs to 800 and extends) | | |

Of the fitting, the Random Forest alone is about 16-23 h (ndvi 7.2-11.6 h, of which ~2.8 h disk reads; defo
5.5-6.8 h; fire 2.0-2.8 h; pm25 1.4-2.2 h; coral 2 min); rulings AA and AC do not change it (AC3 keeps it as built).
Early stopping (AA) shortens the LightGBM tuning, and the lean export skips the R30 count (about 0.16 h defo, 1.15 h
fire, 2.73 h pm25) and the separability check (up to about 1.6 h in all). Before AA the total was 40-70 h over 8-14
sessions. Ruling AC moves the total by less than an hour either way, so it stays at about 33-62 h:
- 255 bins in tuning make each tuning round about 14% slower than before AA (the per-round inner scoring, with no
  bin saving to pay for it; under AA's 63 bins the two about cancelled);
- the extra 255-bin lead-0 guard fit of AA is gone (one 800-round fit per LightGBM learner and problem);
- LightGBM and Tweedie fitting, all problems (x): about 8.5 h if trials stop as early as on coral, 12.1 h in the
  middle case, 19.0 h if no trial stops (under AA: 9.6, 12.6 and 18.4 h; before AA: 17.5 h).
The "+" figures are the worst case where every LightGBM and Tweedie trial runs to the 800 cap without stopping and
is extended to 1600 (AC2: a trial that stopped early is never extended); about a fifth higher than under AA, for the
same per-round reason. On coral no trial came near the cap. After fire's export and probe I send a re-priced table.
