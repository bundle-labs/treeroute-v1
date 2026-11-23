# Commands for the owner: post hoc SHAP (rulings AW1-AW5), protocol v3

Run each command in your own PowerShell window, one at a time. Do not run any other engine job or rival board while
one of these is running: the rebuild's lock lives in this folder and cannot see `D:\treeroute\tmp`. Close games,
browsers and other large programs first (15.8 GB RAM; see the RAM note below).

**Owner rulings of 2026-11-13 (rulings file, section AY):** scope (i), the nowcast of each problem (AY1); D14 (b), so
`--recorded-path-map` is valid (AY2); D8's 1e-12 alternative, so `--arcsine-tolerance 1e-12` is valid (AY3). The coral
nowcast pilot is done. The remaining scope (i) commands are in section 2, in the suggested order: fire, PM2.5, defo,
NDVI.

**Restarting.** Every command can be started again after a stop. Finished pieces are skipped only when their files and
their identity still match (the registered sample, the scripts, the engine folder, the path decision D14 and the D8
tolerance). Engine bank checkpoints are reloaded by their tree fingerprints; the census and R30 checkpoints of the
engines that have them are reloaded too.

**Logs.** Each command logs to `D:\treeroute\analysis\shap_v1\logs\`, one line per step, with timestamps.

**Results.** These go to `D:\treeroute\analysis\shap_v1\out\<problem>\lead_<L>\`:

- `treeroute\`, `rival_<model>\`: `rows.parquet` (row-level SHAP at the feature and the variable level),
  `background_keys.parquet`, `meta.json`, `exactness.json` (rivals);
- `compare\`: `AW3_table.md`, `AW4_table.md`, `AW4_main_row.json`, `pairs.parquet`, `importance.parquet`,
  `families.parquet`, `per_lead.json`, `bootstrap_stats.parquet`.

**Decision D8 (ruled 2026-11-13, AY3: the 1e-12 alternative).** The rebuilt coral model reproduces its saved predictions
bit for bit on every row of every identity-link and log_c arm, and on the identity twin (lead 0) and the trees-off twin
(lead 183). Its arcsine arms differ in the last bits on 84 (lead 0) and 80 (lead 183) of 2,312 rows: at most 1.06e-15
and 9.3e-15 relative (8 and 58 ulps). The arcsine link itself changed in the last bit after the reinstall (stored fire
arcsine normals: 3,590 of 3,597 reproduce; log and identity normals: all). The commands below use
`--arcsine-tolerance 1e-12`, a TRUE relative bound, valid only if you rule D8 that way; leave it out to keep bit
identity (coral 0 and 183 and fire 0 then stop at gate E8).

**Decision D14 (ruled 2026-11-13, AY2: option (b)).** Their run fingerprints hash the package's static
table with its full path, and the package moved with the 2026-11-08 reinstall (same file, same size, same time stamp,
other folder). Without a decision their rebuild stops at the input pre-check E3a within 15 s to 3.5 min. Options:

- (b) `--recorded-path-map`: hash today's file under the run's recorded engine folder; accepted only when gate E3m finds
  the file's content SHA-256, size and time stamp equal to the freeze locks' records (smoke: PASS for all three). The
  commands below use it, valid only if you rule D14 (b).
- (a) a real copy of the package folder at the recorded path (an administrator makes the folder and copies with
  `robocopy /COPY:DAT /DCOPY:T`, so time stamps are kept), read with `tr_rebuild.py --package-dir`. Only (a) also makes
  the NDVI census copy D9 possible (a further `checkpoint_proof.py check`, not built here).

**RAM.** Gate E0 stops the rebuild in the first minute when the engine's own pre-flight says it will be refused after
the census. Free RAM needed after the census: fire about 8.4 GiB, NDVI about 6.2 GiB, PM2.5 about 5.4 GiB, defo about
2.9 GiB. During this session about 6.3 GiB were free, so fire stopped at E0 (as designed). `--ignore-ram-warning`
overrides it.

## 1. The pilot: coral bleaching, nowcast (scope i), treeroute plus its five SHAP-able rivals

```
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\run_shap.py --problem coral --scope i --arcsine-tolerance 1e-12
```

This first command registers the coral sample, which freezes protocol sections 3 and 8.

| Step | Time | Peak RAM | Disk |
|---|---|---|---|
| sample (1,000 visits, 37 regions; registered in `SAMPLE_REGISTER.txt`) | 10 s | < 0.5 GB | < 1 MB |
| treeroute rebuild, lead 0 (measured: 3.3-3.5 min) | 3-4 min | 1.3 GB | 0.1 GB kept; 2.5 GiB free temp space required (freed) |
| treeroute SHAP, two levels (measured: 100 s for 250 rows) | 6-8 min | < 1 GB | 25 MB |
| rivals: ridge, LightGBM, Tweedie, HGB L1, RF (measured: 93 s for 250 rows; RF rebuilt in 7 s) | 5-7 min | < 1.5 GB | 40 MB |
| comparison (2,000 region draws, two levels) | < 1 min | < 0.5 GB | 10 MB |
| **total** | **17-22 min** | **1.5 GB** | **0.2 GB** |

Read `rebuild\coral\lead_0\gates.json` (every gate), `out\coral\lead_0\treeroute\meta.json` (the additivity,
evaluator and S-ZERO results) and `out\coral\lead_0\compare\AW3_table.md`.

## 2. Each scope option, per problem

**First, per problem, the pre-check (minutes).** It registers the problem's sample and runs the rebuild's gates E0,
E1, E2, E3a and E3m, then stops, so a moved input or too little RAM shows in minutes, not hours:

```
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\run_shap.py --problem fire --scope i --arcsine-tolerance 1e-12 --recorded-path-map --precheck
```

Measured in this round on smoke registers: sample 18 s (fire) to 2.5 min (NDVI); pre-check 15 s (defo), 40 s (fire),
2.4 min (PM2.5), 3.3 min (NDVI).

For scope (ii) or (iii), replace `--scope i` with `--scope ii` or `--scope iii`. The rebuild of every tree lead runs in
ONE engine process, so the census and derive run once per problem. Times are wall times on this machine for N = 1,000.

**Where the times come from.** Rebuild: the headline run logs (plus the coral measurements). SHAP: the coral
measurements and the map's 29-61 ms per depth-8 tree for 14,000 pairs, doubled for the variable-level walk (coral:
one walk 50 s, two walks 100 s for 250 rows). Rivals: the boards' own timings, SHAP doubled likewise. They will be
refined from the pilot's log before the next command is given a firm time.

| Problem | Scope (i) nowcast | + (ii) one forecast lead | + (iii) every lead | Peak RAM | Disk kept (temp) |
|---|---|---|---|---|---|
| coral | 17-22 min | + 15-19 min (lead 183: rebuild 3.2 min, SHAP, rivals) | + 7 min (lead 365, declined: rivals only) | 1.5 GB | 0.4 GB (2.5 GiB) |
| PM2.5 | 6.9-7.5 h: census 0.8, derive 3.5, pool 0.5, bank 0.4, sampled routers 0.1-0.2; SHAP 0.6-0.8; rivals 0.9-1.3 (RF 10 min rebuild + 20-40 min SHAP) | + 2.4-3.1 h (lead 6: pool 0.4, bank 0.4, routers 0.1, SHAP 0.6-0.8, rivals 0.9-1.3) | + 0.9-1.3 h (lead 12, declined: rivals only) | 6.5 GB | 1.2 GB per lead (5.5 GiB) |
| NDVI | 21-25 h (census and R30 about 17 h, derive 0.6, pool 0.6, bank 2.1, routers 0.1, SHAP 0.4-0.6, rivals 2.0-2.8) | + 2.0-2.8 h (lead 6, declined: rivals only) | + 2.0-2.8 h (lead 12, declined: rivals only) | 7 GB | 1.3 GB per lead (8 GiB, plus a 5.4 GB RF refit copy) |
| fire | 2.8-3.3 h: census 0.2, derive 1.6, pool 0.2, bank 0.1, GLS 0.06, routers and the identity twin 0.1, SHAP 0.2-0.3, rivals 0.4 | + 0.4 h (lead 6, declined: rivals only) | + 0.4 h (lead 12, declined: rivals only) | 8.4 GiB free needed | 0.6 GB (2 GiB) |
| defo | 12-14 h: census and derive 0.3, vault and labels 2.7, pool 3.1, bank 1.2, 42 region routers 3.5 (21 regions: 1.75), SHAP 0.2-0.4, rivals 1.4-2.0 | + 7-9 h (lead 1: pool 1.6, bank 1.2, silent step 0-1.5, routers 2.9, SHAP, rivals) | none (lead 1 is the last) | 7 GB | 1.5 GB per lead (6 GiB, plus a 3.7 GB RF refit copy) |

Totals over the five problems, run one after another:

- (i): 43-50 h.
- (ii): 55-66 h.
- (iii): 59-71 h.
- Disk kept is about 8 GB for (ii).
- The NDVI census copy (D9) would save about 15-17 h, but only with D14 (a) and a passing `checkpoint_proof.py check`.

Halving the defo regions (`--defo-regions 21`, owner decision D10) saves about 1.75 h at lead 0 and 1.45 h at lead 1.
It also halves the regions of the defo bootstrap. The runner refuses a `--n` or `--defo-regions` that differs from the
registered sample.

**Suggested order.** coral (pilot) -> fire -> PM2.5 -> defo -> NDVI. NDVI and defo are the longest; each needs an overnight
slot.

**Per-problem commands, scope (i).** For (ii) or (iii), change `--scope`. The `--recorded-path-map` and
`--arcsine-tolerance` switches are valid only under rulings D14 (b) and D8.

```
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\run_shap.py --problem fire --scope i --arcsine-tolerance 1e-12 --recorded-path-map
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\run_shap.py --problem pm25 --scope i --recorded-path-map
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\run_shap.py --problem defo --scope i
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\run_shap.py --problem ndvi --scope i --recorded-path-map
```

**Useful switches:**

- `--precheck` registers the sample and runs the input pre-checks, then stops.
- `--dry-run` lists the steps without running them.
- `--skip-rf` leaves the RF rebuild for a later run (the longest rival step).
- `--with-pinned` also explains the pinned arm at the declined leads (D5 alternative; labelled; about +9 h).
- `--ignore-ram-warning` goes on past gate E0.

**What the smokes of this round exercised** (each under 8 minutes, all PASS, under `smoke\` only):

- coral, the real headline: sample; leads 0 AND 183 rebuilt in one engine process (6.6 min; the lead-183 TableLadder
  path for the first time; D8 licensed at lead 183 by lead 0's E5a and the trees-off twin E5b); treeroute SHAP, the
  five rivals and the comparison at both leads; resume skips; the D8-reversal and new-sample resume rules; the
  comparison's refusals of a model from another sample and of other background keys;
- the samples of PM2.5, NDVI, fire and defo on the real exports (18 s to 2.5 min; NDVI lead 12: 491 background keys
  removed for missing router context);
- the input pre-checks of PM2.5, NDVI and fire (without the map fire stops at E3a; with it E3a and E3m pass) and defo;
  gate E0 on fire;
- the engine smoke worlds with each run's own engine snapshot: PM2.5 (per-unit, PM2.5 engine), fire (per-unit, GLS
  corrector arm; also the B1 background), defo (region kind, arcsine arm, every unit) and defo restricted to the sample
  with the real defo arm (region kind, log_c corrector): every gate including the region E9 and E10 proofs.

**Not exercised by any smoke:** the BARDL loader (not built); the Kraft LSTM (D7); the RF memmap path for large refit
sets (PM2.5 1.3 GB, NDVI 5.4 GB, defo 3.7 GB); the defo lead-1 region path; rivals other than coral. Each is first run
by its own owner command, and its gates stop it on any difference. **The smoke worlds build their references on today's
OS and libraries, so they cannot detect a difference between the old and the new installation; only a real headline
rebuild (the coral pilot) can.**

Repeat the quick checks on the morning of a long run if anything was installed in between. Each takes 1-2 min:

```
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\tests\smoke_unit.py
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\tests\smoke_world.py --problem pm25
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\tests\smoke_world.py --problem fire
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\tests\smoke_world.py --problem defo
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\tests\smoke_world.py --problem defo --arm log_c_corrector_unweighted --restricted
```

## 3. What a stop means

- **Exit code 3** is a stop rule. The step's `gates.json`, `exactness.json` or `FAILED.json` names the gate and its
  values. No SHAP value exists for that model, and the comparison runs without it.
- **Any other exit code** is a crash. Start the same command again: finished pieces are kept.

## 4. Privacy

`engine_runs\`, `engine_tmp\` and the smoke worlds' engine folders hold files the engine writes itself; their checkpoint
`key.json` files record input paths that include the Windows account name. Keep these folders out of any archive or
share (D13). Every other file of this folder is free of account and host names (`shapv1_common.privacy_scan()`).
