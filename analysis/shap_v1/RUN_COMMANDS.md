# Commands for the owner: post hoc SHAP (rulings AW1-AW5), protocol v3

Run each command in your own PowerShell window, one at a time. Do not run any other engine job or rival board while
one of these is running: the rebuild's lock lives in this folder and cannot see `D:\treeroute\tmp`. Close games,
browsers and other large programs first (15.8 GB RAM; see the RAM note below).

**Owner rulings of 2026-11-13 and 2026-11-15 (rulings file, sections AY and BA):** scope (i), the nowcast of each
problem (AY1); D14 (b), so `--recorded-path-map` is valid (AY2); D8's 1e-12 alternative, so `--arcsine-tolerance 1e-12`
is valid (AY3). By 2026-11-15, 19:11, every scope (i) command then in this file had run: the coral nowcast pilot, the
fire, PM2.5, defo and NDVI runs, and their ridge and BARDL commands. On fire, PM2.5, defo and NDVI, ridge needed two
more short commands after `run_shap.py`, and NDVI one more for its published rival BARDL (section 2). Treeroute's B1
sensitivity (PROTOCOL.md sections 5 and 12, D3) had no command and had not run when the owner chose on 2026-11-15 to
run it as planned (ruling BA3); its command and status are in section 2, under "Treeroute's B1 sensitivity". The
Kraft LSTM stays out until D7 is ruled.

**Restarting.** Every command can be started again after a stop. Finished pieces are skipped only when their files and
their identity still match (the registered sample, the scripts, the engine folder, the path decision D14 and the D8
tolerance). Engine bank checkpoints are reloaded by their tree fingerprints; the census and R30 checkpoints of the
engines that have them are reloaded too.

**Logs.** Each command logs to `D:\treeroute\analysis\shap_v1\logs\`, one line per step, with timestamps.

**Results.** These go to `D:\treeroute\analysis\shap_v1\out\<problem>\lead_<L>\`:

- `treeroute\`, `treeroute_B1\` (treeroute's B1 sensitivity, section 2), `rival_<model>\`: `rows.parquet` (row-level
  SHAP at the feature and the variable level), `background_keys.parquet`, `meta.json`, `exactness.json` (rivals; in
  `rival_ridge\` outside coral it is `rival_shap.py`'s failed check, kept, and `ridge_shap_exactness.json` beside it is
  the check that passed);
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
one walk 50 s, two walks 100 s for 250 rows). Rivals: the boards' own timings, SHAP doubled likewise. They are the
estimates made before the runs. As logged in scope (i) (`logs\run_<problem>_scope_i.log`; rebuild peaks in
`rebuild\<problem>\lead_0\gates.json`): coral 17 min (peak 1.3 GB), fire 2.4 h over three runs (8.47 GB), PM2.5
5.8 h (4.69 GB), defo 7.7 h (10.3 GB) and NDVI 26.1 h (8.29 GB). The defo and NDVI peaks are above the table's 7 GB.

| Problem | Scope (i) nowcast | + (ii) one forecast lead | + (iii) every lead | Peak RAM | Disk kept (temp) |
|---|---|---|---|---|---|
| coral | 17-22 min | + 15-19 min (lead 183: rebuild 3.2 min, SHAP, rivals) | + 7 min (lead 365, declined: rivals only) | 1.5 GB | 0.4 GB (2.5 GiB) |
| PM2.5 | 6.9-7.5 h: census 0.8, derive 3.5, pool 0.5, bank 0.4, sampled routers 0.1-0.2; SHAP 0.6-0.8; rivals 0.9-1.3 (RF 10 min rebuild + 20-40 min SHAP); then ridge 9.5 s and the comparison again 10 s (measured; their own commands) | + 2.4-3.1 h (lead 6: pool 0.4, bank 0.4, routers 0.1, SHAP 0.6-0.8, rivals 0.9-1.3) | + 0.9-1.3 h (lead 12, declined: rivals only) | 6.5 GB | 1.2 GB per lead (5.5 GiB) |
| NDVI | 21-25 h (census and R30 about 17 h, derive 0.6, pool 0.6, bank 2.1, routers 0.1, SHAP 0.4-0.6, rivals 2.0-2.8; then ridge 45.7 s, BARDL 7.7 s and the comparison again 46 s (measured), their own commands) | + 2.0-2.8 h (lead 6, declined: rivals only) | + 2.0-2.8 h (lead 12, declined: rivals only) | 7 GB | 1.3 GB per lead (8 GiB, plus a 5.4 GB RF refit copy) |
| fire | 2.8-3.3 h: census 0.2, derive 1.6, pool 0.2, bank 0.1, GLS 0.06, routers and the identity twin 0.1, SHAP 0.2-0.3, rivals 0.4; then ridge 3.6 s and the comparison again 12 s (measured; their own commands) | + 0.4 h (lead 6, declined: rivals only) | + 0.4 h (lead 12, declined: rivals only) | 8.4 GiB free needed | 0.6 GB (2 GiB) |
| defo | 12-14 h: census and derive 0.3, vault and labels 2.7, pool 3.1, bank 1.2, 42 region routers 3.5 (21 regions: 1.75), SHAP 0.2-0.4, rivals 1.4-2.0; then ridge 23.9 s and the comparison again 24 s (measured; their own commands) | + 7-9 h (lead 1: pool 1.6, bank 1.2, silent step 0-1.5, routers 2.9, SHAP, rivals) | none (lead 1 is the last) | 7 GB | 1.5 GB per lead (6 GiB, plus a 3.7 GB RF refit copy) |

Totals over the five problems, run one after another:

- (i): 43-50 h.
- (ii): 55-66 h.
- (iii): 59-71 h.
- Disk kept is about 8 GB for (ii).
- The NDVI census copy (D9) would save about 15-17 h, but only with D14 (a) and a passing `checkpoint_proof.py check`.

Halving the defo regions (`--defo-regions 21`, owner decision D10) saves about 1.75 h at lead 0 and 1.45 h at lead 1.
It also halves the regions of the defo bootstrap. The runner refuses a `--n` or `--defo-regions` that differs from the
registered sample. Defo's sample has all 42 regions (registered 2026-11-14), so 21 regions would need a new sample
under a new `--tag`.

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

**Ridge and BARDL have their own commands.** On fire, PM2.5, defo and NDVI, `run_shap.py`'s rivals step stops ridge
at S-EXACT and reports "stopped at a gate" (seen on all four). That is expected:
`rival_shap.py`'s copy of the design adds the terms in another order (PROTOCOL.md section 4.2). Ridge's stop does not
affect the step's other rivals: the summary line of `logs\rival_shap_<problem>_lead0.log` lists ridge as
"stopped (a stop rule)" and the others as "done" (or "skipped (done)"); any other rival listed as stopped is a real
stop. `ridge_shap.py` repeats the board's own scoring, which matches every saved prediction bit for bit, and writes
ridge's SHAP values into `out\<problem>\lead_0\rival_ridge\`. `run_shap.py` never runs NDVI's published rival BARDL;
`bardl_shap.py` does. After the problem's `run_shap.py` has finished, run these lines one at a time, in this order; the
comparison comes last, so that it includes the new pieces.

Defo, after its `run_shap.py` and before NDVI's (`ridge_shap.py` refuses to start while another SHAP step runs):

```
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\ridge_shap.py --problem defo --lead 0
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\compare_shap.py --problem defo --lead 0
```

NDVI, last (one comparison then covers ridge and BARDL), after its `run_shap.py`:

```
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\ridge_shap.py --problem ndvi --lead 0
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\bardl_shap.py --problem ndvi --lead 0
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\compare_shap.py --problem ndvi --lead 0
```

- Fire and PM2.5: done (2026-11-14, 04:46-04:48). Fire's ridge is in the comparison as "raw model, declined by its
  guard" (D6), outside the main set. PM2.5's ridge is in the main set.
- Defo: done (2026-11-14, 14:34-14:35); its ridge is in the main set. NDVI: done (2026-11-15, 19:09-19:11); its ridge
  is in the main set, and so is BARDL by D16's default, the frozen plan, which the owner kept on 2026-11-15
  (ruling BA1; PROTOCOL.md section 12).
- Coral needs nothing: `rival_shap.py`'s ridge passed there. `ridge_shap.py --problem coral --lead 0` says "nothing to
  do" and writes nothing but its log lines.
- No `--n` is needed: `ridge_shap.py` uses the registered N and `bardl_shap.py` the default 1,000; a given `--n` must
  equal the registered N.
- One at a time. `ridge_shap.py` refuses to start (exit 1; nothing is written but its log line) while a heavy-job lock
  exists or another SHAP step runs (`run_shap`, `tr_rebuild`, `tr_shap`, `rival_shap`, `compare_shap`, `make_sample`,
  `bardl_shap` or `ridge_shap`). `bardl_shap.py` has no such check: run it alone, after NDVI's `run_shap.py` has
  finished (it reads the registered NDVI sample).
- Time and RAM, as logged. Ridge: fire 3.6 s, PM2.5 9.5 s, defo 23.9 s and NDVI 45.7 s (peak 0.57, 0.54, 2.04 and
  1.69 GB; the reviews had estimated defo at 2-5 min and NDVI at 3-8 min, about 2.5 GB each); the comparison again
  12 s, 10 s, 24 s and 46 s. BARDL: 7.7 s (peak 0.28 GB). Disk, measured (folder totals): the ridge pieces 1.4 MB on
  fire, 1.3 MB on PM2.5, 2.5 MB on defo and 4.0 MB on NDVI; BARDL's piece 0.2 MB.
- Logs: `logs\ridge_shap_<problem>_lead0.log` and `logs\bardl_shap_ndvi_lead0.log`. BARDL's piece is
  `out\ndvi\lead_0\rival_bardl_h1\`.
- A REMINDER line (on screen and in the log) means that the problem's comparison does not include that piece yet: run
  the comparison line. After `run_shap.py`, the ridge and BARDL lines each log one, as expected: the run's own
  comparison lacks them. The new comparison replaces it, so nothing in the first needs reading.
- To check the new comparison without reading its tables, run the ridge line (on NDVI also the BARDL line) once more:
  each says "skipped" in seconds and logs no REMINDER when the comparison includes its piece (the logs keep the lines
  of earlier runs too). `logs\compare_<problem>_lead0.log` lists the models, their links, the declined models and the
  main set. BARDL's link key is `identity|c=-|ub=1`; it is in the main set when treeroute's is the same, since its
  guard passed.
- If `run_shap.py` is started again for one of these problems, its rivals step again reports ridge "stopped at a gate"
  and rewrites only `exactness.json` in `rival_ridge\`. The finished ridge piece stays, and that run's comparison
  includes it.
- Any BARDL gate stop, a wrong `--n`, `--register` or `--sample-root` included, removes its piece's done record, so
  the comparison no longer sees a finished BARDL piece (section 3). Run the BARDL line again (under 2 min), then the
  comparison.
- In BARDL's `meta.json`, `background_design` may show a test-part difference of about 1e-16: information only, not a
  failure.
- `--exactness-only` runs only S-ENV and S-EXACT (no sample needed; seconds). Ridge's ran on every problem in the
  checks of 2026-11-14, so it is not needed now; an S-EXACT stop of it writes `FAILED.json` and removes
  `ridge_shap.py`'s done record, as any S-EXACT stop does. For a cross-check in a folder that holds another script's
  piece (coral), pass both `--out-root` and `--log-dir` under `smoke\`. BARDL's (4.7 s) writes only `exactness.json` on
  success; when it stops, it also writes `FAILED.json` and removes the BARDL piece's done record.

**Treeroute's B1 sensitivity has its own command** (PROTOCOL.md sections 5 and 10; ruling BA3). With
`--background B1`, `tr_shap.py` explains treeroute's 1,000 sampled rows again, each against all of its unit's router
fit rows at or before the cut, not only those of the same calendar month (B2). It writes
`out\<problem>\lead_0\treeroute_B1\` (the same files as `treeroute\`) and adds its lines to the end of the log of the
main run (treeroute's B2 SHAP step, whose piece is `treeroute\`), `logs\tr_shap_<problem>_lead0.log`;
`compare_shap.py` never reads `treeroute_B1\`. Run this one line in one PowerShell window while nothing else runs. It
runs defo, fire, PM2.5 and NDVI in that order and stops at the first run that fails, printing "STOPPED at" and the
problem:

```
foreach ($p in 'defo','fire','pm25','ndvi') { py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\tr_shap.py --problem $p --lead 0 --background B1; if ($LASTEXITCODE -ne 0) { "STOPPED at $p"; break } }
```

- Status. Given on 2026-11-15 at 23:04; the owner started it at 23:06:16, defo first (the agent's process check of
  23:06:54). It ended with all four runs finished and no "STOPPED at" line; their "done in" lines: defo at 23:14:02
  (465.9 s), fire at 23:58:00 (2,636.6 s), PM2.5 on 2026-11-16 at 04:56:11 (17,890.4 s) and NDVI at 08:14:14
  (11,883.1 s). The owner pasted the window on 2026-11-16 at about 17:00. The agent then checked it against the logs
  and listed the four `treeroute_B1\` folders: each holds `rows.parquet.done.json` and no `FAILED.json`. Defo's check
  (below) passed: its set-up and summary lines equal its main run's (2026-11-14 12:12:00 and 12:18:55) apart from the
  bracketed times. NDVI's B1 run merged the same five context columns as its main run; fire and PM2.5 merged none,
  as their main runs did. The full identity check of PROTOCOL.md section 10 (every SHAP value of the two defo
  pieces) is made with the verification of the numbers. It was made on 2026-11-16 by the independent re-computation:
  exactly 0 at both levels, with the same rows, players and variables, and the two `rows.parquet` files are
  byte-identical (PROTOCOL.md section 14).
- Coral is not in the line: B1 is not defined for it, and `tr_shap.py` refuses it (the neighbour kind).
- Defo comes first, as a 7-minute check of the B1 code before the long runs. Defo is annual, so its B1 background
  is its main run's: its set-up line (the one with "background pairs") must give 16,000 pairs, as the main run's did,
  and its piece must repeat the main run exactly, so its summary line (it begins "treeroute: 1000 rows") equals the
  main run's of 2026-11-14 12:18:55 apart from the bracketed time at its start. Anything else is a finding to report,
  not a result (PROTOCOL.md sections 10 and 14). The line goes on to fire whatever defo's summary says (it stops only
  on a failed run), so this check is made from the pasted log.
- Time, estimates: 12 times the main runs' tree-SHAP times, because B1 holds about 12 times as many pairs on the
  monthly problems. Fire about 55 min, PM2.5 about 4.7 h, NDVI about 4.1 h; defo about 7 min (the same pairs as its
  main run); about 10 h in all. Memory: only arrays of pair length grow with the background (the walk takes the
  pairs in chunks of 20,000); the peak memory of the main runs' SHAP step was not logged (the peaks in "Where the
  times come from" are the rebuilds').
- Conditions: no other SHAP job and no Python on project data running (`tr_shap.py` has no lock or process check of
  its own); at least 6 GiB of RAM free (the smoke guards' threshold; `tr_shap.py` does not measure its own peak);
  games and other large programs closed.
- First runs: before this line, B1 had run only on the fire smoke world (12 rows, 2026-11-12). B1 on the region kind
  (defo) and on the real rebuilds is first run here; the stop rules of PROTOCOL.md sections 5 and 11 apply as in the
  main runs, except S-BG's check of the registered background keys, which B1 does not use (`tr_shap.py`).
- Restarting: a problem whose B1 piece is finished with matching hashes is skipped ("finished piece found with
  matching hashes: skipped"), so after a stop the same line can be started again.
- Paste back: each run's lines from its first line (a "context column ... kept as its own player" line, if any,
  comes before the "background pairs" line) to its "done in" line (the B1 lines carry no B1 label; they are the
  log's last lines), or the "STOPPED at" line with the log lines above it.

**Useful switches of `run_shap.py`:**

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
  with the real defo arm (region kind, log_c corrector): every gate including the region E9 and E10 proofs;
- the BARDL loader (`tests\smoke_bardl.py --label fix`: synthetic step 2026-11-13, real-data steps 2026-11-14; report
  `smoke\bardl_fix\smoke_report.json`), on 29 explained rows of the NDVI smoke sample (equal to the NDVI sample
  registered on 2026-11-14) under their own register:
  - S-ENV; S-EXACT on 95,184 of 95,184 test rows (`pre` and `raw`), with its 46 board record checks (the slim copy's
    provenance: 266 of 266 files);
  - exact SHAP against brute force over all 2^10 coalitions and against the grouped game: on 7 synthetic rows (missing
    values on either side, a missing climate mean, a fallback unit) and on 10 of the 29 real rows (8 of them with a
    missing climate mean);
  - S-ADD; S-EVAL on explained and background rows; S-ZERO; `normal` exactly 0;
  - the owner's run's own S-SAMPLE and S-BG checks on all 16,914 keys of the 1,000-row NDVI smoke sample (no SHAP
    value), and the slim values of the nine players and the normal equal to the common export's, bit for bit;
  - the S-SAMPLE and S-BG refusals (exit 3, no done record left); resume; `--rows 10`;
  - the comparison taking BARDL as a same-link model, the D6 label on a declined copy, and a BARDL re-run afterwards
    skipped with no REMINDER (run with `--no-ridge`); its check values printed on screen include BARDL's family
    shares on the 29 rows;
  - times: synthetic 24.7 s, exact 4.8 s, real 53.4 s, compare 9.6 s; peak RAM 0.3 GB;
- the ridge loader (`tests\smoke_ridge.py --label v4`, every check PASS; report `smoke\ridge_v4\smoke_report.json`):
  - synthetic, 75 checks (2026-11-14 02:47): the board's own fit and scoring reproduced bit for bit (91,440 rows in 2
    column-ordered blocks, missing flags), while `rival_shap.py`'s row-by-row way misses rows; one call for the whole
    test set, 50,000-row blocks and 1 BLAS thread all caught in link space; exact SHAP against brute force at both
    levels, also with an identity link and an open upper bound; every gate, refusal and write rule; the process gate
    and its own lineage; `rival_shap.py`'s own main() run beside the loader (S5b);
  - real, 46 checks (2026-11-14 04:44-04:46): fire lead 0 (S-EXACT on 96,000 of 96,000 test rows, then SHAP on the
    registered fire sample, into `smoke\`); the comparison taking ridge as a declined fire rival (on copies of fire's
    four other pieces, kept in `smoke\ridge_v4\fire_models\`; structured fields only; its `compare\` folder then
    removed); coral lead 0 against its finished piece (every column
    equal); the S-EXACT check alone on PM2.5, defo and NDVI (every test row; every block column-ordered);
  - times: synthetic 25 s, fire 20 s, compare 9 s, coral 17 s, others 28 s; peak RAM 0.3 GB in the smoke itself, up
    to 1.5 GB in its `ridge_shap.py` children (defo's S-EXACT check).

**Not exercised by any smoke:** the BARDL loader on the registered NDVI sample (its smoke used 29 rows of the NDVI
smoke sample under their own register); the ridge loader's full run on defo and NDVI (its smoke checked all their test
rows; the background read and the SHAP step are first run by the owner's commands); the Kraft LSTM (D7); the RF memmap
path for large refit sets (NDVI 5.4 GB, defo 3.7 GB; PM2.5's 1.3 GB set is below the 1.5 GiB threshold and was read in
RAM on 2026-11-14); the defo lead-1 region path; `rival_shap.py` on problems other than coral (the fire, PM2.5, defo
and NDVI runs have since run it). Each is first run by its own owner command, and its gates stop it on any difference.
By 2026-11-15 the commands of this file had run all of them but the Kraft LSTM (D7, left out) and the defo lead-1
region path (outside scope (i)); no gate stopped them except `rival_shap.py`'s expected ridge stops (PROTOCOL.md
sections 4.2 and 14). **The smoke worlds build their references on today's OS and libraries, so they cannot detect a
difference between the old and the new installation; only a real headline rebuild (the coral pilot) can.**

Repeat the quick checks on the morning of a long run if anything was installed in between. Each takes up to 1-2 min:

```
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\tests\smoke_unit.py
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\tests\smoke_world.py --problem pm25
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\tests\smoke_world.py --problem fire
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\tests\smoke_world.py --problem defo
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\tests\smoke_world.py --problem defo --arm log_c_corrector_unweighted --restricted
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\tests\smoke_ridge.py --label quick --step synthetic --fresh
```

The ridge line runs the ridge smoke's synthetic step: no real data, about 25 s on 2026-11-14, at least 3 GiB free. It
writes only `smoke\ridge_quick\`; `--fresh` first removes that label's own synthetic folder, so the line can be
repeated. It never touches `smoke\ridge_v4\`, the record of the checks of 2026-11-14.

BARDL needs no quick check of its own: its command stops at S-ENV or S-EXACT before any SHAP value. The exactness step
of its smoke repeats that check alone, on every lead-0 test row (about 5 s on 2026-11-14, under 0.5 GB; it reads the
NDVI board's files and computes no SHAP value):

```
py -3.9 -I -B D:\treeroute\analysis\shap_v1\scripts\tests\smoke_bardl.py --label quick --step exact --fresh
```

It writes only `smoke\bardl_quick\`; `--fresh` first removes that label's own `exact` folder, so the line can be
repeated. It never touches `smoke\bardl_fix\`, the record of the checks of 2026-11-14. Before it reads real data it
checks that `D:\treeroute\tmp\treeroute_heavy_job.lock` does not exist, that no `run_shap`, `tr_rebuild`, `tr_shap`,
`rival_shap`, `compare_shap` or `make_sample` process runs and that at least 6 GiB is free; otherwise it stops with
exit 4. It does not see the `engine_tmp` lock or a `ridge_shap.py` or `bardl_shap.py` run, so start it alone. The
smoke's real and comparison steps are not repeated here: they compute BARDL SHAP values on 29 NDVI rows and print
their check values on screen, BARDL's family shares among them (PROTOCOL.md section 14).

## 3. What a stop means

- **Exit code 3** is a stop rule. The step's `gates.json`, `exactness.json` or `FAILED.json` names the gate and its
  values. No SHAP value exists for that model, and the comparison runs without it.
- **Any other exit code** is a crash. Start the same command again: finished pieces are kept.
- **`ridge_shap.py`:**
  - Exit 3 is a gate. S-ENV, and S-SAMPLE on the sample or on `--n`, write nothing but their log lines: a finished
    ridge piece stays as it is. Every other gate removes `ridge_shap.py`'s own done record and writes `FAILED.json` in
    `out\<problem>\lead_0\rival_ridge\` (it names the gate; the shared writer's stops name their checks in its
    `checks_passed`); S-EXACT also writes `ridge_shap_exactness.json`. The comparison then runs without ridge until
    `ridge_shap.py` passes again. In a folder that holds another script's finished piece (coral), no stop writes
    anything.
  - Exit 1 is a crash or a refusal; the log's CRASH or REFUSED line says which (a refused `--out-root` or `--log-dir`
    shows on screen only). A refusal writes nothing but that line: another SHAP step or a heavy-job lock (start it
    again when that has finished), no ridge record on the board, a changed source of `rival_shap.py`'s copied
    `run_ridge` or `ridge_design` (the drift guard), a done record that cannot be read, psutil not importable, or
    another script's piece that is not current (or `--exactness-only` in its folder).
  - Exit 2 is a mistyped option; nothing is written, not even the log.
  - Outside coral, `exactness.json` in `rival_ridge\` is `rival_shap.py`'s own check and says FAIL. That is expected,
    and the file is kept.
- **`bardl_shap.py`** exits with code 3 on every gate, S-ENV, S-SAMPLE and S-BG included (where `rival_shap.py`
  exits with 1). Every such stop first removes the BARDL piece's done record (a wrong `--n`, `--register` or
  `--sample-root` included), then writes `FAILED.json` in `out\ndvi\lead_0\rival_bardl_h1\`; S-EXACT also writes
  `exactness.json`. An older `rows.parquet` may stay in the folder; without its done record the comparison ignores
  it. Run the BARDL command again, then the comparison.
  - `FAILED.json` names the gate, except after the writer's checks (S-ADD, S-EVAL, S-ZERO, S-RESID): it then lists
    them under `checks_passed`, with no gate field.
  - A slim train file whose bytes differ from its manifest is found only while the background rows are read. The
    run then stops at S-EXACT (`FAILED.json`, detail beginning `inputs: slim file`), even though `exactness.json`,
    written earlier, says pass true. `FAILED.json` is the record that counts.
- A **REMINDER** line of `ridge_shap.py` or `bardl_shap.py` is not a stop: the comparison does not include that piece
  yet (section 2).
- **The smokes** (`tests\smoke_ridge.py`, `tests\smoke_bardl.py`): exit 0, every check passed; exit 1, a check failed
  (`smoke_report.json` lists it), a refusal (for example a step folder left by an earlier run: use a new `--label`,
  or `--fresh`) or a crash; exit 4, the heavy-job guard stopped a step (a lock, a SHAP process of the owner, or too
  little free RAM: 6 GiB; 3 GiB for ridge's synthetic step). Start it again when the machine is free.

## 4. Privacy

`engine_runs\`, `engine_tmp\` and the smoke worlds' engine folders hold files the engine writes itself; their checkpoint
`key.json` files record input paths that include the Windows account name. Keep these folders out of any archive or
share (D13). Every other file of this folder is free of account and host names (`shapv1_common.privacy_scan()`).
