# Implementer A, round 14: how to re-run, what was opened, what was written

Names: SHAP = `D:\treeroute\analysis\shap_v1`; V = `SHAP\verify_v1`; ROOT = the research-paper folder (not used).
Everything of this implementer is in `V\A\`. The choices are in `V\A\choices.md`, and the results in
`V\A\results.json` (schema `round14_results_v1`).

## Re-run (Windows PowerShell 5.1, any working folder: every script uses absolute paths)

Run these in this order (times measured on 2026-11-16):

| # | command | what it does | time |
|---|---|---|---|
| 1 | `py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\A\scripts\a_selftest.py` | the statistic code on constructed examples (with scipy as an outside reference): average ranks, Spearman and tau-b with ties, RBO (a ranking with itself = 1; direct prefix sums), Kendall's W (textbook case, the no-tie identity, tied identical rankings), region weights, draw counts, Jaccard, percentiles | 0.8 s |
| 2 | `py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\A\scripts\a05_global_rule.py` | section 8's global-index rule on each problem's lead-0 test set; writes `V\A\work\global_rule_<p>.json` | 14 s |
| 3 | `py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\A\scripts\a10_items1_8.py` | **brief items 1-8**, all five problems (or name some: `... a10_items1_8.py coral fire`); writes `V\A\work\items_<p>.json` and `V\A\draws\<p>.npz` | 86 s on the final run (coral 13.5, defo 20.1, fire 11.6, pm25 9.1, ndvi 31.2) |
| 3a | `py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\A\scripts\a50_draws_generator_probe.py` | diagnostic for I02: reproduces every entry of each `bootstrap_draws.npy` from section 8's salt (nothing depends on it) | 1.1 s |
| 4 | `py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\A\scripts\a20_b1.py --identity-only` | defo's B1 identity check alone, printed (it was run first, before any other B1 number) | 0.8 s |
| 5 | `py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\A\scripts\a20_b1.py` | **brief item 9** (B1): the status of every problem; defo's identity check; then, only because it held, the fire, pm25 and ndvi B1 numbers; writes `V\A\work\b1.json` and `V\A\draws\b1_<p>.npz` | 11 s |
| 6 | `py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\A\scripts\a40_spotcheck.py` | spot checks of steps 3 and 5 by a second code path: pandas groupby for I, S and family shares; explicit region loops for draws 0 and 1999; scipy for Spearman and tau-b; Python sets for the top-20 union, Jaccard and RBO; a direct-loop W | 1.6 s |
| 7 | `py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\A\scripts\a30_assemble.py` | writes `V\A\results.json` | 2 s |
| 8 | `py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\spec\tools\validate_results.py --results D:\treeroute\analysis\shap_v1\verify_v1\A\results.json --draws D:\treeroute\analysis\shap_v1\verify_v1\A\draws --shap D:\treeroute\analysis\shap_v1` | the spec's format validator | 3.4 s |

Steps 3 and 5 need step 2's files. Step 7 needs steps 3 and 5.

These scripts only inspect structure or print a summary, and compute nothing that results.json uses:
- `a00_inspect.py`: per_lead.json's structural keys, meta.json summaries and row-file keys;
- `a01_meta_detail.py`: meta.json fields;
- `a02_schemas.py`: parquet schemas;
- `a03_varmaps.py`: the variable maps;
- `a04_checks.py`: row keys, regions, `resid_flag`, `pre` > 0 counts and the draws' SHA-256;
- `a90_view.py`, `a91_view_b1.py`, `a92_nulls.py`: summaries of this implementer's own outputs.

Their printouts are in `V\A\work\a00_inspect.txt` and `V\A\work\a03_varmaps.txt`.

`a_lib.py` (readers, ranks, Spearman, tau-b, RBO, Jaccard, W, percentile intervals, the JSON and per-draw writer) and
`a_core.py` (importances and pair statistics) are imported by steps 3 and 5. The main pairs and the B1 pair therefore
run through the same code and the same choices.

## Which script computes what; B1 kept apart

- Items 1-8: `scripts\a10_items1_8.py`. **It opens nothing under any `treeroute_B1\` folder.** It reads only the pieces
  named by per_lead.json's `models`, and that list never holds `treeroute_B1`. The script stops if it does. The files
  it opened are recorded per problem in `V\A\work\opened_items_<p>.json`, and none of them names `treeroute_B1`.
- Item 9: `scripts\a20_b1.py` (files opened: `V\A\work\opened_b1.json`). It first records each problem's status and
  computes defo's identity check. It computes the fire, pm25 and ndvi numbers only when that check is exactly 0 with
  the same rows, players and variables, which it is.

## Software

Python 3.9.13, numpy 2.0.2, pyarrow 21.0.0, scipy 1.13.1 (self-test and spot checks only), pandas 2.3.3 (inspection
and spot checks only). No package was installed.

## Every file opened (short paths; read-only)

The ground truth and the format:
- `V\_brief\brief_verify.md` (in full), `V\spec\SPEC.md` (in full), `V\spec\results_schema.json` (in full) and
  `V\spec\tools\validate_results.py` (read for the format, then run).
- `SHAP\PROTOCOL.md`: its section headings, then sections 3 (to section 4's opening paragraph), 5, 8, 9, 10 and 14.

The pieces, read by code:
- `SHAP\out\<p>\lead_0\compare\per_lead.json`, five files. They were loaded in Python, and only `models`, `main_set`,
  `declined_by_guard`, `links`, `rows`, `sample_sha256` and `draws_sha256` were kept or printed.
- `SHAP\out\<p>\lead_0\compare\bootstrap_draws.npy`, five files (the SHA-256 of the whole file was checked).
- The names of the files in each compare folder were listed. No other compare file was opened.
- `SHAP\out\<p>\lead_0\<piece>\rows.parquet` and `meta.json` of all 29 pieces (the 24 of the comparisons and the four
  `treeroute_B1`).
- `rows.parquet.done.json`: read by code for the four `treeroute_B1` pieces, and printed for the `treeroute` and
  `rival_lgbm` pieces of every problem.
- `SHAP\out\fire\lead_0\treeroute\background_keys.parquet`: schema only.

The records:
- `SHAP\SAMPLE_REGISTER.txt` and `SHAP\machine_shap.yaml`.
- `SHAP\RUN_COMMANDS.md`: lines 1-60 and section 2's B1 part, lines 195-244.
- `SHAP\sample\fire\sample_manifest.json`; `SHAP\sample\fire\sample.parquet` (schema only).
- `SHAP\rebuild\fire\lead_0\gates.json`, `precheck.json` and `DONE.json`; `SHAP\rebuild\fire\lead_0\rows.parquet`
  (schema only).
- The logs:
  - `SHAP\logs\tr_shap_<p>_lead0.log` for defo, fire, pm25 and ndvi, in full;
  - `SHAP\logs\rival_shap_fire_lead0.log`, its first 30 lines;
  - the "test set:" lines of `SHAP\logs\rival_shap_<p>_lead0.log`, all five problems.
  - The `compare_*.log` files were not opened.
- The headline fire run: the names of the files in `D:\treeroute\runs\fire\headline\20261017_869d1f38\`, and
  `test_preds.parquet` there (schema only).
- The lead-0 test sets: the folder listings of `D:\treeroute\rival_export\<p>\<run>\`. Read by code: every
  `lead_0\test\<region>.parquet`, columns `unit`, `time` and the players' feature columns only. Schemas only:
  `D:\treeroute\rival_export\fire\20261017_869d1f38\lead_0\test\alaska_interior_taiga.parquet`,
  `D:\treeroute\rival_export\coral\20261020_f3b8e3da\lead_0\test\Fiji.parquet` and
  `D:\treeroute\rival_export\defo\20261017_d71c61f4\lead_0\units.parquet`.

Not opened: `SHAP\scripts\compare_shap.py`, `SHAP\scripts\shapv1_stats.py`, and every other script of `SHAP\scripts`.
Also not opened: every compare file except per_lead.json (structural keys) and `bootstrap_draws.npy`, `V\B\`,
`V\reconcile\`, `V\skeptic\`, `SHAP\smoke\` (`bardl_fix` included) and the `RUN_SUMMARY_scope_i.json` files. No
script of SHAP was run.

## Every file written (all inside `V\A\`)

- `results.json`, `choices.md`, `README.md`.
- `scripts\`: `a_lib.py`, `a_core.py`, `a_selftest.py`, `a00_inspect.py`, `a01_meta_detail.py`, `a02_schemas.py`,
  `a03_varmaps.py`, `a04_checks.py`, `a05_global_rule.py`, `a10_items1_8.py`, `a20_b1.py`, `a30_assemble.py`,
  `a40_spotcheck.py`, `a50_draws_generator_probe.py`, `a90_view.py`, `a91_view_b1.py`, `a92_nulls.py`.
- `draws\`: `coral.npz`, `defo.npz`, `fire.npz`, `pm25.npz`, `ndvi.npz`, `b1_fire.npz`, `b1_pm25.npz`, `b1_ndvi.npz`.
  They hold float64 arrays, one row per draw in the draw matrix's row order, NaN where a value is not finite. Keys are
  JSON paths below `problems.<p>` or `b1.<p>`.
- `work\`: `a00_inspect.txt`, `a03_varmaps.txt`, `global_rule_<p>.json` (5), `items_<p>.json` (5), `b1.json`,
  `opened_items_<p>.json` (5), `opened_b1.json`.

## Validator output on the final files

```
D:\treeroute\analysis\shap_v1\verify_v1\A\results.json: 0 errors, 0 warnings
```

(`--selftest` of the validator: SELFTEST PASSED.) Own checks: `a_selftest.py` SELFTEST PASSED; `a40_spotcheck.py`
SPOTCHECK PASSED.
