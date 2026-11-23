# Implementer B, round 14: how to re-run, and what was opened

Short names: SHAP = `D:\treeroute\analysis\shap_v1`; V = `SHAP\verify_v1`. Everything this implementer wrote is in
`V\B\`. The method choices are in `V\B\choices.md` (written before any official number was seen); the results are
`V\B\results.json` (format: `V\spec\SPEC.md` and `V\spec\results_schema.json`) with the per-draw values in
`V\B\draws\<p>.npz` (items 1-8) and `V\B\draws\b1_<p>.npz` (item 9).

## Re-run

Any working folder (every path in the scripts is absolute). Windows PowerShell 5.1, Python 3.9 in isolated mode.
Run in this order (times of the final run, 2026-11-16):

```
py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\B\scripts\b_selftest.py        # 1.6 s  checks of the statistics code
py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\B\scripts\b_global_index.py    # 6.5 s  section 8's global-index rule
py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\B\scripts\b_compare.py         # 52.4 s brief items 1-8
py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\B\scripts\b_b1.py              # 10.5 s brief item 9 (B1)
py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\B\scripts\b_assemble.py        # 1.5 s  writes V\B\results.json
py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\spec\tools\validate_results.py --results D:\treeroute\analysis\shap_v1\verify_v1\B\results.json --draws D:\treeroute\analysis\shap_v1\verify_v1\B\draws --shap D:\treeroute\analysis\shap_v1   # 3.5 s
py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\B\scripts\b_crosscheck.py      # 95.6 s loop-based re-computation of a sample of items 1-8
py -3.9 -I -B D:\treeroute\analysis\shap_v1\verify_v1\B\scripts\b_crosscheck_b1.py   # 83.6 s the same for a sample of item 9
```

`b_compare.py` and `b_global_index.py` take problem names as optional arguments (default: all five); run with all
five before `b_assemble.py`. No seed, no random stream: the draws are the saved matrices; everything is deterministic.

Validator output on the final files: `V\B\results.json: 0 errors, 0 warnings` (with `--draws` and `--shap`);
`validate_results.py --selftest`: `SELFTEST PASSED`. `b_selftest.py`: `SELFTEST PASSED`. `b_crosscheck.py`:
`CROSSCHECK PASSED`. `b_crosscheck_b1.py`: `CROSSCHECK B1 PASSED`.

Versions: Python 3.9.13, numpy 2.0.2, pandas 2.3.3, pyarrow 21.0.0, scipy 1.13.1 (no other package; `jsonschema` is
not installed, so the spec's own validator was used).

## Scripts

| script | what | reads | writes |
|---|---|---|---|
| `b_lib.py` | shared statistics (region weighting, rankings, Spearman, tau-b, RBO, Jaccard, W, families, pair block, intervals) | - | - |
| `b_selftest.py` | constructed examples against scipy and direct formulas; the draw generator | `SHAP\out\<p>\lead_0\compare\bootstrap_draws.npy` | - |
| `b_global_index.py` | the global-index rule on the lead's test set (item 3) | per_lead.json (`models` only); `meta.json` (`variable_map`) of the models of `models`; the export's `lead_0\export_manifest.json` (`counts`) and `lead_0\test\*.parquet` (columns `unit`, `time`, `issue` and the candidate `x__` columns) | `V\B\work\global_<p>.json` |
| `b_compare.py` | **items 1-8** | per_lead.json (`models`, `main_set`, `declined_by_guard`, `links`, `rows`, `draws_sha256`); `bootstrap_draws.npy`; `meta.json` and `rows.parquet` of the pieces named in `models`; `V\B\work\global_<p>.json` | `V\B\work\problems.json`, `V\B\draws\<p>.npz` |
| `b_b1.py` | **item 9** (defo's identity check first) | `SHAP\SAMPLE_REGISTER.txt`; per_lead.json (`models`, `draws_sha256`); `bootstrap_draws.npy`; `treeroute_B1\` (`meta.json`, `rows.parquet`, `rows.parquet.done.json`; `FAILED.json` would be read if present; defo's `background_keys.parquet` hashed); `treeroute\` (`meta.json`, `rows.parquet`; defo's `background_keys.parquet` hashed); `SHAP\logs\tr_shap_<p>_lead0.log` (defo, fire, pm25, ndvi); `V\B\work\global_<p>.json` | `V\B\work\b1.json`, `V\B\draws\b1_<p>.npz` |
| `b_assemble.py` | results.json with the one-line choices | `V\B\work\problems.json`, `V\B\work\b1.json` | `V\B\results.json` |
| `b_crosscheck.py`, `b_crosscheck_b1.py` | slow loop-based re-computation of sampled numbers (full sample and single draws) | `V\B\results.json`, `V\B\draws\*.npz`, some `rows.parquet` (main pieces; B1: `treeroute` and `treeroute_B1` of fire, pm25, ndvi), `bootstrap_draws.npy` | - |
| `b_inspect.py`, `b_inspect2.py`, `b_inspect3.py` | structure inspection before the computation (no statistic) | per_lead.json structural keys; `bootstrap_draws.npy`; every piece's `meta.json` and `rows.parquet` (schema, key columns, `resid_flag`, `pre`); `SHAP\sample\<p>\sample.parquet` (schema); the export manifests (`groups`, `counts`) and one test file's schema per problem | - |
| `b_peek.py`, `b_peek_b1.py` | print my own work files | `V\B\work\problems.json`, `V\B\work\b1.json` | - |

**Items 1-8 do not depend on B1.** `b_compare.py` (and `b_global_index.py`, whose output it reads) opens only the
pieces named in per_lead.json's `models` (it asserts that `treeroute_B1` is not among them) and nothing under any
`treeroute_B1\` folder. Only `b_b1.py` and `b_crosscheck_b1.py` open `treeroute_B1\`.

The lead's test set (identification I04): the rivals' export of each headline run, lead 0 (not under SHAP; the paths
hold no user folder): `D:\treeroute\rival_export\coral\20261020_f3b8e3da`, `...\defo\20261017_d71c61f4`,
`...\fire\20261017_869d1f38`, `...\pm25\20261007_74e67609`, `...\ndvi\20261016_d1de3158`, each `lead_0\test\*.parquet`
and `lead_0\export_manifest.json`.

## Every file opened in this round (code and by hand), by short path

- V: `V\_brief\brief_verify.md`; `V\spec\SPEC.md`; `V\spec\results_schema.json`; `V\spec\tools\validate_results.py`
  (read, and run); folder listings of V, `V\B`, `V\_brief`, `V\spec`.
- Protocol and records: `SHAP\PROTOCOL.md` (all sections; the method from sections 5, 8, 9 and 10);
  `SHAP\RUN_COMMANDS.md` (its headings and lines with "B1", and section 2's B1 command and status, lines 196-245);
  `SHAP\SAMPLE_REGISTER.txt`; `SHAP\logs\tr_shap_defo_lead0.log`, `tr_shap_fire_lead0.log`, `tr_shap_pm25_lead0.log`,
  `tr_shap_ndvi_lead0.log` (read in full).
- Compare folders: `SHAP\out\<p>\lead_0\compare\per_lead.json` (loaded in Python; only `models`, `main_set`,
  `declined_by_guard`, `links`, `rows`, `sample_sha256` and `draws_sha256` were accessed or printed) and
  `SHAP\out\<p>\lead_0\compare\bootstrap_draws.npy`, for the five problems; the compare folders' file names were
  listed. No other compare file was opened.
- Pieces (all five problems): every piece's `meta.json` and `rows.parquet` (the `treeroute_B1` pieces only by
  `b_b1.py`, `b_crosscheck_b1.py` and the inspection scripts); `rows.parquet.done.json` of `SHAP\out\fire\lead_0\treeroute`,
  `...\rival_lgbm`, `...\treeroute_B1` (by hand) and of every `treeroute_B1` piece (by `b_b1.py`); defo's
  `treeroute\background_keys.parquet` and `treeroute_B1\background_keys.parquet` (SHA-256 only).
- Other run records opened by hand while locating the lead's test set and the regions: `SHAP\out\fire\lead_0\rival_lgbm\exactness.json`,
  `SHAP\out\fire\lead_0\rival_rf\exactness.json`, `SHAP\out\fire\lead_0\rival_ridge\ridge_shap_exactness.json` (keys),
  `SHAP\out\fire\RUN_SUMMARY_scope_i.json`, `SHAP\rebuild\fire\lead_0\DONE.json`, `SHAP\rebuild\fire\lead_0\precheck.json`
  (keys), `SHAP\rebuild\fire\lead_0\rows.parquet` (schema), `SHAP\sample\fire\sample_manifest.json`,
  `SHAP\sample\defo\sample_manifest.json`, `SHAP\sample\<p>\sample.parquet` (schema; columns `row` and `group`, for the
region order of I02), the fire export's
  `lead_0\export_manifest.json` (keys); folder listings of SHAP, `SHAP\out\<p>\lead_0` (recursive), `SHAP\logs`,
  `SHAP\sample`, `SHAP\rebuild\fire`, `D:\treeroute`, `D:\treeroute\rival_export` (tree), `D:\treeroute\rivals`.
- Not opened: `SHAP\scripts\compare_shap.py`, `SHAP\scripts\shapv1_stats.py` and every other script of `SHAP\scripts`
  (none was run); every compare file other than `per_lead.json` (structural keys) and `bootstrap_draws.npy`;
  `V\A\`, `V\reconcile\`, `V\skeptic\`; `SHAP\smoke\` (`bardl_fix` included).

## Files written (all under V\B)

`results.json`, `choices.md`, `README.md`, `scripts\*.py`, `draws\coral.npz`, `draws\defo.npz`, `draws\fire.npz`,
`draws\pm25.npz`, `draws\ndvi.npz`, `draws\b1_fire.npz`, `draws\b1_pm25.npz`, `draws\b1_ndvi.npz`,
`work\global_<p>.json` (five), `work\problems.json`, `work\b1.json`. The npz keys are the JSON paths below
`problems.<p>` (or `b1.<p>`) joined by `/`; rows are the 2,000 draws in the order of `bootstrap_draws.npy`; NaN where
a number is not finite on a draw.
